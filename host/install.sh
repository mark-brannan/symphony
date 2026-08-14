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

# The login user that owns the boat's interactive session. Its systemd --user
# units are installed and enabled below.
BOAT_USER=pi

# <source in host/>:<destination>:<mode>:<owner>:<group>
INSTALL=(
	"nightly-reboot:/usr/local/sbin/nightly-reboot:0755:root:root"
	"systemd-watchdog.conf:/etc/systemd/system.conf.d/watchdog.conf:0644:root:root"
	"claude-resident:/home/$BOAT_USER/bin/claude-resident:0755:$BOAT_USER:$BOAT_USER"
	"claude-resident.service:/home/$BOAT_USER/.config/systemd/user/claude-resident.service:0644:$BOAT_USER:$BOAT_USER"
	"chrony-gpsd.conf:/etc/chrony/conf.d/gpsd.conf:0644:root:root"
)

# System services to restart after their config lands. Skipped when the unit
# isn't present, so this file can carry config for a package that hasn't been
# installed yet.
RESTART=(
	"chrony"
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
	IFS=: read -r src dest mode owner group <<<"$spec"
	if [ ! -f "$HERE/$src" ]; then
		echo "  MISSING in repo: $src" >&2
		exit 1
	fi
	install -D -o "$owner" -g "$group" -m "$mode" "$HERE/$src" "$dest"
	echo "  $dest  ($mode $owner:$group)"
	case "$dest" in
	/etc/systemd/*) reexec=yes ;;
	*/.config/systemd/user/*) user_units=yes ;;
	esac
done

# systemd manager settings (watchdog and friends) only take effect on
# re-exec; daemon-reload is not enough.
if [ "${reexec:-}" = yes ]; then
	echo "== systemd daemon-reexec =="
	systemctl daemon-reexec
	systemctl show -p RuntimeWatchdogUSec -p RebootWatchdogUSec | sed 's/^/  /'
fi

# Services whose config lives in host/. A dropped-in config file does nothing
# until its daemon rereads it, and skipping this is how a change looks applied
# while the running service still has the old settings. Units that aren't
# installed are skipped, not an error — this installer places config, it does
# not install packages. Prerequisites are in RUNBOOK.
for unit in "${RESTART[@]:-}"; do
	[ -n "$unit" ] || continue
	if [ -z "${restart_header:-}" ]; then
		echo "== service restarts =="
		restart_header=done
	fi
	if systemctl cat "$unit" >/dev/null 2>&1; then
		systemctl restart "$unit"
		echo "  $unit  ($(systemctl is-active "$unit" || true))"
	else
		echo "  $unit  not installed, skipped"
	fi
done

# A systemd --user unit only runs while that user has a session, unless
# lingering is on. Enabling it here is what lets the resident Claude session
# come back after a reboot with nobody logged in.
if [ "${user_units:-}" = yes ]; then
	echo "== user units =="
	uid="$(id -u "$BOAT_USER")"
	as_boat_user() {
		sudo -u "$BOAT_USER" XDG_RUNTIME_DIR="/run/user/$uid" "$@"
	}
	loginctl enable-linger "$BOAT_USER"
	as_boat_user systemctl --user daemon-reload
	as_boat_user systemctl --user enable --now claude-resident.service
	echo "  claude-resident.service  $(as_boat_user systemctl --user is-enabled claude-resident.service || true)"
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
