"""A sheet carried inside a link: ``site/sharelink.js``, run in node.

Create sheet's *Share link* compresses the whole sheet into the address
(``#s=1.…``) and both Create sheet and Create deck open it. Nothing else holds a
copy of what was shared, so a codec that loses a tab inside a cell, a line break,
a quote or a Vietnamese tone mark loses it for good — and the person who opens
the link has no way to know.
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


def _run(body):
    """Runs ``body`` (an async function body with ``m`` the module) in node."""
    script = (
        f"import({json.dumps((SITE / 'sharelink.js').as_uri())}).then(async (m) => {{"
        f"const out = await (async () => {{ {body} }})();"
        "process.stdout.write(JSON.stringify(out)); })"
        ".catch((e) => { process.stdout.write(JSON.stringify("
        "{ error: e.code || e.message })); })"
    )
    out = subprocess.run(
        [NODE, "--no-warnings", "-e", script],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return json.loads(out.stdout)


ROWS = [
    ["ID", "Từ", "Nghĩa", "Ví dụ"],
    ["#config", "size=44; tts=en_US; voices=Ava,Samantha", "side=back", ""],
    ["w01", "hello", "xin chào", "Hello, how are you?"],
    ["w02", "tab\tinside", "two\nlines", 'a "quoted" word'],
    ["w03", "日本語[にほんご]", "tiếng Nhật — ạ ặ ữ đ", "{{c1::cloze}}"],
    ["w04", "", "", "trailing\r\nCRLF"],
]


def _round_trip(name, rows):
    return _run(
        f"const tsv = m.toTsv({json.dumps(rows)});"
        f"const hash = await m.encodeShare({json.dumps(name)}, tsv);"
        "const back = await m.decodeShare(hash);"
        "return { hash, name: back.name, rows: m.parseTsv(back.tsv), same: back.tsv === tsv };"
    )


def test_a_sheet_survives_the_round_trip():
    out = _round_trip("Từ vựng tiếng Anh", ROWS)
    assert out["name"] == "Từ vựng tiếng Anh"
    assert out["same"]
    assert out["rows"] == ROWS


def test_the_link_carries_its_version():
    out = _round_trip("x", ROWS)
    assert out["hash"].startswith("#s=1.")
    # base64url only: nothing a chat app or a URL parser would escape or cut on.
    body = out["hash"][len("#s=1.") :]
    assert body and all(ch.isalnum() or ch in "-_" for ch in body)


def test_a_name_cannot_break_the_payload_with_a_newline():
    out = _round_trip("two\nlines", [["ID", "A"], ["1", "x"]])
    assert out["name"] == "two lines"
    assert out["rows"] == [["ID", "A"], ["1", "x"]]


def test_a_cell_needing_quotes_is_quoted_the_way_csv_reads_it():
    """The add-on reads the TSV with Python's csv.reader; it must agree."""
    import csv
    import io

    tsv = _run(f"return m.toTsv({json.dumps(ROWS)});")
    assert list(csv.reader(io.StringIO(tsv), delimiter="\t")) == ROWS


def test_a_later_version_is_refused_by_name():
    assert _run('return m.decodeShare("#s=2.abc");') == {"error": "version"}


@pytest.mark.parametrize("hash_", ["#s=", "#s=1", "#s=1.", "#s=1.!!!!", "#s=x.abc"])
def test_a_mangled_link_is_called_broken(hash_):
    assert _run(f"return m.decodeShare({json.dumps(hash_)});") == {"error": "broken"}


def test_a_link_cut_short_is_called_broken():
    out = _run(
        f"const h = await m.encodeShare('x', m.toTsv({json.dumps(ROWS * 20)}));"
        "return m.decodeShare(h.slice(0, Math.floor(h.length / 2)));"
    )
    assert out == {"error": "broken"}


def test_the_fragment_is_recognised():
    assert _run(
        'return [m.isShare("#s=1.x"), m.isShare("#example"), m.isShare("")];'
    ) == [
        True,
        False,
        False,
    ]


def test_fifty_words_fit_well_inside_a_safe_link():
    rows = [
        ["ID", "Word", "IPA", "Meaning", "Example"],
        ["#config", "tts=en_US", "", "", ""],
    ]
    rows += [
        [
            f"w{i:02}",
            f"word{i}",
            f"/wɜːd{i}/",
            f"nghĩa số {i}",
            f"An example sentence {i}.",
        ]
        for i in range(1, 51)
    ]
    out = _run(
        f"const h = await m.encodeShare('Vocab', m.toTsv({json.dumps(rows)}));"
        "return [h.length, m.LONG_LINK];"
    )
    assert out[0] < out[1]


def test_csv_is_rfc_4180_with_a_byte_order_mark():
    rows = [["ID", "a,b", 'say "hi"'], ["w01", "two\nlines", "plain"]]
    out = _run(f"return m.asCsv({json.dumps(rows)});")
    assert out == '﻿ID,"a,b","say ""hi"""\r\nw01,"two\nlines",plain\r\n'
