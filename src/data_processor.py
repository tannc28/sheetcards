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

import csv
import io
import re
import urllib.error
import urllib.request

from . import templates_and_definitions as cols  # Centralized column definitions
from .templates_and_definitions import DEFAULT_CONCEPT
from .templates_and_definitions import DEFAULT_IMPORTANCE
from .templates_and_definitions import DEFAULT_SUBTOPIC
from .templates_and_definitions import DEFAULT_TOPIC
from .templates_and_definitions import TAG_ADDITIONAL
from .templates_and_definitions import TAG_CAREERS
from .templates_and_definitions import TAG_CONCEPTS
from .templates_and_definitions import TAG_EXAM_BOARDS
from .templates_and_definitions import TAG_IMPORTANCE
from .templates_and_definitions import TAG_ROOT
from .templates_and_definitions import TAG_TOPICS
from .templates_and_definitions import TAG_YEARS
from .templates_and_definitions import ensure_custom_models
from .utils import CollectionSaveError
from .utils import add_debug_message
from .utils import ensure_subdeck_exists
from .utils import get_subdeck_name


def add_debug_msg(message, category="DATA_PROCESSOR"):
    """Local helper for debug messages."""
    add_debug_message(message, category)


# Accepted truthy values for the SYNC column (compared against the value
# already normalized to lower-case/stripped at each use site). Single-sourced
# so every sync-marking check below uses the same set.
_SYNC_TRUE_VALUES = frozenset({"true", "1", "yes", "sim"})


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
# CUSTOM EXCEPTIONS
# =============================================================================


class RemoteDeckError(Exception):
    """Custom exception for errors related to remote decks."""

    pass


# =============================================================================
# DATA CLASSES
# =============================================================================


