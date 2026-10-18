/**
 * Sheet to Anki's "Dán văn bản": a list pasted from Apple Notes, Google Keep,
 * Quizlet's Export → Copy text or anywhere, made into a named Basic deck — or a
 * whole CSV/TSV sheet (an AI assistant's answer, fenced or not), kept as it is.
 *
 * Nothing here reads text: wordlist.js splits a line, importformats.js finds
 * where a card ends, whether a first line is column names, whether the paste
 * is a whole sheet, and builds the sheet. This is the dialog around them. What
 * it hands the page is a shared-sheet fragment (`#s=…`, sharelink.js), the same
 * thing Create sheet's share link is, so the deck has an address: a reload
 * keeps it, Copy link sends it, and "Sửa sheet" opens it in Create sheet.
 */

import { escapeHtml } from "./anki.js";
import { lang, t } from "./i18n.js";
import { icon } from "./icons.js";
import { SEPARATORS } from "./wordlist.js";
import { cleanName, detectRowSeparator, namedSheet, pasteGrid, readPaste, readSheetText } from "./importformats.js";
import { encodeShare, shareAddress, toTsv } from "./sharelink.js";

const PREVIEW_ROWS = 200;
// The last name used, so pasting the longer list next week lands in the same deck.
const NAME_KEY = "sc-paste-name";

let page = null;
let box = null;
const state = { separator: "auto", rows: "auto", include: new Map(), parsed: null, sheet: null };

const $in = (sel) => box.querySelector(sel);

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

function build() {
  box = document.createElement("dialog");
  box.id = "textbox";
  box.className = "donebox pickbox wtbox";
  box.setAttribute("aria-labelledby", "tx-title");
  box.innerHTML = `
    <div class="done-head">
      <strong id="tx-title">${escapeHtml(t("txTitle"))}</strong>
      <button class="iconbtn" data-close type="button" title="${escapeHtml(t("close"))}" aria-label="${escapeHtml(t("close"))}">${icon("x")}</button>
    </div>
    <div class="wt-body">
      <p class="small muted wt-lead">${t("txLead")}</p>
      <div class="tx-name">
        <label class="linklabel" for="tx-name">${escapeHtml(t("txName"))}</label>
        <span id="tx-name-error" class="field-error" hidden>${icon("circle-alert")}<span>${escapeHtml(t("txNameEmpty"))}</span></span>
        <input id="tx-name" type="text" maxlength="100" autocomplete="off" required
               placeholder="${escapeHtml(t("txNamePlaceholder"))}" aria-describedby="tx-name-error tx-name-hint">
        <span id="tx-name-hint" class="small muted">${escapeHtml(t("txNameHint"))}</span>
      </div>
      <div class="wt-area">
        <textarea id="tx-text" rows="8" spellcheck="false" autocapitalize="off" autocomplete="off"
                  placeholder="${escapeHtml(t("txPlaceholder"))}" aria-label="${escapeHtml(t("txTitle"))}"></textarea>
        <button class="toolbtn wt-pastebtn" id="tx-paste" type="button" hidden>${icon("clipboard")}<span>${escapeHtml(t("wlPasteBtn"))}</span></button>
      </div>
      <div class="wt-opts" id="tx-opts">
        <label class="wt-sep"><span>${escapeHtml(t("txSides"))}</span><select id="tx-sep"></select></label>
        <label class="wt-sep"><span>${escapeHtml(t("txRows"))}</span><select id="tx-rows"></select></label>
      </div>
      <p class="wt-sum" id="tx-sum" aria-live="polite"></p>
      <div class="wt-preview" id="tx-preview"></div>
    </div>
    <div class="wt-foot">
      <button class="toolbtn" id="tx-edit" type="button" disabled>${icon("pen-line")}<span>${escapeHtml(t("txEdit"))}</span></button>
      <button class="btn" id="tx-go" type="button" disabled><span>${escapeHtml(t("go"))}</span>${icon("arrow-right")}</button>
    </div>`;
  document.body.append(box);
  box.querySelector("[data-close]").addEventListener("click", () => box.close());
  box.addEventListener("click", (e) => {
    if (e.target === box) box.close();
  });
  const text = $in("#tx-text");
  let timer = 0;
  text.addEventListener("input", () => {
    paintPasteButton();
    clearTimeout(timer);
    timer = setTimeout(() => {
      state.include.clear();
      refresh();
    }, 120);
  });
  if (navigator.clipboard?.readText) {
    $in("#tx-paste").addEventListener("click", async () => {
      try {
        text.value = await navigator.clipboard.readText();
        paintPasteButton();
        state.include.clear();
        refresh();
      } catch {
        text.focus();
      }
    });
  }
  $in("#tx-name").addEventListener("input", () => {
    $in("#tx-name-error").hidden = true;
    $in("#tx-name").removeAttribute("aria-invalid");
  });
  $in("#tx-sep").addEventListener("change", (e) => {
    state.separator = e.target.value;
    state.include.clear();
    refresh();
  });
  $in("#tx-rows").addEventListener("change", (e) => {
    state.rows = e.target.value;
    state.include.clear();
    refresh();
  });
  $in("#tx-preview").addEventListener("change", (e) => {
    const row = e.target.dataset?.row;
    if (row === undefined) return;
    state.include.set(Number(row), e.target.checked);
    paint();
  });
  $in("#tx-go").addEventListener("click", () => finish(false));
  $in("#tx-edit").addEventListener("click", () => finish(true));
}

