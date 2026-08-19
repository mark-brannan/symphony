# Pre-commit guards: what they may block on

Status: **proposed, awaiting Mark's approval.** Nothing implemented yet.

Written after the hostvars dead-end (below) made a one-line doc edit
uncommittable for days on a machine with no `hostvars.local.yaml`. That was
not one bad hook. Four hooks share the same shape, so the fix is one stated
invariant applied to all four rather than four patches.

If this is approved, the durable half (the invariant, the filter/checker
split, the message contract) moves to `reference/precommit_guards.md` and
this file goes away.

---

## 1. The invariant

> **A pre-commit hook may FAIL only on a condition that is (a) visible in a
> path listed by `git diff --cached --name-only`, and (b) fixable by the
> person running the commit, right now, with what they have.**
>
> Anything else warns at commit time and fails in CI.

Clause (a) is your starting position and I think it is right. Clause (b) is
the one the incident actually turned on, and it is not implied by (a): the
hostvars checker was arguably scoped correctly in spirit — a machine-local
value really was in the index — and it still trapped you, because the only
remedy it named required a file you did not have. A guard that is correct
and unsatisfiable is still a trap.

Two corollaries:

- **Blocking is a claim about the committer, not about the repo.** "This
  repo is in a bad state" is never sufficient grounds to block. "*You* are
  about to put a bad thing into git, and here is the keystroke that stops
  it" is.
- **CI, not pre-commit, owns whole-repo truth.** `.pre-commit-config.yaml`
  already says this in its header: the hooks are fast feedback, the
  workflow is the boundary. The four hooks quietly contradicted it.

### The case you suspected: guarding against silent *absence*

You were right that there's a category here, and I want to be precise about
where it lands, because it looks like a counterexample and mostly isn't.

Absence is only ever detectable relative to something present. Every
absence guard in this repo already has a staged anchor:

| what is silently absent | anchor path in the staged set |
|---|---|
| a `{{ placeholder }}` missing from git's copy | the covered file being staged |
| sops markers missing from a staged blob | the sops-covered file being staged |
| `filter.sops.clean` missing from git config | the `filter=`-covered file being staged |
| a `.gitattributes` entry missing for a new `.sops.yaml` rule | `.sops.yaml` being staged |
| a covered file *deleted* from `.gitattributes` | `.gitattributes` being staged |

So scoping to staged paths does not blind any of these. In each case the
danger is only *realised* when a covered path is in the commit — an
unconfigured filter on a machine that commits nothing covered has harmed
nobody yet.

The genuine exception is the case with **no nameable staged anchor at all**:
a file that went into history in the clear months ago because a hook was
bypassed or never installed. Nothing in today's staged set points at it. I
concede this category exists — and I still say it must not block a
pre-commit, because the person hitting it is by construction not the person
who caused it and may have no way to fix it. That is a CI job and a
history-rewrite conversation, not a commit-time gate. So the invariant
stands; the exception is routed, not accommodated.

The one real cost of clause (a): repo-wide drift caught *later* than today.
Accepted, with a mitigation — every guard grows an `--all` mode that CI runs
and a person can run by hand, and the commit-time run still *prints*
whole-repo findings as warnings. You lose blocking, not visibility.

---

## 2. Filters fail soft. Checkers fail hard. Neither may fail blind.

The current pairing is the worst available and you named it: `clean` warns
and emits the wrong bytes, `check` then blocks on those bytes. The filter
manufactures the state the checker punishes, and the punished party is
whoever commits next.

**Decision, and the reasoning, because it is not the obvious one:**

- **`smudge` never fails.** Non-negotiable. It runs during `git checkout`;
  a failing smudge breaks checkout itself. (Already true — keep it.)

- **`clean` never fails either.** This is the counterintuitive half. The
  attractive fix is "make `clean` exit non-zero rather than emit a literal
  value" — then the bad bytes never reach the index and the checker has
  nothing to catch. I looked at it and rejected it: git runs `clean` to
  compare the working tree against the index, so a hard-failing clean breaks
  `git status` and `git diff` — in *exactly* the state you were stuck in.
  That converts an uncommittable repo into an unreadable one.

- **Therefore the checker owns all blocking**, and pays for that privilege
  by being scoped (clause a) and escapable (clause b).

