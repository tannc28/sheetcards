"""
Templates and column definitions for the Sheets2Anki addon.

This module centralizes:
- Standardized spreadsheet column name definitions
- HTML templates for Anki cards
- Functions for creating note models
- Data structure validation

Consolidated from:
- card_templates.py: Card templates and models
- column_definitions.py: Spreadsheet column definitions
"""

# =============================================================================
# CONTROL FIELDS
# =============================================================================

# Basic system fields
identifier = "ID"  # Unique question identifier (required)
is_sync = "SYNC"  # Synchronization control field (true/false/1/0)
sanity_check = "[ ✅ / ❌ ] - SANITY CHECK"  # Sanity check/Quality control field

# =============================================================================
# MAIN FIELDS
# =============================================================================

# Main question fields
question = "QUESTION"  # Main question text / front of card
answer = "ANSWER"  # Succinct and atomic answer to the question
reverse = "REVERSE"  # Reverse question (Answer -> Question)

# =============================================================================
# DETAIL FIELDS
# =============================================================================

# Additional information about the question
info_1 = "COMPLEMENTARY INFO"  # Basic complementary information
info_2 = "DETAILED INFO"  # Additional detailed information

# =============================================================================
# EXAMPLE FIELDS
# =============================================================================

# Examples related to the question (up to 3 examples)
example_1 = "EXAMPLE 1"  # First example
example_2 = "EXAMPLE 2"  # Second example
mnemonic = "MNEMONIC"  # Mnemonic for memory aid

# =============================================================================
# MULTIMEDIA FIELDS
# =============================================================================

# Helps make information visually more attractive
multimedia_1 = "HTML IMAGE"  # HTML code for renderable images and illustrations
multimedia_2 = "HTML VIDEO"  # HTML code for embedded videos (YouTube, Vimeo, etc.)

# =============================================================================
# CATEGORIZATION FIELDS
# =============================================================================

# Hierarchical content categorization
hierarchy_1 = "IMPORTANCE"  # Question importance level
hierarchy_2 = "TOPIC"  # Main question topic
hierarchy_3 = "SUBTOPIC"  # Specific subtopic
hierarchy_4 = "CONCEPT"  # Atomic concept being asked (more refined than subtopic)

# =============================================================================
# METADATA FIELDS
# =============================================================================

# Context and source information
tags_1 = "BOARDS"  # Related exam boards
tags_2 = "LAST YEAR IN EXAM"  # Last year appeared in exam
tags_3 = "CAREERS"  # Related careers or professional areas
tags_4 = "OTHER TAGS"  # Additional tags for organization

# =============================================================================
# CUSTOMIZABLE EXTRA FIELDS
# =============================================================================

# Extra fields for user customization
extra_field_1 = "EXTRA FIELD 1"  # Extra field 1 - free use
extra_field_2 = "EXTRA FIELD 2"  # Extra field 2 - free use
extra_field_3 = "EXTRA FIELD 3"  # Extra field 3 - free use

# =============================================================================
# VALIDATION CONFIGURATIONS
# =============================================================================

# Complete list of all available spreadsheet columns
ALL_AVAILABLE_COLUMNS = [
    identifier,  # Unique identifier
    is_sync,  # Synchronization control
    sanity_check,  # Quality control field
    hierarchy_1,  # Importance level
    hierarchy_2,  # Main topic
    hierarchy_3,  # Subtopic
    hierarchy_4,  # Atomic concept
    question,  # Main question text / front of card
    answer,  # Succinct answer (core of response)
    reverse,  # Reverse question
    info_1,  # Complementary info
    info_2,  # Detailed info
    example_1,  # First example
    example_2,  # Second example
    mnemonic,  # Mnemonic for memory aid
    multimedia_1,  # HTML code for images and illustrations
    multimedia_2,  # HTML code for embedded videos
    tags_1,  # Related exam boards
    tags_2,  # Exam year
    tags_3,  # Careers or professional areas
    tags_4,  # Additional tags
    extra_field_1,  # Extra field 1
    extra_field_2,  # Extra field 2
    extra_field_3,  # Extra field 3
]

# Fields considered mandatory for note creation
# Fields considered mandatory for note creation
ESSENTIAL_FIELDS = [identifier]

