#!/usr/bin/env python3
"""Numbered contact sheets so Claude can look at many saved posts at once.

usage:
  contact_sheets.py WORK_DIR sample [N]        # N posts spread across the whole collection (default 240)
  contact_sheets.py WORK_DIR sort [--all]      # every post that has no category yet (--all: every post)
  contact_sheets.py WORK_DIR sort --only A2,Z   # only posts currently labelled with these codes (to re-sort them)

Writes WORK_DIR/sheets/<mode>-NNN.jpg plus WORK_DIR/sheets/<mode>-index.json:
  {"sheets": [{"file": "sort-001.jpg", "codes": ["Cx1..", ...]}, ...]}
Cell numbers on each sheet start at 1; cell k is codes[k-1].
"""
import json, os, random, sys
from PIL import Image, ImageDraw, ImageFont

COLS, ROWS, TW, TH, TXT = 8, 6, 150, 188, 40

def font(size, bold=False):
    names = ["DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", "Arial Bold.ttf" if bold else "Arial.ttf", "arialbd.ttf" if bold else "arial.ttf"]
    dirs = ["/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/TTF", "/Library/Fonts", "C:/Windows/Fonts", ""]
    for d in dirs:
        for n in names:
            try:
                return ImageFont.truetype(os.path.join(d, n) if d else n, size)
            except Exception:
                pass
    return ImageFont.load_default()

def fit(draw, text, f, w):
    if draw.textlength(text, font=f) <= w:
        return text
    while text and draw.textlength(text + "…", font=f) > w:
        text = text[:-1]
    return text + "…"

def sheet(work, codes, posts, path):
    fb, fr = font(13, True), font(11)
    im = Image.new("RGB", (COLS * TW, ROWS * (TH + TXT)), "white")
    d = ImageDraw.Draw(im)
    for k, code in enumerate(codes):
        x, y = (k % COLS) * TW, (k // COLS) * (TH + TXT)
        p = posts[code]
        tp = os.path.join(work, "thumbs", code + ".jpg")
        if os.path.exists(tp):
            im.paste(Image.open(tp).convert("RGB").resize((TW - 4, TH - 4)), (x + 2, y + 2))
        else:
            d.rectangle([x + 2, y + 2, x + TW - 3, y + TH - 3], fill="#ddd")
        d.rectangle([x + 2, y + 2, x + 30, y + 20], fill="black")
        d.text((x + 5, y + 4), str(k + 1), fill="white", font=fb)
        who = "@" + p["user"] if p.get("user") else (p.get("kind") or "")
        d.text((x + 3, y + TH), fit(d, who, fb, TW - 6), fill="black", font=fb)
        cap = " ".join((p.get("cap") or p.get("alt") or "").split())
        d.text((x + 3, y + TH + 18), fit(d, cap, fr, TW - 6), fill="#444", font=fr)
    im.save(path, quality=82)

def main():
    if len(sys.argv) < 3 or sys.argv[2] not in ("sample", "sort"):
        sys.exit(__doc__)
    work, mode = sys.argv[1], sys.argv[2]
    posts_l = json.load(open(os.path.join(work, "posts.json"), encoding="utf-8"))
    posts = {p["code"]: p for p in posts_l}
    if mode == "sample":
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 240
        pool = [p["code"] for p in posts_l if p.get("thumb")]
        step = max(1, len(pool) // n)
        pick = [random.Random(k).choice(pool[k:k + step]) for k in range(0, len(pool), step)][:n]
    else:
        lab = {}
        lp = os.path.join(work, "labels.json")
        if os.path.exists(lp) and "--all" not in sys.argv:
            lab = json.load(open(lp, encoding="utf-8"))
        only = None
        if "--only" in sys.argv:
            only = {c.strip().upper() for c in sys.argv[sys.argv.index("--only") + 1].split(",")}
            lab = json.load(open(lp, encoding="utf-8")) if os.path.exists(lp) else {}
            pick = [p["code"] for p in posts_l if lab.get(p["code"], "").upper() in only
                    or lab.get(p["code"], "").upper().rstrip("0123456789") in only]
        else:
            pick = [p["code"] for p in posts_l if p["code"] not in lab]
    out = os.path.join(work, "sheets"); os.makedirs(out, exist_ok=True)
    for old in os.listdir(out):  # sheets from an earlier pass would no longer match the new index
        if old.startswith(mode + "-") and old.endswith(".jpg"):
            os.remove(os.path.join(out, old))
    per = COLS * ROWS
    idx = []
    for i in range(0, len(pick), per):
        f = f"{mode}-{i // per + 1:03d}.jpg"
        sheet(work, pick[i:i + per], posts, os.path.join(out, f))
        idx.append({"file": f, "codes": pick[i:i + per]})
    json.dump({"sheets": idx}, open(os.path.join(out, f"{mode}-index.json"), "w"))
    print(f"{len(idx)} sheets, {len(pick)} posts -> {out}/{mode}-*.jpg")

if __name__ == "__main__":
    main()
