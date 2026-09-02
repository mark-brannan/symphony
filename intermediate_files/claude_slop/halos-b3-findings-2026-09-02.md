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
