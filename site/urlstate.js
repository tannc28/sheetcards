/**
 * What a page shows, written into its address and read back out of it.
 *
 * Copying the address bar is how people share a place on a site, so what the
 * reader is looking at — which sheet of a workbook, which card, its answer side —
 * goes into the query as they move, and a page opened from that address lands in
 * the same place. Written with history.replaceState by the pages: looking at
 * another card is not a step anybody wants Back to walk through one at a time.
 *
 * The rules, the same on every page:
 *  - only the keys a page declares are read or written; anything else in the
 *    address is left exactly as it was, and never acted on;
 *  - a value that is not one the key accepts is ignored, as if it were absent;
 *  - a value equal to the default is left out, so an address only says what
 *    differs from opening the page plainly.
 *
 * Pure (no DOM), so tests/test_site_urlstate.py runs it in node.
 */

/**
 * The keys each page keeps in its address. `int` is a whole number of at least
 * `min`; `enum` one of `values`; `text` any non-empty string. `def` is the
 * default, which is never written.
 */
export const CREATE_STATE = {
  // The workbook's sheet, by name: a position would move when a sheet is added.
  tab: { type: "text" },
  // The deck picked in the deck panel, below the sheet's own (Geography::Rivers).
  deck: { type: "text" },
  // The row, by its ID rather than its position, so it survives an edit above it.
  row: { type: "text" },
  side: { type: "enum", values: ["front", "back"], def: "front" },
  // Which card of the note: the template, counted from 1 (2 is a reverse card).
  card: { type: "int", min: 1, def: 1 },
  // Which deletion of a cloze note.
  cloze: { type: "int", min: 1 },
  // The Sheet view, open, on its grid or template tab.
  view: { type: "enum", values: ["grid", "template"] },
};

export const SHEET_STATE = {
  // A built-in template, its step open.
  tpl: { type: "text" },
  // The vocabulary templates' choices: the language and the two read-aloud toggles.
  lang: { type: "text" },
  word: { type: "enum", values: ["0", "1"], def: "1" },
  example: { type: "enum", values: ["0", "1"], def: "1" },
  // A theme over the template; "none" for none at all.
  theme: { type: "text" },
  // The editor's step: look (columns and card) or rows (the words).
  view: { type: "enum", values: ["look", "rows"] },
};

export const CONTACT_STATE = {
  kind: { type: "enum", values: ["bug", "feature", "other"], def: "bug" },
  from: { type: "text" },
};

/** `value` as the key accepts it, or undefined if it does not. */
function accept(spec, value) {
  if (value === null || value === undefined) return undefined;
  const text = String(value).trim();
  if (!text) return undefined;
  if (spec.type === "int") {
    if (!/^\d+$/.test(text)) return undefined;
    const n = Number(text);
    return n >= (spec.min ?? 0) ? n : undefined;
  }
  if (spec.type === "enum") return spec.values.includes(text) ? text : undefined;
  return text;
}

/**
 * The declared keys `search` (a query string, a URLSearchParams or a URL)
 * carries with an acceptable value. Absent and unacceptable keys are left out,
 * never filled in with their defaults: the page knows its own defaults.
 */
export function readState(search, schema) {
  const params =
    search instanceof URLSearchParams
      ? search
      : new URLSearchParams(typeof search === "string" ? search : search?.search || "");
  const out = {};
  for (const [key, spec] of Object.entries(schema)) {
    const value = accept(spec, params.get(key));
    if (value !== undefined) out[key] = value;
  }
  return out;
}

/**
 * A copy of `url` with the declared keys set from `values`: written when the
 * value is acceptable and not the default, removed otherwise (including a key
 * `values` does not mention). Every other parameter, and the fragment, is kept.
 */
export function writeState(url, values, schema) {
  const out = new URL(url);
  for (const [key, spec] of Object.entries(schema)) {
    const value = accept(spec, values?.[key]);
    if (value === undefined || value === spec.def) out.searchParams.delete(key);
    else out.searchParams.set(key, String(value));
  }
  return out;
}

/** A copy of `url` without any of the declared keys. */
export function clearState(url, schema) {
  return writeState(url, {}, schema);
}
