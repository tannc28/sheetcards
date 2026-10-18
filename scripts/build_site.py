#!/usr/bin/env python3
"""Assembles the website into build/site/.

Four kinds of page: the landing page (``site/index.html``), Sheet to Anki
(``site/create.html``, served at ``/create/``), Create sheet (``site/sheet.html``,
at ``/sheet/``), the contact page (``site/contact.html``, at ``/contact/``) and the
documentation, written as Markdown under ``docs/site/`` (Vietnamese, served at
``/docs/``, a page at ``/docs/<name>/``) and ``docs/site/en/`` (English, at
``/docs/en/``) and converted here.

Every page is a folder, so no address ends in ``.html``. The pages are written
in ``site/`` as if they sat at the site's root, and moved down a folder here
(``relocate``); every address a page used to have — ``create.html``,
``preview.html``, ``editor.html``, ``docs/faq.html`` — is kept as a small page
that forwards to the new one with its query and fragment (``site/_redirect.html``).
``player.html`` is the exception: its address is written into card templates
people have already imported into Anki (``card_layout.EMBED_PROXY``), so it never
moves.

The site is static, but it is not self-contained in the repository on purpose:
the Python it runs in the browser is copied straight out of ``src/`` at build
time rather than kept as a second copy under ``site/``. A checked-in copy would
be a fork of the add-on that nobody would notice going stale. The landing page's
demo cards are rendered by those same modules here, at build time, so the page
shows the add-on's real card templates without loading Pyodide.

Building the docs needs the ``markdown`` package (the ``dev`` extra). The add-on
itself does not: this script is the only thing that imports it.

Usage:
    python scripts/build_site.py            # build into build/site
    python scripts/build_site.py --serve    # build, then serve it on :8000
"""

import argparse
import html
import json
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"
SITE = REPO / "site"
DOCS = REPO / "docs" / "site"
OUT = REPO / "build" / "site"
EXAMPLES = REPO / "examples" / "sheetcards-examples.xlsx"

# The file a learner downloads from the landing page to start from: one sheet,
# four columns, a settings row and three words — the smallest sheet that already
# makes a good card. Served beside the example workbook, which is copied in too,
# so both downloads are same-origin files rather than GitHub pages.
STARTER_NAME = "sheetcards-mau.xlsx"
STARTER = {
    "Vocabulary": [
        ["ID", "Word", "Meaning", "Example"],
        [
            "#config",
            "size=44; bold; tts=en_US",
            "side=back; size=22",
            "side=back; color=muted; italic; tts=en_US",
        ],
        ["w01", "hello", "xin chào", "Hello, how are you today?"],
        ["w02", "thank you", "cảm ơn", "Thank you for your help."],
        ["w03", "goodbye", "tạm biệt", "Goodbye, see you tomorrow."],
    ],
}

# The documentation's table of contents: ({language: group}, [page, ...]). A
# page is the name of a Markdown file, written once per language, and its title
# is that file's first heading. Declared here rather than found, because order is
# information — the build refuses a page missing from this list, or from either
# language, and a name with no file.
DOC_GROUPS = [
    ({"vi": "Bắt đầu", "en": "Start"}, ["index", "examples", "ai"]),
    (
        {"vi": "Viết sheet", "en": "Write a sheet"},
        ["columns", "settings-row", "card-types", "text", "media", "tts"],
    ),
    ({"vi": "Trong Anki", "en": "In Anki"}, ["menu", "syncing", "sources"]),
    ({"vi": "Trợ giúp", "en": "Help"}, ["faq", "developers"]),
]

# The pages that are folders: written as site/<file>, served at /<folder>/ (the
# folder's index.html), with the old address forwarding to it.
PAGES = {"create.html": "create", "sheet.html": "sheet", "contact.html": "contact"}

# Addresses that were pages once and forward to one now, as {old: new}, each
# relative to the site's root. A moved page's own old address is added to these.
REDIRECTS = {"preview.html": "create/", "editor.html": "sheet/"}

# What each forwarding page calls the page it forwards to.
PAGE_TITLES = {
    "create/": "SheetCards — Sheet to Anki",
    "sheet/": "SheetCards — Tạo Sheet",
    "contact/": "SheetCards — Liên hệ & góp ý",
}

# The docs in each language: the folder under docs/site/ it is written in, which
# is also the folder under /docs/ it is served from. Vietnamese is the docs'
# front door, because most readers are Vietnamese; every page links its twin.
DOC_LANGS = {"vi": "", "en": "en"}

# The words the docs' own chrome says around a page, per language.
DOC_CHROME = {
    "vi": {
        "nav": "Docs",
        "contents": "Mục lục",
        "onpage": "Trên trang này",
        "pages": "Các trang khác",
        "previous": "Trang trước",
        "next": "Trang sau",
        "permalink": "Link tới mục này",
        "edit": "Sửa trang này trên GitHub",
        "twin": "Read this page in English",
        "contact": "Liên hệ &amp; góp ý",
    },
    "en": {
        "nav": "Documentation",
        "contents": "Contents",
        "onpage": "On this page",
        "pages": "More pages",
        "previous": "Previous",
        "next": "Next",
        "permalink": "Link to this section",
        "edit": "Edit this page on GitHub",
        "twin": "Đọc trang này bằng tiếng Việt",
        "contact": "Contact &amp; feedback",
    },
}

# The landing page's demo: (sheet in the example workbook, row ID, i18n key of
# its label, theme). Real rows, rendered with the real templates — the page
# claims the sheet becomes this card, so it had better be the card the add-on
# makes. Each card wears a different theme to show there is more than one; the
# theme is written into the settings cell the strip shows, so the sheet on the
# left still says exactly what made the card on the right.
HOME_EXAMPLES = [
    ("12 Chinese drawing (viết tay)", "d01", "demoWriting", "momiji"),
    ("15 Theme + subdeck (màu, tầng)", "n01", "demoEnglish", "paper"),
    ("13 Furigana (phiên âm kanji)", "f01", "demoJapanese", "sakura"),
    ("06 Cloze (điền chỗ trống)", "z01", "demoCloze", "matcha"),
]


