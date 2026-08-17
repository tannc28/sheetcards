"""Turns a sheet's settings row into Anki card templates.

Everything a card shows comes from two things: the sheet's column order
(:class:`~.column_model.ColumnPlan`) and the optional ``#config`` row parsed into a
:class:`~.sheet_config.SheetConfig`. Nobody edits HTML — a column moved in the sheet
moves on the card, and a directive typed in the settings row is the only way to
override that.

A reverse card is a *second template on the same note type* rather than a second
note: Anki then schedules both directions independently while keeping one row of
data, and turning the reverse card off later removes its cards without touching the
note's content.
"""

from html import escape

from .sheet_config import ALIGNMENTS
from .sheet_config import THEME_COLORS
from .sheet_config import THEMES

# A card frames this page, and this page frames the video.
#
# Anki's mobile clients load a card from a `file://` origin, so their webview
# sends no HTTP Referer and YouTube refuses the embed with "Error 153". A
# referrerpolicy cannot help — there is no origin to send from. Framing an https
# page first gives the request a real referrer, and the video plays.
#
# The address lives here rather than in the notes: a template is rebuilt on every
# sync, so changing or dropping this is one re-sync instead of an edit to every
# row. The cost is that a video needs this page to be reachable, on top of needing
# YouTube — which is why the mobile link below stays as a way through.
EMBED_PROXY = "https://tannc28.github.io/sheets2anki/player.html?src="

# Writing a character is a different skill from recognising one, and no amount of
# HTML can test it: the card has to take strokes and mark them. HanziWriter is the
# library that does that, and it is loaded from a CDN into the card rather than
# vendored, because it is not the add-on that runs it — the card does, inside
# Anki's webview, on whatever machine is reviewing.
#
# The consequences are the same as for any media column and are documented as
# such: the card needs the network, and a client that refuses remote scripts shows
# the placeholder instead. Pinned to a major version so a breaking release upstream
# cannot reach cards that are already in people's collections.
HANZI_WRITER = "https://cdn.jsdelivr.net/npm/hanzi-writer@3/dist/hanzi-writer.min.js"

FRONT_TEMPLATE_NAME = "Card 1"
REVERSE_TEMPLATE_NAME = "Card 2 (reverse)"

# Sizes a field falls back to when the settings row says nothing: the prompt reads
# large, the answer reads at body size. ``size=`` overrides them per field.
FRONT_SIZE_PX = 40
BACK_SIZE_PX = 18


def _escape_field(name):
    """Anki field references are literal; only the surrounding braces are syntax."""
    return name.strip()


def _color(value):
    """A theme name resolves to its custom property; anything else is literal CSS."""
    return THEME_COLORS.get(str(value).lower(), value)


_DEFAULT_PALETTE = {
    "light": {"muted": "#6b7280", "accent": "#1a73e8"},
    "night": {"muted": "#a1a1aa", "accent": "#8ab4f8"},
}


# Where the blossoms sit in one tile of the pattern, as (x, y, scale, rotation).
# Handplaced rather than generated: the point of a scatter is that it does not read
# as a grid, and the eye finds a repeat much faster than a random function avoids
# one. The tile is 240 square and wraps, so a blossom near an edge is met by its
# own other half — none of these sit close enough to an edge to be cut.
_BLOSSOMS = (
    (34, 44, 1.00, 12),
    (128, 22, 0.66, -34),
    (196, 84, 1.14, 41),
    (74, 128, 0.84, 68),
    (162, 178, 0.96, -18),
    (26, 196, 0.60, 27),
)
# Single petals, drifting: the flower is only half of what a sakura in wind looks
# like. Same tuple shape, one ellipse each.
_PETALS = ((104, 88, 0.9, 55), (218, 148, 0.7, -25), (66, 218, 0.8, 100))


def _blossom(x, y, scale, rotation, petal, heart):
    """One five-petal flower, as SVG.

    Five ellipses around a point is the cheapest shape that still reads as a
    cherry blossom at the size a background pattern draws it: at 20 px nobody
    counts the notches in a petal, but everybody counts five.
    """
    place = f"translate({x} {y}) rotate({rotation}) scale({scale})"
    leaves = "".join(
        f"<ellipse cx='0' cy='-9' rx='5.4' ry='8.6' transform='rotate({turn})'/>"
        for turn in (0, 72, 144, 216, 288)
    )
    return (
        f"<g transform='{place}'>"
        f"<g fill='{petal}'>{leaves}</g>"
        f"<circle r='2.3' fill='{heart}'/>"
        f"</g>"
    )


