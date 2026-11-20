# -*- coding: utf-8 -*-
"""Generates the house-bank bus bar board layout (.svg and .drawio), 1 unit = 1 mm.

Run from the repo root. Every size lives in this file: a part's footprint in
its function, its place on the board in build(). Each number is tagged in
PARTS as drawing (maker's dimensioned drawing), scaled (taken off a maker's
picture) or guess; nothing here was measured on the boat's own parts.
"""
import os

BOARD_W, BOARD_H = 457.2, 304.8          # positive board: the whole 18 x 12 in HDPE sheet
NEG = (0.0, BOARD_H + 34.0, 310.0, 166.0)  # negative board, its own piece, sized to its parts; x, y, w, h
PITCH = 44.0                             # battery stud pitch, the same on both bars
CT_STUDS = 102.0                         # Class T cable studs; sets the gap between the two + bars
TOTAL_W = BOARD_W
BAR = 25.0                               # main copper bar width
COPPER, LINK = "#d9925a", "#e8b07a"
INK = "#111111"

# name, size, studs, source, how the numbers were got
PARTS = [
    ("ANL fuse block, Blue Sea 5005", "114.3 x 38.1, cover 41.9 high",
     "2 x 5/16in (M8), 61.72 apart", "bluesea.com/products/5005", "drawing"),
    ("Class T fuse block, Blue Sea 5502 (225-400 A)", "177.8 x 50.8, cover 58.4 high",
     "cable studs about 102 apart", "bluesea.com/products/5502", "drawing; stud spacing scaled"),
    ("Battery switch, Blue Sea m-Series 6006", "74.9 square, 45.6 deep behind the flange",
     "2 x 3/8in (M10) underneath, about 44.5 apart", "bluesea.com/products/6006",
     "drawing; stud spacing scaled"),
    ("60 A breaker, Blue Sea 285-Series 7184", "81.3 x 48.1, 31.5 high",
     "2 x M6 on opposite corners, 63.1 x 25.8", "bluesea.com/products/7184", "drawing"),
    ("Victron SmartShunt 500 A", "base 120 x 25, about 52 wide with the housing",
     "2 x M10, 55 apart, bar seat 33.5 above the board",
     "victronenergy.com DimensionDrawing-SmartShunt-500A50mV.pdf", "drawing; housing scaled"),
    ("Copper bar", "25 wide; links 25, 20 and 15 wide", "", "", "widths given or guessed; thickness open"),
    ("Small always-on fuses", "86 x 135 kept", "", "", "guess; fits a 6-way blade block, 124.3 x 84.2"),
]

shapes = []      # ("rect", x, y, w, h, fill, stroke, dash, opacity) | ("circ", x, y, r, fill) | ("text", ...)
bodies = []      # (name, x, y, w, h) for the overlap check
bars = []        # (name, x, y, w, h, [holes (x, y, label)])


def rect(x, y, w, h, fill="#ffffff", stroke=INK, dash=False, op=1.0):
    shapes.append(("rect", x, y, w, h, fill, stroke, dash, op))


def circ(x, y, r, fill="#ffffff"):
    shapes.append(("circ", x, y, r, fill))


def text(x, y, s, size=5.0, anchor="middle", rot=0):
    shapes.append(("text", x, y, s, size, anchor, rot))


def body(name, x, y, w, h, fill, label, rot=0, dash=False):
    rect(x, y, w, h, fill, dash=dash)
    bodies.append((name, x, y, w, h))
    text(x + w / 2, y + h / 2, label, 4.6, rot=rot)


def stud(x, y, d):
    circ(x, y, d * 0.9, "#8a8a8a")       # nut across flats, roughly
    circ(x, y, d / 2, "#333333")


def screw(x, y):
    circ(x, y, 2.5, "#ffffff")


def anl(name, cx, y0, label, label_at, dash=False):
    """Blue Sea 5005, long axis vertical. Returns (top stud, bottom stud)."""
    body(name, cx - 19.05, y0, 38.1, 114.3, "#f2b84b", "", dash=dash)
    rect(cx - 11.1, y0 + 16.65, 22.2, 81.0, "#fff3d0")          # the ANL fuse, 81 x 22.2
    text(cx - 14.0, y0 + label_at, label, 3.8, rot=-90)   # beside the fuse, clear of the bar
    top, bot = (cx, y0 + 26.29), (cx, y0 + 88.01)
    for p in (top, bot):
        stud(p[0], p[1], 8)
    screw(cx, y0 + 7.93)
    screw(cx, y0 + 106.37)
    return top, bot


