#!/usr/bin/env bash
# Denies `docker compose up|create|run` (and scripts/dev_stack.sh) from a
# linked worktree.
#
# Why: the compose project is named `symphony`, so containers are shared, but
# relative bind mounts (`./signalk`) resolve against the directory compose
# ran in. A session that ran `docker compose up` in a throwaway worktree
# pinned the long-lived signalk-server to that worktree on 2026-09-04; when
# the worktree was deleted, Docker recreated the path as a root-owned stub
# and signalk crash-looped 9,776 times over five weeks. Worktrees are for
# editing; the stack runs from the main checkout.
#
# Passes when the command names the main checkout (`cd <main> && ...` or
# `--project-directory <main>`), since the session cwd is then not where
# compose runs.
set -euo pipefail

input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""')
cwd=$(printf '%s' "$input" | jq -r '.cwd // ""')
[ -n "$cwd" ] || exit 0

printf '%s' "$cmd" | grep -qE '(^|[;&|(]|\s)(docker(-|\s+)compose\s+(.*\s)?(up|create|run)(\s|$)|(\./)?(scripts/)?dev_stack\.sh\s+up)' || exit 0

toplevel=$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null) || exit 0
gitdir=$(git -C "$cwd" rev-parse --absolute-git-dir 2>/dev/null) || exit 0
[ "$gitdir" != "$toplevel/.git" ] || exit 0 # the main checkout itself

main=$(dirname "$(git -C "$cwd" rev-parse --path-format=absolute --git-common-dir)")
case "$cmd" in *"$main"*) exit 0 ;; esac

jq -n --arg m "$main" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: ("Blocked by .claude/hooks/block-compose-up-in-worktree.sh: this is a linked worktree, and compose resolves relative bind mounts against the directory it runs in -- a container created here keeps pointing at this worktree after it is deleted, then crash-loops (signalk-server, 2026-09-04). Run it from the main checkout instead: cd " + $m + " && docker compose up -d --no-deps <service>")}}'
