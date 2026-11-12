# HALMET sensors by port — shopping and bench list

Condensed from `reference/halmet_firmware.md`, 2026-11-12. Search terms
marked *(pick)* are Claude's suggestion; the source names no part.

| Port | Sensor (search term) | What it does | Bench hookup |
|---|---|---|---|
| D1 | Flywheel tach sender (type unknown); if replaced, Hall proximity sensor e.g. NJK-5002C *(pick)* | Engine RPM from pulses | 2 wires; IO33 → D1 jumper gives a 380 Hz test signal; a Hall sensor also needs 12 V + GND |
| D2 | Stock Yanmar oil-pressure switch | Low-oil-pressure alarm, tapped off the lamp wire | 2 wires; toggle switch to simulate |
| D3 | Stock Yanmar coolant-temp switch | Overheat alarm, tapped off the lamp wire | as D2 |
| D4 | IR flame sensor module, LM393 *(pick)*; several can share D4 | Sees flame light; fuel-spray fire warning | 3 wires: VCC 3.3–5 V, GND, DO → D4 |
| A1 | wire only | Start-battery voltage | 12 V bench supply, in-line fuse |
| A2 | wire only | Alternator output voltage | as A1 |
| A3 | wire only | Ignition on/off (key switch) | as A1, via a switch |
| A4 | 0.5–4.5 V pressure transducer, 100 psi (oil) or vacuum range (fuel), one or the other *(pick)* | Oil pressure, or a clogging fuel filter | 3 wires: 5 V, GND, signal; a pot simulates it |
| 1-Wire | DS18B20 waterproof probe, up to ~10 on one chain | Temperatures: coolant, wet exhaust, alternator, raw water, engine room, gearbox, shaft seal, oil sump, muffler | one 3-pin chain (V, GND, data); pull-up is on the board |
| I2C | MCP9600 + K-type thermocouple; or MAX31855 (on hand) on the GPIO header | Dry exhaust elbow temperature (beyond DS18B20's 125 °C); fastest raw-water-loss warning | 4 wires: 3.3 V, GND, SDA, SCL |
| I2C | ADS1115 breakout at 0x48 | Four more analog inputs, for the next two rows | each input needs a 100k/10k divider; it can't take 12 V directly |
| ext. A | Water-in-fuel probe (depends on the filter bowl) | Water in the fuel | |
| ext. A | wire only | Bilge pump running, cycle count | |
| I2C | INA228 + shunt; waits on the alternator-regulator choice | Alternator current | |
| I2C | SSD1306 0.96" OLED (optional) | Local display | |

Open mismatch: the engine plan says the D inputs are not galvanically
isolated; `reference/halmet_firmware.md` says they are. Matters if the bench
supply and the board share a ground.
