/**
 * Sheet to Anki's "Dán văn bản": a list pasted from Apple Notes, Google Keep,
 * Quizlet's Export → Copy text or anywhere, made into a named deck — or a whole
 * set written the way a note is (a `#config` line on top), or a whole CSV/TSV
 * sheet (an AI assistant's answer, fenced or not), kept as it is.
 *
 * Nothing here reads text: wordlist.js splits a line, importformats.js reads
 * the paste (readPaste), suggests settings for one that has none
 * (suggestSettings / applySettings) and writes them back into the reader's own
 * text (withSettings), and builds the sheet (pasteGrid). This is the dialog
 * around them. What it hands the page is a shared-sheet fragment (`#s=…`,
 * sharelink.js), the same thing Create sheet's share link is, so the deck has
 * an address: a reload keeps it, Copy link sends it, and "Sửa sheet" opens it
 * in Create sheet.
 */

import { escapeHtml } from "./anki.js";
import { lang, t } from "./i18n.js";
import { icon } from "./icons.js";
import { SEPARATORS } from "./wordlist.js";
import { deckKey, markerGet } from "./identity.js";
import { warningText } from "./sheetwarnings.js";
import { cardFrame } from "./cardframe.js";
import {
  SPOKEN,
  THEMES,
  applySettings,
  cleanName,
  detectRowSeparator,
  namedSheet,
  pasteGrid,
  readPaste,
  readSheetText,
  suggestSettings,
  withSettings,
} from "./importformats.js";
import { encodeShare, shareAddress, toTsv } from "./sharelink.js";

const PREVIEW_ROWS = 200;
// The last name used, so pasting the longer list next week lands in the same deck.
const NAME_KEY = "sc-paste-name";
// The panel's last choices for each set, by its name: re-pasting the list
// without its #config line starts from them rather than from a guess.
const CHOICES_KEY = "sc-paste-settings";

let page = null;
let box = null;
const state = {
  separator: "auto",
  rows: "auto",
  header: "auto",
  include: new Map(),
  parsed: null,
  sheet: null,
  suggestion: null,
  choices: null,
  touched: false,
  editing: false,
  reused: false,
};

const $in = (sel) => box.querySelector(sel);

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

