"""Sheets2Anki's Qt UI draws from Anki's palette, not from one of its own.

An add-on window sits among Anki's own windows, and every colour it invents is a
colour that will disagree with them — on one of the two themes if not both, and on
whatever Anki ships next. So there is no palette here. ``get_colors()`` resolves
each name against **`aqt.colors`**, the same table Anki styles itself from, through
``theme_manager.var()``, which picks the light or dark value the way the rest of the
app does.

This module used to hold ~75 hand-picked hex values across two dicts, on an accent
(``#4A90D9``) that was nobody's but ours: white cards on Anki's grey canvas, a blue
gradient banner over every dialog, buttons with a border radius Anki does not use.
It looked like a Bootstrap page embedded in Anki, which is what it was.

The key names are kept because the dialogs that have not been rewritten yet still
ask for them; each now resolves to the nearest thing Anki actually has. A dialog
being rewritten should stop asking altogether — Anki styles `QPushButton`,
`QLineEdit`, `QListWidget` and the rest through a global stylesheet, so **the most
native thing a dialog can do is set no stylesheet at all**.
"""

# Anki's own values, copied for the case where aqt is not importable — the test
# suite mocks it away. `aqt.colors` is the source; this is a mirror of the handful
# of entries used here, and `_var` prefers the real thing whenever it is there.
_FALLBACK = {
    "CANVAS": ("#f5f5f5", "#2c2c2c"),
    "CANVAS_ELEVATED": ("white", "#363636"),
    "CANVAS_INSET": ("white", "#2c2c2c"),
    "CANVAS_CODE": ("white", "#252525"),
    "FG": ("#020202", "#fcfcfc"),
    "FG_SUBTLE": ("#737373", "#858585"),
    "FG_FAINT": ("#afafaf", "#545454"),
    "FG_DISABLED": ("#858585", "#737373"),
    "FG_LINK": ("#1d4ed8", "#bfdbfe"),
    "BORDER": ("#c4c4c4", "#202020"),
    "BORDER_SUBTLE": ("#e4e4e4", "#252525"),
    "BORDER_STRONG": ("#858585", "#020202"),
    "BORDER_FOCUS": ("#3b82f6", "#3b82f6"),
    "BUTTON_BG": ("#fcfcfc", "#404040"),
    "BUTTON_HOVER_BORDER": ("#999999", "#141414"),
    "SELECTED_BG": ("rgba(214, 214, 214, 0.5)", "rgba(147, 197, 253, 0.5)"),
    "SELECTED_FG": ("black", "white"),
    "ACCENT_CARD": ("#60a5fa", "#93c5fd"),
    "ACCENT_NOTE": ("#22c55e", "#4ade80"),
    "ACCENT_DANGER": ("#ef4444", "#f87171"),
    "STATE_LEARN": ("#dc2626", "#f87171"),
    "STATE_REVIEW": ("#16a34a", "#22c55e"),
    "HIGHLIGHT_BG": ("rgba(37, 99, 235, 0.5)", "rgba(147, 197, 253, 0.5)"),
    "HIGHLIGHT_FG": ("black", "white"),
}


def is_dark_mode() -> bool:
    """Return True when Anki is in night mode. The single source of truth.

    Prefer Anki's ``theme_manager.night_mode`` over palette-lightness heuristics, which
    can misread custom themes.
    """
    try:
        from aqt import theme

        if hasattr(theme, "theme_manager"):
            return bool(theme.theme_manager.night_mode)
        # Fallback for older Anki versions.
        from aqt import mw as main_window

        if main_window and hasattr(main_window, "pm"):
            return bool(main_window.pm.night_mode())
    except Exception:
        pass
    return False


