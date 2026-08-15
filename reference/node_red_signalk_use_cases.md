# Node-RED + SignalK use cases: community survey

Researched 2026-08-15. Breadth-first web survey (SignalK's own GitHub/forum
ecosystem, OpenPlotter/Victron/DIY communities, and cruiser forums/blogs) of
what boat owners actually build with Node-RED on top of SignalK. List 1 is
the raw categorized inventory. List 2 stack-ranks it by cross-source
popularity. List 3 checks it against Symphony's own plugin inventory and
monitoring posture as documented in this repo — see the note at the top of
that section before trusting it.

## List 1 — categorized use cases

### A. Anchor & ground tackle
- Anchor watch dashboard: swing-radius calc from rode length + depth, live
  drift distance, drag alarm at ~110% radius, drop/raise/silence controls,
  history logged to InfluxDB
- Dedicated anchor-alarm plugin built to pair with Node-RED for push
  notifications, colored track + AIS overlay, auto-disables when engine
  RPM > 0
- Flip a relay/switch (light, siren) when the anchor alarm fires
- DIY windlass chain counter (ESP8266/ESP32) feeding live rode-out length
  into SignalK, wireless up/down/stop control, auto pay-out/retrieve to
  preset scope
- Reminder alert if anchor light isn't switched on after dropping anchor
- Automated anchor light + ACR (charging relay) switching logic

### B. Condition/equipment alarms
- Switch-left-on alarm (canonical example: anchor washdown pump left
  running >10 min)
- Water tank overfill alarm (>96%), auto-clears on drop
- Bilge pump dry-run auto-cutoff (runs >1 min at low current)
- Bilge pump excessive-cycling / long-runtime alarm (early leak indicator)
- High-water bilge event auto-starts generator + sends SMS
- Shore-power-loss / low AC input voltage alarm (active only while docked)
- Low starter-battery voltage alarm with debounce (ignores engine-crank dips)
- Battery over-temperature warning
- High wind speed alarm
- CO2 / smoke / excess-heat safety alerts
- Nav-light reminders (left on by day / forgotten off at night while
  underway)
- Engine health alarms (RPM, oil/seawater/fuel pressure, coolant temp,
  exhaust temp)
- Engine JSON status transformed into 1–5 severity value for a Grafana
  traffic-light panel

### C. Alert delivery / notification channels
- Pushover push notifications for remote (off-boat) alerts
- Local audible beeper via Pi GPIO relay, distinct pulse cadence per
  severity (alert/warn/alarm/emergency)
- Telegram bot alerts via a custom "Renotifier" plugin/script
- Text-to-speech alarm announcements (Google Speech + USB speaker)
- Alarms routed through the boat's Fusion stereo/entertainment system
- Email alert on any SignalK notification/alarm
- SMS alerts for critical events
- Boat-to-shore texting over Meshtastic LoRa mesh (2-way — get alerted, or
  text the boat to turn on a light before returning by dinghy)
- Discord/Slack chatbot nodes used as alternates to Pushover
- Self-hosted ntfy as a LAN-only delivery path when the internet is down

### D. Battery, solar & power management
- LED indicator showing Victron Blue Smart Charger state
  (bulk/absorption/float)
- SOC-based load shedding (cut non-critical DC loads below a threshold)
- Generator auto-start/stop by SOC threshold or schedule
- Scheduled/off-peak battery charging (activate a charge profile at set
  SOC/time)
- Excess-solar diversion to an immersion/water heater via smart relay
- MPPT charge-controller relay switching (e.g., relay on once fully charged)
- Reducing MPPT charge voltage via Node-RED logic
- Battery heater auto-enabled once solar input voltage crosses a minimum
  (cold climate)
- Estimated battery time-remaining calculator (time-to-empty/time-to-full)
- SOC-triggered relay/light (on ≥85%, off below threshold)
- Grid/shore-power draw automation (on overload warning, low SOC, or
  night-rate periods)
