# HALMET engine monitor — plan

Status: planning, 2026-09-26. Nothing here is a ruling; defaults are Claude's
picks and change when Mark says so or the bench says otherwise.

End state: HALMET in the engine compartment, publishing engine data to
Signal K (and NMEA 2000), doing useful work with minimal manual labour.
Milestone 1: working on the bench. Milestone 2: working on the boat.

## What the board is (verified against Hat Labs' docs, 2026-09-26)

Sources: https://docs.hatlabs.fi/halmet/docs/hardware/,
https://github.com/hatlabs/HALMET-hardware,
https://github.com/hatlabs/HALMET-example-firmware,
https://github.com/hatlabs/discussions/discussions/107

| Input | Count | Design | Use on Symphony |
|---|---|---|---|
| Analog A1–A4 | 4 | ADS1115 16-bit, 0–32 V, each with a **jumper-enabled 10 mA current source** for resistive senders (≤ ~300 Ω). Jumper **out** = measure in parallel with an existing gauge, the gauge supplies the current. Jumper **in** = HALMET is the sender's only load. | resistive senders, if the panel has gauges (Q1) |
| Digital D1–D4 | 4 | ±32 V tolerant, Schmitt trigger ~1.5 V threshold, **not** galvanically isolated. Any of them can count pulses (ESP32 PCNT); D1 is the tacho by convention. Alternator W terminal: connect direct, **in-line fuse required**, LP solder jumper (~2.3 kHz) if noisy. | D1 tach; D2/D3 oil-pressure and coolant-temp **switches** (Yanmar stock) |
| 1-Wire | 1 header | pull-up and protection on board; DQ on **GPIO4** (traced in the schematic, rev 1.0.1; not silkscreened) | DS18B20 chain |
| I2C | Qwiic + 2.54 mm header | shares the bus with the onboard ADS1115 (0x4b) | optional BME688 |
| NMEA 2000 | 4-pin screw terminal | bus-powered, 5–32 V | power + data if the backbone reaches (Q3) |
| Flash | ? | documented as 4, 8 and 16 MB in three places; example firmware builds for 8 MB | `esptool flash_id` on the bench settles it |

Co-existence with existing senders: supported by design. A switch-type sender
(lamp/buzzer) goes to a digital input in parallel with the lamp. A gauge-type
resistive sender goes to an analog input with the current-source jumper out;
calibrate the curve against the gauge once, on the boat.

## Mark's answers, 2026-09-26 (to the six questions asked the same day)

1. **Panel: probably all stock** (Yanmar switches → lamp/buzzer). The oil
   sender may be dead; wiring may be crusty. → D2 oil-pressure switch, D3
   coolant-temp switch, wired in parallel with the lamps. Troubleshooting
   the senders is a boat step in its own right (continuity + switch test
   with a meter, before the HALMET is blamed for anything).
2. **Tach: not the alternator.** Mark doesn't trust it (a future smart
   alternator can stop pulsing on command). There is a sender on the
   flywheel now, function unknown. → Step one is to identify it and scope
   its output (a magnetic pickup gives a small AC sine whose amplitude falls
   with RPM; a Hall or optical sender gives a clean square wave). The
   HALMET's digital input wants edges of about 1.5 V or more, so a weak
   pickup may need conditioning or replacing with a Hall-effect sender on
   the flywheel or a pulley. Open; D1 either way.
3. **Power: separate 12 V, not bus power.** 3–6 ft from where the house
   wiring terminates; waterproof 12 V connectors already on hand; the N2K
   connector for the enclosure isn't. → 12 V + WiFi to Signal K. N2K output
   stays compiled in and can be added later by pulling a drop; reversible.
4. **Nothing is installed on the boat**; the earlier compartment-monitor
   ESP32 (DHT22 + flame sensor, in `~/symphony-sensesp`) was home
   experiments. → Fold its jobs into the HALMET when convenient.