def _var(name: str) -> str:
    """One colour out of Anki's table, resolved for the theme in force.

    The result is checked to be a hex string rather than trusted: the test suite
    fabricates `aqt`, and a mock answers `getattr` and `[]` with another mock quite
    happily. A colour that is silently a mock is a stylesheet that silently does
    nothing, which is the failure this module exists to stop.
    """
    dark = is_dark_mode()
    try:
        import aqt.colors

        value = getattr(aqt.colors, name)["dark" if dark else "light"]
        # A plain `str` and nothing else. Anki writes some of these as CSS names
        # rather than hex ("white", "black"), so the check is on the type, not the
        # shape — and a mock, which answers both getattr and [], is not a str.
        if type(value) is str and value:
            return value
    except Exception:
        pass
    light, night = _FALLBACK[name]
    return night if dark else light


# -----------------------------------------------------------------------------
# LAYOUT SCALE — Anki's dialogs are laid out on plain Qt defaults with a little
# breathing room, so this is spacing only. The border-radius scale that used to
# live here is gone with the cards it drew: Anki's global stylesheet already gives
# every control the radius it wants, and a second one on top is the thing that
# reads as a different application.
# -----------------------------------------------------------------------------
MARGIN = 12  # dialog outer content margin (all four sides)
SPACE_SECTION = 12  # gap between sections
SPACE_ELEMENT = 8  # gap between elements within a section
SPACE_TIGHT = 6  # label <-> field, icon <-> text

# Anki rounds every control it styles by 5px (aqt/stylesheets.py). These are here
# only for the dialogs still drawing their own boxes; a rewritten dialog draws none
# and inherits the radius with the rest of the style. They go when the last one does.
RADIUS_CARD = "5px"
RADIUS_CONTROL = "5px"
RADIUS_SMALL = "5px"

# =============================================================================
# THE PALETTE — every entry is a name in `aqt.colors`
# -----------------------------------------------------------------------------
# Left column: the names the dialogs already ask for. Right column: what Anki calls
# the nearest real thing. Where the old palette drew a distinction Anki does not
# make — four accents, a separate list background, a hover shade per button — the
# entries collapse onto the one colour Anki has, which is the point: a distinction
# invented here is a distinction that will not match anything around it.
# =============================================================================

_TOKENS = {
    # --- canonical semantic tokens ---
    "primary": "ACCENT_CARD",
    "primary_dark": "ACCENT_CARD",
    "primary_light": "SELECTED_BG",
    "success": "ACCENT_NOTE",
    "success_light": "CANVAS_INSET",
    "warning": "STATE_LEARN",
    "warning_light": "CANVAS_INSET",
    "error": "ACCENT_DANGER",
    "error_light": "CANVAS_INSET",
    "text_primary": "FG",
    "text_secondary": "FG_SUBTLE",
    "text_muted": "FG_FAINT",
    "background": "CANVAS_ELEVATED",
    "background_secondary": "CANVAS_INSET",
    "border": "BORDER",
    "border_light": "BORDER_SUBTLE",
    "header_gradient_start": "ACCENT_CARD",
    "header_gradient_end": "ACCENT_CARD",
    # --- dialog aliases ---
    "text": "FG",
    "bg": "CANVAS",
    "card_bg": "CANVAS_ELEVATED",
    "list_bg": "CANVAS_ELEVATED",
    "input_bg": "CANVAS_ELEVATED",
    "accent_primary": "ACCENT_CARD",
    "accent_success": "ACCENT_NOTE",
    "accent_warning": "STATE_LEARN",
    "accent_info": "ACCENT_CARD",
    "accent_danger": "ACCENT_DANGER",
    "accent_purple": "ACCENT_CARD",
    "success_dark": "ACCENT_NOTE",
    "danger_dark": "ACCENT_DANGER",
    "warning_dark": "STATE_LEARN",
    "button_bg": "BUTTON_BG",
    "button_hover": "BUTTON_HOVER_BORDER",
    "row_hover": "SELECTED_BG",
    "warning_bg": "CANVAS_INSET",
    # --- names the rewritten dialogs use ---
    "link": "FG_LINK",
    "selected_bg": "SELECTED_BG",
    "selected_text": "SELECTED_FG",
    "code_bg": "CANVAS_CODE",
    "focus": "BORDER_FOCUS",
}


