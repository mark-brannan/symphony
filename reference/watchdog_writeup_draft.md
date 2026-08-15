# Your SignalK plugin can die and nothing will tell you

Draft of a community post. Not published. Facts below were measured on
Symphony (Hans Christian 38T, Raspberry Pi 4, SignalK 2.x) on 2026-08-13/14;
source references are against signalk-server master at f2bedbf0.

---

Last week both of my house battery monitors went silent and SignalK didn't
notice. Neither did I, for a while.

The plugin was `bt-sensors-plugin-sk`, which reads BLE battery sensors. When
it loads, it opens a D-Bus connection to BlueZ. On some starts that handshake
dies with `write EPIPE`, and the plugin doesn't retry. It stays loaded. It's
listed as enabled. The admin UI shows nothing wrong, the log shows one line
that scrolled away hours ago, and everything under `electrical.batteries.*`
just stops. The only symptom is an absence.

Nothing about this is BLE-specific. Any plugin that talks to something
external — a serial port, a socket, MQTT, a cloud API — fails the same way
when its connection dies after startup. The plugin is up; its supply is gone;
no part of the system is watching the difference.

It matters most when nobody's aboard. My Pi has a hardware watchdog that
reboots it if it hangs, which means an unattended reboot can bring back
everything *except* the battery monitoring, indefinitely, while the boat sits
on anchor telling me nothing is wrong because nothing is being said at all.

## Almost nobody covers this

I went looking for the thing that should have caught it.

- `signalk-healthcheck` watches providers — the server's data connections.
  It can't see a plugin that loaded and went mute, and it never acts.
- `signalk-performance-monitor` does event-loop metrics. Different problem.
- `signalk-data-age-watchdog` is the closest: give it a list of paths and a
  max age, and it alarms when data on those paths gets old. Genuinely
  useful — but it reads each path's timestamp from the data tree, and a
  path that has *never* published has no timestamp, so it's silently
  skipped. After a reboot, `electrical.batteries.*` doesn't exist until the
  plugin publishes it. My failure was mute-from-startup: exactly the case a
  timestamp check can't see. It also can't know a path is missing from its
  hand-written list, which is how staleness checks rot when you rename a
  sensor.
- Beyond that, I swept all 559 packages carrying the
  `signalk-node-server-plugin` keyword. No plugin supervises other plugins.

The distinction matters more than it looks: watching *data* can only judge
data that has appeared. Watching *plugins* is the only way to catch "enabled,
loaded, and never said a word" — and nothing does that.

So I sketched one: watch the delta stream, learn which sources each plugin
produces and how often, alarm when one goes quiet. The design hinged on one
question — can a plugin map an observed `$source` back to the plugin that
produced it?

## The answer is no, and it's worth knowing why

When a plugin calls `app.handleMessage(pluginId, delta)`, the server knows
exactly who's talking. But it only uses that identity as the `$source` when
the plugin doesn't supply its own — and plugins supply their own all the
time. `bt-sensors` publishes as `House Battery 1`, not as
`bt-sensors-plugin-sk`. On my boat, 13 of 37 sources don't match any plugin
id. The association exists for one moment inside `handleMessage` and is then
thrown away; nothing downstream records it.

So "learn the sources, match them to plugins" doesn't work, and label
conventions are a coin flip. I was about to conclude the whole idea needed a
core change. Then I found the counter the server has been keeping all along.

## The server already knows. Nobody acts on it.

Every call to `handleMessage` increments a per-plugin delta counter *before*
any source rewriting happens. It's keyed by plugin id — the real one. The
server recomputes rates every five seconds and shows them in the admin
dashboard, where they've been for years.

Which means the detection problem is already solved, in core, on every
SignalK server running today. A plugin that's enabled and has produced zero
deltas is precisely the failure I hit, and it's one integer comparison away
from an alarm. The sensing exists; the acting doesn't. Nobody watches a
dashboard from offshore.

Two catches. First, `providerStatistics` isn't part of the documented plugin
API — a plugin can reach it today, but by accident of how the server shares
its state, not by contract. Second, there's no supported way for a plugin to
restart another plugin; the internal stop/start machinery exists but isn't
exposed, and the only clean route is the HTTP endpoint the admin UI uses,
which wants admin credentials.

Worth noting the maintainers are already circling this area: master has an
unreleased staleness enforcer (#2689) that learns per-path update cadence
and flags paths that go quiet. It watches data, not plugins, and it notifies
rather than acts — but it's clear evidence the problem is recognized.

## What I'm proposing

Three small things, not one big one:

1. **Core PR: make `providerStatistics` an official part of the plugin API.**
   It's a read of state the server already maintains and already displays.
2. **Core PR: a supported `restartPlugin(id)`** that routes through the
   existing stop/start path, so a supervisor — or anything else — can bounce
   one plugin without bouncing the server.
3. **A watchdog plugin, notify-only in v1.** Enabled plugin, zero or stalled
   delta count, sustained past a grace period → SignalK notification, so your
   existing alarm paths pick it up for free. Restart can come later, through
   (2), once it exists.

If you've hit this failure — a plugin that was "running" while publishing
nothing — I'd like to hear what it was, because a supervisor is only as good
as the failure modes it's tested against. Mine came within one bad D-Bus
handshake of an anchor watch with no battery data. That was enough for me.
