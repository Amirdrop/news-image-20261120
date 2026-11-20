#!/usr/bin/env python3
"""Thick-stroke flat vector icon library, stdlib only.

Icons are drawn inside a square box (x, y, size).  Geometry is given on a
0..100 unit square (y down) and mapped as  X = x + u*size/100, so an icon
never exceeds its box.  Every primitive is built from the Canvas.rect op.
"""

import math

# ---------------------------------------------------------------------------
# Primitives (all built from Canvas.rect, the only available op)
# ---------------------------------------------------------------------------

def _disc(c, cx, cy, r, color):
    """Filled circle: scan the bbox rows, stamp one rect per row."""
    r = max(0, r)
    top = int(math.floor(cy - r))
    bot = int(math.floor(cy + r))
    for yy in range(top, bot + 1):
        dy = yy - cy
        half = math.sqrt(max(0, r * r - dy * dy))
        x0 = int(math.floor(cx - half))
        x1 = int(math.floor(cx + half))
        if x1 >= x0:
            c.rect(x0, yy, x1 - x0 + 1, 1, color)


def _ring(c, cx, cy, r, w, color):
    """Annulus: same row-scan, only keep the band within [r-w/2, r+w/2]."""
    r = max(0, r)
    hw = w / 2.0
    top = int(math.floor(cy - r - hw))
    bot = int(math.floor(cy + r + hw))
    for yy in range(top, bot + 1):
        dy = yy - cy
        d2 = r * r - dy * dy
        if d2 < 0:
            continue
        d = math.sqrt(d2)
        # outer reach
        xo0 = int(math.floor(cx - d - hw))
        xo1 = int(math.floor(cx + d + hw))
        # inner reach (the hole)
        lo = max(0, (r - hw) ** 2 - dy * dy)
        hi = (r + hw) ** 2 - dy * dy
        # find x extent of the band per row by walking the outer span once.
        lo_i = None
        hi_i = None
        for xx in range(xo0, xo1 + 1):
            dd = math.hypot(xx - cx, dy)
            if abs(dd - r) <= hw:
                if lo_i is None:
                    lo_i = xx
                hi_i = xx
        if lo_i is not None:
            c.rect(lo_i, yy, hi_i - lo_i + 1, 1, color)


def _seg(c, x1, y1, x2, y2, w, color):
    """Thick straight line by stamping discs along the segment."""
    dx = x2 - x1
    dy = y2 - y1
    length = max(1.0, math.hypot(dx, dy))
    r = w / 2.0
    n = int(math.ceil(length))
    for i in range(n + 1):
        t = i / n
        _disc(c, x1 + t * dx, y1 + t * dy, r, color)


def _poly(c, pts, w, color):
    """Thick polyline: _seg per consecutive pair + a disc at every joint."""
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        _seg(c, x1, y1, x2, y2, w, color)
    for px, py in pts:
        _disc(c, px, py, w / 2.0, color)


# ---------------------------------------------------------------------------
# Icon library  (geometry in 0..100 units, v down)
# ---------------------------------------------------------------------------

def _masthead(c, x, y, s, clr):
    p, sec, acc = clr[0], clr[1], clr[2]
    u = s / 100.0
    _ring(c, x + 24 * u, y + 52 * u, 20 * u, 8 * u, p)
    _seg(c, x + 48 * u, y + 52 * u, x + 88 * u, y + 52 * u, 14 * u, sec)
    _disc(c, x + 78 * u, y + 24 * u, 7 * u, p)


def _summit(c, x, y, s, clr):
    p, sec, acc = clr[0], clr[1], clr[2]
    u = s / 100.0
    _disc(c, x + 32 * u, y + 26 * u, 10 * u, sec)
    _disc(c, x + 68 * u, y + 26 * u, 10 * u, sec)
    _seg(c, x + 32 * u, y + 42 * u, x + 32 * u, y + 62 * u, 8 * u, sec)
    _seg(c, x + 32 * u, y + 48 * u, x + 50 * u, y + 60 * u, 8 * u, p)
    _seg(c, x + 68 * u, y + 48 * u, x + 50 * u, y + 60 * u, 8 * u, p)
    _seg(c, x + 12 * u, y + 74 * u, x + 88 * u, y + 74 * u, 8 * u, acc)


