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

## Order for a fresh-card rebuild

The whole order below is now one command, `scripts/halos_card_prepare.sh
<lan-ip>`. The numbered steps that follow are its contents, kept as the
record of why each exists.

Every step below has been run verbatim on a fresh card (Pi 4 2026-09-03,
Pi 5 2026-09-04). `$IP` is the card's DHCP address; `$D` is
`/var/lib/container-apps/marine-signalk-server-container/data/data`.

**0. Wired Ethernet with internet, plugged in before power-on.** Not
optional — see "Requirements" above. The image ships no container images at
all, so first boot pulls several GB. If the units already failed:

```sh
sudo systemctl reset-failed
sudo systemctl restart --no-block halos-core-containers marine-signalk-server-container
```

Find the card: it is the only Debian 13 box on the LAN.

```sh
for i in $(seq 1 254); do (ping -c1 -W1 192.168.0.$i >/dev/null 2>&1 && echo 192.168.0.$i) & done | sort
# then, per live host:
timeout 3 bash -c 'exec 3<>/dev/tcp/<ip>/22 && head -c 45 <&3'   # want OpenSSH ... Debian-…deb13…
```

**1. Bootstrap: key, password, and a power sanity check.**

```sh
scripts/halos_card_bootstrap.sh $IP
```

Installs your public key, sets `pi` to the sops password (trying the image
defaults `halos` then `raspberry`), and reports board, RAM, sudo mode and
`vcgencmd get_throttled`. **Read the throttled line.** Bit 0 set means
under-voltage *now*; that card will die under a parallel `docker pull` with
no OOM and no panic. Fix the supply, or trade clock for current:

```sh
scripts/halos_card_bootstrap.sh $IP --cap    # 1.5 GHz, powersave; reverts on reboot
```

**2. Record the image baseline into this file** — it drifts between images,
and two of these were wrong before the Pi 5 run:

```sh
ssh pi@$IP 'dpkg -l "marine-*" "halos-*"; cat /etc/halos/port-registry;
  nmcli -t -f NAME,DEVICE,TYPE con show; cat /boot/firmware/cmdline.txt;
  grep -v "^#" /boot/firmware/config.txt | grep -v "^$"; id; timedatectl'
```

**3. Flatten the image-pull peak** on any card that reported under-voltage.
Eight layers decompressing across four cores is the largest transient the
card ever sees:

```sh
printf '{\n  "max-concurrent-downloads": 2,\n  "max-concurrent-uploads": 2\n}\n' \
  | ssh pi@$IP 'sudo tee /etc/docker/daemon.json >/dev/null && sudo systemctl restart docker'
```

**4. The two app packages, BEFORE Ansible.** Order matters: `apt install`
drags in `marine-influxdb-container` as an automatic dependency, and
`roles/base` step 20 purges it. Install first and Ansible cleans up; install
after a converged run and you have silently reinstated the app Ansible exists
to remove.

```sh
ssh pi@$IP 'sudo apt-get update && sudo apt-get install -y marine-questdb-container marine-grafana-container'
```

Offline, or on a slow link, load the images instead of pulling them — they
are the entire weight (the `.deb`s are 34.6 kB):

```sh
gzip -dc halos-db-images.tar.gz | ssh pi@$IP 'sudo docker load'
# export side, from any card that has them:
ssh pi@<src> 'sudo docker save grafana/grafana:13.1.3 questdb/questdb:10.0.0 influxdb:2.9.1 | gzip -1' > halos-db-images.tar.gz
```

**5. Ansible.** Scratch inventory under the scratchpad, never committed:

```yaml
all:
  children:
    halos_cards: { hosts: { symphony-halos: { ansible_host: <IP> } } }
    openplotter_cards: { hosts: { symphony-pi: } }
  vars:
    ansible_user: pi
    ansible_ssh_common_args: '-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
```

```sh
cd ansible && ansible-playbook -i <scratch>/inv.yml site.yml -l symphony-halos
```

Expect the boot role to reboot the card and the run to continue. Rerun until
`changed=0`; record every failure verbatim as a role fix, not a hand fix.

