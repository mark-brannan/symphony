# HALPI2 arrival plan — 2026-09-22

Written before the unit arrives. Everything below that names a HALPI2 fact
not already in `reference/compute_hardware.md` is **unverified** and marked
so; the first bench session verifies against Hat Labs' docs before acting.

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

Unverified until the docs are read, and checked before step 1: what the
first-boot login path is, whether the RP2040 daemon ships in the image,
which overlay the integrated N2K port uses, and what the isolated NMEA 0183
port enumerates as.

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
