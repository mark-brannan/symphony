# Agent decisions

Append-only. Each entry is a call an agent made in pencil: a default it took
under the one-way-door test, with its undo. Written by `agent-decision`; the
heading is the UTC stamp, so `agent_decisions.md#<stamp>` links one entry.

### 20261008t032150z
- HALPI2 bench rollback = release image Halos-Desktop-Marine-HALPI2-AP_2026-08-20.0.img.xz (the shipped image), not a file-level tar Undo: take a file-level tar of / with docker stopped before the real run ([#92](https://github.com/mark-brannan/symphony/pull/92))

### 20261016t035413z
- firmware imported into symphony firmware/halmet rather than a separate repo (the owner offered symphony; the plan records that SensESP repos under the organisation were a mistake) Undo: move the dir to its own repo ([#98](https://github.com/mark-brannan/symphony/pull/98))

### 20261016t045723z
- Boat-down triage raw diagnostics and the agent transcript go to the private claude_prompts_scratch repo under raw_logs/, linked from the public issue, instead of an age-encrypted 1-day artifact. Undo: Revert to the upload-artifact step of 59270367 and drop the scratch push. ([#99](https://github.com/mark-brannan/symphony/pull/99))

### 20261016t045725z
- A triage run whose diagnostics or agent log cannot be saved to the scratch repo fails the job visibly instead of passing green. Undo: Drop the exit 1 on the missing-log branches; the issue comment still shows what was saved. ([#99](https://github.com/mark-brannan/symphony/pull/99))

### 20261016t060101z
- A Discord notification that fails never fails the watch or the triage: the notifier always exits 0 and prints a warning. Undo: run the notifier with check=True and let a Discord or gh failure fail the step ([#112](https://github.com/mark-brannan/symphony/pull/112))

### 20261016t060106z
- One Discord message per outage, edited in place, embed only, mentions disabled; the shared channel sees four edits, not four posts. Undo: post a fresh message per event and drop the marker on the issue ([#112](https://github.com/mark-brannan/symphony/pull/112))
