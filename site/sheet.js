/**
 * Create sheet: a whole flashcard sheet, written in the browser.
 *
 * The step before Sheet to Anki, for whoever has no Google Sheet or does not want
 * one — mostly on a phone. It writes exactly what a sheet holds: the column
 * names in row 1, the settings row in row 2 and a word on every row under it,
 * and it hands that straight to Sheet to Anki (handoff.js), to a file, or to a
 * link (sharelink.js). Nothing here is a second copy of the add-on: the card
 * beside the sheet is drawn by the add-on's own Python, running in Pyodide, and
 * every warning is the add-on's own sentence.
 *
 * On a wide screen the sheet is a spreadsheet — a range, the clipboard as TSV, a
 * fill handle, undo, a right-click menu, and a block pasted out of Excel adding
 * rows. On a phone it is a list of words, each opening as a form with one large
 * field per column, because typing into a grid of tiny cells with a thumb is
 * the thing this page exists to spare people.
 *
 * The draft is kept in this browser's localStorage after every change, so a
 * reload or a closed tab never costs a word.
 */

// First, so a fragment carried through Chrome's intent link is back before
// anything reads it.
import { mountInAppBanner } from "./inapp.js";
import { renderCard, escapeHtml } from "./anki.js";
import { LANGUAGES, lang, paintStrings, setLang, t } from "./i18n.js";
import { FIRST_LOAD_BYTES, mb, onMobileData, startPython } from "./pyodide.js";
import { backOnly, cardDoc, cardFrame } from "./cardframe.js";
import { icon, paintIcons } from "./icons.js";
import { deckTree, treeHtml } from "./decktree.js";
import { stashFile } from "./handoff.js";
import { site } from "./paths.js";
import { SHEET_STATE, readState, writeState } from "./urlstate.js";
import { LONG_LINK, asCsv, decodeShare, encodeShare, isShare, parseTsv, shareAddress, toTsv } from "./sharelink.js";
import { PALETTES, PIECES, TEMPLATES } from "./sheet-templates.js";
import { MAX_TEMPLATES, dropTemplate, keepTemplate, listTemplates } from "./usertemplates.js";
import { deckKey, fileIdentity, fileStem, lastShape, markerGet, markerSet, nameUsed, rememberName } from "./identity.js";
import { detectDevice } from "./devices.js";
import { warningText } from "./sheetwarnings.js";
import { mountWordPaste } from "./wordpaste.js";
import { mountSuggest } from "./suggestpanel.js";
import { withHeaders } from "./importformats.js";
import { sheetGrid, sheetText, textHolds } from "./sheettext.js";

/** What the page asks of the add-on's code. */
const SHEETPY = String.raw`
import csv
import io
import json
from sc import workbook
from sc.card_layout import build_templates, split_sides
from sc.column_model import deck_path, plan_columns
from sc.sheet_config import SheetConfig, is_config_row, parse_config_row, warning_codes
from sc.tsv_model import apply_media_rewrites, build_tags


def keys():
    """The directive names and the closed value sets, read off sheet_config.

    A closed set is the add-on's to decide, so it is sent rather than copied
    into JavaScript where it would be a second answer.
    """
    from sc.sheet_config import (
        ALIGNMENTS,
        BASIC_KEYS,
        INTERNAL_KEYS,
        MEDIA_KINDS,
        SIDES,
        THEME_COLORS,
        _DECK_KEYS,
        _FIELD_KEYS,
        listed_themes,
    )

    return json.dumps(
        {
            "field": list(_FIELD_KEYS),
            "deck": list(_DECK_KEYS),
            "basic": list(BASIC_KEYS),
            "internal": list(INTERNAL_KEYS),
            "closed": {
                "side": list(SIDES),
                "align": list(ALIGNMENTS),
                "theme": listed_themes(),
            },
            "themeColors": list(THEME_COLORS),
            "media": list(MEDIA_KINDS),
        }
    )


def _names(columns):
    """Column names as the sheet will have them, each one distinct.

    A repeated header is honoured once by plan_columns, which would silently drop
    a column from the page; spaced apart, every column keeps a cell of its own.
    """
    names = []
    for index, column in enumerate(columns):
        name = column["name"].strip() or "Column " + str(index + 1)
        while name in names:
            name += " "
        names.append(name)
    return names


def preview(payload):
    """The sheet as a sync reads it, and the card the chosen row makes.

    Built with plan_columns and parse_config_row rather than anything written
    for this page, so a column here behaves exactly as the same column would in
    a real sheet — including when the marker cell has been typed over and row 2
    has stopped being a settings row at all.
    """
    data = json.loads(payload)
    names = _names(data["columns"])
    plan = plan_columns(["ID"] + names)
    settings = {name: column["cell"] for name, column in zip(names, data["columns"])}
    settings["ID"] = data["marker"]

    if is_config_row(settings, plan):
        config = parse_config_row(settings, plan)
    else:
        config = SheetConfig()
    front, back = split_sides(plan, config)
    values = dict(zip(names, data["values"]))
    # What a sync stores: a video address as its player, a cell's line breaks
    # as <br>. The card is drawn from the stored value.
    apply_media_rewrites(values, plan, config)
    decks = [
        "::".join(deck_path(dict(zip(names, row)), plan, config))
        for row in data.get("rows", [])
    ]
    # No backticks in this string: it is a JS template literal.
    return json.dumps(
        {
            "names": names,
            "isConfig": config.present,
            "warnings": config.warnings,
            "warningCodes": warning_codes(config.warnings),
            "front": front,
            "back": back,
            "deck": deck_path(values, plan, config),
            "decks": decks,
            "tags": build_tags(values, plan, config),
            "templates": build_templates(
                plan, config, is_cloze=bool(config.cloze_field)
            ),
        },
        ensure_ascii=False,
    )


def open_file(data, name, index=0):
    """A picked file as rows of cells, plus the sheets a workbook holds."""
    out = json.loads(workbook.read_upload(data, name, int(index)))
    rows = list(csv.reader(io.StringIO(out["tsv"]), delimiter="\t"))
    return json.dumps(
        {
            "tabs": out["tabs"],
            "tab": out["tab"],
            "rows": rows,
            "encoding": out.get("encoding", ""),
            "package": out.get("package"),
        },
        ensure_ascii=False,
    )


def xlsx(payload):
    """The sheet as an .xlsx file, written by the add-on's own workbook module."""
    data = json.loads(payload)
    name = workbook.safe_sheet_name(data["name"])
    return workbook.build_xlsx({name: data["rows"]})
`;

const $ = (sel) => document.querySelector(sel);

const WIDE = matchMedia("(min-width: 60rem)");
const STILL = matchMedia("(prefers-reduced-motion: reduce)");

// The same four views of a card Sheet to Anki offers, with the same names.
const CARD_TABS = ["front", "both", "back", "template"];

// The starting points, and what each is called. The grids, and the card each
// one's first word becomes, are written by scripts/build_site.py
// (BASIC_TEMPLATES, VOCAB_LANGUAGES, CUSTOM_TEMPLATE and the others →
// sheet-templates.js); the words are here so they are translated with the rest
// of the page.
const TEMPLATE_TEXT = {
  basic: { title: "tplBasic", text: "tplBasicText", name: "tplBlankName" },
  vocab: { title: "tplVocab", text: "tplVocabText", name: "tplVocabName" },
  hanzi: { title: "tplHanzi", text: "tplHanziText", name: "tplHanziName" },
  kanji: { title: "tplKanji", text: "tplKanjiText", name: "tplKanjiName" },
  custom: { title: "tplCustom", text: "tplCustomText", name: "tplCustomName" },
  picture: { title: "tplPicture", text: "tplPictureText", name: "tplPictureName" },
  reverse: { title: "tplReverse", text: "tplReverseText", name: "tplReverseName" },
  typed: { title: "tplTyped", text: "tplTypedText", name: "tplTypedName" },
};
// What each listed theme looks like, in a few words. The list itself comes from
// sheet_config.listed_themes() at build time; a theme added there and not here
// is still offered, with the general sentence.
const THEME_TEXT = {
  contrast: "thContrast",
  matcha: "thMatcha",
  momiji: "thMomiji",
  paper: "thPaper",
  sakura: "thSakura",
  yuki: "thYuki",
};

// Each card's HTML arrives as indices into PIECES (_interned in build_site.py:
// two hundred variants share a few stylesheets); joined back once, here.
(function join(node) {
  if (Array.isArray(node)) return node.forEach(join);
  if (!node || typeof node !== "object") return;
  for (const [key, value] of Object.entries(node)) {
    if ((key === "qfmt" || key === "afmt") && Array.isArray(value)) {
      node[key] = value.map((i) => PIECES[i]).join("");
    } else join(value);
  }
})(TEMPLATES);

const byId = (id) => TEMPLATES.find((tpl) => tpl.id === id);
const BASIC = byId("basic");
const VOCAB = byId("vocab");
// Every built-in template, in one grid: the main ones, then picture, reverse
// and typed, which used to sit in a smaller row of their own further down.
// Tùy chỉnh comes last and is not a sample: it is the builder below.
const MAIN = [
  "basic",
  "vocab",
  "hanzi",
  "kanji",
  ...TEMPLATES.filter((tpl) => tpl.more).map((tpl) => tpl.id),
  "custom",
];
// Basic's columns are named in the page's language at the moment the sheet is
// made; a draft keeps them, because by then they are its field names.
const basicVariant = () => BASIC.variants[lang()] || BASIC.variants.en;

// A template somebody kept (usertemplates.js) is picked by an id of its own.
const MINE = "mine:";
const isMine = (id) => id.startsWith(MINE);
const mineOf = (id) => listTemplates().find((tpl) => MINE + tpl.id === id);

/** What a template is called and says, in the page's language. */
function textOf(id) {
  if (isMine(id)) {
    const tpl = mineOf(id);
    const made = tpl ? fromGrid(tpl.rows, tpl.title) : null;
    return {
      title: tpl?.title ?? "",
      text: made ? t("tplMineText", made.columns.length, made.rows.filter((r) => !blankRow(r)).length) : "",
      name: tpl?.title ?? "",
    };
  }
  const text = TEMPLATE_TEXT[id];
  return { title: t(text.title), text: t(text.text), name: t(text.name) };
}

/**
 * Values worth offering for each directive that takes one. Suggestions, not the
 * valid set — the closed sets arrive from sheet_config, and anything else is
 * typed into the box beside them. A key that is not here is a flag.
 */
const OPTIONS = {
  size: ["16", "20", "24", "32", "44", "64"],
  color: ["muted", "accent", "crimson", "teal", "darkorange", "#c2410c"],
  // Anki matches the code against an installed voice exactly, so full forms.
  tts: ["en_US", "en_GB", "vi_VN", "zh_CN", "zh_TW", "ja_JP", "ko_KR"],
  speed: ["0.5", "0.75", "1", "1.25", "1.5", "2"],
  subdeck: ["1", "2", "3"],
  math: ["", "block"],
  code: ["python", "javascript", "sql", "bash", "json", "html"],
  font: ["sc", "tc", "jp", "kr", "serif", "sans", "mono"],
  type: ["", "nc"],
  voices: [],
  label: [],
};

/**
 * What each directive is, and for the ones that do nothing until the cell is
 * written a certain way, a sample that fills the chosen word's cell. The i18n
 * key is written out so the unused-string guard can see it.
 */
const HELP = {
  side: { text: "helpSide" },
  size: { text: "helpSize" },
  color: { text: "helpColor" },
  align: { text: "helpAlign" },
  tts: { text: "helpTts" },
  voices: { text: "helpVoices" },
  speed: { text: "helpSpeed" },
  label: { text: "helpLabel" },
  type: { text: "helpType" },
  subdeck: { text: "helpSubdeck" },
  math: { text: "helpMath", sample: "a^2 + b^2 = c^2" },
  code: { text: "helpCode", sample: "def greet(name):\n    print('hi', name)" },
  font: { text: "helpFont" },
  bold: { text: "helpBold" },
  italic: { text: "helpItalic" },
  hint: { text: "helpHint" },
  furigana: { text: "helpFurigana", sample: "日本語[にほんご]" },
  cloze: { text: "helpCloze", sample: "The capital of France is {{c1::Paris}}." },
  draw: { text: "helpDraw", sample: "我" },
  image: {
    text: "helpImage",
    sample:
      "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/" +
      "Cat_November_2010-1a.jpg/320px-Cat_November_2010-1a.jpg",
  },
  audio: {
    text: "helpAudio",
    sample: "https://upload.wikimedia.org/wikipedia/commons/b/bd/En-us-water.ogg",
  },
  video: { text: "helpVideo", sample: "https://www.youtube.com/watch?v=jNQXAC9IVRw" },
  reverse: { text: "helpReverse" },
  theme: { text: "helpTheme" },
};

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

/** The sheet itself: everything that is saved, shared and exported. */
//
// `title` is the flashcard set's name and is always the marker's `name=` when
// the sheet has one (a legacy sheet, opened from a file written before names,
// may not — see paintNameOffer). `next` is the high-water mark of the IDs: the
// next one to hand out, written into the marker as `next=` on the way out and
// never issued below, so a deleted word's ID is never a new word's. `retired`
// are the IDs of words deleted in this draft, for warning about one typed again.
let sheet = blankSheet();

function blankSheet() {
  return { title: "", marker: "#config", columns: [], rows: [], next: null, retired: [], noId: false };
}

// ---------------------------------------------------------------------------
// A sheet with no ID column
// ---------------------------------------------------------------------------
//
// Basic and the vocabulary templates have no ID column: each word is keyed by
// its first column, exactly as the add-on and the .apkg key such a sheet
// (column_model.derived_ids). In that mode a row's `id` is derived, never typed
// or handed out — no w01, no next=, no deleted-ID list — and the settings
// row's marker shares the first column's cell on the way out (sheet_config.
// marker_parts), since there is no ID cell to put it in.

/** A cell as an ID: NFC, trimmed, inner whitespace collapsed (column_model.id_text). */
const idText = (value) => String(value ?? "").normalize("NFC").split(/\s+/).filter(Boolean).join(" ");

/** column_model.derived_ids: a repeat (ignoring case) becomes "word (2)", "word (3)". */
function derivedIds(values) {
  const taken = new Set();
  const counts = new Map();
  return values.map((value) => {
    const text = idText(value);
    if (!text) return "";
    const key = text.toLowerCase();
    let count = (counts.get(key) ?? 0) + 1;
    let candidate = count === 1 ? text : `${text} (${count})`;
    while (taken.has(candidate.toLowerCase())) candidate = `${text} (${++count})`;
    counts.set(key, count);
    taken.add(candidate.toLowerCase());
    return candidate;
  });
}

/** Writes each row's derived ID, for a sheet keyed by its first column. */
function deriveIds(of = sheet) {
  if (!of.noId) return;
  const ids = derivedIds(of.rows.map((r) => (blankRow(r) ? "" : r.values[0] ?? "")));
  of.rows.forEach((r, k) => (r.id = ids[k]));
}

// The keys a marker cell keeps for the whole sheet when it shares the first
// column's cell; the rest of that cell is the column's (sheet_config._DECK_ONLY_KEYS).
const DECK_ONLY = new Set(["reverse", "theme", "name", "next", "shape"]);

