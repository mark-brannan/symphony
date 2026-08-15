# Software stack

How Symphony's onboard software is put together and why. Reference, not
procedure — for what to *do*, see [RUNBOOK.md](../RUNBOOK.md).

## Containers

Containers come from two places.

**Compose services**, in `docker-compose.yml` and the `compose-*.yml` files
it includes:

| Service | Image | Port | Persistent state |
|---|---|---|---|
| `signalk-server` | `signalk/signalk-server:latest` | 3000, 80 | `./signalk` (bind mount, **in git**) |
| `influxdb` | `influxdb:2.7` | 8086 | `influxdb-data`, `influxdb-config` volumes |
| `grafana` | `grafana/grafana:latest` | 3001→3000 | `grafana-data` volume, `./grafana/provisioning` |
| `caddy` | built from `./caddy` | 443 | `caddy-data` volume (certificates) |
| `dex` | `ghcr.io/dexidp/dex:latest` | none (proxied by caddy) | none (memory only) |
| `dex-dev` | `ghcr.io/dexidp/dex:latest` | 5556 | none (memory only) |

The last three sit behind compose profiles and don't start with a plain
`docker compose up`: `caddy` and `dex` are boat-only (`--profile tls`),
`dex-dev` (`--profile dev-idp`) is the stand-in issuer for testing the SSO
flow on a dev machine.

**Plugin-managed containers**, launched by SignalK plugins through the
`signalk-container` plugin and named `sk-*`. These are in no compose file —
SignalK starts them itself:

| Container | Launched by | Notes |
|---|---|---|
| `sk-signalk-questdb` | `signalk-questdb` | time-series store |
| `sk-signalk-grafana` | `signalk-grafana` | its own Grafana, auto-provisioned against QuestDB |

`docker compose ps` shows only the first group. `docker ps -a` shows both.

Node-RED runs inside SignalK (the `@signalk/signalk-node-red` plugin), with
its flows under `signalk/red/`.

SignalK's whole state directory is a bind mount that's tracked in git. That
is why the in-place encryption scheme exists: SignalK reads and rewrites
these files while running, so they have to be plaintext on disk and
ciphertext in git.

Outbound integrations that need credentials: PostgSail
(`api.openplotter.cloud`), OpenWeather, Windy, and InfluxDB. Each token is
encrypted in the relevant `signalk/plugin-config-data/*.json`.

## The boat Pi runs none of this in Docker

The table above describes the intended deployment. The Pi aboard Symphony
doesn't match it: Docker isn't installed there, and SignalK, InfluxDB,
Grafana, Caddy, Dex, and Telegraf all run as systemd units instead.

The constraint is the hardware. It's a Pi 4B with 4 GB of RAM on a 32 GB SD
card, and the live data — SignalK's state directory, the InfluxDB store,
Grafana's database — already comes to a couple of gigabytes. Container
images plus a copy of that data don't fit, and the SD card is the part most
likely to fail first. Finishing the move to Docker is tracked in
`maintenance/priorities.md`; the likely answer is that it happens on the
machine that replaces this Pi, not on this Pi.

What the compose files supply as container configuration, systemd supplies
natively:

| Service | Native form | Config source |
|---|---|---|
| `caddy` | `/usr/local/bin/caddy`, custom build with `caddy-dns/cloudflare` | `/etc/caddy/Caddyfile`, a copy of `caddy/Caddyfile` with the three upstreams repointed from container names to `localhost` |
| `dex` | `/usr/local/bin/dex`, binary extracted from the OCI image | reads `dex/config.yaml` from the repo directly |
| `telegraf` | Debian package | `/etc/telegraf/telegraf.conf`, a symlink to `telegraf/telegraf.conf` |
| `signalk`, `grafana-server`, `influxdb` | Debian/npm installs predating the repo | their own config trees, not the repo's |

Every one of them reads the same rendered `.env` that compose would have
passed as `env_file`, delivered by an `EnvironmentFile=` drop-in under
`/etc/systemd/system/<unit>.service.d/`. So `scripts/render.py` remains the
single path from sops to running configuration, container or not.

Two traps live here. Dex and Telegraf run as `pi` rather than their own
service users, because `/home/pi` is mode 0700 and their config lives
inside it — the same reason `compose-idp.yml` pins Dex to uid 1000. And
Telegraf's packaged unit is `Type=notify`, which times out under this
configuration; the drop-in overrides it.

