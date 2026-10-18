"""The add-on's half of carrying pictures and recordings inside the deck.

What is fetched, what it is called and what the field then holds are decided in
:mod:`media`, which Sheet to Anki runs too; this module only does the fetching
with ``urllib`` and the writing with ``col.media``. Split in two the way a sync
is: :func:`fetch_deck_media` runs on the background thread beside the sheet's
download and touches no collection, :func:`store_deck_media` runs on the main
thread just before the notes are written.

The add-on could read hosts a browser may not, but it deliberately does not:
one cell must become one field value on every path, or an ``.apkg`` built on a
phone and a sync on the desktop would keep overwriting each other's notes. So a
host outside Commons is kept only when its answer carries the
``Access-Control-Allow-Origin`` a browser would need.
"""

import os
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

try:
    from . import media
    from .debug import add_debug_message
except ImportError:  # pragma: no cover - imported by the tests as a package
    import media
    from debug import add_debug_message

# The origin Sheet to Anki reads from, sent the way a browser sends it so a host
# that answers CORS only when asked is judged the same on both paths.
SITE_ORIGIN = "https://tannc28.github.io"

WORKERS = 4
TIMEOUT = 20

# Wikimedia asks a program to say who it is and where to complain, and answers a
# burst with 429 rather than with the file. Two retries, waiting what it asks
# (at most a few seconds), turn a rate limit into a slower sync, not a link.
USER_AGENT = "SheetCards (https://github.com/tannc28/sheetcards; Anki add-on)"
RETRIES = 2
_BUSY = (429, 503)


def _get(url, timeout, sleep=time.sleep):
    """``(content_type, bytes, allow_origin)`` for an https address, or None."""
    try:
        from .data_processor import _refuse_unsafe_url
    except ImportError:  # pragma: no cover
        from data_processor import _refuse_unsafe_url
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Origin": SITE_ORIGIN}
    )
    for attempt in range(RETRIES + 1):
        try:
            _refuse_unsafe_url(url)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if response.getcode() != 200:
                    return None
                data = response.read(media.FILE_LIMIT + 1)
                headers = response.headers
                return (
                    headers.get("Content-Type", ""),
                    data,
                    headers.get("Access-Control-Allow-Origin", ""),
                )
        except urllib.error.HTTPError as e:
            if e.code in _BUSY and attempt < RETRIES:
                try:
                    wait = float(e.headers.get("Retry-After") or 0)
                except ValueError:
                    wait = 0
                sleep(min(max(wait, 1.0 + attempt), 5.0))
                continue
            add_debug_message(f"Media not fetched: {url} — {e}", "MEDIA")
            return None
        except Exception as e:  # a picture that cannot be had stays a link
            add_debug_message(f"Media not fetched: {url} — {e}", "MEDIA")
            return None
    return None


def _commons(titles, timeout):
    answers = []
    for query in media.commons_queries(titles):
        got = _get(query, timeout)
        if got:
            try:
                answers.append(got[1].decode("utf-8"))
            except UnicodeDecodeError:
                pass
    return media.commons_sources(answers)


def fetch_deck_media(remote_deck, media_dir=None, timeout=TIMEOUT, get=None):
    """Fetches what a deck's media cells point at. Runs on a background thread.

    Args:
        remote_deck: the parsed sheet (``notes``, ``plan``, ``sheet_config``)
        media_dir (str, optional): the collection's media folder, read on the
            main thread; a file already in it is not fetched again
        get (callable, optional): stands in for the network in tests

    Returns:
        dict: ``{"files": {name: bytes}, "names": {address: name}, "links": n}``
        — ``names`` covers files already present too, ``links`` counts the
        addresses left as links
    """
    get = get or _get
    sheet_config = getattr(remote_deck, "sheet_config", None)
    plan = getattr(remote_deck, "plan", None)
    out = {"files": {}, "names": {}, "links": 0}
    if sheet_config is None or plan is None:
        return out
    jobs = media.jobs(remote_deck.notes, plan, sheet_config)
    todo = []
    for job in jobs:
        name = job["name"]
        if name and media_dir and os.path.exists(os.path.join(media_dir, name)):
            out["names"][job["url"]] = name
        else:
            todo.append(job)
    if not todo:
        return out

    titles = [j["commons"] for j in todo if j["commons"]]
    commons = _commons(titles, timeout) if titles else {}

    def one(job):
        src = media.source(job, commons)
        got = get(src, timeout) if src else None
        if not got:
            return job, None, b""
        content_type, data, allow = got
        # Commons' upload host answers any origin; anything else must say so.
        if not job["commons"] and allow.strip() not in ("*", SITE_ORIGIN):
            return job, None, b""
        return job, media.settle(job, content_type, len(data)), data

    total = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for job, name, data in pool.map(one, todo):
            if not name or total + len(data) > media.TOTAL_LIMIT:
                out["links"] += 1
                continue
            total += len(data)
            out["files"][name] = data
            out["names"][job["url"]] = name
    add_debug_message(
        f"Media: {len(out['files'])} fetched, "
        f"{len(out['names']) - len(out['files'])} already here, "
        f"{out['links']} left as links ({total // 1024} KB)",
        "MEDIA",
    )
    return out


def store_deck_media(col, remote_deck, fetched):
    """Writes the fetched files and points the deck's cells at them. Main thread.

    ``write_data`` keeps the name it is given unless a *different* file already
    has it, in which case it would add a hash to the name; a cell is only
    pointed at a file stored under the exact name every other device will use.

    Returns:
        int: how many addresses now point at a file
    """
    if not fetched:
        return 0
    names = dict(fetched.get("names") or {})
    for name, data in (fetched.get("files") or {}).items():
        try:
            stored = col.media.write_data(name, data)
        except Exception as e:
            add_debug_message(f"Media not stored: {name} — {e}", "MEDIA")
            stored = None
        if stored != name:
            names = {url: n for url, n in names.items() if n != name}
    for note_data in remote_deck.notes:
        media.embed(note_data, remote_deck.plan, remote_deck.sheet_config, names)
    return len(names)
