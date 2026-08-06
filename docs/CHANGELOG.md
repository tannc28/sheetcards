# 📋 CHANGELOG - Sheets2Anki

## Complete History of Updates and Modifications

---

## 💥 **v4.0.0** - August 2026 *(Breaking — the sheet now defines the schema)*

The fixed 24-column schema is gone. A sheet declares its own fields, and the card is
built from a layout the user edits in a dialog instead of one hard-coded in Python.

### 💥 Breaking
- **Only four headers are reserved**: `ID` (the key), `SYNC` (per-row gate), `SUBDECK 1..N`
  (deck path, ordered by the number rather than the column position, empty levels
  skipped) and `TAGS`. **Every other column becomes a note field named exactly like the
  header**, so a sheet can use whatever vocabulary its subject calls for. Column order
  decides what lands on the front and back of the card.
- The old exam-prep columns (`QUESTION`, `ANSWER`, `REVERSE`, `IMPORTANCE`, `TOPIC`,
  `SUBTOPIC`, `CONCEPT`, `BOARDS`, `LAST YEAR IN EXAM`, `CAREERS`, `OTHER TAGS`,
  `EXTRA FIELD 1-3`, `SANITY CHECK`) have no special meaning any more — they are just
  ordinary content columns if a sheet still has them. Existing decks need their headers
  renamed, and their notes are rebuilt on the next sync.
- **A sheet with no `SYNC` column now syncs every row.** It previously synced none,
  which produced an empty deck with nothing on screen explaining why.
- **No more `- Reverse` note type.** The reverse direction is a second card template on
  the same note type, so both directions are scheduled independently from one row of
  data, and switching it off removes its cards without touching the note.
- Tags are now `sheets2anki`, `sheets2anki::<subdeck path>` and whatever `TAGS` lists.
  The `[missing_*]` placeholder tags are gone.

### ✨ Card layout
- New **Configure Card Layout** dialog (`Ctrl+Shift+C`): choose which fields sit on the
  front and back, reorder them, toggle field labels, set font sizes and alignment, turn
  the reverse card and timer on or off, with a preview.
- The layout lives in **Anki's collection config**, so it travels between machines
  through AnkiWeb — no Google API, no extra setup. The AI provider API key deliberately
  stays machine-local in `meta.json`.
- "I'll edit the template myself" stops sync from regenerating the note type's
  templates, so hand edits in Anki's Cards editor finally survive a sync.

### 🐛 Fixes
- **Cloze note types were rejected by Anki.** A cloze template must reference
  `{{cloze:Field}}` on *both* sides — `{{FrontSide}}` does not satisfy the check — so
  provisioning one aborted the whole sync, including ordinary notes.
- Adding a column to the sheet now adds the field and shows it; **removing a column
  stops rendering it but never deletes the field**, so data is not destroyed by an
  edit to the header row.
- Dropped the deprecated `col.save()` calls; Anki persists collection changes itself.

---

## 💥 **v3.1.0** - August 2026 *(Breaking)*

The multi-student feature is gone, and the card is cut back to what a study card needs.

### 💥 Breaking
- **Multi-student removed.** The `STUDENTS` column is no longer read, and the
  `[MISSING_STUDENT]` sentinel no longer exists. Notes are keyed by the plain
  spreadsheet `ID` (and `{id}_REV` for the reverse variant) instead of the composite
  `{student}_{note_id}`; note types are `Sheets2Anki - {deck} - Basic|Cloze|Reverse`;
  and the deck hierarchy loses its student level. Existing collections re-key and
  re-file their notes on the next sync.
- **Empty hierarchy levels are skipped** in deck names rather than filled with
  `[MISSING_*]` placeholders — a sheet that only uses `TOPIC` now gets `Deck::Topic`
  instead of a chain of empty subdecks. The old placeholder subdecks are left behind
  empty and can be deleted by hand.
