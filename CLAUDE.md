# Working conventions — Symphony project

This repo combines Symphony's maintenance tracking with her SignalK/IoT
infrastructure. Conventions below cover the maintenance side
(`maintenance/`, `reference/`) and the docs for the software stack
(`RUNBOOK.md`, `reference/software_stack.md`). Ansible practices aren't
covered here.

## Files
- `maintenance/log.md` — chronological ship's-log record of work done.
- `maintenance/priorities.md` — current backlog and triage.
- `reference/specs.md` — vessel identity, registration, and physical particulars.
- `reference/vendors-parts.md` — vendor contacts and parts sourcing.
- `reference/software_stack.md` — how the SignalK stack is built and why.
- `reference/host_provisioning.md` — how hosts get built, and the Ansible plan.
- `RUNBOOK.md` — operating procedures for the software stack.
- `systems/*.md` — one file per boat system, intentionally empty for now.
  Don't impose section structure on these until asked — the owner wants to
  arrive at the right structure organically, not have it templated in.

## log.md
- **A human file.** Written for Mark skimming for "when did X change." Claude
  appends only when a meaningful, high-level piece of work is actually DONE —
  never micro-tasks, session narrative, self-corrections, or verification
  detail. That material goes in `intermediate_files/claude_slop/log.md`.
- Real ship's log style: short, factual, dated entries — 1-3 lines per event,
  past tense, no reasoning. Not a place for technical specs/part numbers
  (those belong in the relevant `systems/*.md` file once populated). If
  you're explaining *why*, it belongs in `reference/` or the slop journal.
- Chronological, oldest entry first, true append — new entries go at the
  bottom, matching `tail` semantics.
- Use whatever date precision is actually known: a full date, a month, or
  just a year. Don't force false precision onto an approximate memory.
  A `## Date unknown` section at the bottom is fine for confirmed-done work
  with no date yet.

## priorities.md
- **Physical boat work is tracked in Evernote, not here.** When the owner asks
  for a hands-on task — rewiring something, a paint job, a fitting to replace —
  Evernote is the authoritative list; don't answer from this file and don't add
  the task to it. What's still listed here overlaps by history, which is fine
  and gets pruned over time. This file stays authoritative for the SignalK /
  IoT section.
- **A human file.** High-level items only, one to a few lines each. Claude
  edits it when real feature-level work completes or the owner asks — never
  to park session state, evidence dumps, "done" annotations, or rules for
  other sessions. All of that lives under
  `intermediate_files/claude_slop/` (`kanban.md` for cards, `kanban-detail.md`
  for their detail, `log.md` for history).
- Kanban-flavored, not GTD: **In Progress** (keep this small — WIP limit of
  roughly 2-3 items, matching the owner's stated preference for steady
  completion over a sprawling backlog) / **Backlog** (ordered —
  position implies priority) / **Someday/Maybe** (uncommitted ideas).
- Finished items don't stay here — they move to `log.md` and get removed
  from this file, so it always reflects only what's still open.
- The **SignalK / IoT — high level** section is the human summary; the
  detailed working state for each item is in
  `intermediate_files/claude_slop/kanban-detail.md`, linked from a card in
  `kanban.md`. Update both when an item opens or closes; update only the
  board for anything smaller.

## Claude session state — `intermediate_files/claude_slop/`
- **All Claude working state is segregated here**, away from the "good"
  content in `maintenance/` and `reference/`. The owner chose this location
  and the name deliberately (2026-08-19): if a future session thinks a file
  here deserves promotion, that's a proposal to Mark, not a move to make.
- `kanban.md` is this project's board under the global **Open loops** rule
  (`~/.claude/CLAUDE.md` § Open loops — the standing-orders file, not this
  repo). That rule owns the mechanics: `## Yours` / `## Claude's`, one line
  per card (a link plus the action in the imperative), `blocked:` only when
  the card is actually blocked, cards deleted on completion rather than
  logged in place. Write the card the moment a loop is found, not at
  wrap-up — by wrap-up the detail that made it actionable is gone. Pull from
  it to start work; it also carries the detailed state behind
  `priorities.md`'s high-level SignalK/IoT list.
- **A wrap-up ends with zero unmeasured decisions** (owner's rule,
  2026-08-19). Every open question is either executed in-session or put to
  Mark as an explicit decision prompt before the turn ends, and his answer
  recorded here. Parking a question in a file without prompting him for the
  call is not wrapped up — a `## Yours` card is a prompt already made, not a
  substitute for making it.
