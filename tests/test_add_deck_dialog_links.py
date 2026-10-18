"""The Add dialog's pointer to something to start from, and its link check.

The example workbook's address is written in one more place now; it has to be
the same file the README, the site and the dev-only test deck point at (which
``tests/test_examples.py`` pins), or a first-time user is sent to a workbook
that is not the one everything else describes.
"""

import pytest

from src.templates_and_definitions import TEST_SHEETS_URLS
from src.ui import add_deck_dialog


@pytest.mark.unit
class TestStarterLinks:
    def test_the_workbook_is_the_published_one(self):
        assert [url for _, url in TEST_SHEETS_URLS] == [
            add_deck_dialog.EXAMPLE_WORKBOOK_URL
        ]

    def test_both_links_are_in_the_line(self):
        html = add_deck_dialog.starter_links_html()
        assert f'href="{add_deck_dialog.EXAMPLE_WORKBOOK_URL}"' in html
        assert 'href="https://tannc28.github.io/sheetcards/create/"' in html
        assert html.startswith("Need a sheet to start from?")


class _Field:
    def __init__(self, text):
        self._text = text

    def text(self):
        return self._text


@pytest.mark.unit
class TestAStaleAnswerIsDropped:
    """A slow check about a link the reader has since changed paints nothing."""

    def _dialog(self, text, generation):
        dialog = add_deck_dialog.AddDeckDialog.__new__(add_deck_dialog.AddDeckDialog)
        dialog.url_edit = _Field(text)
        dialog._check_generation = generation
        dialog._closed = False
        return dialog

    def test_current(self):
        dialog = self._dialog("https://a", 3)
        assert not dialog._is_stale(3, "https://a")

    def test_a_newer_check_has_started(self):
        assert self._dialog("https://a", 4)._is_stale(3, "https://a")

    def test_the_field_has_changed(self):
        assert self._dialog("https://b", 3)._is_stale(3, "https://a")

    def test_the_window_has_closed(self):
        dialog = self._dialog("https://a", 3)
        dialog._closed = True
        assert dialog._is_stale(3, "https://a")

    def test_the_answer_is_not_applied(self):
        dialog = self._dialog("https://b", 3)
        # Would raise on the missing widgets if it went any further.
        dialog._on_link_read(3, "https://a", ([], "name"))
        dialog._on_link_failed(3, "https://a", RuntimeError("late"))
