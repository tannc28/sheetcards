"""The guide an AI assistant reads to write a SheetCards CSV: ``/ai.md`` and ``/llms.txt``.

A learner gives ChatGPT, Gemini or Claude the address of ``ai.md`` and says what
cards they want; the assistant answers with a CSV that opens in Sheet to Anki or
Create sheet without a warning. The page is plain Markdown because that is what
an assistant fetching a URL reads cleanly, and English because that is what every
model follows best — the learner talks to it in their own language.

Nothing in it is written twice. The settings-row keys, their values, the fonts,
the colours and the themes are read from ``sheet_config`` (the copy the site
ships), and every recipe is one of Create sheet's own templates from
``build_site.sheet_templates()`` — or, for cloze, the example workbook's sheet —
with ``name=`` added. Each recipe is written as CSV, read back through the same
path an upload takes (``workbook.read_upload`` → ``tsv_model``) and refused on a
warning or an empty front, so the guide cannot show a sample that would not work.
A key added to ``sheet_config`` shows up in the table by itself; a line in
``KEY_NOTES`` only makes its explanation better.

Called from ``build_site.build()``.
"""

import csv
import io
import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace

GUIDE = "ai.md"
# What a model can hold alongside the conversation it is in.
BUDGET = 25 * 1024

# What each key does, in a line. A key missing here is still listed, with its
# shape read from sheet_config and a pointer to the docs. `example` is a cell the
# build parses: one that warns stops the build.
KEY_NOTES = {
    # column keys
    "side": (
        "side=back",
        "which side the column is on: {sides}. Default: the first "
        "content column is the front, the rest the back. `hide` = not shown",
    ),
    "size": (
        "size=40",
        "font size in px, 6-200. On image/video/draw columns: width " "in px, 1-2000",
    ),
    "color": (
        "color=muted",
        "`muted` or `accent` (follow the card theme; prefer "
        "these), a CSS colour name, or #hex",
    ),
    "align": ("align=left", "{alignments}"),
    "tts": (
        "tts=en_US",
        "read the column aloud. A FULL code: `en_US`, `zh_CN`, "
        "`ja_JP` - never a bare `en`, which plays nothing",
    ),
    "voices": (
        "tts=en_US; voices=Apple_Samantha",
        "preferred voice; only the " "names this guide's recipes use. Optional",
    ),
    "speed": ("tts=en_US; speed=0.8", "speech speed, 0.5-2.0"),
    "label": ("label=Meaning", "a small caption shown above the value"),
    "type": (
        "type",
        "the learner types this column before the answer shows; "
        "`type=nc` forgives missing accents/tones. One column per sheet",
    ),
    "subdeck": (
        "subdeck=1",
        "this column is a deck level (1 = first level) and is " "not shown on the card",
    ),
    "math": ("math", "a formula (LaTeX, no delimiters); `math=block` centred"),
    "code": ("code=python", "source code, coloured for that language"),
    "font": (
        "font=sc",
        "{fonts}, or a font family name. Use `sc` for Simplified "
        "Chinese, `tc` Traditional, `jp` Japanese, `kr` Korean",
    ),
    "bold": ("bold", "bold text"),
    "italic": ("italic", "italic text"),
    "hint": ("hint", "hidden until the learner taps it"),
    "furigana": (
        "furigana",
        "`漢字[かんじ]` in the cell is drawn as a reading over " "the kanji",
    ),
    "cloze": (
        "cloze",
        "the column holding `{{{{c1::...}}}}` deletions. One column "
        "per sheet; always on the front",
    ),
    "draw": (
        "draw; size=260",
        "a writing box: on the front the learner writes the "
        "character stroke by stroke, on the back it animates the strokes",
    ),
    "sort": ("sort", "Anki's browser lists and sorts notes by this column"),
    "rtl": ("rtl", "right-to-left text (Arabic, Hebrew)"),
    "vertical": ("vertical", "top-to-bottom text"),
    "image": ("image; size=300", "the cell is an image URL"),
    "audio": ("audio", "the cell is an audio URL"),
    "video": ("video", "the cell is a YouTube/Drive/.mp4 URL"),
}
DECK_NOTES = {
    "name": ("name=Travel B1", "the set's name: the deck's name in Anki and its "
             "identity. ALWAYS write it. Up to 100 characters, no `;`"),
    "reverse": ("reverse", "every note also gets a back-to-front card"),
    "theme": ("theme=matcha", "a colour theme for the whole card: {themes}"),
    "align": ("align=left", "default alignment for every column (with an `ID` "
              "column only; without one it is the first column's)"),
    "speed": ("speed=0.9", "default speech speed for every column, 0.5-2.0 (as "
              "`align`)"),
    "next": ("next=w15", "written by Create sheet. Never add or change it; keep it "
             "if the learner's file has it"),
    "shape": ("shape=b1f3a2c", "written by SheetCards. Never add or change it; keep "
              "it if the learner's file has it"),
}  # fmt: skip

