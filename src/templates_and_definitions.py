"""
Note types and card assets for the SheetCards addon.

The spreadsheet defines its own columns (see ``column_model``) and its own
presentation (see ``sheet_config``), so this module no longer knows any column names.
What is left is:
- the add-on's fixed names and the development-mode switch
- creating and reconciling the per-deck note types

Consolidated from:
- card_templates.py: Card templates and models
- column_definitions.py: Spreadsheet column definitions
"""

from .card_layout import build_templates

# Defined in the pure layer, which is what actually builds the tags; re-exported
# here so the long-standing `from .templates_and_definitions import TAG_ROOT`
# keeps working and the constant has exactly one definition.
ADDON_MENU_NAME = "SheetCards"

from .tsv_model import DECK_NAME_PREFIX  # noqa: F401  (facade)
from .tsv_model import TAG_ROOT  # noqa: F401  (facade)
from .tsv_model import deck_root_name  # noqa: F401  (facade)

# =============================================================================
# CONSTANTS AND TEMPLATES
# =============================================================================

# Constant to identify if we are in development mode
# This constant will be changed to False during the build process
IS_DEVELOPMENT_MODE = True

# Hardcoded URLs for testing and simulations.
#
# The workbook lives in this repository (examples/, built from the TSVs beside it
# by scripts/build_examples.py) rather than in someone's Drive: a template nobody
# here can edit goes stale the first time a directive is added, and there is no
# way to notice. GitHub's /blob/ address is used deliberately — it is the one a
# person copies out of the browser, and normalize_file_url turns it into the raw
# address that serves the bytes.
TEST_SHEETS_URLS = [
    (
        "SheetCards examples (15 sheets, basic → advanced)",
        "https://github.com/tannc28/sheetcards/blob/main/examples/sheetcards-examples.xlsx",
    )
]


# =============================================================================
# NOTE TYPES
# =============================================================================


def get_model_field_names(model):
    """
    Returns the field names of a note type, in order.

    Args:
        model: Anki note type

    Returns:
        list: Field names
    """
    names = []
    for field in model.get("flds", []):
        if isinstance(field, dict) or hasattr(field, "get"):
            names.append(field.get("name", ""))
        else:
            names.append(getattr(field, "name", ""))
    return names


def add_missing_fields(col, model, fields, add_debug_msg=None):
    """
    Adds fields the note type does not have yet.

    A field the sheet no longer has is deliberately kept: removing it would delete
    the content the user already collected under that column.

    Args:
        col: Anki collection object
        model: Anki note type
        fields (list): Field names the sheet calls for
        add_debug_msg (callable, optional): Debug message sink

    Returns:
        bool: True if any field was added
    """
    existing = get_model_field_names(model)
    added = [name for name in fields if name not in existing]

    for name in added:
        col.models.add_field(model, col.models.new_field(name))
        if add_debug_msg:
            add_debug_msg(f"Added field '{name}' to '{model.get('name', '')}'")

    return bool(added)


def apply_templates(col, model, templates):
    """
    Makes a note type's card templates match the ones the sheet calls for.

    A template the sheet no longer produces (``reverse`` taken out of the settings
    row) is removed together with its cards — that is exactly what removing it means.

    Args:
        col: Anki collection object
        model: Anki note type
        templates (list): ``{"name", "qfmt", "afmt"}`` dicts, in order

    Returns:
        bool: True if anything changed
    """
    changed = False

    for index, spec in enumerate(templates):
        current = model.get("tmpls", [])
        if index < len(current):
            template = current[index]
            for key in ("name", "qfmt", "afmt"):
                if template.get(key) != spec[key]:
                    template[key] = spec[key]
                    changed = True
        else:
            template = col.models.new_template(spec["name"])
            template["qfmt"] = spec["qfmt"]
            template["afmt"] = spec["afmt"]
            col.models.add_template(model, template)
            changed = True

    while len(model.get("tmpls", [])) > len(templates):
        col.models.remove_template(model, model["tmpls"][-1])
        changed = True

    return changed


