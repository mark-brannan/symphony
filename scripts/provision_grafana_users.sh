#!/usr/bin/env bash
# Grafana OSS has no file-based user provisioning (confirmed by inspecting
# the image -- its real provisioning dirs are only access-control, alerting,
# dashboards, datasources, notifiers, plugins; grafana/provisioning/users/
# is never read). Users have to go through the HTTP Admin API instead, so
# this script is the equivalent of a template render for that one file
# format Grafana doesn't support. Idempotent -- safe to re-run.
#
# Requires: the stack running, sops + age key, curl, python3.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

GRAFANA_URL="${GRAFANA_URL:-http://localhost:3000}"
SECRETS_FILE="secrets/symphony.sops.yaml"

secret() { sops --decrypt --extract "[\"$1\"]" "$SECRETS_FILE"; }

admin_user=$(secret grafana_superadmin_user)
admin_pass=$(secret grafana_superadmin_password)
auth=(-u "${admin_user}:${admin_pass}")

# name, login, email, secret-key, org role
users=(
  "Captain|captain|captain@symphony.local|grafana_captain_password|Admin"
)

for entry in "${users[@]}"; do
  IFS='|' read -r name login email password_key role <<<"$entry"
  password=$(secret "$password_key")

  user_id=$(curl -s "${auth[@]}" "${GRAFANA_URL}/api/users/lookup?loginOrEmail=${login}" | \
    python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("id",""))' 2>/dev/null || true)

  if [ -z "$user_id" ]; then
    echo "creating grafana user '${login}'..."
    user_id=$(curl -s "${auth[@]}" -X POST "${GRAFANA_URL}/api/admin/users" \
      -H "Content-Type: application/json" \
      -d "{\"name\":\"${name}\",\"login\":\"${login}\",\"email\":\"${email}\",\"password\":\"${password}\"}" | \
      python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
  else
    echo "'${login}' already exists (id ${user_id}), converging password + role..."
    curl -s "${auth[@]}" -X PUT "${GRAFANA_URL}/api/admin/users/${user_id}/password" \
      -H "Content-Type: application/json" \
      -d "{\"password\":\"${password}\"}" >/dev/null
  fi

  curl -s "${auth[@]}" -X PATCH "${GRAFANA_URL}/api/org/users/${user_id}" \
    -H "Content-Type: application/json" \
    -d "{\"role\":\"${role}\"}" >/dev/null

  echo "'${login}': id=${user_id} role=${role}"
done
