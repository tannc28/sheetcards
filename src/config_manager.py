"""
Configuration manager for the SheetCards addon.

This module implements a hierarchical configuration system that uses:
- config.json: Addon default settings
- meta.json: User settings and remote deck data (source of truth)

Features:
- Loading and saving configurations
- Migrating old configurations
- User preference management
- Remote deck control
"""

import copy
import json
import os

try:
    from .compat import mw
    from .styled_messages import StyledMessageBox
    from .utils import add_debug_message
    from .utils import get_spreadsheet_id_from_url
    from .utils import sheet_name_from_url
    from .utils import source_id
except ImportError:
    # For standalone tests
    from compat import mw
    from utils import add_debug_message
    from utils import get_spreadsheet_id_from_url
    from utils import sheet_name_from_url
    from utils import source_id


def add_debug_msg(message, category="CONFIG"):
    """Local helper for debug messages."""
    add_debug_message(message, category)


# =============================================================================
# UTILITY FUNCTIONS FOR SPREADSHEET ID
# =============================================================================


def get_deck_id(url):
    """
    The key a deck is stored and looked up under.

    A Google Sheets file holds several sheets and a deck syncs exactly one of
    them, so the spreadsheet id alone cannot tell two decks of one file apart —
    they would share a configuration entry and a settings-row cache, and each
    sync would overwrite the other's. The sheet the deck names comes into the key.

    A URL naming no sheet keeps the plain spreadsheet id it has always had, so a
    deck connected before this existed is found exactly where it was left.

    Args:
        url (str): Remote deck edit URL

    Returns:
        str: ``{spreadsheet id}`` or ``{spreadsheet id}#{sheet name}``

    Raises:
        ValueError: If the URL is not a valid edit URL
    """
    base = source_id(url)
    sheet = sheet_name_from_url(url)
    return f"{base}#{sheet}" if sheet else base


# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

DEFAULT_CONFIG = {
    "config": {
        "debug": False,
        "auto_sync_on_startup": False,
        "max_sync_retries": 3,
        "sync_timeout_seconds": 60,
        "ankiweb_sync_mode": "sync",  # "none", "sync"
        "accumulate_logs": True,  # whether to keep logs between sessions
        # Image processor settings
    },
    "decks": {},
}

DEFAULT_META = copy.deepcopy(DEFAULT_CONFIG)

# =============================================================================
# MAIN FUNCTIONS
# =============================================================================


def get_config():
    """
    Loads default configuration from config.json.

    Returns:
        dict: Addon default configuration
    """
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "config.json"
    )

    try:
        if os.path.exists(config_path):
            with open(config_path, encoding="utf-8") as f:
                config = json.load(f)

            # Merge with defaults to ensure compatibility
            merged_config = copy.deepcopy(DEFAULT_CONFIG)
            merged_config.update(config)
            return merged_config
        else:
            return copy.deepcopy(DEFAULT_CONFIG)
    except Exception as e:
        if mw:
            StyledMessageBox.warning(
                mw,
                "Config Load Error",
                f"Error loading config.json: {str(e)}",
                detailed_text="Using default configuration.",
            )
        return copy.deepcopy(DEFAULT_CONFIG)


def get_meta():
    """
    Loads user metadata from meta.json (source of truth).
    If meta.json doesn't exist, allows initialization from config.json.

    Returns:
        dict: User metadata including preferences and remote decks
    """
    try:
        import json
        import os

        # Paths
        addon_path = os.path.dirname(os.path.dirname(__file__))
        meta_path = os.path.join(addon_path, "meta.json")
        config_path = os.path.join(addon_path, "config.json")

        # 1. Try to load meta.json (User settings)
        if os.path.exists(meta_path):
            with open(meta_path, encoding="utf-8") as f:
                meta = json.load(f)

        # 2. If meta.json doesn't exist, try config.json (Defaults)
        elif os.path.exists(config_path):
            with open(config_path, encoding="utf-8") as f:
                meta = json.load(f)

        # 3. Fallback to hardcoded defaults
        else:
            meta = copy.deepcopy(DEFAULT_META)

        # Ensure proper structure
        meta = _ensure_meta_structure(meta)

        return meta
    except Exception as e:
        if mw:
            StyledMessageBox.warning(
                mw,
                "Meta Load Error",
                f"Error loading meta.json: {str(e)}",
                detailed_text="Using default configuration.",
            )
        return copy.deepcopy(DEFAULT_META)


def save_meta(meta):
    """
    Saves user metadata to meta.json.

    Args:
        meta (dict): Metadata to save
    """
    try:
        import json
        import os

        # Save directly to meta.json file
        addon_path = os.path.dirname(os.path.dirname(__file__))
        meta_path = os.path.join(addon_path, "meta.json")

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=4, ensure_ascii=False)
    except Exception as e:
        if mw:
            StyledMessageBox.warning(
                mw, "Meta Save Error", f"Error saving meta.json: {str(e)}"
            )


