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
- [Configuration: where settings live](#configuration-where-settings-live)
- [Development setup](#development-setup)
- [Testing](#testing)
- [Building & packaging](#building--packaging)
- [Debugging](#debugging)
- [Conventions](#conventions)

## What this is

Sheets2Anki is an **Anki add-on**, not a standalone application. The repository root
*is* the add-on directory: Anki loads `__init__.py` from the root, which registers a
`Tools → Sheets2Anki` menu and binds keyboard shortcuts. There is no server and no
`main()` — all code runs inside Anki's Python/Qt6 process.

The architecture is **function-oriented**, organized around a handful of cohesive
modules plus a few small types (`RemoteDeck`, `DebugManager`). It is *not* a class-based
MVC framework; sync is driven by module-level functions such as `syncDecks()` and
`create_or_update_notes()`.

## System architecture

Three layers, from the outside in:

```
┌────────────────────────────────────────────────────────────────────────┐
│  Anki integration  (__init__.py)                                       │
│  • Tools → Sheets2Anki menu     • 9 keyboard shortcuts (Ctrl+Shift+…)  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│  Add-on logic  (src/)                                                  │
│  • sync engine / data processing  • configuration management           │
│  • dialogs (src/ui/)              • AnkiWeb auto-sync                  │
│  • compat.py — the single Qt/Anki gateway                              │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│  Python stdlib + whatever Anki already provides                        │
│  • no vendored code  • no runtime third-party dependencies             │
└────────────────────────────────────────────────────────────────────────┘
```

The nine user-facing shortcuts are `Ctrl+Shift+` `A S D O W C P B L`; `Ctrl+Shift+T`
("Import Test Deck") is bound only while `IS_DEVELOPMENT_MODE` is `True` and never ships.

**No runtime third-party dependencies.** The add-on imports nothing but the standard
library and the modules Anki itself exposes. The old vendored `libs/` tree
(`beautifulsoup4` + `soupsieve`, `chardet`, `org_to_anki`) and the `sys.path` bootstrap
that loaded it were deleted — do not reintroduce vendoring or add a runtime dependency.
Dev/test tooling is separate and lives in `[project.optional-dependencies] dev`.

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
├── __init__.py                 # Anki entry point: menu and shortcuts
├── config.json                 # Default settings (committed)
├── manifest.json               # Add-on metadata (version lives here + pyproject.toml)
├── meta.json                   # User settings + connected decks (gitignored; runtime)
├── src/                        # All add-on logic (see module map below)
│   └── ui/                     # Qt dialogs (9 modules + url_helpers.py)
├── tests/                      # pytest suite (Anki is mocked; no Anki install needed)
├── scripts/                    # Build/packaging tooling for .ankiaddon files
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
- **`sheet_config.py`** — the optional **settings row**: `is_config_row()` recognises it,
  `parse_config_row()` turns it into a `SheetConfig` (`FieldConfig` per column, the
  deck-wide `align`/`speed`/`reverse`, and `warnings`). Also `normalize_tts_language()`
  and the validation tables (`SIDES`, `ALIGNMENTS`, `THEME_COLORS`, `MEDIA_KINDS`, the CSS
  colour names).
- **`deck_manager.py`** — deck CRUD and the selection entry point
  (`syncDecksWithSelection()`).
- **`name_consistency_manager.py`** — keeps dynamically-created note-type names in sync
  when a deck is renamed.

### Configuration & utilities
- **`config_manager.py`** — the only module that reads/writes `meta.json`/`config.json`
  (`get_meta()` / `save_meta()`).
- **`sync_config.py`** — the **cache** of what the last sync parsed out of each sheet's
  settings row, stored in Anki's own collection config so it follows the user between
  machines (`cache_sheet_settings()`, `cached_plan_and_config()`, `get_cached_settings()`,
  `forget_sheet_settings()`, `to_dict()` / `from_dict()`). Nothing here is editable — the
  spreadsheet is the source of truth and every sync overwrites the entry.
- **`card_layout.py`** — turns a `ColumnPlan` plus a `SheetConfig` into Anki card
  templates (`split_sides()`, `build_templates()`), including the per-field styling, the
  `hint:`/`furigana:`/`cloze:` references, the `<img>`/`<audio>`/`<video>` wrappers for
  media columns (`_MEDIA_ELEMENTS`), the TTS tags and the optional reverse template.
- **`utils.py`** — URL conversion (`convert_edit_url_to_tsv()`,
  `get_spreadsheet_id_from_url()`), note-type naming (`get_note_type_name()`), subdeck
  naming (`get_subdeck_name()`), and other helpers; errors/debug/deck-options were split
  into **`errors.py`**, **`debug.py`**, **`deck_options.py`**.
- **`templates_and_definitions.py`** — note-type provisioning against the sheet's columns
  and its settings row (`ensure_custom_models()`, `create_model()`,
  `add_missing_fields()`, `apply_templates()`, `update_existing_note_type_templates()`),
  plus `IS_DEVELOPMENT_MODE` and `TAG_ROOT`.

### Features & integrations
- **`ankiweb_sync.py`** — optional AnkiWeb auto-sync after changes.
- **`compat.py`**, **`styled_messages.py`** — the Qt/Anki gateway and styled dialogs.

### UI (`src/ui/`)
Seven Qt dialogs — add deck, sync, disconnect, debug, deck-options config, AnkiWeb
config and **card-layout config** — plus `url_helpers.py` (shared clean-URL /
copy-to-clipboard helpers), one dialog per menu entry.
Modules in `src/ui/` import siblings one level up (`from ..compat import …`).

**`card_layout_dialog.py`** is a **read-only viewer** of a deck's card layout: the sides
the settings row produced, each column's parsed directives, the warnings the parse
collected, the TTS voices installed on this machine, and a preview. It never writes a
setting — the spreadsheet is the only place they are edited (see
[Card layout](#card-layout) for why) — and it never writes HTML; that is
`card_layout.build_templates()`' job. Its live preview only *approximates* Anki's
template syntax in a `QTextBrowser` (every section is taken, `<script>` blocks are
stripped, since the widget runs no JavaScript). Its own `_FIELD_KEYS` tuple is a second,
hand-maintained copy of the per-column key list and **does not yet include `media`**, so
the settings panel shows nothing for an `image`/`audio`/`video` column even though the
preview renders the element.

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
3. **Read the settings row.** If the row under the header is one
   (`sheet_config.is_config_row()`), `parse_config_row()` turns it into a `SheetConfig`
   carried as `RemoteDeck.sheet_config`, and the row is **dropped from `rows` before any
   counting happens** — it is a directive row, so it must never reach `add_note()` or
   appear in a metric. Its warnings go to the debug log under `SHEET_CONFIG`.
4. **Provision the note types.** `templates_and_definitions.ensure_custom_models()` makes
   the Basic and Cloze note types match `plan` (fields) and `sheet_config` (templates),
   and `data_processor.cache_deck_sheet_config()` records the parse for later rebuilds.
5. **Apply changes.** `data_processor.create_or_update_notes()` creates, updates, and
   deletes Anki notes to match the sheet. (Steps 4 and 5 are one call: the caching and
   `ensure_custom_models()` run at the top of `create_or_update_notes()`.)

> **Safety guard:** if a parsed sheet has `valid_note_lines == 0` (e.g. an empty or
> failed fetch), the deletion pass is skipped so a transient blank download can't wipe
> a deck.

## Column model & note keying

There is **no fixed column list**. The spreadsheet drives the schema: a handful of
headers are reserved, and every other column becomes a note field named exactly like the
header — so a sheet can use whatever vocabulary its subject calls for ("Word",
"Reading", "Meaning") instead of a column list baked into the code. Headers may be in any
language or script, since the header text becomes the field name verbatim. This all lives
in `column_model.py`.

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
  `SUBDECK` columns keeps every note in the deck root. A row that fills in **no** level,
  on a sheet that does sort its rows, lands in `column_model.UNSORTED_DECK` (`Unsorted`) —
  see below.
- **Tags** (`data_processor.build_tags()`): `sheets2anki` on every note the add-on owns,
  `sheets2anki::<subdeck path>` mirroring the deck path, plus whatever the `TAGS` column
  lists. Each component is folded to a safe lower-case tag by `clean_tag_text()`.

### The settings row (`src/sheet_config.py`)

Row 1 names the columns. **Row 2 is the settings row when its `ID` cell is `#config` or
starts with `#config ` — otherwise it is an ordinary data row.** `is_config_row()` tests
the *leading token*, lower-cased, because the deck-wide settings ride along in the same
cell (`#config align=left; reverse`); the marker only needs a non-alphanumeric
separator after it, so `#config;align=left` also counts, while `#configuration` does
**not** match and that line is imported as a note.

That marker is the whole backward-compatibility story: a sheet written before this
feature has no `#config` cell, so nothing changes for it.

`parse_config_row(row, plan)` reads the row into a `SheetConfig`:

| Attribute | Contents |
| :--- | :--- |
| `present` | True when a settings row was found |
| `fields` | `{header: FieldConfig}` — only for columns whose cell was non-empty |
| `align`, `speed`, `reverse`, `theme` | the deck-wide settings from the `#config` cell |
| `warnings` | every directive the parser did not understand, each naming its column |

Each cell is `key=value` pairs split on `;`; a bare key is a flag. Only
`plan.content_headers` (plus the ID cell) are read, so a directive typed into `SYNC`,
`TAGS` or a `SUBDECK n` cell is ignored. An empty cell means "defaults", and no
`FieldConfig` is stored for it — `SheetConfig.for_field()` hands back a blank one.

**Per-column keys** (`_FIELD_KEYS`), each landing on a `FieldConfig` attribute:

| Key | Accepted | Validation |
| :--- | :--- | :--- |
| `side` | `front`, `back`, `hide` | `SIDES`; `hide` sets the `hidden` property |
| `label` | any text | none — used as the caption above the value |
| `size` | integer px (a `px` suffix is stripped, floats truncated) | **6–200**, else a warning and no value |
| `color` | `muted`/`accent` (→ `var(--s2a-muted)` / `var(--s2a-accent)`), a **real** CSS colour name, or `#rgb`/`#rrggbb` | validated against `_CSS_COLOR_NAMES`, not a loose `[a-z]+` rule, so `grey1` is caught |
| `align` | `left`, `center`, `right` | `ALIGNMENTS` |
| `tts` | a full language code | `_LANG_RE` = `^[a-zA-Z]{2,3}[-_][a-zA-Z0-9]{2,4}$`, normalised to `zh_CN` shape |
| `voices` | comma-separated names | at least one non-empty name |
| `speed` | float | **0.5–2.0** |
| `font` | a key of `FONTS` (`sc`/`tc`/`jp`/`kr`/`serif`/`sans`/`mono`) or any family name | a known key becomes its stack and its webfont is imported; anything else is passed to CSS as written |
| `math` | bare, or `math=block` | `\(…\)` inline, `\[…\]` display — drawn by the MathJax Anki ships, so no library is loaded |
| `code` | bare, or `code=python` | `<pre class="s2a-code"><code class="language-…">{{text:F}}</code></pre>`, coloured by `HIGHLIGHT_JS` |
| `bold`, `italic`, `hint`, `furigana`, `rtl`, `vertical`, `sort` | flags | set to True by their mere presence |
| `image`, `audio`, `video` (`MEDIA_KINDS`) | flags | all three land on the single `media` attribute (`"image"`/`"audio"`/`"video"`), not on three independent switches — one column holds one kind. A second, different kind is ignored with a warning |

**Media columns** turn a cell that holds nothing but a URL into the element that plays it
(`card_layout._MEDIA_ELEMENTS`), and they make two checks *post-parse*, in
`parse_config_row()` rather than in `_apply_field_pair()`:

- **`size` is range-checked once the whole cell is known.** It means a font size on a text
  column (**6–200**) and a max width on a media one (**1–2000**), and the deciding key may
  be written after it — so the check has to wait until the cell is fully parsed, which is
  what makes `size=480; video` behave identically to `video; size=480`. Out of range, it
  warns naming `font size` or `width` and drops the value rather than clamping it.
- **`tts` and `furigana` are stripped from a media column**, both with a warning: they
  would act on the address itself (speech would read the URL out loud). `hint` survives
  the parse.

**Three of the per-column keys are not about how the card looks.**

- **`sort`** names the column Anki lists notes under in the browser and sorts a deck
  by. It is stored on the note type as an index into the field list
  (`templates_and_definitions.apply_sort_field`), and the default is field 0 — which
  is `ID`, so without it a deck lists as `w01`, `w02`, `w03`. One column per sheet,
  resolved in `resolve_roles` beside `cloze_field` and `type_field`; refused on a
  media column, and — unlike every *card* key — allowed on a `subdeck` column, since
  filing a note and listing it are both properties of the note.
- **`rtl`** and **`vertical`** are the two writing directions HTML has: `direction:
  rtl` for Arabic, Hebrew and Persian (which also right-aligns unless `align` says
  otherwise), and `writing-mode: vertical-rl` for classical Japanese and Chinese. A
  column has one direction, so asking for both keeps `rtl` and warns.
- **`font`** exists because of Han unification: `直`, `骨` and a few hundred others
  are one code point drawn differently in Chinese and Japanese, and a machine with a
  single CJK font picks for you. `sc`/`tc`/`jp`/`kr` import a Noto face from
  `FONT_CSS`; the imports are emitted by `_font_imports()` at the **top** of the
  stylesheet, because `@import` is only legal there.

**Deck-wide keys** (`_DECK_KEYS`), parsed out of the remainder of the `#config` cell:
`align` (validated), `speed` (parsed as a float but **not** range-checked, unlike the
per-column one), `theme` (a key of `THEMES`), and the `reverse` flag.

**The unsorted pile has no directive.** A row that fills in no level of the path at all —
neither a `SUBDECK n` column nor a `subdeck=n` one — lands in `column_model.UNSORTED_DECK`,
which is `Unsorted`. It is applied in `deck_path()` as the single level of an otherwise
empty path, so the deck **and** the mirrored tag both follow from one place. Three things
are deliberate:

- **It only applies to a sheet that sorts.** With no deck levels at all there is nothing to
  be unsorted from, so a two-column vocabulary sheet keeps every note in the deck itself
  rather than gaining a folder wrapped around all of it.
- **A row that fills in *some* level is not unsorted** — a blank outer level with a deeper
  one filled in still names a deck.
- **The name is fixed and English.** It shipped for one version as `#config unsorted=<name>`
  and the key was removed again: a sheet that sorts its rows is already saying a row belongs
  somewhere, so the row that names none has an answer either way, and a key to switch that
  on would only ever have been a key to leave those rows loose among the folders.

Two design points worth keeping:

- **A flag is only ever turned on.** `_apply_field_pair()` sets the attribute True as soon
  `false`/`no`/`0`/`off`/`none` as an explicit off, so `bold=false` means no bold.
- **Nothing is guessed and nothing is silently dropped.** An unknown key, a bad value or a
  number outside its range appends to `warnings` and is refused rather than clamped. The
  warnings reach the debug log (`SHEET_CONFIG`) during the sync and the card-layout dialog
  through the cache.

### Text-to-speech, and why the language code must be complete

Anki's tag is `{{tts LANG [voices=A,B] [speed=N]:Field}}` and it picks a voice by
comparing the language strings **exactly** (`aqt/tts.py`: `if avail.lang == tag.lang`),
against voice languages that are always the full `language_REGION` form. A bare `zh`
therefore matches no voice and plays **silence**, which is why `_LANG_RE` rejects short
codes with a warning instead of guessing a region — guessing `zh_CN` for someone studying
Traditional Chinese would be wrong *and* inaudible. `normalize_tts_language()` only
touches the separator and the casing, which cannot change which voice is selected.

Three consequences to keep in mind when touching this code or its docs:

- **`voices` is a preference, not a requirement.** Anki falls back to any voice for the
  language, so naming voices stays portable across machines.
- **A missing system voice is silent, not an error.** No Chinese voice installed means
  `tts=zh_CN` plays nothing, with nothing to diagnose from — which is why the dialog lists
  the voices installed on the machine.
- **One cell, one language.** Anki reads the entire field with one voice, so a cell
  holding a sentence and its translation is read end to end by that column's voice.

## Card layout

**How a card looks is a property of the sheet, not of the deck.** There is no editable
layout record: `card_layout.build_templates(plan, sheet_config, is_cloze)` renders the
`ColumnPlan` and the parsed settings row straight into the
`{"name", "qfmt", "afmt"}` template list.

- **`split_sides(plan, sheet_config)`** decides the sides. The default is the sheet's own
  order — first content column is the prompt, the rest are the answer, the same convention
  as Anki's CSV import — so reordering columns reorders the card with no settings at all.
  `side=` overrides it per column and `side=hide` drops the column from both sides. A
  layout that ends up with an empty front promotes the first still-visible back field,
  since Anki refuses to generate a card from a blank prompt.
- **Per-field rendering.** `_inline_style()` emits `size`/`color`/`bold`/`italic`/`align`
  as one `style` attribute; `_reference()` picks the plain `{{Field}}`, `{{hint:Field}}`
  or `{{furigana:Field}}`; `_tts_tag()` emits the TTS tag, with a field-level `speed`
  outranking the deck-wide one. Both the field's `<div>` and its TTS tag are wrapped in
  `{{#Field}}…{{/Field}}`, so an empty cell renders nothing *and* speaks nothing.
- **A `furigana` column is spoken through `kana:`** — `{{tts ja_JP:kana:Field}}`, not
  `{{tts ja_JP:Field}}`. Anki hands the voice the field's *text*, and the text of a
  furigana cell is `日本語[にほんご]`, so the plain tag has the voice say the word,
  then the bracket, then the word again. Checked against a real collection:

  | template | what the voice is given |
  | :--- | :--- |
  | `{{tts ja_JP:Word}}` | `私[わたし]は 日本語[にほんご]` |
  | `{{tts ja_JP:kana:Word}}` | `わたしはにほんご` |
  | `{{tts ja_JP:kanji:Word}}` | `私は日本語` |

  `kana:` rather than `kanji:` because the sheet wrote the reading down on purpose:
  making the engine guess it again is what furigana exists to prevent, and it guesses
  wrong on exactly the names and rare readings someone bothered to annotate. A cell
  with no brackets passes through unchanged, so a half-annotated column still works.
- **Media fields take a different branch.** When `cfg.media` is set, `_rows()` skips
  `_inline_style()` and `_reference()` entirely and calls `_media_html()`, which formats
  `_MEDIA_ELEMENTS[cfg.media]` around `{{Field}}` — `<img src="{{F}}"…>`,
  `<audio src="{{F}}" controls>`, `<video src="{{F}}" controls…>`. `controls` is
  unconditional (unreplayable audio is worse than none), `size` becomes
  `style="max-width: Npx"` on image and video (the audio element has no `{style}` slot, so
  a `size` there parses and then does nothing), and `color`/`bold`/`italic`/the per-column
  `align` are silently dropped. The URL is never string-joined here: it reaches the `src`
  through Anki's own field substitution.
  **Known gap:** the `cfg.hint` branch inside that path only re-wraps the element in a
  second `{{#Field}}…{{/Field}}` guard — identical to the one `_rows()` already emits — so
  `hint` on a media column is a no-op with no warning, and
  `test_hint_still_hides_media_behind_a_link` passes on an assertion the outer guard
  already satisfies. Real click-to-reveal would need markup of its own; `{{hint:Field}}`
  would only reveal the URL as text.
- **The theme colours are CSS custom properties.** `_css()` declares `--s2a-muted` and
  `--s2a-accent` twice — once as the light default and once under `.night_mode`, the class
  Anki puts on the card body in dark mode. A single fixed value would make one of the two
  themes unreadable, which is the entire reason the named colours exist.
- **Cloze.** `cloze:` outranks `hint`/`furigana` in `_reference()`, and the cloze back
  repeats the prompt through `{{cloze:Field}}` rather than `{{FrontSide}}`, because
  **Anki validates that a cloze template references the field through that filter on both
  sides** and refuses to save the note type otherwise. Cloze note types also support
  exactly one template, so the reverse card is skipped for them.
- **Media is referenced, not imported.** The three media kinds emit a remote `src`; nothing
  is ever downloaded into `collection.media`. That is the opposite of Anki's own model
  (collection media syncs and works offline), so the cards need a live connection and
  mobile clients apply stricter rules to remote content — a trade worth restating in any
  user-facing text rather than burying. It also bounds what the feature can do: `<video>`
  plays a media file, so a YouTube *page* URL needs an `<iframe>`, which users can paste
  into the cell directly since field HTML renders as-is.
- **Reverse cards are a second template on the same note type** (`"Card 2 (reverse)"`),
  not a second note. Anki schedules both directions independently off one row, and
  removing `reverse` from the sheet later removes those cards without touching the note's
  content (`apply_templates()` prunes templates the settings no longer produce).

`sync_config.py` **caches** the `(plan, sheet_config)` pair each sync parsed, under
`sheets2anki::sheet_settings`. That is what lets
`templates_and_definitions.update_existing_note_type_templates()` rebuild a deck's
templates outside a sync, and what the dialog reads. A cached entry with no
`content_headers` deliberately yields `(None, None)`: rendering from it would produce a
card with no fields on it.

`src/ui/card_layout_dialog.py` (`Tools → Sheets2Anki → Configure Card Layout`,
`Ctrl+Shift+C`) is a **read-only** view of that cache. Do not add editing controls to it:
with two places able to change one setting, the loser is silently overwritten on the next
sync, and a control that "does nothing" is close to undiagnosable. Settings are changed by
editing the sheet and re-syncing.

## Configuration: where settings live

Settings are split by whether they should follow the user to their other machines.

- **`config.json`** (committed) — default settings only.
- **`meta.json`** (gitignored, auto-created by Anki in the add-on dir) — **the source of
  truth** for machine-local user settings and all connected remote decks.
- **Anki's collection config** (`col.get_config()` / `col.set_config()`) — the **cache of
  each sheet's parsed settings row**, under the single key `sheets2anki::sheet_settings`
  holding `{sheet_id: entry}`. Anki's `config` table carries a `usn`, so entries there
  sync through AnkiWeb along with the notes and note types; a second machine renders
  identical cards before it has ever downloaded the sheet, with no Google API and no extra
  setup. It is a cache, not a store: the spreadsheet is the source of truth and every sync
  overwrites the entry.

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
| `test_card_layout.py` | Side splitting and template generation from a `SheetConfig` |
| `test_sync_config.py` | The settings cache: round-tripping a parse through the collection config |
| `test_data_processor.py` | TSV parsing, validation, Cloze detection, `RemoteDeck` |
| `test_config_manager.py` | Settings CRUD and persistence |
| `test_utils.py` | URL/hash/validation utilities |
| `test_url_simplification.py` | Edit-URL → TSV conversion |
| `test_deck_title.py` | Deriving a deck name from the localised Google Sheets page title |
| `test_deck_configurations.py` | Deck-option handling |
| `test_search_fix.py` | Note-search edge cases |
| `test_theme.py` | Every colour resolves to one of Anki's own |
| `test_icons.py` | The icon set: names, themability, one viewBox |
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

A **Debug Mode** dialog (`Ctrl+Shift+L`) lets you toggle debug mode (and whether logs
accumulate across sessions), view the log inline, clear it, and open its folder — all
from inside Anki. `DebugManager` (in `src/debug.py`) owns the log file's lifecycle;
nothing is written to the file while debug mode is off.

## Conventions

- **Qt6 only.** Import Qt/Anki symbols through `compat.py`; do not reintroduce Qt5
  fallbacks or version-detection.
- **Dual-import pattern** in every `src/` module (see above).
- **No runtime third-party dependencies.** Nothing is vendored; the add-on uses only the
  stdlib and Anki's own modules. Reach for a new dependency only after checking the
  stdlib cannot do the job.
- **Formatting & lint:** `black` (line length 88) and `ruff` are **blocking** CI gates;
  `mypy` is advisory. The ruff config intentionally tolerates camelCase Anki-API names
  (`syncDecks`, `getRemoteDeck`) and the dual-import pattern — see `[tool.ruff.lint]` in
  `pyproject.toml`. Run them (or the pre-commit hooks) before pushing.
- **Version** lives in `manifest.json` and `pyproject.toml`, and the two must always
  agree. Don't copy the current number into prose — read it from the files. Releases are
  tag-driven and `.github/workflows/release.yml` **fails before packaging** if the tag,
  `manifest.json` and `pyproject.toml` disagree, so bump both files in the commit you
  tag.

---

For the contribution workflow and PR expectations, see
[`CONTRIBUTING.md`](../CONTRIBUTING.md). For the canonical, concise architecture rules,
see [`CLAUDE.md`](../CLAUDE.md).
