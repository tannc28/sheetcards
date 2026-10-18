"""
Main synchronization functions for the SheetCards addon.

This module contains the core functions for synchronizing
decks with remote sources, using the new configuration system.
It also includes classes for statistics management and finalization.
"""

import traceback
from dataclasses import dataclass
from dataclasses import field
from typing import Any

from .compat import QDialog
from .compat import QLabel
from .compat import QProgressBar
from .compat import Qt
from .compat import QTextEdit
from .compat import QueryOp
from .compat import QVBoxLayout
from .compat import mw
from .compat import safe_exec_dialog
from .compat import tooltip
from .config_manager import get_remote_decks
from .config_manager import save_remote_decks
from .config_manager import sync_note_type_names_robustly
from .config_manager import update_note_type_names_in_meta
from .data_processor import create_or_update_notes
from .data_processor import getRemoteDeck
from .errors import user_message
from .name_consistency_manager import NameConsistencyManager
from .styled_messages import StyledMessageBox
from .sync_report import _generate_changes_list_html  # noqa: F401
from .sync_report import _generate_details_list_html  # noqa: F401

# --- Re-exported from sync_report (split out of this file) ---
from .sync_report import _generate_metrics_table_html  # noqa: F401
from .sync_report import generate_deck_detailed_metrics  # noqa: F401
from .sync_report import generate_detailed_html_view  # noqa: F401
from .sync_report import generate_errors_view  # noqa: F401
from .sync_report import generate_simplified_view  # noqa: F401
from .templates_and_definitions import update_existing_note_type_templates
from .utils import SyncError
from .utils import add_debug_message
from .utils import capture_deck_note_type_ids
from .utils import clear_debug_messages
from .utils import remove_empty_subdecks

# ========================================================================================
# SYNC STATISTICS CLASSES (consolidated from sync_stats.py)
# ========================================================================================


@dataclass
class SyncStats:
    """Statistics of a synchronization."""

    created: int = 0
    updated: int = 0
    deleted: int = 0
    ignored: int = 0
    errors: int = 0
    unchanged: int = 0
    skipped: int = 0

    # Detailed metrics of the remote deck - REFACTORED
    # 1. Total table lines (regardless of content)
    remote_total_table_lines: int = 0

    # 2. Total lines with valid notes (ID filled)
    remote_valid_note_lines: int = 0

    # 3. Total invalid lines (empty ID)
    remote_invalid_note_lines: int = 0

    # 10. Total ghost rows (ignored)
    remote_ignored_ghost_rows: int = 0

    # 4. Total lines marked for sync (SYNC = true)
    remote_sync_marked_lines: int = 0

    # 5. Potential total notes to be created in Anki
    remote_total_potential_anki_notes: int = 0

    error_details: list[str] = field(default_factory=list)
    # Fields for structured details
    update_details: list[dict[str, Any]] = field(default_factory=list)
    creation_details: list[dict[str, Any]] = field(default_factory=list)
    deletion_details: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, error_msg: str) -> None:
        """Adds an error to the statistics."""
        self.errors += 1
        self.error_details.append(error_msg)

    def add_update_detail_structured(self, detail: dict[str, Any]) -> None:
        """Adds a structured update detail."""
        self.update_details.append(detail)

    def add_creation_detail(self, detail: dict[str, Any]) -> None:
        """Adds a creation detail."""
        self.creation_details.append(detail)

    def add_deletion_detail(self, detail: dict[str, Any]) -> None:
        """Adds a deletion detail."""
        self.deletion_details.append(detail)

    def merge(self, other: "SyncStats") -> None:
        """Merge with other statistics."""
        self.created += other.created
        self.updated += other.updated
        self.deleted += other.deleted
        self.ignored += other.ignored
        self.errors += other.errors
        self.unchanged += other.unchanged
        self.skipped += other.skipped

        # Aggregate metrics from the remote deck - REFACTORED
        self.remote_total_table_lines += other.remote_total_table_lines
        self.remote_valid_note_lines += other.remote_valid_note_lines
        self.remote_invalid_note_lines += other.remote_invalid_note_lines
        self.remote_ignored_ghost_rows += other.remote_ignored_ghost_rows
        self.remote_sync_marked_lines += other.remote_sync_marked_lines
        self.remote_total_potential_anki_notes += (
            other.remote_total_potential_anki_notes
        )

        self.error_details.extend(other.error_details)
        self.update_details.extend(other.update_details)
        self.creation_details.extend(other.creation_details)
        self.deletion_details.extend(other.deletion_details)
        self.warnings.extend(other.warnings)

    def get_total_operations(self) -> int:
        """Returns the total number of operations performed."""
        return self.created + self.updated + self.deleted + self.ignored

    def has_changes(self) -> bool:
        """Checks if there were changes."""
        return self.created > 0 or self.updated > 0 or self.deleted > 0

    def has_errors(self) -> bool:
        """Checks if there were errors."""
        return self.errors > 0


@dataclass
class DeckSyncResult:
    """Result of specific deck synchronization."""

    deck_name: str
    deck_key: str
    deck_url: str
    success: bool
    stats: SyncStats
    was_new_deck: bool = False  # If the deck was new (never synced before)
    error_message: str | None = None

    def __post_init__(self):
        """Initialization after creation."""
        if self.stats is None:
            self.stats = SyncStats()


class SyncStatsManager:
    """Sync statistics manager."""

    def __init__(self):
        self.total_stats = SyncStats()
        self.deck_results: list[DeckSyncResult] = []

    def add_deck_result(self, result: DeckSyncResult) -> None:
        """Adds synchronization result of a deck."""
        self.deck_results.append(result)
        self.total_stats.merge(result.stats)

    def create_deck_result(
        self, deck_name: str, deck_key: str, deck_url: str = ""
    ) -> DeckSyncResult:
        """Creates a new deck result."""
        return DeckSyncResult(
            deck_name=deck_name,
            deck_key=deck_key,
            deck_url=deck_url,
            success=False,
            stats=SyncStats(),
        )

    def get_successful_decks(self) -> list[DeckSyncResult]:
        """Returns successfully synchronized decks."""
        return [r for r in self.deck_results if r.success]

    def get_failed_decks(self) -> list[DeckSyncResult]:
        """Returns decks that failed synchronization."""
        return [r for r in self.deck_results if not r.success]

    def get_summary(self) -> dict[str, Any]:
        """Returns a summary of statistics."""
        successful = len(self.get_successful_decks())
        failed = len(self.get_failed_decks())

        return {
            "total_decks": len(self.deck_results),
            "successful_decks": successful,
            "failed_decks": failed,
            "total_stats": self.total_stats,  # Return SyncStats object directly
            "has_changes": self.total_stats.has_changes(),
            "has_errors": self.total_stats.has_errors(),
        }

    def reset(self) -> None:
        """Resets all statistics."""
        self.total_stats = SyncStats()
        self.deck_results.clear()


# ========================================================================================
# SYNC FINALIZATION FUNCTIONS (consolidated from sync_finalization.py)
# ========================================================================================


def _finalize_sync_cleanup(progress):
    """
    Performs final cleanup operations for synchronization.

    Args:
        progress: LogProgressDialog instance to update status

    Returns:
        int: Number of removed subdecks
    """
    progress.appendMessage("Removing empty subdecks…")
    mw.app.processEvents()

    from .config_manager import get_remote_decks
    from .utils import apply_automatic_deck_options_system

    # Remove empty subdecks
    remote_decks = get_remote_decks()
    removed_subdecks = remove_empty_subdecks(remote_decks)

    progress.appendMessage("Applying deck options…")
    mw.app.processEvents()

    options_result = apply_automatic_deck_options_system()
    add_debug_message(
        f"apply_automatic_deck_options_system() returned: {options_result}", "SYNC"
    )

    add_debug_message("Synchronization cleanup finished", "SYSTEM")

    # Update Anki interface to show changes
    progress.appendMessage("Refreshing Anki…")
    mw.app.processEvents()

    ensure_interface_refresh()

    return removed_subdecks


def _show_sync_summary_new(
    sync_errors,
    total_stats,
    decks_synced,
    total_decks,
    removed_subdecks=0,
    ankiweb_result=None,
    on_close_callback=None,
    deck_results=None,
    new_deck_mode=False,
):
    """
    Shows synchronization summary using scrolled interface.

    Args:
        on_close_callback (callable, optional): Function to be called when the dialogue is closed
        deck_results (list, optional): List of DeckSyncResult for per-deck visualization
    """

    summary = []

    sync_errors = sync_errors or []
    total_errors = total_stats.errors + len(sync_errors)
    summary.append(
        f"Finished with problems: {decks_synced} of {total_decks} decks synced."
        if total_errors
        else f"Finished: {decks_synced} of {total_decks} decks synced."
    )
    for count, word in (
        (total_stats.created, "notes created"),
        (total_stats.updated, "notes updated"),
        (total_stats.deleted, "notes deleted"),
        (total_stats.ignored, "notes ignored"),
        (removed_subdecks, "empty subdecks removed"),
        (total_errors, "errors"),
        (len(total_stats.warnings), "warnings"),
    ):
        if count:
            summary.append(f"{count} {word}")

    # Always use scrolled interface
    _show_sync_summary_with_scroll(
        summary,
        total_stats,
        removed_subdecks,
        sync_errors,
        ankiweb_result,
        on_close_callback,
        deck_results,
    )


