"""Reads CC-CEDICT into `{word: numbered pinyin}`.

Nothing here decides which reading is the usual one — that is worked out from the
dictionary as a whole in build_gs.py, by counting. An earlier version of this file
carried a hand-written table of "the right reading" for the characters that have
several, which is a list nobody can finish and everybody argues with.
"""

import re
from collections import OrderedDict
from pathlib import Path

HERE = Path(__file__).parent
LINE = re.compile(r"^(\S+)\s+(\S+)\s+\[([^]]*)\]\s+/(.*)/$")
SYLLABLE = re.compile(r"[a-zA-Z]+[1-5]|r5|xx5|m[124]|n[234]|ng[24]")


def clean(pinyin):
    """CEDICT's own spelling, minus anything that is not a sound.

    `u:` is how the file writes ü; it becomes `v` here and a real ü on the way out,
    because the whole table stays ASCII until the moment it is displayed.
    """
    text = pinyin.strip().replace("u:", "v")
    if not text or "," in text or "·" in text:
        return None
    if not all(SYLLABLE.fullmatch(syllable) for syllable in text.split()):
        return None
    return text


def build(source):
    """Simplified headword → reading, first entry winning."""
    words = OrderedDict()
    for line in source.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        match = LINE.match(line)
        if not match:
            continue
        _, simplified, pinyin, _ = match.groups()
        if len(simplified) > 6 or not all("一" <= c <= "鿿" for c in simplified):
            continue
        reading = clean(pinyin)
        if reading:
            words.setdefault(simplified, reading)
    return words


if __name__ == "__main__":
    entries = build((HERE / "cedict.txt").read_text(encoding="utf-8"))
    print(f"{len(entries)} entries")
    for probe in ("行动", "银行", "长城", "重要", "西安"):
        print(" ", probe, "->", entries.get(probe))
