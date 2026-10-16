"""The `.apkg` a sheet turns into, and the promises that file makes.

Two of these run a *real* Anki in a subprocess. The suite mocks `anki` for every
other module, so a package that is subtly malformed would sail through a
mock-based test and fail only in front of someone with a phone — and the whole
point of this format is that it reaches a phone without a desktop in between.
"""

import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import unicodedata
import zipfile
from pathlib import Path

import pytest

from src.apkg import build_package
from src.apkg import cloze_ordinals
from src.apkg import deck_identity
from src.apkg import kept_fields
from src.apkg import model_id
from src.apkg import note_guid
from src.apkg import resolve_identity
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
        assert "sheetcards" in tags
        assert "sheetcards::unit_1" in tags
        assert "hsk4" in tags

    def test_every_ancestor_deck_exists(self):
        """Anki nests by name, but a package listing only the leaf imports oddly."""
        (_, _, decks, _), _, _ = _collection(_package(BASIC))
        names = {d["name"] for d in json.loads(decks).values()}
        assert "sc_HSK4" in names
        assert "sc_HSK4::Unit 1" in names

    def test_the_note_type_is_the_one_the_sync_would_make(self):
        (_, models, _, _), _, _ = _collection(_package(BASIC))
        model = next(iter(json.loads(models).values()))
        assert model["name"] == "SheetCards - HSK4 - Basic"
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


VOCAB = "ID\tWord\tMeaning\nw01\tapple\tquả táo\nw02\tbook\tquyển sách\n"


def _ids(data):
    """The note type ids, the (guid, note id) pairs and the deck ids of a package."""
    (_, models, decks, _), _, _ = _collection(data)
    import sqlite3

    with tempfile.TemporaryDirectory() as folder:
        inner = os.path.join(folder, "c.anki2")
        with zipfile.ZipFile(io.BytesIO(data)) as package:
            Path(inner).write_bytes(package.read("collection.anki2"))
        db = sqlite3.connect(inner)
        notes = db.execute("select guid, id from notes order by id").fetchall()
        db.close()
    return list(json.loads(models)), sorted(notes), sorted(json.loads(decks))


@pytest.mark.unit
class TestLegacyIdentity:
    """A sheet with no ``sheet=`` key must keep the ids it has always had.

    These numbers were produced by the code before sheets carried a key. A deck
    imported from it is in somebody's Anki now, and a change here would make
    the next import of that sheet a second copy of every note.
    """

    def test_a_file_handed_over_by_create_sheet(self):
        models, notes, decks = _ids(_package(VOCAB, "file:Từ vựng.tsv#", "Từ vựng"))
        assert models == ["8122527491559623266"]
        assert notes == sorted(
            [
                ("dc2a6873dfac66e7a7f5", 3378217587377289391),
                ("7fe708e34a23b441ac19", 7956096031239844025),
            ]
        )
        assert decks == ["1", "4110335532568893414"]

    def test_a_google_sheet(self):
        models, notes, _ = _ids(_package(VOCAB, "1AbCdEfGh#Sheet1", "Vocab::Sheet1"))
        assert models == ["5925728571391714922"]
        assert notes == sorted(
            [
                ("463715b538f40d02e1b2", 1327077341866221173),
                ("94eb6e564cf9d6605e89", 3674703627276847869),
            ]
        )


