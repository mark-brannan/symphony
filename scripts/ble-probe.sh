#!/usr/bin/env bash
# Identifies an unknown BLE device well enough to pick (or write) a
# bt-sensors-plugin-sk sensor class for it. Written for the Eco-Worthy house
# batteries, which advertise as BATT_xxxx and match no known BMS matcher --
# the advertised name tells you nothing, the GATT service UUID tells you
# everything:
#
#   fff0 / fff1 / fff2               -> Eco-Worthy BW02 family
#   ff00 / ff01 / ff02               -> JBD family
#   00000001-0000-1000-8000-...      -> HumsiENK HSC14F
#   6e400001-b5a3-f393-e0a9-...      -> Nordic UART (E&J and friends)
#
# Run this on the Pi itself, NOT inside the signalk container -- BlueZ lives
# on the host and the container may not even have a route to D-Bus.
#
# The radio does not multiplex: if bt-sensors-plugin-sk is holding GATT
# connections it will fight this script for the adapter. Stop the signalk
# container first, or expect flaky results.
#
# Usage:
#   ble-probe.sh scan [seconds]
#   ble-probe.sh gatt <MAC>
#   ble-probe.sh notify <MAC> <char-uuid> [seconds]
#   ble-probe.sh poll <MAC> <write-char-uuid> <hex-payload> <notify-char-uuid> [seconds]
#
# Typical run: scan to confirm the advertised name, gatt to get the service
# and characteristic UUIDs, then notify against the characteristic that has
# the notify flag to capture raw frames. Some BMS families (JBD/ff00, for
# one) are request/response, not push -- they never notify until a command
# is written to their write characteristic, so `notify` alone comes back
# empty on those. `poll` writes a payload first, then listens like `notify`
# does. Payload is a plain hex string, e.g. dda50300fffd77. The write is
# sent as `command` (write-without-response) -- BlueZ's default write type
# is `request` (write-with-response), and JBD-family write chars answer a
# request-type write with org.bluez.Error.NotSupported since they only
# advertise the write-without-response property.
set -uo pipefail

# Kept out of /tmp deliberately: these logs are the fixture data a sensor
# class gets written and unit tested against, so they need to survive a
# reboot and be worth syncing somewhere durable.
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
out_dir="${BLE_PROBE_OUT:-$SCRIPT_DIR/data}"
mkdir -p "$out_dir" || exit 1
stamp="$(date -u +%Y%m%dT%H%M%SZ)"

need() {
  command -v "$1" >/dev/null 2>&1 || { echo "missing: $1" >&2; exit 1; }
}

# bluetoothctl's gatt `write` takes space-separated 0x-prefixed bytes, not a
# bare hex string -- `dda503...` has to become `0xdd 0xa5 0x03 ...`.
hex_to_btctl() {
  local hex="$1"
  if [ $(( ${#hex} % 2 )) -ne 0 ]; then
    echo "odd-length hex payload: $hex" >&2
    return 1
  fi
  local out="" i
  for (( i=0; i<${#hex}; i+=2 )); do
    out+="0x${hex:i:2} "
  done
  printf '%s' "${out% }"
}

# bluetoothctl is a REPL, not a batch tool. Feeding it a heredoc races --
# it reads every line before the adapter has finished the previous command.
# Interleaving sleeps on stdin is the standard way to pace it.
drive() {
  local delay
  while [ $# -gt 0 ]; do
    printf '%s\n' "$1"
    delay="$2"
    sleep "$delay"
    shift 2
  done
  printf 'quit\n'
}

cmd_scan() {
  local secs="${1:-30}" log="${out_dir}/ble-scan-${stamp}.log"
  need bluetoothctl
  echo "scanning ${secs}s ..." >&2
  bluetoothctl --timeout "$secs" scan on >"$log" 2>&1
  echo "--- devices seen ---"
  bluetoothctl devices | tee -a "$log"
  echo "full scan log: $log" >&2
}

cmd_gatt() {
  local mac="${1:?usage: ble-probe.sh gatt <MAC>}"
  local log="${out_dir}/ble-gatt-${mac//:/}-${stamp}.log"
  need bluetoothctl
  # info before connect captures the advertised name, manufacturer data and
  # any service UUIDs exposed in the advertisement itself.
  bluetoothctl info "$mac" 2>&1 | tee "$log"
  drive \
    "connect $mac" 10 \
    "menu gatt" 1 \
    "list-attributes $mac" 8 \
    "back" 1 \
    "disconnect $mac" 3 \
    | bluetoothctl 2>&1 | tee -a "$log"
  echo "gatt dump: $log" >&2
}

cmd_notify() {
  local mac="${1:?usage: ble-probe.sh notify <MAC> <char-uuid> [seconds]}"
  local uuid="${2:?usage: ble-probe.sh notify <MAC> <char-uuid> [seconds]}"
  local secs="${3:-60}"
  local log="${out_dir}/ble-notify-${mac//:/}-${stamp}.log"
  need bluetoothctl
  # Frames land in the log as "Notification: xx xx xx ..." lines. Those are
  # the fixture data -- a class written against them can be unit tested
  # without the battery present.
  drive \
    "connect $mac" 10 \
    "menu gatt" 1 \
    "select-attribute $uuid" 2 \
    "notify on" "$secs" \
    "notify off" 2 \
    "back" 1 \
    "disconnect $mac" 3 \
    | bluetoothctl 2>&1 | tee "$log"
  echo "captured $(grep -c '^Notification' "$log") notifications" >&2
  echo "frames: $log" >&2
}

cmd_poll() {
  local mac="${1:?usage: ble-probe.sh poll <MAC> <write-char-uuid> <hex-payload> <notify-char-uuid> [seconds]}"
  local write_uuid="${2:?usage: ble-probe.sh poll <MAC> <write-char-uuid> <hex-payload> <notify-char-uuid> [seconds]}"
  local payload="${3:?usage: ble-probe.sh poll <MAC> <write-char-uuid> <hex-payload> <notify-char-uuid> [seconds]}"
  local notify_uuid="${4:?usage: ble-probe.sh poll <MAC> <write-char-uuid> <hex-payload> <notify-char-uuid> [seconds]}"
  local secs="${5:-30}"
  local log="${out_dir}/ble-poll-${mac//:/}-${stamp}.log"
  need bluetoothctl
  local bytes
  bytes="$(hex_to_btctl "$payload")" || exit 1
  drive \
    "connect $mac" 10 \
    "menu gatt" 1 \
    "select-attribute $write_uuid" 2 \
    "write $bytes 0 command" 2 \
    "select-attribute $notify_uuid" 2 \
    "notify on" "$secs" \
    "notify off" 2 \
    "back" 1 \
    "disconnect $mac" 3 \
    | bluetoothctl 2>&1 | tee "$log"
  echo "captured $(grep -c '^Notification' "$log") notifications" >&2
  echo "frames: $log" >&2
}

case "${1:-}" in
  scan)   shift; cmd_scan "$@" ;;
  gatt)   shift; cmd_gatt "$@" ;;
  notify) shift; cmd_notify "$@" ;;
  poll)   shift; cmd_poll "$@" ;;
  *) sed -n '/^# Usage:/,/^# Typical/p' "$0" >&2; exit 1 ;;
esac
