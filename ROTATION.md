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
