"""Every icon the site asks for is one site/icons.js can draw.

`icon("nmae")` returns an empty string rather than throwing — decoration must not
stop a page drawing — so a typo leaves a button blank and says nothing. This is
what notices.
"""

import re
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parent.parent / "site"


def _defined():
    source = (SITE / "icons.js").read_text(encoding="utf-8")
    body = source.split("const PATHS = {", 1)[1].split("\n};", 1)[0]
    return set(re.findall(r'^  "?([\w-]+)"?:', body, re.M))


def _asked_for():
    asked = set()
    for path in SITE.iterdir():
        if path.suffix not in (".js", ".html") or path.name == "icons.js":
            continue
        text = path.read_text(encoding="utf-8")
        asked |= set(re.findall(r'\bicon\("([\w-]+)"', text))
        asked |= set(re.findall(r'data-icon="([\w-]+)"', text))
        for a, b in re.findall(r'\bicon\(\w+\(\) \? "([\w-]+)" : "([\w-]+)"\)', text):
            asked |= {a, b}
        for a, b in re.findall(r'\bicon\(\w+ \? "([\w-]+)" : "([\w-]+)"\)', text):
            asked |= {a, b}
    return asked


@pytest.mark.unit
def test_every_icon_asked_for_exists():
    missing = sorted(_asked_for() - _defined())
    assert not missing, f"site asks for icons icons.js does not define: {missing}"


@pytest.mark.unit
def test_every_icon_defined_is_used():
    unused = sorted(_defined() - _asked_for())
    assert not unused, f"site/icons.js defines icons nothing uses: {unused}"


@pytest.mark.unit
def test_icons_carry_no_colour_of_their_own():
    """currentColor or nothing, so an icon follows the text beside it in both themes."""
    source = (SITE / "icons.js").read_text(encoding="utf-8")
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", source.split("const PATHS", 1)[1])


@pytest.mark.unit
def test_the_anki_mark_ships_at_the_top_level():
    # build_site.py copies site/ files only, not folders — an image in a
    # subfolder would be a broken picture on the published page.
    assert (SITE / "anki.png").is_file()
    assert 'src="./anki.png"' in (SITE / "index.html").read_text(encoding="utf-8")