/** "#config name=X; size=40" as the sheet's marker and the first column's own cell. */
function splitMarker(cell) {
  const deck = [];
  const own = [];
  for (const part of String(cell ?? "").replace(/^\s*#config/i, "").split(";")) {
    const chunk = part.trim();
    if (!chunk) continue;
    (DECK_ONLY.has(chunk.split("=")[0].trim().toLowerCase()) ? deck : own).push(chunk);
  }
  return { marker: "#config" + (deck.length ? " " + deck.join("; ") : ""), own: own.join("; ") };
}

const ui = {
  // Whether the "Nâng cao" fold of the key chips was opened by hand.
  advOpen: false,
  stage: "empty",
  // The word the card shows, and the column the chips act on (-1: the #config
  // cell, where the deck-wide settings live).
  row: 0,
  col: 0,
  // The grid's selection — {r, c} the anchor, {r2, c2} the far corner — and the
  // one cell that has the keyboard, if any.
  sel: null,
  editing: null,
  tab: "both",
  template: 0,
  // The directive whose options are showing; one at a time.
  open: null,
  // The phone's half of the page: the words, or the columns and the card.
  view: "rows",
  // A word added from the form and not yet written in: it goes again if the
  // form is closed with it still empty.
  fresh: null,
  // How the words are shown: "table" (the grid, or a phone's list) or "text".
  form: "table",
};

let run = null;
let toXlsx = null;
let readFile = null;
let keys = { field: [], deck: [] };

// ---------------------------------------------------------------------------
// The sheet as cells
// ---------------------------------------------------------------------------
//
// Row 0 is the column names, row 1 the settings row, row 2 onward the words.
// Column -1 is column A: "ID", the #config marker, then each word's ID.

const firstWordRow = 2;
const lastRow = () => sheet.rows.length + 1;
const isMarkerCell = (cell) => /^\s*#config(\W|$)/i.test(cell ?? "");
const blankRow = (row) => row.values.every((v) => !String(v ?? "").trim());

/** Every word carries one value per column, however the columns moved. */
function fit() {
  const width = sheet.columns.length;
  for (const row of sheet.rows) {
    row.values = row.values.slice(0, width);
    while (row.values.length < width) row.values.push("");
  }
  ui.row = Math.max(0, Math.min(ui.row, sheet.rows.length - 1));
  ui.col = Math.max(-1, Math.min(ui.col, width - 1));
}

function cellAt(r, c) {
  if (c === -1) {
    if (r === 1) return sheet.marker;
    if (sheet.noId) return "";
    return r === 0 ? "ID" : (sheet.rows[r - 2]?.id ?? "");
  }
  const col = sheet.columns[c];
  if (!col) return "";
  if (r === 0) return col.name;
  if (r === 1) return col.cell;
  return sheet.rows[r - 2]?.values[c] ?? "";
}

function writeCell(r, c, text) {
  if (c === -1) {
    if (r === 1) sheet.marker = text;
    else if (r >= 2 && sheet.rows[r - 2] && !sheet.noId) sheet.rows[r - 2].id = text;
    return;
  }
  const col = sheet.columns[c];
  if (!col) return;
  if (r === 0) col.name = text;
  else if (r === 1) col.cell = text;
  else if (sheet.rows[r - 2]) sheet.rows[r - 2].values[c] = text;
}

/**
 * The next free ID, in the shape the sheet already uses.
 *
 * `w07` after `w06`, `k12` after `k11`, `w01` in an empty sheet — numbered past
 * the highest one with the same prefix rather than past the last row, so a word
 * inserted in the middle never collides with one further down.
 */
function nextId() {
  if (sheet.noId) return "";
  raiseMark();
  const ids = new Set(sheet.rows.map((r) => r.id));
  const { prefix, width } = idShape();
  // Past the high-water mark as well as past every ID in the sheet: an ID
  // that was handed out once belongs to whatever word Anki has under it.
  const mark = splitId(sheet.next);
  let n = mark && mark.prefix === prefix ? mark.n - 1 : 0;
  for (const id of ids) {
    const m = splitId(id);
    if (m && m.prefix === prefix) n = Math.max(n, m.n);
  }
  let id;
  do id = prefix + String(++n).padStart(width, "0");
  while (ids.has(id));
  sheet.next = prefix + String(n + 1).padStart(width, "0");
  return id;
}

/**
 * The deleted-word list, recovered from `next=` when a sheet comes back from a
 * file or a link: every ID of the mark's shape below it that the sheet does not
 * hold was handed out once and has gone, so typing it again is warned about as
 * in the draft it was deleted from. Nothing extra travels in the file. A gap
 * the user made by numbering by hand is warned about too — a soft warning,
 * and the right one, since nextId would never hand that ID out either. Capped
 * so a mark of w99999 over ten words is not a list of a hundred thousand.
 */
function retireGaps() {
  if (sheet.noId) return;
  const mark = splitId(sheet.next);
  if (!mark || mark.n > 5000) return;
  const held = new Set(sheet.rows.map((r) => String(r.id ?? "").trim()));
  const retired = new Set(sheet.retired);
  for (let n = 1; n < mark.n; n++) {
    const id = mark.prefix + String(n).padStart(mark.width, "0");
    if (!held.has(id) && !retired.has(id)) sheet.retired.push(id);
  }
}

/** `w07` as `{prefix: "w", n: 7, width: 2}`, or null for an ID with no number. */
function splitId(id) {
  const m = String(id ?? "").trim().match(/^(.*?)(\d+)$/);
  return m ? { prefix: m[1], n: Number(m[2]), width: m[2].length } : null;
}

/** The shape new IDs take: the mark's, else the last numbered row's, else w01. */
function idShape() {
  const shaped = [...sheet.rows].reverse().map((r) => splitId(r.id)).find(Boolean);
  return splitId(sheet.next) ?? shaped ?? { prefix: "w", width: 2 };
}

/**
 * Moves the high-water mark past every ID the sheet holds. Called before a row
 * goes away and before the sheet is written out, so an ID that existed — typed
 * or handed out — is never handed out again, even after a round trip through
 * a file (the mark travels as `next=` in the marker).
 */
function raiseMark(of = sheet) {
  if (of.noId) return;
  const mark = splitId(of.next);
  const shaped = [...of.rows].reverse().map((r) => splitId(r.id)).find(Boolean);
  const prefix = mark?.prefix ?? shaped?.prefix;
  if (prefix === undefined) return;
  const width = mark?.width ?? shaped?.width ?? 2;
  let n = mark ? mark.n - 1 : 0;
  for (const row of of.rows) {
    const m = splitId(row.id);
    if (m && m.prefix === prefix && !blankRow(row)) n = Math.max(n, m.n);
  }
  if (n > 0) of.next = prefix + String(n + 1).padStart(width, "0");
}

function newRow(values = []) {
  const row = { id: nextId(), values: [...values] };
  return row;
}

/**
 * A grid of cells — a template, an opened file, a shared link, a pasted sheet —
 * as the sheet this page edits.
 *
 * The ID column is found by name rather than assumed to be first, a settings
 * row by its marker, and a sheet with no ID column stays one: its first column
 * is the key (deriveIds), as it is to the add-on and the .apkg.
 */
function fromGrid(grid, title) {
  // A file with no header row (term, definition) is read as words, under
  // Mặt trước / Mặt sau: importformats.js decides, as it does on Sheet to Anki.
  const headed = withHeaders((grid || []).map((row) => row.map((cell) => String(cell ?? ""))), { language: lang() });
  const rows = headed.rows;
  const header = rows[0] || [];
  const idAt = header.findIndex((h) => /^\s*\ufeff?id\s*$/i.test(h));
  // No ID column: the first column is the key, and a settings row's marker
  // opens that column's own cell (splitMarker).
  const noId = idAt < 0;
  const keyAt = noId ? 0 : idAt;
  const marked = rows[1] && isMarkerCell(rows[1][keyAt]);
  const split = noId && marked ? splitMarker(rows[1][0]) : null;
  const width = Math.max(header.length, ...rows.map((r) => r.length));
  const content = [];
  for (let i = 0; i < width; i++) if (i !== idAt) content.push(i);
  const used = content.filter(
    (i) => (header[i] || "").trim() || rows.slice(1).some((r) => (r[i] || "").trim()),
  );
  const marker = split ? split.marker : marked ? rows[1][keyAt].trim() : "#config";
  const settingOf = (i) => (!marked ? "" : split && i === 0 ? split.own : (rows[1][i] || "").trim());
  const out = {
    // The sheet's own name, when it has one, over whatever the file was called.
    title: markerGet(marker, "name") ?? title ?? "",
    // `next=` and `shape=` are kept out of the cell and written back on the way
    // out (exportGrid), so the cell shows what a person wrote.
    marker: markerSet(markerSet(marker, "next", null), "shape", null),
    next: noId ? null : markerGet(marker, "next") || null,
    shape: markerGet(marker, "shape") || null,
    retired: [],
    noId,
    columns: used.map((i, n) => ({
      name: (header[i] || "").trim() || `Column ${n + 1}`,
      cell: settingOf(i),
    })),
    rows: [],
  };
  const before = sheet;
  sheet = out;
  for (const row of rows.slice(marked ? 2 : 1)) {
    const values = used.map((i) => row[i] ?? "");
    const id = idAt >= 0 ? (row[idAt] || "").trim() : "";
    if (!id && values.every((v) => !v.trim())) continue;
    sheet.rows.push({ id: id || nextId(), values });
  }
  if (!sheet.columns.length) sheet.columns.push({ name: "Front", cell: "" }, { name: "Back", cell: "" });
  if (!sheet.rows.length) sheet.rows.push(newRow());
  deriveIds(sheet);
  const made = sheet;
  sheet = before;
  if (headed.synthesized) headless.add(made);
  return made;
}

// Sheets whose first row fromGrid read as a word (importformats.withHeaders).
const headless = new WeakSet();

/**
 * What this sheet is to Sheet to Anki (apkg.resolve_identity): its name= when it
 * has one, else the file it is handed over as.
 */
function sheetIdentity(of = sheet) {
  return markerGet(of.marker, "name") !== null && of.title
    ? `name:${deckKey(of.title)}`
    : fileIdentity(`${fileBase(of)}.tsv`, "");
}

/**
 * The note type Anki has for this sheet, as the shape= code: the last download
 * made in this browser (Sheet to Anki keeps its code), else what the sheet
 * already carried from whichever device downloaded it. Written into every way
 * out, so the merge notice is right on a device that never downloaded it.
 */
function shapeMark(of = sheet) {
  const here = lastShape(sheetIdentity(of))?.code;
  if (here && here !== of.shape) of.shape = here;
  return of.shape;
}

/** The sheet as rows of text — what every way out of this page writes. */
function exportGrid(of = sheet, { mark = true } = {}) {
  // A template's own words are samples, not IDs anybody was given.
  if (mark) raiseMark(of);
  let marker = of.marker;
  if (mark && of.next && !of.noId) marker = markerSet(marker, "next", of.next);
  if (mark && shapeMark(of)) marker = markerSet(marker, "shape", of.shape);
  const words = of.rows.filter((r) => !blankRow(r));
  if (of.noId) {
    // No ID cell: the marker opens the first column's settings cell.
    const first = of.columns[0]?.cell ?? "";
    const opened = first ? `${marker}${/#config$/i.test(marker) ? " " : "; "}${first}` : marker;
    return [
      of.columns.map((c) => c.name),
      of.columns.map((c, i) => (i === 0 ? opened : c.cell)),
      ...words.map((r) => [...r.values]),
    ];
  }
  return [
    ["ID", ...of.columns.map((c) => c.name)],
    [marker, ...of.columns.map((c) => c.cell)],
    ...words.map((r) => [r.id, ...r.values]),
  ];
}

const wordCount = () => sheet.rows.filter((r) => !blankRow(r)).length;

/** A file name made of the sheet's title. */
function fileBase(of = sheet) {
  return (of.title || t("tplBlankName")).replace(/[\\/:*?"<>|]+/g, " ").trim() || "Sheet";
}

// ---------------------------------------------------------------------------
// The draft, kept in this browser
// ---------------------------------------------------------------------------

const DRAFT = "sc-sheet-draft";
let saveTimer = 0;

// The sheet as it was when last written to a file or a link, or opened from
// one. The draft lives only in this browser; the file or the link is what
// lasts and opens anywhere — so the page says when the sheet has moved on.
//
// Which of the two is *the* save depends on the device. On a computer it is the
// .csv: it opens in any spreadsheet and is easy to find again. On a phone a
// file lands in Downloads and opening it again is the hard part, while a link
// sent to oneself in Zalo or Notes is one tap — and Safari on an iPhone deletes
// a site's storage after seven days without a visit, draft included.
const DEVICE = detectDevice(navigator);
const SAVE_LINK = DEVICE !== "desktop";
let lastFiled = null;
let filedHow = "";
let draftKept = true;
const filedText = () => toTsv(exportGrid());
const isFiled = () => lastFiled === filedText();
function markFiled(how) {
  lastFiled = filedText();
  filedHow = how;
  paintFiled();
  saveSoon();
}

/** The one line that says whether the sheet is kept, and where. */
function paintFiled() {
  if (ui.stage !== "edit") return;
  const n = wordCount();
  const filed = isFiled();
  $("#saveopen").classList.toggle("unsaved", !filed && n > 0);
  const [key, kind] = !n
    ? ["", ""]
    : filed
      ? [filedHow === "link" ? "shSavedLink" : "shSavedFile", "ok"]
      : !draftKept
        ? ["shNotSaved", "bad"]
        : [SAVE_LINK ? "shUnsavedLink" : "shUnsavedFile", "warn"];
  $("#saved").textContent = key ? t(key) : "";
  $("#saved").className = `saved ${kind}`;
}

/** The device's save, first in the menu and in the line under the title. */
function wireSave() {
  if (!SAVE_LINK) return;
  $("#savebox").classList.add("linkfirst");
  $("#fileline").dataset.i18n = "shFileLineLink";
}

// Said once per device, the first time it matters: what an iPhone does to a
// draft, and what an Android phone does to a .csv tapped in Files.
const NOTES = { ios: ["sc-note-ios", "shIosNote"], android: ["sc-note-android", "shAndroidCsvNote"] };
function showNote(device) {
  const [flag, key] = NOTES[device] || [];
  if (!flag || DEVICE !== device) return;
  try {
    if (localStorage.getItem(flag)) return;
    localStorage.setItem(flag, "1");
  } catch {
    // Without storage it would show every time; better not at all.
    return;
  }
  $("#devnote-text").dataset.i18n = key;
  $("#devnote-text").innerHTML = t(key);
  $("#devnote-text").hidden = false;
  // News about this device brings the note back even if it was put away.
  $("#filenote").hidden = false;
}

const NOTE_DISMISSED = "sc-filenote-dismissed";
try {
  if (localStorage.getItem(NOTE_DISMISSED)) $("#filenote").hidden = true;
} catch {
  // Without storage the note just stays.
}

// Asked once: a browser may then keep this site's storage through a clean-up.
let persistAsked = false;
function askPersist() {
  if (persistAsked || !navigator.storage?.persist) return;
  persistAsked = true;
  navigator.storage
    .persisted()
    .then((kept) => kept || navigator.storage.persist())
    .catch(() => {});
}

function loadDraft() {
  try {
    const saved = JSON.parse(localStorage.getItem(DRAFT) || "null");
    if (!saved?.sheet?.columns?.length || !Array.isArray(saved.sheet.rows)) return null;
    return saved;
  } catch {
    return null;
  }
}

/** Saved shortly after the last change, and at once when the page goes away. */
function saveSoon() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(saveNow, 300);
}

function saveNow() {
  clearTimeout(saveTimer);
  if (saveBlocked || ui.stage !== "edit") return;
  try {
    localStorage.setItem(
      DRAFT,
      JSON.stringify({ v: 1, sheet, row: ui.row, col: ui.col, view: ui.view, filed: lastFiled, how: filedHow }),
    );
    draftKept = true;
    askPersist();
  } catch {
    draftKept = false;
  }
  paintFiled();
}

function dropDraft() {
  clearTimeout(saveTimer);
  try {
    localStorage.removeItem(DRAFT);
  } catch {
    // Nothing kept, nothing to remove.
  }
}

addEventListener("pagehide", saveNow);

// One draft per browser, so two tabs editing it silently overwrite each other.
// The storage event fires only in the *other* tabs, which is exactly the one
// that needs telling. Opening the latest version reloads without saving first,
// or this tab's save on the way out would undo what it was asked to keep.
let saveBlocked = false;
addEventListener("storage", (e) => {
  if (e.key !== DRAFT || e.newValue === null || ui.stage !== "edit") return;
  $("#othertab").hidden = false;
});
$("#othertab-go").addEventListener("click", () => {
  saveBlocked = true;
  clearTimeout(saveTimer);
  location.reload();
});
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "hidden") saveNow();
});

// ---------------------------------------------------------------------------
// Undo
// ---------------------------------------------------------------------------
//
// A step is one action, not one keystroke: a run of typing in one cell is one
// step (markRun), and everything else marks a step of its own (mark).

const steps = { past: [], future: [] };
const LIMIT = 100;
let session = null;

const snapshot = () => JSON.stringify(sheet);

function commit(before) {
  steps.past.push(before);
  if (steps.past.length > LIMIT) steps.past.shift();
  steps.future.length = 0;
  session = null;
  paintUndo();
}

function mark() {
  commit(snapshot());
}

function markRun(tag) {
  if (session === tag) return;
  commit(snapshot());
  session = tag;
}

function restore(from, to) {
  if (!from.length) return false;
  session = null;
  to.push(snapshot());
  sheet = JSON.parse(from.pop());
  ui.editing = null;
  ui.sel = null;
  fit();
  paintAll();
  return true;
}

function undo() {
  if (restore(steps.past, steps.future)) toast(t("edUndone"), "ok");
}
function redo() {
  if (restore(steps.future, steps.past)) toast(t("edRedone"), "ok");
}

function paintUndo() {
  $("#undo").disabled = !steps.past.length;
  $("#redo").disabled = !steps.future.length;
}

// ---------------------------------------------------------------------------
// Saying things
// ---------------------------------------------------------------------------

let toastTimer = 0;

function toast(text, kind = "", busy = false) {
  const el = $("#toast");
  clearTimeout(toastTimer);
  el.hidden = !text;
  if (!text) return;
  el.innerHTML =
    (busy
      ? '<span class="spinner" aria-hidden="true"></span>'
      : kind === "ok"
        ? icon("check")
        : kind === "bad"
          ? icon("circle-alert")
          : "") + `<span>${escapeHtml(text)}</span>`;
  el.className = `toast ${kind}`;
  if (!busy) toastTimer = setTimeout(() => (el.hidden = true), 4200);
}

/** The line under the card: whether the settings row was understood. */
function status(text, kind = "", busy = false) {
  $("#status-text").textContent = text;
  $("#status").className = `status ${kind} ${busy ? "busy" : ""}`;
}

/**
 * A question with two answers, in the page's own dialog rather than the
 * browser's confirm(), which on a phone is a grey box with the site's address
 * in it and no way to say which button does what.
 */
function ask({ title, text, yes, no }) {
  const box = $("#askbox");
  $("#ask-title").textContent = title;
  $("#ask-text").textContent = text;
  $("#ask-yes").textContent = yes;
  $("#ask-no").textContent = no;
  return new Promise((resolve) => {
    const done = (answer) => {
      box.close();
      resolve(answer);
    };
    $("#ask-yes").onclick = () => done(true);
    $("#ask-no").onclick = () => done(false);
    box.oncancel = () => resolve(false);
    box.showModal();
    $("#ask-no").focus();
  });
}

// ---------------------------------------------------------------------------
// Theme and language
// ---------------------------------------------------------------------------

function dark() {
  return document.documentElement.dataset.theme === "dark";
}

function setTheme(on) {
  if (on) document.documentElement.dataset.theme = "dark";
  else delete document.documentElement.dataset.theme;
  try {
    localStorage.setItem("sc-theme", on ? "dark" : "light");
  } catch {
    // A browser refusing storage is not a reason to refuse the theme.
  }
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute("content", on ? "#18151f" : "#ffffff");
  paintChrome();
  if (ui.stage === "empty") paintTemplates();
  if ($("#tplbox").open) paintStep();
  drawCard();
}

function paintChrome() {
  document.documentElement.lang = lang();
  document.title = t("titleSheet");
  paintStrings();
  const button = $("#theme");
  button.innerHTML = icon(dark() ? "sun" : "moon");
  button.title = button.ariaLabel = t(dark() ? "toLight" : "toDark");
  $("#langs").innerHTML =
    `<span class="langs-icon">${icon("languages")}</span>` +
    LANGUAGES.map(
      (l) =>
        `<button data-lang="${l.code}" class="${lang() === l.code ? "on" : ""}"` +
        ` aria-pressed="${lang() === l.code}">${l.label}</button>`,
    ).join("");
}

// ---------------------------------------------------------------------------
// The two screens
// ---------------------------------------------------------------------------

function setStage(stage) {
  ui.stage = stage;
  $("#app").dataset.stage = stage;
  $("#entry").hidden = stage !== "empty";
  $("#work").hidden = stage !== "edit";
  $("#rail-deck").disabled = stage !== "edit";
  delete document.documentElement.dataset.draft;
  if (stage === "empty") paintTemplates();
  if (stage === "edit") showNote("ios");
}

/**
 * Which of the two steps is in front: "look" is step 1, the template (the
 * columns, the settings row and the card they make), "rows" step 2, the words.
 * A phone shows one at a time; a wide screen shows both and numbers them.
 */
/** Whether the grid shows row 2's cells, or the one line that sums them up. */
function cfgOpen() {
  return ui.cfgOpen || ui.view === "look";
}

