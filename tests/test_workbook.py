"""Reading an uploaded workbook — the preview site's one piece of extra Python.

The bar these tests hold it to is not "does it produce something plausible" but
"does it produce what Google's own TSV export would have produced", because the
preview and the add-on have to agree about a sheet. Where they disagree the
preview lies, and a note key is exactly the sort of thing that goes wrong
quietly: an ID read as "1.0" instead of "1" previews perfectly and then syncs
into a second, separate note.

The fixtures are hand-written XML rather than a workbook some library wrote,
because the point is to pin the *shapes a real file uses* — sparse cells,
formatting runs, inline strings, styled dates — not to prove a round trip
through the same assumptions that built the file.
"""

import csv
import io
import json
import zipfile

import pytest

from src import workbook

MAIN = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
DOC_REL = (
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
)
PKG_REL = 'xmlns="http://schemas.openxmlformats.org/package/2006/relationships"'


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def book(sheets, shared=(), styles=None, date1904=False):
    """A workbook holding `sheets`, each a (name, rows-of-XML) pair."""
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as zf:
        zf.writestr(
            "xl/workbook.xml",
            f"<workbook {MAIN} {DOC_REL}>"
            + ('<workbookPr date1904="1"/>' if date1904 else "")
            + "<sheets>"
            + "".join(
                f'<sheet name="{name}" sheetId="{i + 1}" r:id="rId{i + 1}"/>'
                for i, (name, _) in enumerate(sheets)
            )
            + "</sheets></workbook>",
        )
        zf.writestr(
            "xl/_rels/workbook.xml.rels",
            f"<Relationships {PKG_REL}>"
            + "".join(
                f'<Relationship Id="rId{i + 1}" Target="worksheets/sheet{i + 1}.xml"/>'
                for i in range(len(sheets))
            )
            + "</Relationships>",
        )
        for i, (_, rows) in enumerate(sheets):
            zf.writestr(
                f"xl/worksheets/sheet{i + 1}.xml",
                f"<worksheet {MAIN}><sheetData>{rows}</sheetData></worksheet>",
            )
        if shared:
            zf.writestr("xl/sharedStrings.xml", f"<sst {MAIN}>{''.join(shared)}</sst>")
        if styles:
            zf.writestr("xl/styles.xml", f"<styleSheet {MAIN}>{styles}</styleSheet>")
    return out.getvalue()


def one(rows, **kw):
    """A workbook of a single sheet, which is what most of these need."""
    return book([("S", rows)], **kw)


def read(data, name="book.xlsx", index=0):
    return json.loads(workbook.read_upload(data, name, index))


def grid(data, index=0):
    """A workbook's chosen tab, read back as a list of rows of values."""
    return list(csv.reader(io.StringIO(read(data, index=index)["tsv"]), delimiter="\t"))


def cells(rows, **kw):
    """One sheet of cell XML, read back as a list of rows of values."""
    return grid(one(rows, **kw))


def txt(ref, value):
    """A cell holding a literal string, no shared-strings table involved.

    Every cell here carries the reference a real file gives it: a spreadsheet
    addresses its cells rather than ordering them, and reading one positionally
    is a bug that only shows up on a sheet with a gap in it.
    """
    return f'<c r="{ref}" t="inlineStr"><is><t>{value}</t></is></c>'


ONE_SHEET = f'<row r="1">{txt("A1", "ID")}</row>'


# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNamedSheets:
    """How a deck asks for its sheet: by name, because that is what it remembers."""

    def test_the_names_come_back_in_file_order(self):
        data = book([("vocab", ONE_SHEET), ("grammar", ""), ("phrases", "")])
        assert workbook.sheet_names(data) == ["vocab", "grammar", "phrases"]

    def test_a_sheet_is_fetched_by_name_not_position(self):
        """A sheet dragged to a new position in the file is the same sheet."""
        data = book(
            [
                ("vocab", f'<row r="1">{txt("A1", "first")}</row>'),
                ("grammar", f'<row r="1">{txt("A1", "second")}</row>'),
            ]
        )
        assert workbook.sheet_tsv(data, "grammar").strip() == "second"

    def test_a_missing_sheet_says_which_ones_exist(self):
        """This is what a sheet renamed since the deck was connected looks like."""
        data = book([("vocab", ONE_SHEET), ("grammar", "")])
        with pytest.raises(workbook.WorkbookError) as raised:
            workbook.sheet_tsv(data, "vocabulary")
        assert "'vocab'" in str(raised.value)
        assert "connected again" in str(raised.value)

    def test_a_hidden_sheet_is_not_offered(self):
        """Hiding a sheet is how you put it away; a deck for it is the opposite."""
        out = io.BytesIO()
        with zipfile.ZipFile(out, "w") as zf:
            zf.writestr(
                "xl/workbook.xml",
                f"<workbook {MAIN} {DOC_REL}><sheets>"
                '<sheet name="vocab" sheetId="1" r:id="rId1"/>'
                '<sheet name="scratch" sheetId="2" state="hidden" r:id="rId2"/>'
                "</sheets></workbook>",
            )
            zf.writestr(
                "xl/_rels/workbook.xml.rels",
                f"<Relationships {PKG_REL}>"
                '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/>'
                '<Relationship Id="rId2" Target="worksheets/sheet2.xml"/>'
                "</Relationships>",
            )
            for i in (1, 2):
                zf.writestr(
                    f"xl/worksheets/sheet{i}.xml",
                    f"<worksheet {MAIN}><sheetData>{ONE_SHEET}</sheetData></worksheet>",
                )
        assert workbook.sheet_names(out.getvalue()) == ["vocab"]


@pytest.mark.unit
class TestTabs:
    def test_tabs_come_back_in_workbook_order(self):
        data = book([("First", ONE_SHEET), ("Second", ""), ("Third", "")])
        assert read(data)["tabs"] == ["First", "Second", "Third"]

    def test_a_single_tab_offers_no_picker(self):
        """An empty list is how the page knows not to draw a tab select."""
        assert read(one(ONE_SHEET))["tabs"] == []
        assert read(one(ONE_SHEET))["tab"] == "S"

    def test_the_index_chooses_the_tab(self):
        data = book(
            [
                ("A", f'<row r="1">{txt("A1", "first")}</row>'),
                ("B", f'<row r="1">{txt("A1", "second")}</row>'),
            ]
        )
        assert grid(data, 1) == [["second"]]
        assert read(data, index=1)["tab"] == "B"

    def test_an_index_out_of_range_falls_back_to_the_first(self):
        data = book([("A", ONE_SHEET), ("B", "")])
        assert read(data, index=99)["tab"] == "A"


@pytest.mark.unit
class TestCells:
    def test_cells_land_in_the_column_they_name(self):
        """A row of three cells can be columns A, D and F — read in order it shears."""
        row = f'<row r="1">{txt("A1", "a")}{txt("D1", "d")}{txt("F1", "f")}</row>'
        assert cells(row) == [["a", "", "", "d", "", "f"]]

    def test_a_skipped_row_leaves_a_blank_row(self):
        rows = (
            f'<row r="1">{txt("A1", "one")}</row>'
            f'<row r="3">{txt("A3", "three")}</row>'
        )
        assert cells(rows) == [["one"], [""], ["three"]]

    def test_a_shared_string_is_looked_up(self):
        assert cells(
            '<row r="1"><c r="A1" t="s"><v>1</v></c></row>',
            shared=["<si><t>zero</t></si>", "<si><t>one</t></si>"],
        ) == [["one"]]

    def test_formatting_runs_join_back_into_one_value(self):
        """Bolding half a cell in Sheets splits its text into runs."""
        assert cells(
            '<row r="1"><c r="A1" t="s"><v>0</v></c></row>',
            shared=["<si><r><t>very </t></r><r><t>familiar</t></r></si>"],
        ) == [["very familiar"]]

    def test_a_ruby_annotation_is_not_part_of_the_value(self):
        """rPh holds `t` elements of its own; sweeping them up doubles the text."""
        assert cells(
            '<row r="1"><c r="A1" t="s"><v>0</v></c></row>',
            shared=['<si><t>熟悉</t><rPh sb="0" eb="2"><t>shuxi</t></rPh></si>'],
        ) == [["熟悉"]]

    def test_a_boolean_reads_the_way_sync_expects(self):
        row = (
            '<row r="1"><c r="A1" t="b"><v>1</v></c><c r="B1" t="b"><v>0</v></c></row>'
        )
        assert cells(row) == [["TRUE", "FALSE"]]

    def test_a_formula_result_is_taken_not_the_formula(self):
        row = '<row r="1"><c r="A1" t="str"><f>UPPER("x")</f><v>X</v></c></row>'
        assert cells(row) == [["X"]]

    def test_an_empty_cell_is_empty_not_missing(self):
        assert cells(
            f'<row r="1"><c r="A1"/>{txt("B1", "x")}</row>',
        ) == [["", "x"]]


