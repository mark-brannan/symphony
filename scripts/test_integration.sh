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
cd "$(git rev-parse --show-toplevel)"

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
  code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:3001/signalk)
  [ "$code" = "200" ]
}

signalk_admin_ui_reachable() {
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:3001/admin/)
  [ "$code" = "200" ]
}

signalk_rejects_bad_login() {
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:3001/signalk/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username":"captain","password":"definitely-not-the-password"}')
  [ "$code" = "401" ]
}

signalk_captain_login_and_dashboard() {
  local captain_password token code
  captain_password=$(sops --decrypt --extract '["signalk_captain_password"]' secrets/symphony.sops.yaml 2>/dev/null) || return 1
  token=$(curl -s -X POST http://localhost:3001/signalk/v1/auth/login \
    -H "Content-Type: application/json" \
    -d "{\"username\":\"captain\",\"password\":\"${captain_password}\"}" | \
    python3 -c 'import json,sys; print(json.load(sys.stdin).get("token",""))' 2>/dev/null)
  [ -n "$token" ] || return 1
  # A real protected admin-API call, not just "did we get a token back".
  code=$(curl -s -o /dev/null -w '%{http_code}' \
    -H "Authorization: Bearer ${token}" \
    http://localhost:3001/skServer/security/users)
  [ "$code" = "200" ]
}

grafana_reachable() {
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/login)
  [ "$code" = "200" ]
}

grafana_admin_login() {
  local admin_user admin_password code
  admin_user=$(sops --decrypt --extract '["grafana_superadmin_user"]' secrets/symphony.sops.yaml 2>/dev/null) || return 1
  admin_password=$(sops --decrypt --extract '["grafana_superadmin_password"]' secrets/symphony.sops.yaml 2>/dev/null) || return 1
  code=$(curl -s -o /dev/null -w '%{http_code}' -u "${admin_user}:${admin_password}" http://localhost:3000/api/org)
  [ "$code" = "200" ]
}

grafana_rejects_default_admin_admin() {
  # Regression guard: the built-in superadmin account defaults to
  # admin:admin on a fresh volume. This must never authenticate on a
  # provisioned host -- if it does, GF_SECURITY_ADMIN_PASSWORD wasn't
  # applied (see RUNBOOK.md's rotating-a-secret section).
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' -u "admin:admin" http://localhost:3000/api/org)
  [ "$code" = "401" ]
}

influxdb_reachable() {
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8086/health)
  [ "$code" = "200" ]
}

check "SignalK: /signalk endpoint reachable"        signalk_reachable
check "SignalK: admin UI reachable"                 signalk_admin_ui_reachable
check "SignalK: rejects bad login"                  signalk_rejects_bad_login
check "SignalK: captain login + dashboard API call" signalk_captain_login_and_dashboard
check "Grafana: login page reachable"               grafana_reachable
check "Grafana: admin login works"                  grafana_admin_login
check "Grafana: default admin:admin is rejected"    grafana_rejects_default_admin_admin
check "InfluxDB: health endpoint reachable"          influxdb_reachable

echo
echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
