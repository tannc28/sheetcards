"""The guide an AI assistant reads to write a SheetCards set: ``/ai.md`` and ``/llms.txt``.

A learner gives ChatGPT, Gemini or Claude the address of ``ai.md`` and says what
cards they want; the assistant answers with a set in the text form (or, asked
for one, a table or CSV) that opens in Make flashcards without a warning. The page is plain Markdown because that is what
an assistant fetching a URL reads cleanly, and English because that is what every
model follows best — the learner talks to it in their own language.

Nothing in it is written twice. The settings-row keys, their values, the fonts,
the colours and the themes are read from ``sheet_config`` (the copy the site
ships), and every recipe is one of Create sheet's own templates from
``build_site.sheet_templates()`` — or, for cloze, the example workbook's sheet —
with ``name=`` added. Each recipe is written in the text form, read by the
page's own reader (``site/importformats.js``, in node) and then through the
path an upload takes (``workbook.read_upload`` → ``tsv_model``), and refused on
a warning or an empty front, so the guide cannot show a sample that would not
work; the table-form sample is checked the same way as CSV.
A key added to ``sheet_config`` shows up in the table by itself; a line in
``KEY_NOTES`` only makes its explanation better.

Called from ``build_site.build()``.
"""

import csv
import io
import json
import re
import shutil
import subprocess
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
        "`muted` (soft) or `accent` (highlight); both follow the card theme",
    ),
    "align": ("align=left", "this column's alignment: {alignments}"),
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
    "label": (
        "label=Meaning",
        "a small caption above the value; a bare `label` uses the column's name",
    ),
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
        "Chinese, `tc` Traditional, `jp` Japanese, `kr` Korean; a `tts` column "
        "gets its language's one without it",
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
    "image": ("image; size=300", "the cell is an image URL"),
    "audio": ("audio", "the cell is an audio URL"),
    "video": ("video", "the cell is a YouTube/Drive/.mp4 URL"),
}
DECK_NOTES = {
    "name": ("name=Travel B1", "the set's name: the deck's name in Anki and its "
             "identity. ALWAYS write it. Up to 100 characters, no `;`"),
    "reverse": ("reverse", "every note also gets a back-to-front card"),
    "theme": ("theme=matcha", "a colour theme for the whole card: {themes}"),
}  # fmt: skip
# The Advanced table says `color` again, for the values Basic leaves out.
ADVANCED_NOTES = {
    "color": (None, "a CSS colour name or #hex: fixed, so it ignores night mode"),
}

