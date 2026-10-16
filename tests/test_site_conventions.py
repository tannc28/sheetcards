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

# Every page with the shared masthead. player.html is a frame inside a card,
# and preview.html and editor.html are redirects; none of them has chrome.
PAGES = ("index.html", "sheet.html", "create.html", "_docs.html", "404.html")

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
    "page", ("index.html", "sheet.html", "create.html", "404.html")
)
def test_the_title_follows_the_language(page):
    """A tab in English says English: the <title> is translated like the page."""
    assert re.search(r'<title data-i18n="\w+">', _text(page)), page


# The site's flow, in the order a learner walks it: write a sheet, make the deck,
# read about it. Every page's masthead says it the same way, in both languages
# (the names are product names and stay English).
NAV = ["Home", "Create sheet", "Create deck", "Docs", "GitHub"]


@pytest.mark.unit
@pytest.mark.parametrize("page", PAGES)
def test_every_masthead_lists_the_pages_in_the_flows_order(page):
    nav = re.search(r'<nav class="sitenav"[^>]*>(.*?)</nav>', _text(page), re.S)
    assert nav, f"{page} has no site navigation"
    links = re.findall(r'<a href="([^"]*)"[^>]*>(.*?)</a>', nav.group(1), re.S)
    assert [name.strip() for _, name in links] == NAV, f"{page}: {links}"
    pages = [href.rsplit("/", 1)[-1].replace("%%ROOT%%", "") for href, _ in links[1:3]]
    assert pages == ["sheet.html", "create.html"], f"{page}: {pages}"


@pytest.mark.unit
def test_the_nav_names_are_the_same_in_both_languages():
    import json
    import shutil
    import subprocess

    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    keys = ["navHome", "navSheet", "navPreview", "navDocs"]
    script = (
        f"import({json.dumps((SITE / 'i18n.js').as_uri())}).then((m) => "
        f"process.stdout.write(JSON.stringify({json.dumps(keys)}"
        ".map((k) => [m.STRINGS[k].en, m.STRINGS[k].vi]))))"
    )
    out = subprocess.run(
        [node, "--no-warnings", "-e", script],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(out.stdout) == [[name, name] for name in NAV[:4]]


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
    for target in (
        'href="sheet.html"',
        'href="create.html"',
        'href="./"',
        'href="docs/"',
    ):
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