def class_t(cx, cy):
    """Blue Sea 5502, long axis vertical. Returns (upper cable stud, lower cable stud)."""
    body("Class T", cx - 25.4, cy - 88.9, 50.8, 177.8, "#e8837a", "")
    rect(cx - 12.7, cy - 34.95, 25.4, 69.9, "#fde0dc")          # the fuse, 69.9 x 25.4 blades
    text(cx + 1.6, cy, "Class T", 4.6, rot=-90)
    for dy in (-23.4, 23.4):
        stud(cx, cy + dy, 8)
    for dy in (-79.37, 79.37):
        for dx in (-16.77, 16.77):
            screw(cx + dx, cy + dy)
    up, lo = (cx, cy - CT_STUDS / 2), (cx, cy + CT_STUDS / 2)
    for p in (up, lo):
        stud(p[0], p[1], 10)
    return up, lo


def breaker(name, x, y, label, upper_right):
    """Blue Sea 285 surface mount, long axis vertical. Returns (upper stud, lower stud)."""
    w, h = 48.13, 81.28
    body(name, x, y, w, h, "#cfcfcf", label)
    cx, cy = x + w / 2, y + h / 2
    s = 1 if upper_right else -1
    up, lo = (cx + s * 12.92, cy - 31.545), (cx - s * 12.92, cy + 31.545)
    for p in (up, lo):
        stud(p[0], p[1], 6)
    screw(cx - s * 13.335, cy - 28.32)
    screw(cx + s * 13.335, cy + 28.32)
    return up, lo


def switch(name, x, y, dash=False):
    """Blue Sea m-Series, studs underneath on a horizontal line. Returns (left, right)."""
    w = 74.93
    body(name, x, y, w, w, "#9ccc9c", "", dash=dash)
    cx, cy = x + w / 2, y + w / 2
    circ(cx, cy, 24, "#c4e3c4")
    text(cx, y + 8.5, name, 4.2)
    for dx in (-27.625, 27.625):
        for dy in (-27.625, 27.625):
            screw(cx + dx, cy + dy)
    left, right = (cx - 22.25, cy), (cx + 22.25, cy)
    for p in (left, right):
        stud(p[0], p[1], 10)
    return left, right


def bar(name, x, y, w, h, holes, label=None, fill=COPPER, label_x=None):
    """A copper bar or link; holes are (x, y, what bolts there)."""
    rect(x, y, w, h, fill, op=0.78)
    for hx, hy, _ in holes:
        circ(hx, hy, 2.2, "#5a3a1a")
    if label:
        if w >= h:
            text(label_x or x + w / 2, y + h / 2 - 5.5, label, 4.4)
        else:
            text(x - 3.0, y + h / 2 - 20, label, 4.4, rot=-90)
    bars.append((name, x, y, w, h, holes))