# Fields required in spreadsheet headers (for parsing to work)
# Fields required in spreadsheet headers (for parsing to work)
REQUIRED_HEADERS = [identifier, question, answer]

# Fields that can be used for filtering/selection
# Fields that can be used for filtering/selection
FILTER_FIELDS = [
    hierarchy_1,
    hierarchy_2,
    hierarchy_3,
    hierarchy_4,
    tags_1,
    tags_2,
    tags_3,
    tags_4,
]

# Fields containing extensive text information
TEXT_FIELDS = [
    question,
    answer,
    reverse,
    info_1,
    info_2,
    example_1,
    example_2,
    mnemonic,
    extra_field_1,
    extra_field_2,
    extra_field_3,
]

# Fields containing media (images, videos, etc.)
MEDIA_FIELDS = [
    multimedia_1,
    multimedia_2,
]

# Fields that should be included in Anki notes
NOTE_FIELDS = [
    identifier,  # Unique identifier
    hierarchy_1,  # Importance level
    hierarchy_2,  # Main topic
    hierarchy_3,  # Subtopic
    hierarchy_4,  # Atomic concept
    question,  # Question text
    reverse,  # Reverse question
    answer,  # Succinct answer (core of response)
    info_1,  # Complementary info
    info_2,  # Detailed info
    example_1,  # First example
    example_2,  # Second example
    mnemonic,  # Mnemonic for memory aid
    multimedia_1,  # HTML code for images and illustrations
    multimedia_2,  # HTML code for embedded videos
    extra_field_1,  # Extra field 1
    extra_field_2,  # Extra field 2
    extra_field_3,  # Extra field 3
    tags_1,  # Related exam boards
    tags_2,  # Exam year
    tags_3,  # Careers or professional areas
    tags_4,  # Additional tags
    sanity_check,  # Quality control field
]

# Fields containing metadata
METADATA_FIELDS = [
    hierarchy_1,
    hierarchy_2,
    hierarchy_3,
    hierarchy_4,
    tags_1,
    tags_2,
    tags_3,
    tags_4,
]

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

# Template constants for card generation
# --- Re-exported from card_assets (split out of this file) ---
from .card_assets import _AI_JS_ASK_MODAL  # noqa: F401
from .card_assets import _AI_JS_CAPTURE  # noqa: F401
from .card_assets import _AI_JS_COLLECT  # noqa: F401
from .card_assets import _AI_JS_HEAD  # noqa: F401
from .card_assets import _AI_JS_RENDER  # noqa: F401
from .card_assets import _AI_JS_RESET_ASK  # noqa: F401
from .card_assets import _AI_JS_TAIL  # noqa: F401
from .card_assets import AI_HELP_BUTTON_HTML  # noqa: F401
from .card_assets import AI_HELP_CSS  # noqa: F401
from .card_assets import AI_HELP_JS  # noqa: F401
from .card_assets import AI_HELP_JS_DESKTOP  # noqa: F401
from .card_assets import AI_HELP_JS_MOBILE_TEMPLATE  # noqa: F401
from .card_assets import ANSWER_SEPARATOR_HTML
from .card_assets import CARD_SHOW_HIDE_TEMPLATE  # noqa: F401
from .card_assets import REVERSE_INDICATOR_CSS  # noqa: F401
from .card_assets import REVERSE_INDICATOR_HTML  # noqa: F401
from .card_assets import TIMER_CSS  # noqa: F401
from .card_assets import TIMER_CSS_BETWEEN_SECTIONS  # noqa: F401
from .card_assets import TIMER_CSS_TOP_MIDDLE  # noqa: F401
from .card_assets import TIMER_HTML  # noqa: F401
from .card_assets import TIMER_JS_BACK  # noqa: F401
from .card_assets import TIMER_JS_FRONT  # noqa: F401


