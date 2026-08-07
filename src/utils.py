"""
Utility functions for the Sheets2Anki addon.

This module contains auxiliary functions used in
different parts of the project.
"""

import hashlib
import re
from datetime import datetime

try:
    from .compat import mw
except ImportError:
    # For independent tests
    from compat import mw


# --- Re-exported from the modules split out of this file (back-compat facade) ---
from .debug import DebugManager  # noqa: F401
from .debug import add_debug_message  # noqa: F401
from .debug import clear_debug_log  # noqa: F401
from .debug import clear_debug_messages  # noqa: F401
from .debug import get_debug_log_path  # noqa: F401
from .debug import get_debug_messages  # noqa: F401
from .debug import initialize_debug_log  # noqa: F401
from .debug import is_debug_enabled  # noqa: F401
from .deck_options import _is_default_config  # noqa: F401
from .deck_options import apply_automatic_deck_options_system  # noqa: F401
from .deck_options import apply_options_to_subdecks  # noqa: F401
from .deck_options import apply_sheets2anki_options_to_all_remote_decks  # noqa: F401
from .deck_options import apply_sheets2anki_options_to_deck  # noqa: F401
from .deck_options import cleanup_orphaned_deck_option_groups  # noqa: F401
from .deck_options import ensure_root_deck_has_root_options  # noqa: F401
from .deck_options import get_or_create_root_options_group  # noqa: F401
from .deck_options import get_or_create_sheets2anki_options_group  # noqa: F401
from .errors import CollectionSaveError  # noqa: F401
from .errors import ConfigurationError  # noqa: F401
from .errors import NoteProcessingError  # noqa: F401
from .errors import SyncError  # noqa: F401


def safe_find_cards(search_query):
    """
    Performs a safe card search, escaping problematic characters.

    Args:
        search_query (str): Search query

    Returns:
        list: List of IDs of found cards
    """
    try:
        if not mw or not mw.col:
            return []

        # Check if query is empty
        if not search_query or not search_query.strip():
            return []

        return mw.col.find_cards(search_query)
    except Exception:
        return []


def extract_publication_key_from_url(url):
    """
    Extracts a publication key or spreadsheet ID from a Google Sheets URL.
    Handles both published and edit URLs.

    Args:
        url (str): Google Sheets URL

    Returns:
        str: Extraction result or None
    """
    if not url:
        return None

    # Pattern for published URLs
    pub_pattern = r"/spreadsheets/d/e/([^/]+)/"
    pub_match = re.search(pub_pattern, url)
    if pub_match:
        return pub_match.group(1)

    # Pattern for edit URLs
    edit_pattern = r"/spreadsheets/d/([a-zA-Z0-9-_]+)"
    edit_match = re.search(edit_pattern, url)
    if edit_match:
        return edit_match.group(1)

    return None


def extract_spreadsheet_id_from_url(url):
    """
    Extracts the spreadsheet ID from a Google Sheets edit URL.

    Args:
        url (str): Google Sheets edit URL

    Returns:
        str: Spreadsheet ID or None if not found

    Examples:
        >>> extract_spreadsheet_id_from_url("https://docs.google.com/spreadsheets/d/1N-Va4ZzLUJBsD6wBaOkoeFTE6EnbZdaP/edit?usp=sharing")
        "1N-Va4ZzLUJBsD6wBaOkoeFTE6EnbZdaP"
    """
    if not url:
        return None

    # Extract spreadsheet ID from edit URLs (ID between /d/ and /edit)
    edit_pattern = r"/spreadsheets/d/([a-zA-Z0-9-_]+)/edit"
    match = re.search(edit_pattern, url)

    if match:
        return match.group(1)

    return None


def get_publication_key_hash(url):
    """
    Generates a hash for a publication key or spreadsheet ID.
    Used for compatibility in tests and some metadata.

    Args:
        url (str): Google Sheets URL

    Returns:
        str: 8-character hash
    """
    if not url:
        return ""

    # Try to extract ID, otherwise use full URL
    identifier = extract_spreadsheet_id_from_url(url) or url
    return hashlib.md5(identifier.encode()).hexdigest()[:8]


