#!/usr/bin/env python3
"""
Checks every InfluxDB measurement referenced by the provisioned Grafana
dashboards against what the boat's InfluxDB has actually seen.

Run this ON THE BOAT -- it reads the InfluxDB token out of the live
signalk-to-influxdb2 plugin config and talks to localhost:8086.

    python3 scripts/audit_dashboard_paths.py

Why it exists: a Grafana panel pointed at a path nothing publishes doesn't
error. It draws an empty graph, which is indistinguishable from "the sensor
was quiet." That failure mode is how five dashboards ported from another
vessel sat in this repo looking plausible while roughly sixty percent of
their panels could never have drawn anything. This turns that into a
non-zero exit code.

Exit status:
    0  every referenced measurement has data in the recent window
    1  at least one is missing entirely, or was last seen outside it
"""
import argparse
import glob
import json
import os
import re
import sys
import urllib.error
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASH_DIR = os.path.join(REPO_ROOT, "grafana", "provisioning", "dashboards", "json")

MEASUREMENT_RE = re.compile(r'r\["_measurement"\]\s*==\s*"([^"]+)"')
BUCKET_RE = re.compile(r'from\(bucket:\s*"([^"]+)"\)')


def referenced_measurements():
    """measurement -> sorted list of "dashboard: panel" that reference it."""
    found = {}
    for _bucket, measurement, where in _references():
        found.setdefault(measurement, set()).add(where)
    return {m: sorted(v) for m, v in found.items()}


def referenced_by_bucket():
    """bucket -> {measurement -> sorted list of "dashboard: panel"}."""
    found = {}
    for bucket, measurement, where in _references():
        found.setdefault(bucket, {}).setdefault(measurement, set()).add(where)
    return {b: {m: sorted(v) for m, v in ms.items()} for b, ms in found.items()}


def _references():
    for path in sorted(glob.glob(os.path.join(DASH_DIR, "*.json"))):
        with open(path) as f:
            dash = json.load(f)
        label = os.path.basename(path)
        for panel in dash.get("panels", []):
            for target in panel.get("targets", []):
                query = target.get("query", "")
                buckets = BUCKET_RE.findall(query)
                bucket = buckets[0] if buckets else "?"
                where = f"{label}: {panel.get('title') or panel['type']}"
                for measurement in MEASUREMENT_RE.findall(query):
                    yield bucket, measurement, where


def influx_client():
    home = os.path.expanduser("~")
    candidates = sorted(glob.glob(
        os.path.join(home, ".signalk", "plugin-config-data",
                     "signalk-to-influxdb2.json")))
    if not candidates:
        sys.exit("no signalk-to-influxdb2.json under " + home
                 + " -- this script has to run on the boat")
    config = json.load(open(candidates[0]))["configuration"]["influxes"][0]
    token = config["token"]
    if token.startswith("ENC["):
        sys.exit("token is still sops-encrypted in " + candidates[0])

    def call(path, data=None, ctype=None, accept="application/json"):
        req = urllib.request.Request("http://localhost:8086" + path, data=data)
        req.add_header("Authorization", "Token " + token)
        req.add_header("Accept", accept)
        if ctype:
            req.add_header("Content-type", ctype)
        return urllib.request.urlopen(req, timeout=120).read().decode()

    org = json.loads(call("/api/v2/orgs"))["orgs"][0]["name"]
    return call, org


def measurements_since(call, org, bucket, window):
    flux = ('import "influxdata/influxdb/schema"\n'
            f'schema.measurements(bucket: "{bucket}", start: {window})')
    csv = call("/api/v2/query?org=" + org, flux.encode(),
               "application/vnd.flux", "application/csv")
    out = set()
    for line in csv.splitlines():
        if line.startswith("#"):
            continue
        parts = line.split(",")
        if len(parts) > 3 and parts[3] and parts[3] != "_value":
            out.add(parts[3])
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--window", default="-24h",
                        help="freshness window, Flux duration (default -24h)")
    parser.add_argument("--history", default="-30d",
                        help="window treated as 'has ever existed' (default -30d)")
    args = parser.parse_args()

    by_bucket = referenced_by_bucket()
    if not by_bucket:
        sys.exit("no measurements found in " + DASH_DIR)

    call, org = influx_client()
    print(f"org={org}")

    all_stale, all_missing, total, live_count = [], [], 0, 0
    for bucket in sorted(by_bucket):
        referenced = by_bucket[bucket]
        total += len(referenced)
        try:
            fresh = measurements_since(call, org, bucket, args.window)
            historic = measurements_since(call, org, bucket, args.history)
        except urllib.error.HTTPError as exc:
            print(f"\nbucket {bucket}: CANNOT QUERY ({exc.code}) -- "
                  "does it exist, and does the token read it?")
            all_missing.extend((bucket, m, referenced[m]) for m in referenced)
            continue

        missing = sorted(m for m in referenced if m not in historic)
        stale = sorted(m for m in referenced if m in historic and m not in fresh)
        live = sorted(m for m in referenced if m in fresh)
        live_count += len(live)
        all_stale.extend((bucket, m, referenced[m]) for m in stale)
        all_missing.extend((bucket, m, referenced[m]) for m in missing)

        print(f"  bucket {bucket}: {len(referenced)} referenced, "
              f"{len(live)} live, {len(stale)} stale, {len(missing)} missing")

    print(f"\n{total} measurement references across {len(by_bucket)} bucket(s); "
          f"{live_count} live within {args.window}")

    if all_stale:
        print(f"\nSTALE (no data in {args.window}):")
        for bucket, m, wheres in all_stale:
            print(f"  [{bucket}] {m}")
            for where in wheres:
                print(f"      {where}")

    if all_missing:
        print(f"\nMISSING (nothing in {args.history}):")
        for bucket, m, wheres in all_missing:
            print(f"  [{bucket}] {m}")
            for where in wheres:
                print(f"      {where}")

    return 1 if (all_missing or all_stale) else 0


if __name__ == "__main__":
    sys.exit(main())
