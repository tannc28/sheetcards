/**
 * Sheet to Anki's "Dán văn bản": a list pasted from Apple Notes, Google Keep,
 * Quizlet's Export → Copy text or anywhere, made into a named deck — or a whole
 * set written the way a note is (a `#config` line on top), or a table copied
 * from Sheets or Excel, a CSV or a Markdown table (an AI assistant's answer,
 * fenced or not).
 *
 * Nothing here reads text: wordlist.js splits a line, importformats.js reads
 * the paste (readPaste, readSheetText), suggests settings for one that has none
 * (suggestSettings / applySettings), writes them back into the reader's own
 * text (withSettings) and builds the sheet (pasteGrid). This is the dialog
 * around them. What it hands the page is a shared-sheet fragment (`#s=…`,
 * sharelink.js), the same thing Create sheet's share link is, so the deck has
 * an address: a reload keeps it, Copy link sends it, and "Sửa sheet" opens it
 * in Create sheet.
 *
 * A paste is edited in the form it came in. A note stays a note — a textarea
 * on ruled paper, its `#config` line and the settings in brackets tinted on a
 * layer behind the text, so typing, a Telex or kana input method and paste are
 * the browser's own. A table stays a table — a small grid with its letters, its
 * row numbers, the column names in row 1 and the settings row in row 2. The
 * settings under both are written into whichever it is: the `#config` line and
 * the brackets of a note, row 2 of a table. "Ghi chú / Bảng" turns one into the
 * other; the keys are the same.
 *
 * Beside it (after it, on a phone) is the real card: drawn by the page's own
 * Python and framed the way the review below draws it, so what is checked here
 * is what the download will hold. Typing never moves what is typed into:
 * everything redrawn while it changes sits beside it or under it, and the card
 * waits for a pause.
 */

import { clozeOrdinals, escapeHtml, renderCard } from "./anki.js";
import { lang, t } from "./i18n.js";
import { icon } from "./icons.js";
import { site } from "./paths.js";
import { SEPARATORS } from "./wordlist.js";
import { deckKey, markerGet, markerSet } from "./identity.js";
import { warningText } from "./sheetwarnings.js";
import { cardDoc, cardFrame } from "./cardframe.js";
import { THEME_SWATCHES } from "./theme-swatches.js";
import {
  SPOKEN,
  THEMES,
  applySettings,
  cleanName,
  detectRowSeparator,
  namedDeck,
  namedSheet,
  pasteGrid,
  readPaste,
  readSheetText,
  splitDeck,
  suggestSettings,
  withSettings,
} from "./importformats.js";
import { encodeShare, shareAddress, toTsv } from "./sharelink.js";

// The last name used, so pasting the longer list next week lands in the same deck.
const NAME_KEY = "sc-paste-name";
// The panel's last choices for each set, by its name: re-pasting the list
// without its #config line starts from them rather than from a guess.
const CHOICES_KEY = "sc-paste-settings";
// A pause in typing long enough to be one: redrawing on every key is what
// made the dialog jump under the caret.
const SETTLE = 250;
// Two columns from here, as the review below; one step at a time under it.
const WIDE = matchMedia("(min-width: 60rem)");
const STILL = matchMedia("(prefers-reduced-motion: reduce)");
// What in a card is a control of its own rather than a place to tap to turn it.
const INTERACTIVE =
  "a, button, input, textarea, select, label, audio, video, iframe, details, " +
  "summary, [onclick], [data-tts], .sc-draw, .sc-reveal";
const MARKER = /^#config(\s|$|[^a-z0-9])/i;
const ID = /^﻿?id$/i;
// Columns of a sheet that are never on a card, so have no side to choose.
const RESERVED = /^(id|sync|tags|subdeck\s*\d+)$/i;

let page = null;
let box = null;
let saveBox = null;
const state = {
  // "note" (a textarea) or "table" (the grid in `grid`).
  form: "note",
  grid: null,
  separator: "auto",
  rows: "auto",
  header: "auto",
  // The duplicates are left out unless the reader asks for them back.
  dupes: false,
  parsed: null,
  suggestion: null,
  choices: null,
  reused: false,
  splitShown: false,
  // The cards as drawn: the Python's answer for the sheet last sent, the cards
  // it makes, which one is showing and whether its answer is.
  tsv: "",
  deck: null,
  cards: [],
  at: 0,
  answered: false,
  doc: "",
};

const $in = (sel) => box.querySelector(sel);
const dark = () => document.documentElement.dataset.theme === "dark";
const letter = (i) => (i >= 26 ? letter(Math.floor(i / 26) - 1) : "") + String.fromCharCode(65 + (i % 26));
const chunks = (cell) =>
  String(cell ?? "")
    .split(";")
    .map((c) => c.trim())
    .filter(Boolean);

function stored(key, fallback) {
  try {
    return JSON.parse(localStorage.getItem(key)) ?? fallback;
  } catch {
    return fallback;
  }
}

function store(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // A private window: a convenience, nothing depends on it.
  }
}

function remembered() {
  try {
    return localStorage.getItem(NAME_KEY) || "";
  } catch {
    return "";
  }
}

function remember(name) {
  try {
    localStorage.setItem(NAME_KEY, name);
  } catch {
    // A private window: the name is only a convenience.
  }
}

/** Sets markup only when it changed, so an open select keeps its focus. */
const written = new WeakMap();
function setHtml(el, html) {
  if (written.get(el) === html) return;
  el.innerHTML = html;
  written.set(el, html);
}

const sideLabel = { front: "txSideFront", back: "txSideBack", hide: "txSideHide" };

/** The docs section on writing a whole set as text, in the reader's language. */
const syntaxDoc = () =>
  site(lang() === "en" ? "docs/en/import/#write-a-whole-set-as-text" : "docs/import/#viet-ca-bo-bang-chu");

