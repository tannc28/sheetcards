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
// to find out.
//
// The workbook lives in this repository (examples/, built by
// scripts/build_examples.py) rather than in somebody's Google Drive, so the sheet
// the docs describe and the sheet the page loads cannot drift apart — a directive
// added to the add-on gets an example in the same commit.
// Overridden by ?url=, and by anything typed into the field.
const DEMO_SHEET =
  "https://github.com/tannc28/sheets2anki/blob/main/examples/sheets2anki-examples.xlsx";

// Which of its sheets to open on. The workbook is a tour that starts at the
// smallest sheet that works, and a landing page showing two columns and no
// settings row would answer none of the questions people arrive with — so the
// page opens on the one that uses everything at once, and the picker walks back.
const DEMO_TAB = "15 Everything";

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
from s2a.column_model import clean, deck_path
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


def _headers(headers):
    """The sheet's headers, cleaned, in order, repeats and blanks dropped."""
    out = []
    for raw in headers:
        name = clean(raw)
        if name and name not in out:
            out.append(name)
    return out


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
            "deck": tm.get_subdeck_name(root, deck_path(note, plan, cfg)),
            "tags": tm.build_tags(note, plan, cfg),
            "cloze": tm.row_has_cloze(note, plan),
            # Which columns carry the deletion, so the page can tell whether the
            # template will actually cloze them. See clozeTrouble() below.
            "clozeIn": [
                h for h in plan.content_headers
                if tm.has_cloze_deletion(str(note.get(h, "")))
            ],
            # Every column, not only the ones that become fields. Panel 1 offers
            # SYNC, TAGS and the SUBDECK columns to be looked at, and a cell it
            # was never sent reads as an empty cell — which is a lie about the
            # sheet, told in the one place built to answer questions about it.
            "values": {h: note.get(h, "") for h in _headers(headers)},
        })

    _STATE["deck"] = deck
    _STATE["rows"] = kept
    _STATE["name"] = deck_name

    front, back = split_sides(plan, cfg)
    return json.dumps({
        # What each column became, and what the settings row said about it. This
        # was dropped once, along with a reference table nobody read. It is back
        # because panel 1 now answers a question with it — "what did this column
        # turn into" is the commonest thing to be wrong about a sheet — and it is
        # read straight off the plan the parser already built, not recomputed.
        #
        # The header list keeps the sheet's own order and its repeats: a header
        # written twice is honoured once, and the page can only say which of the
        # two was ignored if it can see both.
        #
        # No backticks anywhere in this string. It is a JS template literal, and
        # one inside a Python comment closes it — the whole page then fails to
        # parse, with an error pointing at whatever word came next.
        "plan": {
            "id": plan.id_header,
            "sync": plan.sync_header,
            "tags": plan.tags_header,
            "subdecks": plan.subdeck_headers,
            "content": plan.content_headers,
            "headers": [clean(h) for h in headers if clean(h)],
        },
        "config": {
            "warnings": cfg.warnings,
            "subdecks": cfg.subdeck_columns,
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
    }, ensure_ascii=False)
`;

const $ = (sel) => document.querySelector(sel);
const state = {
  analysis: null, row: 0, template: 0, ordinal: 1, deckName: "", deckFilter: null,
  // Which column of the sheet is opened up in panel 1, by its position in the
  // header row, and whether the next repaint is the one that opened it.
  column: null, columnFlash: false,
  // What the .apkg derives its note ids from — a spreadsheet id for a link, the
  // file and tab for an upload. Either way it has to be the same next time or a
  // re-import duplicates every note instead of updating it.
  sheetId: "",
  // What the stage shows: the card, or its source the way Anki puts the template
  // editor beside it.
  tab: "both",
  // The three panels — where the sheet comes from, what deck it makes, what one
  // card looks like. Each one collapses to its own header, which is what makes
  // the page usable on a phone and what lets a wide window be given entirely to
  // whichever of the three is being read.
  panels: { source: true, deck: true, card: true },
};

const PANEL_ID = { source: "p-source", deck: "p-deck", card: "p-card" };

const WIDE = matchMedia("(min-width: 56rem)");
/** True on the layout where the panels are stacked rather than side by side. */
const narrow = () => !WIDE.matches;

function setPanel(name, open) {
  state.panels[name] = open;
  const el = document.getElementById(PANEL_ID[name]);
  el.dataset.open = String(open);
  el.querySelector(".panel-toggle").setAttribute("aria-expanded", String(open));
}

/**
 * Folding is a narrow-screen affordance.
 *
 * Side by side there is nothing to fold away — all three columns are already in
 * view — so the headers become plain labels: out of the tab order, and saying so
 * rather than announcing a button that will not do anything. Stacked, the three
 * columns are three screenfuls on top of each other and folding is the only way
 * to reach the third without scrolling past the first two.
 */
function applyWidth() {
  const wide = WIDE.matches;
  for (const id of Object.values(PANEL_ID)) {
    const toggle = document.querySelector(`#${id} .panel-toggle`);
    toggle.tabIndex = wide ? -1 : 0;
    toggle.setAttribute("aria-disabled", String(wide));
  }
  if (wide) for (const name of Object.keys(state.panels)) setPanel(name, true);
}
WIDE.addEventListener("change", applyWidth);
const CARD_TABS = ["front", "both", "back", "template"];
let analyze = null;
let buildPackage = null;
let readUpload = null;
let sheetNames = null;

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
  sheetNames = (bytes) => wb.sheet_names(bytes).toJs();
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
  // A column is chosen by position, and a different sheet has different columns
  // in those positions.
  state.column = null;
  render();

  const s = state.analysis.stats;
  status(
    t("readRows", s.total_table_lines, s.sync_marked_lines),
    s.sync_marked_lines ? "ok" : "bad",
  );
}

