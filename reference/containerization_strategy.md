# Containerization strategy

Decision record and plan, researched 2026-08-18. Companion to
[compute_hardware.md](compute_hardware.md) (the hardware and its HALPI2
target), [software_stack.md](software_stack.md) (the current stack) and
[monitoring_decisions.md](monitoring_decisions.md) (whose Role 3 this
partially overturns). Claims are tagged **[verified]** (source named,
fetched or measured during this research) or **[unverified]** (plausible,
not checked — confirm before relying on it).

Source caveat: GitHub-sourced claims (halos-org, questdb, dirkwa), the npm
registry API and the Docker Hub API are solid; vendor blog and docs claims
are snippet-level, taken from search results rather than the pages
themselves.

## Decisions made with Mark, 2026-08-18

1. **Trial HALOS before committing to it.** Build it on the spare Pi 4 at
   home with the spare 64 GB SD card; adopt or reject after seeing it run.
2. **Two tracks in parallel**: the HALOS trial at home *and* continued
   in-place containerization on the boat Pi. Calculated risk to the live
   system is acceptable.
3. The end state is one of four quadrants, deliberately not chosen yet:
   (A) HALOS on HALPI2, (B) HALOS on custom hardware (PiCAN-M Pi or
   other), (C) custom container stack on HALPI2, (D) custom container
   stack on custom hardware. No HALPI2 is owned and its purchase is
   undecided.
4. **InfluxDB history: back up offline, then free to drop.** Verify the
   backup off-boat first; after that, dropping InfluxDB is authorized.
5. **OpenPlotter is dropped at rebuild.** Its two live functions get
   replaced deliberately: pypilot runs standalone, and the BME680 moves to
   the dedicated SignalK plugin (installed on both boxes, currently
   disabled).

The strategic consequence of quadrant thinking: **prioritize work that is
identical in all four quadrants** (QuestDB migration, plugin curation,
host-layer Ansible, monitoring plumbing) and **defer work that only pays
in one** (more Dex/Caddy glue pays only in C/D; HALOS-specific config
pays only in A/B).

## Critical review: which prior conclusions survive

Re-examined per Mark's request, taking nothing in
`monitoring_decisions.md` or `software_stack.md` for granted.

**Overturned — "keep InfluxDB; the QuestDB choice can wait for the
rebuild machine"** (monitoring_decisions.md Role 3, priorities.md). Three
independent grounds:

- InfluxDB 2.x is a strategic dead end. Flux is in maintenance mode and
  dropped from InfluxDB 3; InfluxData's direction is v3; the Docker Hub
  library notice reads "On September 15, 2026, the latest tag for InfluxDB
  will point to InfluxDB 3 Core." As of 2026-08-19 that repoint has not
  happened — `influxdb:latest` and `influxdb:2` resolve to the same digest
  (`sha256:2701452078…`, currently 2.9.1), while `influxdb:3-core` is a
  different one. The repo's pin to `influxdb:2.7` in
  `compose-influxdb.yml` dodges the trap either way
  **[verified — Docker Hub registry API, tag digests compared
  2026-08-19]**.
