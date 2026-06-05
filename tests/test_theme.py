"""Tests for the shared design-system module (``src/theme.py``).

These lock in two invariants:
1. The canonical tokens keep the exact values the StyledMessageBox relies on, so message
   boxes never drift.
2. ``get_colors()`` is a drop-in for every color key the dialogs reference, so a dialog
   migration is a one-line ``self.colors = get_colors()``.
"""

import pytest

from src.theme import _DARK
from src.theme import _LIGHT
from src.theme import get_colors
from src.theme import is_dark_mode

# The 16 canonical light-mode tokens must keep these exact values (StyledMessageBox).
_EXPECTED_LIGHT_CANONICAL = {
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
}

# Every color key any dialog references today (so get_colors() works for all of them).
_REQUIRED_KEYS = {
    "text", "border", "card_bg", "text_secondary", "accent_primary", "button_bg",
    "accent_success", "button_hover", "bg", "input_bg", "accent_warning", "accent_info",
    "accent_danger", "accent_purple", "row_hover", "list_bg", "warning_bg", "primary",
    "background_secondary", "text_primary", "background", "text_muted", "primary_light",
    "warning_light", "success", "warning", "error", "success_light", "error_light",
    "border_light", "header_gradient_start", "header_gradient_end",
}  # fmt: skip


@pytest.mark.unit
class TestThemePalette:
    def test_canonical_light_values_unchanged(self):
        for key, value in _EXPECTED_LIGHT_CANONICAL.items():
            assert _LIGHT[key] == value, f"canonical token {key!r} drifted"

    def test_both_palettes_define_every_dialog_key(self):
        assert _REQUIRED_KEYS <= set(_LIGHT)
        assert _REQUIRED_KEYS <= set(_DARK)

    def test_light_and_dark_define_identical_keys(self):
        assert set(_LIGHT) == set(_DARK)

    def test_all_values_are_hex_colors(self):
        for palette in (_LIGHT, _DARK):
            for key, value in palette.items():
                assert value.startswith("#") and len(value) == 7, f"{key}={value}"

    def test_get_colors_returns_a_mutable_copy(self):
        colors = get_colors()
        assert isinstance(colors, dict)
        colors["primary"] = "#000000"
        assert _LIGHT["primary"] != "#000000"
        assert _DARK["primary"] != "#000000"

    def test_is_dark_mode_returns_bool(self):
        assert isinstance(is_dark_mode(), bool)


@pytest.mark.unit
def test_every_dialog_color_key_is_defined():
    """Every color key referenced by a dialog must exist in get_colors().

    Dialog stylesheets are f-strings evaluated only at widget-construction time, so a
    typo'd or missing key wouldn't surface until that dialog opens in Anki. This scans
    the source and fails fast instead.
    """
    import pathlib
    import re

    ui_dir = pathlib.Path(__file__).resolve().parent.parent / "src" / "ui"
    available = set(get_colors())
    key_re = re.compile(r"(?:self\.colors|\bc)\[['\"]([a-z_]+)['\"]\]")
    used: set[str] = set()
    for path in ui_dir.glob("*.py"):
        used |= set(key_re.findall(path.read_text(encoding="utf-8")))
    assert used, "scan found no color-key references — regex likely broke"
    missing = used - available
    assert not missing, f"dialogs reference undefined color keys: {sorted(missing)}"