SignalK is installed twice on that host, 2.14.4 under `/usr/lib` and 2.30.0
under `/usr/local`. The service ran the older one — which predates OIDC
support entirely — until 2026-08-12, when the launcher script was repointed
at `/usr/local`. Both are still installed: the practical cost of the
OpenPlotter inheritance, and the clearest argument for containers whenever
the rebuild happens.

## Host metrics

Telegraf writes CPU, memory, swap, disk, disk I/O, temperature, network,
per-process and systemd unit state into the `symphony` InfluxDB bucket
every sixty seconds, batched into a single write to spare the SD card.

It exists because nothing else was recording the machine. SignalK's plugins
report vessel data and keep no history of the host, so a hang or an
out-of-memory event left nothing to look at afterwards, and diagnosis meant a
trip to the boat.

`signalk-healthcheck` used to raise alarms on CPU, memory and disk thresholds
and was removed on 2026-08-14. Telegraf measures the same things with history
and higher resolution; the off-boat heartbeat carries them somewhere that
survives the box dying; and the plugin's own alarms went to an SMTP host that
was never configured. What it did uniquely — warn that a data provider had
gone stale — it was no longer doing either, being configured to watch an
"OpenPlotter GPSD" provider that does not exist. That capability is worth
rebuilding in the heartbeat payload rather than in a plugin whose alarms ring
the boat's beeper.

Its credential is `influxdb_captain_token`, which is captain's all-access
token rather than a scoped one. That's a stopgap: the other InfluxDB tokens
in sops no longer authenticate against the running database, and untangling
that is its own task. `TELEGRAF_INFLUX_TOKEN` is a separate variable from
`INFLUX_TOKEN` precisely so the stopgap can be replaced without touching
Grafana's datasource.

## Remote access

rpi-connect is enabled but has been unreliable, and its browser shell
can't tunnel arbitrary tools (a Claude Code session, for one) — it isn't
`sshd`. Tailscale was added as the primary path instead: normal SSH over
a WireGuard mesh, no public exposure, and no dependency on the Cloudflare
zone or AWS account, neither of which had the groundwork (DNS record,
IAM users) this would have needed. rpi-connect stays enabled as a
fallback.

RUNBOOK.md → "Remote SSH access" has setup and verification.

## Web login (SSO)

Both web UIs authenticate against **Dex**, a small OIDC identity provider
running on the boat (`auth.<domain>`), which federates the actual login
out to GitHub or Google. Neither upstream is wired directly, for two
reasons:

- SignalK's built-in OIDC (server ≥ 2.30, `dist/oidc/` in the source)
  speaks to exactly **one** issuer — no side-by-side providers.
- GitHub doesn't do OIDC for user login at all — plain OAuth2, no
  discovery document, no ID tokens — so SignalK couldn't talk to it even
  alone. Dex's GitHub connector does the translation.

How each piece consumes Dex:

- **SignalK** is configured entirely through `SIGNALK_OIDC_*` environment
  variables, which override the `oidc` block in `security.json` — that's
  why the client secret can live in the ordinary Layer-1 `.env` path and
  no new in-place encryption rule was needed. After the code exchange
  SignalK mints its own JWT (subject to `security.json`'s expiration
  setting, currently `NEVER`); the IdP is not consulted again until the
  next login.
- **Grafana** uses `auth.generic_oauth` (`GF_AUTH_GENERIC_OAUTH_*`).
  `use_refresh_token` is deliberately `false`: Grafana's default is to
  sign the user out once the OAuth access token expires and can't be
  refreshed — offshore, that's about an hour after losing internet. With
  it off, Grafana's own session lifetimes govern (30 days idle, 90 days
  absolute).
- **Dex itself** is configured by `dex/config.yaml`, rendered from
  `dex/config.yaml.j2` by `scripts/render.py` — same trust model as
  `.env`: plaintext on disk, gitignored, secrets sourced from
  `secrets/symphony.sops.yaml`. It holds the upstream GitHub/Google client
  credentials and one static client (`symphony`) that SignalK and Grafana
  share. Storage is `memory` on purpose: Dex keeps no state worth keeping,
  and a restart only breaks logins in flight at that second.

### The permission model

