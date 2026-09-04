# Dev/prod config overrides — Mark's review, opened 2026-09-03

Mark's framing, recorded at the moment he raised it. Nothing here is decided;
this is the brief for his own pass, not a plan a session should execute.

## The complaint

The override design for dev is still confusing, and the mechanism for
changing or updating the overrides was fragile the last time he touched it.
The open question is whether the overrides are helping or hindering at all —
not how to document them better.

Two things he wants held together:

- **The differences are too wild.** Dev and the cards diverge more than the
  actual difference in environment justifies. Where a value must differ, the
  goal is a narrow, obvious seam — not a separate shape of config.
- **Changing one should not be an act of archaeology.** Whatever the seam is,
  he has to be able to find it and edit it himself without reconstructing how
  it works first.

## The example he gave

Switching the healthchecks.io ping URL between cards. That same mechanism
should extend to a **dev** configuration on `:3000` — on the Windows box or
the Mac — so that these integrations can be verified end to end off the boat,
rather than only ever being exercised for real on a card. He named it as one
instance of a general pattern, not the item itself.

## Where this came from

The preflight `state` check compares the card's SignalK config against the
boat's and FAILed on five files that differ *by decision*: the
`plugin-config-data` of the four plugins disabled on HALOS, and `venus.json`
with its own host. Excluding them by name (5a04053) is what keeps the check
readable, and is also exactly the smell — by-design differences accumulating
as a list of exceptions somewhere else.

## Not yet looked at

Which mechanisms are actually in play (sops values, host_vars, Ansible
templates, `.env`, per-card plugin config), how many places a single logical
override touches, and whether a dev profile on `:3000` can share any of it.
That inventory is the first hour of the work, whenever it starts.

## Proposed design — from the review session, 2026-09-03

Proposal, not a plan. Mark walked the pain points and agreed the shape;
the inventory spike below decides whether it holds.

**Diagnosis.** The five mechanisms (compose bind-mount pins, the hostvars
git filter, Ansible host_vars, `.env.j2` by hand, preflight exclusion lists)
are sorted by *kind of value*. The tier framework (alpha/beta/gamma/prod,
`signalk-noaa-space-weather/docs/rig-tiers-and-lifecycle.md`) sorts by
*tier*: every tier is the tier above plus a well-defined override set.
Nothing in the repo is shaped that way, and the preflight exclusion list is
the symptom -- the HALOS override set exists only as what the checker skips.

**Shape: main is the source of truth; two verbs.**

- `overrides/<tier>.yaml` -- small patches (file, JSON path, value).
  Secrets are sops key names, never values. Expected rows: heartbeat URL
  per instance, ntfy URL, pushover relay off, the four HALOS-disabled
  plugins, venus host, alpha's port and plugin symlink.
- `seed <tier> <dir>` renders prod config plus the tier's patches into the
  tier's data dir. Same script for `./signalk` (beta container),
  `~/.signalk` (alpha native), and the HALOS card via Ansible. Replaces the
  bind mounts and the hostvars filter.
- `capture <tier>` reverse-diffs the live dir against the rendered
  expectation, subtracts the override paths, and lands the residue on main.
  Preflight's `state` line becomes `capture --dry-run`; the hand list goes.
- Overrides must be *patches*, not replacement files: a reverse diff can
  only subtract an override it can see as data.

**Prod hotfix path (UI change on the boat).**

- Hourly sync moves from fetch-only to autostash-rebase, so the local change
  rides on top of whatever landed on main. Conflict only when the same key
  changed on both sides; then leave the stash intact, log, alert.
- A JSON-aware three-way merge driver, shared with capture, so pretty-printed
  neighbours don't conflict at the line level.
- Secret guard becomes a sorter, not a wall: capture runs residue values
  through `secretguard.py`; plain values land in the config file, secret-
  shaped values go to sops via `add_inplace_secret.sh` with the placeholder
  written in; ambiguous ones stop with one question naming field and file.

