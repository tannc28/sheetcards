/**
 * A settings row, and the card it makes.
 *
 * The reference for these directives is the README, and a copy of it here would
 * be a copy that drifts. This is the other way of documenting them: type one and
 * watch the card change. What a value has to look like is taught by the warning
 * you get when it does not — and that warning is the add-on's own sentence, out
 * of the add-on's own `sheet_config.py`, not a paraphrase that could be wrong.
 *
 * The editor is shaped like the thing it writes into: a sheet, with the column
 * names in row 1, the settings row in row 2 and one row of data in row 3. Typed
 * here it needs no translating into "and where does that go in Google Sheets".
 */

import { renderCard, escapeHtml } from "./anki.js";
import { LANGUAGES, lang, setLang, t } from "./i18n.js";
import { startPython } from "./pyodide.js";
import { cardDoc, cardFrame } from "./cardframe.js";
import { deckTree, treeHtml } from "./decktree.js";

/** Everything the editor needs, computed by the add-on's own code. */
const EDITOR = String.raw`
import json
from s2a.card_layout import build_templates, split_sides
from s2a.column_model import deck_path, plan_columns
from s2a.sheet_config import SheetConfig, is_config_row, parse_config_row
from s2a.tsv_model import build_tags


def keys():
    """The directive names and the value sets, read off sheet_config.

    A closed set — the sides, the alignments, the themes, the media kinds — is
    the add-on's to decide, so it is sent rather than copied into JavaScript
    where it would be a second answer. The open ones (a colour, a language, a
    size) are suggestions and live on the page: there is no complete list of
    them to be wrong about.
    """
    from s2a.sheet_config import (
        ALIGNMENTS,
        MEDIA_KINDS,
        SIDES,
        THEME_COLORS,
        THEMES,
        _DECK_KEYS,
        _FIELD_KEYS,
    )

    return json.dumps(
        {
            "field": list(_FIELD_KEYS),
            "deck": list(_DECK_KEYS),
            "closed": {
                "side": list(SIDES),
                "align": list(ALIGNMENTS),
                "theme": list(THEMES),
            },
            "themeColors": list(THEME_COLORS),
            "media": list(MEDIA_KINDS),
        }
    )


def preview(payload):
    """The sheet, as a sync would read it.

    Built with plan_columns and parse_config_row rather than with anything
    written for this page, so a column here behaves exactly as the same column
    would in a real sheet — including when the marker cell has been typed over
    and row 2 has stopped being a settings row at all.
    """
    data = json.loads(payload)
    names, cells, values = [], {}, {}
    for index, column in enumerate(data["columns"]):
        name = column["name"].strip() or "Column " + str(index + 1)
        # A repeated header is honoured once, which would silently drop a column
        # from the editor. Spaced apart so every column keeps a cell of its own.
        while name in names:
            name += " "
        names.append(name)
        cells[name] = column["cell"]
        values[name] = column["value"]

    plan = plan_columns(["ID"] + names)
    row = dict(cells)
    row["ID"] = data["marker"]

    config = parse_config_row(row, plan) if is_config_row(row, plan) else SheetConfig()
    front, back = split_sides(plan, config)
    # Where row 3 is filed, and under what. A card is not the only thing a
    # settings row decides: a subdeck column reaches the deck and never the card,
    # so with only the card on screen it looked inert.
    # (No backticks in this string: it is a JS template literal.)
    return json.dumps(
        {
            "names": names,
            "isConfig": config.present,
            "warnings": config.warnings,
            "front": front,
            "back": back,
            "deck": deck_path(values, plan, config),
            "tags": build_tags(values, plan, config),
            "templates": build_templates(
                plan, config, is_cloze=bool(config.cloze_field)
            ),
        },
        ensure_ascii=False,
    )
`;

const $ = (sel) => document.querySelector(sel);

// The same four the preview page shows, in the same order and with the same
// names: a card seen here and a card seen there are the same card, and a second
// vocabulary for looking at it would be a second thing to learn.
const CARD_TABS = ["front", "both", "back", "template"];

/**
 * The values worth offering for each directive that takes one.
 *
 * Suggestions, not the valid set — the valid set is `sheet_config.py`'s and the
 * closed ones arrive from there. These are the answers people actually want:
 * five languages rather than every BCP 47 tag, a handful of sizes rather than
 * 6 through 200. Anything not listed is typed into the box beside them, which
 * is why every one of these also accepts free text.
 *
 * A key that is not here is a flag: nothing to choose, so tapping it is the
 * whole interaction.
 */
const OPTIONS = {
  size: ["16", "20", "24", "32", "44", "64"],
  color: ["muted", "accent", "crimson", "teal", "darkorange", "#c2410c"],
  // The languages this add-on is actually used for. Anki matches the code
  // against an installed voice exactly, so these are the full forms.
  tts: ["en_US", "vi_VN", "zh_CN", "zh_TW", "ja_JP", "ko_KR"],
  speed: ["0.5", "0.75", "1", "1.25", "1.5", "2"],
  subdeck: ["1", "2", "3"],
  type: ["", "nc"],
  voices: [],
  label: [],
};

/** What a directive is worth starting from when it is switched on blind. */
function seed(key) {
  const closed = keys.closed?.[key];
  if (closed?.length) return `${key}=${closed[0]}`;
  const listed = OPTIONS[key];
  if (!listed) return key;
  return listed.length ? `${key}=${listed[0]}` : `${key}=`;
}

/** Whether tapping this chip has something to choose. */
function valued(key) {
  return Boolean(keys.closed?.[key] || OPTIONS[key]);
}

/** Whether the options panel has anything at all to show for this key. */
function hasPanel(key) {
  return valued(key) || Boolean(HELP[key]);
}

