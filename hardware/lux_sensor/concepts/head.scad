// Fin mount with a serviceable sensor head: lid with dome lifts off on 3 screws.
explode = 25;
tube_od = 38.1; shell_t = 5; H = 44;
R = tube_od/2; Ro = R + shell_t;
pd = 56; ph = 22; cav = 42; cav_d = 16; lid_t = 5;
gap = 20;                          // tube surface to head edge
xc = R + gap + pd/2; zt = H + 16;  // head centre, top of the cup
$fn = 72;
module rcyl(d, h, r = 3) rotate_extrude() offset(r = r) offset(delta = -r) square([d/2, h]);
module shell() difference() { rcyl(2*Ro, H, 2.5); translate([0,0,-1]) cylinder(r = R + 0.2, h = H + 2); }
module ears() for (s = [-1, 1]) hull() {
  translate([0, s*(Ro + 4), 3]) scale([0.7,1,1]) rcyl(12, H - 6, 3);
  translate([0, s*(Ro - 4), 1]) scale([0.7,1,1]) rcyl(14, H - 2, 3);
}
module screws_at() for (a = [90, 210, 330]) rotate(a) translate([cav/2 + 3.5, 0, 0]) children();
module cup() difference() {
  union() {
    translate([xc, 0, zt - ph]) rcyl(pd, ph, 4);
    hull() {
      translate([Ro - 5, 0, 7]) sphere(d = 14);
      translate([Ro - 5, 0, H - 5]) sphere(d = 14);
      translate([xc - 6, 0, zt - ph + 4]) scale([1.2,1,0.5]) sphere(d = 30);
    }
  }
  translate([xc, 0, zt - cav_d]) cylinder(d = cav, h = cav_d + 1);
  translate([xc, 0, zt]) screws_at() translate([0,0,-8]) cylinder(d = 4, h = 9);   // heat-set inserts
  translate([0,0,-1]) cylinder(r = R + 0.2, h = H + 2);
}
module lid() color("orange") translate([xc, 0, zt + explode]) difference() {
  rcyl(pd, lid_t, 2);
  translate([0,0,-1]) cylinder(d = 18, h = lid_t + 2);
  translate([0,0,lid_t - 2]) cylinder(d = 25.4, h = 3);
  screws_at() translate([0,0,-1]) cylinder(d = 3.4, h = lid_t + 2);
}
module oring() color("black") translate([xc, 0, zt + explode*0.45]) rotate_extrude() translate([cav/2 + 0.8, 0]) circle(d = 1.8);
module dome() color("white", 0.55) translate([xc, 0, zt + explode + lid_t - 2]) scale([1,1,12/12.5]) sphere(d = 25);
module pcb() color("green") translate([xc - 7.5, -10, zt - cav_d + 4]) cube([15, 20, 1.6]);
module tube() color("silver", 0.35) translate([0,0,-40]) cylinder(d = tube_od, h = H + 140);
tube(); shell(); ears(); color("SteelBlue") cup(); lid(); oring(); dome(); pcb();
