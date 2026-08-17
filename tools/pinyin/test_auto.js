/**
 * Checks the part of the edit trigger that decides what a cell should say.
 *
 * The rest of PinyinAuto.gs is fetching and storing, which needs Sheets. This
 * part does not, and it is the part that can lose someone's work: setValues
 * replaces every cell in the range it covers, so a row this pass has nothing to
 * say about must be handed back exactly as it was found.
 */

const fs = require("fs");
const vm = require("vm");
const path = require("path");

const here = __dirname;
const context = vm.createContext({ console });
for (const file of ["PinyinData.gs", "Pinyin.gs", "PinyinAuto.gs"]) {
  vm.runInContext(fs.readFileSync(path.join(here, file), "utf8"), context, { filename: file });
}
const { pinyinReadingsFor_, pinyinColumnOf_ } = context;

let failed = 0;

function check(name, got, expected) {
  const ok = JSON.stringify(got) === JSON.stringify(expected);
  if (!ok) failed += 1;
  console.log(`${ok ? "ok  " : "FAIL"} ${name}`);
  if (!ok) console.log(`       got ${JSON.stringify(got)}\n  expected ${JSON.stringify(expected)}`);
}

const column = (values) => values.map((v) => [v]);

check(
  "a Chinese word gets its reading",
  pinyinReadingsFor_(column(["行动", "银行"]), column(["w1", "w2"]), column(["", ""])),
  [["xíngdòng"], ["yínháng"]]
);

check(
  "an empty word keeps whatever the cell held",
  pinyinReadingsFor_(column(["行动", ""]), column(["w1", "w2"]), column(["", "typed by hand"])),
  [["xíngdòng"], ["typed by hand"]]
);

check(
  "the settings row is never written into",
  pinyinReadingsFor_(column(["行动", "size=48"]), column(["w1", "#config align=left"]), column(["", "side=front"])),
  [["xíngdòng"], ["side=front"]]
);

check(
  "a cell with nothing Chinese in it is left alone",
  pinyinReadingsFor_(column(["hello"]), column(["w1"]), column(["kept"])),
  null
);

check(
  "nothing to change means nothing is written at all",
  pinyinReadingsFor_(column(["行动"]), column(["w1"]), column(["xíngdòng"])),
  null
);

check(
  "a corrected word overwrites the old reading",
  pinyinReadingsFor_(column(["银行"]), column(["w1"]), column(["xíngdòng"])),
  [["yínháng"]]
);

const headings = ["ID", "Word (Mặt trước)", "Loại từ", "Pinyin", "Nghĩa"];
check("a heading is found by what it contains", pinyinColumnOf_(headings, "Word"), 2);
check("and matching ignores case", pinyinColumnOf_(headings, "pinyin"), 4);
check("a heading that is not there is 0", pinyinColumnOf_(headings, "Nothing"), 0);

process.exit(failed ? 1 : 0);
