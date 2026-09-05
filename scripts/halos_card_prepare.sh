#!/usr/bin/env bash
# Prepare a freshly flashed HALOS card for the boat. One command, from a
# tailnet dev box with sops access; the card is in the bench Pi on the LAN.
#
#   scripts/halos_card_prepare.sh <lan-ip>       virgin card: bootstrap first
#   scripts/halos_card_prepare.sh                card already on the tailnet
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
H=symphony-halos                       # tailnet name once the network role ran
D=/var/lib/container-apps/marine-signalk-server-container/data/data
VENUS_HOST=192.168.8.107               # the Cerbo's LAN address; see kanban card "Pick a name for the boat's Venus GX"
STAGE="${TMPDIR:-/tmp}/halos-prepare-$$"
PW=$(sops --decrypt --extract '["symphony_halos_pi_password"]' secrets/symphony.sops.yaml)
. scripts/halos_disabled_plugins.sh    # EXPECT: plugins that stay off on this card

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
    halos_cards: { hosts: { symphony-halos: { ansible_host: $TARGET } } }
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
# 2 GB bench cannot hold the databases next to the build; back up for the preflight.
sudo_on "$CARD" "systemctl stop marine-questdb-container marine-grafana-container marine-influxdb-container" || true

step "2. ansible site.yml (host layer; may reboot the card)"
(cd ansible && ansible-playbook "${ANSIBLE_ARGS[@]}" site.yml -l symphony-halos)
wait_ssh "$H"    # the network role put the card on the tailnet; use that name from here

step "3. SignalK state from the boat, relayed through this box"
mkdir -p "$STAGE/sk" "$STAGE/bt"
rsync -a --exclude node_modules --exclude appstore-cache --exclude signalk-server \
  --exclude 'skserver-raw_*' --exclude '*.bak*' --exclude '*.deb' --exclude 'ssl-*.pem' --exclude '*.sqlite*' \
  pi@symphony-pi:.signalk/ "$STAGE/sk/"
rsync -a --exclude node_modules --exclude .git pi@symphony-pi:bt-sensors-plugin-sk/ "$STAGE/bt/"
# Keep the card's own settings if it already has them (a re-run), else they
# arrive from the boat and step 5 rewrites them.
keep=()
for f in $(echo "$CONFIG_EXPECT" | tr '|' ' '); do
  ssh "pi@$H" "test -f $D/plugin-config-data/$f" && keep+=(--exclude "plugin-config-data/$f")
done
ssh "pi@$H" "mkdir -p $D/local-plugins"
rsync -a --exclude package.json "${keep[@]}" "$STAGE/sk/" "pi@$H:$D/"
rsync -a "$STAGE/bt/" "pi@$H:$D/local-plugins/bt-sensors-plugin-sk/"
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
python3 - "$STAGE/sk/package.json" "$STAGE/installed.txt" <<'PY' | ssh "pi@$H" "cat > $D/package.json"
import json, sys
pkg = json.load(open(sys.argv[1]))
exact = dict(l.split() for l in open(sys.argv[2]) if l.strip())
deps = pkg["dependencies"]
for k in deps:
    if k in exact: deps[k] = exact[k]
for fork in ("bt-sensors-plugin-sk", "signalk-plugin-watchdog"):
    deps[fork] = f"file:local-plugins/{fork}"
json.dump(pkg, sys.stdout, indent=2)
PY
ssh "pi@$H" "grep -c 'file:local-plugins/' $D/package.json" | grep -qx 2 || { echo "fork pins missing in package.json" >&2; exit 1; }

step "4. npm build (about 19 min on a Pi 4; survives a dropped ssh)"
sudo_on "$H" "/home/pi/symphony/scripts/halos_signalk_npm.sh install"

step "5. card overrides: ${EXPECT} off, venus host $VENUS_HOST"
ssh "pi@$H" "python3 - $D/plugin-config-data '$EXPECT' $VENUS_HOST" <<'PY'
import json, sys
d, names, venus = sys.argv[1], sys.argv[2].split(), sys.argv[3]
for n in names:
    p = f"{d}/{n}.json"
    c = json.load(open(p)); c["enabled"] = False
    json.dump(c, open(p, "w"), indent=2)
p = f"{d}/venus.json"
c = json.load(open(p)); c["configuration"]["MQTT"]["host"] = venus
json.dump(c, open(p, "w"), indent=2)
PY
sudo_on "$H" "systemctl restart marine-signalk-server-container"

step "6. front door: ntfy, SignalK route"
# From this checkout, not the card's: the card's clone may be behind.
rsync -a host/halos/ "pi@$H:/home/pi/halos-prepare/"
sudo_on "$H" "sh -c 'cd /home/pi/halos-prepare && docker compose -p symphony-ntfy -f compose-ntfy.yml up -d && install -m 0644 traefik-symphony-signalk-host.yml /etc/halos/traefik-dynamic.d/symphony-signalk-host.yml'"

step "7. reboot, then wait for the cold start"
sudo_on "$H" "systemctl reboot" || true
sleep 20; wait_ssh "$H"
# QuestDB and Grafana come back with the boot; a card under 3 GB cannot run
# them next to SignalK (the preflight checks them as enabled there instead).
mem=$(ssh "pi@$H" "free -m | awk '/^Mem/{print \$2}'")
[ "$mem" -ge 3000 ] || sudo_on "$H" "systemctl stop marine-questdb-container marine-grafana-container"
echo "waiting 5 min for SignalK's cold start"; sleep 300

step "8. preflight -- ready when every line is ok"
exec scripts/halos_preflight.sh "$H"
