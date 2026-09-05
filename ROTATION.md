# Credential rotation checklist

| Credential | Was | Fix |
|---|---|---|
| Grafana built-in superadmin password | Live at the default `admin:admin` | Rotated — new value in `secrets/symphony.sops.yaml` → `grafana_superadmin_password`. Verified via `scripts/test_integration.sh`. |

## History audits

| Date | Scope | Result |
|---|---|---|
| 2026-08-07 | Every historical version of every secret-bearing file, plus a full-history gitleaks and trufflehog scan | Clean. Two files were once committed unencrypted (`signalk/security.json` at `7fe7d40`, `signalk-postgsail.json` at `eb04632`), both holding empty values at the time. No live credential has been in this repo's history, so no rotation or history rewrite was needed. |

Re-run with `scripts/scan_verified_secrets.sh` and the gitleaks command in
`RUNBOOK.md` → "A secret was committed in plaintext".

## 2026-08-14 — `influxdb_captain_token`

Rotated because the value was printed into a Claude session transcript by a
redaction bug (the filter matched `token` exactly and missed `influxToken`).

It mattered more than it first looked: this was *captain's Token*, all-access,
and the only working InfluxDB credential on the box — the sops
`influxdb_operator_token` and the repo's tracked `signalk-to-influxdb2.json`
token both return 401.

Four consumers: `signalk-barograph`, `signalk-to-influxdb2`,
`signalk-to-influxdb-v2-buffer`, and `.env` via `influxdb_captain_token`.

Order was mint, migrate, verify writes, then revoke — so nothing lost data
mid-rotation. Old authorization `0de6f590b7e23000` deleted; the old value now
returns 401. Also synced the repo's tracked `signalk-to-influxdb2.json`, which
had been carrying a third, already-dead token.

Still open: this remains one all-access token doing four jobs. Least privilege
wants scoped write-only tokens per consumer — see the InfluxDB reconciliation
item in `maintenance/priorities.md`.

## 2026-08-20 — `docker compose config` printed the full `.env` into a Claude transcript

Root cause: `docker compose config` (no flags) was run in a Claude Code session
to sanity-check a compose fix. This repo interpolates several secrets
directly in compose YAML (`${GF_SECURITY_ADMIN_PASSWORD}` etc., not only via
`env_file:`), and plain `docker compose config` resolves every `${VAR}` to its
live value by design — that's not a bug in the tool, it's what the command is
documented to do. The resolved output, including every interpolated secret in
cleartext, landed in the session transcript, which Anthropic retains
server-side; deleting local scrollback does not undo that.

No existing guard caught this. `secretguard.py`, `gitleaks_precommit.sh`, and
the rest of this repo's secret tooling all fire at **git-commit time**, on
staged content. This was a **shell-command-output-time** leak — a different
axis entirely, and nothing was watching it.

Fix landed same day: `.claude/hooks/block-secret-printing-compose-config.sh`,
wired into `PreToolUse` in `.claude/settings.json`. Blocks `docker compose
config` / `docker-compose config` unless `--no-interpolate` is present, which
answers the same "is the YAML well-formed" question without ever expanding a
`${VAR}`. Tested against the deny case, the `--no-interpolate` pass case, and
an unrelated `docker compose ps` pass case.

Seven credentials were exposed: `CLOUDFLARE_API_TOKEN`,
`GF_SECURITY_ADMIN_PASSWORD`, `INFLUX_TOKEN`, `TELEGRAF_INFLUX_TOKEN`,
`SIGNALK_OIDC_CLIENT_SECRET` / `GF_AUTH_GENERIC_OAUTH_CLIENT_SECRET` (same
sops field, `dex_symphony_client_secret`), `SIGNALK_TOKEN`,
`HEALTHCHECKS_API_KEY` / `HEALTHCHECKS_API_KEY_READ_ONLY`.

Rotated same day, self-hosted / API-scriptable ones (no third-party dashboard
required):

- **`dex_symphony_client_secret`** — fresh 32-byte hex value, sops + render.
  Dex (`compose-idp.yml`, profile `tls`) is not running on this host, so
  nothing was live to restart; whichever host actually runs the `tls`
  profile needs `scripts/render.py` re-run there too.
