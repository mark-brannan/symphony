#!/usr/bin/env bash
# Smoke/integration checks against the running stack. Not a substitute for
# real coverage -- just enough to catch "the containers came up but the
# thing everyone actually cares about is broken" before it's discovered
# by hand.
#
# Requires: the stack already running (`docker compose up -d`),
# `secrets/symphony.sops.yaml` decryptable (age key present), `sops`,
# `curl`, `python3`.
set -uo pipefail
cd "$(git rev-parse --show-toplevel)" || exit 1

# Published host ports are resolved from compose, never hardcoded. When
# 74525cf swapped SignalK and Grafana between 3000 and 3001, this script kept
# its old numbers and quietly tested each service against the other one --
# including the admin:admin regression guard, which proves nothing when it's
# pointed at SignalK. `docker compose port` reports what is actually
# published, so the next swap can't strand these checks the same way.
host_port() {
  local svc="$1" container_port="$2" published
  published=$(docker compose port "$svc" "$container_port" 2>/dev/null) || return 1
  [ -n "$published" ] || return 1
  printf '%s\n' "${published##*:}"
}

require_port() {
  local svc="$1" container_port="$2" port
  if ! port=$(host_port "$svc" "$container_port"); then
    echo "FATAL: can't resolve the published port for '${svc}' -- is the stack up (docker compose up -d)?" >&2
    exit 1
  fi
  printf '%s\n' "$port"
}

SIGNALK_PORT=$(require_port signalk 3000)
GRAFANA_PORT=$(require_port grafana 3000)
INFLUXDB_PORT=$(require_port influxdb 8086)

pass=0
fail=0

check() {
  local name="$1"; shift
  if "$@"; then
    echo "PASS: $name"
    pass=$((pass + 1))
  else
    echo "FAIL: $name"
    fail=$((fail + 1))
  fi
}

signalk_reachable() {
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:${SIGNALK_PORT}/signalk")
  [ "$code" = "200" ]
}

signalk_admin_ui_reachable() {
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:${SIGNALK_PORT}/admin/")
  [ "$code" = "200" ]
}

signalk_rejects_bad_login() {
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "http://localhost:${SIGNALK_PORT}/signalk/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"captain","password":"definitely-not-the-password"}')
  [ "$code" = "401" ]
}

signalk_captain_login_and_dashboard() {
  local captain_password token code
  captain_password=$(sops --decrypt --extract '["signalk_captain_password"]' secrets/symphony.sops.yaml 2>/dev/null) || return 1
  token=$(curl -s -X POST "http://localhost:${SIGNALK_PORT}/signalk/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"captain\",\"password\":\"${captain_password}\"}" | \
    python3 -c 'import json,sys; print(json.load(sys.stdin).get("token",""))' 2>/dev/null)
  [ -n "$token" ] || return 1
  # A real protected admin-API call, not just "did we get a token back".
  code=$(curl -s -o /dev/null -w '%{http_code}' \
    -H "Authorization: Bearer ${token}" \
    "http://localhost:${SIGNALK_PORT}/skServer/security/users")
  [ "$code" = "200" ]
}

grafana_reachable() {
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:${GRAFANA_PORT}/login")
  [ "$code" = "200" ]
}

grafana_admin_login() {
  local admin_user admin_password code
  admin_user=$(sops --decrypt --extract '["grafana_superadmin_user"]' secrets/symphony.sops.yaml 2>/dev/null) || return 1
  admin_password=$(sops --decrypt --extract '["grafana_superadmin_password"]' secrets/symphony.sops.yaml 2>/dev/null) || return 1
  code=$(curl -s -o /dev/null -w '%{http_code}' -u "${admin_user}:${admin_password}" "http://localhost:${GRAFANA_PORT}/api/org")
  [ "$code" = "200" ]
}

grafana_rejects_default_admin_admin() {
  # Regression guard: the built-in superadmin account defaults to
  # admin:admin on a fresh volume. This must never authenticate on a
  # provisioned host -- if it does, GF_SECURITY_ADMIN_PASSWORD wasn't
  # applied (see RUNBOOK.md's rotating-a-secret section).
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' -u "admin:admin" "http://localhost:${GRAFANA_PORT}/api/org")
  [ "$code" = "401" ]
}

grafana_captain_login() {
  local captain_password code
  captain_password=$(sops --decrypt --extract '["grafana_captain_password"]' secrets/symphony.sops.yaml 2>/dev/null) || return 1
  code=$(curl -s -o /dev/null -w '%{http_code}' -u "captain:${captain_password}" "http://localhost:${GRAFANA_PORT}/api/org")
  [ "$code" = "200" ]
}

