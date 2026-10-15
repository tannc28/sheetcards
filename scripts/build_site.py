#!/usr/bin/env python3
"""Assembles the website into build/site/.

Four kinds of page: the landing page (``site/index.html``), the preview
(``site/preview.html``), the settings-row editor (``site/editor.html``) and the
documentation, written as Markdown under ``docs/site/`` and converted here.

The site is static, but it is not self-contained in the repository on purpose:
the Python it runs in the browser is copied straight out of ``src/`` at build
time rather than kept as a second copy under ``site/``. A checked-in copy would
be a fork of the add-on that nobody would notice going stale. The landing page's
demo cards are rendered by those same modules here, at build time, so the page
shows the add-on's real card templates without loading Pyodide.

Building the docs needs the ``markdown`` package (the ``dev`` extra). The add-on
itself does not: this script is the only thing that imports it.

Usage:
    python scripts/build_site.py            # build into build/site
    python scripts/build_site.py --serve    # build, then serve it on :8000
"""

import argparse
import html
import json
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"
SITE = REPO / "site"
DOCS = REPO / "docs" / "site"
OUT = REPO / "build" / "site"
EXAMPLES = REPO / "examples" / "sheetcards-examples.xlsx"

# The documentation's table of contents: (group, [page, ...]). A page is the
# name of a Markdown file in docs/site/, and its title is that file's first
# heading. Declared here rather than found, because order is information — the
# build refuses a page that is missing from this list or a name with no file.
DOC_GROUPS = [
    ("Start", ["index", "getting-started", "examples"]),
    (
        "Write a sheet",
        ["columns", "settings-row", "card-types", "text", "media", "tts"],
    ),
    ("In Anki", ["menu", "syncing", "sources"]),
    ("Help", ["faq", "developers"]),
]

# Docs pages written in Vietnamese. The docs open on one: most readers are
# Vietnamese, so the first page anyone lands on is in their language.
VI_DOCS = {"index"}

# The landing page's demo: (sheet in the example workbook, row ID, i18n key of
# its label). Real rows, rendered with the real templates — the page claims the
# sheet becomes this card, so it had better be the card the add-on makes.
HOME_EXAMPLES = [
    ("15 Theme + subdeck (màu, tầng)", "n01", "demoEnglish"),
    ("13 Furigana (phiên âm kanji)", "f01", "demoJapanese"),
    ("06 Cloze (điền chỗ trống)", "z01", "demoCloze"),
]


def modules_the_site_loads():
    """The module list declared in site/pyodide.js — the only place it is written."""
    app = (SITE / "pyodide.js").read_text(encoding="utf-8")
    match = re.search(r"export const PURE_MODULES = \[(.*?)\]", app, re.S)
    if not match:
        sys.exit("site/pyodide.js does not declare PURE_MODULES")
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


def build(out=OUT):
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    # Files only: importing site/workbook.py — which the test suite does — leaves a
    # __pycache__ beside it, and a directory here used to stop the build dead.
    # A name starting with "_" is a build input (the docs template), not a page.
    for item in sorted(SITE.iterdir()):
        if item.name.startswith((".", "_")) or not item.is_file():
            continue
        shutil.copy2(item, out / item.name)

    names = modules_the_site_loads()
    check_purity(names)

    pkg = out / "sc"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    for name in names:
        shutil.copy2(SRC / f"{name}.py", pkg / f"{name}.py")

    build_home_cards(out)
    pages = build_docs(out)

    # GitHub Pages runs the output through Jekyll unless told not to, which
    # silently drops files and directories whose names begin with an underscore.
    (out / ".nojekyll").write_text("", encoding="utf-8")

    total = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"built {out}")
    print(f"  page      : {len(list(out.glob('*')))} files")
    print(f"  docs      : {pages} pages")
    print(f"  python    : {', '.join(names)}")
    print(f"  total     : {total / 1024:.0f} KB (Pyodide itself loads from a CDN)")
    return out