- Battery charge-limit slider dashboard (PUT to chargeLimit, remote via
  WilhelmSK)
- Venus OS/Cerbo GX ↔ SignalK bridge (Node-RED relays battery data over
  MQTT/N2K between the two systems)

### E. Digital switching, relays & lighting
- GPIO-driven relay/switch panels, often paired with a KIP dashboard button
  UI
- Dimmer switch flow (PUT to `.dimmingLevel`) for cabin/deck lighting
- Hella LED dimmer automation, incl. adding a second physical control point
  via a Shelly relay emulating the button
- Motion-activated night lighting, gated by day/night derived state
- MQTT-controlled onboard lighting mirrored back to a Node-RED dashboard
- Zigbee stick-on wireless buttons (tap/hold/double-tap) mapped to light
  toggles

### F. Sensor integration (getting non-native data into SignalK)
- Zigbee sensor network: door/hatch, motion, temp/humidity, smoke/CO (one
  owner: 30 devices, 2+ years)
- BLE/Bluetooth fridge & freezer temperature monitoring (RuuviTag)
- 1-Wire DS18B20 temperature sensors via GPIO (engine room, fridge, outside)
- Ecowitt personal weather station bridge (indoor/outdoor temp, humidity,
  pressure)
- Raspberry Pi Sense HAT integration (accel/gyro/mag/temp/humidity/pressure)
- BME280 environmental sensor folded into an NMEA multiplex stream
- Shelly WiFi temp/humidity sensor emitted as a custom NMEA2000 PGN for
  chartplotters lacking a SignalK plugin

### G. Data logging, dashboards & analytics
- Full InfluxDB + Grafana + Node-RED stack for historical logging and
  dashboards
- Semi-automatic electronic logbook (auto position/conditions entries,
  engine start/stop, sail changes, autopilot toggles)
- Automatic trip-distance logger (resets when anchored/moored)
- Remote LED data-repeater display cycling through 5 instrument views,
  driven by Node-RED
- Moving InfluxDB writes out of the native plugin into Node-RED for more
  flexible parsing/rate control
- Live SignalK REST/API values rendered as Node-RED Dashboard widgets

### H. Safety & security
- Man-overboard detection via a BLE beacon going out of range (buzzer +
  position log)
- Door/hatch/motion sensors used as an intruder alarm while unattended at
  anchor or dock

### I. Home automation / platform bridging
- SignalK ↔ Home Assistant bridge (MQTT or websocket node) for HA
  dashboards/automations
- HomeSeer HS4 integration alongside InfluxDB/Grafana

### J. Navigation & instrument data processing
- True heading derived from magnetic heading + variation
- Set-and-drift (current) calculation from heading/COG/STW/SOG/variation
- Custom NMEA2000 PGN generation from SignalK paths (for proprietary
  chartplotter compatibility)
- Node-RED as an NMEA 0183 multiplexer on a Raspberry Pi
- AIS collision-risk alerting (CPA/TCPA calculation → warn/alarm)
- Pulling a full vessel data snapshot (`getPath()`) inside a function node
  for custom math

### K. Connectivity & remote access
- Starlink performance monitoring dashboard + automated alerts
- Remote dashboard/control access via SSH tunnel ("Remote-RED")
- SNMP polling of router/internet status, logged to InfluxDB, alerts on
  connection drop
- Virtual N2K switch/indicator surfacing router WAN status (or battery
  voltage "ok" state) on chartplotter displays

### L. Specialty equipment control
- Spectra Watermaker remote control (start/stop, speed, stats, auto-stop at
  tank fill %)
- Brineomatic open-source watermaker Node-RED integration
- Garmin Reactor autopilot control (engage/disengage, 1°/15° heading nudges)
- Stainless Lobster fridge/compressor monitoring over USB

