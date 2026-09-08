# Handoff — HALOS card prep, successor to the B3 session

**Model: Opus 5. Difficulty: medium-high.** Live hardware, a second Claude
session to coordinate with, and a swap happening in the morning. Not hard
reasoning; hard *care*.

---

You are taking over preparation of the HALOS card for a swap into the boat Pi.
The previous session ran long (317k context) and handed off.

**Read first, in this order:**
1. `intermediate_files/claude_slop/halos-swap-preflight-2026-09-02.md` — the
   single morning read: card state, loose ends, what to watch after the swap.
2. `intermediate_files/claude_slop/halos-b3-findings-2026-09-02.md` — the
   evidence behind every claim in it.
3. `reference/monitoring_decisions.md` and `monitoring_posture.md` **before
   asserting anything about monitoring.** The previous session twice reported
   "findings" these docs already explain. Check them first, every time.

**Hardware:**
- `ssh pi@192.168.0.193` — the staging Pi, 1844 MB. `sudo` needs a password:
  `sops -d --extract '["symphony_halos_pi_password"]' secrets/symphony.sops.yaml | ssh pi@192.168.0.193 'sudo -S -p "" <cmd>'`
- `ssh pi@symphony-pi` — the boat, 3796 MB, the swap target.
- SignalK data dir on halos:
  `/var/lib/container-apps/marine-signalk-server-container/data/data` (call it `$D`).

**Rules learned the hard way — do not relearn them:**
- The staging box is 1844 MB and **cannot run SignalK plus the databases**.
  Keep `opencpn`, `avnav`, `homarr`, `questdb`, `grafana` stopped unless you
  are deliberately measuring. Left running, the box wedges: ports accept TCP,
  nothing completes, and it needs Mark's hands on the power.
- Any session may `systemctl stop` those units without asking. **No session
  asks Mark for a power-cycle without the other active session agreeing first**
  — his explicit instruction.
- Never `docker exec` a long npm operation: the systemd unit tears its own
  container down and SIGKILLs you. Use a throwaway container.
- Never bare `npm rebuild`: `signalk-victron-ble` needs python3-venv, fails,
  and aborts the run. Name packages.
- The HALOS signalk image has **no compiler**. Native modules build in a
  same-ABI toolchain container (`node:24-bookworm`, ABI 137) writing into `$D`.
- Long operations go under `systemd-run --unit=<name> --collect` so an SSH
  drop cannot kill them.
- **The boat's config is not golden.** Repo has 64 plugin configs, boat 84,
  neither a superset. A problem on either side needs investigation, a decision
  from Mark, or both — never an assumption that the boat is right.
- Resolve a plugin's **id**, not its package name, before touching its config
  (`plugin.id` in its `index.js`). The previous session created an inert
  config file by getting this wrong.

**Coordinate with:** the session named `symphony-pr-33-review-601c06-0a`,
which is critically reviewing PR #33 and will execute the plan's steps to
verify. Use `ListAgents` then `SendMessage`. Mark's split: **they have final
say on big things and on PR #33; you own the monitoring posture and low-level
plugin detail.** They had not replied to three messages as of handoff — if
they are unreachable, say so plainly rather than proceeding as if agreed.

**Open work, in priority order:**
1. **Mark is wiring an i2c sensor to the staging Pi** (ideally a BME680). When
   it is on: `i2cdetect -y 1` on the host, then the same from *inside* the
   SignalK container, then confirm the BME680 plugin publishes deltas. The
   container gets `group_add` gids 960 and 4; whether that covers the host
   `i2c` group is **unverified and is the most likely failure**. This is the
   only chance to test the i2c path before swap day.
2. Confirm the `plugin-watchdog` plugin is actually running (its real config
   is the pre-existing `plugin-watchdog.json`; the stray file has been deleted).
3. Re-verify plugin startup end to end with the box quiet: expect ~118 plugins,
   ~66 enabled, and exactly one failure (`signalk-instrument-light-plugin`,
   which has no config and whose serialport bindings will not build for node
   24 — leave it).

**Do not** pre-edit the container healthcheck timeout to suppress the restart
loop. That compose file is package-managed and not a conffile, so `apt upgrade`
reverts it silently — a worse failure than a restart we understand. The loop is
a symptom of the 1844 MB box; let the swap test it.

**Two decisions parked for Mark, not to be acted on:** both anchor-alarm
plugins are installed but disabled on the boat, and `signalk-mob-notifier` and
`signalk-dsc` are enabled in the repo but absent from the boat.
