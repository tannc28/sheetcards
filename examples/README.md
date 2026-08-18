# Example sheets

`sheets2anki-examples.xlsx` is a working Sheets2Anki source, and it is what the
[preview site](https://tannc28.github.io/sheets2anki/) and the add-on's
**Import Test Deck** point at. Twenty sheets, ordered so that reading them from
the first to the last takes you from *the smallest sheet that works* to *a deck
you would keep studying*.

Every sheet is a deck first and an example second. No sheet turns every directive
on at once, and none is wrong on purpose: both used to be here, and neither was a
deck anybody could have learned from.

Connect it exactly as you would your own spreadsheet — paste this link into
`Ctrl+Shift+A`, or into the preview site:

```
https://github.com/tannc28/sheets2anki/blob/main/examples/sheets2anki-examples.xlsx
```

Each sheet becomes its own deck, `s2a_sheets2anki-examples::<sheet name>`, with
its own columns, its own settings row and its own note type. That is the same
thing that happens to a Google Sheets file with several tabs.

**Where a column carries the meaning of a word, it is glossed in Vietnamese** —
this workbook is demonstrated to Vietnamese learners. So is each tab's name: a
word like *cloze* or *furigana* is the name of the thing you came to learn, so it
stays, with what it means in brackets after it. Everything else is English: the
headers, the settings rows, the labels printed on the cards, the explanatory
notes, and the two sheets that are documentation rather than vocabulary (`02`,
`09`). Nothing about the add-on is language-specific — what a sheet teaches
is only ever the content of a cell, and a deck of pharmacology or case law works
exactly the same way.

## Editing it

The workbook is generated, not hand-maintained. Its grids live in `SHEETS` at the
top of [`scripts/build_examples.py`](../scripts/build_examples.py) — one Python
list per sheet — so a settings row changed in a review shows up as a changed
*line* rather than as a changed ZIP. Edit that, then:

```bash
python scripts/build_examples.py            # rebuild the workbook
python scripts/build_examples.py --check    # fail if it is out of date
```

The build reads its own output back through `src/workbook.py` before writing it,
and `tests/test_examples.py` runs the same check — so the file in this directory
and the code that produced it cannot drift apart.

## The tour

### 01 Basic (cơ bản)

`ID`, `Front`, `Back`, nothing else — one word each in English, Chinese,
Japanese, Korean, German and Spanish, answered in Vietnamese. No settings row,
and no `SYNC` column, which means **every row syncs**: the column is opt-in
gating and its absence is not "nothing syncs". The first content column is the
front of the card and the rest are the back, so this sheet needs no
configuration at all.

`Front` and `Back` are *your* names for those columns, not the add-on's — the
same sheet works with `Term`/`Definition` or `Từ`/`Nghĩa`. And nothing here knows
what Korean is: a language is only ever the content of a cell.

### 02 Sync & subdecks (deck con)

Adds the four reserved columns. `SYNC` gates each row — `yes`, `x`, `1`, `TRUE`
and `✓` all count, an empty cell and `no` do not. `SUBDECK 1` and `SUBDECK 2`
build the deck path a level at a time, and a row that leaves them empty stays in
the deck root. `TAGS` is split on either commas or semicolons.

### 03 Card layout (bố cục thẻ)

The first sheet with a **settings row** — row 2, marked by `#config` in the `ID`
cell. It moves `Phonetic` to the front, sets sizes (including `48px`, since the
`px` suffix is tolerated), and shows all three ways to write a colour:
`color=accent` follows the light/dark theme, `color=#c2410c` is a hex value and
`color=teal` is a CSS name. `Note` is behind a `hint`, and `Source` is
`side=hide` — the field still exists on the note, it just is not rendered.
`#config align=left` is a deck-wide default; `align=right` on `Note` overrides it
for that column.

### 04 Reverse (thẻ ngược)

`#config reverse` adds a second card *template on the same note type*, asking the
back and answering with the front. One row, two cards, scheduled independently.

### 05 Type the answer (gõ đáp án)

`type=nc` on the Vietnamese column makes Anki draw an input box on the question
and diff what you typed against the field. `nc` drops the marks from the
comparison, so *cai cay* is accepted for **cái cây** — which is the difference
between practising vocabulary and practising a Vietnamese keyboard. `đ` is a
letter rather than a mark, so it still has to be typed.

### 06 Cloze (điền chỗ trống)

One column declares `cloze` and every deletion in it becomes its own card. The
deleted word is the grammar: *has been*, *by*, *will*, *more*, *used to*. `z02`
carries `c1` and `c2`, so that row makes two. The declaration is per *sheet*, not
per row, because the note type has one template set — and Anki renders a clozed
field holding no deletion as nothing at all, which is why only the declared
column is wrapped.

### 07 Images (hình ảnh)

`image` says the cell holds a bare URL, and `size=320` caps its width. The
picture is the first content column, so it is the prompt: see the thing, recall
the word. This one is a Chinese deck — sheet 16 is the same idea in English, with
a recording as well, and the two share no photograph between them.

### 08 Audio (âm thanh)

`audio` renders `<audio controls>` — listen, then reveal the word, how it is
written in the phonetic alphabet, and what it means. The recordings are real
people on Wikimedia Commons rather than a synthesiser, linked through
`Special:FilePath/En-us-book.ogg` so the address cannot go stale. They are `.ogg`
files, which play on Anki for desktop; a sheet meant for iOS is better off with
`.mp3`.

### 09 Video (video nhúng)

Every link form the add-on rewrites, one per row: a full `watch?v=` link, a
`youtu.be` short link, a `/shorts/` link, a link that is already an `/embed/`
one, and a direct video file. The rewrite happens at sync time, before the note
is written, because a card template can substitute a field but cannot transform
one. `hint` on a media column puts the player behind a disclosure rather than
behind Anki's `{{hint:}}`, which would only reveal the URL.

### 10 Speech (đọc thành tiếng)

`tts=en_US` makes Anki speak the field with an installed voice. The language code
must be the full form: Anki compares it against a voice's language *exactly*, so
a bare `en` matches nothing and plays silence. `#config speed=0.9` sets the
deck-wide rate and the last column overrides it with `speed=0.5`.

`voices=Samantha,Microsoft Zira` names the voices this column would rather be
read by, best first — the first is macOS, the second Windows. It is a
*preference*, not a requirement: a machine with neither installed still speaks
the field in any `en_US` voice it has, which is why naming a voice you happen to
like does not break the deck for anyone else.

### 11 Chinese writing (gõ chữ)

The character-writing deck, and the sheet that shows what these directives are
for. The prompt is the meaning and the pinyin; `type` on the `Hanzi` column asks
you to write the character and diffs it stroke for stroke; the answer then shows
the character large, speaks it, and hides a **stroke-order animation** behind a
`hint` so you only look when you did not know. 25 characters.

`Level` says `subdeck=1`, which makes it the first level of the deck path —
`…::HSK 1`, `…::HSK 2` — without the column having to be named `SUBDECK 1`. It is
a field on the note and never appears on the card: where a note is filed is a
bigger thing than how one card looks.

### 12 Chinese drawing (viết tay)

The same idea as the sheet before it, with the keyboard taken away: `draw` on the
`Draw` column turns it into a box you **write the character into, stroke by
stroke**, and each stroke is marked as you make it. Two misses and it shows you
where the next one starts.

`draw` on the *question* takes strokes; on the *answer* it animates the correct
ones. That is the whole of the directive — nothing says which of the two jobs a
column has, because the side it lands on already said it. `Draw` and `Character`
hold the same character on purpose: the box consumes the column it draws, so the
answer needs its own copy to print and to speak.

The stroke data comes from [HanziWriter](https://hanziwriter.org) over the
network, so these cards need to be online — and a client that refuses remote
scripts shows a dashed box with the character in it rather than nothing.

### 13 Furigana (phiên âm kanji)

`furigana` renders `漢字[かんじ]` as ruby text above the kanji. Anki's own filter
does the work; the settings row only decides which column goes through it.

### 14 Any headers (mọi ngôn ngữ)

The headers are `汉字`, `拼音`, `释义`, `例句`. Only `ID`, `SYNC`, `SUBDECK n`
and `TAGS` are reserved — every other header becomes a note field named exactly
as written, in whatever script your subject calls for.

### 15 Theme + subdeck (màu, tầng)

The tour ends on a deck rather than on a demonstration: fifteen JLPT words, filed
`JLPT::N5::Verbs` and so on, with the reading over the kanji and the word spoken
aloud. It is also the sheet the preview site opens on.

Its settings row is four columns wide and says five things — `theme=sakura`,
`furigana`, `tts=ja_JP`, two `side=back`s and the sizes. That is what a settings
row usually looks like. There used to be a sheet here that turned on every
directive at once, fourteen columns of them, and it taught nobody how to write
one: a card is a small number of decisions, and a sheet that makes all of them at
maximum shows you the ceiling instead of the room.

`theme=sakura` is the only deck-wide look the add-on ships. It repaints the card
— background, text, accent, and blossoms strewn faintly behind the word — in both
Anki's day and night modes, and it is deliberately faint: wallpaper that competes
with the word being learned has failed at being wallpaper.

Three `SUBDECK` levels build `…::JLPT::N5::Verbs`, which is worth doing on day
one: a level is a deck you can study on its own, and the path is mirrored into a
`sheets2anki::JLPT::N5::Verbs` tag for you, so the same cards are one click away
in the browser sidebar. The `TAGS` column is for the words you would search by
rather than file by — here `jlpt` and `n5`, which cut across the three levels.

## Where the media comes from

Every picture, recording and stroke-order animation is a
[Wikimedia Commons](https://commons.wikimedia.org) file, linked at its own
address. Nothing is copied into this repository and nothing lands in your
`collection.media`, so these cards need the network to draw — which is true of
any media column, not just these.

### 16 Picture words (từ vựng ảnh)

A picture on the front, and on the back the word, a recording of someone saying
it, and what it means. `image` and `audio` are two columns because a column holds
one kind of media — and both are addresses, not files: nothing is copied into your
collection, so these cards need the network to draw and to play.

`Group` carries `subdeck=1`. It is an ordinary column with an ordinary name, it
files the note under `…::Animals`, and it is never printed on the card — where a
note lives is a bigger thing than how one card looks.

The example sentence hides behind `hint`, so the card is a picture and a word
until you ask for more.

### 17 Draw & type (viết và gõ)

The same character asked for twice, two ways: `draw` gives you a box to write it
in stroke by stroke and marks each stroke as you go, and `type=nc` gives you
Anki's own box for the pinyin. Recognising a character and being able to produce
it are different skills, and this sheet refuses to let the first stand in for the
second.

`type=nc` ignores tone marks, which is what someone typing `shu` for `shū` means.
The character is spoken on the answer, so you hear it right after writing it.

### 18 Grammar cloze (ngữ pháp)

A sentence with the word that carries the grammar point deleted — 比, 了, 过, 会,
在, 被 — and `type` on the same column, which makes it `{{type:cloze:…}}`: you type
the missing word rather than turning the card over and nodding at it.

`Point` names the pattern on the front, so the card asks a question you can answer
rather than a riddle. The note behind `hint` says why the word is where it is.

### 19 Dictation (nghe rồi gõ)

The sentence column is `side=hide; tts=en_US; type`. Hidden, so it is drawn
nowhere; spoken, so it is on the question anyway; typed, so the only way through
the card is to listen and write down what you heard. Anki's comparison on the
answer shows the sentence character by character against what you typed.

`speed=0.85` slows the voice a little — dictation at conversational speed is a
different exercise, and a harder one than this deck is for. Anki's comparison is
kind about capitals and punctuation and merciless about spelling, which is the
right way round for this.

This is the shape of card the settings row exists for: nothing about it is a
default, and none of it needs a note type built by hand.

### 20 Video lesson (bài video)

The clip is the question. `video` on the *front*, with the question under it, and
the answer on the back — a comprehension deck rather than a vocabulary one, filed
one deck per lesson.

Every address is rewritten to that site's own player before the note is saved, so
a `watch?v=`, a `youtu.be/` and a direct `.webm` all arrive as something that
plays. Framed players do not work on AnkiDroid or AnkiMobile; on a phone these
cards show the question and nothing else.

### 21 Formulas & code (công thức)

The two kinds of cell that are not prose. `math=block` on the formula column wraps
it in `\[…\]`, which is all it takes: **Anki ships MathJax**, so nothing is
loaded and nothing is configured — you write TeX in the cell without the
delimiters and the card draws it.

`code=python` on the listing column keeps the cell exactly as typed, in a
monospace block that scrolls sideways rather than widening the card, and colours
it by language. That colouring *is* a library, fetched into the card the same way
the writing box fetches its own, with the same consequence: no network, no
colours — but the code is still there, still readable, still correctly indented.

`sort` on the question column is what makes this deck findable in the browser.
Without it Anki lists notes by the first field, which is `ID`, and a deck of
`m01, m02, m03` tells you nothing about what is in it.

### 22 Arabic (phải sang trái)

`rtl` is a direction, not a style: it sets `direction: rtl` on the column, and the
column starts from the right unless `align` says otherwise. Arabic, Hebrew and
Persian all need it, and nothing else in a settings row can produce it — a
right-aligned column is not the same thing as a right-to-left one, because the
difference shows the moment a sentence mixes scripts or carries punctuation.

`font=serif` here is a preference rather than a necessity. Where a typeface really
does decide whether a deck is right, see 11 and 23.

### 23 Vertical text (viết dọc)

`vertical` sets `writing-mode: vertical-rl` — top to bottom, right to left, which
is how Japanese is set in a book and how these three haiku by Bashō were meant to
be read. Latin words inside the line stay upright rather than lying on their side,
and the column is capped in height so a long line scrolls instead of growing the
card past the bottom of the screen.

`font=jp` is the important half. `直`, `骨`, `画` and a few hundred others are a
single Unicode code point drawn with different shapes in Chinese and Japanese, so
a machine holding only one CJK font draws whichever it has — and nothing on the
card can say which language the text is in. The sheet has to.
