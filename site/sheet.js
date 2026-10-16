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

import { renderCard, escapeHtml } from "./anki.js";
import { LANGUAGES, lang, paintDocLinks, setLang, t } from "./i18n.js";
import { startPython } from "./pyodide.js";
import { backOnly, cardDoc, cardFrame } from "./cardframe.js";
import { icon, paintIcons } from "./icons.js";
import { deckTree, treeHtml } from "./decktree.js";
import { stashFile } from "./handoff.js";
import { LONG_LINK, asCsv, decodeShare, encodeShare, isShare, parseTsv, toTsv } from "./sharelink.js";
import { PALETTES, PIECES, TEMPLATES } from "./sheet-templates.js";
import { MAX_TEMPLATES, dropTemplate, keepTemplate, listTemplates } from "./usertemplates.js";

/** What the page asks of the add-on's code. */
const SHEETPY = String.raw`
import csv
import io
import json
from sc import workbook
from sc.card_layout import build_templates, split_sides
from sc.column_model import deck_path, plan_columns
from sc.sheet_config import SheetConfig, is_config_row, parse_config_row
from sc.tsv_model import build_tags


def keys():
    """The directive names and the closed value sets, read off sheet_config.

    A closed set is the add-on's to decide, so it is sent rather than copied
    into JavaScript where it would be a second answer.
    """
    from sc.sheet_config import (
        ALIGNMENTS,
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
        {"tabs": out["tabs"], "tab": out["tab"], "rows": rows}, ensure_ascii=False
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
const MAIN = ["basic", "vocab", "hanzi", "kanji", "custom"];
const MORE = TEMPLATES.filter((tpl) => tpl.more);
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
  sort: { text: "helpSort" },
  math: { text: "helpMath", sample: "a^2 + b^2 = c^2" },
  code: { text: "helpCode", sample: "def greet(name):\n    print('hi', name)" },
  font: { text: "helpFont" },
  rtl: { text: "helpRtl", sample: "مرحبا بالعالم" },
  vertical: { text: "helpVertical", sample: "山は静かです" },
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
let sheet = { title: "", marker: "#config", columns: [], rows: [] };

const ui = {
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
  if (c === -1) return r === 0 ? "ID" : r === 1 ? sheet.marker : (sheet.rows[r - 2]?.id ?? "");
  const col = sheet.columns[c];
  if (!col) return "";
  if (r === 0) return col.name;
  if (r === 1) return col.cell;
  return sheet.rows[r - 2]?.values[c] ?? "";
}

function writeCell(r, c, text) {
  if (c === -1) {
    if (r === 1) sheet.marker = text;
    else if (r >= 2 && sheet.rows[r - 2]) sheet.rows[r - 2].id = text;
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
  const ids = new Set(sheet.rows.map((r) => r.id));
  const shaped = [...sheet.rows].reverse().find((r) => /^(.*?)(\d+)$/.test(r.id));
  let prefix = "w";
  let width = 2;
  if (shaped) {
    const m = shaped.id.match(/^(.*?)(\d+)$/);
    prefix = m[1];
    width = m[2].length;
  }
  let n = 0;
  for (const id of ids) {
    const m = id.match(/^(.*?)(\d+)$/);
    if (m && m[1] === prefix) n = Math.max(n, Number(m[2]));
  }
  let id;
  do id = prefix + String(++n).padStart(width, "0");
  while (ids.has(id));
  return id;
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
 * row by its marker, and a sheet with no ID column at all gets IDs, since a row
 * without one is a row Anki cannot keep.
 */
function fromGrid(grid, title) {
  const rows = (grid || []).map((row) => row.map((cell) => String(cell ?? "")));
  const header = rows[0] || [];
  const idAt = header.findIndex((h) => /^\s*﻿?id\s*$/i.test(h));
  const keyAt = idAt < 0 ? 0 : idAt;
  const marked = rows[1] && isMarkerCell(rows[1][keyAt]);
  const width = Math.max(header.length, ...rows.map((r) => r.length));
  const content = [];
  for (let i = 0; i < width; i++) {
    if (i === idAt) continue;
    if (idAt < 0 && marked && i === 0) continue;
    content.push(i);
  }
  const used = content.filter(
    (i) => (header[i] || "").trim() || rows.slice(1).some((r) => (r[i] || "").trim()),
  );
  const out = {
    title: title ?? "",
    marker: marked ? rows[1][keyAt].trim() : "#config",
    columns: used.map((i, n) => ({
      name: (header[i] || "").trim() || `Column ${n + 1}`,
      cell: marked ? (rows[1][i] || "").trim() : "",
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
  const made = sheet;
  sheet = before;
  return made;
}

/** The sheet as rows of text — what every way out of this page writes. */
function exportGrid(of = sheet) {
  return [
    ["ID", ...of.columns.map((c) => c.name)],
    [of.marker, ...of.columns.map((c) => c.cell)],
    ...of.rows.filter((r) => !blankRow(r)).map((r) => [r.id, ...r.values]),
  ];
}

const wordCount = () => sheet.rows.filter((r) => !blankRow(r)).length;

/** A file name made of the sheet's title. */
function fileBase() {
  return (sheet.title || t("tplBlankName")).replace(/[\\/:*?"<>|]+/g, " ").trim() || "Sheet";
}

// ---------------------------------------------------------------------------
// The draft, kept in this browser
// ---------------------------------------------------------------------------

const DRAFT = "sc-sheet-draft";
let saveTimer = 0;

// The sheet as it was when last written to a file or opened from one. The draft
// lives only in this browser; the file is what lasts, opens on any device and
// in any spreadsheet — so the page says when the sheet has moved on from it.
let lastFiled = null;
const filedText = () => toTsv(exportGrid());
const isFiled = () => lastFiled === filedText();
function markFiled() {
  lastFiled = filedText();
  paintFiled();
  saveSoon();
}

function paintFiled() {
  if (ui.stage !== "edit") return;
  const filed = isFiled();
  const button = $("#savecsv");
  button.classList.toggle("unsaved", !filed && wordCount() > 0);
  $("#filed").textContent = t(filed ? "shFiled" : "shNotFiled");
  $("#filed").className = `filed ${filed ? "ok" : wordCount() ? "bad" : ""}`;
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
  if (ui.stage !== "edit") return;
  paintFiled();
  try {
    localStorage.setItem(
      DRAFT,
      JSON.stringify({ v: 1, sheet, row: ui.row, col: ui.col, view: ui.view, filed: lastFiled }),
    );
    $("#saved").textContent = t("shSaved");
    $("#saved").className = "saved";
  } catch {
    $("#saved").textContent = t("shNotSaved");
    $("#saved").className = "saved bad";
  }
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
  paintDocLinks();
  for (const el of document.querySelectorAll("[data-i18n]")) {
    el.innerHTML = t(el.dataset.i18n);
  }
  for (const el of document.querySelectorAll("[data-i18n-attr]")) {
    for (const pair of el.dataset.i18nAttr.split(",")) {
      const [attr, key] = pair.split(":").map((s) => s.trim());
      el.setAttribute(attr, t(key));
    }
  }
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
}

/**
 * Which of the two steps is in front: "look" is step 1, the template (the
 * columns, the settings row and the card they make), "rows" step 2, the words.
 * A phone shows one at a time; a wide screen shows both and numbers them.
 */
function setView(view) {
  ui.view = view;
  $("#app").dataset.view = view;
  for (const b of document.querySelectorAll(".viewseg [data-view]")) {
    b.setAttribute("aria-pressed", String(b.dataset.view === view));
  }
  // A wide screen shows both steps; step 1 folds to its heading while the
  // words are being written, and this opens it again.
  $("#tplfold-text").textContent = t(view === "look" ? "shFoldTemplate" : "shEditTemplate");
  $("#tplfold").setAttribute("aria-expanded", String(view === "look"));
}

/**
 * Starts editing a sheet: a template, a file, a link or the saved draft.
 * `view` is the step it opens on; `filed` is the sheet as last written to a
 * file (see isFiled), or null for a sheet no file holds yet.
 */
function begin(next, { row = 0, col = 0, keepHistory = false, view = "rows", filed = null } = {}) {
  if (keepHistory && ui.stage === "edit") mark();
  else {
    steps.past.length = 0;
    steps.future.length = 0;
  }
  sheet = next;
  lastFiled = filed;
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
  { rootMargin: "200px 0px" },
);

const FACE_CAPTION = { front: "demoFront", back: "demoBack", front2: "tplRevFront", back2: "tplRevBack" };

/**
 * A card's faces side by side, as frames filled when seen. A compact tile has no
 * captions; `waiting` draws the outline of a card whose rendering has to wait
 * for Python (a template somebody kept, which the build has never seen).
 */
function facesHtml(key, faces = ["front", "back"], { compact = false, waiting = false } = {}) {
  // Two faces in a small tile are each a quarter of a card: drawn smaller still.
  const zoom = compact ? (faces.length > 1 ? (WIDE.matches ? 0.5 : 0.42) : 0.55) : 0.6;
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
  let card = null;
  try {
    const made = fromGrid(tpl.rows, tpl.title);
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
  mineCards.set(tpl.id, card);
  return card;
}

/** What a template makes right now: its rows and its first word's card. */
function templateNow(id, choice = vocabChoice) {
  if (id === "basic") return basicVariant();
  if (byId(id)?.rows) return byId(id);
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
  return fromGrid(withTheme(templateNow(id, choice).rows, theme), textOf(id).name);
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
function sheetScrap(rows, { mini = false } = {}) {
  const width = Math.max(...rows.map((r) => r.length));
  const shown = mini ? rows.slice(0, 3) : rows;
  const head = `<tr><th></th>${Array.from({ length: width }, (_, i) => `<th>${letter(i)}</th>`).join("")}</tr>`;
  const body = shown
    .map(
      (row, r) =>
        `<tr class="${r === 0 ? "names" : r === 1 ? "settings" : ""}"><th>${r + 1}</th>${Array.from(
          { length: width },
          (_, c) => `<td>${escapeHtml(row[c] ?? "")}</td>`,
        ).join("")}</tr>`,
    )
    .join("");
  return `<table class="scrap${mini ? " mini" : ""}">${head}${body}</table>`;
}

/** Which faces a tile shows: the front, and the reverse card's front if any. */
function tileFaces(card) {
  return card?.reverse ? ["front", "front2"] : ["front"];
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
    const rows = exportGrid(templateSheet(id, VOCAB_DEFAULT));
    return `<div class="tplcard">
        ${facesHtml(id)}
        <button type="button" class="tpl-go" data-template="${id}">
          <strong>${escapeHtml(text.title)}</strong>
          <span class="tpl-desc">${escapeHtml(text.text)}</span>
        </button>
        <div class="tpl-sheet" aria-hidden="true">${sheetScrap(rows, { mini: true })}</div>
      </div>`;
  }).join("");
  watchFaces($("#templates"), (id) => templateNow(id, VOCAB_DEFAULT).card);

  // The others, smaller: one face each — the card as it comes out, its theme
  // and all — and a name.
  $("#moretemplates").innerHTML = MORE.map((tpl) => {
    const text = textOf(tpl.id);
    return `<div class="tplmini">
        ${facesHtml(tpl.id, tileFaces(variantOf(tpl, VOCAB_DEFAULT).card), { compact: true })}
        <button type="button" class="tpl-go" data-template="${tpl.id}">
          <strong>${escapeHtml(text.title)}</strong>
          <span class="tpl-desc">${escapeHtml(text.text)}</span>
        </button>
      </div>`;
  }).join("");
  watchFaces($("#moretemplates"), (id) => variantOf(byId(id), VOCAB_DEFAULT).card);
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
    const rows = exportGrid(fromGrid(tpl.rows, tpl.title));
    return `<div class="tplmini mine">
        ${facesHtml(id, tileFaces(card), { compact: true, waiting: !card })}
        <button type="button" class="tpl-go" data-template="${escapeHtml(id)}">
          <strong>${escapeHtml(text.title)}</strong>
          <span class="tpl-desc">${escapeHtml(text.text)}</span>
        </button>
        <div class="tpl-sheet" aria-hidden="true">${sheetScrap(rows, { mini: true })}</div>
        <button type="button" class="iconbtn tpl-del" data-drop="${escapeHtml(tpl.id)}"
          title="${escapeHtml(t("tplDelete"))}" aria-label="${escapeHtml(`${t("tplDelete")}: ${tpl.title}`)}">${icon("trash-2")}</button>
      </div>`;
  });
  const add =
    list.length < MAX_TEMPLATES
      ? `<button type="button" class="tplmini tpl-add" id="tpl-upload">
          <span class="tpl-add-icon">${icon("upload")}</span>
          <strong>${escapeHtml(t("tplUpload"))}</strong>
          <span class="tpl-desc">${escapeHtml(t("tplUploadHint"))}</span>
        </button>`
      : "";
  $("#mytemplates").innerHTML = tiles.join("") + add;
  watchFaces($("#mytemplates"), (id) => templateNow(id).card);
}

/**
 * Keeps a grid as one of this browser's templates and says how that went. The
 * grid is the sheet as exportGrid writes it, so a kept template is the sheet
 * the editor would have saved.
 */
function saveTemplate(grid, title) {
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
  $("#vocab-opts").hidden = !languaged;
  $("#tpl-mine").hidden = !isMine(stepId);
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
  $("#tpl-sheet").innerHTML = sheetScrap(exportGrid(templateSheet(stepId)));
}

function pickTemplate(id) {
  if (isMine(id) && !mineOf(id)) return paintMine();
  stepId = id;
  stepTheme = null;
  paintStep();
  $("#tplbox").showModal();
  $("#tpl-go").focus();
}

/** The step's sheet as a .csv — the same writer as Download .csv in the editor. */
function stepCsv() {
  const made = templateSheet(stepId);
  const name = `${made.title}.csv`;
  download(new Blob([asCsv(exportGrid(made))], { type: "text/csv" }), name);
  toast(t("shDownloaded", name), "ok");
}

function createFromStep() {
  $("#tplbox").close();
  const made = templateSheet(stepId);
  // A kept template is step 1 done: its sample word is not one of the words.
  if (isMine(stepId)) made.rows = [{ id: "w01", values: made.columns.map(() => "") }];
  // Custom is a template to make, so it opens on step 1; every other one is a
  // template already, and opens on the words.
  begin(made, { row: 0, col: 0, view: stepId === "custom" ? "look" : "rows" });
  // A sheet with no word yet opens on its first one.
  if (stepId !== "basic" && !isMine(stepId)) return;
  if (WIDE.matches) {
    select(firstWordRow, 0);
    startEditing(firstWordRow, 0);
  } else openForm(0, { field: 0 });
}

// ---------------------------------------------------------------------------
// Painting the sheet
// ---------------------------------------------------------------------------

function paintAll() {
  $("#title").value = sheet.title;
  setView(ui.view);
  paintRows();
  paintColumns();
  paintOut();
  paintUndo();
  drawCard();
}

/** The grid on a wide screen, the list of words on a phone. */
function paintRows() {
  const n = wordCount();
  $("#rowcount").textContent = String(n);
  $("#rowcount-seg").textContent = String(n);
  if (WIDE.matches) paintSheet();
  else paintList();
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
  const cols = sheet.columns;
  const label = (key) => escapeHtml(t(key));
  const cell = (inner, r, c, cls = "") =>
    `<span class="cell ${cls}" data-r="${r}" data-c="${c}">${inner}</span>`;
  const dupes = duplicates();

  const head =
    `<span class="ref corner" data-all="1" title="${label("edSelectAll")}"></span>` +
    '<span class="ref" data-c="-1">A</span>' +
    cols.map((_, i) => `<span class="ref" data-c="${i}">${letter(i + 1)}</span>`).join("");

  const names =
    '<span class="ref" data-r="0">1</span>' +
    cell("ID", 0, -1, "fixed") +
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

  const settings =
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
        cell(
          `<input data-edit="id" data-row="${k}" value="${escapeHtml(row.id)}"
             spellcheck="false" autocomplete="off" aria-label="${label("shIdLabel")}">`,
          r,
          -1,
          `idcell${dupes.has(row.id) || !row.id.trim() ? " dup" : ""}`,
        ) +
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
  grid.innerHTML = head + names + settings + words;
  if (!SIZES_ITSELF) for (const box of grid.querySelectorAll("textarea")) grow(box);
  paintSelection();
}

/** IDs written more than once: Anki keeps one note per ID, so the rest are lost. */
function duplicates() {
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
  const dupes = duplicates();
  $("#wordlist").innerHTML = sheet.rows
    .map((row, k) => {
      const [first = "", second = ""] = row.values.filter((v) => String(v).trim());
      const empty = blankRow(row);
      return `<li><button type="button" class="worditem${k === ui.row ? " cur" : ""}${empty ? " empty" : ""}" data-row="${k}">
        <span class="wi-id${dupes.has(row.id) ? " dup" : ""}">${escapeHtml(row.id)}</span>
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
    sheet = next;
    fit();
    return { replaced: true, rows: sheet.rows.length };
  }
  // A blank word left at the end — the one a new sheet starts with — is
  // filled rather than left above what was pasted.
  while (sheet.rows.length && blankRow(sheet.rows[sheet.rows.length - 1])) sheet.rows.pop();
  const width = Math.max(...rows.map((r) => r.length));
  const withIds = width === sheet.columns.length + 1 && rows.every((r) => looksLikeId(r[0] ?? ""));
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
  const list = ui.col === -1 ? keys.deck : keys.field;
  if (ui.open && !list.includes(ui.open)) ui.open = null;
  $("#keys").innerHTML = list
    .map(
      (key) =>
        `<button type="button" class="col${on.has(key) ? " on" : ""}${ui.open === key ? " open" : ""}"` +
        ` data-key="${escapeHtml(key)}" aria-pressed="${on.has(key)}"` +
        `${hasPanel(key) ? ` aria-expanded="${ui.open === key}" aria-controls="opts"` : ""}` +
        `>${escapeHtml(key)}</button>`,
    )
    .join("");
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

  const warnings = out.warnings || [];
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
  $("#todeck").disabled = !n;
  paintFiled();
}