@pytest.mark.unit
class TestDeckname:
    KEYED = (
        "ID\tWord\tMeaning\n#config name=Từ vựng tiếng Anh\t\t\n"
        "w01\tapple\tquả táo\nw02\tbook\tquyển sách\n"
    )

    def test_the_name_beats_the_source_as_identity_and_as_name(self):
        config = parse_config_row(
            {"ID": "#config name=Từ vựng tiếng Anh"}, plan_columns(["ID", "W"])
        )
        assert resolve_identity("file:x.tsv#", "x", config) == (
            "name:từ vựng tiếng anh",
            "Từ vựng tiếng Anh",
            True,
        )
        assert resolve_identity("file:x.tsv#", "x", SheetConfig()) == (
            "file:x.tsv#",
            "x",
            False,
        )

    def test_spacing_case_and_composition_do_not_make_another_deck(self):
        decomposed = unicodedata.normalize("NFD", "Từ vựng")
        assert deck_identity("  từ   VỰNG ") == deck_identity(decomposed)

    def test_a_named_sheet_is_the_same_notes_from_any_source(self):
        a = _ids(_package(self.KEYED, "file:Từ vựng.tsv#", "Từ vựng"))
        b = _ids(_package(self.KEYED, "file:Từ vựng (1).xlsx#Sheet1", "Từ vựng (1)"))
        c = _ids(_package(self.KEYED, "1AbCdEfGh#Sheet1", "Vocab"))
        assert a == b == c

    def test_the_deck_takes_the_name_as_written(self):
        (_, models, decks, _), _, _ = _collection(_package(self.KEYED))
        assert next(iter(json.loads(models).values()))["name"] == (
            "SheetCards - Từ vựng tiếng Anh - Basic"
        )
        assert "sc_Từ vựng tiếng Anh" in {d["name"] for d in json.loads(decks).values()}

    def test_two_names_do_not_share_notes(self):
        other = self.KEYED.replace("tiếng Anh", "tiếng Trung")
        assert set(_ids(_package(self.KEYED))[1]).isdisjoint(_ids(_package(other))[1])
        assert _ids(_package(self.KEYED))[0] != _ids(_package(other))[0]

    def test_the_model_id_ignores_the_deck_name_only_when_keyed(self):
        assert model_id("k1", "A", False, keyed=True) == model_id(
            "k1", "B", False, keyed=True
        )
        assert model_id("k1", "A", False, keyed=True) != model_id(
            "k1", "A", True, keyed=True
        )
        assert model_id("s", "A", False) != model_id("s", "B", False)


@pytest.mark.unit
class TestKeptFields:
    def test_a_first_package_is_the_sheet(self):
        assert kept_fields(["ID", "Word", "Meaning"]) == ["ID", "Word", "Meaning"]

    def test_removed_and_moved_columns_keep_the_old_order(self):
        old = ["ID", "Word", "Meaning", "Example"]
        assert kept_fields(["ID", "Example", "Word"], old) == old

    def test_new_columns_are_appended_the_way_anki_merges_them(self):
        old = ["ID", "Word", "Meaning"]
        assert kept_fields(["ID", "Word", "Nghĩa"], old) == old + ["Nghĩa"]

    def test_a_removed_column_is_written_empty(self):
        tsv = "ID\tWord\nw01\tapple\n"
        _, notes, _ = _collection(
            build_package(
                "S",
                "D",
                *(lambda r: (r.plan, r.sheet_config, r.notes))(
                    build_remote_deck_from_tsv(parse_tsv_data(tsv), "u")
                ),
                previous_fields=["ID", "Word", "Meaning"],
            )
        )
        assert notes[0][1].split("\x1f") == ["w01", "apple", ""]


@pytest.mark.unit
class TestDuplicateIds:
    def test_the_first_row_of_an_id_is_the_note(self):
        tsv = VOCAB + "w02\tbread\tbánh mì\n"
        _, notes, cards = _collection(_package(tsv))
        assert len(notes) == 2 and len(cards) == 2
        book = [n for n in notes if n[1].startswith("w02")]
        assert book[0][1].split("\x1f")[1] == "book"


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


# Installed by the dev extras. Skipping rather than failing keeps the suite usable
# for anyone who has not installed it, while CI always has it and always runs these.
_HAS_ANKI = importlib.util.find_spec("anki") is not None
needs_anki = pytest.mark.skipif(
    not _HAS_ANKI,
    reason="the real anki library is not installed (pip install -e '.[dev]')",
)


def _real_anki(code):
    """Runs code in a subprocess where `anki` is the real package, not the mock."""
    return subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, cwd=str(REPO)
    )


