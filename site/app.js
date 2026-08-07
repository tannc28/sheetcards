/**
 * Sheets2Anki preview — runs the add-on's own Python in the browser.
 *
 * The point of this page is that it does not reimplement anything. Pyodide loads
 * the very files under src/ that the add-on runs inside Anki, so the column
 * roles, the settings row, the warnings and the card templates shown here are
 * produced by the same code that will produce them at sync time. The only part
 * written for the browser is site/anki.js, which stands in for Anki's own
 * template renderer — see that file for why that one cannot be reused.
 */

import { renderCard, clozeOrdinals, escapeHtml } from "./anki.js";

const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.28.3/full/pyodide.mjs";

// A filled-in report is a better landing page than an empty form: a first-time
// visitor sees what the tool actually answers instead of having to supply a sheet
// to find out. Overridden by ?url=, and by anything typed into the field.
const DEMO_SHEET =
  "https://docs.google.com/spreadsheets/d/1rDmjG7k82PJpAfQE4iT6XTUf3yy_o5GaW7M_CDQaRhE/edit";

// The pure layer, in dependency order. tests/test_pure_modules.py reads this very
// list and fails if it stops matching the modules it proves importable without Anki.
const PURE_MODULES = ["errors", "column_model", "sheet_config", "card_layout", "tsv_model"];

/** Everything the page needs, computed by the add-on's own code. */
const ANALYZER = String.raw`
import json
from s2a import tsv_model as tm
from s2a.card_layout import build_templates, split_sides
from s2a.column_model import deck_path
from s2a.sheet_config import is_config_row

def _settings(cfg):
    """A FieldConfig as a plain dict of only what the sheet actually set."""
    return {k: v for k, v in vars(cfg).items() if v not in (None, False, [])}

def analyze(tsv, deck_name):
    log = []
    parsed = tm.parse_tsv_data(tsv, log)
    headers, plan = parsed["headers"], parsed["plan"]

    # The authoritative numbers: the same object the sync builds and reports from.
    deck = tm.build_remote_deck_from_tsv(parsed, "", log)
    cfg = deck.sheet_config

    rows = parsed["rows"]
    offset = 0
    if rows and is_config_row(tm.row_to_dict(rows[0], headers), plan):
        rows, offset = rows[1:], 1

    listed = []
    for i, raw in enumerate(rows):
        note = tm.row_to_dict(raw, headers)
        kind = tm.classify_row(note, plan)
        if kind == tm.GHOST:
            continue
        path = deck_path(note, plan)
        listed.append({
            "line": i + 2 + offset,
            "kind": kind,
            "id": str(note.get(plan.id_header, "")).strip(),
            "deck": tm.get_subdeck_name(deck_name, path),
            "tags": tm.build_tags(note, plan),
            "cloze": tm.row_has_cloze(note, plan),
            # Which columns carry the deletion, so the page can tell whether the
            # template will actually cloze them. See clozeTrouble() in app.js.
            "clozeIn": [
                h for h in plan.content_headers
                if tm.has_cloze_deletion(str(note.get(h, "")))
            ],
            "values": {h: note.get(h, "") for h in ["ID"] + plan.content_headers},
        })

    front, back = split_sides(plan, cfg)
    return json.dumps({
        "plan": {
            "id": plan.id_header, "sync": plan.sync_header, "tags": plan.tags_header,
            "subdecks": plan.subdeck_headers, "content": plan.content_headers,
            "duplicates": plan.duplicates, "fields": plan.note_type_fields(),
            "headers": [h for h in headers if h.strip()],
        },
        "config": {
            "present": cfg.present, "align": cfg.align, "speed": cfg.speed,
            "reverse": cfg.reverse, "warnings": cfg.warnings,
            "fields": {h: _settings(c) for h, c in cfg.fields.items()},
        },
        "sides": {"front": front, "back": back},
        "templates": {
            "basic": build_templates(plan, cfg, is_cloze=False),
            "cloze": build_templates(plan, cfg, is_cloze=True),
        },
        "noteTypes": {
            "basic": tm.get_note_type_name("", deck_name, is_cloze=False),
            "cloze": tm.get_note_type_name("", deck_name, is_cloze=True),
        },
        "rows": listed,
        "stats": deck.get_statistics(),
        "duplicateIds": deck.duplicate_ids,
        "log": log,
    }, ensure_ascii=False)
`;

