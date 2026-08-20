#!/usr/bin/env python3
"""The voice list the card draws on the device that reviews it.

`card_layout._TTS_VOICES_SCRIPT` is the one piece of this repo that cannot be
checked by calling it: it is JavaScript, it runs inside a card, and what it reads
is whatever `{{tts-voices:}}` printed on that particular phone. So it is run here
in node against a dump captured from a real iPhone (iOS 26, AnkiMobile), with a
DOM stub holding only the handful of methods the script touches.

The dump is what makes this worth having. Every assumption the script started
with was wrong against it: the device writes `en-US` where the sheet writes
`en_US`, and each entry is a whole ready-made tag with the field still on it
(`voices=Apple_Ava_(Premium):Front`), which would otherwise be copied into a
spreadsheet cell verbatim.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")

# Captured from an iPhone 15 Pro Max. Trimmed to the languages that matter here —
# the shape of every line is the device's own, including the "Enhanced:" group,
# which repeats a voice that also appears in the main list.
IPHONE = """Available TTS voices:
Enhanced: {{tts en-US voices=Apple_Ava_(Enhanced):Front}}
{{tts de-DE voices=Apple_Anna:Front}}
{{tts de-DE voices=Apple_Eddy:Front}}
{{tts de-DE voices=Apple_Grandma:Front}}
{{tts en-AU voices=Apple_Karen:Front}}
{{tts en-GB voices=Apple_Daniel:Front}}
{{tts en-GB voices=Apple_Eddy:Front}}
{{tts en-GB voices=Apple_Grandma:Front}}
{{tts en-US voices=Apple_Albert:Front}}
{{tts en-US voices=Apple_Ava_(Enhanced):Front}}
{{tts en-US voices=Apple_Ava_(Premium):Front}}
{{tts en-US voices=Apple_Bad_News:Front}}
{{tts en-US voices=Apple_Bells:Front}}
{{tts en-US voices=Apple_Boing:Front}}
{{tts en-US voices=Apple_Eddy:Front}}
{{tts en-US voices=Apple_Fred:Front}}
{{tts en-US voices=Apple_Grandma:Front}}
{{tts en-US voices=Apple_Samantha:Front}}
{{tts en-US voices=Apple_Trinoids:Front}}
{{tts en-US voices=Apple_Zarvox:Front}}
{{tts vi-VN voices=Apple_Linh:Front}}
{{tts zh-CN voices=Apple_Eddy:Front}}
{{tts zh-CN voices=Apple_Tingting:Front}}"""


# A device where the only voice for the language is one of the joke set. Folding
# it away would leave a heading with nothing under it.
ONLY_JUNK = """Available TTS voices:
{{tts en-US voices=Apple_Zarvox:Front}}
{{tts vi-VN voices=Apple_Linh:Front}}"""

# Every voice this language has, it shares with another. Counting them all away
# would leave the same empty heading.
ONLY_SHARED = """Available TTS voices:
{{tts en-US voices=Apple_Eddy:Front}}
{{tts en-US voices=Apple_Grandma:Front}}
{{tts de-DE voices=Apple_Eddy:Front}}
{{tts de-DE voices=Apple_Grandma:Front}}"""


def _script():
    """The card's script, as the browser would receive it."""
    from src.card_layout import _TTS_VOICES_SCRIPT

    return _TTS_VOICES_SCRIPT.replace("<script>", "").replace("</script>", "")


