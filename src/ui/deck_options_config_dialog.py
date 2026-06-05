"""
Dialog for configuring deck options management mode.

This module allows the user to choose between three modes:
1. Shared - All decks use "Sheets2Anki - Default Options"
2. Individual - Each deck has its own group "Sheets2Anki - [Name]"
3. Manual - No automatic application of options
"""

from ..compat import DialogAccepted
from ..compat import QButtonGroup
from ..compat import QDialog
from ..compat import QHBoxLayout
from ..compat import QPushButton
from ..compat import QVBoxLayout
from ..compat import safe_exec_dialog
from ..styled_messages import StyledMessageBox
from ..theme import get_colors
from ..theme import make_header
from ..theme import make_radio_option_card


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
        self._apply_styles()
        self._connect_signals()

    def _setup_colors(self):
        """Sets up color scheme based on theme."""
        self.colors = get_colors()

    def _apply_styles(self):
        """Applies styles to the dialog."""
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colors['bg']};
                color: {self.colors['text']};
            }}
        """)

    def _setup_ui(self):
        """Sets up the dialog interface."""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header section
        layout.addWidget(
            make_header(
                self.colors,
                "Deck Options Management",
                "Choose how Sheets2Anki should manage study settings for your decks.",
            )
        )

        # Options section
        self.button_group = QButtonGroup()

        # Option 1: Shared
        shared_card = self._create_option_card(
            "shared",
            "Shared Options",
            "Recommended",
            "All remote decks use the same settings group. Configure once and all changes apply to all decks.",
            self.colors["accent_success"],
            0,
        )
        layout.addWidget(shared_card)

        # Option 2: Individual
        individual_card = self._create_option_card(
            "individual",
            "Individual Options",
            "Per Deck",
            "Each remote deck has its own settings group. Useful when decks have specific study needs.",
            self.colors["accent_primary"],
            1,
        )
        layout.addWidget(individual_card)

        # Option 3: Manual
        manual_card = self._create_option_card(
            "manual",
            "Manual Configuration",
            "Advanced",
            "The addon does not apply any settings automatically. Full control over each deck's options.",
            self.colors["accent_warning"],
            2,
        )
        layout.addWidget(manual_card)

        layout.addStretch()

        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 10, 0, 0)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['button_bg']};
                color: {self.colors['text']};
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
                padding: 12px 25px;
                font-size: 12pt;
            }}
            QPushButton:hover {{
                background-color: {self.colors['button_hover']};
            }}
        """)

        self.ok_button = QPushButton("✓ Apply")
        self.ok_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.colors['accent_success']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 25px;
                font-size: 12pt;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.colors['success_dark']};
            }}
        """)
        self.ok_button.setDefault(True)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.cancel_button)
        buttons_layout.addWidget(self.ok_button)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def _create_option_card(
        self, mode, title, badge, description, accent_color, button_id
    ):
        """Creates a styled option card."""
        return make_radio_option_card(
            self.colors,
            key=mode,
            checked=self.current_mode == mode,
            title=title,
            badge=badge,
            description=description,
            accent_color=accent_color,
            button_group=self.button_group,
            button_id=button_id,
        )

    def _connect_signals(self):
        """Connects interface signals."""
        self.ok_button.clicked.connect(self._apply_changes)
        self.cancel_button.clicked.connect(self.reject)

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
