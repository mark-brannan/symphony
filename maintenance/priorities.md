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
- BME680: settle which mechanism owns the sensor and get its data into the tree deliberately (needs boat access). Census 2026-08-14: the dedicated plugin `@oehoe83/signalk-raspberry-pi-bme680` is installed but disabled on both boxes, yet the boat receives 2 paths from source `OpenPlotter.I2C.BME680/688-1` — the legacy `openplotter-i2c-read` service. Identify those 2 paths and their units; the dormant airquality zones in `signalk/baseDeltas.json` assume the dedicated plugin's `environment.inside.airquality` 0–500 index and only fire if something publishes that path on that scale. Decide: enable the dedicated plugin, or keep the OpenPlotter service and re-point the zone meta at what it actually publishes.
- On the boat, remove the deprecated `@signalk/zones` plugin (installed 1.2.0, enabled, never registered) and mirror the airquality zone meta from `signalk/baseDeltas.json` into the boat's own baseDeltas — zones are server-core via `meta.zones` now, the plugin is only a broken editor UI. Fits the next maintenance window.
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
- Finish dockerizing the boat computer. Docker 29.7.2 / Compose v5.4.0 installed
  2026-08-14. **Dex is done** — running as a container, native unit disabled,
  verified through Caddy. SignalK, Grafana and Caddy are still native systemd
  services. Migrate one at a time, not in one move: the remaining images come to
  roughly 2 GB against ~6 GB free on the SD card, and anything mid-migration runs
  native and containerized at once. Caddy is the one to do carefully — it is the
  front door, so a bad move takes the SignalK UI, Grafana and the OIDC callback
  with it, including remote access to fix it. When Caddy does move, drop the
  transitional `127.0.0.1:5556` port publish from `compose-idp.yml`; Caddy will
  reach Dex by service name on `symphony-net` instead.
- Put fail2ban, or an equivalent rate limit, in front of sshd on the boat Pi.
  Measured 2026-08-14: `PasswordAuthentication yes`, `PermitRootLogin
  prohibit-password`, no fail2ban, and no host firewall — the INPUT policy is
  accept and only Tailscale's own chains exist. Zero failed password attempts
  in the previous 24 hours, so this is precautionary, not a response to
  anything. Port 22 answers on the boat LAN, on the Pi's own WPA-PSK access
  point (`SignalK`, wlan9, 10.42.0.1/24) and on the tailnet; nothing is
  exposed to the internet. The reason to do it anyway is an asymmetry of
  consequence. The router is consumer gear, so the wifi PSK is the most
  likely thing to give way, and someone who gets that far can either read
  SignalK — which is acceptable, and already true without a login — or get a
  shell on the box that runs everything, which is not. A shell is where a
  persistent backdoor lives, and it would outlast the wifi password that let
  it in. Password auth itself stays: it's the offline fallback when a keyed
  device is dead and the boat is far from anywhere, so rate-limiting is the
  right control here and keys-only is not.
