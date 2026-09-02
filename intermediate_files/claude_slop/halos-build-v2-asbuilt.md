# HALOS trial card — as-built, plan v2 (Ansible)

As-built record of plan v2: the same card as v1 (`symphony-halos`, hostname
`signalk`, Raspberry Pi 4 Model B Rev 1.5, image
`ghcr.io/halos-org/signalk-server-docker:v2.31.1-halos.3` on HALOS / Debian 13),
rebuilt as `ansible/` on 2026-09-02. v1's Base OS, Network, Host services and
SignalK container layers are now roles; the SignalK state layer is unchanged and
stays a documented procedure.

Where v1 recorded *what was typed*, v2 records *what is declared* — each step
below names the file that holds it, and every one of them was run against
`symphony-halos` over Tailscale. Tags carry the same meaning as in v1, plus one
new one:

- `[artifact: path]` — the thing itself lives at that path in the repo.
- `[narrative]` — recorded here, nowhere else.
- `[checked: script]` — that script verifies it independently.
- `[verified: run N]` — observed in one of the four converge runs below.

Sources: `halos-build-v1-asbuilt.md` (the plan being ported),
`reference/host_provisioning.md` (what Ansible may and may not own),
`host/install.sh`, `host/halos/README.md`, `scripts/halos_preflight.sh`.

## Runs

Four converge runs against the live card, plus two `--check` passes before them.

| Run | Command | Result |
|---|---|---|
| check 1 | `ansible-playbook site.yml --check --diff` | failed 1 — found two bugs (below) |
| check 2 | same, after fixes | `ok=58 changed=4 failed=0` |
| 1 | `ansible-playbook site.yml --diff` | `ok=61 changed=5 failed=0`, 2 min 31 s |
| 2 | same again | `ok=59 changed=1 failed=0` — one task not yet idempotent |
| 3 | `-e symphony_repo_version=claude/ansible-symphony-halos-43cf78` | `ok=60 changed=0 failed=0` |
| 4 | same again | `ok=60 changed=0 failed=0` |

Runs 3 and 4 are the acceptance evidence: **two consecutive converges with
`changed=0`**. Runs 1 and 2 still showed one change per run because the card's
checkout was on `main`, whose `host/install.sh` predates the `keep` flag in step
23 and so rewrote `/etc/boat-heartbeat.json` on every run for Ansible to rewrite
back. `scripts/halos_preflight.sh` returned every line `ok` afterwards.

## Prerequisites — not Ansible's

Unchanged from v1 and deliberately outside the playbooks
(`reference/host_provisioning.md` § What it must not own).

1. On the **control** machine: `ansible-core` (2.21.3 used here), the `sops`
   binary, the age private key at `~/.config/sops/age/keys.txt`, Tailscale up,
   and ssh to `pi@symphony-halos` on a key. Nothing is installed on the card to
   support Ansible beyond the python Raspberry Pi OS already ships. `[narrative]`

2. The card is flashed, on the tailnet, and `pi` can `sudo`. The sudo password
   comes from sops key `symphony_halos_pi_password` via
   `ansible_become_password`. `[artifact: ansible/host_vars/symphony-halos.yml]`

3. The repo checkout on the card needs its git filters wired
   (`bash scripts/setup-git-filters.sh`). The age key has to arrive out of band
   and git filters live in `.git/config`, which is unversioned, so Ansible
   warns about their absence rather than fixing it.
   `[artifact: ansible/roles/repo/tasks/main.yml]`

## Base OS / boot config

Role `boot` (v1 steps 2–4, 8) and role `can` (v1 steps 5–7).

4. `/boot/firmware/config.txt`: `dtparam=i2c_arm=on`, `dtparam=spi=on`,
   `enable_uart=1` and the two overlays, inserted after `[all]`.
   `[artifact: ansible/roles/boot/tasks/main.yml]` `[checked: scripts/halos_preflight.sh]`
   `[verified: run 1]`

   Each line is matched by its own key so a re-run edits in place. The first
   `--check` pass caught the bug that made this necessary: keying on
   `item.split('=')[0]` gives `dtparam` for all three dtparam lines, so each
   loop item overwrote the previous item's line — the diff showed
   `dtparam=spi=on` being replaced by `dtparam=i2c_arm=on`. `dtparam` is a
   namespace, not a key; the fix is `rsplit('=', 1)[0]`. `[narrative]`

