#!/usr/bin/env bash
# First-pass triage of a boat-down issue: gather read-only diagnostics over the
# tailnet into diagnostics.txt, classify them by rule, and post a short verdict
# on the issue. The agent step runs after this and writes the deeper analysis.
#
# Usage: scripts/boat_triage.sh <host> <issue> <since>   (needs GH_TOKEN, tailscale up)
set -uo pipefail

host="${1:?host}" issue="${2:?issue}" since="${3:-}"
[[ "$host" =~ ^symphony-[a-z0-9-]+$ && "$issue" =~ ^[0-9]+$ ]] || { echo "bad input" >&2; exit 1; }
[[ "$since" =~ ^[0-9T:+.Z-]+$ ]] || since=-24h
out=diagnostics.txt

{
  echo "## tailscale status"; tailscale status 2>&1 | grep -E "$host|^#" || true
  echo "## tailscale ping"; timeout 30 tailscale ping -c 3 "$host" 2>&1 || true
  echo "## on host"
  timeout 120 ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 "pi@$host" \
    "uptime; systemctl --failed --no-pager; free -m; df -h /; \
     echo \"timer: \$(systemctl is-active boat-heartbeat.timer)\"; echo \"service: \$(systemctl is-failed boat-heartbeat.service)\"; \
     journalctl -t boat-heartbeat --no-pager --since '$since' | tail -n 60; \
     curl -sS -o /dev/null -w 'healthchecks.io HTTP %{http_code}\n' https://hc-ping.com" 2>&1
  rc=$?; if [ "$rc" -eq 255 ] || [ "$rc" -eq 124 ]; then echo "ssh failed: exit $rc"; fi
} > "$out"

# First matching rule wins; each states the cause and the next human step.
if grep -q '^ssh failed' "$out"; then
  if grep -q 'pong from' "$out"; then
    verdict="Tailnet ping answers but ssh fails: the host is up, sshd or its policy is the problem. Check the Tailscale ACL, then console access."
  else
    verdict="Host does not answer on the tailnet: power, network uplink or tailscaled is down. Check the boat's shore power and uplink; nothing remote can fix this."
  fi
elif grep -qE 'healthchecks.io HTTP (000|[^2])' "$out"; then
  verdict="Host is up but cannot reach healthchecks.io: the uplink or DNS is out. Check the router/cellular link."
elif grep -qE '^timer: (inactive|failed|unknown)|^service: failed' "$out"; then
  verdict="Host is up but the heartbeat timer/service is not running. Restart it: systemctl restart boat-heartbeat.timer."
elif awk '/^Mem:/ {exit !($7 < 400)}' "$out"; then
  verdict="Host is up but available memory is under 400 MB: pressure may be starving the heartbeat. Stop InfluxDB/Grafana per CLAUDE.md."
elif grep -qE '[1-9][0-9]* loaded units listed' "$out"; then
  verdict="Host is up and heartbeat looks fine, but other units have failed. Run systemctl --failed on the host."
else
  verdict="Host is up and the heartbeat path looks healthy now; the outage may already have cleared. Check whether the healthchecks.io check recovered."
fi

body="🤖 Rule-based first pass (run ${GITHUB_RUN_ID:-local}): $verdict A deeper agent triage follows if it succeeds."
gh issue comment "$issue" --body "$body" || echo "verdict comment failed"
