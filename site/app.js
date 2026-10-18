/**
 * SheetCards Sheet to Anki — runs the add-on's own Python in the browser.
 *
 * The point of this page is that it does not reimplement anything. Pyodide loads
 * the very files under src/ that the add-on runs inside Anki, so the column
 * roles, the settings row, the warnings, the deck paths, the card templates and
 * the .apkg itself are produced by the same code that will produce them at sync
 * time. The only part written for the browser is site/anki.js, which stands in
 * for Anki's own template renderer — see that file for why that one cannot be
 * reused.
 *
 * The page is three steps — a sheet, its cards, the file — and is laid out as
 * that sequence (see create.html and the CLAUDE.md section on the website).
 */

// First, so a fragment carried through Chrome's intent link is back before
// anything reads it.
import { mountInAppBanner } from "./inapp.js";
import { renderCard, clozeOrdinals, escapeHtml } from "./anki.js";
import { LANGUAGES, lang, paintStrings, setLang, t } from "./i18n.js";
import { FIRST_LOAD_BYTES, mb, onMobileData, startPython } from "./pyodide.js";
import { cardDoc, cardFrame } from "./cardframe.js";
import { deckTree, treeHtml } from "./decktree.js";
import { dropHandoff, takeHandoff } from "./handoff.js";
import { site } from "./paths.js";
import { CREATE_STATE, clearState, readState, writeState } from "./urlstate.js";
import { decodeShare, isShare } from "./sharelink.js";
import { DEVICES, DEVICE_LABELS, DEVICE_STEPS, detectDevice } from "./devices.js";
import { icon, paintIcons } from "./icons.js";
import { warningText } from "./sheetwarnings.js";
import { droppedTemplates, fileIdentity, fileStem, keepShape, lastShape, shapeChange } from "./identity.js";

// The example workbook lives in this repository (examples/, built by
// scripts/build_examples.py) rather than in somebody's Google Drive, so the sheet
// the docs describe and the sheet the page loads cannot drift apart — a directive
// added to the add-on gets an example in the same commit. Loaded by the "use the
// example" button, by create/#example, and by ?url= pointing at it.
const DEMO_SHEET =
  "https://github.com/tannc28/sheetcards/blob/main/examples/sheetcards-examples.xlsx";

// Which of its sheets to open on. The workbook is a tour that starts at the
// smallest sheet that works, and an example showing two columns and no settings
// row would answer none of the questions people arrive with — so the page opens
// on a sheet with a theme and a deck hierarchy, and the picker walks the rest.
const DEMO_TAB = "15 Theme + subdeck (màu, tầng)";

/** Everything the page needs, computed by the add-on's own code. */
const ANALYZER = String.raw`
import json
from sc import tsv_model as tm
from sc.card_layout import build_templates, split_sides
from sc.column_model import clean, deck_path
from sc.sheet_config import is_config_row, warning_codes
from sc.apkg import build_package, note_type_shape, resolve_identity

# The last analysis, so the package can be built from exactly the rows the page
# drew rather than by parsing the sheet a second time.
_STATE = {}


def _previous(last, key="fields"):
    """The fields (or template names) of this deck's last package, same kind only."""
    last = json.loads(last or "null") or {}
    kind = "cloze" if _STATE["deck"].sheet_config.cloze_field else "basic"
    return last.get(key) or [] if last.get("kind") == kind else []


def shape(last):
    """The note type the next package will carry, given the last one's."""
    deck = _STATE["deck"]
    return json.dumps(
        note_type_shape(
            deck.plan,
            deck.sheet_config,
            _previous(last),
            _previous(last, "templates"),
        ),
        ensure_ascii=False,
    )


def package_bytes(last):
    deck = _STATE["deck"]
    return build_package(
        _STATE["id"], _STATE["name"], deck.plan, deck.sheet_config, _STATE["rows"],
        previous_fields=_previous(last),
        previous_templates=_previous(last, "templates"),
    )


def _settings(cfg):
    """A FieldConfig as a plain dict of only what the sheet actually set."""
    return {k: v for k, v in vars(cfg).items() if v not in (None, False, [])}


# How many rows of the sheet the grid in the Sheet view carries. A spreadsheet runs to
# tens of thousands of rows and each one would become a table row in the page;
# this is a preview of the sheet, not a copy of it. What is cut is said out loud
# above the grid rather than silently missing.
_GRID_ROWS = 400


def _grid(headers, rows, offset):
    """The sheet as it is written, for the Sheet view to draw as a grid.

    Read off the parser rather than by splitting the TSV in the browser: a cell
    may hold a newline, and only the parser knows where a row really ends. Every
    row is here, including the ones no note comes from and the settings row,
    because the point of a grid is to be the spreadsheet.
    """
    names = [clean(h) for h in headers]
    body = rows[:_GRID_ROWS]
    width = max([len(names)] + [len(r) for r in body])
    named = [name for name in names if name]
    padded = (names + [""] * width)[:width]

    def line(cells):
        return [str(cell) for cell in (list(cells) + [""] * width)[:width]]

    return {
        "cells": [line(headers)] + [line(row) for row in body],
        # Which column of the plan each position is, so a click on the grid and a
        # click on the list below it open the same column. They are not the same
        # index: a blank header is a column of the sheet and not a column of the
        # plan.
        "cols": [named.index(n) if n in named else None for n in padded],
        "total": len(rows),
        "config": 2 if offset else None,
    }


def _headers(headers):
    """The sheet's headers, cleaned, in order, repeats and blanks dropped."""
    out = []
    for raw in headers:
        name = clean(raw)
        if name and name not in out:
            out.append(name)
    return out


def analyze(tsv, deck_name, sheet_id=""):
    log = []
    parsed = tm.parse_tsv_data(tsv, log)
    headers, plan = parsed["headers"], parsed["plan"]

    # The authoritative numbers: the same object the sync builds and reports from.
    deck = tm.build_remote_deck_from_tsv(parsed, "", log)
    cfg = deck.sheet_config

    # A sheet that names its deck is that deck, whatever file or link it came in.
    sheet_id, deck_name, named = resolve_identity(sheet_id, deck_name, cfg)

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
            # Every column, not only the ones that become fields. The Sheet view offers
            # SYNC, TAGS and the SUBDECK columns to be looked at, and a cell it
            # was never sent reads as an empty cell — which is a lie about the
            # sheet, told in the one place built to answer questions about it.
            "values": {h: note.get(h, "") for h in _headers(headers)},
        })

    _STATE["deck"] = deck
    _STATE["rows"] = kept
    _STATE["name"] = deck_name
    _STATE["id"] = sheet_id

    front, back = split_sides(plan, cfg)
    return json.dumps({
        "identity": {"id": sheet_id, "deck": deck_name, "named": named},
        # What each column became, and what the settings row said about it. This
        # was dropped once, along with a reference table nobody read. It is back
        # because the Sheet view answers a question with it — "what did this column
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
            "warningCodes": warning_codes(cfg.warnings),
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
        "grid": _grid(headers, parsed["rows"], offset),
        "stats": deck.get_statistics(),
        "duplicateIds": deck.duplicate_ids,
    }, ensure_ascii=False)
`;

const $ = (sel) => document.querySelector(sel);
const state = {
  analysis: null, row: 0, template: 0, ordinal: 1, deckName: "", deckFilter: null,
  // Which column of the sheet is opened up in the Sheet view, by its position in
  // the header row, and whether the next repaint is the one that opened it.
  column: null, columnFlash: false,
  // What the .apkg derives its note ids from — a spreadsheet id for a link, the
  // file and tab for an upload. Either way it has to be the same next time or a
  // re-import duplicates every note instead of updating it.
  sheetId: "",
  // The card is a flashcard: question first, the answer once asked for.
  answered: false,
  // "empty" (the link form), "loading" (a sheet is on its way), "review".
  stage: "empty",
  view: "grid",
  downloaded: false,
  device: detectDevice(navigator),
};

// Beside the card from here up; a bottom sheet below. The card needs ~22rem and
// the deck panel ~19rem, so two columns start being comfortable at 60rem.
const WIDE = matchMedia("(min-width: 60rem)");
// Wide enough for a third column: the Sheet view stops being a toggle under the
// card and stands open beside it, so a big screen shows the sheet and the card
// it makes at once instead of leaving both margins empty.
const XWIDE = matchMedia("(min-width: 100rem)");
const STILL = matchMedia("(prefers-reduced-motion: reduce)");
const TOUCH = matchMedia("(hover: none)");

let analyze = null;
let buildPackage = null;
let nextShape = null;
let readUpload = null;
let sheetNames = null;

// The file last dropped on the page, kept as bytes because changing tab re-reads
// it: a File object is gone once its input has moved on.
let upload = null;

// ---------------------------------------------------------------------------
// The three stages
// ---------------------------------------------------------------------------

/**
 * Which of the page's three states is showing.
 *
 * The link form and the deck are never on screen together: on a phone either
 * one is a screenful, and once there is a deck the question "which sheet" has
 * been answered — the source bar above the card keeps the answer, the sheet
 * picker and the reload button, and "change link" brings the form back.
 */
function setStage(stage) {
  state.stage = stage;
  $("#app").dataset.stage = stage;
  $("#entry").hidden = stage !== "empty";
  $("#deck").hidden = stage === "empty";
  $("#skeleton").hidden = stage !== "loading";
  $("#loadline").hidden = stage !== "loading";
  if (stage === "empty") $("#toast").hidden = true;
  paintTitle();
  paintRail();
  placeDeckPanel();
  placeSheetView();
}

/** The browser tab: the sheet's name once there is one, so two open tabs — or
 *  two entries in the history — can be told apart. */
function paintTitle() {
  document.title =
    state.stage === "review" && state.deckName
      ? t("titleDeck", state.deckName.split("::").pop())
      : t("titleCreate");
}

