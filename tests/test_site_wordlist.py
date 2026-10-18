"""A pasted word list read as rows: ``site/wordlist.js``, run in node.

Create sheet's *Dán danh sách từ* turns whatever someone copied out of a notes
app into words, and Sheet to Anki is to make a deck straight from such a paste.
A separator guessed wrong splits "well-known" in two or files a whole line as
the word; a duplicate missed is a card twice; a mapping guessed wrong puts the
meaning on the front. None of that is visible until the cards are made.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parent.parent / "site"
NODE = shutil.which("node")

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(NODE is None, reason="node is not installed"),
]


def _run(body, data=None):
    """Runs ``body`` (an async function body; ``m`` the module, ``data`` stdin)."""
    script = (
        "let raw = ''; process.stdin.on('data', (c) => (raw += c));"
        "process.stdin.on('end', () => {"
        f"import({json.dumps((SITE / 'wordlist.js').as_uri())}).then(async (m) => {{"
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
    return json.loads(out.stdout)


def _parse(text, **options):
    return _run(
        "return m.parseList(data.text, data.options);",
        {"text": text, "options": options},
    )


@pytest.mark.parametrize(
    "text, separator",
    [
        ("apple\tquả táo\nbook\tsách", "tab"),
        ("apple - quả táo\nbook - sách", "dash"),
        ("apple – quả táo\nbook — sách", "dash"),
        ("apple = quả táo\nbook=sách", "equals"),
        ("apple | quả táo\nbook|sách", "pipe"),
        ("apple ; quả táo\nbook;sách", "semicolon"),
        ("apple: quả táo\nbook : sách", "colon"),
        ("apple, quả táo\nbook, sách", "comma"),
        ("apple\nbook\njourney", "none"),
    ],
)
def test_the_separator_is_detected(text, separator):
    out = _parse(text)
    assert out["separator"] == separator
    if separator != "none":
        assert out["rows"][0] == ["apple", "quả táo"]


def test_a_hyphen_inside_a_word_is_not_a_separator():
    out = _parse("well-known - nổi tiếng\nup-to-date\nself-made - tự lập")
    assert out["separator"] == "dash"
    assert out["rows"] == [
        ["well-known", "nổi tiếng"],
        ["up-to-date"],
        ["self-made", "tự lập"],
    ]


def test_the_separator_that_splits_most_lines_alike_wins():
    # Every line has a dash; only one has a colon, and a comma sits in a meaning.
    text = "apple - quả táo\nratio - tỉ lệ 1:2\nhello - xin chào, chào bạn"
    out = _parse(text)
    assert out["separator"] == "dash"
    assert out["rows"][1] == ["ratio", "tỉ lệ 1:2"]


def test_a_comma_splits_only_a_line_with_exactly_one():
    out = _parse("apple, quả táo\nhello, how are you, chào")
    assert out["rows"] == [["apple", "quả táo"], ["hello, how are you, chào"]]


def test_a_colon_in_an_address_is_not_a_separator():
    out = _parse("cat: con mèo\nhttps://example.org")
    assert out["rows"][1] == ["https://example.org"]


def test_notes_app_bullets_blank_lines_crlf_and_trailing_spaces():
    text = "1. apple - quả táo  \r\n\r\n• book - sách\r\n* tree - cái cây\r\n- sun - mặt trời \r\n   \r\n2) moon - mặt trăng"
    out = _parse(text)
    assert out["separator"] == "dash"
    assert out["rows"] == [
        ["apple", "quả táo"],
        ["book", "sách"],
        ["tree", "cái cây"],
        ["sun", "mặt trời"],
        ["moon", "mặt trăng"],
    ]
    assert out["skipped"] == 2


def test_a_separator_can_be_chosen_by_hand():
    out = _parse("apple - quả táo; trái táo", separator="semicolon")
    assert out["separator"] == "semicolon"
    assert out["rows"] == [["apple - quả táo", "trái táo"]]
    assert _parse("apple - quả táo", separator="none")["rows"] == [["apple - quả táo"]]


def test_duplicates_in_the_list_and_in_the_sheet_are_marked():
    text = "Apple - táo\napple - quả táo\n  book  - sách\nBOOK - sách\nCafé - cà phê\ncafé - cà phê\ntree - cây"
    out = _parse(text, existing=["TREE", "sun"])
    assert out["marks"] == [None, "list", None, "list", None, "list", "sheet"]
    assert out["duplicates"] == [1, 3, 5, 6]


def test_whitespace_inside_a_word_is_normalised_for_duplicates():
    out = _parse("ice  cream - kem\nice cream - kem")
    assert out["marks"] == [None, "list"]


VOCAB = [
    {"name": "Word", "cell": "size=44; tts=en_US"},
    {"name": "Phiên âm", "cell": ""},
    {"name": "Meaning", "cell": "side=back"},
    {"name": "Example", "cell": ""},
    {"name": "Note", "cell": ""},
]


def test_the_mapping_puts_word_and_meaning_where_they_belong():
    out = _run("return m.guessMapping(data, 2);", VOCAB)
    assert out == [0, 2]
    out = _run("return m.guessMapping(data, 3);", VOCAB)
    assert out == [0, 2, 3]


def test_the_mapping_of_a_basic_sheet_is_front_then_back():
    cols = [{"name": "Mặt trước", "cell": ""}, {"name": "Mặt sau", "cell": ""}]
    assert _run("return m.guessMapping(data, 2);", cols) == [0, 1]


def test_the_mapping_skips_media_columns():
    cols = [
        {"name": "Picture", "cell": "side=front; image; size=300"},
        {"name": "Word", "cell": "side=back"},
        {"name": "Meaning", "cell": ""},
    ]
    assert _run("return m.guessMapping(data, 2);", cols) == [1, 2]


def test_a_row_is_placed_by_its_mapping():
    out = _run("return m.placeRow(['apple', 'quả táo', 'x'], [0, 2, -1], 5);")
    assert out == ["apple", "", "quả táo", "", ""]


def test_column_roles_read_names_in_both_languages_and_media_cells():
    cols = [
        {"name": "Từ", "cell": ""},
        {"name": "Pinyin", "cell": ""},
        {"name": "Nghĩa", "cell": ""},
        {"name": "Ví dụ", "cell": ""},
        {"name": "Hình", "cell": ""},
        {"name": "Sound", "cell": "audio"},
        {"name": "Nguồn", "cell": "side=hide"},
    ]
    roles = _run("return m.columnRoles(data);", cols)
    assert roles == {
        "word": 0,
        "reading": 1,
        "meaning": 2,
        "example": 3,
        "image": 4,
        "audio": 5,
        "source": 6,
    }


def test_the_language_comes_from_tts_then_from_the_script():
    cols = [{"name": "Word", "cell": "tts=zh_CN"}]
    assert _run("return m.listLanguage(data, ['apple']);", cols) == "zh"
    plain = [{"name": "Front", "cell": ""}]
    got = _run(
        "return [m.listLanguage(data, ['사과']), m.listLanguage(data, ['りんご']),"
        " m.listLanguage(data, ['苹果']), m.listLanguage(data, ['apple'])];",
        plain,
    )
    assert got == ["ko", "ja", "zh", "en"]


def test_pinyin_is_the_dictionary_reading_without_tone_sandhi():
    out = _run(
        "const read = await m.loadReader('zh');"
        "return ['一个', '不是', '银行', '觉得', 'apple'].map(read);"
    )
    # With sandhi on, pinyin-pro writes yí gè and bú shì: what is said, not
    # what a dictionary (or the learner's textbook) prints.
    assert out == ["yīgè", "bùshì", "yínháng", "juéde", ""]


def test_korean_is_romanised():
    out = _run(
        "const read = await m.loadReader('ko');"
        "return ['감사합니다', '사과', '같이', 'apple'].map(read);"
    )
    assert out == ["gamsahamnida", "sagwa", "gachi", ""]


def test_japanese_has_no_offline_reader_yet():
    assert _run("return await m.loadReader('ja');") is None


def test_the_vendored_libraries_and_their_licences_ship():
    vendor = SITE / "vendor"
    for name in ("pinyin-pro-3.29.5.min.js", "es-hangul-2.4.0.min.js"):
        text = (vendor / name).read_text(encoding="utf-8")
        assert text.startswith("/*! ") and "MIT License" in text.splitlines()[0]
    for name in ("pinyin-pro-LICENSE.txt", "es-hangul-LICENSE.txt"):
        assert "MIT License" in (vendor / name).read_text(encoding="utf-8")
    source = (SITE / "wordlist.js").read_text(encoding="utf-8")
    assert "./vendor/pinyin-pro-3.29.5.min.js" in source
    assert "./vendor/es-hangul-2.4.0.min.js" in source
    # Loaded on demand: no page or module imports them up front.
    for path in SITE.iterdir():
        if path.suffix in (".html", ".js"):
            text = path.read_text(encoding="utf-8")
            assert 'from "./vendor/' not in text, path.name