def generate_ai_assistance_js(
    mobile_enabled=False,
    service="gemini",
    model="",
    api_key="",
    prompt_help="",
    prompt_ask="",
    prompt_checker="",
):
    """
    Generates AI Assistance JavaScript based on configuration.

    Args:
        mobile_enabled: If True, embed API config for mobile support
        service: AI service (gemini, claude, openai)
        model: Model ID
        api_key: API key
        prompt_help: Custom prompt template for AI Help
        prompt_ask: Custom prompt template for AI Ask
        prompt_checker: Custom prompt template for AI Checker

    Returns:
        str: JavaScript code for AI Help
    """
    import base64
    import json

    if not mobile_enabled:
        return AI_HELP_JS_DESKTOP

    # Encode prompts as Base64 to prevent corruption by:
    # 1. HTML parser interpreting XML tags (<command>, <output_format>, etc.)
    # 2. Anki's template engine interpreting {{...}} as field references
    # 3. Python's .format() interpreting {...} as format placeholders
    # The JS code decodes them at runtime using _b64decode()
    def encode_prompt_b64(p):
        return base64.b64encode(p.encode("utf-8")).decode("ascii")

    prompt_help_b64 = encode_prompt_b64(prompt_help)
    prompt_ask_b64 = encode_prompt_b64(prompt_ask)
    prompt_checker_b64 = encode_prompt_b64(prompt_checker)

    # Safely serialize string values to prevent JS injection from special chars
    service_json = json.dumps(service)
    model_json = json.dumps(model)
    api_key_json = json.dumps(api_key)

    return (
        AI_HELP_JS_MOBILE_TEMPLATE.replace("{service_json}", service_json)
        .replace("{model_json}", model_json)
        .replace("{api_key_json}", api_key_json)
        .replace("{prompt_help_b64}", prompt_help_b64)
        .replace("{prompt_ask_b64}", prompt_ask_b64)
        .replace("{prompt_checker_b64}", prompt_checker_b64)
    )


# Default values for empty fields (will be converted to lowercase by clean_tag_text)
DEFAULT_IMPORTANCE = "[MISSING_IMPORTANCE]"
DEFAULT_TOPIC = "[MISSING_TOPIC]"
DEFAULT_SUBTOPIC = "[MISSING_SUBTOPIC]"
DEFAULT_CONCEPT = "[MISSING_CONCEPT]"

# Root deck name - non-modifiable constant by user
DEFAULT_PARENT_DECK_NAME = "Sheets2Anki"

# Tag prefixes (all lowercase for consistency - Anki tags are case-insensitive)
TAG_ROOT = "sheets2anki"
TAG_TOPICS = "topics"
TAG_SUBTOPICS = "subtopics"
TAG_CONCEPTS = "concepts"
TAG_EXAM_BOARDS = "boards"
TAG_YEARS = "years"
TAG_CAREERS = "careers"
TAG_IMPORTANCE = "importance"
TAG_ADDITIONAL = "other_tags"

# =============================================================================
# COLUMN VALIDATION FUNCTIONS
# =============================================================================


def validate_required_columns(columns):
    """
    Validates if all required columns are present in the spreadsheet.

    Args:
        columns (list): List of spreadsheet column names

    Returns:
        tuple: (is_valid, missing_columns) where:
            - is_valid: bool indicating if all columns are present
            - missing_columns: list of missing columns
    """
    missing_columns = [col for col in ALL_AVAILABLE_COLUMNS if col not in columns]
    return len(missing_columns) == 0, missing_columns


def is_essential_field(field_name):
    """
    Checks if a field is considered essential for note creation.

    Args:
        field_name (str): Field name to check

    Returns:
        bool: True if field is essential, False otherwise
    """
    return field_name in ESSENTIAL_FIELDS


def is_filter_field(field_name):
    """
    Checks if a field can be used for filtering/selection.

    Args:
        field_name (str): Field name to check

    Returns:
        bool: True if field can be used for filtering, False otherwise
    """
    return field_name in FILTER_FIELDS


def get_field_category(field_name):
    """
    Returns the category of a specific field.

    Args:
        field_name (str): Field name

    Returns:
        str: Field category ('essential', 'text', 'metadata', 'filter', 'unknown')
    """
    if field_name in ESSENTIAL_FIELDS:
        return "essential"
    elif field_name in TEXT_FIELDS:
        return "text"
    elif field_name in METADATA_FIELDS:
        return "metadata"
    elif field_name in FILTER_FIELDS:
        return "filter"
    else:
        return "unknown"


def get_all_column_info():
    """
    Returns complete information about all defined columns.

    Returns:
        dict: Dictionary with detailed information for each column
    """
    column_info = {}

    for column in ALL_AVAILABLE_COLUMNS:
        column_info[column] = {
            "name": column,
            "category": get_field_category(column),
            "is_essential": is_essential_field(column),
            "is_filter": is_filter_field(column),
            "is_text": column in TEXT_FIELDS,
            "is_metadata": column in METADATA_FIELDS,
        }

    return column_info


