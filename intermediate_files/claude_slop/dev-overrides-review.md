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
