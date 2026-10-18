"""The first load's size and the mobile-data line (site/pyodide.js), in node."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

MODULE = Path(__file__).resolve().parent.parent / "site" / "pyodide.js"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")


def _run(expr):
    script = (
        "import { FIRST_LOAD_BYTES, mb, onMobileData, prefetchPython } from "
        f'"{MODULE.as_uri()}";\nconsole.log(JSON.stringify({expr}));'
    )
    out = subprocess.run(
        [NODE, "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


@pytest.mark.unit
def test_the_size_said_is_what_the_cdn_sends():
    # brotli sizes of pyodide 0.28.3's files plus sqlite3, measured 2026-10
    assert 5.5e6 < _run("FIRST_LOAD_BYTES") < 6.5e6
    assert _run("mb(FIRST_LOAD_BYTES)") == "5.9"
    assert _run("mb(0)") == "0.1"


@pytest.mark.unit
@pytest.mark.parametrize(
    "connection, said",
    [
        ("{type: 'cellular'}", True),
        ("{saveData: true}", True),
        ("{effectiveType: '3g'}", True),
        ("{effectiveType: 'slow-2g'}", True),
        ("{type: 'wifi', effectiveType: '4g'}", False),
        ("undefined", False),
    ],
)
def test_mobile_data_is_said_only_where_the_browser_says_so(connection, said):
    assert _run(f"onMobileData({{connection: {connection}}})") is said


@pytest.mark.unit
def test_the_prefetch_never_spends_mobile_data():
    # requestIdleCallback is stubbed to never run, so nothing is fetched here.
    out = _run(
        "(globalThis.requestIdleCallback = () => 0, "
        "[prefetchPython({connection: {type: 'cellular'}}),"
        " prefetchPython({connection: {saveData: true}}),"
        " prefetchPython({connection: {type: 'wifi'}}),"
        " prefetchPython({})])"
    )
    assert out == [False, False, True, True]
