# HALOS card build plan and work breakdown — 2026-09-01

Goal: get the HALOS card (spare Pi 4 at home, `ssh pi@192.168.0.193`,
tailnet `halos-pi4`) ready to swap into the boat Pi. Context and decisions:
`reference/system_map.md`. The at-boat procedure: `RUNBOOK.md` →
"Swapping the HALOS card onto the boat". Facts below were measured on both
boxes on 2026-09-01.

Ground rules for every item:

- Work on the HALOS card at home only. Nothing is fetched at the boat.
- `sudo` on halos needs a password: pipe it from sops, never type it into a
  transcript. Pattern:
  `sops -d --extract '["symphony_halos_pi_password"]' secrets/symphony.sops.yaml | ssh pi@192.168.0.193 'sudo -S -p "" <command>'`
- Docker on halos is root-only. Use the pattern above for `docker` too.
- The SignalK data dir is `/var/lib/container-apps/marine-signalk-server-container/data/data`
  (call it `$D`). It is uid 1000 = `pi`, so `pi` can edit it without sudo.
- Restart SignalK with `sudo systemctl restart marine-signalk-server-container`,
  never with `docker compose` (the unit injects a guard variable).
- Each item ends with its verification command. Do not report done without
  running it.

## Hard preconditions (sensitive lane, not this plan)

- **S1** WiFi PSKs into sops: the `Symphony` client network and the
  `SignalK` hotspot. Items B2a and B2b block on this.
- **S2** `/etc/boat-heartbeat.json` onto halos, root 0600. Either the age
  key on halos plus `scripts/setup-git-filters.sh` in `/home/pi/symphony`,
  or a direct root-to-root copy from the boat. Item B4b blocks on this.
- **S3** The boat card's `~/influx-export` (1.4 GB), `~/keep-before-purge/`
  and the `symphony_questdb-data` volume (1.8 GB) are the only copies of that
  data. The card comes home after the swap; copy those three off it before
  the card is reused for anything. No InfluxDB data is dropped anywhere in
  this plan; the boat's InfluxDB store is already empty (4 KB).

## Ordered build plan

Order is by dependency. Items with the same letter can run in parallel.

### B1 — boot config and hardware (no dependencies)

**B1a. PiCAN-M overlays.** Append to `/boot/firmware/config.txt` under
`[all]`, copied from the boat card:

```
dtparam=i2c_arm=on
dtparam=spi=on
enable_uart=1
dtoverlay=mcp2515-can0,oscillator=16000000,interrupt=25
dtoverlay=spi-bcm2835-overlay
```

The halos file currently has none of these. Keep the existing lines.

**B1b. Kernel command line.** In `/boot/firmware/cmdline.txt` (one line),
change `cfg80211.ieee80211_regdom=GB` to `=US` and append
`cgroup_enable=memory cgroup_memory=1`. Without the cgroup flags every
container `mem_limit` on HALOS is silently unenforced (measured:
`/sys/fs/cgroup/cgroup.controllers` lacks `memory` on halos, has it on the
boat).

**B1c. `can0` bring-up.** HALOS uses NetworkManager, which does not manage
CAN. Do what HALOS itself does on HALPI2: install
`/etc/systemd/network/80-can.network`:

```
[Match]
Name=can*

[CAN]
BitRate=250000
RestartSec=100ms
```

and `sudo systemctl enable systemd-networkd`. NetworkManager and
systemd-networkd coexist here because networkd only matches `can*`.

Reboot. *Verify:* `ls -l /dev/serial0 /dev/i2c-1` shows both;
`cat /sys/fs/cgroup/cgroup.controllers` includes `memory`;
`iw reg get 2>/dev/null || cat /sys/module/cfg80211/parameters/ieee80211_regdom`
shows `US`; `dmesg | grep -i mcp251` shows the overlay probed (it fails
without the HAT — that is expected at home). `can0` is verified at the boat.

### B2 — network identity (B2a/B2b need S1)

**B2a. Boat WiFi.** `nmcli con add type wifi ifname wlan0 con-name Symphony ssid Symphony wifi-sec.key-mgmt wpa-psk wifi-sec.psk <from sops>`.
The home network profile (`TP-Link_397D`) stays; NM picks whichever is
present. *Verify:* `nmcli -t -f NAME con show | grep ^Symphony`.

**B2b. Hotspot.** Rename HALOS's AP so boat devices reconnect without
changes: `nmcli con modify Halos-AP 802-11-wireless.ssid SignalK wifi-sec.psk <from sops>`.
The boat's hotspot is SSID `SignalK`, `ipv4.method shared`, 10.42.0.1 —
identical addressing to HALOS's, only the SSID and key differ. *Verify:*
`nmcli -f 802-11-wireless.ssid con show Halos-AP` prints `SignalK`, and a
phone sees the network.

