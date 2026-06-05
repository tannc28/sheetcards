"""Card-template assets for Sheets2Anki: CSS, HTML, and JavaScript string
constants for the study timer, reverse-card indicator, and AI Help/Ask/Checker
buttons (extracted verbatim from templates_and_definitions.py).

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

# =============================================================================
# AI HELP BUTTON - CSS, HTML AND JAVASCRIPT
# =============================================================================

# AI Help Button CSS
AI_HELP_CSS = """
<style>
/* Theme variables - defaults to dark mode */
:root {
  --ai-bg: #1e1e1e;
  --ai-bg-secondary: #2d2d2d;
  --ai-text: #e0e0e0;
  --ai-text-muted: #888;
  --ai-border: #404040;
  --ai-accent: #5BA3E0;
  --ai-accent-secondary: #4A90D9;
  --ai-code-bg: #333;
  --ai-code-text: #f8f8f2;
  --ai-error: #ff6b6b;
  --ai-error-bg: rgba(255, 107, 107, 0.1);
  --ai-overlay: rgba(0, 0, 0, 0.7);
  --ai-shadow: rgba(0, 0, 0, 0.5);
}

/* Light mode overrides */
@media (prefers-color-scheme: light) {
  :root {
    --ai-bg: #ffffff;
    --ai-bg-secondary: #f5f5f5;
    --ai-text: #1a1a1a;
    --ai-text-muted: #666;
    --ai-border: #e0e0e0;
    --ai-accent: #4A90D9;
    --ai-accent-secondary: #357ABD;
    --ai-code-bg: #f0f0f0;
    --ai-code-text: #333;
    --ai-error: #e53e3e;
    --ai-error-bg: rgba(229, 62, 62, 0.1);
    --ai-overlay: rgba(0, 0, 0, 0.5);
    --ai-shadow: rgba(0, 0, 0, 0.2);
  }
}

/* Also support Anki's night mode class */
.night_mode {
  --ai-bg: #1e1e1e;
  --ai-bg-secondary: #2d2d2d;
  --ai-text: #e0e0e0;
  --ai-text-muted: #888;
  --ai-border: #404040;
  --ai-accent: #5BA3E0;
  --ai-accent-secondary: #4A90D9;
  --ai-code-bg: #333;
  --ai-code-text: #f8f8f2;
  --ai-error: #ff6b6b;
  --ai-error-bg: rgba(255, 107, 107, 0.1);
}

.ai-help-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin: 20px 0;
  padding: 10px;
}

.ai-buttons-row {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: center;
}

.ai-help-button {
  background: linear-gradient(135deg, var(--ai-accent) 0%, var(--ai-accent-secondary) 100%);
  color: white;
  border: none;
  border-radius: 25px;
  padding: 12px 28px;
  font-size: 14px;
  font-weight: bold;
  cursor: pointer;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
}

.ai-help-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
}

.ai-help-button:active {
  transform: translateY(0);
}

.ai-help-button.loading {
  opacity: 0.7;
  cursor: wait;
}

.ai-ask-button {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: white;
  border: none;
  border-radius: 25px;
  padding: 12px 28px;
  font-size: 14px;
  font-weight: bold;
  cursor: pointer;
  box-shadow: 0 4px 15px rgba(245, 158, 11, 0.4);
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
}

.ai-ask-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(245, 158, 11, 0.6);
}

.ai-ask-button:active {
  transform: translateY(0);
}

.ai-ask-button.loading {
  opacity: 0.7;
  cursor: wait;
}

.ai-checker-button {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  border: none;
  border-radius: 25px;
  padding: 12px 28px;
  font-size: 14px;
  font-weight: bold;
  cursor: pointer;
  box-shadow: 0 4px 15px rgba(16, 185, 129, 0.4);
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
}

.ai-checker-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(16, 185, 129, 0.6);
}

.ai-checker-button:active {
  transform: translateY(0);
}

.ai-checker-button.loading {
  opacity: 0.7;
  cursor: wait;
}

.ai-checker-button .spinner {
  display: none;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-radius: 50%;
  border-top-color: white;
  animation: spin 1s linear infinite;
}

.ai-checker-button.loading .spinner {
  display: inline-block;
}

.ai-checker-button.loading .btn-text {
  display: none;
}

.ai-help-button .spinner {
  display: none;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-radius: 50%;
  border-top-color: white;
  animation: spin 1s linear infinite;
}

.ai-help-button.loading .spinner {
  display: inline-block;
}

.ai-help-button.loading .btn-text {
  display: none;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* AI Ask Input Modal */
.ai-ask-input-modal {
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: var(--ai-overlay);
  z-index: 10001;
  justify-content: center;
  align-items: center;
}

.ai-ask-input-modal.show {
  display: flex;
}

.ai-ask-input-content {
  background: var(--ai-bg);
  color: var(--ai-text);
  border-radius: 16px;
  padding: 24px;
  max-width: 90%;
  width: 500px;
  box-shadow: 0 10px 40px var(--ai-shadow);
  border: 1px solid var(--ai-border);
  box-sizing: border-box;
}

.ai-ask-input-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--ai-border);
}

