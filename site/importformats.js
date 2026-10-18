/**
 * What someone brings from somewhere else, read as a sheet: no DOM, no network.
 *
 * Three questions, each answered in one place so every way in agrees:
 *
 *   headerVerdict(rows)       is the first row column names, or the first card?
 *                             (an uploaded .csv/.txt in Sheet to Anki, a file
 *                             opened in Create sheet, a pasted list)
 *   detectRowSeparator(text)  where does one card end? A newline, or — in a
 *                             Quizlet export set to "between rows: ;" or a custom
 *                             mark — something repeated along a single line
 *   pasteGrid({...})          a pasted list as the Basic sheet Sheet to Anki reads
 *
 * The splitting of one line into front and back is site/wordlist.js's
 * (parseList); `readPaste` only decides the rows and the header around it.
 * tests/test_site_importformats.py runs all of it in node.
 */

import { parseList, splitBy, detectSeparator } from "./wordlist.js";
import { markerGet, markerSet } from "./identity.js";

// ---------------------------------------------------------------------------
// A whole sheet pasted as text (what an AI assistant answers with)
// ---------------------------------------------------------------------------

/** The text inside a ```csv … ``` fence, or the text itself when it has none. */
export function unfence(text) {
  const body = String(text ?? "").replace(/\r\n?/g, "\n").replace(/^﻿/, "");
  const fence = body.match(/^\s*(`{3,}|~{3,})[^\n]*\n([\s\S]*?)\n\s*\1\s*$/);
  if (fence) return fence[2];
  // A fence somewhere in a longer answer ("Here is your sheet: ```csv …```").
  const inner = body.match(/(?:^|\n)\s*(`{3,}|~{3,})\s*(?:csv|tsv|text|plain)?[^\n]*\n([\s\S]*?)\n\s*\1/i);
  return inner ? inner[2] : body;
}

/**
 * CSV or TSV as rows, RFC 4180: a quoted cell may hold the separator, a line
 * break and a doubled quote. The same reading csv.reader gives workbook.py.
 */
export function parseDelimited(text, delimiter) {
  const rows = [[""]];
  let quoted = false;
  const s = String(text ?? "").replace(/\r\n?/g, "\n");
  const push = (ch) => {
    const row = rows[rows.length - 1];
    row[row.length - 1] += ch;
  };
  for (let i = 0; i < s.length; i++) {
    const ch = s[i];
    if (quoted) {
      if (ch !== '"') push(ch);
      else if (s[i + 1] === '"') (push('"'), i++);
      else quoted = false;
      continue;
    }
    const row = rows[rows.length - 1];
    if (ch === '"' && row[row.length - 1] === "") quoted = true;
    else if (ch === delimiter) row.push("");
    else if (ch === "\n") rows.push([""]);
    else push(ch);
  }
  while (rows.length > 1 && rows[rows.length - 1].every((c) => c === "")) rows.pop();
  return rows;
}

/** workbook.sniff_delimiter: whichever of tab, ";", "," splits the first record widest. */
export function sniffDelimiter(text) {
  let best = "\t";
  let widest = 1;
  for (const d of ["\t", ";", ","]) {
    const width = parseDelimited(text, d)[0].length;
    if (width > widest) [best, widest] = [d, width];
  }
  return best;
}

const MARKER_CELL = /^#config(\s|$|[^a-z0-9])/i;

/**
 * A paste that is a whole sheet, not a list: an `ID` header, or a header row
 * with a `#config` settings row under it — what /ai.md asks an assistant to
 * write. `{rows, delimiter, name}` (`name` from `name=`, or ""), else null.
 */
export function readSheetText(text) {
  const body = unfence(text).trim();
  if (!body) return null;
  const delimiter = sniffDelimiter(body);
  const rows = parseDelimited(body, delimiter).map((r) => r.map((c) => c.trim()));
  if (rows.length < 2 || rows[0].length < 2) return null;
  const hasId = rows[0].some((c) => /^﻿?id$/i.test(c));
  const marker = (rows[1] || []).find((c) => MARKER_CELL.test(c));
  if (!hasId && !marker) return null;
  return { rows, delimiter, name: (marker && markerGet(marker, "name")) || "" };
}

/**
 * That sheet with `name=` in it: kept when it says one, else the name given,
 * written into its settings row (one is added under an ID header if it has
 * none). A sheet with no ID column has no cell for a settings row to begin
 * in, so it is left as it is and travels under the name as its title.
 */
