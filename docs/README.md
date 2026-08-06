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
- [Card layout](#card-layout)
- [Card-side features & the AI layer](#card-side-features--the-ai-layer)
- [Configuration: where settings live](#configuration-where-settings-live)
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
│  • Tools → Sheets2Anki menu     • 11 keyboard shortcuts (Ctrl+Shift+…) │
│  • webview_did_receive_js_message hook (AI button pycmd messages)      │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
┌───────────────────────────────▼──────────────────────────────────────┐
│  Add-on logic  (src/)                                                   │
│  • sync engine / data processing  • configuration management           │
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
│   └── ui/                     # Qt dialogs (11 modules + url_helpers.py)
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
  (`create_or_update_notes()`); detects Cloze rows (`row_has_cloze()` /
  `has_cloze_deletion()`) and builds each row's tags (`build_tags()`) and target
  subdeck (`determine_target_deck()`).
- **`column_model.py`** — the free-form column model: which headers are reserved, and
  how a header row is sorted into a `ColumnPlan` (`plan_columns()`). Also the per-row
  readers `row_is_marked_for_sync()`, `deck_path()`, `tags_of()`.
- **`deck_manager.py`** — deck CRUD and the selection entry point
  (`syncDecksWithSelection()`).
- **`name_consistency_manager.py`** — keeps dynamically-created note-type names in sync
  when a deck is renamed.

### Configuration & utilities
- **`config_manager.py`** — the only module that reads/writes `meta.json`/`config.json`
  (`get_meta()` / `save_meta()`); AI prompt defaults live in **`ai_prompts.py`**.
- **`sync_config.py`** — the settings that must follow the user between machines: the
  per-deck **card layouts**, stored in Anki's own collection config
  (`get_card_layout()`, `set_card_layout()`, `ensure_card_layout()`,
  `forget_card_layout()`, `DEFAULT_LAYOUT`).
- **`card_layout.py`** — turns a layout dict into Anki card templates
  (`build_templates()`), including the optional reverse template and the timer/AI
  blocks (`ai_components_for()`).
- **`utils.py`** — URL conversion (`convert_edit_url_to_tsv()`,
  `get_spreadsheet_id_from_url()`), note-type naming (`get_note_type_name()`), subdeck
  naming (`get_subdeck_name()`), and other helpers; errors/debug/deck-options were split
  into **`errors.py`**, **`debug.py`**, **`deck_options.py`**.
- **`templates_and_definitions.py`** — note-type provisioning against the sheet's columns
  and the deck's layout (`ensure_custom_models()`, `create_model()`,
  `add_missing_fields()`, `apply_templates()`), plus `IS_DEVELOPMENT_MODE` and
  `TAG_ROOT`; the large CSS/HTML/JS strings live in **`card_assets.py`**.

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
Eleven Qt dialogs (add deck, sync, disconnect, backup, debug, deck-options config,
AnkiWeb config, **card-layout config**, AI-assistance config, image-processor config,
timer config), plus `url_helpers.py` (shared clean-URL / copy-to-clipboard helpers).
Modules in `src/ui/` import siblings one level up (`from ..compat import …`).

**`card_layout_dialog.py`** is the editor for a deck's card layout: it moves field
*names* between the front and back lists and never writes HTML itself — that is
`card_layout.build_templates()`' job. Its live preview only *approximates* Anki's
template syntax in a `QTextBrowser` (every section is taken, `<script>` blocks are
stripped, since the widget runs no JavaScript). Its user-facing strings are Vietnamese,
matching the add-on's audience; the surrounding code stays English like the rest of the
repository.

## Sync data flow

`deck_manager.syncDecksWithSelection()` → `sync.syncDecks()` orchestrates everything.
Per deck:

1. **URL → TSV.** A Google Sheets **edit URL** is converted to a TSV export URL
   (`.../export?format=tsv`) — `utils.convert_edit_url_to_tsv()` /
   `get_spreadsheet_id_from_url()`. Downloads are restricted to Google hosts.
2. **Download & parse.** `data_processor.getRemoteDeck()` downloads the TSV, runs
   `parse_tsv_data()` and `build_remote_deck_from_tsv()`, and returns a `RemoteDeck`
   (which tracks `valid_note_lines`, `invalid_note_lines`, etc.). The header row is
   sorted into a `ColumnPlan` by `column_model.plan_columns()` and carried on the deck
   as `RemoteDeck.plan`; every later step takes it as its `plan` argument.
3. **Provision the note types.** `data_processor.get_deck_layout()` reads the deck's
   card layout — creating it from the sheet's column order the first time the deck is
   seen — and `templates_and_definitions.ensure_custom_models()` makes the Basic and
   Cloze note types match `plan` (fields) and `layout` (templates).
4. **Apply changes.** `data_processor.create_or_update_notes()` creates, updates, and
   deletes Anki notes to match the sheet. (Steps 3 and 4 are one call: `get_deck_layout()`
   and `ensure_custom_models()` run at the top of `create_or_update_notes()`.)

> **Safety guard:** if a parsed sheet has `valid_note_lines == 0` (e.g. an empty or
> failed fetch), the deletion pass is skipped so a transient blank download can't wipe
> a deck.

## Column model & note keying

There is **no fixed column list**. The spreadsheet drives the schema: a handful of
headers are reserved, and every other column becomes a note field named exactly like the
header — so a sheet can use whatever vocabulary its subject calls for ("Hán tự",
"Pinyin", "Nghĩa") instead of a column list baked into the code. This all lives in
`column_model.py`.

- **Reserved headers**, matched case-insensitively with surrounding whitespace and any
  BOM stripped (`column_model.normalize()` / `clean()`):

  | Header | Role |
  | :--- | :--- |
  | `ID` | The row's stable key. **Required** — a row with an empty `ID` is not synced. Never regenerate it. |
  | `SYNC` | Per-row gate (`row_is_marked_for_sync()`, truthy values in `SYNC_TRUE_VALUES`). **A sheet with no `SYNC` column syncs every row** — absence means "no gating", not "nothing syncs". |
  | `SUBDECK 1..N` | One level of the deck path each, ordered **by the number, not the column position** (`subdeck_level()`); empty levels are dropped (`deck_path()`). |
  | `TAGS` | Extra tags for the row, split on commas and semicolons (`tags_of()`). |

- **`ColumnPlan`.** `plan_columns(headers)` sorts a header row into `id_header`,
  `sync_header`, `tags_header`, `subdeck_headers` and `content_headers` (everything else,
  in sheet order). A header repeated in the sheet is honoured once — the first occurrence
  wins and the rest are recorded in `duplicates`.
- **Note keying.** Notes are matched by the plain spreadsheet `ID`, read straight out of
  the note's `ID` field (`data_processor.get_existing_notes_by_id()`). One row is always
  exactly one note; there are no `_REV` keys and no `[MISSING_*]` sentinels any more.
  Duplicate non-empty IDs are detected during the build and reported
  (`RemoteDeck.duplicate_ids`), because they would silently collapse into one note.
- **Note types (models)** are created dynamically, one set per
  `Sheets2Anki - {deck} - Basic` / `- Cloze` (`utils.get_note_type_name()`,
  `templates_and_definitions.ensure_custom_models()` / `create_model()`). Their fields are
  `plan.note_type_fields()` — `["ID"] + content_headers`, with `ID` first because Anki
  uses the first field for duplicate detection. There is **no `- Reverse` note type**: the
  reverse direction is a second card *template* on the same note type (see
  [Card layout](#card-layout)). `name_consistency_manager.py` keeps the names aligned when
  a deck is renamed.
- **Schema drift is deliberately asymmetric.** Adding a column adds the field
  (`add_missing_fields()`) and appends it to the back of the card (`sync_config._coerce()`).
  **Removing a column stops the field being rendered but never removes it** — dropping it
  would silently delete content the user already collected.
- **Cloze** is decided per row by scanning **every content column** for `{{c1::…}}`
  (`data_processor.row_has_cloze()` → `has_cloze_deletion()`), which routes the row to the
  Cloze note type.
- **Deck hierarchy:** `Sheets2Anki::{deck}` followed by the row's `SUBDECK` levels
  (`utils.get_subdeck_name()`, `data_processor.determine_target_deck()`). A sheet with no
  `SUBDECK` columns keeps every note in the deck root.
- **Tags** (`data_processor.build_tags()`): `sheets2anki` on every note the add-on owns,
  `sheets2anki::<subdeck path>` mirroring the deck path, plus whatever the `TAGS` column
  lists. Each component is folded to a safe lower-case tag by `clean_tag_text()`.

## Card layout

How a card looks is a **per-deck layout dict**, not a property of the sheet.
`sync_config.DEFAULT_LAYOUT` defines its keys: `front`, `back`, `show_labels`,
`front_size`, `back_size`, `align`, `reverse_card`, `timer`, `timer_position`,
`hand_edited`. On first sight of a deck, `default_layout_for()` seeds it from the sheet's
own column order — first content column on the front, the rest on the back, the same
convention as Anki's CSV import.

`card_layout.build_templates(layout, is_cloze, ai_components)` renders it into the
`{"name", "qfmt", "afmt"}` template list:

- **Reverse cards are a second template on the same note type** (`"Card 2 (reverse)"`),
  not a second note. Anki then schedules both directions independently off one row, and
  switching the option off later removes those cards without touching the note's content
  (`apply_templates()` prunes templates the layout no longer produces). Cloze note types
  support exactly one template, so the reverse card is skipped for them.
- A layout with an empty `front` falls back to the first field it does have, since Anki
  refuses to generate a card from a blank prompt.
- Cloze backs repeat the prompt through `{{cloze:Field}}` rather than `{{FrontSide}}`,
  because Anki validates that a cloze template references the filter on both sides.
- `hand_edited: True` makes sync stop regenerating that deck's templates
  (`ensure_custom_models()`, `update_existing_note_type_templates()`), so template work
  the user did by hand in Anki survives a sync.

`src/ui/card_layout_dialog.py` is the editor, reachable at
`Tools → Sheets2Anki → Configure Card Layout` (`Ctrl+Shift+C`).

## Card-side features & the AI layer

`card_assets.py` holds the CSS/HTML/JS rendered into cards — the study **timer** and the
**AI Help / AI Ask / AI Checker** buttons — and `card_layout.py` composes them into the
templates (`_timer_parts()` picks the CSS/JS for the layout's `timer_position`;
`ai_components_for()` / `templates_and_definitions.ai_components()` assemble the AI block
appended to the back). The AI layer has two execution paths that must stay in sync:

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

## Configuration: where settings live

Settings are split by whether they should follow the user to their other machines.

- **`config.json`** (committed) — default settings only.
- **`meta.json`** (gitignored, auto-created by Anki in the add-on dir) — **the source of
  truth** for machine-local user settings and all connected remote decks. The AI provider
  API key lives here deliberately: it must not be uploaded to AnkiWeb.
- **Anki's collection config** (`col.get_config()` / `col.set_config()`) — the per-deck
  **card layouts**, under the single key `sheets2anki::card_layouts` holding
  `{sheet_id: layout}`. Anki's `config` table carries a `usn`, so entries there sync
  through AnkiWeb along with the notes and note types; a layout configured on one machine
  shows up on the next one with no Google API and no extra setup.

`config.json`/`meta.json` are managed *exclusively* through `config_manager.py`
(`get_meta()` / `save_meta()`), and the collection config *exclusively* through
`sync_config.py`. Never read or write either store directly from other modules.

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
| `test_column_model.py` | Header normalization, `plan_columns()`, SYNC gating, deck path, tags |
| `test_card_layout.py` | Layout defaults/reconciliation and template generation |
| `test_data_processor.py` | TSV parsing, validation, Cloze detection, `RemoteDeck` |
| `test_config_manager.py` | Settings CRUD and persistence |
| `test_utils.py` | URL/hash/validation utilities |
| `test_url_simplification.py` | Edit-URL → TSV conversion |
| `test_deck_configurations.py` | Deck-option handling |
| `test_search_fix.py` | Note-search edge cases |
| `test_sanity_check_isolation.py` | Template/prompt assertions on evaluated assets |
| `test_theme.py` | Design-system tokens and `get_colors()` |
| `test_backup_threading.py` | Backup/restore stays on the calling thread |
| `test_ui_import_smoke.py` | Every dialog module imports cleanly |
| `test_ui_instantiate_smoke.py` | Every dialog constructs (full `__init__`) |
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
