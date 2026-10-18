"""Pictures and recordings carried inside the deck (src/media.py, media_fetch.py).

The rules both paths share are pinned here; the browser's half of the fetching
is run in node by tests/test_site_media.py, and the two paths writing the same
notes in a real Anki by tests/real_anki_overlap.py. The decisive real-Anki
check for a package — files land in collection.media, the recording plays
through Anki — is at the bottom.
"""

import io
import json
import zipfile

import pytest

from src import media
from src.apkg import build_package
from src.tsv_model import build_remote_deck_from_tsv
from src.tsv_model import parse_tsv_data

pytestmark = pytest.mark.unit

PIC = "https://example.org/p/apple.jpg"
SND = "https://example.org/s/apple.mp3"
OGG = "https://commons.wikimedia.org/wiki/Special:FilePath/En-us-book.ogg"
SVG = "https://commons.wikimedia.org/wiki/File:Flag_of_Vietnam.svg"
VID = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

SHEET = (
    "ID\tWord\tPicture\tSound\tClip\n"
    "#config\t\timage\taudio\tvideo\n"
    f"w01\tapple\t{PIC}\t{SND}\t{VID}\n"
    f"w02\tbook\t{SVG}\t{OGG}\t\n"
    f"w03\tagain\t{PIC}\tnot a link\t\n"
)


def deck():
    return build_remote_deck_from_tsv(parse_tsv_data(SHEET), "url")


# What Commons answered for these two titles on 2026-10-18, cut to what is read.
COMMONS_ANSWER = {
    "query": {
        "pages": {
            "1": {
                "title": "File:En-us-book.ogg",
                "imageinfo": [
                    {
                        "url": "https://upload.wikimedia.org/wikipedia/commons/3/3d/En-us-book.ogg?utm_source=x",
                        "mime": "application/ogg",
                    }
                ],
                "videoinfo": [
                    {
                        "derivatives": [
                            {
                                "src": "https://upload.wikimedia.org/wikipedia/commons/3/3d/En-us-book.ogg?utm=1",
                                "type": 'audio/ogg; codecs="vorbis"',
                            },
                            {
                                "src": "https://upload.wikimedia.org/wikipedia/commons/transcoded/3/3d/En-us-book.ogg/En-us-book.ogg.mp3",
                                "type": "audio/mpeg",
                            },
                        ]
                    }
                ],
            },
            "2": {
                "title": "File:Flag of Vietnam.svg",
                "imageinfo": [
                    {
                        "thumburl": "https://thumb.wikimedia.org/wikipedia/commons/thumb/2/21/Flag_of_Vietnam.svg/500px-Flag_of_Vietnam.svg.png?utm_source=x",
                        "mime": "image/svg+xml",
                    }
                ],
            },
            "-1": {"title": "File:Gone.jpg", "missing": ""},
        }
    }
}


class TestNames:
    def test_a_name_comes_from_the_address_alone(self):
        a = media.file_name(PIC, "image")
        assert a == media.file_name(PIC, "image", "image/png")
        assert a.startswith("_sc-") and a.endswith(".jpg") and len(a) == 4 + 16 + 4
        assert a != media.file_name(PIC + "?v=2", "image")

    def test_commons_files_are_named_for_what_is_fetched(self):
        assert media.file_name(OGG, "audio").endswith(".mp3")
        assert media.file_name(SVG, "image").endswith(".png")

    def test_no_extension_waits_for_the_answer(self):
        url = "https://example.org/picture?id=7"
        assert media.file_name(url, "image") is None
        assert media.file_name(url, "image", "image/webp; q=1").endswith(".webp")
        assert media.file_name(url, "image", "text/html") is None

    def test_commons_titles(self):
        assert media.commons_title(OGG) == "En-us-book.ogg"
        assert media.commons_title(SVG) == "Flag of Vietnam.svg"
        assert (
            media.commons_title(
                "https://upload.wikimedia.org/wikipedia/commons/b/b3/%E6%88%91-order.gif"
            )
            == "我-order.gif"
        )
        # A thumbnail is already the file somebody chose.
        assert (
            media.commons_title(
                "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3c/A.jpg/500px-A.jpg"
            )
            is None
        )
        assert media.commons_title(PIC) is None

    def test_only_https_is_an_address(self):
        assert media.address(" " + PIC + " ") == PIC
        assert media.address("http://example.org/a.jpg") is None
        assert media.address("apple.jpg") is None


