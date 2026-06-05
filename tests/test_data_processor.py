#!/usr/bin/env python3
"""
Real tests for ``src.data_processor`` (TSV → RemoteDeck).

These exercise the actual functions (previously this file shadowed the import with an
inline mock and asserted against a dead Portuguese schema). See conftest for the Anki
import-mocking that lets ``src`` import without a real Anki.
"""

import pytest

from src import data_processor as d
from src import templates_and_definitions as cols

DECK_URL = "https://docs.google.com/spreadsheets/d/ABC/edit"


def _deck(tsv, **kw):
    return d.build_remote_deck_from_tsv(d.parse_tsv_data(tsv), DECK_URL, **kw)


@pytest.mark.unit
class TestParsing:
    def test_headers_and_rows(self):
        parsed = d.parse_tsv_data("ID\tQUESTION\tANSWER\nQ1\tWhat?\tThis.")
        assert parsed["headers"][0] == "ID"
        assert parsed["rows"] == [["Q1", "What?", "This."]]

    def test_tab_inside_quoted_cell_is_not_a_delimiter(self):
        parsed = d.parse_tsv_data('ID\tQUESTION\tANSWER\nQ1\t"a\tb"\tc')
        # The quoted tab stays part of the QUESTION cell.
        assert parsed["rows"][0] == ["Q1", "a\tb", "c"]


@pytest.mark.unit
class TestSyncSemantics:
    @pytest.mark.parametrize("value", ["true", "TRUE", "1", "yes", "sim"])
    def test_truthy_sync_values_marked(self, value):
        deck = _deck(f"ID\tQUESTION\tANSWER\tSYNC\nQ1\tq\ta\t{value}")
        assert deck.sync_marked_lines == 1

    @pytest.mark.parametrize("value", ["false", "0", "no", ""])
    def test_falsey_sync_values_not_marked(self, value):
        deck = _deck(f"ID\tQUESTION\tANSWER\tSYNC\nQ1\tq\ta\t{value}")
        assert deck.sync_marked_lines == 0


@pytest.mark.unit
class TestStudentMetrics:
    def test_missing_student_is_counted_as_sentinel(self):
        deck = _deck("ID\tQUESTION\tANSWER\tSYNC\tSTUDENTS\nQ1\tq\ta\ttrue\t")
        assert cols.DEFAULT_STUDENT in deck.notes_per_student

    def test_multiple_students_split_on_comma(self):
        deck = _deck("ID\tQUESTION\tANSWER\tSYNC\tSTUDENTS\nQ1\tq\ta\ttrue\tJohn, Mary")
        assert "John" in deck.unique_students
        assert "Mary" in deck.unique_students

    def test_underscore_in_student_name_is_preserved(self):
        # Regression context: student names may contain '_'. The build must keep the
        # name whole (the sync key logic anchors on remote IDs rather than splitting).
        deck = _deck("ID\tQUESTION\tANSWER\tSYNC\tSTUDENTS\nQ1\tq\ta\ttrue\tAna_B")
        assert "Ana_B" in deck.unique_students


@pytest.mark.unit
class TestClozeFormatting:
    def test_has_cloze_detects_basic_and_uppercase(self):
        assert d.has_cloze_deletion("{{c1::x}}")
        assert d.has_cloze_deletion("{{C2::x::hint}}")
        assert not d.has_cloze_deletion("no cloze")

    def test_clean_strips_markup_and_hint(self):
        assert d.clean_cloze_formatting("{{c1::Hello}}") == "Hello"
        assert d.clean_cloze_formatting("{{c2::World::hint}}") == "World"

    def test_clean_preserves_colons_inside_content(self):
        # Regression: content with colons (times, ions, ratios) must survive.
        assert d.clean_cloze_formatting("{{c1::10:30}}") == "10:30"
        assert d.clean_cloze_formatting("{{c1::Na+ : K+}}") == "Na+ : K+"
        assert d.clean_cloze_formatting("{{c1::a::b::c}}") == "a"

    def test_clean_handles_multiple_clozes_and_case(self):
        assert d.clean_cloze_formatting("a {{c1::X}} b {{c2::Y::h}} c") == "a X b Y c"
        assert d.clean_cloze_formatting("{{C1::upper}}") == "upper"


@pytest.mark.unit
class TestTagsGeneration:
    def test_other_tags_split_and_namespaced(self):
        note = {cols.identifier: "Q1", cols.tags_4: "review, hard"}
        tags = d.create_tags_from_fields(note)
        assert any("other_tags::review" in t for t in tags)
        assert any("other_tags::hard" in t for t in tags)
