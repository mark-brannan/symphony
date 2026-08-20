# Claude kanban — session working state (Symphony)

Claude-facing. Micro-tasks, blocked questions, and detailed working state for
SignalK / IoT / infra work live here — segregated from the human files in
`maintenance/`, which get only finished, high-level results. See CLAUDE.md
§ "Claude session state" for the rules. Nothing in this file is authoritative
over the repo's reference docs; it is working memory.

Sessions pull from here to start work and flush loose ends back here at
wrap-up. Dated session narrative goes in `log.md` beside this file.

**Card format:** one line — a link or file reference, the action in the
imperative, `blocked:` plus the dependency only when applicable. Write the
card the moment the loop is found, not at wrap-up. Delete a card the moment
it's done; a durable decision or a meaningful finished result gets its
one- to three-line `log.md` entry in the same edit, not a paragraph left
behind here. This is a WIP list, not a log — `git log` and `log.md` already
keep the history. See CLAUDE.md § "Claude session state" for the full rule.

**2026-08-20 triage note:** the ~960 lines below this point predated the
rule above and had become a log, not a WIP list — resolved items kept
paragraph-long after-the-fact narrative instead of being deleted. Rewritten
down to one-liners in a dedicated pass (Mark's call, not organic decay).
Resolved entries were deleted after confirming their durable facts already
live in `maintenance/log.md`, `intermediate_files/claude_slop/log.md`, a PR
body, or `git log`; two decisions that had no other durable home
(CI-advisory-on-`main`, the frozen-secrets-guard stays-hardcoded call) moved
to `reference/security_posture.md` first. Still-open items kept their
essential facts and lost the verification narrative.

## Doc cleanup
- `maintenance/log.md` purchase itemizations — trim to one-line totals + a purchases file, or keep as-is — blocked: Mark's call.
- Add a soft warn to `scripts/lint_repo_hygiene.py` for `log.md` bullets over ~5 lines.

## Branches
- Delete `claude/git-hygiene-redesign` (7be6e6a) — superseded, nothing worth salvaging, no PR ever opened (session was API-blocked) — blocked: Mark's explicit delete go-ahead (§ Git hygiene, deleting a pushed ref).
- `signalk-oidc-identity-permissions-4kk8gl` (OIDC proposal, `proposals/signalk-oidc-identity-permissions.md`), `symphony-docs-corrections-aeuorm` (DSC/AIS distress-chain test procedure, `reference/distress_monitoring.md`), `laughing-hamilton-7f7pbg` (cherry-pick metrics framework) — each needs its own land-or-discard decision; nothing else has this content.
- `grafana-questdb-port-target` — open PR #10, land or close once the dashboard-port question below is answered.

## `main` rewrite / boat checkout reconciliation
- **The boat's `/home/pi/symphony` checkout is on the old, pre-rewrite `main` lineage (68e4e04) and has never fetched the rewritten `origin/main`.** A plain `git pull` there would merge unrelated histories against a dirty tree. That directory is live — `.env` feeds caddy/dex/telegraf, `dex/config.yaml`, and `/etc/telegraf/telegraf.conf` all read from it — so a bad reconciliation breaks Dex, the OIDC front door, i.e. the thing you'd use to fix it remotely.
- It holds unpushed work nowhere else exists: `claude/ecoworthy-signalk-telemetry-vy82ta` @48f3122 (JBD BMS BLE capture, 8 commits) and `claude/symphony-pushover-setup-ce12i0` @3f08bd3, plus two stashes (`signalk-ntfy.json`, `priorities.md`).
- Order: push the two boat branches as-is (no rebase/squash) → reconcile the checkout → reconcile the stashes → verify caddy/dex/telegraf/signalk/grafana all still run.

## SignalK / infra decisions still open
- **Which Grafana dashboards are the QuestDB port target (B4 of `reference/containerization_strategy.md`)?** Two non-equivalent sets exist — the boat's native five (76 panels, InfluxQL, imported, mostly broken datasource refs) vs. the repo's generated six (`scripts/build_dashboards.py`, Flux, path-accurate). First step: open both side by side on the boat and see what the imported five show that the generated six don't — needs the boat on the tailnet, is a dedicated session's work.
- Decide two-SSO-user-records is fine as-is or needs reconciling — SignalK keys OIDC users on `sub` + issuer, so `mark-brannan` (GitHub) and `markbrannan@gmail.com` (Google) can't merge, only be granted matching permissions.
- `signalk/security.json` in the repo is the dev container's, not the boat's (`secretKey` and the `captain` hash both differ) — syncing either direction invalidates tokens / changes the captain password, so it isn't a sync. One real question inside it: `mark-brannan` is `admin` in the repo, `readonly` on the boat — decide per field.
- Reconcile `symphony.sops.yaml`'s InfluxDB tokens against the running DB — all three (`influx_token`, `influxdb_operator_token`, `influxdb_signalk_token`) 401; only "captain's Token" (all-access, in `signalk-to-influxdb2.json`) works, and the org is wrong too (`darkstarllc` in `.env.j2` vs. `symphony` live). Which side is authoritative is open.
- Decide InfluxDB break-glass ownership — `captain`'s password now works as the signin fallback (fixed), frozen per `reference/security_posture.md`; open question is who owns it and whether the token should have a different owner. Delete `influxdb_init_password` from `.env.j2` once confirmed unread.
- Replace Telegraf's stopgap `influxdb_captain_token` (captain's all-access) with a host-metrics-scoped token once the reconciliation above lands; consider a separate bucket/retention for host metrics at the same time.
- Confirm the router's DNS overrides resolve locally, not just via WAN forwarding — test by unplugging WAN and running `nslookup signalk.symphony.dark-star-llc.com`.
- Decide whether the InfluxDB/Grafana stop-on-memory-pressure should become a permanent disable instead of reboot-restores — only remaining open piece of the 2026-08-13 decision (§ "Boat Pi's memory headroom" in CLAUDE.md covers the rest).

