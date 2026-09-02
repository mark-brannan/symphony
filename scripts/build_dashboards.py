#!/usr/bin/env python3
"""
Generates grafana/provisioning/dashboards/json/*.json from the panel spec
below.

Why a generator and not hand-written JSON: a Grafana dashboard is ~10 KB of
boilerplate per screen, and the part that actually matters -- which SignalK
path a panel reads, and how its SI value is converted for display -- is about
one line of it. Editing the JSON directly means every path change is a hunt
through fieldConfig noise, and it makes "does any panel reference a path the
boat doesn't publish?" unanswerable without a script anyway. So the spec is
the source of truth and the JSON is build output. Regenerate with:

    python3 scripts/build_dashboards.py

The generated files ARE committed -- Grafana provisioning reads files, not
this script, and the boat has no build step. Treat a hand-edit of the JSON
the way you'd treat a hand-edit of any generated file: it will be lost.

Grafana's file provider is configured `editable: true`, so panels can still
be tweaked in the UI to try something out. Those tweaks live only in
Grafana's database and are overwritten on the next provisioning reload.
Anything worth keeping comes back here.

## The write schema this targets

signalk-questdb-history-provider writes every SignalK path into one of three
QuestDB tables, with the path in a `path` column rather than as a table name:

    signalk           ts, path, context, source, value        (numeric)
    signalk_str       ts, path, context, source, value_str, value_kind
    signalk_position  ts, context, source, lat, lon

`context` is `self` for this vessel's own data -- there is no `self` tag as
there was in InfluxDB. Telegraf writes host metrics as its own tables (`cpu`,
`mem`, `disk`, `procstat`, ...) with one column per field and `timestamp` as
the designated timestamp, which is why non-SignalK panels pass
self_only=False: that flag picks the table shape, not just a filter.

Values are stored in SignalK's canonical SI units -- m/s, radians, Kelvin,
Pascals, ratios 0..1. Nothing converts them on the way in, so every panel
that wants knots, degrees, Fahrenheit or percent converts on the way out.
That is what the CONV_* constants are for. Getting this wrong is silent: a
gauge reading 3.6 instead of 7 knots looks like slow going, not a bug.

## Path selection

Every measurement referenced here was confirmed present in the boat's
history store. Paths the reference dashboards used but this boat does not publish
(depth, apparent wind, tanks, propulsion, solar, LTE) are deliberately absent
rather than left in as empty panels -- see reference/signalk_paths.md.
"""
import json
import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO_ROOT, "grafana", "provisioning", "dashboards", "json")

# The QuestDB datasource plugin (questdb-questdb-datasource, Postgres wire
# on 8812). The uid is fixed here and must match the uid in
# grafana/provisioning/datasources/questdb.yaml -- Grafana otherwise assigns
# a random one at startup and every panel comes up empty rather than erroring.
DS = {"type": "questdb-questdb-datasource", "uid": "questdb-symphony"}

# Grafana frame format, as the plugin's Format enum: 0 timeseries, 1 table.
# String-valued panels (state timelines, text stats) and the position query
# come back as tables; numeric series and stats as time series.
FORMAT_TIMESERIES = 0
FORMAT_TABLE = 1

# Set to True once 0146 is wired in parallel with 5C90 and the two packs are
# actually a bank. Until then they are not peers: 5C90 carries the load (it
# tracks the Victron shunt to within 10 mV) and 0146 is a spare sitting
# disconnected with its terminals plugged. Both advertise the same BLE name,
# DP04S007L4S200A, so only the MAC tells them apart.
#
# This changes labelling only -- the paths are identical either way, so
# flipping it and regenerating is the whole change when the wiring is done.
PACKS_PARALLELED = False

_PACK_ROLE = {"5C90": "House", "0146": "Spare"}


def pack_row(pack):
    if PACKS_PARALLELED:
        return ROW(f"Battery pack {pack}")
    state = "wired in" if pack == "5C90" else "disconnected, stored"
    return ROW(f"{_PACK_ROLE[pack]} pack {pack} -- {state}")


def pack_label(pack, what):
    prefix = "Pack" if PACKS_PARALLELED else _PACK_ROLE[pack]
    return f"{prefix} {pack} {what}"



# --------------------------------------------------------------------------
# Tables.
#
# QuestDB has no bucket concept: retention is a per-table TTL, and everything
# the history provider writes lands in these three tables, split by value type
# rather than by writer. Telegraf's tables are named after its input plugins
# and are addressed by the measurement name itself (see sql() below).
# --------------------------------------------------------------------------
TABLE_SIGNALK = "signalk"
TABLE_SIGNALK_STR = "signalk_str"
TABLE_POSITION = "signalk_position"

# --------------------------------------------------------------------------
# Unit conversions: SignalK SI -> what a person reads. Each is a SQL
# expression template; `{v}` is substituted with the column or aggregate the
# query selects, so the same constant works for a raw value and for avg(value).
#
# The vessel's own unit preset is nautical-imperial-us (the captain's
# applicationData), while the server default is nautical-metric. These follow
# the captain's preset, except barometric pressure, which stays in hPa/mbar
# because the barometer-trend plugin's own Beaufort and front predictions are
# computed in hPa and would be inconsistent read alongside inHg.
# --------------------------------------------------------------------------
CONV_MS_TO_KN = "{v} * 1.9438444924406"
CONV_RAD_TO_DEG = "{v} * 57.29577951308232"
CONV_K_TO_F = "({v} - 273.15) * 9.0 / 5.0 + 32.0"
CONV_RATIO_TO_PCT = "{v} * 100.0"
CONV_PA_TO_HPA = "{v} / 100.0"
CONV_M_TO_NM = "{v} / 1852.0"
CONV_M_TO_FT = "{v} * 3.280839895"
CONV_COULOMB_TO_AH = "{v} / 3600.0"
CONV_JOULE_TO_WH = "{v} / 3600.0"
CONV_NEGATE = "{v} * -1.0"

U_KNOT = "velocityknot"
U_DEG = "degree"
U_F = "fahrenheit"
U_PCT = "percent"
U_HPA = "pressurehpa"
U_VOLT = "volt"
U_AMP = "amp"
U_WATT = "watt"
U_SECONDS = "s"
U_NM = "suffix: nm"
U_FT = "lengthft"
U_AH = "suffix: Ah"
U_WH = "watth"
U_NONE = "none"
U_SHORT = "short"
U_BYTES = "decbytes"
U_CELSIUS = "celsius"

GREEN = "green"
YELLOW = "yellow"
ORANGE = "orange"
RED = "red"
BLUE = "blue"
TEXT = "text"


def steps(*pairs):
    """Threshold steps. First entry must have a null value (the base colour)."""
    return [{"color": c, "value": v} for v, c in pairs]


BASE = steps((None, TEXT))