const sideLabel = { front: "txSideFront", back: "txSideBack", hide: "txSideHide" };

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
      <p class="small muted tx-head" id="tx-head" hidden><span id="tx-head-text"></span>
        <button class="linkbtn" id="tx-head-flip" type="button"></button></p>
      <p class="wt-sum" id="tx-sum" aria-live="polite"></p>
      <div class="wt-preview" id="tx-preview"></div>
      <ul class="tx-warn" id="tx-warn" hidden></ul>
      <section class="tx-set" id="tx-set" hidden aria-labelledby="tx-set-title">
        <div class="tx-setgrid">
          <div class="tx-panel">
            <div id="tx-given" hidden>
              <h3 class="tx-h" id="tx-given-title">${escapeHtml(t("txGivenTitle"))}</h3>
              <dl class="tx-givenlist" id="tx-givenlist"></dl>
              <button class="toolbtn" id="tx-edit-settings" type="button">${icon("pen-line")}<span>${escapeHtml(t("txEditSettings"))}</span></button>
            </div>
            <div id="tx-choose" hidden>
              <h3 class="tx-h" id="tx-set-title">${escapeHtml(t("txSettings"))}</h3>
              <p class="small muted tx-reused" id="tx-reused" hidden>${icon("history")}<span>${escapeHtml(t("txReused"))}</span></p>
              <div class="tx-field">
                <label class="tx-label" for="tx-tts">${escapeHtml(t("txSpeak"))}</label>
                <select id="tx-tts"></select>
                <label class="wt-check" id="tx-ex-wrap" hidden><input type="checkbox" id="tx-ex"><span>${escapeHtml(t("txSpeakExample"))}</span></label>
              </div>
              <div class="tx-field">
                <span class="tx-label" id="tx-theme-label">${escapeHtml(t("txTheme"))}</span>
                <div class="tx-chips" id="tx-themes" role="group" aria-labelledby="tx-theme-label"></div>
              </div>
              <div class="tx-field" id="tx-roles-wrap" hidden>
                <span class="tx-label">${escapeHtml(t("txRoles"))}</span>
                <div class="tx-roles" id="tx-roles"></div>
              </div>
              <button class="linkbtn tx-more" id="tx-more" type="button">${escapeHtml(t("txMore"))}</button>
            </div>
          </div>
          <div class="tx-cardwrap">
            <div class="tx-card" id="tx-card"></div>
            <ul class="tx-warn" id="tx-cardwarn" hidden></ul>
          </div>
        </div>
        <div class="tx-out" id="tx-out" hidden>
          <h3 class="tx-h">${escapeHtml(t("txOutTitle"))}</h3>
          <pre class="tx-outtext" id="tx-outtext" tabindex="0"></pre>
          <div class="tx-outbar">
            <button class="toolbtn" id="tx-copy" type="button">${icon("copy")}<span>${escapeHtml(t("txCopy"))}</span></button>
            <span class="small muted" id="tx-copied" aria-live="polite"></span>
          </div>
          <p class="small muted">${escapeHtml(t("txOutHint"))}</p>
        </div>
      </section>
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
      state.editing = false;
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
  let nameTimer = 0;
  $in("#tx-name").addEventListener("input", () => {
    $in("#tx-name-error").hidden = true;
    $in("#tx-name").removeAttribute("aria-invalid");
    clearTimeout(nameTimer);
    nameTimer = setTimeout(() => {
      // Another set's name: its own last choices, unless some were made here.
      if (!state.touched) state.choices = null;
      paint();
    }, 200);
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
  $in("#tx-head-flip").addEventListener("click", () => {
    state.header = state.parsed?.header ? false : true;
    state.include.clear();
    state.choices = null;
    refresh();
  });
  $in("#tx-preview").addEventListener("change", (e) => {
    const row = e.target.dataset?.row;
    if (row === undefined) return;
    state.include.set(Number(row), e.target.checked);
    paint();
  });
  $in("#tx-tts").addEventListener("change", (e) => choose({ tts: e.target.value }));
  $in("#tx-ex").addEventListener("change", (e) => choose({ example: e.target.checked }));
  $in("#tx-themes").addEventListener("click", (e) => {
    const chip = e.target.closest("[data-theme]");
    if (chip) choose({ theme: chip.dataset.theme });
  });
  $in("#tx-roles").addEventListener("change", (e) => {
    const at = e.target.dataset?.col;
    if (at === undefined) return;
    const sides = [...state.choices.sides];
    sides[Number(at)] = e.target.value;
    choose({ sides });
  });
  $in("#tx-edit-settings").addEventListener("click", () => {
    state.editing = true;
    state.choices = null;
    paint();
    $in("#tx-tts").focus();
  });
  $in("#tx-copy").addEventListener("click", copyText);
  $in("#tx-more").addEventListener("click", () => finish(true));
  $in("#tx-go").addEventListener("click", () => finish(false));
  $in("#tx-edit").addEventListener("click", () => finish(true));
}

function choose(change) {
  state.choices = { ...state.choices, ...change };
  state.touched = true;
  state.reused = false;
  paint();
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
  // A whole sheet keeps its own columns and settings row; everything else is
  // read as the text format (a list being the shortest case of it).
  state.sheet = readSheetText(text);
  $in("#tx-opts").hidden = Boolean(state.sheet);
  if (state.sheet?.name) $in("#tx-name").value = state.sheet.name;
  state.parsed = readPaste(text, { rows: state.rows, separator: state.separator, header: state.header });
  const named = state.parsed.deck.find((c) => /^name\s*=/i.test(c));
  if (!state.sheet && named) $in("#tx-name").value = cleanName(named.split("=").slice(1).join("="));
  if (!state.sheet) {
    const auto = readPaste(text, { rows: state.rows, header: state.header });
    options(auto.separator, state.parsed.rowSeparator, text);
  }
  if (!state.touched) state.choices = null;
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
  $in("#tx-head").hidden = true;
  $in("#tx-warn").hidden = true;
  $in("#tx-set").hidden = !words.length;
  $in("#tx-given").hidden = true;
  $in("#tx-choose").hidden = true;
  $in("#tx-out").hidden = true;
  $in("#tx-go").disabled = !words.length;
  $in("#tx-edit").disabled = !words.length;
  if (words.length) paintCard(namedSheet(rows, currentName() || state.sheet.name || "x"));
}

const currentName = () => cleanName($in("#tx-name").value);

/** The panel's choices: made here, else this set's last ones, else a guess. */
function currentChoices(suggestion) {
  const guess = suggestion.choices;
  if (state.choices && state.choices.sides?.length === guess.sides.length) return state.choices;
  state.reused = false;
  let choices = { ...guess, sides: [...guess.sides] };
  const last = !suggestion.given && stored(CHOICES_KEY, {})[deckKey(currentName())];
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
  state.choices = choices;
  return choices;
}

/** What the sheet will be: the text's own settings, or the panel's. */
function settings() {
  const parsed = state.parsed;
  const suggestion = (state.suggestion = suggestSettings(parsed, { language: lang() }));
  const named = parsed.deck.some((c) => /^name\s*=/i.test(c));
  // A #config line that names its set is the reader's own word; one that does
  // not still needs the name written into it, so it gets the panel.
  const choosing = !(parsed.config && named) || state.editing;
  if (!choosing) return { choosing, cells: parsed.cells, deck: parsed.deck };
  const choices = currentChoices(suggestion);
  return { choosing, choices, ...applySettings(suggestion, choices, parsed.deck) };
}

function paint() {
  if (state.sheet) return paintSheet();
  const parsed = state.parsed;
  const rows = chosenRows();
  const width = Math.max(2, parsed.header?.length || 0, ...parsed.rows.map((r) => r.length));
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

  // The first line read one way when the text did not say which: one tap the other.
  // Said only when the line could be either: one that plainly looks like the
  // cards under it ("alike", a sentence, a repeat) is a card without a word.
  const either = parsed.header || ["unlike", "alone"].includes(parsed.headerWhy);
  const unsure = parsed.separator !== "none" && ((!parsed.headerSure && either) || state.header !== "auto");
  $in("#tx-head").hidden = !unsure || (!parsed.header && parsed.rows.length < 2);
  $in("#tx-head-text").textContent = t(parsed.header ? "hdKept" : "hdSynth");
  $in("#tx-head-flip").textContent = t(parsed.header ? "hdUseCard" : "hdUseFirst");

  const warn = $in("#tx-warn");
  warn.innerHTML = parsed.warnings
    .map((w) => `<li>${icon("triangle-alert")}<span>${escapeHtml(w.key === "txTwice" ? t("txTwice", w.col, w.setting) : t("txExtraCell", w.col))}</span></li>`)
    .join("");
  warn.hidden = !parsed.warnings.length;

  $in("#tx-set").hidden = !rows.length;
  if (!rows.length) return;
  const made = settings();
  $in("#tx-given").hidden = made.choosing;
  $in("#tx-choose").hidden = !made.choosing;
  $in("#tx-out").hidden = !made.choosing;
  if (made.choosing) paintChoices(made.choices);
  else paintGiven(made);
  if (made.choosing) {
    $in("#tx-outtext").textContent = withSettings($in("#tx-text").value, parsed, {
      name: currentName(),
      names: state.suggestion.names,
      cells: made.cells,
      deck: made.deck,
    });
    $in("#tx-copied").textContent = "";
  }
  paintCard(pasteGrid({ name: currentName() || "x", rows, header: parsed.header, cells: made.cells, deck: made.deck, language: lang() }));
}

function paintChoices(choices) {
  const s = state.suggestion;
  $in("#tx-reused").hidden = !state.reused;
  const tts = $in("#tx-tts");
  const known = SPOKEN.some(([code]) => code === choices.tts);
  tts.innerHTML = [
    `<option value="">${escapeHtml(t("txSpeakNone"))}</option>`,
    ...SPOKEN.map(([code, label]) => `<option value="${code}">${escapeHtml(label)}</option>`),
    ...(choices.tts && !known ? [`<option value="${escapeHtml(choices.tts)}">${escapeHtml(choices.tts)}</option>`] : []),
  ].join("");
  tts.value = choices.tts;
  $in("#tx-ex-wrap").hidden = s.example < 0 || !choices.tts;
  $in("#tx-ex").checked = choices.example;
  const themes = [["", t("txThemeNone")], ...THEMES.map((name) => [name, name])];
  if (choices.theme && !THEMES.includes(choices.theme)) themes.push([choices.theme, choices.theme]);
  $in("#tx-themes").innerHTML = themes
    .map(
      ([value, label]) =>
        `<button type="button" class="tx-chip" data-theme="${escapeHtml(value)}" aria-pressed="${value === choices.theme}">${escapeHtml(label)}</button>`,
    )
    .join("");
  const many = s.content.length >= 3;
  $in("#tx-roles-wrap").hidden = !many;
  if (many) {
    $in("#tx-roles").innerHTML = s.content
      .map((i) => {
        const opts = ["front", "back", "hide"]
          .map((side) => `<option value="${side}"${choices.sides[i] === side ? " selected" : ""}>${escapeHtml(t(sideLabel[side]))}</option>`)
          .join("");
        return `<label class="tx-role"><span>${escapeHtml(s.names[i])}</span><select data-col="${i}">${opts}</select></label>`;
      })
      .join("");
  }
}

function paintGiven({ cells, deck }) {
  const s = state.suggestion;
  const rows = [[t("txGivenDeck"), deck.join("; ")]];
  s.names.forEach((name, i) => {
    if (cells[i]) rows.push([name, cells[i]]);
  });
  $in("#tx-givenlist").innerHTML = rows
    .map(([k, v]) => `<dt>${escapeHtml(k)}</dt><dd><code>${escapeHtml(v || t("txGivenNone"))}</code></dd>`)
    .join("");
}

let cardTimer = 0;
let lastCard = "";
/** The first card of the sheet as it stands, drawn by the page's own Python. */
function paintCard(grid) {
  const tsv = toTsv(grid);
  if (tsv === lastCard && $in("#tx-card").childElementCount) return;
  clearTimeout(cardTimer);
  cardTimer = setTimeout(() => {
    const out = page.previewCard?.(tsv);
    const slot = $in("#tx-card");
    const warn = $in("#tx-cardwarn");
    if (!out) {
      lastCard = "";
      slot.innerHTML = `<p class="small muted tx-cardwait">${escapeHtml(t("txCardLoading"))}</p>`;
      warn.hidden = true;
      return;
    }
    lastCard = tsv;
    slot.innerHTML = cardFrame(out.doc, t("cardFrameTitle"));
    const frame = slot.querySelector("iframe");
    frame.removeAttribute("id");
    frame.addEventListener("load", () => {
      try {
        frame.style.height = `${Math.min(frame.contentDocument.documentElement.scrollHeight + 4, 640)}px`;
      } catch {
        // Measured where it can be; the minimum height is there otherwise.
      }
    });
    warn.innerHTML = out.warnings
      .map((w) => `<li>${icon("triangle-alert")}<span>${escapeHtml(warningText(w, lang()))}</span></li>`)
      .join("");
    warn.hidden = !out.warnings.length;
  }, 150);
}

async function copyText() {
  const text = $in("#tx-outtext").textContent;
  try {
    await navigator.clipboard.writeText(text);
    $in("#tx-copied").textContent = t("txCopied");
  } catch {
    $in("#tx-copied").textContent = t("txCopyFailed");
    getSelection()?.selectAllChildren($in("#tx-outtext"));
  }
}

function keepChoices(name) {
  if (!state.choices || !state.suggestion || state.suggestion.given) return;
  const all = stored(CHOICES_KEY, {});
  const sides = {};
  state.suggestion.names.forEach((n, i) => (sides[n] = state.choices.sides[i]));
  all[deckKey(name)] = { tts: state.choices.tts, example: state.choices.example, theme: state.choices.theme, sides };
  store(CHOICES_KEY, all);
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
    const made = settings();
    grid = pasteGrid({ name, rows, header: state.parsed.header, cells: made.cells, deck: made.deck, language: lang() });
    if (made.choosing) keepChoices(name);
  }
  remember(name);
  // The grid carries name= and the deck is keyed by it; the link's title is the
  // same name, which is what the page calls the file it makes of it.
  const title = state.sheet?.name || markerGet(grid[1].find((c) => /^#config/i.test(c)) || "", "name") || name;
  const hash = await encodeShare(title, toTsv(grid));
  box.close();
  if (edit) location.assign(shareAddress(hash));
  else page.openShared(hash);
}

/**
 * Wires the dialog to Sheet to Anki. `host.openShared(hash)` opens a `#s=…`
 * sheet the way an address carrying one is opened; `host.previewCard(tsv)`
 * draws the sheet's first card ({doc, warnings}), or null until Python is up.
 */
export function mountTextImport(host) {
  page = host;
  return {
    open,
    // Python has arrived: the card that was waiting for it can be drawn.
    ready() {
      if (box?.open) {
        lastCard = "";
        paint();
      }
    },
  };
}

/**
 * Opens the dialog. `text`, when given, is what was pasted into the page's main
 * field (or the landing page's), put in the box as if pasted here.
 */
export function open(text) {
  if (!box) build();
  if (typeof text === "string" && text.trim()) $in("#tx-text").value = text;
  state.separator = "auto";
  state.rows = "auto";
  state.header = "auto";
  state.include.clear();
  state.choices = null;
  state.touched = false;
  state.editing = false;
  const input = $in("#tx-name");
  if (!input.value) input.value = remembered();
  $in("#tx-name-error").hidden = true;
  paintPasteButton();
  refresh();
  box.showModal();
  (input.value ? $in("#tx-text") : input).focus();
}
