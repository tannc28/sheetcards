"""Turning a downloaded sheet into the shape a note is built from.

This module is deliberately **pure**: nothing here imports Anki, Qt or any other
part of the add-on's runtime, only the standard library and the equally pure
:mod:`column_model` and :mod:`errors`. Together with :mod:`column_model`,
:mod:`sheet_config` and :mod:`card_layout` it forms the layer that answers
"what would this spreadsheet become?" without a collection to put it in.

That purity is a feature, not an accident, and ``tests/test_pure_modules.py``
enforces it: the preview site under ``site/`` runs these very files in the
browser through Pyodide, so a user can see what a sheet will produce before
installing anything. Reaching for ``mw`` here would break that and, worse,
would mean the preview had to be a *second* implementation — one that drifts
from this one the first time either side is fixed alone.
"""

import csv
import io
import re

from . import column_model
from .column_model import clean
from .column_model import deck_path
from .column_model import plan_columns
from .column_model import row_is_marked_for_sync
from .column_model import tags_of
from .errors import RemoteDeckError
from .sheet_config import SheetConfig
from .sheet_config import is_config_row
from .sheet_config import parse_config_row

# Marks every note the add-on owns, so they can be found or bulk-removed from the
# browser without touching notes the user made themselves.
TAG_ROOT = "sheets2anki"

# Every deck the add-on creates hangs under this one, so a collection keeps its own
# decks and the synced ones apart. The real path a row lands in is
# "Sheets2Anki::{sheet name}::{SUBDECK levels}" — see data_processor's
# determine_target_deck, which builds exactly that.
DEFAULT_PARENT_DECK_NAME = "Sheets2Anki"


# =============================================================================
# TSV PARSING
# =============================================================================


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

        # The sheet defines its own fields, so ID is the only header the add-on
        # insists on — it is the key every note is matched by.
        plan = plan_columns(headers)
        if not plan.has_id:
            raise RemoteDeckError(
                f"Mandatory header missing: '{column_model.IDENTIFIER}'"
            )
        if not plan.content_headers:
            raise RemoteDeckError(
                "The sheet has no content columns — add at least one column besides "
                f"'{column_model.IDENTIFIER}', '{column_model.SYNC}', "
                f"'{column_model.TAGS}' and 'SUBDECK n'."
            )
        if plan.duplicates:
            add_debug_msg(f"⚠️ Duplicate headers ignored: {plan.duplicates}")

        return {"headers": headers, "rows": data_rows, "plan": plan}

    except csv.Error as e:
        raise RemoteDeckError(f"Error processing TSV data: {e}")
    except Exception as e:
        raise RemoteDeckError(f"Unexpected parsing error: {e}")


def row_to_dict(row, headers):
    """One TSV row as a dict keyed by the sheet's own (cleaned) headers.

    A header repeated in the sheet keeps its first column, matching ``plan_columns``.
    """
    note_data = {}
    for col_index, header in enumerate(headers):
        cleaned = clean(header)
        if not cleaned or cleaned in note_data:
            continue
        value = row[col_index] if col_index < len(row) else ""
        note_data[cleaned] = value.strip() if isinstance(value, str) else ""
    return note_data


# =============================================================================
# TAGS
# =============================================================================


def clean_tag_text(text):
    """Cleans text for use as an Anki tag — always lower-case.

    Anki treats '::' as tag nesting and spaces as tag separators, so both have to go
    before the value can be used as a single tag component.
    """
    if not text or not isinstance(text, str):
        return ""
    cleaned = text.strip().replace(" ", "_").replace("::", "_").replace(":", "_")
    cleaned = cleaned.replace(";", "_")
    cleaned = re.sub(r"[^\w\-_\[\]]", "", cleaned, flags=re.UNICODE)
    # "Unit 3: intro" would otherwise become "unit_3__intro" — collapse the runs so
    # punctuation next to a space doesn't leave a visible scar in the tag.
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned.lower()


