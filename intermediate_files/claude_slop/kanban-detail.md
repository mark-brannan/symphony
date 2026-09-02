# Kanban card detail

Full working-memory detail behind the one-line cards in `kanban.md`, per the
project's Open Loops board contract. Headings are link targets — don't rename
one without updating the card that points at it. This file dies with its
cards: when a card is checked off and removed from `kanban.md`, delete the
matching section here too.

## Sync halos-pi4's SignalK config with this repo (Track A trial)

Started as "fix the dead RUNBOOK anchor," expanded 2026-08-26 into the
real goal: bring halos-pi4's SignalK config in line with this repo's, and
as much else of the stack as reasonable. Progress and findings below —
this is a bigger job than one session should finish inline; see the
ready-to-run prompt at the bottom.

### The OIDC front door is not actually in the way

`/etc/halos/oidc-clients.d/signalk.yml` federates SignalK's Traefik-fronted
admin UI to Authelia (port 4430). But **SignalK also listens directly on
`:3000` on all interfaces, bypassing Traefik/Authelia entirely** —
confirmed reachable as `curl http://halos-pi4:3000/signalk` from a dev
box over the tailnet. This is a real gap in HALOS's front door (every
container app likely has the same bypass — not verified for the others)
worth flagging to Mark once, not re-litigating: it means anyone on the
tailnet can already reach SignalK's public read API unauthenticated, no
Authelia session needed.

SignalK still runs its own separate security layer on top
(`"security": {"strategy": "./tokensecurity"}` in `settings.json`) —
`:3000/admin/` demands SignalK's own login, and plugin-config endpoints
return 401 without a token. A device-access-token request was already
pending from the earlier setup session (`halos-setup-script`,
`2d350bb4-...`, 2026-08-26T06:08 UTC) — never approved. A second one was
opened this session (`b975da82-fad8-4de4-8293-fe32113f3822`, poll
`http://halos-pi4:3000/signalk/v1/requests/b975da82-...`). Both need
someone to hit **Approve** in the SignalK admin UI (`:3000/admin/#/`,
Security → Access Requests) — that's a browser action, and there's no
known SignalK admin password for this box (`admin-password` file exists
at `/var/lib/container-apps/marine-signalk-server-container/data/admin-password`
but is root:root 600 — `pi` can't read it).

### The actual fast path: direct filesystem access, no token needed

The bind-mounted config dir is **owned by `pi`, not root**:
`/var/lib/container-apps/marine-signalk-server-container/data/data/` holds
`plugin-config-data/`, `package.json`, `settings.json`, `baseDeltas.json`,
etc., all `pi:pi` and writable over plain SSH — no API, no token, no
Authelia. `security.json` is `pi`-owned but `0600` (readable/writable by
`pi`, not world). This is the same shape as boat-Pi config management,
just a different mount point.

**Restarting the container to pick up file changes needs a decision,
not just a command** — `systemctl restart marine-signalk-server-container`
is blocked by this session's own auto-mode classifier as a state-changing
action on live infra, correctly. `pi` has no passwordless sudo either, so
this box's own polkit rules may require asking Mark regardless of the
harness.

### What's already there vs. the repo

Encouraging: an earlier session (`halos-box-setup-plugins-4e5990`,
2026-08-26 AM) already `npm install`ed ~60+ `signalk-*` packages into
`node_modules` on halos-pi4 — a large fraction of this repo's
`signalk/package.json` dependency list is already present as installed
node modules (confirmed via directory listing, not tested running).
`package.json`'s own `dependencies` block wasn't updated to match (still
lists only `signalk-noaa-space-weather`), and `plugin-config-data/` has
only ~12 files — HALOS's own bundled defaults (`course-provider`,
`freeboard-sk`, `signalk-autostate`, `signalk-flags`, `signalk-node-red`,
`signalk-questdb-history-provider`, `signalk-to-influxdb2`,
`sk-ais-status`, `resources-provider`, `skip-plotter-panel`) — so
plugins are installed but **not configured/enabled** with this repo's
settings yet. Architecturally this box already matches where the repo
is heading: QuestDB as history store is HALOS's default, same as our
Track B migration target.

### Left open — this is the real scope of the card now

1. Approve (or get Mark to approve) one of the two pending access
   requests, or find another way to auth for real admin-API-driven config
   pushes (vs. raw file writes + a restart).
2. Decide the restart story: get explicit go-ahead per file-sync round,
   since there's no dry-run for a container restart and no docker/sudo
   access to inspect it beforehand.
3. Actually diff `signalk/plugin-config-data/*.json` and
   `signalk/package.json` against halos-pi4's copies, file by file —
   only the top-level listing was compared so far, not contents. Expect
   real conflicts: this repo already carries per-plugin config (paths,
   credentials, tuned settings) that HALOS's defaults don't have, and
   some plugins (BLE/bt-sensors, GPIO, hardware-specific ones) may not
   even make sense on this box.
4. `security.json` diverges by design (different users, different auth
   mode) — union config data, never security/users config, same as the
   project's existing merge convention for peripheral configs.
5. Decide what "as much else as possible" includes beyond SignalK:
   Grafana dashboards, Telegraf, Caddy have no equivalent on HALOS
   (Traefik replaces Caddy, HALOS's own Grafana container replaces
   ours) — this overlaps directly with the open Track A verdict in
   `reference/containerization_strategy.md` (adopt/reject/adopt-with-exceptions),
   which nothing has settled yet. Don't let file-syncing plugins get
   ahead of that call.
6. Fix the dead RUNBOOK anchor once the real access story (API token vs.
   file+restart) is settled — the current text ("needs a token") is now
   known to undersell what's actually possible (direct file writes) and
   oversell the OIDC path (bypassable, not the actual gate).

### Ready-to-paste prompt for a fresh session (Opus, high effort)

```
Continue the halos-pi4 SignalK sync card in
intermediate_files/claude_slop/kanban-detail.md (heading: "Sync
halos-pi4's SignalK config with this repo (Track A trial)"). Read that
section in full first — it has the access-path findings, the two
pending SignalK access-request IDs, and why a container restart needs
Mark's explicit go-ahead per attempt, not once.

Work in an isolated worktree per this repo's CLAUDE.md.

1. Diff signalk/plugin-config-data/*.json and signalk/package.json
   against halos-pi4:/var/lib/container-apps/marine-signalk-server-container/data/data/
   (reachable read/write over plain SSH as pi, no sudo). Report the
   actual delta — which plugins are installed but unconfigured, which
   configs would need credentials/paths that don't apply on this box,
   which don't make sense there at all (BLE/GPIO/hardware-specific).
2. Ask Mark before writing anything: which plugins from that delta he
   actually wants configured on the HALOS trial box, given it's a
   Track A evaluation, not a second production install.
3. For each approved plugin, write its config JSON directly via SSH
   (pi owns plugin-config-data/), then ask Mark for go-ahead before
   restarting marine-signalk-server-container.service — no
   passwordless sudo on that box, and the harness blocks unprompted
   service restarts on live infra. Verify after restart: the plugin
   shows enabled and initialized in the SignalK log
   (journalctl -u marine-signalk-server-container -n 50) and its data
   appears in the API (curl the relevant path).
4. Once SignalK is settled, ask Mark explicitly whether "as much else
   as possible" should extend to Grafana/dashboards or stop there —
   that decision is entangled with the still-open Track A
   adopt/reject verdict in reference/containerization_strategy.md, and
   isn't yours to make by momentum.
5. Update this kanban-detail.md section (or close the card) with what
   landed, and fix RUNBOOK.md's dead "Setting up plugins on the HALOS
   trial Pi" anchor to describe the real access path once you've used
   it end to end.

Difficulty: high — expect several judgment-heavy back-and-forths with
Mark (which plugins matter on a trial box, restart go-aheads), not a
mechanical copy job. Budget for it, don't try to one-shot it.
```

## Purchase itemizations in maintenance/log.md

From the 2026-08-19 doc-bloat audit. Open call: trim maintenance/log.md's
purchase itemizations to one-line totals with detail moved to a dedicated
purchases file, or leave them as-is. Not acted on because it's editorial
judgment about the human file, not a technical fix.

## Land or discard three held claude/* branches

Three branches hold unlanded work that `main` does not have, kept out of the
2026-08-20 stale-branch sweep (which deleted eight others via content-safety
checks against old-main). Each needs its own land-or-discard decision:

- `signalk-oidc-identity-permissions-4kk8gl` — the OIDC proposal,
  `proposals/signalk-oidc-identity-permissions.md`, exists nowhere else.
- `symphony-docs-corrections-aeuorm` — DSC/AIS distress-chain test procedure
  and `reference/distress_monitoring.md`; main's RUNBOOK has no distress
  content at all.
