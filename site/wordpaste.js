/**
 * Create sheet's "Dán danh sách từ": a list pasted from anywhere, previewed as
 * the sheet's own rows, added in one go.
 *
 * The reading of the list is site/wordlist.js's; this is only the dialog. The
 * page hands it an `editor` (see mountWordPaste) rather than this module
 * reaching into the sheet, so the sheet stays sheet.js's.
 */

import { escapeHtml } from "./anki.js";
import { t } from "./i18n.js";
import { icon } from "./icons.js";
import { SEPARATORS, columnRoles, guessMapping, listLanguage, loadReader, parseList, placeRow } from "./wordlist.js";
import { coverage } from "./suggest.js";

const PREVIEW_ROWS = 200;

let editor = null;
let box = null;
const state = { separator: "auto", mapping: [], include: new Map(), readings: new Map(), fill: true, parsed: null, wanted: null };

const $in = (sel) => box.querySelector(sel);

function build() {
  box = document.createElement("dialog");
  box.id = "pastebox";
  box.className = "donebox pickbox wtbox";
  box.setAttribute("aria-labelledby", "wl-title");
  box.innerHTML = `
    <div class="done-head">
      <strong id="wl-title">${escapeHtml(t("wlTitle"))}</strong>
      <button class="iconbtn" data-close type="button" title="${escapeHtml(t("close"))}" aria-label="${escapeHtml(t("close"))}">${icon("x")}</button>
    </div>
    <div class="wt-body">
      <p class="small muted wt-lead">${t("wlLead")}</p>
      <div class="wt-area">
        <textarea id="wl-text" rows="7" spellcheck="false" autocapitalize="off" autocomplete="off"
                  placeholder="${escapeHtml(t("wlPlaceholder"))}" aria-label="${escapeHtml(t("wlTitle"))}"></textarea>
        <button class="toolbtn wt-pastebtn" id="wl-paste" type="button" hidden>${icon("clipboard")}<span>${escapeHtml(t("wlPasteBtn"))}</span></button>
      </div>
      <div class="wt-opts">
        <label class="wt-sep"><span>${escapeHtml(t("wlSeparator"))}</span><select id="wl-sep"></select></label>
        <div class="wt-map" id="wl-map"></div>
        <label class="wt-check" id="wl-fillrow" hidden><input type="checkbox" id="wl-fill" checked><span id="wl-filltext"></span></label>
        <p class="small muted" id="wl-langnote" hidden></p>
      </div>
      <p class="wt-sum" id="wl-sum" aria-live="polite"></p>
      <div class="wt-preview" id="wl-preview"></div>
    </div>
    <div class="wt-foot">
      <button class="toolbtn" id="wl-suggest" type="button" hidden>${icon("sparkles")}<span id="wl-suggest-text"></span></button>
      <button class="btn" id="wl-add" type="button" disabled>${icon("plus")}<span id="wl-add-text"></span></button>
    </div>`;
  document.body.append(box);
  box.querySelector("[data-close]").addEventListener("click", () => box.close());
  box.addEventListener("click", (e) => {
    if (e.target === box) box.close();
  });
  const text = $in("#wl-text");
  let timer = 0;
  text.addEventListener("input", () => {
    paintPasteButton();
    clearTimeout(timer);
    timer = setTimeout(() => {
      state.mapping = [];
      state.include.clear();
      refresh();
    }, 120);
  });
  if (navigator.clipboard?.readText) {
    $in("#wl-paste").addEventListener("click", async () => {
      try {
        text.value = await navigator.clipboard.readText();
        paintPasteButton();
        state.mapping = [];
        state.include.clear();
        refresh();
      } catch {
        text.focus();
      }
    });
  }
  $in("#wl-sep").addEventListener("change", (e) => {
    state.separator = e.target.value;
    state.mapping = [];
    state.include.clear();
    refresh();
  });
  $in("#wl-map").addEventListener("change", (e) => {
    const part = e.target.dataset?.part;
    if (part === undefined) return;
    state.mapping[Number(part)] = Number(e.target.value);
    refresh();
  });
  $in("#wl-fill").addEventListener("change", (e) => {
    state.fill = e.target.checked;
    refresh();
  });
  $in("#wl-preview").addEventListener("change", (e) => {
    const row = e.target.dataset?.row;
    if (row === undefined) return;
    state.include.set(Number(row), e.target.checked);
    refresh(false);
  });
  $in("#wl-add").addEventListener("click", () => add(false));
  $in("#wl-suggest").addEventListener("click", () => add(true));
}

