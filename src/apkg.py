"""Packs a sheet into an ``.apkg`` file that Anki can import.

This is the one output the add-on itself never produces: inside Anki it writes to
the open collection directly. It exists for the preview site, where there is no
collection — a browser can build the file and hand it to AnkiDroid or AnkiMobile,
so a sheet can reach a phone without the desktop app being involved at all.

**Only the packaging is new.** The fields come from
:meth:`~.column_model.ColumnPlan.note_type_fields`, the templates from
:func:`~.card_layout.build_templates`, the deck path from
:func:`~.tsv_model.get_subdeck_name`, the tags from :func:`~.tsv_model.build_tags`
— the same functions the sync calls. Nothing about how a card looks is decided
twice.

The file targets Anki's **legacy schema 11**, the format written into
``collection.anki2``. Modern Anki still imports it, and it is far simpler than the
current schema; the schema below was read out of a package Anki itself exported
rather than transcribed from documentation.

Re-importing is an *update*, not a duplicate: a note's GUID is derived from the
row's ``ID``, which is the same key the sync matches on. Anki applies the update
only when the incoming note is newer, so ``mod`` is taken from the clock while the
ids stay derived — verified by importing twice into a real collection.

What re-importing cannot do is **delete**. Anki's importer never removes a note
that is missing from the file, so a row deleted from the sheet lives on in the
collection until it is deleted there by hand. That is the real difference between
this and a sync, and it is why the add-on still exists.
"""

import hashlib
import io
import json
import re
import time
import unicodedata
import zipfile

from .card_layout import build_templates
from .column_model import deck_path
from .tsv_model import SYNCED
from .tsv_model import build_tags
from .tsv_model import classify_row
from .tsv_model import deck_root_name
from .tsv_model import get_subdeck_name

# Read from a package exported by Anki 25.x, not from memory. The comment inside
# `notes` is Anki's own and explains why sfld is typed `integer`.
SCHEMA = """
CREATE TABLE col (
    id integer PRIMARY KEY, crt integer NOT NULL, mod integer NOT NULL,
    scm integer NOT NULL, ver integer NOT NULL, dty integer NOT NULL,
    usn integer NOT NULL, ls integer NOT NULL, conf text NOT NULL,
    models text NOT NULL, decks text NOT NULL, dconf text NOT NULL,
    tags text NOT NULL
);
CREATE TABLE notes (
    id integer PRIMARY KEY, guid text NOT NULL, mid integer NOT NULL,
    mod integer NOT NULL, usn integer NOT NULL, tags text NOT NULL,
    flds text NOT NULL,
    -- integer so that numeric ids sort numerically, which is Anki's own reason
    sfld integer NOT NULL, csum integer NOT NULL, flags integer NOT NULL,
    data text NOT NULL
);
CREATE TABLE cards (
    id integer PRIMARY KEY, nid integer NOT NULL, did integer NOT NULL,
    ord integer NOT NULL, mod integer NOT NULL, usn integer NOT NULL,
    type integer NOT NULL, queue integer NOT NULL, due integer NOT NULL,
    ivl integer NOT NULL, factor integer NOT NULL, reps integer NOT NULL,
    lapses integer NOT NULL, left integer NOT NULL, odue integer NOT NULL,
    odid integer NOT NULL, flags integer NOT NULL, data text NOT NULL
);
CREATE TABLE revlog (
    id integer PRIMARY KEY, cid integer NOT NULL, usn integer NOT NULL,
    ease integer NOT NULL, ivl integer NOT NULL, lastIvl integer NOT NULL,
    factor integer NOT NULL, time integer NOT NULL, type integer NOT NULL
);
CREATE TABLE graves (
    usn integer NOT NULL, oid integer NOT NULL, type integer NOT NULL
);
CREATE INDEX ix_notes_usn ON notes (usn);
CREATE INDEX ix_cards_usn ON cards (usn);
CREATE INDEX ix_revlog_usn ON revlog (usn);
CREATE INDEX ix_cards_nid ON cards (nid);
CREATE INDEX ix_cards_sched ON cards (did, queue, due);
CREATE INDEX ix_revlog_cid ON revlog (cid);
CREATE INDEX ix_notes_csum ON notes (csum);
"""

FIELD_SEPARATOR = "\x1f"

MODEL_STANDARD = 0
MODEL_CLOZE = 1

# {{c1::…}} — the number is the card this deletion belongs to.
_CLOZE_RE = re.compile(r"\{\{c(\d+)::", re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text):
    """What Anki stores in ``sfld`` and checksums: the field without its markup."""
    return _TAG_RE.sub("", str(text or ""))


