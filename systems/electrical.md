# Electrical

### Victron VE.CAN to NMEA 2000 cable, DIY

RJ45 A vs B: brown is the same, blue is the same, green and orange are swapped.

N2K male pinout against cable wire colors:

| Pin | Signal | Color |
|---|---|---|
| 1 | Shield | Brown |
| 2 | NET-S (+V) | White |
| 3 | NET-C (−V) | Blue |
| 4 | NET-H (CAN-H) | Black |
| 5 | NET-L (CAN-L) | Gray |

Minimum required for T-568A to N2K: white/brown (RJ45 pin 7) to N2K pin 4
(lower right), and brown (RJ45 pin 8) to N2K pin 5 (center).

No power is carried, so drop RJ45 pins 3 and 6 (A: orange and orange/white;
B: green and green/white) and N2K pins 2 and 3. Optionally keep negative on
RJ45 pin 3 (white/green in A, white/orange in B). Drop shield pin 1 at the
N2K end, or tie it back to negative on pin 3.

### NMEA 2000 device list

Raspberry Pi, AIS, VHF radio, depth transducer, wind speed, radar,
multi-signal converter, MFDs, chart plotter at helm, second chart plotter
at desk.

Undecided: secondary temperature, barometer, battery monitors, alarms and
security devices.

### Lighting sub-panel

Nav lights (running / off / anchor), nav lights (sailing vs steaming),
emergency strobe, courtesy lights, engine room lights, compass and windex
light (combined with nav lights), spreader lights, other deck lights
(cockpit, underwater).

Light types to account for: bi-color deck, masthead (steaming), anchor,
stern, tri-color, red-over-green, compass, windex.

### Alternate DC sub-panel

Nav/comm (NMEA 2000, AIS, wifi), displays, VHF, radar, utility lights
(engine room, binnacle), courtesy lights, cabin lights.

### DC main panel

DC accessory circuit (USB chargers), water pressure, LPG, radar, stereo,
windlass, refrigerator, water maker, heater, bow thrusters, Starlink,
wash down, discharge pump, fans.

### Power distribution

**DC accessory:** USB outlets, DC sockets, buck converters for 9V and
chargers, fans.

**Main cabin lights:** buck converters for 24V LEDs, chart light,
port/starboard or fore/aft split, overhead.

**Individually switched:** courtesy lights, engine room, compass light,
windex light, deck lights (spreader, cockpit, deck).

**Simple panel switching plus terminal:** water pressure, LPG, radar,
stereo, windlass, refrigerator, water maker, heater, bow thrusters,
Starlink, wash down, discharge pump.

**Unswitched, fused:** NMEA 2000, network/wifi/4G modem, SignalK, AIS,
Victron Cerbo and SmartShunt, bilge pumps and high water alarm, ESP32
circuits, LPG and CO detectors.

### Momentary / toggle switches

AIS silent mode, engine emergency start (bank swap), MOB.

### Helm pod concept

Bow thruster joystick, VHF remote mic, chart plotter, MFDs, autopilot
controls, phone/tablet holder.

### Purchased components (from order history)

**Charging & batteries**

- Victron Cerbo GX (MK2) — system monitoring/panel
- Victron Blue Smart IP22 charger, 3-output, 120V AC input
- Victron SmartShunt IP65 + VE.Direct cable
- Victron MultiPlus Inverter/Charger, 500VA
- Victron Orion-Tr DC-DC converter, 24/12V 5A
- Victron BatteryProtect, 12/24V 65A
- Victron BMV-702/712 temperature sensor
- Victron Isolation transformer, 3600W 115/230V, auto
- LiFePO4 house battery: 2x ECO-WORTHY 280Ah 12V (Bluetooth, low-temp protection)
- AGM Starting/accessory battery: EBL AGM Group 48R, 12V 70Ah
- ISINSWIFT Dual Battery Isolator, 12V 140A, Voltage Sensitive Relay (VSR) — not rated for lithium batteries
- VEVOR Dual Battery Isolator, 12V 140A, Manual and Automatic VSR with LCD screen — rated for lithium and lead-acid

**Distribution & protection**

- GOGONFLY battery disconnect/master isolator switch, 275A
- Bus bars: 150A 1/4" bus bar, C110 copper flat bar stock, M8 stud bus bars
- DC-DC boost converter, 12V to 24V, 10A/240W

**Wire**

- Marine tinned wire: 8, 10, 14 AWG duplex/triplex
- Ancor marine primary wire: 14 AWG (100 ft), 12 AWG (25 ft)
- Battery cable: 2 AWG, 6 AWG, with assorted lug terminals
- Silicone hookup wire, 18–20 AWG (non-marine, general purpose)

**NMEA 2000 / navigation electronics**

- Garmin Airmar DST810 smart transducer
- Navico/Lowrance DST-810 bronze triducer
- Regatta Processing N2K backbone/drop cables (1m, 2m, 3m) + tee
  connector
- Rudder angle sender, 0–190 ohm

**Shore power**

- 30A shore power extension cord, 12 ft
