#!/bin/sh
# Integration test for signalk-plugin-watchdog against a real signalk-server.
#
# Needs a directory with signalk-server installed (npm install signalk-server),
# passed as $1. Builds a throwaway config dir, links the watchdog and the two
# fixtures into it, and runs three phases:
#
#   1. Fresh state. mute-plugin (in expectPlugins) never publishes ->
#      the watchdog must ALERT after the grace period. flaky-plugin publishes
#      normally -> no alert, and it must get learned into known-producers.json.
#   2. Server restarted with flaky-plugin muted from startup -- the actual
#      bt-sensors incident shape. flaky-plugin is NOT in expectPlugins, so
#      only the learned expectation from phase 1 can catch it -> must ALERT.
#   3. Un-mute flaky-plugin while the server runs -> alarm must clear to
#      "normal" (recovery path).
#
# The failure path is asserted positively in phases 1 and 2: a watchdog that
# never fires looks exactly like a watchdog with nothing to do.
set -eu

SK_DIR=${1:?usage: run-test.sh /dir/containing/node_modules/signalk-server}
HERE=$(cd "$(dirname "$0")" && pwd)
PLUGIN_DIR=$(dirname "$HERE")
WORK=$(mktemp -d)
CONFIG="$WORK/config"
PORT=3999
API="http://localhost:$PORT/signalk/v1/api"
export FLAKY_MUTE_MARKER="$WORK/mute-marker"

SERVER_PID=""
cleanup() {
	[ -n "$SERVER_PID" ] && kill "$SERVER_PID" 2>/dev/null || true
	rm -rf "$WORK"
}
trap cleanup EXIT

fail() {
	echo "FAIL: $1" >&2
	echo "--- last server log ---" >&2
	tail -30 "$WORK/server.log" >&2 || true
	exit 1
}

mkdir -p "$CONFIG/node_modules" "$CONFIG/plugin-config-data"
ln -s "$PLUGIN_DIR" "$CONFIG/node_modules/signalk-plugin-watchdog"
ln -s "$HERE/fixtures/mute-plugin" "$CONFIG/node_modules/mute-plugin"
ln -s "$HERE/fixtures/flaky-plugin" "$CONFIG/node_modules/flaky-plugin"

cat >"$CONFIG/settings.json" <<EOF
{
  "interfaces": {},
  "ssl": false,
  "pipedProviders": []
}
EOF
cat >"$CONFIG/plugin-config-data/plugin-watchdog.json" <<EOF
{
  "enabled": true,
  "configuration": {
    "checkIntervalSeconds": 5,
    "graceSeconds": 15,
    "stallSeconds": 20,
    "expectPlugins": ["mute-plugin"]
  }
}
EOF
echo '{"enabled": true, "configuration": {}}' >"$CONFIG/plugin-config-data/mute-plugin.json"
echo '{"enabled": true, "configuration": {}}' >"$CONFIG/plugin-config-data/flaky-plugin.json"

start_server() {
	node "$SK_DIR/node_modules/signalk-server/bin/signalk-server" -c "$CONFIG" \
		>"$WORK/server.log" 2>&1 &
	SERVER_PID=$!
	i=0
	until curl -sf "$API/vessels/self" >/dev/null 2>&1; do
		i=$((i + 1))
		[ "$i" -le 30 ] || fail "server did not come up"
		kill -0 "$SERVER_PID" 2>/dev/null || fail "server exited during startup"
		sleep 1
	done
}

stop_server() {
	kill "$SERVER_PID" 2>/dev/null || true
	wait "$SERVER_PID" 2>/dev/null || true
	SERVER_PID=""
}

# jq-free JSON probe: prints the notification state for a plugin id, or "absent".
notif_state() {
	curl -sf "$API/vessels/self/notifications/pluginWatchdog/$1/value" 2>/dev/null |
		python3 -c 'import json,sys
try:
    print(json.load(sys.stdin).get("state", "absent"))
except Exception:
    print("absent")' 2>/dev/null || echo absent
}

wait_state() {
	want=$2
	i=0
	while [ "$(notif_state "$1")" != "$want" ]; do
		i=$((i + 1))
		[ "$i" -le 40 ] || fail "$1 never reached state '$want' (got '$(notif_state "$1")')"
		sleep 2
	done
}

export SIGNALK_NODE_VERSION_CHECK_DISABLE=1 SIGNALK_DISABLE_SERVER_UPDATES=1
export PORT

echo "phase 1: mute-from-startup on an expected plugin must alert"
start_server
wait_state mute-plugin alert
echo "  ok: mute-plugin -> alert"
[ "$(notif_state flaky-plugin)" = "absent" ] ||
	fail "flaky-plugin (healthy) has a notification but should not"
echo "  ok: flaky-plugin (healthy) -> no notification"
grep -q flaky-plugin "$CONFIG/plugin-config-data/plugin-watchdog/known-producers.json" ||
	fail "flaky-plugin was not learned into known-producers.json"
echo "  ok: flaky-plugin learned as a producer"
stop_server

echo "phase 2: learned producer mute from startup after restart must alert"
touch "$FLAKY_MUTE_MARKER"
start_server
wait_state flaky-plugin alert
echo "  ok: flaky-plugin -> alert (caught via learned expectation)"

echo "phase 3: recovery must clear the alarm"
rm -f "$FLAKY_MUTE_MARKER"
wait_state flaky-plugin normal
echo "  ok: flaky-plugin -> normal after publishing resumed"
stop_server

echo "PASS: all phases"