def get_remote_decks():
    """
    Gets configured remote decks with hash-based structure.

    Returns:
        dict: Dictionary {hash_key: deck_info} where deck_info contains:
            - local_deck_id: Deck ID in Anki
            - local_deck_name: Deck name in Anki
            - remote_deck_url: Remote deck URL
            - remote_deck_name: Remote file name
            - note_types: Dict {note_type_id: expected_name}
    """
    meta = get_meta()
    return meta.get("decks", {})


def save_remote_decks(remote_decks):
    """
    Saves remote decks to the configuration using hash-based structure.

    Args:
        remote_decks (dict): Dictionary {hash_key: deck_info}
    """
    # Debug: Log what is being saved
    from .utils import add_debug_message

    add_debug_message("=== SAVING DECK INFO TO META.JSON ===", "Config Manager")
    for hash_key, deck_info in remote_decks.items():
        local_deck_id = deck_info.get("local_deck_id", "N/A")
        local_deck_name = deck_info.get("local_deck_name", "N/A")
        add_debug_message(
            f"Hash {hash_key}: local_deck_id={local_deck_id}, local_deck_name='{local_deck_name}'",
            "Config Manager",
        )

    meta = get_meta()
    meta["decks"] = remote_decks
    save_meta(meta)

    add_debug_message("✓ Deck info successfully saved to meta.json", "Config Manager")


def legacy_whole_file_deck(url):
    """A deck connected before one file could hold several decks, if there is one.

    Such a deck is stored under the bare spreadsheet id and syncs whichever sheet
    the export happens to hand over — the first one. Returns ``(key, deck_info)``
    or ``(None, None)``.
    """
    try:
        spreadsheet_id = get_spreadsheet_id_from_url(url)
    except ValueError:
        return None, None
    decks = get_remote_decks()
    return (
        (spreadsheet_id, decks[spreadsheet_id])
        if spreadsheet_id in decks
        else (None, None)
    )


def adopt_sheet_into_legacy_deck(url, sheet_name):
    """Points an already-connected whole-file deck at the sheet it was syncing.

    The deck keeps its local deck, its notes, its options and its history — only
    its key and its stored URL gain the sheet's name, so the rest of the file's
    sheets can be connected beside it instead of the add-on refusing the file as
    already registered.

    ``sheet_name`` must be the file's *first* sheet, because that is the one the
    export was handing this deck all along. Pointing it at any other sheet would
    silently reassign a deck full of notes to different rows.

    Returns True when an entry was moved.
    """
    from .utils import url_for_sheet

    old_key, deck_info = legacy_whole_file_deck(url)
    if not old_key or not sheet_name:
        return False

    sheet_url = url_for_sheet(deck_info.get("remote_deck_url") or url, sheet_name)
    new_key = get_deck_id(sheet_url)
    if new_key == old_key:
        return False

    decks = get_remote_decks()
    deck_info = dict(deck_info)
    deck_info["remote_deck_url"] = sheet_url
    decks[new_key] = deck_info
    decks.pop(old_key, None)
    save_remote_decks(decks)

    # The settings cache is keyed the same way, so its old entry is now
    # unreachable. Dropping it keeps the collection config from carrying a row
    # nothing will ever read again; the next sync writes the entry under the new
    # key regardless.
    try:
        from .sync_config import forget_sheet_settings

        forget_sheet_settings(old_key)
    except Exception as e:
        add_debug_msg(f"Could not drop the old settings cache entry: {e}")

    add_debug_msg(f"Deck {old_key} now names its sheet: {new_key}")
    return True


def add_remote_deck(url, deck_info):
    """
    Adds a remote deck to the configuration using hash as key.

    Args:
        url (str): Remote deck URL
        deck_info (dict): Deck information in the new structure
    """
    # Generate hash for the spreadsheet ID
    spreadsheet_id = get_deck_id(url)

    remote_decks = get_remote_decks()
    remote_decks[spreadsheet_id] = deck_info
    save_remote_decks(remote_decks)


def create_deck_info(
    url, local_deck_id, local_deck_name, remote_deck_name=None, **additional_info
):
    """
    Creates a deck info dictionary with the new structure.

    Args:
        url (str): Remote deck URL
        local_deck_id (int): Deck ID in Anki
        local_deck_name (str): Deck name in Anki
        remote_deck_name (str, optional): Remote file name
        **additional_info: Additional fields

    Returns:
        dict: Full deck structure
    """
    # Resolve remote_deck_name conflicts using DeckNameManager
    import time

    from .deck_manager import DeckNameManager

    resolved_remote_name = DeckNameManager.resolve_remote_name_conflict(
        url, remote_deck_name or ""
    )

    # One options group for every connected deck. There used to be a choice of
    # three here, which was a setting about a setting: a study preset is Anki's to
    # configure, two clicks away in its own deck options.
    options_group_name = "SheetCards - Default Options"

    # Ensure created_at always exists
    current_timestamp = int(time.time())
    created_at = additional_info.pop("created_at", current_timestamp)

    deck_info = {
        "remote_deck_url": url,
        "local_deck_id": local_deck_id,
        "local_deck_name": local_deck_name,
        "remote_deck_name": resolved_remote_name,
        "note_types": {},
        "is_test_deck": False,
        "is_sync": True,
        "local_deck_configurations_package_name": options_group_name,
        "created_at": created_at,
        "last_sync": None,  # null = never synchronized (NEW)
        "first_sync": None,  # First synchronization timestamp
        "sync_count": 0,  # Synchronization counter
    }

    # Add extra fields if provided
    deck_info.update(additional_info)

    return deck_info