5. `/boot/firmware/cmdline.txt`: `cfg80211.ieee80211_regdom` set to `US`, and
   `cgroup_enable=memory cgroup_memory=1` appended. cmdline.txt is one line, so
   a parameter is added by appending to that line; the idempotence comes from a
   negative lookahead rather than from `lineinfile`.
   `[artifact: ansible/roles/boot/tasks/main.yml]` `[checked: scripts/halos_preflight.sh]`

6. `/etc/modules-load.d/i2c-dev.conf` contains `i2c-dev`.
   `[artifact: ansible/roles/boot/tasks/main.yml]` `[checked: scripts/halos_preflight.sh]`

7. Reboot, if and only if one of steps 4–6 changed, then verify against the
   **running** kernel — `/dev/serial0`, `/dev/i2c-1`, `memory` in
   `/sys/fs/cgroup/cgroup.controllers`, `regdom=US` in `/proc/cmdline`. The role
   flushes its own handler so later roles never run against a stale kernel.
   `-e symphony_allow_reboot=false` turns the reboot into a warning.
   `[artifact: ansible/roles/boot/handlers/main.yml]` `[verified: run 1]`

8. `/etc/systemd/network/80-can.network` — 250 kbit/s, `RestartSec=100ms`.
   `[artifact: ansible/roles/can/files/80-can.network]`

9. `systemd-networkd` enabled and started; `systemd-networkd-wait-online`
   disabled and stopped. `[artifact: ansible/roles/can/tasks/main.yml]`
   `[checked: scripts/halos_preflight.sh]`

10. `can0` is reported, not asserted: the PiCAN-M HAT is on the boat, so an
    absent `can0` on the bench is expected rather than a failure.
    `[artifact: ansible/roles/can/tasks/main.yml]` `[verified: run 1]`

## Network

Role `network` (v1 steps 9–11, 16) and role `identity` (v1 steps 12–15, 17).

11. NetworkManager keyfiles `Symphony` and `Symphony_5G` written from sops keys
    `nm_symphony_nmconnection` and `nm_symphony_5g_nmconnection`, 0600 root:root,
    `no_log`. NetworkManager silently refuses a keyfile that is group- or
    world-readable. `[artifact: ansible/roles/network/tasks/main.yml]`
    `[checked: scripts/halos_preflight.sh]`

    This closes v1 step 9's `[command not recorded]`.

12. `Halos-AP.nmconnection` is edited field-by-field, not replaced: `wifi.ssid`
    to `SignalK`, `wifi-security.psk` to the `psk=` line extracted from sops key
    `nm_signalk_hotspot_nmconnection`. HALOS owns that file; editing two fields
    means a HALOS update that adds a setting is not silently reverted.
    `[artifact: ansible/roles/network/tasks/main.yml]`
    `[checked: scripts/halos_preflight.sh]`

    This closes v1 step 10's `[command not recorded]`. The sops key holds the
    boat card's whole `SignalK-Hotspot` keyfile; only the pre-shared key
    transfers, because the rest of it describes the boat card's radio. `[narrative]`

13. `nmcli connection reload` as a handler — reload, not restart, so the wifi
    association the play is running over survives.
    `[artifact: ansible/roles/network/handlers/main.yml]`

14. Tailnet node renamed to `symphony-halos`, but only when
    `tailscale status --json` says it is not already that. Renaming keeps the
    node key and the tailnet IP. `[artifact: ansible/roles/network/tasks/main.yml]`

15. Hostname `signalk`; `/etc/hosts` 127.0.1.1 line reads
    `signalk.<boat_domain> signalk`. FQDN first is what makes `hostname -d`
    answer, which is step 1 of HALOS's domain resolution chain — short name
    first and the whole chain falls through to DHCP option 15.
    `[artifact: ansible/roles/identity/tasks/main.yml]`
    `[checked: scripts/halos_preflight.sh]`

    This closes v1 steps 13–14's `[command not recorded]`.

