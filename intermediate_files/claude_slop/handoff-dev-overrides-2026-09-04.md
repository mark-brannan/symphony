# Handoff — finish the dev/prod override consolidation

Written 2026-09-04. **Opus 5, medium effort, ~1 session.** Two PRs are open
and stacked; neither has been reviewed by a human or a bot yet.

## Start here

Both PRs are pushed and CI state is **unknown** — the session that opened
them lost its Bash tool before it could read a single check or comment. Read
CI and every review comment on both before touching anything.

```
gh pr checks 41; gh pr checks 42
gh pr view 41 --comments; gh pr view 42 --comments
```

- **[#41](https://github.com/mark-brannan/symphony/pull/41)** `claude/dev-vcan` — base `main`. 3 files, +23/−35.
- **[#42](https://github.com/mark-brannan/symphony/pull/42)** `claude/dev-ntfy-one-url` — base `claude/dev-vcan`. 19 files, +31/−847.

#42 is stacked on #41. Merge #41 first, then re-target #42 to `main`.

## The idea both PRs apply

Mark's test, and it governs everything here: **before splitting a value per
host, ask whether it could be the same everywhere without causing him pain.
Bias toward merging, not toward a better override mechanism.** Applied to the
seven overrides that exist, four can be merged out of existence and three are
genuinely per-host. That is why there is no `overrides/` directory and no
`seed`/`capture` script — the earlier design proposed both, and the test
shrank the problem below the point where they earn their keep. Don't rebuild
them without re-reading § Spike findings in
[dev-overrides-review.md](dev-overrides-review.md).

## Done

- **healthcheck config is tracked** (a057c04, on main). It existed only on the
  boat and in `dev/`, in no host's sync. Taken from the boat minus a dead
  `mail` block — `sendEmail` false on both sections, and the block had no
  `host`/`port`, so nodemailer could never have connected.
- **#41 vcan** — dev gets a real `can0`, so `settings.json`,
  `signalk-healthcheck.json` and the provider watch are identical to the boat.
  A sidecar owns the netns and signalk joins it, because the signalk image has
  no iproute2 and runs as uid 1000. Verified live: `Successfully connected to
  can0`.
- **#42 ntfy** — `http://localhost:8090` is correct on dev and boat alike once
  ntfy shares that namespace, so the whole hostvars git-filter apparatus is
  deleted: the 471-line filter, its 195-line test, `.hostvars.yaml`,
  `hostvars.local.yaml` + example, a pre-commit hook, a CI step, a fresh-clone
  expansion pass, a clone-setup section, and a dead lint rule.
- **A real bug fixed inside #42**, because nothing could commit until it was:
  `test_encoding_health`'s two non-ASCII path tests build a temp repo but git
  exports `GIT_DIR`/`GIT_INDEX_FILE` into hook environments, and those
  override `cwd` — so under `git commit` the fixtures ran `git init` and
  `git add` against the **real** repository and asserted on its index, leaving
  two junk fixture files staged there. Passes standalone and in CI; fails only
  from a commit staging `scripts/*.py`. Both fixtures and both callers now
  scrub the four `GIT_*` variables.

## Left to do

1. **Address the review comments on #42.** Mark asked for this explicitly and
   it was never done — the Bash tool died first. This is the first task.
2. **Pushover** — the last mergeable override. Dev pins
   `signalk-pushover-notification-relay` off because the relay's dedupe state
   is in memory and every container restart re-paged a real phone. Dev's copy
   already has empty `api_user`/`api_key`. Test whether the plugin **no-ops**
   on an empty key rather than erroring; if it no-ops, `enabled: true` is safe
   everywhere, the override disappears, and `dev/plugin-config-overrides/` and
   `docker-compose.override.yml` can both be deleted outright.
3. **Then stop.** What remains is genuinely per-host and needs no machinery:
   the four HALOS plugin disables, the heartbeat URL (per-instance by design —
   it *is* the host's identity), and alpha's port 3010.

## Decisions already made — don't reopen

- **ntfy URLs are not sensitive** (Mark, 2026-09-04). All RFC1918 or a compose
  service name. That call is what justified deleting the filter.
- **The healthcheck `mail` block is dead and stays deleted.** Don't restore it;
  email alerting would need a real SMTP endpoint chosen first.
- **Venus naming is punted** to a `## Yours` card. The HALOS card keeps the
  literal `192.168.8.107` until Mark picks a name.

## Open, needs Mark

**The boat's live ntfy URL is `http://192.168.8.240:8090`; #42 tracks
`http://localhost:8090`.** `localhost` is better — SignalK is native on the
Pi, ntfy publishes that port locally, and it survives a DHCP lease change —
but merging #42 changes the boat's live config at the next sync. Flagged in
#42's body, unanswered.

## Traps

- `git push` needs `--no-verify` in this repo (Mergify pre-push hook).
- `git commit -m ... -- <pathspec>` does **not** limit the commit here —
  pre-commit's stash/restore defeats it, and three attempts to split a commit
  that way all swallowed the whole staged set. Stage narrowly instead.
- The dev stack is currently **running from #41/#42's compose**, with `can0`
  up and ntfy in the shared namespace. `main`'s compose has neither, so a
  `docker compose up` from main will recreate without them.
- `docker compose config` is blocked without `--no-interpolate`.