def build():
    rect(0, 0, BOARD_W, BOARD_H, "#f7f7f2")
    rect(NEG[0], NEG[1], NEG[2], NEG[3], "#f7f7f2")

    # ---- positive board: the whole sheet ----------------------------------------
    # Top row hangs off the unswitched bar; the Class T stands at the right end with one
    # cable stud on each + bar; batteries and the breakers fill the bottom row.
    ms_in, ms_out = (lambda l, r: (r, l))(*switch("Master switch", 10, 10))
    y_top = ms_in[1] - 26.29              # fuse row: upper studs level with the switch studs
    x_ct = BOARD_W - 10 - 25.4
    inv = anl("Inverter/charger fuse", 372, y_top, "Inverter/charger (type open)", 48, dash=True)
    dis_l, dis_r = switch("Inverter disconnect", inv[0][0] - 46 - 22.25 - 37.465, 10, dash=True)
    tops = [anl("Solar fuse", 156, y_top, "Solar (planned, type open)", 48, dash=True),
            anl("2nd charger fuse", 200, y_top, "2nd charger (type open)", 48, dash=True),
            anl("DC-DC ANL", 244, y_top, "ANL 60 A  DC-DC", 48),
            inv]
    y_un = inv[1][1]                      # unswitched bar lies over the fuses' lower studs
    y_bt = y_un + CT_STUDS                # battery bar lies over the fuses' upper studs
    ct_un, ct_bt = class_t(x_ct, y_un + CT_STUDS / 2)
    # Batteries run 1-4 left to right on both bars, with the + takeoff at the right end and
    # the shunt at the left end, so every battery sees about the same length of bar.
    batts = [anl("Battery ANL %d" % (i + 1), cx, y_bt - 26.29,
                 "ANL  battery %d%s" % (i + 1, "" if i < 2 else " (future)"), 78, dash=i >= 2)
             for i, cx in enumerate(240 + PITCH * k for k in range(4))]
    hb_up, hb_lo = breaker("House breaker", ms_out[0] - 11.145, 150, "60 A house", upper_right=False)
    ab_up, ab_lo = breaker("Always-on breaker", 80, 150, "60 A always-on", upper_right=False)
    body("Small always-on fuses", 131, 150, 86, 135, "#ffffff", "", dash=True)
    for i, s in enumerate(("space kept for the", "small always-on fuses:", "Cerbo", "bilge pumps",
                           "monitoring, alarms", "(part open)", "fed from the", "always-on breaker")):
        text(174, 196 + 6.5 * i + (6 if i >= 6 else 0), s, 4.2)

    bar("Unswitched + bar", ms_in[0] - 12.5, y_un - BAR / 2, x_ct + 12.5 - (ms_in[0] - 12.5), BAR,
        [(ms_in[0], y_un, "link to master switch"), (ab_up[0], y_un, "link to always-on breaker")]
        + [(t[1][0], y_un, "fuse stud") for t in tops] + [(x_ct, y_un, "Class T stud")],
        "UNSWITCHED + BAR", label_x=308)
    bar("Link, master switch in", ms_in[0] - BAR / 2, ms_in[1] - 12.5, BAR, y_un - ms_in[1] + 25,
        [(ms_in[0], ms_in[1], "switch stud"), (ms_in[0], y_un, "bar")], fill=LINK)
    bar("Link, master switch to house breaker", ms_out[0] - 10, ms_out[1] - 12.5, 20,
        hb_up[1] - ms_out[1] + 22.5,
        [(ms_out[0], ms_out[1], "switch stud"), (hb_up[0], hb_up[1], "breaker stud")], fill=LINK)
    bar("Link, always-on breaker", ab_up[0] - 7.5, y_un - 7.5, 15, ab_up[1] - y_un + 15,
        [(ab_up[0], y_un, "bar"), (ab_up[0], ab_up[1], "breaker stud")], fill=LINK)
    bar("Link, inverter fuse to disconnect", dis_r[0] - 12.5, dis_r[1] - 12.5, inv[0][0] - dis_r[0] + 25,
        BAR, [(dis_r[0], dis_r[1], "switch stud"), (inv[0][0], inv[0][1], "fuse stud")], fill=LINK)
    bar("Battery + bar", batts[0][0][0] - 13.0, y_bt - BAR / 2, x_ct + 12.5 - (batts[0][0][0] - 13.0), BAR,
        [(b[0][0], y_bt, "fuse stud") for b in batts] + [(x_ct, y_bt, "Class T stud")],
        "BATTERY + BAR", label_x=306)

    # ---- negative board, below ---------------------------------------------------
    # Shunt lies level: system block left, battery block right, housing below.
    x_sys = NEG[0] + 44.5
    x_bat = x_sys + 55.0
    y_rt = NEG[1] + 24.5                  # returns bar
    y_nb = y_rt + 90.0                    # shunt and battery - bar
    body("SmartShunt base", x_sys - 32.5, y_nb - 12.5, 120, 25, "#7fb3e6", "")
    body("SmartShunt housing", x_sys - 10.5, y_nb + 12.5, 76, 27, "#a9cdf0", "SmartShunt")
    screw(x_sys - 23.0, y_nb)
    screw(x_bat + 23.0, y_nb)
    neg = [x_bat + 30.0 + PITCH * k for k in range(4)]
    bar("Battery - bar", x_bat - 12.5, y_nb - BAR / 2, neg[-1] + 13.0 - (x_bat - 12.5), BAR,
        [(x_bat, y_nb, "shunt, battery side, M10")]
        + [(x, y_nb, "battery %d -, M8" % (i + 1)) for i, x in enumerate(neg)], "BATTERY - BAR", label_x=neg[1] + PITCH / 2)
    names = ("inverter/charger -", "DC-DC -", "2nd charger -", "solar -", "house -",
             "Cerbo -", "bilge pumps -", "monitoring -")
    rts = [x_sys + 30.0 * (k + 1) for k in range(len(names))]
    bar("Returns - bar", x_sys - 12.5, y_rt - BAR / 2, rts[-1] + 13.0 - (x_sys - 12.5), BAR,
        [(x_sys, y_rt, "link to shunt")]
        + [(x, y_rt, "%s, %s" % (n, "M8" if i < 4 else "M6")) for i, (x, n) in enumerate(zip(rts, names))],
        )
    text(rts[3] + 15, y_rt - 15.5, "- BAR (returns)", 4.4)
    bar("Link, shunt to returns bar", x_sys - 12.5, y_rt - 12.5, BAR, y_nb - y_rt + 25,
        [(x_sys, y_rt, "bar"), (x_sys, y_nb, "shunt, system side, M10")], fill=LINK)
    for x in (x_sys, x_bat):
        stud(x, y_nb, 10)
    for i, x in enumerate(neg):
        stud(x, y_nb, 8)
        text(x, y_nb + 19, "B%d-" % (i + 1), 3.8)
    for i, (x, n) in enumerate(zip(rts, names)):
        stud(x, y_rt, 8 if i < 4 else 6)
        text(x - 2.0, y_rt + 17, n, 3.8, anchor="start", rot=40)

    # ---- leads and dimensions ---------------------------------------------------
    text(BOARD_W / 2, -14, "positive board 457.2 x 304.8, the whole 18 x 12 in sheet", 5)
    text(264, -5, "always-on chargers and the inverter/charger leave the top edge", 4.6)
    for i, b in enumerate(batts):
        text(b[1][0], BOARD_H + 6, "B%d+" % (i + 1), 3.8)
    text(batts[1][1][0] + PITCH / 2, BOARD_H + 13, "battery + leads, one per fuse", 4.6)
    text(hb_lo[0], BOARD_H + 6, "house lead", 4.6)
    text(174, BOARD_H + 6, "always-on leads", 4.6)
    text(NEG[0] + NEG[2] + 6, NEG[1] + 20, "returns leave the top edge", 4.6, anchor="start")
    text(NEG[0] + NEG[2] + 6, y_nb + 2, "battery - leads leave the bottom edge,", 4.6, anchor="start")
    text(NEG[0] + NEG[2] + 6, y_nb + 8.5, "same order as +", 4.6, anchor="start")
    text(NEG[0] + NEG[2] / 2, NEG[1] - 5, "negative board %g x %g, its own piece" % (NEG[2], NEG[3]), 5)


