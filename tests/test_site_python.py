#!/usr/bin/env python3
"""The Python the preview site runs in the browser, run here instead.

`site/app.js` and `site/editor.js` each carry a block of Python in a `String.raw`
template literal, loaded into Pyodide against copies of the add-on's pure modules.
Nothing else in the suite executes it, so until this file existed a rename in the
pure layer — a function gone, an argument added — reached the deployed page as a
blank panel and an error in a console nobody has open on a phone.

The modules are the real ones, imported under the `s2a` name the site uses, which
is also what `scripts/build_site.py` copies them into.
"""

import json
import re
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

# Everything the block does is `import s2a.…`, so mapping that name at the package
# level is the whole of the emulation: the modules themselves are untouched.
_PACKAGE = types.ModuleType("s2a")
_PACKAGE.__path__ = [str(ROOT / "src")]
sys.modules.setdefault("s2a", _PACKAGE)

_BLOCK = re.compile(r"String\.raw`(.*?)`;", re.S)


def _python_of(module):
    """The Python out of one site module, or None when it carries none."""
    found = _BLOCK.search((SITE / module).read_text(encoding="utf-8"))
    return found.group(1) if found else None


def _loaded(module):
    """The block's namespace, after running it exactly as Pyodide would."""
    source = _python_of(module)
    assert source, f"{module} carries no Python block"
    namespace = {}
    exec(compile(source, f"{module} (embedded Python)", "exec"), namespace)
    return namespace


@pytest.mark.unit
class TestItLoadsAtAll:
    """An import or a syntax error here is a page that renders and does nothing."""

    @pytest.mark.parametrize("module", ["app.js", "editor.js"])
    def test_the_block_runs(self, module):
        assert _loaded(module)


@pytest.mark.unit
class TestTheEditor:
    """`editor.js` — the settings row, the card it makes and where it files a note."""

    PAYLOAD = {
        "marker": "#config",
        "columns": [
            {"name": "Level", "cell": "subdeck=1", "value": ""},
            {"name": "Word", "cell": "size=44; bold", "value": "hello"},
            {"name": "Meaning", "cell": "size=20; color=muted", "value": "xin chào"},
        ],
    }

    def _preview(self, payload=None):
        namespace = _loaded("editor.js")
        return json.loads(namespace["preview"](json.dumps(payload or self.PAYLOAD)))

    def test_the_directive_names_come_from_sheet_config(self):
        from src.sheet_config import _DECK_KEYS
        from src.sheet_config import _FIELD_KEYS

        keys = json.loads(_loaded("editor.js")["keys"]())
        assert keys["field"] == list(_FIELD_KEYS)
        assert keys["deck"] == list(_DECK_KEYS)

    def test_it_returns_a_card_and_no_complaints(self):
        out = self._preview()
        assert out["isConfig"] is True
        assert out["warnings"] == []
        assert out["front"] and out["back"]
        assert out["templates"][0]["qfmt"]

    def test_it_says_where_the_row_is_filed(self):
        # The card is only half of what a settings row decides: a deck level never
        # touches the card, so the page has to show where the row went.
        out = self._preview()
        assert out["deck"] == ["Unsorted"]
        assert "sheets2anki::unsorted" in out["tags"]

    def test_a_filled_level_is_not_the_unsorted_pile(self):
        payload = json.loads(json.dumps(self.PAYLOAD))
        payload["columns"][0]["value"] = "HSK 1"
        assert self._preview(payload)["deck"] == ["HSK 1"]

    def test_a_marker_typed_over_stops_being_a_settings_row(self):
        payload = json.loads(json.dumps(self.PAYLOAD))
        payload["marker"] = "hello"
        out = self._preview(payload)
        assert out["isConfig"] is False


@pytest.mark.unit
class TestTheAnalyzer:
    """`app.js` — a whole sheet, read the way a sync reads it."""

    TSV = "\n".join(
        [
            "ID\tSYNC\tSUBDECK 1\tWord\tMeaning",
            "#config\t\t\tsize=44\tcolor=muted",
            "r1\tyes\tGreetings\thello\txin chào",
            "r2\tyes\t\tthanks\tcảm ơn",
        ]
    )

    def _analysis(self, tsv=None):
        return json.loads(_loaded("app.js")["analyze"](tsv or self.TSV, "Demo"))

    def test_it_analyses_a_sheet(self):
        out = self._analysis()
        decks = {row["deck"] for row in out["rows"] if row["kind"] == "synced"}
        # The root is the add-on's own (`s2a_{name}`), because the page shows the
        # tree Anki would show rather than a tidied version of it.
        assert decks == {"s2a_Demo::Greetings", "s2a_Demo::Unsorted"}

    def test_the_grid_is_the_sheet_and_not_a_tidied_one(self):
        """Panel 1 draws a grid, and a grid that edits its sheet is a lie.

        The settings row and the rows no note comes from are exactly what people
        scroll a sheet to check, so the grid carries every row the file has —
        unlike ``rows``, which is what the sync would make of them.
        """
        grid = self._analysis()["grid"]
        assert grid["cells"][0] == ["ID", "SYNC", "SUBDECK 1", "Word", "Meaning"]
        assert grid["cells"][1][0] == "#config"
        # Header row plus every data row, and the sheet's own numbering: the
        # settings row is row 2 there, so it is row 2 here.
        assert len(grid["cells"]) == 4
        assert grid["config"] == 2
        assert grid["total"] == 3

    def test_a_grid_column_opens_the_column_the_list_opens(self):
        """The two indexes are not the same one, and a blank header proves it."""
        tsv = "\n".join(["ID\t\tWord", "r1\tignored\thello"])
        out = self._analysis(tsv)
        # Position 1 has no header, so it is a column of the sheet and not of the
        # plan; position 2 is the plan's second column.
        assert out["grid"]["cols"] == [0, None, 1]
        assert out["plan"]["headers"] == ["ID", "Word"]

    def test_a_ragged_row_is_squared_off(self):
        """A row longer than the header row still has to be a row of the table."""
        tsv = "\n".join(["ID\tWord", "r1\thello\tstray"])
        grid = self._analysis(tsv)["grid"]
        assert [len(row) for row in grid["cells"]] == [3, 3]
