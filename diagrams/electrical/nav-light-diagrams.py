# -*- coding: utf-8 -*-
"""Generates the 12 V navigation-light controller diagrams (SVG)."""
import os

RED  = "#c62828"   # +12 V
BLK  = "#212121"   # negative
ORA  = "#e07000"   # switched 12 V (load side of the channel)
BLU  = "#1565c0"   # 3.3 V logic / ESP32 side
GRN  = "#2e7d32"   # manual bypass path
MUTE = "#5f6368"
INK  = "#1a1a1a"
FONT = "font-family='DejaVu Sans, Helvetica, Arial, sans-serif'"


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


def hop_h(x, y, color, w=2.6):
    """Semicircular hop where a horizontal wire crosses a vertical one."""
    return ("<path d='M %g,%g A 9,9 0 0 1 %g,%g' fill='none' stroke='%s' "
            "stroke-width='%g'/>" % (x - 9, y, x + 9, y, color, w))


def res_v(x, y, color, label, lx=None, size=12.5):
    """Vertical resistor centred on (x, y); label to the right unless lx given."""
    s = box(x - 11, y - 24, 22, 48, "#ffffff", color, 2.2, 2)
    if label:  # empty = the caller places its own label elsewhere
        s += (txt(x + 17, y + 5, label, size) if lx is None
              else txt(lx, y + 5, label, size, anchor="end"))
    return s


def fuse_v(x, y, color, label, lx=None, sub=None):
    """Vertical blade-fuse symbol centred on (x, y)."""
    s = [box(x - 15, y - 24, 30, 48, "#ffffff", color, 2.2, 3),
         poly([(x, y - 24), (x, y + 24)], color, 2.2)]
    tx, an = (x + 22, "start") if lx is None else (lx, "end")
    s.append(txt(tx, y + 1, label, 12.5, anchor=an, weight="bold"))
    if sub:
        s.append(txt(tx, y + 17, sub, 11.5, anchor=an, fill=MUTE))
    return "".join(s)


def fuse_h(x, y, color, label, above=True):
    """Horizontal blade-fuse symbol centred on (x, y)."""
    s = [box(x - 24, y - 15, 48, 30, "#ffffff", color, 2.2, 3),
         poly([(x - 24, y), (x + 24, y)], color, 2.2)]
    if label:  # the block sheet's fuse rows are named by their column header
        s.append(txt(x, y - 22 if above else y + 32, label, 12,
                     anchor="middle", weight="bold"))
    return "".join(s)


def lamp(x, y, color, r=32):
    """Lamp symbol: circle with an X."""
    k = r * 0.707
    return ("<circle cx='%g' cy='%g' r='%g' fill='#ffffff' stroke='%s' "
            "stroke-width='2.4'/>" % (x, y, r, color)
            + poly([(x - k, y - k), (x + k, y + k)], color, 2.2)
            + poly([(x - k, y + k), (x + k, y - k)], color, 2.2))


def zener_v(x, y, color, label):
    """Zener centred on (x, y), cathode up (reverse-biased gate-source clamp)."""
    s = ["<polygon points='%g,%g %g,%g %g,%g' fill='%s'/>"
         % (x - 11, y + 11, x + 11, y + 11, x, y - 8, color),
         poly([(x - 13, y - 8), (x + 13, y - 8)], color, 3),
         poly([(x - 13, y - 8), (x - 17, y - 14)], color, 3),
         poly([(x + 13, y - 8), (x + 17, y - 2)], color, 3),
         txt(x - 20, y + 5, label, 12.5, anchor="end")]
    return "".join(s)


def pmos(x, y, color):
    """P-channel enhancement MOSFET; gate lead exits left, source up, drain down.

    Returns the symbol only -- the caller draws the leads beyond x+30.
    """
    s = [poly([(x - 16, y - 24), (x - 16, y + 24)], color),          # gate bar
         poly([(x, y - 24), (x, y - 10)], color),                    # channel
         poly([(x, y - 6), (x, y + 6)], color),
         poly([(x, y + 10), (x, y + 24)], color),
         poly([(x, y - 18), (x + 30, y - 18), (x + 30, y - 30)], color),  # source
         poly([(x, y + 18), (x + 30, y + 18), (x + 30, y + 30)], color),  # drain
         poly([(x, y), (x + 30, y), (x + 30, y - 18)], color)]       # body to source
    # substrate arrow, pointing away from the channel (P-channel)
    s.append("<polygon points='%g,%g %g,%g %g,%g' fill='%s'/>"
             % (x + 8, y - 6, x + 8, y + 6, x + 20, y, color))
    return "".join(s)


