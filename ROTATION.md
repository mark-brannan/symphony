# Credential rotation checklist

From the Phase 0 survey. History rewrite is intentionally not part of this
list (tabled per owner — see conversation).

| Credential | Where it was public | Status |
|---|---|---|
| Grafana admin "Cap" (login `captain`) password | `grafana/provisioning/users/users.yaml`, committed since `40e33c6`, live on the public GitHub repo as `"***REDACTED-EXPOSED-PASSWORD***"` | **Done as part of this change** — replaced with a new random 24-char password, stored in `secrets/symphony.sops.yaml` → `grafana_admin_password`. Only action needed from you: log into Grafana once and confirm the new password works (or run `sops secrets/symphony.sops.yaml` and pick your own instead). |
| Grafana viewer "John Smith" (login `johnsmith`) password | same file, same commit, `"***REDACTED-EXPOSED-PASSWORD***"` | **Done as part of this change** — replaced, stored as `grafana_viewer_password`. Same follow-up as above. |
| InfluxDB API token (used by `signalk-to-influxdb2` plugin) | Never in git history | No rotation required. Now tracked as an in-place encrypted field in `signalk/plugin-config-data/signalk-to-influxdb2.json`, and mirrored into `secrets/symphony.sops.yaml` → `influx_token` for Grafana's datasource. |
| SignalK `security.json` `secretKey` (JWT signing key) + captain's bcrypt password hash | Never in git history (only ever committed redacted/blank) | No rotation required. Now tracked in-place, encrypted. |
| `signalk-dsc` plugin `logbookToken` | Never in git history | No rotation required. Now tracked in-place, encrypted. |
| InfluxDB init username/password/org/bucket (`.env`) | Never committed (uncommitted working-tree edit only) | Treated as placeholders per your direction. Replaced with fresh values in `secrets/symphony.sops.yaml`; only matters if/when InfluxDB is re-initialized from an empty volume. |
