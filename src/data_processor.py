"""
Data and note processing for the Sheets2Anki addon.

This module contains functionalities for:
- Downloading and analyzing remote decks from Google Sheets
- Processing TSV data
- Creating and updating notes in Anki
- Managing cloze cards and hierarchical tags

Consolidated from:
- parseRemoteDeck.py: Remote deck analysis
- note_processor.py: Note processing
"""

# =============================================================================
# IMPORTS
# =============================================================================

import urllib.error
import urllib.request

from . import column_model
from . import tsv_model
from .column_model import deck_path
from .column_model import row_is_marked_for_sync

# Re-exported so `from .data_processor import X` keeps resolving for everything that
# already imported these from here. The definitions live in the pure layer because
# the preview site runs those very files in the browser and must not need Anki;
# see tsv_model's docstring.
from .errors import RemoteDeckError  # noqa: F401  (facade)
from .sheet_config import SheetConfig
from .templates_and_definitions import ensure_custom_models
from .tsv_model import TAG_ROOT  # noqa: F401  (facade)
from .tsv_model import RemoteDeck  # noqa: F401  (facade)
from .tsv_model import build_remote_deck_from_tsv  # noqa: F401  (facade)
from .tsv_model import build_tags  # noqa: F401  (facade)
from .tsv_model import clean_tag_text  # noqa: F401  (facade)
from .tsv_model import deck_root_name
from .tsv_model import has_cloze_deletion  # noqa: F401  (facade)
from .tsv_model import parse_tsv_data  # noqa: F401  (facade)
from .tsv_model import row_has_cloze  # noqa: F401  (facade)
from .utils import add_debug_message
from .utils import ensure_subdeck_exists
from .utils import get_subdeck_name


def add_debug_msg(message, category="DATA_PROCESSOR"):
    """Local helper for debug messages."""
    add_debug_message(message, category)


# The pure layer cannot import utils (that import is what would stop it loading in
# the browser), so the add-on hands it the real debug log here instead.
tsv_model.set_addon_logger(add_debug_message)


# Import mw safely
try:
    from .compat import mw
except ImportError:
    # Fallback for direct import
    try:
        from aqt import mw
    except ImportError:
        mw = None

# =============================================================================
# DATA CLASSES
# =============================================================================


# =============================================================================
# REMOTE DECK ANALYSIS FUNCTIONS
# =============================================================================


def getRemoteDeck(url, debug_messages=None):
    """
    Main function to obtain and process a remote deck.

    This function coordinates the entire process of downloading, analyzing, and building
     the remote deck from a Google Sheets spreadsheet URL.

    Args:
        url (str): Spreadsheet URL in TSV format
        debug_messages (list, optional): List to accumulate debug messages

    Returns:
        RemoteDeck: Processed remote deck object

    Raises:
        RemoteDeckError: If there's an error in deck processing
    """

    def add_debug_msg(message, category="REMOTE_DECK"):
        """Helper to add debug messages with timestamp."""
        from datetime import datetime

        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] [{category}] {message}"
        if debug_messages is not None:
            debug_messages.append(formatted_msg)

    try:
        add_debug_msg(f"Starting remote deck download: {url}")

        # 1. Download the sheet this deck syncs.
        #
        # A deck that names a sheet needs the whole file, because Google's export
        # can only hand over one sheet and offers no way to say which. A deck that
        # names none was connected before sheets could be told apart, and keeps
        # downloading exactly what it always did.
        tsv_data = download_deck_tsv(url)
        add_debug_msg(f"Download complete: {len(tsv_data)} bytes")

        # 2. Parse TSV data
        parsed_data = parse_tsv_data(tsv_data, debug_messages)
        add_debug_msg(f"Parse complete: {len(parsed_data['rows'])} lines")

        # 3. Build remote deck
        remote_deck = build_remote_deck_from_tsv(parsed_data, url, debug_messages)

        stats = remote_deck.get_statistics()
        add_debug_msg(
            f"Deck built: {stats['sync_marked_lines']}/{stats['valid_note_lines']} lines marked for sync"
        )
        add_debug_msg(
            f"Final metrics: {stats['total_potential_anki_notes']} potential notes"
        )

        return remote_deck

    except Exception as e:
        add_debug_msg(f"Error processing remote deck: {e}")
        raise RemoteDeckError(f"Error obtaining remote deck: {str(e)}")


def _refuse_unsafe_url(download_url):
    """Refuses an address the add-on has no business fetching.

    Defence in depth against SSRF. A deck URL is typed or pasted in, and a URL
    someone else supplies is a URL someone else chose: Anki runs on the user's own
    machine, inside their own network, so an address like
    ``http://192.168.1.1/admin`` or ``http://169.254.169.254/`` would have the
    add-on knock on doors nothing outside that network can reach.

    Google's own hosts used to be the only ones allowed. A deck can now be a file
    at a plain address — a .xlsx in a GitHub repository, say — so the rule is what
    is left once the arbitrary-host part is given up:

    * https only, so nothing is read over a connection that can be tampered with
      and no other scheme (``file://``, ``ftp://``) gets in;
    * every address the name resolves to must be a public one.

    Resolving first and checking the answers is the point: a hostname is under
    whoever owns it, and "internal.example.com" pointing at 10.0.0.1 is the
    ordinary way this is abused.
    """
    import ipaddress
    import socket
    from urllib.parse import urlparse

    parts = urlparse(download_url)
    if parts.scheme != "https":
        raise RemoteDeckError(
            f"Refusing to download over '{parts.scheme}': the deck URL must be https."
        )

    host = (parts.hostname or "").lower()
    if not host:
        raise RemoteDeckError("The deck URL has no host in it.")

    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(host, parts.port or 443)}
    except OSError as e:
        raise RemoteDeckError(f"Could not look up '{host}': {e}")

    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise RemoteDeckError(
                f"Refusing to download from '{host}': it resolves to {address}, "
                f"which is inside a private network. A deck has to come from a "
                f"public address."
            )