_HARNESS = """
import json, os, sys, tempfile, types
import anki, anki.import_export_pb2 as pb
from anki.collection import Collection

pkg = types.ModuleType("sc"); pkg.__path__ = [os.path.abspath("src")]
sys.modules["sc"] = pkg
from sc.tsv_model import parse_tsv_data, build_remote_deck_from_tsv
from sc.apkg import build_package

ALWAYS = pb.ImportAnkiPackageUpdateCondition.IMPORT_ANKI_PACKAGE_UPDATE_CONDITION_ALWAYS
IF_NEWER = pb.ImportAnkiPackageUpdateCondition.IMPORT_ANKI_PACKAGE_UPDATE_CONDITION_IF_NEWER

def package(tsv, now, sheet="SHEET", deck="HSK4", previous=()):
    remote = build_remote_deck_from_tsv(parse_tsv_data(tsv), "url")
    data = build_package(sheet, deck, remote.plan, remote.sheet_config,
                         remote.notes, now=now, previous_fields=previous)
    path = os.path.join(tempfile.mkdtemp(), "p.apkg")
    open(path, "wb").write(data)
    return path

def load(col, path):
    return col.import_anki_package(anki.collection.ImportAnkiPackageRequest(
        package_path=path,
        options=pb.ImportAnkiPackageOptions(
            merge_notetypes=True, with_scheduling=False,
            update_notes=ALWAYS, update_notetypes=ALWAYS)))

# What every Anki offers when nobody touches the import screen: merge off,
# update notes and note types only when newer. The test above imports with
# merge on, which is exactly what hid a schema change stopping all updates.
def load_default(col, path, merge=False):
    log = col.import_anki_package(anki.collection.ImportAnkiPackageRequest(
        package_path=path,
        options=pb.ImportAnkiPackageOptions(
            merge_notetypes=merge, with_scheduling=False,
            update_notes=IF_NEWER, update_notetypes=IF_NEWER))).log
    return {k: len(getattr(log, k)) for k in ("new", "updated", "conflicting", "duplicate")}

col = Collection(os.path.join(tempfile.mkdtemp(), "c.anki2"))
"""