def on_a_board(x, y, w, h):
    return any(bx <= x and by <= y and x + w <= bx + bw and y + h <= by + bh
               for bx, by, bw, bh in ((0, 0, BOARD_W, BOARD_H), NEG))


def check():
    """Every part on the board, no two part bodies overlapping."""
    bad = []
    for n, x, y, w, h in bodies:
        if not on_a_board(x, y, w, h):
            bad.append("%s is off the board" % n)
    for i, a in enumerate(bodies):
        for b in bodies[i + 1:]:
            if a[1] < b[1] + b[3] and b[1] < a[1] + a[3] and a[2] < b[2] + b[4] and b[2] < a[2] + a[4]:
                bad.append("%s overlaps %s" % (a[0], b[0]))
    for n, x, y, w, h, holes in bars:
        if not on_a_board(x, y, w, h):
            bad.append("%s is off the board" % n)
        for hx, hy, what in holes:
            if not (x + 5 <= hx <= x + w - 5 and y + 5 <= hy <= y + h - 5):
                bad.append("%s: hole for %s is within 5 mm of an edge" % (n, what))
    return bad


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def drill_rows():
    """One row per bar: size, then each hole's distance from the bar's left or top end."""
    rows = []
    for n, x, y, w, h, holes in bars:
        along = (lambda p: p[0] - x) if w >= h else (lambda p: p[1] - y)
        hs = sorted(holes, key=along)
        rows.append((n, "%.1f x %g" % (max(w, h), min(w, h)),
                     ", ".join("%.1f" % along(p) for p in hs)))
    return rows


