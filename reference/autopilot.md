# Autopilot: pypilot on Symphony

A living draft, started 2026-11-19. It is the working document for
[#171](https://github.com/mark-brannan/symphony/issues/171) and is expected
to change. It holds what is known and what has to be worked out. Leads from
research that nobody has checked are in the issue, not here.

## What done looks like

pypilot steers the boat through the drive already on the rudder quadrant,
and the owner's part is a little installation. The whole solution is worked
out end to end, with evidence that it works, before parts are bought.

## Order of work

The owner's, 2026-11-19.

1. Rudder angle sensor on the quadrant, reporting to SignalK. Worth having
   with no autopilot at all.
2. Rudder angle on the screens and in history.
3. pypilot reads that rudder angle.
4. The drive: what it is and whether it runs.
5. The whole build worked out on paper: every part, every connection, every
   wiring run, every enclosure.
6. The motor controller. Last purchase, and only once the finish line is in
   sight. Building one or buying one is the lowest-priority question.
7. Dock test, sea trial.

## What is known

| Thing | State | Source |
|---|---|---|
| Boat computer | the HALPI2; the Pi 4 and its PiCAN-M are disconnected | owner, 2026-11-19 |
| NMEA 0183 | nothing connected; may be hooked up again | owner, 2026-11-19 |
| Drive | a long ram on an arm at the quadrant, left from an Autohelm system | owner, 2026-11-19 |
| Rudder sensor | none aboard | owner, 2026-11-19 |
| pypilot on the Pi 4 | ran in a container with a calibrated MPU9250 compass, linked to SignalK both ways, no motor controller | [pypilot_containerization.md](pypilot_containerization.md) |
| pypilot on the HALPI2 | not recorded | — |
| Spare computer | a Raspberry Pi Zero W, bought to run tinypilot | owner, 2026-11-19 |
| Spare compass sensor | an ICM-20948 | owner's notes, 2025 |
| Rudder angle into pypilot | pypilot takes it from an NMEA `RSA` sentence, and maps SignalK `steering.rudderAngle` | pypilot source, `pypilot/nmea.py` and `pypilot/signalk.py`, master, read 2026-11-19 |

## What the plan has to answer

Each is to be answered from the primary sources — pypilot's schematics,
manual and firmware, the HALPI2's documentation, the boat — and brought to
the owner as a worked answer, not a question.

### Rudder sensor

- Which sensor, and how it mounts and links to the quadrant.
- What reads it and carries the angle to SignalK on the HALPI2.
- Whether the same sensor can later feed the motor controller directly, or
  stays on SignalK.

### The computer that steers

- pypilot on the HALPI2: how a compass sensor and a serial line to the motor
  controller get into it.
- pypilot on the Pi Zero W beside the drive: what it needs added, how it
  reaches SignalK, and what goes wrong on wifi alone.
- Which of the two, and why.

### The motor side

- The drive's type, voltage, running and stalled current, and its clutch.
- Every connection on the controller: motor, clutch, rudder sensor, serial,
  power, fuse.
- A bought controller against one built on an Arduino Nano: what each needs
  made, bought and wired, including any circuit board.

### The boat side

- Each wiring run: from, to, length, wire size, protection.
- Each enclosure and bracket: what goes in it and where it mounts.
- Control at the helm, and the switch that drops the clutch.

### Knowing it works

- What can be proven on a bench before anything goes on the boat.
- Published builds on the same class of drive, read first-hand.
- The test that closes each step in the order of work.
