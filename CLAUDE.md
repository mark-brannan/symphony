# Working conventions — Symphony project

This repo combines Symphony's maintenance tracking with her SignalK/IoT
infrastructure. Conventions below apply to the maintenance side
(`maintenance/`, `reference/`); the SignalK/Ansible side has its own
established practices, not covered here.

## Files
- `maintenance/log.md` — chronological ship's-log record of work done.
- `maintenance/priorities.md` — current backlog and triage.
- `reference/specs.md` — vessel identity, registration, and physical particulars.
- `reference/vendors-parts.md` — vendor contacts and parts sourcing.
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
- Nothing gets committed or pushed without the owner's explicit go-ahead on
  that specific action.
