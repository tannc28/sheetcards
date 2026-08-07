"""The pure layer must stay importable with no Anki, no Qt and no add-on runtime.

``site/`` runs these very files in the browser through Pyodide so a sheet can be
previewed before anything is installed. That only works while they import nothing
but the standard library and each other, and nothing in an ordinary test run would
notice the day someone adds ``from .compat import mw`` to ``column_model`` — the
suite mocks ``aqt`` for every other module, so the import would simply succeed.

So this runs each module in a *fresh interpreter* with the mocks absent and the
add-on's own package machinery unavailable, which is the same condition the
browser imposes.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"

# The exact set the preview site loads. Keep this in step with site/app.js —
# test_site_loads_the_same_modules below fails if they drift apart.
PURE_MODULES = ["errors", "column_model", "sheet_config", "card_layout", "tsv_model"]


def _run_isolated(code):
    """Runs code in a fresh interpreter that cannot see aqt, anki or conftest."""
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(REPO),
    )
    return result


@pytest.mark.unit
def test_pure_modules_import_without_anki():
    """Each module imports as a plain package, exactly as Pyodide will load it."""
    code = f"""
import importlib, importlib.util, json, sys, types

# Build the same package Pyodide builds: the source files under one package name,
# with nothing else from the repo importable.
pkg = types.ModuleType("s2a")
pkg.__path__ = [{str(SRC)!r}]
sys.modules["s2a"] = pkg

# Anything reaching for Anki must fail loudly rather than find a mock.
for blocked in ("aqt", "anki", "PyQt6"):
    sys.modules[blocked] = None

loaded = []
for name in {PURE_MODULES!r}:
    importlib.import_module("s2a." + name)
    loaded.append(name)
print(json.dumps(loaded))
"""
    result = _run_isolated(code)
    assert result.returncode == 0, (
        "The pure layer picked up a dependency it cannot have in the browser.\n"
        "Move the Anki-dependent code into data_processor (or another runtime "
        f"module) and re-export it from there.\n\n{result.stderr}"
    )
    assert json.loads(result.stdout.strip().splitlines()[-1]) == PURE_MODULES


@pytest.mark.unit
def test_pure_layer_produces_templates_without_anki():
    """The whole sheet-to-template pipeline runs with no collection in sight.

    Importing cleanly is not enough — the site calls straight through to
    ``build_templates``, so the path a user's sheet actually takes is the thing
    worth pinning.
    """
    code = f"""
import json, sys, types
pkg = types.ModuleType("s2a"); pkg.__path__ = [{str(SRC)!r}]
sys.modules["s2a"] = pkg
for blocked in ("aqt", "anki", "PyQt6"):
    sys.modules[blocked] = None

from s2a.tsv_model import parse_tsv_data, row_to_dict, build_tags, row_has_cloze
from s2a.sheet_config import is_config_row, parse_config_row
from s2a.card_layout import build_templates

tsv = (
    "ID\\tSYNC\\tSUBDECK 1\\tHanzi\\tPinyin\\n"
    "#config reverse\\t\\t\\tsize=48; tts=zh_CN\\tcolor=muted\\n"
    "1\\ttrue\\tUnit 1\\t\\u4f1a\\u8bae\\thu\\u00ec y\\u00ec\\n"
)
parsed = parse_tsv_data(tsv)
plan = parsed["plan"]
rows = [row_to_dict(r, parsed["headers"]) for r in parsed["rows"]]

config = parse_config_row(rows[0], plan) if is_config_row(rows[0], plan) else None
row = rows[1]
templates = build_templates(plan, config)

print(json.dumps({{
    "content": plan.content_headers,
    "names": [t["name"] for t in templates],
    "tts": "{{{{tts zh_CN:Hanzi}}}}" in templates[0]["qfmt"],
    "tags": build_tags(row, plan),
    "cloze": row_has_cloze(row, plan),
}}, ensure_ascii=False))
"""
    result = _run_isolated(code)
    assert result.returncode == 0, result.stderr

    out = json.loads(result.stdout.strip().splitlines()[-1])
    assert out["content"] == ["Hanzi", "Pinyin"]
    assert out["names"] == ["Card 1", "Card 2 (reverse)"]
    assert out["tts"] is True
    assert out["tags"] == ["sheets2anki", "sheets2anki::unit_1"]
    assert out["cloze"] is False


@pytest.mark.unit
def test_site_loads_the_same_modules():
    """The site's module list is the list above, so neither can be updated alone."""
    app = (REPO / "site" / "app.js").read_text(encoding="utf-8")
    marker = "const PURE_MODULES = ["
    assert marker in app, "site/app.js no longer declares PURE_MODULES"

    listed = app.split(marker, 1)[1].split("]", 1)[0]
    names = [chunk.strip().strip("\"'") for chunk in listed.split(",")]
    names = [n for n in names if n]

    assert names == PURE_MODULES, (
        "site/app.js loads a different set of modules than this test pins.\n"
        f"  site: {names}\n  test: {PURE_MODULES}"
    )
