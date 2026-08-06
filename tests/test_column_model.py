#!/usr/bin/env python3
"""Tests for the free-form column model.

The whole point of this model is that the *sheet* decides the schema, so these
tests use headers that look nothing like the add-on's old fixed vocabulary.
"""

import pytest

from src import column_model as cm

HEADERS = [
    "ID",
    "SYNC",
    "SUBDECK 1",
    "SUBDECK 2",
    "TAGS",
    "Word",
    "Reading",
    "Meaning",
    "Example",
]

# Deliberately non-ASCII: headers, deck levels and values in another script, used by
# TestNonAsciiColumns below.
UNICODE_HEADERS = [
    "ID",
    "SYNC",
    "SUBDECK 1",
    "SUBDECK 2",
    "TAGS",
    "Hán tự",
    "Pinyin",
    "Nghĩa",
    "Ví dụ",
]


def _row(**overrides):
    row = {
        "ID": "4",
        "SYNC": "TRUE",
        "SUBDECK 1": "Unit 3",
        "SUBDECK 2": "Verbs",
        "TAGS": "vocab, verb",
        "Word": "postpone",
        "Reading": "post-PONE",
        "Meaning": "to move to a later time",
        "Example": "The meeting was postponed until tomorrow.",
    }
    row.update(overrides)
    return row


def _unicode_row(**overrides):
    row = {
        "ID": "4",
        "SYNC": "TRUE",
        "SUBDECK 1": "Bài 3",
        "SUBDECK 2": "Động từ",
        "TAGS": "hsk4, động từ",
        "Hán tự": "推迟",
        "Pinyin": "tuīchí",
        "Nghĩa": "hoãn lại",
        "Ví dụ": "会议推迟到明天。",
    }
    row.update(overrides)
    return row


@pytest.mark.unit
class TestPlanColumns:
    def test_content_columns_keep_sheet_order(self):
        plan = cm.plan_columns(HEADERS)
        assert plan.content_headers == ["Word", "Reading", "Meaning", "Example"]

    def test_reserved_columns_are_recognised(self):
        plan = cm.plan_columns(HEADERS)
        assert plan.id_header == "ID"
        assert plan.sync_header == "SYNC"
        assert plan.tags_header == "TAGS"
        assert plan.subdeck_headers == ["SUBDECK 1", "SUBDECK 2"]

    def test_note_type_fields_lead_with_id(self):
        plan = cm.plan_columns(HEADERS)
        assert plan.note_type_fields() == [
            "ID",
            "Word",
            "Reading",
            "Meaning",
            "Example",
        ]

    @pytest.mark.parametrize("header", ["id", "Id", " ID ", "﻿ID"])
    def test_reserved_match_is_case_and_whitespace_insensitive(self, header):
        plan = cm.plan_columns([header, "Front"])
        assert plan.has_id
        assert plan.content_headers == ["Front"]

    @pytest.mark.parametrize(
        "header,level",
        [("SUBDECK 1", 1), ("subdeck2", 2), ("Subdeck  10", 10), ("SUBDECK", None)],
    )
    def test_subdeck_level_parsing(self, header, level):
        assert cm.subdeck_level(header) == level

    def test_subdeck_order_follows_the_number_not_the_column_position(self):
        # Regression guard: dragging SUBDECK 2 left of SUBDECK 1 in the sheet must
        # not silently reorder everyone's deck hierarchy.
        plan = cm.plan_columns(["ID", "SUBDECK 2", "SUBDECK 1", "Front"])
        assert plan.subdeck_headers == ["SUBDECK 1", "SUBDECK 2"]

    def test_duplicate_headers_keep_the_first_and_are_reported(self):
        plan = cm.plan_columns(["ID", "Front", "Front", "Back"])
        assert plan.content_headers == ["Front", "Back"]
        assert plan.duplicates == ["Front"]

    def test_blank_headers_are_skipped(self):
        plan = cm.plan_columns(["ID", "", "   ", "Front"])
        assert plan.content_headers == ["Front"]

    def test_sheet_without_id_is_flagged(self):
        assert cm.plan_columns(["Front", "Back"]).has_id is False