# Create sheet's starting points. There are two, because everything else a
# learner asked for was Basic with the columns renamed: a blank Front / Back,
# and a vocabulary sheet whose settings row is made from two choices — the
# language of the words and which of Word and Example are read aloud. The labels
# live in site/sheet.js, so they are translated with the rest of the page.
# Basic's two columns are named in the page's language when the sheet is made,
# and keep that name after: by then they are field names. ID is reserved.
BASIC_TEMPLATES = {
    "vi": [
        ["ID", "Mặt trước", "Mặt sau"],
        ["#config", "size=40", "size=24"],
        ["w01", "", ""],
    ],
    "en": [
        ["ID", "Front", "Back"],
        ["#config", "size=40", "size=24"],
        ["w01", "", ""],
    ],
}

# Custom: the whole editor, opened on a sheet that shows what a settings row
# can do — a few keys per column, each one visible on the card. The pictures
# and recordings are the example workbook's, already checked to load.
_COMMONS = "https://upload.wikimedia.org/wikipedia/commons/thumb"
CUSTOM_TEMPLATE = [
    ["ID", "SUBDECK 1", "TAGS", "Picture", "Word", "IPA", "Meaning", "Example"],
    [
        "#config theme=sakura",
        "",
        "",
        "image; size=200",
        "side=back; size=44; bold; color=accent; type; tts=en_US; voices=Apple_Samantha",
        "side=back; size=20; color=muted",
        "side=back; size=24; label=Nghĩa",
        "side=back; size=16; italic; hint; tts=en_US; voices=Apple_Samantha",
    ],
    [
        "w01",
        "Animals",
        "animals, a1",
        f"{_COMMONS}/4/4d/Cat_November_2010-1a.jpg/500px-Cat_November_2010-1a.jpg",
        "cat",
        "/kæt/",
        "con mèo",
        "The cat is asleep on the chair.",
    ],
    [
        "w02",
        "Animals",
        "animals, a1",
        f"{_COMMONS}/1/17/Tiger_in_Ranthambhore.jpg/500px-Tiger_in_Ranthambhore.jpg",
        "tiger",
        "/ˈtaɪ.ɡɚ/",
        "con hổ",
        "A tiger hunts alone.",
    ],
    [
        "w03",
        "Food and drink",
        "food, a1",
        f"{_COMMONS}/1/15/Red_Apple.jpg/500px-Red_Apple.jpg",
        "apple",
        "/ˈæp.əl/",
        "quả táo",
        "An apple a day is an old English saying.",
    ],
]

# Writing Chinese: the meaning and pinyin ask, the learner writes the character
# stroke by stroke in the box (draw, on the question), and the answer animates
# the strokes, shows the character large and reads it and an example aloud. The
# same layout as the example workbook's "12 Chinese drawing", minus its deck and
# tag columns, with the Chinese font and the iPhone's own Mandarin voice.
HANZI_TEMPLATE = [
    ["ID", "Meaning", "Pinyin", "Draw", "Character", "Example"],
    [
        "#config",
        "size=24; color=muted; label=Viết chữ có nghĩa",
        "side=front; size=40; color=accent",
        "side=front; draw; size=260",
        "side=back; size=72; font=sc; tts=zh_CN; voices=Apple_Tingting",
        "side=back; size=20; font=sc; tts=zh_CN; voices=Apple_Tingting; speed=0.8",
    ],
    ["d01", "tôi", "wǒ", "我", "我", "我是学生。"],
    ["d02", "bạn", "nǐ", "你", "你", "你好吗？"],
    ["d03", "tốt; khỏe", "hǎo", "好", "好", "今天天气很好。"],
]

# The same sheet for the English page: the label and the meanings are the
# learner's language, which the Vietnamese copy is not.
HANZI_TEMPLATE_EN = [
    HANZI_TEMPLATE[0],
    [HANZI_TEMPLATE[1][0], "size=24; color=muted; label=Write the character for"]
    + HANZI_TEMPLATE[1][2:],
    ["d01", "I; me", "wǒ", "我", "我", "我是学生。"],
    ["d02", "you", "nǐ", "你", "你", "你好吗？"],
    ["d03", "good; well", "hǎo", "好", "好", "今天天气很好。"],
]

# Japanese with furigana: the reading written in brackets after the kanji and
# drawn as ruby over it, as in the example workbook's "13 Furigana". No voice is
# named — the iPhone this was checked against has no ja_JP voice built in.
KANJI_TEMPLATE = [
    ["ID", "Japanese", "Meaning", "Example", "Note"],
    [
        "#config",
        "size=40; furigana; font=jp; tts=ja_JP",
        "side=back; size=24",
        "side=back; size=20; furigana; font=jp; tts=ja_JP",
        "side=back; size=14; color=muted; hint",
    ],
    [
        "j01",
        "日本語[にほんご]",
        "tiếng Nhật",
        " 私[わたし]は 日本語[にほんご]を 勉強[べんきょう]しています。",
        "Viết cách đọc trong ngoặc vuông ngay sau chữ kanji.",
    ],
    [
        "j02",
        "図書館[としょかん]",
        "thư viện",
        " 図書館[としょかん]で 本[ほん]を 読[よ]みます。",
        "Một dấu cách trước chữ kanji tách nó khỏi chữ đứng trước.",
    ],
    ["j03", "先生[せんせい]", "giáo viên", " 先生[せんせい]は 優[やさ]しいです。", ""],
]
KANJI_TEMPLATE_EN = [
    KANJI_TEMPLATE[0],
    KANJI_TEMPLATE[1],
    [
        "j01",
        "日本語[にほんご]",
        "Japanese (the language)",
        " 私[わたし]は 日本語[にほんご]を 勉強[べんきょう]しています。",
        "Write the reading in square brackets right after the kanji.",
    ],
    [
        "j02",
        "図書館[としょかん]",
        "library",
        " 図書館[としょかん]で 本[ほん]を 読[よ]みます。",
        "A space before a kanji keeps it apart from the word before it.",
    ],
    ["j03", "先生[せんせい]", "teacher", " 先生[せんせい]は 優[やさ]しいです。", ""],
]