export function namedSheet(rows, name) {
  const grid = rows.map((r) => [...r]);
  const idAt = grid[0].findIndex((c) => /^﻿?id$/i.test(c));
  if (idAt < 0 || !cleanName(name)) return grid;
  if (grid[1] && MARKER_CELL.test(grid[1][idAt] || "")) {
    if (!markerGet(grid[1][idAt], "name")) grid[1][idAt] = markerSet(grid[1][idAt], "name", cleanName(name));
  } else {
    const row = grid[0].map(() => "");
    row[idAt] = `#config name=${cleanName(name)}`;
    grid.splice(1, 0, row);
  }
  return grid;
}

// ---------------------------------------------------------------------------
// Is the first row a header?
// ---------------------------------------------------------------------------

// Column names people (and other apps' exports) actually use. Compared whole,
// after lower-casing and dropping a trailing number or bracket ("Back 2",
// "Meaning (vi)"), so a word that merely contains one of these is not a header.
const HEADER_WORDS = new Set([
  // the reserved ones are handled separately; these are content columns
  "front", "back", "term", "terms", "definition", "definitions", "word", "words",
  "meaning", "meanings", "question", "questions", "answer", "answers", "translation",
  "example", "examples", "sentence", "note", "notes", "reading", "pronunciation",
  "pinyin", "romaji", "kana", "kanji", "hanzi", "hangul", "hiragana", "katakana",
  "furigana", "ipa", "audio", "sound", "image", "picture", "photo", "text", "extra",
  "back extra", "hint", "vocab", "vocabulary", "phrase", "type", "category", "level",
  "lesson", "unit", "topic", "source", "description", "explanation", "synonym",
  "antonym", "part of speech", "pos", "gender", "plural", "context", "deck",
  "english", "vietnamese", "chinese", "japanese", "korean", "french", "german",
  "spanish", "italian", "russian", "thai", "portuguese",
  "mặt trước", "mặt sau", "từ", "từ vựng", "nghĩa", "ý nghĩa", "định nghĩa",
  "ví dụ", "câu", "câu ví dụ", "dịch", "bản dịch", "phiên âm", "cách đọc",
  "phát âm", "câu hỏi", "câu trả lời", "đáp án", "trả lời", "ghi chú", "chú thích",
  "hình", "ảnh", "hình ảnh", "âm thanh", "loại từ", "từ loại", "chủ đề", "bài",
  "hán tự", "hán việt", "âm hán việt", "chữ hán", "tiếng anh", "tiếng việt",
  "tiếng trung", "tiếng nhật", "tiếng hàn", "nghĩa tiếng việt", "nghĩa tiếng anh",
]);

const RESERVED = /^(id|sync|tags|subdeck\s*\d+)$/;

const norm = (cell) =>
  String(cell ?? "")
    .replace(/^﻿/, "")
    .normalize("NFC")
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ");

const headerish = (cell) =>
  HEADER_WORDS.has(
    norm(cell)
      .replace(/\s*\([^)]*\)$/, "")
      .replace(/\s*\d+$/, "")
      .replace(/[:*]$/, "")
      .trim(),
  );

// What a cell is written in, coarsely: enough to see that "Kanji" does not
// sit over a column of 猫 and that "Tiếng Việt" does not sit over "apple".
function scriptOf(text) {
  const s = String(text ?? "").normalize("NFC");
  if (/[぀-ヿ㐀-鿿]/.test(s)) return "cjk";
  if (/[가-힯ᄀ-ᇿ]/.test(s)) return "hangul";
  if (/[Ѐ-ӿ]/.test(s)) return "cyrillic";
  if (/[฀-๿]/.test(s)) return "thai";
  if (/[؀-ۿ]/.test(s)) return "arabic";
  if (/[ăâđêôơưĂÂĐÊÔƠƯ]|[Ạ-ỹ]|[àáảãạèéẻẽẹìíỉĩịòóỏõọùúủũụỳýỷỹỵ]/i.test(s)) return "vi";
  if (/[a-z]/i.test(s)) return "latin";
  if (/\d/.test(s)) return "digits";
  return "other";
}

function caseOf(text) {
  const first = String(text ?? "").trim().match(/\p{L}/u)?.[0];
  if (!first) return "none";
  if (first === first.toLowerCase() && first !== first.toUpperCase()) return "lower";
  if (first === first.toUpperCase() && first !== first.toLowerCase()) return "upper";
  return "none";
}

const majority = (values) => {
  const counts = new Map();
  for (const v of values) counts.set(v, (counts.get(v) || 0) + 1);
  let best = null;
  let n = 0;
  for (const [v, c] of counts) if (c > n) [best, n] = [v, c];
  return { value: best, share: values.length ? n / values.length : 0 };
};