### M. Weather
- Barometric pressure trend-based squall/foul-weather alert
- Publishing live boat weather data to Windy.com as a public station
- NOAA/BBXX synoptic weather report generation
- Auto-download of Saildocs GRIB weather files to Dropbox

### N. Misc / utility
- Countdown/sleep timer (auto-stop music playback, reset/shutdown Pi
  buttons)
- Geofence-triggered auto-tweet on marina arrival/departure
- Tank-sender calibration (map raw sensor values to accurate %)
- Fuel consumption/economy tracking (twin-engine rate calc, persists across
  restarts)
- Generic water-utility SCADA/HMI template adapted for boat tank + pump
  automation

## List 2 — stack rank

Ranking value is an approximate count of distinct sources/threads (forum
posts, official docs, blog posts, GitHub discussions, repos) found across
the research sweep that referenced this specific pattern. The three research
passes overlapped on some sources (especially GitHub Discussions), so these
counts likely have some double-counting and should be read as ordinal
(relative ranking), not as a precise citation count.

| Rank | Use case | Approx. source count |
|---|---|---|
| 1 | Anchor watch/drag alarm & dashboard | 5 |
| 2 | LED/dashboard indicator for Victron charger state | 6 |
| 3 | Low starter-battery voltage alarm with debounce | 4 |
| 4 | Local audible beeper with severity-based cadence | 4 |
| 5 | SignalK ↔ Home Assistant bridge | 4 |
| 6 | GPIO digital switching/relay panels + KIP UI | 4 |
| 7 | Venus OS/Cerbo GX ↔ SignalK bridge | 4 |
| 8 | Pushover remote push notifications | 3 |
| 9 | Switch-left-on alarm pattern | 3 |
| 10 | Excess-solar diversion to water heater | 3 |
| 11 | MPPT charge-controller relay switching | 3 |
| 12 | Bilge pump monitoring (dry-run cutoff / cycling / high-water) | 3 |
| 13 | Zigbee sensor network | 3 |
| 14 | InfluxDB + Grafana + Node-RED logging stack | 3 |
| 15 | Engine health alarms/dashboard | 3 |
| 16 | Shore-power-loss / low AC alarm | 2 |
| 17 | Generator auto-start/stop by SOC | 2 |
| 18 | Water tank overfill alarm | 2 |
| 19 | SNMP router/internet monitoring | 2 |
| 20 | True heading derivation from magnetic + variation | 2 |
| 21 | Man-overboard detection via BLE beacon | 2 |
| 22 | AIS collision-risk alerting (CPA/TCPA) | 2 |
| 23 | Semi-automatic electronic logbook | 1 |
| 24 | Starlink monitoring dashboard | 1 |
| 25 | Meshtastic off-grid boat-to-shore texting | 1 (one origin post, widely reshared) |

Everything in List 1 below this cutoff is a single-source mention not
reflected in this ranking.

## List 3 — gaps against Symphony's own setup

**This is a first, rough pass, not a thorough comparison.** Everything below
is [recall] — read off this repo's own reference docs
(`software_stack.md`, `monitoring_decisions.md`, `monitoring_posture.md`,
`signalk_plugin_watchdog.md`, `signalk_paths.md`, `priorities.md`) and the
`signalk/plugin-config-data/` file listing as of 2026-08-15, not measured
live on the boat. A plugin file existing doesn't mean it's enabled and
working; a path never having been published doesn't mean it never will be.
Treat every tag below as a starting point to verify, not a verdict.

Tags used: **gap** — no existing plugin/flow does this and the needed data
already exists, so it's buildable now; **gap, blocked** — not implemented,
and the underlying sensor/equipment data doesn't exist in Symphony's
SignalK tree yet; **gap, n/a** — not implemented, and the equipment doesn't
exist on this vessel today.

### A. Anchor & ground tackle
- Anchor swing-radius dashboard + InfluxDB history + manual controls —
  **gap**. The drag-alarm core is already covered (see excluded list
  below); this dashboard/logging layer on top of it is not built.