VOCAB_HEADERS = ["ID", "Word", "Phiên âm", "Meaning", "Example", "Note"]

# One row per language the vocabulary template offers, in the order offered:
# (tts code, the language named in itself, iPhone voice or None, font or None,
# three words as Word / Phiên âm / Meaning / Example / Note).
#
# A voice is named only where tests/test_card_layout_voices.py's dump of a real
# iPhone (iOS 26, AnkiMobile) has one that is not a download: Samantha, Daniel,
# Tingting, Anna and Linh. voices= is a preference, so on Android and desktop
# Anki falls back to any voice of the language. That iPhone had no ja_JP or
# ko_KR voice at all, and fr_FR and es_ES are not in it either — naming one there
# would be naming a voice that is not on the phone, so those name none and the
# page says where to download one.
VOCAB_LANGUAGES = [
    (
        "en_US",
        "English (US)",
        "Apple_Samantha",
        None,
        [
            ["journey", "/ˈdʒɝː.ni/", "chuyến đi", "The journey took three hours.", ""],
            [
                "borrow",
                "/ˈbɑːr.oʊ/",
                "mượn",
                "Can I borrow your pen?",
                "borrow from: mượn của ai; lend to: cho ai mượn",
            ],
            [
                "improve",
                "/ɪmˈpruːv/",
                "cải thiện",
                "Reading every day will improve your English.",
                "",
            ],
        ],
    ),
    (
        "en_GB",
        "English (UK)",
        "Apple_Daniel",
        None,
        [
            ["journey", "/ˈdʒɜː.ni/", "chuyến đi", "The journey took three hours.", ""],
            [
                "borrow",
                "/ˈbɒr.əʊ/",
                "mượn",
                "Can I borrow your pen?",
                "borrow from: mượn của ai; lend to: cho ai mượn",
            ],
            [
                "queue",
                "/kjuː/",
                "hàng người xếp hàng",
                "We waited in a queue for an hour.",
                "Tiếng Mỹ: line",
            ],
        ],
    ),
    (
        "zh_CN",
        "中文 (简体)",
        "Apple_Tingting",
        "sc",
        [
            ["学习", "xuéxí", "học", "我每天学习中文。", ""],
            ["朋友", "péngyou", "bạn bè", "他是我的好朋友。", ""],
            ["喜欢", "xǐhuan", "thích", "我喜欢喝茶。", "喜欢 + động từ: thích làm gì"],
        ],
    ),
    (
        "ja_JP",
        "日本語",
        None,
        "jp",
        [
            [
                "勉強",
                "べんきょう (benkyō)",
                "học",
                "毎日日本語を勉強します。",
                "勉強する: học",
            ],
            ["友達", "ともだち (tomodachi)", "bạn bè", "友達と映画を見ました。", ""],
            [
                "食べる",
                "たべる (taberu)",
                "ăn",
                "朝ご飯を食べましたか。",
                "Động từ nhóm 2",
            ],
        ],
    ),
    (
        "ko_KR",
        "한국어",
        None,
        "kr",
        [
            ["공부하다", "gongbuhada", "học", "저는 매일 한국어를 공부해요.", ""],
            ["친구", "chingu", "bạn bè", "친구랑 영화를 봤어요.", ""],
            [
                "맛있다",
                "masitda",
                "ngon",
                "이 김치는 정말 맛있어요.",
                "Trái nghĩa: 맛없다",
            ],
        ],
    ),
    (
        "fr_FR",
        "Français",
        None,
        None,
        [
            ["bonjour", "/bɔ̃.ʒuʁ/", "xin chào", "Bonjour, comment allez-vous ?", ""],
            ["merci", "/mɛʁ.si/", "cảm ơn", "Merci beaucoup pour votre aide.", ""],
            [
                "la maison",
                "/la mɛ.zɔ̃/",
                "ngôi nhà",
                "La maison est très grande.",
                "Danh từ giống cái",
            ],
        ],
    ),
    (
        "de_DE",
        "Deutsch",
        "Apple_Anna",
        None,
        [
            [
                "das Haus",
                "/haʊ̯s/",
                "ngôi nhà",
                "Das Haus ist sehr groß.",
                "Số nhiều: die Häuser",
            ],
            ["danke", "/ˈdaŋ.kə/", "cảm ơn", "Danke für deine Hilfe.", ""],
            ["lernen", "/ˈlɛʁ.nən/", "học", "Ich lerne jeden Tag Deutsch.", ""],
        ],
    ),
    (
        "es_ES",
        "Español",
        None,
        None,
        [
            ["hola", "/ˈo.la/", "xin chào", "Hola, ¿cómo estás?", ""],
            ["gracias", "/ˈɡɾa.θjas/", "cảm ơn", "Muchas gracias por tu ayuda.", ""],
            [
                "la casa",
                "/ˈka.sa/",
                "ngôi nhà",
                "Mi casa es tu casa.",
                "Danh từ giống cái",
            ],
        ],
    ),
    (
        "vi_VN",
        "Tiếng Việt",
        "Apple_Linh",
        None,
        [
            [
                "kiên nhẫn",
                "",
                "chờ đợi, chịu đựng mà không nản",
                "Học ngoại ngữ cần kiên nhẫn.",
                "Hán Việt: 堅忍",
            ],
            [
                "hạnh phúc",
                "",
                "vui sướng vì được như ý",
                "Gia đình tôi sống rất hạnh phúc.",
                "Hán Việt: 幸福",
            ],
            [
                "thành công",
                "",
                "đạt được kết quả mong muốn",
                "Chúc bạn thành công!",
                "Hán Việt: 成功",
            ],
        ],
    ),
]


def _spoken(base, code, voice, font, speak):
    """One column's cell, with the language's font and, if asked, its voice."""
    parts = [base]
    if font:
        parts.append(f"font={font}")
    if speak:
        parts.append(f"tts={code}" + (f"; voices={voice}" if voice else ""))
    return "; ".join(parts)


