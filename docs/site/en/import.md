# Coming from Quizlet, Noji, Anki

Already have your words somewhere else? Bring them into Sheet to Anki without
typing them again. Everything is read in your browser and sent nowhere.

## Paste text

In Sheet to Anki, press **Paste text**, give the **Flashcard set name**, and
paste the list into the box. One card per line, for example:

```
apple - quả táo
book - quyển sách
journey - chuyến đi
```

- **The separator is detected**: tab, ` - `, `=`, `|`, `;`, `:`, `,`, `>>`. If
  the guess is wrong, pick another under *Between front and back*.
- A line with more than two parts gets extra back columns.
- Repeated lines are marked and left out; tick one to keep it.
- The cards become a Basic sheet with two columns, **Front** / **Back**, and
  `#config name=<name>`. The page's address carries the whole sheet, so a reload
  or a link sent to someone opens the same set.
- **Next week, paste the longer list under the same name**: each card is keyed by
  the text on its front, so importing the new `.apkg` updates the cards you have
  (keeping review progress) and adds the new ones. Fixing a front's spelling
  makes it a new card.
- **Open in Create sheet** takes the list to Create sheet to add columns
  (reading, example, picture…).

## Write a whole set as text

A flashcard set fits in one note, with its name and settings. There are two ways
to write it: the same set, the same keys; only where the settings sit differs.

**Text**, for notes apps:

```text
#config name=Travel B1; theme=sakura
Word [tts=en_US; bold] | IPA [color=muted] | Meaning | Example [italic]
airport | /ˈer.pɔːrt/ | sân bay | We got to the airport early.
luggage | /ˈlʌɡ.ɪdʒ/ | hành lý | My luggage is too heavy.
```

1. **Line 1 is `#config`** with the keys for the whole set: `name=`, `theme=`,
   `reverse`. It can be left out, but with `name=` pasting it again later
   updates the same set.
2. **Line 2 is the column names**, separated by `|`. A column's settings go in
   square brackets after its name, with the keys of the
   [settings row](settings-row.md). A name without brackets uses the defaults
   (the first column on the front, the rest on the back).
3. **Every line after that is a card**, its cells separated by `|`.

**Table**, for Google Sheets and Excel (a CSV file or a Markdown table is this
form too):

| Word | IPA | Meaning | Example |
| :--- | :--- | :--- | :--- |
| `#config name=Travel B1; theme=sakura; tts=en_US; bold` | `color=muted` | | `italic` |
| airport | /ˈer.pɔːrt/ | sân bay | We got to the airport early. |

Row 1 is the column names, row 2 the settings row: the first cell is `#config`,
the keys for the whole set and the first column's settings; every other cell is
the settings of the column above it. Pasting the whole table into **Paste text**
works too.

Only pasting words? The page shows a **Settings** panel (read aloud, theme, which
side each column goes on) and hands your own text back with the first two lines
added, with a **Copy** button. Paste that into your note; next week add words at
the bottom and paste the whole thing again.

## Paste a whole CSV sheet

CSV or TSV text (copied from a file, or inside a ` ```csv ` block) can be pasted
into **Paste text** too: the ` ``` ` block is taken out, and when its first row
has an `ID` column or its second row is `#config`, the sheet opens as it is,
with its own columns and settings row.

## Quizlet

In Quizlet, open the set → **⋯** → **Export** → **Copy text**, and paste it into
**Paste text**.

- Quizlet's default is a tab between term and definition and a new line between
  cards. Both are detected.
- If you chose another mark under *Between rows* (`;`, or a custom one), the
  whole set is one line; the repeated mark is found and offered under *Between
  cards*.
- Quizlet does not export a set you copied from someone else.

## Noji, Brainscape and other CSV files

Noji (formerly Anki Pro) exports a deck as a text-only CSV file. Open it with
**Open file** in Sheet to Anki or Create sheet; a `.txt` file works too.

- **A file with no row of column names** (just term, definition) still reads
  right: when the first row looks like the rows under it, it is read as a card
  and the columns are called **Front** / **Back**. If the guess is wrong, press
  *The first row is column names* (or *The first row is a card*) in the note.
- A first row holding `ID`, `TAGS`, or a familiar column name
  (Front, Back, Term, Definition, Meaning…) is always read as column names.

## A shared Anki deck (.apkg)

A deck from AnkiWeb Shared Decks, or an `.apkg`/`.colpkg` exported from Anki,
opens with **Open file** as a sheet you can edit and turn into an `.apkg` again.

- **Each note type becomes a sheet**: its fields are the columns, each note's
  guid becomes the `ID` column, subdecks become columns `Deck 1`, `Deck 2`…
  (marked `subdeck=1`, `subdeck=2`… in the settings row), tags become `TAGS`. The settings row records which fields are on the front, the
  cloze field, a type-in answer and a reverse card.
- **Formatting**: bold, italic, underline, sub/superscript and line breaks are
  kept; other HTML tags are removed and their text kept.
- **Pictures and sounds cannot come along**: they are files inside the package,
  and a sheet can only link to the web. The page says how many were left out.
  Add them back with an `image` / `audio` column holding links (see
  [Pictures, sound and video](media.md)).
- A deck made from the sheet is a **new deck** in Anki; it does not update the
  original deck's notes, since the two have different guids.
- **A deck exported by a newer Anki**: since Anki 2.1.50 an `.apkg` uses a
  compressed format by default that a browser cannot read, and the page says so.
  In Anki choose **File → Export → Anki Deck Package** and tick **Support older
  Anki versions**, then open the new file.
