#!/usr/bin/env bash
# Check every core boat function on a card, from a tailnet machine.
#
#   scripts/halos_swap_check.sh [host]      default host: symphony-halos
#
# Prints one `ok`/`FAIL` line per function and exits non-zero if any failed.
# Works on either card (native or HALOS); use it for the baseline before the
# swap, the check after it, and the check after a rollback. Sends one ntfy
# message to symphony-alarms so the phone side is exercised too.
# shellcheck disable=SC2015,SC2016
set -uo pipefail

HOST="${1:-symphony-halos}"
rc=0
say() { printf '%-5s %-10s %s\n' "$1" "$2" "$3"; [ "$1" = ok ] || rc=1; }
r() { ssh -o BatchMode=yes -o ConnectTimeout=15 "pi@${HOST}" "$@" 2>/dev/null; }
sk() { r "curl -s localhost:3000/signalk/v1/api/vessels/self/$1"; }

out=$(r 'ip -br a | grep -E "^(eth0|can0) "' | awk '{print $1, ($1=="can0" ? $2 : $3)}' | tr '\n' ' ')
case "$out" in *"eth0 192.168.8.240"*"can0 UP"*) say ok lan "$out" ;; *) say FAIL lan "${out:-no answer from $HOST}" ;; esac

out=$(sk navigation/position | python3 -c '
import json,sys,datetime
d=json.load(sys.stdin); ts=datetime.datetime.fromisoformat(d["timestamp"].replace("Z","+00:00"))
age=(datetime.datetime.now(datetime.timezone.utc)-ts).total_seconds()
print(d["$source"], int(age))' 2>/dev/null)
case "$out" in n2k-can0*) say ok n2k "position from ${out% *}, ${out##* } s old" ;; *) say FAIL n2k "${out:-no position}" ;; esac

est=$(r 'ss -tn | grep -E "192.168.8.107:8883" | awk "{print \$1}"' | head -1)
keys=$(sk electrical | python3 -c 'import json,sys; print(" ".join(sorted(json.load(sys.stdin))))' 2>/dev/null)
if [ "$est" = ESTAB ] && [[ "$keys" == *batteries* ]]; then say ok victron "ESTAB 192.168.8.107:8883; electrical: $keys"; else say FAIL victron "mqtt=${est:-none} electrical: ${keys:-none}"; fi

out=$(sk electrical/batteries | python3 -c '
import json,sys,datetime
d=json.load(sys.stdin); now=datetime.datetime.now(datetime.timezone.utc); ages=[]
for k,v in d.items():
    t=v.get("voltage",{}).get("timestamp")
    if t: ages.append(int((now-datetime.datetime.fromisoformat(t.replace("Z","+00:00"))).total_seconds()))
print(len(ages), min(ages) if ages else -1)' 2>/dev/null)
n=${out%% *}; age=${out##* }
if [ "${n:-0}" -ge 5 ] && [ "$age" -ge 0 ] && [ "$age" -lt 600 ]; then say ok ble "$n batteries, newest ${age} s"; else say FAIL ble "${n:-0} batteries with a voltage timestamp (want 5); allow 10 min after boot"; fi

out=$(r 'journalctl -t boat-heartbeat -n 1 --no-pager -o cat')
case "$out" in *"ping ok"*) say ok heartbeat "$out" ;; *) say FAIL heartbeat "${out:-no heartbeat log}" ;; esac

code=$(r "curl -s -o /dev/null -w '%{http_code}' -d 'swap check from \$(hostname)' localhost:8090/symphony-alarms")
[ "$code" = 200 ] && say ok ntfy "sent to symphony-alarms; check the phone" || say FAIL ntfy "http $code"

rows=$(r "curl -s 'localhost:9000/exec?query=select%20count()%20from%20%27navigation.position%27'" | python3 -c 'import json,sys; print(json.load(sys.stdin)["dataset"][0][0])' 2>/dev/null)
[ "${rows:-0}" -gt 0 ] 2>/dev/null && say ok questdb "navigation.position rows $rows" || say FAIL questdb "no rows"

out=$(r 'ls /dev/serial0 /dev/i2c-1 2>&1' | tr '\n' ' ')
case "$out" in *serial0*i2c-1*) [[ "$out" == *"No such"* ]] && say FAIL devices "$out" || say ok devices "$out" ;; *) say FAIL devices "$out" ;; esac

out=$(sk environment/inside | python3 -c 'import json,sys; print(" ".join(sorted(json.load(sys.stdin))))' 2>/dev/null)
[ -n "$out" ] && say ok bme680 "inside: $out" || say FAIL bme680 "no environment.inside yet; allow 10 min after boot"

exit $rc