def _show_sync_summary_with_scroll(
    base_summary,
    total_stats,
    removed_subdecks=0,
    sync_errors=None,
    ankiweb_result=None,
    on_close_callback=None,
    deck_results=None,
):
    """
    Shows synchronization summary with a modern, user-friendly scrolled interface.

    Args:
        on_close_callback (callable, optional): Function to be called when the dialogue is closed
        deck_results (list, optional): List of DeckSyncResult for per-deck visualization
    """
    from .compat import ButtonBox_Close
    from .compat import QButtonGroup
    from .compat import QDialogButtonBox
    from .compat import QHBoxLayout
    from .compat import QRadioButton
    from .compat import QWidget
    from .theme import ICON_SIZE
    from .theme import MARGIN
    from .theme import SPACE_ELEMENT
    from .theme import SPACE_SECTION
    from .theme import get_colors
    from .theme import icon

    # Create custom dialog
    dialog = QDialog()
    dialog.setWindowTitle("Synchronization Summary")
    dialog.setMinimumSize(850, 650)
    dialog.resize(950, 750)

    # Connect callback to closing if provided
    if on_close_callback and callable(on_close_callback):
        dialog.finished.connect(lambda *_: on_close_callback())

    # Anki's palette, through the add-on's one gateway to it. This function used to
    # carry two dicts of fifteen hand-picked hex values and pick between them by
    # measuring the window's own background lightness — a heuristic that misreads a
    # custom theme, which is why `is_dark_mode()` exists.
    colors = get_colors()

    # Determine overall status
    has_errors = (sync_errors and len(sync_errors) > 0) or total_stats.errors > 0
    has_warnings = bool(total_stats.warnings)

    main_layout = QVBoxLayout(dialog)
    main_layout.setSpacing(SPACE_SECTION)
    main_layout.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)

    # One line saying how it went, with the icon that says the same thing at a
    # glance. It was a banner: a tinted panel with a two-pixel coloured border and
    # a 28pt emoji in it, over a window whose title already said Summary.
    head_row = QHBoxLayout()
    head_row.setSpacing(SPACE_ELEMENT)
    if has_errors:
        shape, colour, status_text = (
            "warning",
            "error",
            "Finished, but some decks or rows did not sync",
        )
    elif has_warnings:
        shape, colour, status_text = (
            "warning",
            "accent_warning",
            "Finished, with warnings to read",
        )
    else:
        shape, colour, status_text = ("success", "accent_success", "Finished")
    status_icon = QLabel()
    status_icon.setPixmap(icon(shape, colour).pixmap(ICON_SIZE, ICON_SIZE))
    status_icon.setFixedWidth(ICON_SIZE)
    status_label = QLabel(f"<b>{status_text}</b>")
    # Anki's caution orange is an icon colour, too faint to read as text on the
    # light theme, so a warning is said in the text colour beside an orange icon.
    text_colour = "text" if colour == "accent_warning" else colour
    status_label.setStyleSheet(f"color: {colors[text_colour]};")
    head_row.addWidget(status_icon)
    head_row.addWidget(status_label)
    head_row.addStretch()
    main_layout.addLayout(head_row)

    # The numbers, as a row of plain labels. They were five tinted cards with a
    # coloured left border and an emoji over an 18pt figure — a dashboard on top of
    # a window whose whole job is to be read once and closed.
    stats_layout = QHBoxLayout()
    stats_layout.setSpacing(SPACE_SECTION)

    def create_stat_card(value, label):
        """One figure and its word, stacked."""
        card = QWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        value_label = QLabel(f"<b>{value}</b>")
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(value_label)

        label_lbl = QLabel(label)
        label_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label_lbl.setStyleSheet(f"color: {colors['text_secondary']};")
        card_layout.addWidget(label_lbl)
        return card

    # Calculate total decks info
    total_decks = len(deck_results) if deck_results else 0
    successful_decks = (
        len([r for r in deck_results if r.success]) if deck_results else 0
    )

    for value, label in (
        (total_stats.created, "Created"),
        (total_stats.updated, "Updated"),
        (total_stats.deleted, "Deleted"),
        (total_stats.skipped, "Skipped"),
        (total_stats.errors + len(sync_errors or []), "Errors"),
        (len(total_stats.warnings), "Warnings"),
    ):
        stats_layout.addWidget(create_stat_card(value, label))
    if total_decks > 0:
        stats_layout.addWidget(
            create_stat_card(f"{successful_decks}/{total_decks}", "Decks")
        )

    main_layout.addLayout(stats_layout)

    # ═══════════════════════════════════════════════════════════════════════════
    # Three views of the same run. They were radio buttons styled to look like
    # filled tabs, with the indicator hidden — which is a radio button pretending
    # to be a thing Qt already has.
    view_row = QHBoxLayout()
    view_row.setSpacing(SPACE_SECTION)
    simplified_radio = QRadioButton("Summary")
    detailed_radio = QRadioButton("Full details")
    errors_radio = QRadioButton("Errors only")
    simplified_radio.setChecked(True)

    radio_group = QButtonGroup(dialog)
    for button in (simplified_radio, detailed_radio, errors_radio):
        radio_group.addButton(button)
        view_row.addWidget(button)
    view_row.addStretch()
    main_layout.addLayout(view_row)

    details_text = QTextEdit()
    details_text.setReadOnly(True)

    def update_details_view():
        """Updates details view based on radiobutton selection."""
        details_content = ""

        if simplified_radio.isChecked():
            details_content = generate_simplified_view(
                total_stats, sync_errors, deck_results
            )
        elif detailed_radio.isChecked():
            details_content = generate_detailed_html_view(
                total_stats, sync_errors, deck_results
            )
        else:
            details_content = generate_errors_view(
                total_stats, sync_errors, deck_results
            )

        # Inject CSS and set HTML
        # Using the colors dictionary defined in the outer scope

        css_content = f"""
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: {colors['text']}; background-color: {colors['card_bg']}; margin: 0; padding: 10px; }}
            h2 {{ color: {colors['text']}; border-bottom: 2px solid {colors['border']}; padding-bottom: 5px; margin-top: 20px; font-size: 1.2em; }}
            h3 {{ color: {colors['text_secondary']}; margin-top: 15px; margin-bottom: 8px; font-size: 1.1em; }}
            h4 {{ color: {colors['text']}; margin-top: 10px; margin-bottom: 5px; font-size: 1.0em; font-weight: 600; }}
            
            .metrics-container {{ display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 20px; }}
            .metrics-table {{ border-collapse: collapse; width: 100%; max-width: 600px; }}
            .metric-row td {{ padding: 6px 8px; border-bottom: 1px solid {colors['border']}; }}
            .metric-row:last-child td {{ border-bottom: none; }}
            .zero-value {{ opacity: 0.5; }}
            
            .label-col {{ font-weight: 500; }}
            .value-col {{ text-align: right; font-family: monospace; font-weight: bold; }}
            
            .stat-value {{ padding: 2px 6px; border-radius: 4px; }}
            .success {{ color: {colors['accent_success']}; }}
            .success-bold {{  background-color: {colors['accent_success']}; padding: 2px 8px; color: white !important; font-weight: bold; display: inline-block; }}
            .error {{ color: {colors['error']}; }}
            .error-bold {{ background-color: {colors['error']}; padding: 2px 8px; color: white !important; font-weight: bold; display: inline-block; }}
            .warning {{ color: {colors['text']}; font-weight: 600; }}
            .warning-bold {{ background-color: {colors['accent_warning']}; padding: 2px 8px; color: black !important; font-weight: bold; display: inline-block; }}
            .info {{ color: {colors['accent_info']}; }}
            .muted {{ color: {colors['text_secondary']}; }}
            
            .separator-row td {{ padding: 10px 0; border: none; }}
            .separator-row hr {{ border: 0; height: 1px; background: {colors['border']}; opacity: 0.5; }}
            .info-row td {{ border-bottom: none; }}

            .details-block {{ margin-top: 20px; }}
            .details-block ul {{ list-style-type: none; padding-left: 0; }}
            .details-block li {{ padding: 4px 0; border-bottom: 1px solid {colors['border']}; }}
            
            .changes-block {{ margin-top: 20px; }}
            .changes-table {{ width: 100%; border-collapse: collapse; }}
            .changes-table td {{ padding: 8px; vertical-align: top; border-bottom: 1px solid {colors['border']}; }}
            .index-col {{ width: 30px; color: {colors['text_secondary']}; }}
            .note-col {{ }}
            .note-extract {{ display: block; margin-top: 4px; font-style: italic; color: {colors['text_secondary']}; font-size: 0.9em; }}
            .changes-list {{ margin-top: 5px; padding-left: 20px; margin-bottom: 0; color: {colors['text_secondary']}; font-size: 0.9em; }}
            
            .section-header {{ background: {colors['bg']}; padding: 10px; border-radius: 6px; margin-bottom: 15px; border-left: 5px solid {colors['accent_info']}; }}
            .section-header h2 {{ margin: 0; border: none; }}
            
            .deck-block {{ margin-bottom: 40px; border: 1px solid {colors['border']}; border-bottom: 5px solid {colors['border']}; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .deck-header {{ padding: 10px 15px; background: {colors['background_secondary']}; border-bottom: 1px solid {colors['border']}; font-weight: bold; font-size: 1.1em; display: flex; align-items: center; color: {colors['text']}; }}
            .tag-new {{ background: {colors['accent_success']}; color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.7em; margin-left: 10px; vertical-align: middle; }}
            .success-deck {{ border-left: 4px solid {colors['accent_success']}; }}
            .fail-deck {{ border-left: 4px solid {colors['error']}; }}
            
            .error-banner {{ background: {colors['error']}; color: white; padding: 10px; margin: 10px; border-radius: 4px; }}
            .deck-metrics-subsection {{ padding: 15px; }}
            
            .deck-separator-visual {{ text-align: center; margin: 40px 0; color: {colors['border']}; font-size: 24px; letter-spacing: 10px; }}
            .separator-dot {{ color: {colors['border']}; opacity: 0.6; }}
            
            .no-changes-info {{ text-align: center; padding: 40px; color: {colors['text_secondary']}; opacity: 0.8; }}
            .no-changes-info ul {{ display: inline-block; text-align: left; margin-top: 15px; }}
            .no-changes-info h3 {{ color: {colors['text']}; }}
        </style>
        """

        full_html = css_content + details_content
        details_text.setHtml(full_html)

    # Connect radiobutton changes to view update
    simplified_radio.toggled.connect(update_details_view)
    detailed_radio.toggled.connect(update_details_view)
    errors_radio.toggled.connect(update_details_view)

    # Set initial content
    update_details_view()

    main_layout.addWidget(details_text, 1)

    button_box = QDialogButtonBox(ButtonBox_Close)
    button_box.rejected.connect(dialog.accept)
    main_layout.addWidget(button_box)

    safe_exec_dialog(dialog)


