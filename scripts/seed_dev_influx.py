#!/usr/bin/env python3
"""
Fills a development InfluxDB with synthetic data shaped exactly like the
boat's, so the provisioned dashboards can be brought up and looked at without
being aboard.

    python3 scripts/seed_dev_influx.py --url http://localhost:8086 \
        --token dev-token --org symphony

Buckets are created if absent and chosen per measurement by the same routing
the dashboards use (build_dashboards.bucket_for), so seeded data lands where
the panels look for it.

NOT for the boat. It writes to whatever bucket you point it at, and the
values are invented. Point it at a throwaway InfluxDB.

The measurement list comes from the dashboards themselves, so seeding covers
exactly what the panels ask for and nothing else -- add a panel, reseed, and
the new path has data. Values are generated in SignalK's SI units (m/s,
radians, Kelvin, Pascals, ratios) because that is what the real writer
stores and what the panels' conversions expect. Seeding in display units
would make a broken conversion look correct.
"""
import argparse
import json
import math
import os
import random
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit_dashboard_paths import referenced_measurements  # noqa: E402
from build_dashboards import bucket_for  # noqa: E402

# Plausible SI ranges per path, so a seeded dashboard looks like a boat rather
# than like noise. (low, high) for a slow sinusoid plus jitter.
RANGES = {
    "navigation.speedOverGround": (0.0, 4.0),
    "navigation.courseOverGroundTrue": (0.0, 6.28),
    "navigation.headingMagnetic": (0.0, 6.28),
    "navigation.magneticVariation": (0.24, 0.29),
    "navigation.attitude.roll": (-0.25, 0.25),
    "navigation.attitude.pitch": (-0.08, 0.08),
    "navigation.trip.log": (0.0, 40000.0),
    "navigation.gnss.satellites": (7, 14),
    "navigation.gnss.satellitesInView": (12, 22),
    "navigation.gnss.horizontalDilution": (0.6, 1.8),
    "navigation.gnss.positionDilution": (1.0, 2.6),
    "navigation.gnss.antennaAltitude": (-2.0, 8.0),
    "environment.outside.temperature": (281.0, 295.0),
    "environment.outside.feelsLikeTemperature": (280.0, 294.0),
    "environment.outside.dewPointTemperature": (277.0, 287.0),
    "environment.outside.relativeHumidity": (0.45, 0.95),
    "environment.outside.cloudCover": (0.0, 1.0),
    "environment.outside.pressure": (100200.0, 102400.0),
    "environment.outside.pressure.oneHourAgo": (100200.0, 102400.0),
    "environment.outside.pressure.threeHoursAgo": (100200.0, 102400.0),
    "environment.outside.pressure.twelveHoursAgo": (100200.0, 102400.0),
    "environment.outside.pressure.oneHourDelta": (-120.0, 120.0),
    "environment.outside.pressure.threeHoursDelta": (-320.0, 320.0),
    "environment.outside.wind.speed": (0.0, 12.0),
    "environment.outside.wind.gust": (0.0, 18.0),
    "environment.outside.wind.direction": (0.0, 6.28),
    "environment.wind.speedTrue": (0.0, 12.0),
    "environment.wind.directionTrue": (0.0, 6.28),
    "environment.inside.refrigerator.temperature": (275.0, 280.0),
    "environment.inside.refrigerator.humidity": (0.3, 0.6),
    "environment.inside.relativeHumidity": (0.4, 0.7),
    "environment.tide.heightNow": (-0.5, 3.2),
    "environment.tide.heightHigh": (2.8, 3.4),
    "environment.tide.heightLow": (-0.8, 0.2),
    "environment.moon.fraction": (0.0, 1.0),
    "environment.rpi.cpu.temperature": (313.0, 341.0),
    "environment.rpi.gpu.temperature": (312.0, 339.0),
    "environment.rpi.memory.utilisation": (0.35, 0.82),
    "environment.rpi.sd.utilisation": (0.55, 0.78),
    "environment.rpi.uptime": (0.0, 900000.0),
    "environment.noaa.swpc.kp.observed": (0.0, 7.0),
    "environment.noaa.swpc.kp.forecast.max24h": (0.0, 7.0),
    "environment.noaa.swpc.solar_wind.speed": (300.0, 700.0),
    "environment.noaa.swpc.solar_wind.Bz": (-15.0, 15.0),
    "environment.noaa.swpc.f107": (90.0, 190.0),
    "electrical.batteries.house.voltage": (12.6, 14.2),
    "electrical.batteries.house.current": (-45.0, 60.0),
    "electrical.batteries.house.power": (-560.0, 780.0),
    "electrical.batteries.house.capacity.stateOfCharge": (0.42, 1.0),
    "electrical.batteries.house.capacity.timeRemaining": (7200.0, 190000.0),
    "electrical.batteries.house.capacity.consumedCharge": (0.0, 900000.0),
    "electrical.batteries.house.capacity.dischargeSinceFull": (0.0, 700000.0),
    "electrical.batteries.house.capacity.dischargedEnergy": (0.0, 9000000.0),
    "electrical.venus.dcPower": (-560.0, 780.0),
    "sensors.refrigerator.switchbot.battery": (35.0, 100.0),
    "sensors.refrigerator.switchbot.signalStrength": (-95.0, -55.0),
    "sensors.houseBattery1.signalStrength": (-95.0, -55.0),
    "sensors.houseBattery2.signalStrength": (-95.0, -55.0),
    "electrical.chargers.VictronACCharger.signalStrength": (-95.0, -55.0),
}