def apply_sort_field(col, model, fields, sheet_config):
    """Points the note type's sort field at the column the sheet named.

    Anki stores it as an index into the field list and uses it for two things: the
    first column of the browser, and what a deck sorts by there. Field 0 is the
    default, and field 0 here is ``ID`` — so without this a sheet's notes are listed
    as w01, w02, w03, which is a list of nothing.

    Returns True when the model changed, so the caller knows whether to save.
    """
    header = getattr(sheet_config, "sort_field", None)
    if not header or header not in fields:
        return False
    index = fields.index(header)
    if model.get("sortf") == index:
        return False
    model["sortf"] = index
    return True


def create_model(
    col,
    model_name,
    fields,
    templates,
    is_cloze=False,
    url=None,
    debug_messages=None,
    sheet_config=None,
):
    """
    Creates a new Anki note model.

    Args:
        col: Anki collection object
        model_name (str): Name for the new model
        fields (list): Field names, in order (the first one is the note's key)
        templates (list): ``{"name", "qfmt", "afmt"}`` dicts, in order
        is_cloze (bool): Whether to create a cloze model
        url (str, optional): Remote deck URL for automatic registration
        debug_messages (list, optional): List for debug

    Returns:
        object: The created Anki model
    """
    from .utils import register_note_type_for_deck

    model = col.models.new(model_name)
    if is_cloze:
        model["type"] = 1  # Set as cloze type

    for field in fields:
        col.models.add_field(model, col.models.new_field(field))

    for spec in templates:
        template = col.models.new_template(spec["name"])
        template["qfmt"] = spec["qfmt"]
        template["afmt"] = spec["afmt"]
        col.models.add_template(model, template)

    if sheet_config is not None:
        apply_sort_field(col, model, list(fields), sheet_config)

    col.models.save(model)

    # Automatically register note type if URL was provided
    if url and model.get("id"):
        try:
            register_note_type_for_deck(url, model["id"], model_name, debug_messages)
        except Exception as e:
            if debug_messages:
                debug_messages.append(f"Error registering note type {model['id']}: {e}")

    return model


def ensure_custom_models(col, url, plan, sheet_config, debug_messages=None):
    """
    Ensures both models (standard and cloze) exist and match the sheet.

    Fields come from the sheet's own columns and card templates from its settings
    row, so adding a column to the sheet adds a field here. Uses IDs stored in
    meta.json to find existing note types, instead of searching only by name.

    Args:
        col: Anki collection object
        url (str): Remote deck URL
        plan (ColumnPlan): how this sheet's headers map onto Anki
        sheet_config (SheetConfig): the sheet's parsed settings row
        debug_messages (list, optional): List for debug

    Returns:
        dict: Dictionary containing 'standard' and 'cloze' models
    """
    from .config_manager import get_deck_note_type_ids
    from .config_manager import get_deck_remote_name
    from .utils import get_note_type_name
    from .utils import register_note_type_for_deck

    def add_debug_msg(message):
        if debug_messages is not None:
            debug_messages.append(f"[ENSURE_MODELS] {message}")

    remote_deck_name = get_deck_remote_name(url) or "RemoteDeck"
    existing_note_types = get_deck_note_type_ids(url) or {}
    fields = plan.note_type_fields()

    add_debug_msg(f"Searching note types for remote_deck_name='{remote_deck_name}'")
    add_debug_msg(f"Existing note types: {len(existing_note_types)} found")

    def find_registered_note_type(suffix):
        """The model registered for this deck whose name ends in ``suffix``."""
        for note_type_id_str, note_type_name in existing_note_types.items():
            if not note_type_name.endswith(suffix):
                continue
            try:
                note_type_id = int(note_type_id_str)
            except (ValueError, TypeError):
                continue

            from anki.models import NotetypeId

            model = col.models.get(NotetypeId(note_type_id))
            if model:
                add_debug_msg(
                    f"Found existing note type: ID {note_type_id} - '{note_type_name}'"
                )
                return model
        return None

    models = {}

    # Cloze is a sheet-level choice: a column declares `cloze` and the templates
    # apply Anki's filter to that column. With no such column there is no
    # `{{cloze:…}}` to put in the template, and Anki refuses the note type outright
    # — "Expected to find '{{cloze:Text}}' or similar" — which fails the whole sync
    # for a sheet that has nothing to do with cloze. Nothing needs the model
    # either: create_new_note routes on bool(sheet_config.cloze_field).
    wants_cloze = bool(getattr(sheet_config, "cloze_field", None))
    if not wants_cloze:
        add_debug_msg("No column declares 'cloze' — not provisioning a Cloze note type")

    for key, is_cloze in (("standard", False), ("cloze", True)):
        if is_cloze and not wants_cloze:
            continue
        label = "Cloze" if is_cloze else "Basic"
        expected_name = get_note_type_name(url, remote_deck_name, is_cloze=is_cloze)
        templates = build_templates(plan, sheet_config, is_cloze=is_cloze)

        model = find_registered_note_type(f" - {label}")
        registered = model is not None

        if model is None:
            # Registration can be lost (meta.json edited or restored) while the note
            # type itself is still there — reusing it avoids a duplicate note type.
            model = col.models.by_name(expected_name)

        if model is None:
            add_debug_msg(f"Creating new ({label}) model: '{expected_name}'")
            models[key] = create_model(
                col,
                expected_name,
                fields,
                templates,
                is_cloze=is_cloze,
                url=url,
                debug_messages=debug_messages,
                sheet_config=sheet_config,
            )
            continue

        model_name = model.get("name", expected_name)
        changed = add_missing_fields(col, model, fields, add_debug_msg)

        if apply_templates(col, model, templates):
            changed = True
            add_debug_msg(f"Templates regenerated for '{model_name}'")

        # After add_missing_fields, so a column added to the sheet in the same sync
        # that named it the sort column is already in the list to be found.
        if apply_sort_field(col, model, fields, sheet_config):
            changed = True
            add_debug_msg(f"Sort field set to '{sheet_config.sort_field}'")

        if changed:
            col.models.save(model)

        if not registered:
            register_note_type_for_deck(url, model["id"], expected_name, debug_messages)
            add_debug_msg(
                f"Existing ({label}) model registered: '{model_name}' → expected: '{expected_name}'"
            )
        else:
            add_debug_msg(f"Using existing ({label}) model: '{model_name}'")

        models[key] = model

    return models


