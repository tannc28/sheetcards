"""The preview site's two languages have to stay in step.

A missing translation degrades quietly — `t()` falls back to English, so half a
page turns back into English and nobody notices until a user mentions it. A typo
in a key is worse: `t("rowsLegned")` renders the key itself on screen. Both are
caught here rather than in front of someone.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SITE = REPO / "site"

LANGUAGES = ("en", "vi")


def _entries():
    """(key, body) for every entry in STRINGS, one-line or many.

    Brace counting rather than a regex: entries hold quoted braces of their own
    (`{{c1::…}}` appears in several strings), so "up to the next `}`" is wrong and
    "up to a `},` at this indent" misses the single-line ones.
    """
    source = (SITE / "i18n.js").read_text(encoding="utf-8")
    body = source.split("const STRINGS = {", 1)[1]

    for match in re.finditer(r"^  (\w+): \{", body, re.M):
        depth, index = 0, match.end() - 1
        while index < len(body):
            if body[index] == "{":
                depth += 1
            elif body[index] == "}":
                depth -= 1
                if depth == 0:
                    break
            index += 1
        yield match.group(1), body[match.end() : index]


def _dictionary():
    """Every key declared in i18n.js, with the languages it defines."""
    return {
        name: {lang for lang in LANGUAGES if re.search(rf"\b{lang}:", entry)}
        for name, entry in _entries()
    }


def _page_source():
    """Every page and every module, found rather than listed.

    Named one by one, this list forgot the guide the day the guide was added, and
    the failure was fourteen strings looking like dead weight.
    """
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(SITE.iterdir())
        if path.suffix in (".js", ".html")
    )


def _keys_called():
    """Keys named directly at a call site — the ones a typo can break.

    Deliberately strict: this drives the does-it-exist test, so it must not be
    able to invent a key that is really a fragment or a variable.
    """
    text = _page_source()
    called = set(re.findall(r'\bt\("([\w]+)"', text))
    called |= set(re.findall(r'data-i18n="([\w]+)"', text))
    for group in re.findall(r'data-i18n-attr="([^"]+)"', text):
        called |= {pair.split(":")[1].strip() for pair in group.split(",")}
    # tabBar() composes t("tab" + Front|Both|Back|…), so the "tab" the regex
    # catches is half a name rather than one.
    called.discard("tab")
    return called | _tab_keys()


def _tab_keys():
    """The keys a tab bar builds, read off every ``CARD_TABS`` in the site.

    Spelled out by hand this was a list that could only go stale: adding a tab
    left its string looking like dead weight, and the failure named the new key
    rather than the test that had not kept up. Every module is searched because
    two pages show tabs now, and a page whose list nothing reads is a page whose
    strings look unused.
    """
    found = set()
    for path in sorted(SITE.glob("*.js")):
        for listed in re.findall(
            r"const CARD_TABS = \[(.*?)\]", path.read_text(encoding="utf-8"), re.S
        ):
            for name in listed.split(","):
                name = name.strip().strip("\"'")
                if name:
                    found.add(f"tab{name[:1].upper()}{name[1:]}")
    assert found, "no site module declares CARD_TABS"
    return found


def _keys_referenced(declared):
    """Keys mentioned anywhere, however indirectly.

    Deliberately loose: this drives the dead-weight test, and a key reached
    through a table (`["statRows", n]`) or a ternary is still very much in use.
    """
    quoted = set(re.findall(r'["\'`]([\w]+)["\'`]', _page_source()))
    # The landing page's demo labels are named beside the rows they label, in
    # HOME_EXAMPLES in the build script, and reach the page through the cards
    # it generates.
    build = (REPO / "scripts" / "build_site.py").read_text(encoding="utf-8")
    examples = build.split("HOME_EXAMPLES = [", 1)[1].split("\n]", 1)[0]
    quoted |= set(re.findall(r'"(\w+)"', examples))
    return (quoted & declared) | _keys_called()


@pytest.mark.unit
def test_every_string_has_both_languages():
    missing = {
        key: sorted(set(LANGUAGES) - langs)
        for key, langs in _dictionary().items()
        if set(LANGUAGES) - langs
    }
    assert not missing, (
        "site/i18n.js has entries that would silently fall back to English:\n  "
        + "\n  ".join(
            f"{key}: missing {', '.join(langs)}" for key, langs in missing.items()
        )
    )


@pytest.mark.unit
def test_the_page_asks_for_keys_that_exist():
    """A typo renders the key itself on screen, which no test would otherwise see."""
    declared = set(_dictionary())
    unknown = sorted(_keys_called() - declared)
    assert (
        not unknown
    ), f"site/app.js calls t() with keys i18n.js does not define: {unknown}"


@pytest.mark.unit
def test_the_dictionary_carries_no_dead_weight():
    declared = set(_dictionary())
    unused = sorted(declared - _keys_referenced(declared))
    assert not unused, f"site/i18n.js declares strings nothing uses: {unused}"


@pytest.mark.unit
def test_placeholder_arity_matches_between_languages():
    """A translation that takes fewer arguments drops information silently."""
    mismatched = []
    for name, entry in _entries():
        arities = {}
        for lang in LANGUAGES:
            fn = re.search(rf"\b{lang}: \(([^)]*)\) =>", entry)
            if fn:
                arities[lang] = len([a for a in fn.group(1).split(",") if a.strip()])
        if len(set(arities.values())) > 1:
            mismatched.append(f"{name}: {arities}")

    assert (
        not mismatched
    ), "translations disagree on how many values they take:\n  " + "\n  ".join(
        mismatched
    )


# The pages the static Vietnamese is baked into: what a reader sees before the
# page's script runs, and all a crawler or a link preview ever sees.
STATIC_PAGES = ("index.html", "sheet.html", "create.html", "_docs.html", "404.html")

_ELEMENT = re.compile(r'<(\w+)\b[^>]*\bdata-i18n="(\w+)"[^>]*>(.*?)</\1>', re.S)
_ATTR_TAG = re.compile(r'<\w+\b[^>]*\bdata-i18n-attr="([^"]+)"[^>]*>', re.S)


def _vietnamese():
    """``{key: vi}`` for every plain-string entry, evaluated by node.

    Evaluated rather than parsed: the strings are concatenations spread over
    several lines, and only JavaScript knows exactly what they add up to.
    """
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    script = (
        f"import({json.dumps((SITE / 'i18n.js').as_uri())}).then((m) => {{"
        "const o = {}; for (const [k, v] of Object.entries(m.STRINGS))"
        " if (typeof v.vi === 'string') o[k] = v.vi;"
        " process.stdout.write(JSON.stringify(o)); })"
    )
    out = subprocess.run(
        [node, "--no-warnings", "-e", script],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(out.stdout)


def _same(text):
    return " ".join(text.split())


@pytest.mark.unit
def test_static_vietnamese_matches_the_dictionary():
    """The text baked into the HTML is exactly ``STRINGS[key].vi``.

    Two copies of every sentence — one in i18n.js, one in the page — drift the
    moment one is edited, and the page then says one thing until its script runs
    and another thing after.
    """
    vi = _vietnamese()
    drift = []
    for name in STATIC_PAGES:
        text = (SITE / name).read_text(encoding="utf-8")
        for _tag, key, inner in _ELEMENT.findall(text):
            if key in vi and _same(inner) != _same(vi[key]):
                drift.append(f"{name} [{key}]: {_same(inner)!r} != {vi[key]!r}")
        for tag in _ATTR_TAG.finditer(text):
            for pair in tag.group(1).split(","):
                attr, key = (s.strip() for s in pair.split(":"))
                found = re.search(rf'\s{re.escape(attr)}="([^"]*)"', tag.group(0))
                if not found:
                    drift.append(f"{name} [{key}]: no static {attr}")
                elif _same(found.group(1)) != _same(vi[key]):
                    drift.append(
                        f"{name} [{key}] {attr}: {found.group(1)!r} != {vi[key]!r}"
                    )
    assert not drift, "static HTML disagrees with i18n.js:\n  " + "\n  ".join(drift)
