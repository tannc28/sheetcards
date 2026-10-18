"""A sheet written as text and read back: ``site/sheettext.js``.

Create sheet's Văn bản view, its .txt download and Copy văn bản write the text
form, and read it back through importformats.readPaste — the reading Sheet to
Anki gives a paste. The grid → text → grid trip must give the same cells, and
the grid → TSV → grid trip (Copy bảng, .tsv) likewise; a sheet the text form
cannot hold must be said to be one, never cut into the wrong cells.
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


def _run(body, data):
    script = (
        "let raw = ''; process.stdin.on('data', (c) => (raw += c));"
        "process.stdin.on('end', () => {"
        f"Promise.all([import({json.dumps((SITE / 'sheettext.js').as_uri())}),"
        f"import({json.dumps((SITE / 'sharelink.js').as_uri())})]).then(([m, s]) => {{"
        "const data = JSON.parse(raw);"
        f"const out = (() => {{ {body} }})();"
        "process.stdout.write(JSON.stringify(out)); })"
        ".catch((e) => { process.stdout.write(JSON.stringify({ error: String(e) })); });"
        "});"
    )
    out = subprocess.run(
        [NODE, "--no-warnings", "-e", script],
        input=json.dumps(data),
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    result = json.loads(out.stdout)
    assert not (isinstance(result, dict) and "error" in result), result
    return result


def _trip(grid):
    return _run(
        "const text = m.sheetText(data);"
        "return { text, back: m.sameShape(m.sheetGrid(text).grid),"
        " want: m.sameShape(data), holds: m.textHolds(data),"
        " tsv: m.sameShape(s.parseTsv(s.toTsv(data))) };",
        grid,
    )


VOCAB = [
    ["Word", "Phiên âm", "Meaning", "Example"],
    [
        "#config name=Từ vựng B1; theme=sakura; tts=en_US; bold",
        "color=muted",
        "",
        "italic; tts=en_US",
    ],
    ["apple", "/ˈæp.əl/", "quả táo", "I ate an apple, then a pear."],
    ["book", "", "", ""],
    ["well-known", "", "nổi tiếng - được biết", "a = b; c"],
    ["a, b", "x", "", ""],
]

WITH_ID = [
    ["ID", "Front", "Back", "TAGS", "SUBDECK 1"],
    ["#config name=X; next=w03; shape=b2", "side=front", "", "", ""],
    ["w01", "dog", "chó", "animal; pet", "Animals"],
    ["w02", "", "mèo", "", ""],
]


def test_an_id_less_sheet_round_trips():
    out = _trip(VOCAB)
    assert out["back"] == out["want"]
    assert out["holds"] == {"ok": True, "why": ""}
    lines = out["text"].splitlines()
    assert lines[0] == "#config name=Từ vựng B1; theme=sakura"
    assert lines[1].startswith("Word [tts=en_US; bold] | Phiên âm [color=muted]")
    assert "ID" not in lines[1].split(" | ")
    # A word with nothing beside it still marks where its first cell ends.
    assert "book |" in lines


def test_a_sheet_with_an_id_column_keeps_it_first():
    out = _trip(WITH_ID)
    assert out["back"] == out["want"]
    assert out["holds"]["ok"]
    lines = out["text"].splitlines()
    assert lines[0] == "#config name=X; next=w03; shape=b2"
    assert lines[1].startswith("ID | Front [side=front] | Back | TAGS | SUBDECK 1")
    assert "w02 | | mèo" in lines


def test_a_sheet_with_no_words_round_trips():
    grid = [["Front", "Back"], ["#config name=Empty", ""]]
    out = _trip(grid)
    assert out["back"] == out["want"]


@pytest.mark.parametrize(
    "cell, why",
    [("a | b", "pipe"), ("line one\nline two", "newline")],
)
def test_a_cell_the_text_form_cannot_hold_is_said(cell, why):
    grid = [row[:] for row in WITH_ID]
    grid[2][2] = cell
    out = _trip(grid)
    assert out["holds"] == {"ok": False, "why": why}
    # The table form holds it all the same.
    assert out["tsv"] == out["want"]


@pytest.mark.parametrize("grid", [VOCAB, WITH_ID])
def test_the_tsv_round_trips(grid):
    out = _trip(grid)
    assert out["tsv"] == out["want"]


def test_semicolons_in_a_word_stay_in_their_cell():
    grid = [["Front", "Back"], ["#config", ""], ["x; y", "a;b"]]
    out = _trip(grid)
    assert out["holds"]["ok"]
    assert out["back"] == out["want"]
