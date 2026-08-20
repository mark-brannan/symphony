#!/usr/bin/env bash
# Shared by every local guard: which mode this clone is in, and one format
# for the message a guard prints when something is missing.
#
# Source it, don't run it:
#
#     . "$(git rev-parse --show-toplevel)/scripts/secretguard.sh"
#
# The invariant every caller is composing against:
#
#     Enforcement may soften a guard about your ENVIRONMENT.
#     It may never soften a guard about the CONTENT of your commit.
#
# So secretguard_require is for a missing capability, secretguard_block is
# for what is in the index. Where both apply, the guard passes only when
# nothing covered is staged AND enforcement is not strict -- i.e. it blocks
# on stages-a-covered-path OR mode-is-strict. Neither axis can wave the
# other through. The long form is in scripts/secretguard.py's docstring.
#
# Two modes:
#
#   strict       -- this clone can hold secrets. A missing capability is an
#                   error and the guard exits non-zero.
#   contributor  -- this clone has no key and isn't expected to. A missing
#                   capability is a warning; the commit goes through and CI
#                   (.github/workflows/validate.yml) is the enforcement
#                   boundary, as it always was.
#
# Resolved in this order:
#   1. $CI / $GITHUB_ACTIONS   strict, always, and first so that nothing can
#                              downgrade it. CI has no age key and no filters,
#                              so auto-detection would call it a contributor
#                              and wave through exactly the gaps CI exists to
#                              catch -- and an explicit override set in a
#                              workflow for some unrelated reason would do the
#                              same. "CI is always strict" only holds if CI
#                              wins over every other input.
#   2. $SECRETGUARD_MODE       one word: strict or contributor.
#   3. .secretguard-mode       the same one word, in a file at the repo root,
#                              to pin a clone without exporting anything.
#   4. auto-detect             strict iff an age key is available AND both git
#                              filters are configured; contributor otherwise.
#
# Auto-detection is never silent: every message this file formats carries a
# `mode:` line naming the mode and how it was decided, so a guard can't be
# quietly in the wrong one.
#
# There is a python twin, scripts/secretguard.py, resolving mode by the
# same rules and formatting messages identically -- guards exist in both
# languages. scripts/test_secretguard.py asserts the two agree.
#
# What this does NOT relax: staging a file that .gitattributes covers with
# filter=sops, without the filter having run, hard-fails in EVERY mode. That
# is the one case where the permissive path would put a cleartext secret in
# a public repo. Use secretguard_block for those, never secretguard_require.

# Process-local cache, deliberately NOT seeded from the environment, and
# named in the lowercase private form so it does not read as one. An earlier
# cut seeded it, which made the cache a second undocumented override that
# this file honored and its python twin did not -- shell guards strict and
# python guards contributor, inside one `pre-commit run`. SECRETGUARD_MODE is
# the one env knob.
_secretguard_mode=""
_secretguard_mode_reason=""

_secretguard_repo_root() {
	git rev-parse --show-toplevel 2>/dev/null || pwd
}

_secretguard_have_age_key() {
	if [ -n "${SOPS_AGE_KEY_FILE:-}" ] && [ -f "${SOPS_AGE_KEY_FILE}" ]; then
		return 0
	fi
	[ -f "$HOME/.config/sops/age/keys.txt" ]
}

# Mirror of secretguard.py's _SOPS_DIRS. git runs hooks from whatever
# spawned git -- an IDE, a GUI client, an agent harness -- and those inherit
# a bare PATH without ~/.local/bin, so `command -v sops` alone misses on a
# machine that has sops installed and working. A function rather than a
# variable so the parity suite can swap it out the way it monkeypatches the
# python list. The parity suite also pins secretguard_sops_locations below
# byte-identical to the python text, which is what keeps the two lists from
# drifting.
_secretguard_sops_dirs() {
	printf '%s\n' "$HOME/.local/bin" /usr/local/bin /opt/homebrew/bin /usr/bin /bin
}

# secretguard_find_sops -- absolute path to a runnable sops on stdout, or
# nothing and exit 1. The shell twin of secretguard.find_sops().
secretguard_find_sops() {
	local found dir candidate
	found="$(command -v sops 2>/dev/null || true)"
	if [ -n "$found" ]; then
		printf '%s\n' "$found"
		return 0
	fi
	while IFS= read -r dir; do
		candidate="$dir/sops"
		if [ -f "$candidate" ] && [ -x "$candidate" ]; then
			printf '%s\n' "$candidate"
			return 0
		fi
	done < <(_secretguard_sops_dirs)
	return 1
}

