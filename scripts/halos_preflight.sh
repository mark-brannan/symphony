#!/usr/bin/env bash
# Before the HALOS card leaves home: check the build against the boat card.
#
#   scripts/halos_preflight.sh [host]      default host: symphony-halos
#
# One `ok`/`FAIL` line per item, non-zero exit if any failed. Run from a
# tailnet machine with sops access; needs ssh to the host and to symphony-pi.
# Nothing can be fetched at the boat, so every line must be ok.
# shellcheck disable=SC2015,SC2016
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

HOST="${1:-symphony-halos}"
BOAT=symphony-pi
D=/var/lib/container-apps/marine-signalk-server-container/data/data
DOMAIN=$(sops --decrypt --extract '["boat_domain"]' secrets/symphony.sops.yaml)
rc=0
say() { printf '%-5s %-10s %s\n' "$1" "$2" "$3"; [ "$1" = ok ] || rc=1; }
r() { ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 "pi@$1" "$2" 2>/dev/null; }

# `id enabled version` per plugin from the running server, not from files: a
# config file that exists but never loaded is exactly the failure to catch.
# /skServer/plugins needs an admin login; the captain password goes over stdin.
plugins() {
  printf '{"username":"captain","password":"%s"}' "$(sops --decrypt --extract '["signalk_captain_password"]' secrets/symphony.sops.yaml)" \
    | ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 "pi@$1" 'T=$(curl -s -m 20 -H "Content-Type: application/json" -X POST 127.0.0.1:3000/signalk/v1/auth/login --data-binary @- | python3 -c "import json,sys; print(json.load(sys.stdin).get(\"token\",\"\"))"); curl -s -m 30 -H "Authorization: Bearer $T" 127.0.0.1:3000/skServer/plugins' 2>/dev/null \
    | python3 -c 'import json,sys
for p in json.load(sys.stdin): print(p["id"], "on" if p.get("data",{}).get("enabled") else "off", p.get("version",""))' 2>/dev/null | sort
}
# Enabled on the boat, disabled on HALOS by decision (halos-swap-plan.md).
EXPECT="signalk-container signalk-to-influxdb2 signalk-to-influxdb-v2-buffer signalk-notification-player"
# Present on one card only, by the images rather than the build: app-dock is bundled
# by the boat's npm server but not the HALOS image; polar-performance the reverse;
# instrument-light is off on the boat and never loads on HALOS (serialport bindings).
IMAGE_ONLY="signalk-app-dock signalk-polar-performance-plugin signalk-instrument-light-plugin"

out=$(r "$HOST" 'echo $(hostname) $(hostname -d) $(cut -d= -f2 /run/halos/domain.env) $(tailscale status --self --peers=false | awk "{print \$2}")')
[ "$out" = "signalk $DOMAIN signalk.$DOMAIN symphony-halos" ] && say ok host "$out" || say FAIL host "${out:-no answer} (want: signalk $DOMAIN signalk.$DOMAIN symphony-halos)"

