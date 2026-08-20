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

## Where things are

**Getting in**
- [Remote SSH access](#remote-ssh-access)
- [Reaching the boat over Tailscale](#reaching-the-boat-over-tailscale)
- [The resident Claude session on the boat Pi](#the-resident-claude-session-on-the-boat-pi)

**Building and maintaining the host**
- [Bringing up a host](#bringing-up-a-host)
- [Installing host files](#installing-host-files)
- [Turning on the off-boat heartbeat](#turning-on-the-off-boat-heartbeat)
- [Don't autostart a browser on the boat Pi](#dont-autostart-a-browser-on-the-boat-pi)
- [Upgrading the scanners](#upgrading-the-scanners)

**Secrets and encryption**
- [Adding a secret](#adding-a-secret)
- [Rotating a secret](#rotating-a-secret)
- [Rotating the age key](#rotating-the-age-key)
- [Removing a secret](#removing-a-secret)
- [Email pseudonyms in security.json](#email-pseudonyms-in-securityjson)
- [Per-machine config values](#per-machine-config-values)
- [Router config backup](#router-config-backup)
- [Scanning for leaks by hand](#scanning-for-leaks-by-hand)

**Identity and access**
- [SSO login (GitHub / Google)](#sso-login-github--google)

**Running SignalK**
- [Stopping SignalK on the boat Pi](#stopping-signalk-on-the-boat-pi)
- [SignalK's NMEA 2000 input](#signalks-nmea-2000-input)
- [Setting up a BLE sensor](#setting-up-a-ble-sensor-in-bt-sensors-plugin-sk)

**Troubleshooting**
- [Hostnames stop resolving](#when-the-boats-hostnames-stop-resolving)
- [A plugin isn't in the config UI](#when-a-plugin-isnt-in-the-config-ui)
- [SignalK errors about missing packages](#when-signalk-errors-about-missing-packages-on-the-boat-pi)
- [BLE sensors silent after a reboot](#ble-sensors-go-silent-after-a-reboot)
- [A BLE sensor connects but delivers nothing](#a-ble-sensor-connects-but-never-delivers-data)
- [A plugin fork keeps reverting](#a-local-plugin-fork-keeps-reverting-to-the-registry-build)
- [A hook blocks your commit](#when-a-hook-blocks-your-commit)
- [Never use OpenPlotter's "Reinstall"](#never-use-openplotters-reinstall-for-signal-k)

**Incidents & recovery**
- [A secret was committed in plaintext](#a-secret-was-committed-in-plaintext)
- [Recovering a lost age key](#recovering-a-lost-age-key)

---

## Two deployments, one runbook

The compose files are the intended deployment. **The boat Pi does not match
them** — SignalK, InfluxDB, Grafana, Caddy and Dex run there as systemd units
(why, in [reference/software_stack.md](reference/software_stack.md)). Commands
below are written for compose. On the boat, translate:

| Compose | Boat Pi |
|---|---|
| `docker compose up -d <svc>` | `sudo systemctl start <svc>` |
| `docker compose restart <svc>`, `--force-recreate` | `sudo systemctl restart <svc>` |
| `docker compose stop <svc>` | `sudo systemctl stop <svc>` |
| `docker exec grafana grafana cli …` | `sudo grafana cli …` |
| service `grafana` | unit `grafana-server` |

Ports are the same either way — SignalK 3000, Grafana 3001, InfluxDB 8086 — so
every `curl http://localhost:…` in this file works unchanged on both.

Both deployments read the same rendered `.env`, but only containers get it
loaded automatically. In a shell, source it first:

```bash
cd ~/symphony && set -a && . ./.env && set +a
```

---

## Remote SSH access

Connect to the boat:

```bash
ssh pi@symphony-pi
```

Attach to the resident Claude session once you're on:

```bash
tmux attach -t claude
```

`Ctrl-b` then `d` detaches and leaves it running — see "The resident Claude
session on the boat Pi".

Tailscale carries this: plain `ssh` over a WireGuard mesh, no port forwarding,
no public exposure. rpi-connect's browser shell can't tunnel `ssh`, so it's no
use for a Claude Code session.

**Adding a host to the tailnet** (substitute its name for `symphony-pi`):

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --ssh --hostname=symphony-pi
```

Follow the printed login URL. *Verify:* `tailscale status` lists it, and
`ssh pi@symphony-pi` connects from another device on the tailnet.

---

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

### A cloud Claude session can't reach symphony-pi

Cloud sessions join the tailnet automatically at startup. If one can't
reach `symphony-pi`:

1. Check session startup output for a `tailscale-join:` line on stderr —
   the hook reports a notice there for every failure (missing auth key,
   join timeout, etc.), it doesn't fail silently.
2. Confirm the join's actual state:
   ```bash
   tailscale status --socket="$HOME/.tailscale-cloud.sock"   # joined? authenticated?
   cat "${TMPDIR:-/tmp}"/tailscaled.*.log                     # daemon's own log
   ```
3. If the notice says `TAILSCALE_AUTHKEY not set`, set or refresh that
   env var on the cloud environment — a reusable, ephemeral,
   `tag:cloud-ephemeral` key from the
   [tailnet admin console](https://login.tailscale.com/admin/machines).
4. If the node joined but ssh is refused, it's the policy, not the join —
   the tailnet needs an `ssh` rule with `tag:cloud-ephemeral` as `src`. See
   § SSH users and the periodic check.

Local/terminal sessions don't need this — they already have tailscale via
the host machine.

### SSH users and the periodic check

Tailscale SSH handles auth, so no key setup is needed, but the tailnet policy
decides both which nodes may connect and which local users you may become.
Two different refusals, two different causes:

- `does not permit you to SSH to this node` — no `ssh` rule matches at all.
- `does not permit you to SSH as user X` — a rule matched, but its `users`
  list doesn't include that account.

Every node except the phone is tagged, and **`autogroup:self` does not apply
to tags** — so a rule written against `autogroup:self` silently covers
nothing here. Rules for tagged devices have to name the tags. This broke all
SSH from the dev machines once already, on 2026-08-19.

Read the live policy without opening the console:

```bash
scripts/tailscale_policy.sh            # prints the current policy file
scripts/tailscale_policy.sh validate <file>   # dry-run a proposed one
```

The stored OAuth credential is read-only, so applying a change is a paste
into the [policy file editor](https://login.tailscale.com/admin/acls/file).
Validate first — a bad save is a lockout.

A `check`-mode rule sets a re-auth period. When it lapses, ssh stops at
`# Tailscale SSH requires an additional check.` and prints a
`login.tailscale.com/a/...` URL — open it, approve, then re-run ssh. The URL
is single-use, so don't bother saving it. Under `-o BatchMode=yes` or any
non-interactive wrapper this just looks like a hang; that message is the
tell. This applies only to connections from untagged devices: **Tailscale
forbids `check` from a tagged source**, so the dev machines and cloud
sessions never see it.

### A page hangs but the host is reachable — MTU

Symptom: the browser spins forever on `https://signalk.symphony.dark-star-llc.com/`, ssh and
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

---

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

---

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
readable YAML.

> 🔴 **Critical:** If it doesn't, stop — nothing downstream will work, and
> continuing will produce confusing failures that look like Docker problems.

### Phase 3 — Repo and configuration

```bash
git clone https://github.com/mark-brannan/symphony.git
cd symphony
cp hostvars.local.yaml.example hostvars.local.yaml
# edit hostvars.local.yaml: set THIS machine's values (the example lists them)
bash scripts/setup-git-filters.sh
python3 scripts/render.py
```

`setup-git-filters.sh` is the one onboarding command: it wires the sops and
hostvars clean/smudge filters, installs the pre-commit hooks, clears any
stale `core.hooksPath`, decrypts the in-place files onto disk, and expands
the per-machine values from `hostvars.local.yaml`
([Per-machine config values](#per-machine-config-values)). It only touches
files that are *still ciphertext or placeholders*, so it can never clobber
live local config, and it's safe to re-run at any time.

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

On the boat, once SSO is configured ([SSO login](#sso-login-github--google)),
use this instead so
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

### Special cases

#### First-ever boot

If no `security.json` has ever existed, there's nothing to decrypt. Let
SignalK create its own through the setup wizard on first admin login, then
`git add signalk/security.json` once so it starts being tracked — encrypted
— from that point forward.

#### What `provision_influxdb.sh` does

It can mint credentials that then need propagating by hand, so read this
before running it:

- On a **fresh** volume it runs `/api/v2/setup` (org `darkstarllc`, bucket
  `symphony`) and stores the resulting operator token. On an **existing**
  one it uses the operator token already in `secrets/symphony.sops.yaml`.
  Everything under `DOCKER_INFLUXDB_INIT_*` is fresh-volume-only in the same
  way. That is why the boat's database says org `symphony` while `.env` says
  `darkstarllc`, and why the admin user `.env` names does not exist: the
  volume predates both. Changing those values on a running install does
  nothing and silently disagrees with reality.
- Either way it creates the `captain` user as an org *member*, not owner —
  InfluxDB OSS has only those two levels — and mints read/write-scoped
  tokens for the SignalK plugin and Grafana's datasource if they don't
  already exist.
- **If it minted a new `influx_token`:** re-run `scripts/render.py` and
  `docker compose up -d --force-recreate grafana`.
- **If it minted a new `influxdb_signalk_token`:** update the `token` field
  in `signalk/plugin-config-data/signalk-to-influxdb2.json` and restart
  `signalk-server`.

---

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
30-second timeout, so a hang that stops answering ping and SSH resets the
board instead of waiting for someone aboard to pull power. Confirm it took:

```bash
journalctl -b | grep -i "hardware watchdog"
systemctl show -p RuntimeWatchdogUSec
cat /sys/class/watchdog/watchdog0/timeout
```

Expect `Watchdog running with a hardware timeout of 30s`,
`RuntimeWatchdogUSec=30s`, and `30`. Read all three: 15s is the bcm2835
hardware heartbeat and the kernel extends past it in software, so a value
above 15 is honoured rather than clamped — but check rather than assume it.

It won't catch a wedged service while systemd keeps running — that needs a
separate check.

`chrony.conf` sets the clock policy: step by any amount at any time, and serve
time to the boat's own networks. chrony replaces `systemd-timesyncd`, which
`apt` removes on install. The installer places config but does not install
packages — do that first, or it sits there inert:

```bash
sudo apt install chrony
sudo host/install.sh
```

*Verify:* `chronyc tracking` names a reference and reports a small offset, and
`chronyc sources` shows one peer selected with `^*`.

Don't add a GPS refclock. The usual `refclock SHM` recipe reads gpsd's shared
memory, and this boat's GNSS is on NMEA 2000 rather than a serial port, so
those segments are never written — `ntpshmmon` returns no samples no matter
which segment number you pick. See `reference/compute_hardware.md` → "GNSS
arrives on NMEA 2000, and SignalK isn't reading it".

Don't add `rtcsync`: the Pi 4B has no RTC, which is the reason `makestep 1.0
-1` is there. Without it chronyd slews rather than steps, and a clock that
booted years wrong stays wrong for hours.

`telegraf-rpi-health` feeds telegraf's `exec` input, turning
`vcgencmd get_throttled` into the `rpi_health` measurement. Run it by hand to
check it works; it prints one line of InfluxDB line protocol:

```bash
/usr/local/bin/telegraf-rpi-health
```

All-zero fields are the healthy answer. A `1` in any `_since_boot` field means
the SoC saw under-voltage or throttling at some point since the last boot,
which on this boat means the NMEA 2000 bus sagged.

`boat-heartbeat` and its timer ping an external dead man's switch every five
minutes with a vitals summary, so that the box going silent raises an alarm
somewhere that isn't the box. **It does nothing until you give it a URL** —
see "Turning on the off-boat heartbeat" below.

`nightly-reboot` is still installed, but its line in root's crontab is
commented out. It rebooted the Pi at 04:00 **unless** an `npm` or `node-gyp`
process was running. Keep that guard if you ever turn it back on.

> 📌 **Gotcha:** Don't call `shutdown` from cron directly — a reboot landing
> on an `npm install` in `~/.signalk` truncates the plugin tree, and npm
> won't repair it afterward because it sees the half-written directories and
> considers those packages installed.

On a night it runs, check which way it went with:

```bash
journalctl -t nightly-reboot --since yesterday
```

---

## Turning on the off-boat heartbeat

Armed on the boat Pi as of 2026-08-13; this is how to change it or set it up
elsewhere. The ping URL lives in `host/boat-heartbeat.json`, whose `url` field
is sops-encrypted, so it is in version control without being readable in a
public repo. `host/install.sh` places it at `/etc/boat-heartbeat.json`, mode
0600 root. The script exits immediately if that file is missing, so removing
it turns the heartbeat off.

Treat the ping URL as a bearer credential — anyone holding it can send false
"alive" pings, which masks a dead boat rather than leaking anything. If it is
ever exposed, rotate the check on the provider's side.

1. Create a check on any service that hands out a ping URL — Healthchecks.io,
   Better Stack, Cronitor all work, and the script doesn't care which. Set the
   expected period to **5 minutes** and the grace period to **20 minutes or
   more**. The boat's uplink drops routinely; a tight grace turns a normal
   marina wifi hiccup into a 3 a.m. alarm, and alarms you learn to ignore are
   worse than none.
2. Put the URL in the repo file and install it. Edit the `url` field in
   `host/boat-heartbeat.json` — on disk it is plaintext, and the clean filter
   encrypts it on the way into git:

```bash
git diff --cached host/boat-heartbeat.json   # must show ENC[...], not the URL
sudo host/install.sh
```

> 🔴 **Critical:** If that diff shows the URL in the clear, stop: the sops
> filter isn't wired in this checkout. Run `bash scripts/setup-git-filters.sh`
> and re-stage. This is not hypothetical — it was found unconfigured here
> on 2026-08-13, which is the state in which a secret gets committed in
> public.

3. Fire one ping by hand and read the result:

```bash
sudo systemctl start boat-heartbeat.service
journalctl -t boat-heartbeat -n 5
systemctl list-timers boat-heartbeat.timer
```

Expect `ping ok` and a `NEXT` about five minutes out. `ping failed` covers both
a dead endpoint and no uplink at all — the script can't tell them apart, so
check the uplink first and the URL second. It exits 0 either way on purpose,
so a boat that is merely offline doesn't leave a failed unit behind; the log
line is the only place a failure shows.

To see what actually gets posted, point it at a listener on the box. Move the
live file aside first — overwriting it in place loses the real ping URL:

```bash
python3 -m http.server 8899 --bind 127.0.0.1 &
sudo mv /etc/boat-heartbeat.json /etc/boat-heartbeat.json.real
echo '{"url":"http://127.0.0.1:8899/test"}' | sudo tee /etc/boat-heartbeat.json >/dev/null
sudo systemctl start boat-heartbeat.service
journalctl -t boat-heartbeat -n 2
sudo mv /etc/boat-heartbeat.json.real /etc/boat-heartbeat.json
```

The body is one `key: value` per line — uptime, load, mem available, disk,
temp, throttled, clock, failed units — so whichever service you choose needs
to accept a POST body, or ignore it.

To turn it off, delete `/etc/boat-heartbeat.json`. Don't disable the timer —
leaving it running means re-enabling is one file away, and the check on the
other end is what tells you the boat went quiet.

---

## Don't autostart a browser on the boat Pi

> 🔴 **Critical:** Chromium started from `~/.config/autostart` renders with
> GPU acceleration whether or not an HDMI display is connected, and on this
> Pi that wedges the v3d driver. `Resetting GPU for hang` then repeats
> several times a minute until a kworker blocks permanently in
> `v3d_gpu_reset_for_timeout`, systemd stops petting the watchdog, and the
> board hard-resets. Those blocked kworkers also hold the load average up by
> one apiece, so load stops meaning anything; nothing but a reboot clears
> them.

```bash
journalctl -b -k | grep -c "Resetting GPU for hang"    # want 0
ps -eo pid,stat,comm | awk '$2 ~ /D/'                  # want no kworker
```

If the count is climbing, find what's driving the GPU and stop it — the
desktop by itself doesn't touch v3d. The Freeboard entry now sits in
`~/.config/autostart-disabled/`; its Desktop launcher still works when
someone is actually at a screen.

---

## Upgrading the scanners

`pre-commit autoupdate` does nothing here — every hook is `repo: local`, so
there are no upstream revisions to bump. The versions live in three places
and all three must move together, or a commit gets cleared by one scanner
version and a push by another:

```bash
grep -n GITLEAKS_VERSION   scripts/gitleaks_precommit.sh    # commit-time
grep -n TRUFFLEHOG_VERSION scripts/scan_verified_secrets.sh # CI + local
grep -n zricethezav        .github/workflows/secret-scan.yml # CI
```

Edit all three to the same tag, then pull the new images **dockside, not
underway** — the first run after a bump fetches from Docker Hub, and a
failed fetch mid-passage leaves the commit-time hook degrading to a warning
just when you can least check it by hand.

The scanners live in `secret-scan.yml`, not `validate.yml`. Nothing in
`validate.yml` is version-pinned this way.

---

## Adding a secret

Two schemes, and they don't share a procedure. A standalone value — an API
key, a token, a password nothing reads yet — goes into the Layer 1 store.
A secret *field inside a config file* SignalK/Grafana reads off disk is
in-place, via the script. Using the script on the store is the failure mode
here — see the warning at the end of this section.

### Layer 1: store the value (`secrets/symphony.sops.yaml`)

This file is encrypted as a whole and sits on disk as ciphertext. No git
filter touches it — `sops` is the only way to edit it, and a plain
`git add` commits the ciphertext exactly as it is on disk.

Storing a secret is a complete change on its own. Commit it as its own
commit; wiring a consumer (next subsection) is a separate change that can
land days later or never:

```bash
sops secrets/symphony.sops.yaml   # opens decrypted in $EDITOR; add the
                                  # `healthchecks_api_key: <value>` line, save
git add secrets/symphony.sops.yaml
git commit -m "Store healthchecks.io API key" -- secrets/symphony.sops.yaml
```

*Verify:* `sops --decrypt --extract '["healthchecks_api_key"]' secrets/symphony.sops.yaml`
prints the value, and
`git show :secrets/symphony.sops.yaml | grep healthchecks_api_key` shows
`ENC[`, not the value.

If sops prints `File has not changed, exiting.`, the edit did not take —
usually the editor quit without saving — and there is nothing to commit.
Re-run it, and trust the verify line over your memory of having typed the
key.

### Layer 1: wire a consumer (a new `.env` value)

When something actually starts reading the stored value:

```bash
$EDITOR .env.example                     # add the same key, blank/dummy value
$EDITOR .env.j2                          # add the {{ jinja }} line
python3 scripts/render.py
```

then restart whatever reads it — a running process picks up `.env` only
across a restart (`docker compose up -d --force-recreate <svc>`; on the
boat, `sudo systemctl restart <svc>`).

### In-place (a plugin config file SignalK/Grafana already owns)

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

### Never point `add_inplace_secret.sh` at `secrets/*.sops.yaml`

The script refuses `secrets/` paths and ciphertext-on-disk files up front.
A run predating that guard edited before it verified: by the time it failed
on a whole-file encrypted store, it had already appended a `.sops.yaml`
rule and a `.gitattributes` `filter=sops` line for it — and
`sops_paths.py check` accepts that state as consistent. The stray filter line then makes every
later `git add` of the file run the clean filter, which fails with sops
complaining about *"a top-level entry called 'sops'"*.

A failed run also leaves the file staged as **deleted** — the script runs
`git rm --cached` just before the `git add` that fails — so until the
recovery below is done, a commit that sweeps up the index would remove the
file from the repo. Don't commit anything else from that checkout first.

If a `secrets/` file gives you that error on `git add`, this is what
happened. To recover, delete the two appended blocks — the `filter=sops`
line at the end of `.gitattributes`, and the `path_regex` block for the
file at the end of `.sops.yaml` — then confirm and re-add:

```bash
git check-attr filter -- secrets/symphony.sops.yaml   # want: unspecified
python3 scripts/sops_paths.py check
git add secrets/symphony.sops.yaml
```

`unspecified` is the correct answer for everything under `secrets/`; those
files never go through the filter.

---

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

**InfluxDB tokens** can't be reset in place — a value is shown once, at
creation. So the order is mint, migrate, verify, *then* revoke: the old token
keeps working until the new one is proven, and no writes are lost mid-rotation.

Everything below is plain HTTP against `:8086` and is identical bare-metal or
containerized. Only step 5 forks.

**1. Get a credential that works, and the org id.** Of the four InfluxDB
tokens in sops, only `influxdb_captain_token` authenticates — the other three
returned 401 when last checked on 2026-08-14. Don't assume; check the code:

```bash
cd ~/symphony
TOK=$(sops --decrypt --extract '["influxdb_captain_token"]' secrets/symphony.sops.yaml)
ORG=$(curl -s -H "Authorization: Token $TOK" http://localhost:8086/api/v2/orgs \
      | python3 -c 'import json,sys;print(json.load(sys.stdin)["orgs"][0]["id"])')
curl -s -o /dev/null -w "auth check: %{http_code}\n" \
     -H "Authorization: Token $TOK" http://localhost:8086/api/v2/authorizations
```

`200` and you can continue. `401` means that one is dead too — see "When every
stored token is dead" below.

**2. Find the authorization you're replacing.** `?orgID=` takes the hex id, not
a name:

```bash
curl -s -H "Authorization: Token $TOK" \
     "http://localhost:8086/api/v2/authorizations?orgID=$ORG" \
  | python3 -c '
import json,sys
for a in json.load(sys.stdin)["authorizations"]:
    print(a["id"], repr(a.get("description","")), "perms=%d" % len(a["permissions"]))
'
OLD_ID=<paste the id>
```

**3. Mint the replacement with the same permissions:**

```bash
curl -s -H "Authorization: Token $TOK" \
     "http://localhost:8086/api/v2/authorizations/$OLD_ID" > /tmp/oldauth.json
python3 -c '
import json
a=json.load(open("/tmp/oldauth.json"))
json.dump({"orgID":a["orgID"],"userID":a["userID"],
           "description":a.get("description","")+" (rotated)",
           "permissions":a["permissions"]}, open("/tmp/newauth-req.json","w"))
'
curl -s -X POST -H "Authorization: Token $TOK" -H "Content-Type: application/json" \
     -d @/tmp/newauth-req.json http://localhost:8086/api/v2/authorizations \
  > /tmp/newauth.json
NEW=$(python3 -c 'import json;print(json.load(open("/tmp/newauth.json"))["token"])')
```

Don't echo `$NEW`. Terminal scrollback persists, and in a Claude session it
lands in a transcript — which is what caused the 2026-08-14 rotation.

**4. Update every consumer. Find them, don't trust a list** — the list grows:

```bash
grep -rl -- "$TOK" ~/.signalk/plugin-config-data/ /etc/telegraf/ 2>/dev/null
grep -c -- "$TOK" ~/symphony/.env

for f in $(grep -rl -- "$TOK" ~/.signalk/plugin-config-data/); do
  OLD="$TOK" NEW="$NEW" python3 -c '
import os,io,sys
p=sys.argv[1]; s=io.open(p,encoding="utf-8").read()
io.open(p,"w",encoding="utf-8").write(s.replace(os.environ["OLD"],os.environ["NEW"]))
print("updated", p)
' "$f"
done

sops --set "[\"influxdb_captain_token\"] \"$NEW\"" secrets/symphony.sops.yaml
python3 scripts/render.py
```

Two of those files are easy to miss by hand: in
`signalk-to-influxdb2.json` the token is nested at
`configuration.influxes[].token`, not top-level, and the buffering plugin's
file is `signalk-to-influxdb-v2-buffer.json` — `-buffer`, though the plugin is
named `-buffering`.

**5. Restart consumers, then prove writes land** *before* revoking:

```bash
sudo systemctl restart signalk telegraf                      # bare metal
# docker compose up -d --force-recreate signalk telegraf     # containerized

curl -s -H "Authorization: Token $NEW" -H "Content-Type: application/vnd.flux" \
     -H "Accept: application/csv" -XPOST \
     "http://localhost:8086/api/v2/query?org=symphony" \
     -d 'from(bucket:"symphony")|>range(start:-2m)|>limit(n:3)' | head -3
```

Rows means the new credential is carrying traffic. No rows means stop and fix
it — the old token still works, so nothing is lost yet.

**6. Revoke, and prove it's dead:**

```bash
curl -s -o /dev/null -w "delete: %{http_code}\n" -X DELETE \
     -H "Authorization: Token $NEW" \
     "http://localhost:8086/api/v2/authorizations/$OLD_ID"
curl -s -o /dev/null -w "old token now: %{http_code}  (401 = revoked)\n" \
     -H "Authorization: Token $TOK" http://localhost:8086/api/v2/authorizations
shred -u /tmp/oldauth.json /tmp/newauth.json /tmp/newauth-req.json
```

Expect `204` then `401`. Record it in `ROTATION.md`, which is where credentials
already rotated and the reason are kept.

### When every stored token is dead

`influxdb_operator_token`, `influxdb_signalk_token` and `influx_token` all
return 401 as of 2026-08-14, and the repo's tracked copy of
`signalk/plugin-config-data/signalk-to-influxdb2.json` carries a *third* dead
token, different again from the boat's live value. Following any procedure
that reaches for one of those propagates a 401 credential.

If nothing authenticates, what's left is the InfluxDB UI at `:8086` with the
`captain` login, or `scripts/provision_influxdb.sh` against a fresh volume.
Neither has been exercised from a fully locked-out state, so treat them as
untested rather than as a procedure.

---

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

---

## Removing a secret

To stop tracking a file's secret (plugin uninstalled, field no longer used):

1. Delete its `path_regex` block from `.sops.yaml`.
2. Delete its `filter=sops` line from `.gitattributes`.
3. `python3 scripts/sops_paths.py check` — confirms the two still agree.
4. If the file itself is going away: `git rm --cached <file>` and add it to
   `.gitignore`.

Removing the rules does **not** un-publish anything already committed. If
the secret was ever live in a public commit, rotate it — see below.

---

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

---

## Per-machine config values

Some plugin-config values differ per machine without being secrets — the
first is `signalk-ntfy`'s server URL (`http://ntfy:80` on the dev stack,
`http://localhost:8090` on the boat Pi). Git stores a placeholder
(`"{{ ntfy_url }}"`); the working tree holds this machine's value, expanded
by the `hostvars` clean/smudge filter from `hostvars.local.yaml`
(gitignored). Which files and variables: `.hostvars.yaml`. Why it's built
this way: [reference/software_stack.md](reference/software_stack.md).

SignalK reads plugin config only when the plugin starts, so every change
below ends with a restart — `sudo systemctl restart signalk` on the boat,
`docker compose restart signalk` on the dev stack. Skip it and the running
plugin keeps its old config, which makes the change look like it did
nothing.

### Set up a machine

```bash
cp hostvars.local.yaml.example hostvars.local.yaml
# edit hostvars.local.yaml -- the example lists the known per-machine values
bash scripts/setup-git-filters.sh
```

*Verify:* `grep url signalk/plugin-config-data/signalk-ntfy.json` shows a
real URL.

> ⚠️ **Warning:** If it shows `{{ ntfy_url }}`, don't (re)start SignalK until
> that's fixed — it reads the placeholder as a literal URL. If SignalK was
> already running during setup, restart it.

### Change this machine's value (e.g. the ntfy URL moved)

```bash
# edit hostvars.local.yaml, then:
python3 scripts/hostvars_filter.py refresh
sudo systemctl restart signalk   # dev stack: docker compose restart signalk
```

Don't skip `refresh`: editing `hostvars.local.yaml` alone changes nothing on
disk, and don't use `git checkout --` for this — it would discard any other
local changes in the file; `refresh` rewrites only the placeholder values.

*Verify:* `grep url signalk/plugin-config-data/signalk-ntfy.json` shows the
new value, and after the restart the plugin's page under Server → Plugin
Config shows it too.

If instead the value was changed in SignalK's admin UI first, the plugin is
already using it and needs no restart, but git and `hostvars.local.yaml` now
disagree with the disk. Update `hostvars.local.yaml` to match and run
`refresh` — it prints `unchanged`, which is right, the disk already has the
value. If the file had already been staged, re-stage it:

```bash
git add --renormalize signalk/plugin-config-data/signalk-ntfy.json
```

Until the two agree, committing the file is blocked by the
`hostvars-placeholders` pre-commit hook (and the same check in CI) rather
than committing one machine's value over the other's.

### Add a new per-machine value

Worked example: `signalk/plugin-config-data/foo.json` gains a per-machine
`"endpoint"` value, variable name `foo_endpoint`.

1. Declare it in `.hostvars.yaml` (and add the file to `.gitattributes` as
   `filter=hostvars` if it isn't listed there yet):

   ```yaml
     signalk/plugin-config-data/foo.json:
       - foo_endpoint
   ```

2. Add it to `hostvars.local.yaml.example` with the known machines' values
   in a comment; set this machine's value in `hostvars.local.yaml`.

3. Leave the real value in the plugin file — never write the placeholder
   into it by hand; the clean filter contracts the value while staging.
   The staging command depends on whether git already tracks the file:

   ```bash
   git add signalk/plugin-config-data/foo.json                # new file
   ```

   ```bash
   git add --renormalize signalk/plugin-config-data/foo.json  # already tracked
   ```

   Already-tracked files need `--renormalize` because a plain `git add`
   skips the filter when the file looks unmodified — but `--renormalize`
   silently stages *nothing* for an untracked file, so a new file needs the
   plain form.

4. *Verify:* `git show :signalk/plugin-config-data/foo.json` shows
   `{{ foo_endpoint }}`. Commit it together with `.hostvars.yaml`,
   `.gitattributes`, and `hostvars.local.yaml.example`.

5. On every other machine, after pulling: add that machine's value to its
   `hostvars.local.yaml`, then

   ```bash
   python3 scripts/hostvars_filter.py refresh
   sudo systemctl restart signalk   # dev stack: docker compose restart signalk
   ```

   The pull prints `hostvars: WARNING ... left unexpanded` as the reminder.
   Until the refresh runs, the file on disk holds the literal placeholder,
   and SignalK would read it as the real value at the plugin's next start —
   `scripts/lint_host_state.py` flags this state on the boat.

### A pull rejects: "Your local changes ... would be overwritten by merge"

Happens when a pull brings a file under hostvars coverage while the working
tree still holds this machine's literal value — this is how an existing
checkout picks up coverage that was added on another machine. Git's own two
suggestions are both wrong here: `git stash` is forbidden repo-wide, and
committing would commit the machine-local value. The local difference is
exactly the value the filter regenerates, so it's safe to discard for this
one file:

1. Discard only the covered file and pull:

   ```bash
   git checkout -- signalk/plugin-config-data/signalk-ntfy.json
   git pull
   ```

2. Put this machine's value in `hostvars.local.yaml` — the pull just
   delivered `hostvars.local.yaml.example` if this machine has neither.
3. Expand it:

   ```bash
   bash scripts/setup-git-filters.sh
   ```

4. *Verify:* `grep url signalk/plugin-config-data/signalk-ntfy.json` shows
   this machine's URL. Restart SignalK.

Between the checkout and the setup script the file on disk is wrong (first
the other machine's committed value, then a placeholder), so run the three
commands in one sitting and don't restart SignalK partway through.

---

## Router config backup

The boat router holds the local DNS override that makes the hostnames
resolve on the boat. A factory reset takes it, and on-boat access with it.
An encrypted copy of the router's full UCI config lives in
`secrets/router-config.sops.yaml`.

Refresh it after any router change (the pi's key is authorized on the
router; run this from anywhere on the tailnet):

```bash
ssh pi@symphony-pi 'ssh root@192.168.8.1 "uci export"' > /tmp/uci.txt
test -s /tmp/uci.txt && grep -q '^package' /tmp/uci.txt && echo export ok
python3 -c "import yaml; yaml.safe_dump({'uci_export': open('/tmp/uci.txt').read()}, open('secrets/router-config.sops.yaml','w'), default_style='|')"
sops --encrypt --in-place secrets/router-config.sops.yaml
rm /tmp/uci.txt
```

Check the `export ok` line before going on — a failed ssh leaves
`/tmp/uci.txt` empty, and the next step overwrites the backup with it.

Overwriting the file with fresh plaintext first is what makes
`--encrypt --in-place` work: run against the existing *encrypted* file it
fails with sops's "top-level entry called 'sops'" error. This file is a
snapshot of one export, so a wholesale replace loses nothing.

*Verify:* `sops --decrypt --extract '["uci_export"]' secrets/router-config.sops.yaml | head -3`
shows the export. Then `git add secrets/router-config.sops.yaml` and commit.

To read or restore:

```bash
sops --decrypt secrets/router-config.sops.yaml
```

Feed the `uci_export` contents back through `uci import` on the router,
then `reload_config`. Restoring overwrites WiFi and WAN settings too —
this is a whole-config restore, not a DNS-only one.

---

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

---

## A secret was committed in plaintext

**Rotate first. Everything else is secondary.** Assume it's compromised the
moment it's pushed — it's in GitHub's API, in forks, and in anything scraping
new commits. Rewriting history does **not** un-publish it; GitHub keeps
unreferenced commits reachable by SHA.

1. Revoke and reissue the credential at its provider. This is the only step
   that fixes anything — see "Rotating a secret" above.

2. Add the `.sops.yaml` rule it was missing, which is usually how it got
   through:

```bash
scripts/add_inplace_secret.sh <file> <field>
```

3. Confirm the new value is encrypted and nothing else is still live:

```bash
bash scripts/verify_encrypted.sh
scripts/scan_verified_secrets.sh
```

Consider history rewriting only if the value genuinely cannot be rotated — a
hardcoded key in a third-party device, say. It force-pushes, breaks every
existing clone, and still does not remove the data from GitHub's servers
without contacting GitHub Support.

`main`'s [branch ruleset](https://github.com/mark-brannan/symphony/settings/rules/21060338)
blocks force pushes with no standing bypass. To do this, temporarily disable
the ruleset (or add yourself to its bypass list), push the rewritten history,
then re-enable it. There is no faster path — this is by design.

---

## Recovering a lost age key

The age private key is the single point of failure — anyone provisioning a new
host, or recovering this one, needs it, and it is never in git.

**Prevent this.** Keep two valid recipients, store the second away from the
first, and never retire it. Losing one then costs nothing:

```bash
scripts/rotate_age_key.sh add --generate
```

**If you have a backup**, restore it and everything works normally:

```bash
mkdir -p ~/.config/sops/age
cp <the backup> ~/.config/sops/age/keys.txt
chmod 600 ~/.config/sops/age/keys.txt
sops --decrypt secrets/symphony.sops.yaml | head -1   # expect readable YAML
```

**If the key is truly gone**, every sops-encrypted value is unrecoverable from
git alone. Generate a fresh keypair, repoint `.sops.yaml`, then re-populate
from live sources:

```bash
age-keygen -o ~/.config/sops/age/keys.txt
# put the new public key in .sops.yaml, then re-add each file:
git add secrets/symphony.sops.yaml signalk/security.json
```

What re-populates from where: `secrets/symphony.sops.yaml` values come from
what's live in the running containers and `.env`. The in-place files come from
their plaintext-on-disk copies, which losing the key does not touch — only the
git-stored encrypted copies become unreadable.

One exception. `influxdb_operator_token` has no plaintext copy anywhere, being
used only by provisioning scripts — and it is already dead. Recovering from
that is its own procedure: "When every stored token is dead", under "Rotating
a secret" above.

**Don't reach for `DOCKER_INFLUXDB_INIT_USERNAME` / `_PASSWORD` as the
break-glass login.** Those apply only when InfluxDB initialises a *fresh*
volume. This volume already existed when they were set, so the user they name
was never created and signing in with them returns 401 — which reads as a wrong
password rather than a missing account. The login that exists is `captain`.

Last resort: `~/symphony-backups/` holds a plaintext snapshot of the live
SignalK config from 2026-08-07, deliberately outside the repo. It is a full set
of live credentials in the clear — treat it accordingly.

---

## SSO login (GitHub / Google)

SignalK and Grafana web UIs show a "Sign in with GitHub / Google" button.
Behind it sits Dex, a small identity provider on the boat at
`auth.symphony.dark-star-llc.com`: SignalK and Grafana trust only Dex; Dex hands the actual
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
   - `symphony.dark-star-llc.com` → the host's **tailnet** IP, e.g. `100.113.172.64`
   - `signalk.symphony.dark-star-llc.com`, `grafana.symphony.dark-star-llc.com`, `auth.symphony.dark-star-llc.com` → CNAME to
     `symphony.dark-star-llc.com`

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
   `address=/symphony.dark-star-llc.com/192.168.1.50`, or the router UI's "local DNS
   records"). One wildcard entry covers the apex and every subdomain,
   so adding a service later needs no router change.

   Don't skip this. It is what makes the hostname work for anything on
   the boat that isn't on the tailnet — a guest's phone — and offshore
   there is no public DNS at all, so without it even already-logged-in
   devices can't resolve the names.

*Verify:* from a device on the boat LAN **with the WAN link
disconnected**, `nslookup signalk.symphony.dark-star-llc.com` returns the LAN IP.

### 2 — OAuth apps (one-time)

**GitHub** — under the personal account, no org involved:
[github.com/settings/developers](https://github.com/settings/developers)
→ OAuth Apps → New OAuth App:

- Application name: anything (e.g. "Symphony boat systems")
- Homepage URL: `https://auth.symphony.dark-star-llc.com`
- Authorization callback URL: `https://auth.symphony.dark-star-llc.com/dex/callback`

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
   `https://auth.symphony.dark-star-llc.com/dex/callback`
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

On the boat Pi today, Dex is a container and Caddy is still a native
systemd service, so deploy them separately:

```bash
git pull
python3 scripts/render.py
docker compose --profile tls up -d dex
sudo systemctl restart caddy
```

**Name `dex` explicitly.** A bare `--profile tls up -d` also starts the
`caddy` container, which fails to bind `:443` against the native Caddy
already holding it and proxies to container names that don't exist on
that host. The front door goes down and the cause isn't obvious.

On a host where everything is containerized, the whole profile is right:

```bash
docker compose --profile tls up -d --build
```

The first run builds the caddy image and issues certificates, so it needs
internet — do it dockside.

Restart Grafana and SignalK too if you changed anything they read —
`GF_AUTH_GENERIC_OAUTH_*` or `SIGNALK_OIDC_*`. They pick up `.env` through
an `EnvironmentFile=` drop-in, so a re-render alone doesn't reach a running
process.

*Verify:*

```bash
curl -s https://signalk.symphony.dark-star-llc.com/signalk/v1/auth/oidc/status
curl -s https://auth.symphony.dark-star-llc.com/dex/.well-known/openid-configuration | head -3
```

The first expects `"enabled":true` and
`"issuer":"https://auth.symphony.dark-star-llc.com/dex"`; the second returns JSON if Dex is
up behind Caddy. If TLS itself fails, certificates haven't issued — check
`docker logs caddy`. Then from a browser on the LAN:

- `https://signalk.symphony.dark-star-llc.com` → sign in as the owner with either provider →
  Security → Users shows that user with type `admin`. Any other account
  shows `readonly`. An owner login that comes out `readonly` means
  `SIGNALK_OIDC_GROUPS_ATTRIBUTE` didn't reach the server — it fails
  silently, so check the container's environment rather than the logs.
- `https://grafana.symphony.dark-star-llc.com` → the owner's login → Admin; any other
  account → refused (that's the strict email list working).
- The `captain` password still logs in on SignalK with admin.

### Who gets what

| Login | SignalK | Grafana |
|---|---|---|
| any GitHub or Google account | readonly | refused |
| the owner's email, via either provider | admin | Admin |
| `captain` (local password) | admin | — |
| Grafana superadmin / provisioned users (password) | — | Admin / as provisioned |

Both services now key off the same thing — the email on the login — so
either provider gives the same answer.

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
- **SignalK:** add the address to `SIGNALK_OIDC_ADMIN_GROUPS` in
  `.env.j2` — comma-separated, e.g.
  `owner@example.com,crew@example.com` — then `python3 scripts/render.py`
  and `docker compose up -d --force-recreate signalk`.
  `SIGNALK_OIDC_READWRITE_GROUPS` takes the same form for a lesser
  grant. Matched literally and case-sensitively.
- Both lists are read fresh on every login, so removing an address
  demotes that person the next time they sign in — no user cleanup
  needed. Promoting someone by hand in the SignalK admin UI does not
  stick, for the same reason.
- **Don't remove `SIGNALK_OIDC_GROUPS_ATTRIBUTE=email`.** It looks
  redundant and isn't: it's what makes ADMIN_GROUPS read as an email
  list at all. Without it the server looks for a `groups` claim that
  nothing sends, and every SSO login silently drops to readonly.

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

---

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

## Bringing up QuestDB on the boat

`compose-questdb.yml` is included from `docker-compose.yml`.

1. Raise the kernel's memory-mapping limit. QuestDB memory-maps every
   partition column file, and a grown database exhausts the default — queries
   then fail with out-of-memory errors while RAM is free. It is a host
   setting; it cannot be set from inside the container.

   ```bash
   if [ "$(cat /proc/sys/vm/max_map_count)" -lt 1048576 ]; then
     echo 'vm.max_map_count=1048576' | sudo tee /etc/sysctl.d/99-questdb.conf
     sudo sysctl --system
   fi
   test "$(cat /proc/sys/vm/max_map_count)" -ge 1048576 && echo ok
   ```

   1048576 is a floor, not a target — the conditional is there so a host that
   already sets it higher for something else keeps its value.

   Still the old value → another file sets it later in load order:
   `grep -r max_map_count /etc/sysctl.d/ /etc/sysctl.conf`, remove the loser,
   re-run `sudo sysctl --system`.

2. Start it and check it is ready.

   ```bash
   docker compose -f docker-compose.yml up -d questdb
   curl -fsS --max-time 5 --retry 30 --retry-delay 2 --retry-connrefused \
     -G --data-urlencode 'query=SELECT 1;' \
     http://127.0.0.1:9000/exec                     # answers = ready
   docker inspect questdb --format '{{range .Config.Env}}{{println .}}{{end}}' \
     | grep '^QDB_CAIRO_' | sort                    # compare against the list below
   ```

   All five must be present, with these values — a count alone would pass a
   container carrying the wrong ones:

   ```
   QDB_CAIRO_COMMIT_MODE=sync
   QDB_CAIRO_O3_COLUMN_MEMORY_SIZE=256k
   QDB_CAIRO_WAL_WRITER_DATA_APPEND_PAGE_SIZE=128k
   QDB_CAIRO_WRITER_DATA_APPEND_PAGE_SIZE=256k
   QDB_CAIRO_WRITER_DATA_INDEX_VALUE_APPEND_PAGE_SIZE=256k
   ```

   `docker compose up -d` returns before QuestDB can serve, hence the retries;
   on this Pi it takes a few seconds. And `http://127.0.0.1:9000/` is not a
   readiness check at all — it answers 301 as soon as the listener binds,
   before the database can serve anything. And check
   the caps with `docker inspect`, not `docker logs`: QuestDB does log each
   one as `server-main env config [key=QDB_CAIRO_...]` at startup, but this
   container caps its json-file log at 10 MB x 2, and QuestDB is verbose
   enough that those lines rotate out within hours — a log grep then reads 0
   on a correctly configured container.

   Any missing or different → the container came up without the page-size caps. Recreate
   it with `docker compose -f docker-compose.yml up -d --force-recreate
   questdb`, then repeat the two checks above before going on; they are read only at start. Without them QuestDB
   preallocates 16 MB per column file, and one Telegraf flush creating a table
   per measurement takes gigabytes for a few hundred rows. That filled this
   Pi's root filesystem on 2026-08-20, and InfluxDB's WAL writer then stuck in
   an ENOSPC retry loop that outlived the recovery.

3. Start the writers and make their tables durable.

   ```bash
   sudo systemctl restart telegraf
   until curl -sf -G --data-urlencode 'query=SELECT 1 FROM cpu LIMIT 1' \
     http://127.0.0.1:9000/exec | grep -q '"count":1'; do sleep 5; done
   scripts/questdb_table_hygiene.sh              # TTL + dedup
   sudo du -sm "$(docker inspect questdb \
     --format '{{range .Mounts}}{{if eq .Destination "/var/lib/questdb"}}{{.Source}}{{end}}{{end}}')"
   ```

   That `du` should read tens of MB, not GB. Ask docker for the volume path
   rather than typing it: it is derived from the compose project name, so it
   differs on any checkout not in a directory called `symphony`.

   Telegraf's first flush is a minute or so out, so wait for its tables rather
   than guessing: `cpu` is the sentinel, and the hygiene script's own output
   lists every table it changed and every one it did not recognise — read it,
   because an unrecognised table with no TTL is usually a new Telegraf
   measurement that needs adding to the script's list. Line protocol creates
   tables with no TTL and no dedup keys, so re-run the script after adding an
   input or recreating a table. Without
   dedup, a batch whose HTTP response timed out is retried into rows QuestDB
   already committed — duplicate data, and a skewed row-count parity check.

   `du` in gigabytes → stop the writers and go back to step 2's env check.

4. Check whether the memory cap is real.

   ```bash
   docker inspect questdb --format '{{.HostConfig.Memory}}'
   ```

   Expect `805306368` (the compose file's `mem_limit: 768m`) once cgroups are
   enabled, and `0` while they are not. Any other number means the running
   container predates a change to `mem_limit` — recreate it. This is a value
   to read, not a gate: it lives in `compose-questdb.yml` and changing it
   there should not fail this step.

   0 on this Pi: Raspberry Pi OS ships without `cgroup_enable=memory`, and
   `docker compose up` logs "Your kernel does not support memory limit
   capabilities or the cgroup is not mounted." To enforce it, append
   `cgroup_enable=memory cgroup_memory=1` to the single line in
   `/boot/firmware/cmdline.txt` and reboot. Until then watch instead of
   capping — `free -m`, `grep ^pswp /proc/vmstat` — and stop QuestDB if
   available memory goes under ~400 MB.

---

## SignalK's NMEA 2000 input

One connection, `n2k-can0`, reads the bus through canboatjs. It lives in
`signalk/settings.json` as a `pipedProvider` and is editable in the admin UI
under Server → Connections.

*Verify it's alive:*

```bash
curl -s localhost:3000/signalk/v1/api/vessels/self/navigation/position
curl -s localhost:3000/signalk/v1/api/vessels/self/navigation/gnss
```

Expect `"$source": "n2k-can0.<addr>"` and coordinates whose last digits move
between calls. A `$source` of `signalk-fixed-position` means the real GPS has
gone quiet and the fallback has taken over — see below.

If nothing arrives at all, check the bus before SignalK:

```bash
ip -br link show can0                  # want UP
timeout 5 candump -n 20 can0           # want frames
```

**Don't unset `uniqueNumber`.** It's pinned to `368391` in the connection's
`subOptions`. It forms part of the NAME this box claims on the bus; left
unset, SignalK generates a random one on save, and the Pi shows up as a
brand-new device to every other instrument each time.

### A fallback that has become the primary looks exactly like success

`signalk-fixed-position` (Position Keeper) stores the last known fix and
re-emits it once GPS has been quiet for its `interval`. That is wanted
behaviour — position-dependent plugins keep working through a GPS dropout.
The trap is that it looks identical to a working GPS: for a long time it was
the *only* position source on this boat, emitting a stored dock coordinate
about two metres from the truth, and nothing appeared broken.

> 📌 **Gotcha:** Don't read "there is a position" as "the GPS works." Read
> `$source`.

### When the AIS is powered, there will be two GPS sources

The chartplotter and the AIS each have their own receiver, so both publish
position, and SignalK will pick between them per-path in whatever order they
arrive. `~/.signalk/priorities.json` is what arbitrates; it is currently `{}`,
meaning no preference is expressed.

Set it once both are live and their addresses are known — an address is only
knowable by looking, since it's claimed dynamically:

```bash
curl -s localhost:3000/signalk/v1/api/sources | python3 -m json.tool | grep -A2 n2k-can0
```

Then give `navigation.position` an ordered source list with a timeout, so the
preferred receiver wins and the other takes over only after it goes quiet.
Doing this before both units are on would mean guessing at an address.

---

## Setting up a BLE sensor in bt-sensors-plugin-sk

Read this before adding a sensor or rebuilding this box. Two config keys are
required that nothing warns you about: leave either out and the sensor
connects, polls, decodes correctly and publishes **nothing**, with no error in
any log. Both are per-peripheral, in
`signalk/plugin-config-data/bt-sensors-plugin-sk.json`.

```json
{
  "active": true,
  "mac_address": "A5:C2:37:40:01:46",
  "params": {
    "name": "House Battery 1",
    "sensorClass": "JBDBMS",
    "batteryID": "0146",
    "pollFreq": 60
  },
  "paths": {
    "voltage": "electrical.batteries.0146.voltage",
    "SOC": "electrical.batteries.0146.capacity.stateOfCharge",
    "temp0": "electrical.batteries.0146.temperature"
  }
}
```

`params.pollFreq` (seconds) is what selects `initGATTInterval()`. Without it
`BTSensor::activateGATT` falls through to `initGATTNotifications()`, which some
sensor classes — JBDBMS among them — implement as an empty method. The device
connects, sends one read request and then sits idle forever.

`paths` must name every tag you want published. `initPaths()` subscribes a tag
only when `deviceConfig.paths[tag]` exists; the `.default` on each metadatum is
a suggestion for the config UI, **not** a runtime fallback. Saving the sensor
through the plugin's own config UI writes this block for you, which is why a
hand-written or hand-merged config is where this bites.

Confirm the whole plugin is publishing, not just one sensor:

```bash
curl -s http://localhost:3000/signalk/v1/api/vessels/self \
  | python3 -c 'import sys,json,collections
d=json.load(sys.stdin); c=collections.Counter()
def w(o):
    if isinstance(o,dict):
        if "value" in o and "$source" in o: c[str(o["$source"])]+=1
        for k,v in o.items():
            if k!="meta": w(v)
w(d)
print(c.most_common(20))'
```

Each configured sensor should appear as its own `$source` (the sensor's
`name`). If **no** sensor from the plugin appears, it is config, not the radio
— don't go debugging BLE.

Identify a device by MAC, never by advertised name. Symphony's two house
batteries both advertise as `DP04S007L4S200A`; only the MAC distinguishes them,
and BlueZ exposes it.

---

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

---

## Grafana dashboards

The dashboards are generated. `scripts/build_dashboards.py` holds the panel
spec; the JSON under `grafana/provisioning/dashboards/json/` is its output and
is committed because Grafana provisioning reads files and the boat has no
build step. After changing the spec:

```bash
python3 scripts/build_dashboards.py
python3 scripts/test_dashboards.py
```

The second one is not optional. It asserts the committed JSON still matches
the spec, that every unit label is backed by the matching conversion in its
query, that panels do not overlap, and that each query reads the bucket its
measurement is actually written to. A dashboard is wrong silently -- nothing
about a blank or mis-scaled panel raises an error at runtime -- so this check
is the only thing standing between a typo and a gauge that confidently reads
3.6 knots when the boat is doing 7.

Grafana's file provider is `editable: true`, so panels can be tweaked in the
UI to try something out. Those tweaks live only in Grafana's database and are
overwritten on the next provisioning reload. Anything worth keeping goes back
into the spec.

### Looking at them without being aboard

```bash
scripts/dev_stack.sh up
```

Starts InfluxDB and Grafana, creates the buckets, seeds synthetic vessel data
in SignalK's SI units, checks every panel draws, and prints the URL. Only
`influxdb` and `grafana` come up -- SignalK wants hardware a laptop does not
have. `scripts/dev_stack.sh down` removes the volumes.

The seed values are invented but the *shape* is real: same measurement names,
same `_field`, same tags, same SI units. Seeding in display units would make a
broken conversion look correct, which is the one thing this has to not do.

### Checking the real thing

Two checks, and they answer different questions:

```bash
python3 scripts/audit_dashboard_paths.py      # on the boat
python3 scripts/verify_dashboards_live.py --grafana https://grafana.<DOMAIN> \
    --user <admin> --password <password>
```

`audit_dashboard_paths.py` asks InfluxDB directly whether each referenced
measurement exists and is fresh, per bucket. It has to run on the boat -- it
reads the token out of the live plugin config.

`verify_dashboards_live.py` runs every panel's query through Grafana's own
`/api/ds/query`. That is the end-to-end one: datasource uid, token, Flux mode,
org, bucket and a publishing path all have to be right for a panel to pass.
The audit can pass while this fails, and that gap is exactly the datasource
wiring.

Both exit non-zero on a problem, so either can go in a cron or a check-in.

---

## InfluxDB buckets

Four buckets, each named after whoever writes it:

| Bucket | Writer | Retention |
|---|---|---|
| `signalk` | `signalk-to-influxdb2`, full rate | 90d |
| `signalk_archive` | the same plugin, second entry, decimated to 1/min | years |
| `telegraf` | Telegraf | 30d |
| `influxdb` | InfluxDB scraping its own `/metrics` | 7d |

Retention is a per-bucket property. That is the entire reason for the split:
one bucket cannot express "years of state-of-charge, two weeks of CPU." The
second reason is tokens -- Telegraf can hold a write-only token scoped to its
own bucket instead of borrowing captain's all-access one.

Splitting costs nothing at query time. **The bucket is named in the Flux
query, not in the datasource** -- `defaultBucket` is only Grafana's default for
ad-hoc exploration. One datasource and one read token reach all four, and a
panel can `union()` across them.

`signalk_archive` is deliberately the *same paths* at lower rate rather than a
chosen subset. Splitting by topic would mean deciding today which paths matter
in three years, and giving every panel a lookup table of which bucket its path
lives in. A superset at lower resolution needs neither: long-range panels read
the archive, live ones read `signalk`.

One caveat to record: the plugin's `resolution` **decimates** -- it drops
updates arriving inside the window -- rather than averaging. The archive keeps
trends and loses spikes between samples. An InfluxDB task doing
`aggregateWindow(fn: max)` would keep the extremes, at the cost of CPU and RAM
on a Pi where memory is already the constraint.

### Creating them

Run on the boat. Idempotent -- `influx bucket create` fails harmlessly if the
bucket is there.

```bash
# The CLI is not installed; these go through the HTTP API. Token comes from
# the live plugin config, same as the audit script.
python3 - <<'EOF'
import glob, json, os, urllib.request

cfg = glob.glob(os.path.expanduser(
    "~/.signalk/plugin-config-data/signalk-to-influxdb2.json"))[0]
token = json.load(open(cfg))["configuration"]["influxes"][0]["token"]

def api(path, data=None, method=None):
    req = urllib.request.Request("http://localhost:8086" + path,
                                 data=data, method=method)
    req.add_header("Authorization", "Token " + token)
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode() or "{}")

org_id = api("/api/v2/orgs?org=symphony")["orgs"][0]["id"]
DAY = 86400
for name, days in [("signalk", 90), ("signalk_archive", 0),
                   ("telegraf", 30), ("influxdb", 7)]:
    if api(f"/api/v2/buckets?name={name}").get("buckets"):
        print(f"{name}: exists")
        continue
    rules = [{"type": "expire", "everySeconds": days * DAY}] if days else []
    api("/api/v2/buckets", json.dumps(
        {"orgID": org_id, "name": name, "retentionRules": rules}).encode(),
        "POST")
    print(f"{name}: created")
EOF
```

Then repoint the writers. Telegraf reads `TELEGRAF_INFLUX_BUCKET` from the
rendered `.env`, so:

```bash
python3 scripts/render.py
sudo systemctl restart telegraf
```

Nothing needs migrating. The existing points in the old `symphony` bucket age
out on their own, and the dashboards stop reading it the moment the new
buckets have data.

### The signalk-to-influxdb2 change

This one is a plugin config edit, and the config file is sops-tracked -- make
it in SignalK's plugin UI (or on the live file on the boat, where the age key
is), not by hand-editing the committed copy. Target state for
`configuration.influxes`:

```json
[
  {
    "url": "http://localhost:8086",
    "token": "<unchanged>",
    "bucket": "signalk",
    "onlySelf": true,
    "useSKTimestamp": true,
    "resolution": 1000,
    "ignoredPaths": [
      "^observations\\.noaa\\.",
      "^pointsOfInterest\\.",
      "^vhfdata\\.",
      "^notifications\\.noaa\\.",
      "^environment\\.noaa\\.swpc\\.scales\\.",
      "^environment\\.forecast\\."
    ],
    "ignoredSources": [],
    "filteringRules": []
  },
  {
    "url": "http://localhost:8086",
    "token": "<same token>",
    "bucket": "signalk_archive",
    "onlySelf": true,
    "useSKTimestamp": true,
    "resolution": 60000,
    "ignoredPaths": ["<same list>"],
    "ignoredSources": [],
    "filteringRules": []
  }
]
```

`influxes` is an array and each entry is an independent writer with its own
bucket, filters and resolution, so the archive tier needs no InfluxDB task.

`ignoredPaths` takes JS regular expressions and both lists were empty, which
is why roughly 1,400 measurements of NOAA shore stations, Wikipedia points of
interest and VHF directory entries were being written to an SD card every
interval. Filtering them is a larger win on write volume than the bucket split
is. Note `ignoredPaths` is disabled entirely if `filteringRules` is non-empty
-- use one mechanism or the other, not both.

The `notifications.noaa.` entry matters for a second reason: those arrive as
`notifications.noaa.urn:oid:<unique>`, one new measurement per NWS alert,
never retired. That was the only unbounded series growth in the database.

### Turning off InfluxDB's self-scrape

If nothing is watching `influxdb` bucket data, the cheapest change of all is
to stop generating it -- InfluxDB scraping its own `/metrics` into the same
database it is trying to keep small is self-inflicted SD wear. The System
health dashboard's series-cardinality panel is the only consumer; drop that
panel and the scrape can go.

---

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

### Back up hand-installed plugins before any npm install

`~/.signalk/.npmrc` sets `package-lock=false` on the boat too, so every
install re-resolves the whole tree and deletes anything in `node_modules`
that no entry in `package.json` asks for. Plugins copied in by hand rather
than installed from the registry are exactly that, and npm removes them
without prompting.

Before installing anything in `~/.signalk`, list what is at risk:

```bash
cd ~/.signalk
npm install <pkg> --dry-run 2>&1 | grep '^remove'
```

Anything it reports is about to be deleted. Back those directories up, run
the install, then restore them and confirm they are back — the dry run only
sees what exists when you run it, so a plugin added afterwards will be
pruned without ever appearing in that list.

On 2026-08-15 this caught `signalk-plugin-watchdog` and `flaky-plugin`,
both hand-installed. The permanent fix for any plugin meant to stay is a
`file:` entry in `package.json`, which takes it out of the prune path.

---

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

> 🔴 **Critical:** Never run `npm install` over a broken tree. npm treats a
> half-written package directory as installed and skips it, so a second run
> repairs nothing.

Move the tree aside first:

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

---

## BLE sensors go silent after a reboot

Known, unfixed, and the thing most likely to confuse someone. On some boots
`bt-sensors-plugin-sk` fails its D-Bus handshake to `org.bluez` as it loads:

```
Uncaught exception: Error: write EPIPE
  at auth (.../@jellybrick/dbus-next/lib/handshake.js:67)
```

It does not retry. Every BLE sensor stays silent for the life of that process,
and nothing else in the log says anything is wrong.

Restart SignalK once the box has settled:

```bash
sudo systemctl stop signalk.socket
sudo systemctl stop signalk.service
sudo systemctl start signalk.socket
curl -s -o /dev/null http://localhost:3000/signalk/    # socket-activates it
```

It is **not** a boot-ordering race, so don't spend time there. Measured
2026-08-13 with `After=bluetooth.service` in place: bluetoothd owned the bus at
18:35:15 and the handshake still failed at 18:37:15, a hundred seconds later.
`host/signalk-after-bluetooth.conf` keeps that ordering because it is correct
hygiene, not because it fixes this.

This matters more than it looks: the hardware watchdog exists to reboot the box
when nobody is aboard, so an unattended reboot can come back with every BLE
sensor dead until someone restarts SignalK by hand. If you depend on remote
battery monitoring, either check after any reboot or add a self-healing check.

---

## A BLE sensor connects but never delivers data

bt-sensors logs `le-connection-abort-by-local` and `Unable to connect to
Bluetooth device after 5 attempts`, and nothing appears under
`electrical.batteries.<id>`.

First find out whether the radio link is forming at all:

```bash
bluetoothctl --timeout 20 scan on >/dev/null 2>&1
bluetoothctl info <MAC> | grep -E 'RSSI|Connected'
{ printf 'connect <MAC>\n'; sleep 25; printf 'quit\n'; } | bluetoothctl
```

A healthy RSSI plus `Connected: yes` immediately followed by
`le-connection-abort-by-local` and `Connected: no` means the link forms and
GATT service discovery is what dies. That pattern rules out range, the plugin
and the sensor class in one shot — don't go hunting in any of them.

None of these clear it, so don't spend time on them:

```bash
bluetoothctl power off && bluetoothctl power on
sudo hciconfig hci0 reset
sudo systemctl restart bluetooth
bluetoothctl remove <MAC>          # even followed by a fresh scan
```

Reboot the Pi. The controller is the onboard BCM4345C0 on UART, and its
firmware patch (`brcm/BCM4345C0.raspberrypi,4-model-b.hcd`) is loaded only at
boot, so nothing short of a reboot re-initialises it.

> ⚠️ **Warning:** Confirm no install is in flight first — a reboot landing on
> an `npm install` in `~/.signalk` truncates the plugin tree:

```bash
pgrep -a -f 'npm |node-gyp|apt-get|dpkg'
```

Reading BLE directly is unaffected by the plugin and is the fastest way to
tell a radio problem from a decode problem:

```bash
scripts/ble-probe.sh poll <MAC> ff02 dda50300fffd77 ff01 15   # JBD packs
```

---

## A local plugin fork keeps reverting to the registry build

`~/.signalk/node_modules/<plugin>` was a symlink to a local fork and is now a
real directory holding the registry version. Any `npm install` in `~/.signalk`
does this, and so does the app store on its own.

Relink it, with SignalK stopped:

```bash
rm -rf ~/.signalk/node_modules/bt-sensors-plugin-sk
ln -s ~/bt-sensors-plugin-sk ~/.signalk/node_modules/bt-sensors-plugin-sk
```

Then pin the exact version the fork declares, in `~/.signalk/package.json`:

```json
"bt-sensors-plugin-sk": "1.3.8-beta10"
```

Relinking without repinning buys you nothing — it will be replaced again. A
caret range like `^1.3.7` never matches a prerelease such as `1.3.8-beta10`,
because npm's semver excludes prereleases from a range unless the range names
one, so the fork permanently reads as a version needing repair. Compare the
two before assuming a link will hold:

```bash
node -e 'console.log("pin: ", require("/home/pi/.signalk/package.json").dependencies["bt-sensors-plugin-sk"])'
node -e 'console.log("fork:", require("/home/pi/bt-sensors-plugin-sk/package.json").version)'
```

Restart SignalK before judging any of this. The server keeps whatever it
loaded at startup, so swapping the directory changes nothing until it
restarts — the fork you just linked is not yet the code that's running, and a
plugin you think you're testing may be the one you replaced.

---

## When a hook blocks your commit

First, when anything here blocks you:

```bash
bash scripts/check_clone_setup.sh      # what this clone has wired, and what to do
```

It needs nothing installed and it names the fix for every gap it finds.

### Mode

Hook messages carry a `mode:` line.

- **contributor** — no age key here. A guard that can't run says so and lets
  the commit through; CI is the gate.
- **strict** — there is a key. The same guard fails instead.

Auto-detected from an age key being present *and* both git filters being
configured. To override:

```bash
SECRETGUARD_MODE=strict git commit ...       # one command, force strict
SECRETGUARD_MODE=contributor git commit ...  # one command, force contributor
echo contributor > .secretguard-mode         # pin this clone (same two words)
bash scripts/check_clone_setup.sh            # confirm: the "mode:" line at the top
```

Those two words are the whole vocabulary — `SECRETGUARD_MODE=1` is ignored,
with a message, rather than guessed at.

CI is always strict, and resolves before both of the above: a
`SECRETGUARD_MODE` exported in a workflow cannot downgrade it.
`.secretguard-mode` is gitignored — it never travels.

Two things never relax, in either mode: staging a `filter=sops` file whose
content isn't encrypted, and editing one you can't decrypt.

### When a push is blocked

`scripts/prepush_secret_scan.sh` reads every commit you are about to
publish, not just the tip — so it catches one made earlier with
`--no-verify`. Push is the irreversible moment: deleting a commit from
GitHub does not un-publish it, and on a topic branch nothing else looks
until a PR exists.

The message names a commit and a file. Then:

```bash
git show <commit>:<file>               # 1. confirm what is in there
bash scripts/setup-git-filters.sh      # 2. wire the filter, if that was the problem
git rebase -i <commit>~1               # 3. fix the commit that carries it
git push                               # 4. re-run the scan
```

Step 3 is a history rewrite, so it is only safe while the branch is
unpushed. If it is already pushed, the secret is out — go to *A secret was
committed in plaintext*, below, and rotate.

### Break glass

```bash
SKIP=<hook-id> git commit ...          # skip one hook
git commit --no-verify                 # skip all commit hooks
git push --no-verify                   # skip the pre-push scan
```

All three are legitimate and every message names the one that applies. CI's
gitleaks and trufflehog passes still run over full history on a PR. If you
push a secret past these, treat it as a leak — *A secret was committed in
plaintext*, below.

### Which check failed

In rough order of likelihood:

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

---

## Fixing openweather-signalk's mis-scaled outside humidity

`environment.outside.relativeHumidity` comes from the `openweather-signalk`
plugin and arrives as OpenWeatherMap's raw percent (e.g. `88`) instead of
SignalK's spec ratio (`0.88`) — an upstream unit-labeling bug. Every
dashboard panel on this path multiplies by 100 expecting a true ratio, so
until the upstream fix ships the outside-humidity panels read ~8800%. The
stopgap is a Node-RED flow that republishes the same path as a corrected
ratio. Node-RED already runs inside SignalK (`@signalk/signalk-node-red`).

1. Open the Node-RED editor: `https://<signalk-host>/node-red/` (or
   `http://<host>:3000/node-red/` if not behind Caddy yet).
2. Menu (☰, top right) → **Import** → paste the flow JSON below → **Import**
   to a new tab.
3. Open the **outside relativeHumidity** node and confirm its path is set to
   `environment.outside.relativeHumidity` with flattened output enabled —
   the import may not carry those fields depending on the installed node
   version; set them by hand if the fields are empty.
4. **Deploy**.
5. Verify: open the SignalK Data Browser
   (`https://<signalk-host>/admin/#/databrowser`) and confirm
   `environment.outside.relativeHumidity` reads as a ratio (`0.0`–`1.0`),
   not a raw percent. Watch it across at least one openweather poll cycle,
   since the correction only applies on the next delta after deploy.
6. Regenerate/refresh the weather and life-support Grafana panels if they
   were mid-way through a bad reading — they read live, so they self-correct
   once the corrected value lands.

Remove this flow once the upstream openweather-signalk fix ships (tracked at
github.com/inspired-technologies/signalk-openweather-plugin) — don't leave
a stopgap running past the reason it exists.

<details>
<summary>Flow JSON</summary>

```json
[
    {
        "id": "hum01tab",
        "type": "tab",
        "label": "openweather humidity fix",
        "disabled": false,
        "info": "Corrects environment.outside.relativeHumidity: openweather-signalk publishes OpenWeatherMap's raw percent (0-100) on this path instead of SignalK's 0-1 ratio (upstream bug, see github.com/inspired-technologies/signalk-openweather-plugin issue). This flow republishes the same path as a corrected ratio for any source labeled openweather. Remove this flow once the upstream fix ships."
    },
    {
        "id": "hum02sub",
        "type": "signalk-subscribe",
        "z": "hum01tab",
        "name": "outside relativeHumidity",
        "path": "environment.outside.relativeHumidity",
        "flatten": true,
        "x": 200,
        "y": 120,
        "wires": [["hum03fn"]]
    },
    {
        "id": "hum03fn",
        "type": "function",
        "z": "hum01tab",
        "name": "percent -> ratio (openweather only)",
        "func": "// openweather-signalk mislabels its 'current' humidity object as\n// unit: 'ratio' instead of '%' (confirmed in its source, skunits.js /\n// openweather.js), so its toSignalK() never divides by 100. It publishes\n// OpenWeatherMap's raw 0-100 percent straight through.\n//\n// Guard 1: only touch deltas from an openweather source, so a future\n// upstream fix (or some other source on this path) is left alone.\n// Guard 2: only divide when the value looks like a percent (> 1.5). Our\n// own corrected republish below lands back on this exact path and\n// retriggers this same subscribe node -- without this guard it would\n// halve its own output forever.\nif (!msg.$source || msg.$source.toLowerCase().indexOf('openweather') === -1) {\n    return null;\n}\nif (typeof msg.payload !== 'number' || msg.payload <= 1.5) {\n    return null;\n}\nmsg.payload = {\n    path: 'environment.outside.relativeHumidity',\n    value: msg.payload / 100\n};\nreturn msg;",
        "outputs": 1,
        "noerr": 0,
        "x": 470,
        "y": 120,
        "wires": [["hum04out", "hum05dbg"]]
    },
    {
        "id": "hum04out",
        "type": "signalk-send-pathvalue",
        "z": "hum01tab",
        "name": "republish corrected ratio",
        "x": 760,
        "y": 100,
        "wires": []
    },
    {
        "id": "hum05dbg",
        "type": "debug",
        "z": "hum01tab",
        "name": "corrected value",
        "active": false,
        "tosidebar": true,
        "console": false,
        "tostatus": false,
        "complete": "payload",
        "x": 760,
        "y": 140,
        "wires": []
    }
]
```

</details>

---

## Never use OpenPlotter's "Reinstall" for Signal K

Settings → Signal K → **Update** is safe. **Reinstall** runs `rm -rf` on
`~/.signalk` first — every plugin's configuration, `security.json`,
`settings.json`, all of it. That is deliberate on OpenPlotter's part: it
forces the first-run branch that rewrites the launcher script, which is
skipped whenever `settings.json` already exists. There is no prompt and
nothing is backed up.

If you need that branch to run — say, to regenerate the launcher after moving
Node — back up `~/.signalk` first and put the config files back afterward.
