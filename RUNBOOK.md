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

## Remote SSH access

rpi-connect gives browser-based screen/shell access but has been
unreliable, and its shell doesn't tunnel plain `ssh` — no good for things
like a Claude Code session. Tailscale is the primary path: normal `ssh`
over a WireGuard mesh, no port forwarding, no public exposure.

**One-time setup on a new host:**

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --ssh --hostname=<host>
```

Follow the printed login URL to join the tailnet.

*Verify:* `tailscale status` lists the host; `ssh pi@<hostname>` from
another device on the tailnet connects.

Symphony's Pi is already on the tailnet as `symphony-pi`.

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

## Installing host files

`host/` holds files that live on the machine rather than in a container —
scripts under `/usr/local/sbin`, and the root cron entries that call them.
On the host:

```bash
cd ~/symphony && git pull
sudo host/install.sh
```

It's idempotent, and it prints what it installed plus the resulting root
crontab. Re-run it after any change under `host/`; it rewrites only the cron
entries pointing at paths it installs and leaves everything else in that
crontab alone.

To add a file, drop it in `host/` and add a line to `INSTALL` (and `CRON` if
it needs scheduling) at the top of `host/install.sh`.

Anything landing under `/etc/systemd/` triggers a `daemon-reexec`, because
manager settings like the watchdog don't apply on a plain `daemon-reload`.

Currently installed:

`systemd-watchdog.conf` turns on the Pi's BCM2835 hardware watchdog with a
15-second timeout, so a hang that stops answering ping and SSH resets the
board instead of waiting for someone aboard to pull power. Confirm it took:

```bash
journalctl -b | grep -i "hardware watchdog"
systemctl show -p RuntimeWatchdogUSec
```

Expect `Watchdog running with a hardware timeout of 15s` and
`RuntimeWatchdogUSec=15s`. It won't catch a wedged service while systemd
keeps running — that needs a separate check.

`nightly-reboot` is still installed, but its line in root's crontab is
commented out. It rebooted the Pi at 04:00 **unless** an `npm` or `node-gyp`
process was running. Keep that guard if you ever turn it back on, and don't
call `shutdown` from cron directly — a reboot landing on an `npm install` in
`~/.signalk` truncates the plugin tree, and npm won't repair it afterward
because it sees the half-written directories and considers those packages
installed. On a night it runs, check which way it went with:

```bash
journalctl -t nightly-reboot --since yesterday
```

## Don't autostart a browser on the boat Pi

Chromium started from `~/.config/autostart` renders with GPU acceleration
whether or not an HDMI display is connected, and on this Pi that wedges the
v3d driver. `Resetting GPU for hang` then repeats several times a minute
until a kworker blocks permanently in `v3d_gpu_reset_for_timeout`, systemd
stops petting the watchdog, and the board hard-resets. Those blocked kworkers
also hold the load average up by one apiece, so load stops meaning anything;
nothing but a reboot clears them.

```bash
journalctl -b -k | grep -c "Resetting GPU for hang"    # want 0
ps -eo pid,stat,comm | awk '$2 ~ /D/'                  # want no kworker
```

If the count is climbing, find what's driving the GPU and stop it — the
desktop by itself doesn't touch v3d. The Freeboard entry now sits in
`~/.config/autostart-disabled/`; its Desktop launcher still works when
someone is actually at a screen.

## Reaching the boat over Tailscale

Setup is under [Remote SSH access](#remote-ssh-access); this covers using it
and the ways it fails. The boat is node `symphony-pi`, tailnet address
100.113.172.64.

Only devices on the tailnet can reach it — which includes the Windows side
of a WSL machine *not* being on it, because WSL runs its own tailscaled and
doesn't share it with the host. If a browser can't load the admin UI,
install Tailscale on *that* machine before debugging anything else.

```bash
tailscale status                 # symphony-pi listed and not "offline"
curl -s http://symphony-pi:3000/signalk    # server version + endpoints
```

SignalK admin UI: `http://symphony-pi:3000/admin/`.

### SSH users and the periodic check