/** "Cài đặt: tts, size, color…" — the keys row 2 uses, in the order met. */
function cfgSummary() {
  const keys = [];
  for (const cell of [sheet.marker.replace(/^#config\b/i, ""), ...sheet.columns.map((c) => c.cell)]) {
    for (const part of String(cell ?? "").split(";")) {
      const key = part.split("=")[0].trim().toLowerCase();
      // The set's own name and bookkeeping are not how a card looks.
      if (key && !["name", "next", "shape"].includes(key) && !keys.includes(key)) keys.push(key);
    }
  }
  return keys.length ? t("cfgSummary", keys.slice(0, 5).join(", ") + (keys.length > 5 ? "…" : "")) : t("cfgSummaryNone");
}

function paintCfgFold() {
  const open = cfgOpen();
  $("#sheet").classList.toggle("cfgopen", open);
  $("#cfgsum")?.setAttribute("aria-expanded", String(open));
}

function setView(view) {
  ui.view = view;
  paintCfgFold();
  $("#app").dataset.view = view;
  for (const b of document.querySelectorAll(".viewseg [data-view]")) {
    b.setAttribute("aria-pressed", String(b.dataset.view === view));
  }
  // A wide screen shows both steps; step 1 folds to its heading while the
  // words are being written, and this opens it again.
  $("#tplfold-text").textContent = t(view === "look" ? "shFoldTemplate" : "shEditTemplate");
  $("#tplfold").setAttribute("aria-expanded", String(view === "look"));
  syncAddress();
}

// ---- the address -----------------------------------------------------------
//
// An open template step says which template, language, read-aloud choices and
// theme it is on (?tpl=vocab&lang=en_US&theme=sakura), and the editor which of
// its two steps is in front (?view=look), so a link copied from the bar opens
// the same thing for whoever it is sent to (urlstate.js). Replaced, never pushed.
// A kept template ("mine:") lives in one browser and is left out.

/** What the page shows, as the address's query. */
function addressState() {
  if ($("#tplbox").open) {
    if (isMine(stepId) || !byId(stepId)) return {};
    const tpl = byId(stepId);
    const out = { tpl: stepId };
    if (tpl.toggles) {
      out.lang = vocabChoice.lang === VOCAB_DEFAULT.lang ? null : vocabChoice.lang;
      out.word = vocabChoice.word ? null : "0";
      if (tpl.toggles.includes("example")) out.example = vocabChoice.example ? null : "0";
    }
    if (stepTheme !== null) out.theme = stepTheme || "none";
    return out;
  }
  if (ui.stage !== "edit") return {};
  return { view: ui.view === "look" ? "look" : null, form: ui.form };
}

function syncAddress() {
  const next = writeState(location.href, addressState(), SHEET_STATE);
  if (next.href !== location.href) history.replaceState(history.state, "", next);
}

/** The template step an address asks for (?tpl=…), opened as if picked. */
function openAsked(want) {
  const tpl = byId(want.tpl);
  if (!tpl) return false;
  // Opened over a sheet being written, the step is only a look until its
  // button is pressed — which asks first (createFromStep).
  if (tpl.toggles) {
    if (VOCAB.languages.some((l) => l.code === want.lang)) vocabChoice.lang = want.lang;
    if (want.word) vocabChoice.word = want.word === "1";
    if (want.example) vocabChoice.example = want.example === "1";
  }
  pickTemplate(tpl.id);
  const theme = want.theme === "none" ? "" : want.theme;
  if (theme !== undefined && theme in PALETTES) {
    stepTheme = theme;
    paintStep();
  }
  return true;
}

/**
 * Starts editing a sheet: a template, a file, a link or the saved draft.
 * `view` is the step it opens on; `filed` is the sheet as last written to a
 * file (see isFiled), or null for a sheet no file holds yet.
 */
function begin(next, { row = 0, col = 0, keepHistory = false, view = "rows", filed = null, how = "file" } = {}) {
  if (keepHistory && ui.stage === "edit") mark();
  else {
    steps.past.length = 0;
    steps.future.length = 0;
  }
  sheet = next;
  sheet.next ??= null;
  sheet.shape ??= null;
  sheet.noId = Boolean(sheet.noId);
  if (!Array.isArray(sheet.retired)) sheet.retired = [];
  retireGaps();
  lastFiled = filed;
  filedHow = how;
  setView(view);
  ui.row = row;
  ui.col = col;
  ui.sel = null;
  ui.editing = null;
  ui.open = null;
  fit();
  setStage("edit");
  paintAll();
  saveSoon();
}

// The card a template's first word becomes: the templates and values came out
// of card_layout.py at build time, so this is the card the sheet will make,
// drawn by the same anki.js Sheet to Anki uses — no Pyodide. `reverse` draws the
// second card of a sheet that asks for one.
function templateCard(card, reverse = false) {
  const template = reverse ? card.reverse : card.template;
  const { front, back } = renderCard(template, card.values, { ordinal: reverse ? 2 : 1 });
  // A small face shows what the answer adds, not the question again.
  const answer = backOnly(back.html, front.html).replace(/^\s*<hr id="answer">/, "");
  // The question carried the note type's stylesheet; the answer alone needs it.
  const styles = (front.html.match(/<style\b[\s\S]*?<\/style>/gi) || []).join("");
  return { front, back: { html: styles + answer } };
}

/**
 * One face of a card, as a document for a frame nobody can click: no
 * scrollbars, and drawn smaller so a whole card fits a tile. A face is "front"
 * or "back", and "front2"/"back2" for the reverse card.
 */
function faceDoc(card, face, zoom = 0.6) {
  const { front, back } = templateCard(card, face.endsWith("2"));
  return cardDoc({ front, back, tab: face.replace("2", ""), dark: dark() }).replace(
    '<meta charset="utf-8">',
    `<meta charset="utf-8"><style>html { zoom: ${zoom}; } html, body { overflow: hidden; } ` +
      "body { padding: 14px 12px; }</style>",
  );
}

// The frames a face is waiting to be drawn into, and what goes in each.
const pendingFaces = new WeakMap();
// A frame is filled only when it is about to scroll into view, so a phone does
// not build every card at once to show the first one.
const facesSeen = new IntersectionObserver(
  (entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      facesSeen.unobserve(entry.target);
      entry.target.srcdoc = pendingFaces.get(entry.target)();
    }
  },
  { rootMargin: "600px 0px" },
);

const FACE_CAPTION = { front: "demoFront", back: "demoBack", front2: "tplRevFront", back2: "tplRevBack" };

/**
 * A card's faces side by side, as frames filled when seen. A compact tile has no
 * captions; `waiting` draws the outline of a card whose rendering has to wait
 * for Python (a template somebody kept, which the build has never seen).
 */
function facesHtml(key, faces = ["front", "back"], { compact = false, waiting = false } = {}) {
  // Two faces in a small tile are each a quarter of a card: drawn smaller still.
  const zoom = compact ? (faces.length > 1 ? (WIDE.matches ? 0.5 : 0.42) : 0.7) : 0.6;
  const face = (name) =>
    waiting
      ? `<figure class="tplface"><div class="facewait"><span class="sk-line w60"></span><span class="sk-line w30"></span></div></figure>`
      : `<figure class="tplface"><iframe sandbox="allow-scripts" tabindex="-1" aria-hidden="true"
      data-face="${escapeHtml(key)}" data-tab="${name}" data-zoom="${zoom}"></iframe>${
        compact ? "" : `<figcaption>${escapeHtml(t(FACE_CAPTION[name]))}</figcaption>`
      }</figure>`;
  return `<div class="tplfaces${faces.length === 1 ? " one" : ""}" aria-hidden="true">${faces.map(face).join("")}</div>`;
}

function watchFaces(root, cardFor) {
  for (const el of root.querySelectorAll("iframe[data-face]")) {
    pendingFaces.set(el, () => faceDoc(cardFor(el.dataset.face), el.dataset.tab, Number(el.dataset.zoom)));
    facesSeen.observe(el);
  }
}

// The language step's choices, shared by every template made from it: the
// words' language and which of Word and Example are read aloud. Kept for the
// visit, so reopening the step resumes.
const vocabChoice = { lang: VOCAB.languages[0].code, word: true, example: true };
const VOCAB_DEFAULT = { lang: VOCAB.languages[0].code, word: true, example: true };

/** A language template's variant for a choice; a toggle it lacks reads as off. */
function variantOf(tpl, { lang: code, word, example } = vocabChoice) {
  const spoken = tpl.toggles.includes("example") && example;
  return tpl.variants[`${code}|${Number(word)}${Number(spoken)}`];
}

/**
 * A kept template's card, drawn by the add-on's own card_layout through the
 * same preview() the editor uses — so only once Python is up. Kept per template
 * for the visit; null until then, and null for a sheet it cannot draw.
 */
const mineCards = new Map();
function mineCard(tpl) {
  if (!run) return null;
  if (mineCards.has(tpl.id)) return mineCards.get(tpl.id);
  const card = cardOfGrid(tpl.rows, tpl.title);
  mineCards.set(tpl.id, card);
  return card;
}

/** The card a grid's first word makes, drawn by preview() — null until Python is up. */
function cardOfGrid(rows, title = "") {
  if (!run) return null;
  let card = null;
  try {
    const made = fromGrid(rows, title);
    const first = made.rows.find((r) => !blankRow(r)) ?? made.rows[0];
    const out = run(
      JSON.stringify({ marker: made.marker, columns: made.columns, values: first.values, rows: [] }),
    );
    let values = { ID: first.id };
    out.names.forEach((name, i) => (values[name] = first.values[i] ?? ""));
    // A template with no word yet shows the column names, as the build does.
    if (!out.names.some((name) => String(values[name]).trim())) {
      values = Object.fromEntries(out.names.map((name) => [name, name]));
    }
    // The device's voice list and the scripts are not part of a picture of a card.
    const picture = (side) =>
      side
        .replace(/<details class="[^"]*sc-tts-debug[\s\S]*?<\/details>/g, "")
        .replace(/<script>[\s\S]*?<\/script>/g, "");
    const faces = (side) => ({ qfmt: picture(side.qfmt), afmt: picture(side.afmt) });
    card = { template: faces(out.templates[0]), values };
    if (out.templates[1]) card.reverse = faces(out.templates[1]);
  } catch {
    card = null;
  }
  return card;
}

// ---------------------------------------------------------------------------
// Tùy chỉnh: a template built here, column by column
// ---------------------------------------------------------------------------
//
// Not a sample deck: a short list of columns, each with its side and a few
// switches (read aloud, picture, typed answer, hint), the theme and the name.
// It writes an ordinary sheet with an ID column — "Tùy chỉnh nâng cao" opens
// that sheet in the full editor for everything else.

const builder = { cols: null, lang: "en_US" };
const SIDES = [
  ["front", "bSideFront"],
  ["back", "bSideBack"],
  ["hide", "bSideHide"],
];
const FLAGS = [
  ["tts", "bTts"],
  ["image", "bImage"],
  ["type", "bType"],
  ["hint", "bHint"],
];

function builderCols() {
  builder.cols ??= [
    { name: t("bFrontName"), side: "front", sample: "" },
    { name: t("bBackName"), side: "back", sample: "" },
  ];
  return builder.cols;
}

/** One column's settings cell: its side, then each switch that is on. */
function builderCell(col) {
  const language = VOCAB.languages.find((l) => l.code === builder.lang);
  const parts = [`side=${col.side}`];
  if (col.image) parts.push("image");
  if (col.type && !col.image) parts.push("type");
  if (col.hint) parts.push("hint");
  if (col.tts && !col.image) parts.push(`tts=${builder.lang}` + (language?.voice ? `; voices=${language.voice}` : ""));
  return parts.join("; ");
}

/** The sheet the builder stands for: names, settings row, the sample word. */
function builderRows() {
  const cols = builderCols();
  const names = cols.map((c, i) => c.name.trim() || t("bColN", i + 1));
  return [["ID", ...names], ["#config", ...cols.map(builderCell)], ["w01", ...cols.map((c) => c.sample)]];
}

const builderCard = () => cardOfGrid(builderRows());

function paintBuilder() {
  const cols = builderCols();
  const opt = (value, key, on) => `<option value="${value}"${on ? " selected" : ""}>${escapeHtml(t(key))}</option>`;
  $("#b-cols").innerHTML = cols
    .map(
      (col, i) => `<li class="b-col" data-i="${i}">
      <div class="b-line">
        <input class="b-name" data-b="name" value="${escapeHtml(col.name)}" spellcheck="false" autocomplete="off"
          aria-label="${escapeHtml(t("bColName"))}">
        <select data-b="side" aria-label="${escapeHtml(t("bSide"))}">${SIDES.map(([v, k]) => opt(v, k, col.side === v)).join("")}</select>
        <span class="b-move">
          <button type="button" class="iconbtn" data-b="up" ${i === 0 ? "disabled" : ""}
            title="${escapeHtml(t("bUp"))}" aria-label="${escapeHtml(t("bUp"))}">${icon("arrow-up")}</button>
          <button type="button" class="iconbtn" data-b="down" ${i === cols.length - 1 ? "disabled" : ""}
            title="${escapeHtml(t("bDown"))}" aria-label="${escapeHtml(t("bDown"))}">${icon("arrow-down")}</button>
          <button type="button" class="iconbtn" data-b="remove" ${cols.length < 2 ? "disabled" : ""}
            title="${escapeHtml(t("bRemove"))}" aria-label="${escapeHtml(t("bRemove"))}">${icon("trash-2")}</button>
        </span>
      </div>
      <div class="b-flags">${FLAGS.map(
        ([f, k]) => `<label class="b-flag"><input type="checkbox" data-b="${f}"${col[f] ? " checked" : ""}${
          (f === "tts" || f === "type") && col.image ? " disabled" : ""
        }> ${escapeHtml(t(k))}</label>`,
      ).join("")}</div>
      <input class="b-sample" data-b="sample" value="${escapeHtml(col.sample)}" spellcheck="false" autocomplete="off"
        placeholder="${escapeHtml(t("bSample"))}" aria-label="${escapeHtml(t("bSample"))}: ${escapeHtml(col.name)}">
    </li>`,
    )
    .join("");
  const spoken = cols.some((c) => c.tts && !c.image);
  $("#b-langrow").hidden = !spoken;
  $("#b-lang").innerHTML = VOCAB.languages
    .map((l) => `<option value="${l.code}"${l.code === builder.lang ? " selected" : ""}>${escapeHtml(l.label)}</option>`)
    .join("");
}

/** Redraws the builder's card, once the typing pauses. */
let builderTimer = 0;
function builderChanged({ list = false } = {}) {
  if (list) paintBuilder();
  clearTimeout(builderTimer);
  builderTimer = setTimeout(paintBuilderCard, 150);
}

function paintBuilderCard() {
  if (stepId !== "custom" || !$("#tplbox").open) return;
  const card = themedCard(builderCard(), stepTheme);
  const faces = card?.reverse ? ["front", "back", "front2", "back2"] : ["front", "back"];
  $("#tpl-card").innerHTML = facesHtml("custom", faces, { waiting: !card });
  for (const el of $("#tplbox").querySelectorAll("iframe[data-face]")) el.srcdoc = faceDoc(card, el.dataset.tab, 0.72);
}

$("#b-cols").addEventListener("input", (e) => {
  const el = e.target.closest("[data-b]");
  const li = e.target.closest(".b-col");
  if (!el || !li) return;
  const col = builderCols()[Number(li.dataset.i)];
  const what = el.dataset.b;
  if (what === "name" || what === "sample") col[what] = el.value;
  else if (what === "side") col.side = el.value;
  else if (el.type === "checkbox") {
    col[what] = el.checked;
    // Anki honours one typed answer per card.
    if (what === "type" && el.checked) for (const other of builderCols()) if (other !== col) other.type = false;
    return builderChanged({ list: true });
  }
  builderChanged({ list: what === "side" });
});
$("#b-cols").addEventListener("click", (e) => {
  const el = e.target.closest("button[data-b]");
  const li = e.target.closest(".b-col");
  if (!el || !li) return;
  const cols = builderCols();
  const i = Number(li.dataset.i);
  const to = el.dataset.b === "up" ? i - 1 : el.dataset.b === "down" ? i + 1 : null;
  if (el.dataset.b === "remove" && cols.length > 1) cols.splice(i, 1);
  else if (to !== null && to >= 0 && to < cols.length) [cols[i], cols[to]] = [cols[to], cols[i]];
  builderChanged({ list: true });
  $(`#b-cols .b-col[data-i="${Math.max(0, Math.min(to ?? i, cols.length - 1))}"] [data-b="${el.dataset.b}"]`)?.focus();
});
$("#b-add").addEventListener("click", () => {
  const cols = builderCols();
  cols.push({ name: t("bColN", cols.length + 1), side: "back", sample: "" });
  builderChanged({ list: true });
  $(`#b-cols .b-col[data-i="${cols.length - 1}"] .b-name`)?.select();
});
$("#b-lang").addEventListener("change", (e) => {
  builder.lang = e.target.value;
  builderChanged();
});

/** What a template makes right now: its rows and its first word's card. */
function templateNow(id, choice = vocabChoice) {
  if (id === "basic") return basicVariant();
  if (id === "custom") return { rows: builderRows(), card: builderCard() };
  // A template written in Vietnamese words keeps an English copy for the
  // English page (build_site.py, HANZI_TEMPLATE_EN).
  if (byId(id)?.rows) return (lang() !== "vi" && byId(id).en) || byId(id);
  if (isMine(id)) {
    const tpl = mineOf(id);
    return tpl ? { rows: tpl.rows, card: mineCard(tpl) } : null;
  }
  return variantOf(byId(id), choice);
}

/**
 * The sheet a template becomes, as Create sheet itself would write it out: the
 * rows go through the same fromGrid → exportGrid every other way in and out of
 * this page goes through, so the scrap on screen, the .csv beside it and the
 * sheet that opens are one thing.
 */
function templateSheet(id, choice, theme = stepTheme) {
  const made = fromGrid(withTheme(templateNow(id, choice).rows, theme), textOf(id).name);
  // A template names no set (saveTemplate takes it out); the step asks.
  made.marker = markerSet(made.marker, "name", null);
  made.next = null;
  made.shape = null;
  return made;
}

// ---- the theme a template is dressed in ------------------------------------
//
// A theme is a choice in the step, over any template — never a template of its
// own. null means "the template's own", which for most of them is none.
let stepTheme = null;

/** The theme a sheet's settings row names, or "" for none. */
function themeOf(rows) {
  const marker = String(rows?.[1]?.[0] ?? "");
  if (!/^#config\b/i.test(marker)) return "";
  return (marker.match(/(?:^|[\s;])theme\s*=\s*([\w-]+)/i)?.[1] ?? "").toLowerCase();
}

/** The rows with their settings row naming `theme` ("" for none, null to keep). */
function withTheme(rows, theme) {
  if (theme === null || theme === undefined || theme === themeOf(rows)) return rows;
  const out = rows.map((row) => [...row]);
  const width = out[0]?.length ?? 1;
  if (!/^#config\b/i.test(String(out[1]?.[0] ?? ""))) {
    out.splice(1, 0, ["#config", ...Array(Math.max(0, width - 1)).fill("")]);
  }
  const rest = String(out[1][0])
    .replace(/^#config/i, "")
    .split(";")
    .map((pair) => pair.trim())
    .filter((pair) => pair && !/^theme\s*=/i.test(pair));
  if (theme) rest.push(`theme=${theme}`);
  out[1][0] = "#config" + (rest.length ? " " + rest.join("; ") : "");
  return out;
}

/** A pictured card redrawn in another theme: its colour block swapped. */
function themedCard(card, theme) {
  if (!card || theme === null || !(theme in PALETTES)) return card;
  const swap = (html) => {
    for (const block of Object.values(PALETTES)) {
      if (html.includes(block)) return html.replace(block, PALETTES[theme]);
    }
    return html;
  };
  const faces = (side) => side && { qfmt: swap(side.qfmt), afmt: swap(side.afmt) };
  return { ...card, template: faces(card.template), reverse: faces(card.reverse) };
}

/** A theme's ground and accent, read out of its own colour block. */
function swatchOf(name) {
  const block = PALETTES[name] ?? "";
  const bg = block.match(/\.card \{[^}]*background-color:\s*([^;}\s]+)/)?.[1] ?? "#ffffff";
  const accent = block.match(/--sc-accent:\s*([^;}\s]+)/)?.[1] ?? "#1a73e8";
  return `--sw-bg: ${bg}; --sw-ac: ${accent}`;
}

/** The theme row of the step: none, then every listed theme. */
function paintThemes(own) {
  const chosen = stepTheme ?? own;
  $("#tpl-theme").innerHTML = Object.keys(PALETTES)
    .map((name) => {
      const label = name || t("tplThemeNone");
      const hint = name ? t(THEME_TEXT[name] || "tplThemeLabel") : t("tplThemeNoneText");
      return `<button type="button" class="themechip${name === chosen ? " on" : ""}" data-theme-pick="${name}"
          aria-pressed="${name === chosen}" title="${escapeHtml(hint)}"><span class="swatch" style="${swatchOf(name)}"></span>${escapeHtml(label)}</button>`;
    })
    .join("");
}

/** Rows drawn as a small spreadsheet: letters, row numbers, the ruled cells. */
function sheetScrap(rows) {
  const width = Math.max(...rows.map((r) => r.length));
  const shown = rows;
  const head = `<tr><th><span class="sr-only">#</span></th>${Array.from({ length: width }, (_, i) => `<th>${letter(i)}</th>`).join("")}</tr>`;
  const body = shown
    .map(
      (row, r) =>
        `<tr class="${r === 0 ? "names" : r === 1 ? "settings" : ""}"><th>${r + 1}</th>${Array.from(
          { length: width },
          (_, c) => `<td>${escapeHtml(row[c] ?? "")}</td>`,
        ).join("")}</tr>`,
    )
    .join("");
  return `<table class="scrap">${head}${body}</table>`;
}

/**
 * The template cards: the card each makes, front and back side by side, the
 * first rows of the sheet behind it, and what it is called. The whole tile is
 * the button (its ::after covers it); the frames stay pictures, since a frame
 * is interactive content and cannot go inside a <button>. The vocabulary tile
 * shows its default: English (US), both read aloud.
 */
function paintTemplates() {
  facesSeen.disconnect();
  $("#templates").innerHTML = MAIN.map((id) => {
    const text = textOf(id);
    // Tùy chỉnh is something to build, not a deck to look at: no card, a pencil.
    if (id === "custom") {
      return `<div class="tplcard tpl-own">
        <span class="tpl-own-icon" aria-hidden="true">${icon("pencil-ruler")}</span>
        <button type="button" class="tpl-go" data-template="custom">
          <strong>${escapeHtml(text.title)}</strong>
          <span class="tpl-desc">${escapeHtml(text.text)}</span>
        </button>
      </div>`;
    }
    return `<div class="tplcard">
        ${facesHtml(id, ["front"], { compact: true })}
        <button type="button" class="tpl-go" data-template="${id}">
          <strong>${escapeHtml(text.title)}</strong>
          <span class="tpl-desc">${escapeHtml(text.text)}</span>
        </button>
      </div>`;
  }).join("");
  watchFaces($("#templates"), (id) => templateNow(id, VOCAB_DEFAULT).card);
  paintMine();
}

