/**
 * Sheets2Anki preview — runs the add-on's own Python in the browser.
 *
 * The point of this page is that it does not reimplement anything. Pyodide loads
 * the very files under src/ that the add-on runs inside Anki, so the column
 * roles, the settings row, the warnings, the deck paths and the card templates
 * shown here are produced by the same code that will produce them at sync time.
 * The only part written for the browser is site/anki.js, which stands in for
 * Anki's own template renderer — see that file for why that one cannot be reused.
 */

import { renderCard, clozeOrdinals, escapeHtml } from "./anki.js";
import { LANGUAGES, lang, setLang, t } from "./i18n.js";

const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.28.3/full/pyodide.mjs";

// A filled-in report is a better landing page than an empty form: a first-time
// visitor sees what the tool actually answers instead of having to supply a sheet
// to find out. This one carries a settings row — sizes, two `tts=zh_CN` columns, a
// muted colour, a hint and a SUBDECK level — so the example shows the directives
// doing something rather than only the defaults.
// Overridden by ?url=, and by anything typed into the field.
const DEMO_SHEET =
  "https://docs.google.com/spreadsheets/d/1ze2znekyf6dduvQ_N6fYc3SEodWnz_CaY2WWLVkvuiI/edit";

// The pure layer, in dependency order. tests/test_pure_modules.py reads this very
// list and fails if it stops matching the modules it proves importable without Anki.
const PURE_MODULES = [
  "errors", "column_model", "sheet_config", "card_layout", "tsv_model", "apkg",
  // Reads an uploaded file, and the file a Google Sheets link downloads to when a
  // deck names a sheet inside it. Shared with the add-on, so both agree.
  "workbook",
];

