#!/usr/bin/env python3
"""Tests for cleaning the Google Sheets page title into a deck name.

Google localises the page title, so a fixed list of locales left non-English users
with the suffix baked into their deck name — "HSK4 - Google Trang tính" instead of
"HSK4". These lock in the shape-based match that replaced it.
"""

import pytest

from src.deck_manager import strip_google_title_suffix


@pytest.mark.unit
class TestStripGoogleTitleSuffix:
    @pytest.mark.parametrize(
        "title,expected",
        [
            ("Vocabulary - Google Sheets", "Vocabulary"),
            ("HSK4 - Google Trang tính", "HSK4"),  # Vietnamese
            ("Vocab - Google Планшети", "Vocab"),  # Ukrainian
            ("Wortschatz - Google Tabellen", "Wortschatz"),  # German
            ("Planilha - Planilhas Google", "Planilha"),  # Portuguese, reversed
            ("  Spaced  - Google Sheets  ", "Spaced"),
        ],
    )
    def test_localised_suffixes_are_removed(self, title, expected):
        assert strip_google_title_suffix(title) == expected

    @pytest.mark.parametrize(
        "title",
        [
            "My Google Ads Report",  # "Google" mid-title, no " - " segment
            "Notes about Google",
            "Q3 - Google",  # bare "Google" is not a product name
            "Plain deck name",
        ],
    )
    def test_unrelated_titles_are_left_alone(self, title):
        assert strip_google_title_suffix(title) == title.strip()

    def test_long_trailing_segment_is_not_truncated(self):
        # The word cap exists so a sheet genuinely named after a Google product
        # keeps its name.
        title = "Report - Google Ads Q3 Summary Draft"
        assert strip_google_title_suffix(title) == title

    @pytest.mark.parametrize("value", ["", None])
    def test_empty_input_is_safe(self, value):
        assert strip_google_title_suffix(value) == ""