def head(w, h, title, subtitle):
    """SVG document opening: canvas, title and subtitle."""
    return ("<?xml version='1.0' encoding='UTF-8'?>\n"
            "<svg xmlns='http://www.w3.org/2000/svg' width='%g' height='%g' "
            "viewBox='0 0 %g %g'>" % (w, h, w, h)
            + box(0, 0, w, h, "#ffffff", "#ffffff", 0, 0)
            + txt(30, 40, title, 21, weight="bold")
            + txt(30, 63, subtitle, 13.5, fill=MUTE))


def legend(x, y, items):
    """Wire-colour legend starting at (x, y)."""
    s = []
    for i, (c, lab) in enumerate(items):
        yy = y + i * 19
        s.append(poly([(x, yy), (x + 26, yy)], c, 3.4))
        s.append(txt(x + 33, yy + 4.5, lab, 11.5, fill=MUTE))
    return "".join(s)


LEG = [(RED, "+12 V, from the panel"), (ORA, "switched 12 V to the fixture"),
       (GRN, "manual bypass (blade fuse)"), (BLU, "3.3 V logic"),
       (BLK, "negative / common ground")]

CHANNELS = [("CH1", "Masthead, leg 1", "mode-select"),
            ("CH2", "Masthead, leg 2", "mode-select"),
            ("CH3", "Masthead, leg 3", "mode-select"),
            ("CH4", "Sidelights", "port + stbd, one channel"),
            ("CH5", "Stern light", "white 135°"),
            ("CH6", "Steaming light", "forward white 225°, under power"),
            ("CH7", "Spreader lights", "deck work light — not a nav light")]


