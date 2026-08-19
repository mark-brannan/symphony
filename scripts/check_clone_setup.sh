#!/usr/bin/env bash
# What is wired up in THIS clone, and what breaks because it isn't.
#
# Read-only. It diagnoses; it never installs, configures or decrypts
# anything. Always exits 0 -- the report is the output, not the status.
#
# Deliberately depends on nothing but bash and git, because the situation
# it exists to explain is "the tooling isn't installed and a hook won't let
# me commit". A checker that needs python3 to tell you python3 is missing
# is no use. Everything that would need python, sops or pyyaml degrades to
# "unknown" rather than erroring.
#
#   bash scripts/check_clone_setup.sh
#
# See also: README.md (Setup) and RUNBOOK.md "When a hook blocks your commit".
set -uo pipefail

if ! command -v git >/dev/null 2>&1; then
	echo "git is not on PATH. Nothing else here can be checked." >&2
	exit 0
fi

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
	echo "not inside a git working tree -- run this from your symphony clone." >&2
	exit 0
}
cd "$ROOT" || exit 0

blockers=0
gaps=0

section() {
	printf '\n%s\n' "$1"
}

# ok LABEL [DETAIL]
ok() {
	printf '  ok        %-22s %s\n' "$1" "${2:-}"
}

# unknown LABEL WHY
unknown() {
	printf '  unknown   %-22s %s\n' "$1" "$2"
}

# gap LABEL SUMMARY BREAKS FIX  -- absent, but you can still commit
gap() {
	gaps=$((gaps + 1))
	printf '  warn      %-22s %s\n' "$1" "$2"
	printf '            %-22s impact: %s\n' "" "$3"
	printf '            %-22s fix: %s\n' "" "$4"
}

# blocker LABEL SUMMARY BREAKS FIX  -- absent AND stops you committing
blocker() {
	blockers=$((blockers + 1))
	printf '  BLOCKING  %-22s %s\n' "$1" "$2"
	printf '            %-22s impact: %s\n' "" "$3"
	printf '            %-22s fix: %s\n' "" "$4"
}

have() { command -v "$1" >/dev/null 2>&1; }

# Paths carrying a given git filter, read straight out of .gitattributes so
# this works without python3 or pyyaml. .sops.yaml is the real source of
# truth (scripts/sops_paths.py reads it); .gitattributes is asserted to
# agree with it by the sops-config-consistency hook and by CI, so it is a
# safe stand-in for a read-only report.
filtered_paths() {
	[ -f .gitattributes ] || return 0
	awk -v want="filter=$1" '
		/^[[:space:]]*#/ { next }
		{ for (i = 2; i <= NF; i++) if ($i == want) { print $1; break } }
	' .gitattributes
}

# Sourced for the mode line only -- nothing here changes behaviour by mode.
# shellcheck source=scripts/symphony_mode.sh disable=SC1091
. "$ROOT/scripts/symphony_mode.sh"

echo "Symphony clone setup"
echo "  repo: $ROOT"
echo "  mode: $(symphony_mode) ($(symphony_mode_reason))"

# --- tooling ----------------------------------------------------------------
section "Tooling on PATH"

if have python3; then
	ok "python3" "$(command -v python3)"
	if python3 -c 'import yaml' >/dev/null 2>&1; then
		ok "pyyaml" "importable"
	else
		gap "pyyaml" "python3 cannot import yaml" \
			"the sops/hostvars filters and several scripts can't parse .sops.yaml; the unit-test hook is skipped" \
			"pip install pyyaml"
	fi
else
	blocker "python3" "not found" \
		"both git filters are python scripts -- covered files cannot be cleaned or smudged at all" \
		"install python3 (see RUNBOOK.md, Bringing up a host -- Phase 1)"
	unknown "pyyaml" "no python3 to ask"
fi

if have sops; then
	ok "sops" "$(command -v sops)"
else
	gap "sops" "not found" \
		"secret-bearing files stay ciphertext on disk; you cannot read or edit a secret" \
		"see RUNBOOK.md, Bringing up a host -- Phase 1 (or skip it: contributors don't need secrets)"
fi

if have age; then
	ok "age" "$(command -v age)"
else
	gap "age" "not found" \
		"you cannot generate or inspect the key sops decrypts with" \
		"see RUNBOOK.md, Bringing up a host -- Phase 2"
fi

if have pre-commit; then
	ok "pre-commit" "$(command -v pre-commit)"
else
	gap "pre-commit" "not found" \
		"commits are not scanned locally; CI (.github/workflows/validate.yml) still blocks a leaked secret on push, in public rather than at your terminal" \
		"pipx install pre-commit  (or: pip install pre-commit), then bash scripts/setup-git-filters.sh"
fi

if have docker; then
	if docker info >/dev/null 2>&1; then
		ok "docker" "daemon reachable"
	else
		gap "docker" "on PATH, daemon not reachable" \
			"the gitleaks pre-commit hook has no scanner to run; CI still runs gitleaks over full history" \
			"start Docker Desktop / dockerd (WSL2: enable integration for this distro)"
	fi
else
	gap "docker" "not found" \
		"the gitleaks pre-commit hook and the local dev stack (scripts/dev_stack.sh) cannot run; CI still runs gitleaks" \
		"install Docker (only needed to run the stack or scan locally)"
fi

# --- git wiring -------------------------------------------------------------
section "Git configuration for this clone"
echo "  (filter *commands* live in .git/config, which git never versions --"
echo "   every clone has to wire its own)"