.ai-ask-input-title {
  font-size: 18px;
  font-weight: bold;
  color: #f59e0b;
}

.ai-ask-input-close {
  background: none;
  border: none;
  color: var(--ai-text-muted);
  font-size: 24px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}

.ai-ask-input-close:hover {
  background: var(--ai-bg-secondary);
  color: var(--ai-text);
}

.ai-ask-textarea {
  width: 100%;
  min-height: 100px;
  padding: 12px;
  background: var(--ai-bg-secondary);
  color: var(--ai-text);
  border: 1px solid var(--ai-border);
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  box-sizing: border-box;
  margin-bottom: 12px;
}

.ai-ask-textarea:focus {
  outline: none;
  border-color: #f59e0b;
}

.ai-ask-textarea::placeholder {
  color: var(--ai-text-muted);
}

.ai-ask-submit {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: white;
  border: none;
  border-radius: 20px;
  padding: 12px 24px;
  font-size: 15px;
  font-weight: bold;
  cursor: pointer;
  width: 100%;
  box-sizing: border-box;
  transition: all 0.3s ease;
}

.ai-ask-submit:hover {
  box-shadow: 0 4px 15px rgba(245, 158, 11, 0.5);
}

/* AI Help Response Modal (for desktop) */
.ai-help-modal {
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: var(--ai-overlay);
  z-index: 10000;
  justify-content: center;
  align-items: center;
}

.ai-help-modal.show {
  display: flex;
}

.ai-help-modal-content {
  background: var(--ai-bg);
  color: var(--ai-text);
  border-radius: 16px;
  padding: 24px;
  max-width: 90%;
  max-height: 80%;
  overflow-y: auto;
  box-shadow: 0 10px 40px var(--ai-shadow);
  position: relative;
  border: 1px solid var(--ai-border);
}

.ai-help-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--ai-border);
}

.ai-help-modal-title {
  font-size: 18px;
  font-weight: bold;
  color: var(--ai-accent);
}

.ai-help-modal-close {
  background: none;
  border: none;
  color: var(--ai-text-muted);
  font-size: 24px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}

.ai-help-modal-close:hover {
  background: var(--ai-bg-secondary);
  color: var(--ai-text);
}

.ai-help-modal-body {
  line-height: 1.7;
  font-size: 14px;
  color: var(--ai-text);
  text-align: center;
}

.ai-help-modal-body h2,
.ai-help-modal-body h3,
.ai-help-modal-body h4 {
  color: var(--ai-accent);
  margin: 16px 0 8px 0;
}

.ai-help-modal-body h2 { font-size: 18px; }
.ai-help-modal-body h3 { font-size: 16px; }
.ai-help-modal-body h4 { font-size: 15px; }

.ai-help-modal-body p { margin: 8px 0; }
.ai-help-modal-body ul, .ai-help-modal-body ol { margin: 8px auto; padding-left: 0; display: inline-block; text-align: left; }
.ai-help-modal-body li { margin: 4px 0; }

.ai-help-modal-body code {
  background: var(--ai-code-bg);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
  color: var(--ai-code-text);
}

.ai-help-modal-body strong { color: var(--ai-text); font-weight: 600; }
.ai-help-modal-body hr { border: none; border-top: 1px solid var(--ai-border); margin: 16px 0; }

.ai-help-error {
  color: var(--ai-error);
  padding: 12px;
  background: var(--ai-error-bg);
  border-radius: 8px;
  text-align: center;
}

/* Usage info - vertical layout */
.ai-help-usage {
  margin-top: 20px;
  padding-top: 12px;
  border-top: 1px solid var(--ai-border);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--ai-text-muted);
}