def add_remote_deck_simple(
    url, local_deck_id, local_deck_name, remote_deck_name=None, **additional_info
):
    """
    Simplified version to add remote deck with clean structure.

    Args:
        url (str): Remote deck URL
        local_deck_id (int): Deck ID in Anki
        local_deck_name (str): Deck name in Anki
        remote_deck_name (str, optional): Remote file name
        **additional_info: Additional fields
    """
    deck_info = create_deck_info(
        url, local_deck_id, local_deck_name, remote_deck_name, **additional_info
    )
    add_remote_deck(url, deck_info)


def update_deck_sync_status(deck_url, success=True):
    """
    Updates synchronization fields for a deck after a sync.

    Args:
        deck_url (str): Synchronized deck URL
        success (bool): Whether the sync was successful

    Returns:
        bool: True if deck was new (never synchronized), False otherwise
    """
    import time

    meta = get_meta()
    decks = meta.get("decks", {})

    # Find deck by URL
    deck_hash = None
    deck_info = None

    for hash_key, info in decks.items():
        if info.get("remote_deck_url") == deck_url:
            deck_hash = hash_key
            deck_info = info
            break

    if not deck_info:
        add_debug_msg(f"[SYNC_STATUS] Deck not found for URL: {deck_url}")
        return False

    # Check if it's a new deck (never synchronized)
    was_new_deck = deck_info.get("last_sync") is None

    if success:
        current_timestamp = int(time.time())

        # If it's the first successful sync, set first_sync
        if deck_info.get("first_sync") is None:
            deck_info["first_sync"] = current_timestamp

        # Update last_sync
        deck_info["last_sync"] = current_timestamp

        # Increment counter
        deck_info["sync_count"] = deck_info.get("sync_count", 0) + 1

        # Save changes
        save_meta(meta)

        add_debug_msg(f"[SYNC_STATUS] Deck {deck_hash} synced (new: {was_new_deck})")

    return was_new_deck


def get_deck_local_name(url):
    """
    Gets the local name of a deck from its URL.

    Args:
        url (str): Deck URL

    Returns:
        str: Local deck name or None if not found
    """
    # Generate spreadsheet ID
    spreadsheet_id = get_deck_id(url)

    remote_decks = get_remote_decks()
    deck_info = remote_decks.get(spreadsheet_id, {})

    return deck_info.get("local_deck_name")


def get_deck_remote_name(url):
    """
    Gets the remote name of a deck from its URL.

    Args:
        url (str): Deck URL

    Returns:
        str: Remote deck name or None if not found
    """
    # Generate hash for the spreadsheet ID
    spreadsheet_id = get_deck_id(url)

    remote_decks = get_remote_decks()
    deck_info = remote_decks.get(spreadsheet_id, {})

    # If it exists in the new structure, use it
    if "remote_deck_name" in deck_info:
        return deck_info["remote_deck_name"]

    # Fallback: extract from URL if it doesn't exist
    if url:
        # If prefix changed, re-extract from URL to keep consistency
        from .deck_manager import DeckNameManager

        return DeckNameManager.extract_remote_name_from_url(url)

    return None


def remove_remote_deck(url):
    """
    Removes a remote deck from the configuration.

    Args:
        url (str): Remote deck URL to be removed
    """
    # Generate hash for the spreadsheet ID
    spreadsheet_id = get_deck_id(url)

    remote_decks = get_remote_decks()
    if spreadsheet_id in remote_decks:
        del remote_decks[spreadsheet_id]
        save_remote_decks(remote_decks)


def disconnect_deck(url):
    """
    Completely removes a remote deck from the system.
    This action is irreversible - the deck can only be reconnected if it's re-registered.

    Args:
        url (str): Deck URL to be disconnected
    """
    # Generate hash for the spreadsheet ID
    spreadsheet_id = get_deck_id(url)

    meta = get_meta()
    remote_decks = meta.get("decks", {})

    # Completely remove deck from remote decks list
    if spreadsheet_id in remote_decks:
        del remote_decks[spreadsheet_id]
        meta["decks"] = remote_decks  # type: ignore
        save_meta(meta)


def is_deck_disconnected(url):
    """
    Checks if a deck is disconnected (no longer in the configuration).

    Args:
        url (str): Deck URL

    Returns:
        bool: True if disconnected (doesn't exist), False if it exists
    """
    # Generate hash for the spreadsheet ID
    spreadsheet_id = get_deck_id(url)

    remote_decks = get_remote_decks()
    return spreadsheet_id not in remote_decks