/** Straight on to Sheet to Anki, with the sheet as a file it opens like any other. */
async function toDeck() {
  if (!wordCount()) return toast(t("shNeedWord"), "bad");
  if (!isFiled()) {
    const save = await ask({
      title: t("shUnfiledTitle"),
      text: t("shUnfiledText"),
      yes: t("shSaveCsv"),
      no: t("shUnfiledGo"),
    });
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
  location.href = "./create.html#file";
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

function saveCsv() {
  if (!wordCount()) return toast(t("shNeedWord"), "bad");
  download(new Blob([asCsv(exportGrid())], { type: "text/csv" }), `${fileBase()}.csv`);
  $("#savebox").close();
  markFiled();
  toast(t("shDownloaded", `${fileBase()}.csv`), "ok");
}

function saveXlsx() {
  $("#savebox").close();
  whenReady(() => {
    try {
      const bytes = new Uint8Array(toXlsx(JSON.stringify({ name: sheet.title || fileBase(), rows: exportGrid() })));
      download(
        new Blob([bytes], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }),
        `${fileBase()}.xlsx`,
      );
      markFiled();
      toast(t("shDownloaded", `${fileBase()}.xlsx`), "ok");
    } catch (err) {
      toast(String(err?.message || err).split("\n").pop(), "bad");
    }
  }, t("shPreparingXlsx"));
}

/** The link, for whichever page it is to open in. */
async function shareUrl() {
  const page = $("#share-deck").checked ? "create.html" : "sheet.html";
  const hash = await encodeShare(sheet.title, toTsv(exportGrid()));
  return new URL(`./${page}${hash}`, location.href).href;
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

async function openShare() {
  if (!wordCount()) return toast(t("shNeedWord"), "bad");
  $("#share-native").hidden = !navigator.share;
  await paintShare();
  $("#sharebox").showModal();
  $("#share-copy").focus();
}

async function copyShare() {
  const url = $("#share-url").value;
  try {
    await navigator.clipboard.writeText(url);
  } catch {
    $("#share-url").select();
    if (!document.execCommand?.("copy")) return toast(t("edCopyFailed"), "bad");
  }
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

const FILE_TYPES = /\.(xlsx|xlsm|csv|tsv|txt)$/i;

/** Opens a picked file to edit — or, `asTemplate`, keeps it as a template. */
function openFile(file, asTemplate = false) {
  if (!FILE_TYPES.test(file.name)) return toast(t("badFileType", file.name), "bad");
  whenReady(() => readPicked(file, 0, true, asTemplate), t("reading"));
}

async function readPicked(file, index, choose = true, asTemplate = false) {
  let out;
  try {
    out = readFile(new Uint8Array(await file.arrayBuffer()), file.name, index);
  } catch (err) {
    return toast(String(err?.message || err).trim().split("\n").pop(), "bad");
  }
  toast("");
  const title = file.name.replace(/\.[^.]+$/, "").trim();
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
  if (asTemplate) return saveTemplate(exportGrid(fromGrid(out.rows, name)), name);
  const opened = fromGrid(out.rows, name);
  begin(opened, { keepHistory: true, view: "rows", filed: toTsv(exportGrid(opened)) });
  toast(t("shOpened", name, wordCount()), "ok");
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

$("#title").addEventListener("input", (e) => {
  markRun("title");
  sheet.title = e.target.value;
  saveSoon();
});

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
    if (ui.col === -1) sheet.marker = e.target.value;
    else sheet.columns[ui.col].cell = e.target.value;
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
  else if (kind === "id") sheet.rows[Number(el.dataset.row)].id = el.value;
  else sheet.rows[Number(el.dataset.row)].values[Number(el.dataset.col)] = el.value;
  if (el.tagName === "TEXTAREA") grow(el);
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
  sheet = { title: "", marker: "#config", columns: [], rows: [] };
  steps.past.length = steps.future.length = 0;
  setStage("empty");
  scrollTo({ top: 0 });
});

$("#todeck").addEventListener("click", toDeck);
$("#savecsv").addEventListener("click", saveCsv);
$("#savemore").addEventListener("click", () => {
  if (!wordCount()) return toast(t("shNeedWord"), "bad");
  $("#savebox").showModal();
});
$("#rail-deck").addEventListener("click", toDeck);
$("#save-csv").addEventListener("click", saveCsv);
$("#save-xlsx").addEventListener("click", saveXlsx);
$("#share").addEventListener("click", openShare);
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
    await navigator.share({ title: sheet.title || "SheetCards", url: $("#share-url").value });
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
    } else if (e.key === "Tab") {
      e.preventDefault();
      stopEditing();
      select(r, c + (e.shiftKey ? -1 : 1));
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
      select(r + step[0], c + step[1]);
      reveal(ui.sel.r, ui.sel.c);
    }
    return;
  }
  if (e.key === "Tab") {
    e.preventDefault();
    return select(r, c + (e.shiftKey ? -1 : 1));
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
  if (!ui.sel || ui.editing || !WIDE.matches) return;
  e.preventDefault();
  e.clipboardData.setData("text/plain", selectionTsv());
  toast(t("edCopiedCells"), "ok");
});

