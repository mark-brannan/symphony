#!/usr/bin/env bash
# Wire a new (or existing) plugin config file into the sops in-place
# encryption scheme: adds the .sops.yaml rule and the .gitattributes entry,
# then stages the file and confirms the field(s) actually encrypted.
# Idempotent -- safe to re-run, skips whatever's already done.
#
# Two files to touch, not three: the pre-commit guard and the CI verifier
# both derive their file list from .sops.yaml at runtime (see
# scripts/sops_paths.py), so there's no third copy to keep in sync.
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

# In-place files only. The whole-file encrypted stores under secrets/ don't
# go through the git filter at all -- wiring one up here appends a filter
# entry that breaks every subsequent `git add` of the file (see RUNBOOK.md,
# "Adding a secret"). Guard BEFORE touching .sops.yaml/.gitattributes: this
# script edits as it goes, so a late failure leaves them half-applied.
case "$FILE" in
  secrets/*)
    echo "error: $FILE is in the whole-file encrypted store -- this script is for" >&2
    echo "  in-place plugin config files only. Edit the store with:  sops $FILE" >&2
    exit 1;;
esac
if grep -qE '^sops:|"sops":' "$FILE" 2>/dev/null; then
  echo "error: $FILE is sops ciphertext on disk -- refusing." >&2
  echo "  Either it's a whole-file encrypted store (edit it with: sops $FILE), or this" >&2
  echo "  clone never wired the smudge filter and the in-place files checked out" >&2
  echo "  encrypted -- run: bash scripts/setup-git-filters.sh" >&2
  exit 1
fi

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
  # `age: *recipients` shares the one recipient list at the top of
  # .sops.yaml, so key rotation stays a single-line edit. Never inline a
  # literal key here.
  cat >>.sops.yaml <<EOF

  - path_regex: ${ESCAPED_PATH}\$
    encrypted_regex: '${ENCRYPTED_REGEX}'
    key_groups:
      - age: *recipients
EOF
  echo "added: .sops.yaml rule (${ENCRYPTED_REGEX})"
fi

if grep -qxF "$FILE filter=sops" .gitattributes 2>/dev/null; then
  echo "skip: .gitattributes already covers $FILE"
else
  echo "$FILE filter=sops" >>.gitattributes
  echo "added: .gitattributes entry"
fi

echo
python3 scripts/sops_paths.py check

git add .sops.yaml .gitattributes
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
