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
- **Anki's collection config** (`col.get_config` / `col.set_config`) — a **cache of the settings row each sheet was last parsed into**, under the single key `sheets2anki::sheet_settings` holding `{sheet_id: entry}`. Anki's `config` table carries a `usn`, so anything stored there rides along to every machine the collection syncs to. Managed entirely through `src/sync_config.py`. It is a cache, never an editable store: the spreadsheet is the source of truth and a sync overwrites the entry.

### Sync data flow
`deck_manager.syncDecksWithSelection()` → `sync.syncDecks()` orchestrates everything. Per deck:
1. A Google Sheets **edit URL** is converted to a TSV export URL (`.../export?format=tsv`) — see `utils.convert_edit_url_to_tsv` / `get_spreadsheet_id_from_url`.
2. `data_processor.getRemoteDeck()` downloads + `parse_tsv_data()` + `build_remote_deck_from_tsv()` → a `RemoteDeck`. The header row is sorted into a `ColumnPlan` by `column_model.plan_columns()`, and the deck carries it as `RemoteDeck.plan`.
3. Still inside `build_remote_deck_from_tsv()`: if the row under the header is a settings row (`sheet_config.is_config_row`), it is parsed (`parse_config_row`) into a `SheetConfig` carried as `RemoteDeck.sheet_config`, and **removed from `rows` before anything is counted** — it must never reach `add_note()` or any metric. `first_row_offset` keeps logged row numbers matching the sheet.
4. `data_processor.create_or_update_notes()` creates/updates/deletes Anki notes. It caches the parsed settings (`cache_deck_sheet_config()` → `sync_config.cache_sheet_settings()`) and calls `templates_and_definitions.ensure_custom_models()`, which provisions the Basic/Cloze note types from `plan` (fields) + `sheet_config` (templates). Paths that provision a note type without the downloaded deck in hand read the cache back through `get_deck_sheet_config()`.

### Column model & note keying (`src/column_model.py`)
There is **no fixed column list**. The sheet decides the schema: only a handful of headers are reserved, and every other column becomes a note field named exactly like its header — so headers can be in any language. Row 1 is the header row; row 2 is either data or the optional **settings row** (see *Presentation* below).
- **Reserved headers** (matched case-insensitively, surrounding whitespace and BOM ignored — `column_model.normalize` / `clean`):
  - `ID` — the stable per-row key. Required; never regenerate it.
  - `SYNC` — per-row gate (`row_is_marked_for_sync`, truthy values in `SYNC_TRUE_VALUES`). **A sheet with no SYNC column syncs every row** — absence means "no gating", not "nothing syncs".
  - `SUBDECK 1..N` — one level of the deck path each. Ordered **by the number, not by column position** (`subdeck_level`), and empty levels are skipped (`deck_path`).
  - `TAGS` — extra tags, comma- or semicolon-separated (`tags_of`).
- `plan_columns(headers)` sorts a header row into a `ColumnPlan` (`id_header`, `sync_header`, `tags_header`, `subdeck_headers`, `content_headers`, `duplicates`). A repeated header is honoured once — first occurrence wins. The `ColumnPlan` is threaded through parsing, note creation and note-type provisioning; most `data_processor` functions take it as `plan`.
- **Note types (models)** are `Sheets2Anki - {deck} - Basic` and `- Cloze` (`utils.get_note_type_name`, `templates_and_definitions.create_model` / `ensure_custom_models`). Fields are `plan.note_type_fields()` = `["ID"] + content_headers` — `ID` leads because Anki uses the first field for duplicate detection. There is **no `- Reverse` note type**; the reverse direction is a second card *template* on the same note type (see below). `name_consistency_manager.py` keeps the names in sync when a deck is renamed.
- **Schema drift is asymmetric on purpose**: adding a column adds the field (`add_missing_fields`) and, unless the settings row says otherwise, puts it on the back of the card (`card_layout.split_sides`); **removing a column stops rendering it but never removes the field**, because dropping it would destroy content the user already collected.
- **Note keying**: notes are matched by the plain spreadsheet `ID`, read straight out of the note's `ID` field (`data_processor.get_existing_notes_by_id`). One row is always exactly one note. There are no `[MISSING_*]` sentinels and no `_REV` keys any more.
- **Cloze** is auto-detected per row by scanning **every content column** for `{{c1::...}}` (`data_processor.row_has_cloze` → `has_cloze_deletion`), which routes the row to the Cloze note type.
- Deck hierarchy: `Sheets2Anki::{deck}` followed by the row's `SUBDECK` levels (`utils.get_subdeck_name`, `data_processor.determine_target_deck`) — a sheet with no `SUBDECK` columns keeps everything in the deck root. Tags (`data_processor.build_tags`): `sheets2anki`, `sheets2anki::<subdeck path>`, plus whatever `TAGS` lists.