def get_active_decks():
    """
    Gets all active remote decks.
    In the new logic, all decks in 'decks' are considered active.

    Returns:
        dict: Dictionary with URLs as keys and deck data as values
    """
    meta = get_meta()
    return meta.get("decks", {})


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def verify_and_update_deck_info(url, local_deck_id, local_deck_name, silent=False):
    """
    Verifies and updates deck info in the configuration using the new structure.

    This function ensures that:
    1. local_deck_id is updated in the configuration
    2. local_deck_name is updated in the configuration
    3. remote_deck_name is synchronized with current URL
    4. Information matches Anki's current state

    Args:
        url (str): Remote deck URL
        local_deck_id (int): Current deck ID in Anki
        local_deck_name (str): Current local deck name in Anki
        silent (bool): If True, doesn't show notifications

    Returns:
        bool: True if there were updates, False otherwise
    """
    # Generate hash for the spreadsheet ID
    spreadsheet_id = get_deck_id(url)

    remote_decks = get_remote_decks()

    # Check if deck exists in the configuration
    if spreadsheet_id not in remote_decks:
        return False

    deck_info = remote_decks[spreadsheet_id]
    updated = False

    # Check if local_deck_id needs update
    current_local_deck_id = deck_info.get("local_deck_id")
    if current_local_deck_id != local_deck_id:
        deck_info["local_deck_id"] = local_deck_id
        updated = True
    # Check if local_deck_name needs update
    current_local_deck_name = deck_info.get("local_deck_name")
    if current_local_deck_name != local_deck_name:
        deck_info["local_deck_name"] = local_deck_name
        updated = True

    # Check if remote_deck_name needs update using DeckNameManager
    from .deck_manager import DeckNameManager

    current_remote_name = DeckNameManager.extract_remote_name_from_url(url)
    stored_remote_name = deck_info.get("remote_deck_name")
    if stored_remote_name != current_remote_name:
        resolved_remote_name = DeckNameManager.resolve_remote_name_conflict(
            url, current_remote_name
        )
        deck_info["remote_deck_name"] = resolved_remote_name

        deck_info["local_deck_configurations_package_name"] = (
            "SheetCards - Default Options"
        )

        updated = True
        if not silent:
            add_debug_msg(
                f"[SheetCards] Remote deck name updated from '{stored_remote_name}' to '{resolved_remote_name}'"
            )

    # Save changes if there were updates
    if updated:
        save_remote_decks(remote_decks)
        return True

    return False


def detect_deck_name_changes(skip_deleted=False):
    """
    Detects changes in local deck names and updates the configuration.

    This function checks all configured remote decks and updates
    their information if the deck name was changed in Anki.

    Args:
        skip_deleted: If True, doesn't update names of deleted decks

    Returns:
        list: List of hash keys for the updated decks
    """
    from .compat import mw

    remote_decks = get_remote_decks()
    updated_hashes = []

    for url_hash, deck_info in remote_decks.items():
        local_deck_id = deck_info.get("local_deck_id")
        if not local_deck_id:
            continue

        # Get current deck from Anki
        if not mw.col or not mw.col.decks:
            continue  # Collection or decks not available

        deck = mw.col.decks.get(local_deck_id)

        # If deck was deleted and skip_deleted=True, skip
        if not deck and skip_deleted:
            continue

        # If deck exists, update name
        if deck:
            current_name = deck.get("name", "")
            saved_name = deck_info.get("local_deck_name", "")

            # Check if name changed
            if current_name and current_name != saved_name:
                # Update name in configuration
                deck_info["local_deck_name"] = current_name
                updated_hashes.append(url_hash)

    # Save changes if there were updates
    if updated_hashes:
        save_remote_decks(remote_decks)

    return updated_hashes


def get_sync_selection():
    """
    Gets persistent selection of decks for synchronization.

    Returns:
        dict: Dictionary with URLs as keys and bool as values
    """
    remote_decks = get_remote_decks()
    selection = {}

    for url, deck_info in remote_decks.items():
        # Use is_sync attribute from deck data, default True if doesn't exist
        selection[url] = deck_info.get("is_sync", True)

    return selection


def save_sync_selection(selection):
    """
    Saves the persistent deck selection for synchronization.

    Args:
        selection (dict): Dictionary with URLs as keys and bool as values
    """
    remote_decks = get_remote_decks()

    # Update is_sync attribute in each deck
    for url, is_selected in selection.items():
        if url in remote_decks:
            remote_decks[url]["is_sync"] = is_selected

    save_remote_decks(remote_decks)


def update_sync_selection(url, selected):
    """
    Updates selection for a specific deck.

    Args:
        url (str): Deck URL
        selected (bool): Whether the deck is selected
    """
    remote_decks = get_remote_decks()

    if url in remote_decks:
        remote_decks[url]["is_sync"] = selected
        save_remote_decks(remote_decks)