influxdb_reachable() {
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:${INFLUXDB_PORT}/health")
  [ "$code" = "200" ]
}

influxdb_captain_login() {
  local captain_password code
  captain_password=$(sops --decrypt --extract '["influxdb_captain_password"]' secrets/symphony.sops.yaml 2>/dev/null) || return 1
  code=$(curl -s -o /dev/null -w '%{http_code}' -X POST -u "captain:${captain_password}" "http://localhost:${INFLUXDB_PORT}/api/v2/signin")
  [ "$code" = "204" ]
}

influxdb_signalk_token_can_write() {
  local token code
  token=$(sops --decrypt --extract '["influxdb_signalk_token"]' secrets/symphony.sops.yaml 2>/dev/null) || return 1
  code=$(curl -s -o /dev/null -w '%{http_code}' -X POST \
    "http://localhost:${INFLUXDB_PORT}/api/v2/write?org=darkstarllc&bucket=symphony&precision=s" \
    -H "Authorization: Token ${token}" --data-raw "integration_test,source=ci value=1")
  [ "$code" = "204" ]
}

influxdb_signalk_token_is_scoped() {
  # Regression guard: this token is meant to be read+write on one bucket
  # only, not an operator token. InfluxDB's list endpoints (users,
  # buckets) don't 401/403 on insufficient scope -- they silently filter
  # to what the token can see, which isn't a reliable "denied" signal. A
  # genuinely admin-only action is: deleting *any* authorization requires
  # write:authorizations, which this token must not have.
  local token operator_token some_auth_id code
  token=$(sops --decrypt --extract '["influxdb_signalk_token"]' secrets/symphony.sops.yaml 2>/dev/null) || return 1
  operator_token=$(sops --decrypt --extract '["influxdb_operator_token"]' secrets/symphony.sops.yaml 2>/dev/null) || return 1
  some_auth_id=$(curl -s -H "Authorization: Token ${operator_token}" "http://localhost:${INFLUXDB_PORT}/api/v2/authorizations" | \
    python3 -c 'import json,sys; print(json.load(sys.stdin)["authorizations"][0]["id"])' 2>/dev/null) || return 1
  code=$(curl -s -o /dev/null -w '%{http_code}' -X DELETE \
    -H "Authorization: Token ${token}" "http://localhost:${INFLUXDB_PORT}/api/v2/authorizations/${some_auth_id}")
  [ "$code" = "401" ] || [ "$code" = "403" ]
}

grafana_influxdb_datasource_healthy() {
  local admin_user admin_password ds_uid status
  admin_user=$(sops --decrypt --extract '["grafana_superadmin_user"]' secrets/symphony.sops.yaml 2>/dev/null) || return 1
  admin_password=$(sops --decrypt --extract '["grafana_superadmin_password"]' secrets/symphony.sops.yaml 2>/dev/null) || return 1
  ds_uid=$(curl -s -u "${admin_user}:${admin_password}" "http://localhost:${GRAFANA_PORT}/api/datasources" | \
    python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["uid"])' 2>/dev/null) || return 1
  status=$(curl -s -u "${admin_user}:${admin_password}" "http://localhost:${GRAFANA_PORT}/api/datasources/uid/${ds_uid}/health" | \
    python3 -c 'import json,sys; print(json.load(sys.stdin).get("status",""))' 2>/dev/null)
  [ "$status" = "OK" ]
}

check "SignalK: /signalk endpoint reachable"        signalk_reachable
check "SignalK: admin UI reachable"                 signalk_admin_ui_reachable
check "SignalK: rejects bad login"                  signalk_rejects_bad_login
check "SignalK: captain login + dashboard API call" signalk_captain_login_and_dashboard
check "Grafana: login page reachable"               grafana_reachable
check "Grafana: admin login works"                  grafana_admin_login
check "Grafana: default admin:admin is rejected"    grafana_rejects_default_admin_admin
check "Grafana: captain login works"                grafana_captain_login
check "InfluxDB: health endpoint reachable"          influxdb_reachable
check "InfluxDB: captain login works"               influxdb_captain_login
check "InfluxDB: signalk token can write"           influxdb_signalk_token_can_write
check "InfluxDB: signalk token is properly scoped"  influxdb_signalk_token_is_scoped
check "Grafana->InfluxDB datasource is healthy"     grafana_influxdb_datasource_healthy

echo
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
