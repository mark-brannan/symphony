# System map: the boat card and the HALOS card

One boat Pi, two SD cards. The **boat card** is the working system. The
**HALOS card** is the trial system built at home to swap in. This page says
what runs where, what each piece is for, and what still has to be built.
Facts here were read off both cards on 2026-09-01 and from the HALOS source
repos; the swap procedure is in [RUNBOOK.md](../RUNBOOK.md) → "Swapping
the HALOS card onto the boat", and the build plan is in
`intermediate_files/claude_slop/halos-swap-plan.md`.

The Pi itself does not change. It keeps its MAC addresses, its DHCP
reservation on the boat router, and its PiCAN-M HAT. Only the card moves.

## The two cards

| | Boat card (golden) | HALOS card (trial) |
|---|---|---|
| OS | Debian 12 bookworm, OpenPlotter on bare metal | Debian 13 trixie + HALOS 0.3.7 apt packages |
| Hostname | `signalk` (mDNS `signalk.local`) | `halos` until the build renames it `signalk` |
| Tailnet name | `symphony-pi` (tag `symphony-devices`) | `halos-pi4` until renamed `symphony-halos` (tag `home-fleet`) |
| Card | 32 GB, ~6 GB free | 128 GB, ~97 GB free |
| SignalK | 2.31.1, native, `~/.signalk`, runs as `pi` | 2.31.1, container, `/var/lib/container-apps/marine-signalk-server-container/data/data`, runs as uid 1000 |
| Front door | Caddy (native), Let's Encrypt certs, one hostname per app | Traefik (container), self-signed device CA, one port per app |
| Login | Dex → GitHub or Google; local `captain` | Authelia local accounts; local `captain` after the state copy |
| History DB | QuestDB 10 container, localhost ports | QuestDB 10 container, same localhost ports |
| Grafana | none (purged 2026-08-25) | Grafana 13 container, QuestDB datasource provisioned |
| Host metrics | Telegraf → QuestDB | not installed yet |
| Off-boat heartbeat | `boat-heartbeat.timer` → healthchecks.io, Pushover on failure | not installed yet |
| Rollback | is the rollback | swap the boat card back |

## Core functions and how each card delivers them

| Function | Boat card | HALOS card | Trial status |
|---|---|---|---|
| Bluetooth batteries | `bt-sensors-plugin-sk`, Mark's fork at `/home/pi/bt-sensors-plugin-sk`, 5 peripherals | same fork, copied into the container's data dir; container has `/run/dbus` and host network | build item, test at the boat |
| Victron data | `signalk-venus-plugin` over MQTT-TLS to `venus.local` | same plugin; the container cannot resolve `.local` names, so the host must be the Cerbo's LAN IP | build item |
| Cerbo GX itself | separate device, VRM cloud, not managed here | untouched | no change |
| Pushover | `boat-heartbeat` escalates to Pushover when healthchecks.io pings fail | same script, same secrets file | build item |
| healthchecks.io | `boat-heartbeat.timer`, every 5 min. Not the `signalk-healthcheck` plugin | same timer | build item |
| ntfy (LAN push) | `ntfy` container on port 8090, `signalk-ntfy` plugin | same container from `compose-ntfy.yml` | build item |
| Plugin watchdog | `signalk-plugin-watchdog` from this repo, `file:` dependency | same plugin under `local-plugins/` in the data dir | build item |
| NMEA 2000 | `can0` via `mcp2515-can0` overlay, brought up by `/etc/network/interfaces` | overlay and bring-up missing | build item, verify only at the boat |
| NMEA 0183 | `/dev/serial0` via `enable_uart=1` | missing | build item |
| I2C / Qwiic | `/dev/i2c-1` via `dtparam=i2c_arm=on`; BME680 and `i2c-reader` plugins | missing | build item |
| Boat LAN | `eth0` DHCP (reserved .240), `wlan0` DHCP on `Symphony` (.241) | `eth0` DHCP ready; `Symphony` WiFi profile missing | build item (PSK from sops) |
| Hotspot | SSID `SignalK` on `wlan9`, 10.42.0.1 | SSID `Halos-A78D` on `wlan0ap`, 10.42.0.1 | build item: rename SSID, set PSK |
| Tailscale SSH | `ssh pi@symphony-pi` | `ssh pi@halos-pi4`, becomes `ssh pi@symphony-halos` | build item |
| Public URL | `https://signalk.<boat-domain>` → Caddy → SignalK | `https://signalk.<boat-domain>` → Traefik → dashboard; SignalK on `:4430` | cutover item |
| Autopilot | `pypilot` native | no package for it | **out of the trial**; swap back if needed |

## Containers

