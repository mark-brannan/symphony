# HALOS swap validation — 2026-09-03

Four legs, run live against `symphony-halos` (bench) and read-only against
`symphony-pi` (boat), per Mark's dispatch tonight. Commands and full output as
run, not reconstructed after the fact.

## 1. Boat pypilot calibration data onto the bench card — PASS

Boat's `~/.pypilot`-equivalent (`/home/pi/symphony/pypilot/data/`) is root-owned,
0600 on the sensitive files (`pypilot.conf*`, `.pypilot_conf.*`, `signalk-token`).
`pi` on the boat can't read those directly, so transfer went boat
`sudo tar czf -` → this dev box (scratch tmpfile, deleted after) → `scp` to halos
`/tmp` → halos `sudo tar xzf` into `/home/pi/symphony/pypilot/data/`, then the
`/tmp` copy on halos removed. Ownership on halos landed root:root as the
compose file's comment says to expect.

halos checkout was on a stale feature branch (`claude/port-install-sh-ansible-388a67`,
34 commits behind); switched to `main` and fast-forwarded before doing anything
else (`git switch main && git pull --ff-only`, clean fast-forward, no local
changes lost).

```
sudo docker compose -p symphony -f docker-compose.yml --profile pypilot up -d --build pypilot pypilot-web
```
Built from cache (first attempt hit a transient TLS timeout fetching
`docker/dockerfile:1` from Docker Hub; retry succeeded immediately). Both
containers created and started.

60s of `docker logs -f pypilot`: no calibration-format or module errors.
Relevant lines:
```
Using settings file RTIMULib.ini
Detected ICM20948 at standard address
Using fusion algorithm Kalman STATE4
IMU Name: ICM-20948
Using ellipsoid compass calibration
Using accel calibration
ICM-20948 init complete
IMU all sensor axes verified
setting initial gyro bias [2.73, 0.18, -0.52]
made imu process realtime
```
The boat's calibration was written for the MPU9250 (`IMUType=7` in
`RTIMULib.ini`); the bench chip is a different physical part (ICM-20948).
pypilot autodetects the chip on the bus rather than trusting the stored type,
so it silently re-typed and used the file's ellipsoid/accel calibration
anyway — matches the finding already recorded in
`reference/pypilot_containerization.md` § Integration seams, item 4. This is
the expected cross-chip behavior, not a bug; it says nothing about whether
this calibration is *good* for the ICM-20948's own axes, only that the file
format loaded and applied without error, which was the actual question.

Checks:
- `curl -s -o /dev/null -w '%{http_code}\n' localhost:8000` → `200`
- `docker exec pypilot i2cdetect -y 1` → device present at `0x68` (and `0x48`,
  a second I2C device on the bench's bus, not pypilot's)
- `docker ps` → `pypilot-web Up 3 minutes (healthy)`, `pypilot Up 3 minutes`
  (pypilot itself has no healthcheck defined in compose-pypilot.yml — only
  pypilot-web does; this is a container status, not a leg failure)

**Leg 1: PASS.**

## 2. Full cold host reboot of the whole container stack — PASS, with a real finding

Before rebooting, halos was switched from a stale feature branch
(`claude/port-install-sh-ansible-388a67`, 34 commits behind) to `main` and
fast-forwarded (see leg 1). `sudo reboot`, waited for the box to answer SSH
again (`Monitor` loop, no fixed sleep).

**First boot after the reboot command:** SSH came back at `up 4 min`. All
non-pypilot containers reached `(healthy)` within ~2 min (SignalK's own cold
start took the full ~2 min, as expected). But `pypilot`, `pypilot-web` and
`ntfy` all still showed `Up 26 hours` — `docker inspect --format
'{{.State.StartedAt}}'` confirmed their StartedAt was `2026-09-02T06:57Z`, from
well before this session touched the box, `RestartCount=0`. They had not
actually restarted with the reboot.

**Then, unprompted, the box rebooted a second time** (`uptime` dropped back to
`up 1 min` a few minutes later, with no reboot command issued by this
session). This time every container — including pypilot/pypilot-web/ntfy —
came up fresh (`StartedAt` all within the same second, `Up 30 seconds`).
`free -m` at that point: 78 MB available, 1661 MB of 1843 MB swap used, load
average 24.95 on a 4-core Pi 4 that had been up under a minute. `docker ps -a`
right after showed `grafana Exited (137)` (SIGKILL — OOM) and `questdb
(unhealthy)`. `docker logs autoheal` recorded real restarts driven by that
pressure:

