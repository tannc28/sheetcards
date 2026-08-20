/**
 * SheetCards — pinyin in a cell.
 *
 *   =PINYIN(A2)        行动             -> xíngdòng
 *   =PINYIN(E2)        我们需要立即行动   -> wǒmen xūyào lìjí xíngdòng
 *   =PINYIN(A2:A200)   a whole column at once
 *
 * One way of writing it, the standard one. The dictionary stores tone numbers
 * because they are ASCII and half the bytes, but that is where they stay: what
 * comes out of a cell is always the tone marks.
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

// Readings already looked up, kept for as long as Sheets keeps this execution
// alive. A column is mostly the same few hundred words, and a second look at one
// costs nothing. It grows to what the column actually used — not to the size of
// the dictionary.
var PINYIN_MEMO = Object.create(null);

/**
 * Pinyin for Chinese text.
 *
 * @param {string|Array} text The text, or a range of cells.
 * @return {string|Array} The reading. Anything that is not Chinese comes back untouched.
 * @customfunction
 */
function PINYIN(text) {
  if (Array.isArray(text)) {
    return text.map(function (row) {
      return Array.isArray(row)
        ? row.map(function (cell) { return PINYIN(cell); })
        : PINYIN(row);
    });
  }
  if (text === null || text === undefined || text === "") return "";

  // A blank cell and a cell with nothing Chinese in it are both answered before
  // the dictionary is touched. A column is mostly empty while it is being filled
  // in, and =PINYIN(A2:A500) over four hundred blanks should cost nothing at all.
  var subject = String(text);
  if (!subject.trim()) return "";
  if (!pinyinHasHan_(subject)) return subject;

  return pinyinJoin_(pinyinSegment_(subject));
}

/**
 * Splits text into words and reads each one.
 *
 * @return {Array} items of {reading: [syllables]} for Chinese, {literal: text} for the rest.
 */
function pinyinSegment_(text) {
  var out = [];
  var index = 0;

  while (index < text.length) {
    var start = index;
    if (!pinyinKnows_(text.charAt(index))) {
      // Punctuation, spaces, Latin, digits — carried through as they were written.
      while (index < text.length && !pinyinKnows_(text.charAt(index))) index += 1;
      out.push({ literal: text.slice(start, index) });
      continue;
    }
    while (index < text.length && pinyinKnows_(text.charAt(index))) index += 1;

    var words = pinyinSplit_(text.slice(start, index));
    for (var i = 0; i < words.length; i += 1) {
      var word = words[i];
      var reading = pinyinReading_(word);
      if (reading) {
        out.push({ reading: reading });
      } else {
        // A Han character the dictionary has never heard of. Printing it beats
        // dropping it: the cell then shows exactly which character to look up.
        out.push({ literal: word });
      }
    }
  }
  return out;
}

/** Whether the text holds anything the dictionary could read at all. */
function pinyinHasHan_(text) {
  for (var i = 0; i < text.length; i += 1) {
    if (isHan_(text.charAt(i))) return true;
  }
  return false;
}

/**
 * Whether this character is something the dictionary can read.
 *
 * The character table holds Han characters and nothing else, so this is a range
 * check rather than a lookup — punctuation and Latin letters are answered without
 * the dictionary being consulted about them at all.
 */