- **Removed**: `student_manager.py`, the global student config dialog, the data-removal
  confirmation dialog, the `Ctrl+Shift+G` shortcut, the `students` config block and the
  disabled-student cleanup subsystem.

### 🐛 Fixes
- **Sync returned 0 notes for any sheet without a `STUDENTS` column.** Such rows fell to
  `[MISSING_STUDENT]`, whose sync is gated on `sync_missing_students_notes` — a key
  `_ensure_meta_structure` never wrote into `meta.json`, so the reader's
  `.get(..., False)` default won and the sync bailed, while `config.json` advertised the
  default as `true`. Removing the feature removes the gate.

### 🎨 Card template
- Front is the timer and the question; back adds the answer plus whatever supporting
  fields the row actually filled (examples, mnemonic, complementary/detailed info,
  image, video), each conditional so an empty field leaves no trace.
- The `CONTEXT`, `INFORMATION` and `TAGS` headings rendered even when every field under
  them was empty, so they are gone, along with their "May be empty" subtitles, the
  exam-prep fields (`BOARDS`, `LAST YEAR IN EXAM`, `CAREERS`, `OTHER TAGS`), the three
  extra fields and the sanity check. Those columns still sync into the note — they are
  just no longer drawn on the card.

### 🤖 CI
- Pushing a `v*` tag now builds both `.ankiaddon` packages, validates them and attaches
  them to a GitHub release. The job refuses to build when the tag, `manifest.json` and
  `pyproject.toml` disagree on the version.

---

## 🔧 **v3.0.3** - June 2026 *(Maintenance)*

The last two audit follow-ups, done in parallel. No new features.

