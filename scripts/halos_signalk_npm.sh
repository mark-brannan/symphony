#!/usr/bin/env bash
# Build SignalK's plugin tree for the HALOS container, on the HALOS card.
#
#   sudo scripts/halos_signalk_npm.sh            install from package.json, then rebuild natives
#   sudo scripts/halos_signalk_npm.sh rebuild    rebuild the native modules only
#
# Safe to run over ssh: the work re-execs itself into a transient systemd unit
# (journal, not your terminal) and this process only follows it. Losing the
# connection loses the follower, never the build. Ctrl-C does the same -- to
# actually abort, `sudo systemctl stop halos-npm`, which still restarts SignalK.
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
SELF_UNIT=halos-npm

[ "$(id -u)" -eq 0 ] || { echo "run with sudo" >&2; exit 1; }

# Detach before doing anything. A 20-minute npm run tied to an ssh session is a
# torn node_modules and a stopped SignalK the moment the link drops: bash takes
# EPIPE on its next echo, `set -e` aborts mid-install, and an OOM kill skips the
# trap below entirely. So the real run happens in a transient unit, this process
# degrades to a log follower, and ExecStopPost restarts SignalK when the trap
# could not. systemd sets INVOCATION_ID inside the unit, which is how the
# re-exec knows not to recurse.
#
# ExecStopPost covers the main process dying (OOM, crash, `systemctl stop`);
# measured 2026-09-03, SignalK came back on its own. Recovery is not instant --
# systemd waits for the npm container, which outlives the script because it runs
# in dockerd's cgroup, so allow it a minute before concluding it failed. It does
# NOT cover `systemctl kill`, which SIGKILLs the whole cgroup including the
# control process; that left SignalK down. To abort a run by hand use
# `systemctl stop halos-npm`, never `systemctl kill`.
if [ -z "${INVOCATION_ID:-}" ]; then
  systemctl is-active --quiet "$SELF_UNIT" && { echo "$SELF_UNIT already running; follow it with: journalctl -u $SELF_UNIT -f" >&2; exit 1; }
  systemctl reset-failed "$SELF_UNIT" 2>/dev/null || true
  started=$(date '+%Y-%m-%d %H:%M:%S')
  systemd-run --unit "$SELF_UNIT" --quiet \
    --property=ExecStopPost="/usr/bin/systemctl start $UNIT" \
    "$(readlink -f "$0")" "$MODE"
  echo "== started as $SELF_UNIT ($(date +%H:%M:%S)); following the journal -- safe to disconnect"
  journalctl -u "$SELF_UNIT" -f -n 0 --no-pager &
  follower=$!
  trap 'kill $follower 2>/dev/null' EXIT
  while systemctl is-active --quiet "$SELF_UNIT"; do sleep 5; done
  sleep 1; kill $follower 2>/dev/null; trap - EXIT
  # Read the outcome from the journal, not from `systemctl show`: a transient
  # unit is garbage-collected once it goes inactive, and `show` on a unit that
  # no longer exists answers Result=success for a run that was killed -- i.e.
  # the one case the caller most needs to hear about (measured 2026-09-03).
  # The journal lines outlive the unit.
  outcome=$(journalctl -u "$SELF_UNIT" --since "$started" --no-pager -o cat 2>/dev/null \
    | grep -oE "Failed with result '[a-z-]+'|Main process exited, code=[a-z]+, status=[0-9]+[^ ]*" | tail -1 || true)
  # `|| true` is load-bearing: under `set -o pipefail` a grep that correctly
  # matches nothing (the clean run) exits 1 and takes the whole script with it.
  systemctl reset-failed "$SELF_UNIT" 2>/dev/null || true
  case "$outcome" in
    "") echo "== $SELF_UNIT finished; no failure recorded in the journal" ;;
    *"Failed with result"*|*status=[1-9]*)
        echo "== $SELF_UNIT ended badly: $outcome -- journalctl -u $SELF_UNIT" >&2; exit 1 ;;
    *)  echo "== $SELF_UNIT finished clean" ;;
  esac
  exit 0
fi
[ -f "$D/package.json" ] || { echo "no $D/package.json" >&2; exit 1; }
grep -q package-lock=false "$D/.npmrc" 2>/dev/null || echo "package-lock=false" >> "$D/.npmrc"
chown 1000:1000 "$D/.npmrc"

# SignalK must be down: npm rewrites node_modules under it, and on a 2 GB card
# the two do not fit together. It comes back at the end whatever happens.
was_active=$(systemctl is-active "$UNIT" || true)
systemctl stop "$UNIT"
trap 'systemctl start "$UNIT" || true' EXIT INT TERM HUP

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

# The forks are `file:local-plugins/...` deps, so npm hoists their dependencies
# to the top level -- and prunes them again the next time the top-level
# package.json comes across from the boat without them. That is not a visible
# failure: bt-sensors-plugin-sk lost @naugehyde/node-ble this way on 2026-09-04
# and SignalK simply started with one fewer plugin and no BLE. Giving each fork
# its own complete node_modules makes it immune to what the top level does.
for fork in "$D"/local-plugins/*/; do
  [ -f "$fork/package.json" ] || continue
  echo "== npm install in $(basename "$fork") ($(date +%H:%M:%S))"
  docker run --rm --network host -u 1000:1000 -e HOME=/home/node \
    -e npm_config_cache=/home/node/.signalk/.npm-cache \
    -v "$D:/home/node/.signalk" -w "/home/node/.signalk/local-plugins/$(basename "$fork")" \
    "$IMAGE" npm install --ignore-scripts --no-audit --no-fund
done

echo "== npm rebuild $NATIVES ($(date +%H:%M:%S))"
# shellcheck disable=SC2086
run rebuild $NATIVES

rm -rf "$D/.npm-cache"
echo "== done ($(date +%H:%M:%S)); unit was $was_active, starting it"