class RemoteDeck:
    """
    Class representing a deck loaded from a remote source.

    This class encapsulates all data from a remote deck, including:
    - List of notes with their respective fields
    - Remote deck name
    - Settings and metadata
    """

    def __init__(self, name="", url=""):
        """
        Initializes an empty remote deck.

        Args:
            name (str): Deck name
            url (str): Data source URL
        """
        self.name = name
        self.url = url
        self.notes = []  # List of dictionaries representing notes
        self.headers = []  # List of spreadsheet headers

        # Refactored metrics per specification
        self.total_table_lines = 0  # 1. Total table lines
        self.valid_note_lines = 0  # 2. Lines with filled ID
        self.invalid_note_lines = 0  # 3. Lines with empty ID
        self.sync_marked_lines = 0  # 4. Lines marked for sync
        self.total_potential_anki_notes = 0  # 5. Total potential Anki notes
        self.ignored_ghost_rows = 0  # 6. Ghost Rows (ignored)

        self.duplicate_ids = []  # Non-empty IDs that appear on more than one row

    def add_note(self, note_data):
        """
        Adds a note to the deck and updates metrics.

        Args:
            note_data (dict): Note data
        """
        if not note_data:
            return

        # Check for completely empty rows (ghost rows from Google Sheets)
        # If all fields are empty (or only contain default Sync values like "FALSE"), we ignore this row
        # This prevents "Invalid Rows" noise from checkbox columns extended down
        has_id = bool(note_data.get(cols.identifier, "").strip())

        if not has_id:
            # Check if there is any content in columns OTHER than SYNC
            # We ignore SYNC because checkboxes often default to FALSE in empty rows
            other_content = False
            for key, value in note_data.items():
                if key != cols.is_sync and value and value.strip():
                    other_content = True
                    break

            # If no ID and no other content, it's a ghost row -> Ignore
            if not other_content:
                self.ignored_ghost_rows += 1
                self.total_table_lines += 1  # Ghost rows are still lines in the table
                return

        self.notes.append(note_data)

        # 1. Total table lines (always increments)
        self.total_table_lines += 1

        # 2 and 3. Valid vs invalid lines (based on ID)
        note_id = note_data.get(cols.identifier, "").strip()
        if note_id:
            self.valid_note_lines += 1
        else:
            self.invalid_note_lines += 1
            # Invalid lines are counted but not processed further.
            return

        # 4. Lines marked for sync (only for valid lines)
        sync_value = str(note_data.get(cols.is_sync, "")).strip().lower()
        if sync_value in _SYNC_TRUE_VALUES:
            self.sync_marked_lines += 1

        # 5. Total potential Anki notes: one per row, plus one more when the row
        # also carries REVERSE content (which produces a second, reversed note).
        has_reverse = bool(note_data.get(cols.reverse, "").strip())
        self.total_potential_anki_notes += 2 if has_reverse else 1

    def finalize_metrics(self):
        """
        Finalizes metric calculation after all notes have been added.
        Should be called at the end of deck processing.
        """
        # Validate automatically
        try:
            self.validate_metrics()
        except ValueError as e:
            # Warning log but not a failure
            add_debug_msg(
                f"⚠️ Warning: Inconsistency detected in remote deck metrics: {e}",
                category="METRICS",
            )

    def get_statistics(self):
        """
        Returns remote deck statistics - REFACTORED.

        Returns:
            dict: Deck statistics according to new specification
        """
        return {
            # Basic table metrics
            "total_table_lines": self.total_table_lines,  # 1. Total lines
            "valid_note_lines": self.valid_note_lines,  # 2. Lines with filled ID
            "invalid_note_lines": self.invalid_note_lines,  # 3. Lines with empty ID
            "ignored_ghost_rows": self.ignored_ghost_rows,  # 6. Ghost Rows
            "sync_marked_lines": self.sync_marked_lines,  # 4. Lines marked for sync
            # Anki potential metrics
            "total_potential_anki_notes": self.total_potential_anki_notes,  # 5. Total potential in Anki
            # Additional info
            "headers": self.headers,
        }

    def validate_metrics(self):
        """
        Validates the consistency of calculated metrics.

        Raises:
            ValueError: If there are inconsistencies in the metrics
        """
        # 1. Validate that valid lines + invalid lines + ghost rows = total
        total_calculated = (
            self.valid_note_lines + self.invalid_note_lines + self.ignored_ghost_rows
        )
        if total_calculated != self.total_table_lines:
            raise ValueError(
                f"Inconsistency: valid({self.valid_note_lines}) + invalid({self.invalid_note_lines}) + ghost({self.ignored_ghost_rows}) != total({self.total_table_lines})"
            )

        # 2. Validate that sync_marked_lines does not exceed valid_note_lines
        if self.sync_marked_lines > self.valid_note_lines:
            raise ValueError(
                f"Inconsistency: lines marked for sync({self.sync_marked_lines}) > valid lines({self.valid_note_lines})"
            )

        # 3. Each valid line yields one note, or two when it has REVERSE content, so the
        # potential total must sit between one and two notes per valid line.
        if not (
            self.valid_note_lines
            <= self.total_potential_anki_notes
            <= 2 * self.valid_note_lines
        ):
            raise ValueError(
                f"Inconsistency: total_potential({self.total_potential_anki_notes}) outside "
                f"[{self.valid_note_lines}, {2 * self.valid_note_lines}] for valid lines({self.valid_note_lines})"
            )


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

        # 1. Download TSV data
        tsv_data = download_tsv_data(url)
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
        # Convert edition URL to TSV format (if necessary)
        try:
            # If URL is already in TSV format, use directly
            if "/export?format=tsv" in url:
                tsv_url = url
            else:
                tsv_url = convert_edit_url_to_tsv(url)
        except ValueError as e:
            raise RemoteDeckError(f"Invalid URL: {str(e)}")

        # Defense-in-depth (SSRF): only ever fetch from Google hosts. The deck URL is
        # user-supplied at add time, and the "/export?format=tsv" pass-through above does
        # not go through convert_edit_url_to_tsv's host check — so a stored URL like
        # "http://169.254.169.254/...export?format=tsv" would otherwise be fetched verbatim.
        from urllib.parse import urlparse

        host = (urlparse(tsv_url).hostname or "").lower()
        if not (
            host == "google.com"
            or host.endswith(".google.com")
            or host.endswith(".googleusercontent.com")
        ):
            raise RemoteDeckError(
                f"Refusing to download from non-Google host '{host}'. "
                f"The deck URL must be a Google Sheets link."
            )

        headers = {"User-Agent": "Mozilla/5.0 (Sheets2Anki) AnkiAddon"}
        request = urllib.request.Request(tsv_url, headers=headers)

        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.getcode() != 200:
                raise RemoteDeckError(
                    f"HTTP {response.getcode()}: Failed to access URL"
                )

            # Read and decode data. Use utf-8-sig so a UTF-8 BOM that some Google
            # export paths prepend is stripped instead of corrupting the first header
            # (e.g. "﻿ID"), which would fail the required-header check.
            data = response.read().decode("utf-8-sig")
            return data

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
    except Exception as e:
        raise RemoteDeckError(f"Unexpected download error: {str(e)}")


def parse_tsv_data(tsv_data, debug_messages=None):
    """
    Parses TSV data and returns processed structure.

    Args:
        tsv_data (str): TSV data as string
        debug_messages (list, optional): Debug list

    Returns:
        dict: Processed data with headers and rows

    Raises:
        RemoteDeckError: If there's an error in parsing
    """

    def add_debug_msg(message, category="TSV_PARSE"):
        from datetime import datetime

        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] [{category}] {message}"
        if debug_messages is not None:
            debug_messages.append(formatted_msg)

    try:
        # Parse with csv.reader over the raw text stream (NOT a pre-split list of lines)
        # so that quoted cells containing embedded newlines — common for multi-line
        # answers/explanations from Google Sheets — are preserved instead of being
        # silently flattened. Outer .strip() only trims the whole document's edges; it
        # does not touch newlines inside quoted cells.
        if not tsv_data.strip():
            raise RemoteDeckError("Empty TSV data")

        reader = csv.reader(io.StringIO(tsv_data.strip()), delimiter="\t")
        rows = list(reader)

        if not rows:
            raise RemoteDeckError("No rows found in TSV data")

        # First row is headers
        headers = rows[0]
        data_rows = rows[1:]

        add_debug_msg(f"Headers found: {len(headers)}")
        add_debug_msg(f"Data rows: {len(data_rows)}")

        # Validate mandatory headers (only ID and ANSWER are enforced)
        required_headers = [cols.identifier, cols.answer]
        missing_headers = [h for h in required_headers if h not in headers]

        if missing_headers:
            raise RemoteDeckError(f"Mandatory headers missing: {missing_headers}")

        return {"headers": headers, "rows": data_rows}

    except csv.Error as e:
        raise RemoteDeckError(f"Error processing TSV data: {e}")
    except Exception as e:
        raise RemoteDeckError(f"Unexpected parsing error: {e}")