BASIC_WORDS = [
    ["Thủ đô của Pháp?", "Paris"],
    ["Nước sôi ở bao nhiêu độ C?", "100 °C"],
]

# What goes in the vocabulary recipe's second column, per language.
READING = {
    "en": "IPA between slashes, as a dictionary prints it, US or UK to match "
    "the `tts` code",
    "zh": "pinyin with tone marks, syllables of one word joined (`yínháng`)",
    "ja": "the reading in hiragana, then romaji in brackets",
    "ko": "Revised Romanization",
    "fr": "IPA between slashes",
    "de": "IPA between slashes",
    "es": "IPA between slashes",
    "vi": "leave empty",
}


def _csv(rows):
    out = io.StringIO()
    csv.writer(out, lineterminator="\n").writerows(rows)
    return out.getvalue()


def _named(rows, name):
    """The rows with ``name=`` written into the marker cell, before any other
    deck setting — the one thing every recipe has to carry."""
    rows = [list(row) for row in rows]
    rest = rows[1][0][len("#config") :].strip()
    rows[1][0] = f"#config name={name}" + (f"; {rest}" if rest else "")
    return rows


def _sample(rows, count=2):
    """Headers, settings row and the first ``count`` words, each cell trimmed:
    the guide tells assistants never to pad a cell, so no sample does."""
    return [[cell.strip() for cell in row] for row in rows[: 2 + count]]


def _file_path(url):
    """A Commons thumbnail address as the stable ``Special:FilePath`` link the
    guide tells assistants to use: it names the file, not a hash of it."""
    match = re.search(r"/commons/thumb/[0-9a-f]/[0-9a-f]{2}/([^/]+)/(\d+)px-", url)
    if not match:
        return url
    return (
        "https://commons.wikimedia.org/wiki/Special:FilePath/"
        f"{match.group(1)}?width={match.group(2)}"
    )


def check(text, label, tm, card_layout, workbook):
    """Reads a CSV the way an upload is read, and refuses it on a warning, an
    empty front, a missing name or a repeated key (an ID, or a first-column word
    on a sheet without one)."""
    upload = json.loads(workbook.read_upload(text.encode("utf-8"), f"{label}.csv"))
    parsed = tm.parse_tsv_data(upload["tsv"], [])
    deck = tm.build_remote_deck_from_tsv(parsed, "", [])
    cfg = deck.sheet_config
    problems = list(cfg.warnings)
    if not cfg.deck_name:
        problems.append("no name=")
    if deck.duplicate_ids:
        problems.append(f"duplicate IDs {deck.duplicate_ids}")
    keys = [note.get("ID") for note in deck.notes]
    if len(set(keys)) != len(keys) or any(" (2)" in str(k) for k in keys):
        problems.append(f"repeated first-column words {keys}")
    front, _ = card_layout.split_sides(deck.plan, cfg)
    if not front:
        problems.append("nothing on the front")
    if not deck.notes:
        problems.append("no rows")
    if problems:
        sys.exit(f"ai.md recipe {label!r}: {problems}")
    return deck


def _key_line(key, notes, values, sc, site):
    _example, what = notes.get(key, (None, None))
    if what is None:
        kind = "flag" if key in sc._FLAGS or key in sc.MEDIA_KINDS else "key=value"
        what = f"{kind}; see {site}docs/en/settings-row/"
    what = what.format(**values)
    return f"| `{key}` | {what} |"


def _table(notes, keys, values, sc, site):
    head = "| key | meaning |\n| :--- | :--- |\n"
    return head + "\n".join(_key_line(k, notes, values, sc, site) for k in keys) + "\n"


