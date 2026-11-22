// node fit-four.search.js [orion] [multiplus] [raise] : how many batteries fit resting flat, 1/8 clear all round.
// Greedy: each battery in turn takes the placement that reaches least far outboard,
// so "no room" means none for the next one after those placed, not a proof over every order.
// orion: in | now | ai | off (as the page's Orion menu); multiplus: on | off; raise: room above the rim, inches.
const F = require('./fit-four.js'), pl = F.Planner(), S = pl.S, CL = F.CL;
const ORION = process.argv[2] || 'off', MULTIPLUS = process.argv[3] === 'on', RAISE = +(process.argv[4] || 0.5);
const STEP_X = 0.5, STEP_Y = 0.25, X_MAX = 50, WALL_MARGIN = 3;   // search grid, inches
const SURFS = ['floor', 'hull1', 'hull2'], FACES = ['up', 'side', 'end', 'down'];
const SPINS = ['square', 'square 90', 'along the hull line', 'up the slope', 'narrowest'];
const MIN_UP = 0.3;   // terminals must face at least this much upward

const U = pl.obstacles({ orion: ORION, mp: MULTIPLUS, raise: RAISE });
const poses = SURFS.flatMap(surf => FACES.flatMap(face => SPINS.map(sp => ({ surf, face, sp }))));
function battery(p, cx, cy) {
  const b = { on: true, cx, cy, lift: 0, mode: 'rest', surf: p.surf, face: p.face, spin: 0 };
  if (p.sp === 'square 90') b.spin = 90;
  if (p.sp === 'along the hull line') b.spin = pl.spinAlong(b, S.strike);
  if (p.sp === 'up the slope') b.spin = pl.spinAlong(b, [S.strike[1], -S.strike[0], 0]);
  if (p.sp === 'narrowest') b.spin = pl.spinNarrow(b, 0);
  return b;
}
const clear = (r, placed) =>
  r.x0 >= CL && r.y0 >= CL && r.y1 <= S.W - CL && r.e[2][2] >= MIN_UP &&
  !U.some(u => Math.max(...r.boxes.map(a => pl.depth(a, u))) > -CL) &&
  !placed.some(q => Math.max(...r.boxes.flatMap(a => q.boxes.map(c => pl.depth(a, c)))) > -CL) &&
  pl.support(r).kind !== 'shelf';

const placed = [];
for (let n = 0; n < 4; n++) {
  let best = null;
  for (const p of poses) for (let cx = 2; cx <= X_MAX; cx += STEP_X) for (let cy = WALL_MARGIN; cy <= S.W - WALL_MARGIN; cy += STEP_Y) {
    const b = battery(p, cx, cy), r = pl.solve(b);
    if (!clear(r, placed)) continue;
    const score = r.x1 + 0.01 * r.c[2];
    if (!best || score < best.score) best = { score, b, r, p };
  }
  if (!best) { console.log(`no room for battery ${n + 1}`); break; }
  placed.push(best.r);
  const { r, p, b } = best;
  console.log(`B${n + 1} ${p.surf} ${p.face} ${p.sp}, spin ${b.spin}, cx ${b.cx} cy ${b.cy} | x ${F.fr(r.x0)} to ${F.fr(r.x1)}, z ${F.fr(r.z0)} to ${F.fr(r.z1)}`);
}
