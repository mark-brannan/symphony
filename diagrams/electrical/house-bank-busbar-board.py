# -*- coding: utf-8 -*-
"""Generates the house-bank bus bar board layout (.svg and .drawio), 1 unit = 1 mm.

Run from the repo root. Every size lives in this file: a part's footprint in
its function, its place on the board in build(). Each number is tagged in
PARTS as drawing (maker's dimensioned drawing), scaled (taken off a maker's
picture) or guess; nothing here was measured on the boat's own parts.
"""
import os

BOARD_W, BOARD_H = 0.0, 203.2           # distribution board; its width ends just past the spare hole, set in build()
BATT = (0.0, 0.0, 228.6, 139.7)         # battery board, 9 x 5.5 in, butted to the right of it; x set in build()
GAP = 3.0                               # between the two positive boards, which butt and stay level
NEG = (0.0, BOARD_H + 34.0, 262.0, 144.0)    # negative board, its own piece, sized to its parts; x, y, w, h
PITCH = 44.0                             # battery stud pitch, the same on both bars
CT_STUDS = 46.8                          # Class T fuse bolt centres
SPARE = 25.4                             # bare length of unswitched bar kept for one spare hole
TOTAL_W = 0.0
DIM = "#1f5fbf"                          # dimension lines
BAR = 25.0                               # main copper bar width
COPPER, LINK = "#d9925a", "#e8b07a"
INK = "#111111"