# --------------------------------------------------------------------------
# QuestDB SQL query construction
#
# Macros are the QuestDB Grafana plugin's, not Grafana's generic SQL ones:
#   $__timeFilter(col)     -> col >= cast(<from> as timestamp) AND col <= ...
#   $__sampleByInterval    -> the panel interval as 1d / 5h / 20s / 500T
# $__interval is deliberately not used with SAMPLE BY: it renders as `1ms`,
# which QuestDB does not accept as a sample unit.
# --------------------------------------------------------------------------
AGG = {"mean": "avg", "max": "max", "min": "min", "sum": "sum", "last": "last"}


def sql(measurement, conv=None, mode="series", field="value", self_only=True,
        extra_filters=(), fn="mean", table=None):
    """
    Build a QuestDB SQL query for one SignalK path or Telegraf field.

    mode:
      "series" -- downsampled numeric time series
      "last"   -- single most recent point (stat/gauge)
      "state"  -- string values downsampled by last(), for state timelines
      "text"   -- single most recent string value

    self_only says the data was written by the SignalK history provider, which
    means the `signalk`/`signalk_str` tables keyed by `path` and filtered to
    context 'self'. Telegraf's metrics are not written that way: each input
    plugin gets its own table, the measurement name IS the table name, and the
    field is a column. Anything not written by SignalK must pass
    self_only=False or the query is nonsense, not merely empty.
    """
    string_mode = mode in ("state", "text")
    if self_only:
        table = table or (TABLE_SIGNALK_STR if string_mode else TABLE_SIGNALK)
        time_col = "ts"
        value_col = "value_str" if table == TABLE_SIGNALK_STR else "value"
        where = [f"path = '{measurement}'", "context = 'self'"]
    else:
        table = table or measurement
        time_col = "timestamp"
        value_col = field
        where = []
    where.append(f"$__timeFilter({time_col})")
    for key, value in extra_filters:
        where.append(f"{key} = '{value}'")

    if mode in ("series", "state"):
        expr = f"{AGG['last' if mode == 'state' else fn]}({value_col})"
        if conv:
            expr = conv.format(v=expr)
        tail = ["SAMPLE BY $__sampleByInterval"]
    else:
        expr = conv.format(v=value_col) if conv else value_col
        tail = [f"ORDER BY {time_col} DESC", "LIMIT 1"]

    return "\n".join([
        f"SELECT {time_col} AS time, {expr} AS value",
        f"FROM {table}",
        "WHERE " + " AND ".join(where),
    ] + tail)


def sql_position():
    """Positions are their own table, with lat and lon as separate columns."""
    return "\n".join([
        "SELECT ts AS time, last(lat) AS lat, last(lon) AS lon",
        f"FROM {TABLE_POSITION}",
        "WHERE context = 'self' AND $__timeFilter(ts)",
        "SAMPLE BY $__sampleByInterval",
    ])


# --------------------------------------------------------------------------
# Panel spec DSL. Each entry describes one panel; layout is computed.
# --------------------------------------------------------------------------
class Panel:
    def __init__(self, kind, title, w, h, **kw):
        self.kind = kind
        self.title = title
        self.w = w
        self.h = h
        self.kw = kw


def ROW(title):
    return Panel("row", title, 24, 1)


def STAT(title, measurement, conv=None, unit=U_NONE, w=3, h=4, decimals=1,
         thresholds=None, self_only=True, field="value", mappings=None,
         text_mode=None):
    return Panel("stat", title, w, h, measurement=measurement, conv=conv,
                 unit=unit, decimals=decimals, thresholds=thresholds,
                 self_only=self_only, field=field, mappings=mappings,
                 text_mode=text_mode)


def GAUGE(title, measurement, conv=None, unit=U_NONE, w=4, h=6, decimals=1,
          vmin=0, vmax=100, thresholds=None, self_only=True, field="value"):
    return Panel("gauge", title, w, h, measurement=measurement, conv=conv,
                 unit=unit, decimals=decimals, vmin=vmin, vmax=vmax,
                 thresholds=thresholds, self_only=self_only, field=field)


def TS(title, series, unit=U_NONE, w=12, h=8, decimals=1, fill=10,
       thresholds=None, stack=False, points=False):
    """series: list of (legend, measurement, conv) or (legend, measurement, conv, opts)."""
    return Panel("timeseries", title, w, h, series=series, unit=unit,
                 decimals=decimals, fill=fill, thresholds=thresholds,
                 stack=stack, points=points)


def STATE(title, series, w=12, h=6, mappings=None):
    """series: list of (legend, measurement) rendered as a state timeline."""
    return Panel("state-timeline", title, w, h, series=series, mappings=mappings)


def GEOMAP(title, w=12, h=10):
    return Panel("geomap", title, w, h)


def TEXTVAL(title, measurement, w=6, h=4, self_only=True, string=True):
    """
    A stat panel showing a path's latest value as text.

    string=False for the handful of paths a plugin publishes as a numeric
    code rather than a word -- they live in `signalk`, not `signalk_str`,
    and a query against the wrong table returns nothing at all.
    """
    return Panel("textval", title, w, h, measurement=measurement,
                 self_only=self_only, string=string)


# --------------------------------------------------------------------------
# Panel rendering
# --------------------------------------------------------------------------
_next_id = [1]


def _pid():
    _next_id[0] += 1
    return _next_id[0]


def _field_config(unit, decimals, thresholds, vmin=None, vmax=None,
                  mappings=None, custom=None):
    defaults = {
        "color": {"mode": "thresholds"},
        "mappings": mappings or [],
        "thresholds": {
            "mode": "absolute",
            "steps": thresholds if thresholds else BASE,
        },
        "unit": unit,
    }
    if decimals is not None:
        defaults["decimals"] = decimals
    if vmin is not None:
        defaults["min"] = vmin
    if vmax is not None:
        defaults["max"] = vmax
    if custom:
        defaults["custom"] = custom
    return {"defaults": defaults, "overrides": []}


def _target(query, ref="A", fmt=FORMAT_TIMESERIES):
    # The plugin reads `rawSql` and `format`; `selectedFormat` is what the
    # query editor shows, and leaving it unset makes an edit in the UI flip
    # the panel back to Auto. queryType "sql" keeps the editor in raw-SQL
    # mode rather than its visual builder.
    return {"datasource": DS, "format": fmt, "queryType": "sql",
            "rawSql": query, "refId": ref, "selectedFormat": fmt}


