# Getting started

SheetCards turns a spreadsheet into Anki flashcards. You write your cards in
Google Sheets, one row per card, and SheetCards makes them into a deck. The
spreadsheet is always the place you edit; Anki holds a copy.

No Google Sheet? [Create sheet](../../sheet.html) lets you write the whole sheet
right on the web, on a phone too, and hands it straight to Create deck.

There are two ways to get the deck into Anki:

- **Create deck**, on this website: paste the sheet's link, check the cards,
  download an `.apkg` and open it in Anki. It works on a phone or a computer,
  with nothing to install.
- **The add-on**, on a computer: connect the sheet once, and from then on one
  shortcut syncs whatever changed.

This page takes you from an empty sheet to cards you can study.

## What you need

- **A Google account**, only to write the sheet. SheetCards reads it without
  signing in.
- **Anki** anywhere: AnkiDroid, AnkiMobile, or Anki 25.x or later on a computer.
  The add-on is only for the second way, and needs the computer.

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

### The sheet is the original

Everything lives in the sheet: the cards, how they look, the deck. SheetCards
only reads it. A `.csv` file is a sheet too, and this is the whole format: row 1
names the columns, row 2 (optional) is the [settings row](settings-row.md)
starting with `#config`, and every row after it is a card.

```
ID,Word,Meaning
#config,size=40; tts=en_US,size=24
1,library,thư viện
2,airport,sân bay
```

It opens in Google Sheets, Excel or Create sheet; every template in Create sheet
has a button that downloads exactly this file.

### Writing it in Create sheet: two steps

Create sheet splits a sheet into two steps. **① Template**: the column names and
the settings row, which is how the cards look, with the card previewed beside
them. **② Cards**: add, edit and delete words. Picking a ready template
(Vocabulary, Vocabulary + picture, Both ways, Type the answer, one per theme…)
goes straight to step 2; *Custom* starts at step 1. A sheet you already have
(`.xlsx` or `.csv`) can be kept as a template too, under *Your templates*, in
this browser only.

The draft lives only in the browser, so press **Save .csv**. Next time, **Open a
file to add words**, on a phone too, and carry on; the old words keep their IDs,
so re-importing the `.apkg` updates the notes and keeps your review progress.

## 2. Share it

In Google Sheets press **Share**, and under *General access* choose **Anyone with
the link → Viewer**. Then copy the address from your browser's address bar (the
normal link ending in `/edit…`).

SheetCards downloads the sheet without signing in, so a private sheet cannot be
read. Viewer access is enough: nothing is ever written back to your sheet.

## 3. Create the deck

1. Paste the link into [Create deck](../../create.html). It runs the add-on's
   own code in your browser, so what you see is what the add-on would make.
2. Check the cards: the decks, every row, and each finished card, which you can
   turn over, listen to and type into.
3. Press **Download for Anki** to get an `.apkg` file.
4. Open it in Anki. On a phone, open the file with **AnkiDroid** or
   **AnkiMobile**; on a computer, double-click it or use **File → Import…**.

Importing the same sheet again later updates those notes instead of duplicating
them, but it cannot delete one: a row you remove from the sheet stays in Anki
until you delete it there. [Sheets, files and .apkg](sources.md) has the
details.

## Or: sync automatically from a computer

The add-on keeps a deck in step with its sheet, deletions included, so that
editing the sheet and pressing one shortcut is the whole routine.

### Install the add-on

1. Download
   [`sheetcards.ankiaddon`](https://github.com/tannc28/sheetcards/releases/latest/download/sheetcards.ankiaddon).
2. In Anki, open **Tools → Add-ons**, press **Install from file…** and pick the
   file you downloaded.
3. Restart Anki.

A **SheetCards** menu now appears under **Tools**. Everything the add-on does is
in that menu.

### Connect the sheet

In Anki choose **Tools → SheetCards → Connect a Google Sheet…** and paste the
link. The window checks the link as you type and tells you what it found: how
many sheets, how many rows, and the names of the decks it will make.

You do not name the deck. It is named after the file and the sheet, as
`sc_<file name>::<sheet name>`. Each tab in the file becomes a deck of its own
(see [Sheets, files and .apkg](sources.md)).

### Sync

Choose **Tools → SheetCards → Update Decks from Sheets…** (`Ctrl+Shift+S`), tick
your deck and press **Update**. When it finishes your cards are ready to study.

From now on the routine is: edit the sheet, press `Ctrl+Shift+S`. New rows become
new cards, edited cells update their cards (your review history is kept), and
deleted rows are removed. [Syncing](syncing.md) has the details.

## Next steps

- **Change how the cards look.** Add a [settings row](settings-row.md) under the
  column names to set sizes, colours, which side a column goes on, sound,
  pictures and more. [Create sheet](../../sheet.html) helps you write one by
  clicking.
- **Start from an example.** The [example workbook](examples.md) has 31 small
  decks, each showing one feature.
- **Something not working?** See [FAQ and troubleshooting](faq.md).
