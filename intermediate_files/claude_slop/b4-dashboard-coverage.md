# B4 — which Grafana dashboard set is the QuestDB port target

Evidence: boat's `/var/lib/grafana/grafana.db` read read-only (copied off via
`sudo cat`, nothing on the boat touched) — tables `dashboard`,
`library_element`, `data_source`; and the six generated JSON files in
`grafana/provisioning/dashboards/json/`. Path liveness is per
`reference/signalk_paths.md` (§ What this boat publishes / Absent entirely).

## Panel counts

| Set A — boat (InfluxQL) | Panels | Library-panel instances | Set B — repo (Flux) | Panels |
| --- | --- | --- | --- | --- |
| Navigation | 12 | 6 | Navigation | 19 |
| Electricity | 19 | 4 | Electricity | 30 |
| Life support | 12 | 4 | Life support | 14 |
| Navstation under way | 22 | 5 | Navstation | 21 |
| Weather | 11 | 4 | Weather | 32 |
| — | — | — | System health | 25 |
| **Total** | **76** | **23** | **Total** | **141** |

Distinct measurements queried: A 59, B 123, shared 17.
Fields: A queries `value` and `stringValue` only. B queries `value`, plus
`lat`/`lon` on `navigation.position`, plus 26 Telegraf/InfluxDB-internal
fields on the System health dashboard.

## How much of Set A works today

Only one datasource exists on the boat: `influxdb` uid `ee2ppw626cqo0a`.
Across the five dashboards there are 167 datasource references — 158 to
`eWjoLxAnk` (does not exist), 4 to the real uid, 5 to the built-in `grafana`.
Every *target*-level reference in dashboard JSON is `eWjoLxAnk`; the 4 real-uid
references are panel-level and are overridden by their targets.

| Panels | State |
| --- | --- |
| 52 | inline query panels, all targets on the dangling uid — dead |
| 15 | library-panel instances whose library element is an empty stub (`{"description":"","type":""}`, no targets) — render nothing |
| 4 | library-backed, real uid, live paths: SOG ×2, Heading ×2 (`navigation.speedOverGround`, `navigation.headingTrue`) — working |
| 4 | library-backed, real uid, but query `electrical.batteries.279.capacity.{stateOfCharge,timeRemaining}` — the pre-mapping name; `signalk-path-mapper` now rewrites 279 → `house`, so current writes land elsewhere |
| 1 | text panel, no query |

So **4 of 76 panels are working, 8 at most**. 9 of the 13 library elements are
empty stubs.

## 1. In Set A, not in Set B (42 measurements)

**Paths that do not exist on this boat** — no panel is possible, in any
dashboard set (all confirmed absent in `reference/signalk_paths.md`):
`environment.depth.belowTransducer`; `environment.wind.speedApparent`,
`.angleApparent`; `navigation.speedThroughWater`; `performance.polarSpeed`;
`navigation.anchor.currentRadius`; `tanks.fuel.diesel.currentLevel`,
`tanks.freshWater.water.currentLevel`; `propulsion.main.runTime`;
`networking.lte.{bars,rssi,usage.rx,usage.tx}`;
`electrical.chargers.alternator.power`, `.hydrogenerator.power`,
`.multiplus.chargingMode`; `electrical.inverters.multiplus.{acin,acout}.power`;
`electrical.venus.totalPanelPower`, `.acSource`;
`electrical.solar.{cabintop,aftarch,flinsail}.panelPower`;
`electrical.batteries.starter.voltage`; `environment.inside.temperature` and
the per-cabin `environment.inside.{saloon,mainCabin,heads,wardrobe,engineRoom}.temperature`
and `.{mainCabin,heads,wardrobe}.relativeHumidity`;
`environment.sun`;
`environment.outside.pressure.prediction.{quadrant,beaufort}`.

**Same thing under a different name, already in Set B:**

| Set A | Set B equivalent |
| --- | --- |
| `environment.outside.heatIndexTemperature` | `environment.outside.feelsLikeTemperature` |
| `environment.outside.humidity` | `environment.outside.relativeHumidity` |
| `electrical.batteries.279.capacity.*` | `electrical.batteries.house.capacity.*` |
| `environment.wind.speedOverGround` (not in the confirmed-present list) | `environment.wind.speedTrue` |

**Genuinely missing from Set B, on a live path: one.**
`navigation.headingTrue` (live since 2026-08-19, derived). Set B renders
heading from `navigation.headingMagnetic` + `navigation.magneticVariation`
instead. One panel to add.

## 2. In Set B, not in Set A (106 measurements)

Nothing in Set A covers any of these:

- **Batteries, per-pack** (28): `electrical.batteries.{5C90,0146}.*` — SoC,
  voltage, current, temperature, cycles, remaining capacity, `cell0..3.voltage`,
  `protectionStatus`, `FETStatus`.
- **House bank detail** (4): `.power`, `.capacity.{consumedCharge,dischargeSinceFull,dischargedEnergy}`.
- **Cerbo / charger state** (7): `electrical.venus.state`,
  `electrical.chargers.VictronACCharger.state`,
  `electrical.venus-input.{1,2,4}.state`, `electrical.switches.venus-{0,1}.state`.
- **Bluetooth sensor health** (8): `sensors.*.{reachable,signalStrength,battery}`
  for both JBD packs, the SwitchBot fridge probe and the IP22 charger.
- **GNSS quality** (7): `navigation.gnss.*`; plus `navigation.position` (map),
  `navigation.headingMagnetic`, `navigation.magneticVariation`,
  `steering.autopilot.engaged`.
- **Weather depth** (26): pressure deltas/history/trend severity/front
  prognose, `environment.outside.{wind.speed,wind.gust,wind.direction,dewPointTemperature,cloudCover}`,
  `environment.tide.*`, `environment.sunlight.times.*`, `environment.moon.*`,
  `environment.noaa.swpc.*`.
- **Fridge/cabin humidity** (3): `environment.inside.refrigerator.humidity`,
  `environment.inside.relativeHumidity`, `environment.outside.relativeHumidity`.
- **System health, whole dashboard** (18 measurements): `environment.rpi.*`
  (CPU/GPU temp, memory, SD, uptime) and Telegraf's `cpu`, `mem`, `swap`,
  `disk`, `diskio`, `net`, `system`, `processes`, `procstat`, `chrony`,
  `rpi_health`, plus InfluxDB internals.

## 3. Recommendation — teach the generator to emit SQL

The evidence supports Mark's lean, strongly.

- Set A is not a working dashboard set to preserve: 4 of 76 panels render.
- 36 of the 42 measurements Set A has and Set B lacks are paths this boat has
  never written; 5 more are naming variants Set B already covers. The real
  porting debt from Set A is **one panel** (`navigation.headingTrue`).
- Set B covers 106 measurements Set A cannot see at all, including every
  per-pack battery cell, all Bluetooth sensor health, GNSS quality and the
  entire System health dashboard.
- The port is small and localised: all Flux in Set B comes from
  `scripts/build_dashboards.py`'s `flux()` and `flux_position()`, called from
  six sites, all inside `_render()`. QuestDB SQL means rewriting those two
  functions, the bucket→table mapping in `bucket_for()`, and the datasource
  uid — panel specs, layout and units are untouched.

Do: port `flux()`/`flux_position()` to QuestDB SQL, add a `navigation.headingTrue`
panel to `navigation.json`'s spec, and treat the boat's five imported
dashboards as reference material to read once, not as a migration source.
