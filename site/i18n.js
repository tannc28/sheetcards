/**
 * The page's own text, in English and Vietnamese.
 *
 * What is *not* here: the warnings a sheet produces. Those come out of
 * `sheet_config.warnings` — the add-on's own code, running in the browser — and
 * they are word for word what Anki will tell you at sync time. Translating them
 * here would make the preview say something the add-on never says, which is the
 * one thing this page exists not to do. They stay in English, and the warning
 * banner says why.
 *
 * English is the default. Vietnamese is offered because the person who maintains
 * this add-on reads Vietnamese; anyone else gets the language they came with.
 */

const STRINGS = {
  // --- masthead and entry ---------------------------------------------------
  brandTag: { en: "preview", vi: "xem trước" },
  skip: { en: "Skip to the preview", vi: "Tới phần xem trước" },
  toDark: { en: "Switch to dark", vi: "Chuyển sang nền tối" },

  // --- the editor ---------------------------------------------------------
  guideTag: { en: "editor", vi: "trình soạn" },
  backToPreview: { en: "Preview a sheet", vi: "Xem trước sheet" },
  toGuide: { en: "Build a settings row", vi: "Soạn settings row" },
  edColumn: { en: "Column", vi: "Cột" },
  edName: { en: "Column name", vi: "Tên cột" },
  edValue: { en: "What a cell holds", vi: "Nội dung một ô" },
  edCell: { en: "Settings row cell", vi: "Ô trong settings row" },
  edAdd: { en: "Add a directive", vi: "Thêm directive" },
  edResult: { en: "Result", vi: "Kết quả" },
  edCopy: { en: "Copy", vi: "Copy" },
  edCopied: { en: "Copied — paste it into the settings row", vi: "Đã copy — dán vào settings row" },
  edCopyFailed: { en: "The browser refused to copy", vi: "Trình duyệt không cho copy" },
  edOk: { en: "Every setting was understood", vi: "Mọi setting đều hợp lệ" },
  edRefused: {
    en: (n) => `${n} setting${n === 1 ? "" : "s"} refused`,
    vi: (n) => `${n} setting bị từ chối`,
  },
  edSides: {
    en: (front, back) =>
      `${front} field on the front, ${back} on the back — the same split the sync makes.`,
    vi: (front, back) =>
      `${front} field ở mặt trước, ${back} ở mặt sau — đúng cách sync chia.`,
  },
  toLight: { en: "Switch to light", vi: "Chuyển sang nền sáng" },
  urlPlaceholder: {
    en: "https://docs.google.com/spreadsheets/d/… or a link ending in .xlsx",
    vi: "https://docs.google.com/spreadsheets/d/… hoặc link kết thúc bằng .xlsx",
  },
  urlLabel: { en: "Sheet link", vi: "Link sheet" },
  deckPlaceholder: { en: "My deck", vi: "Deck của tôi" },
  deckLabel: { en: "Deck name", vi: "Tên deck" },
  go: { en: "Preview", vi: "Xem trước" },
  pick: { en: "Upload a file", vi: "Tải file lên" },
  pickLabel: {
    en: "Preview a file from this computer — .xlsx, .xlsm, .csv or .tsv",
    vi: "Xem trước file trên máy — .xlsx, .xlsm, .csv hoặc .tsv",
  },
  orDrop: {
    en: "or drop one anywhere on this page.",
    vi: "hoặc thả file vào bất kỳ đâu trên trang.",
  },
  tabLabel: { en: "Sheet", vi: "Trang" },

  // --- the three panels -----------------------------------------------------
  // Each header doubles as what a shut panel has left to say, so the notes name
  // what is inside rather than repeating the title.
  panelSource: { en: "Source", vi: "Nguồn" },
  panelDeck: { en: "Deck", vi: "Deck" },
  panelCard: { en: "Card", vi: "Thẻ" },

  // --- what each column turned into ---------------------------------------
  roleId: {
    en: "ID — the key every note is matched by",
    vi: "ID — khoá để nhận lại từng note",
  },
  roleSync: {
    en: "SYNC — which rows are written to Anki",
    vi: "SYNC — dòng nào được ghi vào Anki",
  },
  roleTags: { en: "TAGS — extra tags for the row", vi: "TAGS — tag thêm cho dòng" },
  roleSubdeck: {
    en: (level) => `Deck level ${level} — reserved, so it never reaches the card`,
    vi: (level) => `Tầng deck ${level} — cột dành riêng, không bao giờ lên thẻ`,
  },
  roleSubdeckOnly: {
    en: (level) => `Deck level ${level} — files the note, never drawn on the card`,
    vi: (level) => `Tầng deck ${level} — xếp deck cho note, không hiện trên thẻ`,
  },
  roleField: {
    en: (where) => `A field on the ${where}`,
    vi: (where) => `Field ở ${where}`,
  },
  roleDuplicate: {
    en: "Written twice — this one is ignored",
    vi: "Bị ghi hai lần — cột này bị bỏ qua",
  },
  roleUnused: { en: "Not used", vi: "Không dùng tới" },
  sideFront: { en: "front", vi: "mặt trước" },
  sideBack: { en: "back", vi: "mặt sau" },
  sideHidden: { en: "note only, hidden on the card", vi: "chỉ trong note, ẩn trên thẻ" },
  nothingSet: {
    en: "The settings row says nothing about this column.",
    vi: "Settings row không nói gì về cột này.",
  },
  valueInRow: { en: (line) => `Row ${line}`, vi: (line) => `Dòng ${line}` },
  cellEmpty: { en: "empty", vi: "trống" },
  deckNote: {
    en: (sync, total, decks) =>
      `${sync} of ${total} rows sync · ${decks} deck${decks === 1 ? "" : "s"}`,
    vi: (sync, total, decks) => `${sync}/${total} dòng sẽ sync · ${decks} deck`,
  },
  cardNote: {
    en: (line, label) => `Row ${line} — ${label}`,
    vi: (line, label) => `Dòng ${line} — ${label}`,
  },
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
  downloading: { en: "Downloading the file…", vi: "Đang tải file…" },
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
    en:
      "That is neither a Google Sheets link nor a link to an .xlsx file. " +
      "A file's address has to end in .xlsx or .xlsm.",
    vi:
      "Đây không phải link Google Sheets, cũng không phải link tới file .xlsx. " +
      "Link tới file phải kết thúc bằng .xlsx hoặc .xlsm.",
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
      "Showing the example workbook — sixteen sheets, from the smallest one that " +
      "works to every directive at once. Use the sheet picker above to walk " +
      "through them, or paste your own link to read yours instead.",
    vi:
      "Đang hiện file ví dụ — mười sáu sheet, từ sheet đơn giản nhất tới sheet " +
      "dùng hết mọi directive. Dùng ô chọn sheet ở trên để xem lần lượt, hoặc " +
      "dán link của bạn để đọc sheet của bạn.",
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
  downloadApkg: { en: "Download .apkg", vi: "Tải .apkg" },
  // The caveats used to be a four-sentence paragraph under the button, which is a
  // lot of reading to sit permanently under a control most people press once.
  // README.md carries the long version.
  apkgTitle: {
    en:
      "Import straight into AnkiDroid or AnkiMobile. Importing again updates these " +
      "notes rather than duplicating them, but it cannot delete.",
    vi:
      "Import thẳng vào AnkiDroid hoặc AnkiMobile. Import lại sẽ cập nhật chứ không " +
      "nhân đôi, nhưng không xoá được.",
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