def get_colors() -> dict:
    """Anki's palette, under the names this add-on's dialogs ask for.

    Resolved on every call rather than cached: night mode is switched while Anki is
    running, and a dialog opened after the switch has to come up in the theme that
    is in force, not the one that was.
    """
    return {name: _var(token) for name, token in _TOKENS.items()}


# =============================================================================
# REUSABLE QSS HELPERS
# -----------------------------------------------------------------------------
# Shared stylesheet snippets so dialogs stop hand-rolling button/header styling. Each
# takes the palette dict from ``get_colors()`` and returns a QSS string.
# =============================================================================


def scrollbar_qss(colors: dict) -> str:
    """A thin, modern, arrow-less scrollbar — themed and identical app-wide.

    Append this to a dialog's stylesheet so every scroll area, list and text view
    in that dialog gets the same scrollbar instead of the native one (which renders
    differently per widget type and OS).
    """
    thumb = colors["text_muted"]
    thumb_hover = colors["text_secondary"]
    return f"""
        QScrollBar:vertical {{
            background: transparent;
            width: 12px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {thumb};
            border-radius: 6px;
            min-height: 32px;
        }}
        QScrollBar::handle:vertical:hover {{ background: {thumb_hover}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: transparent;
        }}
        QScrollBar:horizontal {{
            background: transparent;
            height: 12px;
            margin: 0;
        }}
        QScrollBar::handle:horizontal {{
            background: {thumb};
            border-radius: 6px;
            min-width: 32px;
        }}
        QScrollBar::handle:horizontal:hover {{ background: {thumb_hover}; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: transparent;
        }}
    """


def groupbox_qss(colors: dict) -> str:
    """Consistent section delimitation for every QGroupBox — a rounded card with a
    titled border, identical across all dialogs."""
    return f"""
        QGroupBox {{
            background-color: {colors['card_bg']};
            border: 1px solid {colors['border']};
            border-radius: {RADIUS_CARD};
            margin-top: 14px;
            padding: {SPACE_SECTION}px;
            padding-top: {SPACE_SECTION + 4}px;
            font-size: 13pt;
            font-weight: bold;
            color: {colors['text']};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 14px;
            top: 1px;
            padding: 0 6px;
            color: {colors['text_secondary']};
        }}
    """


def base_dialog_qss(colors: dict) -> str:
    """Shared base styling appended to every dialog: a consistent scrollbar and a
    consistent QGroupBox delimitation. Append after the dialog's own stylesheet."""
    return scrollbar_qss(colors) + groupbox_qss(colors)


# =============================================================================
# REUSABLE WIDGET BUILDERS
# -----------------------------------------------------------------------------
# Small widget factories so dialogs stop re-implementing the same banner/option-card.
# =============================================================================


def make_header(colors: dict, title: str, subtitle: str = ""):
    """Build the standard gradient header banner used at the top of every dialog.

    Returns a ``QFrame`` (objectName ``headerFrame``) with the blue gradient
    background, a bold white title and an optional white subtitle — replacing the
    per-dialog copies of this exact block.
    """
    from .compat import QFrame
    from .compat import QLabel
    from .compat import QVBoxLayout

    frame = QFrame()
    frame.setObjectName("headerFrame")
    frame.setStyleSheet(f"""
        QFrame#headerFrame {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {colors['header_gradient_start']},
                stop:1 {colors['header_gradient_end']});
            border-radius: {RADIUS_CARD};
        }}
        QFrame#headerFrame QLabel {{
            background: transparent;
            color: white;
            border: none;
        }}
        """)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(MARGIN, 15, MARGIN, 15)
    layout.setSpacing(6)

    title_label = QLabel(title)
    title_label.setStyleSheet("font-size: 18pt; font-weight: bold;")
    layout.addWidget(title_label)

    if subtitle:
        subtitle_label = QLabel(subtitle)
        subtitle_label.setStyleSheet("font-size: 12pt; opacity: 0.9;")
        subtitle_label.setWordWrap(True)
        layout.addWidget(subtitle_label)

    return frame


