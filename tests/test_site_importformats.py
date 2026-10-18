"""Other apps' exports and pasted lists, read as sheets: ``site/importformats.js``.

Sheet to Anki's *Dán văn bản* and both pages' file upload take what Quizlet,
Noji, Brainscape, a notes app or a spreadsheet hands over. The two decisions
that go wrong silently are where a card ends (a Quizlet export set to "between
rows: ;" is one long line) and whether the first row is column names or the
first card (Noji's and Brainscape's CSVs have no header row). Both are made in
importformats.js and nowhere else; this runs it in node.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SITE = REPO / "site"
NODE = shutil.which("node")

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(NODE is None, reason="node is not installed"),
]


def _run(body, data=None):
    script = (
        "let raw = ''; process.stdin.on('data', (c) => (raw += c));"
        "process.stdin.on('end', () => {"
        f"import({json.dumps((SITE / 'importformats.js').as_uri())}).then(async (m) => {{"
        "const data = raw ? JSON.parse(raw) : null;"
        f"const out = await (async () => {{ {body} }})();"
        "process.stdout.write(JSON.stringify(out)); })"
        ".catch((e) => { process.stdout.write(JSON.stringify({ error: String(e) })); });"
        "});"
    )
    out = subprocess.run(
        [NODE, "--no-warnings", "-e", script],
        input=json.dumps(data) if data is not None else "",
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    result = json.loads(out.stdout)
    assert not (isinstance(result, dict) and "error" in result), result
    return result


def _paste(text, **options):
    return _run(
        "return m.readPaste(data.text, data.options);",
        {"text": text, "options": options},
    )


def _verdict(rows):
    return _run("return m.headerVerdict(data);", rows)


# ---------------------------------------------------------------------------
# Quizlet's Export → Copy text
# ---------------------------------------------------------------------------


def test_quizlet_default_tab_and_newline():
    out = _paste("apple\tquả táo\nbook\tquyển sách\njourney\tchuyến đi\n")
    assert out["separator"] == "tab"
    assert out["rowSeparator"] == {"id": "newline"}
    assert out["rows"] == [
        ["apple", "quả táo"],
        ["book", "quyển sách"],
        ["journey", "chuyến đi"],
    ]
    assert out["header"] is None


def test_quizlet_rows_separated_by_semicolons():
    out = _paste("apple\tquả táo;book\tquyển sách;journey\tchuyến đi;")
    assert out["rowSeparator"] == {"id": "token", "token": ";"}
    assert out["separator"] == "tab"
    assert [r[0] for r in out["rows"]] == ["apple", "book", "journey"]


# ---------------------------------------------------------------------------
# The text form Create sheet writes (sheettext.js)
# ---------------------------------------------------------------------------


def test_the_names_bar_wins_a_tie_with_a_dash_in_the_cards():
    # A dash inside a meaning is not where the columns are: the names say |.
    out = _paste("#config\nFront | Back\ndog | chó - con\ncat | mèo - con\n")
    assert out["rows"] == [["dog", "chó - con"], ["cat", "mèo - con"]]


def test_an_empty_cell_after_a_bar_is_a_cell():
    out = _paste("#config\nFront | Back | Note\nbook |\npen | | x\n")
    assert out["rows"] == [["book", ""], ["pen", "", "x"]]


def test_pasted_names_keep_tags_and_subdeck():
    grid = _run(
        "return m.pasteGrid({name: 'X', rows: data.rows, header: data.header});",
        {
            "header": ["ID", "Front", "TAGS", "SUBDECK 1"],
            "rows": [["w1", "a", "t", "s"]],
        },
    )
    assert grid[0] == ["ID", "Front", "TAGS", "SUBDECK 1"]


def test_quizlet_comma_between_term_and_definition_semicolon_between_rows():
    out = _paste("apple,quả táo;book,quyển sách;journey,chuyến đi")
    assert out["rowSeparator"]["token"] == ";"
    assert out["rows"][1] == ["book", "quyển sách"]


def test_quizlet_custom_row_separator():
    out = _paste("apple - quả táo ## book - quyển sách ## journey - chuyến đi")
    assert out["rowSeparator"] == {"id": "token", "token": "##"}
    assert out["rows"][2] == ["journey", "chuyến đi"]


def test_the_row_separator_can_be_chosen():
    out = _paste("a\tb|c\td|e\tf", rows="|")
    assert out["rows"] == [["a", "b"], ["c", "d"], ["e", "f"]]


def test_a_single_card_is_not_split_into_rows():
    out = _paste("apple - quả táo; trái táo")
    assert out["rowSeparator"] == {"id": "newline"}
    assert len(out["rows"]) == 1


def test_remnote_arrows():
    out = _paste("apple >> quả táo\nbook >> quyển sách")
    assert out["separator"] == "arrow"
    assert out["rows"][0] == ["apple", "quả táo"]


def test_a_named_header_line_is_not_a_card():
    out = _paste("Term\tDefinition\napple\tquả táo\nbook\tquyển sách")
    assert out["header"] == ["Term", "Definition"]
    assert [r[0] for r in out["rows"]] == ["apple", "book"]


def test_duplicates_are_marked():
    out = _paste("apple - quả táo\nbook - sách\nApple - táo")
    assert out["marks"] == [None, None, "list"]


# ---------------------------------------------------------------------------
# Is the first row column names?
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "rows",
    [
        [["ID", "Word", "Meaning"], ["1", "a", "b"]],
        [["Word", "x"], ["#config", ""], ["a", "b"]],
        [["Term", "Definition"], ["apple", "quả táo"]],
        [["Mặt trước", "Mặt sau"], ["apple", "quả táo"]],
        [["Kanji", "Nghĩa"], ["猫", "con mèo"]],
        [["Tiếng Anh", "Tiếng Việt"], ["apple", "quả táo"]],
        # Unknown names, but not shaped like the rows under them.
        [["Lời bài hát", "Bản dịch"], ["hello", "xin chào"], ["world", "thế giới"]],
        [["Từ mới", "Dịch"], ["猫", "con mèo"], ["犬", "con chó"]],
        # One row and nothing to compare it with: a sheet's own names win.
        [["Foo", "Bar"]],
    ],
)
def test_a_header_row_is_kept(rows):
    assert _verdict(rows)["header"] is True


@pytest.mark.parametrize(
    "rows",
    [
        # Noji / Brainscape: term, definition, no header.
        [["apple", "quả táo"], ["book", "quyển sách"], ["journey", "chuyến đi"]],
        [["Apple", "Quả táo"], ["Book", "Quyển sách"]],
        [["猫", "con mèo"], ["犬", "con chó"]],
        [["How are you?", "Bạn khỏe không?"], ["Thanks", "Cảm ơn"]],
        [["gato", "gato"], ["perro", "chó"]],
    ],
)
def test_a_first_card_is_not_a_header(rows):
    assert _verdict(rows)["header"] is False


def test_with_headers_makes_up_front_and_back():
    out = _run(
        "return m.withHeaders(data, {language: 'vi'});",
        [["apple", "quả táo", "noun"], ["book", "quyển sách", "noun"]],
    )
    assert out["synthesized"] is True
    assert out["rows"][0] == ["Mặt trước", "Mặt sau", "Mặt sau 2"]
    assert out["rows"][1] == ["apple", "quả táo", "noun"]
    en = _run("return m.synthHeaders(2, 'en');")
    assert en == ["Front", "Back"]


def test_the_verdict_can_be_overridden():
    out = _run("return m.withHeaders(data, {header: true});", [["a", "b"], ["c", "d"]])
    assert out["synthesized"] is False


# ---------------------------------------------------------------------------
# The sheet a paste becomes
# ---------------------------------------------------------------------------


def test_paste_grid_is_a_named_basic_sheet():
    grid = _run(
        "return m.pasteGrid({name: 'Từ vựng; tuần 1', rows: data, language: 'vi'});",
        [["apple", "quả táo"], ["book", "quyển sách", "a noun"], ["", "orphan"]],
    )
    # No ID column: the parser keys each row by its first column.
    assert grid[0] == ["Mặt trước", "Mặt sau", "Mặt sau 2"]
    assert grid[1] == ["#config name=Từ vựng tuần 1", "", ""]
    assert grid[2] == ["apple", "quả táo", ""]
    assert grid[3] == ["book", "quyển sách", "a noun"]
    assert len(grid) == 4  # the row with no front has no key


def test_paste_grid_reads_back_as_the_named_deck():
    """The grid goes through the add-on's own parser, as Sheet to Anki reads it."""
    grid = _run(
        "return m.pasteGrid({name: 'English week 1', rows: data, language: 'en'});",
        [["apple", "quả táo"], ["Apple", "táo"], ["book", "sách"]],
    )
    from src.apkg import resolve_identity
    from src.tsv_model import build_remote_deck_from_tsv
    from src.tsv_model import parse_tsv_data

    tsv = "\n".join("\t".join(row) for row in grid) + "\n"
    deck = build_remote_deck_from_tsv(parse_tsv_data(tsv), "")
    assert deck.sheet_config.warnings == []
    assert sorted(n["ID"] for n in deck.notes) == ["Apple (2)", "apple", "book"]
    identity, name, keyed = resolve_identity("file:x.tsv#", "x", deck.sheet_config)
    assert (identity, name, keyed) == ("name:english week 1", "English week 1", True)


