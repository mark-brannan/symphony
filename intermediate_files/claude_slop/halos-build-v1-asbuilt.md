# HALOS trial card — as-built, plan v1

As-built record of plan v1: card `halos-pi4` → `symphony-halos` (hostname `signalk`), prepared 2026-08-28..2026-09-02, target hardware Raspberry Pi 4 Model B Rev 1.5 (2 GB bench, 4 GB boat), image `ghcr.io/halos-org/signalk-server-docker:v2.31.1-halos.3` on HALOS (Debian 13 base).
Sources: `intermediate_files/claude_slop/halos-swap-plan.md`, `halos-swap-execution-2026-09-02.md`, `halos-b3-findings-2026-09-02.md`, `halos-swap-preflight-2026-09-02.md`, `halos-sync-inventory-2026-09-01.md`, `prompt-halos-i2c-fix.md`, `handoff-halos-b3-session.md`, `dispatch-halos-swap-day.md`, `log.md` (2026-09-01 onward), `host/halos/README.md`, `host/install.sh`, `scripts/halos_preflight.sh`, `scripts/halos_swap_check.sh`, `RUNBOOK.md`.

## Base OS / boot config

1. `sudo` on the card takes its password from sops key `symphony_halos_pi_password` via `sudo -S -p ""`; every `docker` command runs under `sudo`. `[narrative]`

2. Append to `/boot/firmware/config.txt` under `[all]`, keeping the existing lines: `[checked: scripts/halos_preflight.sh]` `[narrative]`
```
dtparam=i2c_arm=on
dtparam=spi=on
enable_uart=1
dtoverlay=mcp2515-can0,oscillator=16000000,interrupt=25
dtoverlay=spi-bcm2835-overlay
```

3. In `/boot/firmware/cmdline.txt` change `cfg80211.ieee80211_regdom=GB` to `cfg80211.ieee80211_regdom=US` and append `cgroup_enable=memory cgroup_memory=1`. `[checked: scripts/halos_preflight.sh]` `[narrative]`

4. Write `/etc/modules-load.d/i2c-dev.conf`: `[checked: scripts/halos_preflight.sh]` `[narrative]`
```
i2c-dev
```

5. Write `/etc/systemd/network/80-can.network`: `[narrative]`
```
[Match]
Name=can*

[CAN]
BitRate=250000
RestartSec=100ms
```

6. Enable networkd for `can*` only: `[narrative]`
```bash
sudo systemctl enable systemd-networkd
```

7. Disable the wait-online unit: `[artifact: host/halos/README.md]`
```bash
sudo systemctl disable systemd-networkd-wait-online
```

8. Reboot and verify `/dev/serial0`, `/dev/i2c-1`, `memory` in `/sys/fs/cgroup/cgroup.controllers`, regdom `US`. `[checked: scripts/halos_preflight.sh]`

## Network

9. Install the boat's NetworkManager keyfiles from sops keys `nm_symphony_nmconnection` (id `Symphony`), `nm_symphony_5g_nmconnection` (id `Symphony_5G`) into `/etc/NetworkManager/system-connections/`, mode 0600 root:root. `[checked: scripts/halos_preflight.sh]` `[narrative]` `[command not recorded]`

10. Edit `/etc/NetworkManager/system-connections/Halos-AP.nmconnection` in place: `ssid=SignalK`, `psk=` from sops key `nm_signalk_hotspot_nmconnection`; mode stays 0600. `[checked: scripts/halos_preflight.sh]` `[narrative]` `[command not recorded]`

11. Reload profiles: `[narrative]`
```bash
sudo nmcli con reload
```

12. Set the hostname: `[checked: scripts/halos_preflight.sh]` `[narrative]`
```bash
sudo hostnamectl set-hostname signalk
```

13. Edit `/etc/hosts` so the `127.0.1.1` line reads `127.0.1.1 signalk.<boat_domain> signalk` (`boat_domain` is the sops key; its value is the apex). `[checked: scripts/halos_preflight.sh]` `[narrative]`

