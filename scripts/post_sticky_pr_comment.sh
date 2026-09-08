#!/bin/sh
# Post (or update in place) the Claude review's one top-level summary
# comment on a PR, instead of leaving a fresh comment behind on every push.
# PR #44 collected a dozen "Claude finished" comments this way before this
# script existed, and someone had to hide them by hand as outdated.
#
# Usage: scripts/post_sticky_pr_comment.sh <pr-number>
#   Reads the comment body from stdin.
#
# Finds the existing claude[bot] comment carrying MARKER on this PR and
# PATCHes it; if none exists yet (first review, or the fingerprint cache
# missed), falls back to `gh pr comment` to create one. A lookup failure
# (rate limit, API hiccup) also falls back to creating a new comment rather
# than silently posting nothing -- one extra comment costs a scroll, a
# missing review costs a genuine second opinion.

set -eu

MARKER="<!-- claude-review-summary: do not edit, this comment updates in place -->"

pr="${1:?usage: post_sticky_pr_comment.sh <pr-number> (body on stdin)}"

body_file="$(mktemp)"
trap 'rm -f "$body_file"' EXIT
{
	printf '%s\n\n' "$MARKER"
	cat
} >"$body_file"

repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner)"

existing_id="$(
	gh api "repos/${repo}/issues/${pr}/comments" --paginate \
		--jq "[.[] | select(.user.login == \"claude[bot]\" and (.body // \"\" | contains(\"${MARKER}\")))] | last | .id // empty" \
		2>/dev/null
)" || existing_id=""

if [ -n "$existing_id" ]; then
	gh api -X PATCH "repos/${repo}/issues/comments/${existing_id}" -F body=@"${body_file}" >/dev/null
else
	gh pr comment "$pr" --body-file "$body_file"
fi