@pytest.mark.unit
class TestNumbers:
    def test_a_whole_number_loses_the_fraction_google_stores(self):
        """The one that matters: this column is the key a note is matched by.

        Google writes `<v>1.0</v>` and exports "1". Reading the literal gives an
        uploaded workbook different note ids than the same rows through a link.
        """
        row = '<row r="1"><c r="A1"><v>1.0</v></c><c r="B1"><v>42</v></c></row>'
        assert cells(row) == [["1", "42"]]

    def test_a_fractional_number_keeps_its_own_literal(self):
        assert cells('<row r="1"><c r="A1"><v>1.5</v></c></row>') == [["1.5"]]

    def test_a_number_too_large_for_a_float_is_left_alone(self):
        """Past 2**53 int() would invent digits rather than drop a trailing .0."""
        huge = "12345678901234567890"
        assert cells(f'<row r="1"><c r="A1"><v>{huge}</v></c></row>') == [[huge]]


@pytest.mark.unit
class TestDates:
    """A date is stored as a day count; only its number format says it is one."""

    STYLES = (
        '<numFmts><numFmt numFmtId="164" formatCode="yyyy\\-mm\\-dd"/>'
        '<numFmt numFmtId="165" formatCode="#,##0.00&quot; kg&quot;"/></numFmts>'
        '<cellXfs><xf numFmtId="0"/><xf numFmtId="14"/>'
        '<xf numFmtId="164"/><xf numFmtId="165"/></cellXfs>'
    )

    def cell(self, style, value, **kw):
        return cells(
            f'<row r="1"><c r="A1" s="{style}"><v>{value}</v></c></row>',
            styles=self.STYLES,
            **kw,
        )

    def test_a_built_in_date_format_becomes_a_date(self):
        assert self.cell(1, 45678) == [["2025-01-21"]]

    def test_a_custom_date_format_is_recognised_too(self):
        assert self.cell(2, 45678) == [["2025-01-21"]]

    def test_a_format_that_merely_contains_letters_is_not_a_date(self):
        """`#,##0.00" kg"` has a d and an m in it, but only inside quoted text."""
        assert self.cell(3, 45678) == [["45678"]]

    def test_an_unstyled_number_stays_a_number(self):
        assert self.cell(0, 45678) == [["45678"]]

    def test_a_time_of_day_keeps_its_hours(self):
        assert self.cell(1, 45678.5) == [["2025-01-21 12:00:00"]]

    def test_the_1904_workbooks_count_from_a_different_day(self):
        assert self.cell(1, 44216, date1904=True) == [["2025-01-21"]]


@pytest.mark.unit
class TestTrimming:
    def test_trailing_empty_rows_and_columns_are_dropped(self):
        """A spreadsheet's used range runs far past its content — formatting a
        whole column is enough. Every empty column would arrive as a note field
        named "", and every empty row as a ghost row."""
        rows = (
            f'<row r="1">{txt("A1", "ID")}<c r="Z1"/></row>'
            f'<row r="2">{txt("A2", "1")}</row>'
            '<row r="900"><c r="A900"/></row>'
        )
        assert cells(rows) == [["ID"], ["1"]]

    def test_a_gap_inside_the_content_is_kept(self):
        row = f'<row r="1">{txt("A1", "a")}{txt("C1", "c")}</row>'
        assert cells(row) == [["a", "", "c"]]