# ========================================================================================
# INTERFACE UPDATE FUNCTIONS (consolidated from interface_updater.py)
# ========================================================================================


def refresh_deck_list():
    """
    Specifically updates the deck list on the main screen.
    """
    if not mw or not hasattr(mw, "deckBrowser"):
        return

    try:
        add_debug_message("📂 Updating deck list", "INTERFACE_UPDATE")
        mw.deckBrowser.refresh()
    except Exception as e:
        add_debug_message(f"❌ Error updating deck list: {e}", "INTERFACE_UPDATE")


def refresh_counts():
    """
    Updates card counters across all interfaces.
    """
    if not mw:
        return

    try:
        add_debug_message("🔢 Updating card counters", "INTERFACE_UPDATE")

        # Force recalculation of counts in collection
        if mw.col:
            mw.col.sched.reset()

        # Update deck browser
        if hasattr(mw, "deckBrowser") and mw.deckBrowser:
            mw.deckBrowser.refresh()

        # Update reviewer if active
        if hasattr(mw, "reviewer") and mw.reviewer and mw.state == "review":
            if hasattr(mw.reviewer, "_updateCounts"):
                mw.reviewer._updateCounts()

    except Exception as e:
        add_debug_message(f"❌ Error updating counters: {e}", "INTERFACE_UPDATE")


def ensure_interface_refresh():
    """
    Ensures the interface is updated, using multiple strategies.

    This function uses different methods to ensure the interface
    is updated regardless of Anki's current state.
    """
    if not mw:
        return

    try:
        add_debug_message("🎯 Running full interface update", "INTERFACE_UPDATE")

        # Method 1: Collection reset (most complete)
        if mw.col:
            mw.col.reset()

        # Method 2: Main interface reset
        if hasattr(mw, "reset"):
            mw.reset()

        # Method 3: Component-specific update
        refresh_deck_list()
        refresh_counts()

        add_debug_message("✅ Full interface update completed", "INTERFACE_UPDATE")

    except Exception as e:
        add_debug_message(f"❌ Error in full update: {e}", "INTERFACE_UPDATE")


# ========================================================================================
# MAIN SYNCHRONIZATION FUNCTIONS
# ========================================================================================


def _is_anki_ready():
    """Checks if Anki is ready for operations."""
    return mw and hasattr(mw, "col") and mw.col


def _is_anki_decks_ready():
    """Checks if Anki is ready for deck operations."""
    return _is_anki_ready() and hasattr(mw.col, "decks")


def syncDecks(selected_deck_names=None, selected_deck_urls=None, new_deck_mode=False):
    """
    Synchronizes remote decks with their sources.

    The work is split by thread, the way Anki asks add-ons to split it
    (https://docs.ankiweb.net/addons/background-ops): each deck's sheet is
    downloaded and parsed in a ``QueryOp`` on a background thread, and what it
    turned into is written to the collection on the main thread when that
    finishes. Downloads are the slow part — up to the 30 s timeout on a bad
    connection — and they used to run on the main thread, which is what froze
    Anki for the length of a sync.

    Returns as soon as the run has started; :class:`_SyncRun` carries it to the
    end and decides what to show then.

    Args:
        selected_deck_names: List of deck names to synchronize.
                           If None, synchronizes all decks.
        selected_deck_urls: List of deck URLs to synchronize.
                          If provided, takes precedence over selected_deck_names.
        new_deck_mode: If True, indicates this synchronization is for a newly added deck.
    """
    global _ACTIVE_RUN

    # Check if mw.col is available
    if not _is_anki_ready():
        StyledMessageBox.warning(
            None,
            "Anki Not Ready",
            "Anki is not ready. Please try again in a few moments.",
        )
        return

    # The main window stays usable while a sync downloads, so the menu that
    # starts one is reachable again before the first has finished.
    if _ACTIVE_RUN is not None:
        tooltip("A sync is already running.", parent=mw)
        return

    col = mw.col

    # Several decks can live in one Google Sheets file, and each of them needs the
    # whole file. Downloading it once per run is the difference between one
    # request and one per deck; keeping it any longer than the run would mean
    # syncing a sheet as it was hours ago. The page titles deck names come from
    # are remembered for the same span, for the same reasons.
    from .data_processor import clear_workbook_cache
    from .deck_manager import clear_remote_name_cache

    clear_workbook_cache()
    clear_remote_name_cache()

    remote_decks = get_remote_decks()

    # Clear previous debug messages and initialize log file
    from .utils import initialize_debug_log

    clear_debug_messages()
    initialize_debug_log()

    # Determine which decks to synchronize (needed to setup progress dialog)
    deck_keys = _get_deck_keys_to_sync(
        remote_decks, selected_deck_names, selected_deck_urls
    )
    total_decks = len(deck_keys)

    # Check if there are decks to synchronize
    if total_decks == 0:
        _show_no_decks_message(selected_deck_names)
        return

    progress = _setup_progress_dialog(total_decks)
    status_msgs = []
    sync_errors = []

    # Update existing note type templates before synchronization
    status_msgs.append("Updating card templates…")
    _update_progress_text(progress, status_msgs)

    try:
        add_debug_message("Updating existing note type templates...", "SYNC")
        updated_count = update_existing_note_type_templates(col, [])
        add_debug_message(f"{updated_count} note types successfully updated", "SYNC")
        status_msgs.append(f"Card templates updated ({updated_count} note types).")
        _update_progress_text(progress, status_msgs)

    except Exception as e:
        add_debug_message(
            f"Error updating templates: {e}\n{traceback.format_exc()}", "SYNC"
        )
        status_msgs.append("Card templates could not be updated; syncing anyway.")
        sync_errors.append(
            "Card templates could not be updated. Cards keep their previous "
            "layout until the next sync."
        )
        _update_progress_text(progress, status_msgs)

    add_debug_message(f"Sync started - total decks: {total_decks}", "SYNC")

    run = _SyncRun(
        deck_keys=deck_keys,
        remote_decks=remote_decks,
        progress=progress,
        status_msgs=status_msgs,
        sync_errors=sync_errors,
        new_deck_mode=new_deck_mode,
    )
    _ACTIVE_RUN = run
    run.start()


