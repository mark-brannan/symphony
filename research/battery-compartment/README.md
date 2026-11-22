# Battery compartment: fit four

The house-battery compartment under a seat aboard: a box whose outboard end
is the hull, rising to port. The goal is four 12 V 280 Ah batteries plus
room for the bus bars, the Orion-Tr DC-DC charger, the MultiPlus
inverter-charger and their cables. Two batteries are aboard now.

## The tool

[`fit-four.html`](fit-four.html) is an interactive 3D planner. Open it in a
browser; it needs no build. Its geometry is [`fit-four.js`](fit-four.js).

- `node fit-four.test.js` checks the geometry.
- `node fit-four.options.js [out|in] [orion] [multiplus]` places and reports
  the arrangements of four below. They are the page's "All four" buttons.
- "Pack" chooses which end they close up to. Outboard is the default: the
  inboard end is the zone to keep open (owner, 2026-11-22).
- `node fit-four.search.js` is the older greedy search that may build nothing.
- The page starts from the owner's working assumptions (2026-11-22): Orion
  and MultiPlus on the inboard wall, bus bars on the aft wall, 3/4 of room
  above the rim, 1/16 kept clear. The battery's size, the clearance, the lid
  room and the deep lip's underside are boxes on the page; the numbers below
  are for the listed battery with nothing on the walls and 1/8 clear.
- Under those assumptions and the listed battery size, the square stairs fit
  (steps at 3 7/8, 8 3/8 and 13 1/8, 1 1/2 open past the MultiPlus, the upper
  batteries sitting aft to rise past the forward lip) and the diagonal stairs
  do not. A battery 17.3 long or shorter would pass turned onto the hull
  line; the listing says 17.8. The owner doubts the listing and has outlines
  marked aboard that he believes clear: measure the battery.
- Only the hull is solid: batteries pass through everything else, so red
  means "look here", not "does not fit".
- "Copy link" keeps a layout; the page explains its own controls.

[`compartment-map.html`](compartment-map.html) is the compartment as measured
on 2026-11-21, with the equipment placed from that night's photos: a map to
look around in, not a planner.

## What the numbers are

The shell was measured aboard on 2026-11-21 (tape and speed square). Inches.

| Number | Value | Source |
|---|---|---|
| Width between the long walls, below the lip | 19 1/2 | measured |
| Clear opening, aft rim to forward lip edge | 18 | measured |
| Floor to the underside of the lip | 20 | measured |
| Floor to the rim | 22 | measured |
| Lip: forward wall, inboard wall, deep lip's edge; none aft | 2 high, stands in 1 3/8 to 1 1/2 | measured |
| Clear opening along the aft wall / the forward wall | 44 5/8 / 53 3/16 | measured |
| Level floor ends, aft side / forward side | about 15 3/4 / about 23 | measured |
| Rise line skew across the width | 20.4 deg | computed from the two above |
| Rim down to the hull at the opening's outboard corners | about 8 3/8 aft, about 7 forward | measured; taken as from the rim top |
| Deep lip overhang, opening edge to the hull | about 10 | measured |
| Hull rise from the rise line | 25.6 deg | fitted to the two corner drops; the model is within 3/8 of both |
| Hull steepens at | 15.8 up, to 37.1 deg | fitted: the steeper angle is the 2026-11-20 angle-ruler photo; the height is where that slope gives the measured overhang |
| Deep lip | solid from 20 up | assumed: its panel thickness is not measured |
| Room above the rim, clear of the lip | 3/4, set in the page | guess; one side of the berth has raised lid panels |
| Battery | 17.8 x 9.37 x 8.7, both posts at one end | retailer listing; photos of the two aboard |
| MultiPlus 12/500 | 12.24 H x 7.17 W x 3.94 D | Victron datasheet |
| Orion-Tr | about 7 W x 6.5 H x 3.3 D | photo, +/- 1/2 |

No drops were taken along the walls, so the hull between the rise line and
the corners is a straight line that could be an inch or two out. That is
enough to choose between arrangements, not enough to cut a shelf. Of the wall
holes only the fan hole is measured; the rest are dashed where photos put them.

Against the first guesses (2026-11-20): the floor is 2 shorter, the box 1/4
taller, and the hull at the opening's outboard corners about 1 1/2 lower.

## Constraints from the owner

- Every battery as low as possible; raise one only to make room above it.
- A direct two-by-two stack is not wanted.
- Lithium does not need to stand upright, so canted batteries are fair game.
- Top batteries may go aft to clear the lip; lower ones forward, for bus bars.
- One side of the berth has raised lid panels: a battery clear of the lip
  may stand slightly above the rim.