def recipes(templates, cloze_rows):
    """(id, title, when, rows, notes) for every recipe, from the site's templates."""
    by_id = {tpl["id"]: tpl for tpl in templates}
    vocab, typed = by_id["vocab"], by_id["typed"]
    out = []
    for lang in vocab["languages"]:
        code = lang["code"]
        rows = vocab["variants"][f"{code}|11"]["rows"]
        out.append(
            (
                f"vocab-{code}",
                f"Vocabulary, {lang['label']} (`tts={code}`)",
                None,
                _named(_sample(rows), f"Vocabulary {code}"),
                lang,
            )
        )
    hanzi = by_id["hanzi"]["rows"]
    # Basic's template row is blank (a sheet starts empty), so the recipe's words
    # are written here; its headers and settings row are the template's.
    basic = by_id["basic"]["variants"]["en"]["rows"][:2] + BASIC_WORDS
    kanji = by_id["kanji"]["rows"]
    picture = [
        [_file_path(cell) for cell in row] if i > 1 else row
        for i, row in enumerate(by_id["picture"]["variants"]["en_US|10"]["rows"])
    ]
    out += [
        ("hanzi", "Chinese writing (draw)", None, _named(_sample(hanzi), "HSK 1 viết chữ"), None),
        ("kanji", "Japanese with furigana", None, _named(_sample(kanji), "JLPT N5"), None),
        ("cloze", "Cloze (fill in the blank)", None, _named(_sample(cloze_rows), "Grammar cloze"), None),
        ("typed", "Typed answer", None, _named(_sample(typed["variants"]["en_US|11"]["rows"]), "Spelling"), None),
        ("reverse", "Reverse (both directions)", None, _named(_sample(by_id["reverse"]["variants"]["en_US|10"]["rows"]), "Both ways"), None),
        ("picture", "Picture words", None, _named(_sample(picture), "Picture words"), None),
        ("basic", "Basic (front / back, any subject)", None, _named(_sample(basic), "Basic"), None),
    ]  # fmt: skip
    return out