/** Everything the page needs, computed by the add-on's own code. */
const ANALYZER = String.raw`
import json
from s2a import tsv_model as tm
from s2a.card_layout import build_templates, split_sides
from s2a.column_model import deck_path
from s2a.sheet_config import is_config_row
from s2a.apkg import build_package

# The last analysis, so the package can be built from exactly the rows the page
# drew rather than by parsing the sheet a second time.
_STATE = {}


def package_bytes(sheet_id):
    deck = _STATE["deck"]
    return build_package(
        sheet_id, _STATE["name"], deck.plan, deck.sheet_config, _STATE["rows"]
    )


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

    # determine_target_deck builds exactly this name, so the tree below is the
    # tree Anki will show.
    root = tm.deck_root_name(deck_name)

    rows = parsed["rows"]
    offset = 0
    if rows and is_config_row(tm.row_to_dict(rows[0], headers), plan):
        rows, offset = rows[1:], 1

    listed, kept = [], []
    for i, raw in enumerate(rows):
        note = tm.row_to_dict(raw, headers)
        # The same rewrite the sync performs. Skipping it would frame the address
        # the user pasted — the one address that cannot be framed — so a perfectly
        # good card would preview as a blank box.
        tm.apply_media_rewrites(note, plan, cfg)
        kind = tm.classify_row(note, plan)
        if kind == tm.GHOST:
            continue
        kept.append(note)
        listed.append({
            "line": i + 2 + offset,
            "kind": kind,
            "id": str(note.get(plan.id_header, "")).strip(),
            "deck": tm.get_subdeck_name(root, deck_path(note, plan)),
            "tags": tm.build_tags(note, plan),
            "cloze": tm.row_has_cloze(note, plan),
            # Which columns carry the deletion, so the page can tell whether the
            # template will actually cloze them. See clozeTrouble() below.
            "clozeIn": [
                h for h in plan.content_headers
                if tm.has_cloze_deletion(str(note.get(h, "")))
            ],
            "values": {h: note.get(h, "") for h in ["ID"] + plan.content_headers},
        })

    _STATE["deck"] = deck
    _STATE["rows"] = kept
    _STATE["name"] = deck_name

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
const state = {
  analysis: null, row: 0, template: 0, ordinal: 1, deckName: "", deckFilter: null,
  sheetId: "",
  // What the .apkg derives its note ids from — a spreadsheet id for a link, the
  // file and tab for an upload. Either way it has to be the same next time or a
  // re-import duplicates every note instead of updating it.
  sheetId: "",
  // What the right pane shows: the card, or its source the way Anki puts the
  // template editor beside it. The card is never taken away — the sheet's
  // configuration opens as a drawer in the *left* pane instead, because it is
  // reference material you consult while still looking at the card.
  tab: "both",
  detailOpen: false,
};
const CARD_TABS = ["front", "both", "back", "template"];
let analyze = null;
let buildPackage = null;
let readUpload = null;

// The file last dropped on the page, kept as bytes because changing tab re-reads
// it: a File object is gone once its input has moved on.
let upload = null;

// Whether the deck name on screen was typed rather than derived. Without this a
// name filled in from one sheet would quietly become the name of the next one.
let deckNameEdited = false;

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

/**
 * @param {string} text
 * @param {""|"ok"|"bad"} kind
 * @param {boolean} busy  spin while something is genuinely running, so a still
 *   page reads as finished rather than as hung
 */
function status(text, kind = "", busy = false) {
  $("#status-text").textContent = text;
  $("#status").className = `status ${kind} ${busy ? "busy" : ""}`;
}

async function boot() {
  status(t("booting"), "", true);
  const { loadPyodide } = await import(PYODIDE);
  const py = await loadPyodide({ indexURL: PYODIDE.replace("pyodide.mjs", "") });

  status(t("loadingCode"), "", true);
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
  // apkg builds a SQLite file, and Pyodide keeps sqlite3 out of the base image.
  await py.loadPackage("sqlite3");
  py.runPython(ANALYZER);

  const fn = py.globals.get("analyze");
  analyze = (tsv, deckName) => JSON.parse(fn(tsv, deckName));
  const pack = py.globals.get("package_bytes");
  buildPackage = (sheetId) => pack(sheetId).toJs();
  const wb = py.pyimport("s2a.workbook");
  readUpload = (bytes, name, index) =>
    JSON.parse(wb.read_upload(bytes, name, index));
  $("#go").disabled = false;
  $("#pick").disabled = false;
}

/**
 * The last line of a Python traceback, which is the part written for a person.
 *
 * Pyodide surfaces a raised exception as a JS Error carrying the whole traceback
 * in its message. Put in the status bar unedited it buries the sentence
 * workbook.py wrote under twenty lines of frames.
 */
function pythonMessage(err) {
  const lines = String(err?.message || err).trimEnd().split("\n");
  const last = lines[lines.length - 1].trim();
  return last.replace(/^[\w.]*Error:\s*/, "") || String(err?.message || err);
}

// ---------------------------------------------------------------------------
// Fetching the sheet
// ---------------------------------------------------------------------------

/** The spreadsheet id in a Google Sheets link, or null when it is not one. */
function spreadsheetId(url) {
  const m = url.trim().match(/docs\.google\.com\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/);
  return m ? m[1] : null;
}

// A deck's source does not have to be a Google Sheet: a .xlsx at a plain address
// holds the same sheets and is read by the same reader. Mirrors
// utils.is_spreadsheet_file_url / normalize_file_url — the add-on accepts exactly
// these, and a page that accepted more would be previewing something that cannot
// then be synced.
const FILE_SUFFIXES = [".xlsx", ".xlsm"];

function isFileUrl(url) {
  const path = url.trim().split("#")[0].split("?")[0].toLowerCase();
  return !spreadsheetId(url) && FILE_SUFFIXES.some((s) => path.endsWith(s));
}

/** GitHub's /blob/ address serves an HTML page; the raw host serves the file —
 *  and sends `access-control-allow-origin: *`, so this page can read it. */
function normalizeFileUrl(url) {
  const base = url.trim().split("#")[0];
  const blob = base.match(/^https:\/\/github\.com\/([^/]+)\/([^/]+)\/(?:blob|raw)\/(.+)$/i);
  return blob
    ? `https://raw.githubusercontent.com/${blob[1]}/${blob[2]}/${blob[3]}`
    : base;
}

/** A stable id for whatever the URL points at — the same one the add-on keys the
 *  deck by, so a package built here and a sync agree about which notes are which. */
async function sourceId(url) {
  const id = spreadsheetId(url);
  if (id) return id;
  const digest = await crypto.subtle.digest(
    "SHA-1",
    new TextEncoder().encode(normalizeFileUrl(url)),
  );
  const hex = [...new Uint8Array(digest)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  return `file_${hex.slice(0, 16)}`;
}

// The whole file rather than one sheet, exactly as the add-on downloads it in
// utils.convert_edit_url_to_xlsx. A Google Sheets file holds several sheets and
// each becomes its own deck; the TSV export hands over only the first one, and
// there is no official way to ask for another by name. Downloading the file is
// what lets this page show the same sheet picker an uploaded file already gets —
// and, more to the point, the same sheets the add-on will sync.
function toWorkbookUrl(url) {
  if (isFileUrl(url)) return normalizeFileUrl(url);
  const id = spreadsheetId(url);
  if (!id) throw new Error(t("notASheet"));
  return `https://docs.google.com/spreadsheets/d/${id}/export?format=xlsx`;
}

/** Google names the download after the spreadsheet, which is close enough to seed
 *  the deck name — the add-on reads the page title instead, so this is a starting
 *  point the user can correct rather than a promise. */
/** A file's own name, for a URL that serves no Content-Disposition. */
function fileNameFromUrl(url) {
  const path = normalizeFileUrl(url).split("?")[0];
  return decodeURIComponent(path.split("/").pop() || "").replace(/\.[^.]+$/, "");
}

function deckNameFromHeaders(res) {
  const raw = res.headers.get("content-disposition") || "";
  const utf8 = raw.match(/filename\*=UTF-8''([^;]+)/i);
  const plain = raw.match(/filename="([^"]+)"/i);
  let name = utf8 ? decodeURIComponent(utf8[1]) : plain ? plain[1] : "";
  return name.replace(/\.(xlsx|tsv|csv)$/i, "").trim();
}

