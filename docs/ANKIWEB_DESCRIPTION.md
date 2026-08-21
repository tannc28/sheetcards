# SheetCards: flashcards from a spreadsheet

**Write your cards in a spreadsheet. Study them in Anki.**

Stop wasting time creating cards one by one. Use the power of spreadsheets to manage your study material.

## 🚀 Key Features

*   **Bulk Creation:** Write hundreds of cards as fast as you can type.
*   **Your Own Columns:** Apart from a few reserved headers, every column you add becomes a note field with the same name — in any language you like.
*   **Custom Card Layout:** An optional `#config` row in the sheet says which fields go on the front, which on the back, and how they look — sizes, colours, labels, hints, furigana — with no note-type editing at all. Leave the row out and nothing changes, so existing sheets keep working.
*   **Text-to-Speech:** Add `tts=zh_CN` (or `en_US`, `pt_BR`, …) to a column and Anki reads it aloud with your system voices, on desktop and mobile.
*   **Collaboration:** Work with friends or classmates on the same spreadsheet.
*   **Not only Google:** an `.xlsx` at any https address works too, and the browser preview takes an uploaded `.xlsx`, `.csv` or `.tsv`.
*   **Smart Sync:** Cards are automatically organized into subdecks that follow your `SUBDECK` columns.
*   **Media from a link:** Mark a column `image`, `audio` or `video` and a cell holding a bare URL becomes the picture or the player (`size=320` caps the width). These are links, so the card fetches them each time it is shown — great for a tidy sheet, but nothing shows offline, and mobile clients are stricter about remote content. For media that works on a plane, use Anki's own `collection.media`.
*   **Video from an ordinary link:** Paste the YouTube address out of your browser — `watch?v=`, `youtu.be/`, `/shorts/` — or a Google Drive file link, and a `video` column turns it into a player. The address is rewritten into that site's own embed address while it syncs, so nothing has to be typed in a special form. A direct `.mp4` works too. Framed players are blocked on AnkiDroid and AnkiMobile, which get a link instead.
*   **Cloze Support:** Automatically detects `{{c1::cloze}}` cards.

## ⚡ Quick Start

1.  **See it working first:** paste this link into `Tools` -> `SheetCards` -> `Add Remote Deck` and sync it. It is the example workbook — thirty-one sheets, one deck each, from the smallest sheet that works up to a Chinese character-writing deck.
    `https://github.com/tannc28/sheetcards/blob/main/examples/sheetcards-examples.xlsx`
    (Or open <https://tannc28.github.io/sheetcards/> and read it in the browser, with no install at all.)
2.  **Build your own:** a new Google Sheet with an `ID` column and one column per thing you want on the card. Copy the sheet from the example that is nearest to what you are making.
3.  **Connect:**
    *   In Sheets: `Share` -> `Anyone with the link can view` -> Copy Link.
    *   In Anki: `Tools` -> `SheetCards` -> `Add Remote Deck` -> Paste Link.
4.  **Sync:** Press `Ctrl+Shift+S` to bring your cards into Anki.

## 📋 How it Works

The spreadsheet decides the schema. Only these headers are reserved:
- **ID**: Unique identifier for updates (required). | `Q101`
- **SYNC**: Mark the checkbox to sync this row — leave the column out entirely and every row syncs. | `TRUE`
- **SUBDECK 1**, **SUBDECK 2**, …: One level of the deck path each. | `Geography`
- **TAGS**: Extra tags, separated by commas. | `capitals, europe`

Every other column you add becomes a note field with the same name — `Question`, `Answer`, `Pinyin`, whatever your subject calls for. By default the first of them is the front of the card and the rest are the back.

To change that, put one optional **settings row** right under the headers: write `#config` in its `ID` cell and, in each column's cell, what that column should do — `side=front; size=48; tts=zh_CN`, `color=muted; hint`, `furigana`, `image; size=320`. Without that `#config` cell there is no settings row and row 2 is just another card, so sheets made before this feature keep working untouched. `Tools` -> `SheetCards` -> `View Card Layout` (`Ctrl+Shift+C`) shows you what the add-on read, including any typo it could not understand.

The add-on handles the rest, creating beautiful, organized notes in your collection.

---
*Support the project on GitHub: [tannc28/sheetcards](https://github.com/tannc28/sheetcards)*

👀 Try it in the browser, with nothing installed

[--> Live preview <--](https://tannc28.github.io/sheetcards/)

👇 Full documentation and Instruction Manual

[--> GitHub Page <--](https://github.com/tannc28/sheetcards)
