#!/usr/bin/env bash
# Wire a new (or existing) plugin config file into the sops in-place
# encryption scheme: adds the .sops.yaml rule, .gitattributes entry, and
# .githooks/pre-commit tracked-path entry, then stages the file and
# confirms the field(s) actually encrypted. Idempotent -- safe to re-run,
# skips whatever's already done.
#
# Usage: scripts/add_inplace_secret.sh <file> <field> [<field2> ...]
# Example: scripts/add_inplace_secret.sh signalk/plugin-config-data/signalk-postgsail.json token
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

FILE="${1:?usage: $0 <file> <field> [<field2> ...]}"
shift
FIELDS=("$@")
[ "${#FIELDS[@]}" -ge 1 ] || { echo "need at least one field name" >&2; exit 1; }
[ -f "$FILE" ] || { echo "no such file: $FILE" >&2; exit 1; }

if [ "${#FIELDS[@]}" -eq 1 ]; then
  ENCRYPTED_REGEX="^${FIELDS[0]}\$"
else
  joined=$(IFS='|'; echo "${FIELDS[*]}")
  ENCRYPTED_REGEX="^(${joined})\$"
fi

ESCAPED_PATH=$(printf '%s' "$FILE" | sed -e 's/[.]/\\./g')

if grep -qF "path_regex: ${ESCAPED_PATH}\$" .sops.yaml 2>/dev/null; then
  echo "skip: .sops.yaml already has a rule for $FILE"
else
  cat >>.sops.yaml <<EOF

  - path_regex: ${ESCAPED_PATH}\$
    encrypted_regex: '${ENCRYPTED_REGEX}'
    key_groups:
      - age:
          - *host_age
EOF
  echo "added: .sops.yaml rule (${ENCRYPTED_REGEX})"
fi

if grep -qxF "$FILE filter=sops" .gitattributes 2>/dev/null; then
  echo "skip: .gitattributes already covers $FILE"
else
  echo "$FILE filter=sops" >>.gitattributes
  echo "added: .gitattributes entry"
fi

if grep -qF "\"$FILE\"" .githooks/pre-commit; then
  echo "skip: .githooks/pre-commit already covers $FILE"
else
  python3 - "$FILE" <<'PYEOF'
import sys
path = sys.argv[1]
with open(".githooks/pre-commit") as f:
    content = f.read()
marker = "sops_paths=(\n"
idx = content.index(marker) + len(marker)
content = content[:idx] + f'  "{path}"\n' + content[idx:]
with open(".githooks/pre-commit", "w") as f:
    f.write(content)
PYEOF
  echo "added: .githooks/pre-commit entry"
fi

git add .sops.yaml .gitattributes .githooks/pre-commit
git rm --cached "$FILE" >/dev/null 2>&1 || true
git add "$FILE"

echo
fail=0
for field in "${FIELDS[@]}"; do
  if git show ":$FILE" | grep -qE "\"${field}\": *\"ENC\["; then
    echo "verified: $field is encrypted"
  else
    echo "FAILED: $field is NOT encrypted -- check the encrypted_regex in .sops.yaml" >&2
    fail=1
  fi
done

if [ "$fail" -ne 0 ]; then
  exit 1
fi

echo
echo "staged and verified. review with: git diff --cached -- $FILE"
echo "then: git commit"