/** The name to put on the deck, unless the field on screen was typed into. */
function chooseDeckName(fallback) {
  const typed = $("#deck").value.trim();
  return (deckNameEdited && typed) || fallback || "Deck";
}

/** Everything from "we have the text" to "the page is drawn". */
function analyse(tsv, deckName, sheetId) {
  state.deckName = deckName;
  // Kept rather than recovered from the URL field at download time: a file has
  // no link to recover it from, and the id is what makes a second import of the
  // same sheet update its notes instead of duplicating them.
  state.sheetId = sheetId;
  $("#deck").value = deckName;

  status(t("analysing"), "", true);
  state.analysis = analyze(tsv, deckName);
  state.row = state.analysis.rows.findIndex((r) => r.kind === "synced");
  if (state.row < 0) state.row = 0;
  state.template = 0;
  state.deckFilter = null;
  render();

  const s = state.analysis.stats;
  status(
    t("readRows", s.total_table_lines, s.sync_marked_lines),
    s.sync_marked_lines ? "ok" : "bad",
  );
}

function failed(message) {
  status(message, "bad");
  $("#app").hidden = true;
  $("#stats").hidden = true;
}

async function preview() {
  const input = $("#url").value.trim();
  if (!input) return;

  $("#go").disabled = true;
  try {
    const workbookUrl = toWorkbookUrl(input);
    status(t("downloading"), "", true);

    let res;
    try {
      res = await fetch(workbookUrl);
    } catch {
      throw new Error(t("unreachable"));
    }
    if (!res.ok) {
      throw new Error(
        res.status === 400 || res.status === 401 || res.status === 403
          ? t("refused")
          : t("httpError", res.status),
      );
    }

    // From here a link and a dropped file are the same thing: a spreadsheet file
    // with sheets in it. The sheet picker, the deck name and the package all come
    // out of the one path, so the page cannot treat them differently.
    upload = {
      bytes: new Uint8Array(await res.arrayBuffer()),
      name: `${deckNameFromHeaders(res) || fileNameFromUrl(input) || "Deck"}.xlsx`,
      // The key the add-on stores this deck under, so a package downloaded here
      // and a sync from the add-on agree about which notes are which.
      idBase: await sourceId(input),
      tabs: [],
      index: 0,
    };

    // The example is what you get with no query string, so putting it back into
    // the address bar would only make the landing URL longer for no gain.
    const isDemo = input === DEMO_SHEET;
    $("#demo-note").hidden = !isDemo;
    if (!isDemo) {
      const url = new URL(location.href);
      url.searchParams.set("url", input);
      history.replaceState(null, "", url);
    }

    showUpload(0);
  } catch (err) {
    failed(err.message);
  } finally {
    $("#go").disabled = false;
  }
}

// ---------------------------------------------------------------------------
// Reading an uploaded file
// ---------------------------------------------------------------------------

/** The tab picker, drawn only for a workbook that has more than one grid. */
function paintTabs() {
  const el = $("#tabpick");
  const tabs = upload?.tabs || [];
  el.hidden = !tabs.length;
  el.innerHTML = tabs
    .map(
      (name, i) =>
        `<option value="${i}" ${i === upload.index ? "selected" : ""}>` +
        `${escapeHtml(name)}</option>`,
    )
    .join("");
}

/**
 * Reads the held bytes and draws the result.
 *
 * A workbook's tabs are separate sheets that happen to travel together, so each
 * one gets its own deck name — naming fourteen decks after the file they came in
 * would make the download button produce fourteen indistinguishable packages.
 */
