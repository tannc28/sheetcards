"""Dialog for editing one deck's card layout.

The spreadsheet no longer dictates how a card looks: every column that is not
reserved (``ID``, ``SYNC``, ``SUBDECK n``, ``TAGS``) becomes a note field, and the
card is generated from the per-deck layout edited here and stored by
``sync_config``. The dialog therefore only ever moves field *names* around — it
never writes HTML, that is ``card_layout.build_templates``' job.
"""

import re

from ..card_layout import build_templates
from ..compat import DialogAccepted
from ..compat import QCheckBox
from ..compat import QComboBox
from ..compat import QDialog
from ..compat import QGroupBox
from ..compat import QHBoxLayout
from ..compat import QLabel
from ..compat import QListWidget
from ..compat import QPushButton
from ..compat import QSpinBox
from ..compat import QTextBrowser
from ..compat import QVBoxLayout
from ..compat import QWidget
from ..compat import mw
from ..compat import safe_exec_dialog
from ..config_manager import get_remote_decks
from ..styled_messages import StyledMessageBox
from ..sync_config import default_layout_for
from ..sync_config import get_card_layout
from ..sync_config import set_card_layout
from ..theme import base_dialog_qss
from ..theme import get_colors
from ..theme import make_header
from ..theme import primary_button_qss
from ..theme import secondary_button_qss

# The row key is not a note field and must never be offered as a card field.
RESERVED_FIELDS = {"ID"}

# Preview rendering. Anki's template syntax is only approximated here: sections are
# always taken (every field gets a sample value) and scripts are dropped, because a
# QTextBrowser runs no JavaScript and would otherwise print the source.
_SCRIPT_RE = re.compile(r"<script\b.*?</script>", re.DOTALL | re.IGNORECASE)
_SECTION_RE = re.compile(r"\{\{[#^/][^}]*\}\}")
_FIELD_RE = re.compile(r"\{\{([^}]*)\}\}")
_FRONT_SIDE_MARK = "\x00frontside\x00"

ALIGN_CHOICES = (
    ("Left", "left"),
    ("Center", "center"),
    ("Right", "right"),
)

TIMER_POSITION_CHOICES = (
    ("Between sections", "between_sections"),
    ("Top middle", "top_middle"),
)


def _deck_label(sheet_id, deck_info):
    """Human-readable name for the deck picker."""
    remote = (deck_info.get("remote_deck_name") or "").strip()
    local = (deck_info.get("local_deck_name") or "").strip()
    if remote and local and remote != local:
        return f"{remote}  —  {local}"
    return remote or local or sheet_id


