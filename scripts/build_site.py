#!/usr/bin/env python3
"""Assembles the website into build/site/.

Four kinds of page: the landing page (``site/index.html``), Create deck
(``site/create.html``; ``site/preview.html`` is its old address, kept as a
redirect), the settings-row editor (``site/editor.html``) and the
documentation, written as Markdown under ``docs/site/`` (Vietnamese, served at
``/docs/``) and ``docs/site/en/`` (English, at ``/docs/en/``) and converted here.

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
import csv
import html
import io
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

# The file a learner downloads from the landing page to start from: one sheet,
# four columns, a settings row and three words — the smallest sheet that already
# makes a good card. Served beside the example workbook, which is copied in too,
# so both downloads are same-origin files rather than GitHub pages.
STARTER_NAME = "sheetcards-mau.xlsx"
STARTER = {
    "Vocabulary": [
        ["ID", "Word", "Meaning", "Example"],
        [
            "#config",
            "size=44; bold; tts=en_US",
            "side=back; size=22",
            "side=back; color=muted; italic; tts=en_US",
        ],
        ["w01", "hello", "xin chào", "Hello, how are you today?"],
        ["w02", "thank you", "cảm ơn", "Thank you for your help."],
        ["w03", "goodbye", "tạm biệt", "Goodbye, see you tomorrow."],
    ],
}

# The documentation's table of contents: ({language: group}, [page, ...]). A
# page is the name of a Markdown file, written once per language, and its title
# is that file's first heading. Declared here rather than found, because order is
# information — the build refuses a page missing from this list, or from either
# language, and a name with no file.
DOC_GROUPS = [
    ({"vi": "Bắt đầu", "en": "Start"}, ["index", "examples"]),
    (
        {"vi": "Viết sheet", "en": "Write a sheet"},
        ["columns", "settings-row", "card-types", "text", "media", "tts"],
    ),
    ({"vi": "Trong Anki", "en": "In Anki"}, ["menu", "syncing", "sources"]),
    ({"vi": "Trợ giúp", "en": "Help"}, ["faq", "developers"]),
]

# The docs in each language: the folder under docs/site/ it is written in, which
# is also the folder under /docs/ it is served from. Vietnamese is the docs'
# front door, because most readers are Vietnamese; every page links its twin.
DOC_LANGS = {"vi": "", "en": "en"}

# The words the docs' own chrome says around a page, per language.
DOC_CHROME = {
    "vi": {
        "nav": "Docs",
        "contents": "Mục lục",
        "onpage": "Trên trang này",
        "pages": "Các trang khác",
        "previous": "Trang trước",
        "next": "Trang sau",
        "permalink": "Link tới mục này",
        "edit": "Sửa trang này trên GitHub",
        "twin": "Read this page in English",
    },
    "en": {
        "nav": "Documentation",
        "contents": "Contents",
        "onpage": "On this page",
        "pages": "More pages",
        "previous": "Previous",
        "next": "Next",
        "permalink": "Link to this section",
        "edit": "Edit this page on GitHub",
        "twin": "Đọc trang này bằng tiếng Việt",
    },
}

# The landing page's demo: (sheet in the example workbook, row ID, i18n key of
# its label, theme). Real rows, rendered with the real templates — the page
# claims the sheet becomes this card, so it had better be the card the add-on
# makes. Each card wears a different theme to show there is more than one; the
# theme is written into the settings cell the strip shows, so the sheet on the
# left still says exactly what made the card on the right.
HOME_EXAMPLES = [
    ("15 Theme + subdeck (màu, tầng)", "n01", "demoEnglish", "paper"),
    ("13 Furigana (phiên âm kanji)", "f01", "demoJapanese", "sakura"),
    ("06 Cloze (điền chỗ trống)", "z01", "demoCloze", "matcha"),
]


# Create sheet's starting points: (id, source). A source is either a sheet
# of the example workbook, of which the header, the settings row and the first
# few words are taken, or a grid written out here when no sheet in the workbook
# is the right shape. The labels live in site/sheet.js beside the ids, so they
# are translated with the rest of the page.
SHEET_TEMPLATES = [
    (
        "blank",
        [["ID", "Front", "Back"], ["#config", "size=40", "size=24"], ["w01", "", ""]],
    ),
    (
        "english",
        # Word / IPA / Meaning / Example, spoken — the words come from the
        # workbook's card-layout sheet, the columns are the ones learners ask for.
        (
            "03 Card layout (bố cục thẻ)",
            ["Word", "Phonetic", "Meaning", "Example"],
            ["Word", "IPA", "Meaning", "Example"],
            [
                "#config",
                "size=44; bold; tts=en_US",
                "size=20; color=accent",
                "side=back; size=26",
                "side=back; size=16; color=muted; italic; tts=en_US",
            ],
        ),
    ),
    ("kanji", "13 Furigana (phiên âm kanji)"),
    ("cloze", "06 Cloze (điền chỗ trống)"),
]
# How many words of an example sheet a template keeps: enough to see the card,
# few enough that clearing them is not a chore.
TEMPLATE_ROWS = 3


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
    build_sheet_templates(out)
    build_downloads(out)
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


def build_downloads(out):
    """The two workbooks the landing page offers: the starter and the examples."""
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        import build_examples
    finally:
        sys.path.pop(0)
    data, _ = build_examples.build_bytes(STARTER)
    (out / STARTER_NAME).write_bytes(data)
    shutil.copy2(EXAMPLES, out / EXAMPLES.name)


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
    for sheet, row_id, label, theme in HOME_EXAMPLES:
        tsv = workbook.sheet_tsv(data, sheet)
        lines = tsv.split("\n")
        marker, _, rest = lines[1].partition("\t")
        if not marker.lower().startswith("#config"):
            sys.exit(f"home demo: {sheet!r} has no settings row to set a theme in")
        kept = [
            pair.strip()
            for pair in marker[len("#config") :].split(";")
            if pair.strip() and not pair.strip().lower().startswith("theme")
        ]
        marker = "#config " + "; ".join(kept + [f"theme={theme}"])
        lines[1] = marker + "\t" + rest
        parsed = tm.parse_tsv_data("\n".join(lines), [])
        deck = tm.build_remote_deck_from_tsv(parsed, "", [])
        plan, cfg = deck.plan, deck.sheet_config
        if cfg.theme != theme or cfg.warnings:
            sys.exit(f"home demo: {sheet!r} did not take theme={theme}: {cfg.warnings}")
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
# Create sheet's templates
# ---------------------------------------------------------------------------


def sheet_templates(out):
    """Each template as rows of text, checked by the add-on's own parser.

    A template is the first thing somebody writes into, so it must not open with
    a warning: every one is parsed here, and the build stops on a warning or an
    empty front rather than shipping a starting point that is already wrong.
    """
    tm, card_layout, workbook = _pure_package(out)
    data = EXAMPLES.read_bytes()
    built = []
    for template_id, source in SHEET_TEMPLATES:
        if isinstance(source, list):
            rows = [list(row) for row in source]
        else:
            if isinstance(source, str):
                sheet, pick, rename, config = source, None, None, None
            else:
                sheet, pick, rename, config = source
            grid = workbook.sheet_tsv(data, sheet)
            table = list(csv.reader(io.StringIO(grid), delimiter="\t"))
            if pick:
                at = [table[0].index(name) for name in pick]
                table = [[row[0]] + [row[i] for i in at] for row in table]
                table[0] = ["ID"] + rename
                table[1] = config
                for n, row in enumerate(table[2:], start=1):
                    row[0] = f"w{n:02}"
            rows = table[: 2 + TEMPLATE_ROWS]
        parsed = tm.parse_tsv_data("\n".join("\t".join(row) for row in rows), [])
        deck = tm.build_remote_deck_from_tsv(parsed, "", [])
        cfg = deck.sheet_config
        if cfg.warnings:
            sys.exit(f"template {template_id!r} warns: {cfg.warnings}")
        front, _ = card_layout.split_sides(deck.plan, cfg)
        if not front:
            sys.exit(f"template {template_id!r} has nothing on the front")
        built.append({"id": template_id, "rows": rows})
    return built


def build_sheet_templates(out):
    body = json.dumps(sheet_templates(out), ensure_ascii=False, indent=1)
    (out / "sheet-templates.js").write_text(
        "// Generated by scripts/build_site.py from examples/sheetcards-examples.xlsx\n"
        "// and SHEET_TEMPLATES. Do not edit.\n"
        f"export const TEMPLATES = {body};\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# The documentation
# ---------------------------------------------------------------------------


def _doc_names(lang):
    folder = DOCS / DOC_LANGS[lang]
    listed = [name for _, names in DOC_GROUPS for name in names]
    found = sorted(p.stem for p in folder.glob("*.md"))
    missing = sorted(set(listed) - set(found))
    unlisted = sorted(set(found) - set(listed))
    if missing or unlisted or len(listed) != len(set(listed)):
        sys.exit(
            f"{folder.relative_to(REPO)} and DOC_GROUPS disagree:"
            + (f"\n  listed but no file: {missing}" if missing else "")
            + (f"\n  file but not listed: {unlisted}" if unlisted else "")
        )
    return listed


def _slug_vi(value, separator):
    """An ASCII anchor for a Vietnamese heading: ``Đặt tên deck`` → ``dat-ten-deck``.

    The toc extension's ``slugify`` already drops the tone marks, but ``đ`` has no
    decomposition and would vanish (``at-ten-deck``); a heading in no Latin script
    at all falls back to keeping its own letters.
    """
    from markdown.extensions.toc import slugify
    from markdown.extensions.toc import slugify_unicode

    ascii_value = value.replace("đ", "d").replace("Đ", "D")
    return slugify(ascii_value, separator) or slugify_unicode(value, separator)


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


def _nav(current, titles, toc, lang):
    parts = []
    for group, names in DOC_GROUPS:
        parts.append(f'<p class="docnav-group">{html.escape(group[lang])}</p><ul>')
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


def _onpage(toc, words):
    """The page's own headings, for the third column a very wide screen has room
    for; narrower, the same list sits under the page's name in the sidebar."""
    if not toc:
        return ""
    items = "".join(f'<li><a href="#{e["id"]}">{e["name"]}</a></li>' for e in toc)
    return (
        f'<aside class="onpage" aria-label="{html.escape(words["onpage"])}">'
        f'<p class="docnav-group">{html.escape(words["onpage"])}</p><ul>{items}</ul></aside>'
    )