function showUpload(index) {
  $("#pick").disabled = true;
  try {
    let out;
    try {
      out = readUpload(upload.bytes, upload.name, index);
    } catch (err) {
      throw new Error(pythonMessage(err));
    }

    upload.tabs = out.tabs;
    upload.index = index;
    paintTabs();

    const base = upload.name.replace(/\.[^.]+$/, "").trim();
    analyse(
      out.tsv,
      chooseDeckName(out.tabs.length ? `${base}::${out.tab}` : base),
      `${upload.idBase}#${out.tab}`,
    );
  } catch (err) {
    failed(err.message);
  } finally {
    $("#pick").disabled = false;
  }
}

async function previewFile(file) {
  status(t("reading"), "", true);
  try {
    upload = {
      bytes: new Uint8Array(await file.arrayBuffer()),
      name: file.name,
      idBase: `file:${file.name}`,
      tabs: [],
      index: 0,
    };
  } catch (err) {
    return failed(t("unreadableFile", err.message));
  }

  // Nothing about a local file can go in the address bar, so a ?url= left over
  // from a link would send the next person who opens it somewhere else entirely.
  const url = new URL(location.href);
  url.searchParams.delete("url");
  history.replaceState(null, "", url);
  $("#demo-note").hidden = true;
  $("#url").value = "";

  showUpload(0);
}

// ---------------------------------------------------------------------------
// Left pane — navigation only
// ---------------------------------------------------------------------------

/** The deck hierarchy, with each level counting everything beneath it. */
function deckTree(rows) {
  const root = { name: null, path: "", count: 0, children: new Map() };
  for (const r of rows) {
    if (r.kind !== "synced") continue;
    root.count++;
    let node = root;
    const parts = [];
    for (const part of r.deck.split("::")) {
      parts.push(part);
      if (!node.children.has(part)) {
        node.children.set(part, {
          name: part, path: parts.join("::"), count: 0, children: new Map(),
        });
      }
      node = node.children.get(part);
      node.count++;
    }
  }
  return root;
}

function treeHtml(node, depth = 0) {
  return [...node.children.values()]
    .sort((a, b) => a.name.localeCompare(b.name))
    .map(
      (child) => `<li>
        <button data-deck="${escapeHtml(child.path)}" style="--depth:${depth}"
                class="${state.deckFilter === child.path ? "on" : ""}">
          <span class="name">${escapeHtml(child.name)}</span>
          <span class="count">${child.count}</span>
        </button>
        ${child.children.size ? `<ul class="tree">${treeHtml(child, depth + 1)}</ul>` : ""}
      </li>`,
    )
    .join("");
}

function deckPanel({ rows }) {
  const tree = deckTree(rows);
  if (!tree.count) return `<p class="empty">${escapeHtml(t("noSyncRows"))}</p>`;

  return `<ul class="tree">
    <li><button data-deck="" style="--depth:0"
        class="${state.deckFilter === null ? "on" : ""}">
      <span class="name">${escapeHtml(t("allDecks"))}</span><span class="count">${tree.count}</span>
    </button></li>
    ${treeHtml(tree, 0)}
  </ul>`;
}

/** Rows the deck selection lets through, with their index into the full list. */
function visibleRows() {
  const all = state.analysis.rows;
  const f = state.deckFilter;
  return all
    .map((r, i) => ({ r, i }))
    .filter(({ r }) => !f || r.deck === f || r.deck.startsWith(`${f}::`));
}

function rowList() {
  const visible = visibleRows();
  if (!visible.length) return `<p class="empty">${escapeHtml(t("noRowsHere"))}</p>`;

  const prompt = state.analysis.sides.front[0];
  return visible
    .map(
      ({ r, i }) => `<button class="rowitem row-${r.kind} ${i === state.row ? "on" : ""}"
        data-row="${i}" title="row ${r.line} — ${escapeHtml(r.kind)}">
        <span class="n">${r.line}</span>
        <span class="dot ${r.kind}"></span>
        <span class="txt">${escapeHtml(r.values[prompt] || r.id || "—")}</span>
        ${r.cloze ? '<span class="pill cloze">c</span>' : ""}
      </button>`,
    )
    .join("");
}

// ---------------------------------------------------------------------------
// Warnings — surfaced, not buried
// ---------------------------------------------------------------------------

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