def _data_uri(svg):
    """An SVG encoded so it can live inside a CSS ``url()``.

    Only the characters that would end the value or start a comment are escaped,
    which keeps the result short enough to sit in a note type: a fully
    percent-encoded copy of the same tile is roughly twice the size, and this one
    is stored in every template of every themed sheet. The SVG is written with
    single-quoted attributes so the CSS can keep the double quotes.
    """
    text = " ".join(svg.split())
    for character, code in (("%", "%25"), ("#", "%23"), ("<", "%3C"), (">", "%3E")):
        text = text.replace(character, code)
    return "data:image/svg+xml," + text.replace(" ", "%20")


def _blossom_tile(variant):
    """The theme's wallpaper: one tile of blossoms, or ``None`` for a plain palette."""
    petal = variant.get("petal")
    if not petal:
        return None
    heart = variant.get("heart", petal)
    flowers = "".join(_blossom(*spot, petal, heart) for spot in _BLOSSOMS)
    loose = "".join(
        f"<ellipse cx='0' cy='0' rx='4.6' ry='7.4' fill='{petal}'"
        f" transform='translate({x} {y}) rotate({rotation}) scale({scale})'/>"
        for x, y, scale, rotation in _PETALS
    )
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='240' height='240'"
        f" viewBox='0 0 240 240'><g opacity='{variant.get('veil', '0.5')}'>"
        f"{flowers}{loose}</g></svg>"
    )
    return _data_uri(svg)


def _painted(variant):
    """The declarations that make a card look like its theme."""
    parts = [
        f"background-color: {variant['bg']}",
        f"color: {variant['fg']}",
    ]
    tile = _blossom_tile(variant)
    if tile:
        # The colour stays in `background-color` rather than moving into the
        # shorthand: the pattern is a layer over the card's own paint, and a client
        # that refuses the data URI then still gets the theme's background instead
        # of falling through to whatever is behind the card.
        parts.append(f'background-image: url("{tile}")')
        parts.append("background-repeat: repeat")
        parts.append("background-size: 240px 240px")
    return "; ".join(parts)


def _palette(sheet_config):
    """The colour block at the top of the stylesheet, themed or not.

    ``--s2a-muted``/``--s2a-accent`` are declared twice on purpose: once as the light
    default and once under ``.night_mode``, the class Anki puts on the card's body in
    dark mode. A single fixed value would make one of the two themes unreadable, which
    is the whole reason the named colours exist instead of hard-coded ones.

    A named ``theme`` swaps both pairs and additionally paints the card itself. That
    part is written as ``.card``/``.card.night_mode`` rather than ``body`` for two
    reasons: ``.card`` is the class Anki puts on the card's body on every client, and
    the two-class selector outranks the ``.night_mode`` rule Anki's own stylesheet
    brings — a single-class selector would lose in dark mode and the sheet's theme
    would simply not appear. Without a theme nothing paints the card at all, so an
    untouched sheet keeps whatever colours Anki and the note type already had.
    """
    theme = THEMES.get(sheet_config.theme) or _DEFAULT_PALETTE
    lines = [
        f":root {{ --s2a-muted: {theme['light']['muted']};"
        f" --s2a-accent: {theme['light']['accent']}; }}\n",
        f".night_mode {{ --s2a-muted: {theme['night']['muted']};"
        f" --s2a-accent: {theme['night']['accent']}; }}\n",
    ]
    if sheet_config.theme in THEMES:
        lines.append(f".card {{ {_painted(theme['light'])}; }}\n")
        lines.append(f".card.night_mode {{ {_painted(theme['night'])}; }}\n")
    return "".join(lines)


