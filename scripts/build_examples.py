#!/usr/bin/env python3
"""Builds ``examples/sheetcards-examples.xlsx`` — the one example the docs link.

Everything that points a person at an example points at that single file: the
README, the AnkiWeb description, the add-on's dev-only *Import Test Deck*, and the
preview site's landing page. It used to be a Google Sheet nobody working on the
add-on could edit, which is how it came to describe a schema the add-on had
outgrown with nothing in the repository able to notice.

So the sheets live here, in ``SHEETS`` below, and the workbook is generated from
them and committed beside this script. Keeping the grids as Python rather than as
a folder of TSVs means the whole tour is one readable, reviewable file: a settings
row changed in a review shows up as a changed *line*, not as a changed ZIP and not
as a diff spread over one file per sheet.

The writer is the standard library rather than openpyxl, for the same reason
``src/workbook.py`` reads with the standard library: the add-on ships with no
third-party runtime dependency, and a build step that needs one to produce the
file its own README links to is a dependency in all but name. A spreadsheet is a
ZIP of XML, and a grid of text is the small part of it.

Usage:
    python scripts/build_examples.py            # write the workbook
    python scripts/build_examples.py --check    # verify it is up to date
"""

import argparse
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape
from xml.sax.saxutils import quoteattr

REPO = Path(__file__).resolve().parent.parent
EXAMPLES = REPO / "examples"
WORKBOOK = EXAMPLES / "sheetcards-examples.xlsx"

# Media is linked at its own address rather than copied into the repository:
# every picture, recording and stroke-order animation below is a Wikimedia
# Commons file. That is also what a media column does in a real sheet — nothing
# lands in collection.media, so these cards need the network to draw.

# ---------------------------------------------------------------------------
# The tour
# ---------------------------------------------------------------------------
#
# One entry per sheet, in tab order, from the smallest sheet that works to a deck
# somebody would keep studying. Row 1 is the header row; a row whose ID cell
# starts with ``#config`` is the settings row and is read as directives rather
# than as a note.
#
# **Every sheet is a deck first and an example second.** There is no sheet that
# turns every directive on at once, and none that is wrong on purpose: both used
# to be here, and both taught the opposite of what the add-on is for. A settings
# row is a small number of decisions about one deck, so a sheet carrying fourteen
# columns of them showed nobody how to write one, and a sheet of deliberate
# mistakes made the tour end on a card that does not work.
#
# tests/test_examples.py fails if a settings-row key has no example anywhere in
# here, so a directive added to src/sheet_config.py gets a demonstration in the
# same commit rather than eventually. The place for it is the sheet whose deck
# would have wanted it — not a new column bolted onto the widest sheet.
#
# One thing here is not in English, deliberately: **the column that carries the
# meaning of a word is glossed in Vietnamese**, because that is who this workbook
# is demonstrated to. It stops there — headers, the settings row, `label=` text,
# the explanatory notes and the sheets that are documentation rather than
# vocabulary (02, 09) are all English, and a gloss is data rather than prose.

