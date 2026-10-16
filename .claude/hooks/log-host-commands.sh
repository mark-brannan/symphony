#!/usr/bin/env bash
# Appends one line per Bash call containing "ssh " to
# intermediate_files/claude_slop/host-commands.log: ISO timestamp, session
# id, the command. Local buffer for the as-built file, never committed --
# see .gitignore.
#
# Redacts before writing, case-insensitively: a command matching sops -d,
# sudo -S, Authorization, psk=, token, password, sshpass -p, or containing a
# heredoc (<<) is logged as "[redacted: <pattern>]" only: the match is proof
# the command can carry a secret anywhere, line 1 included, so nothing of it
# is kept. Everything else is logged verbatim. Matching is pipe-free (bash
# pattern match): under pipefail, `printf | grep -q` can die by SIGPIPE on a
# very long command and silently skip the redaction.
#
# Fires on PostToolUse for Bash. Must exit 0 on every path -- a missing log
# directory or unwritable file never blocks a tool call -- so every step
# after reading stdin is best-effort.
set -uo pipefail

input=$(cat) || exit 0
tool=$(printf '%s' "$input" | jq -r '.tool_name // ""' 2>/dev/null) || exit 0
[ "$tool" = "Bash" ] || exit 0

cmd=$(printf '%s' "$input" | jq -r '.tool_input.command // ""' 2>/dev/null) || exit 0
[[ ${cmd,,} == *"ssh "* ]] || exit 0

cwd=$(printf '%s' "$input" | jq -r '.cwd // ""' 2>/dev/null)
sid=$(printf '%s' "$input" | jq -r '.session_id // ""' 2>/dev/null)

root=$(cd "${cwd:-.}" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null)
[ -n "$root" ] || root="${cwd:-.}"

# Order matters only for which pattern name gets reported when several
# match -- the redaction itself is the same regardless.
redact_pattern=""
for p in 'sops -d' 'sudo -S' 'Authorization' 'psk=' 'token' 'password' 'sshpass -p' '<<'; do
  if [[ ${cmd,,} == *"${p,,}"* ]]; then
    if [ "$p" = '<<' ]; then redact_pattern="heredoc (<<)"; else redact_pattern="$p"; fi
    break
  fi
done

if [ -n "$redact_pattern" ]; then
  line_cmd="[redacted: ${redact_pattern}]"
else
  line_cmd="$cmd"
fi

log_dir="$root/intermediate_files/claude_slop"
mkdir -p "$log_dir" 2>/dev/null || exit 0

ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
printf '%s\t%s\t%s\n' "$ts" "$sid" "$line_cmd" >> "$log_dir/host-commands.log" 2>/dev/null

exit 0
