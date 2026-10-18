"""Pictures and recordings carried inside the deck instead of linked from it.

A media column's cell is an address on the web. That is what the sheet says and
what stays in the sheet, but a card that has to reach the address every time it
is shown needs the network every time it is reviewed. So both ways a sheet
reaches Anki — the ``.apkg`` Sheet to Anki builds in a browser and the add-on's
sync — fetch what they can and put the file in Anki's media folder, and the field
holds the file's name instead of the address.

Everything that decides *what* happens lives here, in the pure layer, because the
two paths only agree if they run the same rules: the same file name for the same
address on every device (so an import after a sync, or a sync after an import,
finds the note unchanged), the same Commons resolution, the same refusals. The
fetching itself is the one thing each path does its own way — ``fetch()`` in the
browser, ``urllib`` in the add-on — and it is all either of them does.

**Which addresses are fetched.** Only what a browser is allowed to read, because
the add-on could read more and the two would then disagree about the same cell:

* Wikimedia Commons, resolved through its API to the ``upload.wikimedia.org``
  file (which answers any origin). A picture comes as its 500px thumbnail — one
  of Commons' standard steps, so it is never generated on demand — and an Ogg,
  WAV, FLAC or Opus recording as Commons' own MP3 transcode, because AnkiMobile
  cannot play Ogg.
* Any other https address that answers with ``Access-Control-Allow-Origin``.

Anything else keeps its address and still works online. Video is never fetched:
its column frames a player.

**What the field holds.** A picture's field holds the bare name, which
``<img src="{{F}}">`` reads exactly as it read the address. A recording's field
holds ``[sound:name]`` — Anki's own reference, so the card gets Anki's play
button, autoplay and Replay — which is why the template does not wrap it: a
recording left as an address is upgraded to an ``<audio>`` player by a small
script on the card instead (``card_layout._AUDIO_SCRIPT``). Either way the
template is the same whether or not anything was fetched, so a fetch that fails
once and succeeds next time changes a field, never the note type.

Names start with ``_`` so Anki's Check Media leaves them alone: a bare name in a
field is not a reference Anki recognises, and an underscore file is kept.
"""

import hashlib
import json
import re
from urllib.parse import quote
from urllib.parse import unquote
from urllib.parse import urlsplit

# Every file this add-on puts in a collection's media folder starts with this.
PREFIX = "_sc-"

# Commons' thumbnail steps are fixed (asking for 640px is refused); 500 is the
# one the example workbook already links, ~40 KB a picture.
COMMONS_THUMB = 500

# Past these a file stays a link. The total is per package or per sync.
FILE_LIMIT = 20 * 1024 * 1024
TOTAL_LIMIT = 100 * 1024 * 1024

# Commons answers up to fifty titles per query.
COMMONS_BATCH = 50

COMMONS_API = "https://commons.wikimedia.org/w/api.php"

# The kinds that travel. Video is a framed player and stays one.
KINDS = ("image", "audio")

_IMAGE_EXT = ("jpg", "jpeg", "png", "gif", "webp", "svg")
_AUDIO_EXT = ("mp3", "m4a", "aac", "ogg", "oga", "opus", "wav", "flac")
# Commons recordings Anki on an iPhone cannot play, fetched as Commons' MP3.
_TRANSCODED = ("ogg", "oga", "opus", "wav", "flac")

_TYPE_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
    "image/svg+xml": "svg",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/mp4": "m4a",
    "audio/x-m4a": "m4a",
    "audio/aac": "aac",
    "audio/ogg": "ogg",
    "application/ogg": "ogg",
    "audio/opus": "opus",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/wave": "wav",
    "audio/flac": "flac",
}

_COMMONS_PAGE = re.compile(
    r"^https://commons\.(?:m\.)?wikimedia\.org/wiki/"
    r"(?:Special:FilePath/|Special:Redirect/file/|File:)([^?#]+)",
    re.I,
)
# An original on the upload host (not a thumbnail or a transcode, which are
# already the file someone chose).
_COMMONS_UPLOAD = re.compile(
    r"^https://upload\.wikimedia\.org/wikipedia/commons/[0-9a-f]/[0-9a-f]{2}/([^/?#]+)$",
    re.I,
)
_SOUND = re.compile(r"^\[sound:([^\]]+)\]$")


def _ext(path):
    """The lower-cased extension of an address's path, or ''."""
    tail = unquote(urlsplit(path).path).rsplit("/", 1)[-1]
    return tail.rsplit(".", 1)[-1].lower() if "." in tail else ""


def address(value):
    """The cell as an address worth fetching, or None.

    https only: a browser will not read http from an https page, and the add-on
    does not fetch over a connection that can be tampered with.
    """
    url = str(value or "").strip()
    return url if re.match(r"^https://[^\s/]+/\S*$", url) else None


def commons_title(url):
    """The Commons file an address names (``'En-us-book.ogg'``), or None."""
    url = url.split("?", 1)[0].split("#", 1)[0] if "upload." in url else url
    match = _COMMONS_PAGE.match(url) or _COMMONS_UPLOAD.match(url)
    if not match:
        return None
    title = unquote(match.group(1)).replace("_", " ").strip()
    # MediaWiki capitalises a title's first letter, and answers under it.
    return title[:1].upper() + title[1:] if title else None


def _kind_ext(kind, ext):
    return ext in (_IMAGE_EXT if kind == "image" else _AUDIO_EXT)


