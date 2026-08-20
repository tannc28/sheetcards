"""
Sheets2Anki Add-on - Main Anki Integration Module

This module serves as the entry point for the Sheets2Anki Anki add-on,
integrating remote deck synchronization features with Google Sheets.

Main features:
- Python environment configuration for dependencies
- Integration with Anki user interface
- Menu creation and actions for remote deck management
- Error handling and user feedback
- Bridge between Anki interface and synchronization logic

Add-on structure:
- __init__.py: Main module (this file)
- src/: Synchronization and processing logic

Author: tannc28
Email: nguyencongtan1002.work@gmail.com
"""

# =============================================================================
# ANKI AND INTERNAL MODULE IMPORTS
# =============================================================================

# Main Anki imports with compatibility
try:
    from .src.compat import QAction
    from .src.compat import QKeySequence
    from .src.compat import QMenu
    from .src.compat import mw
    from .src.compat import safe_qconnect as qconnect
    from .src.compat import showInfo
except ImportError as e:
    # Fallback for development
    print(f"Error importing compatibility modules: {e}")
    from aqt import mw
    from aqt.qt import QAction
    from aqt.qt import QKeySequence
    from aqt.qt import QMenu
    from aqt.qt import qconnect
    from aqt.utils import showInfo

# Internal module imports with robust error handling
try:
    from .src.deck_manager import addNewDeck
    from .src.deck_manager import import_test_deck
    from .src.deck_manager import removeRemoteDeck as rDecks
    from .src.deck_manager import syncDecksWithSelection as sDecks
    from .src.templates_and_definitions import ADDON_MENU_NAME

except Exception as e:
    showInfo(f"Error importing Sheets2Anki plugin modules:\n{e}")
    raise

# =============================================================================
# TEMPLATES AND CONFIGURATIONS
# =============================================================================

# Error message template for the user
errorTemplate = """
Hello! It seems an error occurred during execution.

The error was: {}.

If you'd like me to fix it, please report here: https://github.com/tannc28/sheets2anki

Please provide as much information as possible, especially the file that caused the error.
"""

# =============================================================================
# USER INTERFACE FUNCTIONS
# =============================================================================


def addDeck():
    """
    Adds a new remote deck connected to a Google Sheets spreadsheet.

    This function:
    1. Initializes the Anki bridge
    2. Calls the interface to add a new deck
    3. Handles errors and displays appropriate feedback
    4. Ensures resource cleanup even in case of error
    """
    try:
        addNewDeck()
    except Exception as e:
        errorMessage = str(e)
        showInfo(errorTemplate.format(errorMessage))
        from .src.debug import is_debug_enabled

        if is_debug_enabled():
            import traceback

            trace = traceback.format_exc()
            showInfo(str(trace))


def syncDecks():
    """
    Synchronizes all configured remote decks.

    This function starts the synchronization process for all decks
    registered in the system, downloading updated data from
    Google Sheets spreadsheets.
    """
    try:
        sDecks()
    except Exception as e:
        error_msg = errorTemplate.format(str(e))
        showInfo(error_msg)


def removeRemote():
    """
    Removes a remote deck connection from the system.

    This function:
    1. Initializes the Anki bridge
    2. Allows the user to disconnect a remote deck
    3. Handles errors and displays appropriate feedback
    4. Ensures resource cleanup
    """
    try:
        rDecks()
    except Exception as e:
        errorMessage = str(e)
        showInfo(errorTemplate.format(errorMessage))
        from .src.debug import is_debug_enabled

        if is_debug_enabled():
            import traceback

            trace = traceback.format_exc()
            showInfo(str(trace))


def configure_deck_options_mode():
    """
    Opens the deck options mode configuration dialog.

    This function allows the user to choose between three modes:
    1. Shared - All decks use "Sheets2Anki - Default"
    2. Individual - Each deck has its own group "Sheets2Anki - [Name]"
    3. Manual - No automatic options application
    """
    try:
        from .src.ui.deck_options_config_dialog import show_deck_options_config_dialog

        show_deck_options_config_dialog(mw)
    except Exception as e:
        error_msg = errorTemplate.format(str(e))
        showInfo(error_msg)


def configure_ankiweb_sync():
    """
    Opens the AnkiWeb automatic synchronization configuration dialog.

    This function allows the user to choose between two modes:
    1. Disabled - No automatic synchronization
    2. Sync - Execute sync after deck synchronization
    """
    try:
        from .src.ui.ankiweb_sync_config_dialog import show_ankiweb_sync_config

        show_ankiweb_sync_config()
    except Exception as e:
        error_msg = errorTemplate.format(str(e))
        showInfo(error_msg)


