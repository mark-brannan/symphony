# Handoff: wire the provisioning credential into the `network` role

**Model: Opus 5, high effort.** It writes a destructive API call (device
delete) into a play that runs against the card staged to become the live boat
card. Not a config task.

## What is already done — do not re-derive

The design is settled and signed off by Mark on 2026-09-04:
[reference/tailnet_identity.md](../../reference/tailnet_identity.md). Read it
first; it carries the constraint evidence and the rejected alternative.

The credential exists and is proven against the live tailnet:
`tailscale_provision_client_id` / `tailscale_provision_client_secret` in
`secrets/symphony.sops.yaml`, scopes `devices:core` + `auth_keys`, tagged
`tag:symphony-devices`. Verified 2026-09-04: token exchange, a full device
list, and a minted single-use tagged key that was deleted again. You do not
need to create anything in the admin console.

Measured the same day, and the reason the guard is where it is: the client's
tag does **not** limit which devices it can see. Tagged
`tag:symphony-devices`, it listed all seven nodes including untagged personal
devices and `symphony-pi`. Assume it can delete any of them.

## The work

Implement steps 1-5 of the design in `ansible/roles/network/tasks/main.yml`,
replacing the "tailscale is not installed on this card" debug branch that
currently ends the flow.

Non-negotiables, in order of how much they cost if you get them wrong:

- **The delete is guarded in the play.** Exact string equality on
  `tailscale_hostname`, and the device must be offline. Never a prefix, never
  a regex, never `startswith`. A test that proves the boat's node is not
  matched when the target is the HALOS card is part of the deliverable.
- **The minted key never reaches disk** and never appears in output.
  `no_log: true` on the mint task and the `tailscale up` task both.
- **The whole block is skipped** when `tailscale status --json` already
  reports the right hostname and tag, so a re-run against a working card is
  inert. This is what makes `site.yml` safe to run repeatedly.
- Key parameters, fixed by the design: not reusable, not ephemeral,
  pre-authorized, tagged `tag:symphony-devices`, expiry in minutes.

## Sequencing

[PR #45](https://github.com/mark-brannan/symphony/pull/45) touches the same
role (install-tailscale-if-missing, plus boot-enabled asserts) and was open as
of 2026-09-04. Check whether it merged; if not, either build on its branch or
rebase onto it, but do not land a conflicting rewrite of the same block.

This is infra with real blast radius, so it goes on a branch with a draft PR
under CLAUDE.md § Git hygiene — not straight to main.

## Proving it

The design is unproven until a genuinely blank card reflash comes up with the
right name and tag, unattended, twice in a row — the second run is the one
that exercises the stale-node delete. That is the 🔴 banner's stage 2. A dry
run against an already-provisioned card proves only the skip path.
