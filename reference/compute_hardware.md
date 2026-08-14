# Compute hardware

The machine the software stack runs on, and where it is going. For what is
installed on it, see [legacy_openplotter_stack.md](legacy_openplotter_stack.md)
and [software_stack.md](software_stack.md).

## Aboard now

Raspberry Pi 4 Model B Rev 1.5, 4 GB RAM, on a 32 GB SD card (29 GB usable).
Debian 12 (bookworm), kernel 6.12.96 aarch64, hostname `signalk`. OpenPlotter
is installed on bare metal — eleven `openplotter-*` packages, no Docker.

The SD card is the constraint that shapes everything else: it holds the OS,
SignalK's state directory, the InfluxDB store and Grafana's database on one
partition, and it is the component most likely to fail first.

### PiCAN-M HAT

The [PiCAN-M](https://copperhilltech.com/pican-m-nmea-0183-nmea-2000-hat-for-raspberry-pi/)
carries both marine buses on one board:

| Bus | Connector | Appears as |
|---|---|---|
| NMEA 2000 | Micro-C | `can0` (SocketCAN) |
| NMEA 0183 | RS422, 5-way screw terminal | `/dev/ttyS0`, via `/dev/serial0` |

`can0` runs at 250 kbit/s, the NMEA 2000 bus rate. The board is 120 Ω
terminator-ready, carries a status LED on GPIO22, and exposes a Qwiic (I2C)
connector for additional sensors.

This is the SMPS variant: the Pi is powered from the NMEA 2000 bus. (The
base board has no onboard supply and can't be.) So bus power and computer
power are the same thing — anything that drops the N2K bus drops the Pi,
with no buffer and no orderly shutdown.

### There is no GNSS receiver attached

Nothing on this box produces a real position or a real GPS time. Measured
2026-08-13:

- `gpsd` runs with `DEVICES="/dev/ttyOP_gps"`, and that device does not
  exist. Neither does any other serial or USB device — `/dev/serial/by-id`,
  `/dev/ttyUSB*`, `/dev/ttyACM*` and `/dev/ttyOP_*` are all absent.
- `gpspipe -w` reports `"devices":[]`, and `ntpshmmon` produces no samples,
  so the NTP shared-memory segments `gpsd` would publish into stay empty.
- `navigation.position` in SignalK has `$source: signalk-fixed-position` — a
  plugin emitting a fixed dock coordinate, not a fix.

`can0` is up and carrying NMEA 2000 traffic, so the bus itself is alive; the
GPS is simply not part of it, or not reporting. This matters twice over.
Chartplotting and AIS aside, it is why chrony's `refclock SHM 2` sits
unreachable and the clock depends entirely on an internet connection — see
`host/chrony-gpsd.conf`. Offline, this boat's time drifts with nothing to
correct it and no RTC to fall back on.

### Display

No HDMI display is attached (`/sys/class/drm/card1-HDMI-A-*/status` reads
`disconnected` on both outputs). The box is not headless by design — it runs
lightdm and a Wayfire desktop, reachable over `rpi-connect`'s wayvnc, and a
screen may be plugged in. What it must not do is render a GPU-accelerated
browser at boot into a display that is not there; see the v3d trap in
[RUNBOOK.md](../RUNBOOK.md).

## Where this is going

The intended replacement is a [HALPI2](https://shop.hatlabs.fi/products/halpi2-computer)
from Hat Labs running [Hal OS](https://hatlabs.fi/posts/2026-01-02-halos-update/).
Not imminent — a month or several out — but it is the target the current
repair work should leave the boat ready for.

### HALPI2

A Compute Module 5 in a marine enclosure. What it changes relative to the
Pi 4B:

- **Power.** 10–32 V input, tolerating spikes to 100 V, and an integrated
  RP2040 microcontroller with short-term energy storage that performs a
  controlled shutdown on power loss. Draws at most 0.8 A when powered from
  NMEA 2000. This is the direct answer to the Pi's current arrangement,
  where a bus drop is an unclean shutdown of the computer.
- **Storage.** eMMC (32 or 64 GB) or SSD (256 GB, 512 GB, 1 TB) instead of an
  SD card.
- **Memory.** 2, 4, 8, or 16 GB.
- **Enclosure.** Die-cast aluminum, 200×130×60 mm, IP65, with the CPU coupled
  to the enclosure floor as its heat sink.
- **Interfaces.** NMEA 2000 Micro-C and an isolated NMEA 0183 interface
  integrated; RJ45, HDMI, two external and two internal USB3, and pre-drilled
  holes for two SMA antenna connectors. Further CAN or RS485 ports come from
  Waveshare isolated HATs.

Listed at €651.61, currently sold out.

### Hal OS

Raspberry Pi OS Trixie underneath, with the applications — Signal K Server,
AvNav, and whatever else — running as Docker containers installed through
Debian packages. Single sign-on spans the containerized apps, which are
reached by domain name (`avnav.halos.local`) rather than by port. Cockpit
provides web-based system administration, and a Container App Store handles
installation. Images ship in headless, desktop, marine, and HALPI2 variants,
and Hal OS can also be layered onto an existing Pi OS Trixie install.

It is an early-stage project whose author is asking for test users, and the
foundation was redesigned once already — so it is a direction, not yet a
commitment.

Two things make it the natural target. It is containerized, which is where
this repo's golden config already points, and its single-sign-on story
overlaps the Dex work rather than fighting it.
