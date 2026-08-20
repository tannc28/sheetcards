"""
Enhanced dialog for adding new remote decks.

This module provides a modern, user-friendly interface for adding decks
with support for automatic naming and conflict resolution.
"""

from ..compat import ButtonBox_Cancel
from ..compat import ButtonBox_Ok
from ..compat import DialogAccepted
from ..compat import QDialog
from ..compat import QDialogButtonBox
from ..compat import QGroupBox
from ..compat import QHBoxLayout
from ..compat import QLabel
from ..compat import QLineEdit
from ..compat import QProgressBar
from ..compat import QTimer
from ..compat import QVBoxLayout
from ..compat import QWidget
from ..compat import TextSelectableByMouse
from ..compat import mw
from ..compat import safe_exec
from ..config_manager import add_remote_deck
from ..config_manager import get_remote_decks
from ..config_manager import is_deck_disconnected
from ..data_processor import RemoteDeckError
from ..data_processor import read_all_sheets
from ..styled_messages import StyledMessageBox
from ..theme import ICON_SIZE
from ..theme import MARGIN
from ..theme import SPACE_ELEMENT
from ..theme import SPACE_SECTION
from ..theme import SPACE_TIGHT
from ..theme import get_colors
from ..theme import icon
from ..tsv_model import deck_root_name
from ..utils import add_debug_message
from ..utils import get_or_create_deck
from ..utils import is_google_sheets_url
from ..utils import is_spreadsheet_file_url
from ..utils import source_id
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

        self._setup_ui()
        self._connect_signals()
        self._adjust_dialog_size()

    def _setup_ui(self):
        """A link, then what it turned out to be, then the buttons.

        Two group boxes and nothing else: no banner, no numbered steps, no cards.
        Anki styles a QGroupBox, a QLineEdit and a QProgressBar itself, so none of
        them is told anything here.
        """
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(SPACE_SECTION)
        main_layout.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)

        main_layout.addWidget(self._create_step1_section())

        self.step2_group = self._create_step2_section()
        self.step2_group.setVisible(False)
        main_layout.addWidget(self.step2_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        main_layout.addWidget(self.progress_bar)

        main_layout.addStretch()
        main_layout.addWidget(self._create_buttons())

    def _create_step1_section(self):
        """The link, and how to get one."""
        group = QGroupBox("Spreadsheet link")
        layout = QVBoxLayout(group)
        layout.setSpacing(SPACE_ELEMENT)

        # Instructions read as a remark under the field rather than as a tip in a
        # tinted box with a lightbulb on it.
        help_text = QLabel(
            "Open your spreadsheet, click <b>Share</b> and set access to "
            "<b>Anyone with the link</b>, then copy the address from your browser. "
            "A link ending in <b>.xlsx</b> or <b>.xlsm</b> — in a GitHub repository "
            "or on any https host — is read the same way."
        )
        help_text.setWordWrap(True)
        help_text.setStyleSheet(f"color: {self.colors['text_secondary']};")
        layout.addWidget(help_text)

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText(
            "https://docs.google.com/spreadsheets/d/…  or  https://…/deck.xlsx"
        )
        layout.addWidget(self.url_edit)

        # What the link turned out to be, in the colour that says how it went. The
        # coloured circle that used to sit beside the field said the same thing a
        # second time, in emoji.
        status_row = QHBoxLayout()
        status_row.setSpacing(SPACE_TIGHT)
        self.status_icon = QLabel()
        self.status_icon.setFixedWidth(ICON_SIZE)
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(f"color: {self.colors['text_secondary']};")
        status_row.addWidget(self.status_icon)
        status_row.addWidget(self.status_label, 1)
        layout.addLayout(status_row)

        return group

    def _create_step2_section(self):
        """What the link turned out to hold, and what it will be called."""
        group = QGroupBox("Deck")
        layout = QVBoxLayout(group)
        layout.setSpacing(SPACE_ELEMENT)

        # Four numbers, as a sentence. They were four tinted cards with an emoji
        # each — 📝 🎯 🫥 👻 — which is a dashboard in a window that is asking one
        # question.
        self.stats_label = QLabel("")
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet(f"color: {self.colors['text_secondary']};")
        layout.addWidget(self.stats_label)

        conflict_row = QHBoxLayout()
        conflict_row.setSpacing(SPACE_TIGHT)
        self.conflict_icon = QLabel()
        self.conflict_icon.setFixedWidth(ICON_SIZE)
        self.conflict_icon.setPixmap(
            icon("warning", "warning").pixmap(ICON_SIZE, ICON_SIZE)
        )
        self.conflict_warning = QLabel("")
        self.conflict_warning.setWordWrap(True)
        self.conflict_warning.setStyleSheet(f"color: {self.colors['warning']};")
        conflict_row.addWidget(self.conflict_icon)
        conflict_row.addWidget(self.conflict_warning, 1)
        self.conflict_row_widget = QWidget()
        self.conflict_row_widget.setLayout(conflict_row)
        self.conflict_row_widget.setVisible(False)
        layout.addWidget(self.conflict_row_widget)

        name_label = QLabel("Will be created as:")
        name_label.setStyleSheet(f"color: {self.colors['text_secondary']};")
        layout.addWidget(name_label)

        # A deck name is a string out of a spreadsheet, so it is set in the face
        # Anki sets a name in, not in a filled blue box.
        self.name_preview = QLabel("")
        self.name_preview.setWordWrap(True)
        self.name_preview.setTextInteractionFlags(TextSelectableByMouse)
        layout.addWidget(self.name_preview)

        return group

    def _create_buttons(self):
        """OK and Cancel, in this platform's order."""
        self.button_box = QDialogButtonBox(ButtonBox_Ok | ButtonBox_Cancel)
        add_button = self.button_box.button(ButtonBox_Ok)
        assert add_button is not None  # just asked for, by name
        add_button.setText("Add Deck")
        add_button.setIcon(icon("plus", "text"))
        add_button.setEnabled(False)
        add_button.setDefault(True)
        self.add_button = add_button
        self.cancel_button = self.button_box.button(ButtonBox_Cancel)
        return self.button_box

    def _connect_signals(self):
        """Connects interface signals."""
        self.validation_timer.setSingleShot(True)
        self.validation_timer.timeout.connect(self._validate_url_auto)

        self.url_edit.textChanged.connect(self._on_url_changed)
        self.button_box.accepted.connect(self._add_deck)
        self.button_box.rejected.connect(self.reject)

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
            # the bare source id, so that is still a duplicate of this file.
            # `source_id` rather than the spreadsheet id: a file at a plain
            # address has no spreadsheet id, and asking for one raised — which
            # read here as "not a duplicate" and offered to connect it twice.
            file_id = source_id(url)
            remote_decks = get_remote_decks()
            if file_id in remote_decks:
                deck_info = remote_decks[file_id]
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

        # A deck's source is a Google Sheet *or* a spreadsheet file at a plain
        # address. This gate used to test for the Google host alone, which made
        # the file source unreachable from the one dialog that connects a deck —
        # the whole feature existed and could not be typed in.
        if not is_google_sheets_url(url) and not is_spreadsheet_file_url(url):
            self._show_status(
                "Paste a Google Sheets link, or a link ending in .xlsx or .xlsm",
                "error",
            )
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
                skipped = (
                    "; ".join(f"{o.name}: {o.problem}" for o in self.offers)
                    or "the file has no sheets in it"
                )
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
        """Says how the link went, in one line and one colour.

        There used to be an emoji per state in a tinted circle beside the field —
        ⚪ 🔄 ✅ ⚠️ ❌ — saying in pictures what the sentence beside it already
        said in words. The sentence is what a reader reads.
        """
        shape, colour = {
            "waiting": (None, "text_secondary"),
            "validating": ("sync", "text_secondary"),
            "success": ("success", "success"),
            "warning": ("warning", "warning"),
            "error": ("error", "error"),
        }.get(status_type, ("info", "text_secondary"))

        if shape:
            self.status_icon.setPixmap(icon(shape, colour).pixmap(ICON_SIZE, ICON_SIZE))
        else:
            self.status_icon.clear()
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {self.colors[colour]};")

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

        deck_stats = self.remote_deck.get_statistics()
        rows = deck_stats.get("valid_note_lines", 0)
        notes = deck_stats.get("total_potential_anki_notes", 0)

        # The two numbers that answer "did it read the sheet". The other two are
        # only worth a clause, and only when they are not zero: a row count of 0
        # invalid and 0 ghost is a row count of nothing to say.
        summary = f"{rows} rows to sync, {notes} notes"
        aside = [
            f"{deck_stats.get(key, 0)} {word}"
            for key, word in (
                ("invalid_note_lines", "invalid"),
                ("ignored_ghost_rows", "ghost"),
            )
            if deck_stats.get(key, 0)
        ]
        if aside:
            summary += f" ({', '.join(aside)})"
        self.stats_label.setText(summary)

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

        # One deck per sheet, so the preview lists them rather than showing one
        # name that is not what any of the decks will be called.
        from ..utils import url_for_sheet

        usable = [o for o in self.offers if o.usable]
        if usable:
            names = [
                deck_root_name(
                    DeckNameManager.resolve_remote_name_conflict(
                        url_for_sheet(current_url, o.name),
                        f"{final_remote_name}::{DeckNameManager.clean_name(o.name)}",
                    )
                )
                for o in usable
            ]
            full_name = "\n".join(names)
        else:
            full_name = deck_root_name(final_remote_name)

        if final_remote_name != self.suggested_name:
            self.conflict_warning.setText(
                f"A deck called '{self.suggested_name}' is already connected, so "
                f"this one is named '{final_remote_name}'."
            )
            self.conflict_row_widget.setVisible(True)
        else:
            self.conflict_row_widget.setVisible(False)
        self.name_preview.setText(full_name)

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
                detailed_text="The URL needs to be checked to ensure it points to a spreadsheet this add-on can read.",
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

        file_name = DeckNameManager.resolve_remote_name_conflict(
            url, self.suggested_name
        )

        self._show_progress(True)
        self.add_button.setEnabled(False)
        self.add_button.setText("Adding...")

        added = []
        try:
            for offer in fresh:
                added.append(self._add_one_sheet(url, file_name, offer))

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

    def _add_one_sheet(self, url, file_name, offer):
        """Connects one sheet of the file as its own deck: ``s2a_{file}::{sheet}``."""
        from ..config_manager import create_deck_info
        from ..deck_manager import DeckNameManager
        from ..utils import url_for_sheet

        sheet_url = url_for_sheet(url, offer.name)
        remote_name = DeckNameManager.resolve_remote_name_conflict(
            sheet_url, f"{file_name}::{DeckNameManager.clean_name(offer.name)}"
        )
        full_name = deck_root_name(remote_name)

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

        add_debug_message(
            f"Connected sheet '{offer.name}' as {actual_name}", "ADD_DECK"
        )
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
