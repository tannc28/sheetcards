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
from .sheet_config import FONTS
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

# Colouring source code is the same bargain as the writing box: a library, loaded
# into the card from a CDN, pinned to a major version so an upstream release cannot
# reach cards already in people's collections. The bundled build is used rather than
# the modular one because it arrives knowing the common languages, and a sheet is
# not the place to declare which grammars to register.
#
# No stylesheet comes with it. The colours are ours (see `_css`), so a code block
# follows the sheet's own theme and stays readable in Anki's night mode — a
# ready-made highlight theme paints its own light background and would sit on a
# dark card as a white rectangle.
HIGHLIGHT_JS = (
    "https://cdn.jsdelivr.net/npm/@highlightjs/cdn-assets@11/highlight.min.js"
)

# Google's stylesheet endpoint for the webfonts named in `sheet_config.FONTS`.
# `display=swap` so the card draws in a fallback face immediately and re-draws when
# the font arrives, rather than showing nothing while a review is waiting.
FONT_CSS = "https://fonts.googleapis.com/css2?family={family}&display=swap"

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


# The corner mark of a signed theme: a heart, then the name from `THEMES[...]["sign"]`.
#
# The heart is drawn rather than typed. U+2665 is a character, so it is whatever the
# machine's fonts make of it — a colour emoji on much of Android, a missing glyph
# elsewhere — and neither of those is the small soft heart this is. A path is the
# same shape on every client, needs no font, and takes the palette's own `heart`
# colour, which until now was only the middle of a blossom.
_HEART = (
    "M12 20.4 C 4.2 14.4, 2.2 9.4, 6 6.9 C 9 4.9, 11.2 6.7, 12 8.3"
    " C 12.8 6.7, 15 4.9, 18 6.9 C 21.8 9.4, 19.8 14.4, 12 20.4 Z"
)
# A script face where the machine has one; everywhere else this falls through to the
# card's own font, which is what `cursive` resolves to on Linux and Android.
_SIGN_FACE = (
    '"Segoe Script", "Bradley Hand", "Snell Roundhand", "Apple Chancery", cursive'
)
# Against a 40px prompt, small enough that the eye stops counting it as content on
# the way to the answer, and still legible on a phone. The heart is sized with the
# text rather than fixed, or it would end up larger than the name it precedes.
_SIGN_SIZE_PX = 12
_HEART_SIZE_PX = 10


def _heart(colour):
    """The mark's heart, as a data URI, in one of the palette's colours."""
    svg = (
        "<svg xmlns='http://www.w3.org/2000/svg' width='24' height='24'"
        f" viewBox='0 0 24 24'><path d='{_HEART}' fill='{colour}'/></svg>"
    )
    return _data_uri(svg)


def _sign_ink(variant):
    """The two declarations that differ between day and night: the colour, twice."""
    colour = variant.get("heart") or variant["muted"]
    return f'color: {colour}; background-image: url("{_heart(colour)}")'


def _signature(variant, name):
    """The corner mark, as the declarations of one ``::after`` rule.

    ``fixed`` rather than ``absolute``: a long card scrolls under the mark instead of
    carrying it off the top of the screen. ``pointer-events`` are off so it cannot
    swallow a tap meant for the card.
    """
    text = name.replace("\\", "\\\\").replace('"', '\\"')
    return "; ".join(
        [
            f'content: "{text}"',
            "position: fixed",
            "top: 8px",
            "right: 12px",
            f"padding-left: {_HEART_SIZE_PX + 4}px",
            f"background: no-repeat left 52% / {_HEART_SIZE_PX}px {_HEART_SIZE_PX}px",
            f"font-family: {_SIGN_FACE}",
            f"font-size: {_SIGN_SIZE_PX}px",
            "pointer-events: none",
            _sign_ink(variant),
        ]
    )


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
        sign = theme.get("sign")
        if sign:
            lines.append(f".card::after {{ {_signature(theme['light'], sign)}; }}\n")
            lines.append(
                f".card.night_mode::after {{ {_sign_ink(theme['night'])}; }}\n"
            )
    return "".join(lines)


def _font_imports(sheet_config):
    """The webfonts this sheet's columns asked for, as CSS imports.

    Only the names in `FONTS` that carry a family are fetched — a literal family
    name is whatever the machine has, and asking Google for it would be asking for
    a font that may not exist. `@import` has to be the first thing in a stylesheet,
    which is why this is prepended rather than appended.
    """
    wanted = []
    for cfg in sheet_config.fields.values():
        known = FONTS.get(str(cfg.font or "").lower())
        if known and known[0] and known[0] not in wanted:
            wanted.append(known[0])
    return "".join(
        f'@import url("{FONT_CSS.format(family=name.replace(" ", "+"))}");\n'
        for name in wanted
    )