def get_spreadsheet_id_from_url(url):
    """
    Extracts the spreadsheet ID from a Google Sheets edit URL.
    This function replaces get_publication_key_hash to work only with actual IDs.

    Args:
        url (str): Google Sheets edit URL

    Returns:
        str: Spreadsheet ID (used directly as identifier)

    Raises:
        ValueError: If URL is not a valid Google Sheets edit URL
    """
    spreadsheet_id = extract_spreadsheet_id_from_url(url)

    if not spreadsheet_id:
        raise ValueError(
            "URL must be a valid Google Sheets edit URL in the format:\n"
            "https://docs.google.com/spreadsheets/d/{ID}/edit?usp=sharing"
        )

    return spreadsheet_id


def update_note_type_names_for_deck_rename(
    url, old_remote_name, new_remote_name, debug_messages=None
):
    """
    Updates only the note type name strings in meta.json when the remote_deck_name changes.
    Synchronization with Anki will be done later by the sync_note_type_names_with_config function.

    Args:
        url (str): Remote deck URL
        old_remote_name (str): Old remote name
        new_remote_name (str): New remote name
        debug_messages (list, optional): List for debug messages

    Returns:
        int: Number of updated note types
    """
    from .config_manager import get_deck_id
    from .config_manager import get_deck_note_type_ids
    from .config_manager import get_meta
    from .config_manager import save_meta

    def add_debug_msg(message, category="NOTE_TYPE_RENAME"):

        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] [{category}] {message}"
        if debug_messages is not None:
            debug_messages.append(formatted_msg)

    try:
        add_debug_msg(
            f"Updating note type strings: '{old_remote_name}' → '{new_remote_name}'"
        )

        # Get current note types
        note_types_config = get_deck_note_type_ids(url)
        updated_count = 0

        if not note_types_config:
            add_debug_msg("No note types to update")
            return 0

        # Update only name strings
        updated_note_types = {}

        for note_type_id_str, current_name in note_types_config.items():
            if old_remote_name and old_remote_name in current_name:
                # Replace old remote name with new one in string
                new_name = current_name.replace(old_remote_name, new_remote_name)
                updated_note_types[note_type_id_str] = new_name
                add_debug_msg(
                    f"Note type ID {note_type_id_str}: '{current_name}' → '{new_name}'"
                )
                updated_count += 1
            else:
                # Keep current name
                updated_note_types[note_type_id_str] = current_name

        # Save to meta.json only if changes occurred
        if updated_count > 0:
            try:
                meta = get_meta()
                spreadsheet_id = get_deck_id(url)

                if "decks" in meta and spreadsheet_id in meta["decks"]:
                    meta["decks"][spreadsheet_id]["note_types"] = updated_note_types
                    save_meta(meta)
                    add_debug_msg(
                        f"✅ Meta.json updated: {updated_count} note type strings updated"
                    )

            except Exception as meta_error:
                add_debug_msg(f"❌ Error updating meta.json: {meta_error}")

        add_debug_msg(f"✅ {updated_count} note type strings updated in meta.json")
        return updated_count

    except Exception as e:
        add_debug_msg(f"❌ ERROR updating note type strings: {e}")
        return 0