16. `/etc/halos/hostnames.conf` copied whole, vendor comment header included,
    with the active tail `${fqdn}` / `${hostname}.local` / `${domain}`.
    `[artifact: ansible/roles/identity/files/halos-hostnames.conf]`

    Copied whole rather than edited because the file is a dpkg conffile: owning
    only the active lines means either markers inside a file HALOS parses, or a
    rewrite that drops its documentation. The cost is that a HALOS update to the
    header is re-asserted away on the next converge; the header is entirely
    comments, so this is cosmetic. `[narrative]`

17. Handlers, in order: restart `halos-resolve-domain` then
    `halos-core-containers`, then start `halos-manage-certs`.
    `[artifact: ansible/roles/identity/handlers/main.yml]`

18. Verify `/run/halos/domain.env` names this card, and that the device
    certificate's SANs cover `signalk.local`, `signalk.<boat_domain>` and
    `<boat_domain>`. Both are assertions, not reports: a wrong name here means
    SSO fails on the name people actually type.
    `[artifact: ansible/roles/identity/tasks/main.yml]` `[verified: run 1]`

## Host services

Role `base` (v1 steps 18, 20, 21, 25), role `repo` (v1 step 22, first half),
role `host_files` (v1 steps 22–23), role `monitoring` (v1 steps 19, 24).

19. InfluxData signing key installed to `/etc/apt/keyrings/influxdata-archive.gpg`
    from a copy carried **in the repo**, then the apt source
    `deb [signed-by=…] https://repos.influxdata.com/debian stable main`.
    `[artifact: ansible/roles/base/files/influxdata-archive.gpg]`

    This closes v1 step 18's `[command not recorded]`. The key is carried rather
    than fetched because every rebuild failure on this boat has been a network
    timeout on its cellular link, not a logic error. Fingerprint, checked against
    InfluxData's published value:
    `24C9 75CB A61A 024E E1B6 3178 7C3D 5715 9FC2 F927`. `[narrative]`

20. `telegraf` and `chrony` installed. chrony's install removes
    `systemd-timesyncd`, which is wanted: timesyncd cannot step a clock that is
    hours out, which is the state a card with no RTC boots into.
    `[artifact: ansible/roles/base/tasks/main.yml]`

21. `systemd-zram-generator` installed and `/etc/systemd/zram-generator.conf`
    written: `zram-size = min(ram / 2, 1024)`, `compression-algorithm = zstd`,
    `swap-priority = 100`. `[artifact: ansible/roles/base/files/zram-generator.conf]`

    This closes v1 step 25's `[command not recorded]`. `min(ram/2, 1024)` gives
    the 2 GB bench card and the 4 GB boat card the same 1 GB, so the two behave
    alike under memory pressure. `[narrative]`

22. `marine-influxdb-container` purged, not removed — `remove` leaves a unit
    that starts at boot, fails, and gets reported by the heartbeat.
    `marine-avnav-container` and `marine-opencpn-container` disabled and stopped,
    tolerating their absence on a card that never had them.
    `[artifact: ansible/roles/base/tasks/main.yml]`
    `[checked: scripts/halos_preflight.sh]`

23. The repo checked out at `/home/pi/symphony`, as `pi`, with `force: false`.
    Never forced: a checkout on a card is not disposable, filtered files read as
    modified whenever the filters are not wired, and a reset would delete
    whatever a session left there. The ref is a variable
    (`symphony_repo_version`, default `main`) so a card can be converged against
    a branch. `[artifact: ansible/roles/repo/tasks/main.yml]`

24. Before that checkout: anything under `/home/pi/symphony` not owned by `pi` is
    given back to `pi`. `[artifact: ansible/roles/repo/tasks/main.yml]`
    `[verified: run 3]`

    Found on this card during run 3. A `sudo git` during the v1 build had left
    `.git/refs/heads/claude/`, the pack files and `.git/config` root-owned, so
    `pi` could not create any branch under `claude/` at all. Git reports it as a
    lock file it cannot create — "Unable to create '…/x.lock': Permission
    denied" — which reads like a stale lock rather than an ownership problem, and
    cost most of an hour to recognise. Repaired in the role rather than by hand,
    because the next root git command puts it straight back. `[narrative]`

25. `host/install.sh` run from the checkout. Ansible does **not** reimplement it:
    it stays the authoritative writer for its whole `INSTALL` array — the
    watchdog drop-in, chrony's conf.d file, the heartbeat and BLE-check units and
    timers, the apt unattended-upgrade confs.
    `[artifact: ansible/roles/host_files/tasks/main.yml]` `[verified: run 1]`