- `laughing-hamilton-7f7pbg` — cherry-pick metrics framework
  (`.claude/hooks/measure-cherry-pick.sh` + `maintenance/stats.*`), plus
  security_posture/software_stack edits not checked line-by-line.

`grafana-questdb-port-target` (open PR #10) is also still around but is
tracked separately — see "Which Grafana dashboard set is the QuestDB port
target".

**Two more branches now exist and must stay out of any further sweep**:
`claude/ecoworthy-signalk-telemetry-vy82ta` @48f3122 (8 commits, JBD BMS BLE
capture) and `claude/symphony-pushover-setup-ce12i0` @3f08bd3, rescued off
the boat's stranded checkout 2026-08-20 (git-divergence reconciliation
session) and pushed after the sweep above ran. Neither is merged anywhere,
and the boat was their only other copy — a Claude's-list card tracks
sweeping the rest of the stale `claude/*` branches, but a session picking
that up must exclude these two the same way.

## Rotate the Tailscale OAuth client credential

A read-only `policy_file:read` OAuth client lives in
`secrets/symphony.sops.yaml` and backs `scripts/tailscale_policy.sh`. The
credential was pasted into a session transcript during the 2026-08-19
Tailscale SSH fix, so it should be rotated at
https://login.tailscale.com/admin/settings/oauth whenever convenient. Not
urgent — read-only scope, no write access was ever granted.

Two adjacent items closed during that same fix, recorded for continuity:
`ssh solace@nucbox-k12` times out because that Windows node has no SSH
server — a Tailscale platform limit, not a policy gap, nothing to fix.
Tracking the tailnet policy file in git was considered and rejected: this
repo is public, and the policy names the tailnet's tags and topology;
`~/claude_prompts_scratch` would be the right home if that's ever wanted.

## Symphony Plumbing Library.xml

Mark's own draw.io shape library for plumbing diagrams, Google Drive only —
not fetchable by a session. Owner deferred 2026-08-19 ("plumbing we'll
figure out later"). Not blocking anything; needed only once plumbing
diagramming starts (the electrical diagrams used the community Victron
library instead, already landed).

## dotfiles Google-connector parity

`dotfiles/.claude/settings.json` denies six connectors (Intuit_QuickBooks,
Intuit_TurboTax, CourtListener, Courtroom5, Legal_Data_Hunter, LegalZoom).
Symphony's `.claude/settings.json` denies those six **plus** Gmail,
Google_Drive, Google_Calendar. Denylists merge across sources so this isn't
a conflict, just an asymmetry — open call is whether dotfiles should also
deny the three Google connectors for parity. That's a dotfiles-repo edit,
not symphony's. Also worth checking on dotfiles' side whether
`disableClaudeAiConnectors: true` / `ENABLE_CLAUDEAI_MCP_SERVERS=false`
(both set there) make the denylists redundant on a machine where they apply.

## Confirm PostgSail is receiving

The plugin is enabled and configured against the hosted
`api.openplotter.cloud`, which answers 200 from the boat, but the only
visible evidence is an hourly "removing metrics from buffer" line — the
plugin finding nothing to delete, not proof of success. Checking whether
voyages are actually landing needs Mark's PostgSail account. If it's
working, the saillogger question mostly answers itself: postgsail is free
and already running, saillogger is $7.99/month.

## Chromium on the boat Pi

Its profile under `~/.config/chromium` is 1.9 GB (692 MB of extensions
across 23 of them, 335 MB of service workers, 231 MB of File System
storage) — the single largest reclaimable thing left on the SD card. Last
used 2026-08-13, not running. `apt autoremove` wanted to remove the package
outright on 2026-08-14 and was deliberately held back with `apt-mark
manual`, along with its codecs, pending a decision. Three options: leave
it, clear caches/service-workers only (~570 MB, keeps logins), or remove
the browser and profile entirely (removing the package alone doesn't
delete the profile). Related: the autostart browser was pointed at a
display whose DRM outputs all read `disconnected` — already handled
separately (autostart removed, per maintenance/log.md 2026-08-13).

## Track `~/.openplotter/openplotter.conf` in git, or not

Its `soundignore` key is load-bearing — it's what keeps OpenPlotter from
spawning a `cvlc` per notification, the process storm behind the 08-13
watchdog resets — and it lives only on the boat, set by hand, backed up to
a `.bak-` file beside it. The OpenPlotter GUI rewrites this file, so
anything tracking it has to survive being overwritten out from under the
repo (same shape as the already-tracked heartbeat config).

## Confirm the router's DNS overrides resolve locally

All four names answer with the boat IP today, but with the WAN up that
can't be told apart from the router forwarding to Cloudflare. The real test
is unplugging the WAN and running `nslookup
signalk.symphony.dark-star-llc.com`.

## HALPI2 purchase / SD-card boot-media strategy

The 32 GB SD card was 67% full as of 2026-08-14 (after a 3.3 GB cleanup),
holding the OS, SignalK state, InfluxDB and Grafana's DB. Measured write
volume ~10.7 GB/day (bursty around that average) since the N2K input was
connected — about 3.9 TB/year, inside a high-endurance card's rated life.
A USB SSD was considered and rejected: consumer SSDs have volatile write
caches, so on this boat's real failure mode (Pi powered straight off the
N2K bus, no buffer, sudden power loss) a cheap SSD can lose *more* than a
card, not less.

**HALPI2 is orderable and ends the decision outright**: 8 GB / 512 GB SSD
at $614.35, in cart without issue on 2026-08-13. It pairs an SSD with an
RP2040 that performs an orderly shutdown on power loss — the actual failure
this boat has, which no choice of card or drive alone fixes. Spending on
interim SD/SSD storage for the Pi 4B only makes sense if HALPI2 itself is
being deferred for other reasons. Trial at home first per the containerization
strategy decision (2026-08-18).

If HALPI2 keeps being deferred: reduce writes first (journald cap, debounce
`signalk-fixed-position` — rejected, see dropped items in the wrap-up
report; InfluxDB retention/downsampling), then replace the card with a
high-endurance one (Samsung PRO Endurance, SanDisk Max Endurance) rather
than a merely bigger one when it does need swapping.

## Read-only root filesystem for the boat Pi

The SD card holds OS, SignalK state, InfluxDB and Grafana's DB on one
partition and is the component most likely to fail first. `overlayfs
root-ro` is the standard mitigation and `tkurki/marinepi-provisioning` has
a `root-ro` role ready to use. It's a real change to how the box gets
worked on — every write becomes deliberate — so it's a decision, not a
config toggle.

## InfluxDB/Grafana: permanent disable or stay stop-on-pressure?

Settled 2026-08-13: SignalK, InfluxDB, Grafana, Caddy, Dex and Telegraf are
all expected to run and stay enabled (this is also written into CLAUDE.md).
InfluxDB and Grafana are the release valve — anyone may `systemctl stop`
them to recover ~600 MB under real memory pressure (swap activity or
available memory under ~400 MB) without asking, but must not disable them,
so a reboot brings them back. Whether that should instead become a
permanent disable is the only part still open.

## Two SSO user records (GitHub vs Google)

SignalK keys OIDC users on `sub` + issuer, so the same person arrives as a
separate readonly user from each provider (`mark-brannan` via GitHub,
`markbrannan@gmail.com` via Google). They can't be merged; both can be
granted the same permission. Decide whether this is worth doing anything
about.

## InfluxDB break-glass ownership and secret reconciliation

Break-glass itself is fixed (2026-08-14): signin now works against
`captain`'s credentials after `DOCKER_INFLUXDB_INIT_USERNAME`/`_PASSWORD`
were found pointing at a user that was never created (those `INIT_` vars
only apply to a fresh volume, and this one predates them). **The credential
itself is frozen — do not rotate it, do not offer to**, per the captain
credentials hold in CLAUDE.md § Security posture.

What's still open: who is responsible for InfluxDB break-glass, and whether
the token and password should have different owners. Separately,
`symphony.sops.yaml`'s three InfluxDB tokens (`influx_token`,
`influxdb_operator_token`, `influxdb_signalk_token`) all return 401 as of
2026-08-11 — the only working credential is captain's all-access token,
held in `signalk/plugin-config-data/signalk-to-influxdb2.json`. The org is
also mismatched: the running DB has org `symphony`, while `.env.j2` renders
`DOCKER_INFLUXDB_INIT_ORG=darkstarllc`. Buckets present: `symphony` (30d),
`_monitoring` (7d), `_tasks` (3d). Which side (repo vs running DB) is
authoritative is the open question — the repo copy isn't automatically
correct. Also: `influxdb_init_password` is unreferenced by `.env.j2` and
should be deleted once confirmed nothing reads it. This whole area becomes
lower-stakes once QuestDB migration finishes and InfluxDB is retired, but
isn't there yet.

## Nine major-version SignalK plugin upgrades

