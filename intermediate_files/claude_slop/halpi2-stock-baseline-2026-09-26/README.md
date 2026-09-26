# HALPI2 stock baseline — 2026-09-26

Read-only inventory of the HALPI2 as shipped, taken on its first boot on
the boat LAN (ethernet to the boat router, 192.168.8.0/24; nothing changed on
the box). This is the
"stock" state `ansible/site.yml` is measured against and the state a later
reset aims to reproduce. Identifiers (serial, MACs, machine-id, LAN IP, hotspot SSID suffix)
are redacted in the `.txt` files; the `.sh` files are the exact commands run.

## Identity

- Image: **HaLOS Desktop Marine HALPI2 AP 2026-08-20.0**, pi-gen
  `0c7cd7324a97d4a169c047de06fbe88d88fb6f3d`
  (release asset `Halos-Desktop-Marine-HALPI2-AP_2026-08-20.0.img.xz`).
- Hat Labs booted it on 2026-09-18 and apt-upgraded (`halos 0.3.7-2`,
  `/etc/halos/*` dated that day); our boot on 2026-09-26 is boot index 0
  in the journal, so the factory boot's journal was not persisted.
- CM5 Lite, 8 GB RAM, 931.5 GB NVMe (`/` at 9.9 GB used), zram swap.
- `halpid` 5.1.1, RP2040 firmware 3.3.1; bootloader EEPROM 2026-05-11 with
  an update available (not applied).
- Debian 13 trixie, kernel 6.18.39+rpt-rpi-2712; timezone Europe/London,
  wifi regdom GB.

## Access as shipped

- SSH password auth, `pi` / the default published in the
  [halos-org/halos README](https://github.com/halos-org/halos) (verified:
  that login is what produced these dumps); `pi` is in `sudo` (with
  password), `docker` group not included. No `authorized_keys`.
- Hotspot `Halos-<xxxx>` on `wlan0ap` (10.42.0.1/24, NM `method=shared`);
  the suffix is per-device, so it is redacted like the MACs. PSK as
  published in the same halos README (not verified here: nothing joined
  the hotspot); `wlan0` STA unconfigured. Ethernet DHCP.
- Web: Traefik 80/443 → Authelia SSO (`admin`, default per the same
  halos README; not verified here, no web login attempted), Homarr
  dashboard, Cockpit 9090, Signal K direct on 3000 / TLS 4430; NMEA 0183
  TCP 10110; gpsd 2947 (loopback only).
- Desktop variant: lightdm + wayvnc autologin on tty, not headless.

## Containers as shipped

traefik 3.7.1, authelia 4.39.19 (+valkey), homarr v1.60.0-halos.1,
autoheal, ca-download, signalk-server v2.31.1-halos.3. No Grafana,
InfluxDB or QuestDB — those come from `marine-container-store`. Compose
files under `/var/lib/container-apps/<app>/`, env under
`/etc/container-apps/<app>/`.

## Hardware config as shipped

`config.txt`: `mcp251xfd` on `spi0-1` (int 26, 40 MHz) → `can0` up at boot
(the integrated N2K port; not the PiCAN-M `mcp2515` our `boot`/`can` roles
write), `uart4-pi5` + `uart0` (the isolated 0183 port and console),
`i2c_arm` (halpid talks to the RP2040 at 0x6D on i2c-1), `dtparam=ant2`
(external antenna), `dtparam=sd=off`.

## Customisation hooks

cloud-init NoCloud reads `/boot/firmware/user-data`, `meta-data`,
`network-config` (shipped user-data is the empty Pi OS template). This is
the sanctioned first-boot path for hostname, password, SSH keys and wifi.

## Resetting to this state later

Two options, from cheapest to most exact:

1. **Reflash the release image.** `rpiboot` (boot switch to Abnormal,
   USB-C "USB Boot" to a laptop) exposes the NVMe as mass storage;
   Raspberry Pi Imager writes `Halos-Desktop-Marine-HALPI2-AP_2026-08-20.0.img.xz`.
   Then `apt update && apt upgrade` to reach at least the 2026-09-18
   package state. Loses: machine-id, SSH host keys (regenerate), the
   factory apt state exactly as it was. Keeps: RP2040 firmware and
   bootloader EEPROM (not on the NVMe; only touched if we update them).
2. **Bit-exact snapshot, before we change anything.** From the box over
   ssh: `sfdisk -d /dev/nvme0n1` (partition table), `dd` of the 512 MB
   boot partition, and `e2image -ra -p /dev/nvme0n1p2 -` piped through
   `zstd` for the root fs — reads only allocated blocks, ~10 GB, so it is
   a ~10 GB pull over the LAN rather than 931 GB. Restore is the same rpiboot
   path with `dd`. This is a read of the disk, not a change, but it is
   not free: ~10 GB on the Mac and tens of minutes of transfer.

Either way, changing the bootloader EEPROM or RP2040 firmware is outside
what a reflash undoes; leave both alone until the baseline is banked.
