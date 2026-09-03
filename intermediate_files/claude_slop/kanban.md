# Symphony — open loops

This is symphony's board under the global "Open loops" rule: one line per
card, imperative, always linked; cards die when done, not archived here — see
`log.md` and `git log` for history. `## Yours` is calls only Mark can make
(decisions, purchases, physical/account access). `## Claude's` is work a
session can pick up and execute. Full working detail behind a card lives in
`kanban-detail.md`, or at an existing reference doc / open PR when one
already carries enough context.

## Standing context — not cards, not decisions to make

**The test before carding a decision for Mark: does anything on a session's
side actually hinge on the answer?** If the work proceeds either way and a
session just updates the docs afterwards to match what he chose, it is not a
card — it is context, and it belongs in this section. Carding a decision
Mark will reach independently, on his own timeline, spends his judgment on a
question that was never blocking. Established 2026-09-02 after three such
cards (the rebuild fork, the WAN, the HALPI2) were pulled off his board.

- **HALOS is an experiment; its output is learning, not a commitment.**
  Whether the boat ends up on HALOS or on a hardened OpenPlotter install is
  deliberately unsettled and stays that way. Sessions carry that ambiguity
  rather than resolving it: don't card it, don't ask Mark to settle it, and
  don't treat the swap plan, the bench card or any PR as evidence the fork
  is closed. Work the trial on its merits and let the long-run answer come
  from what the trial teaches. The evidence on both sides, which is still
  worth reading before touching this track, is in
  [kanban-detail.md](kanban-detail.md#the-rebuild-fork--strategic-context).

- **The cellular WAN is a working constraint, not a task.** Every rebuild
  failure on this boat is a network timeout, not a logic error: `docker pull
  signalk/signalk-server` died on a TLS handshake timeout and `apt install
  grafana` (343 MB) timed out on 2026-08-23; the SignalK reinstall ran 27
  minutes and died on `EIDLETIMEOUT` from registry.npmjs.org on 2026-08-25,
  with single tarballs taking 54 s. `symphony-pi`'s tailscale endpoint is a
  T-Mobile range. The practical consequence is permanent: **the boat cannot
  be rebuilt in place over its own link.** A card staged and fully populated
  at home, then carried down, is the only reliable path — and large data
  moves off the boat go by physical card, not over the wire. Assume this in
  every plan; it does not need re-deciding or re-discovering.

- **The HALPI2 is a probable maybe.** It is in the cart, Mark will decide
  independently, and nothing on a session's side is blocked either way. If it
  arrives, add it to the hardware list in the reference docs; if it doesn't,
  don't. The only thing worth knowing is why it keeps coming up: the bench box
  is a 2 GB Pi 4 sitting at ~358 MB available under load, so anything
  container-heavy on that hardware is memory-bound.

## Yours

### Repo & tooling
- [ ] **When you are next at the boat with the new card, launch [dispatch-halos-swap-day.md](dispatch-halos-swap-day.md)** — a ready-to-paste prompt, no date to pick and nothing scheduled against it. PR #33 is merged and the bench card passes every preflight line after a reboot; the open items that want doing first are the Cerbo power-cycle below and pypilot on Claude's side.
- [ ] Decide the critical-path list and age thresholds for Role 4's off-boat freshness check ([reference/monitoring_decisions.md](../../reference/monitoring_decisions.md) Role 4) — it's the designated owner of data-staleness and is unbuilt, so `signalk-healthcheck`'s single `n2k-can0` watch is holding the role while only alarming when the Pi is healthy enough to complain. Scoped at one script, reuses the live heartbeat + healthchecks.io plumbing; blocked only on which paths count as critical.
- [ ] [Purchase itemizations in maintenance/log.md](kanban-detail.md#purchase-itemizations-in-maintenancelogmd) — trim to one-line totals with detail moved to a purchases file, or keep as-is.
- [ ] Resume the live dashboard walkthrough — Navstation done, 5 to go (Electricity, System health, Navigation, Weather, Life support). [PR #25](https://github.com/mark-brannan/symphony/pull/25) landed on main 2026-09-02, so this now continues **on main**, not on that branch. State and what's still open: [log.md#2026-09-01/02 — PR #25 live walkthrough, session 1 of N](log.md#2026-09-0102--pr-25-live-walkthrough-session-1-of-n-navstation-only). Demo stack is left running at localhost:3100 (admin/devadmin) in worktree `grafana-dashboards-pr25-89c9f8`.
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
- [ ] **Power-cycle the Cerbo GX at the panel** (DC feed off ~30 s), then confirm Settings → Services → MQTT on LAN (SSL) is still on; if it stays dark it is a failed unit, not a config problem. Re-checked from the boat 2026-09-02: no ICMP reply and 80/443/1883/8883/22 all closed, but ARP for `5c:c5:63:0a:df:52` is `REACHABLE` — the NIC answers, nothing above it does. SignalK's Victron client is still in SYN-SENT to 192.168.8.107:8883 since 2026-09-01 21:06Z; Victron data is dead on both cards until then ([execution file](halos-swap-execution-2026-09-02.md)).
- [ ] **Bring the 32 GB card home once the swap succeeds** (decided 2026-09-02; conditional on a successful swap — if it fails the card goes back in the boat). It holds the only copies of `~/influx-export` (1.4 GB) and `~/keep-before-purge/grafana.db`, neither of which can cross the WAN. Copy those and the `symphony_questdb-data` volume off before the card is reused (plan S3 / P7).
- [ ] [Decide whether to track openplotter.conf in git](kanban-detail.md#track-openplotteropenplotterconf-in-git-or-not) — its `soundignore` key is load-bearing and lives only on the boat.
- [ ] [Decide whether to pursue a read-only root filesystem](kanban-detail.md#read-only-root-filesystem-for-the-boat-pi) — real workflow change, not a config toggle.

## Claude's

### Infrastructure
- [ ] Confirm containerized pypilot on `symphony-pi` survives a reboot — cut over 2026-09-03 (native disabled, container `restart: unless-stopped`), but that policy has never been exercised through an actual host reboot. Check `docker ps` shows `pypilot`/`pypilot-web` `Up` after the next reboot the boat takes for any reason; if not, `RUNBOOK.md` § "Cut the boat over" has the rollback.
- [ ] **`docker-compose.override.yml` is deployed to the boat, where its own header says it must not be.** It is the dev-box-only file that mounts `dev/plugin-config-overrides/` over SignalK's plugin configs. Compose loads it automatically with no `-f` flag, so it is now in all three boat containers' `com.docker.compose.project.config_files`. Inert today — it defines only the `signalk` service and the boat runs SignalK natively — but it arms itself the day anyone containerises SignalK there, and it would mount dev plugin configs over the real ones with nothing to say why. Found 2026-09-02 while adding container healthchecks; pre-existing and out of that change's scope, so left alone. Fix is probably to move its contents into a `dev`-profiled file or an explicitly-named `-f`, not to delete it.
- [ ] Capture the SignalK-state hand changes that Ansible deliberately does not own — native-module rebuild recipe, `node_modules` reinstall, the four `"enabled": false` edits, ntfy `.env` values ([halos-b3-findings-2026-09-02.md](halos-b3-findings-2026-09-02.md)). The heartbeat URL, zram config, `hostnames.conf` body and the card's repo checkout are now in `ansible/` ([halos-build-v2-asbuilt.md](halos-build-v2-asbuilt.md)); these four are the remainder, and per `reference/host_provisioning.md` they belong in a documented script, not a role.
- [ ] Delete the stray file on main whose name is a mangled Python heredoc (`", d[enabled])\nw=os.path.join(...` — one tracked file at the repo root, from a session's broken `python3 - <<EOF`). Confirm with `git ls-files | grep 'd\[enabled\]'` before removing; nothing references it.
- [ ] Run `scripts/dev_stack.sh up` end to end once, on a box where 3001/8086/9000/9009/8812 are free. PR #25's QuestDB wait and panel-check guards were verified in isolation (a throwaway QuestDB on 19000, and cmd_up with a stubbed failing verify), but the Grafana-through-PGWire leg — 171 panels actually drawing off the seeded QuestDB — has never been exercised. On this WSL box those five ports are held by `influxdb` and `sk-signalk-questdb`, so bringing the compose project up would have collided with them and `down -v` would have aimed at their volumes.
- [ ] Place `host/halos/traefik-symphony-signalk-host.yml` from Ansible — the other two `host/halos/*` files are now placed by `ansible/roles/signalk_container`; the Traefik router is still by hand because it sits in the "Other containers" layer that plan v2 left out ([halos-build-v2-asbuilt.md](halos-build-v2-asbuilt.md) step 35).
- [ ] Teach `host/install.sh` to place `host/halos/*` on a HALOS card (container unit detected per PR #34's `signalk-unit.sh`) — today they are installed by hand per `host/halos/README.md`.
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
- [ ] Port `host/install.sh`'s contents into the `clock`, `watchdog`, `monitoring` and `claude-resident` roles [reference/host_provisioning.md](../../reference/host_provisioning.md) — `ansible/` exists and `roles/host_files` invokes the installer whole; this is the slice that starts shrinking it. Its `INSTALL` array maps to `copy`, `RESTART`/`ENABLE` to handlers and `systemd`, `CRON` to `cron`.
- [ ] Build a genuinely fresh Pi 4 card with `ansible-playbook site.yml` — every run so far converged a card that v1 had already built by hand, which proves the playbook describes the card but not that it can create one. Untested on that path: the reboot handler (never fired), the apt repo and package installs, purging an absent InfluxDB app, and a clone rather than a pull ([halos-build-v2-asbuilt.md](halos-build-v2-asbuilt.md) § Not done in v2).
- [ ] Delete the local branch `salvage/ansible-partial-checkout` on `symphony-halos` (`/home/pi/symphony`, commit `a6ea802`) — a partially-staged tree preserved rather than discarded when an Ansible checkout failed on root-owned refs 2026-09-02. Never pushed; its content is exactly [PR #38](https://github.com/mark-brannan/symphony/pull/38)'s tree, so it is reproducible.
- [ ] Replace `ansible.builtin.apt_repository` before ansible-core 2.25 removes it — `deb822_repository` writes `influxdata.sources` rather than the `influxdata.list` both cards carry, so it needs a deliberate migration, not a swap. The warning prints on every run, deliberately — that is the reminder.
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
