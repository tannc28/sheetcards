"""Reading an Anki package (.apkg / .colpkg) back into sheets.

A shared deck downloaded from AnkiWeb, or one exported from somebody's Anki, is
turned into what this project calls a sheet: one per note type, the note type's
fields as the columns, so the learner can edit it in Create sheet and make a
deck of it again. It is the reverse of ``apkg.build_package`` and runs in the
same places (the browser through Pyodide, and the suite).

What a sheet gets from each note:

- ``ID``: the note's guid. A stable key for the row, nothing more — a package
  made from the sheet derives its own guids, so it does not update the notes
  the shared deck made; it makes its own.
- one column per field, named as the field is (a field whose name a sheet
  reserves — ``ID``, ``TAGS``, ``SYNC``, ``SUBDECK n`` — gets `` (Anki)`` added,
  or it would stop being a field);
- ``SUBDECK 1..n``: the deck the note's first card is in, below the deck every
  note shares, which becomes the sheet's ``name=``;
- ``TAGS``: the note's tags, when any note has one.

The settings row says what the note type said, as far as a sheet can: which
field is on the front, the cloze field, a type-in answer, a reversed card.

**Formatting.** A field is HTML. Bold, italic, underline, sub/superscript and
line breaks are kept (``<strong>``/``<em>`` written as ``<b>``/``<i>``); every
other tag is taken out and its text kept, block ends (``</div>``, ``</p>``,
``</li>``) become ``<br>``. Entities are decoded to the characters they stand
for, except ``<`` and ``>``, which stay escaped so a field cannot turn into a tag.

**Media cannot come along.** Pictures and sounds are files inside the package,
and a sheet can only point at an address on the web. ``<img>``, ``<audio>``,
``<video>`` and ``[sound:…]`` are removed and counted, and the page says how many.

**The new package format** (Anki 2.1.50+, ``collection.anki21b``) is
zstd-compressed, which the standard library cannot read. Such a package also
carries a ``collection.anki2`` holding a single "Please update to the latest
Anki version" note for older Ankis; that case raises ``NewFormatError`` so the
page can say how to export one this can read (Export → Anki Deck Package,
"Support older Anki versions").

Part of the **pure layer**: standard library only.
"""

import html
import io
import json
import re
import sqlite3
import tempfile
import zipfile
from html.parser import HTMLParser

PACKAGE_SUFFIXES = (".apkg", ".colpkg")

# The note Anki writes into collection.anki2 for an Anki too old to read the
# real collection beside it.
_PLACEHOLDER = "please update to the latest anki version"

_ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"

# Reserved headers a field may not be called (column_model's, matched the same
# way: case-insensitive, whitespace collapsed).
_RESERVED = re.compile(r"^(id|sync|tags|subdeck\s*\d+)$")

# Field references in a template that are not fields.
_SPECIAL = {"frontside", "tags", "deck", "subdeck", "card", "cardflag", "type"}

