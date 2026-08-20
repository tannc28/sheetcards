"""Read-only view of the card layout a spreadsheet declares.

The sheet is the single source of truth: the optional ``#config`` row under the
header row says which column goes on which side and how it looks. Nothing here is
editable — a dialog that also wrote the layout would give one setting two owners,
and the sheet would silently win on the next sync.

So this window only ever *explains*: what the last sync understood, what it could
not understand, which speech voices this machine actually has for the languages the
sheet asks for, and roughly what the resulting card looks like.
"""

import re
from html import escape

from ..compat import ButtonBox_Close
from ..compat import DialogAccepted
from ..compat import QComboBox
from ..compat import QDialog
from ..compat import QDialogButtonBox
from ..compat import QGroupBox
from ..compat import QHBoxLayout
from ..compat import QLabel
from ..compat import QTextBrowser
from ..compat import QVBoxLayout
from ..compat import QWidget
from ..compat import mw
from ..compat import safe_exec_dialog
from ..config_manager import get_remote_decks
from ..sheet_config import THEMES
from ..theme import ICON_SIZE
from ..theme import MARGIN
from ..theme import SPACE_ELEMENT
from ..theme import SPACE_SECTION
from ..theme import get_colors
from ..theme import icon
from ..theme import is_dark_mode

# =============================================================================
# sync_config adapter
# -----------------------------------------------------------------------------
# ``sync_config`` caches what the last sync parsed out of each sheet's ``#config``
# row. Everything this dialog assumes about that cache lives in
# ``_read_sheet_snapshot`` and nowhere else, so a change to the cache shape is a
# one-place edit here.
# =============================================================================

# Per-column settings the ``#config`` row can carry (see ``sheet_config``).
# Kept in step with sheet_config.FieldConfig — a key missing here shows the column
# as having no settings at all, which reads as "the add-on ignored my sheet".
_FIELD_KEYS = (
    "side",
    "size",
    "color",
    "align",
    "media",
    "type_answer",
    "tts",
    "voices",
    "speed",
    "label",
    "bold",
    "italic",
    "hint",
    "furigana",
    "cloze",
    "draw",
    "subdeck",
    "math",
    "code",
    "font",
    "sort",
    "rtl",
    "vertical",
)
_FLAG_KEYS = ("bold", "italic", "hint", "furigana", "draw", "sort", "rtl", "vertical")
_DECK_KEYS = ("align", "speed", "reverse", "theme")


def _empty_snapshot():
    """The shape every caller in this module can rely on."""
    return {
        "sheet_id": None,
        "synced": False,
        "config_present": False,
        "content_headers": [],
        "fields": {},
        "deck": {},
        "warnings": [],
        "raw": None,
    }


def _as_mapping(value):
    """A plain dict for either a mapping or a small settings object."""
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "__dict__"):
        return {k: v for k, v in vars(value).items() if not k.startswith("_")}
    return {}


def _clean_names(values):
    """Non-empty strings from an iterable, order preserved."""
    if not isinstance(values, (list, tuple)):
        return []
    return [str(v).strip() for v in values if str(v).strip()]


def _field_settings(raw):
    """One column's settings as a plain dict with every key present."""
    data = _as_mapping(raw)
    settings = {key: data.get(key) for key in _FIELD_KEYS}
    for flag in _FLAG_KEYS:
        settings[flag] = bool(settings[flag])
    settings["voices"] = _clean_names(settings["voices"])
    return settings