- **A soft filter must be loud in a place the person will actually look.**
  `clean`'s warnings go to stderr in the middle of `git add` output and are
  routinely missed. So the checker's message must *name the filter as the
  cause* — "the hostvars clean filter passed this through because
  `hostvars.local.yaml` is missing" — rather than only describing the
  symptom in the index. The checker is where the human is paying attention.

Stated once, for the reference file: **whichever layer cannot be escaped is
the layer that must not block.**

---

## 3. Per-hook verdicts

The headline: **`always_run: true` was never the bug, and none of the four
should move to `files:`.** The bug is asserting unscoped state. `always_run`
plus *internal* self-scoping from `git diff --cached` is the correct shape —
it is what `precommit_secret_guard.sh` already does, and why that one has
never trapped anyone.

Why not `files:`, concretely:

- pre-commit's `files:` gives the hook a filename list; these hooks read the
  **index**, not those files. The regex would be a second, drifting copy of
  scope that already lives in `.hostvars.yaml` / `.sops.yaml` /
  `.gitattributes`.
- `files:` does not fire on a commit that only *deletes* a covered path —
  which is precisely when check 1 of the secret guard must run.

| hook | today | verdict |
|---|---|---|
| `sops-secret-guard` | `always_run`, self-scoped per block | **Compliant. Keep as-is structurally.** Only change: messages gain the missing elements from §4 (hook name, no-resource exit, `--no-verify`). This is the reference implementation. |
| `hostvars-placeholders` | `always_run`, iterates every covered path | **Self-scope.** `check` intersects `.hostvars.yaml`'s paths with the staged name list. Keep `always_run`; add `check --all` for CI. |
| `repo-hygiene` | `always_run`, three rules of three different scopes | **Split by rule** (below). Keep `always_run`; add `--all`. |
| `encoding-health` | `always_run`, scans every tracked file | **Self-scope.** New `--staged` mode for pre-commit; `--repo` stays whole-tree for CI. Clearest case of the four: mojibake in a file you did not touch is not your commit's problem. |

### `repo-hygiene`, rule by rule

- `rule_frozen_secrets_untouched` — already reads `git diff --cached --
  secrets/`. **Compliant, unchanged.** (And correctly a hard fail: it blocks
  only on a diff you authored, and the exit is to not make that diff.)
