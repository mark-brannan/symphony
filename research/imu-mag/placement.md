# Placement on the boat

From the placement session of 2026-11-20. This is the general reasoning only. That session
went on to weigh named spots against the boat's floor plan (a salon position, a high
position, under the floorboards, a bulkhead by the settee); those details are not
transcribed here yet. The floor plan is in the private state repo.

## Which sensor cares where it sits

| Sensor | Does location matter? | What it wants |
|---|---|---|
| Gyro | No. Turn rate is the same everywhere on a rigid hull | A stiff mount, off the engine bearers |
| Accelerometer | Mildly | Near the axes the boat rotates about: roll near the waterline, pitch a little aft of midships |
| Magnetometer | Strongly | A magnetically steady spot |

## Magnetometer

- Steady beats small. A fixed offset calibrates out; switched loads, motors, a fridge
  compressor, or tools and cans in the same locker do not.
- Single conductors matter more than paired runs, whose fields nearly cancel.
- Tilt error becomes heading error, so the accelerometer's position still counts.
- Keep about 1 m from the engine, the binnacle compass and speakers.
- It must never move after calibration.
- Screws near it are brass or stainless.

## Numbers, all the agent's estimates, none measured

| Quantity | Value |
|---|---|
| False tilt from a 15° roll, 4.5 s period, 1 m off the roll axis | about 3°, mostly filtered by the gyro |
| Field from 10 A in a lone wire at 0.3 m | about 7 µT |
| Horizontal field at Seattle | about 18 µT (from memory) |
| Heading error per 1° of tilt error at about 69° dip | about 2.6° |
| False tilt in a turn, 6 kn at 3°/s | about 1° |

## Given by Solace

- The keel is probably all lead.
- The engine is directly under the galley sink.

## Still to do

At each candidate spot, hold a hand-bearing compass, switch loads and start the engine;
take the spot where the needle stays still.
