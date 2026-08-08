#!/usr/bin/env bash
# Confirms every secret-bearing file is actually encrypted in what git has
# committed. This is the backstop that cannot be bypassed: local hooks can
# be skipped with --no-verify or simply never installed, but this runs in
# CI on every push.
#
# Checks `git show HEAD:<path>`, not the working-tree copy -- locally the
# working tree is deliberately plaintext (smudge filter), so checking raw
# files would false-fail there. In CI, checkout applies no filter, so HEAD
# content and the working-tree file are the same thing anyway. Works
# unchanged in both places.
#
# The file list is derived from .sops.yaml via scripts/sops_paths.py. Do
# not hardcode paths here -- that's what let CI drift to checking 3 of 10.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

fail=0
checked=0
skipped=0

# In-place files: partially encrypted, so they parse as normal JSON/YAML
# but the secret leaves are ENC[...]. sops records what it did in a "sops"
# metadata key -- its absence means nothing was encrypted.
while IFS= read -r path; do
  [ -n "$path" ] || continue
  if ! blob="$(git show "HEAD:${path}" 2>/dev/null)"; then
    echo "note: ${path} is configured for encryption but not committed yet -- skipping." >&2
    skipped=$((skipped + 1))
    continue
  fi
  if ! grep -q '"sops"' <<<"$blob"; then
    echo "NOT ENCRYPTED: ${path}" >&2
    fail=1
  else
    checked=$((checked + 1))
  fi
done < <(python3 scripts/sops_paths.py list)

# Whole-file stores: everything is ciphertext, sops metadata is a top-level
# `sops:` YAML key.
while IFS= read -r path; do
  [ -n "$path" ] || continue
  if ! blob="$(git show "HEAD:${path}" 2>/dev/null)"; then
    echo "note: ${path} is not committed yet -- skipping." >&2
    skipped=$((skipped + 1))
    continue
  fi
  if ! grep -q '^sops:' <<<"$blob"; then
    echo "NOT ENCRYPTED: ${path}" >&2
    fail=1
  else
    checked=$((checked + 1))
  fi
done < <(python3 scripts/sops_paths.py list --whole)

if [ "$fail" -ne 0 ]; then
  echo >&2
  echo "One or more secret-bearing files are not encrypted in git. This must never happen." >&2
  echo "Do not push. See RUNBOOK.md -> 'A secret was committed in plaintext'." >&2
  exit 1
fi

echo "OK: ${checked} secret-bearing file(s) encrypted as committed (${skipped} not yet committed)."
