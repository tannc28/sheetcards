# 📋 CHANGELOG - SheetCards

## Complete History of Updates and Modifications

---

## ✨ **v6.23.0** - August 2026 *(Feature)*

### Five directives: sort, math, code, font, and the two writing directions

**`sort`** names the column Anki lists notes under in the browser and sorts a deck
by. This one is really a fix: the default is the note type's first field, which
here is `ID`, so every deck this add-on made listed as `w01, w02, w03` — a list of
nothing. Now `sort` on the word column lists the words. One column per sheet, and
it is drawn on the card exactly as it was before; a `subdeck` column may also be
the sort column, because filing a note and listing it are both about the note.

**`math`** makes the cell a formula. Anki already ships MathJax, so this loads no
library at all — it is the delimiters and nothing else. Bare `math` is inline,
`math=block` is the centred display form. Write TeX in the cell without the
delimiters.

**`code`** makes the cell source code: kept exactly as typed, in a monospace block
that scrolls rather than widening the card, coloured by language with
`code=python`. The colouring library is loaded into the card the same way the
writing box loads HanziWriter. No highlight theme comes with it — the colours are
ours, in both light and night mode, because a ready-made theme paints its own
light background and would sit on a dark card as a white rectangle.

**`font`** picks the typeface. `sc`, `tc`, `jp`, `kr` load a Noto CJK face; any
other name is a family the machine already has. This exists because of Han
unification: `直`, `骨` and a few hundred others are one code point with a
different *shape* in Chinese and Japanese, so a machine with a single CJK font
draws a Chinese deck in Japanese shapes and nothing on the card can say otherwise.

**`rtl`** and **`vertical`** are the two writing directions HTML has and a sheet
could not previously ask for: right to left for Arabic, Hebrew and Persian — which
also right-aligns the column unless `align` says otherwise — and top-to-bottom,
right-to-left for the way Japanese is set in a book, with Latin words inside the
line kept upright. A column has one direction; asking for both keeps `rtl` and
says so.

Three new sheets in the example workbook show them: `21 Formulas & code`,
`22 Arabic` and `23 Vertical text` — and the Chinese writing sheet now asks for
`font=sc`, which is exactly the deck the font problem was ruining.

The preview page draws all five. It runs a card's scripts already, so `code`
colours itself there; MathJax is not in a browser, so the page brings it in when
the card it is drawing has a formula on it.

---

## 🐛 **v6.22.1** - August 2026 *(Fix)*

### A furigana column was read aloud with its brackets in it

`furigana` and `tts` on the same column produced `{{tts ja_JP:Word}}`, and Anki
hands the voice the field's *text* — which for a furigana cell is
`日本語[にほんご]`. So the voice said the word, then the bracket, then the word
again as kana. On a sentence it was worse: every annotated word was read twice.

The tag is now `{{tts ja_JP:kana:Word}}`, which is what Anki's own manual uses for
Japanese. Checked against a real collection:

| template | what the voice is given |
| :--- | :--- |
| `{{tts ja_JP:Word}}` | `私[わたし]は 日本語[にほんご]` |
| `{{tts ja_JP:kana:Word}}` | `わたしはにほんご` |

`kana:` rather than `kanji:` on purpose. The sheet wrote the reading down so that
nothing would have to guess it, and an engine guesses wrong on exactly the names
and rare readings someone bothered to annotate.

A cell with no brackets in it goes through the filter unchanged, so a column where
only some rows are annotated still speaks correctly — and nothing changes for a
column that never asked for furigana.

The Japanese sheet in the example workbook now has a voice, so the fix has
something to be heard on.

---

## ✨ **v6.22.0** - August 2026 *(Feature)*

### The unsorted pile is automatic, and the directive is gone

v6.21.0 added `#config unsorted=<name>`. It is removed again, one version later,
and what it did now happens by itself:

**A row that fills in no subdeck lands in `Unsorted`.** No key, nothing to switch
on. A sheet that sorts its rows into sub-decks is already saying that a row belongs
somewhere, so the row that names nothing has an answer either way — and a directive
for it could only ever have been a way to ask for those rows to stay loose among the
folders, which is not something anyone wants twice.

The name is fixed and in English, because that is the word every spreadsheet and
mail client already uses for the same pile.

Two things it deliberately does not do:

- **A sheet with no sub-decks at all is untouched.** There is nothing to be unsorted
  from, so a two-column vocabulary sheet keeps every note in the deck itself instead
  of finding all of it moved into a folder.
- **A row that fills in *some* level is not unsorted** — a blank outer level with a
  deeper one filled in still names a deck of its own.

The tag mirrors the deck as always, so the pile is searchable as
`sheetcards::unsorted`. Nothing is drawn on the card: where a note is filed and how
a card looks stay separate jobs.

If you are upgrading from a sheet that had rows sitting in its own deck beside the
sub-decks, those rows move into `Unsorted` on the next sync. Anki keeps a card's
scheduling when it changes deck, so nothing is relearned.

---

## ✨ **v6.21.0** - August 2026 *(Feature)*

### A sheet can name the deck for the rows that name none

> Superseded by v6.22.0: the pile is automatic now and this key no longer exists.

A row that leaves every `SUBDECK` cell empty was never unfiled — Anki has no such
state. It landed in the sheet's own deck, which is a real deck sitting beside the
sub-decks. But that does mix the rows that were filed with the rows that were not,
and there was no way to say where the second kind should go.

Now the settings row can name it:

```
#config unsorted=Chưa phân loại
```

The bare flag — `#config unsorted` — calls the deck `Unsorted`. A value is taken
exactly as written, with surrounding quotes stripped so a name with a space in it
can be quoted. Nothing is invented: without the key, a sheet behaves exactly as it
did before, because a name the add-on chose for you would arrive in English in a
deck list that is not.

It is a deck-level setting and stays out of the card entirely. The tag mirrors the
deck as always, so the pile is searchable as `sheetcards::unsorted` too. A row that
fills in *some* level is not unsorted — a blank outer level with a deeper one filled
in still names a deck of its own.

`02 Sync and subdecks` in the example workbook now shows it, and the editor lists it
with the other deck-wide directives.

---

## ✨ **v6.20.0** - August 2026 *(Feature)*

### `sakura` now has the flowers in it

v6.19.0 shipped `theme=sakura` as a palette, and a palette is not what the name
promises. Anyone reading `theme=sakura` expects blossoms, and got pink.

Now the card is strewn with them: five-petal flowers and a few loose petals
drifting between, in the theme's own colours, faint enough to stay wallpaper
behind the word being learned.

They cost nothing to show. The pattern is an SVG written into the card's
stylesheet, so there is no file to fetch, nothing lands in `collection.media`,
and a card on a plane looks exactly like a card at home. The theme's background
colour stays underneath the pattern rather than being replaced by it, so a client
that refuses the drawing is still left with the theme.

A theme that names no petals is still just a palette — the flowers are a property
of the theme, not of themes in general.

---

## ✨ **v6.19.0** - August 2026 *(Feature)*

### `theme=sakura` — a colour for the whole card

The settings row could already colour one column at a time. It could not say what
the card as a whole should look like, so every card came out black on white however
carefully its columns were styled.

A new deck-wide key names a palette:

```text
#config theme=sakura
```

`sakura` is soft cherry-blossom pink with a deep plum text, and it is the first of
these — more palettes are a table entry, not a feature.

A theme is not just a background. It also redefines what `color=muted` and
`color=accent` mean, so a column written `color=accent` follows the sheet's palette
instead of staying the same blue on every card. Styling a column and choosing a
theme therefore cannot drift apart.

Each palette carries **two** versions, one light and one dark, because Anki decides
at review time which one a card is drawn in. A single set of colours would have left
one of the two unreadable — the same reason `muted` and `accent` existed at all.

What it does not colour: on the desktop the top bar and the answer buttons are
Anki's, not the card's, and they keep Anki's own colours. On AnkiDroid and
AnkiMobile the card fills the review screen, so the tone carries further.

An unknown name is refused by name in the warnings and the card keeps Anki's
colours, rather than being painted in something nobody asked for.

---

## 🐛 **v6.18.0** - August 2026 *(Fix)*

### A deck level is a deck level

`subdeck=n` shipped in v6.15.0 also rendering the column on the card. v6.17.0 made
that need an explicit `side=`. Both were the same mistake at different sizes, and
this removes it: **a `subdeck=n` column is not part of the card at all.**

Where a note is *filed* is a bigger thing than how one card looks. A directive
working at that level has no business reaching down into the card, and the reserved
`SUBDECK n` columns never have — so there is one rule here rather than two.

Every card key written on such a column is now refused **by name** in the warnings:
`side`, `size`, `color`, `align`, `tts`, `voices`, `speed`, `label`, `type`, `bold`,
`italic`, `hint`, `furigana`, `cloze`, `draw`. The column is still a field on the
note — the value is kept, searchable and exportable — it is simply never drawn,
styled or spoken.

Nothing is lost by not printing it: the note is *in* the deck named after that
value, and Anki shows the deck. Printing it on the card would say twice what the
deck tree already says once. If you want it on the card as well, that is a second
column — a decision for the sheet, not for the settings row.

---

## 🐛 **v6.17.0** - August 2026 *(Fix + feature)*

### `subdeck=n` no longer puts the column on the card

Superseded by v6.18.0 above, which removes the `side=` escape hatch this release
added. `subdeck=n` shipped in v6.15.0 rendering the column as a field as well, on
the reasoning that a value wanted in the deck name *and* on the card should not have
to be typed twice. The first person to use it asked why their subdeck column had
appeared on the back of every card, which was the right question.

### `side=hide` + `tts` — heard without being read

`tts` says speak this column; `side=hide` says do not draw it. A column that says
both is asking to be heard and not read, which is what a listening card is: the
sentence said aloud with nothing on screen to read it off. Hiding a column used to
take its voice with it, and there was no way to ask for one without the other.

It is spoken on the side it would have been drawn on, and the reverse card swaps
that along with everything else. `10 Speech` in the example workbook now uses it —
its slow repeat is heard and no longer printed as a duplicate line of text.

---

## ✨ **v6.16.0** - August 2026 *(Feature)*

### Every block on a card now names the column it came from

```html
<div class="sc-back" data-sc-col="Pinyin">…</div>
```

