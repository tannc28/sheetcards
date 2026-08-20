"""
Styled message boxes for SheetCards.

This module provides a consistent, beautiful UI for alerts and messages,
matching the application's design system.
"""

from .compat import AlignCenter
from .compat import AlignLeft
from .compat import QDialog
from .compat import QHBoxLayout
from .compat import QLabel
from .compat import QPushButton
from .compat import Qt
from .compat import QVBoxLayout
from .compat import QWidget

# The color palette now lives in the shared design-system module (src/theme.py); the
# canonical token values are preserved there, so message boxes render unchanged.
try:
    from .theme import get_colors
except ImportError:  # pragma: no cover - direct-import fallback for tests
    from theme import get_colors


class StyledMessageBox(QDialog):
    """
    A custom, styled message box to replace standard QMessageBox.
    Supports Info, Warning, Error, Question types.
    """

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    QUESTION = "question"
    SUCCESS = "success"

    def __init__(
        self,
        parent=None,
        title="",
        text="",
        message_type=INFO,
        buttons=None,
        detailed_text="",
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setMaximumWidth(550)

        self.colors = get_colors()
        self.message_type = message_type

        self._setup_styles()
        self._setup_ui(title, text, detailed_text, buttons)

    def _setup_styles(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colors['background']};
            }}
            QLabel {{
                color: {self.colors['text_primary']};
            }}
        """)

    def _get_icon_and_color(self):
        if self.message_type == self.INFO:
            return "ℹ️", self.colors["primary"], self.colors["primary_light"]
        elif self.message_type == self.WARNING:
            return "⚠️", self.colors["warning"], self.colors["warning_light"]
        elif self.message_type == self.ERROR:
            return "❌", self.colors["error"], self.colors["error_light"]
        elif self.message_type == self.QUESTION:
            return "❓", self.colors["primary"], self.colors["primary_light"]
        elif self.message_type == self.SUCCESS:
            return "✅", self.colors["success"], self.colors["success_light"]
        return "ℹ️", self.colors["text_secondary"], self.colors["background_secondary"]

    def _setup_ui(self, title, text, detailed_text, buttons):
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # === Header Area with Icon ===
        header_widget = QWidget()
        header_widget.setObjectName("msgHeader")
        icon_char, type_color, type_bg = self._get_icon_and_color()
        header_widget.setStyleSheet(f"""
            QWidget#msgHeader {{
                background-color: {type_bg};
                border-bottom: 1px solid {self.colors['border_light']};
            }}
        """)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(24, 20, 24, 20)
        header_layout.setSpacing(16)

        # Icon
        icon_label = QLabel(icon_char)
        icon_label.setStyleSheet("""
            font-size: 32px;
            background: transparent;
        """)
        icon_label.setAlignment(AlignCenter)
        header_layout.addWidget(icon_label)

        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {self.colors['text_primary']};
            background: transparent;
        """)
        title_label.setWordWrap(True)
        header_layout.addWidget(title_label, 1)  # Stretch to fill

        layout.addWidget(header_widget)

        # === Content Area ===
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(16)

        # Main Text
        text_label = QLabel(text)
        text_label.setStyleSheet(f"""
            font-size: 14px;
            color: {self.colors['text_primary']};
            line-height: 1.4;
        """)
        text_label.setWordWrap(True)
        content_layout.addWidget(text_label)

        # Detailed Text (if any)
        if detailed_text:
            # Use a container for the background and padding to avoid QLabel clipping issues
            detail_container = QWidget()
            detail_container.setObjectName("detailContainer")
            detail_container.setStyleSheet(f"""
                QWidget#detailContainer {{
                    background-color: {self.colors['background_secondary']};
                    border-radius: 6px;
                }}
            """)

            container_layout = QVBoxLayout(detail_container)
            container_layout.setContentsMargins(12, 12, 12, 12)
            container_layout.setSpacing(0)

            detail_label = QLabel(detailed_text)
            detail_label.setStyleSheet(f"""
                font-size: 12px;
                color: {self.colors['text_secondary']};
                background: transparent;
                border: none;
            """)
            detail_label.setWordWrap(True)
            detail_label.setAlignment(AlignLeft | Qt.AlignmentFlag.AlignTop)

            container_layout.addWidget(detail_label)
            content_layout.addWidget(detail_container)

        layout.addWidget(content_widget)

        # === Buttons Area ===
        button_widget = QWidget()
        button_widget.setObjectName("msgButtonBar")
        button_widget.setStyleSheet(f"""
            QWidget#msgButtonBar {{
                background-color: {self.colors['background_secondary']};
                border-top: 1px solid {self.colors['border']};
            }}
        """)
        button_layout = QHBoxLayout(button_widget)
        button_layout.setContentsMargins(16, 16, 16, 16)
        button_layout.setSpacing(12)
        button_layout.addStretch()

        if not buttons:
            buttons = [{"text": "OK", "role": "accept", "primary": True}]

        for btn_data in buttons:
            btn = QPushButton(btn_data["text"])
            is_primary = btn_data.get("primary", False)
            is_destructive = btn_data.get("destructive", False)

            if is_primary:
                if is_destructive:
                    bg_color = self.colors["error"]
                    hover_color = "#C0392B"  # Darker red
                else:
                    bg_color = self.colors["primary"]
                    hover_color = self.colors["primary_dark"]

                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {bg_color};
                        color: white;
                        border: none;
                        border-radius: 6px;
                        font-size: 13px;
                        font-weight: bold;
                        padding: 8px 20px;
                        min-width: 80px;
                    }}
                    QPushButton:hover {{
                        background-color: {hover_color};
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {self.colors['background']};
                        color: {self.colors['text_primary']};
                        border: 1px solid {self.colors['border']};
                        border-radius: 6px;
                        font-size: 13px;
                        font-weight: 500;
                        padding: 8px 16px;
                        min-width: 70px;
                    }}
                    QPushButton:hover {{
                        background-color: {self.colors['background_secondary']};
                        border-color: {self.colors['text_secondary']};
                    }}
                """)

            if "result_code" in btn_data:
                # Use default arguments to capture loop variable
                btn.clicked.connect(
                    lambda checked=False, rc=btn_data["result_code"]: self.done(rc)
                )
            elif btn_data["role"] == "accept":
                btn.clicked.connect(self.accept)
                btn.setDefault(True)
            elif btn_data["role"] == "reject":
                btn.clicked.connect(self.reject)

            button_layout.addWidget(btn)

        layout.addWidget(button_widget)
        self.setLayout(layout)

    @staticmethod
    def information(parent, title, text, detailed_text=""):
        dlg = StyledMessageBox(
            parent, title, text, StyledMessageBox.INFO, detailed_text=detailed_text
        )
        dlg.exec()

    @staticmethod
    def success(parent, title, text, detailed_text=""):
        dlg = StyledMessageBox(
            parent, title, text, StyledMessageBox.SUCCESS, detailed_text=detailed_text
        )
        dlg.exec()

    @staticmethod
    def warning(parent, title, text, detailed_text=""):
        dlg = StyledMessageBox(
            parent, title, text, StyledMessageBox.WARNING, detailed_text=detailed_text
        )
        dlg.exec()

    @staticmethod
    def critical(parent, title, text, detailed_text=""):
        dlg = StyledMessageBox(
            parent, title, text, StyledMessageBox.ERROR, detailed_text=detailed_text
        )
        dlg.exec()

    @staticmethod
    def question(
        parent,
        title,
        text,
        detailed_text="",
        yes_text="Yes",
        no_text="No",
        destructive=False,
    ):
        """
        Returns True if Yes is clicked, False otherwise.
        """
        buttons = [
            {"text": no_text, "role": "reject", "primary": False},
            {
                "text": yes_text,
                "role": "accept",
                "primary": True,
                "destructive": destructive,
            },
        ]
        dlg = StyledMessageBox(
            parent,
            title,
            text,
            StyledMessageBox.QUESTION,
            buttons=buttons,
            detailed_text=detailed_text,
        )
        return dlg.exec() == QDialog.DialogCode.Accepted


# --- Helper functions that mimic standard aqt.utils but with style ---
