# Categories: suggesting, agreeing, sorting

## Suggesting

Look at all the sample sheets (240 posts spread across the whole collection, newest to oldest) before drafting. Then:

- Draft **6–12 categories**. Fewer than 6 makes the map a few giant blocks; more than 12 makes the side list hard to scan.
- Give a category sub-categories only where it is big and mixed (roughly more than 10% of the sample). 2–5 subs each. Small categories have none.
- Name categories after what the posts are about: a topic ("Furniture & objects"), a kind of post ("Recipes", "Tutorials"), or a kind of image ("Typography"). Prefer short, plain names, 1–3 words, title case.
- Reflect this user. If 30% of the sample is ceramics, ceramics is a category, not a sub of "Art".
- Always end with **Other**, for posts that fit nowhere. It should stay under ~10% of posts.
- Estimate a share for each category from the sample ("about 1 in 5 of your saves").

Present it like this, then ask:

> Here's how your saves seem to group. Change anything you like: rename, merge, split, delete, add, or add sub-categories.
>
> 1. **Furniture & objects** (about 1 in 5): chairs, lamps, product design. Subs: Chairs · Lighting · Objects
> 2. **Recipes** (about 1 in 8): …
> …
> 12. **Other**: anything that doesn't fit.

AskUserQuestion options: "Looks good, sort everything" / "I'll change some" (free text). Apply their edits literally and show the revised list once more before sorting. If they want categories Claude didn't see in the sample, accept them; they may know their saves better.

## categories.json

```json
{
  "title": "Alex's Saved Index",
  "categories": [
    {"code": "A", "name": "Furniture & objects", "desc": "chairs, lamps, tables, product design, design objects",
     "subs": [{"code": "A1", "name": "Chairs"}, {"code": "A2", "name": "Lighting"}, {"code": "A3", "name": "Objects"}]},
    {"code": "B", "name": "Recipes", "desc": "cooking videos, dishes, drinks", "subs": [{"code": "B1", "name": "Recipes"}]},
    {"code": "Z", "name": "Other", "desc": "anything that fits nowhere", "subs": [{"code": "Z", "name": "Other"}]}
  ]
}
```

- A category without sub-categories gets a single sub with the same name (code `B1`).
- **Other** must be last, with code `Z` and a single sub `Z`.
- `desc` is for Claude and subagents (what belongs there, borderline cases); it is not shown on the page.

## Sorting a sheet

Each sort sheet shows 48 posts, numbered in their top-left corner, with the creator and the start of the caption under each one. For each cell choose the single best sub-category code.

- Decide mainly by the image: what it shows and what kind of post it is. Use the creator and caption to settle unclear cases. A furniture designer's studio-tour reel goes in the furniture category, even if the frame shows a person.
- A text-only post (a quote, a tweet screenshot) goes by its subject.
- Use `Z` only when nothing fits; prefer the closest real category otherwise.
- If a sheet cell is blank or broken, skip that number; it will come back in the next pass.
- Write the whole sheet on one line: `sort-007.jpg: 1=A1 2=A1 3=D2 4=Z … 48=B1`

Subagent brief, when splitting the work:

> Sort Instagram saved posts into categories. Category list with codes and descriptions: <paste categories.json>. For each sheet image below, Read it, then append one line to <label file> in the form `sort-NNN.jpg: 1=CODE 2=CODE …` covering every numbered cell. Decide by the image first, the creator/caption text second; use Z only when nothing fits. Sheets: <paths>. Reply only with how many sheets you finished.

## Quality check (optional, quick)

After every post is labelled, check the biggest categories yourself before publishing: run `contact_sheets.py WORK sort --only <category code>` for one category, look at the first sheet or two, and write corrected labels only for the misfits (`sort-001.jpg: 7=C2 31=Z`). Apply them, then move to the next category. Do this only after all labels are applied, because it renumbers the sort sheets.