# Everywhere secretguard_find_sops looks, phrased for a `needs:` line.
# Must stay byte-identical to secretguard.py's sops_locations(); the parity
# suite asserts it.
secretguard_sops_locations() {
	printf 'sops on PATH or in ~/.local/bin, /usr/local/bin, /opt/homebrew/bin, /usr/bin, /bin\n'
}

# secretguard_can_decrypt -- this machine can open the encrypted store:
# runnable sops AND an age key. Deliberately a separate question from
# secretguard_mode. Strict answers "how rigorously to enforce"; it does not
# answer "does this machine hold keys" -- CI is strict unconditionally while
# carrying no key at all, by design. The python twin is
# secretguard.can_decrypt(); the long form lives on its docstring.
secretguard_can_decrypt() {
	[ -n "$(secretguard_find_sops || true)" ] && _secretguard_have_age_key
}

_secretguard_filters_configured() {
	[ -n "$(git config --get filter.sops.clean 2>/dev/null)" ] &&
		[ -n "$(git config --get filter.hostvars.clean 2>/dev/null)" ]
}

# Where a guard message goes.
#
# pre-commit captures a hook's stderr and prints it only when the hook
# FAILS. In contributor mode a degraded guard passes, so the whole point of
# auto-detection not being silent would be defeated: the mode line would
# exist and nobody would ever see it. When stderr isn't a terminal but one
# is attached, write straight to it. One destination, never both, so
# nothing is printed twice.
#
# The stderr case duplicates FD 2 (`>&2`) rather than opening the path
# /dev/stderr. Opening that path truncates: run a hook as
# `pre-commit run 2>>build.log` and `> "/dev/stderr"` reopens the log with
# O_TRUNC and destroys everything already in it. Verified, not theoretical.
# /dev/tty is opened in append mode for the same reason.
_secretguard_route() {
	if [ -t 2 ]; then
		"$@" >&2
	elif { : >/dev/tty; } 2>/dev/null; then
		"$@" >>/dev/tty
	else
		"$@" >&2
	fi
}

# Normalize a mode word for comparison: lowercased, surrounding whitespace
# gone. The python twin does the same with .strip().lower(), and the parity
# test caught the version of this that only lowercased.
_secretguard_word() {
	printf '%s' "$1" | tr -d '[:space:]' | tr '[:upper:]' '[:lower:]'
}

# secretguard_is_sops_encrypted -- reads the file content on stdin, exits 0
# only if it carries a real sops metadata block.
#
# Not "does the text contain the word sops": a plaintext
# {"note": "sops", "password": "hunter2"} contains it, and every guard
# downstream would then treat a live credential as encrypted. sops writes a
# `sops` key whose value is a mapping carrying at least `mac` and `version`,
# in both its output forms; require that shape. The python twin
# (secretguard.is_sops_encrypted) applies the same rule, and the parity test
# runs both over one fixture list.
secretguard_is_sops_encrypted() {
	local text
	text="$(cat)"
	if grep -Eq '"sops"[[:space:]]*:[[:space:]]*\{' <<<"$text"; then
		grep -Eq '"mac"[[:space:]]*:' <<<"$text" &&
			grep -Eq '"version"[[:space:]]*:' <<<"$text"
		return
	fi
	if grep -Eq '^sops:[[:space:]]*$' <<<"$text"; then
		grep -Eq '^[[:space:]]+mac:' <<<"$text" &&
			grep -Eq '^[[:space:]]+version:' <<<"$text"
		return
	fi
	return 1
}

secretguard_resolve_mode() {
	if [ -n "$_secretguard_mode" ]; then
		return 0
	fi

	local raw word root line key filters missing

	if [ -n "${CI:-}" ] || [ -n "${GITHUB_ACTIONS:-}" ]; then
		_secretguard_mode=strict
		_secretguard_mode_reason="CI"
		return 0
	fi

	raw="${SECRETGUARD_MODE:-}"
	word="$(_secretguard_word "$raw")"
	case "$word" in
	strict | contributor)
		_secretguard_mode="$word"
		_secretguard_mode_reason="SECRETGUARD_MODE=$word"
		return 0
		;;
	"") : ;;
	*) printf 'secretguard: ignoring SECRETGUARD_MODE=%s (expected strict or contributor)\n' "$raw" >&2 ;;
	esac

	root="$(_secretguard_repo_root)"
	if [ -f "$root/.secretguard-mode" ]; then
		# `|| true`: with `set -o pipefail` (setup-git-filters.sh) a
		# comments-only file makes grep exit 1, which would propagate out
		# of the assignment and kill the sourcing script before it
		# configured anything.
		line="$(grep -vE '^[[:space:]]*(#|$)' "$root/.secretguard-mode" 2>/dev/null |
			head -n1 | tr -d '[:space:]' || true)"
		line="$(_secretguard_word "$line")"
		case "$line" in
		strict | contributor)
			_secretguard_mode="$line"
			_secretguard_mode_reason=".secretguard-mode says $line"
			return 0
			;;
		"") : ;;
		*) printf 'secretguard: ignoring .secretguard-mode value %s (expected strict or contributor)\n' "$line" >&2 ;;
		esac
	fi

	key=no
	filters=no
	if _secretguard_have_age_key; then key=yes; fi
	if _secretguard_filters_configured; then filters=yes; fi

	if [ "$key" = yes ] && [ "$filters" = yes ]; then
		_secretguard_mode=strict
		_secretguard_mode_reason="auto-detected: age key available, git filters configured"
	else
		missing=""
		if [ "$key" = no ]; then missing="no age key"; fi
		if [ "$filters" = no ]; then
			missing="${missing:+$missing, }git filters not configured"
		fi
		_secretguard_mode=contributor
		_secretguard_mode_reason="auto-detected: $missing"
	fi
}