/** The paste button sits in the empty box; once there is text it is in the way. */
function paintPasteButton() {
  $in("#wl-paste").hidden = !navigator.clipboard?.readText || Boolean($in("#wl-text").value);
}

/** The words already in the sheet, by the column a list's first part goes to. */
function existingWords(sheet, at) {
  if (at < 0) return [];
  return sheet.rows.map((r) => r.values[at]).filter((v) => String(v ?? "").trim());
}

function separatorOptions(detected) {
  const auto = detected === "none" ? t("wlSepNone") : SEPARATORS.find((s) => s.id === detected)?.label.trim() || detected;
  const opts = [`<option value="auto">${escapeHtml(t("wlSepAuto", auto))}</option>`];
  for (const s of SEPARATORS) opts.push(`<option value="${s.id}">${escapeHtml(s.id === "tab" ? "Tab" : s.label.trim())}</option>`);
  opts.push(`<option value="none">${escapeHtml(t("wlSepNone"))}</option>`);
  return opts.join("");
}

/** Whether row `i` goes in: what the reader ticked, else everything but duplicates. */
const included = (parsed, i) => state.include.get(i) ?? !parsed.marks[i];

/** The rows to add, each as the sheet's values. */
function planned() {
  const sheet = editor.sheet();
  const parsed = state.parsed;
  const width = sheet.columns.length;
  const roles = columnRoles(sheet.columns);
  const out = [];
  parsed.rows.forEach((parts, i) => {
    if (!included(parsed, i)) return;
    const values = placeRow(parts, state.mapping, width);
    const reading = roles.reading ?? roles.ipa;
    if (state.fill && reading !== undefined && !values[reading]) {
      const word = values[state.mapping[0]] || parts[0];
      const r = state.readings.get(word);
      if (r) values[reading] = r;
    }
    out.push(values);
  });
  return out;
}

async function refresh(reparse = true) {
  const sheet = editor.sheet();
  const text = $in("#wl-text").value;
  const firstGuess = guessMapping(sheet.columns, 1)[0];
  if (reparse || !state.parsed) {
    state.parsed = parseList(text, { separator: state.separator, existing: existingWords(sheet, state.mapping[0] ?? firstGuess) });
  }
  const parsed = state.parsed;
  const sepBox = $in("#wl-sep");
  sepBox.innerHTML = separatorOptions(state.separator === "auto" ? parsed.separator : parseList(text).separator);
  sepBox.value = state.separator;

  // The mapping: one select per part the list has, guessed until changed.
  const parts = Math.min(6, Math.max(1, ...parsed.rows.map((r) => r.length)));
  const guess = guessMapping(sheet.columns, parts);
  for (let p = 0; p < parts; p++) if (state.mapping[p] === undefined) state.mapping[p] = guess[p];
  state.mapping.length = parts;
  const colOptions = (sel) =>
    sheet.columns.map((c, i) => `<option value="${i}"${i === sel ? " selected" : ""}>${escapeHtml(c.name || String(i + 1))}</option>`).join("") +
    `<option value="-1"${sel === -1 ? " selected" : ""}>${escapeHtml(t("wlSkipPart"))}</option>`;
  $in("#wl-map").innerHTML = parsed.rows.length
    ? state.mapping
        .map(
          (at, p) =>
            `<label class="wt-mapitem"><span>${escapeHtml(t("wlPart", p + 1))}</span>${icon("arrow-right")}<select data-part="${p}">${colOptions(at)}</select></label>`,
        )
        .join("")
    : "";

  // Readings: the sheet's language, a column to put them in, and a library.
  const roles = columnRoles(sheet.columns);
  const readingAt = roles.reading ?? roles.ipa;
  const language = listLanguage(sheet.columns, parsed.rows.slice(0, 20).map((r) => r[0]), state.mapping[0] ?? 0);
  const offline = language === "zh" || language === "ko";
  const fillRow = $in("#wl-fillrow");
  fillRow.hidden = !(offline && readingAt !== undefined && parsed.rows.length);
  $in("#wl-filltext").textContent = t(language === "zh" ? "wlFillPinyin" : "wlFillRoman", sheet.columns[readingAt]?.name || "");
  const note = $in("#wl-langnote");
  note.hidden = !(language === "ja" && readingAt !== undefined && parsed.rows.length);
  note.textContent = t("wlNoJaReading");
  if (!fillRow.hidden && state.fill) {
    const words = parsed.rows.map((r) => placeRow(r, state.mapping, sheet.columns.length)[state.mapping[0]] || r[0]);
    const missing = words.filter((w) => w && !state.readings.has(w));
    if (missing.length) {
      try {
        const read = await loadReader(language);
        for (const w of missing) state.readings.set(w, read ? read(w) : "");
      } catch {
        fillRow.hidden = true;
        editor.toast(t("wlReaderFailed"), "bad");
      }
    }
  }

  paintPreview();
}

