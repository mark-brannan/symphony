#!/usr/bin/env bash
# Build SignalK's plugin tree for the HALOS container, on the HALOS card.
#
#   sudo scripts/halos_signalk_npm.sh            install from package.json, then rebuild natives
#   sudo scripts/halos_signalk_npm.sh rebuild    rebuild the native modules only
#
# Why this exists: the HALOS SignalK image (ghcr.io/halos-org/signalk-server-
# docker) ships Node 24 and no compiler, so native plugin dependencies never
# build inside it and the plugins that need them fail silently. This runs npm
# in a throwaway node:24-bookworm container -- same Node ABI (137), full
# toolchain -- writing straight into the container's data directory, which is
# uid 1000. `docker exec` into the running server is the wrong tool: the unit
# tears its container down under memory pressure and takes the install with it.
#
# Never a bare `npm rebuild`: signalk-victron-ble's build needs python3-venv,
# fails, and aborts the run before the modules that matter. Rebuild by name.
#
# Recorded 2026-09-03 from halos-b3-findings-2026-09-02.md, which described
# the recipe but never captured the command.
set -euo pipefail

D=/var/lib/container-apps/marine-signalk-server-container/data/data
UNIT=marine-signalk-server-container
IMAGE=node:24-bookworm
NATIVES="i2c-bus epoll sqlite3 serialport lzma-native"
MODE="${1:-install}"

[ "$(id -u)" -eq 0 ] || { echo "run with sudo" >&2; exit 1; }
[ -f "$D/package.json" ] || { echo "no $D/package.json" >&2; exit 1; }
grep -q package-lock=false "$D/.npmrc" 2>/dev/null || echo "package-lock=false" >> "$D/.npmrc"
chown 1000:1000 "$D/.npmrc"

# SignalK must be down: npm rewrites node_modules under it, and on a 2 GB card
# the two do not fit together. It comes back at the end whatever happens.
was_active=$(systemctl is-active "$UNIT" || true)
systemctl stop "$UNIT"
trap 'systemctl start "$UNIT" || true' EXIT

run() { # run <npm args...>  -- as uid 1000, HOME inside the data dir, no TTY needed
  docker run --rm --network host \
    -u 1000:1000 -e HOME=/home/node -e npm_config_cache=/home/node/.signalk/.npm-cache \
    -v "$D:/home/node/.signalk" -w /home/node/.signalk \
    "$IMAGE" npm "$@"
}

docker image inspect "$IMAGE" >/dev/null 2>&1 || docker pull "$IMAGE"
echo "== node ABI in $IMAGE: $(docker run --rm "$IMAGE" node -p process.versions.modules) (HALOS image is 137)"

if [ "$MODE" = install ]; then
  echo "== npm install --ignore-scripts ($(date +%H:%M:%S))"
  run install --ignore-scripts --no-audit --no-fund
fi

echo "== npm rebuild $NATIVES ($(date +%H:%M:%S))"
# shellcheck disable=SC2086
run rebuild $NATIVES

rm -rf "$D/.npm-cache"
echo "== done ($(date +%H:%M:%S)); unit was $was_active, starting it"
