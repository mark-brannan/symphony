# Security Policy

This repo is not a package released to others — it's the source and
configuration for one boat's own IoT stack, plus her maintenance record. A
security issue here is either a flaw in the code and config anyone could
reuse, or a live exposure on the actual vessel. Both matter; they're handled
differently.

## Supported versions

There is one running system, and it tracks `main`. There is no versioned
release and nothing older to support — a fix lands on `main` and gets
deployed.

## Reporting a vulnerability

**Please do not open a public issue for a security problem, and never post a
secret, credential, or the boat's network details anywhere in this repo,
including in an issue, a commit message, or a PR.**

1. Go to
   [Security → Report a vulnerability](https://github.com/mark-brannan/symphony/security/advisories/new).
2. Describe what you found and how to reproduce or verify it. If a live
   credential is involved, say so explicitly — see below — but do not
   include the credential's value in the report.

You should get an acknowledgement within a week. This is a one-person,
spare-time boat project, so a fix (and, if needed, a rotation aboard) may
take longer than that — you will be told where it stands rather than left
waiting. If a report is valid and you want credit, you will be named in the
advisory.

If you get no response at all within two weeks, open a public issue saying only
that you are waiting on a private report — no details — and it will be picked
up.

**A live credential leak is the urgent case.** If a report or a scan surfaces
a working credential — a token, a password, an API key — treat it as already
compromised: it gets rotated before anything else, following the mint →
migrate → verify → revoke order in [ROTATION.md](ROTATION.md), which also
records every rotation done so far and why.

## What is in scope

- **Anything that lets a secret reach a tracked file, a log, a build
  artifact, or a session transcript unencrypted.** The `sops`/`age` pipeline,
  `.gitleaks.toml`, `secret-scan.yml`, and the pre-commit hooks in
  `.pre-commit-config.yaml` exist specifically to catch this before it's
  pushed; a gap in any of them is in scope, as is a redaction filter that
  misses a variant name (see the `influxdb_captain_token` entry in
  [ROTATION.md](ROTATION.md) for a real example).
- **A way past a decision recorded in
  [reference/security_posture.md](reference/security_posture.md)** — for
  example, something on the guest network reaching a service it's walled off
  from, or a port reachable from outside the boat's own network despite the
  no-port-forward stance documented there. Read that file first: it also
  lists the decisions that are *not* findings, made deliberately with the
  tradeoffs understood.
- **Provisioning and deployment** — `ansible/`, `host/`, the `compose-*.yml`
  files, and the CI workflows that gate `main` — doing something other than
  what it's documented to do in
  [reference/software_stack.md](reference/software_stack.md).
- **A real, currently-live exposure on the boat's own stack** reachable
  within the trust boundary that
  [reference/security_posture.md](reference/security_posture.md) defines
  (the boat's LAN, its own access point, and the tailnet).
- **Other people's identifiers leaking through `.pseudonyms.yaml` or
  `scripts/pseudonymize.py`.** The owner's own address, handle and GitHub ID
  are already public by design — see the note in
  [reference/security_posture.md](reference/security_posture.md) — but a
  crew or guest identifier escaping that machinery is in scope.

## What is out of scope

- **The decisions already made in
  [reference/security_posture.md](reference/security_posture.md).** No host
  firewall, plain HTTP on the LAN, local password logins staying, SSO open
  to any GitHub/Google account, read-only SignalK access needing no
  login — these are settled tradeoffs, not open questions. Say so in a line
  if you think one is wrong; don't propose a "safer" alternative that
  quietly gives up what the decision protects.
- **Certificate expiry after weeks offline.** Expected, benign, and
  documented — not a finding.
- **Physical security of the boat or her systems.**
- **Ordinary bugs** in a plugin, a dashboard, or a rule that don't cross a
  security boundary — those are maintenance items; see
  [maintenance/priorities.md](maintenance/priorities.md) or open a public
  issue.

## Notes on how this repo is built

- Secret-bearing files stay ciphertext on disk (`sops` + `age`); a clone with
  no key can still build, test and contribute — see the README's
  *Contributing* path.
- `secret-scan.yml` and `validate.yml` need no secrets and run on every push
  and pull request; both are required checks, and `main` only takes changes
  through a squashed pull request.
- `scripts/scan_verified_secrets.sh` and a full-history gitleaks/trufflehog
  pass are the standing tools for auditing whether anything ever leaked —
  run them, don't re-derive the check.