**6. Disable the heartbeat on any card that is not the one in service.**
`host/install.sh` enables `boat-heartbeat.timer`, and `host_vars` points it
at the *real* card's healthchecks.io check — so a bench card silently
reports as the boat card. It is re-enabled by every Ansible run, so this is
the last step after the last run, not a one-off:

```sh
ssh pi@$IP 'sudo systemctl disable --now boat-heartbeat.timer'
```

**7. SignalK state (as-built steps 31–42).** A card that is not on the
tailnet cannot reach the boat, so the copy relays through the dev box:

```sh
ssh pi@$IP 'cp $D/package.json /home/pi/package.json.halos'
rsync -a --exclude node_modules --exclude appstore-cache --exclude 'skserver-raw_*' \
  --exclude '*.bak*' --exclude '*.deb' --exclude signalk-server --exclude 'ssl-*.pem' \
  pi@symphony-pi:.signalk/ <stage>/          # ~138 MB
rsync -a <stage>/ pi@$IP:$D/                 # run twice; the second moves nothing
rsync -a --exclude node_modules --exclude .git pi@symphony-pi:bt-sensors-plugin-sk/ <bt>/
rsync -a <bt>/ pi@$IP:$D/local-plugins/bt-sensors-plugin-sk/
ssh pi@$IP 'git -C /home/pi/symphony pull && cp -r /home/pi/symphony/plugins/signalk-plugin-watchdog $D/local-plugins/'
```

Then the two `file:` pins in `$D/package.json`
(`file:local-plugins/<name>` for both forks), the build, and the config:

```sh
ssh pi@$IP 'sudo /home/pi/symphony/scripts/halos_signalk_npm.sh install'
```

8 min on a Pi 5 at 1.5 GHz, 19 min on a Pi 4; 2773 packages. Then as-built
37–38: `"enabled": false` in `signalk-container.json`,
`signalk-to-influxdb2.json`, `signalk-to-influxdb-v2-buffer.json`,
`signalk-notification-player.json`, and `venus.json`'s `MQTT.host` to the
Cerbo's address. Restart and confirm no `EACCES` / `Cannot find module`.

**8. Front door and ntfy (as-built 43–46).**

```sh
ssh pi@$IP 'cd /home/pi/symphony && cp -n .env.example .env &&
  sudo docker compose -p symphony -f docker-compose.yml up -d ntfy &&
  sudo install -m 0644 host/halos/traefik-symphony-signalk-host.yml \
    /etc/halos/traefik-dynamic.d/symphony-signalk-host.yml'
```

Verify `/`→302, `/ca`→302, `/ca/`→200, `/sso`→404, `/sso/`→200 with
`curl -sk --resolve signalk.<domain>:443:127.0.0.1`.

**9. Preflight.** `scripts/halos_preflight.sh $IP`. Every gap it names is a
line for Ansible or `install.sh`, not a hand fix. On an off-tailnet card,
`host` FAILs by design; `state` FAILs on any plugin the boat has since
updated, which `RUNBOOK.md` → "final state sync" owns.

### If the card loses power mid-build

A power cut during `docker pull` leaves an image that **`docker pull` will
not repair** — the digest matches, so Docker considers it present and reuses
the corrupt layers. Every binary in it returns `exec format error`, including
`/bin/ls`, while `docker image inspect` still reports the right
architecture. Recovery is remove-then-pull:

```sh
ssh pi@$IP 'sudo docker rmi node:24-bookworm && sudo docker pull node:24-bookworm'
ssh pi@$IP 'sudo docker run --rm node:24-bookworm node -p process.versions.modules'  # want 137
```

`halos_signalk_npm.sh` is safe to re-run after this; npm reconciles the tree.

## The whole plan on a fresh Pi 5, 2026-09-04

The first end-to-end run of this file's own order on hardware where memory
was not the constraint. Board: **Raspberry Pi 5 Model B Rev 1.0, 8 GB**
(8050 MB total), 4 cores, Debian 13 Trixie, kernel 6.18.39+rpt-rpi-2712,
115 GB card. Reached on the LAN at its DHCP address; never joined to the
tailnet, matching the 2026-09-03 fresh Pi 4 run.

