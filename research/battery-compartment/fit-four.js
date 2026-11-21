// Fit four: the geometry behind fit-four.html. Pure JavaScript, no three.js,
// so `node fit-four.test.js` can check it without a browser.
//
// Coordinates, inches: x along the compartment (0 at the inboard wall, the
// hull rising outboard to port), y across (0 at the forward wall, W at the
// aft wall), z up from the floor.
(function (root) {
'use strict';

// ---- shell: best guesses, inches (README.md says where each comes from) ----
const SHELL = {
  W: 19.5,         // width between the long walls
  TOP: 21.75,      // floor to the rim (top of the compartment)
  LIPU: 19.75,     // floor to the underside of the forward lip
  LIPIN: 1.5,      // how far the forward lip stands in
  LIPX: 48,        // how far the forward lip runs along
  RISE_AT: 25,     // where the level floor ends, along the forward wall
  DIAG: 20.4,      // the rise line's skew across the width (110.4 - 90)
  SLOPE1: 26.5,    // hull rise, degrees, up to the step
  STEP_Z: 10.25,   // height where the hull steepens
  SLOPE2: 37.1,    // hull rise above that
  RAISE: 0.5,      // room above the rim aft of the lip (raised lid panels): a guess, set in the page
};
// ---- parts ----
const PART = {
  BL: 17.8, BW: 9.37, BH: 8.7,   // battery, retailer listing
  TN: 0.8, TS: 0.9, TP: 0.32,    // terminal post: height, square size, offset along the length (fraction)
  MP: [12.24, 7.17, 3.94],       // MultiPlus 12/500: H, W, D (Victron datasheet)
  OR: [7, 6.5, 3.3],             // Orion-Tr: W, H, D (photo, +/- 1/2)
};
const CL = 0.125, RAD = Math.PI / 180;

// ---- vectors and 3x3 matrices (columns are the battery's axes) ----
const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const mul = (a, s) => [a[0] * s, a[1] * s, a[2] * s];
const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
const norm = a => { const l = Math.hypot(...a); return l ? mul(a, 1 / l) : a; };
const col = (M, j) => [M[0][j], M[1][j], M[2][j]];
const fromCols = (a, b, c) => [[a[0], b[0], c[0]], [a[1], b[1], c[1]], [a[2], b[2], c[2]]];
const mm = (A, B) => A.map(r => [0, 1, 2].map(j => r[0] * B[0][j] + r[1] * B[1][j] + r[2] * B[2][j]));
const mv = (M, v) => M.map(r => r[0] * v[0] + r[1] * v[1] + r[2] * v[2]);
const I3 = [[1, 0, 0], [0, 1, 0], [0, 0, 1]];
function axisAngle(u, t) {
  u = norm(u); const c = Math.cos(t), s = Math.sin(t), C = 1 - c, [x, y, z] = u;
  return [[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
          [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
          [z * x * C - y * s, z * y * C + x * s, c + z * z * C]];
}
const Rz = t => axisAngle([0, 0, 1], t), Ry = t => axisAngle([0, 1, 0], t), Rx = t => axisAngle([1, 0, 0], t);
// the rotation that turns a onto b by the shortest way
function turnOnto(a, b) {
  a = norm(a); b = norm(b); const ax = cross(a, b), s = Math.hypot(...ax), c = dot(a, b);
  if (s < 1e-9) return c > 0 ? I3 : axisAngle(Math.abs(a[0]) < 0.9 ? cross(a, [1, 0, 0]) : cross(a, [0, 1, 0]), Math.PI);
  return axisAngle(ax, Math.atan2(s, c));
}

// ---- the hull: floor plus two planes; the solid is everything below max() of them ----
function makeShell(sh) {
  const K = Math.tan(sh.DIAG * RAD), T1 = Math.tan(sh.SLOPE1 * RAD), T2 = Math.tan(sh.SLOPE2 * RAD), S1 = sh.STEP_Z / T1;
  // s: distance along x past the rise line at this y
  const sOf = (x, y) => x - (sh.RISE_AT - y * K);
  const facets = [
    { id: 'floor', name: 'floor', z: (x, y) => 0, n: [0, 0, 1] },
    { id: 'hull1', name: 'lower hull', z: (x, y) => sOf(x, y) * T1, n: norm([-T1, -T1 * K, 1]) },
    { id: 'hull2', name: 'upper hull', z: (x, y) => sh.STEP_Z + (sOf(x, y) - S1) * T2, n: norm([-T2, -T2 * K, 1]) },
  ];
  const hull = (x, y) => Math.max(facets[0].z(x, y), facets[1].z(x, y), facets[2].z(x, y));
  const facetAt = (x, y) => { let k = 0; for (let i = 1; i < 3; i++) if (facets[i].z(x, y) > facets[k].z(x, y) + 1e-9) k = i; return facets[k]; };
  // a horizontal direction along the rise line, pointing aft; the "hull line"
  const strike = norm([-K, 1, 0]);
  const tilt = f => Math.acos(f.n[2]) / RAD;
  return Object.assign({}, sh, { K, T1, T2, S1, sOf, facets, hull, facetAt, strike, tilt });
}

// ---- a battery's pose ----
// A battery is { on, cx, cy, lift, mode: 'rest'|'free', surf, face, spin, roll, pitch, yaw }.
//   rest: one face lies flat on a surface (floor, lower hull, upper hull, or
//         'auto', whichever leaves it lowest), then spins about that surface's normal.
//   free: any orientation (yaw about z, then pitch about y, then roll about x),
//         held up by a support that the planner draws and sizes.
// cx, cy place the battery's centre in plan; it then drops as low as the hull
// lets it, and `lift` raises it from there (a shelf).
// Local axes: a across the width (BW), b along the length (BL), c up through the terminals (BH).
const FACES = {
  up:   { name: 'upright', M: I3 },
  side: { name: 'on its side', M: fromCols([0, 0, -1], [0, 1, 0], [1, 0, 0]) },
  end:  { name: 'on its end', M: fromCols([1, 0, 0], [0, 0, 1], [0, -1, 0]) },
  down: { name: 'upside down', M: fromCols([-1, 0, 0], [0, 1, 0], [0, 0, -1]) },
};
function restMatrix(face, spin, n) { return mm(turnOnto([0, 0, 1], n), mm(Rz(spin * RAD), FACES[face].M)); }
function freeMatrix(b) { return mm(Rz(b.yaw * RAD), mm(Ry(b.pitch * RAD), Rx(b.roll * RAD))); }
// Euler angles (z-y-x) of a matrix, degrees, for "free from here"
function eulerOf(M) {
  const pitch = Math.asin(Math.max(-1, Math.min(1, -M[2][0])));
  let roll, yaw;
  if (Math.abs(Math.cos(pitch)) > 1e-6) { roll = Math.atan2(M[2][1], M[2][2]); yaw = Math.atan2(M[1][0], M[0][0]); }
  else { roll = 0; yaw = Math.atan2(-M[0][1], M[1][1]); }
  const r = v => Math.round(v / RAD * 10) / 10;
  return { roll: r(roll), pitch: r(pitch), yaw: r(yaw) };
}

function Planner(shellIn) {
  const S = makeShell(shellIn || SHELL), P = PART;
  const H = [P.BW / 2, P.BL / 2, P.BH / 2];
  // boxes in the battery's local frame, about its centre: body, then the two terminal posts
  const LOCAL = [
    { c: [0, 0, 0], h: H },
    { c: [0, -P.TP * P.BL, H[2] + P.TN / 2], h: [P.TS / 2, P.TS / 2, P.TN / 2], term: 1 },
    { c: [0, P.TP * P.BL, H[2] + P.TN / 2], h: [P.TS / 2, P.TS / 2, P.TN / 2], term: 1 },
  ];
  const corners = (c, M, h) => { const out = []; for (const i of [-1, 1]) for (const j of [-1, 1]) for (const k of [-1, 1]) out.push(add(c, mv(M, [i * h[0], j * h[1], k * h[2]]))); return out; };
  const obb = (n, c, M, h, extra) => Object.assign({ n, c, e: [col(M, 0), col(M, 1), col(M, 2)], h }, extra || {});
  const aabb = (n, x0, x1, y0, y1, z0, z1, extra) => Object.assign(obb(n, [(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2], I3, [(x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2]), { box: [x0, x1, y0, y1, z0, z1] }, extra || {});

  // how high the centre must sit for no corner of any of the battery's boxes to be inside the hull.
  // Exact: hull - z is convex over each box, so its worst point is a corner.
  function dropZ(M, cx, cy) {
    let z = -1e9;
    for (const L of LOCAL) for (const p of corners(mv(M, L.c), M, L.h)) z = Math.max(z, S.hull(cx + p[0], cy + p[1]) - p[2]);
    return z;
  }
  function matrixOf(b) {
    if (b.mode === 'free') return { M: freeMatrix(b), facet: null };
    if (b.surf !== 'auto') { const f = S.facets.find(f => f.id === b.surf); return { M: restMatrix(b.face, b.spin, f.n), facet: f }; }
    // auto: lie on whichever surface leaves the battery lowest, as a real one settles
    let best = null;
    for (const f of S.facets) { const M = restMatrix(b.face, b.spin, f.n), z = dropZ(M, b.cx, b.cy); if (!best || z < best.z - 1e-6) best = { M, facet: f, z }; }
    return { M: best.M, facet: best.facet };
  }

  // place one battery: orientation, resting height, boxes, extents, what holds it up
  function solve(b, below) {
    const { M, facet } = matrixOf(b);
    let zc = dropZ(M, b.cx, b.cy), on = null;
    if (below && below.length) {          // stacking: rise until clear of the batteries already placed
      const at = z => { const r = boxes(M, [b.cx, b.cy, z]); return below.find(q => r.some(a => q.boxes.some(c => depth(a, c) > 0))); };
      let z = zc, hit = at(z);
      if (hit) {
        let n = 0; while (hit && n++ < 600) { z += 1 / 16; on = hit; hit = at(z); }
        let lo = z - 1 / 16, hi = z; for (let k = 0; k < 8; k++) { const m = (lo + hi) / 2; if (at(m)) lo = m; else hi = m; }
        zc = hi;
      }
    }
    const rest = zc;
    zc += b.lift || 0;
    const c = [b.cx, b.cy, zc], bx = boxes(M, c), body = corners(c, M, H);
    const all = bx.flatMap(q => corners(q.c, M, q.h));
    const xs = all.map(p => p[0]), ys = all.map(p => p[1]), zs = all.map(p => p[2]);
    const e3 = col(M, 2), tips = bx.filter(q => q.term).map(q => add(q.c, mul(e3, P.TN / 2)));
    return {
      b, M, e: [col(M, 0), col(M, 1), col(M, 2)], h: H, c, boxes: bx, body, facet, restZ: rest, on,
      x0: Math.min(...xs), x1: Math.max(...xs), y0: Math.min(...ys), y1: Math.max(...ys), z0: Math.min(...zs), z1: Math.max(...zs),
      tips, termTop: Math.max(...tips.map(p => p[2])),
    };
  }
  function boxes(M, c) { return LOCAL.map((L, i) => obb(i ? 'terminal' : 'body', add(c, mv(M, L.c)), M, L.h, L.term ? { term: 1 } : null)); }

  // oriented-box overlap depth by separating axes: > 0 overlapping, < 0 apart by at least that much
  function depth(A, B) {
    const ax = [...A.e, ...B.e];
    for (const a of A.e) for (const b of B.e) { const c = cross(a, b); if (dot(c, c) > 1e-8) ax.push(norm(c)); }
    const d = sub(B.c, A.c); let m = 1e9;
    for (const L of ax) {
      const rA = A.h.reduce((s, h, i) => s + h * Math.abs(dot(A.e[i], L)), 0), rB = B.h.reduce((s, h, i) => s + h * Math.abs(dot(B.e[i], L)), 0);
      m = Math.min(m, rA + rB - Math.abs(dot(d, L)));
    }
    return m;
  }

  // what holds a placed battery up, and what would have to be built
  function support(r) {
    const gap = p => p[2] - S.hull(p[0], p[1]);
    // the face whose outward normal points most nearly down
    const fcs = [];
    for (let i = 0; i < 3; i++) for (const s of [-1, 1]) fcs.push({ i, s, n: mul(r.e[i], s) });
    const down = fcs.reduce((a, f) => f.n[2] < a.n[2] ? f : a);
    const quad = r.body.filter(p => dot(sub(p, r.c), down.n) > 0);   // its four corners
    const gaps = quad.map(gap);
    const shelfTilt = Math.acos(Math.min(1, -down.n[2])) / RAD;
    const contacts = r.body.filter(p => gap(p) < 0.03);
    const stable = r.on ? true : inHull2(r.c, contacts);
    const lifted = (r.b.lift || 0) > 0.06;
    let kind;
    if (r.on) kind = 'stacked';
    else if (!lifted && stable && Math.max(...gaps) < 0.06) kind = shelfTilt < 0.5 ? 'flat' : 'slope';
    else kind = 'shelf';
    return { kind, quad, gaps, shelfTilt, downN: down.n, contacts: contacts.length, stable };
  }
  // is point p (plan) inside the plan outline of these points (their convex hull), within a little
  function inHull2(p, pts) {
    if (pts.length < 3) return false;
    const q = pts.map(v => [v[0], v[1]]).sort((a, b) => a[0] - b[0] || a[1] - b[1]);
    const cr = (o, a, b) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
    const lo = [], up = [];
    for (const v of q) { while (lo.length >= 2 && cr(lo[lo.length - 2], lo[lo.length - 1], v) <= 1e-9) lo.pop(); lo.push(v); }
    for (const v of q.slice().reverse()) { while (up.length >= 2 && cr(up[up.length - 2], up[up.length - 1], v) <= 1e-9) up.pop(); up.push(v); }
    const h = lo.slice(0, -1).concat(up.slice(0, -1));
    if (h.length < 3) return false;
    for (let i = 0; i < h.length; i++) { const a = h[i], b = h[(i + 1) % h.length], l = Math.hypot(b[0] - a[0], b[1] - a[1]); if (cr(a, b, p) / l < -0.05) return false; }
    return true;
  }

  // the shell's fixed things and the other units
  function obstacles(o) {
    const W = S.W, raise = o.raise == null ? S.RAISE : o.raise, lidZ = S.TOP + raise, u = [];
    u.push(aabb('lip', 0, S.LIPX, 0, S.LIPIN, S.LIPU, S.TOP + 12, { lip: 1, show: [0, S.LIPX, 0, S.LIPIN, S.LIPU, S.TOP] }));
    u.push(aabb('lid', -12, 90, -12, W + 12, lidZ, lidZ + 12, { lid: 1, hidden: 1 }));
    const op = o.orion || 'in', mpOn = o.mp !== false;
    if (mpOn) { const y0 = op === 'in' ? 0.75 : (W - P.MP[1]) / 2, z0 = S.TOP - 1 - P.MP[0]; u.push(aabb('MultiPlus', 0, P.MP[2], y0, y0 + P.MP[1], z0, z0 + P.MP[0])); }
    if (op === 'in') { const y0 = mpOn ? 0.75 + P.MP[1] + 1 : (W - P.OR[0]) / 2; u.push(aabb('Orion', 0, P.OR[2], y0, y0 + P.OR[0], S.TOP - 1 - P.OR[1], S.TOP - 1)); }
    if (op === 'now') u.push(aabb('Orion', 4, 11, 0, P.OR[2], 12, 18.5));
    if (op === 'ai') { const x0 = mpOn ? P.MP[2] + 0.5 : 0.5; u.push(aabb('Orion', x0, x0 + P.OR[0], W - P.OR[2], W, 0.5, 7)); }
    return u;
  }

  // everything at once: placements, supports, clashes, notes
  function layout(B, o) {
    o = o || {};
    const U = obstacles(o), raise = o.raise == null ? S.RAISE : o.raise;
    const idx = B.map((b, i) => i).filter(i => B[i].on);
    const sol = B.map(() => null);
    if (o.stack) {   // lowest first; each later one may rest on those already down
      const order = idx.slice().sort((a, b) => solve(B[a]).c[2] - solve(B[b]).c[2]), placed = [];
      for (const i of order) { const r = solve(B[i], placed); r.i = i; sol[i] = r; placed.push(r); }
    } else for (const i of idx) { sol[i] = solve(B[i]); sol[i].i = i; }
    const list = sol.map(() => []), notes = sol.map(() => []), ub = U.map(() => false);
    for (const i of idx) {
      const r = sol[i];
      for (const j of idx) {
        if (j <= i) continue; const q = sol[j];
        const d = Math.max(...r.boxes.flatMap(a => q.boxes.map(b2 => depth(a, b2))));
        if (d > -CL) { list[i].push(['B' + (j + 1), d]); list[j].push(['B' + (i + 1), d]); }
      }
      U.forEach((u, k) => { const d = Math.max(...r.boxes.map(a => depth(a, u))); if (d > -CL) { list[i].push([u.n, d]); ub[k] = true; } });
      if (r.y0 < CL) list[i].push(['fwd wall', -r.y0]);
      if (r.y1 > S.W - CL) list[i].push(['aft wall', r.y1 - S.W]);
      if (r.x0 < CL) list[i].push(['inboard wall', -r.x0]);
      if (r.z1 > S.TOP && !list[i].some(l => l[0] === 'lid')) notes[i].push(`above the rim by ${fr(r.z1 - S.TOP)}`);
      if (r.e[2][2] < -0.2) notes[i].push('terminals face down');
      r.sup = support(r);
      r.near = nearest(r, sol, U, i);
      r.access = termAccess(r, sol, U, i);
      r.face = faceWord(r.e[2]);
    }
    return { sol, U, list, notes, ub, S, raise };
  }
  // nearest neighbour gap (a lower bound, from the separating axes)
  function nearest(r, sol, U, i) {
    let best = null;
    sol.forEach((q, j) => { if (!q || j === i) return; const d = -Math.max(...r.boxes.flatMap(a => q.boxes.map(b2 => depth(a, b2)))); if (!best || d < best.d) best = { n: 'B' + (j + 1), d }; });
    U.forEach(u => { if (u.lid) return; const d = -Math.max(...r.boxes.map(a => depth(a, u))); if (!best || d < best.d) best = { n: u.n, d }; });
    return best;
  }
  // can a hand and a lug reach the terminals: is the 3 in past each tip open?
  function termAccess(r, sol, U, i) {
    const e3 = r.e[2]; let blocked = null;
    for (const t of r.tips) for (let s = 0.5; s <= 3; s += 0.5) {
      const p = add(t, mul(e3, s));
      if (p[2] < S.hull(p[0], p[1])) blocked = blocked || 'hull';
      if (p[0] < 0) blocked = blocked || 'inboard wall';
      if (p[1] < 0) blocked = blocked || 'fwd wall';
      if (p[1] > S.W) blocked = blocked || 'aft wall';
      sol.forEach((q, j) => { if (q && j !== i && inside(p, q.boxes[0])) blocked = blocked || 'B' + (j + 1); });
      U.forEach(u => { if (!u.lid && inside(p, u)) blocked = blocked || u.n; });
    }
    return blocked;
  }
  const inside = (p, A) => { const d = sub(p, A.c); return A.e.every((e, k) => Math.abs(dot(d, e)) <= A.h[k]); };
  function faceWord(v) {
    const a = v.map(Math.abs), k = a.indexOf(Math.max(...a));
    if (k === 2) return v[2] > 0 ? (v[2] > 0.97 ? 'up' : 'up, tilted') : 'down';
    if (k === 0) return v[0] > 0 ? 'outboard' : 'inboard';
    return v[1] > 0 ? 'aft' : 'forward';
  }

  // slide a battery inboard until it meets a wall unit or one of `done` (placed batteries)
  function slide(b, done, o) {
    const U = obstacles(o || {}).filter(u => !u.lip && !u.lid);
    const wall = U.filter(u => u.box[0] === 0).reduce((m, u) => Math.max(m, u.box[1]), 0) + CL;
    let r = solve(b); b.cx += wall - r.x0;
    for (let k = 0; k < 800; k++) {
      r = solve(b);
      const hit = done.some(q => Math.max(...r.boxes.flatMap(a => q.boxes.map(c => depth(a, c)))) > -CL) || U.some(u => Math.max(...r.boxes.map(a => depth(a, u))) > -CL);
      if (!hit) break; b.cx += 0.125;
    }
    b.cx = Math.round(b.cx * 8) / 8; return solve(b);
  }
  // close up the gaps: each battery in turn, inboard first
  function pack(B, o) {
    const done = [];
    for (const i of B.map((b, i) => i).filter(i => B[i].on).sort((a, b) => B[a].cx - B[b].cx)) done.push(slide(B[i], done, o));
  }
  function slideIn(B, i, o) { slide(B[i], B.filter((b, j) => j !== i && b.on).map(b => solve(b)), o); }
  // spin that lays the battery's longest flat edge along a horizontal direction (before the tilt)
  function spinAlong(b, dir) {
    const F = FACES[b.face].M, n = b.surf === 'auto' ? (matrixOf(b).facet || S.facets[0]).n : S.facets.find(f => f.id === b.surf).n;
    // the tilt keeps directions along its axis; express the target before the tilt
    const T = turnOnto([0, 0, 1], n), Tt = [0, 1, 2].map(i => [0, 1, 2].map(j => T[j][i]));
    const d = mv(Tt, dir);
    const flat = [0, 1, 2].filter(k => Math.abs(col(F, k)[2]) < 0.5).sort((p, q) => [P.BW, P.BL, P.BH][q] - [P.BW, P.BL, P.BH][p])[0];
    const e = col(F, flat), a0 = Math.atan2(e[1], e[0]), a1 = Math.atan2(d[1], d[0]);
    let s = (a1 - a0) / RAD; s = ((s % 180) + 180) % 180; if (s > 90) s -= 180;   // either end will do
    return Math.round(s * 10) / 10;
  }
  return { S, P, solve, layout, pack, slideIn, obstacles, depth, support, spinAlong, matrixOf, eulerOf, dropZ };
}

// inches to eighths, as a fraction
function fr(v) {
  const neg = v < 0; v = Math.abs(v); const n = Math.round(v * 8), w = Math.floor(n / 8); let r = n % 8, s;
  if (!r) s = w + ''; else { let d = 8; while (r % 2 === 0) { r /= 2; d /= 2; } s = (w ? w + ' ' : '') + r + '/' + d; }
  return (neg && n ? '−' : '') + s;
}

const api = { SHELL, PART, FACES, CL, RAD, Planner, makeShell, fr, vec: { add, sub, mul, dot, cross, norm, mv, mm, col } };
if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.FitFour = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
