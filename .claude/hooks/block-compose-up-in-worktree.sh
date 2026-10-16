#!/usr/bin/env bash
# Denies `docker compose up|create|run` from a linked worktree.
#
# Why: the compose project is named `symphony`, so containers are shared, but
# relative bind mounts (`./signalk`) resolve against the directory compose
# ran in. A session that ran `docker compose up` in a throwaway worktree
# pinned the long-lived signalk-server to that worktree on 2026-09-04; when
# the worktree was deleted, Docker recreated the path as a root-owned stub
# and signalk crash-looped 9,776 times over five weeks. Worktrees are for
# editing; the stack runs from the main checkout.
#
# Passes when `cd` or `--project-directory` names the main checkout itself;
# worktrees live under it, so a mere prefix match is not enough.
set -euo pipefail

input=$(cat)
cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""')
cwd=$(printf '%s' "$input" | jq -r '.cwd // ""')
[ -n "$cwd" ] || exit 0

printf '%s' "$cmd" | grep -qE '(^|[;&|(]|\s)docker(-|\s+)compose(\s+-{1,2}[a-z-]+(=\S+|\s+[^-[:space:]]\S*)?)*\s+(up|create|run)(\s|$)' || exit 0

toplevel=$(git -C "$cwd" rev-parse --show-toplevel 2>/dev/null) || exit 0
gitdir=$(git -C "$cwd" rev-parse --absolute-git-dir 2>/dev/null) || exit 0
[ "$gitdir" != "$toplevel/.git" ] || exit 0 # the main checkout itself

main=$(dirname "$(git -C "$cwd" rev-parse --path-format=absolute --git-common-dir)")
pre='(cd|--project-directory)[[:space:]]+["'\'']?'
post='/?["'\'']?([[:space:];&|)]|$)'
[[ $cmd =~ $pre"$main"$post ]] && exit 0

jq -n --arg m "$main" '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: ("Blocked by .claude/hooks/block-compose-up-in-worktree.sh: this is a linked worktree, and compose resolves relative bind mounts against the directory it runs in -- a container created here keeps pointing at this worktree after it is deleted, then crash-loops (signalk-server, 2026-09-04). Run it from the main checkout instead: cd " + $m + " && docker compose up -d --no-deps <service>")}}'
