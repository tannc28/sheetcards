"""The guide for AI assistants (``/ai.md``) and its pointer (``/llms.txt``).

``scripts/ai_guide.py`` generates both from ``sheet_config`` and Create sheet's
templates. An assistant copies what the guide shows, so every sample in it has
to be a file Sheet to Anki opens without a warning — read here the way an upload
is read, through the real ``workbook`` and ``tsv_model``.
"""

import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

pytestmark = pytest.mark.unit


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
    build.build_ai_guide(out)
    sys.path.insert(0, str(out))
    saved = {
        m: sys.modules.pop(m)
        for m in list(sys.modules)
        if m == "sc" or m.startswith("sc.")
    }
    try:
        from sc import card_layout
        from sc import sheet_config
        from sc import tsv_model
        from sc import workbook

        yield SimpleModules(out, sheet_config, tsv_model, card_layout, workbook)
    finally:
        sys.path.remove(str(out))
        for m in [m for m in sys.modules if m == "sc" or m.startswith("sc.")]:
            del sys.modules[m]
        sys.modules.update(saved)


class SimpleModules:
    def __init__(self, out, sheet_config, tsv_model, card_layout, workbook):
        self.out = out
        self.guide = (out / "ai.md").read_text(encoding="utf-8")
        self.sc, self.tm, self.cl, self.wb = (
            sheet_config,
            tsv_model,
            card_layout,
            workbook,
        )


def _blocks(text):
    return re.findall(r"```csv\n(.*?)```", text, re.S)


def test_the_guide_is_built_and_fits_the_budget(built):
    size = len(built.guide.encode("utf-8"))
    assert 4000 < size < 25 * 1024, size


def test_every_settings_key_is_in_the_guide(built):
    sc = built.sc
    keys = set(sc._FIELD_KEYS) | set(sc._DECK_KEYS) | set(sc._FLAGS)
    keys |= set(sc.MEDIA_KINDS) | set(sc.THEME_COLORS) | set(sc.FONTS)
    keys |= set(sc.listed_themes())
    missing = sorted(k for k in keys if f"`{k}`" not in built.guide)
    assert not missing, missing


def test_an_unlisted_theme_is_never_named(built):
    for name in built.sc.UNLISTED_THEMES:
        assert name not in built.guide
    assert "ptrang" not in built.guide
    assert "ptrang" not in (built.out / "llms.txt").read_text(encoding="utf-8")


def test_the_ranges_the_guide_states_are_the_parsers(built):
    """size 6-200, media/draw 1-2000, speed 0.5-2.0: each bound accepted, each
    step past it refused."""
    for text in ("6-200", "1-2000", "0.5-2.0"):
        assert text in built.guide

    def warns(cell):
        rows = [["ID", "Word"], ["#config", cell], ["w01", "x"]]
        parsed = built.tm.parse_tsv_data("\n".join("\t".join(r) for r in rows), [])
        return bool(
            built.tm.build_remote_deck_from_tsv(parsed, "", []).sheet_config.warnings
        )

    for good in (
        "size=6",
        "size=200",
        "image; size=1",
        "image; size=2000",
        "draw; size=2000",
        "tts=en_US; speed=0.5",
        "tts=en_US; speed=2",
    ):
        assert not warns(good), good
    for bad in (
        "size=5",
        "size=201",
        "image; size=2001",
        "speed=0.4",
        "speed=2.1",
        "tts=en",
    ):
        assert warns(bad), bad  # fmt: skip


def test_every_sample_csv_opens_without_a_warning(built):
    blocks = _blocks(built.guide)
    assert len(blocks) >= 15
    for text in blocks:
        upload = json.loads(built.wb.read_upload(text.encode("utf-8"), "ai.csv"))
        parsed = built.tm.parse_tsv_data(upload["tsv"], [])
        deck = built.tm.build_remote_deck_from_tsv(parsed, "", [])
        cfg = deck.sheet_config
        assert cfg.present, text
        assert not cfg.warnings, (cfg.warnings, text)
        assert cfg.deck_name, text
        assert parsed["headers"][0] == "ID", text
        assert len(deck.notes) == 2 and not deck.duplicate_ids, text
        front, _ = built.cl.split_sides(deck.plan, cfg)
        assert front, text
        for note in deck.notes:
            assert any(note.get(h) for h in front), text
        width = len(parsed["headers"])
        for row in upload["tsv"].splitlines():
            assert len(row.split("\t")) == width, row


def test_the_guide_covers_every_card_type_asked_for(built):
    text = built.guide
    for code in (
        "en_US",
        "zh_CN",
        "ja_JP",
        "ko_KR",
        "fr_FR",
        "de_DE",
        "es_ES",
        "vi_VN",
    ):
        assert f"tts={code}" in text, code
    for what in (
        "; draw",
        "furigana",
        "cloze",
        "type=nc",
        "; reverse",
        "image",
        "Special:FilePath/",
        "{{c1::",
    ):
        assert what in text, what  # fmt: skip
    for section in (
        "Role and goal",
        "Output contract",
        "IDs",
        "Quality rules",
        "Final checklist",
        "/create/",
        "/sheet/",
    ):
        assert section in text, section  # fmt: skip


def test_llms_txt_points_at_the_guide(built):
    text = (built.out / "llms.txt").read_text(encoding="utf-8")
    assert text.startswith("# SheetCards\n\n> ")
    assert "https://tannc28.github.io/sheetcards/ai.md" in text


def test_the_docs_page_exists_in_both_languages_and_names_the_guide():
    build = _builder()
    assert any("ai" in names for _, names in build.DOC_GROUPS)
    for folder in ("", "en"):
        page = (REPO / "docs" / "site" / folder / "ai.md").read_text(encoding="utf-8")
        assert "https://tannc28.github.io/sheetcards/ai.md" in page
