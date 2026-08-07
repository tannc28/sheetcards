# Sheets2Anki: Google Sheets to Anki

**Create flashcards in Google Sheets and sync them to Anki.**

Stop wasting time creating cards one by one. Use the power of spreadsheets to manage your study material.

## 🚀 Key Features

*   **Bulk Creation:** Write hundreds of cards as fast as you can type.
*   **Your Own Columns:** Apart from a few reserved headers, every column you add becomes a note field with the same name — in any language you like.
*   **Custom Card Layout:** An optional `#config` row in the sheet says which fields go on the front, which on the back, and how they look — sizes, colours, labels, hints, furigana — with no note-type editing at all. Leave the row out and nothing changes, so existing sheets keep working.
*   **Text-to-Speech:** Add `tts=zh_CN` (or `en_US`, `pt_BR`, …) to a column and Anki reads it aloud with your system voices, on desktop and mobile.
*   **Collaboration:** Work with friends or classmates on the same spreadsheet.
*   **Smart Sync:** Cards are automatically organized into subdecks that follow your `SUBDECK` columns.
*   **Media from a link:** Mark a column `image`, `audio` or `video` and a cell holding a bare URL becomes the picture or the player (`size=320` caps the width). These are links, so the card fetches them each time it is shown — great for a tidy sheet, but nothing shows offline, and mobile clients are stricter about remote content. For media that works on a plane, use Anki's own `collection.media`.
*   **Rich Media:** A field's HTML is rendered as written, so pasting an `<iframe>` embed (YouTube, Vimeo) straight into a cell works — a YouTube page link will *not* play in a `video` column, which expects a media file.
*   **Cloze Support:** Automatically detects `{{c1::cloze}}` cards.

## ⚡ Quick Start

1.  **Get the Template:** [Click here to copy the Official Google Sheet Template](https://docs.google.com/spreadsheets/d/1N-Va4ZzLUJBsD6wBaOkoeFTE6EnbZdaPBB88FYl2hrs/edit?usp=sharing).
2.  **Connect:** 
    *   In Sheets: `Share` -> `Anyone with the link can view` -> Copy Link.
    *   In Anki: `Tools` -> `Sheets2Anki` -> `Add Remote Deck` -> Paste Link.
3.  **Sync:** Press `Ctrl+Shift+S` to bring your cards into Anki.

## 📋 How it Works

The spreadsheet decides the schema. Only these headers are reserved:
- **ID**: Unique identifier for updates (required). | `Q101`
- **SYNC**: Mark the checkbox to sync this row — leave the column out entirely and every row syncs. | `TRUE`
- **SUBDECK 1**, **SUBDECK 2**, …: One level of the deck path each. | `Geography`
- **TAGS**: Extra tags, separated by commas. | `capitals, europe`

Every other column you add becomes a note field with the same name — `Question`, `Answer`, `Pinyin`, whatever your subject calls for. By default the first of them is the front of the card and the rest are the back.

To change that, put one optional **settings row** right under the headers: write `#config` in its `ID` cell and, in each column's cell, what that column should do — `side=front; size=48; tts=zh_CN`, `color=muted; hint`, `furigana`, `image; size=320`. Without that `#config` cell there is no settings row and row 2 is just another card, so sheets made before this feature keep working untouched. `Tools` -> `Sheets2Anki` -> `Configure Card Layout` (`Ctrl+Shift+C`) shows you what the add-on read, including any typo it could not understand.

The add-on handles the rest, creating beautiful, organized notes in your collection.

---
*Support the project on GitHub: [igorrflorentino/sheets2anki](https://rb.gy/z4z9cb)*

📸 ScreenShots

<img src="https://igorflorentino.notion.site/image/attachment%3A34b4181a-7e5f-4845-aa46-f46d70882caf%3Aimage.png?table=block&id=2efc60fb-3356-8000-b471-d9f9922f82a2&spaceId=fae2128c-75dd-48a0-a7ba-d31345199f23&width=1360&userId=&cache=v2" width="80%">

<img src="https://igorflorentino.notion.site/image/attachment%3A6474fa0d-2741-426e-853b-c786b9be9b00%3Aimage.png?table=block&id=2eec60fb-3356-802b-8fea-ddb0c56fb29c&spaceId=fae2128c-75dd-48a0-a7ba-d31345199f23&width=1420&userId=&cache=v2
" width="80%">

<img src="https://igorflorentino.notion.site/image/attachment%3A1d0ade0b-ab0a-4b11-9e39-0db0562ba48f%3Aimage.png?table=block&id=2eec60fb-3356-80bd-834c-ecaf59d35027&spaceId=fae2128c-75dd-48a0-a7ba-d31345199f23&width=1420&userId=&cache=v2" width="80%">

<img src="https://igorflorentino.notion.site/image/attachment%3A2c051dc4-c787-4e4f-9358-af54395abac0%3Aimage.png?table=block&id=2eec60fb-3356-803f-8512-e358eea04386&spaceId=fae2128c-75dd-48a0-a7ba-d31345199f23&width=1420&userId=&cache=v2" width="80%">

<img src="https://igorflorentino.notion.site/image/attachment%3A6426f9ea-6ccb-4800-84f1-6cc3c85eb889%3Aimage.png?table=block&id=2efc60fb-3356-807c-a800-caa0c38b2bf0&spaceId=fae2128c-75dd-48a0-a7ba-d31345199f23&width=1360&userId=&cache=v2" width="80%">

<img src="https://igorflorentino.notion.site/image/attachment%3Ab0be78ac-bfdc-402d-bc62-173d03010a1b%3Aimage.png?table=block&id=2efc60fb-3356-80f9-8d96-ee2f0e42dd33&spaceId=fae2128c-75dd-48a0-a7ba-d31345199f23&width=1360&userId=&cache=v2" width="80%">

👇 Full documentation and Instruction Manual

[--> GitHub Page <--](https://rb.gy/z4z9cb)