def open_debug_mode():
    """Opens the debug mode configuration dialog."""
    try:
        from .src.ui.debug_dialog import show_debug_mode_dialog

        show_debug_mode_dialog()
    except Exception as e:
        error_msg = errorTemplate.format(str(e))
        showInfo(error_msg)


def configure_card_layout():
    """
    Opens the card layout viewer.

    The layout is declared in the spreadsheet's '#config' row, so this window is
    read-only. Per connected deck it shows:
    1. What the last sync understood for each column, and anything it could not read
    2. Which speech voices this machine has for the languages the sheet asks for
    3. An approximate preview of the resulting card
    """
    try:
        from .src.ui.card_layout_dialog import show_card_layout_dialog

        show_card_layout_dialog(mw)
    except Exception as e:
        error_msg = errorTemplate.format(str(e))
        showInfo(error_msg)



# =============================================================================
# ANKI INTERFACE CONFIGURATION
# =============================================================================

# Check if Anki is available before configuring the interface
if mw is not None:
    # Create main submenu for Sheets2Anki features
    remoteDecksSubMenu = QMenu(ADDON_MENU_NAME, mw)
    mw.form.menuTools.addMenu(remoteDecksSubMenu)

    # =========================================================================
    # MENU ACTIONS
    # =========================================================================

    # Action: Add new remote deck
    remoteDeckAction = QAction("Add New Remote Deck", mw)
    remoteDeckAction.setShortcut(QKeySequence("Ctrl+Shift+A"))
    qconnect(remoteDeckAction.triggered, addDeck)
    remoteDecksSubMenu.addAction(remoteDeckAction)

    # Action: Synchronize remote decks
    syncDecksAction = QAction("Synchronize Remote Decks", mw)
    syncDecksAction.setShortcut(QKeySequence("Ctrl+Shift+S"))
    qconnect(syncDecksAction.triggered, syncDecks)
    remoteDecksSubMenu.addAction(syncDecksAction)

    # Action: Disconnect remote deck
    removeRemoteDeck = QAction("Disconnect a Remote Deck", mw)
    removeRemoteDeck.setShortcut(QKeySequence("Ctrl+Shift+D"))
    qconnect(removeRemoteDeck.triggered, removeRemote)
    remoteDecksSubMenu.addAction(removeRemoteDeck)

    # Separator
    remoteDecksSubMenu.addSeparator()

    # Action: Configure deck options mode
    deckOptionsConfigAction = QAction("Configure Deck Options", mw)
    deckOptionsConfigAction.setShortcut(QKeySequence("Ctrl+Shift+O"))
    qconnect(deckOptionsConfigAction.triggered, configure_deck_options_mode)
    remoteDecksSubMenu.addAction(deckOptionsConfigAction)

    # Action: Configure AnkiWeb synchronization
    ankiWebSyncConfigAction = QAction("Configure AnkiWeb Sync", mw)
    ankiWebSyncConfigAction.setShortcut(QKeySequence("Ctrl+Shift+W"))
    qconnect(ankiWebSyncConfigAction.triggered, configure_ankiweb_sync)
    remoteDecksSubMenu.addAction(ankiWebSyncConfigAction)

    # Action: View card layout (declared in the sheet, so read-only)
    cardLayoutAction = QAction("View Card Layout", mw)
    cardLayoutAction.setShortcut(QKeySequence("Ctrl+Shift+C"))
    qconnect(cardLayoutAction.triggered, configure_card_layout)
    remoteDecksSubMenu.addAction(cardLayoutAction)

    # Separator
    remoteDecksSubMenu.addSeparator()

    debugModeAction = QAction("Debug Mode", mw)
    debugModeAction.setShortcut(QKeySequence("Ctrl+Shift+L"))
    qconnect(debugModeAction.triggered, open_debug_mode)
    remoteDecksSubMenu.addAction(debugModeAction)

    # Action: Import test deck (development/debug only)
    try:
        from .src.templates_and_definitions import IS_DEVELOPMENT_MODE

        if IS_DEVELOPMENT_MODE:
            importTestDeckAction = QAction("Import Test Deck", mw)
            importTestDeckAction.setShortcut(QKeySequence("Ctrl+Shift+T"))
            qconnect(importTestDeckAction.triggered, import_test_deck)
            remoteDecksSubMenu.addAction(importTestDeckAction)
    except ImportError:
        pass  # If import fails, don't show the menu
