"""Create sheet's templates: what they write, what they say, and the file they make.

``scripts/build_site.py`` declares the templates (Basic in two languages, the
vocabulary template for every language × read-aloud choice, and Custom) and
refuses to build if one warns or has an empty front; this runs that same check
and adds the two rules a build cannot see for itself:

* a spoken column names an iPhone voice only where a real iPhone has one — the
  dump in ``tests/test_card_layout_voices.py`` is the evidence, and it has no
  Japanese, Korean, French or Spanish voice, so those name none;
* the .csv the page hands out (``asCsv`` in ``site/sharelink.js``, the one CSV
  writer on the site) reads back through the add-on's own readers into the same
  deck, with nothing lost and nothing warned.
"""

import importlib.util
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")

pytestmark = pytest.mark.unit

# The voices the iPhone dump lists for each language a template speaks.
VERIFIED = {
    "en_US": "Apple_Samantha",
    "en_GB": "Apple_Daniel",
    "zh_CN": "Apple_Tingting",
    "de_DE": "Apple_Anna",
    "vi_VN": "Apple_Linh",
}


def _builder():
    spec = importlib.util.spec_from_file_location(
        "build_site", REPO / "scripts" / "build_site.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    build = _builder()
    out = tmp_path_factory.mktemp("site")
    pkg = out / "sc"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    for name in build.modules_the_site_loads():
        shutil.copy2(REPO / "src" / f"{name}.py", pkg / f"{name}.py")
    # sheet_templates() exits on a warning or an empty front, for every variant.
    templates = {tpl["id"]: tpl for tpl in build.sheet_templates(out)}
    return build, out, templates


def _all_rows(templates):
    """Every grid a template can produce, by a name for the failure message."""
    yield from (
        (f"basic {lang}", v["rows"])
        for lang, v in templates["basic"]["variants"].items()
    )
    yield from (
        (f"vocab {key}", v["rows"]) for key, v in templates["vocab"]["variants"].items()
    )
    yield "custom", templates["custom"]["rows"]
    for tid, tpl in templates.items():
        if tpl.get("more"):
            yield from (
                (f"{tid} {key}", v["rows"]) for key, v in tpl["variants"].items()
            )


def _all_cards(templates):
    yield from (v["card"] for v in templates["basic"]["variants"].values())
    yield templates["custom"]["card"]
    for tpl in templates.values():
        if "toggles" in tpl:
            yield from (v["card"] for v in tpl["variants"].values())


def _sheet_config():
    spec = importlib.util.spec_from_file_location(
        "sheet_config_for_templates", REPO / "src" / "sheet_config.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_main_templates_then_the_others(built):
    _, _, templates = built
    main = [tid for tid, tpl in templates.items() if not tpl.get("more")]
    assert main == ["basic", "vocab", "hanzi", "kanji", "custom"]
    more = [tid for tid, tpl in templates.items() if tpl.get("more")]
    # A theme is a choice in the step, never a template of its own.
    assert more == ["picture", "reverse", "typed"]


def test_every_listed_theme_can_dress_a_template_and_no_other(built):
    """The step swaps a card's colour block for the chosen theme's, so each block
    must be exactly what card_layout writes — present, verbatim, in the cards."""
    build, out, _ = built
    palettes = build.theme_palettes(out)
    themes = _sheet_config().listed_themes()
    assert "ptrang" not in themes
    assert list(palettes) == ["", *themes]
    assert len(set(palettes.values())) == len(palettes)
    # Each block is, verbatim, the one a template in that theme was built with:
    # the unthemed vocabulary card holds the default, the custom one sakura's.
    _, _, templates = built
    vocab = next(iter(templates["vocab"]["variants"].values()))["card"]
    assert palettes[""] in vocab["template"]["qfmt"]
    assert palettes["sakura"] in templates["custom"]["card"]["template"]["qfmt"]


def test_chinese_writing_and_japanese_furigana_are_offered(built):
    _, _, templates = built
    hanzi = templates["hanzi"]["rows"]
    assert any("draw" in cell for cell in hanzi[1])
    assert any("zh_CN" in cell for cell in hanzi[1])
    kanji = templates["kanji"]["rows"]
    assert any("furigana" in cell for cell in kanji[1])
    assert all("[" in row[1] for row in kanji[2:])


def test_the_english_page_gets_the_written_templates_in_english(built):
    _, _, templates = built
    for tid in ("hanzi", "kanji"):
        vi, en = templates[tid]["rows"], templates[tid]["en"]["rows"]
        assert en[0] == vi[0] and len(en) == len(vi)
        assert en[2:] != vi[2:]
        assert templates[tid]["en"]["card"]
    assert "label=Write the character for" in templates["hanzi"]["en"]["rows"][1][1]


def test_ptrang_is_never_offered(built):
    build, out, _ = built
    site = build.build(out / "whole")
    offenders = [
        str(path.relative_to(site))
        for path in site.rglob("*")
        if path.is_file()
        and path.suffix in {".js", ".html", ".css", ".json", ".py"}
        and "ptrang" in path.read_text(encoding="utf-8", errors="ignore")
    ]
    # The add-on's own module has to define it: a sheet naming it still works.
    assert offenders == ["sc/sheet_config.py"], offenders


def test_the_other_templates_keep_the_main_column_names(built):
    _, _, templates = built
    vocab = ["ID", "Word", "Phiên âm", "Meaning", "Example", "Note"]
    for key, v in templates["typed"]["variants"].items():
        assert v["rows"][0] == vocab, key
        assert "type=nc" in v["rows"][1][1] and "side=front" in v["rows"][1][3]
    for key, v in templates["reverse"]["variants"].items():
        assert v["rows"][0] == vocab[:4], key
        assert v["rows"][1][0] == "#config reverse"
        assert "reverse" in v["card"], key
    for key, v in templates["picture"]["variants"].items():
        assert v["rows"][0] == ["ID", "Word", "Picture", "Meaning"], key
        assert "image" in v["rows"][1][2]
        assert all(
            row[2].startswith("https://upload.wikimedia.org/") for row in v["rows"][2:]
        )


def test_the_pictures_are_the_example_workbooks(built):
    build, _, _ = built
    examples = (REPO / "scripts" / "build_examples.py").read_text(encoding="utf-8")
    for url in build.PICTURES:
        assert url.split("/thumb/", 1)[1] in examples, url


def test_basic_is_named_in_the_page_language(built):
    _, _, templates = built
    variants = templates["basic"]["variants"]
    assert variants["vi"]["rows"][0] == ["ID", "Mặt trước", "Mặt sau"]
    assert variants["en"]["rows"][0] == ["ID", "Front", "Back"]


def test_every_vocab_choice_is_built(built):
    build, _, templates = built
    variants = templates["vocab"]["variants"]
    codes = [lang[0] for lang in build.VOCAB_LANGUAGES]
    assert len(variants) == 4 * len(codes)
    for code in codes:
        for choice in ("11", "10", "01", "00"):
            rows = variants[f"{code}|{choice}"]["rows"]
            assert rows[0] == ["ID", "Word", "Phiên âm", "Meaning", "Example", "Note"]
            word, example = rows[1][1], rows[1][4]
            assert ("tts=" in word) == (choice[0] == "1"), (code, choice)
            assert ("tts=" in example) == (choice[1] == "1"), (code, choice)
            assert len(rows) == 5, f"{code} should carry three words"


def test_the_verified_voices_are_on_the_iphone_dump():
    text = (REPO / "tests" / "test_card_layout_voices.py").read_text(encoding="utf-8")
    dump = text.split('IPHONE = """', 1)[1].split('"""', 1)[0]
    found = set(re.findall(r"\{\{tts (\S+) voices=([^:]+):", dump))
    for code, voice in VERIFIED.items():
        assert (code.replace("_", "-"), voice) in found, (code, voice)


def test_a_spoken_column_names_only_a_verified_voice(built):
    _, _, templates = built
    for name, rows in _all_rows(templates):
        for cell in rows[1]:
            pairs = dict(
                part.strip().split("=", 1)
                for part in cell.split(";")
                if "=" in part and not part.strip().startswith("#")
            )
            if "tts" not in pairs:
                assert "voices" not in pairs, (name, cell)
                continue
            expected = VERIFIED.get(pairs["tts"])
            assert pairs.get("voices") == expected, (name, cell)


def test_every_template_card_has_a_front(built):
    _, _, templates = built
    for card in _all_cards(templates):
        assert card["template"]["qfmt"].strip()
        # The picture of a card leaves out the device's voice list.
        assert "sc-tts-debug" not in card["template"]["afmt"]


def test_custom_shows_off_the_settings_row(built):
    _, _, templates = built
    rows = templates["custom"]["rows"]
    text = " ".join(rows[1])
    for key in ("tts=", "voices=", "size=", "bold", "color=", "side=back", "hint"):
        assert key in text, key
    for key in ("label=", "type", "image", "theme="):
        assert key in text, key
    assert "SUBDECK 1" in rows[0] and "TAGS" in rows[0]


def _trimmed(grid):
    out = []
    for row in grid:
        row = list(row)
        while row and not row[-1]:
            row.pop()
        out.append(row)
    return out


@pytest.mark.skipif(NODE is None, reason="node is not installed")
def test_the_csv_reads_back_as_the_same_deck(built):
    build, out, templates = built
    tm, _card_layout, workbook = build._pure_package(out)
    grids = [
        # What exportGrid writes: the blank word Basic opens on is not written.
        (name, rows[:2] + [row for row in rows[2:] if any(c.strip() for c in row[1:])])
        for name, rows in _all_rows(templates)
    ]
    # The grids go in on stdin, not in the script: every variant of every
    # template is well over Linux's 128 KB limit on one command-line argument,
    # which macOS does not have, so the suite passed locally and failed on CI.
    script = (
        "let input = '';"
        "process.stdin.on('data', (c) => (input += c));"
        "process.stdin.on('end', () => "
        f"import({json.dumps((REPO / 'site' / 'sharelink.js').as_uri())}).then((m) => "
        "process.stdout.write(JSON.stringify(JSON.parse(input)"
        ".map((rows) => m.asCsv(rows))))));"
    )
    done = subprocess.run(
        [NODE, "--no-warnings", "-e", script],
        input=json.dumps([g for _, g in grids]),
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    for (name, rows), csv_text in zip(grids, json.loads(done.stdout), strict=True):
        assert csv_text.startswith("﻿"), name
        assert "\r\n" in csv_text, name
        read = json.loads(workbook.read_upload(csv_text.encode("utf-8"), "t.csv"))
        parsed = tm.parse_tsv_data(read["tsv"], [])
        # A trailing empty cell is no cell to a spreadsheet, nor to the reader.
        assert _trimmed([parsed["headers"], *parsed["rows"]]) == _trimmed(rows), name
        deck = tm.build_remote_deck_from_tsv(parsed, "", [])
        assert not deck.sheet_config.warnings, (name, deck.sheet_config.warnings)
        assert deck.sheet_config.present, name


def test_no_template_names_a_flashcard_set(built):
    """A template is not a set: each sheet made from one is asked for its own
    name, since two sheets with one ``name=`` are one deck in Anki."""
    _, _, templates = built
    for label, rows in _all_rows(templates):
        marker = rows[1][0].lower() if len(rows) > 1 else ""
        assert "name=" not in marker and "next=" not in marker, label
