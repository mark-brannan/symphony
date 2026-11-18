// Concept variants for the exterior lux mount. Shape only: no bores, no split, no bolts cut.
v = 1;
tube_od = 38.1; shell_t = 5; H = 44;
R = tube_od/2; Ro = R + shell_t;
pd = 36; ph = 16;          // puck
$fn = 72;

module rcyl(d, h, r = 3) rotate_extrude() offset(r = r) offset(delta = -r) square([d/2, h]);
module rcyl_half(d, h, r = 3) rotate_extrude() intersection() { offset(r = r) offset(delta = -r) translate([-d/2,0]) square([d, h]); square([d/2, h]); }
module shell() difference() { rcyl(2*Ro, H, 2.5); translate([0,0,-1]) cylinder(r = R + 0.2, h = H + 2); }
module ears() for (s = [-1, 1]) hull() {     // blended bolt bosses, not paddles
  translate([0, s*(Ro + 4), 3]) scale([0.7,1,1]) rcyl(12, H - 6, 3);
  translate([0, s*(Ro - 4), 1]) scale([0.7,1,1]) rcyl(14, H - 2, 3);
}
module puck(x, zt) translate([x, 0, zt - ph]) difference() {
  rcyl(pd, ph, 3);
  translate([0,0,ph-4]) cylinder(d = 30, h = 5);
}
module dome(x, zt) color("white", 0.55) translate([x,0,zt-2]) scale([1,1,12/12.5]) sphere(d = 25);
module bezel(x, zt) color("orange") translate([x,0,zt-4]) difference() { cylinder(d = 29.7, h = 3.6); translate([0,0,-1]) cylinder(d = 18, h = 6); }
module tube() color("silver", 0.35) translate([0,0,-40]) cylinder(d = tube_od, h = H + 130);
function bz(p0, p1, p2, t) = (1-t)*(1-t)*p0 + 2*(1-t)*t*p1 + t*t*p2;

module body(v) {
  if (v == 1) {   // FIN: a tall tapering gusset the full height of the shell
    xc = Ro + 24; zt = H + 14;
    shell(); ears();
    hull() {
      translate([Ro - 5, 0, 7]) sphere(d = 12);
      translate([Ro - 5, 0, H - 4]) sphere(d = 12);
      translate([xc, 0, zt - ph]) rcyl(26, 10, 3);
    }
    puck(xc, zt); dome(xc, zt); bezel(xc, zt);
  }
  if (v == 2) {   // POD: shell and puck are one stadium, tops flush
    xc = Ro + 12; zt = H;
    difference() {
      hull() { rcyl(2*Ro, H, 4); translate([xc,0,0]) rcyl(pd, H, 4); }
      translate([0,0,-1]) cylinder(r = R + 0.2, h = H + 2);
      translate([xc,0,zt-4]) cylinder(d = 30, h = 5);
    }
    ears(); dome(xc, zt); bezel(xc, zt);
  }
  if (v == 3) {   // SWAN NECK: leaves the shell level, curls up under the puck, tapers
    xc = Ro + 32; zt = H + 22;
    shell(); ears();
    p0 = [Ro - 6, 0, H*0.45]; p1 = [xc, 0, H*0.45]; p2 = [xc, 0, zt - ph + 3];
    n = 16;
    for (i = [0:n-1]) hull() {
      translate(bz(p0,p1,p2,i/n))     sphere(d = 24 - 8*i/n);
      translate(bz(p0,p1,p2,(i+1)/n)) sphere(d = 24 - 8*(i+1)/n);
    }
    puck(xc, zt); dome(xc, zt); bezel(xc, zt);
  }
  if (v == 4) {   // SHELF: one flat top running from the shell to the sensor, web beneath
    xc = Ro + 26; zt = H;
    shell(); ears();
    difference() {
      union() {
        hull() { translate([Ro - 8, 0, zt - 12]) rcyl_half(30, 12, 3); translate([xc,0,zt-ph]) rcyl(pd, ph, 3); translate([Ro-4,-15,zt-12]) cube([1,30,12]); }
        hull() { translate([Ro - 4, -4, 3]) cube([1, 8, H - 6]); translate([xc - 6, -4, zt - ph]) cube([1, 8, 2]); }
      }
      translate([0,0,-1]) cylinder(r = R + 0.2, h = H + 2);
      translate([xc,0,zt-4]) cylinder(d = 30, h = 5);
    }
    dome(xc, zt); bezel(xc, zt);
  }
  if (v == 5) {   // SPLIT ARM: arm lies in the clamp's split plane; cable is laid in a groove, not threaded
    yc = Ro + 30; zt = H + 10;
    shell();
    // one ear stays a bolt boss; the other grows into the arm
    hull() { translate([0, -(Ro + 4), 3]) scale([0.7,1,1]) rcyl(12, H - 6, 3); translate([0, -(Ro - 4), 1]) scale([0.7,1,1]) rcyl(14, H - 2, 3); }
    hull() {
      translate([0, Ro - 4, 8]) scale([0.9,1,1]) sphere(d = 14);
      translate([0, Ro - 4, H - 6]) scale([0.9,1,1]) sphere(d = 14);
      translate([0, yc, zt - ph + 5]) scale([1,1,0.4]) sphere(d = 26);
    }
    translate([-(Ro+30)+Ro+30,0,0]) translate([0, yc, zt - ph]) difference() { rcyl(pd, ph, 3); translate([0,0,ph-4]) cylinder(d = 30, h = 5); }
    translate([0, yc, 0]) { dome(0, zt); bezel(0, zt); }
    color("red", 0.6) translate([0,0,0]) for (s=[0]) hull() { translate([0, Ro-2, H*0.5]) sphere(d = 2); translate([0, yc, zt-ph]) sphere(d = 2); }
  }
}

tube();
body(v);
