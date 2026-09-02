# Why the plugin watchdog exists

The plugin now exists at `plugins/signalk-plugin-watchdog` (notify-only,
deployed 2026-08-15). This file records the failure that motivated it and
what was learned building it; the plugin's own README documents how it
works, and [monitoring_decisions.md](monitoring_decisions.md) Role 4 places
it in the monitoring plan. A draft community post about the failure is at
`plugins/signalk-plugin-watchdog/DRAFT-POST.md`. Everything under "What we
found" was measured on Symphony on 2026-08-13/14.

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
So the gap is real, and the missing piece is a supervisor, not a new
mechanism. Detection turned out to be available without the `$source`-to-plugin
mapping the design assumed it needed — `app.providerStatistics` counts deltas
per plugin id directly. Restart did not: it is admin-authenticated and has no
plugin-facing API, which is why the shipped plugin is notify-only. Both
findings, with sources, are in monitoring_decisions.md Role 4.

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