.ai-help-usage span {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* Inline response area (for mobile) */
.ai-help-inline {
  display: none;
  width: 100%;
  max-width: 600px;
  margin-top: 15px;
  padding: 16px;
  background: var(--ai-bg);
  border: 1px solid var(--ai-border);
  border-radius: 12px;
  line-height: 1.7;
  font-size: 14px;
  color: var(--ai-text);
  box-shadow: 0 4px 12px var(--ai-shadow);
  text-align: center;
}

.ai-help-inline.show {
  display: block;
}

.ai-help-inline h2,
.ai-help-inline h3,
.ai-help-inline h4 {
  color: var(--ai-accent);
  margin: 16px 0 8px 0;
}

.ai-help-inline h2 { font-size: 18px; }
.ai-help-inline h3 { font-size: 16px; }
.ai-help-inline h4 { font-size: 15px; }

.ai-help-inline p { margin: 8px 0; }
.ai-help-inline ul, .ai-help-inline ol { margin: 8px auto; padding-left: 0; display: inline-block; text-align: left; }
.ai-help-inline li { margin: 4px 0; }

.ai-help-inline code {
  background: var(--ai-code-bg);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
  color: var(--ai-code-text);
}

.ai-help-inline strong { color: var(--ai-text); font-weight: 600; }
.ai-help-inline hr { border: none; border-top: 1px solid var(--ai-border); margin: 16px 0; }

.ai-help-inline .ai-help-error {
  color: var(--ai-error);
  padding: 12px;
  background: var(--ai-error-bg);
  border-radius: 8px;
  text-align: center;
}

/* Base Table Styles */
.ai-help-modal-body table,
.ai-help-inline table {
  width: 100%;
  border-collapse: collapse;
  margin: 16px 0;
  font-size: 14px;
}

.ai-help-modal-body th,
.ai-help-inline th {
  background: var(--ai-bg-secondary);
  color: var(--ai-accent);
  font-weight: bold;
  text-align: center;
  padding: 10px 12px;
  border: 1px solid var(--ai-border);
}

.ai-help-modal-body td,
.ai-help-inline td {
  padding: 8px 12px;
  border: 1px solid var(--ai-border);
  color: var(--ai-text);
}

.ai-help-modal-body tr:nth-child(even),
.ai-help-inline tr:nth-child(even) {
  background: rgba(128, 128, 128, 0.05);
}

.ai-help-modal-body tr:hover,
.ai-help-inline tr:hover {
  background: rgba(128, 128, 128, 0.1);
}

</style>
"""

# AI Help Button HTML
AI_HELP_BUTTON_HTML = """
<div class="ai-help-container">
  <!-- Load marked.js for markdown parsing -->
  <script src="https://cdn.jsdelivr.net/npm/marked@9.1.6/marked.min.js" integrity="sha384-odPBjvtXVM/5hOYIr3A1dB+flh0c3wAT3bSesIOqEGmyUA4JoKf/YTWy0XKOYAY7" crossorigin="anonymous" referrerpolicy="no-referrer"></script>
  <div class="ai-buttons-row">
    <button id="ai-help-btn" class="ai-help-button" onclick="requestAIHelp()">
      <span class="btn-text">🤖 AI Help</span>
      <span class="spinner"></span>
    </button>
    <button id="ai-ask-btn" class="ai-ask-button" onclick="openAIAskInput()">
      <span class="btn-text">💬 AI Ask</span>
      <span class="spinner"></span>
    </button>
    <button id="ai-checker-btn" class="ai-checker-button" onclick="requestAIChecker()">
      <span class="btn-text">🔍 AI Checker</span>
      <span class="spinner"></span>
    </button>
  </div>
  <div id="ai-help-inline" class="ai-help-inline"></div>
</div>

<div id="ai-ask-input-modal" class="ai-ask-input-modal" onclick="closeAIAskInput(event)">
  <div class="ai-ask-input-content" onclick="event.stopPropagation()">
    <div class="ai-ask-input-header">
      <span class="ai-ask-input-title">💬 AI Ask</span>
      <button class="ai-ask-input-close" onclick="closeAIAskInput()">&times;</button>
    </div>
    <textarea id="ai-ask-textarea" class="ai-ask-textarea" placeholder="Type your question here..."></textarea>
    <button class="ai-ask-submit" onclick="submitAIAsk()">Send Question</button>
  </div>
</div>

<div id="ai-help-modal" class="ai-help-modal" onclick="closeAIHelpModal(event)">
  <div class="ai-help-modal-content" onclick="event.stopPropagation()">
    <div class="ai-help-modal-header">
      <span class="ai-help-modal-title">🤖 AI Help</span>
      <button class="ai-help-modal-close" onclick="closeAIHelpModal()">&times;</button>
    </div>
    <div id="ai-help-modal-body" class="ai-help-modal-body">
      Loading...
    </div>
  </div>
</div>
"""

# AI Help JavaScript - Base template (desktop-only mode)
# Shared <script> head for BOTH AI templates: the security sanitizer
# (escapeHtml / sanitizeHtml). Single source of truth — fix it in one place.
_AI_JS_HEAD = """
<script>
// --- Security: sanitize AI/markdown HTML before inserting via innerHTML ---
function escapeHtml(s) {
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
function sanitizeHtml(dirty) {
  // Conservative allowlist sanitizer (no external dependency, works offline):
  // renders formatted AI output while stripping script-execution vectors.
  var root = document.createElement('div');
  root.innerHTML = String(dirty == null ? '' : dirty);
  var banned = {SCRIPT:1, STYLE:1, IFRAME:1, OBJECT:1, EMBED:1, FORM:1, LINK:1, META:1, BASE:1, SVG:1, MATH:1};
  var els = root.querySelectorAll('*');
  for (var i = els.length - 1; i >= 0; i--) {
    var el = els[i];
    if (banned[el.tagName]) { if (el.parentNode) el.parentNode.removeChild(el); continue; }
    for (var j = el.attributes.length - 1; j >= 0; j--) {
      var an = el.attributes[j].name, av = el.attributes[j].value || '', ln = an.toLowerCase();
      if (ln.indexOf('on') === 0) { el.removeAttribute(an); continue; }
      if (ln === 'href' || ln === 'src' || ln === 'xlink:href' || ln === 'formaction' || ln === 'action') {
        var v = av.replace(/\\s+/g, '').toLowerCase();
        if (v.indexOf('javascript:') === 0 || (v.indexOf('data:') === 0 && v.indexOf('data:image/') !== 0)) el.removeAttribute(an);
      } else if (ln === 'style' && /expression|javascript:/i.test(av)) {
        el.removeAttribute(an);
      }
    }
  }
  return root.innerHTML;
}
"""

# Shared <script> tail for BOTH AI templates: the modal-close handler + the
# globalThis bridge that Python's reviewer.web.eval() calls into. Single source of truth.
_AI_JS_TAIL = """

function closeAIHelpModal(event) {
  if (event && event.target !== event.currentTarget) return;
  var modal = document.getElementById('ai-help-modal');
  if (modal) modal.classList.remove('show');
}

if (typeof globalThis !== 'undefined') {
  globalThis.sheets2ankiAIResponse = function(response, usageInfo) {
    showAIHelpResponse(response, usageInfo);
  };
  globalThis.sheets2ankiAIError = function(error) {
    showAIHelpError(error);
  };
}
</script>
"""

# Shared middle helpers, byte-identical in both desktop and mobile blocks.
# Composed into both via `""" + _AI_JS_X + """` splices, so each lives in one place.
_AI_JS_ASK_MODAL = """function openAIAskInput() {
  var modal = document.getElementById('ai-ask-input-modal');
  if (modal) {
    modal.classList.add('show');
    var textarea = document.getElementById('ai-ask-textarea');
    if (textarea) {
      textarea.value = '';
      textarea.focus();
    }
  }
}

function closeAIAskInput(event) {
  if (event && event.target !== event.currentTarget) return;
  var modal = document.getElementById('ai-ask-input-modal');
  if (modal) modal.classList.remove('show');
}"""

_AI_JS_RESET_ASK = """function resetAIAskInput() {
  var submitBtn = document.querySelector('.ai-ask-submit');
  if (submitBtn) {
    submitBtn.classList.remove('loading');
    submitBtn.innerHTML = 'Send Question';
  }
  var textarea = document.getElementById('ai-ask-textarea');
  if (textarea) textarea.disabled = false;
  closeAIAskInput();
}"""

_AI_JS_COLLECT = """function collectCardContent() {
  // Always return the original card content snapshot, never re-read the DOM
  return window._originalCardContent || '';
}"""

_AI_JS_RENDER = """function renderMathJax() {
  if (typeof MathJax !== 'undefined') {
    if (MathJax.typesetPromise) {
      MathJax.typesetPromise();
    } else if (MathJax.Hub && MathJax.Hub.Queue) {
      MathJax.Hub.Queue(["Typeset", MathJax.Hub]);
    }
  }
}"""

# (@@B6@@ marks an original 6-space blank line; kept as a marker so the source
# carries no trailing whitespace, substituted back at import time.)
_AI_JS_CAPTURE = """// Capture the original card content ONCE on page load, before any AI response is injected.
// This prevents AI responses from contaminating subsequent AI requests.
(function() {
  function captureOriginalContent() {
    if (!window._originalCardContent) {
      // Temporarily hide sanity check so it's not included in AI context
      var sanityCheck = document.querySelector('.sanity-check-container');
      var originalDisplay = '';
      if (sanityCheck) {
        originalDisplay = sanityCheck.style.display;
        sanityCheck.style.display = 'none';
      }
@@B6@@
      var allText = document.body.innerText || document.body.textContent;
@@B6@@
      // Restore sanity check visibility
      if (sanityCheck) {
        sanityCheck.style.display = originalDisplay;
      }
@@B6@@
      window._originalCardContent = allText.trim();
    }
  }
  // Capture immediately (for cases where DOM is already ready)
  captureOriginalContent();
  // Also capture on DOMContentLoaded (fallback for early script execution)
  document.addEventListener('DOMContentLoaded', captureOriginalContent);
})();""".replace(
    "@@B6@@", "      "
)

AI_HELP_JS_DESKTOP = (
    _AI_JS_HEAD
    + """// Desktop-only mode: hide button if pycmd not available
(function() {
  if (typeof pycmd === 'undefined') {
    document.addEventListener('DOMContentLoaded', function() {
      var container = document.querySelector('.ai-help-container');
      if (container) container.style.display = 'none';
    });
    var container = document.querySelector('.ai-help-container');
    if (container) container.style.display = 'none';
  }
})();

function requestAIHelp() {
  var btn = document.getElementById('ai-help-btn');
  if (!btn || btn.classList.contains('loading')) return;
  
  btn.classList.add('loading');
  window._aiModalTitle = '🤖 AI Help';
  var cardContent = collectCardContent();
  
  if (typeof pycmd !== 'undefined') {
    pycmd('sheets2anki_ai_help:' + encodeURIComponent(cardContent));
  } else {
    btn.classList.remove('loading');
  }
}

function requestAIChecker() {
  var btn = document.getElementById('ai-checker-btn');
  if (!btn || btn.classList.contains('loading')) return;
  
  btn.classList.add('loading');
  window._aiModalTitle = '🔍 AI Checker';
  var cardContent = collectCardContent();
  
  if (typeof pycmd !== 'undefined') {
    pycmd('sheets2anki_ai_checker:' + encodeURIComponent(cardContent));
  } else {
    btn.classList.remove('loading');
  }
}

"""
    + _AI_JS_ASK_MODAL
    + """

function submitAIAsk() {
  var submitBtn = document.querySelector('.ai-ask-submit');
  if (submitBtn && submitBtn.classList.contains('loading')) return;
  
  var textarea = document.getElementById('ai-ask-textarea');
  var question = textarea ? textarea.value.trim() : '';
  if (!question) return;
  
  var btn = document.getElementById('ai-ask-btn');
  if (btn) btn.classList.add('loading');
  window._aiModalTitle = '💬 AI Ask';
  
  if (submitBtn) {
    submitBtn.classList.add('loading');
    submitBtn.innerHTML = 'Sending... ⏳';
  }
  if (textarea) textarea.disabled = true;
  
  var cardContent = collectCardContent();
  
  if (typeof pycmd !== 'undefined') {
    pycmd('sheets2anki_ai_ask:' + encodeURIComponent(question) + '|||' + encodeURIComponent(cardContent));
  } else {
    resetAIAskInput();
  }
}

"""
    + _AI_JS_RESET_ASK
    + """


"""
    + """
"""
    + _AI_JS_CAPTURE
    + """

"""
    + _AI_JS_COLLECT
    + """

"""
    + """
function processMathAndMarkdown(text) {
  var mathBlocks = [];
  var placeholder = "MATHBLOCK";
  var suffix = "END";
  
  // Display math $$ ... $$ -> \\[ ... \\]
  text = text.replace(/\\$\\$([\\s\\S]*?)\\$\\$/g, function(match, content) {
    var id = mathBlocks.length;
    mathBlocks.push('\\\\[' + content + '\\\\]');
    return placeholder + id + suffix;
  });
  
  // Inline math $ ... $ -> \\( ... \\) (Disallow newlines)
  text = text.replace(/([^\\\\$]|^)\\$([^\\s$\\n](?:[^$\\n]*?[^\\s$\\n])?)\\$(?!\\d)/g, function(match, prefix, content) {
    var id = mathBlocks.length;
    mathBlocks.push('\\\\(' + content + '\\\\)');
    return prefix + placeholder + id + suffix;
  });
  
  var html = (typeof marked !== 'undefined') ? marked.parse(text) : text;
  
  for (var i = 0; i < mathBlocks.length; i++) {
    var regex = new RegExp(placeholder + i + suffix, 'g');
    html = html.replace(regex, mathBlocks[i]);
  }
  
  return html;
}

"""
    + _AI_JS_RENDER
    + """

function showAIHelpResponse(response, usageInfo) {
  var btn = document.getElementById('ai-help-btn');
  if (btn) btn.classList.remove('loading');
  var askBtn = document.getElementById('ai-ask-btn');
  if (askBtn) askBtn.classList.remove('loading');
  var checkerBtn = document.getElementById('ai-checker-btn');
  if (checkerBtn) checkerBtn.classList.remove('loading');
  
  if (typeof resetAIAskInput === 'function') resetAIAskInput();
  
  var modal = document.getElementById('ai-help-modal');
  var body = document.getElementById('ai-help-modal-body');
  if (!modal || !body) return;
  var titleEl = document.querySelector('.ai-help-modal-title');
  if (titleEl && window._aiModalTitle) titleEl.textContent = window._aiModalTitle;
  
  var html = processMathAndMarkdown(response);
  
  if (usageInfo && (usageInfo.input_tokens || usageInfo.output_tokens)) {
    var totalTokens = usageInfo.input_tokens + usageInfo.output_tokens;
    var cost = usageInfo.cost || 0;
    var costStr = cost < 0.01 ? cost.toFixed(6) : cost.toFixed(4);
    html += '<div class="ai-help-usage">';
    html += '<span>📊 Tokens: ' + totalTokens + ' (' + usageInfo.input_tokens + ' in / ' + usageInfo.output_tokens + ' out)</span>';
    html += '<span>💰 Cost: $' + costStr + '</span>';
    html += '</div>';
  }
  
  body.innerHTML = sanitizeHtml(html);
  modal.classList.add('show');
  
  // Trigger MathJax
  setTimeout(renderMathJax, 10);
}

function showAIHelpError(error) {
  var btn = document.getElementById('ai-help-btn');
  if (btn) btn.classList.remove('loading');
  var askBtn = document.getElementById('ai-ask-btn');
  if (askBtn) askBtn.classList.remove('loading');
  var checkerBtn = document.getElementById('ai-checker-btn');
  if (checkerBtn) checkerBtn.classList.remove('loading');
  
  if (typeof resetAIAskInput === 'function') resetAIAskInput();
  
  var modal = document.getElementById('ai-help-modal');
  var body = document.getElementById('ai-help-modal-body');
  if (!modal || !body) return;
  body.innerHTML = '<div class="ai-help-error">⚠️ ' + escapeHtml(error) + '</div>';
  modal.classList.add('show');
}"""
    + _AI_JS_TAIL
)

# AI Help JavaScript - Mobile mode (with embedded API config)
AI_HELP_JS_MOBILE_TEMPLATE = (
    _AI_JS_HEAD
    + """// Decode Base64-encoded prompts to prevent HTML parser corruption
function _b64decode(str) {
  try {
    return decodeURIComponent(Array.prototype.map.call(
      atob(str), function(c) {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
      }
    ).join(''));
  } catch(e) {
    return atob(str);
  }
}

// AI Help Config (embedded for mobile support)
var AI_CONFIG = {
  service: {service_json},
  model: {model_json},
  apiKey: {api_key_json},
  prompt_help: _b64decode("{prompt_help_b64}"),
  prompt_ask: _b64decode("{prompt_ask_b64}"),
  prompt_checker: _b64decode("{prompt_checker_b64}")
};

// Pricing per 1M tokens
var PRICING = {
  'gemini-2.0-flash': [0.10, 0.40],
  'gemini-1.5-flash': [0.075, 0.30],
  'gemini-1.5-pro': [1.25, 5.00],
  'gemini-pro': [0.50, 1.50],
  'claude-sonnet-4': [3.00, 15.00],
  'claude-3-5-sonnet': [3.00, 15.00],
  'claude-3-5-haiku': [0.80, 4.00],
  'claude-3-opus': [15.00, 75.00],
  'claude-3-haiku': [0.25, 1.25],
  'gpt-4o': [2.50, 10.00],
  'gpt-4o-mini': [0.15, 0.60],
  'gpt-4-turbo': [10.00, 30.00],
  'gpt-4': [30.00, 60.00],
  'gpt-3.5-turbo': [0.50, 1.50],
  'o1': [15.00, 60.00],
  'o1-mini': [3.00, 12.00]
};

function getPricing(model) {
  model = model.toLowerCase();
  for (var prefix in PRICING) {
    if (model.indexOf(prefix) !== -1) return PRICING[prefix];
  }
  return [1.00, 3.00];
}

function calculateCost(model, inputTokens, outputTokens) {
  var p = getPricing(model);
  return (inputTokens * p[0] / 1000000) + (outputTokens * p[1] / 1000000);
}

function requestAIHelp() {
  var btn = document.getElementById('ai-help-btn');
  if (!btn || btn.classList.contains('loading')) return;
  
  btn.classList.add('loading');
  window._aiModalTitle = '🤖 AI Help';
  var cardContent = collectCardContent();
  
  // Try desktop first
  if (typeof pycmd !== 'undefined') {
    pycmd('sheets2anki_ai_help:' + encodeURIComponent(cardContent));
    return;
  }
  
  // Mobile: direct API call
  callAIAPI(cardContent);
}

function requestAIChecker() {
  var btn = document.getElementById('ai-checker-btn');
  if (!btn || btn.classList.contains('loading')) return;
  
  btn.classList.add('loading');
  window._aiModalTitle = '🔍 AI Checker';
  var cardContent = collectCardContent();
  
  // Try desktop first
  if (typeof pycmd !== 'undefined') {
    pycmd('sheets2anki_ai_checker:' + encodeURIComponent(cardContent));
    return;
  }
  
  // Mobile: direct API call with checker prompt
  callAICheckerAPI(cardContent);
}

"""
    + _AI_JS_ASK_MODAL
    + """

function submitAIAsk() {
  var submitBtn = document.querySelector('.ai-ask-submit');
  if (submitBtn && submitBtn.classList.contains('loading')) return;
  
  var textarea = document.getElementById('ai-ask-textarea');
  var question = textarea ? textarea.value.trim() : '';
  if (!question) return;
  
  var btn = document.getElementById('ai-ask-btn');
  if (btn) btn.classList.add('loading');
  window._aiModalTitle = '💬 AI Ask';
  
  if (submitBtn) {
    submitBtn.classList.add('loading');
    submitBtn.innerHTML = 'Sending... ⏳';
  }
  if (textarea) textarea.disabled = true;
  
  var cardContent = collectCardContent();
  
  // Try desktop first
  if (typeof pycmd !== 'undefined') {
    pycmd('sheets2anki_ai_ask:' + encodeURIComponent(question) + '|||' + encodeURIComponent(cardContent));
    return;
  }
  
  // Mobile: direct API call with custom question
  callAIAskAPI(question, cardContent);
}

"""
    + _AI_JS_RESET_ASK
    + """

function _replacePromptPlaceholder(promptTemplate, placeholder, value) {
  // Handles both {placeholder} and {placeholder} forms
  var regex = new RegExp('\\u007B\\u007B' + placeholder + '\\u007D\\u007D|\\u007B' + placeholder + '\\u007D', 'g');
  var testRegex = new RegExp('\\u007B\\u007B' + placeholder + '\\u007D\\u007D|\\u007B' + placeholder + '\\u007D');
  var hadPlaceholder = testRegex.test(promptTemplate);
  var result = promptTemplate.replace(regex, value);
  return { text: result, had: hadPlaceholder };
}

function callAIAskAPI(question, cardContent) {
  var promptTemplate = AI_CONFIG.prompt_ask;
  
  // Replace {card_content} placeholder with fallback
  var r1 = _replacePromptPlaceholder(promptTemplate, 'card_content', cardContent);
  var prompt = r1.text;
  if (!r1.had) {
    prompt = prompt + '\\n\\n' + cardContent;
  }
  
  // Replace {question} placeholder with fallback
  var r2 = _replacePromptPlaceholder(prompt, 'question', question);
  prompt = r2.text;
  if (!r2.had) {
    prompt = prompt + '\\n\\nQuestion: ' + question;
  }
  
  if (AI_CONFIG.service === 'gemini') {
    callGeminiAPI(prompt);
  } else if (AI_CONFIG.service === 'claude') {
    callClaudeAPI(prompt);
  } else if (AI_CONFIG.service === 'openai') {
    callOpenAIAPI(prompt);
  }
}

function callAIAPI(cardContent) {
  var promptTemplate = AI_CONFIG.prompt_help;
  var r = _replacePromptPlaceholder(promptTemplate, 'card_content', cardContent);
  var prompt = r.text;
  if (!r.had) {
    prompt = prompt + '\\n\\n' + cardContent;
  }
  
  if (AI_CONFIG.service === 'gemini') {
    callGeminiAPI(prompt);
  } else if (AI_CONFIG.service === 'claude') {
    callClaudeAPI(prompt);
  } else if (AI_CONFIG.service === 'openai') {
    callOpenAIAPI(prompt);
  }
}

function callAICheckerAPI(cardContent) {
  var checkerTemplate = AI_CONFIG.prompt_checker;
  var r = _replacePromptPlaceholder(checkerTemplate, 'card_content', cardContent);
  var prompt = r.text;
  if (!r.had) {
    prompt = prompt + '\\n\\n' + cardContent;
  }
  
  if (AI_CONFIG.service === 'gemini') {
    callGeminiAPI(prompt);
  } else if (AI_CONFIG.service === 'claude') {
    callClaudeAPI(prompt);
  } else if (AI_CONFIG.service === 'openai') {
    callOpenAIAPI(prompt);
  }
}

function callGeminiAPI(prompt) {
  var url = 'https://generativelanguage.googleapis.com/v1beta/models/' + AI_CONFIG.model + ':generateContent?key=' + AI_CONFIG.apiKey;
  
  fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
      generationConfig: { temperature: 0.7, maxOutputTokens: 4096 }
    })
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    if (data.error) {
      showAIHelpError(data.error.message || 'API Error');
      return;
    }
    var text = '';
    try {
      text = data.candidates[0].content.parts[0].text;
    } catch(e) {
      text = 'No response generated';
    }
    var usage = data.usageMetadata || {};
    var inputTokens = usage.promptTokenCount || 0;
    var outputTokens = usage.candidatesTokenCount || 0;
    showAIHelpResponse(text, {
      input_tokens: inputTokens,
      output_tokens: outputTokens,
      cost: calculateCost(AI_CONFIG.model, inputTokens, outputTokens)
    });
  })
  .catch(function(e) { showAIHelpError('Request failed: ' + e.message); });
}

