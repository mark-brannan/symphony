# HALOS swap — second-pass review, 2026-09-03

Mark's ask: scrutinise the whole plan for holes as if a bad swap cost lives
and so did hedging or escalating needlessly; then judge whether it is
repeatable on a fresh HALOS image. This file is the evidence and the calls.
Fixes made today are listed at the end; anything for Mark is on the board.

## Findings, in severity order

1. **The bench card wedged twice today.** Once overnight (last heartbeat
   06:49 local, red LED solid, green dark, power-cycled 10:16 by Mark), and
   again at ~10:30, ten minutes into the next boot with the full stack up,
   while a `git pull` ran — that time the board reset itself. Measured on the
   rebooted card: the hardware watchdog *is* armed (`Watchdog running with a
   hardware timeout of 30s`, `/dev/watchdog0` BCM2835), so the overnight wedge
   was one that kept PID 1 petting it. Green-dark plus a 1.6 GB zram swap
   footprint fits a compression livelock: CPU-bound, no SD I/O, systemd still
   scheduled. Inference, not measurement — the journal was volatile. At 2 min
   uptime with QuestDB and Grafana up the box had 57 MB free and 940 MB in
   swap. **Bench-only cause (2 GB), boat-relevant lesson: the watchdog does
   not cover a swap livelock.** The 4 GB boat has ~1 GB headroom by the
   existing arithmetic; no change to the swap-day sequence. Cards below for
   the two mitigations worth weighing later.
2. **Journal was volatile on HALOS** — Pi OS Trixie ships
   `/usr/lib/systemd/journald.conf.d/40-rpi-volatile-storage.conf`. Every hang
   would be undiagnosable at the boat. **Fixed:** `host/journald-symphony.conf`
   sets `Storage=persistent`; installed on the card via `host/install.sh`,
   flushed, verified writing to `/var/log/journal`. Preflight `journal` line
   checks persistence and the watchdog.
3. **State drift between the 2026-09-02 copy and the boat was not in the
   plan.** Measured today: installed `signalk-container` 1.32.2 vs 1.32.1
   (disabled on HALOS anyway) and `vhfinfo` 0.0.40 vs 0.0.39; config hashes
   not yet compared (bench went down). **Fixed:** preflight `state` line
   compares config-file hashes and installed plugin versions with the boat;
   RUNBOOK has the final-sync step with the right excludes (`package.json`,
   `node_modules`).
4. **`can0` had no home check.** Modules `mcp251x`, `can_raw`, `can_dev`,
   `vcan` are all present in HALOS kernel 6.18.39; networkd enabled;
   `80-can.network` at 250 kbit; wait-online disabled. All measured good.
   **Fixed:** preflight `can` line so a kernel update can't silently drop it.
5. **Memory limits are enforced now** that `cgroup_enable=memory` is on:
   QuestDB runs with a 768 MB limit (HALOS's own compose), everything else
   unlimited. SignalK sat at 424 MB RSS at 2 min. No action; recorded so a
   QuestDB OOM at the boat is read correctly.
6. **No unattended upgrades on the HALOS card.** `apt-daily-upgrade.timer`
   runs but `unattended-upgrades` is not installed; the boat card has it. Not
   a swap-day issue. Card (Claude's): decide the policy, and blacklist
   `marine-*` before enabling anything — an image upgrade could change the
   SignalK container's Node major under the rebuilt native modules.
7. Retracted after measurement: the WiFi hotspot/client conflict I suspected.
   HALOS runs `Halos-AP` on a virtual `wlan0ap` next to the client on
   `wlan0`, the same shape as the boat's `wlan9`. Preflight `hotspot` line
   checks the AP is up on `wlan0ap`.
8. Lower: the boat check's ping period (5 min) exceeds its timeout (3 min),
   so it lives in grace by design; read healthchecks.io with that in mind.
   The `(halos card)` check went `down` at ~07:35 local today — whether Mark
   was alerted is a question on his board.

## Fresh-image repeatability

Full detail and the step order: [halos-fresh-image-rebuild.md](halos-fresh-image-rebuild.md).
The short version, from a second card imaged today with
`Halos-Marine-RPI_2026-08-20.0.img.xz` and booted on the bench Pi:

- **Not repeatable as documented, and the gap is in front of the plan, not
  inside it.** A fresh card needs wired Ethernet with internet before
  power-on: no WiFi credentials, and the image ships zero container images —
  SignalK, Authelia, Traefik and Homarr are all pulled on first boot. This
  card sat for 30 minutes with two failed units and nothing running until a
  cable went in. Nobody had written this down because Mark did it once by
  hand and the bench card has looked "already built" ever since.
- The image ships only SignalK and Homarr as apps. QuestDB, Grafana and the
  three apps the plan removes (InfluxDB, AvNav, OpenCPN) were all hand
  installs on the bench card. The plan's "remove InfluxDB, disable AvNav and
  OpenCPN" steps describe undoing something a fresh card never has.
- The host layer is now being applied by Ansible to the fresh card; results
  below when the run finishes. The SignalK state layer (boat copy, forks,
  npm build) remains hand procedure with one unrecorded command.
- Consequence for the boat, stated once: a HALOS card is built at home,
  always, and the first boot of any HALOS card is a home-only event.

## What was changed today