def vocab_config(
    code, voice, font, speak_word, speak_example, *, theme=None, typed=False
):
    """The vocabulary template's settings row for one set of choices.

    ``theme`` dresses the same card in one of the listed themes; ``typed`` turns
    it round — Meaning asks, and the Word is typed in (accents forgiven) before
    it is shown and heard.
    """
    word = "side=back; size=44; bold; type=nc" if typed else "size=44; bold"
    meaning = "side=front; size=32" if typed else "size=26"
    return [
        "#config" + (f" theme={theme}" if theme else ""),
        _spoken(word, code, voice, font, speak_word),
        "size=20; color=accent",
        meaning,
        _spoken("size=18; color=muted; italic", code, voice, font, speak_example),
        "size=14; color=muted",
    ]


def vocab_rows(language, speak_word=True, speak_example=True, **shape):
    code, _label, voice, font, words = language
    config = vocab_config(code, voice, font, speak_word, speak_example, **shape)
    rows = [VOCAB_HEADERS, config]
    rows += [[f"w{n:02}", *word] for n, word in enumerate(words, start=1)]
    return rows


def reverse_rows(language, speak_word=True, _speak_example=False):
    """The vocabulary card and its reverse: Word asks on card 1, and Phiên âm +
    Meaning ask on card 2. Example and Note are left out, because whatever is on
    the back of card 1 is the *question* of card 2, and an example sentence
    holding the word gives the answer away."""
    rows = vocab_rows(language, speak_word, False)
    rows = [row[:4] for row in rows]
    rows[1][0] = "#config reverse"
    return rows


# The pictures are the example workbook's (16 Picture words), already checked to
# load; the words are the same three in each language the vocabulary template
# offers, so the language step works here too.
PICTURES = [
    f"{_COMMONS}/4/4d/Cat_November_2010-1a.jpg/500px-Cat_November_2010-1a.jpg",
    f"{_COMMONS}/1/17/Tiger_in_Ranthambhore.jpg/500px-Tiger_in_Ranthambhore.jpg",
    f"{_COMMONS}/1/15/Red_Apple.jpg/500px-Red_Apple.jpg",
]
_PICTURE_MEANINGS = ["con mèo", "con hổ", "quả táo"]
PICTURE_WORDS = {
    "en_US": (["cat", "tiger", "apple"], _PICTURE_MEANINGS),
    "en_GB": (["cat", "tiger", "apple"], _PICTURE_MEANINGS),
    "zh_CN": (["猫", "老虎", "苹果"], _PICTURE_MEANINGS),
    "ja_JP": (["猫", "虎", "りんご"], _PICTURE_MEANINGS),
    "ko_KR": (["고양이", "호랑이", "사과"], _PICTURE_MEANINGS),
    "fr_FR": (["le chat", "le tigre", "la pomme"], _PICTURE_MEANINGS),
    "de_DE": (["die Katze", "der Tiger", "der Apfel"], _PICTURE_MEANINGS),
    "es_ES": (["el gato", "el tigre", "la manzana"], _PICTURE_MEANINGS),
    "vi_VN": (
        ["con mèo", "con hổ", "quả táo"],
        [
            "thú nhỏ nuôi trong nhà, hay bắt chuột",
            "thú dữ lớn, lông vằn",
            "quả tròn, vỏ đỏ hoặc xanh, vị ngọt",
        ],
    ),
}
PICTURE_HEADERS = ["ID", "Word", "Picture", "Meaning"]


def picture_rows(language, speak_word=True, _speak_example=False):
    """Word / Picture / Meaning: the picture asks, the word answers, aloud."""
    code, _label, voice, font, _words = language
    words, meanings = PICTURE_WORDS[code]
    config = [
        "#config",
        _spoken("side=back; size=44; bold", code, voice, font, speak_word),
        "side=front; image; size=300",
        "side=back; size=24",
    ]
    rows = [PICTURE_HEADERS, config]
    for n, (word, picture, meaning) in enumerate(
        zip(words, PICTURES, meanings, strict=True), 1
    ):
        rows.append([f"w{n:02}", word, picture, meaning])
    return rows


def modules_the_site_loads():
    """The module list declared in site/pyodide.js — the only place it is written."""
    app = (SITE / "pyodide.js").read_text(encoding="utf-8")
    match = re.search(r"export const PURE_MODULES = \[(.*?)\]", app, re.S)
    if not match:
        sys.exit("site/pyodide.js does not declare PURE_MODULES")
    return module_names(match.group(1))


def module_names(listed):
    """The names inside a JS array literal, comments and all.

    Comments are stripped first rather than split around: a `//` line explaining
    why a module is in the list will contain a comma sooner or later, and then
    half a sentence gets looked up as a module.
    """
    listed = re.sub(r"//[^\n]*", "", listed)
    return [name.strip().strip("\"'") for name in listed.split(",") if name.strip()]


def check_purity(names):
    """Refuses to ship a module that reaches outside the standard library.

    The browser has no Anki to import, so this failing at build time is far
    better than the page failing at load time in front of a user.
    """
    allowed = set(names) | {"errors"}
    problems = []
    for name in names:
        text = (SRC / f"{name}.py").read_text(encoding="utf-8")
        for line in text.splitlines():
            imported = re.match(
                r"from \.(\w+) import|from \.(\w+)|from \. import (\w+)", line
            )
            if imported:
                target = next(g for g in imported.groups() if g)
                if target not in allowed:
                    problems.append(
                        f"{name}.py imports .{target}, which is not in the site's module set"
                    )
            if re.match(r"\s*(from|import)\s+(aqt|anki|PyQt6)\b", line):
                problems.append(
                    f"{name}.py imports {line.strip()!r} — it cannot run in the browser"
                )
    if problems:
        sys.exit("Preview site would break:\n  " + "\n  ".join(problems))


# An address in an attribute that is relative to the page: not empty, not a
# fragment or a bare query, not rooted, not a scheme (https:, data:, mailto:) and not protocol-relative.
_RELATIVE = re.compile(r'\b(href|src)="(?![#/?]|[a-z][a-z0-9+.-]*:)([^"]+)"', re.I)


