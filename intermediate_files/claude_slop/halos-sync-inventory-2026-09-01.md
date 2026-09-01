# Symphony golden-state inventory — 2026-09-01

Read-only snapshot of the boat Pi (`symphony-pi`), taken to seed the
halos-sync plan. Facts only. No credentials here — those live in sops /
the sensitive lane. This file is input for the planning session.

## Host

| Field | Value |
|---|---|
| Model | Raspberry Pi 4 Model B rev 1.5, 4 GB RAM |
| Storage | 32 GB SD card (29 GB usable, 76% full, ~6.7 GB free) |
| OS | Debian 12 (bookworm), kernel 6.12.96 aarch64 |
| Hostname | `signalk` |
| Tailscale | node `symphony-pi` |
| Network | ethernet `eth0` and wifi `wlan0` both up; own AP hotspot on `wlan9` (SSID `SignalK`) |
| Load at snapshot | ~11 (another session was running bt-sensors work; not normal idle) |

## Containers running now (3)

| Name | Image | Bind | Purpose |
|---|---|---|---|
| `questdb` | questdb/questdb | 127.0.0.1:8812/9000/9009 | time-series history store. **Already up 11 days** |
| `dex` | dexidp/dex:v2.45.1 | 127.0.0.1:5556 | OIDC identity broker for SSO (Google/GitHub upstream) |
| `ntfy` | binwiederhier/ntfy | 0.0.0.0:8090→80 | push-notification bus |

No stopped containers.

## Systemd services

| Service | Active | Enabled | Note |
|---|---|---|---|
| signalk | yes | yes | the core |
| telegraf | yes | yes | host metrics → QuestDB (ILP) |
| caddy | yes | yes | TLS front door |
| pypilot | yes | yes | autopilot |
| chrony | yes | yes | clock |
| gpsd | yes | no | GNSS actually arrives over N2K, not serial |
| influxdb | yes | **disabled** | mid-retirement: runs now, won't survive reboot |
| grafana-server | **failed** | disabled | native Grafana is down, not deliberately stopped |
| dex | n/a | n/a | runs as the container above, not a host unit |

## Key finding: DB migration already happened on the boat

QuestDB is a running container (11 days). InfluxDB is `active/disabled`.
The documented "Track B" QuestDB migration is largely **done on the boat**,
not aspirational. Grafana-server (native) is `failed`. Verify which history
plugin SignalK writes to (influxdb2 vs questdb-history-provider) and whether
any Grafana serves QuestDB — the container Grafana may be the intended one.

## SignalK plugins (~90 installed)

### Must retain (owner's core list) — all present

| Capability | Plugin(s) | State |
|---|---|---|
| Bluetooth batteries | `bt-sensors-plugin-sk` | enabled (a `.1786080342` backup config also present) |
| | `signalk-bluetooth-scanner`, `signalk-victron-ble` | installed |
| Victron data | `signalk-venus-plugin` (config `venus.json`) | enabled |
| Pushover / notifications | `signalk-push-notifications`, `signalk-ntfy`, `signalk-notification-player` | enabled |
| Watchdog | `signalk-plugin-watchdog` (config `plugin-watchdog.json`) | enabled |
| Healthchecks.io | `signalk-healthcheck` | **DISABLED** (`.bak-preretire`) — confirm how healthchecks.io is actually pinged (watchdog? cron? external) |

### Notably disabled

ais-forwarder, noaa-observations, signalk-activecaptain (+resources),
signalk-fixedstation, signalk-gpio-beeper, signalk-healthcheck,
signalk-n2k-switching, signalk-noaa-weather, signalk-rpi-uptime,
signalk-solar-forecast, signalk-tide-watch, tides, tides-api.

## Drivers / buses (PiCAN-M)

| Bus | State |
|---|---|
| NMEA 2000 | `can0` UP, ERROR-ACTIVE (healthy), mtu 16 |
| NMEA 0183 | `/dev/serial0` → `ttyS0` present (root:dialout) |
| SignalK providers | types `NMEA2000`, `canbus-canboatjs`, `providers/simple` |

GNSS arrives over the N2K bus (see `compute_hardware.md`), not a serial GPS.

## Victron / Cerbo GX (out of scope, must keep working)

A separate Victron Cerbo GX runs its own installation on the boat, visible in
Victron VRM cloud. Never documented in this repo. Independent of the Pi swap;
must be left untouched. `signalk-venus-plugin` on the Pi is the SignalK-side
view; the Cerbo itself is not ours to change.

## halos side

Spare Pi 4 at home, `halos.local` = 192.168.0.193 (WSL cannot resolve the
`.local` name; use the IP). Tailscale peer `halos-pi4`, tailnet IP
`100.120.50.62`. Key-based SSH confirmed working: `ssh pi@192.168.0.193`.

Confirmed on login (2026-09-01):

| Field | Value |
|---|---|
| Hostname | `halos` |
| OS | **Debian 13 (trixie)** — matches HALOS's supported APT-layer base |
| `docker ps` | **empty** — HALOS app containers not running (or docker needs sudo). Verify first. |

Runs HALOS (Raspberry Pi OS / Debian base + Docker app packages, Traefik +
Authelia SSO). Full app-level triage is the planning session's job.
