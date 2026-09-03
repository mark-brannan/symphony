# pypilot in a container

Feasibility study and design record, researched and built 2026-09-02. The
artifacts are `pypilot/Dockerfile`, `compose-pypilot.yml` (boat shape) and
`dev/compose-pypilot-dev.yml` (laptop shape); the procedure to run and verify
them is in `RUNBOOK.md` § pypilot in a container.

Claims below are **[verified]** (measured here, source named) or
**[unverified]** (reasoned, not yet tested). The unverified ones are the
bench/boat work that has not happened.

## Verdict

Feasible, and the PoC runs. The autopilot daemon and its web UI build from
source into one image and start clean in containers, with realtime scheduling
intact. Two things make it easy: pypilot's only hardware dependency aboard
today is the I2C IMU, and everything it persists lives in one directory.

It has never driven a rudder — no servo is aboard — but it is no longer just
a proof of concept: `symphony-pi` was cut over 2026-09-03, native `pypilot`/
`pypilot_web` disabled, the container the live service. Measured at cutover:
95 MB + 39 MB (container) vs. 321 MB (native, same host, same moment) —
containerized uses well under half the memory, not more. Procedure and
rollback: `RUNBOOK.md` § "Cut the boat over from native to containerized".

## What pypilot actually is aboard Symphony

Read off the boat Pi 2026-09-02 **[verified]**:

- `pypilot.service` and `pypilot_web.service` active; `pypilot_boatimu.service`
  inactive by design — its unit `Conflicts=pypilot.service`, because the
  autopilot daemon runs the IMU process itself.
- Version 0.56, installed by OpenPlotter into system site-packages.
- IMU: `IMUType=7` (MPU9250), `BusIsI2C=true`, `I2CBus=1`, address 0x68 —
  from `~/.pypilot/RTIMULib.ini`. Live: `imu.heading = 52.58`,
  `imu.pitch = 8.96`, `imu.error` empty.
- **No servo.** `servo.controller = none`, and `/dev/serial/by-id`,
  `/dev/ttyUSB*` and `/dev/ttyAMA*` do not exist. There is no motor
  controller wired, so the autopilot is a heading/attitude sensor with a UI.
- Listening: 23322 (pypilot control), 20220 (NMEA 0183 TCP), 8000 (web UI).
- Resident set of the whole thing is roughly 130 MB across seven processes.
- SignalK integration runs both ways: pypilot pushes to SignalK using the
  token in `~/.pypilot/signalk-token`, and the `pypilot-autopilot-provider`
  plugin (v1.1.2, by panaaj) reaches *in* over the pypilot_web websocket —
  its config aboard is `{"host": "localhost", "port": 8000}`.

## Findings that shaped the build

**The working directory is load-bearing** **[verified]**. `boatimu.py` calls
`RTIMU.Settings("RTIMULib")`, which resolves relative to the process's current
directory — not to `~/.pypilot`. Nothing in pypilot chdirs there; OpenPlotter's
units carry `WorkingDirectory=/home/pi/.pypilot` (confirmed via
`systemctl cat` and `/proc/<pid>/cwd`), while the units in pypilot's own repo
do not. Get this wrong and the compass calibration is silently not loaded and
not saved. The image therefore sets `WORKDIR /root/.pypilot`, the same path as
the mounted data volume.

**Installing straight from the git URL produces a broken install**
**[verified]**. `setup.py` runs SWIG from a `cmdclass` hooked onto the
*install* command, which modern pip never invokes — it builds a wheel. The
result ships `_linebuffer.so` without the generated `linebuffer.py` wrapper,
and the daemon dies on its first pipe with
`NameError: name 'linebuffer' is not defined`. Observed exactly that. The fix
in the Dockerfile is to clone, run `python setup.py build_ext --inplace` so the
wrappers exist in the tree, then `pip install .`.

**Realtime scheduling needs two grants, not one** **[verified]**. pypilot
raises its own priority by shelling out to `sudo -n chrt -f -p 1 <pid>`, so
the image must contain `sudo` and `util-linux`. Docker also pins `rtprio` to
0, which blocks `SCHED_FIFO` even for root. With `cap_add: SYS_NICE` and
`ulimits: rtprio: 99` the daemon logs "made imu process realtime" and its two
main processes show `SCHED_FIFO` priority 1 and 2; without them it logs
"failed to make autopilot process realtime" and everything stays
`SCHED_OTHER`. Nothing fails loudly in that state — the control loop just
runs at ordinary priority, which is the condition you least want to discover
while steering.

**Networking has to be host** **[verified reasoning, from source]**. pypilot
discovers SignalK by browsing mDNS `_http._tcp` and advertises itself over
zeroconf by enumerating `/sys/class/net`; on a bridge it would advertise an
address nothing on the LAN can reach. The SignalK plugin's config aboard
points at `localhost:8000`, and SignalK under HALOS is itself host-network, so
host-network pypilot keeps that working with no config change. The bridge
alternative exists and is documented in `compose-pypilot.yml`: set pypilot's
`signalk.host` property (persistent, manual host overrides discovery — see
`signalk.py`) and re-point the plugin. It costs two settings that can drift.

