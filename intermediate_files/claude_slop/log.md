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
`intermediate_files/pr12-onto-pr13-merge.{patch,md}` (the patch
half was deleted once the real rebase landed; see the notes).

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

PR #13 merged, so #12 came off the shelf. The prior session's saved notes and
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

### 2026-08-20 — PR #12 review rounds: one bug shape, five times

Five review rounds with two agentic reviewers after the rebase. Everything
raised was verified against the code before acting; two findings were real
bugs in code this branch had just written, and one was a fail-open nobody
had asked about.

**The thing worth carrying forward.** Every substantive finding this
session was the same shape: *a check that never looked, reporting ok.*

1. `hostvars_filter.py check` without `--all` in CI — nothing is staged
   there, so it passed vacuously and repo-wide enforcement vanished.
2. The scoping tests asserted against the real clone, where the filters
   ARE configured, so the rule returned early and six assertions passed
   while testing nothing. Fixed with the `filter_is_configured()` seam.
3. My staged-blob test stubbed `staged_blob` but not `git ls-files`, so an
   absent fixture would yield nothing and pass without calling anything.
4. `git diff --cached --name-only` quotes any non-ASCII path
   (`core.quotePath` defaults on), so `café.json` matched no covered
   pattern and left the guard's scope silently.
5. **My own reasoning.** I read one page of `list_branches`, saw
   `protected: false` on every row, and concluded `main` was unprotected —
   `main` was not on that page. I wrote that into
   `reference/precommit_guards.md` and told two reviewers it was verified.
   `main` is `protected: true`.

Four in the guards, one in me, and the last one shipped furthest. The
lesson is not "be careful" — it is that *absence of a signal is not a
negative result*, and the fix in each case was to make the check unable to
run without looking: stub every input a test reads, pin the seam, ask for
NUL-delimited output, and read the row you are drawing a conclusion from.

**Also fixed, all reproduced first:** the staged encoding scan read the
working tree rather than the index (wrong in both directions after
`git add -p`); `--fix` returned 0 on a file that still blocked, so its own
advice looped; a C locale turned a non-ASCII path into a
`UnicodeDecodeError` and took the hook down with a traceback — the exact
failure mode this branch exists to remove.

**Practice that paid for itself:** for the C-locale regression test I
reverted the fix, watched the test fail, restored it, watched it pass. A
regression test nobody has seen fail is finding #3 again.

**Declined, with reasoning on the PR:** `rule_frozen_secrets_untouched`
reads `git diff --cached` and CI's index is empty, so it is vacuous under
`--all` — finding #1 in a rule this branch never touched. Pre-existing;
the fix needs a change-range interface plus workflow wiring, which is a
design change to how CI expresses "what changed". In kanban for Mark.

**Open for Mark, both in kanban Blocked:** which status checks (if any)
are *required* on `main` — `protected: true` does not say, and it decides
whether "CI is the enforcement boundary" is true at all; and the fact that
nothing automated runs the secret-tooling suites today (not `validate.yml`,
and both reviewers were denied permission to execute them).

Correction, same day: when first written that sentence said "both in
kanban" and only the first one was — the suites question existed solely in
this PR's comment thread, which is precisely the "session scrollback" that
CLAUDE.md's park-it rule exists to keep questions out of. A reviewer
caught it. Worth noting that *stating* a question is open is not the same
as parking it where the next session will look, and I had done the former
while claiming the latter.


## 2026-08-19 — Verified heading/COG derivation live on the boat

Independently ssh'd to `symphony-pi` and checked the other session's
`derived-data.json` change (cog_true, heading, magneticVariation flipped to
`true`) against the running system, rather than trusting the diff alone.

Findings:
- The live `~/.signalk/plugin-config-data/derived-data.json` already
  matched the committed change — someone (or something) had saved it
  through the SignalK admin UI around 17:27 PDT, ~1.7 hours before the
  commit landed on `main`. The repo checkout on the boat itself
  (`~/symphony`) is many commits stale (`68e4e04`, from the MOB-detection
  work) and unrelated to how the live config got there — worth noting for
  anyone who assumes `git pull` on the boat is what ships config changes;
  it isn't, the admin UI writes `~/.signalk/plugin-config-data/*.json`
  directly and the repo copy is a tracked mirror, not the source of truth.
- `signalk.service` hadn't restarted (`ActiveEnterTimestamp` still Aug 16),
  but the wrapped `node` process had — a new PID appears in `journalctl`
  right after the config save, consistent with SignalK's own plugin-restart
  mechanics rather than a systemd restart. No `derived-data`-related errors
  in the log window around the save.
- `navigation.headingTrue` is live, `$source: derived-data`, and numerically
  correct: fetched `headingMagnetic` + `magneticVariation` in one API call
  and confirmed they sum to the reported `headingTrue` to within rounding
  (checked twice, a minute apart, values were moving so a stale cache was
  ruled out).
- `navigation.courseOverGroundTrue` stayed on `$source: n2k-can0.2` — the
  `cog_true` calculator needs `courseOverGroundMagnetic`, which doesn't
  exist on this boat (confirmed 404 on that path); the boat's GPS already
  publishes true COG natively, so the calculator has nothing to derive and
  is correctly inert, not broken.
- `magneticVariation` now has two competing sources (native `n2k-can0.2` and
  the newly-live `derived-data` WMM 2025 calculation); the native one keeps
  source priority, so nothing regressed there either.

Updated `reference/signalk_paths.md` to stop claiming `headingTrue` is
absent (it documented the exact "calculators set to false" state that no
longer holds) and closed the item out of `priorities.md` and this file's
kanban.
## 2026-08-19 (later still) — CI: close the unscanned-branch-push window

**Problem.** `validate.yml` fired on `push: branches: [main]` and
`pull_request: branches: [main]`. A `claude/*` branch pushed without a PR
matched neither, so gitleaks and trufflehog never saw it. PR #13's
`scripts/prepush_secret_scan.sh` covers the same window locally, but
`git push --no-verify` skips it; CI can't be skipped from a laptop.

**The fact that resized the question.** `mark-brannan/symphony` is public,
so Actions on standard runners is unmetered — every option on the table
cost $0. The real currencies were wall-clock, check-row noise, and what the
bill would be if the repo ever goes private. Measured baseline from run
`32307681599`: 9 jobs, ~30s wall, 9 billed job-minutes (each job rounds up
to a minute); the four secret jobs are 46s of compute, 4 job-minutes.
Branch-push volume from the last 200 runs: ~22 on the busiest day
(2026-08-19), 0 on quiet ones.

**Options Mark asked about, and the answers.**
- *Split the secret jobs onto a wider trigger* — sound, and taken. Note the
  mechanical constraint: `on:` is per-workflow, not per-job, so splitting
  means a second file or `if:` guards. Second file was cleaner.
- *`paths:` filter* — rejected, and Mark's suspicion was right for a reason
  he hadn't named. Two independent failures: (1) gitleaks exists to catch
  strings in files sops was never told about, so a path allowlist is a
  second list-of-files-we-thought-about gating the tool whose job is the
  gaps in the first; (2) scope mismatch — both scanners run `fetch-depth: 0`
  over full history, so gating a whole-history scan on one push's changed
  files skips it whenever the newest commit only touched a README.
- *Size/heuristic gate* — same allowlist flaw plus custom logic to maintain,
  to save 46s of free compute.

**Landed** (three commits, straight to main, each verified before the next):
`9ec5095` adds `secret-scan.yml` with the four jobs *while they were still
in validate.yml* — deliberate duplication so no window had reduced coverage;
`e952e33` removes them there; `4fd5fc7` fixes the stale required-checks note
in this kanban.

`concurrency` uses `cancel-in-progress: ${{ github.event_name == 'push' }}`
rather than a bare `true`, so a rapid push series can't cancel the weekly
sweep of unchanged history — the one run whose entire purpose is firing when
nothing changed.

**Interaction with PR #13: none, checked rather than assumed.** #13 touches
21 files, none under `.github/workflows/`. Two near-misses steered around:
its `.pre-commit-config.yaml` hunk starts at line 7 and carries line 6 as
context, so editing line 6 was the one guaranteed conflict — left alone (see
Blocked); its RUNBOOK hunk is at ~2261, mine at 628. #13's body claims
"CI's gitleaks and trufflehog passes are what make `--no-verify`
affordable" — that was false for branch pushes until this change, so #13
lands more safely in either order.

**Verified against the real thing,** not just reasoned about: pushed a
throwaway `tmp/verify-secret-scan-trigger` ref with no PR — exactly the
unscanned case — and `Secret scan` fired, four jobs green, 18s, while
`Validate` correctly did not. Ref deleted.

**Not touched, pre-existing:** every run emits a Node 20 deprecation warning
for `actions/checkout@v4` and `actions/setup-python@v5`. Predates this work,
affects both workflows.

## 2026-08-19 — Enabled and verified cog_magnetic derivation

Follow-up to the heading verification above, per owner's ask: audited the
rest of the COG/heading key family for gaps. Found one real, low-effort one
— `navigation.courseOverGroundMagnetic` was entirely absent, and
`signalk-derived-data`'s `"course data".cog_magnetic` calculator (the
mirror of the `heading` calculator: derives magnetic COG from the native
true COG + magnetic variation, rather than the other way around) was off.
Everything else in that section (`dtg`, `setDrift`, `steer_error`,
`vmg_Course`, `vmg_Wind`) needs an active route or `speedThroughWater`
(no log impeller aboard), so those correctly stay inert. `headingCompass`
and `magneticDeviation` are also absent but not gaps: `pypilot` publishes
fused/corrected `headingMagnetic` directly and never routes through the
raw-compass/deviation stage. `rateOfTurn` isn't something this plugin
calculates at all.

Owner approved enabling it. Flipped `"course data".cog_magnetic` to `true`
in both the repo's `signalk/plugin-config-data/derived-data.json` and the
live `~/.signalk/plugin-config-data/derived-data.json` on the boat (the
two files disagree on several unrelated fields — pre-existing drift, not
something this touched — so edited only the one key in each rather than
overwriting one with the other). `sudo systemctl restart signalk`, then
verified: `courseOverGroundMagnetic` now reports from `$source:
derived-data`, and its value matches `courseOverGroundTrue - variation`
normalized into `[0, 2π)` exactly. No `derived-data` errors in the log
around the restart — only pre-existing unrelated noise (barograph policy
warning, a couple of plugins' network calls failing, same as before this
change).

## 2026-08-19 — sops resolved by absolute path (worktree checkout failure)

Symptom: `git worktree add` failed for symphony sessions with
`secretguard BLOCKED: cannot decrypt a file this machine is expected to
read` / `fatal: host/boat-heartbeat.json: smudge filter sops failed`, on a
machine where sops is installed and working. Fixed in PR #18
(`fix/sops-path-resolution`).

