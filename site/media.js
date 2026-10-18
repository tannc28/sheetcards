/**
 * Fetches the pictures and recordings a deck's media columns point at, so the
 * .apkg carries them and its cards can be reviewed offline.
 *
 * Every decision — which addresses, what Commons resolves them to, which
 * answers are kept, what each file is called — is made by the add-on's own
 * src/media.py through Pyodide, handed in here as `py`. That is what makes a
 * download here and a sync in the add-on write the same field values: this
 * module only fetches, four at a time, and remembers what it fetched.
 *
 * An address the browser is not allowed to read (no CORS) stays a link: the
 * card still shows it online. Nothing here can stop a download.
 */

const WORKERS = 4;
const DB = "sheetcards-media";
const STORE = "files";
// Bumped when src/media.py names files differently, so old entries are not reused.
const VERSION = 1;
const key = (url) => `${VERSION}:${url}`;

function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

/**
 * A cache of fetched files by address, in this browser's IndexedDB, so a second
 * download of the same sheet fetches nothing. Absent or refused storage is a
 * cache that remembers nothing.
 */
export function idbCache() {
  let db = null;
  const ready = () => (db ??= openDb());
  const tx = async (mode, work) => {
    const store = (await ready()).transaction(STORE, mode).objectStore(STORE);
    return new Promise((resolve, reject) => {
      const req = work(store);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  };
  return {
    async get(url) {
      try {
        return (await tx("readonly", (s) => s.get(key(url)))) || null;
      } catch {
        return null;
      }
    },
    async put(url, entry) {
      try {
        await tx("readwrite", (s) => s.put(entry, key(url)));
      } catch {
        // A full or private store only means the next download fetches again.
      }
    },
  };
}

/**
 * A plain CORS read: an address that does not allow it throws, and the cell
 * stays the link it was. Wikimedia answers a burst with 429, so a busy answer
 * is asked again, twice, after a second or two.
 */
async function fetchBusy(get, url, wait = (ms) => new Promise((r) => setTimeout(r, ms))) {
  for (let attempt = 0; ; attempt++) {
    // `no-store`: the card preview has already drawn these pictures, and the copy
    // in the HTTP cache is whatever the <img> was sent — a WebP, from Wikimedia,
    // where the add-on (and a plain fetch) gets the JPEG. The same bytes on both
    // paths is what lets one file name stand for one file.
    const res = await get(url, { mode: "cors", credentials: "omit", redirect: "follow", cache: "no-store" });
    if (![429, 503].includes(res.status) || attempt >= 2) return res;
    await wait(1000 * (attempt + 1));
  }
}

/** Runs `work` over `items`, at most `n` at a time, in order of starting. */
async function pool(items, n, work) {
  let next = 0;
  const lanes = Array.from({ length: Math.min(n, items.length) }, async () => {
    while (next < items.length) {
      const i = next++;
      await work(items[i], i);
    }
  });
  await Promise.all(lanes);
}

/**
 * Fetches what `jobs` (media.jobs) point at.
 *
 * @param {Array} jobs `{url, kind, name, commons}` from src/media.py
 * @param {object} o
 * @param {object} o.py `queries(titles)`, `sources(answers)`, `settle(job, type, size)`,
 *   `limit` (bytes in all) — the Python rules
 * @param {Function} [o.fetch] stands in for the network in tests
 * @param {object} [o.cache] `get(url)`, `put(url, entry)`
 * @param {Function} [o.progress] called with `(done, total)`
 * @returns {Promise<{files: Array, links: number, bytes: number, over: number, image: number, audio: number}>}
 *   `files` is `[url, name, Uint8Array]` per file carried; `links` counts the
 *   addresses left as links (`over` of them for the size limit)
 */
export async function gatherMedia(jobs, { py, fetch: get = fetch, cache = null, progress = () => {} }) {
  const out = { files: [], links: 0, bytes: 0, over: 0, image: 0, audio: 0 };
  if (!jobs.length) return out;
  let done = 0;
  const tick = () => progress(++done, jobs.length);
  progress(0, jobs.length);

  const found = new Map();
  const todo = [];
  for (const job of jobs) {
    const hit = cache && (await cache.get(job.url));
    if (hit?.name && hit.data) found.set(job.url, hit);
    else todo.push(job);
  }

  let sources = {};
  const titles = todo.filter((j) => j.commons).map((j) => j.commons);
  if (titles.length) {
    const answers = [];
    for (const query of py.queries(titles)) {
      try {
        const res = await get(query);
        if (res.ok) answers.push(await res.text());
      } catch {
        // Commons out of reach: its files stay links this time.
      }
    }
    sources = py.sources(answers);
  }

  for (const job of jobs) if (found.has(job.url)) tick();
  await pool(todo, WORKERS, async (job) => {
    try {
      const from = job.commons ? sources[job.commons]?.[job.kind] : job.url;
      if (!from) return;
      const res = await fetchBusy(get, from);
      if (!res.ok) return;
      const data = new Uint8Array(await res.arrayBuffer());
      const type = res.headers.get("content-type") || "";
      const name = py.settle(job, type, data.length);
      if (!name) return;
      const entry = { name, type, data };
      found.set(job.url, entry);
      cache?.put(job.url, entry);
    } catch {
      // Left a link.
    } finally {
      tick();
    }
  });

  // In the order of the sheet, so the size limit cuts the same files each time.
  for (const job of jobs) {
    const hit = found.get(job.url);
    if (!hit) {
      out.links++;
      continue;
    }
    const data = hit.data instanceof Uint8Array ? hit.data : new Uint8Array(hit.data);
    if (out.bytes + data.length > py.limit) {
      out.links++;
      out.over++;
      continue;
    }
    out.bytes += data.length;
    out[job.kind]++;
    out.files.push([job.url, hit.name, data]);
  }
  return out;
}
