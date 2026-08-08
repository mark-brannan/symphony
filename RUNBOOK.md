# Symphony systems runbook

Operating and recovering S/V Symphony's onboard computer systems: the
SignalK stack, the host it runs on, and the encrypted configuration that
ties it together.

This repo is public, so nothing sensitive can sit in it in the clear.
Secrets are encrypted with sops before git ever sees them.

Procedures only. For how the stack is built and why — containers, the two
data paths, the encryption design — see
[reference/software_stack.md](reference/software_stack.md). Physical systems
(engine, rigging, ground tackle, plumbing) live in `systems/*.md`, with work
logged in `maintenance/log.md`.

## Bringing up a host

Four phases, in this order: tooling, key material, repo, services. Each ends
with a check — run it, because a failure in an early phase tends to surface
two phases later as something that looks unrelated.

### Phase 1 — Host and tooling

The host needs Docker (with compose v2), and on Linux your user in the
`docker` group. Then install `pre-commit`:

```bash
sudo apt install pre-commit     # Debian/Ubuntu, incl. Pi OS and WSL2
brew install pre-commit         # macOS
```

Prefer the package manager over `pip` — some of these hosts have no `pip`
at all.

`sops` and `age` ship as standalone binaries. Get them from
[sops releases](https://github.com/getsops/sops/releases) and
[age releases](https://github.com/FiloSottile/age/releases) and put them on
`PATH`, e.g. `~/.local/bin`.

*Verify:* `docker compose version && sops --version && age --version && pre-commit --version`

### Phase 2 — Key material

Get the age **private** key onto the host out-of-band — password manager,
offline copy, another host you already trust. Never through this repo, never
over a channel you wouldn't send the secrets themselves over.

```bash
mkdir -p ~/.config/sops/age
cp <the key> ~/.config/sops/age/keys.txt
chmod 600 ~/.config/sops/age/keys.txt
```

(Or point `SOPS_AGE_KEY_FILE` at it wherever it lives.)

*Verify:* `sops --decrypt secrets/symphony.sops.yaml | head -1` returns
readable YAML. If it doesn't, stop — nothing downstream will work, and
continuing will produce confusing failures that look like Docker problems.

### Phase 3 — Repo and configuration

```bash
git clone https://github.com/mark-brannan/symphony.git
cd symphony
bash scripts/setup-git-filters.sh
python3 scripts/render.py
```

`setup-git-filters.sh` is the one onboarding command: it wires the sops
clean/smudge filter, installs the pre-commit hooks, clears any stale
`core.hooksPath`, and decrypts the in-place files onto disk. It only touches
files that are *still ciphertext*, so it can never clobber live local config,
and it's safe to re-run at any time.

Filters can't be wired before this point — git filter commands live in
`.git/config`, which git deliberately doesn't version (arbitrary commands
from a cloned repo would be a code-execution vector). That's why
secret-bearing files check out encrypted and need this step.

`render.py` decrypts `secrets/symphony.sops.yaml` into `.env`, which every
container reads via `env_file`.

*Verify:* `bash scripts/verify_encrypted.sh` passes, and
`grep -c ENC .env` returns 0 (i.e. `.env` is fully rendered plaintext —
it's gitignored and must never be committed).

### Phase 4 — Services

```bash
docker compose up -d
```

On the boat, once SSO is configured (next section), use this instead so
the TLS proxy and the identity provider come up too:

```bash
docker compose --profile tls up -d --build
```

Compose starts InfluxDB first; SignalK and Grafana both declare
`depends_on: influxdb`. Note that `depends_on` waits for the *container*,
not for InfluxDB to be ready to serve — on a cold start the provisioning
scripts below may need a retry.

Then converge the service-internal state, which lives inside those
containers rather than in any file:

```bash
bash scripts/provision_grafana_users.sh
bash scripts/provision_influxdb.sh
```

Both are idempotent and safe to re-run. Grafana's needs its superadmin
password already applied — see the `GF_SECURITY_ADMIN_PASSWORD` note under
"Rotating a secret" if you're on an existing (not fresh) `grafana-data`
volume.

*Verify:* `bash scripts/test_integration.sh` — this is the real check that
the stack works end to end.

### First-ever boot

If no `security.json` has ever existed, there's nothing to decrypt. Let
SignalK create its own through the setup wizard on first admin login, then
`git add signalk/security.json` once so it starts being tracked — encrypted
— from that point forward.

### What `provision_influxdb.sh` does

It can mint credentials that then need propagating by hand, so read this
before running it:

- On a **fresh** volume it runs `/api/v2/setup` (org `darkstarllc`, bucket
  `symphony`) and stores the resulting operator token. On an **existing**
  one it uses the operator token already in `secrets/symphony.sops.yaml`.
- Either way it creates the `captain` user as an org *member*, not owner —
  InfluxDB OSS has only those two levels — and mints read/write-scoped
  tokens for the SignalK plugin and Grafana's datasource if they don't
  already exist.
- **If it minted a new `influx_token`:** re-run `scripts/render.py` and
  `docker compose up -d --force-recreate grafana`.
- **If it minted a new `influxdb_signalk_token`:** update the `token` field
  in `signalk/plugin-config-data/signalk-to-influxdb2.json` and restart
  `signalk-server`.

## SSO login (GitHub / Google)

SignalK and Grafana web UIs show a "Sign in with GitHub / Google" button.
Behind it sits Dex, a small identity provider on the boat at
`auth.<domain>`: SignalK and Grafana trust only Dex; Dex hands the actual
login to GitHub or Google. Any account at either provider can sign in and
view SignalK (readonly). The owner's email also gets Grafana Admin.
Anything that changes state still uses the local password logins
(`captain`, Grafana's superadmin), which are also the no-internet
fallback.

Steps 1–3 are one-time setup from any machine. Step 4 runs on the boat.

### 1 — Domain and DNS (one-time)

Prerequisite: a registered domain with its DNS hosted at Cloudflare (the
free plan is enough). A subdomain of a domain already on Cloudflare works
too (`DOMAIN` can be `boat.example.com`).

1. In Cloudflare DNS, add three **A** records pointing at the LAN IP of
   the host running the stack (DNS only / grey cloud, not proxied):
   - `signalk.<domain>` → e.g. `192.168.1.50`
   - `grafana.<domain>` → same IP
   - `auth.<domain>` → same IP

   Give that host a fixed LAN IP first (DHCP reservation in the boat
   router). A public name resolving to a private IP is fine — nothing
   here is reachable from the internet.
2. Create the certificate-issuance token: Cloudflare → My Profile → API
   Tokens → Create Token → "Edit zone DNS" template → limit it to this
   one zone.
3. On the **boat router**, add local DNS overrides for the same three
   names → the same LAN IP (dnsmasq:
   `address=/signalk.<domain>/192.168.1.50`, or the router UI's "local
   DNS records"). Don't skip this: offshore there is no public DNS, and
   without a local override even already-logged-in devices can't resolve
   the names at all.

*Verify:* from a device on the boat LAN **with the WAN link
disconnected**, `nslookup signalk.<domain>` returns the LAN IP.

### 2 — OAuth apps (one-time)

**GitHub** — under the personal account, no org involved:
[github.com/settings/developers](https://github.com/settings/developers)
→ OAuth Apps → New OAuth App:

- Application name: anything (e.g. "Symphony boat systems")
- Homepage URL: `https://auth.<domain>`
- Authorization callback URL: `https://auth.<domain>/dex/callback`

Copy the client ID; "Generate a new client secret" and copy it.

**Google** — at
[console.cloud.google.com](https://console.cloud.google.com):

1. Create a project (any name).
2. APIs & Services → OAuth consent screen: user type **External**, app
   name + support email → then **publish to production** (Audience →
   "Publish app"). Not Testing: testing mode caps sign-ins to a
   100-address allowlist, and the open readonly door is intended. The
   basic scopes used need no Google review.
3. Credentials → Create credentials → OAuth client ID → type **Web
   application** → one redirect URI:
   `https://auth.<domain>/dex/callback`
4. Copy the client ID and client secret.

Both providers talk only to Dex, hence the single callback URL each — no
signalk/grafana URLs belong in either console.

### 3 — Secrets store (one-time)

```bash
sops secrets/symphony.sops.yaml
```

Replace the `REPLACE_WITH_*` placeholders: `boat_domain`,
`github_oauth_client_id`, `github_oauth_client_secret`,
`google_oauth_client_id`, `google_oauth_client_secret`,
`cloudflare_api_token`. `owner_email` is the email that gets Grafana
Admin. Leave `dex_symphony_client_secret` alone — it's the pre-generated
secret shared between Dex and SignalK/Grafana; nothing outside this repo
ever needs it. Commit the file, then:

```bash
python3 scripts/render.py
```

(renders both `.env` and `dex/config.yaml` — the latter is gitignored
plaintext, same trust level as `.env`).

### 4 — Deploy (on the boat)

```bash
git pull
python3 scripts/render.py
docker compose --profile tls up -d --build
```

The `tls` profile adds `caddy` (HTTPS for all three hostnames, Let's
Encrypt via Cloudflare DNS-01) and `dex`. The first run builds the caddy
image and issues certificates, so it needs internet — do it dockside.

*Verify:*

```bash
curl -s https://signalk.<domain>/signalk/v1/auth/oidc/status
curl -s https://auth.<domain>/dex/.well-known/openid-configuration | head -3
```

The first expects `"enabled":true` and
`"issuer":"https://auth.<domain>/dex"`; the second returns JSON if Dex is
up behind Caddy. If TLS itself fails, certificates haven't issued — check
`docker logs caddy`. Then from a browser on the LAN:

- `https://signalk.<domain>` → sign in with either provider → Security →
  Users shows the new user with type `readonly`.
- `https://grafana.<domain>` → the owner's login → Admin; any other
  account → refused (that's the strict email list working).
- The `captain` password still logs in on SignalK with admin.

### Who gets what

| Login | SignalK | Grafana |
|---|---|---|
| any GitHub or Google account | readonly | refused |
| the owner's email, via either provider | readonly | Admin |
| `captain` (local password) | admin | — |
| Grafana superadmin / provisioned users (password) | — | Admin / as provisioned |

SSO permissions are re-applied at every login: promoting an SSO user in
the SignalK admin UI reverts the next time they sign in, and Grafana
re-evaluates its email list the same way.

### Granting more than readonly

- **Grafana:** add the email to
  `GF_AUTH_GENERIC_OAUTH_ROLE_ATTRIBUTE_PATH` in `.env.j2` — e.g. append
  `|| email=='crew@example.com' && 'Editor'` — then
  `python3 scripts/render.py` and
  `docker compose up -d --force-recreate grafana`. A hand-managed list,
  in the repo.
- **SignalK:** not available for SSO logins — the stock server maps
  permissions only from IdP group claims, which these providers don't
  supply. Someone who needs to change things uses the `captain` login.

### Removing someone

SSO guests need no removal — they're readonly. To cut a person off
entirely: delete their user in SignalK (Security → Users — SignalK
sessions never expire, and deleting the user is what invalidates the
session), remove their email from the Grafana role path if it's there,
and delete their Grafana user (Administration → Users).

### Offshore (no internet)

- Devices already signed in stay signed in: SignalK sessions don't
  expire, Grafana sessions last 30 days idle / 90 days max.
- SSO login needs internet, so a fresh device offshore uses local login
  instead: on SignalK, the username/password form below the SSO button
  (`captain`, password in the secrets store); on Grafana, the password
  box.
- After ~60 days fully offline, browsers start warning about an expired
  certificate. It's only a warning; renewal happens on its own once
  internet returns.

### Re-testing the login flow without real providers

A local stand-in issuer (`dex-dev`) exercises the whole SignalK OIDC
flow on a dev machine. It serves two personas: a "Mock upstream"
connector that logs in as `kilgore@kilgore.trout` in one click, and a
password user `dev@example.com` / `password`. Both land as `readonly`
under the boat's config.

```bash
docker compose --profile dev-idp up -d dex-dev
# point .env's SIGNALK_OIDC_* at it (gitignored; re-render to undo):
#   ISSUER=http://dex-dev:5556/dex  CLIENT_ID=symphony-local
#   CLIENT_SECRET=local-dev-not-a-secret
#   REDIRECT_URI=http://localhost:3001/signalk/v1/auth/oidc/callback
docker compose up -d signalk
```

Log in via the SSO button, then restore:

```bash
python3 scripts/render.py
docker compose up -d signalk
docker compose --profile dev-idp rm -sf dex-dev
```

and delete the test users in SignalK Security → Users (they land in
git-tracked `signalk/security.json` otherwise).

## Adding a secret

**In-place (a plugin config file SignalK/Grafana already owns):**

```bash
scripts/add_inplace_secret.sh <file> <field> [<field2> ...]
git commit
```

Worked example — this is exactly what wires up a new plugin's token:

```bash
scripts/add_inplace_secret.sh signalk/plugin-config-data/signalk-postgsail.json token
git commit -m "Encrypt signalk-postgsail.json's token"
```

The script adds the `.sops.yaml` rule and the `.gitattributes` entry
(skipping either if already present), checks the two stay consistent, stages
the file, and fails loudly if the field didn't actually encrypt. Idempotent
— re-run it any time.

Two files get touched, not three: the pre-commit guard and the CI verifier
read `.sops.yaml` at runtime, so they pick up the new file automatically.

**Layer 1 (a new `.env` value):**

```bash
sops secrets/symphony.sops.yaml          # add the key, save
$EDITOR .env.example                     # add the same key, blank/dummy value
$EDITOR .env.j2                          # add the {{ jinja }} line
python3 scripts/render.py
```

## Rotating a secret

**Layer 1:**

```bash
sops secrets/symphony.sops.yaml          # edit the value, save
python3 scripts/render.py
docker compose up -d --force-recreate <service>
```

`GF_SECURITY_ADMIN_PASSWORD` is the exception — it only takes effect on a
*fresh* `grafana-data` volume. On an existing one, also run:

```bash
docker exec grafana grafana cli admin reset-admin-password '<value>'
curl -u admin:<value> http://localhost:3000/api/org      # expect 200
```

**In-place:** change it through the SignalK admin UI, then:

```bash
git add <file>
git commit
```

The clean filter re-encrypts on the way in. If the same secret is also
mirrored in `secrets/symphony.sops.yaml` (like `influx_token`, which Grafana
needs as an env var — a second consumption path besides SignalK reading it
off disk), update both.

**Grafana / InfluxDB users:** edit the password in
`secrets/symphony.sops.yaml`, then re-run the matching provisioner — both
converge password + role on every run, safe to re-run any time:

```bash
scripts/provision_grafana_users.sh
scripts/provision_influxdb.sh
```

**InfluxDB tokens** can't be reset in place — a token's value is only ever
shown once, at creation. To rotate:

```bash
# find the old authorization's id
curl -H "Authorization: Token $(sops --decrypt --extract '["influxdb_operator_token"]' secrets/symphony.sops.yaml)" \
  "http://localhost:8086/api/v2/authorizations?orgID=<org>"

curl -X DELETE -H "Authorization: Token <operator_token>" \
  "http://localhost:8086/api/v2/authorizations/<old_id>"

scripts/provision_influxdb.sh   # mints a fresh one now that the old one's gone
```

Then update `secrets/symphony.sops.yaml` and (for the SignalK token)
`signalk/plugin-config-data/signalk-to-influxdb2.json`.

`ROTATION.md` records credentials already rotated and why.

## Rotating the age key

The age key is the master key: it decrypts everything else. Rotate it
annually, and immediately if you think it's been exposed.

```bash
scripts/rotate_age_key.sh status                  # what's the current state?
scripts/rotate_age_key.sh add --generate          # phase 1: new key joins
#   ... back up the new key, deploy it to every host ...
scripts/rotate_age_key.sh verify <new-public-key> # gate: prove it works alone
scripts/rotate_age_key.sh retire <old-public-key> # phase 2: old key leaves
```

Commit after each phase.

### Why two phases

Between phase 1 and phase 2 both keys decrypt everything. That window is the
point: it lets you get the new key onto every host and confirm each one
works before the old key stops being accepted. Running both phases together
locks out any host you haven't updated yet.

### Don't skip `verify`

`verify` checks that the new key can decrypt everything **on its own**. Run
it before `retire`. If it fails it names the files that didn't re-key; fix
those with another `add` and run it again.

It's a separate step because two things make a half-finished rotation look
finished:

- The in-place files aren't re-keyed by `sops updatekeys`. On disk they're
  plaintext and only git holds the ciphertext, so they're re-keyed by making
  the clean filter re-encrypt (`SOPS_FILTER_REKEY=1`, which the script
  sets). Without that the filter reuses the old ciphertext unchanged, and
  those files stay readable only by the old key.
- `SOPS_AGE_KEY_FILE` doesn't limit sops to that one key. sops also reads
  `~/.config/sops/age/keys.txt`, so an obvious "can the new key read this?"
  test passes because the *old* key is still in the default keyring.

`verify` works around both: it checks the staged ciphertext with `HOME` and
`XDG_CONFIG_HOME` pointed away from the real keyring, and it proves that
isolation with a throwaway key before trusting its own result.

### What rotation does and does not protect

Rotating the age key protects **future** commits. It does not re-encrypt git
history: every old commit still holds ciphertext readable by the retired
key.

So if the old key was **compromised**, rotating it is not sufficient —
anyone with that key plus a clone can read every secret ever committed. In
that case you must also rotate the underlying secrets themselves (the
InfluxDB tokens, the SignalK `secretKey`, the API keys), following
"Rotating a secret" above. Rotating the age key alone is the right response
to *hygiene*; rotating the secrets is the right response to *exposure*.

### If a host is missed

A host still holding only the retired key will fail to decrypt after phase
2. Nothing is lost — copy a current private key to
`~/.config/sops/age/keys.txt` on that host and re-run
`scripts/setup-git-filters.sh`. The keyring file takes multiple keys, one
block each.

## Removing a secret

To stop tracking a file's secret (plugin uninstalled, field no longer used):

1. Delete its `path_regex` block from `.sops.yaml`.
2. Delete its `filter=sops` line from `.gitattributes`.
3. `python3 scripts/sops_paths.py check` — confirms the two still agree.
4. If the file itself is going away: `git rm --cached <file>` and add it to
   `.gitignore`.

Removing the rules does **not** un-publish anything already committed. If
the secret was ever live in a public commit, rotate it — see below.

## When a plugin isn't in the config UI

A plugin that crashes on load doesn't appear in Server → Plugin Config at
all, which looks identical to not being installed. Check the log first:

```bash
docker logs signalk-server --since 5m 2>&1 | grep 'failed to start'
docker inspect <container> --format '{{.State.Error}}'   # for sk-* containers
```

Missing-module errors usually mean a broken dependency tree. The fix is a
clean reinstall against `signalk/package.json`, which declares every plugin:

```bash
docker compose stop signalk
mv signalk/node_modules signalk/.node_modules_old
docker run --rm -v "$PWD/signalk:/home/node/.signalk" -w /home/node/.signalk \
  --entrypoint npm signalk/signalk-server:latest install
docker compose start signalk
```

Move the old tree aside rather than deleting it, so you can put it back.
Note `signalk/.npmrc` sets `package-lock=false`, so versions resolve fresh
against the `^` ranges each time — this is not a reproducible install. npm 11
also blocks postinstall scripts by default; if a plugin needs a native binary
(`sharp`, `esbuild`), run `npm approve-scripts <pkg>` and reinstall it.

## When a hook blocks your commit

The message names which check failed. In rough order of likelihood:

- **"staged WITHOUT sops encryption markers"** — the clean filter didn't
  run. Almost always a clone that never ran `scripts/setup-git-filters.sh`.
  Run it, then re-stage the file.
- **"looks like a cleartext credential"** — a config file has a
  password/token/apikey field with a real value. Either wire it up with
  `scripts/add_inplace_secret.sh`, or if it genuinely isn't a secret, move
  the value out of a field with that name.
- **gitleaks finding** — a credential-shaped string anywhere in the diff.
  The output is redacted; look at the file and line it names. If it's a
  genuine false positive, add a *narrow* allowlist entry to `.gitleaks.toml`
  with `condition = "AND"` so you silence one string in one file, never a
  whole path.
- **"sops config is inconsistent"** — `.sops.yaml` and `.gitattributes`
  disagree. The message says which file and which direction. A sops rule
  without a filter entry is the dangerous one: that file would commit as
  plaintext.

To see everything without committing:

```bash
pre-commit run --all-files
```

**`--no-verify` skips all of it.** It exists for genuine emergencies. CI
will still catch an unencrypted secret on push — you'll just find out in
public instead of at your terminal.

## Scanning for leaks by hand

Both scanners are pinned to the same versions CI uses.

```bash
# Pattern + entropy scan over the whole history
docker run --rm -v "$PWD:/repo" -w /repo zricethezav/gitleaks:v8.30.1 \
  git --no-banner --redact --config /repo/.gitleaks.toml

# Live-credential scan: actually calls provider APIs to see what still works
scripts/scan_verified_secrets.sh
```

The second is the one that matters during an incident. gitleaks tells you
something *looks* like a secret; trufflehog tells you whether it *still
works*. Output is redacted in both — deliberately, since CI logs on a public
repo are world-readable.

## A secret was committed in plaintext

**Rotate first. Everything else is secondary.**

Once a secret is pushed to a public repo, assume it's compromised — it's in
GitHub's API, in forks, and in anything that scrapes new commits. Rewriting
history does **not** un-publish it: GitHub keeps unreferenced commits
reachable by SHA.

1. **Revoke and reissue the credential at its provider.** This is the only
   step that actually fixes anything. See "Rotating a secret" above.
2. Confirm the new value is encrypted before it goes back:
   `bash scripts/verify_encrypted.sh`
3. Work out how it got through. Usually: the file had no `.sops.yaml` rule.
   Add one with `scripts/add_inplace_secret.sh`.
4. Check whether it's still live anywhere:
   `scripts/scan_verified_secrets.sh`
5. Only *then* consider history rewriting, and only if the value can't be
   rotated (rare — a hardcoded key in a third-party device, say). It
   requires a force-push, breaks every existing clone, and does not remove
   the data from GitHub's servers without also contacting GitHub Support.

## Recovering a lost age key

The age private key is the single point of failure — anyone provisioning a
new host, or recovering this one, needs it. It is never in git.

You can avoid most of this section by keeping two valid recipients: run
`scripts/rotate_age_key.sh add --generate`, store the second key somewhere
separate from the first, and never retire it. Losing one key then costs you
nothing.

- **If you have a backup** (recommended: store the contents of
  `~/.config/sops/age/keys.txt` in a password manager or a printed offline
  copy at provisioning time): restore it to `~/.config/sops/age/keys.txt` on
  the new host and everything above works normally.
- **If the key is truly gone:** every sops-encrypted value — the whole
  `secrets/symphony.sops.yaml` store, and the encrypted fields inside the
  in-place files as they exist in git — is unrecoverable from git alone.
  Recovery path: generate a fresh keypair (`age-keygen`), update the
  recipient in `.sops.yaml`, then re-populate from live sources.
  `secrets/symphony.sops.yaml` values come from whatever's currently live in
  the running containers/`.env`; the in-place files come from their current
  plaintext-on-disk copies, which are unaffected by losing the key — only
  the *git-stored* encrypted copies become unreadable. Then `git add` them
  again under the new key.

  Exception: `influxdb_operator_token` has no plaintext-on-disk copy
  anywhere (it's not consumed by any container, only by provisioning
  scripts). If it's gone, sign in to InfluxDB with
  `influxdb_init_username`/`_password` — a real login, not a token — and
  mint a replacement via `POST /api/v2/authorizations`.

  **The `~/symphony-backups/` directory holds a plaintext snapshot of the
  live SignalK config** taken 2026-08-07. It is deliberately outside the
  repo. Treat it as sensitive: it is a full set of live credentials in the
  clear, and it is a recovery source of last resort.

## Upgrading the scanners

```bash
pre-commit autoupdate      # bumps pinned hook revisions
```

This fetches from GitHub, so do it **dockside, not underway** — a failed
fetch mid-passage will block commits until you revert the config. Commit the
resulting rev change so every machine and CI agree on which scanner version
cleared a given commit. Bump the pinned image tags in
`.github/workflows/validate.yml` and `scripts/scan_verified_secrets.sh` to
match.
