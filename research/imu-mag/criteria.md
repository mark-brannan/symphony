# Criteria

The choice is a multi-criteria one. Weights are Solace's and none are set yet.

## Stated by Solace

| Criterion | In their words or close to it | Date |
|---|---|---|
| Newness | Evaluating new chips; newer is better. Parts marked not for new designs, or being phased out, are out | 2026-11-20 |
| Price | "A good price" | 2026-11-20 |
| Fits the application | Works for the boat | 2026-11-20 |
| Merit only | A pick rests on the part's merits, never on already owning one or on an older part's existing driver | 2026-11-20 |

Given as constraints, same date:

- We write our own driver in RTIMULib2.
- The 6-axis chip is paired with a separate magnetometer.
- The ICM-20948 is not for new designs. The LIS3MDL is being phased out. Both are Solace's
  statements; neither maker's notice has been looked up.

## Proposed by the agent, not yet accepted or weighted

| Criterion | Why it might matter |
|---|---|
| Published drift figure | Only one chip so far has a maker's bias-instability number |
| Gyro offset change with temperature | Sets how far the rate output moves as the cabin warms; datasheets show the same figure for the chips checked |
| Gyro noise | Differences between candidates are below what a hull moving at 0.1 to 1 Hz shows (agent's estimate) |
| Plug-in board available | Boat wiring is crimped or plugged, not soldered |
| Supply life | ST's industrial line carries a 10-year promise |
| Driver effort | Lines to write and registers to learn |
| Rated temperature | All candidates cover a cabin |

## Looked at and found not to matter here

| Feature | Why |
|---|---|
| FIFO size | Only matters if the host stalls at high sample rates |
| On-chip 6-axis fusion | RTIMULib2 does the fusion in software and needs the magnetometer in it; see `software.md` |
| Very high sample rates and resolution | For vibrating airframes |
