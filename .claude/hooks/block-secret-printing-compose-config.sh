#!/usr/bin/env bash
# Blocks `docker compose config` (and the legacy `docker-compose config`)
# unless `--no-interpolate` is present.
#
# Why: this repo's compose files interpolate several secrets directly in
# YAML (e.g. `${GF_SECURITY_ADMIN_PASSWORD}` in compose-proxy.yml's Caddy
# basic-auth), not only via `env_file:`. Plain `docker compose config`
# resolves and prints every one of those in cleartext -- that's it doing
# exactly what it's documented to do, not a bug in the tool. On 2026-08-20,
# running it to sanity-check an unrelated compose fix printed the full
# resolved secret set into a Claude Code session transcript, which
# Anthropic retains server-side; deleting the local terminal scrollback
# does not undo that. Seven credentials had to be rotated as a result --
# see ROTATION.md, 2026-08-20 entry.
#
# `docker compose config --no-interpolate` answers the same question this
# command is almost always asked for real work -- "is the YAML well-formed,
# are the includes/profiles resolving right" -- without ever expanding a
# `${VAR}` reference to its value. If you actually need to confirm a
# specific resolved value, extract that one field from sops directly
# instead of asking compose to print everything:
#   sops --decrypt --extract '["field_name"]' secrets/symphony.sops.yaml
#
# No existing guard in this repo covers this: secretguard.py,
# gitleaks_precommit.sh, and friends all fire at git-commit time, on staged
# content. This is a shell-command-output-time leak, a different axis
# entirely, and nothing was watching it before this hook.
set -euo pipefail

input=$(cat)
tool=$(printf '%s' "$input" | jq -r '.tool_name // ""')

case "$tool" in
  Bash|PowerShell)
    cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""')
    if printf '%s' "$cmd" | grep -qE '(^|[;&|]|\s)docker(-|\s+)compose\s+config(\s|$)' \
       && ! printf '%s' "$cmd" | grep -qE -- '--no-interpolate'; then
      jq -n --arg r "Blocked by .claude/hooks/block-secret-printing-compose-config.sh: 'docker compose config' without --no-interpolate resolves every \${VAR} reference to its live value, including secrets interpolated directly in this repo's compose YAML -- and that output lands in this session's transcript, which is retained server-side even if you delete it locally. This is exactly how the 2026-08-20 credential-rotation incident happened (see ROTATION.md). Add --no-interpolate if you're checking config structure/syntax -- that's almost always what 'validate a compose fix' actually needs. If you genuinely need one resolved value, pull it directly: sops --decrypt --extract '[\"field_name\"]' secrets/symphony.sops.yaml." '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: $r}}'
      exit 0
    fi
    ;;
esac

exit 0
