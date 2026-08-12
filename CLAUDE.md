# Working conventions — Symphony project

This repo combines Symphony's maintenance tracking with her SignalK/IoT
infrastructure. Conventions below cover the maintenance side
(`maintenance/`, `reference/`) and the docs for the software stack
(`RUNBOOK.md`, `reference/software_stack.md`). Ansible practices aren't
covered here.

## Files
- `maintenance/log.md` — chronological ship's-log record of work done.
- `maintenance/priorities.md` — current backlog and triage.
- `reference/specs.md` — vessel identity, registration, and physical particulars.
- `reference/vendors-parts.md` — vendor contacts and parts sourcing.
- `reference/software_stack.md` — how the SignalK stack is built and why.
- `RUNBOOK.md` — operating procedures for the software stack.
- `systems/*.md` — one file per boat system, intentionally empty for now.
  Don't impose section structure on these until asked — the owner wants to
  arrive at the right structure organically, not have it templated in.

## log.md
- Real ship's log style: short, factual, dated entries — what was done,
  found, or decided. Not a place for technical specs/part numbers (those
  belong in the relevant `systems/*.md` file once populated).
- Chronological, oldest entry first, true append — new entries go at the
  bottom, matching `tail` semantics.
- Use whatever date precision is actually known: a full date, a month, or
  just a year. Don't force false precision onto an approximate memory.
  A `## Date unknown` section at the bottom is fine for confirmed-done work
  with no date yet.

## priorities.md
- Kanban-flavored, not GTD: **In Progress** (keep this small — WIP limit of
  roughly 2-3 items, matching the owner's stated preference for steady
  completion over a sprawling backlog) / **Blocked** / **Backlog** (ordered —
  position implies priority) / **Someday/Maybe** (uncommitted ideas).
- Finished items don't stay here — they move to `log.md` and get removed
  from this file, so it always reflects only what's still open.
- Electrical/IoT sensor and SignalK-integration tasks are intentionally
  tracked separately from this backlog for now — don't merge them in without
  asking first.

## reference/specs.md
- Flat `key: value` list, one item per bullet (plain consecutive lines
  collapse into one paragraph in markdown — always use `- ` list items).
- Precise/technical field names over colloquial ones: e.g. "USCG Official
  Number," not "Documentation number." Match the terminology actually used
  on the source document (COD, registration, etc.) where there is one.
- No parenthetical hedging or uncertainty notes in this file. If something
  is uncertain, ask the owner directly rather than writing a caveat into
  the doc.
- Where a field has both a vessel-specific documented value and a generic
  stock/design-reference value (e.g. from sailboatdata), prefer the
  vessel-specific one and drop the generic duplicate — don't carry both as
  if they were peers.

## RUNBOOK.md
- **Actions only.** Every section answers "what do I do." Commands, the
  order to run them in, and how to tell it worked. If a passage doesn't
  change what the reader does next, it belongs in
  `reference/software_stack.md` instead.
- Include a *why* only where its absence causes the wrong action — e.g.
  "don't skip `verify`, here's what silently breaks without it." One or two
  sentences, next to the step. Not a background section.
- No point-in-time status. Don't write down which containers were up, what
  was broken on a given day, or what an audit found last week — that rots
  into a lie within days. Durable config traps are fine; snapshots aren't.
- Don't editorialize about the system's design, security posture, or
  industry practice. State the trap and the fix.

## reference/*.md
- Explanatory material lives here: architecture, design rationale, known
  risks, why a thing is the way it is.
- Still no speculation. Verify before asserting — check the running system,
  the config file, or the vendor's own docs. Never infer behavior from a
  config field name or a plugin's title and write it up as fact.
- When a claim can't be verified, leave it out or flag it in conversation.
  A gap is better than a confident guess.

## Working style, generally
- No unsolicited notes, hedges, or "this may have changed" commentary
  embedded in any doc — flag uncertainty in conversation, keep the files
  themselves clean and current.
- Ambiguity in old records (multiple sources disagreeing, unclear dates)
  gets flagged to the owner rather than silently resolved by guessing.

## Git hygiene
- Never `git add -A` / `git add .` in this repo — it holds infra config and
  secrets (`.env`, `signalk/security.json`) alongside the maintenance docs.
  Stage files explicitly by name.
- Branch judiciously for features.  Small changes such as a package.json update
should go directly to main
- Small atomic changes may be committed and pushed as soon as they are verified.
Larger changes, especially if they merit a feature branch, should get a PR and 
sign off from the owner.  If a change is potentially destructive or could affect
adjacent environments for plugin testing, then ask for explicit permission before
changing, committing, or pushing.
- Multiple Claude sessions may be working this checkout at once. Before running
  any git command whose effect isn't scoped to files you explicitly name, run
  `git status` and read the full output — don't assume the working tree only
  holds what you touched. If it shows changes you didn't make, stop and tell
  the owner before running anything that would revert or discard them; don't
  guess whether they're safe to lose.
- Never run, without the owner's explicit go-ahead in that moment:
  `git reset --hard`, `git clean` (any flags), `git checkout` or `git restore`
  with no pathspec or a directory pathspec, `git stash` (repo-wide, not a
  named/scoped stash), `git branch -D`, or `git push --force*`. Each of these
  can discard or overwrite work outside whatever you meant to target,
  including another session's uncommitted changes. `git checkout HEAD -- path`
  is fine for a single file you've confirmed the diff of; it stops being fine
  the moment `path` is a directory you haven't fully read the diff of first.
- sops-encrypted files must round-trip through the `sops` filter, never
  hand-edited in cleartext and committed directly.
- When two copies of a SignalK peripheral/device config disagree (a backup vs.
  the committed file, two repos, etc.), union them rather than picking one and
  discarding the other's fields — merge to the superset. A stale or invalid
  peripheral entry costs SignalK a harmless connection-retry log line; a
  silently dropped working one costs real functionality. Keep everything, flag
  anything that's a genuine conflict (not just a gap) rather than guessing, and
  let the owner prune deliberately later.
