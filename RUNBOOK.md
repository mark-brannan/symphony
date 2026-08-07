# Secrets & config runbook

Two mechanisms, one age key, one store of truth (`secrets/symphony.sops.yaml`):

- **Layer 1** — `docker-compose` `env_file: .env`. `.env` is gitignored,
  rendered by `scripts/render.py` from `secrets/symphony.sops.yaml`.
  `.env.example` documents every key.
- **In-place** — `signalk/security.json`, `signalk/plugin-config-data/signalk-to-influxdb2.json`,
  and `signalk/plugin-config-data/signalk-dsc.json` are tracked in git *as
  themselves*. A git clean/smudge filter (`scripts/sops_filter.py`, wired by `.gitattributes`
  + `scripts/setup-git-filters.sh`) transparently encrypts just the secret
  leaf fields (`secretKey`, `password`, `token`, `logbookToken`) on commit
  and decrypts them back to plaintext on checkout. The working copy on disk
  is always plaintext — SignalK/Grafana read and rewrite it exactly as they
  do today, no behavior change. Only what git stores (and what's on GitHub)
  is encrypted.
- **API-provisioned** — Grafana users and all of InfluxDB. Neither has a
  file for a template or a git filter to act on: Grafana OSS has no
  file-based user provisioning at all (confirmed by inspecting the image —
  real provisioning dirs are only `access-control, alerting, dashboards,
  datasources, notifiers, plugins`), and InfluxDB's org/bucket/users/tokens
  are pure runtime state created through its own setup + admin API.
  `scripts/provision_grafana_users.sh` and `scripts/provision_influxdb.sh`
  are the equivalent: idempotent, create-or-converge via HTTP API calls
  using a superadmin/operator credential from Layer 1.

## Provisioning a new host

1. Install `sops` and `age` (no package needed — both ship as standalone
   binaries; see https://github.com/getsops/sops/releases and
   https://github.com/FiloSottile/age/releases for the linux-amd64 build,
   drop them somewhere on `PATH` such as `~/.local/bin`).
2. Get the age private key out-of-band (see below) onto the new host at
   `~/.config/sops/age/keys.txt` (`chmod 600`), or set `SOPS_AGE_KEY_FILE`
   to point at it.
3. `git clone` the repo. The clean/smudge filter isn't active yet (git
   filter commands live in `.git/config`, which git deliberately doesn't
   version), so the in-place files will check out still encrypted at this
   point.
4. `bash scripts/setup-git-filters.sh` — wires the `sops` filter and the
   `.githooks/pre-commit` hook.
5. `git checkout -- signalk/security.json signalk/plugin-config-data/signalk-to-influxdb2.json signalk/plugin-config-data/signalk-dsc.json`
   — re-checks-out those 3 files now that the smudge filter is live, which
   decrypts them to real plaintext on disk.
6. `python3 scripts/render.py` — decrypts `secrets/symphony.sops.yaml` and
   renders `.env`.
7. `docker compose up -d`.
8. `bash scripts/provision_grafana_users.sh` — creates/converges Grafana
   users (currently just `captain`). Needs Grafana up and its superadmin
   password already applied (see the `GF_SECURITY_ADMIN_PASSWORD` note
   under "Rotating a secret" if this is an existing, not fresh, volume).
9. `bash scripts/provision_influxdb.sh` — on a truly fresh InfluxDB volume,
   runs `/api/v2/setup` (org `darkstarllc`, bucket `symphony`) and stores
   the resulting operator token; on an existing one, uses the operator
   token already in `secrets/symphony.sops.yaml`. Either way, creates the
   `captain` user (org member, not owner — InfluxDB OSS's access model
   only has those two levels, no Grafana-style viewer/editor/admin) and
   mints read/write-scoped tokens for the SignalK plugin and Grafana's
   datasource if they don't already exist. If it minted a new
   `influx_token`, re-run `scripts/render.py` and recreate `grafana`; if it
   minted a new `influxdb_signalk_token`, update the `token` field in
   `signalk/plugin-config-data/signalk-to-influxdb2.json` by hand and
   restart `signalk-server`.

If this is a genuinely first-ever boot (no prior `security.json` exists
anywhere, nothing to decrypt), skip step 5 and just let SignalK create its
own `security.json` through the setup wizard on first admin login as
normal — then `git add signalk/security.json` once, so it starts being
tracked (encrypted) from that point on.

