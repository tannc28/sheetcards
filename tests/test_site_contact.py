"""The contact page's feedback form: open when configured, a notice when not.

The form posts to the owner's Apps Script web app (``tools/feedback/Code.gs``)
with a Google ID token. Its two settings live in ``site/feedback-config.js`` and
are both public — a client ID and a URL — so nothing here may look like a
secret. The rules (``site/feedback.js``) have no DOM and are run in node; the
real Google sign-in cannot run headless and is not tested.
"""

import base64
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parent.parent / "site"
NODE = shutil.which("node")

CLIENT_ID = "1234567890-abcdefghijklmnop.apps.googleusercontent.com"
ENDPOINT = "https://script.google.com/macros/s/AKfycbx_Example-123/exec"


def _text(name):
    return (SITE / name).read_text(encoding="utf-8")


def _run(body):
    """Runs ``body`` in node with feedback.js imported as ``m``; prints JSON."""
    if not NODE:
        pytest.skip("node is not installed")
    script = (
        f"import({json.dumps((SITE / 'feedback.js').as_uri())}).then((m) => {{"
        f"const out = (() => {{ {body} }})();"
        "process.stdout.write(JSON.stringify(out)); })"
    )
    done = subprocess.run(
        [NODE, "--no-warnings", "-e", script],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(done.stdout)


def _jwt(claims):
    part = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    return f"eyJhbGciOiJSUzI1NiJ9.{part}.signature"


@pytest.mark.unit
def test_the_shipped_config_is_empty_and_holds_only_two_public_values():
    text = _text("feedback-config.js")
    found = re.search(r"export const FEEDBACK = \{([^}]*)\};", text)
    assert found, "feedback-config.js must export FEEDBACK"
    keys = re.findall(r"(\w+):", found.group(1))
    assert keys == ["clientId", "endpoint"]
    code = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith(("*", "/"))
    )
    for word in ("secret", "apikey", "api_key", "password", "token"):
        assert word not in code.lower(), f"feedback-config.js mentions {word}"


@pytest.mark.unit
@pytest.mark.parametrize(
    ("config", "state"),
    [
        ({"clientId": "", "endpoint": ""}, "closed"),
        ({"clientId": CLIENT_ID, "endpoint": ""}, "closed"),
        ({"clientId": "", "endpoint": ENDPOINT}, "closed"),
        ({"clientId": "PASTE-YOUR-CLIENT-ID", "endpoint": ENDPOINT}, "closed"),
        ({"clientId": CLIENT_ID, "endpoint": "https://example.com/exec"}, "closed"),
        ({"clientId": CLIENT_ID, "endpoint": ENDPOINT}, "open"),
        ({"clientId": f" {CLIENT_ID} ", "endpoint": f"{ENDPOINT}\n"}, "open"),
    ],
)
def test_the_form_opens_only_when_both_values_are_set(config, state):
    assert _run(f"return m.formState({json.dumps(config)});") == state


@pytest.mark.unit
def test_the_shipped_config_shows_the_notice():
    if not NODE:
        pytest.skip("node is not installed")
    script = (
        f"Promise.all([import({json.dumps((SITE / 'feedback.js').as_uri())}),"
        f"import({json.dumps((SITE / 'feedback-config.js').as_uri())})])"
        ".then(([m, c]) => process.stdout.write(m.formState(c.FEEDBACK)))"
    )
    out = subprocess.run(
        [NODE, "--no-warnings", "-e", script], capture_output=True, text=True
    )
    assert out.returncode == 0, out.stderr
    # Flip this when the owner fills the two values in.
    assert out.stdout == "closed"


@pytest.mark.unit
def test_the_page_has_both_states_and_loads_google_only_when_open():
    page = _text("contact.html")
    assert 'id="fb-closed"' in page and 'id="fb-open" hidden' in page
    for target in ("github.com/tannc28/sheetcards", "/issues", "facebook.com/tannc28"):
        assert target in page, target
    # The notice names the two ways that always work.
    notice = re.search(r'id="fb-closed"[^>]*>(.*?)</p>', page, re.S).group(1)
    assert "GitHub" in notice and "Facebook" in notice
    script = _text("contact.js")
    branch = script.split('if (formState(FEEDBACK) === "open") {', 1)
    assert len(branch) == 2, "contact.js must gate the form on formState"
    assert (
        "loadGsi()" in branch[1]
        and "loadGsi()" not in branch[0].split("function loadGsi", 1)[0]
    )
    # Google's script is this page's alone.
    for path in SITE.iterdir():
        if path.suffix in (".html", ".js") and path.name != "contact.js":
            assert "accounts.google.com/gsi" not in _text(path.name), path.name


