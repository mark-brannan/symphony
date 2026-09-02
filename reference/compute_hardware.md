# Compute hardware

The machine the software stack runs on, and where it is going. For what is
installed on it, see [legacy_openplotter_stack.md](legacy_openplotter_stack.md)
and [software_stack.md](software_stack.md).

## Aboard now

Raspberry Pi 4 Model B Rev 1.5, 4 GB RAM, on a 32 GB SD card (29 GB usable).
Debian 12 (bookworm), kernel 6.12.96 aarch64, hostname `signalk`. OpenPlotter
is installed on bare metal — eleven `openplotter-*` packages. Docker is also
installed and running, but only for Dex and ntfy; SignalK and the rest of the
stack are native.

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

### GNSS arrives over NMEA 2000

Connected 2026-08-13. `signalk/settings.json` carries one `pipedProvider`,
`n2k-can0`, of type `canbus-canboatjs` on interface `can0`. SignalK now
publishes `navigation.position`, `speedOverGround`, `courseOverGroundTrue`,
`datetime` and the full `navigation.gnss` subtree from source `n2k-can0.2`,
plus `magneticVariation` from `n2k-can0.7`.

The `uniqueNumber` in that config is pinned to `368391` deliberately. It forms
part of the NAME this box claims on the bus; left unset, SignalK generates a
random one, so the Pi would appear as a different N2K device after every
config change.

Five devices answer on the bus: a GNSS at address 2, Navigation at 7, a
Display at 8, Steering and Control at 10, and SignalK's own claimed address at
100. The chartplotter and the AIS each carry their own GPS, so expect a second
position source once the AIS is powered — see the source-priority note in
`RUNBOOK.md`.

#### What this looked like before, and why it hid

Measured 2026-08-13, before the connection existed:

- A GNSS device at N2K source address `0x02` publishes continuously:
  `129025` Position Rapid Update, `129026` COG & SOG, `129029` GNSS Position
  Data, `129539` DOPs, `129540` Satellites in View, and `126992` System Time.
  In one 12-second sample that was 58, 25, 42, 7, 151 and 7 frames.
- Decoding a `129025` frame off the wire gives 47.657794, -122.377303, and
  the last digit moves between frames — a live fix, not a stored value.
- `settings.json` had **zero** `pipedProviders`, and had zero in every version
  of `signalk/settings.json` in this repo's history. SignalK had no NMEA 2000
  input configured at all, so none of the above reached it. It was never
  configured rather than lost.
- `navigation.position` therefore read `$source: signalk-fixed-position`, and
  there was no `navigation.gnss` or `navigation.datetime` at all.

The reason this hid for so long is worth stating plainly, because it is a
general trap. `signalk-fixed-position` is a *fallback* — it stores the last
known fix and re-emits it when GPS goes quiet, so position-dependent systems
keep working. With no real GPS ever connected, the fallback was the only
source, and it had stored a fix from whenever position last worked. It sat
about two metres from the true position. Every consumer saw a plausible
position at the right dock, so nothing looked broken. A fallback that has
silently become the primary is indistinguishable from a working system right
up until the boat moves.

There is no *serial* GPS, which is a different statement: `gpsd` runs with
`DEVICES="/dev/ttyOP_gps"` and that device does not exist, nor does any other
serial or USB device (`/dev/serial/by-id`, `/dev/ttyUSB*`, `/dev/ttyACM*`,
`/dev/ttyOP_*` are all absent). `gpspipe -w` reports `"devices":[]` and
`ntpshmmon` produces no samples.

That distinction is what made the first attempt at GPS time wrong. The usual
recipe — `refclock SHM`, reading the NTP shared-memory segments gpsd
publishes into — assumes a serial receiver this boat does not have, so the
segments are never written and the refclock sat at Reach 0 having never
received a sample. It has been removed; `host/chrony.conf` now carries no
refclock and chrony tracks internet NTP alone. The GPS time it was reaching
for is on the N2K bus in `126992` and `129029` — and now reaches SignalK as
`navigation.datetime`, which is the likely bridge — but getting it to chrony
needs a bridge that doesn't exist yet. Offline, the clock has nothing to
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

Target configuration: 8 GB / 512 GB SSD, ~$614 as of 2026-08-13.

### Hal OS

Raspberry Pi OS Lite arm64 underneath, with the applications — Signal K
Server, Grafana, InfluxDB, QuestDB, AvNav, OpenCPN — running as Docker
containers wrapped as Debian packages from `apt.halos.fi`. Traefik and
Authelia provide SSO over path-based routing (`https://halos.local/grafana/`);
Cockpit provides web administration. Images ship for generic Pi 4/5 as well
as HALPI2, and it can be layered onto an existing Pi OS **Trixie** install
via APT — untested on Bookworm, which is what the boat runs today.

It is self-described as beta, its author is asking for test users, and the
foundation has been redesigned once — so it is a direction, not a commitment.
The full verified survey, the open questions, and the trial plan are in
[containerization_strategy.md](containerization_strategy.md).

It is the natural target because it is containerized, which is where this
repo's golden config already points. Its SSO is Authelia, not Dex; whether
the two federate is one of the open questions the trial has to answer.