document.addEventListener("cut", (e) => {
  if (!ui.sel || ui.editing || !WIDE.matches) return;
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
const bootStatus = () =>
  status(
    [t(bootStep === "boot" ? "booting" : "loadingCode"), bootSlow && t("slowBoot")]
      .filter(Boolean)
      .join("\n"),
    "",
    true,
  );

/** What the address and the saved draft ask for, in that order. */
async function arrive() {
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
    history.replaceState(null, "", location.pathname);
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
        begin(shared);
        toast(t("shOpened", shared.title || fileBase(), wordCount()), "ok");
        return;
      }
    }
  }
  if (draft) {
    begin(draft.sheet, {
      row: draft.row ?? 0,
      col: draft.col ?? 0,
      view: draft.view === "look" ? "look" : "rows",
      filed: typeof draft.filed === "string" ? draft.filed : null,
    });
  }
  else setStage("empty");
}

paintIcons();
paintChrome();

const slowTimer = setTimeout(() => {
  bootSlow = true;
  if (!run) bootStatus();
}, 10_000);

// Started before anything is asked, so a question about a shared link does not
// hold up the ~5 MB download behind it.
const python = startPython(SHEETPY, (step) => {
  bootStep = step;
  if (!run) bootStatus();
})
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
    if ($("#tplbox").open && isMine(stepId)) paintStep();
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
