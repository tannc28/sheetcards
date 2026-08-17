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
  template: 0,
  tab: "both",
  // The directive whose options are showing, if any. One at a time: two open
  // panels on a phone is the list you were choosing from pushed off the screen.
  open: null,
};

let run = null;
let keys = { field: [], deck: [] };

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
  const cell = (inner, cls = "") => `<span class="cell ${cls}">${inner}</span>`;
  const label = (key) => escapeHtml(t(key));

  const head =
    '<span class="ref"></span><span class="ref">A</span>' +
    cols.map((_, i) => `<span class="ref">${letter(i + 1)}</span>`).join("");

  const names =
    '<span class="ref">1</span>' +
    cell("ID", "fixed") +
    cols
      .map((c, i) =>
        cell(
          `<input data-edit="name" data-col="${i}" value="${escapeHtml(c.name)}"
             spellcheck="false" autocomplete="off" aria-label="${label("edName")}">
           <button class="drop" data-drop="${i}" type="button"
             title="${label("edRemoveColumn")}" aria-label="${label("edRemoveColumn")}"
             >×</button>`,
          "named",
        ),
      )
      .join("");

  const settings =
    '<span class="ref">2</span>' +
    cell(
      `<input data-edit="marker" value="${escapeHtml(state.marker)}"
         spellcheck="false" autocomplete="off" aria-label="${label("edDeckCell")}">`,
      `marker${deckActive() ? " on" : ""}`,
    ) +
    cols
      .map((c, i) =>
        cell(
          `<textarea data-edit="cell" data-col="${i}" rows="1" spellcheck="false"
             autocomplete="off" aria-label="${label("edCell")}"
             >${escapeHtml(c.cell)}</textarea>`,
          state.active === i ? "on" : "",
        ),
      )
      .join("");

  const values =
    '<span class="ref">3</span>' +
    cell("1", "fixed") +
    cols
      .map((c, i) =>
        cell(
          `<input data-edit="value" data-col="${i}" value="${escapeHtml(c.value)}"
             spellcheck="false" autocomplete="off" aria-label="${label("edValue")}">`,
        ),
      )
      .join("");

  const sheet = $("#sheet");
  sheet.style.setProperty("--cols", String(cols.length));
  sheet.innerHTML = head + names + settings + values;
  for (const box of sheet.querySelectorAll("textarea")) grow(box);
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

  const doc = `<!doctype html><meta charset="utf-8">
    <style>
      html { color-scheme: ${dark() ? "dark" : "light"}; }
      body { margin: 0; padding: 18px; font-family: arial, sans-serif;
             font-size: 20px; text-align: center;
             color: ${dark() ? "#e6e9ee" : "#111"};
             background: ${dark() ? "#1b1f25" : "#fff"}; }
      hr#answer { margin: 16px 0; border: 0; border-top: 1px solid currentColor;
                  opacity: .25; }
      img, video, iframe { max-width: 100%; }
      a.hint { color: #2f6fd0; font-size: 15px; }
      .cloze { color: #2f6fd0; font-weight: 700; }
      button.tts { font: inherit; font-size: 14px; padding: 2px 10px; cursor: pointer;
                   border: 1px solid currentColor; border-radius: 999px;
                   background: transparent; color: inherit; opacity: .8; }
    </style>
    <body class="card${dark() ? " night_mode" : ""}">
    ${state.tab === "back" ? back.html : front.html}
    ${state.tab === "both" ? `<hr id="answer">${backOnly(back.html, front.html)}` : ""}
    <script>
      // The tts button speaks, here as on the preview page. Picking a language
      // and then finding the button inert would be the editor teaching that the
      // directive does nothing — and this is a real test of whether the machine
      // has a voice for the code that was chosen.
      document.addEventListener("click", (e) => {
        const b = e.target.closest("[data-tts]");
        if (!b) return;
        const spec = JSON.parse(b.dataset.tts);
        const say = new SpeechSynthesisUtterance(spec.text);
        say.lang = spec.lang.replace("_", "-");
        say.rate = Number(spec.speed) || 1;
        const want = new Set(spec.voices);
        const have = speechSynthesis.getVoices();
        say.voice = have.find((v) => want.has(v.name))
                 || have.find((v) => v.lang.replace("-", "_") === spec.lang) || null;
        speechSynthesis.cancel();
        speechSynthesis.speak(say);
      });
      const post = () => parent.postMessage(
        { h: document.documentElement.scrollHeight }, "*");
      addEventListener("load", post); new ResizeObserver(post).observe(document.body);
    <\/script>`;

  $("#view").innerHTML = `<div class="stagebox">${picker}
    <iframe id="card" title="Card preview"
            sandbox="allow-scripts allow-same-origin allow-popups allow-presentation"
            allow="fullscreen; encrypted-media; picture-in-picture; autoplay"
            srcdoc="${escapeHtml(doc)}"></iframe>
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
  const crumbs = [
    `<span class="muted">${escapeHtml(t("edDeckRoot"))}</span>`,
    ...levels.map((name) => `<span class="mono">${escapeHtml(name)}</span>`),
  ].join('<i aria-hidden="true">›</i>');

  $("#deck").innerHTML =
    `<span class="filed"><b>${escapeHtml(t("edFiledIn"))}</b>${crumbs}</span>` +
    `<span class="filed"><b>${escapeHtml(t("edTags"))}</b>${tags
      .map((tag) => `<code>${escapeHtml(tag)}</code>`)
      .join("")}</span>`;
}

/** The answer side minus the repeated question, when the template used FrontSide. */
function backOnly(backHtml, frontHtml) {
  return backHtml.startsWith(frontHtml) ? backHtml.slice(frontHtml.length) : backHtml;
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
  } else {
    const width = Math.max(cells?.length ?? 0, values?.length ?? 0);
    if (!width) return null;
    for (let i = 0; i < width; i++) {
      state.columns[i] ??= { name: `Column ${i + 1}`, cell: "", value: "" };
      if (cells) state.columns[i].cell = at(cells, i).trim();
      if (values) state.columns[i].value = at(values, i);
    }
  }

  if (state.active >= state.columns.length) state.active = 0;

  const skipped = marked > 1 ? marked - 1 : 0;
  const kept = [names, cells, values].filter(Boolean).length + skipped;
  return { dropped: Math.max(0, rows.length - kept) };
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
    setCell(toggle(cellText(), state.open, opt.dataset.opt));
    paintSheet();
    return draw();
  }

  if (e.target.closest("#optsample")) {
    const at = deckActive() ? 0 : state.active;
    state.columns[at].value = HELP[state.open].sample;
    paintSheet();
    return draw();
  }

  if (e.target.closest("#optdrop")) {
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
      state.columns.splice(Number(drop.dataset.drop), 1);
      state.active = Math.min(Math.max(state.active, 0), state.columns.length - 1);
      paintSheet();
      draw();
    }
    return;
  }

  if (e.target.closest("#add")) {
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
    navigator.clipboard
      ?.writeText(asTsv())
      .then(() => status(t("edCopied"), "ok"))
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
  if (!/[\t\n]/.test(text)) return;
  const read = applyBlock(parseBlock(text));
  if (!read) return;
  e.preventDefault();
  paintSheet();
  draw();
  // After draw(), which sets the status from what the settings row turned out to
  // say. This is the reply to the paste itself, and it is the more useful of the
  // two the moment a whole sheet has just arrived.
  status(
    read.dropped
      ? t("edPastedSome", state.columns.length, read.dropped)
      : t("edPasted", state.columns.length),
    "ok",
  );
});

// The sheet is rebuilt whenever its shape changes, so its inputs are reached by
// delegation rather than wired up again each time.
$("#opts").addEventListener("input", (e) => {
  if (e.target.id !== "optfree") return;
  setCell(toggle(cellText(), state.open, e.target.value.trim()));
  paintSheet();
  // Redrawn without repainting the options, so the box keeps the cursor in it.
  drawCard();
});

$("#sheet").addEventListener("input", (e) => {
  const el = e.target.closest("[data-edit]");
  if (!el) return;
  if (el.dataset.edit === "marker") state.marker = el.value;
  else state.columns[Number(el.dataset.col)][el.dataset.edit] = el.value;
  if (el.tagName === "TEXTAREA") grow(el);
  draw();
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