def _css(sheet_config):
    """The card's stylesheet."""
    align = sheet_config.align if sheet_config.align in ALIGNMENTS else "center"
    return (
        "<style>\n"
        + _font_imports(sheet_config)
        + _palette(sheet_config)
        + f".s2a-wrap {{ text-align: {align}; }}\n"
        f".s2a-front {{ font-size: {FRONT_SIZE_PX}px; line-height: 1.3; }}\n"
        f".s2a-back {{ font-size: {BACK_SIZE_PX}px; line-height: 1.5;"
        " margin-top: 14px; }\n"
        ".s2a-label { font-size: 12px; letter-spacing: .06em;"
        " text-transform: uppercase; opacity: .55; margin-bottom: 2px; }\n"
        ".s2a-reveal > summary { cursor: pointer; font-size: 13px;"
        " letter-spacing: .06em; text-transform: uppercase; opacity: .6; }\n"
        ".s2a-tts-note { font-size: 12px; opacity: .7; margin: 6px 0 12px;"
        " text-align: left; }\n"
        ".s2a-tts-lang { font-family: ui-monospace, monospace; font-size: 11px;"
        " opacity: .6; margin: 12px 0 6px; text-align: left; }\n"
        # The snippet takes a whole row of its own: a voice name plus a button per
        # spoken column does not fit a phone's width side by side, and a wrapped
        # <code> next to a shrinking button is the worse of the two.
        ".s2a-tts-row { display: flex; flex-wrap: wrap; align-items: center;"
        " gap: 6px 8px; padding: 6px 0 6px 10px; text-align: left;"
        " border-left: 2px solid var(--s2a-muted); }\n"
        ".s2a-tts-row code { flex: 1 1 100%; font-size: 11px;"
        " overflow-wrap: anywhere; }\n"
        ".s2a-tts-play { flex: none; font-size: 11px; padding: 5px 9px;"
        " border-radius: 6px; border: 1px solid var(--s2a-muted);"
        " background: none; color: inherit; }\n"
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
        # Code is the one thing on a card that is not prose: left-aligned however
        # the deck is aligned, wrapped rather than cut, and scrolling inside its own
        # box so a long line cannot widen the card. The colours are written here
        # rather than imported with a ready-made highlight.js theme, which would
        # paint its own light background and sit on a night-mode card as a white
        # rectangle — these sit on whatever the card is already.
        ".s2a-code { text-align: left; direction: ltr; margin: 10px auto;"
        " padding: 10px 12px; max-width: 40em; overflow-x: auto;"
        " border-radius: 8px; background: rgba(127, 127, 127, .12);"
        " font-family: ui-monospace, 'SF Mono', Menlo, Consolas, monospace;"
        " font-size: 15px; line-height: 1.5; white-space: pre-wrap;"
        " overflow-wrap: anywhere; }\n"
        ".s2a-code code { font: inherit; background: none; padding: 0; }\n"
        ".hljs-comment, .hljs-quote { opacity: .65; font-style: italic; }\n"
        ".hljs-keyword, .hljs-selector-tag, .hljs-literal { color: #a626a4; }\n"
        ".hljs-string, .hljs-attr, .hljs-regexp { color: #50a14f; }\n"
        ".hljs-number, .hljs-symbol, .hljs-bullet { color: #986801; }\n"
        ".hljs-title, .hljs-name, .hljs-section { color: #4078f2; }\n"
        ".hljs-built_in, .hljs-type, .hljs-class { color: #c18401; }\n"
        ".night_mode .hljs-keyword, .night_mode .hljs-selector-tag,"
        " .night_mode .hljs-literal { color: #c678dd; }\n"
        ".night_mode .hljs-string, .night_mode .hljs-attr,"
        " .night_mode .hljs-regexp { color: #98c379; }\n"
        ".night_mode .hljs-number, .night_mode .hljs-symbol,"
        " .night_mode .hljs-bullet { color: #d19a66; }\n"
        ".night_mode .hljs-title, .night_mode .hljs-name,"
        " .night_mode .hljs-section { color: #61afef; }\n"
        ".night_mode .hljs-built_in, .night_mode .hljs-type,"
        " .night_mode .hljs-class { color: #e5c07b; }\n"
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
    if cfg.font:
        parts.append(f"font-family: {_font_stack(cfg.font)}")
    if cfg.rtl:
        # A right-to-left column that is still centred stays centred; one that was
        # not given an alignment starts from the right, which is where a reader of
        # Arabic or Hebrew starts.
        parts.append("direction: rtl")
        if not cfg.align:
            parts.append("text-align: right")
    if cfg.vertical:
        # Classical Japanese and Chinese run top to bottom, right to left. The
        # height is capped so a long line scrolls the card rather than growing it
        # past the bottom of the screen, and `mixed` keeps Latin words upright
        # inside a vertical line instead of rotating them onto their side.
        parts.append("writing-mode: vertical-rl")
        parts.append("text-orientation: mixed")
        parts.append("max-height: 60vh")
        parts.append("margin: 0 auto")
    return "; ".join(parts)


def _font_stack(name):
    """The CSS family list for a `font=` value.

    A name this add-on knows becomes the stack it stands for; anything else is
    passed through as the sheet wrote it, because whether a family is installed on
    the machine reviewing is not something the sheet or this file can know. A
    literal name is quoted only if it has a space in it and was not quoted already.
    """
    known = FONTS.get(str(name).lower())
    if known:
        return known[1]
    literal = str(name).strip()
    if " " in literal and not literal.startswith(("'", '"')):
        return f"'{literal}'"
    return literal


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
    if cfg.math:
        # Anki ships MathJax and renders these delimiters itself, so a formula
        # column needs no library and no script — only the delimiters around it.
        # `\(…\)` is inline, `\[…\]` is the centred display form.
        opener, closer = ("\\[", "\\]") if cfg.math == "block" else ("\\(", "\\)")
        return f"{opener}{{{{{field}}}}}{closer}"
    return f"{{{{{field}}}}}"


def _code_html(field, cfg):
    """A source-code block, kept exactly as it was typed.

    ``{{text:Field}}`` rather than ``{{Field}}``: a cell pasted out of an editor
    arrives with markup in it, and a card that renders `<b>` inside a code sample is
    showing something the compiler will never see. The language is a class rather
    than anything this add-on interprets — the library reads it, and an unknown one
    simply colours nothing.
    """
    language = f' class="language-{escape(cfg.code)}"' if cfg.code else ""
    return f'<pre class="s2a-code"><code{language}>{{{{text:{field}}}}}</code></pre>'


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


# Same shape as the writing box's script and for the same reasons: idempotent,
# because Anki re-runs a card's scripts every time it draws the card, and loaded
# once into the head rather than fetched per block.
_CODE_SCRIPT = (
    "<script>\n"
    "(function () {\n"
    "  function paint() {\n"
    '    document.querySelectorAll("pre.s2a-code code").forEach(function (el) {\n'
    "      if (el.dataset.s2aDone) return;\n"
    '      el.dataset.s2aDone = "1";\n'
    "      window.hljs && hljs.highlightElement(el);\n"
    "    });\n"
    "  }\n"
    "  if (window.hljs) { paint(); return; }\n"
    '  var tag = document.getElementById("s2a-hljs");\n'
    "  if (!tag) {\n"
    '    tag = document.createElement("script");\n'
    '    tag.id = "s2a-hljs";\n'
    '    tag.src = "' + HIGHLIGHT_JS + '";\n'
    "    document.head.appendChild(tag);\n"
    "  }\n"
    '  tag.addEventListener("load", paint);\n'
    "})();\n"
    "</script>"
)


_TTS_VOICES_SCRIPT = """<script>
(function () {
  var box = document.querySelector(".s2a-tts-debug");
  if (!box || box.dataset.s2aReady) return;
  box.dataset.s2aReady = "1";

  var wanted = (box.dataset.s2aLangs || "").split(",").filter(Boolean);
  var raw = box.querySelector(".s2a-tts-raw");
  var list = box.querySelector(".s2a-tts-list");

  // The desktop's webview has no Web Speech API, so there is nothing to press
  // there and the buttons are left out rather than shipped inert.
  var canSpeak = !!window.speechSynthesis;
  var note = box.querySelector(".s2a-tts-note");
  if (!canSpeak && note) {
    note.textContent = "To use a voice, add its line to the column's #config cell.";
  }

  var srcs = [];
  box.querySelectorAll(".s2a-tts-src").forEach(function (el) {
    var text = (el.textContent || "").trim();
    if (text) srcs.push({ col: el.dataset.col, lang: el.dataset.lang, text: text });
  });

  // NOTHING IN THIS SCRIPT MAY CONTAIN A DOUBLED BRACE, not even a comment:
  // Anki scans the whole template for replacements, script tags included, so an
  // example written out here becomes a reference to a field that does not exist
  // and the note type is refused. The regex below escapes each brace for exactly
  // that reason. Prose says "brace brace tts", never the thing itself.
  //
  // Anki joins the voices with <br>, so the whole list arrives as a single line
  // of text: the tags have to be scanned for rather than split on. Each entry is
  // a whole ready-made tag, field and all — AnkiMobile writes the language as
  // en-US and ends the tag with :Front — and only the name between voices= and
  // the colon belongs in a spreadsheet cell. The device lists its Enhanced
  // voices a second time in a group of their own, hence the dedupe.
  var all = [];
  var seen = {};
  var re = /\\{\\{tts\\s+(\\S+)\\s+voices=([^}]+)\\}\\}/g;
  var m;
  while ((m = re.exec(raw.textContent || ""))) {
    var name = m[2].split(":")[0].trim();
    var key = m[1] + "\\u0000" + name;
    if (name && !seen[key]) {
      seen[key] = 1;
      all.push({ lang: m[1], name: name });
    }
  }
  raw.remove();

  // A device spells the code its own way — iOS reports en-US, Android eng_USA —
  // and an exact compare then finds nothing on a phone that plainly has the
  // voice. The sheet's spelling is kept for display; only the compare relaxes.
  function norm(lang) {
    return String(lang || "").toLowerCase().replace(/-/g, "_");
  }
  function stem(lang) {
    return norm(lang).split("_")[0];
  }

  var rows = all.filter(function (v) {
    return wanted.some(function (w) { return norm(w) === norm(v.lang); });
  });

  if (!rows.length) {
    // The note offers a button that is no longer there.
    if (note) note.remove();

    if (!all.length) {
      list.textContent =
        "No voice installed. Settings > Accessibility > Read & Speak > Voices.";
      return;
    }

    // Which codes the device reported is the answer here, so it is printed
    // rather than described: the fix is to copy one of them into tts=. The ones
    // sharing the language are shown alone when there are any, since a list of
    // fifty codes buries the two that matter.
    var codes = [];
    all.forEach(function (v) {
      if (codes.indexOf(v.lang) === -1) codes.push(v.lang);
    });
    codes.sort();
    var near = codes.filter(function (c) {
      return wanted.some(function (w) { return stem(w) === stem(c); });
    });

    list.textContent =
      "This device has " + all.length + " voices, none of them " +
      wanted.join("/") + ". It spells its codes this way — put one in tts=:";
    var found = document.createElement("div");
    found.className = "s2a-tts-lang";
    found.textContent = (near.length ? near : codes).join("   ");
    list.appendChild(found);
    return;
  }

  function better(v) {
    return /\\((?:premium|enhanced)\\)/i.test(v.name) ? 0 : 1;
  }

  function speak(voice, text) {
    if (!window.speechSynthesis) return;
    speechSynthesis.cancel();
    var u = new SpeechSynthesisUtterance(text);
    u.lang = voice.lang.replace(/_/g, "-");
    // Anki names a voice the way a sheet has to spell it: engine first, spaces
    // written as underscores. The Web Speech API knows the same voice as
    // `Ava (Premium)`, so the name is spelled back before it is looked for, and
    // a device exposing only the plain voice still answers to the base name.
    var want = voice.name.replace(/^[A-Za-z]+_/, "").replace(/_/g, " ");
    var base = want.replace(/\\s*\\(.*\\)$/, "");
    var have = speechSynthesis.getVoices();
    var hit =
      have.filter(function (o) { return o.name === want; })[0] ||
      have.filter(function (o) { return o.name.indexOf(base) !== -1; })[0];
    // The picked voice carries its own code; the device's spelling of it is the
    // one that works here, not the sheet's.
    if (hit) { u.voice = hit; u.lang = hit.lang; }
    speechSynthesis.speak(u);
  }

  wanted.forEach(function (lang) {
    var here = rows.filter(function (v) { return norm(v.lang) === norm(lang); });
    if (!here.length) return;

    // Downloading an Enhanced or Premium voice is the whole answer to a card
    // that reads in a robot's voice, so the ones that are get offered first.
    // The rest keep the order the device gave them.
    here.sort(function (a, b) { return better(a) - better(b); });

    var head = document.createElement("div");
    head.className = "s2a-tts-lang";
    head.textContent = "tts=" + lang;
    list.appendChild(head);

    // Every spoken column of this language gets a button — a sheet that speaks
    // eight columns is a sheet whose eighth column is worth hearing too, and the
    // row wraps rather than truncates.
    var cols = srcs.filter(function (s) { return s.lang === lang; });

    here.forEach(function (v) {
      var row = document.createElement("div");
      row.className = "s2a-tts-row";

      var snippet = document.createElement("code");
      snippet.textContent = "voices=" + v.name;
      row.appendChild(snippet);

      if (canSpeak) cols.forEach(function (s) {
        var b = document.createElement("button");
        b.type = "button";
        b.className = "s2a-tts-play";
        b.textContent = "\\u25B6 " + s.col;
        b.setAttribute("aria-label", "Play " + s.col + " with " + v.name);
        b.onclick = function (e) { e.preventDefault(); speak(v, s.text); };
        row.appendChild(b);
      });

      list.appendChild(row);
    });
  });
})();
</script>"""


def _tts_debug_block(plan, sheet_config):
    """The device's own voice list, on the back of any card that speaks.

    There is no opt-in setting. Someone who wrote ``tts=`` and got a robot voice
    (or silence) is exactly the person who needs this, and also the person least
    likely to know a debug flag exists. It is collapsed, so always showing it
    costs one 13px line.

    It has to live on a card rather than in a dialog: only the device can answer
    which voices it has, and ``all_tts_voices()`` in the layout dialog reports
    the *desktop's* voices, which are not the phone's. Anki renders
    ``{{tts-voices:}}`` as one ready-made tag per installed voice; the script
    rewrites those into the sheet's own ``voices=`` syntax, because the reader is
    about to edit a spreadsheet cell, not a template.
    """
    spoken = [
        (name, sheet_config.for_field(name).tts)
        for name in plan.content_headers
        if sheet_config.for_field(name).tts
    ]
    if not spoken:
        return ""

    langs = sorted({lang for _, lang in spoken})
    # One hidden copy of each spoken column, so a play button can read the very
    # word being learned rather than a canned sample. {{text:...}} strips the
    # HTML the field may carry; an empty cell yields an empty span, which the
    # script skips.
    sources = "".join(
        f'<span class="s2a-tts-src" data-col="{name}" data-lang="{lang}" '
        f"hidden>{{{{text:{name}}}}}</span>"
        for name, lang in spoken
    )

    return (
        f'<details class="s2a-reveal s2a-tts-debug" data-s2a-langs="{",".join(langs)}">'
        "<summary>TTS voices</summary>"
        '<div class="s2a-tts-note">Tap \u25b6 to hear a voice. To use it, add its '
        "line to the column's #config cell.</div>"
        f"{sources}"
        '<div class="s2a-tts-raw">{{tts-voices:}}</div>'
        '<div class="s2a-tts-list"></div>'
        "</details>"
    ) + _TTS_VOICES_SCRIPT


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
        elif cfg.code is not None:
            reference = _code_html(field, cfg)
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
    front_fields,
    back_fields,
    sheet_config,
    is_cloze,
    typed=True,
    heard=("", ""),
    tts_debug="",
):
    """Builds a single {qfmt, afmt} pair from one front/back split.

    ``typed`` is False for the reverse card: the typed-answer box belongs to the
    direction the sheet described, and asking for the same answer from both sides
    would be asking the same question twice.

    ``heard`` is the pair of already-rendered TTS tags for the columns that are
    spoken without being drawn — see :func:`spoken_sides`. It arrives rendered
    rather than as field names because the two sides swap for the reverse card,
    and the caller is the one that knows which way round they go.

    ``tts_debug`` is the collapsed voice list from :func:`_tts_debug_block`, and
    goes last on the answer: it annotates the card rather than belonging to it,
    so nothing the sheet asked for should have to scroll past it.
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

    def coded(fields):
        """Whether this side has a code block, and so needs the other library."""
        return any(sheet_config.for_field(name).code is not None for name in fields)

    qfmt = (
        _css(sheet_config)
        + '<div class="s2a-wrap">\n'
        + _rows(front_fields, sheet_config, "s2a-front", as_cloze=is_cloze, quiz=True)
        + type_box
        + "\n</div>"
        + heard[0]
        + (_DRAW_SCRIPT if drawn(front_fields) else "")
        + (_CODE_SCRIPT if coded(front_fields) else "")
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
        + (_CODE_SCRIPT if coded(back_fields) else "")
        + tts_debug
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

    # Identical on both directions: it reports the device, not the card.
    tts_debug = _tts_debug_block(plan, sheet_config)

    templates = [
        dict(
            name=FRONT_TEMPLATE_NAME,
            **_one_template(
                front, back, sheet_config, is_cloze, heard=heard, tts_debug=tts_debug
            ),
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
                    tts_debug=tts_debug,
                ),
            )
        )

    return templates