26. That run exits 1 on a HALOS card, at the `claude-resident` user unit, under
    `set -e`. Tolerated **by name**, so any other failure still fails the play,
    and reported as a message saying exactly what was lost: the root crontab
    section, whose only entry is a deliberately commented-out nightly reboot.
    `[artifact: ansible/roles/host_files/tasks/main.yml]` `[verified: run 1]`

    v1 step 23 recorded that this step fails but not that `set -e` makes it abort
    the rest of the script. `[narrative]`

27. `/etc/telegraf/telegraf.conf` symlinked to
    `/home/pi/symphony/telegraf/telegraf.conf`, and
    `/etc/systemd/system/telegraf.service.d/override.conf` written with
    `User=pi`, `Group=pi`, `Type=simple`. Handler restarts telegraf.
    `[artifact: ansible/roles/monitoring/tasks/main.yml]`
    `[checked: scripts/halos_preflight.sh]`

    This closes v1 step 19's `[command not recorded]`.

28. **`/etc/boat-heartbeat.json` templated per host**, 0600 root, `no_log`, from
    `heartbeat_url` in that host's vars plus the shared Pushover credentials.
    `[artifact: ansible/roles/monitoring/templates/boat-heartbeat.json.j2]`
    `[verified: runs 1–4]`

    This is the carded fix, and it closes v1 step 24's `[command not recorded]`.
    The two cards ping two different healthchecks.io checks and
    `host/boat-heartbeat.json` has room for one URL, so `host/install.sh`'s
    unconditional copy meant whichever card ran the installer last silently took
    over the other's check — and the card that lost it went quiet with nothing
    alarming, because the check itself was still being pinged. Three changes:

    - the two ping URLs are now sops keys `heartbeat_url_symphony_pi` and
      `heartbeat_url_symphony_halos`, recovered from the healthchecks.io API
      (v1 recorded the halos one as held nowhere);
    - `ansible/host_vars/*.yml` names which card gets which;
    - `host/install.sh`'s `INSTALL` array gained a trailing `keep` flag, and the
      heartbeat file carries it, so the installer leaves an existing copy alone
      and prints `(kept, already installed)`.
      `[artifact: host/install.sh]` `[verified: run 4]`

    `monitoring` also runs **after** `host_files` so Ansible is the last writer
    regardless — true even against a card whose checkout predates the `keep`
    flag, which is exactly what runs 1 and 2 demonstrated.

29. Verification: `telegraf` and `chrony` active, `chronyc tracking`, the two
    installer timers active, and the last `boat-heartbeat` journal line.
    `[artifact: ansible/roles/base/tasks/main.yml, ansible/roles/monitoring/tasks/main.yml]`

## SignalK container

Role `signalk_container` (v1 steps 27–30).

30. `/etc/container-apps/marine-signalk-server-container/symphony.override.yml`
    placed from `host/halos/signalk-healthcheck-override.yml`.
    `[artifact: ansible/roles/signalk_container/tasks/main.yml]`
    `[checked: scripts/halos_preflight.sh]` `[verified: run 1]`

31. `/etc/systemd/system/marine-signalk-server-container.service.d/symphony.conf`
    placed from `host/halos/signalk-unit-override.conf`.
    `[artifact: ansible/roles/signalk_container/tasks/main.yml]`

    Both source files stay in `host/halos/` rather than being copied into the
    role. Duplicating a file whose failure mode is silence is how the two copies
    drift. This role is now what places them, which replaces "place them by hand"
    in `host/halos/README.md`. `[narrative]`

32. Handler, in v1 step 29's order: `systemctl reset-failed`, then restart with
    `daemon_reload`. A unit that hit its start limit refuses to restart until it
    is reset, and the refusal reads like the restart simply did nothing.
    `[artifact: ansible/roles/signalk_container/handlers/main.yml]` `[verified: run 1]`

