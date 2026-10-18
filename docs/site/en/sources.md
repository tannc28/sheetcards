# Sheets, files and .apkg

Where your cards can live, and the ways they can reach Anki.

## One file, one deck per sheet

A Google Sheets file holds several sheets, the tabs along the bottom. SheetCards
connects **each sheet as a deck of its own**, named `sc_<file>::<sheet>` (or
exactly the sheet's `name=`, when it has one), with
its own columns, settings row and note type. Paste the file's link once and one
spreadsheet can hold your whole collection. `Ctrl+Shift+S` then lists one line
per sheet, so you choose which to update.

- **In a file whose other sheets have an `ID` column, a sheet without one is
  skipped**, and the window says which. Notes, a colour key or a draft can sit in
  the same file. If no sheet has an `ID` column, each becomes a deck keyed by its
  first column (see [Columns](columns.md#a-sheet-with-no-id-column)). Hidden sheets
  are always skipped.
- **A deck remembers its sheet by name.** Move a sheet to another position and
  its deck follows. **Rename a sheet and the deck can no longer find it**: the
  sync says so and lists the names that do exist. Connect the file again to pick
  up the new name.

## An .xlsx file instead of a Google Sheet

A link to an `.xlsx` or `.xlsm` file works as well, read the same way, one deck
per sheet. A file in a GitHub repository is fine: paste the `…/blob/main/decks.xlsx`
address your browser shows and the add-on fetches the file behind it.

- **A file has to be uploaded again before a sync sees a change.** For a deck you
  edit often, Google Sheets is the better home.
- **The address must be public and start with `https`.** The add-on refuses
  other kinds of address, and any address inside a private network.

## Sheet to Anki

[Sheet to Anki](../../create/) makes Anki flashcards from a sheet on a phone or a
computer, without the add-on. It shows what SheetCards makes of the sheet first: every row and whether it becomes a note, the deck tree, the tags, the
warnings from the settings row, and each finished card, which you can turn over,
listen to and type into. It runs the add-on's own code in your browser, so what
it shows is made the same way the add-on makes it. Only the very last step, drawing
the card, is the page's own approximation of Anki; the template text it shows is
exact.

Press the reload button beside the sheet name after editing your sheet, and
Sheet to Anki fetches it again and keeps your place.

### Upload a file

**Choose an .xlsx or .csv file**, or drag one onto the page, to open an `.xlsx`, `.xlsm`,
`.csv` or `.tsv` from your computer. Each tab of a workbook becomes its own deck.
The file never leaves your browser.

- **The add-on itself still needs a link.** An uploaded file reaches Anki
  through the `.apkg` download below.
- **A cell is read as the sheet shows it.** A date comes out as `2025-01-21`, a
  whole number as `1` rather than `1.0`.
- **A CSV saved by Excel reads too.** The separator (comma, semicolon or tab) is
  detected, and so is UTF-16 ("Unicode Text"). A file that is not UTF-8, like
  Excel's "CSV (Comma delimited)" on a Vietnamese Windows, is read with the
  Windows Vietnamese (cp1258) or Western (cp1252) code page, and the page tells
  you so you can check the accents. Safest is Excel's **CSV UTF-8**.

### Download an .apkg

**Download .apkg** builds the deck as an `.apkg` file. **AnkiDroid and AnkiMobile
import it directly**, so a sheet can reach your phone without Anki on a computer
at all. It is built by the add-on's own code, with the same fields and card
design, and the note identity comes from your `ID` column, so **importing again
updates those notes instead of duplicating them**.

What an import cannot do is **delete**: Anki never removes a note that is missing
from the file. A row you delete from the sheet stays in your collection until you
delete it there. That is the real difference between importing and syncing.

Which deck a file is, in this order:

1. **`name=` in the [settings row](settings-row.md#sheet-wide-keys)**, when
   it is there. The deck carries exactly that name, with no `sc_` prefix; the
   add-on uses it too. Create sheet always writes it (it is the **Flashcard set name**), so a renamed file
   (`Từ vựng (1).csv`), an `.xlsx` copy, a share link or the same sheet in Google
   Sheets all update one deck. Two sheets with one `name` are one deck and
   overwrite each other's notes; a copied sheet stays the old deck until you
   rename it.
2. Otherwise the Google Sheets link and the tab.
3. Otherwise the file name, without its `.csv`/`.tsv`/`.xlsx` extension and the
   ` (1)`, `(1)` or `-2` a phone adds to a second download.

Create sheet also writes `next=` in the same cell: the next ID it will hand out.
That way a deleted word's ID is never reused for another word, which Anki would
take for the old one.

**Changing the columns needs Merge note types once.** Adding or renaming a
column, turning on `reverse`… changes the note type, and with the default
options Anki then updates no note at all. Sheet to Anki compares the sheet with
the `shape=` Create sheet writes into the `#config` cell (and with this device's
last download) and tells you: when you import, turn on **Merge note types** and
set **Update notes** to **Always**. Removing or moving a column needs nothing.
Switching to or from `cloze` cannot be merged by Anki; the page says how to keep
your progress.

## Create sheet

[Create sheet](../../sheet/) writes a whole sheet on the web, no Google
Sheets needed: the column names, the [settings row](settings-row.md) and every
word. Start from one of 8 templates (see
[Writing it in Create sheet](index.md#writing-it-in-create-sheet)), one of your
own templates, or open an `.xlsx`/`.csv` you already have. On a computer it is a spreadsheet: pasting rows
from Excel or Google Sheets adds words. On a phone each word opens as a form, one
field per column. Settings are picked from a list, and the card for the word you
are editing is drawn beside it.

The draft is saved in the browser after every change, but only in this
browser, so save the sheet outside it: **on a phone press Save sheet link, on a
computer press Save .csv**. The page says *Not saved — only a draft in this
browser* until you do. There are three ways out:

- **Make flashcards**: hands the sheet straight to Sheet to Anki, to check the cards
  and download an `.apkg`.
- **Save the sheet as a file**, `.xlsx` or `.csv`: keep the sheet as a file, open it here again to
  keep editing, or upload it to Google Drive to make it a Google Sheet.
- **Share link**: the whole sheet is compressed into the link itself (after the
  `#`) and sent to no server. Whoever opens it sees that sheet and edits their
  own copy; the link can also open straight as cards in Sheet to Anki. Some chat
  apps cut very long links short; send the file instead. **On a phone this
  button is Save sheet link, and it is the main save**: keep the link (send it to
  yourself) and open it next time to add words. On a computer the main save is
  the `.csv`.

### Paste a word list

Step ② **Add cards** has a **Paste a word list** button (above the list of words on
a phone, under the spreadsheet on a computer). Paste one word per line, with its meaning
if you like: `apple - quả táo`, `apple ; quả táo`, `apple: quả táo`,
`apple = quả táo`, or two columns copied from Excel or Google Sheets. The
separator is detected (you can change it), a notes app's bullets such as `- `,
`• `, `1. ` are dropped, and a hyphen inside a word such as `well-known` is not
split.

The preview shows which column each part goes to: the first part into the word
column, the second into the meaning column; each can be changed. **Duplicates**
(repeated in the list, or already in the sheet, ignoring case) are struck
through and left out unless you tick them again. For a Chinese or Korean sheet
(read from the word column's `tts=`) with a Phiên âm column, pinyin or the
romanisation is filled into empty cells. It is a suggestion worked out on your
device, so check it; Japanese is not filled in yet. **Add N words** adds them.
On a sheet keyed by its first column, a word you tick back in despite being a
duplicate is kept as `word (2)`; on a sheet with an `ID` column the new words
get IDs that carry on from the last one.

### Suggest

The **Suggest** button (in a word's form on a phone, under the spreadsheet for
the selected rows on a computer, or *Suggest for N words* when pasting a list)
looks the word up in open sources and offers a choice for each column the sheet
has:

- **Meaning**: up to 5 senses from Wiktionary, each with its part of speech, an
  English gloss and a Vietnamese one where en.wiktionary or vi.wiktionary has it.
- **IPA** in a US or UK accent, from en.wiktionary.
- **Example sentences** from Tatoeba with a Vietnamese translation. The
  translations are written by volunteers, so read one before you use it.
- **Pronunciation audio** from Wikimedia Commons, if the sheet has an `audio`
  column.
- **Pictures** from Wikimedia Commons, if the sheet has an `image` column. The
  cell stores a `Special:FilePath/…` address, as the example workbook does.

Nothing is picked for you. You choose a sense, a sentence, a picture; the
suggestion appears beside the cell's current value and stays marked until you
press **Use**, edit it, or press **Skip**. A cell you typed yourself is only
replaced when you press **Replace**. For Chinese, Japanese and Korean there are
only English meanings from Wiktionary plus pinyin or romanisation, no
Vietnamese meanings yet.

**Privacy:** the first time, the page asks before sending anything. Suggestions
send each word to wikimedia.org (Wiktionary, Commons) and tatoeba.org, and
nothing else from the sheet. Results are kept in the browser so a word is not
looked up twice.

**Sources:** when you use a suggestion, its source is written into the word's
Note or Source column (if the Note column holds your own text, or the sheet has
neither, the page adds a *Source* column with `side=hide`, which is not drawn on
the card and can be deleted). Licences: Wiktionary
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/), Tatoeba
[CC BY 2.0 FR](https://creativecommons.org/licenses/by/2.0/fr/), each Commons
file under its own author and licence (written next to the file name). Pinyin
comes from the pinyin-pro library and Korean romanisation from es-hangul (both
MIT), downloaded to the browser only when needed.
