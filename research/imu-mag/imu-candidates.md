# 6-axis candidates

Gyro plus accelerometer, no magnetometer. Every value carries its source: **ds** datasheet,
**maker** maker's page or blog, **dist** distributor or store listing, **mem** the agent's
memory, unchecked. Blank means not looked up. Links are in `sources.md`.

Collected 2026-11-20. Prices are undated store listings; treat as approximate.

## Specs

| | LSM6DSV16X | ISM330DHCX | ICM-42688-P | ISM330BX | ICM-45686 |
|---|---|---|---|---|---|
| Maker | ST | ST, industrial | TDK | ST, industrial | TDK |
| Launched | Nov 2022 (maker) | about 2019–20 (mem) | about 2020 (mem) | in production 2024 (maker) | dev kit listed Aug 2023, datasheet v1.0 Jul 2024 (dist, maker) |
| Gyro noise, mdps/√Hz | 2.8 (ds) | 5 (mem) | 2.8 (ds) | | |
| Accel noise, µg/√Hz | 60 (mem) | 60 (mem) | 70 (maker) | | |
| Gyro bias instability | not published | about 3°/hr (maker blog) | not published | | |
| Gyro offset vs temperature | not found | ±0.005 dps/°C (maker blog, part not clearly named) | ±0.005 dps/°C (ds) | | |
| Rated temperature, °C | −40 to +85 (mem) | −40 to +105 | −40 to +85 (dist) | | |
| FIFO | 4.5 KB (ds) | 9 KB (maker) | 2 KB (ds) | | |
| On-chip fusion | 6-axis quaternion and gyro bias estimate (ds) | none | none | | |
| Supply promise | none known | 10 years (mem) | none known | | |

## Boards and prices

| Chip | Plug-in (Qwiic) board | Price |
|---|---|---|
| LSM6DSV16X | SparkFun SEN-21325; smaller SEN-21336 | US$24.54; US$25.50 |
| ISM330DHCX | Adafruit 4502; SparkFun SEN-19764; SparkFun SEN-19895 with an MMC5983MA magnetometer | about €17 at DigiKey; not found; US$45.74 |
| ICM-42688-P | not searched | not searched |
| ISM330BX | none found | not found |
| ICM-45686 | none found; TDK eval boards only | bare chip CA$9.31; eval board about AU$51; dev kit US$99 |

## Notes

- Whether the ISM330BX replaces the ISM330DHCX, or the ICM-45686 the ICM-42688-P: not
  confirmed. TDK sells its two side by side. No end-of-life notice was found for the
  ICM-42688-P.
- Noise in boat terms, agent's estimate: 5 against 2.8 mdps/√Hz is about 0.3 against 0.17°
  of angle wander per root-hour before the accelerometer corrects it.
- Only ST and TDK were searched.
- The ICM-20948 (9-axis, the part in `projects/imu-tray`) is outside this comparison.
