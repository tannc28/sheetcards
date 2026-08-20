#!/usr/bin/env python3
"""The icons the dialogs ask for, and the one way they can fail silently.

`theme.icon()` returns an empty `QIcon` when anything goes wrong — a missing file,
a Qt that will not import — because a window that refuses to open over a piece of
decoration would be the worse outcome. The cost of that choice is that a typo in a
name produces nothing at all, with no error, in a place nobody looks twice at. So
the names are checked against the files here instead.
"""

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
ICONS = REPO / "src" / "icons"


def _asked_for():
    """(name, file) for every `icon("name")` written anywhere in `src/`."""
    for path in sorted(REPO.glob("src/**/*.py")):
        source = path.read_text(encoding="utf-8")
        for name in re.findall(r'\bicon\(\s*"([\w-]+)"', source):
            yield name, path.relative_to(REPO)


@pytest.mark.unit
class TestTheFilesExist:
    def test_every_icon_a_dialog_asks_for_is_on_disk(self):
        for name, path in _asked_for():
            assert (ICONS / f"{name}.svg").exists(), f"{path} asks for {name!r}"

    def test_nothing_is_shipped_that_nothing_uses(self):
        """An icon nobody draws is a file in the package for no reason.

        Scanned for the name in quotes rather than for a call, because a name also
        travels as data — `_show_status` maps a state to a shape and hands the
        result to `icon()` — and a file used that way is used.
        """
        source = "".join(
            path.read_text(encoding="utf-8") for path in REPO.glob("src/**/*.py")
        )
        unused = [
            path.stem
            for path in sorted(ICONS.glob("*.svg"))
            if f'"{path.stem}"' not in source
        ]
        assert not unused


@pytest.mark.unit
class TestTheyCanBeThemed:
    def test_every_icon_leaves_its_colour_to_the_theme(self):
        """`INK` is the whole mechanism: no `INK`, no night mode.

        A colour written into one of these files would be a colour that stays put
        when Anki's does not — which is the failure the palette rewrite was for,
        reappearing one file lower down.
        """
        for path in sorted(ICONS.glob("*.svg")):
            body = path.read_text(encoding="utf-8")
            assert "INK" in body, f"{path.name} has no colour to replace"
            assert not re.findall(
                r"#[0-9a-fA-F]{3,6}\b", body
            ), f"{path.name} paints itself"

    def test_every_icon_is_well_formed(self):
        from xml.etree import ElementTree

        for path in sorted(ICONS.glob("*.svg")):
            # Parsed with the placeholder still in it: `INK` is a valid attribute
            # value, and a file that only parses once substituted is a file that
            # can break for one theme and not the other.
            ElementTree.fromstring(path.read_text(encoding="utf-8"))

    def test_they_are_square_and_the_same_size(self):
        # Different viewBoxes would give the same 16px request different amounts of
        # ink, which reads as one icon being bolder than its neighbour.
        boxes = {
            path.stem: re.search(r'viewBox="([^"]+)"', path.read_text(encoding="utf-8"))
            for path in sorted(ICONS.glob("*.svg"))
        }
        found = {name: match.group(1) for name, match in boxes.items() if match}
        assert found and set(found.values()) == {"0 0 24 24"}, found


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
