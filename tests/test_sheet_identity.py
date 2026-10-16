"""The two settings-row keys that are about the sheet, not its cards.

``deckname=`` is the deck's name and the identity a sheet carries wherever it
goes, ``next=`` the next ID Create sheet will hand out. The add-on reads them
without complaint and has no use for them yet; the website keys a package by
the name (see ``apkg.resolve_identity``).
"""

import pytest

from src.column_model import plan_columns
from src.sheet_config import parse_config_row

PLAN = plan_columns(["ID", "Word", "Meaning"])


def _parse(marker):
    return parse_config_row({"ID": marker}, PLAN)


@pytest.mark.unit
class TestSheetKeys:
    def test_both_are_read_without_a_warning(self):
        config = _parse("#config deckname=Từ vựng tiếng Anh; next=w15; theme=sakura")
        assert config.warnings == []
        assert config.deck_name == "Từ vựng tiếng Anh"
        assert config.next_id == "w15"
        assert config.theme == "sakura"

    def test_the_value_keeps_its_case(self):
        assert _parse("#config DECKNAME=HSK Một").deck_name == "HSK Một"

    @pytest.mark.parametrize(
        "marker, word",
        [
            ("#config deckname", "needs a value"),
            ("#config deckname=", "needs a value"),
            ("#config deckname=" + "x" * 101, "longer than"),
            ("#config deckname=A::::B", "empty level"),
            ("#config next=abc", "ending in a number"),
            ("#config next=w 15", "ending in a number"),
        ],
    )
    def test_a_bad_value_is_refused_with_a_warning(self, marker, word):
        config = _parse(marker)
        assert config.deck_name is None and config.next_id is None
        assert any(word in w for w in config.warnings), config.warnings