def build_tags(note_data, plan):
    """Builds the tag list for one row.

    Three kinds of tag, and no placeholders for anything the row left blank:

    1. ``sheets2anki`` — marks every note the add-on owns, so they can be found or
       bulk-removed without touching the user's own notes.
    2. ``sheets2anki::<subdeck path>`` — mirrors the deck path, which makes the
       hierarchy searchable from the browser sidebar.
    3. whatever the TAGS column lists, verbatim (comma or semicolon separated).
    """
    tags = [TAG_ROOT]

    path = [clean_tag_text(level) for level in deck_path(note_data, plan)]
    path = [level for level in path if level]
    if path:
        tags.append(f"{TAG_ROOT}::" + "::".join(path))

    for tag in tags_of(note_data, plan):
        cleaned = clean_tag_text(tag)
        if cleaned:
            tags.append(cleaned)

    # Preserve order while dropping repeats.
    return list(dict.fromkeys(tags))


# =============================================================================
# EMBEDDED PLAYERS
# =============================================================================

# A card template can only substitute a field, never transform one: Anki replaces
# `{{Link}}` with the cell exactly as written. So a YouTube *watch* address cannot
# become a player at render time — and it cannot be framed as-is either, because
# YouTube refuses to be put in an iframe outside its /embed path. The address is
# therefore rewritten here, once, on the way into the note, which is also the value
# the sync compares against to decide whether a row changed.

_YOUTUBE_ID = r"[\w-]{6,}"
_EMBED_PATTERNS = (
    # (what the user pastes, what it becomes) — the id is group 1 throughout.
    (re.compile(rf"youtu\.be/({_YOUTUBE_ID})"), "https://www.youtube.com/embed/{}"),
    (
        re.compile(rf"youtube\.com/(?:watch\?(?:.*&)?v=)({_YOUTUBE_ID})"),
        "https://www.youtube.com/embed/{}",
    ),
    (
        re.compile(rf"youtube\.com/(?:shorts|live|v)/({_YOUTUBE_ID})"),
        "https://www.youtube.com/embed/{}",
    ),
    # Already an embed address: left alone, so re-syncing is idempotent.
    (
        re.compile(rf"youtube\.com/embed/({_YOUTUBE_ID})"),
        "https://www.youtube.com/embed/{}",
    ),
    (
        re.compile(r"drive\.google\.com/file/d/([\w-]+)"),
        "https://drive.google.com/file/d/{}/preview",
    ),
    (
        re.compile(r"drive\.google\.com/open\?id=([\w-]+)"),
        "https://drive.google.com/file/d/{}/preview",
    ),
    (re.compile(r"vimeo\.com/(?:video/)?(\d+)"), "https://player.vimeo.com/video/{}"),
)

# "?t=90", "?t=1m30s", "&start=90" — a link copied at a particular moment.
_START_AT = re.compile(r"[?&](?:t|start)=(?:(\d+)h)?(?:(\d+)m)?(\d+)s?(?:&|$)")


def _start_seconds(url):
    """The moment a shared link points at, in seconds, or None."""
    match = _START_AT.search(url)
    if not match:
        return None
    hours, minutes, seconds = (int(g or 0) for g in match.groups())
    total = hours * 3600 + minutes * 60 + seconds
    return total or None


def normalize_embed_url(value):
    """Turns a page address into the address of that site's own player.

    Args:
        value (str): whatever the cell holds — a watch link, a share link, or
            already a player address

    Returns:
        tuple[str, str | None]: the address to put in the field, and a warning
        when the cell looks like a site this understands but no id could be read
        (a channel page, a Drive folder) — those would frame an error message.
    """
    url = str(value or "").strip()
    if not url:
        return "", None

    for pattern, template in _EMBED_PATTERNS:
        found = pattern.search(url)
        if not found:
            continue
        embed = template.format(found.group(1))
        start = _start_seconds(url)
        return (f"{embed}?start={start}" if start else embed), None

    lowered = url.lower()
    for host in ("youtube.com", "youtu.be", "drive.google.com", "vimeo.com"):
        if host in lowered:
            return url, (
                f"'{url}' is a {host} address with no video in it — a channel, a "
                f"playlist or a folder cannot be embedded, only a single video or file"
            )

    # Anything else is passed through: a direct .mp4 shows in an iframe too, and
    # refusing an address this function simply does not know would be worse.
    return url, None


