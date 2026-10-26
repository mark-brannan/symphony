# HALMET firmware — sensors and capabilities

What the HALMET in the engine compartment measures, where each sensor
attaches to the engine or the boat, and which HALMET input it uses. The
firmware lives in `firmware/halmet/`; the bench-to-boat sequence lives in the
engine plan under `intermediate_files/claude_slop/halmet-engine-plan.md`.

The HALMET is an engine monitor and an early-warning layer. It runs alongside
the stock Yanmar 3QM30 lamps, buzzer and gauges, never in place of them, and
it never commands the engine.

## Principles

- **Parallel, not in-line.** Every stock sender keeps driving its lamp or
  gauge; the HALMET taps the same wire. A dead HALMET leaves the panel as it
  was.
- **Read-only on the engine.** No output pin drives a relay, a shutdown, a
  blower or a suppression system.
- **A missing sensor publishes nothing.** A disconnected probe, an
  out-of-range reading or a sensor that never answered sends no value to
  Signal K, rather than a plausible-looking wrong one.
- **Supplementary, not certified.** Fire and gas signals here add warning
  time; the certified smoke, CO and LPG alarms remain the life-safety
  devices.
- **Signal K first, NMEA 2000 where a PGN fits.** WiFi to Signal K is the
  primary link; the N2K output stays compiled in for the day a drop reaches
  the engine compartment.

## Integration points on the board

Verified against Hat Labs' documentation and the HALMET-hardware schematic
(rev 1.0.1).

| Resource | Electrical | Count | Allocated to |
|---|---|---|---|
| Digital D1–D4 | ±32 V tolerant, Schmitt trigger ~1.5 V, not isolated; any can count pulses (PCNT) | 4 | D1 tach · D2 oil-pressure switch · D3 coolant-temp switch · D4 IR flame |
| Analog A1–A4 | ADS1115 16-bit, 0–32 V via 33.3/3.3 divider; per-channel jumper-enabled 10 mA current source for resistive senders | 4 | A1 start-battery voltage · A2 alternator output voltage · A3 ignition sense · A4 spare (fuel vacuum, or a resistive sender) |
| 1-Wire | header, pull-up and protection on board, DQ on GPIO4 | 1 bus | DS18B20 chain |
| I2C | Qwiic + 2.54 mm header, shared with the onboard ADS1115 at 0x4b | 1 bus | SSD1306 display (0x3c), thermocouple amplifier, second ADS1115, current monitor |
| GPIO header (J201) | 2×10, raw 3.3 V ESP32 pins, no protection; the ESP32 sheet labels IO5, IO16, IO17, IO32–IO35, SENSOR_VP/VN and JTAG | — | SPI thermocouple boards if used; IO33 is the 380 Hz test output |
| NMEA 2000 | 4-pin screw terminal, CAN on GPIO18/19 | 1 | PGN 127488, 127489, 130316 |
| Enclosure | IP65, PG7 glands, SP circular connectors | 2-pin, 3-pin, 5-pin | 12 V in · DS18B20 chain · I2C tether or thermocouple |

The digital and analog inputs are both oversubscribed once everything below
is fitted. The relief valves, in order: an A input reads any 12 V on/off
signal as well as a D input does (a firmware threshold, no hardware); a
second ADS1115 on I2C at 0x48 adds four channels, each needing its own
external divider and protection; the GPIO header takes 3.3 V logic only.

## In the firmware today

