// Variant A, hollowed: open trough from the collar to the head, closed only by the top plate.
// Bosses for lid heat-set inserts, standoffs for the board, big cable window into the tube.
cant = 15; tilt = 8; gap = 20; zup = 10;
hw = 56; ph = 22; lid_t = 4; e = 5; w = 3;      // w = shell wall
tube_od = 38.1; R = tube_od/2; H = 48; wall = 6;
view = "open";      // open | exploded | closed | section | arm_half | solidA
reach = R + gap + hw/2;
P = [0, reach, H + zup];
$fn = 120;
module ecyl(d, h) rotate_extrude() hull() { translate([d/2 - e, e]) circle(e); translate([d/2 - e, h - e]) circle(e); square([0.01, h]); }
module at_head() translate(P) rotate([0, tilt - cant, 0]) children();
module collar() hull() for (s = [-1, 1]) translate([s*6, 0, 0]) ecyl(tube_od + 2*wall, H);
module outer() hull() { collar(); at_head() translate([0,0,-ph]) ecyl(hw, ph); }
module above_lid() at_head() translate([0,0,-lid_t]) cylinder(d = 400, h = 200);
bolt_xz = [for (s = [-1, 1]) for (z = [10, H - 10]) [s*(R + 6), z]];
lid_bosses = concat([for (a = [-30, 90, 210]) at_xy(a, hw/2 - w - 2)], [[0, -(reach - (R + wall + 7))]]);   // head-local xy
function at_xy(a, r) = [cos(a)*r, sin(a)*r];
standoffs = [[-6, -7], [6, 7]];
cable_z = 24;
module pocket() difference() {
  hull() {
    at_head() translate([0,0,-ph + w]) ecyl(hw - 2*w, ph + 20);
    translate([0, R + wall + 6, cable_z - 12]) cylinder(d = 22, h = H + 40);
  }
  translate([0,0,-1]) cylinder(r = R + wall, h = H + 60);   // collar ring stays whole
}
module bosses() intersection() {
  outer();
  union() {
    at_head() for (b = lid_bosses) translate([b[0], b[1], -60]) cylinder(d = 9, h = 60);
    at_head() for (s = standoffs) translate([s[0], s[1], -ph]) cylinder(d = 6, h = w + 6);
  }
}
module holes() {
  at_head() for (b = lid_bosses) translate([b[0], b[1], -lid_t - 6]) cylinder(d = 4, h = 7);       // M3 heat-set
  at_head() for (s = standoffs) translate([s[0], s[1], -ph + w + 1]) cylinder(d = 3.2, h = 6);    // M2 heat-set
}
module cable_window() translate([0, R - 2, cable_z]) rotate([-90,0,0]) hull() for (z = [-5, 5]) translate([0, z, 0]) cylinder(d = 12, h = wall + 6);
module body_solid() difference() {
  union() { difference() { outer(); pocket(); } bosses(); }
  above_lid(); holes(); cable_window();
  translate([0,0,-1]) cylinder(d = tube_od + 0.4, h = H + 2);
  for (b = bolt_xz) translate([b[0], 0, b[1]]) rotate([90,0,0]) cylinder(d = 4.4, h = 80, center = true);
  for (b = bolt_xz) translate([b[0], -(R + 2), b[1]]) rotate([90,0,0]) cylinder(d = 8, h = 30);
  for (b = bolt_xz) translate([b[0], 2, b[1]]) rotate([-90,0,0]) cylinder(d = 8, h = 4, $fn = 6);
}
module arm_half()  intersection() { body_solid(); translate([-200, 0, -100]) cube(400); }
module back_half() intersection() { body_solid(); translate([-200, -400, -100]) cube(400); }
module lid() difference() {
  intersection() { outer(); above_lid(); }
  at_head() translate([0,0,-1]) cylinder(d = 26, h = 20);
  at_head() for (b = lid_bosses) translate([b[0], b[1], -10]) cylinder(d = 3.4, h = 30);
}
module dome() color("white", 0.6) at_head() translate([0,0,-1]) intersection() { scale([1,1,12/12.5]) sphere(d = 25); translate([-20,-20,0]) cube(40); }
module board() color("green") at_head() translate([-9, -11, -ph + w + 6]) cube([18, 22, 1.6]);
module cable() color("red") hull() { at_head() translate([0, -8, -ph + w + 8]) sphere(d = 5); translate([0, R + 3, cable_z]) sphere(d = 5); }
module tube() color("silver", 0.3) difference() { translate([0,0,-40]) cylinder(d = tube_od, h = H + 170); translate([0, R - 4, cable_z]) rotate([-90,0,0]) cylinder(d = 12, h = 10); }
lift = view == "exploded" ? 40 : 0;
back = view == "exploded" ? 40 : 0;
if (view == "arm_half") arm_half();
else if (view == "solidA") difference() { intersection() { outer(); translate([-200, 0, -100]) cube(400); } above_lid(); translate([0,0,-1]) cylinder(d = tube_od + 0.4, h = H + 2); }
else rotate([0, cant, 0]) {
  tube();
  if (view == "section") color("SteelBlue") intersection() { arm_half(); translate([-400, -200, -100]) cube(400); }
  else { color("SteelBlue") arm_half(); color("LightSteelBlue") translate([0, -back, 0]) back_half(); }
  board(); cable();
  if (view == "closed" || view == "exploded") translate([0, 0, lift]) { color("CadetBlue") lid(); dome(); }
  if (view == "section") color("CadetBlue") intersection() { lid(); translate([-400, -200, -100]) cube(400); }
}