def apply_media_rewrites(note_data, plan, sheet_config):
    """Rewrites a row's video cells in place, and says what looked wrong.

    Anything that renders a row has to go through this, not just the sync: a
    preview that skipped it would frame the address the user pasted, which is
    precisely the address that cannot be framed — so the preview would show a
    blank box for a card that is actually fine.

    Args:
        note_data (dict): one row, keyed by header; modified in place
        plan (ColumnPlan): the sheet's column roles
        sheet_config (SheetConfig): the parsed settings row

    Returns:
        list[str]: warnings about addresses that name no single video
    """
    warnings = []
    for header in plan.content_headers:
        if sheet_config.for_field(header).media != "video":
            continue
        fixed, problem = normalize_embed_url(note_data.get(header, ""))
        note_data[header] = fixed
        if problem:
            warnings.append(f"'{header}': {problem}")
    return warnings


# =============================================================================
# WHAT A ROW BECOMES
# =============================================================================

# A row is exactly one of these. Named rather than inlined because the preview
# site labels every row with the same verdict the sync acts on, and two copies of
# "what counts as an empty row" would disagree the first time either was touched.
GHOST = "ghost"  # blank — never counted, never reported
INVALID = "invalid"  # has content but no ID, so nothing can key the note
SKIPPED = "skipped"  # valid, but the SYNC column says not this one
SYNCED = "synced"  # becomes a note


def classify_row(note_data, plan):
    """Which of the four a row is.

    A row with no ID is only a problem when it carries something else. Checkbox
    columns are routinely dragged far below the last real row, leaving a tail of
    rows whose only value is an unticked SYNC; counting those as broken rows would
    bury the real ones in noise, so they are ghosts.
    """
    note_id = str(note_data.get(plan.id_header, "")).strip() if plan.id_header else ""

    if not note_id:
        other_content = any(
            value and str(value).strip()
            for key, value in note_data.items()
            if key != plan.sync_header
        )
        return INVALID if other_content else GHOST

    return SYNCED if row_is_marked_for_sync(note_data, plan) else SKIPPED


# =============================================================================
# CLOZE DETECTION
# =============================================================================


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


def row_has_cloze(note_data, plan):
    """
    Checks whether any of the row's content columns carries a cloze deletion.

    Every content column is inspected because the sheet decides its own columns —
    a cloze can live in any of them.

    Args:
        note_data (dict): Spreadsheet row keyed by the sheet's headers
        plan (ColumnPlan): How this sheet's headers map onto Anki

    Returns:
        bool: True if the row produces a cloze note
    """
    return any(
        has_cloze_deletion(str(note_data.get(header, "")))
        for header in plan.content_headers
    )


# =============================================================================
# THE DECK A SHEET DESCRIBES
# =============================================================================


def _discard(message, category="TSV_MODEL"):
    """Default sink for the add-on's global debug log.

    The pure layer has no debug console to write to — in the browser there is no
    add-on at all — so messages meant for it go nowhere unless the add-on installs
    a real sink at import time via :func:`set_addon_logger`.
    """


log_to_addon = _discard


def set_addon_logger(sink):
    """Points the global-log messages at the add-on's debug log.

    Called once by ``data_processor`` on import. Kept explicit rather than having
    this module import ``utils`` directly, because that import is exactly what
    would make the file unloadable in the browser.
    """
    global log_to_addon
    log_to_addon = sink or _discard


