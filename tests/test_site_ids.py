#!/usr/bin/env python3
"""Every element the site reaches for is an element the site has.

`$("#reload")` on a page with no `id="reload"` throws `null is not an object` at
the moment the control is used, which is a moment nobody runs into until the
feature is being used for real. There is no framework here to catch it and no
test that loads the page — Pyodide makes that a five-minute round trip — so the
markup and the script are checked against each other statically instead.
"""

import re
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"

PAGES = {"app.js": "index.html", "editor.js": "editor.html"}


def _read(name):
    return (SITE / name).read_text(encoding="utf-8")


def _wanted(script):
    """The ids a script asks the document for."""
    return set(re.findall(r'\$\("#([\w-]+)"\)', script)) | set(
        re.findall(r'getElementById\("([\w-]+)"\)', script)
    )


def _built():
    """The ids the site writes into markup of its own, in any module.

    The card frame and the right-click menu are built at the moment they are
    needed rather than sitting empty in the page, so they are legitimately absent
    from both HTML files.
    """
    js = "".join(_read(p.name) for p in SITE.glob("*.js"))
    return set(re.findall(r'id="([\w-]+)"', js)) | set(
        re.findall(r'\.id = "([\w-]+)"', js)
    )


def test_every_id_a_script_reaches_for_exists():
    built = _built()
    for script, page in PAGES.items():
        markup = set(re.findall(r'\bid="([\w-]+)"', _read(page)))
        missing = sorted(_wanted(_read(script)) - markup - built)
        assert not missing, f"{script} reaches for ids no page has: {missing}"


def test_every_translated_attribute_names_a_real_element():
    """`data-i18n-attr` is applied by selector, so a typo is silent."""
    for page in PAGES.values():
        for pairs in re.findall(r'data-i18n-attr="([^"]+)"', _read(page)):
            for pair in pairs.split(","):
                assert ":" in pair, f"{page}: {pair!r} is not attr:key"
