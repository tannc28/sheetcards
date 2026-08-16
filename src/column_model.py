"""Column model for Sheets2Anki spreadsheets.

The spreadsheet drives the schema: only a handful of column names carry special
meaning, and every other column becomes an Anki note field named exactly like the
header. That way a sheet can use whatever vocabulary its subject calls for —
"Word", "Reading", "Meaning" — instead of a fixed column list baked into the code.
Headers may be in any language or script; the text becomes the field name verbatim.

Reserved headers (matched case-insensitively, surrounding whitespace ignored):

    ID          the row's stable key — required
    SYNC        per-row on/off switch; when the column is absent, every row syncs
    SUBDECK n   one level of the deck path, ordered by n (SUBDECK 1, SUBDECK 2, …)
    TAGS        comma-separated Anki tags

Everything else is a *content column*: it becomes a note field, and the order of
the columns in the sheet is the order the fields appear on the card by default.
"""

import re

# =============================================================================
# RESERVED HEADERS
# =============================================================================

IDENTIFIER = "ID"
SYNC = "SYNC"
TAGS = "TAGS"

# "SUBDECK 1", "subdeck2", "Subdeck  10" — the number is the level.
_SUBDECK_RE = re.compile(r"^subdeck\s*(\d+)$")

# Accepted truthy values for the SYNC column, compared against the cell value
# lower-cased and stripped.
SYNC_TRUE_VALUES = frozenset({"true", "1", "yes", "sim", "x", "✓"})


def normalize(header):
    """Folds a header to its comparison form: trimmed, lower-cased, BOM-free."""
    if not isinstance(header, str):
        return ""
    return header.replace("﻿", "").strip().lower()


def clean(header):
    """Returns the header as written, minus surrounding whitespace and any BOM."""
    if not isinstance(header, str):
        return ""
    return header.replace("﻿", "").strip()


def subdeck_level(header):
    """Returns the level of a SUBDECK column, or None if it isn't one."""
    match = _SUBDECK_RE.match(normalize(header))
    return int(match.group(1)) if match else None


def is_reserved(header):
    """True when the header carries special meaning rather than being a field."""
    folded = normalize(header)
    if folded in (normalize(IDENTIFIER), normalize(SYNC), normalize(TAGS)):
        return True
    return subdeck_level(header) is not None


class ColumnPlan:
    """How one sheet's headers map onto Anki.

    Attributes:
        id_header: the header that acts as ID, or None when the sheet has none
        sync_header: the header that gates syncing, or None when absent
        tags_header: the header holding tags, or None when absent
        subdeck_headers: headers forming the deck path, ordered by their level
        content_headers: every other header, in sheet order — these become fields
        duplicates: headers that appeared more than once (only the first is used)
    """

    def __init__(self):
        self.id_header = None
        self.sync_header = None
        self.tags_header = None
        self.subdeck_headers = []
        self.content_headers = []
        self.duplicates = []

    @property
    def has_id(self):
        return self.id_header is not None

    def note_type_fields(self):
        """Field list for the note type: the key first, then the content columns.

        ``ID`` leads because Anki treats the first field as the note's identity for
        duplicate detection, and it is the one field guaranteed to be filled.
        """
        return [IDENTIFIER] + list(self.content_headers)

    def __repr__(self):  # pragma: no cover - debugging aid
        return (
            f"ColumnPlan(id={self.id_header!r}, sync={self.sync_header!r}, "
            f"tags={self.tags_header!r}, subdecks={self.subdeck_headers!r}, "
            f"content={self.content_headers!r})"
        )


def plan_columns(headers):
    """Sorts a sheet's headers into the roles above.

    A header repeated in the sheet is honoured once — the first occurrence wins and
    the rest are recorded in ``duplicates``, because two columns feeding one field
    would make the note's content depend on column order in a way nobody expects.

    Args:
        headers (list[str]): the sheet's header row, as parsed

    Returns:
        ColumnPlan
    """
    plan = ColumnPlan()
    seen = set()
    subdecks = []

    for raw in headers or []:
        name = clean(raw)
        if not name:
            continue

        folded = normalize(name)
        if folded in seen:
            plan.duplicates.append(name)
            continue
        seen.add(folded)

        level = subdeck_level(name)
        if level is not None:
            subdecks.append((level, name))
        elif folded == normalize(IDENTIFIER):
            plan.id_header = name
        elif folded == normalize(SYNC):
            plan.sync_header = name
        elif folded == normalize(TAGS):
            plan.tags_header = name
        else:
            plan.content_headers.append(name)

    # Deck path follows the numbers, not the column positions, so moving SUBDECK 2
    # left of SUBDECK 1 in the sheet doesn't silently reorder anyone's decks.
    plan.subdeck_headers = [name for _, name in sorted(subdecks, key=lambda p: p[0])]

    return plan


def row_is_marked_for_sync(row, plan):
    """True when the row should be synced.

    A sheet with no SYNC column syncs everything — the column is opt-in gating, and
    treating its absence as "nothing syncs" would silently produce an empty deck.
    """
    if plan.sync_header is None:
        return True
    return str(row.get(plan.sync_header, "")).strip().lower() in SYNC_TRUE_VALUES


def deck_path(row, plan, sheet_config=None):
    """The row's deck path as a list of level names, empty levels dropped.

    Two ways to say it, and the settings row wins when a sheet uses both. A
    column named ``SUBDECK n`` is reserved and never becomes a field, which is
    the older way and still the shortest; a column that says ``subdeck=n`` in the
    settings row is an ordinary content column that *also* files the note, so the
    same value can be a level of the deck and something printed on the card
    without being typed into the sheet twice.

    ``sheet_config`` is optional so every caller that has no settings row in hand
    keeps working unchanged.
    """
    headers = getattr(sheet_config, "subdeck_columns", None) or plan.subdeck_headers
    path = []
    for header in headers:
        value = str(row.get(header, "")).strip()
        if value:
            path.append(value)
    return path


def tags_of(row, plan):
    """Tags for the row, split on commas and semicolons, blanks dropped."""
    if plan.tags_header is None:
        return []
    raw = str(row.get(plan.tags_header, "")).strip()
    if not raw:
        return []
    return [t.strip() for t in re.split(r"[,;]", raw) if t.strip()]