### 🐛 Fixes
- **Backup/restore thread-safety**: backup and restore now run synchronously on the main
  thread (behind Anki's progress indicator) instead of in a daemon thread. These operations
  call into `mw.col` (export/import `.apkg`, deck removal, `col.save`), and Anki's collection
  is not thread-safe, so the old threaded path risked database corruption.

### 🎨 UI deduplication (visual consistency)
- Action buttons (Save / Apply / Cancel, and Disconnect's destructive button) across 10
  dialogs now come from shared `theme.primary_button_qss` / `theme.secondary_button_qss`
  helpers instead of per-dialog hand-rolled QSS.
- Group-box styling reconciled: dialogs that overrode the shared `groupbox_qss` with their
  own near-identical block now inherit the canonical one via `base_dialog_qss`.

### 🧪 Tests
- `tests/test_backup_threading.py` asserts backup operations run on the caller (main) thread,
  not a worker — a regression guard against reintroducing the daemon-thread path.

---

## 🔧 **v3.0.2** - June 2026 *(Maintenance)*

Post-v3.0.1 audit follow-ups. No new features and no behavior changes for end users
(the UI work is visual-consistency only).

### 🐛 Fixes
- **Config defaults isolation**: `get_config()` / `get_meta()` now deep-copy the module
  defaults in their fallback/merge paths, so a caller mutating a nested dict can no longer
  corrupt `DEFAULT_CONFIG` / `DEFAULT_META` for the rest of the process.

### 🎨 UI deduplication
- The gradient **header banner** (all 11 dialogs) and the **radio option-card**
  (deck-options + timer) now come from shared `theme.make_header` /
  `theme.make_radio_option_card` factories — ~560 lines of duplicated dialog code removed,
  and the headers are now byte-consistent.
- Removed write-only per-dialog state (`is_dark_mode`, `current_step`, the dead `*_radio`
  attributes) and the orphaned comments left behind.

### 🧪 Tests
- New construction-smoke (`tests/test_ui_instantiate_smoke.py`) instantiates every dialog,
  catching `__init__`/setup errors the import-only smoke can't; plus regression tests for
  the config-defaults isolation.

---

## 🔧 **v3.0.1** - June 2026 *(Maintenance)*

Internal quality work, a full code audit, and a UI-consistency pass since v3.0.0. No new
features and no breaking changes; the UI updates are purely visual (colors and labels) and
the audit changes are bug fixes and cleanup.

### 🔍 Full code audit (bugs, dead code, deduplication)
A repository-wide audit fixed correctness bugs and removed accumulated cruft:

**Bug fixes**
- **Cloze content with colons**: `clean_cloze_formatting` now preserves colons inside the
  answer (e.g. `{{c1::10:30}}` → `10:30`) and strips hints case-insensitively; previously
  such reverse-card fronts could render raw `{{c1::…}}` markup.
- **Backup restore data-loss guard**: a "full" backup whose `.apkg` is missing/corrupt no
  longer deletes the live deck before discovering the deck file is absent.
- **Backup zip-slip**: backup archives are validated against path traversal before extraction.
- **Config persistence**: a deck whose only changed field was its local deck id is now
  written to `meta.json` (previously updated in memory but never saved).
- **Note-type naming**: a whitespace-only student no longer produces a `None` note-type name.
- **Sync robustness**: fixed an `UnboundLocalError` in the cleanup step, stopped
  double-counting a single failed deck as two errors, and corrected the deck name shown in
  "unexpected error" messages.
- Smaller fixes: the import-test-deck duplicate guard, add-deck reconnection prompt for
  disconnected URLs, HTTP error-body decoding, deterministic `student_selection` ordering,
  and the error-traceback dialog now honoring the real debug flag.

**Cleanup**
- Removed ~40 grep-verified unused functions/classes (~1500 lines) across the engine,
  config, deck, student, backup and UI layers, plus stale/misleading comments and leftover
  section banners from the earlier facade split.
- De-duplicated the SYNC-true value set, the two sync error handlers, and the dialogs' URL
  helpers (new `src/ui/url_helpers.py`).
- Pinned `black`/`ruff` in the dev environment to the exact CI versions so local formatting
  matches the gates; added regression tests for the cloze and note-type-name fixes.

### 🎨 UI design system (visual consistency)
A single design system now drives every screen, replacing per-dialog hardcoded styling:
- **New `src/theme.py`** — one source of truth for theme detection (`is_dark_mode()`, via
  Anki's `theme_manager.night_mode`) and a semantic light/dark color palette, plus
  reusable button/header style helpers.
- **All 12 config dialogs** migrated to the shared palette: hardcoded color sprawl dropped
  from ~75 hex values (mixing Material Design and Bootstrap) to **zero**; the three
  competing "primary" blues collapsed into one brand blue (`#4A90D9` / `#5BA3E0`); the
  four duplicate `is_dark_mode()` copies into one; every gradient header unified (they
  previously ranged across green / purple / red). ~330 lines of duplicated palette and
  detection code removed.
- **Card UI** (study timer, AI Help/Ask/Checker buttons, reverse-card badge) re-skinned
  from off-brand purple / neon-green to the same brand blue. CSS-only — the card JS is
  byte-identical (sha256-verified).
- **Button labels** unified ("Save Settings" / "Save Configuration" → "Save").
- **Emoji standardized** — removed decorative emoji from buttons and section headers
  (keeping semantic status icons ⚠️✅❌ℹ️, language flags, and ✓/✗/←/→ affordances) for a
  more professional tone; card icons (timer, reverse badge, AI buttons) were left as-is.
- Regression guards added (`tests/test_theme.py`, `tests/test_ui_import_smoke.py`): they
  lock the palette values, assert every dialog color key resolves, and import every dialog.

### 🗂️ Project reorganization
- **`src/ui/` subpackage**: the Qt dialog modules were grouped under `src/ui/`.
- **God-file splits with back-compat facades**: `utils.py` → `errors.py` / `debug.py` /
  `deck_options.py`; `sync.py` → `sync_report.py`; `config_manager.py` → `ai_prompts.py`;
  `templates_and_definitions.py` → `card_assets.py`. The original modules re-export the
  moved names, so existing imports keep working.

### ⚙️ Tooling & CI
- **GitHub Actions CI**: a test job plus a lint job with **blocking** `ruff` and `black`
  gates (pinned versions) and an advisory `mypy` pass. Undefined-name errors (`F821`) are
  caught as part of the standard `ruff check` (the `F` rule family is enabled).
- **Pre-commit hooks** (`.pre-commit-config.yaml`): ruff + black + hygiene hooks
  (`libs/` excluded).
- **`CONTRIBUTING.md`** added; non-test JS/HTML harnesses moved to `tools/js-harnesses/`.

### 🐛 Fixes
- **Sync-summary crash**: `sync_report.py` referenced `DEFAULT_STUDENT` without importing
  it, raising `NameError` when the post-sync summary dialog rendered. Fixed, and now
  caught by the `ruff check` gate (`F` rules).

### 🎨 Code style & docs
- Repository-wide formatting pass (ruff auto-fixes + black), now enforced in CI.
- README rewritten in a professional tone; the developer guide (`docs/README.md`), test
  guide (`tests/README.md`), and script docs refreshed to match the current structure;
  the obsolete image-CLI docs were removed.

---

## 🚀 **v3.0.0** - January 2026 *(BREAKING CHANGES)*

### ⚠️ **Breaking Changes**
- **Python 3.13 Required**: Minimum Python version upgraded from 3.9 to 3.13
- **Anki 25.x Required**: Add-on now requires Anki version 25.x or newer
- **Qt6 Only**: Removed all Qt5 compatibility code
- **No Backward Compatibility**: Users on older Anki versions must update or use v2.x

### 🔒 **Security & Correctness Hardening (Audit)**

A full security/correctness audit was completed and all findings fixed:

**Critical**
- **Empty-sheet guard**: a sync that parses zero valid rows (e.g. a transient failed
  download) no longer runs the deletion pass, so it cannot wipe a deck.
- **Underscore-safe keys**: note/student/deck matching now uses suffix-aware logic, so an
  underscore in a student name can't corrupt the composite `{student}_{note_id}` key.

**High**
- **Non-destructive note-type changes**: switching a note's type creates the replacement
  before deleting the original, so a failure cannot lose the note.
- **Duplicate spreadsheet IDs** are detected and reported instead of silently colliding.
- **AI output sanitized**: HTML returned by AI providers is escaped/sanitized before it is
  injected into the card webview.
- **Test suite rebuilt** against the real `src` modules (with Anki mocked), replacing the
  previous self-mocking tests.

**Medium / Low**
- **TSV parsing hardened**: BOM handling (`utf-8-sig`), quoted-field parsing, whitespace
  trimming.
- **`marked.js` served locally** (with Subresource Integrity) instead of from a CDN.
- **Bare `except:` clauses** replaced with scoped handlers.
- **SSRF host check**: downloads are restricted to Google hosts; ImgBB uploads forced to
  HTTPS.
- **Card-template JS de-duplicated** into shared single-source constants.
- Version and pytest configuration unified; dead files and a tracked `.pyc` removed.

### 🎯 **Major Simplification**

#### 🔧 **Compatibility Module Rewrite** (`src/compat.py`)
- **Before**: 513 lines with complex version detection
- **After**: 265 lines with clean Qt6-only code
- **Removed**: ~250 lines of backward compatibility code
- **Result**: Simpler, more maintainable codebase

#### 🗑️ **Removed Code**
- ❌ All Qt5/Qt6 version detection logic
- ❌ All Anki version detection (23.x, 24.x checks)
- ❌ `get_anki_version()` function
- ❌ `ANKI_VERSION`, `IS_ANKI_25_PLUS`, `IS_ANKI_24_PLUS` constants
- ❌ `QT_VERSION` detection
- ❌ Conditional imports with `hasattr()` checks
- ❌ `exec_()` fallback methods for Qt5

#### ✨ **Modernization**
- ✅ Direct Qt6 imports only
- ✅ All constants use Qt6 enum syntax (e.g., `Qt.AlignmentFlag.AlignCenter`)
- ✅ Clean `exec()` method calls
- ✅ Simplified utility functions
- ✅ Python 3.13 features available

### 📝 **Configuration Updates**

#### **Development Tools**
- **Black**: Target version updated to `py313` only
- **Ruff**: Target version updated to `py313`
- **Mypy**: Python version set to `3.13`
- **Pyright**: Python version set to `3.13`

#### **Project Files**
- **pyproject.toml**: `requires-python = ">=3.13"`
- **Classifiers**: Removed Python 3.9-3.12, kept only 3.13
- **.python-version**: Updated to `3.13`

### 📚 **Documentation Updates**
- **README.md**: Added system requirements section
- **docs/README.md**: Removed all Anki 2.1.x references
- **Development Guide**: Updated prerequisites to Python 3.13+
- **Code Examples**: Updated to reflect Qt6-only usage

### 🎁 **Benefits**
- **Performance**: Python 3.13 performance improvements
- **Simplicity**: 250+ lines of complexity removed
- **Modern**: Using latest Python and Qt6 features
- **Maintainability**: Single code path, no version conditionals
- **Future-proof**: Ready for upcoming Anki versions
- **Easier Debugging**: No more version-specific bugs

### 📦 **Dependencies**
- **Anki**: 25.7.5+
- **PyQt6**: 6.9.1+
- **Python**: 3.13.5+

### 🔄 **Migration Guide**
Users upgrading from v2.x should:
1. Update to Anki 25.x or newer
2. Install the new add-on version
3. Existing decks and configurations will work without changes
4. No manual migration needed

---

## 🚀 **v2.3.0** - January 2026



### ✨ **New Features**
- **Debug Mode UI**: Dedicated interface (`Ctrl+Shift+L`) to manage debug mode, view logs, and reset configurations.
- **Sync Cancellation**: Added "CANCEL SYNC" button in data removal warning dialogs to prevent accidental data loss.

### 🎨 **UI/UX Improvements**
- **Modernized Configuration Dialogs**: Global Student, Deck Options, and AnkiWeb Sync dialogs updated with gradient headers, improved styling, and full dark mode support.
- **Localization**: Standardized column names to Portuguese (`PERGUNTA`, `ALUNOS`, `LEVAR PARA PROVA`) in documentation and sample data.
- **Sample Data**: Translated `sample_sheet.tsv` content to English while maintaining Portuguese column headers.

### 🔧 **Fixes & Optimization**
- **AnkiWeb Timeout**: Fixed persistence issue where timeout settings were not being saved.
- **Documentation**: Updated README to reflect support for 23 columns.
- **Code Cleanup**: Removed dead code directories (`config_pkg`, `sync_pkg`, `utils_pkg`) and consolidated imports.

---

## 🚀 **v2.2.0** - August 2025

### ✨ **Revolutionary URL System Simplification**

#### 🎯 **Unified URLs**
- **ONLY Edit URLs**: Simplified system works exclusively with edit URLs (`/edit?usp=sharing`)
- **Elimination of Published Format**: Completely removed support for published URLs (`/pub?output=tsv`)
- **Automatic Conversion**: Edit URLs are automatically converted to TSV download format
- **Simplified Process**: A single URL type for all use cases

#### 🆔 **Real ID Identification System**
- **Spreadsheet ID**: Uses the actual Google Sheets spreadsheet ID as identifier
- **End of Hashes**: Completely eliminates the MD5 hash system for identification
- **Clearer Configuration**: `meta.json` now uses real spreadsheet IDs as keys
- **Total Transparency**: Users can see exactly which spreadsheet is configured

#### 🔧 **Complete API Refactoring**
- **New Functions**:
  - `extract_spreadsheet_id_from_url()`: Extracts spreadsheet ID from edit URLs
  - `get_spreadsheet_id_from_url()`: Gets ID with validation
  - `convert_edit_url_to_tsv()`: Converts edit URL to TSV
- **Removed Functions**:
  - `extract_publication_key_from_url()`: ❌ Removed
  - `get_publication_key_hash()`: ❌ Removed
  - `convert_google_sheets_url_to_tsv()`: ❌ Removed

### 🗂️ **Automatic Configuration Migration**
- **Compatibility**: Existing configurations continue working
- **Transparent Migration**: System automatically detects and migrates old configurations
- **Data Preservation**: All decks and preferences are maintained
- **No Intervention**: Completely automatic process for the user

### 🧪 **New Test Suite**
- **Specific Tests**: 18 new tests for simplified functionalities
- **Complete Coverage**: Validation of all new functions
- **Error Tests**: Robust validation of error cases
- **Dedicated File**: `test_url_simplification.py` for new functionality tests

---

## 🚀 **v2.1.0** - August 2025

### ✨ **New Features**

#### 💾 **Advanced Backup System**
- **Automatic Configuration Backup**: Automatic backup on each synchronization with file rotation (keeps only the 50 most recent)
- **Configuration-Only Backup**: New backup mode that preserves only addon settings, ideal for reinstallation
- **3-Column Interface**: Side-by-side layout for full backup, recovery and automatic settings
- **Flexible Configuration**: Customizable directory for automatic backups
- **Sync Integration**: Automatic trigger after each successful synchronization

#### 🔧 **Automatic Name Consistency System**
- **Automatic Correction**: Automatically detects and corrects inconsistencies in note type names
- **Intelligent Synchronization**: Checks name alignment during each synchronization
- **Transparent Update**: Corrects differences between remote and local names without manual intervention
- **Data Preservation**: Maintains study history and settings during corrections
- **Standardized Names**: Implements consistent standards for decks, note types and configurations

#### 📊 **Enhanced Sync Summary**
- **Dual Visualization**: "Simplified" and "Complete" modes for different needs
- **Optimized Order**: In "Complete" mode, aggregated general summary appears first
- **Detailed Metrics**: Complete spreadsheet statistics and results per deck
- **Responsive Interface**: Automatic support for dark mode and adaptive layout

#### 🖼️ **Multimedia Field Support**
- **Media Fields**: "IMAGE HTML" for images/illustrations and "VIDEO HTML" for embedded videos
- **Automatic Template Update**: Automatically adds fields to existing note types
- **Intelligent Positioning**: Media appears on the back of the card for better pedagogy
- **Safe Templates**: Doesn't duplicate fields and preserves existing data

### 🔄 **Improvements and Optimizations**

#### 🌐 **Complete Google Sheets URL Support**
- **Edit URLs**: Native support for `/edit?usp=sharing` URLs
- **Automatic Conversion**: Automatically converts edit URLs to TSV format
- **GID Auto-discovery**: Automatically detects the correct spreadsheet gid
- **Backward Compatibility**: Maintains compatibility with published TSV URLs
- **Bug Fix**: Eliminates HTTP 400 "Bad Request" error with edit URLs

#### 👥 **Advanced Student Management**
- **Global Configuration**: Define once which students to sync across all decks
- **Personalized Subdecks**: Each student has their own organized hierarchy
- **Unique Note Types**: Personalized card templates for each student
- **Intelligent Filtering**: Syncs only the chosen students

#### 🏷️ **Complete Hierarchical Tag System**
- **8 Categories**: Students, Topics, Exam Boards, Years, Careers, Importance, Extra Tags
- **Hierarchical Structure**: Automatic organization in levels (`Sheets2Anki::Category::Item`)
- **Custom Tags**: Support for additional custom tags

### 🐛 **Bug Fixes**
- **HTTP 400 with Edit URLs**: Resolved through GID auto-discovery
- **Name Inconsistency**: Automatically corrected by consistency system
- **Count Calculation**: Fixed to use notes instead of questions
- **Empty Subdecks**: Automatic removal after synchronization
- **Error Reports**: Updated link to correct GitHub repository

### 🧪 **Testing and Quality**
- **Comprehensive Test Suite**: Tests for backup, dialog, name consistency
- **Complete Coverage**: 100% of new features tested
- **Integration Tests**: End-to-end functionality validation
- **Compatibility Tests**: Verification with PyQt5/PyQt6

---

## 🏗️ **v2.0.0** - July 2025

### ✨ **Main Features**
- **Selective Synchronization**: `SYNC` column for individual card control
- **Basic Backup System**: Manual backup and deck restoration
- **AnkiWeb Synchronization**: Automatic after updates
- **Cloze Card Support**: Automatic detection of `{{c1::text}}` patterns
- **Personalized Note Types**: One for each student automatically

### 🔧 **Base Architecture**
- **19 Required Columns**: Standardized structure for spreadsheets
- **TSV Processing**: Robust engine for Google Sheets data
- **Configuration Management**: `meta.json` system for persistence
- **Qt Interface**: Modern dialogs for configuration and status

---

## 📋 **v1.1.0** - June 2025

### ✨ **Basic Features**
- **Google Sheets Synchronization**: Direct connection with TSV spreadsheets
- **Automatic Deck Creation**: Based on spreadsheet data
- **Basic Note Types**: Support for basic and cloze cards
- **Simple Tags**: Basic categorization system

### 🔧 **Infrastructure**
- **Anki Add-on**: Native integration with Anki 2.1+
- **Data Processing**: Basic TSV engine
- **Simple Interface**: Basic configuration dialogs

---

## 📊 **Project Snapshot**

- **Compatibility**: Anki 25.x+ only (Qt6 / PyQt6)
- **Python**: 3.13
- **Platforms**: Windows, macOS, Linux
- **Quality gates**: `ruff` + `black` enforced in CI; the test suite runs against the
  real `src` modules with Anki mocked. Coverage is opt-in
  (`python tests/run_tests.py --coverage`).

---

## 📚 **Related Documentation**

- [`README.md`](../README.md) — end-user install & usage guide
- [`docs/README.md`](README.md) — long-form developer guide
- [`CLAUDE.md`](../CLAUDE.md) — concise architecture & conventions reference
- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — setup & contribution workflow
- [`tests/README.md`](../tests/README.md) — test-suite guide
- [`scripts/README.md`](../scripts/README.md) — build & packaging

---

## 🤝 **Contributions**

### 👥 **Core Team**
- **Igor Florentino** - Lead Developer and Maintainer
- **Email**: igorlopesc@gmail.com
- **GitHub**: [@igorrflorentino](https://github.com/igorrflorentino)

### 🐛 **Report Bugs**
- **Issues**: [GitHub Issues](https://github.com/igorrflorentino/sheets2anki/issues)
- **Discussions**: [GitHub Discussions](https://github.com/igorrflorentino/sheets2anki/discussions)

### 🌟 **Acknowledgments**
- Anki community for the robust platform
- Users who provided valuable feedback
- Code and documentation contributors

---

## 📄 **License**

This project is licensed under the **MIT License** - see the [`LICENSE`](../LICENSE) file for details.

---

## 🔗 **Useful Links**

- **🏠 Repository**: [github.com/igorrflorentino/sheets2anki](https://github.com/igorrflorentino/sheets2anki)
- **🐛 Issues**: [GitHub Issues](https://github.com/igorrflorentino/sheets2anki/issues)
- **📖 Documentation**: [`README.md`](../README.md) · [`docs/README.md`](README.md) · [`CONTRIBUTING.md`](../CONTRIBUTING.md)

---

*Last updated: June 2026*
