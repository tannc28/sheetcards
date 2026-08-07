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
        [
            ("image", "<img"),
            ("audio", "<audio"),
            ("video", "<iframe"),
        ],
    )
    def test_each_kind_wraps_the_field_in_its_element(self, cell, tag):
        plan, sheet_config = self._cfg(cell)
        afmt = build_templates(plan, sheet_config)[0]["afmt"]
        assert f'{tag} src="{{{{Link}}}}"' in afmt

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
        assert "s2a-embed" in template["afmt"]
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
