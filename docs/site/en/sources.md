# Sheets, files and .apkg

Where your cards can live, and the ways they can reach Anki.

## One file, one deck per sheet

A Google Sheets file holds several sheets, the tabs along the bottom. SheetCards
connects **each sheet as a deck of its own**, named `sc_<file>::<sheet>`, with
its own columns, settings row and note type. Paste the file's link once and one
spreadsheet can hold your whole collection. `Ctrl+Shift+S` then lists one line
per sheet, so you choose which to update.

- **A sheet with no `ID` column is skipped**, and the window says which. Notes, a
  colour key or a draft can sit in the same file. Hidden sheets are skipped too.
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

## Create deck

[Create deck](../../create.html) makes an Anki deck from a sheet on a phone or a
computer, without the add-on. It shows what SheetCards makes of the sheet first: every row and whether it syncs, the deck tree, the tags, the
warnings from the settings row, and each finished card, which you can turn over,
listen to and type into. It runs the add-on's own code in your browser, so what
it shows is made the same way the sync makes it. Only the very last step, drawing
the card, is the page's own approximation of Anki; the template text it shows is
exact.

Press the reload button beside the sheet name after editing your sheet, and
Create deck fetches it again and keeps your place.

### Upload a file

**Upload a file**, or drag one onto the page, to open an `.xlsx`, `.xlsm`,
`.csv` or `.tsv` from your computer. Each tab of a workbook becomes its own deck.
The file never leaves your browser.

- **The add-on itself still needs a link.** An uploaded file reaches Anki
  through the `.apkg` download below.
- **A cell is read as the sheet shows it.** A date comes out as `2025-01-21`, a
  whole number as `1` rather than `1.0`.

### Download an .apkg

**Download for Anki** builds the deck as an `.apkg` file. **AnkiDroid and AnkiMobile
import it directly**, so a sheet can reach your phone without Anki on a computer
at all. It is built by the add-on's own code, with the same fields and card
design, and the note identity comes from your `ID` column, so **importing again
updates those notes instead of duplicating them**.

What an import cannot do is **delete**: Anki never removes a note that is missing
from the file. A row you delete from the sheet stays in your collection until you
delete it there. That is the real difference between importing and syncing.

## The editor

The [editor](../../editor.html) is a small spreadsheet for writing a
[settings row](settings-row.md). Pick settings from a list instead of
remembering them, and the deck and the card update beside you as you type. Copy
rows 1 and 2 when it looks right and paste them into cell A1 of your sheet.
