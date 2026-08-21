#!/usr/bin/env python3
"""Tests for the card templates generated from a sheet's columns + settings row."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.card_layout import FRONT_TEMPLATE_NAME
from src.card_layout import REVERSE_TEMPLATE_NAME
from src.card_layout import build_templates
from src.card_layout import split_sides
from src.column_model import plan_columns
from src.sheet_config import THEMES
from src.sheet_config import SheetConfig
from src.sheet_config import parse_config_row

FIELDS = ["Word", "Reading", "Meaning", "Example"]

# Deliberately non-ASCII, used by TestNonAsciiFields below.
UNICODE_FIELDS = ["Hán tự", "Pinyin", "Nghĩa", "Ví dụ"]


def _plan(fields=FIELDS):
    """A plan for a sheet whose content columns are ``fields``."""
    return plan_columns(["ID", "SYNC"] + list(fields))


def _config(plan, cells=None, deck=""):
    """The settings row a user would type, parsed exactly as a sync would parse it.

    Args:
        plan: the sheet's ColumnPlan
        cells (dict): header → the directives written in that column's cell
        deck (str): the directives written after the ``#config`` marker itself
    """
    row = {plan.id_header: ("#config " + deck).strip()}
    row.update(cells or {})
    return parse_config_row(row, plan)


def _both(template):
    return template["qfmt"] + template["afmt"]


@pytest.mark.unit
class TestPlacement:
    def test_first_column_is_the_prompt_and_the_rest_the_answer(self):
        front, back = split_sides(_plan(), SheetConfig())
        assert front == ["Word"]
        assert back == ["Reading", "Meaning", "Example"]

    def test_sheet_order_is_the_card_order(self):
        plan = plan_columns(["ID", "Meaning", "Word"])
        front, back = split_sides(plan, SheetConfig())
        assert front == ["Meaning"] and back == ["Word"]

    def test_side_overrides_the_default_placement(self):
        plan = _plan()
        config = _config(plan, {"Word": "side=back", "Meaning": "side=front"})
        front, back = split_sides(plan, config)
        assert front == ["Meaning"]
        assert back == ["Word", "Reading", "Example"]

    def test_hidden_field_is_rendered_nowhere(self):
        plan = _plan()
        config = _config(plan, {"Meaning": "side=hide"})
        front, back = split_sides(plan, config)
        assert "Meaning" not in front and "Meaning" not in back

        for template in build_templates(plan, config):
            assert "Meaning" not in _both(template)

    def test_empty_front_promotes_the_first_visible_back_field(self):
        # An empty front would make Anki refuse to generate the card.
        plan = _plan()
        config = _config(plan, {"Word": "side=hide"})
        front, _ = split_sides(plan, config)
        assert front == ["Reading"]
        assert "{{Reading}}" in build_templates(plan, config)[0]["qfmt"]

    def test_every_column_pushed_to_the_back_still_leaves_a_prompt(self):
        plan = _plan(["Reading", "Meaning"])
        config = _config(plan, {"Reading": "side=back", "Meaning": "side=back"})
        front, back = split_sides(plan, config)
        assert front == ["Reading"] and back == ["Meaning"]

    def test_only_content_columns_are_rendered(self):
        # ID/SYNC/TAGS/SUBDECK carry meaning, not content: they must never leak onto
        # a card just because the sheet has them.
        plan = plan_columns(["ID", "SYNC", "TAGS", "SUBDECK 1", "Word"])
        for template in build_templates(plan, SheetConfig()):
            rendered = _both(template)
            assert "{{SYNC}}" not in rendered
            assert "{{TAGS}}" not in rendered
            assert "{{SUBDECK 1}}" not in rendered
            assert "{{Word}}" in rendered


@pytest.mark.unit
class TestFieldMarkup:
    def test_field_is_referenced_and_guarded(self):
        qfmt = build_templates(_plan(), SheetConfig())[0]["qfmt"]
        assert "{{Word}}" in qfmt
        assert "{{#Word}}" in qfmt and "{{/Word}}" in qfmt

    def test_size_bold_italic_and_align_become_inline_css(self):
        plan = _plan()
        config = _config(plan, {"Word": "size=64; bold; italic; align=left"})
        qfmt = build_templates(plan, config)[0]["qfmt"]
        assert "font-size: 64px" in qfmt
        assert "font-weight: 700" in qfmt
        assert "font-style: italic" in qfmt
        assert "text-align: left" in qfmt

    def test_unstyled_field_carries_no_style_attribute(self):
        qfmt = build_templates(_plan(), SheetConfig())[0]["qfmt"]
        assert "style=" not in qfmt.split("</style>")[1]
        assert '<div class="sc-front" data-sc-col="Word">{{Word}}</div>' in qfmt

    def test_every_field_says_which_column_it_came_from(self):
        """Anki's own classes say only which side a block is on.

        Without this nothing in the finished card connects a piece of it back to
        the sheet — so the preview cannot point at a field, and a note type's CSS
        cannot target one column.
        """
        both = _both(build_templates(_plan(), SheetConfig())[0])
        for name in FIELDS:
            assert f'data-sc-col="{name}"' in both

    def test_the_column_name_is_escaped_in_the_attribute(self):
        plan = _plan(['A "quoted" & <odd> name'])
        qfmt = build_templates(plan, SheetConfig())[0]["qfmt"]
        assert 'data-sc-col="A &quot;quoted&quot; &amp; &lt;odd&gt; name"' in qfmt

    def test_deck_alignment_reaches_the_css(self):
        plan = _plan()
        qfmt = build_templates(plan, _config(plan, deck="align=left"))[0]["qfmt"]
        assert "text-align: left" in qfmt

    def test_theme_colour_resolves_to_a_custom_property(self):
        plan = _plan()
        config = _config(plan, {"Reading": "color=muted", "Meaning": "color=accent"})
        afmt = build_templates(plan, config)[0]["afmt"]
        assert "color: var(--sc-muted)" in afmt
        assert "color: var(--sc-accent)" in afmt

    def test_theme_colours_are_defined_for_both_themes(self):
        # A single value would leave one theme unreadable, which is the whole point
        # of the named colours: the night_mode override has to be there too.
        qfmt = build_templates(_plan(), SheetConfig())[0]["qfmt"]
        for name in ("--sc-muted", "--sc-accent"):
            assert f":root {{ {name}" in qfmt or f"; {name}" in qfmt
            assert qfmt.count(name) >= 2
        night = qfmt.split(".night_mode {")[1].split("}")[0]
        assert "--sc-muted:" in night and "--sc-accent:" in night

    def test_no_theme_leaves_the_card_the_colours_anki_gave_it(self):
        qfmt = build_templates(_plan(), SheetConfig())[0]["qfmt"]
        assert ".card {" not in qfmt

    def test_a_theme_paints_the_card_in_both_modes(self):
        plan = _plan()
        qfmt = build_templates(plan, _config(plan, deck="theme=sakura"))[0]["qfmt"]
        light = THEMES["sakura"]["light"]
        night = THEMES["sakura"]["night"]
        card = qfmt.split(".card {")[1].split("}")[0]
        night_card = qfmt.split(".card.night_mode {")[1].split("}")[0]
        assert f"background-color: {light['bg']}" in card
        assert f"color: {light['fg']}" in card
        assert f"background-color: {night['bg']}" in night_card
        assert f"color: {night['fg']}" in night_card

    def test_a_seasonal_theme_strews_the_card_with_its_flowers(self):
        # Named after a season, so the pattern is the point rather than decoration
        # on top of it — and it travels in the stylesheet, so no card ever fetches
        # it and nothing lands in collection.media.
        plan = _plan()
        qfmt = build_templates(plan, _config(plan, deck="theme=sakura"))[0]["qfmt"]
        assert 'background-image: url("data:image/svg+xml,' in qfmt
        assert "http://www.w3.org/2000/svg" in qfmt
        # The colour survives underneath, so a client that refuses the data URI is
        # left with the theme rather than with whatever is behind the card.
        card = qfmt.split(".card {")[1].split("}")[0]
        assert "background-color:" in card

    def test_the_flowers_are_the_themes_own_colours(self):
        plan = _plan()
        qfmt = build_templates(plan, _config(plan, deck="theme=sakura"))[0]["qfmt"]
        for variant, selector in (
            ("light", ".card {"),
            ("night", ".card.night_mode {"),
        ):
            colours = THEMES["sakura"][variant]
            block = qfmt.split(selector)[1].split("}")[0]
            assert colours["petal"].replace("#", "%23") in block
            assert colours["heart"].replace("#", "%23") in block

    def test_a_theme_swaps_what_the_named_colours_mean(self):
        # `color=accent` follows the sheet's theme rather than staying Google blue,
        # which is the only way a themed card reads as one palette.
        plan = _plan()
        config = _config(plan, {"Reading": "color=accent"}, deck="theme=sakura")
        qfmt = build_templates(plan, config)[0]["qfmt"]
        assert f"--sc-accent: {THEMES['sakura']['light']['accent']}" in qfmt
        assert f"--sc-accent: {THEMES['sakura']['night']['accent']}" in qfmt
        assert "#1a73e8" not in qfmt

    def test_a_signed_theme_marks_the_corner_of_its_cards(self):
        plan = _plan()
        qfmt = build_templates(plan, _config(plan, deck="theme=sakura"))[0]["qfmt"]
        mark = qfmt.split(".card::after {")[1].split("}")[0]
        assert f'content: "{THEMES["sakura"]["sign"]}"' in mark
        # Drawn rather than typed: U+2665 is a colour emoji on some clients and a
        # missing glyph on others, so the heart is a path in the palette's colour.
        assert "♥" not in qfmt
        for variant, selector in (
            ("light", ".card::after {"),
            ("night", ".card.night_mode::after {"),
        ):
            block = qfmt.split(selector)[1].split("}")[0]
            assert THEMES["sakura"][variant]["heart"].replace("#", "%23") in block

    def test_an_unthemed_sheet_has_no_corner_mark(self):
        assert "::after" not in build_templates(_plan(), SheetConfig())[0]["qfmt"]

    def test_an_unknown_theme_is_named_and_the_card_is_left_alone(self):
        plan = _plan()
        config = _config(plan, deck="theme=neon")
        assert config.theme is None
        assert any("neon" in w for w in config.warnings)
        assert ".card {" not in build_templates(plan, config)[0]["qfmt"]

    def test_literal_colour_is_emitted_as_written(self):
        plan = _plan()
        config = _config(plan, {"Word": "color=#ff0000", "Reading": "color=crimson"})
        templates = build_templates(plan, config)
        assert "color: #ff0000" in templates[0]["qfmt"]
        assert "color: crimson" in templates[0]["afmt"]

    def test_label_renders_as_a_caption_above_the_field(self):
        plan = _plan()
        config = _config(plan, {"Reading": "label=Pronunciation"})
        afmt = build_templates(plan, config)[0]["afmt"]
        assert '<div class="sc-label">Pronunciation</div>{{Reading}}' in afmt

    def test_no_label_means_no_caption_markup(self):
        assert "sc-label" not in build_templates(_plan(), SheetConfig())[0]["afmt"]

    def test_label_text_is_escaped(self):
        plan = _plan()
        config = _config(plan, {"Reading": "label=A & <b>B</b>"})
        afmt = build_templates(plan, config)[0]["afmt"]
        assert "A &amp; &lt;b&gt;B&lt;/b&gt;" in afmt

    def test_templates_are_pure_markup_unless_a_column_asked_for_a_box(self):
        """`draw` is the one directive that puts code in a card.

        Everything else is markup and Anki's own filters, and it stays that way:
        a sheet that did not ask for a writing box gets a template with nothing to
        execute, so nothing it renders can depend on the network or on scripts
        being allowed.
        """
        plan = _plan()
        config = _config(plan, {"Word": "size=48"}, deck="reverse")
        for template in build_templates(plan, config):
            assert "<script" not in _both(template)


@pytest.mark.unit
class TestFilters:
    def test_hint_uses_ankis_own_filter(self):
        plan = _plan()
        config = _config(plan, {"Meaning": "hint"})
        afmt = build_templates(plan, config)[0]["afmt"]
        assert "{{hint:Meaning}}" in afmt
        assert "{{#Meaning}}" in afmt and "{{/Meaning}}" in afmt

    def test_furigana_uses_ankis_own_filter(self):
        plan = _plan()
        config = _config(plan, {"Reading": "furigana"})
        assert "{{furigana:Reading}}" in build_templates(plan, config)[0]["afmt"]

    def test_plain_field_uses_no_filter(self):
        afmt = build_templates(_plan(), SheetConfig())[0]["afmt"]
        assert "{{Reading}}" in afmt
        assert "hint:" not in afmt and "furigana:" not in afmt


@pytest.mark.unit
class TestTextToSpeech:
    def test_tts_tag_names_the_language_first(self):
        plan = _plan()
        config = _config(plan, {"Word": "tts=zh_CN"})
        assert "{{tts zh_CN:Word}}" in build_templates(plan, config)[0]["qfmt"]

    def test_tts_tag_is_guarded_like_the_field(self):
        plan = _plan()
        config = _config(plan, {"Word": "tts=zh_CN"})
        qfmt = build_templates(plan, config)[0]["qfmt"]
        assert "{{#Word}}{{tts zh_CN:Word}}{{/Word}}" in qfmt

    def test_a_furigana_column_is_spoken_through_kana(self):
        """Otherwise the voice reads the brackets, and the word twice.

        Anki hands the voice the field's *text*, and the text of a furigana cell is
        `日本語[にほんご]`. Checked against a real collection: the plain tag speaks
        `日本語[にほんご]`, `kana:` speaks `にほんご`. A cell with no brackets goes
        through the filter unchanged, so a half-annotated column still works.
        """
        plan = _plan()
        config = _config(plan, {"Word": "furigana; tts=ja_JP"})
        qfmt = build_templates(plan, config)[0]["qfmt"]
        assert "{{tts ja_JP:kana:Word}}" in qfmt
        assert "{{tts ja_JP:Word}}" not in qfmt
        # The guard is still on the field, not on the filtered form of it.
        assert "{{#Word}}{{tts ja_JP:kana:Word}}{{/Word}}" in qfmt

    def test_kana_is_only_for_the_column_that_asked_for_furigana(self):
        plan = _plan()
        config = _config(plan, {"Word": "tts=zh_CN", "Reading": "furigana; tts=ja_JP"})
        qfmt = (
            build_templates(plan, config)[0]["qfmt"]
            + build_templates(plan, config)[0]["afmt"]
        )
        assert "{{tts zh_CN:Word}}" in qfmt
        assert "{{tts ja_JP:kana:Reading}}" in qfmt

    def test_a_furigana_column_spoken_but_not_shown_is_filtered_too(self):
        # `side=hide` + `tts` is heard without being read — and what is heard has
        # to be the reading, not the brackets around it.
        plan = _plan()
        config = _config(plan, {"Word": "side=hide; furigana; tts=ja_JP"})
        template = build_templates(plan, config)[0]
        assert "{{tts ja_JP:kana:Word}}" in _both(template)

    def test_voices_are_listed_comma_separated(self):
        plan = _plan()
        config = _config(plan, {"Word": "tts=zh_CN; voices=Ting-Ting,Sin-ji"})
        qfmt = build_templates(plan, config)[0]["qfmt"]
        assert "{{tts zh_CN voices=Ting-Ting,Sin-ji:Word}}" in qfmt

    def test_field_speed_is_emitted(self):
        plan = _plan()
        config = _config(plan, {"Word": "tts=en_US; speed=1.5"})
        assert (
            "{{tts en_US speed=1.5:Word}}" in build_templates(plan, config)[0]["qfmt"]
        )

    def test_deck_speed_applies_when_the_field_names_none(self):
        plan = _plan()
        config = _config(plan, {"Word": "tts=en_US"}, deck="speed=0.8")
        assert (
            "{{tts en_US speed=0.8:Word}}" in build_templates(plan, config)[0]["qfmt"]
        )

    def test_field_speed_beats_the_deck_speed(self):
        plan = _plan()
        config = _config(plan, {"Word": "tts=en_US; speed=1.5"}, deck="speed=0.8")
        qfmt = build_templates(plan, config)[0]["qfmt"]
        assert "{{tts en_US speed=1.5:Word}}" in qfmt
        assert "speed=0.8" not in qfmt

    def test_voices_and_speed_together(self):
        plan = _plan()
        config = _config(plan, {"Word": "tts=ja_JP; voices=Kyoko; speed=1.25"})
        qfmt = build_templates(plan, config)[0]["qfmt"]
        assert "{{tts ja_JP voices=Kyoko speed=1.25:Word}}" in qfmt

    def test_no_tts_means_no_tag(self):
        plan = _plan()
        # A speed on its own has nothing to speak: it must not conjure up a tag.
        config = _config(plan, {"Word": "speed=1.5"}, deck="speed=1.5")
        assert "{{tts" not in build_templates(plan, config)[0]["qfmt"]

    def test_tts_follows_the_field_to_the_other_side(self):
        plan = _plan()
        config = _config(plan, {"Reading": "tts=zh_CN"})
        assert "{{tts zh_CN:Reading}}" in build_templates(plan, config)[0]["afmt"]


@pytest.mark.unit
class TestTemplates:
    def test_single_template_by_default(self):
        templates = build_templates(_plan(), SheetConfig())
        assert [t["name"] for t in templates] == [FRONT_TEMPLATE_NAME]

    def test_back_reuses_the_front_side(self):
        assert build_templates(_plan(), SheetConfig())[0]["afmt"].startswith(
            "{{FrontSide}}"
        )

    def test_reverse_adds_a_second_template_with_sides_swapped(self):
        plan = _plan()
        templates = build_templates(plan, _config(plan, deck="reverse"))

        assert [t["name"] for t in templates] == [
            FRONT_TEMPLATE_NAME,
            REVERSE_TEMPLATE_NAME,
        ]
        assert "{{Reading}}" in templates[1]["qfmt"]
        assert "{{Word}}" in templates[1]["afmt"]

    def test_reverse_keeps_each_fields_own_styling(self):
        plan = _plan()
        config = _config(plan, {"Word": "size=48"}, deck="reverse")
        assert "font-size: 48px" in build_templates(plan, config)[1]["afmt"]

    def test_no_reverse_when_a_side_would_be_empty(self):
        plan = _plan(["Word"])
        assert len(build_templates(plan, _config(plan, deck="reverse"))) == 1

    def test_cloze_never_gets_a_reverse_template(self):
        # Anki only supports one template on a cloze note type.
        plan = _plan()
        config = _config(plan, deck="reverse")
        assert len(build_templates(plan, config, is_cloze=True)) == 1

    def test_cloze_wraps_the_declared_column_on_both_sides(self):
        # Anki refuses to save a cloze note type unless {{cloze:Field}} appears on
        # BOTH sides; {{FrontSide}} does not satisfy it. Regression guard for a
        # sync that aborted with "Card template 1 ... has a problem".
        plan = _plan()
        config = _config(plan, {"Word": "cloze"})
        templates = build_templates(plan, config, is_cloze=True)
        assert "{{cloze:Word}}" in templates[0]["qfmt"]
        assert "{{cloze:Word}}" in templates[0]["afmt"]
        assert "{{FrontSide}}" not in templates[0]["afmt"]

    def test_only_the_declared_column_goes_through_the_filter(self):
        """The others must stay plain.

        Anki renders a clozed field holding no deletion as nothing at all, so
        wrapping every column would blank the whole card except the sentence.
        """
        plan = _plan()
        config = _config(plan, {"Example": "cloze"})
        both = _both(build_templates(plan, config, is_cloze=True)[0])
        assert "{{cloze:Example}}" in both
        for other in ("Word", "Reading", "Meaning"):
            assert f"{{{{cloze:{other}}}}}" not in both
            assert f"{{{{{other}}}}}" in both

    def test_the_clozed_column_is_the_prompt_wherever_it_sits(self):
        """Its deletions are the question, so column order does not get a vote."""
        plan = _plan()
        config = _config(plan, {"Meaning": "cloze"})
        front, _ = split_sides(plan, config)
        assert front[0] == "Meaning" or "Meaning" in front
        assert (
            "{{cloze:Meaning}}"
            in build_templates(plan, config, is_cloze=True)[0]["qfmt"]
        )

    def test_cloze_prompt_keeps_the_filter_even_with_hint_asked_for(self):
        # hint: would replace cloze: and leave nothing to reveal.
        plan = _plan()
        config = _config(plan, {"Word": "cloze; hint"})
        templates = build_templates(plan, config, is_cloze=True)
        assert "{{cloze:Word}}" in templates[0]["qfmt"]
        assert "{{cloze:Word}}" in templates[0]["afmt"]

    def test_two_columns_cannot_both_be_the_cloze_column(self):
        plan = _plan()
        config = _config(plan, {"Word": "cloze", "Meaning": "cloze"})
        assert config.cloze_field == "Word"
        assert any("only one column" in w for w in config.warnings)

    def test_sheet_with_a_single_column_still_renders(self):
        plan = _plan(["Word"])
        templates = build_templates(plan, SheetConfig())
        assert "{{Word}}" in templates[0]["qfmt"]
        assert len(templates) == 1


@pytest.mark.unit
class TestNonAsciiFields:
    """Unicode coverage: Anki matches ``{{Field}}`` on the exact field name, so a
    field copied from a non-ASCII header has to reach the template unaltered."""

    def test_non_ascii_field_names_reach_the_template_verbatim(self):
        # Unicode handling: no escaping, no normalising of the field name.
        templates = build_templates(_plan(UNICODE_FIELDS), SheetConfig())
        qfmt = templates[0]["qfmt"]
        assert "{{Hán tự}}" in qfmt
        assert "{{#Hán tự}}" in qfmt and "{{/Hán tự}}" in qfmt
        assert "{{Nghĩa}}" in templates[0]["afmt"]

    def test_non_ascii_cloze_field_is_wrapped_on_both_sides(self):
        # Unicode handling: the cloze filter has to name the field exactly, or Anki
        # refuses to save the note type.
        plan = _plan(UNICODE_FIELDS)
        config = _config(plan, {"Hán tự": "cloze"})
        templates = build_templates(plan, config, is_cloze=True)
        assert "{{cloze:Hán tự}}" in templates[0]["qfmt"]
        assert "{{cloze:Hán tự}}" in templates[0]["afmt"]

    def test_settings_address_a_non_ascii_column(self):
        # Unicode handling: the settings row is keyed by the header as written, so a
        # multi-byte name has to match the column it configures.
        plan = _plan(UNICODE_FIELDS)
        config = _config(plan, {"Nghĩa": "size=22; color=muted", "Ví dụ": "side=hide"})
        afmt = build_templates(plan, config)[0]["afmt"]
        assert "font-size: 22px" in afmt and "color: var(--sc-muted)" in afmt
        assert "Ví dụ" not in afmt


@pytest.mark.unit
class TestMediaColumns:
    """A media column holds a URL, which is wrapped rather than printed."""

    def _cfg(self, cell):
        from src.column_model import plan_columns
        from src.sheet_config import parse_config_row

        plan = plan_columns(["ID", "Word", "Link"])
        return plan, parse_config_row({"ID": "#config", "Link": cell}, plan)

    @pytest.mark.parametrize(
        "cell,tag",
        [
            ("image", "<img"),
            ("audio", "<audio"),
            ("video", "<iframe"),
        ],
    )
    def test_each_kind_wraps_the_field_in_its_element(self, cell, tag):
        plan, sheet_config = self._cfg(cell)
        afmt = build_templates(plan, sheet_config)[0]["afmt"]
        # A video frame reaches the field through the player page, which is what
        # gives the request an origin — see TestFramedPlayerOnMobile.
        assert f"{tag} src=" in afmt
        assert "{{Link}}" in afmt

    def test_sound_can_always_be_replayed(self):
        # A sound the learner cannot replay is worse than no sound. Video gets its
        # controls from the framed player instead of from an attribute here.
        plan, sheet_config = self._cfg("audio")
        assert "controls" in build_templates(plan, sheet_config)[0]["afmt"]

    def test_size_caps_the_width_not_the_font(self):
        plan, sheet_config = self._cfg("image; size=320")
        afmt = build_templates(plan, sheet_config)[0]["afmt"]
        assert "max-width: 320px" in afmt
        assert "font-size: 320px" not in afmt

    def test_size_may_be_written_before_the_kind(self):
        _, sheet_config = self._cfg("size=480; video")
        assert sheet_config.for_field("Link").size == 480

    def test_media_width_allows_sizes_a_font_size_would_reject(self):
        _, sheet_config = self._cfg("image; size=320")
        assert sheet_config.for_field("Link").size == 320
        assert sheet_config.warnings == []

    def test_a_text_column_still_rejects_a_font_size_of_320(self):
        _, sheet_config = self._cfg("size=320")
        assert sheet_config.for_field("Link").size is None
        assert any("font size" in w for w in sheet_config.warnings)

    def test_two_kinds_on_one_column_keeps_the_first_and_warns(self):
        _, sheet_config = self._cfg("image; video")
        assert sheet_config.for_field("Link").media == "image"
        assert any("one kind of media" in w for w in sheet_config.warnings)

    def test_tts_is_dropped_from_a_media_column(self):
        # Speaking a media column would read the URL out loud.
        _, sheet_config = self._cfg("image; tts=zh_CN")
        cfg = sheet_config.for_field("Link")
        assert cfg.tts is None and cfg.voices == []
        assert any("read the URL aloud" in w for w in sheet_config.warnings)

    def test_hint_really_hides_media_behind_a_disclosure(self):
        # Regression: this used to assert only `{{#Link}}`, which the field guard
        # always supplies — so it passed while `hint` did nothing at all. Anki's
        # {{hint:}} reveals the field's text, i.e. the URL, so media needs its own
        # disclosure element.
        plan, sheet_config = self._cfg("image; hint")
        afmt = build_templates(plan, sheet_config)[0]["afmt"]

        assert "<details" in afmt and "<summary>" in afmt
        assert afmt.index("<summary>") < afmt.index("<img")
        assert "{{hint:Link}}" not in afmt

    def test_hint_summary_uses_the_label_when_one_is_given(self):
        plan, sheet_config = self._cfg("image; hint; label=Picture")
        assert (
            "<summary>Picture</summary>"
            in build_templates(plan, sheet_config)[0]["afmt"]
        )

    def test_media_without_hint_is_not_wrapped_in_a_disclosure(self):
        plan, sheet_config = self._cfg("image")
        assert "<details" not in build_templates(plan, sheet_config)[0]["afmt"]

    @pytest.mark.parametrize(
        "cell", ["image; color=red", "image; bold", "image; align=left"]
    )
    def test_text_styling_on_a_media_column_is_reported(self, cell):
        # These have nothing to style, and silence would read as "it applied".
        _, sheet_config = self._cfg(cell)
        assert any("does nothing on a image column" in w for w in sheet_config.warnings)

    def test_size_on_audio_is_reported_since_it_cannot_apply(self):
        _, sheet_config = self._cfg("audio; size=300")
        assert sheet_config.for_field("Link").size is None
        assert any("size does nothing on an audio" in w for w in sheet_config.warnings)

    def test_a_url_with_query_parameters_survives_into_the_src(self):
        plan, sheet_config = self._cfg("image")
        assert '<img src="{{Link}}"' in build_templates(plan, sheet_config)[0]["afmt"]


class TestEmbeddedPlayers:
    """`video` hands playback to the site hosting the video.

    The distinguishing constraint is that a card template can substitute a field
    but cannot transform one, so the address has to be rewritten on the way into
    the note. These tests pin both halves: the rewrite and the element.
    """

    def _cfg(self, cell="video"):
        plan = plan_columns(["ID", "Word", "Link"])
        return plan, parse_config_row({"ID": "#config", "Link": cell}, plan)

    def test_the_frame_carries_an_aspect_ratio(self):
        # An iframe has no intrinsic size; without this it collapses to ~150px.
        # The rule lives in the stylesheet, which the answer inherits through
        # {{FrontSide}} — hence checking both sides rather than the answer alone.
        plan, sheet_config = self._cfg()
        template = build_templates(plan, sheet_config)[0]
        assert "sc-embed" in template["afmt"]
        assert "aspect-ratio: 16 / 9" in _both(template)

    def test_size_caps_the_width(self):
        plan, sheet_config = self._cfg("video; size=480")
        assert "max-width: 480px" in build_templates(plan, sheet_config)[0]["afmt"]

    def test_it_is_allowed_to_go_fullscreen(self):
        plan, sheet_config = self._cfg()
        assert "allowfullscreen" in build_templates(plan, sheet_config)[0]["afmt"]

    @pytest.mark.parametrize(
        "pasted,expected",
        [
            (
                "https://www.youtube.com/watch?v=gdBu8kLulMM",
                "https://www.youtube.com/embed/gdBu8kLulMM",
            ),
            (
                "https://youtu.be/gdBu8kLulMM",
                "https://www.youtube.com/embed/gdBu8kLulMM",
            ),
            (
                "https://www.youtube.com/shorts/gdBu8kLulMM",
                "https://www.youtube.com/embed/gdBu8kLulMM",
            ),
            (
                "https://www.youtube.com/watch?list=PLxyz&v=gdBu8kLulMM",
                "https://www.youtube.com/embed/gdBu8kLulMM",
            ),
            (
                "https://drive.google.com/file/d/1AbC_dEF/view?usp=sharing",
                "https://drive.google.com/file/d/1AbC_dEF/preview",
            ),
            (
                "https://drive.google.com/open?id=1AbC_dEF",
                "https://drive.google.com/file/d/1AbC_dEF/preview",
            ),
            ("https://vimeo.com/123456789", "https://player.vimeo.com/video/123456789"),
        ],
    )
    def test_a_pasted_address_becomes_a_player_address(self, pasted, expected):
        from src.tsv_model import normalize_embed_url

        assert normalize_embed_url(pasted) == (expected, None)

    def test_an_embed_address_is_left_alone(self):
        # Re-syncing must not keep rewriting a value it already rewrote, or every
        # row would read as changed forever.
        from src.tsv_model import normalize_embed_url

        already = "https://www.youtube.com/embed/gdBu8kLulMM"
        once, _ = normalize_embed_url(already)
        twice, _ = normalize_embed_url(once)
        assert once == twice == already

    def test_the_moment_a_link_points_at_is_kept(self):
        from src.tsv_model import normalize_embed_url

        url, _ = normalize_embed_url("https://youtu.be/gdBu8kLulMM?t=1m30s")
        assert url == "https://www.youtube.com/embed/gdBu8kLulMM?start=90"

    def test_a_channel_or_folder_is_reported_rather_than_framed(self):
        # Framing one of these shows an error page where the video should be,
        # which reads as the add-on being broken.
        from src.tsv_model import normalize_embed_url

        _, warning = normalize_embed_url("https://www.youtube.com/@SomeChannel")
        assert warning and "cannot be embedded" in warning

    def test_an_unknown_address_passes_through(self):
        from src.tsv_model import normalize_embed_url

        direct = "https://example.com/lesson.mp4"
        assert normalize_embed_url(direct) == (direct, None)

    def test_the_sync_stores_the_player_address_not_the_pasted_one(self):
        """End to end: what lands in the note is what the template can play."""
        from src.tsv_model import build_remote_deck_from_tsv
        from src.tsv_model import parse_tsv_data

        tsv = (
            "ID\tWord\tLink\n"
            "#config\t\tvideo\n"
            "1\t熟悉\thttps://www.youtube.com/watch?v=gdBu8kLulMM\n"
        )
        deck = build_remote_deck_from_tsv(parse_tsv_data(tsv), "url")

        assert deck.notes[0]["Link"] == "https://www.youtube.com/embed/gdBu8kLulMM"
        assert deck.sheet_config.warnings == []

    def test_a_column_without_the_directive_is_untouched(self):
        """Only a column that asked for it is rewritten."""
        from src.tsv_model import build_remote_deck_from_tsv
        from src.tsv_model import parse_tsv_data

        pasted = "https://www.youtube.com/watch?v=gdBu8kLulMM"
        tsv = f"ID\tWord\tLink\n1\t熟悉\t{pasted}\n"
        deck = build_remote_deck_from_tsv(parse_tsv_data(tsv), "url")

        assert deck.notes[0]["Link"] == pasted


@pytest.mark.unit
def test_the_shared_rewrite_matches_what_the_sync_stores():
    """One function, so a preview and a sync cannot disagree about a link.

    They did disagree once: the site rebuilt each row from the raw cells and never
    called this, so it framed the un-rewritten address.
    """
    from src.tsv_model import apply_media_rewrites
    from src.tsv_model import build_remote_deck_from_tsv
    from src.tsv_model import parse_tsv_data
    from src.tsv_model import row_to_dict

    pasted = "https://www.youtube.com/watch?v=gdBu8kLulMM"
    tsv = f"ID\tWord\tClip\n#config\t\tvideo\n1\t熟悉\t{pasted}\n"

    parsed = parse_tsv_data(tsv)
    deck = build_remote_deck_from_tsv(parsed, "url")

    # What anything else rendering this row would compute for itself.
    row = row_to_dict(parsed["rows"][1], parsed["headers"])
    apply_media_rewrites(row, deck.plan, deck.sheet_config)

    assert row["Clip"] == deck.notes[0]["Clip"]
    assert row["Clip"] == "https://www.youtube.com/embed/gdBu8kLulMM"


@pytest.mark.unit
class TestTypedAnswer:
    """`type` asks Anki to draw an input box and diff what the learner types."""

    def _cfg(self, cells, deck=""):
        plan = _plan()
        return plan, _config(plan, cells, deck=deck)

    def test_the_box_goes_on_the_question(self):
        # Anki draws the input where {{type:…}} sits and diffs it on the answer, so
        # the tag belongs to the prompt even though the field itself is an answer.
        plan, config = self._cfg({"Meaning": "type"})
        assert "{{type:Meaning}}" in build_templates(plan, config)[0]["qfmt"]

    def test_nc_ignores_diacritics(self):
        # Someone typing pinyin without tone marks still wants a match.
        plan, config = self._cfg({"Reading": "type=nc"})
        assert "{{type:nc:Reading}}" in build_templates(plan, config)[0]["qfmt"]

    def test_the_reverse_card_does_not_ask_the_same_question(self):
        plan, config = self._cfg({"Meaning": "type"}, deck="reverse")
        templates = build_templates(plan, config)
        assert "{{type:" in templates[0]["qfmt"]
        assert "{{type:" not in templates[1]["qfmt"]

    def test_a_clozed_column_is_typed_through_the_cloze_filter(self):
        plan, config = self._cfg({"Example": "cloze; type"})
        qfmt = build_templates(plan, config, is_cloze=True)[0]["qfmt"]
        assert "{{type:cloze:Example}}" in qfmt

    def test_only_one_column_can_be_typed(self):
        # Anki honours one {{type:…}} per card.
        plan, config = self._cfg({"Meaning": "type", "Reading": "type"})
        assert config.type_field == "Reading"  # sheet order, not cell order
        assert any("only one column" in w for w in config.warnings)

    def test_a_bad_mode_is_refused_with_a_warning(self):
        plan, config = self._cfg({"Meaning": "type=fuzzy"})
        assert config.type_field is None
        assert any("type=nc" in w for w in config.warnings)

    def test_typing_a_media_column_is_refused(self):
        plan, config = self._cfg({"Meaning": "image; type"})
        assert config.type_field is None
        assert any("does nothing on a media column" in w for w in config.warnings)


@pytest.mark.unit
class TestClozeIsASheetLevelChoice:
    def test_a_sheet_that_declares_nothing_is_not_a_cloze_sheet(self):
        plan = _plan()
        assert _config(plan, {}).cloze_field is None

    def test_cloze_markup_with_no_declared_column_is_reported(self):
        """Otherwise the markup prints on the card as literal text."""
        from src.tsv_model import build_remote_deck_from_tsv
        from src.tsv_model import parse_tsv_data

        tsv = (
            "ID\tWord\tExample\n" "#config\t\t\n" "1\t熟悉\t我对这里{{c1::很熟悉}}。\n"
        )
        deck = build_remote_deck_from_tsv(parse_tsv_data(tsv), "url")
        assert any("no column is marked" in w for w in deck.sheet_config.warnings)

    def test_a_declared_sheet_reports_nothing(self):
        from src.tsv_model import build_remote_deck_from_tsv
        from src.tsv_model import parse_tsv_data

        tsv = (
            "ID\tWord\tExample\n"
            "#config\t\tcloze\n"
            "1\t熟悉\t我对这里{{c1::很熟悉}}。\n"
        )
        deck = build_remote_deck_from_tsv(parse_tsv_data(tsv), "url")
        assert deck.sheet_config.cloze_field == "Example"
        assert deck.sheet_config.warnings == []


@pytest.mark.unit
def test_a_framed_player_names_a_referrer_policy():
    """Without it the card reads "Error 153" on a phone and plays on a desktop.

    A webview does not send an HTTP Referer the way a browser does, and YouTube
    refuses an embed that arrives without one. Naming the policy is what makes the
    webview send the origin it has.
    """
    plan = plan_columns(["ID", "Word", "Clip"])
    config = parse_config_row({"ID": "#config", "Clip": "video"}, plan)
    afmt = build_templates(plan, config)[0]["afmt"]
    assert 'referrerpolicy="strict-origin-when-cross-origin"' in afmt


@pytest.mark.unit
class TestFramedPlayerOnMobile:
    """A frame cannot play on a phone, so the card must not depend on one.

    The mobile clients load a card from a `file://` origin. No HTTP Referer is
    sent, YouTube answers "Error 153: Video player configuration error", and a
    referrerpolicy cannot help because there is no origin to send. Anki marks
    those clients with a `mobile` class, which is the only reliable way to tell.
    """

    def _templates(self, cell="video"):
        plan = plan_columns(["ID", "Word", "Clip"])
        config = parse_config_row({"ID": "#config", "Clip": cell}, plan)
        return build_templates(plan, config)[0]

    def test_the_frame_goes_through_a_page_with_an_origin(self):
        """This is what lets the video play at all on a phone.

        A card has no origin to lend, so it frames an https page and that page
        frames the video — the request YouTube finally sees carries a referrer.
        """
        from src.card_layout import EMBED_PROXY

        afmt = self._templates()["afmt"]
        assert f'src="{EMBED_PROXY}{{{{Clip}}}}"' in afmt
        assert EMBED_PROXY.startswith("https://")

    def test_the_note_keeps_the_plain_address(self):
        """Only the template knows about that page, so dropping it is a re-sync."""
        afmt = self._templates()["afmt"]
        assert 'sc-embed-link" href="{{Clip}}"' in afmt

    def test_the_link_is_the_way_through_on_mobile(self):
        # Kept small rather than hidden: if that page is ever unreachable, this
        # is the only thing left that opens the video.
        both = _both(self._templates())
        assert ".mobile .sc-embed-link { display: inline-block;" in both

    def test_the_link_is_hidden_everywhere_else(self):
        # On a desktop the frame plays, so a second way in is only clutter.
        assert ".sc-embed-link { display: none; }" in _both(self._templates())

    def test_the_label_names_the_link_when_the_sheet_gave_one(self):
        afmt = self._templates("video; label=Bài giảng")["afmt"]
        assert ">Bài giảng</a>" in afmt

    def test_the_caption_is_escaped(self):
        afmt = self._templates("video; label=A & <b>B</b>")["afmt"]
        assert "A &amp; &lt;b&gt;B&lt;/b&gt;" in afmt


@pytest.mark.unit
class TestFormulaColumn:
    """`math` — Anki ships MathJax, so this is delimiters and nothing else."""

    def test_bare_math_is_inline(self):
        plan = _plan()
        qfmt = build_templates(plan, _config(plan, {"Word": "math"}))[0]["qfmt"]
        assert r"\({{Word}}\)" in qfmt

    def test_block_math_is_the_display_form(self):
        plan = _plan()
        qfmt = build_templates(plan, _config(plan, {"Word": "math=block"}))[0]["qfmt"]
        assert r"\[{{Word}}\]" in qfmt

    def test_no_library_is_loaded_for_it(self):
        # The one thing on a card that needs no script: Anki's own MathJax draws it.
        plan = _plan()
        both = _both(build_templates(plan, _config(plan, {"Word": "math"}))[0])
        assert "mathjax" not in both.lower()

    def test_a_bad_mode_is_refused_by_name(self):
        config = _config(_plan(), {"Word": "math=huge"})
        assert config.for_field("Word").math is None
        assert any("math" in w for w in config.warnings)

    def test_the_cloze_column_keeps_its_filter(self):
        # A clozed field has to reach the card through {{cloze:}}; math would
        # replace that, and Anki draws a clozed field with no deletion as nothing.
        config = _config(_plan(), {"Word": "cloze; math"})
        assert config.for_field("Word").math is None
        assert any("cloze" in w and "math" in w for w in config.warnings)


@pytest.mark.unit
class TestCodeColumn:
    """`code` — kept as typed, coloured by a library the card loads."""

    def test_the_cell_is_a_pre_block_of_plain_text(self):
        plan = _plan()
        qfmt = build_templates(plan, _config(plan, {"Word": "code=python"}))[0]["qfmt"]
        assert '<pre class="sc-code"><code class="language-python">' in qfmt
        # {{text:}} rather than {{Word}}: a cell pasted out of an editor arrives
        # with markup in it, and a card rendering <b> inside a code sample is
        # showing something no compiler will ever see.
        assert "{{text:Word}}" in qfmt

    def test_bare_code_names_no_language(self):
        plan = _plan()
        qfmt = build_templates(plan, _config(plan, {"Word": "code"}))[0]["qfmt"]
        assert '<pre class="sc-code"><code>' in qfmt

    def test_the_library_is_loaded_only_by_the_side_that_needs_it(self):
        plan = _plan()
        template = build_templates(plan, _config(plan, {"Reading": "code=sql"}))[0]
        assert "sc-hljs" in template["afmt"]
        assert "sc-hljs" not in template["qfmt"]

    def test_it_cannot_share_a_column_with_a_formula(self):
        config = _config(_plan(), {"Word": "math; code=python"})
        assert config.for_field("Word").code is None
        assert any("formula or as code" in w for w in config.warnings)


@pytest.mark.unit
class TestFontAndDirection:
    """`font`, `rtl`, `vertical` — the three things CSS can say and a sheet could not."""

    def test_a_known_font_becomes_its_stack_and_is_fetched(self):
        plan = _plan()
        qfmt = build_templates(plan, _config(plan, {"Word": "font=sc"}))[0]["qfmt"]
        assert "font-family: Noto Sans SC, sans-serif" in qfmt
        assert "fonts.googleapis.com" in qfmt
        # @import is only legal at the top of a stylesheet.
        assert qfmt.index("@import") < qfmt.index("{ text-align")

    def test_a_family_name_is_passed_through_as_written(self):
        plan = _plan()
        qfmt = build_templates(plan, _config(plan, {"Word": "font=Comic Sans MS"}))[0][
            "qfmt"
        ]
        assert "font-family: 'Comic Sans MS'" in qfmt
        # Nothing is fetched for it: whether it is installed is not ours to know.
        assert "fonts.googleapis.com" not in qfmt

    def test_right_to_left_also_starts_from_the_right(self):
        plan = _plan()
        qfmt = build_templates(plan, _config(plan, {"Word": "rtl"}))[0]["qfmt"]
        assert "direction: rtl" in qfmt and "text-align: right" in qfmt

    def test_an_explicit_alignment_still_wins(self):
        plan = _plan()
        qfmt = build_templates(plan, _config(plan, {"Word": "rtl; align=center"}))[0][
            "qfmt"
        ]
        assert "text-align: center" in qfmt and "text-align: right" not in qfmt

    def test_vertical_writing_keeps_latin_upright(self):
        plan = _plan()
        qfmt = build_templates(plan, _config(plan, {"Word": "vertical"}))[0]["qfmt"]
        assert "writing-mode: vertical-rl" in qfmt
        assert "text-orientation: mixed" in qfmt

    def test_a_column_has_one_direction(self):
        config = _config(_plan(), {"Word": "rtl; vertical"})
        assert config.for_field("Word").rtl and not config.for_field("Word").vertical
        assert any("two directions" in w for w in config.warnings)

    def test_none_of_them_touch_a_media_column(self):
        config = _config(_plan(), {"Word": "image; font=sc; rtl; vertical"})
        cfg = config.for_field("Word")
        assert cfg.font is None and not cfg.rtl and not cfg.vertical
        said = " ".join(config.warnings)
        for key in ("font", "rtl", "vertical"):
            assert key in said


@pytest.mark.unit
class TestSortColumn:
    """`sort` — a note property, like `subdeck`, and not a card one."""

    def test_it_names_the_column_and_changes_nothing_on_the_card(self):
        plan = _plan()
        plain = build_templates(plan, _config(plan))[0]
        config = _config(plan, {"Meaning": "sort"})
        assert config.sort_field == "Meaning"
        assert build_templates(plan, config)[0] == plain

    def test_only_one_column_can_be_it(self):
        config = _config(_plan(), {"Word": "sort", "Meaning": "sort"})
        assert config.sort_field == "Word"
        assert any("sorts by" in w for w in config.warnings)

    def test_a_media_column_is_refused(self):
        # Sorting a deck by a column of URLs lists it by whatever the addresses
        # happen to start with.
        config = _config(_plan(), {"Word": "image; sort"})
        assert config.sort_field is None
        assert any("sort" in w for w in config.warnings)

    def test_it_reaches_the_note_type_as_an_index(self):
        """Anki stores the sort field as a position in the field list.

        The browser's first column and a deck's sort order both read it, and
        without this it is field 0 — which here is `ID`, so a deck lists as w01,
        w02, w03.
        """
        from src.templates_and_definitions import apply_sort_field

        plan = _plan()
        fields = plan.note_type_fields()
        model = {"sortf": 0}
        config = _config(plan, {"Meaning": "sort"})
        assert apply_sort_field(None, model, fields, config) is True
        assert fields[model["sortf"]] == "Meaning"
        # Idempotent: a re-sync of an unchanged sheet must not mark the note type
        # as changed, which would rewrite it on every single sync.
        assert apply_sort_field(None, model, fields, config) is False

    def test_a_sheet_that_says_nothing_leaves_the_note_type_alone(self):
        from src.templates_and_definitions import apply_sort_field

        plan = _plan()
        model = {"sortf": 0}
        assert apply_sort_field(
            None, model, plan.note_type_fields(), _config(plan)
        ) is (False)
        assert model["sortf"] == 0

    def test_a_deck_level_may_still_be_the_sort_column(self):
        # `subdeck` refuses every *card* key, and this is not one of them: where a
        # note is filed and how it is listed are both properties of the note.
        config = _config(_plan(), {"Word": "subdeck=1; sort"})
        assert config.sort_field == "Word"
        assert config.subdeck_columns == ["Word"]


@pytest.mark.unit
class TestDrawnColumn:
    """``draw`` — a column the learner writes stroke by stroke instead of reads."""

    def _templates(self, cell="draw", header="Word", **kw):
        plan = _plan()
        config = _config(plan, {header: cell}, **kw)
        return build_templates(plan, config)[0], config

    def test_the_box_replaces_the_text(self):
        template, _ = self._templates()
        assert 'sc-draw" data-sc-char="{{text:Word}}"' in template["qfmt"]
        # Printing the field as well would be showing the answer beside the box.
        assert '<div class="sc-front"' in template["qfmt"]
        assert ">{{Word}}<" not in template["qfmt"]

    def test_the_character_is_handed_over_stripped_of_markup(self):
        # {{text:}} rather than {{}}: the box reads its character out of an
        # attribute, and a field carrying <b> would put a tag in there.
        assert "{{text:Word}}" in self._templates()[0]["qfmt"]

    def test_a_prompt_asks_and_an_answer_shows(self):
        # "Reading" rather than "Word": moving the only front column to the back
        # empties the prompt, and split_sides promotes it straight back again.
        front = self._templates()[0]["qfmt"]
        back = self._templates("draw", header="Reading")[0]["afmt"]
        assert 'data-sc-quiz="1"' in front
        assert 'data-sc-quiz="0"' in back

    def test_the_question_is_a_blank_square(self):
        """The outline is the whole character in a pale colour.

        Drawn on the side that is *asking*, it is the answer sitting there to be
        traced over, which is not the same exercise at all.
        """
        assert (
            "showCharacter: !quiz, showOutline: !quiz" in self._templates()[0]["qfmt"]
        )

    def test_the_library_is_loaded_once_per_side_that_needs_it(self):
        template, _ = self._templates()
        assert template["qfmt"].count("hanzi-writer") >= 1
        # A side with no box has no reason to fetch it.
        assert "hanzi-writer" not in build_templates(_plan(), SheetConfig())[0]["qfmt"]

    def test_the_script_can_run_twice_without_drawing_twice(self):
        # Anki re-executes a card's scripts every time it draws the card.
        assert "if (box.dataset.scDone) return;" in self._templates()[0]["qfmt"]

    def test_size_is_the_box_not_a_font(self):
        qfmt = self._templates("draw; size=280")[0]["qfmt"]
        assert 'data-sc-size="280"' in qfmt
        assert "min-width: 280px" in qfmt
        assert "font-size: 280px" not in qfmt

    def test_a_box_sized_like_a_picture_is_allowed(self):
        _, config = self._templates("draw; size=400")
        assert config.for_field("Word").size == 400
        assert not config.warnings

    def test_colour_still_reaches_the_strokes(self):
        # The strokes are drawn in whatever colour the box inherits, so `color`
        # is the one text directive that is not inert here.
        qfmt = self._templates("draw; color=accent")[0]["qfmt"]
        assert "color: var(--sc-accent)" in qfmt

    def test_the_empty_box_says_which_character_it_wanted(self):
        # No network, or a client that refuses remote scripts.
        assert ".sc-draw:empty::before { content: attr(data-sc-char);" in _both(
            self._templates()[0]
        )

    def test_hint_hides_the_box_behind_a_disclosure(self):
        qfmt = self._templates("draw; hint")[0]["qfmt"]
        assert '<details class="sc-reveal"><summary>Write it</summary>' in qfmt

    def test_a_media_column_cannot_be_drawn(self):
        _, config = self._templates("image; draw")
        assert not config.for_field("Word").draw
        assert any("draw removed" in w for w in config.warnings)

    def test_a_cloze_column_cannot_be_drawn(self):
        _, config = self._templates("cloze; draw")
        assert not config.for_field("Word").draw
        assert any("cannot also be drawn" in w for w in config.warnings)

    def test_what_does_nothing_on_a_box_says_so(self):
        _, config = self._templates("draw; bold; italic; furigana")
        joined = " ".join(config.warnings)
        assert "bold, italic" in joined
        assert "furigana does nothing on a drawn column" in joined

    def test_the_reverse_card_asks_on_whichever_side_it_lands(self):
        plan = _plan()
        config = _config(plan, {"Word": "draw"}, deck="reverse")
        templates = build_templates(plan, config)
        assert templates[0]["name"] == FRONT_TEMPLATE_NAME
        assert templates[1]["name"] == REVERSE_TEMPLATE_NAME
        # Word is the prompt on card 1 and the answer on card 2, so the same
        # column takes strokes in one direction and shows them in the other.
        assert 'data-sc-quiz="1"' in templates[0]["qfmt"]
        assert 'data-sc-quiz="0"' in templates[1]["afmt"]

    def test_speech_still_works_on_a_box(self):
        # tts has something to say — the character — unlike on a media column,
        # where it would read a URL aloud.
        _, config = self._templates("draw; tts=zh_CN")
        assert config.for_field("Word").tts == "zh_CN"
        assert not config.warnings


@pytest.mark.unit
class TestDeckFromAColumn:
    """``subdeck=n`` — an ordinary column that also files the note."""

    def _levels(self, cells, headers=None):
        plan = _plan(headers) if headers else _plan()
        return plan, _config(plan, cells)

    def test_a_column_becomes_a_level_of_the_deck_path(self):
        from src.column_model import deck_path

        plan, config = self._levels({"Word": "subdeck=1", "Reading": "subdeck=2"})
        assert config.subdeck_columns == ["Word", "Reading"]
        row = {"Word": "HSK 1", "Reading": "Verbs", "Meaning": "x"}
        assert deck_path(row, plan, config) == ["HSK 1", "Verbs"]

    def test_the_level_number_orders_the_path_not_the_column_position(self):
        from src.column_model import deck_path

        plan, config = self._levels({"Word": "subdeck=2", "Reading": "subdeck=1"})
        assert config.subdeck_columns == ["Reading", "Word"]
        row = {"Word": "Verbs", "Reading": "HSK 1"}
        assert deck_path(row, plan, config) == ["HSK 1", "Verbs"]

    def test_a_deck_level_stays_off_the_card_by_default(self):
        """A directive named after the deck must not also start printing.

        The reserved SUBDECK columns never appear on a card, and a column that
        says `subdeck=1` was written to file the note. Rendering it as well —
        which is what this used to do — put an unasked-for line of text on every
        card of every sheet that used it.
        """
        plan, config = self._levels({"Word": "subdeck=1"})
        assert config.subdeck_columns == ["Word"]
        for template in build_templates(plan, config):
            assert "{{Word}}" not in _both(template)
        front, back = split_sides(plan, config)
        assert "Word" not in front and "Word" not in back

    def test_a_side_cannot_put_it_on_the_card_either(self):
        """Where a note is filed is a bigger thing than how one card looks.

        A directive working at deck level has no business reaching down into the
        card, so there is one rule rather than two: a deck level is a deck level,
        exactly as a reserved SUBDECK column has always been.
        """
        plan, config = self._levels({"Reading": "subdeck=1; side=back"})
        assert config.subdeck_columns == ["Reading"]
        assert "{{Reading}}" not in _both(build_templates(plan, config)[0])
        assert any("not part of the card" in w and "side" in w for w in config.warnings)

    def test_nothing_about_a_card_survives_on_a_deck_level(self):
        # Inert settings are named rather than left to be discovered, the same
        # way they are on a media column.
        _, config = self._levels(
            {"Reading": "subdeck=1; size=20; color=accent; bold; tts=zh_CN; hint"}
        )
        cfg = config.for_field("Reading")
        assert cfg.subdeck == 1
        assert (cfg.size, cfg.color, cfg.tts) == (None, None, None)
        assert not cfg.bold and not cfg.hint
        said = " ".join(config.warnings)
        for key in ("size", "color", "tts", "bold", "hint"):
            assert key in said

    def test_a_deck_level_is_never_spoken_either(self):
        # `side=hide` + `tts` is heard without being read, but that is about the
        # card too — and a deck level is not on the card at all. The stylesheet
        # names the voice-list classes on every card, so this looks for the tag
        # and for the voice list, not for the word.
        plan, config = self._levels({"Reading": "subdeck=1; tts=zh_CN"})
        rendered = _both(build_templates(plan, config)[0])
        assert "{{tts" not in rendered
        # The stylesheet names the voice list's classes on every card, so the
        # marker is the attribute only the block itself carries.
        assert "data-sc-langs" not in rendered

    def test_the_field_exists_on_the_note_either_way(self):
        # Not rendering it is a decision about the card, not about the note: the
        # value is still there to be searched, exported and styled later.
        plan, _ = self._levels({"Word": "subdeck=1"})
        assert "Word" in plan.note_type_fields()

    def test_an_empty_cell_drops_that_level(self):
        from src.column_model import deck_path

        plan, config = self._levels({"Word": "subdeck=1", "Reading": "subdeck=2"})
        assert deck_path({"Word": "HSK 1", "Reading": ""}, plan, config) == ["HSK 1"]

    def test_a_sheet_that_says_nothing_still_uses_the_reserved_columns(self):
        from src.column_model import deck_path
        from src.column_model import plan_columns

        plan = plan_columns(["ID", "SUBDECK 1", "Word"])
        row = {"SUBDECK 1": "Verbs", "Word": "写"}
        assert deck_path(row, plan, SheetConfig()) == ["Verbs"]
        assert deck_path(row, plan) == ["Verbs"]

    def test_the_settings_row_wins_over_the_reserved_columns_and_says_so(self):
        from src.column_model import deck_path
        from src.column_model import plan_columns

        plan = plan_columns(["ID", "SUBDECK 1", "Level", "Word"])
        config = parse_config_row(
            {"ID": "#config", "Level": "subdeck=1"},
            plan,
        )
        assert config.subdeck_columns == ["Level"]
        assert any("'SUBDECK 1'" in w and "ignored" in w for w in config.warnings)
        row = {"SUBDECK 1": "Old", "Level": "New", "Word": "写"}
        assert deck_path(row, plan, config) == ["New"]

    def test_two_columns_cannot_be_the_same_level(self):
        plan, config = self._levels({"Word": "subdeck=1", "Reading": "subdeck=1"})
        assert config.subdeck_columns == ["Word"]
        assert any("already 'Word'" in w for w in config.warnings)

    def test_a_media_column_cannot_be_a_deck_level(self):
        # The cell holds a URL; get_subdeck_name would strip it to something
        # unrecognisable rather than fail, which is worse than refusing it.
        _, config = self._levels({"Word": "image; subdeck=1"})
        assert config.subdeck_columns == []
        assert any("cannot be a deck level" in w for w in config.warnings)

    def test_a_level_that_is_not_a_number_is_refused(self):
        _, config = self._levels({"Word": "subdeck=top"})
        assert config.subdeck_columns == []
        assert any("level number" in w for w in config.warnings)

    def test_a_level_below_one_is_refused(self):
        _, config = self._levels({"Word": "subdeck=0"})
        assert config.subdeck_columns == []
        assert any("below 1" in w for w in config.warnings)

    def test_the_tags_mirror_the_deck_path(self):
        from src.tsv_model import build_tags

        plan, config = self._levels({"Word": "subdeck=1", "Reading": "subdeck=2"})
        tags = build_tags({"Word": "HSK 1", "Reading": "Verbs"}, plan, config)
        assert "sheetcards::hsk_1::verbs" in tags


@pytest.mark.unit
class TestUnsortedDeck:
    """The pile a row lands in when it names no level. There is no directive.

    A sheet that sorts its rows is already saying a row belongs somewhere, so the
    one that names nothing has an answer either way — and a key to switch that on
    would only be a key to leave those rows loose among the folders.
    """

    def test_it_reaches_the_deck_and_the_tags(self):
        from src.column_model import UNSORTED_DECK
        from src.column_model import deck_path
        from src.column_model import plan_columns
        from src.tsv_model import build_tags
        from src.tsv_model import get_subdeck_name

        plan = plan_columns(["ID", "SUBDECK 1", "Word"])
        config = parse_config_row({"ID": "#config"}, plan)
        row = {"SUBDECK 1": "", "Word": "写"}
        assert get_subdeck_name("Deck", deck_path(row, plan, config)) == (
            f"Deck::{UNSORTED_DECK}"
        )
        assert "sheetcards::unsorted" in build_tags(row, plan, config)

    def test_a_deck_column_from_the_settings_row_sorts_the_same_way(self):
        from src.column_model import UNSORTED_DECK
        from src.column_model import deck_path

        plan = _plan()
        config = _config(plan, {"Word": "subdeck=1"})
        assert deck_path({"Word": "", "Reading": "x"}, plan, config) == [UNSORTED_DECK]

    def test_it_says_nothing_about_the_card(self):
        # It is where the note is filed, and a card never mentions that.
        plan = _plan()
        config = _config(plan, {"Word": "subdeck=1"})
        for template in build_templates(plan, config):
            assert "Unsorted" not in _both(template)


@pytest.mark.unit
class TestHeardNotSeen:
    """``side=hide`` + ``tts`` — a column spoken without being shown."""

    def _templates(self, cells, deck=""):
        plan = _plan()
        config = _config(plan, cells, deck=deck)
        return plan, config, build_templates(plan, config)

    def test_a_hidden_column_can_still_be_spoken(self):
        plan, config, templates = self._templates({"Reading": "side=hide; tts=zh_CN"})
        both = _both(templates[0])
        assert "{{tts zh_CN:Reading}}" in both
        # Spoken, and nowhere to be read.
        assert '<div class="sc-back" data-sc-col="Reading"' not in both
        front, back = split_sides(plan, config)
        assert "Reading" not in front and "Reading" not in back

    def test_a_hidden_column_with_no_speech_is_simply_gone(self):
        _, _, templates = self._templates({"Reading": "side=hide"})
        assert "Reading" not in _both(templates[0])

    def test_it_is_heard_on_the_side_it_would_have_been_drawn_on(self):
        _, _, templates = self._templates(
            {"Word": "side=hide; tts=en_US", "Reading": "side=hide; tts=zh_CN"}
        )
        # Word is the sheet's first content column, so its side is the question.
        assert "{{tts en_US:Word}}" in templates[0]["qfmt"]
        assert (
            "{{tts en_US:Word}}"
            not in templates[0]["afmt"].split('<hr id="answer">')[1]
        )
        assert "{{tts zh_CN:Reading}}" in templates[0]["afmt"]

    def test_the_reverse_card_swaps_the_voices_too(self):
        _, _, templates = self._templates(
            {"Reading": "side=hide; tts=zh_CN"}, deck="reverse"
        )
        assert len(templates) == 2
        # Heard on the answer of card 1, so heard on the question of card 2.
        assert "{{tts zh_CN:Reading}}" in templates[1]["qfmt"]

    def test_the_speech_is_guarded_so_an_empty_cell_says_nothing(self):
        _, _, templates = self._templates({"Reading": "side=hide; tts=zh_CN"})
        assert "{{#Reading}}{{tts zh_CN:Reading}}{{/Reading}}" in _both(templates[0])

    def test_speed_still_applies(self):
        _, _, templates = self._templates(
            {"Reading": "side=hide; tts=zh_CN; speed=0.5"}
        )
        assert "{{tts zh_CN speed=0.5:Reading}}" in _both(templates[0])


# ---------------------------------------------------------------------------
# What Anki itself makes of the templates
# ---------------------------------------------------------------------------

_HAS_ANKI = importlib.util.find_spec("anki") is not None
needs_anki = pytest.mark.skipif(
    not _HAS_ANKI,
    reason="the real anki library is not installed (pip install -e '.[dev]')",
)

_SAVE_HARNESS = """
import json, os, sys, tempfile, types
from anki.collection import Collection

