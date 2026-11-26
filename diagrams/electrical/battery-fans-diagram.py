# -*- coding: utf-8 -*-
"""Generates the battery-compartment fan wiring diagram (SVG). Run from the repo root."""
import os

RED  = "#c62828"   # +12 V fused feed
BLK  = "#212121"   # negative
ORA  = "#e07000"   # switched 12 V to the fans
BLU  = "#1565c0"   # temperature sensor
INK  = "#1a1a1a"
MUTE = "#5f6368"
FONT = "font-family='DejaVu Sans, Helvetica, Arial, sans-serif'"
W, H = 1200, 860

# Drawing helpers follow bilge-alarm-diagrams.py; that script writes its sheets on import.
def esc(s):
    """Escape &, < and > for SVG text content."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def txt(x, y, s, size=13, anchor="start", fill=INK, weight="normal"):
    """SVG text element at (x, y)."""
    return ("<text x='%g' y='%g' %s font-size='%g' font-weight='%s' "
            "text-anchor='%s' fill='%s'>%s</text>"
            % (x, y, FONT, size, weight, anchor, fill, esc(s)))

def poly(pts, color, w=2.6, dash=None):
    """Open polyline through `pts`."""
    d = " stroke-dasharray='%s'" % dash if dash else ""
    p = " ".join("%g,%g" % (a, b) for a, b in pts)
    return ("<polyline points='%s' fill='none' stroke='%s' stroke-width='%g' "
            "stroke-linecap='round' stroke-linejoin='round'%s/>" % (p, color, w, d))

def box(x, y, w, h, fill="#ffffff", stroke=INK, sw=2, rx=4, dash=None):
    """Rounded rectangle."""
    d = " stroke-dasharray='%s'" % dash if dash else ""
    return ("<rect x='%g' y='%g' width='%g' height='%g' rx='%g' fill='%s' "
            "stroke='%s' stroke-width='%g'%s/>" % (x, y, w, h, rx, fill, stroke, sw, d))

def dot(x, y, color=INK, r=4.5):
    """Filled junction dot."""
    return "<circle cx='%g' cy='%g' r='%g' fill='%s'/>" % (x, y, r, color)

def pin(x, y, color=INK):
    """Open terminal circle."""
    return ("<circle cx='%g' cy='%g' r='4.5' fill='#ffffff' stroke='%s' "
            "stroke-width='2'/>" % (x, y, color))

def fan(x, y, label, sub, future=False):
    """Fan motor symbol at (x, y) with its + tap from the left and - lead to the right."""
    dash = "5 4" if future else None
    col = MUTE if future else INK
    s = [poly([(XPOS, y), (x - 26, y)], ORA, 2.6, dash),
         poly([(x + 26, y), (XNEG, y)], BLK, 2.6, dash),
         "<circle cx='%g' cy='%g' r='26' fill='#ffffff' stroke='%s' stroke-width='2.4'%s/>"
         % (x, y, col, " stroke-dasharray='5 4'" if future else ""),
         txt(x, y + 6, "M", 17, anchor="middle", fill=col, weight="bold"),
         txt(x + 40, y - 5, label, 13, fill=col, weight="bold"),
         txt(x + 40, y + 13, sub, 11.5, fill=MUTE)]
    if not future:
        s += [dot(XPOS, y, ORA), dot(XNEG, y, BLK)]
    return "".join(s)

XPOS, XNEG, XFAN = 690.0, 1130.0, 740.0
FANS = [("F1  80 mm IP67/68, intake", "forward wall, behind the louvred vent; pushes in", False),
        ("F2  80 mm IP67/68, intake", "forward wall, beside F1; pushes in", False),
        ("F3  120 mm IP68, exhaust", "aft wall, existing round grille; pulls out", False),
        ("F4  spare", "terminal kept free", True),
        ("F5  spare", "terminal kept free", True)]

def sheet():
    s = ["<?xml version='1.0' encoding='UTF-8'?>\n"
         "<svg xmlns='http://www.w3.org/2000/svg' width='%g' height='%g' viewBox='0 0 %g %g'>"
         % (W, H, W, H), box(0, 0, W, H, "#ffffff", "#ffffff", 0, 0),
         txt(30, 40, "Battery compartment fans, switched by the Cerbo GX on temperature", 21,
             weight="bold"),
         txt(30, 63, "Fail-on: the fans hang on the relay's NC contact, so a Cerbo that is off "
                     "or rebooting leaves them running.", 13.5, fill=MUTE)]

    # unswitched bus and fuse
    s.append(poly([(40, 120), (180, 120)], RED, 8))
    s.append(txt(40, 104, "Unswitched distribution bus +", 12.5, weight="bold"))
    s.append(poly([(150, 120), (230, 120)], RED))
    s.append(box(230, 108, 60, 24, "#ffffff", RED, 2.2, 3))
    s.append(txt(260, 125, "5 A", 12, anchor="middle", fill=RED, weight="bold"))
    s.append(txt(260, 150, "ATC, at the bus", 11, anchor="middle", fill=MUTE))
    s.append(poly([(290, 120), (600, 120), (600, 240), (560, 240)], RED))
    s.append(txt(420, 112, "16 AWG", 11.5, anchor="middle", fill=MUTE))

    # Cerbo GX
    s.append(box(330, 170, 230, 230, "#ffffff", BLU, 2.4, 6))
    s.append(txt(445, 198, "CERBO GX", 14, anchor="middle", weight="bold", fill=BLU))
    s.append(txt(445, 214, "inboard wall of the compartment", 10.5, anchor="middle", fill=MUTE))
    for y, lab in [(240, "Relay 2  COM"), (270, "NO  (not used)"), (300, "NC")]:
        s.append(txt(548, y + 4, lab, 11.5, anchor="end"))
        s.append(pin(560, y))
    s.append(txt(445, 322, "dry contact, 6 A at 30 VDC", 11, anchor="middle", fill=MUTE))
    for y, lab in [(350, "Temp 1  +"), (375, "Temp 1  –")]:
        s.append(txt(342, y + 4, lab, 11.5))
        s.append(pin(330, y, BLU))
    s.append(txt(445, 392, "own supply: existing circuit, not drawn", 10.5, anchor="middle",
                 fill=MUTE))

    # switched feed and fan + rail
    s.append(poly([(560, 300), (XPOS, 300)], ORA, 3))
    s.append(txt(625, 292, "16 AWG", 11.5, anchor="middle", fill=MUTE))
    ys = [300 + i * 82 for i in range(len(FANS))]
    s.append(poly([(XPOS, 300), (XPOS, ys[2])], ORA, 3))
    s.append(poly([(XPOS, ys[2]), (XPOS, ys[-1])], ORA, 3, "5 4"))
    s.append(poly([(XNEG, ys[0]), (XNEG, ys[2])], BLK, 3))
    s.append(poly([(XNEG, ys[2]), (XNEG, ys[-1])], BLK, 3, "5 4"))
    for y, (lab, sub, fut) in zip(ys, FANS):
        s.append(fan(XFAN + 26, y, lab, sub, fut))
    s.append(box(XPOS - 60, 160, 120, 40, "#fff3e0", ORA, 1.8, 4))
    s.append(txt(XPOS, 177, "+ lever block", 11.5, anchor="middle", weight="bold"))
    s.append(txt(XPOS, 192, "5-way", 11, anchor="middle", fill=MUTE))
    s.append(box(XNEG - 60, 160, 120, 40, "#eeeeee", BLK, 1.8, 4))
    s.append(txt(XNEG, 177, "– lever block", 11.5, anchor="middle", weight="bold"))
    s.append(txt(XNEG, 192, "5-way", 11, anchor="middle", fill=MUTE))
    s.append(poly([(XPOS, 200), (XPOS, 300)], ORA, 1.4, "2 3"))
    s.append(poly([(XNEG, 200), (XNEG, ys[0])], BLK, 1.4, "2 3"))
    s.append(txt(XFAN + 190, 240, "fan pigtails as supplied, each fan under 1 A", 11,
                 anchor="middle", fill=MUTE))

    # negative return
    yret = ys[-1] + 50
    s.append(poly([(XNEG, ys[2]), (XNEG, yret), (180, yret)], BLK, 3))
    s.append(txt(600, yret - 8, "16 AWG", 11.5, anchor="middle", fill=MUTE))
    s.append(poly([(40, yret), (180, yret)], BLK, 8))
    s.append(txt(40, yret - 14, "Negative bus", 12.5, weight="bold"))

    # temperature sensor
    s.append(poly([(330, 350), (260, 350), (260, 470)], BLU))
    s.append(poly([(330, 375), (280, 375), (280, 470)], BLU))
    s.append(box(170, 470, 140, 54, "#e3f2fd", BLU, 2.2, 5))
    s.append(txt(240, 492, "Temp sensor", 12, anchor="middle", weight="bold", fill=BLU))
    s.append(txt(240, 510, "ASS000001000", 11, anchor="middle", fill=MUTE))
    s.append(txt(240, 545, "lug on a house-battery post", 11, anchor="middle", fill=MUTE))
    s.append(txt(240, 561, "(placement: guess)", 11, anchor="middle", fill=MUTE))

    # rule box
    rx, ry = 330, 430
    s.append(box(rx, ry, 300, 128, "#fafafa", "#cccccc", 1.4, 5))
    rule = [("Relay 2 → Function: Temperature", True),
            ("Sensor: Temp 1", False),
            ("Fans on at 35 °C, off at 30 °C (guess)", False),
            ("Wired on NC: relay energised = fans off.", False),
            ("Set polarity or rule to match; test with", False),
            ("the Cerbo unplugged (fans must run).", False)]
    for i, (line, bold) in enumerate(rule):
        s.append(txt(rx + 12, ry + 22 + i * 19, line, 11.5,
                     weight="bold" if bold else "normal"))

    # legend and footer
    for i, (c, lab) in enumerate([(RED, "+12 V fused feed"), (ORA, "switched 12 V to fans"),
                                  (BLK, "negative"), (BLU, "temperature sensor")]):
        y = 720 + i * 19
        s.append(poly([(40, y), (66, y)], c, 3.4))
        s.append(txt(73, y + 4.5, lab, 11.5, fill=MUTE))
    s.append(txt(40, 800, "dashed = spare, not fitted", 11.5, fill=MUTE))
    fy = 800
    s.append(poly([(30, fy - 90), (W - 30, fy - 90)], "#dddddd", 1.5))
    s.append(txt(330, fy - 60, "Fuse 5 A: sized to the relay's 6 A, not the wire. 16 AWG tinned, 105 °C, "
                         "is the ABYC E-11 minimum and far above the load.", 12, fill=MUTE))
    s.append(txt(330, fy - 42, "Load (guess, typical 12 V fans; read the labels): three fans about "
                              "0.6 to 1 A, five fans about 1.5 A.", 12, fill=MUTE))
    s.append(txt(330, fy - 24, "Run about 3 ft bus to Cerbo and 3 ft Cerbo to fans (guess): drop "
                              "about 0.6 % round trip at 1.5 A.", 12, fill=MUTE))
    s.append("</svg>")
    return "".join(s)

p = os.path.join("diagrams/electrical", "battery-fans.svg")
with open(p, "w") as f:
    f.write(sheet())
print("wrote", p)