def test_a_sheet_without_an_id_column_gets_its_name_in_the_first_cell():
    grid = _run(
        "return m.namedSheet(data, 'Tuần 1');",
        [["Word", "Meaning"], ["apple", "táo"]],
    )
    assert grid[1] == ["#config name=Tuần 1", ""]


# ---------------------------------------------------------------------------
# A whole sheet pasted as text: what an AI assistant answers with
# ---------------------------------------------------------------------------

FENCED = (
    "Here is your sheet:\n\n"
    "```csv\n"
    "ID,Word,Meaning,Example\n"
    '#config name=Từ vựng IELTS,,"tts=en_US",\n'
    'w01,apple,quả táo,"An apple a day, they say."\n'
    'w02,book,"quyển sách, cuốn sách","Line one\n'
    'line two with ""quotes"""\n'
    "```\n"
    "Copy it into Sheet to Anki."
)


def test_a_fenced_csv_is_a_whole_sheet():
    out = _run("return m.readSheetText(data);", FENCED)
    assert out["delimiter"] == ","
    assert out["name"] == "Từ vựng IELTS"
    rows = out["rows"]
    assert rows[0] == ["ID", "Word", "Meaning", "Example"]
    assert rows[1] == ["#config name=Từ vựng IELTS", "", "tts=en_US", ""]
    assert rows[2][3] == "An apple a day, they say."
    assert rows[3][2] == "quyển sách, cuốn sách"
    assert rows[3][3] == 'Line one\nline two with "quotes"'
    assert len(rows) == 4


