# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Sheets2Anki is an **Anki add-on** (not a standalone app) that syncs flashcard decks from Google Sheets into Anki. The repository root *is* the add-on directory: Anki loads `__init__.py` from the root, which registers a `Tools → Sheets2Anki` menu and wires keyboard shortcuts to functions in `src/`. There is no server and no main(); all code runs inside Anki's Python/Qt6 process.

## Commands

Tooling is managed with **uv** (`uv.lock`, Python 3.13 pinned in `.python-version`).

```bash
# Install dev/test deps
uv sync --extra dev          # or: pip install -e ".[dev]"

# Run tests (Anki is auto-mocked by tests/conftest.py — no Anki install needed).
# Use the canonical runner; it sets the required flags (see Note below).
python tests/run_tests.py                  # all tests
python tests/run_tests.py --unit           # only @pytest.mark.unit
python tests/run_tests.py --fast           # skip @pytest.mark.slow
python tests/run_tests.py --coverage       # coverage report → htmlcov/
python tests/run_tests.py --file core_logic --function test_duplicate_ids_detected

# Equivalent direct pytest (the two flags are REQUIRED — see Note):
python -m pytest --rootdir=tests --import-mode=importlib tests/
python -m pytest --rootdir=tests --import-mode=importlib tests/test_core_logic.py::TestUrls

# Lint / format / type-check
ruff check src/ tests/
black src/ tests/            # line-length 88
mypy src/

# Build distributable .ankiaddon packages (interactive menu)
python scripts/build_packages.py
```

**Note (test config):** pytest config lives only in `pyproject.toml` `[tool.pytest.ini_options]` (the old `pytest.ini` was removed). Tests **must** run with `--rootdir=tests --import-mode=importlib`, otherwise pytest builds a `Package` node for the repo-root `__init__.py` (the Anki entry point, which does `from .src...`) and fails to import it. `tests/run_tests.py` passes both flags automatically. `tests/conftest.py` installs an import hook that fabricates *subclassable* `aqt`/`anki` mocks and registers `src` as a package, so the real `src` modules import without Anki. Coverage is opt-in via `--coverage`.

## Architecture

### Layers
- **`__init__.py`** (root) — Anki integration entry point. Builds the menu and binds the nine user-facing shortcuts (Ctrl+Shift+A/S/D/O/W/C/P/B/L), plus Ctrl+Shift+T for the dev-only "Import Test Deck".
- **`src/`** — all add-on logic. The nine Qt dialogs live under **`src/ui/`** (plus `url_helpers.py`); foundational shared modules (`compat`, `styled_messages`, `config_manager`, `templates_and_definitions`, …) and the sync/data engine stay at the `src/` root. Modules in `src/ui/` import siblings one level up (`from ..compat import ...`).
- **Facade-split modules**: several large modules were decomposed but keep a back-compat **facade** (re-export) so `from .<module> import X` still resolves: `utils.py` → `errors.py` / `debug.py` (`DebugManager`, `add_debug_message`) / `deck_options.py`; `sync.py` → `sync_report.py` (summary HTML). When grepping for a definition, the real code may live in the split-out module even though imports point at the original.
- **No runtime third-party dependencies.** The add-on imports nothing but the stdlib and what Anki already provides. The old vendored `libs/` tree (`beautifulsoup4`, `soupsieve`, `chardet`, `org_to_anki`) and its `sys.path` bootstrap in `__init__.py` are **gone** — do not reintroduce a vendoring step or add a runtime dependency. Dev/test tooling is a separate matter (`[project.optional-dependencies] dev`).

### `src/compat.py` is the Qt/Anki gateway
Qt6-only (all Qt5 compat was removed in v3.0.0). **All Qt and Anki UI imports must go through `compat.py`**, not directly from `aqt`/`aqt.qt`. It re-exports widgets and defines Qt6 enum constants (e.g. `AlignCenter`, `DialogAccepted`, `MessageBox_Yes`) plus helpers (`StyledMessageBox` lives in `styled_messages.py`). When you need a new Qt symbol, add it to `compat.py`.