/**
 * The templates somebody kept, and the tile that keeps another. The sheet is
 * drawn at once; the card waits for Python, since nothing at build time knew
 * what this sheet was going to be.
 */
function paintMine() {
  const list = listTemplates();
  const tiles = list.map((tpl) => {
    const id = MINE + tpl.id;
    const card = mineCard(tpl);
    const text = textOf(id);
    return `<div class="tplmini mine">
        ${facesHtml(id, ["front"], { compact: true, waiting: !card })}
        <button type="button" class="tpl-go" data-template="${escapeHtml(id)}">
          <strong>${escapeHtml(text.title)}</strong>
          <span class="tpl-desc">${escapeHtml(text.text)}</span>
        </button>
        <button type="button" class="iconbtn tpl-del" data-drop="${escapeHtml(tpl.id)}"
          title="${escapeHtml(t("tplDelete"))}" aria-label="${escapeHtml(`${t("tplDelete")}: ${tpl.title}`)}">${icon("trash-2")}</button>
      </div>`;
  });
  // Uploading one is part of this section: a kept template is either one
  // saved from the editor or one uploaded here, and both are listed above it.
  $("#tpl-upload").disabled = list.length >= MAX_TEMPLATES;
  $("#mytemplates").hidden = !list.length;
  $("#mytemplates").innerHTML = tiles.join("");
  watchFaces($("#mytemplates"), (id) => templateNow(id).card);
}

/**
 * Keeps a grid as one of this browser's templates and says how that went. The
 * grid is the sheet as exportGrid writes it, so a kept template is the sheet
 * the editor would have saved.
 */
function saveTemplate(grid, title) {
  // A template is the columns and the settings, never the set it was saved
  // from: a sheet started from it names its own set, or two sets would share
  // one deck in Anki.
  grid = grid.map((row, i) =>
    i === 1 && isMarkerCell(row[0])
      ? [markerSet(markerSet(markerSet(row[0], "name", null), "next", null), "shape", null), ...row.slice(1)]
      : row,
  );
  const kept = keepTemplate(grid, title);
  if (!kept.ok) {
    const why = { empty: "tplEmpty", full: "tplFull", big: "tplTooBig", storage: "tplNotStored" }[kept.reason];
    return toast(t(why, MAX_TEMPLATES), "bad");
  }
  mineCards.delete(kept.template.id);
  toast(t(kept.replaced ? "tplUpdated" : "tplSaved", kept.template.title), "ok");
  if (ui.stage !== "empty") return;
  paintMine();
  $(`#mytemplates [data-template="${CSS.escape(MINE + kept.template.id)}"]`)
    ?.closest(".tplmini")
    ?.scrollIntoView({ block: "nearest", behavior: STILL.matches ? "auto" : "smooth" });
}

async function forgetTemplate(id) {
  const tpl = listTemplates().find((one) => one.id === id);
  if (!tpl) return;
  const sure = await ask({
    title: t("tplDeleteTitle", tpl.title),
    text: t("tplDeleteText"),
    yes: t("tplDeleteYes"),
    no: t("shKeep"),
  });
  if (!sure) return;
  if (!dropTemplate(id)) return toast(t("tplNotStored"), "bad");
  mineCards.delete(id);
  if ($("#tplbox").open && stepId === MINE + id) $("#tplbox").close();
  paintMine();
  toast(t("tplDeleted", tpl.title), "ok");
}

// Which template the step is open on.
let stepId = "basic";

/**
 * The step between a tile and the editor: the card, the sheet that makes it,
 * and — for a template made from the vocabulary one — the language and the
 * voices. The sheet is there because it is the thing being made: the card comes
 * out of those rows, and the rows open just as well in Google Sheets or Excel
 * as here.
 */
function paintStep() {
  const box = $("#tplbox");
  const text = textOf(stepId);
  const tpl = byId(stepId);
  $("#tpl-title").textContent = text.title;
  $("#tpl-desc").textContent = text.text;
  const languaged = Boolean(tpl?.toggles);
  const building = stepId === "custom";
  box.classList.toggle("building", building);
  $("#builder").hidden = !building;
  $("#tpl-file").hidden = building;
  $("#tpl-csv").hidden = building;
  $("#tpl-advanced").hidden = !building;
  if (building) paintBuilder();
  $("#vocab-opts").hidden = !languaged;
  // Keyed by its first column (no ID column): the one trade-off, said once.
  $("#tpl-noid").hidden = /^\s*id\s*$/i.test(templateNow(stepId)?.rows?.[0]?.[0] ?? "ID");
  if (languaged) {
    const example = tpl.toggles.includes("example");
    $("#vocab-lang").innerHTML = VOCAB.languages
      .map(
        (l) =>
          `<option value="${l.code}" ${l.code === vocabChoice.lang ? "selected" : ""}>${escapeHtml(l.label)}</option>`,
      )
      .join("");
    $("#vocab-word").checked = vocabChoice.word;
    $("#vocab-example").checked = vocabChoice.example;
    $("#vocab-example").closest("label").hidden = !example;
    const language = VOCAB.languages.find((l) => l.code === vocabChoice.lang);
    // Only a language with a voice every iPhone has is spoken there as written;
    // for the rest, the voice is a download, and silence is the first sign of it.
    const spoken = vocabChoice.word || (example && vocabChoice.example);
    $("#vocab-ios").hidden = Boolean(language.voice) || !spoken;
  }
  const own = themeOf(templateNow(stepId)?.rows);
  paintThemes(own);
  const card = themedCard(templateNow(stepId).card, stepTheme ?? own);
  const faces = card?.reverse ? ["front", "back", "front2", "back2"] : ["front", "back"];
  $("#tpl-card").innerHTML = facesHtml(stepId, faces, { waiting: !card });
  // The step is open, so its frames are in view: no need to wait for them.
  for (const el of box.querySelectorAll("iframe[data-face]")) {
    el.srcdoc = faceDoc(card, el.dataset.tab, 0.72);
  }
  $("#tpl-sheet").innerHTML = sheetScrap(exportGrid(templateSheet(stepId), { mark: false }));
  syncAddress();
}

function pickTemplate(id) {
  if (isMine(id) && !mineOf(id)) return paintMine();
  stepId = id;
  stepTheme = null;
  paintStep();
  // The set's name is asked here, where the sheet is made, rather than taken
  // from the template: two sets with one name are one deck in Anki, and a
  // name nobody chose is how that happens. Suggested, and selected so typing
  // replaces it.
  const base = textOf(id).name;
  let name = base;
  for (let n = 2; nameUsed(name) && n < 50; n++) name = `${base} (${n})`;
  $("#tpl-name").value = name;
  $("#tpl-name-note").className = "tpl-namenote";
  paintNameNote();
  $("#tplbox").showModal();
  $("#tpl-name").focus();
  $("#tpl-name").select();
}

/** After an ID is typed: the warning line, and the cell's own mark. */
let idToastFor = "";
function idTyped(value) {
  paintIdWarning();
  const id = String(value).trim();
  if (sheet.retired.includes(id) && idToastFor !== id) {
    idToastFor = id;
    toast(t("idReused", id), "bad");
  }
  for (const box of document.querySelectorAll('#sheet [data-edit="id"]')) {
    const row = sheet.rows[Number(box.dataset.row)];
    if (!row) continue;
    const cell = box.closest(".cell");
    const twice = duplicates().has(row.id) || (!row.id.trim() && !blankRow(row));
    cell.classList.toggle("dup", twice);
    cell.classList.toggle("reused", !twice && sheet.retired.includes(row.id.trim()));
  }
}

/**
 * Under the name field: a name used before (the set it will update), or — only
 * once Tạo has been pressed with the field empty — that a name is needed. The
 * button itself is never greyed out.
 */
function paintNameNote(asked = false) {
  const name = $("#tpl-name").value.trim();
  const note = $("#tpl-name-note");
  const missing = !name && (asked || note.classList.contains("bad"));
  const used = Boolean(name) && nameUsed(name);
  note.textContent = missing ? t("setNameEmpty") : used ? t("setNameUsed", name) : "";
  note.className = `tpl-namenote${missing ? " bad" : ""}`;
  note.setAttribute("role", missing ? "alert" : "status");
  $("#tpl-name").setAttribute("aria-invalid", String(missing));
}

/** The step's sheet as a .csv — the same writer as Download .csv in the editor. */
function stepCsv() {
  const made = templateSheet(stepId);
  const name = `${made.title}.csv`;
  download(new Blob([asCsv(exportGrid(made, { mark: false }))], { type: "text/csv" }), name);
  toast(t("shDownloaded", name), "ok");
}

async function createFromStep({ advanced = false } = {}) {
  const name = $("#tpl-name").value.replace(/\s+/g, " ").trim().replace(/;/g, ",");
  if (!name) {
    paintNameNote(true);
    return $("#tpl-name").focus();
  }
  // Only reachable over a sheet with words by a link (?tpl=): everywhere else
  // the step opens from the empty page, after "Tạo sheet mới" has asked.
  if (ui.stage === "edit" && wordCount()) {
    const sure = await ask({
      title: t("shNewTitle"),
      text: t("shNewText", wordCount()),
      yes: t("shNewYes"),
      no: t("shKeep"),
    });
    if (!sure) return;
  }
  $("#tplbox").close();
  const made = templateSheet(stepId);
  made.title = name;
  made.marker = markerSet(made.marker, "name", name);
  rememberName(name);
  // The template's sample word shows what a row looks like (the card and the
  // scrap in the step say "example"); it is not one of the learner's words, so
  // the sheet starts with one empty row instead.
  made.rows = [{ id: made.noId ? "" : "w01", values: made.columns.map(() => "") }];
  // Built here, it is ready for words; "Tùy chỉnh nâng cao" opens step 1, the
  // full editor, on the same sheet.
  begin(made, { row: 0, col: 0, view: advanced ? "look" : "rows" });
  if (advanced) return;
  // A phone lands on the list, where pasting a list and adding one word are
  // offered side by side; opening the word form straight away covered the
  // first of them.
  if (WIDE.matches) {
    select(firstWordRow, 0);
    startEditing(firstWordRow, 0);
  }
}

// ---------------------------------------------------------------------------
// Painting the sheet
// ---------------------------------------------------------------------------

function paintAll() {
  $("#title").value = sheet.title;
  paintNameOffer();
  paintIdWarning();
  setView(ui.view);
  paintRows();
  paintColumns();
  paintOut();
  paintUndo();
  drawCard();
}

/** The grid on a wide screen, the list of words on a phone — or the text. */
function paintRows() {
  const n = wordCount();
  $("#rowcount").textContent = String(n);
  $("#rowcount-seg").textContent = String(n);
  if (ui.form === "text") paintText();
  else if (WIDE.matches) paintSheet();
  else paintList();
}

// ---------------------------------------------------------------------------
// The sheet as text
// ---------------------------------------------------------------------------
//
// The Văn bản view is the sheet written the way the paste dialog teaches
// (sheettext.js), and editing it edits the sheet: the text is read back a
// moment after the last key, as one step of undo, and written out again tidy
// when the box is left. `next=` and `shape=` are left out of it, as they are
// left out of the grid's marker cell, and put back on the way in. A sheet the
// text form cannot hold (a cell with a `|` or a line break) is shown read-only
// and says why, rather than being cut into the wrong cells.

const FORM_KEY = "sc-sheet-form";
const TEXT_NOTE = { pipe: "shTextPipe", newline: "shTextNewline", other: "shTextOther" };
let textTimer = 0;
let held = { ok: true, why: "" };

function storedForm() {
  try {
    return localStorage.getItem(FORM_KEY) === "text" ? "text" : "table";
  } catch {
    return "table";
  }
}

function setForm(form, { remember = true } = {}) {
  ui.form = form === "text" ? "text" : "table";
  $("#app").dataset.form = ui.form;
  for (const b of document.querySelectorAll(".sheetforms [data-form]")) {
    b.setAttribute("aria-pressed", String(b.dataset.form === ui.form));
  }
  if (remember) {
    try {
      localStorage.setItem(FORM_KEY, ui.form);
    } catch {
      // Remembered for this visit only.
    }
  }
  if (ui.form === "text") {
    stopEditing();
    ui.sel = null;
  }
  if (ui.stage !== "edit") return;
  paintRows();
  syncAddress();
}

/** The text form of the sheet, or why it has none. */
function textNow() {
  const grid = exportGrid(sheet, { mark: false });
  held = textHolds(grid);
  return sheetText(grid);
}

function paintText({ force = false } = {}) {
  const box = $("#sheettext");
  const text = textNow();
  if (force || document.activeElement !== box) box.value = text;
  box.readOnly = !held.ok;
  for (const id of ["#textnote", "#save-textnote"]) {
    $(id).hidden = held.ok;
    $(id).textContent = held.ok ? "" : t(TEXT_NOTE[held.why]);
  }
  $("#copytext").disabled = !held.ok;
  paintPaper();
}

/** The ruled layer under the text, its #config line and brackets tinted. */
function paintPaper() {
  const box = $("#sheettext");
  const paper = $("#sheetpaper");
  if (!box.offsetParent) return;
  box.style.height = "auto";
  box.style.height = `${box.scrollHeight + 3}px`;
  const lines = box.value.split("\n");
  const filled = lines.map((l, i) => (l.trim() ? i : -1)).filter((i) => i >= 0);
  const config = filled.find((i) => isMarkerCell(lines[i].trim())) ?? -1;
  const head = config >= 0 ? filled.find((i) => i > config) : filled[0];
  paper.innerHTML = lines
    .map((line, i) => {
      const body = escapeHtml(line) || "\u200b";
      if (i === config) return `<div class="ln cfg">${body.replace(/(#config)/i, '<span class="kw">$1</span>')}</div>`;
      if (i === head) return `<div class="ln head">${body.replace(/(\[[^\]\n]*\])/g, '<span class="br">$1</span>')}</div>`;
      return `<div class="ln">${body}</div>`;
    })
    .join("");
  paper.style.width = `${box.clientWidth + 3}px`;
  paper.style.height = `${box.offsetHeight}px`;
}

const sheetKey = (of) => JSON.stringify([of.title, of.marker, of.noId, of.columns, of.rows.map((r) => [r.id, r.values])]);

/** The text read back into the sheet, when it says something new. */
function applyText() {
  clearTimeout(textTimer);
  textTimer = 0;
  if (!held.ok || ui.stage !== "edit") return;
  const { grid } = sheetGrid($("#sheettext").value, { language: lang() });
  const idAt = grid[0].findIndex((h) => /^\s*\ufeff?id\s*$/i.test(h));
  const at = Math.max(0, idAt);
  if (sheet.shape) grid[1][at] = markerSet(grid[1][at], "shape", sheet.shape);
  if (sheet.next && idAt >= 0) grid[1][at] = markerSet(grid[1][at], "next", sheet.next);
  const made = fromGrid(grid, sheet.title);
  made.retired = sheet.retired;
  if (sheet.source) made.source = sheet.source;
  if (sheetKey(made) === sheetKey(sheet)) return;
  markRun("text");
  sheet = made;
  fit();
  paintAll();
  saveSoon();
}


function letter(index) {
  let out = "";
  for (let n = index + 1; n > 0; n = Math.floor((n - 1) / 26)) {
    out = String.fromCharCode(65 + ((n - 1) % 26)) + out;
  }
  return out;
}

/** Lines in a cell, for a textarea that starts as tall as its text. */
const lines = (text) => Math.min(6, String(text ?? "").split("\n").length);

/**
 * The spreadsheet: column A for the IDs, one column per field, and every word
 * on a row of its own. Rebuilt whole when its shape changes; typing never
 * rebuilds it, so a cell being written in keeps its caret.
 */
function paintSheet() {
  deriveIds();
  const cols = sheet.columns;
  const label = (key) => escapeHtml(t(key));
  const cell = (inner, r, c, cls = "") =>
    `<span class="cell ${cls}" data-r="${r}" data-c="${c}">${inner}</span>`;
  const dupes = duplicates();

  const head =
    `<span class="ref corner" data-all="1" title="${label("edSelectAll")}"></span>` +
    // A sheet keyed by its first column has no column A of IDs: the narrow
    // column left of it only holds the settings row's marker.
    `<span class="ref" data-c="-1"${sheet.noId ? ` title="#config"` : ""}>${sheet.noId ? "" : "A"}</span>` +
    cols.map((_, i) => `<span class="ref" data-c="${i}">${letter(sheet.noId ? i : i + 1)}</span>`).join("");

  const names =
    '<span class="ref" data-r="0">1</span>' +
    cell(sheet.noId ? "" : "ID", 0, -1, "fixed") +
    cols
      .map((c, i) =>
        cell(
          `<input data-edit="name" data-col="${i}" value="${escapeHtml(c.name)}"
             spellcheck="false" autocomplete="off" aria-label="${label("edName")}">`,
          0,
          i,
          "named",
        ),
      )
      .join("");

  // Row 2 is folded to one line naming the keys it uses, and opened by a click
  // on that line (or by step 1, where its cells are what the chips edit).
  const summary = `<button type="button" class="cfgsum" id="cfgsum" aria-expanded="${cfgOpen()}"
      aria-controls="sheet">${icon("chevron-right", "caret")}<span class="cfgsum-n">2</span><span class="cfgsum-t">${escapeHtml(cfgSummary())}</span></button>`;
  const settings =
    summary +
    '<span class="ref" data-r="1">2</span>' +
    cell(
      `<input data-edit="marker" value="${escapeHtml(sheet.marker)}"
         spellcheck="false" autocomplete="off" aria-label="${label("edDeckCell")}">`,
      1,
      -1,
      `marker${ui.col === -1 ? " on" : ""}`,
    ) +
    cols
      .map((c, i) =>
        cell(
          `<textarea data-edit="cell" data-col="${i}" rows="${lines(c.cell)}" spellcheck="false"
             autocomplete="off" aria-label="${label("edCell")}">${escapeHtml(c.cell)}</textarea>`,
          1,
          i,
          `cfg${ui.col === i ? " on" : ""}`,
        ),
      )
      .join("");

  const words = sheet.rows
    .map((row, k) => {
      const r = k + firstWordRow;
      return (
        `<span class="ref${k === ui.row ? " cur" : ""}" data-r="${r}">${r + 1}</span>` +
        (sheet.noId
          ? cell("", r, -1, `fixed nokey${!row.id && !blankRow(row) ? " dup" : ""}`)
          : cell(
              `<input data-edit="id" data-row="${k}" value="${escapeHtml(row.id)}"
             spellcheck="false" autocomplete="off" aria-label="${label("shIdLabel")}">`,
              r,
              -1,
              `idcell${dupes.has(row.id) || !row.id.trim() ? " dup" : sheet.retired.includes(row.id.trim()) ? " reused" : ""}`,
            )) +
        cols
          .map((_, i) =>
            cell(
              `<textarea data-edit="value" data-row="${k}" data-col="${i}" rows="${lines(row.values[i])}"
                 spellcheck="false" autocomplete="off"
                 aria-label="${escapeHtml(cols[i].name)}">${escapeHtml(row.values[i])}</textarea>`,
              r,
              i,
            ),
          )
          .join("")
      );
    })
    .join("");

  const grid = $("#sheet");
  grid.style.setProperty("--cols", String(cols.length));
  grid.classList.toggle("cfgopen", cfgOpen());
  grid.innerHTML = head + names + settings + words;
  if (!SIZES_ITSELF) for (const box of grid.querySelectorAll("textarea")) grow(box);
  // The grid is one stop for Tab: its cells are reached with the arrow keys and
  // opened with Enter, so Tab leaves rather than walking every cell.
  for (const box of grid.querySelectorAll("input, textarea")) box.tabIndex = -1;
  paintSelection();
}