### The headroom question is answered: it was the card, not the stack

| | used | available | swap |
|---|---|---|---|
| SignalK alone, image baseline | 1635 MB | 6415 MB | 0 |
| + QuestDB, Grafana, InfluxDB (10 containers) | 2074 MB | 5976 MB | 0 |
| Host layer converged, full stack | 2127 MB | 5934 MB | 0 |
| Final, full boat plugin set loaded | 3509 MB | 4552 MB | 21 pages out |

The stack's steady footprint with the boat's 120 plugins is ~3.5 GB. A 2 GB
card cannot hold that at all, which is the whole of the 2026-09-04 reset
loop; nothing about the stack is at fault. Swap moved 21 pages in 42 minutes,
which is noise, not pressure.

### What the two app packages actually cost

The `.deb`s are **34.6 kB fetched, 195 kB installed** — systemd units and
compose files only. Every byte of weight is the image pull:

| image | size |
|---|---|
| `grafana/grafana:13.1.3` | 1.09 GB |
| `questdb/questdb:10.0.0` | 312 MB |
| `influxdb:2.9.1` | 292 MB |

Disk went 7229 → 9277 MB, so budget ~2 GB. **`marine-influxdb-container`
2.9.1-5 arrives as an automatic dependency** of the other two — the plan
never says so, and `roles/base` step 20 then purges it on the next Ansible
run. Installing the packages *after* a converged run therefore silently
reinstates the app Ansible exists to remove. To cache the images without
that, `docker pull` the three tags directly and skip apt.

### Ansible: one new fix, then clean

Run 1: `ok=69 changed=35 failed=1`. Run 2 after the fix:
**`ok=64 changed=0 failed=0`** — converged and idempotent, including the
boot role's reboot handler firing and passing the running-kernel verify.

9. **The step 30 i2c probe raced the SignalK restart.** `flush_handlers` at
   step 29 can restart the unit; `docker exec` against a container still
   coming up fails outright, and the container's own start period is 900 s.
   Failed on the first run, passed seconds later on a rerun — the tell.
   Fixed the same way as the identity role's SAN probe: `until rc == 0`,
   12 retries at 5 s. Verified by forcing the race deliberately.

### Image baseline divergences from the 2026-08-20 Pi 4 notes

Both measured on the virgin card before anything was changed:

- **`sudo` requires a password.** This file records the image as passwordless
  for `pi`. It is not, here. Unconfirmed whether this is a Pi 5 image
  difference or an error in the original note — re-check on a Pi 4 image
  before treating it as the former.
- **The port registry ships all four ports**, not just SignalK:
  `signalk-server=4430`, `questdb=4431`, `grafana=4432`, `influxdb=4433`.

Otherwise as recorded: no tailscale/telegraf/chrony, `pi` not in `docker`,
journal volatile, `regdom=GB`, no memory cgroup, no i2c/spi/uart/CAN lines,
`systemd-zram-generator` present, Halos-AP up on `wlan0ap`.

### The npm build

`scripts/halos_signalk_npm.sh install`, containers left running:
**8 min 13 s**, exit 0, 2773 packages — against 18 min 52 s on the Pi 4, and
that with the CPU capped to 1.5 GHz (see below). bt-sensors' own tree added
857 packages in 41 s; the five named natives rebuilt clean.

### Preflight: 17 ok, 2 FAIL

Both FAILs are properties of this card, not defects:

```
FAIL  host    no tailscale on this card (by design; not on the tailnet)
FAIL  state   advancedwind 2.9.2 on the boat vs 2.9.3 here -- npm took the
              newer minor; RUNBOOK 'final state sync' owns this
```

Three lines passed that **had never passed on any card**: `services 8 active`,
`questdb telegraf cpu rows 46; newest signalk row 46 s old` (QuestDB actually
ingesting), and `containers all report (healthy)`. `plugins` matched the boat
exactly at 120 loaded / 63 on.

