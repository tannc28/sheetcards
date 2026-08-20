"""Which connected decks this sync should read.

The window is drawn the way Anki draws its own: a sentence, a list, the buttons.
Nothing here sets a background, a border or a radius — Anki styles every standard
widget through a global stylesheet, so the most native thing this file can do is
stay out of the way. The only rule it writes is a text colour, and that colour is
one of Anki's.
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
from ..compat import QVBoxLayout
from ..compat import QWidget
from ..compat import mw
from ..compat import safe_exec
from ..config_manager import get_active_decks
from ..config_manager import get_deck_local_name
from ..config_manager import get_deck_remote_name
from ..theme import MARGIN
from ..theme import SPACE_ELEMENT
from ..theme import SPACE_SECTION
from ..theme import get_colors
from .url_helpers import copy_url_to_clipboard


class SyncDialog(QDialog):
    """
    Dialog for synchronizing active decks with checkboxes.

    Allows multiple selection through checkboxes and maintains
    persistent selection between sessions.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Synchronize Decks")
        self.setModal(True)
        # Sized like one of Anki's own dialogs rather than to fill the screen: the
        # list is the only thing here that wants room, and it scrolls.
        self.setMinimumSize(520, 420)
        self.resize(600, 480)

        self.active_decks = []
        self.deck_checkboxes = {}  # hash_key -> QCheckBox
        self.deck_hash_mapping = {}  # URL -> hash_key (for compatibility)

        self._setup_colors()
        self._setup_ui()
        self._load_decks()
        self._load_persistent_selection()
        self._connect_signals()

    def _setup_colors(self):
        """Sets up color scheme based on theme."""
        self.colors = get_colors()

    def _setup_ui(self):
        """A sentence, the list, the buttons — Anki's own shape for a dialog."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)
        layout.setSpacing(SPACE_SECTION)

        intro = QLabel(
            "Choose which connected decks to read again. "
            "Your choice is remembered for next time."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        # A plain scroll area. The rows inside it are checkboxes, so the list looks
        # like Anki's own lists without being told to.
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

        # The three bulk actions read as verbs, without a tick or a cross in front
        # of them: no button in Anki carries a glyph, and these were the loudest
        # thing in the window.
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(SPACE_ELEMENT)
        self.select_all_button = QPushButton("Select All")
        self.select_all_button.setToolTip("Selects all decks for synchronization")
        self.select_none_button = QPushButton("Select None")
        self.select_none_button.setToolTip("Deselects all decks")
        self.invert_selection_button = QPushButton("Invert")
        self.invert_selection_button.setToolTip("Inverts current selection")
        for button in (
            self.select_all_button,
            self.select_none_button,
            self.invert_selection_button,
        ):
            buttons_layout.addWidget(button)
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

        # A count, in the colour Anki uses for a remark. It was a filled pill of
        # white-on-green, which is how a status line ends up louder than the list
        # it is counting.
        self.selection_info = QLabel("")
        self.selection_info.setStyleSheet(f"color: {self.colors['text_secondary']};")
        layout.addWidget(self.selection_info)

        # A button box rather than two buttons in a row: it is what puts OK and
        # Cancel in the order this platform puts them in, which is the one thing a
        # hand-built row of buttons can never get right on every machine at once.
        self.button_box = QDialogButtonBox(ButtonBox_Ok | ButtonBox_Cancel)
        sync_button = self.button_box.button(ButtonBox_Ok)
        assert sync_button is not None  # just asked for, by name
        sync_button.setText("Synchronize")
        sync_button.setDefault(True)
        self.sync_button = sync_button
        self.cancel_button = self.button_box.button(ButtonBox_Cancel)
        layout.addWidget(self.button_box)

    def _connect_signals(self):
        """Connects interface signals."""
        # Bulk selection buttons
        self.select_all_button.clicked.connect(self._select_all)
        self.select_none_button.clicked.connect(self._select_none)
        self.invert_selection_button.clicked.connect(self._invert_selection)

        self.button_box.accepted.connect(self._sync_selected)
        self.button_box.rejected.connect(self.reject)

    def _load_decks(self):
        """Loads active decks as checkboxes."""
        # Clear existing checkboxes
        for checkbox in self.deck_checkboxes.values():
            checkbox.setParent(None)
        self.deck_checkboxes.clear()
        self.active_decks.clear()

        # Load active decks
        active_decks = get_active_decks()

        for hash_key, deck_info in active_decks.items():
            local_deck_id = deck_info["local_deck_id"]
            remote_deck_url = deck_info.get("remote_deck_url", "")
            deck = None
            if mw and hasattr(mw, "col") and mw.col and hasattr(mw.col, "decks"):
                deck = mw.col.decks.get(local_deck_id)

            # Get remote deck name
            remote_name = get_deck_remote_name(remote_deck_url) or "Remote Deck"

            # One row, drawn as nothing: a widget holding a checkbox, a count and a
            # button. It was a rounded card with a hover tint, which made a list of
            # three decks look like a pricing page.
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(SPACE_ELEMENT)

            # Check if deck exists locally
            if deck and deck["name"].strip().lower() != "default":
                # Deck exists locally
                local_deck_name = deck["name"]
                card_count = 0
                if (
                    mw
                    and hasattr(mw, "col")
                    and mw.col
                    and hasattr(mw.col, "find_cards")
                ):
                    escaped_deck_name = local_deck_name.replace('"', '\\"')
                    card_count = len(mw.col.find_cards(f'deck:"{escaped_deck_name}"'))

                checkbox_text = f"{remote_name}"
                checkbox = QCheckBox(checkbox_text)
                checkbox.setToolTip(
                    f"Remote deck: {remote_name}\nLocal deck: {local_deck_name}\nURL: {remote_deck_url}"
                )

                count_label = QLabel(f"{card_count} cards")
                count_label.setStyleSheet(f"color: {self.colors['text_secondary']};")

                row_layout.addWidget(checkbox)
                row_layout.addWidget(count_label)

            else:
                # Deck was deleted locally, but can be recreated
                local_deck_name = (
                    get_deck_local_name(remote_deck_url) or "Deleted Local Deck"
                )

                checkbox = QCheckBox(remote_name)
                checkbox.setToolTip(
                    f"Remote deck: {remote_name}\nLocal deck was deleted: {local_deck_name}\nWill be recreated during synchronization.\nURL: {remote_deck_url}"
                )

                # The one thing in the list that is not routine, so it is the one
                # thing that is not the colour of the text around it.
                warning_label = QLabel("Will be recreated")
                warning_label.setStyleSheet(f"color: {self.colors['accent_warning']};")

                row_layout.addWidget(checkbox)
                row_layout.addWidget(warning_label)
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
            self.deck_checkboxes[hash_key] = checkbox
            self.deck_hash_mapping[remote_deck_url] = hash_key
            self.active_decks.append(
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
                    "card_count": card_count,
                }
            )

            # Connect change signal
            checkbox.toggled.connect(
                lambda checked, hk=hash_key: self._on_checkbox_changed(hk, checked)
            )

        # Add stretch at the end
        self.checkboxes_layout.addStretch()

        # Update information
        self._update_selection_info()

    def _load_persistent_selection(self):
        """Loads saved persistent selection based on is_sync from meta.json."""
        from ..config_manager import get_meta

        meta = get_meta()
        decks = meta.get("decks", {})

        # Apply saved selection to checkboxes based on each deck's is_sync
        for hash_key, checkbox in self.deck_checkboxes.items():
            deck_info = decks.get(hash_key, {})
            is_selected = deck_info.get("is_sync", True)  # Default: True
            checkbox.setChecked(is_selected)

        self._update_selection_info()

    def _on_checkbox_changed(self, hash_key, checked):
        """Callback for when a checkbox is changed."""
        from ..config_manager import get_meta
        from ..config_manager import save_meta

        # Update is_sync in meta.json
        meta = get_meta()
        if "decks" not in meta:
            meta["decks"] = {}

        if hash_key in meta["decks"]:
            meta["decks"][hash_key]["is_sync"] = checked
            save_meta(meta)

        self._update_selection_info()

    def _select_all(self):
        """Selects all decks."""
        for hash_key, checkbox in self.deck_checkboxes.items():
            checkbox.setChecked(True)

    def _select_none(self):
        """Deselects all decks."""
        for hash_key, checkbox in self.deck_checkboxes.items():
            checkbox.setChecked(False)

    def _invert_selection(self):
        """Inverts current selection."""
        for hash_key, checkbox in self.deck_checkboxes.items():
            checkbox.setChecked(not checkbox.isChecked())

    def _update_selection_info(self):
        """Updates selection information."""
        # Count selections based on checkboxes
        selected_count = sum(
            1 for checkbox in self.deck_checkboxes.values() if checkbox.isChecked()
        )
        total_count = len(self.deck_checkboxes)

        # A count, said once. Three different colours of filled pill for "none",
        # "some" and "all" was three ways of saying a number the reader can see.
        if not total_count:
            self.selection_info.setText("No connected decks")
        elif selected_count == total_count:
            self.selection_info.setText(f"All {total_count} decks selected")
        else:
            self.selection_info.setText(
                f"{selected_count} of {total_count} decks selected"
            )

        # Enable/disable sync button
        self.sync_button.setEnabled(selected_count > 0)

    def _copy_url(self, url):
        """
        Copies clean URL to clipboard.

        Args:
            url (str): Remote deck URL
        """
        copy_url_to_clipboard(url)

    def _sync_selected(self):
        """Synchronizes selected decks."""
        # Collect selected URLs based on checkboxes
        selected_urls = []
        for hash_key, checkbox in self.deck_checkboxes.items():
            if checkbox.isChecked():
                # Find corresponding URL for hash_key
                for deck_info in self.active_decks:
                    if deck_info["hash_key"] == hash_key:
                        selected_urls.append(deck_info["url"])
                        break

        # Store selected URLs for later use
        self.selected_urls = selected_urls

        self.accept()

    def get_selected_urls(self):
        """Returns selected URLs for synchronization."""
        return getattr(self, "selected_urls", [])


def show_sync_dialog(parent=None):
    """
    Shows the synchronization dialog.

    Args:
        parent: Parent widget for the dialog

    Returns:
        tuple: (success, selected_urls) where success is bool and selected_urls is list
    """
    dialog = SyncDialog(parent)

    if safe_exec(dialog) == DialogAccepted:
        return True, dialog.get_selected_urls()

    return False, []
