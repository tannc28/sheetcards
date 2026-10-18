"""A shared Anki deck read back into sheets: ``src/apkg_read.py``.

Two sources: packages this project builds (``apkg.build_package``), and
packages a real Anki exports — with "Support older Anki versions" ticked, which
this can read, and without, which it must recognise and refuse in words a
learner can act on.
"""

import importlib.util
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from src.apkg import build_package
from src.apkg_read import NewFormatError
from src.apkg_read import PackageError
from src.apkg_read import field_text
from src.apkg_read import read_package
from src.tsv_model import build_remote_deck_from_tsv
from src.tsv_model import parse_tsv_data
from src.workbook import read_upload

REPO = Path(__file__).resolve().parent.parent

SHEET = (
    "ID\tSUBDECK 1\tTAGS\tWord\tMeaning\n"
    "#config name=English week 1; reverse\t\t\t\t\n"
    "w01\tUnit 1\tfruit\tapple\tquả táo\n"
    "w02\tUnit 2\t\tbook\tquyển <b>sách</b>\n"
)


def _deck(tsv):
    return build_remote_deck_from_tsv(parse_tsv_data(tsv), "")


def _package(tsv):
    remote = _deck(tsv)
    return build_package(
        "file:x.tsv#",
        "x",
        remote.plan,
        remote.sheet_config,
        remote.notes,
        now=1786000000,
    )


def _tsv(rows):
    return "\n".join("\t".join(r) for r in rows) + "\n"


@pytest.mark.unit
class TestFieldText:
    @pytest.mark.parametrize(
        "raw, cell",
        [
            ("<b>hola</b>", "<b>hola</b>"),
            ("<strong>a</strong> <em>b</em>", "<b>a</b> <i>b</i>"),
            ("hello<br>hi", "hello<br>hi"),
            ("<div>one</div><div>two</div>", "one<br>two"),
            ('<span style="color:red">red</span>', "red"),
            ("dog &amp; puppy&nbsp;!", "dog & puppy !"),
            ("1 &lt; 2", "1 &lt; 2"),
            ("El {{c1::gato}}", "El {{c1::gato}}"),
            ("<script>alert(1)</script>ok", "ok"),
        ],
    )
    def test_formatting(self, raw, cell):
        assert field_text(raw)[0] == cell

    def test_media_is_removed_and_counted(self):
        text, media = field_text(
            'gato <img src="cat.jpg"> [sound:gato.mp3]<b><img src="x.png"></b>'
        )
        assert text == "gato"
        assert media == {"images": 2, "audio": 1}