# `src/__init__.py` imports compat, which imports aqt, which needs a Qt with a
# working libEGL — which a headless CI runner has no reason to have. The pure
# modules need none of it, so they are reached through a package fabricated over
# the same directory, exactly as tests/test_apkg.py does.
pkg = types.ModuleType("sc"); pkg.__path__ = [os.path.join({repo!r}, "src")]
sys.modules["sc"] = pkg
from sc.column_model import plan_columns
from sc.sheet_config import parse_config_row
from sc.card_layout import build_templates

headers, config, is_cloze = {headers!r}, {config!r}, {cloze!r}
plan = plan_columns(headers)
cfg = parse_config_row(dict(zip(headers, config)), plan)
col = Collection(os.path.join(tempfile.mkdtemp(), "c.anki2"))
model = col.models.new("SheetCards - t - " + ("Cloze" if is_cloze else "Basic"))
if is_cloze:
    model["type"] = 1
    model["css"] = ""
for name in plan.note_type_fields():
    col.models.add_field(model, col.models.new_field(name))
if cfg.cloze_field:
    model["sortf"] = plan.note_type_fields().index(cfg.cloze_field)
for t in build_templates(plan, cfg, is_cloze=is_cloze):
    tmpl = col.models.new_template(t["name"])
    tmpl["qfmt"], tmpl["afmt"] = t["qfmt"], t["afmt"]
    col.models.add_template(model, tmpl)
