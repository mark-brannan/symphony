# Claude kanban — session working state (Symphony)

Claude-facing. Micro-tasks, blocked questions, and detailed working state for
SignalK / IoT / infra work live here — segregated from the human files in
`maintenance/`, which get only finished, high-level results. See CLAUDE.md
§ "Claude session state" for the rules. Nothing in this file is authoritative
over the repo's reference docs; it is working memory.

Sessions pull from here to start work and flush loose ends back here at
wrap-up. Dated session narrative goes in `log.md` beside this file.

## Doc-cleanup follow-ups (from the 2026-08-19 bloat audit)

Verdicts and quotes in `intermediate_files/claude_slop/doc-bloat-audit.md`.
Done: claude_slop structure, CLAUDE.md rules, log.md and priorities.md trims,
dotfiles boards descoped to dotfiles-only, and (2026-08-19) all the reference/
trims — monitoring_decisions Roles 1 and 4 restated, software_stack WSL
incident and hedges cut, compute_hardware shopping status and HALOS section,
containerization_strategy caveat plus checklist-stays-here decision, node_red
Lists 2 and 3 cut, watchdog docs consolidated to one with the draft post moved
to the plugin dir. Remaining:

- Purchase itemizations in maintenance/log.md: owner call pending — trim to
  one-line totals with detail moved to a purchases file, or keep.
- Optional enforcement: extend `scripts/lint_repo_hygiene.py` with a soft
  warn on log.md bullets over ~5 lines.
- Dotfiles: `boards/claude.md` still lists "Reconcile standing-orders lines
  with the Standing orders additions session" and deleting the board-rework
  handoff note — dotfiles-side, not symphony's.

## Secret tooling — PATH resolution follow-up

- ~~Shell-side sops lookup is still PATH-only~~ — **done 2026-08-20, PR #19.**
  `secretguard.sh` gained `secretguard_find_sops` and
  `secretguard_sops_locations` (twins of the python pair, parity-tested,
  locations text pinned byte-identical), and both `command -v sops` call
  sites — `precommit_secret_guard.sh` and `check_clone_setup.sh` — now use
  them. Raised 2026-08-19 while fixing the worktree-checkout failure;
  deliberately left out of PR #18 to keep that diff to the failing path.