def relocate(text, depth):
    """A page written as if it sat at its folder, moved ``depth`` folders down.

    ``./style.css`` becomes ``../style.css``, ``./`` becomes ``../``. Only
    ``href`` and ``src`` attributes are touched, and only relative ones; a
    ``#fragment`` stays on the page it is on. Scripts are not rewritten: they
    resolve the site's pages from their own address (site/paths.js), which does
    not depend on the page that loaded them.
    """
    if depth <= 0:
        return text
    up = "../" * depth

    def swap(match):
        value = match.group(2)
        value = value[2:] if value.startswith("./") else value
        return f'{match.group(1)}="{up}{value}"'

    return _RELATIVE.sub(swap, text)


def redirect_page(to, title):
    """The page left at an old address, forwarding to ``to`` (relative to it)."""
    template = (SITE / "_redirect.html").read_text(encoding="utf-8")
    # The template's opening comment is about the template, not the page.
    template = re.sub(r"<!--.*?-->\n", "", template, count=1, flags=re.S)
    return template.replace("%%TO%%", html.escape(to, quote=True)).replace(
        "%%TITLE%%", html.escape(title)
    )


def _relative(old, new):
    """``new`` (from the site's root) as seen from the page at ``old``."""
    up = "../" * old.count("/")
    return (up or "./") + new


def build_pages(out):
    """The site's own pages and the old addresses that forward to them."""
    # Files only: importing site/workbook.py — which the test suite does — leaves a
    # __pycache__ beside it, and a directory here used to stop the build dead.
    # A name starting with "_" is a build input (the docs template), not a page.
    redirects = dict(REDIRECTS)
    for item in sorted(SITE.iterdir()):
        if item.name.startswith((".", "_")) or not item.is_file():
            continue
        if item.name in PAGES:
            folder = out / PAGES[item.name]
            folder.mkdir()
            text = item.read_text(encoding="utf-8")
            (folder / "index.html").write_text(relocate(text, 1), encoding="utf-8")
            redirects[item.name] = f"{PAGES[item.name]}/"
            continue
        if item.name in redirects:
            sys.exit(f"site/{item.name} is a page and an old address at once")
        shutil.copy2(item, out / item.name)
    for old, new in redirects.items():
        page = redirect_page(_relative(old, new), PAGE_TITLES.get(new, "SheetCards"))
        (out / old).write_text(page, encoding="utf-8")


def build(out=OUT):
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    build_pages(out)

    names = modules_the_site_loads()
    check_purity(names)

    pkg = out / "sc"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    for name in names:
        shutil.copy2(SRC / f"{name}.py", pkg / f"{name}.py")

    build_home_cards(out)
    build_sheet_templates(out)
    build_downloads(out)
    build_ai_guide(out)
    pages = build_docs(out)

    # GitHub Pages runs the output through Jekyll unless told not to, which
    # silently drops files and directories whose names begin with an underscore.
    (out / ".nojekyll").write_text("", encoding="utf-8")

    total = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"built {out}")
    print(f"  page      : {len(list(out.glob('*')))} files")
    print(f"  docs      : {pages} pages")
    print(f"  python    : {', '.join(names)}")
    print(f"  total     : {total / 1024:.0f} KB (Pyodide itself loads from a CDN)")
    return out


def build_downloads(out):
    """The two workbooks the landing page offers: the starter and the examples."""
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        import build_examples
    finally:
        sys.path.pop(0)
    data, _ = build_examples.build_bytes(STARTER)
    (out / STARTER_NAME).write_bytes(data)
    shutil.copy2(EXAMPLES, out / EXAMPLES.name)


def build_ai_guide(out):
    """/ai.md and /llms.txt, for an AI assistant writing a CSV (scripts/ai_guide.py)."""
    sys.path.insert(0, str(REPO / "scripts"))
    try:
        import ai_guide
        import build_examples
    finally:
        sys.path.pop(0)
    cloze = build_examples.SHEETS["06 Cloze (điền chỗ trống)"]
    return ai_guide.write(out, sheet_templates(out), *_pure_package(out), cloze)


# ---------------------------------------------------------------------------
# The landing page's demo cards
# ---------------------------------------------------------------------------


def _pure_package(out):
    """The ``sc`` package just copied into ``out``, imported from there.

    The same files the browser loads, so the demo cannot be rendered by a
    different version of the code than the preview runs.
    """
    ours = [m for m in sys.modules if m == "sc" or m.startswith("sc.")]
    saved = {m: sys.modules.pop(m) for m in ours}
    sys.path.insert(0, str(out))
    try:
        from sc import card_layout
        from sc import tsv_model
        from sc import workbook

        return tsv_model, card_layout, workbook
    finally:
        # Put back whatever "sc" meant before — the test suite fabricates a
        # package of that name too, and must not find this one in its place.
        sys.path.remove(str(out))
        for m in [m for m in sys.modules if m == "sc" or m.startswith("sc.")]:
            del sys.modules[m]
        sys.modules.update(saved)


def _letter(index):
    """The column letter a spreadsheet shows: 0 → A, 25 → Z, 26 → AA."""
    text, n = "", index + 1
    while n:
        n, rest = divmod(n - 1, 26)
        text = chr(65 + rest) + text
    return text


