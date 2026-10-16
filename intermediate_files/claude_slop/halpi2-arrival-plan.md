# HALPI2 arrival plan — 2026-09-22

Written before the unit arrives. Everything below that names a HALPI2 fact
not already in `reference/compute_hardware.md` is **unverified** and marked
so; the first bench session verifies against Hat Labs' docs before acting.

## Status — 2026-10-15 (step 4, unattended shift 1)

- Step 4 done: `CARD_NAME=symphony-halpi2 CARD_SSH=192.168.0.110
  scripts/halos_card_prepare.sh` ran end to end (`site.yml` ok=73 changed=0,
  the boat's `.signalk` state, npm build, overrides, ntfy and the Traefik
  route, reboot) and `scripts/halos_preflight.sh` read ok on every line; the
  home-only `lan` and `can` lines pass too (the CM5 checks `mcp251xfd`,
  `uart4-pi5`, `/dev/ttyAMA4`). QuestDB and Grafana stay up (8 GB card).
- Fixes the run forced into `halos_card_prepare.sh`: the boat state copy is
  cached across runs (`$TMPDIR/halos-prepare-cache`, `rsync --partial`) so a
  dropped cellular link resumes; the card sync excludes `system-plugins`
  (root-owned HaLOS content, `signalk-halpi`; `--delete` aborted on it);
  `signalk-rpi-uptime` was unpublished from npm on 2026-10-13, so the boat's
  copy is carried as `local-plugins/signalk-rpi-uptime` pinned `file:` (the
  npm build 404ed on it). Undo for that last one: drop the third fork pin and
  the rsync lines once the package is republished or the plugin is retired.
- Step 5 baseline (`scripts/halos_swap_check.sh symphony-halpi2`, 558 s after
  boot): ok signalk 2.31.1, heartbeat, containers, ntfy, questdb, devices,
  bme680, front. FAIL lan (eth0 is the bench address 192.168.0.110), n2k (no
  CAN bus at home), victron (Cerbo MQTT unreachable at home), ble (0 of 5
  sensors, allow 10 min after boot), pypilot (web UI 000).

## Status — 2026-10-15

- Step 2 landed: the HALPI2 is on the tailnet as `symphony-halpi2` and is in
  `ansible/inventory.yml`. From the WSL box its tailnet name still fails ssh
  host-key verification (stale `known_hosts`), so reach it with
  `ssh pi@192.168.0.110` and `-e ansible_host=192.168.0.110`.
- Step 3 done: `site.yml --limit symphony-halpi2` converged. Run 1 (real):
  ok=78 changed=20, including one reboot from the boot role (cmdline regdom
  US, memory cgroup, `i2c-dev`). Run 2: ok=73 changed=0. Can0 was already up
  at 250 kbit/s from the image's own mcp251xfd overlay; no PiCAN-M lines.
- One role fix: the zram restart handler left `systemd-zram-setup@zram0`
  failed on this image (it already swaps to zram0, so the restart is refused),
  which the heartbeat would report as a fault. The handler now follows with
  `reset-failed`. The new 1 GB size applies at the next boot; the image's 2 GB
  zram0 is what runs until then.
- Still open from step 3: `/home/pi/symphony` has no sops filters on the card
  (bootstrap, `bash scripts/setup-git-filters.sh`), and SignalK state is
  outside Ansible (steps 4 onward).

## Status — 2026-09-26

