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
#
# This guard does NOT relax in contributor mode. Everything else local can
# degrade to a warning when the tooling isn't installed; this one cannot,
# because the thing it stops is a cleartext secret entering a public repo.
# What it does instead is stay runnable: when python3 or pyyaml is missing
# it reads the covered-path list out of .gitattributes rather than skipping
# the check, and says that it did.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

# shellcheck source=scripts/secretguard.sh disable=SC1091
. "$(pwd)/scripts/secretguard.sh"

fail=0

have_python_yaml() {
	command -v python3 >/dev/null 2>&1 && python3 -c 'import yaml' >/dev/null 2>&1
}

# Resolved once, here: the path helpers below run inside process
# substitutions, so anything they set would be lost in a subshell.
degraded=0
have_python_yaml || degraded=1

# In-place (partially encrypted) paths. .sops.yaml is the source of truth;
# .gitattributes is asserted to agree with it by the sops-config-consistency
# hook and by CI, which is what makes it a safe fallback here.
inplace_paths() {
	if [ "$degraded" -eq 0 ] && python3 scripts/sops_paths.py list 2>/dev/null; then
		return 0
	fi
	[ -f .gitattributes ] || return 0
	awk '/^[[:space:]]*#/ { next }
	     { for (i = 2; i <= NF; i++) if ($i == "filter=sops") { print $1; break } }' \
		.gitattributes
}

# Whole-file sops stores. The fallback is the layout .sops.yaml has always
# used for these; a new one outside secrets/ would be caught by CI.
whole_paths() {
	if [ "$degraded" -eq 0 ] && python3 scripts/sops_paths.py list --whole 2>/dev/null; then
		return 0
	fi
	local path
	for path in secrets/*.sops.yaml; do
		[ -e "$path" ] && printf '%s\n' "$path"
	done
	return 0
}

# What is missing, phrased for the `needs:` line of a blocked message.
missing_capability() {
	if ! _secretguard_have_age_key; then
		printf 'an age key (~/.config/sops/age/keys.txt, or SOPS_AGE_KEY_FILE)'
	elif [ -z "$(git config --get filter.sops.clean 2>/dev/null)" ]; then
		printf "filter.sops.clean in this clone's .git/config"
	elif ! command -v sops >/dev/null 2>&1; then
		printf 'sops on PATH'
	else
		printf 'the sops clean filter to have run on this file'
	fi
}

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

# Hard-fails in every mode, including contributor: what git is about to
# store is the secret itself, in the clear, in a public repo. The message
# names the file, what's missing, which hook stopped it, the fix and where
# the procedure is written down -- rather than leaving a raw filter error.
while IFS= read -r path; do
  [ -n "$path" ] || continue
  if grep -qxF "$path" <<<"$staged"; then
    if ! git show ":$path" | secretguard_is_sops_encrypted; then
      secretguard_block "a secret-bearing file is staged in the clear" \
        problem="the sops clean filter did not run, so git's copy of this file has no sops metadata block -- the values in it would be committed readable" \
        file="$path" \
        needs="$(missing_capability)" \
        blocked_by="pre-commit hook 'sops-secret-guard' (scripts/precommit_secret_guard.sh)" \
        fix="bash scripts/setup-git-filters.sh, then: git reset \"$path\" && git add \"$path\"" \
        see="RUNBOOK.md, When a hook blocks your commit" || fail=1
    fi
  fi
done < <(inplace_paths)

while IFS= read -r path; do
  [ -n "$path" ] || continue
  if grep -qxF "$path" <<<"$staged"; then
    if ! git show ":$path" | secretguard_is_sops_encrypted; then
      secretguard_block "a whole-file secret store is staged unencrypted" \
        problem="this file is ciphertext at rest by design; git's copy of it is not" \
        file="$path" \
        needs="$(missing_capability)" \
        blocked_by="pre-commit hook 'sops-secret-guard' (scripts/precommit_secret_guard.sh)" \
        fix="sops --encrypt --in-place $path" \
        see="RUNBOOK.md, Adding a secret" || fail=1
    fi
  fi
done < <(whole_paths)

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
#
# Needs python3 + pyyaml to know which paths are covered, and has no safe
# .gitattributes fallback (coverage comes from .pseudonyms.yaml, which is a
# subset). Skipping it is tolerable where the marker check above is not: an
# address only survives into git if the clean filter didn't run, which the
# marker check already blocks on every one of these files.
if [ "$degraded" -ne 0 ]; then
  secretguard_note "cleartext-address check skipped: no python3 with pyyaml" \
    problem="the encryption-marker check above still covers every one of these files, so this is a narrowing, not a hole" \
    needs="pyyaml for this python3" \
    blocked_by="pre-commit hook 'sops-secret-guard' (scripts/precommit_secret_guard.sh)" \
    fix="pip install pyyaml" \
    see="bash scripts/check_clone_setup.sh"
fi
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
done < <(if [ "$degraded" -eq 0 ]; then python3 scripts/pseudonymize.py paths; fi)

if [ "$degraded" -ne 0 ]; then
  secretguard_note "covered-file list came from .gitattributes, not .sops.yaml" \
    problem="python3 with pyyaml is not available to read .sops.yaml; the two are asserted to agree by CI, so the check still ran over the same files" \
    needs="pyyaml for this python3" \
    fix="pip install pyyaml" \
    see="bash scripts/check_clone_setup.sh"
fi

if [ "$fail" -ne 0 ]; then
  echo >&2
  echo "Commit blocked. Nothing was written to git." >&2
  exit 1
fi
