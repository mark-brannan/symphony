#!/usr/bin/env python3
"""
Fills a development QuestDB with synthetic vessel and host data, so the
provisioned dashboards can be looked at without being aboard.

    python3 scripts/seed_dev_questdb.py --url http://localhost:9000

NOT for the boat. It writes into whatever QuestDB you point it at and the
values are invented. Point it at a throwaway instance.

What it seeds comes from the dashboards themselves: audit_dashboard_paths
extracts every (table, measurement) pair the generated JSON references, and
this fills exactly those. A panel added to the spec is therefore seeded on
the next run without anyone remembering to add it here.

Value ranges are shared with seed_dev_influx.py rather than duplicated. They
are in SignalK's SI units -- m/s, radians, Kelvin, ratios 0..1 -- because
seeding in display units would make a broken conversion in a panel look
correct, which is the one thing this must not do.

## Why the tables are pre-created

Everything is written over the influx line protocol, which QuestDB accepts on
:9000/write. ILP on its own would name the timestamp column `timestamp`, and
the SignalK history provider names it `ts` -- so the three signalk tables are
created first with `TIMESTAMP(ts)`, and ILP then writes into that existing
column. The Telegraf tables want `timestamp` and so are left to ILP.
"""
import argparse
import math
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seed_dev_influx as seed  # noqa: E402
from audit_dashboard_paths import referenced_by_table  # noqa: E402

CONTEXT = "self"

# Tag columns the panels filter on, per table. A panel pinned to one instance
# (disk to `/`, net to eth0) draws nothing unless the seeded rows carry that
# tag value, so these have to match scripts/build_dashboards.py.
TABLE_TAGS = {
    "disk": {"host": "dev", "path": "/", "device": "mmcblk0p2"},
    "diskio": {"host": "dev", "name": "mmcblk0"},
    "net": {"host": "dev", "interface": "eth0"},
    "cpu": {"host": "dev", "cpu": "cpu-total"},
    "storage_bucket_series_num": {"bucket": "symphony"},
}
DEFAULT_TAGS = {"host": "dev"}


def esc_tag(text):
    return (text.replace("\\", "\\\\").replace(",", r"\,")
            .replace(" ", r"\ ").replace("=", r"\="))


def esc_str(text):
    return text.replace("\\", "\\\\").replace('"', r"\"")


def exec_sql(url, sql):
    query = urllib.parse.urlencode({"query": sql})
    req = urllib.request.Request(f"{url.rstrip('/')}/exec?{query}")
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode()


def write_ilp(url, lines, chunk=5000):
    endpoint = f"{url.rstrip('/')}/write?precision=n"
    for start in range(0, len(lines), chunk):
        body = "\n".join(lines[start:start + chunk]).encode()
        req = urllib.request.Request(endpoint, data=body, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                resp.read()
        except urllib.error.HTTPError as exc:
            sys.exit(f"write failed ({exc.code}): {exc.read().decode()[:400]}")


def create_signalk_tables(url):
    for ddl in (
        "CREATE TABLE IF NOT EXISTS signalk (ts TIMESTAMP, path SYMBOL,"
        " context SYMBOL, value DOUBLE) TIMESTAMP(ts) PARTITION BY DAY WAL",
        "CREATE TABLE IF NOT EXISTS signalk_str (ts TIMESTAMP, path SYMBOL,"
        " context SYMBOL, value_str STRING) TIMESTAMP(ts) PARTITION BY DAY WAL",
        "CREATE TABLE IF NOT EXISTS signalk_position (ts TIMESTAMP,"
        " context SYMBOL, lat DOUBLE, lon DOUBLE) TIMESTAMP(ts)"
        " PARTITION BY DAY WAL",
    ):
        exec_sql(url, ddl)


def build_lines(by_table, points, step_s):
    now_ns = int(time.time() * 1e9)
    lines, unranged = [], set()

    for index in range(points):
        ts = now_ns - (points - 1 - index) * step_s * int(1e9)
        phase = index / max(points - 1, 1) * math.pi * 4

        for table, measurements in by_table.items():
            for measurement in measurements:
                tag = f"path={esc_tag(measurement)},context={CONTEXT}"

                if table == "signalk_position":
                    lat = seed.wave(47.62, 47.66, phase, 0.01)
                    lon = seed.wave(-122.38, -122.34, phase * 0.7, 0.01)
                    lines.append(
                        f"signalk_position,context={CONTEXT} "
                        f"lat={lat},lon={lon} {ts}")
                elif table == "signalk_str":
                    if measurement in seed.BOOLEANS:
                        value = "false" if (index % 97) == 0 else "true"
                    else:
                        options = seed.STRINGS.get(measurement, ["ok"])
                        span = max(points // (len(options) * 3), 1)
                        value = options[(index // span) % len(options)]
                    lines.append(
                        f'signalk_str,{tag} value_str="{esc_str(value)}" {ts}')
                elif table == "signalk":
                    if measurement in seed.RANGES:
                        low, high = seed.RANGES[measurement]
                    else:
                        # Seed it anyway so a new panel is never silently
                        # blank, but say so: 0..100 is wrong for a ratio or a
                        # radian and renders as an obvious conversion bug.
                        unranged.add(measurement)
                        low, high = 0.0, 100.0
                    lines.append(
                        f"signalk,{tag} value={seed.wave(low, high, phase)} {ts}")
                elif table == "procstat":
                    for unit in seed.PROCSTAT_UNITS:
                        rss = seed.wave(4.0e7, 5.0e8, phase)
                        lines.append(
                            f"procstat,host=dev,systemd_unit={esc_tag(unit)} "
                            f"memory_rss={rss} {ts}")
                else:
                    fields = seed.HOST_MEASUREMENTS.get(table)
                    if not fields:
                        unranged.add(table)
                        fields = {"value": (0.0, 100.0)}
                    tags = TABLE_TAGS.get(table, DEFAULT_TAGS)
                    tag_str = ",".join(f"{k}={esc_tag(v)}"
                                       for k, v in tags.items())
                    body = ",".join(f"{name}={seed.wave(low, high, phase)}"
                                    for name, (low, high) in fields.items())
                    lines.append(f"{table},{tag_str} {body} {ts}")

    return lines, unranged


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:9000",
                        help="QuestDB HTTP endpoint (default %(default)s)")
    parser.add_argument("--hours", type=float, default=24.0,
                        help="how far back to seed (default %(default)s)")
    parser.add_argument("--step", type=int, default=60,
                        help="seconds between points (default %(default)s)")
    args = parser.parse_args()

    by_table = referenced_by_table()
    if not by_table:
        sys.exit("no measurements found in the provisioned dashboards")

    points = max(int(args.hours * 3600 / args.step), 2)
    create_signalk_tables(args.url)
    lines, unranged = build_lines(by_table, points, args.step)
    write_ilp(args.url, lines)

    print(f"seeded {len(lines)} points across {len(by_table)} tables "
          f"({args.hours}h at {args.step}s)")
    if unranged:
        print("no explicit range, seeded 0..100 (add one to "
              "seed_dev_influx.RANGES): " + ", ".join(sorted(unranged)))


if __name__ == "__main__":
    sys.exit(main())
