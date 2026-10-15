# Getting started

SheetCards is an Anki add-on that turns a spreadsheet into flashcards. You write
your cards in Google Sheets, one row per card, and the add-on brings them into
Anki. When you change the sheet, one click updates the cards. The spreadsheet is
always the place you edit; Anki holds a copy.

This page takes you from an empty sheet to cards you can study, in five steps.
*Đọc bằng tiếng Việt: [Bắt đầu](getting-started-vi.md).*

## What you need

- **Anki 25.x or later** on a computer (Windows, macOS or Linux).
- **A Google account**, only to write the sheet. The add-on reads it without
  signing in.

## Install the add-on

1. Download
   [`sheetcards.ankiaddon`](https://github.com/tannc28/sheetcards/releases/latest/download/sheetcards.ankiaddon).
2. In Anki, open **Tools → Add-ons**, press **Install from file…** and pick the
   file you downloaded.
3. Restart Anki.

A **SheetCards** menu now appears under **Tools**. Everything the add-on does is
in that menu.

## 1. Make a sheet

Open a new Google Sheet and type this, starting in cell A1:

| ID | Word | Meaning |
| :--- | :--- | :--- |
| 1 | library | thư viện |
| 2 | airport | sân bay |
| 3 | season | mùa |

- **Row 1 holds the column names.** `ID` is the only name the add-on requires.
- **`ID` is each card's permanent label.** Any text works (`1`, `w01`, `HSK-17`),
  as long as no two rows share one. Never change or reuse an ID: the add-on uses
  it to know which card is which.
- **Every other column is yours.** `Word` and `Meaning` could just as well be
  `Từ` and `Nghĩa`, or `汉字` and `拼音`. Each becomes a field of that name in
  Anki.

By default the first of your columns goes on the front of the card and the rest
go on the back. So this sheet makes cards that ask `library` and answer
`thư viện`.

## 2. Share it

In Google Sheets press **Share**, and under *General access* choose **Anyone with
the link → Viewer**. Then copy the address from your browser's address bar (the
normal link ending in `/edit…`).

The add-on downloads the sheet without signing in, so a private sheet cannot be
read. Viewer access is enough: nothing is ever written back to your sheet.

## 3. Check it in the preview (optional)

Paste the link into the [preview](../preview.html). It runs the add-on's own code
in your browser and shows the decks, every row, and the finished cards, with
nothing installed. If the preview can read your sheet, so can Anki.

## 4. Connect it

In Anki choose **Tools → SheetCards → Connect a Google Sheet…** and paste the
link. The window checks the link as you type and tells you what it found: how
many sheets, how many rows, and the names of the decks it will make.

You do not name the deck. It is named after the file and the sheet, as
`sc_<file name>::<sheet name>`. Each tab in the file becomes a deck of its own
(see [Sheets, files and .apkg](sources.md)).

## 5. Sync

Choose **Tools → SheetCards → Update Decks from Sheets…** (`Ctrl+Shift+S`), tick
your deck and press **Update**. When it finishes your cards are ready to study.

From now on the routine is: edit the sheet, press `Ctrl+Shift+S`. New rows become
new cards, edited cells update their cards (your review history is kept), and
deleted rows are removed. [Syncing](syncing.md) has the details.

## Next steps

- **Change how the cards look.** Add a [settings row](settings-row.md) under the
  column names to set sizes, colours, which side a column goes on, sound,
  pictures and more. The [editor](../editor.html) helps you write one.
- **Start from an example.** The [example workbook](examples.md) has 31 small
  decks, each showing one feature.
- **Something not working?** See [FAQ and troubleshooting](faq.md).
