/**
 * Create sheet's own templates: a sheet somebody already has, kept as a
 * starting point under "Template của bạn".
 *
 * What is kept is what makes a sheet a template — the column names, the
 * settings row and one word as a sample — and it is kept in this browser's
 * localStorage only. Nothing here touches the network; sharing a template with
 * someone else is Share link's job, which already packs a whole sheet into an
 * address.
 *
 * Every read and write is wrapped: a private window, cleared site data or a full
 * quota must cost the feature, never the page. The functions take the storage
 * as an argument so the test suite can hand them a plain object in node.
 */

export const STORE = "sc-sheet-templates";
// A picker, not an archive: past a dozen tiles nobody finds the one they meant.
export const MAX_TEMPLATES = 12;
// A template is step 1 of a sheet — the columns and the settings row — and the
// first word only as a sample, so its card has something to show. Picking it
// starts on an empty list of words.
export const MAX_WORDS = 1;
// One template's JSON. A sheet of pasted paragraphs is a document, not a template.
export const MAX_BYTES = 24_000;

const MARKER = /^\s*#config(\W|$)/i;

function storage(given) {
  if (given) return given;
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}

/** The kept templates, newest first; an unreadable store reads as none. */
export function listTemplates(given) {
  try {
    const raw = storage(given)?.getItem(STORE);
    const list = JSON.parse(raw || "[]");
    if (!Array.isArray(list)) return [];
    return list.filter(
      (tpl) =>
        tpl &&
        typeof tpl.id === "string" &&
        Array.isArray(tpl.rows) &&
        Array.isArray(tpl.rows[0]) &&
        tpl.rows.every((row) => Array.isArray(row)),
    );
  } catch {
    return [];
  }
}

function write(list, given) {
  try {
    const store = storage(given);
    if (!store) return false;
    store.setItem(STORE, JSON.stringify(list));
    return true;
  } catch {
    return false;
  }
}

const blank = (row) => row.slice(1).every((cell) => !String(cell ?? "").trim());

/**
 * A sheet's grid cut down to a template: row 1, the settings row if row 2 is
 * one, and the first `words` rows under it that hold anything.
 */
export function templateRows(grid, words = MAX_WORDS) {
  const rows = (grid || []).map((row) => (row || []).map((cell) => String(cell ?? "")));
  if (!rows.length) return [];
  const marked = rows[1] && rows[1].some((cell) => MARKER.test(cell));
  const head = rows.slice(0, marked ? 2 : 1);
  const body = rows.slice(head.length).filter((row) => !blank(row));
  return [...head, ...body.slice(0, words)];
}

/**
 * Keeps a grid as a template. A template of the same title is replaced rather
 * than doubled — saving the sheet again is updating it — and moves to the front.
 *
 * Returns `{ ok: true, template, replaced }` or `{ ok: false, reason }`, the
 * reason one of "empty", "full", "big" and "storage".
 */
export function keepTemplate(grid, title, given, now = Date.now()) {
  const name = String(title ?? "").trim() || "Template";
  let rows = templateRows(grid);
  if (!rows.length || !rows[0].some((cell) => cell.trim())) return { ok: false, reason: "empty" };
  const list = listTemplates(given);
  const same = list.findIndex((tpl) => tpl.title === name);
  if (same < 0 && list.length >= MAX_TEMPLATES) return { ok: false, reason: "full" };
  const make = () => ({
    id: same >= 0 ? list[same].id : `u${now.toString(36)}${Math.random().toString(36).slice(2, 6)}`,
    title: name,
    rows,
    saved: now,
  });
  let template = make();
  // A few long cells can be the whole of it: give up words before giving up.
  while (JSON.stringify(template).length > MAX_BYTES && rows.length > 2) {
    rows = rows.slice(0, -1);
    template = make();
  }
  if (JSON.stringify(template).length > MAX_BYTES) return { ok: false, reason: "big" };
  const rest = list.filter((_, i) => i !== same);
  if (!write([template, ...rest], given)) return { ok: false, reason: "storage" };
  return { ok: true, template, replaced: same >= 0 };
}

/** Forgets one template; true when it was there and the store took the change. */
export function dropTemplate(id, given) {
  const list = listTemplates(given);
  const rest = list.filter((tpl) => tpl.id !== id);
  if (rest.length === list.length) return false;
  return write(rest, given);
}
