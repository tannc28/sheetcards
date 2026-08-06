# Sheets2Anki

Author and maintain Anki decks in Google Sheets, then synchronize them into Anki with a single command.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Anki](https://img.shields.io/badge/Anki-25.x%2B-blue)
![Python](https://img.shields.io/badge/python-3.13-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

## Overview

Sheets2Anki is an Anki add-on that treats a Google Sheets spreadsheet as the source of truth for your flashcards. You write and organize cards in a familiar spreadsheet — alone or collaboratively — and the add-on keeps the corresponding Anki notes in sync: creating, updating, and removing them as the sheet changes.

It is designed for users who maintain large or collaboratively authored decks — exam-preparation collections, course material, and any deck that benefits from spreadsheet-style organization, bulk editing, and version control.

## Features

- **Spreadsheet-driven sync** — one-way synchronization from Google Sheets to Anki, with reliable create/update/delete tracking by stable row IDs.
- **Your columns, your schema** — apart from a few reserved headers, every column you add becomes a note field named exactly like the header. Name them in any language you like; the add-on does not impose a column list.
- **Configurable card layout** — decide per deck which fields appear on the front, which on the back, and how they are styled, without ever editing an Anki note type by hand.
- **Collaboration** — multiple authors can edit the same sheet; everyone syncs the latest content.
- **Cloze support** — `{{c1::...}}` patterns are detected automatically and rendered as cloze cards.
- **Reverse cards** — optionally add a second, back-to-front card to the same notes.
- **Hierarchical organization** — automatic deck hierarchy and namespaced tags built from your `SUBDECK` columns.
- **AI assistant** — optional in-card AI help, follow-up questions, and answer checking via Google Gemini, Anthropic Claude, or OpenAI.
- **Rich media** — embed images and videos (YouTube/Vimeo) directly in cards.
- **Automatic image hosting** — images placed in the sheet are uploaded and embedded as `<img>` tags automatically.
- **Study timer** — an optional, unobtrusive per-card timer.
- **AnkiWeb integration** — trigger an AnkiWeb sync automatically after each deck sync to reach AnkiMobile and AnkiWeb.

## Requirements

| Component | Minimum version |
| :--- | :--- |
| Anki | 25.7.5 |
| Qt | 6 (PyQt6 6.9.1) |
| Python | 3.13.5 (bundled with Anki 25.x) |

Sheets2Anki 3.x targets the modern Anki runtime only. Users on older Anki releases should remain on the 2.x line.

## Installation

### From AnkiWeb (recommended)

1. In Anki, open `Tools → Add-ons → Get Add-ons…`.
2. Enter the Sheets2Anki add-on code (see the [AnkiWeb listing](https://ankiweb.net/shared/addons/)).
3. Restart Anki. A new `Sheets2Anki` entry appears under the `Tools` menu.

### Manual installation

1. Download `sheets2anki-standalone.ankiaddon` from the [latest release](https://github.com/igorrflorentino/sheets2anki/releases/latest).
2. In Anki, open `Tools → Add-ons → Install from file…` and select the downloaded file.
3. Restart Anki.

## Getting started

### 1. Copy the template

Start from the official template, which already has the reserved columns in place and a few content columns to build on:

[**Open the Sheets2Anki template**](https://docs.google.com/spreadsheets/d/1N-Va4ZzLUJBsD6wBaOkoeFTE6EnbZdaPBB88FYl2hrs/edit?usp=sharing) → `File → Make a copy`.

### 2. Connect the sheet to Anki

1. In Google Sheets, choose `Share → Anyone with the link → Viewer`, then copy the link.
2. In Anki, press `Ctrl+Shift+A` (or `Tools → Sheets2Anki → Add New Remote Deck`).
3. Paste the link and give the deck a name.

### 3. Sync

Add your content to the sheet, then press `Ctrl+Shift+S` (or `Tools → Sheets2Anki → Synchronize Remote Decks`). Your cards appear in Anki, organized and ready to study.

## Spreadsheet schema

**Your spreadsheet defines the schema.** Only a handful of header names are reserved; every other column becomes an Anki note field named exactly like its header. Nothing forces you to use English — `Hán tự`, `Pinyin` and `Nghĩa` are perfectly good columns. Each row becomes exactly one note.

### Reserved columns

Header names are matched case-insensitively and surrounding whitespace is ignored, so `id`, `ID ` and `Id` are all the same column.

| Column | Required | Description | Example |
| :--- | :--- | :--- | :--- |
| `ID` | Yes | Stable unique identifier used to track each row across syncs. Do not edit or reuse it. | `Q101` |
| `SYNC` | No | Include the row only when this is set (`TRUE`, `1`, `yes`, `x`, `✓`). **If the sheet has no `SYNC` column at all, every row syncs.** | `TRUE` |
| `SUBDECK 1`, `SUBDECK 2`, … | No | One level of the deck path each, ordered by their number rather than their position in the sheet. Blank levels are skipped. | `Geography` |
| `TAGS` | No | Extra Anki tags for the row, separated by commas or semicolons. | `capitals, europe` |

### Content columns

Everything else is yours. Each remaining column becomes a note field carrying its header as the field name, and the column order in the sheet is the field order on the card by default — the first content column goes on the front, the rest on the back.

So a sheet whose header row reads:

```text
ID | SYNC | SUBDECK 1 | SUBDECK 2 | Hán tự | Pinyin | Nghĩa | Ví dụ | TAGS
```

produces notes with the fields `ID`, `Hán tự`, `Pinyin`, `Nghĩa` and `Ví dụ`, filed two subdeck levels deep, with `Hán tự` on the front of the card by default.

> **Adding and removing columns.** Adding a column adds the field and puts it on the back of the card; you can then move it wherever you like in the card layout. Removing a column stops the field being shown, but the field and its content are kept in Anki — Sheets2Anki never deletes data you have already collected.

## Card layout

How a card looks is a per-deck setting, not something the sheet dictates. Open `Tools → Sheets2Anki → Configure Card Layout` (`Ctrl+Shift+C`) to choose:

- which fields appear on the **front** and which on the **back** (by default the first content column is the front and the rest are the back);
- whether each field is preceded by a small **label**;
- **font sizes** for the front and back, and text **alignment**;
- a **reverse card**, a second back-to-front card added to the same notes;
- the **study timer** and where it sits on the card.

The reverse card is a second card template rather than a second note, so both directions are scheduled independently from a single spreadsheet row, and switching it off later removes those cards without touching your content. It is not available for cloze notes, which Anki limits to one template.

If you would rather craft the templates yourself in Anki's card editor, switch on the dialog's "edit the template myself" option; sync will then leave that deck's templates alone.

Card layouts are stored in your Anki collection rather than in the add-on's local settings, so they travel to your other machines through AnkiWeb sync.

## AI assistant

Sheets2Anki can add AI-powered controls to your cards for explanations, follow-up questions, and answer verification.

1. Open `Tools → Sheets2Anki → Configure AI Assistance` (`Ctrl+Shift+H`).
2. Select a provider — Google Gemini, Anthropic Claude, or OpenAI — and enter your API key. The key is stored locally in the add-on configuration.
3. While reviewing, use the **AI Help**, **AI Ask**, and **AI Checker** buttons on the card.

> **Security note:** AI responses are sanitized before display. Optional "mobile support" embeds your API key into the card templates so AnkiMobile and AnkiWeb can call the provider directly — this uploads the key to AnkiWeb and to every synced device. Enable it only if you accept that exposure, and prefer a restricted, rotatable key.

## Automatic image handling

Sheets2Anki can upload images from your spreadsheet and embed them in cards, so they display on every device including AnkiMobile.

1. Add two ordinary content columns named `IMAGE` and `HTML IMAGE` — the Apps Script looks for exactly these names — and insert an image into a cell in the `IMAGE` column (`Insert → Image → Image in cell`).
2. Configure the processor once via `Tools → Sheets2Anki → Configure Image Processor` (`Ctrl+Shift+P`): provide a free [ImgBB](https://api.imgbb.com/) API key and the URL of a deployed Google Apps Script web app.
3. On processing, images are uploaded to ImgBB and the resulting `<img>` markup is written to the `HTML IMAGE` column. Because `HTML IMAGE` is a normal content column, it syncs into a field of the same name like any other.

Full setup instructions, including deploying the Apps Script, are in [`scripts/IMAGE_PROCESSOR_README.md`](scripts/IMAGE_PROCESSOR_README.md).

## Organization

Your `SUBDECK` columns drive both the deck tree and the tags. A row with `SUBDECK 1 = Geography`, `SUBDECK 2 = Europe` and `SUBDECK 3 = Capitals` lands in:

```text
Sheets2Anki
└── <Remote Deck>
    └── Geography
        └── Europe
            └── Capitals
```

Blank levels are simply skipped, and a sheet with no `SUBDECK` columns keeps every note in the deck's root.

Each note also gets a small, predictable set of tags:

```text
sheets2anki                                  every note the add-on owns
sheets2anki::geography::europe::capitals     mirrors the deck path
capitals, europe                             whatever the TAGS column lists
```

## Keyboard shortcuts

All actions are available under `Tools → Sheets2Anki`; the most common have shortcuts:

| Shortcut | Action |
| :--- | :--- |
| `Ctrl+Shift+A` | Add a new remote deck |
| `Ctrl+Shift+S` | Synchronize remote decks |
| `Ctrl+Shift+D` | Disconnect a remote deck |
| `Ctrl+Shift+O` | Configure deck options |
| `Ctrl+Shift+W` | Configure AnkiWeb sync |
| `Ctrl+Shift+C` | Configure card layout |
| `Ctrl+Shift+I` | Configure study timer |
| `Ctrl+Shift+H` | Configure AI assistance |
| `Ctrl+Shift+P` | Configure image processor |
| `Ctrl+Shift+B` | Open the remote-decks backup tool |
| `Ctrl+Shift+L` | Toggle debug mode / view logs |

## Troubleshooting

- **Inspect the logs.** `Tools → Add-ons → Sheets2Anki → View Files → debug_sheets2anki.log` records the most recent sync in detail.
- **Back up before changes.** `Tools → Sheets2Anki → Remote Decks Backup` (`Ctrl+Shift+B`) saves your connected-deck configuration; you can restore it or re-add a deck cleanly.
- **Verify sheet access.** A failed download usually means the sheet is not shared as "Anyone with the link – Viewer".

If a problem persists, please open an issue at [github.com/igorrflorentino/sheets2anki/issues](https://github.com/igorrflorentino/sheets2anki/issues) and attach the relevant portion of the debug log.

## Contributing

Issues and pull requests are welcome. Development setup, the test suite, and the project architecture are documented in [`CLAUDE.md`](CLAUDE.md) and the build scripts under [`scripts/`](scripts/).

## License

Released under the [MIT License](LICENSE).
