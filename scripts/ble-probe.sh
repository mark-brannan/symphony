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
# empty on those. `poll` subscribes first and then writes a payload, because
# the response can beat the subscription if you write first. Payload is a
# plain hex string, e.g. dda50300fffd77.
#
# `poll` talks to BlueZ over D-Bus rather than driving bluetoothctl, because
# bluetoothctl's `write` never gets a reply out of a JBD pack -- see the
# comment on cmd_poll. `scan`, `gatt` and `notify` are still bluetoothctl.
#
# Both of Symphony's house batteries advertise the same name AND expose the
# same ff00/ff01/ff02 UUIDs, so anything that selects a characteristic by
# UUID alone can silently act on the wrong pack. `poll` and `notify` resolve
# the UUID to an object path underneath the MAC you named. Always identify a
# pack by MAC; the advertised name cannot tell them apart.
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

# Two log formats to count. `poll` writes its own "Notification: <hex>"
# lines. `notify` shells out to bluetoothctl, which instead reports an
# incoming value as
#   [CHG] Attribute /org/bluez/hci0/dev_.../char0010 Value:
# followed by an indented hex line -- it never prints the word
# "Notification", so counting only that finds nothing even on a good capture.
# The noisy "ManufacturerData Value:" lines from passive scanning don't match
# either pattern.
report_frames() {
  local log="$1"
  echo "captured $(grep -cE '^Notification:|Attribute .*Value' "$log") notifications" >&2
  echo "frames: $log" >&2
}

dev_key() {
  printf 'dev_%s' "$(printf '%s' "$1" | tr ':' '_' | tr '[:lower:]' '[:upper:]')"
}

# BlueZ drops an unpaired device from D-Bus not long after it disconnects, so
# a probe that worked ten minutes ago can fail with "device not known" purely
# because nothing has scanned since. Re-advertise it before giving up.
ensure_known() {
  local mac="$1"
  if busctl --system tree org.bluez 2>/dev/null \
     | grep -q "/$(dev_key "$mac")\$"; then
    return 0
  fi
  echo "device not in BlueZ, scanning ..." >&2
  bluetoothctl --timeout 15 scan on >/dev/null 2>&1
}

# `select-attribute <uuid>` matches the first characteristic with that UUID
# across EVERY connected device, not just the one you named. Symphony's two
# house batteries expose identical ff00/ff01/ff02 UUIDs, so a UUID selection
# silently lands on whichever BlueZ enumerated first -- you ask to poll one
# battery and the log shows a write to the other one's object path. Resolve
# the UUID against this device's own path and select by path instead.
#
# The GATT tree only exists in D-Bus once the device is connected and its
# services are resolved, so this has to run after connect.
attr_path() {
  local mac="$1" uuid="$2" want p u
  case "$uuid" in
    ????) want="0000${uuid}-0000-1000-8000-00805f9b34fb" ;;
    *)    want="$uuid" ;;
  esac
  want="$(printf '%s' "$want" | tr '[:upper:]' '[:lower:]')"
  for p in $(busctl --system tree org.bluez 2>/dev/null \
             | grep -oE "/org/bluez/hci[0-9]+/$(dev_key "$mac")/service[0-9a-f]+/char[0-9a-f]+"); do
    u="$(busctl --system get-property org.bluez "$p" \
         org.bluez.GattCharacteristic1 UUID 2>/dev/null \
         | tr -d 's" ' | tr '[:upper:]' '[:lower:]')"
    if [ "$u" = "$want" ]; then printf '%s' "$p"; return 0; fi
  done
  echo "could not resolve $uuid on $mac -- is it connected?" >&2
  return 1
}

# attr_path needs a resolved GATT tree, so bring the link up first. A
# separate connect is harmless when the device is already up.
ensure_connected() {
  local mac="$1"
  if busctl --system get-property org.bluez \
       "/org/bluez/hci0/$(dev_key "$mac")" org.bluez.Device1 ServicesResolved \
       2>/dev/null | grep -q true; then
    return 0
  fi
  drive "connect $mac" 12 | bluetoothctl >/dev/null 2>&1
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
  need busctl
  local path
  ensure_known "$mac"
  ensure_connected "$mac"
  path="$(attr_path "$mac" "$uuid")" || exit 1
  echo "notify: $path" >&2
  # Frames land in the log as "[CHG] Attribute ... Value:" lines followed by
  # an indented hex line. Those are the fixture data -- a class written
  # against them can be unit tested without the battery present.
  drive \
    "connect $mac" 10 \
    "menu gatt" 1 \
    "select-attribute $path" 2 \
    "notify on" "$secs" \
    "notify off" 2 \
    "back" 1 \
    "disconnect $mac" 3 \
    | bluetoothctl 2>&1 | tee "$log"
  report_frames "$log"
}

