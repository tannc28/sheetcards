"""
Dialog for configuring deck options management mode.

This module allows the user to choose between three modes:
1. Shared - All decks use "Sheets2Anki - Default Options"
2. Individual - Each deck has its own group "Sheets2Anki - [Name]"
3. Manual - No automatic application of options
"""

from ..compat import ButtonBox_Cancel
from ..compat import ButtonBox_Ok
from ..compat import DialogAccepted
from ..compat import QButtonGroup
from ..compat import QDialog
from ..compat import QDialogButtonBox
from ..compat import QGroupBox
from ..compat import QLabel
from ..compat import QVBoxLayout
from ..compat import safe_exec_dialog
from ..styled_messages import StyledMessageBox
from ..theme import MARGIN
from ..theme import SPACE_SECTION
from ..theme import get_colors
from ..theme import icon
from ..theme import make_radio_choice


class DeckOptionsConfigDialog(QDialog):
    """
    Dialog for configuring deck options management mode.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Deck Options Management")
        self.setMinimumSize(550, 500)
        self.resize(600, 550)

        # Get current mode
        from ..config_manager import get_deck_options_mode

        self.current_mode = get_deck_options_mode()

        self._setup_colors()
        self._setup_ui()
        self._connect_signals()

    def _setup_colors(self):
        """Sets up color scheme based on theme."""
        self.colors = get_colors()

    def _setup_ui(self):
        """A sentence, three choices, the buttons."""
        layout = QVBoxLayout(self)
        layout.setSpacing(SPACE_SECTION)
        layout.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)

        intro = QLabel(
            "Choose how Sheets2Anki should manage study settings for your decks."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.button_group = QButtonGroup()

        # Three exclusive choices in a group box, which is what a Qt window uses to
        # say "these three go together and one of them is on".
        choices = QGroupBox("Deck options")
        choices_layout = QVBoxLayout(choices)
        choices_layout.setSpacing(SPACE_SECTION)
        for index, (mode, title, description) in enumerate(
            (
                (
                    "shared",
                    "Shared options (recommended)",
                    "Every connected deck uses one settings group. Change it once "
                    "and the change reaches all of them.",
                ),
                (
                    "individual",
                    "Individual options",
                    "Each connected deck gets a settings group of its own, for when "
                    "one deck needs to be studied differently.",
                ),
                (
                    "manual",
                    "Manual",
                    "The add-on applies no settings at all. Each deck's options are "
                    "yours to set and yours to keep.",
                ),
            )
        ):
            choices_layout.addWidget(
                self._create_option_card(mode, title, description, index)
            )
        layout.addWidget(choices)

        layout.addStretch()

        self.button_box = QDialogButtonBox(ButtonBox_Ok | ButtonBox_Cancel)
        ok_button = self.button_box.button(ButtonBox_Ok)
        assert ok_button is not None  # just asked for, by name
        ok_button.setText("Apply")
        ok_button.setIcon(icon("success", "text"))
        ok_button.setDefault(True)
        self.ok_button = ok_button
        self.cancel_button = self.button_box.button(ButtonBox_Cancel)
        layout.addWidget(self.button_box)

    def _create_option_card(self, mode, title, description, button_id):
        """One radio button and the sentence under it."""
        return make_radio_choice(
            self.colors,
            key=mode,
            checked=self.current_mode == mode,
            title=title,
            description=description,
            button_group=self.button_group,
            button_id=button_id,
        )

    def _connect_signals(self):
        """Connects interface signals."""
        self.button_box.accepted.connect(self._apply_changes)
        self.button_box.rejected.connect(self.reject)

    def _apply_changes(self):
        """Applies configuration changes."""
        selected_id = self.button_group.checkedId()
        modes = ["shared", "individual", "manual"]

        if selected_id >= 0:
            new_mode = modes[selected_id]

            try:
                from ..config_manager import set_deck_options_mode

                set_deck_options_mode(new_mode)

                # Apply full automatic system
                from ..utils import apply_automatic_deck_options_system

                auto_result = apply_automatic_deck_options_system()

                # Feedback logic
                mode_names = {
                    "shared": "Shared Options",
                    "individual": "Individual Options",
                    "manual": "Manual Configuration",
                }

                info_text = ""
                message_type = StyledMessageBox.SUCCESS
                title = "Configuration Applied"
                main_text = f"Mode changed to: {mode_names[new_mode]}"

                if new_mode == "manual":
                    info_text = "Options will no longer be applied automatically. You have full control over deck settings."
                elif auto_result.get("success", False):
                    details = []
                    if auto_result.get("root_deck_updated", False):
                        details.append(
                            "Root deck configured with 'Sheets2Anki - Root Options'"
                        )
                    if auto_result.get("remote_decks_updated", 0) > 0:
                        deck_count = auto_result["remote_decks_updated"]
                        if new_mode == "individual":
                            details.append(
                                f"{deck_count} decks configured with individual options"
                            )
                        else:
                            details.append(
                                f"{deck_count} decks configured with 'Sheets2Anki - Default Options'"
                            )
                    if auto_result.get("cleaned_groups", 0) > 0:
                        details.append(
                            f"{auto_result['cleaned_groups']} orphaned groups removed"
                        )

                    if details:
                        info_text = "Automatic system applied:\n• " + "\n• ".join(
                            details
                        )
                    else:
                        if new_mode == "individual":
                            info_text = (
                                "Each new deck will have its own custom options group."
                            )
                        else:
                            info_text = "All decks will use 'Sheets2Anki - Default Options' group."

                    if auto_result.get("errors"):
                        errors_text = "\n".join(auto_result["errors"])
                        info_text += f"\n\nWarnings:\n{errors_text}"
                        message_type = StyledMessageBox.WARNING
                else:
                    info_text = f"Mode changed, but there were problems applying the settings: {auto_result.get('error', 'Unknown error')}"
                    message_type = StyledMessageBox.WARNING

                # Show message
                if message_type == StyledMessageBox.SUCCESS:
                    StyledMessageBox.success(
                        self, title, main_text, detailed_text=info_text
                    )
                else:
                    StyledMessageBox.warning(
                        self, title, main_text, detailed_text=info_text
                    )

                self.accept()

            except Exception as e:
                StyledMessageBox.critical(
                    self, "Error", "Error applying configuration", detailed_text=str(e)
                )


def show_deck_options_config_dialog(parent=None):
    """
    Utility function to show deck options configuration dialog.

    Args:
        parent: Parent widget (optional)

    Returns:
        bool: True if user accepted changes, False otherwise
    """
    dialog = DeckOptionsConfigDialog(parent)
    result = safe_exec_dialog(dialog)
    return result == DialogAccepted
