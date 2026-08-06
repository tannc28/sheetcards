#!/usr/bin/env python3
"""
Real unit tests for Sheets2Anki's pure logic.

These import and exercise the ACTUAL ``src`` modules (see conftest for the Anki
import-mocking). They also lock in the behaviour of several recent correctness/security
fixes: multi-line TSV cells, duplicate-ID detection, BOM-tolerant required-header checks,
and the SSRF host guard on downloads.
"""

import pytest

from src import column_model as cm
from src import data_processor as d
from src import utils as u

# =============================================================================
# TSV PARSING
# =============================================================================


@pytest.mark.unit
class TestTsvParsing:
    def test_basic_parse(self):
        parsed = d.parse_tsv_data("ID\tQUESTION\tANSWER\nQ1\tq\ta\nQ2\tq2\ta2")
        assert parsed["headers"] == ["ID", "QUESTION", "ANSWER"]
        assert len(parsed["rows"]) == 2
        assert parsed["rows"][0] == ["Q1", "q", "a"]

    def test_multiline_quoted_cell_is_preserved(self):
        """Regression: a quoted cell with an embedded newline must keep the newline
        (it used to be flattened because the text was split on '\\n' before csv)."""
        tsv = 'ID\tQUESTION\tANSWER\nQ1\t"line one\nline two"\tA1\nQ2\tb\tB'
        parsed = d.parse_tsv_data(tsv)
        assert parsed["rows"][0][1] == "line one\nline two"
        # The embedded newline must NOT create a spurious extra row.
        assert len(parsed["rows"]) == 2

    def test_missing_required_headers_raise(self):
        with pytest.raises(d.RemoteDeckError):
            d.parse_tsv_data("FOO\tBAR\nx\ty")

    def test_empty_input_raises(self):
        with pytest.raises(d.RemoteDeckError):
            d.parse_tsv_data("   \n  ")

    def test_short_rows_are_padded(self):
        # A row with fewer columns than the header should not raise.
        parsed = d.parse_tsv_data("ID\tQUESTION\tANSWER\nQ1\tonlyq")
        assert parsed["rows"][0] == ["Q1", "onlyq"]


# =============================================================================
# CLOZE DETECTION
# =============================================================================


@pytest.mark.unit
class TestCloze:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("{{c1::Paris}}", True),
            ("The {{c2::capital}} is here", True),
            ("no cloze here", False),
            ("", False),
            ("{{notcloze}}", False),
        ],
    )
    def test_has_cloze_deletion(self, text, expected):
        assert d.has_cloze_deletion(text) is expected


# =============================================================================
# REMOTE DECK BUILD  (metrics + duplicate detection)
# =============================================================================


def _build(tsv, **kw):
    parsed = d.parse_tsv_data(tsv)
    return d.build_remote_deck_from_tsv(
        parsed, "https://docs.google.com/spreadsheets/d/ABC/edit", **kw
    )


@pytest.mark.unit
class TestRemoteDeckBuild:
    def test_valid_note_lines_counts_filled_ids(self):
        tsv = "ID\tQUESTION\tANSWER\tSYNC\nQ1\ta\tb\ttrue\nQ2\tc\td\tfalse\n\t\t\t"
        deck = _build(tsv)
        # Two rows have a filled ID; the all-empty row is a ghost row.
        assert deck.valid_note_lines == 2

    def test_duplicate_ids_detected(self):
        """Regression (H7): duplicate non-empty IDs are reported, not silently merged."""
        tsv = (
            "ID\tQUESTION\tANSWER\tSYNC\nQ1\ta\tb\ttrue\nQ1\tc\td\ttrue\nQ2\te\tf\ttrue"
        )
        deck = _build(tsv)
        assert deck.duplicate_ids == ["Q1"]

    def test_no_false_positive_duplicates(self):
        tsv = "ID\tQUESTION\tANSWER\tSYNC\nQ1\ta\tb\ttrue\nQ2\tc\td\ttrue"
        deck = _build(tsv)
        assert deck.duplicate_ids == []

    def test_empty_id_rows_do_not_count_as_duplicates(self):
        tsv = "ID\tQUESTION\tANSWER\tSYNC\nQ1\ta\tb\ttrue\n\tc\td\ttrue\n\te\tf\ttrue"
        deck = _build(tsv)
        assert deck.duplicate_ids == []


# =============================================================================
# HIERARCHICAL TAGS
# =============================================================================


@pytest.mark.unit
class TestTags:
    def test_deck_path_becomes_a_nested_tag(self):
        plan = cm.plan_columns(["ID", "SUBDECK 1", "SUBDECK 2", "TAGS", "Front"])
        tags = d.build_tags(
            {
                "ID": "Q1",
                "SUBDECK 1": "Geography",
                "SUBDECK 2": "Europe",
                "TAGS": "ENEM",
                "Front": "q",
            },
            plan,
        )
        assert "sheets2anki" in tags
        assert "sheets2anki::geography::europe" in tags
        assert "enem" in tags
        assert all(t == t.lower() for t in tags)

    def test_spaces_and_colons_are_neutralised(self):
        # Anki splits tags on spaces and nests on '::', so neither may survive
        # inside a single tag component.
        plan = cm.plan_columns(["ID", "SUBDECK 1", "Front"])
        tags = d.build_tags(
            {"ID": "Q1", "SUBDECK 1": "Bài 3: mở đầu", "Front": "q"}, plan
        )
        assert not any(" " in t for t in tags)
        assert "sheets2anki::bài_3_mở_đầu" in tags


# =============================================================================
# URL HANDLING
# =============================================================================


@pytest.mark.unit
class TestUrls:
    def test_convert_edit_url_to_tsv(self):
        out = u.convert_edit_url_to_tsv(
            "https://docs.google.com/spreadsheets/d/ABC123/edit?usp=sharing"
        )
        assert out == "https://docs.google.com/spreadsheets/d/ABC123/export?format=tsv"

    def test_get_spreadsheet_id_from_url(self):
        assert (
            u.get_spreadsheet_id_from_url(
                "https://docs.google.com/spreadsheets/d/ABC123/edit"
            )
            == "ABC123"
        )

    def test_convert_rejects_non_google(self):
        with pytest.raises(ValueError):
            u.convert_edit_url_to_tsv(
                "https://evil.example.com/spreadsheets/d/ABC/edit"
            )


# =============================================================================
# SSRF GUARD ON DOWNLOAD  (raises before any network access)
# =============================================================================


@pytest.mark.unit
class TestDownloadHostGuard:
    @pytest.mark.parametrize(
        "url",
        [
            "http://169.254.169.254/latest/meta-data/export?format=tsv",
            "http://localhost:8080/x/export?format=tsv",
            "http://internal.example.com/export?format=tsv",
        ],
    )
    def test_rejects_non_google_host(self, url):
        with pytest.raises(d.RemoteDeckError):
            d.download_tsv_data(url)