**CD.** GitHub Environments (beta/gamma/prod) hold the promotion gates and
the deployment record; execution is pull-based on prod and push over the
tailnet elsewhere, via the Tailscale GitHub Action (ephemeral `tag:ci`
node, needs an ACL rule -- Mark's paste). Near-term tiers: alpha native,
beta the :3000 container, gamma the HALOS card, prod the boat. An always-on
cloud gamma is deferred; AWS gets its own card later, noting why the last
attempt stalled.

**Spike first (the "first hour").** Inventory every place a logical
override touches today; check whether any plugin rewrites its config with
extra keys on save (breaks the reverse diff); confirm which command
actually bombed on the dirty-checkout pull (boat `git pull` vs dotsync --
the latter is a yadm problem, out of scope here).

**Evidence, 2026-09-03 (parallel session):** the RUNBOOK "final state sync"
rsync flattened the five HALOS-specific plugin files (the four disables and
venus.json) with the boat's copies. The override set lived only in the
preflight exclusion list, so nothing protected it. That session amended the
RUNBOOK; the structural fix is `seed` owning those files.

## Spike findings — inventory run 2026-09-03, read-only

Answers the three questions the spike names. Nothing was changed; every
line below is from the repo, the SignalK server source at
`~/signalk-server`, or the local alpha data dir.

### 1. Where each logical override touches today

Seven logical overrides. The count is "files you must find and agree before
the value is right", not lines.

| Override | Touchpoints | Count |
|---|---|---|
| heartbeat ping URL, per card | sops keys `heartbeat_url_symphony_{pi,halos}`; `ansible/host_vars/symphony-pi.yml`; `ansible/host_vars/symphony-halos.yml`; `ansible/roles/monitoring/templates/boat-heartbeat.json.j2`; `ansible/roles/monitoring/tasks/main.yml` step 24; `host/boat-heartbeat.json` (sops, holds ONE url, fallback only); `host/install.sh` `:keep` flag on that copy line; `.gitattributes` | 8 |
| ntfy server URL, per machine | `signalk/plugin-config-data/signalk-ntfy.json` (placeholder in git); `.gitattributes` `filter=hostvars`; `.hostvars.yaml`; `hostvars.local.yaml` (gitignored, per machine); `hostvars.local.yaml.example`; `scripts/hostvars_filter.py`; `scripts/setup-git-filters.sh` + the machine's `git config` filter entries | 7 |
| pushover relay off in dev | `dev/plugin-config-overrides/signalk-pushover-notification-relay.json`; `docker-compose.override.yml` mount line; `dev/plugin-config-overrides/README.md` table; the repo copy it shadows | 4 |
| healthcheck `n2k-can0` off in dev | same three + the repo copy; the dev file also *drops* the `mail` block, so it is not a patch of the repo copy but a different document | 4 |
| four plugins disabled on HALOS | **nowhere as data.** `scripts/halos_preflight.sh` `EXPECT`/`CONFIG_EXPECT`; prose in `intermediate_files/claude_slop/halos-swap-plan.md`; the truth lives only in the card's live files | 2 (+live) |
| venus host on HALOS | **nowhere as data.** `CONFIG_EXPECT` in the preflight; the value only in the card's live `venus.json` | 1 (+live) |
| alpha's port and plugin symlink | **nothing in this repo.** `/home/solace/.signalk` is untracked: `settings.json` `"port": 3010`, `node_modules/signalk-noaa-space-weather -> /home/solace/signalk-noaa-space-weather`, and its own 24 plugin configs | 0 |

Three things the table makes concrete:

- **Alpha is on 3010, not 3000.** The review's ":3000 dev" is the *beta*
  container (`compose-signalk.yml` publishes 3000). Alpha and beta are
  different tiers on different ports, and only beta exists in the repo.
- **Beta has no seam at all, because the repo dir *is* the live dir.**
  `compose-signalk.yml` bind-mounts `./signalk:/home/node/.signalk`, so the
  dev server writes its config straight into tracked files. That is why the
  two dev pins had to be read-only single-file mounts, and why `capture`
  for beta is a no-op while `seed` for beta would overwrite the repo.
- **The two override sets that matter most exist only as a skip list.** The
  four HALOS disables and the venus host have no representation anywhere a
  program can read. Corroborated live, this session: another session ran
  RUNBOOK § "final state sync" verbatim and rsync replaced exactly those
  five files with the boat's copies. The documented procedure destroys the
  override set, and the preflight then reports `ok state` — because the
  five files it would have flagged are the five it is told to ignore. This
  is not a hypothetical cost of the current shape; it is a same-day
  incident.

### 2. Do plugins rewrite their config with extra keys on save? Yes.

Three distinct writers, all confirmed in source:

- **UI save writes the whole schema-defaulted object.**
  `PluginConfigurationForm.tsx:461` seeds RJSF `formData` from the current
  data and submits `{...formData, enabled, enableLogging, enableDebug}` to
  `POST /plugins/:id/config`; `plugins.ts:1051` hands `req.body` straight
  to `savePluginOptions`, which is a bare
  `JSON.stringify(data, null, 2)` (`plugins.ts:316-330`). No merge, no
  filter — every field the form rendered lands in the file, including ones
  the operator never touched, plus the three top-level flags. Key order
  becomes schema order.
- **Plugins write their own config at runtime.**
  `plugins.ts:940` exposes `app.savePluginOptions(configuration)`, which
  replaces the whole `configuration` object. A plugin that persists state
  this way rewrites the file with no operator action.
- **Startup can rewrite a file unprompted, and wipe it.**
  `plugins.ts:1000` — a plugin whose package declares
  `signalk-plugin-enabled-by-default` and whose config file has no
  top-level `enabled` key gets the file rewritten at server start with
  `enabled: true` **and `configuration: {}`**. One tracked file is exposed:
  `signalk/plugin-config-data/AdvancedWind.json` has no `enabled` key. It
  is the only one.

Measured evidence, same plugin id across two live dirs (alpha vs the repo
copy, key-set diff):

```
signalk-noaa-space-weather  only in alpha: drapEnabled, drapInterval,
                            goesFluxEnabled, goesFluxInterval, listLevel,
                            enableDebug, enableLogging
freeboard-sk                only in repo:  pypilot.*, weather.*
signalk-logbook             only in repo:  crewNames, displayTimeZone,
                            logNotifications, notificationMinLevel, ...
kip, course-provider, sk-ais-status  further key-set differences
```

`enableDebug`/`enableLogging` appearing only on the alpha side is the UI-save
signature exactly as the code predicts. The repo's own history shows the same
thing: `signalk-noaa-space-weather.json` gained `enableDebug`/`enableLogging`
in b212b3e and lost them in 7b96712, and `signalk-ships-bells.json` gained
`playbackOutputs`/`mopidySettings`/`alertsSettings` wholesale in d44f4d4.

**Consequence for the proposed design.** A reverse diff cannot assume the
live file is "rendered output plus operator edits" — a save also adds keys
nobody chose, drops keys a newer schema no longer defines, and reorders. So
`capture` must diff *semantically* (parse both, compare by JSON path) and
must classify a key that appears on the live side only and equals the
plugin's schema default as noise, not residue. Without that, the first UI
save on the boat produces dozens of spurious residue rows. The JSON-aware
merge driver the design already calls for is necessary but not sufficient;
the schema defaults are the other half, and they are readable from the
running server (`GET /plugins`, which is where the form gets `plugin.schema`).

### 3. Which command bombed on the dirty-checkout pull

**`dotsync`, not the boat's `git pull`.** `dotsync` is
`alias dotsync='yadm pull --rebase --autostash && yadm alt && yadm status --short'`
(`~/.bashrc:158`). Claude Code rewrites `.claude/settings.json` in its own
key order, the three-way merge saw a whole-file conflict, the autostash
re-apply failed, `yadm pull` still exited 0, and `$HOME` was left holding
invalid JSON and an unseen stash. It happened on the boat, and it is
written up in dotfiles `README.md` § "Why the cron sync is ff-only".

Out of scope, and already fixed: `~/.local/bin/dotfiles-sync.sh` never
rebases, stashes or merges — it is fast-forward-only, so the outcomes are
"fast-forwarded", "level", or "skipped" with the blocking files named.
Symphony's own `host/boat-hourly-sync` is fetch-only by deliberate design
and has never pulled.

**This is a live objection to the design's prod-hotfix path.** The proposal
moves the hourly sync "from fetch-only to autostash-rebase". Autostash-rebase
on a checkout a plugin is actively rewriting is the same shape as the failure
above, on a repo whose conflicts are pretty-printed JSON. The fetch-only
posture was chosen for the reason in `host/boat-hourly-sync`'s own comment —
"an unattended pull would move config out from under running containers".
If the sync is going to pull, the JSON merge driver and a stop-the-server
window need to land first, not alongside.

**Correction, 2026-09-03 (checked on the boat):** `~/.signalk` is a plain
directory, not a symlink into `~/symphony`, and the checkout there is clean
and 30 behind main. A UI change on prod never dirties git, so the
"autostash-rebase hourly sync" above is a no-op for the hotfix path and is
withdrawn. The prod seam is the rsync between `~/.signalk` and the
checkout's `signalk/` -- the same step that flattened HALOS today. `capture`
is a JSON-level diff between the live dir and the checkout, applied there;
the git side stays an ordinary pull. The dirty-checkout bomb Mark remembers
is therefore dotsync, not the boat's symphony checkout.

**Confirmed, 2026-09-04:** it was dotsync *on the boat*, but in `$HOME`
(the yadm tree), not in `~/symphony`. dotfiles `README.md` § "Why the cron
sync is ff-only" records it contemporaneously: "That happened on the boat."
Both halves hold -- the boat's symphony checkout is clean and stays clean,
and the dirty-checkout bomb was a different repo on the same machine. The
guess that it was a dev box is withdrawn.