def guide(templates, cloze_rows, tm, card_layout, workbook, site):
    """The text of ai.md, and the recipes in it as CSV (for the tests)."""
    sc = SimpleNamespace(**tm.parse_config_row.__globals__)
    themes = sc.listed_themes()
    values = {
        "sides": ", ".join(f"`{s}`" for s in sc.SIDES),
        "alignments": ", ".join(f"`{a}`" for a in sc.ALIGNMENTS),
        "fonts": ", ".join(f"`{f}`" for f in sc.FONTS),
        "themes": ", ".join(f"`{t}`" for t in themes),
    }
    colours = " and ".join(f"`{c}`" for c in sc.THEME_COLORS)

    # Every example cell is a real cell: parsed here, refused if it warns.
    for notes, marker in ((KEY_NOTES, False), (DECK_NOTES, True)):
        for key, (example, _) in notes.items():
            if marker:
                rows = [["ID", "Word"], [f"#config {example}", ""], ["w01", "x"]]
            else:
                rows = [["ID", "Word"], ["#config", example], ["w01", "x"]]
            parsed = tm.parse_tsv_data("\n".join("\t".join(r) for r in rows), [])
            found = tm.build_remote_deck_from_tsv(parsed, "", []).sheet_config
            if found.warnings:
                sys.exit(f"ai.md: the example for {key!r} warns: {found.warnings}")

    blocks = {}
    hanzi_en = next(t for t in templates if t["id"] == "hanzi")["en"]["rows"]
    hanzi_en_label = next(
        part.strip() for part in hanzi_en[1][1].split(";") if "label=" in part
    )
    parts = []
    w = parts.append
    w(
        "# SheetCards: write a flashcard CSV\n\n"
        "> For AI assistants. A learner sent you this page and asked for flashcards. "
        "Follow it to reply with ONE CSV file. The learner opens it in SheetCards "
        "and gets an Anki deck. Every rule and sample here is generated from "
        "SheetCards' own code and checked by its parser.\n"
    )
    w(
        "## 1. Role and goal\n\n"
        "You are producing a CSV for SheetCards, which turns a sheet into Anki "
        "flashcards: one row = one note, row 2 says how the cards look.\n\n"
        "- Missing the target language, or the words/topic? Ask at most 2 short "
        "questions, in one message, in the learner's language. Anything else has a "
        "default (section 4): do not ask, go ahead.\n"
        "- Talk to the learner in their language; the CSV follows this guide.\n"
        "- Aim: cards that look good and open with no warnings.\n"
    )
    w(
        "## 2. Output contract\n\n"
        "1. Exactly one CSV. UTF-8. Comma-separated, RFC 4180: put a field in "
        'double quotes if it holds a comma, a double quote (written `""`) or a '
        "line break. No space after a separating comma.\n"
        "2. Row 1: the recipe's headers, as the recipe has them (most have no "
        "`ID` column; section 3).\n"
        "3. Row 2: the settings row. Its first cell starts `#config name=<set name>`.\n"
        "4. Then one row per card. Every row has as many cells as row 1.\n"
        "5. If you can create files, attach it as a downloadable `.csv`. Otherwise "
        "give one fenced code block with `csv` as its language, and nothing else "
        "inside it.\n"
        "6. Suggest a file name: lowercase ASCII with hyphens, e.g. "
        "`travel-b1.csv`.\n"
        "7. No prose, comments, Markdown or HTML inside the CSV. Say anything "
        "else outside it, briefly.\n"
    )
    w(
        "## 3. Keys (IDs) and the set name\n\n"
        "Re-importing a newer file updates each note by its key and keeps the "
        "learner's review progress. A sheet has one of two kinds of key:\n\n"
        "- **No `ID` column** (the vocabulary, typed, reverse, picture and basic "
        "recipes): the first column is the key. Write each word once; a repeat "
        "becomes a second card, `word (2)`. Correcting the spelling of a word "
        "later makes a new card (its progress starts over). Prefer this for a "
        "simple set.\n"
        "- **An `ID` column** (the Chinese writing, Japanese and cloze recipes, or "
        "when the learner asks for one or says they will fix spellings later): "
        "`ID` is the first "
        "header, short, unique and stable: `w01`, `w02`, ... (`w001` for more "
        "than 99 cards). The word can then be corrected without losing progress, "
        "so an ID must never change or be reused for another word. Any recipe "
        "can take one: add `ID` as the first header, move `#config ...` and the "
        "deck keys into its cell, and leave the first column's own settings in "
        "its cell.\n"
        "- Adding to an existing list: if the learner gives you their CSV, return "
        "the whole file, old rows unchanged, new rows after them (with an `ID` "
        "column, continuing after the highest ID; never reuse one). If they only "
        "tell you the last ID, return the same headers and settings row with "
        "only the new rows.\n"
        "- `name=` is the deck's name in Anki. Use the name the learner gave, or "
        "make a short one in their language (`Du lịch B1`). Keep it the same when "
        "adding words: the same name updates the same deck, a new name makes a "
        "new deck. No `;` in it; `::` makes a sub-deck.\n"
        "- Keep any `next=` or `shape=` already in the learner's `#config` cell "
        "exactly as it is. Never add them.\n"
    )
    w(
        "## 4. Read the request, pick a recipe\n\n"
        "Read: target language, the learner's own language (default: the one they "
        "write to you in), level (CEFR A1-C2, HSK 1-6, JLPT N5-N1, TOPIK...), "
        "topic, count (default 20), card style.\n\n"
        "| The learner says | Recipe |\n| :--- | :--- |\n"
        "| words, vocabulary, từ vựng (default) | Vocabulary for that language |\n"
        "| Chinese + writing, viết chữ, stroke order | Chinese writing |\n"
        "| Japanese + kanji, furigana, JLPT | Japanese with furigana |\n"
        "| fill in the blank, điền chỗ trống, cloze, grammar, sentences | Cloze |\n"
        "| type, spelling, gõ đáp án, chính tả | Typed answer |\n"
        "| both directions, hai chiều | Reverse |\n"
        "| pictures, ảnh (and they give URLs or ask for pictures) | Picture words |\n"
        "| facts, Q&A, not a language | Basic |\n\n"
        "Change only the words. Keep the recipe's headers and settings row, "
        "except: you may rename a content header (any language works; its "
        "settings stay in the same column), you may drop a column (drop its "
        "settings cell too) and you may add `theme=` from section 6 if the learner "
        "asks for a look. Write `label=` text and any sample-like note in the "
        "learner's language. For a language not listed, use the Vocabulary recipe "
        "with that language's full `tts` code and no `voices=`.\n"
    )

    w(
        "## 5. Recipes\n\n"
        "Each is a complete, valid CSV (headers, settings row, 2 sample rows). "
        "Copy it, set `name=`, replace the sample rows.\n"
    )
    for rid, title, _when, rows, lang in recipes(templates, cloze_rows):
        text = _csv(rows)
        check(text, rid, tm, card_layout, workbook)
        blocks[rid] = text
        w(f"### {title}\n")
        if rid == "vocab-en_US":
            w(
                "Columns: Word (front, read aloud), Phiên âm (reading), Meaning "
                "(in the learner's language), Example (one sentence, read aloud), "
                "Note (optional, short). Vietnamese samples; keep `Phiên âm` or "
                "rename it (e.g. `Reading`).\n"
            )
        if lang:
            reading = READING.get(lang["code"][:2], "")
            voice = f"`voices={lang['voice']}`" if lang["voice"] else "no `voices=`"
            w(f"Reading column: {reading}. Voice: {voice}.\n")
        if rid == "hanzi":
            w(
                "The `Draw` column holds only the Han characters of the word (one "
                "box each; keep to 1-2 characters), no pinyin or punctuation. "
                "`Character` repeats them to be shown and heard. For a learner "
                f"who reads English, the label is `{hanzi_en_label}`.\n"
            )
        if rid == "kanji":
            w(
                "Write the reading in hiragana in `[...]` right after the kanji it "
                "belongs to: `日本語[にほんご]`. Kana after a kanji stays outside: "
                "`読[よ]みます`. Put a space before each kanji group that follows "
                "other text, kana included: `図書館[としょかん]で 本[ほん]を 読[よ]みます。`, "
                "`朝[あさ]ご 飯[はん]` (the space is not shown; without it the reading "
                "would cover the kana too). Never put brackets after kana.\n"
            )
        if rid == "cloze":
            w(
                "Only the `cloze` column holds deletions, and every row has at "
                "least one: `{{c1::answer}}`, optionally `{{c1::answer::hint}}`. "
                "`c2`, `c3` in the same cell make extra cards. Delete the word the "
                "lesson is about, not a random one.\n"
            )
        if rid == "typed":
            w(
                "The meaning asks; the learner types the word (`type=nc`: accents "
                "forgiven). Only one column per sheet can be typed.\n"
            )
        if rid == "reverse":
            w(
                "`reverse` adds a second card, meaning -> word. Leave out example "
                "sentences: they would give the answer away on that card.\n"
            )
        if rid == "picture":
            w(
                "Only when the learner gives image URLs or asks for pictures. Then "
                "use only Wikimedia Commons files you know exist, written as "
                "`https://commons.wikimedia.org/wiki/Special:FilePath/<File name>"
                "?width=500`. Never invent a URL; leave the cell empty if unsure.\n"
            )
        w(f"```csv\n{text}```\n")

    w(
        "## 6. The settings row\n\n"
        "Row 2. Its first cell starts `#config`. With an `ID` column, that cell holds "
        "only the deck settings and every other cell its column's settings. "
        "Without one, the first cell is shared: `name`, `reverse`, `theme` in it "
        "are the deck's, every other key is the first column's "
        "(`#config name=Travel B1; theme=matcha; size=44; bold`). "
        "A cell is `key=value` pairs separated by "
        "`;`, a bare key is a flag (`size=44; bold; tts=en_US`). An empty cell "
        "means defaults. Quote a cell that has a comma (`voices=A,B`). Use only "
        "the keys below: anything else shows the learner a warning.\n\n"
        "Deck settings, in the `#config` cell: `#config name=Travel B1; theme=matcha`\n\n"
        + _table(
            DECK_NOTES,
            sorted(sc._DECK_KEYS, key=lambda k: k != "name"),
            values,
            sc,
            site,
        )
    )
    w("Column settings:\n\n" + _table(KEY_NOTES, sc._FIELD_KEYS, values, sc, site))
    w(
        f"Colours that follow the theme: {colours}. Flags: "
        + ", ".join(f"`{f}`" for f in sc._FLAGS)
        + ". Media kinds (one per column): "
        + ", ".join(f"`{m}`" for m in sc.MEDIA_KINDS)
        + ".\n\n"
        "Reserved headers, never card fields: `ID` (optional, see section 3), "
        "`SYNC`, `SUBDECK 1`, "
        "`SUBDECK 2`... (deck levels), `TAGS` (comma-separated tags, quote the "
        "cell). Name no other column like them.\n\n"
        "Voices: write `tts=` with a full code. Add `voices=` only with these "
        "names, for their language: "
        + ", ".join(
            f"`{lang['voice']}` ({lang['code']})"
            for lang in next(t for t in templates if t["id"] == "vocab")["languages"]
            if lang["voice"]
        )
        + ". Never invent a voice name.\n"
    )
    w(
        "## 7. Quality rules\n\n"
        "- One sense per card. A word with two meanings the learner needs is two "
        "rows; near-synonyms of one sense may share a cell, joined by `; `.\n"
        "- Meaning: short, in the learner's language (Vietnamese for a Vietnamese "
        "learner: `chuyến đi`, not a definition).\n"
        "- One natural example sentence at the learner's level, using the word.\n"
        "- Readings exact: IPA as dictionaries give it; pinyin with tone marks, "
        "joined per word (`yínháng`, `wǒ shì xuésheng`), never tone numbers; kana "
        "readings correct for the word.\n"
        "- No invented image or audio URLs. Leave media columns out unless the "
        "learner gives URLs or asks for them.\n"
        "- No duplicate words. Exactly the requested count.\n"
        "- Words fit the level and topic; most useful first.\n"
        "- Plain text in cells: no Markdown, no HTML.\n"
    )
    w(
        "## 8. Final checklist\n\n"
        "- [ ] Row 1: the recipe's headers (`ID` first only if it has one).\n"
        "- [ ] Row 2: `#config name=...`, then only keys from section 6.\n"
        "- [ ] Every key unique and none empty: the first-column words, or every "
        "`ID` (numbering continued if adding).\n"
        "- [ ] Every row has as many cells as row 1; commas, quotes and line "
        "breaks quoted.\n"
        "- [ ] `tts=` full codes; `voices=` only from the list.\n"
        "- [ ] Cloze: deletions only in the `cloze` column, one in every row.\n"
        "- [ ] Requested count, no duplicates, no invented URLs.\n"
        "- [ ] One file (or one `csv` block) and a suggested file name.\n"
    )
    w(
        "## 9. Tell the learner where the file goes\n\n"
        f"1. Open Sheet to Anki, {site}create/ , and press **Open .xlsx/.csv "
        f"file** (VI: **Mở file .xlsx/.csv**). Or open Create sheet, {site}"
        "sheet/ , to edit it first.\n"
        "2. Check the cards, then press **Download .apkg** and open that file in "
        "Anki, AnkiDroid or AnkiMobile.\n"
        "3. Do not import the `.csv` into Anki or AnkiDroid directly: they would "
        "turn the settings row into a card.\n"
        "4. Keep the `.csv`: to add words later, give it back to you and ask for "
        "more.\n\n"
        f"More: {site}docs/en/settings-row/ · {site}docs/en/card-types/\n"
    )
    text = "\n".join(parts)
    size = len(text.encode("utf-8"))
    if size > BUDGET:
        sys.exit(f"ai.md is {size} bytes, over its {BUDGET}-byte budget")
    return text, blocks