def _render(panel, x, y):
    grid = {"h": panel.h, "w": panel.w, "x": x, "y": y}
    k = panel.kw

    if panel.kind == "row":
        return {
            "type": "row", "title": panel.title, "id": _pid(),
            "gridPos": grid, "collapsed": False, "panels": [],
        }

    if panel.kind == "stat":
        q = sql(k["measurement"], k["conv"], "last", k["field"], k["self_only"])
        return {
            "type": "stat", "title": panel.title, "id": _pid(),
            "gridPos": grid, "datasource": DS, "targets": [_target(q)],
            "fieldConfig": _field_config(k["unit"], k["decimals"],
                                         k["thresholds"], mappings=k["mappings"]),
            "options": {
                "colorMode": "value",
                "graphMode": "area",
                "justifyMode": "auto",
                "orientation": "auto",
                "reduceOptions": {"calcs": ["lastNotNull"], "fields": "",
                                  "values": False},
                "textMode": k["text_mode"] or "auto",
            },
        }

    if panel.kind == "textval":
        mode = "text" if k["string"] else "last"
        q = sql(k["measurement"], None, mode, "value", k["self_only"])
        return {
            "type": "stat", "title": panel.title, "id": _pid(),
            "gridPos": grid, "datasource": DS,
            "targets": [_target(q, fmt=FORMAT_TABLE if k["string"]
                                  else FORMAT_TIMESERIES)],
            "fieldConfig": _field_config(U_NONE, None, None),
            "options": {
                "colorMode": "none",
                "graphMode": "none",
                "justifyMode": "auto",
                "orientation": "auto",
                "reduceOptions": {"calcs": ["lastNotNull"], "fields": "",
                                  "values": False},
                "textMode": "value",
            },
        }

    if panel.kind == "gauge":
        q = sql(k["measurement"], k["conv"], "last", k["field"], k["self_only"])
        return {
            "type": "gauge", "title": panel.title, "id": _pid(),
            "gridPos": grid, "datasource": DS, "targets": [_target(q)],
            "fieldConfig": _field_config(k["unit"], k["decimals"],
                                         k["thresholds"], k["vmin"], k["vmax"]),
            "options": {
                "orientation": "auto",
                "reduceOptions": {"calcs": ["lastNotNull"], "fields": "",
                                  "values": False},
                "showThresholdLabels": False,
                "showThresholdMarkers": True,
            },
        }

    if panel.kind == "timeseries":
        targets, overrides = [], []
        for i, entry in enumerate(k["series"]):
            legend, measurement, conv = entry[0], entry[1], entry[2]
            opts = entry[3] if len(entry) > 3 else {}
            ref = chr(ord("A") + i)
            targets.append(_target(
                sql(measurement, conv, "series",
                    self_only=opts.get("self_only", True),
                    field=opts.get("field", "value"),
                    extra_filters=opts.get("extra_filters", ()),
                    fn=opts.get("fn", "mean"),
                    table=opts.get("table")),
                ref))
            overrides.append({
                "matcher": {"id": "byFrameRefID", "options": ref},
                "properties": [{"id": "displayName", "value": legend}],
            })
        fc = _field_config(k["unit"], k["decimals"], k["thresholds"], custom={
            "axisPlacement": "auto",
            "drawStyle": "line",
            "fillOpacity": k["fill"],
            "lineWidth": 1,
            "pointSize": 4,
            "showPoints": "always" if k["points"] else "never",
            "spanNulls": True,
            "stacking": {"group": "A",
                         "mode": "normal" if k["stack"] else "none"},
        })
        fc["overrides"] = overrides
        return {
            "type": "timeseries", "title": panel.title, "id": _pid(),
            "gridPos": grid, "datasource": DS, "targets": targets,
            "fieldConfig": fc,
            "options": {
                "legend": {"calcs": ["min", "max", "lastNotNull"],
                           "displayMode": "table", "placement": "bottom",
                           "showLegend": True},
                "tooltip": {"mode": "multi", "sort": "none"},
            },
        }

    if panel.kind == "state-timeline":
        targets, overrides = [], []
        for i, (legend, measurement) in enumerate(k["series"]):
            ref = chr(ord("A") + i)
            targets.append(_target(sql(measurement, None, "state"), ref,
                                   fmt=FORMAT_TABLE))
            overrides.append({
                "matcher": {"id": "byFrameRefID", "options": ref},
                "properties": [{"id": "displayName", "value": legend}],
            })
        fc = _field_config(U_NONE, None, None, mappings=k["mappings"], custom={
            "fillOpacity": 70, "lineWidth": 0,
        })
        fc["overrides"] = overrides
        return {
            "type": "state-timeline", "title": panel.title, "id": _pid(),
            "gridPos": grid, "datasource": DS, "targets": targets,
            "fieldConfig": fc,
            "options": {
                "alignValue": "left",
                "legend": {"displayMode": "list", "placement": "bottom",
                           "showLegend": True},
                "mergeValues": True,
                "rowHeight": 0.9,
                "showValue": "auto",
                "tooltip": {"mode": "single", "sort": "none"},
            },
        }

    if panel.kind == "geomap":
        return {
            "type": "geomap", "title": panel.title, "id": _pid(),
            "gridPos": grid, "datasource": DS,
            "targets": [_target(sql_position(), fmt=FORMAT_TABLE)],
            "fieldConfig": _field_config(U_NONE, None, None),
            "options": {
                "basemap": {"name": "Basemap", "type": "default"},
                "controls": {"mouseWheelZoom": True, "showAttribution": True,
                             "showScale": True, "showZoom": True},
                "layers": [{
                    "config": {"showLegend": False,
                               "style": {"size": {"fixed": 4},
                                         "color": {"fixed": "dark-blue"}}},
                    "location": {"latitude": "lat", "longitude": "lon",
                                 "mode": "coords"},
                    "name": "Track",
                    "type": "markers",
                }],
                "view": {"allLayers": True, "id": "fit", "zoom": 10},
            },
        }

    raise ValueError(f"unknown panel kind {panel.kind}")


def build(title, uid, description, panels, refresh="30s",
          time_from="now-24h", tags=("symphony",)):
    rendered, x, y, row_h = [], 0, 0, 0
    for panel in panels:
        if panel.kind == "row":
            if x:
                y += row_h
                x, row_h = 0, 0
            rendered.append(_render(panel, 0, y))
            y += 1
            continue
        if x + panel.w > 24:
            y += row_h
            x, row_h = 0, 0
        rendered.append(_render(panel, x, y))
        x += panel.w
        row_h = max(row_h, panel.h)

    return {
        "annotations": {"list": []},
        "description": description,
        "editable": True,
        "graphTooltip": 1,
        "links": [],
        "panels": rendered,
        "refresh": refresh,
        "schemaVersion": 39,
        "tags": list(tags),
        "templating": {"list": []},
        "time": {"from": time_from, "to": "now"},
        "timepicker": {},
        "timezone": "browser",
        "title": title,
        "uid": uid,
        "version": 1,
        "weekStart": "",
    }


# --------------------------------------------------------------------------
# Shared threshold sets
# --------------------------------------------------------------------------
SOC_STEPS = steps((None, RED), (30, ORANGE), (50, YELLOW), (70, GREEN))
LIFEPO4_V_STEPS = steps((None, RED), (12.8, ORANGE), (13.0, GREEN))
CELL_V_STEPS = steps((None, RED), (3.1, ORANGE), (3.25, GREEN), (3.55, ORANGE))
CPU_TEMP_STEPS = steps((None, GREEN), (65, YELLOW), (75, ORANGE), (82, RED))
UTIL_STEPS = steps((None, GREEN), (70, YELLOW), (85, ORANGE), (95, RED))
FRIDGE_STEPS = steps((None, BLUE), (34, GREEN), (42, ORANGE), (50, RED))

