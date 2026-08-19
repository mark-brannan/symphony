#!/usr/bin/env bash
# Read or validate the Tailscale tailnet policy file (the ACLs) without
# opening the admin console.
#
#   scripts/tailscale_policy.sh                  print the live policy
#   scripts/tailscale_policy.sh validate <file>  dry-run a proposed policy
#
# Uses the read-only OAuth client stored in secrets/symphony.sops.yaml, so
# it cannot apply a change — that stays a deliberate paste-and-Save at
# https://login.tailscale.com/admin/acls/file.
set -euo pipefail

cd "$(dirname "$0")/.."

CLIENT_ID=$(sops --decrypt --extract '["tailscale_oauth_client_id"]' secrets/symphony.sops.yaml)
CLIENT_SECRET=$(sops --decrypt --extract '["tailscale_oauth_client_secret"]' secrets/symphony.sops.yaml)

# --data-urlencode reads the secret from stdin-adjacent argv only within this
# process; it never reaches another process's argv.
TOKEN=$(curl -sf https://api.tailscale.com/api/v2/oauth/token \
  --data-urlencode "client_id=${CLIENT_ID}" \
  --data-urlencode "client_secret=${CLIENT_SECRET}" \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

API=https://api.tailscale.com/api/v2/tailnet/-/acl

case "${1:-get}" in
  get)
    curl -sf -H "Authorization: Bearer ${TOKEN}" -H "Accept: application/hujson" "${API}"
    ;;
  validate)
    [ -n "${2:-}" ] || { echo "usage: $0 validate <file>" >&2; exit 2; }
    # An empty JSON object and HTTP 200 means valid, sshTests included.
    curl -s -w '\nHTTP %{http_code}\n' -X POST \
      -H "Authorization: Bearer ${TOKEN}" -H "Content-Type: application/hujson" \
      --data-binary "@${2}" "${API}/validate"
    ;;
  *)
    echo "usage: $0 [get|validate <file>]" >&2; exit 2
    ;;
esac