def file_name(url, kind, content_type=""):
    """The name a fetched address is stored under, the same on every device.

    Derived from the address alone — never from the bytes, which a browser and a
    desktop may be served differently — so a sync and an import of one sheet
    write one name. The extension comes from the address when it has a usable
    one (``.svg`` on Commons is fetched as a PNG thumbnail, an Ogg recording as
    MP3) and from the answer's type otherwise.

    Returns:
        str | None: ``_sc-<16 hex>.<ext>``, or None when no extension can be told
    """
    ext = _ext(url)
    if commons_title(url):
        title_ext = _ext("x/" + commons_title(url))
        if kind == "image" and title_ext == "svg":
            ext = "png"
        elif kind == "audio" and title_ext in _TRANSCODED:
            ext = "mp3"
        else:
            ext = title_ext
    if ext == "jpeg":
        ext = "jpg"
    if not _kind_ext(kind, ext):
        ext = _TYPE_EXT.get(_mime(content_type), "")
        if not _kind_ext(kind, ext):
            return None
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    return f"{PREFIX}{digest}.{ext}"


def _mime(content_type):
    return str(content_type or "").split(";", 1)[0].strip().lower()


def accepts(kind, content_type):
    """Whether an answer is the kind of file the column said it holds.

    A sign-in page or an error page answered with 200 is not a picture.
    """
    mime = _mime(content_type)
    if kind == "image":
        return mime.startswith("image/")
    return mime.startswith("audio/") or mime == "application/ogg"


def jobs(rows, plan, sheet_config):
    """Every address the rows' picture and recording columns hold, once each.

    Returns:
        list[dict]: ``{"url", "kind", "name", "commons"}`` — ``name`` is None when
        only the answer's type can tell the extension, ``commons`` the Commons
        title to resolve first (or None for an address fetched as written)
    """
    seen, out = set(), []
    kinds = {
        h: sheet_config.for_field(h).media
        for h in plan.content_headers
        if sheet_config.for_field(h).media in KINDS
    }
    for row in rows:
        for header, kind in kinds.items():
            url = address(row.get(header))
            if not url or url in seen:
                continue
            seen.add(url)
            out.append(
                {
                    "url": url,
                    "kind": kind,
                    "name": file_name(url, kind),
                    "commons": commons_title(url),
                }
            )
    return out


def commons_queries(titles):
    """The API addresses that resolve these Commons titles, fifty at a time.

    ``origin=*`` is what makes Commons answer a browser; the add-on sends the
    same query so both read the same answer.
    """
    titles = sorted(set(titles))
    out = []
    for start in range(0, len(titles), COMMONS_BATCH):
        batch = "|".join("File:" + t for t in titles[start : start + COMMONS_BATCH])
        out.append(
            f"{COMMONS_API}?action=query&format=json&origin=*"
            f"&prop=imageinfo%7Cvideoinfo&iiprop=url%7Cmime&iiurlwidth={COMMONS_THUMB}"
            f"&viprop=derivatives&titles={quote(batch, safe='')}"
        )
    return out


def _clean(url):
    """Commons' tracking parameters off an upload address."""
    return url.split("?", 1)[0] if "wikimedia.org/" in url else url


def commons_sources(answers):
    """What each Commons title is fetched from, read off the API's answers.

    Args:
        answers (list[str | dict]): the API's JSON answers

    Returns:
        dict: ``{title: {"image": url, "audio": url}}``, each kind present only
        when Commons has a file of it that can be played everywhere
    """
    out = {}
    for answer in answers:
        data = json.loads(answer) if isinstance(answer, str) else answer
        for page in ((data or {}).get("query") or {}).get("pages", {}).values():
            if "missing" in page or "invalid" in page:
                continue
            title = str(page.get("title", ""))
            title = title.split(":", 1)[1] if ":" in title else title
            found = {}
            info = (page.get("imageinfo") or [{}])[0]
            mime = _mime(info.get("mime"))
            if mime.startswith("image/") and info.get("thumburl"):
                found["image"] = _clean(info["thumburl"])
            if mime == "audio/mpeg" and info.get("url"):
                found["audio"] = _clean(info["url"])
            elif mime.startswith("audio/") or mime == "application/ogg":
                video = (page.get("videoinfo") or [{}])[0]
                for d in video.get("derivatives") or []:
                    if _mime(d.get("type")) == "audio/mpeg" and d.get("src"):
                        found["audio"] = _clean(d["src"])
                        break
            out[title] = found
    return out


def source(job, commons):
    """The address a job's bytes are fetched from, or None to leave it a link."""
    if job["commons"]:
        return (commons.get(job["commons"]) or {}).get(job["kind"])
    return job["url"]


def settle(job, content_type, size):
    """The name a fetched answer is stored under, or None to keep the link.

    The single place the rules for keeping a file are applied, so a browser and
    the add-on refuse the same answers.
    """
    if not accepts(job["kind"], content_type) or not 0 < int(size) <= FILE_LIMIT:
        return None
    return job["name"] or file_name(job["url"], job["kind"], content_type)


def field_value(kind, name):
    """What a field holds once its file is in the media folder."""
    return f"[sound:{name}]" if kind == "audio" else name


def embed(note_data, plan, sheet_config, names):
    """Points a row's media cells at the files that were fetched, in place.

    Args:
        names (dict): ``{address: file name}`` for every address now in the
            media folder; an address not in it keeps its cell
    """
    for header in plan.content_headers:
        kind = sheet_config.for_field(header).media
        if kind not in KINDS:
            continue
        url = address(note_data.get(header))
        if url and url in names:
            note_data[header] = field_value(kind, names[url])


def embedded_name(value):
    """The media file a field points at, if it is one of ours (else None)."""
    text = str(value or "").strip()
    match = _SOUND.match(text)
    name = match.group(1) if match else text
    return name if name.startswith(PREFIX) and "/" not in name else None
