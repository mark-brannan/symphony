#!/usr/bin/env bash
# Last local checkpoint before a secret becomes public.
#
# Pre-commit hooks check what you are committing right now. This checks
# what you are about to PUSH -- every commit in the range, including ones
# made an hour ago with --no-verify. That is the whole point: --no-verify is
# a legitimate break-glass, and a break-glass is only affordable if
# something downstream still looks. This is the last thing that looks while
# the mistake is still local and free to fix.
#
# Push, not commit, is the irreversible moment. A commit lives on your
# laptop; a push puts it on GitHub, where deleting it does not un-publish
# it. CI (gitleaks, trufflehog) is the real enforcement boundary, but
# .github/workflows/validate.yml triggers on push to main and PRs to main
# -- a push to a topic branch with no PR open is scanned by nothing until
# someone opens one. This covers that window.
#
# Deliberately bash + git + grep only. No python, no pyyaml, no sops, no
# Docker. It is the layer that must work on the machine where everything
# else has degraded, so it cannot have anything to degrade.
#
# Hard-fails in every mode -- there is no mode in which publishing a live
# credential is acceptable. `git push --no-verify` still bypasses it, which
# is intended and is named in the message.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

# shellcheck source=scripts/secretguard.sh disable=SC1091
. "$(pwd)/scripts/secretguard.sh"

ZERO="0000000000000000000000000000000000000000"
from_ref="${PRE_COMMIT_FROM_REF:-}"
to_ref="${PRE_COMMIT_TO_REF:-HEAD}"

# Branch deletion: nothing is being published.
if [ "$to_ref" = "$ZERO" ] || [ -z "$to_ref" ]; then
	exit 0
fi

# A new branch has no remote counterpart, so pre-commit reports the null
# ref. Scanning all of history would be both slow and wrong (it is already
# published); what is new is what this branch adds to main.
if [ -z "$from_ref" ] || [ "$from_ref" = "$ZERO" ]; then
	if base="$(git merge-base origin/main "$to_ref" 2>/dev/null)"; then
		from_ref="$base"
	else
		# No origin/main to compare against -- scan the tip commit rather
		# than nothing. Narrow beats silent.
		from_ref="$(git rev-parse "${to_ref}^" 2>/dev/null || echo "$to_ref")"
	fi
fi

range="${from_ref}..${to_ref}"

# Per-commit, never endpoint-to-endpoint. `git diff A..B` compares only the
# two ends, so a secret added in one commit and removed in the next is
# invisible to it -- while still being published, and still retrievable by
# anyone who clones. That is precisely the shape this hook exists to catch,
# so the file list comes from `git log`, the content checks iterate
# `git rev-list`, and the sweep reads every commit's own diff.
changed="$(git log --format= --name-only "$range" 2>/dev/null | sort -u || true)"
[ -n "$changed" ] || exit 0

commits="$(git rev-list "$range" 2>/dev/null || true)"

# First commit in the range that carries this path unencrypted, or empty if
# every version of it is a real sops document. Printed in the message so the
# fix names a commit rather than "somewhere in your branch".
#
# Encryption is judged by secretguard_is_sops_encrypted -- the same metadata
# shape the pre-commit guards use, not the presence of the word "sops".
#
# $1 = path.
first_unencrypted_commit() {
	local path="$1" commit
	for commit in $commits; do
		git cat-file -e "${commit}:${path}" 2>/dev/null || continue
		if ! git show "${commit}:${path}" | secretguard_is_sops_encrypted; then
			printf '%s' "$commit"
			return 0
		fi
	done
	return 1
}

fail=0

# Same source as everywhere else, read without pyyaml. .sops.yaml is
# authoritative; CI asserts .gitattributes still agrees with it.
covered_sops() {
	[ -f .gitattributes ] || return 0
	awk '/^[[:space:]]*#/ { next }
	     { for (i = 2; i <= NF; i++) if ($i == "filter=sops") { print $1; break } }' \
		.gitattributes
}

