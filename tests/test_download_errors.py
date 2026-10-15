"""A failed download says what to do, in one sentence, everywhere.

The sync, the Add dialog's link check and the summary all go through
``errors.describe_download_failure``; these pin the mapping itself and that the
download path uses it rather than nesting "Error: Error obtaining remote deck:
HTTP Error 400…" for the reader to decode.
"""

import io
import socket
import urllib.error

import pytest

from src import data_processor
from src import errors
from src.errors import GENERIC
from src.errors import NOT_FOUND
from src.errors import NOT_SHARED
from src.errors import NOT_SHARED_FILE
from src.errors import OFFLINE
from src.errors import DownloadError
from src.errors import RemoteDeckError
from src.errors import describe_download_failure
from src.errors import looks_like_login_page
from src.errors import user_message

SHEET = "https://docs.google.com/spreadsheets/d/abc/export?format=xlsx"
FILE = "https://raw.githubusercontent.com/someone/repo/main/deck.xlsx"


def http_error(code, url=SHEET):
    return urllib.error.HTTPError(url, code, "reason", {}, io.BytesIO(b""))


@pytest.mark.unit
class TestTheMapping:
    @pytest.mark.parametrize("code", [400, 401, 403])
    def test_not_allowed_means_not_shared(self, code):
        assert describe_download_failure(http_error(code), url=SHEET) == NOT_SHARED

    def test_not_shared_names_the_steps(self):
        assert "Anyone with the link" in NOT_SHARED and "Viewer" in NOT_SHARED

    def test_a_file_that_is_not_public_is_not_told_about_google_sheets(self):
        assert describe_download_failure(http_error(403), url=FILE) == NOT_SHARED_FILE

    @pytest.mark.parametrize("code", [404, 410])
    def test_missing(self, code):
        assert describe_download_failure(http_error(code), url=SHEET) == NOT_FOUND

    def test_a_status_alone_is_enough(self):
        assert describe_download_failure(status=404, url=SHEET) == NOT_FOUND

    @pytest.mark.parametrize(
        "error",
        [
            urllib.error.URLError(socket.gaierror(8, "nodename nor servname")),
            urllib.error.URLError(TimeoutError("timed out")),
            urllib.error.URLError(ConnectionRefusedError(61, "refused")),
            TimeoutError("timed out"),
            TimeoutError("timed out"),
            socket.gaierror(8, "nodename nor servname"),
        ],
    )
    def test_no_network(self, error):
        assert describe_download_failure(error, url=SHEET) == OFFLINE

    def test_no_network_names_the_host_that_could_not_be_reached(self):
        message = describe_download_failure(TimeoutError(), url=FILE)
        assert "raw.githubusercontent.com" in message
        assert "Google" not in message

    @pytest.mark.parametrize("code", [500, 502, 429])
    def test_anything_else_is_short_and_generic(self, code):
        assert describe_download_failure(http_error(code), url=SHEET) == GENERIC

    def test_an_unknown_exception_is_generic(self):
        assert describe_download_failure(ValueError("boom"), url=SHEET) == GENERIC

    def test_an_already_described_failure_keeps_its_sentence(self):
        assert describe_download_failure(DownloadError(NOT_FOUND)) == NOT_FOUND

    def test_no_sentence_leaks_technical_words(self):
        for sentence in (NOT_SHARED, NOT_SHARED_FILE, NOT_FOUND, OFFLINE, GENERIC):
            for word in ("HTTP", "Error", "URL", "Exception"):
                assert word not in sentence


@pytest.mark.unit
class TestLoginPage:
    def test_html_content_type(self):
        assert looks_like_login_page("text/html; charset=utf-8", SHEET, b"")

    def test_redirect_to_sign_in(self):
        assert looks_like_login_page(
            "application/octet-stream",
            "https://accounts.google.com/ServiceLogin?continue=…",
            b"",
        )

    def test_html_body_with_no_content_type(self):
        assert looks_like_login_page("", SHEET, b"\n  <!DOCTYPE html><html>")

    @pytest.mark.parametrize(
        "content_type,head",
        [
            ("text/tab-separated-values", b"ID\tFront\tBack\n"),
            (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                b"PK\x03\x04",
            ),
        ],
    )
    def test_a_sheet_is_not_a_login_page(self, content_type, head):
        assert not looks_like_login_page(content_type, SHEET, head)


class _Response:
    def __init__(self, body, content_type, url=SHEET, status=200):
        self.body = body
        self.headers = {"Content-Type": content_type}
        self.url = url
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def getcode(self):
        return self.status

    def geturl(self):
        return self.url

    def read(self):
        return self.body


