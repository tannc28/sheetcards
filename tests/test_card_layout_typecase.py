#!/usr/bin/env python3
"""A typed answer that differs only in case is marked right.

A phone keyboard capitalises the first letter, and Anki's comparison is exact, so
"Library" against "library" was marked wrong on every card. The answer side now
carries ``card_layout._TYPE_CASE_SCRIPT``, which reads Anki's own comparison back
out of the page and, only when the two strings are equal ignoring case, puts in
the markup Anki draws for an exact match.

``CASES`` is what a real Anki 25.07 returned from ``col.compare_answer`` (inside
``<code id=typeans>``) — rslib's comparison, which desktop Anki, AnkiDroid and
AnkiMobile all print. The script runs here in node over a small fake DOM:
nothing in this suite has a browser, and the script only ever touches the
children of one element.
"""

import importlib.util
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

import pytest

from src.card_layout import _TYPE_CASE_NC_SCRIPT
from src.card_layout import _TYPE_CASE_SCRIPT
from src.card_layout import build_templates
from src.column_model import plan_columns
from src.sheet_config import parse_config_row

REPO = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node is not installed")

try:
    _HAS_ANKI = importlib.util.find_spec("anki") is not None
except (ImportError, ValueError):  # pragma: no cover - the suite mocks anki
    _HAS_ANKI = False

# (nc, expected, typed, what Anki 25.07 drew inside <code id=typeans>, fixed?)
CASES = [
    (
        False,
        "library",
        "Library",
        "<span class=typeBad>L</span><span class=typeGood>ibrary</span><br><span id=typearrow>&darr;</span><br><span class=typeMissed>l</span><span class=typeGood>ibrary</span>",
        True,
    ),
    (False, "library", "library", "<span class=typeGood>library</span>", False),
    (
        False,
        "library",
        "libary",
        "<span class=typeGood>lib</span><span class=typeMissed>-</span><span class=typeGood>ary</span><br><span id=typearrow>&darr;</span><br><span class=typeGood>lib</span><span class=typeMissed>r</span><span class=typeGood>ary</span>",
        False,
    ),
    (
        False,
        "library",
        "Libary",
        "<span class=typeBad>L</span><span class=typeGood>ib</span><span class=typeMissed>-</span><span class=typeGood>ary</span><br><span id=typearrow>&darr;</span><br><span class=typeMissed>l</span><span class=typeGood>ib</span><span class=typeMissed>r</span><span class=typeGood>ary</span>",
        False,
    ),
    (False, "library", "", "library", False),
    (
        False,
        "a < b & c",
        "A < B & C",
        "<span class=typeBad>A</span><span class=typeGood> &lt; </span><span class=typeBad>B</span><span class=typeGood> &amp; </span><span class=typeBad>C</span><br><span id=typearrow>&darr;</span><br><span class=typeMissed>a</span><span class=typeGood> &lt; </span><span class=typeMissed>b</span><span class=typeGood> &amp; </span><span class=typeMissed>c</span>",
        True,
    ),
    (
        False,
        "one, two",
        "One, Two",
        "<span class=typeBad>O</span><span class=typeGood>ne, </span><span class=typeBad>T</span><span class=typeGood>wo</span><br><span id=typearrow>&darr;</span><br><span class=typeMissed>o</span><span class=typeGood>ne, </span><span class=typeMissed>t</span><span class=typeGood>wo</span>",
        True,
    ),
    (
        False,
        "straße",
        "STRASSE",
        "<span class=typeBad>STRASSE</span><br><span id=typearrow>&darr;</span><br><span class=typeMissed>straße</span>",
        False,
    ),
    (
        False,
        "el árbol",
        "El arbol",
        "<span class=typeBad>E</span><span class=typeGood>l </span><span class=typeBad>a</span><span class=typeGood>rbol</span><br><span id=typearrow>&darr;</span><br><span class=typeMissed>e</span><span class=typeGood>l </span><span class=typeMissed>á</span><span class=typeGood>rbol</span>",
        False,
    ),
    (
        False,
        "el árbol",
        "El árbol",
        "<span class=typeBad>E</span><span class=typeGood>l árbol</span><br><span id=typearrow>&darr;</span><br><span class=typeMissed>e</span><span class=typeGood>l árbol</span>",
        True,
    ),
    (
        True,
        "el árbol",
        "El arbol",
        "<span class=typeBad>E</span><span class=typeGood>l arbol</span><br><span id=typearrow>&darr;</span><br><span class=typeMissed>e</span><span class=typeGood>l a\u0301rbol</span>",
        True,
    ),
    (
        True,
        "el árbol",
        "El Arbol",
        "<span class=typeBad>E</span><span class=typeGood>l </span><span class=typeBad>A</span><span class=typeGood>rbol</span><br><span id=typearrow>&darr;</span><br><span class=typeMissed>e</span><span class=typeGood>l </span><span class=typeMissed>a\u0301</span><span class=typeGood>rbol</span>",
        True,
    ),
    (True, "el árbol", "el arbol", "<span class=typeGood>el árbol</span>", False),
    (
        True,
        "el árbol",
        "El arbo",
        "<span class=typeBad>E</span><span class=typeGood>l arbo</span><span class=typeMissed>-</span><br><span id=typearrow>&darr;</span><br><span class=typeMissed>e</span><span class=typeGood>l a\u0301rbo</span><span class=typeMissed>l</span>",
        False,
    ),
    (
        False,
        "cat",
        "Cat ",
        "<span class=typeBad>C</span><span class=typeGood>at</span><span class=typeBad> </span><br><span id=typearrow>&darr;</span><br><span class=typeMissed>c</span><span class=typeGood>at</span>",
        False,
    ),
    (
        False,
        "Went",
        "went",
        "<span class=typeBad>w</span><span class=typeGood>ent</span><br><span id=typearrow>&darr;</span><br><span class=typeMissed>W</span><span class=typeGood>ent</span>",
        True,
    ),
    (
        False,
        "went",
        "gone",
        "<span class=typeBad>go</span><span class=typeGood>n</span><span class=typeBad>e</span><br><span id=typearrow>&darr;</span><br><span class=typeMissed>we</span><span class=typeGood>n</span><span class=typeMissed>t</span>",
        False,
    ),
]


