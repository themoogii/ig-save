#!/usr/bin/env python3
"""Merge collector chunks (si-saved-*.json) into one working set.

usage: ingest.py [--refresh] WORK_DIR CHUNK_FILE_OR_DIR [more ...]

--refresh  the chunks come from a later run that started at the top of the
           Saved page, so posts not seen before are newer saves: they are put
           before everything already in the working set.

Writes WORK_DIR/posts.json (one record per saved post, newest-saved first) and
WORK_DIR/thumbs/<code>.jpg (200x250). Safe to re-run: new chunks are merged in,
existing posts keep their category labels.
"""
import base64, glob, io, json, os, re, sys
from PIL import Image

def chunks(args):
    for a in args:
        if os.path.isdir(a):
            yield from sorted(glob.glob(os.path.join(a, "si-saved-*.json")))
        else:
            yield a

def tags_of(cap):
    return " ".join(dict.fromkeys(t.lower() for t in re.findall(r"#(\w+)", cap or "")))

def main():
    args = sys.argv[1:]
    refresh = "--refresh" in args
    args = [a for a in args if a != "--refresh"]
    if len(args) < 2:
        sys.exit(__doc__)
    work, sources = args[0], args[1:]
    os.makedirs(os.path.join(work, "thumbs"), exist_ok=True)
    pj = os.path.join(work, "posts.json")
    posts = {p["code"]: p for p in json.load(open(pj))} if os.path.exists(pj) else {}
    base_order = max([p["order"] for p in posts.values()], default=0)
    first_order = min([p["order"] for p in posts.values()], default=0)
    fresh = []
    added = updated = bad = 0
    for f in chunks(sources):
        try:
            data = json.load(open(f, encoding="utf-8"))
        except Exception as e:
            print(f"skip {f}: {e}"); continue
        for it in data.get("items", []):
            code = it.get("code")
            if not code:
                continue
            p = posts.get(code)
            if p is None:
                p = posts[code] = {"code": code, "order": base_order + it.get("order", 0), "_o": it.get("order", 0)}
                fresh.append(p); added += 1
            else:
                updated += 1
            for k in ("url", "user", "name", "cap", "ts", "kind", "alt"):
                if it.get(k) and not p.get(k):
                    p[k] = it[k]
            p["coll"] = sorted(set(p.get("coll", [])) | set(it.get("coll") or []))
            th = it.get("thumb", "")
            out = os.path.join(work, "thumbs", code + ".jpg")
            if th.startswith("data:image") and not os.path.exists(out):
                try:
                    im = Image.open(io.BytesIO(base64.b64decode(th.split(",", 1)[1]))).convert("RGB")
                    if im.size != (200, 250):
                        s = max(200 / im.width, 250 / im.height)
                        im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
                        l, t = (im.width - 200) // 2, (im.height - 250) // 2
                        im = im.crop((l, t, l + 200, t + 250))
                    im.save(out, quality=88)
                except Exception:
                    bad += 1
    if refresh and fresh and len(posts) > len(fresh):
        fresh.sort(key=lambda p: p["_o"])
        for i, p in enumerate(fresh):
            p["order"] = first_order - len(fresh) + i
    for p in posts.values():
        p.pop("_o", None)
        p.setdefault("url", f"https://www.instagram.com/p/{p['code']}/")
        p.setdefault("kind", "photo")
        p.setdefault("user", ""); p.setdefault("name", ""); p.setdefault("cap", ""); p.setdefault("ts", 0)
        p["tags"] = tags_of(p.get("cap"))
        p["thumb"] = os.path.exists(os.path.join(work, "thumbs", p["code"] + ".jpg"))
    lst = sorted(posts.values(), key=lambda p: p["order"])
    json.dump(lst, open(pj, "w", encoding="utf-8"), ensure_ascii=False)
    n = len(lst)
    print(f"{n} posts ({added} new, {updated} seen again, {bad} unreadable thumbnails)")
    print(f"  with thumbnail {sum(p['thumb'] for p in lst)}, caption {sum(bool(p['cap']) for p in lst)}, "
          f"creator {sum(bool(p['user']) for p in lst)}, date {sum(bool(p['ts']) for p in lst)}")

if __name__ == "__main__":
    main()
