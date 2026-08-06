"""Central design system for Sheets2Anki's Qt UI.

Single source of truth for **theme detection** and the **color palette** so every
dialog draws from one harmonized set of tokens instead of hardcoding its own colors.
The accent identity is blue: ``#4A90D9`` (light) / ``#5BA3E0`` (dark).

Historically each dialog re-implemented ``is_dark_mode()`` (via the unreliable
``bg_color.lightness() < 128``) and defined its own inline light/dark palette, which
produced ~75 distinct hardcoded colors mixing Material Design and Bootstrap. This module
replaces all of that.

``get_colors()`` returns a **superset** dict: the canonical semantic tokens (the ones
that originated in ``styled_messages.py``) PLUS back-compat alias keys that the existing
dialogs already reference (``accent_primary``, ``bg``, ``card_bg``, ``button_bg``,
``input_bg``, …). That way migrating a dialog is a one-line change
(``self.colors = get_colors()``) and ``styled_messages`` keeps its exact values.
"""


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


# -----------------------------------------------------------------------------
# LAYOUT SCALE (4px grid) — use these instead of ad-hoc margin/spacing numbers so
# every window shares the same rhythm.
# -----------------------------------------------------------------------------
MARGIN = 20  # dialog outer content margin (all four sides)
SPACE_SECTION = 16  # gap between sections
SPACE_ELEMENT = 12  # gap between elements within a section
SPACE_TIGHT = 8  # label <-> field, icon <-> text

# Border-radius scale.
RADIUS_CARD = "12px"  # header banner, section cards, group boxes
RADIUS_CONTROL = "8px"  # buttons, inputs, dropdowns
RADIUS_SMALL = "6px"  # badges, pills, status chips

# =============================================================================
# PALETTES
# -----------------------------------------------------------------------------
# The first 16 keys of each dict are the canonical semantic tokens and keep the exact
# values that ``styled_messages.get_colors()`` used, so message boxes are unchanged.
# The remaining keys are aliases the dialogs already reference, harmonized onto the same
# blue identity (this is what collapses the old ~75-color sprawl).
# =============================================================================

_LIGHT = {
    # --- canonical semantic tokens (unchanged from styled_messages) ---
    "primary": "#4A90D9",
    "primary_dark": "#357ABD",
    "primary_light": "#E8F4FC",
    "success": "#28A745",
    "success_light": "#D4EDDA",
    "warning": "#FFC107",
    "warning_light": "#FFF3CD",
    "error": "#DC3545",
    "error_light": "#F8D7DA",
    "text_primary": "#2C3E50",
    "text_secondary": "#5C656D",
    "text_muted": "#ADB5BD",
    "background": "#FFFFFF",
    "background_secondary": "#F8F9FA",
    "border": "#DEE2E6",
    "border_light": "#E9ECEF",
    "header_gradient_start": "#4A90D9",
    "header_gradient_end": "#357ABD",
    # --- dialog aliases (harmonized to the blue identity) ---
    "text": "#2C3E50",  # == text_primary
    "bg": "#F5F5F5",  # dialog window (recessed surface)
    "card_bg": "#FFFFFF",  # raised panel (== background)
    "list_bg": "#FFFFFF",
    "input_bg": "#FFFFFF",
    "accent_primary": "#4A90D9",
    "accent_success": "#28A745",
    "accent_warning": "#FFC107",
    "accent_info": "#4A90D9",  # info folds into the primary blue
    "accent_danger": "#DC3545",
    "accent_purple": "#7B1FA2",
    # hover/pressed (darker) shades for filled action buttons
    "success_dark": "#218838",
    "danger_dark": "#C0392B",
    "warning_dark": "#E0A800",
    "button_bg": "#E9ECEF",
    "button_hover": "#DEE2E6",
    "row_hover": "#E8F4FC",
    "warning_bg": "#FFF3CD",
}

_DARK = {
    # --- canonical semantic tokens (unchanged from styled_messages) ---
    "primary": "#5BA3E0",
    "primary_dark": "#4A90D9",
    "primary_light": "#2A3F50",
    "success": "#3CB371",
    "success_light": "#1E3A2A",
    "warning": "#E6A817",
    "warning_light": "#3D3520",
    "error": "#E05555",
    "error_light": "#3D2020",
    "text_primary": "#E0E0E0",
    "text_secondary": "#B0B0B0",
    "text_muted": "#707070",
    "background": "#2D2D2D",
    "background_secondary": "#383838",
    "border": "#505050",
    "border_light": "#454545",
    "header_gradient_start": "#3A5A7C",
    "header_gradient_end": "#2A4A6A",
    # --- dialog aliases (harmonized to the blue identity) ---
    "text": "#E0E0E0",  # == text_primary
    "bg": "#1E1E1E",  # dialog window (recessed surface)
    "card_bg": "#2D2D2D",  # raised panel (== background)
    "list_bg": "#2D2D2D",
    "input_bg": "#3D3D3D",
    "accent_primary": "#5BA3E0",
    "accent_success": "#3CB371",
    "accent_warning": "#E6A817",
    "accent_info": "#5BA3E0",
    "accent_danger": "#E05555",
    "accent_purple": "#9C27B0",
    # hover/pressed (darker) shades for filled action buttons
    "success_dark": "#2E9E5B",
    "danger_dark": "#C0392B",
    "warning_dark": "#C99000",
    "button_bg": "#3D3D3D",
    "button_hover": "#4A4A4A",
    "row_hover": "#2A3F50",
    "warning_bg": "#3D3520",
}


def get_colors() -> dict:
    """Return the active palette (dark or light) as a fresh dict.

    A copy is returned so callers can't mutate the module-level constants.
    """
    return dict(_DARK if is_dark_mode() else _LIGHT)


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
