"""Construction-smoke for every Qt dialog.

Instantiating each dialog runs its full ``__init__`` (``get_colors()``, the
``_setup_ui`` widget build, the shared ``theme.make_header`` banner, ``_load_*``),
catching construction-time errors that the import-only smoke in
``test_ui_import_smoke.py`` cannot. Anki/Qt are mocked by ``conftest.py``.
"""

import importlib

import pytest

DIALOGS = [
    ("add_deck_dialog", "AddDeckDialog"),
    ("disconnect_dialog", "DisconnectDialog"),
    ("settings_dialog", "SettingsDialog"),
    ("sync_dialog", "SyncDialog"),
]


@pytest.mark.unit
@pytest.mark.parametrize("module_name,class_name", DIALOGS)
def test_dialog_constructs(module_name, class_name):
    """Each dialog builds without raising (exercises __init__ + _setup_ui)."""
    module = importlib.import_module(f"src.ui.{module_name}")
    getattr(module, class_name)()


@pytest.mark.unit
def test_sync_ticks_are_saved_with_the_sync_not_on_each_click(monkeypatch):
    """Cancel has to leave the remembered selection as it was."""
    import src.config_manager as config_manager

    module = importlib.import_module("src.ui.sync_dialog")
    saved = []
    meta = {"decks": {"k": {"is_sync": True}}}
    monkeypatch.setattr(config_manager, "get_meta", lambda: meta)
    monkeypatch.setattr(config_manager, "save_meta", lambda m: saved.append(m))
    monkeypatch.setattr(module, "get_active_decks", lambda: {})

    dialog = module.SyncDialog()

    class Box:
        def __init__(self, checked):
            self.checked = checked

        def isChecked(self):  # noqa: N802 - Qt's name
            return self.checked

    dialog.deck_checkboxes = {"k": Box(False)}
    dialog.active_decks = [{"hash_key": "k", "url": "u"}]
    dialog._on_checkbox_changed("k", False)
    assert not saved

    dialog._sync_selected()
    assert saved and meta["decks"]["k"]["is_sync"] is False


@pytest.mark.unit
@pytest.mark.parametrize(
    "module_name,class_name,getter",
    [
        ("sync_dialog", "SyncDialog", "get_active_decks"),
        ("disconnect_dialog", "DisconnectDialog", "get_remote_decks"),
        ("card_layout_dialog", "CardLayoutDialog", "get_remote_decks"),
    ],
)
def test_an_empty_list_offers_to_connect_a_sheet(
    monkeypatch, module_name, class_name, getter
):
    module = importlib.import_module(f"src.ui.{module_name}")
    monkeypatch.setattr(module, getter, lambda: {})
    dialog = getattr(module, class_name)()
    assert hasattr(dialog, "connect_button")