function warningItems(analysis) {
  const { config, duplicateIds, sides } = analysis;
  const items = config.warnings.map(
    (w) => `<li><strong>${escapeHtml(t("warnSettingsRow"))}</strong> — ${escapeHtml(w)}</li>`,
  );

  const stranded = clozeTrouble(analysis);
  if (stranded.length) {
    const columns = [...new Set(stranded.flatMap((r) => r.clozeIn))];
    const where =
      stranded.slice(0, 8).map((r) => `${r.line}`).join(", ") +
      (stranded.length > 8 ? ", …" : "");
    items.push(
      `<li><strong>${escapeHtml(t("warnClozeTitle"))}</strong> — ${t(
        "warnClozeBody",
        stranded.length,
        where,
        columns.map(escapeHtml).join("</code>, <code>"),
        escapeHtml(sides.front[0] || "—"),
      )}</li>`,
    );
  }
  if (duplicateIds.length) {
    items.push(
      `<li><strong>${escapeHtml(t("warnDuplicateTitle"))}</strong> — ${t(
        "warnDuplicateBody",
        escapeHtml(duplicateIds.slice(0, 20).join(", ")) + (duplicateIds.length > 20 ? " …" : ""),
      )}</li>`,
    );
  }
  return items;
}

// ---------------------------------------------------------------------------
// Right pane — the card, and behind it the reference material
// ---------------------------------------------------------------------------

const roleOf = (header, plan) => {
  if (header === plan.id) return ["ID", t("roleId")];
  if (header === plan.sync) return ["SYNC", t("roleSync")];
  if (header === plan.tags) return ["TAGS", t("roleTags")];
  if (plan.subdecks.includes(header)) return ["SUBDECK", t("roleSubdeck")];
  return ["field", t("roleField")];
};

const SETTING_LABEL = {
  side: "side", size: "size", color: "colour", align: "align", tts: "speak",
  voices: "voices", speed: "speed", label: "caption", media: "media",
  bold: "bold", italic: "italic", hint: "hint", furigana: "furigana",
};

function detailView(a) {
  const warnings = warningItems(a);

  const columns = a.plan.headers
    .map((h) => {
      const [role, why] = roleOf(h, a.plan);
      const dup = a.plan.duplicates.includes(h);
      const where = a.sides.front.includes(h)
        ? `<span class="pill front">${escapeHtml(t("pillFront"))}</span>`
        : a.sides.back.includes(h)
          ? `<span class="pill">${escapeHtml(t("pillBack"))}</span>`
          : role === "field"
            ? `<span class="pill hidden">${escapeHtml(t("pillHidden"))}</span>`
            : "";
      return `<tr class="${dup ? "dup" : ""}">
        <td><code>${escapeHtml(h)}</code></td>
        <td><span class="role role-${role.toLowerCase()}">${role}</span></td>
        <td>${where}</td>
        <td class="muted">${dup ? escapeHtml(t("roleDuplicate")) : why}</td>
      </tr>`;
    })
    .join("");

  const deckWide = [
    a.config.align && `align=${a.config.align}`,
    a.config.speed && `speed=${a.config.speed}`,
    a.config.reverse && "reverse",
  ].filter(Boolean);

  const settings = !a.config.present
    ? `<p class="empty">${t("noSettingsRow")}</p>`
    : `<p class="deckwide">${escapeHtml(t("deckWide"))}: ${
        deckWide.length
          ? deckWide.map((d) => `<span class="chip">${escapeHtml(d)}</span>`).join("")
          : `<span class="muted">${escapeHtml(t("nothingSet"))}</span>`
      }</p>
      <table class="grid"><tbody>${a.plan.content
        .map((h) => {
          const cfg = a.config.fields[h] || {};
          const chips = Object.entries(cfg)
            .map(([k, v]) => {
              const label = SETTING_LABEL[k] || k;
              const text = v === true ? label : `${label} ${Array.isArray(v) ? v.join(", ") : v}`;
              return `<span class="chip">${escapeHtml(text)}</span>`;
            })
            .join("");
          return `<tr><td><code>${escapeHtml(h)}</code></td>
            <td>${chips || `<span class="muted">${escapeHtml(t("defaults"))}</span>`}</td></tr>`;
        })
        .join("")}</tbody></table>`;

  return `<div class="detail">
    ${
      warnings.length
        ? `<h2>${escapeHtml(t("warnings"))}</h2><ul class="warnings">${warnings.join("")}</ul>
           <p class="muted small">${t("warningsFrom")}</p>`
        : ""
    }

    <h2>${escapeHtml(t("columns"))}</h2>
    <p class="muted small">${t("columnsIntro")}</p>
    <table class="grid">
      <thead><tr><th>${escapeHtml(t("colColumn"))}</th><th>${escapeHtml(t("colRole"))}</th>
        <th>${escapeHtml(t("colCard"))}</th><th></th></tr></thead>
      <tbody>${columns}</tbody></table>

    <h2>${escapeHtml(t("settingsRow"))}</h2>
    ${settings}

    <h2>${escapeHtml(t("noteTypes"))}</h2>
    <p class="small"><code>${escapeHtml(a.noteTypes.basic)}</code></p>
    ${a.rows.some((r) => r.cloze) ? `<p class="small"><code>${escapeHtml(a.noteTypes.cloze)}</code></p>` : ""}
    <p class="muted small">${t("fieldsInOrder")}</p>
    <p>${a.plan.fields.map((f) => `<span class="chip">${escapeHtml(f)}</span>`).join("")}</p>

    <h2>${escapeHtml(t("howItWorks"))}</h2>
    <p class="muted small">${t("howItWorksBody")}</p>
    <p class="muted small">${t("runsAsAnki")}</p>
  </div>`;
}

