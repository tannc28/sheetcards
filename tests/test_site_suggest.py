"""Suggestions for a word: ``site/suggest.js``'s parsers, run in node.

Create sheet's *Gợi ý* offers senses and IPA from Wiktionary, example sentences
from Tatoeba and pictures from Commons. The suite never reaches the network:
each parser is fed a response saved in ``tests/fixtures/suggest/`` (fetched once
by hand from the same URLs the page asks), and a fake ``fetch`` stands in for the
rest. A parser that misreads a template puts a wrong IPA or a stranger's
translation on a card the learner trusts.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parent.parent / "site"
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "suggest"
NODE = shutil.which("node")

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(NODE is None, reason="node is not installed"),
]


def _fixture(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _wikitext(name):
    return _fixture(name)["parse"]["wikitext"]


def _run(body, data=None):
    """Runs ``body`` with ``m`` the module and ``data`` passed on stdin.

    On stdin rather than in argv: a page of wikitext is tens of KB, and CI's
    Linux refuses an argument over 128 KB.
    """
    script = (
        "let raw = ''; process.stdin.on('data', (c) => (raw += c));"
        "process.stdin.on('end', () => {"
        f"import({json.dumps((SITE / 'suggest.js').as_uri())}).then(async (m) => {{"
        "const data = raw ? JSON.parse(raw) : null;"
        f"const out = await (async () => {{ {body} }})();"
        "process.stdout.write(JSON.stringify(out)); })"
        ".catch((e) => { process.stdout.write(JSON.stringify({ error: String(e) })); });"
        "});"
    )
    out = subprocess.run(
        [NODE, "--no-warnings", "-e", script],
        input=json.dumps(data) if data is not None else "",
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return json.loads(out.stdout)


def _senses(name, lang="en"):
    return _run(
        "return m.parseSenses(data.text, data.lang);",
        {"text": _wikitext(name), "lang": lang},
    )


def _pron(name):
    return _run("return m.parsePronunciation(data, 'en');", _wikitext(name))


class TestSenses:
    def test_apple_offers_noun_and_verb_senses_with_vietnamese(self):
        senses = _senses("enwikt-apple.json")
        assert 1 < len(senses) <= 5
        assert {s["pos"] for s in senses} == {"noun", "verb"}
        fruit = next(s for s in senses if "Malus domestica" in s["en"])
        assert "táo" in fruit["vi"].split(", ")
        # Links, templates and bold are gone; nothing of the markup is left.
        for s in senses:
            assert not any(ch in s["en"] for ch in "[]{}|'"), s["en"]

    def test_a_translation_goes_only_to_the_sense_its_table_names(self):
        senses = _senses("enwikt-bank.json")
        money = senses[0]
        assert "institution" in money["en"] and "ngân hàng" in money["vi"]
        # The Hán-Nôm spelling listed beside ngân hàng is not a meaning.
        assert "銀行" not in money["vi"]
        branch = next(s for s in senses if "branch" in s["en"])
        assert branch["vi"] == ""

    def test_labels_are_kept_as_words(self):
        senses = _senses("enwikt-bank.json")
        assert senses[0]["en"].startswith("(countable) ")

    def test_glosses_are_short(self):
        for name in ("enwikt-apple.json", "enwikt-bank.json", "enwikt-journey.json"):
            assert all(len(s["en"]) <= 112 for s in _senses(name))

    def test_chinese_korean_and_japanese_sections_are_read(self):
        zh = _senses("enwikt-zh-yinhang.json", "zh")
        assert zh[0] == {"pos": "noun", "en": "bank (financial institution)", "vi": ""}
        ko = _senses("enwikt-ko-sagwa.json", "ko")
        assert [s["en"] for s in ko] == ["apple", "apology"]
        ja = _senses("enwikt-ja-ringo.json", "ja")
        assert ja[0]["en"] == "apple"
        assert len({s["en"] for s in ja}) == len(ja)

    def test_a_soft_redirect_names_the_page_with_the_entry(self):
        zh = _run(
            "return m.seeAlso(m.languageSection(data, 'Chinese'));",
            _wikitext("enwikt-zh-yinhang-simplified.json"),
        )
        ja = _run(
            "return m.seeAlso(m.languageSection(data, 'Japanese'));",
            _wikitext("enwikt-ja-ringo-kana.json"),
        )
        assert (zh, ja) == ("銀行", "林檎")

    def test_vi_wiktionary_glosses(self):
        out = _run(
            "return m.parseViSenses(data, 'en');", _wikitext("viwikt-journey.json")
        )
        assert out[0] == {
            "pos": "noun",
            "vi": "Cuộc hành trình (thường là bằng đường bộ)",
        }
        assert out[-1]["pos"] == "verb"

    def test_vietnamese_only_senses_are_added_without_crowding_out_the_english(self):
        out = _run(
            "return m.mergeSenses(data.en, data.vi);",
            {
                "en": [{"pos": "noun", "en": f"sense {n}", "vi": ""} for n in range(5)],
                "vi": [{"pos": "noun", "vi": "chuyến đi"}, {"pos": "verb", "vi": "đi"}],
            },
        )
        assert len(out) == 5
        assert [s["source"] for s in out] == ["en", "en", "en", "vi", "vi"]


class TestPronunciation:
    def test_apple_has_one_ipa_for_both_accents_and_files_for_each(self):
        out = _pron("enwikt-apple.json")
        assert out["ipa"] == {"us": "/ˈæpəl/", "uk": "/ˈæpəl/"}
        files = {a["file"]: a["accent"] for a in out["audio"]}
        assert files["En-us-apple.ogg"] == "us"
        assert files["En-uk-apple.ogg"] == "uk"

    def test_journey_differs_between_us_and_uk(self):
        out = _pron("enwikt-journey.json")
        assert out["ipa"]["us"] == "/ˈd͡ʒɝni/"
        assert out["ipa"]["uk"] == "/ˈd͡ʒɜːni/"

    def test_the_first_matching_transcription_wins(self):
        # bank lists /ˈbæŋk/ for RP and GA before the æ-tensing /ˈbeɪ̯ŋk/ for US.
        out = _pron("enwikt-bank.json")
        assert out["ipa"] == {"us": "/ˈbæŋk/", "uk": "/ˈbæŋk/"}
        assert out["audio"] == [{"file": "en-us-bank.ogg", "accent": "us"}]

    def test_an_unlabelled_transcription_stands_for_both(self):
        out = _run(
            "return m.parsePronunciation(data, 'en');",
            "==English==\n* {{IPA|en|/kæt/}}\n",
        )
        assert out["ipa"] == {"us": "/kæt/", "uk": "/kæt/"}


class TestTatoeba:
    def test_sentences_carry_their_vietnamese_translation_and_ids(self):
        out = _run("return m.parseTatoeba(data);", _fixture("tatoeba-apple.json"))
        assert len(out) == 3
        assert out[0] == {
            "id": 9191859,
            "text": "Mom bought apples.",
            "vi": "Mẹ đã mua táo.",
            "viId": 13340198,
            "owner": "CK",
            "viOwner": "leucammieuvu",
        }

    def test_unapproved_long_and_untranslated_sentences_are_left_out(self):
        body = {
            "data": [
                {
                    "id": 1,
                    "text": "Bad.",
                    "is_unapproved": True,
                    "translations": [[{"id": 9, "lang": "vie", "text": "x"}]],
                },
                {
                    "id": 2,
                    "text": "x" * 120,
                    "translations": [{"id": 9, "lang": "vie", "text": "x"}],
                },
                {
                    "id": 3,
                    "text": "No vi.",
                    "translations": [{"id": 9, "lang": "fra", "text": "x"}],
                },
                {
                    "id": 4,
                    "text": "Good.",
                    "translations": [
                        {"id": 10, "lang": "vie", "text": "qua", "is_direct": False},
                        {"id": 11, "lang": "vie", "text": "thẳng", "is_direct": True},
                    ],
                },
            ]
        }
        out = _run("return m.parseTatoeba(data);", body)
        assert [(s["id"], s["vi"]) for s in out] == [(4, "thẳng")]


class TestCommons:
    def test_pictures_are_stored_as_special_filepath_with_their_credit(self):
        out = _run("return m.parseCommons(data);", _fixture("commons-apple.json"))
        assert 4 <= len(out) <= 8
        red = out[0]
        assert red["file"] == "Red Apple.jpg"
        assert (
            red["url"]
            == "https://commons.wikimedia.org/wiki/Special:FilePath/Red_Apple.jpg?width=500"
        )
        assert red["licence"] == "CC BY 2.0"
        assert red["author"] and "<" not in red["author"]
        assert all(p["thumb"].startswith("https://") for p in out)

    def test_an_audio_file_is_linked_the_way_the_workbook_links_it(self):
        assert _run("return m.filePath('En-us-apple.ogg');") == (
            "https://commons.wikimedia.org/wiki/Special:FilePath/En-us-apple.ogg"
        )


class TestCredits:
    def test_the_credit_line_names_every_source_used(self):
        out = _run(
            "return m.creditLine({wiktionary: true, tatoeba: [{id: 1, viId: 2}],"
            " image: {file: 'Red Apple.jpg', author: 'A', licence: 'CC BY 2.0'}});"
        )
        assert out == (
            "Wiktionary (CC BY-SA 4.0); Tatoeba #1/#2 (CC BY 2.0 FR); "
            "Wikimedia Commons: Red Apple.jpg — A, CC BY 2.0"
        )

    def test_a_credit_is_merged_without_repeats(self):
        out = _run(
            "return m.mergeCredit('my note; Wiktionary (CC BY-SA 4.0)', 'Wiktionary (CC BY-SA 4.0); Tatoeba #1 (CC BY 2.0 FR)');"
        )
        assert out == "my note; Wiktionary (CC BY-SA 4.0); Tatoeba #1 (CC BY 2.0 FR)"


class TestLookup:
    def _lookup(self, word, lang, want, responses):
        return _run(
            "const fetcher = async (url) => {"
            "  const hit = Object.entries(data.responses).find(([k]) => url.includes(k));"
            "  if (!hit) throw new TypeError('offline');"
            "  return { ok: true, status: 200, json: async () => hit[1] };"
            "};"
            "return m.lookup(data.word, data.lang, { want: data.want, fetcher });",
            {"word": word, "lang": lang, "want": want, "responses": responses},
        )

    def test_everything_for_an_english_word(self):
        out = self._lookup(
            "apple",
            "en",
            {"examples": True, "images": True},
            {
                "en.wiktionary.org": _fixture("enwikt-apple.json"),
                "vi.wiktionary.org": _fixture("viwikt-apple.json"),
                "api.tatoeba.org": _fixture("tatoeba-apple.json"),
                "commons.wikimedia.org": _fixture("commons-apple.json"),
            },
        )
        assert out["errors"] == []
        assert out["senses"] and out["ipa"]["us"] == "/ˈæpəl/"
        assert len(out["examples"]) == 3 and out["images"]
        assert any(s["source"] == "vi" for s in out["senses"]) or any(
            s["vi"] for s in out["senses"]
        )

    def test_a_simplified_chinese_word_follows_its_soft_redirect(self):
        out = self._lookup(
            "银行",
            "zh",
            {},
            {
                "page=%E9%93%B6%E8%A1%8C": _fixture(
                    "enwikt-zh-yinhang-simplified.json"
                ),
                "page=%E9%8A%80%E8%A1%8C": _fixture("enwikt-zh-yinhang.json"),
            },
        )
        assert out["senses"][0]["en"] == "bank (financial institution)"
        # No Tatoeba, no IPA, no vi.wiktionary for CJK: nothing was asked for.
        assert out["examples"] == [] and out["ipa"] == {"us": "", "uk": ""}

    def test_offline_every_source_fails_and_says_so(self):
        out = self._lookup("apple", "en", {"examples": True, "images": True}, {})
        assert out["senses"] == [] and out["examples"] == [] and out["images"] == []
        assert {e["source"] for e in out["errors"]} == {
            "wiktionary",
            "tatoeba",
            "commons",
        }
        assert all(e["offline"] for e in out["errors"])

    def test_coverage_is_honest_about_cjk(self):
        out = _run("return [m.coverage('en'), m.coverage('zh'), m.coverage('xx')];")
        assert out[0]["vi"] and out[0]["examples"]
        assert out[1] == {
            "senses": True,
            "vi": False,
            "ipa": False,
            "examples": False,
            "audio": False,
            "images": False,
        }
        assert out[2] is None


def test_no_more_than_three_requests_at_once():
    out = _run(
        "const run = m.limiter(3); let now = 0, most = 0;"
        "const job = () => run(async () => { now++; most = Math.max(most, now);"
        "  await new Promise((r) => setTimeout(r, 5)); now--; });"
        "await Promise.all(Array.from({ length: 12 }, job));"
        "return most;"
    )
    assert out == 3
