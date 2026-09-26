# SSO

Dex fronts GitHub and Google. Any account gets SignalK readonly; the owner's
email gets SignalK admin and Grafana Admin. The offline fallback is in
[RUNBOOK.md](../RUNBOOK.md#no-way-to-log-in).

## Deploying Dex

On the boat. Name `dex`: with no service named, compose also starts the
`caddy` container, which fights the native Caddy for port 443.

```bash
git pull
python3 scripts/render.py
docker compose --profile tls up -d dex
sudo systemctl restart caddy
```

Fully containerized host: `docker compose --profile tls up -d --build`,
dockside. Restart grafana and signalk too if their `*_OAUTH_*` / `*_OIDC_*`
values changed.

*Verify:*

```bash
curl -s https://signalk.symphony.dark-star-llc.com/signalk/v1/auth/oidc/status               # "enabled":true, issuer .../dex
curl -s https://auth.symphony.dark-star-llc.com/dex/.well-known/openid-configuration | head -3
```

In a browser: the owner shows `admin` in SignalK Security → Users, any other
account `readonly`; Grafana admits the owner and refuses others; `captain`
still works. Owner as `readonly` means `SIGNALK_OIDC_GROUPS_ATTRIBUTE=email`
never reached the server, silently.

## First-time setup

**1. DNS (Cloudflare).** A record `symphony.dark-star-llc.com` → the host's
tailnet IP; CNAMEs `signalk.`, `grafana.`, `auth.` → it, all DNS-only (grey
cloud). API token from the "Edit zone DNS" template, scoped to this zone. On
the boat router add `address=/symphony.dark-star-llc.com/<LAN IP>`. A rebuilt
host gets a new tailnet IP and this record goes stale: off-boat dead, on-boat
fine.

*Verify:* from the boat LAN with the WAN unplugged, `nslookup signalk.symphony.dark-star-llc.com` returns the LAN IP.

**2. OAuth apps.** GitHub: personal account → OAuth Apps → New, homepage
`https://auth.symphony.dark-star-llc.com`, callback
`https://auth.symphony.dark-star-llc.com/dex/callback`. Google: a project,
consent screen External and **published**, Web application credential with the
same callback.

**3. Secrets.** Fill `boat_domain`, `github_oauth_client_id`,
`github_oauth_client_secret`, `google_oauth_client_id`,
`google_oauth_client_secret`, `cloudflare_api_token` and `owner_email`. Leave
`dex_symphony_client_secret` as it is. Then deploy, above.

```bash
sops secrets/symphony.sops.yaml
python3 scripts/render.py
```

## Access grants

Who gets what is decided from `.env.j2` at every login, not from the user lists
inside SignalK or Grafana: a promotion made in the SignalK UI is undone at the
next login.

- Grafana: append `|| email=='crew@example.com' && 'Editor'` to
  `GF_AUTH_GENERIC_OAUTH_ROLE_ATTRIBUTE_PATH`.
- SignalK: add the address to `SIGNALK_OIDC_ADMIN_GROUPS`, or to
  `SIGNALK_OIDC_READWRITE_GROUPS` (add that variable if it isn't there).
  Comma-separated, case-sensitive.

```bash
python3 scripts/render.py
docker compose up -d --force-recreate grafana signalk
```

To cut someone off entirely, delete their SignalK user (Security → Users;
sessions never expire otherwise) and their Grafana user.