const $ = (sel) => document.querySelector(sel);
const state = { analysis: null, row: 0, side: "both", template: 0, ordinal: 1, deckName: "" };
let analyze = null;

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

function status(text, kind = "") {
  const el = $("#status");
  el.textContent = text;
  el.className = `status ${kind}`;
}

async function boot() {
  status("Starting Python…");
  const { loadPyodide } = await import(PYODIDE);
  const py = await loadPyodide({ indexURL: PYODIDE.replace("pyodide.mjs", "") });

  // Rebuild the add-on's package layout so the relative imports between these
  // files resolve exactly as they do inside Anki.
  py.FS.mkdir("/s2a");
  py.FS.writeFile("/s2a/__init__.py", "");
  await Promise.all(
    PURE_MODULES.map(async (name) => {
      const res = await fetch(`./s2a/${name}.py`);
      if (!res.ok) throw new Error(`could not load ${name}.py (${res.status})`);
      py.FS.writeFile(`/s2a/${name}.py`, await res.text());
    }),
  );
  py.runPython('import sys; sys.path.insert(0, "/")');
  py.runPython(ANALYZER);

  const fn = py.globals.get("analyze");
  analyze = (tsv, deckName) => JSON.parse(fn(tsv, deckName));
  status("Ready.", "ok");
  $("#go").disabled = false;
}

// ---------------------------------------------------------------------------
// Fetching the sheet
// ---------------------------------------------------------------------------

// Same conversion the add-on does in utils.convert_edit_url_to_tsv.
function toTsvUrl(url) {
  const trimmed = url.trim();
  if (trimmed.includes("/export?format=tsv")) return trimmed;
  const m = trimmed.match(/docs\.google\.com\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/);
  if (!m) throw new Error("That is not a Google Sheets link.");
  return `https://docs.google.com/spreadsheets/d/${m[1]}/export?format=tsv`;
}

/** Google names the download "{spreadsheet} - {tab}.tsv", which is close enough
 *  to seed the deck name — the add-on reads the page title instead, so this is a
 *  starting point the user can correct rather than a promise. */
function deckNameFromHeaders(res) {
  const raw = res.headers.get("content-disposition") || "";
  const utf8 = raw.match(/filename\*=UTF-8''([^;]+)/i);
  const plain = raw.match(/filename="([^"]+)"/i);
  let name = utf8 ? decodeURIComponent(utf8[1]) : plain ? plain[1] : "";
  name = name.replace(/\.tsv$/i, "");
  const cut = name.lastIndexOf(" - ");
  return (cut > 0 ? name.slice(0, cut) : name).trim();
}

async function preview() {
  const input = $("#url").value.trim();
  if (!input) return;

  $("#go").disabled = true;
  try {
    const tsvUrl = toTsvUrl(input);
    status("Downloading the sheet…");

    let res;
    try {
      res = await fetch(tsvUrl);
    } catch {
      throw new Error(
        "The browser could not reach the sheet. This is what the add-on sees " +
          "when a sheet is private: open it in Google Sheets → Share → " +
          "“Anyone with the link” → Viewer.",
      );
    }
    if (!res.ok) {
      throw new Error(
        res.status === 400 || res.status === 401 || res.status === 403
          ? "Google refused the download — the sheet is not shared. " +
            "Share → “Anyone with the link” → Viewer, then try again."
          : `Google returned HTTP ${res.status}.`,
      );
    }

    const tsv = await res.text();
    state.deckName = $("#deck").value.trim() || deckNameFromHeaders(res) || "Deck";
    $("#deck").value = state.deckName;

    status("Running the add-on's code…");
    state.analysis = analyze(tsv, state.deckName);
    state.row = state.analysis.rows.findIndex((r) => r.kind === "synced");
    if (state.row < 0) state.row = 0;
    state.template = 0;

    // The example is what you get with no query string, so putting it back into
    // the address bar would only make the landing URL longer for no gain.
    const isDemo = input === DEMO_SHEET;
    $("#demo-note").hidden = !isDemo;
    if (!isDemo) {
      const url = new URL(location.href);
      url.searchParams.set("url", input);
      history.replaceState(null, "", url);
    }

    render();
    status(`Read ${state.analysis.stats.total_table_lines} rows.`, "ok");
  } catch (err) {
    status(err.message, "bad");
    $("#results").hidden = true;
  } finally {
    $("#go").disabled = false;
  }
}