14. Set `/etc/halos/hostnames.conf` to this order (first entry is the canonical name): `[checked: scripts/halos_preflight.sh]` `[narrative]`
```
${fqdn}
${hostname}.local
${domain}
```

15. Re-derive the domain and reissue the device certificate: `[narrative]`
```bash
sudo systemctl restart halos-resolve-domain halos-core-containers
sudo systemctl start halos-manage-certs
```

16. Rename the tailnet node (node key and tailnet IP unchanged): `[checked: scripts/halos_preflight.sh]` `[narrative]`
```bash
sudo tailscale set --hostname=symphony-halos
```

17. Verify `/run/halos/domain.env` reads `HALOS_DOMAIN=signalk.<boat_domain>` and the device cert SANs are `signalk.local`, `signalk.<boat_domain>`, `<boat_domain>`: `[checked: scripts/halos_preflight.sh]`
```bash
cat /run/halos/domain.env
openssl s_client -connect 127.0.0.1:443 </dev/null 2>/dev/null | openssl x509 -noout -ext subjectAltName
```

## Host services

18. Add the InfluxData apt repo (`https://repos.influxdata.com/debian`, suite `stable`) and install telegraf and chrony; chrony removes `systemd-timesyncd`. `[narrative]` `[command not recorded]`
```bash
sudo apt install telegraf chrony
```

19. Point telegraf at the repo config: symlink `/etc/telegraf/telegraf.conf` → `/home/pi/symphony/telegraf/telegraf.conf`; drop-in `/etc/systemd/system/telegraf.service.d/override.conf` with `User=pi`, `Group=pi`, `Type=simple`. `[checked: scripts/halos_preflight.sh]` `[narrative]` `[command not recorded]`

20. Purge the InfluxDB app (`remove` leaves a unit that fails at boot): `[artifact: host/halos/README.md]` `[checked: scripts/halos_preflight.sh]`
```bash
sudo apt-get purge marine-influxdb-container
```

21. Disable AvNav and OpenCPN: `[checked: scripts/halos_preflight.sh]` `[narrative]`
```bash
sudo systemctl disable --now marine-avnav-container marine-opencpn-container
```

22. Clone or pull the repo to `/home/pi/symphony` and run the installer (systemd watchdog conf, `after-bluetooth.conf` drop-in on `marine-signalk-server-container.service.d`, chrony drop-in, `telegraf-rpi-health`, `boat-heartbeat` script/service/timer, `signalk-unit.sh`, `signalk-ble-check` script/service/timer, apt unattended-upgrade confs; enables both timers; restarts chrony and telegraf): `[artifact: host/install.sh]`
```bash
cd /home/pi/symphony && git pull
sudo host/install.sh
```

23. The installer's `claude-resident` user-unit step fails on this card; no other step is affected. `[narrative]`

24. Write `/etc/boat-heartbeat.json`, root 0600, with `url` set to the ping URL of the healthchecks.io check `SignalK Symphony (halos card)` and `pushover_api_token` / `pushover_user_key` from the sops keys of the same names. `[checked: scripts/halos_preflight.sh]` `[narrative]` `[command not recorded]`

25. Install `systemd-zram-generator` configured for a 1 GB zstd swap device at priority 100 (`/dev/zram0` reports 1.8 GB). `[narrative]` `[command not recorded]`

26. Verify host services: `[checked: scripts/halos_preflight.sh]`
```bash
systemctl is-active telegraf chrony boat-heartbeat.timer signalk-ble-check.timer
journalctl -t boat-heartbeat -n 1
chronyc tracking | head -3
```

## SignalK container

27. Write `/etc/container-apps/marine-signalk-server-container/symphony.override.yml` from `host/halos/signalk-healthcheck-override.yml`: `[artifact: host/halos/signalk-healthcheck-override.yml]` `[checked: scripts/halos_preflight.sh]`
```yaml
services:
  signalk-server:
    group_add: ["988"]
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://127.0.0.1:3000/signalk || exit 1"]
      interval: 30s
      timeout: 30s
      start_period: 900s
      retries: 3
```

