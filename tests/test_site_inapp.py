"""Opened inside a chat app: the page has to notice before Download does nothing.

A link to the site is usually tapped in Messenger or Telegram, whose built-in
browser cannot save a file. ``site/inapp.js`` recognises one from its user agent
and builds the Chrome intent link; both are run here in node.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parent.parent / "site"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")

CHROME_ANDROID = (
    "Mozilla/5.0 (Linux; Android 14; SM-A546E) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.6668.81 Mobile Safari/537.36"
)
SAFARI_IPHONE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
)
CHROME_IPHONE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) CriOS/129.0.6668.69 Mobile/15E148 Safari/604.1"
)
# A page added to the Home Screen: a real Safari that drops the token.
HOME_SCREEN = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Mobile/15E148"
)
DESKTOP = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
)

IN_APP = {
    "Telegram": [
        "Mozilla/5.0 (Linux; Android 14; Pixel 8 Build/AP2A.240905.003; wv) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/129.0.6668.81 "
        "Mobile Safari/537.36 Telegram-Android/11.2.2 (Google Pixel 8; Android 14; "
        "SDK 34; AVERAGE)",
    ],
    "Zalo": [
        "Mozilla/5.0 (Linux; Android 13; SM-A325F Build/TP1A.220624.014; wv) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/128.0.6613.146 "
        "Mobile Safari/537.36 Zalo android/12100734 ZaloTheme/light ZaloLanguage/vn",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Mobile/15E148 Zalo iOS/580 ZaloTheme/light "
        "ZaloLanguage/vn",
    ],
    "Messenger": [
        "Mozilla/5.0 (Linux; Android 14; Pixel 7 Build/AP2A.240805.005; wv) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/128.0.6613.127 "
        "Mobile Safari/537.36 [FB_IAB/Orca-Android;FBAV/475.0.0.43.109;]",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Mobile/15E148 [FBAN/MessengerForiOS;FBAV/470.0.0.40.109;"
        "FBBV/622347843;FBDV/iPhone15,2;FBMD/iPhone;FBSN/iOS;FBSV/17.5;FBSS/3;"
        "FBCR/;FBID/phone;FBLC/vi_VN;FBOP/5]",
    ],
    "Facebook": [
        "Mozilla/5.0 (Linux; Android 14; SM-S918B Build/UP1A.231005.007; wv) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/128.0.6613.127 "
        "Mobile Safari/537.36 [FB_IAB/FB4A;FBAV/480.0.0.53.79;]",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Mobile/15E148 [FBAN/FBIOS;FBAV/476.0.0.49.111;]",
    ],
    "Instagram": [
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Mobile/15E148 Instagram 345.0.0.32.97 (iPhone15,2; "
        "iOS 17_5; vi_VN; vi; scale=3.00; 1179x2556; 634108168)",
    ],
    "TikTok": [
        "Mozilla/5.0 (Linux; Android 13; 22101316G Build/TP1A.220624.014; wv) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/116.0.0.0 "
        "Mobile Safari/537.36 trill_360204 JsSdk/1.0 NetType/WIFI "
        "BytedanceWebview/d8a21c6",
    ],
    "Line": [
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Mobile/15E148 Safari Line/14.10.0",
    ],
}


def _run(expr):
    script = (
        f"import({json.dumps((SITE / 'inapp.js').as_uri())}).then((m) => "
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


def _which(ua, standalone=False):
    return _run(
        f"m.inAppBrowser({{ userAgent: {json.dumps(ua)}, "
        f"standalone: {json.dumps(standalone)} }})"
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "app,ua", [(app, ua) for app, uas in IN_APP.items() for ua in uas]
)
def test_each_chat_app_is_named(app, ua):
    assert _which(ua) == app


@pytest.mark.unit
@pytest.mark.parametrize("ua", [CHROME_ANDROID, SAFARI_IPHONE, CHROME_IPHONE, DESKTOP])
def test_a_real_browser_is_left_alone(ua):
    assert _which(ua) == ""


@pytest.mark.unit
def test_an_unnamed_webview_is_still_caught():
    android = CHROME_ANDROID.replace("SM-A546E)", "SM-A546E; wv)")
    assert _which(android) == "WebView"
    assert _which(HOME_SCREEN) == "WebView"


@pytest.mark.unit
def test_a_page_on_the_home_screen_is_not_a_webview():
    """The banner suggests Add to Home Screen; it must not then complain about it."""
    assert _which(HOME_SCREEN, standalone=True) == ""


@pytest.mark.unit
def test_the_intent_link_carries_the_fragment_in_the_query():
    href = "https://tannc28.github.io/sheetcards/sheet/#s=1.abc_-"
    intent = _run(f"m.chromeIntent({json.dumps(href)})")
    assert intent.startswith(
        "intent://tannc28.github.io/sheetcards/sheet/?sc_hash=s%3D1.abc_-#Intent;"
    )
    assert "scheme=https;" in intent and "package=com.android.chrome;" in intent
    assert intent.endswith(";end")
    # Only one '#': the intent's own. A second would be read as part of it.
    assert intent.count("#") == 1


@pytest.mark.unit
def test_the_fragment_is_put_back_on_arrival():
    out = _run(
        "(() => { let to = null;"
        " m.restoreHash({ search: '?a=1&sc_hash=s%3D1.abc', pathname: '/sheet/' },"
        " { replaceState: (_s, _t, url) => (to = url) }); return to; })()"
    )
    assert out == "/sheet/?a=1#s=1.abc"
