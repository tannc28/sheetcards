# The example workbook

`sheetcards-examples.xlsx` holds thirty-one sheets. Each one is a small deck you
could actually study, and each one shows a feature, from the smallest sheet that
works to the more advanced settings. The same tour is on the website, in
Vietnamese and English:
[File ví dụ](https://tannc28.github.io/sheetcards/docs/examples/) ·
[The example workbook](https://tannc28.github.io/sheetcards/docs/en/examples/).

```text
https://github.com/tannc28/sheetcards/blob/main/examples/sheetcards-examples.xlsx
```

## Opening it

- **Tạo flashcard / Make flashcards** (<https://tannc28.github.io/sheetcards/create/>): paste
  the link above, or upload the file
  ([direct download](https://tannc28.github.io/sheetcards/sheetcards-examples.xlsx)).
  *Xem ví dụ* on the landing page opens it on sheet 15. Pick a sheet in the source
  bar, check its cards, and download the `.apkg`.
- **Tạo Sheet / Create sheet** (<https://tannc28.github.io/sheetcards/sheet/>):
  to start your own sheet from one of these, download the file and use **Mở file
  để thêm từ** (*Open a file to add words*), then pick the sheet. To keep only its
  columns and settings row as a starting point, upload it under **Template của
  bạn** (*Your templates*).
- **The add-on**: paste the link into **Tools → SheetCards → Connect a Google
  Sheet…**; every sheet in the file becomes its own deck.

A sheet without `name=` becomes a deck named after the file and the sheet:
`sheetcards-examples::05 Type the answer (gõ đáp án)` from Make flashcards,
`sc_sheetcards-examples::…` from the add-on. Sheet 16 declares
`name=SheetCards examples: Picture words`, so both name its deck that, and both
recognise the same notes.

Tab names carry a Vietnamese gloss in brackets, because the workbook is shown to
Vietnamese learners. Most decks are English for Vietnamese speakers; Chinese,
Japanese, Korean and others appear where a feature belongs to them.

## The sheets

| Sheet | What it shows |
| :--- | :--- |
| `01 Basic (cơ bản)` | `ID`, `Front`, `Back` and nothing else. No settings row and no `SYNC` column, so every row syncs; the first column is the front, the rest the back. |
| `02 Sync & subdecks (deck con)` | The reserved columns. `SYNC` accepts `yes`, `x`, `1`, `TRUE`, `✓`; empty and `no` are off. `Topic` and `Subtopic` build the deck path through `subdeck=1`/`subdeck=2` in the settings row (they stay fields, never drawn); a row naming no level goes to `Unsorted`. `TAGS` splits on commas or semicolons. |
| `03 Card layout (bố cục thẻ)` | The first settings row: `side`, `size` (with a `px` suffix), the three ways to write `color` (`accent`, `#hex`, a CSS name), `bold`, `italic`, a bare `label` (captioned with the column's own name), `hint`, `side=hide`, and `align` per column. |
| `04 Reverse (thẻ ngược)` | `#config reverse`: one row, two cards, scheduled separately. |
| `05 Type the answer (gõ đáp án)` | `type=nc`: *cai cay* is accepted for **cái cây**, but `đ` is a letter and must be typed. |
| `06 Cloze (điền chỗ trống)` | One column declared `cloze`. Each deletion is a card; `z02` has `c1` and `c2`, so it makes two. |
| `07 Images (hình ảnh)` | `image` with `size`: see the picture, recall the Chinese word. |
| `08 Audio (âm thanh)` | `audio`: a real person's recording from Wikimedia Commons, then the word. The files are `.ogg`; for iPhone, `.mp3` is the safer choice. |
| `09 Video (video nhúng)` | Every YouTube link form that is rewritten to a player (`watch?v=`, `youtu.be`, `/shorts/`, `/embed/`) plus a direct file; `hint` puts the player behind a disclosure. Framed players do not play in AnkiDroid or AnkiMobile. |
| `10 Speech (đọc thành tiếng)` | `tts=en_US` (always the full code), `voices=` as a preference, `speed=0.9` on the spoken column, and a `side=hide` column read again at `speed=0.5`. |
| `11 Chinese writing (gõ chữ)` | `type` on the character, a stroke-order `image` behind `hint`, `tts=zh_CN` (which also picks the Chinese font), and `subdeck=1` filing by HSK level without the column ever being drawn. |
| `12 Chinese drawing (viết tay)` | `draw`: write the character stroke by stroke on the question, watch it animated on the answer, filed by `Level` (`subdeck=1`). Needs the network. |
| `13 Furigana (phiên âm kanji)` | `furigana`: `漢字[かんじ]` drawn as ruby, and read aloud from the reading. |
| `14 Any headers (mọi ngôn ngữ)` | Headers written `汉字`, `拼音`, `释义`, `例句`: only `ID`, `SYNC` and `TAGS` are reserved. |
| `15 Theme + subdeck (màu, tầng)` | `theme=sakura`, three deck levels from `Language`, `Level` and `Word class` (`subdeck=1`…`3`, `English::B1::Verbs`), `TAGS` and `tts`. Make flashcards' example opens here. |
| `16 Picture words (từ vựng ảnh)` | `image` and `audio` on one card, `subdeck=1` on `Group`, and the marker `#config name=…; next=i07`: the set's name and identity, and the next ID to hand out. |
| `17 Draw & type (viết và gõ)` | `draw` for the character and `type=nc` for its pinyin on one card. |
| `18 Grammar cloze (ngữ pháp)` | English grammar points: `cloze` plus `type` on the same column, so the missing word is typed. |
| `19 Dictation (nghe rồi gõ)` | `side=hide; tts=en_US; type`: the sentence is only heard, then typed. |
| `20 Video lesson (bài video)` | `video` on the front: the clip is the question, filed by lesson. |
| `21 Formulas & code (công thức)` | `math=block` (Anki's own MathJax) and `code=python`. |
| `22 Arabic (phải sang trái)` | Arabic runs right to left with no key (every block carries `dir="auto"`), in `font=serif`. |
| `23 Haiku (thơ haiku)` | Haiku read with `tts=ja_JP`, which also draws them in the Japanese font. |
| `24 Korean (tiếng Hàn)` | `tts=ko_KR`, which also picks the Korean font. |
| `25 Traditional (chữ phồn thể)` | Traditional read with `tts=zh_TW` (so drawn in the Traditional font) beside Simplified in `font=sc`. |
| `26 Shell commands (dòng lệnh)` | `code=bash`, filed by `subdeck=1`. |
| `27 Web dev (HTML & JS)` | Two code columns, `code=html` and `code=javascript`; an empty one draws nothing. |
| `28 Chemistry (hoá học)` | An answer in words above a `math=block` equation. |
| `29 Phrasal verbs (cụm động từ)` | `cloze` on the particle, the sentence read with `tts=en_US`. |
| `30 German (tiếng Đức)` | der/die/das asked on the front, `tts=de_DE`, a slower example, a `label`led plural. |
| `31 Spanish (tiếng Tây Ban Nha)` | `type=nc` again: *el arbol* passes for **el árbol**, but `ñ` must be typed. |

The six listed themes are `paper`, `contrast`, `matcha`, `momiji`, `yuki` and
`sakura`; the workbook uses `sakura`, and Create sheet offers all six.

## Editing it

The workbook is generated. Its grids live in `SHEETS` at the top of
[`scripts/build_examples.py`](../scripts/build_examples.py); edit that, then:

```bash
python scripts/build_examples.py            # rebuild the workbook
python scripts/build_examples.py --check    # fail if it is out of date
```

`tests/test_examples.py` fails if the file does not match `SHEETS`, if a sheet
warns or renders an empty front, or if a settings-row key has no example
anywhere. A new directive goes on the sheet whose deck would want it, in the same
commit.