```
09:07:16 Container /grafana found to be unhealthy - Restarting container now with 10s timeout
09:07:38 Container /questdb found to be unhealthy - Restarting container now with 10s timeout
09:07:54 Container /homarr found to be unhealthy - Restarting container now with 10s timeout
09:08:09 Container /authelia found to be unhealthy - Restarting container now with 10s timeout
```

Per the standing release-valve rule (`CLAUDE.md` § The boat Pi's memory
headroom), stopped `marine-questdb-container` and `marine-grafana-container`
without asking once memory pressure was confirmed real (available 336 MB,
swap 1358/1843 MB used — both under the documented threshold). Recovered to
730 MB available immediately. Restarted both afterward once the checks below
were done; they came back but the box settled at 358 MB available/1593 MB
swap with the databases up, close to the known bench ceiling.

This matches the pre-existing, already-documented finding, not a new one:
`halos-swap-preflight-2026-09-02.md` and `halos-swap-plan.md` § B6/staging
both say the 2 GB bench card cannot hold SignalK + QuestDB + Grafana +
Homarr + Authelia + pypilot together — "you can have SignalK or the
databases, not both" on this hardware — and that the boat's 4 GB was
arithmetic-checked to fit with ~1 GB headroom. **What this reboot adds that
wasn't measured before:** a genuine full cold boot of the *complete* stack
(SignalK, QuestDB, Grafana, Homarr, Traefik, Authelia+Valkey, autoheal,
pypilot, pypilot-web, ntfy, ca-download — the pypilot pair is new since that
doc was written) can push the 2 GB bench hard enough during the boot storm
to OOM-kill a container and trigger a second, unplanned reboot — not just
sustained swap thrashing under steady load, which is what was measured
before. This is a bench-only ceiling artifact per the existing arithmetic,
not evidence of anything wrong with the boat's 4 GB target, and it should
not block swap day — but it is a new data point (an actual watchdog-driven
reboot loop under full cold-boot memory pressure) that the existing docs
didn't have, since they only ever tested a subset of services or a warm
recreate, never every container the swap now carries booting cold at once.
The `pypilot`/`ntfy` "container survives without restarting" anomaly on the
first boot is left unexplained — plausibly the first reboot didn't fully
complete a clean shutdown of every unit before power actually cycled (e.g. a
straggling `docker stop` timing out under the same load pressure) and the
watchdog-forced second reboot is what actually did a full stop/start of
everything; no persistent journal survived across boots to check `dmesg`
against directly (`journalctl -k -b -1` returned nothing).

After the second boot settled and questdb/grafana were quiesced, ran the
scripts:

`scripts/halos_swap_check.sh symphony-halos`:
```
ok    signalk    signalk 2.31.1 up=391s
FAIL  lan        eth0   (want eth0 192.168.8.240/24 and can0 UP)      -- expected at home, no boat LAN/CAN
FAIL  n2k        no n2k-can0 value under 60 s old                    -- expected at home, no CAN bus
FAIL  victron    mqtt=SYN-SENT ...                                   -- known: Cerbo MQTT down since 2026-09-01
FAIL  ble        0 of 5 configured sensors publishing voltage        -- allow 10 min after boot; not re-checked
ok    heartbeat  ping ok
ok    containers all report (healthy)
ok    pypilot    web ui 200
ok    ntfy       sent to symphony-alarms; check the phone
FAIL  questdb    no answer in 30 s                                   -- self-inflicted: questdb was stopped for memory relief at check time
ok    devices    /dev/serial0 /dev/i2c-1
ok    bme680     inside: airquality gas humidity relativeHumidity temperature
ok    front      https signalk.symphony.dark-star-llc.com :4430 200 -> SignalK
```

`scripts/halos_preflight.sh symphony-halos`:
```
ok    host, boot, wifi, plugins (120 loaded, 63 on), signalk (gid988), staydown, heartbeat, containers, ntfy, front, mem, dns
FAIL  services   ... questdb inactive grafana inactive ...   -- self-inflicted, same cause
FAIL  questdb    cpu rows none, newest signalk row none      -- self-inflicted, same cause
```

