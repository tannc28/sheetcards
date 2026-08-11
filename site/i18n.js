/**
 * The page's own text, in English and Vietnamese.
 *
 * What is *not* here: the warnings a sheet produces. Those come out of
 * `sheet_config.warnings` — the add-on's own code, running in the browser — and
 * they are word for word what Anki will tell you at sync time. Translating them
 * here would make the preview say something the add-on never says, which is the
 * one thing this page exists not to do. They stay in English, and the detail
 * panel says why.
 *
 * English is the default. Vietnamese is offered because the person who maintains
 * this add-on reads Vietnamese; anyone else gets the language they came with.
 */

const STRINGS = {
  // --- control bar --------------------------------------------------------
  brandTag: { en: "preview", vi: "xem trước" },
  urlPlaceholder: {
    en: "https://docs.google.com/spreadsheets/d/…/edit",
    vi: "https://docs.google.com/spreadsheets/d/…/edit",
  },
  urlLabel: { en: "Google Sheets link", vi: "Link Google Sheets" },
  deckPlaceholder: { en: "deck name", vi: "tên deck" },
  deckLabel: { en: "Deck name", vi: "Tên deck" },
  go: { en: "Preview", vi: "Xem trước" },
  or: { en: "or", vi: "hoặc" },
  pick: { en: "Upload a file", vi: "Tải file lên" },
  pickLabel: {
    en: "Preview a file from this computer — .xlsx, .xlsm, .csv or .tsv",
    vi: "Xem trước file trên máy — .xlsx, .xlsm, .csv hoặc .tsv",
  },
  tabLabel: { en: "Sheet in the workbook", vi: "Trang trong file" },
  dropHere: { en: "Drop the file to preview it", vi: "Thả file vào đây để xem trước" },
  dropTypes: {
    en: ".xlsx, .xlsm, .csv or .tsv — nothing leaves this browser",
    vi: ".xlsx, .xlsm, .csv hoặc .tsv — file không rời khỏi trình duyệt",
  },

  // --- status -------------------------------------------------------------
  booting: { en: "Starting Python…", vi: "Đang khởi động Python…" },
  loadingCode: {
    en: "Loading the add-on's code…",
    vi: "Đang tải code của add-on…",
  },
  downloading: { en: "Downloading the sheet…", vi: "Đang tải sheet…" },
  reading: { en: "Reading the file…", vi: "Đang đọc file…" },
  analysing: {
    en: "Running the add-on's code…",
    vi: "Đang chạy code của add-on…",
  },
  loading: { en: "Loading…", vi: "Đang tải…" },
  readRows: {
    en: (n, s) => `${n} rows · ${s} will sync`,
    vi: (n, s) => `${n} dòng · ${s} sẽ sync`,
  },
  bootFailed: {
    en: (m) => `Could not start Python: ${m}`,
    vi: (m) => `Không khởi động được Python: ${m}`,
  },

  // --- errors -------------------------------------------------------------
  notASheet: {
    en: "That is not a Google Sheets link.",
    vi: "Đây không phải link Google Sheets.",
  },
  unreadableFile: {
    en: (m) => `The browser could not read that file: ${m}`,
    vi: (m) => `Trình duyệt không đọc được file đó: ${m}`,
  },
  unreachable: {
    en:
      "The browser could not reach the sheet. This is what the add-on sees " +
      "when a sheet is private: Share → “Anyone with the link” → Viewer.",
    vi:
      "Trình duyệt không đọc được sheet. Add-on cũng gặp đúng lỗi này khi sheet " +
      "còn private: Share → “Anyone with the link” → Viewer.",
  },
  refused: {
    en:
      "Google refused the download — the sheet is not shared. " +
      "Share → “Anyone with the link” → Viewer, then try again.",
    vi:
      "Google từ chối tải — sheet chưa được share. " +
      "Share → “Anyone with the link” → Viewer rồi thử lại.",
  },
  httpError: {
    en: (code) => `Google returned HTTP ${code}.`,
    vi: (code) => `Google trả về HTTP ${code}.`,
  },

  // --- demo ---------------------------------------------------------------
  demoNote: {
    en:
      "Showing an example sheet — an HSK 4 deck with a settings row, so you can " +
      "see what the directives do. Paste your own link above to read yours instead.",
    vi:
      "Đang hiện sheet ví dụ — một deck HSK 4 có settings row, để bạn thấy các " +
      "directive làm gì. Dán link của bạn ở trên để đọc sheet của bạn.",
  },

  // --- the numbers --------------------------------------------------------
  statRows: { en: "rows in the sheet", vi: "dòng trong sheet" },
  statWithId: { en: "with an ID", vi: "có ID" },
  statSync: { en: "marked for sync", vi: "sẽ sync" },
  statNotes: { en: "notes in Anki", vi: "note trong Anki" },
  statCloze: { en: "cloze rows", vi: "dòng cloze" },
  statDecks: { en: "decks", vi: "deck" },

  // --- panes --------------------------------------------------------------
  decks: { en: "Decks", vi: "Deck" },
  allDecks: { en: "All decks", vi: "Tất cả deck" },
  noSyncRows: {
    en: "No rows are marked for sync.",
    vi: "Không dòng nào được đánh dấu sync.",
  },
  rows: { en: "Rows", vi: "Dòng" },
  noRowsHere: { en: "No rows in this deck.", vi: "Deck này không có dòng nào." },
  noRowsAtAll: { en: "No rows to show.", vi: "Không có dòng nào để hiện." },
  sheetDetail: { en: "Sheet detail", vi: "Chi tiết sheet" },
  downloadApkg: { en: "Download .apkg", vi: "Tải .apkg" },
  apkgNote: {
    en:
      "Import it straight into AnkiDroid or AnkiMobile — no desktop needed. " +
      "Importing again updates these notes rather than duplicating them, but it " +
      "cannot delete: a row you remove from the sheet stays in Anki. That is what " +
      "the add-on is still for.",
    vi:
      "Import thẳng vào AnkiDroid hoặc AnkiMobile — không cần máy tính. Import lại " +
      "sẽ cập nhật chứ không nhân đôi, nhưng không xoá được: dòng bạn xoá khỏi sheet " +
      "vẫn còn trong Anki. Đó là chỗ add-on vẫn cần thiết.",
  },
  packing: { en: "Building the package…", vi: "Đang dựng gói…" },
  packed: {
    en: (kb) => `Package ready — ${kb} KB`,
    vi: (kb) => `Gói đã xong — ${kb} KB`,
  },
  packFailed: {
    en: (m) => `Could not build the package: ${m}`,
    vi: (m) => `Không dựng được gói: ${m}`,
  },

  // --- tabs ---------------------------------------------------------------
  tabFront: { en: "front", vi: "mặt trước" },
  tabBoth: { en: "both", vi: "cả hai" },
  tabBack: { en: "back", vi: "mặt sau" },
  tabTemplate: { en: "template", vi: "template" },
  prevRow: { en: "Previous row", vi: "Dòng trước" },
  nextRow: { en: "Next row", vi: "Dòng sau" },

  // --- card ---------------------------------------------------------------
  rowSkipped: {
    en: "This row is not ticked in the SYNC column, so the sync skips it.",
    vi: "Dòng này chưa tick ở cột SYNC nên sync sẽ bỏ qua.",
  },
  rowInvalid: {
    en: "This row has no ID, so the sync counts it as broken and skips it.",
    vi: "Dòng này không có ID nên sync coi là hỏng và bỏ qua.",
  },
  clozeStranded: {
    en: (cols) =>
      `The deletion in <code>${cols}</code> is not on the front, so Anki blanks ` +
      `the prompt and prints the raw <code>{{c1::…}}</code> below. The picture ` +
      `above shows that faithfully.`,
    vi: (cols) =>
      `Chỗ trống nằm ở <code>${cols}</code> chứ không ở mặt trước, nên Anki để ` +
      `trống câu hỏi và in nguyên <code>{{c1::…}}</code> bên dưới. Ảnh trên tái ` +
      `hiện đúng như vậy.`,
  },
  missingFields: {
    en: (f) => `Template references a field the row has no column for: <code>${f}</code>`,
    vi: (f) => `Template gọi field mà dòng này không có cột: <code>${f}</code>`,
  },
  unknownFilters: {
    en: (f) => `Filter not reproduced here: <code>${f}</code>`,
    vi: (f) => `Filter trang này chưa mô phỏng: <code>${f}</code>`,
  },
  deckAndTags: { en: "Deck", vi: "Deck" },
  tagsLabel: { en: "tags", vi: "tags" },

  // --- detail -------------------------------------------------------------
  warnings: { en: "Warnings", vi: "Cảnh báo" },
  warnSettingsRow: { en: "Settings row", vi: "Settings row" },
  warnClozeTitle: {
    en: "Cloze in a column that is not on the front",
    vi: "Cloze nằm ở cột không phải mặt trước",
  },
  warnClozeBody: {
    en: (count, rows, cols, prompt) =>
      `${count} row${count > 1 ? "s" : ""} (${rows}) put the deletion in ` +
      `<code>${cols}</code>, but the card's prompt is <code>${prompt}</code>. Anki ` +
      `renders a clozed field that has no deletion as nothing, so these cards come ` +
      `out with an empty front and the literal <code>{{c1::…}}</code> text on the ` +
      `back. Add <code>cloze</code> to that column in the settings row.`,
    vi: (count, rows, cols, prompt) =>
      `${count} dòng (${rows}) đặt chỗ trống ở <code>${cols}</code>, nhưng câu hỏi ` +
      `của thẻ là <code>${prompt}</code>. Anki render một field bọc cloze mà không ` +
      `có chỗ trống thành rỗng, nên mấy thẻ này ra mặt trước trắng và in nguyên ` +
      `<code>{{c1::…}}</code> ở mặt sau. Thêm <code>cloze</code> vào cột đó trong ` +
      `settings row.`,
  },
  warnDuplicateTitle: { en: "Duplicate IDs", vi: "ID trùng" },
  warnDuplicateBody: {
    en: (ids) =>
      `${ids}. Notes are keyed by ID, so only one row of each survives the sync.`,
    vi: (ids) =>
      `${ids}. Note được khoá theo ID, nên mỗi ID chỉ một dòng sống sót sau sync.`,
  },
  warningsFrom: {
    en:
      "The ones labelled “Settings row” are the add-on's own words, unchanged, so " +
      "they are exactly what Anki will tell you at sync time — which is why they " +
      "stay in English. Nothing is silently ignored: a value the add-on does not " +
      "understand is refused, never guessed at, and the column keeps its default " +
      "until the sheet is fixed.",
    vi:
      "Những dòng gắn nhãn “Settings row” là nguyên văn add-on nói, không sửa — " +
      "đúng câu chữ Anki sẽ báo lúc sync, nên tôi giữ tiếng Anh. Không có gì bị bỏ " +
      "qua âm thầm: giá trị add-on không hiểu thì bị từ chối chứ không đoán, và cột " +
      "giữ mặc định cho tới khi sheet được sửa.",
  },
  columns: { en: "Columns", vi: "Cột" },
  columnsIntro: {
    en:
      "Only <code>ID</code>, <code>SYNC</code>, <code>SUBDECK n</code> and " +
      "<code>TAGS</code> are reserved. Every other column becomes a note field " +
      "named exactly like its header, in any language.",
    vi:
      "Chỉ <code>ID</code>, <code>SYNC</code>, <code>SUBDECK n</code> và " +
      "<code>TAGS</code> là tên dành riêng. Mọi cột khác thành một field trong " +
      "Anki, tên đúng như header, ngôn ngữ nào cũng được.",
  },
  colColumn: { en: "Column", vi: "Cột" },
  colRole: { en: "Role", vi: "Vai trò" },
  colCard: { en: "Card", vi: "Thẻ" },
  roleId: { en: "the row's key — never regenerated", vi: "khoá của dòng — không bao giờ tạo lại" },
  roleSync: { en: "gates whether the row syncs", vi: "quyết định dòng có sync không" },
  roleTags: { en: "extra Anki tags", vi: "tag thêm cho Anki" },
  roleSubdeck: { en: "one level of the deck path", vi: "một cấp trong đường dẫn deck" },
  roleField: {
    en: "becomes a note field of this name",
    vi: "thành một field trong Anki với tên này",
  },
  roleDuplicate: {
    en: "repeated header — only the first is used",
    vi: "header trùng — chỉ cột đầu được dùng",
  },
  pillFront: { en: "front", vi: "trước" },
  pillBack: { en: "back", vi: "sau" },
  pillHidden: { en: "hidden", vi: "ẩn" },

  settingsRow: { en: "Settings row", vi: "Settings row" },
  noSettingsRow: {
    en:
      "This sheet has no settings row, so the defaults apply: the first content " +
      "column is the front, everything else is the back. Add a row under the " +
      "headers with <code>#config</code> in the ID cell to change that.",
    vi:
      "Sheet này không có settings row nên dùng mặc định: cột nội dung đầu tiên " +
      "là mặt trước, còn lại là mặt sau. Thêm một dòng ngay dưới header với " +
      "<code>#config</code> ở ô ID để đổi.",
  },
  deckWide: { en: "Deck-wide", vi: "Toàn deck" },
  nothingSet: { en: "nothing set", vi: "không đặt gì" },
  defaults: { en: "defaults", vi: "mặc định" },

  noteTypes: { en: "Note types", vi: "Note type" },
  fieldsInOrder: {
    en:
      "Fields, in order — <code>ID</code> leads because Anki uses the first field " +
      "for duplicate detection:",
    vi:
      "Các field theo thứ tự — <code>ID</code> đứng đầu vì Anki dùng field đầu " +
      "tiên để phát hiện trùng:",
  },

  howItWorks: { en: "How this preview works", vi: "Trang này hoạt động ra sao" },
  howItWorksBody: {
    en:
      "The page loads <code>column_model.py</code>, <code>sheet_config.py</code>, " +
      "<code>card_layout.py</code>, <code>tsv_model.py</code> and " +
      "<code>errors.py</code> straight from the add-on and runs them through " +
      "<a href='https://pyodide.org'>Pyodide</a>, so the columns, settings, " +
      "warnings, decks and templates above are computed by the code that will run " +
      "at sync time — not by a second implementation of it. Only the card picture " +
      "is drawn by this page; inside Anki that last step belongs to Anki's own " +
      "renderer, so read the template as exact and the layout as an approximation.",
    vi:
      "Trang này tải thẳng <code>column_model.py</code>, <code>sheet_config.py</code>, " +
      "<code>card_layout.py</code>, <code>tsv_model.py</code> và " +
      "<code>errors.py</code> từ add-on rồi chạy bằng " +
      "<a href='https://pyodide.org'>Pyodide</a>. Nên cột, settings, cảnh báo, deck " +
      "và template ở trên là do chính code sẽ chạy lúc sync tính ra — không phải " +
      "một bản cài lại. Chỉ hình ảnh thẻ là do trang này vẽ; trong Anki bước cuối " +
      "đó thuộc về renderer của Anki, nên hãy đọc template như chính xác và bố cục " +
      "như xấp xỉ.",
  },
  runsAsAnki: {
    en:
      "The card is drawn the way Anki draws it, with nothing filtered out — a cell " +
      "containing script runs here because it would run there. That also means " +
      "previewing a spreadsheet is trusting it, the same way syncing one is.",
    vi:
      "Thẻ được vẽ đúng như Anki vẽ, không lọc bỏ gì — ô chứa script sẽ chạy ở đây " +
      "vì nó cũng chạy trong Anki. Nghĩa là mở preview một sheet là tin sheet đó, " +
      "y như khi sync nó.",
  },
  approxNote: {
    en:
      "The template is exactly what the add-on generates. Turning it into this " +
      "picture is done by this page, not by Anki — treat the layout as a close " +
      "approximation.",
    vi:
      "Template là đúng thứ add-on sinh ra. Biến nó thành hình ảnh này là việc của " +
      "trang, không phải của Anki — hãy coi bố cục là xấp xỉ.",
  },

  templateFrom: {
    en: (name) =>
      `The exact text the add-on writes into Anki for <code>${name}</code>, produced ` +
      `here by the same <code>card_layout.py</code> that runs in the add-on.`,
    vi: (name) =>
      `Đúng đoạn text add-on ghi vào Anki cho <code>${name}</code>, sinh ra ở đây ` +
      `bằng chính <code>card_layout.py</code> đang chạy trong add-on.`,
  },
  frontTemplate: { en: "Front template", vi: "Template mặt trước" },
  backTemplate: { en: "Back template", vi: "Template mặt sau" },

  rowsLegend: {
    en: "Click a row to see its card.",
    vi: "Bấm một dòng để xem thẻ của nó.",
  },
  legendSynced: { en: "syncs", vi: "sẽ sync" },
  legendSkipped: { en: "not ticked in SYNC", vi: "chưa tick SYNC" },
  legendInvalid: { en: "no ID", vi: "không có ID" },
  legendGhost: {
    en: "Blank rows are ignored entirely.",
    vi: "Dòng trống bị bỏ qua hoàn toàn.",
  },
};

export const LANGUAGES = [
  { code: "en", label: "EN" },
  { code: "vi", label: "VI" },
];

const STORAGE_KEY = "s2a-lang";

/** Remembered choice, else the browser's own language, else English. */
function initial() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && LANGUAGES.some((l) => l.code === saved)) return saved;
  } catch {
    /* private browsing: fall through to the browser's language */
  }
  return (navigator.language || "en").toLowerCase().startsWith("vi") ? "vi" : "en";
}

let current = initial();

export const lang = () => current;

export function setLang(code) {
  if (!LANGUAGES.some((l) => l.code === code)) return;
  current = code;
  document.documentElement.lang = code;
  try {
    localStorage.setItem(STORAGE_KEY, code);
  } catch {
    /* nothing to do: the choice simply will not survive a reload */
  }
}

/**
 * The string for `key` in the current language.
 *
 * A missing translation falls back to English rather than to the key, because a
 * half-translated page is still readable while `rowsLegend` on screen is not.
 * tests/test_site_i18n.py fails the build if a key is missing either language.
 */
export function t(key, ...args) {
  const entry = STRINGS[key];
  if (!entry) return key;
  const value = entry[current] ?? entry.en;
  return typeof value === "function" ? value(...args) : value;
}

export { STRINGS };