| Capability | Input | Engine / boat point | Signal K | NMEA 2000 | Gap |
|---|---|---|---|---|---|
| Tachometer | D1, PCNT | flywheel sender, type unidentified | `propulsion.main.revolutions` | 127488 speed | sender not yet scoped; pulses-per-rev uncalibrated |
| Low oil pressure | D2 | stock Yanmar oil-pressure switch, parallel to the lamp | `alarm.oil-pressure` | 127489 status | polarity unmeasured on the boat |
| Coolant over-temperature | D3 | stock Yanmar water-temp switch, parallel to the lamp | `alarm.coolant-temp` | 127489 status | the upstream example's active-low inversion is still in place |
| Coolant temperature | 1-Wire index 0 | thermostat housing or head | `propulsion.main.coolantTemperature` | — | |
| Wet exhaust temperature | 1-Wire index 1 | exhaust hose after injection | `propulsion.main.exhaustTemperature` | — | |
| Alternator case temperature | 1-Wire index 2 | alternator body | `electrical.alternators.main.temperature` | — | |
| Raw-water temperature | 1-Wire index 3 | raw-water pump body or intake hose | `propulsion.main.rawWaterTemperature` | — | path is not in the Signal K spec |
| Engine-room ambient | 1-Wire index 4 | compartment air | `environment.inside.engineRoom.temperature` | — | |
| A2 voltage | A2 | none (upstream example) | `sensors.a2.voltage` | — | placeholder; replaced below |
| Local display | I2C SSD1306 | on the board | — | — | |
| N2K watchdog, heap and stack status | — | — | — | — | |
| Test pulse | IO33 | — | — | — | enabled by default; off before install |

Gaps that cut across the table:

- Probes are addressed by bus-scan index, so adding or losing one shifts
  every later reading onto the wrong path. They move to ROM-address lookup,
  with the address-to-location map set in the web UI.
- A missing DS18B20 reads −127 °C and publishes 146.15 K.
- Alarms publish as `alarm.*` booleans, not Signal K `notifications.*`.

## Planned

### Temperatures

| Sensor | Input | Engine / boat point | Signal K | Why |
|---|---|---|---|---|
| DS18B20 | 1-Wire | the five above, by ROM address | as above | |
| DS18B20 | 1-Wire | gearbox case | `propulsion.main.transmission.oilTemperature` | a slipping or low-oil gearbox runs hot first |
| DS18B20 | 1-Wire | shaft seal (dripless) housing | path TBD | a dry dripless seal overheats in minutes |
| DS18B20 | 1-Wire | oil sump, clamped low on the pan | `propulsion.main.oilTemperature` | trend and load proxy |
| DS18B20 | 1-Wire | water-lift muffler body | path TBD | a second raw-water-loss signal, slower than the elbow |
| K-type thermocouple | I2C (MCP9600) or SPI on J201 (MAX31855, on hand) | dry exhaust manifold / elbow before water injection | path TBD | the fastest raw-water-loss warning on the engine; DS18B20 tops out at 125 °C |

Exhaust-elbow and wet-exhaust temperature together are the raw-water-flow
signal: flow stops, both climb within a minute or two, before the coolant
switch trips.

### Engine state and alarms

| Sensor | Input | Engine / boat point | Signal K | Why |
|---|---|---|---|---|
| Ignition sense | A3, thresholded | key-switch run circuit, fused | feeds `propulsion.main.state` | engine state that does not depend on RPM or the alternator |
| Oil-pressure transducer, 0.5–4.5 V or resistive | A4 | in a tee at the oil-pressure switch port | `propulsion.main.oilPressure` | only if the stock sender is replaced; the switch stays on D2 |
| Fuel vacuum transducer | A4 | between the primary filter and lift pump | path TBD | clogged primary filter shows as rising vacuum before the engine starves |
| Water-in-fuel probe | spare A, thresholded | primary filter bowl, if the bowl has a probe port | notification | |

### Fire

| Sensor | Input | Engine / boat point | Signal K | Why |
|---|---|---|---|---|
| IR flame module (760–1100 nm phototransistor + comparator) | D4, active-low | aimed at the fuel filter and injection pump side | `notifications.propulsion.main.fire` (TBD) | fuel-spray fire is the engine-room fire with the shortest fuse |
| Second and third IR flame modules | D4 wired-OR, or analog outputs on spare A inputs | alternator/starter side; exhaust elbow | as above | the comparator outputs are open-collector, so several can share D4; analog outputs give intensity per module |
| Rate-of-rise | derived | engine-room ambient DS18B20 | notification | a second, independent fire signal from a probe already fitted |

The flame code exists in `~/symphony-sensesp` (`addFlameSensor`, active-low,
debounced) and ports across. The engine room is dark, which is the condition
these modules need; sunlight through an open hatch triggers them.

### Electrical

