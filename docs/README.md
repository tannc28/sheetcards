# Sheets2Anki — Developer Guide

Long-form technical guide for contributors. It explains how the add-on is laid out,
how a sync flows end to end, and how to set up, test, build, and debug it.

- For the **concise architecture reference and conventions**, see [`CLAUDE.md`](../CLAUDE.md).
- For **setup and the contribution workflow**, see [`CONTRIBUTING.md`](../CONTRIBUTING.md).
- For the **end-user manual**, see the root [`README.md`](../README.md).

> **Requirements:** Anki **25.x or newer** (Qt6, PyQt6), Python **3.13**. There is no
> Qt5 fallback and no support for older Anki versions — this is v3.0.0+.

## Table of contents

- [What this is](#what-this-is)
- [System architecture](#system-architecture)
- [Project structure](#project-structure)
- [Module map](#module-map)
- [Sync data flow](#sync-data-flow)
- [Column model & note keying](#column-model--note-keying)
- [Card-side features & the AI layer](#card-side-features--the-ai-layer)
- [Configuration: config.json vs meta.json](#configuration-configjson-vs-metajson)
- [Development setup](#development-setup)
- [Testing](#testing)
- [Building & packaging](#building--packaging)
- [Debugging](#debugging)
- [Conventions](#conventions)

## What this is

Sheets2Anki is an **Anki add-on**, not a standalone application. The repository root
*is* the add-on directory: Anki loads `__init__.py` from the root, which registers a
`Tools → Sheets2Anki` menu, binds keyboard shortcuts, and wires the card webview hooks.
There is no server and no `main()` — all code runs inside Anki's Python/Qt6 process.

The architecture is **function-oriented**, organized around a handful of cohesive
modules plus a few small types (`RemoteDeck`, `DebugManager`). It is *not* a class-based
MVC framework; sync is driven by module-level functions such as `syncDecks()` and
`create_or_update_notes()`.

## System architecture

Three layers, from the outside in:

```
┌──────────────────────────────────────────────────────────────────────┐
│  Anki integration  (__init__.py)                                       │
│  • Tools → Sheets2Anki menu     • 12 keyboard shortcuts (Ctrl+Shift+…) │
│  • webview_did_receive_js_message hook (AI button pycmd messages)      │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────┐
│  Add-on logic  (src/)                                                   │
│  • sync engine / data processing  • config & student management        │
│  • dialogs (src/ui/)              • AI, backup, AnkiWeb, images         │
│  • compat.py — the single Qt/Anki gateway                              │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────┐
│  Vendored libraries  (libs/)  — added to sys.path at runtime           │
│  • beautifulsoup4 (+ soupsieve)  • chardet  • org_to_anki              │
└──────────────────────────────────────────────────────────────────────┘
```

**`src/compat.py` is the Qt/Anki gateway.** All Qt and Anki UI imports must go through
`compat.py` (which re-exports widgets and defines Qt6 enum constants), never directly
from `aqt`/`aqt.qt`. When you need a new Qt symbol, add it to `compat.py`.

**Dual-context imports.** `src/` modules are imported two ways: as a package inside Anki
(relative imports) and by the test suite (which registers `src` as a package). Most
modules therefore use the pattern:

```python
try:
    from .compat import mw
except ImportError:
    from compat import mw
```

Preserve this pattern when editing `src/`.

## Project structure

```
sheets2anki/
├── __init__.py                 # Anki entry point: menu, shortcuts, webview hooks
├── config.json                 # Default settings (committed)
├── manifest.json               # Add-on metadata (version lives here + pyproject.toml)
├── meta.json                   # User settings + connected decks (gitignored; runtime)
├── src/                        # All add-on logic (see module map below)
│   └── ui/                     # Qt dialogs (12 modules)
├── libs/                       # Vendored third-party deps — never edit or lint
├── tests/                      # pytest suite (Anki is mocked; no Anki install needed)
├── scripts/                    # Build/packaging tooling for .ankiaddon files
├── tools/js-harnesses/         # Manual JS/HTML harnesses for card-template work
└── docs/                       # This guide, the changelog, and the AnkiWeb listing
```

### Facade-split modules

Several large modules were decomposed but keep a **back-compat facade** (the original
module re-exports the moved names), so `from .<module> import X` — including lazy
imports — keeps working. When grepping for a definition, the real code may live in the
split-out module:

| Original (facade) | Split-out module(s) |
| :--- | :--- |
| `utils.py` | `errors.py`, `debug.py` (`DebugManager`, `add_debug_message`), `deck_options.py` |
| `sync.py` | `sync_report.py` (sync-summary HTML) |
| `config_manager.py` | `ai_prompts.py` (AI prompt dictionaries) |
| `templates_and_definitions.py` | `card_assets.py` (card CSS/HTML/JS strings) |

## Module map

### Sync & data
- **`sync.py`** — orchestrates a sync run (`syncDecks()`): iterates the selected decks,
  delegates per-deck work, aggregates stats, and renders the summary
  (HTML in **`sync_report.py`**).
- **`data_processor.py`** — downloads and parses the spreadsheet
  (`getRemoteDeck()`, `parse_tsv_data()`, `build_remote_deck_from_tsv()` → a
  `RemoteDeck`) and applies changes to the collection
  (`create_or_update_notes()`); detects Cloze cards (`has_cloze_deletion()`).
- **`deck_manager.py`** — deck CRUD and the selection entry point
  (`syncDecksWithSelection()`).
- **`student_manager.py`** — multi-student logic: per-student subdecks, filtering,
  and the composite note key.
- **`name_consistency_manager.py`** — keeps dynamically-created note-type names in sync
  when a deck is renamed.

### Configuration & utilities
- **`config_manager.py`** — the only module that reads/writes `meta.json`/`config.json`
  (`get_meta()` / `save_meta()`); AI prompt defaults live in **`ai_prompts.py`**.
- **`utils.py`** — URL conversion (`convert_edit_url_to_tsv()`,
  `get_spreadsheet_id_from_url()`), note-type naming (`get_note_type_name()`), and other
  helpers; errors/debug/deck-options were split into **`errors.py`**, **`debug.py`**,
  **`deck_options.py`**.
- **`templates_and_definitions.py`** — column definitions (`ALL_AVAILABLE_COLUMNS`,
  `REQUIRED_HEADERS`), note-type/model construction (`create_model()`), and the card
  template assembly; the large CSS/HTML/JS strings live in **`card_assets.py`**.

### Features & integrations
- **`ai_service.py`** — desktop AI calls (`call_ai_api_async()`) to Gemini / Claude /
  OpenAI.
- **`ankiweb_sync.py`** — optional AnkiWeb auto-sync after changes.
- **`backup_system.py`** — configuration/deck backup & restore.
- **`image_processor.py`** + **`image_processor_script.py`** — the in-Anki image
  workflow (a Google Apps Script Web App; see
  [`scripts/IMAGE_PROCESSOR_README.md`](../scripts/IMAGE_PROCESSOR_README.md)).
- **`compat.py`**, **`styled_messages.py`** — the Qt/Anki gateway and styled dialogs.

### UI (`src/ui/`)
Twelve Qt dialogs (add deck, sync, disconnect, backup, debug, global-student config,
deck-options config, AnkiWeb config, AI-assistance config, image-processor config,
timer config, data-removal confirmation). Modules in `src/ui/` import siblings one level
up (`from ..compat import …`).

## Sync data flow

`deck_manager.syncDecksWithSelection()` → `sync.syncDecks()` orchestrates everything.
Per deck:

1. **URL → TSV.** A Google Sheets **edit URL** is converted to a TSV export URL
   (`.../export?format=tsv`) — `utils.convert_edit_url_to_tsv()` /
   `get_spreadsheet_id_from_url()`. Downloads are restricted to Google hosts.
2. **Download & parse.** `data_processor.getRemoteDeck()` downloads the TSV, runs
   `parse_tsv_data()` and `build_remote_deck_from_tsv()`, and returns a `RemoteDeck`
   (which tracks `valid_note_lines`, `invalid_note_lines`, etc.).
3. **Apply changes.** `data_processor.create_or_update_notes()` creates, updates, and
   deletes Anki notes to match the sheet.

> **Safety guard:** if a parsed sheet has `valid_note_lines == 0` (e.g. an empty or
> failed fetch), the deletion pass is skipped so a transient blank download can't wipe
> a deck.

## Column model & note keying

- **Columns** are centralized in `templates_and_definitions.py`:
  **25 available columns** (`ALL_AVAILABLE_COLUMNS`), of which **3 are required
  headers** (`REQUIRED_HEADERS = ID, QUESTION, ANSWER`). `ID` is the stable per-row key
  — never regenerate it.
- **Multi-student.** The `STUDENTS` column duplicates a row into per-student subdecks.
  Notes are matched/tracked by a composite **`{student}_{note_id}`** key. The
  `[MISSING_STUDENT]` and other `[MISSING_*]` sentinels are real values handled
  specially (matching is suffix-aware so an underscore in a student name can't corrupt
  the key).
- **Note types (models)** are created dynamically, one set per
  `Sheets2Anki - {deck} - {student} - Basic|Cloze|Reverse`
  (`utils.get_note_type_name()`, `templates_and_definitions.create_model()`).
  `name_consistency_manager.py` keeps these names aligned when a deck is renamed.
- **Cloze** cards are auto-detected from `{{c1::…}}` patterns
  (`data_processor.has_cloze_deletion()`).
- **Deck hierarchy:**
  `Sheets2Anki::{deck}::{student}::{importance}::{topic}::{subtopic}::{concept}`.
- **Tags:** hierarchical `sheets2anki::…` derived from the categorization columns.

## Card-side features & the AI layer

`templates_and_definitions.py` / `card_assets.py` hold the CSS/JS rendered into card
HTML: the study **timer** and the **AI Help / AI Ask / AI Checker** buttons. The AI
layer has two execution paths that must stay in sync:

- **Desktop:** card JS calls `pycmd(...)` → handled in `__init__.py`
  (`sheets2anki_ai_help/ask/checker:` messages) → `ai_service.call_ai_api_async()`.
- **Mobile / Web (AnkiMobile, AnkiWeb):** `pycmd` is unavailable, so the JS calls the
  provider API directly using config embedded into the template
  (`AI_HELP_JS_MOBILE_TEMPLATE`, with base64-encoded prompts).

The two JS blocks (`AI_HELP_JS_DESKTOP`, `AI_HELP_JS_MOBILE_TEMPLATE`) share their
identical parts via single-source `_AI_JS_*` constants; only genuinely-divergent
functions are duplicated.

> **Card-JS changes are render-sensitive.** Verify any template edit by byte-diffing the
> *rendered* strings against a pre-edit snapshot — see the card-JS note in
> [`CLAUDE.md`](../CLAUDE.md). The AI output is sanitized (`escapeHtml`/`sanitizeHtml`)
> before it is injected into the webview.

## Configuration: config.json vs meta.json

- **`config.json`** (committed) — default settings only.
- **`meta.json`** (gitignored, auto-created by Anki in the add-on dir) — **the source of
  truth** for user settings and all connected remote decks.

Both are managed *exclusively* through `config_manager.py` (`get_meta()` /
`save_meta()`). Never read or write these files directly from other modules.

## Development setup

Tooling is managed with [uv](https://docs.astral.sh/uv/) (`uv.lock`; Python 3.13 pinned
in `.python-version`):

```bash
uv sync --extra dev          # or: pip install -e ".[dev]"
```

To run inside Anki during development, symlink (or copy) the repository into Anki's
add-ons folder, e.g.:

```bash
ln -s "$(pwd)" ~/.local/share/Anki2/addons21/sheets2anki_dev   # Linux
# macOS: ~/Library/Application Support/Anki2/addons21/
```

## Testing

Anki is **auto-mocked** by `tests/conftest.py` (an import hook fabricates subclassable
`aqt`/`anki` modules and registers `src` as a package), so the suite runs without an
Anki install. Use the canonical runner — it sets the flags pytest needs:

```bash
python tests/run_tests.py                  # all tests
python tests/run_tests.py --unit           # only @pytest.mark.unit
python tests/run_tests.py --fast           # skip @pytest.mark.slow
python tests/run_tests.py --coverage       # coverage report → htmlcov/
python tests/run_tests.py --file core_logic --function test_duplicate_ids_detected
```

Running pytest directly **requires** two flags (the runner adds them automatically):

```bash
python -m pytest --rootdir=tests --import-mode=importlib tests/
```

> **Why the flags matter:** pytest config lives only in `pyproject.toml`
> `[tool.pytest.ini_options]` (the old `pytest.ini` was removed). Without
> `--rootdir=tests`, pytest builds a `Package` node for the repo-root `__init__.py`
> (the Anki entry point, which does `from .src…`) and fails to import it.

Current test modules:

| File | Covers |
| :--- | :--- |
| `test_core_logic.py` | URL conversion, note keying, duplicate-ID detection, core helpers |
| `test_data_processor.py` | TSV parsing, validation, Cloze detection, `RemoteDeck` |
| `test_config_manager.py` | Settings CRUD and persistence |
| `test_student_manager.py` | Multi-student filtering and subdecks |
| `test_utils.py` | URL/hash/validation utilities |
| `test_url_simplification.py` | Edit-URL → TSV conversion |
| `test_deck_configurations.py` | Deck-option handling |
| `test_search_fix.py` | Note-search edge cases |
| `test_sanity_check_isolation.py` | Template/prompt assertions on evaluated assets |
| `conftest.py` / `run_tests.py` | Mock-finder + fixtures / the test runner |

## Building & packaging

```bash
python scripts/build_packages.py        # interactive menu (recommended)
# or run a specific builder:
python scripts/create_ankiweb_package.py
python scripts/create_standalone_package.py
python scripts/validate_packages.py build/sheets2anki.ankiaddon
```

The builders produce `build/*.ankiaddon` ZIPs. AnkiWeb requires: files at the **ZIP
root** (no parent folder), a valid `manifest.json`, and **no `__pycache__`/`.pyc`** — the
scripts enforce and verify all three. The AnkiWeb variant strips the manifest to
mandatory fields; the standalone keeps the full manifest. See
[`scripts/README.md`](../scripts/README.md) for details.

> **`IS_DEVELOPMENT_MODE`** is defined `True` in `templates_and_definitions.py` and is
> left `True` in the repo (it gates the "Import Test Deck" menu item). The build scripts
> rewrite it to `False` in the packaged copy.

## Debugging

The add-on writes a debug log to **`debug_sheets2anki.log`** in the add-on directory.
Emit messages through `src/debug.py`:

```python
from .debug import add_debug_message
add_debug_message("Consistency check started", "NAME_CONSISTENCY")
```

A **Debug Mode** dialog (`Ctrl+Shift+L`) lets you toggle debug mode, view the log, and
reset configuration from inside Anki. `DebugManager` (in `src/debug.py`) owns the log
file's lifecycle.

## Conventions

- **Qt6 only.** Import Qt/Anki symbols through `compat.py`; do not reintroduce Qt5
  fallbacks or version-detection.
- **Dual-import pattern** in every `src/` module (see above).
- **Vendored `libs/`** is never edited, linted, or reformatted.
- **Formatting & lint:** `black` (line length 88) and `ruff` are **blocking** CI gates;
  `mypy` is advisory. The ruff config intentionally tolerates camelCase Anki-API names
  (`syncDecks`, `getRemoteDeck`) and the dual-import pattern — see `[tool.ruff.lint]` in
  `pyproject.toml`. Run them (or the pre-commit hooks) before pushing.
- **Version** is `3.0.3` in both `manifest.json` and `pyproject.toml`; keep them in sync
  on release.

---

For the contribution workflow and PR expectations, see
[`CONTRIBUTING.md`](../CONTRIBUTING.md). For the canonical, concise architecture rules,
see [`CLAUDE.md`](../CLAUDE.md).