### Dual-context import pattern (important when editing `src/`)
Source modules are imported two ways: as a package inside Anki (relative imports) and by the test suite (which registers `src` as a package via `tests/conftest.py` and imports `from src.x import ...`). Many modules therefore use:
```python
try:
    from .compat import mw
except ImportError:
    from compat import mw
```
Preserve this pattern. `tests/conftest.py` fabricates the `aqt`/`anki` modules through a `sys.meta_path` import hook (not a fixture), so `src/` imports succeed without Anki.

### Configuration: `config.json` vs `meta.json` vs the collection config
- `config.json` (committed) — default settings only.
- `meta.json` (gitignored, auto-created by Anki in the add-on dir) — **the source of truth** for machine-local user settings + all connected remote decks. Managed entirely through `config_manager.py` (`get_meta()` / `save_meta()`). Never read/write these files directly elsewhere.
- **Anki's collection config** (`col.get_config` / `col.set_config`) — home of the per-deck **card layouts**, under the single key `sheets2anki::card_layouts` holding `{sheet_id: layout}`. Anki's `config` table carries a `usn`, so anything stored there rides along to every machine the collection syncs to. Managed entirely through `src/sync_config.py`.

### Sync data flow
`deck_manager.syncDecksWithSelection()` → `sync.syncDecks()` orchestrates everything. Per deck:
1. A Google Sheets **edit URL** is converted to a TSV export URL (`.../export?format=tsv`) — see `utils.convert_edit_url_to_tsv` / `get_spreadsheet_id_from_url`.
2. `data_processor.getRemoteDeck()` downloads + `parse_tsv_data()` + `build_remote_deck_from_tsv()` → a `RemoteDeck`. The header row is sorted into a `ColumnPlan` by `column_model.plan_columns()`, and the deck carries it as `RemoteDeck.plan`.
3. `data_processor.create_or_update_notes()` creates/updates/deletes Anki notes. It first calls `get_deck_layout()` — which reads the deck's card layout, or creates it from the column order on first sight — and `templates_and_definitions.ensure_custom_models()`, which provisions the Basic/Cloze note types from `plan` + `layout`.

### Column model & note keying (`src/column_model.py`)
There is **no fixed column list**. The sheet decides the schema: only a handful of headers are reserved, and every other column becomes a note field named exactly like its header — so headers can be in any language.
- **Reserved headers** (matched case-insensitively, surrounding whitespace and BOM ignored — `column_model.normalize` / `clean`):
  - `ID` — the stable per-row key. Required; never regenerate it.
  - `SYNC` — per-row gate (`row_is_marked_for_sync`, truthy values in `SYNC_TRUE_VALUES`). **A sheet with no SYNC column syncs every row** — absence means "no gating", not "nothing syncs".
  - `SUBDECK 1..N` — one level of the deck path each. Ordered **by the number, not by column position** (`subdeck_level`), and empty levels are skipped (`deck_path`).
  - `TAGS` — extra tags, comma- or semicolon-separated (`tags_of`).
- `plan_columns(headers)` sorts a header row into a `ColumnPlan` (`id_header`, `sync_header`, `tags_header`, `subdeck_headers`, `content_headers`, `duplicates`). A repeated header is honoured once — first occurrence wins. The `ColumnPlan` is threaded through parsing, note creation and note-type provisioning; most `data_processor` functions take it as `plan`.
- **Note types (models)** are `Sheets2Anki - {deck} - Basic` and `- Cloze` (`utils.get_note_type_name`, `templates_and_definitions.create_model` / `ensure_custom_models`). Fields are `plan.note_type_fields()` = `["ID"] + content_headers` — `ID` leads because Anki uses the first field for duplicate detection. There is **no `- Reverse` note type**; the reverse direction is a second card *template* on the same note type (see below). `name_consistency_manager.py` keeps the names in sync when a deck is renamed.
- **Schema drift is asymmetric on purpose**: adding a column adds the field (`add_missing_fields`) and appends it to the back of the card (`sync_config._coerce`); **removing a column stops rendering it but never removes the field**, because dropping it would destroy content the user already collected.
- **Note keying**: notes are matched by the plain spreadsheet `ID`, read straight out of the note's `ID` field (`data_processor.get_existing_notes_by_id`). One row is always exactly one note. There are no `[MISSING_*]` sentinels and no `_REV` keys any more.
- **Cloze** is auto-detected per row by scanning **every content column** for `{{c1::...}}` (`data_processor.row_has_cloze` → `has_cloze_deletion`), which routes the row to the Cloze note type.
- Deck hierarchy: `Sheets2Anki::{deck}` followed by the row's `SUBDECK` levels (`utils.get_subdeck_name`, `data_processor.determine_target_deck`) — a sheet with no `SUBDECK` columns keeps everything in the deck root. Tags (`data_processor.build_tags`): `sheets2anki`, `sheets2anki::<subdeck path>`, plus whatever `TAGS` lists.

