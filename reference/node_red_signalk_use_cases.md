# Node-RED + SignalK use cases: community survey

Researched 2026-08-15. Breadth-first web survey (SignalK's own GitHub/forum
ecosystem, OpenPlotter/Victron/DIY communities, and cruiser forums/blogs) of
what boat owners actually build with Node-RED on top of SignalK. The
inventory below is the durable part: an idea list to pull from when a job
comes up. What each idea would take on this boat is a live question, not a
recorded one.

## The inventory

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
  position log). What the aboard DSC/AIS hardware feeds is now settled —
  see `reference/distress_monitoring.md`.
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

## What the survey produced

Two items were buildable immediately and are tracked in `priorities.md`:
deriving true heading from magnetic heading plus variation
(`signalk-derived-data` is already installed), and turning a barometric
pressure drop into a notification (both barometer trend trees are already
published).

Everything else in List 1 is either already covered aboard (below) or was an
unverified desk comparison against this repo's own docs, which is not worth
carrying as reference — re-check against the live boat if a category becomes
interesting.

## Not applicable to Symphony

Facts worth keeping so the same categories aren't re-evaluated. Owner-confirmed
2026-08-15 unless noted:

- **No generator**, none planned — the charging plan is solar + alternator
  with a DC-DC charger away from the dock. Revisit section D's solar-dependent
  ideas once solar is actually installed.
- **No Starlink.**
- **No MOB button or crew-tag hardware** of any kind aboard.
- No watermaker (it is on `priorities.md`'s Someday/Maybe list), no battery
  heater, no Zigbee gateway, no Home Assistant or HomeSeer instance, no Shelly
  sensors, no Sense HAT, no remote LED repeater display.
- No tanks or pumps instrumented, and no engine/fuel data published — which
  rules out tank-sender calibration, overfill automation and fuel-economy
  tracking until sensors exist.
- No solar/MPPT data (`electrical.solar.*` has never been published), which
  blocks excess-solar diversion and MPPT relay switching.

## Already covered aboard

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