// ---------------------------------------------------------------------------
// Rendering the report
// ---------------------------------------------------------------------------

const roleOf = (header, plan) => {
  if (header === plan.id) return ["ID", "the row's key — never regenerated"];
  if (header === plan.sync) return ["SYNC", "gates whether the row syncs"];
  if (header === plan.tags) return ["TAGS", "extra Anki tags"];
  if (plan.subdecks.includes(header)) return ["SUBDECK", "one level of the deck path"];
  return ["field", "becomes a note field of this name"];
};

function columnsPanel({ plan, sides }) {
  const rows = plan.headers
    .map((h) => {
      const [role, why] = roleOf(h, plan);
      const dup = plan.duplicates.includes(h);
      const where = sides.front.includes(h)
        ? '<span class="pill front">front</span>'
        : sides.back.includes(h)
          ? '<span class="pill back">back</span>'
          : role === "field"
            ? '<span class="pill hidden">hidden</span>'
            : "";
      return `<tr class="${dup ? "dup" : ""}">
        <td><code>${escapeHtml(h)}</code></td>
        <td><span class="role role-${role.toLowerCase()}">${role}</span></td>
        <td>${where}</td>
        <td class="muted">${dup ? "repeated header — only the first is used" : why}</td>
      </tr>`;
    })
    .join("");

  return `<table class="grid">
    <thead><tr><th>Column</th><th>Role</th><th>Card</th><th></th></tr></thead>
    <tbody>${rows}</tbody></table>`;
}

const SETTING_LABEL = {
  side: "side", size: "size", color: "colour", align: "align", tts: "speak",
  voices: "voices", speed: "speed", label: "caption", media: "media",
  bold: "bold", italic: "italic", hint: "hint", furigana: "furigana",
};

function settingsPanel({ config, plan }) {
  if (!config.present) {
    return `<p class="empty">This sheet has no settings row, so the defaults apply:
      the first content column is the front, everything else is the back.
      Add a row under the headers with <code>#config</code> in the ID cell to change that.</p>`;
  }

  const deckWide = [
    config.align && `align=${config.align}`,
    config.speed && `speed=${config.speed}`,
    config.reverse && "reverse",
  ].filter(Boolean);

  const perField = plan.content.map((h) => {
    const cfg = config.fields[h] || {};
    const chips = Object.entries(cfg)
      .map(([k, v]) => {
        const label = SETTING_LABEL[k] || k;
        const text = v === true ? label : `${label} ${Array.isArray(v) ? v.join(", ") : v}`;
        return `<span class="chip">${escapeHtml(text)}</span>`;
      })
      .join("");
    return `<tr><td><code>${escapeHtml(h)}</code></td>
      <td>${chips || '<span class="muted">defaults</span>'}</td></tr>`;
  }).join("");

  return `
    <p class="deckwide">Deck-wide: ${
      deckWide.length
        ? deckWide.map((d) => `<span class="chip">${escapeHtml(d)}</span>`).join("")
        : '<span class="muted">nothing set</span>'
    }</p>
    <table class="grid"><tbody>${perField}</tbody></table>`;
}

/**
 * Rows whose cloze deletion sits in a column the template does not cloze.
 *
 * A row is routed to the Cloze note type when *any* content column contains
 * `{{c1::…}}`, but the template only applies Anki's `cloze:` filter to the front
 * columns. Anki renders `{{cloze:Field}}` as nothing at all when that field holds
 * no deletion, so such a card comes out with a blank front and the raw `{{c1::…}}`
 * text printed on the back.
 *
 * This check belongs to the page rather than to the add-on: it describes a
 * mismatch between two add-on behaviours, which is exactly the sort of thing a
 * preview exists to make visible.
 */
