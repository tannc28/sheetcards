"""
Deck management for the Sheets2Anki addon.

This module contains functions for adding, removing, and managing
remote decks in Anki with support for automatic naming and
deck disconnection.
"""

from .compat import QInputDialog
from .compat import mw
from .config_manager import add_remote_deck
from .config_manager import create_deck_info
from .config_manager import detect_deck_name_changes
from .config_manager import disconnect_deck
from .config_manager import get_deck_local_name
from .config_manager import get_remote_decks
from .styled_messages import StyledMessageBox
from .templates_and_definitions import TEST_SHEETS_URLS
from .ui.add_deck_dialog import show_add_deck_dialog
from .ui.disconnect_dialog import show_disconnect_dialog
from .ui.sync_dialog import show_sync_dialog
from .utils import add_debug_message
from .utils import get_or_create_deck


def strip_google_title_suffix(title: str) -> str:
    """Removes the localised "Google Sheets" tail from a spreadsheet page title.

    Google serves the page title in the viewer's language — "… - Google Sheets",
    "… - Google Trang tính", "… - Google Планшети", and Portuguese's reversed
    "… - Planilhas Google" — so matching a fixed list of locales left non-English
    users with the suffix baked into their deck name. Match the shape instead: a
    trailing " - " segment that is "Google" plus up to three words, or Portuguese's
    reversed form. The word cap keeps a sheet genuinely named "Report - Google Ads
    Q3 Summary Draft" from being truncated.
    """
    if not title:
        return ""
    return re.sub(
        r"\s*-\s*(?:Google\s+\S+(?:\s+\S+){0,2}|Planilhas\s+Google)$",
        "",
        title.strip(),
        flags=re.IGNORECASE,
    ).strip()


def _without_file_extension(name: str) -> str:
    """Drops a spreadsheet file extension from a document's name.

    A Google Sheets document has no extension — one is only there because the
    document came from an uploaded file and Drive kept the name it arrived with.
    Carrying it into a deck name gives you "my-vocab-sheet.xlsx" in Anki's deck
    list, which reads like a mistake because it more or less is one.
    """
    return re.sub(r"\.(xlsx|xlsm|xls|csv|tsv)$", "", (name or "").strip(), flags=re.I)


def add_debug_msg(message, category="DECK_MANAGER"):
    """Local helper for debug messages."""
    add_debug_message(message, category)


def _delete_local_deck_data(deck_id, deck_name, url):
    """
    Completely deletes local data of a deck (deck, cards, notes, and note types).

    Args:
        deck_id: Anki deck ID
        deck_name: Deck name for logs
        url: Remote deck URL identifying note types
    """
    if not mw or not mw.col:
        return

    try:
        from .config_manager import get_deck_note_type_ids
        from .config_manager import get_deck_remote_name

        # Get note types configured for this deck
        note_types_config = get_deck_note_type_ids(url)
        remote_deck_name = get_deck_remote_name(url) or "RemoteDeck"
        add_debug_msg(f"[DEBUG] URL: {url}")
        add_debug_msg(f"[DEBUG] Remote deck name: {remote_deck_name}")
        add_debug_msg(f"[DEBUG] Configured note types: {note_types_config}")

        # 1. Identify specific note types for this deck based on configuration
        models_to_delete = []
        for note_type_id_str, note_type_name in note_types_config.items():
            try:
                note_type_id = int(note_type_id_str)
                from anki.models import NotetypeId

                model = mw.col.models.get(NotetypeId(note_type_id))

                if not model:
                    add_debug_msg(
                        f"[DEBUG] Note type ID {note_type_id} not found in Anki"
                    )
                    continue

                model_name = model["name"]
                add_debug_msg(
                    f"[DEBUG] Found note type: {model_name} (ID: {note_type_id})"
                )

                # Check if note type is used only by this deck
                notes_with_model = mw.col.find_notes(f'note:"{model_name}"')
                add_debug_msg(
                    f"[DEBUG] Checking note type '{model_name}' for deck-exclusive usage..."
                )

                # If there are notes, check if they are only from this deck
                if notes_with_model:
                    cards_from_other_decks = []
                    for note_id in notes_with_model:
                        card_ids = mw.col.card_ids_of_note(note_id)
                        for card_id in card_ids:
                            card = mw.col.get_card(card_id)
                            if card.did != deck_id:  # Card from another deck
                                cards_from_other_decks.append(card_id)

                    # If no cards from other decks, note type can be deleted
                    if not cards_from_other_decks:
                        models_to_delete.append(model)
                        add_debug_msg(
                            f"[DEBUG] Note type '{model_name}' marked for deletion"
                        )
                    else:
                        add_debug_msg(
                            f"[DEBUG] Pattern found in '{model_name}', adding to deletion list"
                        )
                else:
                    # No notes using this model, can delete
                    models_to_delete.append(model)
                    add_debug_msg(
                        f"[DEBUG] Note type '{model_name}' has no notes, marked for deletion"
                    )

            except Exception as e:
                add_debug_msg(
                    f"[DEBUG] Error checking note type {note_type_id_str}: {e}"
                )

        # 2. Delete all notes from the deck
        escaped_deck_name = deck_name.replace('"', '\\"')
        card_ids = mw.col.find_cards(f'deck:"{escaped_deck_name}"')
        add_debug_msg(f"[DEBUG] Cards found for deletion: {len(card_ids)}")
        if card_ids:
            mw.col.remove_cards_and_orphaned_notes(card_ids)

        # 3. Delete deck (this automatically removes subdecks)
        if mw.col.decks.get(deck_id):
            mw.col.decks.rem(
                deck_id, cardsToo=True
            )  # cardsToo=True forces removal of remaining cards
            add_debug_msg(f"[DEBUG] Deck {deck_name} deleted")

        # 4. Now delete identified note types
        for model in models_to_delete:
            try:
                mw.col.models.rem(model)
                add_debug_msg(
                    f"[DEBUG] Note type '{model['name']}' successfully deleted"
                )
            except Exception as e:
                add_debug_msg(
                    f"[DEBUG] Error deleting note type '{model['name']}': {e}"
                )

        # 5. Force save and UI update
        mw.col.save()
        if hasattr(mw, "deckBrowser"):
            mw.deckBrowser.refresh()
        if hasattr(mw, "reset"):
            mw.reset()  # Forces full UI reload

        add_debug_msg(f"[DEBUG] Complete deletion of deck '{deck_name}' finished")

    except Exception as e:
        # On error, continue but report
        add_debug_msg(f"Error deleting local data of deck '{deck_name}': {str(e)}")
        import traceback

        traceback.print_exc()