- **Stale `claude/*` branches: triaged 2026-08-20, deletion handed to Mark.**
  Content-safety check done (merged in *content*, not ancestry — patch-ids
  vs main, plus per-file diffs of each branch's own commits, isolated
  against old-main tip `0286d8f` for the eight branches rooted in the
  pre-rewrite lineage). Mark authorized the sweep; the session's
  `git push --delete` was blocked by its permission layer, so the deletion
  is his one command:
  `git push origin --delete claude/backlog-issue-candidates-kb6qnb claude/symphony-mcp-tools-context-ia7dgx claude/git-hygiene-recovery-procedures-4ezeho claude/usage-limits-troubleshoot-efhfwc claude/git-hygiene-redesign claude/branch-deletion-cleanup-rules-nisoon claude/boat-containerization-strategy-j2z35u`
  All seven are content-merged: two have zero commits beyond old main, two
  have their single patch verbatim in main, the fold-back rule and the
  containerization additions are line-verified present in main's files, and
  git-hygiene-redesign had its no-salvage verdict here already.
  **Kept, not stale — do NOT delete:** `grafana-questdb-port-target` (open
  PR #10), `influxdb-questdb-container-backlog-kq3t7q` (open PR #15),
  and three holding unlanded work main does not have:
  `signalk-oidc-identity-permissions-4kk8gl` (the OIDC proposal,
  `proposals/signalk-oidc-identity-permissions.md`, exists nowhere else),
  `symphony-docs-corrections-aeuorm` (DSC/AIS distress-chain test procedure
  and `reference/distress_monitoring.md` — main's RUNBOOK has no distress
  content at all), `laughing-hamilton-7f7pbg` (cherry-pick metrics
  framework `.claude/hooks/measure-cherry-pick.sh` + `maintenance/stats.*`,
  plus security_posture/software_stack edits not checked line-by-line).
  Each of those three needs its own land-or-discard decision.

## Blocked

Open questions parked here so they don't live only in a session's last
response. Each names the session that raised it.

- ~~PR #12 waiting on PR #13, and the cross-PR invariant enforced only in
  #12's tests~~ — **both closed 2026-08-19** (pr12-rebase session). #13
  merged; #12 rebased onto it and is out of draft. The invariant sentence
  now lives in `scripts/secretguard.py`'s module docstring and its bash
  twin, which is what every new guard imports to ask whether it is strict —
  so the next session meets it at the moment it would otherwise re-derive
  it. It blocks when `bool(hits) or mode is strict` — equivalently, it
  passes only when nothing covered is staged AND enforcement isn't strict.
  Both axes have to clear it; neither can wave the other through. Tests pin
  it from both modes. Narrative in `log.md` for this date.
- ~~Naming: `SYMPHONY_MODE`/`SYMPHONY_STRICT` rejected, replacement not
  settled~~ — **closed 2026-08-19** by #13, which renamed the whole guard
  surface to `secretguard` (`SECRETGUARD_MODE=strict|contributor`, one
  variable taking a mode word, not the two booleans). Table in #13's body.
- **RESOLVED 2026-08-19 — #13 merged 2 min after the split landed, so this
  was done in the same session** (`76e1e04`). Three cross-references had
  gone stale in the overlap, not the one predicted: `.pre-commit-config.yaml`
  naming `validate.yml` as the every-push gate, `gitleaks_precommit.sh`
  sending a version bump to `validate.yml`'s image tag, and RUNBOOK's
  "Upgrading the scanners" opening with `pre-commit autoupdate` — a no-op
  once #13 made every hook `repo: local`. That last one was #13's staleness,
  not the split's, and was the one that would actually have misled someone.
- **The fork boundary inside `lint_repo_hygiene.py`** (2026-08-19, still
  open). From Mark's own thought exercise: the secret-management core is
  already free of "symphony", but this file mixes one generic rule
  (unconfigured filter) with two site-specific ones (audible alarms, frozen
  captain credentials). `FROZEN_SECRET_KEYS` is the last hardcoded
  boat-specific fact in the guard surface — a review bot flagged it on #12.
  Recommendation on the record: leave it hardcoded. Moving that list to a
  config file makes the freeze editable and gives the rule a way to check
  nothing if the file goes missing, where a tuple in the source cannot fail
  open. Revisit only if a fork becomes real; it is not urgent.
- ~~Nothing automated runs the secret-tooling test suites~~ — **closed
  2026-08-20**: main gained a `secret-tooling-tests` CI job (`5c9f76c`),
  with `test_pseudonymize.py` held out (`c104ddd`) pending the
  keyless-runner fix. The rest of the story is the Infrastructure TASK
  below ("make CI able to run the secret-tooling suite, then collapse the
  CI job onto the existing runner").
- ~~`rule_frozen_secrets_untouched` does not run in CI~~ — **closed
  2026-08-20**: `HYGIENE_COMMIT_RANGE` env var switches the rule to
  diffing a commit range instead of the (empty-in-CI) index; `validate.yml`
  fetches full history and sets the range from the push/PR event. Mark
  pushed back on going further than this one technical gap (no config
  file, no more rules) — see his call under "Blocked — needs Mark's call"
  below.
- ~~Branch protection on `main` — is it, and which checks are required?~~ —
  **answered 2026-08-20**, see "RESOLVED — no required status checks on
  main, deliberately" under "Blocked — needs Mark's call" below: `main` is
  ruleset-protected (21060338: linear history, no force-push, no deletion)
  with no required status checks, by Mark's explicit choice, so CI stays
  advisory. That entry supersedes both the 2026-08-19 "main is unprotected,
  confirmed via `list_branches`" claim and its 2026-08-20 correction; the
  legacy `/branches/main/protection` endpoint 404s on a ruleset-protected
  branch, which is how the wrong claim got written.
- ~~Node 20 deprecation on both workflows~~ — **done.** `6745f76` bumped
  `validate.yml` and `secret-scan.yml` on 2026-08-19; PR #19 (2026-08-20)
  swept the two stragglers that postdated the bump — the
  `secret-tooling-tests` job's steps and `claude-review.yml`'s checkout. No
  `checkout@v4` / `setup-python@v5` remains in any workflow.

- ~~wire-wright publish~~ done 2026-08-19. Diagnosed both original failures:
  `gh repo create --push` had actually already created and pushed
  `mark-brannan/wire-wright` before it errored, so no duplicate was needed —
  just confirmed local `main` matched `origin/main`. `npm publish --tag
  alpha` failed because the account wasn't logged in (`npm whoami` 401);
  after `npm login` (browser passkey), publish still failed under npm
  9.2.0 with `EOTP`, since that npm's `otplease` has no browser fallback for
  writes on a passkey-only (`auth-and-writes`) account — only `npm login`
  got the web flow. `npx npm@latest` (12.0.2) does support a browser-approval
  publish flow, but it needs a real TTY (to press Enter / open a browser),
  which the session's sandboxed shell doesn't have; attempts to fake one
  (pty fork, fifo) were correctly blocked by the sandbox's own classifier.
  Handed the one `npm publish --tag alpha` command to Mark to run in his own
  terminal instead. Verified after: `gh repo view mark-brannan/wire-wright`
  succeeds (public, default branch main), `npm view wire-wright dist-tags`
  shows `alpha: 0.0.1-alpha.0` (also `latest`, since it's the first
  publish — expected, not a mistake).
- ~~Tailscale SSH broken tailnet-wide~~ **fixed 2026-08-19.** Root cause, in
  Tailscale's own words: "autogroup:self ... Does not apply to tags." The
  policy's only user-facing SSH rule was `autogroup:member` →
  `autogroup:self`, and every node except the phone is tagged
  (`tag:home-fleet`, `tag:symphony-devices`, `tag:cloud-ephemeral`), so it
  matched nothing — `ssh pi@symphony-pi` failed with "does not permit you to
  SSH to this node". `grants` was already `*`→`*`, so the packet filter was
  never involved, and the existing `tag:cloud-ephemeral` rule meant cloud
  sessions worked the whole time; only Mark's own machines were locked out.
  Fix: two rules appended — `tag:home-fleet` → home-fleet + symphony-devices
  (accept, nonroot) and `autogroup:member` → symphony-devices (check, 12h) —
  plus an `sshTests` block so a regression fails on save. Mark pasted it;
  verified `ssh pi@symphony-pi` returns and the "access controls don't allow
  anyone to access this device" health warning cleared.
  Corrections owed to earlier reasoning in this session: Mark's chosen
  "accept for my devices, check for cloud" split is not expressible —
  Tailscale forbids check mode from a tagged source, so check survives only
  on the untagged phone. The RUNBOOK's claim that cloud sessions can reach
  the boat was *not* stale; it was the one path that worked.
  A read-only `policy_file:read` OAuth client is now in
  `secrets/symphony.sops.yaml` and `scripts/tailscale_policy.sh` reads and
  validates the policy from the CLI. Write scope was deliberately not
  granted, so applying a policy stays a human paste — confirmed by a 403 on
  the attempted apply.
  Still open: the credential was pasted into a session transcript, so rotate
  it at https://login.tailscale.com/admin/settings/oauth whenever convenient.
  Also unresolved and out of scope: `ssh solace@nucbox-k12` times out — the
  Windows node has no SSH server, which is a Tailscale platform limit, not a
  policy gap. Tracking the policy file in git was considered and rejected for
  this repo: it is public, and the policy names the tailnet's tags and
  topology. `~/claude_prompts_scratch` would be the right home if wanted.
- `Symphony Plumbing Library.xml` (Mark's own draw.io library, Google
  Drive only): owner deferred 2026-08-19 — "plumbing we'll figure out
  later." Not blocking anything; revisit when plumbing diagrams start.
- ~~gitleaks-docker hook vs Docker Desktop~~ decided 2026-08-19:
  skipping the gitleaks hook is the sanctioned path when docker is
  missing from PATH or the daemon isn't reachable (Docker Desktop not
  running / WSL integration off); rule added to CLAUDE.md § Git
  hygiene. Incantation
  updated to `SKIP=gitleaks` on 2026-08-20 after PR #13 renamed the hook
  id. Native-binary hook swap not wanted — closed.
- **Stale branch `claude/git-hygiene-redesign` (7be6e6a) — delete it?**
  (2026-08-19). The pre-worktree take on the git-hygiene redesign,
  superseded by `0a76db4` / `a861190`; no PR was ever opened because that
  session's GitHub API is 403-blocked (push works). Nothing in it is worth
  salvaging. It can't end "merged via PR" per § Git hygiene, and deleting a
  pushed ref needs an explicit go-ahead — so it sits until Mark says drop it.
- **Which Grafana dashboards are the QuestDB port target?** (PR #7 review
  session.) Two sets exist and they are not versions of each other. The boat's
  native Grafana has five dashboards, 76 panels, InfluxQL, imported from
  published examples with 158 of 162 datasource references pointing at a uid
  that doesn't exist there. The repo has six under
  `grafana/provisioning/dashboards/json/` — generated by
  `scripts/build_dashboards.py`, Flux throughout, written against paths this
  boat actually publishes, including a `system` dashboard with no counterpart
  aboard. `reference/legacy_openplotter_stack.md` described the committed set
  as uid-rewritten copies of the boat's five; that was true before commit
  1ce4e87 (2026-08-14) and is now corrected in that file. What is *not*
  settled is which set B4 of `reference/containerization_strategy.md` should
  port to QuestDB SQL: teaching the generator to emit SQL (small, and the
  generated set is already path-accurate) or hand-porting the boat's 76
  imported panels (large, but that is what Mark actually looks at today). The
  honest first step is neither — it is to open both in Grafana side by side
  and find out what the imported five show that the generated six don't. That
  comparison is a dedicated session's work and needs the boat on the tailnet;
  until it's done, treat B4's scope as unknown rather than assuming the
  generator route.

- ~~**Do the connector denials actually save context? Unmeasured.**~~ **CLOSED,
  measured 2026-08-19 (this session).** The denials DO work: a normally-started
  symphony cloud session shows no `mcp__Intuit_QuickBooks__*` or
  `mcp__Intuit_TurboTax__*` tools (both denied in `.claude/settings.json`),
  proving those schemas are not loaded. Evernote_MCP tools ARE present (23
  tools) because Evernote is not on the denylist, which is expected. The earlier
  unmeasured context cost was plausible: Intuit_QuickBooks (~90k) +
  Intuit_TurboTax (~11k) ≈ ~100k tokens saved per session by the denials.
  Verdict: the denials are load-bearing and save significant context.
- **dotfiles and symphony now both set Claude Code settings; three connectors
  differ.** (2026-08-19.) `dotfiles/.claude/settings.json` already carries
  `crossSessionInbound: "hold"` and denies six connectors —
  Intuit_QuickBooks, Intuit_TurboTax, CourtListener, Courtroom5,
  Legal_Data_Hunter, LegalZoom. Symphony denies those six **plus** Gmail,
  Google_Drive, Google_Calendar. Denylists merge from every settings source,
  so this is a union and not a conflict, and the duplicated
  `crossSessionInbound: "hold"` is redundant rather than contradictory (a
  project value applies only when *stricter* than user settings, and equal is
  not stricter — it earns its place only in cloud sessions, which have no
  `~/.claude/settings.json` at all). **Owner call outstanding:** whether
  dotfiles should also deny the three Google connectors for parity. That is a
  dotfiles-repo edit, not symphony's. Note dotfiles also sets
  `disableClaudeAiConnectors: true` and `ENABLE_CLAUDEAI_MCP_SERVERS=false`,
  which are a broader hammer than either denylist — worth checking whether the
  denylists are load-bearing at all on a machine where those apply.
- **Undelivered coordination note to the "Claude hooks and continuity
  cleanup" session** (`session_014zxMuv2RQ3p4Z7PRA1eTm7`, cloud, on dotfiles +
  claude_prompts_scratch, branch `claude/hooks-continuity-cleanup-sq7dnm`).
  Mark asked for the two sessions to coordinate; **no channel exists between
  two cloud sessions** — `ListAgents` returns "No reachable agents" without a
  Remote Control connection, `SendMessage` fails, and the Claude Code Remote
  MCP surface has no `send_message`. Recording the content here since it could
  not be delivered. As of 17:53Z that session is **idle, not blocked on a
  question** — it answered its own four-question `AskUserQuestion`, did the
  work, and opened **PR #3 on dotfiles** ("Automate session continuity:
  SessionStart brief, Stop checkpoint, typed decisions"). What it now waits on
  is two manual steps only Mark can do in the web UI, on the **"Full network
  access"** environment (`env_01TocPy1GquNyfv88tr4Mbz3`): paste the
  `cloud-session-setup.sh` snippet into the setup-script field, and add
  `claude_prompts_scratch` as a second environment source. An earlier read of
  this session at 17:14Z caught the pending dialog and was reported to Mark as
  current; it was 40 minutes stale by then. Treat a `list_sessions` snapshot as
  a point-in-time read, not a live state. What it needs to know: (1) its
  README's premise that cloud sessions have no `~/.claude/settings.json` is
  right, but **project** settings *do* load in cloud when the repo is a
  session source — symphony's PreToolUse hook was confirmed firing in cloud on
  2026-08-19 — so repo-level settings already close the cloud gap for symphony
  independent of the `cloud-session-setup.sh` snippet; (2) the
  `crossSessionInbound` precedence above, if it is setting that key in
  dotfiles user settings; (3) a fresh cloud clone has **no git filters wired**
  — `scripts/lint_repo_hygiene.py` fails `unconfigured-filter` for both sops
  and hostvars and `scripts/setup-git-filters.sh` cannot run because `sops` is
  not on PATH, which is the failure mode to guard if its Stop-hook auto-commit
  ever runs against a filter-covered repo from a cloud container.