Tailscale SSH handles auth, so no key setup is needed, but the ACL names
which local users you may become — `pi` works, other names are rejected with
"tailnet policy does not permit you to SSH as user X". Change that in the
[access controls](https://login.tailscale.com/admin/acls) if you need
another.

The ACL also sets a check period. When it lapses, ssh stops at
`# Tailscale SSH requires an additional check.` and prints a
`login.tailscale.com/a/...` URL — open it, approve, then re-run ssh. The URL
is single-use, so don't bother saving it. Under `-o BatchMode=yes` or any
non-interactive wrapper this just looks like a hang; that message is the
tell.

### A page hangs but the host is reachable — MTU

Symptom: the browser spins forever on `https://signalk.<domain>/`, ssh and
ping to the same host are fine, and a port check succeeds:

```powershell
Test-NetConnection 100.113.172.64 -Port 443 -InformationLevel Quiet   # True
```

That combination means small packets get through and large ones don't. TCP
completes its handshake, then the TLS handshake's full-size packets are
dropped in silence. It shows up when a device takes a *direct* path to the
boat over an uplink whose real MTU is below Tailscale's assumed 1280 —
cellular and Starlink both do this. Relayed connections don't hit it, so one
machine can work while another fails against the same server.

Confirm by finding where ping stops making it through with
don't-fragment set:

```powershell
foreach ($s in 1100,1200,1272,1400) { ping -n 1 -f -l $s 100.113.172.64 }
```

Fix on Windows — find the adapter's `ifIndex`, then lower its MTU
(needs an elevated shell):

```powershell
Get-NetIPInterface -AddressFamily IPv4 | Where-Object InterfaceAlias -like '*Tailscale*'
netsh interface ipv4 set subinterface <ifIndex> mtu=1180 store=persistent
```

On macOS or Linux, set it on the Tailscale interface instead:

```bash
sudo ifconfig utun<N> mtu 1180        # macOS
sudo ip link set tailscale0 mtu 1180  # Linux
```

The Windows form survives reboots; the macOS and Linux ones don't survive a
`tailscaled` restart. It's per-machine either way and doesn't propagate, so
each new device can need it again.

## The resident Claude session on the boat Pi

The Pi keeps a Claude Code session running in tmux with Remote Control on, so
work in progress isn't tied to an SSH connection staying up. It starts at
boot, with nobody logged in.

Attach on the box, and detach without stopping anything:

```bash
tmux attach -t claude       # attach
                            # Ctrl-b then d to detach
```

Detaching, closing the terminal, and dropping the SSH connection all leave the
session running. Remotely, open the `https://claude.ai/code/session_…` URL the
session prints at startup; the footer shows `/rc active` when Remote Control is
live.

If it isn't running:

```bash
systemctl --user status claude-resident.service
systemctl --user start claude-resident.service
```

That's a `--user` unit, so `sudo systemctl` won't find it — run it as `pi`.
What makes it survive a reboot is lingering (`loginctl show-user pi -p Linger`
→ `Linger=yes`); without that, a user unit stops when the last login session
ends. `host/install.sh` sets it.

The wrapper starts the pane with a trailing shell, so if Claude exits the tmux
session stays up and you can restart it in place instead of losing the window.

## Router config backup

The boat router holds the local DNS override that makes the hostnames
resolve on the boat. A factory reset takes it, and on-boat access with it.
An encrypted copy of the router's full UCI config lives in
`secrets/router-config.sops.yaml`.

Refresh it after any router change (the pi's key is authorized on the
router; run this from anywhere on the tailnet):

```bash
ssh pi@symphony-pi 'ssh root@192.168.8.1 "uci export"' > /tmp/uci.txt
```

then re-wrap it as the `uci_export` key of that YAML file and
`sops --encrypt --in-place` it.

To read or restore:

```bash
sops --decrypt secrets/router-config.sops.yaml
```

Feed the `uci_export` contents back through `uci import` on the router,
then `reload_config`. Restoring overwrites WiFi and WAN settings too —
this is a whole-config restore, not a DNS-only one.

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

1. In Cloudflare DNS, add one **A** record and three CNAMEs, all DNS
   only / grey cloud (not proxied):
   - `<domain>` → the host's **tailnet** IP, e.g. `100.113.172.64`
   - `signalk.<domain>`, `grafana.<domain>`, `auth.<domain>` → CNAME to
     `<domain>`

   Public DNS answers for off-boat devices, the boat router answers for
   on-boat ones (step 3), and the same URL works in both places. Give
   the host a fixed LAN IP too (DHCP reservation in the boat router) —
   the router override needs it. A public name resolving to a private
   or CGNAT address is fine; nothing here is reachable from the
   internet.

   The tailnet IP is stable, but it belongs to the *machine*, not the
   hostname. Rebuild the host's SD card, or delete and re-add it in the
   Tailscale console, and it joins as a new machine with a different
   100.x — this record then points at nothing. Symptom: off-boat access
   dies, on-boat keeps working. You can't CNAME to the MagicDNS
   `.ts.net` name instead; it doesn't resolve off the tailnet.
2. Create the certificate-issuance token: Cloudflare → My Profile → API
   Tokens → Create Token → "Edit zone DNS" template → limit it to this
   one zone.
3. On the **boat router**, add a local DNS override sending the whole
   subdomain to the host's LAN IP (dnsmasq:
   `address=/<domain>/192.168.1.50`, or the router UI's "local DNS
   records"). One wildcard entry covers the apex and every subdomain,
   so adding a service later needs no router change.

   Don't skip this. It is what makes the hostname work for anything on
   the boat that isn't on the tailnet — a guest's phone — and offshore
   there is no public DNS at all, so without it even already-logged-in
   devices can't resolve the names.

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

**On a host without Docker, the third command does nothing.** Caddy, Dex
and Telegraf run as systemd units there instead; restart those directly:

```bash
python3 scripts/render.py
sudo systemctl restart caddy dex telegraf
```

Restart Grafana and SignalK too if you changed anything they read —
`GF_AUTH_GENERIC_OAUTH_*` or `SIGNALK_OIDC_*`. They pick up `.env` through
an `EnvironmentFile=` drop-in, so a re-render alone doesn't reach a running
process.

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
#   REDIRECT_URI=http://localhost:3000/signalk/v1/auth/oidc/callback
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

## Email pseudonyms in security.json

Email addresses in `signalk/security.json` become `pid.*` tokens on the way
into git and are restored on the way out. The working tree keeps the real
addresses, so SignalK is unaffected. GitHub logins arrive as a handle
(`mark-brannan`) and stay legible.

### Resolve a token

```
python3 scripts/pseudonymize.py resolve pid.rj232vx
```

Takes the short form or the full `pid.rj232vx+invalid@gmail.com`. Needs an
age identity, which is the point — the token is publishable, the address
behind it isn't.

### Let someone else resolve tokens

Give them the manifest key, not your working key. Copy the block labelled
`age1n566m5z8e5nmhqkhxqmpd9jr2678t6l6wrzvcxrnckdjn9r2adjs55jgp9` out of
`~/.config/sops/age/keys.txt` into theirs. Check what it opens first:

```bash
scripts/rotate_age_key.sh verify age1n566m5z8e5nmhqkhxqmpd9jr2678t6l6wrzvcxrnckdjn9r2adjs55jgp9
```

It should report one file — `secrets/pseudonyms.sops.yaml` — and say the key
is scoped. If it reports more, stop: that key now opens the boat's live
credentials too.

### When someone new logs in

SignalK writes the new address into the file itself, and the clean filter
picks it up at commit time:

```
pseudonymize: new address p*****d@yahoo.com -> pid.t8tym9m+invalid@yahoo.com
pseudonymize: the map changed -- stage secrets/pseudonyms.sops.yaml ...
```

Stage `secrets/pseudonyms.sops.yaml` in that same commit. Without it the
token lands in git with nothing that resolves it, for you and everyone else.

### If checkout warns the map is unavailable

```
pseudonymize: WARNING - cannot decrypt secrets/pseudonyms.sops.yaml
```

Don't start SignalK against that file. The tokens stay in place, SignalK
reads them as real addresses, and rewrites them back as the users' identity.
Get an age identity working, then re-run smudge:

```
git checkout -- signalk/security.json
```

### Find when someone had access

```
git log -S 'pid.rj232vx' -- signalk/security.json
```

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
curl -u admin:<value> http://localhost:3001/api/org      # expect 200
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

### Keys scoped to one file

Most rules in `.sops.yaml` share one recipient list; a few spell out their
own so a key can open a single file. `add` and `retire` reach both kinds, so
a rotation needs no extra steps — but read what `verify` says:

```
OK: age1n566... alone decrypts all 1 file(s) it is a recipient of.
Note: this key is scoped -- 14 other configured file(s) are deliberately
out of its reach.
```

That's a pass, not a lockout. `verify` on a scoped key tells you nothing
about whether the *rotation* is complete — run it against the new global key
for that.

`scripts/rotate_age_key.sh status` lists which keys are scoped and to what.

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

### Checking a key that isn't on this box

`status` lists recipients whose private half is absent — an escrow key
should be one of them:

```
Recipients whose private half is NOT on this box:
  age1a8je25wsr5x7vqznc7zfxjw9jswrwpallp5aphrtxsrcu7ws7shsvdez3q
```

That says the key is *expected*, not that the copy you're keeping elsewhere
still works. Nothing on this machine can tell you that. Check it directly,
at least after any move and once a year:

```bash
# 1. Retrieve it into a scratch file. NOT into ~/.config/sops/age/keys.txt --
#    putting it back defeats the point of keeping it off this box.
install -m 600 /dev/null /tmp/check.key
#    ... paste the key in ...

# 2. Is it the key you think? This catches a truncated or wrong paste,
#    which is the realistic failure and is otherwise invisible.
age-keygen -y /tmp/check.key       # must print the public key from .sops.yaml

# 3. Does it actually open the repo?
SOPS_AGE_KEY_FILE=/tmp/check.key \
  scripts/rotate_age_key.sh verify <public-key>

# 4. Destroy the scratch copy.
shred -u /tmp/check.key
```

`SOPS_AGE_KEY_FILE` makes `verify` read that file instead of the keyring, so
the key is tested without ever being installed here. Expect
`decrypts all 15 file(s)` for an escrow key. Fewer means it's scoped to some
rules only and can't stand in for the working key — fine for the manifest
key, wrong for escrow.

A failure at step 2 is recoverable while the key is still on this box or
another host. A failure at step 3 after the last other copy is gone is not.
Which is why this gets checked on a schedule rather than when you need it.

## Removing a secret

To stop tracking a file's secret (plugin uninstalled, field no longer used):

1. Delete its `path_regex` block from `.sops.yaml`.
2. Delete its `filter=sops` line from `.gitattributes`.
3. `python3 scripts/sops_paths.py check` — confirms the two still agree.
4. If the file itself is going away: `git rm --cached <file>` and add it to
   `.gitignore`.

Removing the rules does **not** un-publish anything already committed. If
the secret was ever live in a public commit, rotate it — see below.

## When the boat's hostnames stop resolving

All three names fail on the boat wifi and browsers say the site can't be
found — a DNS failure, not a certificate or connection error. The services
themselves are still up: `http://192.168.8.240:3000` loads by IP.

Confirm which link is down:

```bash
ping -c2 192.168.8.240   # boat computer, wired
ping -c2 192.168.8.241   # same host, wifi
```

Wired dead and wifi alive points at the cable, the switch port, or the Pi's
`eth0`. The router's wildcard resolves every name to the wired address only,
so all three go down with that one interface even though the host is still
reachable.

Repoint the wildcard at the wifi reservation:

```bash
ssh root@192.168.8.1
uci set dhcp.@dnsmasq[0].address='/symphony.dark-star-llc.com/192.168.8.241'
uci commit dhcp && /etc/init.d/dnsmasq restart
```

From a laptop on the boat wifi, `dig +short signalk.symphony.dark-star-llc.com`
should return `192.168.8.241`. If it still returns the old address, flush the
client's cache — on macOS, `sudo dscacheutil -flushcache; sudo killall -HUP
mDNSResponder`.

Set it back to `192.168.8.240` once the cable is fixed. Wifi is the slower
path and drops when the router reboots.

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

## Stopping SignalK on the boat Pi

`systemctl stop signalk` does not keep it down. A `signalk.socket` unit
re-activates the service on the first connection to port 3000, which in
practice means seconds — the admin UI polls. Stop the socket first:

```bash
sudo systemctl stop signalk.socket
sudo systemctl stop signalk.service
ss -lntp | grep :3000      # expect no output
```

Start them in the reverse order. If the service was killed while running it
shows `failed`; `sudo systemctl reset-failed signalk.service` clears that
before starting.

Do this before any `npm install` in `~/.signalk`. Otherwise the running server
is reading the tree while npm rewrites it, and anything that restarts the
service mid-install brings it up against a half-written plugin directory.

## When SignalK errors about missing packages on the boat Pi

The Pi is a baremetal OpenPlotter install, so the Docker reinstall above
doesn't apply to it. Read this before running `npm install` there — the
obvious fix feeds the problem.

A truncated plugin tree makes SignalK log missing-module errors. `npm install`
in `~/.signalk` looks like the answer, but it wants around 1.7 GB on a box
with 3.7 GB of RAM and 200 MB of swap. Memory runs out, the Pi climbs to ~90%
iowait, and SSH stops answering — a banner can take over a minute. Killing or
rebooting out of that truncates the tree further, so the next start logs more
missing modules than the last one did.

Never run `npm install` over a broken tree. npm treats a half-written package
directory as installed and skips it, so a second run repairs nothing. Move the
tree aside first:

```bash
sudo systemctl stop signalk.socket     # socket first, see above
sudo systemctl stop signalk.service
mv ~/.signalk/node_modules ~/.signalk/.node_modules_old
cd ~/.signalk
npm install --ignore-scripts --no-audit --no-fund   # phase 1: lay down the tree
npm rebuild                                          # phase 2: build the natives
```

Install in those two phases, not as a plain `npm install`. A single
`npm install` deletes the entire tree it just wrote if any one package's
build script fails, and `better-sqlite3@7.6.2` always fails here — see below.
That costs the whole install and leaves `~/.signalk` with no `node_modules`
at all. `npm rebuild` reports the same failure and leaves everything else
built, so the tree survives it.

`npm rebuild` exits non-zero while still having done its job. Judge it by
what it produced, not its exit code:

```bash
find ~/.signalk/node_modules -name '*.node' | wc -l   # expect dozens, not 0
ls -d ~/.signalk/node_modules/@mapbox/node-pre-gyp    # must exist
```

`@mapbox/node-pre-gyp` is what native modules build through. If it is absent,
every native build aborts on it and no `.node` is produced anywhere.

Check `free -m` before starting — you want more than 2 GB available. If you
don't have it, `sudo systemctl stop grafana-server influxdb` frees a few
hundred MB, and `sudo systemctl stop raspotify cups cups-browsed ModemManager`
a couple hundred more. Should a previous install have been interrupted, add
`npm cache clean --force`; it can leave partial tarballs behind, and on a full
disk it also frees a couple of GB.

Watch it with `vmstat 5` rather than the load average. Load average won't tell
a stalled install from a GPU hang, where blocked kworkers inflate it just as
much and only a reboot clears them.

Read the swap columns, not `wa` alone. Phase 1 drives `wa` to 60-80 with `b`
in double digits purely from SD-card writes, and that finishes fine. What
means it won't finish is `si`/`so` staying non-zero with `available` falling
toward zero — that is swapping instead of working. Free more memory then;
`available` recovering is the confirmation. Don't kill the install to fix it.

Start again in reverse order. A service killed while running comes back
`failed`, so clear it with `sudo systemctl reset-failed signalk.service`
first.

## Never use OpenPlotter's "Reinstall" for Signal K

Settings → Signal K → **Update** is safe. **Reinstall** runs `rm -rf` on
`~/.signalk` first — every plugin's configuration, `security.json`,
`settings.json`, all of it. That is deliberate on OpenPlotter's part: it
forces the first-run branch that rewrites the launcher script, which is
skipped whenever `settings.json` already exists. There is no prompt and
nothing is backed up.

If you need that branch to run — say, to regenerate the launcher after moving
Node — back up `~/.signalk` first and put the config files back afterward.

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