def _css(sheet_config):
    """The card's stylesheet."""
    align = sheet_config.align if sheet_config.align in ALIGNMENTS else "center"
    return (
        "<style>\n" + _palette(sheet_config) + f".s2a-wrap {{ text-align: {align}; }}\n"
        f".s2a-front {{ font-size: {FRONT_SIZE_PX}px; line-height: 1.3; }}\n"
        f".s2a-back {{ font-size: {BACK_SIZE_PX}px; line-height: 1.5;"
        " margin-top: 14px; }\n"
        ".s2a-label { font-size: 12px; letter-spacing: .06em;"
        " text-transform: uppercase; opacity: .55; margin-bottom: 2px; }\n"
        ".s2a-reveal > summary { cursor: pointer; font-size: 13px;"
        " letter-spacing: .06em; text-transform: uppercase; opacity: .6; }\n"
        ".s2a-embed { width: 100%; aspect-ratio: 16 / 9; border: 0;"
        " display: block; margin: 0 auto; }\n"
        ".s2a-embed-link { display: none; }\n"
        # A framed player cannot work on the mobile clients: their webview loads
        # the card from a file:// origin, so no HTTP Referer is sent and YouTube
        # answers with "Error 153: Video player configuration error" — a
        # referrerpolicy cannot help, because there is no origin to send. Anki
        # marks those clients with a `mobile` class, so the frame is simply not
        # shown there and a link that opens the video properly takes its place.
        ".mobile .s2a-embed-link { display: inline-block; margin-top: 6px;"
        " font-size: 13px; opacity: .7; }\n"
        # The writing box is sized inline, from `size=`. `:empty` is the state
        # before the library has drawn anything into it — no network, a client
        # that refuses remote scripts, or simply the moment before it loads — and
        # in that state the box says which character it was going to ask for
        # rather than sitting there as a blank square.
        ".s2a-draw { display: inline-flex; align-items: center;"
        " justify-content: center; vertical-align: top; margin: 4px;"
        " border: 1px dashed var(--s2a-muted); border-radius: 8px; }\n"
        ".s2a-draw:empty::before { content: attr(data-s2a-char);"
        " font-size: 40px; opacity: .35; }\n"
        "</style>\n"
    )


def _inline_style(cfg, with_size=True):
    """The per-field directives that are plain CSS, as one style attribute value.

    ``with_size`` is off for a drawn column, where ``size`` is the side of the box
    rather than a font size — but the rest still applies, and ``color`` in
    particular has to, because the strokes are drawn in whatever colour the box
    inherits.
    """
    parts = []
    if cfg.size and with_size:
        parts.append(f"font-size: {int(cfg.size)}px")
    if cfg.color:
        parts.append(f"color: {_color(cfg.color)}")
    if cfg.bold:
        parts.append("font-weight: 700")
    if cfg.italic:
        parts.append("font-style: italic")
    if cfg.align:
        parts.append(f"text-align: {cfg.align}")
    return "; ".join(parts)


# A media column holds nothing but a URL, so the cell is wrapped in the element that
# plays it rather than printed. `controls` is always on: a sound the learner cannot
# replay is worse than no sound.
_MEDIA_ELEMENTS = {
    "image": '<img src="{ref}"{style}>',
    "audio": '<audio src="{ref}" controls></audio>',
    # A frame rather than <video>, because the address a learner pastes is almost
    # always a YouTube or Drive *page*: the site's own player has to do the playing,
    # and YouTube refuses to be framed anywhere but its /embed path — which is why
    # tsv_model.normalize_embed_url rewrites the address on the way into the note.
    # A direct .mp4 also plays when a frame is pointed at it, so this one element
    # covers both and the sheet only ever has to say "video".
    # The aspect ratio lives in the stylesheet because an iframe, unlike <video>,
    # has no intrinsic size and would otherwise collapse to a 150px-tall box.
    # referrerpolicy is not decoration. A webview does not send an HTTP Referer
    # the way a browser does, and YouTube refuses to play an embed without one —
    # the card comes back reading "Error 153: Video player configuration error"
    # on the phone while working perfectly on the desktop. Naming the policy makes
    # the webview send the origin it does have.
    "video": (
        '<iframe src="' + EMBED_PROXY + '{ref}" class="s2a-embed" allowfullscreen '
        'referrerpolicy="strict-origin-when-cross-origin" '
        'allow="encrypted-media; picture-in-picture"{style}></iframe>'
        '<a class="s2a-embed-link" href="{ref}">{caption}</a>'
    ),
}


