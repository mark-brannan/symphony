# Ready-to-paste handoff prompts — 2026-09-02

## 1. Role 4: off-boat freshness check

**Model: Opus 5. Difficulty: medium.** One shell script plus a
healthchecks.io check; the plumbing it reuses is already live. The hard part
is judgment about which paths matter, not code. Expect one round of decisions
back to Mark mid-session.

---
Build Role 4 of `reference/monitoring_decisions.md` — the off-boat freshness
check — and retire `signalk-healthcheck` once it is covered.

Read `reference/monitoring_decisions.md` (Role 4 and Role 1),
`reference/monitoring_posture.md` (the `signalk-healthcheck` section and the
Gaps section) and `reference/signalk_plugin_watchdog.md` first. The decision
record scopes this at "one script, an afternoon" and says it reuses the
existing `host/boat-heartbeat` + healthchecks.io plumbing, which is deployed
and live-tested — do not build a second mechanism alongside it.

What it must do: check the *age and existence* of a set of critical SignalK
paths, and `/fail` a second healthchecks.io check when any is stale or was
never published. "Never published" matters — it is the gap that
`signalk-data-age-watchdog` cannot cover.

Do not block on Mark for the path list. Instead:
1. Read what is actually publishing on the boat (`ssh pi@symphony-pi`, the
   SignalK REST API on localhost:3000) and produce a candidate list of
   critical paths with a proposed staleness threshold for each, with the
   measured current update cadence next to it so the threshold is justified
   rather than guessed.
2. Bring Mark that list as one accept/edit/delete decision — a short table,
   not an open question. Recommend a default.
3. Then build it, deploy it, and verify it end to end by actually letting a
   path go stale (or simulating it) and confirming the check goes red.

Then: retire `signalk-healthcheck`. Its provider watch is the only thing it
still does (host section already disabled 2026-08-14). Confirm the new check
covers the `n2k-can0`-goes-quiet case before disabling it, and record the
retirement in `maintenance/log.md` and the correction in
`reference/monitoring_decisions.md`.

Context worth carrying: signalk-healthcheck delivers through the Pi it is
watching, so it is silent in exactly the unattended-failure case that
matters most. That asymmetry is the reason this work exists.

Branch-vs-main: this touches monitoring infra with real blast radius if left
half-applied — use a branch and open a draft PR.

---

## 2. Card review session

**Model: Sonnet 5. Difficulty: low**, but long — it is reading and triage, not
building. Use Opus 5 only if you want it to argue with the cards rather than
summarize them.

---
Review every open card and tell me what to drop.

Read `intermediate_files/claude_slop/kanban.md` (both `## Yours` and
`## Claude's`), its detail file `kanban-detail.md`, and the global board at
`~/claude_prompts_scratch/state/global/kanban.md`. Also check
`maintenance/priorities.md` for the human-facing SignalK/IoT list.

For each card, tell me in one line: is it still real, is it already done, is
it blocked on something that will never arrive, and is it a duplicate of
another card. Verify before asserting — a card claiming a PR is open should
be checked against the actual PR state (use `merged_at`, not `merged`, on
list responses), and a card describing work on the boat should be checked
against the boat.

Then give me three lists: **delete** (done, stale, or duplicated), **keep**,
and **needs a decision from me**. Recommend a WIP set of 2-3 from the keep
list, ordered.

Do not reorganize the boards, rewrite cards, or start any of the work. This
is triage. Make the edits only after I say which deletions to take.
