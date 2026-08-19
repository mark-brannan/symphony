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

# Explicit, session-unique LocalAPI socket so tailscaled, `tailscale up`,
# and the SSH ProxyCommand below all talk to the same daemon instead of
# racing over whichever default path each of them resolves as non-root.
SOCKET="${HOME}/.tailscale-cloud.sock"

is_joined() {
  tailscale --socket="$SOCKET" status --json 2>/dev/null | grep -q '"BackendState": *"Running"'
}

# LocalAPI availability on our own socket, not `pgrep -x tailscaled` (which
# can match an unrelated system daemon that doesn't serve $SOCKET at all,
# in which case `tailscale up` below would just fail against it).
daemon_reachable() {
  # --json, not text mode: text `status` exits 1 for NeedsLogin/
  # NeedsMachineAuth even when the LocalAPI itself is reachable, which
  # would make this false-negative into starting a second daemon.
  tailscale --socket="$SOCKET" status --json >/dev/null 2>&1
}

if is_joined; then
  exit 0  # already joined and authenticated (e.g. hook re-run on resume)
fi

# CLAUDE_CODE_REMOTE_SESSION_ID contains underscores (e.g. "cse_01AB..."),
# which aren't valid in a DNS label; tailscale rejects the hostname outright
# if we don't strip them first.
SESSION_HOSTNAME="cloud-${CLAUDE_CODE_REMOTE_SESSION_ID:-$$}"
SESSION_HOSTNAME="${SESSION_HOSTNAME//_/-}"
SESSION_HOSTNAME="${SESSION_HOSTNAME:0:32}"
SESSION_HOSTNAME="${SESSION_HOSTNAME%-}"  # a DNS label can't end in a hyphen; the 32-char cut can land right after one

if ! daemon_reachable; then
  LOG_FILE="$(mktemp "${TMPDIR:-/tmp}/tailscaled.XXXXXX.log")" || {
    echo "tailscale-join: cannot create daemon log file" >&2
    exit 0
  }

  # --socks5-server/--outbound-http-proxy-listen give other tooling in the
  # session a way to route through the tailnet via ALL_PROXY/HTTP_PROXY;
  # nothing in this hook sets those env vars today, only the SSH
  # ProxyCommand below consumes the tailnet. Left running for future use.
  tailscaled \
    --tun=userspace-networking \
    --socket="$SOCKET" \
    --socks5-server=localhost:1055 \
    --outbound-http-proxy-listen=localhost:1055 \
    --state=mem: \
    >"$LOG_FILE" 2>&1 &
  disown

  sleep 2
else
  LOG_FILE="the running tailscaled's own log (daemon was already running)"
fi

# Write the auth key to a private tempfile and pass it via --auth-key=file:…
# instead of --authkey=… on the command line, so it doesn't show up in
# `ps`/process-argument listings for other local users.
AUTHKEY_FILE="$(mktemp "${TMPDIR:-/tmp}/tailscale-authkey.XXXXXX")" || {
  echo "tailscale-join: cannot create auth key tempfile" >&2
  exit 0
}
trap 'rm -f "$AUTHKEY_FILE"' EXIT
chmod 600 "$AUTHKEY_FILE"
printf '%s' "$TAILSCALE_AUTHKEY" > "$AUTHKEY_FILE"
unset TAILSCALE_AUTHKEY

if ! tailscale --socket="$SOCKET" up \
  --auth-key="file:$AUTHKEY_FILE" \
  --hostname="$SESSION_HOSTNAME" \
  --ssh=false \
  --accept-routes=false \
  --timeout=30s; then
  echo "tailscale-join: 'tailscale up' failed, see $LOG_FILE" >&2
  exit 0
fi

if ! mkdir -p "$HOME/.ssh"; then
  echo "tailscale-join: cannot create $HOME/.ssh" >&2
  exit 0
fi

if ! grep -q "^Host symphony-pi macbook-air nucboxk12$" "$HOME/.ssh/config" 2>/dev/null; then
  if ! cat >> "$HOME/.ssh/config" <<EOF

Host symphony-pi macbook-air nucboxk12
  ProxyCommand tailscale --socket=$SOCKET nc %h %p
  StrictHostKeyChecking accept-new
EOF
  then
    echo "tailscale-join: cannot update $HOME/.ssh/config" >&2
    exit 0
  fi
fi

echo "tailscale-join: joined tailnet as $SESSION_HOSTNAME" >&2