def clear_sync_selection():
    """
    Clears all persistent selection (sets all as unselected).
    """
    remote_decks = get_remote_decks()

    for url in remote_decks:
        remote_decks[url]["is_sync"] = False

    save_remote_decks(remote_decks)


def set_all_sync_selection(selected=True):
    """
    Sets all decks as selected or unselected.

    Args:
        selected (bool): True to select all, False to unselect all
    """
    remote_decks = get_remote_decks()

    for url in remote_decks:
        remote_decks[url]["is_sync"] = selected

    save_remote_decks(remote_decks)


def _ensure_meta_structure(meta):
    """
    Ensures that meta.json structure is correct.

    Args:
        meta (dict): Metadata to be checked

    Returns:
        dict: Metadata with corrected structure
    """
    # Ensure main keys
    if "decks" not in meta:
        meta["decks"] = {}

    # Migrate remote_decks data to decks if necessary
    if "remote_decks" in meta and meta["remote_decks"] and not meta.get("decks"):
        meta["decks"] = meta["remote_decks"]

    # Remove unnecessary old keys
    if "remote_decks" in meta:
        del meta["remote_decks"]
    if "user_preferencies" in meta:
        del meta["user_preferencies"]

    # Ensure all decks have is_sync attribute
    for url, deck_info in meta["decks"].items():
        if "is_sync" not in deck_info:
            deck_info["is_sync"] = True  # Default: selected for synchronization

    return meta


# =============================================================================
# NOTE TYPE IDS MANAGEMENT
# =============================================================================


def add_note_type_id_to_deck(
    deck_url, note_type_id, expected_name=None, debug_messages=None
):
    """
    Adds a note type ID to deck using new hash-based structure.

    Args:
        deck_url (str): Remote deck URL
        note_type_id (int): Note type ID
        expected_name (str, optional): Expected name of the note type
        debug_messages (list, optional): List to accumulate debug messages
    """

    def add_debug_msg(message, category="CONFIG"):
        """Helper to add debug messages with timestamp."""
        from datetime import datetime

        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] [{category}] {message}"
        if debug_messages is not None:
            debug_messages.append(formatted_msg)

    try:
        add_debug_msg("add_note_type_id_to_deck CALL:")
        add_debug_msg(f"  - URL: {deck_url}")
        add_debug_msg(f"  - ID: {note_type_id}")
        add_debug_msg(f"  - Expected name: {expected_name}")

        # Generate spreadsheet ID
        spreadsheet_id = get_deck_id(deck_url)
        add_debug_msg(f"  - Spreadsheet ID: {spreadsheet_id}")

        meta = get_meta()
        add_debug_msg(f"Meta loaded: {len(meta.get('decks', {}))} decks in config")

        if spreadsheet_id not in meta["decks"]:
            add_debug_msg(f"ERROR: Deck {spreadsheet_id} not found in configuration")
            add_debug_msg("Available decks:")
            for key in meta.get("decks", {}).keys():
                add_debug_msg(f"  - {key}")
            return

        deck_info = meta["decks"][spreadsheet_id]
        add_debug_msg(f"Deck info found: {list(deck_info.keys())}")

        # Ensure note_types structure exists
        if "note_types" not in deck_info:
            deck_info["note_types"] = {}
            add_debug_msg("Initializing empty note_types dictionary")

        note_type_id_str = str(note_type_id)

        # Add or update current note type
        if note_type_id_str not in deck_info["note_types"]:
            # Add new note type with expected name
            deck_info["note_types"][note_type_id_str] = (
                expected_name or f"Note Type {note_type_id}"
            )
            add_debug_msg(f"Note type ID {note_type_id} added to dictionary")
        else:
            # Update expected name if provided and different
            current_name = deck_info["note_types"][note_type_id_str]
            if expected_name and current_name != expected_name:
                old_name = current_name
                deck_info["note_types"][note_type_id_str] = expected_name
                add_debug_msg(
                    f"Note type ID {note_type_id} name updated from '{old_name}' to '{expected_name}'"
                )
            else:
                add_debug_msg(
                    f"Note type ID {note_type_id} already registered with correct name"
                )

        # Save changes
        save_meta(meta)
        add_debug_msg("Meta successfully saved")

        name_info = f" ({expected_name})" if expected_name else ""
        add_debug_msg(f"✅ SUCCESS: Note type ID {note_type_id}{name_info} processed")

    except Exception as e:
        add_debug_msg(f"❌ ERROR adding note type ID: {e}")
        import traceback

        error_details = traceback.format_exc()
        add_debug_msg(f"Error details: {error_details}")


def get_deck_local_id(deck_url):
    """
    Gets the local deck ID from a remote deck using new structure.

    Args:
        deck_url (str): Remote deck URL

    Returns:
        int: Local deck ID or None if not found
    """
    try:
        spreadsheet_id = get_deck_id(deck_url)

        meta = get_meta()

        if spreadsheet_id in meta.get("decks", {}):
            return meta["decks"][spreadsheet_id].get("local_deck_id")
        return None

    except Exception as e:
        add_debug_msg(f"[CONFIG] Error getting local deck ID: {e}")
        return None


