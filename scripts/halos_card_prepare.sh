#!/usr/bin/env bash
# Prepare a freshly flashed HALOS card for the boat. One command, from a
# tailnet dev box with sops access; the card is in the bench Pi on the LAN.
#
#   scripts/halos_card_prepare.sh 192.168.1.50   virgin card: bootstrap first (use the card's own LAN IP)
#   scripts/halos_card_prepare.sh                card already on the tailnet
#
# Another card (the HALPI2): CARD_NAME is its inventory/tailnet name, CARD_SSH
# the address ssh uses when the tailnet name is unusable from this box:
#   CARD_NAME=symphony-halpi2 CARD_SSH=192.168.0.110 scripts/halos_card_prepare.sh
#
# Runs every layer in order and stops at the first failure. Idempotent: a
# re-run after a fix picks up where the card is. Ends with the preflight; the
# card is ready when every preflight line reads ok and nothing else.
#
# Layers, and why each is here rather than in site.yml (see site.yml header):
#   1. app packages    apt, BEFORE Ansible -- they drag in influxdb, which
#                      roles/base then purges
#   2. site.yml        host layer, may reboot the card mid-run
#   3. SignalK state   the boat's config, both plugin forks, the boat's
#                      package.json with the forks re-pinned. Relayed through
#                      this box: a tagged card may not ssh to the boat.
#   4. npm build       scripts/halos_signalk_npm.sh, ~19 min on a Pi 4
#   5. card overrides  the plugins that stay off here, and the Venus host
#   6. front door      ntfy (host/halos/compose-ntfy.yml), the SignalK Traefik route
#   7. reboot          proves the persistent journal; nothing else needs it
#   8. preflight       scripts/halos_preflight.sh
# shellcheck disable=SC2029,SC2086
set -euo pipefail
cd "$(dirname "$0")/.."

for tool in sops ansible-playbook rsync ssh; do
  command -v "$tool" >/dev/null || { echo "need $tool on PATH" >&2; exit 1; }
done

TARGET="${1:-symphony-halos}"
CARD_NAME="${CARD_NAME:-symphony-halos}"   # inventory and tailnet name
H="${CARD_SSH:-$CARD_NAME}"                # what ssh and rsync connect to
D=/var/lib/container-apps/marine-signalk-server-container/data/data
VENUS_HOST=192.168.8.107               # the Cerbo's LAN address; see kanban card "Pick a name for the boat's Venus GX"
STAGE="${TMPDIR:-/tmp}/halos-prepare-$$"
# The boat's state copy survives between runs, so a dropped slow link resumes (--partial) instead of restarting.
CACHE="${TMPDIR:-/tmp}/halos-prepare-cache"
PW=$(sops --decrypt --extract '["symphony_halos_pi_password"]' secrets/symphony.sops.yaml)
. scripts/halos_disabled_plugins.sh    # EXPECT, CONFIG_EXPECT, SIGNALK_STATE_EXCLUDES

step() { printf '\n== %s\n' "$*"; }
sudo_on() { local host=$1; shift; printf '%s\n' "$PW" | ssh "pi@$host" "sudo -S -p '' $*"; }
wait_ssh() { local _; for _ in $(seq 1 60); do ssh -o ConnectTimeout=5 -o BatchMode=yes "pi@$1" true 2>/dev/null && return 0; sleep 5; done; echo "$1 did not come back" >&2; return 1; }
trap 'rm -rf "$STAGE"' EXIT

if [[ "$TARGET" =~ ^[0-9.]+$ ]]; then
  step "bootstrap $TARGET (key, password, power check)"
  scripts/halos_card_bootstrap.sh "$TARGET"
  INV="$STAGE/inv.yml"; mkdir -p "$STAGE"
  cat >"$INV" <<EOF
all:
  children:
    halos_cards: { hosts: { $CARD_NAME: { ansible_host: $TARGET } } }
  vars:
    ansible_user: pi
    ansible_ssh_common_args: '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
EOF
  ANSIBLE_ARGS=(-i "$INV")
  CARD=$TARGET
else
  ANSIBLE_ARGS=()
  CARD=$H
fi

step "1. app packages (QuestDB, Grafana) on $CARD"
sudo_on "$CARD" "sh -c 'apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq marine-questdb-container marine-grafana-container'"
# A card under 3 GB cannot hold the databases next to the build; an 8 GB one runs them.
sudo_on "$CARD" "systemctl stop marine-influxdb-container" || true
[ "$(ssh "pi@$CARD" "free -m | awk '/^Mem/{print \$2}'")" -ge 3000 ] || sudo_on "$CARD" "systemctl stop marine-questdb-container marine-grafana-container" || true

step "2. ansible site.yml (host layer; may reboot the card)"
[ "$H" = "$CARD_NAME" ] || [[ "$TARGET" =~ ^[0-9.]+$ ]] || ANSIBLE_ARGS+=(-e "ansible_host=$H")
(cd ansible && ansible-playbook "${ANSIBLE_ARGS[@]}" site.yml -l "$CARD_NAME")
wait_ssh "$H"    # the network role put the card on the tailnet; use that name from here

