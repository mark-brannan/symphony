#!/usr/bin/env bash
# Give QuestDB's Telegraf tables a finite retention and idempotent writes.
#
#   scripts/questdb_table_hygiene.sh            # 30 days, http://127.0.0.1:9000
#   scripts/questdb_table_hygiene.sh 90         # 90 days
#   scripts/questdb_table_hygiene.sh 30 cpu mem # only these tables
#   QUESTDB_URL=http://questdb:9000 scripts/questdb_table_hygiene.sh
#
# Telegraf's tables are created by the line-protocol writer, not by us, so they
# arrive with no TTL and no deduplication keys:
#
#   * No TTL means they grow until the disk is full. This filled the boat's
#     root filesystem on 2026-08-20.
#   * No dedup keys means a retry can double-write. Telegraf retries a batch
#     whose HTTP response timed out, and QuestDB may already have committed it,
#     so the same samples land twice — which also skews the row-count parity
#     check that gates retiring InfluxDB.
#
# A table dropped and recreated, or a Telegraf input added later, comes back
# without both again, silently — which is why this is a script to re-run rather
# than a one-time ALTER. It only touches what is missing, so re-running is free.
#
# **It only ever alters tables it is told to own.** Setting a TTL deletes data
# at the far end, so "every table that looks unmanaged" is the wrong default:
# a table someone created by hand, deliberately without a TTL, would be quietly
# put on a 30-day deletion clock. So the managed set is the explicit list below
# (Telegraf's measurements on this boat, as at 2026-08-20) plus any table named
# on the command line. Anything else is reported and left alone — including the
# history plugin's own signalk tables, which arrive with dedup already on and
# whose retention the plugin manages from its own retentionDays setting.
#
# Adding a Telegraf input means adding its measurement here. The report at the
# end is what tells you that: an unmanaged table with no TTL is either a new
# Telegraf measurement that belongs in this list, or someone else's table that
# does not.
set -euo pipefail

# Known to be owned by someone else, so not managed here and not worth
# reporting as unowned: the history plugin creates these with dedup on and
# ages their partitions out from its own retentionDays setting.
PLUGIN_TABLES="signalk signalk_str signalk_position"

TELEGRAF_TABLES="
chrony cpu disk diskio kernel mem net processes procstat procstat_lookup
rpi_health swap system systemd_units temp
internal_agent internal_gather internal_memstats internal_parser internal_write
"

DAYS=${1:-30}
shift || true
QUESTDB_URL=${QUESTDB_URL:-http://127.0.0.1:9000}

case "$DAYS" in
  ''|*[!0-9]*) echo "retention must be a whole number of days, got: $DAYS" >&2; exit 2 ;;
esac
[ "$DAYS" -gt 0 ] || { echo "retention must be greater than 0 days" >&2; exit 2; }

# Named tables replace the built-in list rather than adding to it: naming a
# table is how you say "this one, nothing else."
managed=${*:-$TELEGRAF_TABLES}

query() {
  curl -sf --connect-timeout 5 --max-time 30 \
    -G "$QUESTDB_URL/exec" --data-urlencode "query=$1"
}

is_managed() {
  for t in $managed; do [ "$t" = "$1" ] && return 0; done
  return 1
}

rows=$(query "select table_name, ttlValue, dedup from tables()" |
  python3 -c 'import json,sys
for name, ttl, dedup in json.load(sys.stdin)["dataset"]:
    print(name, ttl, dedup)')

# Dedup keys have to include the designated timestamp; the SYMBOL columns are
# the tag set, which is what makes a host-metric row unique.
dedup_keys() {
  query "select \"column\", type from table_columns('$1')" |
    python3 -c 'import json,sys
cols = json.load(sys.stdin)["dataset"]
keys = [c for c, t in cols if t == "SYMBOL"]
print(",".join(f'"'"'"{k}"'"'"' for k in ["timestamp", *keys]))'
}

ttl_set=0 dedup_set=0 failed=0 unmanaged=""
while read -r name ttl dedup; do
  [ -n "$name" ] || continue
  if ! is_managed "$name"; then
    case " $PLUGIN_TABLES " in *" $name "*) continue ;; esac
    case "$name" in sys.*|telemetry*) continue ;; esac
    [ "$ttl" = "0" ] && unmanaged="$unmanaged $name"
    continue
  fi
  if [ "$ttl" = "0" ]; then
    if query "ALTER TABLE \"$name\" SET TTL $DAYS DAYS" >/dev/null; then
      echo "  $name -> TTL $DAYS days"
      ttl_set=$((ttl_set + 1))
    else
      echo "  $name -> TTL FAILED" >&2
      failed=$((failed + 1))
    fi
  fi
  if [ "$dedup" = "False" ]; then
    keys=$(dedup_keys "$name")
    if query "ALTER TABLE \"$name\" DEDUP ENABLE UPSERT KEYS($keys)" >/dev/null; then
      echo "  $name -> dedup on ($keys)"
      dedup_set=$((dedup_set + 1))
    else
      echo "  $name -> dedup FAILED" >&2
      failed=$((failed + 1))
    fi
  fi
done <<EOF
$rows
EOF

echo "$ttl_set table(s) given a $DAYS-day TTL, $dedup_set given dedup keys, $failed failure(s)"
if [ -n "$unmanaged" ]; then
  echo "unrecognised, left alone, no TTL:${unmanaged}"
  echo "  (a new Telegraf measurement belongs in TELEGRAF_TABLES; anything else"
  echo "   is someone's own table and its retention is their call)"
fi
[ "$failed" -eq 0 ]
