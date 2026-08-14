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
- Bring the second house battery into service — `A5:C2:37:40:01:46` sits
  disconnected with its terminals plugged while `A5:C2:37:3C:5C:90` carries the
  bank alone. Charge it to match before paralleling. Its state is already
  visible over Bluetooth, so no need to open anything to check on it.
  *(Parked here for transfer to Evernote.)*
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
  describe the Docker deploy meant to replace them. Docker is now installed
  (29.7.2, Compose v5.4.0, 2026-08-14), so the compose files can finally be
  exercised on the Pi. Migrate one service at a time rather than in one move:
  the four images come to roughly 2 GB against 6.5 GB free on the SD card, and
  anything mid-migration runs native and containerized at once.
- Rebuild boat computer
- Ansible for host provisioning — research and build out, decided 2026-08-13. The plan, scope boundaries and open decisions are written up in `reference/host_provisioning.md`; the repo question is settled (the SignalK/Ansible repo is `tkurki/marinepi-provisioning`, upstream and not ours — read its roles, don't push to it). Next step is the `clock` and `watchdog` roles, since `host/install.sh` already has those two fully described and they're the smallest honest slice.
- Set source priorities for position once the AIS is powered. The chartplotter and the AIS each carry their own GPS, so there will be two sources publishing `navigation.position` and SignalK will pick between them in arrival order. `~/.signalk/priorities.json` is `{}` today. The procedure is in `RUNBOOK.md` → "When the AIS is powered, there will be two GPS sources"; it can't be done in advance because N2K addresses are claimed dynamically and have to be read off the running bus.
- ~~Fork `signalk-fixed-position` to debounce its writes.~~ Considered and rejected 2026-08-13, keeping the note because the write rate is real and will get re-discovered. Measured: 20 rewrites in 20 one-second samples, roughly 86,000 disk writes a day. The plugin subscribes to `navigation.position` at a hardcoded 1000 ms period and calls `savePluginOptions` on every delta, so its stored fallback position is persisted at GPS rate. Its `interval` setting does not affect this. Note this cost did not exist until the N2K input was connected — with no real GPS there was nothing to persist. The plugin's behaviour is wanted, and the write rate does not justify forking it: at roughly 350 MB/day it is 3-9% of the box's ~10 GB/day total, so a fork would buy a few percent of SD life in exchange for maintaining a second fork forever. The count is what makes it sound alarming; the volume is what matters. Stays enabled. If it ever gets fixed, an upstream issue is the right route, not a fork.
- Get GPS time off the N2K bus instead of a serial receiver that isn't there. `126992` System Time and `129029` GNSS Position Data both carry it, and chrony's current `GPS` refclock has never received a sample because it is fed from `gpsd`, which has no device. Depends on the N2K input item above. Doesn't remove the case for an RTC — a GNSS clock needs a fix and the bus powered, so it doesn't cover a cold offline boot.
- Fit a DS3231 RTC to the boat Pi. It has no real-time clock, so the box boots with a wrong clock and stays wrong whenever it's offline — which breaks TLS validity, OIDC token windows and every timestamp written to InfluxDB. The PiCAN-M exposes a Qwiic (I2C) connector, and `dtoverlay=i2c-rtc,ds3231` plus a udev rule is the whole software side (`tkurki/marinepi-provisioning` role `rtc` has it). Cheap, independent of the GNSS question, and it makes the offline case survivable rather than merely detectable.
- Decide what the boat computer boots from. The 32 GB SD card is 74% full (7.2 GB free) while holding the OS, SignalK's state, the InfluxDB store and Grafana's database, and InfluxDB retention work will only add to that. Measured write volume on 2026-08-13, after the N2K input was connected: **about 10.7 GB/day**, taken from the kernel's since-boot counter (2,062 MB of sectors written over 4h36m of uptime) rather than a spot sample; a 60-second sample the same evening read 4 GB/day, so it is bursty around that average. An earlier note here recorded 14.5 GB/day steady with a 270 GB/day burst — disregard the burst, which came from misreading `/proc/diskstats` and is arithmetically impossible against a ~2 GB lifetime counter. Connecting the GPS is what raised it: SignalK now feeds position, SOG, COG and the whole gnss subtree into InfluxDB continuously. Worth measuring properly over a day before spending, and worth asking separately whether everything now being written needs to be. **A USB SSD was considered and is not recommended.** The argument for it was that it survives unclean power loss better, this boat's real failure mode since the Pi is powered from the N2K bus with no buffer. That argument doesn't hold: consumer SSDs carry volatile write caches and power-loss protection is an enterprise feature, so on a sudden power cut a cheap SSD can lose more than a small simple card does. Add the extra cable and connector in a damp vibrating space, the draw on the same bus supply, and USB-SATA bridge quirks on the Pi 4, and it buys endurance the boat doesn't obviously need — 10.7 GB/day is about 3.9 TB/year, inside a high-endurance card's rated life.

What to do instead, in order: **(1) reduce the writes**, which helps on any medium and costs nothing — the read-only root item below, a journald cap, debouncing `signalk-fixed-position`, and InfluxDB retention or downsampling now that the GPS is feeding it continuously. **(2) Fix the power problem at the power layer, not the storage layer** — an orderly shutdown on power loss is what actually protects the filesystem, and it's exactly what the HALPI2's RP2040 and its energy store provide. **(3) When the card does need replacing** — it's 74% full — swap it for a high-endurance card (Samsung PRO Endurance, SanDisk Max Endurance) rather than a merely bigger one, which buys wear-levelling headroom and nothing else.

**The HALPI2 is orderable**, which makes it the answer rather than a someday. 8 GB / 512 GB SSD at $614.35, in cart without issue on 2026-08-13. It ends this decision outright: an SSD instead of an SD card, and an RP2040 with an energy store that performs an orderly shutdown on power loss — which is the failure this boat actually has and the one no choice of card or drive fixes. Spending on interim storage for the Pi 4B only makes sense if the HALPI2 is being deferred for its own reasons.
- Evaluate a read-only root filesystem for the boat Pi. The SD card holds the OS, SignalK's state, the InfluxDB store and Grafana's database on one partition and is the component most likely to fail first; overlayfs root-ro is the standard mitigation and `tkurki/marinepi-provisioning` has a `root-ro` role. It's a real change to how the box gets worked on — every write becomes deliberate — so it's a decision, not a config toggle.
- Watch the first few unattended-upgrades runs. Enabled 2026-08-13 — the package is installed, `20auto-upgrades` and a boat-specific `52unattended-upgrades-boat` are both managed by `host/install.sh`, and a dry run applied cleanly. It takes Debian security updates only, never reboots on its own, and blacklists `nodejs`, `signalk-server`, `bluez`, the kernel and `openplotter-*` — the packages whose upgrades have actually broken this boat. What's left is confirming it behaves over a few cycles: `journalctl -u unattended-upgrades` and `/var/log/unattended-upgrades/`. Mail reporting is configured but goes nowhere until the box can send mail at all.
- Confirm the off-boat heartbeat actually alerts. Armed 2026-08-13 — `/etc/boat-heartbeat.url` holds a healthchecks.io ping URL (0600 root, deliberately not in this repo), the timer fires every five minutes and the first pings logged `ping ok`. What hasn't been proven is the half that matters: that a *missed* ping reaches Mark. Kill the timer for the grace period once and check the alert arrives, otherwise this is a monitor nobody has ever seen fire. Note the ping URL is a bearer credential — anyone holding it can send false 'alive' pings, which would mask a dead boat rather than leak anything; rotate it in healthchecks.io if it is ever exposed.
- Watch SignalK's memory. `signalk-server` measured 578 MB RSS at 17:16 on 2026-08-13 and 1,173 MB at 17:47 — roughly doubling in half an hour on the same boot, after the plugin tree was rebuilt. The box started swapping in that window (`pswpout` 0 → 8,700 pages) having done none since boot. Not acted on: available memory was still 1.2 GB, load was 0.7 and nothing had failed. It may simply be plugins warming up, but a process that grows like that on a 4 GB box is what starves the watchdog. A third reading at 17:52 was 1,148 MB, so it looks like plugins settling after the rebuild rather than a runaway leak — but it settled at twice where it started, on a box that has 4 GB for everything. Sampling every 20s between 17:46 and 17:49 confirms that read and sharpens it: RSS sawtooths, climbing to 1,229 MB and then dropping to 1,113 MB in a single interval before climbing again. A drop that size is V8 reclaiming, which is what distinguishes a large working set from a leak — a leak doesn't give memory back. `pswpout` did keep moving in that window though, 8,700 to 13,147, before going flat again; so the swapping is occasional rather than finished. Telegraf's `procstat` now records it per-service, so the trend is recoverable rather than needing to be re-measured by hand.
- Decide whether to cap journald on the Pi. It reached 639 MB on 2026-08-13, largely `user-1000` files fed by the pypilot crash loop, then self-rotated back to 192 MB. A `SystemMaxUse` cap would bound both the size and the SD-card writes, but the right number isn't obvious yet — deferred deliberately, not forgotten.
- A wedged BLE controller is invisible from off the boat, and only a reboot clears it. `RUNBOOK.md` → "A BLE sensor connects but never delivers data" establishes that nothing short of a reboot re-initialises the BCM4345C0, and nothing reboots this box on a schedule any more — deliberately, since the nightly reboot was covering for the v3d hang and risked landing on an `npm install`. So the house batteries can stop reporting and stay stopped until someone is aboard. The heartbeat payload is the natural place to surface it: add a line for whether `electrical.batteries` has updated recently, so silence in the data shows up in the same place as silence from the box.
- Configure or drop `signalk-solar-forecast` and `signalk-to-influxdb-v2-buffering`. Both are installed and enabled but throw on every server start — `solar-forecast` reading `.length` of undefined at `index.js:124`, `influxdb-v2-buffering` reading `.forEach` of undefined at `index.js:120`. Neither is a missing module; both are reading a config key that was never filled in. Each start since the 2026-08-13 rebuild has logged the pair. Filling them in means supplying a location and InfluxDB credentials, so it's a real decision, not a fix.
- Decide the nine major-version plugin upgrades. As of 2026-08-13 the boat is fully current *within* its declared semver ranges — `npm outdated` shows Current == Wanted for every package — so everything below is a deliberate major bump, not routine drift. Two are safety-of-navigation and want someone watching the boat when they land: `signalk-anchoralarm-plugin` 1.18.2 → 2.0.1 and `@signalk/signalk-autopilot` 1.7.0 → 2.6.0. Four are large webapps or flows: `@mxtommy/kip` 3.12.0 → 4.8.5, `@signalk/freeboard-sk` 2.24.2 → 3.1.0, `@signalk/signalk-node-red` 3.2.1 → 4.4.0, `signalk-tides` 1.5.0 → 2.1.2. The rest are small: `signalk-postgsail` 0.5.1 → 0.6.0 (broken anyway, see the better-sqlite3 item), `signalk-noaa-space-weather` 0.19.0 → 0.20.0 (Mark's own repo — coordinate with that dev work), `vhfinfo` 0.0.34 → 0.0.37. Note `signalk/package.json` already targets the newer major for kip, freeboard, autopilot, node-red, tides and postgsail, which reads as intent — but that file describes a different install than the boat's, so it isn't authority on its own.
- Bridge NMEA 2000 time to chrony, once SignalK is reading `can0`. PGN 126992 (System Time) is on the bus, so the boat has a GPS clock it can't use: the standard `refclock SHM` recipe reads gpsd's shared memory and gpsd has no serial device here. Something has to write a SHM segment from the N2K time, or feed chrony over the network. Until then the clock is internet-only and free-runs offline, on a box with no RTC — which is also what makes the DS3231 item worth doing regardless.
- Install BLE hub for lighting and related devices
- Set up real off-machine hosting (VPS or existing NAS) for Vaultwarden to hold the sops/age key backup, reachable privately (e.g. Tailscale) — currently only a local Docker proof-of-concept on the boat computer, which doesn't yet solve the single-point-of-failure risk for the key protecting `symphony.sops.yaml` / `signalk/security.json`
- Configure InfluxDB to receive data from SignalK, with appropriate data retention policies
- Revisit current InfluxDB org/bucket setup (org "darkstarllc", bucket "symphony") — consider alternatives using multiple buckets aboard Symphony
- Set up Grafana dashboards based on the public examples on GitHub from @meri-imperiumi
- Build a host-health dashboard for the boat computer. Telegraf now records everything needed and none of it is visible anywhere. These four queries were run against the live database on 2026-08-13 and return data, so the remaining work is panels, not discovery: `processes`/`blocked` (a non-zero value that doesn't come back down is a wedged task, the v3d signature), `rpi_health`/`under_voltage_since_boot` (latched — any 1 means the N2K bus sagged since boot), `chrony`/`last_offset` (clock drift; group away the `reference_id` tag or each NTP peer becomes its own series), and `internal_write`/`metrics_dropped` (non-zero means Telegraf is discarding, so gaps elsewhere are the monitor failing rather than the boat being quiet). Pair with `kernel`/`context_switches` and `mem`/`available` on the same time axis — the starvation signature is all three moving together.
- Deploy the repo's Grafana provisioning to the boat. `/etc/grafana/provisioning` on the Pi still holds only Debian's `sample.yaml` files, so none of the five dashboards in `grafana/provisioning/dashboards/json/` or the InfluxDB datasource definition are actually in use — the running Grafana was configured by hand. Either point the native install at the repo's provisioning directory or wait for the Docker deploy, but until then the golden config's dashboards are untested against real data.
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