Anki's own classes say only which *side* a block is on, so nothing in a finished card
connected a piece of it back to the sheet. Two things follow from fixing that:

- **A note type's CSS can target one column**: `[data-sc-col="Pinyin"] { … }`, for
  the rare thing the settings row does not cover.
- **The preview can point at a field**, which is what the rest of this release is.

### The preview says what each column turned into, and shows you where

Panel 1 lists the sheet's headers. Tap one and it opens: the role it ended up with,
every directive the settings row gave it, the value *this row* holds in it, and any
warning naming it — and at the same moment the thing it made lights up wherever that
thing is. A field is ringed inside the card and scrolled into view; a `SUBDECK`
column lights the branch this row lands in; `TAGS` lights the tags; `ID` and `SYNC`
light the count they are responsible for.

- A header written twice is listed twice, the later one struck through and told it is
  ignored. Saying which of the two was honoured is the only reason to list both.
- The role is read off the plan the parser produced. The rules for what counts as
  `SUBDECK 2` live in `column_model.py`, and a second copy in JavaScript would
  eventually be a second answer.
- The flash and the scroll happen only on the click that opens a column — a repaint
  from picking a row would otherwise blink a panel nobody was looking at.

**Also fixed:** the preview was only ever sent the values of columns that become
fields, so opening `SYNC`, `TAGS` or a `SUBDECK` column reported an empty cell — a
lie about the sheet, told in the one place built to answer questions about it.

**And a guard that should have existed already:** nothing in the test suite loaded
`site/app.js`, so a syntax error in it was invisible — the page rendered its markup
and did nothing, with no error a user would ever see. `tests/test_site_syntax.py` now
parses every site module with `node --check`.

---

## ✨ **v6.15.0** - August 2026 *(Feature)*

### 🗂️ `subdeck=n` — a column that files the note *and* stays on the card

The sheet decides everything about a deck except one thing: the deck path had to come
from columns the add-on named itself, `SUBDECK 1`, `SUBDECK 2`. Those are reserved, so
they never become fields and never appear on a card — which meant a value wanted in
both places had to be typed into the sheet twice, once to file the note and once to
show it.

Now any column can say which level of the path it is, from its own settings cell:

```text
ID       Level                Word      Meaning
#config  subdeck=1; size=14   size=48
w01      HSK 1                写        to write
w02      HSK 2                山        mountain
```

→ `sc_{file}::{sheet}::HSK 1`, and `Level` is still a field: style it, speak it,
hide it with `side=hide`. Nothing about the old way changed — a sheet with
`SUBDECK n` columns and no settings row behaves exactly as it did.

- **The number is the level**, so the order comes from the numbers rather than from
  where the columns sit, which is how `SUBDECK n` has always worked.
- An empty cell drops that level; two columns cannot claim the same level; a column
  holding a URL cannot be a deck level at all. Each of those says so.
- **A sheet using both is overruled by the settings row**, and the warning names the
  reserved columns being ignored — a deck quietly not appearing is not something
  anyone thinks to go looking for.

### Fixed along the way: a note type rebuilt from the cache lost its cloze

`cloze_field`, `type_field` and now `subdeck_columns` are *derived* from the per-column
settings rather than stored, and `sync_config.from_dict` never derived them. A note
type rebuilt from the cache — which is what happens when templates are refreshed
outside a sync — therefore came back with no cloze column, producing a cloze template
with no `{{cloze:}}` in it, which Anki refuses to save. There is now one function that
works these out, `sheet_config.resolve_roles()`, and both readers call it.

---

## 🐛 **v6.14.1** - August 2026 *(Fix)*

### The `draw` question showed the answer

HanziWriter's outline is not a faint guide line — it is the **whole character**, drawn
in a pale colour. On the side that is *asking*, that is the answer sitting in the box
waiting to be traced over, which is a completely different exercise from writing it
from memory. The question is now an empty square; the answer still animates the
correct strokes over its outline, which is where an outline belongs. Getting a stroke
wrong twice still lights up where the next one starts.

Checked by driving a real stroke through a real card in a headless browser, in the
same sandbox the preview site puts a card in: the box takes the stroke, marks it and
renders it as the proper glyph.

---

## ✨ **v6.14.0** - August 2026 *(Feature)*

### ✍️ `draw` — write the character, do not type it

`type` asks you to spell an answer on a keyboard. **`draw` asks you to write it**, one
stroke at a time, and marks each stroke as you make it. It is the thing a keyboard
cannot test, and the reason people study Chinese with paper beside the computer.

```text
ID       Meaning   Pinyin   Draw
#config            side=front   side=front; draw; size=260
```

- **Which of its two jobs the box does is decided by the side the column lands on.**
  On the question it starts empty and takes your strokes, showing a hint after two
  misses; on the answer it animates the correct strokes. There is no second directive
  to keep in step with the first — the column already says where it is.
- **A cell can hold more than one character**: `你好` gives two boxes in order.
- `size` is the side of the square rather than a font size, so it takes the same
  1–2000 px range a picture does. `color` still applies — the strokes are drawn in
  whatever colour the box inherits, so `color=accent` follows the light/dark theme.
  `bold`, `italic` and `furigana` have no text to act on and say so; `tts` still
  works, because there is a character to read aloud. `draw` is refused on a media
  column (it holds an address) and on the cloze column (its text *is* the question).