def _checksum(first_field):
    """Anki's field checksum: the first 8 hex digits of the sha1, as an integer.

    Anki uses it to find duplicates, so it has to be computed the same way or the
    duplicate warning in the browser stops working on imported notes.
    """
    digest = hashlib.sha1(_strip_html(first_field).encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


def _stable_id(*parts):
    """A positive 63-bit id derived from its inputs.

    Anki ids are normally timestamps. Deriving them instead means the same row
    keeps the same identity across exports, which is what lets a second import
    update rather than duplicate.

    The *timestamps* deliberately do not follow suit: Anki only overwrites an
    existing note when the incoming one is newer, so ``mod`` comes from the clock.
    Identity stable, modification time moving — exporting twice inside the same
    second is the one case where the second import will find nothing to do.
    """
    digest = hashlib.sha1("::".join(str(p) for p in parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") & 0x7FFFFFFFFFFFFFFF


def note_guid(sheet_id, row_id):
    """The GUID Anki matches an imported note against.

    Derived from the sheet and the row's own ``ID``, which is the key the sync uses
    too, so importing the same sheet twice updates the notes instead of doubling
    them.
    """
    digest = hashlib.sha1(f"{sheet_id}\x1f{row_id}".encode()).digest()
    # Anki's guids are short base91-ish strings; any stable text works, and hex
    # keeps it obvious that this is derived rather than random.
    return digest[:10].hex()


def deck_identity(name):
    """What a ``deckname=`` is as an identity: the same deck however it is typed.

    Trimmed, inner whitespace collapsed, NFC (a phone keyboard and a desktop one
    can compose ``ệ`` differently) and case-folded, because Anki itself treats
    deck names that differ only in case as one deck.
    """
    text = unicodedata.normalize("NFC", str(name or ""))
    return " ".join(text.split()).casefold()


def resolve_identity(sheet_id, deck_name, sheet_config):
    """What a package is keyed by and what its deck is called.

    The sheet's own ``deckname=`` wins over whatever the page derived from the
    source (a spreadsheet id, a file name), as the identity and as the name —
    so a sheet keeps one deck however it travels.

    Returns:
        tuple: ``(sheet_id, deck_name, keyed)``, ``keyed`` true when the
        identity came from the sheet itself
    """
    named = getattr(sheet_config, "deck_name", None)
    if named and deck_identity(named):
        return f"deckname:{deck_identity(named)}", " ".join(named.split()), True
    return sheet_id, deck_name, False


def model_id(sheet_id, deck_name, is_cloze, keyed=False):
    """The note type's id, which Anki matches an imported note type by.

    A keyed sheet derives it from its identity and the kind alone. A sheet
    without one keeps the formula it has always had — the deck name included —
    because changing it would move every deck already imported onto a new note
    type, and every note on it would conflict.
    """
    kind = "Cloze" if is_cloze else "Basic"
    if keyed:
        return _stable_id("model", sheet_id, kind)
    return _stable_id("model", sheet_id, f"SheetCards - {deck_name} - {kind}")


def kept_fields(current, previous=()):
    """The note type's fields, given the ones the last package of this sheet had.

    Anki treats any change to a note type's field list — one added, renamed,
    removed or moved — as a new schema, and with its default import options
    every note on it then *conflicts* instead of updating. After the user merges
    once, Anki holds the old fields with the new ones appended, by name. So the
    package carries exactly that: the previous fields in their order, then each
    new one. A column removed or moved therefore changes nothing Anki can see,
    and after one merge for an added or renamed column the next import matches
    again — instead of conflicting on every import after it.
    """
    previous = [f for f in previous or [] if isinstance(f, str)]
    if not previous or previous[0] != current[0]:
        return list(current)
    return previous + [f for f in current if f not in previous]


def note_type_shape(plan, sheet_config, previous_fields=()):
    """What Anki compares a note type by: its kind, fields and template names."""
    is_cloze = bool(sheet_config.cloze_field)
    return {
        "kind": "cloze" if is_cloze else "basic",
        "fields": kept_fields(plan.note_type_fields(), previous_fields),
        "templates": [
            spec["name"]
            for spec in build_templates(plan, sheet_config, is_cloze=is_cloze)
        ],
    }


def cloze_ordinals(note_data, plan, sheet_config):
    """Which cards a cloze row produces, as zero-based template ordinals.

    Anki makes one card per distinct ``{{cN::}}`` in the field the sheet declared
    as its cloze column — and only that field, since the template only wraps that
    one in ``{{cloze:…}}``.
    """
    header = sheet_config.cloze_field
    if not header:
        return []
    found = {int(n) for n in _CLOZE_RE.findall(str(note_data.get(header, "")))}
    return sorted(n - 1 for n in found if n > 0)


def _field_entry(name, ord_):
    return {
        "name": name,
        "ord": ord_,
        "sticky": False,
        "rtl": False,
        "font": "Arial",
        "size": 20,
        "description": "",
        "plainText": False,
        "collapsed": False,
        "excludeFromSearch": False,
    }


def _template_entry(spec, ord_):
    return {
        "name": spec["name"],
        "ord": ord_,
        "qfmt": spec["qfmt"],
        "afmt": spec["afmt"],
        "did": None,
        "bqfmt": "",
        "bafmt": "",
        "bfont": "",
        "bsize": 0,
    }


def _requirements(templates, fields):
    """Which fields each template needs before Anki will make its card.

    Schema 11 keeps this precomputed in ``req``. Every field the question mentions
    counts, and "any" is right rather than "all" because each field on the card is
    wrapped in its own ``{{#Field}}`` guard: one filled column is enough to make
    the card worth showing.
    """
    req = []
    for ord_, spec in enumerate(templates):
        needed = [
            i
            for i, name in enumerate(fields)
            if f"{{{{{name}}}}}" in spec["qfmt"] or f"{{{{#{name}}}}}" in spec["qfmt"]
        ]
        req.append([ord_, "any" if needed else "none", needed])
    return req


def _model(mid, name, fields, templates, is_cloze, now):
    return {
        "id": mid,
        "name": name,
        "type": MODEL_CLOZE if is_cloze else MODEL_STANDARD,
        "mod": now,
        "usn": -1,
        "sortf": 0,
        "did": 1,
        "tmpls": [_template_entry(spec, i) for i, spec in enumerate(templates)],
        "flds": [_field_entry(name, i) for i, name in enumerate(fields)],
        "css": (
            ".card { font-family: arial; font-size: 20px; text-align: center;"
            " color: black; background-color: white; }"
        ),
        "latexPre": (
            "\\documentclass[12pt]{article}\n\\special{papersize=3in,5in}\n"
            "\\usepackage[utf8]{inputenc}\n\\usepackage{amssymb,amsmath}\n"
            "\\pagestyle{empty}\n\\setlength{\\parindent}{0in}\n\\begin{document}\n"
        ),
        "latexPost": "\\end{document}",
        "latexsvg": False,
        "req": _requirements(templates, fields),
    }


def _deck(deck_id, name, now):
    return {
        "id": deck_id,
        "name": name,
        "mod": now,
        "usn": -1,
        "desc": "",
        "dyn": 0,
        "conf": 1,
        "collapsed": False,
        "browserCollapsed": False,
        "extendNew": 0,
        "extendRev": 0,
        "newToday": [0, 0],
        "revToday": [0, 0],
        "lrnToday": [0, 0],
        "timeToday": [0, 0],
    }


def _deck_config():
    return {
        "1": {
            "id": 1,
            "name": "Default",
            "mod": 0,
            "usn": 0,
            "maxTaken": 60,
            "autoplay": True,
            "timer": 0,
            "replayq": True,
            "new": {
                "bury": False,
                "delays": [1.0, 10.0],
                "initialFactor": 2500,
                "ints": [1, 4, 0],
                "order": 1,
                "perDay": 20,
            },
            "rev": {
                "bury": False,
                "ease4": 1.3,
                "ivlFct": 1.0,
                "maxIvl": 36500,
                "perDay": 200,
                "hardFactor": 1.2,
            },
            "lapse": {
                "delays": [10.0],
                "leechAction": 1,
                "leechFails": 8,
                "minInt": 1,
                "mult": 0.0,
            },
            "dyn": False,
            "newMix": 0,
            "newPerDayMinimum": 0,
            "interdayLearningMix": 0,
            "reviewOrder": 0,
            "newSortOrder": 0,
            "newGatherPriority": 0,
            "buryInterdayLearning": False,
        }
    }


def _collection_config(mid):
    return {
        "nextPos": 1,
        "estTimes": True,
        "activeDecks": [1],
        "sortType": "noteFld",
        "timeLim": 0,
        "sortBackwards": False,
        "addToCur": True,
        "curDeck": 1,
        "newBury": True,
        "newSpread": 0,
        "dueCounts": True,
        "curModel": mid,
        "collapseTime": 1200,
        "schedVer": 2,
        "dayLearnFirst": False,
        "creationOffset": 0,
    }


def build_package(
    sheet_id, deck_name, plan, sheet_config, rows, now=None, previous_fields=()
):
    """Builds an ``.apkg`` from the rows of one sheet.

    Args:
        sheet_id (str): what the page keyed the source by (a spreadsheet id, a
            file name); the sheet's own ``deckname=`` replaces it
        deck_name (str): the deck's own name, without the ``SheetCards`` root;
            the sheet's own ``deckname=`` replaces it
        plan (ColumnPlan): the sheet's column roles
        sheet_config (SheetConfig): the parsed settings row
        rows (list[dict]): rows keyed by header, already media-rewritten
        now (int, optional): the timestamp to stamp; defaults to the clock
        previous_fields (list, optional): the fields of the last package built
            for this sheet, kept in front so a removed or moved column is not a
            new schema to Anki (see kept_fields)

    Returns:
        bytes: the package, ready to be written to a file or handed to a browser
    """
    import sqlite3

    now = int(now if now is not None else time.time())
    is_cloze = bool(sheet_config.cloze_field)
    sheet_id, deck_name, keyed = resolve_identity(sheet_id, deck_name, sheet_config)

    fields = kept_fields(plan.note_type_fields(), previous_fields)
    content = set(plan.content_headers)
    templates = build_templates(plan, sheet_config, is_cloze=is_cloze)
    model_name = f"SheetCards - {deck_name} - {'Cloze' if is_cloze else 'Basic'}"
    mid = model_id(sheet_id, deck_name, is_cloze, keyed)

    root = deck_root_name(deck_name)
    decks = {"1": _deck(1, "Default", now)}

    def deck_id_for(full_name):
        """Registers the deck and every ancestor, the way Anki nests them."""
        parts = full_name.split("::")
        for depth in range(1, len(parts) + 1):
            branch = "::".join(parts[:depth])
            key = str(_stable_id("deck", sheet_id, branch))
            if key not in decks:
                decks[key] = _deck(int(key), branch, now)
        return int(str(_stable_id("deck", sheet_id, full_name)))

    note_rows, card_rows, all_tags = [], [], set()
    seen = set()

    for index, row in enumerate(rows):
        if classify_row(row, plan) != SYNCED:
            continue

        row_id = str(row.get(plan.id_header, "")).strip()
        # Two rows with one ID would be two notes with one id, guid and card ids,
        # and the database refuses the second. The first row is the note — the
        # page's duplicate warning says so — and the rest are left out.
        if row_id in seen:
            continue
        seen.add(row_id)
        # A kept field the sheet no longer has is written empty.
        values = [row_id] + [
            str(row.get(h, "")) if h in content else "" for h in fields[1:]
        ]
        tags = build_tags(row, plan, sheet_config)
        all_tags.update(tags)

        note_id = _stable_id("note", sheet_id, row_id)
        note_rows.append(
            (
                note_id,
                note_guid(sheet_id, row_id),
                mid,
                now,
                -1,
                " " + " ".join(tags) + " " if tags else "",
                FIELD_SEPARATOR.join(values),
                _strip_html(values[0]),
                _checksum(values[0]),
                0,
                "",
            )
        )

        did = deck_id_for(get_subdeck_name(root, deck_path(row, plan, sheet_config)))
        if is_cloze:
            ordinals = cloze_ordinals(row, plan, sheet_config)
            # A cloze row whose declared column holds no deletion would make no
            # cards at all and vanish from the deck, so it keeps card 1 and the
            # sheet's own warning tells the user why it looks empty.
            ordinals = ordinals or [0]
        else:
            ordinals = list(range(len(templates)))

        for ord_ in ordinals:
            card_rows.append(
                (
                    _stable_id("card", sheet_id, row_id, ord_),
                    note_id,
                    did,
                    ord_,
                    now,
                    -1,
                    0,
                    0,
                    index + 1,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    0,
                    "",
                )
            )

    db = sqlite3.connect(":memory:")
    db.executescript(SCHEMA)
    db.execute(
        "insert into col values (1,?,?,?,?,0,-1,0,?,?,?,?,?)",
        (
            now,
            now * 1000,
            now * 1000,
            11,
            json.dumps(_collection_config(mid)),
            json.dumps(
                {str(mid): _model(mid, model_name, fields, templates, is_cloze, now)}
            ),
            json.dumps(decks),
            json.dumps(_deck_config()),
            json.dumps(dict.fromkeys(sorted(all_tags), -1)),
        ),
    )
    db.executemany("insert into notes values (?,?,?,?,?,?,?,?,?,?,?)", note_rows)
    db.executemany(
        "insert into cards values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", card_rows
    )
    db.commit()

    # serialize() hands back the bytes of the database file without a filesystem,
    # which matters because the browser has none.
    collection = db.serialize()
    db.close()

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("collection.anki2", collection)
        # No entries: every media column in this add-on holds a remote URL, so
        # nothing has to travel inside the package.
        package.writestr("media", "{}")
    return buffer.getvalue()