step "3. SignalK state from the boat, relayed through this box"
# The cache holds the boat's security.json; keep it private, and a failed run keeps it for resume.
mkdir -p "$CACHE"; chmod 700 "$CACHE"
mkdir -p "$STAGE" "$CACHE/sk" "$CACHE/bt" "$CACHE/uptime"
excl=(); set -f; for e in $SIGNALK_STATE_EXCLUDES; do excl+=(--exclude "$e"); done; set +f
rsync -a --partial --delete "${excl[@]}" pi@symphony-pi:.signalk/ "$CACHE/sk/"
rsync -a --partial --delete --exclude node_modules --exclude .git pi@symphony-pi:bt-sensors-plugin-sk/ "$CACHE/bt/"
# signalk-rpi-uptime was unpublished from npm on 2026-10-13, so `npm install` 404s on its pin; carry the boat's copy as a local plugin.
rsync -a --delete pi@symphony-pi:.signalk/node_modules/signalk-rpi-uptime/ "$CACHE/uptime/"
# Keep the card's own settings if it already has them (a re-run), else they
# arrive from the boat and step 5 rewrites them.
keep=()
for f in $(echo "$CONFIG_EXPECT" | tr '|' ' '); do
  ssh "pi@$H" "test -f $D/plugin-config-data/$f" && keep+=(--exclude "plugin-config-data/$f")
done
ssh "pi@$H" "mkdir -p $D/local-plugins"
# --delete: a file the boat has since removed must not linger on the card
# (that's exactly what fails the preflight's `state` line); local-plugins is
# excluded because steps below repopulate it from this box, not from the sync.
# system-plugins is root-owned HaLOS image content (signalk-halpi on the HALPI2); --delete cannot, and must not, remove it.
rsync -a --delete --exclude package.json --exclude .halos-npm-stamp --exclude local-plugins --exclude system-plugins "${keep[@]}" "$CACHE/sk/" "pi@$H:$D/"
rsync -a "$CACHE/bt/" "pi@$H:$D/local-plugins/bt-sensors-plugin-sk/"
rsync -a --delete "$CACHE/uptime/" "pi@$H:$D/local-plugins/signalk-rpi-uptime/"
ssh "pi@$H" "git -C /home/pi/symphony pull -q && rm -rf $D/local-plugins/signalk-plugin-watchdog && cp -r /home/pi/symphony/plugins/signalk-plugin-watchdog $D/local-plugins/"
# The boat's package.json with every plugin pinned to the version the boat
# actually runs (its ranges would let npm take a newer patch and fail the
# preflight's state line), and both forks pinned to the copies just made.
ssh pi@symphony-pi 'cd .signalk && python3 -c "
import json,os
for k in json.load(open(\"package.json\"))[\"dependencies\"]:
    p=f\"node_modules/{k}/package.json\"
    if os.path.exists(p): print(k, json.load(open(p))[\"version\"])
"' > "$STAGE/installed.txt"
python3 - "$CACHE/sk/package.json" "$STAGE/installed.txt" host/halos/signalk-plugin-pins.txt <<'PY' | ssh "pi@$H" "cat > $D/package.json"
import json, sys
pkg = json.load(open(sys.argv[1]))
exact = dict(l.split() for l in open(sys.argv[2]) if l.strip())
# A pin wins only while it is ahead of the boat; once the boat catches up it never downgrades.
ver = lambda s: tuple(int(x) for x in s.split("-")[0].split("."))
for l in open(sys.argv[3]):
    if l.strip() and not l.startswith("#"):
        k, v = l.split()
        if k not in exact or ver(v) > ver(exact[k]): exact[k] = v
deps = pkg["dependencies"]
for k in deps:
    if k in exact: deps[k] = exact[k]
for fork in ("bt-sensors-plugin-sk", "signalk-plugin-watchdog", "signalk-rpi-uptime"):
    deps[fork] = f"file:local-plugins/{fork}"
json.dump(pkg, sys.stdout, indent=2)
PY
ssh "pi@$H" "grep -c 'file:local-plugins/' $D/package.json" | grep -qx 3 || { echo "fork pins missing in package.json" >&2; exit 1; }
rm -rf "$CACHE"    # state is on the card now; nothing else reads the cache

step "4. npm build (about 19 min on a Pi 4; survives a dropped ssh)"
sudo_on "$H" "/home/pi/symphony/scripts/halos_signalk_npm.sh install"

step "5. card overrides: ${EXPECT} off, venus host $VENUS_HOST"
out=$(ssh "pi@$H" "python3 - $D/plugin-config-data '$EXPECT' $VENUS_HOST" < scripts/halos_card_overrides.py)
echo "$out"
# Restart only when a file changed: the edit is idempotent, so a re-run leaves SignalK alone.
case "$out" in *"changed: 0") ;; *) sudo_on "$H" "systemctl restart marine-signalk-server-container" ;; esac

step "6. front door: ntfy (the SignalK Traefik route is placed by ansible/roles/signalk_container)"
# From this checkout, not the card's: the card's clone may be behind.
rsync -a host/halos/ "pi@$H:/home/pi/halos-prepare/"
sudo_on "$H" "sh -c 'cd /home/pi/halos-prepare && docker compose -p symphony-ntfy -f compose-ntfy.yml up -d'"

step "7. reboot, then wait for the cold start"
sudo_on "$H" "systemctl reboot" || true
sleep 20; wait_ssh "$H"
# QuestDB and Grafana come back with the boot; a card under 3 GB cannot run
# them next to SignalK (the preflight checks them as enabled there instead).
mem=$(ssh "pi@$H" "free -m | awk '/^Mem/{print \$2}'")
[ "$mem" -ge 3000 ] || sudo_on "$H" "systemctl stop marine-questdb-container marine-grafana-container"
echo "waiting 5 min for SignalK's cold start"; sleep 300

step "8. preflight -- ready when every line is ok"
CARD_NAME="$CARD_NAME" exec scripts/halos_preflight.sh "$H"