def _reference(field, cfg, as_cloze):
    """How the field's value is pulled in: plain, or through one of Anki's filters.

    ``cloze:`` wins over ``hint``/``furigana``: a cloze card's prompt has to reach
    the field through that filter, and hiding it behind a hint would leave nothing
    to reveal. Only the column the sheet declared as ``cloze`` takes this branch —
    Anki renders a clozed field that holds no deletion as *nothing at all*, so
    wrapping any other column would silently blank it.
    """
    if as_cloze:
        return f"{{{{cloze:{field}}}}}"
    if cfg.hint:
        return f"{{{{hint:{field}}}}}"
    if cfg.furigana:
        return f"{{{{furigana:{field}}}}}"
    return f"{{{{{field}}}}}"


def _media_html(field, cfg):
    """The media element for a URL column, sized by ``size`` when given.

    ``size`` means a font size everywhere else, but a picture has no font — here it
    caps the width instead, which is what someone writing ``image; size=200`` means.
    """
    template = _MEDIA_ELEMENTS[cfg.media]
    style = f' style="max-width: {cfg.size}px"' if cfg.size else ""
    # The URL comes from the field, so it goes through Anki's own substitution and is
    # never built by string-joining here. `caption` is only read by the video
    # element, whose mobile fallback needs something to say.
    return template.format(
        ref=f"{{{{{field}}}}}",
        style=style,
        caption=escape(cfg.label) if cfg.label else "▶ Watch the video",
    )


def _draw_html(field, cfg, quiz):
    """The writing box for one column.

    The character is handed over in a data attribute rather than printed: the box
    has to stay empty for `:empty::before` to be the fallback, and on the question
    side printing it would be showing the answer.
    """
    size = int(cfg.size) if cfg.size else 200
    return (
        f'<div class="s2a-draw" data-s2a-char="{{{{text:{field}}}}}" '
        f'data-s2a-size="{size}" data-s2a-quiz="{1 if quiz else 0}" '
        f'style="min-width: {size}px; height: {size}px"></div>'
    )


# Runs once per side that has a writing box on it. Anki re-executes the script
# tags in a card's HTML every time it draws a card, so everything here has to be
# safe to run again: the library is fetched once into the document head, which
# survives the card change, and a box already drawn into is left alone.
_DRAW_SCRIPT = (
    "<script>\n"
    "(function () {\n"
    "  function draw() {\n"
    '    document.querySelectorAll(".s2a-draw").forEach(function (box) {\n'
    "      if (box.dataset.s2aDone) return;\n"
    '      box.dataset.s2aDone = "1";\n'
    "      var style = getComputedStyle(box);\n"
    "      var ink = style.color;\n"
    # The theme's own muted colour, so the outline to trace stays visible in both
    # light and night mode instead of being a fixed grey that vanishes in one.
    '      var faint = style.getPropertyValue("--s2a-muted").trim() || "#888";\n'
    "      var size = parseInt(box.dataset.s2aSize, 10) || 200;\n"
    '      var quiz = box.dataset.s2aQuiz === "1";\n'
    # Array.from rather than split(""), which cuts a character above the basic
    # plane in half and asks the library to draw two halves of nothing.
    '      Array.from((box.dataset.s2aChar || "").trim()).forEach(function (ch) {\n'
    "        if (!ch.trim()) return;\n"
    '        var cell = document.createElement("div");\n'
    "        box.appendChild(cell);\n"
    "        var writer = HanziWriter.create(cell, ch, {\n"
    "          width: size, height: size, padding: 6,\n"
    # The question is a blank square. HanziWriter's outline is the whole
    # character in a pale colour, which on the side that is *asking* is the
    # answer sitting there to be traced — so it is only drawn on the answer.
    # Getting a stroke wrong twice still lights up where the next one starts.
    "          showCharacter: !quiz, showOutline: !quiz,\n"
    "          strokeColor: ink, drawingColor: ink, outlineColor: faint,\n"
    "          delayBetweenStrokes: 150,\n"
    # A character the data set does not have — a letter, a digit, a rare variant —
    # is printed instead of leaving an empty square with no explanation.
    "          onLoadCharDataError: function () { cell.textContent = ch; }\n"
    "        });\n"
    "        if (quiz) { writer.quiz({ showHintAfterMisses: 2 }); }\n"
    "        else { writer.loopCharacterAnimation(); }\n"
    "      });\n"
    "    });\n"
    "  }\n"
    "  if (window.HanziWriter) { draw(); return; }\n"
    '  var tag = document.getElementById("s2a-hanzi-writer");\n'
    "  if (!tag) {\n"
    '    tag = document.createElement("script");\n'
    '    tag.id = "s2a-hanzi-writer";\n'
    '    tag.src = "' + HANZI_WRITER + '";\n'
    "    document.head.appendChild(tag);\n"
    "  }\n"
    '  tag.addEventListener("load", draw);\n'
    "})();\n"
    "</script>"
)