def test_an_unfenced_tsv_with_an_id_header_is_a_whole_sheet():
    out = _run(
        "return m.readSheetText(data);",
        "ID\tFront\tBack\nw01\tapple\tquả táo\nw02\tbook\tsách\n",
    )
    assert out["delimiter"] == "\t"
    assert out["name"] == ""
    assert out["rows"][2] == ["w02", "book", "sách"]


def test_a_config_row_without_an_id_header_is_a_whole_sheet():
    out = _run(
        "return m.readSheetText(data);",
        "Mã;Word;Meaning\n#config name=X;;\n1;a;b",
    )
    assert out["delimiter"] == ";"
    assert out["name"] == "X"


def test_a_list_is_not_a_whole_sheet():
    assert _run("return m.readSheetText(data);", "apple - quả táo\nbook - sách") is None
    assert _run("return m.readSheetText(data);", "apple,quả táo\nbook,sách") is None


def test_a_whole_sheet_reads_back_through_the_parser():
    """The rows as Sheet to Anki hands them on, read by the add-on's own parser."""
    from src.tsv_model import build_remote_deck_from_tsv
    from src.tsv_model import parse_tsv_data

    tsv = _run(
        "const s = m.readSheetText(data); const g = m.namedSheet(s.rows, 'ignored');"
        "const { toTsv } = await import("
        + json.dumps((SITE / "sharelink.js").as_uri())
        + ");"
        "return toTsv(g);",
        FENCED,
    )
    deck = build_remote_deck_from_tsv(parse_tsv_data(tsv), "")
    assert deck.sheet_config.warnings == []
    assert deck.sheet_config.deck_name == "Từ vựng IELTS"
    assert len(deck.notes) == 2


