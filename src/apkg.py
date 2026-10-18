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
from .sheet_config import sort_column
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
    Identity stable, modification time moving — and strictly moving (``_clock``),
    so a second download in the same second still imports as newer.
    """
    digest = hashlib.sha1("::".join(str(p) for p in parts).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") & 0x7FFFFFFFFFFFFFFF


# The last ``mod`` a package was stamped with in this process. Anki overwrites a
# note only when the incoming one is *newer*, so two downloads inside one second
# would leave the second import with nothing to do; each package is therefore at
# least a second after the one before it.
_LAST_NOW = [0]


def _clock():
    now = max(int(time.time()), _LAST_NOW[0] + 1)
    _LAST_NOW[0] = now
    return now


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
    """What a ``name=`` is as an identity: the same deck however it is typed.

    Trimmed, inner whitespace collapsed, NFC (a phone keyboard and a desktop one
    can compose ``ệ`` differently) and case-folded, because Anki itself treats
    deck names that differ only in case as one deck.
    """
    text = unicodedata.normalize("NFC", str(name or ""))
    return " ".join(text.split()).casefold()


def declared_name(sheet_config):
    """The deck name a sheet gives itself with ``name=``, as it is shown, or None.

    Whitespace collapsed and nothing else: the add-on names its deck with this
    exact string too (deck_manager), so the two never disagree about where a
    named sheet's cards live.
    """
    named = getattr(sheet_config, "deck_name", None)
    if named and deck_identity(named):
        return " ".join(str(named).split())
    return None


def resolve_identity(sheet_id, deck_name, sheet_config):
    """What a package is keyed by and what its deck is called.

    The sheet's own ``name=`` wins over whatever the page derived from the
    source (a spreadsheet id, a file name), as the identity and as the name —
    so a sheet keeps one deck however it travels.

    Returns:
        tuple: ``(sheet_id, deck_name, keyed)``, ``keyed`` true when the
        identity came from the sheet itself
    """
    named = declared_name(sheet_config)
    if named:
        return f"name:{deck_identity(named)}", named, True
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


def stub_template(name, key_field="ID"):
    """A card template that renders nothing: kept by name, makes no card.

    ``{{^ID}}`` is "only when ID is empty", and ID never is. Anki accepts it as a
    template (it references a field), makes no card from it for a new note, and
    lists the cards it already made as empty, so Tools → Empty Cards removes
    them — checked in real Anki with its default import options.
    """
    body = f"{{{{^{key_field}}}}}{{{{{key_field}}}}}{{{{/{key_field}}}}}"
    return {"name": name, "qfmt": body, "afmt": body, "stub": True}


def kept_templates(current, previous=(), key_field="ID"):
    """The card templates, given the names the last package of this sheet had.

    A template the sheet no longer makes — ``reverse`` taken out — would be a
    new schema to Anki, so every note would *conflict*; and even merged, Anki
    keeps the old template and goes on showing its cards. Kept as a stub under
    the same name at the same place instead, the note type is unchanged to
    Anki, the import updates, and the cards it made become empty cards for
    Tools → Empty Cards. A template the sheet adds is appended (that one is a
    schema change, and the merge notice says so).
    """
    previous = [n for n in previous or [] if isinstance(n, str)]
    if not previous or not current or previous[0] != current[0]["name"]:
        return list(current)
    by_name = {spec["name"]: spec for spec in current}
    out = [
        by_name.pop(name, None) or stub_template(name, key_field) for name in previous
    ]
    return out + [spec for spec in current if spec["name"] in by_name]


def _templates(plan, sheet_config, previous_templates=()):
    is_cloze = bool(sheet_config.cloze_field)
    current = build_templates(plan, sheet_config, is_cloze=is_cloze)
    if is_cloze:
        # One template, and extra templates on a cloze note type make no cards.
        return current
    return kept_templates(current, previous_templates, plan.note_type_fields()[0])


def note_type_shape(
    plan, sheet_config, previous_fields=(), previous_templates=(), previous_sort=None
):
    """What Anki compares a note type by: its kind, fields and template names.

    ``stubs`` names the kept templates that make no card (kept_templates).
    ``sort`` is the sort field the package carries — not part of what Anki
    compares, but remembered so the next package keeps it (sort_index).
    """
    is_cloze = bool(sheet_config.cloze_field)
    templates = _templates(plan, sheet_config, previous_templates)
    fields = kept_fields(plan.note_type_fields(), previous_fields)
    sortf = sort_index(fields, sheet_config, plan.content_headers, previous_sort)
    return {
        "kind": "cloze" if is_cloze else "basic",
        "fields": fields,
        "sort": fields[sortf],
        "templates": [spec["name"] for spec in templates],
        "stubs": [spec["name"] for spec in templates if spec.get("stub")],
    }


def shape_code(shape):
    """A note type's shape as the short code a sheet carries in ``shape=``.

    The kind (``b`` Basic, ``c`` Cloze), four hex digits of the field list and two
    of the card template names — split so the page can tell a changed column
    from a changed card template (``reverse``) without the lists themselves.
    """

    def digest(parts, n):
        return hashlib.sha1("\x1f".join(parts).encode()).hexdigest()[:n]

    kind = "c" if shape.get("kind") == "cloze" else "b"
    return (
        kind
        + digest(shape.get("fields", []), 4)
        + digest(shape.get("templates", []), 2)
    )


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


# What a shape remembered before it carried a sort field: the package was built
# under the old rule (the column a `sort` key named, else field 0).
OLD_SORT_RULE = ""


def sort_index(fields, sheet_config, content_headers=None, previous_sort=None):
    """The field Anki lists and sorts notes by: the first real column, else 0.

    The same rule the add-on applies (templates_and_definitions.apply_sort_field),
    so a package lists ``apple, book`` in the browser rather than ``w01, w02``.
    ``content_headers`` is the sheet's own columns, because ``fields`` may lead
    with columns an earlier package had and this sheet no longer does.

    ``previous_sort`` is the sort field of the last package this device built for
    the sheet (its shape's ``sort``), :data:`OLD_SORT_RULE` for one built before
    shapes recorded it, None for a sheet never packaged here. A sheet packaged
    before keeps its sort field, because a package whose sort field differs from
    the collection's has its notes skipped as *duplicates* on the next import
    with Anki's default options: Anki rewrites every note when a note type's sort
    field changes, which makes them newer than the package. Verified in real
    Anki 25.07 — the import after that one updates again, but an import that
    silently changes nothing is what makes people stop trusting re-import.
    """
    if previous_sort == OLD_SORT_RULE:
        header = getattr(sheet_config, "legacy_sort_field", None)
    elif previous_sort is not None:
        header = previous_sort
    else:
        header = getattr(sheet_config, "sort_field", None) or sort_column(
            list(content_headers if content_headers is not None else fields[1:]),
            sheet_config,
        )
    return fields.index(header) if header and header in fields else 0


def _model(mid, name, fields, templates, is_cloze, now, sortf=0):
    return {
        "id": mid,
        "name": name,
        "type": MODEL_CLOZE if is_cloze else MODEL_STANDARD,
        "mod": now,
        "usn": -1,
        "sortf": sortf,
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
    sheet_id,
    deck_name,
    plan,
    sheet_config,
    rows,
    now=None,
    previous_fields=(),
    previous_templates=(),
    previous_sort=None,
):
    """Builds an ``.apkg`` from the rows of one sheet.

    Args:
        sheet_id (str): what the page keyed the source by (a spreadsheet id, a
            file name); the sheet's own ``name=`` replaces it
        deck_name (str): the deck's own name, without the ``SheetCards`` root;
            the sheet's own ``name=`` replaces it
        plan (ColumnPlan): the sheet's column roles
        sheet_config (SheetConfig): the parsed settings row
        rows (list[dict]): rows keyed by header, already media-rewritten
        now (int, optional): the timestamp to stamp; defaults to the clock
        previous_fields (list, optional): the fields of the last package built
            for this sheet, kept in front so a removed or moved column is not a
            new schema to Anki (see kept_fields)
        previous_templates (list, optional): that package's template names, so a
            template taken out stays as a stub (see kept_templates)
        previous_sort (str, optional): that package's sort field (see sort_index)

    Returns:
        bytes: the package, ready to be written to a file or handed to a browser
    """
    import sqlite3

    now = int(now) if now is not None else _clock()
    is_cloze = bool(sheet_config.cloze_field)
    sheet_id, deck_name, keyed = resolve_identity(sheet_id, deck_name, sheet_config)

    fields = kept_fields(plan.note_type_fields(), previous_fields)
    sortf = sort_index(fields, sheet_config, plan.content_headers, previous_sort)
    content = set(plan.content_headers)
    templates = _templates(plan, sheet_config, previous_templates)
    model_name = f"SheetCards - {deck_name} - {'Cloze' if is_cloze else 'Basic'}"
    mid = model_id(sheet_id, deck_name, is_cloze, keyed)

    root = deck_root_name(deck_name, named=keyed)
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
                _strip_html(values[sortf]),
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
            ordinals = [i for i, spec in enumerate(templates) if not spec.get("stub")]

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
                {
                    str(mid): _model(
                        mid, model_name, fields, templates, is_cloze, now, sortf
                    )
                }
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
