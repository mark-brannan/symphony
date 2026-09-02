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
