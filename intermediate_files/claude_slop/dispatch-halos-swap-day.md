# Swap-day dispatch — HALOS card into the boat Pi

**Model: Opus 5 (Fable 5.1 if the box misbehaves). Effort: medium. Difficulty:
low-medium** — every command exists and has run; the work is running them in
order against a live boat and reading the output. Budget about an hour at the
boat, most of it waiting on boots. Paste this into a session on a tailnet
machine with sops access (either dev box).

Procedure: `RUNBOOK.md` → "Swapping the HALOS card onto the boat". Build
state: `intermediate_files/claude_slop/halos-swap-execution-2026-09-02.md`.

## Split of labour

Mark, by hand: cards, the Micro-C plug, the phone certificate, reading the
phone for the ntfy message and the healthchecks.io notice.

The session, over Tailscale: every check, the DNS cutover, the rollback
decision on the numbers, and a paragraph in `maintenance/log.md` at the end.

## Sequence

1. Before leaving home (session): `scripts/halos_preflight.sh` — every line
   `ok`. Then the DNS dry run from the same runbook section, and end with the
   record back on `symphony-pi`. Any FAIL here ends the day at home.
2. At the boat, baseline (session): `scripts/halos_swap_check.sh symphony-pi`.
   Paste the output into the session log verbatim; it is the comparison for
   step 5. Expected FAILs: `victron` if the Cerbo is still not answering,
   `questdb` if the boat card's QuestDB is still overloaded.
3. Shutdown (session then Mark): `ssh pi@symphony-pi 'sudo shutdown -h now'`;
   Mark unplugs the Micro-C when the green LED stops, swaps the cards, plugs
   back in. The boat card goes in a pocket.
4. Wait five minutes (both). Nothing to do; SignalK cold-starts in 3–4 min.
5. Post-swap check (session): `scripts/halos_swap_check.sh`. Rerun at ten
   minutes if `ble` or `bme680` FAIL. Go/no-go rule: every line that was `ok`
   in step 2 is `ok` here. A line that FAILed in both is a boat problem and
   does not block.
6. DNS (session): `scripts/dns_cutover.sh set symphony-halos`, then
   `dig +short symphony.dark-star-llc.com @1.1.1.1` until it shows the halos
   tailnet IP. Tell Mark the healthchecks.io `SignalK Symphony` notice will
   arrive within about 35 min and is expected.
7. Phone (Mark): on the boat WiFi (`SignalK`), install the certificate from
   `https://signalk.symphony.dark-star-llc.com/ca/`, then open
   `https://signalk.symphony.dark-star-llc.com/` — SignalK admin, no warning.
8. Log (session): one dated entry in `maintenance/log.md`, past tense, what
   was swapped and what was FAILing before and after. Push to main.

## Rollback (any step from 5 on)

Mark: unplug, swap the boat card back, plug in. Session, after three
minutes: `scripts/halos_swap_check.sh symphony-pi`, then
`scripts/dns_cutover.sh set symphony-pi` only after that check matches the
step-2 baseline. The `(halos card)` healthchecks.io check goes late instead.
Nothing on the boat card was changed by the trial.

## Known before the day

- Cerbo MQTT is down on the boat since 2026-09-01; only Mark can look at the
  Cerbo. The `victron` line FAILs on both cards until then.
- Position comes from `signalk-fixed-position`; N2K is live regardless.
- The boat card's QuestDB may not answer in 30 s; that is the baseline, not
  the new card.
- Containers now carry healthchecks and the boat card runs `autoheal`; the
  HALOS card has its own. What the swap has to carry, including why the
  "QuestDB may not answer in 30 s" line above is now a liveness input:
  [halos-swap-container-liveness-2026-09-02.md](halos-swap-container-liveness-2026-09-02.md).
- **pypilot rides along, containerized** (plan B4d, decided 2026-09-02,
  since validated live on the boat's own card 6+ hours against the real
  MPU9250 and the real 0.56 `~/.pypilot` state — no calibration-format
  errors, gyro bias writing normally). Before the day: copy the boat's
  `pypilot/data/` onto the HALOS card's checkout (same path the boat itself
  runs from) so the trial carries the real calibration, not a fresh one.
  Carrying it across is worth measuring but is not a gate — if the
  calibration comes over wrong, recalibrate on the boat and carry on
  (Mark, 2026-09-03).
  After the post-swap check in step 5: `sudo docker compose -p symphony -f
  docker-compose.yml --profile pypilot up -d`, then confirm
  `curl -s -o /dev/null -w '%{http_code}\n' localhost:8000` is 200 and
  `docker ps` shows both `pypilot` and `pypilot-web` healthy.
