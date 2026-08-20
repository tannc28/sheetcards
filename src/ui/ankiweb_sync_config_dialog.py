"""
Dialog for configuring automatic synchronization with AnkiWeb.

This module allows the user to choose between two synchronization modes:
1. Disabled - No automatic synchronization
2. Sync - Execute sync after deck synchronization
"""

from ..compat import ButtonBox_Cancel
from ..compat import ButtonBox_Ok
from ..compat import ButtonRole_Action
from ..compat import DialogAccepted
from ..compat import QButtonGroup
from ..compat import QDialog
from ..compat import QDialogButtonBox
from ..compat import QGroupBox
from ..compat import QLabel
from ..compat import QPushButton
from ..compat import QVBoxLayout
from ..compat import safe_exec_dialog
from ..styled_messages import StyledMessageBox
from ..theme import MARGIN
from ..theme import SPACE_SECTION
from ..theme import get_colors
from ..theme import icon
from ..theme import make_radio_choice


class AnkiWebSyncConfigDialog(QDialog):
    """
    Dialog for configuring automatic synchronization with AnkiWeb.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure AnkiWeb Synchronization")
        self.setMinimumSize(550, 550)
        self.resize(600, 600)

        # Get current settings
        from ..config_manager import get_ankiweb_sync_mode

        self.current_mode = get_ankiweb_sync_mode()

        self._setup_colors()
        self._setup_ui()
        self._connect_signals()

    def _setup_colors(self):
        """Sets up color scheme based on theme."""
        self.colors = get_colors()

    def _setup_ui(self):
        """A sentence, two choices, the buttons."""
        layout = QVBoxLayout(self)
        layout.setSpacing(SPACE_SECTION)
        layout.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)

        intro = QLabel(
            "What should happen after Sheets2Anki finishes reading your sheets."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.mode_group = QButtonGroup()

        choices = QGroupBox("After a sync")
        choices_layout = QVBoxLayout(choices)
        choices_layout.setSpacing(SPACE_SECTION)
        for index, (mode, title, description) in enumerate(
            (
                (
                    "none",
                    "Do nothing",
                    "Your collection is uploaded when you sync it yourself, from "
                    "Anki's own Sync button.",
                ),
                (
                    "sync",
                    "Sync with AnkiWeb",
                    "Upload to AnkiWeb as soon as the decks have been read, so the "
                    "new cards are on your phone before you pick it up.",
                ),
            )
        ):
            choices_layout.addWidget(
                self._create_mode_card(mode, title, description, index)
            )
        layout.addWidget(choices)

        layout.addStretch()

        # Test Connection is not an OK and not a Cancel, so it goes in the box's
        # action role rather than being a third button loose beside them.
        self.button_box = QDialogButtonBox(ButtonBox_Ok | ButtonBox_Cancel)
        self.test_button = QPushButton("Test connection")
        self.test_button.setIcon(icon("sync", "text_secondary"))
        self.button_box.addButton(self.test_button, ButtonRole_Action)

        save_button = self.button_box.button(ButtonBox_Ok)
        assert save_button is not None  # just asked for, by name
        save_button.setText("Save")
        save_button.setIcon(icon("success", "text"))
        save_button.setDefault(True)
        self.save_button = save_button
        self.cancel_button = self.button_box.button(ButtonBox_Cancel)
        layout.addWidget(self.button_box)

    def _create_mode_card(self, mode, title, description, button_id):
        """One radio button and the sentence under it."""
        return make_radio_choice(
            self.colors,
            key=mode,
            checked=self.current_mode == mode,
            title=title,
            description=description,
            button_group=self.mode_group,
            button_id=button_id,
        )

    def _connect_signals(self):
        """The box's two roles, and the third button's own click."""
        self.button_box.accepted.connect(self._save_settings)
        self.button_box.rejected.connect(self.reject)
        self.test_button.clicked.connect(self._test_connection)

    def _test_connection(self):
        """Tests connection with AnkiWeb."""
        try:
            from ..ankiweb_sync import get_sync_status
            from ..ankiweb_sync import test_ankiweb_connection

            self.test_button.setText("Testing...")
            self.test_button.setEnabled(False)

            result = test_ankiweb_connection()

            if result["success"]:
                StyledMessageBox.success(
                    self, "Connection Successful", result["message"]
                )
            else:
                status = get_sync_status()
                debug_info = status.get("debug_info", {})

                error_msg = f"{result['error']}\n\n"
                error_msg += "Diagnostic information:\n"
                error_msg += f"• Sync system available: {debug_info.get('has_sync_system', 'N/A')}\n"
                error_msg += (
                    f"• Sync key present: {debug_info.get('has_sync_key', 'N/A')}\n"
                )
                error_msg += (
                    f"• Valid profile: {debug_info.get('has_profile', 'N/A')}\n"
                )
                error_msg += f"• Profile syncKey: {debug_info.get('has_profile_synckey', 'N/A')}\n"
                error_msg += f"• Profile syncUser: {debug_info.get('has_profile_syncuser', 'N/A')}\n"

                StyledMessageBox.warning(
                    self,
                    "Connection Failed",
                    "Connection test failed",
                    detailed_text=error_msg,
                )

        except Exception as e:
            StyledMessageBox.warning(
                self, "Error", f"Error testing connection: {str(e)}"
            )
        finally:
            self.test_button.setText("Test Connection")
            self.test_button.setEnabled(True)

    def _save_settings(self):
        """Saves settings and closes dialog."""
        try:
            from ..config_manager import set_ankiweb_sync_config

            mode_map = {0: "none", 1: "sync"}
            selected_mode = mode_map[self.mode_group.checkedId()]

            set_ankiweb_sync_config(selected_mode)

            self.accept()

        except Exception as e:
            StyledMessageBox.warning(self, "Error", f"Error saving settings: {str(e)}")

    @staticmethod
    def show_config_dialog():
        """
        Static method to show the configuration dialog.

        Returns:
            bool: True if user saved settings, False if cancelled
        """
        dialog = AnkiWebSyncConfigDialog()
        return safe_exec_dialog(dialog) == DialogAccepted


# Convenience function for external use
def show_ankiweb_sync_config():
    """Shows the AnkiWeb synchronization configuration dialog."""
    return AnkiWebSyncConfigDialog.show_config_dialog()