def home_cards(out):
    """Each demo row as the sheet shows it and the templates the add-on builds."""
    tm, card_layout, workbook = _pure_package(out)
    data = EXAMPLES.read_bytes()
    cards = []
    for sheet, row_id, label, theme in HOME_EXAMPLES:
        tsv = workbook.sheet_tsv(data, sheet)
        lines = tsv.split("\n")
        marker, _, rest = lines[1].partition("\t")
        if not marker.lower().startswith("#config"):
            sys.exit(f"home demo: {sheet!r} has no settings row to set a theme in")
        kept = [
            pair.strip()
            for pair in marker[len("#config") :].split(";")
            if pair.strip() and not pair.strip().lower().startswith("theme")
        ]
        marker = "#config " + "; ".join(kept + [f"theme={theme}"])
        lines[1] = marker + "\t" + rest
        parsed = tm.parse_tsv_data("\n".join(lines), [])
        deck = tm.build_remote_deck_from_tsv(parsed, "", [])
        plan, cfg = deck.plan, deck.sheet_config
        if cfg.theme != theme or cfg.warnings:
            sys.exit(f"home demo: {sheet!r} did not take theme={theme}: {cfg.warnings}")
        headers = parsed["headers"]
        config, row, line = parsed["rows"][0], None, 0
        for at, raw in enumerate(parsed["rows"]):
            if raw and raw[0] == row_id:
                # Row 1 is the header, so the first parsed row is row 2.
                row, line = raw, at + 2
        if row is None:
            sys.exit(f"home demo: {sheet!r} has no row {row_id!r}")
        values = tm.row_to_dict(row, headers)
        tm.apply_media_rewrites(values, plan, cfg)
        front, back = card_layout.split_sides(plan, cfg)
        shown = [plan.id_header] + list(plan.content_headers)
        columns = []
        for name in shown:
            at = headers.index(name)
            columns.append(
                {
                    "letter": _letter(at),
                    "name": name,
                    "config": config[at] if at < len(config) else "",
                    "value": row[at] if at < len(row) else "",
                    "side": (
                        "front" if name in front else "back" if name in back else "none"
                    ),
                }
            )
        template = card_layout.build_templates(plan, cfg, bool(cfg.cloze_field))[0]
        cards.append(
            {
                "sheet": sheet,
                "label": label,
                "line": line,
                "columns": columns,
                "template": {"qfmt": template["qfmt"], "afmt": template["afmt"]},
                "values": values,
            }
        )
    return cards


def _hanzi_writer(out):
    _tm, card_layout, _workbook = _pure_package(out)
    return card_layout.HANZI_WRITER


def build_home_cards(out):
    body = json.dumps(home_cards(out), ensure_ascii=False, indent=1)
    (out / "home-cards.js").write_text(
        "// Generated by scripts/build_site.py from examples/sheetcards-examples.xlsx\n"
        "// with the add-on's own card_layout.py. Do not edit.\n"
        f"export const CARDS = {body};\n"
        # The writing box's library, from the one place a card gets it, so the
        # demo animates a character with the same pinned version a card loads.
        f"export const HANZI_WRITER = {json.dumps(_hanzi_writer(out))};\n"
        # The feature grid's swatches, from the palettes a card is painted with,
        # so the landing page cannot show a colour no card has.
        f"export const THEME_SWATCHES = {json.dumps(theme_swatches(out))};\n",
        encoding="utf-8",
    )


def theme_swatches(out):
    """``[{name, light: {bg, fg, accent}, night: {...}}]`` for each listed theme."""
    tm, _card_layout, _workbook = _pure_package(out)
    themes = tm.parse_config_row.__globals__["THEMES"]
    names = tm.parse_config_row.__globals__["listed_themes"]()
    keep = ("bg", "fg", "accent")
    return [
        {
            "name": name,
            **{
                mode: {k: themes[name][mode][k] for k in keep}
                for mode in ("light", "night")
            },
        }
        for name in names
    ]


# ---------------------------------------------------------------------------
# Create sheet's templates
# ---------------------------------------------------------------------------


def _template_card(tm, card_layout, name, rows):
    """Parses one template's rows and returns the card its first word becomes.

    A template is the first thing somebody writes into, so it must not open with
    a warning: the build stops on a warning or an empty front rather than
    shipping a starting point that is already wrong. The card is what the picker
    shows: the templates card_layout.py builds and the first word's values, so
    anki.js can fill it without Pyodide. The voice list a spoken card carries is
    left out — it lists the voices of the device reviewing the card, a picture
    of a card is not one, and it is most of the template's weight.
    """
    parsed = tm.parse_tsv_data("\n".join("\t".join(row) for row in rows), [])
    deck = tm.build_remote_deck_from_tsv(parsed, "", [])
    plan, cfg = deck.plan, deck.sheet_config
    if cfg.warnings:
        sys.exit(f"template {name!r} warns: {cfg.warnings}")
    front, _ = card_layout.split_sides(plan, cfg)
    if not front:
        sys.exit(f"template {name!r} has nothing on the front")
    word = parsed["rows"][1] if len(parsed["rows"]) > 1 else []
    values = tm.row_to_dict(word, parsed["headers"])
    tm.apply_media_rewrites(values, plan, cfg)
    if not any(values.get(h) for h in plan.content_headers):
        # The blank template's word is empty; its card shows the column names,
        # which is what a blank card is about to hold.
        values = {h: h for h in plan.content_headers}
    templates = card_layout.build_templates(plan, cfg, bool(cfg.cloze_field))

    def picture(side):
        side = re.sub(
            r"<details class=\"[^\"]*sc-tts-debug[\s\S]*?</details>", "", side
        )
        return re.sub(r"<script>[\s\S]*?</script>", "", side)

    def faces(template):
        return {"qfmt": picture(template["qfmt"]), "afmt": picture(template["afmt"])}

    card = {"template": faces(templates[0]), "values": values}
    if len(templates) > 1:
        # The reverse card: the picker shows both, since that is the point.
        card["reverse"] = faces(templates[1])
    return card


def _language_template(tm, card_layout, tid, rows_for, toggles, theme=None):
    """A template made from the vocabulary template's language step: one variant
    per language × read-aloud choice it offers, each parsed and refused on a
    warning or an empty front like the rest."""
    variants = {}
    for language in VOCAB_LANGUAGES:
        code = language[0]
        for word in (True, False):
            for example in (True, False) if "example" in toggles else (False,):
                key = f"{code}|{int(word)}{int(example)}"
                rows = rows_for(language, word, example)
                variants[key] = {
                    "rows": rows,
                    "card": _template_card(tm, card_layout, f"{tid} {key}", rows),
                }
    out = {"id": tid, "toggles": toggles, "variants": variants}
    if theme:
        out["theme"] = theme
    return out


