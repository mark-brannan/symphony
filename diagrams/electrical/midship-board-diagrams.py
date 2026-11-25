# -*- coding: utf-8 -*-
"""Generates the midship ESP32 board diagrams (SVG).

Drawing helpers and the colour convention come from nav-light-diagrams.py.
"""
import importlib.util
import os

_here = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "nav_light_diagrams", os.path.join(_here, "nav-light-diagrams.py"))
nl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(nl)

RED, BLK, ORA, BLU, GRN, MUTE, INK = (nl.RED, nl.BLK, nl.ORA, nl.BLU, nl.GRN,
                                      nl.MUTE, nl.INK)
txt, poly, box, dot, hop_h = nl.txt, nl.poly, nl.box, nl.dot, nl.hop_h
res_v, fuse_v, fuse_h, pmos = nl.res_v, nl.fuse_v, nl.fuse_h, nl.pmos
head, legend = nl.head, nl.legend

LEG = [(RED, "+12 V (lighting feed or always-on bus)"),
       (ORA, "switched 12 V to the load"),
       (GRN, "Kelvin sense pair / VBUS tap"),
       (BLU, "3.3 V logic / I²C"),
       (BLK, "negative / common ground")]

# (id, name, sub) -- CH5 stern is not on this board
LIGHTS = [("CH1", "Masthead, leg 1", "mode-select"),
          ("CH2", "Masthead, leg 2", "mode-select"),
          ("CH3", "Masthead, leg 3", "mode-select"),
          ("CH4", "Sidelights", "port + stbd, one channel"),
          ("CH6", "Steaming light", "forward white 225°, under power"),
          ("CH7", "Spreader lights", "deck work light — not a nav light")]


def diode_v(x, y, color, label):
    """Diode centred on (x, y), cathode up; label to the right."""
    return ("<polygon points='%g,%g %g,%g %g,%g' fill='%s'/>"
            % (x - 11, y + 11, x + 11, y + 11, x, y - 8, color)
            + poly([(x - 13, y - 8), (x + 13, y - 8)], color, 3)
            + txt(x + 20, y + 5, label, 12.5))