As of 2026-08-13 the boat is fully current *within* declared semver ranges
(`npm outdated` shows Current == Wanted everywhere), so every item below is
a deliberate major bump, not routine drift.

- **Safety-of-navigation, want someone watching when they land:**
  `signalk-anchoralarm-plugin` 1.18.2 → 2.0.1, `@signalk/signalk-autopilot`
  1.7.0 → 2.6.0.
- **Large webapps/flows:** `@mxtommy/kip` 3.12.0 → 4.8.5,
  `@signalk/freeboard-sk` 2.24.2 → 3.1.0, `@signalk/signalk-node-red` 3.2.1
  → 4.4.0, `signalk-tides` 1.5.0 → 2.1.2.
- **Small:** `signalk-postgsail` 0.5.1 → 0.6.0 (not blocked on
  better-sqlite3 — that only affects `signalk-polar`; postgsail declares no
  dependencies and is enabled, loaded and working), `signalk-noaa-space-weather`
  0.19.0 → 0.20.0 (Mark's own repo — coordinate with that dev work),
  `vhfinfo` 0.0.34 → 0.0.37.

`signalk/package.json` already targets the newer major for kip, freeboard,
autopilot, node-red, tides and postgsail, which reads as intent — but that
file describes a different install than the boat's, so it isn't authority
on its own.

## Stalled plugin configs needing a decision

Several plugins are installed, enabled, and doing nothing because a config
field was never filled in — each needs either the missing info or a
decision to drop it:

- **Cerbo GX 1** in the `bt-sensors-plugin-sk` config has an empty `paths`
  block, so it publishes nothing regardless of the D-Bus fix (see
  `RUNBOOK.md` → "Setting up a BLE sensor"). Decide what it should publish
  and fill the block in.
- **`signalk-solar-forecast`** throws on every start (`.length` of
  undefined) — needs a location filled in.
- **`signalk-to-influxdb-v2-buffering`** throws on every start (`.forEach`
  of undefined) — needs InfluxDB credentials filled in. Both have logged
  the same error every restart since 2026-08-13.
- **`@signalk/aisreporter`** throws `Cannot read properties of undefined`
  continuously; its config isn't tracked in this repo, and what's on disk
  has rate settings but no MMSI or endpoint — never fully configured.
  Decide whether to finish configuring it or drop it.

## Subscribe the phone to ntfy

`signalk-ntfy` has been installed and delivering on both the boat Pi
(`symphony-alarms` topic) and the dev stack since 2026-08-15 — real alerts
proven to land within minutes. What's left is Mark's own phone-side step:
install the ntfy Android app and subscribe to `symphony-alarms` on both
servers, using the Pi's tailnet or LAN address (not `localhost`). Decided:
do ntfy *and* a physical speaker, deliberately redundant — two independent
wake-ups aboard is the point when dragging anchor onto a lee shore at
night. The speaker/piezo purchase and wiring is tracked in Evernote
("Symphony Important Tasks"); the GPIO beeper plugin is already installed
and disabled, awaiting hardware.

## BME680 sensor ownership

Census 2026-08-14: the dedicated plugin `@oehoe83/signalk-raspberry-pi-bme680`
is installed but disabled on both boxes, yet the boat receives 2 paths from
source `OpenPlotter.I2C.BME680/688-1` — the legacy `openplotter-i2c-read`
service. Identified 2026-08-15: the two paths are
`environment.inside.relativeHumidity` (ratio) and
`environment.outside.pressure` (Pa), both live and fresh; the OpenPlotter
config leaves the temperature and gas channels unmapped, so nothing aboard
publishes any airquality value. The plugin's formula (`500 - 5 × score`, 0
best / 500 worst) matches the zone bands in `signalk/baseDeltas.json`
exactly.

Decide: enable the dedicated plugin (its saved boat config already points
at bus 1 / 0x77, the working sensor; set its pressure path to `outside` to
keep the barometer-trend source continuity) and retire the OpenPlotter i2c
entries — the service reads nothing else, and its second configured sensor
at 0x68 errors permanently ("Chip ID 0x0") — or keep OpenPlotter and give
up the airquality index, which it cannot compute. Both mechanisms polling
the same chip is not an option: contention disturbs the gas heater cycle.
Note the plugin only publishes after a 500 s burn-in on every start.

## Confirm secret-tooling suite on a keyed machine

The TASK to make CI able to run the secret-tooling suite is done (PR #19,
merged): `secretguard.can_decrypt()` now carries the "this machine holds
keys" meaning in both twins, `TestStore` gates on it, `secret-scan.yml`
runs `run_secret_tooling_tests.sh`. Mark ran the runner on NucBoxK12
(2026-08-20): four suites, all OK, `test_pseudonymize`'s 27 tests passed
with no skip, proving the real store opens on a keyed machine. But that
checkout predated the PR #19 merge — the output shape (four suites, a
22-test `test_secretguard`) is the pre-merge runner. Remaining: `git pull`
there and re-run; the new runner should print six OK blocks and
`test_secretguard` should show 27 tests. The gate change is keyless-only by
construction, so this is a formality, but it only closes once the new code
has actually run under a key.

## Evernote connector needs re-authorization

Token expired mid-session on 2026-08-20 (git-divergence reconciliation);
a cloud session can't run the OAuth flow. **Mark: re-authorize Evernote in
claude.ai connector settings**, then a session can file the list below into
"Symphony Important Tasks" per § Evernote, and drop boat stash `816c890`
(deliberately left in place until the transfer completes). Recovered
verbatim from that stash (`WIP on main: 54ef0e7`, `maintenance/priorities.md`):

- water line from dripless needs to go somewhere real — engineroom air loop?
- small DIY cockpit drain needs a new/different fixture and hose going to
  the stern
- freshwater pump (again)
- composting head, as Mark broke it down:
  - cut new square HDPE for subfloor
  - epoxy down purpleheart base
  - screw in HDPE (sealant around far edge of HDPE)
  - epoxy around sole and HDPE
  - screw down brackets for Airhead
  - run silicone line to shower sump (temp)
  - cut hole for fan
  - wire fan

Settled 2026-08-20: the stash's two plumbing deletions ("Address remaining
holding tank system work now that the old tank is out" and "Tighten head
pump / apply sealant; install Y valve between Lectra-San and head") are
ancient history per Mark and valid to drop; both already removed from
`priorities.md`. Its other four deletions (the Safety & compliance block)
had already landed in main independently — Mark doesn't recall the detail
and isn't worried about it, so they stay gone. Nothing outstanding here but
the Evernote filing itself.

## Dex is running :latest instead of its pin

Found 2026-08-20 (git-divergence reconciliation). `compose-idp.yml` pins
`ghcr.io/dexidp/dex:v2.45.1@sha256:8499afd690c437f...`, with a comment
explaining that `latest` moving under the boat is "not a surprise worth
having offshore." The container actually running is
`ghcr.io/dexidp/dex:latest`, digest `af9469509350...`, self-reporting
**v2.46.0**-20260806171424-ab64ed77 — the pin is defeated. Not caused by
this session's fast-forward; that commit range never touched
`compose-idp.yml`.

**Checked the registry rather than guessing**: `v2.45.1` is already the
newest actual release. `v2.42.0` … `v2.45.1` exist; `v2.45.2`, `v2.46.0`,
`v2.46.1`, `v2.47.0` do not. `:latest` is a rolling nightly off `main`
(built 2026-08-06, never released). So the repo's pin is correct and the
boat is wrong — there is nothing to re-pin *to*.

The fix is `docker compose --profile tls up -d dex`, which recreates the
container onto v2.45.1. Dex uses `storage_type=memory`, so any recreate
drops every session and refresh token — fine dockside, bad offshore.
**Needs Mark to pick the moment**; this is the same "breaking it costs the
remote access you'd fix it with" case as the checkout swap. Also worth
finding out what started Dex from `:latest` in the first place, or the pin
keeps getting defeated.

## Recovered boat-stash notes: IMU, temp sensors, RUNBOOK gaps

Recovered 2026-08-20 from a stash on the boat (Mark's own notes, not yet
investigated):

- i2c IMU data isn't showing up in SignalK — settle whether it should be
  configured via a plugin or via OpenPlotter.
- Temp sensors: unclear whether readings are being dropped or the sensors
  just need new batteries. Determine which before replacing anything.
- RUNBOOK gaps, in Mark's wording ("runbook should say how to..."):
  - how to simulate a ping failure, and the common things to check and try
    when there is a *real* failure
  - how to test ntfy locally
  - how to test Pushover
  - he ended the list with "others?" — worth a pass for further gaps

## Which Grafana dashboard set is the QuestDB port target

