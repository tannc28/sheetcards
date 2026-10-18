"""The things every website does that nobody notices until one is missing.

Each of these shipped missing once and was found by a reader, not by a test: the
name in the masthead that did not go home, a sideways scroll on Sheet to Anki, a
Back button that left the site with the sheet, a missing address answered by
GitHub's own 404 page. They are cheap to check and silent when they break, so
they are checked here.
"""

import re
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parent.parent / "site"

# Every page with the shared masthead. player.html is a frame inside a card,
# and the old addresses (preview.html, docs/faq.html, …) are redirects the build
# writes from _redirect.html; none of them has chrome.
PAGES = (
    "index.html",
    "sheet.html",
    "create.html",
    "contact.html",
    "_docs.html",
    "404.html",
)

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
    "page", ("index.html", "sheet.html", "create.html", "contact.html", "404.html")
)
def test_the_title_follows_the_language(page):
    """A tab in English says English: the <title> is translated like the page."""
    assert re.search(r'<title data-i18n="\w+">', _text(page)), page


# The site's pages, most used first: Tạo flashcard / Make flashcards is the
# product (Sheet to Anki until 2026-10-18), Create sheet the step some people
# need before it, then the docs. Every masthead says it the same way, in the
# reader's language: our own page names are translated, Docs is not. The
# static text is the Vietnamese (the default); i18n.js carries both.
NAV_KEYS = ["navHome", "navPreview", "navSheet", "navDocs"]
NAV = {
    "vi": ["Trang chủ", "Tạo flashcard", "Tạo Sheet", "Docs"],
    "en": ["Home", "Make flashcards", "Create sheet", "Docs"],
}


@pytest.mark.unit
@pytest.mark.parametrize("page", PAGES)
def test_every_masthead_lists_the_pages_in_order(page):
    nav = re.search(r'<nav class="sitenav"[^>]*>(.*?)</nav>', _text(page), re.S)
    assert nav, f"{page} has no site navigation"
    links = re.findall(r'<a href="([^"]*)"[^>]*>(.*?)</a>', nav.group(1), re.S)
    assert [name.strip() for _, name in links] == NAV["vi"], f"{page}: {links}"
    # Clean paths, each page a folder: no address on the site ends in .html.
    pages = [href.replace("%%ROOT%%", "").removeprefix("./") for href, _ in links[1:3]]
    assert pages == ["create/", "sheet/"], f"{page}: {pages}"


@pytest.mark.unit
@pytest.mark.parametrize("page", PAGES)
def test_github_is_an_icon_beside_the_switches(page):
    """Outside the page list, since it leaves the site, and named for a reader
    who cannot see the mark."""
    head = re.search(r'<header class="masthead">(.*?)</header>', _text(page), re.S)
    found = re.search(r'</nav>\s*<a class="ghlink"([^>]*)>', head.group(1))
    assert found, f"{page}: no GitHub icon after the site navigation"
    attrs = found.group(1)
    for want in ('aria-label="GitHub"', 'title="GitHub"', 'data-icon="github"'):
        assert want in attrs, f"{page}: GitHub link lacks {want}"


# The pages that link to the contact page, and how each says where it is. The
# "by ctan" byline that stood in this spot was replaced by the link.
CONTACT_FROM = {
    "index.html": "./contact/?from=home",
    "sheet.html": "./contact/?from=sheet",
    "create.html": "./contact/?from=create",
    "404.html": "contact/?from=404",
    "_docs.html": "%%ROOT%%contact/?from=%%FROM%%",
}


@pytest.mark.unit
@pytest.mark.parametrize("page", sorted(CONTACT_FROM))
def test_every_page_links_contact_and_feedback(page):
    """One quiet line on every page, saying which page it was followed from."""
    text = _text(page)
    href = CONTACT_FROM[page]
    assert f'<p class="contactlink"><a href="{href}">' in text, page
    assert "by ctan" not in text and 'class="byline"' not in text, page


@pytest.mark.unit
def test_the_byline_is_gone_everywhere():
    for path in SITE.iterdir():
        if path.suffix in (".html", ".js", ".css"):
            assert "byline" not in path.read_text(encoding="utf-8"), path.name


@pytest.mark.unit
def test_the_nav_names_follow_the_language():
    import json
    import shutil
    import subprocess

    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    script = (
        f"import({json.dumps((SITE / 'i18n.js').as_uri())}).then((m) => "
        f"process.stdout.write(JSON.stringify({json.dumps(NAV_KEYS)}"
        ".map((k) => [m.STRINGS[k].en, m.STRINGS[k].vi]))))"
    )
    out = subprocess.run(
        [node, "--no-warnings", "-e", script],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(out.stdout) == [
        list(p) for p in zip(NAV["en"], NAV["vi"], strict=True)
    ]


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
        'href="sheet/"',
        'href="create/"',
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