function build() {
  box = document.createElement("dialog");
  box.id = "textbox";
  box.className = "donebox txbox";
  box.dataset.step = "text";
  box.dataset.form = "note";
  box.setAttribute("aria-labelledby", "tx-title");
  box.innerHTML = `
    <div class="tx-top">
      <button class="iconbtn tx-back" id="tx-back" type="button" title="${escapeHtml(t("txBackToText"))}"
              aria-label="${escapeHtml(t("txBackToText"))}">${icon("arrow-left")}</button>
      <strong id="tx-title">${escapeHtml(t("txTitle"))}</strong>
      <div class="tx-forms" role="group" aria-label="${escapeHtml(t("txFormLabel"))}">
        <button type="button" data-form="note" aria-pressed="true">${icon("notebook-pen")}<span>${escapeHtml(t("txFormNote"))}</span></button>
        <button type="button" data-form="table" aria-pressed="false">${icon("sheet")}<span>${escapeHtml(t("txFormTable"))}</span></button>
      </div>
      <button class="iconbtn" data-close type="button" title="${escapeHtml(t("close"))}" aria-label="${escapeHtml(t("close"))}">${icon("x")}</button>
    </div>
    <div class="tx-body">
      <section class="tx-write">
        <div class="tx-name">
          <label class="tx-label" for="tx-name">${escapeHtml(t("txName"))}</label>
          <input id="tx-name" type="text" maxlength="100" autocomplete="off" required
                 placeholder="${escapeHtml(t("txNamePlaceholder"))}" aria-describedby="tx-name-error">
          <span id="tx-name-error" class="field-error" hidden>${icon("circle-alert")}<span>${escapeHtml(t("txNameEmpty"))}</span></span>
        </div>
        <p class="tx-lead" id="tx-lead"><span id="tx-lead-text"></span>
          <a href="${escapeHtml(syntaxDoc())}" target="_blank" rel="noopener">${escapeHtml(t("txSyntaxLink"))}</a></p>
        <div class="tx-area" id="tx-area">
          <div class="tx-paper" id="tx-paper" aria-hidden="true"></div>
          <textarea id="tx-text" spellcheck="false" autocapitalize="off" autocomplete="off"
                    placeholder="${escapeHtml(t("txPlaceholder"))}" aria-labelledby="tx-lead-text"></textarea>
          <button class="toolbtn tx-pastebtn" id="tx-paste" type="button" hidden>${icon("clipboard")}<span>${escapeHtml(t("wlPasteBtn"))}</span></button>
        </div>
        <div class="tx-table" id="tx-table" hidden>
          <div class="tx-gridwrap" id="tx-gridwrap"></div>
          <button class="tx-quiet tx-addrow" id="tx-addrow" type="button">${icon("plus")}<span>${escapeHtml(t("txAddRow"))}</span></button>
        </div>
        <div class="tx-notes">
          <p class="tx-note" id="tx-head" hidden><span id="tx-head-text"></span>
            <button class="tx-link" id="tx-head-flip" type="button"></button></p>
          <ul class="tx-warn" id="tx-warn" hidden></ul>
          <details class="tx-split" id="tx-split">
            <summary>${escapeHtml(t("txSplit"))}${icon("chevron-down", "caret")}</summary>
            <div class="tx-splitrow">
              <label><span>${escapeHtml(t("txSides"))}</span><select id="tx-sep"></select></label>
              <label><span>${escapeHtml(t("txRows"))}</span><select id="tx-rows"></select></label>
            </div>
          </details>
        </div>
      </section>
      <section class="tx-look" aria-label="${escapeHtml(t("cardFrameTitle"))}">
        <p class="tx-meta" id="tx-meta" aria-live="polite"></p>
        <div class="deckstack tx-stack" id="tx-stack">
          <div class="cardslot tx-slot" id="tx-card"></div>
        </div>
        <div class="reviewbar tx-review">
          <button class="navbtn" id="tx-prev" type="button" title="${escapeHtml(t("prevRow"))}" aria-label="${escapeHtml(t("prevRow"))}">${icon("arrow-left")}</button>
          <button class="btn flipbtn" id="tx-flip" type="button">${escapeHtml(t("showAnswer"))}</button>
          <button class="navbtn" id="tx-next" type="button" title="${escapeHtml(t("nextRow"))}" aria-label="${escapeHtml(t("nextRow"))}">${icon("arrow-right")}</button>
        </div>
        <p class="tx-counter" id="tx-counter"></p>
        <ul class="tx-warn" id="tx-cardwarn" hidden></ul>
      </section>
      <section class="tx-set" id="tx-set" hidden aria-label="${escapeHtml(t("txSettings"))}">
        <div class="tx-field">
          <label class="tx-label" for="tx-tts">${icon("volume-2")}<span>${escapeHtml(t("txSpeak"))}</span></label>
          <select id="tx-tts"></select>
          <label class="tx-check" id="tx-ex-wrap" hidden><input type="checkbox" id="tx-ex"><span>${escapeHtml(t("txSpeakExample"))}</span></label>
        </div>
        <div class="tx-field">
          <span class="tx-label" id="tx-theme-label">${escapeHtml(t("txTheme"))}</span>
          <div class="tx-swatches" id="tx-themes" role="group" aria-labelledby="tx-theme-label"></div>
          <span class="tx-themename" id="tx-themename"></span>
        </div>
        <details class="tx-cols" id="tx-roles-wrap" hidden>
          <summary class="tx-pill">${icon("sliders-horizontal")}<span>${escapeHtml(t("txCols"))}</span>${icon("chevron-down", "caret")}</summary>
          <div class="tx-pop">
            <p class="tx-label">${escapeHtml(t("txRoles"))}</p>
            <div class="tx-roles" id="tx-roles"></div>
          </div>
        </details>
        <p class="tx-reused" id="tx-reused" hidden>${icon("history")}<span>${escapeHtml(t("txReused"))}</span></p>
      </section>
    </div>
    <div class="tx-foot">
      <div class="tx-aux">
        <button class="tx-quiet" id="tx-save" type="button" disabled title="${escapeHtml(t("txOutHint"))}">${icon("copy")}<span id="tx-save-text"></span></button>
        <button class="tx-quiet" id="tx-edit" type="button" disabled>${icon("pen-line")}<span>${escapeHtml(t("txEdit"))}</span></button>
        <span class="tx-copied" id="tx-copied" aria-live="polite"></span>
      </div>
      <button class="btn tx-see" id="tx-see" type="button" disabled><span id="tx-see-text"></span>${icon("arrow-right")}</button>
      <button class="btn tx-go" id="tx-go" type="button" disabled><span>${escapeHtml(t("go"))}</span>${icon("arrow-right")}</button>
    </div>`;
  document.body.append(box);
  buildSaveBox();

  box.querySelector("[data-close]").addEventListener("click", () => box.close());
  box.addEventListener("click", (e) => {
    if (e.target === box) box.close();
    // The columns' popover closes on a click anywhere else, as a menu does.
    const cols = $in("#tx-roles-wrap");
    if (cols.open && !e.target.closest("#tx-roles-wrap")) cols.open = false;
  });
  box.addEventListener("keydown", keys);

  // ---- the note
  const text = $in("#tx-text");
  let timer = 0;
  text.addEventListener("input", () => {
    paintPasteButton();
    paintPaper();
    clearTimeout(timer);
    timer = setTimeout(refresh, SETTLE);
  });
  text.addEventListener("scroll", () => ($in("#tx-paper").scrollTop = text.scrollTop));
  // A table pasted into an empty note is a table: it opens as one.
  text.addEventListener("paste", (e) => {
    if (text.value.trim()) return;
    const pasted = e.clipboardData?.getData("text/plain") || "";
    if (!tableFrom(pasted)) return;
    e.preventDefault();
    load(pasted);
  });
  new ResizeObserver(() => paintPaper()).observe(text);
  if (navigator.clipboard?.readText) {
    $in("#tx-paste").addEventListener("click", async () => {
      try {
        load(await navigator.clipboard.readText());
      } catch {
        text.focus();
      }
    });
  }

  // ---- the table
  const wrap = $in("#tx-gridwrap");
  let cellTimer = 0;
  wrap.addEventListener("input", (e) => {
    const { r, c } = e.target.dataset;
    if (r === undefined) return;
    state.grid[Number(r)][Number(c)] = e.target.value;
    clearTimeout(cellTimer);
    cellTimer = setTimeout(() => {
      // The name lives in the marker cell; written there, it is the set's name.
      if (Number(r) === 1) {
        const name = markerGet(state.grid[1][gridKey(state.grid)] || "", "name");
        if (name && document.activeElement !== $in("#tx-name")) $in("#tx-name").value = name;
      }
      paint();
    }, SETTLE);
  });
  wrap.addEventListener("keydown", gridKeys);
  $in("#tx-addrow").addEventListener("click", () => {
    addRow();
    focusCell(state.grid.length - 1, 0);
  });

  // ---- the name, the forms, the reading
  let nameTimer = 0;
  $in("#tx-name").addEventListener("input", () => {
    $in("#tx-name-error").hidden = true;
    $in("#tx-name").removeAttribute("aria-invalid");
    clearTimeout(nameTimer);
    nameTimer = setTimeout(nameChanged, SETTLE);
  });
  $in(".tx-forms").addEventListener("click", (e) => {
    const b = e.target.closest("[data-form]");
    if (b && b.dataset.form !== state.form) switchForm(b.dataset.form);
  });
  $in("#tx-sep").addEventListener("change", (e) => {
    state.separator = e.target.value;
    refresh();
  });
  $in("#tx-rows").addEventListener("change", (e) => {
    state.rows = e.target.value;
    refresh();
  });
  $in("#tx-head-flip").addEventListener("click", () => {
    state.header = state.parsed?.header ? false : true;
    state.choices = null;
    refresh();
  });
  $in("#tx-meta").addEventListener("click", (e) => {
    if (!e.target.closest("#tx-dupes")) return;
    state.dupes = !state.dupes;
    paint();
  });

  // ---- the settings
  $in("#tx-tts").addEventListener("change", (e) => choose({ tts: e.target.value }));
  $in("#tx-ex").addEventListener("change", (e) => choose({ example: e.target.checked }));
  $in("#tx-themes").addEventListener("click", (e) => {
    const chip = e.target.closest("[data-theme]");
    if (chip) choose({ theme: chip.dataset.theme });
  });
  $in("#tx-roles").addEventListener("change", (e) => {
    const at = e.target.dataset?.col;
    if (at === undefined) return;
    const sides = [...currentChoices().sides];
    sides[Number(at)] = e.target.value;
    choose({ sides });
  });

  // ---- the card and the way out
  $in("#tx-prev").addEventListener("click", () => step(-1));
  $in("#tx-next").addEventListener("click", () => step(1));
  $in("#tx-flip").addEventListener("click", flip);
  $in("#tx-see").addEventListener("click", () => setStep("card"));
  $in("#tx-back").addEventListener("click", () => setStep("text"));
  $in("#tx-save").addEventListener("click", copyOut);
  $in("#tx-go").addEventListener("click", () => finish(false));
  $in("#tx-edit").addEventListener("click", () => finish(true));
  // The card is the size of the room it is given; a new size is a new layout.
  WIDE.addEventListener("change", () => box.open && drawCard(true));
}

