/**
 * A pasted word list, read as rows: no DOM, no network, nothing of the page's.
 *
 * Create sheet's "Dán danh sách từ" uses it to turn what someone copied out of a
 * notes app into words, and Sheet to Anki can use it to make a deck straight from
 * pasted text. Everything here is a plain function of its arguments, so the
 * suite runs it in node (tests/test_site_wordlist.py).
 *
 *   parseList(text, {separator, existing}) →
 *     {separator, rows: [[front, back, …]], duplicates: [row index…],
 *      marks: [null | "list" | "sheet"], skipped}
 *
 * The readings (pinyin, romanisation) are the one thing that needs a library;
 * `loadReader` fetches it from site/vendor/ only when a list asks for it.
 */

// ---------------------------------------------------------------------------
// Separators
// ---------------------------------------------------------------------------

// Tried in this order, which is also the order a tie goes to: a tab is never
// typed by accident, and a spaced dash is how most people write "word - meaning".
// The dashes (- – —) need whitespace on both sides, so "well-known" stays one word; a
// colon is not split when it starts an address ("https://"), and only at its
// first occurrence, since a meaning may hold one of its own.
export const SEPARATORS = [
  { id: "tab", label: "Tab", re: /\t/ },
  // One family: a notes app turns some " - " into " – " and leaves others.
  { id: "dash", label: " - ", re: /\s+[-–—]\s+/ },
  { id: "equals", label: "=", re: /\s*=\s*/ },
  { id: "pipe", label: "|", re: /\s*\|\s*/ },
  { id: "semicolon", label: ";", re: /\s*;\s*/ },
  { id: "colon", label: ":", re: /\s*:(?!\/\/)\s*/, once: true },
  { id: "comma", label: ",", re: /\s*,\s*/, single: true },
];

const byId = (id) => SEPARATORS.find((s) => s.id === id);

/** The line split by one separator; a line without it is one part. */
export function splitBy(line, id) {
  const sep = byId(id);
  if (!sep) return [line.trim()];
  if (sep.single && (line.match(/,/g) || []).length !== 1) return [line.trim()];
  let parts;
  if (sep.once) {
    const m = line.match(sep.re);
    parts = m ? [line.slice(0, m.index), line.slice(m.index + m[0].length)] : [line];
  } else {
    parts = line.split(new RegExp(sep.re.source, "g"));
  }
  parts = parts.map((p) => p.trim());
  // "word -" or "- meaning": a separator with nothing on one side split nothing.
  if (parts.length > 1 && parts.filter(Boolean).length < 2) return [line.trim()];
  return parts;
}

// "- ", "• ", "* ", "1. ", "1) ", "☐ ": what a notes app puts in front of a line.
const BULLET = /^\s*(?:[-*•·◦▪‣–—]|\d{1,4}[.)]|[☐☑✓✔])\s+/;

/** The lines of a paste, cleaned: CRLF, bullets, trailing spaces, blanks. */
export function cleanLines(text) {
  const out = [];
  let skipped = 0;
  for (const raw of String(text ?? "").replace(/\r\n?/g, "\n").split("\n")) {
    // A line that is only spaces still holds a tab when copied from a sheet.
    const line = raw.replace(/^﻿/, "").replace(/[  ]+$/, "").replace(BULLET, "");
    if (!line.trim()) {
      skipped++;
      continue;
    }
    out.push(line);
  }
  return { lines: out, skipped };
}

/**
 * The separator that splits the most lines into the same number of parts, or
 * "none" when nothing splits anything (a list of single words).
 */
export function detectSeparator(lines) {
  let best = { id: "none", score: 0 };
  for (const sep of SEPARATORS) {
    const counts = new Map();
    for (const line of lines) {
      const n = splitBy(line, sep.id).length;
      if (n > 1) counts.set(n, (counts.get(n) || 0) + 1);
    }
    const score = Math.max(0, ...counts.values());
    if (score > best.score) best = { id: sep.id, score };
  }
  return best.id;
}

// ---------------------------------------------------------------------------
// Duplicates
// ---------------------------------------------------------------------------

/** The form two spellings of one word share: NFC, case-folded, spaces collapsed. */
export function wordKey(text) {
  return String(text ?? "")
    .normalize("NFC")
    .replace(/\s+/g, " ")
    .trim()
    .toLocaleLowerCase();
}

/**
 * The list read as rows.
 *
 * `separator` is "auto" (the default), "none", or an id from SEPARATORS.
 * `existing` are the words already in the sheet (any spelling); a row whose
 * first part is one of them, or repeats an earlier row, is marked and listed in
 * `duplicates` — it is the caller's to leave out.
 */
export function parseList(text, { separator = "auto", existing = [] } = {}) {
  const { lines, skipped } = cleanLines(text);
  const id = separator === "auto" ? detectSeparator(lines) : separator;
  const rows = lines.map((line) => (id === "none" ? [line.trim()] : splitBy(line, id)));
  const held = new Set([...existing].map(wordKey).filter(Boolean));
  const seen = new Set();
  const marks = rows.map((row) => {
    const key = wordKey(row[0]);
    if (!key) return null;
    if (held.has(key)) return "sheet";
    if (seen.has(key)) return "list";
    seen.add(key);
    return null;
  });
  const duplicates = marks.flatMap((m, i) => (m ? [i] : []));
  return { separator: id, rows, duplicates, marks, skipped };
}

// ---------------------------------------------------------------------------
// The sheet's columns
// ---------------------------------------------------------------------------

