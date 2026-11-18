# Ansible: the HALOS card's host layer

`site.yml` takes a Raspberry Pi running HALOS (Debian 13 with containerised
SignalK) from a freshly imaged, tailnet-joined card to Symphony's host
configuration. It declares the host layer and nothing above it. This file is
the map; the reason for each non-obvious choice sits in a comment beside the
task that makes it, and `reference/host_provisioning.md` explains where the
line between Ansible and everything else is drawn and why.

For the commands to run, see `runbooks/host_bringup.md` § Provisioning a HALOS
card with Ansible. For unattended runs, see `converge`.

## What a card needs before this runs

Ansible runs after these, never instead of them.

- A flashed card on the tailnet, with `pi` able to `sudo`.
  `scripts/halos_card_bootstrap.sh <lan-ip>` takes a factory image to that
  point: it installs the ssh key and moves the password onto the sops value.
- The repo checked out on the card with its git filters wired
  (`bash scripts/setup-git-filters.sh`). Filters live in `.git/config`, which is
  unversioned, so the `repo` role warns about their absence rather than fixing
  it.
- On the control machine: `ansible-core`, the `community.sops` and
  `community.general` collections, the `sops` binary, the age key at
  `~/.config/sops/age/keys.txt`, and Tailscale up. Nothing is installed on the
  card to support Ansible beyond the python Raspberry Pi OS ships.

Secrets are read from `secrets/symphony.sops.yaml` on the control machine at
run time (`group_vars/all.yml`). Tasks that handle them are `no_log`.

## Inventory

| Group | Hosts | Targeted by `site.yml` |
|---|---|---|
| `halos_cards` | `symphony-halos`, `symphony-halpi2` | yes |
| `openplotter_cards` | `symphony-pi` (current boat card) | no |

`openplotter_cards` is carried for its per-host values only; the roles assume
HALOS paths. Per-host differences live in `host_vars/`: today that is the
healthchecks.io ping URL and the sudo password key.

A card that has not joined the tailnet is reached on the LAN with
`-e ansible_host=<lan-ip>`; no address is written into the inventory.

## Roles, in run order

Order is by dependency, not topic. The reasons for each choice are comments in
the role's `tasks/main.yml`, next to the task they explain.

| Role | Owns |
|---|---|
| `pi_password` | The sudo password, moved off HaLOS's factory default; own play, runs first |
| `boot` | `config.txt`, `cmdline.txt`, `i2c-dev`, and the reboot they need |
| `can` | `can0` at 250 kbit/s through `systemd-networkd`; wait-online off |
| `network` | NetworkManager keyfiles, the hotspot profile, the tailnet node name |
| `identity` | Hostname, `/etc/hosts`, HALOS hostnames, the device certificate's names |
| `base` | InfluxData apt repo, telegraf, chrony, zram, the HALOS apps that stay down |
| `repo` | The checkout at `/home/pi/symphony` |
| `host_files` | Runs `host/install.sh`, which still writes its own `INSTALL` array |
| `watchdog` | The systemd hardware-watchdog manager settings |
| `clock` | chrony's drop-in |
| `claude_resident` | The resident Claude Code session's launcher and user unit |
| `monitoring` | Telegraf wiring and the per-card `/etc/boat-heartbeat.json` |
| `signalk_container` | The HALOS compose override and unit drop-in for SignalK |
| `front_door_cert` | A Let's Encrypt certificate for the front door; opt-in |

Three orderings carry weight:

- `boot` reboots before anything reads `/dev/i2c-1`.
- `identity` precedes the front door: it decides the certificate names.
- `monitoring` follows `host_files`, so Ansible is the last writer of the
  heartbeat file, the one file that differs per card.

## Not owned by Ansible

| Thing | Why not | Where it lives |
|---|---|---|
| SignalK's plugin tree | npm and the app store own it | `runbooks/halos_swap.md` |
| Container application config | compose plus `scripts/render.py` | `docker-compose*.yml` |
| The age key, git filters | Must arrive before Ansible can run | `runbooks/host_bringup.md` |
| The `.env`, ntfy, the Traefik router | Not yet a role | `scripts/halos_card_prepare.sh` |

## Checking a card

- `ansible-playbook site.yml --check --diff` shows what would change.
- `ansible-playbook site.yml --tags verify` audits without changing anything,
  including memory headroom.
- `scripts/halos_preflight.sh`, from a tailnet machine with sops access, checks
  the card independently of Ansible. Every line must read `ok`.
- A converge of a built card is idempotent: a second run reports
  `changed=0`. Anything else is a task that is not idempotent, or two writers
  for one path.

## Known gaps

- Every converge to date was against a card built by hand first. That proves the
  playbook describes the card, not that it can create one. The paths a
  from-blank build exercises for the first time are the boot reboot handler,
  the apt repository and package installs, the InfluxDB purge and the initial
  clone.
- `ansible.builtin.apt_repository` is deprecated and removed in ansible-core
  2.25. Its replacement writes `influxdata.sources` rather than
  `influxdata.list`, so moving is a deliberate step for both cards. The warning
  is left visible so it keeps the migration on the board.
- The current boat card (`symphony-pi`) has no roles; it is inventory-only.
- A role owns whole paths. Where `host/install.sh` still writes a path, the path
  stays out of the role until its installer entry is removed; two writers for one
  file is what this tree is organised to avoid.
