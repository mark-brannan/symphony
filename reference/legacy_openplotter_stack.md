# The legacy OpenPlotter stack aboard Symphony

Survey of the baremetal install running on the boat computer, taken 2026-08-11,
recorded so the Docker-based golden config in this repo can be reconciled
against what is actually aboard. Everything below was read off the running
system, not inferred.

This describes the system we are migrating *from*. It will stop being true at
cutover.

## Host

Raspberry Pi 4 Model B Rev 1.5, Debian 12 (bookworm), kernel 6.12.96 aarch64,
hostname `signalk`. No Docker installed.

Three active interfaces, which is why the box answers on more than one address:

- `eth0` — 192.168.8.240
- `wlan0` — 192.168.8.241
- `wlan9` — 10.42.0.1, serving an access point with `dnsmasq` bound to :53

mDNS advertises `signalk.local` and `_signalk-http._tcp`. Which address
`signalk.local` resolves to depends on which interface the client sees first —
both eth0 and wlan0 answer. The DHCP reservation and A record called for in
`SSO-SETUP.md` need to pick one deliberately.

Resources are the binding constraint: 3.7 GiB RAM total with roughly 800 MiB
available under normal load, and a 29 GB SD card. Observed load average around
9. `du` over the whole root filesystem does not complete in five minutes.

## Services

Run by systemd, not containers.

| Service | Port | Notes |
|---|---|---|
| `signalk.service` | 3000 | signalk-server 2.14.4, also 10110 (NMEA 0183 TCP) and 8375 |
| `influxdb.service` | 8086 | InfluxDB **2.8.0** OSS |
| `grafana-server.service` | 3001 | Grafana 13.1.1 |
| `pypilot` | 8000, 20220, 23322 | autopilot |
| `gpsd` | 2947 (localhost) | |
| `pigpiod`, `cupsd`, `librespot`, `avahi-daemon` | | |

The SignalK-on-3000 / Grafana-on-3001 split here is the layout adopted for the
golden config on 2026-08-11, reversing what `docker-compose.yml` previously
specified.

## InfluxDB

Version 2.8.0 — the org/bucket model, not 1.x. This matters: the repo targets
2.7, so aligning is a version bump rather than a data-model migration.

- Org `symphony`, id `e10d24946f714964`. The repo's `provision_influxdb.sh`
  uses org `darkstarllc` instead.
- Bucket `symphony`, id `70ce94895bf27f4d`, retention **720h (30 days)**,
  shard group duration 168h. The repo disagrees with itself here: `.env.j2`
  sets `DOCKER_INFLUXDB_INIT_RETENTION=30d` while `provision_influxdb.sh` posts
  `retentionPeriodSeconds: 0` (infinite). The boat's 720h matches `.env.j2`.
- System buckets `_monitoring` (168h) and `_tasks` (72h).
- One user: `captain`.
- Two all-access tokens: `captain's Token` and an onboarding CLI wizard token.
  Neither carries `read:authorizations`, so **`influx backup` fails with 401**
  against them. A full backup needs an operator token.

### InfluxQL still works, via virtual DBRP

InfluxDB 2.x exposes the 1.x `/query` endpoint through DBRP mappings. Symphony
has no explicit mappings, but the *virtual* read-only ones are present and
sufficient: database `symphony` → bucket `symphony`, retention policy `autogen`,
marked default. This is what lets a Grafana datasource in InfluxQL mode work
without any extra configuration.

### Schema

The `signalk-to-influxdb2` plugin writes SignalK paths as measurement names, so
the measurement list is effectively the vessel's path tree. There are **1268**
measurements in the `symphony` bucket, by top-level namespace:

| Namespace | Measurements |
|---|---|
| `observations` | 579 |
| `environment` | 268 |
| `vhfdata` | 99 |
| `notifications` | 90 |
| `electrical` | 41 |
| `pointsOfInterest` | 39 |
| `host` | 11 |
| `navigation` | 7 |
| `validation`, `steering`, `sensors`, `wind`, `weather` | 1–3 each |

### The writer

`signalk-to-influxdb2` is enabled and is the live path. Its configuration
differs from the repo's committed copy in two ways: it targets org `symphony`
rather than `darkstarllc`, and it sets `onlySelf: false` where the repo sets
`true` — so the boat records data for vessels other than Symphony.

Two other writers are installed but disabled: `signalk-to-influxdb` (the 1.x
plugin) and `signalk-to-influxdb-v2-buffer`.

## Grafana

Grafana 13.1.1, SQLite backend at `/var/lib/grafana/grafana.db`. `sqlite3` is
not installed on the Pi; read the database with Python's built-in `sqlite3`
module against a `file:...?mode=ro` URI.

- One user, `admin`. No OIDC, no Dex.
- **Zero alert rules and zero annotations.** There are no monitors or reports
  aboard to migrate — dashboards are the entire payload.
- One datasource, name `influxdb`, uid `ee2ppw626cqo0a`, pointed at
  `http://localhost:8086` in **InfluxQL** mode with `dbName: symphony`. The
  repo's provisioned datasource is Flux against org `darkstarllc`.

### Five dashboards, and the dangling datasource

No folders; five dashboards totalling 76 panels — Electricity (19), Navstation
under way (22), Navigation (12), Life support (12), Weather (11). Queries are
InfluxQL throughout, apart from a few Flux panels in Life support.

Of the 162 panel-level datasource references, **158 pointed at uid `eWjoLxAnk`,
which does not exist on this Grafana**; only 4 pointed at the real
`ee2ppw626cqo0a`. The dashboards were imported from published examples and the
datasource uid was never remapped.

The copies committed under `grafana/provisioning/dashboards/json/` have all 162
references rewritten to a single stable uid, `influxdb-symphony`. For them to
resolve, the provisioned datasource must declare `uid: influxdb-symphony` — and
because the queries are InfluxQL, that datasource must be in InfluxQL mode.
Pointing them at the repo's current Flux datasource will not work.

## Traps

**`signalk.local` does not resolve on the box itself.** The influx CLI config
and the `signalk-to-influxdb2` plugin config both use
`http://signalk.local:8086`. Node resolves this through NSS and mDNS and works;
Go binaries including the `influx` CLI bypass NSS, ask the router at
192.168.8.1, and fail with `no such host`. Pass
`--host http://localhost:8086` to any `influx` command.

**Disk fills with cache, not data.** On 2026-08-11 the root filesystem was 89%
full. InfluxDB accounted for 308 MB and SignalK's raw logs for 1.2 MB. The
space was in `/var/cache/apt` (2.4 GB), `/home/pi/.npm` (2.2 GB) and journald
(2.0 GB). `apt clean` plus `journalctl --vacuum-size=200M` recovered 4.3 GB and
took the filesystem to 72%.
