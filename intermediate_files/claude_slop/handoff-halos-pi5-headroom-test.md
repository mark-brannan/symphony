# Handoff — does the HALOS stack fit when memory isn't the constraint?

**Model: Opus 5, effort medium. Difficulty: low-medium** — every command
already exists and has been run once; this is the same recipe on different
hardware. Budget ~1 h plus a soak. Run from the WSL box (sops + LAN).

## The one question

Does the full HALOS stack — SignalK **plus** QuestDB and Grafana — stay up
together? On the 2 GB bench Pi it never could: the card hard-reset three
times in fifteen minutes on 2026-09-04 and only ran clean with both databases
stopped. That made every memory finding of that night unfalsifiable. A Pi 5
with 4 GB or more is the first chance to separate "this stack is too big"
from "that bench Pi was too small".

**Stop before anything else if the board has under 4 GB.** `free -m` and
`cat /proc/device-tree/model` first. Under 4 GB, this test reproduces
2026-09-04 and teaches nothing — say so and stop; don't spend the hour.

## Hard constraint

**Use the fresh card, not the payload card.** The payload card is validated
and powered down for the swap; every boot in unfamiliar hardware is a chance
to mutate it (NetworkManager profiles, a firmware or kernel bump on first
boot — the sops WiFi keyfiles' MAC pin already bit this project once). There
is nothing to gain either: the Pi 5's device tree differs, so
`dtoverlay=mcp2515-can0` and the PiCAN-M HAT would not validate the boat's
can0 path regardless.

## What this cannot answer, on any hardware at home

can0 with the HAT, BLE with the boat's sensors in range, the boat LAN. Those
stay boat-only. Don't let a green run here read as more than it is — and note
the honest discount: a Pi 5 is not a Pi 4. A clean run is suggestive, not
proof for the boat's Pi 4B. The stronger existing evidence is that
`symphony-pi` runs its own equivalent stack today at ~1578 MB available.

## Do, in order

1. **Wired Ethernet with internet, plugged in before power-on.** Not
   optional — see `halos-fresh-image-rebuild.md` § Requirements. Boot the
   fresh card, find it on the LAN, `ssh pi@<ip>` (password: sops
   `symphony_halos_pi_password`).
2. `free -m`, `cat /proc/device-tree/model`. **Under 4 GB: stop here.**
   Record the model and RAM either way.
3. Confirm the card came up as it was left: `scripts/halos_preflight.sh <ip>`.
   Expect the same four FAILs as 2026-09-04 (`host` — no tailscale;
   `journal` — staged until a reboot; `services`/`questdb` — databases not
   installed). Anything else is new and worth reading before continuing.
4. Install the two packages, which is the step 2 GB never allowed:
   `sudo apt install marine-questdb-container marine-grafana-container`
   (10.0.0-1 and 13.1.3-2 on `apt.halos.fi` as of 2026-09-04). **Record what
   they pull and how much they add** — that number is still unmeasured
   anywhere in this repo.
5. `scripts/halos_preflight.sh <ip>` again. `services` and `questdb` should
   now read ok, which they never have on any card.
6. Soak: leave it running with everything up. Check back with `free -m`,
   `grep ^pswp /proc/vmstat`, `uptime`, and `journalctl --list-boots -q | wc -l`
   — a boot count that grows is the 2026-09-04 reset loop recurring, and this
   time the journal is persistent so `journalctl -b -1` has the last minute.
7. Write the result into `halos-fresh-image-rebuild.md`: the board, the RAM,
   the package sizes, and whether the stack held. Update the board card.

## Traps already paid for

- Grepping this card's journal for a term also matches your own ssh command
  text, echoed by `tailscaled` — it produced a false "2 OOM kills" reading on
  2026-09-04. Scope with `-u <unit>` or exclude `tailscaled`.
- `sudo` needs the sops password piped on stdin; it times out between calls.
- `scripts/halos_signalk_npm.sh` detaches into its own transient unit now, so
  a dropped ssh cannot tear a build in half. Abort with
  `systemctl stop halos-npm`, never `systemctl kill`.
- The fresh card is not on the tailnet. Use its LAN IP everywhere, including
  as the preflight argument.
