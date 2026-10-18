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
    "muted": "var(--sc-muted)",
    "accent": "var(--sc-accent)",
}

# A whole-card palette, named once in the marker cell: `#config theme=sakura`.
#
# Each theme is given twice because Anki, not the sheet, decides at review time
# whether the card is drawn light or dark — it puts a `night_mode` class on the
# card's body. One set of colours would therefore leave one of the two modes
# unreadable, which is the same reason THEME_COLORS above exists at all. The two
# named colours are part of the palette rather than fixed alongside it, so a column
# written `color=accent` follows whatever theme the sheet chose.
#
# `fg` is the card's own text colour, so it has to carry real contrast against `bg`
# rather than merely being in the same family: the palette is the one thing here
# that a sheet cannot correct per column.
#
# `petal`/`heart`/`veil` are the optional fourth part: a theme named after a season
# owes the card more than that season's colour, so a variant carrying them gets a
# pattern strewn behind the text (drawn by `card_layout`, from these colours).
# `motif` says which pattern — `blossom` (the default), `maple` or `snow` — and sits
# beside the variants like `sign`, because a leaf does not change shape at night.
# `petal` is the motif's main colour and `heart` its second. `veil` is how faint
# they are — the pattern is wallpaper, and wallpaper that competes with the word
# being learned has failed at being wallpaper. A theme with no `petal` is simply a
# palette.
#
# Every `fg` reaches 7:1 against its `bg` and every `muted`/`accent` 4.5:1, in both
# variants; `tests/test_card_layout.py` measures it, since a theme is the one thing
# a sheet cannot correct per column.
#
# `sign` is who the theme was made for, drawn small in the corner of every card it
# paints (again by `card_layout`). It sits beside the two variants rather than
# inside them because a name does not change with the light. A theme without one is
# simply not signed. The annotation is what keeps `sign` from narrowing the whole
# table to its values' common type, which would leave the two variants unindexable.
_SAKURA = {
    "light": {
        "bg": "#fff5f8",
        "fg": "#43262f",
        "muted": "#8a6271",
        "accent": "#c4285e",
        "petal": "#f7bdd0",
        "heart": "#ef9ab6",
        "veil": "0.5",
    },
    "night": {
        "bg": "#2a1d23",
        "fg": "#f2dee5",
        "muted": "#bd97a4",
        "accent": "#ff8fb1",
        "petal": "#7a4a5c",
        "heart": "#95586c",
        "veil": "0.55",
    },
}

# `ptrang` is the VIP edition of `sakura`: the same palette and blossoms, plus the
# signed corner. `sakura` itself stays unsigned.
THEMES: dict[str, dict] = {
    # Plain palettes: chosen for reading, not for a season.
    # Warm paper and ink — the calmest of them for a long session.
    "paper": {
        "light": {"bg": "#faf6ee", "fg": "#2b2620", "muted": "#6b604f", "accent": "#9a4a1f"},
        "night": {"bg": "#1f1b16", "fg": "#ece4d6", "muted": "#b3a794", "accent": "#e8a878"},
    },
    # As much contrast as a screen has, for weak eyes or a phone in the sun.
    "contrast": {
        "light": {"bg": "#ffffff", "fg": "#000000", "muted": "#3d3d3d", "accent": "#0039a6"},
        "night": {"bg": "#000000", "fg": "#ffffff", "muted": "#d0d0d0", "accent": "#ffd400"},
    },
    # Soft green tea.
    "matcha": {
        "light": {"bg": "#f3f7ee", "fg": "#24321f", "muted": "#56664f", "accent": "#3f6b2c"},
        "night": {"bg": "#18211a", "fg": "#e3ecdc", "muted": "#a3b39b", "accent": "#9cc98a"},
    },
    # The seasons, each with its pattern.
    "sakura": _SAKURA,
    "momiji": {
        "motif": "maple",
        "light": {
            "bg": "#fff7f2", "fg": "#3a2218", "muted": "#80594a", "accent": "#b23c0c",
            "petal": "#f4b79c", "heart": "#eb9a74", "veil": "0.5",
        },
        "night": {
            "bg": "#241a16", "fg": "#f3e2d8", "muted": "#c09c8c", "accent": "#ff9a66",
            "petal": "#6e3b28", "heart": "#84452c", "veil": "0.55",
        },
    },
    "yuki": {
        "motif": "snow",
        "light": {
            "bg": "#f5f8fc", "fg": "#1d2a3a", "muted": "#56677d", "accent": "#2c5a92",
            "petal": "#b9cde6", "heart": "#cfdcee", "veil": "0.7",
        },
        "night": {
            "bg": "#151c26", "fg": "#e2eaf4", "muted": "#9fb0c4", "accent": "#8fb8ea",
            "petal": "#3a4c64", "heart": "#2f3f55", "veil": "0.7",
        },
    },
    "ptrang": {**_SAKURA, "sign": "Mèo"},
}  # fmt: skip

