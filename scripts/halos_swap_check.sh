#!/usr/bin/env bash
# Check every core boat function on a card, from a tailnet machine.
#
#   scripts/halos_swap_check.sh [host]      default host: symphony-halos
#
# One `ok`/`FAIL` line per function, non-zero exit if any failed. Works on
# either card. Run it on the boat card before the swap (the baseline), on the
# HALOS card after it, and again after a rollback. A line that FAILs in the
# baseline and FAILs after the swap is a boat problem, not a card problem.
# Sends one ntfy message to symphony-alarms so the phone side is exercised.
# shellcheck disable=SC2015,SC2016
set -uo pipefail

HOST="${1:-symphony-halos}"
cd "$(dirname "$0")/.." || exit 1
DOMAIN=$(sops --decrypt --extract '["boat_domain"]' secrets/symphony.sops.yaml)
rc=0
say() { printf '%-5s %-10s %s\n' "$1" "$2" "$3"; [ "$1" = ok ] || rc=1; }
r() { ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 "pi@${HOST}" "$@" 2>/dev/null; }
sk() { r "curl -s -m 15 127.0.0.1:3000/signalk/v1/api/vessels/self/$1"; }
age_of() { python3 -c 'import sys,datetime; t=sys.argv[1]; print(int((datetime.datetime.now(datetime.timezone.utc)-datetime.datetime.fromisoformat(t.replace("Z","+00:00"))).total_seconds()))' "$1" 2>/dev/null; }

out=$(r 'echo $(hostname) $(curl -s -m 10 127.0.0.1:3000/signalk | python3 -c "import json,sys; print(json.load(sys.stdin)[\"server\"][\"version\"])" 2>/dev/null) up=$(cut -d. -f1 /proc/uptime)s')
[[ "$out" == "signalk 2."* ]] && say ok signalk "$out" || say FAIL signalk "${out:-no answer from $HOST}"

out=$(r 'ip -br a | grep -E "^(eth0|can0) "' | awk '{print $1, ($1=="can0" ? $2 : $3)}' | tr '\n' ' ')
case "$out" in *"eth0 192.168.8.240"*"can0 UP"*) say ok lan "$out" ;; *) say FAIL lan "${out:-no answer} (want eth0 192.168.8.240/24 and can0 UP)" ;; esac

out=$(r "curl -s -m 20 127.0.0.1:3000/signalk/v1/api/vessels/self" | python3 -c '
import json,sys
d=json.load(sys.stdin); best=("","")
def walk(o,p):
    global best
    if isinstance(o,dict):
        if "timestamp" in o and str(o.get("$source","")).startswith("n2k-can0"):
            if o["timestamp"]>best[0]: best=(o["timestamp"],p)
            return
        for k,v in o.items(): walk(v,p+"/"+k)
walk(d,""); print(best[0], best[1])' 2>/dev/null)
age=$(age_of "${out%% *}")
[ "${age:-9999}" -lt 60 ] 2>/dev/null && say ok n2k "newest n2k-can0 value ${age} s old (${out##* })" || say FAIL n2k "no n2k-can0 value under 60 s old (newest: ${out:-none})"

est=$(r 'ss -tn | grep -E "192.168.8.107:8883" | awk "{print \$1}"' | head -1)
keys=$(sk electrical | python3 -c 'import json,sys; print(" ".join(sorted(json.load(sys.stdin))))' 2>/dev/null)
if [ "$est" = ESTAB ] && [[ "$keys" == *batteries* ]]; then say ok victron "ESTAB 192.168.8.107:8883; electrical: $keys"; else say FAIL victron "mqtt=${est:-none} electrical: ${keys:-none} (Cerbo MQTT down on the boat card since 2026-09-01: compare with the baseline)"; fi

conf=$(r 'for f in /home/pi/.signalk/plugin-config-data/bt-sensors-plugin-sk.json /var/lib/container-apps/marine-signalk-server-container/data/data/plugin-config-data/bt-sensors-plugin-sk.json; do [ -f $f ] && python3 -c "import json,sys; print(len(json.load(open(sys.argv[1])).get(\"configuration\",{}).get(\"peripherals\",[])))" $f && break; done')
out=$(sk electrical/batteries | python3 -c '
import json,sys,datetime
d=json.load(sys.stdin); now=datetime.datetime.now(datetime.timezone.utc); ages=[]
for k,v in d.items():
    t=v.get("voltage",{}).get("timestamp")
    if t: ages.append(int((now-datetime.datetime.fromisoformat(t.replace("Z","+00:00"))).total_seconds()))
print(len(ages), min(ages) if ages else -1)' 2>/dev/null)
n=${out%% *}; age=${out##* }
if [ "${n:-0}" -ge 1 ] && [ "$age" -ge 0 ] && [ "$age" -lt 600 ]; then say ok ble "$n of ${conf:-?} configured sensors publishing voltage, newest ${age} s"; else say FAIL ble "${n:-0} of ${conf:-?} configured sensors publishing voltage; allow 10 min after boot"; fi

out=$(r 'journalctl -t boat-heartbeat -n 1 --no-pager -o cat')
case "$out" in *"ping ok"*) say ok heartbeat "$out" ;; *) say FAIL heartbeat "${out:-no heartbeat log}" ;; esac

code=$(r "curl -s -m 10 -o /dev/null -w '%{http_code}' -d 'swap check on ${HOST}' 127.0.0.1:8090/symphony-alarms")
[ "$code" = 200 ] && say ok ntfy "sent to symphony-alarms; check the phone" || say FAIL ntfy "http ${code:-none}"

out=$(r "curl -s -m 30 '127.0.0.1:9000/exec?query=select%20ts%20from%20signalk%20limit%20-1'" | python3 -c 'import json,sys; print(json.load(sys.stdin)["dataset"][0][0])' 2>/dev/null)
age=$(age_of "$out")
if [ "${age:-9999}" -lt 600 ] 2>/dev/null; then say ok questdb "newest signalk history row ${age} s old"; elif [ -z "$out" ]; then say FAIL questdb "no answer in 30 s (the boat card's QuestDB is known to be too loaded to answer; compare with the baseline)"; else say FAIL questdb "newest signalk history row ${out} (want <600 s old)"; fi

out=$(r 'for d in /dev/serial0 /dev/i2c-1; do [ -e $d ] && echo "$d" || echo "MISSING:$d"; done' | tr '\n' ' ')
case "$out" in *MISSING*|"") say FAIL devices "${out:-no answer}" ;; *) say ok devices "$out" ;; esac

out=$(sk environment/inside | python3 -c 'import json,sys; print(" ".join(sorted(json.load(sys.stdin))))' 2>/dev/null)
[[ "$out" == *temperature* ]] && say ok bme680 "inside: $out" || say FAIL bme680 "inside: ${out:-nothing yet}; allow 10 min after boot"

out=$(r "for p in 4430 443; do c=\$(curl -sk -m 15 --resolve signalk.${DOMAIN}:\$p:127.0.0.1 -o /dev/null -w '%{http_code}' https://signalk.${DOMAIN}:\$p/signalk); case \$c in 200|302) echo \"\$p \$c\"; break;; esac; done")
[ -n "$out" ] && say ok front "https signalk.${DOMAIN} :${out} -> SignalK" || say FAIL front "no HTTPS front door answered 200/302 on :4430 (Traefik) or :443 (Caddy) for signalk.${DOMAIN}"

exit $rc
