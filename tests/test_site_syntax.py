"""The preview site's JavaScript has to parse.

Nothing else in the suite loads it: the Python it runs is tested directly, and a
syntax error in ``site/app.js`` shows up only as a page that renders its markup
and then does nothing at all — no error anyone sees, no failing test.

The way this happened was `ANALYZER`, the block of Python that app.js hands to
Pyodide. It is a JS template literal, so a backtick written inside it — in a
Python comment quoting an identifier, which is the natural way to write one —
closes the string early and the rest of the file is parsed as JavaScript. The
browser's complaint points at whatever word followed the backtick, nowhere near
the cause.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SITE = REPO / "site"

NODE = shutil.which("node")


def _modules():
    """Every module the site ships, found rather than listed.

    Checked by parsing, not by running: running one would need a DOM, and a file
    that cannot be parsed cannot run either. Found rather than listed because a
    list is a thing to forget — and an unparsed module is invisible until the
    page it belongs to silently does nothing.
    """
    return sorted(path.name for path in SITE.glob("*.js"))


@pytest.mark.unit
@pytest.mark.skipif(NODE is None, reason="node is not installed")
@pytest.mark.parametrize("name", _modules())
def test_the_module_parses(name, tmp_path):
    # Copied to .mjs because `node --check` parses a bare .js as CommonJS, where
    # the `import` at the top of every one of these is a syntax error in itself.
    target = tmp_path / (Path(name).stem + ".mjs")
    target.write_text((SITE / name).read_text(encoding="utf-8"), encoding="utf-8")

    result = subprocess.run(
        [NODE, "--check", str(target)], capture_output=True, text=True
    )
    assert result.returncode == 0, f"site/{name} does not parse:\n{result.stderr}"


@pytest.mark.unit
def test_the_embedded_python_carries_no_backtick():
    """The specific trap, named, so the next person does not have to find it.

    ``node --check`` above already catches this — but only as "unexpected
    identifier" pointing at a line that is fine. This says what is actually wrong.
    """
    app = (SITE / "app.js").read_text(encoding="utf-8")
    opener = "const ANALYZER = String.raw`"
    start = app.index(opener) + len(opener)
    block = app[start : app.index("`;", start)]

    offenders = [
        f"line {i}: {line.strip()}"
        for i, line in enumerate(block.splitlines(), 1)
        if "`" in line
    ]
    assert not offenders, (
        "a backtick inside ANALYZER closes the template literal early:\n  "
        + "\n  ".join(offenders)
    )
