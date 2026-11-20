# Software: pypilot and RTIMULib2

Checked 2026-11-20 by listing the files in pypilot's fork,
[seandepagnier/RTIMULib2](https://github.com/seandepagnier/RTIMULib2). No driver source
was read.

## What the fork already has

| Kind | Files |
|---|---|
| Fusion | `RTFusionRTQF`, `RTFusionKalman4`, `FusionMadgwick`, `FusionMahony` |
| IMU drivers | BMX055, BNO055, GD20HM303D, GD20HM303DLHC, GD20M303DLHC, HMC5883L+ADXL345, ICM20948, LSM6DS33+LIS3MDL, LSM9DS0, LSM9DS1, MPU9150, MPU925x |

OpenPlotter's pypilot page lists three supported models: ICM-20948 (recommended), MPU-9250
and MPU-9255.

## What follows for a new chip

- A driver hands the library raw gyro, accelerometer and magnetometer readings. The
  library fuses them. No fusion code is ours to write.
- A chip's own 6-axis fusion goes unused: it never sees the magnetometer, so it cannot
  give heading.
- One driver covers a pair: the 6-axis chip and the magnetometer together, as the existing
  LSM6DS33+LIS3MDL driver does.

## Driver effort, agent's estimate, nothing read or measured

| Chip | Starting point |
|---|---|
| ISM330DHCX | Same register family as the LSM6DS33 driver already there |
| LSM6DSV16X | Same maker; range settings moved to different registers in this generation (from memory) |
| ICM-42688-P | Nothing related; banked registers |
| ISM330BX, ICM-45686 | Not looked at |

Solace has set aside "an older part's driver already exists" as a reason to pick a chip;
see `criteria.md`. The table is here for effort planning only.
