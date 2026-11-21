# Battery compartment: fit four

The house-battery compartment under a seat aboard: a box whose outboard end
is the hull, rising to port. The goal is four 12 V 280 Ah batteries plus
room for the bus bars, the Orion-Tr DC-DC charger, the MultiPlus
inverter-charger and their cables.

## The tool

[`fit-four.html`](fit-four.html) is an interactive 3D planner. Open it in a
browser; it needs no build. Its geometry is [`fit-four.js`](fit-four.js);
`node fit-four.test.js` checks it, and
[`fit-four.search.js`](fit-four.search.js) reruns the search below.

- Only the hull is solid: batteries pass through everything else, so red
  means "look here", not "does not fit".
- "Copy link" keeps a layout; the page explains its own controls.

## What the numbers are

**None of the shell is confirmed aboard.** The constants at the top of
`fit-four.js` are best guesses from photos and the owner's first readings
(2026-11-20). Read a red overlap of a fraction of an inch as "close", not as
"no".

| Number | Value | Source |
|---|---|---|
| Width between the long walls | 19 1/2 | owner, against a photo |
| Floor to the underside of the forward lip | 19 3/4 | owner, against a photo |
| Floor to the rim | 21 3/4 | computed: lip underside plus a 2 in lip |
| Room above the rim, clear of the lip | 1/2, set in the page | guess; one side of the berth has raised lid panels (owner, 2026-11-21) |
| Forward lip | stands in 1 1/2, runs 48 | photo; 48 is a guess |
| Level floor ends | 25 along the forward wall | computed |
| Hull rise | 26 1/2°, then 37.1° above 10 1/4 | angle-ruler photos |
| Rise line skew across the width | 20.4° | angle-ruler photo |
| Battery | 17.8 × 9.37 × 8.7 | retailer listing; photos of the one aboard agree |
| MultiPlus 12/500 | 12.24 H × 7.17 W × 3.94 D | Victron datasheet |
| Orion-Tr | about 7 W × 6.5 H × 3.3 D | photo, ±1/2 |
| PR 174 bus-bar board | unknown | not drawn |

Holes (fan, rough hole, floor hole, mousehole, cabin vent) are dashed. Their
places are partly guessed.

## Constraints from the owner

- Every battery as low as possible. Raising one only earns space for the
  ones above, by moving outboard and up the hull.
- A direct two-by-two stack is not wanted.
- Lithium does not need to stand upright, so canted batteries are fair game.
- The top batteries may be pushed aft to clear the lip, and the lower ones
  forward to leave room for bus bars or cables.
- One side of the berth has raised lid panels: a battery clear of the lip
  may stand slightly above the rim.

## What a search of these numbers found (2026-11-21)

`node fit-four.search.js` (half-inch steps; terminals facing at least partly
up; square, along the hull line or up the slope; Orion and MultiPlus on the
inboard wall), counting only placements with 1/8 clear all round. It is
greedy: each battery takes the placement reaching least far outboard.
These rest on guessed numbers, so they say where to measure, not what to
build.

- **Resting flat, two fit, and the search finds no room for a third.** With
  nothing on the inboard wall (`node fit-four.search.js off off`) it is
  still two.
- **Along the hull line does not fit across.** A battery square to the rise
  line spans 20 in of a 19 1/2 in width.
- **Four fit with shelves:** three upright in a row across the compartment,
  stepping up the hull on level wedges (bottoms at 0, 2 3/4 and 7 3/4), and the fourth
  on a shelf 10 in up over the inboard one. That fourth is a direct stack,
  which is not wanted; the page's "Three level, stepping up" preset
  shows it.
- The MultiPlus on the inboard wall hangs 8 1/2 above the floor, so the
  first 4 in of floor holds no battery (a battery is 9 1/2 tall to its terminals).
