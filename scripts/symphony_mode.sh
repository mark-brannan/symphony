#!/usr/bin/env bash
# Shared by every local guard: which mode this clone is in, and one format
# for the message a guard prints when something is missing.
#
# Source it, don't run it:
#
#     . "$(git rev-parse --show-toplevel)/scripts/symphony_mode.sh"
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
#   1. $SYMPHONY_STRICT      (1/true/yes/on/strict, or 0/false/no/off/contributor)
#   2. $CI / $GITHUB_ACTIONS strict, always. CI has no age key and no filters,
#                            so auto-detection would call it a contributor and
#                            wave through exactly the gaps CI exists to catch.
#   3. .symphony-mode        (one word at the repo root)
#   4. auto-detect           strict iff an age key is available AND both git
#                            filters are configured; contributor otherwise.
#
# Auto-detection is never silent: every message this file formats carries a
# `mode:` line naming the mode and how it was decided, so a guard can't be
# quietly in the wrong one.
#
# There is a python twin, scripts/symphony_mode.py, resolving mode by the
# same rules and formatting messages identically -- guards exist in both
# languages. scripts/test_symphony_mode.py asserts the two agree.
#
# What this does NOT relax: staging a file that .gitattributes covers with
# filter=sops, without the filter having run, hard-fails in EVERY mode. That
# is the one case where the permissive path would put a cleartext secret in
# a public repo. Use symphony_block for those, never symphony_require.

SYMPHONY_MODE="${SYMPHONY_MODE:-}"
SYMPHONY_MODE_REASON="${SYMPHONY_MODE_REASON:-}"

_symphony_repo_root() {
	git rev-parse --show-toplevel 2>/dev/null || pwd
}

_symphony_have_age_key() {
	if [ -n "${SOPS_AGE_KEY_FILE:-}" ] && [ -f "${SOPS_AGE_KEY_FILE}" ]; then
		return 0
	fi
	[ -f "$HOME/.config/sops/age/keys.txt" ]
}

_symphony_filters_configured() {
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
_symphony_dest() {
	if [ -t 2 ]; then
		printf '/dev/stderr'
	elif { : >/dev/tty; } 2>/dev/null; then
		printf '/dev/tty'
	else
		printf '/dev/stderr'
	fi
}

_symphony_lower() {
	printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

symphony_resolve_mode() {
	if [ -n "$SYMPHONY_MODE" ]; then
		return 0
	fi

	local raw lowered root line key filters missing
	raw="${SYMPHONY_STRICT:-}"
	lowered="$(_symphony_lower "$raw")"
	case "$lowered" in
	1 | true | yes | on | strict)
		SYMPHONY_MODE=strict
		SYMPHONY_MODE_REASON="SYMPHONY_STRICT=$raw"
		return 0
		;;
	0 | false | no | off | contributor)
		SYMPHONY_MODE=contributor
		SYMPHONY_MODE_REASON="SYMPHONY_STRICT=$raw"
		return 0
		;;
	"") : ;;
	*) printf 'symphony: ignoring unrecognized SYMPHONY_STRICT=%s\n' "$raw" >&2 ;;
	esac

	if [ -n "${CI:-}" ] || [ -n "${GITHUB_ACTIONS:-}" ]; then
		SYMPHONY_MODE=strict
		SYMPHONY_MODE_REASON="CI"
		return 0
	fi

	root="$(_symphony_repo_root)"
	if [ -f "$root/.symphony-mode" ]; then
		line="$(grep -vE '^[[:space:]]*(#|$)' "$root/.symphony-mode" 2>/dev/null |
			head -n1 | tr -d '[:space:]')"
		line="$(_symphony_lower "$line")"
		case "$line" in
		strict | contributor)
			SYMPHONY_MODE="$line"
			SYMPHONY_MODE_REASON=".symphony-mode says $line"
			return 0
			;;
		"") : ;;
		*) printf 'symphony: ignoring unrecognized .symphony-mode value %s\n' "$line" >&2 ;;
		esac
	fi

	key=no
	filters=no
	if _symphony_have_age_key; then key=yes; fi
	if _symphony_filters_configured; then filters=yes; fi

	if [ "$key" = yes ] && [ "$filters" = yes ]; then
		SYMPHONY_MODE=strict
		SYMPHONY_MODE_REASON="auto-detected: age key available, git filters configured"
	else
		missing=""
		if [ "$key" = no ]; then missing="no age key"; fi
		if [ "$filters" = no ]; then
			missing="${missing:+$missing, }git filters not configured"
		fi
		SYMPHONY_MODE=contributor
		SYMPHONY_MODE_REASON="auto-detected: $missing"
	fi
}

symphony_mode() {
	symphony_resolve_mode
	printf '%s\n' "$SYMPHONY_MODE"
}

symphony_mode_reason() {
	symphony_resolve_mode
	printf '%s\n' "$SYMPHONY_MODE_REASON"
}

# symphony_msg LEVEL TITLE [problem=...] [file=...]... [needs=...]
#              [blocked_by=...] [fix=...] [see=...]
#
# Every guard message in this repo has this shape. Fields print in a fixed
# order, absent ones are skipped, `file=` may repeat, and the `mode:` line
# is always last and always present.
symphony_msg() {
	symphony_resolve_mode
	local level="$1" title="$2"
	shift 2

	local problem="" needs="" blocked_by="" fix="" see="" files="" kv key val
	for kv in "$@"; do
		key="${kv%%=*}"
		val="${kv#*=}"
		case "$key" in
		problem) problem="$val" ;;
		needs) needs="$val" ;;
		blocked_by) blocked_by="$val" ;;
		fix) fix="$val" ;;
		see) see="$val" ;;
		file) files="${files}${val}"$'\n' ;;
		*) printf 'symphony_msg: unknown field %s\n' "$key" >&2 ;;
		esac
	done

	{
		printf '\nsymphony %s: %s\n' "$level" "$title"
		if [ -n "$problem" ]; then printf '  problem:    %s\n' "$problem"; fi
		if [ -n "$files" ]; then
			while IFS= read -r val; do
				if [ -n "$val" ]; then printf '  file:       %s\n' "$val"; fi
			done <<<"$files"
		fi
		if [ -n "$needs" ]; then printf '  needs:      %s\n' "$needs"; fi
		if [ -n "$blocked_by" ]; then printf '  blocked by: %s\n' "$blocked_by"; fi
		if [ -n "$fix" ]; then printf '  fix:        %s\n' "$fix"; fi
		if [ -n "$see" ]; then printf '  see:        %s\n' "$see"; fi
		printf '  mode:       %s (%s)\n' "$SYMPHONY_MODE" "$SYMPHONY_MODE_REASON"
	} >"$(_symphony_dest)"
}

# symphony_require TITLE [fields...]
#
# A capability this guard wants. strict -> message and return 1 (the caller
# exits). contributor -> warning and return 0, commit proceeds.
symphony_require() {
	symphony_resolve_mode
	local title="$1"
	shift
	if [ "$SYMPHONY_MODE" = strict ]; then
		symphony_msg BLOCKED "$title" "$@"
		return 1
	fi
	symphony_msg warning "$title" "$@"
	return 0
}

# symphony_block TITLE [fields...]
#
# Not negotiable in any mode. For the cases where continuing would write a
# secret into git in the clear. Always returns 1.
symphony_block() {
	symphony_msg BLOCKED "$1" "${@:2}"
	return 1
}

# symphony_note TITLE [fields...] -- informational, never affects exit status.
symphony_note() {
	symphony_msg note "$1" "${@:2}"
	return 0
}
