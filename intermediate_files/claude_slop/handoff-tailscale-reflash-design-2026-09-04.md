# Handoff: design the Tailscale identity story for repeated card reflashes

**Model: Opus 5, high effort.** This is a design session with real
production-safety consequences (boat SSH access), not a quick config task —
don't downgrade it.

## Why this session exists

A prior session (2026-09-04) proposed "generate a reusable, pre-tagged
Tailscale auth key" as the fix for making `ansible-playbook site.yml` fully
non-interactive against a freshly reflashed card. Mark correctly called that
naive before any key was created. Nothing has been generated yet — this is
still open.

## What's actually established (don't re-derive)

- The bench card's Tailscale identity lives in local state
  (`/var/lib/tailscale/tailscaled.state`), keyed to a node key, not the MAC
  or hardware. A reflash wipes it. A normal card *swap* (moving the SD card)
  does not.
- `tailscale set --hostname=X` only **requests** a name locally. If a stale
  node (even offline) already holds that name in the tailnet, the
  coordination server silently suffixes the new one (`symphony-halos-1`) and
  registers it under Mark's personal identity rather than the intended tag —
  observed live, 2026-09-04, only fixable by deleting the stale node by hand
  in https://login.tailscale.com/admin/machines.
- [PR #45](https://github.com/mark-brannan/symphony/pull/45) (merged or
  pending — check) added: install-tailscale-if-missing to the `network`
  role, and boot-enabled asserts for tailscaled/docker/chrony/telegraf/ssh
  across `network`/`base` roles and `halos_preflight.sh`. That part is solid
  and live-verified. What it does **not** solve is the identity-collision
  problem on repeat reflashes.
- The existing `tailscale_oauth_client_*` secret in
  `secrets/symphony.sops.yaml` is deliberately read-only (its own comment in
  `scripts/tailscale_policy.sh` says so) — it cannot create keys or delete
  devices. Any scripted fix needs either a new credential or accepts a
  manual step.
- ACL policy (`scripts/tailscale_policy.sh`) already defines `tag:home-fleet`
  and `tag:symphony-devices` with real SSH consequences — a key that mints
  `tag:symphony-devices` grants boat-reachable SSH capability the moment it's
  used. Read the live policy before proposing scope.
- The bench card is not a permanent test fixture — it is *staged to become
  the live boat card* after validation. Whatever identity mechanism it gets
  during bench testing has to either (a) already be right for the boat, or
  (b) have an explicit, scripted transition step for swap day.

## What to actually verify before deciding anything (don't assume)

1. **Ephemeral node removal timing.** Tailscale's docs say ephemeral nodes
   are removed after they disconnect — get the actual behavior (immediate?
   a timeout? does it differ for tagged vs. user-owned nodes?) from
   Tailscale's own documentation or support, not inference. This determines
   whether "ephemeral" actually closes the collision race or just narrows
   the window.
2. **Can an ephemeral node's status be converted to non-ephemeral later**
   (for the swap-to-boat transition), or does that require a fresh
   `tailscale up` with a different key regardless? If the latter, the swap
   procedure needs an explicit re-auth step written into
   `halos-swap-plan.md`, not assumed to carry over.
3. **What scope does a reusable auth key actually need**, and should
   `tag:symphony-devices` be granted at key-creation time at all, or added
   later (at swap day, by hand or by a narrower-scoped mechanism) so a
   leaked bench-provisioning key can't SSH-reach the boat unless it already
   should?
4. **Rotation/expiry policy** for whatever key gets created — Tailscale caps
   key expiry; decide the real cadence, not "never."
5. Whether a **narrower, write-scoped OAuth client** (device delete/rename
   only, not full admin) is a better mechanism than an ephemeral key for
   the collision problem specifically — this trades "one key, some
   behavioral assumptions" for "two credentials, deterministic scripted
   cleanup." Lay out both, recommend one, don't default to whichever is
   less work to write up.

## What "done" looks like

A design Mark has actually signed off on, in
`reference/host_provisioning.md` or a new file it links to — not just an
ansible task. Then, and only then, generate the actual key/credential per
RUNBOOK "Adding a secret", wire it into the `network` role, and prove it
against a real fresh Pi 4 reflash end to end (a separate, later session —
see the 🔴 banner in `kanban.md`).

## Where to start

Read `kanban.md`'s 🔴 banner and this file, then open with Mark: which of
the two mechanisms in point 5 he wants investigated first, or whether he
wants both fully speced before either gets built.