- Flip a relay/switch when the anchor alarm fires — **gap**. No delivery
  or actuation is currently wired to the anchor alarm notification either.
- DIY windlass chain counter — **gap, blocked**. No rode-position sensor
  or path exists.
- Reminder to switch on the anchor light — **gap**. Ties to the
  not-yet-built COLREGs nav-lights plugin already in `priorities.md`.
- Automated anchor light + ACR switching — **gap**. Same — no
  nav-light/ACR automation exists yet.

### B. Condition/equipment alarms
- Switch-left-on alarm (generic pattern) — **gap**. Node-RED currently
  runs only the openweather humidity-fix flow.
- Water tank overfill alarm — **gap, blocked**. `tanks.*` has never been
  published on Symphony — no tank senders installed.
- Bilge pump dry-run cutoff / excessive-cycling / high-water alarms —
  **gap, blocked**. No bilge pump current-draw or bilge-water-level path
  found in the tree.
- Shore-power-loss / low-AC alarm — **gap**, buildable now.
  `electrical.chargers.VictronACCharger.state` is already published;
  nothing currently watches it for a loss condition.
- Low starter-battery voltage alarm — **gap, blocked**. No starter-battery
  voltage path is published; only house/JBD-pack batteries are
  instrumented, and "charger for starter battery" is still an unbuilt
  electrical task.
- Battery over-temperature warning — **gap, blocked**. No battery
  temperature path is confirmed among the published battery values.
- High wind speed alarm — **gap**, buildable now.
  `wind.speedTrue`/`directionTrue` are already published; no alarm/zone is
  configured on them.
- CO2 / smoke / propane safety alerts — **gap, blocked**. No gas/smoke
  sensor path exists; a CO detector and propane sensor are still on the
  still-to-buy physical list.
- Nav-light reminders — **gap**. Same as the anchor-light item above.
- Engine health alarms — **gap, blocked**. `propulsion.*` is entirely
  absent — no engine data reaches SignalK at all yet.
- Engine-JSON→Grafana severity transform — **gap, blocked**. No engine
  telemetry exists to transform.

### C. Alert delivery / notification channels
- Telegram bot alerts — **gap**. No Telegram integration found anywhere in
  the stack.
- Text-to-speech alarm announcements — **gap, blocked**. No speaker exists
  yet at all (same hardware gap blocking the GPIO beeper below).
- Alerts via the boat's stereo — **gap**. No such integration.
- Email alert on any SignalK notification — **gap**. No working SMTP path;
  `signalk-healthcheck`'s `sendEmail` is off and was never configured.
- SMS alerts — **gap**. No SMS integration.
- Boat-to-shore texting over Meshtastic — **gap, blocked**. No
  Meshtastic/LoRa hardware aboard.
- Discord/Slack bot alerts — **gap**. No such integration.

### D. Battery, solar & power management
- Physical LED indicator for charger state — **gap**. The data
  (`VictronACCharger.state`) is already available; no GPIO LED output flow
  is built.
- SOC-based load shedding — **gap**. No relay-actuation flow tied to SOC
  found.
- Generator auto-start/stop by SOC — **gap, n/a**, confirmed. Owner
  confirmed 2026-08-15: no generator, none planned — the future charging
  plan is solar + alternator with a DC-DC charger when not at the dock.
  Worth revisiting the other solar-dependent gaps in section D against
  that plan once solar is actually installed.
- Scheduled/off-peak battery charging — **gap**. No schedule-driven
  charging flow found.
- Excess-solar diversion to a water heater — **gap, blocked**.
  `electrical.solar.*` has never been published — no solar/MPPT monitoring
  exists yet.
- MPPT relay switching / voltage reduction — **gap, blocked**. Same — no
  solar/MPPT data.
- Battery heater auto-enable — **gap, n/a**. No battery heater equipment
  known.
