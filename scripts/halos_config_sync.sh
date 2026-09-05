#!/usr/bin/env bash
# Copy the boat's SignalK config onto the HALOS card, keeping the card's own
# settings. Relayed through this box (rsync boat -> temp -> card): a
# provisioned card is tagged symphony-devices and Tailscale policy refuses
# its ssh straight to symphony-pi. Run from a tailnet machine with sops
# access; needs ssh to symphony-halos and symphony-pi.
#
#   scripts/halos_config_sync.sh
#
set -euo pipefail
cd "$(dirname "$0")/.."

D=/var/lib/container-apps/marine-signalk-server-container/data/data
STAGE="${TMPDIR:-/tmp}/halos-config-sync-$$"
PW=$(sops --decrypt --extract '["symphony_halos_pi_password"]' secrets/symphony.sops.yaml)

# Build artifacts and machine state: never copy these, whichever card they
# came from -- they're per-install, not config.
GENERIC_EXCLUDES=(
  node_modules package.json appstore-cache signalk-server
  'skserver-raw_*' '*.bak*' '*.deb' 'ssl-*.pem' '*.sqlite*'
)

# EXPECT / CONFIG_EXPECT: the card's own settings, shared with
# halos_preflight.sh so the two can't disagree about which files these are.
. scripts/halos_disabled_plugins.sh

trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE"

generic_args=()
for e in "${GENERIC_EXCLUDES[@]}"; do generic_args+=(--exclude "$e"); done

rsync -a "${generic_args[@]}" pi@symphony-pi:.signalk/ "$STAGE/"

config_args=()
for f in $(echo "$CONFIG_EXPECT" | tr '|' '\n'); do
  config_args+=(--exclude "plugin-config-data/$f")
done

rsync -a "${generic_args[@]}" "${config_args[@]}" "$STAGE/" "pi@symphony-halos:$D/" \
  || { echo "halos_config_sync: rsync failed; not restarting SignalK" >&2; exit 1; }
printf '%s\n' "$PW" | ssh pi@symphony-halos "sudo -S -p '' systemctl restart marine-signalk-server-container"
