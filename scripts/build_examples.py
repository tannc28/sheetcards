#!/usr/bin/env python3
"""Builds ``examples/sheets2anki-examples.xlsx`` — the one example the docs link.

Everything that points a person at an example points at that single file: the
README, the AnkiWeb description, the add-on's dev-only *Import Test Deck*, and the
preview site's landing page. It used to be a Google Sheet nobody working on the
add-on could edit, which is how it came to describe a schema the add-on had
outgrown with nothing in the repository able to notice.

So the sheets live here, in ``SHEETS`` below, and the workbook is generated from
them and committed beside this script. Keeping the grids as Python rather than as
a folder of TSVs means the whole tour is one readable, reviewable file: a settings
row changed in a review shows up as a changed *line*, not as a changed ZIP and not
as a diff spread over sixteen files.

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
WORKBOOK = EXAMPLES / "sheets2anki-examples.xlsx"

# Media is linked at its own address rather than copied into the repository:
# every picture, recording and stroke-order animation below is a Wikimedia
# Commons file. That is also what a media column does in a real sheet — nothing
# lands in collection.media, so these cards need the network to draw.

# ---------------------------------------------------------------------------
# The tour
# ---------------------------------------------------------------------------
#
# One entry per sheet, in tab order, from the smallest sheet that works to every
# directive at once. Row 1 is the header row; a row whose ID cell starts with
# ``#config`` is the settings row and is read as directives rather than as a note.
#
# tests/test_examples.py fails if a settings-row key has no example anywhere in
# here, so a directive added to src/sheet_config.py gets a demonstration in the
# same commit rather than eventually.
#
# One thing here is not in English, deliberately: **the column that carries the
# meaning of a word is glossed in Vietnamese**, because that is who this workbook
# is demonstrated to. It stops there — headers, the settings row, `label=` text,
# the explanatory notes and the sheets that are documentation rather than
# vocabulary (02, 09, 16) are all English, and a gloss is data rather than prose.

# A grid reads as a grid. One cell per line does not.
# fmt: off
SHEETS = {
    # the smallest sheet that works: an ID, a front, a back. One word per
    # language, answered in Vietnamese — the sheet is three columns wide and
    # the language it teaches is only ever the content of a cell, never a
    # setting. Nothing here knows what Korean is.
    "01 Basic": [
        ["ID", "Front", "Back"],
        ["b01", "bread", "bánh mì"],
        ["b02", "水", "nước"],
        ["b03", "ねこ", "con mèo"],
        ["b04", "학교", "trường học"],
        ["b05", "das Buch", "quyển sách"],
        ["b06", "la casa", "ngôi nhà"],
    ],
    # the reserved columns — SYNC gating, the deck path, tags
    "02 Sync and subdecks": [
        ["ID", "SYNC", "SUBDECK 1", "SUBDECK 2", "TAGS", "Question", "Answer"],
        ["s01", "yes", "Geography", "Capitals", "europe, capitals", "Capital of Portugal?", "Lisbon"],
        ["s02", "x", "Geography", "Capitals", "asia; capitals", "Capital of Vietnam?", "Hanoi"],
        ["s03", "1", "Geography", "Rivers", "rivers", "Longest river in Asia?", "The Yangtze"],
        ["s04", "TRUE", "Geography", "Rivers", "rivers, europe", "Which river flows through Paris?", "The Seine"],
        ["s05", "✓", "History", "", "history", "Who was the first Ming emperor?", "The Hongwu Emperor"],
        ["s06", "yes", "", "", "", "A row with no SUBDECK stays in the deck root.", "No subdeck, no tag."],
        ["s07", "no", "Geography", "Capitals", "capitals", "This row is switched off.", "It is never written to Anki."],
        ["s08", "", "History", "", "history", "An empty SYNC cell is off too.", "Same as 'no'."],
    ],
    # the settings row: sides, sizes, colours, weight, labels, hint
    "03 Card layout": [
        ["ID", "Word", "Pinyin", "Meaning", "Example", "Note", "Source"],
        ["#config align=left", "size=48px; bold", "side=front; size=22; color=accent", "size=26; color=#c2410c", "size=16; color=muted; italic; label=Example", "size=14; color=teal; align=right; hint", "side=hide"],
        ["L01", "图书馆", "túshūguǎn", "thư viện", "图书馆在学校旁边。", "Literally “book-store-hall”.", "HSK 3 word list"],
        ["L02", "飞机", "fēijī", "máy bay", "我明天坐飞机去上海。", "飞 = to fly, 机 = machine.", "HSK 1 word list"],
        ["L03", "医院", "yīyuàn", "bệnh viện", "他在医院工作。", "医 = to heal, 院 = courtyard.", "HSK 1 word list"],
        ["L04", "季节", "jìjié", "mùa", "北京的四个季节都很清楚。", "Used for seasons of the year only.", "HSK 3 word list"],
        ["L05", "习惯", "xíguàn", "thói quen; quen với", "我习惯早起。", "Works as both noun and verb.", "HSK 3 word list"],
        ["L06", "环境", "huánjìng", "môi trường", "这里的环境很安静。", "Covers surroundings, not only nature.", "HSK 3 word list"],
    ],
    # one row, both directions
    "04 Reverse": [
        ["ID", "Vietnamese", "Chinese", "Pinyin"],
        ["#config reverse", "size=30", "side=back; size=44", "side=back; size=20; color=muted"],
        ["r01", "đọc", "读", "dú"],
        ["r02", "viết", "写", "xiě"],
        ["r03", "nghe", "听", "tīng"],
        ["r04", "nói", "说", "shuō"],
        ["r05", "nhớ", "记得", "jìde"],
        ["r06", "quên", "忘记", "wàngjì"],
    ],
    # Anki's typed-answer box, diacritic-insensitive
    "05 Type the answer": [
        ["ID", "Vietnamese", "Spanish", "Note"],
        ["#config", "size=30", "side=back; size=32; type=nc", "size=14; color=muted"],
        ["t01", "cái cây", "el árbol", "type=nc ignores the accent, so “el arbol” counts."],
        ["t02", "thành phố", "la ciudad"],
        ["t03", "trái tim", "el corazón"],
        ["t04", "nhanh chóng", "rápidamente"],
        ["t05", "con chim", "el pájaro"],
        ["t06", "mặt trăng", "la luna"],
        ["t07", "ngọn núi", "la montaña", "ñ is a letter, not an accent — it must be typed."],
        ["t08", "con sông", "el río"],
    ],
    # a declared cloze column, including a row with two deletions
    "06 Cloze": [
        ["ID", "Sentence", "Pinyin", "Translation", "Note"],
        ["#config", "cloze; size=30", "size=18; color=accent", "size=18", "size=14; color=muted; hint"],
        ["z01", "我{{c1::是}}中国人。", "Wǒ shì Zhōngguórén.", "Tôi là người Trung Quốc.", "是 links two nouns; it is not used before an adjective."],
        ["z02", "他{{c1::在}}图书馆{{c2::看}}书。", "Tā zài túshūguǎn kàn shū.", "Anh ấy đang đọc sách trong thư viện.", "Two deletions make two cards from one row."],
        ["z03", "我们{{c1::明天}}去北京。", "Wǒmen míngtiān qù Běijīng.", "Ngày mai chúng tôi đi Bắc Kinh.", "Time words come before the verb."],
        ["z04", "这本书{{c1::很}}有意思。", "Zhè běn shū hěn yǒuyìsi.", "Quyển sách này rất thú vị.", "很 is required before a bare adjective."],
        ["z05", "她{{c1::会}}说三种语言。", "Tā huì shuō sān zhǒng yǔyán.", "Cô ấy nói được ba thứ tiếng.", "会 is learned ability."],
        ["z06", "请{{c1::把}}门关上。", "Qǐng bǎ mén guānshàng.", "Làm ơn đóng cửa lại.", "把 moves the object in front of the verb."],
    ],
    # a column holding a picture URL
    "07 Images": [
        ["ID", "Picture", "Word", "Pinyin", "Meaning"],
        ["#config", "image; size=320", "side=back; size=44", "side=back; size=22; color=accent", "side=back; size=18; color=muted"],
        ["p01", "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/Cat_November_2010-1a.jpg/500px-Cat_November_2010-1a.jpg", "猫", "māo", "con mèo"],
        ["p02", "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3c/Giant_Panda_2004-03-2.jpg/500px-Giant_Panda_2004-03-2.jpg", "熊猫", "xióngmāo", "gấu trúc"],
        ["p03", "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Green_tea_3_appearances.jpg/500px-Green_tea_3_appearances.jpg", "茶", "chá", "trà"],
        ["p04", "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/Great_Wall_of_China_July_2006.JPG/500px-Great_Wall_of_China_July_2006.JPG", "长城", "Chángchéng", "Vạn Lý Trường Thành"],
        ["p05", "https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/Terracotta_Army_Pit_1_-_2.jpg/500px-Terracotta_Army_Pit_1_-_2.jpg", "兵马俑", "bīngmǎyǒng", "đội quân đất nung"],
        ["p06", "https://upload.wikimedia.org/wikipedia/commons/thumb/1/15/Red_Apple.jpg/500px-Red_Apple.jpg", "苹果", "píngguǒ", "quả táo"],
        ["p07", "https://upload.wikimedia.org/wikipedia/commons/thumb/1/17/Tiger_in_Ranthambhore.jpg/500px-Tiger_in_Ranthambhore.jpg", "老虎", "lǎohǔ", "con hổ"],
        ["p08", "https://upload.wikimedia.org/wikipedia/commons/thumb/9/98/Horse-and-pony.jpg/500px-Horse-and-pony.jpg", "马", "mǎ", "con ngựa"],
        ["p09", "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Full_Moon_Luc_Viatour.jpg/500px-Full_Moon_Luc_Viatour.jpg", "月亮", "yuèliang", "mặt trăng"],
        ["p10", "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Fire.JPG/500px-Fire.JPG", "火", "huǒ", "lửa"],
        ["p11", "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d1/Mount_Everest_as_seen_from_Drukair2_PLW_edit.jpg/500px-Mount_Everest_as_seen_from_Drukair2_PLW_edit.jpg", "山", "shān", "núi"],
    ],
    # a column holding a recording
    "08 Audio": [
        ["ID", "Recording", "Answer", "Pinyin", "Meaning"],
        ["#config", "audio; label=Listen", "side=back; size=44", "side=back; size=22; color=accent", "side=back; size=18; color=muted"],
        ["a01", "https://upload.wikimedia.org/wikipedia/commons/8/8a/Zh-Beijing.ogg", "北京", "Běijīng", "Bắc Kinh — thủ đô"],
        ["a02", "https://upload.wikimedia.org/wikipedia/commons/7/73/Zh-Shanghai.ogg", "上海", "Shànghǎi", "Thượng Hải"],
        ["a03", "https://upload.wikimedia.org/wikipedia/commons/8/82/Zh-Guangzhou.ogg", "广州", "Guǎngzhōu", "Quảng Châu"],
        ["a04", "https://upload.wikimedia.org/wikipedia/commons/3/36/Zh-Hangzhou.ogg", "杭州", "Hángzhōu", "Hàng Châu"],
        ["a05", "https://upload.wikimedia.org/wikipedia/commons/9/9b/Zh-Tianjin.ogg", "天津", "Tiānjīn", "Thiên Tân"],
        ["a06", "https://upload.wikimedia.org/wikipedia/commons/5/57/Zh-Anhui.ogg", "安徽", "Ānhuī", "tỉnh An Huy"],
        ["a07", "https://upload.wikimedia.org/wikipedia/commons/2/25/Zh-Taiwan.ogg", "台湾", "Táiwān", "Đài Loan"],
        ["a08", "https://upload.wikimedia.org/wikipedia/commons/9/9e/Zh-Changan.ogg", "长安", "Cháng'ān", "Trường An — kinh đô thời Đường"],
    ],
    # every link form the add-on rewrites into a player
    "09 Video": [
        ["ID", "Question", "Clip", "Answer"],
        ["#config", "size=26", "side=back; video; label=Watch the clip; hint", "size=18"],
        ["v01", "A full YouTube watch link.", "https://www.youtube.com/watch?v=jNQXAC9IVRw", "Rewritten to https://www.youtube.com/embed/… before the note is saved."],
        ["v02", "A youtu.be short link.", "https://youtu.be/aircAruvnKk", "Same rewrite — the id is what matters, not the host."],
        ["v03", "A Shorts link.", "https://www.youtube.com/shorts/5MgBikgcWnY", "/shorts/, /live/ and /v/ are all recognised."],
        ["v04", "A link that is already an embed link.", "https://www.youtube.com/embed/jNQXAC9IVRw", "The rewrite is idempotent — it is left alone."],
        ["v05", "A direct video file, not a page.", "https://upload.wikimedia.org/wikipedia/commons/d/de/Ink_grinding.webmhd.webm", "Passed through unchanged; the frame plays the file itself."],
    ],
    # text-to-speech: deck-wide speed, a per-column override, and a column
    # that is heard without being read
    "10 Speech": [
        ["ID", "Chinese", "Pinyin", "Vietnamese", "Once more, slowly"],
        ["#config speed=0.9", "size=40; tts=zh_CN", "size=22; color=accent", "size=20", "side=hide; tts=zh_CN; speed=0.5"],
        ["k01", "早上好", "zǎoshang hǎo", "chào buổi sáng", "早上好"],
        ["k02", "谢谢你的帮助", "xièxie nǐ de bāngzhù", "cảm ơn bạn đã giúp đỡ", "谢谢你的帮助"],
        ["k03", "请再说一遍", "qǐng zài shuō yí biàn", "làm ơn nói lại một lần nữa", "请再说一遍"],
        ["k04", "我听不懂", "wǒ tīng bu dǒng", "tôi nghe không hiểu", "我听不懂"],
        ["k05", "多少钱", "duōshao qián", "bao nhiêu tiền", "多少钱"],
        ["k06", "洗手间在哪儿", "xǐshǒujiān zài nǎr", "nhà vệ sinh ở đâu", "洗手间在哪儿"],
    ],
    # write the character; a column that files the note without reaching the card
    "11 Chinese writing": [
        ["ID", "TAGS", "Level", "Meaning", "Pinyin", "Hanzi", "Strokes", "Example"],
        ["#config", "", "subdeck=1", "side=front; size=24; color=muted; label=Write the character for", "side=front; size=40; color=accent", "side=back; size=90; type; tts=zh_CN", "side=back; image; size=200; hint; label=Stroke order", "side=back; size=18; tts=zh_CN; speed=0.8"],
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
    "12 Chinese drawing": [
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
    "13 Japanese furigana": [
        ["ID", "Japanese", "Meaning", "Note"],
        ["#config", "size=40; furigana", "size=20", "size=14; color=muted; hint"],
        ["f01", "日本語[にほんご]", "tiếng Nhật", "Write the reading in brackets after the kanji."],
        ["f02", "図書館[としょかん]", "thư viện"],
        ["f03", " 私[わたし]は 学生[がくせい]です。", "Tôi là học sinh.", "A leading space separates one reading from the previous word."],
        ["f04", "新[あたら]しい 本[ほん]", "một quyển sách mới"],
        ["f05", "駅[えき]まで 歩[ある]きます。", "Tôi đi bộ đến ga."],
        ["f06", "先生[せんせい]の 話[はなし]", "câu chuyện của thầy giáo"],
    ],
    # the sheet decides the schema, in any script
    "14 Any language headers": [
        ["ID", "汉字", "拼音", "释义", "例句"],
        ["#config", "size=44; tts=zh_CN", "size=22; color=accent", "size=20", "size=16; color=muted"],
        ["h01", "词典", "cídiǎn", "từ điển", "我买了一本新词典。"],
        ["h02", "练习", "liànxí", "luyện tập; bài tập", "每天练习写汉字。"],
        ["h03", "翻译", "fānyì", "dịch; phiên dịch viên", "他是一位翻译。"],
        ["h04", "笔画", "bǐhuà", "nét (của chữ Hán)", "“我”有七个笔画。"],
        ["h05", "部首", "bùshǒu", "bộ thủ", "这个字的部首是“水”。"],
        ["h06", "声调", "shēngdiào", "thanh điệu", "普通话有四个声调。"],
    ],
    # every role and every directive on one card
    "15 Everything": [
        ["ID", "SYNC", "SUBDECK 1", "SUBDECK 2", "SUBDECK 3", "TAGS", "Picture", "Word", "Pinyin", "Meaning", "Example", "Recording", "Clip", "Source"],
        ["#config align=left; speed=0.9; reverse", "", "", "", "", "", "image; size=260; label=Look", "side=front; size=44; bold; tts=zh_CN; voices=Ting-Ting,Microsoft Huihui", "side=back; size=22; color=accent; align=center; type=nc", "side=back; size=20", "side=back; size=16; color=muted; italic; tts=zh_CN; speed=0.7", "side=back; audio; label=Native recording", "side=back; video; size=480; hint; label=Watch", "side=hide"],
        ["e01", "yes", "Places", "China", "Cities", "cities, hsk1", "https://upload.wikimedia.org/wikipedia/commons/thumb/f/fa/Great_Wall_of_China_July_2006.JPG/500px-Great_Wall_of_China_July_2006.JPG", "北京", "Běijīng", "Bắc Kinh, thủ đô", "北京有很多名胜古迹。", "https://upload.wikimedia.org/wikipedia/commons/8/8a/Zh-Beijing.ogg", "https://www.youtube.com/watch?v=jNQXAC9IVRw", "internal note, never shown"],
        ["e02", "yes", "Places", "China", "Cities", "cities", "", "上海", "Shànghǎi", "Thượng Hải, thành phố lớn nhất", "上海在长江的入海口。", "https://upload.wikimedia.org/wikipedia/commons/7/73/Zh-Shanghai.ogg", "", "internal note, never shown"],
        ["e03", "yes", "Places", "China", "Cities", "cities", "", "广州", "Guǎngzhōu", "Quảng Châu", "广州的早茶很有名。", "https://upload.wikimedia.org/wikipedia/commons/8/82/Zh-Guangzhou.ogg"],
        ["e04", "yes", "Places", "China", "Cities", "cities", "", "杭州", "Hángzhōu", "Hàng Châu", "杭州有西湖。", "https://upload.wikimedia.org/wikipedia/commons/3/36/Zh-Hangzhou.ogg"],
        ["e05", "yes", "Places", "China", "Provinces", "provinces", "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d1/Mount_Everest_as_seen_from_Drukair2_PLW_edit.jpg/500px-Mount_Everest_as_seen_from_Drukair2_PLW_edit.jpg", "安徽", "Ānhuī", "tỉnh An Huy", "安徽有黄山。", "https://upload.wikimedia.org/wikipedia/commons/5/57/Zh-Anhui.ogg"],
        ["e06", "yes", "Places", "China", "History", "history", "https://upload.wikimedia.org/wikipedia/commons/thumb/1/14/Terracotta_Army_Pit_1_-_2.jpg/500px-Terracotta_Army_Pit_1_-_2.jpg", "长安", "Cháng'ān", "Trường An, kinh đô thời Đường", "长安是今天的西安。", "https://upload.wikimedia.org/wikipedia/commons/9/9e/Zh-Changan.ogg", "https://youtu.be/aircAruvnKk"],
        ["e07", "no", "Places", "China", "Cities", "cities", "", "天津", "Tiānjīn", "Thiên Tân — dòng này đang tắt nên không bao giờ vào Anki", "天津在北京的东边。", "https://upload.wikimedia.org/wikipedia/commons/9/9b/Zh-Tianjin.ogg"],
    ],
    # wrong on purpose, so every warning has something to point at
    "16 Edge cases": [
        ["ID", "SYNC", "Word", "Meaning", "Picture", "Clip", "Sentence", "Extra", "Meaning"],
        ["#config align=middle; spid=3; reverse", "", "size=400; colour=red; tts=zh; cloze", "side=upside; cloze", "image; audio; tts=en_US; bold; size=5000; furigana", "video; size=9000", "speed=3; label", "size=abc; align; subdeck=1; bold", "size=20"],
        ["x01", "yes", "{{c1::重复}}的表头", "duplicated header — only the first 'Meaning' is a field", "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Green_tea_3_appearances.jpg/500px-Green_tea_3_appearances.jpg", "https://www.youtube.com/@nationalgeographic", "A channel link is not a video: it is passed through with a warning.", "", "this cell is ignored"],
        ["x02", "yes", "{{c1::网盘}}链接", "a Google Drive link is rewritten to its /preview player", "", "https://drive.google.com/file/d/1PLACEHOLDER_FILE_ID_HERE/view", "The id here is a placeholder, so the frame will not play anything."],
        ["", "yes", "{{c1::无编号}}的一行", "a row with no ID is counted and skipped", "", "", "Nothing is written to Anki for it."],
        ["x01", "yes", "{{c1::重复}}的编号", "the same ID twice — the sync reports it", "", "", "Two rows cannot key one note."],
        ["x05", "no", "{{c1::关闭}}的一行", "switched off", "", "", "Not marked for sync, so it is skipped."],
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

    spec = importlib.machinery.ModuleSpec("s2a_examples", None, is_package=True)
    package = importlib.util.module_from_spec(spec)
    package.__path__ = [str(REPO / "src")]
    sys.modules["s2a_examples"] = package
    workbook = importlib.import_module("s2a_examples.workbook")

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