def test_a_sheet_without_a_name_gets_the_one_typed():
    grid = _run(
        "return m.namedSheet(data, 'Tuần 1');",
        [["ID", "Front", "Back"], ["w01", "a", "b"]],
    )
    assert grid[1] == ["#config name=Tuần 1", "", ""]
    grid = _run(
        "return m.namedSheet(data, 'Tuần 1');",
        [["ID", "Front"], ["#config reverse", ""], ["w01", "a"]],
    )
    assert grid[1][0] == "#config reverse; name=Tuần 1"


# ---------------------------------------------------------------------------
# The text format: a whole set written as a note
# ---------------------------------------------------------------------------

SHARELINK = (SITE / "sharelink.js").as_uri()


def _read(text, **options):
    """readPaste's model, and the sheet Dán văn bản would hand on (TSV)."""
    return _run(
        f"const {{ toTsv }} = await import({json.dumps(SHARELINK)});"
        "const r = m.readPaste(data.text, data.options);"
        "const grid = m.pasteGrid({name: data.name, rows: r.rows, header: r.header,"
        " cells: r.cells, deck: r.deck, language: 'vi'});"
        "return { model: r, grid, tsv: toTsv(grid) };",
        {"text": text, "options": options, "name": options.pop("name", "Bộ thử")},
    )


def _deck(tsv):
    """The TSV through the page's own path: workbook.read_upload → tsv_model."""
    from src.tsv_model import build_remote_deck_from_tsv
    from src.tsv_model import parse_tsv_data
    from src.workbook import read_upload

    upload = json.loads(read_upload(tsv.encode("utf-8"), "Bộ thử.tsv"))
    return build_remote_deck_from_tsv(parse_tsv_data(upload["tsv"], []), "", [])


FULL = (
    "#config name=Du lịch B1; theme=sakura\n"
    "Word [tts=en_US; bold] | IPA [color=muted] | Meaning | Example [italic]\n"
    "airport | /ˈer.pɔːrt/ | sân bay | We got to the airport early.\n"
    "luggage | /ˈlʌɡ.ɪdʒ/ | hành lý | My luggage is too heavy.\n"
)
# The same set as a sheet holds it: names, then the #config row by position.
TABLE = (
    "Word | IPA | Meaning | Example\n"
    "#config name=Du lịch B1; theme=sakura; tts=en_US; bold | color=muted | | italic\n"
    "airport | /ˈer.pɔːrt/ | sân bay | We got to the airport early.\n"
    "luggage | /ˈlʌɡ.ɪdʒ/ | hành lý | My luggage is too heavy.\n"
)
CSV = (
    "Word,IPA,Meaning,Example\n"
    '"#config name=Du lịch B1; theme=sakura; tts=en_US; bold",color=muted,,italic\n'
    "airport,/ˈer.pɔːrt/,sân bay,We got to the airport early.\n"
    "luggage,/ˈlʌɡ.ɪdʒ/,hành lý,My luggage is too heavy.\n"
)
MARKDOWN = (
    "| Word | IPA | Meaning | Example |\n| --- | --- | --- | --- |\n"
    "| #config name=Du lịch B1; theme=sakura; tts=en_US; bold | color=muted | | italic |\n"
    "| airport | /ˈer.pɔːrt/ | sân bay | We got to the airport early. |\n"
    "| luggage | /ˈlʌɡ.ɪdʒ/ | hành lý | My luggage is too heavy. |\n"
)


def test_config_then_a_bracketed_header_then_words():
    out = _read(FULL, name="")
    model = out["model"]
    assert model["header"] == ["Word", "IPA", "Meaning", "Example"]
    assert model["headerSure"] is True and model["config"] is True
    assert model["deck"] == ["name=Du lịch B1", "theme=sakura"]
    assert model["cells"] == ["tts=en_US; bold", "color=muted", "", "italic"]
    assert len(model["rows"]) == 2
    assert out["grid"][1] == [
        "#config name=Du lịch B1; theme=sakura; tts=en_US; bold",
        "color=muted",
        "",
        "italic",
    ]
    deck = _deck(out["tsv"])
    cfg = deck.sheet_config
    assert cfg.warnings == []
    assert cfg.deck_name == "Du lịch B1" and cfg.theme == "sakura"
    word = cfg.for_field("Word")
    assert (word.tts, word.bold) == ("en_US", True)
    assert cfg.for_field("IPA").color == "muted"
    assert cfg.for_field("Example").italic is True
    assert sorted(n["ID"] for n in deck.notes) == ["airport", "luggage"]