def _force_delete_note_types_by_suffix(suffix, remote_deck_name=None, url=None):
    """
    Forces note type deletion using stored IDs (preferred) or name patterns.
    Used as fallback if safe deletion fails.

    Args:
        suffix (str): URL hash suffix
        remote_deck_name (str, optional): Remote deck name for specific search
        url (str, optional): URL to extract additional information
    """
    if not mw or not mw.col:
        return

    try:
        # First, try to delete using stored IDs if we have the URL
        if url:
            from .utils import delete_deck_note_types_by_ids

            deleted_by_ids = delete_deck_note_types_by_ids(url)

            if deleted_by_ids > 0:
                add_debug_msg(
                    f"[FORCE DELETE] {deleted_by_ids} note types deleted using stored IDs"
                )
                # Force save and reset
                mw.col.save()
                if hasattr(mw, "reset"):
                    mw.reset()
                return

            add_debug_msg(
                "[FORCE DELETE] No note type found via IDs, trying direct method..."
            )

        # Fallback: find note types directly in Anki based on remote deck name
        from .config_manager import get_deck_remote_name

        if not remote_deck_name and url:
            remote_deck_name = get_deck_remote_name(url) or "RemoteDeck"

        add_debug_msg(
            f"[FORCE DELETE] Searching for note types for remote deck: '{remote_deck_name}'"
        )

        models_to_delete = []
        for model in mw.col.models.all():
            model_name = model["name"]

            # Check if it's a Sheets2Anki note type for THIS remote deck.
            # Note type names are "Sheets2Anki - {deck} - {Type}", so require the
            # deck name as a ' - '-delimited segment. A plain substring test
            # ("Bio" in name) would wrongly match a different deck whose name is
            # a superstring ("Biologia").
            if remote_deck_name and model_name.startswith(
                f"Sheets2Anki - {remote_deck_name} - "
            ):
                models_to_delete.append(model)
                add_debug_msg(
                    f"[FORCE DELETE] Forcing deletion of note type: {model_name}"
                )

        add_debug_msg(
            f"[FORCE DELETE] Identified {len(models_to_delete)} note types for deletion"
        )

        # Delete found note types
        for model in models_to_delete:
            try:
                mw.col.models.rem(model)
                add_debug_msg(
                    f"   Note type found: {model['name']} (ID: {model['id']})"
                )
            except Exception as e:
                add_debug_msg(
                    f"[FORCE DELETE] ❌ Error deleting note type '{model['name']}': {e}"
                )

        # Force save
        mw.col.save()
        if hasattr(mw, "reset"):
            mw.reset()

    except Exception as e:
        add_debug_msg(f"[FORCE DELETE] Error in forced deletion: {e}")


def syncDecksWithSelection():
    """
    Shows interface to select decks and syncs only selected ones.

    This function is the main entry point for interactive synchronization.
    Uses new configuration system and allows reconnection of disconnected decks.

    Note: Deck names will only be updated when user clicks 'sync selected'.
    """
    # Use new sync dialog without checking for deck name changes
    # to avoid unwanted notifications
    success, selected_urls = show_sync_dialog(mw)

    if success and selected_urls:
        # Sync only selected decks
        # Name updates will be done silently during synchronization
        from .sync import syncDecks

        syncDecks(selected_deck_urls=selected_urls)

    return


def check_and_update_deck_names(silent=False):
    """
    Checks and updates deck names in configuration.

    This function should be called regularly to ensure that
    the configuration always reflects current deck names.

    Note: Deleted decks are not automatically updated.

    Args:
        silent (bool): If True, does not show notifications

    Returns:
        list: List of URLs of updated decks
    """
    try:
        updated_urls = detect_deck_name_changes(skip_deleted=True)

        if updated_urls and not silent:
            # Show update info only if not in silent mode
            deck_names = []
            remote_decks = get_remote_decks()

            for url in updated_urls:
                # Use local_deck_name from new structure, with fallback to old deck_name
                deck_name = get_deck_local_name(url) or "Deck"
                deck_names.append(deck_name)

            if len(deck_names) == 1:
                StyledMessageBox.information(
                    None,
                    "Deck Name Updated",
                    f"The deck '{deck_names[0]}' was renamed in the configuration to match the remote source.",
                )
            else:
                names_str = "\n• " + "\n• ".join(deck_names)
                StyledMessageBox.information(
                    None,
                    "Deck Names Updated",
                    "The following decks were renamed in the configuration:",
                    detailed_text=f"• {names_str}",
                )

        return updated_urls
    except Exception as e:
        if not silent:
            StyledMessageBox.warning(
                None,
                "Error Checking Names",
                f"An error occurred while checking for deck name updates: {str(e)}",
            )
        return []


