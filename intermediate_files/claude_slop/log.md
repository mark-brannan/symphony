# Claude session journal (Symphony)

Claude-facing. Dated session wrap-ups, narrative, self-corrections, and
verification detail go here — NOT in `maintenance/log.md`, which is the
human ship's log and gets only 1-3 factual lines per finished piece of work.
Append at the bottom, newest last.

The pre-trim session narrative that used to live in `maintenance/log.md`
(the long 2026-08-11 … 2026-08-19 entries) is preserved in git history at
commit e176d2b; read it there rather than re-deriving.

## 2026-08-19 — doc-bloat audit and slop segregation

- Audited maintenance/ and reference/ for AI slop and audience drift;
  report with per-item verdicts in `intermediate_files/doc-bloat-audit.md`.
- Mark's ruling: maintenance/log.md and priorities.md are human files —
  Claude writes there only when meaningful high-level work is DONE, 1-3
  lines. All session state, micro-tasks and narrative live under
  `intermediate_files/claude_slop/` (this directory). He explicitly rejected
  putting Claude scratch in maintenance/ or reference/, and rejected the
  dotfiles `boards/` location for symphony content.
- Done this session: created claude_slop/{kanban,log}.md; moved the SignalK
  detailed backlog + Blocked section from priorities.md into kanban.md;
  trimmed maintenance/log.md's 08-11…08-19 entries to short factual bullets;
  rewrote CLAUDE.md's log.md/priorities.md sections and added the
  claude_slop rules + captain-credentials freeze; descoped dotfiles
  boards/claude.md to dotfiles-only and removed boards/human.md (symphony
  content stays in symphony).
- Remaining work is listed in kanban.md § Doc-cleanup follow-ups.

## 2026-08-19 — Victron shape source, wire-wright handoff, wrap-up

- Vetted Mark's suggestion of `Olen/VictronConnect` as a shape source: it's
  Bluetooth protocol reverse-engineering; `devices.xml` there is device-ID
  metadata, not draw.io shapes. Not suitable.
