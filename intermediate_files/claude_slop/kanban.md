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
- [ ] [Land or discard three held claude/* branches](kanban-detail.md#land-or-discard-three-held-claude-branches) — signalk-oidc-identity-permissions-4kk8gl, symphony-docs-corrections-aeuorm, laughing-hamilton-7f7pbg each need their own call.
- [ ] [Rotate the Tailscale OAuth client credential](kanban-detail.md#rotate-the-tailscale-oauth-client-credential) — it was pasted into a session transcript; read-only scope, not urgent.
- [ ] [Decide dotfiles Google-connector parity](kanban-detail.md#dotfiles-google-connector-parity) — symphony denies three more connectors than dotfiles does; dotfiles-repo edit if wanted.

### Boat systems / SignalK
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
- [ ] [Confirm the HALPI2 purchase](kanban-detail.md#halpi2-purchase-sd-card-boot-media-strategy) — already in cart; ends the SD-card/boot-media decision outright.
- [ ] [Decide what to do about Chromium on the boat Pi](kanban-detail.md#chromium-on-the-boat-pi) — leave it, clear its 1.9 GB profile, or remove it.
- [ ] [Decide whether to track openplotter.conf in git](kanban-detail.md#track-openplotteropenplotterconf-in-git-or-not) — its `soundignore` key is load-bearing and lives only on the boat.
- [ ] [Decide whether to pursue a read-only root filesystem](kanban-detail.md#read-only-root-filesystem-for-the-boat-pi) — real workflow change, not a config toggle.
- [ ] [Decide whether InfluxDB/Grafana's stop-under-pressure should become a permanent disable](kanban-detail.md#influxdbgrafana-permanent-disable-or-stay-stop-on-pressure).
- [ ] [Decide whether to cap journald and pick a SystemMaxUse size](kanban-detail.md#journald-cap-on-the-boat-pi).

## Claude's

### Infrastructure
- [ ] [Re-run the secret-tooling suite on a keyed machine (NucBoxK12) after pulling latest main](kanban-detail.md#confirm-secret-tooling-suite-on-a-keyed-machine) — closes the last leg of PR #19's TASK.
- [ ] [Reconcile the boat's checkout with the rewritten main lineage](kanban-detail.md#boats-checkout-stranded-on-the-old-main-lineage) — push its two stranded branches first, then the checkout, then the stashes, then verify all five services. Real blast radius (Dex/OIDC) if done out of order.
- [ ] [Finish dockerizing the boat computer](reference/containerization_strategy.md) — Track B; SignalK, Grafana and Caddy are still native. Caddy last, done carefully — it's the front door.
- [ ] [Run the QuestDB multi-day soak, then B5 parity checks, then retire InfluxDB](reference/containerization_strategy.md) — B1-B3 done; don't uninstall signalk-to-influxdb2 yet.
- [ ] [Resolve which Grafana dashboard set is the QuestDB port target](kanban-detail.md#which-grafana-dashboard-set-is-the-questdb-port-target) — blocks open PR #10.
- [ ] [Deploy the repo's Grafana provisioning to the boat](kanban-detail.md#deploy-the-repos-grafana-provisioning-to-the-boat) — the native install is still hand-configured.
- [ ] [Build a host-health Grafana dashboard from Telegraf's existing metrics](kanban-detail.md#build-a-host-health-grafana-dashboard) — four queries already verified live; it's panels, not discovery.
- [ ] [Replace Telegraf's stopgap InfluxDB credential with a scoped token](kanban-detail.md#replace-telegrafs-stopgap-influxdb-credential) — currently uses captain's all-access token.
- [ ] [Put fail2ban (or equivalent) in front of sshd on the boat Pi](kanban-detail.md#rate-limit-sshd-on-the-boat-pi) — precautionary, not a response to anything measured.
- [ ] [Build the Ansible clock and watchdog roles](reference/host_provisioning.md) — smallest honest slice per the 2026-08-13 plan.
- [ ] [Set up a private repo for Vaultwarden before building off-machine hosting](kanban-detail.md#set-up-a-private-repo-for-vaultwarden-hosting).

### SignalK data & plugins
- [ ] [Deploy the openweather-signalk humidity-fix Node-RED flow](kanban-detail.md#deploy-the-openweather-signalk-humidity-fix-flow) — needs boat access; flow is built but unverified in the live editor.
- [ ] [Add signalk-lint batch 2 (host-level rules)](kanban-detail.md#signalk-lint-batch-2-host-level-rules) — can0/gpsd/systemd/cron/journald faults this boat actually hit.
- [ ] [Make "no rule may throw on malformed input" a stated signalk-lint convention](kanban-detail.md#signalk-lint-no-rule-may-throw-on-malformed-input) — give every rule a garbage-input fixture.
- [ ] [Trim RUNBOOK's remaining prose-heavy sections](kanban-detail.md#trim-runbooks-remaining-prose-heavy-sections) — "Installing host files" is the best target.
- [ ] [Get GPS time off the N2K bus into chrony](kanban-detail.md#gps-time-off-the-n2k-bus-into-chrony) — SHM bridge or network feed; gpsd has no device.
- [ ] [Set source priorities for position once the AIS is powered](kanban-detail.md#set-source-priorities-for-position-once-ais-is-powered) — blocked: AIS not yet powered (physical task, tracked in Evernote).
- [ ] [Fix bt-sensors-plugin-sk's bus lifecycle and retire the dbus workaround](kanban-detail.md#fix-bt-sensors-plugin-sks-bus-lifecycle) — upstream to Mark's fork.
- [ ] [Add bt-sensors-plugin-sk to the watchdog's expectPlugins](kanban-detail.md#add-bt-sensors-plugin-sk-to-the-watchdogs-expectplugins) — watchdog is already deployed, just not watching this plugin.
- [ ] [Trim SignalK's ~45s startup time](kanban-detail.md#trim-signalks-45s-startup-time) — dead internet-speed/healthcheck/duplicate-plugin noise.
- [ ] [Add a fast barometric-pressure-drop notification](kanban-detail.md#fast-barometric-pressure-drop-notification) — trend data exists, no zone configured yet.
- [ ] [Bridge NMEA 2000 System Time to chrony](kanban-detail.md#bridge-nmea-2000-system-time-to-chrony) — PGN 126992 is on the bus, nothing reads it yet.
- [ ] [Verify Grafana SSO end to end](kanban-detail.md#verify-grafana-sso-end-to-end) — config is live, browser login never exercised.
- [ ] [Restore signalk-healthcheck's config to git](kanban-detail.md#restore-signalk-healthchecks-config-to-git) — needs add_inplace_secret.sh rewired for the mail-password field first.
- [ ] [Fix better-sqlite3 so signalk-polar can run](kanban-detail.md#fix-better-sqlite3-for-signalk-polar) — pin a newer version via override, or drop the plugin.
- [ ] [Evaluate the parked/unused SignalK plugins on the dev container](kanban-detail.md#evaluate-parkedunused-signalk-plugins-on-the-dev-container) — open-meteo works, signalk-questdb is misconfigured, three more unevaluated.
- [ ] [Add a weather term to ACTOR_HINTS in signalk_plugin_census.py](kanban-detail.md#add-a-weather-term-to-actor_hints) — open-meteo scores unmatched today.
- [ ] [Scope the COLREGs navigation-lights plugin](kanban-detail.md#scope-the-colregs-navigation-lights-plugin) — switches, condition input and warn-vs-switch are all still open.
- [ ] [Fork signalk-noaa-weather to filter alerts by vessel position](kanban-detail.md#fork-signalk-noaa-weathers-notification-behavior) — currently alarms on any NWS alert for the whole state.
- [ ] [Verify the heartbeat's soft-warning tier live](kanban-detail.md#verify-the-heartbeats-soft-warning-tier-live) — covered by mock tests only; real mem/disk haven't hit the warn band.
- [ ] [Watch unattended-upgrades over a few more cycles](kanban-detail.md#watch-unattended-upgrades-over-a-few-more-cycles) — confirm behavior before calling it settled.
- [ ] [Add data-source staleness to the heartbeat payload](kanban-detail.md#add-data-source-staleness-to-the-heartbeat-payload) — the one healthcheck gap nothing else covers.
- [ ] [Audit and fork signalk-pushover-notification-relay](kanban-detail.md#audit-and-fork-signalk-pushover-notification-relay) — or fall back to the Node-RED flow if it's beyond saving.
- [ ] [Research MOB detection options](kanban-detail.md#mob-detection-research) — never live-test the DSC emergency button, standing rule.
- [ ] [Remove the deprecated @signalk/zones plugin](kanban-detail.md#remove-the-deprecated-signalkzones-plugin) — mirror its zone meta into the boat's own baseDeltas first.

### Hardware design backlog
- [ ] [Sensor design backlog](kanban-detail.md#sensor-hardware-design-backlog) — engine temp/flow, rudder position, pump flow, air quality, pressure, illuminance, smart pump.
- [ ] [Autopilot hardware backlog](kanban-detail.md#autopilot-hardware-backlog) — pypilot, board design, separate IMU.
- [ ] [3D-print sensor enclosures](kanban-detail.md#3d-print-sensor-enclosures-backlog) — gas sensor, BME688, IMU cases.