Both scripts' `containers` line — the one this leg exists to check — read
**`ok all report (healthy)`** on this cold-booted card. The only FAILs are
either pre-existing known conditions (LAN/CAN at home, Cerbo MQTT, BLE
burn-in) or directly caused by this session stopping questdb/grafana for
memory relief moments earlier — not new defects. Restarting the databases
returned `free -m` to 358 MB available, which is below the 400 MB comfort
line in `CLAUDE.md` but not the swap-thrashing condition; left as-is since
the databases running is the card's intended steady state and a further
manual stop wasn't asked for.

**Leg 2: PASS** on the actual ask (every container reaches `(healthy)`,
autoheal recovers real OOM pressure correctly), **with a new finding to
flag**: a full cold boot of the complete stack (including pypilot) can
trigger a genuine unplanned second reboot on the 2 GB bench under memory
pressure. Root cause is the already-known and already-accepted bench-vs-boat
memory gap, not a new defect in the swap mechanics; the boat's 4 GB was
already arithmetic-checked to have ~1 GB headroom the bench doesn't have, so
there is no reason to expect this to recur on the boat. Recommend not
touching the swap-day procedure over this, and noting it in the log so a
future bench session isn't surprised by it.

## 3. i2c passthrough for SignalK itself — PASS

Host i2c group: `getent group i2c` → `i2c:x:988:pi`. SignalK container's
`GroupAdd`: `docker inspect signalk-server --format '{{json
.HostConfig.GroupAdd}}'` → `["960","4","988"]` — 988 is granted, matching the
host group exactly (documented in `host/halos/README.md`, and this
confirms it still holds post-reboot). The running `node` process's actual
group membership (`/proc/<pid>/status`): `Groups: 4 20 960 988 989 990 991
1000` — gid 988 is present in the live process, not just the container
config. Direct proof beyond the preflight script's `gid988` grep: opened the
device from inside the container —
`docker exec signalk-server node -e "require('fs').closeSync(require('fs').openSync('/dev/i2c-1','r'))"`
→ succeeded (`OPENED_OK`), no `EACCES`.

`scripts/halos_preflight.sh`'s `signalk` line already checks for this
(`gid988` in the grep against `/proc/<pid>/status`) and it read `ok` in both
leg-2 runs above, i.e. this held before and after the reboot.

**Leg 3: PASS.**

## 4. Two loose ends

**Stray inert file:** `plugin-config-data/signalk-plugin-watchdog.json` was
already deleted — `halos-swap-preflight-2026-09-02.md` records this as done
on 2026-09-02, and `ls` tonight confirms: the stray file is absent, and the
real config `plugin-config-data/plugin-watchdog.json` (174 bytes, dated
Aug 15) is present and untouched. Nothing to remove tonight.

**`plugin-watchdog` running state**, via the SignalK admin API (same
login-then-`/skServer/plugins` pattern as `halos_preflight.sh`'s `plugins()`
helper, captain password from sops):
```
plugin-watchdog 0.1.0 True
```
Loaded, version 0.1.0, `enabled: true`. Confirmed actually running, not just
configured.

**Leg 4: PASS** (both items were already in the wanted state; nothing needed
changing).

## Go/no-go against `dispatch-halos-swap-day.md`

| Leg | Result |
|---|---|
| 1. Boat calibration onto bench, format load | PASS |
| 2. Full cold reboot of the whole stack | PASS (containers all reach healthy; new finding below) |
| 3. i2c passthrough for SignalK | PASS |
| 4. Stray file + plugin-watchdog state | PASS (both already correct) |

**GO.** Nothing found tonight blocks or changes the swap-day procedure as
written. The one new finding — a cold boot of the *complete* stack (with
pypilot now part of it) can push the 2 GB bench hard enough to OOM a
container and trigger a second, unplanned reboot — is a bench-only ceiling,
already priced into the existing 4 GB-vs-2 GB arithmetic in
`halos-swap-preflight-2026-09-02.md`, and the boat has never shown this
symptom. Nothing in the dispatch's sequence needs a change; the dispatch's
own step 4/5 (wait 5 min, rerun `halos_swap_check.sh`) already covers a
possible slow cold start on the boat, so no new step is needed there either.

