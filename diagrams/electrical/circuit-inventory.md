# Circuit inventory

Starting point for consolidating the old circuits into the chart-table
cabinet. The panel labels are what the 1980s Newmar panel says, which is
often wrong; the *Mark* column copies the hand marks on the panel. *Pos* counts
down each column; *Terminal #* is the matching number at the nav-desk terminals: Engine room is 4
(Solace), and the rest follow the panel's sequential numbering.

## Existing breaker panel (Newmar, chart table)

The panel's circuits run to at least 24 numbered screw terminals below the
nav desk; the terminal numbers match the panel's breaker numbering.

### AC

| Pos | Terminal # | Label | Mark | Notes |
|---|---|---|---|---|
| — | | AC master breaker | | reverse-polarity lamp beside it |
| 1 | | Outlets | | |
| 2 | | Water heater | ? | |
| 3 | | Battery charger | ? | |
| 4 | | Microwave oven | | |
| 5 | | (blank) | | |
| 6 | | (blank) | | |
| 7 | | (blank, no switch) | | |

### DC, left column

| Pos | Terminal # | Label | Mark | Notes |
|---|---|---|---|---|
| 1 | 1 | Cabin lights port | ✓ | |
| 2 | 2 | Cabin lights stbd | ✓ | |
| 3 | 3 | Courtesy lights | ✓ | |
| 4 | 4 | Engine room | ✓ | |
| 5 | 5 | Running | ✗ | label crossed out |
| 6 | 6 | Bow | ? | |
| 7 | 7 | Anchor | ✗ | label crossed out |
| 8 | 8 | Spreader | ? | |
| 9 | 9 | Nav/Com | ? | |
| 10 | 10 | Stereo | | |

### DC, right column

| Pos | Terminal # | Label | Mark | Notes |
|---|---|---|---|---|
| 1 | 11 | Compass light | ✓ | |
| 2 | 12 | Bilge pump | ? | |
| 3 | 13 | Bilge pump | | |
| 4 | 14 | Sump pump | ✓ | |
| 5 | 15 | Water pressure | ✓ | |
| 6 | 16 | LPG control | | |
| 7 | 17 | Refrigerator | | |
| 8 | 18 | Windlass | | |
| 9 | 19 | Heater | ✓ | |
| 10 | 20 | Radar | | |

### Nav-desk terminal strips

Read from a photo: colour and sleeve number only where legible. The upper
strip carries sleeves 1–12, the lower strip 13–24. A third strip, to their
right, is not yet traced.

| Terminal | Wire colour | Breaker |
|---|---|---|
| 1 | red / orange-red | Cabin lights port |
| 2 | red | Cabin lights stbd |
| 3 | red | Courtesy lights |
| 4 | orange | Engine room |
| 5 | white | Running |
| 6 | brown | Bow |
| 7 | yellow | Anchor |
| 8 | orange | Spreader |
| 9 | white | Nav/Com |
| 10 | blue | Stereo |
| 11 | blue | Compass light |
| 12 | blue | Bilge pump |
| 13 | grey | Bilge pump |
| 14 | purple | Sump pump |
| 15 | heavy red, white printed sleeve | Water pressure |
| 16 | red | LPG control |
| 17 | red | Refrigerator |
| 18 | white / pink | Windlass |
| 19 | brown | Heater |
| 20 | black | Radar |
| 21–23 | black | negatives |
| 24 | | main negative: house bank → SmartShunt; shunt input side → engine block |

## Existing circuits not on the breaker panel

| Circuit | Where it lands | Notes |
|---|---|---|

## Planned circuits

From `systems/electrical.md` § Power distribution, plus the at-dock
critical group. *Replaces* is the old breaker it takes over, once decided.

| Circuit | Group | Replaces |
|---|---|---|
| Bilge pumps | at-dock critical, unswitched fused | |
| CO / propane alarms | at-dock critical, unswitched fused | |
| NMEA 2000 (HALPI2, HALMET) | at-dock critical, unswitched fused | |
| AIS | at-dock critical, unswitched fused | |
| Network / wifi / 4G modem | unswitched fused | |
| Victron Cerbo and SmartShunt | unswitched fused | |
| ESP32 circuits | unswitched fused | |
| USB outlets, DC sockets, 9 V bucks, chargers | DC accessory | |
| Battery compartment fans (Cerbo relay, `battery-fans.svg`) | unswitched fused | |
| Fans | DC accessory | |
| Main cabin lights (24 V LED, chart light, overhead) | main cabin lights | |
| Courtesy lights | individually switched | |
| Engine room lights | individually switched | |
| Compass light | individually switched | |
| Windex light | individually switched | |
| Deck lights (spreader, cockpit, deck) | individually switched | |
| Underwater lights | individually switched | |
| Water pressure | panel switch plus terminal | |
| LPG | panel switch plus terminal | |
| Radar | panel switch plus terminal | |
| Stereo / sound system | panel switch plus terminal | |
| Windlass | panel switch plus terminal | |
| Refrigerator | panel switch plus terminal | |
| Water maker | panel switch plus terminal | |
| Heater | panel switch plus terminal | |
| Bow thruster | panel switch plus terminal | |
| Starlink | panel switch plus terminal | |
| Wash down | panel switch plus terminal | |
| Discharge pump | panel switch plus terminal | |
