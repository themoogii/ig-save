# Keeping the board up to date

Both flows need the WORK folder from the first build (`posts.json`, `thumbs/`, `categories.json`, `labels.json`). If it's gone, say so and offer a fresh build.

## Refresh: add new saves

1. Read the codes already in `WORK/posts.json`.
2. Open the Saved page as in a build (`references/collect.md`), run the collector, and start it with those codes:
   `SI.start({known: [ …codes… ]})`. It skips known posts and stops after 36 known ones in a row, meaning it has reached the saves from last time. Usually this takes a minute or two.
3. Export, then `python3 scripts/ingest.py --refresh WORK <files>`. New posts go to the front, as newest saves.
4. `python3 scripts/contact_sheets.py WORK sort` (only unlabelled posts), label them, `apply_labels.py`.
5. If many new posts land in Other, suggest a new category (see below).
6. Rebuild and republish (`references/publish.md` → Updating later).

Unsaved posts are not removed by a refresh. If the user wants an exact mirror, do a full collection again with a fresh `SI.reset()`, ingest into a new WORK folder, and copy `categories.json` and `labels.json` across (labels are keyed by post, so they still apply).

## Categories: rename, merge, split, add

Labels store sub-category codes, so names can change freely.

- **Rename** a category or sub-category: edit `name` in `categories.json`, rebuild, republish. No re-sorting.
- **Reorder**: reorder the list in `categories.json` (keep Other last).
- **Merge** B into A: in `labels.json`, replace every `B…` value with the matching `A…` code (or `A1`), delete B from `categories.json`, rebuild.
- **Split / add / move posts**: add the new category or sub-category to `categories.json` with a fresh code, then re-sort only the posts that might move:
  `python3 scripts/contact_sheets.py WORK sort --only B,Z` (every post currently in B or Other), label those sheets with the full updated list, `apply_labels.py`, rebuild.
- **Delete** a category: move its posts to Other or another category (as a merge), or re-sort them with `--only`.
- **Start over**: write a new `categories.json`, delete `labels.json`, and sort everything again.

After any change, give the user the new counts per category in one line, then republish.