BOOL_MAP = [{
    "options": {
        "0": {"color": GREEN, "index": 0, "text": "OK"},
        "1": {"color": RED, "index": 1, "text": "SET"},
        "false": {"color": GREEN, "index": 2, "text": "no"},
        "true": {"color": RED, "index": 3, "text": "yes"},
    },
    "type": "value",
}]

REACHABLE_MAP = [{
    "options": {
        "false": {"color": RED, "index": 1, "text": "unreachable"},
        "true": {"color": GREEN, "index": 0, "text": "reachable"},
    },
    "type": "value",
}]


# ==========================================================================
# ELECTRICITY
# ==========================================================================
ELECTRICITY = [
    ROW("House bank"),
    GAUGE("State of charge", "electrical.batteries.house.capacity.stateOfCharge",
          CONV_RATIO_TO_PCT, U_PCT, w=4, h=6, decimals=0,
          vmin=0, vmax=100, thresholds=SOC_STEPS),
    STAT("Voltage", "electrical.batteries.house.voltage", None, U_VOLT,
         w=3, h=6, decimals=2, thresholds=LIFEPO4_V_STEPS),
    STAT("Current", "electrical.batteries.house.current", None, U_AMP,
         w=3, h=6, decimals=1),
    STAT("Power", "electrical.batteries.house.power", None, U_WATT,
         w=3, h=6, decimals=0),
    STAT("DC power (Cerbo)", "electrical.venus.dcPower", None, U_WATT,
         w=3, h=6, decimals=0),
    STAT("Time remaining", "electrical.batteries.house.capacity.timeRemaining",
         None, U_SECONDS, w=4, h=6, decimals=0),
    STAT("Consumed", "electrical.batteries.house.capacity.consumedCharge",
         CONV_COULOMB_TO_AH, U_AH, w=4, h=6, decimals=1),

    TS("House bank voltage", [("Voltage", "electrical.batteries.house.voltage", None)],
       U_VOLT, w=12, h=8, decimals=2),
    TS("House bank current and power", [
        ("Current (A)", "electrical.batteries.house.current", None),
        ("Power (W)", "electrical.batteries.house.power", None),
        ("Cerbo DC power (W)", "electrical.venus.dcPower", None),
    ], U_NONE, w=12, h=8, decimals=1),
    TS("State of charge", [
        ("SOC", "electrical.batteries.house.capacity.stateOfCharge", CONV_RATIO_TO_PCT),
    ], U_PCT, w=12, h=8, decimals=0),
    TS("Discharge since full", [
        ("Discharge since full (Ah)",
         "electrical.batteries.house.capacity.dischargeSinceFull", CONV_COULOMB_TO_AH),
        ("Discharged energy (Wh)",
         "electrical.batteries.house.capacity.dischargedEnergy", CONV_JOULE_TO_WH),
    ], U_NONE, w=12, h=8, decimals=1),

    # 5C90 first, and 0146 second, because they are not peers: log entry
    # b6c7dfc identified 5C90 as the pack actually wired into the system (it
    # tracks the Victron shunt to within 10 mV) and 0146 as a spare sitting
    # disconnected with its terminals plugged. Both advertise the same BLE
    # name, so only the MAC distinguishes them. Rendering them as a matched
    # pair invites reading the spare's numbers as half the house bank.
    pack_row("5C90"),
    STAT(pack_label("5C90", "SOC"), "electrical.batteries.5C90.capacity.stateOfCharge",
         CONV_RATIO_TO_PCT, U_PCT, w=3, h=5, decimals=0, thresholds=SOC_STEPS),
    STAT(pack_label("5C90", "voltage"), "electrical.batteries.5C90.voltage", None, U_VOLT,
         w=3, h=5, decimals=2, thresholds=LIFEPO4_V_STEPS),
    STAT(pack_label("5C90", "current"), "electrical.batteries.5C90.current", None, U_AMP,
         w=3, h=5, decimals=1),
    STAT(pack_label("5C90", "temp"), "electrical.batteries.5C90.temperature",
         CONV_K_TO_F, U_F, w=3, h=5, decimals=1),
    STAT(pack_label("5C90", "cycles"), "electrical.batteries.5C90.cycles", None, U_SHORT,
         w=3, h=5, decimals=0),
    STAT(pack_label("5C90", "capacity"), "electrical.batteries.5C90.capacity.remaining",
         CONV_COULOMB_TO_AH, U_AH, w=3, h=5, decimals=1),
    TS(pack_label("5C90", "cell voltages"), [
        ("Cell 0", "electrical.batteries.5C90.cell0.voltage", None),
        ("Cell 1", "electrical.batteries.5C90.cell1.voltage", None),
        ("Cell 2", "electrical.batteries.5C90.cell2.voltage", None),
        ("Cell 3", "electrical.batteries.5C90.cell3.voltage", None),
    ], U_VOLT, w=12, h=8, decimals=3, fill=0, thresholds=CELL_V_STEPS),
    STATE(pack_label("5C90", "protection and FETs"), [
        ("Protection", "electrical.batteries.5C90.protectionStatus"),
        ("FETs", "electrical.batteries.5C90.FETStatus"),
    ], w=12, h=6),

    pack_row("0146"),
    STAT(pack_label("0146", "SOC"), "electrical.batteries.0146.capacity.stateOfCharge",
         CONV_RATIO_TO_PCT, U_PCT, w=3, h=5, decimals=0, thresholds=SOC_STEPS),
    STAT(pack_label("0146", "voltage"), "electrical.batteries.0146.voltage", None, U_VOLT,
         w=3, h=5, decimals=2, thresholds=LIFEPO4_V_STEPS),
    STAT(pack_label("0146", "current"), "electrical.batteries.0146.current", None, U_AMP,
         w=3, h=5, decimals=1),
    STAT(pack_label("0146", "temp"), "electrical.batteries.0146.temperature",
         CONV_K_TO_F, U_F, w=3, h=5, decimals=1),
    STAT(pack_label("0146", "cycles"), "electrical.batteries.0146.cycles", None, U_SHORT,
         w=3, h=5, decimals=0),
    STAT(pack_label("0146", "capacity"), "electrical.batteries.0146.capacity.remaining",
         CONV_COULOMB_TO_AH, U_AH, w=3, h=5, decimals=1),
    TS(pack_label("0146", "cell voltages"), [
        ("Cell 0", "electrical.batteries.0146.cell0.voltage", None),
        ("Cell 1", "electrical.batteries.0146.cell1.voltage", None),
        ("Cell 2", "electrical.batteries.0146.cell2.voltage", None),
        ("Cell 3", "electrical.batteries.0146.cell3.voltage", None),
    ], U_VOLT, w=12, h=8, decimals=3, fill=0, thresholds=CELL_V_STEPS),
    STATE(pack_label("0146", "protection and FETs"), [
        ("Protection", "electrical.batteries.0146.protectionStatus"),
        ("FETs", "electrical.batteries.0146.FETStatus"),
    ], w=12, h=6),

    ROW("Cerbo GX and shore charging"),
    STATE("System state", [
        ("Cerbo state", "electrical.venus.state"),
        ("IP22 charger", "electrical.chargers.VictronACCharger.state"),
    ], w=24, h=6),
    STATE("Cerbo digital inputs", [
        ("Input 1", "electrical.venus-input.1.state"),
        ("Input 2", "electrical.venus-input.2.state"),
        ("Input 4", "electrical.venus-input.4.state"),
    ], w=12, h=6),
    STATE("Cerbo relays", [
        ("Relay 1", "electrical.switches.venus-0.state"),
        ("Relay 2", "electrical.switches.venus-1.state"),
    ], w=12, h=6),
]


