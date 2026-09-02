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
#
# Run anywhere but a boat card -- a Mac, WSL, a desktop container -- this
# refuses and does nothing. It has no notion of a target host: it writes
# root-owned files into /usr/local/sbin, /etc/systemd, /etc/apt and
# /home/pi, enables timers, and rewrites the root crontab, all on whatever
# machine it happens to be on. The three checks below are what stand between
# a mistyped `sudo host/install.sh` and a dev box with a boat's cron in it.
# SYMPHONY_INSTALL_FORCE=1 skips them if you know better.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The login user that owns the boat's interactive session.
BOAT_USER=pi

# Is this a boat card? Three questions, each answered once and by name, so
# the refusal below can say which one failed.
have_systemd=no
have_boat_user=no
is_arm=no
[ -d /run/systemd/system ] && have_systemd=yes
id "$BOAT_USER" >/dev/null 2>&1 && have_boat_user=yes
case "$(uname -m)" in aarch64 | armv7l | armv6l) is_arm=yes ;; esac

if [ "${SYMPHONY_INSTALL_FORCE:-}" != 1 ]; then
	refuse=
	[ "$have_systemd" = yes ] || refuse="$refuse systemd(not booted with it)"
	[ "$have_boat_user" = yes ] || refuse="$refuse user-$BOAT_USER(absent)"
	[ "$is_arm" = yes ] || refuse="$refuse arch($(uname -m), not a Pi)"
	if [ -n "$refuse" ]; then
		echo "install.sh: this does not look like a boat card --$refuse" >&2
		echo "install.sh: refusing. SYMPHONY_INSTALL_FORCE=1 to override." >&2
		exit 1
	fi
fi

# Native SignalK on the boat card, containerised SignalK on a HALOS card; the
# drop-in goes in whichever unit's .d directory, and on a card with neither
# yet, the native one. Shared with host/signalk-ble-check so the two agree.
# shellcheck source=host/signalk-unit.sh
. "$HERE/signalk-unit.sh"
signalk_unit_detect

# <source in host/>:<destination>:<mode>:<owner>:<group>[:keep]
#
# A trailing `keep` means "install it only if it is not already there." Use it
# for a file whose correct contents differ per card, where the copy in host/ is
# one card's version and overwriting the other card's is a silent regression.
INSTALL=(
	"nightly-reboot:/usr/local/sbin/nightly-reboot:0755:root:root"
	"signalk-after-bluetooth.conf:/etc/systemd/system/$SIGNALK_UNIT.d/after-bluetooth.conf:0644:root:root"
	# keep: the two cards ping two DIFFERENT healthchecks.io checks, and this
	# file has room for one URL. Copying it unconditionally meant whichever
	# card ran the installer last took over the other's check -- so the card
	# that lost it went quiet and nothing alarmed, because the check itself
	# was still being pinged. ansible/roles/monitoring writes this file per
	# host from sops; here it is a fallback for a card Ansible has not
	# reached yet.
	"boat-heartbeat.json:/etc/boat-heartbeat.json:0600:root:root:keep"
	"signalk-unit.sh:/usr/local/lib/symphony/signalk-unit.sh:0644:root:root"
	"signalk-ble-check:/usr/local/sbin/signalk-ble-check:0755:root:root"
	"signalk-ble-check.service:/etc/systemd/system/signalk-ble-check.service:0644:root:root"
	"signalk-ble-check.timer:/etc/systemd/system/signalk-ble-check.timer:0644:root:root"
	"apt-auto-upgrades.conf:/etc/apt/apt.conf.d/20auto-upgrades:0644:root:root"
	"apt-unattended-boat.conf:/etc/apt/apt.conf.d/52unattended-upgrades-boat:0644:root:root"
)

# The watchdog drop-in, chrony's conf.d file, claude-resident and the
# heartbeat script/units are gone from here -- ported to ansible/roles/clock,
# watchdog, claude-resident and monitoring. This installer no longer owns
# those paths; reference/host_provisioning.md's migration path is explicit
# that the two must not both own a file.

# System services to restart after their config lands. Skipped when the unit
# isn't present, so this file can carry config for a package that hasn't been
# installed yet.
RESTART=(
)

# System services that reread their config on reload. Same purpose as RESTART,
# but for daemons a restart would be worse than the stale config: bouncing the
# system bus takes every dbus client on the box down with it. Skipped when the
# unit isn't present.
RELOAD=(
)

# System units this installer enables and starts. Timers belong here; a unit
# file that lands in /etc/systemd/system does nothing until something enables
# it, and forgetting that is how a change looks installed but never runs.
ENABLE=(
	"signalk-ble-check.timer"
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
	IFS=: read -r src dest mode owner group keep <<<"$spec"
	if [ ! -f "$HERE/$src" ]; then
		echo "  MISSING in repo: $src" >&2
		exit 1
	fi
	if [ "${keep:-}" = keep ] && [ -e "$dest" ]; then
		echo "  $dest  (kept, already installed)"
		continue
	fi
	install -D -o "$owner" -g "$group" -m "$mode" "$HERE/$src" "$dest"
	echo "  $dest  ($mode $owner:$group)"
	case "$dest" in
	/etc/systemd/*) reexec=yes ;;
	esac
done

# A [Manager] setting under /etc/systemd/system.conf.d only takes effect on
# re-exec; daemon-reload is not enough. Nothing left in INSTALL writes there
# today (ansible/roles/watchdog does), but a unit file under /etc/systemd/
# still wants the manager to have re-read it, so this stays broad rather than
# naming a specific path.
if [ "${reexec:-}" = yes ]; then
	echo "== systemd daemon-reexec =="
	systemctl daemon-reexec
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

for unit in "${RELOAD[@]:-}"; do
	[ -n "$unit" ] || continue
	if [ -z "${reload_header:-}" ]; then
		echo "== service reloads =="
		reload_header=done
	fi
	if systemctl cat "$unit" >/dev/null 2>&1; then
		systemctl reload "$unit"
		echo "  $unit  ($(systemctl is-active "$unit" || true))"
	else
		echo "  $unit  not installed, skipped"
	fi
done

for unit in "${ENABLE[@]:-}"; do
	[ -n "$unit" ] || continue
	if [ -z "${enable_header:-}" ]; then
		echo "== enable =="
		enable_header=done
	fi
	systemctl enable --now "$unit" >/dev/null 2>&1 || true
	echo "  $unit  ($(systemctl is-enabled "$unit" 2>&1), $(systemctl is-active "$unit" 2>&1))"
done

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
