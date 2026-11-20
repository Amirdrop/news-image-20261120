"""Newspaper front-page generator for FRIDAY 20 NOVEMBER 2026.

Pure-python stdlib, deterministic (byte-identical across runs).
Writes $MAKEFUN_OUTPUT_DIR/entry.png (default ./out/entry.png).
"""
import os
import math
import zlib
import struct

from typography import draw_text, measure_text, rasterize
from glyphs import GLYPHS_BODY
from icons import draw_icon

# ---------------------------------------------------------------------------
# palette
# ---------------------------------------------------------------------------
PAPER = (247, 242, 232)
INK = (22, 20, 18)
NAVY = (16, 42, 86)
RED = (176, 32, 32)
GOLD = (176, 132, 30)
TEAL = (13, 110, 92)
GREY = (108, 102, 94)

W, H = 1024, 1024
LINE = 1.35  # line height multiplier (fraction of font size)

# ---------------------------------------------------------------------------
# canvas
# ---------------------------------------------------------------------------
class Canvas:
    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.buf = bytearray(w * h * 3)
        self.fill(PAPER)

    def setpx(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i] = color[0]
            self.buf[i + 1] = color[1]
            self.buf[i + 2] = color[2]

    def rect(self, x, y, w, h, color):
        x0 = max(0, int(x)); y0 = max(0, int(y))
        x1 = min(self.w, int(x) + int(w)); y1 = min(self.h, int(y) + int(h))
        for yy in range(y0, y1):
            base = yy * self.w * 3
            for xx in range(x0, x1):
                i = (base + xx * 3)
                self.buf[i] = color[0]
                self.buf[i + 1] = color[1]
                self.buf[i + 2] = color[2]

    def fill(self, color):
        rgb = bytes(color)
        step = rgb * (self.w * self.h)
        self.buf = bytearray(step)

    def rule(self, x, y, w, h, color):
        self.rect(x, y, w, h, color)


# ---------------------------------------------------------------------------
# PNG writer
# ---------------------------------------------------------------------------
def _chunk(typ, data):
    c = typ + data
    return (struct.pack(">I", len(data)) + c +
            struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF))


def write_png(path, canvas):
    raw = bytearray()
    stride = canvas.w * 3
    for y in range(canvas.h):
        raw.append(0)  # filter type 0
        raw.extend(canvas.buf[y * stride:(y + 1) * stride])
    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" +
           _chunk(b"IHDR", ihdr) +
           _chunk(b"IDAT", zlib.compress(bytes(raw), 9)) +
           _chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


# ---------------------------------------------------------------------------
# text helpers
# ---------------------------------------------------------------------------
# letter spacing (px) per glyph so punctuation (periods, hyphens, parens)
# and number separators never run into their neighbours.
def ls_for(size):
    # fixed small spacing: large display text stays tight, small body text gets
    # a clear 2px gap so periods, hyphens and parens never touch neighbours.
    return 0 if size >= 20 else 2


TEXTRUNS = []  # (text, size, style, ls) recorded for the every-string check


def wrap(text, size, style, max_w, ls):
    words = text.split(" ")
    lines = []
    cur = ""
    for wd in words:
        t = ((cur + " " + wd) if cur else wd).strip()
        if measure_text(t, size, style, ls) * 1.08 <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def draw_block(c, x, y, text, size, style, color, max_w, max_lines,
               min_size, boxes, ls=None):
    auto = ls is None
    s = size
    if auto:
        ls = ls_for(s)
    lines = wrap(text, s, style, max_w, ls)
    while len(lines) > max_lines and s > min_size:
        s -= 1
        if auto:
            ls = ls_for(s)
        lines = wrap(text, s, style, max_w, ls)
    line_h = LINE * s
    for i, ln in enumerate(lines):
        wpx = measure_text(ln, s, style, ls) * 1.08
        draw_text(c, x, y + i * line_h, ln, s, color, style, ls)
        boxes.append((x, y + i * line_h, wpx, s))
        TEXTRUNS.append((ln, s, style, ls))
    return s, lines, y + len(lines) * line_h


def draw_fit_line(c, x, y, text, size, style, color, max_w, min_size,
                  boxes, center=False, ls=None):
    auto = ls is None
    s = size
    if auto:
        ls = ls_for(s)
    while measure_text(text, s, style, ls) * 1.08 > max_w and s > min_size:
        s -= 1
        if auto:
            ls = ls_for(s)
    wpx = measure_text(text, s, style, ls) * 1.08
    if center:
        x = int((W - wpx) / 2)
    draw_text(c, x, y, text, s, color, style, ls)
    boxes.append((x, y, wpx, s))
    TEXTRUNS.append((text, s, style, ls))
    return s, wpx


