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
// Window: glass cabochon loaded from below, dome up through a curved lip; 1 mm PTFE diffuser on its flat back;
// a ring screwed to the lid's underside (M2 into heat-set inserts) holds both. Silicone in the lip, not epoxy.
cab_d = 24.8; cab_h = 6;     // owner's cabochons, measured
ptfe_t = 1;                  // PTFE sheet, cut to the pocket
capture = 1.5;               // lip overlaps the glass by this much of its radius
seat_gap = 0.15;             // silicone between glass and lip
bevel = 30;                  // lid top falls toward the lip at this angle, so it shades little low sun
ring_t = 1.5; ring_ap = 18; ring_r = 17.5; ring_a = [30, 150, 270];   // ears clear the lid bosses at -30/90/210
insert = [3.2, 3.2];         // M2 heat-set insert hole: diameter, depth
board_gap = 1.5;             // board top below the ring
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
module tie_anchor_old() intersection() { outer(); translate([-40, R + wall + 4, cable_z + 2]) cube([80, 4, 4]); }   // bridge across the channel; tie wraps bar + cable
seat_z = Z - ring_t - board_gap - pcb[2] - ledge;    // board top board_gap under the ring
cab_R = (pow(cab_d/2, 2) + cab_h*cab_h)/(2*cab_h);   // sphere radius of the cap
glass_z = Z + ptfe_t;                                // flat back of the glass
lip_r = cab_d/2 - capture;
lip_h = sqrt(cab_R*cab_R - lip_r*lip_r) - (cab_R - cab_h);   // glass height where the lip meets it
echo(cab_R = cab_R, lip_r = lip_r, lip_h = lip_h, dome_above_lid = glass_z + cab_h - H);
module glass(o = 0) translate([0, reach, glass_z - (cab_R - cab_h)]) intersection() { sphere(r = cab_R + o); translate([-50, -50, cab_R - cab_h]) cube(100); }
module window_cut() {
  translate([0, reach, Z - 1]) cylinder(d = cab_d + 0.4, h = ptfe_t + 1);    // PTFE pocket; the glass goes up through it
  glass(seat_gap);                                                            // curved seat
  translate([0, reach, glass_z + lip_h + 0.4]) cylinder(h = 20, r1 = lip_r, r2 = lip_r + 20/tan(bevel));   // bevel to the lip
  for (a = ring_a) translate([ring_r*cos(a), reach + ring_r*sin(a), Z - 1]) cylinder(d = insert[0], h = insert[1] + 1);
}
module ring() translate([0, reach, Z - ring_t]) difference() {
  union() { cylinder(r = cab_d/2 + 2, h = ring_t); for (a = ring_a) hull() { cylinder(r = 5, h = ring_t); translate([ring_r*cos(a), ring_r*sin(a), 0]) cylinder(d = 7, h = ring_t); } }
  translate([0, 0, -1]) cylinder(d = ring_ap, h = ring_t + 2);
  for (a = ring_a) translate([ring_r*cos(a), ring_r*sin(a), -1]) cylinder(d = 2.4, h = ring_t + 2);
}
module ptfe() color("white") translate([0, reach, Z]) cylinder(d = cab_d + 0.2, h = ptfe_t);
module tie_anchor() {}
module seat() translate([0, reach, seat_z]) {
  bw0 = pcb[0] + 2*fit;
  fh = seat_z - floor_z + ledge + 1;
  for (s = [-1, 1]) intersection() {   // two fins: from the board's edge, angling back through the tube-side insert bosses
    hull() { translate([s*(bw0/2 - lip/2), 4, -fh + ledge]) cylinder(d = 1.8, h = fh); translate([s*cos(-30)*(hw/2 - w - 2)*1.3, sin(-30)*(hw/2 - w - 2)*1.3, -fh + ledge]) cylinder(d = 1.8, h = fh); }
    translate([0, 0, -50]) cylinder(d = hw - 2*w + 0.5, h = 100);
  }
  bw = pcb[0] + 2*fit; bl = pcb[1] + 2*fit;
  for (s = [-1, 1]) translate([s < 0 ? -bw/2 : bw/2 - lip, -bl/2 + 4, 0]) cube([lip, bl - 4, ledge]);       // edge ledges
  for (s = [-1, 1]) translate([s < 0 ? -bw/2 - cwall : bw/2, -bl/2 + 2, 0]) cube([cwall, bl - 4, ledge + pcb[2]]);  // side walls
  translate([0, -bl/2 + 3, -(seat_z - floor_z)]) cylinder(d = 7, h = seat_z - floor_z + ledge);              // screw post
}
module bosses() intersection() { outer(); for (b = lid_bosses) translate([b[0], b[1], Z - 9]) { cylinder(d = 9, h = 9); translate([0,0,-4.5]) cylinder(d1 = 0, d2 = 9, h = 4.5); } }
module arm_half() difference() {
  union() { difference() { intersection() { outer(); translate([-200, 0, -1]) cube([400, 400, Z + 1]); } pocket(); } bosses(); tie_anchor(); seat(); }
  bore(); slot();
  translate([0, R + wall + 3, -1]) cylinder(d = 5, h = 12);                                    // drain at the low point
  translate([-18, reach - 5.5, floor_z + 2]) cube([36, 3, 3.5]);                               // zip-tie tunnel through both fins
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
  window_cut();
  for (b = lid_bosses) translate([b[0], b[1], Z - 1]) cylinder(d = 3.4, h = 20);
}
module dome() color("LightCyan", 0.6) glass();
module board() color("green") translate([-pcb[0]/2, reach - pcb[1]/2, seat_z + ledge]) cube(pcb);
module cable() color("red") { hull() { translate([0, reach - 8, seat_z - 2]) sphere(d = 5); translate([0, R + wall + 6, cable_z + 8.5]) sphere(d = 5); }
  hull() { translate([0, R + wall + 6, cable_z + 8.5]) sphere(d = 5); translate([0, R - 6, cable_z]) sphere(d = 5); } }