function failed(message) {
  status(message, "bad");
  document.body.classList.remove("ready");
  $("#p-deck").hidden = true;
  $("#p-card").hidden = true;
  $("#warnbar").hidden = true;
  // Back open: something has to be corrected, and the field that needs
  // correcting is the one a folded panel hides.
  setPanel("source", true);
}

/**
 * Names the loaded sheet in panel 1's header.
 *
 * A folded panel has only its header left to say what is inside it, so the
 * header carries the answer — and stacked, once the answer is there, the
 * question is a screenful in front of the two panels you came to read.
 */
function noteSource(name, tab) {
  const text = tab ? `${name} · ${tab}` : name;
  $("#source").textContent = text;
  $("#source").title = text;
  if (narrow()) setPanel("source", false);
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

    showUpload(isDemo ? demoTab(upload.bytes) : 0);
  } catch (err) {
    failed(err.message);
  } finally {
    $("#go").disabled = false;
  }
}

/** Where the example workbook should open, by name rather than by position.
 *
 *  Asked before the first read rather than after, so adding a sheet to the tour
 *  does not make the landing page draw one grid and then immediately redraw
 *  another. A name that is not in the file falls back to the first sheet.
 */
function demoTab(bytes) {
  try {
    const index = sheetNames(bytes).indexOf(DEMO_TAB);
    return index < 0 ? 0 : index;
  } catch {
    return 0;
  }
}

// ---------------------------------------------------------------------------
// Reading an uploaded file
// ---------------------------------------------------------------------------

