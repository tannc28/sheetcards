"""The website builds, and nothing in it links to a page or a heading it lacks.

The documentation is Markdown under ``docs/site/``, converted by
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


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    build = _builder()
    out = tmp_path_factory.mktemp("site") / "site"
    build.build(out)
    return build, out


@pytest.mark.unit
def test_every_docs_page_is_built(site):
    build, out = site
    for _, names in build.DOC_GROUPS:
        for name in names:
            assert (out / "docs" / f"{name}.html").is_file(), name
    assert (out / "docs" / "index.html").is_file()


@pytest.mark.unit
def test_the_four_kinds_of_page_exist(site):
    _, out = site
    for page in ("index.html", "preview.html", "editor.html", "player.html"):
        assert (out / page).is_file(), page
    # A build input, not a page.
    assert not (out / "_docs.html").exists()


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
    assert url in (out / "docs" / "examples.html").read_text(encoding="utf-8")


@pytest.mark.unit
def test_the_landing_demo_is_rendered_from_the_workbook(site):
    build, out = site
    text = (out / "home-cards.js").read_text(encoding="utf-8")
    assert text.count('"qfmt"') == len(build.HOME_EXAMPLES)
    for sheet, row_id, _ in build.HOME_EXAMPLES:
        assert sheet in text and f'"{row_id}"' in text


@pytest.mark.unit
def test_old_preview_links_are_sent_to_the_preview(site):
    """/?url=… was the preview's address; the landing page forwards it."""
    _, out = site
    landing = (out / "index.html").read_text(encoding="utf-8")
    assert re.search(
        r'location\.replace\("\./preview\.html" \+ location\.search', landing
    )


@pytest.mark.unit
def test_an_unlisted_theme_is_never_published(site):
    """Hidden themes stay out of everything a reader can open."""
    _, out = site
    for path in list(out.rglob("*.html")) + [REPO / "README.md"]:
        assert "ptrang" not in path.read_text(encoding="utf-8"), path