/**
 * What is wrong with the IDs, if anything: written twice, left empty, or a
 * deleted word's ID typed in again. The first two stop the sheet leaving the
 * page — Anki keeps one note per ID, so the second word would be lost — and
 * the third is a warning, since the new word would inherit the old one's
 * review history.
 */
function idProblems() {
  if (sheet.noId) return keyProblems();
  const dupes = duplicates();
  const rowsOf = (pred) =>
    sheet.rows.flatMap((r, k) => (!blankRow(r) && pred(r) ? [k + firstWordRow + 1] : []));
  const dup = [...dupes].map((id) => ({ id, rows: rowsOf((r) => r.id === id) }));
  const blank = rowsOf((r) => !r.id.trim());
  const reused = sheet.rows
    .filter((r) => !blankRow(r) && sheet.retired.includes(r.id.trim()))
    .map((r) => r.id.trim());
  return { dup, blank, reused, blocking: dup.length > 0 || blank.length > 0 };
}

/**
 * The same question for a sheet keyed by its first column: a row with words in
 * it and nothing in that column cannot be keyed (blocks), and a word written
 * twice is kept twice — the second as "word (2)", as the .apkg will — which is
 * said, not refused.
 */
function keyProblems() {
  deriveIds();
  const line = (k) => k + firstWordRow + 1;
  const blank = sheet.rows.flatMap((r, k) => (!blankRow(r) && !r.id ? [line(k)] : []));
  const twins = new Map();
  sheet.rows.forEach((r, k) => {
    if (blankRow(r) || !r.id) return;
    const key = idText(r.values[0]).toLowerCase();
    twins.set(key, [...(twins.get(key) ?? []), k]);
  });
  const twice = [...twins.values()]
    .filter((ks) => ks.length > 1)
    .map((ks) => ({ word: idText(sheet.rows[ks[0]].values[0]), rows: ks.map(line), ids: ks.map((k) => sheet.rows[k].id) }));
  return { dup: [], blank, reused: [], twice, blocking: blank.length > 0 };
}

function paintIdWarning() {
  const box = $("#idwarn");
  if (!box) return;
  const { dup, blank, reused, twice = [] } = idProblems();
  const col = sheet.columns[0]?.name || "A";
  const lines = [
    ...(sheet.noId && blank.length ? [t("keyBlank", col, blank.join(", "))] : []),
    ...twice.map((d) => t("keyTwice", d.word, d.rows.join(", "), d.ids[1])),
    ...dup.map((d) => t("idDup", d.id, d.rows.join(", "))),
    ...(!sheet.noId && blank.length ? [t("idBlank", blank.join(", "))] : []),
    ...reused.map((id) => t("idReused", id)),
  ];
  box.hidden = !lines.length;
  box.className = `idwarn${dup.length || blank.length ? " bad" : ""}`;
  box.innerHTML = lines.map((line) => `<span>${escapeHtml(line)}</span>`).join("");
}

/** True — and said, at the first offending cell — when the IDs must be fixed first. */
function idsBlock() {
  const problems = idProblems();
  paintIdWarning();
  if (!problems.blocking) return false;
  toast(t("idFixFirst"), "bad");
  const k = sheet.rows.findIndex(
    (r) => !blankRow(r) && (!r.id.trim() || problems.dup.some((d) => d.id === r.id)),
  );
  if (k >= 0) {
    // The cell to fix: the ID, or the first column of a sheet keyed by it.
    const c = sheet.noId ? 0 : -1;
    if (WIDE.matches) {
      if (ui.view !== "rows") setView("rows");
      select(k + firstWordRow, c);
      reveal(k + firstWordRow, c);
    } else openForm(k);
  }
  return true;
}

/** IDs written more than once: Anki keeps one note per ID, so the rest are lost. */
function duplicates() {
  // Derived IDs are made unique ("word (2)"); nothing to refuse.
  if (sheet.noId) return new Set();
  const seen = new Set();
  const twice = new Set();
  for (const row of sheet.rows) {
    if (blankRow(row)) continue;
    if (seen.has(row.id)) twice.add(row.id);
    seen.add(row.id);
  }
  return twice;
}

/** The phone's list: one line per word, the first two fields of it. */
function paintList() {
  deriveIds();
  const dupes = duplicates();
  // No words yet: "Thêm từ" and "Dán danh sách từ" are offered side by side
  // (sheet.css .listpane.fresh) rather than one empty line between them.
  $("#listpane").classList.toggle("fresh", sheet.rows.every(blankRow));
  $("#wordlist").innerHTML = sheet.rows
    .map((row, k) => {
      const [first = "", second = ""] = row.values.filter((v) => String(v).trim());
      const empty = blankRow(row);
      return `<li><button type="button" class="worditem${k === ui.row ? " cur" : ""}${empty ? " empty" : ""}" data-row="${k}">
        <span class="wi-id${dupes.has(row.id) ? " dup" : ""}">${sheet.noId ? "" : escapeHtml(row.id)}</span>
        <span class="wi-main">${escapeHtml(first) || escapeHtml(t("shEmptyWord"))}</span>
        <span class="wi-sub">${escapeHtml(second)}</span>
        <span class="wi-go" aria-hidden="true">${icon("chevron-right")}</span>
      </button></li>`;
    })
    .join("");
}

// ---------------------------------------------------------------------------
// The grid's selection
// ---------------------------------------------------------------------------

function bounds() {
  const s = ui.sel;
  if (!s) return null;
  return {
    r1: Math.min(s.r, s.r2),
    r2: Math.max(s.r, s.r2),
    c1: Math.min(s.c, s.c2),
    c2: Math.max(s.c, s.c2),
  };
}

function select(r, c, extend = false) {
  const at = {
    r: Math.max(0, Math.min(lastRow(), r)),
    c: Math.max(-1, Math.min(sheet.columns.length - 1, c)),
  };
  if (extend && ui.sel) ui.sel = { ...ui.sel, r2: at.r, c2: at.c };
  else ui.sel = { r: at.r, c: at.c, r2: at.r, c2: at.c };
  stopEditing();
  paintSelection();
  follow(ui.sel.r, ui.sel.c);
}

/**
 * The chips act on whichever column the selection is anchored in, and the card
 * shows whichever word — one answer to "what am I changing", however it was
 * picked.
 */
function follow(r, c) {
  let moved = false;
  // Column A below row 2 holds IDs, not settings: the chips stay where they were.
  if (c === -1 && r !== 1) c = ui.col;
  if (c !== ui.col) {
    ui.col = c;
    ui.open = null;
    moved = true;
  }
  if (r >= firstWordRow && r - firstWordRow !== ui.row) {
    ui.row = r - firstWordRow;
    moved = true;
  }
  if (!moved) return;
  for (const el of document.querySelectorAll("#sheet .cell.on")) el.classList.remove("on");
  if (ui.col === -1) $('#sheet .cell[data-r="1"][data-c="-1"]')?.classList.add("on");
  else $(`#sheet .cell[data-r="1"][data-c="${ui.col}"]`)?.classList.add("on");
  for (const el of document.querySelectorAll("#sheet .ref.cur")) el.classList.remove("cur");
  $(`#sheet .ref[data-r="${ui.row + firstWordRow}"]`)?.classList.add("cur");
  paintColumns();
  drawCard();
}

function clearSelection() {
  if (!ui.sel) return;
  ui.sel = null;
  paintSelection();
}

const FILL_HANDLE = Object.assign(document.createElement("span"), { className: "fill" });

function paintSelection() {
  const box = bounds();
  const grid = $("#sheet");
  grid.classList.toggle("ranged", Boolean(box));
  for (const el of grid.querySelectorAll(".cell")) {
    const r = Number(el.dataset.r);
    const c = Number(el.dataset.c);
    const inside = box && r >= box.r1 && r <= box.r2 && c >= box.c1 && c <= box.c2;
    el.classList.toggle("sel", Boolean(inside));
    el.classList.toggle("anchor", Boolean(ui.sel?.r === r && ui.sel?.c === c));
    el.classList.toggle("edge-t", Boolean(inside && r === box.r1));
    el.classList.toggle("edge-b", Boolean(inside && r === box.r2));
    el.classList.toggle("edge-l", Boolean(inside && c === box.c1));
    el.classList.toggle("edge-r", Boolean(inside && c === box.c2));
  }
  for (const el of grid.querySelectorAll(".ref")) {
    const r = el.dataset.r === undefined ? null : Number(el.dataset.r);
    const c = el.dataset.c === undefined ? null : Number(el.dataset.c);
    const lit =
      box &&
      ((r !== null && r >= box.r1 && r <= box.r2) || (c !== null && c >= box.c1 && c <= box.c2));
    el.classList.toggle("sel", Boolean(lit));
  }
  if (box) grid.querySelector(`.cell[data-r="${box.r2}"][data-c="${box.c2}"]`)?.append(FILL_HANDLE);
  else FILL_HANDLE.remove();
}

function startEditing(r, c) {
  const cell = $(`#sheet .cell[data-r="${r}"][data-c="${c}"]`);
  const box = cell?.querySelector("[data-edit]");
  if (!box) return false;
  ui.editing = { r, c };
  for (const el of document.querySelectorAll("#sheet .cell.editing")) el.classList.remove("editing");
  cell.classList.add("editing");
  box.focus();
  box.select();
  return true;
}

/** The cell after (or before) one, row by row; null past either end. */
function nextCell(r, c, by) {
  const first = -1;
  const last = sheet.columns.length - 1;
  let row = r;
  let col = c + by;
  if (col > last) [row, col] = [r + 1, first];
  if (col < first) [row, col] = [r - 1, last];
  if (row === 1 && !cfgOpen()) row += by;
  if (row < 0 || row > lastRow()) return null;
  return { r: row, c: col };
}

function stopEditing() {
  if (!ui.editing) return;
  ui.editing = null;
  session = null;
  for (const el of document.querySelectorAll("#sheet .cell.editing")) el.classList.remove("editing");
  if (document.activeElement?.closest?.("#sheet")) document.activeElement.blur();
}

/** Keeps the selected cell in view as the keyboard walks the grid. */
function reveal(r, c) {
  $(`#sheet .cell[data-r="${r}"][data-c="${c}"]`)?.scrollIntoView({ block: "nearest", inline: "nearest" });
}

function selectionTsv() {
  const box = bounds();
  if (!box) return "";
  const rows = [];
  for (let r = box.r1; r <= box.r2; r++) {
    const row = [];
    for (let c = box.c1; c <= box.c2; c++) row.push(cellAt(r, c));
    rows.push(row);
  }
  return toTsv(rows);
}

// Where the browser sizes a textarea to its text by itself (field-sizing), it is
// left to; elsewhere each one is measured.
const SIZES_ITSELF = globalThis.CSS?.supports?.("field-sizing", "content") ?? false;

function grow(box) {
  if (SIZES_ITSELF && box.closest("#sheet")) return;
  box.style.height = "auto";
  box.style.height = `${box.scrollHeight}px`;
}

// ---------------------------------------------------------------------------
// Changing the shape of the sheet
// ---------------------------------------------------------------------------

function addColumn(at = sheet.columns.length, name = "") {
  sheet.columns.splice(at, 0, { name: name || `Column ${sheet.columns.length + 1}`, cell: "" });
  for (const row of sheet.rows) row.values.splice(at, 0, "");
}

function removeColumn(at) {
  if (sheet.columns.length < 2 || at < 0) return false;
  sheet.columns.splice(at, 1);
  for (const row of sheet.rows) row.values.splice(at, 1);
  fit();
  return true;
}

function addRow(at = sheet.rows.length, values = []) {
  const row = newRow(values);
  sheet.rows.splice(at, 0, row);
  fit();
  return at;
}

function removeRows(from, to) {
  raiseMark();
  for (const row of sheet.rows.slice(from, to + 1)) {
    if (!sheet.noId && row.id.trim() && !sheet.retired.includes(row.id.trim())) sheet.retired.push(row.id.trim());
  }
  sheet.rows.splice(from, to - from + 1);
  if (!sheet.rows.length) sheet.rows.push(newRow());
  fit();
}

function moveRow(k, by) {
  const to = k + by;
  if (to < 0 || to >= sheet.rows.length) return false;
  const [row] = sheet.rows.splice(k, 1);
  sheet.rows.splice(to, 0, row);
  return true;
}

/**
 * Writes a block into the grid from the selected cell, growing the sheet to
 * take it: rows past the last word become new words (with IDs of their own when
 * the block did not bring any), columns past the last become new columns.
 */
function pasteAt(block) {
  const box = bounds();
  if (!box) return null;
  let added = 0;
  block.forEach((cells, dr) => {
    const r = box.r1 + dr;
    while (r > lastRow()) {
      sheet.rows.push(newRow());
      added++;
    }
    cells.forEach((text, dc) => {
      const c = box.c1 + dc;
      if (c < -1) return;
      while (c >= sheet.columns.length) addColumn();
      if (r >= firstWordRow && c === -1 && !text.trim()) return;
      writeCell(r, c, r >= firstWordRow ? text : text.trim());
    });
  });
  fit();
  return { added, rows: block.length };
}

const looksLikeId = (cell) => /^[A-Za-z_.-]{0,8}\d{1,6}[A-Za-z_.-]{0,4}$/.test(cell.trim());

/**
 * A block pasted with nothing selected: a whole sheet replaces this one, and
 * rows of words are added under the ones already here.
 *
 * A whole sheet is recognised by its ID header or its #config marker. Rows of
 * words are taken to start with their IDs only when every first cell looks like
 * one and there is exactly one cell more than there are columns — otherwise the
 * first word of each row would be filed as an ID.
 */
function importBlock(block) {
  const rows = block.filter((row) => row.some((cell) => cell.trim()));
  if (!rows.length) return null;
  const whole = /^\s*id\s*$/i.test(rows[0][0] ?? "") || rows.slice(0, 3).some((r) => isMarkerCell(r[0]));
  if (whole) {
    const next = fromGrid(rows, sheet.title);
    // A pasted sheet that names no set stays this set.
    const had = markerGet(sheet.marker, "name");
    if (had !== null && markerGet(next.marker, "name") === null) {
      next.marker = markerSet(next.marker, "name", had);
      next.title = had;
    }
    next.retired = sheet.retired;
    sheet = next;
    fit();
    return { replaced: true, rows: sheet.rows.length };
  }
  // A blank word left at the end — the one a new sheet starts with — is
  // filled rather than left above what was pasted.
  while (sheet.rows.length && blankRow(sheet.rows[sheet.rows.length - 1])) sheet.rows.pop();
  const width = Math.max(...rows.map((r) => r.length));
  const withIds =
    !sheet.noId && width === sheet.columns.length + 1 && rows.every((r) => looksLikeId(r[0] ?? ""));
  for (const row of rows) {
    const values = withIds ? row.slice(1) : row;
    while (values.length > sheet.columns.length) addColumn();
    const word = newRow(values);
    if (withIds && !sheet.rows.some((r) => r.id === row[0].trim())) word.id = row[0].trim();
    sheet.rows.push(word);
  }
  fit();
  return { added: rows.length };
}

// ---------------------------------------------------------------------------
// The columns, and the settings row's chips
// ---------------------------------------------------------------------------

function parts(cell) {
  return String(cell ?? "")
    .split(";")
    .map((part) => part.trim())
    .filter(Boolean);
}

const nameOf = (part) => part.split("=")[0].trim().toLowerCase();

function seed(key) {
  const closed = keys.closed?.[key];
  if (closed?.length) return `${key}=${closed[0]}`;
  const listed = OPTIONS[key];
  if (!listed) return key;
  return listed.length ? `${key}=${listed[0]}` : `${key}=`;
}

const valued = (key) => Boolean(keys.closed?.[key] || OPTIONS[key]);
const hasPanel = (key) => valued(key) || Boolean(HELP[key]);

function toggle(cell, key, value) {
  const had = parts(cell).some((part) => nameOf(part) === key);
  const kept = parts(cell).filter((part) => nameOf(part) !== key);
  if (value !== undefined) return [...kept, value === "" ? key : `${key}=${value}`].join("; ");
  return (had ? kept : [...kept, seed(key)]).join("; ");
}

