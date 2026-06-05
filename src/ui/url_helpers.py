"""Shared URL helpers for Sheets2Anki dialogs.

Centralizes the clean-URL-for-browser and copy-to-clipboard logic that was
previously duplicated verbatim in sync_dialog.py and disconnect_dialog.py.
"""

from ..compat import QApplication
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


def copy_url_to_clipboard(url):
    """
    Copies the clean URL to system clipboard.

    Args:
        url (str): URL to copy
    """
    try:
        clean_url = clean_url_for_browser(url)
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(clean_url)
            return True
        return False
    except Exception as e:
        add_debug_message(f"Error copying URL: {e}", "UI")
        return False
