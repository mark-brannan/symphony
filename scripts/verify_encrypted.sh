#!/usr/bin/env bash
# Confirms the sops-tracked files are actually encrypted in what git has
# committed. Checks `git show HEAD:<path>`, not the working-tree copy --
# locally the working tree is deliberately plaintext (smudge filter), so
# checking raw files would false-fail there. In CI, checkout doesn't apply
# any filter, so HEAD content and the working-tree file are the same
# thing anyway -- this script works unchanged in both places.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

fail=0

partial_files=(
  "signalk/security.json"
  "signalk/plugin-config-data/signalk-to-influxdb2.json"
  "signalk/plugin-config-data/signalk-dsc.json"
)
for path in "${partial_files[@]}"; do
  if ! git show "HEAD:${path}" 2>/dev/null | grep -q '"sops"'; then
    echo "NOT ENCRYPTED: ${path}" >&2
    fail=1
  fi
done

for path in secrets/*.sops.yaml; do
  [ -e "$path" ] || continue
  if ! git show "HEAD:${path}" 2>/dev/null | grep -q '^sops:'; then
    echo "NOT ENCRYPTED: ${path}" >&2
    fail=1
  fi
done

if [ "$fail" -ne 0 ]; then
  echo "One or more secret-bearing files are not encrypted in git. This must never happen." >&2
  exit 1
fi
echo "OK: all sops-tracked files are encrypted as committed."
