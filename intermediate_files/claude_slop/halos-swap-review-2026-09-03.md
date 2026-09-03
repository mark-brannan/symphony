# HALOS swap — second-pass review, 2026-09-03

Mark's ask: scrutinise the whole plan for holes as if a bad swap cost lives
and so did hedging or escalating needlessly; then judge whether it is
repeatable on a fresh HALOS image. This file is the evidence and the calls.
Fixes made today are listed at the end; anything for Mark is on the board.

## Findings, in severity order

1. **The bench card hung unattended for ~3.5 h this morning** (last heartbeat
   06:49 local; red LED solid, green dark; power-cycled 10:40). Not a boot
   loop — a wedge. The hardware watchdog this repo installs should have reset
   it within a minute. Either it is not armed on HALOS or the wedge was of a
   kind it doesn't cover. Forensics below once the card is back. On a 4 GB
   boat the trigger is less likely; the *unrecovered* part is the risk.
2. **The hotspot cannot coexist with the WiFi client on HALOS as built.** The
   boat card runs the `SignalK` AP on a second virtual interface (`wlan9`,
   brcmfmac virtual AP) next to the `Symphony` client on `wlan0`. HALOS has
   one `wlan0` and two autoconnect profiles on it; NetworkManager picks one.
   The LAN comes in on `eth0`, so the AP is the one that must win. No known
   data path depends on the hotspot today (no `10.42.0.x` sources in
   SignalK, no SensESP online), so this is a step-7 and convenience risk, not
   a data risk. Preflight now checks it (`hotspot` line).
3. **The SignalK state on the card is a 2026-09-02 snapshot.** The boat's
   `package.json` changed at 17:27 that evening, after the copy. Config
   drift between copy and swap was not in the plan at all. Preflight now
   diffs config files and `package.json` deps against the boat (`state`
   line); RUNBOOK has the final-sync step.
4. **`can0` had no home check.** The preflight verified config lines but not
   that the `mcp251x` and `can_raw` modules exist in HALOS's kernel, that
   networkd is enabled, or that `80-can.network` is present. N2K dead at the
   boat would have been the first sign. Preflight `can` line added.
5. **HALOS's journal does not survive a reboot** (last night's leg 2 found
   no previous-boot journal). A boat-side hang would be undiagnosable.
   Preflight `journal` line added; fix pending measurement on the bench.
6. Lower: the boat check's ping period (5 min) exceeds its timeout (3 min),
   so it lives in grace by design — fine, but every healthchecks.io reading
   has to be interpreted with that in mind. The halos card's check has been
   `down` since 06:49 today; whether Mark was alerted is a question for him.

## Fresh-image repeatability

(filled in after the gap analysis is reconciled with the bench)

## What was changed today