def svg():
    ox, oy = 22, 26
    tab_y = NEG[1] + NEG[3] + 16
    rows, parts = drill_rows(), PARTS
    total_h = oy + tab_y + 9 + 6.2 * (len(rows) + len(parts) + 5) + 8
    o = ["<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 %g %g' "
         "font-family='DejaVu Sans, Helvetica, Arial, sans-serif'>" % (TOTAL_W + 44, total_h),
         "<rect width='100%' height='100%' fill='#ffffff'/>", "<g transform='translate(%g,%g)'>" % (ox, oy)]
    for s in shapes:
        if s[0] == "rect":
            _, x, y, w, h, fill, stroke, dash, op = s
            o.append("<rect x='%.2f' y='%.2f' width='%.2f' height='%.2f' fill='%s' stroke='%s' "
                     "stroke-width='0.5' fill-opacity='%g'%s/>"
                     % (x, y, w, h, fill, stroke, op, " stroke-dasharray='3 2'" if dash else ""))
        elif s[0] == "circ":
            o.append("<circle cx='%.2f' cy='%.2f' r='%.2f' fill='%s' stroke='%s' stroke-width='0.35'/>"
                     % (s[1], s[2], s[3], s[4], INK))
        else:
            _, x, y, t, size, anchor, rot = s
            tr = " transform='rotate(%g %.2f %.2f)'" % (rot, x, y) if rot else ""
            o.append("<text x='%.2f' y='%.2f' font-size='%g' text-anchor='%s' fill='%s'%s>%s</text>"
                     % (x, y, size, anchor, INK, tr, esc(t)))

    def line(y, cols, bold=False):
        for cx, t in cols:
            o.append("<text x='%g' y='%.1f' font-size='4.4' fill='%s'%s>%s</text>"
                     % (cx, y, INK, " font-weight='bold'" if bold else "", esc(t)))

    y = tab_y
    line(y, [(0, "Copper to cut: length x width, then hole centres from the left end "
                 "(top end for an upright piece), all on the centreline, mm")], True)
    for n, size, hs in rows:
        y += 6.2
        line(y, [(0, n), (95, size), (140, hs)])
    y += 11
    line(y, [(0, "Parts as drawn"), (140, "size, mm"), (240, "studs"), (345, "numbers from")], True)
    for n, size, st, _src, how in parts:
        y += 6.2
        line(y, [(0, n), (140, size), (240, st), (345, how)])
    o.append("</g></svg>")
    return "\n".join(o) + "\n"


def drawio():
    cells = ["<mxCell id=\"0\"/>", "<mxCell id=\"1\" parent=\"0\"/>"]
    for i, s in enumerate(shapes):
        cid = "s%d" % i
        if s[0] == "rect":
            _, x, y, w, h, fill, stroke, dash, op = s
            style = "rounded=0;html=1;fillColor=%s;strokeColor=%s;opacity=%d;%s" % (
                fill, stroke, round(op * 100), "dashed=1;" if dash else "")
            val = ""
        elif s[0] == "circ":
            _, cx, cy, r, fill = s
            x, y, w, h = cx - r, cy - r, 2 * r, 2 * r
            style, val = "ellipse;html=1;fillColor=%s;strokeColor=%s;" % (fill, INK), ""
        else:
            _, tx, ty, t, size, anchor, rot = s
            w, h = max(20.0, len(t) * size * 0.6), size * 1.6
            x = tx - w / 2 if anchor == "middle" else tx
            y = ty - h * 0.75
            style = "text;html=1;align=%s;verticalAlign=middle;fontSize=%g;fontColor=%s;rotation=%g;" % (
                "center" if anchor == "middle" else "left", size, INK, rot)
            val = esc(t).replace('"', "&quot;")
        cells.append("<mxCell id=\"%s\" value=\"%s\" style=\"%s\" vertex=\"1\" parent=\"1\">"
                     "<mxGeometry x=\"%.2f\" y=\"%.2f\" width=\"%.2f\" height=\"%.2f\" as=\"geometry\"/></mxCell>"
                     % (cid, val, style, x + 40, y + 40, w, h))
    return ("<mxfile host=\"drawio\"><diagram id=\"board\" name=\"Bus bar board\">"
            "<mxGraphModel dx=\"1000\" dy=\"600\" grid=\"1\" gridSize=\"5\" guides=\"1\" page=\"1\" "
            "background=\"#ffffff\" pageWidth=\"700\" pageHeight=\"400\" math=\"0\" shadow=\"0\"><root>\n"
            + "\n".join(cells) + "\n</root></mxGraphModel></diagram></mxfile>\n")


if __name__ == "__main__":
    build()
    problems = check()
    if problems:
        raise SystemExit("\n".join(problems))
    here = os.path.dirname(os.path.abspath(__file__))
    for name, data in (("house-bank-busbar-board.svg", svg()), ("house-bank-busbar-board.drawio", drawio())):
        with open(os.path.join(here, name), "w", encoding="utf-8") as f:
            f.write(data)
    for row in drill_rows():
        print("%-30s %-14s %s" % row)