def _speed_text(speed):
    """``1.0`` renders as ``1`` and ``1.25`` as ``1.25`` — no trailing zeros."""
    return f"{float(speed):g}"


def _tts_tag(field, cfg, deck_speed):
    """Anki's TTS tag for the field, or "" when the field asked for no speech.

    The grammar is ``{{tts LANG [voices=A,B] [speed=N]:Field}}``: the language comes
    first and the rest are order-independent options. The tag is wrapped in the same
    ``{{#Field}}`` guard as the field itself so an empty row does not make Anki read
    out silence.

    A furigana column is spoken through ``kana:``, which is not a nicety. Anki hands
    the voice the field's *text*, and the text of a furigana cell is
    ``日本語[にほんご]`` — so the plain tag has the voice say the word, then the
    bracket, then the word again as kana. Verified against a real collection:

    ==========================  ==============================
    ``{{tts ja_JP:Word}}``      ``私[わたし]は 日本語[にほんご]``
    ``{{tts ja_JP:kana:Word}}`` ``わたしはにほんご``
    ==========================  ==============================

    ``kana:`` rather than ``kanji:`` because the sheet went to the trouble of
    writing the reading down: making the engine guess it again is the very thing
    furigana is there to prevent, and it guesses wrong on exactly the names and rare
    readings someone bothered to annotate. A cell with no brackets in it passes
    through either filter unchanged, so a column where only some rows are annotated
    still speaks correctly.
    """
    if not cfg.tts:
        return ""

    options = [f"tts {cfg.tts}"]
    if cfg.voices:
        options.append("voices=" + ",".join(cfg.voices))

    # A field that names its own speed means it, so it outranks the deck-wide value.
    speed = cfg.speed if cfg.speed is not None else deck_speed
    if speed is not None:
        options.append(f"speed={_speed_text(speed)}")

    spoken = f"kana:{field}" if cfg.furigana else field
    tag = "{{" + " ".join(options) + f":{spoken}}}}}"
    return f"{{{{#{field}}}}}{tag}{{{{/{field}}}}}"


def _type_box(field, cfg, cloze_field):
    """Anki's typed-answer box for this field, or "" when it did not ask for one.

    The box goes on the *question*: Anki draws an input there and, on the answer,
    diffs what was typed against the field. ``nc`` drops diacritics from the
    comparison, which is what someone typing pinyin without tone marks means.
    """
    if not cfg.type_answer:
        return ""
    prefix = "nc:" if cfg.type_answer == "nc" else ""
    if field == cloze_field:
        # Typing the deletions themselves rather than the whole sentence.
        return f"<div>{{{{type:cloze:{field}}}}}</div>"
    return f"<div>{{{{type:{prefix}{field}}}}}</div>"