function pinyinKnows_(character) {
  return isHan_(character);
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
function pinyinSplit_(run) {
  var forward = pinyinMatch_(run, false);
  var backward = pinyinMatch_(run, true);
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
function pinyinMatch_(run, reversed) {
  var words = [];
  var index = reversed ? run.length : 0;

  while (reversed ? index > 0 : index < run.length) {
    var room = Math.min(PINYIN_MAX_WORD, reversed ? index : run.length - index);
    var taken = null;
    for (var length = room; length > 1; length -= 1) {
      var candidate = reversed
        ? run.substr(index - length, length)
        : run.substr(index, length);
      if (pinyinReading_(candidate)) { taken = candidate; break; }
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
function pinyinJoin_(items) {
  var parts = [];
  for (var i = 0; i < items.length; i += 1) {
    var item = items[i];
    if (item.literal !== undefined) {
      parts.push({ text: item.literal, spaced: false });
      continue;
    }
    parts.push({ text: pinyinWord_(item.reading), spaced: true });
  }

  var text = "";
  for (var j = 0; j < parts.length; j += 1) {
    var needsGap = j > 0 && parts[j].spaced && parts[j - 1].spaced;
    text += (needsGap ? " " : "") + parts[j].text;
  }
  return text;
}

/** One word: its syllables, joined the way pinyin is written. */
function pinyinWord_(syllables) {
  var text = "";
  for (var i = 0; i < syllables.length; i += 1) {
    var syllable = syllables[i];
    if (syllable === "r5" && i > 0) {
      // Erhua is a suffix, not a syllable: 花儿 is huār, never huā er.
      text += "r";
      continue;
    }
    // Without the apostrophe 西安 and a syllable "xian" are written identically.
    // The test is on the syllable as the dictionary spells it, not on the finished
    // one: by then the vowel may be ā, and "ā" does not start with "a".
    if (i > 0 && /^[aeo]/.test(syllable)) text += "'";
    text += pinyinTone_(syllable);
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
 * "xing2" -> "xíng".
 *
 * Where the mark goes is the standard rule: an `a` or an `e` takes it; in `ou` the
 * `o` does; otherwise it lands on the last vowel.
 */
function pinyinTone_(syllable) {
  var match = /^([a-z]+)([1-5])$/.exec(syllable);
  if (!match) return syllable;
  var letters = match[1];
  var tone = parseInt(match[2], 10);
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

/**
 * The reading for one word or character, or null if the dictionary has neither.
 *
 * Nothing is parsed up front. The two tables in PinyinData.gs are sorted, so a
 * lookup is a binary search straight into the text — about twenty string
 * comparisons — and the file is read where it lies instead of being turned into
 * a hundred thousand object properties first.
 *
 * That matters here more than it usually would. Sheets runs a custom function in
 * an execution it starts and discards as it pleases, so any work done "once" is
 * really done once per execution, and a column of cells can pay for it several
 * times over. Work not done at all cannot be repeated.
 */
function pinyinReading_(key) {
  var cached = PINYIN_MEMO[key];
  if (cached !== undefined) return cached;

  var reading = null;
  if (key.length === 1) {
    var charLine = pinyinFind_(PINYIN_CHARS, key, 1);
    if (charLine) reading = [charLine.slice(1)];
  } else {
    var wordLine = pinyinFind_(PINYIN_WORDS, key, key.length);
    if (wordLine) {
      if (wordLine.length === key.length) {
        // No reading spelled out: the word is its characters, read in order.
        reading = [];
        for (var i = 0; i < key.length; i += 1) {
          var each = pinyinReading_(key.charAt(i));
          if (!each) { reading = null; break; }
          reading.push(each[0]);
        }
      } else {
        reading = wordLine.slice(key.length + 1).match(/[a-z]+[1-5]/g);
      }
    }
  }

  PINYIN_MEMO[key] = reading;
  return reading;
}

/**
 * The line whose first `keyLength` characters are `key`, or null.
 *
 * Both tables are sorted by that key and hold one entry per line, so the search
 * can jump into the middle of the text and walk out to the line boundaries. The
 * comparison is on the key alone: a line may carry a reading after it, and
 * comparing whole lines would sort "行动|xing2dong4" away from "行动".
 */
function pinyinFind_(source, key, keyLength) {
  var low = 0;
  var high = source.length;

  while (low < high) {
    var middle = (low + high) >>> 1;
    // The start of the line the halfway point falls in. Searching back from
    // `middle - 1` rather than from `middle` is what keeps `start <= middle`: on a
    // halfway point that lands exactly on a line break, searching from `middle`
    // returns that break and `start` jumps past it — `high = start` then leaves
    // the window exactly as it was, and the search never ends. Both bounds are
    // always line starts, so clamping to `low` keeps the window whole.
    var start = middle === 0 ? 0 : source.lastIndexOf("\n", middle - 1) + 1;
    if (start < low) start = low;
    var end = source.indexOf("\n", start);
    if (end < 0) end = source.length;

    if (source.substr(start, keyLength) < key) {
      low = end + 1;            // end >= start >= low, so this always advances
    } else if (start === low) {
      break;                    // the window is this one line; halving it again
                                // would leave the bounds exactly where they are,
                                // which is how this loop used to hang on a key
                                // whose halfway point landed on a line break
    } else {
      high = start;             // start <= middle < high, so this always shrinks
    }
  }

  var lineEnd = source.indexOf("\n", low);
  if (lineEnd < 0) lineEnd = source.length;
  var line = source.slice(low, lineEnd);
  return line.substr(0, keyLength) === key ? line : null;
}