/** The tab picker, drawn only for a workbook that has more than one grid. */
function paintTabs() {
  const el = $("#tabpick");
  const tabs = upload?.tabs || [];
  $("#tabfield").hidden = !tabs.length;
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
    noteSource(base, out.tabs.length ? out.tab : "");
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

function treeHtml(node, depth, lit) {
  return [...node.children.values()]
    .sort((a, b) => a.name.localeCompare(b.name))
    .map(
      (child) => `<li>
        <button data-deck="${escapeHtml(child.path)}" style="--depth:${depth}"
                class="${state.deckFilter === child.path ? "on" : ""}${
                  lit.deck === child.path ? " lit" + popping() : ""
                }">
          <span class="name">${escapeHtml(child.name)}</span>
          <span class="count">${child.count}</span>
        </button>
        ${child.children.size ? `<ul class="tree">${treeHtml(child, depth + 1, lit)}</ul>` : ""}
      </li>`,
    )
    .join("");
}

function deckPanel(a) {
  const { rows } = a;
  const lit = chosen(a);
  const tree = deckTree(rows);
  if (!tree.count) return `<p class="empty">${escapeHtml(t("noSyncRows"))}</p>`;

  return `<ul class="tree">
    <li><button data-deck="" style="--depth:0"
        class="${state.deckFilter === null ? "on" : ""}">
      <span class="name">${escapeHtml(t("allDecks"))}</span><span class="count">${tree.count}</span>
    </button></li>
    ${treeHtml(tree, 0, lit)}
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

const BARE_URL = /^https?:\/\/\S+$/i;

/**
 * What to call a row in the list.
 *
 * The obvious answer — the first front column — is wrong whenever that column is
 * a picture or a recording, because then it holds nothing but an address and the
 * list becomes eighty rows of `https://upload.wikimedia.org/…` that name nothing.
 * So: the first front column that reads as words, and only then an address.
 */
function rowLabel(row, front) {
  const values = front.map((h) => String(row.values[h] ?? "").trim()).filter(Boolean);
  return values.find((v) => !BARE_URL.test(v)) || values[0] || row.id || "—";
}

function rowList() {
  const visible = visibleRows();
  if (!visible.length) return `<p class="empty">${escapeHtml(t("noRowsHere"))}</p>`;

  const front = state.analysis.sides.front;
  return visible
    .map(
      ({ r, i }) => `<button class="rowitem row-${r.kind} ${i === state.row ? "on" : ""}"
        data-row="${i}" title="row ${r.line} — ${escapeHtml(r.kind)}">
        <span class="n">${r.line}</span>
        <span class="dot ${r.kind}"></span>
        <span class="txt">${escapeHtml(rowLabel(r, front))}</span>
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
// The stage — the card, or the template it came from
// ---------------------------------------------------------------------------

function templateView(a) {
  const row = a.rows[state.row];
  const templates = row?.cloze ? a.templates.cloze : a.templates.basic;
  const template = templates[Math.min(state.template, templates.length - 1)];
  return `<div class="stagebox">
    <p class="muted small">${t(
      "templateFrom",
      escapeHtml(row?.cloze ? a.noteTypes.cloze : a.noteTypes.basic),
    )}</p>
    <h2 class="src-head">${escapeHtml(t("frontTemplate"))}</h2>
    <pre class="source">${escapeHtml(template.qfmt)}</pre>
    <h2 class="src-head">${escapeHtml(t("backTemplate"))}</h2>
    <pre class="source">${escapeHtml(template.afmt)}</pre>
  </div>`;
}

function cardView(a) {
  const row = a.rows[state.row];
  if (!row) {
    return `<div class="stagebox"><p class="empty">${escapeHtml(t("noRowsAtAll"))}</p></div>`;
  }

  const lit = chosen(a);
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
      ${
        lit.field
          ? `/* Panel 1 has a column open; this is the block it made. The card is
                its own document, so the ring is written into the card's own
                stylesheet on the way in rather than reached for afterwards —
                there is no frame to wait for and nothing to clean up when the
                selection changes, because the frame is rebuilt either way. */
             [data-s2a-col="${lit.field.replace(/["\\]/g, "\\$&")}"] {
               outline: 2px solid #1a73e8; outline-offset: 6px; border-radius: 4px;
               ${
                 state.columnFlash
                   ? "animation: s2a-pop .5s cubic-bezier(.2, .8, .2, 1);"
                   : ""
               }
             }
             @keyframes s2a-pop {
               0%   { transform: translateY(0)    scale(1); }
               35%  { transform: translateY(-8px) scale(1.06); }
               70%  { transform: translateY(2px)  scale(.99); }
               100% { transform: translateY(0)    scale(1); }
             }
             @media (prefers-reduced-motion: reduce) {
               [data-s2a-col] { animation: none; }
             }`
          : ""
      }
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

  return `<div class="stagebox">
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
    <p class="cardmeta">${escapeHtml(t("deckAndTags"))}
      <code>${escapeHtml(row.deck)}</code> · ${escapeHtml(t("tagsLabel"))}
      ${row.tags
        .map((tag) => `<span class="chip${lit.tags ? " lit" + popping() : ""}">${escapeHtml(tag)}</span>`)
        .join("")}</p>
    <p class="muted small approx">${t("approxNote")} ${t("runsAsAnki")}</p>
  </div>`;
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
      <button id="prev" type="button" aria-label="${escapeHtml(t("prevRow"))}"
              title="${escapeHtml(t("prevRow"))}">←</button>
      <span class="at">${at + 1} / ${visible.length}</span>
      <button id="next" type="button" aria-label="${escapeHtml(t("nextRow"))}"
              title="${escapeHtml(t("nextRow"))}">→</button>
    </span>`;
}