class TestJobs:
    def test_every_picture_and_recording_once_and_never_video(self):
        d = deck()
        jobs = media.jobs(d.notes, d.plan, d.sheet_config)
        assert [(j["url"], j["kind"]) for j in jobs] == [
            (PIC, "image"),
            (SND, "audio"),
            (SVG, "image"),
            (OGG, "audio"),
        ]
        assert jobs[3]["commons"] == "En-us-book.ogg"

    def test_commons_resolves_to_the_thumbnail_and_the_mp3(self):
        found = media.commons_sources([json.dumps(COMMONS_ANSWER)])
        assert found["En-us-book.ogg"] == {
            "audio": "https://upload.wikimedia.org/wikipedia/commons/transcoded/3/3d/En-us-book.ogg/En-us-book.ogg.mp3"
        }
        assert found["Flag of Vietnam.svg"]["image"].endswith(
            "500px-Flag_of_Vietnam.svg.png"
        )
        assert "Gone.jpg" not in found

    def test_queries_ask_for_a_standard_thumbnail_fifty_at_a_time(self):
        queries = media.commons_queries([f"T{i}.jpg" for i in range(120)])
        assert len(queries) == 3
        assert "origin=*" in queries[0] and "iiurlwidth=500" in queries[0]

    def test_an_answer_that_is_not_the_kind_is_refused(self):
        job = {"url": PIC, "kind": "image", "name": None, "commons": None}
        assert media.settle(job, "text/html", 100) is None
        assert media.settle(job, "image/jpeg", media.FILE_LIMIT + 1) is None
        assert media.settle(job, "image/jpeg", 0) is None
        assert media.settle(job, "image/jpeg", 10) == media.file_name(PIC, "image")


class TestFields:
    def test_a_picture_holds_its_name_and_a_recording_anki_s_reference(self):
        d = deck()
        names = {PIC: "_sc-p.jpg", SND: "_sc-s.mp3"}
        row = dict(d.notes[0])
        media.embed(row, d.plan, d.sheet_config, names)
        assert row["Picture"] == "_sc-p.jpg"
        assert row["Sound"] == "[sound:_sc-s.mp3]"
        assert row["Clip"].startswith("https://www.youtube.com/embed/")

    def test_what_was_not_fetched_keeps_its_address(self):
        d = deck()
        row = dict(d.notes[1])
        media.embed(row, d.plan, d.sheet_config, {})
        assert row["Picture"] == SVG and row["Sound"] == OGG

    def test_embedded_name(self):
        assert media.embedded_name("[sound:_sc-a.mp3]") == "_sc-a.mp3"
        assert media.embedded_name("_sc-a.jpg") == "_sc-a.jpg"
        assert media.embedded_name(PIC) is None


class TestPackage:
    def test_the_files_travel_in_the_legacy_layout(self):
        d = deck()
        data = build_package(
            "S",
            "D",
            d.plan,
            d.sheet_config,
            d.notes,
            now=1786000000,
            media={PIC: ("_sc-p.jpg", b"jpeg"), SND: ("_sc-s.mp3", b"mp3")},
        )
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            files = json.loads(z.read("media"))
            assert sorted(files.values()) == ["_sc-p.jpg", "_sc-s.mp3"]
            assert {z.read(k) for k in files} == {b"jpeg", b"mp3"}
        # The rows handed in are the page's own; they are not rewritten.
        assert d.notes[0]["Picture"] == PIC

    def test_without_media_the_package_is_as_before(self):
        d = deck()
        data = build_package("S", "D", d.plan, d.sheet_config, d.notes, now=1)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            assert z.read("media") == b"{}"


class TestAddonFetch:
    def _fetch(self, answers, media_dir=None):
        from src import media_fetch

        asked = []

        def get(url, timeout):
            asked.append(url)
            return answers.get(url)

        return media_fetch.fetch_deck_media(deck(), media_dir, get=get), asked

    def test_a_host_a_browser_could_not_read_stays_a_link(self, monkeypatch):
        from src import media_fetch

        monkeypatch.setattr(media_fetch, "_commons", lambda titles, timeout: {})
        out, _ = self._fetch(
            {PIC: ("image/jpeg", b"jpeg", "*"), SND: ("audio/mpeg", b"mp3", "")}
        )
        assert out["names"] == {PIC: media.file_name(PIC, "image")}
        assert out["links"] == 3  # the recording, and two Commons files unresolved

    def test_commons_is_fetched_from_what_the_api_named(self, monkeypatch):
        from src import media_fetch

        found = media.commons_sources([COMMONS_ANSWER])
        monkeypatch.setattr(media_fetch, "_commons", lambda titles, timeout: found)
        mp3 = found["En-us-book.ogg"]["audio"]
        out, asked = self._fetch({mp3: ("audio/mpeg", b"mp3", "")})
        assert mp3 in asked
        assert out["names"][OGG] == media.file_name(OGG, "audio")

    def test_a_file_already_in_the_collection_is_not_fetched_again(
        self, tmp_path, monkeypatch
    ):
        from src import media_fetch

        monkeypatch.setattr(media_fetch, "_commons", lambda titles, timeout: {})
        (tmp_path / media.file_name(PIC, "image")).write_bytes(b"x")
        out, asked = self._fetch({}, str(tmp_path))
        assert PIC not in asked
        assert out["names"][PIC] == media.file_name(PIC, "image")
        assert out["files"] == {}

    def test_a_file_stored_under_another_name_is_not_pointed_at(self):
        from src import media_fetch

        class Media:
            def write_data(self, name, data):
                return name if name.endswith(".jpg") else "renamed.mp3"

        class Col:
            media = Media()

        d = deck()
        names = {PIC: "_sc-p.jpg", SND: "_sc-s.mp3"}
        files = {"_sc-p.jpg": b"j", "_sc-s.mp3": b"s"}
        media_fetch.store_deck_media(Col(), d, {"files": files, "names": names})
        assert d.notes[0]["Picture"] == "_sc-p.jpg"
        assert d.notes[0]["Sound"] == SND