- The marine ecosystem's center of gravity moved, fast. `signalk-questdb`
  (Dirk Wahrheit) has shipped 46 versions since April 2026, latest
  2026-08-17; Hat Labs forked it on 2026-08-16 as
  `signalk-questdb-history-provider` ("a drop-in replacement for
  signalk-to-influxdb and signalk-to-influxdb2"), stripped of container
  management, and HALOS Marine commits of 2026-08-16/17 make QuestDB the
  tracked default history provider with a provisioned Grafana datasource
  **[verified — github.com/halos-org/signalk-questdb-history-provider,
  halos-marine-containers commit log, npm registry]**.
- The boat's InfluxDB was never really settled anyway: every sops token
  401s, the org disagrees with `.env.j2` (`symphony` vs `darkstarllc`),
  retention disagrees between `.env.j2` and `provision_influxdb.sh`, and
  the only working credential is captain's all-access token
  **[verified — priorities.md items, re-read this session]**. There is no
  managed install to preserve — re-provisioning InfluxDB properly costs
  about what standing up QuestDB costs.

The deciding argument for doing it *now* rather than at rebuild: QuestDB
is the one history store that appears in **all four quadrants** (HALOS
ships it; our compose can run it), so the migration — data export, plugin
swap, dashboard ports — is quadrant-invariant work that cannot be wasted.
Waiting means running a dead-end database for months and then doing the
same migration under rebuild pressure.

**Survives — Telegraf.** Re-checked against 2026 alternatives rather than
assumed: Telegraf is the one mainstream collector whose native metrics
format *is* InfluxDB line protocol, which QuestDB ingests directly — the
stock `outputs.influxdb_v2` output pointed at `http://localhost:9000`
with `content_encoding = "identity"`, per QuestDB's own docs; it can
dual-write to both DBs during migration by adding a second output block
**[verified — QuestDB Telegraf docs via search]**. QuestDB has no native
agent and points at Telegraf. Vector needs ≥256 MB disk buffers and has
an open metric-loss-when-offline issue; Fluent Bit is log-first; netdata
is pull/dashboard-shaped and heavier; node_exporter needs a scraper
**[verified — vendor docs and benchmarks, sources in research notes]**.
So "Telegraf stays" is now a conclusion, not an inheritance. Its
captain-token stopgap dies with InfluxDB: QuestDB on localhost needs no
token at all.

**Survives — the alarm-path architecture.** Nothing here touches Roles 1,
2 or 4 of monitoring_decisions.md: heartbeat + healthchecks.io, the
notification bus, ntfy, Pushover, the plugin watchdog. All of it is
DB-independent and quadrant-invariant. The forensics store must stay
alarm-free in the QuestDB era for the same release-valve reason.

**Partially overturned — "Docker finishes on the machine that replaces
this Pi"** (software_stack.md). Already stale in practice (Docker 29 runs
on the boat; Dex and ntfy are containers), and Mark has now explicitly
accepted calculated in-place risk. The constraint that motivated it — 2 GB
of images against ~6 GB free — was re-checked: 9.2 GB free after the
08-14 cleanup, and dropping InfluxDB's store and Chromium's profile
frees more.

**HALOS as of 2026-08-18.** The project has moved
to its own GitHub org (`halos-org`, 31 repos), releases images roughly
monthly (v2026-03-03 … v2026-08-10.1), and ships **generic Pi 4/5
images** (`Halos-Marine-RPI` et al.), not just HALPI2 variants; it can
also be layered onto an existing Raspberry Pi OS **Trixie** install via
APT (`apt install halos-marine`) — explicitly untested on Bookworm, so
layering it onto the boat's current card is not an approved path until
someone validates it (Track A is where that would happen, not the boat).
Architecture today: Raspberry Pi OS Lite arm64 base; apps are Docker
containers wrapped as Debian packages from `apt.halos.fi`; Traefik +
**Authelia** (ForwardAuth + native OIDC) for SSO; Cockpit for admin;
Homarr dashboard; path-based routing (`https://halos.local/grafana/`),
the subdomain scheme having been dropped for Windows-mDNS reasons.
Marine app store: signalk-server, grafana, influxdb, questdb, avnav,
opencpn; 144 auto-converted CasaOS apps including Node-RED; **no ntfy
package found**. An **official OpenPlotter→HALOS migration guide with
backup/restore scripts** covers SignalK, InfluxDB, Grafana and OpenCPN.
Still self-described as beta and not feature complete: Let's Encrypt
TLS, 2FA, automated backup and OTA updates are roadmap items; TLS today
is a self-signed device CA **[all verified —
github.com/halos-org/{halos,halos-pi-gen,
halos-marine-containers,halos-imported-containers,docs}, read
2026-08-18]**.

