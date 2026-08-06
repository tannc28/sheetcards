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
class TestSettingsRow:
    """The optional ``#config`` row is a directive, not data."""

    TSV = (
        "ID\tQUESTION\tANSWER\tSYNC\n"
        "#config reverse; align=left\tsize=48; tts=en_US\tcolor=muted\t\n"
        "Q1\tq\ta\ttrue\n"
    )

    def test_settings_row_is_not_a_note(self):
        deck = _deck(self.TSV)
        assert [n["ID"] for n in deck.notes] == ["Q1"]

    def test_settings_row_is_in_no_metric(self):
        # Not a valid line, not an invalid line, not a ghost row: it is not a line of
        # the table at all as far as the sync report is concerned.
        deck = _deck(self.TSV)
        assert deck.total_table_lines == 1
        assert deck.valid_note_lines == 1
        assert deck.invalid_note_lines == 0
        assert deck.ignored_ghost_rows == 0
        assert deck.total_potential_anki_notes == 1
        deck.validate_metrics()

    def test_settings_reach_the_deck(self):
        deck = _deck(self.TSV)
        assert deck.sheet_config.present is True
        assert deck.sheet_config.reverse is True
        assert deck.sheet_config.align == "left"
        assert deck.sheet_config.for_field("QUESTION").size == 48
        assert deck.sheet_config.for_field("QUESTION").tts == "en_US"
        assert deck.sheet_config.for_field("ANSWER").color == "muted"

    def test_sheet_without_a_settings_row_keeps_every_row_as_data(self):
        deck = _deck("ID\tQUESTION\tANSWER\nQ1\tq\ta\nQ2\tq2\ta2")
        assert deck.sheet_config.present is False
        assert deck.total_table_lines == 2
        assert [n["ID"] for n in deck.notes] == ["Q1", "Q2"]

    def test_a_config_row_further_down_is_ordinary_data(self):
        # Only the row directly under the headers is the settings row; anything else
        # is a note, and silently swallowing it would lose the user's row.
        deck = _deck("ID\tQUESTION\tANSWER\nQ1\tq\ta\n#config\tx\ty")
        assert deck.sheet_config.present is False
        assert deck.total_table_lines == 2

    def test_typos_surface_in_the_debug_log(self):
        messages = []
        _deck(
            "ID\tQUESTION\tANSWER\n#config\tsize=huge\t\nQ1\tq\ta",
            debug_messages=messages,
        )
        joined = "\n".join(messages)
        assert "Settings row" in joined
        assert "size must be a number of pixels" in joined

    def test_row_numbers_in_the_log_still_match_the_sheet(self):
        messages = []
        _deck(
            "ID\tQUESTION\tANSWER\n#config\t\t\n\tq\ta",
            debug_messages=messages,
        )
        # Header is row 1, settings row 2, so the broken note is row 3.
        assert any("Row 3: invalid note (empty ID)" in m for m in messages)


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