### House batteries / bt-sensors follow-ups (root cause fixed 2026-08-20, see log.md)
- Fix the bus lifecycle in `bt-sensors-plugin-sk` (Mark's fork) properly: move `createBluetooth()` out of module scope into `plugin.start()`, add a reconnect-with-backoff `error` handler. Once landed, remove the `auth_timeout` workaround (`/etc/dbus-1/system-local.conf`, `host/dbus-auth-timeout.conf`). Worth upstreaming.
- Install `plugins/signalk-plugin-watchdog` on the boat with `bt-sensors-plugin-sk` in `expectPlugins` — written for this exact incident, still not deployed.
- `Cerbo GX 1` in the bt-sensors config has an empty `paths` block — publishes nothing regardless of the D-Bus fix (documented trap, `RUNBOOK.md` → "Setting up a BLE sensor"). Decide what it should publish.
- Trim SignalK's ~45s startup (`signalk-plugin-internet-speed` throws every start, `signalk-healthcheck` watches a nonexistent `n2k-can0`, `signalk-to-noforeignland` installed twice) — this is what made the D-Bus auth-timeout race reachable at all.

## Plugin decisions (boat)
- BME680: enable the dedicated `@oehoe83/signalk-raspberry-pi-bme680` plugin (config already points at the working sensor, bus 1/0x77; set pressure path to `outside`) and retire the legacy `openplotter-i2c-read` service — or keep OpenPlotter and give up the airquality index. Can't run both: contention disturbs the gas heater cycle. Plugin needs a 500s burn-in after start.
- Remove the deprecated `@signalk/zones` plugin (installed, enabled, never registered) and mirror the airquality zone meta from `signalk/baseDeltas.json` into the boat's own baseDeltas — zones are server-core via `meta.zones` now.
- Fix or drop `signalk-polar` — pinned to `better-sqlite3@^7.6.2`, which can't compile on Node 22 (`reference/legacy_openplotter_stack.md`). Either an npm override to a newer `better-sqlite3` or remove the plugin. (`signalk-postgsail` is unaffected — no dependencies, working.)
- Confirm PostgSail is actually receiving voyages — plugin's enabled, hourly "removing metrics from buffer" line is ambiguous (could mean nothing to send). Needs Mark's PostgSail account to check. If it works, saillogger ($7.99/mo) isn't needed.
- Configure or drop `signalk-solar-forecast` and `signalk-to-influxdb-v2-buffering` — both installed, enabled, throw on every start reading an unfilled config key (a location, InfluxDB credentials respectively). Deliberate config decision, not a bug fix.
- Decide about `@signalk/aisreporter` — throws continuously, untracked config, no MMSI/endpoint ever set.
- Fork `signalk-noaa-weather` and rewrite its notification handling, or replace it — disabled on the boat after driving a reboot loop; it raises every active NWS alert for a whole configured state (`WA`) as a sounding SignalK notification regardless of vessel position. Alerts should be position-filtered and use a different path than real alarms.
- Add a weather term to `ACTOR_HINTS` in `scripts/signalk_plugin_census.py` — `open-meteo` is an actor (registers a v2 weather API, doesn't publish paths) but scores `unmatched` for lack of a hint, misreading as a fault.
- `marinetraffic.XX` publishes one path and shows in `unattributed_sources` despite `marinetraffic-public` reading as unconfigured — unexplained, unresolved.
- Nine major-version plugin upgrades outstanding (all current within declared ranges, so these are deliberate bumps, not drift): `signalk-anchoralarm-plugin` 1.18.2→2.0.1 and `@signalk/signalk-autopilot` 1.7.0→2.6.0 (safety-of-navigation, want someone watching the boat); `@mxtommy/kip` 3.12.0→4.8.5, `@signalk/freeboard-sk` 2.24.2→3.1.0, `@signalk/signalk-node-red` 3.2.1→4.4.0, `signalk-tides` 1.5.0→2.1.2; `signalk-postgsail` 0.5.1→0.6.0, `signalk-noaa-space-weather` 0.19.0→0.20.0 (Mark's own repo — coordinate), `vhfinfo` 0.0.34→0.0.37.
- Evaluate the parked-but-unevaluated dev-container plugins (`signalk-doctor`, `signalk-container`, `signalk-crows-nest`, `signalk-questdb`) — installed on purpose to try, not drift; don't install/remove based on boat-vs-dev difference until Mark's judged them. `signalk-questdb`'s `questdbHost: 127.0.0.1` addresses the wrong container from inside SignalK, so it's never written a row regardless.
- `intermediate_files/plugin-first-pass.md` (started 2026-08-14, not finished) is where the dev-container plugin evaluation write-up belongs before any of it gets committed — don't diff/sync/reconcile `plugin-config-data` against the boat until it exists.

## Delivery / monitoring
- Bridge NMEA 2000 time (PGN 126992) to chrony via a SHM segment or network feed — gpsd has no serial device so the standard `refclock SHM` recipe can't work as-is; the boat's clock is internet-only until this or the DS3231 RTC lands.
- Fit a DS3231 RTC to the boat Pi (Qwiic/I2C on the PiCAN-M; `dtoverlay=i2c-rtc,ds3231` + udev rule, role already in `tkurki/marinepi-provisioning`) — no RTC today means a wrong clock on every offline boot, breaking TLS validity, OIDC token windows, and InfluxDB timestamps.
- Get GPS time off the N2K bus (126992, 129029) instead of the disconnected serial gpsd path — depends on the chrony bridge item above; doesn't remove the RTC case (needs a bus + a fix, doesn't cover cold offline boot).
- Add a fast-barometric-pressure-drop zone/notification (squall warning) — `environment.barometer.*` / `environment.outside.pressure.trend/prediction` carry the data, nothing turns a fast drop into a notification yet. `meta.zones` entry or small Node-RED flow. See `reference/node_red_signalk_use_cases.md` List 3 §M.
- MOB detection — open research item, medium-low priority. **Never live-test the DSC emergency button on this or any boat — standing rule.** Aboard today: handheld VHF w/ DSC emergency button, AIS Class B transceiver, `signalk-mob-notifier` installed but unconfirmed whether anything consumes the DSC/AIS hardware. Only adopt something already proven elsewhere. See `reference/node_red_signalk_use_cases.md` §H.
- Decide whether to cap journald (`SystemMaxUse`) on the boat Pi — hit 639MB on 2026-08-13 (pypilot crash loop), self-rotated to 192MB; right cap number not yet chosen.
- Watch SignalK's RSS over a longer window — sawtooths (1.1–1.2GB) rather than climbing monotonically, which reads as V8 reclaiming rather than a leak, but `pswpout` moved during the same window. Telegraf's `procstat` now records it per-service so this is a query, not a re-measurement.

## Cameras
- Identify + install interior Tapo cam (galley/saloon).
- Identify + install exterior Tapo cam.

## Storage / hosting
- **HALPI2 (8GB/512GB SSD, $614.35) is in cart, orderable** — settles the boat-Pi storage question outright: SSD instead of SD card, RP2040 does an orderly shutdown on power loss (the boat's actual failure mode, which no card/drive choice fixes). Order it; interim SD-card spend only makes sense if this is being deferred on purpose.
- Evaluate a read-only root filesystem for the boat Pi (`tkurki/marinepi-provisioning` has a `root-ro` role) — real workflow change (every write becomes deliberate), so a decision, not a toggle.
- Decide on Chromium's 1.9GB profile on the boat Pi (`~/.config/chromium`, last used 2026-08-13, not running) — leave it, clear caches/service-workers only (~570MB, keeps logins), or remove the browser + profile (`apt-mark manual` is already holding it from `autoremove`).
- Set up off-machine hosting (VPS or NAS) for Vaultwarden holding the sops/age key backup, reachable via Tailscale — currently a local Docker PoC on the boat computer, single point of failure for the key protecting `symphony.sops.yaml`/`signalk/security.json`. `vaultwarden/` compose file is ready; needs a private repo of its own first since this repo is public and Mark wants the vault for non-Symphony things too — plain `git rm` when that happens, nothing secret is in the files today.

## Sensors / hardware backlog
- Design engine temp sensors and diagram.
- Design engine flow sensor plumbing.
- Design engine flow sensor electrical.
- Rudder position sensor.
- Pump flow sensors.
- Air quality sensors.
- Air pressure sensor.
- Illuminance sensor.
- Additional temperature sensors.
- Design smart pump system with voltage/current detection.
- pypilot; design pypilot board; separate IMU for pypilot.
- 3D-print gas sensor case; 3D-print BME688 case; 3D-print IMU case.
- Install BLE hub for lighting and related devices.
- Rebuild boat computer.
- Set source priorities for position once the AIS is powered (`~/.signalk/priorities.json` is `{}` today) — can't be done ahead of time since N2K addresses are claimed dynamically; procedure in `RUNBOOK.md` → "When the AIS is powered, there will be two GPS sources".
- Ansible host provisioning (`reference/host_provisioning.md` has the plan) — next slice is the `clock` and `watchdog` roles, already fully described in `host/install.sh`.
- Deploy the openweather-signalk humidity-fix Node-RED flow (needs boat access) — `environment.outside.relativeHumidity` publishes raw percent instead of SignalK's 0-1 ratio (confirmed root cause upstream, reported). Flow JSON + procedure in `RUNBOOK.md`; built but unverified against the live editor. Remove once the upstream fix ships.
- Evaluate a small custom SignalK plugin for generic single-path scale/offset arithmetic — no existing plugin does it (`signalk-path-mapper` renames only, `signalk-derived-data` has fixed calculators only, `signalk-value-combiner` needs two live paths). Two data points so far (openweather humidity, BME680 naming) don't yet justify it over Node-RED; revisit on a third case.
- New custom plugin: COLREGs-driven navigation-lights switching off NMEA2000/relay state — not scoped yet (which switches/relays, which vessel-condition input, warn-only vs. actively switch). See `systems/electrical.md`'s lighting sub-panel notes. Decide SignalK plugin vs. Node-RED flow early — the branching likely outgrows a flow.
- Fit fail2ban or an equivalent rate limit in front of sshd on the boat Pi — precautionary (zero failed attempts measured), but a shell on the box is a materially worse outcome than a SignalK read, and the wifi PSK is the weakest link in front of it. Password auth stays (offline fallback); this is about rate-limiting, not keys-only.
- signalk-lint: batch 2 host-level rules still to write (needs collector work) — `can0` UP with no N2K provider, `gpsd` naming a nonexistent device, a systemd drop-in with directives before its `[Section]`, a cron reboot with no npm-in-flight guard, an autostart browser against a disconnected DRM output, no RTC + no synced NTP, `RuntimeWatchdogUSec` disagreeing with the kernel watchdog timeout, journald with no `SystemMaxUse`. Each is a fault this boat actually hit.
- Make "no rule may throw on malformed input" a stated signalk-lint convention — a malformed connection entry crashed a whole lint run once; the box most in need of linting is the one most likely to have a garbage config.
- Trim the RUNBOOK's remaining prose-heavy sections — "Installing host files" is the best target (a paragraph per installed file that mostly belongs in `reference/`); "SSO login" is prose-heavy but part of it is genuinely click-through with no command form.
- Build a host-health Grafana dashboard from what Telegraf already records — `processes/blocked` (non-zero+stuck = wedged task), `rpi_health/under_voltage_since_boot` (latched), `chrony/last_offset` (group away `reference_id` or every NTP peer is its own series), `internal_write/metrics_dropped`. Pair with `kernel/context_switches` + `mem/available` on the same axis for the starvation signature. Queries already verified against live data — this is panels, not discovery.
- Deploy the repo's Grafana provisioning to the boat — `/etc/grafana/provisioning` on the Pi still only holds Debian's sample files; the running Grafana was hand-configured, so the repo's five dashboards + datasource def are untested against real data.
- Verify Grafana SSO end to end — config is live, browser login never exercised.
- Watch the first few `unattended-upgrades` cycles (enabled 2026-08-13, security-only, blacklists nodejs/signalk-server/bluez/kernel/openplotter-*) — confirm behavior via `journalctl -u unattended-upgrades`.

## Infrastructure — containerization / QuestDB migration
Track B of `reference/containerization_strategy.md` (decided 2026-08-18) carries the ordered steps and boat-side checklist; this is only where things stand. Dex, ntfy, QuestDB are containerized; SignalK, Grafana, Caddy still native. Migrate one at a time — Caddy last and carefully, it's the front door (SignalK UI, Grafana, OIDC callback, and remote access to fix any of it all ride on it). When Caddy moves, drop the transitional `127.0.0.1:5556` publish from `compose-idp.yml`.

InfluxDB→QuestDB migration (B1-B5, `reference/containerization_strategy.md`): B1 (backup+verify), B2 (QuestDB container), B3 (plugin swap+config+Telegraf dual-write) all done, 2026-08-20 — see `maintenance/log.md`. Remaining:
- **B4 (dashboard port) is blocked** — see "Which Grafana dashboards are the QuestDB port target?" above.
- B5 (parity checks + InfluxDB retirement) — not started, depends on B4 and the multi-day soak.
- Don't uninstall `signalk-to-influxdb2` until B5 passes.
- A true off-boat copy of the InfluxDB backup artifacts is still worth getting — they're sitting at `/home/pi/influx-export/` on the boat, ready for Mark to `scp` from one of his own tailnet-P2P devices; not urgent, the on-boat restore test already proved the backup is good.
- `scripts/questdb_table_hygiene.sh` owns an explicit table list (not "everything unmanaged" — a TTL deletes data at the far end, so auto-adopting an unfamiliar table risks someone else's data). A new Telegraf input needs adding to that list explicitly.
- Watch disk headroom on any new QuestDB writer — a new writer's tables preallocate ~1MB/column + a bitmap index per SYMBOL column; this already filled the boat's root filesystem once (recovered, `compose-questdb.yml`'s `QDB_*` append-page vars now cut to 256k/128k). `du -sm` on the volume is the only honest footprint check; row counts say nothing. Budget ~6GB free, measure over hours not minutes (WAL segment rollover makes short samples read negative).