# Anki joins the entries with <br>, so the card sees one line with no separators
# in it at all. Splitting on newlines here would hide the very thing that broke.
_HARNESS = """
function El(cls) {
  this.className = cls || ""; this.dataset = {}; this.children = [];
  this.textContent = ""; this._q = {}; this._qa = {};
}
El.prototype.appendChild = function (c) { c.parent = this; this.children.push(c); return c; };
El.prototype.insertBefore = function (c, before) {
  c.parent = this;
  this.children.splice(this.children.indexOf(before), 0, c);
  return c;
};
El.prototype.remove = function () {
  this.removed = true;
  if (this.parent) {
    var at = this.parent.children.indexOf(this);
    if (at >= 0) this.parent.children.splice(at, 1);
  }
};
El.prototype.setAttribute = function () {};
El.prototype.querySelector = function (s) { return this._q[s] || null; };
El.prototype.querySelectorAll = function (s) { return this._qa[s] || []; };

var raw = new El("sc-tts-raw");
raw.textContent = DUMP.split("\\n").join("");
var list = new El("sc-tts-list");
var note = new El("sc-tts-note");
note.textContent = "Tap the play button to hear a voice.";

var srcs = COLUMNS.map(function (c) {
  var el = new El();
  el.dataset = { col: c.col, lang: c.lang };
  el.textContent = c.text;
  return el;
});

var box = new El("sc-tts-debug");
box.dataset = { scLangs: WANTED };
box._q = { ".sc-tts-raw": raw, ".sc-tts-list": list, ".sc-tts-note": note };
box._qa = { ".sc-tts-src": srcs };

global.document = {
  querySelector: function () { return box; },
  createElement: function () { return new El(); },
};
global.window = SPEAKS ? { speechSynthesis: {} } : {};

SCRIPT

if (REVEAL) {
  list.children
    .filter(function (c) { return c.className === "sc-tts-more"; })
    .forEach(function (b) { b.onclick({ preventDefault: function () {} }); });
}

var out = { note: note.removed ? null : note.textContent, message: "", rows: [] };
list.children.forEach(function (c) {
  if (c.className === "sc-tts-lang") { out.rows.push({ lang: c.textContent }); return; }
  if (c.className === "sc-tts-more") { out.rows.push({ more: c.textContent }); return; }
  out.rows.push({
    voice: c.children[0].textContent,
    buttons: c.children.slice(1).map(function (b) { return b.textContent; }),
  });
});
if (!list.children.length || list.children[0].className !== "sc-tts-lang") {
  out.message = list.textContent;
}
console.log(JSON.stringify(out));
"""