5. **Enclosure: IP65 or better, from Hat Labs**, PG7 glands plus SP-series
   circular connectors: 2-pin (DC), 3-pin (DS18B20), one 5-pin. → Cable
   runs: 12 V in (2-pin), one DS18B20 chain (3-pin), tach (2-pin or gland),
   two switch senders (gland), spare 5-pin for a thermocouple or I2C tether.
6. **Gas sensors: separate project**, its own box and ESP32, but kicked off
   now — see [gas-sensor-box-plan.md](gas-sensor-box-plan.md).

Firmware repo: local `~/symphony-halmet` is fine. When it gets a GitHub
remote it goes under Mark's own account, not the organisation the earlier
SensESP repos were put under; that placement was a mistake.

Thermocouples: Mark has K-types (with SPI interface boards, probably
MAX6675/MAX31855) on hand. DS18B20 tops out at 125 °C, so it is fine on the
wet exhaust hose and the block, and not fine on the dry exhaust manifold or
the elbow before water injection, which run well past that. → K-type for the
manifold/dry elbow, DS18B20 elsewhere; a bench experiment to prove the
thermocouple chain is a nice-to-try step in its own right.

## Temperature points (DS18B20 chain, default set)

- coolant: thermostat housing or head, hose-clamped → `propulsion.main.coolantTemperature`
- exhaust hose after injection → `propulsion.main.exhaustTemperature`
- alternator case → `electrical.alternators.main.temperature`
- raw-water pump body or intake hose (flow proxy)
- compartment ambient → `environment.inside.engineRoom.temperature`

## Firmware

`~/symphony-halmet` — local git repo, imported from
hatlabs/HALMET-example-firmware (remote `upstream`), SensESP 3.5, ESP-IDF
dual-framework build (`pio run -e halmet_espidf` is the one to flash;
`-e halmet` is the fast compile check). Kept separate from `~/symphony-sensesp`
because the espidf build carries its own sdkconfig/CMake and the monorepo is
plain esp32dev + arduino. No GitHub remote yet.

Done: hostname `symphony-halmet`. The example already does D1 tach → PGN
127488 + SK, D2/D3 alarms → PGN 127489, A1 tank level.

## Sequence

1. Bench, step zero: flash the example as-is (`pio run -e halmet_espidf -t
   upload`), join WiFi, see it in the dev stack's Signal K. `esptool
   flash_id` for the real flash size. Test D1 with the built-in 380 Hz test
   pin (GPIO 33 → D1). (session, Mark plugs in USB; `pio run -e halmet`
   already compiles clean on the WSL box, 2026-09-26; still waiting on the
   board)
   - 1-Wire GPIO **confirmed as GPIO4** from `HALMET.kicad_sch`/
     `onewire.kicad_sch` (DQ net traced to the ESP32-WROOM-32 IO4 pin, rev
     1.0.1) rather than benched — done from the schematic without the board
     in hand, 2026-09-26.
2. Bench: 1-Wire DS18B20 chain to the SK paths above; drop the tank code;
   alarms named oil-pressure / coolant-temp; optional MAX31855 K-type on
   SPI as the thermocouple experiment. (session)
   - Code done 2026-09-26 (`~/symphony-halmet` `8a2471e`, compile-checked
     with `pio run -e halmet`): `halmet_onewire.{h,cpp}` reads the five
     default points by 1-Wire bus-scan index (no probes on hand yet to get
     real addresses) and publishes Kelvin to the plan's SK paths; tank
     sender code removed; D2/D3 alarms renamed to `alarm.oil-pressure` /
     `alarm.coolant-temp`. Raw-water intake has no settled SK path
     convention — `propulsion.main.rawWaterTemperature` is a guess, flagged
     in the code. Still needs the actual chain on the bench to switch from
     index- to address-based lookup. MAX31855 K-type experiment not
     started.
3. Boat, diagnostics before install: identify and scope the flywheel tach
   sender; meter the oil-pressure and coolant switches and their wiring.
   (Mark's hands, session writes the checklist)
4. Boat, install: mount, 12 V run, tach to D1, switches in parallel to
   D2/D3, probes clamped on; verify over Signal K. (Mark's hands)
5. Gas-sensor box runs as its own track; N2K drop later if wanted.
