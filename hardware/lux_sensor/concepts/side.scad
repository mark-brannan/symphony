// Side arm (in the clamp's split plane) + serviceable head, levelled against the tube's aft cant.
// Tube frame: tube axis z, aft +x, split plane x=0, arm along +y.
explode = 0;
cant = 5;                          // tube leans aft
tube_od = 38.1; shell_t = 5; H = 44;
R = tube_od/2; Ro = R + shell_t;
pd = 56; ph = 22; cav = 42; cav_d = 16; lid_t = 5;
gap = 20;                          // tube surface to head edge
yc = R + gap + pd/2; zt = H + 16;
$fn = 72;
module rcyl(d, h, r = 3) rotate_extrude() offset(r = r) offset(delta = -r) square([d/2, h]);
module lvl() translate([0,yc,zt]) rotate([0,-cant,0]) translate([0,-yc,-zt]) children();   // head faces zenith
module shell() difference() { rcyl(2*Ro, H, 2.5); translate([0,0,-1]) cylinder(r = R + 0.2, h = H + 2); }
module ear() hull() { translate([0, -(Ro + 4), 3]) scale([0.7,1,1]) rcyl(12, H - 6, 3); translate([0, -(Ro - 4), 1]) scale([0.7,1,1]) rcyl(14, H - 2, 3); }
module screws_at() for (a = [0, 120, 240]) rotate(a) translate([cav/2 + 3.5, 0, 0]) children();
module cup() difference() {
  union() {
    lvl() translate([0, yc, zt - ph]) rcyl(pd, ph, 4);
    hull() {
      translate([0, Ro - 5, 7]) sphere(d = 14);
      translate([0, Ro - 5, H - 5]) sphere(d = 14);
      lvl() translate([0, yc - 6, zt - ph + 4]) scale([1, 1.2, 0.5]) sphere(d = 30);
    }
  }
  lvl() translate([0, yc, zt - cav_d]) cylinder(d = cav, h = cav_d + 1);
  lvl() translate([0, yc, zt]) screws_at() translate([0,0,-8]) cylinder(d = 4, h = 9);
  translate([0,0,-1]) cylinder(r = R + 0.2, h = H + 2);
}
module lid() color("orange") lvl() translate([0, yc, zt + explode]) difference() {
  rcyl(pd, lid_t, 2);
  translate([0,0,-1]) cylinder(d = 18, h = lid_t + 2);
  translate([0,0,lid_t - 2]) cylinder(d = 25.4, h = 3);
  screws_at() translate([0,0,-1]) cylinder(d = 3.4, h = lid_t + 2);
}
module dome() color("white", 0.55) lvl() translate([0, yc, zt + explode + lid_t - 2]) scale([1,1,12/12.5]) sphere(d = 25);
module tube() color("silver", 0.35) translate([0,0,-40]) cylinder(d = tube_od, h = H + 160);
rotate([0, cant, 0]) { tube(); color("SteelBlue") { shell(); ear(); cup(); } lid(); dome(); }
