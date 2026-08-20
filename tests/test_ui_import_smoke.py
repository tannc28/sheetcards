"""Import-smoke for every UI dialog module.

Importing each dialog exercises its module-level code (class definitions that subclass
Qt widgets, top-level imports from ``..theme`` / ``..compat`` / …). This catches
import-time breakage — a missing symbol, a bad relative import, a stripped re-export —
that the behavioral unit tests don't surface because they never import the dialogs.
Anki/Qt are mocked by ``conftest.py``.
"""

import importlib

import pytest

UI_MODULES = [
    "add_deck_dialog",
    "ankiweb_sync_config_dialog",
    "debug_dialog",
    "deck_options_config_dialog",
    "disconnect_dialog",
    "sync_dialog",
]


@pytest.mark.unit
@pytest.mark.parametrize("name", UI_MODULES)
def test_ui_module_imports(name):
    """Each src/ui/<name>.py imports without error."""
    importlib.import_module(f"src.ui.{name}")
