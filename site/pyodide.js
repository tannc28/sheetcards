/**
 * Putting the add-on's own Python in the browser.
 *
 * Two pages need this — the preview and the guide's editor — and the point of
 * both is that they run the code the add-on runs rather than a copy of it. So
 * the module list lives here, once: scripts/build_site.py copies exactly these
 * files into build/site/s2a/, and tests/test_pure_modules.py proves exactly
 * these still import with no Anki and no Qt anywhere near them.
 */

const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.28.3/full/pyodide.mjs";

// The pure layer, in dependency order. tests/test_pure_modules.py reads this very
// list and fails if it stops matching the modules it proves importable without Anki.
export const PURE_MODULES = [
  "errors", "column_model", "sheet_config", "card_layout", "tsv_model", "apkg",
  // Reads an uploaded file, and the file a Google Sheets link downloads to when a
  // deck names a sheet inside it. Shared with the add-on, so both agree.
  "workbook",
];

/**
 * Loads Pyodide and rebuilds the add-on's package layout inside it.
 *
 * The files go under /s2a so the relative imports between them resolve exactly
 * as they do inside Anki — `from .column_model import …` has to mean the same
 * thing in both places or the preview is previewing something else.
 *
 * @param {string} source Python to run once the package is in place.
 * @param {(step: "boot"|"code") => void} [onStep] progress, for a status line.
 */
export async function startPython(source, onStep = () => {}) {
  onStep("boot");
  const { loadPyodide } = await import(PYODIDE);
  const py = await loadPyodide({ indexURL: PYODIDE.replace("pyodide.mjs", "") });

  onStep("code");
  py.FS.mkdir("/s2a");
  py.FS.writeFile("/s2a/__init__.py", "");
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
      const res = await fetch(`./s2a/${name}.py`, { cache: "no-cache" });
      if (!res.ok) throw new Error(`could not load ${name}.py (${res.status})`);
      py.FS.writeFile(`/s2a/${name}.py`, await res.text());
    }),
  );
  py.runPython('import sys; sys.path.insert(0, "/")');
  // apkg builds a SQLite file, and Pyodide keeps sqlite3 out of the base image.
  await py.loadPackage("sqlite3");
  py.runPython(source);
  return py;
}
