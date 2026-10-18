# The settings row

Without one, the first of your columns is the front of the card and the rest are
the back, in plain text. **The settings row says how each column should look and
behave**: which side it goes on, how big it is, whether it is read aloud, whether
a link in it becomes a picture or a video, and more.

It is one optional row, directly under the column names. Nothing about it is
edited inside Anki: change the row, sync again, and the cards follow.

[Create sheet](../../sheet/) lets you build one by clicking, and shows the card
as you go.

## How to write it

**Row 2 is the settings row when its `ID` cell starts with `#config`.** Your
cards then start on row 3. Without that marker row 2 is an ordinary card, so a
sheet that never asks for settings is not affected.

| ID | Word | Reading | Meaning |
| :--- | :--- | :--- | :--- |
| `#config` | `size=48; tts=zh_CN` | `furigana; color=muted` | |
| 1 | 推迟 | 推迟[tuī chí] | to postpone |

- **Each cell holds `key=value` pairs separated by `;`.** `size=48; color=muted`.
- **A key on its own is a switch**: `bold`, `hint`, `reverse`. Write `bold=false`
  (or `no`, `0`, `off`) to spell out that it is off.
- **An empty cell means "the defaults"**, so you only write what you change.
- **Settings for the whole sheet go in the `#config` cell itself**, after the
  marker and a space: `#config name=HSK 1 words; theme=paper; reverse`.
- `#CONFIG` works too. `#config;align=left` also works, but a value like
  `#configuration` is not the marker, so that row would be a card.
- Only your own columns read their cell. Anything in the settings row's `SYNC`
  or `TAGS` cell is ignored.
- The settings row is never a card and is not counted in the sync's row totals.

**Mistakes are reported, never guessed at.** An unknown key (`siz=48`), a bad
value (`color=notacolour`) or a number out of range (`size=400`) produces a
warning naming the column, and that one setting is left out. The rest of the row
still applies. You see the warnings in the [Sheet to Anki](../../create/), in
Create sheet, and in Anki under **Tools → SheetCards → Card Layout…**.

## Basic keys

These are enough for most flashcard sets. Written in that column's own cell.