def make_radio_option_card(
    colors: dict,
    *,
    key: str,
    checked: bool,
    title: str,
    badge: str,
    description: str,
    accent_color: str,
    button_group,
    button_id: int,
):
    """Build a clickable radio "option card" (radio + title/badge/description).

    Used by the deck-options dialog for its mode picker. Adds ``radio`` to
    ``button_group`` under ``button_id`` and makes the whole card click-to-select.
    """
    from .compat import QFrame
    from .compat import QHBoxLayout
    from .compat import QLabel
    from .compat import QRadioButton
    from .compat import QVBoxLayout

    card = QFrame()
    card.setObjectName(f"card_{key}")
    card.setStyleSheet(f"""
        QFrame#card_{key} {{
            background-color: {colors['card_bg']};
            border: 2px solid {colors['border']};
            border-radius: 10px;
            padding: 5px;
        }}
        QFrame#card_{key}:hover {{
            border-color: {accent_color};
        }}
    """)

    card_layout = QHBoxLayout(card)
    card_layout.setContentsMargins(15, 12, 15, 12)
    card_layout.setSpacing(15)

    radio = QRadioButton()
    radio.setChecked(checked)
    radio.setStyleSheet(f"""
        QRadioButton::indicator {{
            width: 22px;
            height: 22px;
        }}
        QRadioButton::indicator:checked {{
            background-color: {colors['accent_primary']};
            border: 2px solid {colors['accent_primary']};
            border-radius: 11px;
        }}
        QRadioButton::indicator:unchecked {{
            background-color: {colors['card_bg']};
            border: 2px solid {colors['border']};
            border-radius: 11px;
        }}
    """)
    button_group.addButton(radio, button_id)
    card_layout.addWidget(radio)

    content_layout = QVBoxLayout()
    content_layout.setSpacing(4)

    title_row = QHBoxLayout()
    title_label = QLabel(title)
    title_label.setStyleSheet(
        f"font-size: 13pt; font-weight: bold; color: {colors['text']};"
    )
    title_row.addWidget(title_label)

    badge_label = QLabel(badge)
    badge_label.setStyleSheet(f"""
        background-color: {accent_color};
        color: white;
        font-size: 12pt;
        font-weight: bold;
        padding: 3px 10px;
        border-radius: 10px;
    """)
    title_row.addWidget(badge_label)
    title_row.addStretch()
    content_layout.addLayout(title_row)

    desc_label = QLabel(description)
    desc_label.setStyleSheet(f"font-size: 12pt; color: {colors['text_secondary']};")
    desc_label.setWordWrap(True)
    content_layout.addWidget(desc_label)

    card_layout.addLayout(content_layout, 1)

    card.mousePressEvent = lambda e: radio.setChecked(True)
    return card


def primary_button_qss(colors: dict, kind: str = "primary") -> str:
    """Filled action button (Save / Apply / Confirm). kind: 'primary'|'success'|'danger'."""
    accent = {
        "primary": colors["accent_primary"],
        "success": colors["accent_success"],
        "danger": colors["accent_danger"],
    }[kind]
    hover = {
        "primary": colors["primary_dark"],
        "success": colors["success_dark"],
        "danger": colors["danger_dark"],
    }[kind]
    return f"""
        QPushButton {{
            background-color: {accent};
            color: white;
            border: none;
            border-radius: {RADIUS_CONTROL};
            padding: 12px 25px;
            font-size: 12pt;
            font-weight: bold;
        }}
        QPushButton:hover {{ background-color: {hover}; }}
        QPushButton:disabled {{
            background-color: {colors['button_bg']};
            color: {colors['text_muted']};
        }}
    """


def secondary_button_qss(colors: dict) -> str:
    """Filled-grey secondary button (Cancel / secondary actions)."""
    return f"""
        QPushButton {{
            background-color: {colors['button_bg']};
            color: {colors['text']};
            border: 1px solid {colors['border']};
            border-radius: {RADIUS_CONTROL};
            padding: 12px 25px;
            font-size: 12pt;
        }}
        QPushButton:hover {{ background-color: {colors['button_hover']}; }}
    """
