/* Saved Index collector — runs inside the user's own logged-in instagram.com "Saved" page.
 *
 * It only reads what the page itself shows and loads while it scrolls slowly:
 *   - the grid of saved posts (links + the thumbnails Instagram already displays)
 *   - the JSON the page fetches for that grid (captions, creators, dates), when it can see it
 * Everything is kept in this browser (IndexedDB), so a reload or a pause loses nothing.
 *
 * API (call from the browser JavaScript tool; every call returns quickly):
 *   SI.start({limit, pauseEvery, minDelay, maxDelay, collection, known})  starts/resumes scrolling in the background
 *        known: codes collected in an earlier run; the scroll skips them and stops after
 *               `stopAfterKnown` (default 36) of them in a row, i.e. once it reaches old saves
 *   SI.status()                                                    progress summary
 *   SI.stop()                                                      stops after the current step
 *   await SI.exportChunk({size})                                   downloads the next si-saved-NNN.json file
 *   await SI.take({size})                                          returns the next chunk as a JSON string instead
 *   await SI.reset()                                               forgets everything collected in this browser
 */
(() => {
  if (window.SI && window.SI.version) return;
  const VERSION = 1, DBN = "saved-index-collector", ST = "items";
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const rnd = (a, b) => a + Math.random() * (b - a);

  /* ---------- storage ---------- */
  let dbp = null;
  const db = () => dbp || (dbp = new Promise((res, rej) => {
    const q = indexedDB.open(DBN, 1);
    q.onupgradeneeded = () => q.result.createObjectStore(ST, { keyPath: "code" });
    q.onsuccess = () => res(q.result); q.onerror = () => rej(q.error);
  }));
  const tx = async (mode, fn) => { const d = await db(); return new Promise((res, rej) => {
    const t = d.transaction(ST, mode), s = t.objectStore(ST); const out = fn(s);
    t.oncomplete = () => res(out && out.result !== undefined ? out.result : out); t.onerror = () => rej(t.error); }); };
  const putItem = it => tx("readwrite", s => s.put(it));
  const allItems = () => tx("readonly", s => s.getAll());

  /* ---------- state ---------- */
  const S = { items: new Map(), seq: 0, running: false, done: false, stopReq: false, error: "",
              scrolls: 0, idle: 0, since: 0, startedAt: 0, opts: {}, exported: 0 };

  const meta = it => { const { thumb, ...m } = it; m.hasThumb = !!thumb; return m; };
  async function restore() {
    for (const it of await allItems()) { S.items.set(it.code, meta(it)); S.seq = Math.max(S.seq, it.order || 0); if (it.exported) S.exported++; }
  }

  /* ---------- 1. enrich from the JSON the page loads ---------- */
  const pending = new Map();      // code -> fields seen in page data before the tile appears
  function harvest(o, d = 0) {
    if (!o || typeof o !== "object" || d > 40) return;
    if (Array.isArray(o)) { for (const x of o) harvest(x, d + 1); return; }
    if (typeof o.code === "string" && (o.image_versions2 || o.carousel_media || o.display_url || o.thumbnail_src || o.taken_at)) noteMedia(o);
    for (const k in o) { const v = o[k]; if (v && typeof v === "object") harvest(v, d + 1); }
  }
  function noteMedia(m) {
    const f = pending.get(m.code) || {};
    const u = m.user || m.owner || {};
    f.user = f.user || u.username || "";
    f.name = f.name || u.full_name || "";
    const cap = (m.caption && m.caption.text) || (m.edge_media_to_caption && m.edge_media_to_caption.edges && m.edge_media_to_caption.edges[0] && m.edge_media_to_caption.edges[0].node.text);
    if (cap && !f.cap) f.cap = String(cap).slice(0, 600);
    f.ts = f.ts || m.taken_at || m.taken_at_timestamp || 0;
    f.kind = f.kind || (m.product_type === "clips" ? "reel" : (m.media_type === 8 || m.carousel_media) ? "carousel" : m.media_type === 2 ? "video" : "photo");
    const cands = (m.image_versions2 || (m.carousel_media && m.carousel_media[0] && m.carousel_media[0].image_versions2) || {}).candidates;
    if (!f.src && cands && cands.length) { const c = cands.slice().sort((a, b) => a.width - b.width); f.src = (c.find(x => x.width >= 320) || c[c.length - 1]).url; }
    if (!f.src) f.src = m.thumbnail_src || m.display_url || "";
    pending.set(m.code, f);
    const it = S.items.get(m.code); if (it) merge(it, f);
  }
  function merge(it, f) { let ch = false; for (const k of ["user", "name", "cap", "ts", "kind", "src"]) if (f[k] && !it[k]) { it[k] = f[k]; ch = true; } if (ch) it.dirty = true; }
  function hookNetwork() {
    if (window.__siHooked) return; window.__siHooked = true;
    const tryParse = t => { if (!t || t.length < 20) return; const s = t.replace(/^for \(;;\);/, ""); for (const part of s.split(/\n(?=\{)/)) { try { harvest(JSON.parse(part)); } catch (e) {} } };
    const of = window.fetch;
    window.fetch = async function (...a) { const r = await of.apply(this, a); try { const ct = r.headers.get("content-type") || ""; if (/json|javascript|text/.test(ct)) r.clone().text().then(tryParse).catch(() => {}); } catch (e) {} return r; };
    const os = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.send = function (...a) { this.addEventListener("load", () => { try { if (typeof this.responseText === "string") tryParse(this.responseText); } catch (e) {} }); return os.apply(this, a); };
    document.querySelectorAll('script[type="application/json"]').forEach(s => { try { harvest(JSON.parse(s.textContent)); } catch (e) {} });
  }

  /* ---------- 2. read the grid itself ---------- */
  const codeOf = href => { const m = /\/(p|reel|tv)\/([A-Za-z0-9_-]{5,})/.exec(href || ""); return m ? [m[1], m[2]] : null; };
  function blocked() {
    if (/\/accounts\/login|\/challenge\//.test(location.pathname)) return "Instagram asked to log in or verify. Stopped.";
    const t = (document.body && document.body.innerText || "").slice(0, 4000);
    if (/try again later|we restrict certain activity|suspicious activity/i.test(t)) return "Instagram showed a 'try again later' notice. Stopped — wait a few hours before continuing.";
    return "";
  }
  async function thumbFrom(img, src) {
    const W = 200, H = 250;
    const draw = bmp => { const c = document.createElement("canvas"); c.width = W; c.height = H; const g = c.getContext("2d");
      const iw = bmp.width || bmp.naturalWidth, ih = bmp.height || bmp.naturalHeight; const s = Math.max(W / iw, H / ih);
      g.drawImage(bmp, (W - iw * s) / 2, (H - ih * s) / 2, iw * s, ih * s); return c.toDataURL("image/jpeg", 0.82); };
    try { if (img && img.complete && img.naturalWidth) return draw(img); } catch (e) { /* tainted canvas: fall through */ }
    try { const b = await (await fetch(src || img.currentSrc || img.src, { mode: "cors", credentials: "omit" })).blob(); return draw(await createImageBitmap(b)); } catch (e) { return ""; }
  }
  async function scanGrid() {
    let added = 0, knownRun = S.knownRun || 0;
    const links = [...document.querySelectorAll('main a[href*="/p/"], main a[href*="/reel/"], main a[href*="/tv/"]')];
    for (const a of links) {
      const c = codeOf(a.getAttribute("href")); if (!c) continue; const [type, code] = c;
      let it = S.items.get(code);
      const img = a.querySelector("img");
      if (S.known && S.known.has(code)) { if (!S.seenKnown.has(code)) { S.seenKnown.add(code); knownRun++; } continue; }
      if (!it) {
        it = { code, url: `https://www.instagram.com/${type === "reel" ? "reel" : "p"}/${code}/`, order: ++S.seq, kind: type === "reel" ? "reel" : "",
               alt: (img && img.alt || "").slice(0, 400), coll: S.opts.collection ? [S.opts.collection] : [], hasThumb: false };
        S.items.set(code, it); added++; it.dirty = true; knownRun = 0;
      } else if (S.opts.collection && !(it.coll || []).includes(S.opts.collection)) { it.coll = [...(it.coll || []), S.opts.collection]; it.dirty = true; }
      const f = pending.get(code); if (f) merge(it, f);
      if (!it.hasThumb && img) {
        const th = await thumbFrom(img, (f && f.src) || "");
        if (th) { it.hasThumb = true; it.dirty = true; await putItem({ ...it, dirty: undefined, thumb: th }); continue; }
      }
      if (it.dirty) { const full = await tx("readonly", s => s.get(code)); await putItem({ ...(full || {}), ...it, dirty: undefined, thumb: full && full.thumb }); it.dirty = false; }
    }
    S.knownRun = knownRun;
    return added;
  }

  /* ---------- 3. slow scroll loop ---------- */
  async function loop() {
    const o = S.opts; S.running = true; S.done = false; S.error = ""; S.startedAt = Date.now();
    try {
      while (!S.stopReq) {
        const b = blocked(); if (b) { S.error = b; break; }
        const added = await scanGrid(); S.since += added;
        const h = document.documentElement.scrollHeight, grew = h > (S.lastH || 0); S.lastH = Math.max(S.lastH || 0, h);
        S.idle = added || grew ? 0 : S.idle + 1;      // re-scrolling known posts after a reload still counts as progress while the page grows
        if (o.limit && S.items.size >= o.limit) { S.done = true; break; }
        if (S.known && S.knownRun >= o.stopAfterKnown) { S.done = true; break; }   // refresh: reached posts collected last time
        const atBottom = window.innerHeight + window.scrollY >= h - 50;
        if (S.idle >= (atBottom ? 6 : 12)) { S.done = true; break; }      // page stopped growing: reached the end
        if (S.since >= o.pauseEvery) { S.since = 0; await sleep(rnd(25000, 45000)); }   // regular breather
        window.scrollBy({ top: window.innerHeight * rnd(0.6, 0.95), behavior: "smooth" }); S.scrolls++;
        await sleep(rnd(o.minDelay, o.maxDelay) + (S.idle ? 1500 : 0));
      }
    } catch (e) { S.error = String(e && e.message || e); }
    S.running = false; S.stopReq = false;
  }

  /* ---------- 4. hand the data over ---------- */
  async function nextChunk(size) {
    const all = (await allItems()).filter(x => !x.exported && x.thumb).sort((a, b) => a.order - b.order).slice(0, size);
    for (const x of all) { const f = pending.get(x.code); if (f) for (const k of ["user", "name", "cap", "ts", "kind"]) if (f[k] && !x[k]) x[k] = f[k]; }
    return all;
  }
  async function markExported(list) { for (const x of list) { x.exported = true; await putItem(x); const m = S.items.get(x.code); if (m) m.exported = true; } S.exported += list.length; }

  window.SI = {
    version: VERSION,
    async start(opts = {}) {
      if (S.running) return "already running";
      S.opts = Object.assign({ limit: 0, pauseEvery: 300, minDelay: 1600, maxDelay: 3400, collection: "", known: null, stopAfterKnown: 36 }, opts);
      S.known = S.opts.known && !S.opts.collection ? new Set(S.opts.known) : null; S.seenKnown = new Set(); S.knownRun = 0; S.idle = 0; S.lastH = 0;
      hookNetwork(); if (!S.items.size) await restore();
      loop(); return "started";
    },
    stop() { S.stopReq = true; return "stopping"; },
    status() {
      const v = [...S.items.values()];
      return { running: S.running, done: S.done, error: S.error, seen: v.length, withThumb: v.filter(x => x.hasThumb).length,
               withCaption: v.filter(x => x.cap).length, withCreator: v.filter(x => x.user).length,
               exported: v.filter(x => x.exported).length, readyToExport: v.filter(x => x.hasThumb && !x.exported).length,
               minutes: S.startedAt ? Math.round((Date.now() - S.startedAt) / 6000) / 10 : 0 };
    },
    async exportChunk({ size = 500 } = {}) {
      const list = await nextChunk(size); if (!list.length) return "nothing new to export";
      const n = String(Math.floor(S.exported / size) + 1).padStart(3, "0");
      const name = `si-saved-${n}.json`;
      const blob = new Blob([JSON.stringify({ v: VERSION, page: location.pathname, items: list })], { type: "application/json" });
      const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click(); a.remove();
      await markExported(list); return `${name}: ${list.length} posts`;
    },
    async take({ size = 40 } = {}) { const list = await nextChunk(size); await markExported(list); return JSON.stringify({ v: VERSION, items: list }); },
    async unexportAll() { for (const x of await allItems()) { x.exported = false; await putItem(x); } S.exported = 0; for (const m of S.items.values()) m.exported = false; return "all posts can be exported again"; },
    async reset() { S.items.clear(); S.seq = 0; S.exported = 0; await tx("readwrite", s => s.clear()); return "cleared"; }
  };
})();
"Saved Index collector loaded";
