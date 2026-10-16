"""After the download: which device the page guesses, and what it tells it.

The .apkg is the whole product on a phone, and opening it is where people get
stuck, so Sheet to Anki opens on the instructions for the device in hand. The
guess lives in ``site/devices.js`` with no DOM, so it is run here in node.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parent.parent / "site"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")

ANDROID = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36"
)
IPHONE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
)
# iPadOS 13+ presents itself as desktop Safari on a Mac.
MAC_SAFARI = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Safari/605.1.15"
)
WINDOWS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
)


def _module(expr):
    script = (
        f"import({json.dumps((SITE / 'devices.js').as_uri())}).then((m) => "
        f"process.stdout.write(JSON.stringify({expr})))"
    )
    out = subprocess.run(
        [NODE, "--no-warnings", "-e", script],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return json.loads(out.stdout)


def _detect(ua, touch=0):
    return _module(
        f"m.detectDevice({{ userAgent: {json.dumps(ua)}, maxTouchPoints: {touch} }})"
    )


def _strings():
    """``{key: {en, vi}}`` for every plain or function entry, called with a file."""
    script = (
        f"import({json.dumps((SITE / 'i18n.js').as_uri())}).then((m) => {{"
        "const o = {}; for (const [k, v] of Object.entries(m.STRINGS)) {"
        " o[k] = {}; for (const l of ['en', 'vi'])"
        "  o[k][l] = typeof v[l] === 'function' ? v[l]('deck.apkg') : v[l]; }"
        " process.stdout.write(JSON.stringify(o)); })"
    )
    out = subprocess.run(
        [NODE, "--no-warnings", "-e", script],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return json.loads(out.stdout)


@pytest.mark.unit
class TestTheGuess:
    def test_android(self):
        assert _detect(ANDROID, 5) == "android"

    def test_iphone(self):
        assert _detect(IPHONE, 5) == "ios"

    def test_an_ipad_that_says_it_is_a_mac(self):
        assert _detect(MAC_SAFARI, 5) == "ios"

    def test_a_mac_is_a_computer(self):
        assert _detect(MAC_SAFARI, 0) == "desktop"

    def test_windows_is_a_computer(self):
        assert _detect(WINDOWS, 0) == "desktop"

    def test_nothing_known_is_a_computer(self):
        assert _module("m.detectDevice()") == "desktop"


@pytest.mark.unit
class TestTheInstructions:
    def test_every_device_has_a_tab_and_steps(self):
        devices = _module("m.DEVICES")
        assert devices == ["android", "ios", "desktop"]
        assert sorted(_module("Object.keys(m.DEVICE_LABELS)")) == sorted(devices)
        assert sorted(_module("Object.keys(m.DEVICE_STEPS)")) == sorted(devices)

    def test_every_key_exists_in_both_languages(self):
        strings = _strings()
        keys = _module(
            "[...Object.values(m.DEVICE_LABELS), ...Object.values(m.DEVICE_STEPS)].flat()"
        )
        for key in keys:
            assert key in strings, key
            assert strings[key]["en"] and strings[key]["vi"], key

    def test_the_first_step_names_the_file(self):
        """The file is the thing to look for in a downloads list."""
        strings = _strings()
        for steps in _module("Object.values(m.DEVICE_STEPS)"):
            for lang in ("en", "vi"):
                assert "deck.apkg" in strings[steps[0]][lang], (steps[0], lang)

    @pytest.mark.parametrize(
        "key, words",
        [
            ("instAndroid2", ["AnkiDroid"]),
            ("instAndroid3", ["Import"]),
            ("instIos2", ["Share", "AnkiMobile", "Copy to AnkiMobile"]),
            ("instIos3", ["Import"]),
            ("instDesktop2", ["File → Import…"]),
        ],
    )
    def test_the_vietnamese_keeps_the_apps_own_words(self, key, words):
        """The learner's phone shows these in English; so must the instructions."""
        vi = re.sub(r"<[^>]+>", "", _strings()[key]["vi"])
        for word in words:
            assert word in vi, (key, word)
