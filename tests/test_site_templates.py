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


def test_there_are_three_templates(built):
    _, _, templates = built
    assert list(templates) == ["basic", "vocab", "custom"]


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
    cards = [v["card"] for v in templates["basic"]["variants"].values()]
    cards += [v["card"] for v in templates["vocab"]["variants"].values()]
    cards.append(templates["custom"]["card"])
    for card in cards:
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
    script = (
        f"import({json.dumps((REPO / 'site' / 'sharelink.js').as_uri())}).then((m) => "
        f"process.stdout.write(JSON.stringify({json.dumps([g for _, g in grids])}"
        ".map((rows) => m.asCsv(rows)))))"
    )
    done = subprocess.run(
        [NODE, "--no-warnings", "-e", script],
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