/** The step rail: what is done, what is now, what is next. */
function paintRail() {
  const now = state.stage === "review" ? (state.downloaded ? 3 : 2) : 1;
  for (const li of document.querySelectorAll("#rail li")) {
    const n = Number(li.dataset.step);
    const done = n < now || (n === 3 && state.downloaded);
    li.className = done ? "done" : n === now ? "now" : "";
    if (n === now && !done) li.setAttribute("aria-current", "step");
    else li.removeAttribute("aria-current");
    const back = li.querySelector(".rail-go");
    if (back) back.disabled = !(done && state.stage === "review");
    const mark = li.querySelector(".rail-n");
    mark.innerHTML = done ? icon("check") : `<span>${n}</span>`;
  }
}

// ---------------------------------------------------------------------------
// Status: one voice at a time
// ---------------------------------------------------------------------------

let toastTimer = 0;

/**
 * Says what is happening, wherever the reader is looking.
 *
 * Under the link field while the form is up; over the card placeholder while a
 * sheet is on its way; as a toast once the deck is showing, since by then the
 * form is gone. Only one of the three is ever written, so a screen reader hears
 * each message once.
 *
 * @param {""|"ok"|"bad"} kind
 * @param {boolean} busy  spin while something is genuinely running, so a still
 *   page reads as finished rather than as hung
 */
function status(text, kind = "", busy = false) {
  const line = $("#status");
  const load = $("#loadline");
  const toast = $("#toast");
  clearTimeout(toastTimer);

  if (state.stage === "empty") {
    $("#status-text").textContent = text;
    line.className = `status ${kind} ${busy ? "busy" : ""}`;
    line.hidden = !text;
    toast.hidden = true;
    return;
  }
  if (state.stage === "loading") {
    load.innerHTML = `<span class="spinner" aria-hidden="true"></span><span>${escapeHtml(text)}</span>`;
    load.className = `loadline ${kind} busy`;
    return;
  }
  toast.hidden = !text;
  if (!text) return;
  toast.innerHTML =
    (busy ? '<span class="spinner" aria-hidden="true"></span>' : kind === "ok" ? icon("check") : kind === "bad" ? icon("circle-alert") : "") +
    `<span>${escapeHtml(text)}</span>`;
  toast.className = `toast ${kind} ${busy ? "busy" : ""}`;
  // Long enough to be read: a sentence of advice needs more than a "Copied".
  if (!busy) toastTimer = setTimeout(() => (toast.hidden = true), Math.max(4200, text.length * 60));
}

// ---- the first load --------------------------------------------------------
//
// Sheet to Anki is the add-on's own Python, and on a first visit that is about
// 5 MB from a CDN. The wait is said in a learner's words, with its size and the
// fact that it happens once; after ten seconds it says the network is slow,
// because a spinner that has turned for that long reads as broken. The form is
// never disabled for it: a link pasted while it loads is taken, said so, and run
// the moment Python is ready.
const booting = { step: "boot", slow: false, queued: false, done: false, failed: false, bytes: 0 };
let pending = null;

function bootStatus() {
  if (booting.failed) return;
  if (booting.done) {
    if (state.stage === "empty") status(t("readyNow"), "ok");
    return;
  }
  const loading =
    booting.step !== "boot"
      ? t("loadingCode")
      : booting.bytes
        ? t("bootingMB", mb(booting.bytes), mb(FIRST_LOAD_BYTES))
        : t("booting");
  status(
    [
      booting.queued && t(booting.queued === "file" ? "queuedFile" : "queued"),
      loading,
      onMobileData() && t("bootData", mb(FIRST_LOAD_BYTES)),
      booting.slow && t("slowBoot"),
    ]
      .filter(Boolean)
      .join(" "),
    "",
    true,
  );
}

/** Runs `job` now, or once Python has loaded if it has not yet. */
function whenReady(job, what = "link") {
  if (booting.done) return job();
  pending = job;
  booting.queued = what;
  bootStatus();
}

async function boot() {
  const slow = setTimeout(() => {
    booting.slow = true;
    bootStatus();
  }, 10_000);
  let painted = 0;
  const py = await startPython(
    ANALYZER,
    (step) => {
      booting.step = step;
      bootStatus();
    },
    (done) => {
      booting.bytes = done;
      // Half a megabyte at a time: the line is a live region, and one redrawn per chunk is
      // a screen reader saying nothing else.
      if (done - painted >= 5e5 || done === FIRST_LOAD_BYTES) {
        painted = done;
        bootStatus();
      }
    },
  );
  clearTimeout(slow);

  const fn = py.globals.get("analyze");
  analyze = (tsv, deckName, sheetId) => JSON.parse(fn(tsv, deckName, sheetId));
  const pack = py.globals.get("package_bytes");
  buildPackage = (last) => pack(JSON.stringify(last)).toJs();
  const shapeOf = py.globals.get("shape");
  nextShape = (last) => JSON.parse(shapeOf(JSON.stringify(last)));
  const wb = py.pyimport("sc.workbook");
  readUpload = (bytes, name, index) =>
    JSON.parse(wb.read_upload(bytes, name, index));
  sheetNames = (bytes) => wb.sheet_names(bytes).toJs();
  booting.done = true;
}

/**
 * The last line of a Python traceback, which is the part written for a person.
 *
 * Pyodide surfaces a raised exception as a JS Error carrying the whole traceback
 * in its message. Shown unedited it buries the sentence workbook.py wrote under
 * twenty lines of frames.
 */