# Themes that work when named but are never offered: left out of the list an
# unknown name is answered with and out of the editor's picker.
UNLISTED_THEMES = frozenset({"ptrang"})


def listed_themes():
    """The theme names a sheet is told about, in a stable order."""
    return sorted(name for name in THEMES if name not in UNLISTED_THEMES)


# Fonts a sheet can name, and the stack each becomes. The first four are loaded
# from Google Fonts by `card_layout` when a column asks for one; the rest are
# whatever the machine already has.
#
# This exists because of Han unification: 直, 骨, 画 and a few hundred others are
# one code point with a different *shape* in Chinese, Japanese and Korean, and a
# machine with only a Japanese CJK font draws a Chinese deck in Japanese shapes.
# Nothing on the card can say which language the text is in — the sheet has to.
FONTS = {
    "sc": ("Noto Sans SC", "Noto Sans SC, sans-serif"),
    "tc": ("Noto Sans TC", "Noto Sans TC, sans-serif"),
    "jp": ("Noto Sans JP", "Noto Sans JP, sans-serif"),
    "kr": ("Noto Sans KR", "Noto Sans KR, sans-serif"),
    "serif": (None, "Georgia, 'Times New Roman', serif"),
    "sans": (None, "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"),
    "mono": (None, "ui-monospace, 'SF Mono', Menlo, Consolas, monospace"),
}

SIDES = ("front", "back", "hide")
ALIGNMENTS = ("left", "center", "right")

# `cloze` marks the one column whose text carries {{c1::…}} deletions. It is a
# property of the sheet, not of a row: the note type and its template are shared by
# every row, so the column has to be declared once rather than guessed per row.
#
# `draw` turns the column into a stroke-by-stroke writing box instead of printing
# its text: on the question you draw the character yourself and it marks each
# stroke, on the answer it animates the correct strokes. Which of the two you get
# is decided by the side the column lands on, because that is the only thing that
# distinguishes "ask me" from "show me" — a second directive would be a second way
# of saying where the column already is.
# `sort` is not about the card at all: it names the column Anki should show in the
# browser's first column and sort a deck by. Without it that column is `ID`, so a
# sheet's notes are listed as w01, w02, w03 — a list of nothing.
#
# `rtl` and `vertical` are the two writing directions HTML has and a sheet cannot
# otherwise ask for: Arabic and Hebrew run right to left, and classical Japanese
# and Chinese run top to bottom.
_FLAGS = (
    "bold",
    "italic",
    "hint",
    "furigana",
    "cloze",
    "draw",
    "sort",
    "rtl",
    "vertical",
)

# Turn a bare URL in the cell into a media element instead of printing it as
# text. One field is one kind of media, so these are recorded as a single
# value rather than three independent switches.
#
# `video` covers every video link, because what people actually paste is a
# YouTube or Drive address — a page with a player on it, not a video file. Those
# have to be framed, so the column renders an <iframe> and the address is
# rewritten to that site's player URL at sync time by
# tsv_model.normalize_embed_url. A direct .mp4 is passed through and plays in the
# frame as well, so one word covers both and nobody has to know which they have.
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
        "type",
        # Which level of the deck path this column is — the same job a reserved
        # `SUBDECK n` header does, said from an ordinary column instead, so the
        # sheet does not have to give a column one of the add-on's own names.
        # The column stays a field on the note and is never drawn on the card:
        # where a note is filed is a bigger thing than how one card looks.
        "subdeck",
        # A formula, drawn by the MathJax Anki already ships. Bare `math` is
        # inline; `math=block` is the centred display form.
        "math",
        # Source code, kept as typed and coloured by language.
        "code",
        # Which typeface the column is drawn in — see FONTS.
        "font",
    )
    + _FLAGS
    + MEDIA_KINDS
)
_DECK_KEYS = ("align", "speed", "reverse", "theme", "name", "next", "shape")