def _run(
    dump,
    wanted="en_US",
    columns=(("Word", "en_US", "hold"),),
    speaks=True,
    reveal=False,
):
    cols = [{"col": c, "lang": lang, "text": t} for c, lang, t in columns]
    script = (
        f"var DUMP = {json.dumps(dump)};\n"
        f"var WANTED = {json.dumps(wanted)};\n"
        f"var COLUMNS = {json.dumps(cols)};\n"
        f"var SPEAKS = {json.dumps(speaks)};\n"
        f"var REVEAL = {json.dumps(reveal)};\n" + _HARNESS.replace("SCRIPT", _script())
    )
    result = subprocess.run(
        [NODE, "-e", script], capture_output=True, text=True, cwd=ROOT, timeout=30
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _voices(out):
    return [r["voice"] for r in out["rows"] if "voice" in r]


class TestTheDeviceSpellsItsOwnCodes:
    def test_a_hyphenated_code_still_matches_the_sheet(self):
        # iOS reports en-US where the sheet had to write en_US. An exact compare
        # answered "no en_US voice on this device" to a phone holding 28 of them.
        assert _voices(_run(IPHONE))

    def test_only_the_declared_language_is_listed(self):
        # en-AU, en-GB and de-DE are voices, and none of them is what the column
        # asked to be read in.
        listed = " ".join(_voices(_run(IPHONE)))
        for other in ("Karen", "Daniel", "Anna", "Linh", "Tingting"):
            assert other not in listed


class TestWhatGoesInTheCell:
    def test_the_field_name_is_not_part_of_the_voice(self):
        # The device prints a ready-made tag, `voices=Apple_Ava_(Premium):Front`.
        # Copying that into a #config cell names a voice no device has.
        for voice in _voices(_run(IPHONE)):
            assert ":" not in voice
            assert voice.startswith("voices=Apple_")

    def test_a_voice_listed_twice_is_offered_once(self):
        # The Enhanced ones appear in a group of their own and again in place.
        voices = _voices(_run(IPHONE))
        assert len(voices) == len(set(voices))

    def test_the_good_voices_come_first(self):
        # The reason someone opens this block is that the default sounds like a
        # robot, and the answer is the Enhanced or Premium voice.
        voices = _voices(_run(IPHONE))
        assert "(Enhanced)" in voices[0] or "(Premium)" in voices[0]
        assert "(Enhanced)" in voices[1] or "(Premium)" in voices[1]


class TestOneButtonPerSpokenColumn:
    def test_every_column_of_that_language_is_playable(self):
        out = _run(
            IPHONE,
            columns=(("Word", "en_US", "hold"), ("Example", "en_US", "if it holds")),
        )
        for row in out["rows"]:
            if "voice" in row:
                assert row["buttons"] == ["▶ Word", "▶ Example"]

    def test_a_column_of_another_language_is_not_offered(self):
        out = _run(
            IPHONE,
            columns=(("Word", "en_US", "hold"), ("Reading", "zh_CN", "北京")),
        )
        for row in out["rows"]:
            if "voice" in row:
                assert row["buttons"] == ["▶ Word"]

    def test_the_desktop_gets_no_buttons_and_no_invitation(self):
        # QtWebEngine has no Web Speech API. A button that cannot play is worse
        # than no button, and the line above it would be an instruction to press
        # something that is not there.
        out = _run(IPHONE, speaks=False)
        assert _voices(out)
        for row in out["rows"]:
            assert row.get("buttons", []) == []
        assert "Tap" not in (out["note"] or "")


class TestWhenNothingMatches:
    def test_the_codes_the_device_reported_are_printed(self):
        # "Check the tts= language code" is not an answer when the sheet has no
        # way to know what the device calls it.
        out = _run(IPHONE, wanted="en_UK")
        assert not _voices(out)
        codes = " ".join(r["lang"] for r in out["rows"] if "lang" in r)
        assert "en-US" in codes and "en-GB" in codes and "en-AU" in codes

    def test_the_other_languages_are_left_out_of_that_list(self):
        # Fifty codes bury the three that are nearly right.
        out = _run(IPHONE, wanted="en_UK")
        codes = " ".join(r["lang"] for r in out["rows"] if "lang" in r)
        assert "zh-CN" not in codes and "de-DE" not in codes

    def test_every_code_is_offered_when_none_is_close(self):
        out = _run(IPHONE, wanted="ko_KR")
        codes = " ".join(r["lang"] for r in out["rows"] if "lang" in r)
        assert "zh-CN" in codes and "de-DE" in codes

    def test_a_device_with_no_voices_says_where_to_get_them(self):
        out = _run("Available TTS voices:", wanted="en_US")
        assert "No voice installed" in out["message"]

    def test_nothing_invites_a_tap_that_does_nothing(self):
        # The invitation is HTML on the card, so it outlived the list it was
        # written for and sat above an empty box.
        assert _run(IPHONE, wanted="en_UK")["note"] is None
        assert _run("Available TTS voices:")["note"] is None


class TestTheJokeVoicesAreNotOffered:
    """Nineteen of an iPhone's twenty-eight en_US voices are MacinTalk jokes.

    A bell, a cello, a robot, a whisper. Nobody learns a language in the voice of
    a cello, and a list where Zarvox outnumbers Samantha is one nobody reads to
    the end — which is the only thing this block asks of a reader.
    """

    def test_the_real_voices_are_what_shows(self):
        voices = " ".join(_voices(_run(IPHONE)))
        assert "Samantha" in voices and "Ava" in voices

    def test_a_joke_voice_is_not_in_the_list_at_all(self):
        voices = " ".join(_voices(_run(IPHONE)))
        for joke in ("Zarvox", "Bells", "Boing", "Trinoids", "Bad_News", "Albert"):
            assert joke not in voices

    def test_they_are_not_even_in_the_count(self):
        # The shared voices are counted; the jokes are not counted, not listed and
        # not reachable. The fixture holds six of them and two shared ones.
        rows = _run(IPHONE)["rows"]
        assert [r["more"] for r in rows if "more" in r] == ["+ 2 shared voices"]

    def test_pressing_the_count_does_not_bring_them_back(self):
        voices = " ".join(_voices(_run(IPHONE, reveal=True)))
        for joke in ("Zarvox", "Bells", "Boing", "Trinoids", "Bad_News", "Albert"):
            assert joke not in voices

    def test_a_language_of_nothing_but_jokes_keeps_them(self):
        # Dropping the lot would leave a heading with nothing under it, which
        # reads as a device with no voice rather than one with a silly voice.
        assert "Zarvox" in " ".join(_voices(_run(ONLY_JUNK)))

    def test_a_joke_name_from_another_engine_is_not_guessed_at(self):
        # The list is Apple's, matched whole. A voice that merely contains one of
        # the words is a voice, not a joke.
        dump = "{{tts en-US voices=Google_Bells_of_Dublin:Front}}"
        assert "Bells_of_Dublin" in " ".join(_voices(_run(dump)))


class TestALanguagesOwnVoicesComeFirst:
    """Eight of an iPhone's voices are one model in nine hats.

    Eddy, Flo, Grandma, Grandpa, Reed, Rocko, Sandy and Shelley are listed under
    every major language the device speaks, which is the tell: a voice recorded
    fourteen times is fourteen people, and nobody recorded Grandpa in Mandarin.
    They are character presets over one shared neural model, they sound like each
    other, and in front of the voice the language actually has they are the same
    clutter the joke set was. So they are counted rather than listed — and the
    count is derived from the device's own list, not from a list of names here.
    """

    def test_the_languages_own_voices_are_what_shows(self):
        voices = _voices(_run(IPHONE))
        assert [v for v in voices if "Samantha" in v]
        assert [v for v in voices if "Ava_(Premium)" in v]
        for shared in ("Eddy", "Grandma"):
            assert not [v for v in voices if shared in v]

    def test_the_shared_ones_are_counted(self):
        assert [r["more"] for r in _run(IPHONE)["rows"] if "more" in r] == [
            "+ 2 shared voices"
        ]

    def test_one_of_them_is_counted_in_the_singular(self):
        more = [r["more"] for r in _run(IPHONE, wanted="zh_CN")["rows"] if "more" in r]
        assert more == ["+ 1 shared voice"]

    def test_pressing_it_puts_them_back_under_their_language(self):
        rows = _run(IPHONE, reveal=True)["rows"]
        assert "Eddy" in " ".join(_voices(_run(IPHONE, reveal=True)))
        assert "lang" in rows[0] and all("lang" not in r for r in rows[1:])
        assert not [r for r in rows if "more" in r]

    def test_a_voice_of_one_language_only_is_never_counted_away(self):
        # Vietnamese has exactly one voice and shares it with nobody.
        out = _run(IPHONE, wanted="vi_VN")
        assert "Linh" in " ".join(_voices(out))
        assert not [r for r in out["rows"] if "more" in r]

    def test_a_language_that_shares_all_of_them_keeps_them(self):
        out = _run(ONLY_SHARED)
        assert len(_voices(out)) == 2
        assert not [r for r in out["rows"] if "more" in r]

    def test_a_device_of_one_language_shares_nothing(self):
        # Sharedness is evidence, and a device speaking one language offers none.
        dump = (
            "{{tts en-US voices=Apple_Samantha:Front}}\n"
            "{{tts en-US voices=Apple_Eddy:Front}}"
        )
        assert len(_voices(_run(dump))) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