// A cell no column name looks like: a sentence, an address, markup, a cloze.
const dataCell = (cell) => {
  const s = String(cell ?? "").trim();
  return (
    s.length > 40 ||
    /[.?!。？！…]$/.test(s) ||
    /^\d+([.,]\d+)?$/.test(s) ||
    /^https?:\/\//i.test(s) ||
    /<[a-z][^>]*>|\{\{c\d+::/i.test(s)
  );
};

/**
 * Whether the first row of a grid is its column names.
 *
 *   {header: true|false, strong: bool, why}
 *
 * `strong` is true when the row says so itself — a reserved header (ID, SYNC,
 * TAGS, SUBDECK n), a settings row under it, or a column name people use — and
 * `why` names the reason. Otherwise the row is a card when it looks like the
 * rows under it (each cell in the script and capitalisation of its column) or
 * plainly is data (a sentence, a number, an address); and a header when it does
 * not, which is also the answer when there is nothing to compare it with —
 * keeping a sheet's own column names matters more than one card.
 */
export function headerVerdict(rows) {
  const grid = (rows || []).filter((r) => r && r.some((c) => String(c ?? "").trim()));
  const first = grid[0] || [];
  const cells = first.map(norm);
  if (cells.some((c) => RESERVED.test(c))) return { header: true, strong: true, why: "reserved" };
  if ((grid[1] || []).some((c) => /^#config(\s|$|[^a-z0-9])/i.test(String(c ?? "").trim()))) {
    return { header: true, strong: true, why: "config" };
  }
  if (first.some(headerish)) return { header: true, strong: true, why: "named" };
  if (grid.length < 2) return { header: true, strong: false, why: "alone" };
  const filled = cells.filter(Boolean);
  if (new Set(filled).size < filled.length) return { header: false, strong: false, why: "repeated" };
  if (first.some(dataCell)) return { header: false, strong: false, why: "data" };
  const below = grid.slice(1, 41);
  let compared = 0;
  for (let col = 0; col < first.length; col++) {
    const cell = String(first[col] ?? "").trim();
    const values = below.map((r) => String(r[col] ?? "").trim()).filter(Boolean);
    if (!cell || !values.length) continue;
    compared++;
    const script = majority(values.map(scriptOf));
    const kase = majority(values.map(caseOf));
    if (script.share >= 0.6 && scriptOf(cell) !== script.value) return { header: true, strong: false, why: "unlike" };
    if (kase.share >= 0.6 && kase.value !== "none" && caseOf(cell) !== kase.value) {
      return { header: true, strong: false, why: "unlike" };
    }
  }
  return compared ? { header: false, strong: false, why: "alike" } : { header: true, strong: false, why: "alone" };
}

/** Column names for a grid that has none: Mặt trước, Mặt sau, Mặt sau 2… */
export function synthHeaders(width, language = "vi") {
  const [front, back] = language === "en" ? ["Front", "Back"] : ["Mặt trước", "Mặt sau"];
  return Array.from({ length: Math.max(2, width) }, (_, i) => (i === 0 ? front : i === 1 ? back : `${back} ${i}`));
}

/**
 * A grid with a header row for sure: its own when it has one, else made up.
 * `header` overrides the verdict (true / false), "auto" asks headerVerdict.
 */
export function withHeaders(rows, { header = "auto", language = "vi" } = {}) {
  const grid = (rows || []).map((r) => [...r]);
  const has = header === "auto" ? headerVerdict(grid).header : Boolean(header);
  if (has || !grid.length) return { rows: grid, synthesized: false };
  const width = Math.max(...grid.map((r) => r.length));
  return { rows: [synthHeaders(width, language), ...grid], synthesized: true };
}

// ---------------------------------------------------------------------------
// Where a card ends
// ---------------------------------------------------------------------------

/** A run of marks: what Quizlet's "between rows: custom" is usually set to. */
const MARK_RUN = /[^\p{L}\p{N}\s]{1,3}/gu;

/**
 * How a paste separates its cards: `{id: "newline"}`, or `{id: "token", token}`
 * for a single line in which one mark repeats and splits it into records that
 * each split again into a front and a back (Quizlet's "between rows: ;").
 */
export function detectRowSeparator(text) {
  const body = String(text ?? "").replace(/\r\n?/g, "\n").trim();
  const lines = body.split("\n").filter((l) => l.trim());
  if (lines.length !== 1) return { id: "newline" };
  const line = lines[0];
  const tokens = new Set([";", ...(line.match(MARK_RUN) || [])]);
  let best = null;
  for (const token of tokens) {
    if (/^[-.:'"()]$/.test(token)) continue;
    const records = line.split(token).map((r) => r.trim()).filter(Boolean);
    if (records.length < 2) continue;
    const sep = detectSeparator(records);
    if (sep === "none") continue;
    const split = records.filter((r) => splitBy(r, sep).length >= 2).length;
    if (split < Math.max(2, Math.ceil(records.length * 0.8))) continue;
    const score = split * 10 + (token === ";" ? 1 : 0) + token.length;
    if (!best || score > best.score) best = { token, score };
  }
  return best ? { id: "token", token: best.token } : { id: "newline" };
}

/** The records of a paste, one per line, given how its cards are separated. */
export function splitRecords(text, rowSeparator = { id: "newline" }) {
  const body = String(text ?? "").replace(/\r\n?/g, "\n");
  if (rowSeparator?.id !== "token" || !rowSeparator.token) return body;
  return body
    .split(rowSeparator.token)
    .map((r) => r.replace(/\s*\n\s*/g, " ").trim())
    .filter(Boolean)
    .join("\n");
}

/**
 * A paste read as cards.
 *
 *   readPaste(text, {rows: "auto"|"newline"|<token>, separator, existing})
 *     → parseList's {separator, rows, duplicates, marks, skipped}, plus
 *       rowSeparator ({id, token}) and header (the pasted column names, or null)
 *
 * A first line that names its columns the way a sheet would (Term / Definition,
 * Mặt trước / Mặt sau) is taken as the names and is not a card.
 */
export function readPaste(text, { rows = "auto", separator = "auto", existing = [] } = {}) {
  const rowSeparator =
    rows === "auto" ? detectRowSeparator(text) : rows === "newline" ? { id: "newline" } : { id: "token", token: rows };
  const body = splitRecords(text, rowSeparator);
  let parsed = parseList(body, { separator, existing });
  let header = null;
  if (parsed.rows.length >= 2 && parsed.separator !== "none") {
    const verdict = headerVerdict(parsed.rows);
    if (verdict.header && verdict.strong) {
      header = parsed.rows[0];
      const rest = body.replace(/\r\n?/g, "\n").split("\n");
      const at = rest.findIndex((l) => l.trim());
      rest.splice(at, 1);
      parsed = parseList(rest.join("\n"), { separator: parsed.separator, existing });
    }
  }
  return { ...parsed, rowSeparator, header };
}

// ---------------------------------------------------------------------------
// A pasted list as a sheet
// ---------------------------------------------------------------------------

/** column_model.id_text: NFC, trimmed, inner whitespace collapsed, case kept. */
export const idText = (value) => String(value ?? "").normalize("NFC").split(/\s+/).filter(Boolean).join(" ");

/**
 * column_model.derived_ids, the same keys a sheet with no ID column gets: the
 * word itself, and " (2)", " (3)" for a word written again (case-insensitive).
 * tests/test_site_importformats.py checks the two agree.
 */
export function derivedIds(values) {
  const out = [];
  const taken = new Set();
  const counts = new Map();
  // Python's casefold and JS's toLowerCase agree on every letter a word list
  // here is written in; ß is the one that differs, so it is folded by hand.
  const fold = (s) => s.toLowerCase().replace(/ß/g, "ss");
  for (const value of values) {
    const text = idText(value);
    if (!text) {
      out.push("");
      continue;
    }
    const key = fold(text);
    let count = (counts.get(key) || 0) + 1;
    let candidate = count === 1 ? text : `${text} (${count})`;
    while (taken.has(fold(candidate))) {
      count += 1;
      candidate = `${text} (${count})`;
    }
    counts.set(key, count);
    taken.add(fold(candidate));
    out.push(candidate);
  }
  return out;
}

/** A name as `name=` can hold it: one line, no `;` (which ends a setting). */
export function cleanName(name) {
  return cleanNameText(name);
}
const cleanNameText = (name) =>
  String(name ?? "")
    .replace(/[;\t\r\n]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 100)
    .trim();

/**
 * The sheet a pasted list becomes: Basic, named.
 *
 *   ID | Mặt trước | Mặt sau | Mặt sau 2 …
 *   #config name=<name>
 *   <word> | <word> | <meaning> …
 *
 * The ID column holds the word itself (derivedIds) — exactly the key a sheet
 * with no ID column is given by the parser — so pasting the same list again
 * under the same name, with lines added, updates the notes already imported
 * and adds the new ones. It is written out rather than left to the parser
 * because a settings row needs an ID cell to sit in. A row with nothing on the
 * front has no key and is left out.
 */
export function pasteGrid({ name, rows, header = null, language = "vi" }) {
  const kept = (rows || []).filter((r) => idText(r[0]));
  const width = Math.max(2, header?.length || 0, ...kept.map((r) => r.length));
  const names = synthHeaders(width, language).map((fallback, i) => {
    const own = String(header?.[i] ?? "").trim();
    return own && !RESERVED.test(norm(own)) ? own : fallback;
  });
  const ids = derivedIds(kept.map((r) => r[0]));
  const marker = `#config name=${cleanName(name)}`;
  return [
    ["ID", ...names],
    [marker, ...names.map(() => "")],
    ...kept.map((r, i) => [ids[i], ...names.map((_, c) => String(r[c] ?? ""))]),
  ];
}
