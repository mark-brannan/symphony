# Priorities

Physical boat work — anything hands-on that isn't SignalK or embedded software
— is tracked in Evernote, not here. That's the authoritative list for what
Mark is actually working on aboard. This file is not the place to look up or
add a physical task, and the two overlapping in the short term is fine.

This file remains authoritative for the SignalK / IoT section below.

## In Progress
- Chain plate removal, cleaning, and resealing — 1 of the chain plates removed so far.
  - Next: take the removed chain plate to Ballard Sheet Metal for a fabrication quote.

## Blocked

## Backlog

### Safety & compliance
- Monthly valve check (recurring — overdue, was due 2026-07-02)
- WA state vessel registration/decals renewal
- Halon system service/check
- Service fire extinguishers

### Engine & mechanical / drivetrain
- Review overall engine state
- Permanent fix for prop shaft muff coupler (temporary solution currently in place)
- Install flame shield between fuel filter and engine
- Install radiator cap and coolant hoses

### Hull, bilge & underwater
- Clean rusted areas in bilge
- Repaint bilge (after rust cleanup)
- Clean rust off drive shaft
- Clean rust off shaft coupler
- De-rust topside (weather) deck

### Deck & rig
- Fix deck caulking; replace missing teak bungs
- Fix leaky deck boards / port stern deck leak
- Reseal small portholes; finish resealing large porthole; reseal butterfly hatches (partially done — revisit)
- Regrease all winch bearings; build box/jig for winch servicing
- Remove boomkin for rehab, refurb, reinstall
- Refinish wooden blocks/pulleys

### Plumbing & sanitation
- Address remaining holding tank system work now that the old tank is out
- Tighten head pump / apply sealant; install Y valve between Lectra-San and head
- Deep-clean water tank (due again)

### Electrical (core, non-IoT)
- GFCI outlet in head
- Secure batteries with straps; cover exposed positive battery terminals
- Wrap up DC-DC converter install (Victron Orion-Tr, purchased 2025-05-08)
- Charger for starter battery
- Research and diagram correct inverter / transfer-switch installation
- Install inverter and transfer switch correctly
- Install negative bus
- 3D-print negative bus base
- Design new positive bus
- Cut and drill new positive bus
- 3D-print positive bus base
- Design bus bar links
- Fabricate bus bar links
- Rework 3D-printed bus bar covers
- Design battery shelves
- Build battery shelves
- Design small battery holder
- 3D-print small battery holder
- Design pump circuits
- Short-term pump wiring
- Short-term shower sump wiring — white stripe is auto, solid brown is manual
- Design AC system
- Design pump system
- Design under-desk layout
- Design LED COB lighting
- Design CFL-to-LED replacements

### Interior & woodwork
- Refurb stern teak grid, bow pulpit floorboards, sink covers, hob cover
- Order replacement V-berth mattress

### Cleaning, painting & finish
- Paint engine panel
- Paint sole brace
- Paint chain locker cover
- Paint battery compartment
- Paint bilge
- De-rust rudder quadrant
- Paint/varnish rudder quadrant
- Cetol cockpit
- Cetol mid deck
- Cetol foredeck
- Topside paint: bowsprit
- Topside paint: general
- Refinish/refurb boom gallows
- Clean/wash cockpit
- Pressure wash cockpit

### Organization & storage
- Reorganize tool/parts drawers, galley, V-berth
- Pencil/utensil organizer, tool organizers for nav table

### Sharing & documentation
- Upload 3D models (e.g., deck fill cap keys) for others' benefit

### Still to buy
- Sanitation hose/fittings (1/2" and 1.5" clamps, Y connector, waste hose, PVC elbows)
- CO detector, propane sensor/alarm
- Manual bilge pump, floating winch handles, floating lanyard for deck key
- Ship's bell
- Sikasil N Plus (portlight gasket bedding), spare belt
- Fixed-mount VHF radio (Icom M10 Evo)
- Remote mic for fixed-mount VHF

### To sell / divest
- Spinnaker, Baba mainsail, other sails
- Drogue, HF radio, radar

