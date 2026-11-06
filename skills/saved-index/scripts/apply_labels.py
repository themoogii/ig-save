#!/usr/bin/env python3
"""Turn Claude's per-sheet labels into WORK_DIR/labels.json.

usage: apply_labels.py WORK_DIR LABEL_FILE [more ...]

Label files are plain text, one line per contact sheet:
    sort-001.jpg: 1=A1 2=A3 3=C2 4=Z ...
Each token is CELL=SUBCODE, using the sub-category codes in WORK_DIR/categories.json
(a bare category code such as "C" means that category's first sub-category; "Z" is Other).
Cells left out stay unlabelled and show up again in the next `contact_sheets.py sort` run.
"""
import json, os, re, sys

def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    work = sys.argv[1]
    cats = json.load(open(os.path.join(work, "categories.json"), encoding="utf-8"))["categories"]
    valid = {}
    for c in cats:
        for s in c["subs"]:
            valid[s["code"].upper()] = s["code"]
        valid[c["code"].upper()] = c["subs"][0]["code"]
    idx = json.load(open(os.path.join(work, "sheets", "sort-index.json")))["sheets"]
    by_file = {s["file"]: s["codes"] for s in idx}
    lp = os.path.join(work, "labels.json")
    labels = json.load(open(lp, encoding="utf-8")) if os.path.exists(lp) else {}
    n = bad = 0
    for f in sys.argv[2:]:
        for line in open(f, encoding="utf-8"):
            m = re.match(r"\s*([\w.-]+\.jpg)\s*:\s*(.*)", line)
            if not m:
                continue
            codes = by_file.get(m.group(1))
            if codes is None:
                print(f"unknown sheet {m.group(1)}"); continue
            for tok in m.group(2).split():
                mm = re.match(r"(\d+)\s*=\s*([\w-]+)", tok)
                if not mm:
                    continue
                k, sc = int(mm.group(1)), mm.group(2).upper()
                if not 1 <= k <= len(codes) or sc not in valid:
                    bad += 1; continue
                labels[codes[k - 1]] = valid[sc]; n += 1
    json.dump(labels, open(lp, "w", encoding="utf-8"), indent=0)
    total = len(json.load(open(os.path.join(work, "posts.json"), encoding="utf-8")))
    print(f"applied {n} labels ({bad} ignored). labelled {len(labels)} of {total} posts")

if __name__ == "__main__":
    main()
