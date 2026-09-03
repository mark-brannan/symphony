# Rebuilding the HALOS card from a fresh image — what is and isn't repeatable

Written 2026-09-03 from a read of every as-built and Ansible file, plus an
upstream check of HALOS itself. Nothing here has been run against a fresh
card yet; the second card (imaged with `Halos-Marine-RPI_2026-08-20.0.img.xz`,
Raspberry Pi Imager, **no OS customisation** — HALOS's README says so) is the
control for that test.

## Short answer

No, not today. Ansible reproduces the **host layer** and has converged the
bench card four times (`ok=60 changed=0`), but it has never created a card:
every run started from a card v1 had already built by hand. The **SignalK
state layer** (the boat's `.signalk` copy, the two local forks, the
`package.json` pins, the Node-24 npm build) is procedure with one unrecorded
command, and the HALOS **app-store layer** is assumed to be there because the
image shipped it.

## Upstream facts that shape a rebuild

- Image: `Halos-Marine-RPI` from `github.com/halos-org/halos-pi-gen/releases`,
  Debian 13 Trixie, arm64, flashed with Imager "Use custom", customisation off.
- SSH on by default in headless images. Default login is reported as both
  `pi`/`halos` (halos-distro README) and `pi`/`raspberry` (Hat Labs docs) —
  try `halos` first; first boot should change it to the sops value.
- No first-boot wizard; config is Cockpit at `:9090` and the dashboard at `/`.
  No preseed/cloud-init mechanism documented.
- Not found upstream: whether `pi` is in `docker` (it is not on the bench),
  whether sudo is passwordless (it is not), whether `cgroup_enable=memory` is
  on by default (it was not on the bench), any auto-update timer.

## Gaps, ranked by how badly a rebuild goes without them

1. **The npm build recipe is unrecorded.** `halos-b3-findings-2026-09-02.md`
   describes it (throwaway `node:24-bookworm` container writing into `$D`,
   `npm install --ignore-scripts`, named `npm rebuild`s, under
   `systemd-run`) but the literal commands were never captured. Without it the
   BME680, i2c and sqlite-backed plugins load nothing and say nothing.
   *Fix:* write the recipe as `scripts/halos_signalk_npm.sh` and run it once
   on the fresh card.
2. **The HALOS app layer is assumed.** Roles `signalk_container` and the
   preflight expect `marine-signalk-server-container`, QuestDB, Grafana,
   Homarr, Authelia, Traefik, autoheal and the port registry (SignalK on
   4430). The Marine image ships SignalK, Grafana, InfluxDB, AvNav; whether
   QuestDB and Homarr are in the image or were `apt install`ed by Mark is
   unknown. *Fix:* on the fresh card, `dpkg -l 'marine-*' 'halos-*'` before
   anything else and record the delta against the bench card.
3. **`.env`** — copied from `.env.example` by hand; without it compose refuses
   the project file, so no ntfy, no pypilot. Not in Ansible.
4. **Second healthchecks.io check** — the URL is in sops, but nothing creates
   the check; a third card would ping nothing or the wrong one.
5. **pypilot calibration data** — exists on the boat card only; the copy is a
   manual root-to-root tar. Not in Ansible.
6. **Boot chain never exercised by Ansible** — the reboot handler and the
   running-kernel verify (`roles/boot`) have never fired, because the card
   already had the lines.
7. **Silent pre-plan assumptions** — Tailscale joined and authorised (Ansible
   only renames), SSH key or Tailscale SSH from the control box, the `pi`
   password set, HALOS's Authelia user created, `Halos-AP.nmconnection`
   existing under that name.
8. **The two legs no rebuild can do at home** — `can0` with the HAT, and BLE
   with the boat's sensors in range. Vcan (`RUNBOOK.md` § A fake can0) covers
   the socket path; BLE only the D-Bus reachability.

## Requirements before the first boot

- **Wired Ethernet to a network with internet, plugged in before power-on.**
  Not optional. Two reasons, both measured 2026-09-03: a fresh image has no
  WiFi credentials (and HALOS says not to use the imager's customisation),
  and **the image ships no container images at all** — SignalK
  (`ghcr.io`), Authelia, Traefik and Homarr (Docker Hub) are all pulled on
  first boot. With no network, `halos-core-containers` and
  `marine-signalk-server-container` fail, hit systemd's start limit, and the
  card sits with nothing running. So a HALOS card can never be built at the
  boat; the pull alone is several GB. Once the cable is in:
  `sudo systemctl reset-failed && sudo systemctl restart --no-block halos-core-containers marine-signalk-server-container`.
- The image's clock starts at its build date (2026-08-20) until NTP reaches
  it; journal timestamps from the first minutes are wrong.
- Image baseline (`Halos-Marine-RPI_2026-08-20.0`): apps shipped are
  `marine-signalk-server-container` 2.31.1-5 and Homarr only — **no QuestDB,
  Grafana, InfluxDB, AvNav or OpenCPN**; those on the bench card were
  installed by hand. No tailscale, telegraf, chrony or unattended-upgrades;
  `systemd-zram-generator` is present. sudo is passwordless for `pi` (the
  bench card's password prompt was added later). `pi` is not in `docker`.
  cmdline has `regdom=GB` and no memory cgroup; config.txt has no i2c/spi/
  uart/CAN lines; networkd disabled; journal volatile; timezone
  Europe/London; port registry `signalk-server=4430`.

## First attempt, 2026-09-03 — stopped at step 0

The fresh card booted (green activity, then idle) and never appeared on the
LAN. The bench Pi reaches the house network over WiFi, through a profile that
exists only on the payload card; a fresh HALOS image has no WiFi credentials
and HALOS's README says not to use the imager's customisation. So the very
first step of a rebuild, before anything in this repo, is one of:

- **Wired Ethernet** from the Pi to the router for the first boot (the plan
  assumes this and never says so), or
- a laptop joined to HALOS's own default hotspot (`Halos-AP`, comes up on
  `wlan0ap` by default) to add a WiFi profile through Cockpit, or
- a deliberate test of the imager's WiFi/SSH customisation on a HALOS image,
  to learn what "do not apply" actually protects against.

Unrelated to that: unpowered HDMI monitors were cabled to the bench Pi during
the first boot and were removed as a variable.

## Ansible against the fresh card, 2026-09-03 — what broke, what was fixed

Run with a scratch inventory pointing `symphony-halos` at the card's LAN IP
(`ansible_host`, `ansible_user: pi`, host-key checking off), after
`ssh-copy-id` with the image's default password and `chpasswd` to the sops
value. Each run stopped at the first fatal; each fatal became a role fix:

1. **Boot role: a staged-but-not-rebooted card can never pass.** Run 1 was
   deliberately `symphony_allow_reboot=false` (image pulls in flight); run 2
   then found `changed=0`, notified no handler, and failed the running-kernel
   verify. Fixed: the verify registers its result and reboots the card
   itself when the files are right and the kernel is not. Run 3 rebooted and
   passed the boot role.
2. **Network role verified before its reload handler ran.** Keyfiles on
   disk, `nmcli` unaware, assertion failed. Fixed: `flush_handlers` before
   the verify.
3. **Network role assumed tailscale.** Fixed earlier today: the rename is
   skipped with a message when `/usr/bin/tailscale` is absent.
4. **The handler-based reload had the same flaw as the boot reboot**: a run
   that wrote the keyfiles and stopped left them unread, and the next run
   (`changed=0`) never reloaded. Fixed: unconditional `nmcli connection
   reload` before the verify.
5. **The sops WiFi keyfiles pin `mac-address=` to the boat Pi's radio.** On
   the bench Pi the `Symphony` profile loads but can never activate; same on
   a Pi 5 or HALPI2. Invisible on the boat, where the MAC matches. Fixed: the
   role strips the pin when it writes the file.
6. **Identity role's SAN probe raced Traefik's restart** (six seconds after
   the handler). The certificate was right moments later. Fixed: the probe
   retries for a minute.
7. **Monitoring role assumed `/etc/systemd/system/telegraf.service.d/`
   exists.** It did on the bench card (v1 made it by hand). Fixed: the role
   creates it. Base and repo roles passed on the fresh card without change.
8. **`host/install.sh` aborted at the telegraf restart**, before enabling any
   timer, and the host_files role's "stopped at claude-resident" note
   misreported it. On a fresh card telegraf has no usable config until the
   monitoring role runs *after* host_files. Fixed: a failed restart is
   reported and the installer continues (non-zero exit at the end); it also
   flushes the journal after restarting journald so `Storage=persistent`
   takes effect without a reboot. Rerun: both timers active.

After eight fixes: `site.yml` converges on a fresh card, `ok=67 failed=0`,
and `scripts/halos_preflight.sh <lan-ip>` reads ok on boot, wifi, hotspot,
can, signalk (override + gid), containers, front, mem. Still FAIL, by design
of what the play owns: host (no tailscale), state/plugins (SignalK state),
services (no QuestDB/Grafana in the image), ntfy, questdb, journal (until the
flush fix landed).

## SignalK state layer on the fresh card, 2026-09-03

Boat `.signalk` (rsync via the dev box, since the fresh card is not on the
tailnet), both forks into `local-plugins/`, the two `file:` pins, four
plugin disables, `venus.json` host edit — then the recipe as a script:
`sudo scripts/halos_signalk_npm.sh` under `systemd-run`. **Install plus the
named native rebuilds: 18 min 52 s, exit 0, SignalK unit restarted.** The
recipe that was "not recorded" is now `scripts/halos_signalk_npm.sh` and has
run once on a fresh card.

Preflight against it, same evening — the build did what it was meant to:

```
ok    plugins    120 loaded, 63 on; same set and states as the boat except the 4 expected-off and 3 image-only; forks pinned, D-Bus fix present
ok    state      config files and installed plugin versions match the boat (forks, expected-off and venus skipped)
ok    signalk    active 2.31.1 override gid988
ok    boot / wifi / hotspot / can / staydown / heartbeat / containers / ntfy / front / mem / dns
FAIL  host       no tailscale on this card (by design; it is not on the tailnet)
FAIL  journal    staged(1 boot on disk; reboot to prove it) 30s dev
FAIL  services   questdb grafana inactive (not in the image); heartbeat.timer off on purpose
FAIL  questdb    no rows (no questdb)
```

Every FAIL is a known property of this card, not a defect in the build.
`state` matching outright is the stronger result: the fresh card's `npm
install` pulled the same plugin versions the boat is running, so the
`vhfinfo` drift the payload card carries does not exist here.

Two preflight bugs surfaced on this first real run of both checks, fixed in
5a04053: `state` did not exclude the `plugin-config-data` files of the four
expected-off plugins or `venus.json`, all of which differ by decision, so it
would have FAILed on every card forever; and `journal` could not tell
`Storage=volatile` from persistent-but-not-yet-rebooted.

Of the five native modules the recipe rebuilds, four load under Node 24
(`i2c-bus`, `epoll`, `sqlite3`, `lzma-native`). `serialport` does not — "Could
not locate the bindings file" — which matches the already-known reason
`signalk-instrument-light-plugin` never loads on HALOS. Not new, and not
caused by the script.

## The three app packages exist on apt.halos.fi

Asked without installing (`apt-cache policy`, cheaper than an install on a
2 GB card already 1.3 GB into swap), so the plan's "remove InfluxDB, disable
AvNav/OpenCPN" steps have a forward equivalent on a fresh card:

- `marine-questdb-container` 10.0.0-1
- `marine-grafana-container` 13.1.3-2
- `marine-influxdb-container` 2.9.1-5

all from `apt.halos.fi trixie-stable/main`. What they pull on install is
still unmeasured.

## Order for the fresh-card test, when the card is in a Pi

0. Wired Ethernet with internet. Nothing works before this — see
   "Requirements" above.

1. Boot, `ssh pi@<dhcp-ip>` with the default password, change it to the
   sops value, `tailscale up --ssh --hostname=halos-fresh`, note the IP.
2. `dpkg -l 'marine-*' 'halos-*'`, `docker ps`, `cat /etc/halos/port-registry`,
   `nmcli con show`, `cat /boot/firmware/cmdline.txt` — the image baseline,
   into this file.
3. `ansible-playbook -i inventory site.yml -l symphony-halos` against the
   new IP, expect the reboot handler to fire. Record every failure verbatim.
4. B3 by hand: the `.signalk` copy from the boat, forks, pins, the npm
   recipe. Time it.
5. `.env`, ntfy, pypilot image (`--build` takes ~1 h on a Pi 4; export the
   bench image with `docker save` instead).
6. `scripts/halos_preflight.sh halos-fresh` — every gap it finds is a line
   for Ansible or `install.sh`, not a hand fix.
