# HALMET bench session, 2026-11-14: state and findings

Flashed: PR 155 head `cf7ee26` (`halmet_espidf`, USB, CH340 at /dev/ttyUSB0).
Board has only the OLED attached; GPIO header and 1-Wire header not soldered.
A/D connectors are locking connectors (not screw terminals); screw-terminal
plugs exist for them and for NMEA 2000.

## Measured (by Solace on the board)
| Test | Result |
|---|---|
| D4 to GND / to centre 3V3 pad | flame detected / clears: active-low, matches the PR default |
| D3 pins shorted | false "coolant hot" clears (D3 floating reads hot) |
| D1 from GPIO pin 33 (380 Hz) | 228 RPM: tach path works; 228 = 380 x 60 / 100 (arithmetic, source of the /100 not traced) |
| A1/A2 to 3V3 | reads only from the **centre** 3V3 pad, not the GPIO-header 3V3 (isolation) |

## Corrected during the session
D and A inputs ARE galvanically isolated (digital isolator on the schematic).
Earlier advice to power the flame module from the GPIO header was wrong; power
it from the centre 3V3 pad and a connector ground. No header purchase needed
for the module. The I2C header is on the ESP32 side. Schematic source:
hatlabs HALMET KiCad (`digital_input`, `isolation` sheets).

## Changes made to PR 155
- Flame polarity comment fixed (`d5c5f3d`; its commit message wrongly says "not isolated").
- Engine hours: Signal K is the source of truth; flash is a cache, written when
  the whole hour changes; OLED shows `(cache)` until SK reports (`cf7ee26`).
  Not yet exercised on hardware.

## Open
- Unplugged flame module floats D4 and reads as flame: closing D4's PUP solder jumper would fail safe. Solace's call.
- D3 open input reads "hot" (inverted); decide when the Yanmar switch is wired.
- Untested: hours cache and SK sync, A1/A2 with real 12 V, TM1637 display, 60 s-era save (removed).
- Centre 3V3 pad's connector ground pin: waiting on a photo of the board.
- Scratch worktrees to remove: `.../worktrees/pr155-comment-fix`, `.../worktrees/isolation-doc-fix` (after PR 158 merges); local branch `claude/pr155-comment-fix-tmp`.