@pytest.mark.slow
@needs_anki
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
                    if d.name.startswith("sc_")),
    "models": [m.name for m in col.models.all_names_and_ids()
               if m.name.startswith("SheetCards")],
}))
col.close()
""")
    assert result.returncode == 0, result.stderr[-2000:]

    out = json.loads(result.stdout.strip().splitlines()[-1])
    assert out["notes"] == 1  # the SYNC=FALSE row never left the sheet
    assert out["cards"] == 2  # forward and reverse
    assert out["decks"] == ["sc_HSK4", "sc_HSK4::Unit 1"]
    assert out["models"] == ["SheetCards - HSK4 - Basic"]


@pytest.mark.slow
@needs_anki
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


@pytest.mark.slow
@needs_anki
def test_default_import_options():
    """Anki's own defaults: what a schema change does, and what a key buys."""
    result = _real_anki(_HARNESS + """
H = "ID\\tWord\\tMeaning\\n"
ROWS = "w01\\tapple\\tqua tao\\nw02\\tbook\\tquyen sach\\n"
EDIT = ROWS.replace("quyen sach", "EDITED")
out = {}
# The clock, not a fixed stamp: merging a note type rewrites the notes already
# there at the real time, and an import only wins when it is newer than that.
import time
T = int(time.time())
col = Collection(os.path.join(tempfile.mkdtemp(), "c.anki2"))
load_default(col, package(H + ROWS, T + 0))
out["unchanged"] = load_default(col, package(H + EDIT, T + 100))
RENAMED = "ID\\tWord\\tNghia\\n"
out["renamed_off"] = load_default(col, package(RENAMED + ROWS, T + 200))
out["renamed_on"] = load_default(col, package(RENAMED + ROWS, T + 300), merge=True)
ADDED = "ID\\tWord\\tNghia\\tNote\\n"
MORE = "w01\\tapple\\tqua tao\\tx\\nw02\\tbook\\tquyen sach\\ty\\n"
out["added_off"] = load_default(col, package(ADDED + MORE, T + 400))
out["added_on"] = load_default(col, package(ADDED + MORE, T + 500), merge=True)
out["notes"] = col.note_count()
out["merged"] = sorted(col.get_note(n)["Note"] for n in col.find_notes(""))
col.close()

# A named sheet: another file name, another source, the same notes.
KEYED = H + "#config name=Vocab\\t\\t\\n"
col = Collection(os.path.join(tempfile.mkdtemp(), "c.anki2"))
load_default(col, package(KEYED + ROWS, T + 0, "file:Vocab.tsv#", "Vocab"))
out["keyed_file"] = load_default(
    col, package(KEYED + EDIT, T + 100, "file:Vocab (1).csv#", "Vocab (1)"))
out["keyed_google"] = load_default(col, package(KEYED + EDIT, T + 200, "1AbC#Sheet1", "x"))
out["keyed_notes"] = col.note_count()
col.close()

print(json.dumps(out))
""")
    assert result.returncode == 0, result.stderr[-2000:]

    out = json.loads(result.stdout.strip().splitlines()[-1])
    assert out["unchanged"] == {
        "new": 0,
        "updated": 2,
        "conflicting": 0,
        "duplicate": 0,
    }
    # A renamed or added column is a new note type to Anki: with merge off,
    # every note conflicts and nothing is updated. The page tells the user to
    # turn merge on, and this is why.
    assert out["renamed_off"]["conflicting"] == 2
    assert out["renamed_off"]["updated"] == 0
    assert out["renamed_on"]["updated"] == 2
    assert out["added_off"]["conflicting"] == 2
    assert out["added_on"]["updated"] == 2
    assert out["notes"] == 2
    assert out["merged"] == ["x", "y"]
    assert out["keyed_file"] == {
        "new": 0,
        "updated": 2,
        "conflicting": 0,
        "duplicate": 0,
    }
    assert out["keyed_google"] == {
        "new": 0,
        "updated": 2,
        "conflicting": 0,
        "duplicate": 0,
    }
    assert out["keyed_notes"] == 2


@pytest.mark.slow
@needs_anki
def test_kept_fields_make_one_merge_enough():
    """After one merge the next import, with Anki's defaults, updates again."""
    result = _real_anki(_HARNESS + """
import time
T = int(time.time())
out = {}
col = Collection(os.path.join(tempfile.mkdtemp(), "c.anki2"))
OLD = ["ID", "Word", "Meaning", "Example"]
load_default(col, package("ID\\tWord\\tMeaning\\tExample\\nw01\\ta\\tb\\tc\\n", T - 900))
# A column removed: no new schema, so no merge.
out["removed"] = load_default(
    col, package("ID\\tWord\\tMeaning\\nw01\\ta\\tB\\n", T - 800, previous=OLD))
# A column renamed: one merge, with notes updated always (the merge stamps the
# notes already there with the time of the import).
NEW = "ID\\tWord\\tNghia\\nw01\\ta\\tN\\n"
log = col.import_anki_package(anki.collection.ImportAnkiPackageRequest(
    package_path=package(NEW, T - 700, previous=OLD),
    options=pb.ImportAnkiPackageOptions(merge_notetypes=True, with_scheduling=False,
        update_notes=ALWAYS, update_notetypes=IF_NEWER))).log
out["merged"] = len(log.updated)
out["next"] = load_default(col, package(NEW.replace("N\\n", "N2\\n"), int(time.time()) + 5,
                           previous=OLD + ["Nghia"]))
note = col.get_note(col.find_notes("")[0])
out["note"] = dict(zip(note.keys(), note.values()))
out["notes"] = col.note_count()
print(json.dumps(out))
col.close()
""")
    assert result.returncode == 0, result.stderr[-2000:]

    out = json.loads(result.stdout.strip().splitlines()[-1])
    assert out["removed"]["updated"] == 1 and out["removed"]["conflicting"] == 0
    assert out["merged"] == 1
    assert out["next"]["updated"] == 1 and out["next"]["conflicting"] == 0
    assert out["note"]["Nghia"] == "N2"
    assert out["notes"] == 1


