"""The example workbook has to keep working, and keep matching its sources.

``examples/sheetcards-examples.xlsx`` is not sample data sitting in a corner: it
is what the README, the add-on's *Import Test Deck* menu item and the preview
site's landing page all point at. Two things can rot without anyone noticing —
the committed workbook drifting away from the ``SHEETS`` it is generated from in
``scripts/build_examples.py``, and a sheet that stops parsing the way it is
documented to. Both are checked here.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

from src.card_layout import build_templates
from src.card_layout import split_sides
from src.sheet_config import SheetConfig
from src.tsv_model import build_remote_deck_from_tsv
from src.tsv_model import parse_tsv_data
from src.workbook import sheet_names
from src.workbook import sheet_tsv

REPO = Path(__file__).resolve().parent.parent
EXAMPLES = REPO / "examples"
WORKBOOK = EXAMPLES / "sheetcards-examples.xlsx"

# The address the docs, the add-on and the site all hand people. It is spelled
# out here rather than imported so that renaming the file cannot quietly rename
# it in three places and leave every published link pointing at nothing.
PUBLISHED_URL = (
    "https://github.com/tannc28/sheetcards/blob/main/examples/"
    "sheetcards-examples.xlsx"
)


def builder():
    """``scripts/build_examples.py``, loaded by path — scripts/ is not a package."""
    spec = importlib.util.spec_from_file_location(
        "build_examples", REPO / "scripts" / "build_examples.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["build_examples"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def workbook_bytes():
    return WORKBOOK.read_bytes()


@pytest.fixture(scope="module")
def sheets(workbook_bytes):
    """Every sheet as ``(name, RemoteDeck)``, read the way the add-on reads it."""
    return [
        (
            name,
            build_remote_deck_from_tsv(
                parse_tsv_data(sheet_tsv(workbook_bytes, name)), name
            ),
        )
        for name in sheet_names(workbook_bytes)
    ]


@pytest.mark.unit
def test_workbook_matches_its_source():
    """The committed file is what ``SHEETS`` builds to.

    Rebuilding is a two-word command, so the failure worth catching is not a
    missing rebuild — it is an edited grid shipped with the old workbook, which
    would make the documentation describe one sheet and the link serve another.
    """
    data, _ = builder().build_bytes()
    assert WORKBOOK.exists(), "run python scripts/build_examples.py"
    assert data == WORKBOOK.read_bytes(), (
        "examples/sheetcards-examples.xlsx is out of date — "
        "run python scripts/build_examples.py"
    )


@pytest.mark.unit
def test_the_workbook_is_the_only_file_people_need(workbook_bytes):
    """One file, many sheets — not a folder of them."""
    assert sorted(p.name for p in EXAMPLES.iterdir()) == [
        "README.md",
        "sheetcards-examples.xlsx",
    ]
    assert sheet_names(workbook_bytes) == list(builder().SHEETS)
    assert len(sheet_names(workbook_bytes)) >= 15


@pytest.mark.unit
def test_every_sheet_has_an_id_column(sheets):
    """A sheet with no ID column is skipped by the add-on, so none of these may be."""
    for name, deck in sheets:
        assert deck.plan.has_id, f"{name} has no ID column"


@pytest.mark.unit
def test_every_sheet_produces_notes(sheets):
    for name, deck in sheets:
        stats = deck.get_statistics()
        assert stats["sync_marked_lines"] > 0, f"{name} syncs nothing"


@pytest.mark.unit
def test_no_sheet_warns(sheets):
    """A sheet with a warning in it is teaching the wrong thing.

    There used to be one sheet exempt from this, wrong on purpose so that every
    ``SheetConfig.warnings`` message had something to point at. It was the last
    tab in the workbook, which made the tour end on a card that does not work,
    and the warnings themselves are covered by ``tests/test_sheet_config.py``
    without needing a deck to be broken for them.
    """
    for name, deck in sheets:
        warnings = deck.sheet_config.warnings if deck.sheet_config else []
        assert not warnings, f"{name} warns: {warnings}"


@pytest.mark.unit
def test_every_sheet_renders_a_card(sheets):
    """A front that renders nothing means Anki generates no card at all."""
    for name, deck in sheets:
        config = deck.sheet_config or SheetConfig()
        front, _ = split_sides(deck.plan, config)
        assert front, f"{name} has an empty front"
        templates = build_templates(
            deck.plan, config, is_cloze=bool(config.cloze_field)
        )
        for template in templates:
            assert template["qfmt"].strip(), f"{name}: empty qfmt"
            assert template["afmt"].strip(), f"{name}: empty afmt"


@pytest.mark.unit
def test_the_tour_covers_every_directive(sheets):
    """Every settings-row key has to be demonstrated somewhere in the workbook.

    This is the check that makes the examples a contract rather than a snapshot:
    a directive added to ``sheet_config`` without an example here fails the suite,
    which is the only moment anyone is looking.
    """
    from src.sheet_config import MEDIA_KINDS

    used = set()
    for name, deck in sheets:
        config = deck.sheet_config
        if not config:
            continue
        if config.align:
            used.add("deck align")
        if config.speed is not None:
            used.add("deck speed")
        if config.reverse:
            used.add("deck reverse")
        if config.theme:
            used.add("deck theme")
        if config.cloze_field:
            used.add("cloze")
        if config.type_field:
            used.add("type")
        for field in config.fields.values():
            for key in ("side", "size", "color", "align", "tts", "label"):
                if getattr(field, key):
                    used.add(key)
            for flag in ("bold", "italic", "hint", "furigana", "draw"):
                if getattr(field, flag):
                    used.add(flag)
            if field.voices:
                used.add("voices")
            if field.speed is not None:
                used.add("speed")
            if field.media:
                used.add(field.media)
            if field.subdeck:
                used.add("subdeck")

    expected = {
        "deck align",
        "deck speed",
        "deck reverse",
        "deck theme",
        "side",
        "size",
        "color",
        "align",
        "tts",
        "voices",
        "speed",
        "label",
        "bold",
        "italic",
        "hint",
        "furigana",
        "cloze",
        "type",
        "draw",
        "subdeck",
        *MEDIA_KINDS,
    }
    assert expected - used == set(), f"no example uses: {sorted(expected - used)}"


@pytest.mark.unit
def test_the_reserved_columns_are_all_demonstrated(sheets):
    roles = {"sync": False, "tags": False, "subdeck3": False, "subdeck1": False}
    for _, deck in sheets:
        roles["sync"] |= deck.plan.sync_header is not None
        roles["tags"] |= deck.plan.tags_header is not None
        roles["subdeck1"] |= len(deck.plan.subdeck_headers) >= 1
        roles["subdeck3"] |= len(deck.plan.subdeck_headers) >= 3
    assert all(roles.values()), f"not demonstrated: {roles}"


@pytest.mark.unit
def test_the_addon_and_the_site_point_at_this_workbook():
    """The published link is one file — three copies of it must agree."""
    from src.templates_and_definitions import TEST_SHEETS_URLS

    assert [url for _, url in TEST_SHEETS_URLS] == [PUBLISHED_URL]

    app = (REPO / "site" / "app.js").read_text(encoding="utf-8")
    assert PUBLISHED_URL in app, "site/app.js does not load the example workbook"

    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert PUBLISHED_URL in readme, "README.md does not link the example workbook"


@pytest.mark.unit
def test_the_site_opens_on_a_sheet_that_exists(workbook_bytes):
    """``DEMO_TAB`` names a sheet by name, and a name can be renamed."""
    import re

    app = (REPO / "site" / "app.js").read_text(encoding="utf-8")
    match = re.search(r'const DEMO_TAB = "([^"]+)"', app)
    assert match, "site/app.js declares no DEMO_TAB"
    assert match.group(1) in sheet_names(workbook_bytes)


@pytest.mark.unit
def test_media_columns_hold_bare_urls(sheets):
    """A media cell is an address, not HTML — the element is built by the template."""
    for name, deck in sheets:
        config = deck.sheet_config
        if not config:
            continue
        media = [h for h, f in config.fields.items() if f.media]
        for note in deck.notes:
            for header in media:
                value = str(note.get(header, "")).strip()
                if not value:
                    continue
                assert value.startswith(
                    "https://"
                ), f"{name}: {header} holds {value!r}, not an https address"
                assert "<" not in value, f"{name}: {header} holds markup"