# ---------------------------------------------------------------------------
# The landing page's demo cards
# ---------------------------------------------------------------------------


def _pure_package(out):
    """The ``sc`` package just copied into ``out``, imported from there.

    The same files the browser loads, so the demo cannot be rendered by a
    different version of the code than the preview runs.
    """
    ours = [m for m in sys.modules if m == "sc" or m.startswith("sc.")]
    saved = {m: sys.modules.pop(m) for m in ours}
    sys.path.insert(0, str(out))
    try:
        from sc import card_layout
        from sc import tsv_model
        from sc import workbook

        return tsv_model, card_layout, workbook
    finally:
        # Put back whatever "sc" meant before — the test suite fabricates a
        # package of that name too, and must not find this one in its place.
        sys.path.remove(str(out))
        for m in [m for m in sys.modules if m == "sc" or m.startswith("sc.")]:
            del sys.modules[m]
        sys.modules.update(saved)


def _letter(index):
    """The column letter a spreadsheet shows: 0 → A, 25 → Z, 26 → AA."""
    text, n = "", index + 1
    while n:
        n, rest = divmod(n - 1, 26)
        text = chr(65 + rest) + text
    return text


def home_cards(out):
    """Each demo row as the sheet shows it and the templates the add-on builds."""
    tm, card_layout, workbook = _pure_package(out)
    data = EXAMPLES.read_bytes()
    cards = []
    for sheet, row_id, label in HOME_EXAMPLES:
        parsed = tm.parse_tsv_data(workbook.sheet_tsv(data, sheet), [])
        deck = tm.build_remote_deck_from_tsv(parsed, "", [])
        plan, cfg = deck.plan, deck.sheet_config
        headers = parsed["headers"]
        config, row, line = parsed["rows"][0], None, 0
        for at, raw in enumerate(parsed["rows"]):
            if raw and raw[0] == row_id:
                # Row 1 is the header, so the first parsed row is row 2.
                row, line = raw, at + 2
        if row is None:
            sys.exit(f"home demo: {sheet!r} has no row {row_id!r}")
        values = tm.row_to_dict(row, headers)
        tm.apply_media_rewrites(values, plan, cfg)
        front, back = card_layout.split_sides(plan, cfg)
        shown = [plan.id_header] + list(plan.content_headers)
        columns = []
        for name in shown:
            at = headers.index(name)
            columns.append(
                {
                    "letter": _letter(at),
                    "name": name,
                    "config": config[at] if at < len(config) else "",
                    "value": row[at] if at < len(row) else "",
                    "side": (
                        "front" if name in front else "back" if name in back else "none"
                    ),
                }
            )
        template = card_layout.build_templates(plan, cfg, bool(cfg.cloze_field))[0]
        cards.append(
            {
                "sheet": sheet,
                "label": label,
                "line": line,
                "columns": columns,
                "template": {"qfmt": template["qfmt"], "afmt": template["afmt"]},
                "values": values,
            }
        )
    return cards


