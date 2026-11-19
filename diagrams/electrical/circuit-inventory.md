# Circuit inventory

Starting point for consolidating the old circuits into the chart-table
cabinet. The panel labels are what the 1980s Newmar panel says, which is
often wrong; the *Mark* column copies the hand marks on the panel. *Pos* counts
down each column; *Terminal #* is the matching number at the nav-desk terminals.

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
| 1 | | Cabin lights port | ✓ | |
| 2 | | Cabin lights stbd | ✓ | |
| 3 | | Courtesy lights | ✓ | |
| 4 | | Engine room | ✓ | |
| 5 | | Running | ✗ | label crossed out |
| 6 | | Bow | ? | |
| 7 | | Anchor | ✗ | label crossed out |
| 8 | | Spreader | ? | |
| 9 | | Nav/Com | ? | |
| 10 | | Stereo | | |

### DC, right column

| Pos | Terminal # | Label | Mark | Notes |
|---|---|---|---|---|
| 1 | | Compass light | ✓ | |
| 2 | | Bilge pump | ? | |
| 3 | | Bilge pump | | |
| 4 | | Sump pump | ✓ | |
| 5 | | Water pressure | ✓ | |
| 6 | | LPG control | | |
| 7 | | Refrigerator | | |
| 8 | | Windlass | | |
| 9 | | Heater | ✓ | |
| 10 | | Radar | | |

### Nav-desk terminal strips

Read from a photo: colour and sleeve number only where legible. The upper
strip carries sleeves 1–12, the lower strip 13–24. A third strip, to their
right, is not yet traced.

| Terminal | Wire colour | Breaker |
|---|---|---|
| 1 | red / orange-red | |
| 2 | red | |
| 3 | red | |
| 4 | orange | Engine room? (Solace: 4th down in the first DC column) |
| 5 | white | |
| 6 | brown | |
| 7 | yellow | |
| 8 | orange | |
| 9 | white | |
| 10 | blue | |
| 11 | blue | |
| 12 | blue | |
| 13 | grey | |
| 14 | purple | |
| 15 | heavy red, white printed sleeve | |
| 16 | red | |
| 17 | red | |
| 18 | white / pink | |
| 19 | brown | |
| 20–23 | black | |
| 24 | | |

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