## Someday/Maybe
- Watermaker
- Separate fridge/freezer
- Composting toilet
- Additional cabin heating
- Decide whether systems/*.md files should be tracked individually or left untracked until populated.

## SignalK / IoT

### Sensors
- Design engine temp sensors and diagram
- Design engine flow sensor plumbing
- Design engine flow sensor electrical
- Rudder position sensor
- Pump flow sensors
- Air quality sensors
- Air pressure sensor
- Illuminance sensor
- Additional temperature sensors
- Design smart pump system with voltage/current detection

### Autopilot
- pypilot
- Design pypilot board
- Separate IMU for pypilot

### Enclosures
- 3D-print gas sensor case
- 3D-print BME688 case
- 3D-print IMU case

### Infrastructure
- Finish dockerizing the boat computer — SignalK, Grafana, Dex, and Caddy run as
  native systemd services today; the repo's compose files and `RUNBOOK.md`
  describe the Docker deploy meant to replace them. Docker isn't installed on the
  Pi yet, so `docker compose --profile tls up` can't run there.
- Rebuild boat computer
- Ansible for host provisioning — research and build out, decided 2026-08-13. `RUNBOOK.md` → "Bringing up a host" is four phases of hand-run steps, and `host/install.sh` is a deliberately small stopgap: it places files and owns a few cron lines, and deliberately does not install packages. Every host-layer concern it covers — clock, watchdog, cron, gpsd — is kernel-level and survives both the Docker migration and the HALPI2 move unchanged, so this doesn't get simpler by waiting. Check whether the separate SignalK/Ansible repo referenced in `README.md` should own this before starting a third place for it.
- Get something watching the boat from off the boat. Every monitor aboard writes to InfluxDB on the Pi, so when the box dies the evidence and the alert die with it. `signalk-healthcheck` is the only outbound path and may not be able to send mail at all (separate item below). This is the gap that matters most for remote monitoring.
- Decide whether to cap journald on the Pi. It reached 639 MB on 2026-08-13, largely `user-1000` files fed by the pypilot crash loop, then self-rotated back to 192 MB. A `SystemMaxUse` cap would bound both the size and the SD-card writes, but the right number isn't obvious yet — deferred deliberately, not forgotten.
- Delete the orphaned `set-system-time` config. Confirmed 2026-08-13: `@signalk/set-system-time` is in neither `package.json`, the plugin is absent from the Pi's tree, and chrony now owns the clock outright (`systemd-timesyncd` is gone), so no SignalK time-setting plugin is wanted. Nothing left to decide — remove `signalk/plugin-config-data/set-system-time.json` and the boat's copy. It is inert either way, since SignalK ignores configs for plugins it doesn't have.
- Configure or drop `signalk-solar-forecast` and `signalk-to-influxdb-v2-buffering`. Both are installed and enabled but throw on every server start — `solar-forecast` reading `.length` of undefined at `index.js:124`, `influxdb-v2-buffering` reading `.forEach` of undefined at `index.js:120`. Neither is a missing module; both are reading a config key that was never filled in. Each start since the 2026-08-13 rebuild has logged the pair. Filling them in means supplying a location and InfluxDB credentials, so it's a real decision, not a fix.
- Decide the nine major-version plugin upgrades. As of 2026-08-13 the boat is fully current *within* its declared semver ranges — `npm outdated` shows Current == Wanted for every package — so everything below is a deliberate major bump, not routine drift. Two are safety-of-navigation and want someone watching the boat when they land: `signalk-anchoralarm-plugin` 1.18.2 → 2.0.1 and `@signalk/signalk-autopilot` 1.7.0 → 2.6.0. Four are large webapps or flows: `@mxtommy/kip` 3.12.0 → 4.8.5, `@signalk/freeboard-sk` 2.24.2 → 3.1.0, `@signalk/signalk-node-red` 3.2.1 → 4.4.0, `signalk-tides` 1.5.0 → 2.1.2. The rest are small: `signalk-postgsail` 0.5.1 → 0.6.0 (broken anyway, see the better-sqlite3 item), `signalk-noaa-space-weather` 0.19.0 → 0.20.0 (Mark's own repo — coordinate with that dev work), `vhfinfo` 0.0.34 → 0.0.37. Note `signalk/package.json` already targets the newer major for kip, freeboard, autopilot, node-red, tides and postgsail, which reads as intent — but that file describes a different install than the boat's, so it isn't authority on its own.
- Install BLE hub for lighting and related devices
- Set up real off-machine hosting (VPS or existing NAS) for Vaultwarden to hold the sops/age key backup, reachable privately (e.g. Tailscale) — currently only a local Docker proof-of-concept on the boat computer, which doesn't yet solve the single-point-of-failure risk for the key protecting `symphony.sops.yaml` / `signalk/security.json`
- Configure InfluxDB to receive data from SignalK, with appropriate data retention policies
- Revisit current InfluxDB org/bucket setup (org "darkstarllc", bucket "symphony") — consider alternatives using multiple buckets aboard Symphony
- Set up Grafana dashboards based on the public examples on GitHub from @meri-imperiumi
- Give an SSO login admin on SignalK. Every SSO login lands readonly and stays there; admin work still means the local `captain` password. The two routes are written up in `reference/software_stack.md` — have Dex synthesize a group from the email claim (Google only, no upstream change), or add an email list beside `adminGroups` upstream (covers both providers). GitHub orgs was considered and rejected.
- Decide whether to make the InfluxDB/Grafana stop stick across a reboot. Settled 2026-08-13: SignalK, InfluxDB, Grafana, Caddy, Dex and Telegraf are all expected to run and stay enabled, and all six are enabled and active as of that date. InfluxDB and Grafana are the release valve — anyone may `systemctl stop` them to recover roughly 600 MB under real memory pressure, without asking, but must not disable them, so a reboot brings them back. Real pressure means swap activity or available memory under ~400 MB, not a high load average on its own; check `free -m` and `grep ^pswp /proc/vmstat` first, and say so in-session when you stop one. Whether that should instead become a permanent disable is Mark's call and the only part still open.
- Verify Grafana SSO end to end. Its OAuth config is live, but the browser login has never been exercised. `grafana-server` is running again as of the 2026-08-13 reboot, so nothing blocks the test.
- Decide whether two SSO user records is a problem. SignalK keys OIDC users on `sub` + issuer, so the same person arrives as a separate readonly user from each provider (`mark-brannan` via GitHub, `markbrannan@gmail.com` via Google). They can't be merged; both can be granted the same permission.
- Give `signalk-healthcheck` a way to send mail, or accept that nothing leaves the boat. Confirmed dead 2026-08-13, both ways: its `mail` config holds exactly one key, `secure: false` — no host, port, user, password or from-address — while `host.sendEmail` is `true` with `toEmail` set, and the log shows it falling back to `connect ECONNREFUSED 127.0.0.1:587`, where no mail server runs. So every CPU, memory and disk alarm it has ever raised went nowhere. This is the same gap as the off-boat monitoring item above, and it is worse than it looks: that item names healthcheck as the one outbound path, and there isn't one.
- Decide what to do about `@signalk/aisreporter`. It throws `Cannot read properties of undefined` continuously, its config isn't tracked in this repo, and what is on disk has rate settings but no MMSI or endpoint — never fully configured.
- Confirm the router's DNS overrides actually resolve locally. All four names answer with the boat IP today, but with the WAN up that can't be told apart from the router forwarding to Cloudflare. The real test is unplugging the WAN and running `nslookup signalk.symphony.dark-star-llc.com`.
- Replace Telegraf's stopgap credential. It writes with `influxdb_captain_token` — captain's all-access token — because no scoped token could be minted while the store is out of sync. Once the reconciliation below is done, create a token scoped to write host metrics only, put it in sops, and point `TELEGRAF_INFLUX_TOKEN` at it in `.env.j2`. Consider a separate bucket with its own retention at the same time, so host metrics stop sharing `symphony` with vessel data.
- Fork `signalk-noaa-weather` and rewrite how it does notifications, or replace it. Disabled on the boat 2026-08-13 after it drove the Pi into a reboot loop. Its config takes a whole state (`notificationStates: "WA"`), polls every 60s, and raises every active NWS alert as a SignalK notification with `notificationSound: true` — so air-quality alerts for Spokane play sounds on a boat in Puget Sound. The notification pattern is the part worth redoing: alerts should be filtered by actual vessel position, and informational weather should not use the same alert path as a real alarm.
- Stop `signalk-healthcheck`'s memory alarm from feeding itself. It raises `host.memory.freeMemPercentage` with `method: ["visual","sound"]`, OpenPlotter plays that through VLC, and playing it consumes the memory the alarm is about. Under load the loop compounds. Either drop `sound` from the host-resource alarms or make OpenPlotter coalesce repeats — decide which layer owns it.
- Decide what to do about `signalk-polar` and `signalk-postgsail`. Both depend on `better-sqlite3@7.6.2`, which cannot compile against Node 22 — see `reference/legacy_openplotter_stack.md`. Neither has worked on this box; `signalk-postgsail` is enabled in config and silently dead. Either pin a newer `better-sqlite3` via an npm override, or remove the plugins.
- Reconcile the InfluxDB secrets in `symphony.sops.yaml` against the running database. As of 2026-08-11 all three sops tokens (`influx_token`, `influxdb_operator_token`, `influxdb_signalk_token`) return 401; the only working credential is "captain's Token" (all-access), held in `signalk/plugin-config-data/signalk-to-influxdb2.json`. The org is also wrong: the database has `symphony`, while `.env.j2` renders `DOCKER_INFLUXDB_INIT_ORG=darkstarllc`. Buckets present: `symphony` (30d), `_monitoring` (7d), `_tasks` (3d). Which side is authoritative is an open question — the repo copy is not automatically the correct one.

### Cameras
- Identify location for interior Tapo cam
- Install Tapo cam for galley/saloon
- Identify location for exterior Tapo cam
- Install exterior Tapo cam