# ------------------------------------------------------------------ block sheet
def block():
    """System block diagram: seven channels, both fuse blocks, one ESP32."""
    W, H = 1250, 1060
    XBUS, XGND = 230.0, 1060.0
    ROWS = [210.0 + 100.0 * i for i in range(7)]
    s = [head(W, H, "12 V navigation-light controller — system block",
              "Seven identical channels. Each is an opto-driven high-side "
              "P-MOSFET, paralleled by a manual blade-fuse bypass.")]

    # +12 V feed and bus
    s.append(poly([(60, 150), (XBUS, 150)], RED, 3.4))
    s.append("<polygon points='%g,%g %g,%g %g,%g' fill='%s'/>"
             % (200, 143, 200, 157, 216, 150, RED))
    s.append(txt(60, 133, "to panel — +12 V main run, protected at the source",
                 12.5, fill=MUTE))
    s.append(poly([(XBUS, 150), (XBUS, 900)], RED, 5))

    # negative bus
    s.append(poly([(XGND, 190), (XGND, 960)], BLK, 5))
    s.append(txt(XGND + 10, 180, "to negative bus", 12, fill=BLK, weight="bold"))

    # ESP32
    s.append(box(40, 190, 160, 660, "#f3f7fd", BLU, 2.4, 6))
    s.append(txt(120, 222, "ESP32", 15, anchor="middle", weight="bold", fill=BLU))
    s.append(txt(120, 244, "7 × GPIO out", 12, anchor="middle", fill=MUTE))
    s.append(txt(120, 262, "each with a", 11.5, anchor="middle", fill=MUTE))
    s.append(txt(120, 278, "10 kΩ pulldown", 11.5, anchor="middle", fill=MUTE))
    s.append(txt(120, 810, "GPIO low or", 11.5, anchor="middle", fill=MUTE))
    s.append(txt(120, 826, "unpowered =", 11.5, anchor="middle", fill=MUTE))
    s.append(txt(120, 842, "all lights off", 11.5, anchor="middle",
                 fill=RED, weight="bold"))

    # ESP32 supply tap off the bus
    s.append(poly([(XBUS, 900), (140, 900), (140, 930)], RED))
    s.append(dot(XBUS, 900, RED))
    s.append(fuse_h(178, 900, RED, "F-LOGIC 1 A", above=True))
    s.append(box(60, 930, 140, 46, "#ffffff", RED, 2.2, 4))
    s.append(txt(130, 958, "12 V → 5 V buck", 12, anchor="middle"))
    s.append(poly([(80, 930), (80, 850)], RED))

    # ESP32 / board ground
    s.append(poly([(170, 976), (170, 1006), (XGND, 1006), (XGND, 960)], BLK))

    for i, y in enumerate(ROWS):
        cid, name, sub = CHANNELS[i]
        # electronic path: bus -> switch block -> merge
        s.append(dot(XBUS, y - 27, RED))
        s.append(poly([(XBUS, y - 27), (320, y - 27)], RED))
        s.append(box(320, y - 50, 150, 42, "#ffffff", ORA, 2.4, 5))
        s.append(txt(395, y - 32, "opto → P-FET", 12.5, anchor="middle"))
        s.append(txt(395, y - 16, cid, 11.5, anchor="middle", fill=MUTE))
        s.append(poly([(470, y - 27), (600, y - 27)], ORA))

        # control line from the ESP32, hopping the +12 bus
        s.append(poly([(200, y - 4), (XBUS - 9, y - 4)], BLU, 2.2, "6 4"))
        s.append(hop_h(XBUS, y - 4, BLU, 2.2))
        s.append(poly([(XBUS + 9, y - 4), (395, y - 4), (395, y - 8)], BLU, 2.2, "6 4"))

        # manual bypass path: bus -> blade fuse -> merge
        s.append(dot(XBUS, y + 27, GRN))
        s.append(poly([(XBUS, y + 27), (506, y + 27)], GRN))
        s.append(fuse_h(530, y + 27, GRN, "", above=False))
        s.append(poly([(554, y + 27), (600, y + 27)], GRN))

        # merge, branch fuse, load
        s.append(poly([(600, y - 27), (600, y + 27)], ORA))
        s.append(dot(600, y - 27, ORA))
        s.append(dot(600, y + 27, ORA))
        s.append(poly([(600, y), (656, y)], ORA))
        s.append(fuse_h(680, y, ORA, ""))
        s.append(poly([(704, y), (780, y)], ORA))
        s.append(box(780, y - 24, 210, 48, "#ffffff", ORA, 2.4, 5))
        s.append(txt(885, y - 3, name, 13, anchor="middle", weight="bold"))
        s.append(txt(885, y + 15, sub, 11.5, anchor="middle", fill=MUTE))
        s.append(poly([(990, y), (XGND, y)], BLK))
        s.append(dot(XGND, y, BLK))

    # fuse-block groupings
    s.append(box(496, 178, 68, 680, "none", GRN, 2, 8, "7 5"))
    s.append(txt(530, 168, "BYPASS BLOCK", 12, anchor="middle",
                 weight="bold", fill=GRN))
    s.append(txt(530, 876, "normally EMPTY", 11.5, anchor="middle", fill=GRN))
    s.append(txt(530, 892, "fuse in = light on,", 11.5, anchor="middle", fill=MUTE))
    s.append(txt(530, 908, "ESP32 overridden", 11.5, anchor="middle", fill=MUTE))
    s.append(box(648, 178, 64, 680, "none", ORA, 2, 8, "7 5"))
    s.append(txt(680, 168, "BRANCH FUSES", 12, anchor="middle",
                 weight="bold", fill=ORA))
    s.append(txt(680, 876, "always fitted", 11.5, anchor="middle", fill=ORA))
    s.append(txt(680, 892, "protects the run to", 11.5, anchor="middle", fill=MUTE))
    s.append(txt(680, 908, "the fixture, both paths", 11.5, anchor="middle", fill=MUTE))

    s.append(box(770, 180, 232, 262, "none", ORA, 2, 8, "7 5"))
    s.append(txt(885, 456, "one fixture, one cable", 11.5, anchor="middle",
                 fill=ORA, weight="bold"))
    s.append(txt(885, 472, "energise one leg at a time", 11.5, anchor="middle",
                 fill=ORA))
    s.append(legend(800, 890, LEG))
    s.append("</svg>")
    return "".join(s)


