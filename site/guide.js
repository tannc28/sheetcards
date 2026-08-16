/**
 * One column's settings row, and the card it makes.
 *
 * The reference for these directives is the README, and a copy of it here would
 * be a copy that drifts. This is the other way of documenting them: type one and
 * watch the card change. What a value has to look like is taught by the warning
 * you get when it does not — and that warning is the add-on's own sentence, from
 * the add-on's own `sheet_config.py`, not a paraphrase of it.
 *
 * One column rather than a whole row: a column is the unit people get stuck on,
 * and one column fits on a phone.
 */

import { renderCard, escapeHtml } from "./anki.js";
import { LANGUAGES, lang, setLang, t } from "./i18n.js";
import { startPython } from "./pyodide.js";

/** Everything the editor needs, computed by the add-on's own code. */
const EDITOR = String.raw`
import json
from s2a.card_layout import build_templates, split_sides
from s2a.column_model import plan_columns
from s2a.sheet_config import MEDIA_KINDS, parse_config_row


def keys():
    """The directive names, read off sheet_config so the two cannot drift."""
    from s2a.sheet_config import _FIELD_KEYS

    return json.dumps({"keys": list(_FIELD_KEYS), "media": list(MEDIA_KINDS)})


def preview(name, cell):
    """One column, as the sync would read it.

    The plan is ID plus this one column, which is the smallest sheet that parses,
    so everything below is the same code path a real sheet takes.
    """
    name = name.strip() or "Column"
    plan = plan_columns(["ID", name])
    config = parse_config_row({"ID": "#config", name: cell}, plan)
    front, back = split_sides(plan, config)
    return json.dumps(
        {
            "name": name,
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

// What each directive is worth starting from. Not documentation — a seed, so a
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
};

let preview = null;
let keys = { keys: [], media: [] };

function status(text, kind = "", busy = false) {
  $("#status-text").textContent = text;
  $("#status").className = `status ${kind} ${busy ? "busy" : ""}`;
}

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
  paintStatic();
  draw();
}

function paintStatic() {
  document.documentElement.lang = lang();
  for (const el of document.querySelectorAll("[data-i18n]")) {
    el.textContent = t(el.dataset.i18n);
  }
  const button = $("#theme");
  button.textContent = dark() ? "☀" : "☾";
  button.title = button.ariaLabel = t(dark() ? "toLight" : "toDark");

  $("#langs").innerHTML = LANGUAGES.map(
    (l) =>
      `<button data-lang="${l.code}" class="${lang() === l.code ? "on" : ""}"` +
      ` aria-pressed="${lang() === l.code}">${l.label}</button>`,
  ).join("");

  $("#keys").innerHTML = keys.keys
    .map((key) => `<button class="col" data-key="${escapeHtml(key)}">${escapeHtml(key)}</button>`)
    .join("");
}

/**
 * Puts a directive into the cell.
 *
 * Appended with `; ` because that is the separator a settings row uses, and a
 * key already in the cell is left alone rather than added twice — tapping it a
 * second time is somebody looking for it, not asking for two of it.
 */
function addKey(key) {
  const box = $("#cell");
  const seed = SEEDS[key] ?? key;
  const bare = seed.split("=")[0];
  const already = box.value
    .split(";")
    .some((part) => part.trim().split("=")[0].trim() === bare);
  if (!already) {
    box.value = box.value.trim()
      ? `${box.value.trim().replace(/;$/, "")}; ${seed}`
      : seed;
  }
  box.focus();
  draw();
}

/** The card this column makes, drawn from the templates the add-on would write. */
function draw() {
  if (!preview) return;

  let out;
  try {
    out = preview($("#name").value, $("#cell").value);
  } catch (err) {
    return status(String(err?.message || err).trim().split("\n").pop(), "bad");
  }

  const warnings = out.warnings || [];
  $("#warn").hidden = !warnings.length;
  $("#warnlist").innerHTML = warnings
    .map((w) => `<li>${escapeHtml(w)}</li>`)
    .join("");
  status(
    warnings.length ? t("edRefused", warnings.length) : t("edOk"),
    warnings.length ? "bad" : "ok",
  );

  const template = out.templates[0];
  const values = { ID: "1", [out.name]: $("#value").value };
  const { front, back } = renderCard(template, values, { ordinal: 1 });

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
      button.tts { font: inherit; font-size: 14px; padding: 2px 10px;
                   border: 1px solid currentColor; border-radius: 999px;
                   background: transparent; color: inherit; opacity: .8; }
    </style>
    <body class="card">${front.html}<hr id="answer">${backOnly(back.html, front.html)}
    <script>
      const post = () => parent.postMessage(
        { h: document.documentElement.scrollHeight }, "*");
      addEventListener("load", post); new ResizeObserver(post).observe(document.body);
    <\/script>`;

  $("#view").innerHTML = `<div class="stagebox">
    <iframe id="card" title="Card preview"
            sandbox="allow-scripts allow-same-origin allow-popups allow-presentation"
            allow="fullscreen; encrypted-media; picture-in-picture; autoplay"
            srcdoc="${escapeHtml(doc)}"></iframe>
    <p class="muted small">${escapeHtml(t("edSides", out.front.length, out.back.length))}</p>
  </div>`;
}

/** The answer side minus the repeated question, when the template used FrontSide. */
function backOnly(backHtml, frontHtml) {
  return backHtml.startsWith(frontHtml) ? backHtml.slice(frontHtml.length) : backHtml;
}

// ---------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------

document.addEventListener("click", (e) => {
  if (e.target.closest("#theme")) return setTheme(!dark());

  const picker = e.target.closest("[data-lang]");
  if (picker) {
    setLang(picker.dataset.lang);
    paintStatic();
    return draw();
  }

  const key = e.target.closest("[data-key]");
  if (key) return addKey(key.dataset.key);

  if (e.target.closest("#copy")) {
    navigator.clipboard
      ?.writeText($("#cell").value)
      .then(() => status(t("edCopied"), "ok"))
      .catch(() => status(t("edCopyFailed"), "bad"));
  }
});

for (const id of ["#name", "#value", "#cell"]) {
  $(id).addEventListener("input", draw);
}

addEventListener("message", (e) => {
  const frame = $("#card");
  const height = Number(e.data?.h);
  if (frame && height > 0) frame.style.height = `${Math.ceil(height)}px`;
});

paintStatic();
status(t("booting"), "", true);
startPython(EDITOR, (step) =>
  status(t(step === "boot" ? "booting" : "loadingCode"), "", true),
)
  .then((py) => {
    keys = JSON.parse(py.globals.get("keys")());
    const fn = py.globals.get("preview");
    preview = (name, cell) => JSON.parse(fn(name, cell));
    paintStatic();
    $("#cell").value = "size=44; bold";
    draw();
  })
  .catch((err) => status(t("bootFailed", err.message), "bad"));