# ==========================================================================
# NAVIGATION
# ==========================================================================
NAVIGATION = [
    ROW("Under way"),
    GAUGE("SOG", "navigation.speedOverGround", CONV_MS_TO_KN, U_KNOT,
          w=4, h=6, decimals=1, vmin=0, vmax=10,
          thresholds=steps((None, BLUE), (4, GREEN), (7, ORANGE))),
    GAUGE("COG (true)", "navigation.courseOverGroundTrue", CONV_RAD_TO_DEG,
          U_DEG, w=4, h=6, decimals=0, vmin=0, vmax=360),
    GAUGE("Heading (true)", "navigation.headingTrue", CONV_RAD_TO_DEG,
          U_DEG, w=4, h=6, decimals=0, vmin=0, vmax=360),
    GAUGE("Heading (magnetic)", "navigation.headingMagnetic", CONV_RAD_TO_DEG,
          U_DEG, w=4, h=6, decimals=0, vmin=0, vmax=360),
    GAUGE("Heel", "navigation.attitude.roll", CONV_RAD_TO_DEG, U_DEG,
          w=4, h=6, decimals=1, vmin=-45, vmax=45,
          thresholds=steps((None, GREEN), (20, YELLOW), (30, RED))),
    STAT("Magnetic variation", "navigation.magneticVariation", CONV_RAD_TO_DEG,
         U_DEG, w=4, h=6, decimals=1),
    STAT("Trip log", "navigation.trip.log", CONV_M_TO_NM, U_NM,
         w=4, h=6, decimals=1),

    TS("Speed over ground", [("SOG", "navigation.speedOverGround", CONV_MS_TO_KN)],
       U_KNOT, w=12, h=8, decimals=1),
    TS("Attitude", [
        ("Roll", "navigation.attitude.roll", CONV_RAD_TO_DEG),
        ("Pitch", "navigation.attitude.pitch", CONV_RAD_TO_DEG),
    ], U_DEG, w=12, h=8, decimals=1, fill=0),

    ROW("Track"),
    GEOMAP("Position", w=12, h=10),
    TS("Course over ground", [
        ("COG true", "navigation.courseOverGroundTrue", CONV_RAD_TO_DEG),
        ("Heading true", "navigation.headingTrue", CONV_RAD_TO_DEG),
        ("Heading magnetic", "navigation.headingMagnetic", CONV_RAD_TO_DEG),
    ], U_DEG, w=12, h=10, decimals=0, fill=0),

    ROW("Vessel and autopilot state"),
    STATE("State", [
        ("Vessel", "navigation.state"),
        ("Autopilot", "steering.autopilot.state"),
        ("Autopilot engaged", "steering.autopilot.engaged"),
    ], w=24, h=7),

    ROW("GNSS quality"),
    STAT("Satellites", "navigation.gnss.satellites", None, U_SHORT,
         w=4, h=5, decimals=0,
         thresholds=steps((None, RED), (5, ORANGE), (8, GREEN))),
    STAT("Satellites in view", "navigation.gnss.satellitesInView", None,
         U_SHORT, w=4, h=5, decimals=0),
    STAT("HDOP", "navigation.gnss.horizontalDilution", None, U_SHORT,
         w=4, h=5, decimals=2,
         thresholds=steps((None, GREEN), (2, YELLOW), (5, RED))),
    STAT("Antenna altitude", "navigation.gnss.antennaAltitude", CONV_M_TO_FT,
         U_FT, w=4, h=5, decimals=0),
    TEXTVAL("Fix quality", "navigation.gnss.methodQuality", w=4, h=5),
    TEXTVAL("Fix type", "navigation.gnss.type", w=4, h=5),
    TS("Satellites tracked", [
        ("Satellites", "navigation.gnss.satellites", None),
        ("In view", "navigation.gnss.satellitesInView", None),
    ], U_SHORT, w=12, h=7, decimals=0, fill=0),
    TS("Horizontal dilution of precision", [
        ("HDOP", "navigation.gnss.horizontalDilution", None),
        ("PDOP", "navigation.gnss.positionDilution", None),
    ], U_SHORT, w=12, h=7, decimals=2, fill=0),
]