**B2c. Hostname and domain.** `sudo hostnamectl set-hostname signalk`, then
edit `/etc/hosts` so the `127.0.1.1` line reads
`127.0.1.1 signalk.<boat-domain> signalk`. HALOS derives its domain from
`hostname -d`, and `hostnames.conf` already lists `${hostname}.local` and
`${fqdn}`. Then `sudo systemctl restart halos-resolve-domain halos-core-containers`
and `sudo systemctl start halos-manage-certs`. *Verify:*
`cat /run/halos/domain.env` is `HALOS_DOMAIN=signalk.<boat-domain>`;
`openssl s_client -connect 127.0.0.1:443 </dev/null 2>/dev/null | openssl x509 -noout -ext subjectAltName`
lists `signalk.local` and `signalk.<boat-domain>`;
`cat /etc/halos/oidc-clients.d/signalk.yml` redirect uses `${HALOS_DOMAIN}`
(it does; the value is substituted at Authelia start).
Also add the literal line `symphony.<boat-domain>` to
`/etc/halos/hostnames.conf` below `${fqdn}` so the apex name gets a SAN too.

**B2d. Tailscale rename.** `sudo tailscale set --hostname=symphony-halos`.
The node key and IP (100.120.50.62) do not change, so no ACL edit and no
re-auth. *Verify:* from a dev machine `tailscale status | grep symphony-halos`
and `ssh pi@symphony-halos hostname` prints `signalk`.

### B3 — SignalK state (needs nothing; B3c needs B3a and B3b)

**B3a. Copy the boat's state dir.** From halos (home-fleet → symphony-devices
SSH is allowed by policy), over the boat's cellular link, small:

```
rsync -av --exclude node_modules --exclude appstore-cache --exclude 'skserver-raw_*' \
  --exclude '*.bak*' --exclude '*.deb' --exclude signalk-server --exclude 'ssl-*.pem' \
  pi@symphony-pi:.signalk/ "$D"/
```

175 MB excluding those. This brings `settings.json` (the `n2k-can0`
provider, `uniqueNumber` 368391, `bleApi.localBluetoothManaged: false`),
`security.json` (3 users incl. `captain`), all ~90 `plugin-config-data`
files, `red/` (Node-RED flows), `applicationData`, `serverState`,
`baseDeltas.json`, `priorities.json`. It overwrites HALOS's default
`settings.json` (whose only provider was gpsd, not wanted). Keep HALOS's
`package.json` aside first: `cp "$D/package.json" "$D/package.json.halos"`.

**B3b. Local plugin forks.** `mkdir "$D/local-plugins"`, then
`rsync -a --exclude node_modules --exclude .git pi@symphony-pi:bt-sensors-plugin-sk/ "$D/local-plugins/bt-sensors-plugin-sk/"`
(Mark's fork, 1.3.8-beta11 plus the D-Bus reconnect fixes from PR #189;
the registry build lacks them) and
`cp -r /home/pi/symphony/plugins/signalk-plugin-watchdog "$D/local-plugins/"`
after `git -C /home/pi/symphony pull`.

**B3c. `package.json` and install.** Take the boat's `package.json`
(rsynced in B3a, 124 deps) and change two entries:
`"signalk-plugin-watchdog": "file:local-plugins/signalk-plugin-watchdog"` and
`"bt-sensors-plugin-sk": "file:local-plugins/bt-sensors-plugin-sk"`. The
boat's watchdog entry is `file:../symphony/plugins/...`, which does not
exist inside the container. Then install inside the container as the
container user (Node 24, npm 12 there; `.npmrc` has `package-lock=false`):

```
sudo docker exec -u node -w /home/node/.signalk signalk-server npm install --ignore-scripts
sudo docker exec -u node -w /home/node/.signalk signalk-server npm rebuild
```

`--ignore-scripts` then `rebuild` is the boat's own recipe: `better-sqlite3`
(pulled by `signalk-polar`, `signalk-postgsail`) fails to compile, and a
plain `npm install` rolls the whole tree back when one build script fails.
`rebuild` fails on that package alone. Expect 20–40 minutes on home WAN.

Disable in `plugin-config-data` (set `"enabled": false`):
`signalk-container.json`, `signalk-to-influxdb2.json`,
`signalk-to-influxdb-v2-buffer.json` (see the plugin-container decision).
Leave `pypilot-autopilot-provider.json` as it is; with no pypilot it logs a
connection error and nothing else.