def test_the_text_form_and_the_table_form_are_one_deck():
    """The same set written as text, as a sheet's rows, as CSV, as Markdown."""
    from src.sync_config import to_dict

    decks = []
    for text in (FULL, TABLE, MARKDOWN):
        decks.append(_read(text, name="")["tsv"])
    sheet = _run(
        f"const {{ toTsv }} = await import({json.dumps(SHARELINK)});"
        "const s = m.readSheetText(data); return toTsv(m.namedSheet(s.rows, ''));",
        CSV,
    )
    decks.append(sheet)
    assert decks[0] == decks[1] == decks[2] == decks[3]
    configs = [to_dict(d.plan, d.sheet_config) for d in map(_deck, decks)]
    assert all(c == configs[0] for c in configs)


@pytest.mark.parametrize("config", ["", "#config name=X\n"])
def test_a_bracketed_header_is_never_a_card(config):
    text = (
        config
        + "Word [tts=en_US] | IPA | Meaning | Example [italic]\napple | x | táo | An apple.\n"
    )
    model = _read(text)["model"]
    assert model["header"] == ["Word", "IPA", "Meaning", "Example"]
    assert model["headerSure"] is True
    assert model["cells"] == ["tts=en_US", "", "", "italic"]
    assert len(model["rows"]) == 1


@pytest.mark.parametrize("names", ["foo | bar", "apple | quả táo"])
def test_the_line_after_config_is_always_the_names(names):
    model = _read(f"#config name=X\n{names}\napple | táo\nbook | sách\n")["model"]
    assert model["header"] == [p.strip() for p in names.split("|")]
    assert model["rows"] == [["apple", "táo"], ["book", "sách"]]


def test_names_written_with_bars_over_a_dashed_list():
    model = _read(
        "#config name=X\nMặt trước [tts=en_US] | Mặt sau\napple - quả táo\nbook - sách\n"
    )["model"]
    assert model["header"] == ["Mặt trước", "Mặt sau"]
    assert model["separator"] == "dash"
    assert model["cells"] == ["tts=en_US", ""]


def test_a_single_cloze_card_is_split_the_way_the_names_are():
    # `{{c1::been}}` holds RemNote's `::` and the note's own `:` — neither is
    # the columns when the names over the card are split by bars.
    model = _paste(
        "#config name=X\nSentence [cloze] | Meaning | Note [hint]\n"
        "She has {{c1::been}} here. | Cô ấy ở đây. | Present perfect: has been.\n"
    )
    assert model["separator"] == "pipe"
    assert model["rows"] == [
        ["She has {{c1::been}} here.", "Cô ấy ở đây.", "Present perfect: has been."]
    ]


def test_without_config_the_reader_can_say_the_first_line_is_names():
    model = _read("foo | bar\napple | táo\n", header=True)["model"]
    assert model["header"] == ["foo", "bar"]
    assert model["rows"] == [["apple", "táo"]]


def test_brackets_win_over_a_config_cell_and_say_so():
    model = _read(
        "Word [tts=en_GB] | Meaning\n#config tts=en_US | color=muted\napple | táo\n"
    )["model"]
    assert model["header"] == ["Word", "Meaning"]
    assert model["cells"] == ["tts=en_GB", "color=muted"]
    assert model["warnings"] == [{"key": "txTwice", "col": "Word", "setting": "tts"}]


def test_a_config_cell_with_no_column_is_said():
    model = _read("Word | Meaning\n#config name=X | | italic\napple | táo\n")["model"]
    assert model["warnings"] == [{"key": "txExtraCell", "col": 3}]


def test_a_markdown_table_with_config_above():
    text = (
        "Đây là bộ từ của bạn:\n\n"
        "#config name=Du lịch\n"
        "| Word | Meaning [color=accent] |\n|---|---|\n| airport | sân bay |\n| luggage | hành lý |\n"
    )
    out = _read(text)
    assert out["model"]["table"] is True
    assert out["model"]["header"] == ["Word", "Meaning"]
    assert out["model"]["rows"] == [["airport", "sân bay"], ["luggage", "hành lý"]]
    cfg = _deck(out["tsv"]).sheet_config
    assert cfg.warnings == [] and cfg.for_field("Meaning").color == "accent"