def import_test_deck():
    """
    Imports a test deck for development and demonstration.

    This function allows selecting between different pre-configured
    test spreadsheets and using the automatic naming system.
    """
    # Get test deck names list
    names = [name for name, url in TEST_SHEETS_URLS]

    # Show selection dialog
    selection, okPressed = QInputDialog.getItem(
        mw,
        "Import Test Deck",
        "Choose a test deck to import:",
        names,
        0,
        False,
    )

    if not okPressed or not selection:
        return

    # Find URL corresponding to selected deck
    url = dict(TEST_SHEETS_URLS)[selection]

    # Generate automatic deck name using DeckNameManager
    remote_name = DeckNameManager.extract_remote_name_from_url(url)
    deck_name = DeckNameManager.generate_local_name(remote_name)

    # Check if URL is already configured (remote_decks is keyed by spreadsheet id)
    from .config_manager import get_deck_id

    remote_decks = get_remote_decks()
    if get_deck_id(url) in remote_decks:
        local_name = get_deck_local_name(url) or "Deck"
        StyledMessageBox.warning(
            mw,
            "Already Configured",
            f"This test deck is already configured as '{local_name}'.",
        )
        return

    try:
        # Create deck in Anki
        deck_id, actual_name = get_or_create_deck(mw.col, deck_name)

        # Extract remote name from URL using DeckNameManager
        remote_deck_name = DeckNameManager.extract_remote_name_from_url(url)

        # Add to configuration using modular structure
        deck_info = create_deck_info(
            url=url,
            local_deck_id=deck_id,
            local_deck_name=actual_name,
            remote_deck_name=remote_deck_name,
            is_test_deck=True,
        )

        add_remote_deck(url, deck_info)

        # Synchronize deck
        from .sync import syncDecks

        syncDecks(selected_deck_urls=[url], new_deck_mode=True)

    except Exception as e:
        StyledMessageBox.critical(
            mw, "Import Error", "Error importing test deck", detailed_text=str(e)
        )
        return


def addNewDeck():
    """
    Adds a new remote deck using the new configuration system.

    This function uses the enhanced dialog that supports automatic naming,
    conflict resolution, and reconnection of disconnected decks.
    """
    # Use new add deck dialog
    success, deck_info = show_add_deck_dialog(mw)

    if success and deck_info:
        # One link connects every sheet in the file, so this is a list. Older
        # callers stored a single "url"; keep reading that when "urls" is absent.
        urls = deck_info.get("urls") or [deck_info["url"]]
        from .sync import syncDecks

        syncDecks(selected_deck_urls=urls)


def removeRemoteDeck():
    """
    Removes remote decks from configuration using checkbox interface.

    This function uses the new disconnect dialog that allows selecting
    multiple decks for simultaneous disconnection, while keeping local decks.
    """
    # Use new disconnect dialog
    success, selected_urls, delete_local_data = show_disconnect_dialog(mw)

    if success and selected_urls:
        # Process disconnection of selected decks
        disconnected_decks = []

        for url in selected_urls:
            # The key this deck is stored under. Not the bare spreadsheet id:
            # several decks can live in one file, and disconnecting one of them
            # has to find that one.
            from .config_manager import get_deck_id

            spreadsheet_id = get_deck_id(url)

            remote_decks = get_remote_decks()
            if spreadsheet_id in remote_decks:
                deck_info = remote_decks[spreadsheet_id]
                deck_id = deck_info["local_deck_id"]
                deck = None
                # Check if collection and deck manager are available
                if mw and mw.col and mw.col.decks:
                    deck = mw.col.decks.get(deck_id)
                deck_name = (
                    deck["name"]
                    if deck
                    else (get_deck_local_name(url) or "Unknown Deck")
                )

                # If local data should be deleted, do it before disconnection
                if delete_local_data and deck:
                    _delete_local_deck_data(deck_id, deck_name, url)

                    # Fallback: try forced deletion of note types
                    try:
                        from .config_manager import get_deck_remote_name
                        from .utils import get_model_suffix_from_url

                        suffix = get_model_suffix_from_url(url)
                        remote_deck_name = get_deck_remote_name(url)
                        _force_delete_note_types_by_suffix(
                            suffix, remote_deck_name, url
                        )
                    except Exception as fallback_error:
                        add_debug_msg(f"[DEBUG] Fallback also failed: {fallback_error}")

                # Disconnect deck
                disconnect_deck(url)
                disconnected_decks.append(deck_name)

        # Clean up orphaned deck option groups after disconnecting decks
        # This removes any Sheets2Anki deck options that are no longer linked to any local decks
        from .utils import cleanup_orphaned_deck_option_groups

        cleaned_options = cleanup_orphaned_deck_option_groups()
        if cleaned_options > 0:
            add_debug_msg(f"Cleaned up {cleaned_options} orphaned deck option group(s)")

        # Show success message
        if len(disconnected_decks) == 1:
            if delete_local_data:
                message = (
                    f"The deck '{disconnected_decks[0]}' was disconnected and all local data was deleted.\n\n"
                    f"Deleted data:\n"
                    f"• Local deck and subdecks\n"
                    f"• All cards and notes\n"
                    f"• Specific note types (if not used in other decks)\n\n"
                    f"To reconnect, you will need to add it again."
                )
            else:
                message = (
                    f"The deck '{disconnected_decks[0]}' was disconnected from its remote source.\n\n"
                    f"The local deck remains in Anki and can be managed normally.\n"
                    f"To reconnect, you will need to add it again."
                )
        else:
            decks_formatted = "\n• " + "\n• ".join(disconnected_decks)
            if delete_local_data:
                message = (
                    f"The following decks were disconnected and all local data was deleted:{decks_formatted}\n\n"
                    f"Deleted data for each deck:\n"
                    f"• Local decks and subdecks\n"
                    f"• All cards and notes\n"
                    f"• Specific note types (if not used in other decks)\n\n"
                    f"To reconnect, you will need to add them again."
                )
            else:
                message = (
                    f"The following decks were disconnected from their remote sources:{decks_formatted}\n\n"
                    f"The local decks remain in Anki and can be managed normally.\n"
                    f"To reconnect, you will need to add them again."
                )

        StyledMessageBox.success(
            mw,
            "Decks Disconnected",
            "Selected decks have been disconnected.",
            detailed_text=message,
        )

    return


