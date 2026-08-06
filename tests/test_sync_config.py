#!/usr/bin/env python3
"""Tests for the cache of what the last sync read out of each sheet's settings row.

The cache is what lets a template rebuild that runs outside a sync (and a dialog that
only wants to *show* the settings) work without downloading the sheet again, so the
round-trip has to come back as the same ``(plan, sheet_config)`` pair the sync had.
"""

import pytest

from src import sync_config
from src.card_layout import build_templates
from src.column_model import plan_columns
from src.sheet_config import parse_config_row

SHEET_ID = "1AbC"
FIELDS = ["Word", "Reading", "Nghĩa"]


class _FakeCollection:
    """Just enough of Anki's collection config to exercise the round-trip."""

    def __init__(self):
        self.store = {}

    def get_config(self, key, default=None):
        return self.store.get(key, default)

    def set_config(self, key, value):
        self.store[key] = value


@pytest.fixture
def col(monkeypatch):
    collection = _FakeCollection()
    monkeypatch.setattr(sync_config, "_collection", lambda: collection)
    return collection


def _parsed():
    plan = plan_columns(["ID", "SYNC"] + FIELDS)
    row = {
        "ID": "#config reverse; align=left; speed=0.9",
        "Word": "size=48; tts=zh_CN; voices=Ting-Ting; bold; label=Từ",
        "Reading": "side=hide",
        "Nghĩa": "color=muted; hint; size=bogus",
    }
    return plan, parse_config_row(row, plan)


@pytest.mark.unit
class TestCacheRoundTrip:
    def test_nothing_cached_for_an_unknown_sheet(self, col):
        assert sync_config.get_sheet_snapshot(SHEET_ID) is None
        assert sync_config.cached_plan_and_config(SHEET_ID) == (None, None)

    def test_columns_and_deck_settings_survive(self, col):
        plan, config = _parsed()
        assert sync_config.cache_sheet_settings(SHEET_ID, plan, config) is True

        cached_plan, cached_config = sync_config.cached_plan_and_config(SHEET_ID)
        assert cached_plan.content_headers == FIELDS
        assert cached_config.present is True
        assert cached_config.reverse is True
        assert cached_config.align == "left"
        assert cached_config.speed == 0.9

    def test_per_field_settings_survive(self, col):
        plan, config = _parsed()
        sync_config.cache_sheet_settings(SHEET_ID, plan, config)
        _, cached = sync_config.cached_plan_and_config(SHEET_ID)

        word = cached.for_field("Word")
        assert word.size == 48
        assert word.tts == "zh_CN"
        assert word.voices == ["Ting-Ting"]
        assert word.bold is True
        assert word.label == "Từ"
        assert cached.for_field("Reading").hidden is True
        assert cached.for_field("Nghĩa").hint is True

    def test_warnings_survive_so_a_dialog_can_show_them(self, col):
        plan, config = _parsed()
        assert config.warnings  # 'size=bogus'
        sync_config.cache_sheet_settings(SHEET_ID, plan, config)
        _, cached = sync_config.cached_plan_and_config(SHEET_ID)
        assert cached.warnings == config.warnings

    def test_cached_settings_render_the_same_templates(self, col):
        plan, config = _parsed()
        sync_config.cache_sheet_settings(SHEET_ID, plan, config)
        cached_plan, cached_config = sync_config.cached_plan_and_config(SHEET_ID)

        assert build_templates(cached_plan, cached_config) == build_templates(
            plan, config
        )

    def test_forgetting_a_sheet_drops_it(self, col):
        plan, config = _parsed()
        sync_config.cache_sheet_settings(SHEET_ID, plan, config)
        assert sync_config.forget_sheet_settings(SHEET_ID) is True
        assert sync_config.get_sheet_snapshot(SHEET_ID) is None
        assert sync_config.forget_sheet_settings(SHEET_ID) is False

    def test_a_sheet_with_no_columns_yields_nothing_to_render(self, col):
        # Rendering templates from an entry with no columns would blank out the cards.
        col.store[sync_config.SETTINGS_KEY] = {SHEET_ID: {"content_headers": []}}
        assert sync_config.cached_plan_and_config(SHEET_ID) == (None, None)

    def test_the_cache_is_json_safe(self, col):
        import json

        plan, config = _parsed()
        sync_config.cache_sheet_settings(SHEET_ID, plan, config)
        # It rides AnkiWeb through the collection config, so it has to serialise.
        json.dumps(col.store[sync_config.SETTINGS_KEY])

    def test_no_collection_means_no_crash(self, monkeypatch):
        monkeypatch.setattr(sync_config, "_collection", lambda: None)
        plan, config = _parsed()
        assert sync_config.cache_sheet_settings(SHEET_ID, plan, config) is False
        assert sync_config.cached_plan_and_config(SHEET_ID) == (None, None)