@pytest.mark.unit
class TestSyncGate:
    @pytest.mark.parametrize("value", ["true", "TRUE", "1", "yes", "sim", "x", "✓"])
    def test_truthy_values(self, value):
        plan = cm.plan_columns(HEADERS)
        assert cm.row_is_marked_for_sync(_row(SYNC=value), plan) is True

    @pytest.mark.parametrize("value", ["false", "FALSE", "0", "no", "", "   "])
    def test_falsey_values(self, value):
        plan = cm.plan_columns(HEADERS)
        assert cm.row_is_marked_for_sync(_row(SYNC=value), plan) is False

    def test_sheet_without_sync_column_syncs_everything(self):
        # The old model treated a missing SYNC column as "nothing syncs", which
        # produced an empty deck with no visible reason.
        plan = cm.plan_columns(["ID", "Front", "Back"])
        assert cm.row_is_marked_for_sync({"ID": "1", "Front": "a"}, plan) is True


@pytest.mark.unit
class TestDeckPath:
    def test_levels_in_order(self):
        plan = cm.plan_columns(HEADERS)
        assert cm.deck_path(_row(), plan) == ["Unit 3", "Verbs"]

    def test_empty_levels_are_dropped(self):
        plan = cm.plan_columns(HEADERS)
        assert cm.deck_path(_row(**{"SUBDECK 1": ""}), plan) == ["Verbs"]

    def test_no_subdeck_columns_means_no_path(self):
        plan = cm.plan_columns(["ID", "Front"])
        assert cm.deck_path({"ID": "1", "Front": "a"}, plan) == []


@pytest.mark.unit
class TestTags:
    def test_comma_and_semicolon_separated(self):
        plan = cm.plan_columns(HEADERS)
        assert cm.tags_of(_row(TAGS="vocab, verb; formal"), plan) == [
            "vocab",
            "verb",
            "formal",
        ]

    def test_blank_and_missing_yield_nothing(self):
        plan = cm.plan_columns(HEADERS)
        assert cm.tags_of(_row(TAGS="  "), plan) == []
        assert cm.tags_of({"ID": "1"}, cm.plan_columns(["ID", "Front"])) == []


@pytest.mark.unit
class TestNonAsciiColumns:
    """Unicode coverage: the model never re-encodes or normalises sheet text."""

    def test_non_ascii_headers_become_fields_verbatim(self):
        # Unicode handling: a header in another script is the field name, unchanged.
        plan = cm.plan_columns(UNICODE_HEADERS)
        assert plan.content_headers == ["Hán tự", "Pinyin", "Nghĩa", "Ví dụ"]
        assert plan.note_type_fields() == [
            "ID",
            "Hán tự",
            "Pinyin",
            "Nghĩa",
            "Ví dụ",
        ]

    def test_non_ascii_headers_do_not_shadow_the_reserved_ones(self):
        # Unicode handling: case folding a multi-byte header must not accidentally
        # match ID/SYNC/SUBDECK/TAGS, nor drop the header from the plan.
        plan = cm.plan_columns(UNICODE_HEADERS)
        assert plan.id_header == "ID"
        assert plan.sync_header == "SYNC"
        assert plan.tags_header == "TAGS"
        assert plan.subdeck_headers == ["SUBDECK 1", "SUBDECK 2"]
        assert plan.duplicates == []

    def test_non_ascii_deck_levels_and_tags_survive(self):
        # Unicode handling: multi-byte deck levels and tag values round-trip intact.
        plan = cm.plan_columns(UNICODE_HEADERS)
        assert cm.deck_path(_unicode_row(), plan) == ["Bài 3", "Động từ"]
        assert cm.tags_of(_unicode_row(), plan) == ["hsk4", "động từ"]
