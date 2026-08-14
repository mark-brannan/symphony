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
- Resolve the orphaned `set-system-time` config. `signalk/plugin-config-data/set-system-time.json` is tracked with `"enabled": true` and `"sudo": true`, but `@signalk/set-system-time` is in neither `signalk/package.json` nor the Pi's tree — an enabled config for a plugin that doesn't exist. The repo and boat copies also disagree (`interval` 0 vs 60). chrony+gpsd was chosen over the plugin for the system clock, so this is probably a deletion; confirm before removing.
- Install BLE hub for lighting and related devices
- Set up real off-machine hosting (VPS or existing NAS) for Vaultwarden to hold the sops/age key backup, reachable privately (e.g. Tailscale) — currently only a local Docker proof-of-concept on the boat computer, which doesn't yet solve the single-point-of-failure risk for the key protecting `symphony.sops.yaml` / `signalk/security.json`
- Configure InfluxDB to receive data from SignalK, with appropriate data retention policies
- Revisit current InfluxDB org/bucket setup (org "darkstarllc", bucket "symphony") — consider alternatives using multiple buckets aboard Symphony
- Set up Grafana dashboards based on the public examples on GitHub from @meri-imperiumi
- Give an SSO login admin on SignalK. Every SSO login lands readonly and stays there; admin work still means the local `captain` password. The two routes are written up in `reference/software_stack.md` — have Dex synthesize a group from the email claim (Google only, no upstream change), or add an email list beside `adminGroups` upstream (covers both providers). GitHub orgs was considered and rejected.
- Decide whether InfluxDB and Grafana stay up. Both were stopped deliberately on 2026-08-11 to relieve memory and CPU pressure on the Pi, not by any fault of their own — but they were stopped without being disabled, so the 2026-08-13 reboot started them again and both are running now. Either disable them so the decision survives a reboot, or accept them up and close this out.
- Verify Grafana SSO end to end. Its OAuth config is live, but the browser login has never been exercised. `grafana-server` is running again as of the 2026-08-13 reboot, so nothing blocks the test.
- Decide whether two SSO user records is a problem. SignalK keys OIDC users on `sub` + issuer, so the same person arrives as a separate readonly user from each provider (`mark-brannan` via GitHub, `markbrannan@gmail.com` via Google). They can't be merged; both can be granted the same permission.
- Check whether `signalk-healthcheck` can actually send mail. Its config sets `sendEmail: true` with no SMTP host, user or password, so the alarms it raises on CPU, memory and disk thresholds may be going nowhere. It's the only outbound alert path on the boat.
- Delete `/etc/systemd/system/signalk.service.d/override.conf`. It has no `[Unit]` header, so systemd ignores it with "Assignment outside of section," and the unit it orders against (`socketcan-interface.service`) doesn't exist on the host anyway.
- Decide what to do about `@signalk/aisreporter`. It throws `Cannot read properties of undefined` continuously, its config isn't tracked in this repo, and what is on disk has rate settings but no MMSI or endpoint — never fully configured.
- Confirm the router's DNS overrides actually resolve locally. All four names answer with the boat IP today, but with the WAN up that can't be told apart from the router forwarding to Cloudflare. The real test is unplugging the WAN and running `nslookup signalk.symphony.dark-star-llc.com`.
- Decide whether `vncserver-x11-serviced` should stay. It's enabled but failed, and the desktop is already reachable over `rpi-connect`'s wayvnc, with Tailscale SSH covering everything else. The box is not headless — see `reference/compute_hardware.md` → Display — so this is about the redundant server, not about removing graphical access.
- Replace Telegraf's stopgap credential. It writes with `influxdb_captain_token` — captain's all-access token — because no scoped token could be minted while the store is out of sync. Once the reconciliation below is done, create a token scoped to write host metrics only, put it in sops, and point `TELEGRAF_INFLUX_TOKEN` at it in `.env.j2`. Consider a separate bucket with its own retention at the same time, so host metrics stop sharing `symphony` with vessel data.
- Fork `signalk-noaa-weather` and rewrite how it does notifications, or replace it. Disabled on the boat 2026-08-13 after it drove the Pi into a reboot loop. Its config takes a whole state (`notificationStates: "WA"`), polls every 60s, and raises every active NWS alert as a SignalK notification with `notificationSound: true` — so air-quality alerts for Spokane play sounds on a boat in Puget Sound. The notification pattern is the part worth redoing: alerts should be filtered by actual vessel position, and informational weather should not use the same alert path as a real alarm.
- Stop `signalk-healthcheck`'s memory alarm from feeding itself. It raises `host.memory.freeMemPercentage` with `method: ["visual","sound"]`, OpenPlotter plays that through VLC, and playing it consumes the memory the alarm is about. Under load the loop compounds. Either drop `sound` from the host-resource alarms or make OpenPlotter coalesce repeats — decide which layer owns it.
- Pin `bt-sensors-plugin-sk` so the fork survives an install. `~/.signalk/package.json` pins `^1.3.7`, and the fork at `/home/pi/bt-sensors-plugin-sk` is `1.3.8-beta10` — a prerelease, which does not satisfy that range. So the app store treats the symlink as a broken version and overwrites it with the registry copy; this happened twice on 2026-08-13 alone. Pin the prerelease explicitly, or point the dependency at the fork.
- Fix or drop `openplotter-i2c-read`. It crash-restarts about 15 times a minute — 305 restarts in one 33-minute boot on 2026-08-13. Each cycle is small, but it is constant churn against the SD card and the scheduler on a box that is already resource-starved.
- Decide what to do about `signalk-polar` and `signalk-postgsail`. Both depend on `better-sqlite3@7.6.2`, which cannot compile against Node 22 — see `reference/legacy_openplotter_stack.md`. Neither has worked on this box; `signalk-postgsail` is enabled in config and silently dead. Either pin a newer `better-sqlite3` via an npm override, or remove the plugins.
- Reconcile the InfluxDB secrets in `symphony.sops.yaml` against the running database. As of 2026-08-11 all three sops tokens (`influx_token`, `influxdb_operator_token`, `influxdb_signalk_token`) return 401; the only working credential is "captain's Token" (all-access), held in `signalk/plugin-config-data/signalk-to-influxdb2.json`. The org is also wrong: the database has `symphony`, while `.env.j2` renders `DOCKER_INFLUXDB_INIT_ORG=darkstarllc`. Buckets present: `symphony` (30d), `_monitoring` (7d), `_tasks` (3d). Which side is authoritative is an open question — the repo copy is not automatically the correct one.

### Cameras
- Identify location for interior Tapo cam
- Install Tapo cam for galley/saloon
- Identify location for exterior Tapo cam
- Install exterior Tapo cam
