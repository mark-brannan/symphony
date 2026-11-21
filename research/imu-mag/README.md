# IMU and magnetometer

See also: [`reference/pypilot_containerization.md`](../../reference/pypilot_containerization.md), [`runbooks/pypilot.md`](../../runbooks/pypilot.md). The printed tray for the sensor is workshop's [`imu-tray`](https://github.com/mark-brannan/workshop/tree/main/projects/imu-tray).

Choosing the motion sensor (gyro and accelerometer) and the magnetometer for the boat's
attitude and heading, read by pypilot through its RTIMULib2 fork with a driver we write.

Nothing is chosen and nothing is built. This folder is the working record for a
multi-criteria choice made over several sessions: research, criteria, decisions,
experiments, proofs of concept and, later, the board.

## What is in here

| File | Holds |
|---|---|
| [`criteria.md`](criteria.md) | The criteria the choice is scored on, and who stated each |
| [`imu-candidates.md`](imu-candidates.md) | The 6-axis chips looked at so far: specs, dates, boards, prices, each with its source |
| [`mag-candidates.md`](mag-candidates.md) | Magnetometers: only what has come up; not yet researched |
| [`software.md`](software.md) | What pypilot's RTIMULib2 fork already has, and what a new driver must do |
| [`placement.md`](placement.md) | Where the sensor goes on the boat, and why |
| [`claims-reviewed.md`](claims-reviewed.md) | Outside claims checked against sources: a chatbot's case for the ISM330DHCX, the ocean-imu project |
| [`decisions.md`](decisions.md) | The owner's decisions, one dated line each |
| [`sources.md`](sources.md) | Every link used |

`experiments/` arrives with the first bench test, one folder per test, with its data.
Driver and firmware trials and the board are things to make; they go to workshop as a
project when they start.

## Where it stands, 2026-11-20

- Leading 6-axis candidate on the criteria stated so far: **LSM6DSV16X**. It is the newest
  chip found on a plug-in Qwiic board at a hobby price (about US$25).
- Two newer chips, the ISM330BX and ICM-45686, have no plug-in board found and no spec
  comparison yet.
- The magnetometer has not been researched.

## Open questions

| Question | What would answer it |
|---|---|
| How do the ISM330BX and ICM-45686 compare on specs? | Two datasheet reads |
| Is a bare chip on our own board acceptable, or must it be a ready-made Qwiic board? | The owner |
| Which magnetometer? | Research not started; `mag-candidates.md` |
| Do the chips differ in real gyro drift over temperature? Datasheets don't separate them | Bench log of two boards through a warm-up; about two breakout boards |
| Are Bosch and other makers worth a look? Only ST and TDK were searched | One search pass |
| Is the LSM6DSV16X's operating range really −40 to +85 °C, and what is its bias instability? | Datasheet DS13510; ST has not published the second |
