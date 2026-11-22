// node fit-four.options.js [pack] [orion] [multiplus] [raise] : the arrangements of four in fit-four.js, each placed and checked.
// pack: out (as far outboard as they go, the inboard end left open) | in (against the inboard wall)
// orion: in | now | ai | off (as the page's Orion menu); multiplus: on | off; raise: room above the rim, inches.
// Default: packed outboard, nothing on the walls, since where the Orion and MultiPlus go is not settled.
const F = require('./fit-four.js'), pl = F.Planner(), S = pl.S, fr = F.fr, a = process.argv;
const O = { pack: a[2] || 'out', orion: a[3] || 'off', mp: a[4] === 'on', raise: +(a[5] || S.RAISE) };
console.log(`Packed ${O.pack === 'out' ? 'outboard' : 'against the inboard wall'}, Orion ${O.orion}, MultiPlus ${O.mp ? 'on' : 'off'}, lid ${fr(O.raise)} above the rim. Inches.\n`);
for (const opt of F.options(pl, O)) {
  const L = pl.layout(opt.B, O), sol = L.sol.filter(Boolean), R = pl.room(L);
  const bad = L.list.filter(l => l.length).length;
  console.log(`${opt.name}  [${bad ? bad + ' touching or overlapping' : 'all clear'}]  open inboard ${fr(R.inboard)}, open aft ${fr(R.aft)}, reach ${fr(R.reach)}, highest point ${fr(R.top)}`);
  console.log(`  ${opt.what}`);
  sol.forEach(r => {
    const s = r.sup, legs = s.gaps.slice().sort((x, y) => x - y).map(fr).join(', ');
    const held = s.kind === 'flat' ? 'flat on the floor' : s.kind === 'slope' ? `lying on the ${r.facet.name}, ${Math.round(s.shelfTilt)} deg: a stop on its low edge`
      : `shelf ${Math.round(s.shelfTilt)} deg from level, legs ${legs}`;
    const iss = L.list[r.i].map(([w, d]) => d > 0 ? `${w} by ${fr(d)}` : `${w} (touching)`).join(', ');
    console.log(`  B${r.i + 1}: x ${fr(r.x0)} to ${fr(r.x1)}, y ${fr(r.y0)} to ${fr(r.y1)}, z ${fr(r.z0)} to ${fr(r.z1)} | ${held} | terminals ${r.face}${r.access ? ', blocked by ' + r.access : ''}${iss ? ' | ' + iss : ''}`);
  });
  console.log('');
}