# The two JBD packs, generated rather than listed twice. A 4S LiFePO4 pack:
# cells around 3.2-3.45 V, so the pack sits near 13 V.
for _pack in ("0146", "5C90"):
    RANGES.update({
        f"electrical.batteries.{_pack}.voltage": (12.9, 13.8),
        f"electrical.batteries.{_pack}.current": (-24.0, 30.0),
        f"electrical.batteries.{_pack}.temperature": (283.0, 300.0),
        f"electrical.batteries.{_pack}.cycles": (18, 26),
        f"electrical.batteries.{_pack}.capacity.stateOfCharge": (0.42, 1.0),
        f"electrical.batteries.{_pack}.capacity.remaining": (120000.0, 360000.0),
    })
    for _cell in range(4):
        RANGES[f"electrical.batteries.{_pack}.cell{_cell}.voltage"] = (3.21, 3.45)

# Paths whose value is a string, and the states to cycle through.
STRINGS = {
    "navigation.state": ["moored", "anchored", "sailing", "motoring"],
    "steering.autopilot.state": ["standby", "auto", "route"],
    "steering.autopilot.engaged": ["false", "true"],
    "electrical.venus.state": ["Absorption", "Bulk", "Float", "Inverting"],
    "electrical.chargers.VictronACCharger.state": ["off", "bulk", "absorption", "float"],
    "electrical.switches.venus-0.state": ["off", "on"],
    "electrical.switches.venus-1.state": ["off", "on"],
    "electrical.venus-input.1.state": ["open", "closed"],
    "electrical.venus-input.2.state": ["open", "closed"],
    "electrical.venus-input.4.state": ["open", "closed"],
    "navigation.gnss.methodQuality": ["GNSS Fix", "DGNSS fix"],
    "navigation.gnss.type": ["GPS+GLONASS"],
    "environment.outside.pressure.trend.tendency": ["RISING", "FALLING", "STEADY"],
    "environment.outside.pressure.trend.severity": ["0", "1", "2"],
    "environment.outside.pressure.system": ["High", "Low", "Normal"],
    "environment.outside.pressure.prediction.front.prognose": [
        "No change", "Worsening", "Improving"],
    "environment.outside.pressure.prediction.front.wind": [
        "Backing", "Veering", "Steady"],
    "environment.tide.state": ["rising", "falling", "high", "low"],
    "environment.sunlight.times.sunrise": ["2026-08-14T05:53:00.000Z"],
    "environment.sunlight.times.sunset": ["2026-08-14T20:32:00.000Z"],
    "environment.moon.phaseName": ["Waxing Gibbous"],
    "environment.noaa.swpc.xray_flare.class": ["C2.1", "M1.4", "B7.8"],
    "electrical.batteries.0146.protectionStatus": ["OK"],
    "electrical.batteries.5C90.protectionStatus": ["OK"],
    "electrical.batteries.0146.FETStatus": ["charging,discharging"],
    "electrical.batteries.5C90.FETStatus": ["charging,discharging"],
}

