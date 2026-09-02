#!/usr/bin/env bash
# Before the HALOS card leaves home: check the build against the boat card.
#
#   scripts/halos_preflight.sh [host]      default host: symphony-halos
#
# Prints one `ok`/`FAIL` line per item and exits non-zero if any failed.
# Run from a tailnet machine; needs ssh to both the host and symphony-pi.
# Nothing can be fetched at the boat, so every line must be ok.
# shellcheck disable=SC2015,SC2016
set -uo pipefail

HOST="${1:-symphony-halos}"
BOAT=symphony-pi
D=/var/lib/container-apps/marine-signalk-server-container/data/data
rc=0
say() { printf '%-5s %-10s %s\n' "$1" "$2" "$3"; [ "$1" = ok ] || rc=1; }
r() { ssh -o BatchMode=yes -o ConnectTimeout=15 "pi@$1" "$2" 2>/dev/null; }
deps() { r "$1" "python3 -c 'import json; print(*sorted(json.load(open(\"$2\"))[\"dependencies\"]), sep=\"\\n\")'"; }
# name + enabled state per plugin, not just filename presence — a filename
# match hides an enabled/disabled mismatch.
cfgs() { r "$1" "for f in $2/plugin-config-data/*.json; do python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(sys.argv[1].rsplit(\"/\",1)[-1], d.get(\"enabled\"))' \"\$f\"; done | sort"; }
# disabled on HALOS only, by design — see the plugin-container decision in halos-swap-plan.md
EXPECT_NAMES="signalk-container signalk-to-influxdb2 signalk-to-influxdb-v2-buffer"
EXPECT_DIFF='signalk-container\.json|signalk-to-influxdb2\.json|signalk-to-influxdb-v2-buffer\.json'

out=$(r "$HOST" 'echo $(hostname) $(hostname -d) $(cut -d= -f2 /run/halos/domain.env) $(tailscale status --self --peers=false | awk "{print \$2}")')
[ "$out" = "signalk symphony.dark-star-llc.com signalk.symphony.dark-star-llc.com symphony-halos" ] && say ok host "$out" || say FAIL host "${out:-no answer}"

out=$(r "$HOST" 'echo $(grep -cE "mcp2515-can0|enable_uart=1|i2c_arm=on|spi=on" /boot/firmware/config.txt) $(grep -o "cgroup_enable=memory" /boot/firmware/cmdline.txt) $(grep -o "regdom=US" /boot/firmware/cmdline.txt) $(grep -ow memory /sys/fs/cgroup/cgroup.controllers) $(ls /dev/serial0 /dev/i2c-1 2>/dev/null | wc -l)')
[ "$out" = "4 cgroup_enable=memory regdom=US memory 2" ] && say ok boot "overlays cgroup regdom serial0 i2c-1" || say FAIL boot "got: $out (want: 4 cgroup_enable=memory regdom=US memory 2)"

out=$(r "$HOST" 'nmcli -t -f NAME con show | grep -cE "^(Symphony|Halos-AP)$"; nmcli -g 802-11-wireless.ssid con show Halos-AP')
[ "$(echo "$out" | tr '\n' ' ')" = "2 SignalK " ] && say ok wifi "Symphony profile, Halos-AP ssid SignalK" || say FAIL wifi "$(echo "$out" | tr '\n' ' ')"

d=$(diff <(deps "$BOAT" /home/pi/.signalk/package.json) <(deps "$HOST" "$D/package.json") | grep -c '^[<>]')
cfgdiff=$(diff <(cfgs "$BOAT" /home/pi/.signalk) <(cfgs "$HOST" "$D"))
c=$(echo "$cfgdiff" | grep '^[<>]' | grep -cvE "$EXPECT_DIFF")
# Counting only *unexpected* diffs passes when B3c's disable step was skipped
# and nothing differs at all, so require each expected difference to be there.
absent=
for p in $EXPECT_NAMES; do
  echo "$cfgdiff" | grep -q "$p" || absent="$absent $p"
done
l=$(r "$HOST" "ls $D/local-plugins" | tr '\n' ' ')
n=$(r "$HOST" 'curl -s localhost:3000/skServer/plugins' | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))' 2>/dev/null)
if [ "$d" = 0 ] && [ "$c" = 0 ] && [ -z "$absent" ] && [[ "$l" == *bt-sensors-plugin-sk* && "$l" == *signalk-plugin-watchdog* ]] && [ "${n:-0}" -gt 50 ]; then
  say ok plugins "package.json matches; plugin-config-data matches except the 3 expected HALOS-disabled; local-plugins: $l; $n loaded"
else
  say FAIL plugins "package.json diff lines $d, unexpected config diff: $(echo "$cfgdiff" | grep '^[<>]' | grep -vE "$EXPECT_DIFF"), expected-but-absent:${absent:- none}, local-plugins: ${l:-none}, loaded ${n:-0}"
fi

out=$(r "$HOST" 'systemctl is-active telegraf chrony boat-heartbeat.timer signalk-ble-check.timer marine-signalk-server-container marine-questdb-container marine-grafana-container halos-core-containers | sort | uniq -c | tr -s " " | tr "\n" ";"')
[ "$out" = " 8 active;" ] && say ok services "8 active" || say FAIL services "$out"

out=$(r "$HOST" 'systemctl is-enabled marine-avnav-container marine-opencpn-container marine-influxdb-container 2>&1 | tr "\n" " "')
case "$out" in *enabled*|*active*) say FAIL disabled "$out" ;; *) say ok disabled "avnav opencpn influxdb: $out" ;; esac

out=$(r "$HOST" 'journalctl -t boat-heartbeat -n 1 --no-pager -o cat')
case "$out" in *"ping ok"*) say ok heartbeat "$out" ;; *) say FAIL heartbeat "${out:-no heartbeat log}" ;; esac

rows=$(r "$HOST" "curl -s 'localhost:9000/exec?query=select%20count()%20from%20cpu'" | python3 -c 'import json,sys; print(json.load(sys.stdin)["dataset"][0][0])' 2>/dev/null)
[ "${rows:-0}" -gt 0 ] 2>/dev/null && say ok questdb "cpu rows $rows" || say FAIL questdb "no telegraf rows"

code=$(r "$HOST" "curl -s -o /dev/null -w '%{http_code}' localhost:8090/v1/health")
[ "$code" = 200 ] && say ok ntfy "health 200" || say FAIL ntfy "http ${code:-none}"

out=$("$(dirname "$0")/dns_cutover.sh" status 2>&1 | tr '\n' ' ')
[[ "$out" == *"symphony-pi "*"<- current"* && "$out" == *"symphony-halos "* ]] && say ok dns "$out" || say FAIL dns "$out"

exit $rc
