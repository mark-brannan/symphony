// Lux sensor mount, rev 9. Tube frame (z up the tube, aft +x); the head faces along the tube, so it tips aft with the cant.
// Arm half: collar half + open trough + cup, top open. Cable slot open to the top. Top plate is the only cover.
cant = 15;
lid_t = 6; e = 5; w = 3;
tube_od = 38.1; R = tube_od/2; H = 48; wall = 6; 
view = "open";      // open | exploded | closed | section
reach = 135;        // window centre from the tube axis
tip_w = 46; tip_d = 30;   // the arm tapers evenly, in plan and in side view, from the collar to this tip
Z = H - lid_t;      // top of the base = underside of the plate
// Window: glass cabochon loaded from below, dome up through a curved lip; a square of 1 mm PTFE sheet on its flat back;
// a ring screwed to the lid's underside (M3 into heat-set inserts) holds the PTFE, which presses the glass into the lip. Silicone in the lip, not epoxy.
cab_d = 24.8; cab_h = 6;     // owner's cabochons, measured
ptfe_s = 25; ptfe_t = 1;     // PTFE sheet, cut square; the pocket is square so the glass can pass up through it
capture = 1.5;               // lip overlaps the glass by this much of its radius
seat_gap = 0.15;             // silicone between glass and lip
bevel = 30;                  // lid top falls toward the lip at this angle, so it shades little low sun
ring_t = 2; ring_ap = 18; ring_ear = [[-16.5, 0], [16.5, 0]];   // two M3 ears either side, clear of the PTFE flats
m3_insert = [4.0, 4];        // M3 heat-set insert hole: diameter, depth
board_gap = 1.5;             // lux board top below the ring
// Two boards on one tray, joined by a Qwiic cable: the EndPoint (jack toward the tube) and, past it, the VEML7700 on a plinth under the window.
// Neither board's header pins can meet the other's (signal order differs), so no soldering. Boards seat in corner blocks; hot glue or pot them.
// The tray bolts to the arm with four M3 into heat-set inserts in floor posts, so it lifts out with its boards.
lux = [16.51, 16.51, 1.6];   // Adafruit VEML7700 (4162), from its Eagle .brd
ep = [25.4, 44.45, 1.6];     // SparkFun QwiicBus EndPoint (16988), from its Eagle .brd; parts.md
jack = [16.5, 23.2, 13.5];   // RJ45 body: width, length, height above the board (height a guess)
jack_over = 9.7;             // jack overhangs the board end (photo)
plug_z = 6.5;                // plug centre above the board top (guess)
plug = [11.7, 21, 14];       // bootless RJ45 plug: width, length, height with latch
jack_clear = 1.5;            // jack top below the lid
tray_t = 4;                  // tray plate
plinth = 20;                 // plinth under the VEML, square
cb = [6.4, 2.5];             // M3 socket head counterbore in the tray: diameter, depth
lux_top = Z - ring_t - board_gap; lux_bot = lux_top - lux[2];
ep_top = Z - jack_clear - jack[2]; ep_bot = ep_top - ep[2];
tray_bot = ep_bot - tray_t;
cable_z = ep_top + plug_z;   // tube hole centre: the plug's axis
slot_w = 12;
plinth_y0 = reach - plinth/2;
ep_far = plinth_y0 - 6;      // 6 mm for the Qwiic cable between the boards
ep_rear = ep_far - ep[1];
jack_mouth = ep_rear - jack_over;
tray_bolts = [[-16.5, ep_rear - 6], [16.5, ep_rear - 6], [-16.5, ep_rear - 20], [16.5, ep_rear - 20]];   // all four behind the EndPoint, inside the edge wall, where the floor is thick enough for the inserts
qwiic_y = ep_far - 12.7;     // the EndPoint's two Qwiic ports sit this far along, one on each long edge (Eagle .brd J1/J2)
assert(lux_bot - ep_bot >= 6, "plinth too short");
echo(cable_z = cable_z, length = reach + tip_w/2, loop = jack_mouth - (R + wall), plinth_h = lux_bot - ep_bot);
$fn = 120;
module ecyl(d, h) rotate_extrude() hull() { translate([d/2 - e, e]) circle(e); translate([d/2 - e, h - e]) circle(e); square([0.01, h]); }
module collar() hull() for (s = [-1, 1]) translate([s*6, 0, 0]) ecyl(tube_od + 2*wall, H);
module outer() hull() { collar(); translate([0, reach, H - tip_d]) ecyl(tip_w, tip_d); }
module bore() translate([0,0,-1]) cylinder(d = tube_od + 0.4, h = H + 2);
bolt_xz = [for (s = [-1, 1]) for (z = [10, H - 10]) [s*(R + 6), z]];
lid_bosses = [[-21, 45], [21, 45], [0, reach + plinth/2 + 5]];
module pocket(m = 0) difference() {
  hull() { translate([0, reach, H - tip_d + w + m]) ecyl(tip_w - 2*(w + m), tip_d); for (s = [-1, 1]) translate([s*6, 0, w + m]) ecyl(tube_od + 2*wall - 2*(w + m), H); }
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
  translate([-(ptfe_s + 0.4)/2, reach - (ptfe_s + 0.4)/2, Z - 1]) cube([ptfe_s + 0.4, ptfe_s + 0.4, ptfe_t + 1]);   // square PTFE pocket; the glass goes up through it
  glass(seat_gap);                                                            // curved seat
  translate([0, reach, glass_z + lip_h + 0.4]) cylinder(h = 20, r1 = lip_r, r2 = lip_r + 20/tan(bevel));   // bevel to the lip
  for (p = ring_ear) translate([p[0], reach + p[1], Z - 1]) cylinder(d = m3_insert[0], h = m3_insert[1] + 1);
}
module ring() translate([0, reach, Z - ring_t]) difference() {
  union() { translate([-(ptfe_s + 4)/2, -(ptfe_s + 4)/2, 0]) cube([ptfe_s + 4, ptfe_s + 4, ring_t]); for (p = ring_ear) hull() { translate([p[0] > 0 ? 8 : -8, p[1], 0]) cylinder(r = 6, h = ring_t); translate([p[0], p[1], 0]) cylinder(d = 7, h = ring_t); } }
  translate([0, 0, -1]) cylinder(d = ring_ap, h = ring_t + 2);
  for (p = ring_ear) translate([p[0], p[1], -1]) cylinder(d = 3.4, h = ring_t + 2);
}
module ptfe() color("white") translate([-ptfe_s/2, reach - ptfe_s/2, Z]) cube([ptfe_s, ptfe_s, ptfe_t]);
module posts() intersection() { outer(); union() {
  for (b = tray_bolts) translate([b[0], b[1], 0]) cylinder(d = 7.5, h = tray_bot); } }
