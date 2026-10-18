# Card types

A plain sheet makes one card per row: the front asks, the back answers. The
[settings row](settings-row.md) can turn that into other kinds of card.

In [Create sheet](../../sheet/), templates come with the settings row for
the kinds below already written: *Both ways (reverse)*, *Type the answer*,
*Write Chinese characters* (handwriting) and *Japanese with furigana*.

## Reverse cards

`reverse` in the `#config` cell adds a second card for every row that asks the
back and answers with the front.

```text
ID       Vietnamese   English
#config reverse
r01      đọc          to read
```

gives one card asking `đọc` and one asking `to read`. Both are scheduled
separately, from the same row. Remove `reverse` later: with the add-on, those second cards go away on the next
sync; with an `.apkg`, import it as usual (no Merge note types needed), then in
desktop Anki run **Tools → Empty Cards** to delete the old reverse cards. Your
content is not touched. Cloze sheets cannot have reverse cards, and a
card with nothing on one of its sides gets none either.

## Cloze

A cloze card hides part of a sentence. Write the deletions with Anki's usual
`{{c1::…}}` markup and **say which column holds them** with `cloze`:

```text
ID       Word      Example
#config            cloze
1        熟悉       我对这里{{c1::很熟悉}}，也{{c2::常来}}。
```

- That column becomes the question, wherever it sits in the sheet.
- Anki makes **one card per deletion**: two for the row above.
- The other columns appear as usual beside it.
- One cloze column per sheet. A second is ignored with a warning.

Why declare it? A sheet shares one card design across all its rows, so "which
column is the cloze" has to be answered once. Anki shows a cloze field that holds
no deletion as nothing at all, so guessing wrong would silently blank a column.

A row with `{{c1::…}}` on a sheet that declares no cloze column is reported as a
warning, in Sheet to Anki and in Anki's Card Layout window.

## Typing the answer

`type` on a column draws a box on the question. You type the answer, and Anki
compares it with that column, letter by letter, when you turn the card.

```text
ID       Hán tự    Pinyin        Meaning
#config            type=nc
```

- `type=nc` ignores accents and tone marks, so typing `shuxi` matches `shúxī`.
  Useful when the marks are hard to type but not the point.
- One `type` column per sheet; Anki allows one box per card.
- The box is not repeated on the reverse card.
- On a cloze sheet, `type` on the cloze column asks you to type the deleted
  words.

## Writing a character by hand

`draw` turns a column holding Chinese characters into a writing box. Typing tests
whether you can spell a word; this tests whether you can write it.

- **On the question** the box is empty. You write the character stroke by stroke,
  each stroke is checked, and a hint appears after two misses.
- **On the answer** the correct strokes are animated.
- A cell can hold several characters: `你好` gives two boxes.
- `size` is the side of the box in pixels (1–2000); 200–300 is comfortable.
- `color` sets the colour of the strokes. `tts` still works, so the character can
  also be read aloud.
- `hint` puts the box behind a click.

The stroke data comes from [HanziWriter](https://hanziwriter.org) over the
internet, so a `draw` card needs a connection. Without one the box shows the
character faintly instead. It is tested on Anki for desktop; on AnkiDroid and
AnkiMobile it depends on whether the app allows the card to load it. Only Chinese
characters have stroke data; anything else is printed in the box.

The example workbook's `12 Chinese drawing (viết tay)` sheet is a ready-made
deck, and Create sheet's *Write Chinese characters* template starts from the same
layout: meaning and pinyin on the question, a `draw` box, then the character
large and an example read aloud on the answer.