for f in sops hostvars; do
	cmd="$(git config --get "filter.$f.clean" 2>/dev/null)"
	if [ -n "$cmd" ]; then
		ok "filter.$f.clean" "configured"
	else
		blocker "filter.$f.clean" "not set in git config" \
			".gitattributes declares filter=$f, so covered files would commit UNTRANSFORMED -- and the repo-hygiene pre-commit hook fails every commit, including a typo fix in a markdown file" \
			"bash scripts/setup-git-filters.sh"
	fi
done

hooks_path="$(git config --get core.hooksPath 2>/dev/null)"
if [ -n "$hooks_path" ]; then
	blocker "core.hooksPath" "set to '$hooks_path'" \
		"pre-commit refuses to run while it is set, so no local hook fires at all" \
		"git config --unset core.hooksPath  (or: bash scripts/setup-git-filters.sh)"
else
	ok "core.hooksPath" "unset (correct -- pre-commit owns .git/hooks)"
fi

hook_file="$(git rev-parse --git-path hooks/pre-commit 2>/dev/null)"
if [ -n "$hook_file" ] && [ -f "$hook_file" ] && grep -q 'pre-commit' "$hook_file" 2>/dev/null; then
	ok "pre-commit installed" "$hook_file"
else
	gap "pre-commit installed" "no pre-commit hook in .git/hooks" \
		"nothing is checked at commit time; CI is the real gate" \
		"bash scripts/setup-git-filters.sh  (runs 'pre-commit install' for you)"
fi

# --- key material and per-machine values ------------------------------------
section "Key material and per-machine values"

if [ -n "${SOPS_AGE_KEY_FILE:-}" ] && [ -f "${SOPS_AGE_KEY_FILE:-}" ]; then
	ok "age key" "SOPS_AGE_KEY_FILE=$SOPS_AGE_KEY_FILE"
elif [ -f "$HOME/.config/sops/age/keys.txt" ]; then
	ok "age key" "$HOME/.config/sops/age/keys.txt"
else
	gap "age key" "no key at ~/.config/sops/age/keys.txt and SOPS_AGE_KEY_FILE unset" \
		"secret-bearing files smudge as ciphertext, and staging one is blocked rather than committed in the clear" \
		"see RUNBOOK.md, Bringing up a host -- Phase 2 (contributors don't need one)"
fi

if [ -f hostvars.local.yaml ]; then
	ok "hostvars.local.yaml" "present"
else
	gap "hostvars.local.yaml" "missing" \
		"per-machine values (the ntfy server URL) stay as {{ placeholders }} on disk and SignalK reads them literally" \
		"cp hostvars.local.yaml.example hostvars.local.yaml && \$EDITOR hostvars.local.yaml"
fi

# --- what is actually on disk -----------------------------------------------
section "Working-tree state of covered files"

still_ciphertext=0
checked_inplace=0
while IFS= read -r p; do
	[ -n "$p" ] || continue
	[ -f "$p" ] || continue
	checked_inplace=$((checked_inplace + 1))
	if grep -q '"sops"' "$p" 2>/dev/null; then
		still_ciphertext=$((still_ciphertext + 1))
	fi
done < <(filtered_paths sops)

whole_files=0
for p in secrets/*.sops.yaml; do
	[ -f "$p" ] || continue
	whole_files=$((whole_files + 1))
done

if [ "$checked_inplace" -eq 0 ]; then
	unknown "sops in-place files" "none listed in .gitattributes"
elif [ "$still_ciphertext" -eq 0 ]; then
	ok "sops in-place files" "$checked_inplace file(s), all plaintext on disk"
else
	gap "sops in-place files" "$still_ciphertext of $checked_inplace still ciphertext on disk" \
		"SignalK/Grafana read these directly and would parse sops markers as configuration" \
		"provision an age key, then: bash scripts/setup-git-filters.sh"
fi
[ "$whole_files" -gt 0 ] && ok "sops whole-file stores" "$whole_files under secrets/ (ciphertext at rest is correct)"

pending=0
checked_hv=0
while IFS= read -r p; do
	[ -n "$p" ] || continue
	[ -f "$p" ] || continue
	checked_hv=$((checked_hv + 1))
	if grep -qE '"\{\{ *[A-Za-z_]' "$p" 2>/dev/null; then
		pending=$((pending + 1))
	fi
done < <(filtered_paths hostvars)

if [ "$checked_hv" -eq 0 ]; then
	unknown "hostvars files" "none listed in .gitattributes"
elif [ "$pending" -eq 0 ]; then
	ok "hostvars files" "$checked_hv file(s), placeholders expanded"
else
	gap "hostvars files" "$pending of $checked_hv still hold {{ placeholders }}" \
		"SignalK reads the placeholder text literally -- e.g. it posts to the URL '{{ ntfy_url }}'" \
		"create hostvars.local.yaml, then: bash scripts/setup-git-filters.sh"
fi

# --- verdict ----------------------------------------------------------------
section "Summary"
if [ "$blockers" -gt 0 ]; then
	echo "  $blockers thing(s) will stop you committing, $gaps other gap(s)."
	echo "  Start with: bash scripts/setup-git-filters.sh"
	echo "  Still stuck? RUNBOOK.md, \"When a hook blocks your commit\"."
elif [ "$gaps" -gt 0 ]; then
	echo "  Commits should work. $gaps gap(s) above limit what you can do"
	echo "  locally. None of them are needed to contribute -- CI"
	echo "  (.github/workflows/validate.yml) is the enforcement boundary and"
	echo "  needs no secrets."
else
	echo "  Fully wired: tooling, filters, hooks, key material and on-disk state"
	echo "  all check out."
fi
echo

exit 0
