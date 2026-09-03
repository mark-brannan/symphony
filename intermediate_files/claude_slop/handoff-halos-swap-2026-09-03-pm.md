# Handoff — HALOS swap prep, evening of 2026-09-03

**Model: Opus 5, effort medium. Difficulty: low-medium** — every command
exists; the work is running them in order and reading output. Budget ~1 h,
mostly waiting on boots and one npm build. Run from this WSL box (tailnet +
sops). Read first: [halos-swap-review-2026-09-03.md](halos-swap-review-2026-09-03.md)
(findings and fixes) and [halos-fresh-image-rebuild.md](halos-fresh-image-rebuild.md).

## Where things stand

- **Payload card** (the one for the boat): shut down cleanly, out of the Pi.
  Journal fix installed. Not yet run: the new preflight lines (`state`,
  `can`, `hotspot`, `journal`), the final state sync, the DNS write-path dry
  run. `vhfinfo` is one patch version behind the boat.
- **Fresh card** (second card, `Halos-Marine-RPI_2026-08-20.0`): in the bench
  Pi at `192.168.0.192` (LAN, wired; not on the tailnet; ssh key installed;
  `pi` password = sops `symphony_halos_pi_password`). Ansible `site.yml`
  converges on it (`ok=67 failed=0`) after eight role/installer fixes, all on
  main. Boat `.signalk` state, both forks, the four plugin disables and the
  venus host edit are loaded. `scripts/halos_signalk_npm.sh` **finished on it** (18 min 52 s, exit 0,
  `journalctl -u halos-npm` has the log) and restarted the SignalK unit. ntfy is up. Heartbeat timer disabled
  on purpose (it would ping the payload card's check).
- Scratch inventory for the fresh card, if Ansible is needed again:
  `symphony-halos` with `ansible_host: 192.168.0.192`, `ansible_user: pi`,
  host-key checking off — recreate under the scratchpad, don't commit it.

## Do, in order

1. ~~Fresh card preflight.~~ **Done 2026-09-03 20:00.** `plugins` and `state`
   both ok; the four FAILs are all known properties of that card (no
   tailscale, no questdb/grafana, journal staged pending a reboot). Two
   preflight bugs found and fixed (5a04053); result in
   `halos-fresh-image-rebuild.md`.
2. ~~apt question.~~ **Done.** Answered with `apt-cache policy` instead of an
   install (the card was 1.3 GB into swap): questdb 10.0.0-1, grafana
   13.1.3-2, influxdb 2.9.1-5 all exist on `apt.halos.fi`. What they pull is
   still unmeasured.
   Also done, unplanned: `halos_signalk_npm.sh` no longer dies with its ssh
   session (e14fa0a) — it detaches into the transient unit itself. Both
   failure paths measured on the fresh card.
3. Ask Mark to swap the payload card back in (fresh card powered off — from
   here, `ssh pi@192.168.0.192 sudo poweroff`).
4. Payload card: `scripts/halos_preflight.sh`. Stop QuestDB/Grafana first if
   memory is under 400 MB, and expect `services` to FAIL for that reason
   only. Fix anything else it names; the `state` line's sync step is in
   `RUNBOOK.md` → "Before leaving home". For `vhfinfo`, run the sync step's
   npm script — that is also the recipe's first run on the payload card.
   Expect `journal` to read `staged(...)` until step 6's reboot.
5. DNS write-path dry run from the same RUNBOOK section, ending on
   `symphony-pi`. Confirm with `dig`.
6. Reboot the payload card once with the full stack, wait 5 min,
   `scripts/halos_swap_check.sh`; then stop QuestDB and Grafana and leave it
   running overnight so the wedge either recurs (journal is persistent now:
   `journalctl -b -1`) or doesn't.
7. One paragraph in `maintenance/log.md` (what was validated, what changed),
   push, and update the board card that points at `dispatch-halos-swap-day.md`.

## Not for tonight

The three Claude's cards filed today (unattended upgrades, livelock guard,
npm recipe proof — the last is now partly done by step 1) and Mark's two
questions (ntfy phone URL, healthchecks alert).
