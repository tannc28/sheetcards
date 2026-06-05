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


# Base font size for the UI, in points (pt scales with the user's system DPI / font
# settings; px does not). Use this instead of hardcoding mixed pt/px sizes.
FONT_PT = 12

# Corner radius and the standard control padding, kept identical everywhere.
RADIUS = "6px"

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


def primary_button_qss(colors: dict, destructive: bool = False) -> str:
    """QSS for a filled primary (or destructive) call-to-action button."""
    bg = colors["error"] if destructive else colors["primary"]
    hover = "#C0392B" if destructive else colors["primary_dark"]
    return f"""
        QPushButton {{
            background-color: {bg};
            color: #ffffff;
            border: none;
            border-radius: {RADIUS};
            font-size: {FONT_PT}pt;
            font-weight: bold;
            padding: 8px 20px;
            min-width: 80px;
        }}
        QPushButton:hover {{ background-color: {hover}; }}
        QPushButton:disabled {{ background-color: {colors['text_muted']}; }}
    """


def secondary_button_qss(colors: dict) -> str:
    """QSS for a neutral, outlined secondary button."""
    return f"""
        QPushButton {{
            background-color: {colors['background']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border']};
            border-radius: {RADIUS};
            font-size: {FONT_PT}pt;
            font-weight: 500;
            padding: 8px 16px;
            min-width: 70px;
        }}
        QPushButton:hover {{
            background-color: {colors['background_secondary']};
            border-color: {colors['text_secondary']};
        }}
    """


def header_qss(colors: dict) -> str:
    """QSS for a gradient page header (white text on the brand gradient).

    Apply to a header ``QFrame``/``QWidget`` so every dialog gets the same banner.
    """
    return f"""
        QWidget {{
            background-color: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 {colors['header_gradient_start']},
                stop:1 {colors['header_gradient_end']}
            );
            border-top-left-radius: {RADIUS};
            border-top-right-radius: {RADIUS};
        }}
        QLabel {{ color: #ffffff; background: transparent; }}
    """
