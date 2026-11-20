from typography import rasterize

for thr in [120, 160, 200, 230]:
    c = Canvas = None
    print("--- alpha>=", thr)
    ink = []
    for ch in "TH":
        w, rows, adv, pad = rasterize(ch, 54, "display")
        cols = [rx for rx in range(w) if any(row[rx] >= thr for row in rows)]
        bx = round(54*0.28)  # not used
    # do it properly
    for ch in "TH":
        w, rows, adv, pad = rasterize(ch, 54, "display")
        cols = [rx for rx in range(w) if any(row[rx] >= thr for row in rows)]
        if cols:
            bx = round(-pad)  # relative
            # first char at origin: oncanvas = cols - pad
            print("   %s solid cols [%d..%d] (oncanvas rel to origin)" % (ch, min(cols)-pad, max(cols)-pad))
        else:
            print("   %s no solid cols" % ch)