def _rows(fields, sheet_config, css_class, as_cloze=False, quiz=False):
    """Renders one side's fields, each wrapped so an empty field leaves no trace.

    ``quiz`` is what tells a drawn column which of its two jobs it has: on the
    question it takes strokes from the learner, on the answer it shows them. The
    caller knows which side it is building, and the column does not need to be
    told twice in the settings row.
    """
    out = []
    for name in fields:
        field = _escape_field(name)
        if not field:
            continue

        cfg = sheet_config.for_field(name)
        style = "" if cfg.media else _inline_style(cfg, with_size=not cfg.draw)
        style_attr = f' style="{style}"' if style else ""
        # The caption is user text from the sheet, so it is escaped; the field name is
        # not, because Anki matches ``{{Field}}`` on the name exactly as written.
        label = f'<div class="s2a-label">{escape(cfg.label)}</div>' if cfg.label else ""
        if cfg.media:
            reference = _media_html(field, cfg)
            if cfg.hint:
                # Anki's {{hint:}} reveals the field's *text*, which for a media
                # column is the URL — useless. A <details> disclosure hides the
                # element itself, needs no JavaScript, and works on mobile.
                caption = escape(cfg.label) if cfg.label else cfg.media.capitalize()
                reference = (
                    f'<details class="s2a-reveal"><summary>{caption}</summary>'
                    f"{reference}</details>"
                )
                label = ""  # the summary already names it
        elif cfg.draw:
            reference = _draw_html(field, cfg, quiz)
            if cfg.hint:
                # Same reason as for media: {{hint:}} reveals the field's *text*,
                # which here is the character the box exists not to show.
                caption = escape(cfg.label) if cfg.label else "Write it"
                reference = (
                    f'<details class="s2a-reveal"><summary>{caption}</summary>'
                    f"{reference}</details>"
                )
                label = ""
        else:
            reference = _reference(field, cfg, as_cloze and cfg.cloze)

        # Which column this block came from, named on the block itself. Anki's
        # own classes say only which side it is on, so nothing in the finished
        # card connects a piece of it back to the sheet — which makes it the one
        # thing a stylist cannot target and the one thing the preview cannot
        # point at. The value is the header exactly as written, so
        # `[data-s2a-col="Pinyin"]` works in the note type's CSS too.
        out.append(
            f"{{{{#{field}}}}}"
            f'<div class="{css_class}" data-s2a-col="{escape(name)}"{style_attr}>'
            f"{label}{reference}</div>"
            f"{{{{/{field}}}}}"
        )

        tts = _tts_tag(field, cfg, sheet_config.speed)
        if tts:
            out.append(tts)

    return "\n".join(out)


def _one_template(
    front_fields, back_fields, sheet_config, is_cloze, typed=True, heard=("", "")
):
    """Builds a single {qfmt, afmt} pair from one front/back split.

    ``typed`` is False for the reverse card: the typed-answer box belongs to the
    direction the sheet described, and asking for the same answer from both sides
    would be asking the same question twice.

    ``heard`` is the pair of already-rendered TTS tags for the columns that are
    spoken without being drawn — see :func:`spoken_sides`. It arrives rendered
    rather than as field names because the two sides swap for the reverse card,
    and the caller is the one that knows which way round they go.
    """
    type_field = sheet_config.type_field if typed else None
    type_box = (
        _type_box(
            _escape_field(type_field),
            sheet_config.for_field(type_field),
            sheet_config.cloze_field,
        )
        if type_field
        else ""
    )

    def drawn(fields):
        """Whether this side has a writing box, and so needs the library."""
        return any(sheet_config.for_field(name).draw for name in fields)

    qfmt = (
        _css(sheet_config)
        + '<div class="s2a-wrap">\n'
        + _rows(front_fields, sheet_config, "s2a-front", as_cloze=is_cloze, quiz=True)
        + type_box
        + "\n</div>"
        + heard[0]
        + (_DRAW_SCRIPT if drawn(front_fields) else "")
    )

    if is_cloze:
        # Anki validates that a cloze template references {{cloze:Field}} on BOTH
        # sides and refuses to save the note type otherwise, so the back repeats the
        # prompt through the filter (which is also what reveals the deletion) rather
        # than pulling it in via {{FrontSide}}.
        back_head = (
            _css(sheet_config)
            + '<div class="s2a-wrap">\n'
            + _rows(front_fields, sheet_config, "s2a-front", as_cloze=True)
            + "\n</div>"
        )
    else:
        back_head = "{{FrontSide}}"

    afmt = (
        back_head
        + '\n<hr id="answer">\n'
        + '<div class="s2a-wrap">\n'
        + _rows(back_fields, sheet_config, "s2a-back")
        + "\n</div>"
        + heard[1]
        # A question that had boxes brings its own copy of this back inside
        # {{FrontSide}}, so this is here for the case where only the answer draws.
        # Two copies would be harmless anyway — the script skips a box it has
        # already filled.
        + (_DRAW_SCRIPT if drawn(back_fields) else "")
    )

    return {"qfmt": qfmt, "afmt": afmt}


