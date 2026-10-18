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
| `ID` | **Recommended** | The row's permanent key. Any text works (`1`, `Q-101`, `w01`) as long as no two rows share it. **Never change or reuse an ID.** A sheet without one still works, see [A sheet with no ID column](#a-sheet-with-no-id-column). |
| `SYNC` | No | Turns a row on or off. A row syncs when the cell says `TRUE`, `1`, `yes`, `sim`, `x` or `✓`. Anything else, including an empty cell, means "skip this row". **A sheet with no `SYNC` column syncs every row.** |
| `TAGS` | No | Extra Anki tags for the row, separated by commas or semicolons. |

## A sheet with no ID column

A sheet with no `ID` column still makes cards. **The text in each row's first
content column is then the row's ID**, and Sheet to Anki says so in one line:
*"No ID column → using column Word as the ID. Fixing the spelling of that word
makes it a new card."*

- The text is normalised before it becomes an ID: spaces trimmed at both ends,
  runs of spaces collapsed, and accents brought to one encoding (a phone keyboard
  and a desktop one can compose `ệ` differently). Upper and lower case are kept.
- Two rows with the same text (ignoring case) become `word (2)`, then
  `word (3)`, in sheet order.
- Inserting a row in the middle or reordering rows is fine: the key is the
  word, not its position, so a re-import updates the same notes and keeps their
  review progress.
- **Fixing the spelling of that word makes it a new card**, and the old card
  (with its progress) stays in Anki. If you often correct words in the first
  column, add an `ID` column.
- A row whose first column is empty is an invalid row (nothing can key it), even
  if other cells are filled.
- A [settings row](settings-row.md) still works: with no ID cell, `#config` opens
  the first column's settings cell, for example `#config name=Vocabulary; size=40`.
  The sheet-wide keys (`name`, `reverse`, `theme`, `next`, `shape`) belong to the
  sheet; every other key in that cell belongs to the first column.

Create sheet's *Front / Back* and *Vocabulary* templates are sheets like this: the
first column (Front, or Word) is the key, with no `ID` column. A file with no `ID`
column opened in Create sheet stays that way. A sheet with an `ID` column keeps its
IDs and `next=`.

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

Each sheet is a deck. A sheet with `name=` in its
[settings row](settings-row.md#sheet-wide-keys) gets a deck named exactly that, as
typed (e.g. `Từ vựng IELTS tuần 1`), from the `.apkg` and from the add-on. A sheet
without `name=` gets an `sc_` prefix: `sc_<file name>` in Sheet to Anki,
`sc_<file>::<sheet>` in the add-on. A column with `subdeck=1` in the
[settings row](settings-row.md#filing-notes-with-a-column-subdeck) adds a level
under it, and `subdeck=2` the next one:

| ID | Language | Lesson | Word | Meaning |
| :--- | :--- | :--- | :--- | :--- |
| `#config` | `subdeck=1` | `subdeck=2` | | |
| 1 | Japanese | Kanji | 水 | water |

files the card in `<deck>::Japanese::Kanji`. Neither level column is shown on the
card.

- A sheet with no level columns keeps everything in the deck itself.
- On a sheet that does sort its rows, **a row that names no level lands in a
  subdeck called `Unsorted`**, so it is easy to find.
- An older sheet with columns named `SUBDECK 1`, `SUBDECK 2` is still filed the
  same way, with a warning asking you to switch to `subdeck=`.
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
ID | SYNC | Language | Lesson | Word | Reading | Meaning | Example | TAGS
```

The settings row has `subdeck=1` under `Language` and `subdeck=2` under `Lesson`.
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