function callClaudeAPI(prompt) {
  // Note: Claude API may have CORS restrictions from browser
  var url = 'https://api.anthropic.com/v1/messages';
  
  fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': AI_CONFIG.apiKey,
      'anthropic-version': '2023-06-01',
      'anthropic-dangerous-direct-browser-access': 'true'
    },
    body: JSON.stringify({
      model: AI_CONFIG.model,
      max_tokens: 4096,
      messages: [{ role: 'user', content: prompt }]
    })
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    if (data.error) {
      showAIHelpError(data.error.message || 'API Error');
      return;
    }
    var text = data.content && data.content[0] ? data.content[0].text : 'No response';
    var usage = data.usage || {};
    showAIHelpResponse(text, {
      input_tokens: usage.input_tokens || 0,
      output_tokens: usage.output_tokens || 0,
      cost: calculateCost(AI_CONFIG.model, usage.input_tokens || 0, usage.output_tokens || 0)
    });
  })
  .catch(function(e) { showAIHelpError('Request failed: ' + e.message); });
}

function callOpenAIAPI(prompt) {
  var url = 'https://api.openai.com/v1/chat/completions';
  
  fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + AI_CONFIG.apiKey
    },
    body: JSON.stringify({
      model: AI_CONFIG.model,
      messages: [{ role: 'user', content: prompt }],
      max_tokens: 4096,
      temperature: 0.7
    })
  })
  .then(function(r) { return r.json(); })
  .then(function(data) {
    if (data.error) {
      showAIHelpError(data.error.message || 'API Error');
      return;
    }
    var text = data.choices && data.choices[0] ? data.choices[0].message.content : 'No response';
    var usage = data.usage || {};
    showAIHelpResponse(text, {
      input_tokens: usage.prompt_tokens || 0,
      output_tokens: usage.completion_tokens || 0,
      cost: calculateCost(AI_CONFIG.model, usage.prompt_tokens || 0, usage.completion_tokens || 0)
    });
  })
  .catch(function(e) { showAIHelpError('Request failed: ' + e.message); });
}

