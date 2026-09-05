#!/usr/bin/env bash
# First contact with a freshly imaged HALOS card, before Ansible can reach it.
#
#   scripts/halos_card_bootstrap.sh <lan-ip>          key + password + report
#   scripts/halos_card_bootstrap.sh <lan-ip> --cap    also cap the CPU clock
#
# Ansible needs key-based ssh and the sops password; a fresh image has neither.
# This is the gap between "the card booted" and step 3 of
# intermediate_files/claude_slop/halos-fresh-image-rebuild.md, which used to
# read "change it to the sops value" with no command behind it.
#
# Idempotent: safe to re-run against a card that is already bootstrapped.
# shellcheck disable=SC2086,SC2016
set -euo pipefail

cd "$(dirname "$0")/.."

IP="${1:-}"
[ -n "$IP" ] || { echo "usage: $0 <lan-ip> [--cap]" >&2; exit 2; }
CAP="${2:-}"
KEY="${SSH_PUBKEY:-$HOME/.ssh/id_ed25519.pub}"
SSH="ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15"

command -v sshpass >/dev/null || { echo "need sshpass (apt install sshpass)" >&2; exit 1; }
[ -f "$KEY" ] || { echo "no public key at $KEY; set SSH_PUBKEY" >&2; exit 1; }

PW=$(sops --decrypt --extract '["symphony_halos_pi_password"]' secrets/symphony.sops.yaml)

# The image default is `halos` (halos-distro README); Hat Labs' docs say
# `raspberry`. Try the sops value first so a re-run is a no-op.
CUR=""
for cand in "$PW" halos raspberry; do
  if SSHPASS="$cand" sshpass -e $SSH -o PreferredAuthentications=password \
       -o PubkeyAuthentication=no "pi@$IP" true 2>/dev/null; then CUR="$cand"; break; fi
done
[ -n "$CUR" ] || { echo "no known password worked for pi@$IP" >&2; exit 1; }

if ! $SSH -o BatchMode=yes "pi@$IP" true 2>/dev/null; then
  SSHPASS="$CUR" sshpass -e $SSH "pi@$IP" \
    'umask 077; mkdir -p ~/.ssh; cat >> ~/.ssh/authorized_keys; chmod 600 ~/.ssh/authorized_keys' < "$KEY"
  echo "key installed"
else
  echo "key already present"
fi

if [ "$CUR" = "$PW" ]; then
  echo "password already the sops value"
else
  # sudo is NOT passwordless on every image (the Pi 5 card was not, 2026-09-04),
  # and chpasswd needs stdin for the password file -- so the sudo password goes
  # through SUDO_ASKPASS, never down the same pipe as the content.
  AP=/home/pi/.halos-askpass
  printf '#!/bin/sh\nprintf %%s %s\n' "$CUR" | $SSH -o BatchMode=yes "pi@$IP" \
    "umask 077; cat > $AP; chmod 700 $AP"
  printf 'pi:%s\n' "$PW" | $SSH -o BatchMode=yes "pi@$IP" \
    "umask 077; cat > /home/pi/.halos-np
     SUDO_ASKPASS=$AP sudo -A chpasswd < /home/pi/.halos-np
     shred -u /home/pi/.halos-np $AP"
  echo "password set to the sops value"
fi

$SSH -o BatchMode=yes "pi@$IP" 'sudo -k; sudo -n true 2>/dev/null' \
  && SUDO=passwordless || SUDO=password-required

MODEL=$($SSH -o BatchMode=yes "pi@$IP" 'tr -d "\0" < /proc/device-tree/model')
RAM=$($SSH -o BatchMode=yes "pi@$IP" 'free -m | awk "/^Mem/{print \$2}"')
THROT=$($SSH -o BatchMode=yes "pi@$IP" 'vcgencmd get_throttled | cut -d= -f2')

echo "board      $MODEL"
echo "memory     ${RAM} MB"
echo "sudo       $SUDO"
echo "throttled  $THROT"

# Bit 0 is under-voltage right now. A card that reads it at idle will die
# under a parallel `docker pull` -- measured 2026-09-04, a Pi 5 on a bench
# supply dropped off the LAN mid-build with no OOM and no panic.
if [ $(( $((THROT)) & 1 )) -eq 1 ]; then
  echo "WARNING: under-voltage NOW. This card will brown out under load." >&2
  echo "         Fix the supply, or re-run with --cap to trade clock for current." >&2
fi

if [ "$CAP" = "--cap" ]; then
  # scaling_max_freq is the only lever that matters: cpufreq-dt exposes a
  # `boost` knob but scaling_boost_frequencies is empty on the Pi 5, so
  # disabling boost changes nothing. Runtime only; reverts on reboot.
  # The password goes down stdin, never into the command string: an
  # interpolated "echo '$PW' | sudo -S" would sit in ssh's argv locally and in
  # the remote shell's argv on the card, readable from `ps` in both places.
  # Same reason the password-set step above uses SUDO_ASKPASS.
  printf '%s\n' "$PW" | $SSH -o BatchMode=yes "pi@$IP" \
    "sudo -S -p '' sh -c 'for c in /sys/devices/system/cpu/cpu[0-9]*/cpufreq; do
       echo powersave > \$c/scaling_governor
       echo 1500000  > \$c/scaling_max_freq
     done'"
  echo "clock      capped to 1.5 GHz, powersave (runtime only, reverts on reboot)"
  echo "throttled  $($SSH -o BatchMode=yes "pi@$IP" 'vcgencmd get_throttled | cut -d= -f2') after cap"
fi
