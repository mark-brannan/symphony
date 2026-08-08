#!/usr/bin/env bash
# Run once per clone. This is THE onboarding command -- it wires up
# everything a working copy needs that git refuses to version for you.
#
# Two separate things get configured here:
#
#   1. The sops clean/smudge filter. `.gitattributes` names the `sops`
#      filter, but filter *commands* live in .git/config, which git
#      deliberately doesn't version (arbitrary commands from a repo you
#      cloned would be a code-exec vector). So every clone wires its own.
#
#   2. The pre-commit hooks. Same reason -- hooks aren't versioned either.
#
# Safe to re-run at any time.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

missing=0
for tool in sops age python3; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    echo "error: $tool not found on PATH -- install it first (see RUNBOOK.md)" >&2
    missing=1
  fi
done
[ "$missing" -eq 0 ] || exit 1

if [ ! -f "$HOME/.config/sops/age/keys.txt" ] && [ -z "${SOPS_AGE_KEY_FILE:-}" ]; then
  echo "warning: no age key at ~/.config/sops/age/keys.txt and SOPS_AGE_KEY_FILE is unset." >&2
  echo "  Secret-bearing files will smudge as ciphertext until you provision one." >&2
fi

# --- 1. sops clean/smudge filter --------------------------------------------
git config filter.sops.clean  "python3 $(pwd)/scripts/sops_filter.py clean %f"
git config filter.sops.smudge "python3 $(pwd)/scripts/sops_filter.py smudge %f"
git config filter.sops.required true
echo "configured: sops clean/smudge filter"

# --- 2. pre-commit hooks ----------------------------------------------------
# Hooks used to live in .githooks/ via core.hooksPath. They're managed by
# the pre-commit framework now, which installs into .git/hooks and refuses
# to run while core.hooksPath is set -- so clear the old setting on clones
# that still carry it.
if git config --get core.hooksPath >/dev/null 2>&1; then
  git config --unset core.hooksPath
  echo "cleared: stale core.hooksPath (hooks are managed by pre-commit now)"
fi

if command -v pre-commit >/dev/null 2>&1; then
  pre-commit install
  echo "configured: pre-commit hooks"
else
  echo >&2
  echo "warning: pre-commit is not installed -- COMMITS ARE NOT BEING SCANNED LOCALLY." >&2
  echo "  Install it with:  pip install pre-commit  (or: pipx install pre-commit)" >&2
  echo "  then re-run this script." >&2
  echo "  CI still blocks unencrypted secrets on push, but you'll find out later" >&2
  echo "  and in public rather than at commit time." >&2
fi

# --- 3. decrypt the in-place files on disk ----------------------------------
# These check out as ciphertext on a fresh clone (the smudge filter wasn't
# wired yet). Now that it is, re-checking them out decrypts them in place,
# which is the state SignalK/Grafana expect to read.
#
# Only files that are STILL CIPHERTEXT on disk are touched. A file holding
# sops markers in the working tree can only be a fresh-clone artifact --
# never local work -- so re-checking it out cannot lose anything. Files
# already plaintext are left strictly alone: SignalK rewrites them at
# runtime and a blind `git checkout` would discard live configuration.
if [ -f "$HOME/.config/sops/age/keys.txt" ] || [ -n "${SOPS_AGE_KEY_FILE:-}" ]; then
  still_encrypted=()
  while IFS= read -r path; do
    [ -n "$path" ] || continue
    [ -f "$path" ] || continue
    if grep -q '"sops"' "$path" 2>/dev/null; then
      still_encrypted+=("$path")
    fi
  done < <(python3 scripts/sops_paths.py list)

  if [ "${#still_encrypted[@]}" -gt 0 ]; then
    rm -f -- "${still_encrypted[@]}"
    git checkout -- "${still_encrypted[@]}"
    echo "decrypted on disk: ${#still_encrypted[@]} file(s) that checked out encrypted"
  else
    echo "in-place files already plaintext on disk -- left untouched"
  fi
else
  echo
  echo "skipped decrypting in-place files: no age key available." >&2
  echo "  Provision one, then re-run this script." >&2
fi

echo
echo "Setup complete."