function clozeTrouble({ rows, sides }) {
  const front = new Set(sides.front);
  return rows.filter(
    (r) => r.kind === "synced" && r.clozeIn.length && !r.clozeIn.some((h) => front.has(h)),
  );
}

function warningsPanel(analysis) {
  const { config, duplicateIds, sides } = analysis;
  const items = config.warnings.map(
    (w) => `<li><strong>Settings row</strong> — ${escapeHtml(w)}</li>`,
  );

  const stranded = clozeTrouble(analysis);
  if (stranded.length) {
    const columns = [...new Set(stranded.flatMap((r) => r.clozeIn))];
    items.push(
      `<li><strong>Cloze in a column that is not on the front</strong> —
       ${stranded.length} row${stranded.length > 1 ? "s" : ""}
       (${stranded.slice(0, 8).map((r) => `row ${r.line}`).join(", ")}${stranded.length > 8 ? ", …" : ""})
       put the deletion in <code>${columns.map(escapeHtml).join("</code>, <code>")}</code>,
       but the card's prompt is <code>${escapeHtml(sides.front[0] || "—")}</code>.
       Anki renders a clozed field that has no deletion as nothing, so these cards
       come out with an empty front and the literal <code>{{c1::…}}</code> text on
       the back. Move the sentence to the first content column, or give that column
       <code>side=front</code> in the settings row.</li>`,
    );
  }
  if (duplicateIds.length) {
    items.push(
      `<li><strong>Duplicate IDs</strong> — ${escapeHtml(duplicateIds.slice(0, 20).join(", "))}
       ${duplicateIds.length > 20 ? "…" : ""}. Notes are keyed by ID, so only one row of
       each survives the sync.</li>`,
    );
  }
  if (!items.length) return "";
  return `<section class="panel warn">
    <h2>Warnings <span class="count">${items.length}</span></h2>
    <ul class="warnings">${items.join("")}</ul>
    <p class="muted">Nothing here is silently ignored — the add-on refuses the value
      rather than guessing, so the column keeps its default until the sheet is fixed.</p>
  </section>`;
}

function rowsPanel({ rows }) {
  const body = rows
    .map(
      (r, i) => `<tr class="row-${r.kind} ${i === state.row ? "selected" : ""}"
        data-row="${i}" tabindex="0">
        <td class="num">${r.line}</td>
        <td><span class="dot ${r.kind}" title="${r.kind}"></span></td>
        <td><code>${escapeHtml(r.id) || '<span class="muted">— no ID —</span>'}</code></td>
        <td class="muted">${escapeHtml(r.deck)}</td>
        <td>${r.cloze ? '<span class="pill cloze">cloze</span>' : ""}</td>
      </tr>`,
    )
    .join("");

  return `<table class="grid rows">
    <thead><tr><th>Row</th><th></th><th>ID</th><th>Deck</th><th></th></tr></thead>
    <tbody>${body}</tbody></table>`;
}

