// Publishes a temperature every 2 seconds unless the marker file named by
// $FLAKY_MUTE_MARKER exists. The marker is checked on every tick, so a test
// can mute and un-mute this plugin while the server runs.
const fs = require('fs')
const os = require('os')
const path = require('path')

module.exports = function (app) {
  let timer = null
  const marker =
    process.env.FLAKY_MUTE_MARKER ||
    path.join(os.tmpdir(), 'flaky-mute-marker')

  return {
    id: 'flaky-plugin',
    name: 'Flaky fixture',
    description: 'Publishes unless the mute marker file exists',
    schema: {},
    start: function () {
      timer = setInterval(() => {
        if (fs.existsSync(marker)) {
          return
        }
        app.handleMessage('flaky-plugin', {
          updates: [
            {
              values: [
                {
                  path: 'environment.inside.temperature',
                  value: 293.15 + Math.sin(Date.now() / 10000)
                }
              ]
            }
          ]
        })
      }, 2000)
      app.setPluginStatus('publishing every 2s unless muted via ' + marker)
    },
    stop: function () {
      if (timer) {
        clearInterval(timer)
        timer = null
      }
    }
  }
}