try:
    col.models.add(model)
except Exception as exc:
    print(json.dumps({{"ok": False, "error": str(exc)}}))
    raise SystemExit(0)
print(json.dumps({{"ok": True, "error": ""}}))
"""


def _anki_accepts(headers, config, is_cloze=False):
    """Whether a real Anki will save the note type these templates describe.

    The suite's `anki` is a mock that will store any string at all, so a template
    holding a reference to a field that does not exist saves happily here and is
    refused on the machine of whoever synced. Only Anki can answer this.
    """
    code = _SAVE_HARNESS.format(
        repo=str(Path(__file__).resolve().parent.parent),
        headers=headers,
        config=config,
        cloze=is_cloze,
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).resolve().parent.parent),
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


class TestNothingInAScriptLooksLikeAField:
    """The trap that a mock cannot see.

    Anki scans the **whole** template for `{{...}}` — inside `<script>`, inside a
    JavaScript comment, anywhere. A tag written out as an example in a comment is
    therefore a reference to a field, and a note type naming a field it does not
    have is refused outright: the deck stops syncing with "Field 'Front' not
    found" and nothing on the card says which template did it. This shipped once,
    in a comment explaining the shape of the voice list.
    """

    def test_no_script_carries_its_reasoning_onto_the_card(self):
        """A template is not a place to explain anything.

        It is generated, it is overwritten on every sync, and the only person who
        ever opens one is someone already lost. Every note type on every synced
        device would carry the explanation around. So the reasons live in this
        repo as Python comments, outside the string, where they cost a reader
        nothing — which is how the writing box's script and the highlighter's
        have always been written.
        """
        from src import card_layout

        for name in dir(card_layout):
            if not name.endswith("_SCRIPT"):
                continue
            for line in getattr(card_layout, name).split("\n"):
                # `//` on its own is the middle of a CDN address.
                bare = line.strip()
                assert not bare.startswith("//"), f"{name} explains itself"
                assert not bare.startswith("/*"), f"{name} explains itself"

    def test_no_emitted_script_writes_a_doubled_brace(self):
        from src import card_layout

        for name in dir(card_layout):
            if not name.endswith("_SCRIPT"):
                continue
            script = getattr(card_layout, name)
            assert "{{" not in script, f"{name} would be read as a field reference"
            assert "}}" not in script, f"{name} would be read as a field reference"

    @pytest.mark.slow
    @needs_anki
    def test_a_spoken_sheet_saves(self):
        # The sheet this was found on: two columns speaking, a voice pinned.
        headers = ["ID", "SYNC", "SUBDECK 1", "Word", "IPA", "Meaning", "Example"]
        config = [
            "#config align=center",
            "",
            "",
            "side=front; size=40; bold; tts=en_US; voices=Apple_Ava_(Premium)",
            "side=front; size=18; color=muted",
            "size=22",
            "label=Examples; size=17; italic; tts=en_US",
        ]
        assert _anki_accepts(headers, config)["error"] == ""

    @pytest.mark.slow
    @needs_anki
    def test_every_script_bearing_column_saves_together(self):
        # draw, code and the voice list each append a <script>, and each is a
        # place an example tag could be written down by mistake.
        headers = ["ID", "Hanzi", "Snippet", "Formula", "Reading", "Picture", "Clip"]
        config = [
            "#config",
            "side=front; draw; size=200; tts=zh_CN",
            "code=python; side=back",
            "math=block",
            "furigana; tts=ja_JP",
            "image; size=400",
            "video",
        ]
        assert _anki_accepts(headers, config)["error"] == ""

    @pytest.mark.slow
    @needs_anki
    def test_a_cloze_sheet_saves(self):
        headers = ["ID", "Sentence", "Note"]
        config = ["#config", "cloze; type", "size=16; hint"]
        assert _anki_accepts(headers, config, is_cloze=True)["error"] == ""