def split_sides(plan, sheet_config):
    """Which fields go on which side.

    The default is the sheet's own order — first content column is the prompt, the
    rest are the answer — which is the convention Anki's CSV import uses too, and it
    means reordering columns reorders the card with no settings at all. ``side=`` on a
    column overrides the default for that column only; ``side=hide`` drops it from
    both sides.

    Args:
        plan (ColumnPlan): the sheet's column roles
        sheet_config (SheetConfig): the parsed settings row

    Returns:
        tuple[list, list]: (front fields, back fields)
    """
    front: list[str] = []
    back: list[str] = []

    for index, header in enumerate(plan.content_headers):
        cfg = sheet_config.for_field(header)
        if not _is_drawn(cfg):
            continue
        (front if _side_of(index, cfg) == "front" else back).append(header)

    # An empty front would produce a blank prompt and Anki would refuse to generate
    # the card, so the first field that is still visible is promoted.
    if not front and back:
        front.append(back.pop(0))

    return front, back


def _is_drawn(cfg):
    """Whether this column is rendered on the card at all.

    ``side=hide`` is the explicit way to say no. A ``subdeck=n`` column is never
    drawn at all: where a note is *filed* is a bigger thing than how one card
    looks, and a directive working at that level has no business reaching down
    into the card. The reserved ``SUBDECK n`` columns have never done so either,
    so there is one rule rather than two — a deck level is a deck level.

    Nothing is lost by not printing it: the note is in the deck named after that
    value, and Anki shows the deck. Printing it on the card as well says twice
    what the deck tree already says once.
    """
    return not (cfg.hidden or cfg.subdeck)


def _side_of(index, cfg):
    """Which side a column belongs on, drawn or not.

    The clozed column *is* the prompt — its deletions are what the card asks
    about — so it goes on the front whatever the column order says.
    """
    if cfg.cloze:
        return "front"
    # `hide` is not a side, it is the absence of one — so a column that is not
    # drawn still *belongs* somewhere, which is what says where its voice goes.
    if cfg.side in ("front", "back"):
        return cfg.side
    return "front" if index == 0 else "back"


def spoken_sides(plan, sheet_config):
    """The columns that are heard but never seen, split by side.

    ``tts`` says speak this column and ``side=hide`` says do not draw it; each
    keeps its own meaning, so a column that says both is asking to be heard and
    not read. There is no other way to ask for that — dropping a column from the
    card used to take its voice with it — and it is what a listening card is:
    the answer said aloud, with nothing on screen to read it off.
    """
    front: list[str] = []
    back: list[str] = []
    for index, header in enumerate(plan.content_headers):
        cfg = sheet_config.for_field(header)
        if _is_drawn(cfg) or not cfg.tts:
            continue
        (front if _side_of(index, cfg) == "front" else back).append(header)
    return front, back


def build_templates(plan, sheet_config, is_cloze=False):
    """Every card template the sheet's columns and settings row call for.

    Args:
        plan (ColumnPlan): the sheet's column roles
        sheet_config (SheetConfig): the parsed settings row (a default-constructed
            one renders the plain first-column-is-the-prompt layout)
        is_cloze (bool): render the prompt through Anki's ``cloze:`` filter

    Returns:
        list[dict]: ``{"name", "qfmt", "afmt"}`` per template, front card first
    """
    front, back = split_sides(plan, sheet_config)

    # Rendered once here so the reverse card can be handed the same two strings
    # the other way round, exactly as it is handed the two field lists.
    def voices(fields):
        return "\n".join(
            tag
            for tag in (
                _tts_tag(
                    _escape_field(name),
                    sheet_config.for_field(name),
                    sheet_config.speed,
                )
                for name in fields
            )
            if tag
        )

    spoken_front, spoken_back = spoken_sides(plan, sheet_config)
    heard = (voices(spoken_front), voices(spoken_back))

    templates = [
        dict(
            name=FRONT_TEMPLATE_NAME,
            **_one_template(front, back, sheet_config, is_cloze, heard=heard),
        )
    ]

    # Cloze note types support exactly one template, so the reverse card is only
    # offered for ordinary notes.
    if sheet_config.reverse and not is_cloze and front and back:
        templates.append(
            dict(
                name=REVERSE_TEMPLATE_NAME,
                **_one_template(
                    back,
                    front,
                    sheet_config,
                    False,
                    typed=False,
                    heard=(heard[1], heard[0]),
                ),
            )
        )

    return templates
