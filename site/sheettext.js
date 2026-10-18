/**
 * A sheet written as text and read back: no DOM, no network.
 *
 * Create sheet's Văn bản view, its .txt download and its Copy văn bản all write
 * the text form the paste dialog teaches —
 *
 *   #config name=Du lịch B1; theme=sakura
 *   Word [tts=en_US; bold] | IPA [color=muted] | Meaning
 *   airport | /ˈer.pɔːrt/ | sân bay
 *
 * — and read it back through importformats.readPaste, the reading Sheet to
 * Anki gives a paste, so a set copied out of one page is the same set in the
 * other. The text form has no escape: a cell holding a `|` or a line break
 * cannot be written in it, and `textHolds` says so by writing the sheet and
 * reading it back rather than by guessing. tests/test_site_sheettext.py.
 */

import { readPaste, splitDeck, synthHeaders, withSettings } from "./importformats.js";

const ID = /^﻿?id$/i;
const MARKER = /^\s*#config(\W|$)/i;
const chunks = (cell) =>
  String(cell ?? "")
    .split(";")
    .map((c) => c.trim())
    .filter(Boolean);
const tidy = (cell) => chunks(cell).join("; ");
const keyOf = (names) => Math.max(0, names.findIndex((n) => ID.test(String(n ?? "").trim())));

/**
 * Rows of cells (names, the `#config` settings row, the words — what
 * exportGrid writes) as the text form. The deck's keys go on line 1, each
 * column's own settings in brackets after its name, then one word a line with
 * its empty cells at the end left off.
 */
export function sheetText(grid) {
  const names = (grid[0] || []).map((n) => String(n ?? "").trim());
  const keyAt = keyOf(names);
  const settings = grid[1] && MARKER.test(String(grid[1][keyAt] ?? "")) ? grid[1] : null;
  const words = grid.slice(settings ? 2 : 1);
  const mark = splitDeck(settings?.[keyAt] ?? "");
  const cells = names.map((_, i) => (i === keyAt ? mark.own.join("; ") : tidy(settings?.[i])));
  const body = words
    .map((row) => {
      const out = names.map((_, i) => String(row[i] ?? "").trim());
      while (out.length && !out[out.length - 1]) out.pop();
      // A word with nothing beside it still says where its first cell ends.
      if (out.length === 1 && names.length > 1) out.push("");
      return out.map((c, i) => (i ? ` |${c ? ` ${c}` : ""}` : c)).join("");
    })
    .filter(Boolean)
    .join("\n");
  return withSettings(body, { table: false, lines: {}, keyAt }, { name: "", names, cells, deck: mark.deck });
}

/**
 * The text form as rows of cells, in the shape exportGrid writes: names, the
 * settings row with `#config` and the deck's keys in the key column's cell
 * (the ID column, or the first), then every word, none left out.
 */
export function sheetGrid(text, { language = "vi" } = {}) {
  const m = readPaste(text);
  const width = Math.max(m.header?.length || 0, ...m.rows.map((r) => r.length), 1);
  const made = synthHeaders(width, language);
  const names = Array.from({ length: width }, (_, i) => String(m.header?.[i] ?? "").trim() || made[i]);
  const keyAt = keyOf(names);
  const settings = names.map((_, i) => {
    if (i !== keyAt) return tidy(m.cells[i]);
    const parts = [...m.deck, ...chunks(m.cells[i])];
    return `#config${parts.length ? ` ${parts.join("; ")}` : ""}`;
  });
  const rows = m.rows
    .map((r) => names.map((_, i) => String(r[i] ?? "").trim()))
    .filter((r) => r.some(Boolean));
  return { grid: [names, settings, ...rows], header: Boolean(m.header), warnings: m.warnings };
}

/** A grid as compared: cells trimmed, settings cells' spacing made one, blank words gone. */
export function sameShape(grid) {
  const width = Math.max(0, ...grid.map((r) => r.length));
  return grid
    .map((row, r) => Array.from({ length: width }, (_, i) => (r === 1 ? tidy(row[i]) : String(row[i] ?? "").trim())))
    .filter((row, r) => r < 2 || row.some(Boolean));
}

/**
 * Whether the text form holds this sheet: written and read back, the same
 * cells. `why` is "pipe" or "newline" when a cell holds one, else "other".
 */
export function textHolds(grid) {
  const want = sameShape(grid);
  const got = sameShape(sheetGrid(sheetText(grid)).grid);
  if (JSON.stringify(want) === JSON.stringify(got)) return { ok: true, why: "" };
  const cells = grid.slice(2).flat().map((c) => String(c ?? ""));
  const why = cells.some((c) => c.includes("|")) ? "pipe" : cells.some((c) => /[\r\n]/.test(c)) ? "newline" : "other";
  return { ok: false, why };
}
