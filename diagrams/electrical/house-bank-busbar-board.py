# -*- coding: utf-8 -*-
"""Generates the house-bank bus bar board layout (.svg and .drawio), 1 unit = 1 mm.

Run from the repo root. Every size lives in this file: a part's footprint in
its function, its place on the board in build(). Each number is tagged in
PARTS as drawing (maker's dimensioned drawing), scaled (taken off a maker's
picture) or guess; nothing here was measured on the boat's own parts.
"""
import os

BOARD_W, BOARD_H = 457.2, 304.8          # 18 x 12 in HDPE
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
    """Blue Sea 5502, long axis horizontal. Returns (left cable stud, right cable stud)."""
    body("Class T", cx - 88.9, cy - 25.4, 177.8, 50.8, "#e8837a", "")
    rect(cx - 34.95, cy - 12.7, 69.9, 25.4, "#fde0dc")          # the fuse, 69.9 x 25.4 blades
    text(cx, cy + 1.6, "Class T", 4.6)
    for dx in (-23.4, 23.4):
        stud(cx + dx, cy, 8)
    for dx in (-79.37, 79.37):
        for dy in (-16.77, 16.77):
            screw(cx + dx, cy + dy)
    left, right = (cx - 51.0, cy), (cx + 51.0, cy)
    for p in (left, right):
        stud(p[0], p[1], 10)
    return left, right


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


def switch(x, y):
    """Blue Sea m-Series, studs underneath on a horizontal line. Returns (left, right)."""
    w = 74.93
    body("Master switch", x, y, w, w, "#9ccc9c", "")
    cx, cy = x + w / 2, y + w / 2
    circ(cx, cy, 24, "#c4e3c4")
    text(cx, y + 8.5, "Master switch", 4.2)
    for dx in (-27.625, 27.625):
        for dy in (-27.625, 27.625):
            screw(cx + dx, cy + dy)
    left, right = (cx - 22.25, cy), (cx + 22.25, cy)
    for p in (left, right):
        stud(p[0], p[1], 10)
    return left, right


def bar(name, x, y, w, h, holes, label=None, fill=COPPER):
    """A copper bar or link; holes are (x, y, what bolts there)."""
    rect(x, y, w, h, fill, op=0.78)
    for hx, hy, _ in holes:
        circ(hx, hy, 2.2, "#5a3a1a")
    if label:
        if w >= h:
            text(x + w / 2, y + h / 2 - 5.5, label, 4.4)
        else:
            text(x - 3.0, y + h / 2 - 20, label, 4.4, rot=-90)
    bars.append((name, x, y, w, h, holes))