# =============================================================================
# DECK NAME MANAGEMENT (formerly deck_name_manager.py)
# =============================================================================

import re
from typing import Any

from .templates_and_definitions import DEFAULT_PARENT_DECK_NAME


class DeckNameManager:
    """
    Centralized class to manage all aspects of deck naming.

    This class unifies and replaces all scattered logic of:
    - extracting names from URLs
    - conflict resolution
    - configuration synchronization
    - automatic name update
    - hierarchical name generation
    """

    # =============================================================================
    # NAME EXTRACTION AND GENERATION METHODS
    # =============================================================================

    @staticmethod
    def extract_remote_name_from_url(url: str) -> str:
        """
        Extracts remote deck name using multiple strategies.

        Args:
            url: Google Sheets URL

        Returns:
            Extracted remote name or fallback
        """
        try:
            # Strategy 1: Spreadsheet title via HTML
            title = DeckNameManager._extract_spreadsheet_title(url)
            if title and title != "auto name fail":
                return DeckNameManager._with_sheet(url, title)

            # Strategy 2: Filename via Content-Disposition
            filename = DeckNameManager._extract_filename_from_headers(url)
            if filename and filename != "auto name fail":
                return DeckNameManager._with_sheet(url, filename)

            # Strategy 3: Fallback to spreadsheet ID and GID
            return DeckNameManager._generate_fallback_name(url)

        except Exception:
            return "auto name fatal fail"

    @staticmethod
    def _with_sheet(url: str, file_name: str) -> str:
        """``{file}::{sheet}`` when the deck names a sheet, else just the file.

        Every deck of one file would otherwise be called after the file, and the
        automatic name sync — which recomputes this on each run — would rename
        them all onto one another and then push them apart with "#conflict1".
        """
        from .utils import sheet_name_from_url

        name = DeckNameManager.clean_name(_without_file_extension(file_name))
        sheet = sheet_name_from_url(url)
        return f"{name}::{DeckNameManager.clean_name(sheet)}" if sheet else name

    @staticmethod
    def generate_local_name(
        remote_name: str, parent_name: str = DEFAULT_PARENT_DECK_NAME
    ) -> str:
        """
        Generates hierarchical local name: {parent}::{remote_name}

        Args:
            remote_name: Remote deck name
            parent_name: Parent deck name

        Returns:
            Local name in hierarchical format
        """
        if not remote_name:
            return f"{parent_name}::UnknownDeck"

        clean_remote_name = DeckNameManager.clean_name(remote_name)
        return f"{parent_name}::{clean_remote_name}"

    @staticmethod
    def generate_complete_names(url: str) -> tuple[str, str]:
        """
        Generates both local and remote name for a URL.

        Args:
            url: Google Sheets URL

        Returns:
            Tuple (local_name, remote_name)
        """
        remote_name = DeckNameManager.extract_remote_name_from_url(url)
        local_name = DeckNameManager.generate_local_name(remote_name)
        return local_name, remote_name

    # =============================================================================
    # CONFLICT RESOLUTION METHODS
    # =============================================================================

    @staticmethod
    def resolve_remote_name_conflict(url: str, remote_name: str) -> str:
        """
        Resolves remote name conflicts centrally.

        Args:
            url: Deck URL (for unique identification)
            remote_name: Proposed remote name

        Returns:
            Resolved remote name (may have #conflict suffix if necessary)
        """
        if not remote_name:
            return "RemoteDeck"

        clean_name = remote_name.strip()
        if not clean_name:
            return "RemoteDeck"

        # Get all existing remote names (except current deck)
        existing_names = DeckNameManager._get_existing_remote_names(exclude_url=url)

        # If no conflict, use original name
        if clean_name not in existing_names:
            return clean_name

        # Resolve conflict with suffix
        conflict_index = 1
        while conflict_index <= 100:
            candidate_name = f"{clean_name} #conflict{conflict_index}"
            if candidate_name not in existing_names:
                return candidate_name
            conflict_index += 1

        # Fallback if unable to resolve
        return f"{clean_name} #conflict{conflict_index}"

    @staticmethod
    def resolve_local_name_conflict(local_name: str) -> str:
        """
        Resolves local name conflicts in Anki.

        Args:
            local_name: Proposed local name

        Returns:
            Unique local name (may have _X suffix if necessary)
        """
        if not DeckNameManager._check_anki_name_conflict(local_name):
            return local_name

        # Add numeric suffix
        counter = 2
        while counter <= 100:
            candidate_name = f"{local_name}_{counter}"
            if not DeckNameManager._check_anki_name_conflict(candidate_name):
                return candidate_name
            counter += 1

        # Fallback with timestamp
        import time

        timestamp = int(time.time())
        return f"{local_name}_{timestamp}"

    # =============================================================================
    # SYNCHRONIZATION AND UPDATE METHODS
    # =============================================================================

    @staticmethod
    def sync_deck_with_config(
        deck_url: str, debug_callback=None
    ) -> tuple[int, str] | None:
        """
        Syncs deck name in Anki with configuration (source of truth).

        Args:
            deck_url: Remote deck URL
            debug_callback: Debug callback function (optional)

        Returns:
            Tuple (deck_id, synced_name) or None if error
        """
        from .config_manager import get_deck_local_id
        from .config_manager import get_deck_local_name

        def debug(message: str):
            if debug_callback:
                debug_callback(f"[DECK_SYNC] {message}")

        try:
            # Get info from meta.json
            local_deck_id = get_deck_local_id(deck_url)
            expected_name = get_deck_local_name(deck_url)

            if not local_deck_id or not expected_name:
                debug(
                    f"Deck not found in configuration: ID={local_deck_id}, Name='{expected_name}'"
                )
                return None

            # Check if deck exists in Anki
            if not mw or not mw.col:
                debug("Anki not available")
                return None

            from anki.decks import DeckId

            deck = mw.col.decks.get(DeckId(local_deck_id))
            if not deck:
                debug(f"❌ ERROR: Deck ID {local_deck_id} does not exist in Anki")
                return None

            current_name = deck["name"]
            debug(f"Current name: '{current_name}' -> Expected: '{expected_name}'")

            # Sync if necessary
            if current_name != expected_name:
                debug(f"📝 Updating name: '{current_name}' -> '{expected_name}'")
                deck["name"] = expected_name
                mw.col.decks.save(deck)
                debug("✅ Name successfully updated")
                return (local_deck_id, expected_name)
            else:
                debug("✅ Name already synchronized")
                return (local_deck_id, current_name)

        except Exception as e:
            debug(f"❌ ERROR in synchronization: {e}")
            return None

    @staticmethod
    def update_deck_names_automatically(
        deck_url: str,
        deck_id: int,
        current_local_name: str,
        remote_name: str | None = None,
        debug_callback=None,
    ) -> str:
        """
        Updates deck names automatically if necessary.

        This function centralizes all automatic name update logic.

        Args:
            deck_url: Deck URL
            deck_id: Anki deck ID
            current_local_name: Current local name
            remote_name: Remote name (if already known)
            debug_callback: Debug function

        Returns:
            Final local name (updated or maintained)
        """

        def debug(message: str):
            if debug_callback:
                debug_callback(f"[NAME_UPDATE] {message}")

        try:
            # Get remote name if not provided
            if not remote_name:
                remote_name = DeckNameManager.extract_remote_name_from_url(deck_url)

            # Generate desired local name
            desired_local_name = DeckNameManager.generate_local_name(remote_name)
            debug(
                f"Desired name: '{desired_local_name}' (current: '{current_local_name}')"
            )

            # Check if update is needed
            if not DeckNameManager._should_update_name(
                current_local_name, desired_local_name
            ):
                debug("No update needed")
                return current_local_name

            # Get available name
            available_name = DeckNameManager.resolve_local_name_conflict(
                desired_local_name
            )
            debug(f"Available name: '{available_name}'")

            # Update in Anki
            success = DeckNameManager._update_deck_in_anki(deck_id, available_name)
            if success:
                # Update in configuration
                DeckNameManager._update_name_in_config(deck_url, available_name)
                debug(f"✅ Name updated to: '{available_name}'")
                return available_name
            else:
                debug("❌ Failed to update in Anki")
                return current_local_name

        except Exception as e:
            debug(f"❌ ERROR in update: {e}")
            return current_local_name

    @staticmethod
    def create_deck_with_proper_naming(
        deck_url: str, suggested_remote_name: str | None = None
    ) -> tuple[int, str, str]:
        """
        Creates a deck with proper naming and resolves all conflicts.

        This function centralizes all logic used in add_deck_dialog.py.

        Args:
            deck_url: Deck URL
            suggested_remote_name: Suggested remote name (optional)

        Returns:
            Tuple (deck_id, final_local_name, final_remote_name)
        """
        # Get final remote name
        if suggested_remote_name:
            final_remote_name = DeckNameManager.resolve_remote_name_conflict(
                deck_url, suggested_remote_name
            )
        else:
            extracted_name = DeckNameManager.extract_remote_name_from_url(deck_url)
            final_remote_name = DeckNameManager.resolve_remote_name_conflict(
                deck_url, extracted_name
            )

        # Generate hierarchical local name
        desired_local_name = DeckNameManager.generate_local_name(final_remote_name)
        final_local_name = DeckNameManager.resolve_local_name_conflict(
            desired_local_name
        )

        # Create deck in Anki
        from .utils import get_or_create_deck

        deck_id, actual_name = get_or_create_deck(mw.col, final_local_name)

        return deck_id, actual_name, final_remote_name

    # =============================================================================
    # PRIVATE/INTERNAL METHODS
    # =============================================================================

    @staticmethod
    def _get_existing_remote_names(exclude_url: str | None = None) -> set:
        """Gets all existing remote names."""
        from .config_manager import get_remote_decks

        existing_names = set()
        remote_decks = get_remote_decks()

        for deck_url, deck_info in remote_decks.items():
            # Skip current deck if specified
            if exclude_url and deck_info.get("remote_deck_url") == exclude_url:
                continue

            remote_name = deck_info.get("remote_deck_name", "")
            if remote_name:
                existing_names.add(remote_name)

        return existing_names

    @staticmethod
    def _check_anki_name_conflict(name: str) -> bool:
        """Checks if there is a name conflict in Anki."""
        try:
            if mw and mw.col and mw.col.decks:
                existing_deck = mw.col.decks.by_name(name)
                return existing_deck is not None
            return False
        except Exception:
            return False

    @staticmethod
    def _should_update_name(current_name: str, desired_name: str) -> bool:
        """Determines whether to update the name."""
        if not current_name or not desired_name:
            return False

        # Extract base name (without numeric suffix)
        has_suffix, base_name, _ = DeckNameManager._extract_numeric_suffix(current_name)
        comparison_name = base_name if has_suffix else current_name

        return desired_name.lower() != comparison_name.lower()

    @staticmethod
    def _extract_numeric_suffix(name: str) -> tuple[bool, str, int | None]:
        """Extracts numeric suffix from name."""
        suffix_match = re.search(r"_(\d+)$", name)
        if suffix_match:
            suffix_number = int(suffix_match.group(1))
            base_name = name[: suffix_match.start()]
            return True, base_name, suffix_number
        return False, name, None

    @staticmethod
    def _update_deck_in_anki(deck_id: int, new_name: str) -> bool:
        """Updates deck name in Anki."""
        try:
            if mw and mw.col and mw.col.decks:
                from anki.decks import DeckId

                deck = mw.col.decks.get(DeckId(deck_id))
                if deck:
                    deck["name"] = new_name
                    mw.col.decks.save(deck)
                    return True
            return False
        except Exception:
            return False

    @staticmethod
    def _update_name_in_config(deck_url: str, new_name: str) -> bool:
        """Updates name in configuration."""
        try:
            from .config_manager import get_deck_id
            from .config_manager import get_meta
            from .config_manager import save_meta

            meta = get_meta()
            spreadsheet_id = get_deck_id(deck_url)

            if "decks" in meta and spreadsheet_id in meta["decks"]:
                meta["decks"][spreadsheet_id]["local_deck_name"] = new_name
                save_meta(meta)
                return True
            return False
        except Exception:
            return False

    # =============================================================================
    # SPECIFIC CLEANING AND EXTRACTION METHODS
    # =============================================================================

    @staticmethod
    def clean_name(name: str) -> str:
        """Cleans and normalizes a deck name."""
        if not name:
            return "auto name fatal fail"

        name = str(name).strip()

        # Remove " - Google Drive" or " - Google Sheets" suffix
        name = re.sub(
            r"\s*-\s*Google\s+(Drive|Sheets)\s*$", "", name, flags=re.IGNORECASE
        )

        # Remove problematic characters, but keep spaces — and keep "::", which is
        # not a problematic character here but Anki's own separator between a deck
        # and its parent. A deck of one sheet of a file is named "{file}::{sheet}",
        # and flattening that to "{file}__{sheet}" makes the registered deck's name
        # disagree with the name notes are actually filed under, which ends with
        # Anki uniquifying one of them into "…vocab+".
        name = name.replace("::", "\x00")
        name = re.sub(r'[<>:"/\\|?*]', "_", name)
        name = name.replace("\x00", "::")

        if not name:
            return "auto name fatal fail"

        # Limit length
        if len(name) > 100:
            name = name[:100]

        return name

    @staticmethod
    def _extract_spreadsheet_title(url: str) -> str | None:
        """Extracts spreadsheet title via HTML."""
        try:
            import urllib.parse
            import urllib.request

            # Build URL for metadata
            base_url = (
                url.replace("&output=tsv", "")
                .replace("?output=tsv", "")
                .replace("&single=true", "")
            )
            parsed = urllib.parse.urlparse(base_url)
            query_params = urllib.parse.parse_qs(parsed.query)

            # Keep only gid if it exists
            filtered_params = {}
            if "gid" in query_params:
                filtered_params["gid"] = query_params["gid"]

            new_query = urllib.parse.urlencode(filtered_params, doseq=True)
            meta_url = urllib.parse.urlunparse(
                (
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    parsed.params,
                    new_query,
                    parsed.fragment,
                )
            )

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }

            request = urllib.request.Request(meta_url, headers=headers)

            with urllib.request.urlopen(request, timeout=15) as response:
                html = response.read().decode("utf-8", errors="ignore")

                # Multiple patterns to extract title
                title_patterns = [
                    # Google serves the page title localised — "… - Google Sheets",
                    # "… - Google Trang tính", "… - Google Планшети" — so match the
                    # "Google <anything>" tail generically rather than listing locales.
                    r"<title>([^<]+?)\s*-\s*(?:Google\s+|Planilhas\s+Google)[^<]{0,30}</title>",
                    r"<title>([^<]+)</title>",
                    r'"title":"([^"]+)"',
                    r'<meta property="og:title" content="([^"]+)"',
                    r'"doc-name":"([^"]+)"',
                ]

                for pattern in title_patterns:
                    match = re.search(pattern, html, re.IGNORECASE)
                    if match:
                        title = match.group(1).strip()

                        # Clean additional suffixes that may have escaped the regex
                        # Same tail, for titles that came from a pattern other
                        # than the first one above.
                        title = strip_google_title_suffix(title)

                        if title and title.lower() not in [
                            "untitled",
                            "sem título",
                            "planilha sem título",
                        ]:
                            return title

                return None

        except Exception:
            return None

    @staticmethod
    def _extract_filename_from_headers(url: str) -> str | None:
        """Extracts filename via headers."""
        try:
            import urllib.request

            headers = {"User-Agent": "Mozilla/5.0 (Sheets2Anki) AnkiAddon"}
            request = urllib.request.Request(url, headers=headers)

            with urllib.request.urlopen(request, timeout=10) as response:
                content_disposition = response.headers.get("Content-Disposition", "")
                if content_disposition:
                    match = re.search(
                        r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', content_disposition
                    )
                    if match:
                        filename = match.group(1).strip("\"'")
                        if filename:
                            if filename.lower().endswith(".tsv"):
                                filename = filename[:-4]
                            return filename

                return None

        except Exception:
            return None

    @staticmethod
    def _generate_fallback_name(url: str) -> str:
        """Generates fallback name based on spreadsheet ID."""
        try:
            from urllib.parse import parse_qs
            from urllib.parse import urlparse

            # Extract spreadsheet ID
            match = re.search(r"/spreadsheets/d/e/([a-zA-Z0-9-_]+)", url)
            if not match:
                match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)

            if match:
                spreadsheet_id = match.group(1)

                # Extract GID
                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)
                gid = query_params.get("gid", ["0"])[0]

                if gid != "0":
                    return f"Spreadsheet {spreadsheet_id[:8]} - Tab {gid}"
                else:
                    return f"Spreadsheet {spreadsheet_id[:8]} - Main Tab"

            return "External Spreadsheet"

        except Exception:
            return "auto name fatal fail"


