# A watchdog for SignalK plugins that go mute

Design brief for a plugin that doesn't exist yet. Everything under "What we
found" was measured on Symphony on 2026-08-13/14; everything under "Sketch" is
proposal and hasn't been built or tested.

## The failure

A SignalK plugin can be enabled, loaded, free of errors in the log, and
publishing nothing — and nothing in SignalK notices.

What happened here: `bt-sensors-plugin-sk` opens a D-Bus connection to
`org.bluez` as it loads. On some starts the handshake dies with `write EPIPE`
and the plugin never retries. Both house batteries went silent for the life of
that process. The server was healthy, the plugin was listed as enabled, the
admin UI showed nothing wrong, and the only symptom was an absence — no data
under `electrical.batteries.*`.

This is not BLE-specific. Any plugin whose external dependency dies after load
fails the same way: serial, network, MQTT, a cloud API. The plugin is up; its
supply is gone; nobody is watching the difference.

It matters most when nobody is aboard. The hardware watchdog reboots this box
on a hang, so an unattended reboot could bring everything back *except* the
battery monitoring, indefinitely.

## What we found (verified)

Nothing in the ecosystem covers this.

- `signalk-healthcheck` watches **providers** — the server's data connections —
  and raises notifications. It does not watch plugins, cannot see a plugin that
  loaded and went mute, and never acts.
- `signalk-performance-monitor` does event-loop metrics and profiling. Unrelated.
- No plugin-supervision plugin exists in the registry. One path-staleness
  plugin does: `signalk-data-age-watchdog` (a keyword sweep on 2026-08-14
  found it after the original text searches missed it — see
  [monitoring_decisions.md](monitoring_decisions.md), Role 4, for how it
  fits the boat's monitoring plan). Read in source: it watches a
  hand-configured path list against one global age threshold, and skips any
  path with no timestamp in the tree — so it cannot detect a plugin that is
  mute from startup, which is the failure above. Supervision, learned
  cadence, and never-published detection remain uncovered.
- The server core *does* have `stopPlugin` / `restartPlugin` internally
  (`dist/interfaces/plugins.js`). The recovery mechanism exists. Nothing drives
  it.

So the gap is real, and the missing piece is a supervisor, not a new mechanism.

## Sketch (proposal, untested)

A plugin. Notify by default; restart opt-in.

**Learn, don't configure.** Watch the delta stream and record which sources each
plugin produces and how often. No per-plugin setup to maintain, and it stays
correct when someone renames a sensor — which matters, because the obvious
alternative (a hand-written list of expected paths) goes stale silently and
becomes another thing that looks configured but isn't.

**Judge staleness relative to learned cadence.** A 60-second BMS poll and a 1 Hz
GPS cannot share a fixed threshold. Also catch "enabled but never published at
all", which is the case we actually hit — there is no prior cadence to compare
against, so absence has to be first-class rather than an edge case.

**Act in a ladder.** Raise a SignalK notification first, so existing alarm paths,
dashboards and any off-boat alerting pick it up for free. Then, only if enabled,
restart that one plugin through the core API — no service bounce, no collateral.
Attempt budget and backoff, and stop rather than loop.

**Refuse to act when it can't tell.** Startup, a server that just restarted, or
an unreadable state should all mean "do nothing". A supervisor that guesses is
worse than none.

## The crux, settled (2026-08-15, read against signalk-server master)

Can a plugin map an observed `$source` back to the plugin that produced it?
**No — and it turns out not to matter.**

- `handleMessage` only falls back to the plugin id when an update carries no
  source of its own. A plugin that sets `source.label` or `$source` directly
  wins, and the server records no pluginId→sourceRef association anywhere.
  Measured aboard: 13 of 37 live sources match no plugin id, four of them
  bt-sensors' (`House Battery 1`, …) — the plugin that motivated this design
  is exactly the one label-matching fails on. `$source` conventions are not a
  fragile fallback; they are no fallback at all.
- The mapping isn't needed. `incDeltaStatistics(app, providerId)` runs on
  every `handleMessage` call, before any source rewriting, maintaining
  `app.providerStatistics[pluginId]` — delta count and rate per true plugin
  id, recomputed every 5 s, on every 2.x server as shipped. A count of zero
  *is* the enabled-but-never-published case, first-class. This replaces the
  sketch's "learn which sources each plugin produces" machinery entirely.
- The catch: `providerStatistics` is not in the `ServerAPI` type. Plugins
  can read it only because `doRegisterPlugin` shallow-copies the whole app
  object. Works everywhere, promised nowhere.
- Restart has no supported in-process path. `stopPlugin`/`doPluginStart`
  exist in core but aren't exposed to plugins; calling
  `pluginsMap[id].stop()` directly skips the `onStopHandlers` teardown and
  leaks registrations. The only correct route today is what the admin UI
  itself does — `POST /plugins/<id>/config` — which needs credentials.
- Core is moving under the staleness half: master has an unreleased
  enforcer (#2689, merged 2026-07-11, missed v2.30.0) that learns per-path
  cadence and emits `state.timedOut` per path+source. It walks the delta
  cache, so never-published paths are invisible to it too — plugin-level
  supervision stays uncovered.

Plan settled with the owner 2026-08-15: build the plugin on
`providerStatistics`, notify-only in v1, community-facing; propose two small
core PRs — `providerStatistics` added to `ServerAPI`, and a supported
`restartPlugin(id)` — rather than pushing the whole supervisor into core.
Restart automation waits on that PR (or ships later reading credentials,
decided then). Publishable account:
[watchdog_writeup_draft.md](watchdog_writeup_draft.md).

## Our stopgap, and why it isn't the answer

`host/signalk-ble-check` plus its systemd timer does this for one plugin on one
boat: every 15 minutes it asks SignalK what it is serving, and if bt-sensors is
enabled with peripherals configured to publish and none appear as a source, it
restarts SignalK.

It works and it is tested, but note what it costs. It restarts the **whole
server** because a plugin lost a socket. It knows about one plugin. It lives in
systemd rather than SignalK, so it is invisible to anyone administering the
boat through the UI. That's the argument for building the real thing.

Two bugs found while testing it are worth carrying forward, because both made
the check silently incapable of firing and neither was visible without
exercising the action path:

- The verdict came from Python's exit status while the shell read stdout, and a
  `|| echo 99` fallback folded the meaningful code into "could not tell".
- The install-in-flight guard used `pgrep -f`, which matches whole command
  lines and so matched the script's own ancestors.

Test the failure path, not just the healthy one. A watchdog that never fires
looks exactly like a watchdog with nothing to do.