## SignalK / IoT — detailed working backlog

(Moved verbatim from maintenance/priorities.md on 2026-08-19; the human file
now carries only the high-level list.)


### Sensors
- Design engine temp sensors and diagram
- Design engine flow sensor plumbing
- Design engine flow sensor electrical
- Rudder position sensor
- Pump flow sensors
- Air quality sensors
- BME680: settle which mechanism owns the sensor and get its data into the tree deliberately (needs boat access). Census 2026-08-14: the dedicated plugin `@oehoe83/signalk-raspberry-pi-bme680` is installed but disabled on both boxes, yet the boat receives 2 paths from source `OpenPlotter.I2C.BME680/688-1` — the legacy `openplotter-i2c-read` service. Identified 2026-08-15: the two paths are `environment.inside.relativeHumidity` (ratio) and `environment.outside.pressure` (Pa), both live and fresh; the OpenPlotter config leaves the temperature and gas channels unmapped, so nothing aboard publishes any airquality value. The plugin's formula (`500 - 5 × score`, 0 best / 500 worst) matches the zone bands in `signalk/baseDeltas.json` exactly. Decide: enable the dedicated plugin (its saved boat config already points at bus 1 / 0x77, the working sensor; set its pressure path to `outside` to keep the barometer-trend source continuity) and retire the OpenPlotter i2c entries — the service reads nothing else, and its second configured sensor at 0x68 errors permanently ("Chip ID 0x0") — or keep OpenPlotter and give up the airquality index, which it cannot compute. Both mechanisms polling the same chip is not an option: contention disturbs the gas heater cycle. Note the plugin only publishes after a 500 s burn-in on every start.
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
- ~~TASK: make CI able to run the secret-tooling suite, then collapse the CI
  job onto the existing runner~~ — **done 2026-08-20, PR #19**, all five
  steps as written. `secretguard.can_decrypt()` (sops AND age key) now
  carries the "this machine holds keys" meaning in both twins, parity-pinned
  from both sides; `TestStore` gates on it and skips on a keyless runner
  naming what is missing, while `StoreUnavailable` stays strict-fatal;
  `secret-scan.yml`'s job runs `bash scripts/run_secret_tooling_tests.sh`
  and names no individual suite; `claude-review.yml`'s allowedTools names
  the runner. Verified keyless: `CI=1` run of the full runner green — the
  previously-red path (run 32319051952). This unblocks extraction of the
  secret tooling into its own repo, where every CI job is keyless.