- **`influx_token`** (Grafana's read-only InfluxDB datasource token) — live
  when checked. Full mint → verify → migrate → revoke against the InfluxDB
  API: minted authorization `11339b01f5bf7000` with the same read-only
  symphony-bucket permissions as the old `11198cdaf8541000`, verified with an
  authenticated query (200), stored in sops, then revoked
  `11198cdaf8541000` (confirmed 401 afterward, new token confirmed still
  alive).
- **`influxdb_captain_token`** (`TELEGRAF_INFLUX_TOKEN`) — already 401 at
  time of check; no telegraf process exists on this host at all (no
  `telegraf.service`, no `/etc/telegraf`), so nothing was consuming it live.
  Minted a fresh read+write authorization (`11339b0245bf7000`) from the
  `signalk-to-influxdb2` auth's permission shape, verified with an actual
  write + readback (`204` write, marker found on query), stored in sops. Just
  retires the leaked string — no live migration needed since the old one was
  already dead.
- **`grafana_superadmin_password`** — new value generated and stored in
  sops + rendered. **Not yet verified live**: Grafana is currently
  crash-looping (`Datasource provisioning error: data source not found`),
  independent of this rotation — an uncommitted, unfinished migration from an
  earlier session (`compose-grafana.yml` switched from a bind-mounted
  `grafana/provisioning` to `build: ./grafana` with a new, untested
  `grafana/Dockerfile`). Not fixed here, out of scope for a credential
  rotation. Once Grafana starts again: `docker exec grafana grafana cli
  admin reset-admin-password '<value>'` (existing volume, per
  `RUNBOOK.md` → "Rotating a secret"), then confirm login.
- **`signalk_grafana_token`** — SignalK device-token flow, undocumented here
  before now (see below). Old device `signalk-grafana` deleted (confirmed:
  its token now returns 401 on `/signalk/v1/api/vessels/self`); new device
  `signalk-grafana-r2`, readwrite, minted and verified working end-to-end
  (200). `scripts/test_integration.sh` passes for every SignalK and InfluxDB
  check; the only remaining failures are Grafana's, tracing cleanly to the
  pre-existing crash-loop above.

  **Self-inflicted near-repeat, mid-rotation:** the SignalK access-request
  approval endpoint returns the newly-minted token nested at
  `accessRequest.token`, not `data.token` as the code path's own naming
  suggested. A debug step that `cat`'d the raw poll response to find the
  right key printed that token straight into this transcript — the same
  failure mode this whole rotation exists to fix, self-inflicted this time.
  That token (device `signalk-grafana-r20260820`) was deleted within the same
  script run, confirmed 401. No external exposure — it never left this
  transcript — but worth recording plainly rather than quietly redoing it.
  Lesson generalized: **never `cat`/print a file that might hold a freshly
  minted secret while debugging its shape** — parse it with a script and
  print only booleans/lengths/status codes, every time, even mid-debugging.

  Also worth recording for whoever touches this next: SignalK's device JWTs
  encode only `{device: clientId}`, no per-token identifier (no `jti`, no
  issued-at check tied to the current device entry). Re-approving the *same*
  clientId does **not** invalidate a previously-issued token for that
  clientId — both remain valid until the clientId's device entry is deleted
  outright. True rotation requires a new clientId (or a full secretKey
  rotation, which invalidates every device and login session — much bigger
  blast radius, not appropriate for a single-credential rotation).

**Not yet done — needs a human on the provider's dashboard, handed to a
separate session:**

- `cloudflare_api_token` — Cloudflare dashboard (My Profile → API Tokens):
  create a replacement with the same scopes, revoke the old one.
- `healthchecks_api_key` / `healthchecks_api_key_read_only` — healthchecks.io
  (Project Settings → API keys): regenerate both.

Both must be entered directly into `sops secrets/symphony.sops.yaml` by
whoever generates them — never pasted into a Claude Code chat, which is the
exact mistake this whole incident is about.
