# Credential rotation checklist

| Credential | Was | Fix |
|---|---|---|
| Grafana built-in superadmin password | Live at the default `admin:admin` | Rotated — new value in `secrets/symphony.sops.yaml` → `grafana_superadmin_password`. Verified via `scripts/test_integration.sh`. |

## History audits

| Date | Scope | Result |
|---|---|---|
| 2026-08-07 | Every historical version of every secret-bearing file, plus a full-history gitleaks and trufflehog scan | Clean. Two files were once committed unencrypted (`signalk/security.json` at `7fe7d40`, `signalk-postgsail.json` at `eb04632`), both holding empty values at the time. No live credential has been in this repo's history, so no rotation or history rewrite was needed. |

Re-run with `scripts/scan_verified_secrets.sh` and the gitleaks command in
`RUNBOOK.md` → "Scanning for leaks by hand".

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
