# S/V Symphony

## SV Symphony IoT setup
For setting up SV Symphony's devices and computer systems.

Inspired by [meri-imperiumi/curiosity](https://github.com/meri-imperiumi/curiosity)

## Symphony — Maintenance & Improvement Tracking
1985 Hans Christian 38T. Working log of deferred maintenance, in-progress
work, and planned improvements.

### Structure
- `priorities.md` — current triage: In Progress / Blocked / Backlog / Someday-Maybe
- `log.md` — chronological ship's-log record, oldest entry first, real append (tail-friendly)
- `systems/` — one file per system, empty for now; populate as it makes sense
- `reference/specs.md` — vessel identity, registration, and physical particulars
- `reference/vendors-parts.md` — vendor contacts and parts sourcing

### Workflow
- Append to `log.md`; use whatever date precision is actually known (day, month, or year) — don't force false precision
- Move items between In Progress / Blocked / Backlog / Someday-Maybe in `priorities.md` as status changes; keep In Progress small
- `systems/*.md` are living reference, edited in place — git tracks the history

### Open items
- Electrical/IoT sensor and SignalK-integration tasks are tracked separately from the main backlog for now, pending re-integration once `priorities.md` and `log.md` are in good shape.
- Physical specs that also live as SignalK config (calibration curves, sensor mappings) aren't yet reconciled between this repo and the SignalK/Ansible repo.