def get_deck_note_type_ids(deck_url):
    """
    Gets note type IDs of a deck using new structure.

    Args:
        deck_url (str): Remote deck URL

    Returns:
        dict: {note_type_id: expected_name} dictionary
    """
    try:
        spreadsheet_id = get_deck_id(deck_url)

        meta = get_meta()

        if spreadsheet_id in meta.get("decks", {}):
            return meta["decks"][spreadsheet_id].get("note_types", {})
        return {}

    except Exception as e:
        add_debug_msg(f"[NOTE_TYPE_IDS] Error getting note type IDs: {e}")
        return {}


def remove_note_type_id_from_deck(deck_url, note_type_id):
    """
    Removes a note type ID from a deck using new structure.

    Args:
        deck_url (str): Remote deck URL
        note_type_id (int): Note type ID to be removed
    """
    try:
        spreadsheet_id = get_deck_id(deck_url)

        meta = get_meta()

        if spreadsheet_id not in meta["decks"]:
            return

        deck_info = meta["decks"][spreadsheet_id]
        note_type_id_str = str(note_type_id)

        if "note_types" in deck_info and note_type_id_str in deck_info["note_types"]:
            del deck_info["note_types"][note_type_id_str]
            save_meta(meta)
            add_debug_msg(
                f"[NOTE_TYPE_IDS] Removed note type ID {note_type_id} from deck {spreadsheet_id}"
            )

    except Exception as e:
        add_debug_msg(f"[NOTE_TYPE_IDS] Error removing note type ID: {e}")


def cleanup_invalid_note_type_ids():
    """
    Removes note type IDs that no longer exist in Anki from all decks.

    Returns:
        int: Number of IDs removed
    """
    from .compat import mw

    if not mw or not mw.col:
        return 0

    try:
        # Get all valid note types from Anki
        all_models = mw.col.models.all()
        valid_ids = {str(model["id"]) for model in all_models}

        meta = get_meta()

        removed_count = 0

        for deck_hash, deck_info in meta.get("decks", {}).items():
            if "note_types" in deck_info:
                invalid_ids = []
                for note_type_id in deck_info["note_types"].keys():
                    if note_type_id not in valid_ids:
                        invalid_ids.append(note_type_id)

                # Remove invalid IDs
                for invalid_id in invalid_ids:
                    del deck_info["note_types"][invalid_id]
                    removed_count += 1

        if removed_count > 0:
            save_meta(meta)
            add_debug_msg(f"[NOTE_TYPE_IDS] Removed {removed_count} invalid IDs")

        return removed_count

    except Exception as e:
        add_debug_msg(f"[NOTE_TYPE_IDS] Error during cleanup of invalid IDs: {e}")
        return 0


def update_note_type_names_in_meta(url, new_remote_deck_name):
    """
    Updates note type names in meta.json when remote_deck_name changes.

    Args:
        url (str): Remote deck URL
        new_remote_deck_name (str): New remote deck name
    """
    try:
        from .utils import get_note_type_name

        meta = get_meta()
        spreadsheet_id = get_deck_id(url)

        if "decks" not in meta or spreadsheet_id not in meta["decks"]:
            return

        deck_info = meta["decks"][spreadsheet_id]
        note_types = deck_info.get("note_types", {})

        if not note_types:
            return

        add_debug_msg(
            f"[UPDATE_META] Updating note type names for deck: {new_remote_deck_name}"
        )

        # Update each note type ID with the new expected name
        for note_type_id, old_name in note_types.items():
            # Analyze old name to extract the note type
            # IMPORTANT: deck_name may contain " - ", so parse from the END
            if old_name.startswith("SheetCards - "):
                parts = old_name.split(" - ")

                if len(parts) >= 3:
                    # Format: "SheetCards - remote_name - type"
                    # Last part is the type (Basic/Cloze)
                    is_cloze = parts[-1].strip() == "Cloze"
                else:
                    # Unrecognized format, try to deduce
                    is_cloze = "Cloze" in old_name

                new_name = get_note_type_name(
                    url,
                    new_remote_deck_name,
                    is_cloze=is_cloze,
                )

                # Update if name changed
                if new_name != old_name:
                    note_types[note_type_id] = new_name
                    add_debug_msg(f"[UPDATE_META] ✅ Updated: {old_name} -> {new_name}")

        # Save changes
        save_meta(meta)
        add_debug_msg("[UPDATE_META] ✅ Meta.json updated with new note type names")

    except Exception as e:
        add_debug_msg(f"[UPDATE_META] ❌ Error updating names in meta.json: {e}")
        import traceback

        traceback.print_exc()


# =============================================================================
# DECK OPTIONS SETTINGS MANAGEMENT
# =============================================================================


def get_deck_configurations_package_name(url):
    """
    Gets the configured options group name for a specific deck.

    Args:
        url (str): Remote deck URL

    Returns:
        str or None: Options group name or None if manual mode
    """
    remote_decks = get_remote_decks()
    spreadsheet_id = get_deck_id(url)
    deck_info = remote_decks.get(spreadsheet_id)

    if deck_info:
        return deck_info.get("local_deck_configurations_package_name")
    return None


