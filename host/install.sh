#!/usr/bin/env bash
# Install this directory's host files onto the machine it runs on.
#
# Idempotent: re-running replaces the installed copies and rewrites the cron
# entries it owns, leaving any other root cron entry alone. Run it on the
# host itself, as root.
#
#   sudo host/install.sh
#
# Adding a file: drop it in host/, then add a line to INSTALL and (if it
# needs scheduling) to CRON below.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# <source in host/>:<destination>:<mode>
INSTALL=(
	"nightly-reboot:/usr/local/sbin/nightly-reboot:0755"
	"systemd-watchdog.conf:/etc/systemd/system.conf.d/watchdog.conf:0644"
)

# Root cron entries this installer owns. Matched for removal by the command
# path, so editing a schedule here replaces rather than duplicates.
#
# The nightly reboot is written commented-out on purpose. It turned out to be
# covering for the v3d GPU hang rather than preventing anything (RUNBOOK →
# "Don't autostart a browser on the boat Pi"), so it was disabled on the box.
# Leaving it active here would have this installer silently switch it back on.
# Uncomment both here and on the host if you ever want it running again.
CRON=(
	"#0 4 * * * /usr/local/sbin/nightly-reboot"
)

if [ "$(id -u)" -ne 0 ]; then
	echo "install.sh: must run as root (try: sudo host/install.sh)" >&2
	exit 1
fi

echo "== files =="
for spec in "${INSTALL[@]}"; do
	IFS=: read -r src dest mode <<<"$spec"
	if [ ! -f "$HERE/$src" ]; then
		echo "  MISSING in repo: $src" >&2
		exit 1
	fi
	install -D -o root -g root -m "$mode" "$HERE/$src" "$dest"
	echo "  $dest  ($mode)"
	case "$dest" in /etc/systemd/*) reexec=yes ;; esac
done

# systemd manager settings (watchdog and friends) only take effect on
# re-exec; daemon-reload is not enough.
if [ "${reexec:-}" = yes ]; then
	echo "== systemd daemon-reexec =="
	systemctl daemon-reexec
	systemctl show -p RuntimeWatchdogUSec -p RebootWatchdogUSec | sed 's/^/  /'
fi

echo "== root crontab =="
current="$(crontab -l 2>/dev/null || true)"

# Drop any existing entry pointing at a destination we manage, plus the
# bare `shutdown -r` line this replaced.
filtered="$current"
for spec in "${INSTALL[@]}"; do
	IFS=: read -r _ dest _ <<<"$spec"
	filtered="$(printf '%s\n' "$filtered" | grep -vF "$dest" || true)"
done
filtered="$(printf '%s\n' "$filtered" | grep -vE '^[^#]*/sbin/shutdown -r' || true)"

{
	printf '%s\n' "$filtered" | sed '/^$/d'
	printf '%s\n' "${CRON[@]}"
} | crontab -

crontab -l | sed 's/^/  /'
echo "== done =="