# A grid reads as a grid. One cell per line does not.
# fmt: off
SHEETS = {
    # the smallest sheet that works: an ID, a front, a back. One word per
    # language, answered in Vietnamese — the sheet is three columns wide and
    # the language it teaches is only ever the content of a cell, never a
    # setting. Nothing here knows what Korean is.
    "01 Basic (cơ bản)": [
        ["ID", "Front", "Back"],
        ["b01", "bread", "bánh mì"],
        ["b02", "水", "nước"],
        ["b03", "ねこ", "con mèo"],
        ["b04", "학교", "trường học"],
        ["b05", "das Buch", "quyển sách"],
        ["b06", "la casa", "ngôi nhà"],
    ],
    # the reserved columns — SYNC gating, the deck path, tags
    "02 Sync & subdecks (deck con)": [
        ["ID", "SYNC", "SUBDECK 1", "SUBDECK 2", "TAGS", "Question", "Answer"],
        ["s01", "yes", "Geography", "Capitals", "europe, capitals", "Capital of Portugal?", "Lisbon"],
        ["s02", "x", "Geography", "Capitals", "asia; capitals", "Capital of Vietnam?", "Hanoi"],
        ["s03", "1", "Geography", "Rivers", "rivers", "Longest river in Asia?", "The Yangtze"],
        ["s04", "TRUE", "Geography", "Rivers", "rivers, europe", "Which river flows through Paris?", "The Seine"],
        ["s05", "✓", "History", "", "history", "Who was the first Ming emperor?", "The Hongwu Emperor"],
        ["s06", "yes", "", "", "", "Where does a row with both SUBDECK cells empty go?", "Into 'Unsorted'. A sheet that sorts its rows has somewhere for the ones it did not sort."],
        ["s07", "no", "Geography", "Capitals", "capitals", "This row is switched off.", "It is never written to Anki."],
        ["s08", "", "History", "", "history", "An empty SYNC cell is off too.", "Same as 'no'."],
    ],
    # the settings row: sides, sizes, colours, weight, labels, hint
    "03 Card layout (bố cục thẻ)": [
        ["ID", "Word", "Phonetic", "Meaning", "Example", "Note", "Source"],
        ["#config align=left", "size=48px; bold", "side=front; size=22; color=accent", "size=26; color=#c2410c", "size=16; color=muted; italic; label=Example", "size=14; color=teal; align=right; hint", "side=hide"],
        ["L01", "library", "/ˈlaɪbrəri/", "thư viện", "The library is next to the school.", "British speakers often say it in two syllables.", "Oxford 3000"],
        ["L02", "airport", "/ˈeəpɔːt/", "sân bay", "We got to the airport two hours early.", "air + port, the way most compound nouns are built.", "Oxford 3000"],
        ["L03", "hospital", "/ˈhɒspɪtl/", "bệnh viện", "She works at a hospital downtown.", "In British English: in hospital, no article.", "Oxford 3000"],
        ["L04", "season", "/ˈsiːzn/", "mùa", "Autumn is my favourite season.", "Also a verb: to season food.", "Oxford 3000"],
        ["L05", "habit", "/ˈhæbɪt/", "thói quen", "Reading before bed is a good habit.", "A habit is repeated; a custom is shared by a group.", "Oxford 3000"],
        ["L06", "environment", "/ɪnˈvaɪrənmənt/", "môi trường", "The environment here is very quiet.", "Covers surroundings in general, not only nature.", "Oxford 3000"],
    ],
    # one row, both directions
    "04 Reverse (thẻ ngược)": [
        ["ID", "Vietnamese", "English", "Phonetic"],
        ["#config reverse", "size=30", "side=back; size=44", "side=back; size=20; color=muted"],
        ["r01", "đọc", "to read", "/riːd/"],
        ["r02", "viết", "to write", "/raɪt/"],
        ["r03", "nghe", "to listen", "/ˈlɪsn/"],
        ["r04", "nói", "to speak", "/spiːk/"],
        ["r05", "nhớ", "to remember", "/rɪˈmembə/"],
        ["r06", "quên", "to forget", "/fəˈɡet/"],
    ],
    # Anki's typed-answer box, diacritic-insensitive
    "05 Type the answer (gõ đáp án)": [
        ["ID", "English", "Vietnamese", "Note"],
        ["#config", "size=30", "side=back; size=32; type=nc", "size=14; color=muted"],
        ["t01", "the tree", "cái cây", "type=nc ignores the marks, so “cai cay” is counted right."],
        ["t02", "the city", "thành phố"],
        ["t03", "the heart", "trái tim"],
        ["t04", "quickly", "nhanh chóng"],
        ["t05", "the bird", "con chim"],
        ["t06", "the moon", "mặt trăng"],
        ["t07", "the mountain", "ngọn núi", "Marks are ignored, letters are not: đ is a letter and must be typed."],
        ["t08", "the river", "con sông"],
    ],
    # a declared cloze column, including a row with two deletions
    "06 Cloze (điền chỗ trống)": [
        ["ID", "Sentence", "Meaning", "Note"],
        ["#config", "cloze; size=28", "size=18", "size=14; color=muted; hint"],
        ["z01", "She has {{c1::been}} living here for ten years.", "Cô ấy sống ở đây mười năm rồi.", "Present perfect continuous: has been + -ing."],
        ["z02", "I {{c1::have}} never been to Japan, and neither {{c2::has}} she.", "Tôi chưa từng đến Nhật, cô ấy cũng vậy.", "Two deletions make two cards from one row."],
        ["z03", "The letter was written {{c1::by}} my grandmother.", "Bức thư do bà tôi viết.", "In the passive, by introduces who did it."],
        ["z04", "If it rains, we {{c1::will}} stay at home.", "Nếu trời mưa thì chúng tôi ở nhà.", "First conditional: if + present, will + verb."],
        ["z05", "This film is {{c1::more}} interesting than the last one.", "Phim này hay hơn phim trước.", "Long adjectives take more, not -er."],
        ["z06", "I used {{c1::to}} walk to school every day.", "Hồi trước ngày nào tôi cũng đi bộ đến trường.", "used to + bare verb, for a past habit that stopped."],
    ],
    # a column holding a picture URL
    "07 Images (hình ảnh)": [
        ["ID", "Picture", "Word", "Pinyin", "Meaning"],
        ["#config", "image; size=320", "side=back; size=44", "side=back; size=22; color=accent", "side=back; size=18; color=muted"],
        ["p01", "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3c/Giant_Panda_2004-03-2.jpg/500px-Giant_Panda_2004-03-2.jpg", "熊猫", "xióngmāo", "gấu trúc"],
        ["p02", "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Green_tea_3_appearances.jpg/500px-Green_tea_3_appearances.jpg", "茶", "chá", "trà"],
        ["p03", "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/Great_Wall_of_China_July_2006.JPG/500px-Great_Wall_of_China_July_2006.JPG", "长城", "Chángchéng", "Vạn Lý Trường Thành"],
        ["p04", "https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/Terracotta_Army_Pit_1_-_2.jpg/500px-Terracotta_Army_Pit_1_-_2.jpg", "兵马俑", "bīngmǎyǒng", "đội quân đất nung"],
        ["p05", "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d1/Mount_Everest_as_seen_from_Drukair2_PLW_edit.jpg/500px-Mount_Everest_as_seen_from_Drukair2_PLW_edit.jpg", "山", "shān", "núi"],
    ],
    # a column holding a recording
    "08 Audio (âm thanh)": [
        ["ID", "Recording", "Word", "Phonetic", "Meaning"],
        ["#config", "audio; label=Listen", "side=back; size=44", "side=back; size=22; color=accent", "side=back; size=18; color=muted"],
        ["a01", "https://commons.wikimedia.org/wiki/Special:FilePath/En-us-book.ogg", "book", "/bʊk/", "quyển sách"],
        ["a02", "https://commons.wikimedia.org/wiki/Special:FilePath/En-us-bread.ogg", "bread", "/bred/", "bánh mì"],
        ["a03", "https://commons.wikimedia.org/wiki/Special:FilePath/En-us-tree.ogg", "tree", "/triː/", "cái cây"],
        ["a04", "https://commons.wikimedia.org/wiki/Special:FilePath/En-us-river.ogg", "river", "/ˈrɪvə/", "con sông"],
        ["a05", "https://commons.wikimedia.org/wiki/Special:FilePath/En-us-city.ogg", "city", "/ˈsɪti/", "thành phố"],
        ["a06", "https://commons.wikimedia.org/wiki/Special:FilePath/En-us-night.ogg", "night", "/naɪt/", "ban đêm"],
        ["a07", "https://commons.wikimedia.org/wiki/Special:FilePath/En-us-music.ogg", "music", "/ˈmjuːzɪk/", "âm nhạc"],
        ["a08", "https://commons.wikimedia.org/wiki/Special:FilePath/En-us-teacher.ogg", "teacher", "/ˈtiːtʃə/", "giáo viên"],
    ],
    # every link form the add-on rewrites into a player
    "09 Video (video nhúng)": [
        ["ID", "Question", "Clip", "Answer"],
        ["#config", "size=26", "side=back; video; label=Watch the clip; hint", "size=18"],
        ["v01", "A full YouTube watch link.", "https://www.youtube.com/watch?v=jNQXAC9IVRw", "Rewritten to https://www.youtube.com/embed/… before the note is saved."],
        ["v02", "A youtu.be short link.", "https://youtu.be/aircAruvnKk", "Same rewrite — the id is what matters, not the host."],
        ["v03", "A Shorts link.", "https://www.youtube.com/shorts/5MgBikgcWnY", "/shorts/, /live/ and /v/ are all recognised."],
        ["v04", "A link that is already an embed link.", "https://www.youtube.com/embed/jNQXAC9IVRw", "The rewrite is idempotent — it is left alone."],
        ["v05", "A direct video file, not a page.", "https://upload.wikimedia.org/wikipedia/commons/d/de/Ink_grinding.webmhd.webm", "Passed through unchanged; the frame plays the file itself."],
    ],
    # text-to-speech: a voice preference, deck-wide speed, a per-column
    # override, and a column that is heard without being read
    "10 Speech (đọc thành tiếng)": [
        ["ID", "English", "Phonetic", "Vietnamese", "Once more, slowly"],
        ["#config speed=0.9", "size=34; tts=en_US; voices=Samantha,Microsoft Zira", "size=22; color=accent", "size=20", "side=hide; tts=en_US; speed=0.5"],
        ["k01", "Good morning.", "/ɡʊd ˈmɔːnɪŋ/", "chào buổi sáng", "Good morning."],
        ["k02", "Thank you for your help.", "/θæŋk juː fə jɔː help/", "cảm ơn bạn đã giúp đỡ", "Thank you for your help."],
        ["k03", "Could you say that again?", "/kʊd juː seɪ ðæt əˈɡen/", "bạn nói lại được không?", "Could you say that again?"],
        ["k04", "I do not understand.", "/aɪ duː nɒt ˌʌndəˈstænd/", "tôi không hiểu", "I do not understand."],
        ["k05", "How much is it?", "/haʊ mʌtʃ ɪz ɪt/", "cái này bao nhiêu tiền?", "How much is it?"],
        ["k06", "Where is the bathroom?", "/weər ɪz ðə ˈbɑːθruːm/", "nhà vệ sinh ở đâu?", "Where is the bathroom?"],
    ],
    # write the character; a column that files the note without reaching the card
    "11 Chinese writing (gõ chữ)": [
        ["ID", "TAGS", "Level", "Meaning", "Pinyin", "Hanzi", "Strokes", "Example"],
        ["#config", "", "subdeck=1", "side=front; size=24; color=muted; label=Write the character for", "side=front; size=40; color=accent", "side=back; size=90; type; tts=zh_CN; font=sc; sort", "side=back; image; size=200; hint; label=Stroke order", "side=back; size=18; tts=zh_CN; speed=0.8"],
        ["w01", "hanzi, hsk1", "HSK 1", "tôi", "wǒ", "我", "https://upload.wikimedia.org/wikipedia/commons/b/b3/%E6%88%91-order.gif", "我是学生。"],
        ["w02", "hanzi, hsk1", "HSK 1", "bạn", "nǐ", "你", "https://upload.wikimedia.org/wikipedia/commons/e/ee/%E4%BD%A0-order.gif", "你好吗？"],
        ["w03", "hanzi, hsk1", "HSK 1", "tốt; khỏe", "hǎo", "好", "https://upload.wikimedia.org/wikipedia/commons/6/6e/%E5%A5%BD-order.gif", "今天天气很好。"],
        ["w04", "hanzi, hsk1", "HSK 1", "là", "shì", "是", "https://upload.wikimedia.org/wikipedia/commons/4/4f/%E6%98%AF-order.gif", "他是老师。"],
        ["w05", "hanzi, hsk1", "HSK 1", "người", "rén", "人", "https://upload.wikimedia.org/wikipedia/commons/f/fd/%E4%BA%BA-order.gif", "那个人很高。"],
        ["w06", "hanzi, hsk1", "HSK 1", "to; lớn", "dà", "大", "https://upload.wikimedia.org/wikipedia/commons/9/9c/%E5%A4%A7-order.gif", "这个房子很大。"],
        ["w07", "hanzi, hsk1", "HSK 1", "nhỏ", "xiǎo", "小", "https://upload.wikimedia.org/wikipedia/commons/d/de/%E5%B0%8F-order.gif", "小狗在门口。"],
        ["w08", "hanzi, hsk1", "HSK 1", "nước", "shuǐ", "水", "https://upload.wikimedia.org/wikipedia/commons/4/42/%E6%B0%B4-order.gif", "我想喝水。"],
        ["w09", "hanzi, hsk1", "HSK 1", "học", "xué", "学", "https://upload.wikimedia.org/wikipedia/commons/f/f9/%E5%AD%A6-order.gif", "我在学中文。"],
        ["w10", "hanzi, hsk1", "HSK 1", "yêu", "ài", "爱", "https://upload.wikimedia.org/wikipedia/commons/d/d8/%E7%88%B1-order.gif", "我爱我的家人。"],
        ["w11", "hanzi, hsk1", "HSK 1", "trời; ngày", "tiān", "天", "https://upload.wikimedia.org/wikipedia/commons/a/ab/%E5%A4%A9-order.gif", "明天见。"],
        ["w12", "hanzi, hsk1", "HSK 1", "trăng; tháng", "yuè", "月", "https://upload.wikimedia.org/wikipedia/commons/9/92/%E6%9C%88-order.gif", "下个月我去中国。"],
        ["w13", "hanzi, hsk1", "HSK 1", "nhà; gia đình", "jiā", "家", "https://upload.wikimedia.org/wikipedia/commons/5/57/%E5%AE%B6-order.gif", "我家有四个人。"],
        ["w14", "hanzi, hsk1", "HSK 1", "giữa; Trung Quốc", "zhōng", "中", "https://upload.wikimedia.org/wikipedia/commons/8/8a/%E4%B8%AD-order.gif", "他在中国工作。"],
        ["w15", "hanzi, hsk1", "HSK 1", "nước; quốc gia", "guó", "国", "https://upload.wikimedia.org/wikipedia/commons/8/80/%E5%9B%BD-order.gif", "你是哪国人？"],
        ["w16", "hanzi, hsk1", "HSK 1", "xe", "chē", "车", "https://upload.wikimedia.org/wikipedia/commons/b/b0/%E8%BD%A6-order.gif", "我的车坏了。"],
        ["w17", "hanzi, hsk2", "HSK 2", "núi", "shān", "山", "https://upload.wikimedia.org/wikipedia/commons/1/14/%E5%B1%B1-order.gif", "山上有雪。"],
        ["w18", "hanzi, hsk2", "HSK 2", "mặt trời; ngày", "rì", "日", "https://upload.wikimedia.org/wikipedia/commons/f/f6/%E6%97%A5-order.gif", "今日很热。"],
        ["w19", "hanzi, hsk2", "HSK 2", "lửa", "huǒ", "火", "https://upload.wikimedia.org/wikipedia/commons/c/c5/%E7%81%AB-order.gif", "火车快到了。"],
        ["w20", "hanzi, hsk2", "HSK 2", "miệng; cửa", "kǒu", "口", "https://upload.wikimedia.org/wikipedia/commons/3/3c/%E5%8F%A3-order.gif", "门口有人在等。"],
        ["w21", "hanzi, hsk2", "HSK 2", "tay", "shǒu", "手", "https://upload.wikimedia.org/wikipedia/commons/a/a1/%E6%89%8B-order.gif", "请举手。"],
        ["w22", "hanzi, hsk2", "HSK 2", "tim; lòng", "xīn", "心", "https://upload.wikimedia.org/wikipedia/commons/0/0a/%E5%BF%83-order.gif", "谢谢你的关心。"],
        ["w23", "hanzi, hsk2", "HSK 2", "ngựa", "mǎ", "马", "https://upload.wikimedia.org/wikipedia/commons/e/e3/%E9%A9%AC-order.gif", "马跑得很快。"],
        ["w24", "hanzi, hsk3", "HSK 3", "gỗ; cây", "mù", "木", "https://upload.wikimedia.org/wikipedia/commons/f/fb/%E6%9C%A8-order.gif", "这张桌子是木头做的。"],
        ["w25", "hanzi, hsk3", "HSK 3", "ruộng", "tián", "田", "https://upload.wikimedia.org/wikipedia/commons/b/bb/%E7%94%B0-order.gif", "田里有很多水。"],
    ],
    # write the character yourself, stroke by stroke, and be marked on it
    "12 Chinese drawing (viết tay)": [
        ["ID", "SUBDECK 1", "TAGS", "Meaning", "Pinyin", "Draw", "Character", "Example"],
        ["#config", "", "", "size=24; color=muted; label=Draw the character for", "side=front; size=40; color=accent", "side=front; draw; size=260", "side=back; size=72; tts=zh_CN", "side=back; size=18; tts=zh_CN; speed=0.8"],
        ["d01", "HSK 1", "hanzi, hsk1, draw", "tôi", "wǒ", "我", "我", "我是学生。"],
        ["d02", "HSK 1", "hanzi, hsk1, draw", "bạn", "nǐ", "你", "你", "你好吗？"],
        ["d03", "HSK 1", "hanzi, hsk1, draw", "tốt; khỏe", "hǎo", "好", "好", "今天天气很好。"],
        ["d04", "HSK 1", "hanzi, hsk1, draw", "người", "rén", "人", "人", "那个人很高。"],
        ["d05", "HSK 1", "hanzi, hsk1, draw", "to; lớn", "dà", "大", "大", "这个房子很大。"],
        ["d06", "HSK 1", "hanzi, hsk1, draw", "nhỏ", "xiǎo", "小", "小", "小狗在门口。"],
        ["d07", "HSK 1", "hanzi, hsk1, draw", "nước", "shuǐ", "水", "水", "我想喝水。"],
        ["d08", "HSK 1", "hanzi, hsk1, draw", "học", "xué", "学", "学", "我在学中文。"],
        ["d09", "HSK 1", "hanzi, hsk1, draw", "trời; ngày", "tiān", "天", "天", "明天见。"],
        ["d10", "HSK 2", "hanzi, hsk2, draw", "núi", "shān", "山", "山", "山上有雪。"],
        ["d11", "HSK 2", "hanzi, hsk2, draw", "lửa", "huǒ", "火", "火", "火车快到了。"],
        ["d12", "HSK 2", "hanzi, hsk2, draw", "miệng; cửa", "kǒu", "口", "口", "门口有人在等。"],
    ],
    # readings rendered as ruby over the kanji
    "13 Furigana (phiên âm kanji)": [
        ["ID", "Japanese", "Meaning", "Note"],
        ["#config", "size=40; furigana; tts=ja_JP", "size=20", "size=14; color=muted; hint"],
        ["f01", "日本語[にほんご]", "tiếng Nhật", "Write the reading in brackets after the kanji."],
        ["f02", "図書館[としょかん]", "thư viện"],
        ["f03", " 私[わたし]は 学生[がくせい]です。", "Tôi là học sinh.", "A leading space separates one reading from the previous word."],
        ["f04", "新[あたら]しい 本[ほん]", "một quyển sách mới"],
        ["f05", "駅[えき]まで 歩[ある]きます。", "Tôi đi bộ đến ga."],
        ["f06", "先生[せんせい]の 話[はなし]", "câu chuyện của thầy giáo"],
    ],
    # the sheet decides the schema, in any script
    "14 Any headers (mọi ngôn ngữ)": [
        ["ID", "汉字", "拼音", "释义", "例句"],
        ["#config", "size=44; tts=zh_CN", "size=22; color=accent", "size=20", "size=16; color=muted"],
        ["h01", "词典", "cídiǎn", "từ điển", "我买了一本新词典。"],
        ["h02", "练习", "liànxí", "luyện tập; bài tập", "每天练习写汉字。"],
        ["h03", "翻译", "fānyì", "dịch; phiên dịch viên", "他是一位翻译。"],
        ["h04", "笔画", "bǐhuà", "nét (của chữ Hán)", "“我”有七个笔画。"],
        ["h05", "部首", "bùshǒu", "bộ thủ", "这个字的部首是“水”。"],
        ["h06", "声调", "shēngdiào", "thanh điệu", "普通话有四个声调。"],
    ],
    # a whole-card palette, and a deck filed three levels deep: English vocabulary
    # by CEFR level and word class, in the colours of the season the theme is named
    # after. Nothing here is the end of anything — it is the sheet that demonstrates
    # `theme=` and a three-level `SUBDECK`, and the widest one, which is why the
    # preview site opens on it.
    "15 Theme + subdeck (màu, tầng)": [
        ["ID", "SUBDECK 1", "SUBDECK 2", "SUBDECK 3", "TAGS", "Word", "Phonetic", "Meaning", "Example"],
        ["#config theme=sakura", "", "", "", "", "size=44; bold; tts=en_US; sort", "side=back; size=20; color=accent", "side=back; size=22", "side=back; size=16; color=muted; italic; tts=en_US; speed=0.85"],
        ["n01", "English", "B1", "Verbs", "cefr, b1", "to afford", "/əˈfɔːd/", "đủ tiền để mua", "We cannot afford a bigger flat this year."],
        ["n02", "English", "B1", "Verbs", "cefr, b1", "to complain", "/kəmˈpleɪn/", "phàn nàn", "She complained about the noise upstairs."],
        ["n03", "English", "B1", "Verbs", "cefr, b1", "to improve", "/ɪmˈpruːv/", "cải thiện", "His English improved after a year in Leeds."],
        ["n04", "English", "B1", "Verbs", "cefr, b1", "to suggest", "/səˈdʒest/", "gợi ý, đề nghị", "I suggest leaving before the traffic starts."],
        ["n05", "English", "B1", "Nouns", "cefr, b1", "advice", "/ədˈvaɪs/", "lời khuyên", "She gave me some good advice."],
        ["n06", "English", "B1", "Nouns", "cefr, b1", "journey", "/ˈdʒɜːni/", "chuyến đi", "The journey takes about four hours."],
        ["n07", "English", "B1", "Nouns", "cefr, b1", "neighbour", "/ˈneɪbə/", "hàng xóm", "Our neighbour looks after the cat."],
        ["n08", "English", "B1", "Adjectives", "cefr, b1", "crowded", "/ˈkraʊdɪd/", "đông đúc", "The market is crowded on Sunday mornings."],
        ["n09", "English", "B1", "Adjectives", "cefr, b1", "reliable", "/rɪˈlaɪəbl/", "đáng tin cậy", "He is the most reliable person on the team."],
        ["n10", "English", "B2", "Verbs", "cefr, b2", "to acknowledge", "/əkˈnɒlɪdʒ/", "thừa nhận", "She acknowledged that the plan had failed."],
        ["n11", "English", "B2", "Verbs", "cefr, b2", "to postpone", "/pəˈspəʊn/", "hoãn lại", "They postponed the concert until March."],
        ["n12", "English", "B2", "Nouns", "cefr, b2", "assumption", "/əˈsʌmpʃn/", "giả định", "The whole plan rests on one assumption."],
        ["n13", "English", "B2", "Nouns", "cefr, b2", "consequence", "/ˈkɒnsɪkwəns/", "hậu quả", "Nobody thought about the consequences."],
        ["n14", "English", "B2", "Adjectives", "cefr, b2", "thorough", "/ˈθʌrə/", "kỹ lưỡng", "The report was thorough and easy to read."],
        ["n15", "English", "B2", "Adjectives", "cefr, b2", "reluctant", "/rɪˈlʌktənt/", "miễn cưỡng", "He was reluctant to answer the question."],
    ],
    # a picture and a recording on the same card: see the thing, then hear the
    # word for it. The two media kinds are one column each, because a column holds
    # one kind — and `Group` files the note without ever reaching the card.
    "16 Picture words (từ vựng ảnh)": [
        ["ID", "Group", "Picture", "Word", "Sound", "Meaning", "Example"],
        ["#config", "subdeck=1", "side=front; image; size=300", "side=back; size=44; bold", "side=back; audio; label=Native recording", "side=back; size=20", "side=back; size=16; color=muted; italic; hint"],
        ["i01", "Animals", "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/Cat_November_2010-1a.jpg/500px-Cat_November_2010-1a.jpg", "cat", "https://commons.wikimedia.org/wiki/Special:FilePath/En-us-cat.ogg", "con mèo", "The cat is asleep on the chair."],
        ["i02", "Animals", "https://upload.wikimedia.org/wikipedia/commons/thumb/1/17/Tiger_in_Ranthambhore.jpg/500px-Tiger_in_Ranthambhore.jpg", "tiger", "https://commons.wikimedia.org/wiki/Special:FilePath/En-us-tiger.ogg", "con hổ", "A tiger hunts alone."],
        ["i03", "Animals", "https://upload.wikimedia.org/wikipedia/commons/thumb/9/98/Horse-and-pony.jpg/500px-Horse-and-pony.jpg", "horse", "https://commons.wikimedia.org/wiki/Special:FilePath/En-us-horse.ogg", "con ngựa", "She rides a horse every weekend."],
        ["i04", "Food and drink", "https://upload.wikimedia.org/wikipedia/commons/thumb/1/15/Red_Apple.jpg/500px-Red_Apple.jpg", "apple", "https://commons.wikimedia.org/wiki/Special:FilePath/En-us-apple.ogg", "quả táo", "An apple a day is an old English saying."],
        ["i05", "Nature", "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Full_Moon_Luc_Viatour.jpg/500px-Full_Moon_Luc_Viatour.jpg", "moon", "https://commons.wikimedia.org/wiki/Special:FilePath/En-us-moon.ogg", "mặt trăng", "The moon is full tonight."],
        ["i06", "Nature", "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Fire.JPG/500px-Fire.JPG", "fire", "https://commons.wikimedia.org/wiki/Special:FilePath/En-us-fire.ogg", "lửa", "They built a fire on the beach."],
    ],
    # draw the character *and* type its reading: the writing box marks the strokes,
    # Anki's own box marks what was typed. Two ways of being asked one thing.
    "17 Draw & type (viết và gõ)": [
        ["ID", "Level", "Meaning", "Draw", "Pinyin", "Character", "Example"],
        ["#config", "subdeck=1", "side=front; size=26; color=muted; label=Draw it, then type the pinyin", "side=front; draw; size=240", "side=back; size=26; color=accent; type=nc", "side=back; size=64; tts=zh_CN", "side=back; size=16; color=muted; italic"],
        ["q01", "HSK 1", "sách", "书", "shū", "书", "我在看书。"],
        ["q02", "HSK 1", "cơm; bữa ăn", "饭", "fàn", "饭", "该吃饭了。"],
        ["q03", "HSK 1", "nhà", "家", "jiā", "家", "我在家工作。"],
        ["q04", "HSK 1", "nói", "说", "shuō", "说", "请说慢一点。"],
        ["q05", "HSK 1", "nghe", "听", "tīng", "听", "我在听音乐。"],
        ["q06", "HSK 2", "đường phố", "路", "lù", "路", "这条路很长。"],
        ["q07", "HSK 2", "trà", "茶", "chá", "茶", "我想喝茶。"],
        ["q08", "HSK 2", "mưa", "雨", "yǔ", "雨", "今天下雨了。"],
    ],
    # a grammar point with the word that carries it deleted, and the deletion typed
    # rather than recalled: `type` on the cloze column becomes {{type:cloze:…}}.
    "18 Grammar cloze (ngữ pháp)": [
        ["ID", "Point", "Sentence", "Meaning", "Note"],
        ["#config", "side=front; size=15; color=muted; label=Grammar point", "cloze; type; size=28", "side=back; size=20", "side=back; size=15; color=muted; hint"],
        ["g01", "Present perfect", "I have {{c1::lived}} in this city since 2019.", "Tôi sống ở thành phố này từ năm 2019.", "since + a point in time; for + a length of time."],
        ["g02", "Articles", "She plays {{c1::the}} piano every evening.", "Tối nào cô ấy cũng chơi piano.", "Instruments take the; sports take nothing at all."],
        ["g03", "Comparatives", "Today is {{c1::hotter}} than yesterday.", "Hôm nay nóng hơn hôm qua.", "Short adjectives take -er, and the consonant doubles."],
        ["g04", "Passive", "The bridge {{c1::was}} built in 1890.", "Cây cầu được xây năm 1890.", "be + past participle, when who did it does not matter."],
        ["g05", "Reported speech", "He said he {{c1::was}} tired.", "Anh ấy nói anh ấy mệt.", "The tense steps back one when the sentence is reported."],
        ["g06", "Prepositions", "We arrived {{c1::at}} the station at six.", "Chúng tôi đến ga lúc sáu giờ.", "arrive at a place, arrive in a city or a country."],
        ["g07", "Used to", "There {{c1::used}} to be a cinema on this corner.", "Ở góc này trước kia có một rạp chiếu phim.", "For something that was true once and is not now."],
    ],
    # heard, not seen: the sentence is spoken on the question and drawn nowhere, so
    # the only way to answer is to listen. `side=hide` with `tts` and `type`.
    "19 Dictation (nghe rồi gõ)": [
        ["ID", "Sentence", "Task", "Meaning"],
        ["#config", "side=hide; tts=en_US; speed=0.85; type", "side=front; size=18; color=muted", "side=back; size=20"],
        ["y01", "My name is Mai and I live in Hanoi", "Listen, then type the sentence in English.", "Tôi tên là Mai và tôi sống ở Hà Nội."],
        ["y02", "The weather is very nice today", "Listen, then type the sentence in English.", "Hôm nay thời tiết rất đẹp."],
        ["y03", "I would like a cup of coffee please", "Listen, then type the sentence in English.", "Cho tôi một tách cà phê."],
        ["y04", "This book belongs to my sister", "Listen, then type the sentence in English.", "Quyển sách này là của chị tôi."],
        ["y05", "He takes the train to work every morning", "Listen, then type the sentence in English.", "Sáng nào anh ấy cũng đi làm bằng tàu."],
        ["y06", "Could you tell me where the station is", "Listen, then type the sentence in English.", "Bạn chỉ giúp tôi ga ở đâu được không?"],
    ],
    # the clip is the question: watch it, then answer. A video on the front rather
    # than tucked behind a link on the back, filed by lesson.
    "20 Video lesson (bài video)": [
        ["ID", "Lesson", "Clip", "Question", "Answer"],
        ["#config", "subdeck=1", "side=front; video; size=520", "side=front; size=22", "side=back; size=20"],
        ["c01", "Lesson 1", "https://www.youtube.com/watch?v=jNQXAC9IVRw", "Where are the speakers standing?", "In front of the elephant enclosure at the zoo."],
        ["c02", "Lesson 1", "https://youtu.be/aircAruvnKk", "What is the subject of this lecture?", "How a neural network is put together."],
        ["c03", "Lesson 2", "https://upload.wikimedia.org/wikipedia/commons/d/de/Ink_grinding.webmhd.webm", "What is being ground on the stone?", "An ink stick, ground with water to make ink."],
    ],
    # a formula and a listing, the two kinds of cell that are not prose: MathJax
    # is already inside Anki, and the colouring is a library the card loads.
    "21 Formulas & code (công thức)": [
        ["ID", "Topic", "Question", "Formula", "Snippet", "Note"],
        ["#config", "side=front; size=15; color=muted; label=Topic", "side=front; size=24; sort", "side=back; size=26; math=block", "side=back; code=python", "side=back; size=15; color=muted; hint"],
        ["m01", "Geometry", "The area of a circle of radius r", "A = \\pi r^2", "", "The constant is the ratio of any circle's circumference to its diameter."],
        ["m02", "Algebra", "The quadratic formula", "x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a}", "", "The part under the root is the discriminant; its sign counts the roots."],
        ["m03", "Physics", "Einstein's mass–energy equivalence", "E = mc^2", "", "c is the speed of light, so a very small mass is a very large energy."],
        ["m04", "Statistics", "The mean of n observations", "\\bar{x} = \\frac{1}{n}\\sum_{i=1}^{n} x_i", "", "Sum them, divide by how many there were."],
        ["m05", "Python", "Reverse a string", "", "def backwards(text):\n    return text[::-1]", "A slice with a step of -1 walks the string from the end."],
        ["m06", "Python", "Count how often each item appears", "", "from collections import Counter\n\ncounts = Counter(words)\nprint(counts.most_common(3))", "Counter is a dict that starts every key at zero."],
        ["m07", "SQL", "Rows in one table with no match in another", "", "SELECT c.name\nFROM customers c\nLEFT JOIN orders o ON o.customer_id = c.id\nWHERE o.id IS NULL", "A left join keeps every left row; the null is what says there was no match."],
    ],
    # right to left, which is a direction no amount of styling can fake
    "22 Arabic (phải sang trái)": [
        ["ID", "Arabic", "Transliteration", "Meaning", "Note"],
        ["#config", "rtl; size=44; font=serif; sort", "side=back; size=20; color=accent", "side=back; size=20", "side=back; size=14; color=muted; hint"],
        ["b01", "مرحبا", "marḥaban", "xin chào", "The everyday greeting, usable at any hour."],
        ["b02", "كتاب", "kitāb", "quyển sách", "Same root as maktaba, a library or bookshop."],
        ["b03", "ماء", "māʼ", "nước", "The last letter is a hamza, written on a seat here."],
        ["b04", "بيت", "bayt", "ngôi nhà", "Also a line of verse — a house of poetry."],
        ["b05", "مدرسة", "madrasa", "trường học", "Literally a place of study."],
        ["b06", "شكرا", "shukran", "cảm ơn", "Answered with ʿafwan, you are welcome."],
    ],
    # top to bottom, right to left: how Japanese is set in a book
    "23 Vertical text (viết dọc)": [
        ["ID", "Japanese", "Reading", "Meaning"],
        ["#config", "vertical; font=jp; size=30; sort", "side=back; size=18; color=accent", "side=back; size=20"],
        ["t01", "古池や蛙飛びこむ水の音", "ふるいけやかわずとびこむみずのおと", "Ao xưa, ếch nhảy vào, tiếng nước khẽ vang."],
        ["t02", "夏草や兵どもが夢の跡", "なつくさやつわものどもがゆめのあと", "Cỏ mùa hè — dấu vết giấc mộng của những người lính."],
        ["t03", "秋深き隣は何をする人ぞ", "あきふかきとなりはなにをするひとぞ", "Thu đã sâu — người bên cạnh làm nghề gì nhỉ?"],
        ["t04", "山は静かです", "やまはしずかです", "Núi thì yên tĩnh."],
        ["t05", "本を読みます", "ほんをよみます", "Tôi đọc sách."],
    ],
    # a script of its own, and a voice of its own
    "24 Korean (tiếng Hàn)": [
        ["ID", "Korean", "Romanisation", "Meaning", "Example"],
        ["#config", "font=kr; size=44; tts=ko_KR; sort", "side=back; size=20; color=accent", "side=back; size=20", "side=back; size=16; color=muted; italic"],
        ["h01", "학교", "hakgyo", "trường học", "저는 학교에 갑니다."],
        ["h02", "친구", "chingu", "bạn bè", "친구를 만났어요."],
        ["h03", "음식", "eumsik", "món ăn", "한국 음식을 좋아해요."],
        ["h04", "감사합니다", "gamsahamnida", "cảm ơn", "도와주셔서 감사합니다."],
        ["h05", "물", "mul", "nước", "물 한 잔 주세요."],
        ["h06", "시간", "sigan", "thời gian", "시간이 없어요."],
        ["h07", "책", "chaek", "quyển sách", "이 책은 재미있어요."],
        ["h08", "지하철", "jihacheol", "tàu điện ngầm", "지하철로 회사에 가요."],
    ],
    # the same word in two scripts, which is what a Taiwan-bound learner needs
    "25 Traditional (chữ phồn thể)": [
        ["ID", "Traditional", "Simplified", "Pinyin", "Meaning"],
        ["#config", "font=tc; size=48; tts=zh_TW; sort", "side=back; size=36; font=sc; color=muted; label=Simplified", "side=back; size=22; color=accent", "side=back; size=20"],
        ["f01", "學習", "学习", "xuéxí", "học tập"],
        ["f02", "電腦", "电脑", "diànnǎo", "máy tính"],
        ["f03", "圖書館", "图书馆", "túshūguǎn", "thư viện"],
        ["f04", "臺灣", "台湾", "Táiwān", "Đài Loan"],
        ["f05", "醫生", "医生", "yīshēng", "bác sĩ"],
        ["f06", "餐廳", "餐厅", "cāntīng", "nhà hàng"],
        ["f07", "開車", "开车", "kāichē", "lái xe"],
        ["f08", "銀行", "银行", "yínháng", "ngân hàng"],
    ],
    # a deck for the terminal: the answer is a command, and a command is code
    "26 Shell commands (dòng lệnh)": [
        ["ID", "Group", "Task", "Command", "Note"],
        ["#config", "subdeck=1", "side=front; size=24; sort", "side=back; code=bash", "side=back; size=15; color=muted; hint"],
        ["s01", "Files", "List every file, including the hidden ones", "ls -la", "The dot files are configuration; ls hides them by default."],
        ["s02", "Files", "Find every .log file under this directory", "find . -name '*.log'", "The quotes stop the shell expanding the pattern before find sees it."],
        ["s03", "Text", "Count the lines that contain a word", "grep -c 'error' app.log", "-c counts matching lines, not matches: two on one line is one."],
        ["s04", "Text", "Show the last twenty lines and keep following the file", "tail -n 20 -f app.log", "-f holds the file open, which is how you watch a log live."],
        ["s05", "Processes", "See what is listening on port 8000", "lsof -i :8000", "The command for the moment something says the address is in use."],
        ["s06", "Git", "Undo the last commit but keep the changes", "git reset --soft HEAD~1", "--soft keeps the work staged; --hard would throw it away."],
        ["s07", "Git", "See what changed in one file over time", "git log -p -- src/app.py", "-p prints the patch of every commit that touched the path."],
        ["s08", "Archives", "Unpack a .tar.gz into a directory", "tar -xzf release.tar.gz -C build/", "x extracts, z is gzip, f names the file, -C says where to put it."],
    ],
    # two languages on one card, both kept exactly as they were typed
    "27 Web dev (HTML & JS)": [
        ["ID", "Question", "Markup", "Script", "Note"],
        ["#config", "side=front; size=22; sort", "side=back; code=html", "side=back; code=javascript", "side=back; size=15; color=muted; hint"],
        ["w01", "How is a form field tied to its label?", "<label for=\"email\">Email</label>\n<input id=\"email\" type=\"email\">", "", "The for attribute matches the input's id, which is what makes the label clickable."],
        ["w02", "What does defer do on a script tag?", "<script src=\"app.js\" defer></script>", "", "The file downloads in parallel and runs after the document is parsed, in order."],
        ["w03", "How do you copy text to the clipboard?", "", "await navigator.clipboard.writeText('hello');", "Only inside a user gesture, and only on https or localhost."],
        ["w04", "How is a list built without innerHTML?", "", "const ul = document.createElement('ul');\nfor (const item of items) {\n  const li = document.createElement('li');\n  li.textContent = item;\n  ul.append(li);\n}", "textContent cannot execute anything; innerHTML with user text can."],
        ["w05", "How do you wait for an element to appear?", "", "new MutationObserver((_, obs) => {\n  const found = document.querySelector('.ready');\n  if (found) { obs.disconnect(); use(found); }\n}).observe(document.body, { childList: true, subtree: true });", "An observer costs nothing while nothing changes; a setInterval costs something forever."],
    ],
    # an equation is the answer, and it is set on a line of its own
    "28 Chemistry (hoá học)": [
        ["ID", "Topic", "Question", "Answer", "Equation", "Note"],
        ["#config", "subdeck=1", "side=front; size=22; sort", "side=back; size=20", "side=back; size=24; math=block", "side=back; size=15; color=muted; hint"],
        ["c01", "Reactions", "What does hydrogen burning in oxygen make?", "Nước.", "2H_2 + O_2 \\rightarrow 2H_2O", "Balanced: the same atoms come out as went in."],
        ["c02", "Reactions", "What does an acid and a base make?", "Muối và nước.", "HCl + NaOH \\rightarrow NaCl + H_2O", "Neutralisation — the pH moves toward 7."],
        ["c03", "Quantities", "How many particles are in one mole?", "Khoảng 6,022 × 10²³ hạt.", "N_A = 6.022 \\times 10^{23}\\ \\mathrm{mol^{-1}}", "Avogadro's number is a count, not a mass."],
        ["c04", "Quantities", "How do you find the amount of a substance?", "Lấy khối lượng chia cho khối lượng mol.", "n = \\frac{m}{M}", "n in moles, m in grams, M in grams per mole."],
        ["c05", "Gases", "What is the ideal gas law?", "Áp suất nhân thể tích bằng số mol nhân R nhân nhiệt độ.", "pV = nRT", "T is in kelvin, always — the law means nothing in celsius."],
        ["c06", "Solutions", "How is molar concentration defined?", "Số mol chất tan chia cho thể tích dung dịch.", "c = \\frac{n}{V}", "V is the volume of the solution, not of the solvent."],
    ],
    # the shape of English that is hardest to look up: a verb plus its particle
    "29 Phrasal verbs (cụm động từ)": [
        ["ID", "Sentence", "Meaning", "Note"],
        ["#config", "cloze; size=26; tts=en_US; sort", "side=back; size=20", "side=back; size=15; color=muted; hint"],
        ["v01", "I need to {{c1::look after}} my little brother tonight.", "trông nom, chăm sóc", "Take care of. The particle cannot move: never look my brother after."],
        ["v02", "She {{c1::gave up}} smoking two years ago.", "từ bỏ", "Give up + -ing, never give up to smoke."],
        ["v03", "We had to {{c1::put off}} the meeting until Friday.", "hoãn lại", "Postpone. This one does split: put the meeting off."],
        ["v04", "He {{c1::ran into}} an old friend at the station.", "tình cờ gặp", "Met by chance — nobody planned it."],
        ["v05", "Please {{c1::fill in}} this form before you leave.", "điền vào", "British fill in, American fill out, the same form."],
        ["v06", "The car {{c1::broke down}} on the motorway.", "hỏng, chết máy", "Of a machine. Of a person it means to weep."],
        ["v07", "I will {{c1::look it up}} in the dictionary.", "tra cứu", "With a pronoun the particle comes after it: never look up it."],
    ],
    # three genders, and a voice that says them
    "30 German (tiếng Đức)": [
        ["ID", "Article", "Noun", "Plural", "Meaning", "Example"],
        ["#config", "side=front; size=26; color=accent; label=Which article?", "side=front; size=40; tts=de_DE; sort", "side=back; size=20; color=muted; label=Plural", "side=back; size=20", "side=back; size=16; italic; tts=de_DE; speed=0.85"],
        ["g01", "der", "Tisch", "die Tische", "cái bàn", "Der Tisch steht am Fenster."],
        ["g02", "die", "Tür", "die Türen", "cái cửa", "Bitte mach die Tür zu."],
        ["g03", "das", "Fenster", "die Fenster", "cửa sổ", "Das Fenster ist offen."],
        ["g04", "der", "Schlüssel", "die Schlüssel", "chìa khoá", "Ich habe meinen Schlüssel vergessen."],
        ["g05", "die", "Zeitung", "die Zeitungen", "tờ báo", "Er liest jeden Morgen die Zeitung."],
        ["g06", "das", "Mädchen", "die Mädchen", "cô bé", "Jedes Wort auf -chen ist das."],
        ["g07", "der", "Bahnhof", "die Bahnhöfe", "nhà ga", "Wir treffen uns am Bahnhof."],
    ],
    # accents that need not be typed, and one letter that must be
    "31 Spanish (tiếng Tây Ban Nha)": [
        ["ID", "English", "Spanish", "Note"],
        ["#config", "size=28; sort", "side=back; size=32; type=nc; tts=es_ES", "side=back; size=15; color=muted"],
        ["e01", "the tree", "el árbol", "type=nc ignores the accent, so “el arbol” is accepted."],
        ["e02", "the city", "la ciudad"],
        ["e03", "the heart", "el corazón"],
        ["e04", "quickly", "rápidamente"],
        ["e05", "the mountain", "la montaña", "ñ is a letter of its own, not an accent — it has to be typed."],
        ["e06", "the bird", "el pájaro"],
        ["e07", "tomorrow", "mañana", "Also means morning: mañana por la mañana."],
        ["e08", "the river", "el río"],
    ],
}
# fmt: on

