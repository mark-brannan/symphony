# Security posture — decisions already made

A boat is not a datacenter. The calls below were made deliberately, with
the tradeoffs understood, and they are not open questions. If you think
one of them is wrong, say so in a line and move on — don't re-derive the
analysis, and don't route around a decision by proposing a "safer
alternative" that quietly gives up what the decision was protecting.

## The trust boundary is the boat's own network

Nothing here is reachable from the internet. The router's WAN zone drops
inbound traffic, there are no port forwards, and Tailscale Funnel and
serve are both off. Devices on the boat LAN, on the Pi's own access
point, and on the tailnet are treated as trusted; the guest wifi is
walled off at the router and can only reach the internet.

There is no host firewall on the Pi. That is a consequence of the above,
not an oversight.

## Plain HTTP on the LAN stays

SignalK (`:3000`), Grafana (`:3001`) and InfluxDB (`:8086`) listen on
every interface without TLS, alongside the Caddy front door. That is the
point: `http://<lan-ip>:3000` keeps working when the hostnames don't
resolve, which offshore is a live scenario — public DNS is unreachable
and the router's local overrides are the only thing answering.

So don't propose binding these to loopback, don't propose forcing all
traffic through Caddy, and don't treat the raw-IP path as a finding. It
is the fallback. Availability at sea outranks confidentiality on a
network whose radius is the length of the boat.

## Local password logins are the offline fallback

`captain` on SignalK and Grafana's superadmin are not legacy accounts to
be migrated off. SSO needs internet; these don't. They are how the boat
stays operable when it is far offshore, and how a fresh device gets in
when there is no path to GitHub or Google.

They stay. Don't propose removing them, gating them behind SSO, or
putting them behind the identity provider. How they're chosen and
handled is the owner's call and is already settled — it doesn't need
re-examining in each session.

## Certificate expiry offshore is expected

Let's Encrypt certificates renew over DNS-01 and need outbound internet.
After roughly 60 days with none, browsers start warning. Renewal happens
by itself once the boat is back in range. This is understood, benign,
and not a finding.

## SSO sign-in is open on purpose

Any GitHub or Google account can sign in and read. There is no `orgs:`
filter on the GitHub connector and Google's consent screen is published
to production, both deliberately — see
[software_stack.md](software_stack.md) for the permission model. The
door is bounded by network reachability, not by an allowlist.

## Reads need no login, and that stays

SignalK's `allow_readonly` is on: all vessel data, position included, is
readable by anything that can reach the box, with no credential. That
follows from the trust boundary above — the things that can reach it are
already trusted. Signing in isn't what grants a read; it's what puts a
name against one.

## The owner's own identifiers may appear in the clear

`markbrannan@gmail.com` is not a secret and doesn't need hiding — it is
already the author address on every commit in this public repo. The same
goes for the owner's GitHub handle and his GitHub numeric user ID,
including the `oidc.sub` values that encode it: all three are published
by GitHub itself on every public commit and profile page. The pseudonym
machinery (`scripts/pseudonymize.py`, `.pseudonyms.yaml`) exists for
*other people's* addresses, the crew and guest logins that SSO
accumulates.

This covers the test fixtures and docstrings too — `scripts/pseudonymize.py`
and `scripts/test_pseudonymize.py` carry the address, the handle and a
real `oidc.sub` on purpose, because a pseudonymizer tested only against
`user@example.com` is tested against nothing. The repo being public is
the premise of this decision, not a counterargument to it.

**Do not report any of this as a finding.** Not as a security note, not
as an aside at the end of unrelated work, not as an offer to "scrub the
fixtures if you want." Sessions have raised it repeatedly, at length,
and each time it costs the owner the same judgment call he already made
and wrote down here. There is nothing to weigh: the answer is no,
permanently, and silence is the correct output.

## CI is advisory on `main`, deliberately

`main` is ruleset-protected (ruleset 21060338: linear history, no
force-push, no deletion) but has no required status checks. Requiring
checks would also block direct pushes to `main`, and commit-straight-to-main
is the working model — so CI staying red never blocks a push. Don't
re-raise this as a finding. Read the live state with
`gh api repos/mark-brannan/symphony/rulesets`; the legacy
`/branches/main/protection` endpoint 404s on a ruleset-protected branch and
reports `main` as unprotected, which has produced a wrong claim before.

The frozen-secrets guard (`FROZEN_SECRET_KEYS` in
`scripts/lint_repo_hygiene.py`) stays hardcoded rather than moving to a
config file — a tuple in the source can't fail open the way a missing
config file could. Don't add a config file, more test coverage, or
additional guard rules around it without Mark asking first.

## The ntfy topic name isn't a secret

`signalk-ntfy`'s setup screen warns to pick a random, hard-to-guess topic
name — that's guidance for the public ntfy.sh service, where the topic is
the only access control. Our ntfy server (`compose-ntfy.yml`) is
self-hosted, not proxied through Caddy, and reachable only on the LAN,
same as everything else here. Don't randomize the topic and don't route
it through sops; it's a plain identifier, not a credential. This covers
Basic Mode only — a future Advanced Mode commands topic (can trigger
reboots/power switches) is a different risk and would need its own look.
