// Lux sensor mount, rev 8. Tube frame (z up the tube, aft +x); the head faces along the tube, so it tips aft with the cant.
// Arm half: collar half + open trough + cup, top open. Cable slot open to the top. Top plate is the only cover.
cant = 15;
hw = 56; lid_t = 4; e = 5; w = 3;
tube_od = 38.1; R = tube_od/2; H = 48; wall = 6; gap = 20;
view = "open";      // open | exploded | closed | section
reach = R + gap + hw/2;
Z = H - lid_t;      // top of the base = underside of the plate
// Window: glass cabochon loaded from below, dome up through a curved lip; 1 mm PTFE diffuser on its flat back;
// a ring screwed to the lid's underside (M2 into heat-set inserts) holds both. Silicone in the lip, not epoxy.
cab_d = 24.8; cab_h = 6;     // owner's cabochons, measured
ptfe_t = 1;                  // PTFE sheet, cut to the pocket
capture = 1.5;               // lip overlaps the glass by this much of its radius
seat_gap = 0.15;             // silicone between glass and lip
bevel = 30;                  // lid top falls toward the lip at this angle, so it shades little low sun
ring_t = 1.5; ring_ap = 18; ring_r = 17.5; ring_a = [30, 150, 270];   // ears clear the lid bosses at -30/90/210
insert = [3.2, 3.2];         // M2 heat-set insert hole: diameter, depth
board_gap = 1.5;             // lux board top below the ring
// Board stack under the window: VEML7700 on a printed deck, deck on the QwiicBus EndPoint, EndPoint on floor posts.
// One set of 4 x M3 bolts runs deck -> EndPoint -> heat-set inserts in the posts. Cat5 arrives by RJ45 plug, no solder.
lux = [25.4, 17.78, 1.6];    // Adafruit VEML7700 (4162), long side across the arm, clear of the RJ45; family layout, NOT calipered
lux_holes = [20.32, 12.7];   // M2.5, self-tapping into the deck; only the far pair is used, the near pair sits over the deck's bolts
ep = [25.4, 44.45, 1.6];     // SparkFun QwiicBus EndPoint (16988), jack end toward the tube; parts.md
ep_hole = 20.32;             // 4-40 holes, square, 2.54 in from the far end's edges (photo); M3 passes
ep_shift = 6;                // hole square's centre this far past the window centre, so the deck's bolts miss the lux screws
jack = [16.5, 23.2, 13.5];   // RJ45 body: width, length, height above the board (height a guess)
jack_over = 9.7;             // jack overhangs the board end (photo)
plug_z = 6.5;                // plug centre above the board top (guess)
plug = [11.7, 21, 14];       // bootless RJ45 plug: width, length, height with latch
jack_clear = 1.5;            // jack top below the lid
deck_t = 4;                  // deck: flat top carries the lux board, M3 heads counterbored from the top
m3_cb = [6.4, 3];            // M3 socket head counterbore: diameter, depth
m3_insert = [4.0, 5];        // M3 heat-set insert hole in the floor posts
post_h = 6;                  // floor post height under the EndPoint
lux_top = Z - ring_t - board_gap; lux_bot = lux_top - lux[2];
deck_bot = lux_bot - deck_t;
ep_top = Z - jack_clear - jack[2]; ep_bot = ep_top - ep[2];
cable_z = ep_top + plug_z;   // tube hole centre: the plug's axis
slot_w = plug[0] + 1.3;
floor_z = ep_bot - post_h;
ph = H - floor_z + 3;        // head height, from the stack (w = 3)
ep_c = reach + ep_shift;     // EndPoint hole-square centre
ep_far = ep_c + ep_hole/2 + 2.54;
jack_mouth = ep_far - ep[1] - jack_over;
ep_bolts = [for (sx = [-1, 1]) for (sy = [-1, 1]) [sx*ep_hole/2, ep_c + sy*ep_hole/2]];
lux_screws = [for (sx = [-1, 1]) [sx*lux_holes[0]/2, reach + lux_holes[1]/2]];
assert(reach - lux[1]/2 - 1 - (jack_mouth + jack[1]) >= 1, "RJ45 body runs into the deck");
assert(deck_bot - ep_top >= 3.5, "deck legs too short to clear the EndPoint's Qwiic sockets");
echo(head_height = ph, cable_z = cable_z, jack_mouth_to_collar = jack_mouth - (R + 6), deck_legs = deck_bot - ep_top);
$fn = 120;
module ecyl(d, h) rotate_extrude() hull() { translate([d/2 - e, e]) circle(e); translate([d/2 - e, h - e]) circle(e); square([0.01, h]); }
module collar() hull() for (s = [-1, 1]) translate([s*6, 0, 0]) ecyl(tube_od + 2*wall, H);
module outer() hull() { collar(); translate([0, reach, H - ph]) ecyl(hw, ph); }
module bore() translate([0,0,-1]) cylinder(d = tube_od + 0.4, h = H + 2);
bolt_xz = [for (s = [-1, 1]) for (z = [10, H - 10]) [s*(R + 6), z]];
lid_bosses = [for (a = [-30, 90, 210]) [cos(a)*(hw/2 - w - 2), reach + sin(a)*(hw/2 - w - 2)]];
module pocket() difference() {
  hull() { translate([0, reach, floor_z]) ecyl(hw - 2*w, ph); for (s = [-1, 1]) translate([s*6, 0, w]) ecyl(tube_od + 2*wall - 2*w, H); }
  collar();   // bolt meat and ring stay whole
}
module slot() hull() { translate([0, R - 3, cable_z]) rotate([-90,0,0]) cylinder(d = slot_w, h = wall + 6); translate([-slot_w/2, R - 3, H]) cube([slot_w, wall + 6, 1]); }   // round bottom, open to the top
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
module posts() for (b = ep_bolts) translate([b[0], b[1], floor_z - 4]) cylinder(d = 7.5, h = ep_bot - floor_z + 4);
module deck() difference() {   // prints top face down
  union() {
    translate([-ep[0]/2 - 0.5, reach - lux[1]/2 - 1, deck_bot]) cube([ep[0] + 1, ep_c + ep_hole/2 + 3.5 - (reach - lux[1]/2 - 1), deck_t]);
    for (b = ep_bolts) translate([b[0], b[1], ep_top + 0.2]) cylinder(d = 6.5, h = deck_bot - ep_top);   // legs
  }
  for (b = ep_bolts) translate([b[0], b[1], 0]) { cylinder(d = 3.4, h = 100); translate([0, 0, lux_bot - m3_cb[1]]) cylinder(d = m3_cb[0], h = 10); }
  for (b = lux_screws) translate([b[0], b[1], lux_bot - 3.5]) cylinder(d = 2.1, h = 4);
  translate([-5, reach - 5, deck_bot - 1]) cube([10, 10, deck_t + 2]);                        // lightening window
  for (b = lid_bosses) translate([b[0], b[1], 0]) cylinder(d = 10, h = 100);                  // clears the lid bosses
}
module bosses() intersection() { outer(); for (b = lid_bosses) translate([b[0], b[1], Z - 9]) { cylinder(d = 9, h = 9); translate([0,0,-4.5]) cylinder(d1 = 0, d2 = 9, h = 4.5); } }
module arm_half() difference() {
  union() { difference() { intersection() { outer(); translate([-200, 0, -1]) cube([400, 400, Z + 1]); } pocket(); } bosses(); posts(); }
  bore(); slot();
  translate([0, R + wall + 3, -1]) cylinder(d = 5, h = 12);                                    // drain at the low point
  for (b = lid_bosses) translate([b[0], b[1], Z - 6]) cylinder(d = 4, h = 7);
  for (b = ep_bolts) translate([b[0], b[1], ep_bot - m3_insert[1]]) cylinder(d = m3_insert[0], h = m3_insert[1] + 1);
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
module board() {
  color("green") translate([-lux[0]/2, reach - lux[1]/2, lux_bot]) cube(lux);
  color("red", 0.9) translate([-ep[0]/2, ep_far - ep[1], ep_bot]) cube(ep);
  color("DimGray") translate([-jack[0]/2, jack_mouth, ep_top]) cube([jack[0], jack[1], jack[2]]);
}
module cable() { color("SkyBlue") translate([-plug[0]/2, jack_mouth - plug[1] + 6, cable_z - plug[2]/2]) cube(plug);
  color("blue") hull() { translate([0, jack_mouth - plug[1] + 6, cable_z]) sphere(d = 5); translate([0, -4, cable_z - 8]) sphere(d = 5); }
  color("blue") hull() { translate([0, -4, cable_z - 8]) sphere(d = 5); translate([0, -4, -40]) sphere(d = 5); } }
module tube() color("silver", 0.3) difference() { translate([0,0,-40]) cylinder(d = tube_od, h = H + 170); translate([0, R - 4, cable_z]) rotate([-90,0,0]) cylinder(d = 16, h = 10); }   // tube hole passes the plug: 16 mm
if (view == "arm_half") arm_half();
if (view == "lid_print") translate([0, -reach, -Z]) lid();             // bottom face down; the seat is a dome ceiling
if (view == "deck_print") translate([0, -reach, lux_bot]) mirror([0, 0, 1]) deck();
if (view == "ring_print") translate([0, -reach, -(Z - ring_t)]) ring();
module cut() rotate([0, 0, 90]) linear_extrude(1) projection(cut = true) rotate([0, 90, 0]) children();   // x = 0 slice: across = -y, up = z
if (view == "window") {   // section through the window stack
  color("CadetBlue") cut() lid(); color("LightCyan") cut() glass(); color("white") cut() ptfe(); color("orange") cut() ring(); color("green") cut() board(); color("Peru") cut() deck();
}
lift = view == "exploded" ? 35 : 0; back = view == "exploded" ? 40 : 0;
if (view == "open" || view == "exploded" || view == "closed" || view == "section") rotate([0, cant, 0]) {
  tube(); board(); cable(); color("Peru") translate([0, 0, lift/2]) deck();
  if (view == "section") { color("SteelBlue") intersection() { arm_half(); translate([-400, -200, -100]) cube(400); } color("CadetBlue") intersection() { lid(); translate([-400, -200, -100]) cube(400); } intersection() { union() { dome(); ptfe(); color("orange") ring(); } translate([-400, -200, -100]) cube(400); } }
  else { color("SteelBlue") arm_half(); color("LightSteelBlue") translate([0, -back, 0]) back_half(); }
  if (view == "closed" || view == "exploded") translate([0, 0, lift]) { color("CadetBlue") lid(); dome(); ptfe(); color("orange") translate([0, 0, -lift/3]) ring(); }
}
