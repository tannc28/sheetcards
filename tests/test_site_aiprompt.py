"""The landing page's AI prompt (``site/aiprompt.js``), run in node.

The prompt names the guide by the address the page was served from, so moving
the site to another domain needs no edit; nothing here may name a domain.
"""

import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import unquote

import pytest

SITE = Path(__file__).resolve().parent.parent / "site"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")


def _run(expr):
    script = (
        # setLang marks <html lang>; nothing else of a page is needed.
        "globalThis.document = { documentElement: {} };"
        f"Promise.all([import({json.dumps((SITE / 'aiprompt.js').as_uri())}),"
        f" import({json.dumps((SITE / 'i18n.js').as_uri())})])"
        f".then(([m, i]) => process.stdout.write(JSON.stringify({expr})))"
    )
    out = subprocess.run(
        [NODE, "--no-warnings", "-e", script],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return json.loads(out.stdout)


@pytest.mark.parametrize(
    "root",
    [
        "https://tannc28.github.io/sheetcards/",
        "https://cards.example.org/",
        "http://localhost:8123/",
    ],
)
@pytest.mark.parametrize("lang", ["vi", "en"])
def test_the_prompt_names_the_guide_under_the_given_root(root, lang):
    got = _run(
        f"(i.setLang({json.dumps(lang)}, false),"
        f" m.promptFor((u) => i.t('aiPrompt', u), {json.dumps(root)}))"
    )
    assert f"{root}ai.md" in got["text"]
    assert "<" not in got["text"] and "&amp;" not in got["text"]
    # The slots the reader is asked to change are marked, and survive as text.
    slots = re.findall(r'<span class="ai-slot">(\[[^]]+\])</span>', got["html"])
    assert len(slots) >= 4
    for slot in slots:
        assert slot in got["text"]


def test_the_quick_open_links_carry_the_prompt():
    text = "Đọc hướng dẫn tại https://x.example/ai.md: [30] từ & ví dụ?"
    links = _run(f"m.chatLinks({json.dumps(text)})")
    for name in ("chatgpt", "claude"):
        assert unquote(links[name].split("?q=", 1)[1]) == text
    assert links["chatgpt"].startswith("https://chatgpt.com/?q=")
    assert links["claude"].startswith("https://claude.ai/new?q=")
    assert links["gemini"] == "https://gemini.google.com/app"


def test_the_landing_page_builds_the_prompt_from_its_own_root():
    home = (SITE / "home.js").read_text(encoding="utf-8")
    assert re.search(r"promptFor\([^;]*\bROOT\)", home)
    for page in ("index.html", "home.js", "aiprompt.js"):
        text = (SITE / page).read_text(encoding="utf-8")
        assert "tannc28.github.io" not in text, page
