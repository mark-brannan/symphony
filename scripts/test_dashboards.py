#!/usr/bin/env python3
"""
Offline checks on the generated Grafana dashboards. No network, no InfluxDB,
no Grafana -- safe to run in CI.

    python3 scripts/test_dashboards.py

What this catches that a JSON syntax check does not:

- committed JSON drifting from scripts/build_dashboards.py, which is what
  happens the first time someone edits a dashboard in the Grafana UI and
  exports it back into the repo
- a panel pointing at a datasource uid that provisioning does not create
- a unit/conversion mismatch, e.g. a panel labelled knots whose query forgot
  the m/s factor, or one labelled percent reading a raw 0..1 ratio. These
  render as confidently wrong numbers rather than as errors, which makes them
  the most expensive class of mistake here
- panels overlapping in the grid, or running off the 24-column edge
- a path the dev seeder has no values for, which would leave a panel blank in
  the local stack and send someone hunting a bug that is not there

Live checks that need the real thing are in verify_dashboards_live.py
(Grafana end-to-end) and audit_dashboard_paths.py (InfluxDB, on the boat).
"""
import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import build_dashboards as bd  # noqa: E402
import seed_dev_influx as seed  # noqa: E402

DASH_DIR = bd.OUT_DIR
DATASOURCE_YAML = os.path.join(
    REPO_ROOT, "grafana", "provisioning", "datasources", "influxdb.yaml")

failures = []


def fail(message):
    failures.append(message)


def load(filename):
    with open(os.path.join(DASH_DIR, filename)) as handle:
        return json.load(handle)


def check_regenerates_identically():
    """The committed JSON must be exactly what the spec produces."""
    for _title, _uid, filename, _desc, _panels, _refresh, _time in bd.DASHBOARDS:
        path = os.path.join(DASH_DIR, filename)
        if not os.path.exists(path):
            fail(f"{filename}: listed in DASHBOARDS but not committed")
            continue
        with open(path) as handle:
            committed = handle.read()
        bd._next_id[0] = 1
        regenerated = json.dumps(
            bd.build(_title, _uid, _desc, _panels, _refresh, _time),
            indent=2, sort_keys=True) + "\n"
        if committed != regenerated:
            fail(f"{filename}: committed JSON differs from build_dashboards.py "
                 "output -- run `python3 scripts/build_dashboards.py`")


def check_no_orphans():
    """Every JSON in the dashboards dir must come from the spec."""
    expected = {d[2] for d in bd.DASHBOARDS}
    for name in sorted(os.listdir(DASH_DIR)):
        if name.endswith(".json") and name not in expected:
            fail(f"{name}: present in {DASH_DIR} but not produced by "
                 "build_dashboards.py -- stale file?")


def provisioned_datasource_uid():
    with open(DATASOURCE_YAML) as handle:
        for line in handle:
            stripped = line.strip()
            if stripped.startswith("uid:"):
                return stripped.split(":", 1)[1].strip()
    return None


def check_datasource_uids():
    provisioned = provisioned_datasource_uid()
    if not provisioned:
        fail(f"{DATASOURCE_YAML}: no uid found")
        return
    for _t, _u, filename, *_ in bd.DASHBOARDS:
        dashboard = load(filename)
        for panel in dashboard["panels"]:
            if panel["type"] == "row":
                continue
            uid = (panel.get("datasource") or {}).get("uid")
            if uid != provisioned:
                fail(f"{filename}: panel {panel.get('title')!r} datasource uid "
                     f"{uid!r} != provisioned {provisioned!r}")
            for target in panel.get("targets", []):
                tuid = (target.get("datasource") or {}).get("uid")
                if tuid != provisioned:
                    fail(f"{filename}: panel {panel.get('title')!r} target "
                         f"{target.get('refId')} uid {tuid!r} != {provisioned!r}")


def check_query_shape():
    required = ["from(bucket:", "|> range(", 'r["_measurement"]',
                'r["_field"]', "|> keep(columns:"]
    for _t, _u, filename, *_ in bd.DASHBOARDS:
        dashboard = load(filename)
        for panel in dashboard["panels"]:
            for target in panel.get("targets", []):
                query = target.get("query", "")
                if not query.strip():
                    fail(f"{filename}: panel {panel.get('title')!r} target "
                         f"{target.get('refId')} has an empty query")
                    continue
                for fragment in required:
                    if fragment not in query:
                        fail(f"{filename}: panel {panel.get('title')!r} target "
                             f"{target.get('refId')} query is missing "
                             f"{fragment!r}")


# unit -> the conversion that must appear in the query for that unit to be
# truthful. Panels reading a path already in the display unit are exempt via
# EXEMPT below.
UNIT_REQUIRES = {
    bd.U_KNOT: "1.9438444924406",
    bd.U_DEG: "57.29577951308232",
    bd.U_F: "273.15",
    bd.U_HPA: "/ 100.0",
    bd.U_NM: "/ 1852.0",
}

