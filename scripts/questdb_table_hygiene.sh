#!/usr/bin/env bash
# Give QuestDB's line-protocol tables a finite retention and idempotent writes.
#
#   scripts/questdb_table_hygiene.sh            # 30 days, http://127.0.0.1:9000
#   scripts/questdb_table_hygiene.sh 90         # 90 days
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
# The history plugin's own tables (signalk, signalk_str, signalk_position) are
# skipped: the plugin creates them with dedup already on and drops aged
# partitions itself from its retentionDays setting. A second mechanism on the
# same data would make it unclear which one did the deleting.
set -euo pipefail

DAYS=${1:-30}
QUESTDB_URL=${QUESTDB_URL:-http://127.0.0.1:9000}

case "$DAYS" in
  ''|*[!0-9]*) echo "retention must be a whole number of days, got: $DAYS" >&2; exit 2 ;;
esac
[ "$DAYS" -gt 0 ] || { echo "retention must be greater than 0 days" >&2; exit 2; }

query() {
  curl -sf -G "$QUESTDB_URL/exec" --data-urlencode "query=$1"
}

# Rows: table_name, ttlValue, dedup. Skipping the plugin's tables and QuestDB's
# own bookkeeping here rather than in the loop keeps the reported counts honest.
rows=$(query "select table_name, ttlValue, dedup from tables()
              where table_name not in ('signalk', 'signalk_str', 'signalk_position')
                and not table_name like 'sys.%'
                and not table_name like 'telemetry%'" |
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

ttl_set=0 dedup_set=0 failed=0
while read -r name ttl dedup; do
  [ -n "$name" ] || continue
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
[ "$failed" -eq 0 ]
