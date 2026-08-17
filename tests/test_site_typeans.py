#!/usr/bin/env python3
"""The typed-answer box, checked against what Anki itself produces.

`{{type:Field}}` is resolved by Anki's *reviewer*, not by its template renderer:
the tag survives rendering and is swapped for an input while the question is up,
then for a character-by-character comparison once the answer is shown. There is
nothing in ``src/`` to reuse for it, so ``site/typeans.js`` reimplements
``Collection.compare_answer`` — and a reimplementation is worth exactly as much
as the thing it is pinned to.

``CASES`` below is the output of a real Anki 26.08, read off a live collection::

    col.compare_answer(expected, provided, combining)

so a change to the diff that drifts away from Anki fails here. One difference is
deliberate: Anki wraps the result in ``<code id=typeans>`` and the preview draws
its *input* with that id, so ``compareAnswer`` returns the inside of the element
and the caller wraps it. Everything between the wrappers is compared verbatim.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parent.parent / "site"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")

ARROW = "<br><span id=typearrow>&darr;</span><br>"

# (expected, typed, combining, what Anki returned inside <code id=typeans>).
# `combining` False is the `nc:` prefix — compare without the accents.
CASES = [
    ("abc", "abc", True, "<span class=typeGood>abc</span>"),
    # Nothing typed: the expected text, bare. Not a diff, and not empty.
    ("abc", "", True, "abc"),
    (
        "abc",
        "abcd",
        True,
        "<span class=typeGood>abc</span><span class=typeBad>d</span>"
        + ARROW
        + "<span class=typeGood>abc</span>",
    ),
    # A letter left out is a dash standing in its place, not a silent gap.
    (
        "abcd",
        "ab",
        True,
        "<span class=typeGood>ab</span><span class=typeMissed>--</span>"
        + ARROW
        + "<span class=typeGood>ab</span><span class=typeMissed>cd</span>",
    ),
    (
        "ab",
        "ba",
        True,
        "<span class=typeMissed>-</span><span class=typeGood>b</span>"
        "<span class=typeBad>a</span>"
        + ARROW
        + "<span class=typeMissed>a</span><span class=typeGood>b</span>",
    ),
    # A wrong letter and a missing letter in the same place are one substitution:
    # the wrong one against the right one, and no dash.
    (
        "学校",
        "学枚",
        True,
        "<span class=typeGood>学</span><span class=typeBad>枚</span>"
        + ARROW
        + "<span class=typeGood>学</span><span class=typeMissed>校</span>",
    ),
    (
        "北京",
        "北 京",
        True,
        "<span class=typeGood>北</span><span class=typeBad> </span>"
        "<span class=typeGood>京</span>"
        + ARROW
        + "<span class=typeGood>北</span><span class=typeGood>京</span>",
    ),
    # Which of two equally long alignments Anki picks: the missing letter is
    # reported at the first l of "hello", not the second.
    (
        "hello world",
        "helo wrld",
        True,
        "<span class=typeGood>he</span><span class=typeMissed>-</span>"
        "<span class=typeGood>lo w</span><span class=typeMissed>-</span>"
        "<span class=typeGood>rld</span>"
        + ARROW
        + "<span class=typeGood>he</span><span class=typeMissed>l</span>"
        "<span class=typeGood>lo w</span><span class=typeMissed>o</span>"
        "<span class=typeGood>rld</span>",
    ),
    (
        "a",
        "xyz",
        True,
        "<span class=typeBad>xyz</span>" + ARROW + "<span class=typeMissed>a</span>",
    ),
    ("", "abc", True, "<span class=typeBad>abc</span>" + ARROW),
    (
        "la casa",
        "LA CASA",
        True,
        "<span class=typeBad>LA</span><span class=typeGood> </span>"
        "<span class=typeBad>CASA</span>"
        + ARROW
        + "<span class=typeMissed>la</span><span class=typeGood> </span>"
        "<span class=typeMissed>casa</span>",
    ),
    # nc: the accent does not count against you, and what you are shown back is
    # the *right* spelling rather than the one you typed.
    ("el árbol", "el arbol", False, "<span class=typeGood>el árbol</span>"),
    ("rápidamente", "rapidamente", False, "<span class=typeGood>rápidamente</span>"),
    ("el árbol", "el árbol", True, "<span class=typeGood>el árbol</span>"),
    (
        "el árbol",
        "el arbl",
        False,
        "<span class=typeGood>el arb</span><span class=typeMissed>-</span>"
        "<span class=typeGood>l</span>"
        + ARROW
        + "<span class=typeGood>el árb</span><span class=typeMissed>o</span>"
        "<span class=typeGood>l</span>",
    ),
]


def _run(script):
    result = subprocess.run(
        [NODE, "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        cwd=SITE,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.unit
def test_the_comparison_is_the_one_anki_draws():
    payload = json.dumps([[c[0], c[1], not c[2]] for c in CASES])
    got = _run(
        "import { compareAnswer } from './typeans.js';\n"
        f"const cases = {payload};\n"
        "console.log(JSON.stringify(cases.map("
        "([e, t, nc]) => compareAnswer(e, t, nc))));"
    )
    for (expected, typed, _combining, want), actual in zip(CASES, got, strict=True):
        assert actual == want, f"{expected!r} vs {typed!r}"


@pytest.mark.unit
def test_the_question_draws_a_box_instead_of_the_answer():
    """The bug this exists to prevent: `type` treated as an unknown filter.

    An unknown filter falls through to the field's value, which on a typed-answer
    card is the answer — printed on the question, which is the one thing the card
    is for. The answer does travel with the box, in the attribute the comparison
    is drawn from; what it must not do is get drawn.
    """
    out = _run(
        "import { renderSide } from './anki.js';\n"
        "const r = renderSide('{{type:Word}}', {Word: 'el árbol'});\n"
        "console.log(JSON.stringify(r.html));"
    )
    assert 'id="typeans"' in out
    assert '"expect":"el árbol"' in out.replace("&quot;", '"')

    drawn = re.sub(r'data-typeans="[^"]*"', "", out)
    assert "el árbol" not in drawn, "the answer is rendered on the question"


@pytest.mark.unit
def test_nc_and_cloze_reach_the_box():
    out = _run(
        "import { renderSide } from './anki.js';\n"
        "const plain = renderSide('{{type:nc:W}}', {W: 'árbol'});\n"
        "const cl = renderSide('{{type:cloze:S}}', "
        "{S: '他{{c1::在}}图书馆{{c2::看}}书。'}, {ordinal: 1});\n"
        "console.log(JSON.stringify({plain: plain.html, cloze: cl.html}));"
    )
    assert '"nc":true' in out["plain"].replace("&quot;", '"')
    # {{type:cloze:}} asks for the deletions of this card's number, not the whole
    # sentence — c2 belongs to the other card.
    spec = out["cloze"].replace("&quot;", '"')
    assert '"expect":"在"' in spec


@pytest.mark.unit
def test_an_empty_field_draws_no_box():
    """Anki removes the tag outright rather than asking for nothing."""
    out = _run(
        "import { renderSide } from './anki.js';\n"
        "console.log(JSON.stringify("
        "renderSide('{{type:W}}', {W: '   '}).html.trim()));"
    )
    assert out == ""


@pytest.mark.unit
def test_the_card_document_carries_the_comparison_with_it():
    """The card is its own document, so the diff travels as source, not an import."""
    out = _run(
        "import { typeansRuntime } from './typeans.js';\n"
        "console.log(JSON.stringify(typeansRuntime()));"
    )
    assert "function compareAnswer" in out
    assert "</script" not in out[: out.rindex("<")]
