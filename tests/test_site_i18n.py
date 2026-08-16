"""The preview site's two languages have to stay in step.

A missing translation degrades quietly — `t()` falls back to English, so half a
page turns back into English and nobody notices until a user mentions it. A typo
in a key is worse: `t("rowsLegned")` renders the key itself on screen. Both are
caught here rather than in front of someone.
"""

import re
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
    """The keys tabBar() builds, read off ``CARD_TABS`` rather than listed here.

    Spelled out by hand this was a list that could only go stale: adding a tab
    left its string looking like dead weight, and the failure named the new key
    rather than the test that had not kept up.
    """
    text = (SITE / "app.js").read_text(encoding="utf-8")
    match = re.search(r"const CARD_TABS = \[(.*?)\]", text, re.S)
    assert match, "site/app.js declares no CARD_TABS"
    names = [name.strip().strip("\"'") for name in match.group(1).split(",")]
    return {f"tab{name[:1].upper()}{name[1:]}" for name in names if name}


def _keys_referenced(declared):
    """Keys mentioned anywhere, however indirectly.

    Deliberately loose: this drives the dead-weight test, and a key reached
    through a table (`["statRows", n]`) or a ternary is still very much in use.
    """
    quoted = set(re.findall(r'["\'`]([\w]+)["\'`]', _page_source()))
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