# ==========================================================================
# WEATHER
# ==========================================================================
WEATHER = [
    ROW("Conditions"),
    GAUGE("Outside temperature", "environment.outside.temperature", CONV_K_TO_F,
          U_F, w=4, h=6, decimals=1, vmin=20, vmax=100),
    GAUGE("Feels like", "environment.outside.feelsLikeTemperature", CONV_K_TO_F,
          U_F, w=4, h=6, decimals=1, vmin=20, vmax=100),
    GAUGE("Relative humidity", "environment.outside.relativeHumidity",
          CONV_RATIO_TO_PCT, U_PCT, w=4, h=6, decimals=0, vmin=0, vmax=100),
    GAUGE("Wind speed", "environment.wind.speedTrue", CONV_MS_TO_KN, U_KNOT,
          w=4, h=6, decimals=1, vmin=0, vmax=40,
          thresholds=steps((None, GREEN), (15, YELLOW), (22, ORANGE), (30, RED))),
    GAUGE("Wind direction", "environment.wind.directionTrue", CONV_RAD_TO_DEG,
          U_DEG, w=4, h=6, decimals=0, vmin=0, vmax=360),
    STAT("Barometer", "environment.outside.pressure", CONV_PA_TO_HPA, U_HPA,
         w=4, h=6, decimals=1),

    ROW("Barometer"),
    STAT("1 h change", "environment.outside.pressure.oneHourDelta",
         CONV_PA_TO_HPA, U_HPA, w=3, h=5, decimals=2,
         thresholds=steps((None, RED), (-1.6, ORANGE), (-0.5, TEXT), (0.5, GREEN))),
    STAT("3 h change", "environment.outside.pressure.threeHoursDelta",
         CONV_PA_TO_HPA, U_HPA, w=3, h=5, decimals=2,
         thresholds=steps((None, RED), (-3.5, ORANGE), (-1.0, TEXT), (1.0, GREEN))),
    TEXTVAL("Tendency", "environment.outside.pressure.trend.tendency", w=3, h=5),
    TEXTVAL("Severity", "environment.outside.pressure.trend.severity", w=3, h=5,
            string=False),
    TEXTVAL("System", "environment.outside.pressure.system", w=3, h=5),
    TEXTVAL("Predicted front", "environment.outside.pressure.prediction.front.prognose",
            w=4, h=5),
    TEXTVAL("Predicted wind", "environment.outside.pressure.prediction.front.wind",
            w=5, h=5),
    TS("Barometric pressure", [
        ("Now", "environment.outside.pressure", CONV_PA_TO_HPA),
        ("1 h ago", "environment.outside.pressure.oneHourAgo", CONV_PA_TO_HPA),
        ("3 h ago", "environment.outside.pressure.threeHoursAgo", CONV_PA_TO_HPA),
        ("12 h ago", "environment.outside.pressure.twelveHoursAgo", CONV_PA_TO_HPA),
    ], U_HPA, w=24, h=9, decimals=1, fill=0),

    ROW("Wind"),
    TS("Wind speed", [
        ("True wind", "environment.wind.speedTrue", CONV_MS_TO_KN),
        ("Reported speed", "environment.outside.wind.speed", CONV_MS_TO_KN),
        ("Reported gust", "environment.outside.wind.gust", CONV_MS_TO_KN),
    ], U_KNOT, w=12, h=8, decimals=1, fill=0),
    TS("Wind direction", [
        ("True wind", "environment.wind.directionTrue", CONV_RAD_TO_DEG),
        ("Reported", "environment.outside.wind.direction", CONV_RAD_TO_DEG),
    ], U_DEG, w=12, h=8, decimals=0, fill=0, points=True),

    ROW("Temperature and humidity"),
    TS("Outside temperature", [
        ("Outside", "environment.outside.temperature", CONV_K_TO_F),
        ("Feels like", "environment.outside.feelsLikeTemperature", CONV_K_TO_F),
        ("Dew point", "environment.outside.dewPointTemperature", CONV_K_TO_F),
    ], U_F, w=12, h=8, decimals=1, fill=0),
    TS("Humidity and cloud cover", [
        ("Relative humidity", "environment.outside.relativeHumidity", CONV_RATIO_TO_PCT),
        ("Cloud cover", "environment.outside.cloudCover", CONV_RATIO_TO_PCT),
    ], U_PCT, w=12, h=8, decimals=0, fill=0),

    # No forecast-text panels here. The day-named `environment.forecast.*`
    # tree (today.detailedForecast, tonight.shortForecast, and the rest) came
    # from signalk-noaa-weather, which is disabled -- those paths are frozen at
    # whatever they last held, and a stat panel would show stale prose with no
    # indication it had stopped updating. The numeric `environment.forecast.*`
    # paths from the open-meteo provider share the same prefix; until the two
    # are told apart by source tag, nothing under that prefix is safe to plot.
    ROW("Tide and sky"),
    STAT("Tide now", "environment.tide.heightNow", CONV_M_TO_FT, U_FT,
         w=3, h=5, decimals=1),
    STAT("Next high", "environment.tide.heightHigh", CONV_M_TO_FT, U_FT,
         w=3, h=5, decimals=1),
    STAT("Next low", "environment.tide.heightLow", CONV_M_TO_FT, U_FT,
         w=3, h=5, decimals=1),
    TEXTVAL("Tide state", "environment.tide.state", w=3, h=5),
    TEXTVAL("Sunrise", "environment.sunlight.times.sunrise", w=3, h=5),
    TEXTVAL("Sunset", "environment.sunlight.times.sunset", w=3, h=5),
    TEXTVAL("Moon phase", "environment.moon.phaseName", w=3, h=5),
    STAT("Moon illumination", "environment.moon.fraction", CONV_RATIO_TO_PCT,
         U_PCT, w=3, h=5, decimals=0),

    ROW("Space weather"),
    STAT("Kp observed", "environment.noaa.swpc.kp.observed", None, U_SHORT,
         w=4, h=5, decimals=1,
         thresholds=steps((None, GREEN), (5, YELLOW), (7, ORANGE), (8, RED))),
    STAT("Kp max 24 h", "environment.noaa.swpc.kp.forecast.max24h", None,
         U_SHORT, w=4, h=5, decimals=1,
         thresholds=steps((None, GREEN), (5, YELLOW), (7, ORANGE), (8, RED))),
    STAT("Solar wind speed", "environment.noaa.swpc.solar_wind.speed", None,
         U_SHORT, w=4, h=5, decimals=0),
    STAT("Bz", "environment.noaa.swpc.solar_wind.Bz", None, U_SHORT,
         w=4, h=5, decimals=1),
    TEXTVAL("X-ray flare class", "environment.noaa.swpc.xray_flare.class",
            w=4, h=5),
    STAT("F10.7", "environment.noaa.swpc.f107", None, U_SHORT, w=4, h=5,
         decimals=0),
]


# ==========================================================================
# LIFE SUPPORT
# ==========================================================================
LIFE_SUPPORT = [
    ROW("Refrigeration"),
    GAUGE("Fridge", "environment.inside.refrigerator.temperature", CONV_K_TO_F,
          U_F, w=5, h=6, decimals=1, vmin=25, vmax=60, thresholds=FRIDGE_STEPS),
    STAT("Fridge humidity", "environment.inside.refrigerator.humidity",
         CONV_RATIO_TO_PCT, U_PCT, w=4, h=6, decimals=0),
    STAT("Cabin humidity", "environment.inside.relativeHumidity",
         CONV_RATIO_TO_PCT, U_PCT, w=4, h=6, decimals=0),
    GAUGE("House SOC", "electrical.batteries.house.capacity.stateOfCharge",
          CONV_RATIO_TO_PCT, U_PCT, w=5, h=6, decimals=0, vmin=0, vmax=100,
          thresholds=SOC_STEPS),
    STAT("Battery time remaining",
         "electrical.batteries.house.capacity.timeRemaining", None, U_SECONDS,
         w=6, h=6, decimals=0),

    TS("Fridge temperature", [
        ("Fridge", "environment.inside.refrigerator.temperature", CONV_K_TO_F),
        ("Outside", "environment.outside.temperature", CONV_K_TO_F),
    ], U_F, w=12, h=8, decimals=1, fill=0),
    TS("Humidity", [
        ("Fridge", "environment.inside.refrigerator.humidity", CONV_RATIO_TO_PCT),
        ("Cabin", "environment.inside.relativeHumidity", CONV_RATIO_TO_PCT),
        ("Outside", "environment.outside.relativeHumidity", CONV_RATIO_TO_PCT),
    ], U_PCT, w=12, h=8, decimals=0, fill=0),

    ROW("Bluetooth sensor health"),
    STAT("Fridge sensor battery", "sensors.refrigerator.switchbot.battery",
         None, U_PCT, w=4, h=5, decimals=0,
         thresholds=steps((None, RED), (20, ORANGE), (40, GREEN))),
    STAT("Fridge sensor RSSI", "sensors.refrigerator.switchbot.signalStrength",
         None, U_SHORT, w=4, h=5, decimals=0,
         thresholds=steps((None, RED), (-90, ORANGE), (-75, GREEN))),
    STAT("House battery 1 RSSI", "sensors.houseBattery1.signalStrength", None,
         U_SHORT, w=4, h=5, decimals=0,
         thresholds=steps((None, RED), (-90, ORANGE), (-75, GREEN))),
    STAT("House battery 2 RSSI", "sensors.houseBattery2.signalStrength", None,
         U_SHORT, w=4, h=5, decimals=0,
         thresholds=steps((None, RED), (-90, ORANGE), (-75, GREEN))),
    STAT("IP22 charger RSSI",
         "electrical.chargers.VictronACCharger.signalStrength", None, U_SHORT,
         w=4, h=5, decimals=0,
         thresholds=steps((None, RED), (-90, ORANGE), (-75, GREEN))),

    STATE("Sensor reachability", [
        ("House battery 1", "sensors.House_Battery_1_A5_C2_37_40_01_46.reachable"),
        ("House battery 2", "sensors.House_Battery_2_A5_C2_37_3C_5C_90.reachable"),
        ("Fridge", "sensors.SwitchBotTH_Fridge_Thermometer_CE_B5_52_72_1C_81.reachable"),
        ("IP22 charger",
         "sensors.Victron_Blue_Smart_IP22_Charger_12_30_3_D2_2A_6F_EF_DB_36.reachable"),
    ], w=24, h=7, mappings=REACHABLE_MAP),

    TS("Bluetooth signal strength", [
        ("Fridge", "sensors.refrigerator.switchbot.signalStrength", None),
        ("House battery 1", "sensors.houseBattery1.signalStrength", None),
        ("House battery 2", "sensors.houseBattery2.signalStrength", None),
        ("IP22 charger", "electrical.chargers.VictronACCharger.signalStrength", None),
    ], U_SHORT, w=24, h=8, decimals=0, fill=0),
]


