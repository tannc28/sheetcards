"""The website builds, and nothing in it links to a page or a heading it lacks.

The documentation is Markdown under ``docs/site/`` (Vietnamese) and
``docs/site/en/`` (English), converted by
``scripts/build_site.py``; a renamed heading or page breaks a link silently, and a
reader finds out by landing at the top of the wrong page. This builds the whole
site into a temporary folder and follows every link that stays on it.
"""

import importlib.util
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote
from urllib.parse import urlsplit

import pytest

REPO = Path(__file__).resolve().parent.parent
pytest.importorskip("markdown", reason="the docs build needs the dev extra")


def _builder():
    spec = importlib.util.spec_from_file_location(
        "build_site", REPO / "scripts" / "build_site.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links = set(), []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        for name in ("href", "src"):
            if attrs.get(name):
                self.links.append(attrs[name])


def _parse(path):
    page = _Page()
    page.feed(path.read_text(encoding="utf-8"))
    return page


def _doc(out, folder, name):
    """Where a docs page is built: its own folder, the front page its language's."""
    base = out / "docs" / folder
    return base / "index.html" if name == "index" else base / name / "index.html"


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    build = _builder()
    out = tmp_path_factory.mktemp("site") / "site"
    build.build(out)
    return build, out


@pytest.mark.unit
def test_every_docs_page_is_built(site):
    build, out = site
    for folder in build.DOC_LANGS.values():
        for _, names in build.DOC_GROUPS:
            for name in names:
                page = "index.html" if name == "index" else f"{name}/index.html"
                assert (out / "docs" / folder / page).is_file(), name
        assert (out / "docs" / folder / "index.html").is_file()


@pytest.mark.unit
def test_every_docs_page_speaks_its_language_and_links_its_twin(site):
    """Vietnamese at /docs/, English at /docs/en/, and each page names the other."""
    build, out = site
    for lang, folder in build.DOC_LANGS.items():
        (other,) = set(build.DOC_LANGS) - {lang}
        for _, names in build.DOC_GROUPS:
            for name in names:
                path = _doc(out, folder, name)
                text = path.read_text(encoding="utf-8")
                assert f'<html lang="{lang}">' in text, path
                twin = re.search(
                    rf'<link rel="alternate" hreflang="{other}" href="([^"]+)">', text
                )
                assert twin, f"{path} names no {other} twin"
                target = (path.parent / twin.group(1)).resolve()
                if target.is_dir():
                    target = target / "index.html"
                expected = _doc(out, build.DOC_LANGS[other], name)
                assert target == expected.resolve(), (path, twin.group(1))


@pytest.mark.unit
def test_the_four_kinds_of_page_exist(site):
    _, out = site
    for page in (
        "index.html",
        "create/index.html",
        "sheet/index.html",
        "contact/index.html",
        "player.html",
        # The old addresses, forwarding (tests/test_site_redirects.py).
        "create.html",
        "preview.html",
        "sheet.html",
        "editor.html",
        "contact.html",
    ):
        assert (out / page).is_file(), page
    # Build inputs, not pages.
    assert not (out / "_docs.html").exists()
    assert not (out / "_redirect.html").exists()


@pytest.mark.unit
def test_no_page_links_an_address_ending_in_html(site):
    """Every page is a folder, and the site's own links say so. The old .html
    addresses are only there to forward; player.html is framed by cards, never
    linked to."""
    _, out = site
    found = []
    for path in out.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        if "location.replace" in text and 'name="robots" content="noindex"' in text:
            continue
        for link in _parse(path).links:
            parts = urlsplit(link)
            if parts.scheme or link.startswith("//"):
                continue
            if parts.path.endswith(".html"):
                found.append(f"{path.relative_to(out)}: {link}")
    assert not found, "links to .html addresses:\n  " + "\n  ".join(found)


@pytest.mark.unit
def test_no_internal_link_is_broken(site):
    """Every relative href/src resolves to a file, and every #fragment to an id."""
    _, out = site
    pages = {p: _parse(p) for p in out.rglob("*.html")}
    broken = []
    for path, page in pages.items():
        for link in page.links:
            parts = urlsplit(link)
            if parts.scheme or link.startswith("//"):
                continue
            target = path
            if parts.path:
                target = (path.parent / unquote(parts.path)).resolve()
                if link.endswith("/") or target.is_dir():
                    target = target / "index.html"
                if not target.is_file():
                    broken.append(f"{path.relative_to(out)}: {link}")
                    continue
            if parts.fragment and target.suffix == ".html":
                ids = pages.get(target, _parse(target)).ids
                if unquote(parts.fragment) not in ids:
                    broken.append(f"{path.relative_to(out)}: {link} (no such heading)")
    assert not broken, "broken links on the site:\n  " + "\n  ".join(broken)


@pytest.mark.unit
def test_the_docs_link_the_example_workbook(site):
    _, out = site
    url = "https://github.com/tannc28/sheetcards/blob/main/examples/sheetcards-examples.xlsx"
    for folder in ("", "en"):
        page = _doc(out, folder, "examples")
        assert url in page.read_text(encoding="utf-8"), page


@pytest.mark.unit
def test_the_landing_demo_is_rendered_from_the_workbook(site):
    build, out = site
    text = (out / "home-cards.js").read_text(encoding="utf-8")
    assert text.count('"qfmt"') == len(build.HOME_EXAMPLES)
    for sheet, row_id, _label, theme in build.HOME_EXAMPLES:
        assert sheet in text and f'"{row_id}"' in text
        assert f"theme={theme}" in text


@pytest.mark.unit
def test_old_preview_links_are_sent_to_create_deck(site):
    """/?url=… and /preview.html were Sheet to Anki's addresses; both forward it.

    What the forwarding scripts *do* is checked in tests/test_site_redirects.py;
    this only proves the built pages still carry them.
    """
    _, out = site
    for page in ("index.html", "preview.html", "create.html"):
        text = (out / page).read_text(encoding="utf-8")
        assert re.search(
            r'location\.replace\("\./create/" \+ location\.search', text
        ), page


@pytest.mark.unit
def test_an_unlisted_theme_is_never_published(site):
    """Hidden themes stay out of everything a reader can open."""
    _, out = site
    pages = list(out.rglob("*.html"))
    sources = list((REPO / "docs" / "site").rglob("*.md"))
    # Both languages of the docs, built and as written.
    assert any("/docs/en/" in p.as_posix() for p in pages)
    assert any(p.parent.name == "en" for p in sources)
    assert any(p.parent.name == "site" for p in sources)
    for path in pages + sources + [REPO / "README.md"]:
        assert "ptrang" not in path.read_text(encoding="utf-8"), path


@pytest.mark.unit
def test_the_landing_page_downloads_are_built_and_the_starter_is_a_good_sheet(site):
    """The two files the hero offers exist, and the starter makes a clean deck.

    The starter is the first sheet a new learner ever opens, so it must parse with
    no warnings and turn every row into a note — a template that warns teaches
    the wrong lesson on day one.
    """
    build, out = site
    starter = out / build.STARTER_NAME
    assert starter.is_file() and (out / build.EXAMPLES.name).is_file()

    tm, _card_layout, workbook = build._pure_package(out)
    (sheet,) = build.STARTER
    parsed = tm.parse_tsv_data(workbook.sheet_tsv(starter.read_bytes(), sheet), [])
    deck = tm.build_remote_deck_from_tsv(parsed, "", [])
    assert deck.sheet_config.present and not deck.sheet_config.warnings
    assert len(build.STARTER[sheet]) - 2 == 3  # header + settings row + 3 words
    rows = [r for r in parsed["rows"][1:] if r and r[0]]
    assert len(rows) == 3

    landing = (out / "index.html").read_text(encoding="utf-8")
    assert f'href="./{build.STARTER_NAME}" download' in landing
    assert f'href="./{build.EXAMPLES.name}" download' in landing