**Cause.** git runs filters from whatever spawned git, and that is often not
a login shell. `~/.local/bin` is on PATH only via the shell profile, so
`shutil.which("sops")` missed and the strict-mode smudge filter refused the
checkout. A fatal smudge aborts the whole operation, so a shell-config
difference became a failed worktree creation. Nothing was wrong with the
filter's policy — only with how it located the binary.

**What the investigation got wrong first.** The initial diagnosis named one
call site (`sops_filter.SOPS`) and read as a one-line fix. It wasn't:
`pseudonymize.load_store` and `save_store` also shell out to a bare `"sops"`
and are on the smudge path via `to_worktree_form`, so fixing the guard alone
just moved the failure from `host/boat-heartbeat.json` to
`signalk/security.json`. Four bare call sites total (plus `render.py`). The
end-to-end reproduction is what caught it; a unit test would not have.

**Method worth repeating.** Reproduce the *caller's* environment, not a
convenient local one:

    env -i HOME=$HOME PATH=/usr/local/bin:/usr/bin:/bin git worktree add ...

The first by-hand `git worktree add` succeeded and nearly sent the
investigation down a blind alley — the agent's Bash tool initializes from
the login profile, so it had the full PATH and could not see the bug. The
`env -i` form is the honest test. Verification beyond exit 0: the checked-out
files are plaintext not ciphertext, and `git status` in the new worktree is
clean, proving smudge output round-trips through clean.

**Policy unchanged, deliberately.** Missing sops still blocks in strict mode.
Degrading to a ciphertext checkout would hand SignalK and Grafana `ENC[...]`
blobs where they expect configuration — a silent failure on the boat, traded
for a loud one. The fix only stops us concluding "no sops" on a machine that
has it. The one thing a reviewer should weigh is that `find_sops()` will
execute `~/.local/bin/sops` when PATH omits it; not an escalation (that
directory is already account-owned) but it belongs in review, not folded
silently into a checkout fix.

**Also fixed:** `test_secretguard.py` pinned `"contributor"` in the
comments-only-mode-file test, but a comments-only file leaves the mode to
auto-detection, which is legitimately `strict` wherever an age key and the
filters are present — so it failed on exactly the machines the strict path
exists for. That test is about not aborting a `set -euo pipefail` caller; it
now asserts a valid mode came out, not a specific one. Confirmed pre-existing
by stashing the diff and re-running against a clean tree.

**Local hook note.** The gitleaks pre-commit hook could not run (Docker
daemon down on nucbox). Ran gitleaks natively instead —
`/usr/bin/gitleaks`, repo's `.gitleaks.toml`, staged diff, no leaks — and
skipped only that hook via `SKIP=gitleaks`, leaving the rest enforcing. CI's
gitleaks and trufflehog both passed on the branch push, which is the
authoritative scan.

**Left open:** shell-side lookups in `precommit_secret_guard.sh` and
`check_clone_setup.sh` are still PATH-only, same bug. Boarded in kanban.md
§ Secret tooling.

**Outcome (same session).** PR #18 merged to main 2026-08-19 as `49adbf7`
(squash), branch deleted both sides. Final check ran the `env -i` worktree
add against merged main: exit 0, `host/boat-heartbeat.json` plaintext, all
five test files pass.

Review raised two points, both fair, both taken in `6a86384`:

- *Diagnostics had drifted from the resolver.* `can_encrypt()` listed three
  of the five fallback directories and `lint_repo_hygiene` still said only
  "sops on PATH" — a message could send someone to install sops somewhere
  the resolver does not look. `secretguard.sops_locations()` is now the
  single source for that text, and a test asserts it covers every entry in
  `_SOPS_DIRS` so the two cannot drift again. `_SOPS_DIRS` also moved to
  unexpanded paths expanded at lookup, which keeps `~/.local/bin` legible in
  the message and honours a HOME that changes after import.
- *`find_sops` had no tests*, despite deciding whether secrets reach disk as
  plaintext. Seven cases, each building its own fake sops in a tmpdir with
  both PATH and `_SOPS_DIRS` overridden, so none depend on whether the host
  running the suite has the real binary.

**Worth repeating: the new tests were checked by mutation, not by counting
assertions.** Dropping the `X_OK` check failed 2, letting the fallbacks beat
PATH failed 1, truncating the location list failed 1, returning `"sops"`
instead of `""` failed 3. Writing tests and seeing them green proves nothing
about whether they *can* fail; four one-line mutations do.

**Process note.** Two review comments looked like two findings; the second
was the first re-anchored after the fix (`line: null` = outdated). Checked
the current code before answering, rather than trusting either the comment
or my own memory of having fixed it.

**Local hook caveat, again.** Docker still down, so gitleaks ran natively
for both commits and CI's gitleaks + trufflehog were the authoritative
scans. If Docker stays down on nucbox this will recur every commit — worth
either starting Docker Desktop's WSL integration or teaching
`gitleaks_precommit.sh` to fall back to a native binary when one is on PATH.

## 2026-08-20 — PR #12 follow-up: CI tests, the ruleset, and a wrong claim

Acted on the three decisions PR #12's closing comment left open.

**Landed.** `secret-tooling-tests` job in `secret-scan.yml` running
test_secretguard, test_sops_recipients and test_hostvars_filter on every
branch push — nothing automated ran them before. The PR reviewer's
`--allowedTools` now carries the suites and its prompt says "verified" must
mean executed; across seven rounds of #12 both reviewers were denied any
execution, so every verification in those reports was hand-traced.

**A wrong claim, corrected.** I reported main as unprotected on the strength
of `gh api repos/.../branches/main/protection` returning 404. It is
protected — by ruleset 21060338 (linear history, no force-push, no deletion),
which that legacy endpoint does not report. The substance survived (no
required status checks) but the reasoning was wrong, and Mark had to supply
the ruleset URL. `gh api repos/mark-brannan/symphony/rulesets` is the correct
read; it is now written into `validate.yml`'s header.

**Mark's call: no required status checks**, because requiring them would also
block direct pushes to main and commit-straight-to-main is the working model.
Recorded in validate.yml so it does not return as a review finding.

**A second wrong claim, caught by CI.** I wrote "no age key, no sops binary,
no network" on the new job. `test_pseudonymize.py` needs both — run
32319051952 went red. Backed that one suite out with the reasoning in a
comment rather than papering over it. Root cause is boarded: `resolve()`
calls every runner strict, but "strict" is read elsewhere as "can open
secrets", and these workflows are keyless by design.

**Then found the duplication.** `scripts/run_secret_tooling_tests.sh` already
owned the canonical suite list, under the same name as my new job. My CI job
is a second copy of it. It cannot be collapsed until the strict/keyless fix
lands, so both are now one boarded task with numbered steps — written up
because an extraction of the secret tooling into its own repo is being
scoped, and a keyless standalone CI makes that defect load-bearing.

**Shared checkout, mid-session.** Another session switched
`~/symphony` onto `fix/sops-path-resolution` while I was working. My commits
were already on origin/main; the last edit I moved out — restored the file
untouched, cloned to scratch, committed and pushed from there. Worktrees are
erroring on this box, so a throwaway clone in the scratchpad is the working
substitute. `origin/main` moved four times during the session; fetch-rebase
handled each.

**For whoever scopes the extraction:** the boundary is cleaner than it looks.
In sops_paths, sops_filter, sops_recipients, hostvars_filter and pseudonymize
every symphony-specific string is a comment or doc example — no code knows
about SignalK. `lint_repo_hygiene.py` is the exception and stays: its rules
are boat-specific, and PR #12's still-open `rule_frozen_secrets_untouched`
thread belongs to it, not to the extracted tooling. The real coupling is
configuration — `.sops.yaml`, `.gitattributes`, `.pre-commit-config.yaml`,
the RUNBOOK sections — which a dedicated repo must take as inputs it is
handed rather than files it owns. Do not start on top of the unlanded
`fix/sops-path-resolution` work.

## 2026-08-20 — PR #12 landed; the keyless-CI follow-up executed (PR #19)

PR #12 had been done for hours — 24 review threads worked, 22 resolved, two
declined on the merits, all checks green — and was blocked only by a merge
conflict against a main that had moved 17 commits (PRs #17/#18, the interim
secret-tooling CI job, the actions bump). Merged main into the branch rather
than rebasing 25 shared commits: conflicts were the two slop files (union,
with entries main had since resolved reconciled to their outcomes — the
required-checks question got Mark's "no, deliberately", the suites-in-CI
question became the boarded TASK) and test_pseudonymize.py, where PR #18's
find_sops() superseded the branch's shutil.which and left a dead import.
Verified the merged tree exactly as the PR itself had been (six suites,
CI=1 repo-wide checks, syntax passes) before pushing. The independent
reviewer's final pass on the merge commit found nothing; squash-merged as
4bfc3cb per the linear-history ruleset. CodeRabbit's kanban-hedges thread
resolved itself in the merge — the entry it flagged was superseded by the
answered question, so the reconciliation satisfied both the bot and the
convention it had misapplied.

Then executed the boarded keyless/strict TASK as PR #19 (draft), steps 1-5
as written, on this session's assigned branch. The one bug shape again:
mode() == "strict" read as "keys exist here". The new can_decrypt() is the
second meaning given its own name, in both twins, with the parity suite
grown to pin it from both sides — including a locations-text byte-identity
check that keeps the two sops search lists from drifting, and a toolbox-dir
trick because a test that empties PATH also loses bash. Folded in the
shell-side find_sops (the other open PATH-resolution bullet) and the last
Node 20 stragglers, both already boarded against these same files.

Self-correction for the record: the first commit's message accidentally
embedded its own pathspec as a trailing line (the `--` separator written
into the -m string as well as after it); amended before push.