def llms_txt(site):
    return (
        "# SheetCards\n\n"
        "> SheetCards turns a spreadsheet into Anki flashcards. Sheet to Anki, on "
        "the web, reads a Google Sheet or a .csv/.xlsx file and builds an .apkg "
        "for Anki, AnkiDroid or AnkiMobile; an Anki add-on syncs Google Sheets. "
        "If a learner asks you to make flashcards for SheetCards, read the guide "
        "below: it says how to write the CSV (headers, the `#config` settings row, "
        "IDs) and gives ready recipes for vocabulary in many languages, Chinese "
        "writing, Japanese furigana, cloze, typed answers, reverse and picture "
        "cards.\n\n"
        "## Guide\n\n"
        f"- [Write a flashcard CSV for SheetCards]({site}{GUIDE}): the "
        "complete instructions for AI assistants, plain Markdown\n\n"
        "## Docs\n\n"
        f"- [Settings row]({site}docs/en/settings-row/)\n"
        f"- [Card types]({site}docs/en/card-types/)\n"
        f"- [Make a word set with AI]({site}docs/en/ai/)\n"
    )


def write(out, templates, tm, card_layout, workbook, cloze_rows, site):
    """Writes both files; every address in them starts with ``site``."""
    text, _ = guide(templates, cloze_rows, tm, card_layout, workbook, site)
    Path(out, GUIDE).write_text(text, encoding="utf-8")
    Path(out, "llms.txt").write_text(llms_txt(site), encoding="utf-8")
    return len(text.encode("utf-8"))