| Container | Card | Purpose | Reach it at | State on disk |
|---|---|---|---|---|
| `questdb` | both | time-series history for SignalK paths and host metrics | `127.0.0.1:9000` HTTP, `:9009` ILP, `:8812` Postgres wire | boat: volume `symphony_questdb-data` (1.8 GB); HALOS: `.../marine-questdb-container/data/db` |
| `ntfy` | boat, HALOS after build | push notifications to phones on the boat LAN | `0.0.0.0:8090` | volume `symphony_ntfy-data` |
| `dex` | boat only | OIDC broker: turns GitHub/Google login into one issuer for SignalK | `127.0.0.1:5556`, behind Caddy as `auth.<boat-domain>` | none, config from `dex/config.yaml` |
| `signalk-server` | HALOS | SignalK itself | host network, `:3000`; Traefik `:4430` | `.../marine-signalk-server-container/data/data` |
| `traefik` | HALOS | reverse proxy and TLS; `:80`, `:443`, one port per app from `/etc/halos/port-registry` | `:443` | `.../halos-core-containers/data/traefik` |
| `authelia` + `authelia-valkey` | HALOS | single sign-on: local user database, OIDC provider for SignalK and Grafana | `https://<host>/sso/` | `.../halos-core-containers/data/authelia` |
| `homarr` | HALOS | app dashboard at `/` | `:443` root | `.../halos-core-containers/data/homarr` |
| `ca-download` | HALOS | serves the device CA certificate so phones stop warning | `https://<host>/ca/` | none |
| `autoheal` | HALOS | restarts any container whose healthcheck fails | none | none |
| `grafana` | HALOS | dashboards on QuestDB | Traefik `:4433` | `.../marine-grafana-container/data/data` |
| `avnav`, `opencpn` | HALOS | chart plotters | `:4431`, `:4435` | own data dirs |
| `influxdb` (HALOS app) | HALOS | InfluxDB 2.9, **failed to start, to be removed** | `:4434` | own data dir |

Host ports on the HALOS card: SignalK 4430, AvNav 4431, QuestDB 4432,
Grafana 4433, InfluxDB 4434, OpenCPN 4435, Cockpit 9090.

## SSH connection strings

| Command | Host | Account | Use it for |
|---|---|---|---|
| `ssh pi@symphony-pi` | boat Pi over Tailscale, boat card | `pi`, has `sudo` and `docker` | everything on the boat card |
| `ssh pi@192.168.0.193` | spare Pi on the home LAN, HALOS card | `pi`, key login; `sudo` needs the password in sops key `symphony_halos_pi_password`; not in `docker` group | building the HALOS card at home |
| `ssh pi@halos-pi4` | same box over Tailscale SSH | `pi` | same, from any tailnet machine |
| `ssh pi@symphony-halos` | the HALOS card after the rename, at home or aboard | `pi` | the boat during the trial |
| `tmux attach -t claude` | after either ssh | | the resident Claude session (boat card only today) |
| `ssh pi@symphony-pi 'ssh root@192.168.8.1 ...'` | boat router via the boat Pi | `root` | router DNS override and DHCP reservations |

Docker on the HALOS card needs `sudo`. The `pi` user there has no
passwordless sudo, so scripts must pipe the sops password into `sudo -S`.

## Names and addresses

| Name | Answers with | Who answers |
|---|---|---|
| `<boat-domain>` (A record) | tailnet IP of the Pi aboard | Cloudflare; moved by `scripts/dns_cutover.sh` |
| `signalk.`, `grafana.`, `auth.<boat-domain>` | CNAME to the apex | Cloudflare |
| the same names on the boat LAN | `192.168.8.240` | boat router override, fixed to the Pi's MAC |
| `signalk.local` | LAN IP | mDNS from whichever card is running |
| `symphony-pi`, `symphony-halos` | tailnet IPs | Tailscale MagicDNS |
| `venus.local` | `192.168.8.107`, the Cerbo GX | mDNS; not visible inside the SignalK container |

The A record's TTL is 300 s. Off-boat devices see a cutover within five
minutes. On-boat devices never see a change.

## What differs, and whether it matters

