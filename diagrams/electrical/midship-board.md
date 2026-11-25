# Midship ESP32 board — mast lights, forward sidelights, four-pump monitoring

One ESP32 board under the port dinette settee (position 2). It switches the
mast lights and the forward sidelights, switches the dry-bilge pump, and
measures volts and amps on four pumps. The IMU and the paddlewheel are not on
this board.

**Scope:** from the two feeds arriving at the board (the lighting feed and the
always-on bus) to the terminals where each fixture's or pump's pair lands.
Nothing upstream of those feeds, nothing inside the fixtures or pumps.

Every number marked *stand-in* is a working placeholder, not a specification.
Numbers marked *calculated* come from datasheet figures and have not been
measured on this board.

## Diagrams

| | |
|---|---|
| [System block](midship-board-block.svg) | light channels, the pump channel, four INA226s on I²C |
| [Pump sensing](midship-board-sensing.svg) | shunts in the negative leads, Kelvin pairs, Q8 and D8 |

Regenerate both from the repo root:

```bash
python3 diagrams/electrical/midship-board-diagrams.py
```

![System block](midship-board-block.svg)

## Light channels

Identical to [nav-light-controller.md](nav-light-controller.md): an
opto-driven high-side P-MOSFET, a branch fuse, and a normally-empty bypass
fuse block. That document owns the circuit, the fail-off behaviour and the
masthead radio-group rule. Lights are fed from the lighting feed.

| | Channel | Fixture |
|---|---|---|
| CH1–CH3 | Masthead, legs 1–3 | mode-select legs of the masthead unit |
| CH4 | Sidelights | port + starboard, one channel |
| CH6 | Steaming light | forward-facing white 225° |
| CH7 | Spreader lights | deck work light — not a navigation light |
| CH8 | Dry-bilge pump (P3) | see below |

CH5, the stern light, is not on this board: it is neither a mast light nor a
forward light.

A future channel is cabin-light switching. It is deferred and has no
footprint here yet.

## Pumps

P1–P3 run from the always-on bus; P4's feed is open. The ESP32's logic supply (F-LOGIC and
buck) also comes from the always-on bus, so monitoring keeps working with the
house panel off.

| | Pump | Max draw | Fuse | Switching | Shunt |
|---|---|---|---|---|---|
| P1 | SEAFLO 06-series 1100 GPH automatic bilge | 6.0 A (retailer listing) | per the pump's manual | its existing Auto/Off/Man panel switch and float; the board does not switch it | S1, external, 20 A / 75 mV (3.75 mΩ), in the pump's negative |
| P2 | SEAFLO 13A Series 2000 GPH bilge, non-automatic (SFBP1-G2000-13A) | 7.5 A (retailer listing) | per the pump's manual | its existing switching; the board does not switch it | S2, external, 20 A / 75 mV, in the pump's negative |
| P3 | Amarine FLO-2202 12 V diaphragm pump, 4.3 L/min, 35 PSI — the "dry bilge" pump | 3.5 A max (label) | 4 A (label: "4A FUSE REQ'D") | CH8: opto and high-side P-MOSFET Q8 on the board; D8 flyback across the motor; F8 4 A; no bypass fuse | S3, 15 mΩ 2512 resistor on the board, in P3's negative return |
| P4 | shower sump pump, model not yet identified | open | open | its existing switching; the board does not switch it | S4, external, 20 A / 75 mV, in the pump's negative |

The crash pump is near the engine room and is not on this controller.

![Pump sensing](midship-board-sensing.svg)

### Why the shunts are in the negative lead

An Auto/Off/Man switch, or a 3-wire automatic pump, feeds the motor through two
positive leads. One positive-side shunt would miss a mode. The negative lead
carries every mode, and the INA226's common-mode range covers near-0 V.

Each Kelvin lead of an external shunt (S1, S2, S4) has a fuse at the shunt end
(*stand-in*, 0.5 A). If a pump's return opens downstream of its shunt, the
motor's current would otherwise return through the sense lead and the board.
The fuse protects the lead, not the INA226. S3 is on the board and needs none.

### Why P1, P2 and P4 are external and P3 is on the board

Bilge-pump current stays off the board, so a board fault cannot stop a bilge
pump. P4's current does not otherwise cross the board either, and S4 is the
same part as S1 and S2. P3's current already crosses the board through Q8, so an on-board shunt
adds no failure path.

### Shunt sizing (*calculated*, INA226 datasheet: 2.5 µV shunt LSB, 81.92 mV full scale)

| | Full scale | Current LSB | At the pump's draw |
|---|---|---|---|
| S1, S2, S4 (3.75 mΩ) | 21.8 A | 0.67 mA | 22.5 mV, 0.14 W at 6 A (P1); 28.1 mV, 0.21 W at 7.5 A (P2) |
| S3 (15 mΩ) | 5.46 A | 0.17 mA | 52.5 mV, 0.18 W at 3.5 A |

S1, S2 and S4 stay inside two-thirds of the shunt's 20 A rating, the
continuous derating, up to about 13 A. That covers P2 at 7.5 A, and P4
whatever its draw turns out to be within that.

### What each INA226 reports

| | Address | Shunt | Publishes |
|---|---|---|---|
| P1 | 0x40 | S1 | volts, amps |
| P2 | 0x41 | S2 | volts, amps |
| P3 | 0x44 | S3 | volts, amps |
| P4 | 0x45 | S4 | volts, amps |

Firmware derives `running` from amps.

Each INA226's bus-voltage pin taps that pump's feed downstream of its breaker
or fuse and upstream of its switch or Q8, through a series resistor
(*stand-in*, 10 kΩ). A tripped breaker or blown fuse therefore reads as zero
volts, which is an alarm.

## Dry-bilge pump behaviour (firmware requirements)

- **Runtime cap is the hard stop**, a config value. It is required because a
  pressure-type diaphragm pump tolerates only short dry runs.
- **Current-drop "bilge is dry" detection is unproven.** Dry and wet current
  have to be measured on the bench before it gates anything.
- *Guess:* the FLO-2202's 35 PSI rating suggests a built-in pressure switch.
  Discharging overboard it should never reach cutoff, so "commanded on, about
  0 A" would mean a blocked outlet, for example a closed seacock. That is an
  alarm.
- **Hardware watchdog:** the ESP32's watchdog resets the chip if firmware
  hangs. The reset releases the GPIO to its pulldown and turns Q8 off, so the
  runtime cap holds against a hang with the output latched on.
- **Fails off:** unpowered, booting, hung-low or reset means Q8 is off.

## Open questions

- P2's fuse, from its manual.
- P4's model, its draw, its fuse and its feed.
- What triggers the dry-bilge pump: a schedule, a float, or a manual Signal K
  PUT.
- Whether P3 has a pressure switch. Check on the bench.
- The nav-light open questions (masthead legs, two legs hot at once, ESP32
  dedicated or shared) carry over from
  [nav-light-controller.md](nav-light-controller.md).