class _Tree(HTMLParser):
    """Anki's comparison markup as nested dicts, for the fake DOM and for checks."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = {"kids": []}
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        node = {
            "tag": tag,
            "id": attrs.get("id", ""),
            "cls": attrs.get("class", ""),
            "kids": [],
        }
        self.stack[-1]["kids"].append(node)
        if tag != "br":
            self.stack.append(node)

    def handle_endtag(self, tag):
        if tag != "br" and len(self.stack) > 1:
            self.stack.pop()

    def handle_data(self, data):
        self.stack[-1]["kids"].append({"text": data})


def _tree(html):
    parser = _Tree()
    parser.feed(html)
    parser.close()
    return parser.root["kids"]


# A DOM with only what the script asks of one element: enough to run it in node.
_FAKE_DOM = r"""
class Node {
  constructor(spec) {
    if ("text" in spec) { this.nodeType = 3; this.nodeValue = spec.text; this.childNodes = []; }
    else {
      this.nodeType = 1; this.tagName = spec.tag.toUpperCase(); this.id = spec.id || "";
      this.className = spec.cls || ""; this.attrs = {};
      this.childNodes = (spec.kids || []).map((k) => new Node(k));
    }
  }
  get children() { return this.childNodes.filter((n) => n.nodeType === 1); }
  get firstChild() { return this.childNodes[0] || null; }
  get textContent() {
    return this.nodeType === 3 ? this.nodeValue : this.childNodes.map((n) => n.textContent).join("");
  }
  set textContent(v) { this.childNodes = [new Node({ text: String(v) })]; }
  getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; }
  setAttribute(k, v) { this.attrs[k] = String(v); }
  removeChild(n) { this.childNodes = this.childNodes.filter((c) => c !== n); return n; }
  appendChild(n) { this.childNodes.push(n); return n; }
  dump() {
    if (this.nodeType === 3) return { text: this.nodeValue };
    return { tag: this.tagName.toLowerCase(), id: this.id, cls: this.className,
             kids: this.childNodes.map((n) => n.dump()) };
  }
}
const input = JSON.parse(require("fs").readFileSync(0, "utf8"));
const out = [];
for (const c of input.cases) {
  const code = new Node({ tag: "code", id: "typeans", kids: c.tree });
  globalThis.window = {};
  globalThis.document = {
    createElement: (tag) => new Node({ tag }),
    querySelectorAll: (sel) => (sel === "code#typeans" ? [code] : []),
  };
  const body = (c.nc ? input.nc : input.plain).replace(/^<script>|<\/script>$/g, "");
  let error = "";
  try {
    new Function(body)();
    const once = JSON.stringify(code.dump().kids);
    new Function(body)();
    if (JSON.stringify(code.dump().kids) !== once) error = "not idempotent";
  } catch (e) { error = String(e); }
  out.push({ kids: code.dump().kids, error });
}
console.log(JSON.stringify(out));
"""


def _run(cases):
    """Each ``(nc, inner html)`` after the script ran over it (twice)."""
    payload = {
        "plain": _TYPE_CASE_SCRIPT,
        "nc": _TYPE_CASE_NC_SCRIPT,
        "cases": [{"nc": nc, "tree": _tree(html)} for nc, html in cases],
    }
    result = subprocess.run(
        [NODE, "-e", _FAKE_DOM],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    found = json.loads(result.stdout)
    assert all(not r["error"] for r in found), found
    return [r["kids"] for r in found]


def _exact(expected):
    """What Anki draws when the typed answer matches."""
    text = unicodedata.normalize("NFC", expected)
    return _tree(
        "<span class=typeGood>"
        + text.replace("&", "&amp;").replace("<", "&lt;")
        + "</span>"
    )


@needs_node
@pytest.mark.unit
def test_only_a_difference_of_case_is_forgiven():
    got = _run([(nc, raw) for nc, _e, _t, raw, _f in CASES])
    for (nc, expected, typed, raw, fixed), after in zip(CASES, got, strict=True):
        want = _exact(expected) if fixed else _tree(raw)
        assert after == want, f"{typed!r} for {expected!r} (nc={nc})"


@needs_node
@pytest.mark.unit
@pytest.mark.parametrize(
    "html",
    [
        # A wrapper the script does not know: some client drawing its own diff.
        "<div><span class=typeBad>L</span><span class=typeGood>ibrary</span><br>"
        "<span id=typearrow>&darr;</span><br><span class=typeMissed>l</span>"
        "<span class=typeGood>ibrary</span></div>",
        # A word outside any span.
        "Library<br><span id=typearrow>&darr;</span><br>"
        "<span class=typeGood>library</span>",
        # A class it has never seen.
        "<span class=typeOops>Library</span><br><span id=typearrow>&darr;</span><br>"
        "<span class=typeGood>library</span>",
        # No arrow: not the two-line form.
        "<span class=typeBad>Library</span><br><span class=typeGood>library</span>",
        # A placeholder that is not a dash.
        "<span class=typeMissed>L</span><span class=typeGood>ibrary</span><br>"
        "<span id=typearrow>&darr;</span><br><span class=typeGood>library</span>",
    ],
)
def test_markup_it_does_not_recognise_is_left_alone(html):
    assert _run([(False, html)]) == [_tree(html)]


def _templates(cell):
    plan = plan_columns(["ID", "Meaning", "Word"])
    config = parse_config_row({"ID": "#config reverse", "Word": cell}, plan)
    return build_templates(plan, config)


@pytest.mark.unit
def test_the_answer_of_a_typed_card_carries_it():
    forward, reverse = _templates("type")
    assert _TYPE_CASE_SCRIPT in forward["afmt"]
    assert "scTypeCase" not in forward["qfmt"]
    # The reverse card asks for nothing to be typed.
    assert "scTypeCase" not in reverse["afmt"]


@pytest.mark.unit
def test_nc_folds_the_accents_too():
    forward = _templates("type=nc")[0]
    assert _TYPE_CASE_NC_SCRIPT in forward["afmt"]
    assert _TYPE_CASE_SCRIPT not in forward["afmt"]


@pytest.mark.unit
def test_a_card_with_nothing_to_type_does_not():
    assert "scTypeCase" not in _templates("size=20")[0]["afmt"]


# The reviewer's own substitution (aqt/reviewer.py typeAnsQuestionFilter and
# typeAnsAnswerFilter), run against a real collection on templates this repo
# generated. The pure modules are reached through a fabricated package, as the
# save harness in tests/test_card_layout.py does, so no Qt is needed.
_REVIEW_HARNESS = r"""
import json, os, re, sys, tempfile, types
from anki.collection import Collection

