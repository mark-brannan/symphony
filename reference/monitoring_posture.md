# What monitors Symphony, and what can actually raise an alarm

Measured on the boat Pi and the dev container on 2026-08-14. Three monitoring
stacks run aboard. They share no wiring, and the useful question about each is
not what it collects but what it can make happen when something is wrong.

## The three stacks

| Stack | Alarms on | Reaches the crew via | Runs where |
|---|---|---|---|
| `host/boat-heartbeat` → external check service | ping silence; memory available < 400 MB; disk ≥ 90% | email, pushover, discord, SMS — whatever the check service fans out to | Pi, systemd timer, every ~5 min |
| SignalK notification bus | anything that raises a notification into it | `signalk-notification-player` (audio aboard), `signalk-push-notifications` (phone push, remote push enabled) | Pi, inside `signalk-server` |
| Telegraf → InfluxDB → Grafana | nothing | nothing | Pi |

The third stack has the richest data and no path to a human. No alert rules are
provisioned — `/etc/grafana/provisioning/alerting/` holds only Debian's
`sample.yaml`.

## What raises notifications today

21 notifications were live on the bus when measured. Their sources:

- `bt-sensors-plugin-sk`, publishing under per-sensor names — house battery
  protection status, SwitchBot fridge thermometer, Victron devices.
- `signalk-noaa-space-weather`, directly, under `noaa.swpc.*`.
- `self.notificationhandler` — the server core's zone engine, covering the 13
  space-weather paths that carry `meta.zones`.

None of the 21 concerns host health.

## Zones are a server feature, not a plugin

`signalk-server/dist/index.js:509` constructs `Zones` against the stream bundle
and feeds its output to `handleMessage('self.notificationhandler', delta)`. Any
path carrying `meta.zones` raises a notification when its value crosses a zone
boundary, with no plugin involved. `@signalk/zones` ("zones-edit") is the
editor UI for that metadata, not the mechanism.

No zones are configured outside space weather. Checked live on both the boat
and the dev container, 2026-08-15: `environment.inside.airquality` doesn't
exist anywhere in the vessel tree, on either box, so the zone this doc
previously described here was never actually live.

The recovered airquality bands now live as server-native meta in the repo's
`signalk/baseDeltas.json` (dev container config), on the corrected path —
dormant until something publishes there. The zone engine reads notification
methods from meta-level `alertMethod`/`emergencyMethod`/etc. arrays, not the
per-zone `method` fields the old plugin format used (`src/zones.ts` in
signalk-server: explicit `null` means no methods, undefined defaults to
visual); the migration maps them accordingly. The boat still has `@signalk/zones`
1.2.0 installed and enabled with its config never registering; the plugin is
deprecated upstream and superseded by this meta mechanism, so the remaining
move is removing it on the boat and mirroring the meta there, not debugging it.

The limit that matters: **zones fire on a value arriving out of range. They are
silent when values stop arriving.**

## Host metrics are collected three times

| Collector | Where it lands | Can alarm |
|---|---|---|
| Telegraf | InfluxDB | No |
| `signalk-rpi-monitor` | 5 SignalK paths under `environment.rpi.*` | Yes, via zones |
| `signalk-rpi-uptime` | 2 SignalK paths | Yes, via zones |

`signalk-rpi-stats` is enabled on the dev container only, where it publishes 29
paths covering the same ground.

`signalk-rpi-monitor` computes `environment.rpi.memory.utilisation` as
`(MemTotal − MemFree − Buffers − Cached − Slab) / MemTotal`. This is close to
but not the same as `MemAvailable`, so a threshold for it has to be derived from
that formula rather than copied from the heartbeat's 400 MB figure. Derived,
400 MB on the 3.9 GB Pi is a utilisation of roughly 0.89.

## signalk-healthcheck

**This plugin earns its place, and it is the only thing aboard that does what
it does.** Its two halves have opposite value, which is why its worth has read
as ambiguous:

- **Host section — redundant, and off.** CPU, memory and disk thresholds that
  `host/boat-heartbeat` already alarms on, from a process that dies with the
  Pi. Disabled (`host.enabled: false`) and should stay that way.
- **Provider section — unique, and live.** It reads `pipedProviders` from the
  server settings and watches each provider's delta rate, alarming when the
  rate falls to zero. **Nothing else aboard alarms on data stopping.** Zones
  fire on a value arriving out of range and are silent when values stop
  arriving; the plugin watchdog covers mute *plugins*, not mute *providers*.
  A dead NMEA 2000 bus — a failed drop cable, a powered-down MFD, a blown
  fuse on the backbone — is invisible to every other monitor here.

Measured on the boat 2026-09-04: `providers.n2k-can0` is `enabled: true` with
`sendNotification: true`, `deltaWarning: 1`, `deltaAlarm: 1`. It raises onto
the SignalK notification bus, which reaches the phone via
`signalk-push-notifications`. An earlier revision of this section recorded the
watch as disabled; that was true when measured on 2026-08-14 and is no longer.

Email is not wired and is not intended to be. `sendEmail` is `false` on both
sections, and the plugin's `mail` block carried a username and password but
no `host` or `port`, so `nodemailer` could not have connected had it ever been
called (`sendEmail()` is reached only from the two `sendEmail: true` paths).
The block was dead config and has been dropped from the tracked copy; if email
alerting is ever wanted, it needs a real SMTP endpoint chosen first, not that
block restored.

It watches providers, not plugins. A plugin that loads and goes mute is a
different failure, covered by `plugins/signalk-plugin-watchdog` — see
[`signalk_plugin_watchdog.md`](signalk_plugin_watchdog.md).

The config is tracked at `signalk/plugin-config-data/signalk-healthcheck.json`
and is the same on every host, with one legitimate difference: a dev box has
no CAN hardware, so `providers.n2k-can0.enabled` is `false` there or the check
sits in `alarm` forever.

## Gaps

**The heartbeat collects nine vitals and can alarm on two.** Uptime, load,
temperature, throttling, clock offset and failed systemd units all travel in the
ping body every five minutes; only memory and disk can trip `/fail`. A failed
`signalk.service` reaches the crew only if someone opens a ping and reads it.

**Data stopping is covered for providers only.** Zones cannot express it, so
the sole mechanism is `signalk-healthcheck`'s provider watch, live on
`n2k-can0` since 2026-09-04. It covers the one provider the boat has; a
provider added later is watched only if it is added to that plugin's config.

**Vessel alarms have one off-boat path.** Anchor drag or MOB reaches the phone
through `signalk-push-notifications` and nowhere else. The check service's
email/pushover/discord fan-out only ever hears from the heartbeat.

**Node-RED is enabled with no flows.** A routing engine is installed, running,
and doing nothing.

## Standing constraints for anything added here

- The Pi has 3.9 GB for everything and is already the subject of memory-pressure
  alarms. Anything resident on it pays rent in the resource being watched.
- Anything running on the Pi dies with the Pi. Off-boat alarming has to
  originate somewhere the Pi's failure cannot silence, which is why the
  heartbeat is a dead man's switch rather than an alerting agent.
- The uplink is intermittent by design. A missed transmission is the expected
  case, not a fault.
- The crew does not watch this system. It is passive from their point of view,
  which is the same reason nobody watches depth or battery — that is what the
  box is for.
