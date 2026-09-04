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