# The run in progress, if any. Held here so the run is not garbage-collected
# between its background steps, and so a second sync cannot start on top of it.
_ACTIVE_RUN = None


def _fetch_deck(remote_deck_url, media_dir=None):
    """Downloads and parses one deck's sheet. Runs on a background thread.

    Touches nothing but the network, the add-on's own files and the pure
    layer: no ``mw.col``, no Qt. The deck's page title is read here too, so the
    renaming that follows on the main thread finds it remembered rather than
    asking Google again with the window frozen.

    The deck's own URL, not an export URL built from it: converting to
    "/export?format=tsv" drops the "#sheet=" fragment, and a deck with no sheet
    named falls back to downloading the file's *first* sheet. Every deck of one
    file then synced the same sheet — the second deck ending up with the first
    one's columns, note type and rows. getRemoteDeck converts the URL itself.

    The pictures and recordings its media columns point at are fetched here too
    (``media_fetch``), so a card can be reviewed offline; ``media_dir`` is the
    collection's media folder, read on the main thread, so a file already there
    is not fetched again. Nothing about media can fail the deck.
    """
    from .deck_manager import DeckNameManager
    from .deck_manager import remember_declared_name

    remoteDeck = getRemoteDeck(remote_deck_url)
    # Before the title: a sheet that names itself (name=) is called that, here
    # as in Sheet to Anki, and needs no page fetched to find out.
    remember_declared_name(remote_deck_url, getattr(remoteDeck, "sheet_config", None))
    DeckNameManager.extract_remote_name_from_url(remote_deck_url)
    try:
        from .media_fetch import fetch_deck_media

        remoteDeck.fetched_media = fetch_deck_media(remoteDeck, media_dir)
    except Exception as e:
        add_debug_message(f"Media fetch skipped: {e}", "MEDIA")
        remoteDeck.fetched_media = None
    return remoteDeck


class _SyncRun:
    """One sync, carried from deck to deck across background downloads.

    For each deck: download in a :class:`QueryOp` (background), then write in
    its success callback (main thread), then on to the next deck. Cancel is
    honoured between decks — a deck half-written would be worse than a deck
    not started — and the window says so while the current one finishes.

    Why the writes are not a ``CollectionOp``: a deck's write is not one call
    but the whole of :func:`_sync_single_deck` — renaming decks, provisioning
    note types (adding a field is a schema change, which empties Anki's undo
    queue anyway), adding/updating/removing notes, and saving ``meta.json``
    between those steps. That code reaches for ``mw.col`` and the add-on's own
    files throughout, and an undo step that reverted the notes but not
    ``meta.json`` would leave the two disagreeing. The sheet is what a sync is
    recovered from, not Undo, so the writes run on the main thread where all of
    that is safe, and only the slow part — the network — is moved off it.
    """

    def __init__(
        self,
        deck_keys,
        remote_decks,
        progress,
        status_msgs,
        sync_errors,
        new_deck_mode=False,
    ):
        self.deck_keys = list(deck_keys)
        self.remote_decks = remote_decks
        self.progress = progress
        self.status_msgs = status_msgs
        self.sync_errors = sync_errors
        self.new_deck_mode = new_deck_mode
        self.stats_manager = SyncStatsManager()
        self.index = 0
        self.cancelled = False
        self.finished = False
        progress.on_cancel = self.cancel

    # -- driving -------------------------------------------------------------

    def start(self):
        self._next()

    def cancel(self):
        """Stop after the deck in hand. Called by the window's Cancel."""
        if self.finished or self.cancelled:
            return
        self.cancelled = True
        add_debug_message("Sync cancelled by the user", "SYNC")
        self.progress.setTitle("Stopping after this deck…")
        self.progress.setCancelEnabled(False)

    def _deck_label(self, deck_key):
        info = self.remote_decks.get(deck_key, {})
        return info.get("local_deck_name") or info.get("remote_deck_name") or "Deck"

    def _next(self):
        if self.cancelled or self.index >= len(self.deck_keys):
            self._finish()
            return

        deck_key = self.deck_keys[self.index]
        try:
            url = self.remote_decks[deck_key].get("remote_deck_url", "")
            label = self._deck_label(deck_key)
            self.progress.setTitle(
                f"Downloading {label} ({self.index + 1} of {len(self.deck_keys)})…"
            )
            self.status_msgs.append(f"{label}: downloading…")
            _update_progress_text(self.progress, self.status_msgs)

            # Read here, on the main thread: the background step must not touch
            # the collection.
            try:
                media_dir = mw.col.media.dir()
            except Exception:
                media_dir = None
            QueryOp(
                parent=self.progress,
                op=lambda _col: _fetch_deck(url, media_dir),
                success=self._on_fetched,
            ).failure(self._on_fetch_failed).without_collection().run_in_background()
        except Exception as e:
            # Nothing is waiting on a background step now, so a failure here
            # would otherwise leave the window up and every later sync refused
            # as "already running".
            self._record_failure(deck_key, e)
            self._advance()

    def _advance(self):
        self.index += 1
        self.progress.setValue(self.index * 3)
        self._next()

    # -- one deck, back on the main thread ------------------------------------

    def _on_fetched(self, remote_deck):
        deck_key = self.deck_keys[self.index]
        try:
            self._write_deck(deck_key, remote_deck)
        except Exception as e:
            self._record_failure(deck_key, e)
        self._advance()

    def _on_fetch_failed(self, error):
        self._record_failure(self.deck_keys[self.index], error)
        self._advance()

    def _write_deck(self, deck_key, remote_deck):
        remote_decks = self.remote_decks
        self.progress.setTitle(f"Saving {self._deck_label(deck_key)}…")
        _, _, current_stats = _sync_single_deck(
            remote_decks,
            deck_key,
            self.progress,
            self.status_msgs,
            self.index * 3,
            debug_messages=[],
            remote_deck=remote_deck,
        )

        deck_name = remote_decks[deck_key].get("local_deck_name", "Unknown")
        deck_url = remote_decks[deck_key].get("remote_deck_url", "")

        # Check if the deck was new and update sync status
        from .config_manager import update_deck_sync_status

        was_new_deck = update_deck_sync_status(deck_url, success=True)

        # Errors captured row by row, which did not stop the deck.
        has_errors = current_stats.has_errors()
        self.stats_manager.add_deck_result(
            DeckSyncResult(
                deck_name=deck_name,
                deck_key=deck_key,
                deck_url=deck_url,
                success=not has_errors,
                stats=current_stats,
                was_new_deck=was_new_deck,
                error_message="Completed with errors" if has_errors else None,
            )
        )

        if has_errors:
            add_debug_message(f"Deck completed with errors: {deck_key}", "SYNC")
            n = current_stats.errors
            self.status_msgs.append(
                f"{deck_name}: finished with {n} error{'s' if n != 1 else ''}."
            )
            self.sync_errors.append(
                f"{deck_name}: {n} row{'s' if n != 1 else ''} could not be synced."
            )
        else:
            add_debug_message(f"Deck completed: {deck_key}", "SYNC")
            self.status_msgs.append(f"{deck_name}: done.")
        _update_progress_text(self.progress, self.status_msgs)

    def _record_failure(self, deck_key, error):
        """A deck that did not sync at all: say why, plainly, and log the rest."""
        deck_name = _resolve_deck_name_for_error(deck_key, self.remote_decks)
        sentence = user_message(error)
        add_debug_message(
            f"Deck failed: {deck_key} ({deck_name}) — "
            f"{getattr(error, 'detail', None) or repr(error)}\n"
            + "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            ),
            "SYNC",
        )

        # Recorded once, on the deck's own result: it reaches the summary's
        # error list through the merged totals, and adding it to sync_errors
        # as well listed every failed deck twice and counted it as two errors.
        line = f"{deck_name}: {sentence}"
        self.status_msgs.append(line)
        _update_progress_text(self.progress, self.status_msgs)

        failed = DeckSyncResult(
            deck_name=deck_name,
            deck_key=deck_key,
            deck_url=self.remote_decks.get(deck_key, {}).get("remote_deck_url", ""),
            success=False,
            stats=SyncStats(),
            error_message=sentence,
        )
        failed.stats.add_error(line)
        self.stats_manager.add_deck_result(failed)

    # -- the end ---------------------------------------------------------------

    def _finish(self):
        global _ACTIVE_RUN

        self.finished = True
        try:
            self.progress.setCancelEnabled(False)
            self.progress.setTitle("Finishing…")
            removed_subdecks = _finalize_sync_cleanup(self.progress)
            self.progress.setValue(self.progress.maximum())
            self.progress.close_when_done()

            summary = self.stats_manager.get_summary()
            total_stats = summary["total_stats"]
            deck_results = self.stats_manager.deck_results
            successful = len(self.stats_manager.get_successful_decks())

            # The AnkiWeb hand-off is what the user asked for after a sync, so
            # it follows either way — straight away after a clean run, after
            # the summary is closed otherwise. Not after Cancel: someone who
            # stopped a sync did not ask for it to be pushed anywhere.
            hand_off = None if self.cancelled else _hand_off_to_ankiweb

            if _run_was_clean(self.sync_errors, total_stats, deck_results):
                tooltip(
                    clean_run_message(
                        successful,
                        len(self.deck_keys),
                        total_stats,
                        cancelled=self.cancelled,
                    ),
                    period=4000,
                    parent=mw,
                )
                if hand_off:
                    hand_off()
            else:
                _show_sync_summary_new(
                    self.sync_errors,
                    total_stats,
                    successful,
                    len(self.deck_keys),
                    removed_subdecks,
                    ankiweb_result=None,
                    on_close_callback=hand_off,
                    deck_results=deck_results,
                    new_deck_mode=self.new_deck_mode,
                )
        except Exception as e:
            add_debug_message(
                f"Finishing the sync failed: {e!r}\n{traceback.format_exc()}", "SYNC"
            )
        finally:
            _ACTIVE_RUN = None
            # However the end went, the window must not outlive the run: its
            # Cancel does nothing once the run has finished.
            self.progress.close_when_done()


