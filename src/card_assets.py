"""Card-template assets for Sheets2Anki: CSS and HTML string constants for the
card body and the reverse-card indicator.

Pure string constants — the model-building functions in templates_and_definitions
compose these into note-type templates."""

CARD_SHOW_ALLWAYS_TEMPLATE = """
<b>➡️ {field_name}</b><br>
{{{{{field_value}}}}}<br><br>
"""

CARD_SHOW_HIDE_TEMPLATE = """
{{{{#{field_value}}}}}
<b>➡️ {field_name}</b><br>
{{{{{field_value}}}}}<br><br>
{{{{/{field_value}}}}}
"""

MARKERS_TEMPLATE = """
<h2 style="color: orange; text-align: center; margin-bottom: 0;">{text}</h2>
<div style="text-align: center; font-size: 0.8em; color: gray;">{observation}</div>
<hr>
"""


# Divider between the question and the answer on the back of the card. Anki styles the
# "answer" id itself, so the rule also gives themes something to hook onto.
ANSWER_SEPARATOR_HTML = '\n<hr id="answer">\n'


# =============================================================================
# REVERSE CARD INDICATOR - CSS
# =============================================================================

# Reverse Card Indicator CSS
REVERSE_INDICATOR_CSS = """
<style>
.reverse-card-indicator {
  display: block;
  width: fit-content;
  margin: 0 auto 20px auto;
  padding: 10px 20px;
  background: linear-gradient(135deg, #4A90D9 0%, #357ABD 100%);
  color: #ffffff;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 14px;
  font-weight: 600;
  border-radius: 20px;
  text-align: center;
  box-shadow: 0 3px 10px rgba(74, 144, 217, 0.3);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}
.reverse-card-indicator::before {
  content: '🔄 ';
  font-size: 16px;
}
</style>
"""

# Reverse Card Indicator HTML
REVERSE_INDICATOR_HTML = '<div class="reverse-card-indicator">Card Reverso</div>'