def _download(download_url, timeout):
    """The bytes at a URL a deck may legitimately come from.

    Shared by the TSV and whole-file paths so both carry the same address check
    and the same explanation of a 400, which is nearly always an unshared sheet.
    """
    _refuse_unsafe_url(download_url)

    headers = {"User-Agent": "Mozilla/5.0 (Sheets2Anki) AnkiAddon"}
    request = urllib.request.Request(download_url, headers=headers)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.getcode() != 200:
                raise RemoteDeckError(
                    f"HTTP {response.getcode()}: Failed to access URL"
                )
            return response.read()

    except TimeoutError:
        raise RemoteDeckError(f"Timeout of {timeout}s while accessing the URL")
    except urllib.error.HTTPError as e:
        if e.code == 400:
            raise RemoteDeckError(
                "HTTP Error 400: The spreadsheet is not publicly accessible.\n\n"
                "To fix:\n"
                "1. Open spreadsheet in Google Sheets\n"
                "2. Click 'Share'\n"
                "3. Change access to 'Anyone with the link'\n"
                "4. Set permission to 'Viewer'\n\n"
                "Alternatively: File → Share → Publish to web"
            )
        else:
            raise RemoteDeckError(f"HTTP Error {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise RemoteDeckError(f"URL Error: {str(e.reason)}")
    except RemoteDeckError:
        raise
    except Exception as e:
        raise RemoteDeckError(f"Unexpected download error: {str(e)}")


def download_tsv_data(url, timeout=30):
    """
    Downloads TSV data from a URL.

    Supports both edition and TSV format URLs, automatically converting when necessary.

    Args:
        url (str): URL for download (can be edition or TSV format)
        timeout (int): Timeout in seconds

    Returns:
        str: TSV data as string

    Raises:
        RemoteDeckError: If there's an error in download
    """
    from .utils import convert_edit_url_to_tsv

    try:
        # If URL is already in TSV format, use directly
        if "/export?format=tsv" in url:
            tsv_url = url
        else:
            tsv_url = convert_edit_url_to_tsv(url)
    except ValueError as e:
        raise RemoteDeckError(f"Invalid URL: {str(e)}")

    # utf-8-sig so a UTF-8 BOM that some Google export paths prepend is stripped
    # instead of corrupting the first header (e.g. "﻿ID"), which would fail the
    # required-header check.
    return _download(tsv_url, timeout).decode("utf-8-sig")


# The file behind each spreadsheet id, for the length of one sync run. Syncing
# five decks that live in one Google Sheets file is five decks' worth of work but
# one download — without this it would fetch the same file five times.
_WORKBOOK_CACHE = {}


def clear_workbook_cache():
    """Forgets the downloaded files. Called at the start of every sync run.

    Held any longer and a sync would show the sheet as it was the last time Anki
    was opened, which is the one thing a sync must not do.
    """
    _WORKBOOK_CACHE.clear()


def download_workbook(url, timeout=30):
    """The whole spreadsheet file, every sheet in it, cached for this sync run."""
    from .utils import convert_edit_url_to_xlsx
    from .utils import source_id

    try:
        key = source_id(url)
        xlsx_url = convert_edit_url_to_xlsx(url)
    except ValueError as e:
        raise RemoteDeckError(f"Invalid URL: {str(e)}")

    if key not in _WORKBOOK_CACHE:
        _WORKBOOK_CACHE[key] = _download(xlsx_url, timeout)
    return _WORKBOOK_CACHE[key]


def download_sheet_names(url, timeout=30):
    """The sheets inside the file a URL points at, in the order it lists them."""
    from .workbook import WorkbookError
    from .workbook import sheet_names

    try:
        return sheet_names(download_workbook(url, timeout))
    except WorkbookError as e:
        raise RemoteDeckError(str(e))


class SheetOffer:
    """One sheet in a file, and whether it can become a deck.

    ``deck`` is the built RemoteDeck when the sheet is usable, and ``problem`` is
    the plain reason when it is not. A file people actually keep has drafts,
    notes and a colour key in it alongside the vocabulary; refusing the whole
    file because one sheet has no ID column would make the feature useless.
    """

    def __init__(self, name, deck=None, problem=None):
        self.name = name
        self.deck = deck
        self.problem = problem

    @property
    def usable(self):
        return self.deck is not None

    def __repr__(self):
        state = "usable" if self.usable else f"skipped: {self.problem}"
        return f"<SheetOffer {self.name!r} {state}>"


def read_all_sheets(url, timeout=30, debug_messages=None):
    """Every sheet in the file behind a URL, each judged on its own.

    One download serves all of them. Used when a link is connected, to decide
    what it becomes, and by the same code that then syncs each one.
    """
    from .utils import url_for_sheet

    offers = []
    for name in download_sheet_names(url, timeout):
        sheet_url = url_for_sheet(url, name)
        try:
            tsv = download_deck_tsv(sheet_url, timeout)
            parsed = parse_tsv_data(tsv, debug_messages)
            deck = build_remote_deck_from_tsv(parsed, sheet_url, debug_messages)
            offers.append(SheetOffer(name, deck=deck))
        except RemoteDeckError as e:
            offers.append(SheetOffer(name, problem=str(e)))
    return offers


def download_deck_tsv(url, timeout=30):
    """One deck's sheet as TSV, whichever way that deck has to be fetched."""
    from .utils import is_spreadsheet_file_url
    from .utils import sheet_name_from_url
    from .workbook import WorkbookError
    from .workbook import sheet_tsv
    from .workbook import sheet_tsv_by_index

    sheet = sheet_name_from_url(url)
    if not sheet:
        # A file has no per-sheet download to fall back to, so its first sheet is
        # read out of the file the same way a named one is. Only a Google Sheet
        # has the TSV export, and only a deck predating named sheets uses it.
        if is_spreadsheet_file_url(url):
            return sheet_tsv_by_index(download_workbook(url, timeout), 0)
        return download_tsv_data(url, timeout)

    try:
        return sheet_tsv(download_workbook(url, timeout), sheet)
    except WorkbookError as e:
        # A sheet renamed or deleted in Google Sheets since the deck was
        # connected. Saying which sheets do exist is the difference between a
        # fixable message and a mystery.
        raise RemoteDeckError(str(e))


# =============================================================================
# NOTE PROCESSING FUNCTIONS
# =============================================================================


def get_deck_sheet_config(deck_url):
    """
    The sheet settings the last sync cached for this deck.

    Used on the paths that provision a note type without holding the downloaded deck
    (a model that went missing mid-sync). The current sync writes the cache before
    any note is processed, so this is the same settings row the rest of the sync uses.

    Args:
        deck_url (str): Remote deck URL

    Returns:
        SheetConfig: the cached settings, or the plain defaults when none are cached
    """
    from .config_manager import get_deck_id
    from .sync_config import cached_plan_and_config

    try:
        _, sheet_config = cached_plan_and_config(get_deck_id(deck_url))
    except Exception as e:
        # No usable spreadsheet id (URL missing or malformed): render the sheet's own
        # column order instead of failing the whole sync.
        add_debug_msg(f"Could not read cached sheet settings ({e}); using defaults")
        return SheetConfig()

    return sheet_config or SheetConfig()


def cache_deck_sheet_config(deck_url, plan, sheet_config):
    """Records this sync's settings row so later rebuilds can render without it."""
    from .config_manager import get_deck_id
    from .sync_config import cache_sheet_settings

    try:
        cache_sheet_settings(get_deck_id(deck_url), plan, sheet_config)
    except Exception as e:
        add_debug_msg(f"Could not cache the sheet's settings ({e})")


def get_target_model(col, plan, deck_url, is_cloze, debug_messages=None):
    """
    Returns the note type a row belongs in, provisioning it if it is missing.

    Args:
        col: Anki collection
        plan (ColumnPlan): How this sheet's headers map onto Anki
        deck_url (str): Remote deck URL
        is_cloze (bool): Whether the row produces a cloze note
        debug_messages (list, optional): Debug list

    Returns:
        tuple: (model or None, note_type_name)
    """
    from .config_manager import get_deck_remote_name
    from .utils import get_note_type_name

    remote_deck_name = get_deck_remote_name(deck_url)
    note_type_name = get_note_type_name(deck_url, remote_deck_name, is_cloze=is_cloze)

    model = col.models.by_name(note_type_name)
    if model:
        return model, note_type_name

    # The note type is missing or registered under another name — rebuild it.
    models = ensure_custom_models(
        col,
        deck_url,
        plan,
        get_deck_sheet_config(deck_url),
        debug_messages=debug_messages,
    )
    return models.get("cloze" if is_cloze else "standard"), note_type_name


def create_or_update_notes(
    col, remoteDeck, deck_id, deck_url=None, debug_messages=None
):
    """
    Creates or updates notes in the deck based on remote data.

    Each remote spreadsheet row with a unique ID produces exactly one Anki note, keyed
    by that ID. The key is written into the note's ID field and must never be modified
    after creation — it is how a note is matched back to its row. A reverse card is a
    second card template on the same note, not a second note.

    Args:
        col: Anki collection object
        remoteDeck (RemoteDeck): Remote deck object containing sync data
        deck_id (int): Anki deck ID to sync
        deck_url (str, optional): Remote deck URL

    Returns:
        dict: Sync statistics containing counts for created, updated,
              deleted notes and errors

    Raises:
        SyncError: If there are critical errors during synchronization
        CollectionSaveError: If saving collection fails
    """

    def add_debug_msg(message, category="NOTE_PROCESSOR"):
        """Helper to add debug messages using global system."""
        from .utils import add_debug_message

        add_debug_message(message, category)

    add_debug_msg("🔧 Starting note synchronization")
    add_debug_msg(f"🔧 remoteDeck contains {len(remoteDeck.notes)} notes")

    # Import SyncStats
    from .sync import SyncStats

    # Create statistics object with refactored metrics
    stats = SyncStats()

    # Copy metrics already calculated from RemoteDeck
    deck_stats = remoteDeck.get_statistics()
    stats.remote_total_table_lines = deck_stats["total_table_lines"]
    stats.remote_valid_note_lines = deck_stats["valid_note_lines"]
    stats.remote_invalid_note_lines = deck_stats["invalid_note_lines"]
    stats.remote_ignored_ghost_rows = deck_stats.get("ignored_ghost_rows", 0)
    stats.remote_sync_marked_lines = deck_stats["sync_marked_lines"]
    stats.remote_total_potential_anki_notes = deck_stats["total_potential_anki_notes"]

    plan = remoteDeck.plan

    # The sheet's own ID column; its value is the note's key.
    id_header = plan.id_header
    # The first content column stands in for the note in the sync report.
    preview_header = plan.content_headers[0] if plan.content_headers else id_header

    # Surface duplicate spreadsheet IDs (detected during deck build) so the user can fix
    # them — duplicates silently strand notes that share the same key.
    # Anything the settings row got wrong belongs in the sync summary, not only in
    # the debug log — the log is written only while Debug Mode is on, so a typo like
    # "siz=48" would otherwise be invisible and the setting would just never apply.
    for warning in getattr(remoteDeck.sheet_config, "warnings", []):
        stats.warnings.append(f"Settings row — {warning}")

    if getattr(remoteDeck, "duplicate_ids", None):
        shown = ", ".join(remoteDeck.duplicate_ids[:10])
        suffix = " ..." if len(remoteDeck.duplicate_ids) > 10 else ""
        stats.add_error(
            f"Duplicate IDs in the spreadsheet ({len(remoteDeck.duplicate_ids)}): {shown}{suffix}. "
            f"Each '{column_model.IDENTIFIER}' must be unique — duplicate rows are not all synced."
        )

    try:
        # 1. Build the set of note keys the spreadsheet expects to exist.
        expected_note_ids = set()
        for note_data in remoteDeck.notes:
            note_id = str(note_data.get(id_header, "")).strip()
            if note_id and row_is_marked_for_sync(note_data, plan):
                expected_note_ids.add(note_id)

        add_debug_msg("=== REMOTE DECK METRICS ===")
        add_debug_msg(f"📊 Total table lines: {stats.remote_total_table_lines}")
        add_debug_msg(f"✅ Valid lines (filled ID): {stats.remote_valid_note_lines}")
        add_debug_msg(f"❌ Invalid lines (empty ID): {stats.remote_invalid_note_lines}")
        add_debug_msg(f"🔄 Lines marked for sync: {stats.remote_sync_marked_lines}")
        add_debug_msg(
            f"🚀 Total potential notes in Anki: {stats.remote_total_potential_anki_notes}"
        )
        add_debug_msg(f"🎯 Note keys for synchronization: {len(expected_note_ids)}")

        # 2. Ensure the deck's note types match the sheet's columns and its settings
        # row (this provisions the basic and cloze models in one call). The settings
        # are cached first so anything that rebuilds a model later in this sync —
        # or outside one — renders exactly what the sheet just asked for.
        sheet_config = remoteDeck.sheet_config
        cache_deck_sheet_config(deck_url, plan, sheet_config)
        ensure_custom_models(
            col, deck_url, plan, sheet_config, debug_messages=debug_messages
        )

        # 3. Get existing notes by note key
        existing_notes = get_existing_notes_by_id(col, deck_id)
        add_debug_msg(f"Found {len(existing_notes)} existing notes in deck")

        def process_note(note_data, note_id):
            """Creates or updates a single note and records it in stats."""
            try:
                if note_id in existing_notes:
                    success, was_updated, changes = update_existing_note(
                        col,
                        existing_notes[note_id],
                        note_data,
                        plan,
                        deck_url,
                        sheet_config=sheet_config,
                        debug_messages=debug_messages,
                    )
                    if not success:
                        stats.add_error(f"Error updating note: {note_id}")
                        add_debug_msg(f"❌ Error updating note: {note_id}")
                        return

                    if was_updated:
                        stats.updated += 1
                        stats.update_details.append(
                            {
                                "note_id": note_id,
                                "changes": changes,
                            }
                        )
                        add_debug_msg(f"✅ Note updated: {note_id}")
                    else:
                        stats.unchanged += 1
                        add_debug_msg(f"⏭️ Note unchanged: {note_id}")
                    return

                if create_new_note(
                    col,
                    note_data,
                    plan,
                    deck_id,
                    deck_url,
                    sheet_config=sheet_config,
                    debug_messages=debug_messages,
                ):
                    stats.created += 1
                    preview = str(note_data.get(preview_header, ""))
                    stats.creation_details.append(
                        {
                            "note_id": note_id,
                            "pergunta": preview[:100]
                            + ("..." if len(preview) > 100 else ""),
                        }
                    )
                    add_debug_msg(f"✅ Note created: {note_id}")
                else:
                    stats.add_error(f"Error creating note: {note_id}")
                    add_debug_msg(f"❌ Error creating note: {note_id}")

            except Exception as e:
                import traceback

                error_details = traceback.format_exc()
                add_debug_msg(f"❌ Error processing {note_id}: {e}")
                add_debug_msg(f"❌ Stack trace: {error_details}")
                stats.add_error(f"Exception processing {note_id}: {str(e)}")

        # 4. Process each remote note
        for note_data in remoteDeck.notes:
            note_id = str(note_data.get(id_header, "")).strip()
            if not note_id:
                # Empty ID line is not an error, it's a normal situation already accounted for in metrics
                continue

            # Check if it should sync
            if not row_is_marked_for_sync(note_data, plan):
                stats.skipped += 1
                continue

            process_note(note_data, note_id)

        # 5. Separate obsolete notes from sync-disabled notes
        all_existing_note_ids = set(existing_notes.keys())

        # SAFETY GUARD (prevents catastrophic data loss):
        # If the remote spreadsheet returned ZERO valid note lines (no row had a filled
        # ID) — e.g. an empty sheet, the wrong tab/gid, or a transient export that returns
        # a valid-but-empty body — then EVERY existing note would look "obsolete" below and
        # be deleted, wiping the whole deck. Refuse to delete in that case: preserve all
        # notes and surface a warning so the user can fix the source and re-sync.
        if remoteDeck.valid_note_lines == 0 and all_existing_note_ids:
            warning = (
                f"Sync safety: the spreadsheet returned no valid rows (every row had an "
                f"empty '{column_model.IDENTIFIER}'). Skipped deletion of {len(all_existing_note_ids)} "
                f"existing note(s) to prevent accidental data loss. Verify the sheet/tab is "
                f"correct and not empty, then sync again."
            )
            add_debug_msg(f"🛡️ {warning}")
            stats.add_error(warning)
            return stats

        # 5.1. Identify obsolete notes (no longer in spreadsheet) vs sync-disabled ones.
        # Lookup of remote spreadsheet IDs -> sync-enabled flag, keyed by the raw
        # ID-column value.
        remote_id_sync = {}
        for note_data in remoteDeck.notes:
            rid = str(note_data.get(id_header, "")).strip()
            if rid:
                remote_id_sync[rid] = row_is_marked_for_sync(note_data, plan)

        notes_really_obsolete = set()
        notes_with_sync_disabled = set()

        for note_key in all_existing_note_ids - expected_note_ids:
            if note_key in remote_id_sync:
                # Row exists but SYNC=false - ALWAYS preserve (user intentionally disabled sync)
                notes_with_sync_disabled.add(note_key)
                add_debug_msg(f"⏸️ Note with SYNC disabled (preserving): {note_key}")
            else:
                # Note's ID is no longer present anywhere in the spreadsheet.
                notes_really_obsolete.add(note_key)
                add_debug_msg(
                    f"📝 Obsolete note (removed from spreadsheet): {note_key}"
                )

        # 5.2. Remove obsolete notes
        add_debug_msg(f"🗑️ Removing {len(notes_really_obsolete)} obsolete notes")
        for note_key in notes_really_obsolete:
            try:
                note_to_delete = existing_notes[note_key]
                if delete_note_by_id(col, note_to_delete):
                    stats.deleted += 1
                    # Extract preview text for better logging
                    pergunta = ""
                    try:
                        if preview_header in note_to_delete.keys():
                            full_pergunta = note_to_delete[preview_header]
                            pergunta = full_pergunta[:100] + (
                                "..." if len(full_pergunta) > 100 else ""
                            )
                    except Exception:
                        pass
                    # Capture deletion details
                    stats.deletion_details.append(
                        {
                            "note_id": note_key,
                            "reason": "obsolete",
                            "pergunta": pergunta,
                        }
                    )
                    add_debug_msg(f"✅ Obsolete note removed: {note_key}")
            except Exception as e:
                add_debug_msg(f"❌ Error removing obsolete note {note_key}: {e}")
                stats.add_error(f"Error removing obsolete note {note_key}: {str(e)}")

        # 5.3. Log sync-disabled notes (always preserved)
        if notes_with_sync_disabled:
            add_debug_msg(
                f"⏸️ Preserving {len(notes_with_sync_disabled)} notes with SYNC disabled (user choice)"
            )
            for note_key in notes_with_sync_disabled:
                add_debug_msg(f"⏸️ SYNC disabled, preserving: {note_key}")

        # 6. Final statistics
        add_debug_msg("=== FINAL STATISTICS ===")
        add_debug_msg(f"✅ Notes created: {stats.created}")
        add_debug_msg(f"🔄 Notes updated: {stats.updated}")
        add_debug_msg(f"🗑️ Notes removed: {stats.deleted}")
        add_debug_msg(f"⏭️ Notes unchanged: {stats.unchanged}")
        add_debug_msg(f"⏸️ Notes ignored: {stats.skipped}")
        add_debug_msg(f"❌ Errors: {stats.errors}")

        # Anki persists collection changes itself; col.save() is a deprecated no-op.

        add_debug_msg(
            f"🎯 Synchronization complete: +{stats.created} ~{stats.updated} ={stats.unchanged} -{stats.deleted} !{stats.errors}"
        )

        return stats

    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        add_debug_msg(f"❌ CRITICAL ERROR in synchronization: {e}")
        add_debug_msg(f"❌ Full stack trace: {error_details}")

        # Return stats with error
        if stats.remote_total_table_lines == 0:
            stats.remote_total_table_lines = (
                len(remoteDeck.notes) if remoteDeck and remoteDeck.notes else 0
            )
        stats.add_error(f"Critical error in synchronization: {str(e)}")
        # Ensure at least 1 error is counted even if add_error logic changes
        if stats.errors == 0:
            stats.errors = 1
        return stats


def get_existing_notes_by_id(col, deck_id):
    """
    Obtains mapping of existing notes in the deck by note key.

    - Searches all notes in the deck and its subdecks
    - Reads each note's key straight out of its ID field, which holds the
      spreadsheet ID
    - Returns mapping {note_id: note_object}

    Args:
        col: Anki collection
        deck_id (int): Deck ID

    Returns:
        dict: Mapping {note_id: note_object}
    """
    existing_notes = {}

    try:
        # Get the main deck
        deck = col.decks.get(deck_id)
        if not deck:
            return existing_notes

        deck_name = deck["name"]

        # Search for cards in the main deck AND in all subdecks
        # Escape double quotes in deck name to avoid search errors
        escaped_deck_name = deck_name.replace('"', '\\"')
        search_query = f'deck:"{escaped_deck_name}" OR deck:"{escaped_deck_name}::*"'

        # Check if query is not empty or malformed
        if not deck_name.strip():
            add_debug_msg(
                "[DECK_SEARCH] Error: Deck name is empty, using ID search",
                category="DECK_BUILD",
            )
            search_query = f"deck:{deck_id}"

        card_ids = col.find_cards(search_query)

        for card_id in card_ids:
            try:
                card = col.get_card(card_id)
                note = card.note()

                # Get note key from ID field
                if column_model.IDENTIFIER in note.keys():
                    note_id = note[column_model.IDENTIFIER].strip()
                    if note_id:
                        existing_notes[note_id] = note

            except Exception as e:
                add_debug_msg(
                    f"Error processing card {card_id}: {e}", category="DECK_SEARCH"
                )
                continue

    except Exception as e:
        add_debug_msg(f"Error obtaining existing notes: {e}", category="DECK_SEARCH")

    return existing_notes


def create_new_note(
    col, note_data, plan, deck_id, deck_url, sheet_config=None, debug_messages=None
):
    """
    Creates a new Anki note from a spreadsheet row.

    Args:
        col: Anki collection
        note_data (dict): Spreadsheet note data
        plan (ColumnPlan): How this sheet's headers map onto Anki
        deck_id (int): Base deck ID
        deck_url (str): Remote deck URL
        debug_messages (list, optional): Debug list

    Returns:
        bool: True if created successfully, False otherwise
    """

    def add_debug_msg(message, category="CREATE_NOTE"):
        """Helper to add debug messages using global system."""
        from .utils import add_debug_message

        add_debug_message(message, category)

    try:
        note_id = str(note_data.get(plan.id_header, "")).strip()
        add_debug_msg(f"Creating new note: {note_id}")

        # Whether a sheet is a cloze sheet is a property of the sheet, not of a
        # row: one note type and one template set serve every row, so the column
        # carrying the deletions is declared once in the settings row. Deciding it
        # per row is what used to produce cards whose prompt was blank.
        settings = sheet_config or get_deck_sheet_config(deck_url)
        is_cloze = bool(settings.cloze_field)
        model, note_type_name = get_target_model(
            col, plan, deck_url, is_cloze, debug_messages
        )

        add_debug_msg(f"Note type: {note_type_name}")

        if not model:
            add_debug_msg(
                f"❌ CRITICAL ERROR: Could not create/find model: {note_type_name}"
            )
            return False

        add_debug_msg(f"✅ Model found: {note_type_name} (ID: {model['id']})")

        # Create note
        note = col.new_note(model)

        # Fill fields (the ID field receives the note's unique key)
        fill_note_fields(note, note_data, plan)

        # Add tags
        tags = note_data.get("tags", [])
        if tags:
            note.tags = tags

        # Determine target subdeck
        add_debug_msg(f"Determining target deck for note: {note_id}")
        target_deck_id = determine_target_deck(
            col, deck_id, note_data, plan, deck_url, sheet_config, debug_messages
        )
        add_debug_msg(f"Target deck determined: {target_deck_id}")

        # Add note to deck
        add_debug_msg(f"Adding note {note_id} to deck {target_deck_id}")
        col.add_note(note, target_deck_id)
        add_debug_msg(f"✅ Note {note_id} successfully added to deck {target_deck_id}")

        return True

    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        add_debug_msg(
            f"❌ ERROR creating note {note_data.get(plan.id_header, 'UNKNOWN')}: {e}"
        )
        add_debug_msg(f"❌ Stack trace: {error_details}")
        return False


def note_fields_need_update(existing_note, new_data, plan, debug_messages=None):
    """
    Checks if a note needs update by comparing fields and tags.

    The ID field is not compared: it holds the note's key and must stay unchanged.
    Every content column the note actually has a field for is compared against the
    spreadsheet data — a column the sheet dropped keeps whatever the note holds.

    Args:
        existing_note: Existing Anki note
        new_data (dict): New note data
        plan (ColumnPlan): How this sheet's headers map onto Anki
        debug_messages (list, optional): Debug list

    Returns:
        tuple: (needs_update: bool, changes: list)
    """

    def add_debug_msg(message, category="NOTE_COMPARISON"):
        """Helper to add debug messages using global system."""
        from .utils import add_debug_message

        add_debug_message(message, category)

    changes = []

    # Compare content fields (the derived ID is never compared)
    for header in plan.content_headers:
        if header not in existing_note:
            continue

        old_value = str(existing_note[header]).strip()
        new_value = str(new_data.get(header, "")).strip()

        if old_value != new_value:
            # Truncate for log if too long
            old_display = old_value[:50] + "..." if len(old_value) > 50 else old_value
            new_display = new_value[:50] + "..." if len(new_value) > 50 else new_value
            changes.append(f"{header}: '{old_display}' → '{new_display}'")

    # Compare tags (case-insensitive, since Anki treats tags as case-insensitive)
    # This prevents infinite update loops when only the case of a tag changes
    existing_tags = set(existing_note.tags) if hasattr(existing_note, "tags") else set()
    new_tags = set(new_data.get("tags", []))

    # Create case-insensitive versions for comparison
    existing_tags_lower = {tag.lower() for tag in existing_tags}
    new_tags_lower = {tag.lower() for tag in new_tags}

    # Detailed tag debug
    add_debug_msg(f"🏷️ Existing tags: {sorted(existing_tags)}")
    add_debug_msg(f"🏷️ New tags: {sorted(new_tags)}")

    # Compare case-insensitively to avoid false positives from case-only changes
    if existing_tags_lower != new_tags_lower:
        # Find truly added tags (not just case changes)
        added_tags_lower = new_tags_lower - existing_tags_lower
        removed_tags_lower = existing_tags_lower - new_tags_lower

        # Get the original-cased tags for display
        added_tags = {tag for tag in new_tags if tag.lower() in added_tags_lower}
        removed_tags = {
            tag for tag in existing_tags if tag.lower() in removed_tags_lower
        }

        add_debug_msg("🏷️ Different tags detected!")
        if added_tags:
            changes.append(f"Tags added: {', '.join(added_tags)}")
            add_debug_msg(f"🏷️ Added: {sorted(added_tags)}")
        if removed_tags:
            changes.append(f"Tags removed: {', '.join(removed_tags)}")
            add_debug_msg(f"🏷️ Removed: {sorted(removed_tags)}")
    else:
        # Check if there are case-only differences (for logging purposes only)
        if existing_tags != new_tags:
            add_debug_msg(
                "🏷️ Tags differ only in case - treating as identical (Anki is case-insensitive)"
            )
        else:
            add_debug_msg("🏷️ Tags are identical")

    needs_update = len(changes) > 0

    if needs_update:
        add_debug_msg(f"Note needs update. Changes detected: {'; '.join(changes)}")
    else:
        add_debug_msg("Note does NOT need update - identical content")

    return needs_update, changes


def update_existing_note(
    col, existing_note, new_data, plan, deck_url, sheet_config=None, debug_messages=None
):
    """
    Updates an existing note.
    IMPORTANT: Only updates if there are real differences between local and remote content.

    Args:
        col: Anki collection
        existing_note: Existing Anki note
        new_data (dict): New note data
        plan (ColumnPlan): How this sheet's headers map onto Anki
        deck_url (str): Deck URL
        debug_messages (list, optional): Debug list

    Returns:
        tuple: (success: bool, was_updated: bool, changes: list)
    """

    def add_debug_msg(message, category="UPDATE_NOTE"):
        """Helper to add debug messages using global system."""
        from .utils import add_debug_message

        add_debug_message(message, category)

    try:
        note_id = str(new_data.get(plan.id_header, "")).strip()
        add_debug_msg(f"Checking if note {note_id} needs update")

        # Same sheet-level answer as when the note was created — see create_note.
        settings = sheet_config or get_deck_sheet_config(deck_url)
        is_cloze = bool(settings.cloze_field)
        target_model, _ = get_target_model(
            col, plan, deck_url, is_cloze, debug_messages
        )

        # Check for real differences between existing note and new data
        # We MUST do this before type change to capture field differences
        needs_update, changes = note_fields_need_update(
            existing_note, new_data, plan, debug_messages
        )

        # Check if note type needs to be changed (e.g. Basic -> Cloze)
        # This check is now outside the 'needs_update' return to ensure type is corrected
        # even if content is already identical (e.g. failed previous sync or manual change)
        if target_model and existing_note.mid != target_model["id"]:
            old_type_name = existing_note.note_type()["name"]
            new_type_name = target_model["name"]

            add_debug_msg(
                f"🔄 Note {note_id}: Note type change detected! '{old_type_name}' → '{new_type_name}'"
            )

            try:
                # Strategy: recreate the note with the correct note type, because Anki's
                # ModelManager has no direct API to retype an existing note in place.
                # IMPORTANT: create the replacement FIRST and remove the old note only
                # after the new one exists, so a failure can never leave the user with no
                # note at all (the original is preserved on any error). Review history is
                # still reset on a type change — that is inherent to delete+recreate.

                # Get the current deck ID before recreating
                cards = existing_note.cards()
                current_deck_id = cards[0].did if cards else None
                old_note_id = existing_note.id

                # Recreate the note with the correct note type
                success = create_new_note(
                    col,
                    new_data,
                    plan,
                    current_deck_id,
                    deck_url,
                    sheet_config=settings,
                    debug_messages=debug_messages,
                )

                if success:
                    # Only now remove the old note — the replacement is safely in place.
                    col.remove_notes([old_note_id])
                    changes.append(
                        f"Note type changed (recreated): '{old_type_name}' → '{new_type_name}'"
                    )
                    add_debug_msg(
                        f"✅ Note {note_id} recreated with new type '{new_type_name}'; old note removed"
                    )
                    return True, True, changes  # Success, was updated (recreated)
                else:
                    # Keep the original note intact so no data is lost.
                    add_debug_msg(
                        f"❌ Failed to create replacement for note {note_id}; keeping original (type unchanged)"
                    )
                    return False, False, []

            except Exception as e:
                import traceback

                error_details = traceback.format_exc()
                add_debug_msg(f"❌ Error changing note type for {note_id}: {e}")
                add_debug_msg(f"❌ Stack trace: {error_details}")
                # The original note is only removed after a successful create, so it is
                # still present here — no data lost.
                return False, False, []

        if not needs_update:
            add_debug_msg(
                f"⏭️ Note {note_id} was not updated - identical content and note type"
            )
            return True, False, []  # Success, but not updated

        add_debug_msg(
            f"📝 Updating note {note_id} with changes: {'; '.join(changes[:3])}..."
        )

        # Fill fields with new data (the ID field keeps the note's unique key)
        fill_note_fields(existing_note, new_data, plan)

        # Update tags
        tags = new_data.get("tags", [])
        if tags:
            existing_note.tags = tags

        # Check if needs moving to different subdeck
        cards = existing_note.cards()
        if cards:
            current_deck_id = cards[0].did
            target_deck_id = determine_target_deck(
                col,
                current_deck_id,
                new_data,
                plan,
                deck_url,
                sheet_config,
                debug_messages,
            )

            if current_deck_id != target_deck_id:
                # Move cards to new deck
                for card in cards:
                    card.did = target_deck_id
                    col.update_card(card)

        # Save note changes
        existing_note.flush()

        add_debug_msg(f"✅ Note successfully updated: {note_id}")
        return True, True, changes  # Success, was updated, with changes list

    except Exception as e:
        add_debug_msg(f"❌ Error updating note: {e}")
        return False, False, []  # Error, no changes


def delete_note_by_id(col, note):
    """
    Removes a note from Anki.

    Args:
        col: Anki collection
        note: Note to be removed

    Returns:
        bool: True if removed successfully, False otherwise
    """
    try:
        col.remove_notes([note.id])
        return True
    except Exception as e:
        add_debug_msg(f"Error deleting note {note.id}: {e}", category="NOTE_PROCESSOR")
        return False


def fill_note_fields(note, note_data, plan):
    """
    Fills note fields with spreadsheet data.

    - The Anki note ID field is filled with the spreadsheet ID; this unique
      identifier should never be modified after creation
    - Every content column is written into the field of the same name
    - A field the note has but the sheet no longer supplies is left untouched, so a
      removed column does not wipe the content already collected under it

    Args:
        note: Anki note
        note_data (dict): Spreadsheet data
        plan (ColumnPlan): How this sheet's headers map onto Anki
    """
    note_fields = note.keys()

    if column_model.IDENTIFIER in note_fields:
        note[column_model.IDENTIFIER] = str(note_data.get(plan.id_header, "")).strip()

    for header in plan.content_headers:
        if header in note_fields:
            note[header] = str(note_data.get(header, "")).strip()


def determine_target_deck(
    col, base_deck_id, note_data, plan, deck_url, sheet_config=None, debug_messages=None
):
    """
    Determines the target subdeck for a note.

    The path is "s2a_{remote deck name}" followed by the row's deck levels — the
    reserved SUBDECK columns, or the content columns the settings row marked with
    ``subdeck=n`` — so a sheet that names neither keeps every note in the deck root.

    Args:
        col: Anki collection
        base_deck_id (int): Base deck ID
        note_data (dict): Note data
        plan (ColumnPlan): How this sheet's headers map onto Anki
        deck_url (str): Deck URL
        debug_messages (list, optional): Debug list

    Returns:
        int: Target deck ID
    """

    def add_debug_msg(message, category="DECK_TARGET"):
        """Helper to add debug messages using global system."""
        from .utils import add_debug_message

        add_debug_message(message, category)

    try:
        # Get base deck
        base_deck = col.decks.get(base_deck_id)
        if not base_deck:
            return base_deck_id

        # Generate subdeck name with full hierarchy
        from .config_manager import get_deck_remote_name

        remote_deck_name = get_deck_remote_name(deck_url)

        # Create base deck following pattern: s2a_{remote_deck_name}
        deck_with_remote_name = deck_root_name(remote_deck_name)
        subdeck_name = get_subdeck_name(
            deck_with_remote_name, deck_path(note_data, plan, sheet_config)
        )
        subdeck_id = ensure_subdeck_exists(subdeck_name)

        if subdeck_id:
            add_debug_msg(f"Note directed to subdeck: {subdeck_name}")
            return subdeck_id

        return base_deck_id

    except Exception as e:
        add_debug_msg(f"Error determining target deck: {e}")
        return base_deck_id
