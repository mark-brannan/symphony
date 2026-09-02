# HALOS B3 execution findings — 2026-09-02

B3a, B3b and B3c executed against the halos card (`ssh pi@192.168.0.193`).
Plan: `halos-swap-plan.md` on branch `claude/halos-boat-swap-trial-9e5d36`
(PR #33 — not on main, which is why this file is separate).

## Outcome

- **B3a done.** Boat `.signalk` state rsynced; verified by dry run (only live
  runtime counters differ). 124 deps, 105 plugin-config files, `red/`,
  3 users incl. `captain`, `n2k-can0` provider with uniqueNumber 368391.
  `package.json.halos` saved aside.
- **B3b done.** `bt-sensors-plugin-sk` 1.3.8-beta11 and
  `signalk-plugin-watchdog` 0.1.0 in `local-plugins/`.
- **B3c done with residue.** package.json repointed to the two `file:` entries;
  three plugins disabled; `venus.json` MQTT host → 192.168.8.107.
  Final clean install: 2773 packages in 7 min, install and rebuild both exit 0.
  Measured after: 118 installed plugins, 66 enabled.

## Findings the plan did not anticipate

**1. The HALOS image blocks npm install scripts.** npm in
`ghcr.io/halos-org/signalk-server-docker:v2.31.1-halos.3` reports
`30 packages had install scripts blocked because they are not covered by
allowScripts`. Native bindings therefore never compile, and six plugins fail
to start: `i2c-reader`, `@oehoe83/signalk-raspberry-pi-bme680`,
`signalk-instrument-light-plugin`, `signalk-notifications`,
`sk-propulsion-state` (all "Could not locate the bindings file") and
`signalk-speedtest` (`lzma-native`). Several are real boat function — the
BME680 environment sensor and i2c reader among them. This is structural, not
a bad install: `--ignore-scripts` then `npm rebuild` is the plan's recipe and
cannot work while allowScripts blocks the same scripts. **Blocks the swap
until resolved.**

**2. `signalk-plugin-watchdog` has no config file**, so it is installed and
linked but never starts. Needs a `plugin-config-data` entry to be enabled.

**3. The 2 GB Pi 4 cannot do this install with the stack running.** Four
attempts failed: one hard reset of the whole box (no persistent journal, so
cause unproven; no undervoltage or thermal throttle, 60s hardware watchdog
armed), one npm JS-heap OOM, one killed when the SignalK unit tore its own
container down mid-`docker exec`. It succeeded only with six container units
stopped, run in a throwaway container rather than `docker exec`, under
`systemd-run` so an SSH drop could not kill it. **The plan's `docker exec`
recipe should be replaced by the throwaway-container form**, and the memory
caveat is a hard precondition, not a note.

**4. B3c's verification cannot be run as written.** `/skServer/plugins`
returns 401 — it needs admin auth. Substitute used: plugin counts from
`node_modules` keywords plus `plugin-config-data`, and the journal grep.
Also note `localhost` resolves to `::1` on halos and fails; use `127.0.0.1`.

**5. `signalk-notification-player` spams continuously** — `spawn mpg321
ENOENT`; the binary is not in the HALOS image.

**6. SignalK exits code 0 roughly every 3 minutes** and is restarted by
systemd. Cause not identified. `signalk-healthcheck` was ruled out — it has
no `process.exit`; it only raises notifications. Open.

## Not done

B1 (boot config, PiCAN-M overlays, `can0`) is untouched, so `can0` does not
exist and the `n2k-can0` provider errors continuously. That is expected at
this stage, not a B3 defect.

## Update — native bindings and audio, 2026-09-02

**The `allowScripts` warning was a red herring.** The real blocker is that
`ghcr.io/halos-org/signalk-server-docker:v2.31.1-halos.3` ships **no
compiler** — only `python3`; no `make`, `gcc`, `g++` or `cc`. Enabling
install scripts could not have helped. The boat compiles these natively
(node 22, ABI 127, gcc/make/g++ present); the HALOS container is node 24,
ABI 137, toolchain-free.

**Fix applied:** build the native modules in a toolchain image at the *same*
node ABI, writing into the shared data volume, then let the HALOS container
load them. `node:24-bookworm` reports ABI 137, matching. Targets:
`i2c-bus`, `epoll`, `sqlite3`, `serialport`, `lzma-native` — between them
they cover `signalk-i2c-reader`, the BME680 plugin (`bme680-sensor`),
`sk-propulsion-state` (`onoff`), `signalk-instrument-light-plugin`
(`serialport`), `signalk-notifications` (`sqlite3`) and `signalk-speedtest`.

Do **not** run bare `npm rebuild`: it hits `signalk-victron-ble`, whose
build script needs `python3-venv` (absent), fails, and aborts the whole run
before reaching anything useful. Rebuild the named packages only.

**Audio: HALOS has no server-side sound and does not intend one.** Its docs
never mention audio; `signalk-server-docker`'s Dockerfile has no `apt-get`
at all. HALOS's actual alarm mechanism is browser-side — `@halos-org/skip`
ships `sound.service.ts` (Web Audio) with `alarm/alert/warn/emergency` mp3
assets and a notifications settings UI. The container also lacks audio-group
access (`group_add` grants gids 960 and 4; the host's `audio` gid is 29), so
a player inside it could not open `/dev/snd` even if installed.
`signalk-notification-player` therefore disabled on the halos card; the
boat's existing self-hosted ntfy + `signalk-ntfy` remains the off-box path.
Host-side playback is possible if ever wanted (`mpg123`, `aplay`,
`speaker-test` are all on the host and `pi` is in `audio`) but is blocked on
an unverified precondition: whether any speaker is physically connected.

**`signalk-plugin-watchdog` enabled** — it had no `plugin-config-data` entry
so it never started. Schema has no required fields; created with defaults.

## Correction: the boat's config is not golden — 2026-09-02

B3a copies the **boat's** `.signalk` state onto the halos card, so everything
verified above is verified against the boat, not against this repo. Mark's
standing position: neither side is authoritative; the repo's `signalk/` tree
is the intended golden source and reconciling the two is unfinished work.
A problem found on either side needs investigation, a decision from Mark, or
both — not an assumption that the boat is right.

Measured divergence, 2026-09-02:

- repo `signalk/plugin-config-data`: **64** configs
- boat (now on halos): **84** configs
- **17 exist only in the repo**, including `signalk-pushover-notification-relay`
  (enabled, with credentials), `signalk-mob-notifier`, `signalk-dsc`,
  `signalk-questdb`, `signalk-grafana`, `open-meteo`, `signalk-rules`,
  `vedirect-signalk`, `signalk-doctor`.
- **30 exist only on the boat**, including `i2c-reader`, `barometer`,
  `signalk-barometer-trend`, `signalk-triplogger`, `signalk-engine-hours`,
  `signalk-n2k-switching`, `pypilot-autopilot-provider`, `airmar-plugin`.

Neither side is a superset. Two consequences already hit this session:

1. **A Pushover "deployment gap" I reported here was wrong — retracted.**
   There are two distinct Pushover paths and I conflated them:
   - **Role 1 (host liveness):** live on the boat and working.
     `/usr/local/sbin/boat-heartbeat` lines 41-127 read
     `pushover_api_token`/`pushover_user_key` and implement the soft-warning
     tier and escalation; `boat-heartbeat.timer` is active and firing every
     ~5 min. Mark configured and tested this, and it still runs.
   - **Role 2 (SignalK notification bus -> Pushover):**
     `signalk-pushover-notification-relay` is genuinely not on the boat -
     absent from `package.json`, `node_modules` and `plugin-config-data`.
     `monitoring_decisions.md` Role 2 lists it under **Add**, i.e. planned,
     and the board card "Audit and fork signalk-pushover-notification-relay"
     is still open. So this is the documented plan, not a regression.
   The repo's `signalk-pushover-notification-relay.json` (commit 67a7222) is
   repo-side prep for an uninstalled plugin. Nothing reverted.
   **Lesson: check any monitoring claim against `monitoring_decisions.md` and
   `monitoring_posture.md` before reporting it — those docs already assign
   roles and would have caught this.**
2. **The watchdog config I created may be inert.** The boat tree already has
   `plugin-watchdog.json` *and* I added `signalk-plugin-watchdog.json`. Which
   filename SignalK uses depends on the plugin's registered id, which I did
   not confirm. **Unresolved — do not assume the watchdog is running.**

Reconciling these 47 differing configs is its own task and is not attempted
here.

## The memory failures are a staging-rig property, not the target — 2026-09-02

Measured tonight:

| | staging rig (`halos-pi4`, 192.168.0.193) | swap target (`symphony-pi`) |
|---|---|---|
| board | Raspberry Pi 4 Model B Rev 1.5 | Raspberry Pi 4 Model B Rev 1.5 |
| RAM | 1844 MB | 3796 MB |
| boot media | SD card | SD card (`mmcblk0`, 29.5 G) |

Same board, twice the RAM, and the boat boots from SD — so the card swap is
exactly the mechanism, and **the HALOS card will run on 4 GB, not 2 GB.**

Consequences:

- Every memory failure recorded above — the hard reset, the npm heap OOM,
  needing six container units stopped, and sshd refusing banner exchange
  under load — is a property of the **staging box**, not of HALOS and not of
  the destination. They are staging pain, not swap risk.
- The ~3-minute restart loop is most likely the same thing: the healthcheck
  probe *succeeds* but overruns its 10 s timeout because the box is slow
  (13.2 s measured on one API call), so `autoheal` restarts a healthy
  server. On 4 GB with the same container set this may simply not occur.
  **Unproven until the card is in the boat Pi — but it is the leading
  hypothesis and it is testable by the swap itself.**
- **The kanban card's inference "HALOS implies the HALPI2" does not follow.**
  It reasons from the 2 GB staging box to the hardware decision, but the
  card's destination is the existing 4 GB boat Pi. Whether HALOS needs new
  hardware is precisely what the trial is for, and the trial does not
  presuppose a purchase.

What this does *not* excuse: the no-compiler finding is structural and
travels with the image to any host, and the plan's `docker exec` and
verification-command defects are real regardless of RAM.

## Monitoring-posture findings from the repo/boat config diff — 2026-09-02

Found while diffing the repo's `signalk/plugin-config-data` (64 configs)
against the boat's (84). Checked against `reference/monitoring_decisions.md`
and `monitoring_posture.md` before reporting, per Mark's instruction.

**1. Both anchor-alarm plugins are installed on the boat but disabled.**
`hoekens-anchor-alarm` and `signalk-anchoralarm-plugin` are in
`~/.signalk/node_modules` and have **no `plugin-config-data` entry at all**.
Verified this means disabled, from signalk-server source rather than
assumption: `isEnabledByPackageEnableDefault` (`src/interfaces/plugins.ts`
:1089) enables a config-less plugin only when its package.json carries
`signalk-plugin-enabled-by-default`; `hoekens-anchor-alarm` has no such key
and `signalk-anchoralarm-plugin` sets it `false`. When a plugin *is*
default-enabled the server persists a config file (`:1005`) — and none
exists. Corroborating: two days of `journalctl -u signalk` contain no anchor
activity, only `/admin/assets/Anchor-*.js` fetches, and `baseDeltas.json`
holds zero anchor zones.

To be fair to the docs: `monitoring_decisions.md` Role 2 calls
hoekens-anchor-alarm "alive", meaning actively published on npm **[verified —
npm registry]**. It never claims the plugin is enabled aboard. So this is a
**gap the monitoring docs do not currently record**, not a contradiction of
them. It matters because Role 2 names "the dragging-anchor-at-night case" as
the thing the notification bus exists for.

**2. `signalk-mob-notifier` and `signalk-dsc` are enabled in the repo and
absent from the boat.** Not installed, no config, nothing in `package.json`.
Both are safety-of-navigation. `monitoring_decisions.md` mentions
mob-notifier as part of the Role 2 bus; the board separately carries
"Research MOB detection options" and the standing rule never to live-test the
DSC emergency button.

**Neither of these is a swap blocker** — they are pre-existing boat state that
the swap copies faithfully. They are recorded here because the card carries
them onto HALOS unchanged, so the trial will reproduce the same gap.

**Decision needed from Mark** (not actionable by a session): whether the
anchor alarm should be enabled and configured, and whether mob-notifier and
dsc should be installed on the boat to match the repo. All three are his
calls about what the boat should do, not config drift to silently reconcile.

## Why the staging box fails and the boat should not — measured arithmetic

Measured 2026-09-02:

- **SignalK with this plugin set needs ~1246 MB RSS.** Boat `signalk` node
  process: RSS 1246 MB, uptime 9h28m, `NRestarts=0`, `is-active` = active.
  The same ~118 plugins the halos card now carries.
- **HALOS's own container stack plus OS costs ~1000 MB.** Derived from the
  staging box with everything up: 1844 MB total, 845 MB available, SignalK
  not yet loaded.

So a HALOS box running this plugin set needs roughly **1000 + 1246 ≈ 2250 MB**.

| host | RAM | need | verdict |
|---|---|---|---|
| `halos-pi4` staging rig | 1844 MB | ~2250 MB | **cannot fit — thrashes, as observed** |
| `symphony-pi` boat (swap target) | 3796 MB | ~2250 MB | fits, ~1.5 GB headroom |

This explains every failure recorded above without appealing to anything
about HALOS itself, and it predicts the restart loop: SignalK cannot reach a
steady state on the staging box, so the healthcheck overruns its 10 s
timeout and `autoheal` restarts it, forever.

**Observed end state of the staging box, 2026-09-02 ~06:4x UTC:** ports 22,
80, 443 and 3000 all still accept TCP, but nothing completes a request — no
SSH banner, no HTTP response — for 25+ minutes. The kernel is queueing
connections userspace cannot serve. That is memory exhaustion, and it is the
predicted outcome of the table above.

**Caveats, stated rather than hidden.** The ~1000 MB figure is derived from
one `free -m` reading, not from per-container accounting; `opencpn` and
`avnav` are GUI apps whose idle footprint was not measured separately. The
boat also currently runs its own services (InfluxDB, QuestDB, Dex, Caddy,
Grafana) which HALOS replaces rather than adds to, so the comparison is
HALOS-stack-vs-native-stack, not additive. The headroom figure is therefore
approximate. It is not approximate enough to change the verdict: 2250 MB does
not fit in 1844 MB, and does fit in 3796 MB.

**What this means for the swap decision.** The staging box is not a valid
predictor of swap success, and its failures should not be read as HALOS
failures. Conversely, staging cannot fully rehearse the running system on
this hardware — the card can be *built* and its filesystem verified at home,
but HALOS-under-load can only be observed once the card is in the 4 GB boat
Pi. That is an argument for doing the swap, not against it.

## B1b has a second effect nobody flagged: it activates QuestDB's memory cap

Read from `halos-org/halos-marine-containers` (shallow clone, 2026-09-02):

- **`apps/signalk-server/docker-compose.yml` sets no `mem_limit`** and no
  `deploy.resources.limits`. SignalK is uncapped, so nothing will OOM-kill it
  at its ~1246 MB working set. Good — this was worth confirming before the
  swap, because B1b makes limits real.
- **`apps/questdb/docker-compose.yml:110` sets
  `mem_limit: ${QUESTDB_MEMORY_LIMIT:-768m}`**, and HALOS's own comment
  (lines 33-40) says it is currently inert: *"It cannot read mem_limit below,
  because Raspberry Pi OS boots with cgroup_disable=memory and there is no
  memory controller to read — so on a 4 GiB board it reserves 1 GiB and grows
  into it. Measured on a HALPI2: 312 MB of committed heap... Capping at 192m
  (what a working 768m limit would have produced) returns 43 MB of RSS."*

**B1b adds `cgroup_enable=memory cgroup_memory=1` to `cmdline.txt`, so that
limit starts being enforced.** Verified on the staging card: `memory` is now
present in `/sys/fs/cgroup/cgroup.controllers`.

This is an improvement, not a regression, and it is what HALOS intends — the
comment describes the enforced behaviour as the desired one and reports it
measured *better* (43 MB RSS vs 312 MB committed heap). It also slightly
improves the memory arithmetic above in the boat's favour.

It is recorded because it is non-obvious: a boot-config change in B1 silently
alters the runtime behaviour of a container in B4, and the only warning sits
in a comment inside a third-party repo. Anyone reviewing B1b should know it
does more than "make `mem_limit` work in general" — it specifically changes
how much memory QuestDB takes, and the JVM must be container-aware for that
to land softly. **Not yet observed on real hardware; QuestDB has not been
watched under an enforced cap on this card.**

## Checked: wiping the data volume's node_modules did not destroy HALOS's baked plugins

This looked like a real risk after the clean reinstall, so it was verified
against `halos-org/signalk-server-docker` rather than assumed.

HALOS bakes its curated set into
**`/home/node/signalk/node_modules/signalk-server/node_modules/`** — the
*image's* signalk-server package root (`Dockerfile:103-104`), chosen
deliberately because "Signal K discovers modules under `<appPath>/node_modules`
... not the top-level node_modules, where a plain npm install would hoist
them."

The `rm -rf` was against `$D/node_modules`, i.e. the **data volume** at
`/home/node/.signalk/node_modules`. Different path. **Nothing baked was
touched**: `@halos-org/skip` (which carries the browser-side alarm audio),
`@signalk/freeboard-sk`, `@signalk/charts-plugin`,
`signalk-questdb-history-provider`, `@signalk/signalk-node-red` and the rest
of `plugins.list` are intact. The audio recommendation above is unaffected.

One consequence to be aware of rather than fix: the README states the data
volume "shadows the image copy and wins permanently". Where the boat's
`package.json` overlaps HALOS's curated list —
`signalk-anchoralarm-plugin`, `signalk-to-influxdb2`,
`signalk-n2kais-to-nmea0183`, `@signalk/signalk-node-red`, others — the
card now runs **the boat's versions, not HALOS's curated ones**. That is the
inevitable consequence of B3a copying the boat's state wholesale, and it is
another instance of the "the boat is not golden" problem: the trial will
exercise boat-pinned plugin versions rather than the set HALOS tests.
Worth a deliberate decision later; not a swap blocker.

---

## Session `handoff-halos-b3-62a913-a6`, 2026-09-02 ~06:45–07:00 UTC

Successor to the B3 session, working the handoff's items 2 and 3.

### Change made: stopped the `homarr` container

Found the staging Pi 12 min after Mark's ~07:40 BST power-cycle at **270 MB
available, 1124 MB swap in use, actively paging** (`pswpin` 1174243 /
`pswpout` 1955669).

Cause: **the reboot undid the stops.** `homarr` was running again as part of
`halos-core-containers.service` (Traefik, Authelia, Homarr), costing ~195 MB
(`next-server` 166 MB + `tasks.cjs` 28 MB). This is exactly the trap the
project CLAUDE.md records — a `stop` is deliberately not a `disable`, so it
does not survive a reboot. **Any session power-cycling this box must re-stop
the heavy units afterwards.**

Action: `docker stop homarr` (not the systemd unit — that would also stop
Traefik and Authelia). Result: **534 MB available, swap 1124 -> 651 MB and
draining.** `opencpn`, `avnav`, `questdb` and `grafana` were already not
running.

### Confirmed: the watchdog's stray config file is gone

`plugin-config-data/` holds `plugin-watchdog.json` (the live config, matching
the real plugin id) and a `plugin-watchdog/` data dir. The inert
`signalk-plugin-watchdog.json` is **deleted** — loose end 1 in the preflight
is closed. Live config:

    {"enabled": true, "configuration": {"checkIntervalSeconds": 60,
     "graceSeconds": 600, "stallSeconds": 0,
     "expectPlugins": ["bt-sensors-plugin-sk"]}}

`plugin-watchdog/known-producers.json` is dated Aug 26 — **not** evidence
either way: `saveState()` only writes when the producer set changes.

### Confirmed: exactly one plugin fails to start

From the container log, filtering the `can0` retry spam:

- `signalk-instrument-light-plugin failed to start: Could not locate the
  bindings file` — the one expected failure. Leave it.
- Not failures, but noted: `i2c-reader: devices config is missing`;
  `WARNING: found multiple copies of plugin with id signalk-to-noforeignland`;
  `signalk-plugin-internet-speed` throws an unhandled rejection because the
  `speedtest` binary is absent from the image.

### Measured: plugin totals (handoff item 3)

Authenticated `GET /skServer/plugins` as `captain` (unauthenticated gives
401; `allow_readonly: true` covers the *data* API only, not `/skServer`):

- **120 plugins present, 63 enabled.** The handoff expected ~118 / ~66; the
  shortfall is the three plugins B3c deliberately disabled plus
  `signalk-notification-player`. Nothing unaccounted for.
- `plugin-watchdog` v0.1.0 (`packageName` `signalk-plugin-watchdog`) is
  **present and enabled**, as is `bt-sensors-plugin-sk` v1.3.8-beta11.

**`statusMessage` on this endpoint is not usable as evidence.** Only 2 of the
63 enabled plugins carry the field at all, and both carry `''`. It is not the
case that 61 plugins are dead; the list endpoint simply does not surface live
plugin status on this server version. `/skServer/providerStatus` does not
exist here either. Do not read an empty `statusMessage` as "did not start" —
this session briefly did, and was wrong.

### Corrected: the healthcheck restart loop is fixed, not ongoing

A `docker ps` reading of "Up About a minute" at ~07:14 UTC looked like the
~3-min loop continuing. It was not. Evidence:

- `autoheal`'s last restart of the container was **06:45:26 UTC** and it has
  not fired since.
- `docker inspect`: `StartedAt 07:12:50Z`, `ExitCode 0`, `RestartCount 0`,
  `Health.Status healthy`, `Health.FailingStreak 0`.
- The live healthcheck is now
  `curl -sf http://127.0.0.1:3000/signalk`, **interval 30 s, timeout 30 s,
  start_period 900 s, retries 3**.

So the 07:12:50 start is the `symphony.override.yml` drop-in from session
`symphony-pr-33-review-601c06-0a` being applied, not another autoheal kill.
That override supersedes the B3 handoff's "do not pre-edit the healthcheck"
instruction: the handoff's objection was that an `apt upgrade` silently
reverts a package-managed compose file, and a systemd drop-in plus override
file is not subject to that. No objection from this session.

### Still open at the time of writing

- Watchdog **running** state (handoff item 2). Still unconfirmed, but now
  testable: `graceSeconds` is 600 and SignalK started cleanly at 07:12:50Z,
  so if the watchdog is ticking it must log
  `ALERT: plugin bt-sensors-plugin-sk enabled but has published no deltas`
  at about **07:22:50Z** (no BT sensors are in range at home). Absence of
  that line after ~07:23 is real evidence the plugin is not running; before
  it, absence proves nothing.
- The i2c container-access test (handoff item 1) remains blocked on Mark
  wiring the BME680.

### Coordination

Messaged `symphony-pr-33-review-601c06-0a` twice; the first did not arrive.
Staging-box work parked pending their reply, to avoid two sessions bouncing
SignalK and each misreading the other's restart as the healthcheck loop.

### CONFIRMED DEFECT: the SignalK container cannot open `/dev/i2c-1`

The handoff called this "the most likely failure" and expected it to need a
sensor on the bus. It does not — the permission check fails before any
hardware is touched, so this was provable at home, today.

Measured on the card:

    host:      i2c:x:988:pi          /dev/i2c-1 -> crw-rw---- 1 0 988
    container: user=node uid=1000, privileged=true, group_add=["960","4"]
               groups=node,4(adm),20(dialout),960,989(spi),990(i2c),991(docker)
    result:    PermissionError: [Errno 13] Permission denied: '/dev/i2c-1'

Root cause, and the reason it looks fine at a glance: **the container image
has its own `i2c` group at gid 990, and the host's is gid 988.** The `node`
user *is* in a group called `i2c` inside the container, which reads as
correct in `id` output and is worthless — DAC on the bind-mounted host device
node is checked against the host gid 988, which nothing grants. `group_add`
supplies 960 and 4 (`adm`); neither is 988. `privileged: true` does not
rescue it, because the process runs as non-root `node` and so holds no
`CAP_DAC_OVERRIDE`.

This is precisely the audio-gid bug again (host `audio` gid 29 ungranted),
one device along.

**Consequence if shipped as-is:** the BME680 plugin and `i2c-reader` will
find nothing on the boat, and — as B1a already showed with the missing
`i2c-dev` module — the failure is silent. `i2c-reader` currently logs only
"devices config is missing", which would mask this.

**Proposed fix** (not applied — see below): add the host i2c gid to the
override the PR #33 session already established, listing all three gids
explicitly because compose list-merge semantics are not worth betting on:

    services:
      signalk-server:
        group_add: ["4", "960", "988"]

in `/etc/container-apps/marine-signalk-server-container/symphony.override.yml`,
whose source of truth is `host/halos/` on PR #33. The gid travels with the
card, so 988 stays correct on the boat. Verify with the same one-liner:
`docker exec signalk-server python3 -c "open('/dev/i2c-1')"` — silence is a
pass.

Not applied by this session because the override file and its PR are owned by
`symphony-pr-33-review-601c06-0a`, and applying it needs a unit restart while
that session is actively restarting the unit (see below).

### Another session is actively restarting the SignalK unit

`marine-signalk-server-container.service` restarted at 07:12:50Z and again at
07:15:59Z. This is **not** the autoheal loop: autoheal has fired nothing since
06:45:26Z, `RestartCount` is 0, and the journal shows a clean
`Deactivated successfully` / `Stopped` / `Starting` cycle with exit code 0 —
the signature of a deliberate `systemctl restart`, not a health kill.

Two consequences:
- The "correction" recorded above — that the loop was fixed — was itself
  premature. The honest statement is narrower: **autoheal has not restarted
  the container since the override went in at 07:12**, which is consistent
  with the fix working but is not yet a clean observation, because a second
  session keeps bouncing the unit.
- **Handoff item 2 (is `plugin-watchdog` running?) cannot be answered while
  this continues.** The test is that the watchdog must log
  `ALERT: plugin bt-sensors-plugin-sk ...` 600 s after startup; every restart
  resets that clock, and nothing has stayed up for 600 s.

### i2c fix: staged, NOT installed, NOT restarted

Mark's instruction, 2026-09-02: **do not restart the SignalK unit without the
consent of `symphony-pr-33-review-601c06-0a`.** Standing until he or that
session lifts it.

The corrected override is written to **`/tmp/symphony.override.yml` on the
staging Pi** and validated (`yaml.safe_load` returns
`group_add == ['4','960','988']`). It has deliberately **not** been copied to
`/etc/container-apps/marine-signalk-server-container/`: installing it is inert
until a restart, but it would silently change the behaviour of that session's
*next* restart in the middle of their healthcheck verification, which is the
same surprise arriving more slowly.

To install it, once consent is given:

    sudo cp /tmp/symphony.override.yml \
       /etc/container-apps/marine-signalk-server-container/symphony.override.yml
    sudo systemctl restart marine-signalk-server-container.service
    docker exec signalk-server python3 -c "open('/dev/i2c-1')"   # silence = pass

The staged file preserves the PR #33 session's healthcheck block verbatim and
adds only `group_add`, with a comment recording why gid 988 is listed and why
all three gids are spelled out. **`host/halos/` on PR #33 needs the same
change** — that copy is the source of truth and this session cannot edit their
branch.

Three messages sent to that session (07:00, 07:10, 07:25 UTC approx); no reply
to any of them as of this writing.

### Severity of the i2c defect: it is a regression, not a gap

Read alongside `halos-swap-execution-2026-09-02.md` (session
`symphony-pr-33-review-601c06-0a`, commit 48d4b54), whose baseline
`scripts/halos_swap_check.sh symphony-pi` at 07:16Z reports **`bme680 ok`** on
the boat's *current* card.

So the BME680 works today. It works because the boat's present install is
OpenPlotter on bare metal, where SignalK runs as a host user in the host `i2c`
group. Under HALOS the same plugin runs inside a container as `node`, and the
gid mismatch recorded above breaks it.

That reclassifies this. It is not "an untested path on the new card" — it is
**a working boat function that the swap silently removes**, and the swap-check
script would report it the same way B1a's missing `i2c-dev` module would have:
`i2c-reader` logs only "devices config is missing", and the BME680 tree simply
stays empty, which is also the normal appearance during the ~10 minute
post-restart burn-in. There is no error to notice.

Note that the same session's checkpoint records `/dev/i2c-1`: `i2c-dev`
persisted in `/etc/modules-load.d/` as done — which it is. Loading the module
creates the device node; it does not make the node reachable from inside the
container. Both fixes are needed and only one is in.

**Recommendation: this should block the swap until the `group_add` line is in,
or be accepted explicitly as a known regression with the BME680 to be restored
afterwards.** It is a one-line change with a one-line test, so blocking on it
is cheap.
