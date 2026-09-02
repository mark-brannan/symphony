# SignalK paths, and what reaches the dashboards

How vessel data gets from SignalK into InfluxDB, which paths this boat
actually publishes, and where the naming is inconsistent enough to be worth
a decision. Operating procedure for the Grafana stack lives in `RUNBOOK.md`;
this file is the why.

## The write schema

`signalk-to-influxdb2` writes one InfluxDB measurement per SignalK path,
using the path as the measurement name verbatim:

| InfluxDB | Value |
| --- | --- |
| `_measurement` | the SignalK path, unmodified (`electrical.batteries.house.voltage`) |
| `_field` | `value` — except positions, which write `lat` and `lon` |
| tags | `context`, `source`, `self="true"`, plus `s2_cell_id` on positions |

`navigation.attitude` is the one path the plugin decomposes: it arrives as an
object and is written as three separate measurements, `navigation.attitude.pitch`,
`.roll` and `.yaw`.

Values are stored in SignalK's canonical SI units and nothing converts them on
the way in — speeds in m/s, angles in radians, temperatures in Kelvin,
pressures in Pascals, ratios as 0..1, charge in Coulombs, energy in Joules.
Every dashboard panel that shows knots, degrees, Fahrenheit or percent
converts on the way out. This is the single easiest thing to get wrong and
the hardest to notice: a speed gauge that forgets the m/s→knot factor reads
3.6 instead of 7 and looks like a slow day rather than a bug.

The `self="true"` tag is stamped only on data SignalK considers this vessel's
own. Telegraf's host metrics and InfluxDB's self-scraped internals carry no
such tag, so a query that filters on it returns nothing for them.

## What this boat publishes

Confirmed against the boat's InfluxDB. Present and carrying data:

- **Navigation** — `position`, `speedOverGround`, `courseOverGroundTrue`,
  `courseOverGroundMagnetic`, `headingMagnetic`, `headingTrue`,
  `magneticVariation`, `attitude.{pitch,roll,yaw}`,
  `trip.log`, `state`, `datetime`, `gnss.*`, `courseRhumbline.*`
- **Steering** — `steering.autopilot.{state,engaged,defaultPilot,availableActions}`
- **Electrical** — `batteries.house.*` (voltage, current, power, SOC, time
  remaining, consumed charge, discharge since full), `batteries.0146.*` and
  `batteries.5C90.*` (the two JBD packs, including per-cell voltages),
  `venus.{dcPower,state}`, `venus-input.{1,2,4}.*`, `switches.*`,
  `chargers.VictronACCharger.{state,signalStrength}`
- **Environment** — `outside.*` (temperature, humidity, pressure and its full
  trend/prediction tree, feels-like, dew point, cloud cover),
  `inside.refrigerator.{temperature,humidity}`, `inside.relativeHumidity`,
  `wind.{speedTrue,directionTrue}`, `tide.*`, `sunlight.times.*`, `moon.*`,
  `forecast.*`, `noaa.swpc.*`, `rpi.*`
- **Sensors** — Bluetooth reachability and RSSI for the two JBD packs, the
  SwitchBot fridge thermometer and the Victron IP22 charger

Absent entirely — no path under these prefixes has ever been written:

| Missing | Consequence |
| --- | --- |
| `environment.depth.*` | no depth panel is possible |
| `environment.wind.speedApparent` / `angleApparent` | no apparent wind; there is no masthead unit |
| `tanks.*` | no fuel, fresh water or holding level |
| `propulsion.*` | no engine hours and no engine state |
| `electrical.solar.*`, `electrical.venus.totalPanelPower` | no solar or MPPT yield |
| `electrical.inverters.*`, `electrical.chargers.alternator.power` | no inverter or alternator output |
| `navigation.speedThroughWater` | no log impeller |
| `navigation.anchor.*`, `performance.polarSpeed`, `networking.*` | no anchor alarm, polars or uplink telemetry |

One of these is configured for but not delivered. `signalk-alternator-engine-on`
reads `electrical.chargers.alternator.power` and writes `propulsion.main.state`;
neither path exists, so the plugin is inert.

`signalk-derived-data`'s `heading.heading`, `heading.cog_true` and
`heading.magneticVariation` calculators were enabled 2026-08-19.
`navigation.headingTrue` is now live, derived from `headingMagnetic` and
`magneticVariation` (verified against live values on the boat: the two sum
to the reported `headingTrue` to within rounding). `cog_true` has nothing to
derive from — the boat has no `navigation.courseOverGroundMagnetic` source,
only a native true COG from the GPS/N2K bus, which is what
`navigation.courseOverGroundTrue` was already carrying before this change —
so that calculator stays inert with no source to conflict with.