# ------------------------------------------------------------------ block sheet
def block():
    """System block: light channels, the dry-bilge pump channel, four INA226s."""
    W, H = 1420, 1090
    XBUS, XGND = 230.0, 1100.0
    ROWS = [210.0 + 90.0 * i for i in range(6)]
    Y8 = 790.0
    s = [head(W, H, "Midship ESP32 board — system block",
              "Six light channels and the dry-bilge pump switched by opto-driven "
              "high-side P-MOSFETs; four INA226 monitors on I²C for the pumps.")]

    # lighting feed bus and always-on bus
    s.append(poly([(60, 150), (XBUS, 150)], RED, 3.4))
    s.append("<polygon points='%g,%g %g,%g %g,%g' fill='%s'/>"
             % (200, 143, 200, 157, 216, 150, RED))
    s.append(txt(60, 133, "to the lighting feed — +12 V", 12.5, fill=MUTE))
    s.append(poly([(XBUS, 150), (XBUS, 700)], RED, 5))
    s.append(poly([(XBUS, 735), (XBUS, 900)], RED, 5))
    s.append(poly([(XBUS, 1010), (XBUS, 900)], RED, 3.4))
    s.append("<polygon points='%g,%g %g,%g %g,%g' fill='%s'/>"
             % (XBUS - 7, 936, XBUS + 7, 936, XBUS, 920, RED))
    s.append(txt(XBUS + 14, 1004, "to the always-on bus — +12 V", 12.5, fill=MUTE))
    s.append(poly([(XGND, 190), (XGND, 840)], BLK, 5))
    s.append(txt(XGND + 10, 180, "to negative bus", 12, fill=BLK, weight="bold"))

    # ESP32 and its supply, from the always-on bus so monitoring outlives the panel
    s.append(box(40, 190, 160, 660, "#f3f7fd", BLU, 2.4, 6))
    s.append(txt(120, 222, "ESP32", 15, anchor="middle", weight="bold", fill=BLU))
    s.append(txt(120, 244, "7 × GPIO out", 12, anchor="middle", fill=MUTE))
    s.append(txt(120, 262, "each with a", 11.5, anchor="middle", fill=MUTE))
    s.append(txt(120, 278, "10 kΩ pulldown", 11.5, anchor="middle", fill=MUTE))
    s.append(txt(120, 810, "GPIO low or", 11.5, anchor="middle", fill=MUTE))
    s.append(txt(120, 826, "unpowered = all", 11.5, anchor="middle", fill=MUTE))
    s.append(txt(120, 842, "channels off", 11.5, anchor="middle",
                 fill=RED, weight="bold"))
    s.append(poly([(XBUS, 900), (140, 900), (140, 930)], RED))
    s.append(nl.dot(XBUS, 900, RED))
    s.append(fuse_h(178, 900, RED, "F-LOGIC 1 A", above=True))
    s.append(box(60, 930, 140, 46, "#ffffff", RED, 2.2, 4))
    s.append(txt(130, 958, "12 V → 5 V buck", 12, anchor="middle"))
    s.append(poly([(80, 930), (80, 850)], RED))
    s.append(txt(60, 996, "logic on the always-on bus:", 11.5, fill=MUTE))
    s.append(txt(60, 1012, "monitoring survives the", 11.5, fill=MUTE))
    s.append(txt(60, 1028, "house panel being off", 11.5, fill=MUTE))

    def row(y, cid, name, sub, bypass, fuse_lab, load_col):
        s.append(dot(XBUS, y - 27, RED))
        s.append(poly([(XBUS, y - 27), (320, y - 27)], RED))
        s.append(box(320, y - 50, 150, 42, "#ffffff", ORA, 2.4, 5))
        s.append(txt(395, y - 32, "opto → P-FET" if bypass else "opto → Q8",
                     12.5, anchor="middle"))
        s.append(txt(395, y - 16, cid, 11.5, anchor="middle", fill=MUTE))
        s.append(poly([(470, y - 27), (600, y - 27)], ORA))
        s.append(poly([(200, y - 4), (XBUS - 9, y - 4)], BLU, 2.2, "6 4"))
        s.append(hop_h(XBUS, y - 4, BLU, 2.2))
        s.append(poly([(XBUS + 9, y - 4), (395, y - 4), (395, y - 8)], BLU, 2.2, "6 4"))
        if bypass:
            s.append(dot(XBUS, y + 27, GRN))
            s.append(poly([(XBUS, y + 27), (506, y + 27)], GRN))
            s.append(fuse_h(530, y + 27, GRN, "", above=False))
            s.append(poly([(554, y + 27), (600, y + 27)], GRN))
            s.append(poly([(600, y - 27), (600, y + 27)], ORA))
            s.append(dot(600, y + 27, ORA))
        else:
            s.append(txt(395, y + 30, "no bypass fuse", 11.5,
                         anchor="middle", fill=MUTE))
            s.append(poly([(600, y - 27), (600, y)], ORA))
        s.append(dot(600, y - 27, ORA))
        s.append(poly([(600, y), (656, y)], ORA))
        s.append(fuse_h(680, y, ORA, ""))
        s.append(txt(680, y + 32, fuse_lab, 11.5, anchor="middle", fill=MUTE))
        s.append(poly([(704, y), (780, y)], ORA))
        s.append(box(780, y - 24, 210, 48, "#ffffff", load_col, 2.4, 5))
        s.append(txt(885, y - 3, name, 13, anchor="middle", weight="bold"))
        s.append(txt(885, y + 15, sub, 11.5, anchor="middle", fill=MUTE))

    for y, (cid, name, sub) in zip(ROWS, LIGHTS):
        row(y, cid, name, sub, True, "", ORA)
        s.append(poly([(990, y), (XGND, y)], BLK))
        s.append(dot(XGND, y, BLK))

    # CH8: dry-bilge pump, always-on bus, no bypass, S3 in the return
    row(Y8, "CH8", "P3 dry-bilge pump", "Amarine FLO-2202, 3.5 A max", False,
        "F8 4 A", ORA)
    s.append(poly([(990, Y8), (1020, Y8)], BLK))
    s.append(box(1020, Y8 - 12, 36, 24, "#f1f8f1", GRN, 2.2, 3))
    s.append(txt(1038, Y8 - 20, "S3", 12, anchor="middle", weight="bold", fill=GRN))
    s.append(txt(1038, Y8 + 32, "on the board", 11, anchor="middle", fill=MUTE))
    s.append(poly([(1056, Y8), (XGND, Y8)], BLK))
    s.append(dot(XGND, Y8, BLK))

    # the masthead group
    s.append(box(770, 180, 232, 244, "none", ORA, 2, 8, "7 5"))
    s.append(txt(885, 440, "one fixture, one cable — one leg at a time", 11.5,
                 anchor="middle", fill=ORA, weight="bold"))
    s.append(txt(320, 148, "CH5 stern light is not on this board",
                 11.5, fill=MUTE))
    s.append(box(496, 178, 68, 536, "none", GRN, 2, 8, "7 5"))
    s.append(txt(530, 170, "BYPASS BLOCK", 11.5, anchor="middle",
                 weight="bold", fill=GRN))

    # I²C bus to four INA226s
    YB = 845.0
    s.append(poly([(200, YB), (XBUS - 9, YB)], BLU, 2.2, "6 4"))
    s.append(hop_h(XBUS, YB, BLU, 2.2))
    s.append(poly([(XBUS + 9, YB), (1075, YB)], BLU, 2.2, "6 4"))
    s.append(txt(260, YB - 8, "I²C", 12, fill=BLU, weight="bold"))
    for x, addr, pump, shunt in [(400, "0x40", "P1 volts + amps", "S1 external, in P1's negative"),
                                 (625, "0x41", "P2 volts + amps", "S2 external, in P2's negative"),
                                 (850, "0x44", "P3 volts + amps", "S3 on the board, in P3's return"),
                                 (1075, "0x45", "P4 volts + amps", "S4 external, in P4's negative")]:
        s.append(poly([(x, YB), (x, 880)], BLU, 2.2, "6 4"))
        s.append(dot(x, YB, BLU))
        s.append(box(x - 105, 880, 210, 72, "#f1f8f1", GRN, 2.2, 5))
        s.append(txt(x, 902, "INA226  " + addr, 12.5, anchor="middle",
                     weight="bold", fill=GRN))
        s.append(txt(x, 920, pump, 11.5, anchor="middle"))
        s.append(txt(x, 938, shunt, 10.5, anchor="middle", fill=MUTE))
    s.append(txt(1200, 897, "P1–P3 run from the always-on", 11.5, fill=MUTE))
    s.append(txt(1200, 913, "bus; P4's feed is open.", 11.5, fill=MUTE))
    s.append(txt(1200, 929, "Firmware derives running", 11.5, fill=MUTE))
    s.append(txt(1200, 945, "from amps.", 11.5, fill=MUTE))

    s.append(legend(560, 985, LEG))
    s.append("</svg>")
    return "".join(s)


