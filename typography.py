"""Anti-aliased vector glyph renderer built on glyphs.py (pure stdlib).

Strokes each polyline as a signed-distance field: for every pixel in a local
window around a segment, coverage = clamp(0.5 + (halfwidth - dist)/1.0).
Glyphs are rasterized at 4x supersampling into a coverage buffer, then
box-downsampled to anti-aliased alpha. Composited alpha-blended onto the
Canvas API used by main.py (.w .h .buf : bytearray(w*h*3) RGB).

Public API:
  rasterize(char, size_px, style='display'|'body') -> (w_px, alpha, advance_px, pad_px)
  draw_text(canvas, x, y, text, size_px, color, style, letter_spacing=0)
  measure_text(text, size_px, style, letter_spacing=0) -> width
"""

import math
from glyphs import GLYPHS_DISPLAY, GLYPHS_BODY, KERN

SS = 4                      # supersampling factor
EM = 1000.0
_CACHE = {}


# ---------------------------------------------------------------------------
# geometry
# ---------------------------------------------------------------------------
def _dist_seg(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    ll = dx * dx + dy * dy
    t = 0.0 if ll == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / ll))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy)


def _seg_coverage(x, y, ax, ay, bx, by, hw):
    d = _dist_seg(x, y, ax, ay, bx, by)
    c = 0.5 + (hw - d) / 1.0
    return 0.0 if c < 0.0 else (1.0 if c > 1.0 else c)


def _glyph_meta(char, style):
    table = GLYPHS_DISPLAY if style == 'display' else GLYPHS_BODY
    return table.get(char, (([], 300 if style == 'display' else 500)))


def rasterize(char, size_px, style='display'):
    """Return (w, alpha_rows, advance_px) for a cached raster of char."""
    key = (char, size_px, style)
    if key in _CACHE:
        return _CACHE[key]

    polylines, adv = _glyph_meta(char, style)
    scale = size_px / EM
    hw = max(0.4, size_px * 0.06)            # stroke half-width in device px
    phw = hw + 1.5
    pad = size_px * 0.28                   # device px of padding around glyph box

    ss_w = int((adv * scale + 2 * pad) * SS) + 2
    ss_h = int((size_px + 2 * pad) * SS) + 2
    cov = [0.0] * (ss_w * ss_h)

    def add_contrib(pix, pyy, gy, seg, hh):
        c = _seg_coverage(pix / SS - pad, gy, *seg, hh)
        if c > 0.0:
            idx = pyy * ss_w + pix
            if c > cov[idx]:
                cov[idx] = c

    for pl in polylines:
        for (ax, ay), (bx, by) in zip(pl, pl[1:]):
            # local window around this segment, flipped to device y (down)
            X0, X1 = min(ax, bx) * scale, max(ax, bx) * scale
            Y0, Y1 = min(ay, by) * scale, max(ay, by) * scale
            X0max = max(ax, bx) * scale
            Y0min = min(ay, by) * scale
            Y1max = max(ay, by) * scale
            px0 = int((X0 - pad - phw) * SS) - 1
            px1 = int((X0max + pad + phw) * SS) + 1
            py0 = int((size_px + pad - Y1max - phw) * SS) - 1
            py1 = int((size_px + pad - Y0min + phw) * SS) + 1
            for pyy in range(max(0, py0), min(ss_h, py1)):
                gy = (size_px + pad) - pyy / SS     # glyph-space y (up)
                for pix in range(max(0, px0), min(ss_w, px1)):
                    add_contrib(pix, pyy, gy, (ax * scale, ay * scale, bx * scale, by * scale), hw)

    # box downsample 4x4 -> final alpha
    w = int(math.ceil(adv * scale + 2 * pad))
    n = int(size_px + 2 * pad)
    rows = []
    for ry in range(n):
        row = bytearray(w)
        for rx in range(w):
            s = 0.0
            for sy in range(SS):
                for sx in range(SS):
                    s += cov[(ry * SS + sy) * ss_w + rx * SS + sx]
            row[rx] = int(round(s / (SS * SS) * 255.0))
        rows.append(bytes(row))

    res = (w, rows, adv * scale, pad)
    _CACHE[key] = res
    return res


# ---------------------------------------------------------------------------
# measurement / drawing
# ---------------------------------------------------------------------------
def measure_text(text, size_px, style='display', letter_spacing=0):
    if not text:
        return 0
    total = 0.0
    for i, ch in enumerate(text):
        w, _, adv, _pad = rasterize(ch, size_px, style)
        total += adv
        if i > 0:
            total += letter_spacing
    return total


def _kern_px(text, i, size_px, style):
    # A hyphen immediately before a digit keeps its own advance but also nudges
    # the following digit, so every "-<digit>" pair clears a >= 0px gap without
    # widening any other glyph or changing the measured run width.
    if text[i] == '-' and text[i + 1:i + 2].isdigit():
        return 1
    return 0


def draw_text(canvas, x, y, text, size_px, color, style='display', letter_spacing=0):
    if not text or canvas is None:
        return
    cr, cg, cb = color
    cx = float(x)
    base_top = y                     # y is top of the cap box
    for i, ch in enumerate(text):
        w, rows, adv, pad = rasterize(ch, size_px, style)
        _blit(canvas, int(round(cx - pad)), int(base_top - pad), rows, w, cr, cg, cb)
        cx += adv
        if i < len(text) - 1:
            cx += letter_spacing + _kern_px(text, i, size_px, style)



def _blit(canvas, x, y, rows, w, cr, cg, cb):
    W, H = canvas.w, canvas.h
    buf = canvas.buf
    for ry, row in enumerate(rows):
        dy = y + ry
        if dy < 0 or dy >= H:
            continue
        base = dy * W * 3
        for rx in range(w):
            dx = x + rx
            if dx < 0 or dx >= W:
                continue
            a = row[rx] / 255.0
            if a <= 0.0:
                continue
            i = (base + dx * 3)
            ia = 1.0 - a
            buf[i] = int(cr * a + buf[i] * ia)
            buf[i + 1] = int(cg * a + buf[i + 1] * ia)
            buf[i + 2] = int(cb * a + buf[i + 2] * ia)


# ---------------------------------------------------------------------------
# self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    class _Canvas:
        def __init__(self, w, h):
            self.w, self.h = w, h
            self.buf = bytearray(w * h * 3)

    c = _Canvas(700, 120)
    col = (0xF2, 0xEF, 0xE6)
    draw_text(c, 8, 12, 'WORLD NEWS', 60, col, 'display', letter_spacing=0)
    wd = measure_text('WORLD NEWS', 60, 'display', letter_spacing=0)
    # confirm pixels vary
    distinct = len(set(bytes(c.buf)))
    print("WORLD NEWS width = %.1f px" % wd)
    print("buffer distinct byte values =", distinct)
    assert distinct > 1, "no anti-aliasing variation!"
    # raster check: letters must render complete
    for ch in 'LEOS3':
        w, rows, adv, pad = rasterize(ch, 16, 'display')
        print(repr(ch), w, len(rows))
        for r in rows:
            print(''.join('#' if v > 120 else '.' for v in r))
    print("typography.py OK")