module tie() color("black") translate([0, R + wall + 13.5, cable_z - 10 + 2]) rotate([0, 90, 90]) difference() { hull() { translate([-1, 0, 0]) cylinder(d = 9, h = 2.5, center = true); translate([-5, 0, 0]) cylinder(d = 4, h = 2.5, center = true); } cylinder(d = 7.5, h = 4, center = true); }
module tube() color("silver", 0.3) difference() { translate([0,0,-40]) cylinder(d = tube_od, h = H + 170); translate([0, R - 4, cable_z]) rotate([-90,0,0]) cylinder(d = 12, h = 10); }
if (view == "arm_half") arm_half();
if (view == "lid_print") translate([0, -reach, -Z]) lid();             // bottom face down; the seat is a dome ceiling
if (view == "ring_print") translate([0, -reach, -(Z - ring_t)]) ring();
module cut() rotate([0, 0, 90]) linear_extrude(1) projection(cut = true) rotate([0, 90, 0]) children();   // x = 0 slice: across = -y, up = z
if (view == "window") {   // section through the window stack
  color("CadetBlue") cut() lid(); color("LightCyan") cut() glass(); color("white") cut() ptfe(); color("orange") cut() ring(); color("green") cut() board();
}
lift = view == "exploded" ? 35 : 0; back = view == "exploded" ? 40 : 0;
if (view == "open" || view == "exploded" || view == "closed" || view == "section") rotate([0, cant, 0]) {
  tube(); board(); cable();
  if (view == "section") { color("SteelBlue") intersection() { arm_half(); translate([-400, -200, -100]) cube(400); } color("CadetBlue") intersection() { lid(); translate([-400, -200, -100]) cube(400); } intersection() { union() { dome(); ptfe(); color("orange") ring(); } translate([-400, -200, -100]) cube(400); } }
  else { color("SteelBlue") arm_half(); color("LightSteelBlue") translate([0, -back, 0]) back_half(); }
  if (view == "closed" || view == "exploded") translate([0, 0, lift]) { color("CadetBlue") lid(); dome(); ptfe(); color("orange") translate([0, 0, -lift/3]) ring(); }
}