# --------------------------------------------------------------- pump sensing
def sensing():
    """Four pump columns: negative-lead shunts, Kelvin pairs, Q8 and D8 on P3."""
    W, H = 1740, 940
    TOP, NEG = 140.0, 780.0
    s = [head(W, H, "Pump sensing — low-side shunts, Kelvin pairs to four INA226s",
              "P1–P3 on the always-on bus; P4's feed is open. The negative lead "
              "carries every operating mode, so one shunt per pump sees them all.")]
    s.append(poly([(60, TOP), (1690, TOP)], RED, 5))
    s.append(txt(60, TOP - 14, "+12 V always-on bus", 12.5, fill=RED, weight="bold"))
    s.append(poly([(60, NEG), (1690, NEG)], BLK, 5))
    s.append(txt(60, NEG + 22, "to negative bus", 12.5, fill=BLK, weight="bold"))

    cols = [(230, "P1", "SEAFLO 06-series", "1100 GPH automatic bilge", "6.0 A max",
             "breaker", "fuse per pump manual", "S1", "20 A / 75 mV", "external, at the pump",
             "0x40", False),
            (640, "P2", "SEAFLO 13A Series", "2000 GPH bilge, non-auto", "7.5 A max",
             "breaker", "fuse per pump manual", "S2", "20 A / 75 mV", "external, at the pump",
             "0x41", False),
            (1050, "P3", "Amarine FLO-2202", "diaphragm, dry-bilge pump", "3.5 A max",
             "F8", "4 A", "S3", "15 mΩ, 2512", "on the board",
             "0x44", True),
            (1460, "P4", "shower sump pump", "model not yet identified", "draw: open",
             "fuse", "open", "S4", "20 A / 75 mV", "external, at the pump",
             "0x45", False)]
    for (cx, pid, nm, nm2, draw, fl, fsub, sl, ssub, sloc, addr, board) in cols:
        # feed: bus -> fuse -> tap node; P4's feed is open, so it stops short of the bus
        if pid == "P4":
            s.append(txt(cx + 12, 162, "feed: open", 11, fill=MUTE))
        else:
            s.append(poly([(cx, TOP), (cx, 166)], RED))
            s.append(dot(cx, TOP, RED))
        s.append(fuse_v(cx, 190, RED, fl, lx=cx - 24, sub=fsub))
        s.append(poly([(cx, 214), (cx, 245)], RED))
        s.append(dot(cx, 245, RED))
        if board:
            # Q8 high-side switch, opto gate drive
            s.append(poly([(cx, 245), (cx, 270)], RED))
            s.append(pmos(cx - 30, 300, ORA))
            s.append(txt(cx + 12, 306, "Q8 high-side P-FET", 12, weight="bold"))
            s.append(poly([(cx - 46, 300), (cx - 120, 300)], ORA))
            s.append(box(cx - 190, 280, 70, 40, "#ffffff", ORA, 2.2, 5))
            s.append(txt(cx - 155, 297, "CH8 opto", 12, anchor="middle"))
            s.append(txt(cx - 155, 312, "from ESP32", 11, anchor="middle", fill=MUTE))
            s.append(poly([(cx, 330), (cx, 380)], ORA))
            # D8 flyback across the motor
            s.append(dot(cx, 358, ORA))
            s.append(poly([(cx, 358), (cx + 80, 358), (cx + 80, 392)], ORA))
            s.append(diode_v(cx + 80, 404, ORA, "D8"))
            s.append(poly([(cx + 80, 415), (cx + 80, 450), (cx, 450)], BLK))
            s.append(dot(cx, 450, BLK))
            s.append(txt(cx + 100, 432, "flyback", 11, fill=MUTE))
        else:
            s.append(poly([(cx, 245), (cx, 275)], RED))
            s.append(box(cx - 75, 275, 150, 56, "#ffffff", RED, 2.2, 5))
            s.append(txt(cx, 297, "Auto / Off / Man" if pid == "P1"
                         else "existing switching", 12.5, anchor="middle"))
            s.append(txt(cx, 315, "existing switch / float", 11, anchor="middle",
                         fill=MUTE))
            s.append(poly([(cx, 331), (cx, 380)], RED))
        # the motor and its negative lead
        s.append("<circle cx='%g' cy='410' r='30' fill='#ffffff' stroke='%s' "
                 "stroke-width='2.4'/>" % (cx, ORA if board else RED))
        s.append(txt(cx, 416, "M", 16, anchor="middle", weight="bold"))
        s.append(txt(cx - 44, 396, pid, 14, anchor="end", weight="bold"))
        s.append(txt(cx - 44, 413, nm, 11.5, anchor="end"))
        s.append(txt(cx - 44, 429, nm2, 11, anchor="end", fill=MUTE))
        s.append(txt(cx - 44, 445, draw, 11, anchor="end", fill=MUTE))
        s.append(poly([(cx, 440), (cx, 480)], BLK))
        # shunt in the negative lead
        s.append(box(cx - 16, 480, 32, 60, "#f1f8f1", GRN, 2.4, 3))
        s.append(txt(cx - 24, 506, sl, 13, anchor="end", weight="bold", fill=GRN))
        s.append(txt(cx - 24, 522, ssub, 11.5, anchor="end", fill=MUTE))
        s.append(txt(cx - 24, 538, sloc, 11, anchor="end", fill=MUTE))
        s.append(poly([(cx, 540), (cx, NEG)], BLK))
        s.append(dot(cx, NEG, BLK))
        # Kelvin pair to the INA226
        s.append(dot(cx, 468, GRN, 3.6))
        s.append(dot(cx, 552, GRN, 3.6))
        if board:
            s.append(poly([(cx, 468), (cx + 110, 468)], GRN, 2.2))
            s.append(poly([(cx, 552), (cx + 110, 552)], GRN, 2.2))
        else:  # a fuse at the shunt end of each lead of an external shunt
            for yk in (468, 552):
                s.append(poly([(cx, yk), (cx + 30, yk)], GRN, 2.2))
                s.append(fuse_h(cx + 54, yk, GRN, ""))
                s.append(poly([(cx + 78, yk), (cx + 110, yk)], GRN, 2.2))
        s.append(box(cx + 110, 450, 150, 120, "#f1f8f1", GRN, 2.2, 5))
        s.append(txt(cx + 118, 472, "IN+", 11, fill=GRN))
        s.append(txt(cx + 118, 556, "IN−", 11, fill=GRN))
        s.append(txt(cx + 185, 505, "INA226", 12.5, anchor="middle",
                     weight="bold", fill=GRN))
        s.append(txt(cx + 185, 523, addr, 12, anchor="middle"))
        s.append(txt(cx + 185, 541, "volts + amps", 11.5, anchor="middle",
                     fill=MUTE))
        # VBUS taps the feed upstream of the switch or Q8, through a series resistor
        s.append(poly([(cx, 245), (cx + 185, 245), (cx + 185, 330)], GRN, 2.2))
        s.append(res_v(cx + 185, 354, GRN, "10 kΩ"))
        s.append(poly([(cx + 185, 378), (cx + 185, 450)], GRN, 2.2))
        s.append(txt(cx + 192, 466, "VBUS", 11, fill=GRN))
        s.append(txt(cx + 12, 238, "upstream feed", 11, fill=MUTE))
        # I²C drop
        s.append(poly([(cx + 185, 570), (cx + 185, 620)], BLU, 2.2, "6 4"))
        s.append(dot(cx + 185, 620, BLU))

    # I²C bus, hopping the pump columns
    xs = [415] + [x for c in (640, 1050, 1460) for x in (c - 9, c + 9)] + [1645]
    for x0, x1 in zip(xs[0::2], xs[1::2]):
        s.append(poly([(x0, 620), (x1, 620)], BLU, 2.2, "6 4"))
    for c in (640, 1050, 1460):
        s.append(hop_h(c, 620, BLU, 2.2))
    s.append(txt(425, 612, "I²C", 12, fill=BLU, weight="bold"))
    s.append(poly([(930, 620), (930, 650)], BLU, 2.2, "6 4"))
    s.append(dot(930, 620, BLU))
    s.append(box(810, 650, 240, 70, "#f3f7fd", BLU, 2.4, 6))
    s.append(txt(930, 676, "ESP32", 14, anchor="middle", weight="bold", fill=BLU))
    s.append(txt(930, 695, "firmware derives running;", 11.5, anchor="middle",
                 fill=MUTE))
    s.append(txt(930, 711, "publishes volts and amps to Signal K", 11.5,
                 anchor="middle", fill=MUTE))

    s.append(legend(40, 835, LEG))
    s.append(txt(440, 840, "Each Kelvin lead of an external shunt is fused at the "
                           "shunt end: an open return downstream would otherwise "
                           "send motor current down the lead.", 12.5))
    s.append(txt(440, 860, "A tripped breaker or blown fuse reads as zero volts on "
                           "that pump's VBUS — an alarm.", 12.5))
    s.append(txt(440, 880, "P1, P2 and P4 current never crosses the board; P3's "
                           "already does, through Q8.", 12.5))
    s.append(txt(440, 900, "10 kΩ series resistor and 0.5 A sense-lead fuses are "
                           "stand-ins.", 12.5, fill=MUTE))
    s.append("</svg>")
    return "".join(s)


if __name__ == "__main__":
    out = "diagrams/electrical"
    for name, fn in [("midship-board-block", block),
                     ("midship-board-sensing", sensing)]:
        p = os.path.join(out, name + ".svg")
        with open(p, "w") as f:
            f.write(fn())
        print("wrote", p)
