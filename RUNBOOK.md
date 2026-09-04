# Symphony systems runbook

Commands the operator runs on S/V Symphony's computer systems: getting in,
keeping the stack up, secrets, and recovery. Procedures only; the design is
in [reference/software_stack.md](reference/software_stack.md). The HALOS card
swap has its own file: [runbooks/halos_swap.md](runbooks/halos_swap.md).

## Where things are

**Getting in**
- [SSH to the boat](#ssh-to-the-boat)
- [When Tailscale refuses the connection](#when-tailscale-refuses-the-connection)
- [A page hangs but ssh works — MTU](#a-page-hangs-but-ssh-works--mtu)
- [The resident Claude session](#the-resident-claude-session)

**Host**
- [Bringing up a host](#bringing-up-a-host)
- [Provisioning a HALOS card with Ansible](#provisioning-a-halos-card-with-ansible)
- [Installing host files](#installing-host-files)
- [Container health](#container-health)
- [Deploying a compose change to the boat](#deploying-a-compose-change-to-the-boat)
- [The off-boat heartbeat](#the-off-boat-heartbeat)
- [Silencing the alarms for planned work](#silencing-the-alarms-for-planned-work)
- [The boat's hourly fetch](#the-boats-hourly-fetch)
- [GPU hang from a desktop browser](#gpu-hang-from-a-desktop-browser)
- [A desktop on the boat Pi on demand](#a-desktop-on-the-boat-pi-on-demand)

**SignalK**
- [Stopping SignalK](#stopping-signalk)
- [Reinstalling SignalK](#reinstalling-signalk)
- [Never use OpenPlotter's "Reinstall"](#never-use-openplotters-reinstall)
- [NMEA 2000 input](#nmea-2000-input)
- [Adding a BLE sensor](#adding-a-ble-sensor)
- [QuestDB](#questdb)
- [Grafana dashboards](#grafana-dashboards)
- [pypilot](#pypilot)
- [Testing the DSC / AIS distress chain](#testing-the-dsc--ais-distress-chain)

**Secrets**
- [Adding a secret](#adding-a-secret)
- [Rotating a secret](#rotating-a-secret)
- [Rotating an InfluxDB token](#rotating-an-influxdb-token)
- [Rotating the age key](#rotating-the-age-key)
- [Removing a secret](#removing-a-secret)
- [Email pseudonyms in security.json](#email-pseudonyms-in-securityjson)
- [Router config backup](#router-config-backup)
- [SSO login](#sso-login)
- [SSO one-time setup](#sso-one-time-setup)
- [SSO access grants](#sso-access-grants)

**Troubleshooting**
- [Hostnames stop resolving on the boat](#hostnames-stop-resolving-on-the-boat)
- [A plugin isn't in the config UI](#a-plugin-isnt-in-the-config-ui)
- [Every plugin install fails on a `file:` dependency](#every-plugin-install-fails-on-a-file-dependency)
- [SignalK errors about missing packages](#signalk-errors-about-missing-packages)
- [BLE sensors silent after a reboot](#ble-sensors-silent-after-a-reboot)
- [A BLE sensor connects but delivers nothing](#a-ble-sensor-connects-but-delivers-nothing)
- [A plugin fork keeps reverting](#a-plugin-fork-keeps-reverting)
- [A hook blocks your commit](#a-hook-blocks-your-commit)

**Incidents**
- [A secret was committed in plaintext](#a-secret-was-committed-in-plaintext)
- [Lost age key](#lost-age-key)

---

## Two deployments

Commands below are written for compose. On the boat Pi, SignalK, InfluxDB,
Grafana and Caddy are systemd units; Dex, QuestDB, ntfy and autoheal are
containers. Translate:

| Compose | Boat Pi |
|---|---|
| `docker compose up -d <svc>` | `sudo systemctl start <svc>` |
| `docker compose restart <svc>`, `--force-recreate` | `sudo systemctl restart <svc>` |
| `docker compose stop <svc>` | `sudo systemctl stop <svc>` |
| `docker exec grafana grafana cli …` | `sudo grafana cli …` |
| service `grafana` | unit `grafana-server` |

Ports are the same on both: SignalK 3000, Grafana 3001, InfluxDB 8086.
Containers read the rendered `.env` automatically; in a shell, source it:

```bash
cd ~/symphony && set -a && . ./.env && set +a
```

**On the boat, always name the services in a compose command.** A bare
`docker compose up -d` starts containers that fight the native units for
ports 3000, 8086, 3001 and 443.

---

## SSH to the boat

```bash
ssh pi@symphony-pi          # boat card
ssh pi@halos-pi4            # HALOS trial Pi at home (symphony-halos once swapped)
```

Tailscale SSH; no keys. `symphony` alone does not resolve. Only devices on
the tailnet reach it, and the Windows side of a WSL machine is *not* on it
when only WSL runs tailscaled.

*Verify:* `tailscale status` lists the node, `curl -s http://symphony-pi:3000/signalk` returns JSON.

Add a host to the tailnet:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --ssh --hostname=<name>
```

*Verify:* `tailscale status` on another device lists it.

## When Tailscale refuses the connection

- `does not permit you to SSH to this node` — no `ssh` rule matches.
- `does not permit you to SSH as user X` — a rule matched; its `users` list lacks `X`.
- `# Tailscale SSH requires an additional check.` plus a `login.tailscale.com/a/...` URL —
  open it, approve, re-run ssh. Under `BatchMode=yes` this looks like a hang.

Rules for tagged nodes must name the tag; `autogroup:self` never matches a tag.

```bash
scripts/tailscale_policy.sh                   # print the live policy
scripts/tailscale_policy.sh validate <file>   # dry-run a change
```

Apply by pasting into the [policy editor](https://login.tailscale.com/admin/acls/file). Validate first; a bad save is a lockout.

## A page hangs but ssh works — MTU

Browser spins on `https://signalk.symphony.dark-star-llc.com/`, ssh and ping
are fine. Cellular and Starlink uplinks do this on a direct path.

Windows (elevated):

```powershell
Get-NetIPInterface -AddressFamily IPv4 | Where-Object InterfaceAlias -like '*Tailscale*'
netsh interface ipv4 set subinterface <ifIndex> mtu=1180 store=persistent
```

macOS / Linux (does not survive a `tailscaled` restart):

```bash
sudo ifconfig utun<N> mtu 1180        # macOS
sudo ip link set tailscale0 mtu 1180  # Linux
```

*Verify:* the page loads.

## The resident Claude session

```bash
tmux attach -t claude        # Ctrl-b then d detaches, leaves it running
```

If it isn't running (a `--user` unit; run as `pi`, not via `sudo`):

```bash
systemctl --user status claude-resident.service
systemctl --user start claude-resident.service
```

---

## Bringing up a host

Four phases in order. Run each check; an early failure surfaces two phases
later looking unrelated.

**1. Tooling.** Docker with compose v2, your user in `docker`, and:

```bash
sudo apt install pre-commit     # or: brew install pre-commit
# sops and age: standalone binaries from their GitHub releases, onto PATH
```

*Verify:* `docker compose version && sops --version && age --version && pre-commit --version`

**2. Key material.** Get the age private key onto the host out of band, never through the repo.

```bash
mkdir -p ~/.config/sops/age
cp <key file> ~/.config/sops/age/keys.txt
chmod 600 ~/.config/sops/age/keys.txt
```

*Verify:* `sops --decrypt secrets/symphony.sops.yaml | head -1` prints readable YAML. If not, stop here.

**3. Repo.**

```bash
git clone https://github.com/mark-brannan/symphony.git
cd symphony
bash scripts/setup-git-filters.sh
python3 scripts/render.py
```

*Verify:* `bash scripts/verify_encrypted.sh` passes and `grep -c ENC .env` prints 0.

**4. Services.**

```bash
docker compose up -d                              # plain
docker compose --profile tls up -d --build        # fully containerized host with SSO
bash scripts/provision_grafana_users.sh
bash scripts/provision_influxdb.sh
```

```bash
# On the boat, not the --profile tls line: see SSO login.
# provision_influxdb.sh may mint tokens. If it minted influx_token:
#   python3 scripts/render.py && docker compose up -d --force-recreate grafana
# If it minted influxdb_signalk_token: put it in
#   signalk/plugin-config-data/signalk-to-influxdb2.json and restart SignalK.
```

*Verify:* `bash scripts/test_integration.sh`

First-ever boot with no `security.json`: let SignalK's setup wizard create it,
then `git add signalk/security.json` once.

## Provisioning a HALOS card with Ansible

From a laptop on the tailnet, with `sops`, the age key, and ssh to `pi@symphony-halos`:

```bash
sudo apt install ansible
ansible-galaxy collection list community.sops community.general
ssh pi@symphony-halos 'cd /home/pi/symphony && bash scripts/setup-git-filters.sh'   # once per card
cd ansible && ansible-playbook site.yml
```

Variants: `--check --diff` (no changes), `--tags verify` (audit only),
`-e symphony_allow_reboot=false` (card carrying live data; reboot it yourself
after), `-e symphony_repo_version=<branch>`.

*Verify:* run it a second time and get `changed=0 failed=0`, then
`scripts/halos_preflight.sh` reads `ok` on every line.

## Installing host files

```bash
cd ~/symphony && git pull
sudo host/install.sh
```

Idempotent; re-run after any change under `host/`. It refuses on anything
that isn't a boat card; `SYMPHONY_INSTALL_FORCE=1` overrides only for a real
card failing a check.

*Verify* the hardware watchdog took (expect 30s, `30s`, `30`):

```bash
journalctl -b | grep -i "hardware watchdog"
systemctl show -p RuntimeWatchdogUSec
cat /sys/class/watchdog/watchdog0/timeout
```

chrony needs its package before the config means anything:

```bash
sudo apt install chrony
sudo host/install.sh
chronyc tracking && chronyc sources     # a reference named, one `^*` peer
```

`nightly-reboot` is installed but its cron line is commented out. If you
re-enable it, keep its guard: a reboot landing on an `npm install` in
`~/.signalk` truncates the plugin tree and npm will not repair it.

## Container health

```bash
ssh pi@symphony-pi 'docker ps --format "{{.Names}}\t{{.Status}}"'
```

Every line must say `(healthy)`. A line with no health word has no
healthcheck. For an unhealthy one, read the probe before restarting:

```bash
ssh pi@symphony-pi 'docker inspect <name> --format "{{json .State.Health}}"' | python3 -m json.tool
ssh pi@symphony-pi 'docker logs autoheal --since 24h'      # what autoheal restarted
```

Repeated restarts in the autoheal log mean the probe is losing a race: raise
that service's `start_period`, redeploy, then look for a fault.

## Deploying a compose change to the boat

```bash
ssh pi@symphony-pi
cd ~/symphony && git pull
docker compose --profile tls up -d questdb ntfy dex autoheal
```

*Verify:* the `docker ps` check above, about 90 s later.

## The off-boat heartbeat

`boat-heartbeat.timer` pings a healthchecks.io check every five minutes. The
URL lives sops-encrypted in `host/boat-heartbeat.json`; `host/install.sh`
places it at `/etc/boat-heartbeat.json`. No file, no pings.

To set it up or change the URL: create a check (period 5 min, grace 20 min
or more), edit the `url` field, then:

```bash
git diff --cached host/boat-heartbeat.json   # must show ENC[...], not the URL
sudo host/install.sh
sudo systemctl start boat-heartbeat.service
journalctl -t boat-heartbeat -n 5            # expect: ping ok
systemctl list-timers boat-heartbeat.timer   # NEXT about five minutes out
```

If the diff shows the URL in clear, stop: run `bash scripts/setup-git-filters.sh` and re-stage.

`ping failed` is either a dead endpoint or no uplink; check the uplink first.
To turn it off, delete `/etc/boat-heartbeat.json`; leave the timer alone.

## Silencing the alarms for planned work

From a laptop, before a shutdown, card swap or power-off:

```bash
scripts/monitoring_snooze.sh status
scripts/monitoring_snooze.sh pause pi
```

Don't resume by hand; the next ping un-pauses it.

*Verify:* after the box is back, `status` shows the check `up`. Still
`paused` ten minutes after boot means the timer isn't running aboard.

## The boat's hourly fetch

`boat-hourly-sync.timer` fetches `/home/pi/symphony` hourly; it never merges.

```bash
systemctl status boat-hourly-sync.timer
journalctl -t boat-hourly-sync -n 5 --no-pager -o cat    # symphony: fetched, N behind origin/main
```

The heartbeat body carries the same drift line. `behind` is normal.
`ahead`/`diverged` means someone committed on the boat; any `stashed` count
means a yadm autostash rolled back. Both need a person. On `fetch failed`:

```bash
sudo -u pi GIT_SSH_COMMAND='ssh -o BatchMode=yes -o ConnectTimeout=20' git -C /home/pi/symphony fetch origin
```

dotfiles syncs separately: `~/.local/bin/dotfiles-sync.sh --status`.

## GPU hang from a desktop browser

Chromium autostarted on this Pi wedges the v3d driver whether or not a
display is attached, and the board eventually hard-resets. Its autostart
entry lives in `~/.config/autostart-disabled/`; keep it there.

```bash
journalctl -b -k | grep -c "Resetting GPU for hang"    # want 0
ps -eo pid,stat,comm | awk '$2 ~ /D/'                  # want no kworker
```

A climbing count means something is driving the GPU; stop it. Only a reboot clears the blocked kworkers.

## A desktop on the boat Pi on demand

The Pi boots headless. Only RPi Connect *screen sharing* needs this; the
remote shell works without it.

```bash
sudo systemctl start lightdm
sleep 20
XDG_RUNTIME_DIR=/run/user/1000 systemctl --user start rpi-connect-wayvnc
pgrep -a -x labwc                                                              # want a `labwc -m` line
XDG_RUNTIME_DIR=/run/user/1000 systemctl --user is-active rpi-connect-wayvnc   # want active
```

Put it away (labwc burns a full core with no display attached):

```bash
XDG_RUNTIME_DIR=/run/user/1000 systemctl --user stop rpi-connect-wayvnc
sudo systemctl stop lightdm
pkill -u pi -x labwc          # -x, never -f: -f matches your own ssh line
pgrep -a -x labwc             # want no output
```

---

## Stopping SignalK

`signalk.socket` re-activates the service on the first connection to port
3000, so stop the socket first. Do this before any `npm install` in `~/.signalk`.

```bash
sudo systemctl stop signalk.socket
sudo systemctl stop signalk.service
ss -lntp | grep :3000         # expect no output
```

Start in reverse order. A killed service shows `failed`; clear it first:

```bash
sudo systemctl reset-failed signalk.service
sudo systemctl start signalk.socket signalk.service
```

## Reinstalling SignalK

**Do not run `sudo openplotter-signalk-installer`.** It removes the Node
runtime, and under `sudo` writes a launcher path the `pi` service cannot
read. Do the npm half as `pi`:

```bash
sudo systemctl stop signalk.socket signalk.service
npm install -g signalk-server --no-audit --no-fund
printf '#!/bin/sh\n%s/lib/node_modules/signalk-server/bin/signalk-server -c %s $*\n' "$(npm config get prefix)" "$HOME/.signalk" > ~/.signalk/signalk-server && chmod 775 ~/.signalk/signalk-server
sudo systemctl reset-failed signalk.service && sudo systemctl start signalk.socket signalk.service
```

The install takes 30–60 minutes and logs nothing while extracting; watch
`du -sh ~/.npm-global/lib/node_modules/signalk-server` grow instead.

*Verify:* `systemctl is-active signalk` and `journalctl -u signalk -f` reaches plugin loading with no `Cannot find module`.

## Never use OpenPlotter's "Reinstall"

Settings → Signal K → **Update** is safe. **Reinstall** runs `rm -rf ~/.signalk`
first, with no prompt and no backup. If you need it, back up `~/.signalk`
and restore the config files afterward.

## NMEA 2000 input

```bash
curl -s localhost:3000/signalk/v1/api/vessels/self/navigation/position
ip -br link show can0                  # want UP
timeout 5 candump -n 20 can0           # want frames
```

Expect `"$source": "n2k-can0.<addr>"` and coordinates that move between
calls. `$source` of `signalk-fixed-position` means the GPS is quiet and
Position Keeper is replaying the last fix. Read `$source`, not the presence
of a position.

Don't unset `uniqueNumber` (pinned `368391` in the connection's `subOptions`);
the Pi would appear as a new device on the bus each save.

## Adding a BLE sensor

In `signalk/plugin-config-data/bt-sensors-plugin-sk.json`, per peripheral.
`params.pollFreq` and an explicit `paths` block are both required; without
either the sensor connects and publishes nothing, with no error anywhere.
Saving through the plugin's config UI writes both.

```json
{
  "active": true,
  "mac_address": "A5:C2:37:40:01:46",
  "params": { "name": "House Battery 1", "sensorClass": "JBDBMS", "batteryID": "0146", "pollFreq": 60 },
  "paths": {
    "voltage": "electrical.batteries.0146.voltage",
    "SOC": "electrical.batteries.0146.capacity.stateOfCharge",
    "temp0": "electrical.batteries.0146.temperature"
  }
}
```

Identify by MAC, not name; both house batteries advertise as `DP04S007L4S200A`.

*Verify* (each sensor's `name` appears as its own `$source`):

```bash
curl -s http://localhost:3000/signalk/v1/api/vessels/self \
  | python3 -c 'import sys,json,collections
d=json.load(sys.stdin); c=collections.Counter()
def w(o):
    if isinstance(o,dict):
        if "value" in o and "$source" in o: c[str(o["$source"])]+=1
        for k,v in o.items():
            if k!="meta": w(v)
w(d)
print(c.most_common(20))'
```

If no sensor from the plugin appears at all, it is config, not radio.

## QuestDB

Bring-up on a host. The mmap limit is a host sysctl; the container cannot set it.

```bash
if [ "$(cat /proc/sys/vm/max_map_count)" -lt 1048576 ]; then
  echo 'vm.max_map_count=1048576' | sudo tee /etc/sysctl.d/99-questdb.conf
  sudo sysctl --system
fi
test "$(cat /proc/sys/vm/max_map_count)" -ge 1048576 && echo ok
docker compose -f docker-compose.yml up -d questdb
curl -fsS --max-time 5 --retry 30 --retry-delay 2 --retry-connrefused \
  -G --data-urlencode 'query=SELECT 1;' http://127.0.0.1:9000/exec      # answers = ready
docker inspect questdb --format '{{range .Config.Env}}{{println .}}{{end}}' | grep '^QDB_CAIRO_' | sort
```

All five must be present with these values, or the container preallocates
16 MB per column file and fills the SD card:

```
QDB_CAIRO_COMMIT_MODE=sync
QDB_CAIRO_O3_COLUMN_MEMORY_SIZE=256k
QDB_CAIRO_WAL_WRITER_DATA_APPEND_PAGE_SIZE=128k
QDB_CAIRO_WRITER_DATA_APPEND_PAGE_SIZE=256k
QDB_CAIRO_WRITER_DATA_INDEX_VALUE_APPEND_PAGE_SIZE=256k
```

Missing or different: `docker compose -f docker-compose.yml up -d --force-recreate questdb` and re-check.

Then the writers:

```bash
sudo systemctl restart telegraf
until curl -sf -G --data-urlencode 'query=SELECT 1 FROM cpu LIMIT 1' http://127.0.0.1:9000/exec | grep -q '"count":1'; do sleep 5; done
scripts/questdb_table_hygiene.sh              # TTL + dedup; read its output for unrecognised tables
sudo du -sm "$(docker inspect questdb --format '{{range .Mounts}}{{if eq .Destination "/var/lib/questdb"}}{{.Source}}{{end}}{{end}}')"
```

*Verify:* the `du` reads tens of MB, not GB. Re-run the hygiene script after adding a Telegraf input or recreating a table.

Memory pressure (`free -m` available under ~400 MB, or `grep ^pswp /proc/vmstat` climbing): stop QuestDB, InfluxDB or Grafana with `systemctl stop`, never `disable`.

## Grafana dashboards

Dashboards are generated from `scripts/build_dashboards.py`; the committed JSON is its output.

```bash
python3 scripts/build_dashboards.py
python3 scripts/test_dashboards.py       # not optional: a bad panel fails silently at runtime
```

UI tweaks live only in Grafana's database and are overwritten on the next
provisioning reload; put anything worth keeping in the spec.

Check the live boat:

```bash
python3 scripts/verify_dashboards_live.py --grafana https://grafana.<DOMAIN> --user <admin> --password <password>
curl -sG http://localhost:9000/exec --data-urlencode "query=SELECT table_name FROM tables()"   # a missing Telegraf table is a panel that cannot draw
```

## pypilot

Runs as the `pypilot` and `pypilot-web` containers; state is in `pypilot/data/`
(untracked; holds the compass calibration and a SignalK token). The native
units are disabled and `~/.pypilot` is the rollback.

*Verify,* in order:

```bash
docker exec pypilot i2cdetect -y 1                                    # 0x68 present = the IMU answers
docker logs pypilot 2>&1 | grep -i realtime                           # must read: made imu process realtime
docker exec pypilot pypilot_client imu.heading imu.pitch imu.error    # tilt the Pi, run again
curl -s -o /dev/null -w '%{http_code}\n' localhost:8000               # 200
```

Back up before any rebuild or re-image:

```bash
tar czf ~/pypilot-data-$(date +%Y%m%d).tgz -C pypilot data
tar tzf ~/pypilot-data-*.tgz | grep RTIMULib.ini      # must match
```

Roll back to native:

```bash
docker compose --profile pypilot down
sudo systemctl enable --now pypilot pypilot_web
```

## Testing the DSC / AIS distress chain

**Never press a radio's DSC distress button or activate a SART/MOB/EPIRB to
test.** Everything here injects synthetic traffic over UDP.

1. Turn off DSCWatch reporting first: Plugin Config → signalk-dsc → untick
   "Report received calls to DSCWatch.com". Queued reports send later, even
   from an offline test.
2. Add a UDP NMEA 0183 input if none exists (Settings → Connections → Add,
   type NMEA0183, udp, port 7777), then restart SignalK.
3. Clone the plugin repos:

   ```bash
   # the npm tarballs omit scripts/
   git clone https://github.com/sailingnaturali/signalk-dsc
   git clone https://github.com/sailingnaturali/signalk-ais-distress
   ```

4. Fire traffic:

   ```bash
   # always pass --host; the default is the author's boat
   node signalk-dsc/scripts/send-test-dsc.js --host localhost --port 7777
   node signalk-dsc/scripts/send-test-dsc.js --host localhost --port 7777 --nature mob --category urgency
   node signalk-ais-distress/scripts/send-test-ais.js --host localhost --port 7777 --beacon mob
   ```

5. *Verify* through the API, not the phone (per-call alarms never reach
   `signalk-ntfy`; `reference/distress_monitoring.md`):

   ```bash
   curl -s -H "Authorization: Bearer $TOK" localhost:3000/signalk/v2/api/resources/dsc-calls
   curl -s -H "Authorization: Bearer $TOK" localhost:3000/signalk/v2/api/resources/ais-distress
   curl -s -H "Authorization: Bearer $TOK" localhost:3000/signalk/v1/api/vessels/self/notifications
   ```

   Expect the stored call, one `notifications.received.<category>.<id>`
   each, and `notifications.mob` for `--beacon mob`.

6. Clear the alarms (readwrite token):

   ```bash
   cd signalk-dsc          && SIGNALK_TOKEN=$TOK node scripts/clear-dsc-alarm.js --host localhost --category all
   cd ../signalk-ais-distress && SIGNALK_TOKEN=$TOK node scripts/clear-ais-alarm.js --host localhost --beacon all
   ```

7. Restore DSCWatch and remove the test UDP input.

---

## Adding a secret

**A standalone value** (API key, token, password) goes in the store:

```bash
sops secrets/symphony.sops.yaml          # add the `name: value` line, save
git add secrets/symphony.sops.yaml
git commit -m "Store <name>" -- secrets/symphony.sops.yaml
```

*Verify:* `sops --decrypt --extract '["<name>"]' secrets/symphony.sops.yaml` prints the value; `git show :secrets/symphony.sops.yaml | grep <name>` shows `ENC[`. `File has not changed, exiting.` means the edit didn't save.

To make something read it, add the key to `.env.example` and `.env.j2`, run
`python3 scripts/render.py`, and restart the reader.

**A field inside a config file SignalK/Grafana owns** is encrypted in place:

```bash
scripts/add_inplace_secret.sh signalk/plugin-config-data/<plugin>.json token
git commit -m "Encrypt <plugin>.json's token"
```

Never point it at `secrets/*.sops.yaml`. If a `secrets/` file ever fails
`git add` with sops complaining about *"a top-level entry called 'sops'"*,
delete the `filter=sops` line for it from `.gitattributes` and its
`path_regex` block from `.sops.yaml`, then:

```bash
git check-attr filter -- secrets/symphony.sops.yaml   # want: unspecified
python3 scripts/sops_paths.py check
git add secrets/symphony.sops.yaml
```

## Rotating a secret

**Store value:**

```bash
sops secrets/symphony.sops.yaml
python3 scripts/render.py
docker compose up -d --force-recreate <service>
```

`GF_SECURITY_ADMIN_PASSWORD` only applies to a fresh Grafana volume. On an existing one, also:

```bash
docker exec grafana grafana cli admin reset-admin-password '<value>'
curl -u admin:<value> http://localhost:3001/api/org      # expect 200
```

**In-place value:** change it in the SignalK admin UI, then `git add <file>
&& git commit`. If the store mirrors it (`influx_token` does), update both.

**Grafana / InfluxDB user passwords:** edit the store, then re-run
`scripts/provision_grafana_users.sh` / `scripts/provision_influxdb.sh`.

## Rotating an InfluxDB token

Tokens show once at creation, so: mint, migrate, verify, then revoke.

```bash
cd ~/symphony
TOK=$(sops --decrypt --extract '["influxdb_captain_token"]' secrets/symphony.sops.yaml)
ORG=$(curl -s -H "Authorization: Token $TOK" http://localhost:8086/api/v2/orgs \
      | python3 -c 'import json,sys;print(json.load(sys.stdin)["orgs"][0]["id"])')
curl -s -o /dev/null -w "auth check: %{http_code}\n" -H "Authorization: Token $TOK" http://localhost:8086/api/v2/authorizations
```

`200` to continue. Find the authorization to replace:

```bash
curl -s -H "Authorization: Token $TOK" "http://localhost:8086/api/v2/authorizations?orgID=$ORG" \
  | python3 -c '
import json,sys
for a in json.load(sys.stdin)["authorizations"]:
    print(a["id"], repr(a.get("description","")), "perms=%d" % len(a["permissions"]))
'
OLD_ID=<paste the id>
```

Mint the replacement with the same permissions. Don't echo `$NEW`; scrollback and transcripts persist.

```bash
curl -s -H "Authorization: Token $TOK" "http://localhost:8086/api/v2/authorizations/$OLD_ID" > /tmp/oldauth.json
python3 -c '
import json
a=json.load(open("/tmp/oldauth.json"))
json.dump({"orgID":a["orgID"],"userID":a["userID"],
           "description":a.get("description","")+" (rotated)",
           "permissions":a["permissions"]}, open("/tmp/newauth-req.json","w"))
'
curl -s -X POST -H "Authorization: Token $TOK" -H "Content-Type: application/json" \
     -d @/tmp/newauth-req.json http://localhost:8086/api/v2/authorizations > /tmp/newauth.json
NEW=$(python3 -c 'import json;print(json.load(open("/tmp/newauth.json"))["token"])')
```

Update every consumer. Find them; the list grows. The plugin token is nested
at `configuration.influxes[].token`, and the buffering plugin's file is
`signalk-to-influxdb-v2-buffer.json`.

```bash
grep -rl -- "$TOK" ~/.signalk/plugin-config-data/ /etc/telegraf/ 2>/dev/null
grep -c -- "$TOK" ~/symphony/.env
for f in $(grep -rl -- "$TOK" ~/.signalk/plugin-config-data/); do
  OLD="$TOK" NEW="$NEW" python3 -c '
import os,io,sys
p=sys.argv[1]; s=io.open(p,encoding="utf-8").read()
io.open(p,"w",encoding="utf-8").write(s.replace(os.environ["OLD"],os.environ["NEW"]))
print("updated", p)
' "$f"
done
sops --set "[\"influxdb_captain_token\"] \"$NEW\"" secrets/symphony.sops.yaml
python3 scripts/render.py
```

Restart consumers and prove writes land before revoking:

```bash
sudo systemctl restart signalk telegraf                      # boat
# docker compose up -d --force-recreate signalk telegraf     # containerized
curl -s -H "Authorization: Token $NEW" -H "Content-Type: application/vnd.flux" -H "Accept: application/csv" \
     -XPOST "http://localhost:8086/api/v2/query?org=symphony" \
     -d 'from(bucket:"symphony")|>range(start:-2m)|>limit(n:3)' | head -3
```

Rows means the new token carries traffic. No rows: stop and fix; the old one still works. Then revoke:

```bash
curl -s -o /dev/null -w "delete: %{http_code}\n" -X DELETE -H "Authorization: Token $NEW" \
     "http://localhost:8086/api/v2/authorizations/$OLD_ID"
curl -s -o /dev/null -w "old token now: %{http_code}  (401 = revoked)\n" \
     -H "Authorization: Token $TOK" http://localhost:8086/api/v2/authorizations
shred -u /tmp/oldauth.json /tmp/newauth.json /tmp/newauth-req.json
```

Expect `204` then `401`. Record it in `ROTATION.md`.

If nothing authenticates, the InfluxDB UI at `:8086` with the `captain`
login is what's left. `DOCKER_INFLUXDB_INIT_USERNAME`/`_PASSWORD` are not a
login on this volume; it predates them.

## Rotating the age key

Annually, and immediately on suspected exposure. Commit after each phase.

```bash
scripts/rotate_age_key.sh status
scripts/rotate_age_key.sh add --generate           # phase 1: new key joins
#   back up the new key; install it on every host
scripts/rotate_age_key.sh verify <new-public-key>  # gate: the new key alone opens everything
scripts/rotate_age_key.sh retire <old-public-key>  # phase 2
```

Don't skip `verify`. Two things make a half-finished rotation look finished
and it checks for both; if it fails it names the files.

A host missed before phase 2 fails to decrypt afterward: copy a current key
to `~/.config/sops/age/keys.txt` there and re-run `scripts/setup-git-filters.sh`.

If the old key was *compromised*, rotating it is not enough; history still
holds ciphertext it can read. Rotate the secrets themselves too.

Check an escrow key that isn't on this box (after any move, and yearly).
Not into the keyring; that defeats keeping it off-box:

```bash
install -m 600 /dev/null /tmp/check.key            # paste the key in
age-keygen -y /tmp/check.key                       # must print the public key from .sops.yaml
SOPS_AGE_KEY_FILE=/tmp/check.key scripts/rotate_age_key.sh verify <public-key>
shred -u /tmp/check.key
```

Expect `decrypts all N file(s)` for an escrow key; fewer means it is scoped.

## Removing a secret

1. Delete its `path_regex` block from `.sops.yaml`.
2. Delete its `filter=sops` line from `.gitattributes`.
3. `python3 scripts/sops_paths.py check`
4. If the file is going away: `git rm --cached <file>` and add it to `.gitignore`.

If the value was ever live in a public commit, rotate it.

## Email pseudonyms in security.json

Addresses in `signalk/security.json` become `pid.*` tokens in git and are
restored on checkout.

```bash
python3 scripts/pseudonymize.py resolve pid.rj232vx
git log -S 'pid.rj232vx' -- signalk/security.json       # when someone had access
```

When someone new logs in, the commit prints `pseudonymize: the map changed`;
stage `secrets/pseudonyms.sops.yaml` in that same commit.

If checkout warns `cannot decrypt secrets/pseudonyms.sops.yaml`, don't start
SignalK against the file. Get an age identity working, then
`git checkout -- signalk/security.json`.

## Router config backup

The router holds the DNS override that makes the hostnames resolve aboard.
Refresh after any router change, from anywhere on the tailnet:

```bash
ssh pi@symphony-pi 'ssh root@192.168.8.1 "uci export"' > /tmp/uci.txt
test -s /tmp/uci.txt && grep -q '^package' /tmp/uci.txt && echo export ok
python3 -c "import yaml; yaml.safe_dump({'uci_export': open('/tmp/uci.txt').read()}, open('secrets/router-config.sops.yaml','w'), default_style='|')"
sops --encrypt --in-place secrets/router-config.sops.yaml
rm /tmp/uci.txt
```

Stop if `export ok` doesn't print; an empty export overwrites the backup.

*Verify:* `sops --decrypt --extract '["uci_export"]' secrets/router-config.sops.yaml | head -3`, then commit.

Restore: `sops --decrypt secrets/router-config.sops.yaml`, feed `uci_export`
through `uci import` on the router, then `reload_config`. This restores WiFi
and WAN too.

## SSO login

Dex on the boat fronts GitHub and Google. Any account gets SignalK readonly;
the owner's email gets SignalK admin and Grafana Admin. Local password logins
(`captain`, Grafana superadmin) remain and are the offline fallback.
One-time setup is under [SSO one-time setup](#sso-one-time-setup).

Deploy on the boat (Caddy is native; name `dex`, or the caddy container
fights for `:443`):

```bash
git pull
python3 scripts/render.py
docker compose --profile tls up -d dex
sudo systemctl restart caddy
# fully containerized host instead, dockside (first run issues certificates):
#   docker compose --profile tls up -d --build
# restart grafana and signalk too if GF_AUTH_GENERIC_OAUTH_* or SIGNALK_OIDC_* changed
```

*Verify:*

```bash
curl -s https://signalk.symphony.dark-star-llc.com/signalk/v1/auth/oidc/status               # "enabled":true, issuer .../dex
curl -s https://auth.symphony.dark-star-llc.com/dex/.well-known/openid-configuration | head -3
```

Then in a browser: owner login → SignalK Security → Users shows type
`admin`; another account shows `readonly`; Grafana admits the owner as Admin
and refuses others; `captain` still logs in. An owner login that comes out
`readonly` means `SIGNALK_OIDC_GROUPS_ATTRIBUTE=email` didn't reach the
server; it fails silently.

## SSO one-time setup

**1. DNS (Cloudflare).** A record `symphony.dark-star-llc.com` → the host's
tailnet IP; CNAMEs `signalk.`, `grafana.`, `auth.` → it. All DNS-only (grey
cloud). Create an API token from the "Edit zone DNS" template scoped to this
zone. On the boat router add `address=/symphony.dark-star-llc.com/<LAN IP>`.
A rebuilt or re-added host gets a new tailnet IP and this record goes
stale (off-boat dead, on-boat fine).

*Verify:* from the boat LAN with the WAN unplugged, `nslookup signalk.symphony.dark-star-llc.com` returns the LAN IP.

**2. OAuth apps.** GitHub: personal account → OAuth Apps → New, homepage
`https://auth.symphony.dark-star-llc.com`, callback
`https://auth.symphony.dark-star-llc.com/dex/callback`. Google: a project,
consent screen External and **published**, Web application credential
with the same callback.

**3. Secrets.**

```bash
sops secrets/symphony.sops.yaml   # fill boat_domain, github_oauth_client_id/secret,
                                  # google_oauth_client_id/secret, cloudflare_api_token, owner_email;
                                  # leave dex_symphony_client_secret
python3 scripts/render.py
```

Then deploy per [SSO login](#sso-login).

## SSO access grants

Both lists are re-read at every login: promotions made in the SignalK UI
don't stick, and removals take effect at the next login.

```bash
$EDITOR .env.j2
#   Grafana: append  || email=='crew@example.com' && 'Editor'  to GF_AUTH_GENERIC_OAUTH_ROLE_ATTRIBUTE_PATH
#   SignalK: add the address to SIGNALK_OIDC_ADMIN_GROUPS (or _READWRITE_GROUPS), comma-separated, case-sensitive
python3 scripts/render.py
docker compose up -d --force-recreate grafana signalk
```

**Cut someone off entirely:** delete their SignalK user (Security → Users;
sessions never expire otherwise) and their Grafana user.

**Offshore:** signed-in devices stay signed in. A fresh device uses the
local password form. After ~60 days offline browsers warn about the
certificate; it renews itself when internet returns.

---

## Hostnames stop resolving on the boat

All names fail on the boat wifi but `http://192.168.8.240:3000` loads by IP.
The router's wildcard points only at the wired address.

```bash
ping -c2 192.168.8.240   # wired
ping -c2 192.168.8.241   # wifi
```

Wired dead, wifi alive: repoint the wildcard at wifi until the cable is fixed.

```bash
ssh root@192.168.8.1
uci set dhcp.@dnsmasq[0].address='/symphony.dark-star-llc.com/192.168.8.241'
uci commit dhcp && /etc/init.d/dnsmasq restart
```

*Verify:* `dig +short signalk.symphony.dark-star-llc.com` from the boat wifi returns `.241` (flush the client cache if not). Set it back to `.240` afterward.

## A plugin isn't in the config UI

A plugin that crashes on load is absent from Server → Plugin Config, which
looks like not installed.

```bash
docker logs signalk-server --since 5m 2>&1 | grep 'failed to start'      # container
journalctl -u signalk --since -5m | grep 'failed to start'               # boat
```

Missing-module errors: on the boat, see [SignalK errors about missing
packages](#signalk-errors-about-missing-packages). In a container, reinstall
against `signalk/package.json`:

```bash
docker compose stop signalk
mv signalk/node_modules signalk/.node_modules_old
docker run --rm -v "$PWD/signalk:/home/node/.signalk" -w /home/node/.signalk --entrypoint npm signalk/signalk-server:latest install
docker compose start signalk
```

Before any `npm install` in `~/.signalk`, list what it would prune; hand-copied plugins are deleted without prompting:

```bash
cd ~/.signalk && npm install <pkg> --dry-run 2>&1 | grep '^remove'
```

Back those up first. A plugin that must stay gets a `file:` entry in
`package.json` pointing **outside** `node_modules`.

## Every plugin install fails on a `file:` dependency

Every App Store install fails with `ENOENT ... /home/pi/.signalk/<plugin>/package.json`,
naming a plugin you didn't pick. A `file:` entry points inside `node_modules`.

```bash
grep -o '"[^"]*": *"file:[^"]*"' ~/.signalk/package.json     # any `node_modules` result is the fault
cd ~/.signalk
cp -a package.json package.json.bak-$(date +%Y%m%d)
npm pkg set dependencies.<plugin>=file:../symphony/plugins/<plugin>
npm --save --ignore-scripts install
```

*Verify:* `ls -l ~/.signalk/node_modules/<plugin>` is a symlink into `../../symphony/plugins/`, and the source is still there. Restart SignalK.

## SignalK errors about missing packages

A truncated plugin tree on the boat. **Never run `npm install` over a broken
tree**; npm treats half-written packages as installed. Move it aside and
install in two phases; a single `npm install` deletes the whole tree when
`better-sqlite3`'s build fails, which it always does here.

```bash
free -m                                # want > 2 GB available; else stop grafana-server influxdb, then raspotify cups cups-browsed ModemManager
sudo systemctl stop signalk.socket
sudo systemctl stop signalk.service
mv ~/.signalk/node_modules ~/.signalk/.node_modules_old
cd ~/.signalk
npm install --ignore-scripts --no-audit --no-fund   # phase 1: the tree
npm rebuild                                          # phase 2: natives; exits non-zero and that is fine
```

Watch with `vmstat 5`: high `wa` is SD writes and finishes; `si`/`so`
non-zero with `available` falling is swapping, so free more memory. Don't
kill the install. If a previous run was interrupted, `npm cache clean --force` first.

*Verify:*

```bash
find ~/.signalk/node_modules -name '*.node' | wc -l   # dozens, not 0
ls -d ~/.signalk/node_modules/@mapbox/node-pre-gyp    # must exist
sudo systemctl reset-failed signalk.service && sudo systemctl start signalk.socket signalk.service
```

## BLE sensors silent after a reboot

Nothing under `electrical.batteries.*` and one `Uncaught exception: Error: write EPIPE` from `dbus-next` at startup.

```bash
journalctl --since -1h | grep "not authenticated soon enough"          # present = this fault
grep -c getBluetoothSession /home/pi/bt-sensors-plugin-sk/index.js     # want > 0
```

If the count is 0 the boat is on an old copy of the plugin:

```bash
git -C /home/pi/bt-sensors-plugin-sk pull --ff-only
sudo systemctl stop signalk.socket
sudo systemctl stop signalk.service
sudo systemctl start signalk.socket
curl -s -o /dev/null http://localhost:3000/signalk/
```

*Verify* with the `$source` census under [Adding a BLE sensor](#adding-a-ble-sensor), after a few minutes.
Don't reinstate a raised `auth_timeout` in `/etc/dbus-1/`; it only hides a different fault.

## A BLE sensor connects but delivers nothing

Log shows `le-connection-abort-by-local` and `Unable to connect ... after 5 attempts`.

```bash
bluetoothctl --timeout 20 scan on >/dev/null 2>&1
bluetoothctl info <MAC> | grep -E 'RSSI|Connected'
{ printf 'connect <MAC>\n'; sleep 25; printf 'quit\n'; } | bluetoothctl
```

Healthy RSSI and `Connected: yes` then immediately `no` means GATT discovery
dies in the controller firmware. Resetting the adapter, restarting
`bluetooth`, and `remove <MAC>` don't clear it. Reboot the Pi, after
confirming no install is running:

```bash
pgrep -a -f 'npm |node-gyp|apt-get|dpkg'      # want nothing
sudo reboot
```

Read the sensor directly to separate radio from decode:

```bash
scripts/ble-probe.sh poll <MAC> ff02 dda50300fffd77 ff01 15   # JBD packs
```

## A plugin fork keeps reverting

`~/.signalk/node_modules/<plugin>` was a symlink to a fork and is now the
registry build. Any install re-resolves it unless the pin matches the fork's
exact version (a caret range never matches a prerelease).

```bash
node -e 'console.log("pin: ", require("/home/pi/.signalk/package.json").dependencies["bt-sensors-plugin-sk"])'
node -e 'console.log("fork:", require("/home/pi/bt-sensors-plugin-sk/package.json").version)'
```

With SignalK stopped, relink and pin the exact version in `~/.signalk/package.json`:

```bash
rm -rf ~/.signalk/node_modules/bt-sensors-plugin-sk
ln -s ~/bt-sensors-plugin-sk ~/.signalk/node_modules/bt-sensors-plugin-sk
cd ~/bt-sensors-plugin-sk && npm install --omit=dev --ignore-scripts --no-audit --no-fund   # the fork's own deps
find ~/bt-sensors-plugin-sk/node_modules -name '*.node'                                     # want none; else npm rebuild here
```

Restart SignalK before judging anything; it keeps whatever it loaded at startup.

## A hook blocks your commit

```bash
bash scripts/check_clone_setup.sh      # names the fix for every gap
```

- **"staged WITHOUT sops encryption markers"** — the clean filter isn't wired. `bash scripts/setup-git-filters.sh`, re-stage.
- **"looks like a cleartext credential"** — wire it with `scripts/add_inplace_secret.sh`, or rename the field if it isn't a secret.
- **gitleaks finding** — look at the file and line. A true false positive gets a narrow `.gitleaks.toml` allowlist entry with `condition = "AND"`.
- **"sops config is inconsistent"** — `.sops.yaml` and `.gitattributes` disagree; the message says which.

A blocked **push** names a commit and a file:

```bash
git show <commit>:<file>
bash scripts/setup-git-filters.sh
git rebase -i <commit>~1
git push
# if that commit was already pushed, the secret is out: see the incident below
```

Break glass: `SKIP=<hook-id> git commit`, `git commit --no-verify`,
`git push --no-verify`. CI still scans full history on the PR.

---

## A secret was committed in plaintext

**Rotate first.** It is compromised the moment it is pushed; rewriting
history does not un-publish it.

1. Revoke and reissue at the provider ([Rotating a secret](#rotating-a-secret)).
2. Add the missing rule: `scripts/add_inplace_secret.sh <file> <field>`
3. Confirm nothing else is live:

```bash
bash scripts/verify_encrypted.sh
scripts/scan_verified_secrets.sh                     # trufflehog: what still works
docker run --rm -v "$PWD:/repo" -w /repo zricethezav/gitleaks:v8.30.1 git --no-banner --redact --config /repo/.gitleaks.toml
```

Rewrite history only if the value cannot be rotated. `main`'s
[ruleset](https://github.com/mark-brannan/symphony/settings/rules/21060338)
blocks force pushes; disable it, push, re-enable.

## Lost age key

Prevent it: keep two recipients, stored apart, and never retire the second
(`scripts/rotate_age_key.sh add --generate`).

With a backup:

```bash
mkdir -p ~/.config/sops/age
cp <the backup> ~/.config/sops/age/keys.txt
chmod 600 ~/.config/sops/age/keys.txt
sops --decrypt secrets/symphony.sops.yaml | head -1   # expect readable YAML
```

Without one, nothing in git decrypts. Generate a fresh key, put its public
half in `.sops.yaml`, and re-add each file from live sources: the store from
the running containers and `.env`, the in-place files from their plaintext
copies on disk.

```bash
age-keygen -o ~/.config/sops/age/keys.txt
git add secrets/symphony.sops.yaml signalk/security.json
```

`influxdb_operator_token` has no plaintext copy anywhere; the `captain` login
in the InfluxDB UI is what's left. `~/symphony-backups/` on the boat holds
a plaintext snapshot of the SignalK config, deliberately outside the repo.
