#!/usr/bin/env bash
# Point the boat's public DNS at whichever Pi is currently aboard.
#
#   scripts/dns_cutover.sh status                 show the A record and both nodes' tailnet IPs
#   scripts/dns_cutover.sh set <tailnet-node>     point the A record at that node (asks first)
#   scripts/dns_cutover.sh set <tailnet-node> -y  same, no prompt
#
# The apex record `<boat-domain>` is an A record holding a tailnet IP;
# `signalk.`, `grafana.` and `auth.` are CNAMEs to it (RUNBOOK → "SSO login",
# step 1), so one PATCH moves every name. On the boat LAN the router's own
# override answers instead and never changes: the LAN IP follows the Pi's MAC,
# and the card swap keeps the Pi.
#
# Reads `boat_domain` and `cloudflare_api_token` from secrets/symphony.sops.yaml.
# The token is the "Edit zone DNS" one Caddy uses for ACME; it can edit records
# in this zone and nothing else. Tailnet IPs come from the local
# `tailscale status --json`, so run this on a machine that is on the tailnet.
#
# Verify after `set`: `dig +short <boat-domain> @1.1.1.1` shows the new IP
# within the record's TTL (300 s).
set -euo pipefail

cd "$(dirname "$0")/.."

usage() { sed -n '2,8p' "$0"; exit 2; }

CMD="${1:-status}"
NODE="${2:-}"
YES="${3:-}"
case "$CMD" in
  status) ;;
  set) [ -n "$NODE" ] || usage ;;
  *) usage ;;
esac

for tool in sops curl python3 tailscale dig; do
  command -v "$tool" >/dev/null || { echo "missing: $tool" >&2; exit 1; }
done

DOMAIN=$(sops --decrypt --extract '["boat_domain"]' secrets/symphony.sops.yaml)
TOKEN=$(sops --decrypt --extract '["cloudflare_api_token"]' secrets/symphony.sops.yaml)
API=https://api.cloudflare.com/client/v4

cf() { # cf <method> <path> [json-body]
  local method=$1 path=$2 body=${3:-}
  curl -sf -X "$method" "${API}${path}" \
    -H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/json" \
    ${body:+--data "$body"}
}

# The token is zone-scoped, so walk up from the boat domain until a zone answers.
zone_id=""
zone_name="$DOMAIN"
while [ -n "$zone_name" ]; do
  zone_id=$(cf GET "/zones?name=${zone_name}" | python3 -c 'import json,sys; r=json.load(sys.stdin)["result"]; print(r[0]["id"] if r else "")')
  [ -n "$zone_id" ] && break
  zone_name=${zone_name#*.}
  [[ "$zone_name" == *.* ]] || zone_name=""
done
[ -n "$zone_id" ] || { echo "no Cloudflare zone found for ${DOMAIN}" >&2; exit 1; }

record=$(cf GET "/zones/${zone_id}/dns_records?type=A&name=${DOMAIN}")
record_id=$(echo "$record" | python3 -c 'import json,sys; r=json.load(sys.stdin)["result"]; print(r[0]["id"] if r else "")')
current_ip=$(echo "$record" | python3 -c 'import json,sys; r=json.load(sys.stdin)["result"]; print(r[0]["content"] if r else "")')
[ -n "$record_id" ] || { echo "no A record named ${DOMAIN} in zone ${zone_name}" >&2; exit 1; }

# tailnet name -> IPv4, from this machine's view of the tailnet
node_ip() {
  tailscale status --json | python3 -c '
import json, sys
want = sys.argv[1]
d = json.load(sys.stdin)
for n in [d["Self"]] + list(d.get("Peer", {}).values()):
    if n["HostName"] == want:
        print(next(ip for ip in n["TailscaleIPs"] if "." in ip)); break
' "$1"
}

echo "A ${DOMAIN} -> ${current_ip}   (zone ${zone_name}, public answer: $(dig +short "$DOMAIN" @1.1.1.1 | head -1))"
for n in symphony-pi symphony-halos halos-pi4; do
  ip=$(node_ip "$n" || true)
  [ -n "$ip" ] && printf '  %-16s %s%s\n' "$n" "$ip" "$([ "$ip" = "$current_ip" ] && echo '   <- current')"
done

[ "$CMD" = status ] && exit 0

new_ip=$(node_ip "$NODE" || true)
[ -n "$new_ip" ] || { echo "tailnet node ${NODE} not visible from here" >&2; exit 1; }
if [ "$new_ip" = "$current_ip" ]; then echo "already pointing at ${NODE}"; exit 0; fi

if [ "$YES" != "-y" ]; then
  read -r -p "PATCH ${DOMAIN} ${current_ip} -> ${new_ip} (${NODE})? [y/N] " ans
  [ "$ans" = y ] || exit 1
fi
cf PATCH "/zones/${zone_id}/dns_records/${record_id}" "{\"content\":\"${new_ip}\"}" >/dev/null
echo "A ${DOMAIN} -> ${new_ip}. Public resolvers follow within 300 s: dig +short ${DOMAIN} @1.1.1.1"