- `rule_declared_filters_are_configured` — currently fails whenever any
  declared filter is unconfigured, regardless of what you are committing.
  **Scope it:** fail only for filters covering a path in the staged set;
  warn (don't fail) for the rest. This still catches the 2026-08-14 incident
  — that was a Pi about to commit sops-covered files — while letting someone
  without an age key commit a doc edit.
- `rule_audible_alarms_are_scoped` — already warn-only, so it never blocked.
  **Scope its scan to staged plugin configs** anyway, so the warning refers
  to something you did. Whole-tree scan moves under `--all`.

---

## 4. Message contract

Every **blocking** message must carry five elements, in this order:

1. **which hook** — the pre-commit id, so the person can `SKIP=<id>` rather
   than reaching for the blunt instrument.
2. **which file** — a repo-relative path, always, even when the hook found
   it by scanning.
3. **what is actually wrong** — the state, not the rule's name.
4. **the exact command that fixes it** — copy-pasteable, no placeholders the
   reader has to resolve.
5. **how to proceed when that fix is not available to this person** — the
   no-resource exit.

Element 5 is the new one and the whole point. It is always at least one of:

- `git restore --staged <path>` — drop the offending path from *this*
  commit and let the rest through. Non-destructive: the working tree is
  untouched. This is the right exit for nearly every case here.
- `SKIP=<hook-id> git commit ...` — skip one hook, keep the other seven.
- `git commit --no-verify` — documented last resort, **named explicitly.**
  Your incident's sharpest edge was that no message mentioned it. A guard
  that hides its own escape hatch is not safer, it is just harder to leave.

No shared formatter is being built (see §7). The contract is instead
enforced by test: a regression test drives each guard into failure and
asserts its stderr contains a path, a runnable command, and a documented
exit. That catches a future message that quietly drops element 5.

---

## 5. Dead-end loops, and what closes each

**L1 — hostvars, the one you hit.** No `hostvars.local.yaml` → `clean`
passes the literal ntfy URL into the index → `check` (unscoped) fails on
*every* commit → message says run `refresh` → `refresh` requires the file
you don't have. No exit named.
*Closed by:* staged-scoping (a doc-only commit no longer sees this hook at
all — this alone ends the incident) + element 5 on the message
(`git restore --staged signalk/plugin-config-data/signalk-ntfy.json`) +
`refresh`'s own error pointing at `hostvars.local.yaml.example` and saying
you may simply not stage the covered file.

**L2 — unconfigured filter without the key.** `unconfigured-filter` fails →
says run `scripts/setup-git-filters.sh` → that needs `sops`, `age`, and the
age key. A contributor or a fresh cloud checkout has none of them.
*Closed by:* scoping to staged covered paths (you can commit anything else)
+ message naming the unstage exit and `SKIP=repo-hygiene`.

**L3 — sops markers missing, same root cause.** Already scoped; the block is
correct. But the message stops at "did this clone run setup-git-filters.sh?"
with no answer for "no, and it can't."
*Closed by:* element 5 only.

**L4 — pre-existing mojibake.** A tracked file damaged by an old latin-1
round-trip blocks every commit forever, and there is currently no fix
command at all — element 4 is missing outright.
*Closed by:* staged-scoping + a named remedy for a file you did touch.

**L5 — the shared-index race, and the one I cannot fully close.** Another
session stages a broken file; your commit blocks on their work. Staged
scoping does not help — their file *is* staged. `git restore --staged` would
mutate shared state, which `CLAUDE.md` rightly forbids you to do blind.
*Partially closed by:* the message naming the exact path, so you can tell at
a glance it isn't yours, plus an explicit line to that effect — "if you did
not stage this path, another session did; do not unstage it, use
`SKIP=<hook>` for this commit and tell them." I want to be honest that this
is mitigation, not a fix. The real fix is the worktree default `CLAUDE.md`
already prescribes; a hook cannot see your `git commit -- <pathspec>` and so
cannot distinguish your index from theirs.

---

## 6. What this does *not* weaken

Worth stating plainly so the security posture doesn't get re-litigated:

- Nothing here reduces what CI blocks. Every check that is whole-repo today
  stays whole-repo in `.github/workflows/validate.yml`, via `--all`.
- The realistic leak path — a credential-shaped string in a file nobody
  configured — is check 3 of the secret guard, which is staged-scoped
  already and is untouched.
- Making `--no-verify` discoverable does not lower the bar: it was always
  one search away, and the header of `.pre-commit-config.yaml` already says
  these hooks are bypassable by design. Concealing it only taxed the honest.

---

## 7. Overlap with the parallel session

Checked at design time: **`scripts/check_clone_setup.sh` and a shared
strict/contributor mode + message formatter do not exist** — not in
`scripts/`, not on `origin/main`, not on any pushed `claude/*` branch. Per
your instruction I am not building them. Implementation uses plain messages
meeting §4's contract by convention and by test. If those helpers land
before implementation finishes, the messages get retrofitted to them; the
contract in §4 is written so that retrofit is mechanical.

---

## 8. Implementation plan (small verified commits)

1. `hostvars_filter.py`: `check` self-scopes to staged covered paths; add
   `check --all`; messages meet §4. Extend `scripts/test_hostvars_filter.py`.
2. `check_encoding_health.py`: add `--staged`; point the hook at it; keep
   `--repo` for CI. Add a test.
3. `lint_repo_hygiene.py`: scope `unconfigured-filter` and
   `audible-alarms`; add `--all`; messages meet §4. Add a test.
4. `precommit_secret_guard.sh`: messages only.
5. `.pre-commit-config.yaml` comment pass + CI workflow gets the `--all`
   invocations.
6. A message-contract regression test covering all four.

Each commit is independently correct and leaves the hooks working.

### Open question for you

Step 5 assumes CI should gain the `--all` runs so nothing stops being
enforced. If `validate.yml` already covers some of this, I'll wire to what's
there rather than duplicating — I'll confirm against the workflow before
touching it, but flagging it as the one place this design touches CI.