# Two keys that are about the sheet rather than its cards, written by Create
# sheet into the marker cell: `#config name=Từ vựng tiếng Anh; next=w15`.
#
# `name` is the deck's name in Anki *and* the sheet's identity. A file is
# renamed by the phone that saves it (`Từ vựng (1).csv`), re-saved as .xlsx,
# uploaded to Google Sheets — and each of those changed what the website keyed
# notes by, so every re-import doubled the deck. A name written inside the sheet
# travels with it through all of them. Two sheets with one name are
# therefore one deck, which is why Create sheet asks for a name and warns about
# one already used. `next` is the next ID Create sheet will hand out, so a
# deleted word's ID is never given to a new word that would then inherit its
# review history.
#
# The add-on accepts both and needs neither: it matches notes by deck and by the
# ID field. Values may hold spaces and any script; only `;` cannot be written,
# being the separator.
_DECK_NAME_MAX = 100
_NEXT_ID_RE = re.compile(r"^[^\s;]{0,16}?\d{1,9}$")
# What the note type looked like at the last .apkg download — apkg.shape_code: the
# kind, then four hex digits of the fields and two of the card templates.
_SHAPE_RE = re.compile(r"^[bc][0-9a-f]{6}$")

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


# Everything a column can say that only affects how a card looks. A `subdeck=n`
# column is not part of the card, so all of these are inert on one — named rather
# than silently dropped, like every other refused setting.
_CARD_KEYS = (
    "side",
    "size",
    "color",
    "align",
    "tts",
    "voices",
    "speed",
    "label",
    "type_answer",
    "bold",
    "italic",
    "hint",
    "furigana",
    "cloze",
    "draw",
)
_SAID_AS = {"type_answer": "type"}
_EMPTY = dict.fromkeys(_FLAGS, False)
_EMPTY.update(
    dict.fromkeys(
        ("side", "size", "color", "align", "tts", "speed", "label", "type_answer")
    )
)
_EMPTY["voices"] = []


def is_config_row(row, plan):
    """True when this row is the directive row rather than data.

    The marker cell may carry the deck-wide settings after it
    (``#config align=left``), so the test is on the leading token, not the cell.
    """
    # A sheet keyed by its first content column has no ID cell to carry the
    # marker in; that column's cell is a word, whatever it says.
    if not plan.id_header or getattr(plan, "id_from", None):
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
        self.type_answer = None  # None | "plain" | "nc" — Anki's {{type:…}} box
        self.subdeck = None  # int — this column is that level of the deck path
        self.math = None  # None | "inline" | "block" — drawn by MathJax
        self.code = None  # None | "" | a language name — drawn as source code
        self.font = None  # a key of FONTS, or a family name to use as written
        self.bold = False
        self.italic = False
        self.hint = False
        self.furigana = False
        self.cloze = False
        self.draw = False
        self.sort = False
        self.rtl = False
        self.vertical = False

    @property
    def hidden(self):
        return self.side == "hide"

    def __repr__(self):  # pragma: no cover - debugging aid
        set_keys = {k: v for k, v in vars(self).items() if v not in (None, False, [])}
        return f"FieldConfig({set_keys})"


class SheetWarning(str):
    """One thing the settings row got wrong: the English sentence, plus a code.

    It *is* the sentence — the add-on, the sync summary, the log and the cache all
    treat warnings as text — and it also carries a stable ``code`` and the
    ``params`` that filled the sentence, so Sheet to Anki can say the same thing
    in Vietnamese (``site/i18n.js``, keys ``w:<code>``) and fall back to this
    text for a code it does not know.
    """

    code = ""
    params: dict = {}

    def __new__(cls, text, code="", params=None):
        self = super().__new__(cls, text)
        self.code = code
        self.params = {k: str(v) for k, v in (params or {}).items()}
        return self


# Every code a warning can carry. site/sheetwarnings.js says each of them in both
# languages, and tests/test_site_warnings.py holds the two lists together.
WARNING_CODES = (
    "media-twice", "math-mode", "type-mode", "needs-value", "side-bad",
    "font-empty", "align-bad", "size-nan", "color-bad", "tts-short",
    "voices-empty", "speed-nan", "speed-range", "subdeck-nan", "subdeck-low",
    "media-subdeck", "subdeck-inert", "only-one-cloze", "only-one-type",
    "only-one-sort", "sort-media", "role-media", "level-twice",
    "subdeck-headers-ignored", "deck-unknown", "deck-needs-value",
    "deck-align-bad", "theme-unknown", "deck-speed-nan", "deck-speed-range",
    "name-long", "name-empty-level", "next-bad", "shape-bad", "unknown-setting",
    "size-range-width", "size-range-box", "size-range-font", "media-tts",
    "furigana-on", "inert-on", "media-drawn", "audio-size", "draw-media",
    "draw-cloze", "math-and-code", "draw-drops", "cloze-drops", "rtl-vertical",
    # raised by tsv_model while the rows are read
    "embed-not-single", "cloze-unmarked",
)  # fmt: skip