/** Where the copy goes when the clipboard refuses it: selected, to copy by hand. */
function buildSaveBox() {
  saveBox = document.createElement("dialog");
  saveBox.id = "tx-savebox";
  saveBox.className = "donebox tx-savebox";
  saveBox.setAttribute("aria-labelledby", "tx-save-title");
  saveBox.innerHTML = `
    <div class="tx-top">
      <strong id="tx-save-title"></strong>
      <button class="iconbtn" data-close type="button" title="${escapeHtml(t("close"))}" aria-label="${escapeHtml(t("close"))}">${icon("x")}</button>
    </div>
    <div class="tx-savebody">
      <p class="tx-savehint">${escapeHtml(t("txCopyFailed"))}</p>
      <pre class="tx-outtext" id="tx-outtext" tabindex="0"></pre>
    </div>`;
  document.body.append(saveBox);
  saveBox.querySelector("[data-close]").addEventListener("click", () => saveBox.close());
  saveBox.addEventListener("click", (e) => {
    if (e.target === saveBox) saveBox.close();
  });
}

function paintPasteButton() {
  $in("#tx-paste").hidden = !navigator.clipboard?.readText || Boolean($in("#tx-text").value);
}

/** Text or cards: the phone's two steps. A wide screen shows both at once. */
function setStep(name) {
  box.dataset.step = name;
  if (name === "card") {
    document.activeElement?.blur?.();
    drawCard(true);
    $in("#tx-flip").focus({ preventScroll: true });
  }
  $in(".tx-body").scrollTop = 0;
}

// ---------------------------------------------------------------------------
// The note: a textarea over a layer that tints its settings
// ---------------------------------------------------------------------------