# Mirrors of sheet_config's split, used when the shipped copy predates it.
_BASIC_KEYS = (
    "side",
    "size",
    "bold",
    "color",
    "tts",
    "image",
    "type",
    "hint",
    "label",
    "name",
    "theme",
)
_ADVANCED_GROUPS = (
    ("voice", ("voices", "speed")),
    ("card", ("cloze", "reverse", "draw", "furigana")),
    ("text", ("italic", "align", "font", "color", "code", "math")),
    ("media", ("audio", "video")),
    ("deck", ("subdeck",)),
)
_INTERNAL_KEYS = ("next", "shape")
GROUP_TITLES = {
    "voice": "voice",
    "card": "card type",
    "text": "text",
    "media": "media",
    "deck": "deck",
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


def check(text, label, tm, card_layout, workbook, kind="csv"):
    """Reads a CSV (or the TSV a text recipe becomes) the way an upload is read,
    and refuses it on a warning, an empty front, a missing name or a repeated
    key (an ID, or a first-column word on a sheet without one)."""
    upload = json.loads(workbook.read_upload(text.encode("utf-8"), f"{label}.{kind}"))
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


def as_text(rows, deck_keys):
    """A recipe's grid in the text form: ``#config`` and the deck's keys on
    line 1, the names on line 2 with each column's settings in brackets, then
    one card per line, cells separated by `` | ``."""
    names, config, *words = rows
    marker = config[0][len("#config") :]
    deck, own = [], []
    for chunk in (c.strip() for c in marker.split(";")):
        if chunk:
            key = chunk.split("=", 1)[0].strip().lower()
            (deck if key in deck_keys else own).append(chunk)
    cells = ["; ".join(own)] + list(config[1:])
    if names and names[0].strip().upper() == "ID":
        # The marker is the ID cell's; the ID column itself has no settings.
        cells[0] = ""
    head = " | ".join(
        f"{n} [{c}]" if c.strip() else n for n, c in zip(names, cells, strict=True)
    )
    for row in words:
        for cell in row:
            if "|" in cell or "\n" in cell:
                sys.exit(f"ai.md: a text recipe cell holds | or a line break: {cell!r}")
    lines = [f"#config {'; '.join(deck)}".rstrip(), head]
    lines += [" | ".join(row).rstrip() for row in words]
    return "\n".join(lines) + "\n"


def text_to_tsv(texts):
    """Each text recipe as the sheet Dán văn bản makes of it, by the page's own
    reader (site/importformats.js, run in node): nothing here re-implements it."""
    node = shutil.which("node")
    if node is None:
        sys.exit("ai.md: node is needed to check the text recipes")
    site = Path(__file__).resolve().parent.parent / "site"
    script = (
        "let raw = ''; process.stdin.on('data', (c) => (raw += c));"
        "process.stdin.on('end', async () => {"
        f"const m = await import({json.dumps((site / 'importformats.js').as_uri())});"
        f"const s = await import({json.dumps((site / 'sharelink.js').as_uri())});"
        "const out = JSON.parse(raw).map((text) => { const r = m.readPaste(text);"
        " return s.toTsv(m.pasteGrid({name: '', rows: r.rows, header: r.header,"
        " cells: r.cells, deck: r.deck, language: 'en'})); });"
        "process.stdout.write(JSON.stringify(out)); });"
    )
    done = subprocess.run(
        [node, "--no-warnings", "-e", script],
        input=json.dumps(texts),
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return json.loads(done.stdout)


def _key_line(key, notes, values, sc, site):
    _example, what = notes.get(key, (None, None))
    if what is None:
        kind = "flag" if key in sc._FLAGS or key in sc.MEDIA_KINDS else "key=value"
        what = f"{kind}; see {site}docs/en/settings-row/"
    what = what.format(**values)
    return f"| `{key}` | {what} |"


def _split(sc):
    """(basic, [(group, keys)]): every key the parser takes, once, in Basic or
    under its Advanced group; the internal ones nowhere. A key the split does
    not name goes under "other" rather than being left out."""
    basic = list(getattr(sc, "BASIC_KEYS", _BASIC_KEYS))
    groups = [(g, list(k)) for g, k in getattr(sc, "ADVANCED_GROUPS", _ADVANCED_GROUPS)]
    internal = set(getattr(sc, "INTERNAL_KEYS", _INTERNAL_KEYS))
    named = set(basic) | {k for _, keys in groups for k in keys} | internal
    other = [k for k in (*sc._FIELD_KEYS, *sc._DECK_KEYS) if k not in named]
    if other:
        groups.append(("other", other))
    return basic, groups


def _split_tables(notes, values, sc, site):
    """The Basic table, then the Advanced one, each key marked with where it
    goes (its column, or the `#config` cell) and Advanced ones with their group."""
    basic, groups = _split(sc)

    def line(key, table_notes, group=None):
        where = "`#config`" if key in sc._DECK_KEYS else "column"
        if group:
            where += f", {GROUP_TITLES.get(group, group)}"
        return _key_line(key, table_notes, values, sc, site).replace(
            f"| `{key}` |", f"| `{key}` | {where} |", 1
        )

    head = "| key | where | meaning |\n| :--- | :--- | :--- |\n"
    advanced = {**notes, **ADVANCED_NOTES}
    return (
        "**Basic** (enough for most sets):\n\n"
        + head
        + "\n".join(line(k, notes) for k in basic)
        + "\n\n**Advanced** (only when the learner asks for it):\n\n"
        + head
        + "\n".join(line(k, advanced, g) for g, keys in groups for k in keys)
        + "\n"
    )


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
        "# SheetCards: write a flashcard set\n\n"
        "> For AI assistants. A learner sent you this page and asked for flashcards. "
        "Follow it to reply with ONE flashcard set, as text (the default) or as a "
        "table. The learner pastes or opens it in SheetCards and gets an Anki deck. "
        "Every rule and sample here is generated from SheetCards' own code and "
        "checked by its parser.\n"
    )
    w(
        "## 1. Role and goal\n\n"
        "You are writing a set for SheetCards, which turns it into Anki flashcards: "
        "one line (row) = one note, and a few settings say how the cards look.\n\n"
        "- Missing the target language, or the words/topic? Ask at most 2 short "
        "questions, in one message, in the learner's language. Anything else has a "
        "default (section 4): do not ask, go ahead.\n"
        "- Talk to the learner in their language; the set follows this guide.\n"
        "- Aim: cards that look good and open with no warnings.\n"
    )
    w(
        "## 2. Output contract\n\n"
        "Two forms carry the same set. The settings keys are identical; only where "
        "they sit differs.\n\n"
        "**Text form (the default).** One fenced code block with `text` as its "
        "language, and nothing else inside it:\n\n"
        "1. Line 1: `#config name=<set name>`, then any deck keys "
        "(`#config name=Travel B1; theme=matcha`).\n"
        "2. Line 2: the column names, separated by ` | `. A column's settings go in "
        "brackets after its name: `Word [tts=en_US; bold]`. A name without brackets "
        "has default settings.\n"
        "3. Then one card per line, its cells separated by ` | `, as many as there "
        "are names. A cell never holds `|` or a line break.\n\n"
        "**Table form** - only when the learner asks for a table, a spreadsheet, "
        "Google Sheets, Excel or a file:\n\n"
        "1. Row 1: the column names.\n"
        "2. Row 2: the settings row. Its first cell is `#config name=<set name>`, "
        "the deck keys and the first column's own settings "
        "(`#config name=Travel B1; tts=en_US; bold`); every other cell holds its "
        "column's settings, or is empty.\n"
        "3. Then one row per card.\n"
        "4. If you can create files, attach it as a `.csv` (UTF-8, RFC 4180: quote "
        'a field holding a comma, a double quote (written `""`) or a line break; '
        "no space after a comma) with a short lowercase ASCII file name, "
        "`travel-b1.csv`. Otherwise give one fenced `csv` block.\n\n"
        "Which form? Text, unless the learner mentions a table, a sheet, Excel or a "
        "file. If you really cannot tell, ask in one short question. Say anything "
        "else outside the block, briefly; no prose, Markdown or HTML inside it.\n"
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
        "can take one: add `ID` as the first column name, with no settings of its "
        "own (in the table form the `#config` cell is then the ID column's).\n"
        "- Adding to an existing list: if the learner gives you their CSV, return "
        "the whole file, old rows unchanged, new rows after them (with an `ID` "
        "column, continuing after the highest ID; never reuse one). If they only "
        "tell you the last ID, return the same headers and settings row with "
        "only the new rows.\n"
        "- `name=` is the deck's name in Anki. Use the name the learner gave, or "
        "make a short one in their language (`Du lịch B1`). Keep it the same when "
        "adding words: the same name updates the same deck, a new name makes a "
        "new deck. No `;` in it; `::` makes a sub-deck.\n"
        "- Keep any `next` or `shape` key (`next=w15`, `shape=b1f3a2c`) already "
        "in the learner's `#config` cell exactly as it is. SheetCards writes "
        "them; never add or change them.\n"
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
        "Change only the words. Keep the recipe's column names and settings, "
        "except: you may rename a column (any language works; its settings stay "
        "with it), you may drop a column (and its settings) and you may add "
        "`theme=` from section 6 if the learner "
        "asks for a look. Write `label=` text and any sample-like note in the "
        "learner's language. For a language not listed, use the Vocabulary recipe "
        "with that language's full `tts` code and no `voices=`.\n"
    )

    w(
        "## 5. Recipes\n\n"
        "Each is a complete, valid set in the text form (settings line, names, 2 "
        "sample cards). Copy it, set `name=`, replace the sample cards. The first "
        "is shown in the table form as well: for a table, move each column's "
        "brackets into row 2 under it, and the `#config` line's keys to the front "
        "of row 2's first cell.\n"
    )
    listed = recipes(templates, cloze_rows)
    texts = [as_text(rows, sc._DECK_KEYS) for _, _, _, rows, _ in listed]
    for (rid, *_), tsv in zip(listed, text_to_tsv(texts), strict=True):
        check(tsv, rid, tm, card_layout, workbook, kind="tsv")
    for (rid, title, _when, rows, lang), text in zip(listed, texts, strict=True):
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
        w(f"```text\n{text}```\n")
        if rid == "vocab-en_US":
            table = _csv(rows)
            check(table, rid, tm, card_layout, workbook)
            blocks["table"] = table
            w(f"The same set in the table form, as CSV:\n\n```csv\n{table}```\n")

    w(
        "## 6. The settings\n\n"
        "A column's settings are `key=value` pairs separated by `;`; a bare key is "
        "a flag (`size=44; bold; tts=en_US`). No settings means defaults. In the "
        "text form they go in brackets after the column's name and the deck keys "
        "on the `#config` line; in the table form all of them go in row 2: the "
        "first cell `#config` + the deck keys + the first column's keys, then one "
        "cell per column (quote a CSV cell holding a comma, `voices=A,B`). Use only "
        "the keys below: anything else shows the learner a warning.\n\n"
        + _split_tables({**KEY_NOTES, **DECK_NOTES}, values, sc, site)
    )
    w(
        f"Colours that follow the theme: {colours}. Flags: "
        + ", ".join(f"`{f}`" for f in sc._FLAGS)
        + ". Media kinds (one per column): "
        + ", ".join(f"`{m}`" for m in sc.MEDIA_KINDS)
        + ".\n\n"
        "Reserved headers, never card fields: `ID` (optional, see section 3), "
        "`SYNC` (only rows saying yes sync), `TAGS` (comma-separated tags, quote "
        "the cell). Name no other column like them. For deck levels give a "
        "column a real name (`Lesson`) and `subdeck=1`; never a `SUBDECK 1` "
        "header (retired: it warns).\n\n"
        "Automatic, no key: right-to-left text, the browser's sort column, line "
        "breaks in a cell, and the CJK font of a `tts` column.\n\n"
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
        "- [ ] Text form, unless a table or a file was asked for.\n"
        "- [ ] Text: line 1 `#config name=...`, line 2 the names (settings in "
        "brackets), then the cards. Table: row 1 the names, row 2 `#config "
        "name=...` and the settings by column.\n"
        "- [ ] Only keys from section 6.\n"
        "- [ ] Every key unique and none empty: the first-column words, or every "
        "`ID` (numbering continued if adding).\n"
        "- [ ] Every card has as many cells as there are names; no `|` in a text "
        "cell; CSV commas, quotes and line breaks quoted.\n"
        "- [ ] `tts=` full codes; `voices=` only from the list.\n"
        "- [ ] Cloze: deletions only in the `cloze` column, one in every card.\n"
        "- [ ] Requested count, no duplicates, no invented URLs.\n"
        "- [ ] One block (or one file).\n"
    )
    w(
        "## 9. Tell the learner where it goes\n\n"
        f"1. Open Make flashcards (VI: **Tạo flashcard**), {site}create/ . Text: "
        "paste the block into the main field, or press **Paste text** (VI: "
        "**Dán văn bản**). A table or file: press **Open "
        ".xlsx/.csv file** (VI: **Mở file .xlsx/.csv**), or paste the table into "
        f"**Paste text**. Or open Create sheet, {site}sheet/ , to edit it first.\n"
        "2. Check the cards, then press **Download .apkg** and open that file in "
        "Anki, AnkiDroid or AnkiMobile.\n"
        "3. Do not import a `.csv` into Anki or AnkiDroid directly: they would "
        "turn the settings row into a card.\n"
        "4. Keep the text in a note (or keep the `.csv`): to add words later, add "
        "lines under it, or give it back to you and ask for more. The same "
        "`name=` updates the same deck.\n\n"
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
        "> SheetCards turns a spreadsheet or a list into Anki flashcards. Sheet to "
        "Anki, on the web, reads a Google Sheet, a .csv/.xlsx file or pasted text and builds an .apkg "
        "for Anki, AnkiDroid or AnkiMobile; an Anki add-on syncs Google Sheets. "
        "If a learner asks you to make flashcards for SheetCards, read the guide "
        "below: it says how to write the set (as text: a `#config` line, column "
        "names with their settings in brackets, one card per line; or as a table "
        "or CSV with a `#config` settings row) and gives ready recipes for vocabulary in many languages, Chinese "
        "writing, Japanese furigana, cloze, typed answers, reverse and picture "
        "cards.\n\n"
        "## Guide\n\n"
        f"- [Write a flashcard set for SheetCards]({site}{GUIDE}): the "
        "complete instructions for AI assistants, plain Markdown\n\n"
        "## Docs\n\n"
        f"- [Settings row]({site}docs/en/settings-row/)\n"
        f"- [Card types]({site}docs/en/card-types/)\n"
    )


def write(out, templates, tm, card_layout, workbook, cloze_rows, site):
    """Writes both files; every address in them starts with ``site``."""
    text, _ = guide(templates, cloze_rows, tm, card_layout, workbook, site)
    Path(out, GUIDE).write_text(text, encoding="utf-8")
    Path(out, "llms.txt").write_text(llms_txt(site), encoding="utf-8")
    return len(text.encode("utf-8"))
