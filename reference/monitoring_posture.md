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

Installed and enabled on the boat. Both `sendNotification` and `sendEmail` are
`false`, so it raises nothing and sends nothing.

Its host section duplicates thresholds the heartbeat already alarms on. Its
provider section is the exception: it reads `pipedProviders` from the server
settings and watches each one's delta rate, which is the only mechanism aboard
that alarms on data *stopping*. The boat has one provider, `n2k-can0`, and the
watch for it is disabled.

It watches providers, not plugins. A plugin that loads and goes mute is a
different failure and is covered by nothing — see
[`signalk_plugin_watchdog.md`](signalk_plugin_watchdog.md).

## Gaps

**The heartbeat collects nine vitals and can alarm on two.** Uptime, load,
temperature, throttling, clock offset and failed systemd units all travel in the
ping body every five minutes; only memory and disk can trip `/fail`. A failed
`signalk.service` reaches the crew only if someone opens a ping and reads it.

**Nothing alarms on data stopping.** Zones cannot express it, the one provider
watch is disabled, and no plugin covers plugin-level staleness.

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
