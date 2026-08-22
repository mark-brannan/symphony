# Hook Setup & Metrics Collection

## Cherry-pick Detection Hook

The `measure-cherry-pick.sh` hook detects when cherry-pick commits are being pushed and logs them as a quality metric.

### Installation

**Option A: As a git pre-push hook** (automatic on every push)

```bash
# From symphony repo root:
cp .claude/hooks/measure-cherry-pick.sh .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

**Option B: Manual invocation** (when needed)

```bash
.claude/hooks/measure-cherry-pick.sh <branch-name>
```

### How It Works

1. Runs on `git push` (if installed as pre-push hook)
2. Checks commits being pushed for "cherry" in their message
3. **Warns to stderr if found** — visible in the push output
4. Does NOT block the push (it's a metric, not a blocker)
5. Can log to a stats file when integrated (see stats.md)

### What Triggers It

- Commit message contains "cherry-pick" or mentions picking commits
- Commonly occurs when: commits ended up on the wrong branch and were reapplied

### What to Do If It Fires

1. Read CLAUDE.md § Cherry-pick
2. Either:
   - Fix it: rebase, amend, or redo the commit on the correct branch instead
   - Document it: if cherry-pick is genuinely needed, explain why in the commit message
   - Escalate: flag to owner if unclear whether this is legitimate

## Integrating with Dotfiles

If you prefer to track metrics centrally in dotfiles:

1. Symlink or copy this script to `~/.claude/hooks/`
2. Set `STATS_FILE` environment variable to point to your central stats location
3. Modify the hook to append to your JSON/YAML stats log as needed

## Future Metrics

This framework can be extended to track:
- Session duration / agentic loop cost (via harness integration)
- Churn detection (commits that undo prior work)
- Decision-push warnings (when same question asked multiple times)