**What it costs.** The stroke data and the marking come from
[HanziWriter](https://hanziwriter.org) over the network, loaded into the card rather
than shipped with the add-on — the add-on is not what runs it, your Anki is. So a
`draw` column needs the network exactly as a media column does, and a client that
refuses remote scripts shows a dashed box with the character in it instead of
nothing. Verified on Anki for desktop; not tested on AnkiDroid or AnkiMobile.

### The example workbook gained a sheet, and its numbering moved

`12 Chinese drawing` joins the tour where it belongs — after `11 Chinese writing`,
which does the same drill on a keyboard — so `12 Japanese furigana` through
`15 Edge cases` each moved up one. **A deck remembers its sheet by name**, so anyone
who connected the workbook before this has to connect it again to pick the renamed
sheets up. Sixteen sheets now.

---

## 🐛 **v6.13.1** - August 2026 *(Fix)*

### The `.xlsx` source could not actually be typed in

`Add New Remote Deck` (`Ctrl+Shift+A`) still tested the pasted URL for the Google
host and answered *"Please enter a valid Google Sheets URL"*. Everything behind it —
the download, the reader, the deck naming, the sync — had handled a spreadsheet file
at a plain address since v6.12.0, but the one dialog that connects a deck refused to
pass it on, so the feature existed and could not be reached. Pasting the example
workbook's own link, which the README hands you, was rejected.

- The dialog now accepts a Google Sheets link **or** a link ending in `.xlsx` /
  `.xlsm`, and its help text, placeholder and refusal message all say so.
- **A file is now checked against the decks already connected.** The duplicate check
  asked for a spreadsheet id, which a file does not have; the resulting error read as
  "not a duplicate", so a file already connected could be connected a second time and
  sync the same rows twice.

`tests/test_add_deck_dialog_urls.py` covers the gate itself rather than the URL
helpers underneath it — the helpers were never wrong.

### The preview site is three columns

v6.13.0 gave the card a pane of its own opposite the deck, and the card spent it on
empty ground: a card is a narrow thing however much room it is given, so a 46rem card
sat in a 70rem stage with two hundred pixels of nothing either side, while the row
list — the surface the work actually happens on — was squeezed against it.

- **Source, Deck, Card, side by side.** Each is something you look at while changing
  one of the others: switch the sheet and the deck tree and the card both answer
  without anything leaving the screen. The card is capped rather than stretched, and
  the two columns in front of it are sized for the form and the list they hold.
- **The whole top bar is gone.** The link field, the sheet picker and the deck name are
  column 1 rather than a band above everything, so nothing is spent on a question
  already answered and nothing has to fold on a desktop to get the room back.
- **On a phone the three columns stack and each folds to its header**, which says what
  is inside it (`demo · 14 Everything`, `6 of 7 rows sync · 3 decks`, `Row 3 — 北京`).
  The first folds itself once a sheet is loaded, and tapping a row folds the list away
  and brings the card up — that is the moment you stop browsing and start reading.
- Two layout defects went with it: a grid item's `min-height: auto` let the card column
  grow past the bottom of a window that does not scroll, putting the row list out of
  reach with no scrollbar anywhere; and a filled `button:hover` default out-specified
  every quiet button's own hover, so row list entries turned solid accent under the
  pointer. The filled look is opt-in now.

---

## ✨ **v6.13.0** - August 2026 *(Feature)*

### 📚 The example sheet lives in this repository now

The docs, the preview site and *Import Test Deck* used to point at a Google Sheet
nobody working on the add-on could edit. It described a schema the add-on had
outgrown, and there was no way to notice: nothing in the repository knew what was in
it. The examples are now a file here — [`examples/`](../examples/) — and everything
points at the same one:

```text
https://github.com/tannc28/sheetcards/blob/main/examples/sheetcards-examples.xlsx
```

**Fifteen sheets, one deck each, ordered from the smallest sheet that works to every
directive at once**: the reserved columns, the whole settings row, cloze, typed
answers, images, audio, every video link form, text-to-speech, furigana, headers in
Chinese, a Chinese character-writing deck that asks you to type the character and then
shows the stroke order, and a last sheet that is **wrong on purpose** so every warning
the add-on can produce has something to point at.

- **The grids live in `SHEETS` at the top of `scripts/build_examples.py`** and the
  workbook is generated from them, so a changed setting shows up in review as a changed
  line rather than as a changed ZIP. `python scripts/build_examples.py --check` and
  `tests/test_examples.py` both fail if the file and its source drift apart.
- **`tests/test_examples.py` also fails when a settings-row key has no example**, which
  is what makes this a contract rather than a snapshot: a directive added to
  `sheet_config` without one is caught in the commit that adds it.
- **The preview site opens on the workbook's `14 Everything` sheet**, and its sheet
  picker walks back through the rest.
- The stale `sample data/` directory, which still described the fixed-column schema
  removed several versions ago, is gone.

### 🎨 The preview site is laid out for the person using it

The page was dressed as a console — ten font sizes down to 10.5px, monospace on the
inputs and the headings, nine controls crammed into one 56px bar, and no `<label>`
anywhere. It read as a debugger, and the people it is for are learning a language.

- **One type scale, six steps, and one sans-serif family** for everything the page
  says. Monospace is kept for the strings that really did come out of a spreadsheet:
  column names, ids, tags, template source.
- **Three panels, one job each, and every one of them folds.** *Source* — where the
  sheet comes from. *Deck* — what it makes. *Card* — what one card looks like. Each
  collapses to a header that says what is inside it (`demo · 14 Everything`, `6 of 7
  rows sync · 3 decks`, `Row 3 — 北京`), so a folded panel still tells you something.
  Panel 1 folds itself as soon as a sheet is in hand; on a wide screen, folding 2 or 3
  hands the whole window to the other.
- **The row list is the point, so it gets the room.** An Anki card is a narrow thing
  however much room it is given, so the card column is capped at 46rem and the width
  goes to the list you actually work in. Inside panel 2 the deck tree and the list both
  give way when the window is short, instead of a five-level hierarchy leaving the list
  two rows.
- **The page is mobile-first now, not a desktop layout with a fallback.** On a phone the
  three panels simply stack and the page scrolls; tapping a row folds the list away and
  brings the card up, because that is the moment you stop browsing and start reading.
  The sheet picker sits in panel 1's header rather than its body, so it survives the
  panel folding away.
- **Warnings are a banner above the working area.** They used to be a small count on a
  collapsed drawer at the bottom of a scrolling sidebar — the most actionable thing on
  the page, hidden behind the most clicks.
- **Every control has a visible label**, the link field is a real form (so Enter
  submits and a phone offers a "go" key), and the deck name applies when you commit it
  rather than waiting for another Preview.
- **A row is named by the first front column that reads as words.** When the front was
  a picture, the list was eighty rows of `https://upload.wikimedia.org/…`.
- The column-roles and settings-row report is gone. It was reference material, and
  `ANALYZER` in `app.js` no longer computes what only it read. The four-sentence
  paragraph under *Download .apkg* is gone the same way — `README.md` carries the
  caveats, and a control most people press once should not come with an essay.
- Checked against the Web Interface Guidelines: skip link, an `<h1>`, `color-scheme`
  and `theme-color` for both themes (Windows dark mode used to render the sheet picker
  white), `aria-label` on the icon-only row buttons, `overscroll-behavior`,
  `touch-action`, safe-area insets on notched phones, and a real narrow layout rather
  than a wrapped control bar.

---

## ✨ **v6.12.0** - August 2026 *(Feature)*

### 🔗 A deck can be an `.xlsx` at a plain address

Paste a link ending in `.xlsx` or `.xlsm` — a file in a GitHub repository, or on any
https host — and it is read exactly as a Google Sheet is: one deck per sheet, the same
reader, the same settings row, the same note types. Only fetching the bytes differs.

- **GitHub's own address works.** The `.../blob/main/decks.xlsx` link a browser shows
  you serves an HTML page, not the file; it is converted to the raw address, which also
  happens to send `access-control-allow-origin: *`, so the preview site can read it too.
- **A file has no spreadsheet id**, so its address is hashed into a stable one
  (`file_…`). The browser address and the raw address of one file give the same id, so
  connecting from either is the same deck rather than two.
- The deck is named after the file: `sc_english::vocab`.

### 🔒 The address check changed shape

The add-on used to refuse anything that was not a Google host. It cannot any more, so
the rule is what is left once arbitrary hosts are allowed:

- **https only** — no `http`, no `file://`, no other scheme;
- **every address the name resolves to must be public.** Resolving first and checking
  the answers is the point: a hostname belongs to whoever owns it, and pointing
  `internal.example.com` at `10.0.0.1` is the ordinary way this gets abused.

This matters because Anki runs on your machine, inside your network. `192.168.1.1`,
`127.0.0.1` and the cloud metadata address `169.254.169.254` are all refused by name in
the tests.

**A file is a file.** A Google Sheet you edit is edited; an `.xlsx` has to be uploaded
again before a sync sees it. For anything you change often, a Sheet is still the better
home.

---

## ✨ **v6.11.0** - August 2026 *(Feature)*

### 🗂️ A sheet's deck is a subdeck of its file

One spreadsheet is one collapsible branch of the deck list rather than a scatter of
top-level decks:

```
sc_my-vocab-sheet
   vocab                 56 notes · Word, IPA, POS, Meaning, Collocation, Example
      2026-08-11
   grammar               11 notes · Original, Corrected, Fixes
      2026-08-11
```

A subdeck is a deck in every other respect — its own options, its own study queue, its
own row in the sync dialog — and **each sheet keeps its own note type**, holding only
that sheet's columns. Note types are named from the sheet rather than from the deck
tree, so nesting the decks does not make the sheets share one.

(v6.10.0 shipped these as flat top-level decks, `sc_vocab`; the release below
describes the rest of what it changed.)

---

## ✨ **v6.10.0** - August 2026 *(Feature + Fix)*

### 🚨 Every deck of a file was syncing the same sheet

The one that mattered. `sync` validated the deck's URL and then downloaded from what
the validator *returned* — an `/export?format=tsv` URL, which has no room for a
fragment, so `#sheet=grammar` was gone. A URL naming no sheet falls back to the file's
first sheet, so **both decks downloaded `vocab`**: the second deck came out with the
first one's columns, its note type and its rows, and nothing reported an error.

The sync now downloads from the deck's own URL. A test reads `sync.py` for that call,
because this failure is silent — no exception, no warning, just the wrong rows.

It was invisible to the previous release's testing because every check went through
the download router directly. The sync's own entry point was the one path not
exercised, and it was the one that dropped the sheet.

### 🗂️ Decks are named `sc_{file}::{sheet}`

The `SheetCards::` parent deck is gone — one less level, and the prefix is what keeps
synced decks apart from the ones you made yourself. A spreadsheet is one collapsible
branch and each sheet is a deck inside it:

```
sc_my-vocab-sheet
   vocab                      56 notes · Word, IPA, POS, Meaning, Collocation, Example
      2026-08-11
   grammar                    11 notes · Original, Corrected, Fixes
      2026-08-11
```

A subdeck is a deck in every other respect — its own options, its own study queue, its
own row in the sync dialog — and **each sheet keeps its own note type**, holding only
that sheet's columns. Note types are named from the sheet, not from the deck tree, so
nesting the decks does not make the sheets share one.

The name is now built in exactly one place (`tsv_model.deck_root_name`). It used to be
spelled out as an f-string in four modules, which is how v6.9.2's "vocab+" happened.

**This renames existing decks.** Anki's rename keeps the cards; the empty
`SheetCards` parent is left behind for you to delete.

### 🔧 Also

- The root deck options preset has nothing to attach to now and is a no-op; every deck
  still gets its options applied directly, as it already did.
- The **Tools** menu is still called SheetCards — that is the add-on's name, which
  only ever happened to be spelled the same as the deck prefix.

---

## 🐛 **v6.9.2** - August 2026 *(Fix)*

### The deck name lost Anki's own separator, and decks grew a "+"

A deck for one sheet is named `{file}::{sheet}`. The name sanitiser replaced every
`:` with `_` — reasonable for a filename, wrong for a deck name, where `::` is what
Anki puts between a deck and its parent.

So the deck the add-on **registered** was the flat
`SheetCards::my-vocab-sheet__vocab`, while the notes were **filed** under the nested
`SheetCards::my-vocab-sheet::vocab::…` — two deck trees for one deck, computed in two
different modules from the same name. Renaming one onto the other left Anki to
uniquify it, which it does by appending `+`, and the deck list showed a stray empty
`vocab+` and `grammar+` beside the real decks.

`::` is now kept. A lone `:` is still replaced, so a sheet called `morning: verbs`
cannot quietly forge a subdeck, and `< > " / \ | ? *` are still replaced as before.
A test now pins the registered name and the filed-under name to each other, since
they are built in separate modules and nothing else would notice them drifting.

---

## 🐛 **v6.9.1** - August 2026 *(Fix)*

### Three faults a real sync found, that no test had

Reported from an actual run of v6.9.0 that ended `0/2 decks synchronized`.

- **Every deck of a file was renamed onto the same name.** The automatic name sync
  recomputes a deck's name from its URL on *every* run, and that name left the sheet
  out — so `…::vocab` and `…::grammar` both became `…my-vocab-sheet`, collided, and
  were pushed apart again as `#conflict1`. Every sync, for ever. The name now carries
  the sheet, and two sheets can no longer land on one name.

- **A Cloze note type was built for sheets that never mentioned cloze**, and Anki
  refuses it: *"Expected to find '{{cloze:Text}}' or similar on the front and back of
  the card template."* That one error failed the whole sync. Cloze is a sheet-level
  choice — a column declares it — and with no such column there is no `{{cloze:…}}` to
  put in the template and nothing that needs the model, since note routing already
  keys off the declared column. It is no longer provisioned unless a column asks.
  **This one predates multi-sheet**: any sheet without a `cloze` directive hit it.

- **An uploaded spreadsheet brought its file extension into Anki**, giving decks like
  `SheetCards::my-vocab-sheet.xlsx::vocab`. A Google Sheets document has no
  extension; it is left over from the file it was uploaded from, and Drive keeps the
  name it arrived with.

---

## ✨ **v6.9.0** - August 2026 *(Feature)*

### 📚 One Google Sheets file, one deck per sheet

- Paste a file's link once and **every sheet in it becomes its own deck**, named
  `SheetCards::{file}::{sheet}`, each with its own columns, settings row and note
  type. One spreadsheet can now hold a whole collection. `Ctrl+Shift+S` lists one row
  per sheet with no change to that dialog — it lists connected decks, and now there
  are more of them.
- Until now a file could only ever be one deck: a deck is identified by its URL, and
  every sheet of a file shares one URL. The sheet's name is now part of that identity.
- **A sheet with no `ID` column is skipped and named**, rather than the whole file
  being refused. A file people actually keep has drafts and notes in it beside the
  vocabulary. Hidden sheets are skipped too — hiding a sheet is how you put it away.
- **A deck remembers its sheet by name, not by position**, so reordering the tabs
  does not reassign decks. A *renamed* sheet stops being found, and the sync says so
  and lists the names that do exist — better than silently syncing a different sheet
  into a deck full of notes.
- **Existing decks are untouched.** A deck connected before this keeps the exact key
  it had and keeps syncing the file's first sheet. Connect the file again and that
  deck adopts that sheet — keeping its notes, review history, options and note types
  — while the other sheets join it as new decks.
- The whole file is downloaded once per sync run and shared by every deck in it, so
  five decks from one spreadsheet are five decks' work but one request.
- The preview site takes the same path, so the sheet picker it already had for
  uploaded files now works for a pasted link — and what it previews is what the
  add-on syncs.

### 🔧 Fixed

- **Two lookups would have made per-sheet decks unusable**, both by resolving a URL to
  the bare spreadsheet id instead of the deck's key: choosing decks in the sync dialog
  matched nothing and the run reported success over an empty list, and disconnecting a
  deck found nothing to disconnect. Caught by running the flow end to end rather than
  by the type checker — there was nothing wrong with the types.

---

## ✨ **v6.8.0** - August 2026 *(Feature)*

### 📄 The preview reads uploaded files, not only links

- **Upload a file** on <https://tannc28.github.io/sheetcards/> — or drag one onto the
  page — reads `.xlsx`, `.xlsm`, `.csv` and `.tsv`. For a private sheet, a draft that
  is not in Google Sheets yet, or cards kept in Excel, there was previously no way to
  see what the add-on would make of them.
- **A workbook's tabs each become their own deck.** A file with more than one tab gets
  a picker beside the button, and the deck is named after the tab rather than the file
  — fourteen tabs named after the file they arrived in would download as fourteen
  indistinguishable packages.
- The file is read in the browser by Pyodide. There is no server, and nothing is
  uploaded anywhere.
- **A whole number keeps its digits.** Google stores `1` in an `.xlsx` as `1.0`, and
  the ID column is the key a note is matched by — read literally, an uploaded workbook
  would have made a *second* set of notes beside the ones the same sheet syncs as a
  link. Verified the other way round too: the demo sheet as `.xlsx` and as Google's own
  TSV export build byte-identical notes.
- Dates come out as dates rather than as the serial number a spreadsheet stores, and a
  cell holding a newline or a tab survives into the parser instead of splitting its
  row.
- A file the page cannot read says so in a sentence — an `.xls`, or something merely
  named `.xlsx` — rather than a Python traceback.

### 🔧 Fixed

- `scripts/build_site.py` stopped with `IsADirectoryError` once anything had imported
  `site/workbook.py` and left a `__pycache__` beside it. It copies files only now, and
  checks that the uploaded-file reader actually reached the output — app.js fetches it
  at boot, so its absence would take the whole page down, not just the upload button.

---

## ✨ **v6.7.0** - August 2026 *(Feature)*

### 🎬 Video plays inline on a phone, by borrowing an origin

- v6.6.1 added a `referrerpolicy`; v6.6.2 replaced the frame with a link on mobile.
  Neither was what was wanted: a link opens the video *elsewhere*, and the point of a
  `video` column is a video on the card.
- The card now frames **`player.html`** on the preview site, and that page frames the
  video. The page is served over https, so the request that finally reaches YouTube
  carries a real referrer — which is the whole of what "Error 153" was complaining
  about. The video plays inline, on the phone, in the card.
- That page refuses anything that is not a YouTube, Vimeo or Google Drive video
  address. Without the check it would frame any address anyone put in a query string,
  under that domain.
- **The address is in the card template, not in your notes.** Templates are rebuilt on
  every sync, so changing or dropping this costs one re-sync rather than an edit to
  every row. A small link stays under the frame on mobile, so if the page is ever
  unreachable there is still a way to the video.

---

## ✨ **v6.6.2** - August 2026 *(Fix)*

### 🎬 A video column now works on a phone, by not being a frame there

- v6.6.1 added `referrerpolicy` to the frame. **It was not enough, and could not
  be:** AnkiMobile and AnkiDroid load a card from a `file://` origin, so there is
  no origin to send a referrer *from*, and YouTube keeps answering *"Error 153"*.
- The card now carries a frame **and** a link, and the stylesheet shows exactly
  one of them. Anki marks the mobile clients with a `mobile` class on the card, so
  there the frame is hidden and the link takes its place — tap it and the video
  opens properly, with no error box. On the desktop the frame still plays inline
  and the link stays hidden.
- The link is named by the column's `label` when the settings row gives one, and
  reads "▶ Watch the video" otherwise.

---

## ✨ **v6.6.1** - August 2026 *(Fix)*

### 🐞 "Error 153" where a video should be, on the phone only

- A `video` column played on the desktop and showed *"Error 153: Video player
  configuration error"* in AnkiDroid. The frame was loading fine — everything else on
  the card did too, image and TTS and hint and ruby — but a webview does not send an
  HTTP `Referer` the way a browser does, and YouTube refuses an embed that arrives
  without one.
- The card template now sets `referrerpolicy="strict-origin-when-cross-origin"`, the
  documented fix, and the preview's own card frame carries the matching
  `<meta name="referrer">`.
- **Correcting what v6.3.0 and the README said:** framed players are *not* "blocked on
  the mobile clients". They load. YouTube declines them on a referrer technicality,
  which is a different problem with a different fix, and saying otherwise sent anyone
  hitting it looking in the wrong place.

---

## ✨ **v6.6.0** - August 2026 *(Feature)*

### 📦 The preview builds an `.apkg`, in the browser

- A **Download .apkg** button on the preview site. Pyodide loads `sqlite3`, and
  `src/apkg.py` writes a real Anki package — legacy schema 11, read out of a file
  Anki itself exported rather than transcribed from documentation.
- **AnkiDroid and AnkiMobile import it directly**, so a sheet can reach a phone
  without the desktop app. Verified end to end: package built through the site's own
  bundle, then imported into a real collection — 9 notes, 18 cards, the full deck
  hierarchy, tags, furigana ruby, the TTS tag, the image and the YouTube frame all
  arriving intact.
- Only the packaging is new. Fields come from `plan.note_type_fields()`, templates
  from `build_templates()`, the deck path from `get_subdeck_name()`, tags from
  `build_tags()` — nothing about a card is decided twice.
- A note's guid is derived from its row `ID`, so **importing again updates rather
  than duplicates**; Anki applies the update only when the incoming note is newer,
  so ids are derived while `mod` comes from the clock. Both proved against a real
  collection in `tests/test_apkg.py`, which runs Anki in a subprocess because the
  suite's `anki` mock cannot tell a valid package from a broken one.

### ⚠️ What an import is not

- **It cannot delete.** Anki's importer never removes a note missing from the file,
  so a row deleted from the sheet lives on in the collection. That is the honest
  difference between this and a sync.
- **Uploading straight to AnkiWeb is not possible**, and was checked rather than
  assumed: no public API (Anki's own docs point to AnkiConnect instead), no CORS
  headers on any endpoint — a browser refuses before the request leaves — and
  AnkiWeb is a sync target for a collection, not a place where decks are created.

---

## ✨ **v6.5.0** - August 2026 *(Feature)*

### 🌐 The preview site speaks Vietnamese

- An **EN / VI** switch in the control bar. The choice is remembered, and a first
  visit follows the browser's own language, so nobody has to find the button.
- Switching is a repaint, not a reload: the sheet stays loaded and the row you were
  looking at stays selected.
- **What is deliberately not translated:** the warnings labelled *Settings row*.
  Those are the add-on's own words, produced by `sheet_config.py` running in the
  browser, and they are exactly what Anki will say at sync time. Translating them
  would make the preview say something the add-on never says — the one thing this
  page exists not to do. The panel says so. The page's *own* diagnostics — a cloze
  column that is not on the front, duplicate IDs — are page text and are translated.
- `tests/test_site_i18n.py` fails the build on a key that is missing a language, a
  `t()` call naming a key that does not exist, a string nothing uses any more, and a
  translation that takes fewer arguments than its English original.

---

## ✨ **v6.4.0** - August 2026 *(Feature)*

### 🎯 A sheet declares its cloze column — and the broken-card bug goes away

- New `cloze` directive. The column carrying `{{c1::…}}` says so once in the settings
  row, and **that column becomes the prompt wherever it sits**, with Anki making one
  card per deletion. Every other column renders normally beside it.
- This replaces per-row auto-detection, which is what produced the defect reported in
  v6.2.0: routing looked at *every* column while the template clozed only the *front*
  one, so a deletion in a later column gave a blank prompt and printed the raw markup
  on the answer. Verified fixed against a real collection — two deletions in the third
  column now yield two cards with a visible prompt.
- Declaring it also keeps the template a function of the settings row alone. A
  template that changed with your *data* could rewrite the note type mid-sync, and
  removing a template deletes its cards and their review history.
- A row with `{{c1::…}}` in a sheet that declares no `cloze` column is **reported**
  rather than silently turned into a card that shows the markup as text.

### ⌨️ Typed answers

- New `type` directive: Anki draws an input box on the question and diffs what you
  type against that column. `type=nc` ignores diacritics, so `shuxi` matches `shúxī`.
- One column per sheet, because Anki honours one `{{type:…}}` per card; a second is
  ignored with a warning. The box is not repeated on the `reverse` card, which asks
  the other direction. On a cloze sheet, `type` on the clozed column types the
  deletions themselves.

### ⚠️ Changed behaviour

- **A sheet is now a cloze sheet or it is not.** Previously a single sheet could mix
  cloze and basic rows. If you relied on that, add `cloze` to the column holding the
  sentences and keep the rest in another sheet.

---

## ✨ **v6.3.5** - August 2026 *(Fix)*

### 🔁 The preview stopped filtering what Anki would run

- v6.3.4 stripped `<script>`, inline handlers and `javascript:` addresses out of a
  cell before drawing the card. That was wrong: **a preview that behaves differently
  from Anki's webview is a preview that lies**, which is the one thing this page must
  never do. Cells now go onto the card exactly as written, script and all, because
  Anki runs them too.
- The consequence is stated plainly under **Sheet detail** rather than hidden:
  previewing a spreadsheet trusts it, the same way syncing one does. The card frame
  keeps `allow-same-origin`, which embedded players need in order not to render black.

---

## ✨ **v6.3.4** - August 2026 *(Fix)*

### 🐞 Embedded video was a dead black box

- A `video` column showed nothing on the preview site and could not be clicked. The
  card is drawn in a sandboxed frame, and **a nested frame inherits the outer
  sandbox flags** — without `allow-same-origin` the YouTube or Drive player is
  forced into an opaque origin, cannot reach its own storage, and renders black.
- The frame now carries `allow-same-origin`. That grant would let script in a cell
  reach the page, so cells are stripped of `<script>`, inline `on…=` handlers and
  `javascript:` addresses before the card is drawn. Anki itself would run that
  script; a preview looks at spreadsheets that are not always your own, so it does
  not. Everything else — markup, ruby, media, the page's own hint link — is
  untouched.

### 🗂 An even split, and the detail opens where you are

- The two panes are now **50 / 50**. A card is small; the left pane needed the room
  more than the card did.
- **Sheet detail** is a real button that opens a drawer *downward in the left pane*,
  so the card stays on screen while you look something up. It used to take the card
  away, which is the opposite of what a preview is for.

---

## ✨ **v6.3.3** - August 2026 *(Refinement)*

### 🗂 Two panes, and the reference material out of the way

- The middle column is gone. Columns, the settings row, the note types and the
  warnings were never the point of the page — they explain *how the sheet is
  configured*, which you look up when debugging and never again once you know the
  system. They now sit behind **Sheet detail** in the sidebar, with a badge when
  there is something to see.
- The card pane gained a tab bar the way Anki puts one beside a card:
  **front · both · back · template**. The generated template is a view of the card,
  not a separate document, so it belongs there rather than in a panel of its own.
- The left pane is navigation only — the deck tree, then the rows of whichever deck
  is selected, each row showing its prompt so it is recognisable without opening it.
- The footer explaining that the page runs the add-on's own Python through Pyodide
  is gone from every screen. It justified the architecture rather than telling you
  anything you needed while working; it now lives under **Sheet detail**, next to
  the rest of the "how does this work" material.

---

## ✨ **v6.3.2** - August 2026 *(Fix)*

### 🗂 The preview reads like Anki now

- Laid out as a tool rather than a page: a control bar, the **deck tree on the left**
  the way Anki puts it, the sheet in the middle and the card on the right — three
  panes that fill the window and scroll independently, so a wide screen shows the
  whole picture at once instead of a narrow column.
- Clicking a deck in the tree filters the rows to it, and the card navigation follows
  that selection. Each level counts everything beneath it.
- The status line now **spins while something is running** — starting Python,
  downloading the sheet, running the add-on's code — so a slow first load reads as
  working rather than as frozen.

### 🐞 The deck path was missing its root

- The tree showed `HSK4::Bài 1`, but every deck the add-on makes hangs under
  `SheetCards`, so the real path is `SheetCards::HSK4::Bài 1`. The constant now
  lives in the pure layer next to `TAG_ROOT` and `templates_and_definitions`
  re-exports it, so the preview and `determine_target_deck` cannot disagree again.

---

## ✨ **v6.3.1** - August 2026 *(Fix)*

### 🐞 The preview framed the address you pasted

- A `video` column previewed as an empty box on the site. The page rebuilt each row
  from the raw cells and never applied the rewrite the sync applies, so it framed the
  `watch?v=…` address — the one address YouTube refuses to be framed at. The card was
  fine; only the preview was wrong, which is the worse failure of the two: it accuses
  the sheet of a fault it does not have.
- Both halves now call one shared `tsv_model.apply_media_rewrites`, and a test reads
  `site/app.js` to make sure the page keeps calling it.

---

## ✨ **v6.3.0** - August 2026 *(Feature)*

### 🎬 `video` now takes the link from your address bar

- Write `video` in the settings row and paste whatever the browser shows —
  `youtube.com/watch?v=…`, `youtu.be/…`, a YouTube Short, a Drive share link, a Vimeo
  link, or a direct `.mp4`. The add-on turns it into the address of that site's own
  player as it syncs, and the card shows the player. One word covers every case, so
  nobody has to know which kind of link they are holding.
- A link copied at a particular moment keeps it: `youtu.be/ID?t=1m30s` becomes
  `…/embed/ID?start=90`.
- A link that names no single video — a channel, a playlist, a Drive folder — is left
  alone and **reported**, because framing one shows an error page where the video
  should be. An address already in `/embed` form is untouched, so re-syncing never
  rewrites what it just wrote and no row reads as changed for no reason.

### ⚠️ Changed behaviour

- A `video` column now renders an `<iframe>` (16 : 9, `size` sets the width) instead of
  `<video controls>`. This is what makes a YouTube or Drive link work at all; a direct
  `.mp4` still plays, because a frame pointed at a video file shows a player too.
- The rewrite happens **on the way into the note**, not at render time — a card template
  can substitute a field but cannot transform one, and YouTube refuses to be framed
  anywhere except its `/embed` path. So the note stores the player address, not the
  address you pasted. The sheet stays the source of truth: change the cell and the next
  sync rewrites it again.
- **Framed players are blocked on AnkiDroid and AnkiMobile.** They work on the desktop.
  Anything that has to be reviewable on a phone does not belong in a `video` column.

---

## ✨ **v6.2.0** - August 2026 *(Feature)*

### 🔎 Preview a sheet in the browser — <https://tannc28.github.io/sheetcards/>

- A static page that takes a Google Sheets link and shows what the add-on would make
  of it, before installing anything and without touching a collection: which column
  became `ID` / `SYNC` / `SUBDECK n` / `TAGS` and which became fields, every row's
  fate with the same counts the sync reports, whatever the settings row got wrong,
  the deck tree, the tags, and the card itself — front, back, reverse, cloze and
  media, with a TTS button that speaks through the computer's own voices.
- **It is not a second implementation.** The page loads the add-on's own
  `column_model.py`, `sheet_config.py`, `card_layout.py`, `tsv_model.py` and
  `errors.py` and runs them in the browser through Pyodide, so what it shows is
  computed by the code that will run at sync time. Only drawing the finished template
  as a picture is written for the page; in Anki that step belongs to Anki's renderer.

### 🧱 A pure layer, so the two can never drift

- New `src/tsv_model.py` holds the code that turns a sheet into notes — TSV parsing,
  `RemoteDeck` and its metrics, tags, cloze detection, row classification, deck and
  note-type names — with no Anki import anywhere in it. `data_processor.py` and
  `utils.py` re-export everything, so every existing import still resolves.
- `RemoteDeckError` moved to `errors.py`, where the add-on's exceptions live.
- `tests/test_pure_modules.py` runs the whole set in a fresh interpreter with `aqt`
  and `anki` deliberately absent, and `scripts/build_site.py` refuses to publish a
  module that reaches outside that set — so the preview cannot quietly stop matching
  the add-on.

### 🐞 Found by the new preview, documented here

- A row whose `{{c1::…}}` sits in a column that is **not on the front** produces a
  broken card: Anki renders a clozed field with no deletion as nothing, so the prompt
  comes out blank and the raw `{{c1::…}}` text prints on the answer. Confirmed against
  a real collection. Keep the cloze sentence in the first content column, or give its
  column `side=front`; the preview flags any row that trips this. A proper fix needs
  changes to how note types are provisioned and is not in this release.

---

## ✨ **v6.1.0** - August 2026 *(Feature)*

### ✨ Media columns
- Three new settings-row keys turn a column holding a bare URL into the element that
  plays it, instead of printing the address as text: **`image`**, **`audio`** and
  **`video`**. Written as `Picture` → `image; size=320`, the column renders as
  `<img src="…" style="max-width: 320px">`; audio and video always carry `controls`,
  because a sound the learner cannot replay is worse than no sound.
- `size` now means what it should for each kind: a font size on a text column
  (6–200px) and a width on a media one (1–2000px). It may be written before or after
  the kind — `size=480; video` works.
- Conflicting or meaningless combinations are reported rather than silently applied:
  two kinds on one column keeps the first; `tts` on a media column is removed, since
  it would read the URL out loud; `furigana` on one does nothing. `hint` still works,
  so a picture can hide behind a click-to-reveal link.

### ⚠️ Worth knowing
- These are **links**, so the media is fetched over the network: it will not appear
  offline, and mobile clients are stricter than the desktop about loading remote
  content. Anki's own design keeps media inside `collection.media`, which syncs and
  works offline — the trade for a tidier spreadsheet is a card that needs a
  connection.
- A YouTube page URL will not play in a `video` column; that needs an `<iframe>`,
  which you can still paste into a cell directly since a field's HTML renders as-is.

---

## 💥 **v6.0.0** - August 2026 *(Breaking — the sheet now declares the card)*

The spreadsheet already decided what a note contains. Now it decides how the card
looks and sounds too, in an optional second header row.

### ✨ The settings row
- If the cell under `ID` in row 2 begins with `#config`, that row is read as
  presentation directives and data starts at row 3. **Without the marker there is no
  settings row and row 2 is ordinary data**, so sheets written before this release
  keep working untouched.
- Each cell holds `key=value` pairs separated by `;`; a bare key is a switch; an empty
  cell means "use the defaults". Per column: `side` (front / back / **hide**), `label`,
  `size`, `color`, `bold`, `italic`, `align`, `hint`, `furigana`, `tts`, `voices`,
  `speed`. Deck-wide, after the marker in the same cell: `align`, `speed`, `reverse`.
- **Speech.** `tts=zh_CN` speaks a field through the operating system's voice — no
  account, no API key, offline, and it works on AnkiDroid and AnkiMobile. The **full**
  language code is required: Anki compares it against installed voices with an exact
  string match, so a bare `zh` would match nothing and play silently. The parser
  rejects short codes with a warning rather than guessing a region.
- **`hint`** renders a field behind Anki's native click-to-reveal link, and
  **`furigana`** draws a reading above the text (`推迟[tuī chí]`) — both are Anki
  filters, not markup this add-on invents.
- **`muted` and `accent`** follow the card's light/dark theme, because a hard-coded
  `black` disappears in night mode.
- **Typos are reported, not ignored.** `siz=48` or `color=notacolour` produce a warning
  naming the column, in the sync log and in the Card Layout window.

### 💥 Breaking
- **The Card Layout window is now read-only** (`Ctrl+Shift+C`, renamed *View Card
  Layout*). Layouts stored by v5 are no longer applied — the sheet is the only source
  of presentation. Two places editing one setting is precisely how this add-on ended up
  with a Timer dialog whose setting nothing read. The window now shows what the last
  sync understood per column, the warnings, **which speech voices this machine actually
  has for the languages the sheet asks for**, and a preview.

### 🤖 Release process
- **Releasing is driven by the version, not by remembering to push a tag.** Merging to
  `main` with `manifest.json` and `pyproject.toml` bumped tags, builds and publishes;
  merging without a bump finds the tag already present and stops.
- Release notes are now the matching section of this changelog, so a release always
  says what changed. The run **fails before tagging** when a version has no section
  here, rather than leaving a tag pointing at a release that says nothing. Notes for
  v3.1.0 through v5.0.0 were backfilled.

---

## 💥 **v5.0.0** - August 2026 *(Breaking — features removed)*

A deliberate cut: the add-on now does one thing — sync a spreadsheet into Anki — and
carries nothing it does not need to.

### 💥 Removed
- **AI assistance is gone**: the AI Help / AI Ask / AI Checker buttons on cards, the
  Gemini/Claude/OpenAI integration, the desktop `pycmd` bridge and the mobile path that
  **embedded your API key in plaintext inside the card templates** — which meant the key
  was uploaded to AnkiWeb, synced to every device on the account, and included in any
  deck you exported or shared. Removing the feature removes that exposure. Gone with it:
  `ai_prompts.py`, `ai_service.py`, the AI config dialog, `Ctrl+Shift+H`, the
  `webview_did_receive_js_message` hook and every `ai_*` config key.
- **All vendored libraries.** `org_to_anki` (3.6 MB, which itself bundled pygments) was
  reached for exactly two calls — `startEditing()` / `stopEditing()` — which wrap
  `mw.requireReset()` / `mw.maybeReset()`, APIs Anki 25 answers with *"requireReset() is
  obsolete; please use CollectionOp()"*. `bs4`, `soupsieve` and `chardet` (2 MB) had no
  importer anywhere. All four are deleted along with the `sys.path` bootstrap. **The
  add-on now has no runtime third-party dependencies.**
- **The Configure Timer dialog** (`Ctrl+Shift+I`) — `get_timer_position()` and
  `set_timer_position()` were read and written by nothing but that dialog itself, while
  the timer that actually renders comes from the per-deck card layout. Changing the
  setting did nothing and said nothing. The timer is configured in **Configure Card
  Layout** (`Ctrl+Shift+C`), which is where it was always being read from.
- `tools/js-harnesses/`, which only ever exercised the removed AI card JavaScript.

### 📦 Size
- The packaged add-on drops from **386 files / 1.44 MB to 40 files / 169 KB**.

### 🐛 Fixes
- `get_deck_options_mode()` fell back to `"shared"` while the shipped default in
  `config.json` is `"individual"`; the fallback now matches.

### 📖 Documentation
- `README.md` rewritten as a user guide: every menu entry documented with what it does,
  how to open it, **the mechanism that makes it work**, and its caveats — plus a
  spreadsheet reference, sync semantics and troubleshooting drawn from the actual guards
  in the code. Several behaviours are documented for the first time, including that only
  the spreadsheet's **first tab** is ever synced (any `gid` in the URL is ignored), that
  the image processor's Apps Script reads a tab named `Notes` so the first tab must carry
  that name, and that the disconnect dialog's *delete local data* box is ticked by
  default.
- The version gotcha in `CLAUDE.md` is now stated as a rule rather than a number, since
  the hard-coded one had already gone stale.

---

## 🔧 **v4.0.1** - August 2026 *(Maintenance)*

### 🐛 Fixes
- **Deck names kept a localised "Google Sheets" suffix.** The page title Google serves
  is translated — "… - Google Trang tính", "… - Google Планшети", "… - Google Tabellen" —
  but only the English and Portuguese forms were stripped, so everyone else ended up with
  a deck literally named `HSK4 - Google Trang tính`. The suffix is now matched by shape
  rather than by a list of locales, with a word cap so a sheet genuinely named after a
  Google product keeps its name. Extracted as `deck_manager.strip_google_title_suffix`
  and covered by tests.

### 🌍 Language
- The **Configure Card Layout** dialog shipped with Vietnamese strings; it is now English
  like the rest of the add-on.
- Worked examples in `README.md`, `docs/README.md` and the docstrings switched to English
  headers (`Word`, `Reading`, `Meaning`, `Example`). The point that headers may be in any
  language or script is kept — it is now stated rather than demonstrated, so the primary
  example reads for everyone.
- Test sample data is English by default, with explicit non-ASCII cases retained per test
  module so Unicode headers, deck levels and tags stay covered.

---

## 💥 **v4.0.0** - August 2026 *(Breaking — the sheet now defines the schema)*

The fixed 24-column schema is gone. A sheet declares its own fields, and the card is
built from a layout the user edits in a dialog instead of one hard-coded in Python.

### 💥 Breaking
- **Only four headers are reserved**: `ID` (the key), `SYNC` (per-row gate), `SUBDECK 1..N`
  (deck path, ordered by the number rather than the column position, empty levels
  skipped) and `TAGS`. **Every other column becomes a note field named exactly like the
  header**, so a sheet can use whatever vocabulary its subject calls for. Column order
  decides what lands on the front and back of the card.
- The old exam-prep columns (`QUESTION`, `ANSWER`, `REVERSE`, `IMPORTANCE`, `TOPIC`,
  `SUBTOPIC`, `CONCEPT`, `BOARDS`, `LAST YEAR IN EXAM`, `CAREERS`, `OTHER TAGS`,
  `EXTRA FIELD 1-3`, `SANITY CHECK`) have no special meaning any more — they are just
  ordinary content columns if a sheet still has them. Existing decks need their headers
  renamed, and their notes are rebuilt on the next sync.
- **A sheet with no `SYNC` column now syncs every row.** It previously synced none,
  which produced an empty deck with nothing on screen explaining why.
- **No more `- Reverse` note type.** The reverse direction is a second card template on
  the same note type, so both directions are scheduled independently from one row of
  data, and switching it off removes its cards without touching the note.
- Tags are now `sheetcards`, `sheetcards::<subdeck path>` and whatever `TAGS` lists.
  The `[missing_*]` placeholder tags are gone.

### ✨ Card layout
- New **Configure Card Layout** dialog (`Ctrl+Shift+C`): choose which fields sit on the
  front and back, reorder them, toggle field labels, set font sizes and alignment, turn
  the reverse card and timer on or off, with a preview.
- The layout lives in **Anki's collection config**, so it travels between machines
  through AnkiWeb — no Google API, no extra setup. The AI provider API key deliberately
  stays machine-local in `meta.json`.
- "I'll edit the template myself" stops sync from regenerating the note type's
  templates, so hand edits in Anki's Cards editor finally survive a sync.

### 🐛 Fixes
- **Cloze note types were rejected by Anki.** A cloze template must reference
  `{{cloze:Field}}` on *both* sides — `{{FrontSide}}` does not satisfy the check — so
  provisioning one aborted the whole sync, including ordinary notes.
- Adding a column to the sheet now adds the field and shows it; **removing a column
  stops rendering it but never deletes the field**, so data is not destroyed by an
  edit to the header row.
- Dropped the deprecated `col.save()` calls; Anki persists collection changes itself.

---

## 💥 **v3.1.0** - August 2026 *(Breaking)*

The multi-student feature is gone, and the card is cut back to what a study card needs.

### 💥 Breaking
- **Multi-student removed.** The `STUDENTS` column is no longer read, and the
  `[MISSING_STUDENT]` sentinel no longer exists. Notes are keyed by the plain
  spreadsheet `ID` (and `{id}_REV` for the reverse variant) instead of the composite
  `{student}_{note_id}`; note types are `SheetCards - {deck} - Basic|Cloze|Reverse`;
  and the deck hierarchy loses its student level. Existing collections re-key and
  re-file their notes on the next sync.
- **Empty hierarchy levels are skipped** in deck names rather than filled with
  `[MISSING_*]` placeholders — a sheet that only uses `TOPIC` now gets `Deck::Topic`
  instead of a chain of empty subdecks. The old placeholder subdecks are left behind
  empty and can be deleted by hand.
- **Removed**: `student_manager.py`, the global student config dialog, the data-removal
  confirmation dialog, the `Ctrl+Shift+G` shortcut, the `students` config block and the
  disabled-student cleanup subsystem.

### 🐛 Fixes
- **Sync returned 0 notes for any sheet without a `STUDENTS` column.** Such rows fell to
  `[MISSING_STUDENT]`, whose sync is gated on `sync_missing_students_notes` — a key
  `_ensure_meta_structure` never wrote into `meta.json`, so the reader's
  `.get(..., False)` default won and the sync bailed, while `config.json` advertised the
  default as `true`. Removing the feature removes the gate.

### 🎨 Card template
- Front is the timer and the question; back adds the answer plus whatever supporting
  fields the row actually filled (examples, mnemonic, complementary/detailed info,
  image, video), each conditional so an empty field leaves no trace.
- The `CONTEXT`, `INFORMATION` and `TAGS` headings rendered even when every field under
  them was empty, so they are gone, along with their "May be empty" subtitles, the
  exam-prep fields (`BOARDS`, `LAST YEAR IN EXAM`, `CAREERS`, `OTHER TAGS`), the three
  extra fields and the sanity check. Those columns still sync into the note — they are
  just no longer drawn on the card.

### 🤖 CI
- Pushing a `v*` tag now builds both `.ankiaddon` packages, validates them and attaches
  them to a GitHub release. The job refuses to build when the tag, `manifest.json` and
  `pyproject.toml` disagree on the version.

---

## 🔧 **v3.0.3** - June 2026 *(Maintenance)*

The last two audit follow-ups, done in parallel. No new features.

### 🐛 Fixes
- **Backup/restore thread-safety**: backup and restore now run synchronously on the main
  thread (behind Anki's progress indicator) instead of in a daemon thread. These operations
  call into `mw.col` (export/import `.apkg`, deck removal, `col.save`), and Anki's collection
  is not thread-safe, so the old threaded path risked database corruption.

### 🎨 UI deduplication (visual consistency)
- Action buttons (Save / Apply / Cancel, and Disconnect's destructive button) across 10
  dialogs now come from shared `theme.primary_button_qss` / `theme.secondary_button_qss`
  helpers instead of per-dialog hand-rolled QSS.
- Group-box styling reconciled: dialogs that overrode the shared `groupbox_qss` with their
  own near-identical block now inherit the canonical one via `base_dialog_qss`.

### 🧪 Tests
- `tests/test_backup_threading.py` asserts backup operations run on the caller (main) thread,
  not a worker — a regression guard against reintroducing the daemon-thread path.

---

## 🔧 **v3.0.2** - June 2026 *(Maintenance)*

Post-v3.0.1 audit follow-ups. No new features and no behavior changes for end users
(the UI work is visual-consistency only).

### 🐛 Fixes
- **Config defaults isolation**: `get_config()` / `get_meta()` now deep-copy the module
  defaults in their fallback/merge paths, so a caller mutating a nested dict can no longer
  corrupt `DEFAULT_CONFIG` / `DEFAULT_META` for the rest of the process.

### 🎨 UI deduplication
- The gradient **header banner** (all 11 dialogs) and the **radio option-card**
  (deck-options + timer) now come from shared `theme.make_header` /
  `theme.make_radio_option_card` factories — ~560 lines of duplicated dialog code removed,
  and the headers are now byte-consistent.
- Removed write-only per-dialog state (`is_dark_mode`, `current_step`, the dead `*_radio`
  attributes) and the orphaned comments left behind.

### 🧪 Tests
- New construction-smoke (`tests/test_ui_instantiate_smoke.py`) instantiates every dialog,
  catching `__init__`/setup errors the import-only smoke can't; plus regression tests for
  the config-defaults isolation.

---

## 🔧 **v3.0.1** - June 2026 *(Maintenance)*

Internal quality work, a full code audit, and a UI-consistency pass since v3.0.0. No new
features and no breaking changes; the UI updates are purely visual (colors and labels) and
the audit changes are bug fixes and cleanup.

### 🔍 Full code audit (bugs, dead code, deduplication)
A repository-wide audit fixed correctness bugs and removed accumulated cruft:

**Bug fixes**
- **Cloze content with colons**: `clean_cloze_formatting` now preserves colons inside the
  answer (e.g. `{{c1::10:30}}` → `10:30`) and strips hints case-insensitively; previously
  such reverse-card fronts could render raw `{{c1::…}}` markup.
- **Backup restore data-loss guard**: a "full" backup whose `.apkg` is missing/corrupt no
  longer deletes the live deck before discovering the deck file is absent.
- **Backup zip-slip**: backup archives are validated against path traversal before extraction.
- **Config persistence**: a deck whose only changed field was its local deck id is now
  written to `meta.json` (previously updated in memory but never saved).
- **Note-type naming**: a whitespace-only student no longer produces a `None` note-type name.
- **Sync robustness**: fixed an `UnboundLocalError` in the cleanup step, stopped
  double-counting a single failed deck as two errors, and corrected the deck name shown in
  "unexpected error" messages.
- Smaller fixes: the import-test-deck duplicate guard, add-deck reconnection prompt for
  disconnected URLs, HTTP error-body decoding, deterministic `student_selection` ordering,
  and the error-traceback dialog now honoring the real debug flag.

**Cleanup**
- Removed ~40 grep-verified unused functions/classes (~1500 lines) across the engine,
  config, deck, student, backup and UI layers, plus stale/misleading comments and leftover
  section banners from the earlier facade split.
- De-duplicated the SYNC-true value set, the two sync error handlers, and the dialogs' URL
  helpers (new `src/ui/url_helpers.py`).
- Pinned `black`/`ruff` in the dev environment to the exact CI versions so local formatting
  matches the gates; added regression tests for the cloze and note-type-name fixes.

### 🎨 UI design system (visual consistency)
A single design system now drives every screen, replacing per-dialog hardcoded styling:
- **New `src/theme.py`** — one source of truth for theme detection (`is_dark_mode()`, via
  Anki's `theme_manager.night_mode`) and a semantic light/dark color palette, plus
  reusable button/header style helpers.
- **All 12 config dialogs** migrated to the shared palette: hardcoded color sprawl dropped
  from ~75 hex values (mixing Material Design and Bootstrap) to **zero**; the three
  competing "primary" blues collapsed into one brand blue (`#4A90D9` / `#5BA3E0`); the
  four duplicate `is_dark_mode()` copies into one; every gradient header unified (they
  previously ranged across green / purple / red). ~330 lines of duplicated palette and
  detection code removed.
- **Card UI** (study timer, AI Help/Ask/Checker buttons, reverse-card badge) re-skinned
  from off-brand purple / neon-green to the same brand blue. CSS-only — the card JS is
  byte-identical (sha256-verified).
- **Button labels** unified ("Save Settings" / "Save Configuration" → "Save").
- **Emoji standardized** — removed decorative emoji from buttons and section headers
  (keeping semantic status icons ⚠️✅❌ℹ️, language flags, and ✓/✗/←/→ affordances) for a
  more professional tone; card icons (timer, reverse badge, AI buttons) were left as-is.
- Regression guards added (`tests/test_theme.py`, `tests/test_ui_import_smoke.py`): they
  lock the palette values, assert every dialog color key resolves, and import every dialog.

### 🗂️ Project reorganization
- **`src/ui/` subpackage**: the Qt dialog modules were grouped under `src/ui/`.
- **God-file splits with back-compat facades**: `utils.py` → `errors.py` / `debug.py` /
  `deck_options.py`; `sync.py` → `sync_report.py`; `config_manager.py` → `ai_prompts.py`;
  `templates_and_definitions.py` → `card_assets.py`. The original modules re-export the
  moved names, so existing imports keep working.

### ⚙️ Tooling & CI
- **GitHub Actions CI**: a test job plus a lint job with **blocking** `ruff` and `black`
  gates (pinned versions) and an advisory `mypy` pass. Undefined-name errors (`F821`) are
  caught as part of the standard `ruff check` (the `F` rule family is enabled).
- **Pre-commit hooks** (`.pre-commit-config.yaml`): ruff + black + hygiene hooks
  (`libs/` excluded).
- **`CONTRIBUTING.md`** added; non-test JS/HTML harnesses moved to `tools/js-harnesses/`.

### 🐛 Fixes
- **Sync-summary crash**: `sync_report.py` referenced `DEFAULT_STUDENT` without importing
  it, raising `NameError` when the post-sync summary dialog rendered. Fixed, and now
  caught by the `ruff check` gate (`F` rules).

### 🎨 Code style & docs
- Repository-wide formatting pass (ruff auto-fixes + black), now enforced in CI.
- README rewritten in a professional tone; the developer guide (`docs/README.md`), test
  guide (`tests/README.md`), and script docs refreshed to match the current structure;
  the obsolete image-CLI docs were removed.

---

## 🚀 **v3.0.0** - January 2026 *(BREAKING CHANGES)*

### ⚠️ **Breaking Changes**
- **Python 3.13 Required**: Minimum Python version upgraded from 3.9 to 3.13
- **Anki 25.x Required**: Add-on now requires Anki version 25.x or newer
- **Qt6 Only**: Removed all Qt5 compatibility code
- **No Backward Compatibility**: Users on older Anki versions must update or use v2.x

### 🔒 **Security & Correctness Hardening (Audit)**

A full security/correctness audit was completed and all findings fixed:

**Critical**
- **Empty-sheet guard**: a sync that parses zero valid rows (e.g. a transient failed
  download) no longer runs the deletion pass, so it cannot wipe a deck.
- **Underscore-safe keys**: note/student/deck matching now uses suffix-aware logic, so an
  underscore in a student name can't corrupt the composite `{student}_{note_id}` key.

**High**
- **Non-destructive note-type changes**: switching a note's type creates the replacement
  before deleting the original, so a failure cannot lose the note.
- **Duplicate spreadsheet IDs** are detected and reported instead of silently colliding.
- **AI output sanitized**: HTML returned by AI providers is escaped/sanitized before it is
  injected into the card webview.
- **Test suite rebuilt** against the real `src` modules (with Anki mocked), replacing the
  previous self-mocking tests.

**Medium / Low**
- **TSV parsing hardened**: BOM handling (`utf-8-sig`), quoted-field parsing, whitespace
  trimming.
- **`marked.js` served locally** (with Subresource Integrity) instead of from a CDN.
- **Bare `except:` clauses** replaced with scoped handlers.
- **SSRF host check**: downloads are restricted to Google hosts; ImgBB uploads forced to
  HTTPS.
- **Card-template JS de-duplicated** into shared single-source constants.
- Version and pytest configuration unified; dead files and a tracked `.pyc` removed.

### 🎯 **Major Simplification**

#### 🔧 **Compatibility Module Rewrite** (`src/compat.py`)
- **Before**: 513 lines with complex version detection
- **After**: 265 lines with clean Qt6-only code
- **Removed**: ~250 lines of backward compatibility code
- **Result**: Simpler, more maintainable codebase

#### 🗑️ **Removed Code**
- ❌ All Qt5/Qt6 version detection logic
- ❌ All Anki version detection (23.x, 24.x checks)
- ❌ `get_anki_version()` function
- ❌ `ANKI_VERSION`, `IS_ANKI_25_PLUS`, `IS_ANKI_24_PLUS` constants
- ❌ `QT_VERSION` detection
- ❌ Conditional imports with `hasattr()` checks
- ❌ `exec_()` fallback methods for Qt5

#### ✨ **Modernization**
- ✅ Direct Qt6 imports only
- ✅ All constants use Qt6 enum syntax (e.g., `Qt.AlignmentFlag.AlignCenter`)
- ✅ Clean `exec()` method calls
- ✅ Simplified utility functions
- ✅ Python 3.13 features available

### 📝 **Configuration Updates**

#### **Development Tools**
- **Black**: Target version updated to `py313` only
- **Ruff**: Target version updated to `py313`
- **Mypy**: Python version set to `3.13`
- **Pyright**: Python version set to `3.13`

#### **Project Files**
- **pyproject.toml**: `requires-python = ">=3.13"`
- **Classifiers**: Removed Python 3.9-3.12, kept only 3.13
- **.python-version**: Updated to `3.13`

### 📚 **Documentation Updates**
- **README.md**: Added system requirements section
- **docs/README.md**: Removed all Anki 2.1.x references
- **Development Guide**: Updated prerequisites to Python 3.13+
- **Code Examples**: Updated to reflect Qt6-only usage

### 🎁 **Benefits**
- **Performance**: Python 3.13 performance improvements
- **Simplicity**: 250+ lines of complexity removed
- **Modern**: Using latest Python and Qt6 features
- **Maintainability**: Single code path, no version conditionals
- **Future-proof**: Ready for upcoming Anki versions
- **Easier Debugging**: No more version-specific bugs

### 📦 **Dependencies**
- **Anki**: 25.7.5+
- **PyQt6**: 6.9.1+
- **Python**: 3.13.5+

### 🔄 **Migration Guide**
Users upgrading from v2.x should:
1. Update to Anki 25.x or newer
2. Install the new add-on version
3. Existing decks and configurations will work without changes
4. No manual migration needed

---

## 🚀 **v2.3.0** - January 2026



### ✨ **New Features**
- **Debug Mode UI**: Dedicated interface (`Ctrl+Shift+L`) to manage debug mode, view logs, and reset configurations.
- **Sync Cancellation**: Added "CANCEL SYNC" button in data removal warning dialogs to prevent accidental data loss.

### 🎨 **UI/UX Improvements**
- **Modernized Configuration Dialogs**: Global Student, Deck Options, and AnkiWeb Sync dialogs updated with gradient headers, improved styling, and full dark mode support.
- **Localization**: Standardized column names to Portuguese (`PERGUNTA`, `ALUNOS`, `LEVAR PARA PROVA`) in documentation and sample data.
- **Sample Data**: Translated `sample_sheet.tsv` content to English while maintaining Portuguese column headers.

### 🔧 **Fixes & Optimization**
- **AnkiWeb Timeout**: Fixed persistence issue where timeout settings were not being saved.
- **Documentation**: Updated README to reflect support for 23 columns.
- **Code Cleanup**: Removed dead code directories (`config_pkg`, `sync_pkg`, `utils_pkg`) and consolidated imports.

---

## 🚀 **v2.2.0** - August 2025

### ✨ **Revolutionary URL System Simplification**

#### 🎯 **Unified URLs**
- **ONLY Edit URLs**: Simplified system works exclusively with edit URLs (`/edit?usp=sharing`)
- **Elimination of Published Format**: Completely removed support for published URLs (`/pub?output=tsv`)
- **Automatic Conversion**: Edit URLs are automatically converted to TSV download format
- **Simplified Process**: A single URL type for all use cases

#### 🆔 **Real ID Identification System**
- **Spreadsheet ID**: Uses the actual Google Sheets spreadsheet ID as identifier
- **End of Hashes**: Completely eliminates the MD5 hash system for identification
- **Clearer Configuration**: `meta.json` now uses real spreadsheet IDs as keys
- **Total Transparency**: Users can see exactly which spreadsheet is configured

#### 🔧 **Complete API Refactoring**
- **New Functions**:
  - `extract_spreadsheet_id_from_url()`: Extracts spreadsheet ID from edit URLs
  - `get_spreadsheet_id_from_url()`: Gets ID with validation
  - `convert_edit_url_to_tsv()`: Converts edit URL to TSV
- **Removed Functions**:
  - `extract_publication_key_from_url()`: ❌ Removed
  - `get_publication_key_hash()`: ❌ Removed
  - `convert_google_sheets_url_to_tsv()`: ❌ Removed

### 🗂️ **Automatic Configuration Migration**
- **Compatibility**: Existing configurations continue working
- **Transparent Migration**: System automatically detects and migrates old configurations
- **Data Preservation**: All decks and preferences are maintained
- **No Intervention**: Completely automatic process for the user

### 🧪 **New Test Suite**
- **Specific Tests**: 18 new tests for simplified functionalities
- **Complete Coverage**: Validation of all new functions
- **Error Tests**: Robust validation of error cases
- **Dedicated File**: `test_url_simplification.py` for new functionality tests

---

## 🚀 **v2.1.0** - August 2025

### ✨ **New Features**

#### 💾 **Advanced Backup System**
- **Automatic Configuration Backup**: Automatic backup on each synchronization with file rotation (keeps only the 50 most recent)
- **Configuration-Only Backup**: New backup mode that preserves only addon settings, ideal for reinstallation
- **3-Column Interface**: Side-by-side layout for full backup, recovery and automatic settings
- **Flexible Configuration**: Customizable directory for automatic backups
- **Sync Integration**: Automatic trigger after each successful synchronization

#### 🔧 **Automatic Name Consistency System**
- **Automatic Correction**: Automatically detects and corrects inconsistencies in note type names
- **Intelligent Synchronization**: Checks name alignment during each synchronization
- **Transparent Update**: Corrects differences between remote and local names without manual intervention
- **Data Preservation**: Maintains study history and settings during corrections
- **Standardized Names**: Implements consistent standards for decks, note types and configurations

#### 📊 **Enhanced Sync Summary**
- **Dual Visualization**: "Simplified" and "Complete" modes for different needs
- **Optimized Order**: In "Complete" mode, aggregated general summary appears first
- **Detailed Metrics**: Complete spreadsheet statistics and results per deck
- **Responsive Interface**: Automatic support for dark mode and adaptive layout

#### 🖼️ **Multimedia Field Support**
- **Media Fields**: "IMAGE HTML" for images/illustrations and "VIDEO HTML" for embedded videos
- **Automatic Template Update**: Automatically adds fields to existing note types
- **Intelligent Positioning**: Media appears on the back of the card for better pedagogy
- **Safe Templates**: Doesn't duplicate fields and preserves existing data

### 🔄 **Improvements and Optimizations**

#### 🌐 **Complete Google Sheets URL Support**
- **Edit URLs**: Native support for `/edit?usp=sharing` URLs
- **Automatic Conversion**: Automatically converts edit URLs to TSV format
- **GID Auto-discovery**: Automatically detects the correct spreadsheet gid
- **Backward Compatibility**: Maintains compatibility with published TSV URLs
- **Bug Fix**: Eliminates HTTP 400 "Bad Request" error with edit URLs

#### 👥 **Advanced Student Management**
- **Global Configuration**: Define once which students to sync across all decks
- **Personalized Subdecks**: Each student has their own organized hierarchy
- **Unique Note Types**: Personalized card templates for each student
- **Intelligent Filtering**: Syncs only the chosen students

#### 🏷️ **Complete Hierarchical Tag System**
- **8 Categories**: Students, Topics, Exam Boards, Years, Careers, Importance, Extra Tags
- **Hierarchical Structure**: Automatic organization in levels (`SheetCards::Category::Item`)
- **Custom Tags**: Support for additional custom tags

### 🐛 **Bug Fixes**
- **HTTP 400 with Edit URLs**: Resolved through GID auto-discovery
- **Name Inconsistency**: Automatically corrected by consistency system
- **Count Calculation**: Fixed to use notes instead of questions
- **Empty Subdecks**: Automatic removal after synchronization
- **Error Reports**: Updated link to correct GitHub repository

### 🧪 **Testing and Quality**
- **Comprehensive Test Suite**: Tests for backup, dialog, name consistency
- **Complete Coverage**: 100% of new features tested
- **Integration Tests**: End-to-end functionality validation
- **Compatibility Tests**: Verification with PyQt5/PyQt6

---

## 🏗️ **v2.0.0** - July 2025

### ✨ **Main Features**
- **Selective Synchronization**: `SYNC` column for individual card control
- **Basic Backup System**: Manual backup and deck restoration
- **AnkiWeb Synchronization**: Automatic after updates
- **Cloze Card Support**: Automatic detection of `{{c1::text}}` patterns
- **Personalized Note Types**: One for each student automatically

### 🔧 **Base Architecture**
- **19 Required Columns**: Standardized structure for spreadsheets
- **TSV Processing**: Robust engine for Google Sheets data
- **Configuration Management**: `meta.json` system for persistence
- **Qt Interface**: Modern dialogs for configuration and status

---

## 📋 **v1.1.0** - June 2025

### ✨ **Basic Features**
- **Google Sheets Synchronization**: Direct connection with TSV spreadsheets
- **Automatic Deck Creation**: Based on spreadsheet data
- **Basic Note Types**: Support for basic and cloze cards
- **Simple Tags**: Basic categorization system

### 🔧 **Infrastructure**
- **Anki Add-on**: Native integration with Anki 2.1+
- **Data Processing**: Basic TSV engine
- **Simple Interface**: Basic configuration dialogs

---

## 📊 **Project Snapshot**

- **Compatibility**: Anki 25.x+ only (Qt6 / PyQt6)
- **Python**: 3.13
- **Platforms**: Windows, macOS, Linux
- **Quality gates**: `ruff` + `black` enforced in CI; the test suite runs against the
  real `src` modules with Anki mocked. Coverage is opt-in
  (`python tests/run_tests.py --coverage`).

---

## 📚 **Related Documentation**

- [`README.md`](../README.md) — end-user install & usage guide
- [`docs/README.md`](README.md) — long-form developer guide
- [`CLAUDE.md`](../CLAUDE.md) — concise architecture & conventions reference
- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — setup & contribution workflow
- [`tests/README.md`](../tests/README.md) — test-suite guide
- [`scripts/README.md`](../scripts/README.md) — build & packaging

---

## 🤝 **Contributions**

### 👥 **Core Team**
- **tannc28** - Lead Developer and Maintainer
- **Email**: nguyencongtan1002.work@gmail.com
- **GitHub**: [@tannc28](https://github.com/tannc28)

### 🐛 **Report Bugs**
- **Issues**: [GitHub Issues](https://github.com/tannc28/sheetcards/issues)
- **Discussions**: [GitHub Discussions](https://github.com/tannc28/sheetcards/discussions)

### 🌟 **Acknowledgments**
- Anki community for the robust platform
- Users who provided valuable feedback
- Code and documentation contributors

---

## 📄 **License**

This project is licensed under the **MIT License** - see the [`LICENSE`](../LICENSE) file for details.

---

## 🔗 **Useful Links**

- **🏠 Repository**: [github.com/tannc28/sheetcards](https://github.com/tannc28/sheetcards)
- **🐛 Issues**: [GitHub Issues](https://github.com/tannc28/sheetcards/issues)
- **📖 Documentation**: [`README.md`](../README.md) · [`docs/README.md`](README.md) · [`CONTRIBUTING.md`](../CONTRIBUTING.md)

---

*Last updated: June 2026*
