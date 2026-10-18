# The example workbook

Every feature has a working example, and they all live in one file of
thirty-one sheets, ordered from simple to advanced. Each sheet is a deck you could
study, and each shows one feature.

```text
https://github.com/tannc28/sheetcards/blob/main/examples/sheetcards-examples.xlsx
```

- **See it in [Sheet to Anki](../../create/#example)**: paste the link above,
  or [download the file](../../sheetcards-examples.xlsx) and upload it. Pick a
  sheet in the bar at the top, check the cards, then Download `.apkg`.
- **Start your own sheet from one in [Create sheet](../../sheet/)**: download
  the file, press **Open .xlsx/.csv file** and pick the sheet. To keep only
  its columns and settings row, upload the file under **Your templates**.
- **With the add-on**: paste the link into **Tools → SheetCards → Connect a Google
  Sheet…**; every sheet in the file becomes its own deck.

A sheet without `name=` becomes a deck named after the file and the sheet, such
as `sc_sheetcards-examples::05 Type the answer (gõ đáp án)`. Sheet 16 declares
`name=`, so its deck carries exactly that name, with no `sc_`, from the `.apkg` and from the add-on.

Most of it is English for Vietnamese speakers; Chinese, Japanese, Korean and
others appear where a feature belongs to them. Nothing in SheetCards is specific
to one language: a deck of anatomy works the same way. The quickest way to learn
a feature is to find the sheet below that uses it and copy its settings row.

| Sheet | What it shows |
| :--- | :--- |
| `01 Basic (cơ bản)` | `ID`, `Front`, `Back` — a word each in English, Chinese, Japanese, Korean, German and Spanish, answered in Vietnamese. No settings row, no `SYNC` |
| `02 Sync & subdecks (deck con)` | `SYNC` gating, `SUBDECK 1`/`2` (a row naming no level goes to `Unsorted`), `TAGS` |
| `03 Card layout (bố cục thẻ)` | `side`, `size`, all three colour forms, `bold`, `italic`, `label`, `hint`, `side=hide`, deck-wide `align` |
| `04 Reverse (thẻ ngược)` | one row, two cards |
| `05 Type the answer (gõ đáp án)` | `type=nc`, so the Vietnamese marks do not have to be typed |
| `06 Cloze (điền chỗ trống)` | a declared `cloze` column, including a row with two deletions |
| `07 Images (hình ảnh)` | `image` on the prompt, with `size` — the picture asks and the Chinese word answers |
| `08 Audio (âm thanh)` | `audio`, listen-then-recall: an English word spoken by a person, not a synthesiser |
| `09 Video (video nhúng)` | every YouTube link form that is turned into a player, plus a direct file |
| `10 Speech (đọc thành tiếng)` | `tts=en_US`, a `voices=` preference, deck-wide `speed`, and a hidden column that repeats the phrase at half speed |
| `11 Chinese writing (gõ chữ)` | write the character, then check it against a stroke-order animation — `type` + `image` + `hint` + `tts` on one card, and `subdeck=1` filing it by HSK level |
| `12 Chinese drawing (viết tay)` | `draw` — you write the character stroke by stroke and each stroke is marked |
| `13 Furigana (phiên âm kanji)` | `furigana` over kanji |
| `14 Any headers (mọi ngôn ngữ)` | headers written as `汉字`, `拼音`, `释义`, `例句` |
| `15 Theme + subdeck (màu, tầng)` | English vocabulary filed three `SUBDECK` levels deep — `English::B1::Verbs` — in `theme=sakura`, spoken, and sorted by the word |
| `16 Picture words (từ vựng ảnh)` | a picture on the front and a native recording on the back — `image` and `audio` on one card, filed by `Group`; its `#config` cell carries `name=` (the set's name, which is also the deck's identity) and `next=` |
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
[`scripts/build_examples.py`](https://github.com/tannc28/sheetcards/blob/main/scripts/build_examples.py),
and the test suite fails if any setting has no example in it.
[`examples/README.md`](https://github.com/tannc28/sheetcards/blob/main/examples/README.md)
says more about each sheet and how to edit the file.