**Never proven, treat accordingly — the repo's "golden config."** The
compose stack has run on dev machines (including under WSL/Docker
Desktop, a different failure domain), never end-to-end on the boat. Each
service migration on the boat is a first deployment, not a replay.

**The unpriced switching cost — the dashboards.** There are two distinct
dashboard sets, and they are not versions of each other:

- **The boat's native Grafana: five dashboards, 76 panels, InfluxQL
  almost throughout** (Electricity 19, Navstation 22, Navigation 12, Life
  support 12, Weather 11), imported from published examples, with 158 of
  162 panel datasource references pointing at a uid that does not exist on
  that Grafana **[verified — legacy_openplotter_stack.md, measured
  2026-08-14]**.
- **The repo: six dashboards, generated, Flux throughout** — `electricity`,
  `life-support`, `navigation`, `navstation`, `system`, `weather` under
  `grafana/provisioning/dashboards/json/`, build output of
  `scripts/build_dashboards.py` against the paths this boat actually
  publishes, all referencing uid `influxdb-symphony`. Every query is
  `from(bucket: …)`; there is no InfluxQL in them
  **[verified — files read and commit 1ce4e87 "grafana: rebuild dashboards
  against paths this boat actually publishes", 2026-08-14]**.

Which of these is the porting target for QuestDB is **not decided** —
see the Blocked item in `maintenance/priorities.md`. What is certain
either way: QuestDB serves Grafana over PGWire/SQL, so neither Flux nor
InfluxQL transfers, and this is the single largest chunk of real work in
the DB swap. Partial offsets: the retired `signalk-grafana` plugin's
auto-built QuestDB dashboards are preserved in
`signalk/plugin-config-data/signalk-grafana/grafana-data/`, and the
compose Grafana already preinstalls the QuestDB datasource plugin
**[verified — compose-grafana.yml]**. Plan it as its own step, not
something discovered mid-cutover.

**Two committed-config traps found this session** (fix during the
migration): the tracked `signalk-questdb.json` sets `retentionDays: 0` —
infinite retention, which on SD-card storage is a decision nobody made —
and `signalk-container.json` sets `backgroundUpdateChecks: true`, which
software_stack.md itself argues should be off while the docker-socket
mount makes plugin code the security boundary. Better: the external-mode
plugin path below removes the socket-mount requirement entirely.

## Open questions the HALOS trial must answer

- **SSO federation.** Symphony's Dex federates login to GitHub/Google;
  Authelia's user DB is file-based local accounts
  **[verified — halos docs architecture/sso.md]**. Whether Authelia can
  federate upstream, or HALOS can run Dex behind Traefik, or local
  accounts are acceptable aboard, decides how much of the Dex work
  survives quadrants A/B. **[unverified — needs the trial]**
- **Bring-your-own containers.** HALOS FAQ: standalone containers work
  but don't appear in the dashboard. How well our compose services (ntfy,
  anything custom) coexist with its Traefik and its APT lifecycle needs
  hands-on time. **[verified FAQ claim; implications unverified]**
- **State portability.** Whether the boat's `signalk/` state directory
  (settings, plugin configs, security.json) drops into HALOS's
  signalk-server container (app data lives under
  `/var/lib/container-apps/<pkg>/data/`) or needs the migration scripts'
  restore path. **[unverified]**
- **Host metrics.** No evidence HALOS has a host-metrics story; Telegraf
  writing ILP to its QuestDB app should work regardless.
  **[unverified]**
- **Real-domain TLS.** HALOS TLS is a self-signed device CA and Let's
  Encrypt is roadmap; Symphony's OAuth flow requires HTTPS on a real
  domain. Whether our Caddy/Cloudflare front door can sit in front of or
  beside Traefik matters for A/B. **[unverified]**

## The plan

