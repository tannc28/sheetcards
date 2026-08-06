"""
Note types and card assets for the Sheets2Anki addon.

The spreadsheet defines its own columns (see ``column_model``) and the card layout
lives in the collection config (see ``sync_config``), so this module no longer knows
any column names. What is left is:
- the add-on's fixed names and the development-mode switch
- creating and reconciling the per-deck note types

Consolidated from:
- card_templates.py: Card templates and models
- column_definitions.py: Spreadsheet column definitions
"""

from .card_layout import build_templates

# =============================================================================
# CONSTANTS AND TEMPLATES
# =============================================================================

# Constant to identify if we are in development mode
# This constant will be changed to False during the build process
IS_DEVELOPMENT_MODE = True

# Hardcoded URLs for testing and simulations
TEST_SHEETS_URLS = [
    (
        "Sheets2Anki Template (Edit Link)",
        "https://docs.google.com/spreadsheets/d/1N-Va4ZzLUJBsD6wBaOkoeFTE6EnbZdaPBB88FYl2hrs/edit?usp=sharing",
    )
]

# Root deck name - non-modifiable constant by user
DEFAULT_PARENT_DECK_NAME = "Sheets2Anki"

# Tag prefix (lowercase for consistency - Anki tags are case-insensitive)
TAG_ROOT = "sheets2anki"

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
    Makes a note type's card templates match the ones the layout calls for.

    A template the layout no longer produces (the reverse card switched off) is
    removed together with its cards — that is exactly what switching it off means.

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


def create_model(
    col, model_name, fields, templates, is_cloze=False, url=None, debug_messages=None
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

    col.models.save(model)

    # Automatically register note type if URL was provided
    if url and model.get("id"):
        try:
            register_note_type_for_deck(url, model["id"], model_name, debug_messages)
        except Exception as e:
            if debug_messages:
                debug_messages.append(f"Error registering note type {model['id']}: {e}")

    return model


def ensure_custom_models(col, url, plan, layout, debug_messages=None):
    """
    Ensures both models (standard and cloze) exist and match the sheet.

    Fields come from the sheet's own columns and card templates from the deck's
    layout, so adding a column to the sheet adds a field here. Uses IDs stored in
    meta.json to find existing note types, instead of searching only by name.

    Args:
        col: Anki collection object
        url (str): Remote deck URL
        plan (ColumnPlan): how this sheet's headers map onto Anki
        layout (dict): the deck's card layout, as stored by ``sync_config``
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
    hand_edited = bool(layout.get("hand_edited"))

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

    for key, is_cloze in (("standard", False), ("cloze", True)):
        label = "Cloze" if is_cloze else "Basic"
        expected_name = get_note_type_name(url, remote_deck_name, is_cloze=is_cloze)
        templates = build_templates(layout, is_cloze=is_cloze)

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
            )
            continue

        model_name = model.get("name", expected_name)
        changed = add_missing_fields(col, model, fields, add_debug_msg)

        if hand_edited:
            add_debug_msg(
                f"Templates of '{model_name}' left alone (layout is hand-edited)"
            )
        elif apply_templates(col, model, templates):
            changed = True
            add_debug_msg(f"Templates regenerated for '{model_name}'")

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

    A deck whose layout is marked ``hand_edited`` is skipped: the user maintains
    those templates themselves and regenerating them would throw that work away.
    A deck with no layout yet is skipped too — its columns are only known once it
    is downloaded, and rendering the empty default would blank out its cards.

    Args:
        col: Anki collection object
        debug_messages (list, optional): List for debug

    Returns:
        int: Number of updated note types
    """
    if debug_messages is None:
        debug_messages = []

    from .config_manager import get_remote_decks
    from .sync_config import get_card_layout

    updated_count = 0
    remote_decks = get_remote_decks() or {}

    debug_messages.append(
        f"[UPDATE_TEMPLATES] Found {len(remote_decks)} connected decks"
    )

    for sheet_id, deck_info in remote_decks.items():
        deck_name = deck_info.get("remote_deck_name") or sheet_id
        layout = get_card_layout(sheet_id)

        if layout.get("hand_edited"):
            debug_messages.append(
                f"[UPDATE_TEMPLATES] ⏭️ {deck_name}: layout is hand-edited, templates preserved"
            )
            continue

        if not layout.get("front") and not layout.get("back"):
            debug_messages.append(
                f"[UPDATE_TEMPLATES] ⏭️ {deck_name}: no layout stored yet, templates left to the deck's own sync"
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
                templates = build_templates(layout, is_cloze=model.get("type") == 1)

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
