"""A sheet moved from ``SUBDECK n`` headers to ``subdeck=n`` columns, in a real Anki.

``SUBDECK n`` headers are being retired. A sheet that renames them (``Level``)
and writes ``subdeck=1`` in the settings row files every note exactly where it
was, but the levels become fields of the note, so the note type grows three
fields. These tests import the old sheet's package, review a card, then import
the new sheet's package the way Sheet to Anki builds it (``previous_fields``,
see ``apkg.kept_fields``) and check what the page promises: the same notes, in
the same subdecks, with their review history — after one *Merge note types*.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

needs_anki = pytest.mark.skipif(
    importlib.util.find_spec("anki") is None,
    reason="the real anki library is not installed (pip install -e '.[dev]')",
)

SHEET = "15 Theme + subdeck (màu, tầng)"
LEVELS = ("Language", "Level", "Word class")


def _sheets():
    spec = importlib.util.spec_from_file_location(
        "build_examples_migration", REPO / "scripts" / "build_examples.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SHEETS


def _tsv(rows):
    width = max(len(r) for r in rows)
    return "".join("\t".join(list(r) + [""] * (width - len(r))) + "\n" for r in rows)


def old_and_new():
    """The workbook's sheet as it is now, and as it was with SUBDECK headers."""
    new = [list(r) for r in _sheets()[SHEET]]
    old = [list(r) for r in new]
    for n, name in enumerate(LEVELS, start=1):
        at = old[0].index(name)
        old[0][at] = f"SUBDECK {n}"
        old[1][at] = ""
    return _tsv(old), _tsv(new)


_RUN = r"""
import json, os, sys, tempfile, types
import anki, anki.import_export_pb2 as pb
from anki.collection import Collection

pkg = types.ModuleType("sc"); pkg.__path__ = [os.path.abspath("src")]
sys.modules["sc"] = pkg
from sc.tsv_model import parse_tsv_data, build_remote_deck_from_tsv
from sc.apkg import build_package, kept_fields

ALWAYS = pb.ImportAnkiPackageUpdateCondition.IMPORT_ANKI_PACKAGE_UPDATE_CONDITION_ALWAYS
IF_NEWER = pb.ImportAnkiPackageUpdateCondition.IMPORT_ANKI_PACKAGE_UPDATE_CONDITION_IF_NEWER
OLD, NEW = json.loads(sys.stdin.read())

def package(tsv, now, previous=()):
    remote = build_remote_deck_from_tsv(parse_tsv_data(tsv), "url")
    data = build_package("examples#15", "Examples", remote.plan, remote.sheet_config,
                         remote.notes, now=now, previous_fields=previous)
    path = os.path.join(tempfile.mkdtemp(), "p.apkg")
    open(path, "wb").write(data)
    return path, kept_fields(remote.plan.note_type_fields(), previous)

def load(col, path, merge, update):
    # Update note types stays at Anki's default: the page only asks for merge
    # and for Update notes = Always.
    log = col.import_anki_package(anki.collection.ImportAnkiPackageRequest(
        package_path=path,
        options=pb.ImportAnkiPackageOptions(
            merge_notetypes=merge, with_scheduling=False,
            update_notes=update, update_notetypes=IF_NEWER))).log
    return {k: len(getattr(log, k)) for k in ("new", "updated", "conflicting", "duplicate")}

def where(col):
    out = {}
    for cid in col.find_cards(""):
        card = col.get_card(cid)
        note = card.note()
        out[note.guid] = col.decks.name(card.did)
    return out

# The clock, not a fixed stamp: merging rewrites the notes already there at the
# real time, and an import only wins when it is newer than that.
import time
T = int(time.time())
result = {}
for name, merge, update in (("page", True, ALWAYS), ("default", False, IF_NEWER)):
    col = Collection(os.path.join(tempfile.mkdtemp(), "c.anki2"))
    old_path, old_fields = package(OLD, T - 900)
    load(col, old_path, False, IF_NEWER)
    before = where(col)

    # Some progress on one card: answered Good twice, so it is a review card.
    cid = sorted(col.find_cards(""))[0]
    for _ in range(2):
        card = col.get_card(cid)
        card.start_timer()
        col.sched.answerCard(card, 3)
    card = col.get_card(cid)
    progress = [card.type, card.ivl, card.reps, col.db.scalar(
        "select count() from revlog where cid=?", cid)]

    new_path, _ = package(NEW, T - 700, previous=old_fields)
    log = load(col, new_path, merge, update)
    # Reopened: the Python side caches note types, and a merge done by the
    # importer would otherwise be read back as the note type it replaced.
    path = col.path
    col.close()
    col = Collection(path)
    card = col.get_card(cid)
    model = col.models.get(col.get_note(card.nid).mid)
    note = card.note()
    result[name] = {
        "log": log,
        "notes": col.note_count(),
        "cards": col.card_count(),
        "same_decks": where(col) == before,
        "decks": sorted(set(where(col).values())),
        "progress_before": progress,
        "progress_after": [card.type, card.ivl, card.reps, col.db.scalar(
            "select count() from revlog where cid=?", cid)],
        "fields": [f["name"] for f in model["flds"]],
        "level_value": note["Level"] if "Level" in note else None,
        "models": len([m for m in col.models.all_names_and_ids()
                       if m.name.startswith("SheetCards")]),
    }
    if merge:
        # After the one merge, the next download imports with Anki's defaults.
        again, _ = package(NEW, int(time.time()) + 5, previous=result[name]["fields"])
        result[name]["next"] = load(col, again, False, IF_NEWER)
    col.close()
print(json.dumps(result))
"""


@pytest.mark.slow
@needs_anki
def test_a_sheet_moved_to_subdeck_columns_keeps_its_notes_where_they_were():
    old, new = old_and_new()
    run = subprocess.run(
        [sys.executable, "-c", _RUN],
        input=json.dumps([old, new]),
        capture_output=True,
        text=True,
        cwd=str(REPO),
    )
    assert run.returncode == 0, run.stderr[-3000:]
    out = json.loads(run.stdout.strip().splitlines()[-1])

    # What Sheet to Anki tells the user to do for a changed note type: merge,
    # update always. Every note updates in place, in the same subdeck, with its
    # review history, and the three levels are now fields holding their values.
    page = out["page"]
    assert page["log"]["conflicting"] == 0 and page["log"]["new"] == 0, page
    assert page["log"]["updated"] == page["notes"] == 15
    assert page["same_decks"], page["decks"]
    assert page["progress_after"] == page["progress_before"]
    assert page["progress_before"][2] == 2  # the card really was reviewed
    assert page["models"] == 1
    assert {"Language", "Level", "Word class"} <= set(page["fields"])
    assert page["level_value"] == "B1"
    assert page["next"]["conflicting"] == 0 and page["next"]["updated"] == 15

    # With the default options the changed note type conflicts and nothing is
    # touched — no duplicate, no lost progress — which is why the page shows the
    # merge notice for a change of fields.
    default = out["default"]
    assert default["log"]["new"] == 0 and default["log"]["duplicate"] == 0
    assert default["notes"] == 15 and default["same_decks"]
    assert default["progress_after"] == default["progress_before"]
