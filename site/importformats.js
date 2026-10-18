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

import { cleanLines, columnRoles, parseList, splitBy, detectSeparator } from "./wordlist.js";
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
  // The text format (readPaste): a #config line on top, or a Markdown table.
  if (MARKER_CELL.test(body) || /^\|/.test(body)) return null;
  const delimiter = sniffDelimiter(body);
  const rows = parseDelimited(body, delimiter).map((r) => r.map((c) => c.trim()));
  if (rows.length < 2 || rows[0].length < 2) return null;
  const hasId = rows[0].some((c) => /^﻿?id$/i.test(c));
  const marker = (rows[1] || []).find((c) => MARKER_CELL.test(c));
  if (!hasId && !marker) return null;
  if (rows[0].some((c) => headerCell(c).cell)) return null;
  return { rows, delimiter, name: (marker && markerGet(marker, "name")) || "" };
}

/**
 * That sheet with `name=` in it: kept when it says one, else the name given,
 * written into its settings row — one is added when it has none. The marker
 * sits in the ID cell, or, in a sheet with no ID column, opens the first
 * column's own settings cell (sheet_config.marker_parts).
 */
export function namedSheet(rows, name) {
  const grid = rows.map((r) => [...r]);
  const idAt = Math.max(0, grid[0].findIndex((c) => /^﻿?id$/i.test(c)));
  if (!cleanName(name)) return grid;
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

// ---------------------------------------------------------------------------
// The text format: a whole set written the way a note is
// ---------------------------------------------------------------------------
//
//   #config name=Du lịch B1; theme=sakura
//   Word [tts=en_US; bold] | IPA [color=muted] | Meaning | Example [italic]
//   airport | /ˈer.pɔːrt/ | sân bay | We got to the airport early.
//
// Line 1 the deck's settings, line 2 the column names, each with its own
// settings in brackets, then one card per line. The same set can be written as
// a sheet is (names, then a `#config` row whose cells go to the columns by
// position, the first holding the deck's keys and the first column's own), and
// both make the ID-less sheet pasteGrid has always made, so nothing after this
// point knows the text was not a sheet.

/** sheet_config._DECK_KEYS (tests/test_site_importformats.py pins the copy). */
export const DECK_KEYS = ["reverse", "theme", "name", "next", "shape"];
/** sheet_config._FIELD_KEYS, plus the retired keys a column cell still reads. */
export const COLUMN_KEYS = [
  "side", "size", "color", "align", "tts", "voices", "speed", "label", "type", "subdeck",
  "math", "code", "font", "bold", "italic", "hint", "furigana", "cloze", "draw",
  "image", "audio", "video", "rtl", "sort", "vertical",
];
/** sheet_config.listed_themes(). */
export const THEMES = ["contrast", "matcha", "momiji", "paper", "sakura", "yuki"];
/** build_site.VOCAB_LANGUAGES: the tts codes the vocabulary template offers. */
export const SPOKEN = [
  ["en_US", "English (US)"], ["en_GB", "English (UK)"], ["zh_CN", "中文 (简体)"],
  ["ja_JP", "日本語"], ["ko_KR", "한국어"], ["fr_FR", "Français"], ["de_DE", "Deutsch"],
  ["es_ES", "Español"], ["vi_VN", "Tiếng Việt"],
];
/** tsv_model._IMAGE_URL: a cell that is nothing but a picture's address. */
export const IMAGE_URL = /^https?:\/\/\S+\.(?:png|jpe?g|gif|webp|svg|avif|bmp)(?:[?#]\S*)?$/i;

const keyOf = (chunk) => String(chunk).split("=", 1)[0].trim().toLowerCase();
const chunksOf = (cell) =>
  String(cell ?? "")
    .split(";")
    .map((c) => c.trim())
    .filter(Boolean);

/** A bracket that holds settings, not a word: `[italic]`, `[tts=en_US; bold]`. */
function settingsBracket(inner) {
  const chunks = chunksOf(inner);
  return !chunks.length || chunks.some((c) => c.includes("=") || COLUMN_KEYS.includes(keyOf(c)));
}

/** A column name and the settings written after it in brackets. */
export function headerCell(cell) {
  const s = String(cell ?? "").trim();
  const m = s.match(/^(.*?\S)\s*\[([^[\]]*)\]$/);
  if (m && settingsBracket(m[2])) return { name: m[1].trim(), cell: chunksOf(m[2]).join("; ") };
  return { name: s, cell: "" };
}

/** The positional cells of a `#config` line: deck keys and column 1's in the first. */
export function configCells(line) {
  return String(line ?? "")
    .trim()
    .replace(/^#config/i, "")
    .split("|")
    .map((c) => chunksOf(c).join("; "));
}

/** A marker cell's text split into the deck's keys and its column's own. */
export function splitDeck(cell) {
  const deck = [];
  const own = [];
  for (const chunk of chunksOf(String(cell ?? "").replace(/^#config/i, ""))) {
    (DECK_KEYS.includes(keyOf(chunk)) ? deck : own).push(chunk);
  }
  return { deck, own };
}

/**
 * Two settings cells for one column, merged: every key once. On a key both
 * give a value for, `over` wins, and the clash is returned so it can be said.
 */
export function mergeCells(base, over) {
  const out = chunksOf(base);
  const clashes = [];
  for (const chunk of chunksOf(over)) {
    const at = out.findIndex((c) => keyOf(c) === keyOf(chunk));
    if (at < 0) out.push(chunk);
    else {
      if (out[at] !== chunk) clashes.push(keyOf(chunk));
      out[at] = chunk;
    }
  }
  return { cell: out.join("; "), clashes };
}

const isRule = (line) => /^[\s|:-]+$/.test(line) && line.includes("|") && /-{3,}/.test(line);
const isFilled = (line) => cleanLines(line).lines.length > 0;
const tableCells = (line) => line.trim().replace(/^\|/, "").replace(/(?<!\\)\|$/, "");

// Brackets on the header line are hidden while the line is split, so a `;` or
// `=` inside one is never taken for the separator between columns.
const MASK = /\[[^[\]\n]*\]/g;
const unmask = (cell, masks) => cell.replace(/\uE000(\d+)\uE001/g, (_, i) => masks[i]);

/**
 * A paste read as cards.
 *
 *   readPaste(text, {rows: "auto"|"newline"|<token>, separator, existing, header})
 *     → parseList's {separator, rows, duplicates, marks, skipped}, plus
 *       rowSeparator ({id, token}), header (the column names, or null),
 *       headerSure (the text said so: a #config line under it, a Markdown
 *       table, known names), config (a #config line was written), cells (each
 *       column's settings, the deck's keys left out), deck (the deck's keys),
 *       warnings ([{key, col}] for i18n), table, keyAt (the key column)
 *
 * Two forms, both a sheet: the text form — `#config name=…` on line 1, the
 * column names (each may carry `[settings]`) on line 2, then the cards — and
 * the table form — names on line 1, the `#config` settings row on line 2 (a
 * CSV, a Markdown table, a copy from Sheets). A `#config` line on either line
 * makes the other one the names, always. With none, a line with settings in
 * brackets is the names, else headerVerdict decides and `header` (true /
 * false) is the reader's word against it. Plain lists, Quizlet's export and
 * notes bullets are the same reading with no names and no settings.
 */
export function readPaste(text, { rows = "auto", separator = "auto", existing = [], header = "auto" } = {}) {
  const source = unfence(text).split("\n");
  const drop = new Set();
  const lines = [...source];

  // A Markdown table: the line over the |---| rule names the columns, and
  // anything said around it ("Here is your table:") is not a card.
  const ruleAt = source.findIndex(isRule);
  let tableHead = -1;
  for (let i = ruleAt - 1; i >= 0 && tableHead < 0; i--) if (source[i].trim()) tableHead = i;
  const table = ruleAt > 0 && tableHead >= 0 && source[tableHead].includes("|");
  if (table) {
    source.forEach((line, i) => {
      if (isRule(line)) drop.add(i);
      else if (i < tableHead && !MARKER_CELL.test(line.trim())) drop.add(i);
      else if (line.includes("|")) lines[i] = tableCells(line);
    });
  }
  const filled = () => source.map((_, i) => i).filter((i) => !drop.has(i) && isFilled(lines[i]));
  const marker = (i) => i !== undefined && MARKER_CELL.test(lines[i].trim());

  // Where the #config line is, and so whether line 1 is names for certain.
  const [l0, l1] = filled();
  let configAt = -1;
  let forced = -1;
  if (marker(l0)) [configAt, forced] = [l0, l1 ?? -1];
  else if (marker(l1)) [configAt, forced] = [l1, l0];
  if (configAt >= 0) drop.add(configAt);

  // Brackets after a column name are read too (`Word [bold]`), hidden while
  // the line is split so a `;` or `=` in one is never taken for a separator.
  const masks = [];
  const candidate = forced >= 0 ? forced : filled()[0];
  if (candidate !== undefined) {
    lines[candidate] = lines[candidate].replace(MASK, (m) =>
      settingsBracket(m.slice(1, -1)) ? (masks.push(m), `${masks.length - 1}`) : m,
    );
  }
  const restore = (row) => row.map((c) => unmask(c, masks));

  let named = null;
  if (forced >= 0) drop.add(forced);
  // Names known to be names (beside a #config line, or carrying settings in
  // brackets) were written on a line of their own, and split the way the cards
  // are: so the cards are one per line, and a single card is not split at a
  // mark inside it — `{{c1::been}}` is a cloze, not RemNote's `::`.
  const namesAt = forced >= 0 ? forced : masks.length ? candidate : -1;
  const namesSep = namesAt >= 0 ? detectSeparator([lines[namesAt]]) : "none";
  const bodyText = () => filled().map((i) => lines[i]).join("\n");
  const rowSeparator = table
    ? { id: "newline" }
    : rows === "auto"
      ? forced >= 0 && namesSep !== "none"
        ? { id: "newline" }
        : detectRowSeparator(bodyText())
      : rows === "newline"
        ? { id: "newline" }
        : { id: "token", token: rows };
  const split = (sep) => parseList(splitRecords(bodyText(), rowSeparator), { separator: sep, existing });
  let parsed = split(table ? "pipe" : separator);
  // The cards read by their own marks unless the names' mark fits them better:
  // `Word | IPA` over `apple - táo` is a dashed list, but over a card holding a
  // `::` the bars are the columns. A card fits when it splits into two cells or
  // more and no more than there are names (its empty cells at the end may be
  // left off), and a tie goes to the names' mark, which is the one they chose.
  if (!table && separator === "auto" && namesSep !== "none" && namesSep !== parsed.separator) {
    const width = splitBy(lines[namesAt], namesSep).length;
    const fits = (p) => p.rows.filter((r) => r.length >= 2 && r.length <= width).length;
    const other = split(namesSep);
    if (fits(other) >= fits(parsed)) parsed = other;
  }

  // The names over a #config line: split the way the cards are, or, when that
  // does not split them, the way the line itself is written.
  if (forced >= 0) {
    const line = lines[forced];
    let parts = parsed.separator === "none" ? [line.trim()] : splitBy(line, parsed.separator);
    if (parts.length < 2) parts = splitBy(line, detectSeparator([line]));
    named = restore(parts).map(headerCell);
  }

  let sure = forced >= 0;
  let why = forced >= 0 ? "config" : "";
  let headerLine = forced;
  if (!named && parsed.rows.length >= 2 && parsed.separator !== "none") {
    const first = restore(parsed.rows[0]).map(headerCell);
    const verdict = headerVerdict([first.map((c) => c.name), ...parsed.rows.slice(1)]);
    let is = false;
    if (table) [is, sure, why] = [true, true, "table"];
    else if (masks.length || verdict.strong) [is, sure, why] = [true, true, masks.length ? "settings" : verdict.why];
    else why = verdict.why;
    if (header === true || header === false) is = header;
    if (is) {
      named = first;
      if (rowSeparator.id === "newline") {
        headerLine = filled()[0];
        drop.add(headerLine);
        parsed = split(parsed.separator);
      } else {
        const sep = parsed.separator;
        const records = splitRecords(bodyText(), rowSeparator).split("\n").filter((l) => l.trim());
        parsed = parseList(records.slice(1).join("\n"), { separator: sep, existing });
      }
    }
  }
  if (!named && masks.length) parsed.rows = parsed.rows.map((r, i) => (i ? r : restore(r)));

  const width = Math.max(named?.length || 0, ...parsed.rows.map((r) => r.length), 0);
  const keyAt = Math.max(0, (named || []).findIndex((c) => /^﻿?id$/i.test(c.name)));
  const warnings = [];

  // Each column's settings: by position from the #config line, then any
  // written after its name.
  const cells = Array.from({ length: width }, () => "");
  (configAt >= 0 ? configCells(lines[configAt]) : []).forEach((cell, i) => {
    if (i < width) cells[i] = cell;
    else if (cell) warnings.push({ key: "txExtraCell", col: i + 1 });
  });
  const mark = splitDeck(cells[keyAt]);
  cells[keyAt] = mark.own.join("; ");
  (named || []).forEach((c, i) => {
    if (!c.cell) return;
    const merged = mergeCells(cells[i], c.cell);
    cells[i] = merged.cell;
    for (const key of merged.clashes) warnings.push({ key: "txTwice", col: c.name, setting: key });
  });

  return {
    ...parsed,
    rowSeparator,
    header: named ? named.map((c) => c.name) : null,
    headerSure: sure,
    headerWhy: why,
    brackets: Boolean(masks.length),
    config: configAt >= 0,
    cells,
    deck: mark.deck,
    warnings,
    table,
    keyAt,
    lines: { config: configAt, header: headerLine },
  };
}

// ---------------------------------------------------------------------------
// A pasted list as a sheet
// ---------------------------------------------------------------------------

/** column_model.id_text: NFC, trimmed, inner whitespace collapsed, case kept. */
export const idText = (value) => String(value ?? "").normalize("NFC").split(/\s+/).filter(Boolean).join(" ");

/** A name as `name=` can hold it: one line, no `;` (which ends a setting). */
export function cleanName(name) {
  return cleanNameText(name);
}
const cleanNameText = (name) =>
  String(name ?? "")
    .replace(/[;|\t\r\n]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 100)
    .trim();

/** The deck's keys with `name=` set to `name` (first) and the others kept. */
export function namedDeck(deck, name) {
  if (!cleanName(name)) return [...(deck || [])];
  const rest = (deck || []).filter((c) => keyOf(c) !== "name");
  return [`name=${cleanName(name)}`, ...rest];
}

/**
 * The sheet a pasted list becomes: named, with no ID column.
 *
 *   Mặt trước                    | Mặt sau   | Mặt sau 2 …
 *   #config name=<name>; <cell>  | <cell>    |
 *   <word>                       | <meaning> | …
 *
 * A sheet with no ID column is keyed by its first column (column_model.
 * derived_ids: the word itself, " (2)" for a word written again), so pasting
 * the same list again under the same name, with lines added, updates the notes
 * already imported and adds the new ones. The marker opens the first column's
 * settings cell, as in Create sheet's Basic template. A row with nothing in its
 * key column has no key and is left out. `cells` are each column's settings
 * and `deck` the deck's keys other than the name; a header naming an `ID`
 * column keeps it, and the marker goes in its cell.
 */
export function pasteGrid({ name, rows, header = null, cells = [], deck = [], language = "vi" }) {
  const own = (header || []).map((h) => String(h ?? "").trim());
  const keyAt = Math.max(0, own.findIndex((h) => /^﻿?id$/i.test(h)));
  const kept = (rows || []).filter((r) => idText(r[keyAt]));
  const width = Math.max(2, own.length, ...kept.map((r) => r.length));
  const names = synthHeaders(width, language).map((fallback, i) => {
    const given = own[i] || "";
    if (!given) return fallback;
    // SYNC, TAGS and SUBDECK n keep their meaning; only one column is the ID.
    return norm(given) !== "id" || i === keyAt ? given : fallback;
  });
  const settings = names.map((_, i) => (i === keyAt ? "" : String(cells[i] ?? "")));
  const marker = [...namedDeck(deck, name), ...chunksOf(cells[keyAt])].join("; ");
  settings[keyAt] = `#config${marker ? ` ${marker}` : ""}`;
  return [names, settings, ...kept.map((r) => names.map((_, c) => String(r[c] ?? "")))];
}

/**
 * The text a reader pasted in the form the site teaches, with the settings
 * chosen written into it: `#config` and the deck's keys on line 1, the column
 * names on line 2 with each column's settings in brackets, then the cards,
 * every one exactly as written. Names are added when the text had none
 * (`names`, as the sheet will call the columns); a #config line already there
 * is replaced. A Markdown table stays a table: its #config row goes under the
 * |---| rule, as in a sheet.
 */
export function withSettings(text, model, { name, names = model.header, deck = model.deck, cells = model.cells } = {}) {
  const source = unfence(text).split("\n");
  const at = model.lines || {};
  const width = Math.max(cells.length, names?.length || 0, 1);
  const own = (i) => String(cells[i] ?? "").trim();
  const keys = namedDeck(deck, name);
  const out = [];
  if (model.table) {
    const parts = Array.from({ length: width }, (_, i) =>
      i === model.keyAt ? `#config ${[...keys, ...chunksOf(own(i))].join("; ")}`.trim() : own(i),
    );
    let pending = true;
    source.forEach((raw, i) => {
      if (i === at.config) return;
      out.push(i === at.header && model.brackets ? `| ${model.header.join(" | ")} |` : raw);
      if (pending && i > at.header && isRule(raw)) {
        out.push(`| ${parts.join(" | ")} |`);
        pending = false;
      }
    });
  } else {
    const head = Array.from({ length: width }, (_, i) => {
      const label = names?.[i] ?? "";
      return own(i) ? `${label} [${own(i)}]` : label;
    }).join(" | ");
    out.push(`#config ${keys.join("; ")}`.trimEnd(), head);
    source.forEach((raw, i) => {
      if (i !== at.config && i !== at.header) out.push(raw);
    });
  }
  while (out.length && !out[0].trim()) out.shift();
  return out.join("\n").replace(/\s+$/, "") + "\n";
}

// ---------------------------------------------------------------------------
// Settings suggested for a paste that has none
// ---------------------------------------------------------------------------

/** The voice a column's words are written for: Han, kana, Hangul; else none. */
export function guessVoice(values) {
  const text = (values || []).join(" ");
  if (/[぀-ヿ]/.test(text)) return "ja_JP";
  if (/[가-힯]/.test(text)) return "ko_KR";
  if (/[㐀-鿿]/.test(text)) return "zh_CN";
  // A Latin word could be English, French or Vietnamese without its accents:
  // guessing one would be a voice reading another language aloud.
  return "";
}

const MANAGED = new Set(["side", "tts", "voices", "speed"]);
const most = (values, test) => values.length > 0 && values.filter(test).length > values.length / 2;

/**
 * What the Cài đặt panel starts from, for a paste read by readPaste:
 *
 *   {names, content: [column index…], front (the first content column),
 *    example (a column of sentences, or -1), choices: {tts, example, theme,
 *    sides: ["front"|"back"|"hide"…]}, base: [each column's other settings]}
 *
 * A paste that already says how it looks is read back (its sides, its voice,
 * its theme, and every other key kept as written in `base`); one that says
 * nothing gets a guess: a voice from the front column's script, and, with
 * three columns or more, a place and a look for each column from its name or
 * its contents (a word in bold, a reading muted beside it, the meaning in the
 * accent colour, an example sentence in italics, picture links as pictures).
 */
export function suggestSettings(model, { language = "vi" } = {}) {
  const width = Math.max(model.header?.length || 0, model.cells?.length || 0, ...model.rows.map((r) => r.length), 2);
  const names = model.header ? [...model.header] : synthHeaders(width, language);
  while (names.length < width) names.push(synthHeaders(width, language)[names.length]);
  const values = names.map((_, i) => model.rows.map((r) => String(r[i] ?? "").trim()).filter(Boolean));
  const content = names.map((_, i) => i).filter((i) => !(model.header && /^﻿?id$/i.test(names[i])));
  const front = content[0] ?? 0;
  const defaults = names.map((_, i) => (i === front ? "front" : "back"));
  // Roles come from names the reader wrote; Mặt trước / Mặt sau name nothing.
  const roles = model.header ? columnRoles(names.map((name) => ({ name }))) : {};
  const sentences = (i) => most(values[i], (v) => /[.?!。？！]$/.test(v) && /\s|[。？！]/.test(v));
  const example = roles.example ?? content.find((i) => i !== front && sentences(i)) ?? -1;
  const given = model.config || model.brackets;
  const cells = names.map((_, i) => chunksOf(model.cells?.[i]));
  const choices = { tts: "", example: false, theme: "", sides: [...defaults] };
  const base = names.map(() => []);

  const deckTheme = (model.deck || []).find((c) => keyOf(c) === "theme");
  if (deckTheme) choices.theme = deckTheme.split("=").slice(1).join("=").trim().toLowerCase();

  if (given) {
    names.forEach((_, i) => {
      const side = cells[i].find((c) => keyOf(c) === "side");
      if (side) choices.sides[i] = side.split("=")[1]?.trim().toLowerCase() || defaults[i];
      base[i] = cells[i].filter((c) => !MANAGED.has(keyOf(c)));
    });
    const spoken = names.map((_, i) => cells[i].find((c) => keyOf(c) === "tts")?.split("=")[1]?.trim() || "");
    const at = content.find((i) => choices.sides[i] === "front" && spoken[i]) ?? content.find((i) => spoken[i]);
    choices.tts = at === undefined ? "" : spoken[at];
    choices.example = example >= 0 && Boolean(spoken[example]);
  } else {
    choices.tts = guessVoice(values[front]);
    const many = content.length >= 3;
    for (const i of content) {
      if (most(values[i], (v) => IMAGE_URL.test(v))) {
        base[i] = ["image"];
        continue;
      }
      if (!many) continue;
      const role = Object.keys(roles).find((r) => roles[r] === i);
      if (role === "word") base[i] = ["bold"];
      else if (role === "reading" || role === "ipa") {
        choices.sides[i] = "front";
        base[i] = ["color=muted"];
      } else if (role === "meaning") base[i] = ["color=accent"];
      else if (i === example) base[i] = ["italic"];
      else if (most(values[i], (v) => /^\/.+\/$/.test(v))) base[i] = ["color=muted"];
      else if (sentences(i)) base[i] = ["italic"];
    }
  }
  return { names, content, front, example, choices, base, given: Boolean(given), cells };
}

/**
 * Each column's settings, and the deck's keys, for the choices made in the
 * panel. `side=` is written only where it is not the default (the first
 * column on the front, the rest on the back), and the voice goes on the
 * first column shown on the front — and on the example column when asked.
 */
export function applySettings(suggestion, choices, deck = []) {
  const { names, content, front, example, base, cells: was } = suggestion;
  const sides = choices.sides;
  const media = (i) => base[i].some((c) => ["image", "audio", "video"].includes(keyOf(c)));
  const speaker = content.find((i) => sides[i] === "front" && !media(i)) ?? -1;
  const cells = names.map((_, i) => {
    const out = [];
    const side = sides[i] || (i === front ? "front" : "back");
    if (side !== (i === front ? "front" : "back")) out.push(`side=${side}`);
    out.push(...base[i]);
    const spoken = choices.tts && side !== "hide" && (i === speaker || (choices.example && i === example));
    if (spoken) {
      out.push(`tts=${choices.tts}`);
      // A voice the sheet named stays while the language does.
      const old = (was?.[i] || []).find((c) => keyOf(c) === "tts")?.split("=")[1]?.trim();
      if (old === choices.tts) out.push(...(was[i] || []).filter((c) => ["voices", "speed"].includes(keyOf(c))));
    }
    return out.join("; ");
  });
  const keys = (deck || []).filter((c) => keyOf(c) !== "theme");
  if (choices.theme) keys.push(`theme=${choices.theme}`);
  return { cells, deck: keys };
}
