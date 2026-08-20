"""What the Add Deck dialog will accept into its URL box.

This is the only way a deck is connected, so a source the dialog refuses does not
exist however well the rest of the add-on supports it. That is exactly what
happened to the `.xlsx`-at-a-plain-address source: `utils`, the downloader, the
naming and the sync all handled it, while the dialog still tested the typed URL
for the Google host and answered "Please enter a valid Google Sheets URL".

The check is on the dialog's own gate rather than on ``utils``, because the bug
was never in ``utils``.
"""

import importlib

import pytest

GOOGLE = "https://docs.google.com/spreadsheets/d/1AbC_dEf-123/edit?usp=sharing"
GITHUB_BLOB = (
    "https://github.com/tannc28/sheetcards/blob/main/examples/"
    "sheetcards-examples.xlsx"
)
RAW = (
    "https://raw.githubusercontent.com/tannc28/sheetcards/main/examples/"
    "sheetcards-examples.xlsx"
)

ACCEPTED = [
    pytest.param(GOOGLE, id="google-sheet"),
    pytest.param(GITHUB_BLOB, id="github-blob-xlsx"),
    pytest.param(RAW, id="raw-xlsx"),
    pytest.param("https://example.com/decks/vocab.xlsm", id="plain-host-xlsm"),
    pytest.param("https://example.com/a%20b/deck.xlsx?v=2", id="query-and-escapes"),
]

REFUSED = [
    pytest.param("https://example.com/decks/vocab.pdf", id="not-a-spreadsheet"),
    pytest.param("https://drive.google.com/file/d/123/view", id="drive-page"),
    pytest.param("ftp://example.com/deck.xlsx", id="wrong-scheme"),
    pytest.param("just some text", id="not-a-url"),
]


def dialog():
    """A constructed dialog — Anki and Qt come from conftest's mocks."""
    module = importlib.import_module("src.ui.add_deck_dialog")
    return module.AddDeckDialog()


def gate(url):
    """Run the typed-URL gate and report whether it stopped there.

    ``_on_url_changed`` is the whole of the immediate feedback: it either refuses
    the text outright or starts the 1.2 s timer that does the real validation. A
    refusal is therefore "the timer was never started".

    The line edit's ``text`` is replaced rather than filled in: conftest's Qt is a
    mock, so ``setText`` stores nothing and ``text()`` hands back a MagicMock —
    which would reach the gate as neither kind of URL and make every case look
    refused, including the ones that work.
    """
    dlg = dialog()
    dlg.url_edit.text = lambda: url

    started = []
    dlg.validation_timer.start = lambda *a, **k: started.append(a)
    said = []
    dlg._show_status = lambda message, kind="info": said.append(message)

    dlg._on_url_changed()
    return bool(started), said[-1] if said else ""


@pytest.mark.unit
@pytest.mark.parametrize("url", ACCEPTED)
def test_the_dialog_goes_on_to_validate(url):
    accepted, message = gate(url)
    assert accepted, f"the dialog refused {url!r} with {message!r}"


@pytest.mark.unit
@pytest.mark.parametrize("url", REFUSED)
def test_the_dialog_stops_at_what_it_cannot_read(url):
    accepted, _ = gate(url)
    assert not accepted, f"the dialog accepted {url!r}"


@pytest.mark.unit
def test_the_refusal_names_both_kinds_of_source():
    """A message naming only Google Sheets is what hid the file source."""
    _, message = gate("https://example.com/decks/vocab.pdf")
    assert ".xlsx" in message, message


@pytest.mark.unit
def test_a_file_url_is_checked_against_the_decks_already_connected():
    """A file has no spreadsheet id, and asking for one used to raise.

    The exception was caught as "not a duplicate", so a file already connected
    could be connected a second time and sync the same rows twice.
    """
    from src.utils import source_id

    module = importlib.import_module("src.ui.add_deck_dialog")
    dlg = dialog()
    key = source_id(GITHUB_BLOB)
    module.get_remote_decks = lambda: {key: {"remote_deck_name": "examples"}}
    try:
        is_duplicate, info, _ = dlg._check_duplicate_spreadsheet(GITHUB_BLOB)
    finally:
        importlib.reload(module)

    assert is_duplicate
    assert info["remote_deck_name"] == "examples"


@pytest.mark.unit
def test_the_browser_address_and_the_raw_address_are_one_deck():
    """Pasting either form of the same file must not make two decks."""
    from src.utils import source_id

    assert source_id(GITHUB_BLOB) == source_id(RAW)
