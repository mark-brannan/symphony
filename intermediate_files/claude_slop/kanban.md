# Symphony — open loops

This is symphony's board under the global "Open loops" rule: one line per
card, imperative, always linked; cards die when done, not archived here — see
`log.md` and `git log` for history. `## Yours` is calls only Mark can make
(decisions, purchases, physical/account access). `## Claude's` is work a
session can pick up and execute. Full working detail behind a card lives in
`kanban-detail.md`, or at an existing reference doc / open PR when one
already carries enough context.

## Yours

### Repo & tooling
- [ ] [Purchase itemizations in maintenance/log.md](kanban-detail.md#purchase-itemizations-in-maintenancelogmd) — trim to one-line totals with detail moved to a purchases file, or keep as-is.
- [ ] Merge or close [PR #31](https://github.com/mark-brannan/symphony/pull/31) — superseded: `host/boat-heartbeat` on main already carries the same fails-silent Pushover escalation, better implemented and live-tested 2026-08-14, and the branch's `pushover_token`/`pushover_user` field names would break the deployed `pushover_api_token`/`pushover_user_key` contract. Recommend close.
- [ ] Merge or close PR #25 (influxdb→questdb migration, B4 port) — rebased onto main 2026-08-21, conflicts resolved, CI green and mergeable; it repoints Grafana's provisioned dashboards at QuestDB, so landing it changes what the boat's dashboards query.
- [ ] [Rotate the Tailscale OAuth client credential](kanban-detail.md#rotate-the-tailscale-oauth-client-credential) — it was pasted into a session transcript; read-only scope, not urgent.
- [ ] [Decide dotfiles Google-connector parity](kanban-detail.md#dotfiles-google-connector-parity) — symphony denies three more connectors than dotfiles does; dotfiles-repo edit if wanted.
- [ ] [Approve deleting stale branch `claude/git-hygiene-redesign`](kanban-detail.md#stale-branch-claudegit-hygiene-redesign) — superseded, nothing to salvage, but deleting a pushed ref needs your go-ahead.
- [ ] [Check whether the dotfiles "hooks-continuity-cleanup" session's PR #3 still needs your two manual web-UI steps](kanban-detail.md#undelivered-coordination-note-to-the-hooks-continuity-cleanup-session) — last known state 2026-08-19; may already be resolved.
- [ ] [Re-authorize the Evernote connector](kanban-detail.md#evernote-connector-needs-re-authorization) — token expired mid-session; once it's back, a session files your recovered physical-task list and drops the boat stash.

### Boat systems / SignalK
- [ ] [Pick a moment for Claude to reconcile the boat's Dex onto its pin](kanban-detail.md#dex-is-running-latest-instead-of-its-pin) — recreates the container and drops every OIDC session/refresh token; fine dockside, bad offshore.
- [ ] [Decide BME680 sensor ownership](kanban-detail.md#bme680-sensor-ownership) — enable the dedicated plugin and retire the OpenPlotter i2c entries, or keep OpenPlotter and give up the airquality index.
- [ ] [Confirm PostgSail is receiving voyages](kanban-detail.md#confirm-postgsail-is-receiving) — needs Mark's own PostgSail account to check.
- [ ] [Decide what Cerbo GX 1, solar-forecast, influxdb-v2-buffering and aisreporter should be configured to do](kanban-detail.md#stalled-plugin-configs-needing-a-decision) — four stalled plugins, each missing one piece of owner-known info.
- [ ] [Decide the nine major-version SignalK plugin upgrades](kanban-detail.md#nine-major-version-signalk-plugin-upgrades) — two are safety-of-navigation and want someone watching when they land.
- [ ] [Decide whether two SSO user records (GitHub vs Google) is a problem](kanban-detail.md#two-sso-user-records-github-vs-google) — SignalK can't merge them; both can hold the same permission.
- [ ] [Reconcile signalk/security.json (repo vs boat)](kanban-detail.md#reconcile-signalksecurityjson-repo-vs-boat) — field-by-field, including whether mark-brannan should be admin on both.
- [ ] [Decide who owns InfluxDB break-glass, and which side is authoritative for org/tokens](kanban-detail.md#influxdb-break-glass-ownership-and-secret-reconciliation).
- [ ] [Confirm the router's DNS overrides resolve locally](kanban-detail.md#confirm-the-routers-dns-overrides-resolve-locally) — needs the WAN physically unplugged to test.
- [ ] [Install the ntfy Android app and subscribe to symphony-alarms](kanban-detail.md#subscribe-the-phone-to-ntfy) — on both the boat and dev servers, using the tailnet/LAN address.
- [ ] [Hand over Symphony Plumbing Library.xml](kanban-detail.md#symphony-plumbing-libraryxml) when plumbing diagramming starts (Google Drive only, not fetchable).

### Boat Pi / hardware
- [ ] **Decide the rebuild fork: HALOS on a fresh 64 GB card, or keep hardening the current OpenPlotter install.** Grafana's return, the dockerization track and the SD-card strategy are all downstream of this one call. Evidence on 2026-08-25: a Node runtime swap silently removed `signalk-server`, the boat ran dark for 2 days, and OpenPlotter's own installer is what did it (`signalkPostInstall.py:45` runs `apt autoremove -y nodejs npm`). Against: HALOS undoes real work already done.
- [ ] **Decide whether the current 32 GB card comes home after the swap.** It holds the only copies of `~/influx-export` (1.4 GB) and `~/keep-before-purge/grafana.db` — neither can cross the WAN without throttling risk, so a physical card swap is the only way to recover them.
- [ ] [Confirm the HALPI2 purchase](kanban-detail.md#halpi2-purchase-sd-card-boot-media-strategy) — already in cart; ends the SD-card/boot-media decision outright.
- [ ] [Decide whether to track openplotter.conf in git](kanban-detail.md#track-openplotteropenplotterconf-in-git-or-not) — its `soundignore` key is load-bearing and lives only on the boat.
- [ ] [Decide whether to pursue a read-only root filesystem](kanban-detail.md#read-only-root-filesystem-for-the-boat-pi) — real workflow change, not a config toggle.
- [ ] [Pick a journald SystemMaxUse size](kanban-detail.md#journald-cap-on-the-boat-pi) — no longer hypothetical: the journal had grown to 1.3 GB and was a top-5 disk consumer on 2026-08-25. Vacuumed to 200 MB as a one-time fix; without a cap it just regrows.

## Claude's

### Infrastructure
- [ ] Deploy the `telegraf.conf` InfluxDB-output removal to the boat — the repo change is committed, but `/etc/telegraf/telegraf.conf` is a symlink into the boat's own checkout, so it needs a pull there. Until then Telegraf fails every flush against the purged InfluxDB and drops host metrics on buffer overflow.
- [ ] Document the boat Pi's non-standard Node/npm state in `RUNBOOK.md` — `/usr/bin/node` is nsolid 22.23.2 (apt), the shadowing standalone 22.17.0 is parked at `/usr/local/bin/node.disabled-20260825`, `signalk-server` now lives in `/home/pi/.npm-global`, and `~/.signalk/signalk-server` was rewritten to match. None of this matches what the runbook currently describes.
- [ ] Correct `RUNBOOK.md` § "Upgrading SignalK on the boat Pi" — it currently directs the reader to `sudo openplotter-signalk-installer` as the only safe path. That tool caused the 2026-08-23 outage, and its `npm config get prefix` step (`signalkPostInstall.py:91`) is cwd-dependent under sudo, so it can write a launcher pointing into `/root` that the `User=pi` service cannot read.
- [ ] [Re-run the secret-tooling suite on a keyed machine (NucBoxK12) after pulling latest main](kanban-detail.md#confirm-secret-tooling-suite-on-a-keyed-machine) — closes the last leg of PR #19's TASK.
- [ ] [Sweep the stale claude/* branches, excluding the two rescued from the boat](kanban-detail.md#land-or-discard-three-held-claude-branches) — `ecoworthy-signalk-telemetry-vy82ta` @48f3122 and `symphony-pushover-setup-ce12i0` @3f08bd3 are unmerged and exist nowhere else; don't touch them.
- [ ] [Finish dockerizing the boat computer](../../reference/containerization_strategy.md) — Track B; SignalK, Grafana and Caddy are still native. Caddy last, done carefully — it's the front door.
- [ ] [Close out the QuestDB migration now that InfluxDB is gone](kanban-detail.md#questdb-migration-execution-notes-not-in-the-reference-doc) — InfluxDB was stopped, disabled and purged on 2026-08-25 under disk pressure, so the soak and B5 parity checks can never run against it. Remaining: confirm QuestDB is actually capturing what InfluxDB did, re-run `scripts/questdb_table_hygiene.sh`, and uninstall signalk-to-influxdb2.
- [ ] [Resolve which Grafana dashboard set is the QuestDB port target](kanban-detail.md#which-grafana-dashboard-set-is-the-questdb-port-target) — blocks open PR #10.
- [ ] [Deploy the repo's Grafana provisioning to the boat](kanban-detail.md#deploy-the-repos-grafana-provisioning-to-the-boat) — blocked: Grafana was disabled and `/var/lib/grafana` purged on 2026-08-25; the hand-made dashboards survive only as `~/keep-before-purge/grafana.db` on the Pi. Whether Grafana returns natively or only in the dockerized/HALOS build is the fork below.
- [ ] [Build a host-health Grafana dashboard from Telegraf's existing metrics](kanban-detail.md#build-a-host-health-grafana-dashboard) — blocked: no Grafana on the boat since 2026-08-25. Queries were verified live and still apply; this is panels, not discovery, whenever Grafana comes back.
- [ ] [Put fail2ban (or equivalent) in front of sshd on the boat Pi](kanban-detail.md#rate-limit-sshd-on-the-boat-pi) — precautionary, not a response to anything measured.
- [ ] [Build the Ansible clock and watchdog roles](../../reference/host_provisioning.md) — smallest honest slice per the 2026-08-13 plan.
- [ ] [Extend `lint_repo_hygiene.py` with a soft warn on long log.md bullets](kanban-detail.md#doc-cleanup-follow-ups-still-open) — optional enforcement, from the 2026-08-19 bloat audit.
- [ ] [Set up a private repo for Vaultwarden before building off-machine hosting](kanban-detail.md#set-up-a-private-repo-for-vaultwarden-hosting).

### SignalK data & plugins
- [ ] [Assess PR #28's project-specific half](https://github.com/mark-brannan/symphony/pull/28) — the global part landed in dotfiles already; decide whether symphony needs its own `maintenance/stats.md`, `stats-data.json`, `.claude/hooks/measure-cherry-pick.sh` and the CLAUDE.md no-cherry-pick rule, or whether the dotfiles copy covers it. Keep the PR open either way — do not delete.
- [ ] Carry [PR #29](https://github.com/mark-brannan/symphony/pull/29)'s OIDC identity-permissions work upstream — implementation is on [the fork branch](https://github.com/mark-brannan/signalk-server/tree/oidc-identity-permissions) behind [fork PR #1](https://github.com/mark-brannan/signalk-server/pull/1); next step is opening the conversation with Matti Airas (Hat Labs) on the SignalK Discord before an upstream PR. Mark intends to pursue this; not top priority.
- [ ] Review [PR #30](https://github.com/mark-brannan/symphony/pull/30) properly and do a redaction/simplification pass — it carries the verified DSC/AIS distress-chain findings, `reference/distress_monitoring.md` and the RUNBOOK test procedure, none of which are on main. **Keep it in draft** until the delicate details are redacted; resolve its conflicts as part of that pass.
- [ ] [Deploy the openweather-signalk humidity-fix Node-RED flow](kanban-detail.md#deploy-the-openweather-signalk-humidity-fix-flow) — needs boat access; flow is built but unverified in the live editor.
- [ ] [Add signalk-lint batch 2 (host-level rules)](kanban-detail.md#signalk-lint-batch-2-host-level-rules) — can0/gpsd/systemd/cron/journald faults this boat actually hit.
- [ ] [Make "no rule may throw on malformed input" a stated signalk-lint convention](kanban-detail.md#signalk-lint-no-rule-may-throw-on-malformed-input) — give every rule a garbage-input fixture.
- [ ] [Trim RUNBOOK's remaining prose-heavy sections](kanban-detail.md#trim-runbooks-remaining-prose-heavy-sections) — "Installing host files" is the best target.
- [ ] [Bridge NMEA 2000 System Time (PGN 126992) to chrony](kanban-detail.md#gps-time-off-the-n2k-bus-into-chrony) — SHM bridge or network feed; gpsd has no device, so the boat has a GPS clock it can't use yet.
- [ ] [Set source priorities for position once the AIS is powered](kanban-detail.md#set-source-priorities-for-position-once-ais-is-powered) — blocked: AIS not yet powered (physical task, tracked in Evernote).
- [ ] Shepherd [upstream PR #189](https://github.com/naugehyde/bt-sensors-plugin-sk/pull/189) (lazy D-Bus + reconnect-on-error) to merge — opened 2026-08-25 against `naugehyde/bt-sensors-plugin-sk`; the fix is already deployed on the boat and the `auth_timeout` workaround is already gone.
- [ ] [Re-link bt-sensors-plugin-sk after the SignalK reinstall](kanban-detail.md#bt-sensors-plugin-sk-must-survive-the-signalk-reinstall) — the boat runs a source checkout, not the published package; the registry build lacks the fix.
- [ ] [Confirm whether SignalK's missing /usr/local/bin symlinks were a real regression](kanban-detail.md#signalks-usrlocalbin-symlinks-went-missing) — exit 127 seen 2026-08-25, but a concurrent reinstall session may account for it.
- [ ] [Trim SignalK's ~45s startup time](kanban-detail.md#trim-signalks-45s-startup-time) — dead internet-speed/healthcheck/duplicate-plugin noise.
- [ ] [Add a fast barometric-pressure-drop notification](kanban-detail.md#fast-barometric-pressure-drop-notification) — trend data exists, no zone configured yet.
- [ ] [Verify Grafana SSO end to end](kanban-detail.md#verify-grafana-sso-end-to-end) — config is live, browser login never exercised.
- [ ] [Restore signalk-healthcheck's config to git](kanban-detail.md#restore-signalk-healthchecks-config-to-git) — needs add_inplace_secret.sh rewired for the mail-password field first.
- [ ] [Fix better-sqlite3 so signalk-polar can run](kanban-detail.md#fix-better-sqlite3-for-signalk-polar) — pin a newer version via override, or drop the plugin.
- [ ] [Evaluate the parked/unused SignalK plugins on the dev container](kanban-detail.md#evaluate-parkedunused-signalk-plugins-on-the-dev-container) — open-meteo works, signalk-questdb is misconfigured, three more unevaluated.
- [ ] [Add a weather term to ACTOR_HINTS in signalk_plugin_census.py](kanban-detail.md#add-a-weather-term-to-actor_hints) — open-meteo scores unmatched today.
- [ ] [Scope the COLREGs navigation-lights plugin](kanban-detail.md#scope-the-colregs-navigation-lights-plugin) — switches, condition input and warn-vs-switch are all still open.
- [ ] [Evaluate a generic single-path-arithmetic SignalK plugin](kanban-detail.md#generic-single-path-arithmetic-plugin-idea) — not yet justified; revisit if a third case turns up.
- [ ] [Fork signalk-noaa-weather to filter alerts by vessel position](kanban-detail.md#fork-signalk-noaa-weathers-notification-behavior) — currently alarms on any NWS alert for the whole state.
- [ ] [Verify the heartbeat's soft-warning tier live](kanban-detail.md#verify-the-heartbeats-soft-warning-tier-live) — covered by mock tests only; real mem/disk haven't hit the warn band.
- [ ] [Watch unattended-upgrades over a few more cycles](kanban-detail.md#watch-unattended-upgrades-over-a-few-more-cycles) — confirm behavior before calling it settled.
- [ ] [Add data-source staleness to the heartbeat payload](kanban-detail.md#add-data-source-staleness-to-the-heartbeat-payload) — the one healthcheck gap nothing else covers.
- [ ] [Audit and fork signalk-pushover-notification-relay](kanban-detail.md#audit-and-fork-signalk-pushover-notification-relay) — or fall back to the Node-RED flow if it's beyond saving.
- [ ] [Research MOB detection options](kanban-detail.md#mob-detection-research) — never live-test the DSC emergency button, standing rule.
- [ ] [Remove the deprecated @signalk/zones plugin](kanban-detail.md#remove-the-deprecated-signalkzones-plugin) — mirror its zone meta into the boat's own baseDeltas first.
- [ ] [Settle i2c IMU data not showing up in SignalK](kanban-detail.md#recovered-boat-stash-notes-imu-temp-sensors-runbook-gaps) — plugin or OpenPlotter; Mark's own note.
- [ ] [Determine why temp sensor readings look off](kanban-detail.md#recovered-boat-stash-notes-imu-temp-sensors-runbook-gaps) — dropped readings vs. dead batteries; Mark's own note.
- [ ] [Fill the RUNBOOK gaps Mark called out](kanban-detail.md#recovered-boat-stash-notes-imu-temp-sensors-runbook-gaps) — simulating a ping failure, testing ntfy and Pushover locally, and a pass for further gaps.

### Hardware design backlog
- [ ] [Fit a DS3231 RTC to the boat Pi](kanban-detail.md#fit-a-ds3231-rtc-to-the-boat-pi) — cheap, independent of the GNSS question, makes the offline clock survivable.
- [ ] [Plan the sensor design backlog](kanban-detail.md#sensor-hardware-design-backlog) — engine temp/flow, rudder position, pump flow, air quality, pressure, illuminance, smart pump.
- [ ] [Plan the autopilot hardware backlog](kanban-detail.md#autopilot-hardware-backlog) — pypilot, board design, separate IMU.
- [ ] [3D-print the sensor enclosures](kanban-detail.md#3d-print-sensor-enclosures-backlog) — gas sensor, BME688, IMU cases.