33. Verify, as an assertion rather than a report: `docker exec signalk-server
    python3 -c "open('/dev/i2c-1')"` returns 0, `GroupAdd` contains `988`,
    `Healthcheck.StartPeriod` is 900 s.
    `[artifact: ansible/roles/signalk_container/tasks/main.yml]` `[verified: run 1]`

    Observed: `i2c reachable in-container; gid 988 present; 900 s start window`.
    Asserted rather than printed because both settings fail silently — without
    gid 988 the BME680 tree stays empty, which is indistinguishable from the
    normal ~10 minute post-restart burn-in.

## SignalK state — still a script, deliberately

34. v1 steps 31–42 are unchanged and stay a documented procedure: save HALOS's
    `package.json`, rsync the boat's `.signalk` twice, install the two local
    plugin forks and pin them in `package.json`, stop the memory-hungry units,
    `npm install --ignore-scripts` in a throwaway `node:24-bookworm` container,
    `npm rebuild` the five named native packages, the four `"enabled": false`
    edits, the Cerbo MQTT host, and the stray watchdog config removal.
    `[artifact: intermediate_files/claude_slop/halos-build-v1-asbuilt.md]`

    Not ported, on the owner's instruction and for the reason
    `reference/host_provisioning.md` gives: `~/.signalk/node_modules` belongs to
    npm and the app store, and an Ansible task writing there is a third writer
    racing the other two — which is how the tree got wrecked in the first place.
    `[narrative]`

## Layers not in scope for v2

35. v1 steps 43–47 (`.env`, ntfy, the Traefik host router, the bench-only
    stop of QuestDB and Grafana), 48–50 (boat-side: the Cerbo DHCP reservation,
    the two dead units, the second healthchecks.io check) and 51–54
    (verification) are unchanged and still run as v1 records them. The Traefik
    router file is the one `[artifact]` among them and is a candidate for a
    tenth role; it was left out because the brief named four layers. `[narrative]`

## What v2 changes about the card

Nothing functional. Converging an already-built card produced exactly three
diffs, all benign:

- the checkout moved from `76683e7` to the tip of `main`;
- `/etc/boat-heartbeat.json` was reformatted — three identical values, different
  whitespace and key order;
- `host/halos/signalk-healthcheck-override.yml`'s **comment block** differed
  from the copy on the card, which notified the unit restart. The `services:`
  body was byte-identical.

`scripts/halos_preflight.sh` returned every line `ok` afterwards, including
`mem 337 MB available`.

## Not recorded

- The `.env` creation command (v1 step 43) — still open.
- The halos-card healthchecks.io check's **name-to-UUID mapping** is now
  recoverable from the API with sops key `healthchecks_api_key`, but the API
  call itself is not part of any script.
- Which sops age key was used to build the card originally.

## Left behind on the card

- Local branch `salvage/ansible-partial-checkout` (commit `a6ea802`) at
  `/home/pi/symphony`. Run 3's first attempt failed mid-`git checkout` on the
  ownership problem in step 24 and left a partially-staged tree; rather than
  discard it, it was committed to that branch. Its content is exactly the PR
  branch's tree, so it is reproducible and safe to delete. Never pushed.

## Not done in v2

- **`host/install.sh`'s own contents are not roles yet.** The `clock`,
  `watchdog`, `monitoring` and `claude-resident` roles that
  `reference/host_provisioning.md` proposes are still inside the installer; role
  `host_files` invokes it. This is the next slice and it is already carded.
- **The boat card (`symphony-pi`) is inventory-only.** It is in `inventory.yml`
  with its heartbeat URL in `host_vars`, in group `openplotter_cards`, which no
  play targets. The roles assume HALOS paths.
- **A genuinely fresh card has not been built by this playbook.** Every run
  above converged a card v1 had already built by hand, which proves the
  playbook *describes* the card but not that it can *create* one. Steps
  sensitive to that difference: 4–7 (the reboot handler has never actually
  fired), 19–20 (the apt repo and packages were already installed), 22 (purging
  an InfluxDB app that was already absent), 23 (a clone rather than a pull).
- `ansible.builtin.apt_repository` is deprecated and goes away in ansible-core
  2.25. Its replacement writes `influxdata.sources` rather than
  `influxdata.list`; both cards carry the `.list` form, so moving is a separate,
  deliberate step. Deprecation warnings are off in `ansible.cfg` because of it.
- pypilot, QuestDB history migration, Grafana provisioning, Dex and Caddy — all
  as v1 left them.