def build_home_cards(out):
    body = json.dumps(home_cards(out), ensure_ascii=False, indent=1)
    (out / "home-cards.js").write_text(
        "// Generated by scripts/build_site.py from examples/sheetcards-examples.xlsx\n"
        "// with the add-on's own card_layout.py. Do not edit.\n"
        f"export const CARDS = {body};\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# The documentation
# ---------------------------------------------------------------------------


def _doc_names():
    listed = [name for _, names in DOC_GROUPS for name in names]
    found = sorted(p.stem for p in DOCS.glob("*.md"))
    missing = sorted(set(listed) - set(found))
    unlisted = sorted(set(found) - set(listed))
    if missing or unlisted or len(listed) != len(set(listed)):
        sys.exit(
            "docs/site and DOC_GROUPS disagree:"
            + (f"\n  listed but no file: {missing}" if missing else "")
            + (f"\n  file but not listed: {unlisted}" if unlisted else "")
        )
    return listed


def _href(name):
    return "./" if name == "index" else f"{name}.html"


def _rewrite_links(text):
    """``columns.md#x`` → ``columns.html#x``: the Markdown links work on GitHub
    and in an editor, and the built pages link to each other."""

    def swap(match):
        name, anchor = match.group(1), match.group(2) or ""
        return f'href="{_href(name)}{anchor}"'

    return re.sub(r'href="([\w-]+)\.md(#[^"]*)?"', swap, text)


def _wrap_tables(text):
    """A table scrolls inside its own box, so the page never scrolls sideways."""
    return re.sub(
        r"(<table>.*?</table>)", r'<div class="tablewrap">\1</div>', text, flags=re.S
    )


def _nav(current, titles, toc):
    parts = []
    for group, names in DOC_GROUPS:
        parts.append(f'<p class="docnav-group">{html.escape(group)}</p><ul>')
        for name in names:
            here = ' aria-current="page"' if name == current else ""
            parts.append(
                f'<li><a href="{_href(name)}"{here}>{html.escape(titles[name])}</a>'
            )
            if name == current and toc:
                parts.append('<ul class="docnav-toc">')
                for entry in toc:
                    parts.append(
                        f'<li><a href="#{entry["id"]}">{entry["name"]}</a></li>'
                    )
                parts.append("</ul>")
            parts.append("</li>")
        parts.append("</ul>")
    return "\n".join(parts)


def _pager(names, index, titles):
    links = []
    if index > 0:
        prev = names[index - 1]
        links.append(
            f'<a class="prev" href="{_href(prev)}"><span data-icon="arrow-left">'
            f"</span><span><small>Previous</small>{html.escape(titles[prev])}</span></a>"
        )
    if index < len(names) - 1:
        nxt = names[index + 1]
        links.append(
            f'<a class="next" href="{_href(nxt)}"><span><small>Next</small>'
            f'{html.escape(titles[nxt])}</span><span data-icon="arrow-right"></span></a>'
        )
    return "\n".join(links)


def build_docs(out):
    """docs/site/*.md → out/docs/*.html, in the site's own chrome."""
    import markdown
    from markdown.extensions.toc import slugify_unicode

    names = _doc_names()
    template = (SITE / "_docs.html").read_text(encoding="utf-8")
    sources = {n: (DOCS / f"{n}.md").read_text(encoding="utf-8") for n in names}
    titles = {}
    for name, text in sources.items():
        heading = re.search(r"^# (.+)$", text, re.M)
        if not heading:
            sys.exit(f"docs/site/{name}.md has no '# Title' line")
        titles[name] = heading.group(1).strip()

    target = out / "docs"
    target.mkdir()
    for index, name in enumerate(names):
        md = markdown.Markdown(
            extensions=["tables", "fenced_code", "toc", "sane_lists"],
            extension_configs={
                "toc": {
                    "slugify": slugify_unicode,
                    "permalink": "#",
                    "permalink_class": "headerlink",
                    "permalink_title": "Link to this section",
                    "toc_depth": "2",
                }
            },
        )
        body = _wrap_tables(_rewrite_links(md.convert(sources[name])))
        toc = md.toc_tokens[0]["children"] if md.toc_tokens else []
        first = re.search(r"<p>(.*?)</p>", body, re.S)
        summary = re.sub(r"<[^>]+>", "", first.group(1)) if first else ""
        summary = " ".join(summary.split())[:200]
        page = (
            template.replace("%%TITLE%%", html.escape(titles[name]))
            .replace("%%DESCRIPTION%%", html.escape(summary))
            .replace("%%LANG%%", "vi" if name in VI_DOCS else "en")
            .replace("%%NAV%%", _nav(name, titles, toc))
            .replace("%%PAGER%%", _pager(names, index, titles))
            .replace("%%SOURCE%%", f"docs/site/{name}.md")
            .replace("%%BODY%%", body)
        )
        (target / f"{name}.html").write_text(page, encoding="utf-8")
    return len(names)


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