def sheet_templates(out):
    """Every template: the main ones — Basic in both languages, every variant of
    the vocabulary template, Chinese writing, Japanese furigana and the custom
    one — then the others: picture words, reverse and typed answer. A theme is
    not a template of its own: the step offers every listed theme over any of
    them (theme_palettes()).

    Every language × read-Word × read-Example combination is parsed here, so a
    choice on the page can never produce a sheet that warns.
    """
    tm, card_layout, _workbook = _pure_package(out)
    basic = {
        "id": "basic",
        "variants": {
            lang: {
                "rows": rows,
                "card": _template_card(tm, card_layout, f"basic {lang}", rows),
            }
            for lang, rows in BASIC_TEMPLATES.items()
        },
    }
    both = ["word", "example"]
    vocab = _language_template(tm, card_layout, "vocab", vocab_rows, both)
    vocab["languages"] = [
        {"code": code, "label": label, "voice": voice}
        for code, label, voice, _font, _words in VOCAB_LANGUAGES
    ]
    fixed = [
        {"id": tid, "rows": rows, "card": _template_card(tm, card_layout, tid, rows)}
        for tid, rows in (
            ("hanzi", HANZI_TEMPLATE),
            ("kanji", KANJI_TEMPLATE),
            ("custom", CUSTOM_TEMPLATE),
        )
    ]
    # The English page's copy of a template whose words are Vietnamese.
    for tpl, rows in zip(fixed, (HANZI_TEMPLATE_EN, KANJI_TEMPLATE_EN), strict=False):
        tpl["en"] = {
            "rows": rows,
            "card": _template_card(tm, card_layout, f"{tpl['id']} en", rows),
        }
    more = [
        _language_template(tm, card_layout, "picture", picture_rows, ["word"]),
        _language_template(tm, card_layout, "reverse", reverse_rows, ["word"]),
        _language_template(
            tm,
            card_layout,
            "typed",
            lambda lang, w, e: vocab_rows(lang, w, e, typed=True),
            both,
        ),
    ]
    for tpl in more:
        tpl["more"] = True
    return [basic, vocab, *fixed, *more]


def theme_palettes(out):
    """The colour block card_layout puts at the top of a card's stylesheet, for
    no theme ("") and for each listed theme — never an unlisted one.

    The template step lets any template be dressed in any theme, and its cards
    are drawn without Python: sheet.js swaps the block a card was built with for
    the chosen one. That only works because this is the exact text _palette()
    writes, so it is taken from it rather than written twice.
    """
    from types import SimpleNamespace

    tm, card_layout, _workbook = _pure_package(out)
    # The themes a sheet is told about, never the unlisted ones: asked of the
    # copy just loaded, through a function of the module that defines them.
    names = tm.parse_config_row.__globals__["listed_themes"]()
    return {
        name: card_layout._palette(SimpleNamespace(theme=name or None))
        for name in ["", *names]
    }


