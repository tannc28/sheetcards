"""Settings that must follow the user between machines.

Anki's own collection config (``col.get_config`` / ``col.set_config``) lives in the
``config`` table, which carries a ``usn`` column and therefore travels through
AnkiWeb along with the notes and note types. Anything stored here is available on
every machine the collection syncs to, with no Google API and no extra setup.

``meta.json`` stays the home for machine-local settings — most importantly the AI
provider API key, which should not be uploaded to AnkiWeb.
"""

import copy

try:
    from .compat import mw
except ImportError:  # pragma: no cover - direct (non-package) import in tests
    from compat import mw

# One collection-config key holding {sheet_id: layout}. A single key keeps the
# collection's config table tidy and makes the whole set easy to read at once.
LAYOUT_KEY = "sheets2anki::card_layouts"

# Card layout defaults. `front`/`back` are filled per deck from the sheet's own
# column order the first time a deck is synced.
DEFAULT_LAYOUT = {
    "front": [],
    "back": [],
    "show_labels": False,
    "front_size": 40,
    "back_size": 18,
    "align": "center",
    "reverse_card": False,
    "timer": True,
    "timer_position": "between_sections",  # or "top_middle"
    # Set from the dialog's "let me edit the template myself" switch. While true,
    # sync leaves the note type's templates alone instead of regenerating them.
    "hand_edited": False,
}


def _collection():
    """The open collection, or None when Anki isn't available (tests, headless)."""
    return getattr(mw, "col", None) if mw else None


def _read_all():
    """Every stored layout, keyed by sheet id. Never raises."""
    col = _collection()
    if col is None:
        return {}
    try:
        stored = col.get_config(LAYOUT_KEY, default=None)
    except Exception:
        return {}
    return stored if isinstance(stored, dict) else {}


def _write_all(layouts):
    """Persists the whole layout map. Returns True when it reached the collection."""
    col = _collection()
    if col is None:
        return False
    try:
        col.set_config(LAYOUT_KEY, layouts)
        return True
    except Exception:
        return False


def default_layout_for(content_headers):
    """Builds the starting layout for a sheet from its column order.

    The first content column is the prompt and the rest are the answer — the same
    convention as Anki's own CSV import, and it means reordering columns in the
    sheet reorders the card without touching any setting.
    """
    headers = [h for h in (content_headers or []) if h]
    layout = copy.deepcopy(DEFAULT_LAYOUT)
    if headers:
        layout["front"] = [headers[0]]
        layout["back"] = headers[1:]
    return layout


def _coerce(layout, content_headers=None):
    """Fills in missing keys and drops fields the sheet no longer has."""
    merged = copy.deepcopy(DEFAULT_LAYOUT)
    if isinstance(layout, dict):
        merged.update(layout)

    def field_list(value):
        return (
            [f for f in value if isinstance(f, str)] if isinstance(value, list) else []
        )

    front = field_list(merged.get("front"))
    back = field_list(merged.get("back"))

    if content_headers is not None:
        known = set(content_headers)
        # A column removed from the sheet stops being rendered, but the note's field
        # is left in place — dropping it here would silently delete the user's data.
        front = [f for f in front if f in known]
        back = [f for f in back if f in known]

        # A newly added column has to surface somewhere, or it would look like the
        # add-on ignored it.
        placed = set(front) | set(back)
        back += [h for h in content_headers if h not in placed]

    merged["front"] = front
    merged["back"] = back
    return merged


def get_card_layout(sheet_id, content_headers=None):
    """The layout for one sheet, defaulted and reconciled against its columns."""
    stored = _read_all().get(sheet_id)
    if stored is None:
        return (
            default_layout_for(content_headers)
            if content_headers
            else copy.deepcopy(DEFAULT_LAYOUT)
        )
    return _coerce(stored, content_headers)


def set_card_layout(sheet_id, layout):
    """Stores one sheet's layout. Returns True when it reached the collection."""
    layouts = _read_all()
    layouts[sheet_id] = _coerce(layout)
    return _write_all(layouts)


def ensure_card_layout(sheet_id, content_headers):
    """Returns the stored layout, creating it from column order on first sight."""
    layouts = _read_all()
    if sheet_id in layouts:
        return _coerce(layouts[sheet_id], content_headers)

    layout = default_layout_for(content_headers)
    layouts[sheet_id] = layout
    _write_all(layouts)
    return layout


def forget_card_layout(sheet_id):
    """Drops a sheet's layout, e.g. when its deck is disconnected."""
    layouts = _read_all()
    if sheet_id in layouts:
        del layouts[sheet_id]
        return _write_all(layouts)
    return False
