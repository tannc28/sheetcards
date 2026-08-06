#!/usr/bin/env python3
"""Tests for layout defaults and the templates generated from them."""

import pytest

from src import sync_config
from src.card_layout import FRONT_TEMPLATE_NAME
from src.card_layout import REVERSE_TEMPLATE_NAME
from src.card_layout import build_templates

FIELDS = ["Word", "Reading", "Meaning", "Example"]

# Deliberately non-ASCII, used by TestNonAsciiFields below.
UNICODE_FIELDS = ["Hán tự", "Pinyin", "Nghĩa", "Ví dụ"]


@pytest.mark.unit
class TestDefaultLayout:
    def test_first_column_is_the_prompt(self):
        layout = sync_config.default_layout_for(FIELDS)
        assert layout["front"] == ["Word"]
        assert layout["back"] == ["Reading", "Meaning", "Example"]

    def test_single_column_sheet_has_empty_back(self):
        layout = sync_config.default_layout_for(["Front"])
        assert layout["front"] == ["Front"]
        assert layout["back"] == []

    def test_no_columns_yields_the_bare_defaults(self):
        layout = sync_config.default_layout_for([])
        assert layout["front"] == [] and layout["back"] == []

    def test_defaults_cover_every_key_the_renderer_reads(self):
        # build_templates() reads these; a missing default would silently change how
        # every card looks the first time a deck is synced.
        for key in (
            "show_labels",
            "front_size",
            "back_size",
            "align",
            "reverse_card",
            "timer",
            "timer_position",
            "hand_edited",
        ):
            assert key in sync_config.DEFAULT_LAYOUT


@pytest.mark.unit
class TestCoerce:
    def test_new_sheet_column_is_added_to_the_back(self):
        stored = {"front": ["Word"], "back": ["Reading"]}
        layout = sync_config._coerce(stored, FIELDS)
        assert "Meaning" in layout["back"] and "Example" in layout["back"]

    def test_removed_sheet_column_stops_being_rendered(self):
        stored = {"front": ["Word"], "back": ["Reading", "Retired column"]}
        layout = sync_config._coerce(stored, FIELDS)
        assert "Retired column" not in layout["back"]

    def test_missing_keys_fall_back_to_defaults(self):
        layout = sync_config._coerce({"front": ["Word"]}, FIELDS)
        assert layout["align"] == sync_config.DEFAULT_LAYOUT["align"]


