#!/usr/bin/env python3
"""
Runs every provisioned panel's query through a live Grafana and reports which
ones come back with data.

    python3 scripts/verify_dashboards_live.py \
        --grafana http://localhost:3001 --user admin --password devadmin

Works against the local dev stack (scripts/dev_stack.sh) and against the
boat's real Grafana. On the boat it is the honest end-to-end check: a panel
that passes here has a working datasource uid, a valid token, a datasource in
Flux mode pointed at the right org and bucket, and a path that is actually
publishing. Any one of those being wrong shows up as an empty panel in the
browser and as a FAIL here.

This complements scripts/audit_dashboard_paths.py rather than replacing it.
The audit asks InfluxDB directly whether a measurement exists; this asks
Grafana whether the panel can draw it. The audit can pass while this fails --
that gap is exactly the datasource wiring.

Exit status:
    0  every panel returned at least one row
    1  at least one panel returned nothing
"""
import argparse
import base64
import glob
import json
import os
import sys
import urllib.error
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASH_DIR = os.path.join(REPO_ROOT, "grafana", "provisioning", "dashboards", "json")


def panels_with_targets():
    """Yield (dashboard file, panel title, refId, target) per non-empty target."""
    for path in sorted(glob.glob(os.path.join(DASH_DIR, "*.json"))):
        with open(path) as handle:
            dashboard = json.load(handle)
        label = os.path.basename(path)
        for panel in dashboard.get("panels", []):
            title = panel.get("title") or panel["type"]
            for target in panel.get("targets", []):
                if not target.get("rawSql", "").strip():
                    continue
                yield label, title, target.get("refId", "A"), target


def make_caller(base_url, user, password, token):
    def call(path, payload=None, method=None):
        url = base_url.rstrip("/") + path
        data = json.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("Accept", "application/json")
        if data is not None:
            request.add_header("Content-Type", "application/json")
        if token:
            request.add_header("Authorization", "Bearer " + token)
        else:
            raw = f"{user}:{password}".encode()
            request.add_header("Authorization",
                               "Basic " + base64.b64encode(raw).decode())
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read().decode()
        return json.loads(body) if body else {}
    return call


def frame_rows(result):
    """Total rows across every frame in one /api/ds/query result."""
    rows = 0
    for frame in result.get("frames", []) or []:
        values = frame.get("data", {}).get("values") or []
        if values:
            rows += max(len(column) for column in values)
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grafana", default="http://localhost:3001")
    parser.add_argument("--user", default="admin")
    parser.add_argument("--password", default=os.environ.get("GF_PASSWORD", ""))
    parser.add_argument("--token", default=os.environ.get("GF_TOKEN", ""),
                        help="service account token, instead of user/password")
    parser.add_argument("--from", dest="time_from", default="now-24h")
    parser.add_argument("--to", dest="time_to", default="now")
    parser.add_argument("--quiet", action="store_true",
                        help="print only failures and the summary")
    args = parser.parse_args()

    call = make_caller(args.grafana, args.user, args.password, args.token)

    try:
        health = call("/api/health")
    except urllib.error.URLError as exc:
        sys.exit(f"cannot reach Grafana at {args.grafana}: {exc}")
    print(f"grafana {health.get('version', '?')} "
          f"database={health.get('database', '?')}")

    datasources = {ds["uid"]: ds for ds in call("/api/datasources")}
    for uid, ds in sorted(datasources.items()):
        version = (ds.get("jsonData") or {}).get("version", "InfluxQL")
        print(f"datasource {uid}: type={ds['type']} url={ds.get('url')} "
              f"queryLanguage={version}")

    failures, empty, passed = [], [], 0
    for label, title, ref, target in panels_with_targets():
        where = f"{label}: {title} [{ref}]"
        uid = (target.get("datasource") or {}).get("uid")
        if uid not in datasources:
            failures.append((where, f"datasource uid {uid!r} is not provisioned"))
            continue
        payload = {
            "from": args.time_from,
            "to": args.time_to,
            "queries": [{
                "refId": ref,
                "datasource": target["datasource"],
                # The QuestDB datasource's own query model: raw SQL, plus the
                # frame format the panel expects (0 time series, 1 table).
                # The macros in the SQL are expanded by the plugin's backend
                # from the from/to and intervalMs sent alongside.
                "queryType": "sql",
                "rawSql": target["rawSql"],
                "format": target.get("format", 0),
                "intervalMs": 60000,
                "maxDataPoints": 500,
            }],
        }
        try:
            response = call("/api/ds/query", payload)
        except urllib.error.HTTPError as exc:
            failures.append((where, f"HTTP {exc.code}: {exc.read().decode()[:200]}"))
            continue
        result = (response.get("results") or {}).get(ref, {})
        if result.get("error"):
            failures.append((where, result["error"][:200]))
            continue
        rows = frame_rows(result)
        if rows == 0:
            empty.append(where)
        else:
            passed += 1
            if not args.quiet:
                print(f"  ok    {where}  ({rows} rows)")

    total = passed + len(empty) + len(failures)
    print(f"\n{total} panel queries: {passed} returned data, "
          f"{len(empty)} empty, {len(failures)} errored")

    if empty:
        print("\nEMPTY (query ran, no rows -- path not publishing, or "
              "outside the time range):")
        for where in empty:
            print(f"  {where}")
    if failures:
        print("\nERRORED:")
        for where, reason in failures:
            print(f"  {where}\n      {reason}")

    return 1 if (empty or failures) else 0


if __name__ == "__main__":
    sys.exit(main())
