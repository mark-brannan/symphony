# SSO setup — owner's action checklist

Working checklist for standing up the GitHub/Google login. The durable
procedure lives in [RUNBOOK.md](RUNBOOK.md) → "SSO login (GitHub /
Google)"; this file is only what's left for the owner to do, in
dependency order. Delete it when everything's checked.

The model: any GitHub or Google account can sign in and view SignalK
(readonly); the owner's email also gets Grafana Admin; writes keep using
the local `captain` / Grafana-superadmin passwords, which are also the
no-internet fallback. No GitHub org or teams involved.

Values written `<like-this>` get decided along the way. Real values go in
`secrets/symphony.sops.yaml` (`sops secrets/symphony.sops.yaml` to edit),
never in this file.

Already done and waiting in the repo: all compose/Caddy/Dex/SignalK/
Grafana config, `dex_symphony_client_secret` in sops, and a locally
verified login flow. The remaining sops placeholders are exactly the
values collected below.

## A. Decide the domain (everything below bakes it into URLs)

- [x] Pick the boat's domain: `symphony.dark-star-llc.com` (the boat is
      a sub-zone; apex and top-level names stay free for the LLC).
- [x] Put it in sops as `boat_domain`.

## B. OAuth apps (needs only the domain name, not working DNS)

GitHub — personal account:

- [ ] <https://github.com/settings/developers> → OAuth Apps → New OAuth
      App:
      - Application name: anything (e.g. "Symphony boat systems")
      - Homepage URL: `https://auth.<domain>`
      - Authorization callback URL: `https://auth.<domain>/dex/callback`
- [ ] Copy the client ID; "Generate a new client secret" and copy it.
- [ ] Into sops: `github_oauth_client_id`, `github_oauth_client_secret`.

Google:

- [ ] <https://console.cloud.google.com> → create a project (any name).
- [ ] APIs & Services → OAuth consent screen: **External**, app name +
      support email → then **Publish app** (production). Not Testing:
      testing mode caps sign-ins to a 100-address allowlist, and the
      open readonly door is intended. The basic scopes used need no
      Google review.
- [ ] Credentials → Create credentials → OAuth client ID → **Web
      application** → one redirect URI:
      `https://auth.<domain>/dex/callback`
- [ ] Into sops: `google_oauth_client_id`, `google_oauth_client_secret`.

## C. Cloudflare and boat network (needs router access / being aboard)

- [ ] Give the server host a fixed LAN IP: DHCP reservation in the boat
      router. (No Tailscale involvement — the names must work for any
      device on the boat wifi, tailnet member or not.)
- [x] Cloudflare DNS, all grey cloud (DNS only, not proxied): one **A**
      record `<domain>` → the boat IP, and `signalk.<domain>`,
      `grafana.<domain>`, `auth.<domain>` as CNAMEs to it.
- [ ] Replace the A record's placeholder content (`192.0.2.1`) with the
      real DHCP-reserved IP once it exists.
- [x] Cloudflare API token: My Profile → API Tokens → Create Token →
      "Edit zone DNS" template → limit to this zone. Into sops:
      `cloudflare_api_token`.
- [ ] Router local DNS overrides for all four names → the same IP
      (offshore there is no public DNS). Check from the boat LAN with
      WAN unplugged: `nslookup signalk.<domain>` returns the LAN IP.

## D. Ship it

- [ ] Review and commit the working-tree changes (stage by name, never
      `git add -A` in this repo).
- [ ] On the boat, dockside (first run builds the caddy image and issues
      certificates, so it needs internet):

      ```
      git pull
      python3 scripts/render.py
      docker compose --profile tls up -d --build
      ```

- [ ] Run the verify steps in RUNBOOK.md → "SSO login" step 4: two
      curls, then browser logins — any SSO account → SignalK `readonly`;
      owner's login at Grafana → Admin, anyone else refused; `captain`
      password still admin.

Notes:

- `dex_symphony_client_secret` in sops is pre-generated and internal;
  leave it.
- Grafana roles are a hand-managed email list in `.env.j2`
  (`GF_AUTH_GENERIC_OAUTH_ROLE_ATTRIBUTE_PATH`) — extend it when a crew
  member needs Editor.
- SSO logins can't get SignalK write access on the stock server (it only
  maps IdP group claims, which these providers don't send). If that ever
  chafes, the fix is a small upstream patch adding email lists — until
  then, `captain` is the write path.