/** The counts as one readable line. Six equal tiles said nothing about which of
 *  them mattered; only "marked for sync" is ever a problem, so only it is red. */
function summaryLine(a) {
  const { stats, rows } = a;
  const lit = chosen(a);
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
        `<span class="${n === 0 && key === "statSync" ? "zero" : ""}${
          lit.stat === key ? " lit" + popping() : ""
        }">` + `<b>${n}</b> ${escapeHtml(t(key))}</span>`,
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
  document.body.classList.add("ready");
  $("#p-deck").hidden = false;
  $("#p-card").hidden = false;
  $("#summary").innerHTML = summaryLine(a);
  $("#tree").innerHTML = deckPanel(a);
  $("#rowlist").innerHTML = rowList();
  $("#rowcount").textContent = `${visibleRows().length}`;
  $("#tabs").innerHTML = tabBar();
  $("#view").innerHTML = state.tab === "template" ? templateView(a) : cardView(a);

  $("#columns").hidden = false;
  $("#colcount").textContent = `${a.plan.headers.length}`;
  $("#collist").innerHTML = columnList(a);
  $("#coldetail").innerHTML = state.column == null ? "" : columnDetail(a);
  // The flash and the scroll both mark *choosing a column*. Every other repaint
  // — a row picked, a language switched — would otherwise blink a panel nobody
  // was looking at, and move the page under a reader who asked for nothing.
  if (state.columnFlash) revealField(chosen(a).field);
  state.columnFlash = false;

  // Each header says what its panel holds, because that sentence is all a shut
  // panel has left.
  const synced = a.rows.filter((r) => r.kind === "synced");
  $("#deck-note").textContent = t(
    "deckNote",
    a.stats.sync_marked_lines,
    a.stats.total_table_lines,
    new Set(synced.map((r) => r.deck)).size,
  );
  const row = a.rows[state.row];
  $("#card-note").textContent = row
    ? t("cardNote", row.line, rowLabel(row, a.sides.front))
    : "";

  // Above the working area rather than behind a drawer: a sheet that warns is
  // telling you the cards will come out wrong, which is the one thing on this
  // page nobody should have to go looking for.
  const warnings = warningItems(a);
  $("#warnbar").hidden = !warnings.length;
  $("#warncount").textContent = warnings.length ? `(${warnings.length})` : "";
  $("#warnlist").innerHTML = warnings.join("");
}

// ---------------------------------------------------------------------------
// Panel 1 — what each column turned into
// ---------------------------------------------------------------------------

/**
 * The role a header ended up with, as `{kind, label}`.
 *
 * Read off the plan the parser produced rather than worked out again from the
 * header text: the rules for what counts as `SUBDECK 2` live in
 * `column_model.py`, and a second copy of them here would be a second answer.
 */
function columnRole(name, index, a) {
  const p = a.plan;
  // A header written twice is honoured once. The first one is the column; every
  // later one is inert, and saying so is the whole reason both are listed.
  if (p.headers.indexOf(name) !== index) {
    return { kind: "dead", label: t("roleDuplicate") };
  }
  if (name === p.id) return { kind: "key", label: t("roleId") };
  if (name === p.sync) return { kind: "gate", label: t("roleSync") };
  if (name === p.tags) return { kind: "tag", label: t("roleTags") };

  const reserved = p.subdecks.indexOf(name);
  if (reserved >= 0) {
    return { kind: "deck", label: t("roleSubdeck", reserved + 1) };
  }
  const declared = (a.config.subdecks || []).indexOf(name);
  // Said by the settings row rather than by the header, but the same job and the
  // same result: the note is filed, and nothing of it reaches the card.
  if (declared >= 0) return { kind: "deck", label: t("roleSubdeckOnly", declared + 1) };
  if (p.content.includes(name)) {
    return { kind: "field", label: t("roleField", side(name, a)) };
  }
  return { kind: "dead", label: t("roleUnused") };
}

