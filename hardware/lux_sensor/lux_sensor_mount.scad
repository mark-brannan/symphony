// Lux sensor mount, rev 10. A two-part collar centred on the cross-bar joint of the vane frame; the arm, in the aft half, tapers aft to the dome.
// Frame: z up the tube, +y aft along the arm, x athwartships. tilt() takes it to the world.
// Measured (owner): tube 1 1/2", bars 5/8". Guessed: bars level, 120 deg apart in plan, V opening forward, sensor aft; tube canted 15 deg aft.
view = "assembly";   // assembly | exploded | section | aft_half | front_print | aft_print | cup_print
cant = 15; vee = 120;
R = 19.05; br = 15.9/2; e = 4; $fn = 96;
H = 48; wall = 6;
reach = R + 50;      // dome centre from the tube axis
tip = [52, 18];      // the arm tapers to this tip: plan diameter, height under the top
split = 0.5;         // each half stops this short of the split plane, so 1 mm closes as the bolts pull it onto the tube
bore_r = R + 0.15;
// Clamp: four M3 socket heads from the front, through the front half, into heat-set inserts in the aft half. M3 x 12.
m3_clear = 3.4; m3_head = 6.5; m3_insert = [4.0, 4];
clamp = [for (sx = [-1, 1], z = [11, -17.5]) [sx*(R + 5.5), z]];   // above and below the bar slots
seat_y = -8;         // head seat: 7.5 of the front half is clamped
win = [30, 20]; win_z = 4;   // window in the aft bore, so the cable meets it wherever the tube's grommet ends up
// The arm is hollow from that window to the dome. Shielded cat5e runs through it, soldered straight to a VEML7700 under the window.
skin = 3;
Z = H/2 - 6;                 // underside of the top over the window
zb = H/2 - tip[1];           // the tip's bottom; the underside slopes evenly from the collar to the tip's far edge
// Window, as rev 9: glass cabochon loaded from below, dome up through a curved lip, a square of 1 mm PTFE on its flat back. Silicone in the lip.
// With no lid, rev 9's retaining ring becomes a cup: it closes the arm's bottom opening, its rim presses the PTFE onto the glass,
// and it carries the VEML7700 under the window. Two M3 up through its flange into heat-set inserts. Pot the board in the cup.
cab_d = 24.8; cab_h = 6;     // owner's cabochons, measured
ptfe_s = 25; ptfe_t = 1;
capture = 1.5; seat_gap = 0.15; bevel = 30;
op = ptfe_s + 0.6;           // square bottom opening; glass and PTFE pass up through it
cup_s = op - 0.4; cup_w = 2.5; fl_t = 2; cup_ears = [-17, 17];
lux = [16.51, 16.51, 1.6];   // Adafruit VEML7700 (4162)
board_gap = 1.5;             // board top below the PTFE
lux_bot = Z - board_gap - lux[2];
function under(y) = -H/2 + (y - (R + wall - e))*(H - tip[1])/(reach + tip[0]/2 - R - wall);   // underside on the centreline
zf = under(reach + cup_s/2 + 0.3);   // flange seat, a flat pocket flush with the underside at its aft edge
notch = [8, 7];              // cable notch in the cup's forward wall
cab_R = (pow(cab_d/2, 2) + cab_h*cab_h)/(2*cab_h);
glass_z = Z + ptfe_t;
lip_r = cab_d/2 - capture;
lip_h = sqrt(cab_R*cab_R - lip_r*lip_r) - (cab_R - cab_h);
echo(dome_above_top = glass_z + cab_h - H/2, under_board = lux_bot - zf - fl_t, cup_h = Z - zf);
module ecyl(d, h) rotate_extrude() hull() { translate([d/2 - e, e]) circle(e); translate([d/2 - e, h - e]) circle(e); square([0.01, h]); }
module collar() hull() for (s = [-1, 1]) translate([s*5, 0, -H/2]) ecyl(2*R + 2*wall, H);
module outer() hull() { collar(); translate([0, reach, H/2 - tip[1]]) ecyl(tip[0], tip[1]); }
module tilt() rotate([-cant, 0, 0]) children();
module bar_world(g = 0) for (a = [(180 - vee)/2, 180 - (180 - vee)/2]) rotate([0, 0, -a]) rotate([0, 90, 0]) cylinder(r = br + g, h = 160);
module bars(g = 0) rotate([cant, 0, 0]) bar_world(g);   // the bars in this frame
// The bars are fixed to the tube, so the front half slides on from forward: each bar notch runs aft to the split.
module bar_slots() for (b = [0, 1]) hull() for (dy = [0, 60]) translate([0, dy, 0]) rotate([cant, 0, 0]) rotate([0, 0, -[30, 150][b]]) rotate([0, 90, 0]) cylinder(r = br + 0.4, h = 160);
module bore() translate([0, 0, -100]) cylinder(r = bore_r, h = 200);
module clamp_holes(half) for (b = clamp) translate([b[0], 0, b[1]]) rotate([-90, 0, 0]) {
  if (half == "front") { translate([0, 0, seat_y - 60]) cylinder(d = m3_head, h = 60); translate([0, 0, seat_y - 1]) cylinder(d = m3_clear, h = 10); }
  else translate([0, 0, -1]) cylinder(d = m3_insert[0], h = 1 + split + m3_insert[1] + 2);   // insert, then room for the bolt tip
}
module glass(o = 0) translate([0, reach, glass_z - (cab_R - cab_h)]) intersection() { sphere(r = cab_R + o); translate([-50, -50, cab_R - cab_h]) cube(100); }
module window_cut() {
  translate([-op/2, reach - op/2, -H]) cube([op, op, glass_z + H]);   // bottom opening and PTFE pocket
  glass(seat_gap);
  translate([0, reach, glass_z + lip_h + 0.4]) cylinder(h = 20, r1 = lip_r, r2 = lip_r + 20/tan(bevel));   // bevel to the lip
}
module cavity() intersection() {
  hull() {
    translate([-23, R + wall - 1, -H/2 + skin + e]) cube([46, 1, H - 2*skin - e]);
    translate([0, reach, zb + skin]) cylinder(d = tip[0] - 2*skin, h = Z - zb - skin);
  }
  hull() {   // the outer form, one skin in
    for (s = [-1, 1]) translate([s*5, 0, -H/2 + skin]) ecyl(2*R + 2*wall - 2*skin, H - 2*skin);
    translate([0, reach, zb + skin]) ecyl(tip[0] - 2*skin, tip[1] - 2*skin);
  }
}
module flange2d() hull() { square(cup_s, center = true); for (x = cup_ears) translate([x, 0]) circle(d = 7); }
module cup_bosses() intersection() { outer(); for (x = cup_ears) translate([x, reach, zf - 10]) cylinder(d = 8, h = 10 + fl_t + m3_insert[1] + 4); }
module corners(x0, y0, sx, sy, h) for (cx = [0, 1], cy = [0, 1]) {   // L-shaped blocks round a board's corners, 2 thick, 6 long
  px = x0 + cx*sx; py = y0 + cy*sy;
  translate([cx ? px - 6 : px, cy ? py : py - 2, 0]) cube([6, 2, h]);
  translate([cx ? px : px - 2, cy ? py - 6 : py, 0]) cube([2, 6, h]);
}
module cup() translate([0, reach, zf]) difference() {   // prints flange down
  union() {
    linear_extrude(fl_t) flange2d();
    translate([-cup_s/2, -cup_s/2, 0]) cube([cup_s, cup_s, Z - zf]);
  }
  difference() {
    translate([-(cup_s/2 - cup_w), -(cup_s/2 - cup_w), fl_t]) cube([cup_s - 2*cup_w, cup_s - 2*cup_w, 50]);
    for (sx = [-1, 1], sy = [-1, 1]) translate([sx*(lux[0]/2 - 1.5) - 1.5, sy*(lux[1]/2 - 1.5) - 1.5, 0]) cube([3, 3, lux_bot - zf]);   // pads under the board corners
    corners(-lux[0]/2 - 0.2, -lux[1]/2 - 0.2, lux[0] + 0.4, lux[1] + 0.4, lux_bot - zf + lux[2]);
  }
  for (x = cup_ears) translate([x, 0, -1]) cylinder(d = m3_clear, h = 10);
  translate([-notch[0]/2, -cup_s/2 - 1, fl_t]) cube([notch[0], cup_w + 2, notch[1]]);
  translate([0, cup_s/2 - cup_w - 1.5, -1]) cylinder(d = 2.5, h = 5);   // drain at the aft edge, the cup's low side
}
module front_half() difference() {
  intersection() { outer(); translate([-100, -100 - split, -100]) cube([200, 100, 200]); }
  bore(); bar_slots(); clamp_holes("front");
}
module aft_half() difference() {
  union() { difference() { intersection() { outer(); translate([-100, split, -100]) cube([200, 200, 200]); } cavity(); } cup_bosses();
    intersection() { outer(); translate([0, reach, -H]) linear_extrude(H + zf + fl_t + skin) offset(delta = 0.3 + skin) flange2d(); } }   // walls round the flange pocket
  bore(); window_cut(); bars(0.4); clamp_holes("aft");
  translate([-win[0]/2, 0, win_z - win[1]/2]) cube([win[0], R + wall, win[1]]);
  translate([0, reach, -H]) linear_extrude(H + zf + fl_t) offset(delta = 0.3) flange2d();   // flange pocket
  for (x = cup_ears) translate([x, reach, zf + fl_t - 0.01]) cylinder(d = m3_insert[0], h = m3_insert[1] + 2);
  translate([0, reach + 17, -H]) cylinder(d = 4, h = H + under(reach + 17) + skin + 1);   // drains: aft of the cup, and the cavity's forward foot, its low point at the cant
  translate([0, R + wall + 1.5, -H/2 - 1]) cylinder(d = 4, h = skin + e + 3);
}
module tube() color("Gainsboro") difference() { translate([0, 0, -120]) cylinder(r = R, h = 260); rotate([0, 0, 20]) translate([0, R - 5, 6]) rotate([-90, 0, 0]) cylinder(d = 12, h = 10); }   // grommet hole, position a guess
module ptfe() color("white") translate([-ptfe_s/2, reach - ptfe_s/2, Z]) cube([ptfe_s, ptfe_s, ptfe_t]);
module board() color("green") translate([-lux[0]/2, reach - lux[1]/2, lux_bot]) cube(lux);
module cable() color("RoyalBlue") {   // shielded cat5e, ~6 mm (a guess), from the grommet through the window and arm into the cup
  pts = [[0, 0, -60], [0, 0, 0], [-6.5, 17.9, 6], [0, 34, 8], [0, reach - cup_s/2 - 3, zf + fl_t + 3.5], [0, reach - 5, zf + fl_t + 3.5], [0, reach - 5, lux_bot]];
  for (i = [0 : len(pts) - 2]) hull() { translate(pts[i]) sphere(d = 6, $fn = 16); translate(pts[i + 1]) sphere(d = 6, $fn = 16); }
}
gap = view == "exploded" ? 40 : 0; drop = view == "exploded" ? 30 : 0;
module parts() {
  color("SteelBlue") aft_half(); color("LightSteelBlue") translate([0, -gap, 0]) front_half();
  translate([0, 0, -drop]) { color("Peru") cup(); board(); }
  translate([0, 0, -drop/2]) { ptfe(); color("LightCyan", 0.7) glass(); }
}
if (view == "assembly" || view == "exploded") { color("Gainsboro") bar_world(); tilt() { tube(); parts(); } }
if (view == "section") tilt() { intersection() { union() { parts(); cable(); } translate([0, -200, -200]) cube(400); } color("Gainsboro", 0.4) tube(); }
if (view == "aft_half") color("SteelBlue") aft_half();
if (view == "front_print") translate([0, 0, -split]) rotate([-90, 0, 0]) front_half();   // split face down
if (view == "cup_print") translate([0, -reach, -zf]) cup();
if (view == "aft_print") translate([0, 0, -split]) rotate([90, 0, 0]) aft_half();