The owner's login gets admin on SignalK; everyone else lands at
`SIGNALK_OIDC_DEFAULT_PERMISSION` (readonly). Deployed 2026-08-14.

SignalK's permission mapper reads groups and nothing else, and neither
GitHub nor Google sends any. Rather than manufacture a group, the server
is pointed at a claim that already exists:
`SIGNALK_OIDC_GROUPS_ATTRIBUTE=email` names which claim to treat as
groups, and the callback normalizes a bare string into a one-element
list, so the email *is* the group. `SIGNALK_OIDC_ADMIN_GROUPS` then
holds plain addresses — the same shape as Grafana's, and no Dex change
at all. Both providers work, because Dex carries an email claim for
either one.

The load-bearing part is `GROUPS_ATTRIBUTE`. Drop it and the server
looks for a `groups` claim nothing sends, and every SSO login silently
becomes readonly — no error, either side.

What makes this safe: permissions are recalculated on every login
(`findOrCreateOIDCUser` updates an existing user's type when the mapping
changes), so editing the list demotes or promotes people on their next
sign-in with no cleanup. And the failure mode is closed — a broken
mapping costs an admin their rights rather than handing anyone else
theirs, with `captain` still available to fix it.

Verified end-to-end against 2.30.0 on 2026-08-14, on a throwaway Dex and
SignalK pair: a listed address came out `admin`, an unlisted one
`readonly`, and swapping the list demoted the first and promoted the
second on their next login.

Two things to know before touching it. `dist/oidc/user-info.js` gates
groups behind `Array.isArray` and would reject a bare string — but
`extractUserInfo` is exported and never called anywhere in `dist`. It's
dead code, and an earlier version of this document cited it as proof
that no email-based hook existed. The live path is the callback in
`dist/oidc/oidc-auth.js`. Second, pointing `groupsAttribute` at a claim
that isn't a group is off-label: both halves are supported (the option
is documented, and the string-to-list normalization is deliberate and
commented), but a future release could tighten it and quietly demote the
owner. The RUNBOOK's post-deploy check is what catches that; the
upstream patch below is the durable fix.

The local `captain` account predates SSO and is unaffected by any of
this — it stays the offshore fallback.

Grafana is the exception because its role mapping can key off the
**email claim**: `role_attribute_path` holds a hand-managed list in
`.env.j2` (owner's email → Admin; `role_attribute_strict` refuses every
login that maps to nothing). The same email gets the same role from
either provider.

Open readonly sign-in is deliberate: no `orgs:` filter on the GitHub
connector, Google consent screen published to production — anyone with an
account at either provider can sign in from the boat's LAN and watch. The
identity lands in `security.json`'s user list, so there's a name
attached. SignalK's separate anonymous no-login readonly mode (`allow_readonly`)
is on as well, so reads don't require a login at all; signing in is what puts
a name against them.

Neither of the two routes considered on 2026-08-11 is what shipped — the
Dex-synthesized group was built and then dropped, since it only ever
covered Google and the `GROUPS_ATTRIBUTE` route above covers both for
less. The upstream one is still open, and is now a tidiness argument
rather than a coverage one:

- **Patch upstream.** An email list beside `adminGroups` in
  `dist/oidc/permission-mapping.js`, which today takes the groups array
  and nothing else. This is the only route that covers both providers,
  and it removes the Dex-side asymmetry rather than working around it.
  The OIDC code is Matti Airas's (Hat Labs), who is active on the SignalK
  Discord.

### TLS, offline, and the dev harness

