"""
SheetCards Add-on - Main Anki Integration Module

The entry point Anki loads: it adds a SheetCards submenu to Tools, binds the
shortcuts, and points Anki's own Add-ons -> Config button at the settings window.
Everything else lives in ``src/``.

Author: tannc28
Email: nguyencongtan1002.work@gmail.com
"""

from .src.compat import QAction
from .src.compat import QKeySequence
from .src.compat import QMenu
from .src.compat import mw
from .src.compat import safe_qconnect as qconnect
from .src.deck_manager import addNewDeck
from .src.deck_manager import import_test_deck
from .src.deck_manager import removeRemoteDeck
from .src.deck_manager import syncDecksWithSelection
from .src.templates_and_definitions import ADDON_MENU_NAME

# There is no error wrapper around these. An exception raised from a menu action
# reaches Anki's own handler, which names the add-on that raised it, shows the
# traceback behind a button and points at the add-on's page — everything the old
# "Hello! It seems an error occurred" box tried to do, done the way every other
# add-on's errors look.


def open_settings():
    """The add-on's one settings window: the AnkiWeb hand-off and the debug log."""
    from .src.ui.settings_dialog import show_settings_dialog

    show_settings_dialog(mw)


def open_card_layout():
    """What the last sync read out of each sheet's '#config' row. Read-only."""
    from .src.ui.card_layout_dialog import show_card_layout_dialog

    show_card_layout_dialog(mw)


def _action(menu, text, handler, shortcut=None):
    action = QAction(text, mw)
    if shortcut:
        action.setShortcut(QKeySequence(shortcut))
    qconnect(action.triggered, handler)
    menu.addAction(action)
    return action


if mw is not None:
    remoteDecksSubMenu = QMenu(ADDON_MENU_NAME, mw)
    mw.form.menuTools.addMenu(remoteDecksSubMenu)

    # Connecting and disconnecting carry no shortcut. Anki already owns
    # Ctrl+Shift+A (Tools -> Add-ons) and Ctrl+Shift+D (Set Due Date while
    # reviewing); a second binding makes the key ambiguous, and Qt then fires
    # neither. Both are rare enough to be reached through the menu.
    _action(remoteDecksSubMenu, "Connect a Google Sheet…", addNewDeck)
    _action(
        remoteDecksSubMenu,
        "Update Decks from Sheets…",
        syncDecksWithSelection,
        "Ctrl+Shift+S",
    )
    _action(remoteDecksSubMenu, "Disconnect a Sheet…", removeRemoteDeck)
    remoteDecksSubMenu.addSeparator()
    _action(remoteDecksSubMenu, "Card Layout…", open_card_layout, "Ctrl+Shift+C")
    remoteDecksSubMenu.addSeparator()
    _action(remoteDecksSubMenu, "Settings…", open_settings, "Ctrl+Shift+O")

    # Anki's Add-ons window has a Config button. Without this it opens the raw
    # config.json, which holds defaults only — the settings that matter live in
    # meta.json, behind the window above.
    mw.addonManager.setConfigAction(__name__, open_settings)

    from .src.templates_and_definitions import IS_DEVELOPMENT_MODE

    if IS_DEVELOPMENT_MODE:
        _action(
            remoteDecksSubMenu, "Import Test Deck", import_test_deck, "Ctrl+Shift+T"
        )
