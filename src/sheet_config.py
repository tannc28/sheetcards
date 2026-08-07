"""The optional second header row, where a sheet describes how its cards look.

Row 1 names the columns. If the cell under ``ID`` in row 2 starts with ``#config``,
row 2 is read as per-column presentation directives and row 3 onwards is data.
Without that marker there is no config row and row 2 is an ordinary data row, so
sheets written before this feature existed keep working untouched.

Each cell holds ``key=value`` pairs separated by ``;``; a key with no value is a
flag. An empty cell means "use the defaults", so a sheet only spells out what it
actually wants to change::

    ID       SYNC   SUBDECK 1   Word                      Reading   Meaning
    #config                     side=front; size=48; tts=zh_CN   size=20   size=16; color=muted; hint

The deck-wide settings live in the ``#config`` cell itself: ``#config align=left``.
"""

import re

MARKER = "#config"

# Anki's TTS tag is `{{tts LANG [voices=A,B] [speed=N]:Field}}` and it matches a tag
# to an installed voice by comparing the language strings *exactly*
# (aqt/tts.py: `if avail.lang == tag.lang`). Voice languages are always the full
# form — `voice.language.replace("-", "_")` — so a bare "zh" matches nothing and
# plays silently. Full codes are therefore required, and the only normalisation is
# the separator and the casing, which cannot change which voice is chosen.

# Colours that follow the card's light/dark theme. A literal colour is allowed too,
# but a hard-coded "black" vanishes in night mode, so these are what the docs push.
THEME_COLORS = {
    "muted": "var(--s2a-muted)",
    "accent": "var(--s2a-accent)",
}

SIDES = ("front", "back", "hide")
ALIGNMENTS = ("left", "center", "right")

_FLAGS = ("bold", "italic", "hint", "furigana")

# Turn a bare URL in the cell into a media element instead of printing it as
# text. One field is one kind of media, so these are recorded as a single
# value rather than three independent switches.
MEDIA_KINDS = ("image", "audio", "video")
_FIELD_KEYS = (
    (
        "side",
        "size",
        "color",
        "align",
        "tts",
        "voices",
        "speed",
        "label",
    )
    + _FLAGS
    + MEDIA_KINDS
)
_DECK_KEYS = ("align", "speed", "reverse")

_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
# Full form only: a language plus a region, e.g. zh_CN, en_US, pt_BR, zh-TW.
_LANG_RE = re.compile(r"^[a-zA-Z]{2,3}[-_][a-zA-Z0-9]{2,4}$")

# The CSS named colours. Validating against the real list matters: a plain
# "[a-z]+ is a colour" rule accepts a typo like "grey1" or "notacolour", the card
# silently renders with no colour at all, and nothing tells the user why.
_CSS_COLOR_NAMES = frozenset(
    """aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond
    blue blueviolet brown burlywood cadetblue chartreuse chocolate coral cornflowerblue
    cornsilk crimson cyan darkblue darkcyan darkgoldenrod darkgray darkgreen darkgrey
    darkkhaki darkmagenta darkolivegreen darkorange darkorchid darkred darksalmon
    darkseagreen darkslateblue darkslategray darkslategrey darkturquoise darkviolet
    deeppink deepskyblue dimgray dimgrey dodgerblue firebrick floralwhite forestgreen
    fuchsia gainsboro ghostwhite gold goldenrod gray green greenyellow grey honeydew
    hotpink indianred indigo ivory khaki lavender lavenderblush lawngreen lemonchiffon
    lightblue lightcoral lightcyan lightgoldenrodyellow lightgray lightgreen lightgrey
    lightpink lightsalmon lightseagreen lightskyblue lightslategray lightslategrey
    lightsteelblue lightyellow lime limegreen linen magenta maroon mediumaquamarine
    mediumblue mediumorchid mediumpurple mediumseagreen mediumslateblue
    mediumspringgreen mediumturquoise mediumvioletred midnightblue mintcream mistyrose
    moccasin navajowhite navy oldlace olive olivedrab orange orangered orchid
    palegoldenrod palegreen paleturquoise palevioletred papayawhip peachpuff peru pink
    plum powderblue purple rebeccapurple red rosybrown royalblue saddlebrown salmon
    sandybrown seagreen seashell sienna silver skyblue slateblue slategray slategrey
    snow springgreen steelblue tan teal thistle tomato turquoise violet wheat white
    whitesmoke yellow yellowgreen transparent currentcolor""".split()
)


