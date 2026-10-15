"""Custom exception types for the SheetCards addon (extracted from utils.py)."""


class SyncError(Exception):
    """Base exception for sync-related errors."""

    pass


class NoteProcessingError(SyncError):
    """Exception raised when processing a note fails."""

    pass


class CollectionSaveError(SyncError):
    """Exception raised when saving the collection fails."""

    pass


class ConfigurationError(Exception):
    """Exception raised for configuration-related issues."""

    pass


class RemoteDeckError(Exception):
    """Custom exception for errors related to remote decks.

    Lives here rather than in :mod:`data_processor` so the pure layer
    (:mod:`tsv_model`) can raise it without importing a module that needs Anki.
    ``data_processor`` re-exports it, so ``from .data_processor import
    RemoteDeckError`` still resolves.
    """

    pass


# =============================================================================
# WHAT A FAILED DOWNLOAD MEANS, IN ONE SENTENCE
# =============================================================================
#
# One table, consulted by every place that fetches a sheet — the sync, the link
# check in the Add dialog, and the summary afterwards — so a link that is not
# shared reads the same everywhere. It used to read "Error: Error obtaining
# remote deck: HTTP Error 400: Bad Request", which is three layers of the
# add-on talking to itself and none of them saying what to do.
#
# The technical detail (status code, the reason Python gave, the address) is
# what a bug report needs, so it goes to the debug log; the sentence is what a
# learner needs, so it goes on the screen. Stdlib only: this module is part of
# the pure layer.

NOT_SHARED = (
    "This sheet isn't shared. In Google Sheets: Share → General access → "
    "Anyone with the link → Viewer."
)
NOT_SHARED_FILE = (
    "This file isn't public. Make sure anyone with the link can open it, "
    "without signing in."
)
NOT_FOUND = "There's no sheet at this address. Was it deleted, or is the link mistyped?"
OFFLINE = "Can't reach Google. Check your internet connection and try again."
OFFLINE_HOST = "Can't reach {host}. Check your internet connection and try again."
GENERIC = (
    "The sheet couldn't be downloaded. Try again in a moment — if it keeps "
    "happening, turn on debug logging in Settings and look at the log."
)

# A status that means "you are not allowed to see this". Google answers an
# unshared sheet's export with 400 more often than with 401 or 403.
_NOT_ALLOWED = frozenset({400, 401, 403})


class DownloadError(RemoteDeckError):
    """A sheet could not be fetched, with the sentence that says what to do.

    ``str()`` is the sentence, so every existing ``except RemoteDeckError`` that
    shows ``str(e)`` shows the right thing without being changed. ``detail`` is
    the technical account for the debug log.
    """

    def __init__(self, message, detail=""):
        super().__init__(message)
        self.detail = detail or message


def _host_of(url):
    from urllib.parse import urlparse

    try:
        return (urlparse(url or "").hostname or "").lower()
    except ValueError:
        return ""


def _is_google(url):
    host = _host_of(url)
    return not host or host == "google.com" or host.endswith(".google.com")


def looks_like_login_page(content_type="", final_url="", head=b""):
    """True when what came back is a web page rather than a spreadsheet.

    An unshared Google Sheet does not always fail: its export can redirect to
    the sign-in page and answer 200 with HTML. Read as data that is a deck with
    one column called ``<!DOCTYPE html>``, or a file that is "not a zip", and
    either way the reader is told the wrong thing.
    """
    if _host_of(final_url) == "accounts.google.com":
        return True
    if (content_type or "").lower().split(";")[0].strip() == "text/html":
        return True
    start = bytes(head or b"")[:512].lstrip().lower()
    return start.startswith((b"<!doctype html", b"<html"))


def describe_download_failure(error=None, url="", status=None):
    """The sentence for a failed download, from the exception or the status.

    ``error`` may be an ``urllib.error.HTTPError``, a ``URLError``, a
    ``TimeoutError``/``socket.timeout``, any ``OSError`` raised while looking
    the host up, or a :class:`DownloadError` (whose sentence is kept). ``url``
    decides whether the sentence talks about Google or about the file's own
    host.
    """
    import socket
    import urllib.error

    if isinstance(error, DownloadError):
        return str(error)

    google = _is_google(url)
    if status is None and isinstance(error, urllib.error.HTTPError):
        status = error.code

    if status is not None:
        if status in _NOT_ALLOWED:
            return NOT_SHARED if google else NOT_SHARED_FILE
        if status in (404, 410):
            return NOT_FOUND
        return GENERIC

    # HTTPError is a URLError, so the status branch above has to come first.
    reason = error.reason if isinstance(error, urllib.error.URLError) else error
    if isinstance(reason, (TimeoutError, socket.timeout, socket.gaierror)) or (
        isinstance(reason, OSError) and not isinstance(reason, FileNotFoundError)
    ):
        host = _host_of(url)
        return OFFLINE if google or not host else OFFLINE_HOST.format(host=host)
    return GENERIC


def user_message(error):
    """What to show for any exception raised while syncing a deck.

    A :class:`RemoteDeckError` was written for a reader — a missing ID column,
    a sheet renamed since the deck was connected, a download that failed — so
    its text is shown as it is. Anything else is a fault in the add-on, whose
    text is a Python message and belongs in the log.
    """
    if isinstance(error, (RemoteDeckError, SyncError)):
        text = str(error).strip()
        if text:
            return text
    return (
        "Something went wrong while syncing this deck. Turn on debug logging "
        "in Settings and sync again to see the details."
    )