class RemoteDeck:
    """
    Class representing a deck loaded from a remote source.

    This class encapsulates all data from a remote deck, including:
    - List of notes with their respective fields
    - Remote deck name
    - Settings and metadata
    """

    def __init__(self, name="", url="", plan=None, sheet_config=None):
        """
        Initializes an empty remote deck.

        Args:
            name (str): Deck name
            url (str): Data source URL
            plan (ColumnPlan): how this sheet's headers map onto Anki
            sheet_config (SheetConfig): the sheet's parsed settings row; a
                default-constructed one (``present`` False) when the sheet has none
        """
        self.name = name
        self.url = url
        self.notes = []  # List of dictionaries representing notes
        self.headers = []  # List of spreadsheet headers
        self.plan = plan or plan_columns([])
        self.sheet_config = sheet_config or SheetConfig()

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

        plan = self.plan
        note_id = (
            str(note_data.get(plan.id_header, "")).strip() if plan.id_header else ""
        )

        if classify_row(note_data, plan) == GHOST:
            self.ignored_ghost_rows += 1
            self.total_table_lines += 1  # Ghost rows are still lines in the table
            return

        self.notes.append(note_data)

        # 1. Total table lines (always increments)
        self.total_table_lines += 1

        # 2 and 3. Valid vs invalid lines (based on ID)
        if note_id:
            self.valid_note_lines += 1
        else:
            self.invalid_note_lines += 1
            # Invalid lines are counted but not processed further.
            return

        # 4. Lines marked for sync (only for valid lines)
        if row_is_marked_for_sync(note_data, plan):
            self.sync_marked_lines += 1

        # 5. One Anki note per valid row. The reverse direction, when enabled, is a
        # second card on the same note rather than a second note.
        self.total_potential_anki_notes += 1

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
            log_to_addon(
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

        # 3. Each valid line yields exactly one note; the reverse direction is a
        # second card on that note, not a second note.
        if self.total_potential_anki_notes != self.valid_note_lines:
            raise ValueError(
                f"Inconsistency: potential notes({self.total_potential_anki_notes}) "
                f"!= valid lines({self.valid_note_lines})"
            )


def build_remote_deck_from_tsv(parsed_data, url, debug_messages=None):
    """
    Builds RemoteDeck object from processed TSV data.

    Args:
        parsed_data (dict): Processed TSV data, including the sheet's ColumnPlan
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
    plan = parsed_data.get("plan") or plan_columns(headers)

    # The sheet may describe how its cards look in the row right under the headers.
    # It is a directive row, not data: it is removed here so it never reaches
    # add_note() and therefore never shows up in any metric.
    sheet_config = SheetConfig()
    first_row_offset = 0
    if rows and is_config_row(row_to_dict(rows[0], headers), plan):
        sheet_config = parse_config_row(row_to_dict(rows[0], headers), plan)
        rows = rows[1:]
        first_row_offset = 1  # keeps the row numbers in the log matching the sheet
        add_debug_msg(
            f"Settings row found: {len(sheet_config.fields)} column(s) configured"
        )
        for warning in sheet_config.warnings:
            message = f"⚠️ Settings row: {warning}"
            add_debug_msg(message)
            # Also into the global log: getRemoteDeck is called without a debug list
            # during a normal sync, and a typo nobody sees is a typo nobody fixes.
            log_to_addon(message, "SHEET_CONFIG")

    # Create remote deck
    remote_deck = RemoteDeck(url=url, plan=plan, sheet_config=sheet_config)
    remote_deck.headers = headers

    add_debug_msg(f"Content columns: {plan.content_headers}")
    add_debug_msg(f"Deck path columns: {plan.subdeck_headers}")

    embed_warnings = set()
    cloze_rows = []

    # Process each row
    for row_index, row in enumerate(rows):
        sheet_row = row_index + 2 + first_row_offset
        try:
            # Create note dictionary keyed by the sheet's own headers
            note_data = row_to_dict(row, headers)

            # Rewritten here rather than at render time because a card template can
            # substitute a field but cannot transform one. Doing it before add_note
            # means the sync's change comparison sees the same value it stores, so a
            # row does not read as modified on every single sync.
            for problem in apply_media_rewrites(note_data, plan, sheet_config):
                embed_warnings.add(f"row {sheet_row}: {problem}")

            # A sheet says once which column carries its deletions. A row that has
            # cloze markup anywhere else would print `{{c1::…}}` on the card as
            # literal text, so it is reported rather than left to be discovered
            # during a review.
            if not sheet_config.cloze_field and row_has_cloze(note_data, plan):
                cloze_rows.append(sheet_row)

            # ALWAYS add to deck for correct metrics accounting
            # Empty ID validation will be done inside add_note() method
            remote_deck.add_note(note_data)

            note_id = str(note_data.get(plan.id_header, "")).strip()
            if not note_id:
                add_debug_msg(f"Row {sheet_row}: invalid note (empty ID)")
                continue

            if not row_is_marked_for_sync(note_data, plan):
                add_debug_msg(f"Row {sheet_row}: note not marked for sync")
                continue

            # Attach the tags this row will carry
            note_data["tags"] = build_tags(note_data, plan)

        except Exception as e:
            add_debug_msg(f"Error processing row {sheet_row}: {e}")
            continue

    if cloze_rows:
        shown = ", ".join(str(r) for r in cloze_rows[:10])
        suffix = " …" if len(cloze_rows) > 10 else ""
        message = (
            f"{len(cloze_rows)} row(s) contain {{{{c1::…}}}} but no column is marked "
            f"`cloze` in the settings row (rows {shown}{suffix}) — the markup will "
            f"show as text. Add `cloze` to the column holding the sentences."
        )
        add_debug_msg(f"⚠️ {message}")
        log_to_addon(message, "SHEET_CONFIG")
        sheet_config.warnings.append(message)

    # An address that cannot be embedded frames an error message on the card, which
    # looks like the add-on broke rather than like a link that needs fixing.
    for warning in sorted(embed_warnings):
        message = f"⚠️ Embed: {warning}"
        add_debug_msg(message)
        log_to_addon(message, "SHEET_CONFIG")
        sheet_config.warnings.append(warning)

    # Detect duplicate (non-empty) IDs. These silently collapse during sync because
    # notes are keyed by their ID — only one survives and the others are
    # stranded/un-updated. Record them so the user can be warned.
    seen_ids: dict[str, int] = {}
    for note_data in remote_deck.notes:
        nid = str(note_data.get(plan.id_header, "")).strip()
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


# =============================================================================
# NAMES ANKI WILL SEE
# =============================================================================


def get_subdeck_name(main_deck_name, path_levels):
    """
    Generates subdeck name from the main deck and a row's SUBDECK levels.

    Args:
        main_deck_name (str): Main deck name
        path_levels (list): Deck path levels, outermost first (see column_model.deck_path)

    Returns:
        str: Full subdeck name in the format "MainDeck::Level1::Level2::..."
    """

    def clean_deck_text(text):
        """Cleans text for use as Anki deck name (single value, NOT list)."""
        if not text or not isinstance(text, str):
            return ""
        # Remove problematic characters but keep spaces intact
        # Deck names can't contain :: as it's the separator
        cleaned = text.strip().replace("::", "_").replace(":", "_")
        # Remove special characters that may cause issues, but allow brackets and basic punctuation
        cleaned = re.sub(r"[^\w\s\-_\[\]()]", "", cleaned)
        # Normalize multiple spaces to single space (keep spaces, don't replace with underscores)
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned

    # Only levels that actually carry a value become subdecks — a level whose text
    # survives cleaning as an empty string (e.g. it held only invalid characters) is
    # skipped as well, so the deck never gains a nameless level.
    parts = [main_deck_name]
    for level in path_levels or []:
        cleaned = clean_deck_text(str(level).strip())
        if cleaned:
            parts.append(cleaned)

    return "::".join(parts)


def get_note_type_name(url, remote_deck_name, is_cloze=False):
    """
    Generates standardized name for Sheets2Anki note types.

    Format: "Sheets2Anki - {remote_deck_name} - Basic/Cloze"
    The remote_deck_name already has conflict resolution applied by config_manager.
    The reverse direction is a second card template on the same note type, so it
    does not get a name of its own.

    Args:
        url (str): Remote deck URL
        remote_deck_name (str): Remote deck name from spreadsheet (with suffix if necessary)
        is_cloze (bool): If it's a Cloze note type

    Returns:
        str: Standardized note type name
    """
    note_type = "Cloze" if is_cloze else "Basic"

    # Use remote name directly (already comes with conflict suffix from config_manager)
    clean_remote_name = remote_deck_name.strip() if remote_deck_name else "RemoteDeck"

    return f"Sheets2Anki - {clean_remote_name} - {note_type}"