- SOC-triggered relay/light — **gap**. No such automation flow found.
- Grid/shore-power draw automation — **gap**. Shore-power state is
  readable (`VictronACCharger`) but nothing automates drawing from it.
- Battery charge-limit slider dashboard — **gap**. No PUT-based
  charge-limit control flow found.

### E. Digital switching, relays & lighting
- GPIO relay/switch panel automation via Node-RED — **gap**. `switches.*`
  paths and KIP both exist, but no Node-RED-driven relay-control flow was
  found — only the humidity-fix flow runs.
- Dimmer switch flow — **gap**. No dimming path/plugin found; cabin
  lighting circuits are still an unbuilt electrical design item.
- Hella LED dimmer automation — **gap, blocked**. No Hella dimmer hardware
  confirmed aboard.
- Motion-activated night lighting — **gap, blocked**. No motion sensors or
  Zigbee gateway aboard.
- MQTT-controlled lighting — **gap**. No MQTT broker/lighting bridge found.
- Zigbee stick-on buttons — **gap, blocked**. No Zigbee gateway; Symphony's
  wireless sensors come in over BLE (`bt-sensors-plugin-sk`) instead.

### F. Sensor integration
- Zigbee sensor network generally — **gap, blocked**. No Zigbee gateway
  aboard.
- 1-Wire DS18B20 temperature sensors — **gap, blocked**. None deployed;
  "additional temperature sensors" is still an open backlog item.
- Sense HAT — **gap, n/a**. No such hardware, and would overlap
  `signalk-rpi-monitor`/Telegraf for host metrics.
- Shelly sensor → custom N2K PGN — **gap, n/a**. No Shelly sensors and no
  proprietary chartplotter needing PGN translation identified.

### G. Data logging, dashboards & analytics
- Remote LED data-repeater display — **gap, n/a**. No such remote display
  hardware.
- Live SignalK values as Node-RED Dashboard widgets — **gap**, but low
  value: KIP, freeboard-sk and Grafana already serve as the boat's
  dashboards.

### H. Safety & security
- MOB detection — **gap, blocked**, confirmed. Owner confirmed 2026-08-15:
  no MOB button or crew-tag hardware of any kind aboard — the BLE-tag
  pattern specifically needs hardware that doesn't exist. What does exist:
  a handheld VHF with DSC and an emergency button, and an AIS Class B
  transceiver. `signalk-mob-notifier` is installed; whether it (or
  anything else) consumes a DSC distress alert, an AIS MOB beacon message,
  or neither is unconfirmed. **Verification has to come from documentation
  or source, never from live-testing the DSC emergency button** — that
  sends a real distress call to the Coast Guard on Ch 16, with possible
  legal/regulatory consequences. Owner confirmed 2026-08-15 this is a
  standing rule, not a one-off caution — see `maintenance/priorities.md`.
  Owner wants MOB detection eventually (medium-low priority, open research
  item as of 2026-08-15, not immediately planned) and is only willing to
  adopt a solution already proven elsewhere to work reliably — not
  something built and validated on this boat.
- Door/hatch/motion intruder alarm — **gap, blocked**. No door/hatch/motion
  sensors or Zigbee gateway aboard.

### I. Home automation / platform bridging
- SignalK ↔ Home Assistant bridge — **gap**. No Home Assistant instance
  found anywhere in the stack.
- HomeSeer HS4 integration — **gap, n/a**. No HomeSeer in use.

### J. Navigation & instrument data processing
- True heading derived from magnetic heading + variation — **gap**,
  buildable immediately and the lowest-effort item on this whole list:
  `signalk-derived-data` is already installed, but its
  `heading`/`cog_true`/`magneticVariation` calculators are explicitly
  disabled, and the inputs (`headingMagnetic`, `magneticVariation`) are
  already published.
- Set-and-drift calculation — **gap**. No set/drift path found among
  published values.
