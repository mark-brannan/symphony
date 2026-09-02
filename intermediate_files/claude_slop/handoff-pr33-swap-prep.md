# Handoff — finish the HALOS swap prep and PR #33

**Model: Fable 5.1 (Opus 5 acceptable). Effort: high. Difficulty: medium-high** —
live hardware on a 2 GB box, a PR to slim, and a swap that may happen in the
morning. Predecessor: session `symphony-pr-33-review-601c06-0a`, stopped by the
usage window at ~07:30Z 2026-09-02.

**Read first:** `intermediate_files/claude_slop/halos-swap-execution-2026-09-02.md`
(what is done, measured), then `halos-b3-findings-2026-09-02.md` and
`halos-swap-preflight-2026-09-02.md` (the other session's evidence), then the
PR branch `claude/halos-boat-swap-trial-9e5d36` (checkpointed as `pr33-fable`
merged with main; scripts rewritten, runbook and plan NOT yet updated).

**At 07:35Z Mark's Opus session (`handoff-halos-b3-62a913-a6`) was working
i2c on the bench box — check `ListAgents`/message it before touching halos.**

**Mark's standing calls tonight:** bypass permissions is on; do the work, ask
only what is genuinely his. Defaults he accepted: secrets move by pipe and
never print; DNS write path may be exercised; the trial accepts local Authelia
logins only, no pre-swap history, pypilot verified only at the boat; the bench
card is ours to stop/reboot. Keep AvNav/OpenCPN disabled (staydown). One
session on the bench box at a time; the `handoff-halos-b3-62a913-a6` session
is paused by Mark and owns monitoring posture + plugin detail if resumed.
`~/.local/state/claude-tmpdir/.../scratchpad/hs` is gone with the old session;
recreate the sudo pattern: `sops -d --extract '["symphony_halos_pi_password"]'
secrets/symphony.sops.yaml | ssh pi@192.168.0.193 "sudo -S -p '' bash -c '<cmd>'"`
(never combine with a heredoc on the same stdin).

## Do, in order

1. **Cold-start check.** SignalK on halos was restarted at 07:28Z for the new
   domain; a cold start takes 3–4 min there. `docker ps` must show
   `signalk-server ... (healthy)`; if `unhealthy`, the override did not apply —
   `systemctl cat marine-signalk-server-container | grep symphony.override`.
2. **B5a Traefik router — installed 07:33Z; only the `/sso/` confirmation is
   left** (see the execution file). Original instructions, for reference: write `/etc/halos/traefik-dynamic.d/symphony-signalk-host.yml`
   from the plan (B5a), literal host `signalk.symphony.dark-star-llc.com`,
   `url: http://host.docker.internal:3000` (HALOS's own
   `signalk-server-icons.yml` uses exactly that, so it resolves). HALOS's own
   SignalK router is priority 2 on entrypoint `app-4430`, not `websecure`, so
   priority 50 on `websecure` collides only with Homarr (priority 1) and
   Authelia (`/sso`). Verify the five curls with `--resolve`
   (`curl -sk --resolve signalk.symphony.dark-star-llc.com:443:127.0.0.1 https://signalk.symphony.dark-star-llc.com/`
   → 200 SignalK; `/sso`, `/sso/`, `/ca`, `/ca/` → not SignalK). If it
   misbehaves, delete the file.
3. **Swap check fixed and re-verified against the boat at 07:34Z** (PR head
   after commit "N2K liveness from any n2k-can0 value"). Left for you: the
   preflight has never run end to end against halos. Details of what was
   fixed, for context:
   - `n2k`: position on the boat comes from `signalk-fixed-position`; test N2K
     liveness as "newest value with `$source` starting `n2k-can0` anywhere in
     `vessels/self` is < 60 s old" (water temperature was 5 s old).
   - `devices`: `ls` prints `/dev/i2c-1` before `/dev/serial0`; test each node.
   - `front`: Caddy on the boat needs SNI — `curl -sk --resolve signalk.<domain>:443:127.0.0.1 https://signalk.<domain>/signalk`
     (accept 200 or 302); Traefik on halos `:4430` the same way. `boat_domain`
     is in sops; the script runs from a machine with sops.
   - `questdb`: the boat's QuestDB is overloaded (see the execution file);
     `select ts from signalk limit -1` and `max(ts)` both exceed 40 s there.
     On halos (WAL tables, designated timestamp) `limit -1` is instant. Use a
     30 s timeout and print "timed out" as its own state rather than FAIL, or
     find a metadata-cheap query; the runbook must say what a timeout means.
   Same `front`/`questdb` fixes in `scripts/halos_preflight.sh` (it also has
   the authenticated plugin parity check — untested against halos yet).
4. **Run the preflight for real:** `scripts/halos_preflight.sh` (defaults to
   `symphony-halos`). Expect FAILs for `services` (questdb/grafana stopped)
   until the soak. Fix script bugs, not thresholds, unless a threshold is
   wrong in fact.
5. **Soak (B6).** With zram in place (1 GB zstd, priority 100) try the full
   stack on the bench: `systemctl start marine-questdb-container marine-grafana-container`,
   watch `free -m` and `grep ^pswp /proc/vmstat` for five minutes. If it holds,
   reboot once and re-run the preflight; every line must be ok except what
   only the boat can satisfy (none, by design). If it thrashes, stop the
   databases again — that outcome is a bench limit, not a card defect
   (boat arithmetic in `halos-swap-preflight-2026-09-02.md`), and the
   runbook says so. After any reboot `docker stop homarr` again on the bench.
6. **Docs, then the PR.** Update `intermediate_files/claude_slop/halos-swap-plan.md`
   from the execution file (B1a i2c-dev; B2c hostnames.conf order; B3c: the
   B3 session's throwaway-container + native-module recipe; new item "healthcheck
   override"; B4a/B4b/B4c done; heartbeat = second check). Rewrite the RUNBOOK
   section with the real preflight and baseline output, the rule "a line that
   FAILs in the baseline and after the swap is a boat problem", the expected
   "boat check goes late" healthchecks.io notice on swap day, and the
   pre-existing boat issues (Cerbo MQTT, fixed position, QuestDB load). Land
   the claude_slop files on main directly, then merge main into the PR branch
   so the PR diff is only: RUNBOOK section, `reference/system_map.md`,
   `reference/containerization_strategy.md`, the three scripts, and the new
   `host/halos/` files (put `symphony.override.yml` and the drop-in there as
   the source of truth). Push with `git push --no-verify` — the Mergify stacks
   pre-push hook refuses plain pushes; that is its own documented bypass.
   Rewrite the PR body: what to read (runbook section + swap-check thresholds),
   what is verified, what only the boat can test.
7. **Swap-day dispatch prompt** into `intermediate_files/claude_slop/`: the
   at-boat sequence with the exact commands, what Mark does by hand (cards,
   Micro-C, phone cert), what a session does (checks, DNS), and rollback.
   Name model and effort.

## Not started, decide with Mark

- **pypilot (B4d)** — not installed on halos. The boat card runs it natively
  (`pypilot-sk` publishes attitude). Trial without it, or install per B4d.
- **PR #34** must merge before or with #33: halos runs its branch
  (`claude/ble-check-dual-unit`) for `host/install.sh`.
- **Cerbo MQTT** is dead on the boat (all ports closed since 2026-09-01 21:06Z).
  Only Mark can look at the Cerbo / VRM. The `victron` line fails on both cards
  until then.
- **Boat load** 11.8 with 13 logged-in users and QuestDB at 164 % CPU — worth
  a look before the swap so the baseline is taken on a calm box.
