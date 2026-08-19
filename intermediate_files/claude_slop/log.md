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