# Paths whose stored value is already in the panel's display unit, so no
# conversion is expected. RSSI in dBm and the SwitchBot battery percentage are
# written by bt-sensors in display units, not SI.
EXEMPT_MEASUREMENTS = {
    "sensors.refrigerator.switchbot.battery",
    "sensors.refrigerator.switchbot.signalStrength",
    "sensors.houseBattery1.signalStrength",
    "sensors.houseBattery2.signalStrength",
    "electrical.chargers.VictronACCharger.signalStrength",
}

MEASUREMENT_RE = re.compile(r'r\["_measurement"\]\s*==\s*"([^"]+)"')


def check_unit_conversions():
    for _t, _u, filename, *_ in bd.DASHBOARDS:
        dashboard = load(filename)
        for panel in dashboard["panels"]:
            unit = (panel.get("fieldConfig", {})
                    .get("defaults", {}).get("unit"))
            if unit not in UNIT_REQUIRES:
                continue
            needed = UNIT_REQUIRES[unit]
            for target in panel.get("targets", []):
                query = target.get("query", "")
                measurements = MEASUREMENT_RE.findall(query)
                if any(m in EXEMPT_MEASUREMENTS for m in measurements):
                    continue
                if needed not in query:
                    fail(f"{filename}: panel {panel.get('title')!r} target "
                         f"{target.get('refId')} displays unit {unit!r} but its "
                         f"query has no {needed!r} conversion "
                         f"({', '.join(measurements)})")

            # A percent panel must be reading something scaled to percent.
            if unit == bd.U_PCT:
                for target in panel.get("targets", []):
                    query = target.get("query", "")
                    measurements = MEASUREMENT_RE.findall(query)
                    if any(m in EXEMPT_MEASUREMENTS for m in measurements):
                        continue
                    if "* 100.0" not in query and "used_percent" not in query \
                            and "usage_" not in query:
                        fail(f"{filename}: panel {panel.get('title')!r} target "
                             f"{target.get('refId')} displays percent but its "
                             f"query neither scales a ratio nor reads a "
                             f"percent field ({', '.join(measurements)})")


def check_layout():
    for _t, _u, filename, *_ in bd.DASHBOARDS:
        dashboard = load(filename)
        seen_ids, occupied = set(), set()
        for panel in dashboard["panels"]:
            pid = panel.get("id")
            if pid in seen_ids:
                fail(f"{filename}: duplicate panel id {pid}")
            seen_ids.add(pid)

            grid = panel["gridPos"]
            if grid["x"] + grid["w"] > 24:
                fail(f"{filename}: panel {panel.get('title')!r} runs past the "
                     f"grid edge (x={grid['x']} w={grid['w']})")
            if grid["w"] < 1 or grid["h"] < 1:
                fail(f"{filename}: panel {panel.get('title')!r} has zero size")
            for row in range(grid["y"], grid["y"] + grid["h"]):
                for col in range(grid["x"], grid["x"] + grid["w"]):
                    if (row, col) in occupied:
                        fail(f"{filename}: panel {panel.get('title')!r} "
                             f"overlaps another at ({col}, {row})")
                        break
                    occupied.add((row, col))


def check_seed_coverage():
    """Every referenced path must have seed values, or the dev stack lies."""
    known = (set(seed.RANGES) | set(seed.STRINGS) | set(seed.BOOLEANS)
             | set(seed.HOST_MEASUREMENTS) | {"navigation.position", "procstat"})
    referenced = set()
    for _t, _u, filename, *_ in bd.DASHBOARDS:
        dashboard = load(filename)
        for panel in dashboard["panels"]:
            for target in panel.get("targets", []):
                referenced.update(MEASUREMENT_RE.findall(target.get("query", "")))
    for measurement in sorted(referenced - known):
        fail(f"seed_dev_influx.py has no values for {measurement!r} -- it would "
             "be seeded 0..100, which is wrong for ratios, radians and Kelvin")


def check_uids_unique():
    seen = {}
    for _title, uid, filename, *_ in bd.DASHBOARDS:
        if uid in seen:
            fail(f"dashboard uid {uid!r} used by both {seen[uid]} and {filename}")
        seen[uid] = filename


def main():
    check_regenerates_identically()
    check_no_orphans()
    check_uids_unique()
    check_datasource_uids()
    check_query_shape()
    check_unit_conversions()
    check_layout()
    check_seed_coverage()

    if failures:
        print(f"{len(failures)} dashboard check(s) failed:")
        for message in failures:
            print(f"  {message}")
        return 1
    print(f"OK: {len(bd.DASHBOARDS)} dashboards pass structure, datasource, "
          "unit-conversion, layout and seed-coverage checks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
