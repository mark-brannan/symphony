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

1. **Read first, touch nothing.** Hat Labs docs for the HALPI2: how the
   OS lands on eMMC/SSD (CM5 eMMC needs `rpiboot`/usbboot; SSD may image
   like a Pi 5 — unverified), the power-controller daemon the RP2040 needs
   on the OS side (unverified whether the HALOS HALPI2 image ships it),
   the CAN overlay for the integrated NMEA 2000 port (**not** the PiCAN-M
   `mcp2515-can0` lines the `boot`/`can` roles write — wrong for this board
   until proven otherwise), and what the isolated NMEA 0183 port enumerates
   as.
2. **Power from a bench DC supply at 12–13.8 V, not USB-C.** The Pi 5 run
   died on USB-C brownout and needed a CPU cap
   (`halos-fresh-image-rebuild.md` § Power); the HALPI2's 10–32 V input is
   the fix. The CPU-cap card on the board is re-evaluated for this board,
   not carried over.
3. **Flash the HALOS HALPI2 image**, first boot on the home LAN, join the
   tailnet as a *new* node named `symphony-halpi2`. The Tailscale
   reflash-identity design card is now live: this is the third name and the
   one that becomes the boat.
4. **Add it to `ansible/inventory.yml` under `halos_cards`** with its own
   `host_vars`, run `site.yml`. The Pi 5 run went clean after one fix; the
   HALPI2 will surface whatever is CM5- or board-specific (item 1's CAN
   overlay, the power daemon). Each fix goes into the role, not the box.
5. **SignalK state layer**: the B3 script (`halos-b3-findings-2026-09-02.md`
   recipe), then `scripts/halos_preflight.sh` — expect the same two
   home-only FAILs (LAN/CAN) as the Pi 5 run and nothing else. Memory is no
   longer the constraint: run QuestDB and Grafana together and record
   `free -m` under load for the reference doc.
6. **`scripts/halos_swap_check.sh symphony-halpi2`** as the bench baseline.
   Then leave it running for days — the soak the 2 GB card never could.
7. **Second heartbeat check.** `/etc/boat-heartbeat.json` on this box points
   at the existing `SignalK Symphony (halos card)` check (dead since
   2026-09-05, free to repurpose) or a new one.

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