# name, size, studs, source, how the numbers were got
PARTS = [
    ("ANL fuse block, Blue Sea 5005", "114.3 x 38.1, cover 41.9 high",
     "2 x 5/16in (M8), 61.72 apart", "bluesea.com/products/5005", "drawing"),
    ("Class T fuse block, compact, part not named", "about 100 x 40, long axis vertical",
     "2 x M10 on the fuse's bolt centres, 46.8 apart", "", "guess, sized like the ANL block"),
    ("Battery switch, Blue Sea m-Series 6006", "74.9 square, 45.6 deep behind the flange",
     "2 x 3/8in (M10) underneath, about 44.5 apart", "bluesea.com/products/6006",
     "drawing; stud spacing scaled"),
    ("Breaker, surface mount, waterproof (owner's)", "74 x 48.4, 34 high",
     "BAT, LOAD on opposite corners, ~62 x 23.5", "seller's dimensioned photo",
     "outline drawing; studs scaled"),
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


BRK_L, BRK_W = 74.0, 48.4               # breaker flange, long axis
BRK_DX, BRK_DY = 31.0, 11.75            # stud offset from centre, lying on its side; scaled from a photo


def breaker_side(name, x, y, label, dash=False):
    """Surface-mount breaker turned a quarter clockwise from upright: BAT (top right upright)
    comes to the right, below centre; LOAD to the left, above. It cannot be mirrored, so the
    input is always the lower stud. Returns (input stud, output stud)."""
    w, h = BRK_L, BRK_W
    body(name, x, y, w, h, "#cfcfcf", "", dash=dash)
    cx, cy = x + w / 2, y + h / 2
    text(cx + 3, y + 7, label, 3.6)          # clear of the bar on its input stud
    inp, out = (cx + BRK_DX, cy + BRK_DY), (cx - BRK_DX, cy - BRK_DY)
    for p in (inp, out):
        stud(p[0], p[1], 6)
    screw(cx + 28.35, cy - 15.15)
    screw(cx - 28.35, cy + 15.15)
    text(cx + BRK_DX, cy + BRK_DY - 7, "BAT", 3.2)
    text(cx - BRK_DX, cy - BRK_DY + 9.5, "LOAD", 3.2)
    return inp, out


def line(x1, y1, x2, y2, color=DIM, dash=False, w=0.3):
    shapes.append(("line", x1, y1, x2, y2, color, dash, w))


def dim_h(holes, y_line, below=False):
    """Chain dimension along x: holes are (x, y); dashed extension lines to a line at y_line."""
    holes = sorted(holes)
    s = 1 if below else -1
    for hx, hy in holes:
        line(hx, hy + s * 3, hx, y_line + s * 2, dash=True, w=0.2)
    for (a, _), (b, _) in zip(holes, holes[1:]):
        line(a, y_line, b, y_line)
        text((a + b) / 2, y_line - 1.2, "%.1f" % (b - a), 3.2 if b - a > 12 else 2.4)
    for hx, _ in holes:
        line(hx - 1.2, y_line + 1.2, hx + 1.2, y_line - 1.2, w=0.4)


def dim_v(ys, x_line, x_from):
    """Chain dimension along y at x_line, extension lines from x_from."""
    ys = sorted(ys)
    for y in ys:
        line(x_from, y, x_line + 2, y, dash=True, w=0.2)
        line(x_line - 1.2, y + 1.2, x_line + 1.2, y - 1.2, w=0.4)
    for a, b in zip(ys, ys[1:]):
        line(x_line, a, x_line, b)
        text(x_line - 1.2, (a + b) / 2, "%.1f" % (b - a), 3.2, rot=-90)


def switch(name, x, y, dash=False, upright=False):
    """Blue Sea m-Series, studs underneath on a horizontal line, or a vertical one when
    upright. Returns (left, right), or (top, bottom)."""
    w = 74.93
    body(name, x, y, w, w, "#9ccc9c", "", dash=dash)
    cx, cy = x + w / 2, y + w / 2
    circ(cx, cy, 24, "#c4e3c4")
    text(cx, cy + 1.5 if upright else y + 8.5, name, 4.2)   # clear of the bars on its studs
    for dx in (-27.625, 27.625):
        for dy in (-27.625, 27.625):
            screw(cx + dx, cy + dy)
    a, b = ((cx, cy - 22.25), (cx, cy + 22.25)) if upright else ((cx - 22.25, cy), (cx + 22.25, cy))
    for p in (a, b):
        stud(p[0], p[1], 10)
    return a, b


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


def class_t(cx, y_top):
    """Compact Class T holder, long axis vertical, hanging from the battery bar.
    Returns (top stud, bottom stud)."""
    cy = y_top + CT_STUDS / 2
    body("Class T", cx - 20.0, cy - 50.0, 40.0, 100.0, "#e8837a", "")
    rect(cx - 12.7, cy - 34.95, 25.4, 69.9, "#fde0dc")          # the fuse, 69.9 x 25.4 blades
    text(cx - 15.5, cy, "Class T", 4.2, rot=-90)
    top, bot = (cx, y_top), (cx, y_top + CT_STUDS)
    for p in (top, bot):
        stud(p[0], p[1], 10)
    return top, bot


def build():
    global BOARD_W, BATT, TOTAL_W
    # ---- positive boards -------------------------------------------------------------
    # Two boards, butted level with a small gap. The battery board carries the battery bar,
    # four ANL fuses hanging below it and the Class T upright at its left end. The
    # distribution board ends just past the spare hole; the unswitched bar runs on across
    # the seam to the Class T's lower stud, which is the feed.
    # On the distribution board, what a hand operates stands in two columns at the left
    # edge: breakers on the edge, lying on their sides with the input stud on the right and
    # the lead leaving the left edge; switches beside them. Fuses hang below the unswitched
    # bar to their right and their leads leave the bottom edge, so nothing is reached across.
    # Batteries run 1-4 left to right on the battery bar (+ takes off at the left, B1
    # nearest) and 4-1 on the negative board (shunt at its left, B4 nearest): the battery
    # nearest one takeoff is the farthest from the other.
    y_un = 92.0                           # unswitched bar
    col_a = 6.0                           # breakers, on the left edge
    col_b = col_a + BRK_L + 5.0           # switches, beside them
    ms_out, ms_in = switch("Master switch", col_b, y_un - 22.25 - 37.465, upright=True)
    dis_l, dis_r = switch("Service disconnect", col_b, y_un + 61.72 - 37.465, dash=True)
    hb_in, hb_out = breaker_side("House breaker", col_a, 3.0, "60 A house")
    ab_in, ab_out = breaker_side("Always-on breaker", col_a, y_un - BRK_DY - BRK_W / 2,
                                 "60 A always-on")    # input on the unswitched bar
    ib_in, ib_out = breaker_side("Inverter breaker", col_a, dis_l[1] - BRK_DY - BRK_W / 2,
                                 "inverter breaker (rating open)", dash=True)

    xf = [dis_r[0] + 37.85 + PITCH * i for i in range(4)]    # inverter fuse beside the disconnect
    specs = (("MultiPlus 12/500", True), ("Solar (planned, type open)", True),
             ("2nd charger (type open)", True), ("ANL 60 A  DC-DC", False))
    hung = [anl(("Inverter/charger fuse" if i == 0 else "Fuse %d" % (i + 1)), x, y_un - 26.29,
                lab, 57 if i == 0 else 78, dash=d)       # the inverter fuse has a link on its lower stud
            for i, (x, (lab, d)) in enumerate(zip(xf, specs))]
    inv = hung[0]
    x_sp = xf[-1] + 19.05 + SPARE / 2             # spare hole
    BOARD_W = -(-(x_sp + SPARE / 2) // 3.175) * 3.175      # up to the next 1/8 in
    BATT = (BOARD_W + GAP, 0.0, BATT[2], BATT[3])
    TOTAL_W = BATT[0] + BATT[2]
    shapes.insert(0, ("rect", 0, 0, BOARD_W, BOARD_H, "#f7f7f2", INK, False, 1.0))
    shapes.insert(1, ("rect", BATT[0], BATT[1], BATT[2], BATT[3], "#f7f7f2", INK, False, 1.0))
    shapes.insert(2, ("rect", NEG[0], NEG[1], NEG[2], NEG[3], "#f7f7f2", INK, False, 1.0))

    # battery board
    y_bt = y_un - CT_STUDS                # battery bar; the Class T's lower stud is on the unswitched bar
    x_ct = BATT[0] + 6.0 + 20.0
    ct_t, ct_b = class_t(x_ct, y_bt)
    batts = [anl("Battery ANL %d" % n, x_ct + PITCH * (i + 1), y_bt - 26.29,
                 "ANL  battery %d%s" % (n, "" if n < 3 else " (future)"), 78, dash=n >= 3)
             for i, n in enumerate((1, 2, 3, 4))]
    x_bb = ct_t[0] - 12.5
    bar("Battery + bar", x_bb, y_bt - BAR / 2, batts[-1][0][0] + 13.0 - x_bb, BAR,
        [(ct_t[0], y_bt, "Class T stud")] + [(b[0][0], y_bt, "fuse stud") for b in batts],
        "BATTERY + BAR", label_x=(batts[1][0][0] + batts[2][0][0]) / 2)

    x0 = ab_in[0] - 12.5
    bar("Unswitched + bar", x0, y_un - BAR / 2, ct_b[0] + 12.5 - x0, BAR,
        [(ab_in[0], y_un, "always-on breaker stud"), (ms_in[0], y_un, "master switch stud")]
        + [(h[0][0], y_un, "fuse stud") for h in hung]
        + [(x_sp, y_un, "spare"), (ct_b[0], y_un, "Class T lower stud, the feed")],
        "UNSWITCHED + BAR", label_x=(xf[0] + xf[1]) / 2)
    text(x_sp, y_un - 15.5, "spare", 3.8)
    bar("Link, house breaker to master switch", hb_in[0] - 10, (hb_in[1] + ms_out[1]) / 2 - 10,
        ms_out[0] - hb_in[0] + 20, 20,
        [(hb_in[0], hb_in[1], "breaker stud"), (ms_out[0], ms_out[1], "switch stud")], fill=LINK)
    bar("Link, service disconnect to inverter breaker", ib_in[0] - 10, ib_in[1] - 10,
        dis_l[0] - ib_in[0] + 20, 20,
        [(ib_in[0], ib_in[1], "breaker stud"), (dis_l[0], dis_l[1], "switch stud")], fill=LINK)
    bar("Link, inverter fuse to service disconnect", dis_r[0] - 12.5, inv[1][1] - 12.5,
        inv[1][0] - dis_r[0] + 25, BAR,
        [(dis_r[0], dis_r[1], "switch stud"), (inv[1][0], inv[1][1], "fuse stud")], fill=LINK)

    # hole spacing, from the boards' top-left corner
    dim_h([(0, 0), ab_in, ms_in] + [h[0] for h in hung] + [(x_sp, y_un), ct_b]
          + [b[0] for b in batts], -8)
    dim_v([0, y_bt, y_un, BATT[3]], TOTAL_W + 10, batts[-1][0][0] + 13.0)
    dim_v([0, hb_in[1], ms_out[1], y_un, dis_l[1], BOARD_H], -46, -40)

    # ---- negative board, below ---------------------------------------------------
    # The shunt stands upright at the left end and is the only bridge between the bars:
    # system stud on the returns bar, battery stud on the battery - bar.
    x_sh = NEG[0] + 52.0
    y_mid = NEG[1] + NEG[3] / 2
    y_rt, y_nb = y_mid - 27.5, y_mid + 27.5
    body("SmartShunt base", x_sh - 12.5, y_mid - 60, 25, 120, "#7fb3e6", "")
    body("SmartShunt housing", x_sh - 39.5, y_mid - 38, 27, 76, "#a9cdf0", "SmartShunt", rot=-90)
    screw(x_sh, y_mid - 50.5)
    screw(x_sh, y_mid + 50.5)
    neg = [x_sh + 30.0 + PITCH * k for k in range(4)]            # batteries 4, 3, 2, 1
    bar("Battery - bar", x_sh - 12.5, y_nb - BAR / 2, neg[-1] + 13.0 - (x_sh - 12.5), BAR,
        [(x_sh, y_nb, "shunt, battery side, M10")]
        + [(x, y_nb, "battery %d -, M8" % n) for n, x in zip((4, 3, 2, 1), neg)],
        "BATTERY - BAR", label_x=(neg[1] + neg[2]) / 2)
    names = ("inverter/charger -", "DC-DC -", "2nd charger -", "solar -", "house -", "always-on -")
    rts = [x_sh + 35.0 + 30.0 * k for k in range(len(names))]
    bar("Returns - bar", x_sh - 12.5, y_rt - BAR / 2, rts[-1] + 13.0 - (x_sh - 12.5), BAR,
        [(x_sh, y_rt, "shunt, system side, M10")]
        + [(x, y_rt, "%s, %s" % (n, "M8" if i < 4 else "M6")) for i, (x, n) in enumerate(zip(rts, names))])
    text(rts[2], y_rt + 19, "- BAR (returns)", 4.4)
    for y in (y_rt, y_nb):
        stud(x_sh, y, 10)
    for n, x in zip((4, 3, 2, 1), neg):
        stud(x, y_nb, 8)
        text(x, y_nb + 19, "B%d-" % n, 3.8)
    for i, (x, n) in enumerate(zip(rts, names)):
        stud(x, y_rt, 8 if i < 4 else 6)
        text(x + 2.0, y_rt - 15, n, 3.8, anchor="start", rot=-40)

    dim_h([(NEG[0], NEG[1] + NEG[3]), (x_sh, y_nb)] + [(x, y_nb) for x in neg], NEG[1] + NEG[3] + 8, below=True)
    dim_h([(x_sh, y_rt)] + [(x, y_rt) for x in rts], NEG[1] + NEG[3] + 20, below=True)

    # ---- leads and dimensions ---------------------------------------------------
    text(BOARD_W / 2, -20, "distribution board %.1f x %g, %g x %g in, from a 12 x 18 in sheet"
         % (BOARD_W, BOARD_H, BOARD_W / 25.4, BOARD_H / 25.4), 5)
    text(BATT[0] + BATT[2] / 2, -20, "battery board %g x %g, %g x %g in"
         % (BATT[2], BATT[3], BATT[2] / 25.4, BATT[3] / 25.4), 5)
    for n, b in zip((1, 2, 3, 4), batts):
        text(b[1][0], BATT[3] + 7, "B%d+" % n, 3.8)
    text(batts[1][0][0] + PITCH / 2, BATT[3] + 14, "battery + leads leave the bottom edge", 4.6)
    text(-3, hb_out[1] + 1.5, "house lead", 4.6, anchor="end")
    text(-3, ab_out[1] + 1.5, "always-on lead", 4.6, anchor="end")
    text(-3, ib_out[1] + 1.5, "inverter lead", 4.6, anchor="end")
    text((xf[0] + xf[3]) / 2, BOARD_H + 7, "unswitched leads leave the bottom edge", 4.6)
    text(NEG[0] + NEG[2] + 6, y_rt + 1.5, "returns leave the top edge", 4.6, anchor="start")
    text(NEG[0] + NEG[2] + 6, y_nb - 1, "battery - leads leave the bottom edge,", 4.6, anchor="start")
    text(NEG[0] + NEG[2] + 6, y_nb + 5.5, "order mirrored from +: B4 nearest the shunt", 4.6, anchor="start")
    text(NEG[0] + NEG[2] / 2, NEG[1] - 5, "negative board %g x %g, its own piece" % (NEG[2], NEG[3]), 5)


def on_a_board(x, y, w, h):
    return any(bx <= x and by <= y and x + w <= bx + bw and y + h <= by + bh
               for bx, by, bw, bh in ((0, 0, BOARD_W, BOARD_H), BATT, NEG))


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
        across = 0 <= x and x + w <= TOTAL_W and 0 <= y and y + h <= BATT[3]   # over the butted seam
        if not (on_a_board(x, y, w, h) or across):
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
    ox, oy = 60, 32
    tab_y = NEG[1] + NEG[3] + 36
    rows, parts = drill_rows(), PARTS
    total_h = oy + tab_y + 9 + 6.2 * (len(rows) + len(parts) + 5) + 8
    o = ["<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 %g %g' "
         "font-family='DejaVu Sans, Helvetica, Arial, sans-serif'>" % (TOTAL_W + 96, total_h),
         "<rect width='100%' height='100%' fill='#ffffff'/>", "<g transform='translate(%g,%g)'>" % (ox, oy)]
    for s in shapes:
        if s[0] == "rect":
            _, x, y, w, h, fill, stroke, dash, op = s
            o.append("<rect x='%.2f' y='%.2f' width='%.2f' height='%.2f' fill='%s' stroke='%s' "
                     "stroke-width='0.5' fill-opacity='%g'%s/>"
                     % (x, y, w, h, fill, stroke, op, " stroke-dasharray='3 2'" if dash else ""))
        elif s[0] == "line":
            _, x1, y1, x2, y2, color, dash, w = s
            o.append("<line x1='%.2f' y1='%.2f' x2='%.2f' y2='%.2f' stroke='%s' stroke-width='%g'%s/>"
                     % (x1, y1, x2, y2, color, w, " stroke-dasharray='2 1.5'" if dash else ""))
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
        if s[0] == "line":
            _, x1, y1, x2, y2, color, dash, w = s
            cells.append("<mxCell id=\"%s\" style=\"endArrow=none;html=1;strokeColor=%s;strokeWidth=%g;%s\" "
                         "edge=\"1\" parent=\"1\"><mxGeometry relative=\"1\" as=\"geometry\">"
                         "<mxPoint x=\"%.2f\" y=\"%.2f\" as=\"sourcePoint\"/>"
                         "<mxPoint x=\"%.2f\" y=\"%.2f\" as=\"targetPoint\"/></mxGeometry></mxCell>"
                         % (cid, color, w, "dashed=1;" if dash else "", x1 + 40, y1 + 40, x2 + 40, y2 + 40))
            continue
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
