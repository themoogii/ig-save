---
name: saved-index
description: Builds and updates a "Saved Index" — a private visual board of the user's Instagram saved posts, sorted into categories the user chooses, with a grid and a zoomable map, published as a private claude.ai page. Use when the user says "build my saved index", "organize my Instagram saves", "sort my saved posts", "make a board of my Instagram saves", "add my new saves to the index", "update my saved index", "change/rename/merge my categories", or "re-sort my saved posts".
---

# Saved Index

Turn the user's Instagram saved posts into a private board: Claude reads their own Saved page slowly in their own logged-in browser, suggests categories from what they actually save, lets them edit those categories, sorts every post by looking at it, and publishes a grid + zoomable map as a private claude.ai page.

Everything the user sees is plain language. Do not mention file names, scripts, JSON or codes unless they ask.

## What this needs

- A browser tool that can run JavaScript in a page where the user is logged in to Instagram: the built-in browser pane (preferred) or Claude in Chrome. Without one, stop and say the plugin needs a browser connected to Claude.
- Python 3 with Pillow (`pip install pillow`, add `--break-system-packages` if pip asks).
- The Artifact tool to publish. Without it, deliver the board folder as a zip (see `references/publish.md`).
- A work folder that lasts: prefer a folder on the user's computer (ask for a connected folder and create `Saved Index/` inside it); otherwise use the session workspace and tell the user that updating later will mean collecting again.

Scripts live in `scripts/` next to this file and the page template in `assets/`. Call the work folder WORK and the published folder BOARD (WORK/board).

## Modes

Pick the mode from the request:

1. **Build** — first time. Do every step below.
2. **Add new saves** — WORK already has `posts.json`. Follow `references/maintain.md` → Refresh.
3. **Change categories** — rename, merge, split, add, or re-sort. Follow `references/maintain.md` → Categories.

## Build

### 1. Agree on the plan (one short message, then AskUserQuestion)

Tell the user, briefly and honestly:
- Claude will open their Saved page in their browser and scroll it slowly, reading only what the page shows (thumbnails, creator, caption). It never logs in for them, types passwords, likes, unsaves, follows or messages anyone.
- This is automated use of their own account. Instagram's terms restrict automated collection, so there is a small risk of a temporary "try again later" limit. The collector goes slowly and takes breaks to keep that risk low, and they can stop it at any time.
- Rough time: about an hour for 5,000–7,000 saves, mostly unattended.

Ask: go ahead with everything, or do a test run of about 100 posts first. Also ask what the board should be called (default "<their first name>'s Saved Index").

### 2. Collect (details and troubleshooting: `references/collect.md`)

1. Open `https://www.instagram.com/` in the browser. If it shows a login form, ask the user to log in themselves in that browser and say when done. Never type credentials.
2. Go to their profile page, read the collector from `scripts/collector.js` and run its full text with the browser JavaScript tool, then open the **Saved** tab by clicking it (client-side navigation keeps the collector running and lets it see the captions the page loads).
3. Run `SI.start({limit: 100})` for a test, or `SI.start()` for everything.
4. Check `SI.status()` about once a minute, not more. Report progress to the user every few minutes in one line.
5. Every time `readyToExport` reaches 500, and once at the end, run `await SI.exportChunk()`; each call downloads one `si-saved-NNN.json` file to the user's Downloads folder. Move those files into WORK (stage them from Downloads when the browser runs on the user's computer). If downloads don't arrive, use `await SI.take({size: 40})` in a loop and write each returned string to a file in WORK.
6. If `SI.status().error` says Instagram asked to verify or to try again later: stop, tell the user, and do not retry for several hours.
7. Run `python3 scripts/ingest.py WORK <folder with the si-saved files>` and report how many posts came in.

### 3. Suggest categories, then let the user decide (details: `references/categories.md`)

1. `python3 scripts/contact_sheets.py WORK sample 240` and look at every `WORK/sheets/sample-*.jpg` with Read.
2. Draft 6–12 categories that describe what *this user* saves, each with 0–5 sub-categories, plus a final **Other**. Name them in the user's words (their captions' language, their interests), not a generic taxonomy.
3. Show the draft as a short list with a one-line description and an example or two each. Ask with AskUserQuestion whether to use it as is or change it; take edits as free text (rename, merge, delete, add, split, add sub-categories). Repeat until they approve. The user's choice is final, even if Claude would group things differently.
4. Write `WORK/categories.json` in the format in `references/categories.md` (letters A, B, C… for categories, A1, A2… for sub-categories, Z for Other).

### 4. Sort every post

1. `python3 scripts/contact_sheets.py WORK sort` → numbered sheets of 48 posts (`WORK/sheets/sort-*.jpg`).
2. Look at each sheet and write one line per sheet to a label file: `sort-001.jpg: 1=A1 2=C3 3=Z …`, using the rules in `references/categories.md`. Above ~30 sheets, split the sheets across parallel subagents (each gets the category list with codes and descriptions, its sheet paths, and its own label file to write).
3. `python3 scripts/apply_labels.py WORK <label files>`; then run `contact_sheets.py WORK sort` again and label any posts it still finds, until none are left. Apply labels *before* regenerating sheets, because sheets are renumbered each run.
4. Give the user the count per category in one line. If a category looks wrong to them, use `references/maintain.md` → Categories.

### 5. Build and publish (details: `references/publish.md`)

1. `python3 scripts/build_board.py WORK WORK/board`.
2. Publish `WORK/board/index.html` with the Artifact tool, with `posts.json`, `thumbs.json` and everything in `t/` as supporting files at the same relative paths, in batches under the per-publish limits. It starts private.
3. Tell the user in two sentences what they have: Grid (categories as covers, then posts; search by caption, creator or hashtag) and Map (every thumbnail on one zoomable canvas, grouped by their categories, arranged by colour or newest). Remind them that the page shows other creators' posts, so share the link only with people they trust.

## Rules

- Read-only on Instagram: never like, save, unsave, comment, follow or message, and never open a post's own page in a loop.
- Keep the collector's default pace. Do not lower `minDelay`/`maxDelay` or skip its breaks, even if asked to hurry; offer a smaller `limit` instead.
- Categories describe what posts are about (a topic, a format, a kind of image), never what the people in them are like. Do not suggest categories about people's bodies, looks, health, sexuality or ethnicity. If the user names such a category themselves, use their wording.
- Keep the template's design. Fix bugs in it if needed, but do not restyle it unless the user asks.
