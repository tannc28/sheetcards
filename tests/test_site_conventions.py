"""The things every website does that nobody notices until one is missing.

Each of these shipped missing once and was found by a reader, not by a test: the
name in the masthead that did not go home, a sideways scroll on Create deck, a
Back button that left the site with the sheet, a missing address answered by
GitHub's own 404 page. They are cheap to check and silent when they break, so
they are checked here.
"""

import re
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parent.parent / "site"

# Every page with the shared masthead. player.html is a frame inside a card and
# preview.html a redirect; neither has chrome.
PAGES = ("index.html", "create.html", "editor.html", "_docs.html", "404.html")

# How each page spells the way back to the site's root.
ROOTS = {"./", "%%ROOT%%"}


def _text(name):
    return (SITE / name).read_text(encoding="utf-8")


@pytest.mark.unit
@pytest.mark.parametrize("page", PAGES)
def test_the_name_in_the_masthead_goes_home(page):
    found = re.search(
        r'<div class="brand">\s*<a class="name" href="([^"]*)"', _text(page)
    )
    assert found, f"{page}: the masthead's name is not a link"
    assert found.group(1) in ROOTS, f"{page}: the name links to {found.group(1)!r}"


@pytest.mark.unit
@pytest.mark.parametrize(
    "page", ("index.html", "create.html", "editor.html", "404.html")
)
def test_the_title_follows_the_language(page):
    """A tab in English says English: the <title> is translated like the page."""
    assert re.search(r'<title data-i18n="\w+">', _text(page)), page


@pytest.mark.unit
def test_a_missing_address_gets_a_page_of_ours():
    """GitHub Pages serves 404.html for any address it lacks, at that address.

    So its paths cannot be relative to itself: it sets a <base> to the site's
    root before anything is loaded, and offers the way on.
    """
    text = _text("404.html")
    head = text.split("<title", 1)[0]
    assert "<base href=" in head, "404.html must set its base before its first link"
    assert 'name="robots" content="noindex"' in text
    for target in ('href="create.html"', 'href="./"', 'href="docs/"'):
        assert target in text, f"404.html offers no {target}"


@pytest.mark.unit
def test_create_deck_does_not_scroll_sideways():
    """The ruling behind step 1 reaches 50vw past its column; .cr clips it."""
    css = _text("create.css")
    assert "inset: 0 -50vw auto" not in css or re.search(
        r"\.cr \{[^}]*overflow-x: clip", css
    ), "the ruling behind step 1 widens the page again"


@pytest.mark.unit
def test_back_from_a_deck_returns_to_the_form():
    """A deck loaded from the form is a history entry of its own, and Back to the
    form (or Forward to the deck) is drawn rather than ignored."""
    app = _text("app.js")
    assert "history.pushState({ deck:" in app
    assert 'addEventListener("popstate"' in app