def sync_note_type_names_with_config(col, deck_url, debug_messages=None):
    """
    Synchronizes Anki note type names with meta.json configurations.
    This function uses note_types as the source of truth for names.

    Args:
        col: Anki Collection
        deck_url (str): Remote deck URL
        debug_messages (list, optional): List for debug messages

    Returns:
        dict: Synchronization statistics
    """
    from .config_manager import get_deck_note_type_ids

    def add_debug_msg(message, category="NOTE_TYPE_SYNC"):
        """Helper to add debug messages with timestamp."""

        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] [{category}] {message}"
        if debug_messages is not None:
            debug_messages.append(formatted_msg)

    stats = {
        "total_note_types": 0,
        "synced_note_types": 0,
        "unchanged_note_types": 0,
        "error_note_types": 0,
        "errors": [],
    }

    try:
        add_debug_msg("🔄 STARTING note type synchronization...")

        # Get configured note types
        note_types_config = get_deck_note_type_ids(deck_url)
        stats["total_note_types"] = len(note_types_config)

        if not note_types_config:
            add_debug_msg("⚠️ No note types configured to synchronize")
            return stats

        add_debug_msg(
            f"📋 Synchronizing {stats['total_note_types']} configured note types"
        )

        # List all configured note types first
        for note_type_id_str, expected_name in note_types_config.items():
            add_debug_msg(f"  - ID {note_type_id_str}: '{expected_name}'")

        # Now process each one
        for note_type_id_str, expected_name in note_types_config.items():
            try:
                note_type_id = int(note_type_id_str)

                add_debug_msg(f"🔍 Processing note type ID {note_type_id}...")

                # Find note type in Anki
                from anki.models import NotetypeId

                note_type = col.models.get(NotetypeId(note_type_id))
                if not note_type:
                    add_debug_msg(
                        f"❌ Note type ID {note_type_id} does not exist in Anki"
                    )
                    stats["error_note_types"] += 1
                    continue

                current_name = note_type.get("name", "")
                add_debug_msg(f"📝 Note type ID {note_type_id}:")
                add_debug_msg(f"    Current name in Anki: '{current_name}'")
                add_debug_msg(f"    Expected name (config): '{expected_name}'")

                # ALWAYS try to update to ensure synchronization
                if current_name != expected_name:
                    add_debug_message(
                        f"🔄 UPDATING note type from '{current_name}' to '{expected_name}'"
                    )

                    # Update note type name in Anki
                    note_type["name"] = expected_name
                    col.models.save(note_type)

                    # Force collection save to ensure immediate persistence
                    col.save()
                    add_debug_msg("💾 Collection saved to ensure persistence")

                    # Verify if it was actually updated
                    updated_note_type = col.models.get(NotetypeId(note_type_id))
                    if (
                        updated_note_type
                        and updated_note_type.get("name") == expected_name
                    ):
                        stats["synced_note_types"] += 1
                        add_debug_msg("✅ Note type updated SUCCESSFULLY")
                    else:
                        add_debug_msg(
                            "❌ FAILED to update note type - post-save verification failed"
                        )
                        stats["error_note_types"] += 1
                else:
                    stats["unchanged_note_types"] += 1
                    add_debug_msg("✅ Note type is already synchronized")

            except Exception as note_type_error:
                stats["error_note_types"] += 1
                error_msg = f"Error synchronizing note type {note_type_id_str}: {note_type_error}"
                stats["errors"].append(error_msg)
                add_debug_msg(f"❌ {error_msg}")
                import traceback

                add_debug_msg(f"Traceback: {traceback.format_exc()}")

        add_debug_msg(
            f"📊 RESULT: {stats['synced_note_types']} synchronized, {stats['unchanged_note_types']} unchanged, {stats['error_note_types']} errors"
        )

        # Cleanup orphaned note types in configuration
        try:
            orphaned_count = cleanup_orphaned_note_types()
            if orphaned_count > 0:
                add_debug_msg(
                    f"🧹 Cleanup: {orphaned_count} orphaned note types removed from configuration"
                )
        except Exception as cleanup_error:
            add_debug_msg(f"⚠️ Error cleaning up orphaned types: {cleanup_error}")

        return stats

    except Exception as e:
        add_debug_msg(f"❌ General synchronization ERROR: {e}")
        stats["errors"].append(f"General error: {e}")
        return stats


def get_or_create_deck(col, deckName, remote_deck_name=None):
    """
    Creates or gets an existing deck in Anki and applies options based on configured mode.

    Args:
        col: Anki Collection
        deckName: Deck name
        remote_deck_name (str, optional): Remote deck name for individual mode

    Returns:
        tuple: (deck_id, actual_name) where deck_id is the deck ID and actual_name is the real name used

    Raises:
        ValueError: If deck name is invalid
    """
    if (
        not deckName
        or not isinstance(deckName, str)
        or deckName.strip() == ""
        or deckName.strip().lower() == "default"
    ):
        raise ValueError(
            f"Invalid deck name or forbidden for synchronization: '{deckName}'"
        )

    deck = col.decks.by_name(deckName)
    deck_was_created = False

    if deck is None:
        try:
            deck_id = col.decks.id(deckName)
            deck_was_created = True
            # Get newly created deck to verify real name used
            new_deck = col.decks.get(deck_id)
            actual_name = new_deck["name"] if new_deck else deckName
        except Exception as e:
            raise ValueError(f"Could not create deck '{deckName}': {str(e)}")
    else:
        deck_id = deck["id"]
        actual_name = deck["name"]

    # Apply options based on mode (new or existing that is Sheets2Anki)
    if deckName.startswith("Sheets2Anki::") or deck_was_created:
        try:
            apply_sheets2anki_options_to_deck(deck_id, remote_deck_name)
        except Exception as e:
            add_debug_message(
                f"Warning: Failed to apply options to deck '{actual_name}': {e}",
                "DECK_OPTIONS",
            )

    return deck_id, actual_name