`"course data".cog_magnetic` was also enabled 2026-08-19, the mirror image:
`navigation.courseOverGroundMagnetic` is now live too, derived from the
native `courseOverGroundTrue` and `magneticVariation` (verified: the two
combine to the reported value, normalized into `[0, 2π)`).

## Where the naming is inconsistent

These are observations, not corrections — nothing here has been renamed. Each
is a live path carrying real data today.

**`environment.outside.pressure` is both a value and a container.** It holds a
reading, and it also has children: `.1hr`, `.3hr`, `.oneHourAgo`,
`.oneHourDelta`, `.trend.*`, `.prediction.*`, `.system`. The same shape
appears on `environment.outside.temperature` (which has a `.dewpoint` child)
and `environment.outside.weather`. The SignalK schema treats a path as either
a value or a branch; InfluxDB doesn't care, because each becomes its own
measurement, so this works in practice while being unrepresentable in the
SignalK tree.

**Two barometer stacks run in parallel.** `environment.barometer.*` (trend,
prediction, front, wind) and `environment.outside.pressure.{trend,prediction}.*`
carry overlapping derivations of the same reading from different plugins.

**Two host-metric trees, plus Telegraf.** `environment.rpi.*` comes from the
SignalK RPi plugins; `host.{cpu,disk,memory}.*` comes from another SignalK
source; Telegraf writes raw `cpu`, `mem`, `disk`, `swap`, `system` and friends
directly. All three describe the same machine. The System health dashboard
reads Telegraf and `environment.rpi.*`, because those two between them cover
throttling, SD wear and per-service memory, which the others don't.

**The same two Cerbo relays appear twice**, as
`electrical.switches.venus-{0,1}.state` and as
`electrical.switches.gx.gxInternalRelay{1,2}.state`.

**`electrical.venus-input.{1,2,4}`** uses a hyphen, which no other branch in
the tree does.

**`environment.venus.20.status`** puts what is a Cerbo device instance under
`environment`.

**`electrical.chargers.VictronACCharger`** names the instance after the
sensor class rather than the device. Only `state` and `signalStrength` are
present: the bt-sensors config also declares `batt1`..`batt3`, `curr1`..`curr3`
and `temp` against `electrical.chargers.{id}.*`, and that `{id}` placeholder
is not substituted, so those paths never materialise.

**Refrigerator humidity is `humidity`**, where the neighbouring cabin sensor
uses `environment.inside.relativeHumidity`. The SignalK dictionary term is
`relativeHumidity`.

**Sensor identifiers use three schemes at once** —
`sensors.houseBattery1.signalStrength` (camelCase logical name),
`sensors.refrigerator.switchbot.battery` (logical name plus vendor segment),
and `sensors.House_Battery_1_A5_C2_37_40_01_46.reachable` (display name plus
MAC, generated by bt-sensors rather than configured).

**Renaming a Bluetooth device mints new series.** The one IP22 charger has
appeared as `Victron_VictronACCharger_Model_ID_27054_...`,
`Victron_VictronACCharger_Model_ID_Unknown_...` and
`Victron_Blue_Smart_IP22_Charger_12_30_3_...`, all against the same MAC. The
dashboards read the most recent.

**Battery instance identifiers are mixed, and the two JBD packs are not
peers.** The house bank is `electrical.batteries.house`, reached by a
`signalk-path-mapper` rule that rewrites `electrical.batteries.279`. The two
JBD packs stay as `0146` and `5C90`, fragments of their serial numbers.
Notifications still fire against the pre-mapping name —
`notifications.electrical.batteries.279.lowVoltage`.

Any renaming scheme here has to account for what the packs actually are:
`5C90` is wired into the system and tracks the Victron shunt to within 10 mV;
`0146` is a spare sitting disconnected with its terminals plugged (log entry
of 2026-08-13). A symmetric pair of names — `houseA`/`houseB` or similar —
would assert a two-pack bank that does not exist, and would invite reading the
spare's state of charge as half the house capacity. Both packs advertise the
same BLE name, `DP04S007L4S200A`, so only the MAC distinguishes them.

## Org and buckets

One org, `symphony`. The org is InfluxDB's tenancy boundary -- tokens, users,
buckets and dashboards all hang off it, a token belongs to exactly one org,
and a bucket cannot be reassigned to another. That makes it the one boundary
that is expensive to get wrong, and the one there is no reason to cross here:
a second org would put data permanently out of reach of the same query.

