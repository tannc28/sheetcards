# Example sheets

`sheets2anki-examples.xlsx` is a working Sheets2Anki source, and it is what the
[preview site](https://tannc28.github.io/sheets2anki/) and the add-on's
**Import Test Deck** point at. Fifteen sheets, ordered so that reading them from
the first to the last takes you from *the smallest sheet that works* to *every
directive at once*.

Connect it exactly as you would your own spreadsheet — paste this link into
`Ctrl+Shift+A`, or into the preview site:

```
https://github.com/tannc28/sheets2anki/blob/main/examples/sheets2anki-examples.xlsx
```

Each sheet becomes its own deck, `s2a_sheets2anki-examples::<sheet name>`, with
its own columns, its own settings row and its own note type. That is the same
thing that happens to a Google Sheets file with several tabs.

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

### 01 Basic

`ID`, `Front`, `Back`, nothing else — one word each in English, Chinese,
Japanese, Korean, German and Spanish, answered in Vietnamese. No settings row,
and no `SYNC` column, which means **every row syncs**: the column is opt-in
gating and its absence is not "nothing syncs". The first content column is the
front of the card and the rest are the back, so this sheet needs no
configuration at all.

`Front` and `Back` are *your* names for those columns, not the add-on's — the
same sheet works with `Term`/`Definition` or `Từ`/`Nghĩa`. And nothing here knows
what Korean is: a language is only ever the content of a cell. Vocabulary is
simply the shortest way to show a deck working; every other sheet in this file
is something else.

### 02 Sync and subdecks

Adds the four reserved columns. `SYNC` gates each row — `yes`, `x`, `1`, `TRUE`
and `✓` all count, an empty cell and `no` do not. `SUBDECK 1` and `SUBDECK 2`
build the deck path a level at a time, and a row that leaves them empty stays in
the deck root. `TAGS` is split on either commas or semicolons.

### 03 Card layout

The first sheet with a **settings row** — row 2, marked by `#config` in the `ID`
cell. It moves `Pinyin` to the front, sets sizes (including `48px`, since the
`px` suffix is tolerated), and shows all three ways to write a colour:
`color=accent` follows the light/dark theme, `color=#c2410c` is a hex value and
`color=teal` is a CSS name. `Note` is behind a `hint`, and `Source` is
`side=hide` — the field still exists on the note, it just is not rendered.
`#config align=left` is a deck-wide default; `align=right` on `Note` overrides it
for that column.

### 04 Reverse

`#config reverse` adds a second card *template on the same note type*, asking the
back and answering with the front. One row, two cards, scheduled independently.

### 05 Type the answer

`type=nc` on the Spanish column makes Anki draw an input box on the question and
diff what you typed against the field. `nc` drops diacritics from the
comparison, so *el arbol* is accepted for **el árbol** — but `ñ` is a letter
rather than an accent and still has to be typed.

### 06 Cloze

One column declares `cloze` and every deletion in it becomes its own card. `z02`
carries `c1` and `c2`, so that row makes two. The declaration is per *sheet*, not
per row, because the note type has one template set — and Anki renders a clozed
field holding no deletion as nothing at all, which is why only the declared
column is wrapped.

### 07 Images

`image` says the cell holds a bare URL, and `size=320` caps its width. The
picture is the first content column, so it is the prompt: see the thing, recall
the word.

### 08 Audio

`audio` renders `<audio controls>` — listen, then reveal the characters, the
pinyin and the meaning. The recordings are Wikimedia Commons `.ogg` files, which
play on Anki for desktop; a sheet meant for iOS is better off with `.mp3`.

### 09 Video

Every link form the add-on rewrites, one per row: a full `watch?v=` link, a
`youtu.be` short link, a `/shorts/` link, a link that is already an `/embed/`
one, and a direct video file. The rewrite happens at sync time, before the note
is written, because a card template can substitute a field but cannot transform
one. `hint` on a media column puts the player behind a disclosure rather than
behind Anki's `{{hint:}}`, which would only reveal the URL.

### 10 Speech

`tts=zh_CN` makes Anki speak the field with an installed voice. The language code
must be the full form: Anki compares it against a voice's language *exactly*, so
a bare `zh` matches nothing and plays silence. `#config speed=0.9` sets the
deck-wide rate and the `Slowly` column overrides it with `speed=0.5`.

### 11 Chinese writing

The character-writing deck, and the sheet that shows what these directives are
for. The prompt is the meaning and the pinyin; `type` on the `Hanzi` column asks
you to write the character and diffs it stroke for stroke; the answer then shows
the character large, speaks it, and hides a **stroke-order animation** behind a
`hint` so you only look when you did not know. `SUBDECK 1` splits it by HSK
level and `TAGS` adds the same as tags. 25 characters.

### 12 Japanese furigana

`furigana` renders `漢字[かんじ]` as ruby text above the kanji. Anki's own filter
does the work; the settings row only decides which column goes through it.

### 13 Any language headers

The headers are `汉字`, `拼音`, `释义`, `例句`. Only `ID`, `SYNC`, `SUBDECK n`
and `TAGS` are reserved — every other header becomes a note field named exactly
as written, in whatever script your subject calls for.

### 14 Everything

All fifteen reserved and content roles at once: three `SUBDECK` levels, `TAGS`,
`SYNC`, a picture, a recording, a video, `tts` with a `voices=` preference,
`type=nc`, a hidden column, deck-wide `align`, `speed` and `reverse`. It is also
the sheet the preview site opens on. Several rows leave `Picture` or `Clip`
empty on purpose: an empty cell renders nothing at all rather than an empty box,
because every field is wrapped in Anki's `{{#Field}}` guard.

### 15 Edge cases

**This sheet is wrong on purpose.** Every mistake in it produces a named warning
rather than silence, and the preview site lists them all — an unknown key, a
misspelled `colour`, a `side` that is not a side, a font size and a media width
out of range, a short `tts` code, `speed=3`, a bare `label` with no value, two
columns both claiming `cloze`, `image` and `audio` on one column, and `tts`,
`bold` and `furigana` on a column that holds a URL. The rows are wrong too: one
has no `ID`, one repeats an `ID` that is already used, one is not marked for
sync, one points its video column at a *channel* — which cannot be embedded, and
says so — and one at a Google Drive link whose id is a placeholder, so the
rewrite is visible even though nothing will play.

Nothing here is clamped or quietly dropped. A refused value is refused, and the
add-on says which column and why.

## Where the media comes from

Every picture, recording and stroke-order animation is a
[Wikimedia Commons](https://commons.wikimedia.org) file, linked at its own
address. Nothing is copied into this repository and nothing lands in your
`collection.media`, so these cards need the network to draw — which is true of
any media column, not just these.
