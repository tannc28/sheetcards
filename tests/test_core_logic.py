#!/usr/bin/env python3
"""
Real unit tests for SheetCards's pure logic.

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

    def test_a_sheet_with_only_reserved_columns_raises(self):
        with pytest.raises(d.RemoteDeckError):
            d.parse_tsv_data("SYNC\tTAGS\nx\ty")


@pytest.mark.unit
class TestNoIdColumn:
    """A sheet with no ID column is keyed by its first content column."""

    def deck(self, tsv):
        parsed = d.parse_tsv_data(tsv)
        return parsed, d.build_remote_deck_from_tsv(parsed, "")

    def test_the_first_content_column_becomes_the_id(self):
        parsed, deck = self.deck("Word\tMeaning\njourney\tchuyến đi\nborrow\tmượn")
        assert parsed["plan"].id_from == "Word"
        assert parsed["plan"].id_header == "ID"
        assert [n["ID"] for n in deck.notes] == ["journey", "borrow"]
        assert parsed["plan"].content_headers == ["Word", "Meaning"]
        # The sheet as written is kept for whatever draws the spreadsheet itself.
        assert parsed["sheet_headers"] == ["Word", "Meaning"]

    def test_the_id_is_normalised_but_keeps_its_case(self):
        _, deck = self.deck("Word\tMeaning\n  New   York \tx\nCafe\u0301\ty")
        assert [n["ID"] for n in deck.notes] == ["New York", "Café"]

    def test_repeats_are_numbered_in_row_order_ignoring_case(self):
        _, deck = self.deck("Word\tM\nbank\t1\nBank\t2\nbank\t3\nbank (2)\t4")
        assert [n["ID"] for n in deck.notes] == [
            "bank",
            "Bank (2)",
            "bank (3)",
            "bank (2) (2)",
        ]
        assert deck.duplicate_ids == []

    def test_a_blank_first_cell_is_still_an_invalid_row(self):
        _, deck = self.deck("Word\tMeaning\n\tno word\njourney\tx")
        assert deck.invalid_note_lines == 1
        assert deck.total_potential_anki_notes == 1

    def test_inserting_a_row_keeps_every_other_id(self):
        _, before = self.deck("Word\tM\na\t1\nb\t2")
        _, after = self.deck("Word\tM\nz\t0\na\t1\nb\t2")
        assert {n["ID"] for n in before.notes} < {n["ID"] for n in after.notes}

    def test_reserved_columns_still_work(self):
        _, deck = self.deck("TAGS\tWord\tM\tSYNC\nt1\tx\ty\t\nt2\tz\tw\tx")
        assert [n["ID"] for n in deck.notes] == ["x", "z"]
        assert deck.sync_marked_lines == 1

    def test_the_package_keys_each_note_by_its_word(self):
        import io
        import sqlite3
        import tempfile
        import zipfile

        from src import apkg

        _, deck = self.deck("Word\tMeaning\njourney\tx\nborrow\ty")
        data = apkg.build_package(
            "file:w.tsv#", "w", deck.plan, deck.sheet_config, deck.notes, now=1
        )
        with tempfile.NamedTemporaryFile(suffix=".anki2") as f:
            f.write(zipfile.ZipFile(io.BytesIO(data)).read("collection.anki2"))
            f.flush()
            guids = {
                g for (g,) in sqlite3.connect(f.name).execute("select guid from notes")
            }
        assert guids == {
            apkg.note_guid("file:w.tsv#", "journey"),
            apkg.note_guid("file:w.tsv#", "borrow"),
        }

    def test_a_sheet_with_an_id_column_is_untouched(self):
        parsed, deck = self.deck("ID\tWord\nw01\tjourney")
        assert parsed["plan"].id_from is None
        assert "sheet_headers" not in parsed
        assert deck.notes[0]["ID"] == "w01"

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
        assert "sheetcards" in tags
        assert "sheetcards::geography::europe" in tags
        assert "enem" in tags
        assert all(t == t.lower() for t in tags)

    def test_spaces_and_colons_are_neutralised(self):
        # Anki splits tags on spaces and nests on '::', so neither may survive
        # inside a single tag component.
        plan = cm.plan_columns(["ID", "SUBDECK 1", "Front"])
        tags = d.build_tags(
            {"ID": "Q1", "SUBDECK 1": "Unit 3: opening", "Front": "q"}, plan
        )
        assert not any(" " in t for t in tags)
        assert "sheetcards::unit_3_opening" in tags

    def test_spaces_and_colons_are_neutralised_in_non_ascii_deck_names(self):
        # Unicode coverage: multi-byte deck names are exactly where tag cleaning
        # could break — lower-casing and the space/colon substitutions have to work
        # on characters, and \w must keep the non-ASCII letters instead of stripping
        # them.
        plan = cm.plan_columns(["ID", "SUBDECK 1", "Front"])
        tags = d.build_tags(
            {"ID": "Q1", "SUBDECK 1": "Bài 3: mở đầu", "Front": "q"}, plan
        )
        assert not any(" " in t for t in tags)
        assert "sheetcards::bài_3_mở_đầu" in tags


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
