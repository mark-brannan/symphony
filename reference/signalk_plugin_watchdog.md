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
- No staleness, liveness, or plugin-supervision plugin exists in the registry.
  Searched npm for watchdog, health, stale, and monitor against `signalk`.
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

## The crux to settle first

Can a plugin map an observed `$source` back to the plugin that produced it?

`app.handleMessage(pluginId, delta)` means the **server** knows. Whether that
association is visible from another plugin is the open question, and the whole
design rests on it. Settle it before writing anything else.

If it isn't exposed, the fallbacks get worse fast: match on `$source` label
conventions (fragile), require configuration (the thing we're trying to avoid),
or push the feature into the server core instead of a plugin — which may be the
honest answer.

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
