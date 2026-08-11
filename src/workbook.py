"""Reading a spreadsheet file, so one file can hold more than one deck.

A Google Sheets *file* holds several *sheets* — the tabs along the bottom — and
people keep a deck per sheet. The TSV export the add-on downloads can only ever
return one of them, and there is no official way to ask for a named sheet: the
`gviz` endpoint that takes a name folds the header row and the settings row into
a single line, so `ID` arrives as `ID #config` and every column name is wrong.
Downloading the whole file is what is left, and this turns it into the TSV the
add-on's parser already expects. From there nothing is special-cased — the column
roles, the settings row, the warnings, the deck paths and the cards all come from
the same code that reads a single-sheet download.

It also reads a file someone uploads to the preview site, which is the same job.

The reader is written against the standard library rather than openpyxl. Pyodide
does not ship openpyxl, so using it would mean the preview site fetching a wheel
from PyPI at load time — a second CDN to depend on. A spreadsheet file is a ZIP
of XML, and the part of it a page of flashcards uses is a small part.

This module is part of the **pure layer**: it imports nothing but the standard
library, so it runs unchanged inside Anki and in the browser. Do not give it an
Anki, Qt or `compat` import.
"""

import csv
import datetime
import io
import json
import re
import xml.etree.ElementTree as ET
import zipfile

# A workbook mixes three namespaces, and two of them are called "relationships".
# The one on a `r:id` attribute is not the one on a `.rels` file's elements.
MAIN = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
DOC_REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

WORKBOOK_SUFFIXES = (".xlsx", ".xlsm")

# Excel counts days from an epoch two days before 1900-01-01 because it believes
# 1900 was a leap year, which it was not. Anchoring here reproduces the quirk
# rather than fighting it. A workbook can also ask for the 1904 system instead.
_EPOCH_1900 = datetime.datetime(1899, 12, 30)
_EPOCH_1904 = datetime.datetime(1904, 1, 1)

# The built-in number formats that mean date or time (ECMA-376 §18.8.30).
_BUILTIN_DATE_FORMATS = frozenset(range(14, 23)) | frozenset(range(45, 48))


class WorkbookError(Exception):
    """A file this page cannot read, described in a way a person can act on."""


# ---------------------------------------------------------------------------
# Cell values
# ---------------------------------------------------------------------------


def _is_date_format(code):
    """Whether a custom number format code renders its value as a date or time."""
    code = re.sub(r'"[^"]*"', "", code)  # literal text: "on" is not a month
    code = re.sub(r"\[[^\]]*\]", "", code)  # colour and locale: [Red] is not a day
    code = re.sub(r"\\.", "", code)  # an escaped single character
    return bool(re.search(r"[ymdhs]", code, re.I))


def _date_styles(book):
    """The indexes into cellXfs whose number format makes a cell a date."""
    try:
        root = ET.fromstring(book.read("xl/styles.xml"))
    except KeyError:
        return frozenset()

    custom = {
        int(fmt.get("numFmtId", -1)): fmt.get("formatCode", "")
        for fmt in root.iter(f"{MAIN}numFmt")
    }
    formats = root.find(f"{MAIN}cellXfs")
    if formats is None:
        return frozenset()

    return frozenset(
        index
        for index, xf in enumerate(formats)
        if int(xf.get("numFmtId", 0)) in _BUILTIN_DATE_FORMATS
        or _is_date_format(custom.get(int(xf.get("numFmtId", 0)), ""))
    )


def _date_text(raw, epoch):
    try:
        serial = float(raw)
    except ValueError:
        return raw
    # Serials below 60 predate the phantom 29 February 1900 and so escaped the
    # off-by-one the epoch above compensates for.
    if epoch is _EPOCH_1900 and serial < 60:
        serial += 1

    moment = epoch + datetime.timedelta(seconds=round(serial * 86400))
    if serial < 1:
        return moment.strftime("%H:%M:%S")
    if moment.hour or moment.minute or moment.second:
        return moment.strftime("%Y-%m-%d %H:%M:%S")
    return moment.strftime("%Y-%m-%d")