## Power is the Pi 5's binding constraint on a bench supply

The run died once, hard, and the cause was not memory.

Twelve minutes in, ten seconds into the npm build's `docker pull`, the card
dropped off the LAN and did not return; it needed a power cycle. `journalctl
-b -1` ends mid-sentence at `10:10:22.007` while Docker was tearing down the
SignalK container — no OOM kill, no panic, no shutdown. That is instantaneous
power loss, and it is the opposite signature to a 2 GB card's memory reset,
which leaves an OOM trail.

`vcgencmd get_throttled` after the bounce read **`0x50005`**: under-voltage
*now*, throttled *now*, and both latched since boot — at a load average of
0.24. The supply (USB-C from a bench supply, no PD negotiation) was below
spec even at rest.

**What fixed it, without touching hardware:** cap the clock.

```sh
for c in /sys/devices/system/cpu/cpu[0-9]*/cpufreq; do
  echo powersave > $c/scaling_governor
  echo 1500000  > $c/scaling_max_freq
done
```

`get_throttled` went to `0x50000` immediately — the live bits cleared, only
the latched history left. The card then survived the full npm build, showing
one brief `0x50005` transient at peak and riding it out. **`cpufreq-dt`
exposes a `boost` knob on this board but `scaling_boost_frequencies` is
empty, so disabling boost does nothing; `scaling_max_freq` is the only lever
that matters.** Available range is a flat 1.5–2.4 GHz in 100 MHz steps.

Also set on this card by hand: `/etc/docker/daemon.json`
`max-concurrent-downloads: 2` — eight layers decompressing in parallel across
four cores is the peak that killed it. **It is captured nowhere in `host/` or
`ansible/`, so it dies with this card**, which is right if it is only a
bench-supply workaround and wrong if the boat wants it. Carded rather than
generalised from here.

All of this is **runtime-only and reverts on reboot**. Persisting it is
`arm_freq=1500` in `config.txt` or a small unit writing `scaling_max_freq`,
and it costs throughput — an open question, not a decision made here.

### A power cut mid-`docker pull` leaves an image that `docker pull` will not repair

After the bounce, every binary in `node:24-bookworm` returned
`exec format error` — `/bin/ls` included — though `docker image inspect`
reported `arm64/linux` correctly and the root filesystem was clean. The
layers had been extracted from an interrupted pull. Re-pulling did **not**
fix it: the digest matched, so Docker considered the image present and reused
the corrupt layers. Only `docker rmi node:24-bookworm` followed by a fresh
pull recovered it. Worth knowing on any card that loses power during a build.

### Host monitoring for this already existed and worked

`host/telegraf-rpi-health` (telegraf `inputs.exec`) reads `get_throttled` and
emits `under_voltage`/`freq_capped`/`throttled`/`soft_temp_limit` as both
`_now` and `_since_boot`. Deployed and telegraf active on both cards; it
recorded this event correctly. **lm-sensors is installed on neither card and
should not be** — a Pi has no chip for it to read.

CPU frequency was missing and is now emitted by the same script as
`cpu_freq_khz` / `cpu_freq_max_khz`: `inputs.cpu` is utilisation, not clock,
so a thermal downclock or a deliberate cap previously left no trace at all.

**Nothing alerts on any of it.** `grafana/provisioning/dashboards/json/system.json`
shows eight stat panels (`Under-voltage now`, `Throttled since boot`, …) and
there is no alert rule anywhere in the repo — no Grafana alerting provisioning
exists at all. The metric is therefore visible only to someone already looking
at the dashboard, which is why the 2026-09-04 brownout was diagnosed by hand
despite being recorded correctly the whole time. Building that alert is real
work (the provisioning does not exist yet), not a line to slip into this run.

### What this still cannot answer

Unchanged from the top of this file: `can0` with the HAT, BLE with the boat's
sensors in range, the boat LAN. And a Pi 5 is not a Pi 4 — a clean run here
is suggestive for the boat's Pi 4B, never proof.
