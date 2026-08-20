"""
Dialog for disconnecting remote decks.

This module provides an interface for the user
to select and disconnect multiple remote decks using checkboxes.
"""

from ..compat import ButtonBox_Cancel
from ..compat import ButtonBox_Ok
from ..compat import DialogAccepted
from ..compat import QCheckBox
from ..compat import QDialog
from ..compat import QDialogButtonBox
from ..compat import QHBoxLayout
from ..compat import QLabel
from ..compat import QPushButton
from ..compat import QScrollArea
from ..compat import Qt
from ..compat import QVBoxLayout
from ..compat import QWidget
from ..compat import mw
from ..compat import safe_exec
from ..config_manager import get_deck_local_name
from ..config_manager import get_deck_remote_name
from ..config_manager import get_remote_decks
from ..styled_messages import StyledMessageBox
from ..theme import ICON_SIZE
from ..theme import MARGIN
from ..theme import SPACE_ELEMENT
from ..theme import SPACE_SECTION
from ..theme import SPACE_TIGHT
from ..theme import get_colors
from ..theme import icon
from .url_helpers import copy_url_to_clipboard


class DisconnectDialog(QDialog):
    """
    Dialog for disconnecting remote decks with checkboxes.

    Allows multiple selection through checkboxes to disconnect
    multiple remote decks at the same time.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Disconnect Remote Decks")
        self.setModal(True)
        self.setMinimumWidth(750)
        self.setMinimumHeight(700)

        self.remote_decks = []
        self.deck_checkboxes = {}  # URL -> QCheckBox
        self.selected_urls = []

        # Define color scheme
        self._setup_colors()
        self._setup_ui()
        self._load_decks()
        self._connect_signals()

    def _setup_colors(self):
        """Sets up color scheme based on theme."""
        self.colors = get_colors()

    def _setup_ui(self):
        """The consequence, the list, the buttons."""
        layout = QVBoxLayout(self)
        layout.setSpacing(SPACE_SECTION)
        layout.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)

        # What disconnecting means, said once and in the colour it deserves. It
        # used to be a boxed banner with a 20pt emoji beside it and a two-pixel
        # border, above a window whose title already said Disconnect.
        warning_row = QHBoxLayout()
        warning_row.setSpacing(SPACE_TIGHT)
        warning_icon = QLabel()
        warning_icon.setFixedWidth(ICON_SIZE)
        warning_icon.setPixmap(
            icon("warning", "accent_warning").pixmap(ICON_SIZE, ICON_SIZE)
        )
        warning_text = QLabel(
            "The local decks stay in Anki, but they stop being read from your "
            "spreadsheet. Reconnecting means adding the link again."
        )
        warning_text.setWordWrap(True)
        warning_text.setStyleSheet(f"color: {self.colors['accent_warning']};")
        warning_row.addWidget(warning_icon)
        warning_row.addWidget(warning_text, 1)
        layout.addLayout(warning_row)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.checkboxes_widget = QWidget()
        self.checkboxes_layout = QVBoxLayout(self.checkboxes_widget)
        self.checkboxes_layout.setContentsMargins(
            SPACE_ELEMENT, SPACE_ELEMENT, SPACE_ELEMENT, SPACE_ELEMENT
        )
        self.checkboxes_layout.setSpacing(SPACE_ELEMENT)
        scroll_area.setWidget(self.checkboxes_widget)
        layout.addWidget(scroll_area, 1)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(SPACE_ELEMENT)
        self.select_all_button = QPushButton("Select All")
        self.select_all_button.setIcon(icon("success", "text_secondary"))
        self.select_all_button.setToolTip("Selects all decks for disconnection")
        self.select_none_button = QPushButton("Select None")
        self.select_none_button.setIcon(icon("error", "text_secondary"))
        self.select_none_button.setToolTip("Deselects all decks")
        self.invert_selection_button = QPushButton("Invert")
        self.invert_selection_button.setIcon(icon("sync", "text_secondary"))
        self.invert_selection_button.setToolTip("Inverts current selection")
        for button in (
            self.select_all_button,
            self.select_none_button,
            self.invert_selection_button,
        ):
            buttons_layout.addWidget(button)
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

        self.selection_info = QLabel("")
        self.selection_info.setStyleSheet(f"color: {self.colors['text_secondary']};")
        layout.addWidget(self.selection_info)

        # The one irreversible thing in the window. A checkbox in a red-bordered
        # tinted box shouted it; the icon beside it says the same thing at the
        # weight everything else in this window is said at, and the tooltip keeps
        # the detail.
        delete_row = QHBoxLayout()
        delete_row.setSpacing(SPACE_TIGHT)
        delete_icon = QLabel()
        delete_icon.setFixedWidth(ICON_SIZE)
        delete_icon.setPixmap(
            icon("warning", "accent_danger").pixmap(ICON_SIZE, ICON_SIZE)
        )
        self.delete_local_data_checkbox = QCheckBox(
            "Also delete the local decks, cards and note types"
        )
        self.delete_local_data_checkbox.setChecked(True)
        self.delete_local_data_checkbox.setToolTip(
            "This cannot be undone. Everything below the deck goes:\n"
            "• the deck and its subdecks\n"
            "• every card and note in them\n"
            "• the note types, unless another deck is using them"
        )
        self.delete_local_data_checkbox.setStyleSheet(
            f"color: {self.colors['accent_danger']};"
        )
        delete_row.addWidget(delete_icon)
        delete_row.addWidget(self.delete_local_data_checkbox, 1)
        layout.addLayout(delete_row)

        self.button_box = QDialogButtonBox(ButtonBox_Ok | ButtonBox_Cancel)
        disconnect_button = self.button_box.button(ButtonBox_Ok)
        assert disconnect_button is not None  # just asked for, by name
        disconnect_button.setText("Disconnect")
        disconnect_button.setIcon(icon("error", "text"))
        self.disconnect_button = disconnect_button
        self.cancel_button = self.button_box.button(ButtonBox_Cancel)
        # Not the default: pressing Enter in this window should not be how a deck
        # gets deleted.
        self.cancel_button.setDefault(True)
        layout.addWidget(self.button_box)

    def _connect_signals(self):
        """Connects interface signals."""
        # Bulk selection buttons
        self.select_all_button.clicked.connect(self._select_all)
        self.select_none_button.clicked.connect(self._select_none)
        self.invert_selection_button.clicked.connect(self._invert_selection)

        # Main buttons
        self.button_box.accepted.connect(self._disconnect_selected)
        self.button_box.rejected.connect(self.reject)

    def _load_decks(self):
        """Loads remote decks as checkboxes."""
        # Clear existing checkboxes
        for checkbox in self.deck_checkboxes.values():
            checkbox.setParent(None)
        self.deck_checkboxes.clear()
        self.remote_decks.clear()

        # Load remote decks
        remote_decks = get_remote_decks()

        if not remote_decks:
            # Show message if no decks
            no_decks_label = QLabel("No decks are connected.")
            no_decks_label.setStyleSheet(f"color: {self.colors['text_secondary']};")
            no_decks_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.checkboxes_layout.addWidget(no_decks_label)
            return

        for hash_key, deck_info in remote_decks.items():
            local_deck_id = deck_info["local_deck_id"]
            deck = None
            if mw.col and hasattr(mw.col, "decks"):
                deck = mw.col.decks.get(local_deck_id)

            # Get URL and remote deck name
            remote_deck_url = deck_info.get("remote_deck_url", "")
            remote_name = get_deck_remote_name(remote_deck_url) or "Remote Deck"

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(SPACE_ELEMENT)

            # Check if deck exists locally
            if deck and deck["name"].strip().lower() != "default":
                # Deck exists locally
                local_deck_name = deck["name"]
                card_count = 0
                if mw.col and hasattr(mw.col, "find_cards"):
                    escaped_deck_name = local_deck_name.replace('"', '\\"')
                    card_count = len(mw.col.find_cards(f'deck:"{escaped_deck_name}"'))

                checkbox_text = f"{remote_name}"
                checkbox = QCheckBox(checkbox_text)
                checkbox.setToolTip(
                    f"Remote deck: {remote_name}\nLocal deck: {local_deck_name}\nURL: {remote_deck_url}"
                )

                # Card count label
                count_label = QLabel(f"{card_count} cards")
                count_label.setStyleSheet(f"color: {self.colors['text_secondary']};")

                row_layout.addWidget(checkbox)
                row_layout.addWidget(count_label)

            else:
                # Deck was deleted locally
                local_deck_name = (
                    get_deck_local_name(remote_deck_url) or "Deleted Local Deck"
                )

                checkbox = QCheckBox(remote_name)
                checkbox.setToolTip(
                    f"Remote deck: {remote_name}\nLocal deck was deleted: {local_deck_name}\nConfiguration still exists.\nURL: {remote_deck_url}"
                )

                # Status label
                status_label = QLabel("Local deck already deleted")
                status_label.setStyleSheet(f"color: {self.colors['text_secondary']};")

                row_layout.addWidget(checkbox)
                row_layout.addWidget(status_label)
                card_count = 0

            # Copy URL button
            copy_button = QPushButton("Copy link")
            copy_button.clicked.connect(
                lambda checked, u=remote_deck_url: self._copy_url(u)
            )

            row_layout.addStretch()
            row_layout.addWidget(copy_button)

            # Add to main layout
            self.checkboxes_layout.addWidget(row_widget)

            # Store references
            self.deck_checkboxes[remote_deck_url] = checkbox
            self.remote_decks.append(
                {
                    "url": remote_deck_url,
                    "hash_key": hash_key,
                    "deck_info": deck_info,
                    "local_deck_name": (
                        local_deck_name
                        if deck
                        else get_deck_local_name(remote_deck_url)
                    ),
                    "remote_deck_name": remote_name,
                    "card_count": card_count if deck else 0,
                }
            )

            # Connect change signal
            checkbox.toggled.connect(
                lambda checked, u=remote_deck_url: self._on_checkbox_changed(u, checked)
            )

        # Add stretch at the end
        self.checkboxes_layout.addStretch()

        # Update information
        self._update_selection_info()

    def _copy_url(self, url):
        """Copies URL to clipboard and opens in browser"""
        copy_url_to_clipboard(url)

    def _on_checkbox_changed(self, url, checked):
        """Callback for when a checkbox is changed."""
        if checked:
            if url not in self.selected_urls:
                self.selected_urls.append(url)
        else:
            if url in self.selected_urls:
                self.selected_urls.remove(url)

        self._update_selection_info()

    def _select_all(self):
        """Selects all decks."""
        for url, checkbox in self.deck_checkboxes.items():
            checkbox.setChecked(True)

    def _select_none(self):
        """Deselects all decks."""
        for url, checkbox in self.deck_checkboxes.items():
            checkbox.setChecked(False)

    def _invert_selection(self):
        """Inverts current selection."""
        for url, checkbox in self.deck_checkboxes.items():
            checkbox.setChecked(not checkbox.isChecked())

    def _update_selection_info(self):
        """Updates selection information."""
        selected_count = len(self.selected_urls)
        total_count = len(self.deck_checkboxes)

        # A count, said once. It was a filled pill that went grey, then amber, then
        # red as more boxes were ticked — three colours for a number the reader can
        # see, in a window that already has one thing coloured for a reason.
        if not total_count:
            self.selection_info.setText("No connected decks")
        elif selected_count == total_count:
            self.selection_info.setText(f"All {total_count} decks selected")
        else:
            self.selection_info.setText(
                f"{selected_count} of {total_count} decks selected"
            )

        # Enable/disable disconnect button
        self.disconnect_button.setEnabled(selected_count > 0)

    def _disconnect_selected(self):
        """Disconnects selected decks."""
        if not self.selected_urls:
            return

        # Check if should delete local data
        delete_local_data = self.delete_local_data_checkbox.isChecked()

        # Show confirmation
        selected_count = len(self.selected_urls)

        if selected_count == 1:
            # Get deck name for confirmation
            deck_name = None
            for deck in self.remote_decks:
                if deck["url"] == self.selected_urls[0]:
                    # Use local_deck_name from new structure
                    deck_name = get_deck_local_name(deck["url"]) or deck.get(
                        "local_deck_name", "Deck"
                    )
                    break

            if delete_local_data:
                question_text = (
                    f"Disconnect deck '{deck_name}' and DELETE all local data?"
                )
            else:
                question_text = f"Disconnect deck '{deck_name}' from remote source?"
        else:
            if delete_local_data:
                question_text = (
                    f"Disconnect {selected_count} decks and DELETE all local data?"
                )
            else:
                question_text = (
                    f"Disconnect {selected_count} decks from their remote sources?"
                )

        detailed_text = ""
        if delete_local_data:
            detailed_text = (
                "⚠️ ATTENTION: ALL LOCAL DATA WILL BE PERMANENTLY DELETED!\n"
                "• Local decks and subdecks\n"
                "• All cards and notes\n"
                "• Specific note types (if not used in other decks)\n\n"
                "This action CANNOT be undone!"
            )
        else:
            detailed_text = (
                "This action cannot be undone. Local decks will remain in Anki."
            )

        if StyledMessageBox.question(
            self,
            "Confirm Disconnection",
            question_text,
            detailed_text=detailed_text,
            yes_text="Disconnect",
            no_text="Cancel",
            destructive=delete_local_data,
        ):
            self.accept()

    def get_selected_urls(self):
        """Returns selected URLs for disconnection."""
        return self.selected_urls

    def should_delete_local_data(self):
        """Returns whether to delete local data along with disconnection."""
        return self.delete_local_data_checkbox.isChecked()


def show_disconnect_dialog(parent=None):
    """
    Shows the remote deck disconnection dialog.

    Args:
        parent: Parent widget for the dialog

    Returns:
        tuple: (success, selected_urls, delete_local_data) where:
            - success: bool indicating if user confirmed
            - selected_urls: list of selected URLs
            - delete_local_data: bool indicating if should delete local data
    """
    dialog = DisconnectDialog(parent)

    if safe_exec(dialog) == DialogAccepted:
        return True, dialog.get_selected_urls(), dialog.should_delete_local_data()

    return False, [], False