function paintPasteButton() {
  $in("#tx-paste").hidden = !navigator.clipboard?.readText || Boolean($in("#tx-text").value);
}

const sepLabel = (id) =>
  id === "none" ? t("wlSepNone") : id === "tab" ? "Tab" : SEPARATORS.find((s) => s.id === id)?.label.trim() || id;
const rowLabel = (sep) => (sep.id === "token" ? `“${sep.token}”` : t("txRowsNewline"));

function options(detectedSep, detectedRows, text) {
  const seps = [`<option value="auto">${escapeHtml(t("wlSepAuto", sepLabel(detectedSep)))}</option>`];
  for (const s of SEPARATORS) seps.push(`<option value="${s.id}">${escapeHtml(sepLabel(s.id))}</option>`);
  seps.push(`<option value="none">${escapeHtml(t("wlSepNone"))}</option>`);
  $in("#tx-sep").innerHTML = seps.join("");
  $in("#tx-sep").value = state.separator;

  // The row choice: newline, ";", and whatever mark this paste repeats.
  const found = detectRowSeparator(text);
  const tokens = new Set([";"]);
  if (found.id === "token") tokens.add(found.token);
  if (state.rows !== "auto" && state.rows !== "newline") tokens.add(state.rows);
  const rows = [`<option value="auto">${escapeHtml(t("wlSepAuto", rowLabel(detectedRows)))}</option>`];
  rows.push(`<option value="newline">${escapeHtml(t("txRowsNewline"))}</option>`);
  for (const tok of tokens) rows.push(`<option value="${escapeHtml(tok)}">${escapeHtml(`“${tok}”`)}</option>`);
  $in("#tx-rows").innerHTML = rows.join("");
  $in("#tx-rows").value = state.rows;
}

const included = (parsed, i) => state.include.get(i) ?? !parsed.marks[i];

function refresh() {
  const text = $in("#tx-text").value;
  // A whole sheet keeps its own columns and settings row; only a list is mapped
  // onto Mặt trước / Mặt sau.
  state.sheet = readSheetText(text);
  $in("#tx-opts").hidden = Boolean(state.sheet);
  if (state.sheet?.name) $in("#tx-name").value = state.sheet.name;
  state.parsed = readPaste(text, { rows: state.rows, separator: state.separator });
  if (!state.sheet) {
    const auto = readPaste(text, { rows: state.rows });
    options(auto.separator, state.parsed.rowSeparator, text);
  }
  paint();
}

function chosenRows() {
  const parsed = state.parsed;
  return parsed.rows.filter((_, i) => included(parsed, i));
}

function table(head, body, more) {
  return `<table class="wt-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>${
    more > 0 ? `<p class="small muted">${escapeHtml(t("wlMore", more))}</p>` : ""
  }`;
}

