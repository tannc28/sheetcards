"""Every address the site has ever had still reaches its page, query and fragment intact.

The pages are folders now (``/create/``, ``/sheet/``, ``/contact/``,
``/docs/faq/``), and before that they were files (``create.html``,
``docs/faq.html``); Sheet to Anki was also ``/?url=…`` and ``/preview.html``, and
Create sheet ``/editor.html``. Links to all of them are out there — in older
copies of the add-on, in posts, in bookmarks, in shared sheets (``#s=…``) — so
each old address is a small page the build writes, forwarding with a line of
inline script. Those lines are run here, in node, against a fake ``location``
at the old address, and the result resolved the way a browser would: a forward
that dropped the query would still land on the page, just on an empty form,
and nothing else would notice.
"""

import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SITE = REPO / "site"
NODE = shutil.which("node")
ORIGIN = "https://tannc28.github.io"
ROOT = "/sheetcards/"

pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")


def _builder():
    spec = importlib.util.spec_from_file_location(
        "build_site", REPO / "scripts" / "build_site.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILD = _builder()


def _forwarding_script(text):
    """The first inline script in ``text`` that calls location.replace."""
    for body in re.findall(r"<script>(.*?)</script>", text, re.S):
        if "location.replace" in body:
            return body
    raise AssertionError("no forwarding script")


def _run(text, path, search="", hash_=""):
    """Where the page ``text``, served at ``path`` under the site's root, sends a
    visitor arriving with ``search`` and ``hash_`` — as a path under the root
    plus query and fragment, or None if it stays."""
    href = f"{ORIGIN}{ROOT}{path}{search}{hash_}"
    script = (
        "const vm = require('vm');"
        f"const href = {json.dumps(href)};"
        f"const ctx = {{ location: {{ href, search: {json.dumps(search)},"
        f" hash: {json.dumps(hash_)}, replace(u) {{ ctx.went = u; }} }}, went: null }};"
        f"vm.runInNewContext({json.dumps(_forwarding_script(text))}, ctx);"
        "const out = ctx.went === null ? null : new URL(ctx.went, href);"
        "process.stdout.write(JSON.stringify(out &&"
        f" out.href.slice({json.dumps(ORIGIN + ROOT)}.length)));"
    )
    out = subprocess.run(
        [NODE, "-e", script], capture_output=True, text=True, check=True, timeout=30
    )
    return json.loads(out.stdout)


def _old_addresses():
    """{old address: the page it must reach}, every one the site keeps."""
    found = dict(BUILD.REDIRECTS)
    found.update({old: f"{new}/" for old, new in BUILD.PAGES.items()})
    for folder in BUILD.DOC_LANGS.values():
        base = f"docs/{folder}/" if folder else "docs/"
        for _, names in BUILD.DOC_GROUPS:
            for name in names:
                if name != "index":
                    found[f"{base}{name}.html"] = f"{base}{name}/"
    return found


OLD = _old_addresses()


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("site") / "site"
    BUILD.build(out)
    return out


@pytest.mark.unit
class TestEveryOldAddress:
    def test_the_known_old_addresses_are_all_kept(self):
        for old, new in {
            "create.html": "create/",
            "sheet.html": "sheet/",
            "contact.html": "contact/",
            "preview.html": "create/",
            "editor.html": "sheet/",
            "docs/settings-row.html": "docs/settings-row/",
            "docs/en/faq.html": "docs/en/faq/",
        }.items():
            assert OLD.get(old) == new, old

    @pytest.mark.parametrize("old", sorted(OLD))
    def test_query_and_fragment_are_carried_over(self, site, old):
        text = (site / old).read_text(encoding="utf-8")
        new = OLD[old]
        assert _run(text, old) == new
        assert _run(text, old, "?url=https%3A%2F%2Fx%2Fy&tab=A") == (
            f"{new}?url=https%3A%2F%2Fx%2Fy&tab=A"
        )
        assert _run(text, old, "", "#s=1.abc_-") == f"{new}#s=1.abc_-"
        assert _run(text, old, "?row=w03", "#example") == f"{new}?row=w03#example"

    @pytest.mark.parametrize("old", sorted(OLD))
    def test_it_works_without_script_too(self, site, old):
        text = (site / old).read_text(encoding="utf-8")
        refresh = re.search(r'http-equiv="refresh" content="0; url=([^"]+)"', text)
        assert refresh, old
        script = re.search(r'location\.replace\("([^"]+)"', text).group(1)
        assert refresh.group(1) == script, old
        assert 'name="robots" content="noindex"' in text

    @pytest.mark.parametrize("old", sorted(OLD))
    def test_the_new_address_is_a_page(self, site, old):
        assert (site / OLD[old] / "index.html").is_file(), OLD[old]

    def test_old_shared_sheets_still_open(self, site):
        """A sheet shared before the move: sheet.html#s=… and create.html#s=…."""
        for old, new in (("sheet.html", "sheet/"), ("create.html", "create/")):
            text = (site / old).read_text(encoding="utf-8")
            assert _run(text, old, "", "#s=1.q1w2e3") == f"{new}#s=1.q1w2e3"


@pytest.mark.unit
class TestThePlayerNeverMoves:
    """Its address is in card templates already imported into Anki."""

    def test_it_is_still_a_page_at_the_root(self, site):
        text = (site / "player.html").read_text(encoding="utf-8")
        assert "location.replace" not in text and "ALLOWED" in text
        assert not (site / "player").exists()

    def test_the_cards_still_point_at_it(self):
        source = (REPO / "src" / "card_layout.py").read_text(encoding="utf-8")
        assert (
            'EMBED_PROXY = "https://tannc28.github.io/sheetcards/player.html?src="'
            in (source)
        )


@pytest.mark.unit
class TestTheLandingPage:
    def _text(self):
        return (SITE / "index.html").read_text(encoding="utf-8")

    def test_a_link_goes_to_sheet_to_anki(self):
        assert _run(self._text(), "", "?url=x") == "create/?url=x"

    def test_a_foreign_fragment_goes_to_sheet_to_anki(self):
        assert _run(self._text(), "", "", "#example") == "create/#example"

    @pytest.mark.parametrize(
        "own", ["#main", "#ai", "#how", "#features", "#soon", "#addon"]
    )
    def test_its_own_sections_stay(self, own):
        assert _run(self._text(), "", "", own) is None

    def test_every_own_fragment_is_a_real_section(self):
        """A section renamed without the list would forward its own anchor away."""
        text = self._text()
        listed = re.search(r"var own = \[(.*?)\]", text).group(1)
        for name in re.findall(r'"#([\w-]+)"', listed):
            assert f'id="{name}"' in text, name


@pytest.mark.unit
class TestRetiredDocsPages:
    """A docs page that is gone forwards to what took its job: the AI guide's
    page (*Tạo bộ từ bằng AI*) is now the landing page's small #ai block."""

    RETIRED = BUILD.retired_doc_addresses()

    def test_every_address_of_the_ai_page_is_kept(self):
        for old in (
            "docs/ai/index.html",
            "docs/ai.html",
            "docs/en/ai/index.html",
            "docs/en/ai.html",
        ):
            assert self.RETIRED.get(old) == "#ai", old

    @pytest.mark.parametrize("old", sorted(RETIRED))
    def test_it_lands_on_the_landing_block(self, site, old):
        text = (site / old).read_text(encoding="utf-8")
        # Landing exactly there: a query would send the reader on to /create/,
        # and the old page's own fragments mean nothing on the landing page.
        assert _run(text, old) == "#ai"
        assert _run(text, old, "?x=1", "#cac-buoc") == "#ai"
        refresh = re.search(r'http-equiv="refresh" content="0; url=([^"]+)"', text)
        assert refresh and refresh.group(1).endswith("#ai"), old

    def test_the_landing_keeps_the_block(self):
        text = (SITE / "index.html").read_text(encoding="utf-8")
        assert 'id="ai"' in text
        assert _run(text, "", "", "#ai") is None

    def test_no_page_links_the_old_docs_page(self):
        for page in SITE.glob("*.html"):
            text = page.read_text(encoding="utf-8")
            assert 'data-doc="ai/"' not in text, page.name
            assert "docs/ai/" not in text, page.name
