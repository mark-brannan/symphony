# shellcheck shell=sh
# SC2034: every SIGNALK_* here is read by whoever sources this file.
# shellcheck disable=SC2034
# Which shape of SignalK this host runs. Sourced by host/install.sh and
# host/signalk-ble-check so the two can never drift apart; not executable on
# its own. POSIX sh, because signalk-ble-check is.
#
# Call signalk_unit_detect, then read:
#
#   SIGNALK_KIND        native | container | none
#   SIGNALK_UNIT        the systemd unit to act on
#   SIGNALK_CONFIG      bt-sensors-plugin-sk.json for that shape
#   SIGNALK_HAS_SOCKET  1 if signalk.socket exists, else 0
#
# `none` means neither unit is installed: a fresh card before SignalK is on
# it, or a machine that is not a boat card at all. SIGNALK_UNIT is the native
# name in that case, so a caller that only needs somewhere to put a drop-in
# gets the right answer on a fresh native card. A caller that needs a running
# server must check SIGNALK_KIND, not just SIGNALK_UNIT.
#
# HAS_SOCKET is read from the socket unit itself rather than inferred from
# KIND: native SignalK is socket-activated on this boat and the HALOS
# container is not, but that is a fact about the install, not a law.

SIGNALK_NATIVE_UNIT=signalk.service
SIGNALK_CONTAINER_UNIT=marine-signalk-server-container.service
SIGNALK_SOCKET_UNIT=signalk.socket

SIGNALK_NATIVE_CONFIG=/home/pi/.signalk/plugin-config-data/bt-sensors-plugin-sk.json
SIGNALK_CONTAINER_CONFIG=/var/lib/container-apps/marine-signalk-server-container/data/data/plugin-config-data/bt-sensors-plugin-sk.json

signalk_unit_detect() {
	# Each question asked once, by name. `systemctl cat` fails the same way
	# for "unit not installed" and for "no systemctl on this machine", which
	# is what makes `none` the honest answer on a Mac or a WSL box.
	signalk_native_installed=no
	signalk_container_installed=no
	signalk_socket_installed=no
	systemctl cat "$SIGNALK_NATIVE_UNIT" >/dev/null 2>&1 && signalk_native_installed=yes
	systemctl cat "$SIGNALK_CONTAINER_UNIT" >/dev/null 2>&1 && signalk_container_installed=yes
	systemctl cat "$SIGNALK_SOCKET_UNIT" >/dev/null 2>&1 && signalk_socket_installed=yes

	if [ "$signalk_native_installed" = yes ]; then
		SIGNALK_KIND=native
	elif [ "$signalk_container_installed" = yes ]; then
		SIGNALK_KIND=container
	else
		SIGNALK_KIND=none
	fi

	if [ "$SIGNALK_KIND" = container ]; then
		SIGNALK_UNIT=$SIGNALK_CONTAINER_UNIT
		SIGNALK_CONFIG=$SIGNALK_CONTAINER_CONFIG
	else
		SIGNALK_UNIT=$SIGNALK_NATIVE_UNIT
		SIGNALK_CONFIG=$SIGNALK_NATIVE_CONFIG
	fi

	SIGNALK_HAS_SOCKET=0
	[ "$signalk_socket_installed" = yes ] && SIGNALK_HAS_SOCKET=1

	return 0
}