def _tanker(c, x, y, s, clr):
    p, sec, acc = clr[0], clr[1], clr[2]
    u = s / 100.0
    _poly(c, [(x + 10 * u, y + 72 * u), (x + 18 * u, y + 84 * u),
              (x + 82 * u, y + 84 * u), (x + 90 * u, y + 72 * u)], 8 * u, sec)
    _seg(c, x + 10 * u, y + 72 * u, x + 90 * u, y + 72 * u, 8 * u, sec)
    _seg(c, x + 60 * u, y + 72 * u, x + 60 * u, y + 54 * u, 10 * u, p)
    _seg(c, x + 60 * u, y + 54 * u, x + 74 * u, y + 54 * u, 10 * u, p)
    _seg(c, x + 70 * u, y + 54 * u, x + 70 * u, y + 40 * u, 6 * u, acc)
    _seg(c, x + 6 * u, y + 92 * u, x + 28 * u, y + 92 * u, 5 * u, acc)
    _seg(c, x + 34 * u, y + 92 * u, x + 56 * u, y + 92 * u, 5 * u, acc)


def _scales(c, x, y, s, clr):
    p, sec, acc = clr[0], clr[1], clr[2]
    u = s / 100.0
    _seg(c, x + 50 * u, y + 14 * u, x + 50 * u, y + 70 * u, 9 * u, sec)
    _seg(c, x + 34 * u, y + 74 * u, x + 66 * u, y + 74 * u, 9 * u, sec)
    _seg(c, x + 16 * u, y + 24 * u, x + 84 * u, y + 24 * u, 9 * u, sec)
    _seg(c, x + 16 * u, y + 24 * u, x + 8 * u, y + 46 * u, 6 * u, p)
    _seg(c, x + 16 * u, y + 24 * u, x + 24 * u, y + 46 * u, 6 * u, p)
    _seg(c, x + 4 * u, y + 46 * u, x + 28 * u, y + 46 * u, 6 * u, p)
    _seg(c, x + 84 * u, y + 24 * u, x + 76 * u, y + 46 * u, 6 * u, p)
    _seg(c, x + 84 * u, y + 24 * u, x + 92 * u, y + 46 * u, 6 * u, p)
    _seg(c, x + 72 * u, y + 46 * u, x + 96 * u, y + 46 * u, 6 * u, p)
    _disc(c, x + 50 * u, y + 12 * u, 6 * u, acc)


def _strike(c, x, y, s, clr):
    p, sec, acc = clr[0], clr[1], clr[2]
    u = s / 100.0
    _poly(c, [(x + 10 * u, y + 74 * u), (x + 20 * u, y + 86 * u),
              (x + 60 * u, y + 86 * u), (x + 70 * u, y + 74 * u)], 7 * u, sec)
    _seg(c, x + 20 * u, y + 74 * u, x + 60 * u, y + 74 * u, 7 * u, sec)
    _seg(c, x + 22 * u, y + 90 * u, x + 88 * u, y + 16 * u, 12 * u, p)
    _seg(c, x + 88 * u, y + 16 * u, x + 72 * u, y + 20 * u, 10 * u, p)


def _chip(c, x, y, s, clr):
    p, sec, acc = clr[0], clr[1], clr[2]
    u = s / 100.0
    _poly(c, [(x + 30 * u, y + 30 * u), (x + 70 * u, y + 30 * u),
              (x + 70 * u, y + 70 * u), (x + 30 * u, y + 70 * u),
              (x + 30 * u, y + 30 * u)], 9 * u, sec)
    _disc(c, x + 50 * u, y + 50 * u, 11 * u, p)
    _seg(c, x + 50 * u, y + 18 * u, x + 50 * u, y + 30 * u, 7 * u, acc)
    _seg(c, x + 50 * u, y + 70 * u, x + 50 * u, y + 82 * u, 7 * u, acc)
    _seg(c, x + 18 * u, y + 50 * u, x + 30 * u, y + 50 * u, 7 * u, acc)
    _seg(c, x + 70 * u, y + 50 * u, x + 82 * u, y + 50 * u, 7 * u, acc)


