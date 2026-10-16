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

It also reads a file someone uploads to the preview site, which is the same job,
and writes one (``build_xlsx``): the example workbook is built with it, and so is
the .xlsx that Create sheet saves in the browser.

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
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from xml.sax.saxutils import escape as _escape
from xml.sax.saxutils import quoteattr as _quoteattr

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


def sheet_tsv_by_index(data, index=0):
    """One sheet by position — used when nothing has named one yet."""
    return _read_workbook(bytes(data), index)[2]


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

    text, encoding = decode_text(data)
    delimiter = sniff_delimiter(text)
    if delimiter != "\t":
        text = _tsv(list(csv.reader(io.StringIO(text), delimiter=delimiter)))
    out = {"tabs": [], "tab": "", "tsv": text}
    if encoding not in ("utf-8", "utf-16"):
        # Read, but not in the encoding the page assumes: the page says so,
        # because a letter guessed wrong is a word learnt wrong.
        out["encoding"] = encoding
    return json.dumps(out, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Text files: which encoding, which separator
# ---------------------------------------------------------------------------
#
# A .csv saved by Excel on a Vietnamese Windows is not the file the rest of the
# world calls CSV. "CSV (Comma delimited)" writes the ANSI code page — cp1258,
# where a tone mark is a separate combining character — and separates cells
# with ";" whenever the region's list separator is ";". "Unicode Text" writes
# UTF-16 with tabs. "CSV UTF-8" is the only one that is what it says. Each is
# read as what it is, and a guess is reported rather than made silently.

# Letters only Vietnamese writes, and the five combining tone marks cp1258
# spells a toned vowel with. Seeing one means the cp1258 reading is the right one.
_VIETNAMESE = re.compile("[ăâđơưĂÂĐƠƯ\u0300\u0301\u0303\u0309\u0323]")


class _Undecodable(Exception):
    pass


def decode_text(data):
    """(text, encoding) for the bytes of a text file.

    UTF-16 by its byte order mark (or by the zero bytes every ASCII character
    carries in it), UTF-8 with or without a BOM, and otherwise one of the two
    Windows code pages a spreadsheet here is likely to have been saved in. A
    file none of them reads raises rather than coming out full of "\ufffd".
    """
    data = bytes(data)
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16"), "utf-16"
    sample = data[:400]
    if len(sample) >= 4:
        odd, even = sample[1::2].count(0), sample[0::2].count(0)
        unmarked = (
            "utf-16-le"
            if odd > len(sample) // 4 and not even
            else "utf-16-be" if even > len(sample) // 4 and not odd else None
        )
        if unmarked:
            try:
                return data.decode(unmarked), "utf-16"
            except UnicodeDecodeError:
                pass
    try:
        return data.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        pass
    readings = {}
    for encoding in ("cp1258", "cp1252"):
        try:
            readings[encoding] = data.decode(encoding)
        except UnicodeDecodeError:
            continue
    vietnamese = "cp1258" in readings and _VIETNAMESE.search(readings["cp1258"])
    for encoding in ("cp1258", "cp1252") if vietnamese else ("cp1252", "cp1258"):
        if encoding in readings:
            # NFC: cp1258 writes "ạ" as "a" + a combining dot, and a field
            # that looks the same but compares differently breaks type-in
            # answers and duplicate checks alike.
            return unicodedata.normalize("NFC", readings[encoding]), encoding
    raise WorkbookError(
        "This file is not UTF-8 text and no Windows code page reads it either. "
        "Open it in Excel and choose Save As → CSV UTF-8, then upload that."
    )


def sniff_delimiter(text):
    """Tab, ";" or "," — whichever splits the header row into the most cells.

    Read from the first record only, quotes respected: the header row is where
    a separator shows up with nothing else around it, while a meaning further
    down is free to hold commas. A tie goes to tab, then ";", since a sheet
    using ";" never writes one into a header by accident.
    """
    best, widest = "\t", 1
    for delimiter in ("\t", ";", ","):
        try:
            first = next(csv.reader(io.StringIO(text), delimiter=delimiter), [])
        except csv.Error:
            continue
        if len(first) > widest:
            best, widest = delimiter, len(first)
    return best


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------

# Every entry gets the same timestamp so an unchanged grid rebuilds to a
# byte-identical file. A workbook that churned on every build would show up as a
# binary diff in every commit that touched anything nearby.
_STAMP = (2020, 1, 1, 0, 0, 0)

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" '
    'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.'
    'openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    '<Override PartName="/xl/styles.xml" ContentType="application/vnd.'
    'openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
    "{sheets}"
    "</Types>"
)