"""
    + _AI_JS_CAPTURE
    + """

"""
    + _AI_JS_COLLECT
    + """

function processMathAndMarkdown(text) {
  var mathBlocks = [];
  var placeholder = "MATHBLOCK";
  var suffix = "END";
  
  // Display math $$ ... $$ -> \\[ ... \\]
  text = text.replace(/\\$\\$([\\s\\S]*?)\\$\\$/g, function(match, content) {
    var id = mathBlocks.length;
    mathBlocks.push('\\\\[' + content + '\\\\]');
    return placeholder + id + suffix;
  });
  
  // Inline math $ ... $ -> \\( ... \\)
  text = text.replace(/([^\\\\$]|^)\\$([^\\s$\\n](?:[^$\\n]*?[^\\s$\\n])?)\\$(?!\\d)/g, function(match, prefix, content) {
    var id = mathBlocks.length;
    mathBlocks.push('\\\\(' + content + '\\\\)');
    return prefix + placeholder + id + suffix;
  });
  
  var html = (typeof marked !== 'undefined') ? marked.parse(text) : text;
  
  for (var i = 0; i < mathBlocks.length; i++) {
    var regex = new RegExp(placeholder + i + suffix, 'g');
    html = html.replace(regex, mathBlocks[i]);
  }
  
  return html;
}

