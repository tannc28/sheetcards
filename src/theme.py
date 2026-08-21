"""SheetCards's Qt UI draws from Anki's palette, not from one of its own.

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
# LAYOUT SCALE — spacing, and nothing else. There used to be a border-radius scale
# here too, and a set of QSS builders under it for banners, cards, group boxes and
# filled buttons. All of it is gone with the windows that drew them: Anki's global
# stylesheet already gives every control the radius and the fill it wants, and a
# second one on top is precisely what read as a different application.
# -----------------------------------------------------------------------------
MARGIN = 12  # dialog outer content margin (all four sides)
SPACE_SECTION = 12  # gap between sections
SPACE_ELEMENT = 8  # gap between elements within a section
SPACE_TIGHT = 6  # label <-> field, icon <-> text

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
# ICONS
# -----------------------------------------------------------------------------
# Anki draws its own icons as SVGs recoloured to the theme, and uses no emoji at
# all — a grep of `aqt/` turns up one llama. So these are SVGs too, eight of them
# in `src/icons/`, each written with the literal `INK` where a colour goes.
# `icon()` substitutes one of Anki's own colours and renders the result, which is
# what keeps a warning triangle the same red as the sentence beside it and keeps
# both legible on either theme.
#
# Emoji would have been fewer lines, but they belong to the font rather than to
# the theme: colour on macOS and Windows, monochrome or missing on a Linux box
# without Noto Color Emoji, a different size and baseline in each, and never the
# colour of the text they sit beside.
# =============================================================================

# 16px, the size Anki gives an icon beside a line of text.
ICON_SIZE = 16

# Where a radio button's text starts, so a sentence under it lines up with the
# words rather than with the dot.
RADIO_INDENT = 22

_ICON_CACHE: dict = {}


def icon(name: str, color: str = "text"):
    """The named icon from ``src/icons``, inked in one of Anki's colours.

    ``color`` is a key of :func:`get_colors`, so an icon changes with night mode
    the same way the text around it does. Returns an empty ``QIcon`` when Qt is not
    importable or the file is missing: an icon is decoration, and a window that
    fails to open because one is absent would be a poor trade.
    """
    from .compat import QIcon
    from .compat import QPixmap

    ink = get_colors().get(color, color)
    key = (name, ink)
    if key in _ICON_CACHE:
        return _ICON_CACHE[key]

    result = QIcon()
    try:
        import os

        path = os.path.join(os.path.dirname(__file__), "icons", f"{name}.svg")
        with open(path, encoding="utf-8") as handle:
            svg = handle.read().replace("INK", ink)
        pixmap = QPixmap()
        # Rendered from the string rather than from the file: the file on disk has
        # no colour in it, only the word INK.
        if pixmap.loadFromData(svg.encode("utf-8"), "SVG"):
            result = QIcon(pixmap)
    except Exception:
        pass

    _ICON_CACHE[key] = result
    return result