def test_notes_bullets_are_cards():
    model = _read("- apple - quả táo\n- book - quyển sách\n• cat - con mèo\n")["model"]
    assert model["rows"] == [
        ["apple", "quả táo"],
        ["book", "quyển sách"],
        ["cat", "con mèo"],
    ]
    assert model["config"] is False


def test_the_old_kinds_still_read_as_before():
    plain = _read("apple - quả táo\nbook - quyển sách\n")["model"]
    assert (
        plain["header"] is None and plain["cells"] == ["", ""] and plain["deck"] == []
    )
    named = _read("Term\tDefinition\napple\tquả táo\nbook\tquyển sách")["model"]
    assert named["header"] == ["Term", "Definition"] and named["config"] is False
    quizlet = _read("apple\tquả táo;book\tquyển sách;journey\tchuyến đi;")["model"]
    assert quizlet["rowSeparator"]["token"] == ";" and len(quizlet["rows"]) == 3
    assert _run("return m.readSheetText(data);", FENCED)["name"] == "Từ vựng IELTS"
    # The text form is never mistaken for a whole CSV sheet.
    for text in (FULL, "#config name=X\na | b", "| ID | Word |\n|---|---|\n| w1 | a |"):
        assert _run("return m.readSheetText(data);", text) is None


def test_an_id_column_keeps_its_ids():
    out = _read(
        "#config name=X\nID | Word [tts=en_US] | Meaning\nw01 | apple | táo\nw02 | book | sách\n"
    )
    assert out["grid"][0] == ["ID", "Word", "Meaning"]
    assert out["grid"][1] == ["#config name=Bộ thử", "tts=en_US", ""]
    deck = _deck(out["tsv"])
    assert deck.sheet_config.warnings == []
    assert sorted(n["ID"] for n in deck.notes) == ["w01", "w02"]


# ---------------------------------------------------------------------------
# Settings suggested for a paste that has none, written back into its text
# ---------------------------------------------------------------------------


def _suggest(text, choices=None, name="Bộ thử", language="vi"):
    return _run(
        f"const {{ toTsv }} = await import({json.dumps(SHARELINK)});"
        "const lang = data.language;"
        "const r = m.readPaste(data.text);"
        "const s = m.suggestSettings(r, {language: lang});"
        "const choices = {...s.choices, ...(data.choices || {})};"
        "const made = m.applySettings(s, choices, r.deck);"
        "const text = m.withSettings(data.text, r, {name: data.name, names: s.names, ...made});"
        "const grid = m.pasteGrid({name: data.name, rows: r.rows, header: r.header, ...made, language: lang});"
        "const again = m.readPaste(text);"
        "const regrid = m.pasteGrid({name: '', rows: again.rows, header: again.header,"
        " cells: again.cells, deck: again.deck, language: lang});"
        "return { s, made, text, tsv: toTsv(grid), grid, regrid, again };",
        {"text": text, "choices": choices, "name": name, "language": language},
    )


@pytest.mark.parametrize(
    "words, voice",
    [
        (["学习", "银行"], "zh_CN"),
        (["勉強", "ねこ"], "ja_JP"),
        (["공부", "사과"], "ko_KR"),
        (["apple", "journey"], ""),
        (["la pomme", "le chat"], ""),
    ],
)
def test_the_voice_is_guessed_from_the_script(words, voice):
    text = "\n".join(f"{w} - nghĩa {i}" for i, w in enumerate(words))
    assert _suggest(text)["s"]["choices"]["tts"] == voice


@pytest.mark.parametrize(
    "language, names", [("vi", "Mặt trước | Mặt sau"), ("en", "Front | Back")]
)
def test_a_plain_list_gets_both_lines(language, names):
    text = "apple - quả táo\nborrow - mượn\n"
    out = _suggest(
        text,
        {"tts": "en_US", "theme": "sakura"},
        name="Từ mới tuần 3",
        language=language,
    )
    front, back = names.split(" | ")
    assert out["text"] == (
        f"#config name=Từ mới tuần 3; theme=sakura\n{front} [tts=en_US] | {back}\n"
        + text
    )
    # Read back, the text is the same sheet: nothing to choose the second time.
    assert out["regrid"] == out["grid"]
    assert out["again"]["config"] is True
    cfg = _deck(out["tsv"]).sheet_config
    assert cfg.warnings == [] and cfg.theme == "sakura"
    assert cfg.for_field(names.split(" | ")[0]).tts == "en_US"