| Area | Boat card | HALOS card | Matters? | What to do |
|---|---|---|---|---|
| Plugin tree | 124 deps in `package.json`, `package-lock=false` | 1 dep in `package.json`, ~80 plugins installed loose, same `package-lock=false` | **Yes.** The next app-store install prunes every plugin not in `package.json` | copy the boat's `package.json`, then `npm install` inside the container |
| Local plugin forks | symlinks to `/home/pi/bt-sensors-plugin-sk` and `../symphony/plugins/...` | container sees only the data dir | Yes | copy both into `data/local-plugins/` and use `file:local-plugins/...` |
| BlueZ access | native process, D-Bus on the host | container mounts `/run`, so `/run/dbus/system_bus_socket` is present; runs as uid 1000 | Test | enable the plugin, check `electrical.batteries.*` |
| mDNS inside SignalK | works (nss-mdns) | `nsswitch` is `files dns`, no mDNS | **Yes** for `venus.local` | point the Victron plugin at the Cerbo's LAN IP |
| CAN, UART, I2C | configured in `config.txt` and `/etc/network/interfaces` | nothing; HALOS only configures CAN on HALPI2 | **Yes** | copy the overlays; add a `systemd-networkd` `can0` unit |
| Memory cgroup | on (`cgroup_enable=memory` in `cmdline.txt`) | off; QuestDB's 768 MB limit is not enforced | Yes | add `cgroup_enable=memory cgroup_memory=1` |
| WiFi regulatory domain | US | GB | Yes for the hotspot's channels | set `cfg80211.ieee80211_regdom=US` |
| RAM | 4 GB Pi aboard | built on a 2 GB Pi, swapping 1.5 GB at home | Yes at home, less aboard | disable AvNav, OpenCPN and InfluxDB apps for the trial |
| Docker socket for plugins | native SignalK has host Docker | socket is inside the container but owned by gid 105, which `node` lacks | Only for container-managing plugins | disable `signalk-container`, `signalk-questdb`, `signalk-grafana`; keep the history provider in external mode |
| TLS | real certificates via Cloudflare DNS challenge | self-signed device CA, 824-day leaf | Yes for phones and OAuth | install the CA on each device from `/ca/`; no GitHub/Google login during the trial |
| Login federation | GitHub and Google through Dex | file-based accounts only | Yes | Authelia account for Mark; `captain` stays |
| URL shape | one hostname per app | one port per app, dashboard at `/` | Cosmetic | `signalk.<boat-domain>:4430`, or add a Traefik router for `/` |
| Node.js | nsolid 22 from apt | Node 24 inside the image | Native modules rebuild on `npm install` | expect `better-sqlite3` to fail; use `--ignore-scripts` then `npm rebuild` |
| `NODE_TLS_REJECT_UNAUTHORIZED=0` | not set | set by HALOS for the SignalK container | Outbound HTTPS from plugins skips certificate checks | accept for the trial; raise upstream later |
| pypilot | native service | absent | Yes if the autopilot is needed | trial without it, or swap back |
| gpsd | running, no device | running; default SignalK config has a gpsd provider | No | the boat's `settings.json` replaces it |
| Unattended upgrades | configured by `host/install.sh` | none | No for a short trial | install with the host layer |

## Decisions

**History DB: QuestDB only.** The boat already writes SignalK paths and
Telegraf metrics to QuestDB, and the boat's InfluxDB data was purged on
2026-08-25 with the only export sitting on the boat card. HALOS's QuestDB app
uses the same localhost ports as the boat's container, so `signalk-questdb-
history-provider` and `telegraf.conf` carry over unchanged, and HALOS's
Grafana already provisions a QuestDB datasource. InfluxDB 2.x is a dead end
(Flux frozen, v3 is a rewrite) and HALOS's own InfluxDB app is failing to
start. Keep `signalk-to-influxdb2` disabled and remove the InfluxDB app. The
boat's QuestDB history (1.8 GB) does not move for the trial; it comes home on
the old card. Both cards run QuestDB 10.0.0, so a stopped-database directory
copy can merge it later if HALOS is adopted.

**SSO and TLS for the trial: HALOS as shipped.** Set the HALOS hostname to
`signalk` and its domain to `<boat-domain>`. HALOS then derives
`signalk.<boat-domain>` as its canonical name, puts it in the certificate,
and uses it for every login redirect. That name already resolves on the LAN
(router override) and off-boat (Cloudflare → tailnet IP). Install the device
CA on Mark's phone and laptop once. Dex, Caddy and the GitHub/Google login
stay on the boat card; they are the rollback. What survives if HALOS is
adopted: the hostname and DNS design, Authelia accounts, and the QuestDB
stack. What does not: Dex and Caddy. Real certificates need a leaf-cert path
HALOS does not expose yet (it accepts a custom CA, not a custom leaf), so
that is an upstream ask, not a trial task.

**Plugin containers: HALOS-managed apps plus external-mode plugins.** HALOS
runs apps as apt packages with systemd units, Traefik routes and Homarr
tiles. Dirk Wahrheit's `signalk-container` family starts containers from
inside SignalK over the Docker socket. On HALOS that socket is not writable
by the container user, and any container it did start would sit outside
Traefik, autoheal and the port registry, and fight the HALOS QuestDB for
port 9000. The boat already runs the history provider in external mode
(`managedContainer: false`, host `127.0.0.1`), which is exactly what HALOS
wants. Cost: none today. Plugins that only work with managed containers
(`signalk-grafana`, `signalk-chart-locker`) stay disabled.

## Known gaps in the trial

- No autopilot. `pypilot` has no HALOS package and is not on the must-keep list.
- No GitHub/Google login. Local accounts only.
- No history before the swap. Old data stays on the boat card.
- Cellular WAN aboard: every package, image and plugin must be on the card before it leaves home.