def get_model_suffix_from_url(url):
    """
    Generates a unique and short suffix based on the URL.

    Args:
        url: Remote deck URL

    Returns:
        str: 8-character suffix based on URL SHA1 hash
    """
    return hashlib.sha1(url.encode()).hexdigest()[:8]


def register_note_type_for_deck(url, note_type_id, note_type_name, debug_messages=None):
    """
    Registers a note type ID at creation/use time (intelligent approach).
    Stores full note type name as source of truth.

    Args:
        url (str): Remote deck URL
        note_type_id (int): Note type ID
        note_type_name (str): Full note type name in standard format
        debug_messages (list, optional): List for debug messages
    """
    from .config_manager import add_note_type_id_to_deck

    def add_debug_msg(message, category="NOTE_TYPE_REG"):
        """Helper to add debug messages with timestamp."""

        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] [{category}] {message}"
        if debug_messages is not None:
            debug_messages.append(formatted_msg)

    try:
        add_debug_msg(
            f"Registering note type: ID={note_type_id}, Name='{note_type_name}'"
        )

        # Use full name as is (already in standard format)
        # Full name will be the source of truth
        add_note_type_id_to_deck(url, note_type_id, note_type_name, debug_messages)
        add_debug_msg(f"✅ Note type successfully registered: '{note_type_name}'")

    except Exception as e:
        add_debug_msg(f"❌ ERROR registering note type: {e}")


def capture_deck_note_type_ids_from_cards(url, local_deck_id, debug_messages=None):
    """
    Captures note type IDs by analyzing existing cards in the local deck (more intelligent approach).
    Instead of searching by name, analyzes actual cards belonging to the deck.

    Args:
        url (str): Remote deck URL
        local_deck_id (int): Local deck ID in Anki
        debug_messages (list, optional): List for debug messages
    """
    from .compat import mw
    from .config_manager import add_note_type_id_to_deck

    def add_debug_msg(message, category="NOTE_TYPE_IDS"):
        """Helper to add debug messages with timestamp."""

        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] [{category}] {message}"
        if debug_messages is not None:
            debug_messages.append(formatted_msg)

    add_debug_msg(f"INTELLIGENT CAPTURE: Analyzing cards from deck ID {local_deck_id}")

    if not mw or not mw.col:
        add_debug_msg("ERROR: Anki not available")
        return

    try:
        # Search for all cards in specific deck
        # Use safe deck ID search
        card_ids = mw.col.find_cards(f"did:{local_deck_id}")
        add_debug_msg(f"Found {len(card_ids)} cards in deck")

        if not card_ids:
            add_debug_msg(
                "⚠️ No cards found in deck - note types will be captured during synchronization"
            )
            return

        # Collect unique note type IDs from existing cards
        note_type_ids = set()
        note_type_info = {}  # {note_type_id: {'name': str, 'count': int}}

        for card_id in card_ids:
            try:
                card = mw.col.get_card(card_id)
                note = card.note()
                note_type = note.note_type()

                if not note_type:
                    add_debug_msg(f"Ignoring card {card_id} - note type not found")
                    continue

                note_type_id = note_type["id"]
                note_type_name = note_type["name"]

                note_type_ids.add(note_type_id)

                if note_type_id not in note_type_info:
                    note_type_info[note_type_id] = {"name": note_type_name, "count": 0}
                note_type_info[note_type_id]["count"] += 1

            except Exception as card_error:
                add_debug_msg(f"Error processing card {card_id}: {card_error}")
                continue

        add_debug_msg(f"Unique note types found: {len(note_type_ids)}")

        # Register each found note type
        for note_type_id in note_type_ids:
            info = note_type_info[note_type_id]
            full_name = info["name"]  # Full note type name
            count = info["count"]

            add_debug_msg(
                f"Registering: ID {note_type_id}, Full Name '{full_name}', Cards: {count}"
            )

            # Use full name as source of truth (don't extract parts)
            add_note_type_id_to_deck(url, note_type_id, full_name, debug_messages)

        add_debug_msg(
            f"✅ SUCCESS: Captured {len(note_type_ids)} note types from existing cards"
        )

    except Exception as e:
        add_debug_msg(f"❌ ERROR in intelligent capture: {e}")
        import traceback

        add_debug_msg(f"Details: {traceback.format_exc()}")