- Custom NMEA2000 PGN generation from SignalK — **gap**. No evidence of
  any PGN-generation flow; the boat only receives N2K today.
- AIS collision-risk alerting (CPA/TCPA) — **gap, blocked**. AIS doesn't
  appear to be fully powered/operational yet — `priorities.md` notes
  position-source-priority work is still waiting on "when the AIS is
  powered."

### K. Connectivity & remote access
- SNMP router/internet polling to InfluxDB — **gap**, but partially
  redundant: the heartbeat already probes uplink health a different way
  (a raw-IP probe gating its Pushover escalation).
- Virtual N2K switch/indicator (e.g. router status on a chartplotter
  display) — **gap**. No such indicator exists.
- Starlink monitoring dashboard — **gap, n/a**, confirmed. Owner confirmed
  2026-08-15: no Starlink aboard.

### L. Specialty equipment control
- Spectra/Brineomatic watermaker control — **gap, n/a**. No watermaker
  aboard — it's on `priorities.md`'s Someday/Maybe list.
- Autopilot control via Node-RED PUT — **gap**. `@signalk/signalk-autopilot`
  is installed and `steering.autopilot.*` is published, but nothing drives
  it from Node-RED; note pypilot is a separate, unbuilt backlog project and
  not confirmed to be the boat's current autopilot.
- Fridge/compressor current-draw monitoring — **gap** (partial — fridge
  *temperature* is already covered via BLE; compressor current draw
  specifically is not monitored).

### M. Weather
- Barometric-pressure-trend alert — **gap**, buildable immediately: both
  barometer trend/prediction trees are already published; nothing
  currently turns a pressure drop into a notification.
- NOAA/BBXX synoptic weather report generation — **gap**, questionable fit
  — not installed, and unclear this adds anything beyond the NOAA plugins
  already in use.
- Auto-download GRIB weather files — **gap**. No Saildocs/GRIB integration
  found.

### N. Misc / utility
- Countdown/sleep timer dashboard — **gap**, low value: trivial Node-RED
  pattern, no clear need identified.
- Geofence auto-tweet on arrival/departure — **gap**, low value: no
  geofence flow and no social-posting integration anywhere in the stack.
- Tank-sender calibration — **gap, n/a**. No tanks instrumented yet.
- Fuel consumption/economy tracking — **gap, n/a**. No engine/fuel data
  exists.
- Water-utility SCADA template — **gap, n/a**. No tanks/pumps instrumented.

### Excluded — already covered (not in the gap list above)

- Dedicated anchor-drag alarm — `signalk-anchoralarm-plugin` (installed
  per `priorities.md`)
- Pushover push notifications — `signalk-pushover-notification-relay`
  (installed) plus the heartbeat's own separate Pushover escalation
- Self-hosted ntfy delivery (LAN-only fallback) — `signalk-ntfy`
  (installed and delivering per `priorities.md`)
- Local audible beeper mechanism — `signalk-gpio-beeper-plugin` is
  installed; only the speaker/piezo hardware is pending, not the software
- Battery time-remaining calculator — already a published path
  (`batteries.house.*` time remaining)
- Venus OS/Cerbo GX ↔ SignalK bridge — native `venus` +
  `vedirect-signalk` plugins
- BLE fridge/freezer temperature monitoring — `bt-sensors-plugin-sk`
  (SwitchBot thermometer)
- Outside weather (temp/humidity/pressure) ingestion —
  `open-meteo` + `openweather-signalk`
- InfluxDB + Grafana + Node-RED logging stack — already the boat's whole
  history/forensics stack
- Semi-automatic electronic logbook — `signalk-logbook` (installed)
- Trip-distance logging — `navigation.trip.log` already published
- Publish weather data to Windy.com — `signalk-windy-plugin` (installed)
- Remote dashboard/control access — Tailscale SSH already provides this,
  more generally than an SSH-tunneled Node-RED editor would
