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
- [ ] Decide the critical-path list and age thresholds for Role 4's off-boat freshness check ([reference/monitoring_decisions.md](../../reference/monitoring_decisions.md) Role 4) — it's the designated owner of data-staleness and is unbuilt, so `signalk-healthcheck`'s single `n2k-can0` watch is holding the role while only alarming when the Pi is healthy enough to complain. Scoped at one script, reuses the live heartbeat + healthchecks.io plumbing; blocked only on which paths count as critical.
- [ ] [Purchase itemizations in maintenance/log.md](kanban-detail.md#purchase-itemizations-in-maintenancelogmd) — trim to one-line totals with detail moved to a purchases file, or keep as-is.
- [ ] Review and land the five open PRs, in this order: [#34](https://github.com/mark-brannan/symphony/pull/34), [#28](https://github.com/mark-brannan/symphony/pull/28), [#29](https://github.com/mark-brannan/symphony/pull/29), [#33](https://github.com/mark-brannan/symphony/pull/33), [#25](https://github.com/mark-brannan/symphony/pull/25) — all green, all mergeable, bot threads answered and resolved as of 2026-09-01; each PR body names the sections worth reading. #31 closed as superseded.
- [ ] [Rotate the Tailscale OAuth client credential](kanban-detail.md#rotate-the-tailscale-oauth-client-credential) — it was pasted into a session transcript; read-only scope, not urgent.
- [ ] [Decide dotfiles Google-connector parity](kanban-detail.md#dotfiles-google-connector-parity) — symphony denies three more connectors than dotfiles does; dotfiles-repo edit if wanted.
- [ ] [Check whether the dotfiles "hooks-continuity-cleanup" session's PR #3 still needs your two manual web-UI steps](kanban-detail.md#undelivered-coordination-note-to-the-hooks-continuity-cleanup-session) — last known state 2026-08-19; may already be resolved.

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
- [ ] **Decide the HALOS trial's known losses before the swap:** no GitHub/Google login (Authelia is file-based), no history before the swap; pypilot is plan item B4d (native install, IMU + web UI). Trial without them, or hold. Plan: [halos-swap-plan.md](halos-swap-plan.md).
- [ ] Do the sensitive-lane items S1–S3 in [halos-swap-plan.md](halos-swap-plan.md#hard-preconditions-sensitive-lane-not-this-plan) — WiFi PSKs to sops, heartbeat secrets file onto halos, salvage the old card's data once it is home. B2 and B4b block on S1 and S2.
- [ ] Check the boat's Victron MQTT link before the swap — `ss -tn | grep 8883` on `symphony-pi` showed `SYN-SENT`, not `ESTABLISHED`, on 2026-09-01; the trial needs a baseline.
- [ ] **Decide the rebuild fork: HALOS on a fresh 64 GB card, or keep hardening the current OpenPlotter install.** Grafana's return, the dockerization track and the SD-card strategy are all downstream of this one call. Evidence on 2026-08-25: a Node runtime swap silently removed `signalk-server`, the boat ran dark for 2 days, and OpenPlotter's own installer is what did it (`signalkPostInstall.py:45` runs `apt autoremove -y nodejs npm`). Against: HALOS undoes real work already done. Survey of `halos-pi4` (reachable as `ssh pi@halos-pi4`): Traefik + Authelia + Homarr core, containerised SignalK/QuestDB/Grafana/OpenCPN/AvNav, all systemd-managed, declarative config under `/etc/halos/` — architecturally where this repo was already heading, and it retires the "move off hand-rolled bash wrappers" item in `priorities.md` outright. Caveat: that box is a 2 GB Pi 4 with ~358 MB available under load, so HALOS implies the HALPI2.
- [ ] **The cellular WAN is the binding constraint — decide the staging plan around it.** Every rebuild failure on this boat is a network timeout, not a logic error. 2026-08-23: `docker pull signalk/signalk-server` died on TLS handshake timeout, `apt install grafana` (343 MB) timed out, `npm install` hit ETIMEDOUT. 2026-08-25: the SignalK reinstall ran 27 minutes and died on `EIDLETIMEOUT` from registry.npmjs.org, with single tarballs taking 54 s. `symphony-pi`'s tailscale endpoint is `172.56.x`, a T-Mobile range. Practical consequence: **the boat cannot be rebuilt in place over its own link** — a card staged and fully populated at home, then carried down, is the only reliable path.
- [ ] **Decide whether the current 32 GB card comes home after the swap.** It holds the only copies of `~/influx-export` (1.4 GB) and `~/keep-before-purge/grafana.db` — neither can cross the WAN without throttling risk, so a physical card swap is the only way to recover them.
- [ ] [Confirm the HALPI2 purchase](kanban-detail.md#halpi2-purchase-sd-card-boot-media-strategy) — already in cart; ends the SD-card/boot-media decision outright.
- [ ] [Decide whether to track openplotter.conf in git](kanban-detail.md#track-openplotteropenplotterconf-in-git-or-not) — its `soundignore` key is load-bearing and lives only on the boat.
- [ ] [Decide whether to pursue a read-only root filesystem](kanban-detail.md#read-only-root-filesystem-for-the-boat-pi) — real workflow change, not a config toggle.
- [ ] [Pick a journald SystemMaxUse size](kanban-detail.md#journald-cap-on-the-boat-pi) — measured 1.6 GB on 2026-09-02, already regrown past the 200 MB one-time vacuum; no `SystemMaxUse` set anywhere. Root fs 76% full.

## Claude's

### Infrastructure
- [ ] Coordinate with session `symphony-pr-33-review-601c06-0a` before touching the halos bench card, the boat's heartbeat/healthchecks config, or PR #33 — it owns the swap prep on 2026-09-02 (Mark's split in [handoff-halos-b3-session.md](handoff-halos-b3-session.md): that session has final say on PR #33 and big changes; the monitoring session owns monitoring posture and plugin-level detail). It created a second healthchecks.io check `SignalK Symphony (halos card)` so the bench card's pings cannot mask a boat outage while both run; the boat's check goes late on swap day — expected, pause it then.
- [ ] Build the HALOS card for the boat swap — items P1–P6 in [halos-swap-plan.md](halos-swap-plan.md#parallel-work-breakdown), one session each, dependencies marked there; P3 (SignalK state) and P1 (boot config) can start now.
- [ ] Run [PR #34](https://github.com/mark-brannan/symphony/pull/34) (`signalk-ble-check` on both cards) on the halos card once B3 lands, then merge it.
- [ ] File Mark's recovered physical-task list into Evernote and drop the boat stash — the connector is re-authorized and answering; `search_tasks "freshwater pump"` still returns nothing, and `stash@{0}: WIP on main: 54ef0e7` is still in place.
- [ ] Confirm after the swap that SignalK stays `healthy` in `docker ps` on the boat — on the bench the container healthcheck (60 s start window, 10 s timeout) lost the race against a 3–4 min cold start and `autoheal` restarted it every ~3 min. Fixed 2026-09-02 without touching the package-owned compose file: `/etc/container-apps/marine-signalk-server-container/symphony.override.yml` (start_period 900 s, timeout 30 s, 127.0.0.1) added via a systemd drop-in `marine-signalk-server-container.service.d/symphony.conf`; survives `apt upgrade`. Source of truth: `host/halos/` on PR #33 ([findings](halos-b3-findings-2026-09-02.md)).
- [ ] [Uninstall `signalk-to-influxdb2` on the boat](kanban-detail.md#uninstall-signalk-to-influxdb2-blocked-on-an-npm-tree-quirk) — still installed (`^2.2.0`) and erroring ~876 times/day. Card premise was wrong: InfluxDB was NOT purged — `influxdb2 2.9.1-1` is installed and active (boot-disabled); only `/var/lib/grafana` went. WAN is no longer the blocker (confirmed healthy 2026-08-26); a real `npm uninstall` now aborts on an unrelated tree quirk involving `signalk-plugin-watchdog`'s self-referencing `file:` dependency. No functional loss from the attempt, but the uninstall itself didn't land.
- [ ] Document the boat Pi's non-standard Node/npm state in `RUNBOOK.md` — `/usr/bin/node` is nsolid 22.23.2 (apt), the shadowing standalone 22.17.0 is parked at `/usr/local/bin/node.disabled-20260825`, `signalk-server` now lives in `/home/pi/.npm-global`, and `~/.signalk/signalk-server` was rewritten to match. None of this matches what the runbook currently describes.
- [ ] [Re-run the secret-tooling suite on a keyed machine (NucBoxK12) after pulling latest main](kanban-detail.md#confirm-secret-tooling-suite-on-a-keyed-machine) — closes the last leg of PR #19's TASK.
- [ ] [Sweep the stale claude/* branches, excluding the two rescued from the boat](kanban-detail.md#land-or-discard-three-held-claude-branches) — exclusion list was stale — `ecoworthy-signalk-telemetry-vy82ta` is already gone from the remote (verified 2026-09-02). Only `claude/symphony-pushover-setup-ce12i0` is deliberately kept. Triage: `archive-pi-plugins-recovery`, `claude/clarify-deployment-bullets-opwpv2`, `claude/grafana-questdb-port-target`, `claude/symphony-kanban-approach-bs9d08`.
- [ ] [Finish dockerizing the boat computer](../../reference/containerization_strategy.md) — Track B; SignalK, Grafana and Caddy are still native. Caddy last, done carefully — it's the front door.
- [ ] [Deploy the repo's Grafana provisioning to the boat](kanban-detail.md#deploy-the-repos-grafana-provisioning-to-the-boat) — blocked: Grafana was disabled and `/var/lib/grafana` purged on 2026-08-25; the hand-made dashboards survive only as `~/keep-before-purge/grafana.db` on the Pi. Whether Grafana returns natively or only in the dockerized/HALOS build is the fork below.
- [ ] [Build a host-health Grafana dashboard from Telegraf's existing metrics](kanban-detail.md#build-a-host-health-grafana-dashboard) — blocked: no Grafana on the boat since 2026-08-25. Queries were verified live and still apply; this is panels, not discovery, whenever Grafana comes back.
- [ ] [Put fail2ban (or equivalent) in front of sshd on the boat Pi](kanban-detail.md#rate-limit-sshd-on-the-boat-pi) — precautionary, not a response to anything measured.
- [ ] [Build the Ansible clock and watchdog roles](../../reference/host_provisioning.md) — smallest honest slice per the 2026-08-13 plan.
- [ ] [Extend `lint_repo_hygiene.py` with a soft warn on long log.md bullets](kanban-detail.md#doc-cleanup-follow-ups-still-open) — optional enforcement, from the 2026-08-19 bloat audit.
- [ ] [Set up a private repo for Vaultwarden before building off-machine hosting](kanban-detail.md#set-up-a-private-repo-for-vaultwarden-hosting).

### SignalK data & plugins
- [ ] [Assess PR #28's project-specific half](https://github.com/mark-brannan/symphony/pull/28) — the global part landed in dotfiles already; decide whether symphony needs its own `maintenance/stats.md`, `stats-data.json`, `.claude/hooks/measure-cherry-pick.sh` and the CLAUDE.md no-cherry-pick rule, or whether the dotfiles copy covers it. Keep the PR open either way — do not delete.
- [ ] Carry [PR #29](https://github.com/mark-brannan/symphony/pull/29)'s OIDC identity-permissions work upstream — implementation is on [the fork branch](https://github.com/mark-brannan/signalk-server/tree/oidc-identity-permissions) behind [fork PR #1](https://github.com/mark-brannan/signalk-server/pull/1); next step is opening the conversation with Matti Airas (Hat Labs) on the SignalK Discord before an upstream PR. Mark intends to pursue this; not top priority.
- [ ] [Deploy the openweather-signalk humidity-fix Node-RED flow](kanban-detail.md#deploy-the-openweather-signalk-humidity-fix-flow) — needs boat access; flow is built but unverified in the live editor.
- [ ] [Add signalk-lint batch 2 (host-level rules)](kanban-detail.md#signalk-lint-batch-2-host-level-rules) — can0/gpsd/systemd/cron/journald faults this boat actually hit.
- [ ] [Make "no rule may throw on malformed input" a stated signalk-lint convention](kanban-detail.md#signalk-lint-no-rule-may-throw-on-malformed-input) — give every rule a garbage-input fixture.
- [ ] [Trim RUNBOOK's remaining prose-heavy sections](kanban-detail.md#trim-runbooks-remaining-prose-heavy-sections) — "Installing host files" is the best target.
- [ ] [Bridge NMEA 2000 System Time (PGN 126992) to chrony](kanban-detail.md#gps-time-off-the-n2k-bus-into-chrony) — SHM bridge or network feed; gpsd has no device, so the boat has a GPS clock it can't use yet.
- [ ] [Set source priorities for position once the AIS is powered](kanban-detail.md#set-source-priorities-for-position-once-ais-is-powered) — blocked: AIS not yet powered (physical task, tracked in Evernote).
- [ ] In detail, walk Mark through the additional commit on our fork of bt-sensors-plugin-sk for 'Lazy D-Bus connection with reconnect-on-error' noting plan to get us off of forked (manually installed plugin) and (if needed) get this commit into the upstream via PR.
- [ ] Tune the shared-checkout warning gate in `.claude/hooks/warn-shared-checkout.sh` — warns every turn (deliberately) when writing in `/home/solace/symphony` while it is behind `origin/main` or holds uncommitted paths. Built 2026-08-27 after prose alone failed to prevent the 2026-08-26 near-revert; the two risk conditions are a first try, not a settled design — change them if it nags wrongly or stays quiet when it shouldn't ([log](log.md#2026-08-26--symphony-pi-npm-install-failure-and-a-shared-checkout-near-miss)).
- [ ] [Trim SignalK's ~45s startup time](kanban-detail.md#trim-signalks-45s-startup-time) — dead internet-speed/healthcheck/duplicate-plugin noise.
- [ ] [Add a fast barometric-pressure-drop notification](kanban-detail.md#fast-barometric-pressure-drop-notification) — trend data exists, no zone configured yet.
- [ ] [Verify Grafana SSO end to end](kanban-detail.md#verify-grafana-sso-end-to-end) — config is live, browser login never exercised.
- [ ] [Restore signalk-healthcheck's config to git](kanban-detail.md#restore-signalk-healthchecks-config-to-git) — needs add_inplace_secret.sh rewired for the mail-password field first.
- [ ] [Fix better-sqlite3 so signalk-polar can run](kanban-detail.md#fix-better-sqlite3-for-signalk-polar) — pin a newer version via override, or drop the plugin.
- [ ] [Evaluate the parked/unused SignalK plugins on the dev container](kanban-detail.md#evaluate-parkedunused-signalk-plugins-on-the-dev-container) — open-meteo works, signalk-questdb is misconfigured, three more unevaluated.
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
