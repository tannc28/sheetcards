"""The settings row's warnings, coded once and said in both languages.

``src/sheet_config.py`` (and ``tsv_model``) tag every warning with a code from
``WARNING_CODES``; ``site/sheetwarnings.js`` says each code in English and
Vietnamese. These tests hold the three together: no code without a sentence,
no sentence without a code, and the site's English is the parser's English
word for word, measured on warnings the parser really produces.
"""

import ast
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from src.column_model import plan_columns
from src.sheet_config import WARNING_CODES
from src.sheet_config import parse_config_row
from src.sheet_config import warning_codes
from src.tsv_model import build_remote_deck_from_tsv
from src.tsv_model import parse_tsv_data

REPO = Path(__file__).resolve().parent.parent
MODULE = REPO / "site" / "sheetwarnings.js"
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node is not installed")


def _codes_in_source():
    """Every code a ``_w(...)`` or ``SheetWarning(...)`` call can carry."""
    found = set()
    for name in ("sheet_config.py", "tsv_model.py"):
        tree = ast.parse((REPO / "src" / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = getattr(node.func, "id", None)
            if func == "_w" and node.args:
                arg = node.args[0]
            elif func == "SheetWarning" and len(node.args) > 1:
                arg = node.args[1]
            else:
                continue
            if isinstance(arg, ast.Constant):
                found.add(arg.value)
            elif isinstance(arg, ast.JoinedStr):
                # f"only-one-{role}": every listed code with that prefix
                prefix = arg.values[0].value
                found |= {c for c in WARNING_CODES if c.startswith(prefix)}
            elif isinstance(arg, ast.Name) or (
                isinstance(arg, ast.Call) and getattr(arg.func, "id", "") == "getattr"
            ):
                continue  # _w itself, or a warning re-wrapped with its own code
            else:
                found.add("<computed>")
    found.discard("")
    return found


def _node(script, data=None):
    result = subprocess.run(
        [NODE, "--input-type=module", "-e", script],
        input=json.dumps(data) if data is not None else None,
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


_IMPORT = f'import {{ WARNINGS, warningText }} from "{MODULE.as_uri()}";\n'


@pytest.mark.unit
def test_every_call_names_a_listed_code():
    used = _codes_in_source()
    assert "<computed>" not in used
    assert used == set(WARNING_CODES), (
        f"unlisted: {sorted(used - set(WARNING_CODES))}, "
        f"listed but never raised: {sorted(set(WARNING_CODES) - used)}"
    )


@needs_node
@pytest.mark.unit
def test_every_code_has_both_languages_and_nothing_else():
    table = _node(
        _IMPORT
        + "console.log(JSON.stringify(Object.fromEntries(Object.entries(WARNINGS)"
        ".map(([k, v]) => [k, Object.keys(v).sort()]))));"
    )
    assert set(table) == set(WARNING_CODES)
    assert all(langs == ["en", "vi"] for langs in table.values()), table


# Settings rows that between them raise most of the codes, read by the parser.
PLAN = plan_columns(["ID", "Word", "Pic", "Sound", "Meaning", "Note", "SUBDECK 1"])
ROWS = [
    {
        "ID": "#config theme=nope; speed=9; align=up; foo; next=abc; name",
        "Word": "side=up; size=900; color=nopecolour; tts=zh; speed=x; voices=,"
        "; cloze; bold; rtl; vertical; math; code",
        "Pic": "image; audio; tts=en_US; furigana; color=red; math; subdeck=1",
        "Sound": "audio; size=40; sort",
        "Meaning": "type=zz; math=zz; cloze; subdeck=x; whatever=1; draw; size=5000",
        "Note": "subdeck=0; side; font=; align=x; size=x; sort; type; draw; furigana",
    },
    {
        "ID": "#config speed=x; name=A::::B",
        "Word": "draw; image",
        "Pic": "video; subdeck=1; bold",
        "Meaning": "subdeck=1; side=front",
        "Note": "draw; bold; italic; furigana; math",
        "Sound": "sort; image",
    },
    {
        "ID": "#config name=" + "x" * 101,
        "Word": "speed=3; subdeck=2",
        "Pic": "image; type; size=3000",
        "Meaning": "type",
        "Note": "subdeck=2",
    },
]


def _real_warnings():
    found = []
    for row in ROWS:
        found += warning_codes(parse_config_row(row, PLAN).warnings)
    tsv = (
        "ID\tSentence\tClip\n#config\t\tvideo\n"
        "1\t{{c1::x}}\thttps://www.youtube.com/@channel\n"
    )
    found += warning_codes(
        build_remote_deck_from_tsv(parse_tsv_data(tsv), "u").sheet_config.warnings
    )
    # The hints read the rows, and the SUBDECK one needs no settings row at all.
    tsv = (
        "ID\tSUBDECK 1\tWord\tPic\n"
        "1\tA\t日本語[にほんご]\thttps://example.org/a.png\n"
        "2\tB\t私[わたし]\thttps://example.org/b.JPG\n"
    )
    found += warning_codes(
        build_remote_deck_from_tsv(parse_tsv_data(tsv), "u").sheet_config.warnings
    )
    return found


@needs_node
@pytest.mark.unit
def test_the_english_is_the_parsers_own_sentence():
    warnings = _real_warnings()
    assert (
        len({w["code"] for w in warnings}) >= 30
    ), "the samples stopped covering codes"
    said = _node(
        _IMPORT + "let s=''; for await (const c of process.stdin) s+=c;"
        "console.log(JSON.stringify(JSON.parse(s).map((w) => [warningText(w, 'en'), "
        "warningText(w, 'vi')])));",
        warnings,
    )
    for warning, (en, vi) in zip(warnings, said, strict=True):
        assert en == warning["text"], warning["code"]
        assert vi and "undefined" not in vi, warning["code"]
        assert vi != en, warning["code"]


@needs_node
@pytest.mark.unit
def test_an_unknown_code_keeps_the_english():
    out = _node(
        _IMPORT
        + "console.log(JSON.stringify(warningText({code: 'new', text: 'hello'}, 'vi')));"
    )
    assert out == "hello"