function paintPreview() {
  const sheet = editor.sheet();
  const parsed = state.parsed;
  const rows = planned();
  const dupes = parsed.marks.filter(Boolean).length;
  $in("#wl-sum").textContent = parsed.rows.length
    ? [t("wlCount", rows.length), dupes ? t("wlDupes", dupes) : ""].filter(Boolean).join(" · ")
    : "";
  const shown = [...new Set(state.mapping.filter((at) => at >= 0))].sort((a, b) => a - b);
  const roles = columnRoles(sheet.columns);
  const readingAt = roles.reading ?? roles.ipa;
  if (state.fill && readingAt !== undefined && !shown.includes(readingAt) && !$in("#wl-fillrow").hidden) {
    shown.push(readingAt);
    shown.sort((a, b) => a - b);
  }
  const head = shown.map((at) => `<th>${escapeHtml(sheet.columns[at]?.name || "")}</th>`).join("");
  const body = parsed.rows
    .slice(0, PREVIEW_ROWS)
    .map((parts, i) => {
      const values = placeRow(parts, state.mapping, sheet.columns.length);
      const mark = parsed.marks[i];
      let readingCell = false;
      if (state.fill && readingAt !== undefined && !values[readingAt] && !$in("#wl-fillrow").hidden) {
        const r = state.readings.get(values[state.mapping[0]] || parts[0]);
        if (r) {
          values[readingAt] = r;
          readingCell = true;
        }
      }
      const on = included(parsed, i);
      const cells = shown
        .map((at) => `<td${at === readingAt && readingCell ? ' class="sgval"' : ""}>${escapeHtml(values[at] || "")}</td>`)
        .join("");
      const why = mark ? `<span class="wt-dup">${escapeHtml(t(mark === "sheet" ? "wlDupSheet" : "wlDupList"))}</span>` : "";
      return `<tr class="${on ? "" : "off"}${mark ? " dup" : ""}"><td class="wt-tick"><input type="checkbox" data-row="${i}"${on ? " checked" : ""}
        aria-label="${escapeHtml(parts[0] || "")}"></td>${cells}<td class="wt-why">${why}</td></tr>`;
    })
    .join("");
  const more = parsed.rows.length > PREVIEW_ROWS ? `<p class="small muted">${escapeHtml(t("wlMore", parsed.rows.length - PREVIEW_ROWS))}</p>` : "";
  $in("#wl-preview").innerHTML = parsed.rows.length
    ? `<table class="wt-table"><thead><tr><th class="wt-tick"></th>${head}<th></th></tr></thead><tbody>${body}</tbody></table>${more}`
    : "";
  const n = rows.length;
  const addBtn = $in("#wl-add");
  addBtn.disabled = !n || state.mapping[0] < 0;
  $in("#wl-add-text").textContent = t("wlAdd", n);
  const language = listLanguage(sheet.columns, parsed.rows.slice(0, 20).map((r) => r[0]), state.mapping[0] ?? 0);
  const sug = $in("#wl-suggest");
  sug.hidden = !n || !coverage(language) || !editor.canSuggest();
  sug.disabled = addBtn.disabled;
  $in("#wl-suggest-text").textContent = t("wlSuggestN", n);
}

function add(thenSuggest) {
  const rows = planned();
  if (!rows.length) return;
  const first = editor.addWords(rows);
  box.close();
  editor.toast(t("wlAdded", rows.length), "ok");
  if (thenSuggest) editor.suggest(rows.map((_, i) => first + i));
}

/**
 * Wires the dialog to the page. `editor` is the page's side of it:
 *   sheet()          the sheet being edited ({columns, rows})
 *   addWords(rows)   appends rows of values (IDs as the sheet keys them); returns the first's index
 *   suggest(rows)    opens suggestions for those row indices
 *   canSuggest()     whether the sheet has a column suggestions could fill
 *   toast(text, kind)
 */
export function mountWordPaste(page) {
  editor = page;
  return { open };
}

export function open() {
  if (!box) build();
  state.separator = "auto";
  state.mapping = [];
  state.include.clear();
  state.parsed = null;
  $in("#wl-text").value = "";
  paintPasteButton();
  refresh();
  box.showModal();
  $in("#wl-text").focus();
}