def build_remote_deck_from_tsv(parsed_data, url, debug_messages=None):
    """
    Builds RemoteDeck object from processed TSV data.

    Args:
        parsed_data (dict): Processed TSV data
        url (str): Source URL
        debug_messages (list, optional): Debug list

    Returns:
        RemoteDeck: Built remote deck object
    """

    def add_debug_msg(message, category="DECK_BUILD"):
        from datetime import datetime

        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] [{category}] {message}"
        if debug_messages is not None:
            debug_messages.append(formatted_msg)

    headers = parsed_data["headers"]
    rows = parsed_data["rows"]

    # Create remote deck
    remote_deck = RemoteDeck(url=url)
    remote_deck.headers = headers

    # Process each row
    for row_index, row in enumerate(rows):
        try:
            # Create note dictionary
            note_data = {}

            # Fill fields based on headers
            for col_index, header in enumerate(headers):
                if col_index < len(row):
                    note_data[header] = row[col_index].strip()
                else:
                    note_data[header] = ""

            # ALWAYS add to deck for correct metrics accounting
            # Empty ID validation will be done inside add_note() method
            remote_deck.add_note(note_data)

            # Validate if it's a processable note (only ID is mandatory)
            if not note_data.get(cols.identifier):
                add_debug_msg(f"Row {row_index + 2}: invalid note (empty ID)")
                continue

            # Check if it should sync
            sync_value = str(note_data.get(cols.is_sync, "")).strip().lower()
            if sync_value not in _SYNC_TRUE_VALUES:
                add_debug_msg(f"Row {row_index + 2}: note not marked for sync")
                continue

            # Additional processing of fields for valid notes
            process_note_fields(note_data)

        except Exception as e:
            add_debug_msg(f"Error processing row {row_index + 2}: {e}")
            continue

    # Detect duplicate (non-empty) IDs. These silently collapse during sync because
    # notes are keyed by their ID — only one survives and the others are
    # stranded/un-updated. Record them so the user can be warned.
    seen_ids = {}
    for note_data in remote_deck.notes:
        nid = note_data.get(cols.identifier, "").strip()
        if nid:
            seen_ids[nid] = seen_ids.get(nid, 0) + 1
    remote_deck.duplicate_ids = sorted(
        nid for nid, count in seen_ids.items() if count > 1
    )
    if remote_deck.duplicate_ids:
        shown = ", ".join(remote_deck.duplicate_ids[:20])
        suffix = " ..." if len(remote_deck.duplicate_ids) > 20 else ""
        add_debug_msg(
            f"⚠️ Duplicate IDs detected ({len(remote_deck.duplicate_ids)}): {shown}{suffix}"
        )

    # Finalize calculation of metrics
    remote_deck.finalize_metrics()

    # Validate consistency of calculated metrics
    try:
        remote_deck.validate_metrics()
        add_debug_msg("✅ Metrics validated - all consistent")
    except ValueError as e:
        add_debug_msg(f"⚠️ Metrics inconsistency: {e}")

    stats = remote_deck.get_statistics()
    add_debug_msg(
        f"Final deck: {stats['sync_marked_lines']} lines marked for sync, {stats['total_potential_anki_notes']} potential Anki notes"
    )

    return remote_deck


def process_note_fields(note_data):
    """
    Processes special note fields.

    Args:
        note_data (dict): Note data to process
    """
    # IMPORTANT: DO NOT add DEFAULT values directly to note data
    # DEFAULT values are used only for internal logic (ex: subdeck creation)
    # but should not appear on real Anki notes

    # Create hierarchical tags (uses original values or DEFAULT only for internal logic)
    tags = create_tags_from_fields(note_data)
    note_data["tags"] = tags