@pytest.mark.unit
class TestOwnPackage:
    def test_one_sheet_per_note_type(self):
        sheets = read_package(_package(SHEET), "English week 1.apkg")
        assert [s["name"] for s in sheets] == ["SheetCards - English week 1 - Basic"]
        rows = sheets[0]["rows"]
        # The package's own ID field is a field like any other; its guid is the key.
        assert rows[0] == ["ID", "ID (Anki)", "Word", "Meaning", "SUBDECK 1", "TAGS"]
        assert rows[1][0] == "#config name=English week 1; reverse"
        by_word = {r[2]: r for r in rows[2:]}
        assert by_word["apple"][1] == "w01"
        assert by_word["apple"][4] == "Unit 1"
        assert "fruit" in by_word["apple"][5].split(", ")
        assert by_word["book"][3] == "quyển <b>sách</b>"

    def test_the_sheet_reads_back_without_a_warning(self):
        sheet = read_package(_package(SHEET), "x.apkg")[0]
        deck = _deck(_tsv(sheet["rows"]))
        assert deck.sheet_config.warnings == []
        assert len(deck.notes) == 2
        assert deck.sheet_config.reverse is True

    def test_read_upload_offers_it_like_a_workbook(self):
        out = json.loads(read_upload(_package(SHEET), "Shared deck.apkg", 0))
        assert out["tabs"] == []
        assert out["package"] == {"notes": 2, "media": {"images": 0, "audio": 0}}
        assert out["tsv"].startswith("ID\tID (Anki)\tWord")

    def test_not_a_package(self):
        with pytest.raises(PackageError):
            read_package(b"hello", "x.apkg")

    def test_a_new_format_package_is_named_as_one(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as z:
            z.writestr("collection.anki21b", b"\x28\xb5\x2f\xfd" + b"\0" * 20)
            z.writestr("media", b"\x28\xb5\x2f\xfd")
        with pytest.raises(NewFormatError):
            read_package(buffer.getvalue(), "x.apkg")


# ---------------------------------------------------------------------------
# Packages a real Anki exported
# ---------------------------------------------------------------------------

_HAS_ANKI = importlib.util.find_spec("anki") is not None
needs_anki = pytest.mark.skipif(
    not _HAS_ANKI, reason="the real anki library is not installed"
)

_EXPORT = """
import base64, json, os, sys, tempfile
from anki.collection import Collection, DeckIdLimit
from anki.import_export_pb2 import ExportAnkiPackageOptions

col = Collection(os.path.join(tempfile.mkdtemp(), "c.anki2"))
basic = col.models.by_name("Basic")
rev = col.models.by_name("Basic (and reversed card)")
cloze = col.models.by_name("Cloze")
typed = col.models.by_name("Basic (type in the answer)")

def add(model, fields, deck, tags=""):
    note = col.new_note(model)
    for i, value in enumerate(fields):
        note.fields[i] = value
    note.tags = tags.split()
    col.add_note(note, col.decks.id(deck))

add(basic, ["<b>hola</b>", "hello<br>hi"], "Spanish::Lesson 1", "greet")
add(basic, ['gato <img src="cat.jpg">', "cat [sound:gato.mp3]"], "Spanish::Lesson 2")
add(rev, ["perro", "dog &amp; puppy"], "Spanish::Lesson 1")
add(cloze, ["El {{c1::gato}} es {{c2::negro}}", "extra"], "Spanish")
add(typed, ["uno", "one"], "Spanish")
top = col.decks.id("Spanish")
out = {}
for legacy in (True, False):
    path = os.path.join(tempfile.mkdtemp(), "p.apkg")
    col.export_anki_package(out_path=path, options=ExportAnkiPackageOptions(
        with_scheduling=False, with_deck_configs=False, with_media=True, legacy=legacy),
        limit=DeckIdLimit(top))
    out["legacy" if legacy else "new"] = base64.b64encode(open(path, "rb").read()).decode()
print(json.dumps(out))
"""


@pytest.fixture(scope="module")
def exported():
    import base64

    result = subprocess.run(
        [sys.executable, "-c", _EXPORT], capture_output=True, text=True, cwd=str(REPO)
    )
    assert result.returncode == 0, result.stderr[-2000:]
    out = json.loads(result.stdout.strip().splitlines()[-1])
    return {k: base64.b64decode(v) for k, v in out.items()}


@pytest.mark.slow
@needs_anki
def test_a_legacy_export_reads_as_sheets(exported):
    sheets = {s["name"]: s for s in read_package(exported["legacy"], "Spanish.apkg")}
    assert set(sheets) == {
        "Basic",
        "Basic (and reversed card)",
        "Cloze",
        "Basic (type in the answer)",
    }
    basic = sheets["Basic"]
    assert basic["rows"][0] == ["ID", "Front", "Back", "SUBDECK 1", "TAGS"]
    assert basic["rows"][1][0] == "#config name=Spanish (Basic)"
    words = {r[1]: r for r in basic["rows"][2:]}
    assert words["<b>hola</b>"][2] == "hello<br>hi"
    assert words["<b>hola</b>"][3] == "Lesson 1"
    assert words["gato"][2] == "cat"
    assert basic["media"] == {"images": 1, "audio": 1}

    assert sheets["Basic (and reversed card)"]["rows"][1][0].endswith("; reverse")
    cloze = sheets["Cloze"]["rows"]
    assert cloze[1][1] == "cloze"
    assert sheets["Basic (type in the answer)"]["rows"][1][2] == "type"

    for sheet in sheets.values():
        deck = _deck(_tsv(sheet["rows"]))
        assert deck.sheet_config.warnings == [], sheet["name"]
        assert len(deck.notes) == sheet["notes"]


@pytest.mark.slow
@needs_anki
def test_a_new_format_export_is_refused_by_name(exported):
    with pytest.raises(NewFormatError):
        read_package(exported["new"], "Spanish.apkg")