_KEPT = {
    "b": "b",
    "strong": "b",
    "i": "i",
    "em": "i",
    "u": "u",
    "sub": "sub",
    "sup": "sup",
}
_BLOCK = {"div", "p", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote"}
_MEDIA = {"img": "images", "audio": "audio", "video": "audio"}
_SKIP = {"script", "style"}


class PackageError(ValueError):
    """A file named .apkg/.colpkg that cannot be read as one."""


class NewFormatError(PackageError):
    """A package in Anki's new (zstd) format, which this cannot read."""


# ---------------------------------------------------------------------------
# A field, as a sheet's cell
# ---------------------------------------------------------------------------

_SOUND = re.compile(r"\[sound:[^\]]*\]")


class _Cell(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.out = []
        self.skip = 0
        self.media = {"images": 0, "audio": 0}

    def _br(self):
        if self.out and self.out[-1] != "<br>":
            self.out.append("<br>")

    def handle_starttag(self, tag, attrs):
        if tag in _SKIP:
            self.skip += 1
        elif tag in _MEDIA:
            self.media[_MEDIA[tag]] += 1
        elif tag == "br":
            self._br()
        elif tag in _KEPT:
            self.out.append(f"<{_KEPT[tag]}>")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in _SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag in _KEPT:
            self.out.append(f"</{_KEPT[tag]}>")
        elif tag in _BLOCK:
            self._br()

    def _text(self, text):
        if not self.skip and text:
            # Decoded text, re-escaped only where it could become markup.
            self.out.append(text.replace("<", "&lt;").replace(">", "&gt;"))

    def handle_data(self, data):
        self._text(data)

    def handle_entityref(self, name):
        self._text(html.unescape(f"&{name};"))

    def handle_charref(self, name):
        self._text(html.unescape(f"&#{name};"))


def field_text(value):
    """``(cell, media)``: one field as a sheet cell, and what was taken out of it."""
    value = str(value or "")
    sounds = len(_SOUND.findall(value))
    parser = _Cell()
    parser.feed(_SOUND.sub(" ", value))
    parser.close()
    parser.media["audio"] += sounds
    text = re.sub(r"\s+", " ", "".join(parser.out).replace("\xa0", " "))
    text = re.sub(r"\s*<br>\s*", "<br>", text)
    text = re.sub(r"^(?:<br>)+|(?:<br>)+$", "", text)
    # A tag left holding nothing ("<b></b>", what a removed picture leaves).
    text = re.sub(r"<(b|i|u|sub|sup)>\s*</\1>", "", text).strip()
    return text, parser.media


# ---------------------------------------------------------------------------
# The package
# ---------------------------------------------------------------------------


def _open_collection(raw):
    if raw[:4] == _ZSTD_MAGIC:
        raise NewFormatError("This package was exported by a newer Anki")
    db = sqlite3.connect(":memory:")
    try:
        db.deserialize(raw)
    except (AttributeError, sqlite3.Error):
        # deserialize needs SQLite built with it; a temporary file always works.
        with tempfile.NamedTemporaryFile(suffix=".anki2", delete=False) as handle:
            handle.write(raw)
        db = sqlite3.connect(handle.name)
    try:
        db.execute("select 1 from col").fetchone()
    except sqlite3.DatabaseError as error:
        raise PackageError("This is not an Anki package") from error
    return db


def _collection(data):
    try:
        package = zipfile.ZipFile(io.BytesIO(bytes(data)))
    except zipfile.BadZipFile as error:
        raise PackageError("This is not an Anki package") from error
    names = set(package.namelist())
    newer = "collection.anki21b" in names
    for inner in ("collection.anki21", "collection.anki2"):
        if inner in names:
            db = _open_collection(package.read(inner))
            if _is_placeholder(db):
                raise NewFormatError("This package was exported by a newer Anki")
            return db
    if newer:
        raise NewFormatError("This package was exported by a newer Anki")
    raise PackageError("This is not an Anki package")


def _is_placeholder(db):
    rows = db.execute("select flds from notes limit 2").fetchall()
    return len(rows) == 1 and rows[0][0].lower().startswith(_PLACEHOLDER)


def _refs(template):
    """The fields a template shows, and the ones it asks to be typed or clozed."""
    shown, typed, clozed = [], [], []
    for ref in re.findall(r"\{\{([^{}]+)\}\}", template or ""):
        ref = ref.strip()
        if ref[:1] in "#^/!":
            continue
        parts = [p.strip() for p in ref.split(":")]
        name = parts[-1]
        filters = [p.lower() for p in parts[:-1]]
        if name.lower() in _SPECIAL or name.lower().startswith("tts "):
            continue
        if "type" in filters:
            typed.append(name)
            continue
        if "cloze" in filters:
            clozed.append(name)
        shown.append(name)
    return shown, typed, clozed


def _column_name(name, taken):
    text = " ".join(str(name).split()) or "Field"
    if _RESERVED.match(text.lower()):
        text = f"{text} (Anki)"
    base, n = text, 2
    while text.lower() in taken:
        text, n = f"{base} {n}", n + 1
    taken.add(text.lower())
    return text


def _common_root(paths):
    """The levels every deck path starts with."""
    if not paths:
        return []
    root = list(paths[0])
    for path in paths[1:]:
        n = 0
        while n < len(root) and n < len(path) and root[n].lower() == path[n].lower():
            n += 1
        root = root[:n]
    return root


def _settings(fields, columns, model):
    """The settings row's cells for one note type, as far as a sheet can say it."""
    templates = model.get("tmpls") or []
    first = templates[0] if templates else {}
    shown, typed, clozed = _refs(first.get("qfmt", ""))
    back, _, _ = _refs(first.get("afmt", ""))
    is_cloze = model.get("type") == 1
    cells = {}
    for i, (field, column) in enumerate(zip(fields, columns, strict=True)):
        keys = []
        if (
            is_cloze
            and field in clozed
            and not any("cloze" in k for k in cells.values())
        ):
            keys.append("cloze")
        elif field in shown and i > 0:
            keys.append("side=front")
        elif field not in shown and i == 0 and field in back:
            keys.append("side=back")
        elif field not in shown and field not in back and field not in typed:
            keys.append("side=hide")
        if field in typed and not is_cloze:
            keys.append("type")
        if keys:
            cells[column] = "; ".join(keys)
    # Two templates, the second asking the other way round — unless it is shown
    # only when some other field is filled in ("optional reversed card").
    reverse = False
    if not is_cloze and len(templates) == 2:
        second = templates[1].get("qfmt", "")
        shown2, _, _ = _refs(second)
        gates = re.findall(r"\{\{#([^{}]+)\}\}", second)
        reverse = bool(shown2) and all(g.strip() in shown2 for g in gates)
    return cells, reverse


def read_package(data, name=""):
    """The sheets in an .apkg/.colpkg.

    Returns:
        list of dicts ``{"name", "rows", "notes", "media"}``, one per note type
        that has notes, in the order the note types were first used: ``rows`` is
        the sheet (header row, settings row, one row per note) and ``media`` the
        pictures and sounds that could not come along (``{"images", "audio"}``).
    """
    db = _collection(data)
    try:
        models_json, decks_json = db.execute("select models, decks from col").fetchone()
        models = json.loads(models_json or "{}")
        decks = {
            int(k): str(v.get("name", "")).replace("\x1f", "::")
            for k, v in json.loads(decks_json or "{}").items()
        }
        first_deck = dict(
            db.execute(
                "select nid, did from cards c where ord = "
                "(select min(ord) from cards where nid = c.nid)"
            ).fetchall()
        )
        notes = db.execute(
            "select id, guid, mid, tags, flds from notes order by id"
        ).fetchall()
    finally:
        db.close()

    def path_of(nid):
        deck = decks.get(first_deck.get(nid), "")
        return [level for level in deck.split("::") if level.strip()]

    paths = [path_of(nid) for nid, *_ in notes]
    root = _common_root([p for p in paths if p])
    if [lvl.lower() for lvl in root] == ["default"]:
        root = []

    by_model = {}
    for (nid, guid, mid, tags, flds), path in zip(notes, paths, strict=True):
        if str(mid) not in models:
            continue
        by_model.setdefault(str(mid), []).append((guid, tags, flds, path[len(root) :]))

    stem = re.sub(r"\.(apkg|colpkg)$", "", str(name), flags=re.I).strip()
    deck_name = "::".join(root) if root else stem
    several = len(by_model) > 1
    sheets, taken_tabs = [], set()
    for mid, items in by_model.items():
        model = models[mid]
        fields = [
            f["name"] for f in sorted(model.get("flds", []), key=lambda f: f["ord"])
        ]
        taken = {"id", "tags", "sync"}
        columns = [_column_name(f, taken) for f in fields]
        depth = max((len(p) for *_, p in items), default=0)
        has_tags = any(str(t).strip() for _, t, _, _ in items)
        header = ["ID", *columns]
        header += [f"SUBDECK {n}" for n in range(1, depth + 1)]
        if has_tags:
            header.append("TAGS")

        cells, reverse = _settings(fields, columns, model)
        label = str(model.get("name") or "Notes").strip() or "Notes"
        named = f"{deck_name} ({label})" if several and deck_name else deck_name
        named = re.sub(r"[;\t\r\n]+", " ", named).strip()[:100].strip()
        marker = "#config"
        if named:
            marker += f" name={named}"
        if reverse:
            marker += "; reverse" if named else " reverse"
        settings = [marker, *(cells.get(c, "") for c in columns)]
        settings += [""] * (len(header) - len(settings))

        media = {"images": 0, "audio": 0}
        rows = [header, settings]
        for guid, tags, flds, path in items:
            values = str(flds).split("\x1f")
            values += [""] * (len(fields) - len(values))
            row = [guid]
            for value in values[: len(fields)]:
                text, lost = field_text(value)
                row.append(text)
                for kind, count in lost.items():
                    media[kind] += count
            row += path + [""] * (depth - len(path))
            if has_tags:
                row.append(", ".join(str(tags).split()))
            rows.append(row)

        tab, n = label, 2
        while tab.lower() in taken_tabs:
            tab, n = f"{label} {n}", n + 1
        taken_tabs.add(tab.lower())
        sheets.append({"name": tab, "rows": rows, "notes": len(items), "media": media})

    if not sheets:
        raise PackageError("This Anki package has no notes in it")
    return sheets
