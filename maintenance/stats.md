# Quality Metrics & Session Hygiene Stats

Tracking measurable indicators of workflow health and session cost. These are both direct signals (cherry-pick happens) and proxy signals (churn, session duration) for workflow breakdown.

## Metrics

### Cherry-picks
- **Definition**: Using `git cherry-pick` instead of fixing the root cause (rebase, amend, redo on correct branch)
- **Why it matters**: Red flag for worktree collisions, sessions sharing state incorrectly, or workflow breakdown
- **Recorded by**: `.claude/hooks/measure-cherry-pick.sh` (detects `cherry-pick` in commit messages)
- **Target**: Zero, or only documented exceptions with owner approval

### Session Duration (Agentic Loop Cost)
- **Definition**: Total tool-call count / wall-clock time in minutes
- **Why it matters**: Long agentic loops (PR review, CI chasing, branch cleanup) re-send full context on every tool call, multiplying token cost
- **Target**: Scope tightly; prefer one considered pass over iterative poking

### Churn (Rework & Revisions)
- **Definition**: Commits that undo or significantly refactor prior commits in the same session
- **Why it matters**: Indicates either unclear requirements, insufficient planning, or unnecessary iteration
- **Recorded**: Manual notes in session or commit messages
- **Target**: Minimize; each commit should be verified before the next

### Decision Pushes (Unwarranted)
- **Definition**: Questions/decisions pushed to owner without sufficient context, multiple times for the same decision
- **Why it matters**: Owner context-switches; same decision re-derived costs their judgment twice
- **Target**: Batch questions; research fully before asking; record open Qs in `maintenance/priorities.md` under Blocked, not session scrollback

## Tracking Format

Metrics are recorded as:
- **Cherry-picks**: Detected by hook, logged on push
- **Session notes**: Added to commit messages, session summaries, or `maintenance/log.md`
- **Trends**: Reviewed periodically to surface patterns (e.g., "cherry-picks spike after concurrent multi-session changes")

## Hook Behavior

When `git push` is called, `.claude/hooks/measure-cherry-pick.sh` checks for cherry-pick commits and:
1. Logs them to a stats file (timestamp, commit hash, branch)
2. Warns in stderr so it's visible to the session
3. **Does not block the push** (but records for measurement)

## Open Questions

- Should churn/session-duration be auto-measured by hooks, or manual notes?
- Stats file location: symphony `maintenance/` or dotfiles?
- Reporting cadence: per-push, per-session, weekly?