Edit `venus.json`: `MQTT.host` from `venus.local` to `192.168.8.107` (the
Cerbo's LAN IP, measured on the boat via mDNS). The container's
`nsswitch.conf` is `files dns`, so `.local` names never resolve in there.
Add a DHCP reservation for the Cerbo on the boat router when convenient;
the RUNBOOK's router section has the access pattern.

Restart the unit. *Verify:*
`curl -s localhost:3000/skServer/plugins | python3 -c 'import json,sys; p=json.load(sys.stdin); print(len(p), sum(1 for x in p if x.get("data",{}).get("enabled")))'`
gives roughly 90 total and 60 enabled;
`journalctl -u marine-signalk-server-container -n 200 | grep -iE "EACCES|Cannot find module|watchdog|bt-sensors"` shows the two local plugins starting
and no module errors; `curl -s localhost:3000/signalk` returns 2.31.1.
`captain` can log in at `https://<halos-ip>:4430`.

**B3d. Plugin-tree hazard, for anyone touching npm later.** `package-lock=false`
plus a `package.json` that lists a plugin is what keeps it alive. Any
`npm install` of something not in `package.json` prunes it. This bit the
boat twice; it bit halos already (HALOS's file listed 1 dep with ~80 loose
plugins). Always install through `package.json`.

### B4 — host layer (B4b needs S2; rest independent)

**B4a. Packages.** `sudo apt install telegraf chrony` — telegraf from the
InfluxData apt repo (`https://repos.influxdata.com/debian`, suite
`stable`; the `.deb` is a static Go binary, the Debian release does not
matter). Installing chrony replaces `systemd-timesyncd` automatically.
`sudo apt remove marine-influxdb-container` (its unit is in
`failed, start-limit-hit` on halos anyway; `apt remove` keeps data).
`sudo systemctl disable --now marine-avnav-container marine-opencpn-container`
to free RAM (measured on the 2 GB halos: 1.5 GB in swap with them running).

**B4b. Repo host files.** `cd /home/pi/symphony && git pull`, then
`sudo host/install.sh`. Three files need HALOS variants before or after the
run, because the unit is `marine-signalk-server-container.service` and not
`signalk.service`:

- `signalk-after-bluetooth.conf` → install as
  `/etc/systemd/system/marine-signalk-server-container.service.d/after-bluetooth.conf`
  (same content).
- `signalk-ble-check` → the copy at `/usr/local/sbin/signalk-ble-check` needs
  `signalk.service` and `signalk.socket` replaced by the container unit
  (there is no socket unit; drop those two lines) and `CONFIG=` pointed at
  `$D/plugin-config-data/bt-sensors-plugin-sk.json`. Best done as a
  `host/signalk-ble-check` change that detects which unit exists, so the
  repo file serves both cards.
- Telegraf: symlink `/etc/telegraf/telegraf.conf` → `/home/pi/symphony/telegraf/telegraf.conf`,
  drop-in `/etc/systemd/system/telegraf.service.d/override.conf` with
  `User=pi`, `Group=pi`, `Type=simple` (why: `/home/pi` is 0700 and the
  packaged unit is `Type=notify`, per `reference/software_stack.md`).
  The config already targets `127.0.0.1:9000`, which is HALOS's QuestDB.

*Verify:* `systemctl is-active telegraf chrony boat-heartbeat.timer signalk-ble-check.timer`
all `active`; `journalctl -t boat-heartbeat -n 1` says `ping ok`;
`curl -s "localhost:9000/exec?query=select%20count()%20from%20cpu"` grows
between two runs a minute apart; `chronyc tracking | head -3` shows a
source.

**B4c. ntfy.** From `/home/pi/symphony`:
`sudo docker compose -p symphony -f docker-compose.yml up -d ntfy`.
The project file includes every `compose-*.yml`; naming the service starts
only ntfy. Port 8090 on all interfaces, same as the boat, so
`signalk-ntfy.json`'s `http://localhost:8090` works unchanged. *Verify:*
`curl -s -o /dev/null -w '%{http_code}\n' localhost:8090/v1/health` is 200
and `curl -d test localhost:8090/symphony-alarms` reaches a subscribed phone.

### B5 — front door polish (needs B2c; optional)

**B5a. SignalK at the root of `signalk.<boat-domain>`.** Today
`https://signalk.<boat-domain>/` shows Homarr and SignalK is on `:4430`.
To serve SignalK at `/` on that hostname only, add
`/etc/halos/traefik-dynamic.d/symphony-signalk-host.yml`:

```yaml
http:
  routers:
    symphony-signalk-host:
      rule: "Host(`signalk.<boat-domain>`) && !PathPrefix(`/sso/`) && !PathPrefix(`/ca/`)"
      entrypoints: [websecure]
      tls: {}
      priority: 50
      service: symphony-signalk
  services:
    symphony-signalk:
      loadBalancer:
        servers:
          - url: "http://host.docker.internal:3000"
```

Traefik watches that directory; no restart. Homarr's router is priority 1,
Authelia's `/sso/` router uses default priority (rule length ~20), so 50
wins for this host and the exclusions keep SSO and CA download working.
*Verify:* `curl -sk -o /dev/null -w '%{http_code}\n' https://127.0.0.1/signalk -H 'Host: signalk.<boat-domain>'`
is 200 and `.../sso/` still is. Untested; if it misbehaves, delete the file.

### B6 — reboot soak and image (needs everything above)

Reboot twice. After each: `sudo docker ps --format '{{.Names}} {{.Status}}'`
shows every remaining container `healthy`; `free -m` available above 400 MB
on the 2 GB box (the boat Pi has 4 GB); the B3c and B4b verifications pass
again. Then run the "Before leaving home" block in the RUNBOOK procedure.

## Parallel work breakdown

Each item is one session. Paste the prompt; it names its inputs. Dependencies
are on items above. Recommended model and effort are per item.

| Item | Blocks on | Model, effort | Prompt |
|---|---|---|---|
| P1 hardware+boot | — | Sonnet, low | Do B1a–B1c from `intermediate_files/claude_slop/halos-swap-plan.md` on `ssh pi@192.168.0.193` (sudo password via the sops pattern in the plan). Reboot, run the B1 verification, report each line's output. |
| P2 network identity | S1 for B2a/B2b | Sonnet, low | Do B2a–B2d from the plan. Read the PSKs from sops keys the sensitive lane added (names in `secrets/symphony.sops.yaml`, never print them). Run the B2 verifications. Do B2c last: it restarts every HALOS container. |
| P3 SignalK state | — (rsync over the boat's cellular link; retry on timeouts) | Opus, medium | Do B3a–B3c from the plan. Keep `package.json.halos` aside. Use `--ignore-scripts` then `rebuild`. Then run the B3c verification and paste the plugin count and the grep output. If `npm rebuild` fails on anything other than `better-sqlite3`, stop and report. |
| P4 host layer | S2 for B4b; P3 for the ble-check path | Opus, medium | Do B4a–B4c from the plan. Change `host/signalk-ble-check` in the repo so it picks `marine-signalk-server-container.service` when `signalk.service` is absent, and the config path from the running unit; keep it working unchanged on the boat card. Commit that to a branch and open a draft PR. Run the B4 verifications. |
| P5 front door | P2 | Sonnet, low | Do B5a. If the router file does not work as written, find the Traefik priority Homarr and Authelia actually got (`docker exec traefik wget -qO- localhost:8080/api/http/routers`) and fix the priority; report what worked. |
| P6 soak | P1–P5 | Sonnet, low | Do B6. Run the RUNBOOK "Before leaving home" block verbatim and paste every output. Anything that fails is a card, not a fix. |
| P7 old-card salvage (after the swap) | the boat card at home | Sonnet, low | With the old boat card in a reader or the spare Pi: copy `home/pi/influx-export`, `home/pi/keep-before-purge` and `var/lib/docker/volumes/symphony_questdb-data` to the dev box, verify SHA256SUMS, and record sizes in `intermediate_files/claude_slop/log.md`. |

Left out on purpose: pypilot (no HALOS package, not on the must-keep list),
Dex and Caddy (they are the rollback and stay on the boat card), QuestDB
history migration (old card holds it; merge later if HALOS is adopted),
Grafana dashboards (HALOS provisions the datasource; panels are the open
PR #25 question).

## Observations for Mark, not in the plan

- The boat's Victron plugin socket to the Cerbo was in `SYN-SENT`, not
  `ESTABLISHED`, at the snapshot. Either the Cerbo's MQTT was down at that
  moment or the connection is flapping. Worth a look before the swap so the
  trial has a baseline.
- `signalk-healthcheck` is enabled on the boat card again (config keys
  `host`, `providers`, `mail`), against the inventory that said disabled. It
  is not the healthchecks.io path either way.
- `NODE_TLS_REJECT_UNAUTHORIZED=0` is set by HALOS on its SignalK container.
  Every plugin's outbound HTTPS skips certificate checks. Fine for a trial;
  an upstream issue if HALOS is adopted.