module corners(x0, y0, sx, sy, h) for (cx = [0, 1], cy = [0, 1]) {   // four L-shaped corner blocks round a board: 2 thick, 6 long
  px = x0 + cx*sx; py = y0 + cy*sy;
  translate([cx ? px - 6 : px, cy ? py : py - 2, 0]) cube([6, 2, h]);
  translate([cx ? px : px - 2, cy ? py - 6 : py, 0]) cube([2, 6, h]);
}
tray_y0 = ep_rear - 24;      // tray rear edge; the rear bolt pairs sit where the chamber is widest
module tray_body() intersection() { translate([-23, tray_y0, tray_bot]) cube([46, reach + 10 - tray_y0, tray_t + 5]); pocket(0.6); }
module tray() difference() {   // prints flat, plate down
  union() {
    difference() {   // plate plus a complete wall round its whole edge, to hold potting; low only where the jack and plug cross the rear edge
      tray_body();
      translate([0, 0, ep_bot]) linear_extrude(20) offset(delta = -2) projection() tray_body();
      translate([-10, tray_y0 - 1, ep_bot + 1]) cube([20, 5, 20]);
    }
    translate([0, 0, ep_bot]) difference() {   // potting wall all round the EndPoint, 2 thick
      translate([-ep[0]/2 - 2.2, ep_rear - 2.2, 0]) cube([ep[0] + 4.4, ep[1] + 4.4, 3]);
      translate([-ep[0]/2 - 0.2, ep_rear - 0.2, -1]) cube([ep[0] + 0.4, ep[1] + 0.4, 6]);
      for (sx = [-1, 1]) translate([sx*(ep[0]/2 + 1.2) - 2.5, qwiic_y - 6, 1]) cube([5, 12, 5]);   // Qwiic notches, 1 mm lip kept
      translate([-ep[0]/2 - 3, ep_rear - 3, ep[2]]) cube([ep[0] + 6, 3, 5]);                      // rear wall flush with the board so the jack overhangs it
    }
    translate([-plinth/2, plinth_y0, ep_bot - 0.01]) cube([plinth, plinth, lux_bot - ep_bot + 0.01]);
    translate([0, 0, lux_bot]) corners(-lux[0]/2 - 0.2, reach - lux[1]/2 - 0.2, lux[0] + 0.4, lux[1] + 0.4, 2.2);
  }
  translate([-plinth/2 + 2.5, plinth_y0 + 2.5, ep_bot]) cube([plinth - 5, plinth - 5, lux_bot - ep_bot - 2.5]);   // hollow plinth
  translate([-3, reach - 3, lux_bot - 4]) cube([6, 6, 5]);                                                      // opens the plinth top
  for (b = tray_bolts) translate([b[0], b[1], 0]) { cylinder(d = 3.4, h = 100); translate([0, 0, ep_bot - cb[1]]) cylinder(d = cb[0], h = 10); }
  for (b = lid_bosses) translate([b[0], b[1], 0]) cylinder(d = 9, h = 100);
}
module bosses() intersection() { outer(); for (b = lid_bosses) translate([b[0], b[1], Z - 9]) { cylinder(d = 8, h = 9); translate([0,0,-4]) cylinder(d1 = 0, d2 = 8, h = 4); } }
module arm_half() difference() {
  union() { difference() { intersection() { outer(); translate([-200, 0, -1]) cube([400, 400, Z + 1]); } pocket(); } bosses(); posts(); }
  bore(); slot();
  translate([0, R + wall + 3, -1]) cylinder(d = 5, h = 12);                                    // drain at the low point
  for (b = lid_bosses) translate([b[0], b[1], Z - 6]) cylinder(d = 4, h = 7);
  for (b = tray_bolts) translate([b[0], b[1], tray_bot - m3_insert[1]]) cylinder(d = m3_insert[0], h = m3_insert[1] + 1);
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
  color("red", 0.9) translate([-ep[0]/2, ep_rear, ep_bot]) cube(ep);
  color("DimGray") translate([-jack[0]/2, jack_mouth, ep_top]) cube([jack[0], jack[1], jack[2]]);
}
module cable() { color("SkyBlue") translate([-plug[0]/2, jack_mouth - plug[1] + 6, cable_z - plug[2]/2]) cube(plug);
  color("blue") hull() { translate([0, jack_mouth - plug[1] + 6, cable_z]) sphere(d = 5); translate([0, -4, cable_z - 8]) sphere(d = 5); }
  color("blue") hull() { translate([0, -4, cable_z - 8]) sphere(d = 5); translate([0, -4, -40]) sphere(d = 5); } }
