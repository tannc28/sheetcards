"""The add-on and Sheet to Anki's .apkg agree on which notes are which.

The unit half pins the naming rules both sides share; the real-Anki half runs
``tests/real_anki_overlap.py`` — the add-on's own sync code against a real
collection, with Anki's default import options — in both orders.
"""

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from src.apkg import declared_name
from src.apkg import resolve_identity
from src.column_model import plan_columns
from src.config_manager import get_deck_id
from src.sheet_config import parse_config_row
from src.utils import sheet_is_only
from src.utils import sheet_name_from_url
from src.utils import url_for_sheet

GID = "1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789abcd"
BASE = f"https://docs.google.com/spreadsheets/d/{GID}/edit"


@pytest.mark.unit
class TestOnlySheet:
    def test_the_only_sheet_is_marked_and_keeps_its_key(self):
        only = url_for_sheet(BASE, "Sheet1", only=True)
        plain = url_for_sheet(BASE, "Sheet1")
        assert only.endswith("#sheet=Sheet1&only=1")
        assert sheet_is_only(only) and not sheet_is_only(plain)
        assert sheet_name_from_url(only) == "Sheet1"
        # the identity Sheet to Anki keys a Google link by: id#tab
        assert get_deck_id(only) == get_deck_id(plain) == f"{GID}#Sheet1"

    def test_names_follow_the_site(self):
        from src.deck_manager import DeckNameManager

        assert DeckNameManager.sheet_remote_name("Vocab", "Sheet1", True) == "Vocab"
        assert (
            DeckNameManager.sheet_remote_name("Vocab", "Sheet1", False)
            == "Vocab::Sheet1"
        )
        assert DeckNameManager.sheet_remote_name("Vocab", None) == "Vocab"


@pytest.mark.unit
class TestDeclaredName:
    def _config(self, marker):
        return parse_config_row({"ID": marker}, plan_columns(["ID", "Word"]))

    def test_name_is_the_deck_as_written(self):
        config = self._config("#config name=  Bài 1:  chào hỏi ")
        assert declared_name(config) == "Bài 1: chào hỏi"
        sheet_id, deck, keyed = resolve_identity("x#y", "Vocab", config)
        assert (sheet_id, deck, keyed) == (
            "name:bài 1: chào hỏi",
            "Bài 1: chào hỏi",
            True,
        )

    def test_no_name_keeps_the_source(self):
        assert declared_name(self._config("#config")) is None
        assert resolve_identity("x#y", "Vocab", self._config("#config")) == (
            "x#y",
            "Vocab",
            False,
        )

    def test_the_add_on_names_the_deck_after_it(self):
        from src import deck_manager as dm

        url = url_for_sheet(BASE, "Sheet1", only=True)
        try:
            assert dm.remember_declared_name(
                url, self._config("#config name=Từ vựng: bài 1")
            ) == ("Từ vựng: bài 1")
            assert dm.DeckNameManager.extract_remote_name_from_url(url) == (
                "Từ vựng: bài 1"
            )
            # used as written: the .apkg does not clean the ':' either
            assert dm.DeckNameManager.generate_local_name("Từ vựng: bài 1") == (
                "sc_Từ vựng: bài 1"
            )
            assert dm.remember_declared_name(url, self._config("#config")) is None
        finally:
            dm._DECLARED_NAMES.clear()


_HAS_ANKI = importlib.util.find_spec("anki") is not None


@pytest.mark.slow
@pytest.mark.skipif(
    not _HAS_ANKI,
    reason="the real anki library is not installed (pip install -e '.[dev]')",
)
def test_one_set_of_notes_whichever_way_they_arrive():
    script = Path(__file__).with_name("real_anki_overlap.py")
    result = subprocess.run(
        [sys.executable, str(script)], capture_output=True, text=True, timeout=300
    )
    assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-4000:]
    assert "FAILURES: none" in result.stdout
