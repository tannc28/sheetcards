"""A deck whose source is a spreadsheet file at a plain address.

Not every deck comes from Google Sheets. A .xlsx in a GitHub repository holds the
same sheets and is read by the same reader; only getting hold of the bytes is
different, and everything downstream of the download is untouched.

Two things here are worth more than the happy path. One is the address check:
opening the door to arbitrary hosts is opening it inside the user's own network,
because Anki runs on their machine. The other is identity — a file has no
spreadsheet id, and if the id it gets instead is unstable then every sync builds
a second deck.
"""

import pytest

from src.config_manager import get_deck_id
from src.utils import convert_edit_url_to_xlsx
from src.utils import file_name_from_url
from src.utils import is_spreadsheet_file_url
from src.utils import normalize_file_url
from src.utils import sheet_name_from_url
from src.utils import source_id
from src.utils import url_for_sheet
from src.utils import validate_url

BLOB = "https://github.com/tannc28/decks/blob/main/english.xlsx"
RAW = "https://raw.githubusercontent.com/tannc28/decks/main/english.xlsx"
SHEETS = "https://docs.google.com/spreadsheets/d/ABC/edit"


@pytest.mark.unit
class TestRecognisingAFileUrl:
    def test_an_xlsx_address_is_a_file(self):
        assert is_spreadsheet_file_url(BLOB)
        assert is_spreadsheet_file_url(RAW)
        assert is_spreadsheet_file_url("https://example.com/a/b.xlsm")

    def test_a_google_sheets_link_is_not(self):
        """It has sheets in it, but it is fetched a different way."""
        assert not is_spreadsheet_file_url(SHEETS)

    def test_something_that_is_neither_is_not(self):
        for url in [
            "https://example.com/deck.csv",
            "https://example.com/",
            "https://example.com/notes.xlsx.html",
            "",
            None,
        ]:
            assert not is_spreadsheet_file_url(url)

    def test_the_sheet_fragment_does_not_hide_the_extension(self):
        assert is_spreadsheet_file_url(url_for_sheet(BLOB, "vocab"))


@pytest.mark.unit
class TestGithubsTwoAddresses:
    """The address a browser shows is not the one that serves the file."""

    def test_a_blob_address_becomes_the_raw_one(self):
        assert normalize_file_url(BLOB) == RAW

    def test_a_raw_address_is_left_alone(self):
        assert normalize_file_url(RAW) == RAW

    def test_a_branch_with_slashes_in_it_survives(self):
        deep = "https://github.com/u/r/blob/feature/new-cards/decks/a.xlsx"
        assert normalize_file_url(deep) == (
            "https://raw.githubusercontent.com/u/r/feature/new-cards/decks/a.xlsx"
        )

    def test_another_host_is_not_rewritten(self):
        other = "https://example.com/github.com/blob/main/a.xlsx"
        assert normalize_file_url(other) == other

    def test_validate_url_hands_back_the_address_that_serves_the_file(self):
        assert validate_url(BLOB) == RAW

    def test_the_download_url_is_the_file_itself(self):
        assert convert_edit_url_to_xlsx(BLOB) == RAW


@pytest.mark.unit
class TestIdentity:
    def test_the_two_addresses_of_one_file_are_one_deck(self):
        """Otherwise connecting from the browser address and from the raw one
        would build two decks over the same rows."""
        assert source_id(BLOB) == source_id(RAW)

    def test_the_id_is_stable(self):
        assert source_id(BLOB) == source_id(BLOB)

    def test_it_cannot_be_mistaken_for_a_spreadsheet_id(self):
        assert source_id(BLOB).startswith("file_")
        assert source_id(SHEETS) == "ABC"

    def test_different_files_are_different_decks(self):
        other = "https://raw.githubusercontent.com/tannc28/decks/main/other.xlsx"
        assert source_id(RAW) != source_id(other)

    def test_each_sheet_of_the_file_is_its_own_deck(self):
        assert get_deck_id(url_for_sheet(BLOB, "vocab")) != get_deck_id(
            url_for_sheet(BLOB, "grammar")
        )
        assert get_deck_id(url_for_sheet(BLOB, "vocab")).endswith("#vocab")

    def test_a_url_that_is_neither_is_refused_by_name(self):
        with pytest.raises(ValueError, match="xlsx"):
            source_id("https://example.com/notes.pdf")


@pytest.mark.unit
class TestTheDeckName:
    def test_it_comes_from_the_file(self):
        assert file_name_from_url(BLOB) == "english"

    def test_an_escaped_name_is_readable_again(self):
        assert file_name_from_url("https://e.com/T%E1%BB%AB%20v%E1%BB%B1ng.xlsx") == (
            "Từ vựng"
        )

    def test_the_sheet_is_still_part_of_the_name(self):
        from src.deck_manager import DeckNameManager

        assert (
            DeckNameManager.extract_remote_name_from_url(url_for_sheet(BLOB, "vocab"))
            == "english::vocab"
        )

    def test_the_fragment_is_not_part_of_the_file_name(self):
        assert file_name_from_url(url_for_sheet(BLOB, "vocab")) == "english"
        assert sheet_name_from_url(url_for_sheet(BLOB, "vocab")) == "vocab"


@pytest.mark.unit
class TestWhereADeckMayComeFrom:
    """The address check, now that it is no longer "Google or nothing".

    Anki runs on the user's own machine, inside their own network. A URL someone
    else supplied is a URL someone else chose, and `http://192.168.1.1/admin` is
    a door nothing outside that network can knock on.
    """

    def _refuse(self, url):
        from src.data_processor import RemoteDeckError
        from src.data_processor import _refuse_unsafe_url

        with pytest.raises(RemoteDeckError):
            _refuse_unsafe_url(url)

    def test_a_public_https_address_is_allowed(self):
        from src.data_processor import _refuse_unsafe_url

        _refuse_unsafe_url(RAW)
        _refuse_unsafe_url("https://docs.google.com/spreadsheets/d/A/export?format=tsv")

    def test_plain_http_is_refused(self):
        """Not paranoia about eavesdropping so much as one fewer scheme to reason
        about, and http is where the interesting internal addresses live."""
        self._refuse("http://raw.githubusercontent.com/a/b/main/x.xlsx")

    def test_other_schemes_are_refused(self):
        for url in ["file:///etc/passwd", "ftp://example.com/a.xlsx"]:
            self._refuse(url)

    def test_loopback_is_refused(self):
        self._refuse("https://127.0.0.1/x.xlsx")
        self._refuse("https://localhost/x.xlsx")

    def test_a_private_network_address_is_refused(self):
        for host in ["192.168.1.1", "10.0.0.1", "172.16.0.1"]:
            self._refuse(f"https://{host}/x.xlsx")

    def test_the_cloud_metadata_address_is_refused(self):
        """The classic SSRF target, and link-local besides."""
        self._refuse("https://169.254.169.254/latest/meta-data/")

    def test_ipv6_loopback_is_refused(self):
        self._refuse("https://[::1]/x.xlsx")

    def test_a_url_with_no_host_is_refused(self):
        self._refuse("https:///x.xlsx")
