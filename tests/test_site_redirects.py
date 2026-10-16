"""Create deck's old addresses still reach it, query and fragment intact.

Create deck was the site's front page (``/?url=…``), then ``/preview.html``, and
is now ``/create.html``. Links to both old addresses are out there — in older
copies of the add-on, in posts, in bookmarks — and they carry the sheet's link in
``?url=`` or ask for the example with ``#example``. Each old page forwards with
a few lines of inline script, so those lines are run here, in node, against a
fake ``location``: a forward that dropped the query would still land on the page,
just on an empty form, and nothing else would notice.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parent.parent / "site"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")


def _forwarding_script(page):
    """The first inline script on ``page`` that calls location.replace."""
    text = (SITE / page).read_text(encoding="utf-8")
    for body in re.findall(r"<script>(.*?)</script>", text, re.S):
        if "location.replace" in body:
            return body
    raise AssertionError(f"{page} has no forwarding script")


def _run(page, search="", hash_=""):
    """Where ``page`` sends a visitor arriving with ``search`` and ``hash_``."""
    script = (
        "const vm = require('vm');"
        f"const ctx = {{ location: {{ search: {json.dumps(search)},"
        f" hash: {json.dumps(hash_)}, replace(u) {{ ctx.went = u; }} }}, went: null }};"
        f"vm.runInNewContext({json.dumps(_forwarding_script(page))}, ctx);"
        "process.stdout.write(JSON.stringify(ctx.went));"
    )
    out = subprocess.run(
        [NODE, "-e", script], capture_output=True, text=True, check=True, timeout=30
    )
    return json.loads(out.stdout)


@pytest.mark.unit
class TestPreviewHtml:
    def test_a_link_is_carried_over(self):
        url = "?url=https%3A%2F%2Fdocs.google.com%2Fspreadsheets%2Fd%2Fabc"
        assert _run("preview.html", url) == f"./create.html{url}"

    def test_the_fragment_is_carried_over(self):
        assert _run("preview.html", "", "#example") == "./create.html#example"

    def test_a_bare_visit_still_arrives(self):
        assert _run("preview.html") == "./create.html"

    def test_it_works_without_script_too(self):
        text = (SITE / "preview.html").read_text(encoding="utf-8")
        assert 'http-equiv="refresh" content="0; url=./create.html"' in text


@pytest.mark.unit
class TestTheLandingPage:
    def test_a_link_goes_to_create_deck(self):
        assert _run("index.html", "?url=x") == "./create.html?url=x"

    def test_a_foreign_fragment_goes_to_create_deck(self):
        assert _run("index.html", "", "#example") == "./create.html#example"

    @pytest.mark.parametrize("own", ["#main", "#why", "#how", "#features", "#addon"])
    def test_its_own_sections_stay(self, own):
        assert _run("index.html", "", own) is None

    def test_every_own_fragment_is_a_real_section(self):
        """A section renamed without the list would forward its own anchor away."""
        text = (SITE / "index.html").read_text(encoding="utf-8")
        listed = re.search(r"var own = \[(.*?)\]", text).group(1)
        for name in re.findall(r'"#([\w-]+)"', listed):
            assert f'id="{name}"' in text, name


@pytest.mark.unit
class TestEditorHtml:
    """The settings-row editor grew into Create sheet; its address forwards."""

    def test_the_query_and_fragment_are_carried_over(self):
        assert _run("editor.html", "?x", "#y") == "./sheet.html?x#y"

    def test_a_shared_sheet_survives_the_forward(self):
        assert _run("editor.html", "", "#s=1.abc") == "./sheet.html#s=1.abc"

    def test_a_bare_visit_still_arrives(self):
        assert _run("editor.html") == "./sheet.html"

    def test_it_works_without_script_too(self):
        text = (SITE / "editor.html").read_text(encoding="utf-8")
        assert 'http-equiv="refresh" content="0; url=./sheet.html"' in text