pkg = types.ModuleType("sc"); pkg.__path__ = [os.path.join(sys.argv[1], "src")]
sys.modules["sc"] = pkg
from sc.column_model import plan_columns
from sc.sheet_config import parse_config_row
from sc.card_layout import build_templates

col = Collection(os.path.join(tempfile.mkdtemp(), "c.anki2"))
pat = r"\[\[type:(.+?)\]\]"
out = {"compare": [], "pages": []}
for nc, expected, typed in json.loads(sys.argv[2]):
    out["compare"].append(col.compare_answer(expected, typed, not nc))
for n, (cell, word, typed) in enumerate(json.loads(sys.argv[3])):
    plan = plan_columns(["ID", "Meaning", "Word"])
    cfg = parse_config_row({"ID": "#config", "Word": cell}, plan)
    model = col.models.new("t%d" % n)
    for name in plan.note_type_fields():
        col.models.add_field(model, col.models.new_field(name))
    for t in build_templates(plan, cfg):
        tmpl = col.models.new_template(t["name"])
        tmpl["qfmt"], tmpl["afmt"] = t["qfmt"], t["afmt"]
        col.models.add_template(model, tmpl)
    col.models.add(model)
    note = col.new_note(col.models.by_name(model["name"]))
    note["ID"], note["Meaning"], note["Word"] = "w1", "m", word
    col.add_note(note, 1)
    card = note.cards()[0]
    fld = re.search(pat, card.question()).group(1)
    shown = col.compare_answer(note["Word"], typed, not fld.startswith("nc:"))
    page = card.answer().replace("<hr id=answer>", "")
    page = re.sub(pat, lambda m: "<div>" + shown + "</div>", page)
    out["pages"].append(page)