/**
 * What each directive is, and where the ones that need it get an example.
 *
 * The i18n key is written out rather than built from the name: the guard that
 * catches an unused string looks for the key quoted somewhere, and a key
 * assembled at runtime is a key it cannot see.
 *
 * `sample` is for the directives that do nothing on their own — `furigana` needs
 * `漢字[かんじ]` in the cell, `cloze` needs a `{{c1::…}}` in it, a media column
 * needs a URL. Those are the ones people give up on, because switching them on
 * and watching the card break teaches the wrong lesson. One tap fills row 3 with
 * something that works and the card explains itself.
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

const state = {
  marker: "#config",
  columns: [
    { name: "Word", cell: "size=44; bold", value: "hello" },
    { name: "Meaning", cell: "size=20; color=muted", value: "xin chào" },
  ],
  // Which cell the directive chips act on. A chip has to act on something, and
  // asking which column first would be a dialog in the way of a tap. -1 is the
  // marker cell, where the deck-wide settings live.
  active: 0,
  // The selected range — {r, c} is the anchor and {r2, c2} the far corner — and
  // which single cell has the keyboard, if any. Both are null most of the time.
  sel: null,
  editing: null,
  template: 0,
  tab: "both",
  // The directive whose options are showing, if any. One at a time: two open
  // panels on a phone is the list you were choosing from pushed off the screen.
  open: null,
};

let run = null;
let keys = { field: [], deck: [] };

// ---------------------------------------------------------------------------
// Undo
// ---------------------------------------------------------------------------
//
// The one spreadsheet habit that has no substitute and no workaround: a cell typed
// over is gone, and every other way of getting it back means remembering what was
// in it. Cheap to keep here — the whole sheet is three rows of strings, so a step
// is a copy of the sheet rather than a description of a change.
//
// A step is one *action*, not one keystroke: a cell being typed in is remembered
// as it was when the typing started, so Ctrl+Z takes back the word rather than the
// letter. `mark()` is called before anything that changes the sheet.
const history = { past: [], future: [] };
const LIMIT = 100;

// What is being typed into right now, if anything. A run of keystrokes in one cell
// is one step; moving to another cell, or doing anything that is not typing, ends
// the run. Without it Ctrl+Z would take back a letter at a time, which is what a
// text box does and not what a sheet does.
let session = null;

const sheetState = () => JSON.stringify({ marker: state.marker, columns: state.columns });

/** Remembers `before` as a step. Call it with the sheet as it was. */
function commit(before) {
  history.past.push(before);
  if (history.past.length > LIMIT) history.past.shift();
  history.future.length = 0;
  session = null;
}

/** One step for whatever is about to happen. */
function mark() {
  commit(sheetState());
}

/** One step for the *run* of keystrokes about to happen in `tag`. */
function markRun(tag) {
  if (session === tag) return;
  const before = sheetState();
  commit(before);
  session = tag;
}

/** Puts a remembered sheet back. Shared by undo and redo, which are each other. */
function restore(from, to) {
  if (!from.length) return false;
  session = null;
  to.push(sheetState());
  const { marker, columns } = JSON.parse(from.pop());
  state.marker = marker;
  state.columns = columns;
  state.editing = null;
  if (state.active >= columns.length) state.active = 0;
  if (state.sel) state.sel = null;
  paintSheet();
  draw();
  return true;
}

function status(text, kind = "", busy = false) {
  $("#status-text").textContent = text;
  $("#status").className = `status ${kind} ${busy ? "busy" : ""}`;
}

// ---------------------------------------------------------------------------
// Theme
// ---------------------------------------------------------------------------

function dark() {
  return document.documentElement.dataset.theme === "dark";
}

function setTheme(on) {
  if (on) document.documentElement.dataset.theme = "dark";
  else delete document.documentElement.dataset.theme;
  try {
    localStorage.setItem("s2a-theme", on ? "dark" : "light");
  } catch {
    // A browser refusing storage is not a reason to refuse the theme.
  }
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute("content", on ? "#0f1216" : "#ffffff");
  paintChrome();
  draw();
}

// ---------------------------------------------------------------------------
// A cell is text, and stays text
// ---------------------------------------------------------------------------

/** The directives in a cell, in the order they were typed. */
function parts(cell) {
  return cell
    .split(";")
    .map((part) => part.trim())
    .filter(Boolean);
}

const nameOf = (part) => part.split("=")[0].trim().toLowerCase();

/**
 * Adds a directive, or takes it away when it is already there.
 *
 * A chip that only ever adds cannot undo itself with the thing that did it: the
 * second tap looked broken, because nothing happened. Tapping now means "this
 * column has this directive", both ways round.
 */
function toggle(cell, key, value) {
  const had = parts(cell).some((part) => nameOf(part) === key);
  const kept = parts(cell).filter((part) => nameOf(part) !== key);
  if (value !== undefined) {
    return [...kept, value === "" ? key : `${key}=${value}`].join("; ");
  }
  return (had ? kept : [...kept, seed(key)]).join("; ");
}