def update_existing_note_type_templates(col, debug_messages=None):
    """
    Regenerates the card templates of every connected deck's note types.

    The sheet is the source of truth, so this rebuilds from the settings the last
    sync cached. A deck that has never been synced is skipped — its columns are only
    known once it is downloaded, and rendering nothing would blank out its cards.

    Args:
        col: Anki collection object
        debug_messages (list, optional): List for debug

    Returns:
        int: Number of updated note types
    """
    if debug_messages is None:
        debug_messages = []

    from .config_manager import get_remote_decks
    from .sync_config import cached_plan_and_config

    updated_count = 0
    remote_decks = get_remote_decks() or {}

    debug_messages.append(
        f"[UPDATE_TEMPLATES] Found {len(remote_decks)} connected decks"
    )

    for sheet_id, deck_info in remote_decks.items():
        deck_name = deck_info.get("remote_deck_name") or sheet_id
        plan, sheet_config = cached_plan_and_config(sheet_id)

        if plan is None:
            debug_messages.append(
                f"[UPDATE_TEMPLATES] ⏭️ {deck_name}: no settings cached yet, templates left to the deck's own sync"
            )
            continue

        for note_type_id_str in deck_info.get("note_types", {}):
            try:
                from anki.models import NotetypeId

                model = col.models.get(NotetypeId(int(note_type_id_str)))
                if not model:
                    debug_messages.append(
                        f"[UPDATE_TEMPLATES] Note type ID {note_type_id_str} not found in Anki"
                    )
                    continue

                model_name = model.get("name", "")
                templates = build_templates(
                    plan, sheet_config, is_cloze=model.get("type") == 1
                )

                if apply_templates(col, model, templates):
                    col.models.save(model)
                    updated_count += 1
                    debug_messages.append(
                        f"[UPDATE_TEMPLATES] ✅ {model_name} updated successfully"
                    )
                else:
                    debug_messages.append(
                        f"[UPDATE_TEMPLATES] ⏭️ {model_name} is already up to date"
                    )

            except Exception as e:
                debug_messages.append(
                    f"[UPDATE_TEMPLATES] ❌ Error processing note type {note_type_id_str}: {e}"
                )
                import traceback

                debug_messages.append(traceback.format_exc())

    debug_messages.append(
        f"[UPDATE_TEMPLATES] 🎯 Total note types updated: {updated_count}"
    )
    return updated_count