print(json.dumps(out))
"""


@pytest.mark.slow
@pytest.mark.skipif(not _HAS_ANKI, reason="the real anki library is not installed")
@needs_node
def test_against_a_real_anki():
    """Anki still draws what ``CASES`` says, and a real answer page is fixed."""
    reviews = [
        ("type", "library", "Library", True),
        ("type=nc", "el árbol", "El arbol", True),
        ("type", "library", "libary", False),
    ]
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            _REVIEW_HARNESS,
            str(REPO),
            json.dumps([[nc, e, t] for nc, e, t, _r, _f in CASES]),
            json.dumps([[c, w, t] for c, w, t, _f in reviews]),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO),
    )
    assert result.returncode == 0, result.stderr
    found = json.loads(result.stdout)
    for (_nc, expected, typed, raw, _f), drawn in zip(
        CASES, found["compare"], strict=True
    ):
        assert drawn == f"<code id=typeans>{raw}</code>", (expected, typed)

    inner = []
    for (cell, _w, _t, _f), page in zip(reviews, found["pages"], strict=True):
        code = re.search(r"<code id=typeans>(.*?)</code>", page)
        # The script comes after the comparison, so it finds it already drawn.
        assert code and page.index("scTypeCase") > code.end()
        inner.append((cell == "type=nc", code.group(1)))
    after = _run(inner)
    for (_c, word, _t, fixed), (_nc, raw), got in zip(
        reviews, inner, after, strict=True
    ):
        assert got == (_exact(word) if fixed else _tree(raw))