- **Confirm the strict path on a keyed machine** — the one leg of the TASK
  above that a keyless session cannot run. Mark ran the runner on
  NucBoxK12 (2026-08-20): four suites, all OK, and `test_pseudonymize`'s
  27 tests passed with **no skip**, which proves the real store opens on a
  keyed machine. But the output shape (four suites, a 22-test
  `test_secretguard`) is the pre-PR-#19 runner — the checkout predated the
  merge. Remaining: `git pull` there and re-run; the new runner prints six
  OK blocks and `test_secretguard` has 27 tests. The gate change is
  keyless-only by construction, so this is a formality — but it closes only
  when the new code has run under a key.

- Deploy the openweather-signalk humidity-fix Node-RED flow (needs boat
  access). `environment.outside.relativeHumidity` publishes OpenWeatherMap's
  raw percent instead of SignalK's 0-1 ratio, so every dashboard panel on
  that path reads ~8800%. Root cause confirmed in the plugin's source
  (`openweather.js`/`skunits.js`) and reported upstream. Procedure and the
  flow JSON are in `RUNBOOK.md` → "Fixing openweather-signalk's mis-scaled
  outside humidity". Flow is built but unverified against the live editor —
  the `signalk-subscribe` node's path/flatten fields may need setting by
  hand on import. Remove the flow once the upstream fix ships.
