/**
 * Putting the add-on's own Python in the browser.
 *
 * Two pages need this — Sheet to Anki and Create sheet — and the point of
 * both is that they run the code the add-on runs rather than a copy of it. So
 * the module list lives here, once: scripts/build_site.py copies exactly these
 * files into build/site/sc/, and tests/test_pure_modules.py proves exactly
 * these still import with no Anki and no Qt anywhere near them.
 */

const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.28.3/full/pyodide.mjs";
const BASE = PYODIDE.replace("pyodide.mjs", "");

// What a first visit downloads, per file: [bytes over the wire (brotli), bytes
// once decoded]. Measured off the CDN for this exact version; a stream can only
// count decoded bytes, so each is scaled by its own ratio to say how much data
// has actually come in. Change these with the version above.
const FILES = {
  "pyodide.asm.wasm": [2667808, 8645967],
  "python_stdlib.zip": [2379766, 2416866],
  "sqlite3-1.0.0-cp313-cp313-pyodide_2025_0_wasm32.whl": [566360, 566355],
  "pyodide.asm.js": [226208, 1073033],
  "pyodide-lock.json": [23865, 109732],
  "pyodide.mjs": [6711, 6711],
};

/** The first visit's download, in bytes over the wire (~5.9 MB). */
export const FIRST_LOAD_BYTES = Object.values(FILES).reduce((sum, [wire]) => sum + wire, 0);

/** Megabytes the way a status line says them: one decimal, at least 0.1. */
export const mb = (bytes) => Math.max(0.1, bytes / 1e6).toFixed(1);

/**
 * True where the browser says the page is on mobile data or saving it. Only
 * Chrome on Android answers (navigator.connection); Safari says nothing, and
 * then nothing is said.
 */
export function onMobileData(nav = globalThis.navigator) {
  const c = nav?.connection;
  if (!c) return false;
  return c.saveData === true || c.type === "cellular" || /(^|-)(2g|3g)$/.test(c.effectiveType || "");
}

/**
 * Counts what Pyodide downloads while it boots, by wrapping fetch for its own
 * files only. Every response is passed on with its status and headers intact
 * (instantiateStreaming needs application/wasm), and anything that goes wrong
 * here hands back the untouched response: a progress line must not stop a boot.
 * Returns a function that puts fetch back.
 */
function countDownloads(onBytes) {
  const real = globalThis.fetch;
  const seen = {};
  const tell = () => {
    const done = Object.values(seen).reduce((a, b) => a + b, 0);
    onBytes(Math.min(done, FIRST_LOAD_BYTES), FIRST_LOAD_BYTES);
  };
  globalThis.fetch = async function (input, init) {
    const res = await real.call(this, input, init);
    try {
      const url = typeof input === "string" ? input : input?.url || String(input);
      if (!url.startsWith(BASE) || !res.body || typeof TransformStream !== "function") return res;
      const name = url.slice(BASE.length).split("?")[0];
      const [wire, raw] = FILES[name] || [0, 0];
      const ratio = raw ? wire / raw : 1;
      let got = 0;
      const counted = res.body.pipeThrough(
        new TransformStream({
          transform(chunk, out) {
            got += chunk.byteLength;
            seen[name] = wire ? Math.min(got * ratio, wire) : got;
            tell();
            out.enqueue(chunk);
          },
        }),
      );
      return new Response(counted, { status: res.status, statusText: res.statusText, headers: res.headers });
    } catch {
      return res;
    }
  };
  return (finished = false) => {
    globalThis.fetch = real;
    if (finished) {
      // The two files loaded as scripts rather than fetched are in by now.
      for (const name of ["pyodide.mjs", "pyodide.asm.js"]) seen[name] = FILES[name][0];
      tell();
    }
  };
}

/**
 * Warms the browser's HTTP cache with Pyodide's files while nothing else is
 * happening, so the first Sheet to Anki or Create sheet visit after the landing
 * page does not start with a 6 MB wait. Never on mobile data or Save-Data —
 * a page nobody has asked anything of must not spend somebody's plan — and
 * never more than once per page. Failures are ignored: it is only a head start.
 */
export function prefetchPython(nav = globalThis.navigator) {
  if (onMobileData(nav) || nav?.connection?.saveData) return false;
  const idle = globalThis.requestIdleCallback || ((fn) => setTimeout(fn, 2000));
  idle(
    () => {
      for (const name of Object.keys(FILES)) {
        fetch(BASE + name, { priority: "low" })
          .then((res) => res.arrayBuffer())
          .catch(() => {});
      }
    },
    { timeout: 8000 },
  );
  return true;
}

// The pure layer, in dependency order. tests/test_pure_modules.py reads this very
// list and fails if it stops matching the modules it proves importable without Anki.
export const PURE_MODULES = [
  "errors", "column_model", "sheet_config", "card_layout", "tsv_model", "apkg",
  // Reads a shared Anki deck (.apkg/.colpkg) back into sheets, for workbook.
  "apkg_read",
  // Reads an uploaded file, and the file a Google Sheets link downloads to when a
  // deck names a sheet inside it. Shared with the add-on, so both agree.
  "workbook",
];

/**
 * Loads Pyodide and rebuilds the add-on's package layout inside it.
 *
 * The files go under /sc so the relative imports between them resolve exactly
 * as they do inside Anki — `from .column_model import …` has to mean the same
 * thing in both places or the preview is previewing something else.
 *
 * @param {string} source Python to run once the package is in place.
 * @param {(step: "boot"|"code") => void} [onStep] progress, for a status line.
 * @param {(done: number, total: number) => void} [onBytes] bytes downloaded so
 *   far out of FIRST_LOAD_BYTES; from the HTTP cache it races to the total.
 */
export async function startPython(source, onStep = () => {}, onBytes = () => {}) {
  onStep("boot");
  const restore = countDownloads(onBytes);
  let py;
  try {
    const { loadPyodide } = await import(PYODIDE);
    py = await loadPyodide({ indexURL: BASE });
    // apkg builds a SQLite file, and Pyodide keeps sqlite3 out of the base image.
    await py.loadPackage("sqlite3");
  } finally {
    restore(Boolean(py));
  }

  onStep("code");
  py.FS.mkdir("/sc");
  py.FS.writeFile("/sc/__init__.py", "");
  await Promise.all(
    PURE_MODULES.map(async (name) => {
      // `no-cache` revalidates rather than refetches: the browser still sends its
      // ETag and still gets a 304 for an unchanged module. What it cannot do is
      // answer from disk without asking. GitHub Pages serves these with
      // `max-age=600`, so without this a deploy is invisible for ten minutes —
      // the page keeps running the previous version of the add-on's own code and
      // reports a setting the sheet does have as one it has never heard of. Every
      // other request here is a CDN asset that may safely be stale; these seven
      // files are the one thing on the page that must be the deployed ones.
      // Beside this module rather than beside the page, which may be a folder down.
      const res = await fetch(new URL(`./sc/${name}.py`, import.meta.url), { cache: "no-cache" });
      if (!res.ok) throw new Error(`could not load ${name}.py (${res.status})`);
      py.FS.writeFile(`/sc/${name}.py`, await res.text());
    }),
  );
  py.runPython('import sys; sys.path.insert(0, "/")');
  py.runPython(source);
  return py;
}