def create_tags_from_fields(note_data):
    """
    Creates hierarchical tag system from note fields.

    Structure of created tags (all nested under 'Sheets2Anki'):
    1. topics::topic::subtopic::concept: Full nested hierarchy
    2. concepts: Direct concept tags (for easy search)
    3. examination_boards: Tags for each examination board
    4. years: Tags for each test year
    5. careers: Tags for each career
    6. importance: Importance level tag
    7. additionals: Extra tags from the ADDITIONAL TAGS field

    Args:
        note_data (dict): Note data

    Returns:
        list: List of hierarchical tags
    """
    tags = []

    # Root tag
    tags.append(TAG_ROOT)

    def clean_tag_text(text):
        """Cleans text for use as Anki tag - always returns lowercase"""
        if not text or not isinstance(text, str):
            return ""
        # Remove extra spaces, replace spaces with underscores and problematic characters
        cleaned = text.strip().replace(" ", "_").replace(":", "_").replace(";", "_")
        # Remove special characters that may cause issues in Anki, but allow brackets
        cleaned = re.sub(r"[^\w\-_\[\]]", "", cleaned)
        # Always return lowercase for consistency (Anki tags are case-insensitive)
        return cleaned.lower()

    # 1. TOPIC::SUBTOPIC::CONCEPT hierarchical tags (single values, NOT lists)
    topico = note_data.get(cols.hierarchy_2, "").strip()
    subtopico = note_data.get(cols.hierarchy_3, "").strip()
    conceito = note_data.get(cols.hierarchy_4, "").strip()

    # Use default values if empty
    if not topico:
        topico = DEFAULT_TOPIC
    if not subtopico:
        subtopico = DEFAULT_SUBTOPIC
    if not conceito:
        conceito = DEFAULT_CONCEPT

    # Clean for tag use (single values, not lists)
    topico_clean = clean_tag_text(topico)
    subtopico_clean = clean_tag_text(subtopico)
    conceito_clean = clean_tag_text(conceito)

    # If cleaning results in empty string (e.g., field had only invalid characters),
    # use the default placeholder to ensure tags are always generated
    if not topico_clean:
        topico_clean = clean_tag_text(DEFAULT_TOPIC)
    if not subtopico_clean:
        subtopico_clean = clean_tag_text(DEFAULT_SUBTOPIC)
    if not conceito_clean:
        conceito_clean = clean_tag_text(DEFAULT_CONCEPT)

    # Generate hierarchical tag - format: Sheets2Anki::Topics::topic::subtopic::concept
    tags.append(
        f"{TAG_ROOT}::{TAG_TOPICS}::{topico_clean}::{subtopico_clean}::{conceito_clean}"
    )

    # 3. Direct CONCEPT tag (for easy search)
    tags.append(f"{TAG_ROOT}::{TAG_CONCEPTS}::{conceito_clean}")

    # 4. EXAMINATION BOARD tags (supports comma-separated list)
    bancas = note_data.get(cols.tags_1, "").strip()
    if bancas:
        for banca in bancas.split(","):
            banca_clean = clean_tag_text(banca)
            if banca_clean:
                tags.append(f"{TAG_ROOT}::{TAG_EXAM_BOARDS}::{banca_clean}")

    # 5. YEAR tag (single value, NOT list - represents LAST year in exam)
    ano = note_data.get(cols.tags_2, "").strip()
    if ano:
        ano_clean = clean_tag_text(ano)
        if ano_clean:
            tags.append(f"{TAG_ROOT}::{TAG_YEARS}::{ano_clean}")

    # 6. CAREER tags (supports comma-separated list)
    carreira = note_data.get(cols.tags_3, "").strip()
    if carreira:
        for carr in carreira.split(","):
            carr_clean = clean_tag_text(carr)
            if carr_clean:
                tags.append(f"{TAG_ROOT}::{TAG_CAREERS}::{carr_clean}")

    # 7. IMPORTANCE tags (single value, NOT list)
    importancia = note_data.get(cols.hierarchy_1, "").strip()

    if not importancia:
        importancia = DEFAULT_IMPORTANCE

    importancia_clean = clean_tag_text(importancia)

    # If cleaning results in empty string (e.g., field had only invalid characters),
    # use the default placeholder to ensure importance tag is always generated
    if not importancia_clean:
        importancia_clean = clean_tag_text(DEFAULT_IMPORTANCE)

    tags.append(f"{TAG_ROOT}::{TAG_IMPORTANCE}::{importancia_clean}")

    # 8. ADDITIONAL tags (supports comma and semicolon separated list)
    tags_adicionais = note_data.get(cols.tags_4, "").strip()
    if tags_adicionais:
        # Supports both comma and semicolon separation
        separadores = [",", ";"]
        for sep in separadores:
            if sep in tags_adicionais:
                tags_list = tags_adicionais.split(sep)
                break
        else:
            tags_list = [tags_adicionais]

        for tag in tags_list:
            tag_clean = clean_tag_text(tag)
            if tag_clean:
                tags.append(f"{TAG_ROOT}::{TAG_ADDITIONAL}::{tag_clean}")

    return tags


def has_cloze_deletion(text):
    """
    Checks if a text contains Anki cloze formatting in a robust way.
    Checks for {{c1::...}} or {{C1::...}} formats.

    Args:
        text (str): Text to check

    Returns:
        bool: True if it contains cloze, False otherwise
    """
    if not text or not isinstance(text, str):
        return False

    # Pattern to detect cloze: {{c1::text}} or {{c1::text::hint}}
    # Added re.IGNORECASE to catch {{C1::...}} which Anki also supports
    cloze_pattern = r"\{\{c\d+::[^}]+\}\}"
    return bool(re.search(cloze_pattern, text, re.IGNORECASE))


def clean_cloze_formatting(text):
    """
    Removes Anki cloze formatting from text, leaving only the inner content.
    Example: "{{c1::Hello}}" -> "Hello", "{{c2::World::hint}}" -> "World"

    Args:
        text (str): Text to clean

    Returns:
        str: Cleaned text
    """
    if not text or not isinstance(text, str):
        return text

    # Regex to find {{cX::content}} or {{cX::content::hint}}
    # ([^}]+?) lazily captures the content so colons inside the answer are
    # preserved (e.g. "{{c1::10:30}}" -> "10:30"); (?:::[^}]*)? strips an
    # optional ::hint. IGNORECASE matches {{C1::...}} like has_cloze_deletion.
    pattern = r"\{\{c\d+::([^}]+?)(?:::[^}]*)?\}\}"

    # Replace all occurrences with the first capturing group (the content)
    return re.sub(pattern, r"\1", text, flags=re.IGNORECASE)