def _run_was_clean(sync_errors, total_stats, deck_results):
    """Nothing failed and nothing warned — so nothing needs reading."""
    return (
        not sync_errors
        and not total_stats.errors
        and not total_stats.warnings
        and all(r.success for r in deck_results or [])
    )


def clean_run_message(decks_synced, total_decks, total_stats, cancelled=False):
    """The one line a clean sync leaves behind, e.g. ``2 decks synced · 12 new``.

    A sync that went as expected used to end in two windows and two Close
    buttons; there is nothing in that case a reader needs beyond these numbers.
    """
    if cancelled:
        noun = "deck" if total_decks == 1 else "decks"
        head = f"Sync stopped · {decks_synced} of {total_decks} {noun} synced"
    else:
        noun = "deck" if decks_synced == 1 else "decks"
        head = f"{decks_synced} {noun} synced"
    parts = [
        f"{n} {word}"
        for n, word in (
            (total_stats.created, "new"),
            (total_stats.updated, "changed"),
            (total_stats.deleted, "removed"),
        )
        if n
    ]
    return " · ".join([head] + (parts or ["no changes"]))


def _hand_off_to_ankiweb(*_args):
    """Runs AnkiWeb synchronization if configured. Last step of every sync."""
    add_debug_message("Checking AnkiWeb synchronization configuration...", "SYNC")
    try:
        from .ankiweb_sync import execute_ankiweb_sync_if_configured

        ankiweb_result = execute_ankiweb_sync_if_configured()
        if ankiweb_result:
            if ankiweb_result["success"]:
                add_debug_message(f"AnkiWeb sync: {ankiweb_result['message']}", "SYNC")
            else:
                add_debug_message(
                    f"AnkiWeb sync failed: {ankiweb_result['error']}", "SYNC"
                )
        else:
            add_debug_message("AnkiWeb sync disabled", "SYNC")
    except Exception as ankiweb_error:
        add_debug_message(f"AnkiWeb synchronization error: {ankiweb_error}", "SYNC")


def _get_deck_keys_to_sync(remote_decks, selected_deck_names, selected_deck_urls=None):
    """
    Determines which deck keys should be synchronized.
    Now works with hash keys from the new structure.

    Args:
        remote_decks: Dictionary of remote decks (hash_key -> deck_info)
        selected_deck_names: Names of selected decks or None
        selected_deck_urls: URLs of selected decks or None

    Returns:
        list: List of hash keys to be synchronized
    """

    # If specific URLs were provided, convert them to the keys decks are stored
    # under. get_deck_id rather than the bare spreadsheet id: several decks can
    # live in one file, and a URL naming a sheet has to resolve to that deck
    # rather than to nothing at all.
    if selected_deck_urls is not None:
        from .config_manager import get_deck_id

        filtered_keys = []
        for url in selected_deck_urls:
            key = get_deck_id(url)
            if key in remote_decks:
                filtered_keys.append(key)
        return filtered_keys

    # Check if mw.col and mw.col.decks are available
    if not _is_anki_decks_ready():
        return []

    assert mw.col is not None  # Type hint for checker

    # Create name to hash key mapping
    name_to_key = {}
    for hash_key, deck_info in remote_decks.items():
        # Check if deck still exists
        local_deck_id = deck_info.get("local_deck_id")
        deck = mw.col.decks.get(local_deck_id) if local_deck_id is not None else None

        if deck:
            # Use current deck name
            actual_deck_name = deck["name"]
            name_to_key[actual_deck_name] = hash_key

            # Also map config name if different
            config_deck_name = deck_info.get("local_deck_name")
            if config_deck_name and config_deck_name != actual_deck_name:
                name_to_key[config_deck_name] = hash_key

    # If specific names were selected, filter by them
    if selected_deck_names is not None:
        filtered_keys = []
        for deck_name in selected_deck_names:
            if deck_name in name_to_key:
                filtered_keys.append(name_to_key[deck_name])
        return filtered_keys

    # Otherwise, return all hash keys
    return list(remote_decks.keys())


def _show_no_decks_message(selected_deck_names):
    """Shows message when there are no decks to synchronize."""
    if selected_deck_names is not None:
        StyledMessageBox.warning(
            None,
            "Decks Not Found",
            "None of the selected decks were found in the configuration.",
            detailed_text=f"Selected decks: {', '.join(selected_deck_names)}",
        )
    else:
        StyledMessageBox.information(
            None, "No Remote Decks", "No remote decks configured for synchronization."
        )


class LogProgressDialog(QDialog):
    """
    Custom progress dialog with a scrollable log area.
    Mimics QProgressDialog interface used in this module.

    Cancel stops the run between decks (``on_cancel``, set by :class:`_SyncRun`)
    rather than hiding the window: hiding it used to leave the sync carrying on
    out of sight, which is the opposite of what the button says.
    """

    def __init__(self, title, message, min_val, max_val, parent=None):
        from .compat import ButtonBox_Cancel
        from .compat import QDialogButtonBox
        from .theme import MARGIN
        from .theme import SPACE_ELEMENT

        super().__init__(parent)
        self.setWindowTitle("Synchronizing")
        self.on_cancel = None
        self._done = False

        layout = QVBoxLayout(self)
        layout.setSpacing(SPACE_ELEMENT)
        layout.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)

        # What is happening now, in bold, and the log of what already has. It used
        # to carry two dicts of nine hand-picked colours, chosen by measuring the
        # window's background lightness, and a progress bar filled with a green
        # gradient — Anki's own progress bars are not green and are not gradients.
        self.label = QLabel(title)
        self.label.setWordWrap(True)
        self.label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.label)

        self.bar = QProgressBar()
        self.bar.setRange(min_val, max_val)
        self.bar.setValue(0)
        self.bar.setTextVisible(True)
        layout.addWidget(self.bar)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area, 1)

        self.button_box = QDialogButtonBox(ButtonBox_Cancel)
        cancel_btn = self.button_box.button(ButtonBox_Cancel)
        assert cancel_btn is not None  # just asked for, by name
        self.cancel_btn = cancel_btn
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

        self.resize(560, 420)

    def setValue(self, val):
        self.bar.setValue(val)

    def maximum(self):
        return self.bar.maximum()

    def setLabelText(self, text):
        import html

        # Formatting to increase spacing
        lines = text.split("\n")
        html_parts = []
        for line in lines:
            if not line:
                continue
            escaped = html.escape(line)
            # Use div with margin and line-height for spacing
            html_parts.append(
                f"<div style='margin-bottom: 6px; line-height: 1.45;'>{escaped}</div>"
            )

        full_html = "".join(html_parts)
        self.log_area.setHtml(full_html)

        # Scroll to bottom
        cursor = self.log_area.textCursor()
        from .compat import QTextCursor

        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_area.setTextCursor(cursor)

    def setCancelEnabled(self, enabled):
        if self.cancel_btn is not None:
            self.cancel_btn.setEnabled(enabled)

    def setTitle(self, text):
        """Updates the title label."""
        self.label.setText(text)

    def appendMessage(self, text):
        """Appends a message to the log area without clearing history."""
        import html

        escaped = html.escape(text)
        # Create styled HTML block
        html_block = (
            f"<div style='margin-bottom: 6px; line-height: 1.45;'>{escaped}</div>"
        )
        self.log_area.append(html_block)

        # Scroll to bottom
        cursor = self.log_area.textCursor()
        from .compat import QTextCursor

        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_area.setTextCursor(cursor)

    # -- closing ---------------------------------------------------------------
    #
    # Cancel, Escape and the title bar's close button all mean "stop": while the
    # run is going they ask it to stop after the current deck and leave the
    # window up to say so; once it has finished, the window closes itself.

    def reject(self):
        if self._done:
            super().reject()
            return
        if callable(self.on_cancel):
            self.on_cancel()

    def closeEvent(self, event):
        if self._done:
            super().closeEvent(event)
            return
        event.ignore()
        self.reject()

    def close_when_done(self):
        """Closes the window for good. Called by the run when it has finished."""
        self._done = True
        self.close()