/**
 * The layer behind the text: the same lines, wrapped the same way, with the
 * `#config` line and the header's brackets tinted. The text itself is the
 * textarea's, drawn on top, so nothing here can get between a key and the
 * letter it types.
 */
function paintPaper() {
  if (state.form !== "note") return;
  const text = $in("#tx-text");
  const paper = $in("#tx-paper");
  const lines = text.value.split("\n");
  const head = headerLine(lines);
  paper.innerHTML = lines
    .map((line, i) => {
      const body = escapeHtml(line) || "​";
      if (MARKER.test(line.trim())) {
        return `<div class="ln cfg">${body.replace(/(#config)/i, '<span class="kw">$1</span>')}</div>`;
      }
      if (i === head) return `<div class="ln head">${body.replace(/(\[[^\]\n]*\])/g, '<span class="br">$1</span>')}</div>`;
      return `<div class="ln">${body}</div>`;
    })
    .join("");
  // The text's own width, scrollbar left out, so a line wraps where it does.
  // Its border is the textarea's, so the inner widths agree.
  paper.style.width = `${text.clientWidth + 3}px`;
  paper.style.height = `${text.offsetHeight}px`;
  paper.scrollTop = text.scrollTop;
}

/** Which line names the columns: beside the #config line, or carrying brackets. */
function headerLine(lines) {
  const filled = lines.map((l, i) => [l, i]).filter(([l]) => l.trim());
  const [a, b] = filled;
  if (a && MARKER.test(a[0].trim())) return b ? b[1] : -1;
  if (b && MARKER.test(b[0].trim())) return a[1];
  if (a && /\S\s*\[[^\]\n]*\]/.test(a[0]) && state.parsed?.brackets) return a[1];
  return -1;
}

/** Replaces the note's text as one edit, keeping where it was scrolled to. */
function setText(value) {
  const text = $in("#tx-text");
  const top = text.scrollTop;
  text.value = value;
  text.scrollTop = top;
  paintPasteButton();
  paintPaper();
}

// ---------------------------------------------------------------------------
// The table: a grid of cells, row 1 the names, row 2 the settings
// ---------------------------------------------------------------------------

const gridKey = (grid) => Math.max(0, grid[0].findIndex((h) => ID.test(String(h).trim())));
const gridWidth = (grid) => Math.max(2, ...grid.map((r) => r.length));

/** The table read the way readPaste reads a note: names, settings, cards. */
function gridModel(grid) {
  const width = gridWidth(grid);
  const header = Array.from({ length: width }, (_, i) => String(grid[0][i] ?? "").trim());
  const keyAt = gridKey(grid);
  const mark = splitDeck(grid[1]?.[keyAt] || "");
  const cells = header.map((_, i) => (i === keyAt ? mark.own : chunks(grid[1]?.[i])).join("; "));
  const rows = grid.slice(2).map((r) => header.map((_, i) => String(r[i] ?? "")));
  return { rows, header, cells, deck: mark.deck, config: true, brackets: false, marks: [], warnings: [], keyAt, table: true };
}

/** A table with a settings row under its names, added when it had none. */
function withConfigRow(rows) {
  const grid = rows.map((r) => [...r]);
  const width = gridWidth(grid);
  for (const r of grid) while (r.length < width) r.push("");
  if (!(grid[1] || []).some((c) => MARKER.test(String(c).trim()))) {
    const row = Array(width).fill("");
    row[gridKey(grid)] = "#config";
    grid.splice(1, 0, row);
  }
  return grid;
}

/**
 * The table a paste is, or null when it is a note: a whole sheet (an ID
 * column, or a settings row under the names), a Markdown table, or cells
 * between tabs as Sheets and Excel copy them — with names, or three columns
 * and more. Two columns between tabs and no names is Quizlet's export, a list.
 */
function tableFrom(text) {
  const sheet = readSheetText(text);
  if (sheet) return { grid: withConfigRow(sheet.rows), name: sheet.name };
  const parsed = readPaste(text);
  const width = Math.max(0, ...parsed.rows.map((r) => r.length));
  if (!parsed.rows.length || !(parsed.table || (parsed.separator === "tab" && (parsed.header || width >= 3)))) return null;
  return { parsed };
}

function paintGrid() {
  const grid = state.grid;
  const width = gridWidth(grid);
  const head = `<tr><th class="corner"></th>${Array.from({ length: width }, (_, i) => `<th>${letter(i)}</th>`).join("")}</tr>`;
  const body = grid
    .map((row, r) => {
      const cls = r === 0 ? "names" : r === 1 ? "settings" : "";
      const cells = Array.from({ length: width }, (_, c) => {
        const value = String(row[c] ?? "");
        const label = `${letter(c)}${r + 1}`;
        return `<td><input data-r="${r}" data-c="${c}" value="${escapeHtml(value)}" aria-label="${label}"
          spellcheck="false" autocomplete="off"></td>`;
      }).join("");
      return `<tr class="${cls}"><th>${r + 1}</th>${cells}</tr>`;
    })
    .join("");
  $in("#tx-gridwrap").innerHTML = `<table class="tx-grid">${head}${body}</table>`;
}

/** Row 2 written again, into the cells already on screen. */
function paintSettingsRow() {
  for (const input of $in("#tx-gridwrap").querySelectorAll('input[data-r="1"]')) {
    const value = String(state.grid[1][Number(input.dataset.c)] ?? "");
    if (input.value !== value) input.value = value;
  }
}

function addRow() {
  state.grid.push(Array(gridWidth(state.grid)).fill(""));
  paintGrid();
}

function focusCell(r, c) {
  const input = $in(`#tx-gridwrap input[data-r="${r}"][data-c="${c}"]`);
  if (!input) return;
  input.focus();
  input.select();
}

/** Enter goes down a row (adding one at the bottom), Shift+Enter up, as in Sheets. */
function gridKeys(e) {
  const { r, c } = e.target.dataset;
  if (r === undefined || e.isComposing) return;
  const row = Number(r);
  const down = (e.key === "Enter" && !e.shiftKey) || e.key === "ArrowDown";
  const up = (e.key === "Enter" && e.shiftKey) || e.key === "ArrowUp";
  if (!down && !up) return;
  e.preventDefault();
  e.stopPropagation();
  if (down && row === state.grid.length - 1) {
    if (e.key !== "Enter") return;
    addRow();
  }
  focusCell(Math.max(0, row + (down ? 1 : -1)), Number(c));
}

