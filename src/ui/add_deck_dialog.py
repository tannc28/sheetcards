"""
Enhanced dialog for adding new remote decks.

This module provides a modern, user-friendly interface for adding decks
with support for automatic naming and conflict resolution.
"""

from ..compat import AlignCenter
from ..compat import DialogAccepted
from ..compat import QDialog
from ..compat import QGroupBox
from ..compat import QHBoxLayout
from ..compat import QLabel
from ..compat import QLineEdit
from ..compat import QProgressBar
from ..compat import QPushButton
from ..compat import QTimer
from ..compat import QVBoxLayout
from ..compat import QWidget
from ..compat import mw
from ..compat import safe_exec
from ..config_manager import add_remote_deck
from ..config_manager import get_remote_decks
from ..config_manager import is_deck_disconnected
from ..data_processor import RemoteDeckError
from ..data_processor import read_all_sheets
from ..styled_messages import StyledMessageBox
from ..templates_and_definitions import DEFAULT_PARENT_DECK_NAME
from ..theme import base_dialog_qss
from ..theme import get_colors
from ..theme import make_header
from ..theme import primary_button_qss
from ..theme import secondary_button_qss
from ..utils import add_debug_message
from ..utils import get_or_create_deck
from ..utils import get_spreadsheet_id_from_url
from ..utils import validate_url


