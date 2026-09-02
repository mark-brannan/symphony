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
# Tuned 2026-08-28: the original "dirty with files this session did not
# touch" gate actually checked total dirty-path count, full stop -- so it
# fired on every single write in the shared checkout, including a session's
# own prior edits from earlier in the same conversation. That is alert
# fatigue, not signal: a warning that fires on every turn regardless of
# content trains you to stop reading it, which is the one failure mode this
# hook exists to prevent. Fix: remember which paths *this session* has
# already written (a per-session marker file under .git/, cheap and
# auto-cleaned since .git/ isn't tracked) and only count dirty paths outside
# that set. A file dirty because of your own last three edits is not a
# collision risk; a file dirty because someone else touched it is.
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

# Uncommitted work already sitting here, from whoever else -- but not work
# this same session already put there itself. Track paths this session has
# written across turns in a marker file under .git/ (never shared with
# other checkouts or sessions), and only flag dirty paths outside that set.
session_id=$(printf '%s' "$input" | jq -r '.session_id // ""')
touched_file=""
if [ -n "$session_id" ]; then
  touched_file="$toplevel/.git/claude-shared-checkout-touched.$session_id"
  new_path=$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null || true)
  if [ -n "$new_path" ]; then
    case "$new_path" in
      "$toplevel"/*) rel_path="${new_path#"$toplevel"/}" ;;
      *) rel_path="$new_path" ;;
    esac
    printf '%s\n' "$rel_path" >>"$touched_file"
  fi
fi

foreign_dirty=0
while IFS= read -r line; do
  [ -n "$line" ] || continue
  path="${line#???}"
  # Rename/copy lines read "old -> new"; the working-tree path is the new one.
  case "$path" in
    *' -> '*) path="${path#*' -> '}" ;;
  esac
  if [ -n "$touched_file" ] && [ -f "$touched_file" ] && grep -qxF "$path" "$touched_file"; then
    continue
  fi
  foreign_dirty=$((foreign_dirty + 1))
done <<EOF
$(git -C "$toplevel" status --porcelain 2>/dev/null)
EOF

if [ "$foreign_dirty" -gt 0 ]; then
  reasons="$reasons  - $foreign_dirty uncommitted path(s) in the tree that this session didn't put there. If you did not put them there, another session (or Mark) did -- read them before committing anything.
"
fi

[ -n "$reasons" ] || exit 0

msg="SHARED CHECKOUT, RISKY STATE -- $toplevel
$reasons
Not blocked. But: commit with an explicit pathspec (git commit -m ... -- path),
never 'git add -A', and consider EnterWorktree instead."

jq -n --arg m "$msg" '{systemMessage: $m}'
