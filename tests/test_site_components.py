#!/usr/bin/env python3
"""The two pieces of the site both pages draw: the deck tree and the card frame.

`site/decktree.js` and `site/cardframe.js` are imported by `app.js` (the preview)
and by `editor.js` (the editor). They are plain string-building modules with no DOM
in them, so they can be imported by node and checked here — which is the only thing
standing between a change to either and two pages breaking at once, since neither
page can be exercised without Pyodide.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parent.parent / "site"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")


def _run(script):
    """Runs an ES module against the real site files and returns its JSON output."""
    result = subprocess.run(
        [NODE, "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        cwd=SITE,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


ROWS = [
    {"kind": "synced", "deck": "Deck::Geography::Capitals"},
    {"kind": "synced", "deck": "Deck::Geography::Rivers"},
    {"kind": "synced", "deck": "Deck::Unsorted"},
    {"kind": "skipped", "deck": "Deck::Geography::Capitals"},
]


@pytest.mark.unit
class TestDeckTree:
    def _tree(self, opts="{}"):
        return _run(
            "import { deckTree, treeHtml } from './decktree.js';\n"
            f"const tree = deckTree({json.dumps(ROWS)});\n"
            f"console.log(JSON.stringify({{ count: tree.count, "
            f"html: treeHtml(tree, {opts}) }}));"
        )

    def test_only_synced_rows_are_counted(self):
        # A row that will not be written to Anki has no deck to be counted in.
        assert self._tree()["count"] == 3

    def test_every_level_counts_what_is_under_it(self):
        html = self._tree()["html"]
        assert '>Deck</span><span class="count">3<' in html
        assert '>Geography</span><span class="count">2<' in html
        assert '>Unsorted</span><span class="count">1<' in html

    def test_levels_are_nested_and_indented(self):
        html = self._tree()["html"]
        assert "--depth:0" in html and "--depth:1" in html and "--depth:2" in html
        assert html.count('<ul class="tree">') == 2  # Deck, then Geography

    def test_names_are_sorted_at_each_level(self):
        html = self._tree()["html"]
        assert html.index(">Capitals<") < html.index(">Rivers<")
        assert html.index(">Geography<") < html.index(">Unsorted<")

    def test_picking_makes_the_levels_buttons(self):
        # The preview page filters its row list by clicking a level; `data-deck` is
        # what its click handler reads.
        html = self._tree('{ pick: true, selected: "Deck::Geography" }')["html"]
        assert 'data-deck="Deck::Geography::Rivers"' in html
        assert '<button data-deck="Deck::Geography"' in html
        assert 'class="on"' in html

    def test_without_picking_there_is_nothing_to_click(self):
        # The editor has one row and nothing to filter down to.
        html = self._tree()["html"]
        assert "<button" not in html and 'class="node"' in html

    def test_a_name_with_markup_in_it_is_escaped(self):
        rows = [{"kind": "synced", "deck": "Deck::<script>x</script>"}]
        out = _run(
            "import { deckTree, treeHtml } from './decktree.js';\n"
            f"console.log(JSON.stringify({{ html: treeHtml(deckTree({json.dumps(rows)})) }}));"
        )
        assert "<script>" not in out["html"]
        assert "&lt;script&gt;" in out["html"]


@pytest.mark.unit
class TestCardFrame:
    def _doc(self, opts):
        return _run(
            "import { cardDoc, cardFrame } from './cardframe.js';\n"
            "const front = { html: '<div data-sc-col=\"Word\">你好</div>' };\n"
            'const back = { html: \'<div data-sc-col="Word">你好</div>'
            '<div data-sc-col="Meaning">xin chào</div>\' };\n'
            f"const doc = cardDoc({{ front, back, ...{opts} }});\n"
            "console.log(JSON.stringify({ doc, frame: cardFrame(doc) }));"
        )

    def test_the_front_tab_shows_only_the_question(self):
        doc = self._doc('{ tab: "front", dark: false }')["doc"]
        assert "xin chào" not in doc

    def test_both_puts_the_answer_under_a_rule_without_repeating_the_question(self):
        # The template answers with {{FrontSide}}, so the question is already in
        # the back's html; printing it twice is what `backOnly` exists to stop.
        doc = self._doc('{ tab: "both", dark: false }')["doc"]
        assert '<hr id="answer">' in doc
        assert doc.count("你好") == 1

    def test_dark_carries_ankis_own_night_mode_class(self):
        # A sheet's theme declares a colour pair, and the second half of it is
        # chosen by this class rather than by the page.
        assert (
            'class="card night_mode"' in self._doc('{ tab: "both", dark: true }')["doc"]
        )
        assert 'class="card"' in self._doc('{ tab: "both", dark: false }')["doc"]

    def test_a_ring_targets_the_column_that_asked_for_it(self):
        doc = self._doc('{ tab: "both", dark: false, ring: "Word" }')["doc"]
        assert '[data-sc-col="Word"]' in doc
        assert "outline: 2px solid" in doc
        assert "animation: sc-pop" not in doc

        flashed = self._doc('{ tab: "both", dark: false, ring: "Word", flash: true }')
        assert "animation: sc-pop" in flashed["doc"]

    def test_a_column_name_with_a_quote_cannot_break_out_of_the_selector(self):
        doc = self._doc('{ tab: "both", dark: false, ring: \'Wo"rd\' }')["doc"]
        assert '[data-sc-col="Wo\\"rd"]' in doc

    def test_no_ring_means_no_rule_for_one(self):
        assert (
            'data-sc-col="'
            not in self._doc('{ tab: "both", dark: false }')["doc"].split("<body")[0]
        )

    def test_the_frame_keeps_the_flags_a_framed_player_needs(self):
        frame = self._doc('{ tab: "both", dark: false }')["frame"]
        # allow-same-origin is not incidental: without it a nested YouTube or Drive
        # player renders a dead black box.
        assert "allow-same-origin" in frame
        assert "allow-scripts" in frame
        assert "srcdoc=" in frame and "&lt;!doctype html&gt;" in frame

    def test_the_document_asks_for_a_referrer(self):
        # An embed loaded with no referrer at all is refused by YouTube (Error 153).
        doc = self._doc('{ tab: "both", dark: false }')["doc"]
        assert 'name="referrer"' in doc