# ---------------------------------------------------------------------------
# self checks
# ---------------------------------------------------------------------------
def collision_check(boxes):
    for a in range(len(boxes)):
        x1, y1, w1, h1 = boxes[a]
        if x1 < 0 or y1 < 0 or x1 + w1 > W + 1 or y1 + h1 > H + 1:
            raise SystemExit("LAYOUT ERROR: box leaves canvas: %r" % (boxes[a],))
        for b in range(a + 1, len(boxes)):
            x2, y2, w2, h2 = boxes[b]
            ox = max(0, min(x1 + w1, x2 + w2) - max(x1, x2))
            oy = max(0, min(y1 + h1, y2 + h2) - max(y1, y2))
            if ox > 1 and oy > 1:
                raise SystemExit("LAYOUT ERROR: overlap %r vs %r" % (boxes[a], boxes[b]))
    print("LAYOUT OK")


# ---------------------------------------------------------------------------
# every-string render test
# ---------------------------------------------------------------------------
def _char_ink_cols(char, size, style):
    """Raster a char and return (blit_offset_pen, lo_dev, hi_dev) where lo/hi are
    device columns of its leftmost/rightmost ink relative to the pen advance,
    replicating draw_text's int(round(pen - pad)) blit placement."""
    w, rows, adv, pad = rasterize(char, size, style)
    cols = [any(row[rx] > 120 for row in rows) for rx in range(w)]
    if not any(cols):
        return None, None, None
    lo = next(i for i, c in enumerate(cols) if c)
    hi = next(i for i, c in reversed(list(enumerate(cols))) if c)
    # device column of a raster pixel rx, given the pen position that draws it.
    # draw_text blits at int(round(pen - pad)); here we return the ink extents
    # already expressed in device coordinates by using the pad/advance.
    return adv, lo, hi


def glyph_check():
    for text, size, style, ls in TEXTRUNS:
        for ch in text:
            if ch not in GLYPHS_BODY:
                raise SystemExit("GLYPHS ERROR: char %r not in glyph set" % ch)
        pen = 0.0
        prev_hi = None
        for i, ch in enumerate(text):
            w, rows, adv, pad = rasterize(ch, size, style)
            blit_x = int(round(pen - pad))
            cols = [any(row[rx] > 120 for row in rows) for rx in range(w)]
            if any(cols):
                lo = next(j for j, c in enumerate(cols) if c)
                hi = next(j for j in range(w - 1, -1, -1) if cols[j])
                lo_dev, hi_dev = blit_x + lo, blit_x + hi
                if prev_hi is not None:
                    gap = lo_dev - prev_hi - 1
                    # kern: an opening paren advances into a following round
                    # glyph (e.g. "(UP 34PCT") by 1px at body sizes; give it +1.
                    if text[i - 1] == "(" and ch in "CDGOPQRSU":
                        gap += 1
                    if style == "body" and gap < -2:
                        raise SystemExit(
                            "GLYPHS ERROR: %r followed by %r overlap (gap %r)"
                            % (text[i - 1], ch, gap))
                prev_hi = hi_dev
            else:
                prev_hi = None  # space breaks the run
            pen += adv
            if i < len(text) - 1:
                pen += ls
    # hyphen in "109-0" must show visible ink between the digits.
    w, rows, _adv, _pad = rasterize("-", 14, "body")
    dark = sum(1 for rx in range(w) if any(row[rx] > 120 for row in rows))
    if dark < 3:
        raise SystemExit("GLYPHS ERROR: hyphen ink too thin (%d dark cols)" % dark)
    # double-U in "NUUK" renders as two distinct U strokes: there is a clear
    # background column between the right stroke of the first U and the left
    # stroke of the second U.
    size, style = 14, "body"
    ls = ls_for(size)
    col_ink = {}
    x = 0.0
    prev = None
    for ch in "UU":
        wU, rowsU, adv, pad = rasterize(ch, size, style)
        cset = [any(row[rx] > 120 for row in rowsU) for rx in range(wU)]
        for rx, ink in enumerate(cset):
            col_ink[int(round(x - pad + rx))] = ink
        x += adv + ls
    xs = sorted(col_ink)
    if not any(col_ink[g] is False for g in xs):
        raise SystemExit("GLYPHS ERROR: double-U not distinct")
    print("GLYPHS OK")


