"""SheetCards' message boxes, drawn the way Anki draws its own.

These used to be a small web page each: a tinted header band with a 32px emoji in
it, a white body, a grey button bar with a hairline above it, and a filled blue
button. Three horizontal bands and four hand-set colours to say one sentence.

What is left is a layout — an icon, a sentence, the buttons — and Anki's global
stylesheet doing the rest. The icon is one of the add-on's own SVGs, inked in the
colour that matches what is being said, which is the only colour in the window.

The class survives rather than being replaced by `QMessageBox` because callers use
things `QMessageBox` makes awkward: button text of their own, a destructive role,
and a specific result code per button.
"""

from .compat import ButtonRole_Accept
from .compat import ButtonRole_Destructive
from .compat import ButtonRole_Reject
from .compat import QDialog
from .compat import QDialogButtonBox
from .compat import QHBoxLayout
from .compat import QLabel
from .compat import QVBoxLayout
from .compat import RichText
from .compat import TopAlign

try:
    from .theme import ICON_SIZE
    from .theme import MARGIN
    from .theme import SPACE_SECTION
    from .theme import get_colors
    from .theme import icon
except ImportError:  # pragma: no cover - direct-import fallback for tests
    from theme import ICON_SIZE
    from theme import MARGIN
    from theme import SPACE_SECTION
    from theme import get_colors
    from theme import icon


class StyledMessageBox(QDialog):
    """A message, an icon, and the buttons that answer it."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    QUESTION = "question"
    SUCCESS = "success"

    # message type -> (icon name, colour key). The icon names are files in
    # `src/icons`; the colour keys are Anki's, through `get_colors()`.
    _LOOK = {
        INFO: ("info", "primary"),
        WARNING: ("warning", "warning"),
        ERROR: ("error", "error"),
        QUESTION: ("question", "primary"),
        SUCCESS: ("success", "success"),
    }

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
        self.setMinimumWidth(380)
        self.setMaximumWidth(560)

        self.colors = get_colors()
        self.message_type = message_type
        self._setup_ui(title, text, detailed_text, buttons)

    def _setup_ui(self, title, text, detailed_text, buttons):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)
        layout.setSpacing(SPACE_SECTION)

        # The icon sits beside the words rather than above them in a band of its
        # own, at twice the size it takes elsewhere: this is the one place in the
        # add-on where the icon is the first thing read.
        row = QHBoxLayout()
        row.setSpacing(SPACE_SECTION)
        shape, colour = self._LOOK.get(self.message_type, ("info", "text_secondary"))
        icon_label = QLabel()
        icon_label.setPixmap(icon(shape, colour).pixmap(ICON_SIZE * 2, ICON_SIZE * 2))
        icon_label.setAlignment(TopAlign)
        icon_label.setFixedWidth(ICON_SIZE * 2)
        row.addWidget(icon_label)

        words = QVBoxLayout()
        words.setSpacing(6)

        # The window title is in the title bar already, so it is repeated here only
        # when it is saying something the sentence under it does not.
        if title and title.strip().lower() not in text.strip().lower():
            title_label = QLabel(f"<b>{title}</b>")
            title_label.setWordWrap(True)
            words.addWidget(title_label)

        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setTextFormat(RichText)
        words.addWidget(text_label)

        if detailed_text:
            detail_label = QLabel(detailed_text)
            detail_label.setWordWrap(True)
            detail_label.setStyleSheet(f"color: {self.colors['text_secondary']};")
            words.addWidget(detail_label)

        words.addStretch()
        row.addLayout(words, 1)
        layout.addLayout(row)

        # A button box, so OK and Cancel come out in this platform's order and a
        # destructive button lands where this platform puts one.
        self.button_box = QDialogButtonBox()
        for spec in buttons or [{"text": "OK", "role": "accept", "primary": True}]:
            role = (
                ButtonRole_Destructive
                if spec.get("destructive")
                else (
                    ButtonRole_Accept if spec["role"] == "accept" else ButtonRole_Reject
                )
            )
            button = self.button_box.addButton(spec["text"], role)
            if "result_code" in spec:
                button.clicked.connect(
                    lambda checked=False, code=spec["result_code"]: self.done(code)
                )
            elif spec["role"] == "accept":
                button.clicked.connect(self.accept)
                button.setDefault(True)
            else:
                button.clicked.connect(self.reject)
        layout.addWidget(self.button_box)

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