function cardFrame(analysis) {
  const row = analysis.rows[state.row];
  if (!row) return `<p class="empty">No rows to show.</p>`;

  const isCloze = row.cloze;
  const templates = isCloze ? analysis.templates.cloze : analysis.templates.basic;
  const template = templates[Math.min(state.template, templates.length - 1)];

  const ordinals = isCloze
    ? [...new Set(Object.values(row.values).flatMap((v) => clozeOrdinals(v)))]
    : [1];
  const ordinal = ordinals.includes(state.ordinal) ? state.ordinal : ordinals[0] || 1;

  const { front, back } = renderCard(template, row.values, { ordinal });

  const doc = `<!doctype html><meta charset="utf-8">
    <style>
      html { color-scheme: light dark; }
      body { margin: 0; padding: 20px; font-family: arial, sans-serif; font-size: 20px;
             text-align: center; color: #111; background: #fff; }
      @media (prefers-color-scheme: dark) {
        body { color: #e6e9ee; background: #1b1f25; }
      }
      hr#answer { margin: 18px 0; border: 0; border-top: 1px solid currentColor; opacity: .25; }
      .cloze { color: #2f6fd0; font-weight: 700; }
      a.hint { color: #2f6fd0; font-size: 15px; }
      button.tts { font: inherit; font-size: 14px; padding: 2px 10px; cursor: pointer;
                   border: 1px solid currentColor; border-radius: 999px;
                   background: transparent; color: inherit; opacity: .8; }
      img, video { max-width: 100%; }
    </style>
    <body class="card">
      ${state.side === "back" ? back.html : front.html}
      ${state.side === "both" ? '<hr id="answer">' + backOnly(back.html, front.html) : ""}
      <script>
        document.addEventListener("click", (e) => {
          const b = e.target.closest("[data-tts]");
          if (!b) return;
          const t = JSON.parse(b.dataset.tts);
          const u = new SpeechSynthesisUtterance(t.text);
          u.lang = t.lang.replace("_", "-");
          u.rate = Number(t.speed) || 1;
          const want = new Set(t.voices);
          const v = speechSynthesis.getVoices();
          u.voice = v.find((x) => want.has(x.name))
                 || v.find((x) => x.lang.replace("-", "_") === t.lang) || null;
          speechSynthesis.cancel();
          speechSynthesis.speak(u);
        });
        const post = () => parent.postMessage(
          { h: document.documentElement.scrollHeight }, "*");
        addEventListener("load", post); new ResizeObserver(post).observe(document.body);
      <\/script>`;

  const notes = [...new Set([...front.unknownFilters, ...back.unknownFilters])];
  const missing = [...new Set([...front.missingFields, ...back.missingFields])];

  return `
    <div class="cardbar">
      <div class="segmented">
        ${["front", "both", "back"]
          .map(
            (s) =>
              `<button data-side="${s}" class="${state.side === s ? "on" : ""}">${s}</button>`,
          )
          .join("")}
      </div>
      ${
        templates.length > 1
          ? `<select id="tpl">${templates
              .map(
                (t, i) =>
                  `<option value="${i}" ${i === state.template ? "selected" : ""}>${escapeHtml(t.name)}</option>`,
              )
              .join("")}</select>`
          : `<span class="muted mono">${escapeHtml(template.name)}</span>`
      }
      ${
        ordinals.length > 1
          ? `<select id="ord">${ordinals
              .map(
                (n) =>
                  `<option value="${n}" ${n === ordinal ? "selected" : ""}>card c${n}</option>`,
              )
              .join("")}</select>`
          : ""
      }
      <span class="spacer"></span>
      <button id="prev" title="Previous row">←</button>
      <span class="mono muted">row ${row.line}</span>
      <button id="next" title="Next row">→</button>
    </div>
    <iframe id="card" sandbox="allow-scripts" srcdoc="${escapeHtml(doc)}"></iframe>
    ${
      row.kind !== "synced"
        ? `<p class="note ${row.kind}">This row ${
            row.kind === "invalid"
              ? "has no ID, so the sync counts it as broken and skips it."
              : "is not ticked in the SYNC column, so the sync skips it."
          }</p>`
        : ""
    }
    ${
      row.clozeIn.length && !row.clozeIn.some((h) => analysis.sides.front.includes(h))
        ? `<p class="note invalid">The deletion in
           <code>${row.clozeIn.map(escapeHtml).join("</code>, <code>")}</code> is not on
           the front, so Anki blanks the prompt and prints the raw
           <code>{{c1::…}}</code> below. The picture above shows that faithfully.</p>`
        : ""
    }
    ${missing.length ? `<p class="note">Template references a field the row has no column for: <code>${missing.map(escapeHtml).join("</code>, <code>")}</code></p>` : ""}
    ${notes.length ? `<p class="note">Filter not reproduced here: <code>${notes.map(escapeHtml).join("</code>, <code>")}</code></p>` : ""}
    <p class="muted small">The template above is exactly what the add-on generates.
      Turning it into this picture is done by this page, not by Anki — treat the
      layout as a close approximation.</p>`;
}

