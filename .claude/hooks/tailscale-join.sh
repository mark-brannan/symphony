#!/usr/bin/env bash
# SessionStart hook: join the tailnet from a cloud session so Claude can
# reach symphony-pi and the dev machines over SSH.
#
# Requires the cloud environment to have:
#   - network access to tailscale.com and *.tailscale.com
#   - the tailscale package installed (via the environment's setup script)
#   - a TAILSCALE_AUTHKEY environment variable set to a reusable, ephemeral,
#     tag:cloud-ephemeral auth key
#
# No-ops (with a stderr note) when any of those aren't in place, and never
# blocks session startup on tailnet failures.
set -uo pipefail

# Only relevant in cloud sessions; local/terminal sessions already have
# tailscale via the host machine.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

if ! command -v tailscale >/dev/null 2>&1; then
  echo "tailscale-join: tailscale not installed (check the environment's setup script)" >&2
  exit 0
fi

if [ -z "${TAILSCALE_AUTHKEY:-}" ]; then
  echo "tailscale-join: TAILSCALE_AUTHKEY not set, skipping tailnet join" >&2
  exit 0
fi

if pgrep -x tailscaled >/dev/null 2>&1; then
  exit 0  # already joined (e.g. hook re-run on resume)
fi

SESSION_HOSTNAME="cloud-${CLAUDE_CODE_REMOTE_SESSION_ID:-$$}"
SESSION_HOSTNAME="${SESSION_HOSTNAME:0:32}"

tailscaled \
  --tun=userspace-networking \
  --socks5-server=localhost:1055 \
  --outbound-http-proxy-listen=localhost:1055 \
  --state=mem: \
  >/tmp/tailscaled.log 2>&1 &
disown

sleep 2

if ! tailscale up \
  --authkey="$TAILSCALE_AUTHKEY" \
  --hostname="$SESSION_HOSTNAME" \
  --ssh=false \
  --accept-routes=false \
  --timeout=30s; then
  echo "tailscale-join: 'tailscale up' failed, see /tmp/tailscaled.log" >&2
  exit 0
fi

mkdir -p ~/.ssh
if ! grep -q "^Host symphony-pi macbook-air nucboxk12$" ~/.ssh/config 2>/dev/null; then
  cat >> ~/.ssh/config <<'EOF'

Host symphony-pi macbook-air nucboxk12
  ProxyCommand tailscale nc %h %p
  StrictHostKeyChecking accept-new
EOF
fi

echo "tailscale-join: joined tailnet as $SESSION_HOSTNAME" >&2