# =============================================================================
# SUBDECK MANAGEMENT (formerly subdeck_manager.py)
# =============================================================================

# =============================================================================
# DECK RECREATION (formerly deck_recreation.py)
# =============================================================================


class DeckRecreationManager:
    """Manager for recreating deleted decks."""

    @staticmethod
    def recreate_deck_if_missing(
        deck_info: dict[str, Any],
    ) -> tuple[bool, int | None, str | None]:
        """
        Recreates a deck if it is missing.

        Args:
            deck_info: Deck info from configuration

        Returns:
            Tuple[bool, Optional[int], Optional[str]]:
            (was_recreated, new_deck_id, current_name)
        """
        from .utils import add_debug_message

        # Check if mw and col are available
        if not mw or not mw.col:
            raise ValueError("Anki is not available")

        local_deck_id = deck_info.get("local_deck_id")
        add_debug_message(
            f"🔍 Checking deck with ID: {local_deck_id}", "DECK_RECREATION"
        )

        # Check if deck exists
        deck = mw.col.decks.get(local_deck_id) if local_deck_id is not None else None

        if deck:
            deck_name = deck.get("name", "")
            expected_name = deck_info.get("local_deck_name", "")

            add_debug_message(
                f"📋 Deck found: '{deck_name}' (ID: {local_deck_id})",
                "DECK_RECREATION",
            )
            add_debug_message(f"📋 Expected name: '{expected_name}'", "DECK_RECREATION")

            # Check if it's really the correct deck or if it was renamed/changed
            if deck_name == expected_name or expected_name in deck_name:
                add_debug_message("✅ Deck exists and name matches", "DECK_RECREATION")
                return False, local_deck_id, deck_name
            else:
                add_debug_message(
                    f"⚠️ WARNING: Deck exists but name changed: '{deck_name}' != '{expected_name}'",
                    "DECK_RECREATION",
                )
                add_debug_message(
                    "🔧 Considering as deck to be recreated due to name inconsistency",
                    "DECK_RECREATION",
                )
                # Continue to recreation
        else:
            add_debug_message(
                f"❌ Deck with ID {local_deck_id} not found", "DECK_RECREATION"
            )

        # Deck does not exist or was changed, need to recreate
        add_debug_message(
            "⚠️ Local deck was deleted or changed, starting recreation",
            "DECK_RECREATION",
        )

        try:
            new_deck_id, actual_name = DeckRecreationManager._create_new_deck(deck_info)

            # Apply Sheets2Anki options to recreated deck
            from .utils import apply_sheets2anki_options_to_deck

            remote_deck_name = deck_info.get("remote_deck_name")
            try:
                apply_sheets2anki_options_to_deck(new_deck_id, remote_deck_name)
                add_debug_message(
                    f"✅ Options applied to recreated deck: {actual_name}",
                    "DECK_RECREATION",
                )
            except Exception as e:
                add_debug_message(
                    f"⚠️ Failed to apply options to recreated deck: {e}",
                    "DECK_RECREATION",
                )

            add_debug_message(
                f"✅ Deck successfully recreated: {actual_name} (ID: {new_deck_id})",
                "DECK_RECREATION",
            )
            return True, new_deck_id, actual_name

        except Exception as e:
            add_debug_message(f"❌ Error recreating deck: {e}", "DECK_RECREATION")
            raise

    @staticmethod
    def _create_new_deck(deck_info: dict[str, Any]) -> tuple[int, str]:
        """
        Creates a new deck based on provided information.

        Args:
            deck_info: Deck info

        Returns:
            Tuple[int, str]: (deck_id, current_name)
        """
        from .utils import add_debug_message

        # Check if mw and col are available
        if not mw or not mw.col:
            raise ValueError("Anki is not available")

        # Determine desired deck name
        current_remote_name = deck_info.get("remote_deck_name")

        if current_remote_name:
            desired_local_name = DeckNameManager.generate_local_name(
                current_remote_name
            )
        else:
            # Fallback to name saved in configuration
            local_deck_id = deck_info.get("local_deck_id")
            desired_local_name = (
                deck_info.get("local_deck_name") or f"Sheets2Anki::Deck_{local_deck_id}"
            )

        add_debug_message(
            f"🎯 Desired name for recreation: {desired_local_name}", "DECK_RECREATION"
        )

        # Check if a deck with this name already exists before creating
        existing_deck = mw.col.decks.by_name(desired_local_name)

        if existing_deck:
            # Deck already exists, use existing one
            new_deck_id = existing_deck["id"]
            actual_name = existing_deck["name"]
            add_debug_message(
                f"📂 Using existing deck: {actual_name} (ID: {new_deck_id})",
                "DECK_RECREATION",
            )
        else:
            # Deck does not exist, create new one
            try:
                add_debug_message(
                    f"🆕 Creating new deck: '{desired_local_name}'", "DECK_RECREATION"
                )
                new_deck_id = mw.col.decks.id(desired_local_name)
                add_debug_message(
                    f"🆔 ID returned by Anki API: {new_deck_id} (type: {type(new_deck_id)})",
                    "DECK_RECREATION",
                )

                # Check if deck was correctly created
                if new_deck_id is None:
                    raise ValueError(f"Failed to create deck: {desired_local_name}")

                # Check if name was kept or changed by Anki
                new_deck = mw.col.decks.get(new_deck_id)
                if not new_deck:
                    raise ValueError(
                        f"Failed to obtain created deck: {desired_local_name}"
                    )

                actual_name = new_deck["name"]
                add_debug_message(
                    f"✅ Deck confirmed in Anki: '{actual_name}' (ID: {new_deck_id})",
                    "DECK_RECREATION",
                )

                if actual_name != desired_local_name:
                    add_debug_message(
                        f"📝 Name changed during creation: {desired_local_name} -> {actual_name}",
                        "DECK_RECREATION",
                    )

                add_debug_message(
                    f"🆕 New deck created: {actual_name} (ID: {new_deck_id})",
                    "DECK_RECREATION",
                )

            except Exception:
                # On error, use unique name based on timestamp
                import time

                unique_suffix = str(int(time.time()))[-6:]
                fallback_name = f"Sheets2Anki::Deck_{unique_suffix}"

                add_debug_message(
                    f"🔄 Creating with fallback name: {fallback_name}",
                    "DECK_RECREATION",
                )

                new_deck_id = mw.col.decks.id(fallback_name)
                if new_deck_id is None:
                    raise ValueError(
                        f"Failed to create deck with fallback name: {fallback_name}"
                    )

                new_deck = mw.col.decks.get(new_deck_id)

                if not new_deck:
                    raise ValueError(
                        f"Failed to obtain deck with fallback name: {fallback_name}"
                    )

                actual_name = new_deck["name"]

        return int(new_deck_id), str(actual_name)

    @staticmethod
    def update_deck_info_after_recreation(
        deck_info: dict[str, Any], new_deck_id: int, actual_name: str
    ) -> None:
        """
        Updates deck info after recreation.

        Args:
            deck_info: Deck info (will be modified in-place)
            new_deck_id: New deck ID
            actual_name: Current deck name
        """
        from .utils import add_debug_message

        old_deck_id = deck_info.get("local_deck_id")

        if new_deck_id != old_deck_id:
            add_debug_message(
                f"🔄 Updating deck ID: {old_deck_id} -> {new_deck_id}",
                "DECK_RECREATION",
            )
            deck_info["local_deck_id"] = new_deck_id
            add_debug_message(
                f"✅ Confirmation: deck_info['local_deck_id'] now = {deck_info['local_deck_id']}",
                "DECK_RECREATION",
            )

        old_name = deck_info.get("local_deck_name", "")
        if actual_name != old_name:
            add_debug_message(
                f"📝 Updating deck name: '{old_name}' -> '{actual_name}'",
                "DECK_RECREATION",
            )
            deck_info["local_deck_name"] = actual_name
