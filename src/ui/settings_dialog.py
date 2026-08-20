"""Everything about the add-on that is not about a sheet.

Three windows used to live here — one for the deck-options mode, one for AnkiWeb,
one for debug logging — each with a global shortcut of its own, for three radio
buttons, two radio buttons and a checkbox respectively. Anki has one Preferences
window; an add-on does not need more.

The deck-options mode went with them: a study preset is Anki's to configure, two
clicks away in its own deck options, and the choice this offered was a setting
about a setting. Every connected deck now studies under one group.

Nothing here sets a background, a border or a radius. Anki styles every standard
widget through a global stylesheet, so staying out of the way is the technique.
"""

import os

from ..compat import ButtonBox_Cancel
from ..compat import ButtonBox_Ok
from ..compat import QCheckBox
from ..compat import QDialog
from ..compat import QDialogButtonBox
from ..compat import QGroupBox
from ..compat import QHBoxLayout
from ..compat import QLabel
from ..compat import QPushButton
from ..compat import QVBoxLayout
from ..compat import TextSelectableByMouse
from ..compat import mw
from ..compat import safe_exec_dialog
from ..config_manager import get_ankiweb_sync_mode
from ..config_manager import get_meta
from ..config_manager import save_meta
from ..config_manager import set_accumulate_logs
from ..config_manager import set_ankiweb_sync_config
from ..config_manager import should_accumulate_logs
from ..debug import add_debug_message
from ..debug import get_debug_log_path
from ..debug import is_debug_enabled
from ..styled_messages import StyledMessageBox
from ..theme import MARGIN
from ..theme import RADIO_INDENT
from ..theme import SPACE_ELEMENT
from ..theme import SPACE_SECTION
from ..theme import get_colors
from ..theme import icon


class SettingsDialog(QDialog):
    """The add-on's settings, in one window."""

    def __init__(self, parent=None):
        super().__init__(parent or mw)
        self.setWindowTitle("Sheets2Anki Settings")
        self.setModal(True)
        self.setMinimumWidth(460)

        self.colors = get_colors()
        self._setup_ui()
        self._load()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(SPACE_SECTION)
        layout.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)

        layout.addWidget(self._ankiweb_group())
        layout.addWidget(self._logging_group())
        layout.addStretch()

        self.button_box = QDialogButtonBox(ButtonBox_Ok | ButtonBox_Cancel)
        save_button = self.button_box.button(ButtonBox_Ok)
        assert save_button is not None  # just asked for, by name
        save_button.setText("Save")
        save_button.setIcon(icon("success", "text"))
        save_button.setDefault(True)
        self.button_box.accepted.connect(self._save)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _ankiweb_group(self):
        group = QGroupBox("After a sync")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(SPACE_ELEMENT)

        self.ankiweb_check = QCheckBox("Upload to AnkiWeb")
        group_layout.addWidget(self.ankiweb_check)

        note = QLabel(
            "So the new cards are on your phone before you pick it up. Without "
            "this, your collection goes up when you press Anki's own Sync button."
        )
        note.setWordWrap(True)
        note.setContentsMargins(RADIO_INDENT, 0, 0, 0)
        note.setStyleSheet(f"color: {self.colors['text_secondary']};")
        group_layout.addWidget(note)
        return group

    def _logging_group(self):
        group = QGroupBox("Logging")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(SPACE_ELEMENT)

        self.debug_check = QCheckBox("Write a debug log")
        group_layout.addWidget(self.debug_check)

        self.accumulate_check = QCheckBox("Keep the logs from earlier syncs")
        self.accumulate_check.setContentsMargins(RADIO_INDENT, 0, 0, 0)
        group_layout.addWidget(self.accumulate_check)

        note = QLabel(
            "Useful when something goes wrong, and worth turning off again "
            "afterwards. The log is a text file; read it in whatever you read text "
            "files in."
        )
        note.setWordWrap(True)
        note.setContentsMargins(RADIO_INDENT, 0, 0, 0)
        note.setStyleSheet(f"color: {self.colors['text_secondary']};")
        group_layout.addWidget(note)

        # The path is a string people copy, so it can be selected. The window that
        # used to be here also displayed the log's contents in a read-only text
        # box, which is a text editor with everything taken out.
        path_row = QHBoxLayout()
        path_row.setSpacing(SPACE_ELEMENT)
        self.path_label = QLabel(get_debug_log_path())
        self.path_label.setWordWrap(True)
        self.path_label.setTextInteractionFlags(TextSelectableByMouse)
        self.path_label.setStyleSheet(f"color: {self.colors['text_secondary']};")
        path_row.addWidget(self.path_label, 1)
        open_button = QPushButton("Open folder")
        open_button.clicked.connect(self._open_log_folder)
        path_row.addWidget(open_button)
        group_layout.addLayout(path_row)
        return group

    def _load(self):
        self.ankiweb_check.setChecked(get_ankiweb_sync_mode() == "sync")
        self.debug_check.setChecked(is_debug_enabled())
        self.accumulate_check.setChecked(should_accumulate_logs())

    def _save(self):
        """Writes all three settings, then closes.

        Written on Save rather than on each toggle. The debug window used to save
        the moment a box was ticked, which meant Cancel did nothing and the window
        had no way to be left alone.
        """
        try:
            set_ankiweb_sync_config(
                "sync" if self.ankiweb_check.isChecked() else "none"
            )

            debug_on = self.debug_check.isChecked()
            meta = get_meta()
            meta.setdefault("config", {})["debug"] = debug_on
            save_meta(meta)
            set_accumulate_logs(self.accumulate_check.isChecked())
            if debug_on:
                add_debug_message("🔧 Debug logging enabled", "DEBUG")

            self.accept()
        except Exception as error:
            StyledMessageBox.warning(self, "Error", f"Could not save: {error}")

    def _open_log_folder(self):
        """Shows the log's folder in whatever this platform browses files with."""
        try:
            import platform
            import subprocess

            folder = os.path.dirname(get_debug_log_path())
            system = platform.system()
            if system == "Darwin":
                subprocess.run(["open", folder])
            elif system == "Windows":
                subprocess.run(["explorer", folder])
            else:
                subprocess.run(["xdg-open", folder])
        except Exception as error:
            StyledMessageBox.warning(self, "Error", f"Could not open folder: {error}")


def show_settings_dialog(parent=None):
    """Shows the settings window."""
    dialog = SettingsDialog(parent)
    safe_exec_dialog(dialog)