# ==========================================================================
# NAVSTATION -- the at-a-glance screen
# ==========================================================================
NAVSTATION = [
    STAT("SOG", "navigation.speedOverGround", CONV_MS_TO_KN, U_KNOT,
         w=4, h=5, decimals=1),
    STAT("COG", "navigation.courseOverGroundTrue", CONV_RAD_TO_DEG, U_DEG,
         w=4, h=5, decimals=0),
    STAT("Heading (M)", "navigation.headingMagnetic", CONV_RAD_TO_DEG, U_DEG,
         w=4, h=5, decimals=0),
    STAT("Heel", "navigation.attitude.roll", CONV_RAD_TO_DEG, U_DEG,
         w=4, h=5, decimals=1),
    STAT("Trip log", "navigation.trip.log", CONV_M_TO_NM, U_NM,
         w=4, h=5, decimals=1),
    TEXTVAL("Vessel state", "navigation.state", w=4, h=5),

    STAT("House SOC", "electrical.batteries.house.capacity.stateOfCharge",
         CONV_RATIO_TO_PCT, U_PCT, w=4, h=5, decimals=0, thresholds=SOC_STEPS),
    STAT("House volts", "electrical.batteries.house.voltage", None, U_VOLT,
         w=4, h=5, decimals=2, thresholds=LIFEPO4_V_STEPS),
    STAT("DC power", "electrical.venus.dcPower", None, U_WATT,
         w=4, h=5, decimals=0),
    STAT("Time remaining",
         "electrical.batteries.house.capacity.timeRemaining", None, U_SECONDS,
         w=4, h=5, decimals=0),
    STAT("Barometer", "environment.outside.pressure", CONV_PA_TO_HPA, U_HPA,
         w=4, h=5, decimals=1),
    TEXTVAL("Tendency", "environment.outside.pressure.trend.tendency", w=4, h=5),

    STAT("Wind speed", "environment.wind.speedTrue", CONV_MS_TO_KN, U_KNOT,
         w=4, h=5, decimals=1),
    STAT("Wind direction", "environment.wind.directionTrue", CONV_RAD_TO_DEG,
         U_DEG, w=4, h=5, decimals=0),
    STAT("Outside", "environment.outside.temperature", CONV_K_TO_F, U_F,
         w=4, h=5, decimals=1),
    STAT("Feels like", "environment.outside.feelsLikeTemperature", CONV_K_TO_F,
         U_F, w=4, h=5, decimals=1),
    STAT("Fridge", "environment.inside.refrigerator.temperature", CONV_K_TO_F,
         U_F, w=4, h=5, decimals=1, thresholds=FRIDGE_STEPS),
    STAT("Tide now", "environment.tide.heightNow", CONV_M_TO_FT, U_FT,
         w=4, h=5, decimals=1),

    TS("Speed over ground", [("SOG", "navigation.speedOverGround", CONV_MS_TO_KN)],
       U_KNOT, w=8, h=8, decimals=1),
    TS("House bank", [
        ("SOC (%)", "electrical.batteries.house.capacity.stateOfCharge",
         CONV_RATIO_TO_PCT),
        ("Current (A)", "electrical.batteries.house.current", None),
    ], U_NONE, w=8, h=8, decimals=1),
    TS("Barometer", [("Pressure", "environment.outside.pressure", CONV_PA_TO_HPA)],
       U_HPA, w=8, h=8, decimals=1),
]


# ==========================================================================
# SYSTEM HEALTH
#
# Not modelled on the reference dashboards -- they have no equivalent. It
# exists because this boat's failure modes so far have been machine-level
# (memory pressure, SD write volume, a GPU hang, an unsynced clock, bus
# brownout), and none of those are visible on a vessel-data dashboard.
#
# Telegraf's metrics are not written by SignalK, hence self_only=False
# throughout this section: the measurement names here are Telegraf table
# names, not SignalK paths. InfluxDB's own scraped metrics (series
# cardinality and friends) have no counterpart in QuestDB -- nothing
# collects them -- so no panel here reads them.
# ==========================================================================
NOSELF = {"self_only": False}


def _tg(field, **kw):
    opts = dict(NOSELF)
    opts["field"] = field
    opts.update(kw)
    return opts


