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
