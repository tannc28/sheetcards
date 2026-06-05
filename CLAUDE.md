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
- **`__init__.py`** (root) — Anki integration entry point. Builds the menu, binds shortcuts (Ctrl+Shift+A/S/D/G/O/W/I/H/P/B/L), and registers the `webview_did_receive_js_message` hook that handles AI button clicks (`pycmd` messages `sheets2anki_ai_help/ask/checker:`).
- **`src/`** — all add-on logic. UI dialogs/screens live under **`src/ui/`**; foundational shared modules (`compat`, `styled_messages`, `config_manager`, `templates_and_definitions`, …) and the sync/data engine stay at the `src/` root. Modules in `src/ui/` import siblings one level up (`from ..compat import ...`).
- **Facade-split modules**: several large modules were decomposed but keep a back-compat **facade** (re-export) so `from .<module> import X` still resolves: `utils.py` → `errors.py` / `debug.py` (`DebugManager`, `add_debug_message`) / `deck_options.py`; `sync.py` → `sync_report.py` (summary HTML); `config_manager.py` → `ai_prompts.py`; `templates_and_definitions.py` → `card_assets.py`. When grepping for a definition, the real code may live in the split-out module even though imports point at the original.
- **`libs/`** — **vendored** third-party deps (`beautifulsoup4`, `chardet`, `org_to_anki`, `pygments`). Added to `sys.path` at runtime by `__init__.py`. **Never edit or lint these**; they're excluded from ruff/black/coverage.

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
Preserve this pattern. `tests/conftest.py` mocks `aqt`/`anki` modules via an autouse fixture so `src/` imports succeed without Anki.

### Configuration: `config.json` vs `meta.json`
- `config.json` (committed) — default settings only.
- `meta.json` (gitignored, auto-created by Anki in the add-on dir) — **the source of truth** for user settings + all connected remote decks. Managed entirely through `config_manager.py` (`get_meta()` / `save_meta()`). Never read/write these files directly elsewhere.

### Sync data flow
`deck_manager.syncDecksWithSelection()` → `sync.syncDecks()` orchestrates everything. Per deck:
1. A Google Sheets **edit URL** is converted to a TSV export URL (`.../export?format=tsv`) — see `utils.convert_edit_url_to_tsv` / `get_spreadsheet_id_from_url`.
2. `data_processor.getRemoteDeck()` downloads + `parse_tsv_data()` + `build_remote_deck_from_tsv()` → a `RemoteDeck`.
3. `data_processor.create_or_update_notes()` creates/updates/deletes Anki notes.

### Column model & note keying
- Column names are centralized in `src/templates_and_definitions.py` (imported elsewhere as `cols`). Required headers: `ID`, `QUESTION`, `ANSWER`. `ID` is the stable per-row key — never regenerate it.
- **Multi-student**: the `STUDENTS` column duplicates a row into per-student subdecks. Notes are matched/tracked by a composite **`{student}_{note_id}`** key (`extract_student_from_student_note_id`, `get_existing_notes_by_student_id`). `[MISSING_STUDENT]` and other `[MISSING_*]` sentinels (defined in `templates_and_definitions.py`) are real values, handled specially.
- **Note types (models)** are created dynamically per `Sheets2Anki - {deck} - {student} - Basic|Cloze|Reverse` (`utils.get_note_type_name`, `templates_and_definitions.create_model`). `name_consistency_manager.py` keeps these names in sync when a deck is renamed.
- **Cloze** cards are auto-detected from `{{c1::...}}` patterns (`data_processor.has_cloze_deletion`).
- Deck hierarchy: `Sheets2Anki::{deck}::{student}::{importance}::{topic}::{subtopic}::{concept}`. Tags: hierarchical `sheets2anki::...` (`create_tags_from_fields`).

### Card-side features (rendered into card HTML/CSS/JS)
`src/card_assets.py` holds the large CSS/HTML/JS template strings for the study **timer** and the **AI Help / AI Ask / AI Checker** buttons (re-exported from `templates_and_definitions.py` via a back-compat facade; the model-building functions in `templates_and_definitions.py` compose them). The AI layer has two execution paths:
- **Desktop**: card JS calls `pycmd(...)` → handled in `__init__.py` → `ai_service.call_ai_api_async()` (Gemini/Claude/OpenAI).
- **Mobile/Web (AnkiMobile, AnkiWeb)**: `pycmd` is unavailable, so the JS calls the provider API directly using config embedded into the template (`AI_HELP_JS_MOBILE_TEMPLATE`, with base64-encoded prompts). Keep both paths in sync when changing AI behavior.

### `IS_DEVELOPMENT_MODE` (build-time flip)
Defined `True` in `templates_and_definitions.py`. The AnkiWeb/standalone build scripts **rewrite it to `False`** in the packaged copy. It gates the "Import Test Deck" menu item and `TEST_SHEETS_URLS`. Leave it `True` in the repo.

## Building & packaging

`scripts/create_ankiweb_package.py` and `create_standalone_package.py` produce `build/*.ankiaddon` ZIPs. AnkiWeb requires: files at the **ZIP root** (no parent folder), a valid `manifest.json`, and **no `__pycache__`/`.pyc`** — the scripts enforce and verify all three. The AnkiWeb variant strips the manifest to mandatory fields; the standalone keeps the full manifest. `validate_packages.py` checks an existing `.ankiaddon`.

## Gotchas
- Version is `3.0.0` in both `manifest.json` and `pyproject.toml` (keep them in sync on release).
- Card-template JS lives in `src/card_assets.py` as two blocks (`AI_HELP_JS_DESKTOP` and `AI_HELP_JS_MOBILE_TEMPLATE`), composed from shared `_AI_JS_*` constants. Everything byte-identical between the two blocks is now single-source: `_AI_JS_HEAD` (the `escapeHtml`/`sanitizeHtml` sanitizer), `_AI_JS_TAIL` (`closeAIHelpModal` + the `globalThis` bridge), `_AI_JS_ASK_MODAL`, `_AI_JS_RESET_ASK`, `_AI_JS_COLLECT`, `_AI_JS_RENDER`, and `_AI_JS_CAPTURE` (the capture IIFE). Only the genuinely-divergent functions stay per-block: `requestAIHelp`/`requestAIChecker`/`submitAIAsk` (desktop is pycmd-only; mobile falls back to direct-provider calls), `processMathAndMarkdown` (one comment differs), and `showAIHelpResponse`/`showAIHelpError` (desktop modal-only vs mobile inline-vs-modal) — a change to one of those must be mirrored in both. **Verify any template edit by byte-diffing the rendered strings** (`AI_HELP_JS_DESKTOP`, `AI_HELP_JS_MOBILE_TEMPLATE`, and `generate_ai_assistance_js(mobile_enabled=True, …)`) against a pre-edit snapshot — the cards only see the composed output.
- Requires Anki **25.x+** / Qt6 / Python 3.13 — do not reintroduce version-detection or Qt5 fallbacks.