function paintSheet() {
  const { rows } = state.sheet;
  const [header, ...rest] = rows;
  const words = rest.filter((r) => !/^#config/i.test(r[0] || "") && r.some(Boolean));
  $in("#tx-sum").textContent = t("txWholeSheet", header.length, words.length);
  const head = header.map((h) => `<th>${escapeHtml(h)}</th>`).join("");
  const body = rest
    .slice(0, PREVIEW_ROWS)
    .map((r) => {
      const config = r.some((c) => /^#config/i.test(c));
      return `<tr class="${config ? "off" : ""}">${header.map((_, c) => `<td>${escapeHtml(r[c] || "")}</td>`).join("")}</tr>`;
    })
    .join("");
  $in("#tx-preview").innerHTML = table(head, body, rest.length - PREVIEW_ROWS);
  $in("#tx-go").disabled = !words.length;
  $in("#tx-edit").disabled = !words.length;
}

function paint() {
  if (state.sheet) return paintSheet();
  const parsed = state.parsed;
  const rows = chosenRows();
  const width = Math.max(2, ...parsed.rows.map((r) => r.length));
  const names = pasteGrid({ name: "x", rows: parsed.rows, header: parsed.header, language: lang() })[0].slice(0, width);
  const dupes = parsed.marks.filter(Boolean).length;
  const oneSided = rows.filter((r) => r.length < 2 || !r[1]).length;
  $in("#tx-sum").textContent = parsed.rows.length
    ? [t("txCount", rows.length), dupes ? t("wlDupes", dupes) : "", oneSided ? t("txOneSided", oneSided) : ""]
        .filter(Boolean)
        .join(" · ")
    : "";
  const head = `<th class="wt-tick"></th>${names.map((n) => `<th>${escapeHtml(n)}</th>`).join("")}<th></th>`;
  const body = parsed.rows
    .slice(0, PREVIEW_ROWS)
    .map((parts, i) => {
      const on = included(parsed, i);
      const mark = parsed.marks[i];
      const cells = names.map((_, c) => `<td>${escapeHtml(parts[c] || "")}</td>`).join("");
      const why = mark ? `<span class="wt-dup">${escapeHtml(t("wlDupList"))}</span>` : "";
      return `<tr class="${on ? "" : "off"}${mark ? " dup" : ""}"><td class="wt-tick"><input type="checkbox" data-row="${i}"${on ? " checked" : ""}
        aria-label="${escapeHtml(parts[0] || "")}"></td>${cells}<td class="wt-why">${why}</td></tr>`;
    })
    .join("");
  $in("#tx-preview").innerHTML = parsed.rows.length ? table(head, body, parsed.rows.length - PREVIEW_ROWS) : "";
  $in("#tx-go").disabled = !rows.length;
  $in("#tx-edit").disabled = !rows.length;
}

async function finish(edit) {
  const input = $in("#tx-name");
  const name = cleanName(input.value) || state.sheet?.name || "";
  if (!name) {
    $in("#tx-name-error").hidden = false;
    input.setAttribute("aria-invalid", "true");
    input.focus();
    return;
  }
  let grid;
  if (state.sheet) grid = namedSheet(state.sheet.rows, name);
  else {
    const rows = chosenRows();
    if (!rows.length) return;
    grid = pasteGrid({ name, rows, header: state.parsed.header, language: lang() });
  }
  remember(name);
  // The sheet's own name= is its name wherever it goes; the title only names a
  // sheet that cannot carry one (no ID column).
  const hash = await encodeShare(state.sheet?.name || name, toTsv(grid));
  box.close();
  if (edit) location.assign(shareAddress(hash));
  else page.openShared(hash);
}

/**
 * Wires the dialog to Sheet to Anki. `host.openShared(hash)` opens a `#s=…`
 * sheet the way an address carrying one is opened.
 */
export function mountTextImport(host) {
  page = host;
  return { open };
}

export function open() {
  if (!box) build();
  state.separator = "auto";
  state.rows = "auto";
  state.include.clear();
  const input = $in("#tx-name");
  if (!input.value) input.value = remembered();
  $in("#tx-name-error").hidden = true;
  paintPasteButton();
  refresh();
  box.showModal();
  (input.value ? $in("#tx-text") : input).focus();
}