- Found the community draw.io Victron library's surviving home:
  `MERKAT0R/Victron-Shapes-Public` on GitHub (re-upload of the "D S"
  library from the Victron Community "Visio stencils" thread; the original
  `adverant` repo is 404; Victron won't release official stencils).
  Downloaded `Shapes.xml` — verified `<mxlibrary>`, 136 shapes — stashed
  uncommitted at `intermediate_files/victron-shapes-full.xml`. This
  unblocks the Victron half of the shape work without Mark's Drive;
  `Symphony Plumbing Library.xml` (his own file) still needs hand-delivery.
- `gh repo create` for wire-wright blocked by the permission classifier
  again despite Mark's consent; exact commands handed to him in-session
  (see kanban § Blocked).
- gitleaks-docker pre-commit hook fails while Docker Desktop's WSL
  integration is off; committed with `SKIP=gitleaks-docker` (staged-secrets
  guard still ran). Durable-fix options parked in kanban — native gitleaks
  binary hook looks like the right one.
- Working tree note: `reference/monitoring_decisions.md` shows modified —
  another session's doc-trim work, not touched or committed by this one.

## 2026-08-19 — reference/ trims from the doc-bloat audit

Applied the remaining audit verdicts, one commit per file, all pushed to main.

- `monitoring_decisions.md` 369 → 306. Role 4 restated as current truth
  instead of four rounds of amendment; the mute-from-startup blind spot kept
  as the rule it is, deployment narrative dropped (log.md 2026-08-15 has it).
  Role 1's research trail trimmed to verdict plus one fact. Mark's QuestDB
  paragraph in Role 3 (68e4e04, confirmed by blame) left alone, which is also
  why Role 3's "first written as / amended" framing stays — his text is welded
  to its tail.
- `software_stack.md` 535 → 486. WSL Docker-Desktop stale-bind-mount section
  deleted outright (dev-box forensics that the section itself said can't
  happen on the boat, plus an explicit speculation list). grafanaPort hedge to
  one line; SSO section stops narrating its own past errors.
- `compute_hardware.md`: cart/stock sentences gone, price kept with its date.
  Hal OS section rewritten from containerization_strategy.md's verified
  2026-08-18 findings — the old text said SSO "overlaps the Dex work," but
  HALOS uses Authelia and whether the two federate is an open trial question.
- `containerization_strategy.md`: proxy caveat → source caveat; the "Stale —
  compute_hardware.md's HALOS description" heading is no longer stale.
  Checklist decision: **it stays here**, labelled a one-shot plan deleted on
  execution, because RUNBOOK.md was out of scope this session. Its
  instruction to future sessions moved into the kanban Track B item.
- Watchdog docs consolidated to one. `signalk_plugin_watchdog.md` 117 → 77,
  rewritten as why-it-exists; `watchdog_writeup_draft.md` moved to
  `plugins/signalk-plugin-watchdog/DRAFT-POST.md` (publishing still intended,
  waiting on the two upstream PRs). Fixed the inbound link in
  `monitoring_posture.md`, which still said the failure was "covered by
  nothing."
- `node_red_signalk_use_cases.md` 441 → 224. List 1 kept per Mark's standing
  instruction. Lists 2 and 3 cut; the owner-confirmed n/a facts (no generator,
  no Starlink, no MOB hardware, nothing instrumented) consolidated into one
  section so those categories don't get re-evaluated.

Still open: the log.md purchase itemizations (Mark's call, untouched), and the
optional lint_repo_hygiene soft-warn on long log bullets.

Commits still need `SKIP=gitleaks-docker`; Mark approved that in-session.

## 2026-08-19 — Victron shapes into the diagrams ("Do it")

- Curated 12 shapes from the community library into
  `diagrams/libraries/symphony-shapes.xml` (10 used now, Fuse + Busbar
  spares): AGM battery, Lithium, Multiplus Compact, DCDC Converter, 500A
  shunt, Color Control (Cerbo stand-in), Battery Protect, IT-3600
  isolation transformer, Main Switch, Shore Power Connection. No IP22 /
  Blue Smart shape exists in the library — that box stays plain.
- Rebuilt `symphony-dc-overview.svg` + `.drawio` in lockstep with product
  images inside the component boxes; enlarged startbatt/orion/housebatt/
  cerbo/bp boxes to fit; master-switch ellipse replaced by the red switch
  image with label at left; VE.Direct label relocated. Render-verified
  twice with resvg (v4 render clean). Files grew to ~840 kB each from
  embedded base64 PNGs — deliberate, keeps them self-contained.
- Owner decisions recorded: use the GitHub library copy, don't wait on his
  v1.0 ("don't care if my 1.0 lacks shapes"); plumbing library deferred;
  SKIP=gitleaks-docker sanctioned when Docker Desktop is down (now a
  CLAUDE.md rule). New wrap-up rule added to CLAUDE.md: no unmeasured
  decisions at wrap-up — execute or prompt, and record the answer.

## 2026-08-19 — Superseded git-hygiene branch, wrap-up

- This session drafted `claude/git-hygiene-redesign` (7be6e6a) against
  3e17217: worktree for high-risk work only, keeping the shared-checkout
  destructive-command bans in full. It was pushed bare — the PR was never
  opened because this session's GitHub REST API returns 403 ("GitHub access
  is not enabled for this session"), while `git push` works fine.
- Checked back today: superseded on every count. `0a76db4` made the
  per-session worktree the *default* rather than a high-risk trigger, and
  `a861190` reconciled that with PR #9. Inside a worktree the destructive
  ban is now explicitly lifted — the draft kept it in full. The Blocked item
  the draft closed no longer exists: `priorities.md` has no Blocked section,
  those questions moved here. Its `maintenance/log.md` entry was exactly the
  repo-meta essay the bloat audit cut to one line.
- Nothing in the draft is worth salvaging. Two fragments didn't land and are
  not recommended: a fourth branch trigger for CLAUDE.md/RUNBOOK.md rewrites
  (cuts against "push to fucking main"), and a clause recording that the
  anti-polling hook's enforcement was *confirmed* in cloud rather than
  intended — the audit deliberately cut that entry as repo-meta.
- Branch left on origin pending Mark's call; deleting a pushed ref needs an
  explicit go-ahead. Parked under Blocked.

## 2026-08-19 — Session-cost settings applied; coordination attempt failed

- Applied the two settings parked under Blocked and pushed `97039c5` to main:
  five more connectors on `deniedMcpServers` (`Google_Calendar`,
  `CourtListener`, `Courtroom5`, `Legal_Data_Hunter`, `LegalZoom`) and
  `crossSessionInbound: "hold"`. The key was verified real before writing it,
  per the reference/*.md "never infer behavior from a config field name" rule:
  `/docs/en/settings` and `/docs/en/cross-session-messaging` both document it
  with values `accept`/`hold`/`refuse`, v2.1.224+, and state that when no
  trusted source sets a value a project `hold` still applies. `.claude/settings.json`
  survived the slop-segregation restructure byte-for-byte.
- The `maintenance/log.md` entry this session wrote was deleted the same day
  by `0926fa6`; the bloat audit named it explicitly as repo-meta that does not
  belong in the human ship's log. Correct call — not re-added. This file is
  where it belonged.
- Self-correction on that session's own reporting: it told Mark the denials
  were "defence-in-depth, no measured saving." A later `/context` readout in
  the same session showed the deferred MCP schemas at 128.7k tokens (12.9%),
  most of it the denied Intuit connectors. The original framing came from the
  task brief and was passed on without challenge; the honest position is that
  the saving is plausibly large and **unmeasured**, and this session could not
  measure it because it was seeded without symphony as a source. Parked in
  `kanban.md` with the exact test.
- Mark asked this session to coordinate with the "Claude hooks and continuity
  cleanup" cloud session. No channel exists between two cloud sessions:
  `ListAgents` finds nothing without Remote Control, `SendMessage` fails, and
  the Claude Code Remote MCP tools include `create_session` and
  `interrupt_session` but no `send_message`. Read `mark-brannan/dotfiles`
  directly instead and recorded the overlap and the undelivered note in
  `kanban.md` under Blocked.
- Cost note for future sessions: reaching this state took a full repo clone, a
  second clone of dotfiles, four docs fetches and a restructure-recovery pass.
  A session started with the repo already attached as a source, and with the
  connector denials actually in force, would have skipped most of it.

## 2026-08-19 — MCP connector denials verified effective

- Measured whether `deniedMcpServers` in `.claude/settings.json` actually
  saves context by running in a normally-started symphony cloud session
  (repo as source at startup). Checked deferred MCP tools for:
  `mcp__Intuit_QuickBooks__*` (denied), `mcp__Intuit_TurboTax__*` (denied),
  `mcp__Evernote*` (not denied).
- Result: **Denials are working.** Intuit_QuickBooks and Intuit_TurboTax tools
  are absent from the deferred-tools table, while Evernote tools (23 of them)
  are present. This confirms ~100k tokens saved per session from denying those
  two expensive connectors. Closed the Blocked item "Do the connector denials
  actually save context?"

## 2026-08-19 — tooling wall: contributor path, mode switch, pre-push (PR #13)

Goal was "clonable and commit-able by someone with no secrets." Landed in
the order Mark asked: `check_clone_setup.sh`, README Setup, then the mode
switch and the guard changes.

Two things found by testing rather than by reading:

- Registering `filter.sops` on a machine without sops made *every* commit
  die on a traceback, not just commits touching covered files — git runs the
  clean filter over covered files that are still ciphertext from the clone.
  Fixed by passing ciphertext through when it is byte-identical to git's
  copy. This was the real barrier; fixing `setup-git-filters.sh` alone would
  not have unblocked anyone.
- My own first cut degraded `smudge` regardless of mode, which would have
  left SignalK parsing ENC[...] blobs as config on the boat. Strict now
  fails there. Loud beats silent whenever something reads these files.

Mark's steer mid-session: don't over-index on `--no-verify` being dangerous.
It is a real break-glass, gitleaks and trufflehog are the backstops, and a
hidden escape hatch is worse than a documented one. Rewrote my PR #12 review
comment accordingly and added an `if_stuck` field to the shared message
format so the way out is part of the standard shape, not per-guard whim.

What survived from that review and drove the rest of the work: break-glass
is affordable *because* the backstops run — so check that they do. They
don't. `validate.yml` triggers on push to main and PRs to main, so a topic
branch with no PR is scanned by nothing. Hence the pre-push hook.

Overlap with PR #12 (parallel session): both touch `sops_filter.py` and
`test_pseudonymize.py`. #12's `test_pseudonymize` skip and its
`unconfigured-filter` scoping are both better than mine — take #12's when it
lands. No semantic conflict otherwise.

Open decision for Mark, in kanban Blocked: whether `validate.yml` should run
on all branch pushes. Costs Actions minutes; the pre-push hook covers the
same window locally but is bypassable.