def _run_text(node):
    """The text of a shared string or an inline one, formatting runs and all.

    Ruby annotations (`rPh`) hold `t` elements of their own and are not part of
    the value, so the children are taken by name instead of swept up with iter().
    """
    parts = [node.text or "" for node in node.findall(f"{MAIN}t")]
    for run in node.findall(f"{MAIN}r"):
        parts += [node.text or "" for node in run.findall(f"{MAIN}t")]
    return "".join(parts)


def _shared_strings(book):
    try:
        root = ET.fromstring(book.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return [_run_text(item) for item in root.findall(f"{MAIN}si")]


def _cell_text(cell, shared, date_styles, epoch):
    kind = cell.get("t", "n")

    if kind == "inlineStr":
        inline = cell.find(f"{MAIN}is")
        return _run_text(inline) if inline is not None else ""

    value = cell.find(f"{MAIN}v")
    if value is None or value.text is None:
        return ""
    raw = value.text

    if kind == "s":
        index = int(raw)
        return shared[index] if 0 <= index < len(shared) else ""
    if kind == "b":
        # Written back the way a Google Sheets TSV export writes it, so the SYNC
        # column reads the same whether the sheet arrived as a link or a file.
        return "FALSE" if raw.strip() in ("0", "") else "TRUE"
    if kind in ("str", "e"):
        return raw
    if int(cell.get("s", 0)) in date_styles:
        return _date_text(raw, epoch)
    return _number_text(raw)


def _number_text(raw):
    """A numeric cell written the way an export writes it.

    Google stores a whole number as `<v>1.0</v>` but exports it as "1", and the
    ID column is the key a note is matched by — so leaving the file's own literal
    alone would give an uploaded workbook different note ids than the very same
    rows synced through the add-on. A fractional value keeps its literal, which
    says what the file says without a round trip through float formatting.
    """
    try:
        number = float(raw)
    except ValueError:
        return raw
    # Past 2**53 a float no longer holds every integer, so int() would invent
    # digits rather than drop a redundant ".0".
    if number.is_integer() and abs(number) < 2**53:
        return str(int(number))
    return raw


# ---------------------------------------------------------------------------
# The grid
# ---------------------------------------------------------------------------


def _column_index(ref):
    """`"AB12"` → 27. None when the cell carries no reference."""
    letters = re.match(r"([A-Z]+)", ref or "")
    if not letters:
        return None
    index = 0
    for char in letters.group(1):
        index = index * 26 + (ord(char) - 64)
    return index - 1


def _tabs(book):
    """(name, path) for every visible sheet, in the order the file lists them.

    A hidden sheet is left out. Someone hides a sheet to get it out of the way,
    and a deck appearing in Anki for it would be the opposite of that.
    """
    try:
        root = ET.fromstring(book.read("xl/workbook.xml"))
        rels = {
            rel.get("Id"): rel.get("Target", "")
            for rel in ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))
        }
    except KeyError as missing:
        raise WorkbookError(f"This is not a workbook: {missing} is missing.")

    tabs = []
    for sheet in root.iter(f"{MAIN}sheet"):
        target = rels.get(sheet.get(f"{DOC_REL}id"), "")
        if not target or sheet.get("state", "visible") != "visible":
            continue
        path = target[1:] if target.startswith("/") else "xl/" + target
        tabs.append((sheet.get("name", "Sheet"), path))
    if not tabs:
        raise WorkbookError("This workbook has no sheets in it.")
    return tabs


def _epoch(book):
    root = ET.fromstring(book.read("xl/workbook.xml"))
    properties = root.find(f"{MAIN}workbookPr")
    uses_1904 = properties is not None and properties.get("date1904") in ("1", "true")
    return _EPOCH_1904 if uses_1904 else _EPOCH_1900


def _grid(book, path, shared, date_styles, epoch):
    """The tab as a list of rows of strings, gaps filled in.

    Rows and cells are both addressed rather than ordered — a row of three cells
    can be columns A, D and Z — so a sheet read positionally comes out sheared.
    """
    rows = []
    for row in ET.fromstring(book.read(path)).iter(f"{MAIN}row"):
        number = int(row.get("r", len(rows) + 1))
        while len(rows) < number - 1:
            rows.append([])

        cells = []
        for cell in row.findall(f"{MAIN}c"):
            at = _column_index(cell.get("r"))
            if at is None:
                at = len(cells)
            while len(cells) <= at:
                cells.append("")
            cells[at] = _cell_text(cell, shared, date_styles, epoch)
        rows.append(cells)
    return rows