def test_a_header_without_config_gets_config_and_brackets():
    text = (
        "Word | IPA | Meaning | Example\n"
        "airport | /ˈer.pɔːrt/ | sân bay | We got to the airport early.\n"
        "luggage | /ˈlʌɡ.ɪdʒ/ | hành lý | My luggage is too heavy.\n"
    )
    out = _suggest(text, {"tts": "en_US", "example": True})
    assert out["s"]["example"] == 3
    assert out["made"]["cells"] == [
        "bold; tts=en_US",
        "side=front; color=muted",
        "color=accent",
        "italic; tts=en_US",
    ]
    lines = out["text"].split("\n", 2)
    assert lines[0] == "#config name=Bộ thử"
    assert lines[1] == (
        "Word [bold; tts=en_US] | IPA [side=front; color=muted] | Meaning [color=accent]"
        " | Example [italic; tts=en_US]"
    )
    # The reader's own lines, untouched.
    assert lines[2] == text.split("\n", 1)[1]
    assert out["regrid"] == out["grid"]
    cfg = _deck(out["tsv"]).sheet_config
    assert cfg.warnings == []
    assert cfg.for_field("IPA").side == "front"


def test_a_headerless_table_gets_names_and_a_look_by_shape():
    text = (
        "airport | /ˈer.pɔːrt/ | sân bay | We got to the airport early.\n"
        "luggage | /ˈlʌɡ.ɪdʒ/ | hành lý | My luggage is too heavy.\n"
    )
    out = _suggest(text)
    cells = out["made"]["cells"]
    assert cells[1] == "color=muted" and cells[3] == "italic"
    assert out["text"].startswith(
        "#config name=Bộ thử\nMặt trước | Mặt sau [color=muted] | Mặt sau 2 | Mặt sau 3 [italic]\n"
    )
    assert out["text"].endswith(text)
    assert out["regrid"] == out["grid"]
    assert _deck(out["tsv"]).sheet_config.warnings == []


def test_a_markdown_table_gets_its_config_row_under_the_rule():
    text = "| Word | Meaning |\n|---|---|\n| airport | sân bay |\n"
    out = _suggest(text, {"theme": "matcha"})
    assert out["text"] == (
        "| Word | Meaning |\n|---|---|\n| #config name=Bộ thử; theme=matcha |  |\n| airport | sân bay |\n"
    )
    assert out["regrid"] == out["grid"]


def test_a_picture_column_is_an_image():
    text = (
        "cat | con mèo | https://commons.wikimedia.org/wiki/Special:FilePath/Cat.jpg\n"
        "dog | con chó | https://example.org/dog.png\n"
    )
    assert _suggest(text)["made"]["cells"][2] == "image"


def test_a_bracketed_header_with_no_config_gets_only_the_config_line():
    out = _suggest("Word [tts=en_US] | Meaning [italic]\napple | táo\n", name="Du lịch")
    assert (
        out["text"]
        == "#config name=Du lịch\nWord [tts=en_US] | Meaning [italic]\napple | táo\n"
    )
    assert out["regrid"] == out["grid"]


# ---------------------------------------------------------------------------
# The copies importformats.js keeps of sheet_config's lists
# ---------------------------------------------------------------------------


def test_the_key_lists_match_sheet_config():
    from src import sheet_config as sc
    from src import tsv_model as tm

    got = _run(
        "return {deck: m.DECK_KEYS, column: m.COLUMN_KEYS, themes: m.THEMES,"
        " spoken: m.SPOKEN, image: m.IMAGE_URL.source};"
    )
    assert got["deck"] == list(sc._DECK_KEYS)
    assert set(got["column"]) == set(sc._FIELD_KEYS) | set(sc._RETIRED_KEYS)
    assert got["themes"] == sc.listed_themes()
    build = _builder()
    assert got["spoken"] == [[c, label] for c, label, *_ in build.VOCAB_LANGUAGES]
    assert got["image"].replace("\\/", "/") == tm._IMAGE_URL.pattern


def _builder():
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "build_site", REPO / "scripts" / "build_site.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