// ---------------------------------------------------------------------------
// Reading what is there
// ---------------------------------------------------------------------------

const sepLabel = (id) =>
  id === "none" ? t("wlSepNone") : id === "tab" ? "Tab" : SEPARATORS.find((s) => s.id === id)?.label.trim() || id;
const rowLabel = (sep) => (sep.id === "token" ? `“${sep.token}”` : t("txRowsNewline"));

function options(detectedSep, detectedRows, text) {
  const seps = [`<option value="auto">${escapeHtml(t("wlSepAuto", sepLabel(detectedSep)))}</option>`];
  for (const s of SEPARATORS) seps.push(`<option value="${s.id}">${escapeHtml(sepLabel(s.id))}</option>`);
  seps.push(`<option value="none">${escapeHtml(t("wlSepNone"))}</option>`);
  setHtml($in("#tx-sep"), seps.join(""));
  $in("#tx-sep").value = state.separator;

  // The row choice: newline, ";", and whatever mark this paste repeats.
  const found = detectRowSeparator(text);
  const tokens = new Set([";"]);
  if (found.id === "token") tokens.add(found.token);
  if (state.rows !== "auto" && state.rows !== "newline") tokens.add(state.rows);
  const rows = [`<option value="auto">${escapeHtml(t("wlSepAuto", rowLabel(detectedRows)))}</option>`];
  rows.push(`<option value="newline">${escapeHtml(t("txRowsNewline"))}</option>`);
  for (const tok of tokens) rows.push(`<option value="${escapeHtml(tok)}">${escapeHtml(`“${tok}”`)}</option>`);
  setHtml($in("#tx-rows"), rows.join(""));
  $in("#tx-rows").value = state.rows;
}

const included = (parsed, i) => state.dupes || !parsed.marks[i];

/** The note read again; the table needs no reading. */
function refresh() {
  if (state.form === "table") return paint();
  const text = $in("#tx-text").value;
  state.parsed = readPaste(text, { rows: state.rows, separator: state.separator, header: state.header });
  const named = state.parsed.deck.find((c) => /^name\s*=/i.test(c));
  if (named && document.activeElement !== $in("#tx-name")) {
    $in("#tx-name").value = cleanName(named.split("=").slice(1).join("="));
  }
  const auto = readPaste(text, { rows: state.rows, header: state.header });
  options(auto.separator, state.parsed.rowSeparator, text);
  paintPaper();
  paint();
}

/** What the settings are drawn from: the note's reading, or the table's. */
const model = () => (state.form === "table" ? gridModel(state.grid) : state.parsed);

function chosenRows() {
  const parsed = state.parsed;
  return parsed.rows.filter((_, i) => included(parsed, i));
}

const currentName = () => cleanName($in("#tx-name").value);

/**
 * The panel's choices. Settings written in the note or the table are read back
 * from it; a list that says nothing starts from this set's last choices, else
 * from a guess, until a choice is made — which is written into the list.
 */
function currentChoices() {
  const suggestion = (state.suggestion = suggestSettings(model(), { language: lang() }));
  if (state.form === "table") {
    suggestion.content = suggestion.content.filter((i) => !RESERVED.test(suggestion.names[i]));
  }
  state.reused = false;
  if (suggestion.given) return suggestion.choices;
  const guess = suggestion.choices;
  if (state.choices && state.choices.sides?.length === guess.sides.length) return state.choices;
  let choices = { ...guess, sides: [...guess.sides] };
  const last = stored(CHOICES_KEY, {})[deckKey(currentName())];
  if (last) {
    choices = {
      ...choices,
      tts: last.tts ?? choices.tts,
      example: Boolean(last.example),
      theme: last.theme ?? choices.theme,
      sides: suggestion.names.map((n, i) => last.sides?.[n] ?? choices.sides[i]),
    };
    state.reused = true;
  }
  return (state.choices = choices);
}

/** Each column's settings and the deck's keys, as the cards are made from them. */
function settings() {
  const m = model();
  const choices = currentChoices();
  if (state.suggestion.given) return { choices, cells: m.cells, deck: m.deck };
  return { choices, ...applySettings(state.suggestion, choices, m.deck) };
}

/** A choice made under the cards, written into the note or the table. */
function choose(change) {
  const choices = { ...currentChoices(), ...change };
  const made = applySettings(state.suggestion, choices, model().deck);
  if (state.form === "table") {
    state.grid[1] = settingsRow(made, state.grid);
    paintSettingsRow();
    return paint();
  }
  const parsed = state.parsed;
  setText(
    withSettings($in("#tx-text").value, parsed, {
      name: currentName(),
      names: state.suggestion.names,
      cells: made.cells,
      deck: made.deck,
    }),
  );
  state.choices = null;
  refresh();
}

/** Row 2 of a table for these settings: the marker and the deck's keys in the key column. */
function settingsRow({ cells, deck }, grid, name = currentName()) {
  const width = gridWidth(grid);
  const keyAt = gridKey(grid);
  const row = Array.from({ length: width }, (_, i) => (i === keyAt ? "" : String(cells[i] ?? "")));
  const own = name ? namedDeck(deck, name) : deck;
  row[keyAt] = `#config ${[...own, ...chunks(cells[keyAt])].join("; ")}`.trim();
  return row;
}

/** The name typed is the set's name, in the note's #config line or the table's marker. */
function nameChanged() {
  const name = currentName();
  if (name && state.form === "table") {
    const keyAt = gridKey(state.grid);
    state.grid[1][keyAt] = markerSet(state.grid[1][keyAt], "name", name);
    paintSettingsRow();
  } else if (name && state.parsed?.config) {
    const m = state.parsed;
    setText(withSettings($in("#tx-text").value, m, { name, cells: m.cells, deck: m.deck }));
    return refresh();
  }
  // Another set's name: its own last choices.
  state.choices = null;
  paint();
}

// ---------------------------------------------------------------------------
// Painting
// ---------------------------------------------------------------------------