/** The active settings cell's text — for the #config cell, what follows the marker. */
function cellText() {
  return ui.col === -1
    ? sheet.marker.replace(/^\s*#config/i, "").trim()
    : (sheet.columns[ui.col]?.cell ?? "");
}

function setCell(text) {
  if (ui.col === -1) sheet.marker = `#config ${text}`.trim();
  else if (sheet.columns[ui.col]) sheet.columns[ui.col].cell = text;
  // The grid shows the same cell; written into rather than rebuilt, so a long
  // sheet does not repaint for one chip.
  const box = $(`#sheet .cell[data-r="1"][data-c="${ui.col}"] [data-edit]`);
  if (box) box.value = ui.col === -1 ? sheet.marker : text;
}

function valueOf(key) {
  const part = parts(cellText()).find((p) => nameOf(p) === key);
  if (part === undefined) return null;
  const at = part.indexOf("=");
  return at < 0 ? "" : part.slice(at + 1).trim();
}

/** The column strip, the chosen column's name and cell, and its chips. */
function paintColumns() {
  $("#colstrip").innerHTML =
    `<button type="button" class="colchip deck${ui.col === -1 ? " on" : ""}" data-col="-1"
       aria-pressed="${ui.col === -1}"><span class="mono">#config</span></button>` +
    sheet.columns
      .map(
        (c, i) =>
          `<button type="button" class="colchip${ui.col === i ? " on" : ""}" data-col="${i}"
             aria-pressed="${ui.col === i}">${escapeHtml(c.name || letter(i + 1))}</button>`,
      )
      .join("") +
    `<button type="button" class="colchip add" id="colplus" title="${escapeHtml(t("edAddColumn"))}"
       aria-label="${escapeHtml(t("edAddColumn"))}">${icon("plus")}</button>`;

  if (ui.col === -1) {
    $("#colhead").innerHTML = `<p class="colnote">${escapeHtml(t("shDeckCellNote"))}</p>
      <label class="colfield"><span>${escapeHtml(t("edDeckCell"))}</span>
        <input id="colcell" class="mono" value="${escapeHtml(sheet.marker)}" spellcheck="false" autocomplete="off"></label>`;
  } else {
    const col = sheet.columns[ui.col];
    $("#colhead").innerHTML = `<div class="colrow">
        <label class="colfield grow"><span>${escapeHtml(t("edName"))}</span>
          <input id="colname" value="${escapeHtml(col?.name ?? "")}" spellcheck="false" autocomplete="off"></label>
        <button type="button" class="iconbtn" id="coldrop" ${sheet.columns.length < 2 ? "disabled" : ""}
          title="${escapeHtml(t("edRemoveColumn"))}" aria-label="${escapeHtml(t("edRemoveColumn"))}">${icon("trash-2")}</button>
      </div>
      <label class="colfield"><span>${escapeHtml(t("edCell"))}</span>
        <input id="colcell" class="mono" value="${escapeHtml(col?.cell ?? "")}" spellcheck="false" autocomplete="off"
          placeholder="size=32; tts=en_US"></label>`;
  }
  paintKeys();
}

function paintKeys() {
  const on = new Set(parts(cellText()).map(nameOf));
  // The set's name is the page's to write (the title field), and `next`/`shape`
  // are its bookkeeping (nextId, shapeMark) — none of them a setting to toggle.
  const hidden = new Set(["name", ...(keys.internal ?? ["next", "shape"])]);
  const list = (ui.col === -1 ? keys.deck : keys.field).filter((k) => !hidden.has(k));
  if (ui.open && !list.includes(ui.open)) ui.open = null;
  // The keys most sheets need are shown; the rest wait under "Nâng cao", the
  // same split as the docs (sheet_config.BASIC_KEYS). `image` stands for the
  // media kinds in Basic; audio and video are advanced.
  const basic = new Set(keys.basic ?? []);
  const chip = (key) =>
    `<button type="button" class="col${on.has(key) ? " on" : ""}${ui.open === key ? " open" : ""}"` +
    ` data-key="${escapeHtml(key)}" aria-pressed="${on.has(key)}"` +
    `${hasPanel(key) ? ` aria-expanded="${ui.open === key}" aria-controls="opts"` : ""}` +
    `>${escapeHtml(key)}</button>`;
  const order = [...basic];
  const shown = list.filter((k) => basic.has(k)).sort((a, b) => order.indexOf(a) - order.indexOf(b));
  const more = list.filter((k) => !basic.has(k));
  // Open while one of its keys is written or being edited, or once opened.
  const open = ui.advOpen || more.some((k) => on.has(k) || ui.open === k);
  $("#keys").innerHTML =
    shown.map(chip).join("") +
    (more.length
      ? `<details class="advkeys" id="advkeys"${open ? " open" : ""}><summary>${escapeHtml(
          t("edAdvanced"),
        )}</summary><div class="advlist">${more.map(chip).join("")}</div></details>`
      : "");
  $("#advkeys")?.addEventListener("toggle", (e) => (ui.advOpen = e.target.open));
  $("#keyfor").textContent =
    ui.col === -1 ? t("edForDeck") : t("edForColumn", sheet.columns[ui.col]?.name || "");
  paintOptions();
}

function paintOptions() {
  const key = ui.open;
  const box = $("#opts");
  box.hidden = !key || !hasPanel(key);
  if (box.hidden) return;
  const current = valueOf(key);
  const listed = keys.closed?.[key] ?? OPTIONS[key] ?? [];
  const swatch = (v) =>
    key === "color" && !keys.themeColors?.includes(v)
      ? ` style="border-color:${escapeHtml(v)};color:${escapeHtml(v)}"`
      : "";
  const help = HELP[key];
  const sample = ui.col === -1 ? null : help?.sample;
  box.innerHTML = `${help ? `<p class="opthelp">${escapeHtml(t(help.text))}</p>` : ""}${
    sample
      ? `<p class="optsample"><button type="button" class="col" id="optsample">${escapeHtml(
          t("edSample"),
        )}</button><code>${escapeHtml(sample)}</code></p>`
      : ""
  }<p class="optbar"><b class="mono">${escapeHtml(key)}</b>
      ${listed
        .map(
          (v) =>
            `<button type="button" class="col${current === v ? " on" : ""}" data-opt="${escapeHtml(v)}"` +
            `${swatch(v)}>${escapeHtml(v || t("edOther"))}</button>`,
        )
        .join("")}
      ${
        keys.closed?.[key] || !valued(key)
          ? ""
          : `<input id="optfree" value="${escapeHtml(current ?? "")}" spellcheck="false" autocomplete="off"
               placeholder="${escapeHtml(t("edOther"))}" aria-label="${escapeHtml(t("edOther"))}">`
      }
      <button type="button" class="drop" id="optdrop" title="${escapeHtml(t("edRemoveKey"))}"
        aria-label="${escapeHtml(t("edRemoveKey"))}">${icon("x")}</button></p>`;
}

// ---------------------------------------------------------------------------
// The card
// ---------------------------------------------------------------------------

let drawQueued = false;

/** Redraws the card on the next frame — once, however many changes came in. */
function drawSoon() {
  if (drawQueued) return;
  drawQueued = true;
  requestAnimationFrame(() => {
    drawQueued = false;
    drawCard();
  });
}

/** The box the card goes in: the form's while a word is open, the page's otherwise. */
const cardTarget = () => ($("#rowform").open ? $("#formcard") : $("#cardbox"));

function drawCard() {
  if (ui.stage !== "edit") return;
  const target = cardTarget();
  const other = target.id === "formcard" ? $("#cardbox") : $("#formcard");
  other.innerHTML = "";
  if (!run) {
    target.innerHTML = `<div class="cardwait"><span class="sk-line w60"></span><span class="sk-line w30"></span>
      <span class="sk-rule"></span><span class="sk-line w45"></span></div>`;
    return;
  }

  const row = sheet.rows[ui.row] ?? { id: "", values: [] };
  let out;
  try {
    out = run(
      JSON.stringify({
        marker: sheet.marker,
        columns: sheet.columns,
        values: row.values,
        rows: sheet.rows.filter((r) => !blankRow(r)).map((r) => r.values),
      }),
    );
  } catch (err) {
    status(String(err?.message || err).trim().split("\n").pop(), "bad");
    return;
  }

  const warnings = (out.warningCodes || (out.warnings || []).map((text) => ({ text }))).map((w) =>
    warningText(w, lang()),
  );
  $("#warn").hidden = !warnings.length;
  $("#warntitle").textContent = t("edRefused", warnings.length);
  $("#warnlist").innerHTML = warnings.map((w) => `<li>${escapeHtml(w)}</li>`).join("");
  status(
    !out.isConfig ? t("edNoMarker") : warnings.length ? t("edRefused", warnings.length) : t("edOk"),
    !out.isConfig || warnings.length ? "bad" : "ok",
  );

  const levels = out.deck || [];
  $("#cardmeta").innerHTML =
    `<span class="rowtag">${escapeHtml(t("shWordN", ui.row + 1, sheet.rows.length))}</span>` +
    `<span class="crumbs">${[t("edDeckRoot"), ...levels]
      .map((part, i) => `${i ? `<span class="sep">${icon("chevron-right")}</span>` : ""}<span>${escapeHtml(part)}</span>`)
      .join("")}</span>`;

  paintDeckLine(out);

  const tabs = `<div class="tabs cardtabs"><span class="tabset">${CARD_TABS.map(
    (name) =>
      `<button type="button" data-tab="${name}" class="${ui.tab === name ? "on" : ""}" aria-pressed="${ui.tab === name}">` +
      `${escapeHtml(t("tab" + name[0].toUpperCase() + name.slice(1)))}</button>`,
  ).join("")}</span></div>`;

  const index = Math.min(ui.template, out.templates.length - 1);
  const template = out.templates[index];
  const picker =
    out.templates.length > 1
      ? `<select id="tpl" class="tplpick" aria-label="${escapeHtml(t("edTemplate"))}">${out.templates
          .map((tpl, i) => `<option value="${i}" ${i === index ? "selected" : ""}>${escapeHtml(tpl.name)}</option>`)
          .join("")}</select>`
      : "";

  if (ui.tab === "template") {
    target.innerHTML = `${tabs}${picker}
      <h4 class="src-head">${escapeHtml(t("frontTemplate"))}</h4>
      <pre class="source">${escapeHtml(template.qfmt)}</pre>
      <h4 class="src-head">${escapeHtml(t("backTemplate"))}</h4>
      <pre class="source">${escapeHtml(template.afmt)}</pre>`;
    return;
  }

  const values = { ID: row.id };
  out.names.forEach((name, i) => (values[name] = row.values[i] ?? ""));
  const { front, back } = renderCard(template, values, { ordinal: 1 });
  const doc = cardDoc({ front, back, tab: ui.tab, dark: dark() });
  target.innerHTML = `${tabs}${picker}<div class="shcard">${cardFrame(doc, t("cardFrameTitle"))}</div>
    <p class="muted small sides">${escapeHtml(t("edSides", out.front.length, out.back.length))}</p>`;
}

/**
 * Where the words are filed, for the whole sheet: a subdeck column reaches the
 * deck and never the card, so with only the card on screen it looked inert.
 */
function paintDeckLine(out) {
  const rows = (out.decks || []).map((deck) => ({
    kind: "synced",
    deck: [t("edDeckRoot"), ...(deck ? deck.split("::") : [])].join("::"),
  }));
  const tags = out.tags || [];
  $("#deckline").innerHTML =
    `<h4 class="keyhead">${escapeHtml(t("panelDeck"))}</h4>` +
    (rows.length ? `<ul class="tree">${treeHtml(deckTree(rows))}</ul>` : "") +
    `<p class="tagline"><b>${escapeHtml(t("edTags"))}</b>${tags
      .map((tag) => `<code>${escapeHtml(tag)}</code>`)
      .join("")}</p>`;
}

// ---------------------------------------------------------------------------
// The bar at the bottom: the three ways out
// ---------------------------------------------------------------------------

function paintOut() {
  const n = wordCount();
  $("#out-count").textContent = t("shWords", n);
  $("#out-sub").textContent = t("shColumnsN", sheet.columns.length);
  paintFiled();
}

/** Straight on to Sheet to Anki, with the sheet as a file it opens like any other. */
async function toDeck() {
  if (!wordCount()) return toast(t("shNeedWord"), "bad");
  if (idsBlock()) return;
  if (!isFiled()) {
    const save = await ask({
      title: t(SAVE_LINK ? "shUnlinkedTitle" : "shUnfiledTitle"),
      text: t(SAVE_LINK ? "shUnlinkedText" : "shUnfiledText"),
      yes: t(SAVE_LINK ? "shSaveLink" : "shSaveCsv"),
      no: t("shUnfiledGo"),
    });
    // The link is saved by sending or copying it, which happens in the share
    // box; Tạo flashcard is pressed again from there.
    if (save && SAVE_LINK) return openShare("save");
    if (save) saveCsv();
  }
  saveNow();
  leaving = true;
  const file = new File([toTsv(exportGrid())], `${fileBase()}.tsv`, {
    type: "text/tab-separated-values",
  });
  try {
    await stashFile(file, "sheet");
  } catch {
    return toast(t("shHandoffFailed"), "bad");
  }
  location.href = site("create/#file");
}

// Leaving with words no file holds: the browser's own question, the one place
// a page can ask on the way out. Not when the page itself is going to Create
// deck — that was asked already.
let leaving = false;
addEventListener("beforeunload", (e) => {
  if (leaving || ui.stage !== "edit" || !wordCount() || isFiled()) return;
  e.preventDefault();
  e.returnValue = "";
});

function download(blob, name) {
  const url = URL.createObjectURL(blob);
  const link = Object.assign(document.createElement("a"), { href: url, download: name });
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Tải về / Lưu: every way the sheet leaves, the device's save first. */
function openSaveMenu() {
  if (!wordCount()) return toast(t("shNeedWord"), "bad");
  if (idsBlock()) return;
  textNow();
  for (const id of ["#save-txt", "#copy-text"]) $(id).disabled = !held.ok;
  $("#save-textnote").hidden = held.ok;
  $("#save-textnote").textContent = held.ok ? "" : t(TEXT_NOTE[held.why]);
  $("#savebox").showModal();
}

/** Whether the sheet may leave: it has words, and every one an ID. */
function mayLeave() {
  if (!wordCount()) {
    toast(t("shNeedWord"), "bad");
    return false;
  }
  if ($("#savebox").open) $("#savebox").close();
  return !idsBlock();
}

/** A file of the sheet, which marks it kept. */
function saveAs(ext, text, type) {
  if (!mayLeave()) return;
  download(new Blob([text], { type }), `${fileBase()}.${ext}`);
  markFiled("file");
  toast(t("shDownloaded", `${fileBase()}.${ext}`), "ok");
  if (ext === "csv") showNote("android");
}

const saveCsv = () => saveAs("csv", asCsv(exportGrid()), "text/csv");
const saveTsv = () => saveAs("tsv", toTsv(exportGrid()) + "\n", "text/tab-separated-values");
function saveTxt() {
  textNow();
  if (!held.ok) return toast(t(TEXT_NOTE[held.why]), "bad");
  saveAs("txt", sheetText(exportGrid()), "text/plain;charset=utf-8");
}

// A copy is not a save: the clipboard keeps it only until the next copy, so the
// sheet stays "not saved" until it is in a file or a link.
async function copyOut(text, done) {
  if (!mayLeave()) return;
  try {
    await navigator.clipboard.writeText(text);
    toast(t(done), "ok");
  } catch {
    toast(t("edCopyFailed"), "bad");
  }
}
function copyText() {
  textNow();
  if (!held.ok) return toast(t(TEXT_NOTE[held.why]), "bad");
  return copyOut(sheetText(exportGrid()), "shCopiedText");
}
const copyTable = () => copyOut(toTsv(exportGrid()), "shCopiedTable");

function saveXlsx() {
  if (!mayLeave()) return;
  whenReady(() => {
    try {
      const bytes = new Uint8Array(toXlsx(JSON.stringify({ name: sheet.title || fileBase(), rows: exportGrid() })));
      download(
        new Blob([bytes], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }),
        `${fileBase()}.xlsx`,
      );
      markFiled("file");
      toast(t("shDownloaded", `${fileBase()}.xlsx`), "ok");
    } catch (err) {
      toast(String(err?.message || err).split("\n").pop(), "bad");
    }
  }, t("shPreparingXlsx"));
}

/** The link, for whichever page it is to open in. */
async function shareUrl() {
  const hash = await encodeShare(sheet.title, toTsv(exportGrid()));
  return shareAddress(hash, { deck: $("#share-deck").checked });
}

function sizeText(bytes) {
  return bytes < 1024 ? `${bytes} B` : `${(bytes / 1024).toFixed(1)} KB`;
}

async function paintShare() {
  const url = await shareUrl();
  $("#share-url").value = url;
  $("#share-size").textContent = t("shLinkSize", sizeText(url.length), wordCount());
  const long = url.length > LONG_LINK;
  $("#share-long").hidden = !long;
  $("#share-long").textContent = long ? t("shLinkLong") : "";
}

/**
 * The link box, as a way to share ("share") or as the phone's save ("save"):
 * the same link either way, said as what it is for. Saving always opens in
 * Create sheet, where the words can be added to.
 */
async function openShare(mode = SAVE_LINK ? "save" : "share") {
  if (!wordCount()) return toast(t("shNeedWord"), "bad");
  if (idsBlock()) return;
  const save = mode === "save";
  for (const [el, key] of [
    [$("#share-title"), save ? "shSaveLink" : "shShare"],
    [$("#share-lead"), save ? "shSaveLinkLead" : "shShareLead"],
  ]) {
    el.dataset.i18n = key;
    el.innerHTML = t(key);
  }
  $("#share-choice").hidden = save;
  if (save) $("#share-deck").checked = false;
  const native = Boolean(navigator.share);
  $("#share-native").hidden = !native;
  // Where the phone can send it, sending it is the save: first and filled.
  const sendFirst = save && native;
  $("#share-native").className = sendFirst ? "btn big" : "toolbtn";
  $("#share-copy").className = sendFirst ? "toolbtn" : "btn big";
  $("#share-native").style.order = sendFirst ? "-1" : "";
  await paintShare();
  $("#sharebox").showModal();
  (sendFirst ? $("#share-native") : $("#share-copy")).focus();
}

async function copyShare() {
  const url = $("#share-url").value;
  try {
    await navigator.clipboard.writeText(url);
  } catch {
    $("#share-url").select();
    if (!document.execCommand?.("copy")) return toast(t("edCopyFailed"), "bad");
  }
  markFiled("link");
  $("#share-copy").querySelector("[data-i18n]").textContent = t("shCopied");
  setTimeout(() => {
    const label = $("#share-copy [data-i18n]");
    if (label) label.textContent = t("shCopyLink");
  }, 2000);
}

// ---------------------------------------------------------------------------
// The phone's form: one word at a time
// ---------------------------------------------------------------------------

function openForm(k, { field = null } = {}) {
  ui.row = Math.max(0, Math.min(k, sheet.rows.length - 1));
  const row = sheet.rows[ui.row];
  const box = $("#rowform");
  $("#rf-title").textContent = t("shWordN", ui.row + 1, sheet.rows.length);
  $("#rf-id").value = row.id;
  // A sheet keyed by its first column has no ID to type.
  $("#rf-id").closest(".rf-id").hidden = Boolean(sheet.noId);
  const last = sheet.columns.length - 1;
  $("#rf-fields").innerHTML = sheet.columns
    .map(
      (col, i) => `<label class="rf-field"><span class="rf-label">${escapeHtml(col.name || letter(i + 1))}</span>
        <textarea data-fi="${i}" rows="1" enterkeyhint="${i === last ? "done" : "next"}" spellcheck="false"
          autocapitalize="off">${escapeHtml(row.values[i] ?? "")}</textarea></label>`,
    )
    .join("");
  $("#rf-prev").disabled = ui.row === 0;
  if (!box.open) box.showModal();
  for (const area of box.querySelectorAll("textarea")) grow(area);
  drawCard();
  if (field !== null) box.querySelector(`[data-fi="${field}"]`)?.focus();
  else box.querySelector(".rf-body").scrollTop = 0;
}

/** Closes the form; a word added and never written in goes again. */
function closeForm() {
  const box = $("#rowform");
  if (ui.fresh !== null) {
    const row = sheet.rows[ui.fresh];
    if (row && blankRow(row) && sheet.rows.length > 1) {
      sheet.rows.splice(ui.fresh, 1);
      fit();
    }
    ui.fresh = null;
  }
  if (box.open) box.close();
  paintRows();
  paintOut();
  drawCard();
  saveSoon();
}

/** A new word at the end, opened at its first field — "add word" as one tap. */
function addWord() {
  const last = sheet.rows[sheet.rows.length - 1];
  // A blank word already waiting at the end is the one to fill.
  if (last && blankRow(last)) {
    openForm(sheet.rows.length - 1, { field: 0 });
    return;
  }
  mark();
  const k = addRow();
  ui.fresh = k;
  paintRows();
  paintOut();
  openForm(k, { field: 0 });
}

/** Enter on the last field: on to the next word, making one if this was the last. */
function nextWord() {
  if (ui.row < sheet.rows.length - 1) return openForm(ui.row + 1, { field: 0 });
  if (blankRow(sheet.rows[ui.row])) return;
  ui.fresh = null;
  addWord();
}

// ---------------------------------------------------------------------------
// Opening a file
// ---------------------------------------------------------------------------

const FILE_TYPES = /\.(xlsx|xlsm|csv|tsv|txt|apkg|colpkg)$/i;

/** Opens a picked file to edit — or, `asTemplate`, keeps it as a template. */
async function openFile(file, asTemplate = false) {
  if (!FILE_TYPES.test(file.name)) return toast(t("badFileType", file.name), "bad");
  const grid = /\.txt$/i.test(file.name) ? await textFile(file) : null;
  if (grid) return openGrid(grid, fileStem(file.name), file.name, asTemplate);
  whenReady(() => readPicked(file, 0, true, asTemplate), t("reading"));
}

/** A .txt written in the text form (its first line `#config`), as cells; else null. */
async function textFile(file) {
  let text;
  try {
    text = new TextDecoder("utf-8", { fatal: true }).decode(await file.arrayBuffer());
  } catch {
    return null;
  }
  const first = text.replace(/^\ufeff/, "").split(/\r?\n/).find((l) => l.trim()) || "";
  return isMarkerCell(first.trim()) ? sheetGrid(text, { language: lang() }).grid : null;
}

async function readPicked(file, index, choose = true, asTemplate = false) {
  let out;
  try {
    out = readFile(new Uint8Array(await file.arrayBuffer()), file.name, index);
  } catch (err) {
    const last = String(err?.message || err).trim().split("\n").pop();
    const known = /not UTF-8 text/.test(last)
      ? "badEncoding"
      : /NewFormatError|exported by a newer Anki/.test(last)
        ? "apkgNewFormat"
        : /not an Anki package/.test(last)
          ? "apkgBroken"
          : /has no notes in it/.test(last)
            ? "apkgEmpty"
            : "";
    return toast(known ? t(known) : last, "bad");
  }
  toast("");
  // Without what a phone adds to a second download, so a legacy sheet keeps
  // the file identity Sheet to Anki has always keyed it by.
  const title = fileStem(file.name);
  if (choose && out.tabs.length > 1) {
    // A workbook of several sheets: ask which, the way Sheet to Anki's picker does.
    $("#tablist").innerHTML = out.tabs
      .map(
        (name, i) =>
          `<button type="button" class="tabchoice" data-tabi="${i}">${icon("sheet")}` +
          `<span>${escapeHtml(name)}</span></button>`,
      )
      .join("");
    $("#tablist").onclick = (e) => {
      const b = e.target.closest("[data-tabi]");
      if (!b) return;
      $("#tabbox").close();
      readPicked(file, Number(b.dataset.tabi), false, asTemplate);
    };
    $("#tabbox").showModal();
    return;
  }
  const name = out.tabs.length > 1 ? out.tab : title;
  const lost = (out.package?.media?.images || 0) + (out.package?.media?.audio || 0);
  const said = out.encoding ? t("readAsEncoding", out.encoding) : lost ? t("apkgMedia", lost) : "";
  openGrid(out.rows, name, file.name, asTemplate, said);
}

/** Cells read from a file, opened to edit (or kept as a template). */
function openGrid(rows, name, source, asTemplate = false, said = "") {
  if (asTemplate) return saveTemplate(exportGrid(fromGrid(rows, name), { mark: false }), name);
  const opened = fromGrid(rows, name);
  // What the file was called, for the line that says it is keyed by its name.
  opened.source = source;
  if (markerGet(opened.marker, "name")) rememberName(opened.title);
  begin(opened, { keepHistory: true, view: "rows", filed: toTsv(exportGrid(opened)) });
  if (said) toast(said, "bad");
  else if (headless.has(opened)) toast(t("hdSynth"), "bad");
  else toast(t("shOpened", name, wordCount()), "ok");
}

// ---------------------------------------------------------------------------
// Python, which the card, the .xlsx and opening a file wait for
// ---------------------------------------------------------------------------

const queue = [];
let booted = false;

/** Runs `job` once Python is up, saying so if that is not yet. */
function whenReady(job, waiting = "") {
  if (booted) return job();
  queue.push(job);
  if (waiting) toast(waiting, "", true);
}

// ---------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------

document.addEventListener("click", (e) => {
  const item = e.target.closest("[data-menu]");
  if (item) return runMenu(item.dataset.menu);
  closeMenu();

  if (e.target.closest("#theme")) return setTheme(!dark());
  const picker = e.target.closest("[data-lang]");
  if (picker) {
    setLang(picker.dataset.lang);
    paintChrome();
    if (ui.stage === "empty") paintTemplates();
    else paintAll();
    if ($("#tplbox").open) paintStep();
    if (!run) bootStatus();
    return;
  }

  const tpl = e.target.closest("[data-template]");
  if (tpl) return pickTemplate(tpl.dataset.template);
  const pick = e.target.closest("[data-theme-pick]");
  if (pick) {
    stepTheme = pick.dataset.themePick;
    return paintStep();
  }
  if (e.target.closest("#tpl-go")) return createFromStep();
  if (e.target.closest("#tpl-advanced")) return createFromStep({ advanced: true });
  if (e.target.closest("#tpl-csv")) return stepCsv();
  if (e.target.closest("#tpl-upload")) return $("#tplfile").click();
  const drop = e.target.closest("[data-drop]");
  if (drop) return forgetTemplate(drop.dataset.drop);

  if (e.target.closest("[data-close]")) return e.target.closest("dialog").close();

  const view = e.target.closest(".viewseg [data-view]");
  if (view) {
    setView(view.dataset.view);
    return drawCard();
  }
  if (e.target.closest("#tplfold")) {
    setView(ui.view === "look" ? "rows" : "look");
    return drawCard();
  }

  const tab = e.target.closest("[data-tab]");
  if (tab) {
    ui.tab = tab.dataset.tab;
    return drawCard();
  }

  const word = e.target.closest("[data-row].worditem");
  if (word) return openForm(Number(word.dataset.row));

  const colchip = e.target.closest(".colchip[data-col]");
  if (colchip) {
    ui.col = Number(colchip.dataset.col);
    ui.open = null;
    paintColumns();
    if (WIDE.matches) paintSheet();
    return;
  }
  if (e.target.closest("#colplus")) {
    mark();
    addColumn();
    ui.col = sheet.columns.length - 1;
    afterShape();
    $("#colname")?.focus();
    $("#colname")?.select();
    return;
  }
  if (e.target.closest("#coldrop")) {
    mark();
    if (removeColumn(ui.col)) afterShape();
    return;
  }

  const key = e.target.closest("[data-key]");
  if (key) {
    mark();
    const name = key.dataset.key;
    if (!valued(name)) setCell(toggle(cellText(), name));
    ui.open = ui.open === name && valued(name) ? null : name;
    paintColumns();
    drawCard();
    return saveSoon();
  }
  const opt = e.target.closest("[data-opt]");
  if (opt) {
    mark();
    setCell(toggle(cellText(), ui.open, opt.dataset.opt));
    paintColumns();
    drawCard();
    return saveSoon();
  }
  if (e.target.closest("#optsample")) {
    mark();
    if (!sheet.rows.length) addRow();
    sheet.rows[ui.row].values[ui.col] = HELP[ui.open].sample;
    paintRows();
    drawCard();
    return saveSoon();
  }
  if (e.target.closest("#optdrop")) {
    mark();
    setCell(parts(cellText()).filter((part) => nameOf(part) !== ui.open).join("; "));
    ui.open = null;
    paintColumns();
    drawCard();
    return saveSoon();
  }
});

/** After a column or row is added, removed or moved: everything that shows it. */
function afterShape() {
  fit();
  paintAll();
  saveSoon();
}

// The title is the set's name, which is its identity in Anki: renaming it is
// making a new deck there. So it is typed freely and asked about once, when
// the field is left — never changed one keystroke at a time.
$("#title").addEventListener("keydown", (e) => {
  // Left on the key's way up, not down: the rename question focuses a button,
  // and the rest of the same Enter would otherwise press it.
  if (e.key === "Enter" && !e.isComposing) e.preventDefault();
  if (e.key === "Escape") {
    e.target.value = sheet.title;
    e.target.blur();
  }
});
$("#title").addEventListener("keyup", (e) => {
  if (e.key === "Enter" && !e.isComposing) e.target.blur();
});
$("#title").addEventListener("change", (e) => rename(e.target.value));

async function rename(typed) {
  const name = String(typed ?? "").replace(/\s+/g, " ").trim().replace(/;/g, ",");
  const had = markerGet(sheet.marker, "name");
  const back = () => ($("#title").value = sheet.title);
  if (!name || (name === sheet.title && had !== null)) return back();
  const same = had !== null && deckKeyOf(had) === deckKeyOf(name);
  if (!same) {
    const sure = await ask({
      title: t(had === null ? "nameAddTitle" : "renameTitle"),
      text:
        t(had === null ? "nameAddText" : "renameText", sheet.title || "—", name) +
        (nameUsed(name) ? " " + t("setNameUsed", name) : ""),
      yes: t(had === null ? "nameAddYes" : "renameYes"),
      no: t("renameNo"),
    });
    if (!sure) return back();
  }
  mark();
  sheet.title = name;
  sheet.marker = markerSet(sheet.marker, "name", name);
  rememberName(name);
  paintAll();
  saveSoon();
}

const deckKeyOf = (name) => String(name).normalize("NFC").replace(/\s+/g, " ").trim().toLowerCase();

/** Keeps the title on the marker's `name=` when the marker is typed into. */
function followMarker() {
  const named = markerGet(sheet.marker, "name");
  if (named !== null && named !== sheet.title) {
    sheet.title = named;
    $("#title").value = named;
  }
  paintNameOffer();
}

/**
 * A sheet that names no set — opened from a file written before sheets did.
 * Sheet to Anki then keys it by its file name, so leaving it as it is keeps
 * updating the deck already in Anki. Writing a name in is offered, never done
 * silently: it makes a new deck there, once.
 */
function paintNameOffer() {
  const box = $("#nameoffer");
  const legacy = ui.stage === "edit" && markerGet(sheet.marker, "name") === null;
  box.hidden = !legacy;
  if (legacy) $("#nameoffer-text").textContent = t("nameOffer", sheet.source || `${fileBase()}.csv`);
}

$("#colhead").addEventListener("input", (e) => {
  if (e.target.id === "colname") {
    markRun(`name:${ui.col}`);
    sheet.columns[ui.col].name = e.target.value;
    const box = $(`#sheet .cell[data-r="0"][data-c="${ui.col}"] input`);
    if (box) box.value = e.target.value;
    const chip = $(`.colchip[data-col="${ui.col}"]`);
    if (chip) chip.textContent = e.target.value || letter(ui.col + 1);
    $("#keyfor").textContent = t("edForColumn", e.target.value);
  } else if (e.target.id === "colcell") {
    markRun(`cell:${ui.col}`);
    if (ui.col === -1) {
      sheet.marker = e.target.value;
      followMarker();
    } else sheet.columns[ui.col].cell = e.target.value;
    const box = $(`#sheet .cell[data-r="1"][data-c="${ui.col}"] [data-edit]`);
    if (box) box.value = e.target.value;
    paintKeys();
  } else return;
  drawSoon();
  saveSoon();
});

$("#opts").addEventListener("input", (e) => {
  if (e.target.id !== "optfree") return;
  markRun(`opt:${ui.open}`);
  setCell(toggle(cellText(), ui.open, e.target.value.trim()));
  const colcell = $("#colcell");
  if (colcell) colcell.value = ui.col === -1 ? sheet.marker : cellText();
  drawSoon();
  saveSoon();
});

// The grid's inputs, reached by delegation since the grid is rebuilt whole.
$("#sheet").addEventListener("input", (e) => {
  const el = e.target.closest("[data-edit]");
  if (!el) return;
  const kind = el.dataset.edit;
  markRun(`cell:${kind}:${el.dataset.row ?? ""}:${el.dataset.col ?? ""}`);
  if (kind === "marker") sheet.marker = el.value;
  else if (kind === "name") sheet.columns[Number(el.dataset.col)].name = el.value;
  else if (kind === "cell") sheet.columns[Number(el.dataset.col)].cell = el.value;
  else if (kind === "id") {
    sheet.rows[Number(el.dataset.row)].id = el.value;
    idTyped(el.value);
  }
  else sheet.rows[Number(el.dataset.row)].values[Number(el.dataset.col)] = el.value;
  if (sheet.noId && kind === "value" && el.dataset.col === "0") paintIdWarning();
  if (el.tagName === "TEXTAREA") grow(el);
  if (kind === "marker") followMarker();
  if (kind === "name" || kind === "cell" || kind === "marker") paintColumns();
  paintOut();
  drawSoon();
  saveSoon();
});

// ---- the phone's form ------------------------------------------------------

$("#rf-fields").addEventListener("input", (e) => {
  const area = e.target.closest("[data-fi]");
  if (!area) return;
  markRun(`form:${ui.row}:${area.dataset.fi}`);
  sheet.rows[ui.row].values[Number(area.dataset.fi)] = area.value;
  if (sheet.noId && area.dataset.fi === "0") paintIdWarning();
  grow(area);
  drawSoon();
  saveSoon();
});

$("#rf-fields").addEventListener("keydown", (e) => {
  const area = e.target.closest("[data-fi]");
  if (!area || e.key !== "Enter" || e.shiftKey || e.altKey || e.isComposing) return;
  e.preventDefault();
  const next = $(`#rf-fields [data-fi="${Number(area.dataset.fi) + 1}"]`);
  if (next) next.focus();
  else nextWord();
});

$("#rf-id").addEventListener("input", (e) => {
  markRun(`formid:${ui.row}`);
  sheet.rows[ui.row].id = e.target.value;
  idTyped(e.target.value);
  saveSoon();
});
$("#rf-id").addEventListener("keydown", (e) => {
  if (e.key !== "Enter") return;
  e.preventDefault();
  $('#rf-fields [data-fi="0"]')?.focus();
});

$("#rf-close").addEventListener("click", closeForm);
$("#rf-done").addEventListener("click", closeForm);
$("#rowform").addEventListener("cancel", (e) => {
  e.preventDefault();
  closeForm();
});
$("#rf-prev").addEventListener("click", () => openForm(ui.row - 1));
$("#rf-next").addEventListener("click", () => {
  if (ui.row < sheet.rows.length - 1) openForm(ui.row + 1);
  else addWord();
});
$("#rf-del").addEventListener("click", () => {
  mark();
  const gone = sheet.rows[ui.row].id;
  ui.fresh = null;
  removeRows(ui.row, ui.row);
  $("#rowform").close();
  paintRows();
  paintOut();
  drawCard();
  saveSoon();
  toast(t("shDeleted", gone), "ok");
});

$("#addword").addEventListener("click", addWord);

// ---- a pasted word list, and suggestions (wordpaste.js, suggestpanel.js) ---
//
// Both dialogs are modules of their own; this is the whole of what they may do
// to the sheet, each change one undo step and saved like any other.

function showWord(k) {
  ui.row = Math.max(0, Math.min(k, sheet.rows.length - 1));
  if ($("#rowform").open) return openForm(ui.row);
  if (WIDE.matches) {
    select(ui.row + firstWordRow, 0);
    reveal(ui.row + firstWordRow, 0);
  } else {
    paintList();
    $(`#wordlist [data-row="${ui.row}"]`)?.scrollIntoView({ block: "center" });
    drawCard();
  }
}

function afterWordTool() {
  afterShape();
  if ($("#rowform").open) openForm(ui.row);
}

const wordTools = {
  sheet: () => sheet,
  toast,
  canSuggest: () => suggestPanel.canSuggest(),
  suggest: (rows) => suggestPanel.open(rows),
  addWords(rows) {
    mark();
    // The blank word a new sheet starts with is filled, not left above the list.
    while (sheet.rows.length && blankRow(sheet.rows[sheet.rows.length - 1])) sheet.rows.pop();
    const first = sheet.rows.length;
    for (const values of rows) sheet.rows.push(newRow(values));
    ui.fresh = null;
    afterShape();
    showWord(first);
    return first;
  },
  setCell(k, c, value) {
    mark();
    writeCell(k + firstWordRow, c, value);
    afterWordTool();
  },
  addColumn(name, cell) {
    addColumn(sheet.columns.length, name);
    sheet.columns[sheet.columns.length - 1].cell = cell;
    afterWordTool();
    return sheet.columns.length - 1;
  },
  showRow: (k) => k >= 0 && showWord(k),
};
const wordPaste = mountWordPaste(wordTools);
const suggestPanel = mountSuggest(wordTools);

$("#pastelist").addEventListener("click", () => wordPaste.open());
$("#pastelist-m").addEventListener("click", () => wordPaste.open());
$("#rf-suggest").addEventListener("click", () => suggestPanel.open([ui.row]));
$("#suggestrows").addEventListener("click", () => {
  const box = bounds();
  const rows = [];
  if (box && box.r2 >= firstWordRow) {
    for (let r = Math.max(box.r1, firstWordRow); r <= box.r2; r++) rows.push(r - firstWordRow);
  }
  suggestPanel.open(rows.length ? rows : [ui.row]);
});

// ---- the grid's own buttons ------------------------------------------------

$("#addrow").addEventListener("click", () => {
  mark();
  const k = addRow();
  afterShape();
  select(k + firstWordRow, 0);
  startEditing(k + firstWordRow, 0);
  reveal(k + firstWordRow, 0);
});
$("#addcol").addEventListener("click", () => {
  mark();
  addColumn();
  ui.col = sheet.columns.length - 1;
  afterShape();
  select(0, ui.col);
  startEditing(0, ui.col);
});

// ---- the bars ---------------------------------------------------------------

$("#undo").addEventListener("click", undo);
$("#redo").addEventListener("click", redo);
$("#open").addEventListener("click", () => $("#file").click());
$("#pick").addEventListener("click", () => $("#file").click());
$("#file").addEventListener("change", (e) => {
  const file = e.target.files?.[0];
  e.target.value = "";
  if (file) openFile(file);
});
$("#tplfile").addEventListener("change", (e) => {
  const file = e.target.files?.[0];
  e.target.value = "";
  if (file) openFile(file, true);
});
$("#keep").addEventListener("click", () => saveTemplate(exportGrid(), sheet.title.trim() || fileBase()));
$("#new").addEventListener("click", async () => {
  const sure = await ask({
    title: t("shNewTitle"),
    text: t("shNewText", wordCount()),
    yes: t("shNewYes"),
    no: t("shKeep"),
  });
  if (!sure) return;
  dropDraft();
  sheet = blankSheet();
  steps.past.length = steps.future.length = 0;
  setStage("empty");
  scrollTo({ top: 0 });
});

$("#tpl-name").addEventListener("input", paintNameNote);
// Closed, the step is no longer what the address says is open.
$("#tplbox").addEventListener("close", syncAddress);
$("#tpl-name").addEventListener("keydown", (e) => {
  if (e.key !== "Enter" || e.isComposing) return;
  e.preventDefault();
  createFromStep();
});
$("#nameoffer-go").addEventListener("click", () => rename(sheet.title || fileBase()));

$("#todeck").addEventListener("click", toDeck);
$("#saveopen").addEventListener("click", openSaveMenu);
$("#rail-deck").addEventListener("click", toDeck);
$("#save-csv").addEventListener("click", saveCsv);
$("#save-xlsx").addEventListener("click", saveXlsx);
$("#save-txt").addEventListener("click", saveTxt);
$("#save-tsv").addEventListener("click", saveTsv);
$("#copy-text").addEventListener("click", copyText);
$("#copy-table").addEventListener("click", copyTable);
$("#save-link").addEventListener("click", () => {
  $("#savebox").close();
  openShare();
});
$("#copytext").addEventListener("click", copyText);
$(".sheetforms").addEventListener("click", (e) => {
  const b = e.target.closest("[data-form]");
  if (b && b.dataset.form !== ui.form) setForm(b.dataset.form);
});
$("#sheettext").addEventListener("input", () => {
  paintPaper();
  clearTimeout(textTimer);
  textTimer = setTimeout(applyText, 500);
});
$("#sheettext").addEventListener("blur", () => {
  if (textTimer) applyText();
  if (ui.form === "text") paintText({ force: true });
});
addEventListener("resize", () => ui.form === "text" && paintPaper());
// ⋯ on a phone: the toolbar's rarer actions, closed by a pick, a tap elsewhere or Escape.
function rareMenu(open) {
  $(".sheetbar .src-acts").classList.toggle("open", open);
  $("#moreacts").setAttribute("aria-expanded", String(open));
}
$("#moreacts").addEventListener("click", () => rareMenu($("#moreacts").getAttribute("aria-expanded") !== "true"));
$("#rareacts").addEventListener("click", (e) => {
  if (e.target.closest("button")) rareMenu(false);
});
document.addEventListener("click", (e) => {
  if (!e.target.closest(".sheetbar .src-acts")) rareMenu(false);
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && $("#moreacts").getAttribute("aria-expanded") === "true") {
    rareMenu(false);
    $("#moreacts").focus();
  }
});

