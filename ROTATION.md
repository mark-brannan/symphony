# Credential rotation checklist

| Credential | Was | Fix |
|---|---|---|
| Grafana built-in superadmin password | Live at the default `admin:admin` | Rotated — new value in `secrets/symphony.sops.yaml` → `grafana_superadmin_password`. Verified via `scripts/test_integration.sh`. |
