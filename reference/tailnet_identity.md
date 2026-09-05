# Tailnet identity across reflashes

How a card that has been reflashed gets its tailnet name and tag back without
a hand edit in the admin console, and why the mechanism is an OAuth client
rather than an auth key.

## What breaks today

A node's tailnet identity lives in `/var/lib/tailscale/tailscaled.state` and
is keyed to a node key. Reflashing the SD card destroys it; moving the card
between machines does not.

`tailscale set --hostname=X` only *requests* a name. If any node still holds
that name in the tailnet, the coordination server silently registers the new
one suffixed — `symphony-halos-1` — and an interactive `tailscale up`
registers it under Mark's personal identity rather than under a tag. A stale
node that is offline, or whose key has expired, still holds its name; only
deleting it releases the name. Observed live on 2026-09-04.

The consequence is the one that matters: `ansible-playbook site.yml` cannot
bring a freshly reflashed card onto the tailnet unattended, because releasing
the name is a click in <https://login.tailscale.com/admin/machines>.

## The constraints that pick the mechanism

- Auth keys expire after **90 days at most**. There is no non-expiring key, so
  a key stored in `secrets/symphony.sops.yaml` is a standing rotation chore.
- An **OAuth client secret does not expire** and mints keys on demand, so the
  long-lived credential and the short-lived one can be different objects.
- **Ephemeral nodes are removed 30 to 60 minutes after last activity**, not at
  disconnect.
- `devices:core` is the only scope that can remove a machine; there is no
  narrower delete-only scope. `auth_keys` is separate from it.
- Under the live policy (`scripts/tailscale_policy.sh`), `tag:home-fleet`
  already has SSH to `tag:symphony-devices`.

## Why not an ephemeral key

Ephemeral registration is the obvious-looking fix and it is the wrong one
here, for three independent reasons.

It does not close the race. A reflash-and-reprovision cycle is minutes; the
stale node lingers for thirty to sixty. The collision it is meant to prevent
happens inside the window.

It is wrong for the destination. This card is staged to become the live boat
card, and the boat is on a cellular link where half an hour offline is
routine, not exceptional. An ephemeral boat node deletes itself during an
ordinary outage.

There is no documented conversion. Nothing in Tailscale's documentation turns
an ephemeral node into a permanent one in place, so swap day would need an
explicit re-authentication step that a permanent registration does not.

## The design

One OAuth client, scopes `devices:core` and `auth_keys`, tag
`tag:symphony-devices`, stored as `tailscale_provision_client_id` and
`tailscale_provision_client_secret` in `secrets/symphony.sops.yaml`.

The `network` role, only when `tailscaled` has no identity or holds the wrong
name:

1. Exchange the client credentials for a token.
2. List devices; find an **exact** match on `tailscale_hostname`.
3. Delete that device only if the name matches exactly **and** it is offline.
4. Mint a key: not reusable, not ephemeral, pre-authorized, tagged
   `tag:symphony-devices`, expiring in minutes.
5. `tailscale up --ssh --authkey=… --hostname={{ tailscale_hostname }}`.

The key is used once, within its own play, and never written to disk. When
`tailscale status --json` already reports the right hostname and tag, steps 1
through 5 are skipped entirely, which is what keeps a re-run of `site.yml`
against a working card inert.

### Why the guard is in the playbook, not in the scope

There is no delete-only scope to fall back on, and the client's tag does not
narrow what it reaches: tagged `tag:symphony-devices`, it lists every device in
the tailnet, untagged personal devices and the boat's own node included
(measured 2026-09-04). The tag governs which tags it may *assign*, not which
devices it may touch.

So the destructive step is constrained where the constraint can be read and
tested: an exact hostname match against a device that is currently offline. The
boat's own node fails both tests whenever the target is the HALOS card, and no
prefix or fuzzy match is ever used.

### Rotation

Nothing rotates on a schedule. The minted keys are single-use and expire in
minutes; the client secret does not expire. If the secret leaks, delete the
client in the admin console, create a replacement, and update the two sops
entries per RUNBOOK → Adding a secret. That is the whole policy.

### What this means at swap time

The registration is permanent and already carries `tag:symphony-devices`, so
physically moving the card to the boat requires no Tailscale action at all —
the node key survives the move. Only the hostname question remains, and that
belongs to the swap plan, not here.
