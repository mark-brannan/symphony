# Proposal: identity-based permission mapping for signalk-server OIDC

Status: implementation written and pushed; conversation with the OIDC author
not yet opened. The OIDC code is Matti Airas's (Hat Labs), active on the
SignalK Discord — post the opener below there before turning the branch into
an upstream PR.

- Branch: https://github.com/mark-brannan/signalk-server/tree/oidc-identity-permissions
- Preview PR (fork-internal, for review before going upstream): https://github.com/mark-brannan/signalk-server/pull/1

## Problem

`src/oidc/permission-mapping.ts` maps permissions from group claims only.
Google never sends a groups claim; GitHub only exposes groups as
organization/team membership. So a boat owner using Google or GitHub SSO
cannot grant themselves admin without joining or creating a GitHub org —
hoops without payoff for a single-admin vessel install.

## Design

- `adminUsers` / `readwriteUsers` lists alongside the existing
  `adminGroups`/`readwriteGroups`, plus `identityClaim` (default `email`)
  choosing which claim the lists match against.
- Precedence: groups → identity lists → `defaultPermission`. Behavior is
  unchanged when the lists are absent.
- Readwrite via identity is opt-in by config presence, same as admin.
- Case is normalized before comparing for `email` and `preferred_username`;
  `sub` is an opaque, case-sensitive identifier and is compared exactly.
- Configurable through both paths the existing options use: env vars
  (`SIGNALK_OIDC_ADMIN_USERS`, `SIGNALK_OIDC_READWRITE_USERS`,
  `SIGNALK_OIDC_IDENTITY_CLAIM`) and the `oidc` section of `security.json`,
  merged by the existing `config.ts` logic (env wins).
- The admin settings API (`PUT /skServer/security/oidc`) preserves the new
  fields when a client that doesn't know about them (e.g. the current admin
  UI form) saves other settings — otherwise a UI save would silently wipe a
  hand-edited allowlist. Admin UI form fields are left as a follow-up PR.

## The security crux

Identity lists only match on `email` when the token carries
`email_verified: true`. Without that gate, any IdP that lets a user set an
arbitrary email becomes an admin bypass: register `owner@example.com` at a
provider that doesn't verify addresses, and you're the admin. The gate is
strict (`=== true`, boolean only). `email_verified` is also merged from the
userinfo endpoint together with `email`, so the pair stays consistent.
Consequence, documented: an IdP that omits `email_verified` entirely can't
use email allowlists — fail closed, switch `identityClaim` instead.

## Open design question (argue yes)

With `SIGNALK_OIDC_AUTO_CREATE_USERS=false`, should a named allowlist entry
still be creatable on first login? The implementation says **yes**: being on
the list *is* the preconfiguration — the admin wrote that identity into the
server's own config, which is a stronger statement than the blanket
auto-create toggle. Without it, a closed server can never admit its own
admin: the account can't exist until the person logs in, and they can't log
in until the account exists. Group matches deliberately do **not** bypass
the toggle; group membership is managed in the IdP, not in the server's
config, so it isn't the same explicit local statement.

## Smaller calls a reviewer may want to weigh in on

- Groups win over identity lists when both match (source-major precedence).
  A user in a readwrite group who is also in `adminUsers` gets readwrite.
  Rationale: keeps the existing group semantics fully authoritative;
  swapping to level-major (adminGroups → adminUsers → readwriteGroups →
  readwriteUsers) is a two-line change if preferred.
- `identityClaim` is restricted to `email` / `preferred_username` / `sub` —
  the claims the server already extracts — rather than any arbitrary claim.
  YAGNI until someone needs `upn` or similar.

## Discord opener (draft)

> Hi Matti — I'd like to propose an addition to the OIDC permission
> mapping and have a branch ready if the idea sounds right to you.
>
> Problem: permission mapping is groups-only, and some IdPs can't play —
> Google never sends groups, GitHub only as org/team membership. So a boat
> owner can't preconfigure themselves as admin via SSO without standing up
> group infrastructure somewhere.
>
> Proposal: `adminUsers` / `readwriteUsers` lists matched against a
> configurable `identityClaim` (default `email`), checked only after groups
> produce no match, falling back to `defaultPermission` as today — so
> nothing changes unless the lists are configured. The security crux: email
> matching requires `email_verified: true` in the token, otherwise an IdP
> with unverified user-entered emails becomes an admin bypass.
>
> One question I'd like your read on: with `autoCreateUsers=false`, the
> branch still creates a user on first login *if* they're on an allowlist —
> the list entry is the preconfiguration, and otherwise a closed server can
> never admit its own admin. Reasonable?
>
> Branch with tests and docs: 
> https://github.com/mark-brannan/signalk-server/tree/oidc-identity-permissions
> Happy to adjust and open a PR if you're broadly good with the shape.