| Key | Values | What it does |
| :--- | :--- | :--- |
| `side` | `front`, `back`, `hide` | Which side the column appears on. `hide` keeps the field in Anki but shows it on neither side. Default: the first column front, the rest back. |
| `size` | a number of pixels: **6–200** for text, **1–2000** for a picture, video or writing box (`size=48` or `size=48px`) | Font size for text; maximum width for an `image` or `video`; the side of the box for `draw`. Default: 40 px on the front (smaller on a phone), 18 px on the back. |
| `bold` | switch | Bold text. |
| `color` | `muted`, `accent` | Text colour: `muted` is a soft colour for secondary text, `accent` the highlight colour. Both follow Anki's light and dark mode and the sheet's [theme](text.md#themes). Other colours: see [Advanced](#text). |
| `tts` | a **full** language code: `en_US`, `zh_CN`, `ja_JP` | Anki reads the column aloud. See [Text to speech](tts.md). |
| `image` | switch | The cell holds a link to a picture, and the card shows the picture. See [Media](media.md). |
| `type` | switch, or `type=nc` | A box on the question where you type the answer. `nc` ignores accents. See [Card types](card-types.md#typing-the-answer). |
| `hint` | switch | Hides the value behind a link you click to reveal. |
| `label` | any text, or bare | A small caption above the value. A bare `label` uses the column's own name as the caption; `label=Pinyin` writes a different one. |

## Sheet-wide keys

Written after `#config` in the marker cell.

| Key | Values | What it does |
| :--- | :--- | :--- |
| `name` | a deck name; spaces and any script are fine, up to 100 characters | The deck's name in Anki, exactly as typed (e.g. `Từ vựng IELTS tuần 1`, no `sc_` in front), and the sheet's identity. Sheet to Anki and the add-on recognise the sheet's notes by it, so a renamed file, a download saved as `Từ vựng (1).csv`, an .xlsx copy or the same sheet in Google Sheets is still one deck. Two sheets with one `name` are **one** deck: importing one overwrites the other's notes that share an ID. Changing `name` makes a new deck; review progress stays with the old one. Case and extra spaces do not count. |
| `theme` | `paper`, `contrast`, `matcha`, `momiji`, `yuki`, `sakura` | A colour scheme for the whole card. In Create sheet you pick it in the template step. See [Themes and text](text.md#themes). |

`name` is the **Flashcard set name** you fill in when you pick a template in
Create sheet, and Create sheet asks before changing it, since a new name is a new
deck in Anki. A sheet without `name` is recognised by its Google Sheets link, or
by its file name (the `.csv`/`.tsv`/`.xlsx` extension and a ` (1)`, `-2` suffix
left out), and its deck carries an `sc_` prefix. The add-on uses `name` exactly as
Sheet to Anki does, as the deck name and the identity, so an `.apkg` and the
add-on update the same notes.

You may also see `next=w15` and `shape=b1f3a2c` in the `#config` cell. Create
sheet writes these two itself, so that a deleted word's ID is never handed out
again and so it knows when **Merge note types** is needed. Do not edit them by
hand; the add-on reads them and does not use them.

## Advanced

The keys below are for when you need more. Per-column keys go in that column's
cell; `reverse` goes after `#config`.

### Voices

| Key | Values | What it does |
| :--- | :--- | :--- |
| `voices` | voice names, separated by commas | Which voices you would prefer for a `tts` column. Anki falls back to any voice of that language. |
| `speed` | **0.5–2.0** | Speaking rate for this column. |

### Card types

| Key | Values | What it does |
| :--- | :--- | :--- |
| `cloze` | switch | The column holds `{{c1::…}}` deletions, and the whole sheet becomes a cloze sheet. See [Card types](card-types.md#cloze). |
| `reverse` | switch, after `#config` | Adds a second card that asks the back and answers with the front. See [Card types](card-types.md#reverse-cards). |
| `draw` | switch | The cell holds a Chinese character that you write by hand on the card. See [Card types](card-types.md#writing-a-character-by-hand). |
| `furigana` | switch | Prints the reading above the text. The cell must be written `日本語[にほんご]`: text, then the reading in square brackets. |

### Text

| Key | Values | What it does |
| :--- | :--- | :--- |
| `italic` | switch | Italic text. |
| `align` | `left`, `center`, `right` | Alignment for this column only. The default is centred. |
| `font` | `sc`, `tc`, `jp`, `kr`, `serif`, `sans`, `mono`, or any font name | The typeface. A column with Chinese, Japanese or Korean `tts` gets the right one by itself; see [Themes and text](text.md#fonts-for-chinese-japanese-and-korean). |
| `color` | a CSS colour name (`crimson`), or `#hex` | A fixed colour. Unlike `muted`/`accent` it does not follow night mode, so `black` disappears on a dark background. |
| `code` | switch, or `code=python` (any language name) | The cell is source code, coloured by language. See [Themes and text](text.md#formulas-and-code). |
| `math` | switch, or `math=block` | The cell is a formula. |

### Media

| Key | Values | What it does |
| :--- | :--- | :--- |
| `audio` | switch | The cell holds a link to a sound file, and the card shows a player. |
| `video` | switch | The cell holds a YouTube, Google Drive or video file link, and the card shows the video. See [Media](media.md). |

### Deck

| Key | Values | What it does |
| :--- | :--- | :--- |
| `subdeck` | a level number: `subdeck=1` | The column is that level of the deck path, and is not shown on the card. See [below](#filing-notes-with-a-column-subdeck). |

### Reserved columns

These are not keys but column names in row 1. See [Columns](columns.md).

| Column | What it does |
| :--- | :--- |
| `ID` | The row's permanent key, so the note is updated when you sync or import again. Without one, the text in the first column is the key. |
| `TAGS` | Extra tags for the note, separated by commas or `;`. |
| `SYNC` | Only rows saying `TRUE`, `1`, `yes`, `sim`, `x` or `✓` sync. Without this column every row syncs. |

### Automatic, no key needed

- **Writing direction.** Each cell follows the direction of its own text, so
  Arabic, Hebrew and Persian run right to left by themselves.
- **Order in Browse.** Anki's browser lists and sorts the notes by the first
  content column that is not a deck level or a media column, instead of by `ID`.
- **Line breaks.** A cell with several lines shows as several lines on the card.
- **Hints.** A column whose cells mostly look like picture links warns
  *looks like picture links — add `image`*; one whose cells mostly look like
  `漢字[かな]` warns *looks like furigana — add `furigana`*.

`rtl` and `sort` are still accepted and do nothing more. `vertical`, and `align`
or `speed` written in the `#config` cell, are no longer settings: each gives a
warning saying what to do instead (write `align=`/`speed=` in each column's own
cell).

## Filing notes with a column (`subdeck`)

Write `subdeck=1` in a column's settings cell, and that column becomes the first
level of the deck path. The column keeps its real name, like `Lesson` or `Level`:

```text
ID       Level        Word     Meaning
#config  subdeck=1    size=48
w01      HSK 1        写       to write
w02      HSK 2        山       mountain
```

This files `w01` in the deck's `HSK 1` subdeck, and `Level` is not drawn on the
card. Where a note is filed is shown by the deck it sits in, so it is not
repeated on the card; the card settings (`size`, `color`, `side`, `tts` and the
rest) are refused on such a column with a warning.

- The number is the level, so the order comes from the numbers, not from where
  the columns sit. `subdeck=2` is the level under `subdeck=1`.
- An empty cell drops that level.
- Two columns cannot be the same level, and a media column cannot be a level.

**An older sheet with columns named `SUBDECK 1`, `SUBDECK 2`** still works as
before, with a warning: *SUBDECK columns are being retired — rename the column
(e.g. 'Lesson') and write subdeck=1 in the settings row*. Renaming the column
changes the note type's fields once: on Sheet to Anki, the download page reminds
you to turn on **Merge note types** for that import; the notes stay in the same
subdecks and keep their review progress.

## Heard but not shown (`side=hide` with `tts`)

A column with both `side=hide` and `tts` is read aloud but not printed. That is a
listening card: the sentence is spoken with nothing on screen to read it from.

```text
ID       Chinese              Pinyin   Meaning   Once more, slowly
#config  size=40; tts=zh_CN                      side=hide; tts=zh_CN; speed=0.5
```

It is spoken on the side it would have been drawn on, and a reverse card swaps it
along with everything else.

## A worked example

| Column | Its cell in the settings row |
| :--- | :--- |
| `ID` | `#config reverse` |
| `Word` | `side=front; size=48; tts=zh_CN; voices=Huihui` |
| `Reading` | `label=Pinyin; furigana; color=muted` |
| `Meaning` | `size=20` |
| `Example` | `size=16; color=muted; hint` |

With the data row `42 | 推迟 | 推迟[tuī chí] | to postpone, to delay | 会议推迟到下周。`
this gives:

- **Front:** `推迟` at 48 px, read aloud in Mandarin, by the *Huihui* voice if
  the device has it.
- **Back:** the reading printed above the characters, captioned *Pinyin*, in the
  muted colour; the meaning at 20 px; the example at 16 px, muted, behind a hint
  link.
- **A second card** (`reverse`) that asks the back and answers with `推迟`.

Everything not mentioned keeps its default, which is why `Meaning` only needs
`size=20`.

## Styling one column with CSS

Every block on a card carries the name of the column it came from:

```html
<div class="sc-back" data-sc-col="Pinyin">…</div>
```

So for something the settings row does not cover, the note type's **Styling** in
Anki can reach one column, for example
`[data-sc-col="Pinyin"] { letter-spacing: .04em; }`. Edit only the Styling: the
front and back templates are rebuilt from the sheet on every sync, so edits to
them do not last.