- Step 1 half done: the stock inventory is banked
  ([PR #81](https://github.com/mark-brannan/symphony/pull/81),
  [baseline](halpi2-stock-baseline-2026-09-26/README.md)). Still open from
  step 1: the `pi` password is the published default, no `authorized_keys`,
  and no restorable snapshot of the stock disk has been taken.
- The unit is now on the home LAN; steps 2–6 not started, no inventory entry.
- Until the tailnet join, find it by LAN scan, not mDNS (`halos.local`
  doesn't resolve from the WSL box): it is the host with ssh (Debian 13
  banner) plus 9090 and 3000 open — 192.168.0.110 on 2026-10-08, DHCP.
- 2026-10-08: live root snapshot failed. `fsfreeze -f /` was followed by a
  reboot ~9 min later (suspected: systemd's 1-min hardware watchdog);
  fs came back clean. Don't freeze / on this box. Partition table and boot
  partition are in `~/halpi2-snapshot-2026-10-08/` on the WSL box; no root image.

## Recommendation

**Skip the Pi 4 card swap. The HALPI2 is the swap.** The 2026-09-04 HALOS
card was a rehearsal for exactly this; every artifact it produced transfers
(Ansible `site.yml`, `halos_preflight.sh`, `halos_swap_check.sh`, the
SignalK state script, `host/halos/`). What does not transfer is the reason to
keep going with the Pi 4: its 32 GB card is at 90 % and the 2 GB bench box
was the memory ceiling the whole trial fought. Doing the card swap first
would spend a boat trip on hardware that leaves within weeks.

Exception: if the HALPI2 slips past the next boat visit *and* the boat Pi
needs a rebuild anyway (disk full, card failing), do the card swap as
planned — `dispatch-halos-swap-day.md` is still valid.

## Bench, at home — in order

The unit ships with the current HALOS on its SSD. **No reflash.** The
premise is that `ansible/site.yml` takes a stock HALOS box to a boat card;
the HALPI2 is the first true test of that premise, since both earlier cards
were hand-imaged and hand-fixed first. Anything Ansible cannot do from a
stock image is a gap in a role, fixed in the role.

1. **First boot as shipped.** Bench DC supply at 12–13.8 V into the DC
   input, ethernet to the home LAN. Log in via HALOS's first-boot path
   (Cockpit or console — check Hat Labs' docs), set the `pi` password from
   sops, get SSH. Record the image version and what packages are already
   present (`dpkg -l | grep -i halos`, `docker ps`) before touching anything;
   that snapshot is the "stock" baseline the roles are measured against.
2. **Tailnet join** as `symphony-halpi2`, by hand or via the `identity` role
   if it already handles a fresh node — this is where the reflash-identity
   design card becomes concrete, and the answer here is the boat's answer.
3. **Inventory + host_vars**, then `ansible-playbook site.yml --limit
   symphony-halpi2 --check --diff` first. Read the diff: the `boot` and
   `can` roles will try to write PiCAN-M overlays (`mcp2515-can0`) that are
   wrong for the integrated N2K port; the power-controller daemon for the
   RP2040 may already be in the image. Fix the roles (a per-board variable,
   not a fork), then run for real. Repeat until a second run is idempotent.
4. **SignalK state layer**: the B3 script, then `scripts/halos_preflight.sh`
   — expect only the two home-only FAILs (LAN/CAN).
5. **`scripts/halos_swap_check.sh symphony-halpi2`** as the bench baseline,
   then leave it running for days with QuestDB and Grafana up; record
   `free -m` under load.
6. **Heartbeat**: point `/etc/boat-heartbeat.json` at the dead
   `SignalK Symphony (halos card)` check, repurposed, or a new one.

Settled by the [stock baseline](halpi2-stock-baseline-2026-09-26/README.md),
no doc research needed: login is ssh `pi`/`halos` (cloud-init NoCloud is the
first-boot hook); `halpid` ships in the image; the N2K port is `mcp251xfd`
on `spi0-1`; the 0183 port is `uart4-pi5`, `/dev/ttyAMA4`.

## What the bench cannot answer (unchanged)

`can0` on a live N2K bus, BLE with the boat's sensors in range, the boat LAN
and router DNS overrides, Cerbo MQTT. All of that is swap day.

## Swap day differences from `dispatch-halos-swap-day.md`

- Physical: N2K Micro-C drop cable and tee, DC feed from the panel (or bus
  power at ≤0.8 A — check that drop's budget first), mounting the enclosure,
  moving the BLE dongle and any USB devices off the Pi 4. Evernote tasks.
- The Pi 4 with its PiCAN-M stays aboard, powered off, as the rollback for
  one visit; the 32 GB card still comes home for the S3 data copy-off.
- DNS cutover and the `hostnames.conf` order are unchanged; only the
  tailnet name differs.

## Before any of this: the boat

The boat Pi has had no uplink since 2026-09-20. The Cerbo reboot result,
the disk-90 % alarm and the pypilot-survives-reboot check all wait on the
next boat visit or the router coming back. Cards on the board.