def set_deck_configurations_package_name(url, package_name):
    """
    Sets the options group name for a specific deck.

    Args:
        url (str): Remote deck URL
        package_name (str or None): Options group name
    """
    remote_decks = get_remote_decks()
    spreadsheet_id = get_deck_id(url)
    deck_info = remote_decks.get(spreadsheet_id)

    if deck_info:
        deck_info["local_deck_configurations_package_name"] = package_name
        add_remote_deck(url, deck_info)
        add_debug_msg(
            f"[DECK_CONFIG] Options group '{package_name}' defined for deck {deck_info.get('remote_deck_name', 'Unknown')}"
        )
    else:
        add_debug_msg(f"[DECK_CONFIG] Deck not found for URL: {url}")


def ensure_deck_configurations_consistency():
    """
    Ensures that all decks have local_deck_configurations_package_name setting,
    and that it names the one options group every connected deck studies under.
    """
    meta = get_meta()
    remote_decks = meta.get("decks", {})

    added_count = 0
    fixed_count = 0

    for deck_hash, deck_info in remote_decks.items():
        remote_deck_name = deck_info.get("remote_deck_name", "UnknownDeck")
        current_package_name = deck_info.get("local_deck_configurations_package_name")

        expected_package_name = "SheetCards - Default Options"

        # If configuration doesn't exist, add it
        if "local_deck_configurations_package_name" not in deck_info:
            deck_info["local_deck_configurations_package_name"] = expected_package_name
            added_count += 1
        # If it exists but is inconsistent, fix it
        elif current_package_name != expected_package_name:
            deck_info["local_deck_configurations_package_name"] = expected_package_name
            fixed_count += 1

    total_changes = added_count + fixed_count
    if total_changes > 0:
        save_meta(meta)
        if added_count > 0:
            add_debug_msg(
                f"[DECK_CONFIG_CONSISTENCY] Added local_deck_configurations_package_name configuration to {added_count} decks"
            )
        if fixed_count > 0:
            add_debug_msg(
                f"[DECK_CONFIG_CONSISTENCY] Fixed inconsistencies in {fixed_count} decks"
            )

    return total_changes


# =============================================================================
# ANKIWEB SYNCHRONIZATION SETTINGS
# =============================================================================


def get_ankiweb_sync_mode():
    """
    Gets the current automatic AnkiWeb synchronization mode.

    Returns:
        str: "none" (do not synchronize), "sync" (normal synchronization)
    """
    meta = get_meta()
    config = meta.get("config", {})
    return config.get("ankiweb_sync_mode", "none")


def set_ankiweb_sync_mode(mode):
    """
    Sets the automatic AnkiWeb synchronization mode.

    Args:
        mode (str): "none" or "sync"
    """
    if mode not in ["none", "sync"]:
        raise ValueError(f"Invalid mode: {mode}. Use 'none' or 'sync'")

    meta = get_meta()
    if "config" not in meta:
        meta["config"] = {}

    meta["config"]["ankiweb_sync_mode"] = mode
    save_meta(meta)
    add_debug_msg(f"[ANKIWEB_SYNC_MODE] Mode changed to: {mode}")


def set_ankiweb_sync_config(mode):
    """
    Sets all AnkiWeb synchronization configuration at once.

    Args:
        mode (str): "none" or "sync"
    """
    # Validation
    if mode not in ["none", "sync"]:
        raise ValueError(f"Invalid mode: {mode}")

    meta = get_meta()
    if "config" not in meta:
        meta["config"] = {}

    meta["config"]["ankiweb_sync_mode"] = mode

    save_meta(meta)
    add_debug_msg(f"[ANKIWEB_CONFIG] Updated: mode={mode}")