/** The line over the card: how many, and what was left out. */
function paintMeta(count, { dupes = 0, oneSided = 0 } = {}) {
  const parts = [`<strong>${escapeHtml(t("txCount", count))}</strong>`];
  if (dupes) {
    parts.push(
      `<button class="tx-chipbtn${state.dupes ? " on" : ""}" id="tx-dupes" type="button" aria-pressed="${state.dupes}">${escapeHtml(
        t(state.dupes ? "txDupesIn" : "txDupesOut", dupes),
      )}</button>`,
    );
  }
  if (oneSided) parts.push(`<span class="tx-dim">${escapeHtml(t("txOneSided", oneSided))}</span>`);
  setHtml($in("#tx-meta"), parts.join(""));
  $in("#tx-see-text").textContent = t("txSeeCards", count);
}

function enable(on) {
  for (const id of ["#tx-go", "#tx-edit", "#tx-see", "#tx-save"]) $in(id).disabled = !on;
}

/** Which form is on screen, and the words that go with it. */
function paintForm() {
  const table = state.form === "table";
  box.dataset.form = state.form;
  $in("#tx-area").hidden = table;
  $in("#tx-table").hidden = !table;
  $in("#tx-lead-text").innerHTML = t(table ? "txLeadTable" : "txLead");
  $in("#tx-save-text").textContent = t(table ? "txCopyTable" : "txCopyText");
  for (const b of box.querySelectorAll(".tx-forms [data-form]")) b.setAttribute("aria-pressed", String(b.dataset.form === state.form));
}

function paint() {
  const table = state.form === "table";
  const m = model();
  const rows = table ? m.rows.filter((r) => r[m.keyAt]?.trim()) : chosenRows();
  const dupes = table ? 0 : m.marks.filter(Boolean).length;
  const oneSided = table ? 0 : rows.filter((r) => r.length < 2 || !r[1]).length;
  paintMeta(state.deck && state.tsv ? state.cards.length : rows.length, { dupes, oneSided });
  enable(rows.length > 0);

  // The note's own questions: how it is split, and whether line 1 is names.
  $in("#tx-split").hidden = table;
  $in("#tx-head").hidden = true;
  $in("#tx-warn").hidden = true;
  if (!table) {
    // The separators are a question only when the answer looks wrong: some
    // lines split and some not, or a choice already made. Opened once, never
    // shut on the reader.
    const mixed = oneSided > 0 && oneSided < rows.length;
    if ((mixed || state.separator !== "auto" || state.rows !== "auto") && !state.splitShown) {
      $in("#tx-split").open = true;
      state.splitShown = true;
    }
    // The first line read one way when the text did not say which: one tap the
    // other. Said only when the line could be either: one that plainly looks
    // like the cards under it is a card without a word.
    const either = m.header || ["unlike", "alone"].includes(m.headerWhy);
    const unsure = m.separator !== "none" && ((!m.headerSure && either) || state.header !== "auto");
    $in("#tx-head").hidden = !unsure || (!m.header && m.rows.length < 2);
    $in("#tx-head-text").textContent = t(m.header ? "hdKept" : "hdSynth");
    $in("#tx-head-flip").textContent = t(m.header ? "hdUseCard" : "hdUseFirst");
    const warn = $in("#tx-warn");
    setHtml(
      warn,
      m.warnings
        .map((w) => `<li>${icon("triangle-alert")}<span>${escapeHtml(w.key === "txTwice" ? t("txTwice", w.col, w.setting) : t("txExtraCell", w.col))}</span></li>`)
        .join(""),
    );
    warn.hidden = !m.warnings.length;
  }

  $in("#tx-set").hidden = !rows.length;
  if (!rows.length) return paintCards(null);
  const made = settings();
  paintChoices(made.choices);
  paintCards(
    table
      ? state.grid
      : pasteGrid({ name: currentName() || "x", rows, header: m.header, cells: made.cells, deck: made.deck, language: lang() }),
  );
}

/** A theme's chip: its own card colours, the accent as a bar under "Aa". */
function swatch(value, label, colours, chosen) {
  const style = colours ? `--sw-bg:${colours.bg};--sw-fg:${colours.fg};--sw-ac:${colours.accent}` : "";
  return `<button type="button" class="tx-swatch" data-theme="${escapeHtml(value)}"
    aria-pressed="${value === chosen}" title="${escapeHtml(label)}" aria-label="${escapeHtml(label)}" style="${style}"><span aria-hidden="true">Aa</span></button>`;
}

function paintChoices(choices) {
  const s = state.suggestion;
  $in("#tx-reused").hidden = !state.reused;
  const tts = $in("#tx-tts");
  const known = SPOKEN.some(([code]) => code === choices.tts);
  setHtml(
    tts,
    [
      `<option value="">${escapeHtml(t("txSpeakNone"))}</option>`,
      ...SPOKEN.map(([code, label]) => `<option value="${code}">${escapeHtml(label)}</option>`),
      ...(choices.tts && !known ? [`<option value="${escapeHtml(choices.tts)}">${escapeHtml(choices.tts)}</option>`] : []),
    ].join(""),
  );
  tts.value = choices.tts;
  $in("#tx-ex-wrap").hidden = s.example < 0 || !choices.tts;
  $in("#tx-ex").checked = choices.example;

  const mode = dark() ? "night" : "light";
  const listed = new Map(THEME_SWATCHES.map((w) => [w.name, w[mode]]));
  const plain = dark() ? { bg: "#1b1f25", fg: "#e6e9ee", accent: "#7aa7ef" } : { bg: "#ffffff", fg: "#111111", accent: "#2f6fd0" };
  const chips = [swatch("", t("txThemeNone"), plain, choices.theme), ...THEMES.map((name) => swatch(name, name, listed.get(name), choices.theme))];
  if (choices.theme && !THEMES.includes(choices.theme)) chips.push(swatch(choices.theme, choices.theme, null, choices.theme));
  setHtml($in("#tx-themes"), chips.join(""));
  $in("#tx-themename").textContent = choices.theme || t("txThemeNone");

  const many = s.content.length >= 3;
  $in("#tx-roles-wrap").hidden = !many;
  if (many) {
    setHtml(
      $in("#tx-roles"),
      s.content
        .map((i) => {
          const opts = ["front", "back", "hide"]
            .map((side) => `<option value="${side}"${choices.sides[i] === side ? " selected" : ""}>${escapeHtml(t(sideLabel[side]))}</option>`)
            .join("");
          return `<label class="tx-role"><span>${escapeHtml(s.names[i])}</span><select data-col="${i}">${opts}</select></label>`;
        })
        .join(""),
    );
  }
}