- Rebuild boat computer
- Deploy `plugins/signalk-plugin-watchdog` to the boat Pi as a proof of concept — notify-only supervision for a plugin that's enabled but publishing no deltas (the bt-sensors D-Bus-death failure). Built, tested, and merged to main 2026-08-15 (recovered from a stray branch that never landed); design and verification are in `reference/signalk_plugin_watchdog.md` and `reference/monitoring_decisions.md` Role 4. Deployment itself (copy into `~/.signalk/node_modules/`, configure `expectPlugins: ["bt-sensors-plugin-sk"]`, restart, verify, then prove the failure path with the `flaky-plugin` test fixture) needs a session with actual reach to `symphony-pi` over Tailscale — this checkout's remote sandbox has no `ssh` client and no tailnet route. Steps are written up ready to run in the session prompt kept for this handoff.
- Ansible for host provisioning — research and build out, decided 2026-08-13. The plan, scope boundaries and open decisions are written up in `reference/host_provisioning.md`; the repo question is settled (the SignalK/Ansible repo is `tkurki/marinepi-provisioning`, upstream and not ours — read its roles, don't push to it). Next step is the `clock` and `watchdog` roles, since `host/install.sh` already has those two fully described and they're the smallest honest slice.
- Set source priorities for position once the AIS is powered. The chartplotter and the AIS each carry their own GPS, so there will be two sources publishing `navigation.position` and SignalK will pick between them in arrival order. `~/.signalk/priorities.json` is `{}` today. The procedure is in `RUNBOOK.md` → "When the AIS is powered, there will be two GPS sources"; it can't be done in advance because N2K addresses are claimed dynamically and have to be read off the running bus.
- Feed signalk-lint the rest of the rules this boat's failures earned. Batch 1 (config-only, no collector change) is written: bt-sensors scan starvation, alarm-path-dead, no-data-connections, fallback-is-primary. Batch 2 is host-level and needs collector work: `can0` UP with no NMEA2000 provider (stronger than the config-only version, since it proves the bus exists), `gpsd` naming a device that doesn't exist, a systemd drop-in with directives before any `[Section]` (systemd ignores it silently), a cron reboot with no npm-in-flight guard, a browser in autostart while every DRM output reads `disconnected`, no RTC combined with no synced NTP source, `RuntimeWatchdogUSec` disagreeing with `/sys/class/watchdog/watchdog0/timeout`, and journald with no `SystemMaxUse`. Each one is a fault this boat actually hit.
- Make "no rule may throw on malformed input" a stated convention in signalk-lint. A malformed connection entry crashed an entire lint run on 2026-08-14 — code already on main, not a new diff. A linter fails hardest on exactly the box that most needs it, because the machine with a broken config is the one being linted. Every rule wants a garbage-input fixture.
- Trim the RUNBOOK's remaining prose-heavy sections. Measured 2026-08-14 by prose-to-command line ratio: "SSO login (GitHub / Google)" 141:18, "Bringing up a host" 71:13, "Installing host files" 52:9, "When SignalK errors about missing packages" 39:8. The two sections with literally zero code blocks are already fixed. SSO is the worst but part of it is genuinely click-through in provider consoles with no command form, so trim rather than restructure. "Installing host files" is the better target — it has grown a paragraph per installed file, and most of that belongs in `reference/` under the file's own actions-only rule.
- ~~Fork `signalk-fixed-position` to debounce its writes.~~ Considered and rejected 2026-08-13, keeping the note because the write rate is real and will get re-discovered. Measured: 20 rewrites in 20 one-second samples, roughly 86,000 disk writes a day. The plugin subscribes to `navigation.position` at a hardcoded 1000 ms period and calls `savePluginOptions` on every delta, so its stored fallback position is persisted at GPS rate. Its `interval` setting does not affect this. Note this cost did not exist until the N2K input was connected — with no real GPS there was nothing to persist. The plugin's behaviour is wanted, and the write rate does not justify forking it: at roughly 350 MB/day it is 3-9% of the box's ~10 GB/day total, so a fork would buy a few percent of SD life in exchange for maintaining a second fork forever. The count is what makes it sound alarming; the volume is what matters. Stays enabled. If it ever gets fixed, an upstream issue is the right route, not a fork.
- Get GPS time off the N2K bus instead of a serial receiver that isn't there. `126992` System Time and `129029` GNSS Position Data both carry it, and chrony's current `GPS` refclock has never received a sample because it is fed from `gpsd`, which has no device. Depends on the N2K input item above. Doesn't remove the case for an RTC — a GNSS clock needs a fix and the bus powered, so it doesn't cover a cold offline boot.
- Fit a DS3231 RTC to the boat Pi. It has no real-time clock, so the box boots with a wrong clock and stays wrong whenever it's offline — which breaks TLS validity, OIDC token windows and every timestamp written to InfluxDB. The PiCAN-M exposes a Qwiic (I2C) connector, and `dtoverlay=i2c-rtc,ds3231` plus a udev rule is the whole software side (`tkurki/marinepi-provisioning` role `rtc` has it). Cheap, independent of the GNSS question, and it makes the offline case survivable rather than merely detectable.
- ~~Census the dev container's SignalK install.~~ Done 2026-08-14,
  `census-container.json`. Two results settled, everything else from that pass
  was inconclusive and deliberately not written down.
  **Container-side orphans: none.** All four candidates resolve. `signalk-noaa-sonar-charts`
  and `@signalk/vedirect-serial-usb` are already in `signalk/package.json` under
  their package names rather than their plugin ids; `@signalk/course-provider`
  and `@signalk/app-dock` ship inside `signalk-server` itself. Nothing to install
  and nothing to add — declaring a bundled package would pin a version against
  the one the server already carries. Note the id-vs-package trap for whoever
  compares these files next: a config is named for the plugin id, the manifest
  for the npm package, and they differ often enough to manufacture phantom
  orphans in both directions.
  **Webapp-load counts do not measure people.** Eight webapps sit at exactly 12,
  and `signalk-doctor`/`signalk-questdb`/`signalk-container`/`signalk-crows-nest`
  are hit together in fixed ratios at repeating intervals. Something enumerates
  them; a high count is not evidence of use. The column is still useful as
  positive evidence for a *single* webapp with an irregular burst, and useless
  for ranking.
- **Dev-container plugin configs are a workbench, not state, until the
  first-pass evaluation lands.** A session was started 2026-08-14 to actually
  use the installed plugins — opening webapps, filling in configs, enabling and
  disabling things to see what they do — and to write up
  `intermediate_files/plugin-first-pass.md` for Mark to read before any of it
  is committed. Until that report exists, do not diff, sync or reconcile the
  container's `plugin-config-data` against the boat or the repo: churn there is
  someone experimenting, not intent. `census-container.json` is the snapshot
  taken before that began, so use it rather than the live container.
- Evaluate the parked plugins on the dev container. These were installed on
  purpose to be tried and then never got the time — they are **not** broken
  candidates for removal, and reading them as idle is the mistake to avoid.
  **Reconciliation rule while this stays open: a parked plugin is not drift.**
  Don't install one on the boat because the dev box has it, don't remove one
  from the dev box because the boat doesn't, and don't file the difference as
  something to fix. Unevaluated software does not belong on the boat, and the
  dev box is exactly where it should sit until Mark has judged it — so the two
  installs are *expected* to differ here, and that difference is not a defect.
  A census can't tell this category from a fault, because both look like
  "enabled, configured, publishing nothing." Only Mark knows which is which,
  so the state below is measurement to start from, not a verdict:
  - `open-meteo` — **works today, nothing blocking it.** Serves SignalK's v2
    weather API via `registerWeatherProvider`, so publishing zero paths is
    correct rather than idle. `GET /signalk/v2/api/weather/observations?lat=&lon=`
    returned live, sane, correctly-united data on 2026-08-14. The API key is
    optional and buys premium content only (the plugin's own README), so the
    empty `apiKey` in its config is not the blocker it looks like.
  - `signalk-questdb` — enabled, and QuestDB holds zero tables. Configured with
    `questdbHost: 127.0.0.1`, which from inside the SignalK container addresses
    that container rather than QuestDB, and the two aren't on a shared network
    anyway (`sk-signalk-questdb` on `symphony-net`, `signalk-server` on
    `symphony_symphony-net`). So it has never written a row. Whether that's
    worth fixing depends on what it's wanted for; note it would be a second
    time-series store beside InfluxDB, which is a real cost on the Pi but not
    on the dev box.
  - `signalk-doctor`, `signalk-container`, `signalk-crows-nest` — installed,
    unevaluated. Their webapp-load counts are the enumeration artifact above,
    not use. `signalk-questdb` sets `managedContainer: true`, so there is some
    relationship between it and `signalk-container` that nobody has traced.
- **Answering the census's question 2 — "which of the 15 container-only plugins
  are earning their place" — cannot be done from the container**, and the
  attempt is what produced today's wrong verdicts. Webapp loads don't rank (see
  the enumeration artifact above), and "publishes nothing" is correct behaviour
  for every webapp, exporter, provider and actor among them. What the census
  does settle, and all it settles:
  - `signalk-rpi-stats` publishes 29 paths. It demonstrably works.
  - `signalk-marinetraffic-public`, `signalk-mob-notifier` and
    `signalk-basic-tide-widgets` have never been configured (`configured_values:
    false`), so they have had no chance to do anything either way.
  - One unexplained thing: `marinetraffic-public` reads unconfigured, yet
    `marinetraffic.XX` publishes one path and shows in `unattributed_sources`.
    Nobody has traced it. Flagged, not resolved.
  - Everything else on that list is the parked category above — a question for
    Mark, not a measurement.
- **Retire `signalk-healthcheck`'s host section; keep its provider watch.**
  Correcting this entry, which previously said the plugin was removed on
  2026-08-14 and asked whether to reinstate it. Verified on the boat: it was
  never removed. The package is installed and the config reads
  `"enabled": true`. What happened on 2026-08-14 was a reconfigure — a POST to
  its config endpoint at 15:35 stopped the `Could not get statisics for
  OpenPlotter GPSD` line it had been logging every 60 seconds until 11:47.
  - It has been raising nothing and sending nothing the whole time. Both
    `sendNotification` and `sendEmail` are `false` in its config, on the boat
    and in the repo copy.
  - Its host CPU/memory/disk section duplicates thresholds
    `host/boat-heartbeat` already alarms on, and duplicates them worse: no
    history, thresholds invisible in the UI, a second polling process on a
    memory-constrained box.
  - Its provider section is the exception and the reason to keep the plugin.
    It reads `pipedProviders` from the server settings and watches each one's
    delta rate, which is the only mechanism aboard that alarms on data
    *stopping* rather than on a value going bad. The boat has one provider,
    `n2k-can0`, and the watch for it is currently `"enabled": false`.
  - The onboard host alarm it was being considered for is better served by
    zone metadata, which the server core already turns into notifications —
    see `reference/monitoring_posture.md`. Note the threshold has to be
    derived from `signalk-rpi-monitor`'s own formula rather than copied from
    the heartbeat's 400 MB.
  Per-role ownership is settled in `reference/monitoring_decisions.md`.
  **Done on the boat 2026-08-14**: host section disabled, `n2k-can0`
  provider-staleness watch enabled with `sendNotification: true`. The
  repo's tracked copy of this plugin's config was deleted from git in a
  past commit (b8b4cc2) along with its `.gitattributes` sops rule for the
  mail password field — restoring it to git needs that rewired first
  (`scripts/add_inplace_secret.sh` or equivalent), so the settled config
  exists on disk, untracked, rather than committed.
- Fix `better-sqlite3` so `signalk-polar` can run. It is stuck at 7.6.2, which
  does not build on Node 22 — the release predates the removal of
  `v8::AccessorSignature` and `v8::Object::CreationContext`, so compilation
  fails and no `.node` artifact exists. `signalk-polar` is the only thing on the
  boat that needs it; **postgsail does not**, contrary to what this file and the
  log said before 2026-08-14. The fix is a newer better-sqlite3, but polar pins
  `^7.6.2`, so it needs either an upstream bump or an override — decide which
  before installing anything, and remember npm rolls the whole tree back on a
  build failure here.
- Confirm PostgSail is actually receiving. The plugin is enabled and configured
  against the hosted `api.openplotter.cloud`, which answers 200 from the boat,
  but the only evidence visible from this side is an hourly "removing metrics
  from buffer" line, which is the plugin finding nothing to delete rather than a
  failure. Checking whether voyages are landing needs Mark's PostgSail account.
  If it is working, the saillogger question mostly answers itself: postgsail is
  free and already running, saillogger is $7.99/month.
- Boat-side orphan configs, re-derived 2026-08-14 the only way that works:
  **ask the server which plugin ids it actually loaded** (`/skServer/plugins`),
  rather than inferring from package names or config filenames. Four are real —
  `signalk-fixedstation`, `signalk-saillogger`, `signalk-tide-watch`,
  `signalk-to-influxdb` — and `signalk-saillogger` is the odd one, enabled with
  no plugin behind it. Deliberately not removed: per the parked rule, a config
  without a plugin may be something Mark installed to try and later uninstalled,
  and the config is the only record of how it was set up.
  Both earlier counts were wrong and neither method should be reused. Matching
  config filenames against `signalk/package.json` undercounts, because that file
  is keyed by npm package name while configs are named for plugin id. Deriving
  ids by scanning installed packages overcounts — it returned 13 here, 9 of them
  false, including `charts`, `derived-data` and `venus`, all of which are loaded
  and working. The server is the only source that knows.
- `signalk/security.json` in the repo is the dev container's, not the boat's,
  which is the same two-live-installs case as the configs above. Compared
  2026-08-14 against `~/.signalk/security.json` on the Pi: `secretKey` and the
  `captain` password hash both differ, and the repo carries a `screenshots`
  user and a `claude-dev-tools` device the boat has never had. So copying
  either file over the other is not a sync — it invalidates every token
  SignalK has issued and changes the captain password on whichever box
  receives it. One difference is a real question rather than drift:
  `mark-brannan` is `admin` in the repo and `readonly` on the boat, the same
  permission the "Give an SSO login admin" item below is about. Decide per
  field, and note the union rule doesn't apply to `secretKey` — there is no
  superset of two signing keys.
- Add a weather term to `ACTOR_HINTS` in `scripts/signalk_plugin_census.py`.
  `open-meteo` is an actor by the script's own definition — its product is a
  registered v2 API, not published paths — but the hint list has no weather
  entry, so it scores `unmatched` and reads like a fault. Any other provider
  plugin will land the same way.
- **Do not touch the `captain` credentials.** `signalk_captain_password` and
  `influxdb_captain_password` in `secrets/symphony.sops.yaml` are frozen at
  Mark's instruction until his own hardening pass, which is scheduled work and
  not something a session should get ahead of. Do not rotate them, do not split
  them, do not "helpfully" strengthen them, and do not offer to — the offer
  itself is the thing he asked to stop, because it recurs in every session that
  reads this file. He knows their current state and has decided when it changes.
  `scripts/lint_repo_hygiene.py` fails the commit if a diff touches them, since
  prose in this file is context and not a constraint.
- Boat Pi UTF-8 locale — host fix done 2026-08-15 (see `log.md`); layer 3
  (running processes) needs a deliberate reboot. Decided 2026-08-15: waiting
  for natural convergence won't work. The 58 stale processes are the desktop
  stack (lightdm, wayfire, gvfs, pipewire), pypilot's 9 processes, pigpiod,
  tailscaled and PID 1 itself — none of which restart on their own, so the
  count sits where it is until the box comes up again. Newly started services
  are already fine: `systemctl show-environment` carries `LANG=en_US.UTF-8`
  and `PYTHONUTF8=1`, so anything spawned from here inherits the right
  environment, and the Python exposure that motivated the fix (pypilot,
  openplotter-notifications) clears on the same reboot.
  Blocked on a reboot window, not on the decision: as of 2026-08-15 another
  session is mid-deploy of `signalk-plugin-watchdog` with a two-restart
  failure-path test to run (~11 min settle each), and the resident session on
  the Pi is mid npm-upgrade. Reboot once both are clear, then re-run
  `python3 scripts/check_encoding_health.py` on the box to confirm layer 3.
- Decide what to do about Chromium on the boat Pi. Its profile under
  `~/.config/chromium` is 1.9 GB — 692 MB of extensions across 23 of them, 335 MB
  of service workers, 231 MB of File System storage — and it is the single
  largest reclaimable thing left on the card. It was last used 2026-08-13 and
  isn't running. `apt autoremove` wanted to remove the package outright on
  2026-08-14 and was deliberately held back with `apt-mark manual`, along with
  its codecs, because that's a decision. Three options: leave it, clear the
  caches and service workers only (roughly 570 MB, keeps logins), or remove the
  browser and the profile. Note removing the package does not delete the
  profile. Related: the autostart browser is pointed at a display whose DRM
  outputs all read `disconnected`.
- Bring `~/.openplotter/openplotter.conf` under version control, or decide
  deliberately not to. Its `soundignore` key is now load-bearing — it's what
  keeps OpenPlotter from spawning a `cvlc` per notification, the process storm
  behind the 08-13 watchdog resets — and it lives only on the boat, set by hand,
  backed up to a `.bak-` file beside it. The OpenPlotter GUI rewrites this file,
  so anything tracking it has to survive being overwritten out from under the
  repo. Same argument as the heartbeat config, which is already tracked.
- Decide what the boat computer boots from. The 32 GB SD card is 67% full (9.2 GB free, after the 2026-08-14 cleanup reclaimed 3.3 GB) while holding the OS, SignalK's state, the InfluxDB store and Grafana's database, and InfluxDB retention work will only add to that. Measured write volume on 2026-08-13, after the N2K input was connected: **about 10.7 GB/day**, taken from the kernel's since-boot counter (2,062 MB of sectors written over 4h36m of uptime) rather than a spot sample; a 60-second sample the same evening read 4 GB/day, so it is bursty around that average. An earlier note here recorded 14.5 GB/day steady with a 270 GB/day burst — disregard the burst, which came from misreading `/proc/diskstats` and is arithmetically impossible against a ~2 GB lifetime counter. Connecting the GPS is what raised it: SignalK now feeds position, SOG, COG and the whole gnss subtree into InfluxDB continuously. Worth measuring properly over a day before spending, and worth asking separately whether everything now being written needs to be. **A USB SSD was considered and is not recommended.** The argument for it was that it survives unclean power loss better, this boat's real failure mode since the Pi is powered from the N2K bus with no buffer. That argument doesn't hold: consumer SSDs carry volatile write caches and power-loss protection is an enterprise feature, so on a sudden power cut a cheap SSD can lose more than a small simple card does. Add the extra cable and connector in a damp vibrating space, the draw on the same bus supply, and USB-SATA bridge quirks on the Pi 4, and it buys endurance the boat doesn't obviously need — 10.7 GB/day is about 3.9 TB/year, inside a high-endurance card's rated life.

What to do instead, in order: **(1) reduce the writes**, which helps on any medium and costs nothing — the read-only root item below, a journald cap, debouncing `signalk-fixed-position`, and InfluxDB retention or downsampling now that the GPS is feeding it continuously. **(2) Fix the power problem at the power layer, not the storage layer** — an orderly shutdown on power loss is what actually protects the filesystem, and it's exactly what the HALPI2's RP2040 and its energy store provide. **(3) When the card does need replacing** — it's 67% full — swap it for a high-endurance card (Samsung PRO Endurance, SanDisk Max Endurance) rather than a merely bigger one, which buys wear-levelling headroom and nothing else.

**The HALPI2 is orderable**, which makes it the answer rather than a someday. 8 GB / 512 GB SSD at $614.35, in cart without issue on 2026-08-13. It ends this decision outright: an SSD instead of an SD card, and an RP2040 with an energy store that performs an orderly shutdown on power loss — which is the failure this boat actually has and the one no choice of card or drive fixes. Spending on interim storage for the Pi 4B only makes sense if the HALPI2 is being deferred for its own reasons.
- Evaluate a read-only root filesystem for the boat Pi. The SD card holds the OS, SignalK's state, the InfluxDB store and Grafana's database on one partition and is the component most likely to fail first; overlayfs root-ro is the standard mitigation and `tkurki/marinepi-provisioning` has a `root-ro` role. It's a real change to how the box gets worked on — every write becomes deliberate — so it's a decision, not a config toggle.
- Watch the first few unattended-upgrades runs. Enabled 2026-08-13 — the package is installed, `20auto-upgrades` and a boat-specific `52unattended-upgrades-boat` are both managed by `host/install.sh`, and a dry run applied cleanly. It takes Debian security updates only, never reboots on its own, and blacklists `nodejs`, `signalk-server`, `bluez`, the kernel and `openplotter-*` — the packages whose upgrades have actually broken this boat. What's left is confirming it behaves over a few cycles: `journalctl -u unattended-upgrades` and `/var/log/unattended-upgrades/`. Mail reporting is configured but goes nowhere until the box can send mail at all.
- Add data-source staleness to the heartbeat payload. This is the one thing `signalk-healthcheck` did that nothing else does, and it was the gap that let `signalk-fixed-position` pass for a real GPS for months: the box is healthy, the data is dead, and every liveness check says fine. Carry the age of `navigation.position` and of the house battery readings in the ping, so silence in the data shows up in the same place as silence from the box. The plugin is still installed and enabled, but it wasn't delivering this either: it was watching an "OpenPlotter GPSD" provider that doesn't exist, and both its notification and email flags are off.
- Heartbeat fails-silent escalation. When pings to hc-ping.com fail repeatedly
  while the uplink is otherwise up, `host/boat-heartbeat` should POST directly
  to the Pushover API — "your monitoring is down" — since healthchecks.io can't
  report its own outage. Decided in `reference/monitoring_decisions.md`, Role 1.
  **Failed systemd units now trip `/fail`, done and deployed 2026-08-14** — it
  was already riding along in the ping body unread; now it's in the same
  reasons/debounce path as the memory and disk checks. **Healthchecks.io's
  weekly report email is on, Mark confirmed 2026-08-14.** **The direct
  Pushover POST and the soft warning tier (thresholds shy of the alarm ones —
  disk ≥80%, memory <600MB — a low-priority buzz, never `/fail`) are both
  written into `host/boat-heartbeat` and tested 2026-08-14** against a local
  mock server, gated behind an uplink-up probe (a raw-IP request to
  Cloudflare's resolver, so DNS being down doesn't read as an escalation) and
  debounced to one Pushover message per outage/crossing rather than one per
  5-minute cycle. **Deployed and live-tested 2026-08-14**: `pushover_api_token`/
  `pushover_user_key` are in `host/boat-heartbeat.json` (in-place-encrypted,
  same pattern as `url`), installed on the boat via `host/install.sh`, and
  the escalation path fired for real — pointed `/etc/boat-heartbeat.json` at
  a bad URL, ran the service 3x, got the "Symphony monitoring is down"
  Pushover message, restored the real URL. Soft warning tier is untested live
  (real mem/disk aren't in the warn band to trigger it) but covered by the
  same mock-server pass as the escalation logic.
- Host-metrics collectors: keep two, delete two — decided 2026-08-14, done
  2026-08-14. Telegraf stays the history source. `signalk-rpi-monitor` stays
  too, now with the job it didn't have before: warn/alarm zones on
  `environment.rpi.memory.utilisation` (normal <0.84, warn 0.84–0.89, alarm
  >0.89), set via `PUT .../meta/zones` as `captain` on both boat and dev and
  confirmed live on each afterward. Checked both boxes' Grafana dashboards
  for `environment.rpi.*` panels first — none of the 5 provisioned
  dashboards (same set on boat and dev) reference `rpi` anywhere, checked at
  the file level on both and also live via the Grafana API on dev (`captain`
  authenticates there; the boat's Grafana rejects that password, so the boat
  side is file-level only — a UI-added panel wouldn't show up in that check).
  `signalk-rpi-uptime` disabled on the boat, `signalk-rpi-stats` disabled on
  the dev container, `signalk-server` restarted on each and both confirmed
  back up with the plugin off. Per `reference/monitoring_decisions.md` Role 3.
- Phone and audible delivery for vessel alarms — build it; shape decided
  2026-08-14. The
  notification bus raises alarms fine; delivery is the gap, owner-confirmed
  2026-08-14: Mark's phone is Android, WilhelmSK is iOS-only on an
  occasionally-aboard iPad, and no speaker is wired to the Pi, so
  notification-player plays to nothing. Likely shape:
  `signalk-pushover-notification-relay` (2022, unmaintained — audit on
  install; a Node-RED flow is the fallback) to Pushover on the Android as the
  primary path. Open: whether any Android-native SignalK alarm app exists.
  Note nothing installed can reach a phone with the internet down — Pushover,
  SNS and healthchecks all need cloud. A self-hosted ntfy server on the Pi +
  `signalk-ntfy` + the ntfy Android app delivers over boat WiFi with no
  internet.
  **ntfy server done 2026-08-14, both places** — up and verified (round-tripped
  a test message) on the boat Pi (`localhost:8090`) and the dev docker stack
  (`compose-ntfy.yml`, service name `ntfy` on `symphony-net`). `signalk-ntfy`
  **installed and delivering in both places 2026-08-15**, topic
  `symphony-alarms` — dev container against `http://ntfy:80`, boat Pi against
  `http://localhost:8090`, configs otherwise identical. Proven end to end on
  the boat: real alerts landed on the topic within two minutes of restart.
  Remaining: subscribe the phone (below), which needs the Pi's tailnet or LAN
  address rather than `localhost`.
  `signalk-pushover-notification-relay` not installed. The credential
  blocker is gone — `pushover_api_token`/`pushover_user_key` landed in
  `secrets/symphony.sops.yaml` 2026-08-14 for the heartbeat escalation above
  and are the same values this plugin needs — but the install (and the
  unmaintained-plugin audit) hasn't been done.
  Installing the Android ntfy app and subscribing to `symphony-alarms` on
  each server is Mark's phone-side step, tracked separately, not a blocker
  for anything above. Decided: do ntfy *and* a speaker, deliberately redundant — two
  independent wake-ups aboard is what you want when dragging anchor onto a
  lee shore at night, and both pieces are cheap. The speaker (or piezo)
  purchase and wiring is filed in Evernote (2026-08-14, "Symphony Important
  Tasks") — the GPIO
  beeper plugin is already installed, disabled, awaiting hardware. Per
  `reference/monitoring_decisions.md` Role 2, as amended.
- Watch SignalK's memory. `signalk-server` measured 578 MB RSS at 17:16 on 2026-08-13 and 1,173 MB at 17:47 — roughly doubling in half an hour on the same boot, after the plugin tree was rebuilt. The box started swapping in that window (`pswpout` 0 → 8,700 pages) having done none since boot. Not acted on: available memory was still 1.2 GB, load was 0.7 and nothing had failed. It may simply be plugins warming up, but a process that grows like that on a 4 GB box is what starves the watchdog. A third reading at 17:52 was 1,148 MB, so it looks like plugins settling after the rebuild rather than a runaway leak — but it settled at twice where it started, on a box that has 4 GB for everything. Sampling every 20s between 17:46 and 17:49 confirms that read and sharpens it: RSS sawtooths, climbing to 1,229 MB and then dropping to 1,113 MB in a single interval before climbing again. A drop that size is V8 reclaiming, which is what distinguishes a large working set from a leak — a leak doesn't give memory back. `pswpout` did keep moving in that window though, 8,700 to 13,147, before going flat again; so the swapping is occasional rather than finished. Telegraf's `procstat` now records it per-service, so the trend is recoverable rather than needing to be re-measured by hand.
- Decide whether to cap journald on the Pi. It reached 639 MB on 2026-08-13, largely `user-1000` files fed by the pypilot crash loop, then self-rotated back to 192 MB. A `SystemMaxUse` cap would bound both the size and the SD-card writes, but the right number isn't obvious yet — deferred deliberately, not forgotten.
- A wedged BLE controller is invisible from off the boat, and only a reboot clears it. `RUNBOOK.md` → "A BLE sensor connects but never delivers data" establishes that nothing short of a reboot re-initialises the BCM4345C0, and nothing reboots this box on a schedule any more — deliberately, since the nightly reboot was covering for the v3d hang and risked landing on an `npm install`. So the house batteries can stop reporting and stay stopped until someone is aboard. The heartbeat payload is the natural place to surface it: add a line for whether `electrical.batteries` has updated recently, so silence in the data shows up in the same place as silence from the box.
- Configure or drop `signalk-solar-forecast` and `signalk-to-influxdb-v2-buffering`. Both are installed and enabled but throw on every server start — `solar-forecast` reading `.length` of undefined at `index.js:124`, `influxdb-v2-buffering` reading `.forEach` of undefined at `index.js:120`. Neither is a missing module; both are reading a config key that was never filled in. Each start since the 2026-08-13 rebuild has logged the pair. Filling them in means supplying a location and InfluxDB credentials, so it's a real decision, not a fix.
- Decide the nine major-version plugin upgrades. As of 2026-08-13 the boat is fully current *within* its declared semver ranges — `npm outdated` shows Current == Wanted for every package — so everything below is a deliberate major bump, not routine drift. Two are safety-of-navigation and want someone watching the boat when they land: `signalk-anchoralarm-plugin` 1.18.2 → 2.0.1 and `@signalk/signalk-autopilot` 1.7.0 → 2.6.0. Four are large webapps or flows: `@mxtommy/kip` 3.12.0 → 4.8.5, `@signalk/freeboard-sk` 2.24.2 → 3.1.0, `@signalk/signalk-node-red` 3.2.1 → 4.4.0, `signalk-tides` 1.5.0 → 2.1.2. The rest are small: `signalk-postgsail` 0.5.1 → 0.6.0 (broken anyway, see the better-sqlite3 item), `signalk-noaa-space-weather` 0.19.0 → 0.20.0 (Mark's own repo — coordinate with that dev work), `vhfinfo` 0.0.34 → 0.0.37. Note `signalk/package.json` already targets the newer major for kip, freeboard, autopilot, node-red, tides and postgsail, which reads as intent — but that file describes a different install than the boat's, so it isn't authority on its own.
- Bridge NMEA 2000 time to chrony, once SignalK is reading `can0`. PGN 126992 (System Time) is on the bus, so the boat has a GPS clock it can't use: the standard `refclock SHM` recipe reads gpsd's shared memory and gpsd has no serial device here. Something has to write a SHM segment from the N2K time, or feed chrony over the network. Until then the clock is internet-only and free-runs offline, on a box with no RTC — which is also what makes the DS3231 item worth doing regardless.
- Install BLE hub for lighting and related devices
- Set up real off-machine hosting (VPS or existing NAS) for Vaultwarden to hold the sops/age key backup, reachable privately (e.g. Tailscale) — currently only a local Docker proof-of-concept on the boat computer, which doesn't yet solve the single-point-of-failure risk for the key protecting `symphony.sops.yaml` / `signalk/security.json`. The compose file that settled the hosting shape is in `vaultwarden/` in this repo, and this repo is public; Mark expects to use the vault for things that aren't Symphony, so the files want a private repo of their own before the VPS is built. Plain `git rm` when that happens, not a history rewrite — nothing secret is in them.
- Configure InfluxDB to receive data from SignalK, with appropriate data retention policies
- Revisit current InfluxDB org/bucket setup (org "darkstarllc", bucket "symphony") — consider alternatives using multiple buckets aboard Symphony
- Set up Grafana dashboards based on the public examples on GitHub from @meri-imperiumi
- Build a host-health dashboard for the boat computer. Telegraf now records everything needed and none of it is visible anywhere. These four queries were run against the live database on 2026-08-13 and return data, so the remaining work is panels, not discovery: `processes`/`blocked` (a non-zero value that doesn't come back down is a wedged task, the v3d signature), `rpi_health`/`under_voltage_since_boot` (latched — any 1 means the N2K bus sagged since boot), `chrony`/`last_offset` (clock drift; group away the `reference_id` tag or each NTP peer becomes its own series), and `internal_write`/`metrics_dropped` (non-zero means Telegraf is discarding, so gaps elsewhere are the monitor failing rather than the boat being quiet). Pair with `kernel`/`context_switches` and `mem`/`available` on the same time axis — the starvation signature is all three moving together.
- Deploy the repo's Grafana provisioning to the boat. `/etc/grafana/provisioning` on the Pi still holds only Debian's `sample.yaml` files, so none of the five dashboards in `grafana/provisioning/dashboards/json/` or the InfluxDB datasource definition are actually in use — the running Grafana was configured by hand. Either point the native install at the repo's provisioning directory or wait for the Docker deploy, but until then the golden config's dashboards are untested against real data.
- Decide whether to make the InfluxDB/Grafana stop stick across a reboot. Settled 2026-08-13: SignalK, InfluxDB, Grafana, Caddy, Dex and Telegraf are all expected to run and stay enabled, and all six are enabled and active as of that date. InfluxDB and Grafana are the release valve — anyone may `systemctl stop` them to recover roughly 600 MB under real memory pressure, without asking, but must not disable them, so a reboot brings them back. Real pressure means swap activity or available memory under ~400 MB, not a high load average on its own; check `free -m` and `grep ^pswp /proc/vmstat` first, and say so in-session when you stop one. Whether that should instead become a permanent disable is Mark's call and the only part still open.
- Verify Grafana SSO end to end. Its OAuth config is live, but the browser login has never been exercised. `grafana-server` is running again as of the 2026-08-13 reboot, so nothing blocks the test.
- Decide whether two SSO user records is a problem. SignalK keys OIDC users on `sub` + issuer, so the same person arrives as a separate readonly user from each provider (`mark-brannan` via GitHub, `markbrannan@gmail.com` via Google). They can't be merged; both can be granted the same permission.
- Decide what to do about `@signalk/aisreporter`. It throws `Cannot read properties of undefined` continuously, its config isn't tracked in this repo, and what is on disk has rate settings but no MMSI or endpoint — never fully configured.
- Confirm the router's DNS overrides actually resolve locally. All four names answer with the boat IP today, but with the WAN up that can't be told apart from the router forwarding to Cloudflare. The real test is unplugging the WAN and running `nslookup signalk.symphony.dark-star-llc.com`.
- Replace Telegraf's stopgap credential. It writes with `influxdb_captain_token` — captain's all-access token — because no scoped token could be minted while the store is out of sync. Once the reconciliation below is done, create a token scoped to write host metrics only, put it in sops, and point `TELEGRAF_INFLUX_TOKEN` at it in `.env.j2`. Consider a separate bucket with its own retention at the same time, so host metrics stop sharing `symphony` with vessel data.
- Fork `signalk-noaa-weather` and rewrite how it does notifications, or replace it. Disabled on the boat 2026-08-13 after it drove the Pi into a reboot loop. Its config takes a whole state (`notificationStates: "WA"`), polls every 60s, and raises every active NWS alert as a SignalK notification with `notificationSound: true` — so air-quality alerts for Spokane play sounds on a boat in Puget Sound. The notification pattern is the part worth redoing: alerts should be filtered by actual vessel position, and informational weather should not use the same alert path as a real alarm.
- Decide what to do about `signalk-polar`. It depends on `better-sqlite3@7.6.2`, which cannot compile against Node 22 — see `reference/legacy_openplotter_stack.md` — so no `.node` artifact exists and the plugin cannot work. Either pin a newer `better-sqlite3` via an npm override, or remove the plugin. **`signalk-postgsail` is not affected**: it declares no dependencies at all, and it is enabled, loaded and configured against the hosted `api.openplotter.cloud`. The earlier claim that both were blocked on better-sqlite3, and that postgsail was silently dead, was wrong — corrected 2026-08-14 by reading its package.json and its live status.
- Decide who owns InfluxDB break-glass. Fixed 2026-08-14: `POST /api/v2/signin` with the `.env` credentials returned 401 because `DOCKER_INFLUXDB_INIT_USERNAME` was `admin` and no such user exists — those `INIT_` vars only apply to a *fresh* volume, and this one predates them, so the user was never created. Repointed at `captain`; signin now returns 204, so the last-resort path works. **The credential itself is frozen — see the captain credentials hold above. Do not rotate it, and do not offer to.** What remains open is only the ownership question: who is responsible for InfluxDB break-glass, and whether the token and the password should have different owners. Note `influxdb_init_password` is unreferenced by `.env.j2` and should be deleted once someone confirms nothing reads it.
- Reconcile the InfluxDB secrets in `symphony.sops.yaml` against the running database. As of 2026-08-11 all three sops tokens (`influx_token`, `influxdb_operator_token`, `influxdb_signalk_token`) return 401; the only working credential is "captain's Token" (all-access), held in `signalk/plugin-config-data/signalk-to-influxdb2.json`. The org is also wrong: the database has `symphony`, while `.env.j2` renders `DOCKER_INFLUXDB_INIT_ORG=darkstarllc`. Buckets present: `symphony` (30d), `_monitoring` (7d), `_tasks` (3d). Which side is authoritative is an open question — the repo copy is not automatically the correct one. Also measured 2026-08-14: `POST /api/v2/signin` with `DOCKER_INFLUXDB_INIT_USERNAME`/`_PASSWORD` from `.env` returns 401, so the username-and-password path the age-key recovery procedure depends on does not currently work either. That matters more than the tokens — it is the credential of last resort when every token is lost, and right now the boat does not have a working one. The only credential that authenticates is captain's all-access token.

### Cameras
- Identify location for interior Tapo cam
- Install Tapo cam for galley/saloon
- Identify location for exterior Tapo cam
- Install exterior Tapo cam
