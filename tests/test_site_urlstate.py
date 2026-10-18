"""What a page shows, kept in its address: ``site/urlstate.js``, run in node.

Sheet to Anki writes the card on screen into its query (``?tab=…&row=w03&side=back``),
Create sheet the template step it has open (``?tpl=vocab&lang=en_US&theme=sakura``)
and the contact page the kind of message (``?kind=bug``), so that an address
copied out of the bar opens the same place for whoever it is sent to. Those
pages cannot be driven without a browser and Pyodide; the rules they share can:
what is written comes back as it went in, defaults and unknown values are left
out, and nothing else in the address is touched.

Also here: the share builder emits the clean ``sheet/#s=`` and ``create/#s=``
addresses, and ``paths.js`` resolves pages from the site's root whatever page
loaded it.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parent.parent / "site"
NODE = shutil.which("node")

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(NODE is None, reason="node is not installed"),
]

BASE = "https://tannc28.github.io/sheetcards/create/"


def _run(body, module="urlstate.js"):
    """Runs ``body`` (an async function body with ``m`` the module) in node."""
    script = (
        f"import({json.dumps((SITE / module).as_uri())}).then(async (m) => {{"
        f"const out = await (async () => {{ {body} }})();"
        "process.stdout.write(JSON.stringify(out)); })"
        ".catch((e) => { process.stdout.write(JSON.stringify({ error: e.message })); })"
    )
    out = subprocess.run(
        [NODE, "--no-warnings", "-e", script],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return json.loads(out.stdout)


def _write(url, values, schema="CREATE_STATE"):
    return _run(
        f"return m.writeState({json.dumps(url)}, {json.dumps(values)}, m.{schema}).href;"
    )


def _read(url, schema="CREATE_STATE"):
    return _run(f"return m.readState(new URL({json.dumps(url)}), m.{schema});")


class TestSheetToAnki:
    def test_a_card_round_trips(self):
        want = {
            "tab": "15 Theme + subdeck (màu, tầng)",
            "deck": "Geography::Rivers",
            "row": "w03",
            "side": "back",
            "card": 2,
            "cloze": 3,
            "view": "template",
        }
        url = _write(BASE + "?url=https%3A%2F%2Fx%2Fy#example", want)
        assert _read(url) == want
        # The source and the fragment are not the page's to rewrite.
        assert "url=https%3A%2F%2Fx%2Fy" in url and url.endswith("#example")

    def test_defaults_are_left_out(self):
        url = _write(BASE, {"side": "front", "card": 1, "row": None, "deck": ""})
        assert url == BASE

    def test_unknown_and_bad_values_are_ignored(self):
        got = _read(BASE + "?side=sideways&card=0&cloze=x&view=chart&row=w01&foo=1")
        assert got == {"row": "w01"}

    def test_unknown_parameters_are_kept(self):
        url = _write(BASE + "?foo=1&row=w01", {"row": "w02"})
        assert url == BASE + "?foo=1&row=w02"

    def test_clearing_keeps_the_source(self):
        url = _run(
            f"return m.clearState({json.dumps(BASE + '?url=u&row=w1&side=back#s=1.x')},"
            " m.CREATE_STATE).href;"
        )
        assert url == BASE + "?url=u#s=1.x"

    def test_a_row_id_with_odd_characters_survives(self):
        want = {"row": "a&b=c #1 ạ"}
        assert _read(_write(BASE, want)) == want


class TestCreateSheet:
    URL = "https://tannc28.github.io/sheetcards/sheet/"

    def test_a_template_step_round_trips(self):
        want = {"tpl": "vocab", "lang": "en_US", "word": "0", "theme": "sakura"}
        url = _write(self.URL, want, "SHEET_STATE")
        assert url == self.URL + "?tpl=vocab&lang=en_US&word=0&theme=sakura"
        assert _read(url, "SHEET_STATE") == want

    def test_the_default_toggles_are_not_written(self):
        url = _write(
            self.URL, {"tpl": "vocab", "word": "1", "example": "1"}, "SHEET_STATE"
        )
        assert url == self.URL + "?tpl=vocab"

    def test_the_view(self):
        assert _read(self.URL + "?view=look", "SHEET_STATE") == {"view": "look"}
        assert _read(self.URL + "?view=grid", "SHEET_STATE") == {}

    def test_a_shared_sheet_is_left_alone(self):
        url = _write(self.URL + "#s=1.abc", {"view": "look"}, "SHEET_STATE")
        assert url == self.URL + "?view=look#s=1.abc"


class TestContact:
    URL = "https://tannc28.github.io/sheetcards/contact/"

    def test_kind_preselects(self):
        assert _read(self.URL + "?kind=feature&from=create", "CONTACT_STATE") == {
            "kind": "feature",
            "from": "create",
        }
        assert _read(self.URL + "?kind=spam", "CONTACT_STATE") == {}

    def test_the_default_kind_is_not_written(self):
        url = _write(
            self.URL + "?from=home", {"from": "home", "kind": "bug"}, "CONTACT_STATE"
        )
        assert url == self.URL + "?from=home"


class TestAddresses:
    def test_pages_resolve_from_the_root(self):
        got = _run(
            "return { root: m.ROOT, create: m.site(m.PAGE.create),"
            " doc: m.site('docs/en/faq/'), addon: m.site('./#addon') };",
            "paths.js",
        )
        root = SITE.as_uri() + "/"
        assert got == {
            "root": root,
            "create": root + "create/",
            "doc": root + "docs/en/faq/",
            "addon": root + "#addon",
        }

    def test_share_links_use_the_clean_addresses(self):
        got = _run(
            "return [m.shareAddress('#s=1.abc'), m.shareAddress('#s=1.abc', { deck: true })];",
            "sharelink.js",
        )
        root = SITE.as_uri() + "/"
        assert got == [root + "sheet/#s=1.abc", root + "create/#s=1.abc"]