BOOLEANS = {
    "sensors.House_Battery_1_A5_C2_37_40_01_46.reachable",
    "sensors.House_Battery_2_A5_C2_37_3C_5C_90.reachable",
    "sensors.SwitchBotTH_Fridge_Thermometer_CE_B5_52_72_1C_81.reachable",
    "sensors.Victron_Blue_Smart_IP22_Charger_12_30_3_D2_2A_6F_EF_DB_36.reachable",
}

# Telegraf and InfluxDB-internal measurements: no `self` tag, named fields.
HOST_MEASUREMENTS = {
    "cpu": {"usage_active": (2.0, 60.0), "usage_iowait": (0.0, 12.0),
            "usage_system": (1.0, 25.0)},
    "mem": {"used_percent": (35.0, 85.0), "available": (4.0e8, 2.4e9)},
    "swap": {"used_percent": (0.0, 40.0)},
    "disk": {"used_percent": (55.0, 79.0)},
    "diskio": {"write_bytes": (1.0e9, 4.0e9), "read_bytes": (1.0e9, 3.0e9)},
    "system": {"load1": (0.2, 3.5), "load5": (0.2, 3.0), "load15": (0.2, 2.5)},
    "processes": {"blocked": (0, 3)},
    "net": {"bytes_recv": (1.0e8, 9.0e8), "bytes_sent": (1.0e8, 6.0e8)},
    "chrony": {"last_offset": (-0.004, 0.004)},
    "internal_write": {"metrics_dropped": (0, 0), "write_errors": (0, 0),
                       "buffer_size": (0, 400)},
    "rpi_health": {
        "under_voltage_now": (0, 0), "throttled_now": (0, 0),
        "freq_capped_now": (0, 0), "soft_temp_limit_now": (0, 0),
        "under_voltage_since_boot": (0, 1), "throttled_since_boot": (0, 0),
        "freq_capped_since_boot": (0, 0), "soft_temp_limit_since_boot": (0, 0),
    },
    "storage_bucket_series_num": {"value": (1200, 2600)},
}

PROCSTAT_UNITS = ["signalk.service", "influxdb.service", "grafana-server.service",
                  "caddy.service", "dex.service"]

CONTEXT = "vessels.urn:mrn:imo:mmsi:368391180"


def escape_key(text):
    return text.replace(",", r"\,").replace(" ", r"\ ").replace("=", r"\=")


def escape_str(text):
    return text.replace('"', r"\"").replace("\\", r"\\")


def wave(low, high, phase, jitter=0.04):
    mid, half = (low + high) / 2.0, (high - low) / 2.0
    value = mid + half * math.sin(phase)
    return value + random.uniform(-half * jitter, half * jitter)


