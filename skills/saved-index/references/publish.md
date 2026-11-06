# Publishing the board

## What build_board.py makes

```
WORK/board/
  index.html      page body (no <html>/<head>/<body>: the Artifact tool adds the skeleton)
  posts.json      title, categories, sub-categories, posts
  thumbs.json     sheet list, thumbnail positions, colour order per sub-category
  t/s000.jpg …    full thumbnails, 10×10 per sheet, 200×250 each (~0.6–1 MB per sheet)
  t/m/s000.jpg …  half size, for zoomed-out views
  t/lo.jpg        one small atlas (20×25 per post) shown instantly
```

About 100 posts per sheet, so 7,000 posts ≈ 70 + 70 sheets + 4 other files, about 60–90 MB.

## Publishing with the Artifact tool

- Publish `WORK/board/index.html` as the page, with `files` mapping each supporting file to its same relative path (`posts.json`, `thumbs.json`, `t/lo.jpg`, `t/s000.jpg`, `t/m/s000.jpg`, …).
- One publish takes at most 255 files and 64 MB. For a big board, first publish the page with `posts.json`, `thumbs.json`, `t/lo.jpg` and the `t/m/` sheets, then republish to the same URL with the `t/` sheets in batches that fit the limits. Each later publish adds to the files already there.
- Icon: `grid`. Description: "<N> Instagram saves, sorted into <K> categories."
- The page keeps its own look. It already defines light and dark colours and loads its fonts from Google Fonts, so don't restyle it.
- After publishing, say in one or two sentences what the page is. Don't paste the URL unless asked.

## Updating later

Re-run `build_board.py` into the same `WORK/board`, then republish the same artifact. Send `index.html`, `posts.json`, `thumbs.json`, `t/lo.jpg` and only the sheets that changed or are new. Thumbnails are packed newest first, so after a refresh every sheet shifts; in that case republish all of them, in batches.

## Without the Artifact tool

Zip `WORK/board` and send it. Explain that it is a small website: opening `index.html` straight from disk won't load the data, so they need to put the folder on a static host (Cloudflare Pages, Netlify Drop, GitHub Pages) or a local server. Before zipping, wrap `index.html` in a full document: add `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body>` before it and `</body></html>` after it.
