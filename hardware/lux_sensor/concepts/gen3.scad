// Variant A, exploded. Split plane y=0 so the whole arm + head is ONE piece; the back half is a plain half-collar.
cant = 15; tilt = 8; gap = 20; zup = 10;
hw = 56; ph = 22; lid_t = 5; e = 3;
tube_od = 38.1; R = tube_od/2; H = 48; wall = 6;
step = 4;        // 0 assembled .. 4 fully exploded
back_out = step >= 3 ? 45 : 0;     // back half off along -y
bolts_out = step >= 3 ? 30 : 0;
board_up  = step >= 2 ? 22 : 0;
lid_up    = step >= 1 ? 45 : 0;
dome_up   = step >= 4 ? 22 : 0;
reach = R + gap + hw/2;
P = [0, reach, H + zup];
$fn = 64;
module ecyl(d, h) rotate_extrude() hull() { translate([d/2 - e, e]) circle(e); translate([d/2 - e, h - e]) circle(e); square([0.01, h]); }
module at_head() translate(P) rotate([0, tilt - cant, 0]) children();
module collar() hull() for (s = [-1, 1]) translate([s*6, 0, 0]) ecyl(tube_od + 2*wall, H);     // oval along x: bolt meat at +-x
module outer() hull() { collar(); at_head() translate([0,0,-ph]) ecyl(hw, ph); }
bolt_xz = [for (s = [-1, 1]) for (z = [10, H - 10]) [s*(R + 6), z]];
screw_at = [for (a = [30, 150, 270]) [cos(a)*(hw/2 - 6), sin(a)*(hw/2 - 6)]];
module cuts() {
  at_head() translate([0,0,-lid_t]) cylinder(d = hw + 30, h = 60);
  at_head() translate([0,0,-ph + 6]) cylinder(d = hw - 14, h = ph);
  translate([0,0,-1]) cylinder(d = tube_od + 0.4, h = H + 2);
  for (b = bolt_xz) translate([b[0], 0, b[1]]) rotate([90,0,0]) cylinder(d = 4.4, h = 80, center = true);
  for (b = bolt_xz) translate([b[0], -(R + 2), b[1]]) rotate([90,0,0]) cylinder(d = 8, h = 30);     // counterbore, back face
  for (b = bolt_xz) translate([b[0], 2, b[1]]) rotate([-90,0,0]) cylinder(d = 8, h = 4, $fn = 6);  // nut trap, arm half
  at_head() for (s = screw_at) translate([s[0], s[1], -12]) cylinder(d = 4, h = 13);              // heat-set inserts
  hull() { at_head() translate([0, -10, -ph + 6]) sphere(d = 8); translate([0, R + 1, 18]) sphere(d = 8); }  // cable path to tube hole
}
module arm_half() color("SteelBlue") difference() { intersection() { outer(); translate([-200, 0, -100]) cube([400, 400, 400]); } cuts(); }
module back_half() color("LightSteelBlue") translate([0, -back_out, 0]) difference() { intersection() { outer(); translate([-200, -400, -100]) cube([400, 400, 400]); } cuts(); }
module lid() color("CadetBlue") translate([0, 0, lid_up]) difference() {
  intersection() { outer(); at_head() translate([0,0,-lid_t + 0.6]) cylinder(d = hw + 30, h = 60); }
  at_head() translate([0,0,-1]) cylinder(d = 26, h = 20);
  at_head() for (s = screw_at) translate([s[0], s[1], -10]) cylinder(d = 3.4, h = 30);
}
module lid_screws() color("DimGray") translate([0,0,lid_up + (step >= 1 ? 20 : 0)]) at_head() for (s = screw_at) translate([s[0], s[1], 0]) { cylinder(d = 5.5, h = 2); translate([0,0,-10]) cylinder(d = 3, h = 10); }
module dome() color("white", 0.6) translate([0,0,lid_up + dome_up]) at_head() translate([0,0,-1]) intersection() { scale([1,1,12/12.5]) sphere(d = 25); translate([-20,-20,0]) cube(40); }
module board() color("green") translate([0,0,board_up]) at_head() translate([-7.5, -10, -ph + 7]) cube([15, 20, 1.6]);
module oring() color("black") translate([0,0,lid_up*0.5]) at_head() translate([0,0,-lid_t]) rotate_extrude() translate([hw/2 - 8.5, 0]) circle(d = 1.8);
module bolts() color("DimGray") for (b = bolt_xz) translate([b[0], -back_out - bolts_out - (R + 2), b[1]]) rotate([90,0,0]) { cylinder(d = 7, h = 4); translate([0,0,-36]) cylinder(d = 4, h = 36); }
module cable() color("red") translate([0,0,board_up]) at_head() translate([0, -10, -ph + 7]) cylinder(d = 2, h = 1);
module tube() color("silver", 0.3) difference() { translate([0,0,-40]) cylinder(d = tube_od, h = H + 170); translate([0, R - 2, 18]) rotate([-90,0,0]) cylinder(d = 10, h = 10); }
rotate([0, cant, 0]) { tube(); arm_half(); back_half(); lid(); lid_screws(); dome(); board(); oring(); bolts(); }