class CardLayoutDialog(QDialog):
    """Lets the user decide which field goes where, and how the card is styled."""

    def __init__(self, parent=None):
        super().__init__(parent or mw)
        self.setWindowTitle("Configure Card Layout")
        self.setMinimumSize(900, 640)
        self.resize(980, 720)

        self.colors = get_colors()
        self.decks = self._load_decks()
        self.sheet_id = None
        self.fields = []
        # Guards the preview/refresh chain while widgets are being repopulated.
        self._loading = False

        self._setup_ui()
        self._apply_styles()
        self.setStyleSheet(self.styleSheet() + base_dialog_qss(self.colors))
        self._connect_signals()
        self._load_selected_deck()

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def _load_decks(self):
        """Connected decks as ``[(sheet_id, label, deck_info)]``, sorted by label."""
        decks = []
        for sheet_id, deck_info in (get_remote_decks() or {}).items():
            if isinstance(deck_info, dict):
                decks.append((sheet_id, _deck_label(sheet_id, deck_info), deck_info))
        decks.sort(key=lambda entry: entry[1].lower())
        return decks

    def _note_types_for(self, deck_info):
        """The deck's Sheets2Anki note types, "Basic" first (it is the reference)."""
        col = getattr(mw, "col", None)
        models = getattr(col, "models", None) if col else None
        if models is None:
            return []

        found = []
        for raw_id in (deck_info.get("note_types") or {}).keys():
            try:
                note_type = models.get(int(raw_id))
            except Exception:
                note_type = None
            if note_type:
                found.append(note_type)

        # A deck synced before note types were registered (or renamed outside the
        # add-on) still resolves by name.
        if not found:
            remote = (deck_info.get("remote_deck_name") or "").strip()
            prefix = f"Sheets2Anki - {remote}" if remote else None
            if prefix:
                try:
                    entries = list(models.all_names_and_ids())
                except Exception:
                    entries = []
                for entry in entries:
                    name = getattr(entry, "name", "")
                    if not name.startswith(prefix):
                        continue
                    try:
                        note_type = models.get(entry.id)
                    except Exception:
                        note_type = None
                    if note_type:
                        found.append(note_type)

        found.sort(key=lambda nt: 0 if str(nt.get("name", "")).endswith("Basic") else 1)
        return found

    def _fields_for(self, deck_info, layout):
        """Candidate field names for the deck.

        Read from the note type when it exists — that is the authoritative list of
        names a template may reference. Before the deck's first sync no note type
        exists yet, so the stored layout's own fields stand in; that keeps the
        dialog usable (and non-destructive) on a freshly added deck.
        """
        names = []
        for note_type in self._note_types_for(deck_info):
            for field in note_type.get("flds", []):
                name = str(field.get("name", "")).strip()
                if name and name not in RESERVED_FIELDS and name not in names:
                    names.append(name)

        if not names:
            for name in list(layout.get("front") or []) + list(
                layout.get("back") or []
            ):
                name = str(name).strip()
                if name and name not in RESERVED_FIELDS and name not in names:
                    names.append(name)

        return names

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        root = QVBoxLayout()
        root.setSpacing(15)
        root.setContentsMargins(20, 20, 20, 20)

        root.addWidget(
            make_header(
                self.colors,
                "Card Layout",
                "Choose which fields appear on the front and the back, and how the "
                "card is styled. Every column in the spreadsheet is a field.",
            )
        )

        deck_row = QHBoxLayout()
        deck_row.setSpacing(10)
        deck_label = QLabel("Deck:")
        deck_label.setStyleSheet(f"font-size: 12pt; color: {self.colors['text']};")
        deck_row.addWidget(deck_label)

        self.deck_combo = QComboBox()
        for sheet_id, label, _info in self.decks:
            self.deck_combo.addItem(label, sheet_id)
        deck_row.addWidget(self.deck_combo, 1)
        root.addLayout(deck_row)

        self.empty_label = QLabel(
            "No decks are connected yet. Add a deck from Google Sheets "
            "(Ctrl+Shift+A) first, then come back here to edit its card layout."
        )
        self.empty_label.setWordWrap(True)
        self.empty_label.setObjectName("emptyState")
        root.addWidget(self.empty_label)

        self.body = QWidget()
        body_layout = QHBoxLayout(self.body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(15)

        left_column = QVBoxLayout()
        left_column.setSpacing(15)
        left_column.addWidget(self._build_fields_group())
        left_column.addWidget(self._build_format_group())
        left_column.addWidget(self._build_hand_edited_group())
        left_column.addStretch()
        body_layout.addLayout(left_column, 3)
        body_layout.addWidget(self._build_preview_group(), 2)

        root.addWidget(self.body, 1)

        buttons = QHBoxLayout()
        buttons.setContentsMargins(0, 10, 0, 0)

        self.reset_button = QPushButton("↺ Restore Defaults")
        self.reset_button.setStyleSheet(secondary_button_qss(self.colors))
        buttons.addWidget(self.reset_button)
        buttons.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setStyleSheet(secondary_button_qss(self.colors))
        buttons.addWidget(self.cancel_button)

        self.save_button = QPushButton("✓ Save")
        self.save_button.setStyleSheet(primary_button_qss(self.colors, "success"))
        self.save_button.setDefault(True)
        buttons.addWidget(self.save_button)

        root.addLayout(buttons)
        self.setLayout(root)

        has_decks = bool(self.decks)
        self.empty_label.setVisible(not has_decks)
        self.body.setEnabled(has_decks)
        self.deck_combo.setEnabled(has_decks)
        self.save_button.setEnabled(has_decks)
        self.reset_button.setEnabled(has_decks)

    def _build_fields_group(self):
        group = QGroupBox("Fields Shown")
        layout = QHBoxLayout()
        layout.setSpacing(10)

        self.front_list = QListWidget()
        self.back_list = QListWidget()

        layout.addLayout(self._build_list_column("Front", self.front_list), 1)

        move_column = QVBoxLayout()
        move_column.addStretch()
        self.to_back_button = QPushButton("→")
        self.to_front_button = QPushButton("←")
        for button in (self.to_back_button, self.to_front_button):
            button.setStyleSheet(secondary_button_qss(self.colors))
            button.setFixedWidth(58)
            move_column.addWidget(button)
        move_column.addStretch()
        layout.addLayout(move_column)

        layout.addLayout(self._build_list_column("Back", self.back_list), 1)

        group.setLayout(layout)
        return group

    def _build_list_column(self, title, list_widget):
        """One side's list plus its reorder buttons."""
        column = QVBoxLayout()
        column.setSpacing(8)

        label = QLabel(title)
        label.setStyleSheet(
            f"font-size: 12pt; font-weight: bold; color: {self.colors['text']};"
        )
        column.addWidget(label)

        list_widget.setMinimumHeight(150)
        column.addWidget(list_widget, 1)

        reorder = QHBoxLayout()
        reorder.setSpacing(8)
        up_button = QPushButton("↑")
        down_button = QPushButton("↓")
        for button in (up_button, down_button):
            button.setStyleSheet(secondary_button_qss(self.colors))
            reorder.addWidget(button)
        reorder.addStretch()
        column.addLayout(reorder)

        up_button.clicked.connect(lambda: self._move_within(list_widget, -1))
        down_button.clicked.connect(lambda: self._move_within(list_widget, 1))
        return column

    def _build_format_group(self):
        group = QGroupBox("Formatting")
        layout = QVBoxLayout()
        layout.setSpacing(10)

        self.show_labels_check = QCheckBox("Show field labels")
        layout.addWidget(self.show_labels_check)

        sizes = QHBoxLayout()
        sizes.setSpacing(10)

        sizes.addWidget(QLabel("Front text size:"))
        self.front_size_spin = QSpinBox()
        self.front_size_spin.setRange(10, 120)
        self.front_size_spin.setSuffix(" px")
        sizes.addWidget(self.front_size_spin)

        sizes.addSpacing(15)
        sizes.addWidget(QLabel("Back text size:"))
        self.back_size_spin = QSpinBox()
        self.back_size_spin.setRange(10, 120)
        self.back_size_spin.setSuffix(" px")
        sizes.addWidget(self.back_size_spin)

        sizes.addSpacing(15)
        sizes.addWidget(QLabel("Alignment:"))
        self.align_combo = QComboBox()
        for label, value in ALIGN_CHOICES:
            self.align_combo.addItem(label, value)
        sizes.addWidget(self.align_combo)
        sizes.addStretch()
        layout.addLayout(sizes)

        self.reverse_check = QCheckBox("Add a reverse card (back asks the front)")
        layout.addWidget(self.reverse_check)

        timer_row = QHBoxLayout()
        timer_row.setSpacing(10)
        self.timer_check = QCheckBox("Show the timer")
        timer_row.addWidget(self.timer_check)
        timer_row.addWidget(QLabel("Position:"))
        self.timer_position_combo = QComboBox()
        for label, value in TIMER_POSITION_CHOICES:
            self.timer_position_combo.addItem(label, value)
        timer_row.addWidget(self.timer_position_combo)
        timer_row.addStretch()
        layout.addLayout(timer_row)

        group.setLayout(layout)
        return group

    def _build_hand_edited_group(self):
        group = QGroupBox("Hand-Edited Templates")
        layout = QVBoxLayout()
        layout.setSpacing(6)

        self.hand_edited_check = QCheckBox("I edit the templates myself")
        layout.addWidget(self.hand_edited_check)

        note = QLabel(
            "When enabled, syncing no longer rebuilds the templates, so any changes "
            "you make in Anki's card editor are kept."
        )
        note.setWordWrap(True)
        note.setStyleSheet(
            f"font-size: 11pt; color: {self.colors['text_secondary']}; font-weight: normal;"
        )
        layout.addWidget(note)

        group.setLayout(layout)
        return group

    def _build_preview_group(self):
        group = QGroupBox("Preview")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        self.preview_view = QTextBrowser()
        self.preview_view.setOpenExternalLinks(False)
        layout.addWidget(self.preview_view, 1)

        caption = QLabel(
            "The preview only approximates the card structure with sample content — "
            "the real card in Anki may look slightly different."
        )
        caption.setWordWrap(True)
        caption.setStyleSheet(
            f"font-size: 11pt; color: {self.colors['text_secondary']}; font-weight: normal;"
        )
        layout.addWidget(caption)

        group.setLayout(layout)
        return group

    def _apply_styles(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {self.colors['bg']};
                color: {self.colors['text']};
            }}
            QLabel {{
                color: {self.colors['text']};
                font-size: 12pt;
            }}
            QLabel#emptyState {{
                background-color: {self.colors['warning_bg']};
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
                padding: 14px;
            }}
            QCheckBox {{
                color: {self.colors['text']};
                font-size: 12pt;
                font-weight: normal;
                spacing: 8px;
            }}
            QListWidget {{
                background-color: {self.colors['list_bg']};
                color: {self.colors['text']};
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
                padding: 4px;
                font-size: 12pt;
                font-weight: normal;
            }}
            QListWidget::item {{
                padding: 6px 8px;
                border-radius: 6px;
            }}
            QListWidget::item:hover {{ background-color: {self.colors['row_hover']}; }}
            QListWidget::item:selected {{
                background-color: {self.colors['accent_primary']};
                color: white;
            }}
            QComboBox, QSpinBox {{
                background-color: {self.colors['input_bg']};
                color: {self.colors['text']};
                border: 1px solid {self.colors['border']};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12pt;
                font-weight: normal;
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: 10px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {self.colors['input_bg']};
                color: {self.colors['text']};
                selection-background-color: {self.colors['accent_primary']};
            }}
            QTextBrowser {{
                background-color: {self.colors['card_bg']};
                color: {self.colors['text']};
                border: 1px solid {self.colors['border']};
                border-radius: 8px;
                padding: 8px;
                font-weight: normal;
            }}
        """)

    def _connect_signals(self):
        self.deck_combo.currentIndexChanged.connect(self._load_selected_deck)
        self.to_back_button.clicked.connect(
            lambda: self._move_between(self.front_list, self.back_list)
        )
        self.to_front_button.clicked.connect(
            lambda: self._move_between(self.back_list, self.front_list)
        )
        self.show_labels_check.stateChanged.connect(self._refresh_preview)
        self.front_size_spin.valueChanged.connect(self._refresh_preview)
        self.back_size_spin.valueChanged.connect(self._refresh_preview)
        self.align_combo.currentIndexChanged.connect(self._refresh_preview)
        self.reverse_check.stateChanged.connect(self._refresh_preview)
        self.timer_check.stateChanged.connect(self._on_timer_toggled)
        self.timer_position_combo.currentIndexChanged.connect(self._refresh_preview)
        self.reset_button.clicked.connect(self._reset_layout)
        self.cancel_button.clicked.connect(self.reject)
        self.save_button.clicked.connect(self._save_layout)

    # ------------------------------------------------------------------
    # Loading / editing state
    # ------------------------------------------------------------------

    def _load_selected_deck(self):
        """Loads the stored layout of the deck currently selected in the combo."""
        if not self.decks:
            return

        index = max(0, self.deck_combo.currentIndex())
        self.sheet_id, _label, deck_info = self.decks[index]

        layout = get_card_layout(self.sheet_id)
        self.fields = self._fields_for(deck_info, layout)
        self._apply_layout(layout)

    def _apply_layout(self, layout):
        """Pushes a layout dict into the widgets."""
        self._loading = True
        try:
            front = [f for f in (layout.get("front") or []) if f in self.fields]
            back = [
                f
                for f in (layout.get("back") or [])
                if f in self.fields and f not in front
            ]
            # Anything the layout does not mention has to surface somewhere, or the
            # user would think the add-on lost the column.
            placed = set(front) | set(back)
            back.extend(f for f in self.fields if f not in placed)

            self.front_list.clear()
            self.front_list.addItems(front)
            self.back_list.clear()
            self.back_list.addItems(back)

            self.show_labels_check.setChecked(bool(layout.get("show_labels", False)))
            self.front_size_spin.setValue(int(layout.get("front_size", 40) or 40))
            self.back_size_spin.setValue(int(layout.get("back_size", 18) or 18))
            self._select_data(self.align_combo, layout.get("align", "center"))
            self.reverse_check.setChecked(bool(layout.get("reverse_card", False)))
            self.timer_check.setChecked(bool(layout.get("timer", True)))
            self._select_data(
                self.timer_position_combo,
                layout.get("timer_position", "between_sections"),
            )
            self.hand_edited_check.setChecked(bool(layout.get("hand_edited", False)))
            self.timer_position_combo.setEnabled(self.timer_check.isChecked())
        finally:
            self._loading = False
        self._refresh_preview()

    @staticmethod
    def _select_data(combo, value):
        """Selects the combo entry carrying ``value``, falling back to the first."""
        index = combo.findData(value)
        combo.setCurrentIndex(index if index >= 0 else 0)

    @staticmethod
    def _items(list_widget):
        return [list_widget.item(row).text() for row in range(list_widget.count())]

    def _move_between(self, source, target):
        """Moves the selected field to the other side, keeping it in exactly one."""
        row = source.currentRow()
        if row < 0:
            return
        item = source.takeItem(row)
        target.addItem(item.text())
        target.setCurrentRow(target.count() - 1)
        source.setCurrentRow(min(row, source.count() - 1))
        self._refresh_preview()

    def _move_within(self, list_widget, delta):
        """Reorders the selected field inside its own list."""
        row = list_widget.currentRow()
        target = row + delta
        if row < 0 or target < 0 or target >= list_widget.count():
            return
        item = list_widget.takeItem(row)
        list_widget.insertItem(target, item.text())
        list_widget.setCurrentRow(target)
        self._refresh_preview()

    def _on_timer_toggled(self):
        self.timer_position_combo.setEnabled(self.timer_check.isChecked())
        self._refresh_preview()

    def _current_layout(self):
        """The layout described by the widgets right now."""
        return {
            "front": self._items(self.front_list),
            "back": self._items(self.back_list),
            "show_labels": self.show_labels_check.isChecked(),
            "front_size": self.front_size_spin.value(),
            "back_size": self.back_size_spin.value(),
            "align": self.align_combo.currentData() or "center",
            "reverse_card": self.reverse_check.isChecked(),
            "timer": self.timer_check.isChecked(),
            "timer_position": self.timer_position_combo.currentData()
            or "between_sections",
            "hand_edited": self.hand_edited_check.isChecked(),
        }

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def _refresh_preview(self):
        if self._loading:
            return
        try:
            html = self._preview_html(self._current_layout())
        except Exception as error:  # a broken preview must not block editing
            html = f"<p>Could not build the preview: {error}</p>"
        self.preview_view.setHtml(html)

    def _preview_html(self, layout):
        """Renders every template the layout produces, with sample field values."""
        blocks = []
        for template in build_templates(layout):
            front = self._render(template["qfmt"])
            back = self._render(
                template["afmt"].replace("{{FrontSide}}", _FRONT_SIDE_MARK)
            ).replace(_FRONT_SIDE_MARK, front)
            blocks.append(self._preview_block(template["name"], "Front", front))
            blocks.append(self._preview_block(template["name"], "Back", back))
        return "".join(blocks)

    def _preview_block(self, template_name, side, body):
        return (
            f'<p style="color:{self.colors["text_secondary"]};font-size:10pt;'
            f'margin-bottom:2px;">{template_name} · {side}</p>'
            f'<div style="border:1px solid {self.colors["border"]};'
            f'background-color:{self.colors["background"]};padding:10px;">{body}</div>'
            "<p>&nbsp;</p>"
        )

    @staticmethod
    def _render(template_html):
        """Turns one template into previewable HTML with placeholder content."""
        html = _SCRIPT_RE.sub("", template_html)
        # Every field has a sample value, so conditional sections always render.
        html = _SECTION_RE.sub("", html)
        return _FIELD_RE.sub(CardLayoutDialog._sample_for, html)

    @staticmethod
    def _sample_for(match):
        """Sample text for one ``{{Field}}`` reference, filters stripped."""
        token = match.group(1).strip()
        name = token.split(":")[-1].strip()
        return f"[{name}]" if name else ""

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _reset_layout(self):
        """Back to the default split for the deck's current fields."""
        self._apply_layout(default_layout_for(self.fields))

    def _save_layout(self):
        if not self.sheet_id:
            return

        layout = self._current_layout()
        if set_card_layout(self.sheet_id, layout):
            StyledMessageBox.success(
                self,
                "Card Layout Saved",
                "The card layout has been saved.",
                detailed_text=(
                    "Run a sync (Ctrl+Shift+S) so Anki rebuilds the templates with the new layout."
                    if not layout["hand_edited"]
                    else "You enabled 'I edit the templates myself', so syncing will not rebuild the templates."
                ),
            )
            self.accept()
        else:
            StyledMessageBox.critical(
                self,
                "Save Failed",
                "The card layout could not be saved.",
                detailed_text=(
                    "The layout is stored in the Anki collection, but no collection is "
                    "currently open. Open an Anki profile and try again."
                ),
            )


def show_card_layout_dialog(parent=None):
    """
    Utility function to show the card layout dialog.

    Args:
        parent: Parent widget (optional)

    Returns:
        bool: True if user saved changes, False otherwise
    """
    dialog = CardLayoutDialog(parent)
    result = safe_exec_dialog(dialog)
    return result == DialogAccepted