Two dashboard sets exist and are not versions of each other. The boat's
native Grafana has five dashboards, 76 panels, InfluxQL, imported from
published examples with 158 of 162 datasource references pointing at a uid
that doesn't exist there. The repo has six under
`grafana/provisioning/dashboards/json/`, generated by
`scripts/build_dashboards.py`, Flux throughout, written against paths this
boat actually publishes, including a `system` dashboard with no
counterpart aboard. `reference/legacy_openplotter_stack.md` used to
describe the committed set as uid-rewritten copies of the boat's five —
that was true before commit `1ce4e87` (2026-08-14) and is now corrected in
that file.

Not settled: which set B4 of `reference/containerization_strategy.md`
should port to QuestDB SQL — teaching the generator to emit SQL (small, the
generated set is already path-accurate) or hand-porting the boat's 76
imported panels (large, but that's what Mark actually looks at today). The
honest first step is neither — open both in Grafana side by side and find
out what the imported five show that the generated six don't. That
comparison needs the boat on the tailnet. Until it's done, treat B4's scope
as unknown rather than assuming the generator route. This is what open PR
#10 (`grafana-questdb-port-target`) is blocked on.

## Deploy the repo's Grafana provisioning to the boat

`/etc/grafana/provisioning` on the Pi still holds only Debian's
`sample.yaml` files, so none of the five dashboards in
`grafana/provisioning/dashboards/json/` or the InfluxDB datasource
definition are actually in use — the running Grafana was configured by
hand. Either point the native install at the repo's provisioning directory,
or wait for the Docker deploy (Track B). Until then the golden config's
dashboards are untested against real data.

## Build a host-health Grafana dashboard

Telegraf already records everything needed; none of it is visible
anywhere. Four queries were run against the live database on 2026-08-13
and return data, so the remaining work is panels, not discovery:
`processes`/`blocked` (a non-zero value that doesn't come back down is a
wedged task, the v3d signature), `rpi_health`/`under_voltage_since_boot`
(latched — any 1 means the N2K bus sagged since boot), `chrony`/`last_offset`
(clock drift; group away the `reference_id` tag or each NTP peer becomes
its own series), `internal_write`/`metrics_dropped` (non-zero means
Telegraf is discarding, so gaps elsewhere are the monitor failing rather
than the boat being quiet). Pair with `kernel`/`context_switches` and
`mem`/`available` on the same time axis — the starvation signature is all
three moving together.

## Replace Telegraf's stopgap InfluxDB credential

Telegraf writes with `influxdb_captain_token` — captain's all-access token
— because no scoped token could be minted while the store was out of sync.
Once the InfluxDB secret reconciliation is done, create a token scoped to
write host metrics only, put it in sops, and point `TELEGRAF_INFLUX_TOKEN`
at it in `.env.j2`. Consider a separate bucket with its own retention at
the same time, so host metrics stop sharing `symphony` with vessel data.

## Rate-limit sshd on the boat Pi

Measured 2026-08-14: `PasswordAuthentication yes`, `PermitRootLogin
prohibit-password`, no fail2ban, no host firewall (INPUT policy accept,
only Tailscale's own chains exist). Zero failed password attempts in the
previous 24 hours — precautionary, not a response to anything. Port 22
answers on the boat LAN, the Pi's own WPA-PSK access point (`SignalK`,
wlan9, 10.42.0.1/24), and the tailnet; nothing is internet-exposed. The
reason to do it anyway: the router is consumer gear, so the wifi PSK is the
weakest link, and someone who gets that far can either read SignalK
(acceptable, already true without login) or get a shell on the box that
runs everything (not acceptable — a shell is where a persistent backdoor
lives, and it'd outlast the wifi password that let it in). Password auth
itself stays: it's the offline fallback when a keyed device is dead and the
boat is far from anywhere, so rate-limiting is the right control, not
keys-only.

## Reconcile signalk/security.json (repo vs boat)

The repo's `signalk/security.json` is the dev container's, not the boat's
— same two-live-installs shape as the plugin configs. Compared 2026-08-14
against `~/.signalk/security.json` on the Pi: `secretKey` and the
`captain` password hash both differ, and the repo carries a `screenshots`
user and a `claude-dev-tools` device the boat has never had. Copying
either file over the other is not a sync — it invalidates every token
SignalK has issued and changes the captain password on whichever box
receives it. One difference is a real decision rather than drift:
`mark-brannan` is `admin` in the repo and `readonly` on the boat — decide
whether that permission level should match on both. Decide per field; the
union rule doesn't apply to `secretKey` — there is no superset of two
signing keys.

## Set up a private repo for Vaultwarden hosting

Off-machine hosting (VPS or existing NAS) for Vaultwarden, holding the
sops/age key backup, reachable privately (e.g. Tailscale) — currently only
a local Docker proof-of-concept on the boat computer, which doesn't solve
the single-point-of-failure risk for the key protecting
`symphony.sops.yaml` / `signalk/security.json`. The compose file that
settled the hosting shape is in `vaultwarden/` in this repo — but this repo
is public, and Mark expects to use the vault for things unrelated to
Symphony, so the files want a private repo of their own *before* the VPS is
built. Plain `git rm` when that happens, not a history rewrite — nothing
secret is in them currently.

## Deploy the openweather-signalk humidity-fix flow

`environment.outside.relativeHumidity` publishes OpenWeatherMap's raw
percent instead of SignalK's 0-1 ratio, so every dashboard panel on that
path reads ~8800%. Root cause confirmed in the plugin's source
(`openweather.js`/`skunits.js`) and reported upstream. Procedure and the
flow JSON are in `RUNBOOK.md` → "Fixing openweather-signalk's mis-scaled
outside humidity". The flow is built but unverified against the live
editor — the `signalk-subscribe` node's path/flatten fields may need
setting by hand on import. Needs boat access. Remove the flow once the
upstream fix ships.

## signalk-lint batch 2 (host-level rules)

Batch 1 (config-only, no collector change) was written 2026-08-14:
bt-sensors scan starvation, alarm-path-dead, no-data-connections,
fallback-is-primary — status of whether it landed on `main` wasn't
re-verified this session, worth checking before starting batch 2. Batch 2
needs collector work: `can0` UP with no NMEA2000 provider (stronger than
the config-only version, since it proves the bus exists), `gpsd` naming a
device that doesn't exist, a systemd drop-in with directives before any
`[Section]` (systemd ignores it silently), a cron reboot with no
npm-in-flight guard, a browser in autostart while every DRM output reads
`disconnected`, no RTC combined with no synced NTP source,
`RuntimeWatchdogUSec` disagreeing with `/sys/class/watchdog/watchdog0/timeout`,
and journald with no `SystemMaxUse`. Each one is a fault this boat actually
hit.

## signalk-lint: no rule may throw on malformed input

A malformed connection entry crashed an entire lint run on 2026-08-14 —
code already on main at the time, not a new diff. A linter fails hardest on
exactly the box that most needs it, because the machine with a broken
config is the one being linted. Make this a stated convention, and give
every rule a garbage-input fixture.

## Trim RUNBOOK's remaining prose-heavy sections

Measured 2026-08-14 by prose-to-command line ratio: "SSO login (GitHub /
Google)" 141:18, "Bringing up a host" 71:13, "Installing host files" 52:9,
"When SignalK errors about missing packages" 39:8. SSO is the worst but
part of it is genuinely click-through in provider consoles with no command
form, so trim rather than restructure. "Installing host files" is the
better target — it has grown a paragraph per installed file, and most of
that belongs in `reference/` under the file's own actions-only rule.

## GPS time off the N2K bus into chrony

PGN 126992 (System Time) and 129029 (GNSS Position Data) both carry it, and
chrony's current `GPS` refclock has never received a sample because it's
fed from `gpsd`, which has no device. Something has to write a SHM segment
from the N2K time, or feed chrony over the network — same fix either way it
gets scoped: read PGN 126992 once SignalK is on `can0`, or the wider GNSS
position fix. Until then the clock is internet-only and free-runs offline,
on a box with no RTC — which is also what makes the DS3231 fit worth doing
regardless; doesn't remove the case for the RTC either way, since a GNSS
clock needs a fix and a powered bus, so it cannot cover a cold boot while
offline.

## Set source priorities for position once AIS is powered

The chartplotter and the AIS each carry their own GPS, so once the AIS is
powered there will be two sources publishing `navigation.position` and
SignalK will pick between them in arrival order.
`~/.signalk/priorities.json` is `{}` today. Procedure is in `RUNBOOK.md` →
"When the AIS is powered, there will be two GPS sources"; can't be done in
advance because N2K addresses are claimed dynamically and have to be read
off the running bus.

## Add bt-sensors-plugin-sk to the watchdog's expectPlugins

`plugins/signalk-plugin-watchdog` was deployed to the boat back on
2026-08-15 and proved both the healthy and failure paths — but it wasn't
watching `bt-sensors-plugin-sk`, which is why the total loss of battery
data (the 2026-08-20 D-Bus incident) surfaced only when a migration audit
tripped over 79 empty tables. Add it to `expectPlugins` so a repeat is
visible immediately rather than discovered later. `host/signalk-ble-check`
catches the same silence but only heals by restarting, which can't fix a
deterministic fault — the watchdog is what makes it *visible*.

## Trim SignalK's ~45s startup time

`signalk-plugin-internet-speed` throws on every start (`speedtest: Network
unreachable`), `signalk-healthcheck` watches an `n2k-can0` that doesn't
exist, and `signalk-to-noforeignland` is installed twice. Swap was 199/199
full with 828 MB available when this was measured. Cutting startup below
30s removes the conditions that made the D-Bus timeout above reachable at
all, workaround or no workaround.

## Fast barometric-pressure-drop notification

Both `environment.barometer.*` and
`environment.outside.pressure.{trend,prediction}.*` already carry
trend/prediction data (`reference/signalk_paths.md` notes the two parallel
barometer stacks), but nothing currently turns a fast drop into a
notification — no zone is configured on either path. A `meta.zones` entry
(server-native, no plugin) or a small Node-RED flow would both work.
Flagged in `reference/node_red_signalk_use_cases.md` (List 3, section M).

## Verify Grafana SSO end to end

Its OAuth config is live, but the browser login has never actually been
exercised. `grafana-server` is running (confirmed after the 2026-08-13
reboot), so nothing blocks the test.

## Restore signalk-healthcheck's config to git

The host-alarm section of `signalk-healthcheck` is disabled and its
`n2k-can0` provider-staleness watch is enabled — done on the boat
2026-08-14. But the repo's tracked copy of this plugin's config was deleted
from git in an earlier commit (`b8b4cc2`) along with its `.gitattributes`
sops rule for the mail-password field. Restoring it to git needs that
rewired first (`scripts/add_inplace_secret.sh` or equivalent) — until then
the settled config exists on disk, untracked, rather than committed.

## Fix better-sqlite3 for signalk-polar

Stuck at 7.6.2, which doesn't build on Node 22 — the release predates the
removal of `v8::AccessorSignature` and `v8::Object::CreationContext`, so
compilation fails and no `.node` artifact exists. `signalk-polar` is the
only thing on the boat that needs it — **`signalk-postgsail` is not
affected**, contrary to what older notes said; it declares no dependencies
at all and is enabled, loaded and working. The fix is a newer
better-sqlite3, but polar pins `^7.6.2`, so it needs either an upstream
bump or an npm override — decide which before installing anything, and
remember npm rolls the whole tree back on a build failure here. Or drop the
plugin.

## Evaluate parked/unused SignalK plugins on the dev container

**A parked plugin is not drift** — these were installed on purpose to try
and never got the time; don't install one on the boat because the dev box
has it, don't remove one from the dev box because the boat doesn't, and
don't file the difference as something to fix. Only Mark can judge which
of these are worth pursuing; what's below is measurement to start from.

- `open-meteo` — **works today, nothing blocking it.** Serves SignalK's v2
  weather API via `registerWeatherProvider`, so publishing zero paths is
  correct rather than idle; verified live sane data 2026-08-14. The API key
  is optional (premium content only, per the plugin's README).
- `signalk-questdb` — enabled, QuestDB holds zero tables. Configured with
  `questdbHost: 127.0.0.1`, which from inside the SignalK container
  addresses that container rather than QuestDB, and the two aren't even on
  a shared network (`sk-signalk-questdb` on `symphony-net`, `signalk-server`
  on `symphony_symphony-net`). Never written a row. Worth fixing depends on
  what it's wanted for — it'd be a second time-series store beside
  InfluxDB, real cost on the Pi but not on the dev box.
- `signalk-doctor`, `signalk-container`, `signalk-crows-nest` — installed,
  unevaluated. Their webapp-load counts are an enumeration artifact (eight
  webapps sit at exactly 12 loads each, hit together in fixed ratios — not
  a usage signal). `signalk-questdb` sets `managedContainer: true`, so
  there's some relationship between it and `signalk-container` nobody has
  traced.
- Of the 15 container-only plugins overall, only `signalk-rpi-stats`
  (publishes 29 paths, demonstrably works) can be positively confirmed.
  `signalk-marinetraffic-public`, `signalk-mob-notifier` and
  `signalk-basic-tide-widgets` have never been configured
  (`configured_values: false`). One unexplained thing, flagged not
  resolved: `marinetraffic-public` reads unconfigured, yet
  `marinetraffic.XX` publishes one path and shows in
  `unattributed_sources` — nobody has traced why.

## Add a weather term to ACTOR_HINTS

`open-meteo` is an actor by `scripts/signalk_plugin_census.py`'s own
definition — its product is a registered v2 API, not published paths — but
`ACTOR_HINTS` has no weather entry, so it scores `unmatched` and reads like
a fault. Any other provider plugin will land the same way; add the term.

## Scope the COLREGs navigation-lights plugin

New custom plugin idea: navigation-lights switching per COLREGs, driven off
NMEA 2000 / relay switch state rather than manual toggles alone — enforce
the correct light combination for the vessel's current condition
(underway/sailing vs. power, at anchor, restricted in ability to
manoeuvre) and flag an invalid or incomplete combination rather than
silently allowing it. Not scoped yet: which physical switches/relays this
reads and drives (`systems/electrical.md`'s lighting sub-panel has nav
lights running/off/anchor and sailing/steaming on separate circuits today,
not obviously behind a single NMEA 2000 switch bank), which
vessel-condition input it trusts (AIS nav status? a manual mode switch?
autopilot engaged state?), and whether it should only *warn* on a wrong
combination or actively *switch* lights. Worth deciding early whether this
is a SignalK plugin (packaged, testable, installable elsewhere) or a
Node-RED flow (faster to iterate, but COLREGs light-combination logic has
enough branching that it likely outgrows a flow — don't reach for Node-RED
just to dodge writing a real plugin).

## Fork signalk-noaa-weather's notification behavior

Disabled on the boat 2026-08-13 after it drove the Pi into a reboot loop.
Its config takes a whole state (`notificationStates: "WA"`), polls every
60s, and raises every active NWS alert as a SignalK notification with
`notificationSound: true` — so air-quality alerts for Spokane play sounds
on a boat in Puget Sound. The notification pattern is what's worth redoing:
alerts should be filtered by actual vessel position, and informational
weather shouldn't use the same alert path as a real alarm.

## Verify the heartbeat's soft-warning tier live

The escalation path (direct Pushover POST when hc-ping.com fails
repeatedly) is deployed and was live-tested for real 2026-08-14 (pointed
`/etc/boat-heartbeat.json` at a bad URL, got the Pushover message,
restored). The soft-warning tier (thresholds shy of the alarm ones — disk
≥80%, memory <600MB — a low-priority buzz, never `/fail`) is covered by a
mock-server pass but not a live one, since real mem/disk haven't actually
been in the warn band to trigger it.

## Watch unattended-upgrades over a few more cycles

Enabled 2026-08-13 — `20auto-upgrades` and a boat-specific
`52unattended-upgrades-boat` are both managed by `host/install.sh`, a dry
run applied cleanly, and it takes Debian security updates only, never
reboots on its own, and blacklists `nodejs`, `signalk-server`, `bluez`, the
kernel and `openplotter-*` (the packages whose upgrades have actually
broken this boat). What's left is confirming it behaves over a few real
cycles: check `journalctl -u unattended-upgrades` and
`/var/log/unattended-upgrades/`. Mail reporting is configured but goes
nowhere until the box can send mail at all.

## Add data-source staleness to the heartbeat payload

This is the one thing `signalk-healthcheck` used to do that nothing else
does, and it was the gap that let `signalk-fixed-position` pass for a real
GPS for months: the box is healthy, the data is dead, and every liveness
check says fine. Carry the age of `navigation.position` and of the house
battery readings in the heartbeat ping, so silence in the data shows up in
the same place as silence from the box.

## Audit and fork signalk-pushover-notification-relay

Likely shape for phone+audible alarm delivery: `signalk-pushover-notification-relay`
(2022, unmaintained) relaying to Pushover on Mark's Android, alongside the
already-working ntfy path. License checked 2026-08-15: ISC, permissive —
forking and republishing under a new name is clear. Three branches, not
two: audit the plugin first; if it's basically sound and just stale (four
years untouched, single-dependency drift is the likely failure mode for a
plugin this small), **fork it, fix what the audit finds, publish under our
own name** rather than discard the working parts; only if it's
fundamentally broken or the SignalK plugin API has moved past it does it
drop to the Node-RED flow (subscribe `notifications.*`, POST to Pushover).

**Unresolved flag from 2026-08-15**: `signalk/plugin-config-data/signalk-pushover-notification-relay.json`
exists in the repo with `enabled: true`, which contradicts an earlier note
that the plugin wasn't installed. Unclear whether that means it's actually
live on the boat, or the config was copied in without the plugin running —
check on the boat before trusting either. The credential blocker is gone
either way: `pushover_api_token`/`pushover_user_key` are already in
`secrets/symphony.sops.yaml`. Node-RED (`@signalk/signalk-node-red`,
upgraded to 4.4.0) is otherwise idle rent on the Pi aside from the
openweather humidity-fix flow — if the fork or existing config already
covers delivery, don't leave a Node-RED Pushover fallback flow half-built
as dead weight.

## MOB detection research

Open research item, medium-low priority. **Never live-test the DSC
emergency button, on this or any other item — standing rule.** Owner
confirmed 2026-08-15: triggering it sends a real distress call to the
Coast Guard on Ch 16 DSC, with possible fines or legal consequences, and
it "ain't happening." What's aboard today: a handheld VHF with DSC and an
emergency button, and an AIS Class B transceiver — no MOB button or
crew-tag hardware of any other kind. `signalk-mob-notifier` is installed;
whether it (or anything else) actually consumes that DSC/AIS hardware is
unconfirmed, and has to stay that way until it can be settled by reading
documentation or source — never by pressing the button to see what
happens. Owner is only willing to adopt a solution already proven
elsewhere to work reliably, not something built and validated on this
boat. See `reference/node_red_signalk_use_cases.md` section H.

## Remove the deprecated @signalk/zones plugin

Installed at 1.2.0, enabled, never registered. Zones are server-core via
`meta.zones` now — the plugin is only a broken editor UI. Remove it on the
boat, and mirror the airquality zone meta from `signalk/baseDeltas.json`
into the boat's own baseDeltas. Fits the next maintenance window.

## Fit a DS3231 RTC to the boat Pi

The Pi has no real-time clock, so it boots with a wrong clock and stays
wrong whenever it's offline — which breaks TLS validity, OIDC token
windows, and every timestamp written to InfluxDB/QuestDB. The PiCAN-M
exposes a Qwiic (I2C) connector; `dtoverlay=i2c-rtc,ds3231` plus a udev
rule is the whole software side (`tkurki/marinepi-provisioning` role `rtc`
already has it). Cheap, independent of the N2K/GPS time question above,
and it's what makes the offline case survivable rather than merely
detectable.

## Generic single-path-arithmetic plugin idea

Came up chasing the openweather humidity bug (see the humidity-fix flow
card): neither `signalk-path-mapper` (rename/duplicate only),
`signalk-derived-data` (fixed built-in calculators, no custom formula),
nor `signalk-value-combiner` (needs two live input paths, no constant) can
scale/offset a single path by a constant, and nothing in the plugin store
fills the gap. Verdict: two data points (this and the BME680
path-naming mismatch) don't yet justify building and maintaining a new
plugin when Node-RED, already running, covers it generically — revisit if
a third case shows up.

## Doc-cleanup follow-ups still open

From the 2026-08-19 doc-bloat audit; the bulk of it closed same-session
(claude_slop structure, CLAUDE.md rules, log.md/priorities.md trims,
dotfiles boards descoped, all the reference/ trims). Two small items
remain:

- Extend `scripts/lint_repo_hygiene.py` with a soft warn on
  `maintenance/log.md` bullets over ~5 lines — optional enforcement, not
  acted on.
- Dotfiles: `boards/claude.md` still lists "Reconcile standing-orders
  lines with the Standing orders additions session" and a board-rework
  handoff note that should be deleted — dotfiles-side, not symphony's; a
  note here rather than a symphony card because no symphony session can
  action it.

Separately, and settled rather than open: the fork boundary inside
`lint_repo_hygiene.py` (2026-08-19) — the file mixes one generic secret-
management rule with two site-specific ones (audible alarms,
`FROZEN_SECRET_KEYS`), and a review bot flagged the hardcoding on PR #12.
Recorded recommendation: leave it hardcoded. Moving the list to a config
file makes the freeze editable and gives the rule a way to fail closed if
the file goes missing, where a tuple in the source cannot fail open.
Revisit only if a fork becomes real.

## Stale branch `claude/git-hygiene-redesign`

Pushed ref `7be6e6a`, the pre-worktree take on the git-hygiene redesign,
superseded by `0a76db4`/`a861190`. No PR was ever opened (that session's
GitHub API was 403-blocked; push still worked). Nothing in it is worth
salvaging, and per § Git hygiene it can't end "merged via PR," so deleting
it needs Mark's explicit go-ahead rather than a session doing it
unilaterally.

## Undelivered coordination note to the "hooks-continuity-cleanup" session

Mark asked this repo's session and a dotfiles + claude_prompts_scratch
cloud session (`session_014zxMuv2RQ3p4Z7PRA1eTm7`, branch
`claude/hooks-continuity-cleanup-sq7dnm`) to coordinate, but no channel
exists between two cloud sessions — `ListAgents` returns nothing without a
Remote Control connection, `SendMessage` fails, and Claude Code Remote's
MCP surface has no `send_message`. Last known state, 2026-08-19 ~17:53Z:
that session was idle, not blocked — it had opened **PR #3 on dotfiles**
("Automate session continuity: SessionStart brief, Stop checkpoint, typed
decisions") and was waiting on two manual steps only Mark can do in the
dotfiles web UI. Worth checking whether those steps still need doing
before treating this as live — a session-and-a-half has passed since.

## QuestDB migration execution notes not in the reference doc

**Closed out 2026-08-26**: QuestDB is confirmed capturing what it should.
23 tables present (3 history-plugin, 20 Telegraf/internal); `signalk` and
`signalk_position` row counts climb minute to minute; sampled rows carry
real, non-null values (dock GPS coords, battery/environment paths). This
also resolves the "QuestDB holds zero tables" line under "Evaluate
parked/unused SignalK plugins on the dev container" below, for the
avoidance of doubt — that finding was always about the **dev container's**
different, older `signalk-questdb` plugin, not the boat's
`signalk-questdb-history-provider` (B3). The boat's `questdbHost:
127.0.0.1` is correct: SignalK runs natively there, not in a container, so
`127.0.0.1` reaches QuestDB's published Docker port. Re-ran
`scripts/questdb_table_hygiene.sh` against the boat — 0 changes needed,
every managed table already had TTL and dedup keys set.

`reference/containerization_strategy.md` carries the B1-B7 plan and some
retroactively-added plan-level facts, but three execution findings from
the actual 2026-08-20 B1-B3 run aren't in it:

- **Telegraf's retry can double-write.** A timed-out HTTP response can
  still have been committed by QuestDB, so a retried batch lands twice —
  measured on the boat: writing the same line twice landed two rows before
  dedup and was absorbed after. That's a hole in B5's row-count parity
  check specifically, since the QuestDB-side count would be inflated by
  exactly the retries. The history plugin's own tables ship with dedup on;
  only Telegraf's were exposed, and are handled by
  `scripts/questdb_table_hygiene.sh`.
- **`retentionDays` is not a real QuestDB TTL.** All three history-plugin
  tables read `ttlValue 0` in QuestDB's own metadata — the plugin drops
  aged partitions itself. There's nothing in QuestDB to check the setting
  against; verifying it means watching partitions age out at day 30 (set
  by Mark against a boat root filesystem at 82% full, with InfluxDB still
  running) or reading the plugin's config back.
- **The off-boat backup copy is still outstanding.** B1's two InfluxDB
  backup artifacts (`influxdb-data-<ts>.tar.gz`, `symphony-<ts>.lp.gz`,
  sha256-summed) proved they restore correctly via an on-boat restore
  test, but they still only exist on the boat's own SD card, at
  `/home/pi/influx-export/`. This session's tailnet path off-boat ran at
  ~30-50KB/s (DERP relay, not a direct P2P path), so the copy was left for
  Mark to `scp` from one of his own devices whenever convenient — not
  urgent, since the on-boat restore test is solid evidence the backup
  itself is good, but B1 isn't fully done until it happens.

Also worth knowing before touching QuestDB's compose config again: the
disk-fill incident (root hit 100% within 15 minutes of the Telegraf output
going live, from QuestDB's per-column-file preallocation on 20 new SYMBOL-
heavy tables) is already documented in `containerization_strategy.md`,
along with its fix (`QDB_*` append-page env vars cut to 256k/128k). That
part didn't need repeating here.

## Sensor hardware design backlog

One backlog of engineering/diagramming tasks (planning-stage, not the
physical install itself — physical fitting stays in Evernote per project
convention):

- Design engine temp sensors and diagram
- Design engine flow sensor plumbing
- Design engine flow sensor electrical
- Rudder position sensor
- Pump flow sensors
- Air quality sensors (general — separate from the BME680 ownership
  decision above)
- Air pressure sensor
- Illuminance sensor
- Additional temperature sensors
- Design smart pump system with voltage/current detection

## Autopilot hardware backlog

- pypilot
- Design pypilot board
- Separate IMU for pypilot

## 3D-print sensor enclosures backlog

- 3D-print gas sensor case
- 3D-print BME688 case
- 3D-print IMU case

## bt-sensors-plugin-sk must survive the SignalK reinstall

The boat runs a **source checkout**, not the published package. The fix in
upstream PR #189 (lazy D-Bus + reconnect-on-error) is not in any released
version — `1.3.8-beta10` on the registry does **not** have it. Two links carry
it, and both live outside git:

- `~/.signalk/node_modules/bt-sensors-plugin-sk` -> `~/bt-sensors-plugin-sk`
- npm global prefix is `/home/pi/.npm-global`, where
  `bt-sensors-plugin-sk@1.3.8-beta10 -> ../../bt-sensors-plugin-sk` is linked.

`~/bt-sensors-plugin-sk` also holds **untracked webpack output** in `public/`
(`main.js`, `remoteEntry.js`, the numbered chunks) that the plugin's webview
needs at runtime and `.gitignore` excludes. A re-clone loses them; `npm run
build` in that directory regenerates them.

`/etc/dbus-1/system-local.conf` and its raised `auth_timeout` were deliberately
removed once the plugin fix landed. Don't restore that workaround — the fix
replaces it.

**2026-08-26 update: it didn't survive.** After the 2026-08-25 SignalK
reinstall, `~/bt-sensors-plugin-sk/node_modules` was gone entirely (no
lockfile either) and the plugin failed to load with `Cannot find module
'@naugehyde/node-ble'`. Both symlinks above were intact, and so was the
untracked `public/` webpack output — only `node_modules` needs restoring.
`npm install --no-audit --no-fund --prefer-offline` in that directory ran
29m28s and died on `ECONNRESET` (8 direct deps, but no lockfile pulls in
their full dev tree — material-ui, recharts, eslint, etc). npm rolled back
cleanly; no partial `node_modules` left behind. Matches the documented
cellular-WAN pattern (see the "binding constraint" card) — didn't retry a
second time per standing instruction. SignalK's core (NMEA 2000 via
canboatjs, confirmed live) is unaffected; this only blocks BLE sensor data.
Next attempt: either retry over a quieter link, or pre-populate `~/.npm/_cacache`
from a machine with faster internet the way the signalk-server reinstall did.

## Evidence-gathering for upstream PR #189

2026-08-27/28, on Symphony, working toward a merge case for
[PR #189](https://github.com/naugehyde/bt-sensors-plugin-sk/pull/189) (lazy
D-Bus + reconnect-on-error, replacing the `auth_timeout` workaround).

**Confirmed:**
- Deployed `~/bt-sensors-plugin-sk/index.js` matches the PR's diff exactly
  (`getBluetoothSession`, backoff reconnect, the "Bluetooth D-Bus connection
  lost, reconnecting…" status text are all present).
- `/etc/dbus-1/system-local.conf` is gone, as the PR says it should be.
- SignalK ran 10h+ crash-free under real BLE error load (800
  `DBusError: Not connected` / 1130 `Unhandled rejection` log lines/24h from
  `JBDBMS.js` — a separate, still-open BLE-level issue this PR doesn't
  touch) before this session started poking at it.
- Live battery data (House Battery 2) flows continuously with fresh
  timestamps throughout — the plugin works end-to-end on real hardware.

**Three attempts to directly trigger the PR's new reconnect branch, none
succeeded, none caused lasting damage:**
1. `systemctl restart bluetooth` — only bounces bluetoothd/BlueZ objects,
   not the D-Bus system bus socket the plugin's connection lives on. No
   effect on the plugin's bus connection.
2. `systemctl restart dbus.service` — bounces the system bus itself.
   Confirmed prediction: NetworkManager (D-Bus-activated) died with
   `SIGTERM` and stayed down (`Restart=no`) until manually restarted;
   SSH/Tailscale connectivity never dropped throughout. Restarted
   NetworkManager afterward — reassociated eth0/wlan0/wlan9 within ~10s,
   fully recovered. But the plugin's own bus connection apparently
   survived this too — no reconnect log line fired.
3. Identified the plugin's live system-bus fd directly (node pid's fd 39,
   paired with dbus-daemon's fd 18 via matching adjacent socket inodes —
   `ss -xp` / `lsof -p <pid> -a -U`) and closed it with
   `gdb -p <pid> -batch -ex 'call (int)close(39)'`. Fd confirmed closed,
   SignalK stayed up, battery data kept flowing — but still no reconnect
   log line. Likely explanation: a raw `close()` syscall via gdb bypasses
   libuv's own bookkeeping, so Node/dbus-next's event-driven error handling
   (which expects an OS-level error like `ECONNRESET` from a live peer,
   not a silently-vanished fd) may never actually observe it the way a
   real network-level disconnect would.

**Still missing for a fully closed case:** direct proof the PR's own
error-handler + backoff branch has ever fired and recovered on real
hardware. What's next to try (not yet attempted): trigger a genuine
peer-side disconnect instead of a local fd close — e.g. `nft`/`iptables`
DROP on the dbus socket briefly (won't work, it's AF_UNIX, not
TCP/netfilter-visible), or send `SIGKILL`/restart directly to the
`dbus-daemon` PID that's actually serving this connection (not
`systemctl restart dbus.service`, which is a controlled `SIGTERM` the
daemon handles gracefully) — a hard kill should generate a real socket
error on the plugin's end without dragging NetworkManager through another
death-and-recovery cycle. Handoff prompt for this: see `log.md`'s
2026-08-28 entry.

## postgsail SQLite bind fix — done 2026-08-26

Applied and verified on the boat: `maxSpeedOverGround`/`courseOverGroundTrue`
in `~/.signalk/node_modules/signalk-postgsail/index.js` (lines 51-52) now
default to `0`, matching `windSpeedApparent`/`angleSpeedApparent` two lines
below. Restarted `signalk`; the `TypeError: Provided value cannot be bound
to SQLite parameter 5` is gone from the log, only unrelated
`api.openplotter.cloud` connect-timeout errors remain (a WAN/upstream
issue, not this bug). Root cause and upstream fix:
[issue #68](https://github.com/xbgmsharp/signalk-postgsail/issues/68).
Reminder for whoever next reinstalls this plugin: the patch lives in
`node_modules` and is silently lost on the next `npm install`/upgrade —
reapply until upstream merges.

## Uninstall signalk-to-influxdb2, blocked on an npm-tree quirk

Confirmed dead: InfluxDB was purged 2026-08-25 (disk pressure), and
`signalk-to-influxdb2`'s `HistoryAPI` throws an unhandled rejection
(`Cannot read properties of undefined (reading 'filter')`) trying to reach
it, live-confirmed 2026-08-26 00:30.

**2026-08-26: WAN is no longer the blocker** — checked first
(`curl` to registry.npmjs.org, 1.4s; `ping` to 8.8.8.8, 30-45ms, 0% loss)
and `cd ~/.signalk && npm uninstall signalk-to-influxdb2 --dry-run`
completed cleanly in 56s, showing a sane 14-package removal plan with
`signalk-plugin-watchdog` merely re-resolved (version unchanged), not
pruned.

The **real** `npm uninstall signalk-to-influxdb2` (no `--dry-run`) then
failed, exit 254:
```
npm warn tarball tarball data for signalk-plugin-watchdog@file:signalk-plugin-watchdog (null) seems to be corrupted. Trying again.
npm error enoent Could not read package.json: ENOENT: /home/pi/.signalk/signalk-plugin-watchdog/package.json
```
Root cause and what it did and didn't damage:
[signalk-plugin-watchdog's self-referencing `file:` dependency](#signalk-plugin-watchdogs-self-referencing-file-dependency)
below — read that card before retrying. Net effect of the failed attempt:
**`signalk-to-influxdb2` is untouched** (still in `~/.signalk/package.json`
and `node_modules`, confirmed after) — the transaction aborted before
reaching it. A harmless stray top-level directory,
`~/.signalk/signalk-plugin-watchdog/` (not the working
`node_modules/signalk-plugin-watchdog/` copy, not the git-tracked
`plugins/signalk-plugin-watchdog/` source — nothing on the boat or in this
repo referenced that top-level path), got pruned as extraneous mid-run;
confirmed no operational effect (no watchdog errors in the log since,
plugin dependency in `~/.signalk/node_modules/signalk-plugin-watchdog/` is
intact).

**Also found while investigating this**: a live concurrent session
(`claude --continue --remote-control symphony-pi`, running since 2026-08-25,
several tailnet ssh sessions attached) was actively using the SignalK
app store — installing `signalk-noaa-space-weather@0.29.1` — within two
minutes of this session's `systemctl restart signalk` for the postgsail
fix above. No sign either session broke the other, but it's real evidence
the "check for a live session first" rule in this repo's CLAUDE.md isn't
theoretical here; a `who`/`ps aux` check that shows no process mid-install
at the instant you look can still be running one 90 seconds later. Retry
the uninstall only after fixing the `file:` dependency below, and re-check
for concurrent activity immediately before, not just at session start.

To finish once the `file:` dependency card is resolved: `cd ~/.signalk &&
npm uninstall signalk-to-influxdb2`, remove
`~/.signalk/plugin-config-data/signalk-to-influxdb2.json`, restart
signalk, confirm the `HistoryAPI` errors stop in the log, and drop
`signalk-to-influxdb2` from the repo's `signalk/package.json` (the
tracked manifest a clean reinstall is built against) in the same commit.

## signalk-plugin-watchdog's self-referencing `file:` dependency

`~/.signalk/package.json` on the boat declares
`"signalk-plugin-watchdog": "file:./node_modules/signalk-plugin-watchdog"`
— the dependency's `file:` source points at its own resolved location
inside `node_modules`, rather than at an external directory. This is what
made the influxdb2-uninstall attempt above fail: npm's reify step for a
self-referencing `file:` dependency errored trying to read a package.json
from a derived top-level path (`~/.signalk/signalk-plugin-watchdog/`, no
`node_modules/`) that doesn't correspond to anything real, and aborted the
whole transaction. This will recur on **any** future `npm install` or
`npm uninstall` in `~/.signalk` that touches dependency resolution, not
just this one.

Likely fix: repoint the entry at the boat's actual git checkout,
`file:../symphony/plugins/signalk-plugin-watchdog` (confirmed present and
matching `node_modules/signalk-plugin-watchdog`'s contents on the boat,
2026-08-26), so it's a real external source rather than a self-reference.
Untested — didn't attempt it this session given a live concurrent session
was using the box (see above); this is exactly the kind of npm-tree
mutation that shouldn't run next to someone else's app-store install.
Confirm afterward with a `npm install --dry-run` in `~/.signalk` that it
resolves cleanly.

## PR #189 verification, 2026-09-01 — the reconnect branch fires but does not recover

Reproduced the bug, verified the fix's detection path, found two real
defects in the PR, fixed both, and then established that **the PR still
does not restore sensor data after a D-Bus drop.**

**Working repro of the original bug** (answers the maintainer's question):
`/etc/dbus-1/system-local.conf` with `<limit name="auth_timeout">20</limit>`,
`systemctl reload dbus`, restart SignalK → `electrical/batteries/5C90`
404s, plugin mute. At 1000ms and 100ms the handshake still wins; 20ms is
reliable. Also reproduces off-boat against a private `dbus-daemon` with no
BLE hardware — see the PR comment draft.

Note the plugin uses **`@jellybrick/dbus-next`** (a fork, via
`@naugehyde/node-ble`), not upstream `dbus-next`.

**Why three earlier attempts read as "the branch never fired":** it logs
nowhere observable. `index.js:233` used `plugin.debug` (dark without
`DEBUG=bt-sensors-plugin-sk`) and the backoff used only `setStatusText`
(admin UI, not the journal). Absence of a journal line was never evidence.
Fixed on branch `verify-reconnect-logging`: connection loss, each retry and
successful reconnect now log at error level.

**The working fault-injection harness** (the thing three sessions failed to
find). `systemctl restart bluetooth`, `systemctl restart dbus.service` and a
gdb fd-close all fail to trigger it. What works:
1. Drop-in `/etc/systemd/system/dbus.service.d/99-test-restart.conf` with
   `Restart=always`, `RestartSec=1`, `daemon-reload`. **Required** — not
   just for safety: with stock `Restart=no` the plugin retries against a bus
   that never returns, so only detection can be observed, never recovery.
2. `sudo kill -9 $(systemctl show dbus -p MainPID --value)`.
3. dbus respawns in ~1s. NetworkManager dies (D-Bus-activated, `Restart=no`)
   — `systemctl start NetworkManager` afterwards; recovers in ~10s.
   SSH/Tailscale are unaffected throughout.
Arm `systemd-run --on-active=8min` to restart dbus/NM/signalk as a net.

**Two defects found and fixed** (branch `verify-reconnect-logging`, commit
`7282ae3`):
- A dying bus emits once *per queued write*, not once. Every error called
  `scheduleBluetoothReconnect()` → restart loop, ~170 errors/min. Now only
  the session still held in `btSession` may drive a reconnect; replaced
  sessions are detached and ignored. Measured: 170 errors → 1.
- `plugin.start()` clears `sensorMap` but **not** the discovery, progress
  and device-health timers — only `plugin.stop()` does. Replaying `start()`
  alone hits `!discoveryIntervalID`, finds the stale id set, and never
  restarts discovery. Now tears down first, bounded at 10s since a dead bus
  can hang `stop()`.
- Also resets `plugin.stopped` if `start()` throws, so a failed attempt
  isn't silently the last one.

**Diagnosed and fixed 2026-09-01 (later session), commit `f1c9cb8` (squashed from the four commits below).**
The reconnect path came back with a clean log and BlueZ discovering, but
no GATT sensor ever republished. Cause: every GATT connect goes through
one process-wide serial queue (`connectQueue` in `BTSensor.js`), and
dbus-next never settles a method call that was pending when the
connection died. A connect action in flight at the moment of the kill
stayed `pending=true` for the life of the process and every connect the
re-created sensors queued sat behind it. Deterministic repro: tail the
journal for the sensor's connect and `kill -9` dbus on it — the earlier
"kill between polls" runs passed by luck (kill 20:13:03Z, data 20:14:59Z)
and only the mid-connect kill wedged (kill 20:19:32Z, frozen at
20:18:33Z until the healer). The fix: fresh queue before replaying
`start()`; `deviceConnect()`'s timeout rejects instead of throwing from
inside the timer callback (an uncaught exception, not a rejection — it
stalled the queue the same way); `plugin.stop()` stops sensors
concurrently so every sensor drops its timers even when an earlier one
hangs disconnecting from a dead bus. Verified on the committed code with
the mid-connect kill: kill 20:35:21Z, reconnect logged 20:35:35Z, first
fresh 5C90 values 20:36:09Z, polling normally after, no SignalK restart.

Pre-existing and untouched: `Response timed out (+30s)` / `DBusError: Not
connected` from `JBDBMS.js` run 8–63/hour in steady state over the prior
24 h (BMS link flakiness); the `preparePath ... reading 'substring'`
TypeError (JBDBMS protectionStatus path) and the influxdb2 `HistoryAPI`
`reading 'filter'` rejection both predate every kill. The two Victron
advertisement devices time out in `waitDevice` on a plain restart too.

**Landed:** fork `main` and `verify-reconnect-logging` both at `f1c9cb8`
(PR #189 now carries all four commits); maintainer comment posted with
the repro, harness, diagnosis and timestamps. Boat left on
`verify-reconnect-logging` at `f1c9cb8`, all scaffolding removed (no dbus
drop-in, `Restart=no`, no healer timer, no `/tmp` files), services
active, data flowing.

## The rebuild fork — strategic context

Not a card and not a decision waiting on Mark; see the standing-context note
at the top of [kanban.md](kanban.md). Kept here because the evidence is real
and a session picking up HALOS work should have it.

For HALOS: on 2026-08-25 a Node runtime swap silently removed
`signalk-server` and the boat ran dark for two days — OpenPlotter's own
installer did it (`signalkPostInstall.py:45` runs `apt autoremove -y nodejs
npm`). The survey of `halos-pi4` (`ssh pi@halos-pi4`) found Traefik +
Authelia + Homarr core with containerised SignalK/QuestDB/Grafana/OpenCPN/
AvNav, all systemd-managed and declaratively configured under `/etc/halos/`
— architecturally where this repo was already heading, and it would retire
the "move off hand-rolled bash wrappers" item in `priorities.md` outright.

Against: HALOS undoes real work already done. And the bench box is a 2 GB
Pi 4 sitting at ~358 MB available under load, so HALOS in practice implies
the HALPI2.

Downstream of the fork, but not blocked on it: Grafana's return, the
dockerization track, and the SD-card/boot-media strategy.

## Bench-test containerized pypilot on HALOS

Blocked on PR #37 merging. Run this prompt exactly as written, no
improvising around it:

```
Bench-test the containerized pypilot on the HALOS Pi. Follow RUNBOOK.md § "pypilot in a container" → "Run it on a Pi with the IMU" verbatim; do not improvise around it. Record: image build time and peak memory on arm64, whether `docker exec pypilot i2cdetect -y 1` shows 0x68, whether imu.heading moves when the Pi is tilted, and whether pypilot 0.71 reads a copy of the boat's 0.56 ~/.pypilot without complaint. Copy the boat's state, never move it. Update reference/pypilot_containerization.md § "Not yet verified" with what you measured and close the board card.
```
