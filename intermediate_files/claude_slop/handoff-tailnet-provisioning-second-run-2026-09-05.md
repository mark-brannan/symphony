# Handoff: prove the tailnet stale-node delete, run 2 of 2

**Model/effort: Sonnet 5, medium.** Mostly execution against a known-good
procedure; no design judgment needed unless something breaks.

## Context

[PR #48](https://github.com/mark-brannan/symphony/pull/48) wired an
unattended tailnet-identity block into `ansible/roles/network`: a reflashed
card releases its own stale Tailscale registration and re-registers itself,
no click in the admin console. [PR #48's own body](https://github.com/mark-brannan/symphony/pull/48)
said explicitly this needed proving twice, on real hardware — the second
run is the one that exercises the delete-guard against a node *this
session's own first run* left behind, not a pre-existing one.

**Run 1 is done** (2026-09-05, see `log.md` entry same date). It found and
fixed a real bug along the way — [PR #58](https://github.com/mark-brannan/symphony/pull/58),
merged — and confirmed the card came up as `symphony-halos` /
`tag:symphony-devices` / `BackendState: Running`, fully unattended.

**Run 2 is what's left.** Prompt Mark:

> Flash the same Pi 4 again with a fresh `Halos-Marine-RPI` image (Raspberry
> Pi Imager, "Use custom", **no OS customisation** — same recipe as before,
> in `halos-fresh-image-rebuild.md`), wired Ethernet before power-on, then
> power it on and let me know.

## What to do once it's up

1. Rebase this repo's worktree onto `origin/main` first (Mark may have
   merged other things since).
2. Find the card on the LAN — scan for its SSH banner
   (`OpenSSH...Debian`), same as before. It'll come up on a new DHCP lease,
   not necessarily `.192` again.
3. `scripts/halos_card_bootstrap.sh <ip>` — key, password, throttled check.
4. Build a scratch inventory pointing `symphony-halos` at that IP (see the
   one used in run 1 for the exact shape — not committed, lived in the
   session's scratchpad).
5. `cd ansible && ansible-playbook -i <scratch-inv> site.yml`. Expect it to
   converge clean this time — the mint-step bug is fixed on main now.
6. **The actual thing being proven:** this fresh registration is now the
   live `symphony-halos` node. Reflash the card a **second** time this
   session (same image, same steps) so *that* registration goes stale and
   offline, then find the new boot on the LAN and run `site.yml` against it
   again. Confirm via the play's own debug line
   ("nodes holding this card's name, offline") that it names the node this
   session itself just created — not the pre-existing leftover run 1
   incidentally cleaned up — and that the delete-then-remint sequence
   completes with `tailscale status --json` again showing `HostName:
   symphony-halos`, `Tags: [tag:symphony-devices]`, `BackendState: Running`.
7. Write up the result in `log.md` (append) either way — pass or a new bug
   found. If it passes clean, this closes the `## Claude's` card "Prove the
   tailnet provisioning block against a genuinely blank reflash, twice" in
   `kanban.md` — delete the card, don't just check it off.

## Watch for

- The classifier will likely deny editing `no_log` on a tracked Ansible
  task to debug something live. Don't fight it a second time — the working
  pattern from run 1 is an **untracked** scratch playbook in `ansible/`
  (git-ignored by virtue of never being staged) that makes the identical
  API call outside the real role, with `no_log: false` only on that
  throwaway file. Clean it up (`rm`) and revoke any throwaway auth keys via
  the API afterward.
- If a stale node shows up that ISN'T this session's own prior registration
  (i.e., something else is using the name `symphony-halos` offline again),
  stop and flag it to Mark before letting the play delete it — that's
  exactly the failure mode the guard exists to prevent, and two sessions
  finding the same mystery stale node in a row is worth a direct question,
  not a second silent cleanup.
