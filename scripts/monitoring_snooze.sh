#!/usr/bin/env bash
# The suppress button for the boat's off-boat alarms.
#
#   scripts/monitoring_snooze.sh status [pi|halos|all]   show each check's state
#   scripts/monitoring_snooze.sh pause  [pi|halos|all]   silence it (default: pi)
#   scripts/monitoring_snooze.sh resume [pi|halos|all]   un-silence by hand
#
# Why this exists: `boat-heartbeat` pings healthchecks.io every 5 minutes and
# silence is the alarm, so any planned outage -- a card swap, a reboot into a
# rebuild, pulling power at the panel -- pages Mark through Pushover for doing
# the maintenance on purpose. Pausing the check is the off-boat equivalent of
# the suppress button on a ship's alarm panel.
#
# It suppresses at the receiving end, not on the boat, which is the only thing
# that can work here: during a card swap the Pi is powered off and the new card
# is a different rootfs, so nothing stored on the boat survives to un-suppress
# itself. Server-side pause does.
#
# It self-clears. healthchecks.io leaves the paused state on the next ping
# (`manual_resume` is off), so the first heartbeat from whichever card ends up
# aboard resumes alerting -- `resume` here is for abandoning a swap without
# booting anything. Two checks exist because the HALOS card pings its own; a
# swap normally wants `pause pi`, since the halos check starts alerting the
# moment that card first pings and then goes quiet.
#
# Prefer letting a ping clear the pause over running `resume`. Measured
# 2026-09-03: a paused check that gets pinged goes straight back to `up` with
# its ping history intact, while `resume` puts the check in `new` and reports
# `last ping never` until something pings it again. Neither state alerts, so
# `resume` is safe -- it just throws away the history you would want if the
# swap goes wrong.
#
# This does not touch Pushover directly, and doesn't need to: the heartbeat's
# own Pushover paths (early warning, "monitoring is down") and SignalK's
# notification relay all run *on* the Pi, so a powered-off boat sends nothing.
# healthchecks.io's silence alarm is the only channel still live, and this is it.
#
# Reads `healthchecks_api_key` and the `heartbeat_url_*` ping URLs from
# secrets/symphony.sops.yaml; the check's UUID is the last path segment of its
# ping URL. Run it from a laptop, never from the boat -- a script that has to
# reach the box it is silencing is useless for the case it exists for.
#
# Verify: `scripts/monitoring_snooze.sh status` prints `paused` for the check
# you paused. Confirm it cleared after the swap the same way -- `up` means
# pings are landing again and alerting is live.
set -euo pipefail

cd "$(dirname "$0")/.."

usage() { sed -n '2,6p' "$0"; exit 2; }

CMD="${1:-status}"
TARGET="${2:-}"
case "$CMD" in
  status) TARGET="${TARGET:-all}" ;;
  pause|resume) TARGET="${TARGET:-pi}" ;;
  *) usage ;;
esac
case "$TARGET" in pi|halos|all) ;; *) usage ;; esac

for tool in sops curl python3; do
  command -v "$tool" >/dev/null || { echo "missing: $tool" >&2; exit 1; }
done

SECRETS=secrets/symphony.sops.yaml
KEY=$(sops --decrypt --extract '["healthchecks_api_key"]' "$SECRETS")
API=https://healthchecks.io/api/v3

uuid_for() { # uuid_for <pi|halos>
  sops --decrypt --extract "[\"heartbeat_url_symphony_$1\"]" "$SECRETS" | sed 's#.*/##'
}

hc() { # hc <method> <path>
  curl -sf -X "$1" "${API}$2" -H "X-Api-Key: ${KEY}"
}

show() { # show <name> <uuid>
  hc GET "/checks/$2" | python3 -c '
import json,sys
c = json.load(sys.stdin)
print("%-6s %-8s last ping %s" % (sys.argv[1], c.get("status","?"), c.get("last_ping") or "never"))
' "$1"
}

act() { # act <name> <uuid> <pause|resume>
  hc POST "/checks/$2/$3" >/dev/null
  echo "$1: $3d"
  show "$1" "$2"
}

targets=$([ "$TARGET" = all ] && echo "pi halos" || echo "$TARGET")
for name in $targets; do
  id=$(uuid_for "$name")
  case "$CMD" in
    status) show "$name" "$id" ;;
    *)      act "$name" "$id" "$CMD" ;;
  esac
done