missing=$(r "$HOST" 'for l in "dtparam=i2c_arm=on" "dtparam=spi=on" "enable_uart=1" "dtoverlay=mcp2515-can0"; do grep -q "^$l" /boot/firmware/config.txt || echo "config.txt:$l"; done
grep -q cgroup_enable=memory /boot/firmware/cmdline.txt || echo cmdline:cgroup_enable=memory
grep -q regdom=US /boot/firmware/cmdline.txt || echo cmdline:regdom=US
grep -qw memory /sys/fs/cgroup/cgroup.controllers || echo cgroup:memory
grep -qs "^i2c-dev" /etc/modules-load.d/*.conf || echo modules-load:i2c-dev
for d in /dev/serial0 /dev/i2c-1; do [ -e $d ] || echo "missing:$d"; done' | tr '\n' ' ')
[ -z "$missing" ] && say ok boot "overlays cgroup regdom i2c-dev serial0 i2c-1" || say FAIL boot "$missing"

out=$(r "$HOST" 'echo $(nmcli -g 802-11-wireless.ssid con show Symphony 2>/dev/null) $(nmcli -g 802-11-wireless.ssid con show Halos-AP 2>/dev/null)')
[ "$out" = "Symphony SignalK" ] && say ok wifi "profile Symphony; hotspot Halos-AP ssid SignalK" || say FAIL wifi "got '${out}' (want: Symphony SignalK)"

boatp=$(plugins "$BOAT"); hostp=$(plugins "$HOST")
if [ -z "$boatp" ] || [ -z "$hostp" ]; then
  say FAIL plugins "could not list plugins (boat: $(echo "$boatp" | grep -c .), $HOST: $(echo "$hostp" | grep -c .)) — login or server down"
else
  # id+enabled must match except EXPECT (boat on, halos off); versions differ only for the two forks.
  unexpected=$(diff <(echo "$boatp" | awk '{print $1, $2}') <(echo "$hostp" | awk '{print $1, $2}') | grep '^[<>]' | grep -vE "^[<>] (${EXPECT// /|}|${IMAGE_ONLY// /|}) " | tr '\n' ';')
  absent=; for p in $EXPECT; do echo "$hostp" | grep -q "^$p off" || absent="$absent $p"; done
  pins=$(r "$HOST" "python3 -c 'import json; d=json.load(open(\"$D/package.json\"))[\"dependencies\"]; print(d.get(\"bt-sensors-plugin-sk\",\"MISSING\"), d.get(\"signalk-plugin-watchdog\",\"MISSING\"))'")
  fix=$(r "$HOST" "grep -c getBluetoothSession $D/local-plugins/bt-sensors-plugin-sk/index.js")
  if [ -z "$unexpected" ] && [ -z "$absent" ] && [ "$pins" = "file:local-plugins/bt-sensors-plugin-sk file:local-plugins/signalk-plugin-watchdog" ] && [ "${fix:-0}" -gt 0 ]; then
    say ok plugins "$(echo "$hostp" | grep -c .) loaded, $(echo "$hostp" | grep -c ' on ') on; same set and states as the boat except the $(echo "$EXPECT" | wc -w) expected-off and $(echo "$IMAGE_ONLY" | wc -w) image-only; forks pinned, D-Bus fix present"
  else
    say FAIL plugins "unexpected diffs (< boat, > $HOST): ${unexpected:-none}; expected-but-not-off:${absent:- none}; pins: $pins; fix grep: ${fix:-0}"
  fi
fi

# The override's two effects fail silently (host/halos/README.md); the gid is read
# from the container's node process because `pi` cannot run docker on HALOS.
out=$(r "$HOST" 'echo $(systemctl is-active marine-signalk-server-container) $(curl -s -m 10 127.0.0.1:3000/signalk | python3 -c "import json,sys; print(json.load(sys.stdin)[\"server\"][\"version\"])" 2>/dev/null) $([ -f /etc/container-apps/marine-signalk-server-container/symphony.override.yml ] && [ -f /etc/systemd/system/marine-signalk-server-container.service.d/symphony.conf ] && echo override) $(grep -q "^Groups:.* 988 " /proc/$(pgrep -f "^node /home/node/signalk" | head -1)/status 2>/dev/null && echo gid988)')
[[ "$out" == "active 2."*" override gid988" ]] && say ok signalk "$out (healthcheck override installed, i2c gid in the SignalK process)" || say FAIL signalk "got '$out' (want: active <version> override gid988)"

out=$(r "$HOST" 'systemctl is-active telegraf chrony boat-heartbeat.timer signalk-ble-check.timer marine-signalk-server-container marine-questdb-container marine-grafana-container halos-core-containers | paste -sd" "')
[ "$out" = "active active active active active active active active" ] && say ok services "8 active" || say FAIL services "telegraf chrony heartbeat.timer ble-check.timer signalk questdb grafana core: $out"

out=$(r "$HOST" 'echo $(systemctl is-enabled marine-avnav-container marine-opencpn-container 2>&1 | paste -sd,) $(systemctl is-active marine-avnav-container marine-opencpn-container | paste -sd,) influxdb:$(dpkg-query -W -f="${db:Status-Status}" marine-influxdb-container 2>/dev/null || echo absent)')
[ "$out" = "disabled,disabled inactive,inactive influxdb:absent" ] && say ok staydown "avnav opencpn disabled+inactive; influxdb app absent" || say FAIL staydown "$out"

out=$(r "$HOST" 'journalctl -t boat-heartbeat -n 1 --no-pager -o cat')
case "$out" in *"ping ok"*) say ok heartbeat "$out" ;; *) say FAIL heartbeat "${out:-no heartbeat log yet}" ;; esac

# A container with no (healthy)/(unhealthy) word never gets watched by
# autoheal at all — that gap is the whole reason this line exists.
out=$(r "$HOST" 'docker ps --format "{{.Names}} {{.Status}}"' | grep -v '(healthy)' | tr '\n' ';')
[ -z "$out" ] && say ok containers "all report (healthy)" || say FAIL containers "no/bad health: ${out%;}"

out=$(r "$HOST" 'curl -s -m 10 "127.0.0.1:9000/exec?query=select%20count()%20from%20cpu" | python3 -c "import json,sys; print(json.load(sys.stdin)[\"dataset\"][0][0])" 2>/dev/null; curl -s -m 10 "127.0.0.1:9000/exec?query=select%20max(ts)%20from%20signalk" | python3 -c "
import json,sys,datetime; t=json.load(sys.stdin)[\"dataset\"][0][0]
print(int((datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(t.replace(\"Z\",\"+00:00\"))).total_seconds()))" 2>/dev/null' | paste -sd" ")
rows=${out%% *}; age=${out##* }
[ "${rows:-0}" -gt 0 ] 2>/dev/null && [ "${age:-99999}" -lt 600 ] 2>/dev/null && say ok questdb "telegraf cpu rows $rows; newest signalk row ${age} s old" || say FAIL questdb "cpu rows ${rows:-none}, newest signalk row ${age:-none} s old (want >0 and <600)"

code=$(r "$HOST" "curl -s -m 10 -o /dev/null -w '%{http_code}' 127.0.0.1:8090/v1/health")
[ "$code" = 200 ] && say ok ntfy "health 200" || say FAIL ntfy "http ${code:-none}"

out=$(r "$HOST" "echo \$(curl -sk -m 15 --resolve signalk.$DOMAIN:4430:127.0.0.1 -o /dev/null -w '%{http_code}' https://signalk.$DOMAIN:4430/signalk) \$(openssl s_client -connect 127.0.0.1:443 </dev/null 2>/dev/null | openssl x509 -noout -ext subjectAltName | grep -c signalk.$DOMAIN)")
[ "$out" = "200 1" ] && say ok front "Traefik :4430 -> SignalK 200; device cert has signalk.$DOMAIN" || say FAIL front "http/san: $out (want: 200 1)"

out=$(r "$HOST" 'free -m | awk "/Mem:/{print \$7}"; awk "/SwapTotal/{t=\$2} /SwapFree/{f=\$2} END{print int((t-f)/1024)}" /proc/meminfo' | paste -sd" ")
avail=${out%% *}; swap=${out##* }
[ "${avail:-0}" -ge 150 ] 2>/dev/null && say ok mem "${avail} MB available, ${swap} MB swap used (2 GB bench cannot hold the databases; the 4 GB boat can)" || say FAIL mem "${avail:-?} MB available, ${swap:-?} MB swap used"

out=$(scripts/dns_cutover.sh status 2>&1 | tr '\n' ' ')
[[ "$out" == *"symphony-pi "*"<- current"* && "$out" == *"symphony-halos "* ]] && say ok dns "$out" || say FAIL dns "$out"

exit $rc