**Root in the container, deliberately.** `/dev/i2c-1` is opened either as root
or as a member of the host's `i2c` group, whose gid differs per image — 988 on
HALOS, per `host/halos/README.md`, which documents this exact trap costing the
BME680 its data with no error message. Running as root removes the gid
guessing at the cost of root-owned files in `pypilot/data/`.

**One directory holds all state.** `pypilot.conf`, `RTIMULib.ini` (the compass
calibration — expensive to redo, it means swinging the boat), `signalk-token`
(a credential, so `pypilot/data/.gitignore` excludes everything) and the
serial-probe hints. Back that directory up and the container is disposable.

## Integration seams to get right at cutover

1. **The SignalK plugin's host/port.** `localhost:8000` holds only while both
   sides are host-network. Any bridge deployment must re-point it.
2. **The SignalK access token.** pypilot requests access and the request is
   approved once in SignalK's admin UI; the token then lives in the data
   directory. Copy the existing token forward rather than re-approving.
3. **gpsd.** pypilot connects to gpsd on 2947 for position. Host networking
   keeps that; a bridge does not.
4. **Version jump.** The image builds pypilot master (0.71 at the pinned
   commit) against the boat's 0.56. **[verified]** 2026-09-03, on a copy of
   the boat's `~/.pypilot` run on the HALOS bench card: 0.71 loaded the 0.56
   `RTIMULib.ini` byte-for-byte unchanged except one field — `IMUType`
   flipped from 7 (MPU9250) to 14 (ICM-20948), because pypilot autodetects
   the chip on the bus rather than trusting the stored type. The compass
   ellipsoid calibration, accel calibration, and every other field carried
   over untouched, and the log confirms both were actually applied ("Using
   ellipsoid compass calibration", "Using accel calibration"), not silently
   replaced with defaults. This result is IMU-agnostic — it holds for
   whichever chip is physically on the bus.

   **[verified]** 2026-09-03, against the boat's actual MPU9250 on
   `symphony-pi` itself (native pypilot stopped, image built from source on
   the boat, run against a copy of the live `~/.pypilot`): the log reads
   "MPU-925x init complete" and "IMU all sensor axes verified",
   `imu.heading`/`imu.pitch` came back live (52.35°/8.64°, matching the
   boat's own documented native reading of 52.58° closely), and
   `RTIMULib.ini` came back byte-for-byte identical — no field changed at
   all, since the stored `IMUType=7` already matched the real chip. The
   MPU9250 driver path is no longer a gap.
5. **A servo, when one is fitted.** A USB motor controller appearing after the
   container starts will not show up inside it: `devices:` is static. That
   needs either a restart after plugging in, or `device_cgroup_rules` plus a
   `/dev` bind mount. Not solved here, because there is no servo aboard.

## Not yet verified

- **The arm64 build.** Built and run only on amd64 (WSL, 16 cores) originally:
  about 90 s, 682 MB image. **[verified]** arm64: 416 s on the 2 GB HALOS
  bench card (2026-09-02); 9m38s from scratch on `symphony-pi` itself
  (2026-09-03, no docker layer cache, fresh clone of the boat's actual
  cellular WAN — apt, PyPI wheels, and the RTIMULib2/pypilot SWIG compiles
  all completed in one pass with no retries needed, network estimated at
  ~190 MB total). numpy and scipy pulled aarch64 wheels on both; RTIMULib2
  and pypilot's SWIG extensions compiled from source in both, at 35 s for
  RTIMULib2 on the boat Pi.
- **A real IMU through the container.** On the dev box `imu.heading` is
  `False` and the loop logs "server/client is running too _slowly_" — expected
  with no IMU pacing it, but it means the I2C path itself is untested from
  inside a container. **[verified]** 2026-09-03: the HALOS bench card's
  ICM-20948 (`i2cdetect` shows `0x68`, "made imu process realtime", "IMU all
  sensor axes verified", live moving `imu.heading`/`imu.pitch`) and then
  the boat's own MPU9250 on `symphony-pi` itself — "MPU-925x init complete",
  heading/pitch matching the boat's documented native reading. Both chips
  confirmed; nothing left untested on this leg.
- **HALOS siting.** HALOS owns `/var/lib/container-apps/` and overwrites it on
  upgrade, so a Symphony-owned pypilot must be a separate compose project with
  its own systemd unit, alongside HALOS's apps rather than inside them. Which
  is also how it would work on a plain Trixie box with the rest of this
  repo's stack. The unit file does not exist yet.
- Whether the containerized daemon behaves the same as the native one over
  hours, and how the two would coexist during a transition (they cannot —
  both bind 23322 and 8000).