def _setup_progress_dialog(total_decks):
    """
    Configures and returns the progress window with its scrollable log.

    Window-modal over Anki's main window, like Anki's own progress windows: the
    main window keeps painting and answering while the sheets download, but a
    note cannot be edited out from under a sync that is about to write it.

    Args:
        total_decks: Total number of decks to calculate bar maximum

    Returns:
        LogProgressDialog: Configured progress dialog
    """
    from .compat import WINDOW_MODAL

    total_steps = total_decks * 3

    progress = LogProgressDialog("Synchronizing…", "", 0, total_steps, mw)
    progress.setWindowModality(WINDOW_MODAL)
    progress.show()
    return progress


def _update_progress_text(
    progress, status_msgs, max_lines=None, debug_messages=None, show_debug=False
):
    """
    Updates progress bar log with all messages.

    Args:
        progress: LogProgressDialog instance
        status_msgs: List of status messages
        max_lines: Ignored (kept for compatibility)
        debug_messages: List of debug messages
        show_debug: If True, shows debug messages in interface
    """
    all_text_lines = []

    # Add all status messages
    if status_msgs:
        all_text_lines.extend(status_msgs)

    # Add debug messages if provided AND requested
    if debug_messages and show_debug:
        all_text_lines.append("")
        all_text_lines.append("=== DEBUG MESSAGES ===")
        all_text_lines.extend(debug_messages)

    # Join all lines
    text = "\n".join(all_text_lines)

    # Update log area (no manual wrapping needed as QTextEdit handles it)
    progress.setLabelText(text)

    # Force interface update
    mw.app.processEvents()