function pythonMessage(err) {
  const lines = String(err?.message || err).trimEnd().split("\n");
  const last = lines[lines.length - 1].trim();
  // A sheet with no ID column is the commonest first mistake there is, and the
  // parser's sentence for it is English and names a "mandatory header". Said
  // as what to do about it instead.
  if (/Mandatory header missing: 'ID'/.test(last)) return t("noIdColumn");
  if (/not UTF-8 text/.test(last)) return t("badEncoding");
  if (/Empty TSV data|No rows found in TSV data/.test(last)) return t("emptySheet");
  if (/has no content columns/.test(last)) return t("noContentColumns");
  if (/This is not a workbook|is named \.xlsx but is not one/.test(last)) return t("notAWorkbook");
  if (/old \.xls format/.test(last)) return t("oldXls");
  if (/has no sheets in it/.test(last)) return t("noSheets");
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
// these, and a page that accepted more would be making decks from something that
// cannot then be synced.
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

/**
 * The name to put on the deck.
 *
 * There used to be a field for this, seeded from the file and yours to correct.
 * It was the only control on the page that changed the *answer* rather than the
 * question, and it changed it into a guess: the add-on names a deck after the
 * spreadsheet and the sheet, so a name typed here made the page describe a deck
 * the sync would never produce. The file already said what it is called.
 */
function chooseDeckName(fallback) {
  return fallback || "Deck";
}

/** Everything from "we have the text" to "the page is drawn". */
function analyse(tsv, deckName, sheetId, { keepRow = false } = {}) {
  // Where the reader was. A reload is for looking at the row just edited, so
  // landing back on the deck's first row would answer the wrong question.
  const was = state.row;
  status(t("analysing"), "", true);
  state.analysis = analyze(tsv, deckName, sheetId);
  // What the sheet itself says wins: a name= is the deck and its identity.
  // Kept rather than recovered at download time: a file has no link to recover
  // it from, and the id is what makes a second import of the same sheet update
  // its notes instead of duplicating them.
  state.deckName = state.analysis.identity.deck;
  state.sheetId = state.analysis.identity.id;
  state.shape = null;
  state.change = null;
  state.dropped = [];
  try {
    const last = lastShape(state.sheetId);
    state.shape = nextShape(last);
    state.change = shapeChange(last, state.shape);
    state.dropped = droppedTemplates(last, state.shape);
  } catch {
    // Without a remembered package there is nothing to compare with.
  }
  state.row = state.analysis.rows.findIndex((r) => r.kind === "synced");
  if (state.row < 0) state.row = 0;
  // Only if the row is still there: a sheet can come back shorter than it went.
  if (keepRow && was < state.analysis.rows.length) state.row = was;
  state.template = 0;
  state.deckFilter = null;
  state.answered = false;
  if (!keepRow) state.downloaded = false;
  // A column is chosen by position, and a different sheet has different columns
  // in those positions.
  state.column = null;
  if (wanted && !keepRow) arriveAt(wanted);
  wanted = null;
  setStage("review");
  render();
  // The button that started this is gone with the form (and a side panel shown
  // beside the card takes focus for itself), so focus would otherwise fall back
  // to the top of the page; the card is where the next key press belongs. Not
  // on arrival from an address: nobody pressed anything, and a ring round Show
  // Answer would be the first thing on screen.
  const at = document.activeElement;
  if (fromPage && !keepRow && (!at || at === document.body || at.closest("#entry, #deckpanel"))) {
    $("#flip").focus({ preventScroll: true });
  }

  const s = state.analysis.stats;
  status(
    t("readRows", s.total_table_lines, s.sync_marked_lines),
    s.sync_marked_lines ? "ok" : "bad",
  );
}

/**
 * Puts a problem with the link under the link, or takes it away.
 *
 * The GOV.UK error-message pattern: the sentence sits beside the field it is
 * about, the field says it is invalid and points at the sentence, and the cursor
 * goes there — because the field is the thing that has to change.
 */
function fieldError(message) {
  const input = $("#url");
  $("#url-error").hidden = !message;
  $("#url-error-text").textContent = message || "";
  if (message) {
    input.setAttribute("aria-invalid", "true");
    input.setAttribute("aria-describedby", "url-error");
  } else {
    input.removeAttribute("aria-invalid");
    input.removeAttribute("aria-describedby");
  }
}

function failed(message, { field = false, share = false } = {}) {
  // Back to the form: something has to be corrected, and the form is where.
  // A deck left on screen under a failure would read as the thing that failed.
  setStage("empty");
  // Said once, in the place it belongs: a problem with the link is said at the
  // link, anything else on the status line.
  status(field ? "" : message, "bad");
  fieldError(field ? message : "");
  // A private sheet is the commonest failure by far, and the fix is four clicks
  // in Google Sheets: show them, rather than describe them.
  // And put away again when the next failure is about something else: left open,
  // it reads as the reason for a problem it has nothing to do with.
  $("#sharehint").open = share;
  if (field) $("#url").focus();
}

/**
 * What went wrong fetching a link, said as what to do about it.
 *
 * Only a Google link is told about sharing — a file on GitHub has no Share
 * button — and only a Google link is said to be a Google one. A private sheet
 * answers its export with a redirect to a sign-in page, which the browser
 * refuses to hand over cross-origin, so for Google a failed fetch while online
 * is almost always the sharing setting.
 */
function fetchProblem({ google, code = null, html = false }) {
  if (code === null && !html) {
    if (navigator.onLine === false) return t("offline");
    return t(google ? "notShared" : "fileUnreachable");
  }
  if (html) return t(google ? "notShared" : "notAFile");
  if (code === 404 || code === 410) return t("notFound", google);
  if (google && (code === 400 || code === 401 || code === 403)) return t("notShared");
  if (code === 401 || code === 403) return t("fileRefused");
  return t("httpError", code);
}

/** Names the loaded file in the source bar. Which of its sheets is loaded is
 *  said by the picker beside it, which is a control rather than a sentence. */
function noteSource(name) {
  $("#source").textContent = name;
  $("#source").title = name;
  $("#reload").hidden = false;
}

async function preview({ again = false } = {}) {
  let input = $("#url").value.trim();
  // A link without its https:// is still a link (and fetched without one, it
  // would be read as a path on this site).
  if (/^[\w-]+(\.[\w-]+)+\/\S*$/.test(input)) input = "https://" + input;
  if (!input) {
    fieldError(t("emptyLink"));
    $("#url").focus();
    return;
  }

  // Which sheet of the workbook was open. A reload that dropped you back on
  // sheet 1 would be a reload nobody uses twice.
  const at = again ? (upload?.index ?? 0) : null;

  $("#go").disabled = true;
  fieldError("");
  let bytes, res;
  const google = Boolean(spreadsheetId(input));
  try {
    const workbookUrl = toWorkbookUrl(input);
    if (!again) {
      setStage("loading");
      $("#source").textContent = sourceLabel(input);
    }
    status(t(again ? "reloading" : "downloading"), "", true);

    try {
      // Never the browser's copy. The whole question this page answers is what
      // the sheet says *now*, and a cached answer to that is a wrong answer —
      // which on a reload is also the only thing the reader asked for.
      res = await fetch(workbookUrl, { cache: "reload" });
    } catch {
      throw new Error(fetchProblem({ google }));
    }
    if (!res.ok) throw new Error(fetchProblem({ google, code: res.status }));
    bytes = new Uint8Array(await res.arrayBuffer());
    // An .xlsx is a ZIP and starts "PK". Anything else that came back with a 200
    // — a sign-in page, a file host's download page — is not the file.
    if (bytes[0] !== 0x50 || bytes[1] !== 0x4b) {
      throw new Error(fetchProblem({ google, html: true }));
    }
  } catch (err) {
    $("#go").disabled = false;
    // For a Google link every fetch failure but "offline" may be the sharing
    // setting — a private sheet can answer 404 as readily as a sign-in page.
    return failed(err.message, { field: true, share: google && navigator.onLine !== false });
  }

  try {
    // From here a link and a dropped file are the same thing: a spreadsheet file
    // with sheets in it. The sheet picker, the deck name and the package all come
    // out of the one path, so the page cannot treat them differently.
    upload = {
      bytes,
      name: `${deckNameFromHeaders(res) || fileNameFromUrl(input) || "Deck"}.xlsx`,
      // The key the add-on stores this deck under, so a package downloaded here
      // and a sync from the add-on agree about which notes are which.
      idBase: await sourceId(input),
      google: true,
      tabs: [],
      index: 0,
    };

    // The example has an address of its own (#example), so putting the workbook
    // link into the address bar would only make that longer for no gain.
    const isDemo = input === DEMO_SHEET;
    $("#demo-note").hidden = !isDemo;
    $("#editsheet").hidden = true;
    // A new deck starts from a clean address; where in it the reader is gets
    // written back once it is drawn (syncAddress).
    const url = clearState(location.href, CREATE_STATE);
    if (isDemo) {
      url.searchParams.delete("url");
      url.hash = "#example";
    } else {
      url.searchParams.set("url", input);
      url.hash = "";
    }
    rememberDeck(url);
    dropHandoff();

    upload.home = isDemo ? demoTab(upload.bytes) : 0;
    showUpload(at ?? wantedTab(upload.bytes) ?? upload.home, { keepRow: again });
  } catch (err) {
    failed(err.message);
  } finally {
    $("#go").disabled = false;
  }
}

/** What to call a link in the source bar before its file has said its name. */
function sourceLabel(url) {
  return (isFileUrl(url) && fileNameFromUrl(url)) || shortLink(url);
}

/** A link short enough for the source bar while the file's own name is unknown. */
function shortLink(url) {
  try {
    const u = new URL(url);
    return u.hostname.replace(/^www\./, "") + "/…";
  } catch {
    return url;
  }
}

/**
 * Reads the source again — the link refetched, the dropped file re-opened.
 *
 * The sheet is edited somewhere else and read here, so this is the loop the page
 * is actually used in: edit a row in Sheets, come back, press this, look at the
 * card again. It keeps the sheet of the workbook and the row you were on.
 *
 * A File is a reference rather than a copy, so re-reading one is only sometimes
 * possible: a spreadsheet app writing a new file over the old one leaves the
 * reference pointing at nothing, and the browser throws. That is said plainly
 * rather than left as a silent no-op, because "nothing happened" is exactly what
 * a stale preview looks like.
 */
async function reload() {
  if (!upload) return;
  if (!upload.file) return preview({ again: true });

  $("#reload").disabled = true;
  status(t("reloading"), "", true);
  try {
    upload.bytes = new Uint8Array(await upload.file.arrayBuffer());
  } catch {
    return failed(t("fileGone"));
  } finally {
    $("#reload").disabled = false;
  }
  showUpload(upload.index, { keepRow: true });
}

/** Where the example workbook should open, by name rather than by position.
 *
 *  Asked before the first read rather than after, so adding a sheet to the tour
 *  does not make the page draw one deck and then immediately redraw another. A
 *  name that is not in the file falls back to the first sheet.
 */
function demoTab(bytes) {
  try {
    const index = sheetNames(bytes).indexOf(DEMO_TAB);
    return index < 0 ? 0 : index;
  } catch {
    return 0;
  }
}

/** The sheet the address names (`tab=`), as a position, or null. */
function wantedTab(bytes) {
  if (!wanted?.tab) return null;
  try {
    const index = sheetNames(bytes).indexOf(wanted.tab);
    return index < 0 ? null : index;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Reading an uploaded file
// ---------------------------------------------------------------------------

/** The sheet picker, drawn only for a workbook that has more than one grid. */
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
function showUpload(index, { keepRow = false } = {}) {
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

    // A Google link keeps the name and the id it has always had; a file is
    // named and keyed without what a phone adds to a second download of it.
    const base = upload.google ? upload.name.replace(/\.[^.]+$/, "").trim() : fileStem(upload.name);
    noteSource(upload.name.replace(/\.[^.]+$/, "").trim());
    analyse(
      out.tsv,
      chooseDeckName(out.tabs.length ? `${base}::${out.tab}` : base),
      upload.google
        ? `${upload.idBase}#${out.tab}`
        : fileIdentity(upload.name, out.tabs.length ? out.tab : ""),
      { keepRow },
    );
    // Read, but in a Windows code page rather than UTF-8: said, because a
    // letter decoded wrong is a word learnt wrong.
    if (out.encoding) status(t("readAsEncoding", out.encoding), "bad");
  } catch (err) {
    // The add-on's own sentence, not the twenty lines of traceback above it.
    failed(pythonMessage(err));
  } finally {
    $("#pick").disabled = false;
  }
}

// What the file picker offers; a file dropped on the page is held to the same.
const FILE_TYPES = /\.(xlsx|xlsm|csv|tsv|txt)$/i;

/** A file picked or dropped here: read once Python is ready, if it is one. */
function openFile(file) {
  // Said before anything is read or queued: the parser's answer for a PDF is a
  // complaint about a missing ID column, which sends the reader looking in the
  // wrong place. A deck already on screen stays there under the toast.
  if (!FILE_TYPES.test(file.name)) return status(t("badFileType", file.name), "bad");
  fromPage = true;
  wanted = null;
  whenReady(() => previewFile(file), "file");
}

/**
 * @param {File} file
 * @param {{hash?: string, edit?: string}} [from] where the file came from: a
 *   shared link keeps its `#s=` in the address so a reload opens it again, and a
 *   sheet written in Create sheet gets a way back to it (`edit`, an address).
 */
async function previewFile(file, { hash = "", edit = "" } = {}) {
  setStage("loading");
  $("#source").textContent = file.name;
  status(t("reading"), "", true);
  try {
    upload = {
      bytes: new Uint8Array(await file.arrayBuffer()),
      name: file.name,
      tabs: [],
      index: 0,
      // Kept so the reload button has something to re-open. The bytes are read
      // eagerly all the same: changing tab re-reads them, and a File that has
      // moved on would leave the picker doing nothing.
      file,
    };
  } catch (err) {
    return failed(t("unreadableFile", err.message));
  }

  // Nothing about a local file can go in the address bar, so a ?url= left over
  // from a link would send the next person who opens it somewhere else entirely.
  const url = clearState(location.href, CREATE_STATE);
  url.searchParams.delete("url");
  url.hash = hash;
  rememberDeck(url);
  // A handed-over file is only kept for as long as it is what is open.
  if (hash !== "#file") dropHandoff();
  $("#demo-note").hidden = true;
  $("#editsheet").hidden = !edit;
  if (edit) $("#editsheet").href = edit;
  $("#url").value = "";
  // The link it complained about is gone, so the complaint goes with it.
  fieldError("");

  upload.home = 0;
  showUpload(wantedTab(upload.bytes) ?? 0);
}

// ---- the browser's Back button ---------------------------------------------
//
// The form and the deck are two screens to whoever is looking at them, so Back
// from a deck loaded on this page goes back to the form it was loaded from —
// with the link still in it — rather than off the site, and Forward brings the
// same deck back. A deck that arrived in the address (from the landing page, a
// bookmark, a shared link) replaces the entry instead: Back from there goes
// where the reader came from, not to an empty form they never saw.

/** True while a load was started by something done on this page. */
let fromPage = false;
/** Which history entry the deck in memory belongs to. */
let shownKey = 0;

function rememberDeck(url) {
  const was = history.state?.deck ? history.state : null;
  if (fromPage && !was) {
    shownKey = Date.now();
    history.pushState({ deck: "pushed", key: shownKey }, "", url);
  } else {
    shownKey = was?.key || Date.now();
    history.replaceState({ deck: was?.deck || "replaced", key: shownKey }, "", url);
  }
}

// ---- where in the deck the address says the reader is ----------------------
//
// Which sheet, deck, row, side and card are on screen, and whether the Sheet view
// is open, go into the query as the reader moves (urlstate.js), so the address
// copied from the bar opens the same card for whoever it is sent to. Replaced,
// never pushed: Back still goes from the deck to the form in one step.

/** What the address asked for, waiting for its deck to be read; then null. */
let wanted = null;

/** Puts the reader where `want` (read from an address) says, as far as it can. */
// A deck in the address is named below the sheet's own deck (Geography::Rivers),
// which is all of the name a reader would recognise; the root is the sheet's.
const deckRoot = () => `sc_${state.deckName}::`;
const shortDeck = (deck) => (deck?.startsWith(deckRoot()) ? deck.slice(deckRoot().length) : deck);

function arriveAt(want) {
  const rows = state.analysis.rows;
  const deck = want.deck && deckRoot() + want.deck;
  if (deck && rows.some((r) => r.deck === deck || r.deck.startsWith(`${deck}::`))) {
    state.deckFilter = deck;
    const first = visibleRows()[0];
    if (first) state.row = first.i;
  }
  if (want.row) {
    const at = rows.findIndex((r) => r.id === want.row);
    if (at >= 0) {
      state.row = at;
      // A row the deck filter would hide wins over the filter: the row is the
      // more particular thing to have asked for.
      if (!visibleRows().some(({ i }) => i === at)) state.deckFilter = null;
    }
  }
  if (want.card) state.template = want.card - 1;
  if (want.cloze) state.ordinal = want.cloze;
  state.answered = want.side === "back";
  if (want.view) {
    state.view = want.view;
    $("#sheetview").hidden = false;
    $("#open-sheet").setAttribute("aria-expanded", "true");
  }
}

/** Whether the address can bring this deck back: a link, the example, a shared
 *  sheet or a handed-over file. A file picked here cannot, so nothing is written. */
function addressable() {
  return Boolean(new URLSearchParams(location.search).get("url")) ||
    location.hash === "#example" || location.hash === "#file" || isShare(location.hash);
}

/** Where the reader is, as the address's query. */
function addressState() {
  const a = state.analysis;
  const card = currentCard(a);
  const tabs = upload?.tabs || [];
  // The row a plain visit would show: the first card, or the first in the deck picked.
  const first = state.deckFilter
    ? (visibleRows()[0]?.i ?? 0)
    : Math.max(0, a.rows.findIndex((r) => r.kind === "synced"));
  const row = card?.row;
  const open = $("#open-sheet").getAttribute("aria-expanded") === "true" && !$("#sheetview").dataset.beside;
  return {
    tab: tabs.length > 1 && upload.index !== (upload.home ?? 0) ? tabs[upload.index] : null,
    deck: shortDeck(state.deckFilter),
    row: row && row.id && state.row !== first ? row.id : null,
    side: state.answered ? "back" : null,
    card: card && card.templates.length > 1 ? Math.min(state.template, card.templates.length - 1) + 1 : null,
    cloze: card && card.ordinals.length > 1 && card.ordinal !== card.ordinals[0] ? card.ordinal : null,
    view: open || state.view !== "grid" ? state.view : null,
  };
}

/** Writes where the reader is into the address, if the address can say it. */
function syncAddress() {
  if (state.stage !== "review" || !state.analysis || wanted || !addressable()) return;
  const next = writeState(location.href, addressState(), CREATE_STATE);
  if (next.href !== location.href) history.replaceState(history.state, "", next);
}

/**
 * The source bar's share button: the address as it stands, which already says
 * which card is on screen. On a phone the system's share sheet (a chat app is
 * where a link goes from there); elsewhere the clipboard. A file opened from
 * this device has no address anybody else can open — #file is this browser's
 * own storage — so that is said instead, with the two ways to get one.
 */
async function shareCard() {
  if (!addressable() || location.hash === "#file") return status(t("shareCardFile"));
  syncAddress();
  const url = location.href;
  if (TOUCH.matches && navigator.share) {
    try {
      await navigator.share({ title: document.title, url });
    } catch {
      // Dismissed: nothing to say.
    }
    return;
  }
  try {
    await navigator.clipboard.writeText(url);
    status(t("shareCardCopied"), "ok");
  } catch {
    status(t("shareCardFailed"), "bad");
  }
}

/** The link form, with whatever link was last in it. */
function showForm({ focus = true } = {}) {
  // Whatever was waiting for Python is no longer what is wanted.
  pending = null;
  wanted = null;
  booting.queued = false;
  setStage("empty");
  bootStatus();
  if (focus) {
    $("#url").focus();
    $("#url").select();
  }
}

/** Starts the load the address asks for, if it asks for one. */
function loadFromAddress() {
  wanted = readState(location.search, CREATE_STATE);
  const asked = new URLSearchParams(location.search).get("url");
  if (asked) $("#url").value = asked;
  else if (location.hash === "#example") $("#url").value = DEMO_SHEET;
  else {
    // A handed-over file and a shared sheet are read from the address too, by
    // the start of this module; anything else has nothing to arrive at.
    if (location.hash !== "#file" && !isShare(location.hash)) wanted = null;
    return false;
  }
  fromPage = false;
  submit();
  return true;
}

addEventListener("popstate", (e) => {
  // A same-page anchor (the skip link) is an entry too, and not a screen.
  if (!e.state && location.hash && location.hash !== "#example") return;
  if (e.state?.deck) {
    if (e.state.key === shownKey && state.analysis) {
      setStage("review");
      render();
    } else if (!loadFromAddress()) showForm({ focus: false });
    return;
  }
  for (const dlg of document.querySelectorAll("dialog[open]:modal")) dlg.close();
  showForm({ focus: false });
});

/** Starts a load from whatever the form says, now or once Python is ready. */
function submit() {
  if (!$("#url").value.trim()) {
    fieldError(t("emptyLink"));
    $("#url").focus();
    return;
  }
  // Said straight away, with the form still usable: the card placeholder and
  // its status line take over the moment a link is accepted.
  if (!booting.done) {
    setStage("loading");
    $("#source").textContent = sourceLabel($("#url").value.trim());
  }
  whenReady(() => preview());
}

// ---------------------------------------------------------------------------
// The deck panel: the tree, the counts, the rows
// ---------------------------------------------------------------------------

function deckPanel(a) {
  const { rows } = a;
  const lit = chosen(a);
  const tree = deckTree(rows);
  if (!tree.count) return `<p class="empty">${escapeHtml(t("noSyncRows"))}</p>`;

  return `<ul class="tree">
    <li><button data-deck="" style="--depth:0"
        class="${state.deckFilter === null ? "on" : ""}"${
          state.deckFilter === null ? ' aria-current="true"' : ""
        }>
      <span class="name">${escapeHtml(t("allDecks"))}</span><span class="count">${tree.count}</span>
    </button></li>
    ${treeHtml(tree, {
      selected: state.deckFilter,
      lit: lit.deck,
      pop: popping(),
      pick: true,
    })}
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

/** A row's fate in words — the legend's own, so the list and its key agree. */
const KIND_LABEL = { synced: "legendSynced", skipped: "legendSkipped", invalid: "legendInvalid" };
const kindLabel = (kind) => t(KIND_LABEL[kind] || "legendSynced");

function rowList() {
  const visible = visibleRows();
  if (!visible.length) return `<p class="empty">${escapeHtml(t("noRowsHere"))}</p>`;

  const front = state.analysis.sides.front;
  return visible
    .map(
      // The dot's colour is backed by its shape (filled, hollow, diamond) for
      // whoever cannot tell green from red, and by words for a screen reader.
      ({ r, i }) => `<button class="rowitem row-${r.kind} ${i === state.row ? "on" : ""}"
        data-row="${i}" title="${escapeHtml(t("rowTitle", r.line, kindLabel(r.kind)))}"${
          i === state.row ? ' aria-current="true"' : ""
        }>
        <span class="n">${r.line}</span>
        <span class="dot ${r.kind}" aria-hidden="true"></span>
        <span class="sr-only">${escapeHtml(kindLabel(r.kind))}:</span>
        <span class="txt">${escapeHtml(rowLabel(r, front))}</span>
        ${r.cloze ? '<span class="pill cloze">cloze</span>' : ""}
      </button>`,
    )
    .join("");
}

/** The counts as one readable line. Only "marked for sync" is ever a problem,
 *  so only it turns red. */
function summaryLine(a) {
  const { stats, rows } = a;
  const lit = chosen(a);
  const cells = [
    ["statRows", stats.total_table_lines],
    ["statWithId", stats.valid_note_lines],
    ["statSync", stats.sync_marked_lines],
    ["statNotes", stats.total_potential_anki_notes],
    ["statCloze", rows.filter((r) => r.cloze && r.kind === "synced").length],
    ["statDecks", deckCount(a)],
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

const syncedRows = (a) => a.rows.filter((r) => r.kind === "synced");
const deckCount = (a) => new Set(syncedRows(a).map((r) => r.deck)).size;

/**
 * How many cards the package will hold — not rows, and not notes.
 *
 * A note makes one card per template (a reverse card doubles it), and a cloze
 * note one per deletion. The number on the download button is the number a
 * learner will see in Anki, so it is counted the way Anki will count it.
 */
function cardCount(a) {
  return syncedRows(a).reduce((n, row) => {
    if (!row.cloze) return n + a.templates.basic.length;
    const ords = new Set(Object.values(row.values).flatMap((v) => clozeOrdinals(v)));
    return n + Math.max(1, ords.size);
  }, 0);
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

/** The settings row's warnings in the page's language (sheetwarnings.js). */
function sheetWarnings(config) {
  const coded = config.warningCodes || (config.warnings || []).map((text) => ({ text }));
  return coded.map((w) => warningText(w, lang()));
}

function warningItems(analysis) {
  const { config, duplicateIds, sides } = analysis;
  const items = sheetWarnings(config).map(
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
// The card
// ---------------------------------------------------------------------------

/** The template the current row is drawn with, and the cloze card shown. */
function currentCard(a) {
  const row = a.rows[state.row];
  if (!row) return null;
  const templates = row.cloze ? a.templates.cloze : a.templates.basic;
  const template = templates[Math.min(state.template, templates.length - 1)];
  const ordinals = row.cloze
    ? [...new Set(Object.values(row.values).flatMap((v) => clozeOrdinals(v)))]
    : [1];
  const ordinal = ordinals.includes(state.ordinal) ? state.ordinal : ordinals[0] || 1;
  return { row, templates, template, ordinals, ordinal };
}

/**
 * Draws the current card into its slot.
 *
 * The question side until the answer is asked for, then the question with the
 * answer under a rule — what Anki shows after Show Answer. `typed` is whatever was
 * typed into a type-in box on the question, carried across so the answer side
 * compares it rather than an empty box.
 */
function paintCard({ typed = null } = {}) {
  const a = state.analysis;
  const slot = $("#cardslot");
  const card = currentCard(a);
  const visible = visibleRows();
  const at = visible.findIndex(({ i }) => i === state.row);

  $("#counter").textContent = visible.length ? `${at + 1} / ${visible.length}` : "";
  $("#prev").disabled = $("#next").disabled = visible.length < 2;
  // How many cards are left under this one, drawn as up to two edges of paper.
  $("#stack").dataset.depth = String(Math.max(0, Math.min(2, visible.length - at - 1)));

  $("#flip").disabled = !card;
  $("#flip-text").textContent = t(state.answered ? "flipBack" : "showAnswer");
  $("#flip").classList.toggle("answered", state.answered);
  $("#fliphint").textContent = card ? t(TOUCH.matches ? "flipHintTouch" : "flipHintKeys") : "";

  if (!card) {
    slot.innerHTML = `<div class="nocard">${escapeHtml(t("noRowsAtAll"))}</div>`;
    $("#cardmeta").innerHTML = "";
    $("#cardbar").hidden = true;
    $("#cardnotes").innerHTML = "";
    return;
  }

  const { row, templates, template, ordinals, ordinal } = card;
  const lit = chosen(a);
  const { front, back } = renderCard(template, row.values, { ordinal });
  const doc = cardDoc({
    front,
    back,
    tab: state.answered ? "both" : "front",
    dark: dark(),
    ring: lit.field,
    flash: state.columnFlash,
  });

  // The new frame starts at the old one's height, so the card does not collapse
  // and regrow on every turn while the new document measures itself.
  const was = $("#card")?.style.height;
  slot.innerHTML = cardFrame(doc, t("cardFrameTitle"));
  const frame = $("#card");
  if (was) frame.style.height = was;
  frame.addEventListener("load", () => wireFrame(frame, typed), { once: true });

  $("#cardmeta").innerHTML = cardMeta(a, row);
  paintCardBar(templates, ordinals, ordinal);
  $("#cardnotes").innerHTML = cardNotes(a, row, front, back);
  syncAddress();
}

/** Above the card: which row of the sheet it is, and where in the deck it lands. */
function cardMeta(a, row) {
  const root = `sc_${state.deckName}`.split("::").length;
  const parts = row.deck.split("::");
  const path = parts.length > root ? parts.slice(root) : parts.slice(-1);
  const fate =
    row.kind === "synced"
      ? ""
      : `<span class="fate ${row.kind}"><span class="dot ${row.kind}" aria-hidden="true"></span>${escapeHtml(
          kindLabel(row.kind),
        )}</span>`;
  return (
    `<span class="rowtag">${escapeHtml(t("valueInRow", row.line))}</span>` +
    `<span class="crumbs" title="${escapeHtml(row.deck)}">${path
      .map((p) => `<span>${escapeHtml(p)}</span>`)
      .join(icon("chevron-right", "sep"))}</span>` +
    fate
  );
}

/** A note with a reverse card, or a cloze with several deletions, has more than
 *  one card; these say which one is showing. */
function paintCardBar(templates, ordinals, ordinal) {
  const bar = $("#cardbar");
  const parts = [];
  if (templates.length > 1) {
    parts.push(
      `<select id="tpl" aria-label="${escapeHtml(t("edTemplate"))}">${templates
        .map(
          (tp, i) =>
            `<option value="${i}" ${i === state.template ? "selected" : ""}>${escapeHtml(tp.name)}</option>`,
        )
        .join("")}</select>`,
    );
  }
  if (ordinals.length > 1) {
    parts.push(
      `<select id="ord" aria-label="${escapeHtml(t("clozeCard"))}">${ordinals
        .map(
          (n) =>
            `<option value="${n}" ${n === ordinal ? "selected" : ""}>${escapeHtml(t("clozeCardN", n))}</option>`,
        )
        .join("")}</select>`,
    );
  }
  bar.hidden = !parts.length;
  bar.innerHTML = parts.join("");
}

/** Under the card: why a row will not sync, what the renderer could not do, and
 *  the deck and tags the note is filed under. */
function cardNotes(a, row, front, back) {
  const unknown = [...new Set([...front.unknownFilters, ...back.unknownFilters])];
  const missing = [...new Set([...front.missingFields, ...back.missingFields])];
  const lit = chosen(a);
  return [
    row.kind !== "synced"
      ? `<p class="note ${row.kind}">${escapeHtml(
          t(row.kind === "invalid" ? "rowInvalid" : "rowSkipped"),
        )}</p>`
      : "",
    row.clozeIn.length && !row.clozeIn.some((h) => a.sides.front.includes(h))
      ? `<p class="note invalid">${t(
          "clozeStranded",
          row.clozeIn.map(escapeHtml).join("</code>, <code>"),
        )}</p>`
      : "",
    missing.length
      ? `<p class="note">${t("missingFields", missing.map(escapeHtml).join("</code>, <code>"))}</p>`
      : "",
    unknown.length
      ? `<p class="note">${t("unknownFilters", unknown.map(escapeHtml).join("</code>, <code>"))}</p>`
      : "",
    row.tags.length
      ? `<p class="tags"><span class="tags-k">${escapeHtml(t("tagsLabel"))}</span>${row.tags
          .map((tag) => `<span class="chip${lit.tags ? " lit" + popping() : ""}">${escapeHtml(tag)}</span>`)
          .join("")}</p>`
      : "",
  ].join("");
}

// What inside a card is a control of its own: a tap there is for it, not a
// request to turn the card over.
const INTERACTIVE =
  "a, button, input, textarea, select, label, audio, video, iframe, details, " +
  "summary, [onclick], [data-tts], .sc-draw, .sc-reveal";

/**
 * Makes the card itself the thing you touch.
 *
 * The card is a same-origin srcdoc frame, so its document can be listened to: a
 * tap anywhere that is not a control turns it over, a sideways drag moves to the
 * next card with the card following the finger, and the keys work while focus is
 * inside it. Enter in a type-in box asks for the answer, as it does in Anki.
 */
function wireFrame(frame, typed) {
  let doc;
  try {
    doc = frame.contentDocument;
  } catch {
    return;
  }
  if (!doc) return;
  doc.body.style.cursor = "pointer";

  if (typed !== null && state.answered) {
    const box = doc.querySelector("#typeans");
    if (box) {
      box.value = typed;
      box.dispatchEvent(new Event("input"));
    }
  }

  let swiped = false;
  doc.addEventListener("click", (e) => {
    if (swiped) {
      swiped = false;
      return;
    }
    if (e.target.closest(INTERACTIVE)) return;
    flip();
  });
  doc.addEventListener("keydown", (e) => {
    const typing = e.target.closest("input, textarea, select, [contenteditable]");
    if (typing) {
      if (e.key === "Enter" && e.target.id === "typeans" && !state.answered) {
        e.preventDefault();
        flip();
      }
      return;
    }
    // Enter or Space on a control in the card presses that control.
    if ((e.key === "Enter" || e.key === " ") && e.target.closest(INTERACTIVE)) return;
    keys(e);
  });

  // Follow the finger, then either throw the card or let it settle back.
  const slot = $("#cardslot");
  let x0 = 0;
  let y0 = 0;
  let dx = 0;
  let dragging = false;
  doc.addEventListener(
    "touchstart",
    (e) => {
      if (e.touches.length !== 1 || e.target.closest(INTERACTIVE)) return;
      x0 = e.touches[0].clientX;
      y0 = e.touches[0].clientY;
      dx = 0;
      dragging = null;
    },
    { passive: true },
  );
  doc.addEventListener(
    "touchmove",
    (e) => {
      if (dragging === false || e.touches.length !== 1) return;
      const mx = e.touches[0].clientX - x0;
      const my = e.touches[0].clientY - y0;
      if (dragging === null) {
        if (Math.abs(mx) < 8 && Math.abs(my) < 8) return;
        dragging = Math.abs(mx) > Math.abs(my) * 1.2;
        if (!dragging) return;
      }
      dx = mx;
      if (!STILL.matches) {
        slot.style.transition = "none";
        slot.style.transform = `translateX(${dx}px) rotate(${dx / 28}deg)`;
      }
    },
    { passive: true },
  );
  doc.addEventListener("touchend", () => {
    if (!dragging) return;
    dragging = false;
    swiped = true;
    setTimeout(() => (swiped = false), 400);
    if (Math.abs(dx) > 64 && visibleRows().length > 1) step(dx < 0 ? 1 : -1);
    else settle(slot);
  });
}

function settle(slot) {
  slot.style.transition = "";
  slot.style.transform = "";
}

let moving = false;
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

/** Turns the card over: question to answer, or back. */
async function flip() {
  if (moving || !state.analysis || !currentCard(state.analysis)) return;
  let typed = null;
  try {
    typed = $("#card")?.contentDocument?.querySelector("#typeans")?.value ?? null;
  } catch {
    // An unreadable frame only loses the typed text, never the turn.
  }
  if (STILL.matches) {
    state.answered = !state.answered;
    return paintCard({ typed });
  }
  moving = true;
  const slot = $("#cardslot");
  slot.classList.add("turn-out");
  await wait(170);
  state.answered = !state.answered;
  paintCard({ typed });
  slot.classList.remove("turn-out");
  slot.classList.add("turn-in");
  void slot.offsetWidth;
  slot.classList.remove("turn-in");
  await wait(200);
  moving = false;
}

/** Moves to the card `by` places along, throwing the current one aside. */
async function step(by) {
  const visible = visibleRows();
  if (!visible.length) return;
  const at = visible.findIndex(({ i }) => i === state.row);
  const target = visible[(at + by + visible.length) % visible.length].i;
  const slot = $("#cardslot");

  if (STILL.matches || moving) {
    if (moving) return settle(slot);
    state.row = target;
    state.answered = false;
    state.template = 0;
    return render();
  }
  moving = true;
  slot.style.transition = "transform .22s cubic-bezier(.4,0,1,1), opacity .22s ease";
  slot.style.transform = `translateX(${by > 0 ? -115 : 115}%) rotate(${by > 0 ? -9 : 9}deg)`;
  slot.style.opacity = "0";
  await wait(200);

  state.row = target;
  state.answered = false;
  state.template = 0;
  // Up from the stack underneath: the next card was already there.
  slot.style.transition = "none";
  slot.style.transform = "translateY(14px) scale(.95)";
  slot.style.opacity = ".3";
  render();
  void slot.offsetWidth;
  slot.style.transition = "";
  slot.style.transform = "";
  slot.style.opacity = "";
  await wait(260);
  moving = false;
}

function keys(e) {
  if (state.stage !== "review" || document.querySelector("dialog[open]:modal")) return;
  if (e.key === "ArrowRight") {
    e.preventDefault();
    step(1);
  } else if (e.key === "ArrowLeft") {
    e.preventDefault();
    step(-1);
  } else if (e.key === " " || e.key === "Enter") {
    e.preventDefault();
    flip();
  }
}

// ---------------------------------------------------------------------------
// Download, and what to do with the file
// ---------------------------------------------------------------------------

const fileName = () => `${state.deckName || "deck"}.apkg`.replace(/[\\/:*?"<>|]+/g, " ");

/** Hands the built package to the browser as a download. */
function downloadPackage() {
  const button = $("#apkg");
  button.disabled = true;
  status(t("packing"), "", true);
  try {
    // What Anki has now, as far as this browser knows: the last package of the
    // deck. Its fields go in front of this one's (apkg.kept_fields), and the
    // change between the two is what the done dialog warns about.
    const last = lastShape(state.sheetId);
    state.change = shapeChange(last, state.shape);
    state.dropped = droppedTemplates(last, state.shape);
    // A copy, because the array Pyodide hands over is a view onto its heap and
    // the next Python call is free to reuse that memory.
    const bytes = new Uint8Array(buildPackage(last));
    if (state.shape) keepShape(state.sheetId, { ...state.shape, deck: state.deckName });
    const url = URL.createObjectURL(
      new Blob([bytes], { type: "application/octet-stream" }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = fileName();
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    status(t("packed", Math.round(bytes.length / 1024)), "ok");
    state.downloaded = true;
    paintRail();
    openDone();
  } catch (err) {
    // The sentence, never the traceback above it.
    status(t("packFailed", pythonMessage(err)), "bad");
  } finally {
    button.disabled = false;
  }
}

/** The steps for opening the file, on whichever device is picked. */
function paintDone() {
  const name = fileName();
  $("#done-name").textContent = name;
  $("#devtabs").innerHTML = DEVICES.map((d) => {
    const [label, sub] = DEVICE_LABELS[d];
    const on = d === state.device;
    return `<button type="button" role="tab" id="dev-${d}" data-device="${d}"
      aria-selected="${on}" aria-controls="devpanel" tabindex="${on ? 0 : -1}">
      ${icon(d === "desktop" ? "monitor" : "smartphone")}
      <span><strong translate="no">${escapeHtml(t(label))}</strong><small>${escapeHtml(t(sub))}</small></span>
    </button>`;
  }).join("");
  $("#devpanel").setAttribute("aria-labelledby", `dev-${state.device}`);
  $("#devpanel").innerHTML = `<ol class="inst">${DEVICE_STEPS[state.device]
    .map((key) => `<li>${t(key, escapeHtml(name))}</li>`)
    .join("")}</ol>`;
  paintSchema($("#done-schema"), state.device);
}

function openDone() {
  paintDone();
  const dlg = $("#done");
  if (!dlg.open) dlg.showModal();
  $(`#dev-${state.device}`)?.focus();
}

// ---------------------------------------------------------------------------
// Painting
// ---------------------------------------------------------------------------

/**
 * Light unless somebody said otherwise.
 *
 * Not `prefers-color-scheme`: a page that opens dark because the laptop is set
 * dark looks broken to a reader who did not ask for it, and this one is mostly
 * read on a phone in daylight. The choice is explicit and remembered.
 */
function dark() {
  return document.documentElement.dataset.theme === "dark";
}

function setTheme(on) {
  if (on) document.documentElement.dataset.theme = "dark";
  else delete document.documentElement.dataset.theme;
  try {
    localStorage.setItem("sc-theme", on ? "dark" : "light");
  } catch {
    // A browser refusing storage is not a reason to refuse the theme.
  }
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute("content", on ? "#18151f" : "#ffffff");
  paintTheme();
  // The card is a separate document that was handed the old palette.
  if (state.analysis && state.stage === "review") paintCard();
}

function paintTheme() {
  const button = $("#theme");
  // What pressing it gives you: a sun on the dark page, a moon on the light one.
  button.innerHTML = icon(dark() ? "sun" : "moon");
  button.title = button.ariaLabel = t(dark() ? "toLight" : "toDark");
}

/** Text that lives in create.html rather than in a render function. */
function paintStatic() {
  // A screen reader picks its voice from this, so it has to follow the page's
  // language, not just the button that last changed it.
  document.documentElement.lang = lang();
  paintStrings();
  $("#rows-legend").innerHTML =
    `<span><span class="dot synced"></span> ${escapeHtml(t("legendSynced"))}</span>` +
    `<span><span class="dot skipped"></span> ${escapeHtml(t("legendSkipped"))}</span>` +
    `<span><span class="dot invalid"></span> ${escapeHtml(t("legendInvalid"))}</span>` +
    `<span class="ghost">${escapeHtml(t("legendGhost"))}</span>`;

  paintTheme();
  // The glyph says "language" to somebody who reads neither EN nor VI as a word.
  $("#langs").innerHTML = `<span class="langs-icon">${icon("languages")}</span>` + LANGUAGES.map(
    (l) =>
      `<button data-lang="${l.code}" class="${lang() === l.code ? "on" : ""}"` +
      ` aria-pressed="${lang() === l.code}">${l.label}</button>`,
  ).join("");
  paintTitle();
  paintRail();
}

function render() {
  const a = state.analysis;
  paintStatic();
  $("#summary").innerHTML = summaryLine(a);
  $("#tree").innerHTML = deckPanel(a);
  $("#rowlist").innerHTML = rowList();
  $("#rowcount").textContent = `${visibleRows().length}`;
  paintCard();
  paintSheetView(a);

  // The flash and the scroll both mark *choosing a column*. Every other repaint
  // — a row picked, a language switched — would otherwise blink a block nobody
  // was looking at, and move the page under a reader who asked for nothing.
  if (state.columnFlash) revealField(chosen(a).field);
  state.columnFlash = false;

  const cards = cardCount(a);
  const decks = deckCount(a);
  $("#dl-count").textContent = cards ? t("dlCards", cards) : t("noSyncRows");
  $("#dl-decks").textContent = cards ? t("dlDecks", decks) : "";
  $("#apkg").disabled = !cards;

  // Above the card rather than behind a menu: a sheet that warns is telling you
  // some cards will come out wrong. Folded to its count, so it is seen without
  // being read before the card.
  const warnings = warningItems(a);
  $("#warnbar").hidden = !warnings.length;
  $("#warntitle").textContent = t("warnTitle", warnings.length);
  $("#warnlist").innerHTML = warnings.join("");

  paintSchema($("#schemanote"));
  if ($("#done").open) paintDone();
}

// Which app's merge step goes with which device tab.
const MERGE_STEP = { desktop: "mergeDesktop", android: "mergeAndroid", ios: "mergeIos" };

/**
 * The notice for a note type that changed since this deck's last download, or
 * nothing. `device` narrows the steps to one app (the done dialog has tabs for
 * the device); without it all three are listed.
 */
function paintSchema(el, device = null) {
  const change = state.change;
  const shown = change || state.dropped?.length;
  el.hidden = !shown;
  if (!shown) return (el.innerHTML = "");
  const apps = device ? [device] : ["android", "ios", "desktop"];
  if (change === "cloze") {
    const type = state.analysis?.noteTypes?.[state.shape?.kind === "cloze" ? "cloze" : "basic"] ?? "";
    el.innerHTML = `<strong>${escapeHtml(t("clozeTitle"))}</strong><p>${t("clozeBody", escapeHtml(type))}</p>`;
    return;
  }
  const empty = state.dropped?.length ? `<p>${t("emptyCards")}</p>` : "";
  if (!change) {
    // Only a template taken out: the note type is the same to Anki (it is kept
    // as a stub), so there is nothing to merge — just cards to empty.
    el.innerHTML = `<strong>${escapeHtml(t("emptyCardsTitle"))}</strong>${empty}`;
    return;
  }
  const fields = escapeHtml((state.shape?.fields || []).join(", "));
  el.innerHTML =
    `<strong>${escapeHtml(t("schemaTitle"))}</strong><p>${t("schemaBody", fields)}</p>` +
    `<ul>${apps.map((d) => `<li>${t(MERGE_STEP[d])}</li>`).join("")}</ul>` +
    empty +
    `<p class="muted small">${escapeHtml(t("mergeAfter"))}</p>`;
}

// ---------------------------------------------------------------------------
// The deck panel's two shapes
// ---------------------------------------------------------------------------

/**
 * Beside the card when there is room, a bottom sheet when there is not.
 *
 * One `<dialog>`, shown non-modally as a side panel on a wide screen and modally
 * on a phone, where it slides up over the card, traps focus and closes on Escape
 * — so the tree and the rows exist once, and a phone gets them as the secondary
 * thing they are rather than as a screenful above the card.
 */
function placeDeckPanel() {
  const dlg = $("#deckpanel");
  const want = WIDE.matches && state.stage === "review";
  if (want) {
    if (dlg.open && dlg.matches(":modal")) dlg.close();
    if (!dlg.open) dlg.show();
  } else if (dlg.open && !dlg.matches(":modal")) {
    dlg.close();
  }
}
WIDE.addEventListener("change", placeDeckPanel);

/** Beside the card on a very wide screen, behind its toggle everywhere else. */
function placeSheetView() {
  const view = $("#sheetview");
  const beside = XWIDE.matches && state.stage === "review";
  $("#open-sheet").hidden = beside;
  if (beside) {
    view.hidden = false;
    if (state.analysis) paintSheetView(state.analysis);
  } else if (view.dataset.beside) {
    view.hidden = $("#open-sheet").getAttribute("aria-expanded") !== "true";
  }
  view.dataset.beside = beside ? "1" : "";
}
XWIDE.addEventListener("change", placeSheetView);

function openDeckPanel() {
  const dlg = $("#deckpanel");
  if (WIDE.matches) {
    dlg.querySelector(".tree button.on, .rowitem.on")?.focus();
    return;
  }
  if (!dlg.open) dlg.showModal();
  dlg.querySelector(".rowitem.on")?.scrollIntoView({ block: "center" });
}

function closeDeckPanel() {
  const dlg = $("#deckpanel");
  if (dlg.matches(":modal")) dlg.close();
}

// ---------------------------------------------------------------------------
// The Sheet view — the sheet as a sheet, the row cell by cell, the template
// ---------------------------------------------------------------------------

function paintSheetView(a) {
  paintSheetViewBody(a);
  syncAddress();
}

function paintSheetViewBody(a) {
  for (const b of document.querySelectorAll("[data-view]")) {
    b.setAttribute("aria-pressed", String(b.dataset.view === state.view));
  }
  $("#gridview").hidden = state.view !== "grid";
  $("#tplview").hidden = state.view !== "template";
  if ($("#sheetview").hidden) return;
  if (state.view === "template") {
    $("#tplview").innerHTML = templateView(a);
    return;
  }
  paintGrid(a);
  const shown = a.rows[state.row];
  $("#cells").hidden = !shown;
  if (shown) {
    $("#cellhead").textContent = t("valueInRow", shown.line);
    $("#colcount").textContent = `${a.plan.headers.length}`;
    $("#celllist").innerHTML = rowCells(a);
  }
}

function templateView(a) {
  const card = currentCard(a);
  if (!card) return "";
  const { row, template } = card;
  return `<p class="muted small">${t(
      "templateFrom",
      escapeHtml(row.cloze ? a.noteTypes.cloze : a.noteTypes.basic),
    )}</p>
    <h3 class="src-head">${escapeHtml(t("frontTemplate"))}</h3>
    <pre class="source">${escapeHtml(template.qfmt)}</pre>
    <h3 class="src-head">${escapeHtml(t("backTemplate"))}</h3>
    <pre class="source">${escapeHtml(template.afmt)}</pre>`;
}

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
 * Draws the grid, leaving it where the reader left it.
 *
 * Every repaint rebuilds the table, and a table rebuilt inside a scrolled box
 * starts at the top — so picking row 90 would send the grid back to row 1, which
 * is the reader's place being taken away for choosing something. The offsets are
 * put back on the same frame, before the browser paints.
 */
function paintGrid(a) {
  const box = $("#grid");
  const { scrollTop, scrollLeft } = box;
  const shown = Math.max(0, (a.grid?.cells.length ?? 0) - 1);

  $("#gridbox").hidden = !shown;
  $("#gridcount").textContent = `${shown}`;
  box.innerHTML = sheetGrid(a);
  box.scrollTop = scrollTop;
  box.scrollLeft = scrollLeft;

  // A grid that stops partway through is saying something about the sheet, so it
  // says it rather than simply ending.
  const cut = a.grid && a.grid.total > shown;
  $("#gridcut").hidden = !cut;
  if (cut) $("#gridcut").textContent = t("gridCut", shown, a.grid.total);
}

/** A spreadsheet's name for a column at this position: A, B, … Z, AA, AB. */
function columnLetter(index) {
  let n = index;
  let out = "";
  do {
    out = String.fromCharCode(65 + (n % 26)) + out;
    n = Math.floor(n / 26) - 1;
  } while (n >= 0);
  return out;
}

/**
 * The sheet as a grid — the same rows and columns the spreadsheet shows.
 *
 * It answers "is this the sheet I meant", which only the sheet's own shape
 * answers: the settings row sitting in row 2, the empty column somebody left in
 * the middle, the thirty rows below the ones you meant. Everything is here —
 * blank rows, the settings row, columns with no header — because a preview that
 * quietly tidied would be a different sheet. What it adds is what the parser
 * knows: which rows sync, which one is the settings row, and which column a
 * click opens.
 */
function sheetGrid(a) {
  const g = a.grid;
  if (!g || !g.cells.length) return "";

  // Row numbers are the sheet's own, so a row here and a row anywhere else on
  // the page are named the same thing.
  const found = new Map(a.rows.map((row, i) => [row.line, i]));
  const selected = a.rows[state.row]?.line;

  const letters = g.cells[0]
    .map((_, j) => {
      const col = g.cols[j];
      const on = col !== null && col === state.column ? " on" : "";
      return `<th class="colh${on}"${col === null ? "" : ` data-col="${col}"`}
        >${columnLetter(j)}</th>`;
    })
    .join("");

  const body = g.cells
    .map((cells, r) => {
      const line = r + 1;
      const at = found.get(line);
      const kind = at === undefined ? "" : a.rows[at].kind;
      const cls = [
        r === 0 ? "hdr" : "",
        line === g.config ? "cfg" : "",
        kind && `k-${kind}`,
        line === selected ? "on" : "",
      ]
        .filter(Boolean)
        .join(" ");
      const cellsHtml = cells
        .map((value, j) => {
          // Only row 1 opens a column: everywhere else a click picks the row,
          // which is the thing under the pointer.
          const pick = r === 0 && g.cols[j] !== null ? ` data-col="${g.cols[j]}"` : "";
          // A cell is cut to keep the row one row high, so the whole of it is on
          // the cell itself — nothing in the sheet becomes unreachable here.
          const full = value ? ` title="${escapeHtml(value)}"` : "";
          return `<td${pick}${full}>${escapeHtml(value)}</td>`;
        })
        .join("");
      const row = at === undefined ? "" : ` data-row="${at}"`;
      return `<tr class="${cls}"${row}>
        <th class="rowh" scope="row"${
          kind ? ` title="${escapeHtml(kindLabel(kind))}"` : ""
        }>${kind ? `<span class="dot ${kind}" aria-hidden="true"></span>` : ""}${line}</th>${cellsHtml}</tr>`;
    })
    .join("");

  return `<table class="sheetgrid">
    <thead><tr><th class="corner"></th>${letters}</tr></thead>
    <tbody>${body}</tbody></table>`;
}

/**
 * The chosen row, one line per column of the sheet.
 *
 * The grid above answers "is this the sheet I meant"; this answers "what is in
 * this row", which on a phone is the question a grid answers badly — fourteen
 * columns is a sideways scroll inside a downwards one. So it stays a list at
 * every width, and each line doubles as the way to open that column.
 */
function rowCells(a) {
  const row = a.rows[state.row];
  if (!row) return "";

  return a.plan.headers
    .map((name, i) => {
      // A header written twice is one column. The later one has no cell of its
      // own, and saying which of the two was honoured is why both are listed.
      const repeat = a.plan.headers.indexOf(name) !== i;
      const value = repeat ? "" : String(row.values[name] ?? "").trim();
      const line = `<button class="cellrow${repeat ? " dead" : ""}${
        state.column === i ? " on" : ""
      }" data-col="${i}" aria-expanded="${state.column === i}">
        <span class="k">${escapeHtml(name)}</span>
        <span class="v${value ? "" : " none"}">${escapeHtml(
          value || t(repeat ? "roleDuplicate" : "cellEmpty"),
        )}</span>
      </button>`;
      // The answer opens under the question rather than at the foot of the
      // block: on a phone the two would otherwise be a screen apart.
      return state.column === i ? line + columnDetail(a) : line;
    })
    .join("");
}

/** True only while drawing the repaint that a column was just chosen on. */
function popping() {
  return state.columnFlash ? " pop" : "";
}

/**
 * What the chosen column, if any, points at elsewhere on the page.
 *
 * Answering "what did this column become" in words and leaving the reader to go
 * find it is half an answer. Everything below returns something the rest of the
 * page can light up at the same moment — the block on the card, the branch of
 * the deck tree, the count — so the word and the thing arrive together.
 *
 * @returns {{name: string|null, field: string|null, deck: string|null,
 *            tags: boolean, stat: string|null}}
 */
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
 * Sliced off the deck name the add-on itself produced rather than rebuilt from
 * the cells: a level is cleaned on its way into a deck name — `::` and a few
 * other characters cannot survive there — so the cell and the segment are not
 * always the same text. Only the *count* of levels is taken from the cells, since
 * an empty level is dropped from the path.
 */
function branchFor(name, levels, a) {
  const row = a.rows[state.row];
  if (!row) return null;

  const root = `sc_${state.deckName}`.split("::").length;
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
 * Brings the ringed block into view, for a card taller than its frame's slot.
 *
 * Only ever called from the click that opened a column: scrolling is a strong
 * thing to do to somebody, and doing it on every repaint would move the page
 * under a reader who asked for nothing.
 */
function revealField(name) {
  const frame = $("#card");
  if (!frame || !name) return;
  const go = () => {
    try {
      const el = frame.contentDocument?.querySelector(
        `[data-sc-col="${name.replace(/["\\]/g, "\\$&")}"]`,
      );
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

/**
 * The chosen column, opened up: what it became, what the settings row said, what
 * this row actually holds in it, and anything the add-on could not understand.
 */
function columnDetail(a) {
  const name = a.plan.headers[state.column];
  if (name === undefined) return "";

  const role = columnRole(name, state.column, a);
  const set = directives(name, a);
  // The warnings name their column in single quotes, which is also how a person
  // reading them finds the one they are looking at.
  const said = (a.config.warningCodes || [])
    .filter((w) => w.text.startsWith(`'${name}':`) || w.params?.col === name)
    .map((w) => warningText(w, lang()));

  return `<div class="coldetail${state.columnFlash ? " flash" : ""}">
    <p class="colrole"><span class="mark ${role.kind}"></span>${escapeHtml(role.label)}</p>
    ${
      set.length
        ? `<p class="colset">${set
            .map((d) => `<span class="chip">${escapeHtml(d)}</span>`)
            .join("")}</p>`
        : `<p class="muted small">${escapeHtml(t("nothingSet"))}</p>`
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
  if (e.target.closest("#theme")) return setTheme(!dark());
  const picker = e.target.closest("[data-lang]");
  if (!picker) return;
  setLang(picker.dataset.lang);
  // Everything on screen is produced by a render function, so switching
  // languages is a repaint rather than a reload — the sheet stays loaded.
  if (state.analysis && state.stage === "review") render();
  else {
    paintStatic();
    bootStatus();
  }
});

// A real form, so Enter submits and the browser supplies the keyboard's "go"
// key on a phone.
$("#entry-form").addEventListener("submit", (e) => {
  e.preventDefault();
  fromPage = true;
  wanted = null;
  submit();
});

// A changed link is a new question; the old complaint is about the last one.
$("#url").addEventListener("input", () => fieldError(""));

// Pasting is what everybody arriving here does next, and on a phone a long-press
// in an empty field is a fiddly way to do it. Only offered where the browser can
// read the clipboard at all; a refusal leaves the cursor in the field.
if (navigator.clipboard?.readText) {
  $("#paste").hidden = false;
  $("#paste").addEventListener("click", async () => {
    try {
      const text = (await navigator.clipboard.readText()).trim();
      if (text) {
        $("#url").value = text;
        fieldError("");
      }
    } catch {
      // Permission refused: the field is still there to paste into by hand.
    }
    $("#url").focus();
  });
}

$("#example").addEventListener("click", () => {
  $("#url").value = DEMO_SHEET;
  fieldError("");
  fromPage = true;
  wanted = null;
  submit();
});

$("#reload").addEventListener("click", reload);
$("#sharecard").addEventListener("click", shareCard);
$("#change").addEventListener("click", changeSource);
// The rail's first step, once done, is the same way back: it is where a learner
// looks for "start again with another sheet".
$("#rail-back").addEventListener("click", changeSource);

function changeSource() {
  // The form is the screen before this one when the deck was loaded from it, so
  // this is Back; otherwise the form becomes a screen of its own, and Back from
  // it returns to the deck.
  if (history.state?.deck === "pushed") {
    history.back();
    showForm();
    return;
  }
  history.pushState(null, "", location.pathname);
  showForm();
}

$("#open-deck").addEventListener("click", openDeckPanel);
$("#dp-close").addEventListener("click", closeDeckPanel);
// A tap on the dimmed card behind the sheet puts the sheet away.
$("#deckpanel").addEventListener("click", (e) => {
  if (e.target === e.currentTarget && e.currentTarget.matches(":modal")) closeDeckPanel();
});

$("#open-sheet").addEventListener("click", () => {
  const view = $("#sheetview");
  view.hidden = !view.hidden;
  $("#open-sheet").setAttribute("aria-expanded", String(!view.hidden));
  view.dataset.beside = "";
  if (!view.hidden) {
    paintSheetView(state.analysis);
    view.scrollIntoView({ block: "start", behavior: STILL.matches ? "auto" : "smooth" });
  } else syncAddress();
});

$("#flip").addEventListener("click", flip);
$("#apkg").addEventListener("click", downloadPackage);
$("#again").addEventListener("click", downloadPackage);
for (const id of ["#done-close", "#done-ok"]) {
  $(id).addEventListener("click", () => $("#done").close());
}
$("#done").addEventListener("click", (e) => {
  if (e.target === e.currentTarget) $("#done").close();
});
$("#devtabs").addEventListener("click", (e) => {
  const tab = e.target.closest("[data-device]");
  if (!tab) return;
  state.device = tab.dataset.device;
  paintDone();
  $(`#dev-${state.device}`).focus();
});
// The tab pattern: arrows move between devices, one tab stop for the group.
$("#devtabs").addEventListener("keydown", (e) => {
  const move = { ArrowRight: 1, ArrowLeft: -1 }[e.key];
  if (!move) return;
  e.preventDefault();
  const at = DEVICES.indexOf(state.device);
  state.device = DEVICES[(at + move + DEVICES.length) % DEVICES.length];
  paintDone();
  $(`#dev-${state.device}`).focus();
});

$("#pick").addEventListener("click", () => $("#file").click());
$("#file").addEventListener("change", (e) => {
  const file = e.target.files[0];
  // Cleared so that choosing the same file twice fires a change event again —
  // the obvious thing to do after editing it and wanting the new version.
  e.target.value = "";
  if (file) openFile(file);
});

document.addEventListener("keydown", (e) => {
  if (e.target.closest?.("input, textarea, select, [contenteditable]")) return;
  // Enter and Space on a button press the button; only the bare page turns the
  // card with them.
  if ((e.key === " " || e.key === "Enter") && e.target.closest?.("button, a, summary, [tabindex]:not(#app)")) return;
  keys(e);
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
  if (file && !$("#pick").disabled) openFile(file);
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
  const view = e.target.closest("[data-view]");
  if (view) {
    state.view = view.dataset.view;
    return paintSheetView(state.analysis);
  }
  const deckEl = e.target.closest("[data-deck]");
  if (deckEl) {
    state.deckFilter = deckEl.dataset.deck || null;
    const first = visibleRows()[0];
    if (first) state.row = first.i;
    state.answered = false;
    return render();
  }
  const rowEl = e.target.closest("[data-row]");
  if (rowEl) {
    // Asked before render(), which replaces the list and leaves rowEl detached.
    const inPanel = Boolean(rowEl.closest("#deckpanel"));
    state.row = Number(rowEl.dataset.row);
    state.template = 0;
    state.answered = false;
    render();
    // Picking a row is the moment you stop browsing and start reading: the
    // sheet goes away and the card comes to you.
    if (inPanel && !WIDE.matches) {
      closeDeckPanel();
      $("#stage").scrollIntoView({ block: "start" });
    }
    return;
  }
  const stepper = e.target.closest("[data-step]");
  if (stepper && stepper.closest(".reviewbar")) step(Number(stepper.dataset.step));
});

document.addEventListener("change", (e) => {
  if (e.target.id === "tabpick") return showUpload(Number(e.target.value));
  if (e.target.id === "tpl") state.template = Number(e.target.value);
  else if (e.target.id === "ord") state.ordinal = Number(e.target.value);
  else return;
  state.answered = false;
  render();
});

addEventListener("message", (e) => {
  const frame = $("#card");
  if (!frame || e.source !== frame.contentWindow || !e.data?.h) return;
  frame.style.height = `${e.data.h}px`;
});

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------

paintIcons();
paintStatic();
mountInAppBanner({ t, icon });

// What the address asked for: a link (?url=, which the landing page and old
// preview links forward here), the example (#example), or nothing — the form.
setStage("empty");
if (loadFromAddress()) {
  // On its way; the queue in whenReady() runs it once Python is up.
} else if (location.hash === "#file") {
  // A file picked on the landing page, or a sheet written in Create sheet,
  // handed over through IndexedDB. #file stays in the address and the file in
  // the slot until something else is opened, so a reload brings the deck back.
  setStage("loading");
  takeHandoff().then(({ file, from }) => {
    if (file) {
      const edit = from === "sheet" ? site("sheet/") : "";
      whenReady(() => previewFile(file, { hash: "#file", edit }), "file");
    } else {
      history.replaceState(null, "", location.pathname);
      setStage("empty");
      bootStatus();
    }
  });
} else if (isShare(location.hash)) {
  // A sheet shared from Create sheet, carried whole in the fragment
  // (sharelink.js). It stays in the address, so a reload opens it again, and
  // "edit" takes the same sheet back to Create sheet.
  const hash = location.hash;
  setStage("loading");
  decodeShare(hash).then(
    ({ name, tsv }) => {
      const file = new File([tsv], `${(name || "Sheet").replace(/[\\/:*?"<>|]+/g, " ").trim() || "Sheet"}.tsv`, {
        type: "text/tab-separated-values",
      });
      whenReady(() => previewFile(file, { hash, edit: site(`sheet/${hash}`) }), "file");
    },
    (err) => failed(t(err.code === "version" ? "shareTooNew" : "shareBroken")),
  );
} else bootStatus();

boot()
  .then(() => {
    bootStatus();
    if (pending) pending();
  })
  .catch((err) => {
    booting.failed = true;
    if (state.stage === "loading") setStage("empty");
    status(t("bootFailed", err.message), "bad");
  });
