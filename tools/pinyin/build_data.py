"""Writes PinyinData.gs — the dictionary the custom function reads.

Two tables come out of CC-CEDICT:

* a character table, one line per character, holding the reading that character
  most often has across the whole dictionary. CEDICT lists readings in headword
  order rather than by how often anyone meets them, so taking the first one makes
  the common reading look like the exception — 行 would come out `hang2`.
* a word list, longest-match segmentation reads it. Most words are simply their
  characters in order, so those lines carry the word alone and the reading is
  derived; only a word that disagrees with its characters spells one out. That is
  what keeps a 118,000-word dictionary inside one file.
"""

from collections import Counter
from collections import defaultdict
from pathlib import Path

from cedict import build

HERE = Path(__file__).parent
BANNER = """/**
 * Sheets2Anki — pinyin dictionary (generated, do not edit by hand).
 *
 * Built from CC-CEDICT (CC BY-SA 4.0, https://www.mdbg.net/chinese/dictionary?page=cedict).
 *
 * CHARS: one character per line, "字" followed by its usual reading.
 * WORDS: one word per line. A bare word is read as its characters in order; a
 *        word followed by "|reading" disagrees with them and says so — this is
 *        where 银行 stops being yin2xing2.
 */
"""


def main():
    words = {
        w: r.lower() for w, r in build((HERE / "cedict.txt").read_text("utf-8")).items()
    }

    votes = defaultdict(Counter)
    for word, reading in words.items():
        syllables = reading.split()
        if len(syllables) != len(word):
            continue  # a reading that does not line up teaches nothing about one character
        weight = 3 if len(word) == 1 else 1
        for character, syllable in zip(word, syllables, strict=True):
            votes[character][syllable] += weight
    chars = {c: counter.most_common(1)[0][0] for c, counter in votes.items()}

    def derived(word):
        parts = [chars.get(c) for c in word]
        return " ".join(parts) if all(parts) else None

    lines = []
    for word, reading in sorted(words.items()):
        # A single character belongs to the character table and nowhere else. Left
        # in the word list it would win the lookup and bring CEDICT's headword
        # order back with it: 个 has an entry reading `ge3`, used by exactly one
        # word, and it would have been the reading for every 个 on the sheet.
        if len(word) < 2:
            continue
        if derived(word) == reading:
            lines.append(word)
        else:
            lines.append(f"{word}|{reading.replace(' ', '')}")

    table = "\n".join(f"{c}{r}" for c, r in sorted(chars.items()))
    source = (
        BANNER
        + "\n// eslint-disable-next-line no-unused-vars\n"
        + "var PINYIN_CHARS = `\n"
        + table
        + "\n`;\n\n// eslint-disable-next-line no-unused-vars\n"
        + "var PINYIN_WORDS = `\n"
        + "\n".join(lines)
        + "\n`;\n"
    )
    out = HERE / "PinyinData.gs"
    out.write_text(source, encoding="utf-8")
    print(
        f"{out.name}: {len(chars)} characters, {len(lines)} words, "
        f"{len(source.encode())/1e6:.2f} MB"
    )


if __name__ == "__main__":
    main()