28. Write `/etc/systemd/system/marine-signalk-server-container.service.d/symphony.conf` from `host/halos/signalk-unit-override.conf`: `[artifact: host/halos/signalk-unit-override.conf]` `[checked: scripts/halos_preflight.sh]`
```
[Service]
ExecStart=
ExecStart=/bin/sh -c 'OVERRIDE=""; [ -f /run/halos/routing-labels/signalk-server.yml ] && OVERRIDE="-f /run/halos/routing-labels/signalk-server.yml"; docker compose -f docker-compose.yml $$OVERRIDE -f /etc/container-apps/marine-signalk-server-container/symphony.override.yml up'
ExecStop=
ExecStop=/bin/sh -c 'OVERRIDE=""; [ -f /run/halos/routing-labels/signalk-server.yml ] && OVERRIDE="-f /run/halos/routing-labels/signalk-server.yml"; docker compose -f docker-compose.yml $$OVERRIDE -f /etc/container-apps/marine-signalk-server-container/symphony.override.yml down'
```

29. Apply and restart (restart the unit, never `docker compose`): `[artifact: host/halos/README.md]`
```bash
sudo systemctl daemon-reload
sudo systemctl reset-failed marine-signalk-server-container.service
sudo systemctl restart marine-signalk-server-container.service
```

30. Verify the override took effect: `[artifact: host/halos/README.md]` `[checked: scripts/halos_preflight.sh]`
```bash
sudo docker exec signalk-server python3 -c "open('/dev/i2c-1')"
sudo docker inspect signalk-server --format '{{json .HostConfig.GroupAdd}}'
sudo docker inspect signalk-server --format '{{json .Config.Healthcheck}}'
```

Expected: silence; `["960","4","988"]`; interval 30s, timeout 30s, start_period 900s, retries 3.

## SignalK state

31. Save HALOS's own `package.json`, then rsync the boat's `.signalk` (run twice; the second pass transfers nothing but runtime counters): `[narrative]`
```bash
D=/var/lib/container-apps/marine-signalk-server-container/data/data
cp "$D/package.json" /home/pi/package.json.halos
rsync -av --exclude node_modules --exclude appstore-cache --exclude 'skserver-raw_*' \
  --exclude '*.bak*' --exclude '*.deb' --exclude signalk-server --exclude 'ssl-*.pem' \
  pi@symphony-pi:.signalk/ "$D"/
```

32. Install the two local plugin forks: `[checked: scripts/halos_preflight.sh]` `[narrative]`
```bash
mkdir "$D/local-plugins"
rsync -a --exclude node_modules --exclude .git pi@symphony-pi:bt-sensors-plugin-sk/ "$D/local-plugins/bt-sensors-plugin-sk/"
git -C /home/pi/symphony pull
cp -r /home/pi/symphony/plugins/signalk-plugin-watchdog "$D/local-plugins/"
```

33. In `$D/package.json` set `"signalk-plugin-watchdog": "file:local-plugins/signalk-plugin-watchdog"` and `"bt-sensors-plugin-sk": "file:local-plugins/bt-sensors-plugin-sk"`. `[checked: scripts/halos_preflight.sh]` `[narrative]`

34. Stop `marine-signalk-server-container`, `marine-questdb-container`, `marine-grafana-container`, `marine-avnav-container`, `marine-opencpn-container` and `docker stop homarr` before installing on a 2 GB card. `[narrative]`

35. Delete `$D/node_modules` and run `npm install --ignore-scripts` in a throwaway `node:24-bookworm` container with `$D` mounted at `/home/node/.signalk`, under `systemd-run --unit=<name> --collect`; expected 2773 packages, exit 0. `[narrative]` `[command not recorded]`

36. In the same container form, `npm rebuild` the named packages `i2c-bus epoll sqlite3 serialport lzma-native` only, never a bare `npm rebuild`. `[narrative]` `[command not recorded]`