secretguard_mode() {
	secretguard_resolve_mode
	printf '%s\n' "$_secretguard_mode"
}

secretguard_mode_reason() {
	secretguard_resolve_mode
	printf '%s\n' "$_secretguard_mode_reason"
}

# secretguard_msg LEVEL TITLE [problem=...] [file=...]... [needs=...]
#              [blocked_by=...] [fix=...] [if_stuck=...] [see=...]
#
# `if_stuck` is the break-glass line: what to do when the fix isn't
# available to you right now. It is deliberately part of the standard shape
# rather than something each guard decides to mention. An escape hatch
# nobody wrote down is not an escape hatch -- it is a thing people
# rediscover at the worst possible moment, and CI's gitleaks and trufflehog
# passes are what make writing it down affordable.
#
# Every guard message in this repo has this shape. Fields print in a fixed
# order, absent ones are skipped, `file=` may repeat, and the `mode:` line
# is always last and always present.
# Prints the message body. Split out so the destination can be chosen with
# a redirect on the call rather than a path opened inside it. Reads the
# caller's locals -- bash scopes those dynamically.
_secretguard_msg_body() {
		printf '\nsecretguard %s: %s\n' "$level" "$title"
		if [ -n "$problem" ]; then printf '  problem:    %s\n' "$problem"; fi
		if [ -n "$files" ]; then
			while IFS= read -r val; do
				if [ -n "$val" ]; then printf '  file:       %s\n' "$val"; fi
			done <<<"$files"
		fi
		if [ -n "$needs" ]; then printf '  needs:      %s\n' "$needs"; fi
		if [ -n "$blocked_by" ]; then printf '  blocked by: %s\n' "$blocked_by"; fi
		if [ -n "$fix" ]; then printf '  fix:        %s\n' "$fix"; fi
		if [ -n "$if_stuck" ]; then printf '  if stuck:   %s\n' "$if_stuck"; fi
		if [ -n "$see" ]; then printf '  see:        %s\n' "$see"; fi
		printf '  mode:       %s (%s)\n' "$_secretguard_mode" "$_secretguard_mode_reason"
}

secretguard_msg() {
	secretguard_resolve_mode
	local level="$1" title="$2"
	shift 2

	local problem="" needs="" blocked_by="" fix="" if_stuck="" see="" files="" kv key val
	for kv in "$@"; do
		key="${kv%%=*}"
		val="${kv#*=}"
		case "$key" in
		problem) problem="$val" ;;
		needs) needs="$val" ;;
		blocked_by) blocked_by="$val" ;;
		fix) fix="$val" ;;
		if_stuck) if_stuck="$val" ;;
		see) see="$val" ;;
		file) files="${files}${val}"$'\n' ;;
		*) printf 'secretguard_msg: unknown field %s\n' "$key" >&2 ;;
		esac
	done

	_secretguard_route _secretguard_msg_body
}

# secretguard_require TITLE [fields...]
#
# A capability this guard wants. strict -> message and return 1 (the caller
# exits). contributor -> warning and return 0, commit proceeds.
secretguard_require() {
	secretguard_resolve_mode
	local title="$1"
	shift
	if [ "$_secretguard_mode" = strict ]; then
		secretguard_msg BLOCKED "$title" "$@"
		return 1
	fi
	secretguard_msg warning "$title" "$@"
	return 0
}

# secretguard_block TITLE [fields...]
#
# Not negotiable in any mode. For the cases where continuing would write a
# secret into git in the clear. Always returns 1.
secretguard_block() {
	secretguard_msg BLOCKED "$1" "${@:2}"
	return 1
}

# secretguard_note TITLE [fields...] -- informational, never affects exit status.
secretguard_note() {
	secretguard_msg note "$1" "${@:2}"
	return 0
}