# =============================================================================
# CARD TEMPLATES
# =============================================================================


def create_card_template(
    is_cloze=False, timer_position=None, ai_assistance_enabled=None, is_reverse=False
):
    """
    Creates the HTML template for a card (standard or cloze).

    Args:
        is_cloze (bool): Whether to create a cloze template
        timer_position (str): Timer position - "top_middle", "between_sections", or "hidden"
                             If None, reads from config
        ai_assistance_enabled (bool): Whether to include AI Assistance button on back card
                               If None, reads from config
        is_reverse (bool): Whether to create a reverse template (Reverse->Question)

    Returns:
        dict: Dictionary with 'qfmt' and 'afmt' template strings
    """

    # Get timer position from config if not specified
    if timer_position is None:
        try:
            from .config_manager import get_timer_position

            timer_position = get_timer_position()
        except ImportError:
            timer_position = "between_sections"  # Default fallback

    # Get AI Assistance config from settings if not specified
    ai_assistance_config = None
    if ai_assistance_enabled is None:
        try:
            from .config_manager import get_ai_assistance_config

            ai_assistance_config = get_ai_assistance_config()
            ai_assistance_enabled = ai_assistance_config.get("enabled", False)
        except ImportError:
            ai_assistance_enabled = False  # Default fallback
            ai_assistance_config = None

    # The card is deliberately minimal: the front carries the timer and the question,
    # the back adds the answer plus whatever supporting content the row actually has.
    # The old CONTEXT / INFORMATION / TAGS sections were removed outright — their
    # headings rendered even when every field under them was empty, and the exam-prep
    # fields (BOARDS, LAST YEAR IN EXAM, CAREERS, OTHER TAGS, EXTRA FIELD 1-3, SANITY
    # CHECK) are still synced into the note, just not shown on the card.

    # Question and answer are rendered bare — no label, nothing to read past.
    cloze_prefix = "cloze:" if is_cloze else ""
    question_html = f"{{{{{cloze_prefix}{question}}}}}"
    answer_html = f"{{{{{cloze_prefix}{answer}}}}}"

    if is_reverse:
        # Reverse cards swap the two: REVERSE asks, QUESTION answers.
        question_html = f"{{{{{reverse}}}}}"
        answer_html = f"{{{{{question}}}}}"

    # Supporting content, each row conditional so an empty field leaves no trace.
    supporting_fields = [
        info_1,
        info_2,
        example_1,
        example_2,
        mnemonic,
        multimedia_1,
        multimedia_2,
    ]

    supporting_html = ""
    for field in supporting_fields:
        supporting_html += CARD_SHOW_HIDE_TEMPLATE.format(
            field_name=field.capitalize(), field_value=field
        )

    # Build reverse indicator if needed (CSS separate from HTML for positioning)
    reverse_indicator_css = ""
    reverse_indicator_html = ""
    if is_reverse:
        reverse_indicator_css = REVERSE_INDICATOR_CSS
        reverse_indicator_html = REVERSE_INDICATOR_HTML

    # Determine timer components based on position
    if timer_position == "hidden":
        timer_css = ""
        timer_html = ""
        timer_js_front = ""
        timer_js_back = ""
    elif timer_position == "top_middle":
        timer_css = TIMER_CSS_TOP_MIDDLE
        timer_html = TIMER_HTML
        timer_js_front = TIMER_JS_FRONT
        timer_js_back = TIMER_JS_BACK
    else:  # "between_sections" (default)
        timer_css = TIMER_CSS_BETWEEN_SECTIONS
        timer_html = TIMER_HTML
        timer_js_front = TIMER_JS_FRONT
        timer_js_back = TIMER_JS_BACK

    # Front: timer, then the question. Nothing else.
    qfmt = (
        reverse_indicator_css
        + timer_css
        + timer_html
        + reverse_indicator_html
        + question_html
        + timer_js_front
    )

    # Build AI Assistance components if enabled
    ai_assistance_components = ""
    if ai_assistance_enabled:
        # Check if mobile support is enabled
        if ai_assistance_config and ai_assistance_config.get("mobile_enabled", False):
            ai_help_js = generate_ai_assistance_js(
                mobile_enabled=True,
                service=ai_assistance_config.get("service", "gemini"),
                model=ai_assistance_config.get("model", ""),
                api_key=ai_assistance_config.get("api_key", ""),
                prompt_help=ai_assistance_config.get("prompt", ""),
                prompt_ask=ai_assistance_config.get("prompt_ask", ""),
                prompt_checker=ai_assistance_config.get("prompt_checker", ""),
            )
        else:
            ai_help_js = AI_HELP_JS_DESKTOP
        ai_assistance_components = AI_HELP_CSS + AI_HELP_BUTTON_HTML + ai_help_js

    # Back: the front again, then a rule, then the answer and its supporting rows.
    # A cloze card already reveals its answer inside the question text, so it does not
    # repeat the ANSWER field.
    back_answer = "" if is_cloze else answer_html + "<br><br>"

    afmt = (
        "{{FrontSide}}"
        + ANSWER_SEPARATOR_HTML
        + back_answer
        + supporting_html
        + ai_assistance_components
        + timer_js_back
    )

    return {"qfmt": qfmt, "afmt": afmt}