37. In `$D/plugin-config-data/` set `"enabled": false` in `signalk-container.json`, `signalk-to-influxdb2.json`, `signalk-to-influxdb-v2-buffer.json`, `signalk-notification-player.json`. `[checked: scripts/halos_preflight.sh]` `[narrative]`

38. In `$D/plugin-config-data/venus.json` set `MQTT.host` from `venus.local` to `192.168.8.107`. `[narrative]`

39. `$D/plugin-config-data/plugin-watchdog.json` (from the boat rsync) is the live watchdog config; content as recorded: `[narrative]`
```json
{"enabled": true, "configuration": {"checkIntervalSeconds": 60,
 "graceSeconds": 600, "stallSeconds": 0,
 "expectPlugins": ["bt-sensors-plugin-sk"]}}
```

40. Remove the stray inert config: `[narrative]`
```bash
rm /var/lib/container-apps/marine-signalk-server-container/data/data/plugin-config-data/signalk-plugin-watchdog.json
```

41. Leave `pypilot-autopilot-provider.json` and `signalk-instrument-light-plugin` (no config, serialport bindings absent) unchanged. `[narrative]`

42. Restart the unit and verify 120 plugins, 63 enabled, one start failure (`signalk-instrument-light-plugin`): `[checked: scripts/halos_preflight.sh]`
```bash
sudo systemctl restart marine-signalk-server-container
journalctl -u marine-signalk-server-container -n 200 | grep -iE "EACCES|Cannot find module|watchdog|bt-sensors"
curl -s 127.0.0.1:3000/signalk
```

## Other containers

43. Create `/home/pi/symphony/.env` as a copy of `.env.example`. `[narrative]` `[command not recorded]`

44. Start ntfy from the repo compose: `[narrative]`
```bash
cd /home/pi/symphony
sudo docker compose -p symphony -f docker-compose.yml up -d ntfy
curl -s -o /dev/null -w '%{http_code}\n' 127.0.0.1:8090/v1/health
```

