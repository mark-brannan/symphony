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
| 1-Wire | 1 header | pull-up and protection on board; GPIO not yet confirmed (read the schematic or bench it) | DS18B20 chain |
| I2C | Qwiic + 2.54 mm header | shares the bus with the onboard ADS1115 (0x4b) | optional BME688 |
| NMEA 2000 | 4-pin screw terminal | bus-powered, 5–32 V | power + data if the backbone reaches (Q3) |
| Flash | ? | documented as 4, 8 and 16 MB in three places; example firmware builds for 8 MB | `esptool flash_id` on the bench settles it |

Co-existence with existing senders: supported by design. A switch-type sender
(lamp/buzzer) goes to a digital input in parallel with the lamp. A gauge-type
resistive sender goes to an analog input with the current-source jumper out;
calibrate the curve against the gauge once, on the boat.

## Open questions (asked 2026-09-26, answers pending)

1. Panel: stock Yanmar switches (lamp + buzzer) or aftermarket gauges with
   resistive senders? Photo of the panel back + senders answers it.
   Default until known: switches → D2 oil pressure, D3 coolant temp.
2. Tach: electric (alternator W / tach terminal) or mechanical cable?
   Default: alternator W → D1, fused.
3. Does the N2K backbone reach, or could reach, the engine compartment?
   Default: yes → bus power + bus data, WiFi as second path, no separate 12 V run.
4. Existing engine-room ESP32 (DHT22 + flame, `~/symphony-sensesp` env
   `engine-room`): deployed, bench, or never? Default: fold its jobs into the
   HALMET when convenient; not a blocker.
5. Enclosure and connector inventory (IP rating, gland count) → number of
   cable runs the layout designs for.
6. Gas sensors: default is a **separate** vented box with its own cheap ESP32
   (MQ heaters ~150 mA each; the HALMET box stays sealed), BME688 rides along
   on its I2C. `~/sensesp-mq-gas-sensors` is the starting point. Tethered
   breakout from the HALMET stays open as an option.

Thermocouple: not for now. A DS18B20 strapped to the exhaust hose just past
the raw-water injection catches lost raw-water flow, the failure that
matters. K-type (MAX31855) is a later nice-to-have for dry-elbow EGT.

## Temperature points (DS18B20 chain, default set)

- coolant: thermostat housing or head, hose-clamped → `propulsion.main.coolantTemperature`
- exhaust hose after injection → `propulsion.main.exhaustTemperature`
- alternator case → `electrical.alternators.main.temperature`
- raw-water pump body or intake hose (flow proxy)
- engine-room ambient → `environment.inside.engineRoom.temperature`

## Firmware

`~/symphony-halmet` — local git repo, imported from
hatlabs/HALMET-example-firmware (remote `upstream`), SensESP 3.5, ESP-IDF
dual-framework build (`pio run -e halmet_espidf` is the one to flash;
`-e halmet` is the fast compile check). Kept separate from `~/symphony-sensesp`
because the espidf build carries its own sdkconfig/CMake and the monorepo is
plain esp32dev + arduino. No GitHub remote yet — Mark's call whether it goes
under Dark-Star-LLC like the others.

Done: hostname `symphony-halmet`. The example already does D1 tach → PGN
127488 + SK, D2/D3 alarms → PGN 127489, A1 tank level.

## Sequence

1. Bench, step zero: flash the example as-is, join WiFi, see it in the dev
   stack's Signal K. `esptool flash_id` for the real flash size. Confirm the
   1-Wire GPIO from the schematic. Test D1 with the built-in 380 Hz test pin
   (GPIO 33 → D1). (session, Mark plugs in USB)
2. Bench: 1-Wire DS18B20 chain, N2K senders for coolant/exhaust/alternator
   temps, SK paths above; remove the tank code; alarms named for oil/coolant.
   (session)
3. Answers to Q1–Q3 → analog-input decisions and the cable-run list. (Mark)
4. Boat: mount, N2K drop or 12 V, D1 to alternator W via fuse, switch
   senders in parallel to D2/D3, probes clamped on. (Mark's hands; session
   writes the checklist and verifies over Signal K)
5. Later: gas-sensor box; thermocouple if wanted.
