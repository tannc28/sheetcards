# Columns

There is no fixed list of columns. **Row 1 names the columns, and every row
under it is one card** (one Anki note). A handful of names have a special
meaning; every other column becomes a field of the same name, in any language.

Column names are matched without caring about upper or lower case or spaces
around them, so `id`, `ID ` and `Id` are the same column.

## Reserved columns

Only these names are special:

| Column | Needed? | What it does |
| :--- | :--- | :--- |
| `ID` | **Yes** | The row's permanent key. Any text works (`1`, `Q-101`, `w01`) as long as no two rows share it. **Never change or reuse an ID.** |
| `SYNC` | No | Turns a row on or off. A row syncs when the cell says `TRUE`, `1`, `yes`, `sim`, `x` or `✓`. Anything else, including an empty cell, means "skip this row". **A sheet with no `SYNC` column syncs every row.** |
| `SUBDECK 1`, `SUBDECK 2`, … | No | One level of the deck path each. They are ordered by their number, not by where they sit in the sheet, and an empty cell skips that level. `subdeck2` and `Subdeck  10` work too. |
| `TAGS` | No | Extra Anki tags for the row, separated by commas or semicolons. |

## Your own columns

Every other column becomes a field of the note, named exactly like the column.
`Word`, `Pinyin`, `Nghĩa`, `例句`: name them however your subject needs.

- **You need at least one.** A sheet with only reserved columns is refused with
  *"The sheet has no content columns"*.
- **Left to right is the card order.** The first of your columns goes on the
  front and the others on the back. Move a column and the card changes with it.
  To decide per column, use `side=` in the [settings row](settings-row.md).
- **A name used twice counts once.** The first column with that name wins and
  the other is ignored.

## Subdecks

Each sheet is a deck. In Sheet to Anki the deck takes its name from `name=` in
the [settings row](settings-row.md#sheet-wide-keys) (or from the file name
without one); the add-on names it `sc_<file>::<sheet>`. The `SUBDECK` columns add
levels under it:

| ID | SUBDECK 1 | SUBDECK 2 | Word | Meaning |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Japanese | Kanji | 水 | water |

files the card in `<deck>::Japanese::Kanji`.

- A sheet with no `SUBDECK` columns keeps everything in the deck itself.
- On a sheet that does sort its rows, **a row that names no level lands in a
  subdeck called `Unsorted`**, so it is easy to find.
- An ordinary column can also be a deck level, with `subdeck=1` in the
  [settings row](settings-row.md#filing-notes-with-a-column-subdeck).
- Subdecks that end up empty after a sync are removed.

## Tags

Every note gets three kinds of tag:

1. `sheetcards`, on every note the add-on made, so you can find them all.
2. `sheetcards::<subdeck path>`, which mirrors the deck tree in Anki's Browse
   sidebar.
3. Whatever the `TAGS` column lists.

Tags are tidied up: lower case, spaces and `:`/`;` turned into `_`, other
punctuation removed. `Unit 3: Intro` becomes `unit_3_intro`.

## A worked example

Row 1:

```text
ID | SYNC | SUBDECK 1 | SUBDECK 2 | Word | Reading | Meaning | Example | TAGS
```

One row:

```text
42 | TRUE | Japanese | Kanji | 水 | みず | water | 水を飲む | jlpt-n5; nature
```

This makes:

- **Fields:** `ID`, `Word`, `Reading`, `Meaning`, `Example`. `ID` always comes
  first.
- **Card:** front `Word`; back `Reading`, `Meaning` and `Example`.
- **Deck:** `<deck>::Japanese::Kanji`.
- **Tags:** `sheetcards`, `sheetcards::japanese::kanji`, `jlpt-n5`, `nature`.

## Cloze is a choice the sheet makes

A cell holding `{{c1::…}}` does not make a cloze card by itself. You say which
column carries the deletions with `cloze` in the settings row; see
[Card types](card-types.md#cloze). A row with `{{c1::…}}` on a sheet that declares
no cloze column is reported as a warning, because the markup would otherwise be
printed on the card as it is.
