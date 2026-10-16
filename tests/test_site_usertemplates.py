"""Create sheet's own templates (site/usertemplates.js), run in node.

The store is localStorage in the browser; here it is a plain object with the
same two methods, which is all the module asks of it. What is pinned: a kept
template is the header, the settings row and one word as a sample; the same
title replaces rather than doubles; the cap and the size limit refuse rather than
evict; a broken or refusing store costs the feature, never an exception.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(NODE is None, reason="node is not installed"),
]

SCRIPT = """
const m = await import(%s);
const store = () => { const data = {}; return {
  data, getItem: (k) => (k in data ? data[k] : null), setItem: (k, v) => { data[k] = String(v); } }; };
const grid = [
  ["ID", "Word", "Meaning"],
  ["#config", "size=44; tts=en_US", "side=back"],
  ["w01", "hello", "xin chào"],
  ["w02", "bye", "tạm biệt"],
  ["w03", "", ""],
];
const out = {};
const s = store();
out.first = m.keepTemplate(grid, "Mine", s, 1000);
out.listed = m.listTemplates(s);
out.again = m.keepTemplate(grid, "Mine", s, 2000);
out.afterAgain = m.listTemplates(s).length;
for (let i = 0; i < 20; i++) out.last = m.keepTemplate(grid, "T" + i, s, 3000 + i);
out.count = m.listTemplates(s).length;
out.dropped = m.dropTemplate(m.listTemplates(s)[0].id, s);
out.afterDrop = m.listTemplates(s).length;
out.dropMissing = m.dropTemplate("nope", s);
const big = [["ID", "Text"], ["#config", "label=" + "x".repeat(40000)], ["w01", "a"]];
out.longWord = m.keepTemplate([["ID", "Text"], ["#config", ""], ["w01", "x".repeat(40000)]], "Long", store());
out.big = m.keepTemplate(big, "Big", store());
out.empty = m.keepTemplate([], "Empty", store());
const broken = store(); broken.data[m.STORE] = "{not json";
out.broken = m.listTemplates(broken);
const refusing = { getItem: () => null, setItem: () => { throw new Error("quota"); } };
out.refused = m.keepTemplate(grid, "X", refusing);
out.noConfig = m.templateRows([["ID", "A"], ["w01", "a"], ["w02", "b"]]);
process.stdout.write(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def run():
    module = json.dumps((REPO / "site" / "usertemplates.js").as_uri())
    done = subprocess.run(
        [NODE, "--no-warnings", "--input-type=module", "-e", SCRIPT % module],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return json.loads(done.stdout)


def test_a_template_is_the_header_the_settings_row_and_one_sample(run):
    assert run["first"]["ok"] and not run["first"]["replaced"]
    (tpl,) = run["listed"]
    assert tpl["title"] == "Mine"
    assert tpl["rows"] == [
        ["ID", "Word", "Meaning"],
        ["#config", "size=44; tts=en_US", "side=back"],
        ["w01", "hello", "xin chào"],
    ]


def test_the_same_title_replaces(run):
    assert run["again"]["ok"] and run["again"]["replaced"]
    assert run["again"]["template"]["id"] == run["first"]["template"]["id"]
    assert run["afterAgain"] == 1


def test_the_cap_refuses_rather_than_evicts(run):
    assert run["count"] == 12
    assert run["last"] == {"ok": False, "reason": "full"}


def test_delete(run):
    assert run["dropped"] is True
    assert run["afterDrop"] == 11
    assert run["dropMissing"] is False


def test_limits_and_broken_stores(run):
    assert run["big"] == {"ok": False, "reason": "big"}
    # A sample too long to keep is given up before the template is.
    assert run["longWord"]["ok"]
    assert run["longWord"]["template"]["rows"] == [["ID", "Text"], ["#config", ""]]
    assert run["empty"] == {"ok": False, "reason": "empty"}
    assert run["broken"] == []
    assert run["refused"] == {"ok": False, "reason": "storage"}


def test_a_sheet_without_a_settings_row_keeps_its_header(run):
    assert run["noConfig"] == [["ID", "A"], ["w01", "a"]]
