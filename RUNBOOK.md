# Symphony systems runbook

Find the symptom in the index, run the section. Design and rationale:
[reference/software_stack.md](reference/software_stack.md). Planned work:
[longer procedures](#longer-procedures).

## Where things are

**Can't get in**
- [Reaching the boat, and which card am I on](#ssh-to-the-boat)
- [Tailscale refuses the connection](#when-tailscale-refuses-the-connection)
- [ssh works but a page hangs](#a-page-hangs-but-ssh-works--mtu)
- [Names stop resolving on the boat wifi](#hostnames-stop-resolving-on-the-boat)
- [No way to log in to SignalK or Grafana](#no-way-to-log-in)

**Nothing is reporting**
- [No position, no instruments](#nmea-2000-input)
- [Batteries and tanks silent](#ble-sensors-silent-after-a-reboot)
- [One sensor connects and delivers nothing](#a-ble-sensor-connects-but-delivers-nothing)
- [SignalK errors about missing packages](#signalk-errors-about-missing-packages)

**The box is sick**
- [What is running, what is unhealthy](#container-health)
- [Out of memory](#the-pi-is-out-of-memory)
- [The Pi keeps hard-resetting](#the-pi-keeps-hard-resetting)
- [Stopping and starting SignalK](#stopping-signalk)
- [Reinstalling SignalK](#reinstalling-signalk)

**A plugin is misbehaving**
- [It isn't in the config UI](#a-plugin-isnt-in-the-config-ui)
- [Every install fails on a `file:` dependency](#every-plugin-install-fails-on-a-file-dependency)
- [A fork keeps reverting](#a-plugin-fork-keeps-reverting)

**Changing something**
- [Compose here, systemd aboard](#two-deployments)
- [Deploying a change to the boat](#deploying-a-change-to-the-boat)
- [Before a shutdown or power-off](#silencing-the-alarms-for-planned-work)
- [A screen on the Pi](#a-desktop-on-the-boat-pi-on-demand)
- [The resident Claude session](#the-resident-claude-session)

**Secrets**
- [Rotating a secret](#rotating-a-secret)
- [A hook blocks your commit](#a-hook-blocks-your-commit)
- [A secret was committed in plaintext](#a-secret-was-committed-in-plaintext)
- [Lost age key](#lost-age-key)

**Not an emergency**
- [Longer procedures](#longer-procedures) — bring-up, secrets, SSO, dashboards, sensors, tests

---

## SSH to the boat

```bash
ssh pi@symphony-pi          # boat card
ssh pi@symphony-halos       # HALOS card
```

Tailscale SSH, so no key files. Plain `symphony` does not resolve. Only
tailnet devices get in; if only WSL runs tailscaled, the Windows side of that
machine is not on it.

Both cards answer `hostname` with `signalk`. To know which one you are on:

```bash
tailscale status --self=true --peers=false    # symphony-pi or symphony-halos
```

*Verify:* `curl -s http://symphony-pi:3000/signalk` returns JSON.

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
are fine.

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

A router that lost its config lost the override too: restore from
[runbooks/secrets.md](runbooks/secrets.md#router-config-backup).

## No way to log in

Dex fronts GitHub and Google, so with no uplink neither answers. The local
password logins always work: `captain` in SignalK and InfluxDB, the Grafana
superadmin. They are in the store:

```bash
sops --decrypt --extract '["signalk_captain_password"]' secrets/symphony.sops.yaml
```

After about 60 days offline browsers warn about the certificate until internet
returns; accept it. An owner login landing as `readonly` is an SSO fault:
[runbooks/sso.md](runbooks/sso.md).

---

## Two deployments

Commands here are written for compose. On the boat Pi, SignalK, InfluxDB,
Grafana and Caddy are systemd units; Dex, QuestDB, ntfy, autoheal,
pypilot and pypilot-web are containers. Translate:

| Compose | Boat Pi |
|---|---|
| `docker compose up -d <svc>` | `sudo systemctl start <svc>` |
| `docker compose restart <svc>`, `--force-recreate` | `sudo systemctl restart <svc>` |
| `docker compose stop <svc>` | `sudo systemctl stop <svc>` |
| `docker exec grafana grafana cli …` | `sudo grafana cli …` |
| service `grafana` | unit `grafana-server` |

Ports are the same on both: SignalK 3000, Grafana 3001, InfluxDB 8086.
Containers read the rendered `.env`; in a shell, source it:

```bash
cd ~/symphony && set -a && . ./.env && set +a
```

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

## The Pi is out of memory

Real pressure is `available` under about 400 MB, or the swap counters
climbing between two reads a minute apart — not load average on its own.

```bash
free -m
grep ^pswp /proc/vmstat
```

InfluxDB and Grafana are the release valve, roughly 600 MB between them;
QuestDB, a container here, can go too.

```bash
sudo systemctl stop influxdb grafana-server
docker compose stop questdb
```

Stop, never `disable`: they come back at the next reboot, which is what we
want. The pressure is normally transient — an `npm install`, a rebuild.

## The Pi keeps hard-resetting

Chromium autostarted on this Pi wedges the v3d driver, display attached or
not, and the board eventually hard-resets. Its autostart entry
`freeboard.desktop` is parked in `~/.config/autostart-disabled/`; keep it
there.

```bash
journalctl -b -k | grep -c "Resetting GPU for hang"    # want 0
ps -eo pid,stat,comm | awk '$2 ~ /D/'                  # want no kworker
```

A climbing count means something is driving the GPU; stop it. Only a reboot clears the blocked kworkers.

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

**Never run `sudo openplotter-signalk-installer`,** and never OpenPlotter's
Settings → Signal K → **Reinstall**: the installer removes the Node runtime
and writes a launcher path the `pi` service cannot read, and Reinstall runs
`rm -rf ~/.signalk` with no prompt and no backup. Settings → Signal K →
**Update** is safe. Do the npm half as `pi`:

```bash
sudo systemctl stop signalk.socket signalk.service
npm install -g signalk-server --no-audit --no-fund
printf '#!/bin/sh\n%s/lib/node_modules/signalk-server/bin/signalk-server -c %s $*\n' "$(npm config get prefix)" "$HOME/.signalk" > ~/.signalk/signalk-server && chmod 775 ~/.signalk/signalk-server
sudo systemctl reset-failed signalk.service && sudo systemctl start signalk.socket signalk.service
```

The install takes 30–60 minutes and logs nothing while extracting; watch
`du -sh ~/.npm-global/lib/node_modules/signalk-server` grow instead.

*Verify:* `systemctl is-active signalk` and `journalctl -u signalk -f` reaches plugin loading with no `Cannot find module`.

## NMEA 2000 input

```bash
curl -s localhost:3000/signalk/v1/api/vessels/self/navigation/position
ip -br link show can0                  # want UP
timeout 5 candump -n 20 can0           # want frames
```

Expect `"$source": "n2k-can0.<addr>"` and coordinates that move between calls.
A `$source` of `signalk-fixed-position` means the GPS is quiet and Position
Keeper is replaying the last fix. Read `$source`, not the presence of a
position.

Don't unset `uniqueNumber` (pinned `368391` in the connection's `subOptions`);
the Pi would appear as a new device on the bus each save.

## SignalK errors about missing packages

A truncated plugin tree on the boat. **Never run `npm install` over a broken
tree**; npm treats half-written packages as installed, and a single pass
deletes the tree when `better-sqlite3`'s build fails, which it always does
here. Move it aside and install in two phases:

```bash
free -m                                # want > 2 GB available; else stop influxdb and grafana-server
sudo systemctl stop signalk.socket
sudo systemctl stop signalk.service
mv ~/.signalk/node_modules ~/.signalk/.node_modules_old
cd ~/.signalk
npm install --ignore-scripts --no-audit --no-fund   # phase 1: the tree
npm rebuild                                          # phase 2: natives; exits non-zero and that is fine
```

Watch with `vmstat 5`: high `wa` is SD writes and finishes; `si`/`so` non-zero
with `available` falling is swapping, so free more memory. Don't kill the
install. If a previous run was interrupted, `npm cache clean --force` first.

*Verify:*

```bash
find ~/.signalk/node_modules -name '*.node' | wc -l   # dozens, not 0
ls -d ~/.signalk/node_modules/@mapbox/node-pre-gyp    # must exist
sudo systemctl reset-failed signalk.service && sudo systemctl start signalk.socket signalk.service
```

## BLE sensors silent after a reboot

Nothing under `electrical.batteries.*` and one `Uncaught exception: Error: write EPIPE` from `dbus-next` at startup.

`signalk-ble-check.timer` restarts SignalK by itself when the plugin is loaded
but publishing nothing: six minutes after boot, then every fifteen, at most
three times per boot.

```bash
journalctl -t signalk-ble-check --since -1d -o cat                      # what the timer did
journalctl --since -1h | grep "not authenticated soon enough"           # present = this fault
grep -c getBluetoothSession ~/.signalk/node_modules/bt-sensors-plugin-sk/index.js   # want > 0
```

Grep the copy SignalK loads, not the fork checkout. A count of 0 means SignalK
runs a build without the fix: relink it per [A plugin fork keeps
reverting](#a-plugin-fork-keeps-reverting), then restart:

```bash
sudo systemctl stop signalk.socket
sudo systemctl stop signalk.service
sudo systemctl start signalk.socket
curl -s -o /dev/null http://localhost:3000/signalk/
```

*Verify,* after a few minutes — each sensor's `name` appears as its own `$source`:

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

Identify a pack by MAC, not name; both house batteries advertise as `DP04S007L4S200A`.

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

---

## Deploying a change to the boat

```bash
ssh pi@symphony-pi
cd ~/symphony && git pull
docker compose --profile tls up -d questdb ntfy dex autoheal pypilot pypilot-web
sudo host/install.sh      # only if anything under host/ changed; idempotent
```

That container list is every container the boat runs. **Always name the
services.** A bare `docker compose up -d` starts containers that fight the
native units for ports 3000, 8086, 3001 and 443.

*Verify:* the [container health](#container-health) check about 90 s later.
After a `host/` change, also confirm the watchdog took (expect 30s, `30s`, `30`):

```bash
journalctl -b | grep -i "hardware watchdog"
systemctl show -p RuntimeWatchdogUSec
cat /sys/class/watchdog/watchdog0/timeout
```

`boat-hourly-sync.timer` fetches hourly and never merges; the heartbeat body
carries its drift line. `behind` is normal; `ahead`, `diverged` or any
`stashed` count needs a person before you pull.

```bash
systemctl status boat-hourly-sync.timer                  # active, and a next run scheduled
journalctl -t boat-hourly-sync -n 5 --no-pager -o cat   # symphony: fetched, N behind origin/main
sudo -u pi GIT_SSH_COMMAND='ssh -o BatchMode=yes -o ConnectTimeout=20' git -C /home/pi/symphony fetch origin   # on `fetch failed`
~/.local/bin/dotfiles-sync.sh --status                  # dotfiles sync separately
```

## Silencing the alarms for planned work

From a laptop, before a shutdown, card swap or power-off:

```bash
scripts/monitoring_snooze.sh status
scripts/monitoring_snooze.sh pause pi
```

Don't resume by hand; the next ping un-pauses it.

*Verify:* after the box is back, `status` shows the check `up`. Still `paused`
ten minutes after boot means the timer isn't running aboard:

```bash
journalctl -t boat-heartbeat -n 5            # expect: ping ok
```

`ping failed` is a dead endpoint or no uplink; check the uplink first. No
`/etc/boat-heartbeat.json`, no pings at all.

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

**In-place value:** change it in the SignalK admin UI, then `git add <file> &&
git commit`. If the store mirrors it (`influx_token` does), update both.

**Grafana / InfluxDB user passwords:** edit the store, then re-run
`scripts/provision_grafana_users.sh` / `scripts/provision_influxdb.sh`.
InfluxDB tokens rotate differently: [runbooks/secrets.md](runbooks/secrets.md#rotating-an-influxdb-token).

## A hook blocks your commit

```bash
bash scripts/check_clone_setup.sh      # names the fix for every gap
```

- **"a secret-bearing file is staged in the clear"** — the clean filter isn't wired. `bash scripts/setup-git-filters.sh`, re-stage.
- **"a whole-file secret store is staged unencrypted"** — `sops --encrypt --in-place <file>`, re-stage.
- **"looks like a cleartext credential"** — wire it with `scripts/add_inplace_secret.sh`, or rename the field if it isn't a secret.
- **gitleaks finding** — look at the file and line. A true false positive gets a narrow `.gitleaks.toml` allowlist entry with `condition = "AND"`.
- **"sops config is inconsistent"** — `.sops.yaml` and `.gitattributes` disagree; the message says which.

A blocked **push** names a commit and a file:

```bash
git show <commit>:<file>
bash scripts/setup-git-filters.sh
git rebase -i <commit>~1
git push
```

If that commit was already pushed, the secret is out: [A secret was committed
in plaintext](#a-secret-was-committed-in-plaintext).

Break glass: `SKIP=<hook-id> git commit`, `git commit --no-verify`,
`git push --no-verify`. CI still scans full history on the pull request.

## A secret was committed in plaintext

**Rotate first.** It is compromised the moment it is pushed; rewriting history
does not un-publish it.

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
in the InfluxDB UI is what's left.

---

## Longer procedures

Planned work, off the emergency path:

- [Bringing up a host](runbooks/host_bringup.md) — tooling, key, repo, services, Ansible, host files, QuestDB, heartbeat.
- [Swapping the HALOS card](runbooks/halos_swap.md)
- [Secrets](runbooks/secrets.md) — adding, removing, InfluxDB token, age key, pseudonyms, router backup.
- [SSO](runbooks/sso.md) — Dex, OAuth and DNS setup, access grants.
- [Adding a BLE sensor](runbooks/ble_sensors.md)
- [Grafana dashboards](runbooks/grafana_dashboards.md)
- [pypilot](runbooks/pypilot.md)
- [Testing the DSC / AIS distress chain](runbooks/distress_test.md)