Open after this session, all needing Mark: merge PR #19 (green CI plus one
run of run_secret_tooling_tests.sh on a keyed machine is the remaining
done-when leg); the stale claude/* branch sweep (now 16-ish with PR #12's
branch merged and this one pending — deletion needs his go-ahead); whether
validate.yml should also run on branch pushes.

## 2026-08-20 (frozen-secrets-fix session)

Fixed the frozen-secrets CI change-range gap PR #12 had left open:
`rule_frozen_secrets_untouched` read `git diff --cached`, empty in CI after
checkout, so `lint_repo_hygiene.py --all` never actually evaluated it there.
Added `HYGIENE_COMMIT_RANGE` (base..head, set by validate.yml from the
push/PR event) as the range the rule diffs when present; local pre-commit
behavior unchanged. Unusable range warns and skips rather than crashing or
passing silent. Verified against a scratch clone that a real edit to
`signalk_captain_password` is caught across a range. Opened as draft PR #22
(assigned branch, and the diff crosses the doc-lines threshold anyway).

Mark reviewed inline and was explicit that this stops here: fine leaving
the captain credentials as-is, doesn't want them touched, but doesn't want
a standing rule policing his own password either -- called the existing
depth (lint rule + CI gate + test class) for something this narrow AI slop.
Recorded as closed in kanban.md, with his no-further-expansion call boarded
under "Blocked -- needs Mark's call" so it isn't re-proposed. Declined to
touch anything else in the same pass (didn't rename FROZEN_SECRET_KEYS to a
config file, didn't add more rules) per that same instruction.

Subscribed to PR #22 for CI/review events rather than polling; one
claude[bot] review comment came in confirming the `base.sha..github.sha`
range reasoning for pull_request events, no action needed. All checks
cleared -- Validate, Secret scan, and the claude[bot] independent review
(no blocking findings, full checklist run including
`run_secret_tooling_tests.sh` and `validate_configs.py`) -- and
CodeRabbit's rate-limited status came back success. Squash-merged as
91dc878; unsubscribed. Fix now runs on every push and PR to main.

## 2026-08-20 (git-divergence reconciliation session)

Handed a detailed brief asserting `origin/main` had been force-updated onto a
rebuilt history, with 67 commits stranded on an old lineage reachable only via
`claude/*` branches. Told to confirm content preservation across the whole tree
first, because a wrong answer there changed the plan. It changed the plan
completely, but in the opposite direction from the one anticipated.

**The divergence did not exist.** The dev clone was shallow — `.git/shallow`
grafted `ae0391d` and `fdf155f` as false roots, and every symptom fell out of
that: a shallow clone whose graft boundary moves reports the fetch as
`(forced update)`, and commits below the boundary look unrelated because their
parents are absent. `git fetch --unshallow` settled it: `git rev-list --count
0286d8f ^origin/main` is 0, `git merge-base 0286d8f origin/main` returns
0286d8f itself, main has 423 commits on the original `6f1ee30` root, and
4bfc3cb / 77a27e6 / 0286d8f / 68e4e04 are all ancestors. The boat, a
non-shallow clone, then fetched `68e4e04..eac1fc5` with no forced-update
marker — independent confirmation from a second machine.

Self-correction worth recording: the first pass at "confirm content
preservation" built a corpus of every line in main's tree and diffed the old
tip's lines against it, which reported 601/710 lines of `maintenance/log.md`
missing and looked like real loss. That was the right check with the wrong
conclusion — the content was neither in the working tree nor deleted, it was
*in history*. `0926fa6`, Mark's own commit, trimmed log.md 812→254 and
priorities.md 609→175 implementing the bloat audit, and its message names
`e176d2b` as the pre-trim ref; verified e176d2b holds both at full length and
is an ancestor of main. `f89786f` folded `watchdog_writeup_draft.md` into one
reference doc. Lesson: "absent from the tip" and "lost" are different claims,
and a corpus diff only answers the first.

Order of operations held: pushed the two boat branches before touching any
ref on the boat. `claude/ecoworthy-signalk-telemetry-vy82ta` @48f3122 (8
commits) and `claude/symphony-pushover-setup-ce12i0` @3f08bd3 existed on no
origin ref — `ls-remote` confirmed absence rather than trusting the boat's
never-fetched tracking refs, which still showed them as tracked. 3f08bd3
existed on no machine but the boat.

The feared blast radius was smaller than the brief assumed, and checking
rather than accepting it is what made the fast-forward routine: `.env` and
`dex/config.yaml` are both **untracked**, so git could never have touched
them, and `telegraf/telegraf.conf`'s worktree content was byte-identical to
main's target (md5 `11f7e981…`), so the file's content never changed at any
point. Backed it up anyway, cleared the single-file modification with an
explicit pathspec, fast-forwarded 92 commits.

Dex turned out to be the interesting one. `systemctl is-active dex` says
`inactive` and the unit is `disabled`, which reads as a dead OIDC front door —
but something was listening on 5556, and it was a **container**
(`ghcr.io/dexidp/dex:latest`, compose-managed via `docker-compose.yml`),
serving discovery 200 with keys rotating on schedule. The move was deliberate
(`d3d690e`); only the docs lagged, and they lagged self-contradictorily —
`RUNBOOK.md:1519` said "Dex is a container" while `RUNBOOK.md:67` listed it
among the systemd units and `software_stack.md` had a section titled "The boat
Pi runs none of this in Docker". Fixed all three at Mark's ask, plus the unit
file on the boat, now headed SUPERSEDED -- do not enable.

That dig turned up a real latent finding: `compose-idp.yml` pins Dex to
v2.45.1 by digest, deliberately, but the running container is `:latest` at
v2.46.0. The pin is defeated, and the next `compose up` would *downgrade* and
bounce the front door — with `storage_type=memory`, dropping every session.
Not caused by this session's fast-forward (that range never touched
`compose-idp.yml`). Boarded, not acted on: recreating Dex is precisely the
"breaking it costs the remote access you'd fix it with" case.

The boat rebooted at 09:18 UTC mid-session, which briefly looked like fallout.
It wasn't — clean `systemd-logind`-requested reboot, and per Mark it was the
InfluxDB→QuestDB migration session that asked for one; nobody was aboard
despite the tty1 console session. Useful accident: it proved the
fast-forwarded checkout survives a reboot with every service returning on its
own.

Verified on both sides of that reboot: caddy, telegraf, signalk,
grafana-server, influxdb active+enabled, dex container serving, telegraf
dual-writing with InfluxDB and QuestDB both fresh and zero write errors. The
"no space left on device" errors in the journal predate the merge by ~5 hours
and were not this session's.

Stashes: `be26ff3` (signalk-ntfy.json) was superseded by main, which contains
the same change with the more specific label "Self-hosted ntfy" vs the
stash's "Self-hosted" — dropped with Mark's say-so. `816c890` (priorities.md) was Mark's own handwriting and
not junk; content is now durably in the kanban, and the stash is deliberately
left in place on the boat because the Evernote connector's token expired
mid-call and a cloud session cannot run OAuth. Its two plumbing deletions he
confirmed as ancient history and valid; both removed from priorities.md.

PR #24 opened as a draft, all five checks green. Subscribed via webhook only —
Mark's explicit constraint, and no scheduled wakeup was created (the
no-persistent-polling hook enforces the same thing). CodeRabbit skipped review
because the PR is a draft, which is expected and not a finding.

## 2026-08-20 — kanban.md restructure to the Open Loops card contract

Rewrote `kanban.md` to the global "Open loops" board contract (`## Yours` /
`## Claude's`, one line per card, checkboxes, every card linked). Full prose
that used to live inline moved to the new `kanban-detail.md`, one heading per
surviving card. Two closed items found while triaging had no record in either
log file, so recording them here before dropping their kanban entries:

- **`wire-wright` published to npm, 2026-08-19.** `gh repo create --push` had
  already created and pushed `mark-brannan/wire-wright` before it errored, so
  no duplicate repo was needed. `npm publish --tag alpha` couldn't run from
  the session's sandboxed shell — no TTY for the browser-approval OTP flow
  npm 12 needs on a passkey-only account — so the exact command was handed to
  Mark to run in his own terminal. Verified after: `gh repo view
  mark-brannan/wire-wright` succeeds (public, default branch main), `npm view
  wire-wright dist-tags` shows `alpha: 0.0.1-alpha.0` (also `latest`, as
  expected for a first publish).
- **Forking `signalk-fixed-position` to debounce its writes: considered and
  rejected, 2026-08-13.** It subscribes to `navigation.position` at a
  hardcoded 1000 ms and calls `savePluginOptions` on every delta, so its
  fallback position gets persisted at GPS rate — ~86,000 writes/day, ~350
  MB/day, roughly 3-9% of the box's ~10 GB/day total. The count looks
  alarming; the volume doesn't justify maintaining a fork forever for a few
  percent of SD life. Stays enabled as-is. If it's ever fixed upstream, an
  issue is the right route, not a fork.

All other resolved kanban items had a matching entry already in
`maintenance/log.md`, this file, or a `reference/*.md` file, and were dropped
without further logging. Full accounting of what moved where, what was
dropped outright, and what's still ambiguous is in this session's wrap-up
message to Mark.
## 2026-08-20 (bt-sensors D-Bus EPIPE session)

Boarded with the handoff note saying SignalK was publishing no
`electrical.batteries.*` at all, that it was not the port or QuestDB, and
that the previous session had deliberately not diagnosed it.

Root-caused it to `bt-sensors-plugin-sk` calling `createBluetooth()` at
module scope in its `index.js`. That opens the org.bluez socket at
`require()` time, during SignalK's plugin-load sweep; dbus-next runs the
auth handshake from that socket's `connect` callback, which the event loop
cannot dispatch until the ~45s synchronous plugin load finishes.
dbus-daemon closes the unauthenticated socket at its 30s `auth_timeout` and
the handshake's first `stream.write('\0')` lands on a dead socket -- the
`write EPIPE at handshake.js:67` that had been in the log for weeks. The
stack was the tell: line 67 col 10 is the *first* byte of the handshake, so
the socket was already dead before auth began.

Evidence, in the order it landed: `dbus-daemon: Connection has not
authenticated soon enough, closing it (auth_timeout=30000ms)` at 02:57:05
with the EPIPE at 02:57:07, one such pair per SignalK start; `busctl` as
`pi` introspecting org.bluez fine, ruling out bus policy; and a direct
repro on the Pi using the plugin's own dbus-next -- a bus opened and then
held behind a 35s synchronous block failed identically, while the same call
on a free loop connected in 66ms. `hci0` was UP RUNNING with zero errors
throughout.

`host/signalk-ble-check` had been firing every boot and logging "still
publishing nothing after 3 restarts this boot; leaving it alone" for hours.
That is what made this look intermittent: a restart cannot fix a fault that
is deterministic on every start. Corrected its comment to say so.

Fixed by raising `auth_timeout` to 120s via `host/dbus-auth-timeout.conf` ->
`/etc/dbus-1/system-local.conf` (included last by the shipped system.conf).
First attempt was rejected: XML forbids a double hyphen inside a comment and
the file used them. dbus rejected the whole file and kept its previous
config, so the failure was loud and nothing broke. Rewrote without them.
After reload and a SignalK restart both banks appeared within 85s and have
stayed live since -- zero EPIPEs, zero healer restarts.

Landed on main rather than the assigned branch, on Mark's explicit
"go to main if you can justify that". Justification recorded at the time:
the config was verified live on the boat before committing, and the repo
files are inert until `install.sh` runs, so there is no half-applied state.
Noted openly that this does brush the CLAUDE.md infra trigger.

Added a `RELOAD` array to `host/install.sh` rather than putting dbus in
`RESTART` -- bouncing the system bus would take every D-Bus client on the
box down with it. Tested the new loop in a stub harness (both the
installed and not-installed branches); did not run the full installer on
the boat, since it also does a systemd daemon-reexec and rewrites the root
crontab. The file's effect was applied by hand with the same path and mode.

Second half of the session was a sync/branch question from Mark. The
"stale remote branch" I had mentioned turned out not to exist: my assigned
branch was never pushed, and `origin/claude/bt-sensors-dbus-epipe-flc6u2`
was a local remote-tracking ref inside this container pointing at the old
main tip. Pruned. My earlier wording implied a live problem and did not
say clearly that I had chosen not to push -- Mark reasonably read it as a
regression.

But the underlying claim in CLAUDE.md was wrong, and that is what caused
the confusion. Every closed PR in this repo, #1 through #23, reports
`merged: false`. Nothing has ever been merged through GitHub's button, so
delete-on-merge has never had an event to fire on. The bullet had cited
#15's and #22's branches vanishing "within moments of merge" as proof the
setting works; neither was merged. Corrected in e2d1307, and explicitly
recorded that the repo setting itself was not readable from this session,
so the note says only that no merge has ever occurred -- not that the
setting is off. Checked PR #26 first, which also edits CLAUDE.md, and
confirmed its hunk is ~280 lines away from this one.

Sync at wrap-up: GitHub main, this session, and the boat's
`/home/pi/symphony` all at e2d1307. The boat was 5 behind, then 1 behind,
clean tree and zero ahead both times, so both were pure fast-forwards.
Mark's desktop was never visible from this cloud container and is the one
unknown.

Not done, deliberately: the plugin-side fix (lazy bus + reconnect on
error), deploying `signalk-plugin-watchdog`, the Cerbo GX empty `paths`
block, and trimming SignalK's startup. All four boarded in kanban.md. Also
did not reboot-test the dbus config -- dbus reads that file at start the
same way it did on reload, but it has not been watched come up cold. Did
not touch the five orphan `claude/*` branches; that needs Mark's call.

**Correction, same session.** The CLAUDE.md rewrite described above was
wrong and has been reverted to the substance of what it replaced.
`merged: false` came from GitHub's *list* pull-requests endpoint, which does
not return the `merged` boolean at all -- only the single-PR GET does -- so
every row reads false regardless. `merged_at` is the field that carries the
truth, and it is populated on 22 of the 26 closed PRs, #15 and #22 among
them. The original bullet was right: delete-on-merge is on and works, now
independently confirmed by PR #24 and PR #26 merging later the same day and
both head branches disappearing immediately.

The failure mode worth remembering is not the API quirk, it is that a
missing field was read as a positive finding. The count was checked twice
and both checks used the same bad source, which felt like verification and
was not. The leftover branches are branches whose PR was closed unmerged or
that never had one, plus branches merged before the setting was enabled --
which was the original bullet's claim all along. Recorded the `merged_at`
trap in CLAUDE.md next to the branch rule so the next session doesn't
repeat it.

## 2026-08-20 — QuestDB migration: closing the four loose ends

Orchestration session. Took the four items the previous migration session
left open and either finished them or handed them off deliberately.

**cgroup / memory limit — done.** `cgroup_enable=memory cgroup_memory=1`
appended to `/boot/firmware/cmdline.txt`, backup at
`cmdline.txt.bak-precgroup`, rebooted with Mark's in-chat authorization.
Verified after: `memory` in `/sys/fs/cgroup/cgroup.controllers`,
`docker stats` 443 MiB / 768 MiB. The running container was updated in place
(`docker update --memory 768m --memory-swap 1536m`) rather than recreated,
to avoid touching the boat's shared checkout while another session is
reconciling its git state. All six services and all three containers came
back unattended; SignalK→QuestDB writes resumed ~4 min after boot, so the
soak continued rather than restarting. Worth remembering: the firmware still
injects `cgroup_disable=memory` ahead of our flag and `cgroup_enable=`
overrides it, so both show in `/proc/cmdline` — that looks like a failed
edit and is not one.

**The BLE commits — already done by someone else.** Checked with
`git ls-remote` before touching anything: both tips
(`claude/ecoworthy-signalk-telemetry-vy82ta` @48f3122,
`claude/symphony-pushover-setup-ce12i0` @3f08bd3) were already on origin at
the boat's exact SHAs. The reconciliation session got there first. Verifying
before acting cost one command and saved a redundant push.

Attempted to message that session as Mark asked. **Confirmed again that no
channel exists between two cloud sessions**: `ListAgents` returns "No
reachable agents" and `SendMessage` to a session id fails outright. The
kanban already recorded this on 2026-08-19; this is a second measurement of
the same limit, so treat it as settled rather than re-testing it a third
time. `list_sessions` on the Claude Code Remote MCP surface *does* show
other sessions and their pending questions, which is how the session was
identified — read-only visibility exists, delivery does not.

**Off-boat backup — handed to Mark, which is the honest resolution.**
Nothing a session can finish: this sandbox's tailnet path is the slow DERP
relay and the sandbox is ephemeral. Generated `SHA256SUMS` next to the
artifacts on the boat so the copy can be *checked* rather than assumed, and
wrote the `scp` + `sha256sum -c` pair into the kanban.

**B4 — unblocked by reframing it.** It had been sitting on "open both
dashboard sets in Grafana side by side," which needs a dedicated session.
A programmatic diff of what every panel actually queries answered it instead,
and answered it decisively: 4 of the boat's 76 imported panels render today.
Mark's instruction was "1 and 2 — I'll maybe look at the diff but probably
not. Don't wait for me," so the analysis ran and the port followed
immediately without waiting on him to read it. Lesson worth keeping: a
question parked as "needs a human in front of a GUI" is worth re-examining
for a measurable proxy before it gets deferred again.

**Scope discipline.** Chased one finding beyond the four items and stopped:
79 of the 171 ported queries return empty, and the cause is that SignalK
publishes no `electrical.batteries.*` at all —
`bt-sensors-plugin-sk` dies on a D-Bus `write EPIPE` at every start, and it
survived the reboot, so it is not the wedged-controller fault in the
RUNBOOK. Boarded it, did not diagnose it. That is the next session's work
and it matters, since power monitoring is the stated point of this stack.

Left as a draft PR (#25), CI green, per the repo's own convention.

## 2026-08-21 (bt-sensors verification, branch/PR cleanup)

Continuation session. Four of the five open items closed.

**bt-sensors-plugin-sk PR #1 — verified and merged.** Deployed the branch
into the boat's checkout at `/home/pi/bt-sensors-plugin-sk` (it's a git
clone symlinked into `.signalk/node_modules`, so deploying is a checkout,
not an npm install). Then removed `/etc/dbus-1/system-local.conf` and
restarted SignalK: battery data was back within 15s. Cold-booted the Pi to
test the real case — the workaround-free path through a full plugin-load
sweep — and both banks (`0146`, `5C90`) published 80s post-boot with zero
`auth_timeout`/`EPIPE` lines in the boot journal. Squash-merged as 2d58949,
put the boat checkout back on `main` at that commit (identical content, so
no further restart), and dropped `host/dbus-auth-timeout.conf`, its INSTALL
entry and the now-empty `dbus` RELOAD entry from `host/install.sh`.
Rewrote the RUNBOOK's "BLE sensors go silent after a reboot" section around
the fix, with an explicit don't-reinstate-the-timeout note.

Ordering note for the record: the "does the dbus config survive a cold
boot" card became moot rather than passing. Removing the workaround made
the reboot a stronger test — it verified the plugin fix cold, which is what
the dbus file existed to substitute for.

Pre-reboot check for other sessions: the Pi's resident
`claude --remote-control` session had last written its transcript 16h
earlier, and nothing else (npm/apt/git) was running. Safe.

**Orphan branch deletion — the previous session's claim was wrong.**
The card said "session push access doesn't cover branch deletion." It does:
`git push origin --delete` removed both
`claude/ecoworthy-signalk-telemetry-vy82ta` and
`claude/symphony-git-divergence-followups-q2yynq` first try. Worth
remembering the next time a card asserts a permission limit without a
recorded error.

**PR #25 rebased.** 7 commits onto a main that had moved 22 ahead; four
conflicts, not three. `intermediate_files/claude_slop/kanban.md` conflicted
three separate times and each time the branch carried the whole
pre-restructure board — took main's side outright rather than merging a
superseded structure. `maintenance/log.md` and the slop log were genuine
union merges. `test_dashboards.py` passes and `build_dashboards.py`
regenerates byte-identical output; CI green. Left open — it repoints the
boat's provisioned Grafana dashboards at QuestDB, which is Mark's call to
land.

## 2026-08-25 — Disk recovery on the boat, and the SignalK outage's real cause

**Started as** a disk-pressure and kanban-triage session. Turned into an
outage post-mortem: SignalK had been down since 2026-08-23 and nobody knew.

### What was actually wrong

`/usr/local/lib/node_modules/signalk-server` had been deleted. Config was
intact — `security.json`, `plugin-config-data`, the whole `~/.signalk` tree —
only the executable was gone, so `signalk.service` failed with
`status=127, /usr/local/bin/signalk-server: not found` and had been failing
for two days.

Reconstructed from `/var/log/apt/term.log` and the tmux scrollback of the
login shell that did it:

- 02:33 — `nodejs` 18.20.4 removed, `nsolid` 22.23.2 installed in its place
- 04:01 — `/usr/local/lib/node_modules` rewritten; `signalk-server` gone
- 04:10 — `rpi-eeprom` upgraded
- 06:07 — `apt upgrade -y rpi-eeprom --fix-missing` started, then suspended
  (state `T`, `do_signal_stop`) and left holding the package lock for 2d12h

The tmux session showed what was being attempted: `docker pull
signalk/signalk-server` (TLS handshake timeout), `apt install grafana`
(343 MB, connection timed out), `npm install` (ETIMEDOUT), `sudo apt`
(broken pipe). All network failures.

### The finding that matters most

**The cellular WAN is the binding constraint on this boat, and it has now
caused two separate outages.** `symphony-pi` reaches the tailnet from
`172.56.x`, a T-Mobile range. The 2026-08-23 attempt died on it; so did this
session's recovery attempt, 27 minutes in, with `EIDLETIMEOUT` from
registry.npmjs.org and single tarballs taking 54 seconds.

This reframes the fresh-card plan from convenience to necessity: the boat
cannot be rebuilt in place over its own link. A card staged and fully
populated at home and carried down is the only reliable path.

### Why the "official" install route is not the safe one

`RUNBOOK.md` directed the reader to `sudo openplotter-signalk-installer` as
the only safe path. Reading
`/usr/lib/python3/dist-packages/openplotterSignalkInstaller/signalkPostInstall.py`
showed it is the opposite:

- line 45 runs `apt autoremove -y nodejs npm` before reinstalling from
  NodeSource — on this Pi that resolved to the conflicting `nsolid` package
- line 91 derives the install prefix from `npm config get prefix` and line 95
  writes it into the `~/.signalk/signalk-server` launcher. Under `sudo` that
  value is **working-directory dependent**: from `/home/pi`, npm reads
  `/home/pi/.npmrc` as *project* config, refuses its `prefix=~/.npm-global`,
  and re-expands `~` against root's HOME to `/root/.npm-global` — a path the
  `User=pi` service cannot read, silently.

Mark had flagged this instinct before I read the source; the source confirmed
it and went further than expected. RUNBOOK section rewritten in `d040724`.

### Work completed

Disk 91% → 64% (2.6 GB → 9.9 GB free), all with Mark's per-item approval:

| action | reclaimed |
|---|---|
| journald vacuum to 200 MB | 1.1 GB |
| `~/.config/chromium` | 1.9 GB |
| `/var/lib/influxdb` + `/var/lib/grafana` (stopped, disabled, purged) | 1.5 GB |
| `~/.claude/remote`, bt-sensors `node_modules` | 1.2 GB |
| apt cache (after clearing the lock) | 745 MB |
| npm cache, docker dangling images | ~1 GB |

`grafana.db` (2.2 MB, the hand-made dashboards) copied to
`~/keep-before-purge/` before the purge. `~/influx-export` (1.4 GB) left
untouched at Mark's instruction — it must not cross the WAN.

Also: cleared the wedged apt and its orphaned `sudo` wrapper (`dpkg --audit`
clean throughout, `apt-get check` passes); removed Telegraf's dead InfluxDB
output, which was failing every flush and dropping metrics on buffer overflow
(`0ac6266`); raised npm's timeouts in `~/.npmrc` for the retry.

### HALOS survey

`halos-pi4` is reachable as `ssh pi@halos-pi4` over the tailnet — worth
recording, since Mark had been using the IP. It runs Traefik + Authelia +
Homarr as core, with containerised SignalK, QuestDB, Grafana, OpenCPN and
AvNav, each its own systemd unit, config declarative under `/etc/halos/`
(`hostnames.conf`, `oidc-clients.d/`, `port-registry`, `routing.d/`,
`traefik-dynamic.d/`) and per-app compose plus prestart hooks under
`/var/lib/container-apps/`. Direct `docker compose` is deliberately blocked by
a sentinel env var.

It is architecturally where this repo was already heading — QuestDB as history
store, containers, reverse proxy plus SSO — and adopting it would retire
`priorities.md`'s top SignalK/IoT item (move off hand-rolled bash wrappers onto
declarative config management) outright. What it discards is plumbing; what it
preserves is the judgments. Caveat: that box is a 2 GB Pi 4 running at ~358 MB
available, so HALOS implies committing to the HALPI2.

### Left open

SignalK is still down. The retry is carded with everything staged for it.

## 2026-08-26 — halos-pi4 SSH re-verified
`ssh pi@halos-pi4` re-confirmed working from this host (key-auth, no
prompt, tailnet). No open card existed for this — RUNBOOK.md § "The HALOS
trial Pi (home, not the boat)" already documents it (committed 4dee11c,
same session as the original verification). Nothing to update there;
re-verification just confirms it still holds.

## 2026-08-26 — dropped symphony's redundant no-persistent-polling.sh
Mark asked to "assess whether symphony needs its own copy [of a hook] or
the dotfiles one covers it" — no literal card for this; matched it to
dotfiles' CLAUDE.md note that `no-persistent-polling.sh` was hoisted to
`~/.claude/hooks/` on 2026-08-19 "so it covers every repo." It's wired at
user scope in `~/.claude/settings.json` on the same matcher
(`mcp__.*__(send_later|create_trigger)`) symphony's own copy used, so both
were firing on every call — same deny, doubled — and had already drifted
(dotfiles' copy gained a fail-closed jq-missing branch and fixed the path
in its deny messages; symphony's never got either).

Deleted symphony's `.claude/hooks/no-persistent-polling.sh` and its
settings.json wiring; left CLAUDE.md's mention of the guard in place but
repointed it at the user-level hook, with one added sentence: without
dotfiles installed, nothing here enforces the rule mechanically. Mark
asked explicitly to keep that edit light — a contributor without his
dotfiles shouldn't trip over an unexplained rewrite.

Pushed straight to main (bf2344d) — under the branch-vs-main line, not a
branch trigger.

Self-correction, not left for Mark to catch: the first attempt at the
settings.json edit and the `rm` of the hook file landed in the shared
checkout (`/home/solace/symphony`) instead of this session's worktree —
copy-pasted the wrong path. Caught before committing anything;
`git checkout HEAD -- .claude/hooks/no-persistent-polling.sh` in the
shared checkout restored the one file touched there, untouched the other
sessions' unrelated uncommitted work sitting in that checkout, and both
edits were redone correctly in the worktree. No trace of the slip reached
the shared checkout or the commit.

## 2026-08-26 — SignalK health check, outside + inside

**Recovered, both ways.** `signalk.symphony.dark-star-llc.com` is 200 via
Caddy from outside; `auth.symphony...` (Dex) is 200. `grafana.symphony...`
is 502 — expected, Grafana's been off since the 2026-08-25 disk-pressure
purge (already on the board).

Inside via ssh: `signalk` systemd unit active, started 00:09:51 today,
`NRestarts=0`, no errors in its unit history, admin UI serving fine. This
retires the "SignalK reinstall — still down" card: the 2026-08-25 outage
is over, the install landed. Removed that card, replaced with a new
finding below.

Host state: `influxdb`/`grafana-server` systemd units are `inactive` +
`disabled` (matches the known 2026-08-25 purge, not new). Dex, QuestDB
and ntfy run as docker containers, all `Up 4 days` — expected per
`reference/software_stack.md`. `signalk-to-influxdb2`'s `HistoryAPI`
unhandled rejection is present in the log too — already covered by the
open "uninstall signalk-to-influxdb2" card, this is just live confirmation
it's still misbehaving.

New: `signalk-postgsail` is throwing `TypeError: Provided value cannot be
bound to SQLite parameter 5` in `updateDatabase` on every delta right now
— its own local SQLite queue, not the InfluxDB/QuestDB path. Carded.

Memory: 59 MB free, swap 199/199 MB full, `pswpout` climbing — real
pressure, right now, even with InfluxDB and Grafana already off. Didn't
act on it: a live session (tmux + several ssh pts, one active
`claude --remote-control symphony-pi`) is already on the box, so stopping
anything risked stepping on concurrent work. Flagging rather than acting.

## 2026-08-26 — PR #30 landed and closed
- The draft PR #30 (mislabeled "Docs corrections", actually carrying the
  DSC/AIS distress-chain material) squash-landed on main as 9f90ebf, then
  closed with a pointer comment; head branch deleted. Main's branch rules
  reject merge commits, hence the squash.
- Conflict resolution: main had rewritten `maintenance/priorities.md` and
  `reference/node_red_signalk_use_cases.md` into compact form since the
  branch diverged; kept main's structure and grafted short pointers into
  `reference/distress_monitoring.md` (new file, landed intact) — the
  distress-chain boat-install item, the delivery-gap note on the alarm
  bullet, MOB pointers. `maintenance/log.md`'s 2026-08-19 section gained
  the four distress bullets; the resurrected "Date unknown" header from
  the stale branch was dropped to match main.
- Redaction pass per Mark's call: the plugin author stays unnamed (log
  entry now "corresponded with the author of…", no verified-his-claims
  framing) and the census comment no longer attributes the misreading to
  him. MMSI 368391180 was checked and is already public on main
  (specs.md, README AIS links) — not redacted.
- Board card for PR #30 retired.

## 2026-08-26 — postgsail fix + influxdb2 uninstall, both blocked

Found the root cause of the postgsail SQLite error from the earlier
health check: `maxSpeedOverGround`/`courseOverGroundTrue` never
initialized, undefined bind on every delta while the boat has no SOG
source (dockside, AIS unpowered). Filed
[upstream issue #68](https://github.com/xbgmsharp/signalk-postgsail/issues/68)
with the one-line fix.

Tried to apply it directly and to uninstall `signalk-to-influxdb2` (both
carded as "easy" pickups). Neither landed: the harness's permission
classifier blocked writing to the boat over ssh (`scp`, `sed -i` — reads
were fine), and independently `npm uninstall --dry-run` over ssh hung
>200s on the boat's cellular WAN before I killed it. Didn't force either
— a hung npm operation on this boat's `package-lock=false` tree is the
exact shape of the 2026-08-25 outage. Detail and exact resume commands in
kanban-detail.md under both cards.

## 2026-08-26 — SignalK restored
Ran the retry per RUNBOOK.md § Upgrading SignalK on the boat Pi with what
the prior session staged (warm 167 MB `~/.npm/_cacache`, raised
`~/.npmrc` timeouts). `npm install -g signalk-server --no-audit --no-fund
--prefer-offline` as `pi`, no `sudo`: 756 packages in 10m, no network
error this time.

One thing the runbook didn't anticipate: npm's install-scripts allowlist
gate (new in this npm 11.19.0) skipped `@canboat/canboatjs`'s native
`canSocket.node` build along with 5 other packages' scripts. That's the
CAN-bus addon for `n2k-can0`/`canbus-canboatjs` — Symphony's actual NMEA
2000 source, and exactly the thing "boat collecting nothing" meant.
Re-ran with `npm install -g --allow-scripts=@canboat/canboatjs,es5-ext,
storage-engine,@serialport/bindings-cpp,@scarf/scarf,core-js` (2m,
incremental) and confirmed the `.node` build landed.

Launcher (`~/.signalk/signalk-server`) was still pointing at
`/usr/local/bin/signalk-server` — stale from the pre-outage 2.14.4
install. Rewrote it per the runbook, started `signalk.socket` before
`signalk.service`. Verified: `Successfully connected to can0` in the
journal, no `Cannot find module` anywhere in the signalk-server tree, and
live n2k deltas over the HTTP API (`signalk-n2k-displays`, fresh
timestamps).

Reconciled two open cards against this:
- **`/usr/local/bin` symlinks card** — closed. Confirmed cause: npm's
  prefix has been `~/.npm-global` since bt-sensors was linked globally;
  nothing manages `/usr/local/bin` anymore, and nothing needs to now that
  the launcher points straight at `~/.npm-global`. The old
  `/usr/lib/node_modules/signalk-server` (2.14.4) tree is still on disk,
  inert.
- **RUNBOOK's `openplotter-signalk-installer` warning** — already landed
  by an earlier session; card removed, nothing to do.

Then found `bt-sensors-plugin-sk` failing to load
(`Cannot find module '@naugehyde/node-ble'`) — first read as unrelated
history (last commit 2026-08-21), but its `node_modules` was gone
entirely and its `.git` dir had been touched the same day as the outage.
This is exactly what the existing "must survive the reinstall" card
anticipated. Both symlinks and the plugin's untracked webpack `public/`
output were intact — only `node_modules` was gone. Tried `npm install`
there (8 direct deps, no lockfile): 29m28s, died on `ECONNRESET`. Matches
the "cellular WAN is the binding constraint" card exactly. Didn't retry a
second time per standing instruction — updated the card with these
findings instead of re-running into the same wall. Core SignalK is
unaffected; this only blocks BLE sensor data.

`maintenance/log.md` got one factual line for the outage+restore.
`kanban.md`/`kanban-detail.md` updated: removed the SignalK-retry card,
the now-done RUNBOOK-correction card, and the resolved symlinks card;
updated the bt-sensors card in place.

Not done, not carded further — the RUNBOOK card asking to document the
boat's non-standard Node/npm state (nsolid at `/usr/bin/node`, standalone
node parked at `/usr/local/bin/node.disabled-20260825`, npm prefix at
`~/.npm-global`) is still open and accurate; left it as-is rather than
expand this session further.

## 2026-08-26 — Track B: QuestDB "connectivity bug" didn't exist; postgsail fixed; influxdb2 uninstall hit a new npm quirk; found a live concurrent session mid-session

Read `reference/containerization_strategy.md` in full, then investigated
the reported B3 bug ("signalk-questdb enabled, QuestDB holds zero tables,
questdbHost 127.0.0.1 misconfigured"). That finding, in kanban-detail.md
under "Evaluate parked/unused SignalK plugins on the dev container", was
always about the **dev container's** older `signalk-questdb` plugin
(dirkwa's original, container-to-container networking), not the boat's
`signalk-questdb-history-provider` (the Hat Labs B3 fork). On the boat,
SignalK runs natively, so `questdbHost: 127.0.0.1` correctly reaches
QuestDB's Docker-published port. Verified directly: 23 tables present,
`signalk`/`signalk_position` row counts climbing minute to minute
(confirmed with two counts a minute apart), sampled rows non-null and
sane (dock GPS coords, live battery/environment/nav paths). Re-ran
`scripts/questdb_table_hygiene.sh` against the boat — 0 changes needed,
already fully applied. No fix was needed or made; this was a stale/
misattributed finding, now corrected in kanban-detail.md.

Cleared the two boat-write-permission-blocked cards, since this session
had that permission — checked `who`/`ps aux` first, saw no active
npm/apt/docker process, and confirmed WAN health
(curl to registry.npmjs.org: 1.4s; ping to 8.8.8.8: 30-45ms, 0% loss)
before either:

- **postgsail SQLite-bind fix**: applied the two-line default (`= 0` on
  `maxSpeedOverGround`/`courseOverGroundTrue`), restarted `signalk`,
  confirmed the bind error is gone from the log.
- **signalk-to-influxdb2 uninstall**: dry-run succeeded cleanly (56s,
  14-package removal plan). The real uninstall then failed, exit 254, on
  an unrelated tree quirk — `signalk-plugin-watchdog`'s dependency entry
  is a *self-referencing* `file:` path
  (`file:./node_modules/signalk-plugin-watchdog`), and npm's reify step
  errored trying to read a package.json from a derived top-level path
  that doesn't exist, aborting the whole transaction before touching
  signalk-to-influxdb2. Confirmed no functional damage: signalk-to-
  influxdb2 is unchanged, and the one thing that *did* get deleted mid-run
  (`~/.signalk/signalk-plugin-watchdog/`, a stray top-level directory) was
  provably unreferenced by anything — not the working
  `node_modules/signalk-plugin-watchdog/` copy, not this repo's tracked
  `plugins/signalk-plugin-watchdog/` source, not any deploy script or
  cron job. Watchdog has logged no errors since. Filed both the uninstall
  retry and the underlying `file:` fix as separate cards in kanban.md —
  the fix (repointing at `file:../symphony/plugins/signalk-plugin-watchdog`
  on the boat) is untested and belongs in its own session.

**Stopped there rather than starting B4/B6.** Right after the postgsail
restart, boat logs showed the box's standing `claude --continue
--remote-control symphony-pi` session actively installing
`signalk-noaa-space-weather@0.29.1` via the SignalK app store — direct
evidence it was doing real work at that moment, not sitting idle the way
the earlier `who`/`ps aux` check (which only catches an in-progress
process, not a session about to start one) suggested. Nothing looked
broken on either side, but B4 (dashboards) and B6 (containerize SignalK,
drop the docker.sock mount) are exactly the higher-blast-radius changes
that shouldn't run next to someone else's live session on the same box.
Left both for a session that confirms the box is clear first.

## 2026-08-26 — symphony-pi npm install failure, and a shared-checkout near-miss

Boat symptom: every SignalK App Store install failed with ENOENT on
`/home/pi/.signalk/signalk-plugin-watchdog/package.json` — a package nobody
was installing. Cause: `~/.signalk/package.json` carried
`"signalk-plugin-watchdog": "file:./node_modules/signalk-plugin-watchdog"`,
a self-reference. npm packs the file: source, then clears the destination
before unpacking; source and destination were the same directory, so reify
aborted and nothing installed. Repointed at the git-tracked source,
`file:../symphony/plugins/signalk-plugin-watchdog`, and ran a real install:
clean, `signalk-noaa-space-weather` now 0.21.1 on disk. Server still runs
0.21.0 in memory; restart deliberately left to Mark.

`npm install --dry-run` exits 0 against the broken entry — it resolves
without reifying, and the bug is entirely in reify. It is not a valid check.
Documented in RUNBOOK.md, along with an amendment to the 2026-08-15
"use a `file:` entry" advice, which is what produced this: the target has to
be outside `node_modules`.

The larger finding is not about npm. The shared checkout `/home/solace/symphony`
had ten files of uncommitted work that nobody could account for. Unpicking it:

- Commit `351fdb0` (08:34) was orphaned a minute later by `dc36c63` — same
  commit message, different content, two sessions committing into one
  checkout. Its log content had already reached main by another path, so
  nothing was lost there, but only by luck.
- The working tree was never brought forward onto `dc36c63`, so most of what
  looked like edits was stale content. Committing it as-is would have
  reverted eight commits — 854 deletions, including deleting
  `reference/distress_monitoring.md` outright and restoring the 08-21 advice
  to "use the openplotter installer only", which `d040724` reversed on 08-25
  after that tool took the boat offline for two days.
- Genuinely uncommitted work was in there too, and is now on main: two
  hand-written RUNBOOK notes, a round of dev-container plugin upgrades, and
  two bt-sensors-plugin-sk board cards.

Also: this session and `questdb-connectivity-track-b` independently
diagnosed the same npm bug and were both about to write to `~/.signalk`.
Two earlier messages from that session never arrived here; Mark relayed the
diagnosis by hand. Collision was avoided because that session checked, not
because anything prevented it.

## 2026-08-28 — PR #189 evidence gathering, live experiments on Symphony

Verified SSH access, confirmed the deployed plugin matches PR #189's diff,
`auth_timeout` workaround already removed, 10h+ SignalK uptime under real
BLE error load, live battery data flowing throughout. Detail and the
attempt log (bluetooth.service restart, dbus.service restart + NetworkManager
recovery, gdb fd-close) are in `kanban-detail.md` §"Evidence-gathering for
upstream PR #189" — not duplicated here.

Mark explicitly approved forcing a `dbus.service` restart after being told
the specific risk (NetworkManager is D-Bus-activated and could die without
auto-restarting) and the confidence level (moderate, reasoned from config,
not measured precedent). It happened exactly as predicted; recovered in
under a minute, fully remote, no lasting damage. Also got explicit
go-ahead to try a gdb-based fd close after the harness's auto-mode
classifier blocked the first attempt — that one worked mechanically (fd
closed clean, no crash) but didn't hit the target code path either.

Net: two service-level restarts and one syscall-level fd close, three
attempts, zero damage, zero direct proof the PR's reconnect branch has
ever fired. That's a real gap, not a formality — worth closing before
leaning on this as the case for merge.

**Handoff for next session** (recommend: Sonnet, low-medium effort — this
is mechanical, not exploratory; the diagnosis and dead ends are already
written down):

> On Symphony (`ssh pi@symphony-pi`), read
> `intermediate_files/claude_slop/kanban-detail.md` § "Evidence-gathering
> for upstream PR #189" for what's been tried. Find the actual PID
> currently running `dbus-daemon` (`systemctl show dbus -p MainPID
> --value` or `pgrep dbus-daemon`) and send it a hard `SIGKILL` (not
> `systemctl restart dbus.service`, which is a graceful SIGTERM the daemon
> already handles fine and produces no reconnect signal) — systemd's
> `dbus.socket` should respawn a fresh `dbus-daemon` on the next
> connection attempt. Watch `journalctl -u signalk -f` for the plugin's
> own "Bluetooth D-Bus connection lost, reconnecting in Ns..." line and
> confirm battery data (`curl localhost:3000/signalk/v1/api/vessels/self/electrical/batteries/5C90/voltage`)
> resumes after. Also re-check NetworkManager (`systemctl is-active
> NetworkManager`) afterward and restart it if it died again, same as last
> time. If this still doesn't trigger the reconnect branch, stop escalating
> further live-fault-injection attempts and instead draft the PR #189
> comment from the evidence already gathered (10h+ crash-free under real
> error load, live data flowing) — that's solid regression evidence even
> without a direct reconnect-branch trace. Post it only with Mark's
> go-ahead, per standing orders on outward-facing actions.

## 2026-09-01 — PR #189: found and fixed why sensors never republished after a D-Bus reconnect

Root cause was the process-wide GATT connect queue, not device objects
bound to the dead bus: a connect in flight when dbus died never settles
(dbus-next never rejects pending calls), so the queue stayed busy forever
and every re-created sensor's connect waited behind it. Reproduced
deterministically by killing dbus during a connect; fixed with a fresh
queue on reconnect, a real timeout rejection in `deviceConnect()`, and
concurrent sensor teardown in `stop()`. Pass criterion met on the
committed code: kill 20:35:21Z, fresh 5C90 data 20:36:09Z, no SignalK
restart. Pushed to fork `main` (updates PR #189), maintainer comment
posted, scaffolding removed. Detail in kanban-detail.md § "PR #189
verification, 2026-09-01".

One slip: the comment was posted before the push had succeeded (the
boat has no GitHub credentials; the ssh exit code hid the failure).
Pushed from the dev box a minute later, so the PR and the comment agree.

Correction, same day: Mark rejected the PR comment and the code comments as
wordy and obviously AI. Replaced the comment with bare repro steps
(auth_timeout 20 ms in `/etc/dbus-1/system-local.conf`), trimmed every
comment to one line (later squashed with everything else into one signed commit `f1c9cb8` on fork main, PR #189 head), and re-ran the
repro in order on the boat: pre-PR code logs one uncaught EPIPE and 404s;
PR code retries with backoff and reconnects by itself once the file is
removed. Scaffolding removed, data flowing 21:08Z.

## 2026-09-01 — HALOS boat-swap plan (Fable planning session)

Planned the accelerated trial: the HALOS card built at home goes into the
boat Pi; the boat card is the rollback. Measured both boxes live and read
the halos-org sources through a subagent. Landed: `reference/system_map.md`
(both cards, containers, SSH strings, diff table, three decisions),
`RUNBOOK.md` → "Swapping the HALOS card onto the boat" (verification per
step, rollback), `scripts/dns_cutover.sh` (read path tested against the live
zone; `set` untested), `intermediate_files/claude_slop/halos-swap-plan.md`
(ordered build plan B1–B6, parallel items P1–P7 with prompts), and a plan
shift note at the top of `containerization_strategy.md`.

Findings that changed the plan: the HALOS SignalK container is privileged,
host-network, mounts `/dev` and `/run` (BlueZ D-Bus reachable) but its
`nsswitch` has no mDNS (Victron's `venus.local` must become the Cerbo's IP,
192.168.8.107); its `package.json` lists one plugin against ~80 loose
installs (prune trap); the halos card lacks every PiCAN-M overlay, `can0`
bring-up, the memory cgroup (container limits unenforced) and has regdom
GB; the spare Pi is 2 GB and swapping 1.5 GB. InfluxDB is already gone from
the boat (purged 08-25, export only on the boat card), so QuestDB-only is
the decision, not a migration. healthchecks.io is pinged by
`boat-heartbeat.timer`, not a plugin. Pushover = the heartbeat's escalation.

### PR #33 review triage (same session, handed off unstarted)

Mark asked for a wrap-up before the CodeRabbit round was addressed. Triage,
so the next session fixes rather than re-reads. Fix = change the file;
reply-only = explain and resolve.

- 3909035421 plan B2a/B2b: PSK on `nmcli` argv. **Fix**: write an NM keyfile
  (`/etc/NetworkManager/system-connections/<name>.nmconnection`, 0600) built
  locally from sops, scp'd, `nmcli con reload`; no PSK in any argv.
- 3909035427 plan B3a: rsync of live state. **Reply-only**: SignalK rewrites
  config only on admin saves; run rsync twice, second pass must transfer
  nothing. Don't stop the boat's SignalK for a copy.
- 3909035432 plan B3a: `$D` undefined. **Fix**: define it in the block.
- 3909035436 plan B3c: `package.json.halos` backup happens after rsync
  overwrote it. **Fix**: move the backup before B3a, to `/home/pi/`.
- 3909035437 plan B3c: Cerbo IP without a reservation. **Fix**: make the
  router DHCP reservation for the Cerbo (192.168.8.107) a precondition,
  verify with `ssh root@192.168.8.1 'uci show dhcp | grep -i cerbo'` or the
  MAC.
- 3909035441 plan B3c + RUNBOOK: parity by counts. **Fix**: add a diff of
  `<config> <enabled>` pairs from plugin-config-data on both cards; list the
  three expected differences (signalk-container, signalk-to-influxdb2,
  signalk-to-influxdb-v2-buffer disabled on HALOS).
- 3909035444 plan B5a: rule misses exact `/sso` and `/ca`. **Fix**: add
  `!Path(...)` for both; make the test five explicit curls (`/`, `/sso`,
  `/sso/`, `/ca`, `/ca/`).
- 3909035455 containerization_strategy: "B3 done" while
  `signalk-to-influxdb2` is still enabled on the boat. **Fix**: say QuestDB
  is the only *live* store and name the two leftover cleanups.
- 3909035460 system_map: `NODE_TLS_REJECT_UNAUTHORIZED=0`. **Fix (one
  sentence)**: it's HALOS's package-owned compose, not ours; name the
  affected traffic (every plugin's outbound HTTPS and the MQTT-TLS link to
  the Cerbo) and that the trial accepts it.
- 3909035465 system_map + plan: directory copy "merges" history. **Fix**:
  a stopped copy *replaces*; merging needs an ILP re-export
  (`Table2Ilp` or REST export). Reword both.
- 3909035472 RUNBOOK: `;`-chained checks. **Reply-only**: read-by-eye
  checks with stated expected output are the RUNBOOK convention.
- 3909035477 RUNBOOK: DNS before readiness. **Fix**: move the DNS cutover
  after the local checks (step 6 before step 5); same order in rollback.
- 3909035482 RUNBOOK: `set` untested. **Fix**: add to "Before leaving
  home": `set symphony-halos` then `set symphony-pi` from home, both
  verified with dig; costs about ten minutes of off-boat access.
- Minor, quick: `dns_cutover.sh` exit unless exactly one apex A record;
  ntfy curl `-f`; "Keep the runbook procedural" at RUNBOOK 708 (the
  pocket/only-copy sentence — move to system_map); system_map 48 and 89
  wording nits.
## 2026-09-01 — B1a–c on halos (P1 of the swap plan), and a credential leak

Executed `intermediate_files/claude_slop/halos-swap-plan.md` items B1a–c on
`pi@192.168.0.193`: PiCAN-M overlays appended to `/boot/firmware/config.txt`,
`cfg80211.ieee80211_regdom` GB→US plus `cgroup_enable=memory
cgroup_memory=1` in `cmdline.txt`, `/etc/systemd/network/80-can.network`
added and `systemd-networkd` enabled. The plan file itself only exists on
the unmerged `claude/halos-boat-swap-trial-9e5d36` branch, not on main or
this session's branch — read via `git show` rather than checked out.

**Incident, self-caused.** First attempt used
`run(){ printf "%s\n" "$PW" | sudo -S "$@"; }` called as
`run tee -a file <<EOF ... EOF`. The pipe into `sudo -S` overrides the
function's stdin, so the heredoc content never reached `tee` — instead the
sops-decrypted `symphony_halos_pi_password` itself got written into
`/boot/firmware/config.txt` and `/etc/systemd/network/80-can.network`, and
printed once into this transcript. Caught it in the very next command,
confirmed the exact scope (`cat -A` on both files — one leaked line each,
nothing else touched), and rewrote both files correctly using a
password-free sudo call against a temp file staged as `pi` (no sudo
needed for `/tmp`). Verified clean afterward. Mark's call: not rotating
the password, not raising it again. Memory saved
(`sudo-password-heredoc-pipe-bug`) so no future session repeats the
pattern of mixing a piped sudo password with heredoc content in the same
invocation.

Rebooted, ran the B1 verification block:
- `/dev/serial0` present; `/dev/i2c-1` **absent** — `i2c_bcm2835` loaded,
  `dtparam=i2c_arm=on` is in config.txt, but no `i2c-dev` device node.
  Outside B1a–c scope (plan didn't call for it), flagged not fixed.
- `cgroup.controllers` includes `memory` ✓.
- regdom reports `US` ✓.
- `dmesg | grep mcp251`: overlay probed, `Probe failed, err=110` —
  expected, no PiCAN-M HAT attached at home.
- `can0` not present — plan says that verifies at the boat only.

P2–P7 of the swap plan are unstarted.

## 2026-09-01/02 — PR #25 live walkthrough, session 1 of N (Navstation only)

Worktree: `grafana-dashboards-pr25-89c9f8`, branch
`claude/influxdb-questdb-migration-t3lkra` (PR #25 itself). Demo stack
(`questdb-demo`, `grafana-demo` on `symphony-demo-net`, localhost:3100
admin/devadmin) reused from an earlier session rather than rebuilt — still
up, left running for the next session. `verify_dashboards_live.py`
confirmed 196/196 before and after tonight's change.

**Navstation redesigned and shipped.** Was a flat grid of 18 identical
`w=4 h=5` stat tiles; compared side-by-side against
`meri-imperiumi/lille-oe`'s Navstation (same six-dashboard structure,
public repo) and found panel *count* was nearly identical (21 vs 22) — the
"busy" feeling was panel-type/size uniformity, not density. Regrouped into
Navigation/Power/Weather-and-tide rows with gauges on primary values (SOG,
heading, house SOC, wind) and varied stat sizing for the rest. Committed
`7ff9d48`, pushed to the PR branch. Mark reviewed live and approved.

**Verified against real boat data, once, carefully.** Boat's real QuestDB
(on symphony-pi) is 11 days up with SignalK actively writing — confirmed
fresh (`max(ts)` ~now) and confirmed real row volume
(`environment.outside.pressure`: 4,271 rows/6h, ~1 sample/5s) before
touching anything, so the bandwidth estimate for the boat's constrained
uplink is measured, not guessed. No Grafana currently runs on the boat at
all (compose `grafana` crash-looped, `sk-signalk-grafana` lost its port
race, `grafana-server` systemd unit is `failed`) — so there was nothing to
deploy to or risk breaking; the move was a read-only SSH tunnel
(`127.0.0.1:18812` on this box → boat's `127.0.0.1:8812`, never exposed
past loopback) into the *demo* Grafana's existing QuestDB datasource,
one-shot, then reverted and torn down. Confirmed real values came back:
Heel 0.6°, Barometer 1010.3 hPa, Outside 61.6°F, Fridge 69.6°F, Trip log
0.0 nm. Nav/wind/power panels reading "No data" against real data matched
what the row-count query predicted (those paths have zero rows right
now — boat's at dock, sensors quiet) — not a bug. `Vessel state` /
`Tendency` "No data" is the pre-existing text-mode-stat bug, unrelated to
tonight, not fixed.

Two Playwright screenshot attempts against the live tunnel came back
empty — a genuine bug in my own capture script (the dashboard's saved 10s
refresh never actually turned off, so screenshots raced the refresh
cycle), not a data problem. Didn't retry a third time against the boat to
chase a client-side timing bug — burning more of the boat's measured
bandwidth to fix a screenshot script isn't a good trade. Mark asked to cut
the boat connection; confirmed torn down (no process on 18812, datasource
reverted). Noted but did not touch: two unrelated pre-existing
`ssh pi@symphony-pi` sessions on this box (since Aug 22 and today
13:43) — not mine to kill.

**PR #25 review scope, for whenever Mark reads the diff himself:** 3051+/
1852- across 23 files, but only `scripts/build_dashboards.py` (348 lines,
the actual panel/unit/threshold decisions),
`grafana/provisioning/datasources/questdb.yaml` + `.env.j2` (what the boat
will point at once deployed), and `RUNBOOK.md` are worth a human read. The
six dashboard JSON files (3600+ of the diff) are pure `build_dashboards.py`
output verified by `test_dashboards.py`; `intermediate_files/claude_slop/*`
and the test/verify scripts are mechanical/session-state. Not yet decided:
whether/when to actually deploy PR #25 (the InfluxDB→QuestDB cutover) to
the boat — nothing tonight implied or executed that; it's still open.

**Not yet walked:** Electricity, System health, Navigation, Weather, Life
support — five dashboards, same process (show, take comments, fix small
ones in `build_dashboards.py`, regenerate, commit; anything bigger gets a
card). Demo stack is up and ready; PR #25 branch is the working branch, no
new branch needed to keep committing to it.

## 2026-09-02 — HALOS swap prep executed overnight (Fable, PR #33)

Mark asked for PR #33 fixed, tested and executed unattended. Did B2, B4a–c,
B5a and a healthcheck fix on the bench card, verified the DNS write path both
ways, took the real boat baseline and rewrote the two check scripts from it;
the runbook section now carries measured output. Facts and times in
`halos-swap-execution-2026-09-02.md`; what is left in
`handoff-pr33-swap-prep.md`. Two sessions shared the 2 GB bench box for a
while and it hard-reset once under swap thrash after AvNav/OpenCPN were
stopped; one session on that box at a time from now on. The boat's heartbeat
had been pinging `/fail` for a week on two dead units; cleared. Pre-existing
boat issues found and left for Mark: Cerbo MQTT dead, position from a fixed
plugin, QuestDB pegged with load ~12.

## 2026-09-02 — PR #33 landed; bench card preflight green (session pr33-comments-merge-33902c)

Answered and resolved all 13 review threads on PR #33 (shellcheck, the ble
ok-line, the 60 s vs 150 s healthcheck numbers, the two verbatim-block
threads), then squash-merged it as c8bbbb5. #35 landed into the branch
mid-session; rebased onto it. First end-to-end preflight against the bench
card found three card-side problems, none of them script bugs:
`systemd-networkd-wait-online` enabled that morning by a session and failing
every boot, the removed InfluxDB app's unit still starting and failing, and
three plugin diffs that are image facts (allow-listed). Fixed on the card,
recorded in `host/halos/README.md`. `pi` cannot run docker on HALOS, so the
#35 runbook check now says `sudo`, and the preflight reads gid 988 from
`/proc`. Soak with QuestDB and Grafana held on zram (load 1.1, paging
~250 MB/min); rebooted once, every preflight line ok at 10:26Z. Dispatch
prompt for swap day in `dispatch-halos-swap-day.md`; the handoff file is
deleted, its results are in `halos-swap-execution-2026-09-02.md`. Left for
Mark: pypilot, the Cerbo, the swap day itself (cards).

## 2026-09-02 — PR #34 already merged; boat calmed for the baseline (session pr-34-merge-baseline-091553)

PR #34 needed nothing: merged 10:22:17Z as 364ad2a, and `origin/main` carries
`host/signalk-unit.sh` with `install.sh` sourcing it at line 54 and installing
it to `/usr/local/lib/symphony/`. Card retired unworked.

Calming the boat found a different problem than the card described. The "13
logged-in users" is a utmp artifact — `who -a` lists 16 entries, most of them
dead pts records with exit codes, and only 5 live sessions, two of which are
tmux panes from 21 and 23 August. Nothing to kill there.

The real load was **six orphaned lightdm greeter sessions**: `lightdm
--session-child` processes reparented to PID 1 by lightdm restarts on 26
August and 1 September, each still running a `labwc -C
/etc/xdg/labwc-greeter/` compositor spinning at 20-55 % of a core. Killed all
six (458186, 461611, 505317, 507218, 509660, 2091034); the one live greeter
under the running `/usr/sbin/lightdm` sits at 0.0 %. Available memory went
409 → 675 MB immediately.

There was no QuestDB *query* to find. QuestDB had **wedged at
2026-09-02T07:01:25Z** and spun for eleven hours: no log line after that
timestamp, `/exec` accepting the socket in 0.5 ms then never answering inside
30 s, docker's NET and BLOCK I/O counters frozen across successive samples,
all while the container burned 180-250 % CPU. `jcmd` isn't in the image so no
thread dump was possible. `docker restart -t 30 questdb` fixed it — it came
back logging, and `/exec` now answers `select 1` in 51 ms. Cause unknown; the
last healthy log lines show `ApplyWal2TableJob` committing 50 rows in 5074 ms
(9 rows/s) against ~284k-row partitions, so it was already struggling before
it stopped.

Net: load average 13.2 → 2.67, QuestDB 250 % → 21 %. `scripts/halos_swap_check.sh
symphony-pi` now passes every line including `questdb` (newest history row 6 s
old); the only FAIL is the already-carded Cerbo MQTT SYN-SENT.

Left for Mark as a new card: PID 986 `labwc -m`, his own desktop session on
tty1, spins at 100 % of a core with 6d7h of CPU in 12 days uptime — the same
labwc spin as the greeters, but it is the physical screen so a session won't
kill it. Swap is still 199/199 MB full and won't drain without a reboot.

### Same session, follow-up — the boat Pi now boots headless

Mark asked whether the GUI was earning its keep. Measured first: with
`rpi-connect-wayvnc` stopped, `labwc` still burned 98 % of a core, so the
spin is labwc's own on a display-less Pi, not wayvnc pulling frames. Same bug
explains the six leaked greeters — one spinning compositor per orphaned
session.

Checked what would break before changing anything. RPi Connect was signed in
and healthy the whole time (the earlier "not running" was a missing
`XDG_RUNTIME_DIR`, not a fault); remote shell needs no display, screen
sharing does, because wayvnc attaches to a live Wayland session. `Linger=yes`
is set for `pi`, so RPi Connect's user services survive a headless boot with
nobody logged in — that was the one thing that could have cost Mark remote
access, and it was already right.

Mark chose on-demand. Executed: `systemctl set-default multi-user.target`,
lightdm stopped, `rpi-connect-wayvnc` disabled (it restart-loops against a
display that isn't there). `systemctl stop lightdm` did not stop the tty1
autologin compositor — PID 986 under PID 920, reparented away at boot — so
both were killed by PID. Procedure is in `RUNBOOK.md` § Starting a desktop on the
boat Pi on demand, and both halves have now been run verbatim from it:
`start lightdm` + `--user start rpi-connect-wayvnc` gives `814691
/usr/bin/labwc -m` and an active wayvnc; the reverse plus `pkill -u pi -x
labwc` leaves `pgrep -a -x labwc` empty with the ssh session intact.

Self-correction worth keeping: the first tear-down used `pkill -u pi -f
"/usr/bin/labwc -m"` and killed the ssh session running it, because `-f`
matched its own command line. `-x labwc` is the correct form, is what the
runbook says, and was left untested until Mark asked whether the scar was
actually fixed — it now is, exercised end to end.

Boat after: load average 1.31 (from 13.2 at session start), 869 MB available,
swap draining, no compositor anywhere, SignalK/Caddy/dex/questdb/ntfy all up.

### Same session, follow-up — stability sweep after the desktop change

Mark asked what else was needed to stabilize the box. Swept it; three things,
and two suspicions of mine that checking killed before they reached him.

**Root cause of the greeter leak, found.** dbus was killed six times on
2026-09-01 (`Main process exited, code=killed, status=9/KILL`), each kill
taking lightdm with it (`lightdm.service: Main process exited,
code=exited, status=1/FAILURE`) and orphaning one `labwc` compositor that
then spun forever. A session at 13:09 that day had installed
`/etc/systemd/system/dbus.service.d/99-test-restart.conf` with
`Restart=always` to test restart behavior. I expected to find that drop-in
still in place and was ready to report it as leftover scaffolding — it is
gone, and `systemctl show dbus -p Restart` reads `no`. That session cleaned
up after itself. Checked before reporting; would have been a false
accusation.

Second false positive caught the same way: `journalctl | grep -c oom-kill`
returned 1, which was **my own grep command echoing into the journal** via
tailscaled's ssh logging. Zero real OOM kills on this boot.

**`pypilot_web` was the real find.** Serving nothing (`curl :8000` →
`code=000`) while writing 720 lines/min — 324k/day, 60 % of all journal
traffic — every line the same `TypeError: wrap_socket() got an unexpected
keyword argument 'allow_unsafe_werkzeug'`. That is what drove journald to
1.8 GB with no `SystemMaxUse` set and root fs at 77 %. Mark's call: disable
now, fix as a high-priority item once stabilized. Disabled; `pypilot.service`
stayed active throughout. Carded with the measured package versions.

Incidental: `navigation/attitude` is currently sourced from `n2k-can0.35`
PGN 127257, not from pypilot-sk, and `yaw` is null. Relevant to the open
"decide pypilot for the trial" card — the attitude feed is not evidence
that pypilot is carrying its weight.

Vacuumed the journal with `--vacuum-time=7d` rather than by size: 1.8 → 1.4
GB, root fs 77 → 76 %. Kept 7 days deliberately so the 2026-09-01 dbus
crashes and the 2026-09-02 QuestDB wedge survive to swap day. The remaining
1.4 GB is nearly all inside that window and will roll off now the flood has
stopped; the `SystemMaxUse` cap is still Mark's open card.

**Still unverified: nothing has rebooted since the box was made headless.**
`multi-user.target` is set and `Linger=yes` is right, but that RPi Connect
returns on a headless boot with nobody logged in is inferred, not observed.
Offered a reboot; not approved this turn. Swap remains 199/199 and the stale
utmp still makes `uptime` claim 13 users — both clear on reboot.

QuestDB's wedge still has no root cause. No OOM, no throttle at the time; it
stopped logging at 07:01:25Z and spun. It could recur on swap day.

### Same session — where the remaining journal traffic comes from

After disabling `pypilot_web`, a clean per-unit count over 80 s reads
**146 lines/min**, down from 543k/day (≈377/min average, with pypilot_web
peaking at 720/min on its own). A first attempt via `journalctl --no-pager |
wc -l` gave 435/min and was wrong — tailscaled logs every ssh command
verbatim, so that method counts the measuring session's own traffic. Use a
`--since` window with a per-unit breakdown, not a whole-journal line count.

88 % of what is left is one thing, and it is **by design, not a fault**:
`openplotter-i2c-read.service` is `Restart=always` / `RestartSec=3` around a
program that reads the sensors once and exits cleanly (`Result=success`,
`ExecMainStatus=0`). OpenPlotter implements its i2c polling loop as a systemd
restart loop — 240,833 restarts in 12 days uptime, ≈13.9/min, each cycle also
opening a `sudo` session for root. That produces five `init.scope` lines plus
its own output every three seconds forever. Do not "fix" it by disabling it:
it is how the BME680 and the other i2c sensors get read.

It does mean the journal will keep growing at a fixed floor no matter what
else is tidied, which is an argument for Mark's open `SystemMaxUse` card
rather than for touching the service. If the dedicated BME680 plugin ever
takes over (the open "BME680 sensor ownership" card), this service and its
traffic go with it.