@pytest.mark.unit
class TestSortAndClock:
    def test_the_sort_column_is_what_anki_lists_notes_by(self):
        data = _package("ID\tWord\tMeaning\n#config\tsort\t\n1\tapple\tquả táo\n")
        col, notes, _ = _collection(data)
        model = next(iter(json.loads(col[1]).values()))
        assert [f["name"] for f in model["flds"]][model["sortf"]] == "Word"
        assert notes[0][3] == "apple"

    def test_without_sort_it_is_the_first_field(self):
        col, notes, _ = _collection(_package(BASIC))
        assert next(iter(json.loads(col[1]).values()))["sortf"] == 0

    def test_two_downloads_in_one_second_are_still_newer(self):
        from src import apkg

        stamps = [apkg._clock() for _ in range(3)]
        assert stamps == sorted(set(stamps))


@pytest.mark.unit
def test_a_template_taken_out_is_kept_as_a_stub():
    from src.apkg import kept_templates
    from src.apkg import note_type_shape

    on = build_remote_deck_from_tsv(
        parse_tsv_data("ID\tWord\tMeaning\n#config reverse\t\t\n1\ta\tb\n"), "u"
    )
    off = build_remote_deck_from_tsv(
        parse_tsv_data("ID\tWord\tMeaning\n#config\t\t\n1\ta\tb\n"), "u"
    )
    was = note_type_shape(on.plan, on.sheet_config)
    now = note_type_shape(off.plan, off.sheet_config, (), was["templates"])
    assert now["templates"] == was["templates"]
    assert now["stubs"] == [was["templates"][1]]
    # turned back on, the real template takes the stub's place
    again = note_type_shape(on.plan, on.sheet_config, (), now["templates"])
    assert again["templates"] == was["templates"] and again["stubs"] == []
    # nothing remembered: just what the sheet makes
    assert kept_templates([{"name": "Card 1"}], ()) == [{"name": "Card 1"}]


@pytest.mark.slow
@needs_anki
def test_reverse_turned_off_updates_and_leaves_empty_cards():
    """Default import options: no conflict, and Empty Cards finds the old ones."""
    result = _real_anki(_HARNESS + """
from sc.apkg import note_type_shape
ON = "ID\\tWord\\tMeaning\\n#config reverse\\t\\t\\nw1\\tapple\\tt\\nw2\\tbook\\ts\\n"
OFF = ("ID\\tWord\\tMeaning\\n#config\\t\\t\\nw1\\tapple\\tt2\\nw2\\tbook\\ts\\n"
       "w3\\tcat\\tm\\n")
on = build_remote_deck_from_tsv(parse_tsv_data(ON), "u")
names = note_type_shape(on.plan, on.sheet_config)["templates"]
first = load_default(col, package(ON, 1786000000))
off = build_remote_deck_from_tsv(parse_tsv_data(OFF), "u")
data = build_package("SHEET", "HSK4", off.plan, off.sheet_config, off.notes,
                     now=1786000100, previous_templates=names)
path = os.path.join(tempfile.mkdtemp(), "p.apkg"); open(path, "wb").write(data)
second = load_default(col, path)
empty = sum(len(n.card_ids) for n in col.get_empty_cards().notes)
print(json.dumps({"first": first, "second": second, "cards": col.card_count(),
                  "empty": empty, "notes": col.note_count()}))
""")
    assert result.returncode == 0, result.stderr[-2000:]
    out = json.loads(result.stdout.strip().splitlines()[-1])
    assert out["second"]["conflicting"] == 0
    assert out["second"]["updated"] == 2 and out["second"]["new"] == 1
    assert out["notes"] == 3
    assert out["cards"] == 5  # 2 forward + 2 old reverse + w3's forward only
    assert out["empty"] == 2  # the old reverse cards, for Tools → Empty Cards