function templateView(a) {
  const row = a.rows[state.row];
  const templates = row?.cloze ? a.templates.cloze : a.templates.basic;
  const template = templates[Math.min(state.template, templates.length - 1)];
  return `
    <p class="muted small">${t(
      "templateFrom",
      escapeHtml(row?.cloze ? a.noteTypes.cloze : a.noteTypes.basic),
    )}</p>
    <h2>${escapeHtml(t("frontTemplate"))}</h2>
    <pre class="source">${escapeHtml(template.qfmt)}</pre>
    <h2 class="spaced">${escapeHtml(t("backTemplate"))}</h2>
    <pre class="source">${escapeHtml(template.afmt)}</pre>`;
}

function cardView(a) {
  const row = a.rows[state.row];
  if (!row) return `<p class="empty">${escapeHtml(t("noRowsAtAll"))}</p>`;

  const isCloze = row.cloze;
  const templates = isCloze ? a.templates.cloze : a.templates.basic;
  const template = templates[Math.min(state.template, templates.length - 1)];

  const ordinals = isCloze
    ? [...new Set(Object.values(row.values).flatMap((v) => clozeOrdinals(v)))]
    : [1];
  const ordinal = ordinals.includes(state.ordinal) ? state.ordinal : ordinals[0] || 1;

  const { front, back } = renderCard(template, row.values, { ordinal });

  const doc = `<!doctype html><meta charset="utf-8">
    <!-- Same reason as the referrerpolicy on the frame itself: an embed with no
         referrer is refused by YouTube with "Error 153". -->
    <meta name="referrer" content="strict-origin-when-cross-origin">
    <style>
      html { color-scheme: light dark; }
      body { margin: 0; padding: 18px; font-family: arial, sans-serif; font-size: 20px;
             text-align: center; color: #111; background: #fff; }
      @media (prefers-color-scheme: dark) { body { color: #e6e9ee; background: #1b1f25; } }
      hr#answer { margin: 16px 0; border: 0; border-top: 1px solid currentColor; opacity: .25; }
      .cloze { color: #2f6fd0; font-weight: 700; }
      a.hint { color: #2f6fd0; font-size: 15px; }
      button.tts { font: inherit; font-size: 14px; padding: 2px 10px; cursor: pointer;
                   border: 1px solid currentColor; border-radius: 999px;
                   background: transparent; color: inherit; opacity: .8; }
      img, video, iframe { max-width: 100%; }
    </style>
    <body class="card">
      ${state.tab === "back" ? back.html : front.html}
      ${state.tab === "both" ? '<hr id="answer">' + backOnly(back.html, front.html) : ""}
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

  const unknown = [...new Set([...front.unknownFilters, ...back.unknownFilters])];
  const missing = [...new Set([...front.missingFields, ...back.missingFields])];

  return `
    ${
      templates.length > 1 || ordinals.length > 1
        ? `<div class="cardbar">
            ${
              templates.length > 1
                ? `<select id="tpl" aria-label="Card template">${templates
                    .map((t, i) => `<option value="${i}" ${i === state.template ? "selected" : ""}>${escapeHtml(t.name)}</option>`)
                    .join("")}</select>`
                : ""
            }
            ${
              ordinals.length > 1
                ? `<select id="ord" aria-label="Cloze card">${ordinals
                    .map((n) => `<option value="${n}" ${n === ordinal ? "selected" : ""}>card c${n}</option>`)
                    .join("")}</select>`
                : ""
            }
          </div>`
        : ""
    }
    <!-- allow-same-origin is required, not incidental: a nested player inherits
         these flags, and in an opaque origin YouTube and Drive render a dead black
         box. Cells go in exactly as written, script and all, because Anki's webview
         runs them too and a preview that quietly filtered them would be reporting on
         a card nobody is going to see. -->
    <iframe id="card" title="Card preview"
            sandbox="allow-scripts allow-same-origin allow-popups allow-presentation"
            allow="fullscreen; encrypted-media; picture-in-picture; autoplay"
            srcdoc="${escapeHtml(doc)}"></iframe>
    ${
      row.kind !== "synced"
        ? `<p class="note ${row.kind}">${escapeHtml(
            t(row.kind === "invalid" ? "rowInvalid" : "rowSkipped"),
          )}</p>`
        : ""
    }
    ${
      row.clozeIn.length && !row.clozeIn.some((h) => a.sides.front.includes(h))
        ? `<p class="note invalid">${t(
            "clozeStranded",
            row.clozeIn.map(escapeHtml).join("</code>, <code>"),
          )}</p>`
        : ""
    }
    ${missing.length ? `<p class="note">${t("missingFields", missing.map(escapeHtml).join("</code>, <code>"))}</p>` : ""}
    ${unknown.length ? `<p class="note">${t("unknownFilters", unknown.map(escapeHtml).join("</code>, <code>"))}</p>` : ""}
    <p class="muted small" style="margin-top:10px">${escapeHtml(t("deckAndTags"))}
      <code>${escapeHtml(row.deck)}</code> · ${escapeHtml(t("tagsLabel"))}
      ${row.tags.map((tag) => `<span class="chip">${escapeHtml(tag)}</span>`).join("")}</p>
    <p class="muted small">${t("approxNote")}</p>`;
}

/** The answer side minus the repeated question, when the template used FrontSide. */
function backOnly(backHtml, frontHtml) {
  return backHtml.startsWith(frontHtml) ? backHtml.slice(frontHtml.length) : backHtml;
}

/** Hands the built package to the browser as a download. */
function downloadPackage() {
  const button = $("#apkg");
  const sheetId = state.sheetId || "sheet";
  button.disabled = true;
  status(t("packing"), "", true);
  try {
    // A copy, because the array Pyodide hands over is a view onto its heap and
    // the next Python call is free to reuse that memory.
    const bytes = new Uint8Array(buildPackage(sheetId));
    const url = URL.createObjectURL(
      new Blob([bytes], { type: "application/octet-stream" }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = `${state.deckName || "deck"}.apkg`;
    link.click();
    URL.revokeObjectURL(url);
    status(t("packed", Math.round(bytes.length / 1024)), "ok");
  } catch (err) {
    status(t("packFailed", err.message), "bad");
  } finally {
    button.disabled = false;
  }
}

function tabBar() {
  const visible = visibleRows();
  const at = visible.findIndex(({ i }) => i === state.row);
  return `
    ${CARD_TABS.map(
      (name) =>
        `<button data-tab="${name}" class="${state.tab === name ? "on" : ""}">` +
        `${escapeHtml(t("tab" + name[0].toUpperCase() + name.slice(1)))}</button>`,
    ).join("")}
    <span class="spacer"></span>
    <span class="nav">
      <button id="prev" title="${escapeHtml(t("prevRow"))}">←</button>
      <span class="at">${at + 1} / ${visible.length}</span>
      <button id="next" title="${escapeHtml(t("nextRow"))}">→</button>
    </span>`;
}

function statStrip({ stats, rows }) {
  const cells = [
    ["statRows", stats.total_table_lines],
    ["statWithId", stats.valid_note_lines],
    ["statSync", stats.sync_marked_lines],
    ["statNotes", stats.total_potential_anki_notes],
    ["statCloze", rows.filter((r) => r.cloze && r.kind === "synced").length],
    ["statDecks", new Set(rows.filter((r) => r.kind === "synced").map((r) => r.deck)).size],
  ];
  return cells
    .map(
      ([key, n]) =>
        `<div class="stat ${n === 0 && key === "statSync" ? "zero" : ""}">
           <b>${n}</b><span>${escapeHtml(t(key))}</span></div>`,
    )
    .join("");
}

/** Text that lives in index.html rather than in a render function. */
function paintStatic() {
  for (const el of document.querySelectorAll("[data-i18n]")) {
    el.innerHTML = t(el.dataset.i18n);
  }
  for (const el of document.querySelectorAll("[data-i18n-attr]")) {
    for (const pair of el.dataset.i18nAttr.split(",")) {
      const [attr, key] = pair.split(":");
      el.setAttribute(attr.trim(), t(key.trim()));
    }
  }
  $("#rows-legend").innerHTML =
    `${escapeHtml(t("rowsLegend"))} <span class="dot synced"></span> ${escapeHtml(t("legendSynced"))} · ` +
    `<span class="dot skipped"></span> ${escapeHtml(t("legendSkipped"))} · ` +
    `<span class="dot invalid"></span> ${escapeHtml(t("legendInvalid"))}. ` +
    escapeHtml(t("legendGhost"));

  $("#langs").innerHTML = LANGUAGES.map(
    (l) =>
      `<button data-lang="${l.code}" class="${lang() === l.code ? "on" : ""}"` +
      ` aria-pressed="${lang() === l.code}">${l.label}</button>`,
  ).join("");
}

function render() {
  const a = state.analysis;
  paintStatic();
  $("#app").hidden = false;
  $("#stats").hidden = false;
  $("#stats").innerHTML = statStrip(a);
  $("#tree").innerHTML = deckPanel(a);
  $("#rowlist").innerHTML = rowList();
  $("#rowcount").textContent = `${visibleRows().length}`;
  $("#tabs").innerHTML = tabBar();
  $("#view").innerHTML = state.tab === "template" ? templateView(a) : cardView(a);

  $("#detail").hidden = !state.detailOpen;
  $("#detail").innerHTML = state.detailOpen ? detailView(a) : "";
  $("#details-btn").setAttribute("aria-expanded", String(state.detailOpen));
  document.querySelector(".side").classList.toggle("open", state.detailOpen);

  const warnings = warningItems(a).length;
  $("#warncount").hidden = !warnings;
  $("#warncount").textContent = warnings;
}

// ---------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------

document.addEventListener("click", (e) => {
  const picker = e.target.closest("[data-lang]");
  if (!picker) return;
  setLang(picker.dataset.lang);
  // Everything on screen is produced by a render function, so switching
  // languages is a repaint rather than a reload — the sheet stays loaded.
  if (state.analysis) render();
  else paintStatic();
});

$("#go").addEventListener("click", preview);
$("#url").addEventListener("keydown", (e) => e.key === "Enter" && preview());
$("#deck").addEventListener("input", () => (deckNameEdited = true));
$("#details-btn").addEventListener("click", () => {
  state.detailOpen = !state.detailOpen;
  render();
});

$("#pick").addEventListener("click", () => $("#file").click());
$("#file").addEventListener("change", (e) => {
  const file = e.target.files[0];
  // Cleared so that choosing the same file twice fires a change event again —
  // the obvious thing to do after editing it and wanting the new version.
  e.target.value = "";
  if (file) previewFile(file);
});

// ---- drag and drop --------------------------------------------------------

// Counted rather than toggled: dragging across a child element fires leave on the
// one being left before enter on the one being entered, so a plain flag flickers.
let dragDepth = 0;
const draggingFile = (e) => [...(e.dataTransfer?.types || [])].includes("Files");

addEventListener("dragenter", (e) => {
  if (!draggingFile(e) || $("#pick").disabled) return;
  e.preventDefault();
  dragDepth += 1;
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
  const file = e.dataTransfer.files[0];
  if (file && !$("#pick").disabled) previewFile(file);
});

document.addEventListener("click", (e) => {
  const tab = e.target.closest("[data-tab]");
  if (tab) {
    state.tab = tab.dataset.tab;
    return render();
  }
  const deckEl = e.target.closest("[data-deck]");
  if (deckEl) {
    state.deckFilter = deckEl.dataset.deck || null;
    const first = visibleRows()[0];
    if (first) state.row = first.i;
    return render();
  }
  const rowEl = e.target.closest("[data-row]");
  if (rowEl) {
    state.row = Number(rowEl.dataset.row);
    state.template = 0;
    return render();
  }
  if (e.target.id === "apkg") return downloadPackage();
  if (e.target.id === "prev" || e.target.id === "next") {
    const visible = visibleRows();
    if (!visible.length) return;
    const at = visible.findIndex(({ i }) => i === state.row);
    const step = e.target.id === "next" ? 1 : -1;
    state.row = visible[(at + step + visible.length) % visible.length].i;
    return render();
  }
});

document.addEventListener("change", (e) => {
  if (e.target.id === "tabpick") return showUpload(Number(e.target.value));
  if (e.target.id === "tpl") state.template = Number(e.target.value);
  else if (e.target.id === "ord") state.ordinal = Number(e.target.value);
  else return;
  render();
});

addEventListener("message", (e) => {
  const frame = $("#card");
  if (frame && e.data?.h) frame.style.height = `${e.data.h + 8}px`;
});

paintStatic();
status(t("loading"), "", true);
$("#url").value = new URLSearchParams(location.search).get("url") || DEMO_SHEET;

boot()
  .then(preview)
  .catch((err) => status(t("bootFailed", err.message), "bad"));