# --- 1. files that must never be tracked ------------------------------------
for path in .env age.key; do
	grep -qxF "$path" <<<"$changed" || continue
	carrier=""
	for commit in $commits; do
		if git cat-file -e "${commit}:${path}" 2>/dev/null; then
			carrier="$commit"
			break
		fi
	done
	if [ -n "$carrier" ]; then
		secretguard_block "a file that must never be tracked is in this push" \
			problem="this file holds live credentials and is present in commit ${carrier} -- deleting it in a later commit does not remove it from the history you are about to publish" \
			file="$path" \
			needs="the file removed from every commit in $range, not just the tip" \
			blocked_by="pre-push hook 'prepush-secret-scan' (scripts/prepush_secret_scan.sh)" \
			fix="git rm --cached $path, commit, then rewrite the earlier commits that carry it" \
			if_stuck="git push --no-verify pushes anyway -- CI's gitleaks and trufflehog will see it, and by then it is public" \
			see="RUNBOOK.md, A secret was committed in plaintext" || fail=1
	fi
done

# --- 2. covered files must be encrypted in what is being pushed -------------
while IFS= read -r path; do
	[ -n "$path" ] || continue
	grep -qxF "$path" <<<"$changed" || continue
	if bad="$(first_unencrypted_commit "$path")"; then
		secretguard_block "a secret-bearing file is unencrypted in this push" \
			problem="commit ${bad} stores this file without a sops metadata block -- readable to anyone who clones the repo, even if a later commit fixed it" \
			file="$path" \
			needs="the sops clean filter to have run before it was committed" \
			blocked_by="pre-push hook 'prepush-secret-scan' (scripts/prepush_secret_scan.sh)" \
			fix="bash scripts/setup-git-filters.sh, then re-commit the file: git add --renormalize $path" \
			if_stuck="already pushed elsewhere, or you need this out now? git push --no-verify -- then treat it as a leak and follow the rotation procedure" \
			see="RUNBOOK.md, A secret was committed in plaintext" || fail=1
	fi
done < <(covered_sops)

for path in secrets/*.sops.yaml; do
	[ -e "$path" ] || continue
	grep -qxF "$path" <<<"$changed" || continue
	if bad="$(first_unencrypted_commit "$path")"; then
		secretguard_block "a whole-file secret store is unencrypted in this push" \
			problem="this file is ciphertext at rest by design; commit ${bad} publishes it in the clear" \
			file="$path" \
			needs="sops encryption applied before the commit" \
			blocked_by="pre-push hook 'prepush-secret-scan' (scripts/prepush_secret_scan.sh)" \
			fix="sops --encrypt --in-place $path, then re-commit it" \
			if_stuck="git push --no-verify pushes anyway -- and this one is a live credential store, so rotate afterwards" \
			see="RUNBOOK.md, Rotating a secret" || fail=1
	fi
done

# --- 3. cleartext credential sweep over the whole range ---------------------
# The check most likely to catch a file nobody thought to configure, which
# is the realistic leak. Same pattern as the pre-commit guard, over a range
# of commits rather than the index.
hits="$(git log --format= -U0 -p "$range" -- '*.json' '*.yaml' '*.yml' '.env*' ':!*.sops.yaml' 2>/dev/null |
	grep -E '^\+' | grep -viE '^\+\+\+' |
	grep -iE '"(password|secret[kK]ey|token|apikey|api_key|logbookToken)"[[:space:]]*:[[:space:]]*"[^"]+' |
	grep -cv 'ENC\[' || true)"

if [ "${hits:-0}" -gt 0 ]; then
	secretguard_block "a commit in this push adds what looks like a cleartext credential" \
		problem="$hits added line(s) across the commits in $range set a password/secret/token field to a value that is not ENC[...]. A later commit removing one does not unpublish it" \
		needs="the value encrypted, or the field renamed if it genuinely is not a secret" \
		blocked_by="pre-push hook 'prepush-secret-scan' (scripts/prepush_secret_scan.sh)" \
		fix="find them with: git log -p -U0 $range -- '*.json' '*.yaml' '.env*' | grep -iE '\"(password|token|apikey)\"' -- then scripts/add_inplace_secret.sh <file> <field>" \
		if_stuck="a genuine false positive (a test fixture, a deliberate wrong-password case)? git push --no-verify, and add the exclusion so the next person does not hit it" \
		see="RUNBOOK.md, When a hook blocks your commit" || fail=1
fi

if [ "$fail" -ne 0 ]; then
	echo >&2
	echo "Push blocked. Nothing has left this machine." >&2
	exit 1
fi