Ordered, high level. Track A and Track B run in parallel; B's steps are
sequential. Every boat step follows the existing session rules: announce
release-valve stops, respect the memory thresholds, explicit-pathspec
commits.

### Track A — HALOS trial at home (spare Pi 4, 64 GB card)

- **A1.** Flash the current `Halos-Marine-RPI` image from
  `halos-org/halos-pi-gen` releases to the 64 GB card; boot on the spare
  Pi 4. (The spare Pi 5 is an alternative host, but the Pi 4 matches the
  boat's hardware class and answers the performance question that
  matters. Do not plan quadrant D around PiCAN-M-on-Pi-5 without checking
  HAT compatibility — **[unverified]**.)
- **A2.** Exercise the product: app store installs of signalk-server,
  questdb, grafana; the Authelia/Traefik login flow; Cockpit; the
  apt-driven update flow; a backup/restore cycle of
  `/var/lib/container-apps`.
- **A3.** Answer the open questions above, especially SSO federation and
  state portability — try mounting a copy of the boat's `signalk/` state
  (with secrets handled per the repo's rules) into its SignalK container.
- **A4.** Write the verdict into this file: adopt HALOS (quadrants A/B),
  reject (C/D), or adopt-with-exceptions (e.g. HALOS plus our Caddy for
  real-domain TLS). This is the decision gate for the SSO and proxy work,
  so until A4, **stop investing in Dex/Caddy beyond keeping them
  running**.

### Track B — the boat, in place

- **B1. Back up InfluxDB offline.** Two artifacts, both taken and copied
  off-boat, then verified: a raw copy of the data directory (bolt +
  engine, taken with `influxd` stopped), and a line-protocol export via
  `influxd inspect export-lp` — which reads engine files directly and
  **needs no token**, sidestepping the 401 problem. Also export the boat
  Grafana's five dashboards as JSON and its datasource definition; the
  repo's generated six are already tracked and are a different set (see
  the dashboards section above).
  **Verification means recoverability, not archive integrity.** Listing a
  tarball and line-counting a gzip proves neither restores. Off-boat,
  restore into a disposable InfluxDB 2.7 container and query it: the
  bucket exists, the expected measurements are present, and a spot-check
  query returns values matching the boat for a known window. `influx
  backup`/`influx restore` is the supported flow but 401s on this boat's
  tokens, so the practical path is the raw data directory mounted into the
  throwaway container, with the `.lp.gz` replayed via `influx write` as
  the cross-check. Only after that query succeeds is the drop
  authorization from the decisions above active. Details in the checklist
  below.
