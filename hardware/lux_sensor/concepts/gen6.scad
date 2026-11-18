// Variant A, rev 5. Tube frame (z up the tube, aft +x); the head faces along the tube, so it tips aft with the cant.
// Arm half: collar half + open trough + cup, top open. Cable slot open to the top. Top plate is the only cover.
cant = 15;
hw = 56; ph = 22; lid_t = 4; e = 5; w = 3;
tube_od = 38.1; R = tube_od/2; H = 48; wall = 6; gap = 20;
view = "open";      // open | exploded | closed | section
reach = R + gap + hw/2;
Z = H - lid_t;      // top of the base = underside of the plate
cable_z = 22;       // tube hole centre
slot_w = 12;
pcb = [15, 20, 1.6]; ledge = 1.5; lip = 1.2; cwall = 1.2; fit = 0.3;   // board seat, as on the halmet tier cradle
$fn = 120;
module ecyl(d, h) rotate_extrude() hull() { translate([d/2 - e, e]) circle(e); translate([d/2 - e, h - e]) circle(e); square([0.01, h]); }
module collar() hull() for (s = [-1, 1]) translate([s*6, 0, 0]) ecyl(tube_od + 2*wall, H);
module outer() hull() { collar(); translate([0, reach, H - ph]) ecyl(hw, ph); }
module bore() translate([0,0,-1]) cylinder(d = tube_od + 0.4, h = H + 2);
bolt_xz = [for (s = [-1, 1]) for (z = [10, H - 10]) [s*(R + 6), z]];
lid_bosses = [for (a = [-30, 90, 210]) [cos(a)*(hw/2 - w - 2), reach + sin(a)*(hw/2 - w - 2)]];
floor_z = H - ph + w;
module pocket() difference() {
  hull() { translate([0, reach, floor_z]) ecyl(hw - 2*w, ph); for (s = [-1, 1]) translate([s*6, 0, w]) ecyl(tube_od + 2*wall - 2*w, H); }
  collar();   // bolt meat and ring stay whole
}
module slot() hull() { translate([0, R - 3, cable_z]) rotate([-90,0,0]) cylinder(d = slot_w, h = wall + 6); translate([-slot_w/2, R - 3, H]) cube([slot_w, wall + 6, 1]); }   // round bottom, open to the top
module tie_anchor() intersection() { outer(); translate([-40, R + wall + 4, cable_z + 2]) cube([80, 4, 4]); }   // bridge across the channel; tie wraps bar + cable
seat_z = Z - 1.5 - pcb[2] - ledge;    // board top 1.5 under the plate
module seat() translate([0, reach, seat_z]) {
  bw0 = pcb[0] + 2*fit;
  for (s = [-1, 1]) intersection() { translate([s < 0 ? -bw0/2 - cwall : bw0/2 - lip, -(hw/2), -(seat_z - floor_z) - 1]) cube([cwall + lip, hw, seat_z - floor_z + 1 + ledge]); translate([0, 0, -50]) cylinder(d = hw - 2*w + 0.5, h = 100); }   // fins wall to wall carry the ledges
  bw = pcb[0] + 2*fit; bl = pcb[1] + 2*fit;
  for (s = [-1, 1]) translate([s < 0 ? -bw/2 : bw/2 - lip, -bl/2 + 4, 0]) cube([lip, bl - 4, ledge]);       // edge ledges
  for (s = [-1, 1]) translate([s < 0 ? -bw/2 - cwall : bw/2, -bl/2 + 2, 0]) cube([cwall, bl - 4, ledge + pcb[2]]);  // side walls
  translate([0, -bl/2 + 3, -(seat_z - floor_z)]) cylinder(d = 7, h = seat_z - floor_z + ledge);              // screw post
}
module bosses() intersection() { outer(); for (b = lid_bosses) translate([b[0], b[1], Z - 9]) { cylinder(d = 9, h = 9); translate([0,0,-4.5]) cylinder(d1 = 0, d2 = 9, h = 4.5); } }
module arm_half() difference() {
  union() { difference() { intersection() { outer(); translate([-200, 0, -1]) cube([400, 400, Z + 1]); } pocket(); } bosses(); tie_anchor(); seat(); }
  bore(); slot();
  for (b = lid_bosses) translate([b[0], b[1], Z - 6]) cylinder(d = 4, h = 7);
  translate([0, reach - (pcb[1] + 2*fit)/2 + 3, seat_z - 5]) cylinder(d = 3.2, h = 6);
  for (b = bolt_xz) translate([b[0], 0, b[1]]) rotate([90,0,0]) cylinder(d = 4.4, h = 80, center = true);
  for (b = bolt_xz) translate([b[0], 2, b[1]]) rotate([-90,0,0]) cylinder(d = 8, h = 4, $fn = 6);
}
module back_half() difference() {
  intersection() { outer(); translate([-200, -400, -1]) cube([400, 400, H + 2]); }
  bore();
  for (b = bolt_xz) translate([b[0], 0, b[1]]) rotate([90,0,0]) cylinder(d = 4.4, h = 80, center = true);
  for (b = bolt_xz) translate([b[0], -(R + 2), b[1]]) rotate([90,0,0]) cylinder(d = 8, h = 30);
}
module lid() difference() {   // arm side only; tube notch opens toward the split, so it slides off sideways
  intersection() { outer(); translate([-200, 0, Z]) cube([400, 400, 50]); }
  bore();
  translate([0, reach, Z - 1]) cylinder(d = 26, h = 20);
  for (b = lid_bosses) translate([b[0], b[1], Z - 1]) cylinder(d = 3.4, h = 20);
}
module dome() color("white", 0.6) translate([0, reach, H - 1]) intersection() { scale([1,1,12/12.5]) sphere(d = 25); translate([-20,-20,0]) cube(40); }
module board() color("green") translate([-pcb[0]/2, reach - pcb[1]/2, seat_z + ledge]) cube(pcb);
module cable() color("red") { hull() { translate([0, reach - 8, seat_z - 2]) sphere(d = 5); translate([0, R + wall + 6, cable_z + 8.5]) sphere(d = 5); }
  hull() { translate([0, R + wall + 6, cable_z + 8.5]) sphere(d = 5); translate([0, R - 6, cable_z]) sphere(d = 5); } }
module tie() color("black") translate([0, R + wall + 13.5, cable_z - 10 + 2]) rotate([0, 90, 90]) difference() { hull() { translate([-1, 0, 0]) cylinder(d = 9, h = 2.5, center = true); translate([-5, 0, 0]) cylinder(d = 4, h = 2.5, center = true); } cylinder(d = 7.5, h = 4, center = true); }
module tube() color("silver", 0.3) difference() { translate([0,0,-40]) cylinder(d = tube_od, h = H + 170); translate([0, R - 4, cable_z]) rotate([-90,0,0]) cylinder(d = 12, h = 10); }
if (view == "arm_half") arm_half();
lift = view == "exploded" ? 35 : 0; back = view == "exploded" ? 40 : 0;
if (view != "arm_half") rotate([0, cant, 0]) {
  tube(); board(); cable();
  if (view == "section") { color("SteelBlue") intersection() { arm_half(); translate([-400, -200, -100]) cube(400); } color("CadetBlue") intersection() { lid(); translate([-400, -200, -100]) cube(400); } }
  else { color("SteelBlue") arm_half(); color("LightSteelBlue") translate([0, -back, 0]) back_half(); }
  if (view == "closed" || view == "exploded") translate([0, 0, lift]) { color("CadetBlue") lid(); dome(); }
}