- `log.md` — dated session journal: wrap-up narrative, self-corrections,
  verification detail. Append at the bottom. This is where the continuity
  rule's "write state before ending" output goes.
- Other files under `intermediate_files/` are per-task scratch. Nothing in
  the directory is authoritative over `reference/` or the running system.
- **Do not** put symphony session state in the dotfiles repo's `boards/`
  files — that experiment was rolled back 2026-08-19; those boards are for
  dotfiles work only.

## Evernote (where physical tasks actually live)
- Sessions can read and write Evernote directly. The MCP tools
  (`create_task`, `search_tasks`, `search_notes`, `get_note`, …) are
  **deferred** — they appear by name in the deferred-tools list, currently
  prefixed `mcp__38e9d000-…`, and must be loaded with ToolSearch
  (`select:<full tool name>`) before calling. If no such tools are in the
  deferred list, the connector isn't attached to your session; say so
  instead of improvising.
- Everything is in the "Symphony" notebook. The task notes:
  - **"Symphony Important Tasks"** — the priority list and the catchall,
    both (owner's description). Default destination for a new physical
    task unless a per-system note clearly fits better. Note GUID
    `8a3a821c-90b4-e29b-db37-6b261d0dbfec` — pass this directly to
    `get_note`/`create_task` rather than re-resolving it via `search_notes`.
  - "Symphony Electrical Tasks", "Symphony Plumbing Tasks", "Symphony
    Rigging Tasks", "Symphony Clean/Paint/Finish", "Symphony Woody Tasks" —
    per-system lists.
- To add a task to an existing list: `get_note` for the note, take a task
  group id from the ENML placeholder (`--en-id:` in the group div), pass it
  as `taskGroupNoteLevelId` to `create_task`. Omitting the group id creates
  a new group at the end of the note, which clutters — reuse the existing
  group.
- `search_tasks` is a case-insensitive substring match on task labels and
  is the quick answer to "is X already on the list."
- Task granularity: size each task so one person can finish it in a single
  work session, with few interdependent steps — ADHD-friendly sizing, per
  the owner's explicit ask (made twice). "Paint the bilge" is several
  tasks — de-rust, clean, prime, paint — not one.

## reference/specs.md
- Flat `key: value` list, one item per bullet (plain consecutive lines
  collapse into one paragraph in markdown — always use `- ` list items).
- Precise/technical field names over colloquial ones: e.g. "USCG Official
  Number," not "Documentation number." Match the terminology actually used
  on the source document (COD, registration, etc.) where there is one.
- No parenthetical hedging or uncertainty notes in this file. If something
  is uncertain, ask the owner directly rather than writing a caveat into
  the doc.
- Where a field has both a vessel-specific documented value and a generic
  stock/design-reference value (e.g. from sailboatdata), prefer the
  vessel-specific one and drop the generic duplicate — don't carry both as
  if they were peers.

## RUNBOOK.md
- **Actions only.** Every section answers "what do I do." Commands, the
  order to run them in, and how to tell it worked. If a passage doesn't
  change what the reader does next, it belongs in
  `reference/software_stack.md` instead.
- A procedure isn't done until it's been run verbatim once, including the
  transition path for existing checkouts — the boat is never a fresh clone.
- Include a *why* only where its absence causes the wrong action — e.g.
  "don't skip `verify`, here's what silently breaks without it." One or two
  sentences, next to the step. Not a background section.
- No point-in-time status. Don't write down which containers were up, what
  was broken on a given day, or what an audit found last week — that rots
  into a lie within days. Durable config traps are fine; snapshots aren't.
- Don't editorialize about the system's design, security posture, or
  industry practice. State the trap and the fix.

## reference/*.md
- Explanatory material lives here: architecture, design rationale, known
  risks, why a thing is the way it is.
- Still no speculation. Verify before asserting — check the running system,
  the config file, or the vendor's own docs. Never infer behavior from a
  config field name or a plugin's title and write it up as fact.
- When a claim can't be verified, leave it out or flag it in conversation.
  A gap is better than a confident guess.

## Reaching the boat
- `ssh pi@symphony-pi`. Use `pi` — it's the only account on the box. The
  hostname is Tailscale's; plain `symphony` doesn't resolve. Both of Mark's
  dev machines already hold the credentials, so don't go hunting for keys or
  IPs. This has cost several sessions the same detour; the details are in
  `RUNBOOK.md` § Reaching the boat over Tailscale.
- If ssh is refused by *policy* rather than by the host, read the two
  distinct Tailscale refusals and the tag-vs-`autogroup:self` trap in
  `RUNBOOK.md` § SSH users and the periodic check before touching anything.
  `scripts/tailscale_policy.sh` prints the live policy read-only; applying a
  change is Mark's paste into the admin console, never a session's.

## The boat Pi's memory headroom
- Expected state: SignalK, InfluxDB, Grafana, Caddy, Dex and Telegraf all run
  and stay enabled. Telegraf is the intended host-metrics source, not a
  leftover — don't remove it.
- InfluxDB and Grafana are the release valve. Any session may `systemctl stop`
  them to recover roughly 600 MB when the Pi is under real memory pressure,
  without asking first. Say so in your session so the others aren't surprised.
- **Stop, don't disable.** They come back at the next reboot, which is what we
  want: the pressure is normally transient (an `npm install`, a rebuild), not
  a standing condition. A stop that survives a reboot is a decision for the
  owner. This already bit us once — both were stopped on 2026-08-11 and
  silently came back on 2026-08-13.
- Real pressure means swap activity or available memory under ~400 MB, not a
  high load average on its own. Check `free -m` and `grep ^pswp /proc/vmstat`
  before stopping anything.

## Security posture
- `reference/security_posture.md` records the calls already made about this
  boat's threat model — the LAN as trust boundary, plain HTTP alongside the
  TLS front door, local password logins as the offline fallback, certificate
  expiry offshore. **Read it before reporting any of those as a finding.**
  They are decisions, not oversights, and re-arguing them each session costs
  the owner the same judgment twice.
- Raising a real objection to one of them is fine — one line, then move on.
  Re-deriving the whole analysis is not.
- **The owner's email address, GitHub handle, and GitHub numeric user ID
  (including `oidc.sub` values that encode it) stay in the clear, fixtures
  and docstrings included.** Decided, written up in
  `reference/security_posture.md`, and re-raised by session after session
  anyway. Never report it as a finding, never offer to scrub it, don't
  mention it at all — not even as a one-line aside at the end of unrelated
  work. This is the one item where "raise a real objection in one line"
  does not apply; the objection has been heard and rejected.
- **Do not touch the `captain` credentials.** `signalk_captain_password` and
  `influxdb_captain_password` in `secrets/symphony.sops.yaml` are frozen at
  Mark's instruction until his own hardening pass. Don't rotate, split, or
  "helpfully" strengthen them — and don't offer to; the offer itself is what
  he asked to stop. `scripts/lint_repo_hygiene.py` fails any commit whose
  diff touches them.

## Working style, generally
- No unsolicited notes, hedges, or "this may have changed" commentary
  embedded in any doc — flag uncertainty in conversation, keep the files
  themselves clean and current.
- Ambiguity in old records (multiple sources disagreeing, unclear dates)
  gets flagged to the owner rather than silently resolved by guessing.

## PR automation and session cost
The general conventions — wake on events not timers, never bind a scheduled
wakeup to a live session, one watcher per PR, batch review responses, long
agentic loops (not long conversations) are the real expense, park open
questions durably rather than in scrollback, and draft PRs are mine to get
ready-and-green without being asked — live in
`dotfiles/.claude/rules/code.md` § PR ownership / § Babysitting a PR is
cheap. Symphony-specific instances of those:
- The no-scheduled-wakeup rule is enforced by a PreToolUse hook — if it
  denies a call, take the redirect rather than looking for another way to
  schedule. On a machine with `dotfiles` installed this comes from its
  user-level `~/.claude/hooks/no-persistent-polling.sh`, wired in every
  session; without it, nothing in this repo enforces the rule mechanically.
- One-watcher-per-PR has bitten this repo concretely: two sessions babysat
  PR #8 while four triggers queued against it.
- Open questions park in `intermediate_files/claude_slop/kanban.md` under
  Blocked — that's this repo's "durable" per the dotfiles rule.

## Git hygiene
- At the start of every session, before doing any work: `git fetch` and check
  whether the local branch is behind `origin/main`. Multiple sessions push to
  this repo, so a checkout that looked current yesterday usually isn't. Get
  onto the tip of main first — landing work on a stale base means a rebase and
  hand-resolved conflicts later, in files another session has since rewritten.

### Work in an isolated worktree, not the shared checkout
- **Default to an isolated git worktree for any editing session, unless Mark
  is actively driving the session with you right now and asks for edits
  directly in the existing checkout — then just do that, no ceremony.** A
  worktree is a second, disposable folder checked out from this same repo on
  its own throwaway branch: edits there can't collide with whatever another
  session (or Mark, hand-editing) has staged or left uncommitted in the main
  checkout, and the whole folder can be thrown away without touching anyone
  else's work. This is the fix for the root cause behind most of the
  destructive-command incidents below — those all trace back to several
  sessions sharing one working directory and one index.
- In this harness, use the `EnterWorktree` tool at the start of the session
  (default `fresh` mode branches it from `origin/main`, so the fetch-and-check
  above is answered by construction) and `ExitWorktree` when the task is done
  — `action: "remove"` for a clean exit, `discard_changes: true` if you're
  sure nothing in it is worth keeping. Outside this harness, the equivalent is
  `git worktree add ../symphony-<slug> -b claude/<slug> origin/main`.
- **A worktree's own branch is not "branching" in the sense of the rule
  below.** It's always short-lived, always merged back to `main` same-session,
  and never left pushed on its own — push each verified commit from it
  straight to `origin main` (fast-forward) as you go, per "Work on main"
  below. If `origin/main` moved since you branched, `git fetch && git rebase
  origin/main` inside the worktree and push again — that rewrites only your
  own not-yet-shared commits, never anyone else's history, so it doesn't need
  asking.
- **Inside your own worktree, the destructive-command ban further down
  doesn't apply** — `git stash`, `git reset --hard`, `git checkout -- .`, all
  fine, because the only thing at risk is your own uncommitted work in a
  folder nobody else touches. It still applies in full, everywhere, to
  anything that mutates a *shared* ref: `git push --force` to `main` or any
  pushed branch, `git branch -D` of one, deleting remote refs. Land on main
  with ordinary fast-forward pushes; never force one open.
- Keep worktrees short-lived — same session, same task. A worktree revisited
  days later has quietly reacquired the "how far behind main am I" problem
  this whole model exists to avoid.
- **`docker compose up` must never depend on a host bind mount whose source
  can be absent** — a directory that doesn't exist yet when Docker starts a
  container gets silently created by dockerd (root, even under WSL) as
  `root:root` before the container runs. `compose-grafana.yml` used to
  bind-mount `./grafana/provisioning`; a session running it from an
  incompletely-populated worktree left a root-owned stub behind that, because
  Claude Code's local tmpdir is shared per-uid across all projects, broke
  every later Claude Code session on the machine with an unrelated-looking
  `/tmp/claude-<uid>` ownership error (2026-08-19). The fix was structural,
  not a guard: `grafana/Dockerfile` now `COPY`s `grafana/provisioning` into
  the image at build time and `compose-grafana.yml` uses `build: ./grafana`
  instead of `image:` — there is no host bind mount left to auto-vivify, so
  `docker compose up` is safe to run directly, from anywhere, without a
  wrapper script or special knowledge. If a future service needs a host
  bind mount for something git-tracked, prefer this bake-into-image pattern
  over a raw bind mount, or a launcher-side existence check as a fallback —
  never a bare bind mount to a path that might not exist yet.
- Never `git add -A` / `git add .` in this repo — it holds infra config and
  secrets (`.env`, `signalk/security.json`) alongside the maintenance docs.
  Stage files explicitly by name.
- **No cherry-pick.** Cherry-pick is a signal that commits ended up in the
  wrong place. This repo's workflow (worktrees + push-on-verify) is designed
  to prevent that state. If you're reaching for cherry-pick, stop and ask:
  Did a worktree collision happen? Did a commit land on the wrong branch by
  mistake? Fix the root cause instead — rebase, amend, redo the commit on the
  right branch. Cherry-picks are recorded as a quality metric (they happen, but
  they're a red flag for workflow breakdown). If cherry-pick is genuinely the
  right tool for a specific case, document it in the commit message and flag it
  to the owner.
- **Work on main.** Default to committing straight to main in small,
  iterative commits, each one verified before the next. Push as soon as a
  commit is verified rather than batching. Don't create a branch because the
  work feels large — break it into smaller commits on main instead.
- **Branch-vs-main is a rule, not a judgment call — don't ask.** Commit
  straight to main unless at least one of these is true:
  - The work can't be landed in a working state at every intermediate
    commit (a multi-step migration, a rename/restructure spanning several
    files, anything where a push mid-sequence would leave the repo broken).
  - It touches infra with real blast radius if left half-applied —
    Ansible, docker-compose, systemd units, SignalK security/plugin
    config, `.env`, or sops-encrypted secrets.
  - The owner explicitly asks for it to be reviewed as a PR, or the work
    is large enough to want follow-up discussion/tracking (several
    unrelated files, a new system brought online, anything you'd want a
    second look at before it's final).
  - **Explicit phrase** — the owner says "make this a feature," "make this
    a branch," or "this needs review." Branch immediately, no metric check.
  - **Metric threshold crossed** (placeholders, tune later): >50 lines of
    code changed (excluding docs), >200 lines of docs changed, session
    >100k tokens, or session >30 min wall clock.

  Everything else — a single doc/reference edit, a log entry, a small
  RUNBOOK.md or CLAUDE.md fix, a one-file config tweak that's correct as
  soon as it's written — goes straight to main, no branch, no asking.
  When a branch *is* warranted under this rule, always open the PR
  yourself as part of finishing the work, **as a draft, with no reviewer
  requested** — don't leave a pushed branch without one, and don't wait to
  be asked. **A branch opened under this rule only ends one way: merged
  via PR — never folded back to main and deleted instead.** If you're
  deciding whether a branch was warranted, you're mid-work; don't
  retroactively un-decide it once it's pushed.
- **Cloud sessions: a pre-assigned `claude/*` branch name is not, by
  itself, a decision to branch.** Some task setups hand a session a branch
  name before any content decision gets made. Apply the branch-vs-main rule
  above as normal — if nothing crosses a trigger, land the work with
  `git push origin HEAD:main`, pushed early and often, rather than treating
  the assigned name as the destination; don't manufacture a PR to justify a
  branch name you didn't choose. This does **not** apply when a session's
  own task instructions separately name one specific branch and say to stay
  on it — that instruction is for that session only and takes precedence;
  finish that branch with a PR as usual.
  Standing grant, confirmed 2026-08-19; ported from
  `dotfiles/.claude/rules/code.md`, see
  `claude_prompts_scratch/state/global/log/2026-08-19-git-hygiene-branch-override.md`.
  Supersedes the earlier "fold it back to main (fast-forward, no PR)"
  handling of this case — the fix is now not branching in the first place,
  which also settles the 2026-08-19 split where two sessions resolved the
  same situation oppositely (one folded back, one opened PR #9 to ban
  folding back outright); see `maintenance/log.md`. **The reason has
  changed as of 2026-08-20**: this used to lean on "cloud sessions can't
  reliably delete their own remote branches" as the justification — true,
  but no longer the operative one. With "Automatically delete head
  branches" now on (see next bullet), a branch that actually goes through
  a PR merge cleans itself up with no git command from any session. The
  rule stands for a cleaner reason: below the branch-vs-main threshold, a
  branch is unneeded ceremony, not an unclearable liability.
- **Automatically delete head branches: keep it on.** It works, and it is
  confirmed by a merge you can check: PR #24 and PR #26 were both merged on
  2026-08-20 and both head branches were gone immediately after, with no
  session action. It fires on an actual *merge* event only, so a branch
  whose PR is closed unmerged, or that never gets a PR at all, is untouched
  — that is the whole of the leftover-branch population, not a failure of
  the setting. Branches merged before the setting was switched on also stay
  (PR #1's `claude/ecoworthy-signalk-telemetry-vy82ta`, merged 2026-08-04,
  is still on the remote).
- **Reading merge state from the API: use `merged_at`, never `merged`.**
  GitHub's *list* pull-requests endpoint does not return the `merged`
  boolean at all — only the single-PR GET does — so every row in a list
  response reads `merged: false` regardless of the truth. A session on
  2026-08-20 took that default for data, concluded no PR in this repo had
  ever been merged, and rewrote the bullet above to say delete-on-merge had
  never fired. Both claims were false: `merged_at` is populated on 22 of
  the 26 closed PRs. If you are about to assert something about merges from
  a list call, check `merged_at`, or fetch the PR individually.
- If a change is potentially destructive, or could affect adjacent
  environments for plugin testing, ask for explicit permission before
  changing, committing, or pushing.
- **Always commit with an explicit pathspec: `git commit -m "..." -- path1 path2`.**
  `git commit` otherwise commits the whole index, not the files you staged.
  With several sessions sharing this checkout the index is shared mutable
  state, so `git add <file> && git commit` is a race — anything another
  session staged in between rides along in your commit, under your message.
  Checking `git status` first does not close this; it's an observation, not a
  constraint, and the other session can stage between your check and your
  commit. The pathspec form commits only the named paths and leaves the rest
  of the index untouched, which removes the race instead of watching for it.
  This happened: b11b40d silently carried unrelated SSO-SETUP.md edits.
- Multiple Claude sessions may be working the shared checkout at once (this is
  the scenario the worktree default above exists to avoid — prefer that over
  ever needing this bullet). Before running any git command in the shared
  checkout whose effect isn't scoped to files you explicitly name, run
  `git status` and read the full output — don't assume the working tree only
  holds what you touched. If it shows changes you didn't make, stop and tell
  the owner before running anything that would revert or discard them; don't
  guess whether they're safe to lose.
- **In the shared checkout** (i.e. you're not in your own worktree — see
  above), never run, without the owner's explicit go-ahead in that moment:
  `git reset --hard`, `git clean` (any flags), `git checkout` or `git restore`
  with no pathspec or a directory pathspec, `git stash` (repo-wide, not a
  named/scoped stash), `git branch -D`, or `git push --force*`. Each of these
  can discard or overwrite work outside whatever you meant to target,
  including another session's uncommitted changes. `git checkout HEAD -- path`
  is fine for a single file you've confirmed the diff of; it stops being fine
  the moment `path` is a directory you haven't fully read the diff of first.

### Recovery: when git itself suggests one of the banned commands
Git's own error messages routinely tell you to run exactly the commands above
— that advice is correct for a private worktree and wrong for the shared
checkout. If you're in your own worktree, just follow git's suggestion; the
entries below are for when you're not.
- *"Your local changes... would be overwritten by merge/checkout. Please
  commit your changes or stash them"* — don't run a bare `git stash`. Either
  commit the named files with an explicit pathspec, or `git stash push --
  <the exact paths git listed>` (a scoped stash is already permitted above),
  then proceed, then `git stash pop`.
- *"Not possible to fast-forward, aborting"* on `git pull` — someone else
  pushed to main first. Never force-push past this. `git fetch && git rebase
  origin/main` if these are your own not-yet-pushed commits (safe — it's your
  own private history); if there's a real conflict, resolve it file by file,
  never with `git checkout --ours/--theirs .` across the whole tree.
- Pre-commit's autofix stashes unstaged files, then rolls back on conflict —
  this is what silently reverted work before (see below). Don't
  self-remediate with `git checkout -- .`. Run `git stash list` first: a
  "pre-commit autostash" entry means your files are sitting there intact;
  `git stash pop` (that one named ref, not a clear/drop-all) gets them back.
- `git worktree remove` refuses with "contains modified or untracked files" —
  confirm you don't need what's there, then `ExitWorktree` with
  `discard_changes: true` (or `git worktree remove --force` outside the
  harness). Safe by construction: a worktree only ever holds your own
  throwaway work.
- Detached HEAD after a bad checkout in the shared checkout — note the commit
  you were on (`git log --oneline -1`), then `git switch main` (name only, not
  a reset) to get back onto the branch.
- If the gitleaks pre-commit hook errors with "gitleaks did not run: no
  docker on PATH" (docker isn't installed in this distro, or Docker
  Desktop's WSL integration is off) or "docker daemon not reachable"
  (Docker Desktop isn't running), commit with
  `SKIP=gitleaks` and move on — decided 2026-08-19; the local
  staged-secrets guard still runs and covers the commit. This sanctions
  skipping that one hook for that one failure, nothing else.
- sops-encrypted files must round-trip through the `sops` filter, never
  hand-edited in cleartext and committed directly.
- `secrets/pseudonyms.sops.yaml` is generated — the clean filter rewrites it
  whenever a new email address appears in a covered file. Don't hand-edit it,
  and don't reformat a sops-filtered JSON file by hand: sops re-serializes on
  every encrypt and decrypt, so the indentation comes from `--indent` in
  `scripts/sops_filter.py` and nothing you do in an editor survives.
- Stage *all* files you've touched before committing, even ones you mean to
  commit later. pre-commit stashes unstaged changes, and if a hook auto-fix
  conflicts it rolls back with `git checkout -- .`, which reverts them and
  can leave a filtered file deleted mid-smudge. This happened; the recovery
  patch is in `~/.cache/pre-commit/`.
- When two copies of a SignalK peripheral/device config disagree (a backup vs.
  the committed file, two repos, etc.), union them rather than picking one and
  discarding the other's fields — merge to the superset. A stale or invalid
  peripheral entry costs SignalK a harmless connection-retry log line; a
  silently dropped working one costs real functionality. Keep everything, flag
  anything that's a genuine conflict (not just a gap) rather than guessing, and
  let the owner prune deliberately later.
