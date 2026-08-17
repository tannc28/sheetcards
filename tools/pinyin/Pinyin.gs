/**
 * Sheets2Anki — pinyin in a cell.
 *
 *   =PINYIN(A2)            行动           -> xíngdòng
 *   =PINYIN(E2)            我们需要立即行动 -> wǒmen xūyào lìjí xíngdòng
 *   =PINYIN(A2, "number")  行动           -> xing2dong4
 *   =PINYIN(A2, "plain")   行动           -> xingdong
 *   =PINYIN(A2:A200)       a whole column at once
 *
 * Everything happens inside this file. There is no API key, no network call and
 * no quota to run out of: the dictionary is in PinyinData.gs and the work is a
 * table lookup. That is why this one is safe as a custom function, while a
 * function that phoned a service would not be — a cell showing "Loading..." or
 * an error when the sync runs is what Anki would import.
 *
 * The whole word is looked up, never the characters one at a time. 行 is xíng in
 * 行动 and háng in 银行; a per-character mapping gets one of the two wrong every
 * time, and a deck teaches whatever it is given.
 */

// The longest headword in the dictionary. Segmentation never has to look further
// ahead than this, and looking further would only cost time.
var PINYIN_MAX_WORD = 6;

// Built once and kept for as long as Sheets keeps this execution alive. A
// recalculation fills a whole column through the same instance, so the dictionary
// is parsed once for the column rather than once per cell.
var PINYIN_TABLES = null;

/**
 * Pinyin for Chinese text.
 *
 * @param {string|Array} text The text, or a range of cells.
 * @param {string} [style] "tone" (default) for mǎ, "number" for ma3, "plain" for ma.
 * @return {string|Array} The reading. Anything that is not Chinese comes back untouched.
 * @customfunction
 */
function PINYIN(text, style) {
  if (Array.isArray(text)) {
    return text.map(function (row) {
      return Array.isArray(row)
        ? row.map(function (cell) { return PINYIN(cell, style); })
        : PINYIN(row, style);
    });
  }
  if (text === null || text === undefined || text === "") return "";

  var mode = String(style || "tone").toLowerCase();
  var syllables = pinyinSegment_(String(text));
  return pinyinJoin_(syllables, mode);
}

/**
 * Pinyin written with tone numbers, e.g. xing2dong4.
 *
 * @param {string|Array} text The text, or a range of cells.
 * @return {string|Array} The reading.
 * @customfunction
 */
function PINYIN_NUM(text) {
  return PINYIN(text, "number");
}

/**
 * Splits text into words and reads each one.
 *
 * @return {Array} items of {reading: [syllables]} for Chinese, {literal: text} for the rest.
 */
function pinyinSegment_(text) {
  var tables = pinyinTables_();
  var out = [];
  var index = 0;

  while (index < text.length) {
    var start = index;
    if (!pinyinKnows_(text.charAt(index), tables)) {
      // Punctuation, spaces, Latin, digits — carried through as they were written.
      while (index < text.length && !pinyinKnows_(text.charAt(index), tables)) index += 1;
      out.push({ literal: text.slice(start, index) });
      continue;
    }
    while (index < text.length && pinyinKnows_(text.charAt(index), tables)) index += 1;

    var words = pinyinSplit_(text.slice(start, index), tables);
    for (var i = 0; i < words.length; i += 1) {
      var word = words[i];
      if (tables.words[word]) {
        out.push({ reading: tables.words[word] });
      } else if (tables.chars[word]) {
        out.push({ reading: [tables.chars[word]] });
      } else {
        // A Han character the dictionary has never heard of. Printing it beats
        // dropping it: the cell then shows exactly which character to look up.
        out.push({ literal: word });
      }
    }
  }
  return out;
}

/** Whether this character is something the dictionary can read. */
function pinyinKnows_(character, tables) {
  return Boolean(tables.chars[character]) || isHan_(character);
}

/**
 * Cuts a run of Chinese into words, both directions, and keeps the better cut.
 *
 * Longest-match from the left is the usual trick and it is usually right, but it
 * commits early and cannot take the commitment back: in 新词典 it takes 新词 and
 * leaves 典 stranded, so a dictionary comes out as "xīncí diǎn". Running the same
 * match from the right gives 新 + 词典, and comparing the two costs one more pass
 * over a sentence. Fewer words wins, then fewer characters left standing alone;
 * an even tie goes to the backward cut, which is the more accurate of the two on
 * Chinese in general.
 */
function pinyinSplit_(run, tables) {
  var forward = pinyinMatch_(run, tables, false);
  var backward = pinyinMatch_(run, tables, true);
  if (forward.length !== backward.length) {
    return forward.length < backward.length ? forward : backward;
  }
  return pinyinLoners_(forward) < pinyinLoners_(backward) ? forward : backward;
}

/** How many single characters a cut leaves on their own. */
function pinyinLoners_(words) {
  var count = 0;
  for (var i = 0; i < words.length; i += 1) if (words[i].length === 1) count += 1;
  return count;
}

