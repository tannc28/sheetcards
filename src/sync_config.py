"""A cache of what the last sync read out of each sheet's settings row.

The spreadsheet is the single source of truth for how a card looks: the ``#config``
row is parsed on every sync and rendered straight into the note type's templates.
Nothing here is editable — this module only remembers the *result* of the last parse,
so a dialog can show a deck's current settings (and the warnings the parse produced)
without downloading the sheet again, and so a template rebuild that runs outside a
sync still knows what the sheet asked for.

Anki's own collection config (``col.get_config`` / ``col.set_config``) lives in the
``config`` table, which carries a ``usn`` column and therefore travels through
AnkiWeb along with the notes and note types. Storing the cache there means a second
machine renders identical cards before it has ever downloaded the sheet itself.

``meta.json`` stays the home for machine-local settings, such as API keys and
directory paths, which should not be uploaded to AnkiWeb.
"""

from .column_model import IDENTIFIER
from .column_model import plan_columns
from .sheet_config import FieldConfig
from .sheet_config import SheetConfig
from .sheet_config import resolve_roles

try:
    from .compat import mw
except ImportError:  # pragma: no cover - direct (non-package) import in tests
    from compat import mw

# One collection-config key holding {sheet_id: settings}. A single key keeps the
# collection's config table tidy and makes the whole set easy to read at once.
SETTINGS_KEY = "sheets2anki::sheet_settings"


def _collection():
    """The open collection, or None when Anki isn't available (tests, headless)."""
    return getattr(mw, "col", None) if mw else None


def _read_all():
    """Every cached sheet's settings, keyed by sheet id. Never raises."""
    col = _collection()
    if col is None:
        return {}
    try:
        stored = col.get_config(SETTINGS_KEY, default=None)
    except Exception:
        return {}
    return stored if isinstance(stored, dict) else {}


def _write_all(settings):
    """Persists the whole cache. Returns True when it reached the collection."""
    col = _collection()
    if col is None:
        return False
    try:
        col.set_config(SETTINGS_KEY, settings)
        return True
    except Exception:
        return False


def field_to_dict(field_config):
    """One column's settings as JSON-safe primitives."""
    return dict(vars(field_config))


def field_from_dict(data):
    """Rebuilds a :class:`FieldConfig`, ignoring keys it no longer knows."""
    field_config = FieldConfig()
    if isinstance(data, dict):
        for key, value in data.items():
            if key in vars(field_config):
                setattr(field_config, key, value)
    return field_config


def to_dict(plan, sheet_config):
    """The cache entry for one sheet: its columns plus everything the row said."""
    return {
        "content_headers": list(plan.content_headers),
        "present": bool(sheet_config.present),
        "align": sheet_config.align,
        "speed": sheet_config.speed,
        "reverse": bool(sheet_config.reverse),
        "warnings": list(sheet_config.warnings),
        "fields": {
            header: field_to_dict(field_config)
            for header, field_config in sheet_config.fields.items()
        },
    }


def from_dict(stored):
    """Turns a cache entry back into the ``(plan, sheet_config)`` pair that renders it.

    Returns ``(None, None)`` for an entry that carries no columns: rendering templates
    from it would produce a card with no fields on it at all.
    """
    if not isinstance(stored, dict):
        return None, None

    headers = [h for h in stored.get("content_headers") or [] if isinstance(h, str)]
    if not headers:
        return None, None

    plan = plan_columns([IDENTIFIER] + headers)

    sheet_config = SheetConfig()
    sheet_config.present = bool(stored.get("present"))
    sheet_config.align = stored.get("align")
    sheet_config.speed = stored.get("speed")
    sheet_config.reverse = bool(stored.get("reverse"))
    sheet_config.warnings = list(stored.get("warnings") or [])
    fields = stored.get("fields")
    if isinstance(fields, dict):
        sheet_config.fields = {
            header: field_from_dict(data)
            for header, data in fields.items()
            if header in headers
        }

    # `cloze_field`, `type_field` and `subdeck_columns` are derived from the
    # columns rather than stored, so a cache entry that only carried the per-column
    # settings came back with all three unset — and a note type rebuilt from it
    # rendered a cloze sheet with no `{{cloze:}}` in its template, which Anki
    # refuses to save. Derived here by the same function the parser uses, with no
    # warn callback because the complaints were recorded when the sheet was read.
    resolve_roles(sheet_config, headers)

    return plan, sheet_config


def cache_sheet_settings(sheet_id, plan, sheet_config):
    """Records what this sync parsed. Returns True when it reached the collection."""
    settings = _read_all()
    settings[sheet_id] = to_dict(plan, sheet_config)
    return _write_all(settings)


def get_sheet_snapshot(sheet_id):
    """The raw cache entry for one sheet, or None when it has never been synced.

    Plain primitives, for a dialog that only wants to *show* what the sheet asked
    for. Rendering goes through :func:`cached_plan_and_config` instead.
    """
    stored = _read_all().get(sheet_id)
    return stored if isinstance(stored, dict) else None


def cached_plan_and_config(sheet_id):
    """The ``(plan, sheet_config)`` last parsed for a sheet, or ``(None, None)``."""
    return from_dict(_read_all().get(sheet_id))


def forget_sheet_settings(sheet_id):
    """Drops a sheet's cached settings, e.g. when its deck is disconnected."""
    settings = _read_all()
    if sheet_id in settings:
        del settings[sheet_id]
        return _write_all(settings)
    return False
