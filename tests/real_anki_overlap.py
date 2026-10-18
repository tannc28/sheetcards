"""Phone .apkg then desktop add-on, and the reverse, in a real Anki.

Run by tests/test_addon_site_overlap.py in a subprocess (the suite mocks anki).
The add-on's own code — naming, ensure_custom_models, create_or_update_notes —
runs against a real 25.x collection; aqt is faked (no Qt) and src/ is copied
into a throwaway add-on folder so meta.json lands there. Every import uses
Anki's DEFAULT options: merge note types off, update notes/note types if newer.
Prints FAILURES: none and exits 0 when every check holds.
"""

import importlib.abc
import importlib.machinery
import os
import shutil
import sys
import tempfile
import types

WT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADDON = tempfile.mkdtemp(prefix="scaddon")
shutil.copytree(os.path.join(WT, "src"), os.path.join(ADDON, "src"))
shutil.copy(os.path.join(WT, "config.json"), ADDON)


class Meta(type):
    def __getattr__(cls, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return Meta(name, (Dummy,), {})

    def __or__(cls, o):
        return cls

    __ror__ = __or__


class Dummy(metaclass=Meta):
    def __init__(self, *a, **k):
        pass

    def __getattr__(self, name):
        return Dummy()

    def __call__(self, *a, **k):
        return Dummy()

    def __bool__(self):
        return False

    def __iter__(self):
        return iter(())

    def __or__(self, o):
        return self

    __ror__ = __or__


class FakeModule(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return Meta(name, (Dummy,), {})


class Mw:
    col = None
    addonManager = Dummy()  # noqa: N815  (the name aqt uses)
    app = Dummy()
    pm = Dummy()


MW = Mw()


class Finder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, name, path, target=None):
        if (
            name == "aqt"
            or name.startswith("aqt.")
            or name == "_aqt"
            or name.startswith("_aqt.")
        ):
            return importlib.machinery.ModuleSpec(name, self, is_package=True)
        return None

    def create_module(self, spec):
        m = FakeModule(spec.name)
        m.__path__ = []
        if spec.name == "aqt":
            m.mw = MW
        return m

    def exec_module(self, module):
        pass


sys.meta_path.insert(0, Finder())

import anki  # noqa: E402  real
import anki.import_export_pb2 as pb  # noqa: E402
from anki.collection import Collection  # noqa: E402

pkg = types.ModuleType("addon")
pkg.__path__ = [ADDON]
sys.modules["addon"] = pkg
src = importlib.import_module("addon.src")

from addon.src import config_manager as cm  # noqa: E402
from addon.src import data_processor as dp  # noqa: E402
from addon.src import deck_manager as dm  # noqa: E402
from addon.src.apkg import build_package  # noqa: E402
from addon.src.tsv_model import build_remote_deck_from_tsv  # noqa: E402
from addon.src.tsv_model import parse_tsv_data  # noqa: E402
from addon.src.utils import get_or_create_deck  # noqa: E402
from addon.src.utils import url_for_sheet  # noqa: E402

IF_NEWER = (
    pb.ImportAnkiPackageUpdateCondition.IMPORT_ANKI_PACKAGE_UPDATE_CONDITION_IF_NEWER
)
GID = "1AbCdEfGhIjKlMnOpQrStUvWxYz0123456789abcd"
import time

CLOCK = [int(time.time()) + 1000]


def reset():
    meta = os.path.join(ADDON, "meta.json")
    if os.path.exists(meta):
        os.remove(meta)
    dm._DECLARED_NAMES.clear()
    dm._REMOTE_NAMES.clear()
    MW.col = Collection(os.path.join(tempfile.mkdtemp(), "c.anki2"))
    return MW.col


def tsv(rows):
    return "".join("\t".join(r) + "\n" for r in rows)


def site_package(text, sheet_id, deck):
    CLOCK[0] += 100
    remote = build_remote_deck_from_tsv(parse_tsv_data(text), "url")
    data = build_package(
        sheet_id, deck, remote.plan, remote.sheet_config, remote.notes, now=CLOCK[0]
    )
    path = os.path.join(tempfile.mkdtemp(), "p.apkg")
    open(path, "wb").write(data)
    return path


def site_import(col, text, sheet_id, deck, label="apkg"):
    path = site_package(text, sheet_id, deck)
    opts = pb.ImportAnkiPackageOptions(
        merge_notetypes=False,
        with_scheduling=False,
        update_notes=IF_NEWER,
        update_notetypes=IF_NEWER,
    )
    res = col.import_anki_package(
        anki.collection.ImportAnkiPackageRequest(package_path=path, options=opts)
    )
    log = res.log
    summ = {
        k: len(getattr(log, k))
        for k in [
            "new",
            "updated",
            "duplicate",
            "conflicting",
            "first_field_match",
            "missing_notetype",
            "missing_deck",
            "empty_first_field",
        ]
    }
    print(f"  IMPORT[{label}] {({k: v for k, v in summ.items() if v})}")
    return log


def connect(col, title, text, sheet="Sheet1", only=True, legacy_url=False):
    """What add_deck_dialog._add_one_sheet does for one sheet."""
    base = f"https://docs.google.com/spreadsheets/d/{GID}/edit"
    url = url_for_sheet(base, sheet, only=only and not legacy_url)
    file_remote = dm.DeckNameManager.sheet_remote_name(
        title, sheet, only and not legacy_url
    )
    dm._REMOTE_NAMES[url] = file_remote
    sc = build_remote_deck_from_tsv(parse_tsv_data(text), url).sheet_config
    remote = dm.remember_declared_name(url, sc) or file_remote
    did, actual = get_or_create_deck(
        col, dm.DeckNameManager.generate_local_name(remote)
    )
    cm.add_remote_deck(
        url,
        cm.create_deck_info(
            url=url,
            local_deck_id=did,
            local_deck_name=actual,
            remote_deck_name=remote,
            declared_name=dm.declared_name_for(url),
        ),
    )
    return url


def addon_sync(col, url, text, label="add-on"):
    """The parts of sync._sync_single_deck that decide names, then the notes."""
    remote = build_remote_deck_from_tsv(parse_tsv_data(text), url)
    dm.remember_declared_name(url, remote.sheet_config)
    info = cm.get_remote_decks()[cm.get_deck_id(url)]
    name = dm.DeckNameManager.extract_remote_name_from_url(url)
    if name != info["remote_deck_name"]:
        info["remote_deck_name"] = name
        local = dm.DeckNameManager.generate_local_name(name)
        d = col.decks.get(info["local_deck_id"])
        d["name"] = local
        col.decks.save(d)
        info["local_deck_name"] = local
        decks = cm.get_remote_decks()
        decks[cm.get_deck_id(url)] = info
        cm.save_remote_decks(decks)
    stats = dp.create_or_update_notes(col, remote, info["local_deck_id"], url)
    print(
        f"  SYNC[{label}] +{stats.created} ~{stats.updated} ={stats.unchanged} "
        f"-{stats.deleted} skipped={stats.skipped} errors={stats.errors} "
        f"warnings={[w[:90] for w in stats.warnings]}"
    )
    return stats


def review_all(col):
    from anki.scheduler.v3 import CardAnswer

    seen = set()
    for d in col.decks.all_names_and_ids():
        if d.name != "Default" and "::" not in d.name:
            col.decks.select(d.id)
            break
    for _ in range(50):
        q = col.sched.get_queued_cards(fetch_limit=1)
        if not q.cards or q.cards[0].card.id in seen:
            break
        qc = q.cards[0]
        seen.add(qc.card.id)
        card = col.get_card(qc.card.id)
        card.start_timer()
        col.sched.answer_card(
            col.sched.build_answer(card=card, states=qc.states, rating=CardAnswer.EASY)
        )


def dump(col, title=""):
    print(f"  STATE {title}")
    models = [
        m.name
        for m in col.models.all_names_and_ids()
        if m.name.startswith("SheetCards")
    ]
    decks = sorted(d.name for d in col.decks.all_names_and_ids() if d.name != "Default")
    print(f"    notetypes={models} decks={decks}")
    print(
        f"    notes={col.note_count()} cards={col.card_count()} "
        f"revlog={col.db.scalar('select count() from revlog')}"
    )
    for nid in sorted(col.find_notes(""), key=lambda n: col.get_note(n).fields[0]):
        n = col.get_note(nid)
        m = n.note_type()
        cs = []
        for c in n.cards():
            rl = col.db.scalar("select count() from revlog where cid=?", c.id)
            cs.append(f"ivl{c.ivl}/rev{rl}/{col.decks.name(c.did)}")
        print(f"    {n.guid[:10]:<10} [{m['name']}] {n.fields} {cs}")


def ids_of(col):
    return sorted(col.get_note(n).fields[0] for n in col.find_notes(""))


# ---- the scenarios --------------------------------------------------

H = ["ID", "Word", "Meaning"]
A = [H, ["w01", "apple", "quả táo"], ["w02", "book", "quyển sách"]]
B = [
    H,
    ["w01", "apple", "quả táo (sửa)"],
    ["w02", "book", "quyển sách"],
    ["w03", "cat", "con mèo"],
]
C = B + [["w04", "dog", "con chó"]]
SID = f"{GID}#Sheet1"
fails = []


def check(cond, what):
    print(("  OK   " if cond else "  FAIL ") + what)
    if not cond:
        fails.append(what)


def one_set(col, want):
    ids = ids_of(col)
    check(ids == sorted(want), f"one set of notes {sorted(want)} (got {ids})")


def named(rows, name):
    return [rows[0], ["#config name=" + name] + [""] * (len(rows[0]) - 1)] + rows[1:]


for label, mk, site_deck, only in [
    ("unnamed, one-sheet file", lambda r: r, "Vocab", True),
    ("unnamed, multi-sheet file", lambda r: r, "Vocab::Sheet1", False),
    ("name= sheet", lambda r: named(r, "Từ vựng: bài 1"), "Vocab", True),
]:
    print(f"\n### {label}: phone .apkg first, then the add-on")
    col = reset()
    site_import(col, tsv(mk(A)), SID, site_deck)
    review_all(col)
    url = connect(col, "Vocab", tsv(mk(A)), only=only)
    addon_sync(col, url, tsv(mk(B)))
    dump(col, "after add-on sync")
    one_set(col, ["w01", "w02", "w03"])
    check(col.db.scalar("select count() from revlog") == 2, "review history kept")
    log = site_import(col, tsv(mk(C)), SID, site_deck, "apkg again")
    check(
        len(log.conflicting) == 0 and len(log.new) == 1,
        "the next .apkg updates, adds w04, no conflicts",
    )
    addon_sync(col, url, tsv(mk(C)), "add-on again")
    one_set(col, ["w01", "w02", "w03", "w04"])
    check(
        len(
            {
                m.name
                for m in col.models.all_names_and_ids()
                if m.name.startswith("SheetCards")
            }
        )
        == 1,
        "one note type",
    )
    check(
        len(
            [
                d
                for d in col.decks.all_names_and_ids()
                if d.name != "Default" and d.name.count("::") == (0 if only else 1)
            ]
        )
        == 1,
        "one deck",
    )

    print(f"\n### {label}: add-on first, then the phone .apkg")
    col = reset()
    url = connect(col, "Vocab", tsv(mk(A)), only=only)
    addon_sync(col, url, tsv(mk(A)))
    review_all(col)
    log = site_import(col, tsv(mk(B)), SID, site_deck)
    dump(col, "after .apkg import")
    check(
        len(log.conflicting) == 0 and len(log.updated) >= 1 and len(log.new) == 1,
        "the .apkg updates the add-on's notes",
    )
    one_set(col, ["w01", "w02", "w03"])
    check(col.db.scalar("select count() from revlog") == 2, "review history kept")
    addon_sync(col, url, tsv(mk(C)), "add-on again")
    one_set(col, ["w01", "w02", "w03", "w04"])
    check(
        len(
            [
                m
                for m in col.models.all_names_and_ids()
                if m.name.startswith("SheetCards")
            ]
        )
        == 1,
        "one note type",
    )

print("\n### a deck the add-on made before this change (random guids, own note type)")
col = reset()
url = connect(col, "Vocab", tsv(A), legacy_url=True)
# what the old add-on did: no derived id, no guid
import addon.src.templates_and_definitions as td  # noqa: E402

real_add = td._add_with_id
td._add_with_id = lambda *a, **k: None
real_guid = dp.guid_for
dp.guid_for = lambda *a, **k: None
addon_sync(col, url, tsv(A), "old add-on")
td._add_with_id = real_add
dp.guid_for = real_guid
review_all(col)
addon_sync(col, url, tsv(A), "upgraded add-on (restamps guids)")
addon_sync(col, url, tsv(A), "upgraded add-on again (idempotent)")
log = site_import(col, tsv(B), SID, "Vocab::Sheet1")
dump(col, "after .apkg import")
check(len(log.duplicate) == 0, "no duplicates of the restamped rows")
addon_sync(col, url, tsv(B), "add-on after the .apkg")
dump(col, "after add-on")
one_set(col, ["w01", "w02", "w03"])
check(col.db.scalar("select count() from revlog") == 2, "review history kept")

print("\nFAILURES:", fails or "none")
sys.exit(1 if fails else 0)