# Every entry gets the same timestamp so an unchanged SHEETS rebuilds to a
# byte-identical file. A workbook that churned on every build would show up as a
# binary diff in every commit that touched anything nearby.
_STAMP = (2020, 1, 1, 0, 0, 0)

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" '
    'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.'
    'openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    '<Override PartName="/xl/styles.xml" ContentType="application/vnd.'
    'openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
    "{sheets}"
    "</Types>"
)

# Nothing here is styled, but Excel treats a workbook with no styles part as
# damaged and offers to repair it — and the point of this file is that someone
# can open it, look at the settings row, and copy it. The reader in
# src/workbook.py does not need it: it already treats a missing styles.xml as
# "no cell is a date".
_STYLES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
    '<fills count="1"><fill><patternFill patternType="none"/></fill></fills>'
    '<borders count="1"><border/></borders>'
    '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>'
    "</cellStyleXfs>"
    '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" '
    'xfId="0"/></cellXfs>'
    "</styleSheet>"
)

_ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
    'relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.'
    'org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"'
    "/></Relationships>"
)


def column_ref(index):
    """0 → "A", 26 → "AA" — the letters Excel addresses a cell by."""
    letters = ""
    index += 1
    while index:
        index, rest = divmod(index - 1, 26)
        letters = chr(65 + rest) + letters
    return letters


