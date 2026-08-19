#!/usr/bin/env bash
# Blocks scheduled wakeups that are bound to a live session.
#
# Why: a trigger bound to a persistent session re-sends that session's ENTIRE
# accumulated context on every firing. The cost grows with each wake, and the
# harness asks PR-watching sessions to re-arm a check-in before ending a turn,
# so the shape reproduces itself. On 2026-08-18 this put five self-re-arming
# wakeups on one PR against a session holding 2.6M tokens of read history, and
# burned two five-hour limit windows.
#
# What is still allowed:
#   - subscribe_pr_activity  -- webhook-driven, free while idle, faster too
#   - create_trigger with create_new_session_on_fire=true -- each fire starts
#     from a clean context instead of compounding
#   - CronCreate / /loop -- session-scoped, 7-day expiry, self-terminating
set -euo pipefail

input=$(cat)
tool=$(printf '%s' "$input" | jq -r '.tool_name // ""')

deny() {
  jq -n --arg r "$1" '{hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: $r}}'
  exit 0
}

case "$tool" in
  *__send_later)
    deny "Blocked by .claude/hooks/no-persistent-polling.sh: send_later binds a wakeup to this session and re-sends its full context on every fire, which compounds without bound. Use subscribe_pr_activity to wake on real events instead, or create_trigger with create_new_session_on_fire=true. If a check is still running, say so and end the turn -- the webhook will wake the session when it finishes."
    ;;
  *__create_trigger)
    fresh=$(printf '%s' "$input" | jq -r '.tool_input.create_new_session_on_fire // false')
    persist=$(printf '%s' "$input" | jq -r '.tool_input.persistent_session_id // ""')
    if [ "$fresh" != "true" ] || [ -n "$persist" ]; then
      deny "Blocked by .claude/hooks/no-persistent-polling.sh: a trigger bound to an existing session re-sends that session's whole context each time it fires. Set create_new_session_on_fire=true (and omit persistent_session_id) so each firing starts from a clean context, or use subscribe_pr_activity for event-driven waking."
    fi
    ;;
esac

exit 0
