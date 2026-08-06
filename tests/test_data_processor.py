#!/usr/bin/env python3
"""
Real tests for ``src.data_processor`` (TSV → RemoteDeck).

These exercise the actual functions (previously this file shadowed the import with an
inline mock and asserted against a dead Portuguese schema). See conftest for the Anki
import-mocking that lets ``src`` import without a real Anki.
"""

import pytest

from src import data_processor as d
from src.column_model import plan_columns

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
class TestPotentialNoteMetrics:
    def test_plain_row_counts_as_one_note(self):
        deck = _deck("ID\tQUESTION\tANSWER\tSYNC\nQ1\tq\ta\ttrue")
        assert deck.total_potential_anki_notes == 1

    def test_every_valid_row_is_exactly_one_note(self):
        # The reverse direction is a second card template on the same note type,
        # not a second note, so the count tracks rows one-for-one.
        deck = _deck("ID\tFront\tBack\tSYNC\nQ1\tq\ta\ttrue\nQ2\tq2\ta2\ttrue")
        assert deck.total_potential_anki_notes == 2


@pytest.mark.unit
class TestClozeFormatting:
    def test_has_cloze_detects_basic_and_uppercase(self):
        assert d.has_cloze_deletion("{{c1::x}}")
        assert d.has_cloze_deletion("{{C2::x::hint}}")
        assert not d.has_cloze_deletion("no cloze")


@pytest.mark.unit
class TestTagsGeneration:
    def test_root_tag_deck_path_and_user_tags(self):
        plan = plan_columns(["ID", "SUBDECK 1", "SUBDECK 2", "TAGS", "Front"])
        row = {
            "ID": "Q1",
            "SUBDECK 1": "Unit 3",
            "SUBDECK 2": "Verbs",
            "TAGS": "review, hard",
            "Front": "q",
        }
        tags = d.build_tags(row, plan)

        assert tags[0] == "sheets2anki"
        assert "sheets2anki::unit_3::verbs" in tags
        assert "review" in tags and "hard" in tags

    def test_non_ascii_deck_levels_and_tags_are_kept(self):
        # Unicode coverage: deck levels and user tags in another script must end up
        # in the tag tree with their characters intact, only lower-cased and with
        # spaces folded to underscores.
        plan = plan_columns(["ID", "SUBDECK 1", "SUBDECK 2", "TAGS", "Front"])
        row = {
            "ID": "Q1",
            "SUBDECK 1": "Bài 3",
            "SUBDECK 2": "Động từ",
            "TAGS": "ôn tập, 汉字",
            "Front": "q",
        }
        tags = d.build_tags(row, plan)

        assert tags[0] == "sheets2anki"
        assert "sheets2anki::bài_3::động_từ" in tags
        assert "ôn_tập" in tags and "汉字" in tags

    def test_no_placeholder_tags_for_blank_levels(self):
        # The old model emitted [missing_subtopic]-style tags; nothing should now.
        plan = plan_columns(["ID", "SUBDECK 1", "Front"])
        tags = d.build_tags({"ID": "Q1", "SUBDECK 1": "", "Front": "q"}, plan)
        assert tags == ["sheets2anki"]