def _sync_single_deck(
    remote_decks,
    deckKey,
    progress,
    status_msgs,
    step,
    debug_messages=None,
    remote_deck=None,
):
    """
    Writes one deck's downloaded sheet into the collection. Main thread only.

    ``remote_deck`` is what :func:`_fetch_deck` made of the sheet on a
    background thread; nothing in here touches the network any more, except as
    a fallback when it is called without one.

    Args:
        remote_decks: Remote decks dictionary
        deckKey: Deck key to synchronize
        progress: Progress dialog
        status_msgs: List of status messages
        step: Current progress step

    Returns:
        tuple: (step, deck_sync_increment, current_stats)
    """
    from .deck_manager import DeckNameManager
    from .deck_manager import DeckRecreationManager

    # Check if mw.col and mw.col.decks are available
    if not _is_anki_decks_ready():
        raise SyncError("Anki is not ready. Please try again in a few moments.")

    assert mw.col is not None  # Type hint for checker

    currentRemoteInfo = remote_decks[deckKey]
    local_deck_id = currentRemoteInfo["local_deck_id"]
    remote_deck_url = currentRemoteInfo["remote_deck_url"]
    add_debug_message(f"📋 Local Deck ID: {local_deck_id}", "SYNC")
    add_debug_message(f"🔗 Remote URL: {remote_deck_url}", "SYNC")

    # Check if deck exists or needs to be recreated
    was_recreated, current_deck_id, current_deck_name = (
        DeckRecreationManager.recreate_deck_if_missing(currentRemoteInfo)
    )

    if was_recreated and current_deck_id is not None and current_deck_name is not None:
        # Capture old ID before update for correct logging
        old_deck_id = local_deck_id

        # Update info in configuration
        DeckRecreationManager.update_deck_info_after_recreation(
            currentRemoteInfo, current_deck_id, current_deck_name
        )

        # IMPORTANT: Save local_deck_id changes immediately after recreation
        # This ensures the new ID is persisted even if a subsequent error occurs
        save_remote_decks(remote_decks)
        add_debug_message(
            f"[CONFIG_SAVE] local_deck_id updated and saved after recreation: {old_deck_id} -> {current_deck_id}",
            "SYNC",
        )

        # Update local variables
        local_deck_id = current_deck_id

        # Inform about recreation
        msg = (
            f"{current_deck_name}: the deck was missing in Anki and has been recreated."
        )
        status_msgs.append(msg)
        _update_progress_text(progress, status_msgs)

        step += 1
        progress.setValue(step)
        mw.app.processEvents()

    # Get current deck (can be original or recreated)
    if local_deck_id is None:
        raise ValueError("Local deck ID is None")

    # Ensure ID is the correct type for Anki
    from anki.decks import DeckId

    deck_id: DeckId = DeckId(local_deck_id)
    deck = mw.col.decks.get(deck_id)
    if not deck:
        raise ValueError(f"Failed to get deck: {deck_id}")

    deckName = deck["name"]
    add_debug_message(f"📋 Current deck: '{deckName}' (ID: {deck_id})", "SYNC")

    # Update info in configuration with actual name used
    currentRemoteInfo["local_deck_name"] = deckName

    if remote_deck is None:
        remote_deck = _fetch_deck(remote_deck_url)
    remoteDeck = remote_deck

    # What the sheet calls itself, kept in meta.json so the first name pass after
    # a restart agrees with this one instead of renaming the deck back and forth.
    from .deck_manager import remember_declared_name

    declared = (
        remember_declared_name(
            remote_deck_url, getattr(remoteDeck, "sheet_config", None)
        )
        or ""
    )
    if currentRemoteInfo.get("declared_name", "") != declared:
        currentRemoteInfo["declared_name"] = declared
        save_remote_decks(remote_decks)

    notes_count = len(remoteDeck.notes) if getattr(remoteDeck, "notes", None) else 0
    add_debug_message(f"Notes loaded from remote deck: {notes_count}", "REMOTE_DECK")

    # Update remote_deck_name with name extracted from URL
    new_remote_name_from_url = DeckNameManager.extract_remote_name_from_url(
        remote_deck_url
    )
    stored_remote_name = currentRemoteInfo.get("remote_deck_name")

    # Check if we could extract a valid name from URL
    if not new_remote_name_from_url:
        add_debug_message(
            f"[NAME_EXTRACT_ERROR] Could not extract name from URL: {remote_deck_url}",
            "SYNC",
        )
        # Use stored name as fallback
        new_remote_name_from_url = stored_remote_name or "Untitled Deck"

    # Defensive initialization of current_remote_name
    current_remote_name = stored_remote_name or new_remote_name_from_url

    # IMPORTANT: Improved logic to resolve conflicts dynamically
    # Check if remote name changed and re-evaluate conflict resolution
    should_update = False
    if stored_remote_name != new_remote_name_from_url:
        # Check if stored name has conflict suffix
        if stored_remote_name and " #conflict" in stored_remote_name:
            # Name has conflict suffix - check if still necessary
            add_debug_message(
                f"[CONFLICT_REEVALUATE] Re-evaluating conflict: '{stored_remote_name}' vs new name '{new_remote_name_from_url}'",
                "SYNC",
            )

            # Use centralized DeckNameManager for conflict resolution
            resolved_new_name = DeckNameManager.resolve_remote_name_conflict(
                remote_deck_url, new_remote_name_from_url
            )

            # If resolved name equals original name, there is no more conflict
            if resolved_new_name == new_remote_name_from_url:
                # Conflict was resolved - can use original name
                should_update = True
                current_remote_name = new_remote_name_from_url
                add_debug_message(
                    f"[CONFLICT_RESOLVED] Conflict resolved! '{stored_remote_name}' → '{new_remote_name_from_url}'",
                    "SYNC",
                )

                # Also update local_deck_name to remove suffix
                old_local_name = currentRemoteInfo.get("local_deck_name", "")
                if old_local_name and " #conflict" in old_local_name:
                    # Remove suffix from local name as well
                    new_local_name = old_local_name.split(" #conflict")[0]
                    add_debug_message(
                        f"[CONFLICT_RESOLVED] Updating local_deck_name: '{old_local_name}' → '{new_local_name}'",
                        "SYNC",
                    )

                    # Update deck name in Anki
                    try:
                        deck_id = currentRemoteInfo.get("local_deck_id")
                        if deck_id and mw and mw.col:
                            from anki.decks import DeckId

                            deck = mw.col.decks.get(DeckId(deck_id))
                            if deck:
                                old_anki_name = deck.get("name", "")
                                deck["name"] = new_local_name
                                mw.col.decks.save(deck)
                                add_debug_message(
                                    f"[ANKI_UPDATE] Deck renamed in Anki: '{old_anki_name}' → '{new_local_name}'",
                                    "SYNC",
                                )
                    except Exception as e:
                        add_debug_message(
                            f"[ANKI_ERROR] Error renaming deck in Anki: {e}", "SYNC"
                        )

                    # Update in configuration
                    currentRemoteInfo["local_deck_name"] = new_local_name
                    remote_decks[deckKey]["local_deck_name"] = new_local_name

            else:
                # Still dynamic conflict, but suffix might have changed
                if resolved_new_name != stored_remote_name:
                    should_update = True
                    current_remote_name = resolved_new_name
                    add_debug_message(
                        f"[CONFLICT_UPDATE] Updating conflict suffix: '{stored_remote_name}' → '{resolved_new_name}'",
                        "SYNC",
                    )
                else:
                    current_remote_name = stored_remote_name  # Keep existing name
                    add_debug_message(
                        f"[CONFLICT_UNCHANGED] Keeping existing resolution: '{stored_remote_name}'",
                        "SYNC",
                    )

        else:
            # Name doesn't have conflict, apply normal resolution with DeckNameManager
            resolved_remote_name = DeckNameManager.resolve_remote_name_conflict(
                remote_deck_url, new_remote_name_from_url
            )

            if resolved_remote_name != stored_remote_name:
                should_update = True
                current_remote_name = resolved_remote_name
                add_debug_message(
                    f"[CONFLICT_RESOLVE] Applying resolution: '{new_remote_name_from_url}' → '{resolved_remote_name}'",
                    "SYNC",
                )
            else:
                current_remote_name = stored_remote_name  # Keep existing name
                add_debug_message(
                    f"[CONFLICT_KEEP] Keeping resolved name: '{stored_remote_name}'",
                    "SYNC",
                )

    else:
        # Name didn't change, no update needed
        add_debug_message(
            f"[CONFLICT_SKIP] Remote name didn't change, keeping: '{stored_remote_name}'",
            "SYNC",
        )
        current_remote_name = stored_remote_name

    # ROBUST APPROACH: Always recreate local_deck_name and check if it changed
    from .deck_manager import DeckNameManager

    # Recreate local_deck_name based on current remote_deck_name
    expected_local_deck_name = DeckNameManager.generate_local_name(current_remote_name)
    current_local_deck_name = currentRemoteInfo.get("local_deck_name", "")

    add_debug_message("[DECK_NAME_CHECK] Checking name consistency:", "SYNC")
    add_debug_message(f"[DECK_NAME_CHECK] - Remote: '{current_remote_name}'", "SYNC")
    add_debug_message(
        f"[DECK_NAME_CHECK] - Current local: '{current_local_deck_name}'", "SYNC"
    )
    add_debug_message(
        f"[DECK_NAME_CHECK] - Expected local: '{expected_local_deck_name}'", "SYNC"
    )

    # Check if local_deck_name needs update
    local_name_needs_update = current_local_deck_name != expected_local_deck_name

    # Apply necessary updates
    if should_update or local_name_needs_update:
        if should_update:
            add_debug_message("[UPDATE_REASON] remote_deck_name changed", "SYNC")
        if local_name_needs_update:
            add_debug_message("[UPDATE_REASON] local_deck_name inconsistent", "SYNC")

        # Update local_deck_name in meta.json
        if local_name_needs_update:
            DeckNameManager._update_name_in_config(
                remote_deck_url, expected_local_deck_name
            )
            add_debug_message(
                f"[LOCAL_NAME_UPDATE] local_deck_name updated: '{current_local_deck_name}' -> '{expected_local_deck_name}'",
                "SYNC",
            )

        # Sync physical deck name in Anki if necessary
        sync_result = DeckNameManager.sync_deck_with_config(remote_deck_url)
        if sync_result:
            add_debug_message(
                f"[DECK_SYNC] Physical deck synchronized: ID {sync_result[0]} -> '{sync_result[1]}'",
                "SYNC",
            )

        # Update configuration if remote_deck_name changed
        if should_update:
            # IMPORTANT: Update note type names BEFORE changing remote_deck_name
            old_remote_name_config = currentRemoteInfo.get("remote_deck_name")
            if old_remote_name_config and old_remote_name_config != current_remote_name:
                try:
                    from .config_manager import get_deck_note_type_ids
                    from .utils import update_note_type_names_for_deck_rename

                    # Detect actual name present in note types
                    note_types_config = get_deck_note_type_ids(remote_deck_url)
                    actual_old_name = None

                    if note_types_config:
                        # Look for common pattern in note types to extract actual name
                        for note_type_name in note_types_config.values():
                            # Format: "SheetCards - {remote_name} - {type}"
                            if " - " in note_type_name:
                                parts = note_type_name.split(" - ")
                                if len(parts) >= 3 and parts[0] == "SheetCards":
                                    # Reconstruct remote name (can have multiple hyphens)
                                    # Get everything between "SheetCards - " and " - {type}"
                                    start_idx = note_type_name.find(
                                        "SheetCards - "
                                    ) + len("SheetCards - ")
                                    # Find last occurrence of " - {type}"
                                    last_dash_type = note_type_name.rfind(
                                        " - " + parts[-1]
                                    )
                                    if last_dash_type > start_idx:
                                        potential_name = note_type_name[
                                            start_idx:last_dash_type
                                        ]
                                        actual_old_name = potential_name
                                        break

                    # If detection failed, use name from configuration
                    old_name_to_use = (
                        actual_old_name if actual_old_name else old_remote_name_config
                    )

                    add_debug_message(
                        f"[NOTE_TYPE_DETECT] old_remote_name_config: '{old_remote_name_config}'",
                        "SYNC",
                    )
                    add_debug_message(
                        f"[NOTE_TYPE_DETECT] actual_old_name detected: '{actual_old_name}'",
                        "SYNC",
                    )
                    add_debug_message(
                        f"[NOTE_TYPE_DETECT] using for update: '{old_name_to_use}' → '{current_remote_name}'",
                        "SYNC",
                    )

                    updated_count = update_note_type_names_for_deck_rename(
                        remote_deck_url,
                        old_name_to_use,
                        current_remote_name,
                        debug_messages,
                    )
                    add_debug_message(
                        f"[NOTE_TYPE_UPDATE] {updated_count} note types updated to new remote_deck_name",
                        "SYNC",
                    )

                    # Sync note types in Anki with updated names
                    if updated_count > 0:
                        try:
                            from .utils import sync_note_type_names_with_config

                            sync_result = sync_note_type_names_with_config(
                                mw.col, remote_deck_url, debug_messages
                            )
                            if (
                                sync_result
                                and sync_result.get("renamed_in_anki", 0) > 0
                            ):
                                add_debug_message(
                                    f"[NOTE_TYPE_ANKI_SYNC] {sync_result['renamed_in_anki']} note types renamed in Anki",
                                    "SYNC",
                                )
                            else:
                                add_debug_message(
                                    "[NOTE_TYPE_ANKI_SYNC] No note types renamed in Anki",
                                    "SYNC",
                                )
                        except Exception as anki_sync_error:
                            add_debug_message(
                                f"[NOTE_TYPE_ANKI_ERROR] Error syncing note types in Anki: {anki_sync_error}",
                                "SYNC",
                            )
                except Exception as note_type_error:
                    add_debug_message(
                        f"[NOTE_TYPE_ERROR] Error updating note types: {note_type_error}",
                        "SYNC",
                    )

        currentRemoteInfo["remote_deck_name"] = current_remote_name
        remote_decks[deckKey]["remote_deck_name"] = current_remote_name
        add_debug_message(
            f"[REMOTE_NAME_UPDATE] remote_deck_name updated to: '{current_remote_name}'",
            "SYNC",
        )

        # Always update local_deck_name in memory configuration
        if local_name_needs_update:
            currentRemoteInfo["local_deck_name"] = expected_local_deck_name
            remote_decks[deckKey]["local_deck_name"] = expected_local_deck_name
            add_debug_message("[MEMORY_UPDATE] In-memory configuration updated", "SYNC")

        # IMPORTANT: Do not reload from file here to preserve in-memory updates
        add_debug_message(
            "[CONFIG_PRESERVE] Preserving in-memory updates (remote_deck_name, note_types, and deck_options)",
            "SYNC",
        )

        # Save final configuration (now with updated note_types AND correct remote_deck_name)
        save_remote_decks(remote_decks)
        add_debug_message(
            "[CONFIG_SAVE] Configuration saved after name update (with correct note_types)",
            "SYNC",
        )  # Update deck name if necessary using DeckNameManager
    current_remote_name = currentRemoteInfo.get("remote_deck_name")
    sync_result = DeckNameManager.sync_deck_with_config(remote_deck_url)

    if sync_result:
        sync_deck_id, updated_name = sync_result
        if updated_name != deckName:
            # Update deck info in configuration
            currentRemoteInfo["local_deck_name"] = updated_name

            msg = f"{deckName}: renamed to {updated_name}."
            deckName = updated_name
            remoteDeck.deckName = updated_name

            status_msgs.append(msg)
            _update_progress_text(progress, status_msgs)

    # 2. Processing and writing to database
    remoteDeck.deckName = deckName

    # The files fetched in the background go into the media folder first, and
    # the cells that point at them become their names, before anything compares
    # the rows against the notes.
    try:
        from .media_fetch import store_deck_media

        embedded = store_deck_media(
            mw.col, remoteDeck, getattr(remoteDeck, "fetched_media", None)
        )
        if embedded:
            status_msgs.append(
                f"{deckName}: {embedded} picture{'s' if embedded != 1 else ''}/"
                f"recording{'s' if embedded != 1 else ''} saved for offline review."
            )
            _update_progress_text(progress, status_msgs)
    except Exception as e:
        add_debug_message(f"Media not stored: {e}", "MEDIA")

    msg = f"{deckName}: saving changes…"
    status_msgs.append(msg)
    _update_progress_text(progress, status_msgs)

    add_debug_message(
        f"🚀 ABOUT TO CALL create_or_update_notes - remoteDeck has {len(remoteDeck.notes) if hasattr(remoteDeck, 'notes') and remoteDeck.notes else 0} notes",
        "SYNC",
    )

    # Critical debug to verify import
    add_debug_message(
        f"🔧 create_or_update_notes function: {create_or_update_notes}", "SYNC"
    )
    add_debug_message(
        f"🔧 mw.col: {mw.col}, remoteDeck: {remoteDeck}, local_deck_id: {local_deck_id}",
        "SYNC",
    )

    try:
        add_debug_message("🔧 CALLING create_or_update_notes NOW...", "SYNC")
        deck_stats = create_or_update_notes(
            mw.col,
            remoteDeck,
            local_deck_id,
            deck_url=remote_deck_url,
            debug_messages=debug_messages,
        )
        add_debug_message(f"🔧 create_or_update_notes RETURNED: {deck_stats}", "SYNC")
    except Exception as e:
        error_details = traceback.format_exc()
        add_debug_message(f"❌ ERROR in create_or_update_notes call: {e}", "SYNC")
        add_debug_message(f"❌ Stack trace: {error_details}", "SYNC")
        # Return default stats with errors (add_error increments the counter,
        # so start at 0 to avoid double-counting this single failure).
        deck_stats = SyncStats(created=0, updated=0, deleted=0, errors=0, ignored=0)
        deck_stats.add_error(user_message(e))

    add_debug_message(
        f"✅ create_or_update_notes COMPLETED - returned: {deck_stats}", "SYNC"
    )

    # Show warnings in progress bar if any
    if deck_stats.warnings:
        for warning in deck_stats.warnings:
            status_msgs.append(warning)
        _update_progress_text(progress, status_msgs)

    step += 1
    progress.setValue(step)
    mw.app.processEvents()

    # 4. Capture and store note type IDs after successful synchronization
    try:

        add_debug_message(f"Starting note type ID capture for deck: {deckName}", "SYNC")

        # Capture created/updated note type IDs
        capture_deck_note_type_ids(
            remote_deck_url,  # Use actual URL instead of hash key
            currentRemoteInfo.get("remote_deck_name", "RemoteDeck"),
        )

        add_debug_message(
            f"✅ Note type IDs captured and stored for deck: {deckName}",
            "SYNC",
        )

        # NEW: Ensure automatic name consistency after synchronization
        add_debug_message(
            f"🔧 Starting name consistency check for: {remote_deck_url}",
            "NAME_CONSISTENCY",
        )

        try:
            consistency_result = NameConsistencyManager.ensure_consistency_during_sync(
                deck_url=remote_deck_url,
                remote_decks=remote_decks,
                debug_callback=lambda msg: add_debug_message(msg, "NAME_CONSISTENCY"),
            )

            if consistency_result and not consistency_result.get("errors"):
                # Success - log what was updated
                updates = []
                if consistency_result.get("deck_updated"):
                    updates.append("deck name")
                if consistency_result.get("note_types_updated"):
                    updates.append(
                        f"{len(consistency_result['note_types_updated'])} note types"
                    )
                if consistency_result.get("deck_options_updated"):
                    updates.append("deck options")

                if updates:
                    add_debug_message(
                        f"✅ Consistency applied: {', '.join(updates)} updated",
                        "NAME_CONSISTENCY",
                    )
                    status_msgs.append(f"{deckName}: updated {', '.join(updates)}.")
                    _update_progress_text(progress, status_msgs)
                else:
                    add_debug_message(
                        "✅ Consistency verified: all names were already correct",
                        "NAME_CONSISTENCY",
                    )
            elif consistency_result and consistency_result.get("errors"):
                # Error - but don't fail synchronization
                for error in consistency_result["errors"]:
                    add_debug_message(
                        f"⚠️ Name consistency error: {error}",
                        "NAME_CONSISTENCY",
                    )
        except Exception as consistency_error:
            # Don't fail synchronization due to name consistency
            add_debug_message(
                f"⚠️ Unexpected name consistency error: {consistency_error}",
                "NAME_CONSISTENCY",
            )

    except Exception as e:
        # Don't fail synchronization due to ID capture
        add_debug_message(
            f"❌ ERROR capturing note type IDs for {deckName}: {e}", "SYNC"
        )
        error_details = traceback.format_exc()
        add_debug_message(f"Error details: {error_details}", "SYNC")

    # 5. ROBUST NOTE_TYPE SYNCHRONIZATION after Anki note creation
    add_debug_message(
        "[NOTE_TYPE_SYNC] Starting robust note_type synchronization AFTER note creation...",
        "SYNC",
    )
    try:
        sync_result = sync_note_type_names_robustly(
            remote_deck_url, current_remote_name
        )

        if sync_result["updated_count"] > 0:
            add_debug_message(
                f"[NOTE_TYPE_SYNC] ✅ {sync_result['updated_count']} note_types successfully synchronized",
                "SYNC",
            )
            add_debug_message(
                f"[NOTE_TYPE_SYNC] - Renamed in Anki: {sync_result['renamed_in_anki']}",
                "SYNC",
            )
            add_debug_message(
                f"[NOTE_TYPE_SYNC] - Updated in meta.json: {sync_result['updated_in_meta']}",
                "SYNC",
            )
            if sync_result.get("notes_migrated", 0) > 0:
                add_debug_message(
                    f"[NOTE_TYPE_SYNC] - Notes migrated: {sync_result['notes_migrated']}",
                    "SYNC",
                )

            n = sync_result["updated_count"]
            status_msgs.append(
                f"{deckName}: renamed {n} note type{'s' if n != 1 else ''}."
            )
            _update_progress_text(progress, status_msgs)

        else:
            add_debug_message(
                "[NOTE_TYPE_SYNC] ✅ All note_types are already consistent", "SYNC"
            )

    except Exception as e:
        add_debug_message(
            f"[NOTE_TYPE_SYNC] ❌ Robust synchronization error: {e}", "SYNC"
        )
        # Try fallback with old method
        try:
            update_note_type_names_in_meta(remote_deck_url, current_remote_name)
            add_debug_message("[NOTE_TYPE_SYNC] Fallback successfully applied", "SYNC")
        except Exception as fallback_error:
            add_debug_message(
                f"[NOTE_TYPE_SYNC] ❌ Fallback also failed: {fallback_error}", "SYNC"
            )

    # CRITICAL: Save final configurations after name consistency
    # This ensures NameConsistencyManager updates are persisted
    try:
        from .config_manager import get_meta
        from .config_manager import save_meta

        current_meta = get_meta()
        save_meta(current_meta)
        add_debug_message(
            "💾 FINAL_SAVE: Configurations saved after consistency check", "SYNC"
        )
    except Exception as save_error:
        add_debug_message(
            f"⚠️ FINAL_SAVE: Error saving final configurations: {save_error}", "SYNC"
        )

    return step, 1, deck_stats


def _resolve_deck_name_for_error(deckKey, remote_decks):
    """Best-effort local deck name for an error message; never raises."""
    if not _is_anki_decks_ready():
        return "Unknown"
    assert mw.col is not None  # Type hint for checker
    try:
        deck_info = remote_decks[deckKey]
        local_deck_id = deck_info["local_deck_id"]
        deck = mw.col.decks.get(local_deck_id) if local_deck_id is not None else None
        if deck:
            return deck["name"]
        if local_deck_id is not None:
            # deckKey is a spreadsheet id, so resolve the name from deck_info
            # (get_deck_local_name expects a URL and would fail on a bare id).
            return deck_info.get("local_deck_name") or str(local_deck_id)
        return "Unknown"
    except Exception:
        return "Unknown"
