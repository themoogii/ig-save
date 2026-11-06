#!/usr/bin/env python3
"""Build the board folder (page + data + thumbnail sheets) from the working set.

usage: build_board.py WORK_DIR OUT_DIR

Needs WORK_DIR/posts.json, WORK_DIR/thumbs/, WORK_DIR/categories.json, WORK_DIR/labels.json.
Posts without a label go to the last category (Other). Writes:
  OUT_DIR/index.html   the page (assets/board.html with the title filled in)
  OUT_DIR/posts.json   categories, sub-categories and posts
  OUT_DIR/thumbs.json  where each thumbnail sits in the sheets, plus colour order per sub-category
  OUT_DIR/t/           sXXX.jpg (200x250 cells), m/sXXX.jpg (100x125), lo.jpg (20x25 atlas)
"""
import colorsys, json, math, os, shutil, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
COLS = ROWS = 10

def colour_key(path):
    r, g, b = (v / 255 for v in Image.open(path).convert("RGB").resize((1, 1), Image.BOX).getpixel((0, 0)))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    if s < 0.16 or l < 0.12 or l > 0.92:          # greys, near-black, near-white: one band, dark to light
        return (0, l, 0)
    return (1, round(h * 12) / 12, l)               # colours: by hue band, then light to dark inside the band

def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    work, out = sys.argv[1], sys.argv[2]
    posts = json.load(open(os.path.join(work, "posts.json"), encoding="utf-8"))
    cfg = json.load(open(os.path.join(work, "categories.json"), encoding="utf-8"))
    lp = os.path.join(work, "labels.json")
    labels = json.load(open(lp, encoding="utf-8")) if os.path.exists(lp) else {}
    cats = cfg["categories"]
    areas, subs, sub_of = [], [], {}
    for ai, c in enumerate(cats):
        areas.append(c["name"])
        for s in c["subs"]:
            sub_of[s["code"].upper()] = len(subs)
            subs.append([ai, s["name"]])
    other = len(subs) - 1                              # last sub-category of the last category = Other
    colls = sorted({c for p in posts for c in p.get("coll", [])})
    ci = {c: i for i, c in enumerate(colls)}

    os.makedirs(os.path.join(out, "t", "m"), exist_ok=True)
    for f in os.listdir(os.path.join(out, "t")):
        if f.endswith(".jpg"):
            os.remove(os.path.join(out, "t", f))
    for f in os.listdir(os.path.join(out, "t", "m")):
        os.remove(os.path.join(out, "t", "m", f))

    rows, tmap, keys, by_sub = [], {}, {}, {}
    have = [p for p in posts if os.path.exists(os.path.join(work, "thumbs", p["code"] + ".jpg"))]
    per = COLS * ROWS
    nsh = math.ceil(len(have) / per)
    lo = Image.new("RGB", (per * 20, max(1, nsh) * 25), "white")
    for si in range(nsh):
        full = Image.new("RGB", (COLS * 200, ROWS * 250), "white")
        for n, p in enumerate(have[si * per:(si + 1) * per]):
            im = Image.open(os.path.join(work, "thumbs", p["code"] + ".jpg")).convert("RGB")
            full.paste(im, ((n % COLS) * 200, (n // COLS) * 250))
            lo.paste(im.resize((20, 25), Image.LANCZOS), (n * 20, si * 25))
            tmap[p["code"]] = si * per + n
        full.save(os.path.join(out, "t", f"s{si:03d}.jpg"), quality=80, optimize=True)
        full.resize((COLS * 100, ROWS * 125), Image.LANCZOS).save(os.path.join(out, "t", "m", f"s{si:03d}.jpg"), quality=78, optimize=True)
    lo.save(os.path.join(out, "t", "lo.jpg"), quality=80)

    for i, p in enumerate(posts):
        sub = sub_of.get(labels.get(p["code"], "").upper(), other)
        by_sub.setdefault(sub, []).append(i)
        if p["code"] in tmap:
            keys[i] = colour_key(os.path.join(work, "thumbs", p["code"] + ".jpg"))
        kind = 1 if p.get("kind") in ("reel", "video") else 0
        rows.append([i, p["code"], kind, p.get("user", ""), p.get("name", ""), int(p.get("ts") or 0), sub, [],
                     [ci[c] for c in p.get("coll", [])], (p.get("cap") or "")[:300], p.get("tags", ""), p["url"]])

    mo = {}
    for s, ids in by_sub.items():
        withk = sorted([i for i in ids if i in keys], key=lambda i: keys[i]) + [i for i in ids if i not in keys]
        mo[str(s)] = {"ids": withk, "c": max(2, round(math.sqrt(len(withk) * 1.25)))}

    json.dump({"title": cfg.get("title", "Saved Index"), "areas": areas, "subs": subs, "formats": [], "collections": colls, "posts": rows},
              open(os.path.join(out, "posts.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    json.dump({"v": 2, "cols": COLS, "rows": ROWS, "sheets": [f"t/s{i:03d}.jpg" for i in range(nsh)],
               "msheets": [f"t/m/s{i:03d}.jpg" for i in range(nsh)], "lo": "t/lo.jpg",
               "map": {str(i): tmap[p["code"]] for i, p in enumerate(posts) if p["code"] in tmap}, "mo": mo},
              open(os.path.join(out, "thumbs.json"), "w"), separators=(",", ":"))

    title = cfg.get("title", "Saved Index")
    html = open(os.path.join(HERE, "..", "assets", "board.html"), encoding="utf-8").read()
    html = html.replace("{{TITLE}}", title.replace("<", "&lt;"))
    open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(html)

    size = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(out) for f in fs)
    files = sum(len(fs) for _, _, fs in os.walk(out))
    counts = {}
    for r in rows:
        counts[areas[subs[r[6]][0]]] = counts.get(areas[subs[r[6]][0]], 0) + 1
    print(f"{len(rows)} posts, {len(have)} thumbnails in {nsh} sheets; {files} files, {size / 1e6:.1f} MB -> {out}")
    print("  " + " · ".join(f"{a} {n}" for a, n in counts.items()))

if __name__ == "__main__":
    main()