def _cyclone(c, x, y, s, clr):
    p, sec, acc = clr[0], clr[1], clr[2]
    u = s / 100.0
    _poly(c, [(x + 62 * u, y + 40 * u), (x + 50 * u, y + 26 * u),
              (x + 30 * u, y + 30 * u), (x + 20 * u, y + 50 * u),
              (x + 32 * u, y + 68 * u), (x + 56 * u, y + 72 * u),
              (x + 74 * u, y + 60 * u), (x + 78 * u, y + 42 * u),
              (x + 64 * u, y + 30 * u)], 8 * u, p)
    _poly(c, [(x + 56 * u, y + 44 * u), (x + 44 * u, y + 40 * u),
              (x + 36 * u, y + 48 * u), (x + 40 * u, y + 60 * u),
              (x + 54 * u, y + 62 * u)], 6 * u, sec)
    _disc(c, x + 71 * u, y + 74 * u, 9 * u, acc)


def _gamepad(c, x, y, s, clr):
    p, sec, acc = clr[0], clr[1], clr[2]
    u = s / 100.0
    _poly(c, [(x + 12 * u, y + 42 * u), (x + 30 * u, y + 38 * u),
              (x + 70 * u, y + 38 * u), (x + 88 * u, y + 42 * u),
              (x + 92 * u, y + 60 * u), (x + 86 * u, y + 72 * u),
              (x + 74 * u, y + 70 * u), (x + 70 * u, y + 56 * u),
              (x + 30 * u, y + 56 * u), (x + 26 * u, y + 70 * u),
              (x + 14 * u, y + 72 * u), (x + 8 * u, y + 60 * u),
              (x + 12 * u, y + 42 * u)], 8 * u, sec)
    _seg(c, x + 24 * u, y + 47 * u, x + 40 * u, y + 47 * u, 7 * u, p)
    _seg(c, x + 32 * u, y + 39 * u, x + 32 * u, y + 55 * u, 7 * u, p)
    _disc(c, x + 68 * u, y + 45 * u, 5 * u, acc)
    _disc(c, x + 79 * u, y + 53 * u, 5 * u, acc)


def _cyber(c, x, y, s, clr):
    p, sec, acc = clr[0], clr[1], clr[2]
    u = s / 100.0
    _disc(c, x + 50 * u, y + 58 * u, 16 * u, sec)
    _disc(c, x + 50 * u, y + 34 * u, 8 * u, sec)
    _seg(c, x + 50 * u, y + 42 * u, x + 50 * u, y + 48 * u, 7 * u, sec)
    _seg(c, x + 34 * u, y + 50 * u, x + 18 * u, y + 40 * u, 6 * u, p)
    _seg(c, x + 34 * u, y + 58 * u, x + 16 * u, y + 58 * u, 6 * u, p)
    _seg(c, x + 34 * u, y + 66 * u, x + 18 * u, y + 76 * u, 6 * u, p)
    _seg(c, x + 66 * u, y + 50 * u, x + 82 * u, y + 40 * u, 6 * u, p)
    _seg(c, x + 66 * u, y + 58 * u, x + 84 * u, y + 58 * u, 6 * u, p)
    _seg(c, x + 66 * u, y + 66 * u, x + 82 * u, y + 76 * u, 6 * u, p)
    _seg(c, x + 38 * u, y + 30 * u, x + 30 * u, y + 18 * u, 5 * u, p)
    _seg(c, x + 62 * u, y + 30 * u, x + 70 * u, y + 18 * u, 5 * u, p)


# ---------------------------------------------------------------------------
# Registry + dispatcher
# ---------------------------------------------------------------------------

ICONS = {
    "masthead": _masthead,
    "summit": _summit,
    "tanker": _tanker,
    "scales": _scales,
    "strike": _strike,
    "chip": _chip,
    "cyclone": _cyclone,
    "gamepad": _gamepad,
    "cyber": _cyber,
}


def draw_icon(canvas, name, x, y, size, colors):
    """Draw icon `name` into its (x, y, size) box using the color palette.

    colors is a list [primary, secondary, accent]; missing entries fall back
    to (colors*3)[:3].
    """
    clr = (colors * 3)[:3]
    ICONS[name](canvas, int(x), int(y), size, clr)


# ---------------------------------------------------------------------------
# Smoke test: draw every icon into one row and save a PNG.
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import main as _main
    RED = (255, 61, 0)
    IVORY = (242, 239, 230)
    AMBER = (255, 212, 0)
    names = list(ICONS.keys())
    cw = 88
    gap = 24
    n = len(names)
    canvas = _main.Canvas(cw * n + gap * (n + 1), 100)
    x = gap
    for name in names:
        draw_icon(canvas, name, x, 0, 96, [RED, IVORY, AMBER])
        x += cw + gap
    _main.write_png("/tmp/icons_smoke.png", canvas)
    print("ok")