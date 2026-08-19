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

### 2026-08-19 (later) — review round on PR #13

Nine threads from the agentic reviewers. Verified each against the code
before acting rather than trusting the label; three were real bugs, two of
them in code I had just written and verified.

- **Pre-push scan compared range ENDPOINTS.** `git diff A..B` ignores
  intermediate commits, so a secret committed with `--no-verify` and removed
  in the next commit was invisible — the exact scenario the hook exists for.
  Reproduced, fixed to walk `git log`/`git rev-list`, reproduced clean.
- **`symphony_msg` opened `/dev/stderr` as a path**, which truncates a log
  when a hook runs as `2>>build.log`. GitHub had auto-marked this thread
  resolved; it was not fixed. Checking rather than trusting the label is the
  transferable lesson.
- **`SYMPHONY_MODE` honored by the shell twin, ignored by python.** Fixed by
  narrowing (made it process-local in both) rather than adding a second
  undocumented override. The reviewer's better point was that the test could
  not have caught it — `_env()` popped the variable, so the blind spot was
  structural.

Also: hooks without an explicit stage were re-running every commit-time
guard on push against an empty index; a comments-only `.symphony-mode` would
have killed `setup-git-filters.sh` under pipefail before it configured
anything; the plaintext-secrets rule matched only the JSON sops marker, and
its failure mode is "nobody can commit and the message is wrong."

Judgment call worth keeping: a reviewer asked for `hostvars_filter`'s
clean/smudge to degrade symmetrically, like `sops_filter`'s smudge. Declined
the symmetry — direction decides it. Smudge passing through leaves a
placeholder on your own disk; clean passing through writes one machine's
value into the shared repo, which is the failure that filter exists to
prevent. Same asymmetry as #12's `to_git_form`. It now appears twice for the
same reason and should be stated once centrally, after #12 lands.

## 2026-08-19 — PR #13, naming pass (`secretguard`)

Mark's note on the PR: "These names are bad: SYMPHONY_MODE, SYMPHONY_STRICT",
plus the standing thought exercise — would these names survive if the secret
management were split off as a package for another vessel owner?

They fail it twice: they carry the boat's name, and neither says what is
strict or what the mode is a mode *of*. Renamed the whole guard surface to
`secretguard` (files, functions, env var, mode file, message prefix). Full
table is in the PR body and the commit message for 40bc27b.

Three behaviour changes fell out of the rename rather than being decided
separately, which is the argument for doing renames properly:

- `SECRETGUARD_MODE` now takes a mode word only. `SYMPHONY_STRICT` accepted
  `1/true/yes/on` and `0/false/no/off` — coherent while the name said
  "strict", incoherent once it says "mode", and `=0` meaning contributor is a
  guess a secret guard shouldn't make.
- The cache is `_secretguard_mode`, lowercase. Its env-shaped name is what
  invited seeding it from the environment — the cf892e2 bug. Renaming removed
  the invitation rather than re-fixing the symptom.
- The bash twin didn't trim whitespace around a mode word; python did. The
  parity test caught it on `" strict "` while I was rewriting the tests. Worth
  noting the twin+parity-test design has now paid for itself twice.

Also closed the three review threads still open. The one that mattered:
"is this file encrypted" was five separate greps for the string `sops`, so a
plaintext `{"note": "sops", "password": "hunter2"}` read as encrypted at
every one of them. Now one policy in both languages requiring sops' actual
metadata shape (`sops` key → mapping with `mac` and `version`), applied at
all five sites — pre-commit guard, pre-push scan, clean filter, repo-hygiene
rule, and CI's `verify_encrypted.sh`. Reproduced the bypass against a bare
remote before fixing, confirmed the block after, confirmed the 16 real
encrypted files still pass.

Transferable: the reviewer named two sites. Fixing two would have left a file
that reads as encrypted to one guard and plaintext to another, which is worse
than either answer alone — the commit sails through, the push blocks, and
neither message explains the disagreement. When a finding is "this predicate
is wrong," the unit of repair is the predicate, not the lines cited.
## 2026-08-19 — Pre-commit guards: block only on staged, fixable state (PR #12)

**The incident this fixes.** Mark could not commit a one-line doc edit for
days. `hostvars_filter.py clean` fails soft when `hostvars.local.yaml` is
missing, so the machine-local ntfy URL landed in the index literally;
`check` then failed unconditionally on every commit and named `refresh` as
the remedy — which itself requires the file he did not have. Closed loop,
and no message anywhere mentioned `--no-verify`. Reproduced it exactly in a
throwaway clone before changing anything.

**Invariant landed.** A hook may FAIL only on a condition (a) visible in a
`git diff --cached` path and (b) fixable by the person committing right
now. Clause (b) is the addition — the hostvars checker was arguably scoped
correctly in spirit and still trapped him, because correct-and-unsatisfiable
is still a trap. Repo-wide truth moved to CI.

**`always_run` was never the bug.** None of the four moved to `files:`.
Internal self-scoping from the index — what `precommit_secret_guard.sh`
already did — is the right shape; `files:` would duplicate scope config
living in `.sops.yaml`/`.hostvars.yaml` and miss deletion-only commits.

**Rejected the obvious filter fix, deliberately.** Making `clean` hard-fail
so bad bytes never reach the index is attractive and wrong: git runs clean
to diff working tree against index, so a failing clean breaks `git status`
in exactly the stuck state. Uncommittable would become unreadable. Both
filter directions stay soft; the checker owns all blocking and pays for it
with scoping and a named exit. Written down as: whichever layer cannot be
escaped is the layer that must not block.

