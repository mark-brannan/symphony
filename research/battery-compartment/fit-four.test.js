// node fit-four.test.js : checks the planner's geometry without a browser
const assert = require('assert'), F = require('./fit-four.js'), pl = F.Planner(), S = pl.S, P = F.PART;
const bat = o => Object.assign({ on: true, cx: 6, cy: S.W / 2, lift: 0, mode: 'rest', surf: 'floor', face: 'up', spin: 0, roll: 0, pitch: 0, yaw: 0 }, o);
const near = (a, b, t = 1e-6) => assert.ok(Math.abs(a - b) < t, `${a} vs ${b}`);
// upright on the floor: bottom at 0, terminals at BH + TN, flat
let r = pl.solve(bat({})); near(r.z0, 0); near(r.termTop, P.BH + P.TN); assert.strictEqual(pl.support(r).kind, 'flat');
// lying on the lower hull: the bottom face is parallel to the hull plane
r = pl.solve(bat({ cx: 30, surf: 'hull1' })); const n1 = S.facets[1].n; near(F.vec.dot(r.e[2], n1), 1);
assert.strictEqual(pl.support(r).kind, 'slope');
// auto picks the floor far inboard and the hull far up the slope
assert.strictEqual(pl.matrixOf(bat({ surf: 'auto', cx: 6 })).facet.id, 'floor');
assert.strictEqual(pl.matrixOf(bat({ surf: 'auto', cx: 36 })).facet.id, 'hull1');
// along the hull line: the long edge runs along the rise line
const b = bat({ cx: 30, surf: 'hull1' }); b.spin = pl.spinAlong(b, S.strike); r = pl.solve(b);
near(Math.abs(F.vec.dot(r.e[1], S.strike)), 1, 1e-3);
// lift makes a shelf; support gaps equal the lift on the floor
r = pl.solve(bat({ lift: 2 })); const s = pl.support(r); assert.strictEqual(s.kind, 'shelf'); s.gaps.forEach(g => near(g, 2));
// free pose round-trips through Euler angles
const M = pl.matrixOf(b).M, e = pl.eulerOf(M), M2 = pl.matrixOf(bat(Object.assign({ mode: 'free' }, e))).M;
M.forEach((row, i) => row.forEach((v, j) => near(v, M2[i][j], 2e-3)));
// stacking rests a battery on one below it
const L = pl.layout([bat({ cx: 6 }), bat({ cx: 6 }), bat({ on: false }), bat({ on: false })], { stack: true });
near(L.sol[1].z0, P.BH + P.TN, 0.02); assert.strictEqual(L.sol[1].sup.kind, 'stacked');
// terminals facing a wall unit within 3 in read as blocked by it, not as reachable
const T = pl.layout([bat({ cx: 10, cy: 9, face: 'side', spin: 90 }), bat({ on: false }), bat({ on: false }), bat({ on: false })], { orion: 'ai', mp: false });
assert.strictEqual(T.sol[0].access, 'Orion');
console.log('fit-four: all checks pass');
