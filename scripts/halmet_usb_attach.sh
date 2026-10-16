#!/usr/bin/env bash
# Attach the HALMET CH340 (1a86:7523) to WSL from the WSL side; Windows-side `usbipd attach` hangs here.
# Usage: halmet_usb_attach.sh [busid]   (default 5-3)
set -euo pipefail
BUSID="${1:-5-3}"
# Needed for usbip attach and for the CH340 serial node.
sudo modprobe vhci-hcd
sudo modprobe ch341
if [ -e /dev/ttyUSB0 ]; then
  echo "/dev/ttyUSB0 already present"
  exit 0
fi
# Mirrored WSL networking: the Windows usbipd server is on 127.0.0.1.
sudo "/mnt/c/Program Files/usbipd-win/WSL/usbip" attach --remote=127.0.0.1 --busid="$BUSID" || true
for _ in $(seq 1 20); do
  if [ -e /dev/ttyUSB0 ]; then
    echo "OK /dev/ttyUSB0"
    exit 0
  fi
  sleep 0.5
done
echo "FAIL: /dev/ttyUSB0 did not appear; run 'usbipd bind --busid $BUSID' once in an admin PowerShell, then retry" >&2
exit 1
