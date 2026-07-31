#!/usr/bin/env bash
# Idempotent InfluxDB provisioning: initial setup (org/bucket/admin user),
# a captain login, and scoped tokens for the services that need one.
#
# Token caveat (InfluxDB's own design, not a limitation of this script):
# a token's secret value is only ever shown once, at creation. This script
# can converge *existence* (skip creating a same-described token that's
# already there) but can't converge *value* the way the Grafana password
# reset can -- if a token is lost from secrets/symphony.sops.yaml, the fix
# is to revoke the old authorization and mint + store a new one, not to
# "reset" it in place.
#
# Requires: the stack running, sops + age key, curl, python3.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

INFLUX_URL="${INFLUX_URL:-http://localhost:8086}"
SECRETS_FILE="secrets/symphony.sops.yaml"
ORG_NAME="darkstarllc"
BUCKET_NAME="symphony"

secret() { sops --decrypt --extract "[\"$1\"]" "$SECRETS_FILE" 2>/dev/null || true; }
set_secret() { sops --set "[\"$1\"] \"$2\"" "$SECRETS_FILE"; }

setup_allowed=$(curl -s "${INFLUX_URL}/api/v2/setup" | python3 -c 'import json,sys; print(json.load(sys.stdin)["allowed"])')

if [ "$setup_allowed" = "True" ]; then
  echo "InfluxDB unprovisioned -- running initial setup..."
  init_user=$(secret influxdb_init_username)
  init_pass=$(secret influxdb_init_password)
  resp=$(curl -s -X POST "${INFLUX_URL}/api/v2/setup" -H "Content-Type: application/json" \
    -d "{\"username\":\"${init_user}\",\"password\":\"${init_pass}\",\"org\":\"${ORG_NAME}\",\"bucket\":\"${BUCKET_NAME}\",\"retentionPeriodSeconds\":0}")
  operator_token=$(echo "$resp" | python3 -c 'import json,sys; print(json.load(sys.stdin)["auth"]["token"])')
  org_id=$(echo "$resp" | python3 -c 'import json,sys; print(json.load(sys.stdin)["org"]["id"])')
  bucket_id=$(echo "$resp" | python3 -c 'import json,sys; print(json.load(sys.stdin)["bucket"]["id"])')
  set_secret influxdb_operator_token "$operator_token"
  set_secret influxdb_org_id "$org_id"
  set_secret influxdb_bucket_id "$bucket_id"
  echo "setup complete: org=${org_id} bucket=${bucket_id}"
else
  echo "InfluxDB already provisioned."
fi

operator_token=$(secret influxdb_operator_token)
org_id=$(secret influxdb_org_id)
bucket_id=$(secret influxdb_bucket_id)
auth=(-H "Authorization: Token ${operator_token}")

# --- captain user + org membership ---
captain_id=$(curl -s "${auth[@]}" "${INFLUX_URL}/api/v2/users" | \
  python3 -c 'import json,sys; d=json.load(sys.stdin); print(next((u["id"] for u in d.get("users",[]) if u["name"]=="captain"), ""))')

if [ -z "$captain_id" ]; then
  echo "creating influxdb user 'captain'..."
  captain_pass=$(secret influxdb_captain_password)
  captain_id=$(curl -s "${auth[@]}" -X POST "${INFLUX_URL}/api/v2/users" \
    -H "Content-Type: application/json" -d '{"name":"captain","status":"active"}' | \
    python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
  curl -s "${auth[@]}" -X POST "${INFLUX_URL}/api/v2/users/${captain_id}/password" \
    -H "Content-Type: application/json" -d "{\"password\":\"${captain_pass}\"}" >/dev/null
  curl -s "${auth[@]}" -X POST "${INFLUX_URL}/api/v2/orgs/${org_id}/members" \
    -H "Content-Type: application/json" -d "{\"id\":\"${captain_id}\"}" >/dev/null
  echo "'captain': id=${captain_id}, role=member of ${ORG_NAME}"
else
  echo "'captain' already exists (id ${captain_id})"
fi

# --- scoped tokens (create-if-missing by description; can't converge value) ---
ensure_token() {
  local description="$1" secret_key="$2" permissions_json="$3"
  local existing
  existing=$(curl -s "${auth[@]}" "${INFLUX_URL}/api/v2/authorizations?orgID=${org_id}" | \
    python3 -c "import json,sys; d=json.load(sys.stdin); print(next((a['id'] for a in d.get('authorizations',[]) if a['description']=='${description}'), ''))")
  if [ -n "$existing" ]; then
    echo "token '${description}' already exists (id ${existing}); not re-minting -- see script header re: token values."
    return
  fi
  echo "minting token '${description}'..."
  local token
  token=$(curl -s "${auth[@]}" -X POST "${INFLUX_URL}/api/v2/authorizations" \
    -H "Content-Type: application/json" \
    -d "{\"orgID\":\"${org_id}\",\"description\":\"${description}\",\"permissions\":${permissions_json}}" | \
    python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')
  set_secret "$secret_key" "$token"
  echo "stored as secrets/symphony.sops.yaml -> ${secret_key}"
}

ensure_token \
  "signalk-to-influxdb2 plugin (read+write, symphony bucket)" \
  "influxdb_signalk_token" \
  "[{\"action\":\"read\",\"resource\":{\"type\":\"buckets\",\"id\":\"${bucket_id}\",\"orgID\":\"${org_id}\"}},{\"action\":\"write\",\"resource\":{\"type\":\"buckets\",\"id\":\"${bucket_id}\",\"orgID\":\"${org_id}\"}}]"

ensure_token \
  "grafana datasource (read-only, symphony bucket)" \
  "influx_token" \
  "[{\"action\":\"read\",\"resource\":{\"type\":\"buckets\",\"id\":\"${bucket_id}\",\"orgID\":\"${org_id}\"}}]"

echo
echo "Done. If token values changed, re-run scripts/render.py and update"
echo "signalk/plugin-config-data/signalk-to-influxdb2.json's token field by hand."
