"""
Dialog for configuring timer position on cards.

This module allows the user to choose between three timer positions:
1. Top Middle - Timer at top center of card
2. Between Sections - Timer between CONTEXT and CARD sections
3. Hidden - Timer disabled
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
from ..theme import primary_button_qss
from ..theme import secondary_button_qss


class TimerConfigDialog(QDialog):
    """
    Dialog for configuring timer position on cards.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configure Timer Position")
        self.setMinimumSize(500, 450)
        self.resize(550, 480)

        # Get current position
        from ..config_manager import get_timer_position

        self.current_position = get_timer_position()

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
                "Timer Position",
                "Choose where the review timer appears on your cards.",
            )
        )

        # Options section
        self.button_group = QButtonGroup()

        # Option 1: Top Middle
        top_middle_card = self._create_option_card(
            "top_middle",
            "Top Middle",
            "Fixed",
            "Timer appears fixed at the top center of the screen, always visible.",
            self.colors["accent_primary"],
            0,
        )
        layout.addWidget(top_middle_card)

        # Option 2: Between Sections
        between_sections_card = self._create_option_card(
            "between_sections",
            "Between Sections",
            "Default",
            "Timer appears between CONTEXT and CARD sections, flows with content.",
            self.colors["accent_success"],
            1,
        )
        layout.addWidget(between_sections_card)

        # Option 3: Hidden
        hidden_card = self._create_option_card(
            "hidden",
            "Hidden",
            "Disabled",
            "Timer is completely disabled. No timer will be shown on cards.",
            self.colors["accent_warning"],
            2,
        )
        layout.addWidget(hidden_card)

        layout.addStretch()

        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setContentsMargins(0, 10, 0, 0)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet(secondary_button_qss(self.colors))

        self.ok_button = QPushButton("✓ Apply")
        self.ok_button.setStyleSheet(primary_button_qss(self.colors, "success"))
        self.ok_button.setDefault(True)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.cancel_button)
        buttons_layout.addWidget(self.ok_button)

        layout.addLayout(buttons_layout)
        self.setLayout(layout)

    def _create_option_card(
        self, position, title, badge, description, accent_color, button_id
    ):
        """Creates a styled option card."""
        return make_radio_option_card(
            self.colors,
            key=position,
            checked=self.current_position == position,
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
        positions = ["top_middle", "between_sections", "hidden"]

        if selected_id >= 0:
            new_position = positions[selected_id]

            try:
                from ..config_manager import set_timer_position

                set_timer_position(new_position)

                # Feedback
                position_names = {
                    "top_middle": "Top Middle",
                    "between_sections": "Between Sections",
                    "hidden": "Hidden (Disabled)",
                }

                StyledMessageBox.success(
                    self,
                    "Timer Position Updated",
                    f"Timer position changed to: {position_names[new_position]}",
                    detailed_text="Run a sync (Ctrl+Shift+S) to update card templates with the new timer position.",
                )

                self.accept()

            except Exception as e:
                StyledMessageBox.critical(
                    self, "Error", "Error applying configuration", detailed_text=str(e)
                )


def show_timer_config_dialog(parent=None):
    """
    Utility function to show timer configuration dialog.

    Args:
        parent: Parent widget (optional)

    Returns:
        bool: True if user accepted changes, False otherwise
    """
    dialog = TimerConfigDialog(parent)
    result = safe_exec_dialog(dialog)
    return result == DialogAccepted
