#!/usr/bin/env bash
# Exits 1 and names each problem when a container of the compose project is
# crash-looping, unhealthy, built from somewhere other than the main
# checkout, or bind-mounting a path that no longer exists.
#
# Why: `restart: unless-stopped` loops forever and autoheal only acts on
# containers that report `unhealthy`, so a crash-looping container with no
# healthcheck raises nothing. signalk-server restarted 9,776 times over five
# weeks (2026-09-04..2026-10-15) and grafana 9,871 times; no one was told.
#
#   scripts/check_dev_containers.sh        # exit 0 and silent when all is well
#
# Run per prompt by .claude/hooks/warn-broken-dev-containers.sh.
set -uo pipefail

command -v docker >/dev/null 2>&1 && command -v jq >/dev/null 2>&1 || exit 0
ids=$(docker ps -aq --filter label=com.docker.compose.project=symphony 2>/dev/null) || exit 0
[ -n "$ids" ] || exit 0

main=$(cd "$(dirname "$0")/.." && dirname "$(realpath "$(git rev-parse --git-common-dir)")")

# shellcheck disable=SC2086 # ids is a newline-separated list of hex ids
problems=$(docker inspect $ids | jq -r --arg main "$main" --argjson now "$(date +%s)" '
  .[] | (.Name | ltrimstr("/")) as $n
  | (.Config.Labels["com.docker.compose.project.working_dir"] // "") as $wd
  | (if .State.Restarting or .State.Status == "restarting" then
       "\($n): crash-looping (RestartCount \(.RestartCount), last exit \(.State.ExitCode))"
     elif .RestartCount >= 10 and ($now - (.State.StartedAt | sub("\\.[0-9]+Z$"; "Z") | fromdateiso8601)) < 600 then
       "\($n): restarted \(.RestartCount) times and only just came up"
     else empty end),
    (if .State.Health.Status == "unhealthy" then "\($n): unhealthy" else empty end),
    (if $wd != "" and $wd != $main then "\($n): created from \($wd), not the main checkout \($main) -- its bind mounts die with that directory" else empty end),
    (.Mounts[] | select(.Type == "bind") | "BIND \($n) \(.Source)")
' | while IFS= read -r line; do
	case "$line" in
	BIND\ *)
		rest=${line#BIND }
		name=${rest%% *}
		src=${rest#* }
		[ -e "$src" ] || echo "$name: bind mount source $src does not exist"
		;;
	*) echo "$line" ;;
	esac
done)
[ -z "$problems" ] && exit 0
printf '%s\n' "$problems"
exit 1