/**
 * What the chosen column, if any, points at elsewhere on the page.
 *
 * Answering "what did this column become" in words and leaving the reader to go
 * find it is half an answer. Everything below returns something the other two
 * panels can light up at the same moment, so the word and the thing arrive
 * together.
 *
 * @returns {{name: string|null, field: string|null, deck: string|null,
 *            tags: boolean, stat: string|null}}
 */
/** True only while drawing the repaint that a column was just chosen on. */
function popping() {
  return state.columnFlash ? " pop" : "";
}

function chosen(a) {
  const blank = { name: null, field: null, deck: null, tags: false, stat: null };
  if (state.column === null) return blank;

  const name = a.plan.headers[state.column];
  if (name === undefined) return blank;
  const role = columnRole(name, state.column, a);
  const at = { ...blank, name };

  if (role.kind === "dead") return at;
  if (name === a.plan.id) return { ...at, stat: "statWithId" };
  if (name === a.plan.sync) return { ...at, stat: "statSync" };
  if (name === a.plan.tags) return { ...at, tags: true };

  // A deck level points at the branch *this row* lands in, which is why the row
  // shows its own value for the column right beside it.
  const levels = a.config.subdecks.length ? a.config.subdecks : a.plan.subdecks;
  if (levels.includes(name)) {
    at.deck = branchFor(name, levels, a);
    at.stat = "statDecks";
  }
  // A column can be both — that is the whole point of `subdeck=n`.
  if (a.plan.content.includes(name)) at.field = name;
  return at;
}

/**
 * The deck this column files the selected row into, or null.
 *
 * Rebuilt from the row's own cells rather than sliced off `row.deck`: an empty
 * level is dropped from the path, so the third column is not always the third
 * segment of the name.
 */
function branchFor(name, levels, a) {
  const row = a.rows[state.row];
  if (!row) return null;

  // Sliced off the deck name the add-on itself produced rather than rebuilt from
  // the cells: a level is cleaned on its way into a deck name — `::` and a few
  // other characters cannot survive there — so the cell and the segment are not
  // always the same text. Only the *count* of levels is taken from the cells.
  const root = `s2a_${state.deckName}`.split("::").length;
  let depth = 0;
  for (const level of levels) {
    const filled = String(row.values[level] ?? "").trim() !== "";
    if (level === name) {
      return filled ? row.deck.split("::").slice(0, root + depth + 1).join("::") : null;
    }
    if (filled) depth += 1;
  }
  return null;
}

/**
 * Brings the ringed block into view, for a card taller than the panel.
 *
 * Only ever called from the click that opened a column: scrolling is a strong
 * thing to do to somebody, and doing it on every repaint — a row picked, a
 * language switched — would move the page under a reader who asked for nothing.
 *
 * The card is a same-origin srcdoc frame, so its elements can be reached and
 * `scrollIntoView` carries through the frame boundary to the panel outside it.
 */
function revealField(name) {
  const frame = $("#card");
  if (!frame || !name) return;
  const go = () => {
    try {
      const el = frame.contentDocument?.querySelector(
        `[data-s2a-col="${name.replace(/["\\]/g, "\\$&")}"]`,
      );
      // "nearest" so a block already on screen does not move: the hop is the
      // motion, and sliding the card as well would be two things at once.
      el?.scrollIntoView({ block: "nearest", behavior: "auto" });
    } catch {
      // A frame that cannot be read is not worth breaking the page over. The
      // ring is already drawn; only the scroll is lost.
    }
  };
  if (frame.contentDocument?.readyState === "complete") go();
  else frame.addEventListener("load", go, { once: true });
}

/** Where a content column is rendered on the card. */
function side(name, a) {
  if (a.sides.front.includes(name)) return t("sideFront");
  if (a.sides.back.includes(name)) return t("sideBack");
  return t("sideHidden");
}

/** The settings row's directives for a column, as `key=value` text. */
function directives(name, a) {
  const set = (a.config.fields || {})[name] || {};
  return Object.entries(set).map(([key, value]) => {
    if (value === true) return key;
    if (Array.isArray(value)) return `${key}=${value.join(",")}`;
    // `media` is stored as the kind it holds, which reads better as the word the
    // sheet actually wrote than as `media=image`.
    if (key === "media") return String(value);
    if (key === "type_answer") return value === "nc" ? "type=nc" : "type";
    return `${key}=${value}`;
  });
}