def create_model(
    col, model_name, is_cloze=False, url=None, debug_messages=None, is_reverse=False
):
    """
    Creates a new Anki note model.

    Args:
        col: Anki collection object
        model_name (str): Name for the new model
        is_cloze (bool): Whether to create a cloze model
        url (str, optional): Remote deck URL for automatic registration
        debug_messages (list, optional): List for debug
        is_reverse (bool): Whether to create a reverse model
        debug_messages (list, optional): List for debug

    Returns:
        object: The created Anki model
    """
    from .utils import register_note_type_for_deck

    model = col.models.new(model_name)
    if is_cloze:
        model["type"] = 1  # Set as cloze type

    # Add fields (excluding internal control fields like SYNC)
    for field in NOTE_FIELDS:
        template = col.models.new_field(field)
        col.models.add_field(model, template)

    # Add card template
    template = col.models.new_template("Cloze" if is_cloze else "Card 1")
    card_template = create_card_template(is_cloze, is_reverse=is_reverse)
    template["qfmt"] = card_template["qfmt"]
    template["afmt"] = card_template["afmt"]

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


def ensure_custom_models(col, url, debug_messages=None):
    """
    Ensures both models (standard and cloze) exist in Anki.
    Uses IDs stored in meta.json to find existing note types,
    instead of searching only by name.

    Args:
        col: Anki collection object
        url (str): Remote deck URL
        debug_messages (list, optional): List for debug

    Returns:
        dict: Dictionary containing 'standard', 'cloze', and 'reverse' models
    """
    from .config_manager import get_deck_note_type_ids
    from .config_manager import get_deck_remote_name
    from .utils import get_note_type_name
    from .utils import register_note_type_for_deck

    def add_debug_msg(message):
        if debug_messages:
            debug_messages.append(f"[ENSURE_MODELS] {message}")

    models = {}

    # Get remote deck name and existing note types
    remote_deck_name = get_deck_remote_name(url) or "RemoteDeck"
    existing_note_types = get_deck_note_type_ids(url) or {}

    add_debug_msg(f"Searching note types for remote_deck_name='{remote_deck_name}'")
    add_debug_msg(f"Existing note types: {len(existing_note_types)} found")

    # Helper function to find note type by pattern
    def find_existing_note_type(is_cloze=False, is_reverse=False):
        if is_reverse:
            target_type = "Reverse"
        elif is_cloze:
            target_type = "Cloze"
        else:
            target_type = "Basic"

        target_pattern = f" - {target_type}"

        # Search in existing note types
        for note_type_id_str, note_type_name in existing_note_types.items():
            if note_type_name.endswith(target_pattern):
                try:
                    note_type_id = int(note_type_id_str)
                    from anki.models import NotetypeId

                    model = col.models.get(NotetypeId(note_type_id))
                    if model:
                        add_debug_msg(
                            f"Found existing note type: ID {note_type_id} - '{note_type_name}'"
                        )
                        return model, note_type_name
                except (ValueError, TypeError):
                    continue
        return None, None

    # Standard model (Basic)
    expected_name = get_note_type_name(url, remote_deck_name, is_cloze=False)
    existing_model, existing_name = find_existing_note_type(is_cloze=False)

    if existing_model:
        # Use existing model and do NOT force new name if already registered
        current_registered_name = None
        for note_type_id_str, note_type_name in existing_note_types.items():
            try:
                if int(note_type_id_str) == existing_model["id"]:
                    current_registered_name = note_type_name
                    break
            except ValueError:
                continue

        if current_registered_name:
            # Already registered, use current config name
            add_debug_msg(
                f"Using existing (Basic) model ALREADY REGISTERED: '{existing_name}' with config name: '{current_registered_name}'"
            )
            models["standard"] = existing_model
        else:
            # Not registered, register with expected name
            register_note_type_for_deck(
                url, existing_model["id"], expected_name, debug_messages
            )
            models["standard"] = existing_model
            add_debug_msg(
                f"Existing (Basic) model registered: '{existing_name}' → expected: '{expected_name}'"
            )
    else:
        # Create new model only if it really doesn't exist
        add_debug_msg(f"Creating new (Basic) model: '{expected_name}'")
        model = create_model(
            col, expected_name, is_cloze=False, url=url, debug_messages=debug_messages
        )
        models["standard"] = model

    # Cloze model
    expected_cloze_name = get_note_type_name(url, remote_deck_name, is_cloze=True)
    existing_cloze_model, existing_cloze_name = find_existing_note_type(is_cloze=True)

    if existing_cloze_model:
        # Use existing model and do NOT force new name if already registered
        current_registered_cloze_name = None
        for note_type_id_str, note_type_name in existing_note_types.items():
            try:
                if int(note_type_id_str) == existing_cloze_model["id"]:
                    current_registered_cloze_name = note_type_name
                    break
            except ValueError:
                continue

        if current_registered_cloze_name:
            # Already registered, use current config name
            add_debug_msg(
                f"Using existing (Cloze) model ALREADY REGISTERED: '{existing_cloze_name}' with config name: '{current_registered_cloze_name}'"
            )
            models["cloze"] = existing_cloze_model
        else:
            # Not registered, register with expected name
            register_note_type_for_deck(
                url, existing_cloze_model["id"], expected_cloze_name, debug_messages
            )
            models["cloze"] = existing_cloze_model
            add_debug_msg(
                f"Existing (Cloze) model registered: '{existing_cloze_name}' → expected: '{expected_cloze_name}'"
            )
    else:
        # Create new model only if it really doesn't exist
        add_debug_msg(f"Creating new (Cloze) model: '{expected_cloze_name}'")
        cloze_model = create_model(
            col,
            expected_cloze_name,
            is_cloze=True,
            url=url,
            debug_messages=debug_messages,
        )
        models["cloze"] = cloze_model

    # Reverse model
    expected_reverse_name = get_note_type_name(
        url, remote_deck_name, is_cloze=False, is_reverse=True
    )
    existing_reverse_model, existing_reverse_name = find_existing_note_type(
        is_cloze=False, is_reverse=True
    )

    if existing_reverse_model:
        # Use existing model and do NOT force new name if already registered
        current_registered_reverse_name = None
        for note_type_id_str, note_type_name in existing_note_types.items():
            try:
                if int(note_type_id_str) == existing_reverse_model["id"]:
                    current_registered_reverse_name = note_type_name
                    break
            except ValueError:
                continue

        if current_registered_reverse_name:
            # Already registered, use current config name
            add_debug_msg(
                f"Using existing (Reverse) model ALREADY REGISTERED: '{existing_reverse_name}' with config name: '{current_registered_reverse_name}'"
            )
            models["reverse"] = existing_reverse_model
        else:
            # Not registered, register with expected name
            register_note_type_for_deck(
                url, existing_reverse_model["id"], expected_reverse_name, debug_messages
            )
            models["reverse"] = existing_reverse_model
            add_debug_msg(
                f"Existing (Reverse) model registered: '{existing_reverse_name}' → expected: '{expected_reverse_name}'"
            )
    else:
        # Create new model only if it really doesn't exist
        add_debug_msg(f"Creating new (Reverse) model: '{expected_reverse_name}'")
        # We use standard template structure (is_cloze=False) for Reverse notes
        # The fields are mapped differently in data_processor.py
        reverse_model = create_model(
            col,
            expected_reverse_name,
            is_cloze=False,
            url=url,
            debug_messages=debug_messages,
            is_reverse=True,
        )
        models["reverse"] = reverse_model

    return models