def build_lines(measurements, points, step_s, unranged=None):
    """Yield (bucket, line-protocol) pairs.

    Bucket comes from the same routing the dashboards use, so seeded data
    lands where the panels look for it. Getting this wrong would leave every
    panel blank in the local stack for a reason that has nothing to do with
    the dashboards being wrong.
    """
    now_ns = int(time.time() * 1e9)
    lines = []
    if unranged is None:
        unranged = set()
    for index in range(points):
        ts = now_ns - (points - 1 - index) * step_s * int(1e9)
        phase = index / max(points - 1, 1) * math.pi * 4

        for measurement in measurements:
            key = escape_key(measurement)
            base = f"{key},context={escape_key(CONTEXT)},source=dev,self=true"
            vessel_bucket = bucket_for(measurement, True)

            if measurement in STRINGS:
                options = STRINGS[measurement]
                value = options[(index // max(points // (len(options) * 3), 1))
                                % len(options)]
                lines.append((vessel_bucket, f'{base} value="{escape_str(value)}" {ts}'))
            elif measurement in BOOLEANS:
                value = "false" if (index % 97) == 0 else "true"
                lines.append((vessel_bucket, f"{base} value={value} {ts}"))
            elif measurement == "navigation.position":
                lat = wave(47.62, 47.66, phase, 0.01)
                lon = wave(-122.38, -122.34, phase * 0.7, 0.01)
                lines.append((vessel_bucket, f"{base} lat={lat},lon={lon} {ts}"))
            elif measurement in RANGES:
                low, high = RANGES[measurement]
                lines.append((vessel_bucket, f"{base} value={wave(low, high, phase)} {ts}"))
            elif measurement in HOST_MEASUREMENTS or measurement == "procstat":
                continue  # handled below: no self tag, and named fields
            else:
                # Anything the dashboards reference with no explicit range:
                # still seed it, so a new panel is never silently empty, but
                # say so. A 0..100 default is wrong for most SignalK paths --
                # a ratio seeded that way renders as 5138% once the panel
                # multiplies by 100, which looks like a conversion bug in the
                # dashboard rather than a gap in this table.
                unranged.add(measurement)
                lines.append((vessel_bucket, f"{base} value={wave(0.0, 100.0, phase)} {ts}"))

        for measurement, fields in HOST_MEASUREMENTS.items():
            if measurement not in measurements:
                continue
            if measurement == "storage_bucket_series_num":
                tags = "bucket=symphony"
            else:
                tags = "host=dev"
            body = ",".join(
                f"{name}={wave(low, high, phase)}"
                for name, (low, high) in fields.items())
            lines.append((bucket_for(measurement, False), f"{measurement},{tags} {body} {ts}"))

        if "procstat" in measurements:
            for unit in PROCSTAT_UNITS:
                rss = wave(4.0e7, 5.0e8, phase)
                lines.append((
                    bucket_for("procstat", False),
                    f"procstat,host=dev,systemd_unit={escape_key(unit)} "
                    f"memory_rss={rss} {ts}"))

    return lines


def ensure_bucket(url, token, org, bucket, retention_seconds=0):
    """Create the bucket if it isn't there. Idempotent."""
    base = url.rstrip("/")

    def api(path, data=None, method=None):
        req = urllib.request.Request(base + path, data=data, method=method)
        req.add_header("Authorization", "Token " + token)
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode() or "{}")

    existing = api(f"/api/v2/buckets?name={bucket}")
    if existing.get("buckets"):
        return
    org_id = api(f"/api/v2/orgs?org={org}")["orgs"][0]["id"]
    payload = json.dumps({
        "orgID": org_id,
        "name": bucket,
        "retentionRules": ([{"type": "expire",
                             "everySeconds": retention_seconds}]
                           if retention_seconds else []),
    }).encode()
    api("/api/v2/buckets", payload, "POST")
    print(f"created bucket {bucket}")


def write(url, token, org, bucket, lines, chunk=4000):
    endpoint = (f"{url.rstrip('/')}/api/v2/write?org={org}"
                f"&bucket={bucket}&precision=ns")
    for start in range(0, len(lines), chunk):
        payload = "\n".join(lines[start:start + chunk]).encode()
        req = urllib.request.Request(endpoint, data=payload, method="POST")
        req.add_header("Authorization", "Token " + token)
        req.add_header("Content-Type", "text/plain; charset=utf-8")
        with urllib.request.urlopen(req, timeout=120) as response:
            if response.status not in (200, 204):
                raise SystemExit(f"write failed: {response.status}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8086")
    parser.add_argument("--token", required=True)
    parser.add_argument("--org", default="symphony")
    parser.add_argument("--hours", type=float, default=24.0,
                        help="how far back to seed (default 24)")
    parser.add_argument("--step", type=int, default=60,
                        help="seconds between points (default 60)")
    parser.add_argument("--seed", type=int, default=1,
                        help="RNG seed, so runs are reproducible")
    args = parser.parse_args()

    random.seed(args.seed)
    measurements = sorted(referenced_measurements())
    points = max(int(args.hours * 3600 / args.step), 2)
    unranged = set()
    lines = build_lines(measurements, points, args.step, unranged)

    by_bucket = {}
    for bucket, line in lines:
        by_bucket.setdefault(bucket, []).append(line)

    print(f"seeding {len(measurements)} measurements x {points} points "
          f"= {len(lines)} lines across {len(by_bucket)} bucket(s)")
    if unranged:
        print(f"WARNING: {len(unranged)} path(s) have no entry in RANGES "
              "and were seeded 0..100, which is wrong for ratios, "
              "radians and Kelvin:")
        for name in sorted(unranged):
            print(f"  {name}")
    for bucket in sorted(by_bucket):
        ensure_bucket(args.url, args.token, args.org, bucket)
        write(args.url, args.token, args.org, bucket, by_bucket[bucket])
        print(f"  {bucket}: {len(by_bucket[bucket])} lines")
    print("done")


if __name__ == "__main__":
    main()
