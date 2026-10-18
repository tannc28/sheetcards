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


@pytest.mark.parametrize("key", ["aiPrompt", "aiPromptTable"])
@pytest.mark.parametrize("lang", ["vi", "en"])
def test_the_prompt_teaches_the_format_with_its_slots_marked(key, lang):
    got = _run(
        f"(i.setLang({json.dumps(lang)}, false),"
        f" m.promptFor((u) => i.t({json.dumps(key)}, u), 'https://x.example/deep/'))"
    )
    assert "<" not in got["text"] and "&amp;" not in got["text"]
    # The full guide, built from the root it was given, as the prompt's last words,
    # for an assistant that can open it; the rules above it are for one that cannot.
    assert got["text"].rstrip(")").endswith("https://x.example/deep/ai.md")
    assert got["text"].count("https://x.example/deep/ai.md") == 1
    assert "#config name=" in got["text"]
    # The slots the reader is asked to change are marked, and survive as text.
    slots = re.findall(r'<span class="ai-slot">([^<]+)</span>', got["html"])
    assert len(slots) >= 5
    for slot in slots:
        assert slot in got["text"]
    if key == "aiPrompt":
        assert (
            "Word [tts=en_US; bold] | IPA [color=muted] | Meaning | Example [italic]"
            in got["text"]
        )
    else:
        assert "Word | IPA | Meaning | Example" in got["text"]


def test_a_text_prompt_answer_reads_as_the_deck_it_describes():
    """What the text prompt asks for, written out, is a set with no warnings."""
    from src.tsv_model import build_remote_deck_from_tsv
    from src.tsv_model import parse_tsv_data

    answer = (
        "#config name=Du lịch B1\n"
        "Word [tts=en_US; bold] | IPA [color=muted] | Meaning | Example [italic]\n"
        "airport | /ˈer.pɔːrt/ | sân bay | We got to the airport early.\n"
    )
    script = (
        f"Promise.all([import({json.dumps((SITE / 'importformats.js').as_uri())}),"
        f" import({json.dumps((SITE / 'sharelink.js').as_uri())})]).then(([m, s]) => {{"
        f"const r = m.readPaste({json.dumps(answer)});"
        "process.stdout.write(JSON.stringify(s.toTsv(m.pasteGrid({name: '', rows: r.rows,"
        " header: r.header, cells: r.cells, deck: r.deck}))));})"
    )
    out = subprocess.run(
        [NODE, "--no-warnings", "-e", script],
        capture_output=True,
        text=True,
        check=True,
    )
    deck = build_remote_deck_from_tsv(parse_tsv_data(json.loads(out.stdout)), "")
    assert deck.sheet_config.warnings == []
    assert deck.sheet_config.deck_name == "Du lịch B1"


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
