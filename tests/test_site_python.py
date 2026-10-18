#!/usr/bin/env python3
"""The Python the preview site runs in the browser, run here instead.

`site/app.js` and `site/sheet.js` each carry a block of Python in a `String.raw`
template literal, loaded into Pyodide against copies of the add-on's pure modules.
Nothing else in the suite executes it, so until this file existed a rename in the
pure layer — a function gone, an argument added — reached the deployed page as a
blank panel and an error in a console nobody has open on a phone.

The modules are the real ones, imported under the `sc` name the site uses, which
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

# Everything the block does is `import sc.…`, so mapping that name at the package
# level is the whole of the emulation: the modules themselves are untouched.
_PACKAGE = types.ModuleType("sc")
_PACKAGE.__path__ = [str(ROOT / "src")]
sys.modules.setdefault("sc", _PACKAGE)

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

    @pytest.mark.parametrize("module", ["app.js", "sheet.js"])
    def test_the_block_runs(self, module):
        assert _loaded(module)


@pytest.mark.unit
class TestCreateSheet:
    """`sheet.js` — the settings row, the card a word makes, and the files."""

    PAYLOAD = {
        "marker": "#config",
        "columns": [
            {"name": "Level", "cell": "subdeck=1"},
            {"name": "Word", "cell": "size=44; bold"},
            {"name": "Meaning", "cell": "size=20; color=muted"},
        ],
        "values": ["", "hello", "xin chào"],
        "rows": [["", "hello", "xin chào"], ["A1", "goodbye", "tạm biệt"]],
    }

    def _preview(self, payload=None):
        namespace = _loaded("sheet.js")
        return json.loads(namespace["preview"](json.dumps(payload or self.PAYLOAD)))

    def _copy(self):
        return json.loads(json.dumps(self.PAYLOAD))

    def test_the_directive_names_come_from_sheet_config(self):
        from src.sheet_config import _DECK_KEYS
        from src.sheet_config import _FIELD_KEYS

        keys = json.loads(_loaded("sheet.js")["keys"]())
        assert keys["field"] == list(_FIELD_KEYS)
        assert keys["deck"] == list(_DECK_KEYS)

    def test_it_returns_a_card_and_no_complaints(self):
        out = self._preview()
        assert out["isConfig"] is True
        assert out["warnings"] == []
        assert out["front"] and out["back"]
        assert out["templates"][0]["qfmt"]

    def test_it_says_where_the_word_is_filed(self):
        out = self._preview()
        assert out["deck"] == ["Unsorted"]
        assert "sheetcards::unsorted" in out["tags"]

    def test_it_files_every_word_for_the_deck_tree(self):
        assert self._preview()["decks"] == ["Unsorted", "A1"]

    def test_a_marker_typed_over_stops_being_a_settings_row(self):
        payload = self._copy()
        payload["marker"] = "hello"
        assert self._preview(payload)["isConfig"] is False

    def test_a_repeated_column_name_keeps_both_columns(self):
        payload = self._copy()
        payload["columns"][2]["name"] = "Word"
        assert len(self._preview(payload)["names"]) == 3

    def test_the_xlsx_reads_back_through_the_add_ons_reader(self):
        import csv
        import io

        from src import workbook

        rows = [
            ["ID", "Word", "Meaning"],
            ["#config", "tts=en_US", ""],
            ["w01", "hello", "xin chào"],
        ]
        data = _loaded("sheet.js")["xlsx"](
            json.dumps({"name": "Từ vựng: bài 1", "rows": rows})
        )
        assert workbook.sheet_names(data) == ["Từ vựng bài 1"]
        tsv = workbook.sheet_tsv(data, "Từ vựng bài 1")
        assert list(csv.reader(io.StringIO(tsv), delimiter="\t")) == rows

    def test_an_opened_csv_comes_back_as_rows(self):
        text = b'ID,Word\n#config,size=40\nw01,"a, b"\n'
        out = json.loads(_loaded("sheet.js")["open_file"](text, "words.csv", 0))
        assert out["rows"] == [["ID", "Word"], ["#config", "size=40"], ["w01", "a, b"]]
        assert out["tabs"] == []


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
        # The root is the add-on's own (`sc_{name}`), because the page shows the
        # tree Anki would show rather than a tidied version of it.
        assert decks == {"sc_Demo::Greetings", "sc_Demo::Unsorted"}

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

    def test_a_name_is_the_deck_and_the_identity(self):
        tsv = self.TSV.replace("#config\t", "#config name=Từ vựng  HSK\t")
        out = self._analysis(tsv)
        assert out["identity"] == {
            "id": "name:từ vựng hsk",
            "deck": "Từ vựng HSK",
            "named": True,
            "root": "Từ vựng HSK",
        }
        # Shown in Anki exactly as named: no sc_ prefix.
        assert {r["deck"] for r in out["rows"]} >= {"Từ vựng HSK::Greetings"}

    def test_without_one_the_source_is_kept(self):
        app = _loaded("app.js")
        out = json.loads(app["analyze"](self.TSV, "Demo", "file:Demo.tsv#"))
        assert out["identity"] == {
            "id": "file:Demo.tsv#",
            "deck": "Demo",
            "named": False,
            "root": "sc_Demo",
        }

    def test_the_shape_keeps_the_last_fields_of_the_same_kind(self):
        app = _loaded("app.js")
        app["analyze"](self.TSV, "Demo", "file:Demo.tsv#")
        last = {"kind": "basic", "fields": ["ID", "Word", "Old"]}
        assert json.loads(app["shape"](json.dumps(last)))["fields"] == [
            "ID",
            "Word",
            "Old",
            "Meaning",
        ]
        cloze = {"kind": "cloze", "fields": ["ID", "Old"]}
        assert json.loads(app["shape"](json.dumps(cloze)))["fields"] == [
            "ID",
            "Word",
            "Meaning",
        ]
        assert app["package_bytes"]("null")[:2] == b"PK"

    def test_a_repeated_id_packs_instead_of_crashing(self):
        app = _loaded("app.js")
        app["analyze"](self.TSV + "\nr1\tyes\t\tagain\tlần nữa", "Demo", "x")
        assert app["package_bytes"]("null")[:2] == b"PK"

    def test_a_ragged_row_is_squared_off(self):
        """A row longer than the header row still has to be a row of the table."""
        tsv = "\n".join(["ID\tWord", "r1\thello\tstray"])
        grid = self._analysis(tsv)["grid"]
        assert [len(row) for row in grid["cells"]] == [3, 3]