### Card layout (`src/sync_config.py`, `src/card_layout.py`, `src/ui/card_layout_dialog.py`)
How a card looks is a **per-deck layout dict**, not a property of the sheet. `sync_config.py` stores it in the Anki collection config (see above) and defaults it from the sheet's own column order — first content column on the front, the rest on the back (`default_layout_for`). Keys (`DEFAULT_LAYOUT`): `front`, `back`, `show_labels`, `front_size`, `back_size`, `align`, `reverse_card`, `timer`, `timer_position`, `hand_edited`.
- `card_layout.build_templates(layout, is_cloze)` turns a layout into the `{"name", "qfmt", "afmt"}` template list. `reverse_card` adds a **second template on the same note type** (`"Card 2 (reverse)"`) rather than a second note — Anki then schedules both directions independently off one row, and switching it off later removes those cards (`apply_templates` prunes templates the layout no longer produces) without touching the note's content. Cloze note types support only one template, so the reverse card is skipped for them.
- `hand_edited: True` makes sync stop regenerating the note type's templates (`ensure_custom_models`, `update_existing_note_type_templates`), so the user's own template edits survive.
- `src/ui/card_layout_dialog.py` is the editor (`Tools → Sheets2Anki → Configure Card Layout`, `Ctrl+Shift+C`). It only moves field *names* between the front/back lists and never writes HTML — that is `build_templates`' job. Its preview approximates Anki's template syntax in a `QTextBrowser` (sections always taken, scripts stripped).

### Card-side features (rendered into card HTML/CSS/JS)
`src/card_assets.py` holds the CSS/HTML/JS template strings for the study **timer**. `card_layout.py` imports them directly and composes them into the templates: `_timer_parts()` picks the timer CSS/JS for the layout's `timer` and `timer_position` keys. **The timer is per-deck only** — it is part of the layout dict, and there is no global timer setting: the old `Configure Timer` dialog and `config_manager.get_timer_position()` were removed because nothing read them.

### `IS_DEVELOPMENT_MODE` (build-time flip)
Defined `True` in `templates_and_definitions.py`. The AnkiWeb/standalone build scripts **rewrite it to `False`** in the packaged copy. It gates the "Import Test Deck" menu item and `TEST_SHEETS_URLS`. Leave it `True` in the repo.

## Building & packaging

`scripts/create_ankiweb_package.py` and `create_standalone_package.py` produce `build/*.ankiaddon` ZIPs. AnkiWeb requires: files at the **ZIP root** (no parent folder), a valid `manifest.json`, and **no `__pycache__`/`.pyc`** — the scripts enforce and verify all three. The AnkiWeb variant strips the manifest to mandatory fields; the standalone keeps the full manifest. `validate_packages.py` checks an existing `.ankiaddon`.

## Gotchas
- **The version lives in `manifest.json` and `pyproject.toml` and the two must always agree.** Do not write the current number into prose (that is exactly how this line went stale); read it from the files. Releases are tag-driven, and `.github/workflows/release.yml` fails the build before packaging if the tag, `manifest.json` and `pyproject.toml` do not all match — so bump both files in the same commit as the tag.
- Requires Anki **25.x+** / Qt6 / Python 3.13 — do not reintroduce version-detection or Qt5 fallbacks.