class AddDeckDialog(QDialog):
    """
    Modern, user-friendly dialog for adding new remote decks.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Remote Deck")
        self.setModal(True)
        self.setMinimumWidth(520)

        self.remote_deck = None
        self.suggested_name = ""
        # Every sheet in the file, judged one by one. A Google Sheets file holds
        # several sheets and each becomes its own deck, so connecting a link is a
        # decision about a file rather than about a single grid.
        self.offers = []
        self.validation_timer = QTimer()

        # Get colors based on current theme
        self.colors = get_colors()

        self._setup_styles()
        self.setStyleSheet(self.styleSheet() + base_dialog_qss(self.colors))
        self._setup_ui()
        self._connect_signals()
        self._adjust_dialog_size()

    def _setup_styles(self):
        """Sets up the dialog's stylesheet."""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colors['background']};
            }}
            QGroupBox {{
                font-weight: bold;
                font-size: 13px;
                color: {self.colors['text_primary']};
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                background-color: {self.colors['background']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                background-color: {self.colors['background']};
            }}
            QLineEdit {{
                padding: 12px 16px;
                font-size: 13px;
                border: 2px solid {self.colors['border']};
                border-radius: 8px;
                background-color: {self.colors['background']};
                color: {self.colors['text_primary']};
            }}
            QLineEdit:focus {{
                border-color: {self.colors['primary']};
                background-color: {self.colors['primary_light']};
            }}
            QLineEdit:disabled {{
                background-color: {self.colors['background_secondary']};
                color: {self.colors['text_muted']};
            }}
            QLabel {{
                color: {self.colors['text_primary']};
            }}
        """)

    def _setup_ui(self):
        """Sets up the modern user interface."""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # ===== HEADER SECTION =====
        header_widget = self._create_header()
        main_layout.addWidget(header_widget)

        # ===== STEP 1: URL INPUT =====
        step1_group = self._create_step1_section()
        main_layout.addWidget(step1_group)

        # ===== STEP 2: PREVIEW (Initially hidden) =====
        self.step2_group = self._create_step2_section()
        self.step2_group.setVisible(False)
        main_layout.addWidget(self.step2_group)

        # ===== PROGRESS BAR =====
        self.progress_bar = self._create_progress_bar()
        main_layout.addWidget(self.progress_bar)

        # ===== SPACER =====
        main_layout.addStretch()

        # ===== BUTTONS =====
        buttons_layout = self._create_buttons()
        main_layout.addLayout(buttons_layout)

        self.setLayout(main_layout)

    def _create_header(self):
        """Creates the gradient header banner (consistent with the other dialogs)."""
        return make_header(
            self.colors,
            "Add Remote Deck",
            "Connect a Google Sheets spreadsheet to sync flashcards automatically.",
        )

    def _create_step1_section(self):
        """Creates Step 1: URL input section."""
        group = QGroupBox("Step 1: Paste Spreadsheet URL")
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(16, 20, 16, 16)

        # Help text
        help_text = QLabel(
            "💡 <b>How to get the URL:</b> Open your Google Sheets spreadsheet, "
            'click <b>Share</b>, set access to <b>"Anyone with the link"</b>, '
            "then copy the URL from your browser."
        )
        help_text.setStyleSheet(f"""
            font-size: 11px;
            color: {self.colors['text_secondary']};
            background-color: {self.colors['background_secondary']};
            padding: 10px 12px;
            border-radius: 6px;
            line-height: 1.5;
        """)
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        # URL input container
        input_container = QWidget()
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(8)

        # URL input field
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://docs.google.com/spreadsheets/d/...")
        self.url_edit.setMinimumHeight(44)
        input_layout.addWidget(self.url_edit)

        # Status indicator button (visual only)
        self.status_indicator = QLabel("⚪")
        self.status_indicator.setFixedSize(32, 32)
        self.status_indicator.setAlignment(AlignCenter)
        self.status_indicator.setStyleSheet(f"""
            font-size: 16px;
            background-color: {self.colors['background_secondary']};
            border-radius: 16px;
        """)
        input_layout.addWidget(self.status_indicator)

        layout.addWidget(input_container)

        # Status message area
        self.status_container = QWidget()
        status_layout = QHBoxLayout(self.status_container)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(8)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(f"""
            font-size: 12px;
            color: {self.colors['text_secondary']};
            padding: 4px 0;
        """)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        layout.addWidget(self.status_container)

        group.setLayout(layout)
        return group

    def _create_step2_section(self):
        """Creates Step 2: Preview section."""
        group = QGroupBox("Step 2: Review Deck Details")
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(16, 20, 16, 16)

        # Statistics container
        self.stats_widget = QWidget()
        stats_layout = QHBoxLayout(self.stats_widget)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(16)

        # We'll add stat cards dynamically
        self.stats_layout = stats_layout
        layout.addWidget(self.stats_widget)

        # Conflict warning (initially hidden)
        self.conflict_warning = QLabel("")
        self.conflict_warning.setVisible(False)
        self.conflict_warning.setStyleSheet(f"""
            font-size: 12px;
            color: {self.colors['warning']};
            background-color: {self.colors['warning_light']};
            border: 1px solid {self.colors['warning']};
            border-radius: 6px;
            padding: 10px 14px;
        """)
        self.conflict_warning.setWordWrap(True)
        layout.addWidget(self.conflict_warning)

        # Deck name preview section
        name_section = QWidget()
        name_layout = QVBoxLayout(name_section)
        name_layout.setContentsMargins(0, 8, 0, 0)
        name_layout.setSpacing(6)

        name_label = QLabel("Deck will be created as:")
        name_label.setStyleSheet(f"""
            font-size: 11px;
            color: {self.colors['text_secondary']};
            font-weight: bold;
        """)
        name_layout.addWidget(name_label)

        self.name_preview = QLabel("")
        self.name_preview.setStyleSheet(f"""
            font-size: 14px;
            font-weight: bold;
            color: {self.colors['primary']};
            background-color: {self.colors['primary_light']};
            padding: 12px 16px;
            border-radius: 6px;
            border: 1px solid {self.colors['primary']};
        """)
        self.name_preview.setWordWrap(True)
        name_layout.addWidget(self.name_preview)

        layout.addWidget(name_section)

        group.setLayout(layout)
        return group

    def _create_stat_card(self, icon, value, label):
        """Creates a statistics card widget."""
        card = QWidget()
        card.setObjectName("statCard")
        card.setStyleSheet(f"""
            QWidget#statCard {{
                background-color: {self.colors['background_secondary']};
                border-radius: 8px;
                min-width: 110px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # Icon and value
        value_label = QLabel(f"{icon} {value}")
        value_label.setStyleSheet(f"""
            QLabel {{
                font-size: 16px;
                font-weight: bold;
                color: {self.colors['text_primary']};
            }}
        """)
        value_label.setAlignment(AlignCenter)
        value_label.setWordWrap(True)
        layout.addWidget(value_label)

        # Label
        text_label = QLabel(label)
        text_label.setStyleSheet(f"""
            QLabel {{
                font-size: 10px;
                color: {self.colors['text_secondary']};
            }}
        """)
        text_label.setAlignment(AlignCenter)
        text_label.setWordWrap(True)
        layout.addWidget(text_label)

        return card

    def _create_progress_bar(self):
        """Creates a modern progress bar."""
        progress = QProgressBar()
        progress.setVisible(False)
        progress.setMaximumHeight(4)
        progress.setTextVisible(False)
        progress.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                background-color: {self.colors['border_light']};
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {self.colors['primary']};
                border-radius: 2px;
            }}
        """)
        return progress

    def _create_buttons(self):
        """Creates the button section."""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 8, 0, 0)
        layout.setSpacing(12)

        # Cancel button
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumHeight(40)
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.setStyleSheet(secondary_button_qss(self.colors))

        # Add button
        self.add_button = QPushButton("✓ Add Deck")
        self.add_button.setEnabled(False)
        self.add_button.setMinimumHeight(40)
        self.add_button.setMinimumWidth(140)
        self.add_button.setStyleSheet(primary_button_qss(self.colors, "success"))

        layout.addStretch()
        layout.addWidget(self.cancel_button)
        layout.addWidget(self.add_button)

        return layout

    def _connect_signals(self):
        """Connects interface signals."""
        self.validation_timer.setSingleShot(True)
        self.validation_timer.timeout.connect(self._validate_url_auto)

        self.url_edit.textChanged.connect(self._on_url_changed)
        self.add_button.clicked.connect(self._add_deck)
        self.cancel_button.clicked.connect(self.reject)

    def _adjust_dialog_size(self):
        """Adjusts window size based on visible content."""
        QTimer.singleShot(10, self._do_adjust_size)

    def _do_adjust_size(self):
        """Executes window size adjustment."""
        layout = self.layout()
        if not layout:
            return

        # Force layout recalculation
        layout.activate()
        self.adjustSize()

        # Get the recommended size
        size_hint = self.sizeHint()

        # Calculate ideal dimensions with better bounds
        # When step2 is visible, need more width for 5 stat cards with potentially large numbers
        min_width = 720 if self.step2_group.isVisible() else 520
        ideal_width = max(size_hint.width(), min_width)
        ideal_height = max(size_hint.height(), 300)

        # Apply the new size
        self.resize(ideal_width, ideal_height)
        self.updateGeometry()

    def _check_duplicate_spreadsheet(self, url):
        """
        Checks if a spreadsheet is already registered.

        Args:
            url (str): URL to check

        Returns:
            tuple: (is_duplicate, deck_info, is_disconnected)
        """
        try:
            # A deck connected before sheets could be told apart is stored under
            # the bare spreadsheet id, so that is still a duplicate of this file.
            spreadsheet_id = get_spreadsheet_id_from_url(url)
            remote_decks = get_remote_decks()
            if spreadsheet_id in remote_decks:
                deck_info = remote_decks[spreadsheet_id]
                is_disconnected = is_deck_disconnected(url)
                return True, deck_info, is_disconnected
            return False, None, False
        except ValueError:
            return False, None, False

    def _unconnected_sheets(self, url):
        """The usable sheets of this file that are not decks yet.

        A file is not all-or-nothing: someone adds a sheet to a spreadsheet they
        connected last month and expects connecting it again to pick up the new
        one, not to be told the whole thing is already registered.
        """
        from ..config_manager import get_deck_id
        from ..utils import url_for_sheet

        remote_decks = get_remote_decks()
        fresh = []
        for offer in self.offers:
            if not offer.usable:
                continue
            try:
                if get_deck_id(url_for_sheet(url, offer.name)) not in remote_decks:
                    fresh.append(offer)
            except ValueError:
                continue
        return fresh

    def _on_url_changed(self):
        """Called when URL is changed - starts automatic validation."""
        self.add_button.setEnabled(False)
        self.step2_group.setVisible(False)
        self.remote_deck = None
        self.suggested_name = ""
        self.offers = []
        self._adjust_dialog_size()

        url = self.url_edit.text().strip()

        if not url:
            self._show_status("Waiting for URL...", "waiting")
            self.validation_timer.stop()
            return

        # Immediate feedback for obviously invalid URLs
        if not url.startswith(("http://", "https://")):
            self._show_status("URL must start with http:// or https://", "error")
            self.validation_timer.stop()
            return

        if "docs.google.com/spreadsheets" not in url:
            self._show_status("Please enter a valid Google Sheets URL", "error")
            self.validation_timer.stop()
            return

        # Start timer for automatic validation
        self._show_status("Validating URL...", "validating")
        self.validation_timer.stop()
        self.validation_timer.start(1200)

    def _validate_url_auto(self):
        """Validates URL automatically (called by timer)."""
        from ..deck_manager import DeckNameManager

        url = self.url_edit.text().strip()

        if not url:
            return

        # Check if URL is already in use
        is_duplicate, deck_info, is_disconnected = self._check_duplicate_spreadsheet(
            url
        )
        if is_duplicate:
            if is_disconnected:
                self._show_status(
                    "This spreadsheet will reconnect an existing deck", "warning"
                )
            else:
                # A whole-file deck from before sheets could be told apart. It is
                # not a dead end: the first sheet is the one it has been syncing,
                # so it can adopt that sheet and the rest can join it as decks of
                # their own. Said here, done on Add.
                deck_name = (
                    deck_info.get("remote_deck_name", "Unknown")
                    if deck_info
                    else "Unknown"
                )
                self._show_status(
                    f"'{deck_name}' already covers this file — adding will keep it "
                    "and connect the other sheets beside it",
                    "warning",
                )

        self._show_progress(True)

        try:
            # Validate URL format
            self.tsv_url = validate_url(url)

            # Read every sheet in the file. One download serves all of them, and
            # what comes back decides how many decks this link becomes.
            self.offers = read_all_sheets(url)
            usable = [o for o in self.offers if o.usable]
            if not usable:
                skipped = "; ".join(
                    f"{o.name}: {o.problem}" for o in self.offers
                ) or "the file has no sheets in it"
                self._show_status(
                    f"No sheet in this file can become a deck — {skipped}", "error"
                )
                self.add_button.setEnabled(False)
                return

            # The first usable sheet fills the preview, which shows one set of
            # numbers; the sheet list below it says what else is coming.
            self.remote_deck = usable[0].deck

            # Extract suggested name
            self.suggested_name = DeckNameManager.extract_remote_name_from_url(url)

            # Show preview
            self._show_deck_preview()

            fresh = self._unconnected_sheets(url)
            if not fresh:
                self._show_status(
                    f"All {len(usable)} sheets in this file are already connected",
                    "error",
                )
                self.add_button.setEnabled(False)
                return

            self._show_status(self._sheet_summary(fresh), "success")
            self.add_button.setEnabled(True)

        except RemoteDeckError as e:
            self._show_status(f"Error: {str(e)}", "error")
        except Exception as e:
            self._show_status(f"Validation error: {str(e)}", "error")
        finally:
            self._show_progress(False)

    def _show_progress(self, show):
        """Shows/hides progress bar."""
        if show:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setVisible(False)
        self._adjust_dialog_size()

    def _show_status(self, message, status_type="info"):
        """Shows status message with visual indicator."""
        indicators = {
            "waiting": (
                "⚪",
                self.colors["text_muted"],
                self.colors["background_secondary"],
            ),
            "validating": ("🔄", self.colors["primary"], self.colors["primary_light"]),
            "success": ("✅", self.colors["success"], self.colors["success_light"]),
            "warning": ("⚠️", self.colors["warning"], self.colors["warning_light"]),
            "error": ("❌", self.colors["error"], self.colors["error_light"]),
        }

        icon, color, bg = indicators.get(
            status_type,
            ("ℹ️", self.colors["text_secondary"], self.colors["background_secondary"]),
        )

        self.status_indicator.setText(icon)
        self.status_indicator.setStyleSheet(f"""
            font-size: 16px;
            background-color: {bg};
            border-radius: 16px;
        """)

        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"""
            font-size: 12px;
            color: {color};
            padding: 4px 0;
            font-weight: {'bold' if status_type in ['success', 'error'] else 'normal'};
        """)

    def _sheet_summary(self, fresh):
        """What this link is about to become, in one line."""
        skipped = [o for o in self.offers if not o.usable]
        names = ", ".join(o.name for o in fresh)
        head = (
            f"1 sheet: {names}"
            if len(fresh) == 1
            else f"{len(fresh)} sheets, one deck each: {names}"
        )
        if skipped:
            head += f" (skipping {len(skipped)}: {', '.join(o.name for o in skipped)})"
        return head

    def _show_deck_preview(self):
        """Shows preview of validated deck with statistics."""
        if not self.remote_deck:
            return

        # Clear existing stat cards
        while self.stats_layout.count():
            item = self.stats_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Get statistics
        deck_stats = self.remote_deck.get_statistics()

        # Create stat cards
        # Create stat cards - ALWAYS SHOW ALL for consistent UI
        valid_lines = deck_stats.get("valid_note_lines", 0)
        self.stats_layout.addWidget(
            self._create_stat_card("📝", str(valid_lines), "Questions")
        )

        potential_notes = deck_stats.get("total_potential_anki_notes", 0)
        self.stats_layout.addWidget(
            self._create_stat_card("🎯", str(potential_notes), "Anki Notes")
        )

        invalid_lines = deck_stats.get("invalid_note_lines", 0)
        self.stats_layout.addWidget(
            self._create_stat_card("🫥", str(invalid_lines), "Invalid Rows")
        )

        ghost_rows = deck_stats.get("ignored_ghost_rows", 0)
        self.stats_layout.addWidget(
            self._create_stat_card("👻", str(ghost_rows), "Ghost Rows")
        )

        self.stats_layout.addStretch()

        # Update deck name preview
        self._update_deck_name_preview()

        self.step2_group.setVisible(True)
        self._adjust_dialog_size()

    def _update_deck_name_preview(self):
        """Updates deck name preview with conflict detection."""
        from ..deck_manager import DeckNameManager

        if not self.suggested_name:
            return

        current_url = self.url_edit.text().strip()
        final_remote_name = DeckNameManager.resolve_remote_name_conflict(
            current_url, self.suggested_name
        )

        parent_name = DEFAULT_PARENT_DECK_NAME
        full_name = f"{parent_name}::{final_remote_name}"

        if final_remote_name != self.suggested_name:
            # CONFLICT - Show warning
            self.conflict_warning.setText(
                f"⚠️ Name conflict detected! Original: '{self.suggested_name}' → "
                f"Renamed to: '{final_remote_name}'"
            )
            self.conflict_warning.setVisible(True)

            self.name_preview.setText(full_name)
            self.name_preview.setStyleSheet(f"""
                font-size: 14px;
                font-weight: bold;
                color: {self.colors['warning']};
                background-color: {self.colors['warning_light']};
                padding: 12px 16px;
                border-radius: 6px;
                border: 1px solid {self.colors['warning']};
            """)
        else:
            # No conflict
            self.conflict_warning.setVisible(False)
            self.name_preview.setText(full_name)
            self.name_preview.setStyleSheet(f"""
                font-size: 14px;
                font-weight: bold;
                color: {self.colors['primary']};
                background-color: {self.colors['primary_light']};
                padding: 12px 16px;
                border-radius: 6px;
                border: 1px solid {self.colors['primary']};
            """)

        self._adjust_dialog_size()

    def _add_deck(self):
        """Adds the remote deck."""
        from ..deck_manager import DeckNameManager

        url = self.url_edit.text().strip()

        if not url or not self.remote_deck:
            StyledMessageBox.warning(
                self,
                "Validation Required",
                "Please validate the URL before proceeding.",
                detailed_text="The URL needs to be checked to ensure it points to a valid Google Sheet.",
            )
            return

        # A file already connected as one whole deck, from before sheets could be
        # told apart. Connecting it again would sit a per-sheet deck beside it and
        # sync the same rows twice.
        usable = [o for o in self.offers if o.usable]
        if usable:
            # The old deck has been syncing the first sheet all along, so that is
            # the only sheet it can be pointed at without reassigning its notes to
            # different rows. Done before the fresh list is worked out, so the
            # sheet it adopts is not offered again as a second deck.
            from ..config_manager import adopt_sheet_into_legacy_deck

            if adopt_sheet_into_legacy_deck(url, usable[0].name):
                add_debug_message(
                    f"Existing deck now names its sheet: {usable[0].name}", "ADD_DECK"
                )

        fresh = self._unconnected_sheets(url)
        if not fresh:
            StyledMessageBox.warning(
                self,
                "Already Registered",
                "Every sheet in this file is already connected.",
            )
            return

        parent_name = DEFAULT_PARENT_DECK_NAME
        file_name = DeckNameManager.resolve_remote_name_conflict(
            url, self.suggested_name
        )

        self._show_progress(True)
        self.add_button.setEnabled(False)
        self.add_button.setText("Adding...")

        added = []
        try:
            for offer in fresh:
                added.append(self._add_one_sheet(url, file_name, offer, parent_name))

            self.accept()

        except Exception as e:
            StyledMessageBox.critical(
                self,
                "Error Adding Deck",
                "An unexpected error occurred while adding the deck.",
                detailed_text=str(e),
            )
            self.add_button.setEnabled(True)
            self.add_button.setText("✓ Add Deck")
        finally:
            self._show_progress(False)

        self.added_urls = [u for u, _ in added]

    def _add_one_sheet(self, url, file_name, offer, parent_name):
        """Connects one sheet of the file as its own deck.

        The deck sits under the file it came from — ``Sheets2Anki::{file}::{sheet}``
        — so every sheet of one spreadsheet lands in one branch of the deck tree
        rather than scattered through it, and two files that happen to have a
        sheet called "vocab" do not collide.
        """
        from ..config_manager import create_deck_info
        from ..deck_manager import DeckNameManager
        from ..utils import url_for_sheet

        sheet_url = url_for_sheet(url, offer.name)
        remote_name = f"{file_name}::{offer.name}"
        full_name = f"{parent_name}::{remote_name}"

        deck_id, actual_name = get_or_create_deck(mw.col, full_name)

        add_remote_deck(
            sheet_url,
            create_deck_info(
                url=sheet_url,
                local_deck_id=deck_id,
                local_deck_name=actual_name,
                remote_deck_name=remote_name,
            ),
        )

        sync_result = DeckNameManager.sync_deck_with_config(sheet_url)
        if sync_result:
            _, synced_name = sync_result
            add_debug_message(
                f"Deck synchronized: {actual_name} → {synced_name}", "ADD_DECK"
            )

        try:
            from ..utils import apply_sheets2anki_options_to_deck

            apply_sheets2anki_options_to_deck(deck_id)
        except Exception as e:
            add_debug_message(f"Warning: Error applying options: {e}", "ADD_DECK")

        if is_deck_disconnected(sheet_url):
            from ..config_manager import reconnect_deck

            reconnect_deck(sheet_url)

        add_debug_message(f"Connected sheet '{offer.name}' as {actual_name}", "ADD_DECK")
        return sheet_url, actual_name

    def get_deck_info(self):
        """What was connected, so the caller can sync exactly those decks."""
        urls = getattr(self, "added_urls", [])
        if not urls:
            return None
        return {
            "url": urls[0],
            "urls": urls,
            "name": f"{len(urls)} decks" if len(urls) > 1 else urls[0],
            "is_automatic": True,
        }


def show_add_deck_dialog(parent=None):
    """
    Shows the dialog for adding a new remote deck.

    Args:
        parent: Parent widget for the dialog

    Returns:
        tuple: (success, deck_info)
    """
    dialog = AddDeckDialog(parent)

    if safe_exec(dialog) == DialogAccepted:
        return True, dialog.get_deck_info()

    return False, None