/** The value a directive currently carries in the active cell, or null. */
function valueOf(key) {
  const cell = deckActive()
    ? state.marker.replace(/^\s*#config/i, "")
    : (state.columns[state.active]?.cell ?? "");
  const part = parts(cell).find((p) => nameOf(p) === key);
  if (part === undefined) return null;
  const at = part.indexOf("=");
  return at < 0 ? "" : part.slice(at + 1).trim();
}

/** Writes the active cell back, wherever it lives. */
function setCell(text) {
  if (deckActive()) state.marker = `#config ${text}`.trim();
  else state.columns[state.active].cell = text;
}

function cellText() {
  return deckActive()
    ? state.marker.replace(/^\s*#config/i, "")
    : (state.columns[state.active]?.cell ?? "");
}

/** True while the marker cell — the deck-wide one — is being edited. */
function deckActive() {
  return state.active === -1;
}

/** What the chips should show as on, for whichever cell is active. */
function activeKeys() {
  const cell = deckActive()
    ? state.marker.replace(/^\s*#config/i, "")
    : (state.columns[state.active]?.cell ?? "");
  return new Set(parts(cell).map(nameOf));
}

// ---------------------------------------------------------------------------
// Drawing
// ---------------------------------------------------------------------------

function paintChrome() {
  document.documentElement.lang = lang();
  for (const el of document.querySelectorAll("[data-i18n]")) {
    el.textContent = t(el.dataset.i18n);
  }
  for (const el of document.querySelectorAll("[data-i18n-attr]")) {
    for (const pair of el.dataset.i18nAttr.split(",")) {
      const [attr, key] = pair.split(":").map((s) => s.trim());
      el.setAttribute(attr, t(key));
    }
  }
  const button = $("#theme");
  button.textContent = dark() ? "☀" : "☾";
  button.title = button.ariaLabel = t(dark() ? "toLight" : "toDark");

  $("#langs").innerHTML = LANGUAGES.map(
    (l) =>
      `<button data-lang="${l.code}" class="${lang() === l.code ? "on" : ""}"` +
      ` aria-pressed="${lang() === l.code}">${l.label}</button>`,
  ).join("");
}

/** The letters a spreadsheet puts across the top: A, B, … Z, AA. */
function letter(index) {
  let out = "";
  for (let n = index + 1; n > 0; n = Math.floor((n - 1) / 26)) {
    out = String.fromCharCode(65 + ((n - 1) % 26)) + out;
  }
  return out;
}

/**
 * The sheet: column A fixed, one column per thing being edited.
 *
 * A wide sheet scrolls inside this box and nowhere else. The page itself must
 * never scroll sideways, which is the rule everything on a phone lives by.
 */
function paintSheet() {
  const cols = state.columns;
  // Every cell says where it is, which is what lets a range be selected, copied
  // and walked with the arrow keys. Column A is -1: it is the sheet's own column,
  // not one of the ones being edited, and numbering it 0 would put the ID column
  // and the first real column in the same place.
  const cell = (inner, r, c, cls = "") =>
    `<span class="cell ${cls}" data-r="${r}" data-c="${c}">${inner}</span>`;
  const label = (key) => escapeHtml(t(key));

  const head =
    `<span class="ref corner" data-all="1" title="${label("edSelectAll")}"></span>` +
    '<span class="ref" data-c="-1">A</span>' +
    cols
      .map((_, i) => `<span class="ref" data-c="${i}">${letter(i + 1)}</span>`)
      .join("");

  const names =
    '<span class="ref" data-r="0">1</span>' +
    cell("ID", 0, -1, "fixed") +
    cols
      .map((c, i) =>
        cell(
          `<input data-edit="name" data-col="${i}" value="${escapeHtml(c.name)}"
             spellcheck="false" autocomplete="off" aria-label="${label("edName")}">
           <button class="drop" data-drop="${i}" type="button"
             title="${label("edRemoveColumn")}" aria-label="${label("edRemoveColumn")}"
             >×</button>`,
          0,
          i,
          "named",
        ),
      )
      .join("");

  const settings =
    '<span class="ref" data-r="1">2</span>' +
    cell(
      `<input data-edit="marker" value="${escapeHtml(state.marker)}"
         spellcheck="false" autocomplete="off" aria-label="${label("edDeckCell")}">`,
      1,
      -1,
      `marker${deckActive() ? " on" : ""}`,
    ) +
    cols
      .map((c, i) =>
        cell(
          `<textarea data-edit="cell" data-col="${i}" rows="1" spellcheck="false"
             autocomplete="off" aria-label="${label("edCell")}"
             >${escapeHtml(c.cell)}</textarea>`,
          1,
          i,
          state.active === i ? "on" : "",
        ),
      )
      .join("");

  const values =
    '<span class="ref" data-r="2">3</span>' +
    cell("1", 2, -1, "fixed") +
    cols
      .map((c, i) =>
        cell(
          `<input data-edit="value" data-col="${i}" value="${escapeHtml(c.value)}"
             spellcheck="false" autocomplete="off" aria-label="${label("edValue")}">`,
          2,
          i,
        ),
      )
      .join("");

  const sheet = $("#sheet");
  sheet.style.setProperty("--cols", String(cols.length));
  sheet.innerHTML = head + names + settings + values;
  for (const box of sheet.querySelectorAll("textarea")) grow(box);
  // The grid is rebuilt from scratch whenever its shape changes, so the selection
  // has to be drawn back on afterwards rather than living in the markup above.
  paintSelection();
}

// ---------------------------------------------------------------------------
// A range of cells, the way a spreadsheet has one
// ---------------------------------------------------------------------------
//
// The editor is shaped like a sheet, so it has to behave like one where it costs
// nothing: drag across cells to select them, Ctrl+C to take them, Ctrl+V to put
// them back. Nothing here is a grid library — three rows is not enough sheet to
// hand the whole editing model over to one, and a canvas-drawn grid would lose
// the inputs, the labels and every bit of the keyboard support that comes free
// with them. What it is instead: the inputs stop swallowing the pointer unless
// the cell is being edited (`.cell.editing input`), so an ordinary drag lands on
// the cells and can be read as a range.
//
// Rows are 0, 1, 2 — the names, the settings row, the one row of data — and
// column -1 is column A. A cell is only ever those two numbers.
const LAST_ROW = 2;

/** What is in one cell, wherever it lives. */
function cellAt(r, c) {
  if (c === -1) return r === 0 ? "ID" : r === 1 ? state.marker : "1";
  const col = state.columns[c];
  if (!col) return "";
  return r === 0 ? col.name : r === 1 ? col.cell : col.value;
}

/** Writes one cell, ignoring the two that are not the sheet's to write. */
function writeCell(r, c, text) {
  if (c === -1) {
    if (r === 1) state.marker = text;
    return;
  }
  const col = state.columns[c];
  if (!col) return;
  if (r === 0) col.name = text;
  else if (r === 1) col.cell = text;
  else col.value = text;
}

/** The selection as ordered bounds, or null. Dragging upwards is still a range. */
function bounds() {
  const s = state.sel;
  if (!s) return null;
  return {
    r1: Math.min(s.r, s.r2),
    r2: Math.max(s.r, s.r2),
    c1: Math.min(s.c, s.c2),
    c2: Math.max(s.c, s.c2),
  };
}

/**
 * Moves or extends the selection.
 *
 * The anchor is where the drag (or the click) started, because that is what a
 * shift-click extends from. Selecting also blurs whatever was being edited: the
 * keyboard belongs to the grid while a range is up, and a caret still sitting in
 * a cell would take the arrow keys instead.
 */
function select(r, c, extend = false) {
  const at = {
    r: Math.max(0, Math.min(LAST_ROW, r)),
    c: Math.max(-1, Math.min(state.columns.length - 1, c)),
  };
  if (extend && state.sel) state.sel = { ...state.sel, r2: at.r, c2: at.c };
  else state.sel = { r: at.r, c: at.c, r2: at.r, c2: at.c };

  stopEditing();
  paintSelection();

  // The directive chips act on whichever cell the selection is anchored in, the
  // same as they follow the cursor while typing — one answer to "which column am
  // I changing", however the column was picked.
  const active = state.sel.c;
  if (active !== state.active) {
    state.active = active;
    paintKeys();
  }
}

function clearSelection() {
  if (!state.sel) return;
  state.sel = null;
  paintSelection();
}

/** Draws the range. Called after every repaint, since the markup carries none. */
function paintSelection() {
  const box = bounds();
  const sheet = $("#sheet");
  sheet.classList.toggle("ranged", Boolean(box));
  for (const el of sheet.querySelectorAll(".cell")) {
    const r = Number(el.dataset.r);
    const c = Number(el.dataset.c);
    const inside =
      box && r >= box.r1 && r <= box.r2 && c >= box.c1 && c <= box.c2;
    el.classList.toggle("sel", Boolean(inside));
    el.classList.toggle("anchor", Boolean(state.sel?.r === r && state.sel?.c === c));
    // The border a spreadsheet draws is around the *range*, not around each cell
    // in it, and CSS cannot see a neighbour — so each cell is told which of its
    // sides is on the outside of the block.
    el.classList.toggle("edge-t", Boolean(inside && r === box.r1));
    el.classList.toggle("edge-b", Boolean(inside && r === box.r2));
    el.classList.toggle("edge-l", Boolean(inside && c === box.c1));
    el.classList.toggle("edge-r", Boolean(inside && c === box.c2));
  }
  for (const el of sheet.querySelectorAll(".ref")) {
    const r = el.dataset.r === undefined ? null : Number(el.dataset.r);
    const c = el.dataset.c === undefined ? null : Number(el.dataset.c);
    const lit =
      box &&
      ((r !== null && r >= box.r1 && r <= box.r2) ||
        (c !== null && c >= box.c1 && c <= box.c2));
    el.classList.toggle("sel", Boolean(lit));
  }

  // The little square on the bottom-right corner of a range. One element moved
  // from cell to cell rather than one per cell: it is the same handle wherever
  // the selection goes, and a handle left behind in an old corner is the kind of
  // thing that gets dragged by accident.
  if (box) {
    const corner = sheet.querySelector(`.cell[data-r="${box.r2}"][data-c="${box.c2}"]`);
    corner?.append(FILL_HANDLE);
  } else {
    FILL_HANDLE.remove();
  }
}

const FILL_HANDLE = Object.assign(document.createElement("span"), {
  className: "fill",
  title: "",
});

/** Hands one cell to the keyboard, with its text selected so typing replaces it. */
function startEditing(r, c) {
  const cell = $(`#sheet .cell[data-r="${r}"][data-c="${c}"]`);
  const box = cell?.querySelector("[data-edit]");
  if (!box) return false;
  state.editing = { r, c };
  for (const el of document.querySelectorAll("#sheet .cell.editing")) {
    el.classList.remove("editing");
  }
  cell.classList.add("editing");
  box.focus();
  box.select();
  return true;
}

function stopEditing() {
  if (!state.editing) return;
  state.editing = null;
  // Leaving a cell ends the run, so coming back to it starts a new undo step.
  session = null;
  for (const el of document.querySelectorAll("#sheet .cell.editing")) {
    el.classList.remove("editing");
  }
  if (document.activeElement?.closest?.("#sheet")) document.activeElement.blur();
}

/**
 * The selected cells as a spreadsheet would put them on the clipboard.
 *
 * Quoted the same way `parseBlock` un-quotes them, so a settings cell holding a
 * line break survives the round trip out of here and back in.
 */
function selectionTsv() {
  const box = bounds();
  if (!box) return "";
  const quote = (value) =>
    /[\t\n"]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
  const rows = [];
  for (let r = box.r1; r <= box.r2; r++) {
    const row = [];
    for (let c = box.c1; c <= box.c2; c++) row.push(quote(cellAt(r, c)));
    rows.push(row.join("\t"));
  }
  return rows.join("\n");
}

/** Keeps a settings cell exactly as tall as what is in it. */
function grow(box) {
  box.style.height = "auto";
  box.style.height = `${box.scrollHeight}px`;
}

function paintKeys() {
  const on = activeKeys();
  const list = deckActive() ? keys.deck : keys.field;
  if (state.open && !list.includes(state.open)) state.open = null;

  $("#keys").innerHTML = list
    .map(
      (key) =>
        `<button class="col${on.has(key) ? " on" : ""}` +
        `${state.open === key ? " open" : ""}" data-key="${escapeHtml(key)}"` +
        ` aria-pressed="${on.has(key)}">${escapeHtml(key)}</button>`,
    )
    .join("");
  $("#keyfor").textContent = deckActive()
    ? t("edForDeck")
    : t("edForColumn", state.columns[state.active]?.name || "");
  paintOptions();
}

/**
 * The values on offer for the open directive.
 *
 * Inline under the chips rather than floating over them: a popover on a phone
 * covers the row you were choosing from, and there is nowhere for it to go.
 */
function paintOptions() {
  const key = state.open;
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
  const sample = help?.sample;

  box.innerHTML = `${
    help ? `<p class="opthelp">${escapeHtml(t(help.text))}</p>` : ""
  }${
    sample
      ? `<p class="optsample"><button class="col" id="optsample" type="button"
           >${escapeHtml(t("edSample"))}</button>
           <code>${escapeHtml(sample)}</code></p>`
      : ""
  }<p class="optbar"><b class="mono">${escapeHtml(key)}</b>
      ${listed
        .map(
          (v) =>
            `<button class="col${current === v ? " on" : ""}" data-opt="${escapeHtml(v)}"` +
            `${swatch(v)}>${escapeHtml(v || t("edOther"))}</button>`,
        )
        .join("")}
      ${
        keys.closed?.[key] || !valued(key)
          ? ""
          : `<input id="optfree" value="${escapeHtml(current ?? "")}"
               spellcheck="false" autocomplete="off"
               placeholder="${escapeHtml(t("edOther"))}"
               aria-label="${escapeHtml(t("edOther"))}">`
      }
      <button class="drop" id="optdrop" type="button"
        title="${escapeHtml(t("edRemoveKey"))}"
        aria-label="${escapeHtml(t("edRemoveKey"))}">×</button></p>`;
}

/** The card these columns make, from the templates the add-on would write. */
function draw() {
  paintKeys();
  drawCard();
}

/** Everything downstream of the cells: the warnings, the card, the split. */
function drawCard() {
  if (!run) return;

  let out;
  try {
    out = run(JSON.stringify({ marker: state.marker, columns: state.columns }));
  } catch (err) {
    return status(String(err?.message || err).trim().split("\n").pop(), "bad");
  }

  const warnings = out.warnings || [];
  $("#warn").hidden = !warnings.length;
  $("#warnlist").innerHTML = warnings
    .map((w) => `<li>${escapeHtml(w)}</li>`)
    .join("");
  status(
    !out.isConfig
      ? t("edNoMarker")
      : warnings.length
        ? t("edRefused", warnings.length)
        : t("edOk"),
    !out.isConfig || warnings.length ? "bad" : "ok",
  );

  drawDeck(out);

  const index = Math.min(state.template, out.templates.length - 1);
  const template = out.templates[index];
  const values = { ID: "1" };
  out.names.forEach((name, i) => (values[name] = state.columns[i].value));
  const { front, back } = renderCard(template, values, { ordinal: 1 });

  $("#tabs").innerHTML = CARD_TABS.map(
    (name) =>
      `<button data-tab="${name}" class="${state.tab === name ? "on" : ""}">` +
      `${escapeHtml(t("tab" + name[0].toUpperCase() + name.slice(1)))}</button>`,
  ).join("");

  const picker =
    out.templates.length > 1
      ? `<div class="cardbar"><select id="tpl" aria-label="${escapeHtml(
          t("edTemplate"),
        )}">${out.templates
          .map(
            (tpl, i) =>
              `<option value="${i}" ${i === index ? "selected" : ""}>` +
              `${escapeHtml(tpl.name)}</option>`,
          )
          .join("")}</select></div>`
      : "";

  // The template is the exact text the add-on writes into Anki; the picture of
  // it is this page's approximation. Showing the source beside the card is the
  // only way to tell which of the two you are looking at.
  if (state.tab === "template") {
    $("#view").innerHTML = `<div class="stagebox">${picker}
      <h2 class="src-head">${escapeHtml(t("frontTemplate"))}</h2>
      <pre class="source">${escapeHtml(template.qfmt)}</pre>
      <h2 class="src-head">${escapeHtml(t("backTemplate"))}</h2>
      <pre class="source">${escapeHtml(template.afmt)}</pre>
    </div>`;
    return;
  }

  const doc = cardDoc({ front, back, tab: state.tab, dark: dark() });

  $("#view").innerHTML = `<div class="stagebox">${picker}
    ${cardFrame(doc)}
    <p class="muted small">${escapeHtml(
      t("edSides", out.front.length, out.back.length),
    )}</p>
  </div>`;
}

/**
 * Where row 3 lands, and under what tags.
 *
 * The card is only half of what a settings row decides: `subdeck=n` files the note
 * and never touches the card, so a column carrying it looked inert here. It also
 * shows the row landing in `Unsorted` when it names no level, which is a thing that
 * happens to a sheet rather than a thing a sheet asked for. Beside the card rather
 * than as a fifth tab, because it is not a view of the card — it is the other half
 * of the answer.
 *
 * The root is named for what it is rather than guessed at: the real one comes
 * from the file and the sheet, and this editor has neither. Only the levels below
 * it are this settings row's doing, so only they are shown as the sheet's own
 * words.
 */
function drawDeck(out) {
  const levels = out.deck || [];
  const tags = out.tags || [];

  // The preview page's own tree, from this page's one row of data: the same
  // component, so a deck looks like a deck on both pages. `pick` is off — there is
  // nothing here to filter down to.
  const rows = [{ kind: "synced", deck: [t("edDeckRoot"), ...levels].join("::") }];

  $("#deck").innerHTML =
    `<ul class="tree">${treeHtml(deckTree(rows))}</ul>` +
    `<p class="tagline"><b>${escapeHtml(t("edTags"))}</b>${tags
      .map((tag) => `<code>${escapeHtml(tag)}</code>`)
      .join("")}</p>`;
}

/**
 * The two rows that are worth taking away: the headers and the settings row.
 *
 * Row 3 is sample data — a card to look at while editing, not something anyone
 * wants pasted into their sheet.
 */
function rows() {
  return [
    ["ID", ...state.columns.map((c) => c.name)],
    [state.marker, ...state.columns.map((c) => c.cell)],
  ];
}

/** Tab-separated, which is what Sheets and Excel split a pasted block on. */
function asTsv() {
  return rows()
    .map((row) => row.join("\t"))
    .join("\n");
}

/**
 * The same two rows as a file both spreadsheets open by double-clicking.
 *
 * Quoted per RFC 4180 rather than joined with commas: a settings cell is full of
 * them already (`voices=Ting-Ting,Huihui`), and a bare join would spread one
 * cell across three.
 */
function asCsv() {
  const quote = (value) =>
    /[",\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value;
  // Excel reads a .csv as the machine's own encoding unless the file says
  // otherwise, and a byte order mark is the only thing it takes as saying so.
  return `\uFEFF${rows()
    .map((row) => row.map(quote).join(","))
    .join("\r\n")}`;
}

/**
 * A block copied out of Sheets or Excel, split back into rows of cells.
 *
 * The clipboard hands over TSV: tabs between cells, newlines between rows, and a
 * cell containing either of those wrapped in quotes with its own quotes doubled.
 * Walked character by character rather than split on tabs, because a settings cell
 * is exactly the kind of cell that arrives quoted — and a sentence in row 3 with a
 * line break in it would otherwise become two rows.
 */
function parseBlock(text) {
  const rows = [[""]];
  let quoted = false;
  const push = (ch) => {
    const row = rows[rows.length - 1];
    row[row.length - 1] += ch;
  };

  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch !== '"') push(ch);
      else if (text[i + 1] === '"') (push('"'), i++);
      else quoted = false;
      continue;
    }
    const row = rows[rows.length - 1];
    if (ch === '"' && row[row.length - 1] === "") quoted = true;
    else if (ch === "\t") row.push("");
    else if (ch === "\n") rows.push([""]);
    else if (ch !== "\r") push(ch);
  }

  // A selection dragged to the end of a sheet ends in a newline.
  const last = rows[rows.length - 1];
  if (rows.length > 1 && last.length === 1 && last[0] === "") rows.pop();
  return rows;
}

/** True for the ``#config`` cell, by the same rule ``sheet_config`` uses. */
const isMarkerCell = (cell) => /^\s*#config(\W|$)/i.test(cell ?? "");

/**
 * True when every filled cell in the row is made of directives.
 *
 * The marker cell is what normally identifies the settings row, so this is only
 * asked when column A was left out of the selection — copying B1:D2 out of a sheet
 * gives you a settings row with nothing to recognise it by. The directive names
 * come from `sheet_config.py` via `keys`, so it is the add-on's own list doing the
 * recognising rather than a second list kept here.
 */
function looksLikeSettings(row) {
  const filled = (row ?? []).filter((cell) => cell.trim());
  if (!filled.length || !keys.field?.length) return false;
  return filled.every((cell) =>
    parts(cell).every((part) => keys.field.includes(nameOf(part))),
  );
}

/**
 * Reads a pasted block into the sheet.
 *
 * A selection out of a spreadsheet is some of row 1, row 2 and row 3, in that
 * order, with any of them missing — so the rows are identified rather than
 * counted: the settings row by its marker (or by being nothing but directives),
 * and column A by the reserved `ID` header. What is left is columns.
 *
 * With a header row the block replaces the sheet, because the columns it names are
 * the sheet. Without one it fills the columns already here from the left, which is
 * what pasting one row back over another means.
 *
 * Returns null when there was nothing to read, and otherwise how many rows of the
 * block went unused — this page shows one row of data, and a whole sheet pasted in
 * has to say that the other forty rows were not lost, only not shown.
 */
function applyBlock(block) {
  const rows = block.filter((row) => row.some((cell) => cell.trim()));
  if (!rows.length) return null;

  const marked = rows.findIndex((row) => isMarkerCell(row[0]));
  let names = null;
  let cells = null;
  let values = null;

  if (marked === 0) {
    [cells, values] = [rows[0], rows[1] ?? null];
  } else if (marked > 0) {
    [names, cells, values] = [rows[0], rows[marked], rows[marked + 1] ?? null];
  } else if (looksLikeSettings(rows[0])) {
    [cells, values] = [rows[0], rows[1] ?? null];
  } else if (looksLikeSettings(rows[1])) {
    [names, cells, values] = [rows[0], rows[1], rows[2] ?? null];
  } else {
    [names, values] = [rows[0], rows[1] ?? null];
  }

  // Column A holds the ID and the marker, and it is either in the selection or it
  // is not. Taking it for a content column would put a column called "ID" on every
  // card, which is the one column Anki already keeps for itself.
  if (cells ? isMarkerCell(cells[0]) : /^\s*id\s*$/i.test(names?.[0] ?? "")) {
    if (cells) state.marker = cells[0].trim();
    for (const row of [names, cells, values]) row?.shift();
  }

  const at = (row, i) => row?.[i] ?? "";
  let read = 0;
  if (names) {
    const width = Math.max(names.length, cells?.length ?? 0, values?.length ?? 0);
    const columns = [];
    for (let i = 0; i < width; i++) {
      const name = at(names, i).trim();
      // A column with nothing in it anywhere is the empty part of a dragged
      // selection, not a column somebody meant to make.
      if (!name && !at(cells, i).trim() && !at(values, i).trim()) continue;
      columns.push({
        name: name || `Column ${columns.length + 1}`,
        cell: at(cells, i).trim(),
        value: at(values, i),
      });
    }
    if (!columns.length) return null;
    state.columns = columns;
    read = columns.length;
  } else {
    const width = Math.max(cells?.length ?? 0, values?.length ?? 0);
    if (!width) return null;
    read = width;
    for (let i = 0; i < width; i++) {
      state.columns[i] ??= { name: `Column ${i + 1}`, cell: "", value: "" };
      if (cells) state.columns[i].cell = at(cells, i).trim();
      if (values) state.columns[i].value = at(values, i);
    }
  }

  if (state.active >= state.columns.length) state.active = 0;

  const skipped = marked > 1 ? marked - 1 : 0;
  const kept = [names, cells, values].filter(Boolean).length + skipped;
  return { columns: read, dropped: Math.max(0, rows.length - kept) };
}

/**
 * Writes a block into the grid starting at the selected cell.
 *
 * This is what pasting means once a cell has been picked: put it *here*. The
 * shape-guessing in `applyBlock` is for the other case — a block arriving with no
 * target, which is someone bringing a sheet in rather than filling cells.
 *
 * A block wider than the sheet grows it, because that is what the paste asked for.
 * Taller than three rows it cannot grow: there is one row of data here.
 */
function pasteAt(block) {
  const anchor = state.sel;
  if (!anchor) return null;
  let dropped = 0;
  let widest = 0;

  block.forEach((cells, dr) => {
    const r = anchor.r + dr;
    if (r > LAST_ROW) {
      dropped++;
      return;
    }
    cells.forEach((text, dc) => {
      const c = anchor.c + dc;
      if (c < -1) return;
      while (c >= state.columns.length) {
        state.columns.push({
          name: `Column ${state.columns.length + 1}`,
          cell: "",
          value: "",
        });
      }
      writeCell(r, c, r === 2 ? text : text.trim());
      widest = Math.max(widest, dc + 1);
    });
  });

  return { columns: widest, dropped };
}

function download(text, name) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/csv" }));
  const link = Object.assign(document.createElement("a"), { href: url, download: name });
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------

document.addEventListener("click", (e) => {
  const item = e.target.closest("[data-menu]");
  if (item) return runMenu(item.dataset.menu);
  closeMenu();

  if (e.target.closest("#theme")) return setTheme(!dark());

  const tab = e.target.closest("[data-tab]");
  if (tab) {
    state.tab = tab.dataset.tab;
    return drawCard();
  }

  const picker = e.target.closest("[data-lang]");
  if (picker) {
    setLang(picker.dataset.lang);
    paintChrome();
    paintSheet();
    return draw();
  }

  const key = e.target.closest("[data-key]");
  if (key) {
    mark();
    const name = key.dataset.key;
    // A flag has nothing to choose, so the tap still does the whole job — but it
    // also opens the panel, because `cloze` and `furigana` switched on with no
    // word about them is where people give up. One that takes a value only
    // opens: inserting blind is what the options are there to replace.
    if (!valued(name)) setCell(toggle(cellText(), name));
    state.open = state.open === name && valued(name) ? null : name;
    paintSheet();
    return draw();
  }

  const opt = e.target.closest("[data-opt]");
  if (opt) {
    mark();
    setCell(toggle(cellText(), state.open, opt.dataset.opt));
    paintSheet();
    return draw();
  }

  if (e.target.closest("#optsample")) {
    mark();
    const at = deckActive() ? 0 : state.active;
    state.columns[at].value = HELP[state.open].sample;
    paintSheet();
    return draw();
  }

  if (e.target.closest("#optdrop")) {
    mark();
    setCell(
      parts(cellText())
        .filter((part) => nameOf(part) !== state.open)
        .join("; "),
    );
    paintSheet();
    return draw();
  }

  const drop = e.target.closest("[data-drop]");
  if (drop) {
    // One column has to survive: a sheet with none has nothing to put on a card.
    if (state.columns.length > 1) {
      mark();
      state.columns.splice(Number(drop.dataset.drop), 1);
      state.active = Math.min(Math.max(state.active, 0), state.columns.length - 1);
      paintSheet();
      draw();
    }
    return;
  }

  if (e.target.closest("#add")) {
    mark();
    state.columns.push({
      name: `Column ${state.columns.length + 1}`,
      cell: "",
      value: "",
    });
    state.active = state.columns.length - 1;
    paintSheet();
    return draw();
  }

  if (e.target.closest("#export")) {
    download(asCsv(), "settings-row.csv");
    return status(t("edExported"), "ok");
  }

  if (e.target.closest("#copy")) {
    // Whatever is selected, or the two rows worth taking away when nothing is.
    // On a phone there is no Ctrl+C, so this button is the only way a range that
    // was picked by tapping a column letter can leave the page.
    navigator.clipboard
      ?.writeText(state.sel ? selectionTsv() : asTsv())
      .then(() => status(t(state.sel ? "edCopiedCells" : "edCopied"), "ok"))
      .catch(() => status(t("edCopyFailed"), "bad"));
  }
});

/**
 * A block pasted anywhere on the page is the sheet, not one cell's worth of text.
 *
 * This is the way back in: the settings row is written here, copied into Sheets,
 * and then a week later it needs another column — at which point the sheet is the
 * one with the current version of it and this page has to be able to take it back.
 * Without this the only way to edit an existing row here was to retype it.
 *
 * One cell's worth of text — no tab, no line break — is left alone, because it
 * belongs to whichever input has the cursor.
 */
document.addEventListener("paste", (e) => {
  const text = e.clipboardData?.getData("text/plain") ?? "";
  const block = parseBlock(text);
  // Taken before the block is applied and only remembered if it was, so a paste
  // that turned out to be nothing does not cost a press of Ctrl+Z.
  const before = sheetState();
  // A cell has been picked, so the paste goes there — one cell's worth included,
  // which is the whole point of having picked it. Editing a cell is the exception:
  // then the caret has the clipboard, the same as in any other text box.
  const read =
    state.sel && !state.editing
      ? pasteAt(block)
      : /[\t\n]/.test(text)
        ? applyBlock(block)
        : null;
  if (!read) return;
  e.preventDefault();
  commit(before);
  paintSheet();
  draw();
  // After draw(), which sets the status from what the settings row turned out to
  // say. This is the reply to the paste itself, and it is the more useful of the
  // two the moment a whole sheet has just arrived.
  status(
    read.dropped
      ? t("edPastedSome", read.columns, read.dropped)
      : t("edPasted", read.columns),
    "ok",
  );
});

// The sheet is rebuilt whenever its shape changes, so its inputs are reached by
// delegation rather than wired up again each time.
$("#opts").addEventListener("input", (e) => {
  if (e.target.id !== "optfree") return;
  markRun(`opt:${state.open}`);
  setCell(toggle(cellText(), state.open, e.target.value.trim()));
  paintSheet();
  // Redrawn without repainting the options, so the box keeps the cursor in it.
  drawCard();
});

$("#sheet").addEventListener("input", (e) => {
  const el = e.target.closest("[data-edit]");
  if (!el) return;
  markRun(`cell:${el.dataset.edit}:${el.dataset.col ?? "marker"}`);
  if (el.dataset.edit === "marker") state.marker = el.value;
  else state.columns[Number(el.dataset.col)][el.dataset.edit] = el.value;
  if (el.tagName === "TEXTAREA") grow(el);
  draw();
});

// ---------------------------------------------------------------------------
// Selecting: pointer, keyboard, clipboard
// ---------------------------------------------------------------------------

let dragging = false;
// The range the fill started from, while its handle is being dragged.
let filling = null;

/**
 * Copies a range across the cells it was dragged over.
 *
 * The rule is the spreadsheet's: the source block repeats to cover the target, so
 * dragging one cell across four fills all four with it, and dragging a pair
 * alternates them. Written as one modulo rather than as a case for each direction,
 * which is also why dragging back over the source leaves it exactly as it was.
 */
function fillFrom(src, box) {
  const height = src.r2 - src.r1 + 1;
  const width = src.c2 - src.c1 + 1;
  for (let r = box.r1; r <= box.r2; r++) {
    for (let c = box.c1; c <= box.c2; c++) {
      if (r >= src.r1 && r <= src.r2 && c >= src.c1 && c <= src.c2) continue;
      const from = {
        r: src.r1 + ((r - src.r1) % height + height) % height,
        c: src.c1 + ((c - src.c1) % width + width) % width,
      };
      writeCell(r, c, cellAt(from.r, from.c));
    }
  }
}

/**
 * A press on the grid: on the refs it takes a whole column or row, on a cell it
 * starts a range.
 *
 * Touch is left alone deliberately. There is no drag-select on a phone — the
 * gesture is already how the grid scrolls sideways — so a tap goes straight to
 * typing, which is what it did before any of this existed. Selecting a column by
 * its letter still works there, and the copy button takes whatever is selected,
 * so the phone keeps the whole feature without the gesture.
 */
$("#sheet").addEventListener("pointerdown", (e) => {
  if (e.target === FILL_HANDLE) {
    // Not a new selection: the handle belongs to the one already there.
    e.preventDefault();
    filling = bounds();
    return;
  }

  const ref = e.target.closest(".ref");
  if (ref) {
    e.preventDefault();
    if (ref.dataset.all !== undefined) {
      select(0, -1);
      select(LAST_ROW, state.columns.length - 1, true);
    } else if (ref.dataset.c !== undefined) {
      select(0, Number(ref.dataset.c));
      select(LAST_ROW, Number(ref.dataset.c), true);
    } else if (ref.dataset.r !== undefined) {
      select(Number(ref.dataset.r), -1);
      select(Number(ref.dataset.r), state.columns.length - 1, true);
    }
    return;
  }

  const cell = e.target.closest(".cell");
  if (!cell || e.target.closest(".drop")) return;
  const [r, c] = [Number(cell.dataset.r), Number(cell.dataset.c)];

  if (e.pointerType === "touch") {
    // The inputs do not take the pointer any more, so a tap has to be handed the
    // cell on purpose. Done inside the gesture, which is what makes the phone's
    // keyboard come up.
    clearSelection();
    startEditing(r, c);
    return;
  }
  // Already editing this cell: the press is someone placing the caret in the text
  // they are writing, not the start of a new selection.
  if (state.editing?.r === r && state.editing?.c === c) return;

  e.preventDefault();
  select(r, c, e.shiftKey);
  dragging = true;
});

$("#sheet").addEventListener("pointermove", (e) => {
  const cell = e.target.closest(".cell");
  if (!cell) return;
  const [r, c] = [Number(cell.dataset.r), Number(cell.dataset.c)];

  // While filling, the range grows to show what is about to be written into —
  // the same tinted block, because that is exactly what it will hold.
  if (filling) {
    state.sel = {
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
  // Nothing was dragged over, so there is nothing to fill and nothing to undo.
  if (box.r1 === src.r1 && box.r2 === src.r2 && box.c1 === src.c1 && box.c2 === src.c2) {
    return;
  }
  mark();
  fillFrom(src, box);
  paintSheet();
  draw();
});

$("#sheet").addEventListener("contextmenu", (e) => {
  const cell = e.target.closest(".cell");
  if (!cell) return;
  e.preventDefault();
  const [r, c] = [Number(cell.dataset.r), Number(cell.dataset.c)];
  // Right-clicking outside the selection moves it there first, the way it does in
  // a spreadsheet: the menu acts on what is highlighted, so what is highlighted
  // has to be what was just pointed at.
  const box = bounds();
  const inside = box && r >= box.r1 && r <= box.r2 && c >= box.c1 && c <= box.c2;
  if (!inside) select(r, c);
  openMenu(e.clientX, e.clientY);
});

// A second click is how a spreadsheet asks for the caret. So is Enter, below.
$("#sheet").addEventListener("dblclick", (e) => {
  const cell = e.target.closest(".cell");
  if (cell) startEditing(Number(cell.dataset.r), Number(cell.dataset.c));
});

/**
 * The menu a spreadsheet opens on right-click.
 *
 * Everything in it can already be done another way — the "+" adds a column, the
 * "×" removes one, Delete empties a range — but not *here*, at the cell being
 * looked at, which is where a hand already is. Adding a column between two others
 * had no other way at all: the "+" only ever appends.
 */
const MENU = ["left", "right", "drop", "clear"];
const MENU_LABEL = {
  left: "edInsertLeft",
  right: "edInsertRight",
  drop: "edRemoveColumn",
  clear: "edClearCells",
};

function blankColumn() {
  return { name: "", cell: "", value: "" };
}

function closeMenu() {
  document.getElementById("cellmenu")?.remove();
}

/** Opens the menu at the pointer, kept inside the window. */
function openMenu(x, y) {
  closeMenu();
  const el = document.createElement("div");
  el.id = "cellmenu";
  el.className = "menu";
  el.style.left = `${x}px`;
  el.style.top = `${y}px`;
  el.innerHTML = MENU.map(
    (id) =>
      `<button data-menu="${id}"${
        id === "drop" && state.columns.length < 2 ? " disabled" : ""
      }>${escapeHtml(t(MENU_LABEL[id]))}</button>`,
  ).join("");
  document.body.append(el);

  const box = el.getBoundingClientRect();
  if (box.right > innerWidth) {
    el.style.left = `${Math.max(4, innerWidth - box.width - 4)}px`;
  }
  if (box.bottom > innerHeight) el.style.top = `${Math.max(4, y - box.height)}px`;
}

/** Carries out one item of the menu, on the cell it was opened over. */
function runMenu(id) {
  const at = state.sel;
  if (!at) return;
  mark();

  if (id === "clear") {
    const box = bounds();
    for (let r = box.r1; r <= box.r2; r++) {
      for (let c = box.c1; c <= box.c2; c++) writeCell(r, c, "");
    }
  } else if (id === "drop") {
    if (state.columns.length < 2 || at.c < 0) return;
    state.columns.splice(at.c, 1);
    state.active = Math.min(Math.max(state.active, 0), state.columns.length - 1);
    state.sel = null;
  } else {
    // Column A is the sheet's own; a column asked for beside it goes first.
    const where = at.c < 0 ? 0 : id === "left" ? at.c : at.c + 1;
    state.columns.splice(where, 0, blankColumn());
    select(at.r, where);
  }

  closeMenu();
  paintSheet();
  draw();
}

/**
 * The keyboard while a range is up: move it, extend it, empty it, or start typing.
 *
 * Nothing here fires while a cell is being edited except Escape and Enter, which
 * hand the keyboard back — the caret has to keep the arrow keys, or a word cannot
 * be corrected in the middle.
 */
document.addEventListener("keydown", (e) => {
  const cmd = e.ctrlKey || e.metaKey;

  if (state.editing) {
    if (e.key === "Escape") {
      const { r, c } = state.editing;
      stopEditing();
      select(r, c);
    } else if (e.key === "Enter" && e.target.tagName !== "TEXTAREA") {
      const { r, c } = state.editing;
      stopEditing();
      select(Math.min(LAST_ROW, r + 1), c);
    }
    return;
  }

  // Some other input has the keyboard — the free-text box beside the options, say.
  // Its own undo is the browser's, and taking Ctrl+Z off it would be worse than
  // not having one here at all.
  if (document.activeElement?.matches?.("input, textarea, select")) return;

  // Undo works with nothing selected: the action being taken back is often the
  // one that cleared the selection.
  if (cmd && (e.key === "z" || e.key === "Z") && !e.shiftKey) {
    e.preventDefault();
    if (restore(history.past, history.future)) status(t("edUndone"), "ok");
    return;
  }
  if (cmd && ((e.key === "z" || e.key === "Z") || e.key === "y" || e.key === "Y")) {
    e.preventDefault();
    if (restore(history.future, history.past)) status(t("edRedone"), "ok");
    return;
  }

  if (!state.sel) return;

  const { r, c } = state.sel;
  const step = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] }[
    e.key
  ];
  if (step) {
    e.preventDefault();
    if (e.shiftKey) {
      select(state.sel.r2 + step[0], state.sel.c2 + step[1], true);
      state.sel = { r, c, r2: state.sel.r2, c2: state.sel.c2 };
    } else {
      select(r + step[0], c + step[1]);
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
  if (e.key === "Escape") {
    closeMenu();
    return clearSelection();
  }

  if (e.key === "a" && (e.ctrlKey || e.metaKey)) {
    e.preventDefault();
    select(0, -1);
    return select(LAST_ROW, state.columns.length - 1, true);
  }

  if (e.key === "Delete" || e.key === "Backspace") {
    e.preventDefault();
    mark();
    const box = bounds();
    for (let row = box.r1; row <= box.r2; row++) {
      for (let col = box.c1; col <= box.c2; col++) writeCell(row, col, "");
    }
    paintSheet();
    return draw();
  }

  // Anything printable starts typing over the cell, which is the one spreadsheet
  // habit that has no substitute: reaching for Enter first is a step nobody takes.
  // The character is written in rather than left to the browser, because the input
  // is only focused halfway through this very event and where the keystroke lands
  // after that is not something to depend on.
  if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
    if (!startEditing(r, c)) return;
    e.preventDefault();
    const box = document.activeElement;
    // The same tag the input handler below uses, so this first character and the
    // rest of the word are one step. Marked with its own tag rather than with
    // `mark()`, which would end the run and make the second letter a step of its
    // own — undo would then take back "s" and leave "ize=20" behind.
    markRun(`cell:${box.dataset.edit}:${box.dataset.col ?? "marker"}`);
    box.value = e.key;
    writeCell(r, c, e.key);
    if (box.tagName === "TEXTAREA") grow(box);
    draw();
  }
});

/**
 * Ctrl+C, Ctrl+X and Ctrl+V over a range.
 *
 * The browser's own copy has nothing to copy — the cells are not text selected in
 * the document — so the range is written onto the clipboard by hand, as the TSV
 * that Sheets and Excel split back into cells.
 */
document.addEventListener("copy", (e) => {
  if (!state.sel || state.editing) return;
  e.preventDefault();
  e.clipboardData.setData("text/plain", selectionTsv());
  status(t("edCopiedCells"), "ok");
});

document.addEventListener("cut", (e) => {
  if (!state.sel || state.editing) return;
  e.preventDefault();
  e.clipboardData.setData("text/plain", selectionTsv());
  mark();
  const box = bounds();
  for (let r = box.r1; r <= box.r2; r++) {
    for (let c = box.c1; c <= box.c2; c++) writeCell(r, c, "");
  }
  paintSheet();
  draw();
  status(t("edCopiedCells"), "ok");
});

// Which cell the chips act on follows the cursor, so there is never a step
// between choosing a column and changing it.
$("#sheet").addEventListener("focusin", (e) => {
  const el = e.target.closest("[data-edit]");
  if (!el) return;
  const now = el.dataset.edit === "marker" ? -1 : Number(el.dataset.col);
  if (now === state.active) return;
  state.active = now;
  for (const box of document.querySelectorAll("#sheet .cell")) {
    box.classList.remove("on");
  }
  el.closest(".cell")?.classList.add("on");
  paintKeys();
});

document.addEventListener("change", (e) => {
  if (e.target.id !== "tpl") return;
  state.template = Number(e.target.value);
  draw();
});

addEventListener("message", (e) => {
  const frame = $("#card");
  const height = Number(e.data?.h);
  if (frame && height > 0) frame.style.height = `${Math.ceil(height)}px`;
});

paintChrome();
paintSheet();
status(t("booting"), "", true);
startPython(EDITOR, (step) =>
  status(t(step === "boot" ? "booting" : "loadingCode"), "", true),
)
  .then((py) => {
    keys = JSON.parse(py.globals.get("keys")());
    const fn = py.globals.get("preview");
    run = (payload) => JSON.parse(fn(payload));
    draw();
  })
  .catch((err) => status(t("bootFailed", err.message), "bad"));
