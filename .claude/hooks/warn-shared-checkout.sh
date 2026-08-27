#!/usr/bin/env bash
# Warns -- every single time, deliberately -- when a session is about to
# write inside the SHARED checkout of this repo while that checkout is in a
# state where the write could clobber or revert someone else's work.
#
# Why this exists: CLAUDE.md has mandated worktree-per-session since
# 2026-08-19 (0a76db4) and the collision happened anyway on 2026-08-26 --
# commit 351fdb0 orphaned by dc36c63 a minute later, plus ten files of stale
# tree that would have reverted eight commits and deleted
# reference/distress_monitoring.md if committed. Prose did not hold. A
# blanket deny was rejected: Mark legitimately drives sessions in the shared
# checkout to untangle his own work, and a ban there is friction with no
# payoff. So: warn, never block.
#
# Every turn, not once per session. That is the point, not an oversight --
# the warning has to be annoying enough not to scroll past, and the risk
# gate below means it should be rare.
#
# PROVISIONAL, not settled (2026-08-27): the specific risk gate -- behind
# origin/main, or dirty with files this session did not touch -- is a first
# try. If it warns when it shouldn't, or stays quiet when it should have
# spoken, change the gate. Do not treat these two conditions as the design.
set -euo pipefail

input=$(cat)
cwd=$(printf '%s' "$input" | jq -r '.cwd // ""')
[ -n "$cwd" ] || exit 0

# Only the shared checkout. A worktree lives under .claude/worktrees/ and is
# nobody else's business.
case "$cwd" in
  */.claude/worktrees/*) exit 0 ;;
esac

toplevel=$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null) || exit 0
# A linked worktree's git-dir is under <main>/.git/worktrees/; the shared
# checkout's is <toplevel>/.git itself. --absolute-git-dir, not --git-dir:
# the latter answers ".git" relative to cwd and never matches.
gitdir=$(git -C "$cwd" rev-parse --absolute-git-dir 2>/dev/null) || exit 0
[ "$gitdir" = "$toplevel/.git" ] || exit 0

reasons=""

# Behind origin/main? Use the ref already on disk -- no fetch, a hook must
# not add network latency to every tool call.
behind=$(git -C "$toplevel" rev-list --count HEAD..origin/main 2>/dev/null || echo 0)
if [ "${behind:-0}" -gt 0 ] 2>/dev/null; then
  reasons="$reasons  - HEAD is $behind commit(s) behind origin/main. Editing on a stale base is exactly how 2026-08-26's near-revert happened.
"
fi

# Uncommitted work already sitting here, from whoever else.
dirty=$(git -C "$toplevel" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
if [ "${dirty:-0}" -gt 0 ] 2>/dev/null; then
  reasons="$reasons  - $dirty uncommitted path(s) already in the tree. If you did not put them there, another session (or Mark) did -- read them before committing anything.
"
fi

[ -n "$reasons" ] || exit 0

msg="SHARED CHECKOUT, RISKY STATE -- $toplevel
$reasons
Not blocked. But: commit with an explicit pathspec (git commit -m ... -- path),
never 'git add -A', and consider EnterWorktree instead."

jq -n --arg m "$msg" '{systemMessage: $m}'
