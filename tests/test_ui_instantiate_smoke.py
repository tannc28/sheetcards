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
    ("ankiweb_sync_config_dialog", "AnkiWebSyncConfigDialog"),
    ("backup_dialog", "BackupDialog"),
    ("debug_dialog", "DebugModeDialog"),
    ("deck_options_config_dialog", "DeckOptionsConfigDialog"),
    ("disconnect_dialog", "DisconnectDialog"),
    ("image_processor_config_dialog", "ImageProcessorConfigDialog"),
    ("sync_dialog", "SyncDialog"),
]


@pytest.mark.unit
@pytest.mark.parametrize("module_name,class_name", DIALOGS)
def test_dialog_constructs(module_name, class_name):
    """Each dialog builds without raising (exercises __init__ + _setup_ui)."""
    module = importlib.import_module(f"src.ui.{module_name}")
    getattr(module, class_name)()
