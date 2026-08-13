#!/usr/bin/env bash
# Blocks a commit that would put a secret into git in readable form.
#
# Runs as a pre-commit hook (see .pre-commit-config.yaml) and inspects what
# is *staged*, not what is on disk -- the working tree is deliberately
# plaintext here, git's copy is what must be safe.
#
# Three independent checks, in increasing order of paranoia:
#   1. files that must never be tracked at all (.env, age.key)
#   2. sops-configured files staged without encryption markers
#   3. a regex sweep for credential-shaped values in any config file,
#      including ones sops has never heard of
#
# Check 3 is the one that matters most: 1 and 2 only cover paths already
# known to the config, and the realistic leak is a file nobody thought to
# configure. Do not narrow it without a reason.
#
# The file lists come from .sops.yaml via scripts/sops_paths.py. Nothing
# secret-bearing is hardcoded in this file.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

fail=0

# --- 1. never-tracked files -------------------------------------------------
# Deleting them (untracking via `git rm --cached`) is fine and expected;
# only block adds and modifies.
for path in .env age.key; do
  status="$(git diff --cached --name-status -- "$path" | cut -f1)"
  if [ -n "$status" ] && [ "$status" != "D" ]; then
    echo "BLOCKED: '$path' is staged (status: $status) but must never be committed." >&2
    echo "  Unstage it:  git rm --cached $path" >&2
    fail=1
  fi
done

# --- 2. sops-configured files must be encrypted -----------------------------
staged="$(git diff --cached --name-only)"

while IFS= read -r path; do
  [ -n "$path" ] || continue
  if grep -qxF "$path" <<<"$staged"; then
    if ! git show ":$path" | grep -q '"sops"'; then
      echo "BLOCKED: '$path' is staged WITHOUT sops encryption markers." >&2
      echo "  The clean filter did not run. Did this clone run scripts/setup-git-filters.sh?" >&2
      fail=1
    fi
  fi
done < <(python3 scripts/sops_paths.py list)

while IFS= read -r path; do
  [ -n "$path" ] || continue
  if grep -qxF "$path" <<<"$staged"; then
    if ! git show ":$path" | grep -q '^sops:'; then
      echo "BLOCKED: '$path' is staged without sops encryption." >&2
      echo "  Encrypt it:  sops --encrypt --in-place $path" >&2
      fail=1
    fi
  fi
done < <(python3 scripts/sops_paths.py list --whole)

# --- 3. cleartext credential sweep ------------------------------------------
# Scoped to config-shaped files (json/yaml/env) only. Application and test
# source legitimately contains strings like `"password": "wrong-on-purpose"`
# in login-rejection cases, which isn't a real secret and shouldn't trip
# this. Whole-file sops stores are excluded -- they're ciphertext by
# definition and their base64 blobs can otherwise false-positive.
if git diff --cached -U0 -- '*.json' '*.yaml' '*.yml' '.env*' ':!*.sops.yaml' | \
   grep -E '^\+' | grep -viE '^\+\+\+' | \
   grep -iE '"(password|secret[kK]ey|token|apikey|api_key|logbookToken)"[[:space:]]*:[[:space:]]*"[^"]+' | \
   grep -v 'ENC\[' >/dev/null; then
  echo "BLOCKED: a staged line in a config file looks like a cleartext credential" >&2
  echo "  (a password/secret/token field with a value that isn't ENC[...])." >&2
  echo >&2
  echo "  If this file should be encrypted, wire it up:" >&2
  echo "    scripts/add_inplace_secret.sh <file> <field>" >&2
  echo "  If it genuinely isn't a secret, unstage it and see RUNBOOK.md." >&2
  fail=1
fi

# --- 4. cleartext addresses in pseudonymized files --------------------------
# The staged blob is sops ciphertext, so this only ever sees what really
# stayed in the clear. Base64 has no '@', so ENC[...] cannot false-positive.
# A hit means the clean filter did not substitute -- usually a clone that
# never ran setup-git-filters.sh, or a path added to .pseudonyms.yaml
# without being wired to filter=sops.
while IFS= read -r path; do
  [ -n "$path" ] || continue
  grep -qxF "$path" <<<"$staged" || continue
  if git show ":$path" | grep -oE '"[^"]+@[^"]+\.[A-Za-z]{2,}"' | grep -qv '^"pid\.'; then
    echo "BLOCKED: '$path' is staged with a cleartext email address." >&2
    echo "  Expected every address to be a pid.* token. The clean filter" >&2
    echo "  did not substitute. Check that this clone ran" >&2
    echo "  scripts/setup-git-filters.sh and that the path is filter=sops." >&2
    fail=1
  fi
done < <(python3 scripts/pseudonymize.py paths)

if [ "$fail" -ne 0 ]; then
  echo >&2
  echo "Commit blocked. Nothing was written to git." >&2
  exit 1
fi
