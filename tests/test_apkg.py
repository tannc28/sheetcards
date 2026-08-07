"""The `.apkg` a sheet turns into, and the promises that file makes.

Two of these run a *real* Anki in a subprocess. The suite mocks `anki` for every
other module, so a package that is subtly malformed would sail through a
mock-based test and fail only in front of someone with a phone — and the whole
point of this format is that it reaches a phone without a desktop in between.
"""

import io
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest

from src.apkg import build_package
from src.apkg import cloze_ordinals
from src.apkg import note_guid
from src.column_model import plan_columns
from src.sheet_config import SheetConfig
from src.sheet_config import parse_config_row
from src.tsv_model import build_remote_deck_from_tsv
from src.tsv_model import parse_tsv_data

REPO = Path(__file__).resolve().parent.parent

BASIC = (
    "ID\tSYNC\tSUBDECK 1\tTAGS\tWord\tMeaning\n"
    "1\tTRUE\tUnit 1\thsk4\t熟悉\tfamiliar\n"
    "2\tTRUE\tUnit 1\t\t复杂\tcomplicated\n"
    "3\tFALSE\tUnit 2\t\t危险\tdangerous\n"
)

CLOZE = (
    "ID\tWord\tSentence\n"
    "#config\t\tcloze\n"
    "1\t熟悉\t我对这里{{c1::很熟悉}}，也{{c2::常来}}。\n"
    "2\t推迟\t会议{{c1::推迟}}到明天。\n"
)


def _package(tsv, sheet="SHEET", deck="HSK4", now=1786000000):
    remote = build_remote_deck_from_tsv(parse_tsv_data(tsv), "url")
    return build_package(
        sheet, deck, remote.plan, remote.sheet_config, remote.notes, now=now
    )


def _collection(data):
    """The `col` row and the note/card rows, read back out of the package."""
    import sqlite3

    with tempfile.TemporaryDirectory() as folder:
        path = os.path.join(folder, "p.apkg")
        Path(path).write_bytes(data)
        with zipfile.ZipFile(path) as package:
            inner = os.path.join(folder, "collection.anki2")
            Path(inner).write_bytes(package.read("collection.anki2"))
        db = sqlite3.connect(inner)
        col = db.execute("select ver, models, decks, tags from col").fetchone()
        notes = db.execute("select guid, flds, tags, sfld from notes").fetchall()
        cards = db.execute("select nid, did, ord from cards").fetchall()
        db.close()
    return col, notes, cards


@pytest.mark.unit
class TestPackageShape:
    def test_it_is_a_zip_anki_recognises(self):
        with zipfile.ZipFile(io.BytesIO(_package(BASIC))) as package:
            assert sorted(package.namelist()) == ["collection.anki2", "media"]
            # Empty on purpose: a media column holds a remote URL, so nothing
            # has to travel inside the package.
            assert json.loads(package.read("media")) == {}

    def test_it_declares_the_legacy_schema(self):
        (ver, *_), _, _ = _collection(_package(BASIC))
        assert ver == 11

    def test_only_rows_marked_for_sync_become_notes(self):
        _, notes, _ = _collection(_package(BASIC))
        assert len(notes) == 2  # row 3 is SYNC=FALSE

    def test_the_id_leads_the_fields(self):
        # Anki uses the first field for duplicate detection, so it has to be the key.
        _, notes, _ = _collection(_package(BASIC))
        first = sorted(n[1].split("\x1f") for n in notes)[0]
        assert first[0] == "1"
        assert first[1] == "熟悉"

    def test_tags_carry_the_deck_path(self):
        _, notes, _ = _collection(_package(BASIC))
        tags = {t for note in notes for t in note[2].split()}
        assert "sheets2anki" in tags
        assert "sheets2anki::unit_1" in tags
        assert "hsk4" in tags

    def test_every_ancestor_deck_exists(self):
        """Anki nests by name, but a package listing only the leaf imports oddly."""
        (_, _, decks, _), _, _ = _collection(_package(BASIC))
        names = {d["name"] for d in json.loads(decks).values()}
        assert "Sheets2Anki" in names
        assert "Sheets2Anki::HSK4" in names
        assert "Sheets2Anki::HSK4::Unit 1" in names

    def test_the_note_type_is_the_one_the_sync_would_make(self):
        (_, models, _, _), _, _ = _collection(_package(BASIC))
        model = next(iter(json.loads(models).values()))
        assert model["name"] == "Sheets2Anki - HSK4 - Basic"
        assert model["type"] == 0
        assert [f["name"] for f in model["flds"]] == ["ID", "Word", "Meaning"]


@pytest.mark.unit
class TestIdentity:
    def test_the_same_row_keeps_its_guid(self):
        """This is what makes a second import an update instead of a duplicate."""
        assert note_guid("SHEET", "1") == note_guid("SHEET", "1")

    def test_different_rows_and_sheets_do_not_collide(self):
        assert note_guid("SHEET", "1") != note_guid("SHEET", "2")
        assert note_guid("SHEET", "1") != note_guid("OTHER", "1")

    def test_identity_survives_a_rebuild_but_the_timestamp_moves(self):
        """Anki only overwrites a note when the incoming one is newer."""
        _, early, _ = _collection(_package(BASIC, now=1786000000))
        _, later, _ = _collection(_package(BASIC, now=1786009999))
        assert {n[0] for n in early} == {n[0] for n in later}