def is_config_row(row, plan):
    """True when this row is the directive row rather than data.

    The marker cell may carry the deck-wide settings after it
    (``#config align=left``), so the test is on the leading token, not the cell.
    """
    if not plan.id_header:
        return False
    cell = str(row.get(plan.id_header, "")).strip().lower()
    if not cell.startswith(MARKER):
        return False
    # Anything directly after the marker must be a separator, never more word
    # characters — otherwise a column genuinely called "#configuration" would be
    # swallowed. A missing space (`#config;align=left`) is still accepted, because
    # the alternative is silently importing the settings row as a note.
    rest = cell[len(MARKER) :]
    return rest == "" or not rest[0].isalnum()


def normalize_tts_language(value):
    """Puts a full language code into the exact shape Anki compares against.

    Only the separator and the casing are touched — `zh-cn` and `zh_CN` name the
    same voice, so accepting both cannot pick a different one. A bare `zh` is
    rejected by the caller rather than guessed at, because guessing `zh_CN` for
    someone studying Traditional Chinese would be wrong and silent.
    """
    code = str(value or "").strip().replace("-", "_")
    if "_" not in code:
        return None
    head, tail = code.split("_", 1)
    return f"{head.lower()}_{tail.upper()}"


def _parse_pairs(text):
    """Splits ``a=1; b; c=2`` into ``[("a","1"), ("b",None), ("c","2")]``."""
    pairs: list[tuple[str, str | None]] = []
    for chunk in str(text or "").split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" in chunk:
            key, value = chunk.split("=", 1)
            pairs.append((key.strip().lower(), value.strip()))
        else:
            pairs.append((chunk.lower(), None))
    return pairs


class FieldConfig:
    """How one column is presented. Every attribute is None/False when unset."""

    def __init__(self):
        self.side = None
        self.size = None
        self.color = None
        self.align = None
        self.tts = None
        self.voices = []
        self.speed = None
        self.label = None
        self.media = None  # "image" | "audio" | "video"
        self.bold = False
        self.italic = False
        self.hint = False
        self.furigana = False

    @property
    def hidden(self):
        return self.side == "hide"

    def __repr__(self):  # pragma: no cover - debugging aid
        set_keys = {k: v for k, v in vars(self).items() if v not in (None, False, [])}
        return f"FieldConfig({set_keys})"


class SheetConfig:
    """The parsed config row: per-field settings plus the deck-wide ones.

    ``warnings`` collects everything that looked like a mistake — an unknown key, a
    colour that is not a colour — so the add-on can show the user what it did not
    understand instead of silently ignoring a typo.
    """

    def __init__(self):
        self.present = False
        self.fields = {}
        self.align = None
        self.speed = None
        self.reverse = False
        self.warnings = []

    def for_field(self, header):
        return self.fields.get(header) or FieldConfig()


# A flag written with a value is honoured rather than ignored: `bold=false` reads as
# "no bold" to anyone, and silently turning bold ON would be the opposite of what the
# sheet says.
_FALSEY = frozenset({"false", "no", "0", "off", "none"})


def _apply_field_pair(cfg, key, value, header, warn):
    if key in MEDIA_KINDS:
        if value is not None and value.strip().lower() in _FALSEY:
            return
        if cfg.media and cfg.media != key:
            warn(
                f"'{header}': already set to {cfg.media}, ignoring '{key}' — "
                f"a column holds one kind of media"
            )
            return
        cfg.media = key
        return

    if key in _FLAGS:
        setattr(cfg, key, value is None or value.strip().lower() not in _FALSEY)
        return

    if value is None:
        warn(f"'{header}': '{key}' needs a value (write {key}=…)")
        return

    if key == "side":
        if value.lower() in SIDES:
            cfg.side = value.lower()
        else:
            warn(f"'{header}': side must be one of {', '.join(SIDES)} — got '{value}'")
    elif key == "align":
        if value.lower() in ALIGNMENTS:
            cfg.align = value.lower()
        else:
            warn(f"'{header}': align must be left, center or right — got '{value}'")
    elif key == "size":
        try:
            cfg.size = int(float(value.rstrip("px").strip()))
        except ValueError:
            warn(f"'{header}': size must be a number of pixels — got '{value}'")
    elif key == "color":
        lowered = value.lower()
        if lowered in THEME_COLORS or lowered in _CSS_COLOR_NAMES:
            cfg.color = lowered
        elif _HEX_RE.match(value):
            cfg.color = value
        else:
            warn(f"'{header}': '{value}' is not a colour name or #hex value")
    elif key == "tts":
        if _LANG_RE.match(value):
            cfg.tts = normalize_tts_language(value)
        else:
            warn(
                f"'{header}': tts needs a full language code such as zh_CN or "
                f"en_US — got '{value}'. Anki matches the code against installed "
                f"voices exactly, so a short code plays nothing."
            )
    elif key == "voices":
        names = [v.strip() for v in value.split(",") if v.strip()]
        if names:
            cfg.voices = names
        else:
            warn(f"'{header}': voices needs at least one voice name")
    elif key == "speed":
        try:
            speed = float(value)
        except ValueError:
            warn(f"'{header}': speed must be a number — got '{value}'")
            return
        if not 0.5 <= speed <= 2.0:
            warn(f"'{header}': speed {speed} is outside 0.5–2.0")
            return
        cfg.speed = speed
    elif key == "label":
        cfg.label = value