cmd_poll() {
  local mac="${1:?usage: ble-probe.sh poll <MAC> <write-char-uuid> <hex-payload> <notify-char-uuid> [seconds]}"
  local write_uuid="${2:?usage: ble-probe.sh poll <MAC> <write-char-uuid> <hex-payload> <notify-char-uuid> [seconds]}"
  local payload="${3:?usage: ble-probe.sh poll <MAC> <write-char-uuid> <hex-payload> <notify-char-uuid> [seconds]}"
  local notify_uuid="${4:?usage: ble-probe.sh poll <MAC> <write-char-uuid> <hex-payload> <notify-char-uuid> [seconds]}"
  local secs="${5:-30}"
  local log="${out_dir}/ble-poll-${mac//:/}-${stamp}.log"
  need python3
  need busctl
  ensure_known "$mac"
  # Deliberately not bluetoothctl. Its `write` never elicits a reply from a
  # JBD pack no matter how the payload is quoted or typed -- the write is
  # dispatched with no error and the BMS simply never answers -- while the
  # same bytes sent as a D-Bus WriteValue with type=command get a frame back
  # every time. `select-attribute <uuid>` is also ambiguous when two packs
  # expose identical UUIDs; going through D-Bus lets us address the
  # characteristic by its object path, under the MAC we were actually asked
  # for. See reference/software_stack.md.
  python3 - "$mac" "$write_uuid" "$payload" "$notify_uuid" "$secs" 2>&1 \
    <<'PYPOLL' | tee "$log"
import sys, time
import dbus, dbus.mainloop.glib
from gi.repository import GLib

mac, write_uuid, payload_hex, notify_uuid, secs = sys.argv[1:6]
secs = int(secs)

BLUEZ = "org.bluez"
OM = "org.freedesktop.DBus.ObjectManager"
PROPS = "org.freedesktop.DBus.Properties"
CHRC = "org.bluez.GattCharacteristic1"
DEV = "org.bluez.Device1"


def full(uuid):
    u = uuid.lower()
    return "0000%s-0000-1000-8000-00805f9b34fb" % u if len(u) == 4 else u


dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SystemBus()
om = dbus.Interface(bus.get_object(BLUEZ, "/"), OM)
key = "dev_" + mac.replace(":", "_").upper()

objs = om.GetManagedObjects()
dev_path = next((p for p in objs if p.endswith(key) and DEV in objs[p]), None)
if dev_path is None:
    sys.exit("device %s not known to BlueZ -- run `ble-probe.sh scan` first" % mac)

dev = dbus.Interface(bus.get_object(BLUEZ, dev_path), DEV)
devp = dbus.Interface(bus.get_object(BLUEZ, dev_path), PROPS)
print("device: %s" % dev_path)

if not devp.Get(DEV, "Connected"):
    dev.Connect()
for _ in range(40):
    if devp.Get(DEV, "ServicesResolved"):
        break
    time.sleep(0.5)
if not devp.Get(DEV, "ServicesResolved"):
    sys.exit("services never resolved on %s" % mac)

# Restricted to this device's own object path, so two packs advertising the
# same name and the same UUIDs stay distinguishable.
chars = {}
for path, ifaces in om.GetManagedObjects().items():
    if CHRC in ifaces and path.startswith(dev_path):
        chars[str(ifaces[CHRC]["UUID"]).lower()] = path

for want, label in ((notify_uuid, "notify"), (write_uuid, "write")):
    if full(want) not in chars:
        sys.exit("%s characteristic %s not on %s" % (label, want, mac))
notify_path, write_path = chars[full(notify_uuid)], chars[full(write_uuid)]
print("notify: %s" % notify_path)
print("write : %s" % write_path)


def on_props(iface, changed, invalidated, path=None):
    if "Value" in changed:
        print("Notification: %s"
              % bytes(bytearray(changed["Value"])).hex(" "), flush=True)


bus.add_signal_receiver(on_props, dbus_interface=PROPS,
                        signal_name="PropertiesChanged", path=notify_path)

nif = dbus.Interface(bus.get_object(BLUEZ, notify_path), CHRC)
wif = dbus.Interface(bus.get_object(BLUEZ, write_path), CHRC)

# Subscribe before writing: the reply can beat StartNotify otherwise.
nif.StartNotify()
time.sleep(1.0)

payload = bytes.fromhex(payload_hex)
print("wrote: %s" % payload.hex(" "))
wif.WriteValue(dbus.Array([dbus.Byte(b) for b in payload], signature="y"),
               dbus.Dictionary({"type": "command"}, signature="sv"))

loop = GLib.MainLoop()
GLib.timeout_add_seconds(secs, lambda: (loop.quit(), False)[1])
loop.run()
try:
    nif.StopNotify()
except Exception:
    pass
PYPOLL
  report_frames "$log"
}

case "${1:-}" in
  scan)   shift; cmd_scan "$@" ;;
  gatt)   shift; cmd_gatt "$@" ;;
  notify) shift; cmd_notify "$@" ;;
  poll)   shift; cmd_poll "$@" ;;
  *) sed -n '/^# Usage:/,/^# Typical/p' "$0" >&2; exit 1 ;;
esac
