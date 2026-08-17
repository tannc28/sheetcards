/** Runs the .gs files as plain JS and checks the readings a learner would notice. */

const fs = require("fs");
const vm = require("vm");
const path = require("path");

const here = __dirname;
const context = vm.createContext({ console });
for (const file of ["PinyinData.gs", "Pinyin.gs"]) {
  vm.runInContext(fs.readFileSync(path.join(here, file), "utf8"), context, { filename: file });
}
const { PINYIN, PINYIN_NUM } = context;

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

console.log("\nstyles:");
for (const [style, expected] of [["number", "xing2dong4"], ["plain", "xingdong"]]) {
  const got = PINYIN("行动", style);
  console.log(`  ${style}: ${got}${got === expected ? "" : ` (expected ${expected})`}`);
  if (got !== expected) failed += 1;
}
console.log(`  PINYIN_NUM: ${PINYIN_NUM("银行")}`);

console.log("\nrange:", JSON.stringify(PINYIN([["行动"], ["银行"]])));

const started = Date.now();
for (let i = 0; i < 500; i += 1) PINYIN("我们需要立即行动");
console.log(`\n500 sentences in ${Date.now() - started} ms (tables already built)`);

process.exit(failed ? 1 : 0);