"""
    + _AI_JS_RENDER
    + """

function showAIHelpResponse(response, usageInfo) {
  var btn = document.getElementById('ai-help-btn');
  if (btn) btn.classList.remove('loading');
  var askBtn = document.getElementById('ai-ask-btn');
  if (askBtn) askBtn.classList.remove('loading');
  var checkerBtn = document.getElementById('ai-checker-btn');
  if (checkerBtn) checkerBtn.classList.remove('loading');
  
  if (typeof resetAIAskInput === 'function') resetAIAskInput();
  
  var html = processMathAndMarkdown(response);
  
  if (usageInfo && (usageInfo.input_tokens || usageInfo.output_tokens)) {
    var totalTokens = usageInfo.input_tokens + usageInfo.output_tokens;
    var cost = usageInfo.cost || 0;
    var costStr = cost < 0.01 ? cost.toFixed(6) : cost.toFixed(4);
    html += '<div class="ai-help-usage">';
    html += '<span>📊 Tokens: ' + totalTokens + ' (' + usageInfo.input_tokens + ' in / ' + usageInfo.output_tokens + ' out)</span>';
    html += '<span>💰 Cost: $' + costStr + '</span>';
    html += '</div>';
  }
  
  // On mobile (no pycmd), show inline; on desktop, use modal
  if (typeof pycmd === 'undefined') {
    var inline = document.getElementById('ai-help-inline');
    if (inline) {
      var titleHtml = window._aiModalTitle ? '<h3>' + window._aiModalTitle + '</h3>' : '';
      inline.innerHTML = titleHtml + sanitizeHtml(html);
      inline.classList.add('show');
    }
  } else {
    var modal = document.getElementById('ai-help-modal');
    var body = document.getElementById('ai-help-modal-body');
    if (!modal || !body) return;
    var titleEl = document.querySelector('.ai-help-modal-title');
    if (titleEl && window._aiModalTitle) titleEl.textContent = window._aiModalTitle;
    body.innerHTML = sanitizeHtml(html);
    modal.classList.add('show');
  }
  
  // Trigger MathJax
  setTimeout(renderMathJax, 10);
}