// The sticky bar's height, for the page's scroll-padding (200% zoom included).
new ResizeObserver(() =>
  document.documentElement.style.setProperty("--outbar-h", `${Math.ceil($("#outbar").getBoundingClientRect().height)}px`),
).observe($("#outbar"));

$("#filenote-close").addEventListener("click", () => {
  $("#filenote").hidden = true;
  try {
    localStorage.setItem(NOTE_DISMISSED, "1");
  } catch {
    // A private window: put away for this visit only.
  }
});
$("#share-deck").addEventListener("change", paintShare);
$("#vocab-lang").addEventListener("change", (e) => {
  vocabChoice.lang = e.target.value;
  paintStep();
});
for (const [id, key] of [["#vocab-word", "word"], ["#vocab-example", "example"]]) {
  $(id).addEventListener("change", (e) => {
    vocabChoice[key] = e.target.checked;
    paintStep();
  });
}
$("#share-copy").addEventListener("click", copyShare);
$("#share-native").addEventListener("click", async () => {
  try {
    // Named so a chat full of saved links can be told apart: which sheet, how
    // many words, and when — the newest is the one to open.
    const when = new Date().toLocaleDateString(lang() === "vi" ? "vi-VN" : "en-GB", { day: "2-digit", month: "2-digit" });
    const label = t("shShareLabel", sheet.title || "SheetCards", wordCount(), when);
    await navigator.share({ title: label, text: label, url: $("#share-url").value });
    markFiled("link");
    toast(t("shLinkKept"), "ok");
  } catch {
    // Dismissed: nothing to say.
  }
});
$("#share-url").addEventListener("focus", (e) => e.target.select());