def _trimmed(rows):
    """The grid cut back to the cells that hold something.

    A spreadsheet remembers a used range far wider and taller than its content —
    formatting a whole column is enough — and every empty column would otherwise
    arrive as a note field named "" and every empty row as a ghost row.
    """
    while rows and not any(value.strip() for value in rows[-1]):
        rows.pop()

    width = 0
    for row in rows:
        for index, value in enumerate(row):
            if value.strip():
                width = max(width, index + 1)
    return [row[:width] + [""] * (width - len(row)) for row in rows]


def _tsv(rows):
    """Rows as TSV, written the way parse_tsv_data reads it.

    csv.writer quotes a cell holding a tab or a newline, and parse_tsv_data runs
    csv.reader over the text, so a multi-line answer survives the round trip
    instead of being flattened or splitting the row in two.
    """
    out = io.StringIO()
    csv.writer(out, delimiter="\t", lineterminator="\n").writerows(rows)
    return out.getvalue()


# ---------------------------------------------------------------------------
# What the add-on and the page call
# ---------------------------------------------------------------------------


def _read_workbook(data, index):
    """(sheet names, chosen sheet's name, that sheet as TSV)."""
    with zipfile.ZipFile(io.BytesIO(data)) as book:
        sheets = _tabs(book)
        if not 0 <= index < len(sheets):
            index = 0
        rows = _grid(
            book,
            sheets[index][1],
            _shared_strings(book),
            _date_styles(book),
            _epoch(book),
        )
    return [name for name, _ in sheets], sheets[index][0], _tsv(_trimmed(rows))


def sheet_names(data):
    """The visible sheets in a spreadsheet file, in the order it lists them."""
    with zipfile.ZipFile(io.BytesIO(bytes(data))) as book:
        return [name for name, _ in _tabs(book)]


def sheet_tsv(data, name):
    """One named sheet as TSV.

    Named rather than numbered because a deck remembers which sheet it syncs, and
    a sheet dragged to a different position in the file is still the same sheet.

    Raises:
        WorkbookError: when the file holds no sheet by that name — which is what
            a sheet renamed or deleted since the deck was connected looks like,
            and is worth saying rather than silently syncing a different one.
    """
    names = sheet_names(data)
    if name not in names:
        raise WorkbookError(
            f"This file has no sheet called {name!r}. It has: "
            + ", ".join(repr(n) for n in names)
            + ". A sheet renamed in Google Sheets has to be connected again."
        )
    return _read_workbook(bytes(data), names.index(name))[2]


def read_upload(data, name, index=0):
    """A dropped file as JSON: its tab names, and the chosen tab as TSV.

    `tabs` is empty for a file that holds a single grid, which is how the page
    knows not to offer a tab picker.
    """
    data = bytes(data)
    lower = name.lower()

    if lower.endswith(WORKBOOK_SUFFIXES):
        if data[:2] != b"PK":
            raise WorkbookError(
                "This file is named .xlsx but is not one. If it came out of an "
                "older Excel, open it and choose Save As → .xlsx."
            )
        names, chosen, tsv = _read_workbook(data, index)
        return json.dumps(
            {"tabs": names if len(names) > 1 else [], "tab": chosen, "tsv": tsv},
            ensure_ascii=False,
        )

    if lower.endswith(".xls"):
        raise WorkbookError(
            "This is the old .xls format, which this page cannot read. Open it "
            "and choose Save As → .xlsx, or upload it to Google Sheets."
        )

    # utf-8-sig rather than utf-8: a spreadsheet exported on Windows leads with a
    # byte order mark, and a BOM stuck to the first header would hide the ID
    # column. The add-on's own `clean()` strips it too, but only from headers.
    text = data.decode("utf-8-sig", errors="replace")
    if lower.endswith(".csv"):
        text = _tsv(list(csv.reader(io.StringIO(text))))
    return json.dumps({"tabs": [], "tab": "", "tsv": text}, ensure_ascii=False)