/** The answer side minus the repeated question, when the template used FrontSide. */
function backOnly(backHtml, frontHtml) {
  return backHtml.startsWith(frontHtml) ? backHtml.slice(frontHtml.length) : backHtml;
}

function deckTree({ rows }) {
  const counts = new Map();
  for (const r of rows) {
    if (r.kind !== "synced") continue;
    counts.set(r.deck, (counts.get(r.deck) || 0) + 1);
  }
  if (!counts.size) return `<p class="empty">No rows are marked for sync.</p>`;

  return `<ul class="tree">${[...counts.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([name, n]) => {
      const parts = name.split("::");
      return `<li style="--depth:${parts.length - 1}">
        <code>${escapeHtml(parts[parts.length - 1])}</code>
        <span class="count">${n}</span></li>`;
    })
    .join("")}</ul>`;
}

function statStrip({ stats, rows }) {
  const cells = [
    ["rows in the sheet", stats.total_table_lines],
    ["with an ID", stats.valid_note_lines],
    ["marked for sync", stats.sync_marked_lines],
    ["notes in Anki", stats.total_potential_anki_notes],
    ["cloze rows", rows.filter((r) => r.cloze && r.kind === "synced").length],
  ];
  return cells
    .map(
      ([label, n]) =>
        `<div class="stat ${n === 0 && label === "marked for sync" ? "zero" : ""}">
           <b>${n}</b><span>${label}</span></div>`,
    )
    .join("");
}

function render() {
  const a = state.analysis;
  $("#results").hidden = false;
  $("#stats").innerHTML = statStrip(a);
  $("#columns").innerHTML = columnsPanel(a);
  $("#settings").innerHTML = settingsPanel(a);
  $("#warnings").innerHTML = warningsPanel(a);
  $("#rowlist").innerHTML = rowsPanel(a);
  $("#card-panel").innerHTML = cardFrame(a);
  $("#tree").innerHTML = deckTree(a);
  $("#notetypes").innerHTML = `
    <p><code>${escapeHtml(a.noteTypes.basic)}</code></p>
    ${a.rows.some((r) => r.cloze) ? `<p><code>${escapeHtml(a.noteTypes.cloze)}</code></p>` : ""}
    <p class="muted">Fields, in order — <code>ID</code> leads because Anki uses the
      first field for duplicate detection:</p>
    <p>${a.plan.fields.map((f) => `<span class="chip">${escapeHtml(f)}</span>`).join("")}</p>`;

  const templates = a.rows[state.row]?.cloze ? a.templates.cloze : a.templates.basic;
  $("#source").textContent = templates
    .map((t) => `═══ ${t.name} — front ═══\n${t.qfmt}\n\n═══ ${t.name} — back ═══\n${t.afmt}`)
    .join("\n\n");
}

// ---------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------

$("#go").addEventListener("click", preview);
$("#url").addEventListener("keydown", (e) => e.key === "Enter" && preview());

document.addEventListener("click", (e) => {
  const rowEl = e.target.closest("[data-row]");
  if (rowEl) {
    state.row = Number(rowEl.dataset.row);
    state.template = 0;
    return render();
  }
  const side = e.target.closest("[data-side]");
  if (side) {
    state.side = side.dataset.side;
    return render();
  }
  if (e.target.id === "prev" || e.target.id === "next") {
    const step = e.target.id === "next" ? 1 : -1;
    const n = state.analysis.rows.length;
    state.row = (state.row + step + n) % n;
    return render();
  }
});

document.addEventListener("change", (e) => {
  if (e.target.id === "tpl") state.template = Number(e.target.value);
  else if (e.target.id === "ord") state.ordinal = Number(e.target.value);
  else return;
  render();
});

addEventListener("message", (e) => {
  const frame = $("#card");
  if (frame && e.data?.h) frame.style.height = `${e.data.h + 8}px`;
});

$("#url").value = new URLSearchParams(location.search).get("url") || DEMO_SHEET;

boot()
  .then(preview)
  .catch((err) => status(`Could not start Python: ${err.message}`, "bad"));
