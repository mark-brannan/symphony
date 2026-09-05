# System map

What runs where. Hardware detail is in [compute_hardware.md](compute_hardware.md);
how the stack is built is in [software_stack.md](software_stack.md). One row
per machine, host configuration, service or name, so adding or dropping one
touches one line.

## Hardware

Labelled by role. Hostnames come from the card or install that boots on the
machine, not from the machine.

| Label | What | Where | Boots |
|---|---|---|---|
| boat Pi | Pi 4, 4 GB, PiCAN-M HAT | aboard | whichever card is in it |
| bench Pi | Pi 4, 2 GB | home LAN, `192.168.0.193` | the `halos` card, while it is being built |
| dev machines | Windows (WSL2), Mac | home | the `dev` stack |
| Cerbo GX | Venus OS Large | aboard, `192.168.8.107` (`venus.local`) | Victron's own stack; SignalK reads it over MQTT |
| HALPI2 | not bought | | candidate for `halos` |

## Host configurations

Each is a way of building a SignalK host, kept in this repo. A *card* is one
of these on an SD card.

| Config | Base | SignalK | Front door, login | From this repo |
|---|---|---|---|---|
| `openplotter` | Debian 12, OpenPlotter, bare metal; hostname `signalk` | native, `~/.signalk`, user `pi` | Caddy, Let's Encrypt; Dex → GitHub/Google | `host/`, `docker-compose.yml` + `compose-*.yml`, `dex/` |
| `halos` | Debian 13 + HALOS 0.3.7 apt packages; hostname `signalk` after build | container, `/var/lib/container-apps/marine-signalk-server-container/data/data`, uid 1000 | Traefik, device CA; Authelia local accounts | `host/` (partly), `compose-ntfy.yml`; the rest lives in HALOS's `/etc/halos/` |
| `dev` | any Docker host | container | none | `scripts/dev_stack.sh` |

## Services

| Service | Purpose | Runs on | Reach |
|---|---|---|---|
| SignalK 2.31.1 | the server | `openplotter`, `halos` | `:3000`; `halos` also Traefik `:4430` |
| QuestDB 10 | history for SignalK paths and host metrics | `openplotter` (volume `symphony_questdb-data`), `halos` (HALOS app) | `127.0.0.1:9000` HTTP, `:9009` ILP, `:8812` PG wire |
| Telegraf | host metrics → QuestDB | `openplotter`; `halos` after build | |
| ntfy | push to phones on the boat LAN | `openplotter`; `halos` after build | `:8090` |
| `boat-heartbeat.timer` | healthchecks.io ping, Pushover on failure | `openplotter`; `halos` after build | |
| `signalk-ble-check.timer` | restart SignalK when BLE goes silent | `openplotter`; `halos` after build | |
| chrony, unattended upgrades | time, patches | `openplotter`; `halos` after build | |
| Caddy, Dex | TLS and OIDC front door | `openplotter` | `:443`, `auth.<domain>` |
| Traefik, Authelia, Homarr, ca-download, autoheal | HALOS core: proxy, SSO, dashboard, CA download, restarts | `halos` | `:443`; ports per `/etc/halos/port-registry` |
| Grafana 13 | dashboards on QuestDB | `halos` | Traefik `:4433` |
| AvNav, OpenCPN | chart plotters | `halos`, disabled for the trial | `:4431`, `:4435` |
| pypilot | autopilot and IMU web UI | `openplotter`; `halos` after build | `:8000` |
| InfluxDB | none: purged 2026-08-25; HALOS app removed | | |

## Names and addresses

| Name | Answers with | Who answers |
|---|---|---|
| `symphony.dark-star-llc.com` (A record) | tailnet IP of the Pi aboard | Cloudflare; moved by `scripts/dns_cutover.sh` |
| `signalk.`, `grafana.`, `auth.` under it | CNAME to the apex | Cloudflare |
| the same names on the boat LAN | `192.168.8.240` | boat router override, fixed to the boat Pi's MAC |
| `signalk.local` | LAN IP | mDNS from whichever card is running |
| `symphony-pi`, `symphony-halos` | tailnet IPs of the `openplotter` and `halos` cards | Tailscale MagicDNS |
| `venus.local` | `192.168.8.107` | mDNS; not visible inside the `halos` SignalK container |

## SSH

| Command | Reaches | Notes |
|---|---|---|
| `ssh pi@symphony-pi` | the `openplotter` card, over Tailscale | `pi` has passwordless `sudo` and `docker` |
| `ssh pi@symphony-halos` | the `halos` card, over Tailscale (`halos-pi4` until renamed) | `sudo` needs sops key `symphony_halos_pi_password`; `docker` needs `sudo` |
| `ssh pi@192.168.0.193` | the bench Pi on the home LAN | same card as above |
| `ssh pi@symphony-pi 'ssh root@192.168.8.1 ...'` | boat router via the boat Pi | DNS override and DHCP reservations |
| `tmux attach -t claude` | after either ssh | resident Claude session (`openplotter` only) |

---

*Card swap, September 2026:* the `halos` card built on the bench Pi goes
into the boat Pi for a trial; the `openplotter` card comes home as the
rollback. Plan: `intermediate_files/claude_slop/halos-swap-plan.md`;
procedure: [runbooks/halos_swap.md](../runbooks/halos_swap.md). Cellular WAN aboard: every package, image and plugin must be on the
card before it leaves home.