@pytest.mark.unit
class TestCloze:
    def test_one_card_per_deletion_in_the_declared_column(self):
        plan = plan_columns(["ID", "Word", "Sentence"])
        config = parse_config_row({"ID": "#config", "Sentence": "cloze"}, plan)
        row = {"Sentence": "a {{c1::one}} b {{c3::three}}"}
        assert cloze_ordinals(row, plan, config) == [0, 2]

    def test_a_column_that_was_not_declared_contributes_nothing(self):
        plan = plan_columns(["ID", "Word", "Sentence"])
        config = parse_config_row({"ID": "#config", "Sentence": "cloze"}, plan)
        assert cloze_ordinals({"Word": "{{c1::x}}"}, plan, config) == []

    def test_a_sheet_with_no_cloze_column_has_no_ordinals(self):
        plan = plan_columns(["ID", "Word"])
        assert cloze_ordinals({"Word": "{{c1::x}}"}, plan, SheetConfig()) == []

    def test_the_package_makes_a_card_per_deletion(self):
        _, notes, cards = _collection(_package(CLOZE, deck="Cloze"))
        assert len(notes) == 2
        assert len(cards) == 3  # two deletions in one row, one in the other


# ---------------------------------------------------------------------------
# Against a real Anki
# ---------------------------------------------------------------------------


def _real_anki(code):
    """Runs code in a subprocess where `anki` is the real package, not the mock."""
    return subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, cwd=str(REPO)
    )


_HARNESS = """
import json, os, sys, tempfile, types
import anki, anki.import_export_pb2 as pb
from anki.collection import Collection

pkg = types.ModuleType("s2a"); pkg.__path__ = [os.path.abspath("src")]
sys.modules["s2a"] = pkg
from s2a.tsv_model import parse_tsv_data, build_remote_deck_from_tsv
from s2a.apkg import build_package

ALWAYS = pb.ImportAnkiPackageUpdateCondition.IMPORT_ANKI_PACKAGE_UPDATE_CONDITION_ALWAYS

def package(tsv, now):
    remote = build_remote_deck_from_tsv(parse_tsv_data(tsv), "url")
    data = build_package("SHEET", "HSK4", remote.plan, remote.sheet_config,
                         remote.notes, now=now)
    path = os.path.join(tempfile.mkdtemp(), "p.apkg")
    open(path, "wb").write(data)
    return path

def load(col, path):
    return col.import_anki_package(anki.collection.ImportAnkiPackageRequest(
        package_path=path,
        options=pb.ImportAnkiPackageOptions(
            merge_notetypes=True, with_scheduling=False,
            update_notes=ALWAYS, update_notetypes=ALWAYS)))

col = Collection(os.path.join(tempfile.mkdtemp(), "c.anki2"))
"""


@pytest.mark.slow
def test_real_anki_imports_the_package():
    """The decisive check: a mock cannot tell a valid package from a broken one."""
    result = _real_anki(_HARNESS + """
tsv = ("ID\\tSYNC\\tSUBDECK 1\\tWord\\tMeaning\\n"
       "#config reverse\\t\\t\\tsize=48\\tsize=18\\n"
       "1\\tTRUE\\tUnit 1\\t\\u719f\\u6089\\tfamiliar\\n"
       "2\\tFALSE\\tUnit 2\\t\\u590d\\u6742\\tcomplicated\\n")
load(col, package(tsv, 1786000000))
print(json.dumps({
    "notes": col.note_count(),
    "cards": col.card_count(),
    "decks": sorted(d.name for d in col.decks.all_names_and_ids()
                    if d.name.startswith("Sheets2Anki")),
    "models": [m.name for m in col.models.all_names_and_ids()
               if m.name.startswith("Sheets2Anki")],
}))
col.close()
""")
    assert result.returncode == 0, result.stderr[-2000:]

    out = json.loads(result.stdout.strip().splitlines()[-1])
    assert out["notes"] == 1  # the SYNC=FALSE row never left the sheet
    assert out["cards"] == 2  # forward and reverse
    assert out["decks"] == [
        "Sheets2Anki",
        "Sheets2Anki::HSK4",
        "Sheets2Anki::HSK4::Unit 1",
    ]
    assert out["models"] == ["Sheets2Anki - HSK4 - Basic"]


@pytest.mark.slow
def test_importing_twice_updates_instead_of_duplicating():
    """The property that makes this usable more than once."""
    result = _real_anki(_HARNESS + """
BASE = "ID\\tWord\\tMeaning\\n1\\t\\u719f\\u6089\\tfamiliar\\n"
EDIT = "ID\\tWord\\tMeaning\\n1\\t\\u719f\\u6089\\tCHANGED\\n"
load(col, package(BASE, 1786000000))
first = col.note_count()
load(col, package(EDIT, 1786009999))
note = col.get_note(col.find_notes("")[0])
print(json.dumps({"first": first, "after": col.note_count(), "meaning": note.fields[2]}))
col.close()
""")
    assert result.returncode == 0, result.stderr[-2000:]

    out = json.loads(result.stdout.strip().splitlines()[-1])
    assert out["first"] == 1
    assert (
        out["after"] == 1
    ), "a second import duplicated the note instead of updating it"
    assert out["meaning"] == "CHANGED", "the edit did not reach the existing note"
