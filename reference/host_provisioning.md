# Host provisioning

How a boat computer gets from a blank card to a running host, why that moved to
Ansible, and what Ansible should and shouldn't own.

## What exists now

`ansible/` provisions the host layer of a HALOS card, ported from the plan-v1
as-built record and converged against `symphony-halos` on 2026-09-02 (two
consecutive runs at `changed=0`). Nine roles cover boot config and `can0`,
NetworkManager and hostname/certificate identity, packages and swap, the repo
checkout, `host/install.sh`, telegraf and the heartbeat, and the SignalK
container overrides. `RUNBOOK.md` → "Provisioning a HALOS card with Ansible" is
how to run it.

The two mechanisms that preceded it are both still in place, and one of them is
still authoritative:

**`RUNBOOK.md` → "Bringing up a host"** is four phases of commands typed by
hand: tooling (Docker, pre-commit, sops, age), key material, repo and git
filters, then services. It is accurate and it works, but it is a procedure a
person executes, so it drifts from what the hosts actually have and it cannot
tell you whether a host is currently in the state it describes.

**`host/install.sh`** is a deliberately small stopgap. It copies files from
`host/` to fixed destinations with an owner and mode, restarts the services
whose config it just placed, enables system units, enables `pi`'s user units,
and owns a couple of root cron lines. What it explicitly does not do is
install packages — every prerequisite is a manual `apt install` recorded in
the RUNBOOK. It is idempotent and it is honest about its scope; it is also a
hand-rolled 130-line configuration manager, which is the thing worth
replacing.

## Why now rather than after the migrations

Two moves are planned — native systemd services to Docker, and the Pi 4B to a
HALPI2 (`compute_hardware.md`). Neither changes the host layer. The clock, the
watchdog, cron and timers, gpsd, users and groups, kernel modules, the SD-card
mount options: all of it is outside any container and all of it comes along
unchanged. Work done here is not thrown away by either migration, and the
HALPI2 move is precisely the moment a repeatable host build stops being a
convenience.

## `marinepi-provisioning` is upstream, not ours

`README.md` refers to "the SignalK/Ansible repo." That is
[tkurki/marinepi-provisioning](https://github.com/tkurki/marinepi-provisioning),
Teppo Kurki's own project, cloned locally for reference. It is not a place
Symphony's provisioning can live: it belongs to someone else, and its newest
commit pins Node 18 while this boat runs Node 22.

It is still worth reading before writing anything. Roles that map onto
problems this boat actually has:

| Role | What it solves here |
|---|---|
| `root-ro` | Overlayfs read-only root. The SD card is the component most likely to fail first, and this is the standard mitigation. |
| `rtc` | `dtoverlay=i2c-rtc,ds3231` plus a udev rule to set system time from the RTC at boot. Directly answers this box having no RTC. |
| `mcp2515-can` | CAN interface bring-up. The PiCAN-M's `can0` is configured by hand today. |
| `unattended_upgrades` | Nothing patches this box on a schedule right now. |
| `common`, `node`, `signalk-npm` | Reference for shape and ordering, not for direct use. |

## Shape

An `ansible/` directory **in this repo**, not a new one. The playbooks need
`secrets/symphony.sops.yaml`, the rendered `.env`, the compose files and
`host/`'s file contents; splitting them from those inputs means either
duplicating the golden config or wiring two repos together for every change.
This repo already carries infrastructure alongside the maintenance log, so
this is not a new kind of thing for it.

Built layout. Roles are named for what they own and ordered by dependency, not
by the as-built's section headings:

```
ansible/
  inventory.yml          # halos_cards: symphony-halos, over Tailscale
                         # openplotter_cards: symphony-pi, inventory-only
  site.yml
  roles/
    boot/                # config.txt, cmdline.txt, i2c-dev, the reboot
    can/                 # 80-can.network, networkd, wait-online off
    network/             # NetworkManager keyfiles, the AP, the tailnet name
    identity/            # hostname, /etc/hosts, HALOS hostnames + certs
    base/                # apt repo and packages, zram, the stay-down apps
    repo/                # the checkout at /home/pi/symphony
    host_files/          # invokes host/install.sh
    monitoring/          # telegraf wiring, per-host heartbeat config
    signalk_container/   # the two HALOS override files
```

The `clock`, `watchdog` and `claude-resident` roles this file originally
proposed are **not** here: their contents are still inside `host/install.sh`,
which `host_files` invokes. Porting them is the next slice, and it is the point
at which `install.sh` starts to shrink.

`monitoring` runs after `host_files` so that Ansible, not the installer, is the
last writer of `/etc/boat-heartbeat.json`. That file is the one place the two
cards genuinely differ — they ping two different healthchecks.io checks — and
`install.sh` copying one card's copy onto the other is how a card went quiet
with nothing alarming.

### What Ansible owns

The host layer, and only the host layer: packages, users and groups, kernel
modules and device-tree overlays, systemd unit and manager config, timers and
cron, mount options, network interfaces including `can0`, and the contents of
`host/`.

### What it must not own

- **SignalK's plugin tree.** `~/.signalk/node_modules` is npm's and the app
  store's. An Ansible task that writes there is a third writer racing the
  other two, which is how the tree got wrecked in the first place
  (`legacy_openplotter_stack.md`).
- **Container application config.** That is compose plus `render.py`.
- **The age private key and git filters.** Phases 2 and 3 of "Bringing up a
  host" are bootstrap: the key has to arrive out of band, and git filters live
  in `.git/config`, which is deliberately unversioned. Ansible can run after
  those, never instead of them.

## Migration path

`install.sh`'s arrays map onto Ansible one-for-one — `INSTALL` to `copy`
tasks, `RESTART` and `ENABLE` to handlers and `systemd` tasks, `CRON` to
`cron`. Port them role by role, keep `install.sh` working the whole time, and
retire it only once a run of `site.yml` against a fresh card reproduces the
box. Until then the two must not both own a file: whichever one is authoritative
for a given path should be the only one that writes it.

## Open decisions

- Which host runs the playbooks. Answered provisionally by use: a laptop over
  Tailscale, which is easier to iterate on and useless with no uplink. The boat
  Pi could run them against `localhost` with no control machine, which works
  offshore, but it would need Ansible and the age key on it. Doing both is
  normal; nothing here prevents it.
- Whether the boat card gets roles of its own. It is in the inventory with its
  own heartbeat URL, in a group no play targets, because these roles assume
  HALOS paths.
- Whether to adopt `root-ro`. A read-only root is the strongest available
  answer to SD-card wear, and it makes every write an explicit decision —
  which is a real change to how the box is worked on, not just a config
  toggle.
- Whether the HALPI2 gets built by these playbooks from day one, or by hand
  first and captured afterward.
