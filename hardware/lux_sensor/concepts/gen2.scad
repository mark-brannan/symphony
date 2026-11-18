// One continuous blended body: collar + head as a single hull. Flush lid. Outer rims only rounded/chamfered.
cant = 15; tilt = 8; dir = 90; gap = 20; zup = 10;
hw = 56; ph = 22; edge = "round";   // round | chamfer
lid_t = 5; e = 3;
tube_od = 38.1; R = tube_od/2; H = 48; wall = 6;
reach = R + gap + hw/2;
u = [cos(dir), sin(dir), 0];
P = [u[0]*reach, u[1]*reach, H + zup];
$fn = 72;
module ecyl(d, h) if (edge == "round") rotate_extrude() hull() { translate([d/2 - e, e]) circle(e); translate([d/2 - e, h - e]) circle(e); square([0.01, h]); }
                  else hull() { translate([0,0,e]) cylinder(d = d, h = h - 2*e); cylinder(d = d - 2*e, h = h); }
module at_head() translate(P) rotate([0, tilt - cant, 0]) children();
module collar() hull() for (s = [-1, 1]) translate([0, s*6, 0]) ecyl(tube_od + 2*wall, H);   // oval: bolt meat inside, no ears
module head_solid(t = 0) at_head() translate([0,0,-ph]) ecyl(hw, ph + t);
module body() difference() {
  hull() { collar(); head_solid(); }
  at_head() translate([0,0,-lid_t]) cylinder(d = hw + 20, h = 50);                // lid plane
  at_head() translate([0,0,-ph + 6]) cylinder(d = hw - 14, h = ph);              // cavity
  translate([0,0,-1]) cylinder(d = tube_od + 0.4, h = H + 2);
  for (s = [-1, 1]) for (z = [9, H - 9]) translate([-30, s*(R + 6), z]) rotate([0,90,0]) cylinder(d = 8, h = 60);  // counterbores, both sides
}
module lid() color("SteelBlue") intersection() {
  hull() { collar(); head_solid(); }
  at_head() difference() { translate([0,0,-lid_t + 0.6]) cylinder(d = hw + 20, h = 50); translate([0,0,-1]) cylinder(d = 26, h = 10); }
}
module dome() color("white", 0.6) at_head() translate([0,0,-1]) scale([1,1,12/12.5]) sphere(d = 25);
module tube() color("silver", 0.35) translate([0,0,-40]) cylinder(d = tube_od, h = H + 170);
rotate([0, cant, 0]) { tube(); color("SteelBlue") body(); lid(); dome(); }