| Sensor | Input | Engine / boat point | Signal K | Why |
|---|---|---|---|---|
| Start-battery voltage | A1 | start battery positive, fused at the battery | `electrical.batteries.start.voltage` | nothing on the boat publishes it today |
| Alternator output voltage | A2 | alternator B+ stud, fused | `propulsion.main.alternatorVoltage`; 127489 alternator potential | charging-or-not, independent of the Victron side |
| Alternator current | I2C INA228 + shunt, or Hall clamp on an A input | alternator output lead | `electrical.alternators.main.current` | waits on the alternator and regulator choice: a smart regulator reports its own current |
| Bilge pump run | spare A, thresholded | pump positive lead downstream of the float switch | path TBD; cycle count | pump cycles are the leak trend |

The house bank, the JBD packs and the shunt stay with the Cerbo GX; the
HALMET does not duplicate them.

### Derived capabilities (no new hardware)

| Capability | From | Signal K | NMEA 2000 |
|---|---|---|---|
| Engine run hours, persisted in flash | RPM > 0, or ignition sense | `propulsion.main.runTime` | 127489 total hours |
| Engine state | ignition, RPM, oil-pressure switch | `propulsion.main.state` | — |
| Raw-water-loss alarm | exhaust-elbow and wet-exhaust slope while running | notification | — |
| Charging fault | alternator voltage below threshold while running | notification | 127489 status |
| Probe-fault notification | DS18B20 missing or out of range | notification | — |
| Temperatures over N2K | DS18B20 and thermocouple | — | 130316 temperature, extended range |

## Gas detection: on the gas-sensor box

Gas sensing is its own device — a separate ESP32 in a vented box, low where
fumes pool — not the HALMET. The HALMET box is sealed to IP65, so a gas or
humidity sensor inside it measures only the enclosure's own air, and MQ
heaters draw about 150 mA each at 5 V. Plan:
`intermediate_files/claude_slop/gas-sensor-box-plan.md`.

| Sensor | Gas box input | Point | What it gives |
|---|---|---|---|
| BME688, or its successor BME690 | I2C | engine compartment, low | temperature, humidity, pressure, VOC index (Bosch BSEC library) |
| MQ-2 | ADS1115 | propane locker drain and lowest bilge point | LPG / propane, smoke |
| MQ-7 | ADS1115 | engine compartment | CO trend, not a CO alarm |
| MQ-135 | ADS1115 | engine compartment | general air quality |

The HALMET's share of gas detection is one digital input: if a certified
LPG or CO alarm has an alarm-relay contact, D-input it into Signal K.

## Considered and not done

| Option | Why not |
|---|---|
| MQ-series sensors on the HALMET | heater current and a sealed enclosure; they live on the gas box |
| BME688/BME690 inside the HALMET enclosure | measures the sealed box, not the compartment; a Qwiic tether through the 5-pin connector is the only way it would work |
| Tach from the alternator W terminal | a smart regulator can stop it pulsing; the flywheel sender is the source |
| DS18B20 on the dry exhaust manifold or elbow | 125 °C ceiling; thermocouple instead |
| DHT22 (from the earlier engine-room node) | DS18B20 and the gas box's BME688 cover temperature and humidity |
| Turbine flow meter in the raw-water circuit | adds restriction and a clog point to the circuit it is meant to protect; exhaust temperatures give the same warning |
| Fuel flow meter | a 3QM30 burns too little for hobby-grade meters, and the return line means two meters and a difference |
| Driving anything — shutdown, blower, suppression release | read-only principle; a firmware fault must not stop the engine |
| Cheap MQ sensors as the CO or LPG alarm | uncalibrated and drift-prone; certified alarms do that job |
| Oil-level and exhaust back-pressure senders | no practical fitting on the 3QM30 |
| Rudder angle, IMU for the autopilot | not engine-compartment; pypilot has its own board |
| House battery voltage and current | the Cerbo GX and Victron shunt already publish them |

## Open

- Whether this 3QM30 is raw-water cooled (as the stock 3QM30 is) or
  converted to fresh-water cooling. It decides whether "coolant" and
  "raw water" are one circuit or two, and where the probes go.
- What the flywheel sender is, and its signal on a scope.
- Polarity of the stock oil-pressure and water-temperature switches.
- Whether the primary fuel filter bowl has a water-in-fuel port.
- Whether the boat has a certified LPG or CO alarm with a relay contact.
- The J201 pinout, bench-checked before anything is wired to it.