def build():
    rect(0, 0, BOARD_W, BOARD_H, "#f7f7f2")

    # ---- positive side, left ------------------------------------------------
    sw_in, sw_out = switch(10, 10)
    tops = [anl("Inverter/charger fuse", 116, 10, "Inverter/charger (type open)", 48, dash=True),
            anl("DC-DC ANL", 160, 10, "ANL 60 A  DC-DC", 48),
            anl("2nd charger fuse", 204, 10, "2nd charger (type open)", 48, dash=True)]
    hb_up, hb_lo = breaker("House breaker", 231, 10, "60 A house", upper_right=True)
    ct_load, ct_batt = class_t(196, 152.5)
    ab_up, ab_lo = breaker("Always-on breaker", 11, 199.4, "60 A always-on", upper_right=True)
    # Batteries run 1-4 left to right on both bars, with the + takeoff at the right end and
    # the shunt at the left end, so every battery sees about the same length of bar.
    batts = [anl("Battery ANL %d" % (i + 1), cx, 180.7,
                 "ANL  battery %d%s" % (i + 1, "" if i < 2 else " (future)"), 78, dash=i >= 2)
             for i, cx in enumerate((82, 126, 170, 214))]

    y_sw = tops[0][1][1]                  # switched bar lies over the fuses' lower studs
    y_bt = batts[0][0][1]                 # battery bar lies over the fuses' upper studs
    y_un = ct_load[1]                     # unswitched bar lands on the Class T load stud

    bar("Switched + bar", 57.2, y_sw - BAR / 2, 205.0, BAR,
        [(sw_out[0], y_sw, "link to switch")] + [(t[1][0], y_sw, "fuse stud") for t in tops]
        + [(hb_lo[0], y_sw, "link to house breaker")], "SWITCHED + BAR")
    bar("Link, switch out", sw_out[0] - BAR / 2, sw_out[1] - 12.5, BAR, y_sw - sw_out[1] + 25,
        [(sw_out[0], sw_out[1], "switch stud"), (sw_out[0], y_sw, "bar")], fill=LINK)
    bar("Link, house breaker", hb_lo[0] - 7.5, hb_lo[1] - 7.5, 15, y_sw - hb_lo[1] + 15,
        [(hb_lo[0], hb_lo[1], "breaker stud"), (hb_lo[0], y_sw, "bar")], fill=LINK)

    bar("Unswitched + bar", 12.0, y_un - BAR / 2, ct_load[0] + 12.5 - 12.0, BAR,
        [(sw_in[0], y_un, "link to switch"), (ab_up[0], y_un, "link to always-on breaker"),
         (75.0, y_un, "Cerbo +, M6"), (100.0, y_un, "spare, M6"),
         (ct_load[0], y_un, "Class T stud")], "UNSWITCHED + BAR")
    stud(75.0, y_un, 6)
    stud(100.0, y_un, 6)
    text(75.0, y_un + 10.5, "Cerbo +", 3.6)
    bar("Link, switch in", sw_in[0] - BAR / 2, sw_in[1] - 12.5, BAR, y_un - sw_in[1] + 25,
        [(sw_in[0], sw_in[1], "switch stud"), (sw_in[0], y_un, "bar")], fill=LINK)
    bar("Link, always-on breaker", ab_up[0] - 7.5, y_un - 7.5, 15, ab_up[1] - y_un + 15,
        [(ab_up[0], y_un, "bar"), (ab_up[0], ab_up[1], "breaker stud")], fill=LINK)

    bar("Battery + bar", 69.0, y_bt - BAR / 2, 190.5, BAR,
        [(b[0][0], y_bt, "fuse stud") for b in batts] + [(ct_batt[0], y_bt, "link to Class T")],
        "BATTERY + BAR")
    bar("Link, Class T to battery bar", ct_batt[0] - 10, ct_batt[1] - 12.5, 20, y_bt - ct_batt[1] + 25,
        [(ct_batt[0], ct_batt[1], "Class T stud"), (ct_batt[0], y_bt, "bar")], fill=LINK)

    # ---- divider --------------------------------------------------------------
    rect(290.5, 3, 3, BOARD_H - 6, "#ffffff", dash=True)

    # ---- negative side, right ---------------------------------------------------
    sx = 342.5                            # shunt centreline; the bars are as wide as its base
    body("SmartShunt base", sx - 12.5, y_bt - 87.5, 25, 120, "#7fb3e6", "")
    body("SmartShunt housing", sx - 39.5, y_bt - 65.5, 27, 76, "#a9cdf0", "SmartShunt", rot=-90)
    s_sys, s_bat = (sx, y_bt - 55.0), (sx, y_bt)
    screw(sx, y_bt - 78.0)
    screw(sx, y_bt + 23.0)

    bar("Battery - bar", sx - 12.5, y_bt - BAR / 2, 120.0, BAR,
        [(s_bat[0], y_bt, "shunt, battery side, M10")]
        + [(x, y_bt, "battery %d -, M8" % (i + 1)) for i, x in enumerate((366, 390, 414, 438))],
        "BATTERY - BAR")
    ys = (25, 46, 67, 88, 109, 130)
    names = ("inverter/charger -", "DC-DC -", "2nd charger -", "house -", "always-on -", "Cerbo -")
    bar("Returns - bar", sx - 12.5, 12.0, BAR, s_sys[1] + 12.5 - 12.0,
        [(sx, y, "%s, %s" % (n, "M8" if i < 3 else "M6")) for i, (y, n) in enumerate(zip(ys, names))]
        + [(s_sys[0], s_sys[1], "shunt, system side, M10")], "- BAR (returns)")
    for p in (s_sys, s_bat):
        stud(p[0], p[1], 10)
    for x in (366, 390, 414, 438):
        stud(x, y_bt, 8)
    for i, (y, n) in enumerate(zip(ys, names)):
        stud(sx, y, 8 if i < 3 else 6)
        text(sx + 16, y + 1.5, n, 3.8, anchor="start")

    # ---- leads and dimensions ---------------------------------------------------
    text(160, -5, "switched leads leave the top edge", 4.6)
    text(400, -5, "returns leave the top edge", 4.6)
    text(148, BOARD_H + 8, "battery + leads, one per fuse", 4.6)
    text(402, BOARD_H + 8, "battery - leads", 4.6)
    text(35, BOARD_H + 8, "always-on leads", 4.6)
    text(BOARD_W / 2, -14, "457.2 (18 in)", 5)
    text(-8, BOARD_H / 2, "304.8 (12 in)", 5, rot=-90)
    for i, b in enumerate(batts):
        text(b[1][0], BOARD_H - 3.5, "B%d+" % (i + 1), 3.8)
    for i, x in enumerate((366, 390, 414, 438)):
        text(x, y_bt + 19, "B%d-" % (i + 1), 3.8)


def check():
    """Every part on the board, no two part bodies overlapping."""
    bad = []
    for n, x, y, w, h in bodies:
        if x < 0 or y < 0 or x + w > BOARD_W or y + h > BOARD_H:
            bad.append("%s is off the board" % n)
    for i, a in enumerate(bodies):
        for b in bodies[i + 1:]:
            if a[1] < b[1] + b[3] and b[1] < a[1] + a[3] and a[2] < b[2] + b[4] and b[2] < a[2] + a[4]:
                bad.append("%s overlaps %s" % (a[0], b[0]))
    for n, x, y, w, h, holes in bars:
        if x < 0 or y < 0 or x + w > BOARD_W or y + h > BOARD_H:
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
    tab_y = BOARD_H + 22
    rows, parts = drill_rows(), PARTS
    total_h = oy + tab_y + 9 + 6.2 * (len(rows) + len(parts) + 5) + 8
    o = ["<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 %g %g' "
         "font-family='DejaVu Sans, Helvetica, Arial, sans-serif'>" % (BOARD_W + 44, total_h),
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
            "background=\"#ffffff\" pageWidth=\"540\" pageHeight=\"400\" math=\"0\" shadow=\"0\"><root>\n"
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
