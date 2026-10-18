"""Download .apkg crossed the JS/Python boundary with a null and crashed.

JavaScript's ``null`` reaches Python as ``JsNull``, not ``None``, so a guard
written ``if files is not None`` calls ``.to_py()`` on it and the download dies
with "'JsNull' object has no attribute 'to_py'" -- which shipped once. Pyodide
is not in the suite, so this pins both sides of the call by their text.
"""

import re
from pathlib import Path

import pytest

APP = (Path(__file__).resolve().parent.parent / "site" / "app.js").read_text("utf-8")


@pytest.mark.unit
def test_the_analyzer_never_tests_a_js_value_against_none():
    analyzer = APP.split("const ANALYZER = String.raw`", 1)[1].split("`;", 1)[0]
    assert not re.search(r"\bis not None\b|\bis None\b", analyzer)


@pytest.mark.unit
def test_build_package_never_hands_python_a_null():
    call = re.search(r"buildPackage = \(last, files\) => (.+);", APP).group(1)
    assert "|| null" not in call and "|| []" in call