def parse_config_row(row, plan):
    """Reads the directive row into a :class:`SheetConfig`.

    Args:
        row (dict): the row, keyed by header, whose ID cell holds ``#config``
        plan (ColumnPlan): the sheet's column roles

    Returns:
        SheetConfig
    """
    config = SheetConfig()
    config.present = True

    def warn(message):
        config.warnings.append(message)

    # Deck-wide settings ride along in the marker cell: "#config align=left".
    marker_cell = str(row.get(plan.id_header, "")).strip()
    remainder = marker_cell[len(MARKER) :] if len(marker_cell) > len(MARKER) else ""
    for key, value in _parse_pairs(remainder):
        if key not in _DECK_KEYS:
            warn(f"'{MARKER}': unknown deck setting '{key}'")
        elif key == "reverse":
            config.reverse = value is None or value.strip().lower() not in _FALSEY
        elif value is None:
            warn(f"'{MARKER}': '{key}' needs a value")
        elif key == "align":
            if value.lower() in ALIGNMENTS:
                config.align = value.lower()
            else:
                warn(f"'{MARKER}': align must be left, center or right")
        elif key == "speed":
            try:
                speed = float(value)
            except ValueError:
                warn(f"'{MARKER}': speed must be a number — got '{value}'")
            else:
                if 0.5 <= speed <= 2.0:
                    config.speed = speed
                else:
                    warn(f"'{MARKER}': speed {speed} is outside 0.5–2.0")

    for header in plan.content_headers:
        cell = str(row.get(header, "")).strip()
        if not cell:
            continue

        cfg = FieldConfig()
        for key, value in _parse_pairs(cell):
            if key not in _FIELD_KEYS:
                warn(f"'{header}': unknown setting '{key}'")
                continue
            _apply_field_pair(cfg, key, value, header, warn)

        # `size` is a font size on a text column and a width on a media one, so the
        # sane range depends on a key that may be written after it in the same cell.
        # Checking here rather than while parsing makes `size=320; image` work.
        if cfg.size is not None:
            low, high = (1, 2000) if cfg.media else (6, 200)
            if not low <= cfg.size <= high:
                what = "width" if cfg.media else "font size"
                warn(f"'{header}': {what} {cfg.size}px is outside {low}–{high}px")
                cfg.size = None

        # A media column holds a URL, so these would act on the address itself:
        # tts would read the URL out loud, furigana would try to annotate it.
        if cfg.media:
            if cfg.tts:
                warn(
                    f"'{header}': tts on a {cfg.media} column would read the URL "
                    f"aloud — removed"
                )
                cfg.tts = None
                cfg.voices = []
            if cfg.furigana:
                warn(f"'{header}': furigana does nothing on a {cfg.media} column")
                cfg.furigana = False

            # Text styling has nothing to style: the cell renders as an element,
            # not as words. Saying so beats leaving the setting quietly inert.
            inert = [
                name
                for name, on in (
                    ("color", cfg.color),
                    ("bold", cfg.bold),
                    ("italic", cfg.italic),
                    ("align", cfg.align),
                )
                if on
            ]
            if inert:
                warn(
                    f"'{header}': {', '.join(inert)} "
                    f"{'do' if len(inert) > 1 else 'does'} nothing on a "
                    f"{cfg.media} column"
                )
            if cfg.media == "audio" and cfg.size is not None:
                warn(f"'{header}': size does nothing on an audio column")
                cfg.size = None

        config.fields[header] = cfg

    return config
