/**
 * Sheets2Anki — pinyin that fills itself in.
 *
 * Type a word in the Chinese column and its reading appears in the pinyin column
 * a moment later, as plain text. Nothing to run, no menu, no formula in the cell.
 *
 * Why not a formula. `=PINYIN()` is a custom function, and Sheets recalculates
 * custom functions inside an execution it starts and discards on its own
 * schedule. That startup is the slow part — it is there even for a function that
 * returns a constant — and a column of five hundred formulas pays it again and
 * again, every time the file is opened. The lookup underneath takes microseconds;
 * the waiting was Google's, not the dictionary's.
 *
 * An edit trigger pays it once, for the row you just touched, in the background
 * while you carry on typing. And what lands in the cell is text: the sheet opens
 * instantly ever after, nothing recalculates, and what Sheets2Anki exports is
 * exactly what you can see.
 *
 * Set up the pairs below once. Columns are found by their heading rather than by
 * their letter, so inserting a column somewhere does not quietly break this.
 */

// Which column feeds which. A heading matches when it contains the text below,
// ignoring case — "Word" finds "Word (Mặt trước)", "Pinyin" finds "Pinyin".
// Add a pair to read a second column, e.g. an example sentence:
//   { from: "Ví dụ", into: "Pinyin ví dụ" }
var PINYIN_PAIRS = [
  { from: "Word", into: "Pinyin" }
];

// The row the headings are on.
var PINYIN_HEADER_ROW = 1;

/**
 * Sheets calls this on every edit a person makes. It is a simple trigger: no
 * authorization, no installation, nothing to switch on.
 */
function onEdit(event) {
  if (!event || !event.range) return;
  var sheet = event.range.getSheet();
  var headings = pinyinHeadings_(sheet);
  if (!headings) return;

  var firstRow = event.range.getRow();
  var lastRow = firstRow + event.range.getNumRows() - 1;
  var firstColumn = event.range.getColumn();
  var lastColumn = firstColumn + event.range.getNumColumns() - 1;

  for (var i = 0; i < PINYIN_PAIRS.length; i += 1) {
    var from = pinyinColumnOf_(headings, PINYIN_PAIRS[i].from);
    var into = pinyinColumnOf_(headings, PINYIN_PAIRS[i].into);
    if (!from || !into) continue;
    if (from < firstColumn || from > lastColumn) continue;  // this pair was not touched

    pinyinWriteRows_(sheet, from, into, firstRow, lastRow);
  }
}

/** The heading row as an array of strings, or null if the sheet has no headings. */
function pinyinHeadings_(sheet) {
  var width = sheet.getLastColumn();
  if (width < 1 || sheet.getLastRow() < PINYIN_HEADER_ROW) return null;
  return sheet.getRange(PINYIN_HEADER_ROW, 1, 1, width).getValues()[0];
}

/** The 1-based column whose heading contains `name`, or 0. */
function pinyinColumnOf_(headings, name) {
  var wanted = String(name).trim().toLowerCase();
  for (var i = 0; i < headings.length; i += 1) {
    if (String(headings[i]).trim().toLowerCase().indexOf(wanted) >= 0) return i + 1;
  }
  return 0;
}

/** Reads the source rows, works out the readings, and writes them in one call. */
function pinyinWriteRows_(sheet, from, into, firstRow, lastRow) {
  var top = Math.max(firstRow, PINYIN_HEADER_ROW + 1);
  if (top > lastRow) return;
  var height = lastRow - top + 1;

  var words = sheet.getRange(top, from, height, 1).getValues();
  var markers = sheet.getRange(top, 1, height, 1).getValues();
  // What the pinyin column holds now. A row this pass has nothing to say about
  // has to be written back as it was: setValues replaces every cell it covers,
  // and a null in that array clears the cell rather than skipping it.
  var existing = sheet.getRange(top, into, height, 1).getValues();

  var readings = pinyinReadingsFor_(words, markers, existing);
  if (!readings) return;

  // One write for the whole edited span. A call to Sheets per row would be the
  // same mistake as a formula per row, one layer down.
  sheet.getRange(top, into, height, 1).setValues(readings);
}

/**
 * The pinyin column for a block of source cells, or null if none of it changed.
 *
 * Kept free of Sheets so it can be tested: everything above is fetching and
 * storing, and this is the part that decides what a row should say.
 *
 * A row is skipped rather than blanked when its word is empty — a half-typed
 * sheet should not have its pinyin column wiped — and the settings row is left
 * alone entirely, because `#config` holds Sheets2Anki's directives, not a word.
 */
function pinyinReadingsFor_(words, markers, existing) {
  var readings = [];
  var changed = false;

  for (var row = 0; row < words.length; row += 1) {
    var marker = String((markers[row] || [])[0] || "").trim().toLowerCase();
    var word = String(words[row][0] || "").trim();
    var was = (existing[row] || [])[0];
    var keep = was === undefined || was === null ? "" : was;

    if (marker.indexOf("#config") === 0 || !word) {
      readings.push([keep]);
      continue;
    }

    var reading = PINYIN(word);
    // Nothing Chinese in the cell: PINYIN hands the text back unchanged, and
    // copying a Vietnamese word into the pinyin column would be nonsense.
    if (reading === word) {
      readings.push([keep]);
      continue;
    }

    readings.push([reading]);
    if (reading !== keep) changed = true;
  }

  return changed ? readings : null;
}