def sync_note_type_names_robustly(url, correct_remote_name):
    """
    Robust note_types synchronization: recreates names, detects changes,
    renames in Anki and migrates notes if necessary.

    This is the full implementation of the desired logic:
    1. At each synchronization: Recreates note_type names following the correct pattern
    2. Detects changes: Compares old vs. recreated string
    3. Renames in Anki: Updates physical note type name in Anki
    4. Checks notes: Ensures notes are in the correct note type

    Args:
        url (str): Remote deck URL
        correct_remote_name (str): Current correct remote name

    Returns:
        dict: Sync result with counters
    """
    try:
        from aqt import mw

        from .utils import get_note_type_name

        if not mw or not mw.col:
            add_debug_msg("[NOTE_TYPE_SYNC] Anki is not available")
            return {"updated_count": 0, "renamed_in_anki": 0, "updated_in_meta": 0}

        meta = get_meta()
        spreadsheet_id = get_deck_id(url)

        if "decks" not in meta or spreadsheet_id not in meta["decks"]:
            add_debug_msg(
                f"[NOTE_TYPE_SYNC] Deck {spreadsheet_id} not found in meta.json"
            )
            return {"updated_count": 0, "renamed_in_anki": 0, "updated_in_meta": 0}

        deck_info = meta["decks"][spreadsheet_id]
        note_types = deck_info.get("note_types", {})

        if not note_types:
            add_debug_msg("[NOTE_TYPE_SYNC] No note_type found")
            return {"updated_count": 0, "renamed_in_anki": 0, "updated_in_meta": 0}

        def extract_type_from_name(old_name):
            """Extracts the note type from old name."""
            if not old_name.startswith("SheetCards - "):
                return None, False

            parts = old_name.split(" - ")
            # IMPORTANT: deck_name may contain " - ", so parse from the END
            if len(parts) >= 3:  # "SheetCards - remote_name - type"
                # Last part is the type (Basic/Cloze)
                note_type = parts[-1].strip()
                return note_type, note_type == "Cloze"

            return None, False

        result = {
            "updated_count": 0,
            "renamed_in_anki": 0,
            "updated_in_meta": 0,
            "notes_migrated": 0,
        }

        add_debug_msg(
            f"[NOTE_TYPE_SYNC] Starting robust synchronization for {len(note_types)} note_types"
        )

        # Process each note_type
        for note_type_id, old_name in note_types.items():
            try:
                note_type_id_int = int(note_type_id)

                # 1. RECREATE: Generate expected name based on correct pattern
                note_type, is_cloze = extract_type_from_name(old_name)

                if note_type is None:
                    add_debug_msg(
                        f"[NOTE_TYPE_SYNC] Unrecognized format for {note_type_id}: '{old_name}'"
                    )
                    continue

                expected_name = get_note_type_name(
                    url,
                    correct_remote_name,
                    is_cloze=is_cloze,
                )

                # 2. DETECT: Compare old vs. recreated name
                if expected_name == old_name:
                    add_debug_msg(
                        f"[NOTE_TYPE_SYNC] ✅ {note_type_id} is already correct: '{old_name}'"
                    )
                    continue

                add_debug_msg(
                    f"[NOTE_TYPE_SYNC] 🔄 {note_type_id} needs to be updated:"
                )
                add_debug_msg(f"[NOTE_TYPE_SYNC]    Old:      '{old_name}'")
                add_debug_msg(f"[NOTE_TYPE_SYNC]    Expected: '{expected_name}'")

                # 3. RENAME IN ANKI: Update physical note type name
                from anki.models import NotetypeId

                note_type_obj = mw.col.models.get(NotetypeId(note_type_id_int))
                if note_type_obj:
                    old_anki_name = note_type_obj.get("name", "")
                    note_type_obj["name"] = expected_name
                    mw.col.models.save(note_type_obj)

                    add_debug_msg(
                        f"[NOTE_TYPE_SYNC] ✅ Renamed in Anki: '{old_anki_name}' -> '{expected_name}'"
                    )
                    result["renamed_in_anki"] += 1
                else:
                    add_debug_msg(
                        f"[NOTE_TYPE_SYNC] ⚠️ Note type {note_type_id} not found in Anki"
                    )

                # 4. UPDATE META.JSON: Update name in configuration
                note_types[note_type_id] = expected_name
                result["updated_in_meta"] += 1

                # 5. CHECK NOTES: Ensure notes are in the correct note type
                # (Normally notes automatically follow note_type in Anki)

                result["updated_count"] += 1

            except Exception as e:
                add_debug_msg(
                    f"[NOTE_TYPE_SYNC] ❌ Error processing {note_type_id}: {e}"
                )
                continue

        # Save meta.json changes if there were updates
        if result["updated_in_meta"] > 0:
            save_meta(meta)
            add_debug_msg(
                f"[NOTE_TYPE_SYNC] ✅ Meta.json saved with {result['updated_in_meta']} updates"
            )

        # Save Anki changes
        if result["renamed_in_anki"] > 0:
            mw.col.save()
            add_debug_msg(
                f"[NOTE_TYPE_SYNC] ✅ Anki saved with {result['renamed_in_anki']} note_types renamed"
            )

        return result

    except Exception as e:
        add_debug_msg(
            f"[NOTE_TYPE_SYNC] ❌ General error in robust synchronization: {e}"
        )
        import traceback

        add_debug_msg(f"[NOTE_TYPE_SYNC] Traceback: {traceback.format_exc()}")
        return {"updated_count": 0, "renamed_in_anki": 0, "updated_in_meta": 0}


# =============================================================================
# DEBUG LOG CONFIGURATION
# =============================================================================


def should_accumulate_logs():
    """Checks if logs should be accumulated over time."""
    meta = get_meta()
    return meta.get("config", {}).get("accumulate_logs", True)


def set_accumulate_logs(enabled):
    """Sets whether logs should be accumulated over time."""
    meta = get_meta()
    if "config" not in meta:
        meta["config"] = {}
    meta["config"]["accumulate_logs"] = enabled
    save_meta(meta)


# =============================================================================
# IMAGE PROCESSOR CONFIGURATION
# =============================================================================