## Adding a secret

**In-place (a plugin config file SignalK/Grafana already owns):**

```
scripts/add_inplace_secret.sh <file> <field> [<field2> ...]
git commit
```

Worked example — this is exactly what wires up a new plugin's token:

```
scripts/add_inplace_secret.sh signalk/plugin-config-data/signalk-postgsail.json token
git commit -m "Encrypt signalk-postgsail.json's token"
```

The script adds the `.sops.yaml` rule, the `.gitattributes` entry, and the
`.githooks/pre-commit` tracked-path entry (skipping any of the three
that's already there), stages the file, and fails loudly if the field
didn't actually encrypt. Re-run it any time — it's idempotent.

**Layer 1 (a new `.env` value):**

```
sops secrets/symphony.sops.yaml          # add the key, save
$EDITOR .env.example                     # add the same key, blank/dummy value
$EDITOR .env.j2                          # add the {{ jinja }} line
python3 scripts/render.py
```

## Rotating a secret

**Layer 1:**

```
sops secrets/symphony.sops.yaml          # edit the value, save
python3 scripts/render.py
docker compose up -d --force-recreate <service>
```

`GF_SECURITY_ADMIN_PASSWORD` is the exception — it only takes effect on a
*fresh* `grafana-data` volume. On an existing one, also run:

```
docker exec grafana grafana cli admin reset-admin-password '<value>'
curl -u admin:<value> http://localhost:3000/api/org      # expect 200
```

**In-place:** change it through the SignalK admin UI, then:

```
git add <file>
git commit
```

If the same secret is also mirrored in `secrets/symphony.sops.yaml` (like
`influx_token`, which Grafana also needs as an env var — a second
consumption path besides SignalK reading it off disk), update both.

**Grafana / InfluxDB users:** edit the password in `secrets/symphony.sops.yaml`,
then re-run the matching provisioner — both converge password + role on
every run, safe to re-run any time:

```
scripts/provision_grafana_users.sh
scripts/provision_influxdb.sh
```

**InfluxDB tokens** can't be reset in place — a token's value is only ever
shown once, at creation. To rotate:

```
# find the old authorization's id
curl -H "Authorization: Token $(sops --decrypt --extract '["influxdb_operator_token"]' secrets/symphony.sops.yaml)" \
  "http://localhost:8086/api/v2/authorizations?orgID=<org>"

curl -X DELETE -H "Authorization: Token <operator_token>" \
  "http://localhost:8086/api/v2/authorizations/<old_id>"

scripts/provision_influxdb.sh   # mints a fresh one now that the old one's gone
```

Then update `secrets/symphony.sops.yaml` and (for the SignalK token)
`signalk/plugin-config-data/signalk-to-influxdb2.json` with the new value.

See `ROTATION.md` for the specific credentials flagged in the Phase 0 survey.

## Recovering a lost age key

The age private key is the single point of failure — anyone provisioning a
new host, or recovering this one, needs it. It is never in git.

- **If you have a backup** (recommended: store the contents of
  `~/.config/sops/age/keys.txt` in a password manager or printed/offline
  copy at provisioning time): restore it to `~/.config/sops/age/keys.txt`
  on the new/recovered host and everything above works normally.
- **If the key is truly gone:** every sops-encrypted value (the whole
  `secrets/symphony.sops.yaml` store, and the encrypted fields inside the
  3 in-place files as they exist in git history) is unrecoverable from git
  alone. Recovery path: generate a fresh keypair (`age-keygen`), update the
  recipient in `.sops.yaml`, then re-populate secrets from their live
  source — `secrets/symphony.sops.yaml` values from whatever's currently
  live in the running containers/`.env`, and the 3 in-place files by just
  reading their current plaintext-on-disk copies (which are unaffected by
  losing the key — only the *git-stored* encrypted copies are unreadable)
  and `git add`-ing them again under the new key. Exception:
  `influxdb_operator_token` has no plaintext-on-disk copy anywhere (it's
  not consumed by any container, just used by provisioning scripts) — if
  it's gone, sign in to InfluxDB with `influxdb_init_username`/`_password`
  (a real login, not just a token) and mint a replacement via `POST
  /api/v2/authorizations`.