def capture_deck_note_type_ids(url, remote_deck_name, debug_messages=None):
    """
    Compatibility function using card-based intelligent approach.

    Args:
        url (str): Remote deck URL
        remote_deck_name (str): Remote deck name
        debug_messages (list, optional): List for debug messages
    """
    from .config_manager import get_deck_local_id

    def add_debug_msg(message, category="NOTE_TYPE_IDS"):

        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] [{category}] {message}"
        if debug_messages is not None:
            debug_messages.append(formatted_msg)

    try:
        # Get local deck ID
        local_deck_id = get_deck_local_id(url)

        if local_deck_id:
            add_debug_msg(
                f"Using intelligent capture for local deck ID: {local_deck_id}"
            )
            capture_deck_note_type_ids_from_cards(url, local_deck_id, debug_messages)
        else:
            add_debug_msg(
                "⚠️ Local deck not found - note types will be registered during creation"
            )

    except Exception as e:
        add_debug_msg(f"❌ ERROR: {e}")
        import traceback

        add_debug_msg(f"Details: {traceback.format_exc()}")
        import traceback

        error_details = traceback.format_exc()
        add_debug_msg(f"Error details: {error_details}")


def delete_deck_note_types_by_ids(url):
    """
    Deletes note types using stored IDs from deck configuration.
    This is a more robust alternative to searching for name patterns.

    Args:
        url (str): Remote deck URL

    Returns:
        int: Number of deleted note types
    """
    from .compat import mw
    from .config_manager import cleanup_invalid_note_type_ids
    from .config_manager import get_deck_note_type_ids
    from .config_manager import remove_note_type_id_from_deck

    if not mw or not mw.col:
        add_debug_message("Anki not available", "DELETE_BY_IDS")
        return 0

    try:
        # First cleanup invalid IDs
        cleanup_invalid_note_type_ids()

        # Get valid IDs
        note_type_ids = get_deck_note_type_ids(url)

        if not note_type_ids:
            add_debug_message("No note type IDs found for deck", "DELETE_BY_IDS")
            return 0

        deleted_count = 0

        for note_type_id in note_type_ids.copy():  # Use copy to modify during iteration
            from anki.models import NotetypeId

            model = mw.col.models.get(NotetypeId(note_type_id))
            if model:
                model_name = model["name"]

                try:
                    # Check if there are notes using this note type
                    note_ids = mw.col.models.nids(note_type_id)
                    if note_ids:
                        add_debug_message(
                            f"Note type '{model_name}' has {len(note_ids)} notes, deleting them first...",
                            "DELETE_BY_IDS",
                        )
                        mw.col.remove_notes(note_ids)

                    # Delete note type
                    mw.col.models.rem(model)
                    deleted_count += 1

                    # Remove ID from configuration
                    remove_note_type_id_from_deck(url, note_type_id)

                    add_debug_message(
                        f"Note type '{model_name}' (ID: {note_type_id}) successfully deleted",
                        "DELETE_BY_IDS",
                    )

                except Exception as e:
                    add_debug_message(
                        f"Error deleting note type '{model_name}' (ID: {note_type_id}): {e}",
                        "DELETE_BY_IDS",
                    )
            else:
                # ID no longer exists, remove from configuration
                remove_note_type_id_from_deck(url, note_type_id)
                add_debug_message(
                    f"Note type ID {note_type_id} not found, removed from configuration",
                    "DELETE_BY_IDS",
                )

        if deleted_count > 0:
            mw.col.save()
            add_debug_message(
                f"Operation completed: {deleted_count} note types deleted",
                "DELETE_BY_IDS",
            )

        return deleted_count

    except Exception as e:
        add_debug_message(f"Error in deletion by IDs: {e}", "DELETE_BY_IDS")
        import traceback

        traceback.print_exc()
        return 0


