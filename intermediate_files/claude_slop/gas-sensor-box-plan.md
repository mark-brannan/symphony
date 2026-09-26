# Gas-sensor box — plan

Status: kicked off 2026-09-26 as its own track, separate from the HALMET
engine monitor. Nothing here is a ruling.

End state: a small vented box, low in the engine compartment or bilge where
fumes pool, with its own ESP32, publishing air-quality data to Signal K and
raising alarms.

## Defaults (Claude's picks, open to change)

- Own ESP32 and own 12 V feed. MQ heaters draw ~150 mA each at 5 V; keep them
  off the HALMET's sealed box and supply.
- Sensors: MQ-2 (LPG/propane, smoke), MQ-7 or MQ-135 (CO / general), BME688
  on I2C for temp/humidity/pressure/VOC. MQ outputs are analog only → an
  ADS1115 on I2C rather than the ESP32's noisy ADC.
- Firmware: `~/sensesp-mq-gas-sensors` (SensESP 3.5; DHT22 + MQ-135 done,
  R0 calibration not) is the starting point; re-home it under Mark's own
  GitHub account.
- Enclosure: vented, printed or drilled; the backlog already lists
  "3D-print gas sensor / BME688 / IMU cases" under Someday/Maybe.

## Sequence

1. Bench: MQ-2 + MQ-135 + BME688 + ADS1115 on one ESP32, raw values into
   Signal K. 24–48 h MQ burn-in before trusting anything.
2. Bench: R0 calibration in clean air, ppm curves, SK paths and alarm
   thresholds.
3. Boat: placement, 12 V, mount, verify.

## Open

- Which MQ sensors Mark actually has on hand.
- Whether the BME688 belongs here or in the HALMET box (default: here).