- **B2. Stand up QuestDB as a compose service on the boat.** New
  `compose-questdb.yml`: pinned `questdb/questdb` version (arm64
  official **[verified — Docker Hub API]**), ports 9000/9009/8812 bound
  to localhost, named volume, container memory limit ~768 MB (the marine
  plugin's own Pi default **[verified — dirkwa/signalk-questdb
  README]**). Put it on `symphony-net` with the rest of the stack. This is
  also the boat's third container, extending the Dex/ntfy pattern rather
  than inventing one.
  **Endpoints depend on where the client runs.** Native clients on the Pi
  (today's SignalK, Telegraf, native Grafana) reach it at `localhost:9000`
  / `:8812` via the published ports. Clients that are themselves compose
  services reach it at `questdb:9000` / `questdb:8812` — inside a
  container `localhost` is that container. This is the same trap
  `compose-grafana.yml` already documents for InfluxDB with
  `host.docker.internal`; each of B3, B4 and B6 crosses that boundary and
  has to switch the endpoint when it does.
- **B3. Swap the SignalK history plugin.** Install Hat Labs'
  `signalk-questdb-history-provider` (external-DB-only fork — no
  `signalk-container`, no docker socket) pointed at localhost, or
  dirkwa's `signalk-questdb` in external mode (`managedContainer:
  false`) if the fork isn't on npm yet **[unverified — check]**. Set a
  finite retention. Run it alongside `signalk-to-influxdb2` for a short
  soak (days); Telegraf dual-writes via a second `influxdb_v2` output to
  `:9000`. Mind the npm-prune hazard in the checklist.
- **B4. Port the dashboards.** Stand the compose Grafana up against
  QuestDB (PGWire datasource; QuestDB datasource plugin already
  preinstalled per `compose-grafana.yml`, reached at `questdb:8812` from
  the container). **Settle the two-set question first** — the repo's
  generated six or the boat's legacy five, per the Blocked item in
  `priorities.md`; the work is materially different (teaching
  `build_dashboards.py` to emit SQL vs. hand-porting 76 imported panels)
  and doing it in the wrong one is the wasted-effort risk in this whole
  plan. Seed from the auto-built QuestDB dashboards where they overlap.
  Native Grafana keeps running until the container's dashboards are
  usable; then stop and disable the native `grafana-server` (a deliberate
  disable is the point here — get Mark's explicit go-ahead in-session, per
  the stop-don't-disable rule).
- **B5. Retire InfluxDB.** The gate is measured parity, not "looks
  right." Before anything is disabled, with both writers still running:
  every SignalK path `signalk-to-influxdb2` writes has a corresponding
  QuestDB table; every Telegraf host-metric measurement does too; over the
  same soak window the row counts agree with each other within what the
  configured sampling rates predict; the timestamp ranges have no gaps
  QuestDB has and InfluxDB doesn't; a spot-check of representative values
  (a battery voltage, a position, a CPU temperature) matches within
  float tolerance; and SignalK and Telegraf logs show no write errors to
  QuestDB. **Rollback criterion:** any of those failing means QuestDB is
  not ready — fix and re-soak; InfluxDB stays enabled meanwhile, which is
  why it is not disabled until after the checks pass. Then: disable
  `signalk-to-influxdb2`, stop and disable `influxdb.service`, remove
  Telegraf's InfluxDB output (and with it the captain-token stopgap),
  and reclaim the ~300+ MB store. The sops cleanup (dead influx tokens,
  `INFLUX_*` in `.env.j2`, `provision_influxdb.sh`) follows, as does
  updating monitoring_decisions.md Role 3 and software_stack.md's
  two-paths section.
- **B6. Containerize SignalK.** The big one, and the one that kills the
  fragile `~/.signalk` npm tree (dual installs, `package-lock=false`,
  103-plugin re-resolution) by replacing it with a container whose plugin
  set installs fresh from the committed manifest. Prerequisite:
  **curate the plugin list first** — reconcile the boat's installed set
  against `signalk/package.json`, decide the parked/broken ones
  (signalk-polar, aisreporter, solar-forecast, saillogger orphan, the
  deprecated zones plugin), and land hand-installed locals
  (signalk-plugin-watchdog) properly. Native SignalK stays installed and
  stopped as instant rollback. The serial/CAN devices (`can0`,
  `/dev/serial0`) pass through to the container; verify the N2K provider
  and the `uniqueNumber` NAME pin survive the move.
  **Drop the Docker socket as part of this step.** The tracked
  `compose-signalk.yml` today mounts `/var/run/docker.sock` and carries
  `group_add: ["1001"]` (the host docker GID) — together that gives any
  SignalK plugin host-level Docker control, which is exactly the security
  boundary the external-mode history plugin was chosen to remove. Both
  lines exist only for `signalk-container`, which B3 retires. Delete the
  volume mount and the `group_add` block in the same change, and verify on
  the running container that neither survived: `docker inspect
  signalk-server` shows no `docker.sock` bind and no supplementary group,
  and `docker exec signalk-server docker ps` fails. Removing the plugin
  without removing these leaves the hole open with nothing using it.
- **B7. Caddy last.** Front door only after everything behind it is
  stable in containers; when it moves, drop the transitional
  `127.0.0.1:5556` Dex publish per the existing priorities note. If
  Track A ends in HALOS adoption, B7 may be skipped entirely in favor of
  the cutover below.

### Convergence — the decision gate and cutover

- **C1.** With A4's verdict and the HALPI2 purchase decision, pick the
  quadrant. What Track B built is *expected* to transfer either way —
  QuestDB data and dashboards (HALOS ships the same DB and Grafana), the
  curated plugin manifest, Telegraf config, the monitoring plumbing — but
  treat dashboard portability as a claim to test, not a given: HALOS
  migrates custom dashboards best-effort and its own built-ins are
  InfluxDB-shaped. Don't pick a quadrant on the strength of dashboard
  portability until B4's panels have been validated against QuestDB *and*
  restored onto a HALOS instance in Track A with its datasource
  provisioning intact.
- **C2.** Capture the host layer in Ansible per
  [host_provisioning.md](host_provisioning.md) — clock, watchdog, can0,
  RTC when fitted — which is what makes the final machine build
  repeatable regardless of quadrant.
- **C3.** Cutover: for HALOS quadrants, the official migration scripts
  (SignalK + Grafana; InfluxDB by then is empty) plus our Ansible host
  layer; for custom quadrants, fresh OS + Ansible + compose. Either
  way OpenPlotter is not reinstalled: pypilot standalone, BME680 via the
  dedicated plugin, and the openplotter-* packages stay behind on the
  retired card, which remains the rollback medium.

### Answers to the two direct questions

- **"Drop OpenPlotter and full-reinstall a new SD card with HALOS?"**
  Yes to the reinstall — but on the spare Pi at home first (Track A),
  not on the boat. The boat keeps its working card until the decision
  gate; its cutover then reuses whatever Track A proved, and OpenPlotter
  is dropped at that point (decision 5).
- **"Dump InfluxDB 2 and run more containers now?"** Yes to both, in the
  B1→B5 order: backup first, QuestDB and Grafana as containers next,
  InfluxDB retired after the soak. Not because the current install is
  about to fail, but because InfluxDB 2.x is a platform dead end, the
  boat's install was never coherently provisioned, and the QuestDB work
  is the one investment all four end states share.

## Boat-side investigation checklist

A one-shot plan, not a procedure: it lives here rather than in RUNBOOK.md
because it runs once and then gets deleted from this file, its findings
folded into the decisions above. Written for whoever is next on a tailnet
machine (`ssh pi@symphony-pi`), in order. Semi-destructive items are
marked; Mark has pre-authorized them, except where a line says otherwise.

1. **State snapshot (read-only).** `free -m`, `grep ^pswp /proc/vmstat`,
   `df -h /`, `docker ps -a`, `systemctl status influxdb grafana-server
   signalk telegraf caddy`. Abort the destructive items if the box is
   under real memory pressure.
2. **Find the InfluxDB paths (read-only).** `systemctl cat influxdb` and
   `influxd print-config 2>/dev/null | grep -Ei 'engine|bolt'` — the
   Debian layout is expected to be `/var/lib/influxdb/` **[unverified —
   confirm, don't assume]**. Record store size with `du -sh`.
3. **Backup (announce; stops services briefly).** Stop Grafana first if
   memory is tight (release-valve rule — say so in session).
   `systemctl stop influxdb`, then tar the data directory, then
   `influxd inspect export-lp --engine-path <engine> --bucket-id
   70ce94895bf27f4d --output-path /home/pi/influx-export/symphony.lp.gz
   --compress` (`--compress` writes gzip to the path given; it does not
   append `.gz`, so name the file `.lp.gz` here or the later steps
   reference something that doesn't exist. Bucket id from
   legacy_openplotter_stack.md; re-derive with `influx bucket list --host
   http://localhost:8086` if it disagrees — remember `signalk.local`
   doesn't resolve for Go binaries). Restart influxdb. `scp` both
   artifacts off-boat.
4. **Prove the backup restores (off-boat, no boat involvement).** Listing
   a tarball and line-counting a gzip is not verification. On a dev
   machine: `docker run` a throwaway `influxdb:2.7` with the untarred data
   directory mounted at `/var/lib/influxdb2`, then confirm the `symphony`
   bucket is present, list measurements, and run one spot-check query
   against a window whose values you can compare to the boat. Cross-check
   by replaying the `.lp.gz` into a second empty bucket with `influx
   write`. `influx backup`/`influx restore` is the supported flow and is
   preferable where it works, but this boat's tokens 401, which is why the
   raw-directory route is primary. **The drop authorization is not active
   until this step passes.**
5. **QuestDB feasibility probe (semi-destructive, contained).**
   `docker run` a pinned questdb/questdb with `-m 768m`, ports on
   localhost, a throwaway volume. Run it for an hour alongside the full
   native stack, sampling `free -m`, `grep ^pswp /proc/vmstat` and
   container RSS every 30 s — a script writing to a file, not eyeballing,
   because **the peak is the measurement and the average hides it**. This
   answers the only question the research couldn't: whether the 4 GB box
   carries SignalK (~1.1 GB), QuestDB (~0.5–0.75 GB), Grafana, Telegraf
   and Caddy together.
   **Pass:** minimum available memory across all samples stays above
   ~400 MB and `pswpin`/`pswpout` do not move — the same thresholds
   CLAUDE.md uses for real pressure. Then B2 can proceed as written, with
   InfluxDB still running.
   **Fail:** available dips below ~400 MB at any single sample, or swap
   activity appears. Then the box does not carry both databases, and the
   order inverts — **B5 (InfluxDB off) must precede B2**, which means B1's
   backup must be complete and restore-verified first, since there is then
   no dual-run soak to fall back on and B3's parity comparison has to be
   made against the backup rather than a live InfluxDB. Say so in-session
   before re-ordering the plan; this is the one measurement that changes
   Track B's shape.
   Remove the container after; keep the sample file.
6. **Plugin install dry-run (semi-destructive).** Before any npm work in
   `~/.signalk`: back up `signalk-plugin-watchdog` and any other
   hand-installed plugin — `package-lock=false` npm installs prune
   anything without a `package.json` entry (bit us 2026-08-15). Check
   whether `signalk-questdb-history-provider` exists on npm; dry-run its
   install; on success configure it against the probe QuestDB from
   step 5 (localhost ports, finite retention) and confirm rows arrive.
   `show tables` only proves the table metadata exists — also
   `select count() from '<a path you know is live>'` twice a minute apart
   and confirm it climbs at roughly the plugin's configured rate, and
   `select * from … limit 5` to eyeball that the values are SI and not
   nulls. Record which SignalK paths appear, for the B5 parity comparison.
   Do **not** uninstall `signalk-to-influxdb2` in the same session —
   dual-run is the plan.
7. **Telegraf dual-write (semi-destructive, reversible).** Add a second
   `[[outputs.influxdb_v2]]` block pointed at `http://localhost:9000`
   with `content_encoding = "identity"` to the repo-tracked
   `telegraf/telegraf.conf`, restart telegraf, confirm host-metric
   tables appear in QuestDB. Revert by deleting the block.
8. **Grafana ⇄ QuestDB probe (read-mostly).** Add a PGWire datasource to
   the *native* Grafana by hand (`localhost:8812`) or bring up the compose
   Grafana with `--no-deps` (per the compose file's own warning about the
   8086 port race) — from the container the host is `questdb:8812` if
   QuestDB is on `symphony-net`, or `host.docker.internal:8812` while it
   is still a bare `docker run`; `localhost` inside the Grafana container
   is the Grafana container. Prove one panel of one dashboard reads
   QuestDB. This scopes the B4 porting effort with real
   queries before committing to it.