function showAIHelpError(error) {
  var btn = document.getElementById('ai-help-btn');
  if (btn) btn.classList.remove('loading');
  var askBtn = document.getElementById('ai-ask-btn');
  if (askBtn) askBtn.classList.remove('loading');
  var checkerBtn = document.getElementById('ai-checker-btn');
  if (checkerBtn) checkerBtn.classList.remove('loading');
  
  if (typeof resetAIAskInput === 'function') resetAIAskInput();
  
  var errorHtml = '<div class="ai-help-error">⚠️ ' + escapeHtml(error) + '</div>';
  
  // On mobile (no pycmd), show inline; on desktop, use modal
  if (typeof pycmd === 'undefined') {
    var inline = document.getElementById('ai-help-inline');
    if (inline) {
      var titleHtml = window._aiModalTitle ? '<h3>' + window._aiModalTitle + '</h3>' : '';
      inline.innerHTML = titleHtml + errorHtml;
      inline.classList.add('show');
    }
  } else {
    var modal = document.getElementById('ai-help-modal');
    var body = document.getElementById('ai-help-modal-body');
    if (!modal || !body) return;
    var titleEl = document.querySelector('.ai-help-modal-title');
    if (titleEl && window._aiModalTitle) titleEl.textContent = window._aiModalTitle;
    body.innerHTML = errorHtml;
    modal.classList.add('show');
  }
}"""
    + _AI_JS_TAIL
)

# Keep old constant for backward compatibility (desktop-only mode)
AI_HELP_JS = AI_HELP_JS_DESKTOP
