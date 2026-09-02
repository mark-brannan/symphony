#!/usr/bin/env python3
"""
Lists every measurement the provisioned Grafana dashboards reference, and
which panel references it.

    python3 scripts/audit_dashboard_paths.py

Why it exists: a Grafana panel pointed at a path nothing publishes doesn't
error. It draws an empty graph, which is indistinguishable from "the sensor
was quiet." That failure mode is how five dashboards ported from another
vessel sat in this repo looking plausible while roughly sixty percent of
their panels could never have drawn anything.

This used to also ask InfluxDB whether each measurement was live. That half
was never ported when the dashboards moved to QuestDB SQL; the live question
is now answered end-to-end by scripts/verify_dashboards_live.py, or directly
by the QuestDB queries in RUNBOOK.md -> "Checking the real thing".
"""
import glob
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASH_DIR = os.path.join(REPO_ROOT, "grafana", "provisioning", "dashboards", "json")

# The dashboards are QuestDB SQL: a SignalK path appears as a `path = '...'`
# filter against the signalk/signalk_str tables, and a Telegraf metric as the
# table name itself. `navigation.position` has neither -- it is the whole of
# the signalk_position table -- so it is named from the table.
PATH_RE = re.compile(r"path = '([^']+)'")
TABLE_RE = re.compile(r"FROM (\w+)")
SIGNALK_TABLES = {"signalk", "signalk_str"}


def referenced_measurements():
    """measurement -> sorted list of "dashboard: panel" that reference it."""
    found = {}
    for _table, measurement, where in _references():
        found.setdefault(measurement, set()).add(where)
    return {m: sorted(v) for m, v in found.items()}


def referenced_by_table():
    """table -> {measurement -> sorted list of "dashboard: panel"}."""
    found = {}
    for table, measurement, where in _references():
        found.setdefault(table, {}).setdefault(measurement, set()).add(where)
    return {b: {m: sorted(v) for m, v in ms.items()} for b, ms in found.items()}


def _references():
    for path in sorted(glob.glob(os.path.join(DASH_DIR, "*.json"))):
        with open(path) as f:
            dash = json.load(f)
        label = os.path.basename(path)
        for panel in dash.get("panels", []):
            for target in panel.get("targets", []):
                query = target.get("rawSql", "")
                tables = TABLE_RE.findall(query)
                table = tables[0] if tables else "?"
                where = f"{label}: {panel.get('title') or panel['type']}"
                # Telegraf's `disk` table also has a `path` tag, so only take
                # `path = '...'` as a SignalK path on a SignalK table.
                paths = PATH_RE.findall(query) if table in SIGNALK_TABLES else []
                if paths:
                    for measurement in paths:
                        yield table, measurement, where
                elif table == "signalk_position":
                    yield table, "navigation.position", where
                elif table != "?":
                    yield table, table, where


def main():
    by_table = referenced_by_table()
    if not by_table:
        sys.exit("no measurements found in " + DASH_DIR)
    total = 0
    for table in sorted(by_table):
        print(table)
        for measurement, wheres in sorted(by_table[table].items()):
            total += 1
            print(f"  {measurement}")
            for where in wheres:
                print(f"      {where}")
    print(f"\n{total} measurement references across {len(by_table)} table(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