/** Longest match through the run, from the left or from the right. */
function pinyinMatch_(run, tables, reversed) {
  var words = [];
  var index = reversed ? run.length : 0;

  while (reversed ? index > 0 : index < run.length) {
    var room = Math.min(PINYIN_MAX_WORD, reversed ? index : run.length - index);
    var taken = null;
    for (var length = room; length > 1; length -= 1) {
      var candidate = reversed
        ? run.substr(index - length, length)
        : run.substr(index, length);
      if (tables.words[candidate]) { taken = candidate; break; }
    }
    if (!taken) taken = reversed ? run.charAt(index - 1) : run.charAt(index);
    words.push(taken);
    index += reversed ? -taken.length : taken.length;
  }

  if (reversed) words.reverse();
  return words;
}

/** Whether a character is in a CJK block, for text the dictionary does not cover. */
function isHan_(character) {
  var code = character.charCodeAt(0);
  return (code >= 0x4e00 && code <= 0x9fff)
      || (code >= 0x3400 && code <= 0x4dbf)
      || (code >= 0xf900 && code <= 0xfaff);
}

/** Words separated by a space, syllables inside a word run together. */
function pinyinJoin_(items, mode) {
  var parts = [];
  for (var i = 0; i < items.length; i += 1) {
    var item = items[i];
    if (item.literal !== undefined) {
      parts.push({ text: item.literal, spaced: false });
      continue;
    }
    parts.push({ text: pinyinWord_(item.reading, mode), spaced: true });
  }

  var text = "";
  for (var j = 0; j < parts.length; j += 1) {
    var needsGap = j > 0 && parts[j].spaced && parts[j - 1].spaced;
    text += (needsGap ? " " : "") + parts[j].text;
  }
  return text;
}

/** One word: its syllables, joined the way pinyin is written. */
function pinyinWord_(syllables, mode) {
  var text = "";
  for (var i = 0; i < syllables.length; i += 1) {
    var syllable = syllables[i];
    if (syllable === "r5" && i > 0) {
      // Erhua is a suffix, not a syllable: 花儿 is huār, never huā er.
      text += mode === "number" ? "r" : "r";
      continue;
    }
    // Without the apostrophe 西安 and a syllable "xian" are written identically.
    // The test is on the syllable as the dictionary spells it, not on the finished
    // one: by then the vowel may be ā, and "ā" does not start with "a".
    if (i > 0 && /^[aeo]/.test(syllable)) text += "'";
    text += mode === "number" ? syllable : pinyinTone_(syllable, mode);
  }
  return text;
}

var PINYIN_VOWELS = {
  a: "āáǎàa",
  o: "ōóǒòo",
  e: "ēéěèe",
  i: "īíǐìi",
  u: "ūúǔùu",
  v: "ǖǘǚǜü"
};

/**
 * "xing2" -> "xíng", or "xing" when the mode is plain.
 *
 * Where the mark goes is the standard rule: an `a` or an `e` takes it; in `ou` the
 * `o` does; otherwise it lands on the last vowel.
 */
function pinyinTone_(syllable, mode) {
  var match = /^([a-z]+)([1-5])$/.exec(syllable);
  if (!match) return syllable;
  var letters = match[1];
  var tone = parseInt(match[2], 10);
  if (mode === "plain") return letters.replace(/v/g, "ü");

  var target = -1;
  if (letters.indexOf("a") >= 0) {
    target = letters.indexOf("a");
  } else if (letters.indexOf("e") >= 0) {
    target = letters.indexOf("e");
  } else if (letters.indexOf("ou") >= 0) {
    target = letters.indexOf("ou");
  } else {
    for (var i = letters.length - 1; i >= 0; i -= 1) {
      if (PINYIN_VOWELS[letters.charAt(i)]) { target = i; break; }
    }
  }
  if (target < 0) return letters.replace(/v/g, "ü");

  var marks = PINYIN_VOWELS[letters.charAt(target)];
  var marked = marks.charAt(tone - 1);
  return (letters.slice(0, target) + marked + letters.slice(target + 1)).replace(/v/g, "ü");
}

/** Parses the two tables in PinyinData.gs, once. */
function pinyinTables_() {
  if (PINYIN_TABLES) return PINYIN_TABLES;

  var chars = Object.create(null);
  var charLines = PINYIN_CHARS.split("\n");
  for (var i = 0; i < charLines.length; i += 1) {
    var line = charLines[i];
    if (line.length > 1) chars[line.charAt(0)] = line.slice(1);
  }

  var words = Object.create(null);
  var wordLines = PINYIN_WORDS.split("\n");
  for (var j = 0; j < wordLines.length; j += 1) {
    var entry = wordLines[j];
    if (!entry) continue;
    var bar = entry.indexOf("|");
    if (bar < 0) {
      // Read as its characters in order — the case the data file leaves unsaid.
      var derived = [];
      for (var k = 0; k < entry.length; k += 1) derived.push(chars[entry.charAt(k)]);
      words[entry] = derived;
    } else {
      words[entry.slice(0, bar)] = entry.slice(bar + 1).match(/[a-z]+[1-5]/g) || [];
    }
  }

  PINYIN_TABLES = { chars: chars, words: words };
  return PINYIN_TABLES;
}