def cleanup_orphaned_note_types():
    """
    Removes note types that no longer exist in Anki from the configuration.
    Useful for cleaning up references to deleted note types.

    Returns:
        int: Number of orphaned note types removed from configuration
    """
    try:
        from aqt import mw

        add_debug_message("Starting orphaned note type cleanup...", "CLEANUP_ORPHANED")

        if not mw or not mw.col:
            add_debug_message("Anki is not available", "CLEANUP_ORPHANED")
            return 0

        from .config_manager import get_meta
        from .config_manager import save_meta

        meta = get_meta()
        if not meta or "decks" not in meta:
            add_debug_message("No deck configuration found", "CLEANUP_ORPHANED")
            return 0

        cleaned_count = 0

        for publication_key, deck_info in meta["decks"].items():
            if "note_types" not in deck_info:
                continue

            orphaned_ids = []

            # Check which note types from the configuration no longer exist in Anki
            for note_type_id_str, note_type_name in deck_info["note_types"].items():
                try:
                    note_type_id = int(note_type_id_str)
                    # Use the same pattern as the rest of the code
                    from anki.models import NotetypeId

                    model = mw.col.models.get(NotetypeId(note_type_id))  # type: ignore

                    if not model:
                        orphaned_ids.append(note_type_id_str)
                        add_debug_message(
                            f"Orphan found: ID {note_type_id_str} - '{note_type_name}'",
                            "CLEANUP_ORPHANED",
                        )

                except (ValueError, TypeError):
                    # Invalid ID, also remove
                    orphaned_ids.append(note_type_id_str)
                    add_debug_message(
                        f"Invalid ID found: '{note_type_id_str}'", "CLEANUP_ORPHANED"
                    )

            # Remove orphans from configuration
            for orphaned_id in orphaned_ids:
                del deck_info["note_types"][orphaned_id]
                cleaned_count += 1
                add_debug_message(
                    f"Orphan removed: ID {orphaned_id}", "CLEANUP_ORPHANED"
                )

        if cleaned_count > 0:
            save_meta(meta)
            add_debug_message(
                f"Cleanup completed: {cleaned_count} orphaned note types removed",
                "CLEANUP_ORPHANED",
            )
        else:
            add_debug_message("No orphaned note types found", "CLEANUP_ORPHANED")

        return cleaned_count

    except Exception as e:
        add_debug_message(f"Error in cleanup: {e}", "CLEANUP_ORPHANED")
        import traceback

        traceback.print_exc()
        return 0


# =============================================================================
# URL CONVERSION
# =============================================================================


def convert_edit_url_to_tsv(url):
    """
    Converts Google Sheets edit URLs to TSV download format.

    Args:
        url (str): Google Sheets edit URL

    Returns:
        str: URL in TSV format for download

    Raises:
        ValueError: If the URL is not a valid edit URL
    """
    import re

    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")

    # Check if it's a Google Sheets URL
    if "docs.google.com/spreadsheets" not in url:
        raise ValueError("URL must be from Google Sheets")

    # Extract spreadsheet ID for edit URLs
    edit_pattern = r"https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)/edit"
    match = re.search(edit_pattern, url)

    if match:
        spreadsheet_id = match.group(1)
        # Convert to TSV export format (without gid to automatically download the first tab)
        return (
            f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=tsv"
        )

    # If it reached here, it's not a valid edit URL
    raise ValueError(
        "URL must be a Google Sheets edit URL in the format:\n"
        "https://docs.google.com/spreadsheets/d/{ID}/edit?usp=sharing"
    )