// What a column is for, from its name (in any of the languages people name
// columns in here) and its settings cell. Order matters: the first match wins.
const ROLES = [
  ["source", /^(nguồn|nguon|source|sources|credit|credits|attribution)$/],
  ["note", /^(note|notes|ghi chú|ghi chu|chú thích)$/],
  ["image", /(picture|image|ảnh|hình|photo|img)/],
  ["audio", /(audio|sound|âm thanh|recording|ghi âm)/],
  ["ipa", /^(ipa)$/],
  ["reading", /(phiên âm|phien am|pinyin|reading|romaji|romaja|romani[sz]ation|kana|furigana|cách đọc|phát âm|pronunciation|transcription)/],
  ["exampleMeaning", /(nghĩa ví dụ|dịch ví dụ|example (meaning|translation)|translation of example)/],
  ["example", /(example|ví dụ|vi du|sentence|câu)/],
  ["meaning", /(meaning|nghĩa|nghia|definition|định nghĩa|translation|dịch|back|mặt sau|answer|đáp án)/],
  ["word", /(word|từ|front|mặt trước|term|vocab|hanzi|kanji|hangul|chữ)/],
];

/** A column's role: "word", "reading", "ipa", "meaning", "example", … or "". */
export function roleOf(column) {
  const cell = String(column?.cell ?? "").toLowerCase();
  if (/(^|;)\s*image\s*(;|$)/.test(cell)) return "image";
  if (/(^|;)\s*audio\s*(;|$)/.test(cell)) return "audio";
  const name = String(column?.name ?? "").normalize("NFC").trim().toLowerCase();
  for (const [role, re] of ROLES) if (re.test(name)) return role;
  return "";
}

/** The columns' roles, each claimed by its first column only. */
export function columnRoles(columns) {
  const roles = {};
  (columns || []).forEach((col, i) => {
    const role = roleOf(col);
    if (role && !(role in roles)) roles[role] = i;
  });
  return roles;
}

/** A column a word can be written into: not media, not a deck level. */
const writable = (col) =>
  !/(^|;)\s*(image|audio|video|subdeck\s*=)/i.test(String(col?.cell ?? "")) &&
  !["image", "audio", "source"].includes(roleOf(col));

/**
 * Where each part of a row goes: an index into `columns` per part, or -1 for a
 * part left out. The first part goes to the word column (or the first column a
 * word can go into), the second to the meaning-like one, the rest to the next
 * free columns in order.
 */
export function guessMapping(columns, parts) {
  const cols = columns || [];
  const roles = columnRoles(cols);
  const used = new Set();
  const take = (i) => (i === undefined || i < 0 || used.has(i) ? -1 : (used.add(i), i));
  const firstFree = () => {
    const i = cols.findIndex((c, k) => !used.has(k) && writable(c) && roleOf(c) !== "reading");
    return i < 0 ? -1 : take(i);
  };
  const out = [];
  for (let p = 0; p < parts; p++) {
    let at = -1;
    if (p === 0) at = take(roles.word ?? cols.findIndex(writable));
    else if (p === 1) at = take(roles.meaning);
    if (at < 0) at = firstFree();
    out.push(at);
  }
  return out;
}

/** One row of values, `width` wide, with each part where `mapping` puts it. */
export function placeRow(parts, mapping, width) {
  const values = Array.from({ length: width }, () => "");
  parts.forEach((part, p) => {
    const at = mapping[p];
    if (at >= 0 && at < width && part) values[at] = values[at] ? `${values[at]}; ${part}` : part;
  });
  return values;
}

// ---------------------------------------------------------------------------
// The sheet's language, and its readings
// ---------------------------------------------------------------------------

/** The `tts=` code of the word column (or of any column), lower-case, "en_us". */
export function ttsCode(columns, wordAt = 0) {
  const codeOf = (col) => String(col?.cell ?? "").match(/(?:^|;)\s*tts\s*=\s*([a-z]{2,3}[-_][a-z0-9]{2,4})/i)?.[1];
  const own = codeOf((columns || [])[wordAt]);
  const any = (columns || []).map(codeOf).find(Boolean);
  return (own || any || "").replace("-", "_").toLowerCase();
}

/**
 * The language of a list: its `tts=` code's, else what the words are written in
 * (Hangul, kana, Han), else English for Latin script. "" when there is no telling.
 */
export function listLanguage(columns, words = [], wordAt = 0) {
  const code = ttsCode(columns, wordAt).split("_")[0];
  if (code) return code;
  const text = words.join(" ");
  if (/[가-힯ᄀ-ᇿ]/.test(text)) return "ko";
  if (/[぀-ヿ]/.test(text)) return "ja";
  if (/[一-鿿]/.test(text)) return "zh";
  if (/[a-z]/i.test(text)) return "en";
  return "";
}

// Versions are part of the file name, so a new one is a new address and never
// a stale copy from the browser's cache. Both are MIT; the licences sit beside
// them in site/vendor/.
export const VENDOR = {
  zh: "./vendor/pinyin-pro-3.29.5.min.js",
  ko: "./vendor/es-hangul-2.4.0.min.js",
};

const readers = {};

/**
 * A function from a word to its reading, for the languages that have one
 * offline (zh: pinyin, ko: romanisation), or null. The library is fetched the
 * first time a list in that language asks for it, never with the page.
 */
export async function loadReader(language) {
  const url = VENDOR[language];
  if (!url) return null;
  readers[language] ??= import(new URL(url, import.meta.url).href).then((lib) =>
    language === "zh"
      ? // Dictionaries write 一个 as yī gè, not the spoken yí gè: the reading is
        // the word's own, and tone sandhi is the speaker's to apply.
        (word) => (/[一-鿿]/.test(word) ? lib.pinyin(word, { toneSandhi: false }) : "")
      : (word) => (/[가-힯]/.test(word) ? lib.romanize(word) : ""),
  );
  try {
    return await readers[language];
  } catch (error) {
    delete readers[language];
    throw error;
  }
}