// ---------------------------------------------------------------------------
// The cards
// ---------------------------------------------------------------------------

/** Every card the notes make, the way Anki counts them: a template each, a
 *  cloze deletion each. */
function cardsOf(deck) {
  if (!deck) return [];
  const out = [];
  for (const note of deck.notes) {
    if (note.cloze) {
      const ords = [...new Set(Object.values(note.values).flatMap((v) => clozeOrdinals(v)))];
      for (const ordinal of ords.length ? ords : [1]) out.push({ template: deck.templates.cloze[0], values: note.values, ordinal });
    } else {
      for (const template of deck.templates.basic) out.push({ template, values: note.values, ordinal: 1 });
    }
  }
  return out;
}

/** The sheet as it stands, read by the page's own Python into its cards. */
function paintCards(grid) {
  const tsv = grid ? toTsv(grid) : "";
  if (tsv === state.tsv && (state.deck || !tsv)) return drawCard();
  const deck = tsv ? page.previewDeck?.(tsv) : null;
  state.tsv = deck ? tsv : "";
  state.deck = deck;
  state.cards = cardsOf(deck);
  state.at = Math.min(state.at, Math.max(0, state.cards.length - 1));
  if (deck) {
    const m = model();
    const dupes = state.form === "note" ? m.marks.filter(Boolean).length : 0;
    const oneSided = state.form === "note" ? chosenRows().filter((r) => r.length < 2 || !r[1]).length : 0;
    paintMeta(state.cards.length, { dupes, oneSided });
  }
  const warn = $in("#tx-cardwarn");
  setHtml(
    warn,
    (deck?.warningCodes || []).map((w) => `<li>${icon("triangle-alert")}<span>${escapeHtml(warningText(w, lang()))}</span></li>`).join(""),
  );
  warn.hidden = !deck?.warningCodes?.length;
  drawCard(false, Boolean(tsv) && !deck);
}

/** The card showing, drawn only when it is not the one already there. */
function drawCard(force = false, waiting = false) {
  const slot = $in("#tx-card");
  const n = state.cards.length;
  $in("#tx-prev").disabled = $in("#tx-next").disabled = n < 2;
  $in("#tx-flip").disabled = !n;
  $in("#tx-flip").textContent = t(state.answered ? "flipBack" : "showAnswer");
  $in("#tx-flip").classList.toggle("answered", state.answered);
  $in("#tx-counter").textContent = n ? `${state.at + 1} / ${n}` : "";
  $in("#tx-stack").dataset.depth = String(Math.max(0, Math.min(2, n - state.at - 1)));
  if (!n) {
    state.doc = "";
    // Before Python is up the card waits; ready() draws it when it is.
    setHtml(slot, `<div class="tx-empty">${escapeHtml(t(waiting ? "txCardLoading" : "txCardEmpty"))}</div>`);
    return;
  }
  const card = state.cards[state.at];
  const { front, back } = renderCard(card.template, card.values, { ordinal: card.ordinal });
  const doc = cardDoc({ front, back, tab: state.answered ? "both" : "front", dark: dark() });
  if (doc === state.doc && !force && slot.querySelector("iframe")) return;
  state.doc = doc;
  written.delete(slot);
  slot.innerHTML = cardFrame(doc, t("cardFrameTitle"));
  const frame = slot.querySelector("iframe");
  frame.removeAttribute("id");
  frame.addEventListener("load", () => wireFrame(frame), { once: true });
}

function step(by) {
  const n = state.cards.length;
  if (n < 2) return;
  state.at = (state.at + by + n) % n;
  state.answered = false;
  turn(() => drawCard());
}

function flip() {
  if (!state.cards.length) return;
  state.answered = !state.answered;
  turn(() => drawCard());
}

/** The same half-turn the review below makes, skipped under reduced motion. */
function turn(swap) {
  const slot = $in("#tx-card");
  if (STILL.matches) return swap();
  slot.classList.add("turn-out");
  setTimeout(() => {
    swap();
    slot.classList.remove("turn-out");
    slot.classList.add("turn-in");
    requestAnimationFrame(() => requestAnimationFrame(() => slot.classList.remove("turn-in")));
  }, 170);
}

/** ← → and Space step and turn, unless the reader is typing. */
function keys(e) {
  if (e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey) return;
  if (e.target.closest?.("input, textarea, select, [contenteditable]")) return;
  if (!WIDE.matches && box.dataset.step !== "card") return;
  if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
    e.preventDefault();
    step(e.key === "ArrowLeft" ? -1 : 1);
  } else if (e.key === " " && !e.target.closest?.("button, a, summary")) {
    e.preventDefault();
    flip();
  }
}

/** The card itself: a tap turns it, a sideways swipe steps, keys work inside. */
function wireFrame(frame) {
  let doc;
  try {
    doc = frame.contentDocument;
  } catch {
    return;
  }
  if (!doc) return;
  doc.body.style.cursor = "pointer";
  let x0 = 0;
  let y0 = 0;
  let swiped = false;
  doc.addEventListener("click", (e) => {
    if (swiped) {
      swiped = false;
      return;
    }
    if (!e.target.closest(INTERACTIVE)) flip();
  });
  doc.addEventListener("keydown", (e) => {
    if (e.target.closest("input, textarea, select, [contenteditable]")) return;
    keys(e);
  });
  doc.addEventListener(
    "touchstart",
    (e) => {
      x0 = e.touches[0].clientX;
      y0 = e.touches[0].clientY;
    },
    { passive: true },
  );
  doc.addEventListener(
    "touchend",
    (e) => {
      const dx = e.changedTouches[0].clientX - x0;
      const dy = e.changedTouches[0].clientY - y0;
      if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 1.5) {
        swiped = true;
        step(dx < 0 ? 1 : -1);
      }
    },
    { passive: true },
  );
}

// ---------------------------------------------------------------------------
// One form into the other, and out
// ---------------------------------------------------------------------------

/** The note as a table: names, the settings row, the cards — the same keys. */
function noteAsGrid() {
  const made = settings();
  const m = state.parsed;
  const grid = pasteGrid({ name: currentName(), rows: chosenRows(), header: m.header, cells: made.cells, deck: made.deck, language: lang() });
  return withConfigRow(grid);
}