- Nothing now in the compartment is in its final place (2026-11-22).
- Keep the inboard end open, for air and for the chargers, and the aft wall
  for the bus bar: batteries go as far outboard, and up, as they can
  (2026-11-22).

## Arrangements of four (2026-11-22)

`node fit-four.options.js out`: nothing on the walls, 1/8 clear all round,
each battery as far outboard as the lid, the lips and the deep lip allow.
"Across" is the long way across the compartment, "lengthwise" along it.
"Open inboard" is the clear length from the inboard wall to the first battery.

| Arrangement | Open inboard | Reach | What has to be built |
|---|---|---|---|
| Two on end, two on the hull | 14 1/4 | 47 1/4 | pads of 2 and 4 1/2 for the pair on end; stops for two lying at 27 deg |
| Two on end, a pair up the slope | 14 1/4 | 46 | the same pads; wedges up to 1 5/8 and stops |
| Lengthwise, rear pair up the slope | 7 1/8 | 46 | a shelf at 2 5/8 to 5 1/8; wedges up to 1 5/8 and stops |
| Two level, two on the hull | 6 3/4 | 47 1/4 | a step at 4 3/8; stops for two lying at 27 deg |
| Three level, one on the hull | 5 7/8 | 47 1/4 | steps at 4 and 8 1/2; one stop |
| Two pairs lengthwise | 5 1/4 | 42 5/8 | shelves at about 2 to 4 1/4 and 10 3/8 to 12 7/8 |
| Two across, then a pair | 4 1/4 | 42 5/8 | a step at 3 1/4; a shelf at 10 3/8 to 12 7/8 |
| A pair, then two across | 2 3/4 | 39 1/2 | pads; steps at 6 5/8 and 11 1/8 |
| Four on end, two rows | 2 1/4 | 26 1/8 | pads of 2 and 4 5/8 |
| Stairs: four across, upright | 1 3/4 | 39 1/2 | steps at 2, 6 5/8 and 11 1/8 |
| Diagonal, two level, two on the hull | 3 7/8 | 47 1/4 | a step at 3 3/8; stops for two lying at 27 deg |
| Diagonal stairs (the owner's arrangement) | 5/8 | 42 3/8 | steps at 1 3/4, 6 1/2 and 11 1/8 |

- **The owner's arrangement is diagonal stairs:** batteries turned along the
  hull line, stepping up the hull (2026-11-22). Turned the whole 20.4 deg an
  upright battery spans 19.95 across a 19 1/2 compartment, 1/4 into each
  wall. It clears by 1/8 a side up to 10.8 deg and touches both walls at
  13.4. At 10.8 deg four fit, on steps at 1 3/4, 6 1/2 and 11 1/8, topping
  out at 20 5/8. True to the hull line each step would be one level board
  with a 4 3/4 riser; at 10.8 deg the risers run from 1 1/2 to 6 1/4.
- **Diagonal stairs use the whole length.** The turn lets the last battery
  reach 3 further outboard, and costs the same 3 at the inboard end. Three
  batteries on the upper three steps leave about 10 open; the fourth takes it.
  A half inch decides whether the true hull line fits: the battery's real
  length and the width at the height it sits are worth a tape.
- **Upright or tilted, four batteries leave at most about 7 open inboard.**
  A single layer of four is 36 to 40 long and the hull lets it reach 39 to 47.
- **Standing one pair on end doubles that, to about 14.** It is the only way
  found to use the height where the hull is still low. The result is the same
  with the lid flush to the rim. It needs the maker's word on standing a
  battery on end.
- **The aft wall is never open beside a battery:** an across battery leaves
  1 1/2, a pair leaves 1/8. The bus bar's clear wall is in the open inboard
  zone, or above the low batteries.
- An across battery cannot rise past 20: the opening is 18 and the battery
  17.8, so it cannot clear the forward lip. That is what stops the stairs.
- More room above the rim does not help: the lips and the deep lip stop
  things first. A deep lip whose underside is above 20 would.
- With the Orion and MultiPlus on the inboard wall (`node fit-four.options.js
  out in on`) the two on-end arrangements still leave 10 1/4 past them.
- Packed against the inboard wall instead (`node fit-four.options.js in`) the
  stairs reach 38 3/8 and top out at 20 3/8; every arrangement but the on-end
  ones then starts with one battery flat on the floor and the next on a pad
  of 1 to 1 3/8.
- One level, three on the hull: packed inboard the fourth meets the lip and
  the lid; packed outboard one of the three ends up back at the inboard wall.
- The MultiPlus hangs 7 1/4 above the floor under the inboard lip: no
  battery fits under it.