@pytest.mark.unit
class TestOtherFiles:
    def test_a_csv_becomes_tsv(self):
        data = b"ID,Word,Meaning\n1,\xe7\x86\x9f\xe6\x82\x89,familiar\n"
        assert read(data, "deck.csv")["tsv"] == "ID\tWord\tMeaning\n1\t熟悉\tfamiliar\n"

    def test_a_quoted_comma_stays_inside_its_cell(self):
        data = b'ID,Meaning\n1,"familiar, at ease"\n'
        assert read(data, "d.csv")["tsv"] == "ID\tMeaning\n1\tfamiliar, at ease\n"

    def test_a_tsv_is_already_what_the_parser_wants(self):
        assert read("ID\tWord\n1\t熟悉\n".encode(), "d.tsv")["tsv"] == (
            "ID\tWord\n1\t熟悉\n"
        )

    def test_a_byte_order_mark_does_not_stick_to_the_first_header(self):
        """A BOM welded onto "ID" hides the one column the add-on requires."""
        assert read("﻿ID\tWord\n1\tx\n".encode(), "d.tsv")["tsv"].startswith("ID\t")

    def test_the_old_excel_format_says_so(self):
        with pytest.raises(workbook.WorkbookError, match="Save As"):
            read(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1", "old.xls")

    def test_a_file_that_is_not_a_workbook_says_so_rather_than_crashing(self):
        with pytest.raises(workbook.WorkbookError, match="not one"):
            read(b"ID\tWord\n1\tx\n", "lying.xlsx")

    def test_a_zip_that_is_not_a_workbook_says_so(self):
        empty = io.BytesIO()
        zipfile.ZipFile(empty, "w").close()
        with pytest.raises(workbook.WorkbookError, match="not a workbook"):
            read(empty.getvalue(), "empty.xlsx")


@pytest.mark.unit
class TestAgainstTheAddon:
    """The property the whole feature rests on: a file and a link agree."""

    def test_a_multi_line_cell_survives_into_the_parser(self):
        """TSV cannot hold a newline unquoted, and the parser reads with csv."""
        from src.tsv_model import parse_tsv_data

        rows = (
            f'<row r="1">{txt("A1", "ID")}{txt("B1", "Note")}</row>'
            f'<row r="2"><c r="A2"><v>1</v></c>{txt("B2", "line one\nline two")}</row>'
        )
        parsed = parse_tsv_data(read(one(rows))["tsv"])
        assert parsed["rows"] == [["1", "line one\nline two"]]

    def test_a_tab_inside_a_cell_does_not_split_the_row(self):
        from src.tsv_model import parse_tsv_data

        rows = (
            f'<row r="1">{txt("A1", "ID")}{txt("B1", "Note")}</row>'
            f'<row r="2"><c r="A2"><v>1</v></c>{txt("B2", "a\tb")}</row>'
        )
        assert parse_tsv_data(read(one(rows))["tsv"])["rows"] == [["1", "a\tb"]]

    def test_a_workbook_and_a_tsv_of_the_same_sheet_build_the_same_notes(self):
        from src.tsv_model import build_remote_deck_from_tsv
        from src.tsv_model import parse_tsv_data

        table = [
            ["ID", "SYNC", "SUBDECK 1", "TAGS", "Word", "Meaning"],
            ["1", "TRUE", "Unit 1", "hsk4", "熟悉", "familiar"],
            ["2", "FALSE", "Unit 2", "", "复杂", "complicated"],
        ]
        tsv = "".join("\t".join(row) + "\n" for row in table)

        # The same table as a workbook holds it: ids numeric and written the way
        # Google writes them, the sync flag a real boolean, the text shared.
        strings, xml = [], ""
        for r, row in enumerate(table, start=1):
            cells_xml = ""
            for c, value in enumerate(row):
                ref = f"{chr(65 + c)}{r}"
                if value in ("TRUE", "FALSE"):
                    cells_xml += f'<c r="{ref}" t="b"><v>{int(value == "TRUE")}</v></c>'
                elif value.isdigit():
                    cells_xml += f'<c r="{ref}"><v>{value}.0</v></c>'
                elif value:
                    strings.append(f"<si><t>{value}</t></si>")
                    cells_xml += f'<c r="{ref}" t="s"><v>{len(strings) - 1}</v></c>'
                else:
                    cells_xml += f'<c r="{ref}"/>'
            xml += f'<row r="{r}">{cells_xml}</row>'

        from_file = build_remote_deck_from_tsv(
            parse_tsv_data(read(one(xml, shared=strings))["tsv"]), ""
        )
        from_link = build_remote_deck_from_tsv(parse_tsv_data(tsv), "")

        assert from_file.notes == from_link.notes
        assert from_file.get_statistics() == from_link.get_statistics()