def _w(code, text, **params):
    return SheetWarning(text, code, params)


def warning_codes(warnings):
    """``[{"code", "params", "text"}]`` for a list of warnings, for the site."""
    return [
        {
            "code": getattr(w, "code", ""),
            "params": dict(getattr(w, "params", {}) or {}),
            "text": str(w),
        }
        for w in warnings
    ]


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
        self.theme = None  # a key of THEMES; None leaves the card Anki's own colours
        # `name=` (the deck's name and the sheet's identity) and `next=` (the
        # next ID to hand out) — see _DECK_KEYS. None when the sheet does not say.
        self.deck_name = None
        self.next_id = None
        # The note type's shape at the last download (apkg.shape_code), written by
        # Create sheet so the merge notice is right on a device that never
        # downloaded this sheet. None when the sheet does not say.
        self.shape = None
        self.warnings = []
        # The column carrying cloze deletions, and the one Anki asks the learner to
        # type. Both are single because a note type has one template set and Anki
        # honours one {{type:…}} per card.
        self.cloze_field = None
        self.type_field = None
        # The column the browser lists notes under and sorts a deck by. Without one
        # that is field 0, which is `ID` — a list of w01, w02, w03.
        self.sort_field = None
        # The content columns that build the deck path, outermost first. Empty
        # when the sheet says nothing, and then column_model.deck_path falls back
        # to the reserved SUBDECK columns.
        self.subdeck_columns = []

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
                _w(
                    "media-twice",
                    f"'{header}': already set to {cfg.media}, ignoring '{key}' — "
                    f"a column holds one kind of media",
                    col=header,
                    media=cfg.media,
                    key=key,
                )
            )
            return
        cfg.media = key
        return

    if key in _FLAGS:
        setattr(cfg, key, value is None or value.strip().lower() not in _FALSEY)
        return

    if key == "math":
        # Bare is inline, which is what a formula in a sentence wants; `block` is
        # the centred display form for a formula that is the whole answer.
        mode = (value or "inline").strip().lower()
        if mode in ("inline", "block"):
            cfg.math = mode
        else:
            warn(
                _w(
                    "math-mode",
                    f"'{header}': math is written bare or as math=block — got '{value}'",
                    col=header,
                    value=value,
                )
            )
        return

    if key == "code":
        # The language is a hint for the colouring and nothing else: an unknown one
        # simply colours nothing, so it is taken as written rather than checked
        # against a list this file would have to keep in step with a library.
        cfg.code = (value or "").strip().lower()
        return

    if key == "type":
        # Anki compares what the learner types against this field. Bare `type` is an
        # exact comparison; `type=nc` ignores diacritics, which is what someone
        # typing pinyin without tone marks wants.
        mode = (value or "plain").strip().lower()
        if mode in ("plain", "nc"):
            cfg.type_answer = mode
        else:
            warn(
                _w(
                    "type-mode",
                    f"'{header}': type must be written bare or as type=nc — got '{value}'",
                    col=header,
                    value=value,
                )
            )
        return

    if value is None:
        warn(
            _w(
                "needs-value",
                f"'{header}': '{key}' needs a value (write {key}=…)",
                col=header,
                key=key,
            )
        )
        return

    if key == "side":
        if value.lower() in SIDES:
            cfg.side = value.lower()
        else:
            warn(
                _w(
                    "side-bad",
                    f"'{header}': side must be one of {', '.join(SIDES)} — got '{value}'",
                    col=header,
                    value=value,
                )
            )
    elif key == "font":
        name = value.strip().strip("\"'").strip()
        if not name:
            warn(
                _w(
                    "font-empty",
                    f"'{header}': font needs a name — {', '.join(sorted(FONTS))}, "
                    f"or a family",
                    col=header,
                    fonts=", ".join(sorted(FONTS)),
                )
            )
        else:
            # A key from FONTS is a stack this add-on knows how to load; anything
            # else is passed to CSS as written, because the fonts installed on the
            # machine reviewing are not something this file can know.
            cfg.font = name.lower() if name.lower() in FONTS else name
    elif key == "align":
        if value.lower() in ALIGNMENTS:
            cfg.align = value.lower()
        else:
            warn(
                _w(
                    "align-bad",
                    f"'{header}': align must be left, center or right — got '{value}'",
                    col=header,
                    value=value,
                )
            )
    elif key == "size":
        try:
            cfg.size = int(float(value.rstrip("px").strip()))
        except ValueError:
            warn(
                _w(
                    "size-nan",
                    f"'{header}': size must be a number of pixels — got '{value}'",
                    col=header,
                    value=value,
                )
            )
    elif key == "color":
        lowered = value.lower()
        if lowered in THEME_COLORS or lowered in _CSS_COLOR_NAMES:
            cfg.color = lowered
        elif _HEX_RE.match(value):
            cfg.color = value
        else:
            warn(
                _w(
                    "color-bad",
                    f"'{header}': '{value}' is not a colour name or #hex value",
                    col=header,
                    value=value,
                )
            )
    elif key == "tts":
        if _LANG_RE.match(value):
            cfg.tts = normalize_tts_language(value)
        else:
            warn(
                _w(
                    "tts-short",
                    f"'{header}': tts needs a full language code such as zh_CN or "
                    f"en_US — got '{value}'. Anki matches the code against installed "
                    f"voices exactly, so a short code plays nothing.",
                    col=header,
                    value=value,
                )
            )
    elif key == "voices":
        names = [v.strip() for v in value.split(",") if v.strip()]
        if names:
            cfg.voices = names
        else:
            warn(
                _w(
                    "voices-empty",
                    f"'{header}': voices needs at least one voice name",
                    col=header,
                )
            )
    elif key == "speed":
        try:
            speed = float(value)
        except ValueError:
            warn(
                _w(
                    "speed-nan",
                    f"'{header}': speed must be a number — got '{value}'",
                    col=header,
                    value=value,
                )
            )
            return
        if not 0.5 <= speed <= 2.0:
            warn(
                _w(
                    "speed-range",
                    f"'{header}': speed {speed} is outside 0.5–2.0",
                    col=header,
                    value=speed,
                )
            )
            return
        cfg.speed = speed
    elif key == "label":
        cfg.label = value
    elif key == "subdeck":
        # The number is the level, exactly as it is in a `SUBDECK n` header, so
        # the two ways of saying this order their levels the same way.
        try:
            level = int(float(value))
        except ValueError:
            warn(
                _w(
                    "subdeck-nan",
                    f"'{header}': subdeck must be a level number — got '{value}'",
                    col=header,
                    value=value,
                )
            )
            return
        if level < 1:
            warn(
                _w(
                    "subdeck-low",
                    f"'{header}': subdeck level {level} is below 1",
                    col=header,
                    value=level,
                )
            )
            return
        cfg.subdeck = level