@pytest.mark.unit
def test_the_token_is_never_stored():
    for name in ("contact.js", "feedback.js"):
        text = _text(name)
        assert "localStorage" not in text and "sessionStorage" not in text, name


@pytest.mark.unit
def test_the_post_is_a_simple_request():
    """text/plain, so the browser sends no preflight Apps Script cannot answer."""
    assert '"Content-Type": "text/plain;charset=utf-8"' in _text("contact.js")


@pytest.mark.unit
def test_a_token_is_read_for_display():
    token = _jwt({"email": "an@example.com", "name": "Ân Nguyễn", "exp": 2000000000})
    got = _run(f"return m.readToken({json.dumps(token)});")
    assert got == {"email": "an@example.com", "name": "Ân Nguyễn", "exp": 2000000000}
    assert _run('return m.readToken("not.a-token");') is None
    assert _run(f"return m.readToken({json.dumps(_jwt({'name': 'x'}))});") is None
    assert _run("return m.expired({exp: 1}, 5000);") is True
    assert _run("return m.expired({exp: 2000000000}, 0);") is False


@pytest.mark.unit
def test_where_the_reader_came_from():
    origin = "https://tannc28.github.io"
    cases = [
        ("?from=create", "", "create"),
        ("?from=docs/en/faq", f"{origin}/sheetcards/x.html", "docs/en/faq"),
        ("?from=<script>", "", "script"),
        (
            "",
            f"{origin}/sheetcards/sheet/?url=secret#s=1",
            "/sheetcards/sheet/",
        ),
        ("", "https://elsewhere.example/page", ""),
        ("", "", ""),
    ]
    for search, referrer, want in cases:
        got = _run(
            f"return m.cameFrom({json.dumps(search)}, {json.dumps(referrer)}, "
            f"{json.dumps(origin)});"
        )
        assert got == want, (search, referrer)


@pytest.mark.unit
def test_screenshots_are_checked_before_sending():
    got = _run(
        "return ["
        "m.imageProblem({type: 'image/png', size: 1000}),"
        "m.imageProblem({type: 'image/svg+xml', size: 10}),"
        "m.imageProblem({type: 'image/jpeg', size: 4 * 1024 * 1024 + 1}),"
        "m.imageProblem(null)];"
    )
    assert got == ["", "fbErrImageType", "fbErrImageSize", ""]
    # The same list Code.gs accepts.
    gs = (SITE.parent / "tools" / "feedback" / "Code.gs").read_text(encoding="utf-8")
    listed = re.search(r"const IMAGE_TYPES = \[([^\]]*)\]", gs).group(1)
    types = re.findall(r'"([^"]+)"', listed)
    assert _run("return m.IMAGE_TYPES;") == types
    assert "4 * 1024 * 1024" in gs and _run("return m.MAX_IMAGE_BYTES;") == 4 << 20


@pytest.mark.unit
def test_the_payload_matches_the_web_app():
    got = _run(
        "return m.payload({idToken: 't', kind: 'nope', message: 'hi', "
        "image: {data: 'AAA', type: 'image/png', name: 'a.png', url: 'data:'}, "
        "device: 'ios', sheetUrl: ' https://x ', page: 'create', userAgent: 'UA', "
        "lang: 'vi'});"
    )
    assert got == {
        "idToken": "t",
        "kind": "other",
        "message": "hi",
        "device": "ios",
        "sheetUrl": "https://x",
        "page": "create",
        "userAgent": "UA",
        "lang": "vi",
        "image": {"data": "AAA", "type": "image/png", "name": "a.png"},
    }
    assert "image" not in _run("return m.payload({idToken: 't', message: 'x'});")


@pytest.mark.unit
def test_every_answer_has_a_message():
    got = _run(
        "return ['auth', 'rate', 'empty', 'image', 'server', 'whatever']"
        ".map((error) => m.readReply({ok: false, error}))"
        ".concat([m.readReply({ok: true}), m.readReply(null), m.NETWORK]);"
    )
    keys = [g.get("key") for g in got]
    assert keys == [
        "fbErrAuth",
        "fbErrRate",
        "fbErrEmpty",
        "fbErrImage",
        "fbErrServer",
        "fbErrServer",
        None,
        "fbErrServer",
        "fbErrNetwork",
    ]
    assert got[0]["signIn"] is True and got[1]["signIn"] is False
    assert got[6] == {"ok": True}
    # Every error Code.gs can return is one feedback.js knows.
    gs = (SITE.parent / "tools" / "feedback" / "Code.gs").read_text(encoding="utf-8")
    for code in set(re.findall(r'error: "(\w+)"', gs)):
        assert f"{code}:" in _text("feedback.js"), code
