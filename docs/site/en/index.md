# Getting started

SheetCards turns a spreadsheet into Anki flashcards. You write your cards in a
sheet, one row per card, and SheetCards makes them into a deck. The spreadsheet
is always the place you edit; Anki holds a copy. Every step works on a phone or
a computer.

No Google Sheet? [Create sheet](../../sheet.html) lets you write the whole sheet
on the web, and hands it straight to Sheet to Anki.

There are two ways to get the flashcards into Anki:

- **Sheet to Anki**, on this website: paste the sheet's link or open a file,
  check the cards, download an `.apkg` and open it in the Anki app (AnkiDroid,
  AnkiMobile or Anki on a computer). No add-on to install.
- **The add-on**, on a computer: connect the sheet once, and from then on one
  shortcut syncs whatever changed.

This page takes you from an empty sheet to cards you can study.

## What you need

- **The Anki app** you already use: the `.apkg` opens in AnkiDroid, AnkiMobile
  or Anki on a computer. SheetCards is free and needs no account.
- **A Google account**, only if you write in Google Sheets. Writing in
  [Create sheet](../../sheet.html) needs nothing. SheetCards reads a sheet without
  signing in.
- The add-on is only for the second way, and needs Anki 25.x or later on a
  computer.

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

### Writing it in Create sheet

1. **Pick a template and a theme.** There are 8 templates: *Front / Back*,
   *Vocabulary*, *Write Chinese characters* (stroke by stroke with `draw`),
   *Japanese with furigana*, *Custom*, *Vocabulary + picture*, *Both ways
   (reverse)* and *Type the answer*. In the same step pick a
   [theme](text.md#themes) for the cards (paper, contrast, matcha, momiji, sakura,
   yuki, or Anki's own colours); a theme is not a template, so any template can
   wear any theme.
2. **Name the flashcard set.** The name is written as `name=` in the settings
   row: it is both the deck's name in Anki and what lets Anki recognise the old
   deck when you import again. A new name is a new deck, so Create sheet asks
   before a rename.
3. **① Columns & card**: the column names and the settings row (row 2 of the
   sheet, where each cell says how that column shows on the card), with the card
   previewed beside them. **② Cards**: add, edit and delete words; IDs (`w01`,
   `w02`…) are given automatically. *Custom* opens on step ①, every other
   template goes straight to step ②.

**Your templates**: a sheet you already have (upload an `.xlsx` or `.csv`), or
the one you are writing (**Save as template**), kept as a template of your own:
its column names, settings row and one sample word. It lives in this browser
only.

The draft lives only in the browser (and Safari on an iPhone deletes it after 7
days without a visit), so save the sheet:

- **On a phone: press Save sheet link.** The whole sheet is in that link. Keep
  it (send it to yourself in Messenger, Telegram or Notes). Next time: open the link → add words
  → Make flashcards. Added words? Save a new link; the old one opens the old
  sheet.
- **On a computer: press Save .csv.** Next time, **Open a file to add words**.

The old words keep their IDs, so re-importing the `.apkg` updates the notes and
keeps your review progress.

## 2. Share it

In Google Sheets press **Share**, and under *General access* choose **Anyone with
the link → Viewer**. Then copy the address from your browser's address bar (the
normal link ending in `/edit…`).

SheetCards downloads the sheet without signing in, so a private sheet cannot be
read. Viewer access is enough: nothing is ever written back to your sheet.

## 3. Make the flashcards

1. Paste the link into [Sheet to Anki](../../create.html). It runs the add-on's
   own code in your browser, so what you see is what the add-on would make.
2. Check the cards: the decks, every row, and each finished card, which you can
   turn over, listen to and type into.
3. Press **Download .apkg** to get the file.
4. Open it in the Anki app. On a phone, open the file with **AnkiDroid** or
   **AnkiMobile**; on a computer, double-click it or use **File → Import…**.

Instead of a link you can open an `.xlsx` or `.csv` file, including a CSV saved
by Excel in Vietnamese (see [Upload a file](sources.md#upload-a-file)), or a
sheet link from Create sheet.

Opened the page from Messenger, Telegram, Facebook…? Those apps' built-in
browsers cannot download files, so the page shows a banner with **Copy link**
(and **Open in Chrome** on Android) to open it again in a real browser.

Added or renamed a column, or turned on `reverse`? The note type changed, so
when you import, turn on **Merge note types** and set **Update notes** to
**Always**. Sheet to Anki reminds you right before the download.

Importing the same sheet again later updates those notes instead of duplicating
them, but it cannot delete one: a row you remove from the sheet stays in Anki
until you delete it there. [Sheets, files and .apkg](sources.md) has the
details.

## Next week: adding words

1. Open the sheet again: the sheet link you saved, the `.csv` (with **Open a file
   to add words** in Create sheet — on Android, not from the Files app, where
   AnkiDroid would import the CSV straight into junk notes), or your Google Sheet.
2. Add the words. Leave the **flashcard set's name** alone: it is how Anki
   recognises the deck.
3. Press **Make flashcards**, download the new `.apkg` and import it. Your old
   cards are updated, their progress kept, nothing doubled.

Something off? See [FAQ: on a phone](faq.md#on-a-phone).

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
- **Something not working?** See [FAQ and troubleshooting](faq.md), or
  [Contact & feedback](../../contact.html?from=docs/en/index).

## Coming soon

- **Template library**: browse and use templates other people share.
- **Theme library**: more themes to dress your cards in.

Want them sooner, or something else? [Tell us](../../contact.html?from=docs/en/index).