@pytest.mark.unit
class TestBuildTemplates:
    def test_single_template_by_default(self):
        tpls = build_templates(sync_config.default_layout_for(FIELDS))
        assert [t["name"] for t in tpls] == [FRONT_TEMPLATE_NAME]

    def test_front_field_is_referenced_and_guarded(self):
        tpls = build_templates(sync_config.default_layout_for(FIELDS))
        qfmt = tpls[0]["qfmt"]
        assert "{{Word}}" in qfmt
        assert "{{#Word}}" in qfmt and "{{/Word}}" in qfmt

    def test_back_reuses_the_front_side(self):
        tpls = build_templates(sync_config.default_layout_for(FIELDS))
        assert tpls[0]["afmt"].startswith("{{FrontSide}}")

    def test_reverse_card_adds_a_second_template_with_sides_swapped(self):
        layout = sync_config.default_layout_for(FIELDS)
        layout["reverse_card"] = True
        tpls = build_templates(layout)

        assert [t["name"] for t in tpls] == [
            FRONT_TEMPLATE_NAME,
            REVERSE_TEMPLATE_NAME,
        ]
        assert "{{Reading}}" in tpls[1]["qfmt"]
        assert "{{Word}}" in tpls[1]["afmt"]

    def test_cloze_layout_never_gets_a_reverse_template(self):
        # Anki only supports one template on a cloze note type.
        layout = sync_config.default_layout_for(FIELDS)
        layout["reverse_card"] = True
        assert len(build_templates(layout, is_cloze=True)) == 1

    def test_cloze_wraps_the_prompt_in_the_cloze_filter(self):
        tpls = build_templates(sync_config.default_layout_for(FIELDS), is_cloze=True)
        assert "{{cloze:Word}}" in tpls[0]["qfmt"]

    def test_labels_are_off_by_default_and_on_when_asked(self):
        layout = sync_config.default_layout_for(FIELDS)
        assert "s2a-label" not in build_templates(layout)[0]["afmt"]

        layout["show_labels"] = True
        assert "s2a-label" in build_templates(layout)[0]["afmt"]

    def test_timer_can_be_switched_off(self):
        layout = sync_config.default_layout_for(FIELDS)
        assert "sheets2anki-timer" in build_templates(layout)[0]["qfmt"]

        layout["timer"] = False
        assert "sheets2anki-timer" not in build_templates(layout)[0]["qfmt"]

    def test_sizes_and_alignment_reach_the_css(self):
        layout = sync_config.default_layout_for(FIELDS)
        layout.update(front_size=64, back_size=22, align="left")
        qfmt = build_templates(layout)[0]["qfmt"]
        assert "font-size: 64px" in qfmt
        assert "text-align: left" in qfmt

    def test_layout_with_only_back_fields_still_renders_a_prompt(self):
        # An empty front would make Anki refuse to generate the card.
        tpls = build_templates({"front": [], "back": ["Reading", "Meaning"]})
        assert "{{Reading}}" in tpls[0]["qfmt"]

    def test_cloze_back_also_references_the_cloze_filter(self):
        # Anki refuses to save a cloze note type unless {{cloze:Field}} appears on
        # BOTH sides; {{FrontSide}} does not satisfy it. Regression guard for a
        # sync that aborted with "Card template 1 ... has a problem".
        tpls = build_templates(sync_config.default_layout_for(FIELDS), is_cloze=True)
        assert "{{cloze:Word}}" in tpls[0]["qfmt"]
        assert "{{cloze:Word}}" in tpls[0]["afmt"]
        assert "{{FrontSide}}" not in tpls[0]["afmt"]

    def test_non_cloze_back_still_reuses_the_front_side(self):
        tpls = build_templates(sync_config.default_layout_for(FIELDS))
        assert tpls[0]["afmt"].startswith("{{FrontSide}}")


@pytest.mark.unit
class TestNonAsciiFields:
    """Unicode coverage: Anki matches ``{{Field}}`` on the exact field name, so a
    field copied from a non-ASCII header has to reach the template unaltered."""

    def test_non_ascii_field_names_reach_the_template_verbatim(self):
        # Unicode handling: no escaping, no normalising of the field name.
        tpls = build_templates(sync_config.default_layout_for(UNICODE_FIELDS))
        qfmt = tpls[0]["qfmt"]
        assert "{{Hán tự}}" in qfmt
        assert "{{#Hán tự}}" in qfmt and "{{/Hán tự}}" in qfmt
        assert "{{Nghĩa}}" in tpls[0]["afmt"]

    def test_non_ascii_cloze_field_is_wrapped_on_both_sides(self):
        # Unicode handling: the cloze filter has to name the field exactly, or Anki
        # refuses to save the note type.
        tpls = build_templates(
            sync_config.default_layout_for(UNICODE_FIELDS), is_cloze=True
        )
        assert "{{cloze:Hán tự}}" in tpls[0]["qfmt"]
        assert "{{cloze:Hán tự}}" in tpls[0]["afmt"]

    def test_removed_non_ascii_column_stops_being_rendered(self):
        # Unicode handling: dropping a column compares multi-byte names, so a stale
        # non-ASCII entry must still be recognised and left out.
        stored = {"front": ["Hán tự"], "back": ["Pinyin", "Cột đã xoá"]}
        layout = sync_config._coerce(stored, UNICODE_FIELDS)
        assert "Cột đã xoá" not in layout["back"]
        assert "Nghĩa" in layout["back"] and "Ví dụ" in layout["back"]