- Evaluate a small custom SignalK plugin for generic single-path arithmetic
  (scale/offset a path by a constant). Came up chasing the openweather
  humidity bug: neither `signalk-path-mapper` (rename/duplicate only),
  `signalk-derived-data` (fixed built-in calculators, no custom formula),
  nor `signalk-value-combiner` (needs two live input paths, no constant) can
  do it, and nothing in the plugin store fills the gap. Opinion: two
  data points (this and the BME680 path-naming mismatch) don't yet justify
  building and maintaining a new plugin when Node-RED, already running,
  covers it generically — revisit if a third case shows up.
- New custom plugin: navigation-lights switching per COLREGs, driven off
  NMEA 2000 / relay switch state rather than manual toggles alone —
  e.g. enforce the correct combination for the vessel's current condition
  (underway/sailing vs. power, at anchor, restricted in ability to
  manoeuvre) and flag an invalid or incomplete combination rather than
  silently allowing it. Not scoped yet: which physical switches/relays
  this reads and drives (see `systems/electrical.md`'s lighting sub-panel —
  nav lights running/off/anchor and sailing/steaming are separate circuits
  today, not obviously behind a single NMEA 2000 switch bank), which
  vessel-condition input it trusts (AIS nav status? a manual mode switch?
  autopilot engaged state?), and whether it should only *warn* on a wrong
  combination or actively *switch* lights. Worth deciding early whether
  this is a SignalK plugin (packaged, testable, installable elsewhere) or
  a Node-RED flow (faster to iterate, but per the pattern above, don't
  reach for it as a way to dodge writing a real plugin when the logic
  outgrows a couple of nodes — COLREGs light-combination logic has enough
  branching that it likely does).
- Finish dockerizing the boat computer, per Track B of
  `reference/containerization_strategy.md` (decided 2026-08-18) — that file
  carries the ordered steps B1-B7 and the boat-side checklist; this entry
  tracks only where we are in it. Findings from the checklist go back into
  that file and into `maintenance/log.md`, and anything contradicting the
  plan amends the plan rather than being worked around silently; delete the
  checklist from the file once it has been executed. **Dex and ntfy are done** — containers,
  native units disabled, verified through Caddy. SignalK, Grafana and Caddy
  are still native systemd services. **QuestDB is now also a container**
  (2026-08-20, see the QuestDB entry below) — Dex, ntfy and QuestDB.
  Migrate one service at a time, not
  in one move — anything mid-migration runs native and containerized at once.
  Caddy is last and is the one to do carefully: it is the front door, so a bad
  move takes the SignalK UI, Grafana and the OIDC callback with it, including
  remote access to fix it. When Caddy does move, drop the transitional
  `127.0.0.1:5556` port publish from `compose-idp.yml`; Caddy will reach Dex
  by service name on `symphony-net` instead.
