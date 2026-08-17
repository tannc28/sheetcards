/** Runs the .gs files as plain JS and checks the readings a learner would notice. */

const fs = require("fs");
const vm = require("vm");
const path = require("path");

const here = __dirname;
const context = vm.createContext({ console });
for (const file of ["PinyinData.gs", "Pinyin.gs"]) {
  vm.runInContext(fs.readFileSync(path.join(here, file), "utf8"), context, { filename: file });
}
const { PINYIN } = context;

const cases = [
  ["行动", "xíngdòng"],
  ["银行", "yínháng"],
  ["长城", "chángchéng"],
  ["重要", "zhòngyào"],
  ["图书馆", "túshūguǎn"],
  ["西安", "xī'ān"],
  ["绿色", "lǜsè"],
  ["我们需要立即行动", "wǒmen xūyào lìjí xíngdòng"],
  ["图书馆在学校旁边。", "túshūguǎn zài xuéxiào pángbiān。"],
  ["我买了一本新词典。", "wǒ mǎi le yī běn xīn cídiǎn。"],
  ["他在医院工作", "tā zài yīyuàn gōngzuò"],
  ["", ""],
  ["hello", "hello"],
];

let failed = 0;
for (const [input, expected] of cases) {
  const got = PINYIN(input);
  const ok = got === expected;
  if (!ok) failed += 1;
  console.log(`${ok ? "ok  " : "FAIL"} ${JSON.stringify(input)} -> ${JSON.stringify(got)}` +
              (ok ? "" : `  (expected ${JSON.stringify(expected)})`));
}

// There is one way of writing it, so a second argument must change nothing.
const extra = PINYIN("行动", "number");
if (extra !== "xíngdòng") {
  failed += 1;
  console.log(`FAIL a second argument changed the output: ${JSON.stringify(extra)}`);
}

console.log("\nrange:", JSON.stringify(PINYIN([["行动"], ["银行"]])));

// The lookup is a binary search into the raw text rather than a map built up
// front, which is what keeps the first call cheap — and what makes an off-by-one
// a hang rather than a wrong answer. So every entry in both tables is asked for,
// and the answers are checked against the same file read the obvious way.
console.log("\nchecking every entry against a plain parse of the same data:");
const reference = new Map();
for (const line of context.PINYIN_CHARS.split("\n")) {
  if (line.length > 1) reference.set(line.charAt(0), line);
}
for (const line of context.PINYIN_WORDS.split("\n")) {
  if (!line) continue;
  const bar = line.indexOf("|");
  reference.set(bar < 0 ? line : line.slice(0, bar), line);
}

let mismatched = 0;
const started2 = Date.now();
for (const [key, line] of reference) {
  const source = key.length === 1 ? context.PINYIN_CHARS : context.PINYIN_WORDS;
  const found = context.pinyinFind_(source, key, key.length);
  if (found !== line) {
    mismatched += 1;
    if (mismatched < 6) console.log(`  FAIL ${key}: found ${JSON.stringify(found)}`);
  }
}
console.log(`  ${reference.size} entries, ${mismatched} wrong, ${Date.now() - started2} ms`);
if (mismatched) failed += 1;

// Keys that are not in the dictionary must come back empty rather than wander.
let phantom = 0;
for (const key of ["鿕", "一鿿", "𠀀", "zz", "。", "", "行动行动行动"]) {
  const source = key.length === 1 ? context.PINYIN_CHARS : context.PINYIN_WORDS;
  if (key && context.pinyinFind_(source, key, key.length) !== null) phantom += 1;
}
console.log(`  ${phantom} phantom hits (want 0)`);
if (phantom) failed += 1;

const started = Date.now();
for (let i = 0; i < 500; i += 1) PINYIN("我们需要立即行动");
console.log(`\n500 sentences in ${Date.now() - started} ms (tables already built)`);

process.exit(failed ? 1 : 0);
