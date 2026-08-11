#!/usr/bin/env python3
"""Assembles the preview site into build/site/.

The site is static, but it is not self-contained in the repository on purpose:
the Python it runs in the browser is copied straight out of ``src/`` at build
time rather than kept as a second copy under ``site/``. A checked-in copy would
be a fork of the add-on that nobody would notice going stale.

Usage:
    python scripts/build_site.py            # build into build/site
    python scripts/build_site.py --serve    # build, then serve it on :8000
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"
SITE = REPO / "site"
OUT = REPO / "build" / "site"


def modules_the_site_loads():
    """The module list declared in site/app.js — the only place it is written."""
    app = (SITE / "app.js").read_text(encoding="utf-8")
    match = re.search(r"const PURE_MODULES = \[(.*?)\]", app, re.S)
    if not match:
        sys.exit("site/app.js does not declare PURE_MODULES")
    return module_names(match.group(1))


def module_names(listed):
    """The names inside a JS array literal, comments and all.

    Comments are stripped first rather than split around: a `//` line explaining
    why a module is in the list will contain a comma sooner or later, and then
    half a sentence gets looked up as a module.
    """
    listed = re.sub(r"//[^\n]*", "", listed)
    return [name.strip().strip("\"'") for name in listed.split(",") if name.strip()]


def check_purity(names):
    """Refuses to ship a module that reaches outside the standard library.

    The browser has no Anki to import, so this failing at build time is far
    better than the page failing at load time in front of a user.
    """
    allowed = set(names) | {"errors"}
    problems = []
    for name in names:
        text = (SRC / f"{name}.py").read_text(encoding="utf-8")
        for line in text.splitlines():
            imported = re.match(
                r"from \.(\w+) import|from \.(\w+)|from \. import (\w+)", line
            )
            if imported:
                target = next(g for g in imported.groups() if g)
                if target not in allowed:
                    problems.append(
                        f"{name}.py imports .{target}, which is not in the site's module set"
                    )
            if re.match(r"\s*(from|import)\s+(aqt|anki|PyQt6)\b", line):
                problems.append(
                    f"{name}.py imports {line.strip()!r} — it cannot run in the browser"
                )
    if problems:
        sys.exit("Preview site would break:\n  " + "\n  ".join(problems))


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    # Files only: importing site/workbook.py — which the test suite does — leaves a
    # __pycache__ beside it, and a directory here used to stop the build dead.
    for item in sorted(SITE.iterdir()):
        if item.name.startswith(".") or not item.is_file():
            continue
        shutil.copy2(item, OUT / item.name)

    names = modules_the_site_loads()
    check_purity(names)

    pkg = OUT / "s2a"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    for name in names:
        shutil.copy2(SRC / f"{name}.py", pkg / f"{name}.py")

    # GitHub Pages runs the output through Jekyll unless told not to, which
    # silently drops files and directories whose names begin with an underscore.
    (OUT / ".nojekyll").write_text("", encoding="utf-8")

    total = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"built {OUT.relative_to(REPO)}")
    print(f"  page      : {len(list(OUT.glob('*')))} files")
    print(f"  python    : {', '.join(names)}")
    print(f"  total     : {total / 1024:.0f} KB (Pyodide itself loads from a CDN)")
    return OUT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--serve", action="store_true", help="serve the result on :8000"
    )
    args = parser.parse_args()

    out = build()
    if args.serve:
        import functools
        import http.server

        handler = functools.partial(
            http.server.SimpleHTTPRequestHandler, directory=str(out)
        )
        print("\nhttp://localhost:8000  (Ctrl+C to stop)")
        http.server.ThreadingHTTPServer(("", 8000), handler).serve_forever()


if __name__ == "__main__":
    main()
