#!/usr/bin/env bash
# Copy the boat's SignalK config onto the HALOS card, keeping the card's own
# settings. Run from a tailnet machine; needs ssh to symphony-halos and
# symphony-pi.
#
#   scripts/halos_config_sync.sh
#
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

D=/var/lib/container-apps/marine-signalk-server-container/data/data

# Build artifacts and machine state: never copy these, whichever card they
# came from -- they're per-install, not config.
GENERIC_EXCLUDES=(
  node_modules package.json appstore-cache signalk-server
  'skserver-raw_*' '*.bak*' '*.deb' 'ssl-*.pem' '*.sqlite*'
)

# EXPECT / CONFIG_EXPECT: the card's own settings, shared with
# halos_preflight.sh so the two can't disagree about which files these are.
. scripts/halos_disabled_plugins.sh

args=()
for e in "${GENERIC_EXCLUDES[@]}"; do args+=(--exclude "$e"); done
for f in $(echo "$CONFIG_EXPECT" | tr '|' '\n'); do
  args+=(--exclude "plugin-config-data/$f")
done

remote_excludes=$(printf '%q ' "${args[@]}")
# shellcheck disable=SC2029  # client-side expansion is the point: the excludes are built here
ssh pi@symphony-halos "rsync -av $remote_excludes pi@symphony-pi:.signalk/ $D/" \
  || { echo "halos_config_sync: rsync failed; not restarting SignalK" >&2; exit 1; }
ssh pi@symphony-halos 'sudo systemctl restart marine-signalk-server-container'