module tube() color("silver", 0.3) difference() { translate([0,0,-40]) cylinder(d = tube_od, h = H + 170); translate([0, R - 4, cable_z]) rotate([-90,0,0]) cylinder(d = 12, h = 10); }   // tube hole: the cable only; the plug is crimped inside the head
if (view == "arm_half") arm_half();
if (view == "lid_print") translate([0, -reach, -Z]) lid();             // bottom face down; the seat is a dome ceiling
if (view == "tray_print") translate([0, -reach, -tray_bot]) tray();
if (view == "ring_print") translate([0, -reach, -(Z - ring_t)]) ring();
module cut() rotate([0, 0, 90]) linear_extrude(1) projection(cut = true) rotate([0, 90, 0]) children();   // x = 0 slice: across = -y, up = z
if (view == "window") {   // section through the window stack
  color("CadetBlue") cut() lid(); color("LightCyan") cut() glass(); color("white") cut() ptfe(); color("orange") cut() ring(); color("green") cut() board(); color("Peru") cut() tray();
}
lift = view == "exploded" ? 35 : 0; back = view == "exploded" ? 40 : 0;
if (view == "open" || view == "exploded" || view == "closed" || view == "section") rotate([0, cant, 0]) {
  tube(); board(); cable(); color("Peru") translate([0, 0, lift/2]) tray();
  if (view == "section") { color("SteelBlue") intersection() { arm_half(); translate([-400, -200, -100]) cube(400); } color("CadetBlue") intersection() { lid(); translate([-400, -200, -100]) cube(400); } intersection() { union() { dome(); ptfe(); color("orange") ring(); } translate([-400, -200, -100]) cube(400); } }
  else { color("SteelBlue") arm_half(); color("LightSteelBlue") translate([0, -back, 0]) back_half(); }
  if (view == "closed" || view == "exploded") translate([0, 0, lift]) { color("CadetBlue") lid(); dome(); ptfe(); color("orange") translate([0, 0, -lift/3]) ring(); }
}