// A tap on a dialog's backdrop puts it away, as it does on Sheet to Anki.
for (const box of document.querySelectorAll(".pickbox")) {
  box.addEventListener("click", (e) => {
    if (e.target === box && box.id !== "askbox") box.close();
  });
}

document.addEventListener("change", (e) => {
  if (e.target.id !== "tpl") return;
  ui.template = Number(e.target.value);
  drawCard();
});

addEventListener("message", (e) => {
  const frame = $("#card");
  const height = Number(e.data?.h);
  if (frame && e.source === frame.contentWindow && height > 0) {
    frame.style.height = `${Math.ceil(height)}px`;
  }
});

WIDE.addEventListener("change", () => {
  if (ui.stage !== "edit") return;
  if ($("#rowform").open) closeForm();
  stopEditing();
  ui.sel = null;
  paintRows();
});

// ---- the grid: pointer, keyboard, clipboard --------------------------------

let dragging = false;
let filling = null;

function fillFrom(src, box) {
  const height = src.r2 - src.r1 + 1;
  const width = src.c2 - src.c1 + 1;
  for (let r = box.r1; r <= box.r2; r++) {
    for (let c = box.c1; c <= box.c2; c++) {
      if (r >= src.r1 && r <= src.r2 && c >= src.c1 && c <= src.c2) continue;
      // An ID is a key, and a key repeated down a column is every note but one lost.
      if (c === -1 && r >= firstWordRow) continue;
      const from = {
        r: src.r1 + ((((r - src.r1) % height) + height) % height),
        c: src.c1 + ((((c - src.c1) % width) + width) % width),
      };
      writeCell(r, c, cellAt(from.r, from.c));
    }
  }
}

// Tabbed into: the arrow keys start from the first word.
$("#sheet").addEventListener("focus", () => {
  if (!ui.sel && ui.stage === "edit") select(Math.min(firstWordRow, lastRow()), 0);
});

$("#sheet").addEventListener("click", (e) => {
  if (!e.target.closest("#cfgsum")) return;
  ui.cfgOpen = !cfgOpen();
  // Step 1 holds it open; folding it there means going back to the words.
  if (!ui.cfgOpen && ui.view === "look") setView("rows");
  paintCfgFold();
});

$("#sheet").addEventListener("pointerdown", (e) => {
  if (e.target === FILL_HANDLE) {
    e.preventDefault();
    filling = bounds();
    return;
  }
  const ref = e.target.closest(".ref");
  if (ref) {
    e.preventDefault();
    if (ref.dataset.all !== undefined) {
      select(0, -1);
      select(lastRow(), sheet.columns.length - 1, true);
    } else if (ref.dataset.c !== undefined) {
      select(0, Number(ref.dataset.c));
      select(lastRow(), Number(ref.dataset.c), true);
    } else if (ref.dataset.r !== undefined) {
      select(Number(ref.dataset.r), -1);
      select(Number(ref.dataset.r), sheet.columns.length - 1, true);
    }
    return;
  }
  const cell = e.target.closest(".cell");
  if (!cell) return;
  const [r, c] = [Number(cell.dataset.r), Number(cell.dataset.c)];
  if (e.pointerType === "touch") {
    clearSelection();
    follow(r, c);
    startEditing(r, c);
    return;
  }
  if (ui.editing?.r === r && ui.editing?.c === c) return;
  if (e.button === 2) {
    const box = bounds();
    if (box && r >= box.r1 && r <= box.r2 && c >= box.c1 && c <= box.c2) return;
  }
  e.preventDefault();
  select(r, c, e.shiftKey);
  dragging = e.button === 0;
});

$("#sheet").addEventListener("pointermove", (e) => {
  const cell = e.target.closest(".cell");
  if (!cell) return;
  const [r, c] = [Number(cell.dataset.r), Number(cell.dataset.c)];
  if (filling) {
    ui.sel = {
      r: Math.min(filling.r1, r),
      c: Math.min(filling.c1, c),
      r2: Math.max(filling.r2, r),
      c2: Math.max(filling.c2, c),
    };
    paintSelection();
    return;
  }
  if (dragging) select(r, c, true);
});

addEventListener("pointerup", () => {
  dragging = false;
  if (!filling) return;
  const box = bounds();
  const src = filling;
  filling = null;
  if (box.r1 === src.r1 && box.r2 === src.r2 && box.c1 === src.c1 && box.c2 === src.c2) return;
  mark();
  fillFrom(src, box);
  afterShape();
});

$("#sheet").addEventListener("dblclick", (e) => {
  const cell = e.target.closest(".cell");
  if (cell) startEditing(Number(cell.dataset.r), Number(cell.dataset.c));
});

$("#sheet").addEventListener("contextmenu", (e) => {
  const cell = e.target.closest(".cell, .ref[data-r]");
  if (!cell) return;
  e.preventDefault();
  const r = Number(cell.dataset.r);
  const c = cell.dataset.c === undefined ? -1 : Number(cell.dataset.c);
  const box = bounds();
  const inside = box && r >= box.r1 && r <= box.r2 && (cell.classList.contains("ref") || (c >= box.c1 && c <= box.c2));
  if (!inside) select(r, c);
  openMenu(e.clientX, e.clientY);
});

/**
 * The right-click menu: what a spreadsheet offers at the cell under the pointer.
 * Rows of words can be inserted, moved and deleted; columns inserted and
 * deleted; any range emptied.
 */
const MENU_LABEL = {
  above: "shInsertAbove",
  below: "shInsertBelow",
  up: "shMoveUp",
  down: "shMoveDown",
  droprow: "shDeleteRows",
  left: "edInsertLeft",
  right: "edInsertRight",
  drop: "edRemoveColumn",
  clear: "edClearCells",
};

function closeMenu() {
  document.getElementById("cellmenu")?.remove();
}

function openMenu(x, y) {
  closeMenu();
  const box = bounds();
  const words = box && box.r2 >= firstWordRow;
  const groups = [
    words ? ["above", "below", "up", "down", "droprow"] : [],
    ["left", "right", "drop"],
    ["clear"],
  ].filter((g) => g.length);
  const disabled = (id) =>
    (id === "drop" && (sheet.columns.length < 2 || box.c1 < 0)) ||
    (id === "up" && box.r1 <= firstWordRow) ||
    (id === "down" && box.r2 >= lastRow());
  const el = document.createElement("div");
  el.id = "cellmenu";
  el.className = "menu";
  el.setAttribute("role", "menu");
  el.style.left = `${x}px`;
  el.style.top = `${y}px`;
  el.innerHTML = groups
    .map((g) =>
      g
        .map(
          (id) =>
            `<button type="button" role="menuitem" data-menu="${id}"${disabled(id) ? " disabled" : ""}>` +
            `${escapeHtml(t(MENU_LABEL[id], box.r2 - Math.max(box.r1, firstWordRow) + 1))}</button>`,
        )
        .join(""),
    )
    .join('<hr class="menusep">');
  document.body.append(el);
  const rect = el.getBoundingClientRect();
  if (rect.right > innerWidth) el.style.left = `${Math.max(4, innerWidth - rect.width - 4)}px`;
  if (rect.bottom > innerHeight) el.style.top = `${Math.max(4, y - rect.height)}px`;
  el.querySelector("button:not(:disabled)")?.focus();
}

function runMenu(id) {
  const box = bounds();
  closeMenu();
  if (!box) return;
  mark();
  const k1 = Math.max(box.r1, firstWordRow) - firstWordRow;
  const k2 = box.r2 - firstWordRow;
  if (id === "clear") {
    for (let r = box.r1; r <= box.r2; r++) {
      for (let c = box.c1; c <= box.c2; c++) {
        if (!(c === -1 && r >= firstWordRow)) writeCell(r, c, "");
      }
    }
  } else if (id === "above" || id === "below") {
    const at = id === "above" ? k1 : k2 + 1;
    addRow(at);
    ui.sel = { r: at + firstWordRow, c: Math.max(0, box.c1), r2: at + firstWordRow, c2: Math.max(0, box.c1) };
  } else if (id === "up" || id === "down") {
    const by = id === "up" ? -1 : 1;
    const order = by < 0 ? [...Array(k2 - k1 + 1).keys()] : [...Array(k2 - k1 + 1).keys()].reverse();
    for (const i of order) moveRow(k1 + i, by);
    ui.sel = { ...ui.sel, r: ui.sel.r + by, r2: ui.sel.r2 + by };
    ui.row = Math.max(0, ui.row + by);
  } else if (id === "droprow") {
    removeRows(k1, k2);
    ui.sel = null;
  } else if (id === "drop") {
    for (let c = box.c2; c >= box.c1; c--) removeColumn(c);
    ui.sel = null;
  } else {
    const at = box.c1 < 0 ? 0 : id === "left" ? box.c1 : box.c2 + 1;
    addColumn(at);
    ui.col = at;
    ui.sel = { r: 0, c: at, r2: 0, c2: at };
  }
  afterShape();
}

document.addEventListener("keydown", (e) => {
  const cmd = e.ctrlKey || e.metaKey;
  if (e.key === "Escape" && document.getElementById("cellmenu")) return closeMenu();

  if (ui.editing) {
    const { r, c } = ui.editing;
    if (e.key === "Escape") {
      stopEditing();
      select(r, c);
      $("#sheet").focus({ preventScroll: true });
    } else if (e.key === "Enter" && !e.shiftKey && !e.altKey && !e.isComposing) {
      // Enter goes down, as in a spreadsheet; past the last word it makes one.
      e.preventDefault();
      stopEditing();
      if (r === lastRow() && r >= firstWordRow && !blankRow(sheet.rows[r - firstWordRow])) {
        mark();
        addRow();
        afterShape();
      }
      select(Math.min(lastRow(), r + 1), c);
      reveal(Math.min(lastRow(), r + 1), c);
      $("#sheet").focus({ preventScroll: true });
    } else if (e.key === "Tab") {
      // On to the next cell's field, as in a spreadsheet, wrapping at the end of
      // a row; past the last cell Tab leaves the grid.
      const next = nextCell(r, c, e.shiftKey ? -1 : 1);
      stopEditing();
      if (!next) return;
      e.preventDefault();
      select(next.r, next.c);
      reveal(next.r, next.c);
      if (!startEditing(next.r, next.c)) $("#sheet").focus({ preventScroll: true });
    }
    return;
  }

  if (document.activeElement?.matches?.("input, textarea, select") && !document.activeElement.closest("#sheet")) return;
  if ($("dialog[open]")) return;

  if (cmd && (e.key === "z" || e.key === "Z") && !e.shiftKey) {
    e.preventDefault();
    return undo();
  }
  if (cmd && (e.key === "z" || e.key === "Z" || e.key === "y" || e.key === "Y")) {
    e.preventDefault();
    return redo();
  }

  if (!ui.sel || !WIDE.matches || ui.stage !== "edit") return;
  const { r, c } = ui.sel;
  const step = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] }[e.key];
  if (step) {
    e.preventDefault();
    if (e.shiftKey) {
      const anchor = { r, c };
      select(ui.sel.r2 + step[0], ui.sel.c2 + step[1], true);
      ui.sel = { ...anchor, r2: ui.sel.r2, c2: ui.sel.c2 };
      reveal(ui.sel.r2, ui.sel.c2);
    } else {
      // A folded settings row is stepped over.
      let to = r + step[0];
      if (to === 1 && !cfgOpen()) to += step[0] || 0;
      select(Math.max(0, to), c + step[1]);
      reveal(ui.sel.r, ui.sel.c);
    }
    return;
  }
  if (e.key === "Enter" || e.key === "F2") {
    e.preventDefault();
    return void startEditing(r, c);
  }
  if (e.key === "Escape") return clearSelection();
  if (e.key === "a" && cmd) {
    e.preventDefault();
    select(0, -1);
    return select(lastRow(), sheet.columns.length - 1, true);
  }
  if (e.key === "Delete" || e.key === "Backspace") {
    e.preventDefault();
    mark();
    const box = bounds();
    for (let row = box.r1; row <= box.r2; row++) {
      for (let col = box.c1; col <= box.c2; col++) {
        if (!(col === -1 && row >= firstWordRow)) writeCell(row, col, "");
      }
    }
    return afterShape();
  }
  if (e.key.length === 1 && !cmd && !e.altKey) {
    if (!startEditing(r, c)) return;
    e.preventDefault();
    const box = document.activeElement;
    markRun(`cell:${box.dataset.edit}:${box.dataset.row ?? ""}:${box.dataset.col ?? ""}`);
    box.value = e.key;
    writeCell(r, c, e.key);
    if (box.tagName === "TEXTAREA") grow(box);
    paintOut();
    drawSoon();
    saveSoon();
  }
});

document.addEventListener("copy", (e) => {
  if (!ui.sel || ui.editing || !WIDE.matches || ui.form === "text") return;
  e.preventDefault();
  e.clipboardData.setData("text/plain", selectionTsv());
  toast(t("edCopiedCells"), "ok");
});

document.addEventListener("cut", (e) => {
  if (!ui.sel || ui.editing || !WIDE.matches || ui.form === "text") return;
  e.preventDefault();
  e.clipboardData.setData("text/plain", selectionTsv());
  mark();
  const box = bounds();
  for (let r = box.r1; r <= box.r2; r++) {
    for (let c = box.c1; c <= box.c2; c++) {
      if (!(c === -1 && r >= firstWordRow)) writeCell(r, c, "");
    }
  }
  afterShape();
});

/**
 * A block pasted onto the page. Onto a selected cell it goes *there*, growing
 * the sheet as far as it reaches; with nothing selected, a whole sheet replaces
 * this one and rows of words are added under these. One cell's worth of text,
 * or a paste into any other box, is the browser's.
 */
document.addEventListener("paste", (e) => {
  if (ui.stage !== "edit" || $("dialog[open]")) return;
  const text = e.clipboardData?.getData("text/plain") ?? "";
  const focus = document.activeElement;
  const inBox = focus?.matches?.("input, textarea") && !focus.closest("#sheet");
  if (inBox || (ui.editing && !/[\t\n]/.test(text.replace(/\n$/, "")))) return;
  const block = parseTsv(text);
  const before = snapshot();
  let read = null;
  if (ui.sel) {
    if (ui.editing) stopEditing();
    read = pasteAt(block);
  } else if (/[\t\n]/.test(text)) read = importBlock(block);
  if (!read) return;
  e.preventDefault();
  commit(before);
  afterShape();
  if (read.replaced) toast(t("shPastedSheet", read.rows), "ok");
  else if (read.added) toast(t("shPastedRows", read.added), "ok");
  else toast(t("shPastedCells", read.rows), "ok");
});

// ---- a file dropped anywhere -------------------------------------------------

let dragDepth = 0;
const draggingFile = (e) => [...(e.dataTransfer?.types || [])].includes("Files");
addEventListener("dragenter", (e) => {
  if (!draggingFile(e)) return;
  dragDepth++;
  $("#drop").hidden = false;
});
addEventListener("dragover", (e) => draggingFile(e) && e.preventDefault());
addEventListener("dragleave", () => {
  dragDepth = Math.max(0, dragDepth - 1);
  if (!dragDepth) $("#drop").hidden = true;
});
addEventListener("drop", (e) => {
  if (!draggingFile(e)) return;
  e.preventDefault();
  dragDepth = 0;
  $("#drop").hidden = true;
  const file = e.dataTransfer.files?.[0];
  if (file) openFile(file);
});

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------

let bootStep = "boot";
let bootSlow = false;
let bootBytes = 0;
const bootStatus = () =>
  status(
    [
      bootStep !== "boot"
        ? t("loadingCode")
        : bootBytes
          ? t("bootingMB", mb(bootBytes), mb(FIRST_LOAD_BYTES))
          : t("booting"),
      onMobileData() && t("bootData", mb(FIRST_LOAD_BYTES)),
      bootSlow && t("slowBoot"),
    ]
      .filter(Boolean)
      .join("\n"),
    "",
    true,
  );

/** What the address and the saved draft ask for, in that order. */
async function arrive() {
  const want = readState(location.search, SHEET_STATE);
  const draft = loadDraft();
  if (isShare(location.hash)) {
    let shared = null;
    try {
      const { name, tsv } = await decodeShare(location.hash);
      shared = fromGrid(parseTsv(tsv), name);
    } catch (err) {
      toast(t(err.code === "version" ? "shareTooNew" : "shareBroken"), "bad");
    }
    // The fragment has done its job; left in the address, a reload would ask
    // the same question again over edits made since.
    history.replaceState(null, "", location.pathname + location.search);
    if (shared) {
      const differs = draft && JSON.stringify(draft.sheet) !== JSON.stringify(shared) && draft.sheet.rows.some((r) => !blankRow(r));
      const replace =
        !differs ||
        (await ask({
          title: t("shSharedTitle"),
          text: t("shSharedText", shared.title || "—", draft.sheet.title || "—"),
          yes: t("shSharedYes"),
          no: t("shKeep"),
        }));
      if (replace) {
        // Opened from the link it was saved in: kept, until it changes.
        begin(shared, { filed: toTsv(exportGrid(shared)), how: "link" });
        toast(t("shOpened", shared.title || fileBase(), wordCount()), "ok");
        return arriveAt(want);
      }
    }
  }
  if (draft) {
    begin(draft.sheet, {
      row: draft.row ?? 0,
      col: draft.col ?? 0,
      view: draft.view === "look" ? "look" : "rows",
      filed: typeof draft.filed === "string" ? draft.filed : null,
      how: draft.how === "link" ? "link" : "file",
    });
  }
  else setStage("empty");
  // The landing page's "no sheet yet" door: straight to the templates, which on
  // a phone are a screen or two below the other ways in.
  if (location.hash === "#templates" && ui.stage === "empty") {
    requestAnimationFrame(() => $("#templates-title").scrollIntoView({ block: "start" }));
  }
  return arriveAt(want);
}

/** After the sheet is open: the step or the view the address asked for. */
function arriveAt(want) {
  if (want.tpl && openAsked(want)) return;
  if (want.form && ui.stage === "edit") setForm(want.form, { remember: false });
  if (want.view && ui.stage === "edit") {
    setView(want.view);
    drawCard();
  }
  syncAddress();
}

wireSave();
setForm(storedForm(), { remember: false });
paintIcons();
paintChrome();
mountInAppBanner({ t, icon });

const slowTimer = setTimeout(() => {
  bootSlow = true;
  if (!run) bootStatus();
}, 10_000);

// Started before anything is asked, so a question about a shared link does not
// hold up the ~6 MB download behind it.
let bootPainted = 0;
const python = startPython(
  SHEETPY,
  (step) => {
    bootStep = step;
    if (!run) bootStatus();
  },
  (done) => {
    bootBytes = done;
    if (!run && (done - bootPainted >= 5e5 || done === FIRST_LOAD_BYTES)) {
      bootPainted = done;
      bootStatus();
    }
  },
)
  .then((py) => {
    clearTimeout(slowTimer);
    keys = JSON.parse(py.globals.get("keys")());
    const fn = py.globals.get("preview");
    run = (payload) => JSON.parse(fn(payload));
    const xl = py.globals.get("xlsx");
    toXlsx = (payload) => xl(payload).toJs();
    const of = py.globals.get("open_file");
    readFile = (bytes, name, index) => JSON.parse(of(bytes, name, index));
    booted = true;
    status("");
    // A kept template's card could not be drawn before now.
    if (ui.stage === "empty") paintMine();
    if ($("#tplbox").open && (isMine(stepId) || stepId === "custom")) paintStep();
    if (ui.stage === "edit") {
      paintColumns();
      drawCard();
    }
    while (queue.length) queue.shift()();
  })
  .catch((err) => status(t("bootFailed", err.message), "bad"));

await arrive();
if (!run) bootStatus();
void python;