function columnList(a) {
  return a.plan.headers
    .map((name, i) => {
      const role = columnRole(name, i, a);
      const on = state.column === i ? " on" : "";
      return `<button class="col col-${role.kind}${on}" data-col="${i}"
        aria-pressed="${state.column === i}">${escapeHtml(name)}</button>`;
    })
    .join("");
}

/**
 * The chosen column, opened up: what it became, what the settings row said, what
 * this row actually holds in it, and anything the add-on could not understand.
 */
function columnDetail(a) {
  const name = a.plan.headers[state.column];
  if (name === undefined) return "";

  const role = columnRole(name, state.column, a);
  const set = directives(name, a);
  const row = a.rows[state.row];
  const value = row ? String(row.values[name] ?? "") : "";
  // The warnings name their column in single quotes, which is also how a person
  // reading them finds the one they are looking at.
  const said = (a.config.warnings || []).filter((w) => w.startsWith(`'${name}':`));

  return `<div class="coldetail${state.columnFlash ? " flash" : ""}">
    <p class="colrole"><span class="mark ${role.kind}"></span>${escapeHtml(role.label)}</p>
    ${
      set.length
        ? `<p class="colset">${set
            .map((d) => `<span class="chip">${escapeHtml(d)}</span>`)
            .join("")}</p>`
        : `<p class="muted small">${escapeHtml(t("nothingSet"))}</p>`
    }
    ${
      row
        ? `<p class="colvalue"><span class="k">${escapeHtml(
            t("valueInRow", row.line),
          )}</span> ${
            value
              ? `<code>${escapeHtml(value)}</code>`
              : `<span class="muted">${escapeHtml(t("cellEmpty"))}</span>`
          }</p>`
        : ""
    }
    ${said
      .map((w) => `<p class="colwarn">${escapeHtml(w)}</p>`)
      .join("")}
  </div>`;
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

// A real form, so Enter submits from either field the way it does everywhere else
// and the browser supplies the keyboard's "go" key on a phone.
$("#entry-form").addEventListener("submit", (e) => {
  e.preventDefault();
  preview();
});

document.addEventListener("click", (e) => {
  const head = e.target.closest(".panel-toggle");
  if (!head || !narrow()) return;
  const name = head.id.replace("-toggle", "").replace("src", "source");
  setPanel(name, !state.panels[name]);
  // Re-opening panel 1 means the link is about to be replaced, so put the cursor
  // where the work is.
  if (name === "source" && state.panels.source) {
    $("#url").focus();
    $("#url").select();
  }
});

$("#deck").addEventListener("input", () => (deckNameEdited = true));
// Applied on commit rather than only on the next Preview: typing a deck name and
// watching nothing happen reads as a control that does not work.
$("#deck").addEventListener("change", () => {
  if (upload && $("#deck").value.trim()) showUpload(upload.index);
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
  const col = e.target.closest("[data-col]");
  if (col) {
    const index = Number(col.dataset.col);
    // Clicking the open one shuts it: the detail is an answer to a question, and
    // there has to be a way to stop asking without picking something else.
    state.column = state.column === index ? null : index;
    state.columnFlash = state.column !== null;
    return render();
  }
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
    render();
    // Stacked, the card is below a list long enough to scroll: picking a row is
    // the moment you stop browsing and start reading, so the list folds away and
    // the card comes to you. Side by side it is already on screen.
    if (narrow()) {
      setPanel("deck", false);
      document.getElementById("p-card").scrollIntoView({ block: "start" });
    }
    return;
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
// Written into the DOM rather than left implicit, so `data-open` and
// `aria-expanded` say the same thing from the first paint.
for (const name of Object.keys(state.panels)) setPanel(name, state.panels[name]);
applyWidth();
status(t("loading"), "", true);
$("#url").value = new URLSearchParams(location.search).get("url") || DEMO_SHEET;

boot()
  .then(preview)
  .catch((err) => status(t("bootFailed", err.message), "bad"));