# Nothing here is styled, but Excel treats a workbook with no styles part as
# damaged and offers to repair it — and the point of this file is that someone
# can open it, look at the settings row, and copy it. The reader
# above does not need it: it already treats a missing styles.xml as "no cell
# is a date".
_STYLES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
    '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
    '<borders count="1"><border/></borders>'
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>'
    "</cellStyleXfs>"
    '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" '
    'xfId="0"/></cellXfs>'
    "</styleSheet>"
)

_ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
    'relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.'
    'org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"'
    "/></Relationships>"
)


def _column_ref(index):
    """0 → "A", 26 → "AA" — the letters Excel addresses a cell by."""
    letters = ""
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        letters = chr(65 + rest) + letters
    return letters


def _clean(text):
    """XML 1.0 forbids most control characters outright, even escaped."""
    return "".join(ch for ch in text if ch >= " " or ch in "\t\n\r")


def _sheet_xml(rows):
    """A grid as a worksheet part.

    Every cell is written as an inline string. A shared-string table would make
    the file smaller, but a sheet of flashcards is small and an inline string is
    the one cell type that cannot be misread: no number formatting, no date
    serial, no locale — what was written is what the reader gets back.
    """
    out = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/'
        'main"><sheetData>'
    ]
    for r, row in enumerate(rows, start=1):
        cells = []
        for c, value in enumerate(row):
            if not value:
                continue  # an empty cell is an absent cell
            ref = f"{_column_ref(c)}{r}"
            cells.append(
                f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">'
                f"{_escape(_clean(value))}</t></is></c>"
            )
        if cells:
            out.append(f'<row r="{r}">' + "".join(cells) + "</row>")
    out.append("</sheetData></worksheet>")
    return "".join(out)


def _workbook_xml(names):
    sheets = "".join(
        f'<sheet name={_quoteattr(name)} sheetId="{i}" r:id="rId{i}"/>'
        for i, name in enumerate(names, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/'
        f'relationships"><sheets>{sheets}</sheets></workbook>'
    )


def _workbook_rels(count):
    rels = "".join(
        f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/'
        f'officeDocument/2006/relationships/worksheet" '
        f'Target="worksheets/sheet{i}.xml"/>'
        for i in range(1, count + 1)
    )
    # The styles part is reached through a relationship like any other, and it is
    # numbered past the sheets so a sheet's rId stays equal to its position.
    rels += (
        f'<Relationship Id="rId{count + 1}" Type="http://schemas.openxmlformats.'
        'org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
        f'relationships">{rels}</Relationships>'
    )


def build_xlsx(sheets):
    """``{sheet name: rows of text}`` as the bytes of an .xlsx file.

    The writing half of this module, used to build the example workbook and by
    Create sheet to save what was written in the browser. Every cell is text, so
    the file reads back through ``sheet_tsv`` exactly as it went in.

    Raises:
        ValueError: for a sheet name Excel would refuse — longer than 31
            characters, empty, or holding one of ``[]:*?/\\``.
    """
    names = list(sheets)
    bad = [n for n in names if not n or len(n) > 31 or set(n) & set("[]:*?/\\")]
    if bad:
        raise ValueError(
            "a sheet name must be 1-31 characters with none of []:*?/\\ — "
            + ", ".join(repr(n) for n in bad)
        )

    parts = {
        "[Content_Types].xml": _CONTENT_TYPES.format(
            sheets="".join(
                f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.'
                'spreadsheetml.worksheet+xml"/>'
                for i in range(1, len(names) + 1)
            )
        ),
        "_rels/.rels": _ROOT_RELS,
        "xl/workbook.xml": _workbook_xml(names),
        "xl/_rels/workbook.xml.rels": _workbook_rels(len(names)),
        "xl/styles.xml": _STYLES,
    }
    for i, name in enumerate(names, start=1):
        parts[f"xl/worksheets/sheet{i}.xml"] = _sheet_xml(sheets[name])

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as book:
        for name, text in parts.items():
            info = zipfile.ZipInfo(name, date_time=_STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            book.writestr(info, text.encode("utf-8"))
    return buffer.getvalue()


def safe_sheet_name(name, fallback="Sheet1"):
    """A title turned into a name Excel accepts for a sheet: the forbidden
    characters dropped, cut to 31 characters, never empty."""
    cleaned = "".join(ch for ch in str(name) if ch not in "[]:*?/\\").strip()
    return cleaned[:31].strip() or fallback
