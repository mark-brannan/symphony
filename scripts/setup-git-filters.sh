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
# Safe to re-run at any time, and safe to run without sops, age or a key:
# missing tooling is reported and skipped rather than aborting the run. A
# contributor who never runs this at all can still commit -- see README.md,
# Setup. For what a given clone is missing: scripts/check_clone_setup.sh.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

# shellcheck source=scripts/symphony_mode.sh disable=SC1091
. "$(pwd)/scripts/symphony_mode.sh"

echo "symphony setup -- mode: $(symphony_mode) ($(symphony_mode_reason))"

# Missing tools used to exit 1 here, before a single thing was configured.
# That made the documented onboarding command all-or-nothing: without sops
# and age you got no filters, no cleared core.hooksPath and no installed
# hooks -- and, because the repo-hygiene guard fails on an unconfigured
# filter, no ability to commit anything at all. Everything below that does
# not need the missing tool still runs; each gap is reported with what it
# costs you. In strict mode the script still ends non-zero -- a maintainer's
# machine missing sops is a real failure -- but it ends that way AFTER
# wiring everything it could.
setup_incomplete=0

for tool in sops age; do
  if ! command -v "$tool" >/dev/null 2>&1; then
    symphony_require "$tool is not installed" \
      problem="secret-bearing files cannot be decrypted or edited on this machine" \
      needs="$tool on PATH" \
      blocked_by="scripts/setup-git-filters.sh" \
      fix="see RUNBOOK.md, Bringing up a host -- Phase 1" \
      see="README.md, Setup (contributors do not need it)" || setup_incomplete=1
  fi
done

# python3 is a harder gap than sops/age: both filter commands ARE python
# scripts, so they get registered below and then fail the moment git tries
# to run one. Registering them anyway is still right -- an unregistered
# filter commits secrets as plaintext, silently, which is strictly worse
# than a loud failure.
if ! command -v python3 >/dev/null 2>&1; then
  symphony_require "python3 is not installed" \
    problem="both git filters are python scripts; they will be registered below but cannot run, so checking out or staging a covered file will fail loudly" \
    needs="python3 on PATH" \
    blocked_by="scripts/setup-git-filters.sh" \
    fix="install python3 (see RUNBOOK.md, Bringing up a host -- Phase 1)" \
    see="bash scripts/check_clone_setup.sh" || setup_incomplete=1
fi

if [ ! -f "$HOME/.config/sops/age/keys.txt" ] && [ -z "${SOPS_AGE_KEY_FILE:-}" ]; then
  symphony_require "no age key on this machine" \
    problem="secret-bearing files will smudge as ciphertext until you provision one" \
    needs="~/.config/sops/age/keys.txt, or SOPS_AGE_KEY_FILE pointing at a key" \
    blocked_by="scripts/setup-git-filters.sh" \
    fix="see RUNBOOK.md, Bringing up a host -- Phase 2" \
    see="README.md, Setup (contributors do not need one)" || setup_incomplete=1
fi

# --- 1. sops clean/smudge filter --------------------------------------------
git config filter.sops.clean  "python3 $(pwd)/scripts/sops_filter.py clean %f"
git config filter.sops.smudge "python3 $(pwd)/scripts/sops_filter.py smudge %f"
git config filter.sops.required true
echo "configured: sops clean/smudge filter"

# --- 1b. hostvars clean/smudge filter ---------------------------------------
# Per-machine values (the ntfy server URL, for now): git stores
# {{ placeholders }}, this machine's values come from hostvars.local.yaml.
# See scripts/hostvars_filter.py.
git config filter.hostvars.clean  "python3 $(pwd)/scripts/hostvars_filter.py clean %f"
git config filter.hostvars.smudge "python3 $(pwd)/scripts/hostvars_filter.py smudge %f"
git config filter.hostvars.required true
echo "configured: hostvars clean/smudge filter"

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
if { [ -f "$HOME/.config/sops/age/keys.txt" ] || [ -n "${SOPS_AGE_KEY_FILE:-}" ]; } &&
   command -v python3 >/dev/null 2>&1; then
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
  echo "skipped decrypting in-place files: no age key, or no python3 to run the filter." >&2
  echo "  Provision what is missing, then re-run this script." >&2
fi

# --- 4. expand per-machine values in place ----------------------------------
# Same fresh-clone problem as the sops files: hostvars-covered files check
# out with their {{ placeholders }} intact when the filter wasn't wired yet.
# A placeholder in the working tree can only be that artifact -- SignalK
# never writes one -- so re-checking the file out cannot lose local work.
if [ -f hostvars.local.yaml ] && command -v python3 >/dev/null 2>&1; then
  pending=()
  while IFS= read -r path; do
    [ -n "$path" ] || continue
    [ -f "$path" ] || continue
    if grep -qE '"\{\{ *[A-Za-z_]' "$path" 2>/dev/null; then
      pending+=("$path")
    fi
  done < <(python3 scripts/hostvars_filter.py paths)

  if [ "${#pending[@]}" -gt 0 ]; then
    rm -f -- "${pending[@]}"
    git checkout -- "${pending[@]}"
    echo "expanded per-machine values: ${#pending[@]} file(s)"
  else
    echo "per-machine values already expanded on disk -- left untouched"
  fi
elif ! command -v python3 >/dev/null 2>&1; then
  echo
  echo "skipped expanding per-machine values: no python3 to run the filter." >&2
else
  echo
  echo "warning: no hostvars.local.yaml -- per-machine plugin values (the ntfy" >&2
  echo "  server URL) stay as {{ placeholders }} on disk, and SignalK would read" >&2
  echo "  them literally. Copy hostvars.local.yaml.example to hostvars.local.yaml," >&2
  echo "  set this machine's values, and re-run this script." >&2
fi

echo
echo "For a full report on what this clone has and hasn't got:"
echo "  bash scripts/check_clone_setup.sh"

if [ "$setup_incomplete" -ne 0 ]; then
  echo
  echo "Setup ran to the end, but something above is missing and this clone is" >&2
  echo "in strict mode. Filters, hooks and core.hooksPath were still wired." >&2
  exit 1
fi

echo
echo "Setup complete -- mode: $(symphony_mode)."
