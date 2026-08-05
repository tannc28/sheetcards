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
- **Collaboration** — multiple authors can edit the same sheet; everyone syncs the latest content.
- **Cloze support** — `{{c1::...}}` patterns are detected automatically and rendered as cloze cards.
- **Reverse cards** — optionally generate an Answer → Question card from the same row.
- **Hierarchical organization** — automatic deck hierarchy and namespaced tags derived from topic, subtopic, concept, importance, exam board, and more.
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

Start from the official template, which has every supported column pre-configured:

[**Open the Sheets2Anki template**](https://docs.google.com/spreadsheets/d/1N-Va4ZzLUJBsD6wBaOkoeFTE6EnbZdaPBB88FYl2hrs/edit?usp=sharing) → `File → Make a copy`.

### 2. Connect the sheet to Anki

1. In Google Sheets, choose `Share → Anyone with the link → Viewer`, then copy the link.
2. In Anki, press `Ctrl+Shift+A` (or `Tools → Sheets2Anki → Add New Remote Deck`).
3. Paste the link and give the deck a name.

### 3. Sync

Add questions and answers to the sheet, then press `Ctrl+Shift+S` (or `Tools → Sheets2Anki → Synchronize Remote Decks`). Your cards appear in Anki, organized and ready to study.

## Spreadsheet schema

The template ships with a full set of columns, but only three are required in the header. Each row becomes one note — or two, when the row also defines a reverse card.

### Required columns

| Column | Description | Example |
| :--- | :--- | :--- |
| `ID` | Stable unique identifier used to track each card across syncs. Do not edit or reuse it. | `Q101` |
| `QUESTION` | Front of the card. | `Capital of France?` |
| `ANSWER` | Back of the card. | `Paris` |

### Control column (recommended)

| Column | Description | Example |
| :--- | :--- | :--- |
| `SYNC` | Set to `TRUE` to include the row in synchronization. | `TRUE` |

### Optional columns

| Column | Description |
| :--- | :--- |
| `IMPORTANCE` | Priority level (used in the deck hierarchy and tags). |
| `TOPIC` / `SUBTOPIC` / `CONCEPT` | Hierarchical categorization, from broad to atomic. |
| `REVERSE` | Text for an additional Answer → Question card. |
| `COMPLEMENTARY INFO` / `DETAILED INFO` | Additional context and extended explanation. |
| `EXAMPLE 1` / `EXAMPLE 2` | Worked examples. |
| `MNEMONIC` | Memory aid. |
| `IMAGE` / `HTML IMAGE` | Source image cell and the generated `<img>` markup (see [Automatic image handling](#automatic-image-handling)). |
| `HTML VIDEO` | Embedded video markup (YouTube/Vimeo). |
| `BOARDS` / `LAST YEAR IN EXAM` / `CAREERS` | Exam metadata used for tagging. |
| `OTHER TAGS` | Additional free-form tags. |
| `EXTRA FIELD 1/2/3` | Free-use fields. |

> Columns you do not use can be hidden in Google Sheets without affecting synchronization.

## AI assistant

Sheets2Anki can add AI-powered controls to your cards for explanations, follow-up questions, and answer verification.

1. Open `Tools → Sheets2Anki → Configure AI Assistance` (`Ctrl+Shift+H`).
2. Select a provider — Google Gemini, Anthropic Claude, or OpenAI — and enter your API key. The key is stored locally in the add-on configuration.
3. While reviewing, use the **AI Help**, **AI Ask**, and **AI Checker** buttons on the card.

> **Security note:** AI responses are sanitized before display. Optional "mobile support" embeds your API key into the card templates so AnkiMobile and AnkiWeb can call the provider directly — this uploads the key to AnkiWeb and to every synced device. Enable it only if you accept that exposure, and prefer a restricted, rotatable key.

## Automatic image handling

Sheets2Anki can upload images from your spreadsheet and embed them in cards, so they display on every device including AnkiMobile.

1. Insert an image into a cell in the `IMAGE` column (`Insert → Image → Image in cell`).
2. Configure the processor once via `Tools → Sheets2Anki → Configure Image Processor` (`Ctrl+Shift+P`): provide a free [ImgBB](https://api.imgbb.com/) API key and the URL of a deployed Google Apps Script web app.
3. On processing, images are uploaded to ImgBB and the resulting `<img>` markup is written to the `HTML IMAGE` column, then synced like any other field.

Full setup instructions, including deploying the Apps Script, are in [`scripts/IMAGE_PROCESSOR_README.md`](scripts/IMAGE_PROCESSOR_README.md).

## Organization

Sheets2Anki builds a namespaced tag hierarchy in the Anki browser:

```text
sheets2anki
├── topics::topic::subtopic::concept    hierarchical content tree
├── concepts::concept                   flat concept search
├── importance::level                   priority level
├── boards::board                       exam boards
├── years::year                         exam years
├── careers::career                     professional areas
└── other_tags::tag                     additional tags
```

Decks are nested to mirror your spreadsheet's structure:

```text
Sheets2Anki
└── <Remote Deck>
    └── <Importance>
        └── <Topic>
            └── <Subtopic>
                └── <Concept>
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