def _read_sheet_snapshot(sheet_id):
    """What the last sync parsed for one sheet, as a plain dict.

    Returns the ``_empty_snapshot()`` shape when the module, the accessor or the
    entry is missing — a deck that has never been synced is a normal state, not an
    error, and the dialog reports it as such.
    """
    snapshot = _empty_snapshot()
    if not sheet_id:
        return snapshot
    snapshot["sheet_id"] = sheet_id

    try:
        from .. import sync_config
    except ImportError:  # pragma: no cover - direct (non-package) import in tests
        try:
            import sync_config  # type: ignore[no-redef]
        except ImportError:
            return snapshot

    try:
        raw = sync_config.get_sheet_snapshot(sheet_id)
    except Exception:
        raw = None

    if not raw:
        return snapshot

    data = _as_mapping(raw)
    snapshot["raw"] = raw

    headers = _clean_names(
        data.get("content_headers") or data.get("headers") or data.get("columns")
    )
    if not headers:
        # A layout-shaped cache names the columns through its two sides instead.
        headers = _clean_names(
            list(data.get("front") or []) + list(data.get("back") or [])
        )

    fields_raw = (
        data.get("fields") or data.get("field_settings") or data.get("field_config")
    )
    if isinstance(fields_raw, dict):
        for header, cfg in fields_raw.items():
            header = str(header).strip()
            if header:
                snapshot["fields"][header] = _field_settings(cfg)

    # Columns only mentioned in the per-field map still have to be listed.
    for header in snapshot["fields"]:
        if header not in headers:
            headers.append(header)
    snapshot["content_headers"] = headers

    deck_raw = data.get("deck") or data.get("deck_settings")
    deck = _as_mapping(deck_raw) if deck_raw else data
    snapshot["deck"] = {key: deck.get(key) for key in _DECK_KEYS}

    snapshot["warnings"] = [
        str(w).strip() for w in (data.get("warnings") or []) if str(w).strip()
    ]

    present = data.get("config_present")
    if present is None:
        present = data.get("present")
    if present is None:
        present = bool(
            snapshot["fields"]
            or snapshot["warnings"]
            or any(v not in (None, False, "") for v in snapshot["deck"].values())
        )
    snapshot["config_present"] = bool(present)

    # No columns means no sync has ever described this sheet to us.
    snapshot["synced"] = bool(headers)
    return snapshot


# =============================================================================
# Installed speech voices
# =============================================================================


def _installed_voices():
    """``(voices, error)`` where voices is ``[(name, lang)]`` or None on failure.

    ``aqt.tts`` is imported here rather than at module level: it is not part of the
    add-on's Qt gateway, it is absent outside Anki, and a machine with a broken
    speech stack must still be able to open this window.
    """
    try:
        from aqt.tts import all_tts_voices

        found = all_tts_voices()
    except Exception as error:
        return None, str(error) or error.__class__.__name__

    voices = []
    for voice in found or []:
        name = str(getattr(voice, "name", "") or "").strip()
        lang = str(getattr(voice, "lang", "") or "").strip()
        if name or lang:
            voices.append((name, lang))
    voices.sort(key=lambda entry: (entry[1].lower(), entry[0].lower()))
    return voices, None


# =============================================================================
# Preview rendering
# -----------------------------------------------------------------------------
# Anki's template syntax is only approximated: sections are always taken (every
# field gets a sample value) and scripts are dropped, because a QTextBrowser runs no
# JavaScript and would otherwise print the source.
# =============================================================================

_SCRIPT_RE = re.compile(r"<script\b.*?</script>", re.DOTALL | re.IGNORECASE)
_SECTION_RE = re.compile(r"\{\{[#^/][^}]*\}\}")
_FIELD_RE = re.compile(r"\{\{([^}]*)\}\}")
_FRONT_SIDE_MARK = "\x00frontside\x00"


def _usable_templates(templates):
    """True when ``build_templates`` returned something we can actually render."""
    if not isinstance(templates, list) or not templates:
        return False
    return all(
        isinstance(t, dict) and t.get("qfmt") and t.get("afmt") for t in templates
    )


def _build_templates_for(snapshot):
    """The real card templates for this sheet, or ``[]`` when unavailable.

    ``card_layout`` builds the templates from exactly what ``sync_config`` cached,
    so the cached object is handed straight back to it. Anything unexpected falls
    through to the simpler preview below instead of breaking the dialog.
    """
    sheet_id = snapshot.get("sheet_id")
    if not sheet_id:
        return []
    try:
        from .. import sync_config
        from ..card_layout import build_templates

        plan, sheet_config = sync_config.cached_plan_and_config(sheet_id)
        if plan is None:
            return []
        templates = build_templates(plan, sheet_config)
    except Exception:
        return []
    return templates if _usable_templates(templates) else []


def _sample_for(match):
    """Sample text for one ``{{Field}}`` reference, filters stripped."""
    token = match.group(1).strip()
    name = token.split(":")[-1].strip()
    return f"[{name}]" if name else ""


def _render_template(template_html):
    """Turns one template into previewable HTML with placeholder content."""
    html = _SCRIPT_RE.sub("", template_html)
    # Every field has a sample value, so conditional sections always render.
    html = _SECTION_RE.sub("", html)
    return _FIELD_RE.sub(_sample_for, html)


