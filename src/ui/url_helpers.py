"""What the deck-list windows share: a sheet's link, and the way to a first one.

The Sync and Disconnect windows each draw one row per connected sheet with the
same two buttons on it, and each has the same thing to say when there are no rows
at all. Both live here so the two windows cannot drift apart.
"""

import webbrowser

from ..compat import QApplication
from ..compat import QTimer
from ..compat import tooltip
from ..utils import add_debug_message


def clean_url_for_browser(url):
    """
    Removes the '&output=tsv' ending from URL to allow browser viewing.

    Args:
        url (str): Complete URL with TSV ending

    Returns:
        str: Clean URL for browser viewing
    """
    if url.endswith("&output=tsv"):
        return url[:-11]  # Removes '&output=tsv'
    elif url.endswith("&single=true&output=tsv"):
        return url[:-23]  # Removes '&single=true&output=tsv'
    return url


def copy_url_to_clipboard(url, parent=None):
    """
    Copies the clean URL to system clipboard, and says so.

    A button that copies and shows nothing reads as a button that did nothing,
    so the copy is confirmed with Anki's own transient tooltip.

    Args:
        url (str): URL to copy
        parent: the window the confirmation is shown over
    """
    try:
        clean_url = clean_url_for_browser(url)
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(clean_url)
            tooltip("Link copied", parent=parent)
            return True
        return False
    except Exception as e:
        add_debug_message(f"Error copying URL: {e}", "UI")
        return False


def open_url_in_browser(url):
    """Opens the sheet itself, which is where every change to a deck is made."""
    try:
        return bool(webbrowser.open(clean_url_for_browser(url)))
    except Exception as e:
        add_debug_message(f"Error opening URL: {e}", "UI")
        return False


def connect_a_sheet(dialog):
    """Closes ``dialog`` and opens the window that connects a Google Sheet.

    For the empty state of a window that lists connected sheets: with nothing to
    list, the one useful thing it can offer is the way to a first one. The opener
    is imported here rather than at the top because ``deck_manager`` imports the
    dialogs that call this, and it runs on the next turn of the event loop so the
    window asking has finished closing before the next one opens over it.
    """
    from ..deck_manager import addNewDeck

    dialog.reject()
    QTimer.singleShot(0, addNewDeck)
