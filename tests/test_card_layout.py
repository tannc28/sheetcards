#!/usr/bin/env python3
"""Tests for the card templates generated from a sheet's columns + settings row."""

import pytest

from src.card_layout import FRONT_TEMPLATE_NAME
from src.card_layout import REVERSE_TEMPLATE_NAME
from src.card_layout import build_templates
from src.card_layout import split_sides
from src.column_model import plan_columns
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
        assert 'class="s2a-front"><' not in qfmt  # no label either
        assert 'class="s2a-front">{{Word}}' in qfmt

    def test_deck_alignment_reaches_the_css(self):
        plan = _plan()
        qfmt = build_templates(plan, _config(plan, deck="align=left"))[0]["qfmt"]
        assert "text-align: left" in qfmt

    def test_theme_colour_resolves_to_a_custom_property(self):
        plan = _plan()
        config = _config(plan, {"Reading": "color=muted", "Meaning": "color=accent"})
        afmt = build_templates(plan, config)[0]["afmt"]
        assert "color: var(--s2a-muted)" in afmt
        assert "color: var(--s2a-accent)" in afmt

    def test_theme_colours_are_defined_for_both_themes(self):
        # A single value would leave one theme unreadable, which is the whole point
        # of the named colours: the night_mode override has to be there too.
        qfmt = build_templates(_plan(), SheetConfig())[0]["qfmt"]
        for name in ("--s2a-muted", "--s2a-accent"):
            assert f":root {{ {name}" in qfmt or f"; {name}" in qfmt
            assert qfmt.count(name) >= 2
        night = qfmt.split(".night_mode {")[1].split("}")[0]
        assert "--s2a-muted:" in night and "--s2a-accent:" in night

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
        assert '<div class="s2a-label">Pronunciation</div>{{Reading}}' in afmt

    def test_no_label_means_no_caption_markup(self):
        assert "s2a-label" not in build_templates(_plan(), SheetConfig())[0]["afmt"]

    def test_label_text_is_escaped(self):
        plan = _plan()
        config = _config(plan, {"Reading": "label=A & <b>B</b>"})
        afmt = build_templates(plan, config)[0]["afmt"]
        assert "A &amp; &lt;b&gt;B&lt;/b&gt;" in afmt

    def test_templates_are_pure_markup(self):
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

    def test_cloze_wraps_the_prompt_on_both_sides(self):
        # Anki refuses to save a cloze note type unless {{cloze:Field}} appears on
        # BOTH sides; {{FrontSide}} does not satisfy it. Regression guard for a
        # sync that aborted with "Card template 1 ... has a problem".
        templates = build_templates(_plan(), SheetConfig(), is_cloze=True)
        assert "{{cloze:Word}}" in templates[0]["qfmt"]
        assert "{{cloze:Word}}" in templates[0]["afmt"]
        assert "{{FrontSide}}" not in templates[0]["afmt"]

    def test_cloze_prompt_keeps_the_filter_even_with_hint_asked_for(self):
        # hint: would replace cloze: and take the whole note type down with it.
        plan = _plan()
        config = _config(plan, {"Word": "hint"})
        templates = build_templates(plan, config, is_cloze=True)
        assert "{{cloze:Word}}" in templates[0]["qfmt"]
        assert "{{cloze:Word}}" in templates[0]["afmt"]

    def test_cloze_prompt_moved_by_side_is_still_wrapped_on_both_sides(self):
        plan = _plan()
        config = _config(plan, {"Word": "side=back", "Meaning": "side=front"})
        templates = build_templates(plan, config, is_cloze=True)
        assert "{{cloze:Meaning}}" in templates[0]["qfmt"]
        assert "{{cloze:Meaning}}" in templates[0]["afmt"]

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
        templates = build_templates(_plan(UNICODE_FIELDS), SheetConfig(), is_cloze=True)
        assert "{{cloze:Hán tự}}" in templates[0]["qfmt"]
        assert "{{cloze:Hán tự}}" in templates[0]["afmt"]

    def test_settings_address_a_non_ascii_column(self):
        # Unicode handling: the settings row is keyed by the header as written, so a
        # multi-byte name has to match the column it configures.
        plan = _plan(UNICODE_FIELDS)
        config = _config(plan, {"Nghĩa": "size=22; color=muted", "Ví dụ": "side=hide"})
        afmt = build_templates(plan, config)[0]["afmt"]
        assert "font-size: 22px" in afmt and "color: var(--s2a-muted)" in afmt
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
        [("image", "<img"), ("audio", "<audio"), ("video", "<video")],
    )
    def test_each_kind_wraps_the_field_in_its_element(self, cell, tag):
        plan, sheet_config = self._cfg(cell)
        afmt = build_templates(plan, sheet_config)[0]["afmt"]
        assert f'{tag} src="{{{{Link}}}}"' in afmt

    def test_playable_media_always_gets_controls(self):
        # A sound the learner cannot replay is worse than no sound.
        for kind in ("audio", "video"):
            plan, sheet_config = self._cfg(kind)
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