SYSTEM = [
    ROW("SoC"),
    GAUGE("CPU temperature", "environment.rpi.cpu.temperature", CONV_K_TO_F,
          U_F, w=4, h=6, decimals=1, vmin=80, vmax=200),
    GAUGE("Memory used", "environment.rpi.memory.utilisation",
          CONV_RATIO_TO_PCT, U_PCT, w=4, h=6, decimals=0, vmin=0, vmax=100,
          thresholds=UTIL_STEPS),
    GAUGE("SD card used", "environment.rpi.sd.utilisation", CONV_RATIO_TO_PCT,
          U_PCT, w=4, h=6, decimals=0, vmin=0, vmax=100, thresholds=UTIL_STEPS),
    STAT("GPU temperature", "environment.rpi.gpu.temperature", CONV_K_TO_F,
         U_F, w=4, h=6, decimals=1),
    STAT("Uptime", "environment.rpi.uptime", None, U_SECONDS, w=4, h=6,
         decimals=0),
    STAT("Load (1 m)", "system", None, U_SHORT, w=4, h=6, decimals=2,
         self_only=False, field="load1"),

    ROW("Power and thermal throttling"),
    STAT("Under-voltage now", "rpi_health", None, U_SHORT, w=3, h=4,
         decimals=0, self_only=False, field="under_voltage_now",
         mappings=BOOL_MAP, text_mode="value"),
    STAT("Throttled now", "rpi_health", None, U_SHORT, w=3, h=4, decimals=0,
         self_only=False, field="throttled_now", mappings=BOOL_MAP,
         text_mode="value"),
    STAT("Freq capped now", "rpi_health", None, U_SHORT, w=3, h=4, decimals=0,
         self_only=False, field="freq_capped_now", mappings=BOOL_MAP,
         text_mode="value"),
    STAT("Soft temp limit now", "rpi_health", None, U_SHORT, w=3, h=4,
         decimals=0, self_only=False, field="soft_temp_limit_now",
         mappings=BOOL_MAP, text_mode="value"),
    STAT("Under-voltage since boot", "rpi_health", None, U_SHORT, w=3, h=4,
         decimals=0, self_only=False, field="under_voltage_since_boot",
         mappings=BOOL_MAP, text_mode="value"),
    STAT("Throttled since boot", "rpi_health", None, U_SHORT, w=3, h=4,
         decimals=0, self_only=False, field="throttled_since_boot",
         mappings=BOOL_MAP, text_mode="value"),
    STAT("Freq capped since boot", "rpi_health", None, U_SHORT, w=3, h=4,
         decimals=0, self_only=False, field="freq_capped_since_boot",
         mappings=BOOL_MAP, text_mode="value"),
    STAT("Soft temp limit since boot", "rpi_health", None, U_SHORT, w=3, h=4,
         decimals=0, self_only=False, field="soft_temp_limit_since_boot",
         mappings=BOOL_MAP, text_mode="value"),

    ROW("Memory and swap"),
    TS("Memory", [
        ("Used %", "mem", None, _tg("used_percent")),
        ("Available (bytes)", "mem", None, _tg("available")),
    ], U_NONE, w=12, h=8, decimals=1, fill=0),
    TS("Swap used", [("Swap %", "swap", None, _tg("used_percent"))],
       U_PCT, w=12, h=8, decimals=1),

    ROW("CPU and load"),
    TS("CPU usage", [
        ("Active %", "cpu", None, _tg("usage_active")),
        ("IO wait %", "cpu", None, _tg("usage_iowait")),
        ("System %", "cpu", None, _tg("usage_system")),
    ], U_PCT, w=12, h=8, decimals=1, fill=0),
    TS("Load average and blocked processes", [
        ("Load 1 m", "system", None, _tg("load1")),
        ("Load 5 m", "system", None, _tg("load5")),
        ("Load 15 m", "system", None, _tg("load15")),
        ("Blocked", "processes", None, _tg("blocked")),
    ], U_SHORT, w=12, h=8, decimals=2, fill=0),

    ROW("Storage"),
    # Telegraf writes one row per mount point into `disk` and one per block
    # device into `diskio`, so an unfiltered avg()/max() blends them. Pin
    # `disk` to the root filesystem; `diskio`'s max() picks the whole-device
    # counter, which is >= any of its partitions, so it needs no filter.
    TS("Disk used", [("Root %", "disk", None,
                      _tg("used_percent", extra_filters=(("path", "/"),)))],
       U_PCT, w=8, h=8, decimals=1),
    TS("Disk write volume", [
        ("Write bytes", "diskio", None, _tg("write_bytes", fn="max")),
        ("Read bytes", "diskio", None, _tg("read_bytes", fn="max")),
    ], U_BYTES, w=8, h=8, decimals=0, fill=0),
    ROW("Clock and recording"),
    TS("chrony offset", [
        ("Last offset (s)", "chrony", None, _tg("last_offset")),
    ], U_SECONDS, w=8, h=8, decimals=6, fill=0),
    TS("Telegraf write health", [
        ("Metrics dropped", "internal_write", None, _tg("metrics_dropped")),
        ("Write errors", "internal_write", None, _tg("write_errors")),
        ("Buffer size", "internal_write", None, _tg("buffer_size")),
    ], U_SHORT, w=8, h=8, decimals=0, fill=0),
    # Pinned to eth0 -- telegraf.conf also collects wlan0 and can0, and an
    # unfiltered max() would silently switch to whichever interface is busiest.
    TS("Network throughput (eth0)", [
        ("Bytes received", "net", None,
         _tg("bytes_recv", fn="max", extra_filters=(("interface", "eth0"),))),
        ("Bytes sent", "net", None,
         _tg("bytes_sent", fn="max", extra_filters=(("interface", "eth0"),))),
    ], U_BYTES, w=8, h=8, decimals=0, fill=0),

    ROW("Per-service memory"),
    TS("Resident memory by service", [
        ("signalk", "procstat", None,
         dict(NOSELF, field="memory_rss",
              extra_filters=(("systemd_unit", "signalk.service"),))),
        ("influxdb", "procstat", None,
         dict(NOSELF, field="memory_rss",
              extra_filters=(("systemd_unit", "influxdb.service"),))),
        ("grafana", "procstat", None,
         dict(NOSELF, field="memory_rss",
              extra_filters=(("systemd_unit", "grafana-server.service"),))),
        ("caddy", "procstat", None,
         dict(NOSELF, field="memory_rss",
              extra_filters=(("systemd_unit", "caddy.service"),))),
        ("dex", "procstat", None,
         dict(NOSELF, field="memory_rss",
              extra_filters=(("systemd_unit", "dex.service"),))),
    ], U_BYTES, w=24, h=9, decimals=0, fill=0),
]


DASHBOARDS = [
    ("Navstation", "symphony-navstation", "navstation.json",
     "At-a-glance vessel state: nav, house bank, weather, tide.",
     NAVSTATION, "10s", "now-6h"),
    ("Navigation", "symphony-navigation", "navigation.json",
     "Speed, course, attitude, track and GNSS quality.",
     NAVIGATION, "10s", "now-24h"),
    ("Electricity", "symphony-electricity", "electricity.json",
     "House bank, the two JBD packs, and Cerbo GX state.",
     ELECTRICITY, "30s", "now-24h"),
    ("Weather", "symphony-weather", "weather.json",
     "Conditions, barometer trend, forecast, tide and space weather. "
     "All of it externally sourced -- this boat has no masthead unit.",
     WEATHER, "1m", "now-48h"),
    ("Life support", "symphony-life-support", "life-support.json",
     "Refrigeration, cabin humidity, and Bluetooth sensor health.",
     LIFE_SUPPORT, "1m", "now-48h"),
    ("System health", "symphony-system", "system.json",
     "The boat computer itself: memory, SD wear, throttling, clock, "
     "and whether we are still recording.",
     SYSTEM, "1m", "now-24h"),
]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    written = []
    for title, uid, filename, description, panels, refresh, time_from in DASHBOARDS:
        _next_id[0] = 1
        dash = build(title, uid, description, panels, refresh, time_from)
        path = os.path.join(OUT_DIR, filename)
        with open(path, "w") as f:
            json.dump(dash, f, indent=2, sort_keys=True)
            f.write("\n")
        written.append((filename, len(dash["panels"])))

    for filename, count in written:
        print(f"wrote {filename} ({count} panels)")


if __name__ == "__main__":
    main()
