// Reproduces the bt-sensors failure shape: the plugin starts cleanly, its
// external dependency is already dead, it never retries and never publishes.
// From the server's point of view it is enabled, loaded, and error-free.
module.exports = function (app) {
  return {
    id: 'mute-plugin',
    name: 'Mute fixture',
    description: 'Starts fine, publishes nothing, forever',
    schema: {},
    start: function () {
      app.setPluginStatus('started (and will now say nothing, by design)')
    },
    stop: function () {}
  }
}