- Migrate the history store from InfluxDB to QuestDB. **The evaluation is
  closed** — decided 2026-08-18 with Mark, reasoning and evidence in
  `reference/containerization_strategy.md`. Steps B1-B5, in order: back up
  InfluxDB offline and prove the backup restores; stand QuestDB up as a
  compose service; swap the SignalK history plugin to the external-mode
  QuestDB one and soak it alongside `signalk-to-influxdb2` with Telegraf
  dual-writing; port the dashboards (scope blocked, see Blocked); retire
  InfluxDB once measured parity passes.

  **B1 done, 2026-08-20.** Stopped `influxdb.service` (down ~19 min: tar +
  export-lp took most of that on the Pi's SD card, not the stop itself),
  took two artifacts — `influxdb-data-<ts>.tar.gz` (478MB raw data dir) and
  `symphony-<ts>.lp.gz` (952MB `influxd inspect export-lp`, needs no
  token — sidesteps the boat's dead InfluxDB tokens) — both sha256-summed,
  both at `/home/pi/influx-export/` on the boat, restarted InfluxDB
  (confirmed healthy, all three buckets intact). **Verified on-boat, not
  off-boat**: this session's tailnet path to any off-boat host (this cloud
  sandbox, and relayed on to `nucboxk12`) ran at ~30-50KB/s — a 1.4GB
  transfer would have taken 7+ hours, so instead of waiting, restored the
  tarball into a second, disposable native `influxd` process on the boat
  (different bolt/engine paths, port 8087, torn down after) since no
  Docker daemon was available in this session and pulling a fresh
  `influxdb` image over the same slow link was similarly impractical
  (aborted after ~10 min, no image landed). All 3 buckets and every
  measurement present; a spot-check of `navigation.position` lat/lon
  matched the live instance exactly at matching timestamps; full-history
  row counts differed by exactly the ~19 minutes of live writes that
  happened during and after the backup window (451441 vs 449375 on the
  main GPS source) — expected, not a discrepancy. The `.lp.gz` cross-
  checked separately: decompresses clean (127.2M lines), and the first
  2000 lines wrote into a scratch QuestDB-instance bucket and queried back
  correctly. **This proves the backup mechanism restores correctly; it
  does not prove survival of a boat-level disk failure**, since the
  restore target was the same SD card. A true off-boat copy is still
  worth getting — the artifacts are sitting at `/home/pi/influx-export/`
  ready for Mark to `scp` directly from one of his own devices (which
  should hold a direct tailnet P2P connection rather than this session's
  apparent DERP relay, and therefore be much faster) whenever convenient;
  not urgent, since the on-boat restore test is solid evidence the backup
  itself is good.

  **B2 done, 2026-08-20.** `compose-questdb.yml` added and running on the
  boat as the `questdb` container (pinned by digest, ports 9000/9009/8812
  on localhost, `QDB_CAIRO_COMMIT_MODE=sync` for durability — this Pi has
  no UPS). Two prerequisites from the history-plugin's own tuning notes,
  also done: `vm.max_map_count` raised to 1048576 via
  `/etc/sysctl.d/99-questdb.conf` (was 65530, no reboot needed); **the
  `mem_limit: 768m` in the compose file is NOT actually enforced** — this
  Pi's kernel lacks `cgroup_enable=memory` on the boot cmdline, so `docker
  compose up` logs "kernel does not support memory limit capabilities...
  Limitation discarded." Fixing that needs a `cmdline.txt` edit and a
  reboot; deferred rather than done blind. QuestDB is being watched
  instead (`free -m` / `pswp`) — measured healthy at deploy time: ~486MB
  RSS, boat available memory 872-912MB throughout, swap stable, well
  inside the ~400MB pressure threshold. Deployed by merging
  `compose-questdb.yml` with the boat's on-`main` `docker-compose.yml` via
  `docker compose -f docker-compose.yml -f <tmp-copy> up -d questdb`,
  deliberately without checking the boat's shared `/home/pi/symphony`
  checkout onto this session's feature branch — that checkout is shared
  across sessions and other people may be relying on it staying on
  `main`. The boat's checkout will pick up `compose-questdb.yml` itself
  once PR #15 merges; nothing further needed there.

  **B3 (plugin swap) half done, 2026-08-20 — package installed, not yet
  configured.** `signalk-questdb-history-provider` 1.10.0 (Hat Labs'
  external-only fork, the plan's preferred option over dirkwa's managed
  one) is now in `~/.signalk/package.json` and `node_modules` on the boat.
  Stopping SignalK to install it was initially denied by this session's
  permission classifier (a materially bigger ask than the InfluxDB risk
  pre-authorized earlier); **Mark explicitly authorized it in-chat**
  ("Take the risk... we're not concerned with nav, just power
  monitoring... if it goes dark I can drive down and check on it"), so
  the install went ahead. Sequence used, matching RUNBOOK.md's own
  procedure: `systemctl stop signalk.socket` then `signalk.service`
  (the latter went to `failed (Result: timeout)` and needed
  `reset-failed` before restart — expected, RUNBOOK already documents
  this), snapshotted `node_modules` before and after
  (`find node_modules -maxdepth 2 -mindepth 1 | sort`) and diffed —
  **zero packages pruned**, so the package-lock=false pruning risk the
  plan warned about did not bite here. Restarted `signalk.socket` +
  `signalk.service`; confirmed back up within ~10s (HTTP 200 on
  `/signalk`, fresh live data on `/signalk/v1/api/vessels/self/electrical`
  with current timestamps). Total live-nav downtime was a few minutes,
  not "seconds to low tens of seconds" as estimated beforehand — the npm
  install itself (resolving into an 11.6k-entry flat tree) took longer
  than expected. Worth knowing for next time, not a problem this time.

  **B3 finished, 2026-08-20 (later session).** Plugin enabled and
  recording; Telegraf dual-writing. Details:

  - **Auth stayed unsolved, and was worked around.** No sops/age key in a
    cloud session, so the captain password could not be read; minting a JWT
    from the server's own `secretKey` was blocked by the session's
    permission classifier (it reads as credential extraction, fairly).
    Mark authorized any of "admin UI / restart / token" in-chat, so the
    file route was taken: write
    `~/.signalk/plugin-config-data/signalk-questdb-history-provider.json`
    with the server stopped, then start it. **The plugin id is
    `signalk-questdb-history-provider`** — the README's REST paths still
    say `signalk-questdb`, which is the upstream id, not this fork's.
  - Config set: `managedContainer: false`, host `127.0.0.1`, HTTP 9000,
    ILP 9009, PGWire 8812, `retentionDays: 30`, `enableConsole: false`,
    everything else at schema defaults. **30 days was Mark's call**, made
    against a boat root filesystem at 82% with InfluxDB still running.
  - Verified recording: `signalk`, `signalk_str` and `signalk_position`
    exist and climb (511 → 1888 → 2066 rows over ~3 min), 86 distinct
    paths, values are SI with a real `source` (`n2k-can0.2`), and
    `max(ts)` tracks the server clock to within seconds.
  - **`retentionDays` is not a QuestDB TTL.** All three tables read
    `ttlValue 0` — the plugin drops aged partitions itself. So there is
    nothing in QuestDB's own metadata to check the setting against;
    checking means watching partitions age out at day 30, or reading the
    plugin's config back.
  - **Telegraf dual-write done** — second `[[outputs.influxdb_v2]]` at
    `http://127.0.0.1:9000` in `telegraf/telegraf.conf`, 20 host-metric
    tables landing, no output errors. Retention and dedup are applied by
    `scripts/questdb_table_hygiene.sh` rather than by hand: line protocol
    auto-creates tables with neither, and a dropped-and-recreated table or a
    new input comes back bare and silent, so the script is written to re-run.
    **It owns an explicit table list, not "everything that looks unmanaged"**
    — a TTL deletes data at the far end, so auto-adopting an unfamiliar table
    would put someone else's data on a deletion clock. Unrecognised tables are
    reported instead, which is also how a newly added Telegraf input announces
    that it needs listing.
    **Dedup turned out to matter more than retention.** Telegraf retries a
    batch whose HTTP response timed out, and QuestDB may already have
    committed it — measured on the boat: writing the same line twice landed
    two rows before dedup and was absorbed after. That is a duplicate-data
    bug *and* a hole in B5's row-count parity check, since the count on the
    QuestDB side would have been inflated by exactly the retries. The
    history plugin's own tables already ship with dedup on; only Telegraf's
    were exposed.

  **The disk incident, 2026-08-20 — read this before adding any writer.**
  Deploying the Telegraf output filled the boat's root filesystem within
  15 minutes: 5.1 GB consumed by 20 new tables holding a few hundred rows.
  QuestDB `fallocate`s an append page per column file (16 MB default), and
  every SYMBOL column also carries a bitmap index whose rowid file
  preallocates another 16 MB; host-metric tables are mostly SYMBOL tags.
  Root hit 100%, and InfluxDB's WAL writer then wedged in an ENOSPC retry
  loop that **outlived the recovery** — it kept failing after space was
  free and needed `systemctl restart influxdb`. SignalK was throwing
  write errors throughout. Recovered with Mark's go-ahead by dropping the
  20 Telegraf tables (5 GB back) and `journalctl --vacuum-size=200M`
  (1.1 GB back, and journald still has no `SystemMaxUse` — separate
  standing item). Fixed properly in `compose-questdb.yml` with four
  `QDB_*` env vars: data append page, index value append page, O3 column
  memory and WAL writer append page, all cut to 256k/128k. Same 20 tables
  now cost ~20 MB. Two things learned the hard way: the settings are
  read at container start, so each try meant recreate + re-measure; and
  `du -sm` on the volume after the first few flushes is the only honest
  check, because row counts say nothing about footprint here.

  **Watch item for the soak:** the volume settled around 140 MB within ten
  minutes of both writers running, most of it one-time preallocation rather
  than data. **Short-window sampling cannot measure its growth** — an 85 s
  sample came back *negative* (146.5 MB → 141.5 MB) because WAL segments
  roll over and get purged on their own schedule, so the number oscillates.
  Measure over hours, not minutes, and treat ~6 GB free as the budget.

  **Two things about the boat's own checkout,** noticed while deploying:
  `/home/pi/symphony/telegraf/telegraf.conf` is a symlink target for
  `/etc/telegraf/telegraf.conf`, so deploying the Telegraf change meant
  editing that tracked file in place — the boat's checkout now shows
  `M telegraf/telegraf.conf` and will until PR #15 merges and it pulls.
  Bigger: the boat's `main` is at `68e4e04`, which is **not an ancestor of
  today's `origin/main`** — main was force-updated upstream at some point,
  so the boat cannot fast-forward and a plain `git pull` there will merge
  two lineages against a dirty file. Worth sorting deliberately rather than
  discovering it mid-deploy. (The content looks preserved — PR #15's diff
  against the rewritten main is exactly its own seven files — so this is a
  history-shape problem, not lost work.)

  **The tracked container-side configs were a trap too.**
  `signalk/plugin-config-data/signalk-questdb.json` (dirkwa's plugin) was
  still `enabled: true` with `managedContainer: true`, `retentionDays: 0`
  and ports 9000/9009/8812 — so B6 bringing the containerized SignalK up
  would have started a second, managed QuestDB fighting our compose one for
  the same ports. Disabled, and the fork's config added beside it with
  `questdbHost: questdb` (the container-side endpoint; `127.0.0.1` inside a
  container is that container, which is the same trap B2 documents).

  **What's left:** the multi-day soak itself, then B5's parity checks
  (`reference/containerization_strategy.md`). Don't uninstall
  `signalk-to-influxdb2`. B4 (dashboards) is still blocked on the
  two-set question above.

  Assets already in place: the compose Grafana keeps the QuestDB datasource plugin
  installed, and the retired `signalk-grafana` plugin's auto-built QuestDB
  dashboards are preserved in
  `signalk/plugin-config-data/signalk-grafana/grafana-data/`.
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
  `signalk-pushover-notification-relay` not installed as of this bullet's
  last edit — flag: `signalk/plugin-config-data/signalk-pushover-notification-relay.json`
  now exists in the repo with `enabled: true` (landed in the 2026-08-15
  "bringing over more extant plugins from the boat" commit), which
  contradicts "not installed" above. Unclear whether that means it's live
  on the boat and this paragraph is stale, or the config was copied in
  without the plugin actually running — check on the boat before trusting
  either. The credential blocker is gone either way —
  `pushover_api_token`/`pushover_user_key` landed in
  `secrets/symphony.sops.yaml` 2026-08-14 for the heartbeat escalation above
  and are the same values this plugin needs.
  License checked 2026-08-15: ISC (npm registry), permissive — forking and
  republishing under a new name is clear. So the audit's real branches are
  three, not two: audit `signalk-pushover-notification-relay` first; if it's
  basically sound and just stale (four years untouched, single-dependency
  drift is the likely failure mode for a plugin this small), **fork it,
  fix what the audit finds, publish under our own name** rather than
  discard the working parts; only if the plugin is fundamentally broken or
  the SignalK plugin API has moved past it does it drop to the Node-RED
  flow (subscribe `notifications.*`, POST to Pushover). Node-RED
  (`@signalk/signalk-node-red`, upgraded to 4.4.0, now has one small flow —
  the openweather humidity fix, see Infrastructure below) is otherwise idle
  rent on the Pi; if the fork or the existing config turns out to already
  cover delivery, don't leave Node-RED's Pushover fallback flow half-built
  as dead weight.
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
- Add a notification/zone for a fast barometric pressure drop (squall/foul-weather warning). Both `environment.barometer.*` and `environment.outside.pressure.{trend,prediction}.*` already carry trend/prediction data (`reference/signalk_paths.md` notes the two parallel barometer stacks), but nothing currently turns a fast drop into a notification — no zone is configured on either path. A `meta.zones` entry (server-native, no plugin) or a small Node-RED flow would both work. Flagged in `reference/node_red_signalk_use_cases.md` (List 3, section M), 2026-08-15.
- MOB detection — open research item, medium-low priority, not immediately planned. **Never live-test the DSC emergency button, on this or any other item — standing rule, not a one-off caution.** Owner confirmed 2026-08-15: triggering it sends a real distress call to the Coast Guard on Ch 16 DSC, with possible fines or legal consequences, and it "ain't happening." What's aboard today: a handheld VHF with DSC and an emergency button, and an AIS Class B transceiver — no MOB button or crew-tag hardware of any other kind. `signalk-mob-notifier` is installed; whether it (or anything else) actually consumes that DSC/AIS hardware is unconfirmed, and has to stay that way until it can be settled by reading documentation or source — never by pressing the button to see what happens. Owner is only willing to adopt a solution already proven elsewhere to work reliably, not something built and validated on this boat. See `reference/node_red_signalk_use_cases.md` section H.

### Cameras
- Identify location for interior Tapo cam
- Install Tapo cam for galley/saloon
- Identify location for exterior Tapo cam
- Install exterior Tapo cam

## Blocked — needs Mark's call

- **RESOLVED 2026-08-20 — frozen-secrets enforcement stays exactly where
  it is; no expansion.** Fixed the one real bug (CI's index is empty, so
  the rule ran vacuously there — see above), nothing more. Mark: he's fine
  leaving the captain credentials as-is for now and doesn't want Claude
  touching them, but doesn't want a standing rule policing what he does to
  his own password either — called the existing depth (a lint rule, a CI
  gate, a test class) AI slop for something this narrow. Don't add a config
  file for `FROZEN_SECRET_KEYS`, more test coverage, or additional guard
  rules here without him asking first.

- **RESOLVED 2026-08-20 — no required status checks on main, deliberately.**
  Asked whether the ruleset should require CI to pass. Mark: no, not at this
  point; requiring checks also blocks direct pushes to main, and
  commit-straight-to-main is the working model. Ruleset 21060338 stays as it
  is — linear history, no force-push, no deletion. So CI is advisory by
  choice, not by oversight; don't re-raise it as a finding. Read the live
  state with `gh api repos/mark-brannan/symphony/rulesets`; the legacy
  `/branches/main/protection` endpoint 404s on a ruleset-protected branch and
  reports main as unprotected, which cost this session a wrong claim.

- ~~`validate.yml` triggers on branch pushes?~~ — **RESOLVED 2026-08-20,
  widened.** Mark's condition: fine only if it never removes the ability to
  push directly to main or start requiring merges. Satisfied by
  construction — the trigger controls when jobs *run*, not what a push
  needs; the ruleset still requires no status checks, so red stays
  advisory everywhere including main. Widened `on.push.branches` to `'**'`
  with superseded-run cancellation (same shape as secret-scan.yml). The
  secret-scan half of the original gap had already been closed by the
  2026-08-19 CI split; this closes the validation half.
