# -*- coding: utf-8 -*-
"""Generates the bilge high-water alarm wiring diagrams (SVG)."""
import os

RED   = "#c62828"   # +12 V
BLK   = "#212121"   # negative
ORA   = "#e07000"   # switched output (12 V when alarm active)
BLU   = "#1565c0"   # signal / isolated side
GRY   = "#9e9e9e"
INK   = "#1a1a1a"
MUTE  = "#5f6368"
BILGE = "#e3f2fd"
FONT  = "font-family='DejaVu Sans, Helvetica, Arial, sans-serif'"

def esc(s):
    """Escape &, < and > for SVG text content."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def txt(x, y, s, size=13, anchor="start", fill=INK, weight="normal", italic=False):
    """SVG text element at (x, y)."""
    st = " font-style='italic'" if italic else ""
    return ("<text x='%g' y='%g' %s font-size='%g' font-weight='%s' "
            "text-anchor='%s' fill='%s'%s>%s</text>"
            % (x, y, FONT, size, weight, anchor, fill, st, esc(s)))

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
    """Filled junction dot at (x, y)."""
    return "<circle cx='%g' cy='%g' r='%g' fill='%s'/>" % (x, y, r, color)

def hop_v(x, y, color, w=2.6):
    """Semicircular hop where a vertical wire crosses another."""
    return ("<path d='M %g,%g A 9,9 0 0 0 %g,%g' fill='none' stroke='%s' "
            "stroke-width='%g'/>" % (x, y + 9, x, y - 9, color, w))

def pin(x, y, color=INK):
    """Open terminal circle at (x, y)."""
    return ("<circle cx='%g' cy='%g' r='4' fill='#ffffff' stroke='%s' "
            "stroke-width='2'/>" % (x, y, color))

def res_v(x, y, color, label):
    """Vertical resistor centred on (x, y)."""
    return (box(x - 11, y - 24, 22, 48, "#ffffff", color, 2.2, 2)
            + txt(x + 18, y + 5, label, 12.5, fill=INK))

def diode_v(x, y, color, down=True, label=None, lx=None, anch="start"):
    """Vertical diode centred on (x, y); `down` = current flows downward."""
    s = []
    if down:
        s.append("<polygon points='%g,%g %g,%g %g,%g' fill='%s'/>"
                 % (x - 11, y - 11, x + 11, y - 11, x, y + 8, color))
        s.append(poly([(x - 13, y + 8), (x + 13, y + 8)], color, 3))
    else:
        s.append("<polygon points='%g,%g %g,%g %g,%g' fill='%s'/>"
                 % (x - 11, y + 11, x + 11, y + 11, x, y - 8, color))
        s.append(poly([(x - 13, y - 8), (x + 13, y - 8)], color, 3))
    if label:
        s.append(txt(lx if lx is not None else x + 18, y + 5, label, 12.5,
                     anchor="end" if lx is not None and lx < x else "start"))
    return "".join(s)

def push_v(x, y, color, label):
    """Vertical momentary push-to-make switch centred on (x, y)."""
    s = [poly([(x, y - 26), (x, y - 14)], color),
         poly([(x, y + 26), (x, y + 14)], color),
         poly([(x - 16, y - 14), (x + 12, y + 16)], color),
         poly([(x + 6, y - 14), (x + 22, y - 14)], color, 2.2),
         poly([(x + 14, y - 14), (x + 14, y - 24)], color, 2.2),
         txt(x + 26, y + 5, label, 12.5)]
    return "".join(s)

def bracket_v(x, y1, y2, label, side=1):
    """Vertical dimension bracket with a label."""
    s = [poly([(x - 6 * side, y1), (x, y1), (x, y2), (x - 6 * side, y2)], MUTE, 1.6)]
    s.append(txt(x + 8 * side, (y1 + y2) / 2 + 4, label, 12,
                 anchor="start" if side > 0 else "end", fill=MUTE))
    return "".join(s)

def bracket_h(y, x1, x2, label, above=False):
    """Horizontal dimension bracket with a label."""
    d = -6 if not above else 6
    s = [poly([(x1, y + d), (x1, y), (x2, y), (x2, y + d)], MUTE, 1.6)]
    s.append(txt((x1 + x2) / 2, y - 8 if above else y + 17, label, 12,
                 anchor="middle", fill=MUTE))
    return "".join(s)

def head(w, h, title, subtitle):
    """SVG document opening: canvas, title and subtitle."""
    return ("<?xml version='1.0' encoding='UTF-8'?>\n"
            "<svg xmlns='http://www.w3.org/2000/svg' width='%g' height='%g' "
            "viewBox='0 0 %g %g'>" % (w, h, w, h)
            + box(0, 0, w, h, "#ffffff", "#ffffff", 0, 0)
            + txt(30, 40, title, 21, weight="bold")
            + txt(30, 63, subtitle, 13.5, fill=MUTE))

FOOT_L1 = ("Fuse 1 A ATC/ATO  ·  all power conductors 16 AWG tinned, 105 °C  "
           "·  ampacity 25 A outside engine space, 21 A inside (×0.85)")
FOOT_L2 = ("Design load ≤ 0.25 A  ·  worst case 6 m one-way = 39 ft round trip "
           "→ 0.04 V drop (0.3 %)  ·  16 AWG holds 3 % to ~345 ft round trip")
FOOT_L3 = ("Gauge is set by the ABYC 16 AWG minimum, not by ampacity or voltage drop: "
           "no gauge change anywhere in the 1–3 m range.")

def foot(y, w, extra=None):
    """Shared sizing footer at the bottom of a sheet."""
    s = [poly([(30, y - 22), (w - 30, y - 22)], "#dddddd", 1.5)]
    s.append(txt(30, y, FOOT_L1, 12.5, fill=MUTE))
    s.append(txt(30, y + 18, FOOT_L2, 12.5, fill=MUTE))
    s.append(txt(30, y + 36, FOOT_L3, 12.5, fill=MUTE))
    if extra:
        s.append(txt(30, y + 58, extra, 12.5, fill=INK, weight="bold"))
    return "".join(s)

def legend(x, y):
    """Wire-colour legend starting at (x, y)."""
    items = [(RED, "+12 V, always-on fused feed"), (BLK, "negative"),
             (ORA, "switched 12 V (hot only during alarm)"),
             (BLU, "isolated signal side")]
    s = []
    for i, (c, lab) in enumerate(items):
        yy = y + i * 19
        s.append(poly([(x, yy), (x + 26, yy)], c, 3.4))
        s.append(txt(x + 33, yy + 4.5, lab, 11.5, fill=MUTE))
    return "".join(s)

# ---------------------------------------------------------------- shared left half
Y12, YOUT, YNEG = 70.0, 300.0, 650.0
X12DROP, XTEST = 170.0, 460.0

def source_and_sensor(sensor_title, sensor_lines, out_pin_label, xout_end):
    """Shared left half: fused feed, rails, sensor box, test branch."""
    s = []
    # bilge band
    s.append(box(188, 404, 300, 206, BILGE, "#bbdefb", 1.5, 6, "6 4"))
    s.append(txt(198, 601, "IN THE BILGE", 11.5, fill="#4a7fb5", weight="bold"))
    # +12 rail
    s.append(poly([(40, Y12), (XTEST, Y12)], RED, 3))
    s.append(txt(30, Y12 - 52, "from unswitched, always-on fused distribution", 12.5, fill=MUTE))
    s.append(box(80, Y12 - 13, 56, 26, "#ffffff", RED, 2.2, 3))
    s.append(poly([(88, Y12), (98, Y12 - 6), (110, Y12 + 6), (120, Y12), (128, Y12)], RED, 2))
    s.append(txt(108, Y12 + 34, "FUSE 1 A", 13, anchor="middle", weight="bold", fill=RED))
    # negative rail
    s.append(poly([(40, YNEG), (xout_end, YNEG)], BLK, 3))
    s.append(txt(30, YNEG + 24, "to DC negative bus", 12.5, fill=MUTE))
    # +12 down to sensor
    s.append(poly([(X12DROP, Y12), (X12DROP, 460), (228, 460)], RED))
    s.append(dot(X12DROP, Y12, RED))
    # sensor box
    s.append(box(228, 424, 232, 122, "#ffffff", INK, 2.4, 5))
    s.append(txt(344, 460, sensor_title, 13, anchor="middle", weight="bold"))
    for i, ln in enumerate(sensor_lines):
        s.append(txt(344, 482 + i * 16, ln, 11.5, anchor="middle", fill=MUTE))
    s.append(pin(228, 460, RED))
    s.append(txt(222, 448, "+12 V", 11.5, anchor="end", fill=RED))
    s.append(pin(344, 424, ORA))
    s.append(txt(354, 418, out_pin_label, 11.5, fill=ORA))
    s.append(pin(344, 546, BLK))
    s.append(txt(354, 562, "NEG", 11.5, fill=BLK))
    # sensor out -> OUT rail; sensor neg -> NEG rail
    s.append(poly([(344, 424), (344, YOUT)], ORA))
    s.append(poly([(344, 546), (344, YNEG)], BLK))
    s.append(dot(344, YOUT, ORA))
    s.append(dot(344, YNEG, BLK))
    # OUT rail
    s.append(poly([(344, YOUT), (xout_end, YOUT)], ORA, 3))
    s.append(txt(356, YOUT - 12, "switched +12 V — hot only while the alarm is active",
                 12.5, fill=ORA))
    # run brackets
    s.append(bracket_v(196, YOUT + 20, 430, "", -1))
    s.append(txt(160, 336, "Run B: 1–3 m", 12, anchor="end", fill=MUTE))
    s.append(txt(160, 352, "3-cond 16 AWG", 12, anchor="end", fill=MUTE))
    s.append(txt(160, 368, "tinned, jacketed", 12, anchor="end", fill=MUTE))
    s.append(bracket_h(Y12 - 24, 145, XTEST, "Run A — 1–3 m, 16 AWG × 2 (+12 V and negative)", True))
    # test branch
    s.append(dot(XTEST, Y12, RED))
    s.append(poly([(XTEST, Y12), (XTEST, YOUT)], RED))
    s.append(push_v(XTEST, 150, RED, "TEST (optional)"))
    s.append(diode_v(XTEST, 225, RED, True, "1N4001 — blocks back-feed", XTEST + 18))
    s.append(dot(XTEST, YOUT, ORA))
    return "".join(s)

def piezo(x=570):
    """Piezo alarm box hung between the OUT and NEG rails."""
    s = [poly([(x, YOUT), (x, 380)], ORA), poly([(x, 450), (x, YNEG)], BLK),
         dot(x, YOUT, ORA), dot(x, YNEG, BLK),
         box(x - 70, 380, 140, 70, "#ffffff", INK, 2.4, 5),
         txt(x, 408, "PIEZO ALARM", 13, anchor="middle", weight="bold"),
         txt(x, 426, "SEAFLO 95 dB, 12 V", 11.5, anchor="middle", fill=MUTE),
         txt(x, 441, "< 60 mA", 11.5, anchor="middle", fill=MUTE)]
    return "".join(s)

def cerbo(x=980, y=340, h=200, note="dry contact or open collector"):
    """Cerbo GX digital-input block with DI n and GND pins."""
    s = [box(x, y, 190, h, "#ffffff", BLU, 2.4, 5),
         txt(x + 95, y + 28, "CERBO GX MK2", 13.5, anchor="middle", weight="bold", fill=BLU),
         txt(x + 95, y + 46, "digital input block", 11.5, anchor="middle", fill=MUTE),
         txt(x + 95, y + 80, "3V3 via 10 kΩ pull-up", 11.5, anchor="middle", fill=MUTE),
         txt(x + 95, y + 96, "pull LOW to trigger", 11.5, anchor="middle", fill=MUTE),
         txt(x + 95, y + 112, "0.33 mA · NOT isolated", 11.5, anchor="middle", fill=MUTE),
         pin(x, 400, BLU), txt(x + 12, 395, "DI n", 11.5, fill=BLU),
         pin(x, 480, BLU), txt(x + 12, 475, "GND", 11.5, fill=BLU),
         txt(x + 95, y + h + 22, note, 11.5, anchor="middle", fill=MUTE, italic=True)]
    return "".join(s)

# ---------------------------------------------------------------- V1: optocoupler
def v1():
    """Variant 1 — optocoupler (recommended)."""
    W, H = 1280, 940
    s = [head(W, H, "Variant 1 — recommended: SEAFLO field switch + piezo + PC817 optocoupler",
              "Solid state end to end. Victron specifies the digital input for a dry contact "
              "or an open-collector optocoupler; this is the second case.")]
    s.append("<g transform='translate(0,70)'>")
    s.append(source_and_sensor(
        "SEAFLO electric-field switch",
        ["solid state, no moving parts", "trips ~50 mm, 3 s delay"],
        "OUT", 930))
    s.append(piezo(570))
    # opto input branch
    XA, XK = 700.0, 660.0
    s.append(dot(XA, YOUT, ORA))
    s.append(poly([(XA, YOUT), (XA, 400), (730, 400)], ORA))
    s.append(res_v(XA, 345, ORA, "R  1 kΩ  ¼ W"))
    s.append(poly([(730, 480), (XK, 480), (XK, YNEG)], BLK))
    s.append(dot(XK, YNEG, BLK))
    # D anti-parallel across the LED: cathode to the A node, anode to the K node
    s.append(diode_v(715, 440, BLK, False, "D", 688))
    s.append(poly([(715, 400), (715, 432)], BLK, 2))
    s.append(poly([(715, 451), (715, 480)], BLK, 2))
    s.append(dot(715, 400, ORA))
    s.append(dot(715, 480, BLK))
    # opto package
    s.append(box(730, 360, 200, 160, "#fafafa", INK, 2.4, 5))
    s.append(poly([(830, 366), (830, 514)], GRY, 2, "5 4"))
    s.append(txt(830, 384, "PC817", 13.5, anchor="middle", weight="bold"))
    s.append(txt(760, 447, "LED", 11.5, anchor="end", fill=MUTE))
    s.append(txt(830, 502, "5 kV isolation", 11, anchor="middle", fill=MUTE))
    # LED symbol
    s.append("<polygon points='768,432 792,432 780,452' fill='%s'/>" % ORA)
    s.append(poly([(766, 452), (794, 452)], ORA, 3))
    s.append(poly([(780, 410), (780, 432)], ORA, 2))
    s.append(poly([(780, 452), (780, 472)], BLK, 2))
    s.append(poly([(796, 428), (806, 418)], ORA, 1.8))
    s.append(poly([(798, 438), (808, 428)], ORA, 1.8))
    # transistor symbol
    s.append("<circle cx='884' cy='448' r='24' fill='none' stroke='%s' stroke-width='2'/>" % BLU)
    s.append(poly([(876, 434), (876, 462)], BLU, 3))
    s.append(poly([(876, 440), (896, 428)], BLU, 2))
    s.append(poly([(876, 456), (896, 468)], BLU, 2))
    s.append(poly([(896, 428), (896, 410)], BLU, 2))
    s.append(poly([(896, 468), (896, 486)], BLU, 2))
    s.append(pin(730, 400, ORA)); s.append(txt(736, 394, "A", 11.5, fill=ORA))
    s.append(pin(730, 480, BLK)); s.append(txt(736, 496, "K", 11.5, fill=BLK))
    s.append(pin(930, 400, BLU)); s.append(txt(922, 394, "C", 11.5, anchor="end", fill=BLU))
    s.append(pin(930, 480, BLU)); s.append(txt(922, 496, "E", 11.5, anchor="end", fill=BLU))
    s.append(poly([(896, 410), (896, 400), (930, 400)], BLU, 2))
    s.append(poly([(896, 486), (896, 480), (930, 480)], BLU, 2))
    s.append(poly([(780, 472), (780, 480), (730, 480)], BLK, 2))
    s.append(poly([(780, 410), (780, 400), (730, 400)], ORA, 2))
    # to Cerbo
    s.append(poly([(930, 400), (980, 400)], BLU))
    s.append(poly([(930, 480), (980, 480)], BLU))
    s.append(cerbo(980, 340, 200, "collector to DI n, emitter to GND"))
    s.append(bracket_h(596, 930, 1170, "≤ 12 in, 20 AWG + ferrules"))
    s.append(txt(30, 690, "I_F = (12 − 1.2 V) / 1 kΩ = 10.8 mA. The input needs only "
                          "0.33 mA, so CTR of 3.06 % suffices — a PC817 rank A gives 80 % minimum, "
                          "and V_CE(sat) stays under 0.2 V.", 12, fill=INK))
    s.append(txt(30, 708, "D is a 1N4148 anti-parallel across the LED: the PC817's reverse LED "
                          "rating is only 6 V, and the sensor's output polarity is not verified "
                          "until you meter it.", 12, fill=INK))
    s.append(txt(30, 726, "Leave the module's output-side VCC DISCONNECTED — an on-board pull-up "
                          "would drive 5 V into a 3.3 V input.", 12, fill=RED, weight="bold"))
    s.append(legend(960, 40))
    s.append("</g>")
    s.append(foot(862, W))
    s.append("</svg>")
    return "".join(s)

# ---------------------------------------------------------------- V2: relay
def v2():
    """Variant 2 — isolating signal relay."""
    W, H = 1280, 940
    s = [head(W, H, "Variant 2 — alternative: SEAFLO field switch + piezo + isolating relay",
              "Gives a true potential-free contact. Requires a signal relay with gold-clad "
              "contacts — a 10 A power relay is the wrong part here.")]
    s.append("<g transform='translate(0,70)'>")
    s.append(source_and_sensor(
        "SEAFLO electric-field switch",
        ["solid state, no moving parts", "trips ~50 mm, 3 s delay"],
        "OUT", 930))
    s.append(piezo(570))
    XC, XK = 700.0, 660.0
    s.append(dot(XC, YOUT, ORA))
    s.append(poly([(XC, YOUT), (XC, 400), (730, 400)], ORA))
    s.append(poly([(730, 480), (XK, 480), (XK, YNEG)], BLK))
    s.append(dot(XK, YNEG, BLK))
    # flyback D across the coil: cathode to COIL+, anode to COIL−
    s.append(diode_v(715, 440, BLK, False, "D", 688))
    s.append(poly([(715, 400), (715, 432)], BLK, 2))
    s.append(poly([(715, 451), (715, 480)], BLK, 2))
    s.append(dot(715, 400, ORA))
    s.append(dot(715, 480, BLK))
    s.append(box(730, 360, 200, 160, "#fafafa", INK, 2.4, 5))
    s.append(poly([(830, 366), (830, 514)], GRY, 2, "5 4"))
    s.append(txt(830, 384, "SIGNAL RELAY", 13.5, anchor="middle", weight="bold"))
    s.append(box(766, 418, 28, 56, "#ffffff", ORA, 2.4, 2))
    s.append(poly([(780, 400), (780, 418)], ORA, 2))
    s.append(poly([(780, 474), (780, 480)], BLK, 2))
    s.append(poly([(796, 446), (824, 446)], GRY, 2, "4 3"))
    s.append(poly([(856, 420), (856, 438)], BLU, 2))
    s.append(poly([(856, 438), (900, 468)], BLU, 2.4))
    s.append(dot(856, 438, BLU, 3.5))
    s.append(poly([(856, 420), (856, 400), (930, 400)], BLU, 2))
    s.append(poly([(900, 468), (900, 480), (930, 480)], BLU, 2))
    s.append(txt(830, 548, "12 V coil and 1 Form C contact — fully separate metal",
                 11.5, anchor="middle", fill=MUTE))
    s.append(pin(730, 400, ORA)); s.append(txt(736, 394, "COIL+", 11.5, fill=ORA))
    s.append(pin(730, 480, BLK)); s.append(txt(736, 496, "COIL−", 11.5, fill=BLK))
    s.append(pin(930, 400, BLU)); s.append(txt(922, 394, "COM", 11.5, anchor="end", fill=BLU))
    s.append(pin(930, 480, BLU)); s.append(txt(922, 496, "NO", 11.5, anchor="end", fill=BLU))
    s.append(poly([(930, 400), (980, 400)], BLU))
    s.append(poly([(930, 480), (980, 480)], BLU))
    s.append(cerbo(980, 340, 200, "contact polarity does not matter"))
    s.append(bracket_h(596, 930, 1170, "≤ 12 in, 20 AWG + ferrules"))
    s.append(txt(30, 690, "REQUIRED COIL SPEC:  12 V DC nominal, pull-in at ≤ 9 V, datasheet "
                          "max allowable coil voltage ≥ 16 V (a 120 %-of-rated coil maxes at "
                          "14.4 V)  ·  coil current ≤ 40 mA", 12, fill=INK))
    s.append(txt(30, 708, "REQUIRED CONTACT SPEC:  1 Form C, rated for low-level / dry-circuit "
                          "switching — minimum switching load ≤ 1 mA at ≤ 1 V DC, "
                          "gold-clad or bifurcated contacts.", 12, fill=INK))
    s.append(txt(30, 726, "The Cerbo input offers only 3.3 V at 0.33 mA. Silver-alloy 10 A power "
                          "contacts have no low-level rating and can film over while idle — "
                          "exactly this circuit's duty cycle.", 12, fill=RED))
    s.append(legend(960, 40))
    s.append("</g>")
    s.append(foot(862, W))
    s.append("</svg>")
    return "".join(s)

# ---------------------------------------------------------------- V3: mechanical DPDT float
def v3():
    """Variant 3 — mechanical DPDT float switch (counter-example)."""
    W, H = 1280, 940
    s = [head(W, H, "Variant 3 — counter-example: mechanical DPDT float switch, no isolation device",
              "Fewest active parts, but it spends the Run B length carrying a dry-circuit signal "
              "and gives up the SEAFLO kit's 3 s debounce.")]
    s.append("<g transform='translate(0,70)'>")
    # bilge band + rails
    s.append(box(200, 410, 300, 200, BILGE, "#bbdefb", 1.5, 6, "6 4"))
    s.append(txt(210, 601, "IN THE BILGE", 11.5, fill="#4a7fb5", weight="bold"))
    s.append(poly([(40, Y12), (X12DROP, Y12)], RED, 3))
    s.append(txt(30, Y12 - 52, "from unswitched, always-on fused distribution", 12.5, fill=MUTE))
    s.append(box(80, Y12 - 13, 56, 26, "#ffffff", RED, 2.2, 3))
    s.append(poly([(88, Y12), (98, Y12 - 6), (110, Y12 + 6), (120, Y12), (128, Y12)], RED, 2))
    s.append(txt(108, Y12 + 34, "FUSE 1 A", 13, anchor="middle", weight="bold", fill=RED))
    s.append(poly([(X12DROP, Y12), (X12DROP, 470), (240, 470)], RED))
    s.append(poly([(40, YNEG), (640, YNEG)], BLK, 3))
    s.append(txt(30, YNEG + 24, "to DC negative bus", 12.5, fill=MUTE))
    # float switch
    s.append(box(240, 440, 220, 120, "#ffffff", INK, 2.4, 5))
    s.append(txt(350, 470, "DPDT FLOAT SWITCH", 13.5, anchor="middle", weight="bold"))
    s.append(txt(350, 490, "two mechanically ganged,", 11.5, anchor="middle", fill=MUTE))
    s.append(txt(350, 505, "electrically separate poles", 11.5, anchor="middle", fill=MUTE))
    s.append(txt(350, 528, "no debounce — chatters in a seaway", 11, anchor="middle", fill=RED))
    s.append(pin(240, 470, RED)); s.append(txt(234, 458, "P1 COM", 11.5, anchor="end", fill=RED))
    s.append(pin(300, 440, ORA)); s.append(txt(292, 434, "P1 NO", 11.5, anchor="end", fill=ORA))
    s.append(pin(390, 440, BLU)); s.append(txt(398, 434, "P2 a", 11.5, fill=BLU))
    s.append(pin(440, 440, BLU)); s.append(txt(448, 434, "P2 b", 11.5, fill=BLU))
    # pole 1 -> piezo
    s.append(poly([(300, 440), (300, YOUT), (640, YOUT)], ORA, 3))
    s.append(txt(312, YOUT - 12, "switched +12 V", 12.5, fill=ORA))
    s.append(piezo(570))
    # pole 2 -> Cerbo, twisted pair
    s.append(poly([(390, 440), (390, 309)], BLU))
    s.append(hop_v(390, 300, BLU))
    s.append(poly([(390, 291), (390, 208), (950, 208), (950, 400), (980, 400)], BLU))
    s.append(poly([(440, 440), (440, 309)], BLU))
    s.append(hop_v(440, 300, BLU))
    s.append(poly([(440, 291), (440, 232), (918, 232), (918, 480), (980, 480)], BLU))
    s.append(txt(430, 196, "potential-free pair — run as its own twisted pair, "
                           "20–16 AWG, not bundled with the 12 V legs", 12, fill=BLU))
    s.append(cerbo(980, 340, 200, "true dry contact"))
    s.append(bracket_v(196, 300, 440, "", -1))
    s.append(txt(160, 336, "Run B: 1–3 m", 12, anchor="end", fill=MUTE))
    s.append(txt(160, 352, "4-cond 16 AWG", 12, anchor="end", fill=MUTE))
    s.append(bracket_h(Y12 - 24, 145, X12DROP, "Run A — 1–3 m", True))
    s.append(txt(30, 690, "TRADE-OFFS:  no relay, no optocoupler, no shared node between the "
                          "12 V and the signal side — the two poles are physically separate metal.",
                 12, fill=INK))
    s.append(txt(30, 708, "Against it: the P2 contact is the same dry-circuit problem as Variant 2 "
                          "(a float switch's contacts are silver, not gold), it has moving parts in a "
                          "dirty bilge,", 12, fill=INK))
    s.append(txt(30, 726, "and losing the 3 s delay means bilge slop toggles the alarm and the digital "
                          "input together. Use only if a DPDT float switch is already the plan.",
                 12, fill=INK))
    s.append(legend(960, 40))
    s.append("</g>")
    s.append(foot(862, W))
    s.append("</svg>")
    return "".join(s)

# ---------------------------------------------------------------- anti-pattern
def vx():
    """Anti-pattern — piezo hot leg tapped straight into the input."""
    W, H = 900, 420
    s = ["<?xml version='1.0' encoding='UTF-8'?>\n"
         "<svg xmlns='http://www.w3.org/2000/svg' width='%g' height='%g' viewBox='0 0 %g %g'>"
         % (W, H, W, H)]
    s.append(box(0, 0, W, H, "#ffffff", "#ffffff", 0, 0))
    s.append(txt(30, 38, "Do NOT do this", 20, weight="bold", fill=RED))
    s.append(txt(30, 60, "Tapping the piezo's hot leg straight into the digital input.",
                 13, fill=MUTE))
    y0, yn = 130.0, 330.0
    s.append(box(40, 100, 150, 70, "#ffffff", INK, 2.4, 5))
    s.append(txt(115, 128, "water switch", 12.5, anchor="middle", weight="bold"))
    s.append(txt(115, 146, "OUT", 12, anchor="middle", fill=ORA))
    s.append(poly([(190, y0), (600, y0)], ORA, 3))
    s.append(poly([(320, y0), (320, 220)], ORA))
    s.append(box(250, 220, 140, 60, "#ffffff", INK, 2.4, 5))
    s.append(txt(320, 256, "PIEZO", 12.5, anchor="middle", weight="bold"))
    s.append(poly([(320, 280), (320, yn), (40, yn)], BLK))
    s.append(txt(30, yn + 22, "negative", 12, fill=MUTE))
    s.append(poly([(600, y0), (660, y0), (660, 200), (700, 200)], ORA, 3))
    s.append(box(700, 160, 160, 130, "#ffffff", BLU, 2.4, 5))
    s.append(txt(780, 190, "CERBO GX", 13, anchor="middle", weight="bold", fill=BLU))
    s.append(txt(780, 210, "DI n", 12, anchor="middle", fill=BLU))
    s.append(txt(780, 236, "3.3 V logic", 11.5, anchor="middle", fill=MUTE))
    s.append(txt(780, 252, "10 kΩ to 3V3", 11.5, anchor="middle", fill=MUTE))
    s.append(txt(780, 274, "NOT isolated", 11.5, anchor="middle", fill=RED, weight="bold"))
    s.append(poly([(638, 187), (682, 143)], RED, 6))
    s.append(poly([(638, 143), (682, 187)], RED, 6))
    s.append(txt(30, 372, "12 V onto a 3.3 V input that is referenced to the Cerbo's own ground. "
                          "It reads as permanently triggered at best;", 12.5, fill=INK))
    s.append(txt(30, 392, "at worst any fault on the bilge run travels straight into the GX. "
                          "The isolation device is the whole point of this circuit.", 12.5, fill=INK))
    s.append("</svg>")
    return "".join(s)

out = "diagrams/electrical"
for name, fn in [("bilge-alarm-v1-optocoupler", v1), ("bilge-alarm-v2-relay", v2),
                 ("bilge-alarm-v3-float-dpdt", v3), ("bilge-alarm-antipattern", vx)]:
    p = os.path.join(out, name + ".svg")
    with open(p, "w") as f:
        f.write(fn())
    print("wrote", p)