def validate_url(url):
    """
    Validates if the URL is a valid Google Sheets edit URL.

    Args:
        url (str): The URL to be validated

    Returns:
        str: URL in valid TSV format for download

    Raises:
        ValueError: If the URL is invalid or inaccessible
        URLError: If there are network connectivity issues
        HTTPError: If the server returns a status error
    """
    import socket
    import urllib.error
    import urllib.request

    # Check if URL is not empty
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")

    # Validate URL format
    if not url.startswith(("http://", "https://")):
        raise ValueError("Invalid URL: Must start with http:// or https://")

    # If URL is already in TSV format, return it directly
    if "/export?format=tsv" in url:
        return url

    # Convert to TSV format
    try:
        tsv_url = convert_edit_url_to_tsv(url)
    except ValueError as e:
        raise ValueError(f"Invalid URL: {str(e)}")

    # Test TSV URL accessibility with timeout and proper error handling
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Sheets2Anki) AnkiAddon"  # More specific user agent
        }
        request = urllib.request.Request(tsv_url, headers=headers)

        # USE LOCAL TIMEOUT instead of global it to avoid conflicts
        response = urllib.request.urlopen(request, timeout=30)  # ✅ LOCAL TIMEOUT

        if response.getcode() != 200:
            raise ValueError(
                f"URL returned unexpected status code: {response.getcode()}"
            )

        # Validate content type
        content_type = response.headers.get("Content-Type", "").lower()
        if not any(
            valid_type in content_type
            for valid_type in ["text/tab-separated-values", "text/plain", "text/csv"]
        ):
            raise ValueError(
                f"URL does not return TSV content (received {content_type})"
            )

        # Return valid TSV URL
        return tsv_url

    except TimeoutError:
        raise ValueError(
            "Connection timeout when accessing the URL (30s). Check your connection or try again."
        )
    except urllib.error.HTTPError as e:
        if e.code == 400:
            raise ValueError(
                "HTTP Error 400: The spreadsheet is not publicly accessible.\n\n"
                "To fix:\n"
                "1. Open the spreadsheet in Google Sheets\n"
                "2. Click 'Share'\n"
                "3. Change access to 'Anyone with the link'\n"
                "4. Set permission to 'Viewer'\n\n"
                "Alternatively: File → Share → Publish to the web"
            )
        else:
            raise ValueError(f"HTTP Error {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        if isinstance(e.reason, socket.timeout):
            raise ValueError(
                "Connection timeout when accessing the URL. Check your connection or try again."
            )
        elif isinstance(e.reason, socket.gaierror):
            raise ValueError("DNS Error. Check your internet connection.")
        else:
            raise ValueError(
                f"Error accessing URL - Network or server problem: {str(e.reason)}"
            )
    except Exception as e:
        raise ValueError(f"Unexpected error accessing URL: {str(e)}")


# ========================================================================================
# SUBDECK FUNCTIONS
# ========================================================================================


def ensure_subdeck_exists(deck_name):
    """
    Ensures that a subdeck exists, creating it if necessary.

    This function supports hierarchical names like "Deck::Subdeck::Subsubdeck".

    Args:
        deck_name (str): Full deck/subdeck name

    Returns:
        int: Deck/subdeck ID

    Raises:
        RuntimeError: If mw is not available
    """
    if not mw or not hasattr(mw, "col") or not mw.col:
        raise RuntimeError("Anki main window (mw) is not available")

    # Check if deck already exists
    did = mw.col.decks.id_for_name(deck_name)
    if did is not None:
        return did

    # If it doesn't exist, create deck and all necessary parent decks
    return mw.col.decks.id(deck_name)


def remove_empty_subdecks(remote_decks):
    """
    Removes empty subdecks after synchronization.

    This function checks all subdecks of remote decks and removes those
    that contain no notes or cards.

    Args:
        remote_decks (dict): Remote decks dictionary

    Returns:
        int: Number of removed empty subdecks
    """
    if not mw or not hasattr(mw, "col") or not mw.col:
        return 0

    removed_count = 0
    processed_decks = set()

    # Collect all main decks to check their subdecks
    main_deck_ids = []
    for deck_info in remote_decks.values():
        local_deck_id = deck_info.get("local_deck_id")
        if local_deck_id and local_deck_id not in processed_decks:
            main_deck_ids.append(local_deck_id)
            processed_decks.add(local_deck_id)

    # For each main deck, check its subdecks
    for local_deck_id in main_deck_ids:
        deck = mw.col.decks.get(local_deck_id)
        if not deck:
            continue

        main_deck_name = deck["name"]

        # Find all subdecks of this main deck
        all_decks = mw.col.decks.all_names_and_ids()
        subdecks = [d for d in all_decks if d.name.startswith(main_deck_name + "::")]

        # Sort subdecks from deepest to shallowest to avoid dependency problems
        subdecks.sort(key=lambda d: d.name.count("::"), reverse=True)

        # Check each subdeck
        for subdeck in subdecks:
            # Count cards in subdeck
            escaped_subdeck_name = subdeck.name.replace('"', '\\"')
            card_count = len(mw.col.find_cards(f'deck:"{escaped_subdeck_name}"'))

            # If subdeck is empty, remove it
            if card_count == 0:
                try:
                    # Convert ID to type expected by Anki
                    subdeck_id = mw.col.decks.id(subdeck.name)
                    if subdeck_id is not None:
                        mw.col.decks.remove([subdeck_id])
                        removed_count += 1
                except Exception as e:
                    # Ignore subdeck removal errors
                    add_debug_message(f"Error removing subdeck: {e}", "SUBDECK")

    return removed_count


# Re-exported from the pure layer: both are plain string formatting the
# preview site needs too, and it cannot import this module (utils reaches for
# Anki). See tsv_model's docstring.
from .tsv_model import get_note_type_name  # noqa: F401,E402  (facade)
from .tsv_model import get_subdeck_name  # noqa: F401,E402  (facade)
