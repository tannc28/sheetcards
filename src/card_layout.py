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


def _css(sheet_config):
    """The card's stylesheet.

    ``--s2a-muted``/``--s2a-accent`` are declared twice on purpose: once as the light
    default and once under ``.night_mode``, the class Anki puts on the card's body in
    dark mode. A single fixed value would make one of the two themes unreadable, which
    is the whole reason the named colours exist instead of hard-coded ones.
    """
    align = sheet_config.align if sheet_config.align in ALIGNMENTS else "center"
    return (
        "<style>\n"
        ":root { --s2a-muted: #6b7280; --s2a-accent: #1a73e8; }\n"
        ".night_mode { --s2a-muted: #a1a1aa; --s2a-accent: #8ab4f8; }\n"
        f".s2a-wrap {{ text-align: {align}; }}\n"
        f".s2a-front {{ font-size: {FRONT_SIZE_PX}px; line-height: 1.3; }}\n"
        f".s2a-back {{ font-size: {BACK_SIZE_PX}px; line-height: 1.5;"
        " margin-top: 14px; }\n"
        ".s2a-label { font-size: 12px; letter-spacing: .06em;"
        " text-transform: uppercase; opacity: .55; margin-bottom: 2px; }\n"
        ".s2a-reveal > summary { cursor: pointer; font-size: 13px;"
        " letter-spacing: .06em; text-transform: uppercase; opacity: .6; }\n"
        ".s2a-embed { width: 100%; aspect-ratio: 16 / 9; border: 0;"
        " display: block; margin: 0 auto; }\n"
        "</style>\n"
    )


def _inline_style(cfg):
    """The per-field directives that are plain CSS, as one style attribute value."""
    parts = []
    if cfg.size:
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
        '<iframe src="{ref}" class="s2a-embed" allowfullscreen '
        'referrerpolicy="strict-origin-when-cross-origin" '
        'allow="encrypted-media; picture-in-picture"{style}></iframe>'
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
    # never built by string-joining here.
    return template.format(ref=f"{{{{{field}}}}}", style=style)


def _speed_text(speed):
    """``1.0`` renders as ``1`` and ``1.25`` as ``1.25`` — no trailing zeros."""
    return f"{float(speed):g}"


def _tts_tag(field, cfg, deck_speed):
    """Anki's TTS tag for the field, or "" when the field asked for no speech.

    The grammar is ``{{tts LANG [voices=A,B] [speed=N]:Field}}``: the language comes
    first and the rest are order-independent options. The tag is wrapped in the same
    ``{{#Field}}`` guard as the field itself so an empty row does not make Anki read
    out silence.
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

    tag = "{{" + " ".join(options) + f":{field}}}}}"
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


def _rows(fields, sheet_config, css_class, as_cloze=False):
    """Renders one side's fields, each wrapped so an empty field leaves no trace."""
    out = []
    for name in fields:
        field = _escape_field(name)
        if not field:
            continue

        cfg = sheet_config.for_field(name)
        style = "" if cfg.media else _inline_style(cfg)
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
        else:
            reference = _reference(field, cfg, as_cloze and cfg.cloze)

        out.append(
            f"{{{{#{field}}}}}"
            f'<div class="{css_class}"{style_attr}>{label}{reference}</div>'
            f"{{{{/{field}}}}}"
        )

        tts = _tts_tag(field, cfg, sheet_config.speed)
        if tts:
            out.append(tts)

    return "\n".join(out)


def _one_template(front_fields, back_fields, sheet_config, is_cloze, typed=True):
    """Builds a single {qfmt, afmt} pair from one front/back split.

    ``typed`` is False for the reverse card: the typed-answer box belongs to the
    direction the sheet described, and asking for the same answer from both sides
    would be asking the same question twice.
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

    qfmt = (
        _css(sheet_config)
        + '<div class="s2a-wrap">\n'
        + _rows(front_fields, sheet_config, "s2a-front", as_cloze=is_cloze)
        + type_box
        + "\n</div>"
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
        if cfg.hidden:
            continue
        # The clozed column *is* the prompt — its deletions are what the card asks
        # about — so it goes on the front whatever the column order says.
        default = "front" if (index == 0 or cfg.cloze) else "back"
        side = "front" if cfg.cloze else (cfg.side or default)
        (front if side == "front" else back).append(header)

    # An empty front would produce a blank prompt and Anki would refuse to generate
    # the card, so the first field that is still visible is promoted.
    if not front and back:
        front.append(back.pop(0))

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

    templates = [
        dict(
            name=FRONT_TEMPLATE_NAME,
            **_one_template(front, back, sheet_config, is_cloze),
        )
    ]

    # Cloze note types support exactly one template, so the reverse card is only
    # offered for ordinary notes.
    if sheet_config.reverse and not is_cloze and front and back:
        templates.append(
            dict(
                name=REVERSE_TEMPLATE_NAME,
                **_one_template(back, front, sheet_config, False, typed=False),
            )
        )

    return templates
