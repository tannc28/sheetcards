#!/usr/bin/env python3
"""The add-on's dialogs draw from Anki's palette, and this is what holds them to it.

An add-on window sits among Anki's own windows. Every colour it invents is a colour
that will disagree with them on one theme or the other, and on whatever Anki ships
next — which is how this module came to hold seventy-five hand-picked hex values on
an accent that was nobody's but ours.

So the invariant is not *which* colours: it is that there are none. Every name maps
to an entry in `aqt.colors`, the same table Anki styles itself from.
"""

import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

from src.theme import _FALLBACK
from src.theme import _TOKENS
from src.theme import get_colors
from src.theme import is_dark_mode

REPO = Path(__file__).resolve().parent.parent

# Every colour key any dialog reaches for. A missing one is an f-string KeyError at
# the moment a window opens.
_REQUIRED_KEYS = {
    "text", "border", "card_bg", "text_secondary", "accent_primary", "button_bg",
    "accent_success", "button_hover", "bg", "input_bg", "accent_warning", "accent_info",
    "accent_danger", "accent_purple", "row_hover", "list_bg", "warning_bg", "primary",
    "background_secondary", "text_primary", "background", "text_muted", "primary_light",
    "warning_light", "success", "warning", "error", "success_light", "error_light",
    "border_light", "header_gradient_start", "header_gradient_end",
}  # fmt: skip


@pytest.mark.unit
class TestNoColourIsInvented:
    def test_every_name_resolves_to_a_colour_anki_has(self):
        assert set(_TOKENS.values()) <= set(
            _FALLBACK
        ), "a token name with no entry in the mirror falls back to a KeyError"

    def test_the_module_holds_no_palette_of_its_own(self):
        """The only hex literals allowed are the mirror of Anki's own values.

        A colour written anywhere else is one nobody chose against Anki's, and the
        seventy-five that used to be here are exactly how the dialogs came to look
        like a different application.
        """
        source = (REPO / "src" / "theme.py").read_text(encoding="utf-8")
        # The module docstring names the old accent in order to say it is gone.
        code = source[source.index("_FALLBACK = {") :]
        mirror = code[: code.index("def is_dark_mode")]
        assert not re.findall(r"#[0-9a-fA-F]{6}\b", code.replace(mirror, ""))


@pytest.mark.unit
class TestWhatTheDialogsAskFor:
    def test_every_key_a_dialog_uses_is_there(self):
        assert _REQUIRED_KEYS <= set(get_colors())

    def test_every_value_is_a_colour(self):
        # Under the suite's mocked `aqt`, `getattr` and `[]` both answer with another
        # mock rather than raising, so a value that is not a string means the guard
        # in `_var` stopped working and the stylesheets would silently do nothing.
        # Anki writes these three ways — hex, a CSS name (CANVAS_ELEVATED is
        # "white") and rgba() for the translucent ones — so the check is that it is
        # something Qt will accept, and never the `<Mock id=...>` a fabricated aqt
        # hands back for any attribute asked of it.
        shape = re.compile(r"#[0-9a-fA-F]{3,8}|[a-z]+|rgba?\([\d.,%\s]+\)")
        for key, value in get_colors().items():
            assert type(value) is str and shape.fullmatch(value), f"{key} is {value!r}"

    def test_the_caller_cannot_reach_the_module_state(self):
        colours = get_colors()
        colours["text"] = "#000000"
        assert get_colors()["text"] != "#000000" or colours is not get_colors()


@pytest.mark.unit
class TestTheThemeInForce:
    def test_dark_mode_is_asked_of_anki_not_guessed(self):
        assert isinstance(is_dark_mode(), bool)

    def test_the_two_themes_are_not_the_same(self, monkeypatch):
        import src.theme as theme

        monkeypatch.setattr(theme, "is_dark_mode", lambda: False)
        light = theme.get_colors()
        monkeypatch.setattr(theme, "is_dark_mode", lambda: True)
        dark = theme.get_colors()
        assert light["bg"] != dark["bg"] and light["text"] != dark["text"]

    def test_it_is_read_again_every_time(self, monkeypatch):
        # Night mode is switched while Anki is running, and a dialog opened after the
        # switch has to come up in the theme that is in force, not the one that was.
        import src.theme as theme

        monkeypatch.setattr(theme, "is_dark_mode", lambda: False)
        was = theme.get_colors()["bg"]
        monkeypatch.setattr(theme, "is_dark_mode", lambda: True)
        assert theme.get_colors()["bg"] != was


_HAS_ANKI = importlib.util.find_spec("anki") is not None


@pytest.mark.slow
@pytest.mark.skipif(not _HAS_ANKI, reason="the real anki library is not installed")
def test_the_mirror_still_matches_anki():
    """`_FALLBACK` is a copy, and a copy goes stale.

    It is only reached when `aqt` cannot be imported, so a value that drifted would
    never show up in Anki and never show up in this suite either — it would show up
    on a machine where the import failed, which is the machine least able to say so.
    """
    code = f"""
import json, sys
sys.path.insert(0, {str(REPO)!r})
import aqt.colors
from src.theme import _FALLBACK
print(json.dumps({{
    name: [aqt.colors.__dict__[name]["light"], aqt.colors.__dict__[name]["dark"]]
    for name in _FALLBACK
    if name in aqt.colors.__dict__
}}))
"""
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, cwd=str(REPO)
    )
    if result.returncode != 0:
        pytest.skip(f"aqt will not import here: {result.stderr.strip()[-200:]}")

    import json

    # The last line only: importing `src` runs the add-on's entry point, which
    # prints a line of its own when the local meta.json has debug logging on.
    payload = result.stdout.strip().splitlines()[-1]
    for name, (light, dark) in json.loads(payload).items():
        assert _FALLBACK[name] == (light, dark), f"{name} drifted from aqt.colors"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
