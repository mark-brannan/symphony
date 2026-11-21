# Outside claims, checked

## 2026-11-20: a chatbot's case that "the ISM330DHCX wins at sea"

Compared the ISM330DHCX, LSM6DSV16X and ICM-42688-P. The spec numbers were mostly real;
the reasoning built on them mostly did not hold.

| Claim | Checks out? | Bears on a boat? |
|---|---|---|
| ISM330DHCX gyro bias instability about 3°/hr | Yes, per ST's blog (5°/hr for its consumer sibling) | Little. Pitch and roll are tied to gravity by the accelerometer and don't wander over a watch |
| Industrial calibration stops the offset shifting with temperature | No. ±0.005 dps/°C in ST's blog, the same figure as the ICM-42688-P datasheet | No. A cabin is well inside every chip's range |
| 9 KB FIFO prevents dropped samples | The size is right | No. It matters only if the host stalls at high sample rates |
| 10-year availability | Yes, from memory of ST's longevity programme; not searched | Somewhat |
| ICM-42688-P is overkill and weaker on drift | Half. Its gyro noise equals the LSM6DSV16X's; its drift is unpublished | No |
| LSM6DSV16X's on-chip fusion is fooled by turns and heel | Misleading. Any 6-axis fusion reads a turn as tilt; the ISM330DHCX has no on-chip fusion; sustained heel is real tilt | Small |

Not confirmed at the time: the LSM6DSV16X's temperature range and bias instability, and
the ISM330DHCX's own noise figure.

## 2026-11-20: the ocean-imu project's announcement of 2026-10-06

[ocean-imu](https://github.com/bareboat-necessities/ocean-imu) is an open-source (MIT)
library of marine attitude and heave filters, with firmware for the M5Stack AtomS3R. Its
README and GitHub record were read on 2026-11-20; its result tables and documents were
not opened.

| Claim, paraphrased | Checks out? | Bears on our choice? |
|---|---|---|
| Heave error is within 5% of significant wave height | Not found. The README text gives no figure; its results are from a simulated 28 ft vessel at 5 kn in a 1.5 m sea, and it says sea-trial evidence varies by filter | No. We have no heave requirement |
| Five filter methods: two quaternion Kalman, two observers, one Lie-group | The README names about ten, three of them marked experimental. The primary is a 27-state Lie-group filter | No |
| The simulation applies a vessel response to several sea states | Yes, with the README's own limit: no hull-specific forward-speed or steering dynamics | No |
| Degradation is studied for engine vibration and for mounting away from the centre of gravity | Yes, such a study is listed. Its numbers were not read | Somewhat; see below |
| All methods now run better on the AtomS3R | The AtomS3R is the only board named. Commits of the same day were still repairing its magnetometer start-up | No |

How it sits beside this folder's work:

- A different layer. This folder picks the chips; ocean-imu is the maths run on their
  readings, on its own microcontroller, sent out as NMEA. It does not mention pypilot and
  would not feed pypilot's steering.
- It reports its results from a low-cost consumer sensor. That fits the note in
  [`criteria.md`](criteria.md) that gyro noise differences between candidates are below
  what a hull shows. This is the agent's inference, and the AtomS3R's chips (BMI270 and
  BMM150) are from memory, not from the repo.
- Its off-centre mounting study matters to heave more than to attitude.
  [`placement.md`](placement.md) weighs attitude only.
- If heave and wave data are ever wanted, it is a separate standalone sensor to try, not
  a change to the chip choice.