def _interned(templates):
    """The templates with each card's HTML cut into pieces held once.

    Two hundred variants share a handful of stylesheets and a few dozen
    template bodies — a theme changes only the stylesheet — so each side is
    written as a list of indices into one table, and site/sheet.js joins them
    back on load. What is shipped is still exactly what card_layout made.
    """
    table, index = [], {}

    def ref(text):
        pieces = [p for p in re.split(r"(<style>[\s\S]*?</style>)", text) if p]
        out = []
        for piece in pieces:
            if piece not in index:
                index[piece] = len(table)
                table.append(piece)
            out.append(index[piece])
        return out

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ("qfmt", "afmt") and isinstance(value, str):
                    node[key] = ref(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(templates)
    return templates, table


def build_sheet_templates(out):
    templates, pieces = _interned(sheet_templates(out))
    palettes = json.dumps(
        theme_palettes(out), ensure_ascii=False, separators=(",", ":")
    )
    body = json.dumps(templates, ensure_ascii=False, separators=(",", ":"))
    table = json.dumps(pieces, ensure_ascii=False, separators=(",", ":"))
    (out / "sheet-templates.js").write_text(
        "// Generated by scripts/build_site.py from SHEET_TEMPLATES with the\n"
        "// add-on's own card_layout.py. Do not edit. Each qfmt/afmt is a list of\n"
        "// indices into PIECES, joined back by site/sheet.js.\n"
        f"export const PIECES = {table};\n"
        f"export const TEMPLATES = {body};\n"
        f"export const PALETTES = {palettes};\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# The documentation
# ---------------------------------------------------------------------------


def _doc_names(lang):
    folder = DOCS / DOC_LANGS[lang]
    listed = [name for _, names in DOC_GROUPS for name in names]
    found = sorted(p.stem for p in folder.glob("*.md"))
    missing = sorted(set(listed) - set(found))
    unlisted = sorted(set(found) - set(listed))
    if missing or unlisted or len(listed) != len(set(listed)):
        sys.exit(
            f"{folder.relative_to(REPO)} and DOC_GROUPS disagree:"
            + (f"\n  listed but no file: {missing}" if missing else "")
            + (f"\n  file but not listed: {unlisted}" if unlisted else "")
        )
    return listed


def _slug_vi(value, separator):
    """An ASCII anchor for a Vietnamese heading: ``Đặt tên deck`` → ``dat-ten-deck``.

    The toc extension's ``slugify`` already drops the tone marks, but ``đ`` has no
    decomposition and would vanish (``at-ten-deck``); a heading in no Latin script
    at all falls back to keeping its own letters.
    """
    from markdown.extensions.toc import slugify
    from markdown.extensions.toc import slugify_unicode

    ascii_value = value.replace("đ", "d").replace("Đ", "D")
    return slugify(ascii_value, separator) or slugify_unicode(value, separator)


def _href(name):
    """A docs page's address, from its language's folder (``docs/`` or
    ``docs/en/``): ``faq/``, or ``./`` for the front page. Every docs page is
    written as if it sat there and moved into its own folder afterwards
    (``relocate``), so one function serves every page."""
    return "./" if name == "index" else f"{name}/"


def _rewrite_links(text):
    """``columns.md#x`` → ``columns/#x``: the Markdown links work on GitHub
    and in an editor, and the built pages link to each other."""

    def swap(match):
        name, anchor = match.group(1), match.group(2) or ""
        return f'href="{_href(name)}{anchor}"'

    return re.sub(r'href="([\w-]+)\.md(#[^"]*)?"', swap, text)


def _wrap_tables(text):
    """A table scrolls inside its own box, so the page never scrolls sideways."""
    return re.sub(
        r"(<table>.*?</table>)", r'<div class="tablewrap">\1</div>', text, flags=re.S
    )


def _nav(current, titles, toc, lang):
    parts = []
    for group, names in DOC_GROUPS:
        parts.append(f'<p class="docnav-group">{html.escape(group[lang])}</p><ul>')
        for name in names:
            here = ' aria-current="page"' if name == current else ""
            parts.append(
                f'<li><a href="{_href(name)}"{here}>{html.escape(titles[name])}</a>'
            )
            if name == current and toc:
                parts.append('<ul class="docnav-toc">')
                for entry in toc:
                    parts.append(
                        f'<li><a href="#{entry["id"]}">{entry["name"]}</a></li>'
                    )
                parts.append("</ul>")
            parts.append("</li>")
        parts.append("</ul>")
    return "\n".join(parts)


def _onpage(toc, words):
    """The page's own headings, for the third column a very wide screen has room
    for; narrower, the same list sits under the page's name in the sidebar."""
    if not toc:
        return ""
    items = "".join(f'<li><a href="#{e["id"]}">{e["name"]}</a></li>' for e in toc)
    return (
        f'<aside class="onpage" aria-label="{html.escape(words["onpage"])}">'
        f'<p class="docnav-group">{html.escape(words["onpage"])}</p><ul>{items}</ul></aside>'
    )


def _pager(names, index, titles, words):
    links = []
    if index > 0:
        prev = names[index - 1]
        links.append(
            f'<a class="prev" href="{_href(prev)}"><span data-icon="arrow-left">'
            f"</span><span><small>{words['previous']}</small>{html.escape(titles[prev])}</span></a>"
        )
    if index < len(names) - 1:
        nxt = names[index + 1]
        links.append(
            f'<a class="next" href="{_href(nxt)}"><span><small>{words["next"]}</small>'
            f'{html.escape(titles[nxt])}</span><span data-icon="arrow-right"></span></a>'
        )
    return "\n".join(links)


def build_docs(out):
    """docs/site/**.md → out/docs/**.html, one tree per language."""
    template = (SITE / "_docs.html").read_text(encoding="utf-8")
    return sum(build_docs_in(out, lang, template) for lang in DOC_LANGS)


def build_docs_in(out, lang, template):
    import markdown
    from markdown.extensions.toc import slugify_unicode

    folder = DOC_LANGS[lang]
    words = DOC_CHROME[lang]
    names = _doc_names(lang)
    source_dir = DOCS / folder
    sources = {n: (source_dir / f"{n}.md").read_text(encoding="utf-8") for n in names}
    titles = {}
    for name, text in sources.items():
        heading = re.search(r"^# (.+)$", text, re.M)
        if not heading:
            sys.exit(f"{source_dir.relative_to(REPO)}/{name}.md has no '# Title' line")
        titles[name] = heading.group(1).strip()

    # The other language's copy of a page: Vietnamese sits at /docs/, English
    # one folder down at /docs/en/.
    (twin_lang,) = set(DOC_LANGS) - {lang}
    up = "../" if folder else ""
    root = "../" + up
    target = out / "docs" / folder
    target.mkdir(parents=True, exist_ok=True)
    for index, name in enumerate(names):
        md = markdown.Markdown(
            extensions=["tables", "fenced_code", "toc", "sane_lists"],
            extension_configs={
                "toc": {
                    "slugify": _slug_vi if lang == "vi" else slugify_unicode,
                    "permalink": "#",
                    "permalink_class": "headerlink",
                    "permalink_title": words["permalink"],
                    "toc_depth": "2",
                }
            },
        )
        body = _wrap_tables(_rewrite_links(md.convert(sources[name])))
        toc = md.toc_tokens[0]["children"] if md.toc_tokens else []
        first = re.search(r"<p>(.*?)</p>", body, re.S)
        summary = re.sub(r"<[^>]+>", "", first.group(1)) if first else ""
        summary = " ".join(summary.split())[:200]
        twin = up + (DOC_LANGS[twin_lang] + "/" if DOC_LANGS[twin_lang] else "")
        twin = (twin or "./") if name == "index" else twin + f"{name}/"
        source = "/".join(p for p in ("docs/site", folder, f"{name}.md") if p)
        page = (
            template.replace("%%TITLE%%", html.escape(titles[name]))
            .replace("%%DESCRIPTION%%", html.escape(summary))
            .replace("%%LANG%%", lang)
            .replace("%%ROOT%%", root)
            .replace("%%TWIN_LANG%%", twin_lang)
            .replace("%%TWIN%%", twin)
            .replace("%%TWIN_TEXT%%", words["twin"])
            .replace("%%W_NAV%%", words["nav"])
            .replace("%%W_CONTENTS%%", words["contents"])
            .replace("%%W_PAGES%%", words["pages"])
            .replace("%%W_EDIT%%", words["edit"])
            .replace("%%W_CONTACT%%", words["contact"])
            .replace("%%FROM%%", "/".join(p for p in ("docs", folder, name) if p))
            .replace("%%NAV%%", _nav(name, titles, toc, lang))
            .replace("%%ONPAGE%%", _onpage(toc, words))
            .replace("%%PAGER%%", _pager(names, index, titles, words))
            .replace("%%SOURCE%%", source)
            .replace("%%BODY%%", body)
        )
        if name == "index":
            (target / "index.html").write_text(page, encoding="utf-8")
            continue
        (target / name).mkdir(exist_ok=True)
        (target / name / "index.html").write_text(relocate(page, 1), encoding="utf-8")
        # The page's address until it became a folder, forwarding to it.
        (target / f"{name}.html").write_text(
            redirect_page(f"./{name}/", f"{titles[name]} — SheetCards docs"),
            encoding="utf-8",
        )
    return len(names)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--serve", action="store_true", help="serve the result on :8000"
    )
    args = parser.parse_args()

    out = build()
    if args.serve:
        import functools
        import http.server

        handler = functools.partial(
            http.server.SimpleHTTPRequestHandler, directory=str(out)
        )
        print("\nhttp://localhost:8000  (Ctrl+C to stop)")
        http.server.ThreadingHTTPServer(("", 8000), handler).serve_forever()


if __name__ == "__main__":
    main()
