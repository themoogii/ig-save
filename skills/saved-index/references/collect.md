# Collecting the saved posts

## How the collector works

`scripts/collector.js` defines `window.SI`. It:

- reads the Saved grid as it appears (links to `/p/…` and `/reel/…`, plus the thumbnail each tile already shows),
- listens to the JSON the page itself loads and to JSON embedded in the page, picking out captions, creators, post dates and media type for the posts in the grid,
- scrolls by 60–95% of a screen every 1.6–3.4 s, takes a 25–45 s break every 300 new posts, and stops when the page stops growing,
- saves every post with a 200×250 JPEG thumbnail in the browser's IndexedDB, so a reload or a stop loses nothing.

It never sends anything anywhere. Data leaves the page only when Claude calls `exportChunk` (a download) or `take` (returned to Claude).

## Injecting it

Run the whole file text with the browser JavaScript tool. Load it on the profile page (`https://www.instagram.com/<username>/`), then click the **Saved** tab: Instagram switches pages without reloading, so the collector sees the requests that fill the grid. If you load it directly on the Saved page, the first screen of posts may have no captions; that's acceptable.

A full page reload removes the collector. Run the file again and `SI.start()` again: it restores what it saved, re-scrolls past known posts quickly, and carries on.

For a saved collection (to tag posts with its name), open that collection's page and run `SI.start({collection: "Collection name"})`. Posts already collected just gain the tag.

## Calls

| Call | Returns |
| --- | --- |
| `SI.start({limit, collection, known})` | `"started"`; runs in the background |
| `SI.status()` | `{running, done, error, seen, withThumb, withCaption, withCreator, exported, readyToExport, minutes}` |
| `SI.stop()` | stops after the current step |
| `await SI.exportChunk({size: 500})` | downloads `si-saved-NNN.json`, marks those posts exported |
| `await SI.take({size: 40})` | the next posts as a JSON string, marked exported |
| `await SI.unexportAll()` | makes everything exportable again (if files went missing) |
| `await SI.reset()` | forgets everything in this browser |

Each exported file is about 5–6 MB per 500 posts.

## Getting the files into WORK

- Browser pane / Chrome on the user's computer: downloads land in their Downloads folder. With a device bridge, stage `Downloads/si-saved-*.json` into the session, or ask for access to Downloads first. When Claude runs on the same computer, read them from Downloads directly.
- If downloads are blocked or never appear: loop `await SI.take({size: 40})` and write each result to `WORK/chunks/si-saved-NNN.json`. Keep chunks small; tool results have size limits.
- Then `python3 scripts/ingest.py WORK <folder or files>`. It is safe to re-run with more chunks.

## Pace and stopping

- Check status about once a minute. Each check is cheap, but checking every few seconds adds nothing.
- `done: true` with no error means the end of the Saved list was reached. If `seen` is far below what the user expects, scroll the page to the bottom once by hand (or ask the user to) and `SI.start()` again.
- `error` containing "log in or verify" or "try again later": stop everything, tell the user what Instagram showed, and suggest waiting a few hours. Never solve a CAPTCHA or verification step; the user does that themselves.
- Low `withThumb`: the thumbnails couldn't be read (a browser setting or a CDN change). Report it. Don't work around it by opening posts one by one.

## Privacy

Thumbnails and captions belong to the creators of the saved posts. Keep the working files in the user's own folder or the session, and publish only to the user's private page.