# ---------------------------------------------------------------- channel sheet
def channel():
    """One channel in detail: gate network, optocoupler, both current paths."""
    W, H = 1080, 920
    Y12, YGND, YOUT = 150.0, 830.0, 360.0
    s = [head(W, H, "One channel — opto-driven high-side P-MOSFET, "
                    "with manual bypass",
              "Repeat seven times. Values are working stand-ins; only the "
              "MOSFET and the two fuses scale with the load.")]

    # rails
    s.append(poly([(30, Y12), (1030, Y12)], RED, 3.4))
    s.append(txt(30, Y12 - 18, "+12 V from the main run", 12.5, fill=MUTE))
    s.append(poly([(30, YGND), (1030, YGND)], BLK, 3.4))
    s.append(txt(30, YGND + 22, "to negative bus — one bonding point for the "
                                "board and the fixtures", 12.5, fill=MUTE))
    s.append(poly([(30, YGND + 40), (1030, YGND + 40)], "#dddddd", 1.5))
    s.append(txt(30, YGND + 62, "R1 holds Q1's gate at the source rail, so OFF is the "
                                "default at every point in the ESP32's boot — and the state "
                                "it falls back to if the ESP32 dies.", 12.5))
    s.append(txt(30, YGND + 80, "R4 covers the window before firmware drives the pin, when "
                                "the GPIO is high-impedance. FB is then the only way to get "
                                "the light back — deliberately manual.", 12.5))

    # ---- power path: MOSFET
    s.append(pmos(490, 250, ORA))
    s.append(poly([(520, 220), (520, Y12)], RED))
    s.append(poly([(520, 280), (520, YOUT)], ORA))
    s.append(dot(520, Y12, RED))
    s.append(txt(556, 236, "Q1", 14, weight="bold"))
    s.append(txt(556, 254, "P-channel MOSFET", 12))
    s.append(txt(556, 270, "≥ 60 V, low R_DS(on)", 11.5, fill=MUTE))

    # ---- gate network
    s.append(poly([(474, 250), (400, 250)], ORA))
    s.append(res_v(400, 200, ORA, "R1  100 kΩ"))
    s.append(poly([(400, Y12), (400, 176)], RED))
    s.append(poly([(400, 224), (400, 306)], ORA))
    s.append(dot(400, Y12, RED))
    s.append(dot(400, 250, ORA))
    s.append(zener_v(320, 200, ORA, "D1  15 V"))
    s.append(poly([(320, Y12), (320, 188)], RED))
    s.append(poly([(320, 211), (320, 250), (400, 250)], ORA))
    s.append(dot(320, Y12, RED))
    s.append(txt(220, 232, "V_GS clamp", 11.5, anchor="end", fill=MUTE))
    s.append(res_v(400, 330, ORA, "R2  22 kΩ"))
    s.append(txt(417, 349, "V_GS ≈ −9.8 V when on", 11.5, fill=MUTE))
    s.append(poly([(400, 354), (400, 400), (660, 400), (660, 460), (600, 460)], ORA))

    # ---- optocoupler
    s.append(box(340, 430, 260, 140, "#fbfbfb", INK, 2.4, 6))
    s.append(poly([(470, 430), (470, 570)], MUTE, 2, "7 5"))
    s.append(txt(470, 418, "U1   PC817 optocoupler", 13, anchor="middle",
                 weight="bold"))
    s.append(txt(405, 496, "LED", 12, anchor="middle", fill=BLU))
    s.append(txt(405, 514, "3.3 V side", 11, anchor="middle", fill=MUTE))
    s.append(txt(537, 496, "photo-", 12, anchor="middle", fill=ORA))
    s.append(txt(537, 512, "transistor", 12, anchor="middle", fill=ORA))
    s.append(txt(537, 530, "12 V side", 11, anchor="middle", fill=MUTE))
    for px, py, lab, col, an in [(340, 470, "A", BLU, "start"),
                                 (340, 530, "K", BLU, "start"),
                                 (600, 460, "C", ORA, "end"),
                                 (600, 540, "E", ORA, "end")]:
        s.append(txt(px + (10 if an == "start" else -10), py + 4, lab, 11.5,
                     anchor=an, fill=col))
    s.append(poly([(600, 540), (690, 540), (690, YGND)], ORA))
    s.append(dot(690, YGND, BLK))

    # ---- ESP32 drive
    s.append(poly([(340, 470), (200, 470), (200, 576)], BLU))
    s.append(res_v(200, 600, BLU, "R3  220 Ω"))
    s.append(txt(217, 622, "≈ 9.5 mA", 11.5, fill=MUTE))
    s.append(poly([(200, 624), (200, 650)], BLU))
    s.append(dot(200, 640, BLU))
    s.append(poly([(200, 640), (260, 640), (260, 666)], BLU))
    s.append(res_v(260, 690, BLU, "", lx=None))
    s.append(txt(326, 686, "R4  10 kΩ", 12.5))
    s.append(txt(326, 706, "holds the LED off while", 11.5, fill=MUTE))
    s.append(txt(326, 722, "the ESP32 boots or resets", 11.5, fill=MUTE))
    s.append(poly([(260, 714), (260, YGND)], BLU))
    s.append(dot(260, YGND, BLK))
    s.append(poly([(340, 530), (310, 530), (310, YGND)], BLU))
    s.append(dot(310, YGND, BLK))

    s.append(box(70, 650, 180, 160, "#f3f7fd", BLU, 2.4, 6))
    s.append(txt(160, 690, "ESP32", 15, anchor="middle", weight="bold", fill=BLU))
    s.append(txt(160, 712, "one GPIO", 12, anchor="middle", fill=MUTE))
    s.append(txt(160, 730, "per channel", 12, anchor="middle", fill=MUTE))
    s.append(txt(160, 756, "HIGH = light on", 11.5, anchor="middle", fill=INK))
    s.append(poly([(250, 780), (310, 780)], BLK))
    s.append(dot(310, 780, BLK))

    # ---- logic supply
    s.append(box(40, 500, 120, 90, "#ffffff", RED, 2.2, 5))
    s.append(txt(100, 538, "12 V → 5 V", 12.5, anchor="middle"))
    s.append(txt(100, 556, "buck", 12.5, anchor="middle"))
    s.append(txt(100, 574, "shared ground", 11, anchor="middle", fill=MUTE))
    s.append(poly([(100, 500), (100, 444)], RED))
    s.append(fuse_v(100, 420, RED, "F-LOGIC", lx=78, sub="1 A"))
    s.append(poly([(100, 396), (100, Y12)], RED))
    s.append(dot(100, Y12, RED))
    s.append(poly([(140, 590), (140, 650)], RED))
    s.append(poly([(55, 590), (55, YGND)], BLK))
    s.append(dot(55, YGND, BLK))

    # ---- manual bypass
    s.append(poly([(720, Y12), (720, 226)], GRN))
    s.append(dot(720, Y12, RED))
    s.append(fuse_v(720, 250, GRN, "FB — bypass",
                    sub="normally EMPTY"))
    s.append(poly([(720, 274), (720, YOUT)], GRN))
    s.append(txt(742, 300, "fuse in = light on regardless", 11.5, fill=MUTE))
    s.append(txt(742, 316, "of the ESP32; fuse out =", 11.5, fill=MUTE))
    s.append(txt(742, 332, "ESP32 has control", 11.5, fill=MUTE))

    # ---- output node, branch fuse, fixture
    s.append(poly([(520, YOUT), (900, YOUT)], ORA))
    s.append(dot(520, YOUT, ORA))
    s.append(dot(720, YOUT, ORA))
    s.append(poly([(900, YOUT), (900, 426)], ORA))
    s.append(fuse_v(900, 450, ORA, "F1 — branch", lx=878,
                    sub="always fitted"))
    s.append(poly([(900, 474), (900, 538)], ORA))
    s.append(lamp(900, 570, ORA, 32))
    s.append(poly([(900, 602), (900, YGND)], BLK))
    s.append(dot(900, YGND, BLK))
    s.append(txt(944, 566, "fixture", 12.5))
    s.append(txt(944, 584, "at the mast", 11.5, fill=MUTE))

    s.append(legend(390, 734, LEG))
    s.append("</svg>")
    return "".join(s)