def resolve_roles(config, content_headers, subdeck_headers=(), warn=None):
    """Works out the sheet-level roles from the per-column settings.

    Three of a :class:`SheetConfig`'s attributes are not typed into any cell —
    ``cloze_field``, ``type_field`` and ``subdeck_columns`` are *derived* from what
    the columns individually asked for. This is the one place that derives them,
    because the settings row is read twice: once while parsing a sheet, and once
    when :mod:`.sync_config` rebuilds a cached one to redraw a note type outside a
    sync. A second copy of these rules would mean a cached rebuild quietly
    producing a different card from the one the sheet describes.

    Args:
        config (SheetConfig): the settings so far, with ``fields`` filled in
        content_headers (list): the sheet's content columns, in sheet order
        subdeck_headers (list): the sheet's reserved ``SUBDECK n`` columns, if any
        warn (callable): called with each complaint; ``None`` while rebuilding
            from cache, where the warnings were recorded the first time round
    """
    if warn is None:

        def warn(_message):
            return None

    # A media column holds an address. Filing notes under a deck named after a URL
    # is not something anyone meant, and get_subdeck_name would strip it to
    # something unrecognisable rather than fail, so it is refused here instead.
    # Media wins: it is the cell's *content* that is wrong for a deck name.
    for header in content_headers:
        cfg = config.for_field(header)
        if cfg.subdeck and cfg.media:
            warn(
                _w(
                    "media-subdeck",
                    f"'{header}': a {cfg.media} column cannot be a deck level",
                    col=header,
                    media=cfg.media,
                )
            )
            cfg.subdeck = None

    # A deck level is a deck level. Where a note is filed is a bigger thing than
    # how one card looks, so a column working at that level is not part of the card
    # at all — not drawn, not styled, not spoken. Every card key in the cell is
    # therefore inert, and an inert setting is named rather than left to be found.
    #
    # Done before the two resolutions below so that neither can pick a column that
    # is only there to file the note.
    for header in content_headers:
        cfg = config.for_field(header)
        if not cfg.subdeck:
            continue
        inert = [key for key in _CARD_KEYS if getattr(cfg, key)]
        if not inert:
            continue
        said = ", ".join(_SAID_AS.get(key, key) for key in inert)
        warn(
            _w(
                "subdeck-inert",
                f"'{header}': a deck level is not part of the card, so "
                + said
                + (" do" if len(inert) > 1 else " does")
                + " nothing here",
                col=header,
                keys=said,
            )
        )
        for key in inert:
            setattr(cfg, key, _EMPTY[key])

    # A note type has one template set, and Anki honours one {{type:…}} per card, so
    # each of these names exactly one column. Resolved after the whole row is read so
    # the warning can name every column that asked, not just the second one.
    for key, attribute, what, role in (
        ("cloze", "cloze_field", "carry the cloze deletions", "cloze"),
        ("type_answer", "type_field", "be typed in", "type"),
        # A note type has one sort field, which is also the column the browser
        # lists notes under.
        ("sort", "sort_field", "be the one the browser sorts by", "sort"),
    ):
        claimed = [h for h in content_headers if getattr(config.for_field(h), key)]
        if not claimed:
            continue
        setattr(config, attribute, claimed[0])
        if len(claimed) > 1:
            others = ", ".join(f"'{h}'" for h in claimed[1:])
            warn(
                _w(
                    f"only-one-{role}",
                    f"only one column can {what} — keeping '{claimed[0]}', ignoring "
                    + others,
                    col=claimed[0],
                    others=others,
                )
            )
            for header in claimed[1:]:
                setattr(
                    config.fields[header], key, None if key == "type_answer" else False
                )

    # Sorting a deck by a column of URLs lists it by whatever the addresses happen
    # to start with, which is never what was meant.
    if config.sort_field and config.for_field(config.sort_field).media:
        warn(
            _w(
                "sort-media",
                f"'{config.sort_field}': a media column is no use to sort by",
                col=config.sort_field,
            )
        )
        config.fields[config.sort_field].sort = False
        config.sort_field = None

    # Both act on the text of a field, and a media column holds an address.
    for attribute, key, label in (
        ("cloze_field", "cloze", "cloze"),
        ("type_field", "type_answer", "type"),
    ):
        header = getattr(config, attribute)
        if header and config.for_field(header).media:
            warn(
                _w(
                    "role-media",
                    f"'{header}': {label} does nothing on a media column",
                    col=header,
                    key=label,
                )
            )
            setattr(config, attribute, None)
            setattr(config.fields[header], key, None if key == "type_answer" else False)

    # The deck path, outermost first — by the level number, not by where the column
    # sits in the sheet, which is how `SUBDECK n` has always behaved.
    levels = {}
    for header in content_headers:
        level = config.for_field(header).subdeck
        if not level:
            continue
        if level in levels:
            warn(
                _w(
                    "level-twice",
                    f"'{header}': level {level} is already '{levels[level]}' — "
                    f"two columns cannot be the same level of the deck",
                    col=header,
                    value=level,
                    other=levels[level],
                )
            )
            config.fields[header].subdeck = None
            continue
        levels[level] = header
    config.subdeck_columns = [levels[level] for level in sorted(levels)]

    # Both at once is a sheet saying two different things about where its notes go.
    # The settings row is the one being read right now, so it wins — and the columns
    # it overrules are named, because a deck quietly not appearing is exactly the
    # kind of thing nobody thinks to look for.
    if config.subdeck_columns and subdeck_headers:
        named = ", ".join(f"'{h}'" for h in subdeck_headers)
        warn(
            _w(
                "subdeck-headers-ignored",
                "the settings row builds the deck path, so the reserved "
                + named
                + " column"
                + ("s are" if len(subdeck_headers) > 1 else " is")
                + " ignored",
                others=named,
            )
        )

    return config


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
            warn(
                _w(
                    "deck-unknown",
                    f"'{MARKER}': unknown deck setting '{key}'",
                    key=key,
                )
            )
        elif key == "reverse":
            config.reverse = value is None or value.strip().lower() not in _FALSEY
        elif value is None:
            warn(_w("deck-needs-value", f"'{MARKER}': '{key}' needs a value", key=key))
        elif key == "align":
            if value.lower() in ALIGNMENTS:
                config.align = value.lower()
            else:
                warn(
                    _w(
                        "deck-align-bad",
                        f"'{MARKER}': align must be left, center or right",
                        value=value,
                    )
                )
        elif key == "theme":
            if value.lower() in THEMES:
                config.theme = value.lower()
            else:
                warn(
                    _w(
                        "theme-unknown",
                        f"'{MARKER}': unknown theme '{value}' — "
                        f"the themes are {', '.join(listed_themes())}",
                        value=value,
                        themes=", ".join(listed_themes()),
                    )
                )
        elif key == "speed":
            try:
                speed = float(value)
            except ValueError:
                warn(
                    _w(
                        "deck-speed-nan",
                        f"'{MARKER}': speed must be a number — got '{value}'",
                        value=value,
                    )
                )
            else:
                if 0.5 <= speed <= 2.0:
                    config.speed = speed
                else:
                    warn(
                        _w(
                            "deck-speed-range",
                            f"'{MARKER}': speed {speed} is outside 0.5–2.0",
                            value=speed,
                        )
                    )
        elif not value:
            warn(_w("deck-needs-value", f"'{MARKER}': '{key}' needs a value", key=key))
        elif key == "name":
            if len(value) > _DECK_NAME_MAX:
                warn(
                    _w(
                        "name-long",
                        f"'{MARKER}': name is longer than {_DECK_NAME_MAX} characters",
                        value=_DECK_NAME_MAX,
                    )
                )
            elif any(part.strip() == "" for part in value.split("::")):
                warn(
                    _w(
                        "name-empty-level",
                        f"'{MARKER}': name '{value}' has an empty level",
                        value=value,
                    )
                )
            else:
                config.deck_name = value
        elif key == "shape":
            if _SHAPE_RE.match(value.lower()):
                config.shape = value.lower()
            else:
                warn(
                    _w(
                        "shape-bad",
                        f"'{MARKER}': shape is written by SheetCards (like b1f3a2c) "
                        f"— got '{value}'",
                        value=value,
                    )
                )
        elif key == "next":
            if _NEXT_ID_RE.match(value):
                config.next_id = value
            else:
                warn(
                    _w(
                        "next-bad",
                        f"'{MARKER}': next must be an ID ending in a number, "
                        f"like w15 — got '{value}'",
                        value=value,
                    )
                )

    for header in plan.content_headers:
        cell = str(row.get(header, "")).strip()
        if not cell:
            continue

        cfg = FieldConfig()
        for key, value in _parse_pairs(cell):
            if key not in _FIELD_KEYS:
                warn(
                    _w(
                        "unknown-setting",
                        f"'{header}': unknown setting '{key}'",
                        col=header,
                        key=key,
                    )
                )
                continue
            _apply_field_pair(cfg, key, value, header, warn)

        # `size` is a font size on a text column, a width on a media one and the
        # side of the square on a writing box, so the sane range depends on a key
        # that may be written after it in the same cell. Checking here rather than
        # while parsing makes `size=320; image` work.
        if cfg.size is not None:
            box = cfg.media or cfg.draw
            low, high = (1, 2000) if box else (6, 200)
            if not low <= cfg.size <= high:
                what = "width" if cfg.media else "box" if cfg.draw else "font size"
                warn(
                    _w(
                        f"size-range-{'width' if cfg.media else 'box' if cfg.draw else 'font'}",
                        f"'{header}': {what} {cfg.size}px is outside {low}–{high}px",
                        col=header,
                        value=cfg.size,
                        low=low,
                        high=high,
                    )
                )
                cfg.size = None

        # A media column holds a URL, so these would act on the address itself:
        # tts would read the URL out loud, furigana would try to annotate it.
        if cfg.media:
            if cfg.tts:
                warn(
                    _w(
                        "media-tts",
                        f"'{header}': tts on a {cfg.media} column would read the URL "
                        f"aloud — removed",
                        col=header,
                        media=cfg.media,
                    )
                )
                cfg.tts = None
                cfg.voices = []
            if cfg.furigana:
                warn(
                    _w(
                        "furigana-on",
                        f"'{header}': furigana does nothing on a {cfg.media} column",
                        col=header,
                        media=cfg.media,
                    )
                )
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
                    ("font", cfg.font),
                    ("rtl", cfg.rtl),
                    ("vertical", cfg.vertical),
                )
                if on
            ]
            if inert:
                warn(
                    _w(
                        "inert-on",
                        f"'{header}': {', '.join(inert)} "
                        f"{'do' if len(inert) > 1 else 'does'} nothing on a "
                        f"{cfg.media} column",
                        col=header,
                        keys=", ".join(inert),
                        media=cfg.media,
                    )
                )
            for name in ("font", "rtl", "vertical"):
                setattr(cfg, name, None if name == "font" else False)
            for name in ("math", "code"):
                if getattr(cfg, name) is not None:
                    # These two do not decorate the text, they *are* how the cell
                    # is drawn — and a media cell is an address, not text.
                    warn(
                        _w(
                            "media-drawn",
                            f"'{header}': a {cfg.media} column holds an address, "
                            f"so {name} has nothing to draw — removed",
                            col=header,
                            media=cfg.media,
                            key=name,
                        )
                    )
                    setattr(cfg, name, None)

            if cfg.media == "audio" and cfg.size is not None:
                warn(
                    _w(
                        "audio-size",
                        f"'{header}': size does nothing on an audio column",
                        col=header,
                    )
                )
                cfg.size = None

        # A writing box draws the character the cell names; it never prints the
        # cell. Anything that acts on printed text therefore has nothing to act on
        # — except `color`, which the strokes inherit from the card, and `tts`,
        # which still has a character to say.
        if cfg.draw:
            if cfg.media:
                warn(
                    _w(
                        "draw-media",
                        f"'{header}': a {cfg.media} column holds an address, not a "
                        f"character — draw removed",
                        col=header,
                        media=cfg.media,
                    )
                )
                cfg.draw = False
            elif cfg.cloze:
                # The clozed column is the prompt and its deletion is the question.
                # Drawing it would replace the very text the card asks about.
                warn(
                    _w(
                        "draw-cloze",
                        f"'{header}': a cloze column cannot also be drawn — "
                        f"draw removed",
                        col=header,
                    )
                )
                cfg.draw = False
            else:
                if cfg.furigana:
                    warn(
                        _w(
                            "furigana-on",
                            f"'{header}': furigana does nothing on a drawn column",
                            col=header,
                            media="drawn",
                        )
                    )
                    cfg.furigana = False
                inert = [
                    name
                    for name, on in (("bold", cfg.bold), ("italic", cfg.italic))
                    if on
                ]
                if inert:
                    warn(
                        _w(
                            "inert-on",
                            f"'{header}': {', '.join(inert)} "
                            f"{'do' if len(inert) > 1 else 'does'} nothing on a "
                            f"drawn column",
                            col=header,
                            keys=", ".join(inert),
                            media="drawn",
                        )
                    )

        # Three ways of drawing one cell, and a cell is drawn once. Order matters
        # only in that the *earlier* one is kept, which is the same rule the media
        # kinds follow: the sheet's first answer stands.
        if cfg.math and cfg.code is not None:
            warn(
                _w(
                    "math-and-code",
                    f"'{header}': a column is drawn as a formula or as code, not both",
                    col=header,
                )
            )
            cfg.code = None
        if cfg.draw and (cfg.math or cfg.code is not None):
            what = "math" if cfg.math else "code"
            warn(
                _w(
                    "draw-drops",
                    f"'{header}': a writing box draws a character, so {what} is "
                    f"removed",
                    col=header,
                    key=what,
                )
            )
            cfg.math, cfg.code = None, None
        if cfg.cloze and (cfg.math or cfg.code is not None):
            what = "math" if cfg.math else "code"
            warn(
                _w(
                    "cloze-drops",
                    f"'{header}': the cloze column has to reach the card through "
                    f"{{{{cloze:}}}}, which {what} would replace — {what} removed",
                    col=header,
                    key=what,
                )
            )
            cfg.math, cfg.code = None, None
        if cfg.furigana and (cfg.math or cfg.code is not None):
            what = "math" if cfg.math else "code"
            warn(
                _w(
                    "furigana-on",
                    f"'{header}': furigana does nothing on a {what} column",
                    col=header,
                    media=what,
                )
            )
            cfg.furigana = False

        # One direction of writing at a time.
        if cfg.rtl and cfg.vertical:
            warn(
                _w(
                    "rtl-vertical",
                    f"'{header}': rtl and vertical are two directions — keeping rtl",
                    col=header,
                )
            )
            cfg.vertical = False

        config.fields[header] = cfg

    resolve_roles(config, plan.content_headers, plan.subdeck_headers, warn)

    return config