def _pager(names, index, titles, words):
    links = []
    if index > 0:
        prev = names[index - 1]
        links.append(
            f'<a class="prev" href="{_href(prev)}"><span data-icon="arrow-left">'
            f"</span><span><small>{words['previous']}</small>{html.escape(titles[prev])}</span></a>"
        )
    if index < len(names) - 1:
        nxt = names[index + 1]
        links.append(
            f'<a class="next" href="{_href(nxt)}"><span><small>{words["next"]}</small>'
            f'{html.escape(titles[nxt])}</span><span data-icon="arrow-right"></span></a>'
        )
    return "\n".join(links)


def build_docs(out):
    """docs/site/**.md → out/docs/**.html, one tree per language."""
    template = (SITE / "_docs.html").read_text(encoding="utf-8")
    return sum(build_docs_in(out, lang, template) for lang in DOC_LANGS)


def build_docs_in(out, lang, template):
    import markdown
    from markdown.extensions.toc import slugify_unicode

    folder = DOC_LANGS[lang]
    words = DOC_CHROME[lang]
    names = _doc_names(lang)
    source_dir = DOCS / folder
    sources = {n: (source_dir / f"{n}.md").read_text(encoding="utf-8") for n in names}
    titles = {}
    for name, text in sources.items():
        heading = re.search(r"^# (.+)$", text, re.M)
        if not heading:
            sys.exit(f"{source_dir.relative_to(REPO)}/{name}.md has no '# Title' line")
        titles[name] = heading.group(1).strip()

    # The other language's copy of a page: Vietnamese sits at /docs/, English
    # one folder down at /docs/en/.
    (twin_lang,) = set(DOC_LANGS) - {lang}
    up = "../" if folder else ""
    root = "../" + up
    target = out / "docs" / folder
    target.mkdir(parents=True, exist_ok=True)
    for index, name in enumerate(names):
        md = markdown.Markdown(
            extensions=["tables", "fenced_code", "toc", "sane_lists"],
            extension_configs={
                "toc": {
                    "slugify": _slug_vi if lang == "vi" else slugify_unicode,
                    "permalink": "#",
                    "permalink_class": "headerlink",
                    "permalink_title": words["permalink"],
                    "toc_depth": "2",
                }
            },
        )
        body = _wrap_tables(_rewrite_links(md.convert(sources[name])))
        toc = md.toc_tokens[0]["children"] if md.toc_tokens else []
        first = re.search(r"<p>(.*?)</p>", body, re.S)
        summary = re.sub(r"<[^>]+>", "", first.group(1)) if first else ""
        summary = " ".join(summary.split())[:200]
        twin = up + (DOC_LANGS[twin_lang] + "/" if DOC_LANGS[twin_lang] else "")
        twin = (twin or "./") if name == "index" else twin + f"{name}.html"
        source = "/".join(p for p in ("docs/site", folder, f"{name}.md") if p)
        page = (
            template.replace("%%TITLE%%", html.escape(titles[name]))
            .replace("%%DESCRIPTION%%", html.escape(summary))
            .replace("%%LANG%%", lang)
            .replace("%%ROOT%%", root)
            .replace("%%TWIN_LANG%%", twin_lang)
            .replace("%%TWIN%%", twin)
            .replace("%%TWIN_TEXT%%", words["twin"])
            .replace("%%W_NAV%%", words["nav"])
            .replace("%%W_CONTENTS%%", words["contents"])
            .replace("%%W_PAGES%%", words["pages"])
            .replace("%%W_EDIT%%", words["edit"])
            .replace("%%NAV%%", _nav(name, titles, toc, lang))
            .replace("%%ONPAGE%%", _onpage(toc, words))
            .replace("%%PAGER%%", _pager(names, index, titles, words))
            .replace("%%SOURCE%%", source)
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