def _deck_label(sheet_id, deck_info):
    """Human-readable name for the deck picker."""
    remote = (deck_info.get("remote_deck_name") or "").strip()
    local = (deck_info.get("local_deck_name") or "").strip()
    if remote and local and remote != local:
        return f"{remote}  —  {local}"
    return remote or local or sheet_id


class CardLayoutDialog(QDialog):
    """Shows what the sheet's ``#config`` row asked for, and what came of it."""

    def __init__(self, parent=None):
        super().__init__(parent or mw)
        self.setWindowTitle("Card Layout")
        self.setMinimumSize(900, 640)
        self.resize(1000, 740)

        self.colors = get_colors()
        self.decks = self._load_decks()
        self.sheet_id = None
        self.snapshot = _empty_snapshot()
        self.voices, self.voices_error = _installed_voices()

        self._setup_ui()
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

    def _requested_languages(self):
        """Every TTS language the sheet asks for, deduplicated and sorted."""
        languages = set()
        for settings in self.snapshot["fields"].values():
            language = (settings.get("tts") or "").strip()
            if language:
                languages.add(language)
        return sorted(languages)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(SPACE_SECTION)
        root.setContentsMargins(MARGIN, MARGIN, MARGIN, MARGIN)

        intro = QLabel(
            "How your spreadsheet says the cards should look. This window reports "
            "what the last sync understood — nothing here is editable."
        )
        intro.setWordWrap(True)
        root.addWidget(intro)

        deck_row = QHBoxLayout()
        deck_row.setSpacing(SPACE_ELEMENT)
        deck_icon = QLabel()
        deck_icon.setPixmap(icon("deck", "text_secondary").pixmap(ICON_SIZE, ICON_SIZE))
        deck_row.addWidget(deck_icon)
        deck_row.addWidget(QLabel("Deck:"))

        self.deck_combo = QComboBox()
        for sheet_id, label, _info in self.decks:
            self.deck_combo.addItem(label, sheet_id)
        deck_row.addWidget(self.deck_combo, 1)
        root.addLayout(deck_row)

        self.empty_label = QLabel(
            "No decks are connected yet. Add a deck from Google Sheets "
            "(Ctrl+Shift+A) first, then come back here to see how its cards "
            "are laid out."
        )
        self.empty_label.setWordWrap(True)
        root.addWidget(self.empty_label)

        self.body = QWidget()
        body_layout = QHBoxLayout(self.body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(SPACE_SECTION)

        left_column = QVBoxLayout()
        left_column.setSpacing(SPACE_SECTION)
        left_column.addWidget(self._build_fields_group(), 3)
        left_column.addWidget(self._build_warnings_group(), 2)
        body_layout.addLayout(left_column, 3)

        right_column = QVBoxLayout()
        right_column.setSpacing(SPACE_SECTION)
        right_column.addWidget(self._build_preview_group(), 3)
        right_column.addWidget(self._build_voices_group(), 2)
        body_layout.addLayout(right_column, 2)

        root.addWidget(self.body, 1)

        source_note = QLabel(
            "These settings come from the '#config' row of your spreadsheet — edit "
            "that row and sync again (Ctrl+Shift+S) to change how the cards look."
        )
        source_note.setWordWrap(True)
        source_note.setStyleSheet(f"color: {self.colors['text_secondary']};")
        root.addWidget(source_note)

        self.button_box = QDialogButtonBox(ButtonBox_Close)
        close_button = self.button_box.button(ButtonBox_Close)
        assert close_button is not None  # just asked for, by name
        close_button.setDefault(True)
        self.close_button = close_button
        root.addWidget(self.button_box)

        has_decks = bool(self.decks)
        self.empty_label.setVisible(not has_decks)
        self.body.setVisible(has_decks)
        self.deck_combo.setEnabled(has_decks)

    def _make_browser(self):
        """A read-only rich-text panel — the shared building block of this window."""
        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        return browser

    def _build_fields_group(self):
        group = QGroupBox("What the add-on understood")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        self.fields_view = self._make_browser()
        layout.addWidget(self.fields_view, 1)

        caption = QLabel(
            "A column with no settings uses the defaults: the first content column "
            "is the front of the card and the rest are the back."
        )
        caption.setWordWrap(True)
        caption.setObjectName("caption")
        layout.addWidget(caption)

        group.setLayout(layout)
        return group

    def _build_warnings_group(self):
        self.warnings_group = QGroupBox("Warnings")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        self.warnings_view = self._make_browser()
        layout.addWidget(self.warnings_view, 1)

        self.warnings_group.setLayout(layout)
        return self.warnings_group

    def _build_voices_group(self):
        group = QGroupBox("Voices on this machine")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        self.voices_view = self._make_browser()
        layout.addWidget(self.voices_view, 1)

        group.setLayout(layout)
        return group

    def _build_preview_group(self):
        group = QGroupBox("Preview")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        self.preview_view = self._make_browser()
        layout.addWidget(self.preview_view, 1)

        caption = QLabel(
            "The preview only approximates the card structure with sample content — "
            "the real card in Anki may look slightly different."
        )
        caption.setWordWrap(True)
        caption.setObjectName("caption")
        layout.addWidget(caption)

        group.setLayout(layout)
        return group

    def _connect_signals(self):
        self.deck_combo.currentIndexChanged.connect(self._load_selected_deck)
        self.button_box.rejected.connect(self.accept)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load_selected_deck(self):
        """Reads the cached parse of the deck currently selected in the combo."""
        if not self.decks:
            return

        index = max(0, self.deck_combo.currentIndex())
        self.sheet_id, _label, _deck_info = self.decks[index]
        self.snapshot = _read_sheet_snapshot(self.sheet_id)

        self._refresh_fields()
        self._refresh_warnings()
        self._refresh_voices()
        self._refresh_preview()

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    def _note(self, text, color=None):
        """One paragraph of explanatory text, used for every empty/error state."""
        return (
            f'<p style="color:{color or self.colors["text_secondary"]};">'
            f"{escape(text)}</p>"
        )

    def _never_synced_note(self):
        return self._note(
            "This deck has not been synced yet, so the add-on has not read its "
            "columns. Run a sync (Ctrl+Shift+S) and open this window again."
        )

    # ------------------------------------------------------------------
    # Section: what the add-on understood
    # ------------------------------------------------------------------

    def _refresh_fields(self):
        if not self.snapshot["synced"]:
            self.fields_view.setHtml(self._never_synced_note())
            return

        blocks = [self._config_row_summary(), self._fields_table()]
        self.fields_view.setHtml("".join(blocks))

    def _config_row_summary(self):
        """Whether a ``#config`` row was found, plus any deck-wide settings."""
        if not self.snapshot["config_present"]:
            return self._note(
                "This sheet has no '#config' row, so every column uses the "
                "defaults shown below."
            )

        parts = []
        deck = self.snapshot["deck"]
        align = deck.get("align")
        if align:
            parts.append(f"text aligned {align}")
        speed = deck.get("speed")
        if speed not in (None, ""):
            parts.append(f"speech speed {speed}")
        if deck.get("reverse"):
            parts.append("a reverse card is generated")
        theme = deck.get("theme")
        if theme:
            parts.append(f"the '{theme}' theme")

        detail = "; ".join(parts) if parts else "no deck-wide settings"
        return self._note(f"Config row found — {detail}.")

    def _fields_table(self):
        headers = ("Column", "Side", "Text", "Style", "Label", "Speech")
        border = self.colors["border"]
        head_bg = self.colors["background_secondary"]

        rows = [
            "<tr>"
            + "".join(
                f'<td style="background-color:{head_bg};"><b>{escape(h)}</b></td>'
                for h in headers
            )
            + "</tr>"
        ]

        for index, header in enumerate(self.snapshot["content_headers"]):
            settings = self.snapshot["fields"].get(header) or _field_settings(None)
            cells = (
                escape(header),
                escape(self._side_text(settings, index)),
                escape(self._text_style_text(settings)),
                escape(self._flags_text(settings)),
                escape(str(settings.get("label") or "—")),
                escape(self._speech_text(settings)),
            )
            rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")

        return (
            f'<table width="100%" cellspacing="0" cellpadding="6" '
            f'style="border:1px solid {border};">' + "".join(rows) + "</table>"
        )

    @staticmethod
    def _side_text(settings, index):
        side = (settings.get("side") or "").strip().lower()
        if side == "hide":
            return "hidden"
        if side:
            return side
        return "front (default)" if index == 0 else "back (default)"

    @staticmethod
    def _text_style_text(settings):
        parts = []
        size = settings.get("size")
        if size not in (None, ""):
            parts.append(f"{size}px")
        color = settings.get("color")
        if color:
            parts.append(str(color))
        align = settings.get("align")
        if align:
            parts.append(f"aligned {align}")
        return " · ".join(parts) if parts else "default"

    @staticmethod
    def _flags_text(settings):
        flags = [flag for flag in _FLAG_KEYS if settings.get(flag)]
        return ", ".join(flags) if flags else "—"

    @staticmethod
    def _speech_text(settings):
        language = (settings.get("tts") or "").strip()
        if not language:
            return "—"
        parts = [language]
        voices = settings.get("voices") or []
        if voices:
            parts.append("voices: " + ", ".join(voices))
        speed = settings.get("speed")
        if speed not in (None, ""):
            parts.append(f"speed {speed}")
        return " · ".join(parts)

    # ------------------------------------------------------------------
    # Section: warnings
    # ------------------------------------------------------------------

    def _refresh_warnings(self):
        warnings = self.snapshot["warnings"]

        if not self.snapshot["synced"]:
            self.warnings_group.setTitle("Warnings")
            self.warnings_view.setHtml(self._never_synced_note())
            return

        if not warnings:
            self.warnings_group.setTitle("Warnings")
            self.warnings_view.setHtml(
                self._note(
                    "No problems found — the add-on understood every setting in "
                    "the config row.",
                    self.colors["accent_success"],
                )
            )
            return

        count = len(warnings)
        self.warnings_group.setTitle(
            f"Warnings — {count} problem{'s' if count != 1 else ''} found"
        )
        items = "".join(f"<li>{escape(w)}</li>" for w in warnings)
        self.warnings_view.setHtml(
            self._note(
                "The add-on ignored these settings because it could not read them. "
                "Fix them in the spreadsheet and sync again.",
                self.colors["accent_warning"],
            )
            + f'<ul style="color:{self.colors["text"]};">{items}</ul>'
        )

    # ------------------------------------------------------------------
    # Section: voices
    # ------------------------------------------------------------------

    def _refresh_voices(self):
        if self.voices is None:
            self.voices_view.setHtml(
                self._note(
                    "The installed speech voices could not be listed on this "
                    f"machine ({self.voices_error}). Any 'tts' setting below may "
                    "or may not work here.",
                    self.colors["accent_warning"],
                )
            )
            return

        self.voices_view.setHtml(self._language_check_html() + self._voice_list_html())

    def _language_check_html(self):
        """Compares the languages the sheet asks for against the installed voices.

        Anki matches a ``{{tts}}`` tag to a voice by comparing the language strings
        exactly, and plays nothing at all when none matches — so an unmatched
        language has to be called out here or the card is just silent.
        """
        languages = self._requested_languages()
        if not languages:
            if not self.snapshot["synced"]:
                return ""
            return self._note("This sheet does not ask for any spoken field.")

        installed = {lang for _name, lang in self.voices}
        lines = []
        for language in languages:
            matches = [name for name, lang in self.voices if lang == language]
            if matches:
                lines.append(
                    f'<li style="color:{self.colors["accent_success"]};">'
                    f"{escape(language)} — {len(matches)} voice"
                    f"{'s' if len(matches) != 1 else ''} installed"
                    f' <span style="color:{self.colors["text_secondary"]};">'
                    f"({escape(', '.join(matches[:3]))}"
                    f"{'…' if len(matches) > 3 else ''})</span></li>"
                )
            else:
                near = sorted(
                    lang
                    for lang in installed
                    if lang.split("_")[0].lower() == language.split("_")[0].lower()
                )
                hint = (
                    f" Your system does have {escape(', '.join(near))}, "
                    "which Anki treats as a different language."
                    if near
                    else ""
                )
                lines.append(
                    f'<li style="color:{self.colors["accent_danger"]};">'
                    f"{escape(language)} — no voice installed for this language, "
                    f"so these fields will stay silent.{hint}</li>"
                )

        return (
            self._note("Languages this sheet asks for:")
            + f'<ul style="color:{self.colors["text"]};">{"".join(lines)}</ul>'
        )

    def _voice_list_html(self):
        if not self.voices:
            return self._note(
                "No speech voices are installed on this machine, so no field can "
                "be read aloud here.",
                self.colors["accent_warning"],
            )

        grouped = {}
        for name, lang in self.voices:
            grouped.setdefault(lang or "(unknown language)", []).append(name)

        items = "".join(
            f"<li><b>{escape(lang)}</b> — {escape(', '.join(names))}</li>"
            for lang, names in sorted(grouped.items())
        )
        return (
            self._note(f"Installed on this machine ({len(self.voices)}):")
            + f'<ul style="color:{self.colors["text"]};">{items}</ul>'
        )

    # ------------------------------------------------------------------
    # Section: preview
    # ------------------------------------------------------------------

    def _refresh_preview(self):
        if not self.snapshot["synced"]:
            self.preview_view.setHtml(self._never_synced_note())
            return
        try:
            html = self._preview_html()
        except Exception as error:  # a broken preview must not blank the window
            html = self._note(f"Could not build the preview: {error}")
        self.preview_view.setHtml(html)

    def _preview_html(self):
        """Renders every template the sheet's layout produces, with sample values."""
        templates = _build_templates_for(self.snapshot)
        if not templates:
            return self._approximate_preview_html()

        blocks = []
        for template in templates:
            front = _render_template(template["qfmt"])
            back = _render_template(
                template["afmt"].replace("{{FrontSide}}", _FRONT_SIDE_MARK)
            ).replace(_FRONT_SIDE_MARK, front)
            name = str(template.get("name") or "Card")
            blocks.append(self._preview_block(name, "Front", front))
            blocks.append(self._preview_block(name, "Back", back))
        return "".join(blocks)

    def _approximate_preview_html(self):
        """Fallback when the real templates are unavailable: the two sides only."""
        front, back = [], []
        for index, header in enumerate(self.snapshot["content_headers"]):
            settings = self.snapshot["fields"].get(header) or _field_settings(None)
            side = self._side_text(settings, index)
            if side == "hidden":
                continue
            (front if side.startswith("front") else back).append(
                self._preview_field(header, settings, side.startswith("front"))
            )

        if not front and not back:
            return self._note("This sheet has no content columns to show.")

        body = "".join(front) + "<hr>" + "".join(back)
        return self._preview_block("Card", "Front and back", body)

    def _theme_palette(self):
        """The sheet's ``theme``, in the variant matching Anki's current mode.

        A card theme is CSS custom properties plus a background, and a QTextBrowser
        resolves neither — so the preview has to be painted with the palette's own
        values. Showing the dialog's background while the real card is pink would
        say the setting did nothing.
        """
        palette = THEMES.get(self.snapshot["deck"].get("theme"))
        return palette["night" if is_dark_mode() else "light"] if palette else None

    def _preview_color(self, color):
        """A colour this preview can actually paint with.

        The sheet's theme colours (``muted``, ``accent``) become CSS variables on
        the real card, which a QTextBrowser cannot resolve — so they are shown in
        the sheet's own palette when it named a theme, and in the equivalent dialog
        colour otherwise, instead of silently rendering as no colour.
        """
        palette = self._theme_palette()
        value = str(color or "").strip()
        if not value:
            return (palette or {}).get("fg") or self.colors["text"]
        lowered = value.lower()
        if lowered == "muted" or lowered.startswith("var("):
            return (palette or {}).get("muted") or self.colors["text_secondary"]
        if lowered == "accent":
            return (palette or {}).get("accent") or self.colors["accent_primary"]
        return value

    def _preview_field(self, header, settings, is_front):
        """One field as it would appear, honouring size, colour and alignment."""
        size = settings.get("size") or (40 if is_front else 18)
        color = self._preview_color(settings.get("color"))
        align = settings.get("align") or self.snapshot["deck"].get("align") or "center"

        label = settings.get("label") or header
        head = (
            f'<div style="font-size:9pt;color:{self._preview_color("muted")};">'
            f"{escape(str(label))}</div>"
        )
        return (
            f'<div style="text-align:{escape(str(align))};">{head}'
            f'<div style="font-size:{size}px;color:{color};">'
            f"[{escape(header)}]</div></div>"
        )

    def _preview_block(self, template_name, side, body):
        palette = self._theme_palette()
        background = (palette or {}).get("bg") or self.colors["background"]
        return (
            f'<p style="color:{self.colors["text_secondary"]};font-size:10pt;'
            f'margin-bottom:2px;">{escape(template_name)} · {escape(side)}</p>'
            f'<div style="border:1px solid {self.colors["border"]};'
            f'background-color:{background};padding:10px;">{body}</div>'
            "<p>&nbsp;</p>"
        )


def show_card_layout_dialog(parent=None):
    """
    Utility function to show the card layout dialog.

    Args:
        parent: Parent widget (optional)

    Returns:
        bool: True if the dialog was closed normally, False otherwise
    """
    dialog = CardLayoutDialog(parent)
    result = safe_exec_dialog(dialog)
    return result == DialogAccepted