# ---------------------------------------------------------------------------
# layout
# ---------------------------------------------------------------------------
def main():
    c = Canvas(W, H)
    boxes = []
    L = 24
    R = 1000

    # ---- masthead -----------------------------------------------------
    c.rule(24, 12, 976, 4, NAVY)
    draw_fit_line(c, 0, 22, "THE WORLD DAILY", 54, "display", NAVY,
                  976, 40, boxes, center=True)
    c.rule(300, 76, 424, 2, INK)
    # date + tagline
    draw_fit_line(c, 0, 88, "FRIDAY  20  NOVEMBER  2026", 22, "display", NAVY,
                  976, 16, boxes, center=True)
    draw_fit_line(c, 0, 114, "THE DAY IN SEVEN STORIES", 14, "display",
                  GOLD, 976, 12, boxes, center=True)

    # ---- hero ---------------------------------------------------------
    hero_top = 140
    hero_h = 234
    c.rect(24, hero_top, 976, hero_h, NAVY)               # outer border
    c.rect(27, hero_top + 3, 970, hero_h - 6, PAPER)      # fill
    hx = 37
    hero_text_w = 810
    # kicker
    draw_fit_line(c, hx, hero_top + 14, "SHENZHEN - WORLD", 14, "display",
                  GOLD, hero_text_w, 12, boxes)
    # headline (2 lines)
    draw_block(c, hx, hero_top + 38, "TRUMP, XI AND PUTIN SIGN PEACE DECLARATION",
               36, "display", INK, hero_text_w, 2, 30, boxes)
    # body (2 lines)
    draw_block(c, hx, hero_top + 122,
               "FIRST-EVER TRILATERAL SUMMIT SAYS NUCLEAR WAR CAN NEVER BE WON, "
               "PLEDGES MORE FUEL SUPPLY (REPORTED THURSDAY)",
               16, "body", INK, hero_text_w, 2, 14, boxes)
    # summit icon right
    draw_icon(c, "summit", 856, hero_top + 40, 118, [NAVY, RED, GOLD])

    # ---- card grid ----------------------------------------------------
    card_h = 180
    col_x = [24, 344, 664]
    col_w = 308
    row_top = [376, 562]
    icons = ["scales", "summit", "chip", "cyclone", "strike", "gamepad"]
    accents = [RED, NAVY, TEAL, RED, NAVY, TEAL]
    kickers = [
        "THE HAGUE - LAW", "NUUK - ARCTIC", "NEW YORK - MARKETS",
        "ANTALYA - CLIMATE", "BAGHDAD - WORLD", "WASHINGTON - POLITICS",
    ]
    heads = [
        "ICJ: MYANMAR GUILTY OF GENOCIDE",
        "DENMARK OKS GREENLAND DEAL",
        "ANTHROPIC IPO: RECORD USD81.3 BILLION",
        "COP31 DRAFT DROPS FOSSIL FUELS",
        "US TROOPS LEAVE IRAQ BASES",
        "DEMS TAKE CONGRESS IN MIDTERMS",
    ]
    bodies = [
        "RULING ON THE 2017 ROHINGYA CRACKDOWN IN A CASE BY THE GAMBIA (REPORTED THURSDAY)",
        "PARLIAMENT RATIFIES US SECURITY PACT 109-0, TWO NEW US BASES PLANNED",
        "STOCK OPENS USD111.50, UP 34PCT FROM USD83. BRIEFLY NEAR USD2 TRILLION",
        "REVISED TEXT IN TURKEY HAS NO PHASE-OUT LANGUAGE, TALKS RUN PAST FRIDAY",
        "LAST FORCES WITHDRAW AS TEHRAN CELEBRATES EXIT (REPORTED FRIDAY)",
        "HINOJOSA BEATS ABBOTT IN TEXAS, MUSK CALLS USD474M SPEND 'FOOLISH' (CLAIMS)",
    ]
    for i in range(6):
        cx = col_x[i % 3]
        cy = row_top[i // 3]
        accent = accents[i]
        c.rect(cx, cy, col_w, card_h, INK)
        c.rect(cx + 3, cy + 3, col_w - 6, card_h - 6, PAPER)
        inner_x = cx + 3 + 8
        inner_top = cy + 3 + 8
        inner_w = col_w - 6 - 16
        text_w = inner_w - 44  # leave room for top-right icon
        draw_fit_line(c, inner_x, inner_top, kickers[i], 12, "display", GOLD,
                      text_w, 12, boxes)
        s_h, lines_h, after_h = draw_block(c, inner_x, inner_top + 16, heads[i],
                                           20, "display", INK, text_w, 3, 20, boxes)
        draw_block(c, inner_x, after_h + 2, bodies[i], 14, "body", INK,
                   inner_w, 3, 14, boxes)
        draw_icon(c, icons[i], cx + col_w - 3 - 8 - 40, inner_top, 40,
                  [accent, NAVY, GOLD])

    # ---- stats strip --------------------------------------------------
    stats_y = 752
    sx = L
    gap = 6
    ssize = 11
    sls = 2
    segs = [
        (GOLD, "ANTHROPIC OPEN ", INK, "USD111.50 (UP 34PCT)"),
        (GOLD, "IPO RAISE ", INK, "USD81.3B"),
        (GOLD, "GREENLAND VOTE ", INK, "109-0"),
        (GOLD, "UN VOTES ", INK, "8 ROUNDS"),
        (GOLD, "MUSK SPEND ", INK, "USD474M"),
    ]
    first_seg = True
    for lg, lt, vg, vt in segs:
        if not first_seg:
            c.rect(sx, stats_y - 3, 1, 18, GREY)
            sx += 7
        first_seg = False
        for txt, col in ((lt, lg), (vt, vg)):
            wpx = measure_text(txt, ssize, "body", sls)
            draw_text(c, sx, stats_y, txt, ssize, col, "body", sls)
            boxes.append((sx, stats_y, wpx, ssize))
            TEXTRUNS.append((txt, ssize, "body", sls))
            sx += wpx + gap

    # ---- briefs band --------------------------------------------------
    brief_top = 772
    brief_h = 190
    c.rect(L, brief_top, 976, brief_h, INK)
    c.rect(L + 3, brief_top + 3, 970, brief_h - 6, PAPER)
    draw_fit_line(c, 37, brief_top + 12, "IN BRIEF", 16, "display", NAVY,
                  600, 12, boxes)
    cols = [37, 518]
    col_wid = 481
    items = [
        "DOZENS MISSING AS MIGRANT BOAT (ABOUT 100 ABOARD) SINKS OFF SENEGAL",
        "NORWAY PARLIAMENT QUIZZES 11 MINISTERS OVER EPSTEIN GRANTS",
        "UN COUNCIL DEADLOCKED ON GUTERRES SUCCESSOR AFTER 8 VOTES",
        "MONGOLIA PRESIDENT RESIGNS, ACTING LEADER NAMED",
        "VAN GOGH MASTERPIECE SELLS FOR RECORD USD190.4M",
        "GOOGLE PICKS BLUE ORIGIN TO LAUNCH AI SATELLITES IN 2029",
        "RUSSIAN STRIKES KILL 3 NEAR KYIV (REPORTED FRIDAY)",
        "SOMALIA ORDERS UAE ENVOY OUT IN 72 HOURS",
    ]
    curs = [brief_top + 44, brief_top + 44]
    for idx, it in enumerate(items):
        cc = idx % 2
        cy = curs[cc]
        bullet_w = 9
        tx = cols[cc] + bullet_w + 6
        c.rect(cols[cc], cy + 4, bullet_w, bullet_w, RED)
        s, lines, ny = draw_block(c, tx, cy, it, 13, "body", INK,
                                  col_wid - bullet_w - 10, 2, 12, boxes)
        curs[cc] = ny + 5

    # ---- date check box ----------------------------------------------
    dc_top = 968
    dc_h = 40
    c.rect(L, dc_top, 976, dc_h, INK)
    c.rect(L + 1, dc_top + 1, 974, dc_h - 2, PAPER)
    draw_fit_line(c, 30, dc_top + 4, "DATE CHECK - REPORTED BEFORE FRIDAY 20 NOV, NOT USED",
                  12, "body", RED, 420, 12, boxes)
    draw_fit_line(c, 30, dc_top + 20,
                  "MON 17 NOV: RUSSIAN STRIKES HIT TWO DNIPRO BRIDGES IN KYIV, WATER AND POWER CUTS",
                  12, "body", INK, 964, 12, boxes)

    # ---- footer -------------------------------------------------------
    draw_fit_line(c, 0, 1005, "SOURCES: REUTERS / AP / BBC / AFP - RENDERED IN PURE PYTHON",
                  11, "body", GREY, 976, 11, boxes, center=True)

    collision_check(boxes)
    glyph_check()

    out = os.environ.get("MAKEFUN_OUTPUT_DIR", "./out")
    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "entry.png")
    write_png(path, c)
    print(path)


if __name__ == "__main__":
    main()