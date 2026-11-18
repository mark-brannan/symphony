// Exterior lux sensor: clamshell on a vertical tube (like the antenna-mount-for-oversized-tubing),
// the sensor puck grown out of the aft half. Print halves split-face down in ASA (PETG chalks in UV).
// Frame: tube axis = +z, aft = +x, halves split on the x=0 plane, bolts at the +-y flanges.

tube_od   = 38.1;   // 1.5" OD, ASSUMED -- measure the real tube
cant_deg  = 5;      // tube leans aft by this much
face_deg  = 90;     // window normal, degrees from zenith toward aft (0 = up, 90 = level aft)
part      = "assembly";  // "assembly" | "aft" | "front" | "bezel"

dome_d    = 25;     // glass half-dome diameter
dome_h    = 12;     // dome height above its rim (ASSUMED)
pcb_w     = 15;     // sensor board (GY-302-class)
pcb_l     = 20;
aperture  = 18;
head_od   = 36;
head_len  = 30;
cav_id    = 28;
cav_depth = 14;
bore_d    = 9;      // cat5-class cable
shell_t   = 5;      // shell wall
shell_h   = 44;
flange_w  = 12;     // ear width beyond the shell
flange_t  = 6;
bolt_d    = 4.4;    // M4 clearance
$fn = 72;

R   = tube_od/2;
Ro  = R + shell_t;
alpha = face_deg - cant_deg;           // window tilt in the tube frame
zc  = shell_h/2;                       // puck centred on the shell
xc  = R + 2 + head_len*sin(alpha);     // puck back overlaps the shell wall
hole_z = zc - ((xc - R)/sin(alpha))*cos(alpha);   // drill the tube hole here, measured from the shell's bottom edge
echo(tube_hole_height_above_shell_bottom = hole_z);

module head_frame() { translate([xc,0,zc]) rotate([0,alpha,0]) children(); }   // local z = window normal
module rounded_profile_full(r, h, rr) { offset(r = rr) offset(delta = -rr) translate([-r,0]) square([2*r, h]); }

module shell_full() {
  rotate_extrude() translate([R + 0.2, 0]) offset(r = 2) offset(delta = -2) square([shell_t, shell_h]);
}
module flanges() {   // flat ears on the split plane, +-y, with chamfered outer corners
  for (s = [-1, 1]) for (z = [7, shell_h - 7])
    translate([-flange_t, s*(R + shell_t/2 + flange_w/2 + 1), z]) 
      cube([2*flange_t, flange_w + shell_t, 12], center = true);
}
module bolts() {
  for (s = [-1, 1]) for (z = [7, shell_h - 7])
    translate([0, s*(Ro + flange_w/2 - 1), z]) rotate([0,90,0]) cylinder(d = bolt_d, h = 40, center = true);
}
module head_outer() {
  head_frame() translate([0,0,-head_len])
    rotate_extrude() intersection() { rounded_profile_full(head_od/2, head_len, 4); square([head_od/2, head_len]); }
}
module head_cuts() {
  head_frame() {
    translate([0,0,-cav_depth]) cylinder(d = cav_id, h = cav_depth + 1);
    translate([0,0,-5]) cylinder(d = cav_id + 2, h = 6);                            // ledge for the bezel
    translate([0,0,-head_len-1]) cylinder(d = bore_d, h = head_len - cav_depth + 2); // cable bore out the back
  }
}

module whole() {   // both halves joined; the two parts below are its x>0 / x<0 halves
  difference() {
    union() { shell_full(); flanges(); head_outer(); }
    translate([0,0,-1]) cylinder(d = tube_od + 0.4, h = shell_h + 2);
    head_cuts();
    bolts();
  }
}
module half(sgn) { intersection() { whole(); translate([sgn > 0 ? 0 : -100, -100, -10]) cube([100, 200, shell_h + 120]); } }

module bezel() {   // plate with aperture and dome seat, silicone-bedded onto the front ledge
  head_frame() translate([0,0,-5]) difference() {
    cylinder(d = cav_id + 2 - 0.3, h = 5);
    translate([0,0,-1]) cylinder(d = aperture, h = 7);
    translate([0,0,2]) cylinder(d = dome_d + 0.4, h = 4);
  }
}
module dome() { color("white", 0.5) head_frame() translate([0,0,-3]) scale([1,1,dome_h/(dome_d/2)]) sphere(d = dome_d); }
module pcb()  { color("green") head_frame() translate([-pcb_w/2,-pcb_l/2,-5-1.6-1]) cube([pcb_w,pcb_l,1.6]); }
module tube() { color("silver", 0.4) translate([0,0,-30]) cylinder(d = tube_od, h = shell_h + 100); }

if (part == "aft") half(1);
else if (part == "front") half(-1);
else if (part == "bezel") bezel();
else rotate([0,-cant_deg,0]) {
  tube(); color("gold") half(1); color("goldenrod") translate([-0.0,0,0]) half(-1); color("orange") bezel(); dome(); pcb();
}