### Presentation: the sheet's settings row (`src/sheet_config.py`, `src/card_layout.py`, `src/sync_config.py`)
**How a card looks is a property of the sheet, not of the deck.** The pipeline is parse → render → cache:
- **`src/sheet_config.py` parses it.** Row 2 is the settings row when its `ID` cell is `#config` or starts with `#config ` (`is_config_row`, matched lower-cased — so `#config;align=left` is *not* the marker and that row becomes data). `parse_config_row(row, plan)` returns a `SheetConfig` (`fields: {header: FieldConfig}`, deck-wide `align`/`speed`/`reverse`, `present`, `warnings`). Cells are `key=value` pairs split on `;`; a bare key is a flag. Only `plan.content_headers` + the ID cell are read. Per-field keys: `side` (front/back/hide), `size` (int, **6–200**, `px` suffix tolerated), `color` (`muted`/`accent` → `var(--s2a-*)`, the real CSS named-colour list, or `#hex`), `align`, `tts`, `voices`, `speed` (**0.5–2.0**), `label`, and the flags `bold`/`italic`/`hint`/`furigana`. Deck-wide keys (`_DECK_KEYS`): `align`, `speed` (**not** range-checked, unlike the per-field one), `reverse`.
- **Nothing is silently dropped.** An unknown key, a bad value or an out-of-range number appends to `SheetConfig.warnings` naming the column; the value is refused, never clamped. `data_processor.build_remote_deck_from_tsv()` echoes each warning to the debug log under the `SHEET_CONFIG` category, and the cache carries them to the dialog.
- **`tts` requires a full language code** (`^[a-zA-Z]{2,3}[-_][a-zA-Z0-9]{2,4}$`, normalised by `normalize_tts_language` to `zh_CN` shape). Anki matches a TTS tag to an installed voice with an **exact** string compare (`aqt/tts.py`: `if avail.lang == tag.lang`), so a bare `zh` matches nothing and plays silence. Short codes are rejected rather than guessed at — guessing `zh_CN` for a Traditional-Chinese learner would be wrong *and* inaudible. `voices` is a preference (Anki falls back to any voice of that language), and a language with no installed voice is silent with no error.
- **`src/card_layout.py` renders from it.** `split_sides(plan, sheet_config)` applies the default (first content column front, rest back), `side=` overrides, `side=hide` drops; an empty front promotes the first visible back field. `build_templates(plan, sheet_config, is_cloze)` returns the `{"name", "qfmt", "afmt"}` list. Per field: `_inline_style` (size/color/bold/italic/align), `_reference` (plain, `{{hint:…}}` or `{{furigana:…}}`), `_tts_tag` (`{{tts LANG voices=… speed=…:Field}}`, field-level `speed` beating the deck-wide one). Both the field div and the TTS tag are wrapped in `{{#Field}}…{{/Field}}` so an empty cell renders — and speaks — nothing.
- **Cloze gotcha**: `cloze:` outranks `hint`/`furigana` in `_reference`, and the cloze **back repeats the prompt through `{{cloze:Field}}` instead of `{{FrontSide}}`** — Anki validates that a cloze template references the field through that filter on *both* sides and refuses to save the note type otherwise. Cloze note types also support exactly one template, so `reverse` is skipped for them.
- **`src/sync_config.py` caches the result** (`to_dict`/`from_dict`, `cache_sheet_settings`, `cached_plan_and_config`, `forget_sheet_settings`) under `sheets2anki::sheet_settings`, so `update_existing_note_type_templates()` can rebuild templates outside a sync and the dialog can show a deck's settings without downloading the sheet. A cache entry with no `content_headers` yields `(None, None)` — rendering from it would blank the card.
- **`src/ui/card_layout_dialog.py` is a read-only viewer** (`Ctrl+Shift+C`): the parsed sides, the per-column settings, the warnings, the TTS voices installed on this machine, and a preview. **Do not add editing controls to it.** Two places able to change one setting means the loser is silently overwritten on the next sync, which is exactly how a control ends up doing nothing with no way to tell. Settings are changed in the sheet and re-synced.

### `IS_DEVELOPMENT_MODE` (build-time flip)
Defined `True` in `templates_and_definitions.py`. The AnkiWeb/standalone build scripts **rewrite it to `False`** in the packaged copy. It gates the "Import Test Deck" menu item and `TEST_SHEETS_URLS`. Leave it `True` in the repo.

## Building & packaging

`scripts/create_ankiweb_package.py` and `create_standalone_package.py` produce `build/*.ankiaddon` ZIPs. AnkiWeb requires: files at the **ZIP root** (no parent folder), a valid `manifest.json`, and **no `__pycache__`/`.pyc`** — the scripts enforce and verify all three. The AnkiWeb variant strips the manifest to mandatory fields; the standalone keeps the full manifest. `validate_packages.py` checks an existing `.ankiaddon`.

## Gotchas
- **The version lives in `manifest.json` and `pyproject.toml` and the two must always agree.** Do not write the current number into prose (that is exactly how this line went stale); read it from the files. **Releasing is driven by the version**: merging to `main` with both files bumped makes `.github/workflows/release.yml` tag, build and publish; merging without a bump finds the tag already present and stops. The run fails if the two files disagree, or if `docs/CHANGELOG.md` has no section for that version — so a release always carries notes.
- Requires Anki **25.x+** / Qt6 / Python 3.13 — do not reintroduce version-detection or Qt5 fallbacks.