# --------------------------------------------------------------- feedback sheet
def feedback():
    """Three options for telling the ESP32 what the channel is actually doing."""
    W, H = 1240, 620
    s = [head(W, H, "Feedback options — what the ESP32 knows about the channel",
              "One channel shown. Option A is v1; B and C are the upgrades the "
              "board should leave footprints for.")]
    panels = [
        (30, "A — command only", "v1", MUTE,
         ["No parts. The ESP32 knows what it commanded",
          "and nothing else. A blown lamp, a blown branch",
          "fuse, or a bypass fuse someone left in all look",
          "identical from the helm: exactly like normal."]),
        (425, "B — load-present sense", "2 resistors/ch", BLU,
         ["Reads the voltage at the load side of F1. Tells",
          "apart: commanded-on and lit; commanded-off but",
          "energised (bypass fuse left in); commanded-on",
          "but dead (open lamp or blown branch fuse)."]),
        (820, "C — current sense", "1 IC + shunt/ch", GRN,
         ["Actual amps per channel. Adds what B cannot see:",
          "a partly-failed LED array, a fixture drawing high",
          "before it fails, and a real power budget. Needs",
          "calibration and I²C address planning."]),
    ]
    for px, title, cost, col, notes in panels:
        s.append(box(px, 90, 380, 452, "#ffffff", "#dddddd", 2, 8))
        s.append(txt(px + 20, 122, title, 14.5, weight="bold", fill=col))
        s.append(txt(px + 360, 122, cost, 12, anchor="end", fill=MUTE))
        s.append(poly([(px + 20, 138), (px + 360, 138)], "#eeeeee", 1.6))
        # the shared output leg
        s.append(txt(px + 20, 178, "output node (Q1 ∥ bypass fuse)", 11.5, fill=MUTE))
        s.append(poly([(px + 20, 200), (px + 330, 200)], ORA))
        s.append("<polygon points='%g,%g %g,%g %g,%g' fill='%s'/>"
                 % (px + 330, 193, px + 330, 207, px + 348, 200, ORA))
        s.append(txt(px + 300, 186, "to F1 → fixture", 11.5, anchor="end", fill=MUTE))
        s.append(poly([(px + 20, 420), (px + 348, 420)], BLK, 2.6))
        s.append(txt(px + 20, 440, "negative", 11, fill=MUTE))
        for i, n in enumerate(notes):
            s.append(txt(px + 20, 465 + i * 17, n, 11.5, fill=INK))

    # B: divider to an ADC
    px = 425
    s.append(dot(px + 150, 200, ORA))
    s.append(poly([(px + 150, 200), (px + 150, 236)], ORA))
    s.append(res_v(px + 150, 260, BLU, "100 kΩ"))
    s.append(poly([(px + 150, 284), (px + 150, 336)], BLU))
    s.append(dot(px + 150, 310, BLU))
    s.append(res_v(px + 150, 360, BLU, "22 kΩ"))
    s.append(poly([(px + 150, 384), (px + 150, 420)], BLK))
    s.append(dot(px + 150, 420, BLK))
    s.append(poly([(px + 150, 310), (px + 230, 310)], BLU))
    s.append(box(px + 230, 282, 120, 56, "#f3f7fd", BLU, 2.2, 5))
    s.append(txt(px + 290, 306, "ESP32", 12.5, anchor="middle", weight="bold", fill=BLU))
    s.append(txt(px + 290, 324, "ADC in", 11.5, anchor="middle", fill=MUTE))
    s.append(txt(px + 20, 260, "12 V →", 11.5, fill=MUTE))
    s.append(txt(px + 20, 276, "2.2 V", 11.5, fill=MUTE))

    # C: shunt + high-side monitor
    px = 820
    s.append(box(px + 126, 186, 48, 28, "#ffffff", GRN, 2.2, 3))
    s.append(txt(px + 150, 240, "R_S", 12, anchor="middle", weight="bold", fill=GRN))
    s.append(poly([(px + 120, 200), (px + 120, 250)], GRN, 2.2))
    s.append(poly([(px + 180, 200), (px + 180, 250)], GRN, 2.2))
    s.append(dot(px + 120, 200, GRN, 3.6))
    s.append(dot(px + 180, 200, GRN, 3.6))
    s.append(box(px + 80, 250, 160, 66, "#f1f8f1", GRN, 2.2, 5))
    s.append(txt(px + 160, 276, "INA226", 12.5, anchor="middle", weight="bold", fill=GRN))
    s.append(txt(px + 160, 296, "high-side monitor", 11, anchor="middle", fill=MUTE))
    s.append(poly([(px + 160, 316), (px + 160, 420)], BLK))
    s.append(dot(px + 160, 420, BLK))
    s.append(poly([(px + 240, 283), (px + 280, 283)], BLU, 2.2, "6 4"))
    s.append(box(px + 280, 255, 70, 56, "#f3f7fd", BLU, 2.2, 5))
    s.append(txt(px + 315, 279, "ESP32", 12, anchor="middle", weight="bold", fill=BLU))
    s.append(txt(px + 315, 297, "I²C", 11.5, anchor="middle", fill=MUTE))

    s.append("</svg>")
    return "".join(s)


out = "diagrams/electrical"
for name, fn in [("nav-light-block", block), ("nav-light-channel", channel),
                 ("nav-light-feedback", feedback)]:
    p = os.path.join(out, name + ".svg")
    with open(p, "w") as f:
        f.write(fn())
    print("wrote", p)
