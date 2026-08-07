#!/usr/bin/env python3
"""
Cross-platform BLE probe mirroring ble-probe.sh's interface, for hosts
without bluetoothctl (macOS, or any box without BlueZ). Uses bleak, which
wraps CoreBluetooth on macOS and BlueZ on Linux behind one API -- same
script works on either.

Usage:
  ble-probe-mac.py scan [seconds]
  ble-probe-mac.py gatt <address-or-name>
  ble-probe-mac.py notify <address-or-name> <char-uuid> [seconds]
  ble-probe-mac.py poll <address-or-name> <write-char-uuid> <hex-payload> <notify-char-uuid> [seconds]

<address-or-name>: on macOS, BLE addresses are OS-assigned UUIDs, not the
real BLE MAC (Apple hides it) -- pass the advertised name instead (e.g.
"DP04S007L4S200A") and this script scans to resolve it to a connectable
address. A real address/UUID also works directly if you already have one.

Setup: pip3 install bleak
"""
import asyncio
import sys
import time
from pathlib import Path

try:
    from bleak import BleakClient, BleakScanner
except ImportError:
    sys.exit("missing dependency -- run: pip3 install bleak")

OUT_DIR = Path(__file__).parent / "data"
OUT_DIR.mkdir(exist_ok=True)


def stamp():
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


async def resolve(target, timeout=10.0):
    """Return a connectable address for `target`. If it's already an
    address-shaped string, use it as-is; otherwise scan and match by
    advertised name (case-insensitive substring)."""
    looks_like_address = (":" in target and len(target) >= 17) or "-" in target
    if looks_like_address:
        return target
    print(f"resolving name '{target}' via scan ({timeout}s) ...")
    devices = await BleakScanner.discover(timeout=timeout)
    for d in devices:
        if d.name and target.lower() in d.name.lower():
            print(f"resolved '{target}' -> {d.address}")
            return d.address
    sys.exit(f"no advertising device matched name '{target}'")


async def cmd_scan(seconds=10.0):
    print(f"scanning {seconds}s ...")
    devices = await BleakScanner.discover(timeout=seconds)
    for d in devices:
        print(f"{d.address}  {d.name or '(no name)'}")


async def cmd_gatt(target):
    address = await resolve(target)
    async with BleakClient(address) as client:
        print(f"connected: {client.address}")
        for service in client.services:
            print(f"Service {service.uuid}  {service.description}")
            for ch in service.characteristics:
                print(f"  Characteristic {ch.uuid}  props={ch.properties}  {ch.description}")


def _notify_handler(frames):
    def handler(_, data: bytearray):
        line = f"Notification: {data.hex()}"
        print(line)
        frames.append(line)
    return handler


async def cmd_notify(target, char_uuid, seconds=30.0):
    address = await resolve(target)
    log = OUT_DIR / f"ble-notify-mac-{stamp()}.log"
    frames = []
    async with BleakClient(address) as client:
        await client.start_notify(char_uuid, _notify_handler(frames))
        await asyncio.sleep(seconds)
        await client.stop_notify(char_uuid)
    log.write_text("\n".join(frames) + "\n")
    print(f"captured {len(frames)} notifications")
    print(f"frames: {log}")


async def cmd_poll(target, write_uuid, hex_payload, notify_uuid, seconds=30.0):
    address = await resolve(target)
    log = OUT_DIR / f"ble-poll-mac-{stamp()}.log"
    frames = []
    payload = bytes.fromhex(hex_payload)
    async with BleakClient(address) as client:
        await client.start_notify(notify_uuid, _notify_handler(frames))
        await asyncio.sleep(0.5)  # let the subscription settle before writing
        # response=False forces write-without-response -- JBD's write char
        # (ff02) only supports this, same lesson as ble-probe.sh's poll fix.
        await client.write_gatt_char(write_uuid, payload, response=False)
        await asyncio.sleep(seconds)
        await client.stop_notify(notify_uuid)
    log.write_text("\n".join(frames) + "\n")
    print(f"captured {len(frames)} notifications")
    print(f"frames: {log}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "scan":
        asyncio.run(cmd_scan(float(args[0]) if args else 10.0))
    elif cmd == "gatt":
        asyncio.run(cmd_gatt(args[0]))
    elif cmd == "notify":
        asyncio.run(cmd_notify(args[0], args[1], float(args[2]) if len(args) > 2 else 30.0))
    elif cmd == "poll":
        asyncio.run(cmd_poll(args[0], args[1], args[2], args[3], float(args[4]) if len(args) > 4 else 30.0))
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
