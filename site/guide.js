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
from s2a.column_model import plan_columns
from s2a.sheet_config import SheetConfig, is_config_row, parse_config_row


def keys():
    """The directive names, read off sheet_config so the two cannot drift."""
    from s2a.sheet_config import _DECK_KEYS, _FIELD_KEYS

    return json.dumps({"field": list(_FIELD_KEYS), "deck": list(_DECK_KEYS)})


def preview(payload):
    """The sheet, as a sync would read it.

    Built with plan_columns and parse_config_row rather than with anything
    written for this page, so a column here behaves exactly as the same column
    would in a real sheet — including when the marker cell has been typed over
    and row 2 has stopped being a settings row at all.
    """
    data = json.loads(payload)
    names, cells = [], {}
    for index, column in enumerate(data["columns"]):
        name = column["name"].strip() or "Column " + str(index + 1)
        # A repeated header is honoured once, which would silently drop a column
        # from the editor. Spaced apart so every column keeps a cell of its own.
        while name in names:
            name += " "
        names.append(name)
        cells[name] = column["cell"]

    plan = plan_columns(["ID"] + names)
    row = dict(cells)
    row["ID"] = data["marker"]

    config = parse_config_row(row, plan) if is_config_row(row, plan) else SheetConfig()
    front, back = split_sides(plan, config)
    return json.dumps(
        {
            "names": names,
            "isConfig": config.present,
            "warnings": config.warnings,
            "front": front,
            "back": back,
            "templates": build_templates(
                plan, config, is_cloze=bool(config.cloze_field)
            ),
        },
        ensure_ascii=False,
    )
`;

const $ = (sel) => document.querySelector(sel);

// What each directive is worth starting from. Not documentation — a seed, so one
// tap produces something that already works and can then be edited. The names
// come from Python; only these starting values live here.
const SEEDS = {
  side: "side=front",
  size: "size=32",
  color: "color=accent",
  align: "align=left",
  tts: "tts=zh_CN",
  voices: "voices=Ting-Ting",
  speed: "speed=0.9",
  label: "label=Meaning",
  type: "type",
  subdeck: "subdeck=1",
  theme: "theme=sakura",
};

const state = {
  marker: "#config",
  columns: [
    { name: "Word", cell: "size=44; bold", value: "北京" },
    { name: "Meaning", cell: "size=20; color=muted", value: "Bắc Kinh" },
  ],
  // Which cell the directive chips act on. A chip has to act on something, and
  // asking which column first would be a dialog in the way of a tap. -1 is the
  // marker cell, where the deck-wide settings live.
  active: 0,
  template: 0,
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
function toggle(cell, key) {
  const had = parts(cell).some((part) => nameOf(part) === key);
  const kept = parts(cell).filter((part) => nameOf(part) !== key);
  return (had ? kept : [...kept, SEEDS[key] ?? key]).join("; ");
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
  $("#keys").innerHTML = list
    .map(
      (key) =>
        `<button class="col${on.has(key) ? " on" : ""}" data-key="${escapeHtml(key)}"` +
        ` aria-pressed="${on.has(key)}">${escapeHtml(key)}</button>`,
    )
    .join("");
  $("#keyfor").textContent = deckActive()
    ? t("edForDeck")
    : t("edForColumn", state.columns[state.active]?.name || "");
}

/** The card these columns make, from the templates the add-on would write. */
function draw() {
  if (!run) return;
  paintKeys();

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

  const index = Math.min(state.template, out.templates.length - 1);
  const values = { ID: "1" };
  out.names.forEach((name, i) => (values[name] = state.columns[i].value));
  const { front, back } = renderCard(out.templates[index], values, { ordinal: 1 });

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
      button.tts { font: inherit; font-size: 14px; padding: 2px 10px;
                   border: 1px solid currentColor; border-radius: 999px;
                   background: transparent; color: inherit; opacity: .8; }
    </style>
    <body class="card${dark() ? " night_mode" : ""}">${front.html}
    <hr id="answer">${backOnly(back.html, front.html)}
    <script>
      const post = () => parent.postMessage(
        { h: document.documentElement.scrollHeight }, "*");
      addEventListener("load", post); new ResizeObserver(post).observe(document.body);
    <\/script>`;

  $("#view").innerHTML = `<div class="stagebox">
    ${
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
        : ""
    }
    <iframe id="card" title="Card preview"
            sandbox="allow-scripts allow-same-origin allow-popups allow-presentation"
            allow="fullscreen; encrypted-media; picture-in-picture; autoplay"
            srcdoc="${escapeHtml(doc)}"></iframe>
    <p class="muted small">${escapeHtml(
      t("edSides", out.front.length, out.back.length),
    )}</p>
  </div>`;
}

/** The answer side minus the repeated question, when the template used FrontSide. */
function backOnly(backHtml, frontHtml) {
  return backHtml.startsWith(frontHtml) ? backHtml.slice(frontHtml.length) : backHtml;
}

/** Row 2, tab-separated — which is what a spreadsheet accepts as a pasted row. */
function rowText() {
  return [state.marker, ...state.columns.map((c) => c.cell)].join("\t");
}

// ---------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------

document.addEventListener("click", (e) => {
  if (e.target.closest("#theme")) return setTheme(!dark());

  const picker = e.target.closest("[data-lang]");
  if (picker) {
    setLang(picker.dataset.lang);
    paintChrome();
    paintSheet();
    return draw();
  }

  const key = e.target.closest("[data-key]");
  if (key) {
    if (deckActive()) {
      const rest = toggle(state.marker.replace(/^\s*#config/i, ""), key.dataset.key);
      state.marker = `#config ${rest}`.trim();
    } else {
      const column = state.columns[state.active];
      column.cell = toggle(column.cell, key.dataset.key);
    }
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

  if (e.target.closest("#copy")) {
    navigator.clipboard
      ?.writeText(rowText())
      .then(() => status(t("edCopied"), "ok"))
      .catch(() => status(t("edCopyFailed"), "bad"));
  }
});

// The sheet is rebuilt whenever its shape changes, so its inputs are reached by
// delegation rather than wired up again each time.
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
