# Sheets2Anki

**Sheets2Anki turns a Google Sheets spreadsheet into an Anki deck and keeps it in sync.**
You write and organize your cards in a spreadsheet; the add-on downloads it, creates or
updates one Anki note per row, files the notes into subdecks, tags them, and builds the
card templates for you. Nothing is uploaded back to the sheet — the sheet is the source
of truth, Anki is the copy.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Anki](https://img.shields.io/badge/Anki-25.x%20%7C%2026.x-blue)
![Python](https://img.shields.io/badge/python-3.13-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

---

## Table of contents

- [Requirements](#requirements)
- [Preview a sheet in your browser](#preview-a-sheet-in-your-browser)
- [The example workbook](#the-example-workbook)
- [Install](#install)
- [Quick start](#quick-start)
- [Spreadsheet reference](#spreadsheet-reference)
- [Features](#features)
- [How syncing behaves](#how-syncing-behaves)
- [Keyboard shortcuts](#keyboard-shortcuts)
- [Where your settings live](#where-your-settings-live)
- [Troubleshooting](#troubleshooting)

---

## Requirements

| Component | Version |
| :--- | :--- |
| Anki | 25.x or 26.x (`min_point_version 250000`) |
| Qt | 6 |
| Python | 3.13 (the one bundled with Anki) |

There is no Qt5 / Anki 2.1.4x fallback. A Google account is needed only to *write* the
sheet — Anki reads it anonymously over a public link.

## Preview a sheet in your browser

**<https://tannc28.github.io/sheets2anki/>**

Paste a Google Sheets link and the page shows what the add-on would make of it —
before anything is installed and before your collection is touched:

| It shows | Why that helps |
|---|---|
| The sheet itself, as a grid — its own row numbers and column letters, the settings row where it sits, and which rows will sync | Tells you straight away that the file that arrived is the one you meant |
| Which column became `ID`, `SYNC`, `SUBDECK n`, `TAGS`, and which became fields | The commonest cause of "it synced nothing" is a column the add-on did not recognise |
| Every row's fate: syncs, not ticked, or no ID — with the same counts the sync reports | Answers "why 0 notes?" without installing anything |
| Whatever the settings row got wrong, spelled out | Otherwise these only appear in the debug log |
| The deck tree and the tags each row lands in | Catches a `SUBDECK` typo before it creates a stray deck |
| The card itself — front, back, reverse, cloze, media, a TTS button that speaks through your computer's voices, and a typed-answer box you can actually type into | The TTS button is a real test of whether a language code has a voice on this machine, and the typed-answer box marks what you type exactly as Anki does |

The page is not a second implementation. It downloads the add-on's own
`column_model.py`, `sheet_config.py`, `card_layout.py`, `tsv_model.py` and
`errors.py` and runs them in the browser through [Pyodide](https://pyodide.org),
so the columns, settings, warnings and card templates it shows are produced by the
code that will produce them at sync time. Only the last step — drawing the finished
template as a picture — is written for the page; inside Anki that step is Anki's own
renderer, so treat the card image as a close approximation and the template text as
exact.

The sheet needs the same sharing the add-on needs (**Anyone with the link →
Viewer**), so if the preview can read your sheet, so can Anki.

### One file, one deck per sheet

A Google Sheets file holds several **sheets** — the tabs along the bottom — and
Sheets2Anki connects **every one of them as its own deck**. Paste the file's link
once and each sheet becomes a deck of its own — `s2a_{file}::{sheet}` — with its own columns,
its own settings row and its own note type. One spreadsheet can hold your whole
collection.

`Ctrl+Shift+S` then lists one row per sheet, so you choose which to sync.

- **A sheet with no `ID` column is skipped**, and the dialog says which — a file
  people actually use has drafts, notes and a colour key in it beside the
  vocabulary. Hidden sheets are skipped too.
- **A deck remembers its sheet by name.** Move a sheet to a different position in
  the file and its deck follows it. **Rename a sheet and the deck stops finding
  it** — the sync says so and lists the names that do exist; connect the file
  again to pick the renamed sheet up.
- **Decks connected before this keep working untouched.** They stay pointed at the
  file's first sheet. Connect the file again and that deck keeps its notes and its
  review history while the other sheets join it as decks of their own.

### Or point at an `.xlsx` file instead of a Google Sheet

A deck's source does not have to be a Google Sheet. Paste a link that ends in
`.xlsx` or `.xlsm` — a file in a GitHub repository, or on any https host — and it
is read by the same reader, one deck per sheet, exactly as a Google Sheet is.

GitHub's own address works: paste the `.../blob/main/decks.xlsx` link the browser
shows you and the add-on fetches the raw file behind it.

Two things follow from the file being a file:

- **There is no "edit and it's synced".** A Google Sheet you change is changed;
  a file has to be uploaded again before a sync sees it. For anything you edit
  often, a Sheet is still the better home.
- **The address must be public and `https`.** The add-on refuses `http`, other
  schemes, and any address that resolves inside a private network — it runs on
  your machine, inside your network, so an address someone else chose is not one
  it should be knocking on.

### Or upload a file instead of a link

**Upload a file** — or drag one onto the page — reads `.xlsx`, `.xlsm`, `.csv` and
`.tsv` from your computer. Useful when the sheet is private, when you are still
drafting it offline, or when you keep your cards in Excel and have no Google Sheet
at all. A workbook with several tabs gets a picker beside the button; each tab is
read on its own and becomes its own deck, named after the tab.

The file never leaves your browser — Pyodide reads it in the page, and there is no
server to send it to.

Two things to know:

- **The add-on itself still needs a link.** Only the preview reads files, so the
  `.apkg` download is how an uploaded workbook reaches Anki. To *sync* a sheet —
  which is what lets a deleted row disappear from your collection — it has to live
  in Google Sheets.
- **A cell is read as the sheet shows it.** A date column comes out as
  `2025-01-21`, and a whole number as `1` rather than `1.0`, so the `ID` column
  keys the same notes it would have if the same sheet had arrived as a link.

### Download an `.apkg` — no desktop needed

The preview page can also build the deck as an `.apkg` file, right in the browser.
**AnkiDroid and AnkiMobile import it directly**, so a sheet can reach your phone
without Anki for desktop being involved at all.

It is built by the add-on's own code — same fields, same note type, same templates
— and a note's identity comes from its `ID`, so **importing again updates those
notes instead of duplicating them**.

What it cannot do is **delete**. Anki's importer never removes a note that is
missing from the file, so a row you delete from the sheet stays in your collection
until you delete it there. That is the real difference between an import and a
sync, and it is why the add-on still exists.

> Uploading straight to AnkiWeb is not possible: AnkiWeb has no public API, sends
> no CORS headers (so a browser refuses the request before it leaves your machine),
> and is a sync target for a collection rather than a place decks are created.

To run it locally: `python scripts/build_site.py --serve`.

---

## The example workbook

Every feature below has a working example, and they all live in one file in this
repository: [`examples/`](examples/). Paste this link into the preview site, or
into **Add New Remote Deck** (`Ctrl+Shift+A`), and study the result:

```text
https://github.com/tannc28/sheets2anki/blob/main/examples/sheets2anki-examples.xlsx
```

Most of it is English for Vietnamese speakers, because that is what most people
are studying; Chinese, Japanese and Korean appear where the feature is theirs —
handwriting, furigana, non-Latin headers.

Thirty-one sheets, each one its own deck, ordered from *the smallest sheet that
works* to *a deck you would keep studying*. Where a column carries the meaning of a
word it is glossed in Vietnamese; everything else is English. Nothing about the
add-on is language-specific — a deck of anatomy or case law works the same way:

| Sheet | What it shows |
| :--- | :--- |
| `01 Basic (cơ bản)` | `ID`, `Front`, `Back` — a word each in English, Chinese, Japanese, Korean, German and Spanish, answered in Vietnamese. No settings row, no `SYNC` |
| `02 Sync & subdecks (deck con)` | `SYNC` gating, `SUBDECK 1`/`2`, `TAGS` |
| `03 Card layout (bố cục thẻ)` | `side`, `size`, all three colour forms, `bold`, `italic`, `label`, `hint`, `side=hide`, deck-wide `align` |
| `04 Reverse (thẻ ngược)` | one row, two cards |
| `05 Type the answer (gõ đáp án)` | `type=nc`, so the Vietnamese marks do not have to be typed |
| `06 Cloze (điền chỗ trống)` | a declared `cloze` column, including a row with two deletions |
| `07 Images (hình ảnh)` | `image` on the prompt, with `size` — the picture asks and the Chinese word answers |
| `08 Audio (âm thanh)` | `audio`, listen-then-recall: an English word spoken by a person, not a synthesiser |
| `09 Video (video nhúng)` | every YouTube link form the add-on rewrites, plus a direct file |
| `10 Speech (đọc thành tiếng)` | `tts=en_US`, a `voices=` preference, deck-wide `speed`, and a hidden column that repeats the phrase at half speed |
| `11 Chinese writing (gõ chữ)` | write the character, then check it against a stroke-order animation — `type` + `image` + `hint` + `tts` on one card, and `subdeck=1` filing it by HSK level |
| `12 Chinese drawing (viết tay)` | `draw` — you write the character stroke by stroke and each stroke is marked |
| `13 Furigana (phiên âm kanji)` | `furigana` over kanji |
| `14 Any headers (mọi ngôn ngữ)` | headers written as `汉字`, `拼音`, `释义`, `例句` |
| `15 Theme + subdeck (màu, tầng)` | English vocabulary filed three `SUBDECK` levels deep — `English::B1::Verbs` — in `theme=sakura`, spoken, and sorted by the word |
| `16 Picture words (từ vựng ảnh)` | a picture on the front and a native recording on the back — `image` and `audio` on one card, filed by `Group` |
| `17 Draw & type (viết và gõ)` | write the character stroke by stroke *and* type its pinyin: `draw` and `type=nc` asking the same thing two ways |
| `18 Grammar cloze (ngữ pháp)` | the word carrying the grammar point deleted, and typed rather than recalled — `cloze` plus `type` |
| `19 Dictation (nghe rồi gõ)` | the sentence is spoken and drawn nowhere: `side=hide` + `tts` + `type`, so the only way through is to listen |
| `20 Video lesson (bài video)` | the clip *is* the question — `video` on the front, filed by lesson |
| `21 Formulas & code (công thức)` | `math` for formulas and `code=python` for listings — the two kinds of cell that are not prose, plus `sort` |
| `22 Arabic (phải sang trái)` | `rtl`, the direction Arabic, Hebrew and Persian are written in |
| `23 Vertical text (viết dọc)` | `vertical` — top to bottom, right to left, the way Japanese is set in a book |
| `24 Korean (tiếng Hàn)` | `font=kr` and a Korean voice — a script with a font of its own |
| `25 Traditional (chữ phồn thể)` | the same word in `font=tc` and `font=sc` side by side, spoken in `zh_TW` |
| `26 Shell commands (dòng lệnh)` | `code=bash` — the answer is a command, filed by what it is for |
| `27 Web dev (HTML & JS)` | two code columns on one card, `code=html` and `code=javascript` |
| `28 Chemistry (hoá học)` | `math=block` equations under a plain-language answer |
| `29 Phrasal verbs (cụm động từ)` | `cloze` on the particle that is hardest to look up, and the sentence spoken |
| `30 German (tiếng Đức)` | der/die/das asked on the front, `tts=de_DE` on the noun and the example |
| `31 Spanish (tiếng Tây Ban Nha)` | `type=nc` again, where the accents are Spanish and `ñ` still has to be typed |

The workbook is generated from `SHEETS` in
[`scripts/build_examples.py`](scripts/build_examples.py), and the test suite fails
when a directive has no example — so one added to the add-on gets an example in
the same commit. [`examples/README.md`](examples/README.md) walks through each
sheet in detail.

---

## Install

1. Download the released `sheets2anki-standalone.ankiaddon` file.
2. In Anki: **Tools → Add-ons → Install from file…**, select the downloaded file.
3. **Restart Anki.**

A new **Sheets2Anki** submenu appears under **Tools**. That submenu is the whole
interface — the add-on adds no toolbar buttons and no browser actions.

---

## Quick start

### 1. Build the smallest possible sheet

Open a new Google Sheet and put this in row 1:

| ID | Question | Answer |
| :--- | :--- | :--- |
| 1 | Capital of France | Paris |
| 2 | Capital of Japan | Tokyo |

`ID` is the only header the add-on requires. `Question` and `Answer` are *your* names —
you could call them `Term`/`Definition` or `Palabra`/`Significado`; each becomes an Anki
field with exactly that name.

### 2. Share the sheet

**Share → General access → Anyone with the link → Viewer.** The add-on downloads the
sheet without signing in, so a private sheet will fail with an HTTP 400.

Copy the URL from the browser address bar (the normal `.../edit?...` link).

### 3. Connect it

**Tools → Sheets2Anki → Add New Remote Deck** (`Ctrl+Shift+A`). Paste the URL. The
dialog validates it as you type (with a ~1.2 s pause after you stop), downloads the
sheet, and shows how many rows it found and what the deck will be called.

You do **not** name the deck — the name is read from the spreadsheet's title, and the
deck is always created as `s2a_<file name>::<sheet name>`.

### 4. Sync

**Tools → Sheets2Anki → Synchronize Remote Decks** (`Ctrl+Shift+S`), tick your deck,
press **Synchronize Selected**. A summary window reports what was created, updated and
deleted. Your cards are ready to study.

### 5. Decide what the card looks like

By default the **first** content column is the front and the rest are the back, so the
example above gives you `Question` → `Answer`. To change that — or to set text sizes,
colours, hints, furigana, text-to-speech, or to turn a column of URLs into pictures, sound
or video — add a [settings row](#the-settings-row) to the sheet and sync again.
**Configure Card Layout** (`Ctrl+Shift+C`) shows you what the add-on read out of that row,
but the sheet is where you edit it.

The fastest way to see what a settings row can do is to connect
[the example workbook](#the-example-workbook) and look at the sheet nearest to
what you are building.

---

## Spreadsheet reference

**Row 1 is the header row. Every other row is one Anki note.** Header names are matched
case-insensitively with surrounding whitespace and any BOM ignored, so `id`, `ID ` and
`Id` are the same column.

Row 2 is an ordinary note like any other — *unless* its `ID` cell starts with `#config`,
which turns it into the optional [settings row](#the-settings-row) that describes how the
columns are presented.

### Reserved headers

Only these four names carry special meaning:

| Header | Required | What it does |
| :--- | :--- | :--- |
| `ID` | **Yes** | The row's permanent key. The add-on matches Anki notes back to spreadsheet rows by this value. Any text works (`1`, `Q-101`, a UUID) as long as it is unique. **Never change or reuse an ID.** |
| `SYNC` | No | Per-row on/off switch. A row syncs when the cell equals `TRUE`, `1`, `yes`, `sim`, `x` or `✓` (case-insensitive, trimmed). Anything else — including blank — means "don't sync". **If the sheet has no `SYNC` column at all, every row syncs.** |
| `SUBDECK 1`, `SUBDECK 2`, … | No | One level of the deck path each. Levels are ordered by their *number*, not by their position in the sheet, so moving `SUBDECK 2` left of `SUBDECK 1` does not reorder anyone's decks. Blank levels are skipped. Spelling is flexible: `subdeck2`, `Subdeck  10` all work. |
| `TAGS` | No | Extra Anki tags for the row, separated by commas or semicolons. |

### Content columns

**Every other column becomes an Anki note field with the header as its name.** Headers
may be in any language or script. There is no fixed column list and no "QUESTION"/
"ANSWER" requirement.

Two rules govern content columns:

- **The sheet must have at least one.** A sheet containing only reserved headers is
  rejected with *"The sheet has no content columns"*.
- **Their left-to-right order is the card order.** The first content column goes on the
  front, all the others on the back, so reordering columns reorders the card. To override
  that per column, use `side=` in the [settings row](#the-settings-row).

If the same header appears twice, the **first** occurrence wins and the duplicate is
ignored (it is noted in the debug log).

### Worked example

Header row:

```text
ID | SYNC | SUBDECK 1 | SUBDECK 2 | Word | Reading | Meaning | Example | TAGS
```

One row:

```text
42 | TRUE | Japanese | Kanji | 水 | みず | water | 水を飲む | jlpt-n5; nature
```

This produces:

- **Note fields** — `ID`, `Word`, `Reading`, `Meaning`, `Example` (in that order; `ID`
  is always the first field).
- **Card** — front `Word`, back `Reading` + `Meaning` + `Example`.
- **Deck** — `s2a_<file>::<sheet>::Japanese::Kanji`.
- **Tags** — `sheets2anki`, `sheets2anki::japanese::kanji`, `jlpt-n5`, `nature`.

### The settings row

Everything above describes a sheet that only holds *content*. A sheet can also describe
**how** its columns are presented — which side of the card they land on, how big they
are, whether they are read aloud, whether a URL becomes a picture or a player — by adding
one optional row directly under the header row.

**Row 2 becomes the settings row when its `ID` cell starts with `#config`.** Data then
starts at row 3. Without that marker there is no settings row at all and row 2 is an
ordinary note, so **every sheet written before this feature keeps working exactly as it
did** — you only get a settings row if you ask for one.

| ID | Word | Reading | Meaning |
| :--- | :--- | :--- | :--- |
| `#config` | `side=front; size=48` | `color=muted` | |
| 1 | 推迟 | 推迟[tuī chí] | to postpone |

**Syntax.** Each cell holds `key=value` pairs separated by `;`. A key written on its own
is a switch (`bold`, `hint`). An **empty cell means "use the defaults"**, so a sheet only
spells out what it actually changes. The marker itself is case-insensitive (`#CONFIG`
works) and must be followed by a space if you put deck-wide settings after it:

```text
#config align=left; speed=0.9; reverse
```

#### Per-column keys

Written in that column's cell of the settings row.

| Key | Values | Default | What it does |
| :--- | :--- | :--- | :--- |
| `side` | `front`, `back`, `hide` | first content column front, all others back | Which side the column appears on. `hide` keeps the field and its content in Anki but shows it on neither side |
| `label` | any text | no caption | Prints a small caption above the value. Without it the value stands alone |
| `size` | a number of pixels — **6–200** on a text column, **1–2000** on a media one (`size=48` or `size=48px`) | 40 px on the front, 18 px on the back; no width cap on media | **Font size** on a text column, maximum **width** on an `image` or `video` column. The range that applies is the one for whatever the cell turned out to be, so `size=480; video` works as well as `video; size=480` |
| `color` | `muted`, `accent`, a CSS colour name (`crimson`), or a `#hex` value | the card's normal text colour | `muted` and `accent` **follow Anki's light/dark theme**; a fixed colour does not, so a hard-coded `black` disappears in night mode |
| `bold` | switch | off | Bold text |
| `italic` | switch | off | Italic text |
| `align` | `left`, `center`, `right` | the deck-wide `align`, otherwise centred | Alignment for that column only |
| `hint` | switch | off | Renders the field through Anki's `hint:` filter: the value stays hidden behind a link until you click it |
| `furigana` | switch | off | Renders the field through Anki's `furigana:` filter, printing the reading above the text. **Requires the cell to be written `推迟[tuī chí]`** — text, then the reading in square brackets |
| `tts` | a **full** language code (`zh_CN`, `en_US`, `pt_BR`; `zh-CN` is accepted too) | no speech | Has Anki read the field aloud with the system voices |
| `voices` | comma-separated voice names (`voices=Huihui,Yaoyao`) | Anki picks | A *preference*, not a requirement — see below |
| `speed` | a number **0.5–2.0** | the deck-wide `speed`, otherwise Anki's own default | Speaking rate for that column; overrides the deck-wide value |
| `image` | switch | off | The column holds a **bare image URL**: the card shows the picture instead of printing the address. `size` caps its width |
| `audio` | switch | off | The column holds a **bare audio URL**: the card shows a player, always with `controls` so it can be replayed |
| `cloze` | switch | off | The column holds the sentences with `{{c1::…}}` deletions. **Declaring it makes the whole sheet a cloze sheet**, and the column becomes the prompt wherever it sits |
| `type` | switch, or `type=nc` | off | Anki draws a box on the question and diffs what you type against this column. `type=nc` ignores diacritics, so `shuxi` matches `shúxī`. One column per sheet |
| `video` | switch | off | The column holds a **bare video link** — YouTube, Drive, Vimeo or a direct `.mp4`: the card shows that site's own player. `size` caps its width |
| `draw` | switch | off | The column holds a **Chinese character**, and the card turns it into a writing box: on the question you draw it stroke by stroke and each stroke is marked, on the answer the correct strokes are animated. `size` is the side of the box in pixels — see below |
| `subdeck` | a level number (`subdeck=1`) | off | This column is that level of the **deck path**, exactly as a `SUBDECK n` header would be. It is never drawn on the card. See below |

#### Filing notes with a column you also show (`subdeck`)

`SUBDECK 1`, `SUBDECK 2` are names the *add-on* chose. `subdeck=n` says the same
thing from an ordinary column's own settings cell, so a sheet never has to give
one of its columns a reserved name:

```text
ID       Level        Word     Meaning
#config  subdeck=1    size=48
w01      HSK 1        写       to write
w02      HSK 2        山       mountain
```

→ `s2a_{file}::{sheet}::HSK 1`, and nothing on the card.

**Where a note is filed is a bigger thing than how one card looks**, so a column
working at deck level is not part of the card at all — not drawn, not styled, not
spoken. `size`, `color`, `side`, `tts` and the rest are refused on it, by name, in
the warnings. That is the same rule a reserved `SUBDECK n` column has always
followed; there is one rule here, not two.

Nothing is lost by not printing it: the note is *in* the deck named after that
value, and Anki shows the deck. Printing it on the card would say twice what the
deck tree already says once. If you want it on the card as well, that is a second
column — and the sheet is the place to decide that, not the settings row.

- **The number is the level**, exactly as in `SUBDECK 1` / `SUBDECK 2`, so the
  order comes from the numbers rather than from where the columns sit.
- **An empty cell drops that level**, same as an empty `SUBDECK` cell.
- **Two columns cannot be the same level**, and a column holding a URL
  (`image`/`audio`/`video`) cannot be a deck level at all — both say so.
- **A sheet that uses both wins with the settings row**, and names the reserved
  `SUBDECK` columns it is overruling, because a deck quietly not appearing is not
  something anyone thinks to go looking for.

#### Writing a character by hand (`draw`)

`type` asks you to spell an answer on the keyboard. `draw` asks you to *write* it,
which is the thing a keyboard cannot test — and the reason a lot of people study
Chinese with paper beside the computer.

- **Which of the two things the box does is decided by the side the column lands
  on.** On the **question** it starts empty and takes your strokes, marks each
  one, and shows a hint after two misses. On the **answer** it animates the
  correct strokes in a loop. There is no second directive for this: the column
  already says where it is.
- **A cell can hold more than one character** — `你好` gives two boxes side by
  side, in order.
- `size` is the **side of the square**, not a font size, so the usable range is
  the same as for a picture (1–2000 px). 200–300 is comfortable.
- `color` still applies: the strokes are drawn in whatever colour the box
  inherits, so `color=accent` follows your light/dark theme. `bold`, `italic` and
  `furigana` have no text to act on and say so; `tts` still works, because there
  is a character to read aloud.
- `hint` puts the box behind a disclosure, the same way it does for media — Anki's
  own `hint:` filter would reveal the character's *text*, which is exactly what
  the box exists not to show.

**What it costs.** The stroke data and the code that marks your strokes come from
[HanziWriter](https://hanziwriter.org) over the network, loaded into the card
rather than shipped with the add-on — the add-on is not what runs it, your Anki
is. So a `draw` column needs the network, exactly like a media column, and a
client that refuses remote scripts shows a dashed box with the character in it
instead. It is verified on Anki for desktop; on AnkiDroid and AnkiMobile it
depends on that client allowing remote scripts, which we have not tested.

Only Chinese characters have stroke data. A cell holding anything else — a
letter, a digit, a character the data set does not cover — is printed in the box
rather than left blank.

#### Heard without being read (`side=hide` + `tts`)

`tts` says *speak this column*; `side=hide` says *do not draw it*. A column that
says both is asking to be heard and not read, which is what a listening card is —
the sentence said aloud with nothing on screen to read it off:

```text
ID       Chinese            Pinyin   Meaning   Once more, slowly
#config  size=40; tts=zh_CN                    side=hide; tts=zh_CN; speed=0.5
```

It is spoken on the side it would have been drawn on, and the reverse card swaps
that along with everything else. Before this, hiding a column took its voice with
it and there was no way to ask for one without the other.

#### Styling one column yourself

Every block a card renders carries the column it came from:

```html
<div class="s2a-back" data-s2a-col="Pinyin">…</div>
```

So for the rare thing the settings row does not cover, the note type's **Styling**
can reach a single column — `[data-s2a-col="Pinyin"] { letter-spacing: .04em; }` —
without touching the templates, which are rebuilt from the sheet on every sync
and would lose the edit.

#### Media columns

`image`, `audio` and `video` say *what the cell contains*, so a column of links becomes
the thing the links point at:

| Its cell in the settings row | What the card renders |
| :--- | :--- |
| `image; size=320` | `<img src="{{Picture}}" style="max-width: 320px">` |
| `audio` | `<audio src="{{Sound}}" controls></audio>` |
| `video; size=480` | `<iframe src="{{Clip}}" class="s2a-embed" allowfullscreen …>` |

The cell in a *data* row holds nothing but the URL — the add-on builds the tag around it.
A column carries **one** kind of media: `image; video` keeps `image` and warns.

##### Video: paste the link from the address bar

Write `video` and paste whatever your browser's address bar shows. The add-on turns it
into the address of that site's own player while it syncs, because a card template can
substitute a field but cannot transform one — `{{Clip}}` becomes the cell exactly as
written, and YouTube refuses to be framed anywhere except its `/embed` path:

| What you paste | What ends up in the note |
| :--- | :--- |
| `youtube.com/watch?v=ID` · `youtu.be/ID` · `youtube.com/shorts/ID` | `youtube.com/embed/ID` |
| `youtu.be/ID?t=1m30s` | `youtube.com/embed/ID?start=90` — the moment is kept |
| `drive.google.com/file/d/ID/view?usp=sharing` | `drive.google.com/file/d/ID/preview` |
| `vimeo.com/123456789` | `player.vimeo.com/video/123456789` |
| `example.com/lesson.mp4` | unchanged — a direct file plays in the frame too |

So one word covers every case and you never have to know which kind of link you have.
A link that names no single video — a channel, a playlist, a Drive *folder* — is left
alone and **reported as a warning**, because framing one shows an error page where the
video should be. An address already in `/embed` form is left as it is, so re-syncing
never rewrites what it just wrote.

#### Deck-wide keys

Written after the marker, in the `#config` cell itself.

| Key | Values | What it does |
| :--- | :--- | :--- |
| `align` | `left`, `center`, `right` | Alignment for the whole card (a column's own `align` still wins) |
| `speed` | a number — keep it inside 0.5–2.0 | Speaking rate for every spoken column that does not set its own. Unlike the per-column `speed`, the deck-wide one is **not** range-checked, so an absurd value reaches Anki unchallenged |
| `reverse` | switch | Adds a second card template that asks the back and answers with the front. Skipped for cloze rows, and for a card that has nothing on one of its sides |
| `theme` | `sakura` | Dresses the whole card instead of leaving it black on white: `sakura` is a cherry-blossom palette **and** a drift of blossoms strewn behind the text. A theme also points `color=muted` / `color=accent` at its own two colours, and carries a light and a dark version so night mode stays readable. The flowers are drawn in the stylesheet itself, so they need no network and nothing lands in `collection.media`. An unrecognised name is refused with a warning and the card keeps Anki's colours |

#### Worked example

Header row (row 1):

```text
ID | Word | Reading | Meaning | Example
```

Settings row (row 2), cell by cell:

| Column | Its cell in the settings row |
| :--- | :--- |
| `ID` | `#config reverse` |
| `Word` | `side=front; size=48; tts=zh_CN; voices=Huihui` |
| `Reading` | `label=Pinyin; furigana; color=muted` |
| `Meaning` | `size=20` |
| `Example` | `size=16; color=muted; hint` |

One data row (row 3):

```text
42 | 推迟 | 推迟[tuī chí] | to postpone, to delay | 会议推迟到下周。
```

That produces:

- **Front** — `推迟` on its own at 48 px, spoken in Mandarin (preferring the *Huihui*
  voice if that machine has it).
- **Back** — `Reading` with the pinyin printed above the characters, captioned *Pinyin*
  and in the theme's muted grey; `Meaning` at 20 px; `Example` at 16 px, muted, and
  hidden behind a hint link until you click it.
- **A second card** (`reverse`) that asks the back and answers with `推迟`.

Everything not mentioned keeps its default, which is why `Meaning` only needs `size=20`.

#### Caveats

- **Text-to-speech needs the full language code.** `tts=zh` is rejected with a warning
  instead of being guessed at. Anki compares the code against your installed voices with
  an **exact string match**, so a short code matches nothing and plays *silently* —
  the parser refuses rather than shipping you silence.
- **A missing system voice is silence, not an error.** `tts=zh_CN` on a machine with no
  Chinese voice installed plays nothing at all, and nothing warns you: the sheet is fine,
  the machine is not. On Windows, voices are added under
  **Settings → Time & Language → Speech**; macOS has them under
  **System Settings → Accessibility → Spoken Content**.
- **`voices` is a preference, not a requirement.** If none of the named voices exist,
  Anki falls back to any voice for that language — so naming voices stays portable
  across your machines and phones.
- **One cell, one language.** Anki reads the *whole* field, so a cell holding a Chinese
  sentence and its English translation is read end to end by the Chinese voice. Give each
  language its own column if you want each spoken properly.
- **`hint` hides text, not sound.** A column that is both `hint` and `tts` is still read
  aloud when the side appears, even while its text is collapsed.
- **A `theme` colours the card, not the window around it.** On the desktop the top bar
  and the answer buttons belong to Anki, not to the card, so they keep Anki's own
  colours; on AnkiDroid and AnkiMobile the card fills the review screen and the tone
  carries further. Switching Anki between light and dark swaps the theme with it — each
  palette ships both halves, so neither one is left unreadable.
- **`furigana` does nothing visible without the `text[reading]` shape.** A plain `tuī chí`
  cell simply prints as-is.
- **Media columns are *links*, and links need the network.** The URL is fetched every time
  the card is shown, so the picture or player is blank offline, and mobile clients are
  stricter than the desktop about loading remote content. Anki's own design is the
  opposite: media lives in your `collection.media` folder, which syncs with your
  collection and works with the plane in the air. What you buy with `image`/`audio`/
  `video` is a tidier spreadsheet; what you pay is a card that needs a connection. If a
  deck must work offline, put the files in `collection.media` and reference them the
  ordinary Anki way.
- **A video frame reaches the video through a page, not directly.** AnkiMobile and
  AnkiDroid load a card from a `file://` origin, so the webview sends no HTTP `Referer`
  and YouTube refuses the embed — *"Error 153: Video player configuration error"*. No
  `referrerpolicy` fixes that: there is no origin to send *from*. So the card frames
  `player.html` on the preview site, which is served over https, and that page frames the
  video — the request YouTube finally sees carries a real referrer, and it plays inline on
  a phone.
  That page only ever frames YouTube, Vimeo and Google Drive addresses; anything else is
  refused rather than displayed.
  The address lives in the card template, not in your notes, so it is rebuilt on every
  sync — dropping it later costs one re-sync rather than an edit to every row. The price
  is that a video now needs that page reachable as well as YouTube, which is why the card
  also carries a small link under the frame on mobile: if the page ever goes, that link
  still opens the video. Its text is the column's `label` when the settings row gives
  one.
- **`tts` and `furigana` are refused on a media column.** They would act on the address:
  `tts` would read the URL out loud, so it is dropped with a warning, and `furigana` is
  turned off with one. `hint`, on the other hand, is *accepted and currently has no
  effect* — the element still appears as soon as its side does, and nothing warns you.
- **Text styling does not apply to a media column.** `color`, `bold`, `italic` and the
  column's own `align` are skipped for `image`/`audio`/`video`; only `size` (as a width),
  `side`, `label` and the deck-wide `align` reach the card. `size` on an `audio` column is
  accepted but changes nothing visible. A `video` column keeps a 16 : 9 shape, so `size`
  sets its width and the height follows.
- **The Card Layout window does not list the media kind.** Its **Settings** panel predates
  these three keys, so a media column looks bare there; the **Preview** panel and the real
  card do show the element.
- **A switch can be written off.** `bold` turns bold on; `bold=false` (or `no`, `0`,
  `off`, `none`) turns it off, so a shared sheet can spell out both.
- **Typos are reported, not ignored.** `siz=48` or `color=notacolour` produce a warning
  naming the column (*"'Word': 'notacolour' is not a colour name or #hex value"*), and a
  per-column value outside its range (`size=400`, `speed=9`) is refused rather than
  clamped. Every warning is listed in the Card Layout window (`Ctrl+Shift+C`) and written
  to the debug log; the rest of the row still applies.
- **The settings row is never a note.** It is removed before anything is counted, so it
  does not appear in the sync summary's row totals and cannot become a card.
- **Only content columns carry directives.** Anything typed into the settings row's
  `SYNC`, `TAGS` or `SUBDECK n` cells is ignored.
- **Separate the marker from its settings with a space.** `#config align=left` is a
  settings row; the marker is followed by a separator, so both `#config align=left`
  and `#config;align=left` are recognised, while a real column value like
  is imported as a note.
- **On a cloze row, `cloze:` wins.** A column carrying `{{c1::…}}` is rendered through
  Anki's cloze filter, so `hint` and `furigana` do not apply to it — Anki refuses to save
  a cloze note type whose template does not reference the field through `cloze:`.

### How tags are built

Every note gets three kinds of tag:

1. `sheets2anki` — on every note the add-on owns, so you can find or bulk-remove them
   without touching your own notes.
2. `sheets2anki::<subdeck path>` — mirrors the deck hierarchy, so the tree is browsable
   from the Browse sidebar.
3. Whatever the `TAGS` column lists.

All tag text is normalized: lower-cased, spaces and `:`/`;` turned into `_`, runs of
`_` collapsed, and any remaining punctuation stripped. `Unit 3: Intro` becomes
`unit_3_intro`.

### Cloze cards

**A sheet is a cloze sheet or it is not — say which column carries the deletions:**

```
ID        Word      Example
#config             cloze
1         熟悉       我对这里{{c1::很熟悉}}，也{{c2::常来}}。
```

That column becomes the prompt wherever it sits in the sheet, and Anki makes **one
card per deletion** — two, above. Every other column renders normally beside it.

The declaration is not bureaucracy. A note type has **one** template set shared by
every row, so "which column is clozed" has to be answered once for the sheet; and
Anki renders a field wrapped in `{{cloze:…}}` that holds *no* deletion as **nothing
at all**, so the wrong guess silently blanks a column. Declaring it also keeps the
template a function of your settings row alone — a template that changed with your
*data* could rewrite the note type mid-sync, and removing a template deletes its
cards and their review history.

A row containing `{{c1::…}}` in a sheet that declares no `cloze` column is
**reported** — in the debug log and on the [preview site](#preview-a-sheet-in-your-browser) —
because that markup would otherwise print on the card as literal text.

Cloze note types carry exactly one template, so `reverse` is skipped for them.

### Typed answers

`type` on a column makes Anki draw an input box on the question and compare what you
type against that column:

```
ID        Hán tự    Pinyin        Ví dụ
#config             type=nc       cloze
```

`type=nc` drops diacritics from the comparison, so typing `shuxi` matches `shúxī` —
which is what you want when the tone marks are the hard part but not the point. Anki
honours **one** `{{type:…}}` per card, so one column per sheet; a second is ignored
with a warning. The box is not repeated on the `reverse` card, which asks the other
direction. On a cloze sheet, `type` on the clozed column types the deletions
themselves (`{{type:cloze:…}}`).

---

## Features

Everything lives under **Tools → Sheets2Anki**.

### Add New Remote Deck

**What it does** — connects one Google Sheets spreadsheet as a new remote deck.
**Where** — Tools → Sheets2Anki → *Add New Remote Deck* (`Ctrl+Shift+A`).

**How it works.** You paste the ordinary `docs.google.com/spreadsheets/d/<ID>/edit…`
link. The add-on rewrites it to `…/export?format=tsv` and downloads that with a plain
HTTP GET (30 s timeout, no authentication). The download is parsed as TSV; quoted cells
keep their embedded newlines, so multi-line answers survive. The **spreadsheet ID**, not
the URL, is the deck's identity — reopening the same sheet from a different link is
recognised as the same deck.

The deck name is derived automatically, in this order: the spreadsheet's HTML `<title>`,
then the download's `Content-Disposition` filename, then a generated fallback built from
the spreadsheet ID. The deck is created as `s2a_<that name>`. If the name
collides with an existing remote deck, a ` #conflict1`, ` #conflict2`, … suffix is added
and the dialog tells you.

**Caveats**

- **Only the first tab of the spreadsheet is ever synced.** The export URL is built
  deliberately without a `gid`, so any `#gid=…` in the link you paste is ignored. Put
  your cards on the first sheet tab.
- The sheet must be shared as *Anyone with the link → Viewer* (or published to the web).
  Otherwise the download returns HTTP 400.
- Only Google hosts are ever fetched. A stored URL pointing anywhere else is refused —
  a deliberate guard against a malicious URL turning Anki into an HTTP client for
  internal addresses.
- There is no name field. If you want a different deck name, rename the spreadsheet and
  sync — see [Renames](#renames-are-driven-by-the-spreadsheet).
- Re-adding a spreadsheet that is already connected is blocked; a spreadsheet that was
  *disconnected* is reconnected instead.

### Synchronize Remote Decks

**What it does** — downloads each selected sheet and reconciles it with Anki.
**Where** — Tools → Sheets2Anki → *Synchronize Remote Decks* (`Ctrl+Shift+S`).

**How it works.** The dialog lists every connected deck with a checkbox and a card
count. Your ticks are saved to the add-on's settings the moment you click them, so the
selection is remembered next time (even if you then press Cancel). Pressing
**Synchronize Selected** runs, in order:

1. a rebuild of the card templates of every connected deck from the settings its last
   sync read out of the sheet;
2. per deck: download → parse → create/update/delete notes → name-consistency pass;
3. removal of subdecks that ended up empty;
4. application of the deck-options mode;
5. after you close the summary, the AnkiWeb sync, if enabled.

The summary window has three views — **📊 Summary**, **📑 Full Details**,
**⚠️ Errors Only** — and reports these row counts:

| Report line | Meaning |
| :--- | :--- |
| Total spreadsheet rows | Every row below the header |
| Rows with content (Valid ID) | Rows whose `ID` cell is filled |
| Rows skipped (Missing ID) | Rows with content but a blank `ID` — these are never synced |
| Empty rows (Ignored) | "Ghost rows": rows whose only non-blank cell is `SYNC` (a checkbox dragged past the last real row). Counted, never reported as broken |
| Rows enabled / disabled for sync | The `SYNC` column split |
| Created / Updated / Deleted / Unchanged | What happened in Anki |

**Caveats**

- Syncing runs on Anki's main thread behind a progress dialog; the UI is busy while it
  works.
- A failed deck does not abort the others; its error appears in the summary.

### Disconnect a Remote Deck

**What it does** — stops syncing a deck, and optionally deletes it.
**Where** — Tools → Sheets2Anki → *Disconnect a Remote Deck* (`Ctrl+Shift+D`).

**How it works.** Tick the decks to disconnect, then decide with a single checkbox:

> 🗑️ **Delete local data (decks, cards, notes and note types)** — **checked by default.**

Left checked, disconnecting deletes the local deck and all its subdecks, every card and
note in them, and the deck's `Sheets2Anki - … - Basic` / `- Cloze` note types (only if no
other deck uses them). Unchecked, everything stays in Anki exactly as it is and only the
link to the spreadsheet is dropped. Either way, orphaned Sheets2Anki deck-options presets
are cleaned up afterwards.

**Caveats**

- **Read the checkbox before confirming** — the destructive option is the default, and
  the deletion cannot be undone from inside the add-on. Anki's own *Undo* and Anki's
  automatic backups (Preferences → Backups) are the recovery, and the spreadsheet is
  still there to sync from.
- Reconnecting means adding the spreadsheet again; scheduling of deleted cards is gone.

### Configure Card Layout

**What it does** — shows, per deck, what the add-on read out of the sheet's
[settings row](#the-settings-row): which fields it put on which side, how they are
styled, what it did not understand, and which text-to-speech voices this machine has.
**Where** — Tools → Sheets2Anki → *Configure Card Layout* (`Ctrl+Shift+C`).

> **This window is read-only.** The spreadsheet is the only place a card's appearance is
> edited. That is deliberate: with two places able to change one setting, the loser is
> silently overwritten on the next sync and the control that "does nothing" is impossible
> to diagnose. To change something, edit the settings row and sync again.

**What it shows**

| Panel | Contents |
| :--- | :--- |
| **Front** / **Back** | The fields the sheet put on each side, in order — and which columns `side=hide` kept off the card entirely |
| **Settings** | Each column's parsed directives — size, colour, alignment, hint, furigana, speech |
| **Warnings** | Everything the settings row asked for that the add-on could not understand, named per column |
| **Voices** | The text-to-speech voices installed on *this* computer, so you can tell a wrong `tts=` code from a missing voice |
| **Preview** | An approximation of the generated templates, with `[FieldName]` placeholders |

**How it works.** Every sync parses the settings row, renders it into the actual Anki
card templates (`qfmt`/`afmt`), and writes those into the deck's note types. Each field
is wrapped in Anki's `{{#Field}}…{{/Field}}` conditional, so a row that leaves a cell
blank shows nothing there instead of an empty gap.

The parsed result of the last sync is cached in **Anki's own collection config** (key
`sheets2anki::sheet_settings`), not in the add-on's local files. Anki's config table is
part of what AnkiWeb synchronizes, so a second machine renders identical cards before it
has ever downloaded the sheet itself — and this window can show a deck's settings without
going back to Google.

The reverse card (deck-wide `reverse`) is a *second template on the same note type*, not
a second note. Both directions are scheduled independently from one spreadsheet row, and
removing `reverse` from the sheet later removes those cards without touching your
content.

**Caveats**

- **Changes only reach the cards on the next sync** (`Ctrl+Shift+S`).
- **Reverse cards are not available for cloze notes** — Anki allows a cloze note type
  exactly one template.
- A deck that has never been synced has nothing cached yet, so it is skipped by the
  template rebuild and shows nothing here until its first sync.
- Hand-editing a Sheets2Anki note type in Anki's own card editor does not stick: the next
  sync rebuilds those templates from the sheet.

### Configure AnkiWeb Sync

**What it does** — kicks off a normal AnkiWeb sync right after a deck sync, so the new
cards reach your phone without a second click.
**Where** — Tools → Sheets2Anki → *Configure AnkiWeb Sync* (`Ctrl+Shift+W`).

Two modes: **Disabled**, or **Sync with AnkiWeb**.

**How it works.** There is no separate sync implementation — the add-on simply calls
Anki's own sync (`mw.sync.sync()`, the same code path as Tools → Sync), fired once you
close the Sheets2Anki summary window. Progress appears in Anki's normal status bar.

A **Test Connection** button fetches `ankiweb.net` and reports both network reachability
and whether your profile actually has AnkiWeb credentials.

**Caveats**

- You must already be logged into AnkiWeb in Anki (**Tools → Sync** once). If not, the
  add-on warns you and does nothing.
- Conflicts (full upload / full download prompts) are handled by Anki's own dialogs, not
  by the add-on.
- Enabled by default in the shipped configuration.

### Configure Deck Options

**What it does** — decides which Anki deck-options preset your remote decks use.
**Where** — Tools → Sheets2Anki → *Configure Deck Options* (`Ctrl+Shift+O`).

| Mode | Behaviour |
| :--- | :--- |
| **Shared Options** | Every remote deck (and subdeck) uses one preset named `Sheets2Anki - Default Options` |
| **Individual Options** | Each remote deck gets its own preset named `Sheets2Anki - <deck name>` |
| **Manual Configuration** | The add-on never touches deck options; you manage them in Anki |

**How it works.** These are real Anki deck-options presets, visible in Anki's own preset
dropdown. The add-on creates the preset if it is missing and assigns it to the deck and
every subdeck. The root `Sheets2Anki` deck additionally gets a preset called
`Sheets2Anki - Root Options`. This runs at the end of every sync and immediately when you
press **✓ Apply**.

A newly created preset is seeded with 20 new / 200 review cards per day (30 / 150 for the
root preset). **An existing preset is never overwritten** — once you tune
`Sheets2Anki - Default Options` by hand, your settings survive every sync.

**Caveats**

- After each sync, presets whose name starts with `Sheets2Anki` and that no deck uses are
  deleted. Don't park an unused preset under that name.
- Switching to **Manual** does not restore whatever preset the decks had before; they
  simply keep what they were last given.
- The shipped default is **Individual**.

### Debug Mode

**What it does** — writes a detailed log of everything the add-on does.
**Where** — Tools → Sheets2Anki → *Debug Mode* (`Ctrl+Shift+L`).

**How it works.** With *Enable Debug Mode* ticked (it applies immediately, no Save
button), every internal step is timestamped, categorized (`SYNC`, `REMOTE_DECK`,
`NOTE_PROCESSOR`, `IMAGE_PROCESSOR`, `NAME_CONSISTENCY`, …), printed to Anki's console and
appended to `debug_sheets2anki.log` inside the add-on folder. The dialog shows the file
inline with **Refresh**, **Scroll to End**, **Clear Log** and **Open Log Folder** buttons.

A second checkbox, *Accumulate logs over time*, decides whether each sync starts a fresh
log or appends to the existing one.

**Caveats**

- With debug off, the log file is not written at all — turn it on *before* reproducing a
  problem.
- With accumulation on the file grows without limit; clear it occasionally.
- The log records spreadsheet content (field values, note IDs). Review it before
  attaching it to a public issue.

---

## How syncing behaves

### Notes are keyed by `ID`

Each row's `ID` is written into the note's first field, also called `ID`. On every sync
the add-on searches `deck:"s2a_<name>" OR deck:"s2a_<name>::*"`, reads
that field on each note it finds, and matches rows to notes by it.

Consequences worth internalizing:

- **Never change an ID.** Editing an ID in the sheet reads as "the old row was deleted
  and a new one appeared": the old note is removed and a new one is created with no
  review history.
- **Never reuse an ID.** Two rows with the same ID collapse onto one note. This is
  detected: duplicates are listed as an error in the sync summary
  (*"Duplicate IDs in the spreadsheet (n): …"*).
- **A row with a blank `ID` is never synced** — it is counted as *Rows skipped (Missing ID)*.
- Moving a Sheets2Anki note out of its `s2a_<deck>` tree in Anki makes it
  invisible to the matcher, and the next sync will recreate the row as a new note.

### What each change to the sheet does

| You do this in the sheet | Sync does this |
| :--- | :--- |
| Add a row | Creates a note |
| Edit a cell | Updates only that field; the note keeps its scheduling |
| Change `SUBDECK n` | Moves the note's cards to the new subdeck and rewrites its tags |
| Set `SYNC` to a non-truthy value | **Preserves the note untouched** and stops updating it — it is *not* deleted |
| Set `SYNC` back to `TRUE` | Resumes updating that note |
| Delete a row | **Deletes the note** (its ID is no longer anywhere in the sheet) |
| Add a column | Adds a field of that name to the deck's note types and puts it on the back of the card |
| Remove a column | **Keeps the field and its content in Anki** and stops rendering it. Nothing you have already collected is deleted |
| Rename a column | Reads as "old column removed, new column added": a new empty field appears; the old field keeps its data |
| Add `{{c1::…}}` to a row | The note is recreated as a Cloze note (see below) |
| Edit the [settings row](#the-settings-row) | Rebuilds the deck's card templates. Notes, fields and scheduling are untouched — only the presentation changes |

### Safety guards

- **Zero valid rows ⇒ no deletions.** If the download returns a sheet where *every* row
  has an empty `ID` — an empty sheet, the wrong tab, a truncated export — every existing
  note would look obsolete. The add-on refuses: it deletes nothing and reports
  *"Sync safety: the spreadsheet returned no valid rows … Skipped deletion of N existing
  note(s)"*.
- **A note type change never loses the note.** When a row switches between Basic and
  Cloze, the note must be recreated (Anki has no in-place retype). The replacement is
  created *first* and the original only removed once it exists. The review history of
  that note is reset — that is unavoidable.
- **A removed column never deletes data** — see the table above.

### Renames are driven by the spreadsheet

The remote deck name is re-read from the spreadsheet's title on every sync. When it
changes, the add-on renames, in one cascade: the Anki deck
(`s2a_<new name>`), the note types (`Sheets2Anki - <new name> - Basic` / `-
Cloze`), and — in *Individual* deck-options mode — the options preset.

> ⚠️ **Renaming a Sheets2Anki deck or note type inside Anki does not stick.** The next
> sync finds the deck by its stored ID, sees a name it does not expect, and renames it
> back. To rename a deck, rename the spreadsheet.

### After every sync

Subdecks that ended up with no cards are removed, and the deck-options mode is
(re)applied to every remote deck and subdeck.

---

## Keyboard shortcuts

All of these live under **Tools → Sheets2Anki**. On macOS, ⌘ replaces Ctrl.

| Shortcut | Menu entry |
| :--- | :--- |
| `Ctrl+Shift+A` | Add New Remote Deck |
| `Ctrl+Shift+S` | Synchronize Remote Decks |
| `Ctrl+Shift+D` | Disconnect a Remote Deck |
| `Ctrl+Shift+O` | Configure Deck Options |
| `Ctrl+Shift+W` | Configure AnkiWeb Sync |
| `Ctrl+Shift+C` | Configure Card Layout |
| `Ctrl+Shift+L` | Debug Mode |

---

## Where your settings live

| Setting | Stored in | Travels via AnkiWeb? |
| :--- | :--- | :--- |
| The parsed settings row (sides, sizes, colours, speech, reverse card) | Anki's collection config, key `sheets2anki::sheet_settings` — a cache of what the last sync read; the sheet stays the source of truth | **Yes** |
| Note types and card templates | Anki's collection | **Yes** |
| Connected decks, deck-options mode, AnkiWeb mode, debug flags | `meta.json` in the add-on folder | No — machine-local |

`config.json` in the add-on folder holds only the shipped defaults used to seed
`meta.json` on first run. Out of the box: deck options *Individual*, AnkiWeb sync *on*,
debug *off*.

---

## Troubleshooting

**"HTTP Error 400: The spreadsheet is not publicly accessible."**
The sheet is private. Share → *Anyone with the link* → *Viewer*, or File → Share →
Publish to web.

**"Mandatory header missing: 'ID'"**
Row 1 of the first tab has no `ID` column. Note that only row 1 is read as the header
row — a title row above it will break this.

**"The sheet has no content columns"**
The sheet only has reserved headers (`ID`, `SYNC`, `TAGS`, `SUBDECK n`). Add at least one
column of your own.

**"URL must be a Google Sheets edit URL in the format …"**
Paste the address-bar link that looks like
`https://docs.google.com/spreadsheets/d/<ID>/edit?usp=sharing`.

**"Refusing to download from non-Google host …"**
The stored URL does not point at Google. Disconnect the deck and add it again with the
real sheet link.

**"Timeout of 30s while accessing the URL"**
The export did not finish in time — usually a very large sheet or a slow connection.
Retry; if it persists, split the sheet.

**"Duplicate IDs in the spreadsheet (n): …"**
Two or more rows share an `ID`. Only one of them ends up in Anki. Make every `ID` unique.

**"Sync safety: the spreadsheet returned no valid rows …"**
Nothing was deleted — on purpose. Check that the *first tab* is the one with your cards,
that row 1 is the header row, and that the `ID` column is filled, then sync again.

**Cards appear but a change to the settings row did nothing.**
The settings row is only read during a sync — press `Ctrl+Shift+S`. Then open
`Ctrl+Shift+C` and read the **Warnings** panel: a mistyped key (`siz=48`) or an
out-of-range value is reported there instead of being applied. The same warnings are
written to the debug log (`Ctrl+Shift+L`) while debug mode is on.

**My first note was swallowed / a row full of `key=value` text became a card.**
The settings row is recognised only when its `ID` cell *starts with* `#config`. Write
`#config` on its own, or `#config` followed by a **space** and the deck-wide settings —
`#configuration` is a value, not the marker, so that row is imported as a note.
Conversely, a row that accidentally begins with `#config` is treated as settings and
never becomes a card.

**Text-to-speech is silent.**
Three separate causes, in the order worth checking: (1) the code is short — `tts=zh`
matches no voice, use `tts=zh_CN`; the add-on refuses short codes with a warning;
(2) that language has no voice installed on this computer — Anki says nothing, it just
plays silence (Windows: **Settings → Time & Language → Speech**; macOS:
**System Settings → Accessibility → Spoken Content**). The Card Layout window
(`Ctrl+Shift+C`) lists the voices this machine actually has; (3) the field is empty for
that row — an empty field is never spoken.

**The wrong language is read out for part of a card.**
Anki reads the whole field with one voice. A cell that holds a sentence *and* its
translation is read end to end by that column's voice — split them into two columns, each
with its own `tts=`.

**`furigana` prints nothing above the text.**
The cell has to be written `推迟[tuī chí]`: text, then the reading in square brackets. A
cell without that shape renders unchanged.

**Deck-wide `reverse` does nothing for some notes.**
Those rows are cloze notes. Anki's cloze note types support exactly one template.

**Anki renamed my deck back after I renamed it.**
Expected. Rename the spreadsheet instead — see
[Renames](#renames-are-driven-by-the-spreadsheet).

**Images do not appear on the cards.**
A picture *pasted into a cell* is not something Anki can reach — the cell holds a
drawing, not an address. Put the picture somewhere with a link (Drive, imgur, a
repository), put that link in the cell, and mark the column `image` in the settings
row. The card then needs a network connection to show it.

**"AnkiWeb not configured - access Tools > Sync in Anki"**
Log in to AnkiWeb once through Anki's own Sync button; the add-on reuses that session.

**Anything else.**
Enable **Debug Mode** (`Ctrl+Shift+L`), reproduce the problem, then read or attach
`debug_sheets2anki.log` (the dialog's *Open Log Folder* button takes you there). Please
report issues at
[github.com/tannc28/sheets2anki/issues](https://github.com/tannc28/sheets2anki/issues).

---

## Contributing

Development setup, the test suite and the architecture are documented in
[`CLAUDE.md`](CLAUDE.md) and the build scripts under [`scripts/`](scripts/).

> **Maintainer note.** An extra menu entry, *Import Test Deck* (`Ctrl+Shift+T`), appears
> only while `IS_DEVELOPMENT_MODE` is `True` in `src/templates_and_definitions.py`. The
> build scripts flip it to `False`, so it never ships to users. It connects
> [the example workbook](#the-example-workbook), which is also what the preview
> site loads — so a change to a directive can be checked against a real deck
> without anyone having to keep a private spreadsheet in step with the code.

## License

Released under the [MIT License](LICENSE).