- **TLS**: OAuth redirect URIs must be HTTPS on a real domain (both
  Google and SignalK's own validation enforce it). `caddy` terminates TLS
  for `signalk.` / `grafana.` / `auth.<domain>` with Let's Encrypt via
  Cloudflare DNS-01 — chosen because the boat is never reachable from the
  internet, which rules out HTTP-01. The image is built locally from
  `caddy/Dockerfile` because stock caddy lacks the Cloudflare DNS module.
- **Offline**: existing sessions survive (see above); new SSO logins need
  internet; local password logins always work; and name resolution
  offshore depends on the boat router's local DNS overrides — public DNS
  holds the same records but is unreachable at sea.
- **Dev harness**: `dex-dev` + `dev/dex.yaml` reproduce the whole flow
  locally with two personas — a one-click mock connector (whose identity
  carries groups `["authors"]`, useful for exercising the server's group
  mapping even though the boat's config ignores groups) and a password
  user. Its static secrets are intentionally public; nothing they protect
  exists outside the dev machine.

RUNBOOK.md → "SSO login (GitHub / Google)" has all procedures.

## Two paths to the same job

There are two parallel data paths, and which one is live has changed over
time. Check before assuming:

- SignalK → InfluxDB (`signalk-to-influxdb2`) → compose `grafana`
- SignalK → QuestDB (`signalk-questdb`) → `sk-signalk-grafana`

Credentials for both are tracked and encrypted, so the secrets tooling
doesn't decide between them. Three traps on the QuestDB path, all of which
fail quietly:

**Network names get a project prefix.** Both plugins default to
`networkName: symphony-net`, but compose actually creates
`symphony_symphony-net`. Finding no bare `symphony-net`, `signalk-container`
creates one, and the plugin containers end up on a bridge SignalK isn't on —
`getent hosts sk-signalk-questdb` from inside `signalk-server` won't resolve.
Point the plugins at `symphony_symphony-net`, or declare `symphony-net`
external and have compose join it.

**`questdbHost` defaults to `127.0.0.1`,** which inside the `signalk-server`
container means that container, not the host. It's ignored while
`managedContainer` is true, and starts mattering the moment you set it false.

**Both Grafanas want host port 3001.** The compose `grafana` service publishes
on 3001 and `signalk-grafana` defaults to `grafanaPort: 3001`, so the
plugin-managed one dies with
`Bind for 0.0.0.0:3001 failed: port is already allocated` and sits in
`Created`.

A container that lost this race is not retried — it stays in `Created`, and
freeing 3001 afterwards has not been seen to bring it back on its own.

*Unverified, and worth correcting if you learn otherwise:* the fix has never
been run. Pointing the plugin's `grafanaPort` at a free port is the obvious
move, but nobody has tried it, and it isn't known whether `signalk-grafana`
honours the change or whether its auto-provisioning assumes 3001 elsewhere.
Don't treat "just change `grafanaPort`" as a tested procedure.

To run QuestDB from your own compose file instead, set
`managedContainer: false` and point `questdbHost` at the service name. The
plugin then behaves as a client and `signalk-container` isn't involved.
`signalk-grafana` has no equivalent switch — it always runs its own.

## The Docker socket

`compose-signalk.yml` mounts `/var/run/docker.sock` into `signalk-server`
and adds the host's `docker` group. This is what lets `signalk-container`
start containers on behalf of other plugins — `signalk-questdb`,
`signalk-grafana`, `signalk-chart-locker` and `signalk-doctor` all delegate
their container lifecycle to it.

This has nothing to do with SignalK reaching InfluxDB or Grafana. Those are
ordinary HTTP calls over the container network. The socket is only about
*launching and managing* containers.

Docker API access is equivalent to root on the host: anything that can reach
the socket can start a container that mounts the host filesystem. That socket
is reachable from inside `signalk-server` — confirmed by querying `/version`
through it from within the container. So any SignalK plugin, or anything that
compromises one, can take the host.

While those plugins are enabled, plugin installation is the security boundary.
Know what you're installing, and consider turning off `backgroundUpdateChecks`
in the `signalk-container` config so new plugin code doesn't arrive
unattended.

The mount can go entirely if nothing needs managed containers: run QuestDB
from compose (`managedContainer: false`), drop `signalk-grafana`, and remove
the `docker.sock` volume and `group_add` from `compose-signalk.yml`.

A socket proxy is the usual middle path, but it buys little here —
`signalk-container` has to create containers to do its job, and container
creation is itself the escalation.

### The mount can go stale and strand the container

Seen once, on the WSL dev box, 2026-08-12: `signalk-server` exited 127 and
did not come back, with

```
error mounting "/run/desktop/mnt/host/wsl/docker-desktop-bind-mounts/Ubuntu/docker.sock"
to rootfs at "/var/run/docker.sock": not a directory
```

The host socket itself was healthy at the time — `srw-rw---- root docker`,
with an mtime matching Docker Desktop's restart. What had gone stale was
Docker Desktop's own bind-mount staging path, not `/var/run/docker.sock`.
`docker compose up -d --force-recreate` cleared it.

The cost is that the container sits dead with nothing retrying it, and
nothing alarms on it — this instance was down about eight hours before
anyone noticed.

*Unverified, and worth correcting if you learn otherwise:*

- Whether this recurs on every Docker Desktop restart or was a one-off. It
  has been observed exactly once.
- Why `restart: unless-stopped` didn't recover it. The container had been up
  since 2026-08-09 and `RestartCount` was still 0 afterwards, which points to
  the policy never retrying rather than retrying and giving up — but that is
  read off the counter, not observed directly.
- Whether anything short of a full recreate fixes it. Plain `docker start`
  was never tried.

This is a Docker Desktop / WSL failure mode. The boat Pi runs Docker, but
only for Dex and ntfy, and not under Docker Desktop — so it cannot be hit
there.

## How secrets are stored

Two encryption mechanisms, one age key, one store of truth
(`secrets/symphony.sops.yaml`):

- **Layer 1** — `docker-compose` `env_file: .env`. `.env` is gitignored,
  rendered by `scripts/render.py` from `secrets/symphony.sops.yaml`.
  `.env.example` documents every key.
- **In-place** — plugin config files that SignalK/Grafana read directly off
  disk (and rewrite at runtime) are tracked in git *as themselves*. A git
  clean/smudge filter (`scripts/sops_filter.py`, wired by `.gitattributes` +
  `scripts/setup-git-filters.sh`) encrypts just the secret leaf fields on
  commit and decrypts them back on checkout. The working copy on disk is
  always plaintext — SignalK reads and rewrites it exactly as it would
  otherwise. Only what git stores is encrypted.
- **API-provisioned** — Grafana users and all of InfluxDB. These have no file
  to encrypt; their state lives inside the containers and is created over
  HTTP by `scripts/provision_grafana_users.sh` and
  `scripts/provision_influxdb.sh`.

`.sops.yaml` is the single source of truth for which files carry secrets. The
pre-commit guard and the CI verifier read it at runtime via
`scripts/sops_paths.py`. Don't hardcode that list anywhere else; duplicate
copies drift, and the copy that drifts is usually the one doing the checking.

## Email pseudonyms

Anyone who logs in via OIDC gets written into `signalk/security.json` by
SignalK. That record is wanted — knowing who had access to the boat is a
feature, and a GitHub login shows up as a readable handle. What isn't wanted
is publishing a guest's mailbox as a side effect. Dex's `google` connector
sets no `preferred_username`, so SignalK falls back to the address, and it
lands in `username` as well as `oidc.email`.

Addresses are therefore replaced with a short keyed hash on the way into git
and restored on the way out, by the same clean/smudge filter that does the
sops encryption. Three consequences worth knowing:

- **Selection is by value, not field name.** sops picks what to encrypt with
  `encrypted_regex` on key names. That can't work here: no key-name rule
  matches the `username` holding an address without also matching
  `mark-brannan`. Any string that parses as an address gets tokenized,
  wherever it sits — which self-selects correctly with no per-user config.
- **Not sops, because identifiers have to stay comparable.** An `ENC[...]`
  blob is ~200 characters and re-randomizes on every write. A token is short,
  stable forever, and greppable, so `git log -S` still answers when a person
  got access and when it went away.
- **The salt is what makes it a pseudonym.** A 7-character hash of a
  `@gmail.com` address falls to a dictionary attack in seconds without one.
  It lives in `secrets/pseudonyms.sops.yaml` beside the map.

### Who can read the map

`.sops.yaml` gives `secrets/pseudonyms.sops.yaml` its own recipient list —
the two global keys plus a third, the manifest key — instead of the shared
anchor every other rule uses. That third key answers "who is pid.rj232vx?"
and nothing else, so it can go to someone who needs the answer without also
trusting them with the boat's live credentials.

Two traps come with a per-rule list:

- sops applies the **first** matching creation rule. The narrow
  `secrets/pseudonyms\.sops\.ya?ml$` rule has to sit above the general
  `secrets/.*` one; below it, the anchor wins and the manifest key is
  quietly dropped.
- An explicit list doesn't follow the anchor. A rotation that edited only
  the anchor would leave the list holding the retired key, and the file
  would keep committing and keep looking encrypted right until that private
  key was deleted. Both are edited together through
  `scripts/sops_recipients.py`, which is why `rotate_age_key.sh` has no path
  that touches one without the other.

`oidc.sub` is deliberately left alone. It is self-regulating *today*: the
GitHub subject decodes (base64 protobuf, no key) to a numeric user ID that
resolves to a public profile with one unauthenticated API call, which is
exposure we're content with; the Google subject has no public resolver. That
is a property of those two Dex connectors, not a guarantee — GitLab IDs
resolve publicly, and Dex's static password DB puts whatever string you typed
into the subject. Re-check it before adding a connector.

## Per-machine values in plugin config

The tracked plugin-config files double as the live configuration on every
checkout, and one value genuinely differs by machine: `signalk-ntfy`'s
server URL is `http://ntfy:80` on the dev stack (SignalK reaches ntfy over
the compose network) but `http://localhost:8090` on the boat Pi (native
SignalK, ntfy container's published port). With a single committed file,
whichever machine committed last silently broke the other's alarm delivery.

The fix reuses the clean/smudge filter architecture: git stores a
placeholder (`"url": "{{ ntfy_url }}"`), and a second filter (`hostvars`,
`scripts/hostvars_filter.py`) expands it on checkout from a gitignored
per-machine `hostvars.local.yaml` and contracts it back on commit. SignalK
reads and rewrites the file exactly as before; the machine-specific value
never reaches git.

Not sops, deliberately: these values aren't secrets, they just aren't
shared — an ENC[...] blob would hide a harmless URL and still couldn't
differ per machine. Only whole string values substitute, matched
byte-for-byte, so a value can never be rewritten where it appears inside
some longer string. `.hostvars.yaml` declares which files and variable
names participate; the placeholder syntax matches the jinja2 templates
`scripts/render.py` already renders, so an eventual Ansible migration
treats these files as the templates they effectively are.

The invariant — git's copy holds the placeholder, never one machine's
literal value — is enforced the same way as the sops layer: a loud warning
from the clean filter, a pre-commit hook (`hostvars-placeholders`), and the
same check in CI (`scripts/hostvars_filter.py check`).

### Alternatives considered for the ntfy URL

Two other mechanisms could have carried this value; both were rejected for
this case, and the reasons bound when each is the right tool.

**A dev override** (`dev/plugin-config-overrides/`, a read-only bind mount
over the repo's copy). Right for plugins that must be *forced* into a dev
state — the pin deliberately breaks admin-UI saves, and it assumes the
committed file is the boat's value with dev as the exception. Neither fits
ntfy: the plugin is live in both environments, its other settings (topic,
levels, `minIntervalMinutes`) should stay editable and committable from
either machine, and the URL difference has no "real" side for the repo to
own. The filter keeps the committed file environment-neutral and the
admin-UI workflow intact on both machines.

**One URL everywhere via DNS** — a split-horizon name, an `/etc/hosts`
alias, or routing ntfy through Caddy. The two SignalK instances talk to
*different* ntfy servers, each co-located with its SignalK; a shared name
would not remove the per-machine difference, only relocate it from a
declared, CI-checked `hostvars.local.yaml` into unversioned network state —
a dnsmasq override per router, an `/etc/hosts` entry, a published-port
choice — one copy per LAN, invisible to git and to `check`. On the boat it
would also insert a resolver (and, via Caddy, the TLS front door and its
offshore-expiring certificates) into the alarm-delivery path, which today
depends on nothing but the loopback interface. Dev in fact already uses a
split-horizon name: `ntfy` resolves only inside the compose network, via
Docker's embedded DNS. The boat's equivalent binding is `localhost` — it
just cannot be spelled identically, and alarms are the last traffic that
should take on new dependencies to make a config file byte-identical.

A client-facing name (a phone finding ntfy on the boat LAN, via the
existing router DNS override and a Caddy route) is a separate, compatible
concern — it would not change what SignalK dials.

## How the safety net is layered

The layers are not equally trustworthy:

| Layer | What it catches | Can it be bypassed? |
|---|---|---|
| sops clean filter | encrypts configured fields automatically on commit | only if the clone never ran `setup-git-filters.sh` |
| pre-commit hooks | unencrypted secrets, cleartext credentials, forbidden files | **yes** — `--no-verify`, or never installing them |
| GitHub Actions | all of the above, plus full-history and live-credential scans | **no** — runs on every push |

CI is the enforcement boundary; the hooks are fast feedback, not a guarantee.
That is why `.github/workflows/validate.yml` re-runs the same checks rather
than trusting that a hook already ran.