def update_existing_note_type_templates(col, debug_messages=None):
    """
    Updates templates of all existing Sheets2Anki note types
    to include ALL fields defined in NOTE_FIELDS and ensure templates are up to date.

    Args:
        col: Anki collection object
        debug_messages (list, optional): List for debug

    Returns:
        int: Number of updated note types
    """
    if debug_messages is None:
        debug_messages = []

    updated_count = 0

    # Search all note types that start with "Sheets2Anki"
    all_models = col.models.all()
    sheets2anki_models = [
        model for model in all_models if model.get("name", "").startswith("Sheets2Anki")
    ]

    debug_messages.append(
        f"[UPDATE_TEMPLATES] Found {len(sheets2anki_models)} Sheets2Anki note types"
    )

    for model in sheets2anki_models:
        try:
            model_name = model.get("name", "")
            is_cloze = model.get("type") == 1
            model_was_updated = False

            # 1. Check for missing fields
            # ----------------------------------------------------------------
            existing_field_names = []
            for field in model.get("flds", []):
                # Handle different field formats (dict or object)
                if hasattr(field, "get"):
                    fname = field.get("name", "")
                elif isinstance(field, dict):
                    fname = field.get("name", "")
                else:
                    fname = getattr(field, "name", "")
                existing_field_names.append(fname)

            # Verify every standard field
            for target_field in NOTE_FIELDS:
                if target_field not in existing_field_names:
                    debug_messages.append(
                        f"[UPDATE_TEMPLATES] Adding missing field '{target_field}' to {model_name}"
                    )
                    # Add missing field
                    field_template = col.models.new_field(target_field)
                    col.models.add_field(model, field_template)
                    model_was_updated = True

            # 2. Update card templates (HTML/CSS)
            # ----------------------------------------------------------------
            # We force update if we added fields OR if we want to ensure latest HTML structure
            # To be efficient, we generate the current standard template

            # Detect if this is a reverse note type by checking the name
            is_reverse = model_name.endswith(" - Reverse")

            # Generate template with correct parameters
            new_card_template = create_card_template(
                is_cloze=is_cloze, is_reverse=is_reverse
            )
            templates = model.get("tmpls", [])

            if templates:
                for i, template in enumerate(templates):
                    # Get current content
                    if hasattr(template, "get"):
                        current_qfmt = template.get("qfmt", "")
                        current_afmt = template.get("afmt", "")
                    elif isinstance(template, dict):
                        current_qfmt = template.get("qfmt", "")
                        current_afmt = template.get("afmt", "")
                    else:
                        current_qfmt = getattr(template, "qfmt", "")
                        current_afmt = getattr(template, "afmt", "")

                    # Check if update is needed (simple string comparison)
                    # This ensures any HTML change in code is propagated
                    needs_template_update = (
                        current_qfmt.strip() != new_card_template["qfmt"].strip()
                        or current_afmt.strip() != new_card_template["afmt"].strip()
                    )

                    if needs_template_update:
                        # Update template content
                        if hasattr(template, "__setitem__"):
                            template["qfmt"] = new_card_template["qfmt"]
                            template["afmt"] = new_card_template["afmt"]
                        elif isinstance(template, dict):
                            template["qfmt"] = new_card_template["qfmt"]
                            template["afmt"] = new_card_template["afmt"]
                        else:
                            template.qfmt = new_card_template["qfmt"]
                            template.afmt = new_card_template["afmt"]

                        model_was_updated = True
                        template_type = (
                            "Reverse"
                            if is_reverse
                            else ("Cloze" if is_cloze else "Basic")
                        )
                        debug_messages.append(
                            f"[UPDATE_TEMPLATES] Template {i+1} ({template_type}) updated for {model_name}"
                        )

            # 3. Save changes if anything was modified
            # ----------------------------------------------------------------
            if model_was_updated:
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
                f"[UPDATE_TEMPLATES] ❌ Error processing {model.get('name', 'unknown')}: {e}"
            )
            import traceback

            debug_messages.append(traceback.format_exc())

    debug_messages.append(
        f"[UPDATE_TEMPLATES] 🎯 Total note types updated: {updated_count}"
    )
    return updated_count