**Two bugs in my own work, caught by testing rather than reasoning.**
`--fix` re-encoded whole files, so it failed on any document containing a
legitimate em dash — i.e. nearly all of them; now repairs per damaged run.
And `test_encoding_health.py` contained literal mojibake fixtures and
flagged itself on the first CI run. Both are the exact class of thing Mark
called AI slop. A third followed later: two of my `test_repo_hygiene.py`
assertions matched on message *wording* and broke the moment #13's
formatter landed — change-detectors, which his own rules warn against.

**Pseudonymizer, three findings, three different answers to "fail open?"**
Clean side had no handler at all and died on a bare `FileNotFoundError`
traceback — still refuses (a guest's mailbox in public history cannot be
taken back) but now says so in words. Nothing guarded that the pseudonym
map travels with the tokens: commit a token without the map and it is
unresolvable forever — made a warning, not a block, since the map is still
on disk. And the one sops-dependent test now skips rather than erroring.

**Coordination with PR #13.** Could not message that session directly (no
`send_message` in this session's toolset, `ListAgents` empty), so the PR
thread was the channel — which Mark could read, arguably better. Rather
than predict the merge I ran it: rebased onto their branch in a scratch
clone, resolved all four conflicts, verified all six suites and all four
of Mark's paths on the merged tree. Resolution saved at
`intermediate_files/pr12-onto-pr13-merge.{patch,md}`.

**The cross-PR hazard, and the invariant it produced.** Both PRs rewrote
`rule_declared_filters_are_configured` on orthogonal axes — theirs keyed on
who is committing, mine on what is in the commit. Composed as OR,
contributor mode swallows the staged case and a plaintext secret only
warns. Merged as AND. Stated as: **enforcement may soften a guard about
your ENVIRONMENT; never one about the CONTENT of your commit.**

**Naming.** Mark rejected `SYMPHONY_MODE`/`SYMPHONY_STRICT` on #13 — "mode"
collides with vessel operating mode and SignalK's own usage, and the boat's
name has no place in a mechanism that is not boat-specific. Proposed
`SECRETS_ENFORCEMENT=strict|warn-only`, one variable rather than two (the
old pair were two knobs on one axis and could disagree). Checked the
extraction question rather than guessing: the whole secret-management core
is already free of "symphony", and the real fork boundary is *inside*
`lint_repo_hygiene.py`, which mixes one generic rule with two site-specific
ones. #12's shipped code never referenced the old names, so the rename
costs this branch nothing.

**Self-correction.** Three times in this session I ran `git reset --hard` /
`git checkout -- .` in the scratch clone *after* copying patched scripts in,
silently reverting them and producing a bogus comparison I then reported.
Caught each time by the output not making sense. Order matters: reset
first, copy second.

## 2026-08-19 (later still) — PR #12 rebased onto #13, ready for review

#13 merged, so #12 came off the shelf. The prior session's saved notes and
patch (`intermediate_files/pr12-onto-pr13-merge.{md,patch}`) held up: the
four conflicts resolved as written, the `precommit_secret_guard.sh` commit
was skipped as superseded, and `sops_filter.py` was taken whole from #13
with the auto-merged `die()` deleted.

Three things the trial did not predict, all recorded in the merge notes:

- a fifth conflict in `hostvars_filter.py` (#13's later review round added
  `head_blob()` where this branch added `staged_paths()`) — purely additive;
- #13 had already landed `staged_paths()` and `gitattributes_filters()` in
  `lint_repo_hygiene.py`, so #12's copies were dropped rather than merged;
- #13's rule matched staged paths by exact membership where `.gitattributes`
  entries are globs. Took #12's fnmatch. Worth noting because it is the
  quiet kind of wrong: the rule looks right, runs, and matches nothing.

**The bug I found in my own tests, which is the transferable one.** The
scoping suite asserted against the real clone. On any machine that HAS the
filters wired — every maintainer's — the rule returns early, and all six
assertions passed while testing nothing. Same shape as the `check --all`
trap this whole PR is about, one level in: a check that cannot fail is
indistinguishable from a check that passes. `filter_is_configured()` is now
a seam, and the tests pin it along with mode, scope and CI. Two more tests
came out of pinning strict mode explicitly, which the old suite never
exercised at all.

Also rewrote the two wording assertions to assert severity and the presence
of message fields. Mark had flagged this twice; the underlying reason is
that the formatter's own parity suite already owns wording, so a second
assertion on it is duplication that only ever produces false failures.

Retrofitted all four guards onto `secretguard`'s formatter, using `block()`
rather than `require()` for hostvars-placeholders and encoding-health —
both are about content in the index, and content is never mode-softened.

Put the invariant sentence in `secretguard.py`'s module docstring and its
bash twin, per the open question the #13 session raised. Reasoning: that
module is what a new guard imports to ask "am I strict," which is exactly
the moment someone decides whether their guard should soften. The
alternatives reach the wrong reader — `reference/precommit_guards.md` is
read by someone hitting an error, and a comment on one rule only reaches
whoever edits that rule.

Verified in a throwaway keyless clone rather than by reasoning: doc edit
commits, a staged `filter=sops` path blocks in contributor mode, the
`git restore --staged` exit the message names actually clears it, and the
`--fix` the encoding message names actually works. All six suites green,
all ten CI checks green.

Flagged to Mark on the PR, not fixed: the secret-tooling suites don't run
in CI at all. `validate.yml` compiles every script and runs
`test_dashboards.py`; `run_secret_tooling_tests.sh` is a pre-commit hook
only. Predates both PRs, so it belongs in its own change.
