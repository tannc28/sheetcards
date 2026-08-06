"""Card-template assets for Sheets2Anki: CSS, HTML, and JavaScript string
constants for the study timer and the reverse-card indicator.

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
# TIMER FEATURE - CSS AND JAVASCRIPT
# =============================================================================

# Timer CSS styling - Between Sections (inline, centered)
TIMER_CSS_BETWEEN_SECTIONS = """
<style>
.sheets2anki-timer {
  display: block;
  width: fit-content;
  margin: 10px auto;
  padding: 8px 16px;
  background: rgba(0, 0, 0, 0.75);
  color: #5BA3E0;
  font-family: 'Courier New', Consolas, monospace;
  font-size: 18px;
  font-weight: bold;
  border-radius: 8px;
  text-align: center;
  user-select: none;
  pointer-events: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}
.sheets2anki-timer::before {
  content: '⏱️ ';
}
.sheets2anki-timer-frozen::before {
  content: '🏁 ';
}
</style>
"""

# Timer CSS styling - Top Middle (fixed position)
TIMER_CSS_TOP_MIDDLE = """
<style>
/* Add padding to prevent timer from covering content */
body {
  padding-top: 50px;
}
.sheets2anki-timer {
  position: fixed;
  top: 10px;
  left: 50%;
  transform: translateX(-50%);
  padding: 8px 16px;
  background: rgba(0, 0, 0, 0.75);
  color: #5BA3E0;
  font-family: 'Courier New', Consolas, monospace;
  font-size: 18px;
  font-weight: bold;
  border-radius: 8px;
  z-index: 9999;
  user-select: none;
  pointer-events: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}
.sheets2anki-timer::before {
  content: '⏱️ ';
}
.sheets2anki-timer-frozen::before {
  content: '🏁 ';
}
</style>
"""

# Default timer CSS (for backward compatibility)
TIMER_CSS = TIMER_CSS_BETWEEN_SECTIONS

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

# Timer JavaScript for FRONT side (starts timer)
TIMER_JS_FRONT = """
<script>
(function() {
  // Start timer when front side loads
  var startTime = Date.now();
  sessionStorage.setItem('sheets2anki_timer_start', startTime.toString());
  
  var timerEl = document.getElementById('sheets2anki-timer');
  if (!timerEl) return;
  
  function formatTime(ms) {
    var totalSeconds = Math.floor(ms / 1000);
    var minutes = Math.floor(totalSeconds / 60);
    var seconds = totalSeconds % 60;
    return (minutes < 10 ? '0' : '') + minutes + ':' + (seconds < 10 ? '0' : '') + seconds;
  }
  
  function updateTimer() {
    var elapsed = Date.now() - startTime;
    timerEl.textContent = formatTime(elapsed);
  }
  
  // Update immediately and then every second
  updateTimer();
  var intervalId = setInterval(updateTimer, 1000);
  
  // Store interval ID for potential cleanup
  window.sheets2ankiTimerInterval = intervalId;
})();
</script>
"""

# Timer JavaScript for BACK side (shows frozen time)
TIMER_JS_BACK = """
<script>
(function() {
  var timerEl = document.getElementById('sheets2anki-timer');
  if (!timerEl) return;
  
  // Clear any running interval from front side
  if (window.sheets2ankiTimerInterval) {
    clearInterval(window.sheets2ankiTimerInterval);
  }
  
  // Change emoji to 🏁 to indicate frozen/finished state
  timerEl.classList.add('sheets2anki-timer-frozen');
  
  var startTimeStr = sessionStorage.getItem('sheets2anki_timer_start');
  if (startTimeStr) {
    var startTime = parseInt(startTimeStr, 10);
    var elapsed = Date.now() - startTime;
    
    function formatTime(ms) {
      var totalSeconds = Math.floor(ms / 1000);
      var minutes = Math.floor(totalSeconds / 60);
      var seconds = totalSeconds % 60;
      return (minutes < 10 ? '0' : '') + minutes + ':' + (seconds < 10 ? '0' : '') + seconds;
    }
    
    timerEl.textContent = formatTime(elapsed);
  } else {
    timerEl.textContent = '--:--';
  }
})();
</script>
"""

# Timer HTML element
TIMER_HTML = '<div id="sheets2anki-timer" class="sheets2anki-timer">00:00</div>'