/** The table as a note: `#config` on line 1, names with their brackets, a card a line. */
function gridAsNote(grid, name = currentName()) {
  const m = gridModel(grid);
  const body = m.rows.filter((r) => r.some((c) => c.trim())).map((r) => r.join(" | ")).join("\n");
  return withSettings(body, { ...m, table: false, lines: {} }, { name, names: m.header, cells: m.cells, deck: m.deck });
}

function switchForm(form) {
  if (form === "table") {
    if (!state.parsed?.rows.length) return;
    state.grid = noteAsGrid();
    state.form = "table";
    paintGrid();
  } else {
    const text = gridAsNote(state.grid);
    state.form = "note";
    resetReading();
    setText(text);
  }
  state.choices = null;
  paintForm();
  refresh();
}

function resetReading() {
  Object.assign(state, { separator: "auto", rows: "auto", header: "auto", dupes: false, splitShown: false });
  $in("#tx-split").open = false;
}

/**
 * A paste, opened in its own form: a table as the grid (with suggested
 * settings written into its row 2 when it had none), anything else as a note.
 */
function load(text) {
  resetReading();
  state.choices = null;
  const found = tableFrom(text);
  if (found?.grid) {
    state.form = "table";
    state.grid = found.grid;
    if (found.name) $in("#tx-name").value = found.name;
    const keyAt = gridKey(state.grid);
    const name = markerGet(state.grid[1][keyAt], "name");
    if (!name && currentName()) state.grid[1][keyAt] = markerSet(state.grid[1][keyAt], "name", currentName());
  } else if (found?.parsed) {
    state.form = "note";
    state.parsed = found.parsed;
    state.grid = noteAsGrid();
    state.form = "table";
  } else {
    state.form = "note";
    setText(text);
  }
  if (state.form === "table") {
    $in("#tx-text").value = "";
    paintGrid();
  }
  paintPasteButton();
  paintForm();
  refresh();
}

function nameMissing() {
  const input = $in("#tx-name");
  if (currentName()) return false;
  if (box.dataset.step !== "text") setStep("text");
  $in("#tx-name-error").hidden = false;
  input.setAttribute("aria-invalid", "true");
  input.focus();
  return true;
}

/** The sheet the cards are made from, named: what goes to the page. */
function finalGrid(name) {
  if (state.form === "table") {
    const grid = state.grid.filter((r, i) => i < 2 || r.some((c) => String(c).trim()));
    const keyAt = gridKey(grid);
    grid[1] = [...grid[1]];
    grid[1][keyAt] = markerSet(grid[1][keyAt], "name", name);
    return grid;
  }
  const rows = chosenRows();
  if (!rows.length) return null;
  const made = settings();
  return pasteGrid({ name, rows, header: state.parsed.header, cells: made.cells, deck: made.deck, language: lang() });
}

/** The set in the form it is edited in: the note's text, or the table as TSV for Sheets. */
async function copyOut() {
  if (nameMissing()) return;
  const name = currentName();
  let out;
  if (state.form === "table") out = toTsv(finalGrid(name));
  else {
    const made = settings();
    out = withSettings($in("#tx-text").value, state.parsed, {
      name,
      names: state.suggestion.names,
      cells: made.cells,
      deck: made.deck,
    });
  }
  const said = $in("#tx-copied");
  try {
    await navigator.clipboard.writeText(out);
    said.textContent = t("txCopied");
    clearTimeout(copyOut.timer);
    copyOut.timer = setTimeout(() => (said.textContent = ""), 4000);
  } catch {
    saveBox.querySelector("#tx-save-title").textContent = t(state.form === "table" ? "txCopyTable" : "txCopyText");
    saveBox.querySelector("#tx-outtext").textContent = out;
    saveBox.showModal();
    getSelection()?.selectAllChildren(saveBox.querySelector("#tx-outtext"));
  }
}

function keepChoices(name) {
  if (!state.suggestion) return;
  const choices = currentChoices();
  const all = stored(CHOICES_KEY, {});
  const sides = {};
  state.suggestion.names.forEach((n, i) => (sides[n] = choices.sides[i]));
  all[deckKey(name)] = { tts: choices.tts, example: choices.example, theme: choices.theme, sides };
  store(CHOICES_KEY, all);
}

async function finish(edit) {
  if (nameMissing()) return;
  const name = currentName();
  const grid = finalGrid(name);
  if (!grid) return;
  keepChoices(name);
  remember(name);
  // The grid carries name= and the deck is keyed by it; the link's title is the
  // same name, which is what the page calls the file it makes of it.
  const title = markerGet(grid[1].find((c) => MARKER.test(String(c).trim())) || "", "name") || name;
  const hash = await encodeShare(title, toTsv(grid));
  box.close();
  if (edit) location.assign(shareAddress(hash));
  else page.openShared(hash);
}

/**
 * Wires the dialog to Sheet to Anki. `host.openShared(hash)` opens a `#s=…`
 * sheet the way an address carrying one is opened; `host.previewDeck(tsv)`
 * reads the sheet into its notes and templates ({templates, notes,
 * warningCodes}), or null until Python is up.
 */
export function mountTextImport(host) {
  page = host;
  return {
    open,
    // Python has arrived: the cards that were waiting for it can be drawn.
    ready() {
      if (box?.open) {
        state.tsv = "";
        paint();
      }
    },
  };
}

/**
 * Opens the dialog. `text`, when given, is what was pasted into the page's main
 * field (or the landing page's), opened in its own form.
 */
export function open(text) {
  if (!box) build();
  Object.assign(state, { at: 0, answered: false, tsv: "", doc: "", deck: null, cards: [] });
  box.dataset.step = "text";
  const input = $in("#tx-name");
  if (!input.value) input.value = remembered();
  $in("#tx-name-error").hidden = true;
  if (typeof text === "string" && text.trim()) load(text);
  else if (state.form === "table") {
    paintForm();
    refresh();
  } else load($in("#tx-text").value);
  box.showModal();
  paintPaper();
  if (!input.value) input.focus();
  else if (state.form === "table") focusCell(Math.min(2, state.grid.length - 1), 0);
  else $in("#tx-text").focus();
}