def _clean(text):
    """XML 1.0 forbids most control characters outright, even escaped."""
    return "".join(ch for ch in text if ch >= " " or ch in "\t\n\r")


def sheet_xml(rows):
    """A grid as a worksheet part.

    Every cell is written as an inline string. A shared-string table would make
    the file smaller, but these sheets are small and an inline string is the one
    cell type that cannot be misread: no number formatting, no date serial, no
    locale — what ``SHEETS`` says is what the reader gets back.
    """
    out = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/'
        'main"><sheetData>'
    ]
    for r, row in enumerate(rows, start=1):
        cells = []
        for c, value in enumerate(row):
            if not value:
                continue  # an empty cell is an absent cell
            ref = f"{column_ref(c)}{r}"
            cells.append(
                f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">'
                f"{escape(_clean(value))}</t></is></c>"
            )
        if cells:
            out.append(f'<row r="{r}">' + "".join(cells) + "</row>")
    out.append("</sheetData></worksheet>")
    return "".join(out)


def workbook_xml(names):
    sheets = "".join(
        f'<sheet name={quoteattr(name)} sheetId="{i}" r:id="rId{i}"/>'
        for i, name in enumerate(names, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
        ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/'
        f'relationships"><sheets>{sheets}</sheets></workbook>'
    )


def workbook_rels(count):
    rels = "".join(
        f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/'
        f'officeDocument/2006/relationships/worksheet" '
        f'Target="worksheets/sheet{i}.xml"/>'
        for i in range(1, count + 1)
    )
    # The styles part is reached through a relationship like any other, and it is
    # numbered past the sheets so a sheet's rId stays equal to its position.
    rels += (
        f'<Relationship Id="rId{count + 1}" Type="http://schemas.openxmlformats.'
        'org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
        f'relationships">{rels}</Relationships>'
    )


def build_bytes():
    """The workbook as bytes, plus the sheet names it holds."""
    names = list(SHEETS)

    too_long = [name for name in names if len(name) > 31]
    if too_long:
        sys.exit("a sheet name may be at most 31 characters: " + ", ".join(too_long))

    parts = {
        "[Content_Types].xml": _CONTENT_TYPES.format(
            sheets="".join(
                f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.'
                'spreadsheetml.worksheet+xml"/>'
                for i in range(1, len(names) + 1)
            )
        ),
        "_rels/.rels": _ROOT_RELS,
        "xl/workbook.xml": workbook_xml(names),
        "xl/_rels/workbook.xml.rels": workbook_rels(len(names)),
        "xl/styles.xml": _STYLES,
    }
    for i, name in enumerate(names, start=1):
        parts[f"xl/worksheets/sheet{i}.xml"] = sheet_xml(SHEETS[name])

    import io

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as book:
        for name, text in parts.items():
            info = zipfile.ZipInfo(name, date_time=_STAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            book.writestr(info, text.encode("utf-8"))
    return buffer.getvalue(), names


def verify(data, names):
    """Reads the result back with the add-on's own reader.

    Building a file the add-on cannot read is the one failure that would not
    show up until someone pasted the link, so the check is part of the build
    rather than a separate step nobody runs.
    """
    sys.path.insert(0, str(REPO / "src"))
    import importlib.machinery
    import importlib.util

    spec = importlib.machinery.ModuleSpec("sc_examples", None, is_package=True)
    package = importlib.util.module_from_spec(spec)
    package.__path__ = [str(REPO / "src")]
    sys.modules["sc_examples"] = package
    workbook = importlib.import_module("sc_examples.workbook")

    read = workbook.sheet_names(data)
    if read != names:
        sys.exit(f"the file reads back as {read}, not {names}")
    for name in names:
        # The reader hands back TSV, so the grid is compared in that shape rather
        # than cell by cell: trailing empty cells are absent in both, and a cell
        # holding a tab or a newline would be quoted in both.
        want = _tsv(SHEETS[name])
        if workbook.sheet_tsv(data, name) != want:
            sys.exit(f"sheet {name!r} does not read back as it was written")
    return len(names)


def _tsv(rows):
    """A grid as the TSV ``src/workbook.py`` produces for it."""
    import csv
    import io

    out = io.StringIO()
    csv.writer(out, delimiter="\t", lineterminator="\n").writerows(_padded(rows))
    return out.getvalue()


def _padded(rows):
    """The grid squared off, the way the reader's own trimming returns it.

    ``SHEETS`` lets a row stop early — a settings row that configures the first
    three columns of eight should not have to carry five empty strings — while
    the reader always returns every row at the sheet's full width.
    """
    width = max((len(row) for row in rows), default=0)
    return [list(row) + [""] * (width - len(row)) for row in rows]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail instead of writing when the workbook is out of date",
    )
    args = parser.parse_args()

    data, names = build_bytes()
    verify(data, names)

    if args.check:
        if not WORKBOOK.exists() or WORKBOOK.read_bytes() != data:
            sys.exit(
                f"{WORKBOOK.relative_to(REPO)} is out of date — "
                "run python scripts/build_examples.py"
            )
        print(f"{WORKBOOK.relative_to(REPO)} is up to date ({len(names)} sheets)")
        return

    WORKBOOK.write_bytes(data)
    print(
        f"wrote {WORKBOOK.relative_to(REPO)} — {len(names)} sheets, {len(data)} bytes"
    )
    for name in names:
        print(f"  {name}")


if __name__ == "__main__":
    main()