@pytest.fixture
def public_host(monkeypatch):
    """The address check resolves the host; pretend it is a public one."""
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port: [(None, None, None, None, ("142.250.0.1", port))],
    )


@pytest.mark.unit
class TestTheDownloadUsesIt:
    def test_403_reads_as_not_shared(self, monkeypatch, public_host):
        def urlopen(request, timeout):
            raise http_error(403)

        monkeypatch.setattr(data_processor.urllib.request, "urlopen", urlopen)
        with pytest.raises(DownloadError) as caught:
            data_processor._download(SHEET, 5)
        assert str(caught.value) == NOT_SHARED
        assert "403" in caught.value.detail

    def test_a_sign_in_page_reads_as_not_shared(self, monkeypatch, public_host):
        monkeypatch.setattr(
            data_processor.urllib.request,
            "urlopen",
            lambda request, timeout: _Response(b"<!DOCTYPE html>", "text/html"),
        )
        with pytest.raises(DownloadError) as caught:
            data_processor._download(SHEET, 5)
        assert str(caught.value) == NOT_SHARED

    def test_a_sheet_comes_back_as_bytes(self, monkeypatch, public_host):
        monkeypatch.setattr(
            data_processor.urllib.request,
            "urlopen",
            lambda request, timeout: _Response(b"PK\x03\x04", "application/zip"),
        )
        assert data_processor._download(SHEET, 5) == b"PK\x03\x04"

    def test_a_host_that_cannot_be_looked_up_reads_as_offline(self, monkeypatch):
        def fail(host, port):
            raise socket.gaierror(8, "nodename nor servname provided")

        monkeypatch.setattr(socket, "getaddrinfo", fail)
        with pytest.raises(DownloadError) as caught:
            data_processor._download(SHEET, 5)
        assert str(caught.value) == OFFLINE

    def test_get_remote_deck_does_not_wrap_the_sentence(self, monkeypatch):
        def download(url, timeout=30):
            raise DownloadError(NOT_FOUND, detail="HTTP 404")

        monkeypatch.setattr(data_processor, "download_deck_tsv", download)
        with pytest.raises(RemoteDeckError) as caught:
            data_processor.getRemoteDeck(SHEET)
        assert str(caught.value) == NOT_FOUND

    def test_a_parse_crash_is_a_sentence_too(self, monkeypatch):
        monkeypatch.setattr(
            data_processor, "download_deck_tsv", lambda url, timeout=30: "ID\n1\n"
        )

        def explode(*a, **k):
            raise KeyError("ID")

        monkeypatch.setattr(data_processor, "parse_tsv_data", explode)
        with pytest.raises(RemoteDeckError) as caught:
            data_processor.getRemoteDeck(SHEET)
        assert "KeyError" not in str(caught.value)
        assert "Error obtaining" not in str(caught.value)


@pytest.mark.unit
class TestValidateUrl:
    def test_without_probe_nothing_is_fetched(self, monkeypatch):
        import urllib.request

        from src.utils import validate_url

        def urlopen(*a, **k):
            raise AssertionError("validate_url(probe=False) went to the network")

        monkeypatch.setattr(urllib.request, "urlopen", urlopen)
        url = "https://docs.google.com/spreadsheets/d/abc123/edit#gid=0"
        assert "export?format=tsv" in validate_url(url, probe=False)

    def test_the_probe_says_the_same_sentence(self, monkeypatch):
        import urllib.request

        from src.utils import validate_url

        def urlopen(request, timeout):
            raise http_error(400)

        monkeypatch.setattr(urllib.request, "urlopen", urlopen)
        with pytest.raises(ValueError) as caught:
            validate_url("https://docs.google.com/spreadsheets/d/abc123/edit")
        assert str(caught.value) == NOT_SHARED


@pytest.mark.unit
class TestUserMessage:
    def test_a_remote_deck_error_is_shown_as_written(self):
        assert user_message(RemoteDeckError("The sheet has no ID column.")) == (
            "The sheet has no ID column."
        )

    def test_a_python_error_is_not_shown(self):
        message = user_message(KeyError("local_deck_id"))
        assert "local_deck_id" not in message
        assert "debug logging" in message

    def test_the_pure_layer_stays_pure(self):
        """errors.py is run by the preview site in a browser: stdlib only."""
        import ast
        import inspect

        tree = ast.parse(inspect.getsource(errors))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert node.level == 0 or node.module in (None, "errors")
                assert (node.module or "").split(".")[0] not in ("aqt", "anki")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in ("aqt", "anki")