# =============================================================================
# NOTE PROCESSING FUNCTIONS
# =============================================================================


def create_or_update_notes(
    col, remoteDeck, deck_id, deck_url=None, debug_messages=None
):
    """
    Creates or updates notes in the deck based on remote data.

    Each remote spreadsheet row with a unique ID produces one Anki note, keyed by that
    ID. A row that also carries REVERSE content produces a second note keyed
    "{id}_REV". Those keys are written into the note's ID field and must never be
    modified after creation — they are how a note is matched back to its row.

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

    # Surface duplicate spreadsheet IDs (detected during deck build) so the user can fix
    # them — duplicates silently strand notes that share the same key.
    if getattr(remoteDeck, "duplicate_ids", None):
        shown = ", ".join(remoteDeck.duplicate_ids[:10])
        suffix = " ..." if len(remoteDeck.duplicate_ids) > 10 else ""
        stats.add_error(
            f"Duplicate IDs in the spreadsheet ({len(remoteDeck.duplicate_ids)}): {shown}{suffix}. "
            f"Each '{cols.identifier}' must be unique — duplicate rows are not all synced."
        )

    try:
        # 1. Build the set of note keys the spreadsheet expects to exist.
        expected_note_ids = set()
        for note_data in remoteDeck.notes:
            note_id = note_data.get(cols.identifier, "").strip()
            if not note_id:
                continue

            sync_value = str(note_data.get(cols.is_sync, "")).strip().lower()
            if sync_value not in _SYNC_TRUE_VALUES:
                continue

            expected_note_ids.add(note_id)
            if note_data.get(cols.reverse, "").strip():
                expected_note_ids.add(f"{note_id}_REV")

        add_debug_msg("=== REMOTE DECK METRICS ===")
        add_debug_msg(f"📊 Total table lines: {stats.remote_total_table_lines}")
        add_debug_msg(f"✅ Valid lines (filled ID): {stats.remote_valid_note_lines}")
        add_debug_msg(f"❌ Invalid lines (empty ID): {stats.remote_invalid_note_lines}")
        add_debug_msg(f"🔄 Lines marked for sync: {stats.remote_sync_marked_lines}")
        add_debug_msg(
            f"🚀 Total potential notes in Anki: {stats.remote_total_potential_anki_notes}"
        )
        add_debug_msg(f"🎯 Note keys for synchronization: {len(expected_note_ids)}")

        # 2. Ensure the deck's note types exist (this provisions basic, cloze and
        # reverse models in one call).
        ensure_custom_models(col, deck_url, debug_messages=debug_messages)

        # 3. Get existing notes by note key
        existing_notes = get_existing_notes_by_id(col, deck_id)
        add_debug_msg(f"Found {len(existing_notes)} existing notes in deck")

        def process_variant(note_data, note_id, key, is_reverse=False):
            """Creates or updates a single note variant and records it in stats."""
            try:
                if key in existing_notes:
                    success, was_updated, changes = update_existing_note(
                        col,
                        existing_notes[key],
                        note_data,
                        deck_url,
                        debug_messages,
                        is_reverse=is_reverse,
                    )
                    if not success:
                        stats.add_error(f"Error updating note: {key}")
                        add_debug_msg(f"❌ Error updating note: {key}")
                        return

                    if was_updated:
                        stats.updated += 1
                        stats.update_details.append(
                            {
                                "note_key": key,
                                "note_id": note_id,
                                "changes": changes,
                            }
                        )
                        add_debug_msg(f"✅ Note updated: {key}")
                    else:
                        stats.unchanged += 1
                        add_debug_msg(f"⏭️ Note unchanged: {key}")
                    return

                if create_new_note(
                    col,
                    note_data,
                    deck_id,
                    deck_url,
                    debug_messages,
                    is_reverse=is_reverse,
                ):
                    stats.created += 1
                    preview_source = cols.reverse if is_reverse else cols.question
                    preview = note_data.get(preview_source, "")
                    stats.creation_details.append(
                        {
                            "note_key": key,
                            "note_id": note_id,
                            "pergunta": preview[:100]
                            + ("..." if len(preview) > 100 else ""),
                        }
                    )
                    add_debug_msg(f"✅ Note created: {key}")
                else:
                    stats.add_error(f"Error creating note: {key}")
                    add_debug_msg(f"❌ Error creating note: {key}")

            except Exception as e:
                import traceback

                error_details = traceback.format_exc()
                add_debug_msg(f"❌ Error processing {key}: {e}")
                add_debug_msg(f"❌ Stack trace: {error_details}")
                stats.add_error(f"Exception processing {key}: {str(e)}")

        # 4. Process each remote note
        for note_data in remoteDeck.notes:
            note_id = note_data.get(cols.identifier, "").strip()
            if not note_id:
                # Empty ID line is not an error, it's a normal situation already accounted for in metrics
                continue

            # Check if it should sync
            sync_value = str(note_data.get(cols.is_sync, "")).strip().lower()
            if sync_value not in _SYNC_TRUE_VALUES:
                stats.skipped += 1
                continue

            process_variant(note_data, note_id, note_id)

            # Process REVERSE note if applicable
            reverse_content = note_data.get(cols.reverse, "").strip()
            if reverse_content:
                # WARNING for reverse-only notes
                if not note_data.get(cols.question, "").strip():
                    warning_msg = (
                        f"⚠️ Note {note_id}: Reverse note created but has no answer "
                        f"(QUESTION field is empty)."
                    )
                    stats.warnings.append(warning_msg)
                    add_debug_msg(warning_msg)

                add_debug_msg(
                    f"🔍 Found REVERSE content for {note_id}: '{reverse_content[:50]}'"
                )
                process_variant(note_data, note_id, f"{note_id}_REV", is_reverse=True)

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
                f"empty '{cols.identifier}'). Skipped deletion of {len(all_existing_note_ids)} "
                f"existing note(s) to prevent accidental data loss. Verify the sheet/tab is "
                f"correct and not empty, then sync again."
            )
            add_debug_msg(f"🛡️ {warning}")
            stats.add_error(warning)
            try:
                col.save()
                add_debug_msg("Collection saved successfully (no changes applied)")
            except Exception as e:
                raise CollectionSaveError(f"Failed to save collection: {e}")
            return stats

        # 5.1. Identify obsolete notes (no longer in spreadsheet) vs sync-disabled ones.
        # Lookup of remote spreadsheet IDs -> sync-enabled flag, keyed by the raw
        # ID-column value.
        remote_id_sync = {}
        for note_data in remoteDeck.notes:
            rid = note_data.get(cols.identifier, "").strip()
            if not rid:
                continue
            sv = str(note_data.get(cols.is_sync, "")).strip().lower()
            remote_id_sync[rid] = sv in _SYNC_TRUE_VALUES

        def _base_id(key):
            """Maps a stored note key back to its spreadsheet ID, or None if unknown.

            A whole key is preferred over stripping the "_REV" suffix, so a spreadsheet
            ID that itself ends in "_REV" still resolves to its own row.
            """
            if key in remote_id_sync:
                return key
            if key.endswith("_REV") and key[:-4] in remote_id_sync:
                return key[:-4]
            return None

        notes_really_obsolete = set()
        notes_with_sync_disabled = set()

        for note_key in all_existing_note_ids - expected_note_ids:
            base_id = _base_id(note_key)

            if base_id is None:
                # Note's ID is no longer present anywhere in the spreadsheet.
                notes_really_obsolete.add(note_key)
                add_debug_msg(
                    f"📝 Obsolete note (removed from spreadsheet): {note_key}"
                )
            elif not remote_id_sync[base_id]:
                # Row exists but SYNC=false - ALWAYS preserve (user intentionally disabled sync)
                notes_with_sync_disabled.add(note_key)
                add_debug_msg(f"⏸️ Note with SYNC disabled (preserving): {note_key}")
            else:
                # Row is synced but no longer produces this variant (e.g. its REVERSE
                # content was cleared), so the leftover note is obsolete.
                notes_really_obsolete.add(note_key)
                add_debug_msg(
                    f"📝 Obsolete note variant (no longer produced): {note_key}"
                )

        # 5.2. Remove obsolete notes
        add_debug_msg(f"🗑️ Removing {len(notes_really_obsolete)} obsolete notes")
        for note_key in notes_really_obsolete:
            try:
                note_to_delete = existing_notes[note_key]
                if delete_note_by_id(col, note_to_delete):
                    stats.deleted += 1
                    # Extract question text for better logging
                    pergunta = ""
                    try:
                        if cols.question in note_to_delete.keys():
                            full_pergunta = note_to_delete[cols.question]
                            pergunta = full_pergunta[:100] + (
                                "..." if len(full_pergunta) > 100 else ""
                            )
                    except Exception:
                        pass
                    # Capture deletion details
                    stats.deletion_details.append(
                        {
                            "note_key": note_key,
                            "note_id": _base_id(note_key) or note_key,
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

        # 7. Save changes
        try:
            col.save()
            add_debug_msg("Collection saved successfully")
        except Exception as e:
            raise CollectionSaveError(f"Failed to save collection: {e}")

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
      spreadsheet ID (or "{id}_REV" for a reverse note)
    - Returns mapping {note_key: note_object}

    Args:
        col: Anki collection
        deck_id (int): Deck ID

    Returns:
        dict: Mapping {note_key: note_object}
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
                note_fields = note.keys()
                if cols.identifier in note_fields:
                    note_key = note[cols.identifier].strip()
                    if note_key:
                        existing_notes[note_key] = note

            except Exception as e:
                add_debug_msg(
                    f"Error processing card {card_id}: {e}", category="DECK_SEARCH"
                )
                continue

    except Exception as e:
        add_debug_msg(f"Error obtaining existing notes: {e}", category="DECK_SEARCH")

    return existing_notes


def create_new_note(
    col, note_data, deck_id, deck_url, debug_messages=None, is_reverse=False
):
    """
    Creates a new Anki note from a spreadsheet row.

    Args:
        col: Anki collection
        note_data (dict): Spreadsheet note data
        deck_id (int): Base deck ID
        deck_url (str): Remote deck URL
        debug_messages (list, optional): Debug list
        is_reverse (bool): Whether to create the reversed variant of the row

    Returns:
        bool: True if created successfully, False otherwise
    """

    def add_debug_msg(message, category="CREATE_NOTE"):
        """Helper to add debug messages using global system."""
        from .utils import add_debug_message

        add_debug_message(message, category)

    try:
        note_id = note_data.get(cols.identifier, "").strip()
        add_debug_msg(f"Creating new note: {note_id}")

        # Determine note type (cloze or basic)
        pergunta = note_data.get(cols.question, "")
        resposta = note_data.get(cols.answer, "")
        is_cloze = has_cloze_deletion(pergunta) or has_cloze_deletion(resposta)

        # Get appropriate model
        from .config_manager import get_deck_remote_name
        from .utils import get_note_type_name

        remote_deck_name = get_deck_remote_name(deck_url)
        note_type_name = get_note_type_name(
            deck_url,
            remote_deck_name,
            is_cloze=is_cloze,
            is_reverse=is_reverse,
        )

        add_debug_msg(f"Note type: {note_type_name}")

        model = col.models.by_name(note_type_name)
        if not model:
            add_debug_msg(f"❌ ERROR: Model not found: '{note_type_name}'")
            add_debug_msg(f"❌ Attempting to create note type for note: {note_id}")
            # Attempt to create model if it doesn't exist
            from .templates_and_definitions import ensure_custom_models

            models = ensure_custom_models(col, deck_url, debug_messages=debug_messages)
            model = models.get(
                "reverse" if is_reverse else ("cloze" if is_cloze else "standard")
            )
            if not model:
                add_debug_msg(
                    f"❌ CRITICAL ERROR: Could not create/find model: {note_type_name}"
                )
                return False
            add_debug_msg(f"✅ Model created successfully: {note_type_name}")

        add_debug_msg(
            f"✅ Model found: {note_type_name} (ID: {model['id'] if model else 'None'})"
        )

        # Create note
        note = col.new_note(model)

        # Fill fields (the ID field receives the note's unique key)
        fill_note_fields(note, note_data, is_reverse=is_reverse)

        # Add tags
        tags = note_data.get("tags", [])
        if tags:
            note.tags = tags

        # Determine target subdeck
        add_debug_msg(f"Determining target deck for note: {note_id}")
        target_deck_id = determine_target_deck(
            col, deck_id, note_data, deck_url, debug_messages
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
            f"❌ ERROR creating note {note_data.get(cols.identifier, 'UNKNOWN')}: {e}"
        )
        add_debug_msg(f"❌ Stack trace: {error_details}")
        return False


def note_fields_need_update(existing_note, new_data, debug_messages=None):
    """
    Checks if a note needs update by comparing fields and tags.

    The ID field is not compared: it holds the note's derived key and must stay
    unchanged. Every other field is compared against the spreadsheet data.

    Args:
        existing_note: Existing Anki note
        new_data (dict): New note data
        debug_messages (list, optional): Debug list

    Returns:
        tuple: (needs_update: bool, changes: list)
    """

    def add_debug_msg(message, category="NOTE_COMPARISON"):
        """Helper to add debug messages using global system."""
        from .utils import add_debug_message

        add_debug_message(message, category)

    changes = []

    # Compare fields (excluding the derived ID)
    # Use real field names in Anki (which are the same as spreadsheet)
    for field_key, field_anki_name in [
        (cols.question, cols.question),
        (cols.answer, cols.answer),
        (cols.reverse, cols.reverse),
        (cols.info_1, cols.info_1),
        (cols.info_2, cols.info_2),
        (cols.multimedia_1, cols.multimedia_1),
        (cols.multimedia_2, cols.multimedia_2),
        (cols.example_1, cols.example_1),
        (cols.example_2, cols.example_2),
        (cols.mnemonic, cols.mnemonic),
        (cols.hierarchy_1, cols.hierarchy_1),
        (cols.hierarchy_2, cols.hierarchy_2),
        (cols.hierarchy_3, cols.hierarchy_3),
        (cols.hierarchy_4, cols.hierarchy_4),
        (cols.tags_1, cols.tags_1),
        (cols.tags_2, cols.tags_2),
        (cols.tags_3, cols.tags_3),
        (cols.tags_4, cols.tags_4),
        (cols.extra_field_1, cols.extra_field_1),
        (cols.extra_field_2, cols.extra_field_2),
        (cols.extra_field_3, cols.extra_field_3),
        (cols.sanity_check, cols.sanity_check),
    ]:
        if field_anki_name in existing_note:
            old_value = str(existing_note[field_anki_name]).strip()
            new_value = str(new_data.get(field_key, "")).strip()

            if old_value != new_value:
                # Truncate for log if too long
                old_display = (
                    old_value[:50] + "..." if len(old_value) > 50 else old_value
                )
                new_display = (
                    new_value[:50] + "..." if len(new_value) > 50 else new_value
                )
                changes.append(f"{field_anki_name}: '{old_display}' → '{new_display}'")

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
    col,
    existing_note,
    new_data,
    deck_url,
    debug_messages=None,
    is_reverse=False,
):
    """
    Updates an existing note.
    IMPORTANT: Only updates if there are real differences between local and remote content.

    Args:
        col: Anki collection
        existing_note: Existing Anki note
        new_data (dict): New note data
        deck_url (str): Deck URL
        debug_messages (list, optional): Debug list
        is_reverse (bool): Whether this is the reversed variant of the row

    Returns:
        tuple: (success: bool, was_updated: bool, changes: list)
    """

    def add_debug_msg(message, category="UPDATE_NOTE"):
        """Helper to add debug messages using global system."""
        from .utils import add_debug_message

        add_debug_message(message, category)

    try:
        note_id = new_data.get(cols.identifier, "").strip()
        add_debug_msg(f"Checking if note {note_id} needs update")

        # Determine expected note type
        pergunta = new_data.get(cols.question, "")
        resposta = new_data.get(cols.answer, "")

        # Cloze detection: check both fields
        is_cloze = has_cloze_deletion(pergunta) or has_cloze_deletion(resposta)

        # Get appropriate model for the current state
        models = ensure_custom_models(col, deck_url, debug_messages=debug_messages)
        target_model = models.get(
            "reverse" if is_reverse else ("cloze" if is_cloze else "standard")
        )

        # Check for real differences between existing note and new data
        # We MUST do this before type change to capture field differences
        needs_update, changes = note_fields_need_update(
            existing_note, new_data, debug_messages
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
                    current_deck_id,
                    deck_url,
                    debug_messages,
                    is_reverse=is_reverse,
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
        fill_note_fields(existing_note, new_data, is_reverse=is_reverse)

        # Update tags
        tags = new_data.get("tags", [])
        if tags:
            existing_note.tags = tags

        # Check if needs moving to different subdeck
        cards = existing_note.cards()
        if cards:
            current_deck_id = cards[0].did
            target_deck_id = determine_target_deck(
                col, current_deck_id, new_data, deck_url, debug_messages
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


def fill_note_fields(note, note_data, is_reverse=False):
    """
    Fills note fields with spreadsheet data.

    - The Anki note ID field is filled with the spreadsheet ID, or "{id}_REV" for the
      reversed variant
    - This unique identifier should never be modified after creation
    - All other fields are filled normally from spreadsheet data

    Args:
        note: Anki note
        note_data (dict): Spreadsheet data
        is_reverse (bool): Whether this is the reversed variant of the row
    """
    # Get original spreadsheet ID
    original_id = note_data.get(cols.identifier, "").strip()

    # Key for this note variant
    note_key = f"{original_id}_REV" if is_reverse else original_id

    # Field mapping with special treatment for ID
    field_mappings = {
        cols.identifier: note_key,  # Unique key for this note
        cols.question: note_data.get(cols.question, "").strip(),
        cols.answer: note_data.get(cols.answer, "").strip(),
        cols.reverse: note_data.get(cols.reverse, "").strip(),
        cols.hierarchy_1: note_data.get(cols.hierarchy_1, "").strip(),
        cols.hierarchy_2: note_data.get(cols.hierarchy_2, "").strip(),
        cols.hierarchy_3: note_data.get(cols.hierarchy_3, "").strip(),
        cols.hierarchy_4: note_data.get(cols.hierarchy_4, "").strip(),
        cols.info_1: note_data.get(cols.info_1, "").strip(),
        cols.info_2: note_data.get(cols.info_2, "").strip(),
        cols.multimedia_1: note_data.get(cols.multimedia_1, "").strip(),
        cols.multimedia_2: note_data.get(cols.multimedia_2, "").strip(),
        cols.example_1: note_data.get(cols.example_1, "").strip(),
        cols.example_2: note_data.get(cols.example_2, "").strip(),
        cols.mnemonic: note_data.get(cols.mnemonic, "").strip(),
        # Metadata fields
        cols.tags_1: note_data.get(cols.tags_1, "").strip(),
        cols.tags_2: note_data.get(cols.tags_2, "").strip(),
        cols.tags_3: note_data.get(cols.tags_3, "").strip(),
        cols.tags_4: note_data.get(cols.tags_4, "").strip(),
        # Personalizable extra fields
        cols.extra_field_1: note_data.get(cols.extra_field_1, "").strip(),
        cols.extra_field_2: note_data.get(cols.extra_field_2, "").strip(),
        cols.extra_field_3: note_data.get(cols.extra_field_3, "").strip(),
        cols.sanity_check: note_data.get(cols.sanity_check, "").strip(),
    }

    # If it's a reverse note, we MUST clean clozes from the QUESTION field
    # since it will act as the answer and clozes shouldn't be hidden there.
    if is_reverse:
        raw_question = note_data.get(cols.question, "").strip()
        field_mappings[cols.question] = clean_cloze_formatting(raw_question)

    # Fill available note fields
    for field_name in note.keys():
        if field_name in field_mappings:
            note[field_name] = field_mappings[field_name]


def determine_target_deck(col, base_deck_id, note_data, deck_url, debug_messages=None):
    """
    Determines the target subdeck for a note.

    Args:
        col: Anki collection
        base_deck_id (int): Base deck ID
        note_data (dict): Note data
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

        # Create base deck following pattern: Sheets2Anki::{remote_deck_name}
        deck_with_remote_name = f"Sheets2Anki::{remote_deck_name}"
        subdeck_name = get_subdeck_name(deck_with_remote_name, note_data)
        subdeck_id = ensure_subdeck_exists(subdeck_name)

        if subdeck_id:
            add_debug_msg(f"Note directed to subdeck: {subdeck_name}")
            return subdeck_id

        return base_deck_id

    except Exception as e:
        add_debug_msg(f"Error determining target deck: {e}")
        return base_deck_id
