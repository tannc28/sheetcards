# The settings row

Without one, the first of your columns is the front of the card and the rest are
the back, in plain text. **The settings row says how each column should look and
behave**: which side it goes on, how big it is, whether it is read aloud, whether
a link in it becomes a picture or a video, and more.

It is one optional row, directly under the column names. Nothing about it is
edited inside Anki: change the row, sync again, and the cards follow.

The [editor](../../editor.html) lets you build one by clicking, and shows the card
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
  marker and a space: `#config align=left; speed=0.9; reverse`.
- `#CONFIG` works too. `#config;align=left` also works, but a value like
  `#configuration` is not the marker, so that row would be a card.
- Only your own columns read their cell. Anything in the settings row's `SYNC`,
  `TAGS` or `SUBDECK` cells is ignored.
- The settings row is never a card and is not counted in the sync's row totals.

**Mistakes are reported, never guessed at.** An unknown key (`siz=48`), a bad
value (`color=notacolour`) or a number out of range (`size=400`) produces a
warning naming the column, and that one setting is left out. The rest of the row
still applies. You see the warnings in the [Create deck](../../create.html), in the
editor, and in Anki under **Tools → SheetCards → Card Layout…**.

## Per-column keys

Written in that column's cell.

| Key | Values | What it does |
| :--- | :--- | :--- |
| `side` | `front`, `back`, `hide` | Which side the column appears on. `hide` keeps the field in Anki but shows it on neither side. Default: the first column front, the rest back. |
| `size` | a number of pixels: **6–200** for text, **1–2000** for a picture, video or writing box (`size=48` or `size=48px`) | Font size for text; maximum width for an `image` or `video`; the side of the box for `draw`. Default: 40 px on the front (smaller on a phone), 18 px on the back. |
| `color` | `muted`, `accent`, a CSS colour name (`crimson`), or `#hex` | Text colour. `muted` and `accent` follow Anki's light and dark mode and the sheet's [theme](text.md#themes). A fixed colour like `black` does not, and disappears in night mode. |
| `bold`, `italic` | switch | Bold or italic text. |
| `align` | `left`, `center`, `right` | Alignment for this column only. |
| `label` | any text | A small caption above the value. |
| `hint` | switch | Hides the value behind a link you click to reveal. |
| `furigana` | switch | Prints the reading above the text. The cell must be written `日本語[にほんご]`: text, then the reading in square brackets. |
| `font` | `sc`, `tc`, `jp`, `kr`, `serif`, `sans`, `mono`, or any font name | The typeface. See [Themes and text](text.md#fonts-for-chinese-japanese-and-korean). |
| `rtl` | switch | Right-to-left text, for Arabic, Hebrew and Persian. |
| `vertical` | switch | Top-to-bottom text, the way Japanese is set in a book. |
| `math` | switch, or `math=block` | The cell is a formula. See [Themes and text](text.md#formulas-and-code). |
| `code` | switch, or `code=python` (any language name) | The cell is source code, coloured by language. |
| `tts` | a **full** language code: `en_US`, `zh_CN`, `ja_JP` | Anki reads the column aloud. See [Text to speech](tts.md). |
| `voices` | voice names, separated by commas | Which voices you would prefer. Anki falls back to any voice of that language. |
| `speed` | **0.5–2.0** | Speaking rate for this column. |
| `image`, `audio`, `video` | switch | The cell holds a link, and the card shows the picture, a player, or the video. See [Media](media.md). |
| `cloze` | switch | The column holds `{{c1::…}}` deletions, and the whole sheet becomes a cloze sheet. See [Card types](card-types.md#cloze). |
| `type` | switch, or `type=nc` | A box on the question where you type the answer. `nc` ignores accents. See [Card types](card-types.md#typing-the-answer). |
| `draw` | switch | The cell holds a Chinese character that you write by hand on the card. See [Card types](card-types.md#writing-a-character-by-hand). |
| `subdeck` | a level number: `subdeck=1` | The column is that level of the deck path, and is not shown on the card. See below. |
| `sort` | switch | Anki's browser lists and sorts the notes by this column instead of by `ID`. |

## Sheet-wide keys

Written after `#config` in the marker cell.

| Key | Values | What it does |
| :--- | :--- | :--- |
| `align` | `left`, `center`, `right` | Alignment for the whole card. A column's own `align` still wins. |
| `speed` | a number; keep it within 0.5–2.0 | Speaking rate for every spoken column that does not set its own. Unlike the per-column `speed`, this one is not checked, so an odd value reaches Anki as it is. |
| `reverse` | switch | Adds a second card that asks the back and answers with the front. See [Card types](card-types.md#reverse-cards). |
| `theme` | `paper`, `contrast`, `matcha`, `momiji`, `yuki`, `sakura` | A colour scheme for the whole card. See [Themes and text](text.md#themes). |

## Filing notes with a column (`subdeck`)

`SUBDECK 1`, `SUBDECK 2` are names the add-on chose. `subdeck=1` says the same
thing from one of your own columns, so you can keep your own column name:

```text
ID       Level        Word     Meaning
#config  subdeck=1    size=48
w01      HSK 1        写       to write
w02      HSK 2        山       mountain
```

This files `w01` in `sc_<file>::<sheet>::HSK 1`, and `Level` is not drawn on the
card. Where a note is filed is shown by the deck it sits in, so it is not
repeated on the card; the card settings (`size`, `color`, `side`, `tts` and the
rest) are refused on such a column with a warning. `sort` is the one exception,
because it is about the note too.

- The number is the level, so the order comes from the numbers, not from where
  the columns sit.
- An empty cell drops that level, just like an empty `SUBDECK` cell.
- Two columns cannot be the same level, and a media column cannot be a level.
- If a sheet uses both, the settings row wins, and the warning names the
  `SUBDECK` columns it overrules.

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
