# Secrets & config runbook

Two mechanisms, one age key, one store of truth (`secrets/symphony.sops.yaml`):

- **Layer 1** — `docker-compose` `env_file: .env`. `.env` is gitignored,
  rendered by `scripts/render.py` from `secrets/symphony.sops.yaml`.
  `.env.example` documents every key.
- **In-place** — `signalk/security.json`, `signalk/plugin-config-data/signalk-to-influxdb2.json`,
  `signalk/plugin-config-data/signalk-dsc.json`, and
  `grafana/provisioning/users/users.yaml` are tracked in git *as themselves*.
  A git clean/smudge filter (`scripts/sops_filter.py`, wired by `.gitattributes`
  + `scripts/setup-git-filters.sh`) transparently encrypts just the secret
  leaf fields (`secretKey`, `password`, `token`, `logbookToken`) on commit
  and decrypts them back to plaintext on checkout. The working copy on disk
  is always plaintext — SignalK/Grafana read and rewrite it exactly as they
  do today, no behavior change. Only what git stores (and what's on GitHub)
  is encrypted.

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
5. `git checkout -- signalk/security.json signalk/plugin-config-data/signalk-to-influxdb2.json signalk/plugin-config-data/signalk-dsc.json grafana/provisioning/users/users.yaml`
   — re-checks-out those 4 files now that the smudge filter is live, which
   decrypts them to real plaintext on disk.
6. `python3 scripts/render.py` — decrypts `secrets/symphony.sops.yaml` and
   renders `.env`.
7. `docker compose up -d`.

If this is a genuinely first-ever boot (no prior `security.json` exists
anywhere, nothing to decrypt), skip step 5 and just let SignalK create its
own `security.json` through the setup wizard on first admin login as
normal — then `git add signalk/security.json` once, so it starts being
tracked (encrypted) from that point on.

## Adding a secret

- **Layer 1 (.env value):** `sops secrets/symphony.sops.yaml`, add the key,
  save. Add the same key (blank/dummy) to `.env.example` so it stays a
  complete contract. Add a line to `.env.j2`. Re-run `scripts/render.py`.
- **In-place (embedded in a config file SignalK/Grafana already owns):**
  add a rule to `.sops.yaml` (`path_regex` for the file, `encrypted_regex`
  matching the new field's key name), add the path to `.gitattributes`
  (`filter=sops`), add the path to the `sops_paths` list in
  `.githooks/pre-commit`. Then just edit/save the file normally — the next
  `git add` encrypts the new field along with the rest.

## Rotating a secret

- **Layer 1:** `sops secrets/symphony.sops.yaml`, edit the value, save,
  re-run `scripts/render.py`, restart the affected container(s)
  (`docker compose up -d --force-recreate <service>` or just `restart`).
- **In-place:** change it the normal way — through the SignalK/Grafana
  admin UI (or, for `users.yaml`, edit the file directly since Grafana only
  reads it, it doesn't own it) — then `git add <file>` to pick up and
  encrypt the new value. If you also keep a copy in
  `secrets/symphony.sops.yaml` (as we do for `influx_token`, since Grafana
  needs it as an env var too, a separate consumption path from SignalK
  reading it off disk), update both.
- See `ROTATION.md` for the specific credentials flagged in the Phase 0
  survey.

## Recovering a lost age key

The age private key is the single point of failure — anyone provisioning a
new host, or recovering this one, needs it. It is never in git.

- **If you have a backup** (recommended: store the contents of
  `~/.config/sops/age/keys.txt` in a password manager or printed/offline
  copy at provisioning time): restore it to `~/.config/sops/age/keys.txt`
  on the new/recovered host and everything above works normally.
- **If the key is truly gone:** every sops-encrypted value (the whole
  `secrets/symphony.sops.yaml` store, and the encrypted fields inside the
  4 in-place files as they exist in git history) is unrecoverable from git
  alone. Recovery path: generate a fresh keypair (`age-keygen`), update the
  recipient in `.sops.yaml`, then re-populate secrets from their live
  source — `secrets/symphony.sops.yaml` values from whatever's currently
  live in the running containers/`.env`, and the 4 in-place files by just
  reading their current plaintext-on-disk copies (which are unaffected by
  losing the key — only the *git-stored* encrypted copies are unreadable)
  and `git add`-ing them again under the new key.
