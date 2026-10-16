#!/usr/bin/env bash
# Every prompt, tells the session when a compose container is crash-looping,
# unhealthy, or built from somewhere other than the main checkout. Silent
# otherwise. See scripts/check_dev_containers.sh for why nothing else says so.
set -uo pipefail

cd "$(dirname "$0")/../.." || exit 0
out=$(bash scripts/check_dev_containers.sh 2>&1) && exit 0
[ -n "$out" ] || exit 0

msg="BROKEN DEV CONTAINERS (scripts/check_dev_containers.sh):
$out"
jq -n --arg m "$msg" '{systemMessage: $m, hookSpecificOutput: {hookEventName: "UserPromptSubmit", additionalContext: $m}}'
