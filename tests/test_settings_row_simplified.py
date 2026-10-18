"""What the settings row stopped asking for, and what the rows now say by themselves.

Keys were taken out (``rtl``, ``sort``, ``vertical``, a deck-wide ``align`` and
``speed``), the reserved ``SUBDECK n`` headers are on their way out, and a few
things a sheet used to have to spell out are worked out from the cells: line
breaks, a bare ``label``, and hints for a picture or furigana column nobody
declared.
"""

import pytest

from src.column_model import plan_columns
from src.sheet_config import _DECK_KEYS
from src.sheet_config import _FIELD_KEYS
from src.sheet_config import ADVANCED_GROUPS
from src.sheet_config import BASIC_KEYS
from src.sheet_config import INTERNAL_KEYS
from src.sheet_config import MEDIA_KINDS
from src.sheet_config import parse_config_row
from src.tsv_model import build_remote_deck_from_tsv
from src.tsv_model import parse_tsv_data


def _deck(tsv):
    return build_remote_deck_from_tsv(parse_tsv_data(tsv), "u")


def _codes(deck):
    return [w.code for w in deck.sheet_config.warnings]


@pytest.mark.unit
class TestKeySets:
    def test_basic_and_advanced_cover_every_key_once_each(self):
        advanced = [key for _, keys in ADVANCED_GROUPS for key in keys]
        offered = set(BASIC_KEYS) | set(advanced) | set(INTERNAL_KEYS)
        every = set(_FIELD_KEYS) | set(_DECK_KEYS)
        assert offered == every
        # color is taught twice on purpose (muted/accent, then names and #hex)
        assert [k for k in advanced if k in BASIC_KEYS] == ["color"]
        assert len(BASIC_KEYS) == 11

    def test_deck_keys_and_column_keys_share_no_name(self):
        assert not set(_DECK_KEYS) & set(_FIELD_KEYS)
        assert set(MEDIA_KINDS) <= set(_FIELD_KEYS)


@pytest.mark.unit
class TestRetiredKeys:
    def test_absorbed_keys_say_nothing(self):
        plan = plan_columns(["ID", "Word", "Meaning"])
        config = parse_config_row({"ID": "#config", "Word": "rtl; sort"}, plan)
        assert config.warnings == []

    def test_dropped_keys_say_what_to_do(self):
        plan = plan_columns(["ID", "Word"])
        config = parse_config_row(
            {"ID": "#config align=left; speed=0.8", "Word": "vertical"}, plan
        )
        assert _codes_of(config) == ["retired-key"] * 3
        said = " ".join(config.warnings)
        assert "each column's own cell" in said and "left to right" in said

    def test_without_an_id_column_align_is_the_first_columns_own(self):
        deck = _deck("Word\tMeaning\n#config theme=paper; align=left\t\napple\tx\n")
        config = deck.sheet_config
        assert config.warnings == []
        assert config.theme == "paper"
        assert config.for_field("Word").align == "left"


def _codes_of(config):
    return [w.code for w in config.warnings]


@pytest.mark.unit
class TestBareLabel:
    def test_a_bare_label_is_the_header(self):
        plan = plan_columns(["ID", "Word", "Nghĩa"])
        config = parse_config_row({"ID": "#config", "Nghĩa": "label"}, plan)
        assert config.warnings == []
        assert config.for_field("Nghĩa").label == "Nghĩa"

    def test_a_written_label_still_wins(self):
        plan = plan_columns(["ID", "Word", "Nghĩa"])
        config = parse_config_row({"ID": "#config", "Nghĩa": "label=Meaning"}, plan)
        assert config.for_field("Nghĩa").label == "Meaning"


@pytest.mark.unit
class TestSubdeckHeaders:
    def test_they_still_file_notes_and_say_they_are_going(self):
        deck = _deck("ID\tSUBDECK 1\tWord\n1\tLesson 1\tapple\n")
        assert _codes(deck) == ["subdeck-header-retired"]
        assert "subdeck=1" in deck.sheet_config.warnings[0]
        assert deck.notes[0]["tags"][1].lower() == "sheetcards::lesson_1"

    def test_not_said_twice_when_the_settings_row_overrules_them(self):
        deck = _deck(
            "ID\tSUBDECK 1\tBài học\tWord\n#config\t\tsubdeck=1\t\n1\tx\tL1\tapple\n"
        )
        assert _codes(deck) == ["subdeck-headers-ignored"]

    def test_a_named_column_says_nothing(self):
        deck = _deck("ID\tBài học\tWord\n#config\tsubdeck=1\t\n1\tL1\tapple\n")
        assert _codes(deck) == []


@pytest.mark.unit
class TestLineBreaks:
    def test_a_cell_on_three_lines_reaches_the_note_as_three(self):
        rows = [["ID", "Word", "Example"], ["1", "a", "one\ntwo\r\nthree"]]
        deck = build_remote_deck_from_tsv({"headers": rows[0], "rows": rows[1:]}, "u")
        assert deck.notes[0]["Example"] == "one<br>two<br>three"

    def test_code_media_math_and_deck_levels_keep_theirs(self):
        rows = [
            ["ID", "Word", "Code", "Formula", "Pic", "Lesson"],
            ["#config", "", "code=python", "math", "image", "subdeck=1"],
            ["1", "a", "x = 1\ny = 2", "a\nb", "https://e.org/a\n", "L\n1"],
        ]
        note = build_remote_deck_from_tsv(
            {"headers": rows[0], "rows": rows[1:]}, "u"
        ).notes[0]
        assert note["Code"] == "x = 1\ny = 2"
        assert note["Formula"] == "a\nb"
        assert "<br>" not in note["Pic"] and "<br>" not in note["Lesson"]

    def test_the_rewrite_is_stable(self):
        """A second pass changes nothing, so a re-sync sees no modification."""
        from src.tsv_model import _cell_breaks

        once = _cell_breaks("a\nb")
        assert _cell_breaks(once) == once


@pytest.mark.unit
class TestHints:
    def test_a_column_of_picture_links_is_named(self):
        deck = _deck(
            "ID\tWord\tPic\n1\ta\thttps://e.org/a.png\n2\tb\thttps://e.org/b.jpg?x=1\n"
        )
        assert _codes(deck) == ["looks-like-image"]

    def test_a_declared_or_mostly_text_column_is_not(self):
        assert (
            _codes(
                _deck("ID\tWord\tPic\n#config\t\timage\n1\ta\thttps://e.org/a.png\n")
            )
            == []
        )
        assert (
            _codes(
                _deck(
                    "ID\tWord\tPic\n1\ta\thttps://e.org/a.png\n2\tb\tbook\n3\tc\tcat\n"
                )
            )
            == []
        )

    def test_a_column_of_furigana_is_named(self):
        deck = _deck("ID\tWord\n1\t日本語[にほんご]\n2\t私[わたし]は\n")
        assert _codes(deck) == ["looks-like-furigana"]
        deck = _deck("ID\tWord\n#config\tfurigana\n1\t日本語[にほんご]\n")
        assert _codes(deck) == []
