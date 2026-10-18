"""Which deck a sheet is: ``site/identity.js``, run in node.

A sheet's ``name=`` is its deck and its identity; without one, a file is
keyed by its name with what a phone adds to a second download taken off. The
note guids follow from this (``apkg.resolve_identity``), so a mistake here is a
deck that doubles on the next import — or two decks that overwrite each other.
"""

import json
import shutil
import subprocess
import unicodedata
from pathlib import Path

import pytest

from src.apkg import deck_identity

SITE = Path(__file__).resolve().parent.parent / "site"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")

# A plain object standing in for localStorage.
STORE = (
    "const mem = {}; const s = { getItem: (k) => (k in mem ? mem[k] : null),"
    " setItem: (k, v) => { mem[k] = String(v); } };"
)


def _run(expr):
    script = (
        f"import({json.dumps((SITE / 'identity.js').as_uri())}).then((m) => {{"
        f"{STORE} process.stdout.write(JSON.stringify({expr})); }})"
    )
    out = subprocess.run(
        [NODE, "--no-warnings", "-e", script],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return json.loads(out.stdout)


@pytest.mark.parametrize(
    "name",
    [
        "Từ vựng.csv",
        "Từ vựng (1).csv",
        "Từ vựng(2).tsv",
        "Từ vựng-2.csv",
        "Từ vựng.xlsx",
    ],
)
def test_a_second_download_is_the_same_file(name):
    assert _run(f"m.fileIdentity({json.dumps(name)})") == "file:Từ vựng.tsv#"


def test_the_create_sheet_handoff_keeps_the_identity_it_always_had():
    assert _run('m.fileIdentity("Từ vựng.tsv")') == "file:Từ vựng.tsv#"


def test_a_number_that_is_part_of_the_name_is_kept():
    assert _run('[m.fileStem("HSK 1.csv"), m.fileStem("HSK 2.csv")]') == [
        "HSK 1",
        "HSK 2",
    ]


def test_the_deck_key_is_the_python_one():
    for name in ["  Từ   VỰNG ", unicodedata.normalize("NFD", "Tiếng Việt")]:
        assert _run(f"m.deckKey({json.dumps(name)})") == deck_identity(name)


def test_the_marker_cell_is_edited_pair_by_pair():
    out = _run(
        '[m.markerSet("#config theme=sakura", "name", "Từ; vựng"),'
        ' m.markerSet("#config name=A; theme=sakura", "name", "B"),'
        ' m.markerSet("#config name=A; next=w03", "name", ""),'
        ' m.markerGet("#config theme=sakura; name=Từ vựng", "name"),'
        ' m.markerGet("#config", "next")]'
    )
    assert out == [
        "#config theme=sakura; name=Từ, vựng",
        "#config name=B; theme=sakura",
        "#config next=w03",
        "Từ vựng",
        None,
    ]


def test_used_names_are_matched_as_identities():
    out = _run(
        '(m.rememberName("Từ vựng", s), '
        '[m.nameUsed(" từ  VỰNG", s), m.nameUsed("Tiếng Anh", s)])'
    )
    assert out == [True, False]


def test_a_changed_note_type_is_told_apart():
    out = _run(
        "[m.shapeChange(null, {kind: 'basic', fields: ['ID']}),"
        " m.shapeChange({kind: 'basic', fields: ['ID', 'A'], templates: ['Card 1']},"
        "               {kind: 'basic', fields: ['ID', 'A'], templates: ['Card 1']}),"
        " m.shapeChange({kind: 'basic', fields: ['ID', 'A'], templates: ['Card 1']},"
        "               {kind: 'basic', fields: ['ID', 'A', 'B'], templates: ['Card 1']}),"
        " m.shapeChange({kind: 'basic', fields: ['ID'], templates: ['Card 1']},"
        "               {kind: 'basic', fields: ['ID'], templates: ['Card 1', 'Card 2']}),"
        " m.shapeChange({kind: 'basic', fields: ['ID']}, {kind: 'cloze', fields: ['ID']})]"
    )
    assert out == [None, None, "schema", "template", "cloze"]


def test_a_shape_code_is_told_apart_the_same_way():
    out = _run(
        "[m.codeChange(null, 'b1234ab'), m.codeChange('b1234ab', 'b1234ab'),"
        " m.codeChange('b1234ab', 'b9999ab'), m.codeChange('b1234ab', 'b1234cd'),"
        " m.codeChange('b1234ab', 'c1234ab')]"
    )
    assert out == [None, None, "schema", "template", "cloze"]


def test_the_sheet_wins_when_another_device_downloaded_since():
    last = (
        "{kind: 'basic', fields: ['ID', 'A'], templates: ['Card 1'], code: 'b1111aa'}"
    )
    now = "{kind: 'basic', fields: ['ID', 'A'], templates: ['Card 1']}"
    out = _run(
        f"[m.judgeShape({last}, 'b1111aa', 'b1111aa', {now}),"
        f" m.judgeShape({last}, 'b2222aa', 'b1111aa', {now}),"
        f" m.judgeShape(null, 'b2222aa', 'b1111aa', {now}),"
        f" m.judgeShape({last}, null, 'b1111aa', {now}),"
        f" m.judgeShape(null, null, 'b1111aa', {now})]"
    )
    assert [(o["change"], o["known"]) for o in out] == [
        (None, True),
        ("schema", True),
        ("schema", True),
        (None, True),
        (None, False),
    ]


def test_a_named_set_from_before_asks_for_its_old_deck_to_be_renamed():
    ident = "{named: true, root: 'Từ vựng', deck: 'Từ vựng'}"
    out = _run(
        f"[m.renamedRoot({{deck: 'Từ vựng', fields: []}}, {ident}),"
        f" m.renamedRoot({{deck: 'Từ vựng', root: 'Từ vựng', fields: []}}, {ident}),"
        f" m.renamedRoot(null, {ident}),"
        " m.renamedRoot({deck: 'X', fields: []}, {named: false, root: 'sc_X'})]"
    )
    assert out == ["sc_Từ vựng", None, None, None]


def test_a_newly_stubbed_template_is_said_once():
    out = _run(
        "[m.droppedTemplates({kind: 'basic', stubs: []}, {kind: 'basic', stubs: ['R']}),"
        " m.droppedTemplates({kind: 'basic', stubs: ['R']}, {kind: 'basic', stubs: ['R']}),"
        " m.droppedTemplates(null, {kind: 'basic', stubs: ['R']}),"
        " m.droppedTemplates({kind: 'basic'}, {kind: 'cloze', stubs: ['R']})]"
    )
    assert out == [["R"], [], [], []]


def test_storage_that_throws_costs_the_feature_not_the_page():
    broken = "{ getItem() { throw 1; }, setItem() { throw 1; } }"
    assert _run(
        f"[m.usedNames({broken}), m.rememberName('x', {broken}),"
        f" m.lastShape('k', {broken}), m.keepShape('k', {{}}, {broken})]"
    ) == [[], False, None, False]