It is named for the vessel rather than the owning LLC because neither name is
durable and the vessel's is the one a person reading a dashboard recognises.
Renaming an org is cheap and non-destructive -- the ID is stable, buckets stay
attached -- so this is reversible; putting data in *separate* orgs is not.

Buckets are named after whoever writes them:

| Bucket | Writer | Retention |
| --- | --- | --- |
| `signalk` | `signalk-to-influxdb2`, full rate | 90d |
| `signalk_archive` | the same plugin, second entry, decimated to 1/min | years |
| `telegraf` | Telegraf | 30d |
| `influxdb` | InfluxDB's own `/metrics` scrape | 7d |

Retention is a per-bucket property, and that is the whole argument for the
split: one bucket cannot express "years of state-of-charge, two weeks of CPU."
The second argument is credentials -- Telegraf currently borrows captain's
all-access token because there was nothing narrower to scope to.

The split costs nothing at query time, because the bucket is named in the Flux
query rather than in the datasource. `defaultBucket` is only Grafana's
starting point for ad-hoc exploration; one datasource and one read token reach
all four, and a panel can `union()` across them.

`signalk_archive` holds the same paths at lower rate rather than a chosen
subset of paths. Splitting by topic would mean deciding today which paths
matter in three years, and giving every panel a lookup table of which bucket
its path lives in. A superset at lower resolution needs neither.

The mechanism is that `influxes` in the plugin config is an array, and each
entry is an independent writer with its own bucket, filters and `resolution` --
so the archive tier needs no InfluxDB task, and no task competes for RAM on a
Pi where memory is the constraint. The cost is that `resolution` *decimates*
rather than averages: it drops updates arriving inside the window, so the
archive keeps trends and loses spikes between samples.

## Cardinality

The `symphony` bucket accumulated roughly 1,400 more measurements than the
vessel produces, because `signalk-to-influxdb2` had both `filteringRules` and
`ignoredPaths` empty and so wrote everything SignalK knew:

- `observations.noaa.*` -- around 150 shore and airport stations, eight paths
  each, at a top-level `observations.` branch outside `environment`
- `vhfdata.nearest.*` and `pointsOfInterest.wikipedia.*` -- a few hundred more
- `notifications.noaa.urn:oid:...` -- one measurement per NWS alert, each with
  a unique identifier, and nothing retires them
- InfluxDB scrapes its own `/metrics` into the same database: `go_*`,
  `storage_*`, `task_*`, `qc_*`, `http_*`, `service_*`, `influxdb_*`
- `<empty>` -- the plugin's sentinel for a delta arriving with an empty path

The NWS alert measurements were the only unbounded growth. `ignoredPaths` in
RUNBOOK.md ("The signalk-to-influxdb2 change") covers all of these, and is a
larger win on SD-card write volume than the bucket split is.

## Two Grafanas, two InfluxDBs

`reference/software_stack.md` covers the SignalK→InfluxDB→Grafana and
SignalK→QuestDB→`signalk-grafana` split. One more fragment belongs with it:
the `signalk-usage` plugin writes to org `signalk`, bucket `signalk` — not the
`symphony` org and bucket everything else uses — so its tankage and power
reporting is not queryable from the provisioned dashboards.

## Dashboards

The five dashboards previously in this repo were copied from Lille Ø
(`meri-imperiumi/lille-oe`) unmodified: the same dashboard UIDs, the same
library-panel references to panels that exist only in that vessel's Grafana,
and that vessel's paths — `electrical.solar.flinsail.panelPower`,
`electrical.chargers.hydrogenerator.power`, `networking.lte.*`. They also used
InfluxQL query-builder targets while this repo provisions its datasource with
`version: Flux`. Nothing in them could render.

They are replaced by six generated dashboards — Navstation, Navigation,
Electricity, Weather, Life support, System health — built from the panel spec
in `scripts/build_dashboards.py`. The generated JSON is committed, because
Grafana provisioning reads files and the boat has no build step; edit the spec
and regenerate rather than editing the JSON.

`scripts/audit_dashboard_paths.py` checks every measurement the dashboards
reference against what InfluxDB has actually seen, and exits non-zero on
anything missing or stale. It has to run on the boat — it reads the InfluxDB
token from the live plugin config. A panel pointed at a path nothing publishes
does not error; it draws an empty graph, which looks exactly like a quiet
sensor. That is how the ported dashboards sat here looking plausible.
