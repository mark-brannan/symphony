#!/usr/bin/env bash
# Install the dev-box Signal K mDNS announcer as a systemd user service (WSL).
# Runs in WSL, not Docker: under Docker Desktop "host network" is its VM, which
# is not on the LAN. Idempotent; prints the check at the end.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
dest="$HOME/.local/share/signalk-mdns"

mkdir -p "$dest" "$HOME/.config/systemd/user"
[ -x "$dest/venv/bin/python" ] || python3 -m venv "$dest/venv"
"$dest/venv/bin/pip" install -q zeroconf
install -m 0644 "$here/announce.py" "$dest/announce.py"
install -m 0644 "$here/signalk-mdns.service" "$HOME/.config/systemd/user/signalk-mdns.service"
systemctl --user daemon-reload
systemctl --user enable signalk-mdns.service
systemctl --user restart signalk-mdns.service
sleep 3
journalctl --user -u signalk-mdns.service -n 1 --no-pager -o cat