45. Write `/etc/halos/traefik-dynamic.d/symphony-signalk-host.yml` from `host/halos/traefik-symphony-signalk-host.yml` (Traefik reloads on write): `[artifact: host/halos/traefik-symphony-signalk-host.yml]` `[checked: scripts/halos_preflight.sh]`
```yaml
http:
  routers:
    symphony-signalk-host:
      rule: "Host(`signalk.symphony.dark-star-llc.com`) && !PathPrefix(`/sso/`) && !PathPrefix(`/ca/`) && !Path(`/sso`) && !Path(`/ca`)"
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

46. Verify with `--resolve` against 127.0.0.1: `/` → 302 `/admin/`, `/ca` → 302 `/ca/`, `/ca/` → 200, `/sso` → 404, `/sso/` → 200 Authelia. `[checked: scripts/halos_preflight.sh]` `[narrative]`

47. On the 2 GB bench only, after the preflight: `[narrative]`
```bash
sudo systemctl stop marine-questdb-container marine-grafana-container
sudo docker stop homarr
```

## Boat-side changes

48. Add a router DHCP reservation `cerbo` `<cerbo MAC>` → 192.168.8.107; verify: `[narrative]`
```bash
ssh pi@symphony-pi 'ssh root@192.168.8.1 "uci show dhcp | grep -i cerbo"'
```

49. Clear the two dead units the boat heartbeat was reporting: `[narrative]`
```bash
ssh pi@symphony-pi 'sudo systemctl reset-failed grafana-server unattended-upgrades'
```

50. Create a second healthchecks.io check `SignalK Symphony (halos card)` on the same Pushover channel; its ping URL goes in step 24. `[narrative]`

## Verification

51. From a tailnet machine with sops access, every line `ok`: `[artifact: scripts/halos_preflight.sh]`
```bash
scripts/halos_preflight.sh
```

```
ok    host       signalk symphony.dark-star-llc.com signalk.symphony.dark-star-llc.com symphony-halos
ok    boot       overlays cgroup regdom i2c-dev serial0 i2c-1
ok    wifi       profile Symphony; hotspot Halos-AP ssid SignalK
ok    plugins    120 loaded, 63 on; same set and states as the boat except the 4 expected-off and 3 image-only; forks pinned, D-Bus fix present
ok    signalk    active 2.31.1 override gid988 (healthcheck override installed, i2c gid in the SignalK process)
ok    services   8 active
ok    staydown   avnav opencpn disabled+inactive; influxdb app absent
ok    heartbeat  ping ok
ok    questdb    telegraf cpu rows 53; newest signalk row 1 s old
ok    ntfy       health 200
ok    front      Traefik :4430 -> SignalK 200; device cert has signalk.symphony.dark-star-llc.com
ok    mem        401 MB available, 1118 MB swap used (2 GB bench cannot hold the databases; the 4 GB boat can)
ok    dns        A symphony.dark-star-llc.com -> 100.x.x.x   (...)   symphony-pi   100.x.x.x   <- current   symphony-halos   100.x.x.x
```

52. DNS write-path dry run, ending on `symphony-pi`: `[artifact: scripts/dns_cutover.sh]`
```bash
scripts/dns_cutover.sh set symphony-halos -y
dig +short symphony.dark-star-llc.com @1.1.1.1
scripts/dns_cutover.sh set symphony-pi -y
dig +short symphony.dark-star-llc.com @1.1.1.1
```

53. Reboot twice with QuestDB and Grafana enabled; after each, SignalK answers within ~200 s, no failed units, preflight all `ok`. `[checked: scripts/halos_preflight.sh]` `[narrative]`

54. Boat baseline before the swap, then the same on the card after it; `victron` and `questdb` may FAIL on both: `[artifact: scripts/halos_swap_check.sh]`
```bash
scripts/halos_swap_check.sh symphony-pi
scripts/halos_swap_check.sh
```

Expected: eleven `ok` lines — `signalk`, `lan` (eth0 192.168.8.240/24, can0 UP), `n2k`, `victron`, `ble`, `heartbeat`, `ntfy`, `questdb`, `devices` (/dev/serial0 /dev/i2c-1), `bme680`, `front` (`:443` on the boat card, `:4430` on the HALOS card).

## Not recorded

- The literal keyfile install commands for steps 9–10 (which sops key maps to which filename, and the `scp`/`install` invocations).
- The InfluxData apt repo add command and key install (step 18).
- The telegraf symlink and drop-in file content as written on the card (step 19).
- The halos-card healthchecks.io ping URL; no sops key holds it (step 24).
- The `systemd-zram-generator` install command and `/etc/systemd/zram-generator.conf` content (step 25).
- The throwaway `node:24-bookworm` `docker run` / `systemd-run` invocations for install and rebuild (steps 35–36).
- The `.env` creation command (step 43).
- The `/etc/hosts` edit and `hostnames.conf` write as commands (steps 13–14).
- Whether `host/install.sh` was run from PR #34's branch or after its merge.

## Not done in v1

- pypilot (plan B4d): not installed; the trial runs without autopilot, IMU and pypilot web UI.
- `plugin-watchdog` running state: the 600 s `ALERT: plugin bt-sensors-plugin-sk ...` line never observed under unbroken uptime.
- BME680 / i2c against real hardware on the bench: permission path verified only; no sensor on the bus at home.
- `can0` and the `n2k-can0` provider: verifiable only with the PiCAN-M HAT on the boat.
- QuestDB under the now-enforced `mem_limit: 768m`: not observed on this card.
- `host/install.sh` does not install `host/halos/*`; they are placed by hand.
- Repo-vs-boat plugin config reconciliation (64 vs 84 configs); anchor-alarm plugins disabled; `signalk-mob-notifier` and `signalk-dsc` absent — all copied from the boat unchanged, decisions pending.
- QuestDB history migration from the boat card (ILP re-export) and Grafana dashboard provisioning (PR #25).
- Dex and Caddy: intentionally not on the card; remain on the boat card as rollback.
- Old-card salvage (plan P7): `~/influx-export`, `~/keep-before-purge/`, `symphony_questdb-data` volume copy-off after the swap.
