// Watches per-plugin delta counts and raises a SignalK notification when an
// enabled plugin that should be publishing has gone silent.
//
// Detection reads `app.providerStatistics` — the counter the server increments
// at the top of handleMessage, before $source rewriting, keyed by the real
// plugin id. That object is NOT part of the documented plugin API; it reaches
// plugins only because the server copies its own state into each plugin's
// `app`. If a server release stops sharing it, this plugin must go inert
// rather than guess — hence the hard checks in start() and tick().
//
// v1 is notify-only by design. Restarting the offending plugin is a separate
// decision with no clean mechanism today (the only external restart path is
// the admin-credentialed HTTP config endpoint).

const fs = require('fs')
const path = require('path')

const NOTIFICATION_PREFIX = 'notifications.pluginWatchdog.'

module.exports = function (app) {
  const plugin = {
    id: 'plugin-watchdog',
    name: 'Plugin Watchdog',
    description:
      'Raises a notification when an enabled plugin publishes no deltas (never, or no longer)'
  }

  let timer = null
  let startedAt = null
  let lastCounts = {} // pluginId -> last observed deltaCount
  let lastChangeAt = {} // pluginId -> ms timestamp the count last increased
  let alarmed = {} // pluginId -> true while an alert notification stands
  let knownProducers = {} // pluginId -> ISO timestamp first seen producing (persisted)

  plugin.schema = {
    type: 'object',
    properties: {
      checkIntervalSeconds: {
        type: 'number',
        title: 'Check interval (seconds)',
        default: 30
      },
      graceSeconds: {
        type: 'number',
        title:
          'Startup grace period (seconds) before "never published" can fire. Cover the slowest plugin\'s first publish — BLE first polls can take minutes.',
        default: 300
      },
      stallSeconds: {
        type: 'number',
        title:
          'Stall threshold (seconds): alert when a watched plugin that has published this boot goes this long without a new delta. 0 disables stall detection.',
        default: 900
      },
      expectPlugins: {
        type: 'array',
        title:
          'Plugin ids always expected to publish (watched even before they are ever seen producing)',
        items: { type: 'string' },
        default: []
      },
      excludePlugins: {
        type: 'array',
        title: 'Plugin ids never to watch',
        items: { type: 'string' },
        default: []
      }
    }
  }

  function stateFile() {
    return path.join(app.getDataDirPath(), 'known-producers.json')
  }

  function loadState() {
    try {
      knownProducers = JSON.parse(fs.readFileSync(stateFile(), 'utf8'))
      if (typeof knownProducers !== 'object' || knownProducers === null) {
        knownProducers = {}
      }
    } catch {
      knownProducers = {}
    }
  }

  function saveState() {
    try {
      fs.mkdirSync(app.getDataDirPath(), { recursive: true })
      fs.writeFileSync(stateFile(), JSON.stringify(knownProducers, null, 2))
    } catch (err) {
      app.error('could not persist known-producers state: ' + err)
    }
  }

  function notify(pluginId, state, message) {
    app.handleMessage(plugin.id, {
      updates: [
        {
          values: [
            {
              path: NOTIFICATION_PREFIX + pluginId,
              value: {
                state,
                method: state === 'normal' ? [] : ['visual', 'sound'],
                message
              }
            }
          ]
        }
      ]
    })
  }

  // Enumerating enabled plugins from inside a plugin is harder than it
  // should be: `app.getPluginsList` exists on the server's real app object,
  // but interfaces get a Proxy over a key-snapshot taken before it is
  // assigned, so plugins never see it (verified against signalk-server
  // 2.31.0 and master). Fall back to the on-disk plugin config files —
  // `<configPath>/plugin-config-data/<id>.json` with an `enabled` flag —
  // which is the same source of truth the server itself reads.
  async function enabledPluginIds() {
    if (typeof app.getPluginsList === 'function') {
      const list = await app.getPluginsList(true)
      return list.map((p) => p.id)
    }
    const dir = path.join(app.config.configPath, 'plugin-config-data')
    return fs
      .readdirSync(dir)
      .filter((f) => f.endsWith('.json'))
      .filter((f) => {
        try {
          return (
            JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8')).enabled ===
            true
          )
        } catch {
          return false
        }
      })
      .map((f) => f.slice(0, -'.json'.length))
  }

  async function tick(opts) {
    // The whole design rests on state the server does not promise to share.
    // If the hook is gone, say so and do nothing — a supervisor that
    // guesses is worse than none.
    const stats = app.providerStatistics
    if (!stats || typeof stats !== 'object') {
      app.setPluginError(
        'app.providerStatistics not available; watchdog inactive'
      )
      return
    }

    let enabledList
    try {
      enabledList = await enabledPluginIds()
    } catch (err) {
      app.error('could not enumerate enabled plugins, skipping this check: ' + err)
      return
    }

    const excluded = new Set(opts.excludePlugins)
    const expected = new Set(opts.expectPlugins)
    const now = Date.now()

    const enabledIds = new Set(
      enabledList.filter((id) => id !== plugin.id && !excluded.has(id))
    )

    // Observe counts and learn producers before judging anyone.
    for (const id of enabledIds) {
      const count = stats[id] ? stats[id].deltaCount : 0
      if (!(id in lastCounts) || count > lastCounts[id]) {
        lastCounts[id] = count
        if (count > 0) {
          lastChangeAt[id] = now
        }
      }
      if (count > 0 && !knownProducers[id]) {
        knownProducers[id] = new Date().toISOString()
        saveState()
      }
    }

    for (const id of enabledIds) {
      // Only judge plugins we have grounds to expect deltas from: seen
      // producing before (any boot), or explicitly configured. Everything
      // else — webapps, pure consumers like a database writer — is silent
      // legitimately and forever.
      if (!expected.has(id) && !knownProducers[id]) {
        continue
      }

      const count = stats[id] ? stats[id].deltaCount : 0
      let problem = null
      if (count === 0) {
        if (now - startedAt > opts.graceSeconds * 1000) {
          problem = `enabled but has published no deltas since startup (grace ${opts.graceSeconds}s exceeded)`
        }
      } else if (
        opts.stallSeconds > 0 &&
        lastChangeAt[id] &&
        now - lastChangeAt[id] > opts.stallSeconds * 1000
      ) {
        const quiet = Math.round((now - lastChangeAt[id]) / 1000)
        problem = `stopped publishing: no deltas for ${quiet}s (threshold ${opts.stallSeconds}s)`
      }

      if (problem && !alarmed[id]) {
        alarmed[id] = true
        notify(id, 'alert', `Plugin ${id} ${problem}`)
        app.error(`ALERT: plugin ${id} ${problem}`)
      } else if (!problem && alarmed[id]) {
        delete alarmed[id]
        notify(id, 'normal', `Plugin ${id} is publishing again`)
      }
    }

    // A plugin someone disabled is not a failure; retract its alarm.
    for (const id of Object.keys(alarmed)) {
      if (!enabledIds.has(id)) {
        delete alarmed[id]
        notify(id, 'normal', `Plugin ${id} was disabled; alarm withdrawn`)
      }
    }

    const watchedCount = [...enabledIds].filter(
      (id) => expected.has(id) || knownProducers[id]
    ).length
    const alarmCount = Object.keys(alarmed).length
    app.setPluginStatus(
      `watching ${watchedCount} of ${enabledIds.size} enabled plugins` +
        (alarmCount ? `; ${alarmCount} ALARMED` : '')
    )
  }

  plugin.start = function (options) {
    const opts = Object.assign(
      {
        checkIntervalSeconds: 30,
        graceSeconds: 300,
        stallSeconds: 900,
        expectPlugins: [],
        excludePlugins: []
      },
      options || {}
    )
    opts.checkIntervalSeconds = Math.max(5, Number(opts.checkIntervalSeconds))

    startedAt = Date.now()
    lastCounts = {}
    lastChangeAt = {}
    alarmed = {}

    if (
      !app.providerStatistics ||
      typeof app.providerStatistics !== 'object'
    ) {
      app.setPluginError(
        'This server does not expose providerStatistics to plugins; watchdog inactive'
      )
      return
    }

    loadState()

    timer = setInterval(() => {
      tick(opts).catch((err) => app.error('watchdog check failed: ' + err))
    }, opts.checkIntervalSeconds * 1000)
    app.setPluginStatus('started; first check in ' + opts.checkIntervalSeconds + 's')
  }

  plugin.stop = function () {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  return plugin
}
