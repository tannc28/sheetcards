# `=PINYIN()` for Google Sheets

A spreadsheet function that writes the pinyin for Chinese text, with real tone
marks. No API key, no network call, no quota: the dictionary travels with the
script.

```
=PINYIN(A2)         行动             →  xíngdòng
=PINYIN(E2)         我们需要立即行动   →  wǒmen xūyào lìjí xíngdòng
=PINYIN(A2:A200)    a whole column at once
```

One function, one way of writing the result — the standard one. The dictionary
stores tone numbers internally because they are ASCII and half the bytes, but a
cell only ever shows the tone marks.

## Setup, once per spreadsheet

1. In the sheet: **Extensions → Apps Script**.
2. Paste `Pinyin.gs` into the file that is already open, replacing what is there.
3. **+ → Script** for a second file, name it `PinyinData`, paste `PinyinData.gs`
   into it. It is 1.2 MB, so the editor takes a moment.
4. **Save**. Back in the sheet, type `=PINYIN(A2)`.

No deployment, no authorization prompt — a function that only reads its argument
needs no permission to anything.

## Why the whole word is looked up

`行` is *xíng* in 行动 and *háng* in 银行. Any tool that maps character by
character gets one of the two wrong every time, and a deck teaches whatever it is
given. So the lookup is by word: text is cut into words first, and each word is
read from CC-CEDICT.

The cut runs longest-match from both ends and keeps the better result. Left to
right alone commits too early — in 新词典 it takes 新词 and strands 典, so a
dictionary comes out as *xīncí diǎn* instead of *xīn cídiǎn*.

Also handled: `西安` → *xī'ān*, not *xīān* — without the apostrophe it could be
read as one syllable *xian*. `花儿` → *huār*, because erhua is a suffix rather
than a syllable. `绿` → *lǜ*.

## Why it starts instantly

Nothing is parsed when the function is first called. Both tables in
`PinyinData.gs` are sorted, so a lookup is a binary search straight into the text
— about twenty string comparisons — rather than a hundred thousand object
properties built up front and then thrown away.

That distinction matters more here than it normally would: Sheets runs a custom
function inside an execution it starts and discards as it pleases, so work done
"once" is really done once *per execution*, and one column can pay for it several
times. Building the tables cost about 175 ms every time; the search costs 1.4 µs
per word and nothing at startup.

A blank cell, and a cell with nothing Chinese in it, are answered before the
dictionary is touched at all — `=PINYIN(A2:A500)` over four hundred empty rows
does no lookups.

## What it will not do

- **Chinese only.** Japanese kanji (図書館, 駅) are not in this dictionary and come
  back untouched — which is the right answer, not a failure.
- **No tone sandhi.** 你好 is written *nǐhǎo*, the way a dictionary writes it, not
  *níhǎo* the way it is said.
- **No capitals.** 北京 is *běijīng*, not *Běijīng*. Proper nouns were folded to
  lower case to halve the size of the dictionary.
- **Segmentation is a heuristic**, not an understanding of the sentence. It is
  right nearly always and quietly odd occasionally; on a deck you are reviewing
  anyway, that is a fair trade.

## Before syncing to Anki

A custom function recalculates when the file opens. This one is local and fast,
so that is normally invisible — but a cell that is still `Loading...` or holds an
error is what the add-on would import. When a pinyin column is settled, select it
and **Copy → Paste special → Values only**. The sheet then holds plain text, and
what Anki gets is exactly what you can see.

## Rebuilding the dictionary

`PinyinData.gs` is generated, not written:

```bash
curl -sSL -o cedict.txt.gz https://www.mdbg.net/chinese/export/cedict/cedict_1_0_ts_utf-8_mdbg.txt.gz
gunzip cedict.txt.gz
python build_data.py          # writes PinyinData.gs
node test_pinyin.js         # checks the readings a learner would notice
```

Two tables come out. A **character table** holds each character's usual reading,
worked out by counting how it is read across every word in the dictionary —
CC-CEDICT lists readings in headword order, not by how often anyone meets them,
so taking the first would make 行 come out *háng*. A **word list** holds the
words; most are simply their characters in order and carry no reading at all,
which is what fits 108,000 words in one file.

## Licence

The dictionary is [CC-CEDICT](https://www.mdbg.net/chinese/dictionary?page=cedict),
licensed **CC BY-SA 4.0**. Keep the attribution in `PinyinData.gs`, and if you
publish anything built from it, it carries the same licence.
