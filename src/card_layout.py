"""Turns a card layout into Anki card templates.

The layout is a plain dict (see ``sync_config.DEFAULT_LAYOUT``) naming which fields
belong on the front, which on the back, and how they should look. Everything the
card shows is derived from it, so the layout dialog never has to write HTML and the
user never has to edit the note type by hand.

A reverse card is a *second template on the same note type* rather than a second
note: Anki then schedules both directions independently while keeping one row of
data, and turning the reverse card off later removes its cards without touching the
note's content.
"""

from .card_assets import AI_HELP_BUTTON_HTML
from .card_assets import AI_HELP_CSS
from .card_assets import TIMER_CSS_BETWEEN_SECTIONS
from .card_assets import TIMER_CSS_TOP_MIDDLE
from .card_assets import TIMER_HTML
from .card_assets import TIMER_JS_BACK
from .card_assets import TIMER_JS_FRONT

FRONT_TEMPLATE_NAME = "Card 1"
REVERSE_TEMPLATE_NAME = "Card 2 (reverse)"


def _escape_field(name):
    """Anki field references are literal; only the surrounding braces are syntax."""
    return name.strip()


def _layout_css(layout):
    """Sizing and alignment come from the layout, so the dialog can drive them."""
    align = layout.get("align", "center")
    if align not in ("left", "center", "right"):
        align = "center"
    return f"""
<style>
.s2a-wrap {{ text-align: {align}; }}
.s2a-front {{ font-size: {int(layout.get("front_size", 40))}px; line-height: 1.3; }}
.s2a-back {{ font-size: {int(layout.get("back_size", 18))}px; line-height: 1.5; margin-top: 14px; }}
.s2a-label {{
  font-size: 12px; letter-spacing: .06em; text-transform: uppercase;
  opacity: .55; margin-bottom: 2px;
}}
</style>
"""


def _rows(fields, layout, css_class, is_cloze=False):
    """Renders one side's fields, each wrapped so an empty field leaves no trace."""
    show_labels = bool(layout.get("show_labels", False))
    out = []
    for name in fields:
        field = _escape_field(name)
        if not field:
            continue
        ref = f"{{{{cloze:{field}}}}}" if is_cloze else f"{{{{{field}}}}}"
        label = f'<div class="s2a-label">{field}</div>' if show_labels else ""
        out.append(
            f"{{{{#{field}}}}}"
            f'<div class="{css_class}">{label}{ref}</div>'
            f"{{{{/{field}}}}}"
        )
    return "\n".join(out)


def _timer_parts(layout):
    """Timer CSS/HTML/JS, or empty strings when the timer is switched off."""
    if not layout.get("timer", True):
        return "", "", "", ""
    position = layout.get("timer_position", "between_sections")
    css = (
        TIMER_CSS_TOP_MIDDLE if position == "top_middle" else TIMER_CSS_BETWEEN_SECTIONS
    )
    return css, TIMER_HTML, TIMER_JS_FRONT, TIMER_JS_BACK


def _one_template(front_fields, back_fields, layout, is_cloze, ai_components):
    """Builds a single {qfmt, afmt} pair from one front/back split."""
    timer_css, timer_html, timer_js_front, timer_js_back = _timer_parts(layout)

    qfmt = (
        _layout_css(layout)
        + timer_css
        + timer_html
        + '<div class="s2a-wrap">\n'
        + _rows(front_fields, layout, "s2a-front", is_cloze)
        + "\n</div>"
        + timer_js_front
    )

    if is_cloze:
        # Anki validates that a cloze template references {{cloze:Field}} on BOTH
        # sides and refuses to save the note type otherwise, so the back repeats the
        # prompt through the filter (which is also what reveals the deletion) rather
        # than pulling it in via {{FrontSide}}.
        back_head = (
            _layout_css(layout)
            + timer_css
            + timer_html
            + '<div class="s2a-wrap">\n'
            + _rows(front_fields, layout, "s2a-front", is_cloze=True)
            + "\n</div>"
        )
    else:
        back_head = "{{FrontSide}}"

    afmt = (
        back_head
        + '\n<hr id="answer">\n'
        + '<div class="s2a-wrap">\n'
        + _rows(back_fields, layout, "s2a-back", is_cloze=False)
        + "\n</div>"
        + ai_components
        + timer_js_back
    )

    return {"qfmt": qfmt, "afmt": afmt}


def build_templates(layout, is_cloze=False, ai_components=""):
    """Every card template the layout calls for.

    Args:
        layout (dict): a layout as stored by ``sync_config``
        is_cloze (bool): render the front through Anki's ``cloze:`` filter
        ai_components (str): AI button CSS/HTML/JS to append to the back, if enabled

    Returns:
        list[dict]: ``{"name", "qfmt", "afmt"}`` per template, front card first
    """
    front = list(layout.get("front") or [])
    back = list(layout.get("back") or [])

    # A layout with nothing on the front would produce a blank prompt and Anki would
    # refuse to generate the card, so fall back to the first field we do have.
    if not front and back:
        front, back = back[:1], back[1:]

    templates = [
        dict(
            name=FRONT_TEMPLATE_NAME,
            **_one_template(front, back, layout, is_cloze, ai_components),
        )
    ]

    # Cloze note types support exactly one template, so the reverse card is only
    # offered for ordinary notes.
    if layout.get("reverse_card") and not is_cloze and front and back:
        templates.append(
            dict(
                name=REVERSE_TEMPLATE_NAME,
                **_one_template(back, front, layout, False, ai_components),
            )
        )

    return templates


def ai_components_for(ai_config):
    """Assembles the AI button assets, or nothing when the feature is off."""
    if not ai_config or not ai_config.get("enabled"):
        return ""

    from .templates_and_definitions import generate_ai_assistance_js

    if ai_config.get("mobile_enabled"):
        js = generate_ai_assistance_js(
            mobile_enabled=True,
            service=ai_config.get("service", "gemini"),
            model=ai_config.get("model", ""),
            api_key=ai_config.get("api_key", ""),
            prompt_help=ai_config.get("prompt", ""),
            prompt_ask=ai_config.get("prompt_ask", ""),
            prompt_checker=ai_config.get("prompt_checker", ""),
        )
    else:
        from .card_assets import AI_HELP_JS_DESKTOP

        js = AI_HELP_JS_DESKTOP

    return AI_HELP_CSS + AI_HELP_BUTTON_HTML + js
