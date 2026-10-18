/**
 * The page's own text, in English and Vietnamese.
 *
 * What is *not* here: the warnings a sheet produces. Those come out of
 * `sheet_config.warnings` — the add-on's own code, running in the browser — with
 * a stable code each, and site/sheetwarnings.js says them in both languages
 * (the add-on and its log keep the English sentence).
 *
 * Vietnamese is the default: the site is made for Vietnamese learners first.
 * The Vietnamese keeps every technical word in English — deck, note, field,
 * card, cloze, sync, settings row, every Anki and Google Sheets label — and only
 * the explanation around it is translated. The learners run Anki in English, so
 * a translated term is a word they will never see again. Our own page and button
 * names are ours to translate (Trang chủ, Tạo Sheet), except the product name
 * Sheet to Anki, which stays English in both languages.
 *
 * Each `data-i18n` element in the HTML carries its `vi` string as static text
 * (what shows before any script runs); tests/test_site_i18n.py keeps the two equal.
 */

import { rootLinks, site } from "./paths.js";

const STRINGS = {
  // --- masthead and entry ---------------------------------------------------
  skip: { en: "Skip to Sheet to Anki", vi: "Tới phần Sheet to Anki" },
  toDark: { en: "Switch to dark", vi: "Chuyển sang nền tối" },
  langLabel: { en: "Language", vi: "Ngôn ngữ" },
  close: { en: "Close", vi: "Đóng" },

  // --- the site's own navigation, on every page ---------------------------
  navLabel: { en: "Site", vi: "Các trang" },
  navFootLabel: { en: "Pages (footer)", vi: "Các trang (cuối trang)" },
  navHome: { en: "Home", vi: "Trang chủ" },
  navPreview: { en: "Sheet to Anki", vi: "Sheet to Anki" },
  navSheet: { en: "Create sheet", vi: "Tạo Sheet" },
  navDocs: { en: "Docs", vi: "Docs" },
  docsTag: { en: "docs", vi: "docs" },
  skipMain: { en: "Skip to the content", vi: "Tới nội dung chính" },

  // --- what the browser tab says ------------------------------------------
  // In the reader's language like the rest of the page, and on Sheet to Anki the
  // loaded sheet's name first: that is what tells two open tabs, or two entries
  // in the history, apart.
  titleHome: {
    en: "SheetCards — Anki flashcards from Google Sheets",
    vi: "SheetCards — tạo flashcard Anki từ Google Sheets",
  },
  titleCreate: {
    en: "SheetCards — Sheet to Anki: Anki flashcards from Google Sheets",
    vi: "SheetCards — Sheet to Anki: tạo flashcard Anki từ Google Sheets",
  },
  titleDeck: { en: (name) => `${name} — Sheet to Anki · SheetCards`, vi: (name) => `${name} — Sheet to Anki · SheetCards` },
  titleSheet: {
    en: "SheetCards — Create sheet: write a flashcard sheet on the web",
    vi: "SheetCards — Tạo Sheet: soạn sheet flashcard ngay trên web",
  },
  title404: { en: "Page not found — SheetCards", vi: "Không tìm thấy trang — SheetCards" },
  notFoundTitle: { en: "This page doesn't exist", vi: "Không có trang này" },
  notFoundBody: {
    en: "The link may be old or mistyped. Everything SheetCards has is one of the pages below.",
    vi: "Có thể link đã cũ hoặc gõ nhầm. Mọi thứ của SheetCards đều nằm ở các trang dưới đây.",
  },

  // --- the landing page ---------------------------------------------------
  // Written for somebody who has never used an add-on: what it does, the one
  // file to download, the three steps that get it into Anki, and nothing else.
  homeTitle: {
    en: "Anki flashcards from <mark>Google Sheets</mark>",
    vi: "Tạo flashcard Anki từ <mark>Google Sheets</mark>",
  },
  homeLead: {
    en: "Paste a Google Sheets link, open a file or paste a word list, check every card, then download an .apkg for the Anki app.",
    vi: "Dán link Google Sheets, mở file hoặc dán danh sách từ, xem từng card, rồi tải file .apkg cho app Anki.",
  },
  homeDownload: { en: "Download", vi: "Tải về" },
  homeNeeds: {
    en: "Needs Anki 25.x or later on a computer",
    vi: "Cần Anki 25.x trở lên trên máy tính",
  },

  // The demo: a row of the example workbook and the card it becomes.
  demoLabel: {
    en: "Example: from a row of a sheet to an .apkg on a phone",
    vi: "Ví dụ: từ một dòng trong sheet tới file .apkg trên điện thoại",
  },
  demoEnglish: { en: "English · paper", vi: "English · paper" },
  demoJapanese: { en: "Furigana · sakura", vi: "Furigana · sakura" },
  demoCloze: { en: "Cloze · matcha", vi: "Cloze · matcha" },
  demoWriting: { en: "Chinese writing · momiji", vi: "Viết chữ Hán · momiji" },
  demoFront: { en: "Card front", vi: "Mặt trước card" },
  demoBack: { en: "Card back", vi: "Mặt sau card" },
  demoPause: { en: "Pause the example", vi: "Tạm dừng ví dụ" },
  demoPlay: { en: "Play the example", vi: "Chạy ví dụ" },
  // Anki's own words on its review screen, kept in English in both languages:
  // the learners this is for run Anki in English, and a demo that says "Lại"
  // where their Anki says "Again" is showing a screen they will never see.
  showAnswer: { en: "Show Answer", vi: "Show Answer" },

  featTitle: { en: "One sheet, many kinds of card", vi: "Một sheet, nhiều kiểu card" },
  featSpeechTitle: { en: "Read aloud", vi: "Đọc thành tiếng" },
  featSpeech: {
    en: "Anki reads the column you choose aloud, with the voices on your device.",
    vi: "Anki đọc to cột bạn chọn bằng giọng có sẵn trên máy.",
  },
  featTplTitle: {
    en: "8 ready-made templates",
    vi: "8 template có sẵn",
  },
  featTpl: {
    en: "Or save and upload templates of your own.",
    vi: "Hoặc lưu, upload template của riêng bạn.",
  },
  featKeepTitle: {
    en: "Re-importing keeps your progress",
    vi: "Import lại vẫn giữ tiến độ",
  },
  featKeep: {
    en: "Add or fix words and import the new file: cards are updated, not doubled.",
    vi: "Thêm hay sửa từ rồi import file mới: card được cập nhật, không nhân đôi.",
  },
  featDevicesTitle: {
    en: "Phone or computer",
    vi: "Điện thoại hay máy tính",
  },
  featDevices: {
    en: "Every step works on both.",
    vi: "Mọi bước đều làm được trên cả hai.",
  },
  featPreviewTitle: {
    en: "See every card before you download",
    vi: "Xem từng card trước khi tải",
  },
  featPreview: {
    en: "Cards look just as they will in Anki, with Show Answer, before you download the .apkg.",
    vi: "Card hiện đúng như trong Anki, có Show Answer, trước khi bạn tải file .apkg.",
  },
  soonTitle: {
    en: "Coming soon",
    vi: "Sắp có",
  },
  soonBadge: {
    en: "Coming soon",
    vi: "Sắp có",
  },
  soonTplTitle: {
    en: "Template library",
    vi: "Thư viện template",
  },
  soonTpl: {
    en: "Browse and use templates other people share.",
    vi: "Xem và dùng template người khác chia sẻ.",
  },
  soonThemeTitle: {
    en: "Theme library",
    vi: "Thư viện Theme",
  },
  soonTheme: {
    en: "More themes to dress your cards in.",
    vi: "Thêm nhiều theme để khoác lên card của bạn.",
  },
  soonAsk: {
    en: "Want these sooner? Tell us →",
    vi: "Muốn có sớm? Góp ý →",
  },

  homeHow: { en: "How it works", vi: "Cách hoạt động" },
  homeHow1Title: {
    en: "Have a word list",
    vi: "Có danh sách từ",
  },
  homeHow1: {
    en: "A Google Sheet, an Excel file, or a list in your notes. None yet? Write one in Create sheet: pick a template, set up columns &amp; card, then add cards.",
    vi: "Một Google Sheet, file Excel, hay danh sách trong ghi chú. Chưa có thì soạn trong Tạo Sheet: chọn template, đặt cột &amp; card, rồi thêm thẻ.",
  },
  homeHow2Title: {
    en: "Sheet to Anki",
    vi: "Sheet to Anki",
  },
  homeHow2: {
    en: "Paste a link, open a file or paste text, check each real card, then press Download .apkg.",
    vi: "Dán link, mở file hoặc dán chữ, xem từng card thật, rồi bấm Download .apkg.",
  },
  homeHow3Title: {
    en: "Open it in the Anki app",
    vi: "Mở bằng app Anki",
  },
  homeHow3: {
    en: "Open the .apkg in the Anki app (AnkiDroid, AnkiMobile or Anki on a computer). Added words? Import again: cards are updated, progress kept.",
    vi: "Mở file .apkg bằng app Anki (AnkiDroid, AnkiMobile hoặc Anki trên máy tính). Thêm từ rồi import lại: card được cập nhật, giữ tiến độ.",
  },
  homeFootNote: {
    en: "MIT licence. SheetCards is not made by or affiliated with Anki or Ankitects.",
    vi: "Giấy phép MIT. SheetCards không do Anki hay Ankitects làm ra và không liên kết với họ.",
  },


  // --- Create sheet ---------------------------------------------------------
  // The step before Sheet to Anki: a whole sheet written in the browser. Its
  // reader is usually on a phone and may never have opened a spreadsheet, so
  // the words are a learner's — "từ", a word — rather than a spreadsheet's.
  skipSheet: { en: "Skip to Create sheet", vi: "Tới phần Tạo Sheet" },
  shStep1: { en: "Write the sheet", vi: "Viết sheet" },
  shTitle: {
    en: "Write a flashcard sheet <mark>right on the web</mark>",
    vi: "Soạn sheet flashcard <mark>ngay trên web</mark>",
  },
  shLead: {
    en: "No Google Sheets needed. Pick a template, type your words, then press Make flashcards for an .apkg that AnkiDroid, AnkiMobile or Anki opens.",
    vi: "Không cần Google Sheets. Chọn một mẫu, gõ từ của bạn, rồi bấm Tạo flashcard để có file .apkg cho AnkiDroid, AnkiMobile hoặc Anki.",
  },
  shPickTemplate: { en: "Or start from a template", vi: "Hoặc bắt đầu từ một template" },
  tplBasic: { en: "Front / Back", vi: "Mặt trước / Mặt sau" },
  tplBasicText: {
    en: "A basic card: one side asks, the other answers",
    vi: "Card cơ bản: một mặt hỏi, một mặt đáp",
  },
  tplBlankName: { en: "New sheet", vi: "Sheet mới" },
  tplVocab: { en: "Vocabulary", vi: "Học từ vựng" },
  tplVocabText: {
    en: "A word, how it sounds, its meaning and an example — in the language you are learning, read aloud",
    vi: "Từ, phiên âm, nghĩa và câu ví dụ — bằng ngôn ngữ bạn đang học, có đọc to",
  },
  tplVocabName: { en: "Vocabulary", vi: "Từ vựng" },
  tplIosVoice: {
    en: "On iPhone the voice may need downloading: Settings → Accessibility → Spoken Content → Voices",
    vi: "Trên iPhone có thể phải tải giọng đọc: Cài đặt → Trợ năng → Nội dung được đọc → Giọng nói",
  },
  shSettingsDocs: { en: "Every settings-row key", vi: "Mọi key của settings row" },
  shSettingsLine: {
    en: "The settings row is row 2 of the sheet, right under the column names: each cell says how that column shows on the card — front or back, text size, read aloud or not. Pick a column and add directives below.",
    vi: "Settings row là dòng 2 của sheet, ngay dưới tên cột: mỗi ô ghi cột đó hiện thế nào trên card — mặt trước hay sau, cỡ chữ, có đọc to không. Chọn một cột rồi thêm directive bên dưới.",
  },
  vocabLang: { en: "Your words are in", vi: "Từ của bạn bằng tiếng" },
  vocabSpeakWord: { en: "Read Word aloud", vi: "Đọc to Word" },
  vocabSpeakExample: { en: "Read Example aloud", vi: "Đọc to Example" },
  tplCustom: { en: "Custom", vi: "Tùy chỉnh" },
  tplCustomText: {
    en: "Choose your own columns, front / back",
    vi: "Tự chọn cột, mặt trước / mặt sau",
  },
  // The Tùy chỉnh builder (sheet.js, paintBuilder).
  bFrontName: { en: "Front", vi: "Mặt trước" },
  bBackName: { en: "Back", vi: "Mặt sau" },
  bColN: { en: (n) => `Column ${n}`, vi: (n) => `Cột ${n}` },
  bColName: { en: "Column name", vi: "Tên cột" },
  bSide: { en: "Side", vi: "Mặt" },
  bSideFront: { en: "Front", vi: "Mặt trước" },
  bSideBack: { en: "Back", vi: "Mặt sau" },
  bSideHide: { en: "Hidden", vi: "Ẩn" },
  bTts: { en: "Read aloud", vi: "Đọc to" },
  bImage: { en: "Picture", vi: "Ảnh" },
  bType: { en: "Type the answer", vi: "Gõ đáp án" },
  bHint: { en: "Hint", vi: "Gợi ý" },
  bUp: { en: "Move up", vi: "Lên trên" },
  bDown: { en: "Move down", vi: "Xuống dưới" },
  bRemove: { en: "Remove column", vi: "Xoá cột" },
  bAdd: { en: "Add column", vi: "Thêm cột" },
  bLang: { en: "Read aloud in", vi: "Đọc to bằng tiếng" },
  bSample: { en: "Example for this column", vi: "Ví dụ cho cột này" },
  bAdvanced: { en: "Advanced settings", vi: "Tùy chỉnh nâng cao" },
  tplCustomName: { en: "My deck", vi: "Deck của tôi" },
  tplSheetCaption: {
    en: "Example: the sample row shows what the sheet looks like, and the card beside it is made from it. Your sheet starts empty — you add your words in step ② Add cards.",
    vi: "Ví dụ: dòng mẫu cho thấy sheet trông thế nào, và card bên cạnh được tạo từ nó. Sheet của bạn bắt đầu trống — bạn thêm từ ở bước ② Thêm thẻ.",
  },
  tplNoIdNote: {
    en: "Changing the words on the front makes a new card (the old card's progress is lost).",
    vi: "Sửa chữ ở mặt trước sẽ thành card mới (mất tiến độ của card cũ).",
  },
  tplSheetLabel: { en: "Example sheet", vi: "Sheet ví dụ" },
  tplCsv: { en: "Download .csv", vi: "Tải file .csv mẫu" },
  vocabCreate: { en: "Create sheet", vi: "Tạo sheet" },
  shOpenFile: { en: "Open .xlsx/.csv file", vi: "Mở file .xlsx/.csv" },
  shOpenFileHint: {
    en: "The .csv or .xlsx you saved — open it and carry on adding words",
    vi: "File .csv hoặc .xlsx bạn đã lưu — mở ra là thêm từ tiếp được ngay",
  },
  shIdsKept: {
    en: "Every word keeps its ID, so re-importing the .apkg updates the notes and keeps your review progress.",
    vi: "ID của từng từ giữ nguyên, nên import lại file .apkg sẽ cập nhật note và giữ tiến độ ôn.",
  },
  shMyTemplates: { en: "Your templates", vi: "Template của bạn" },
  shMyTemplatesHint: {
    en: "Kept in this browser only, never sent anywhere. To give one to someone: pick it, Create sheet, then Share link.",
    vi: "Chỉ lưu trong trình duyệt này, không gửi đi đâu. Muốn gửi cho người khác: chọn template, Tạo sheet, rồi bấm Share link.",
  },
  tplUpload: { en: "Upload a template", vi: "Tải lên template" },
  tplUploadHint: {
    en: ".xlsx or .csv — its columns and settings row are kept, ready for new words",
    vi: ".xlsx hoặc .csv — giữ tên cột và settings row, sẵn sàng cho từ mới",
  },
  tplSaveMine: { en: "Save as template", vi: "Lưu làm template" },
  tplMineText: {
    en: (cols) => `Your template · ${cols} column${cols === 1 ? "" : "s"}`,
    vi: (cols) => `Template của bạn · ${cols} cột`,
  },
  tplMineShare: {
    en: "Create sheet to add words. To give this template to someone: Create sheet, then Share link.",
    vi: "Chọn Tạo sheet để thêm từ. Muốn gửi template này cho người khác: Tạo sheet rồi bấm Share link.",
  },
  tplSaved: {
    en: (name) => `Saved “${name}” to Your templates`,
    vi: (name) => `Đã lưu “${name}” vào Template của bạn`,
  },
  tplUpdated: { en: (name) => `Updated the template “${name}”`, vi: (name) => `Đã cập nhật template “${name}”` },
  tplFull: {
    en: (n) => `You already have ${n} templates — delete one first`,
    vi: (n) => `Đã có ${n} template — xoá bớt một cái trước`,
  },
  tplTooBig: { en: "This sheet is too big to keep as a template", vi: "Sheet này quá lớn để lưu làm template" },
  tplNotStored: { en: "This browser won't keep templates", vi: "Trình duyệt này không cho lưu template" },
  tplEmpty: { en: "This sheet has no columns to keep", vi: "Sheet này không có cột nào để lưu" },
  tplDelete: { en: "Delete template", vi: "Xoá template" },
  tplDeleteTitle: { en: (name) => `Delete the template “${name}”?`, vi: (name) => `Xoá template “${name}”?` },
  tplDeleteText: {
    en: "It is kept only in this browser, so it cannot be brought back. Sheets made from it are not touched.",
    vi: "Template chỉ lưu trong trình duyệt này, xoá rồi không lấy lại được. Sheet đã tạo từ nó vẫn còn nguyên.",
  },
  tplDeleteYes: { en: "Delete", vi: "Xoá" },
  tplDeleted: { en: (name) => `Deleted the template “${name}”`, vi: (name) => `Đã xoá template “${name}”` },
  tplPicture: { en: "Vocabulary + picture", vi: "Từ vựng + ảnh" },
  tplPictureText: {
    en: "The picture asks; Word (read aloud) and Meaning answer",
    vi: "Ảnh ở mặt trước; Word (có đọc to) và Meaning ở mặt sau",
  },
  tplPictureName: { en: "Picture words", vi: "Từ vựng ảnh" },
  tplReverse: { en: "Both ways (reverse)", vi: "Hai chiều (reverse)" },
  tplReverseText: {
    en: "Two cards per word: Word → Meaning, and Meaning → Word",
    vi: "Mỗi từ thành 2 card: Word → Meaning, và Meaning → Word",
  },
  tplReverseName: { en: "Vocabulary both ways", vi: "Từ vựng hai chiều" },
  tplTyped: { en: "Type the answer", vi: "Gõ đáp án" },
  tplTypedText: {
    en: "Meaning asks; type the Word — accents forgiven — then hear it",
    vi: "Meaning ở mặt trước; gõ Word (không cần đúng dấu) rồi nghe đọc to",
  },
  tplTypedName: { en: "Typing vocabulary", vi: "Gõ từ vựng" },
  tplThemeLabel: { en: "Theme", vi: "Theme" },
  tplThemeNone: { en: "Default", vi: "Mặc định" },
  tplThemeNoneText: { en: "Anki's own colours", vi: "Màu mặc định của Anki" },
  tplHanzi: { en: "Write Chinese characters", vi: "Viết chữ Hán" },
  tplHanziText: {
    en: "Meaning and pinyin ask; write the character stroke by stroke, then watch the strokes and hear it",
    vi: "Mặt trước có nghĩa và pinyin; viết chữ Hán từng nét, mặt sau chạy lại thứ tự nét và đọc to",
  },
  tplHanziName: { en: "Chinese characters", vi: "Chữ Hán" },
  tplKanji: { en: "Japanese with furigana", vi: "Tiếng Nhật (furigana)" },
  tplKanjiText: {
    en: "Kanji with its reading drawn above it: write 日本語[にほんご]",
    vi: "Kanji có cách đọc hiện nhỏ phía trên: viết 日本語[にほんご]",
  },
  tplKanjiName: { en: "Japanese vocabulary", vi: "Từ vựng tiếng Nhật" },
  thContrast: { en: "High contrast, easiest to read", vi: "Tương phản cao, dễ đọc nhất" },
  thMatcha: { en: "Soft green-tea paper", vi: "Nền xanh trà dịu mắt" },
  thMomiji: { en: "Autumn maple leaves", vi: "Lá phong mùa thu" },
  thPaper: { en: "Warm paper and ink", vi: "Giấy ngà, chữ mực" },
  thSakura: { en: "Cherry blossom pink", vi: "Hoa anh đào hồng" },
  thYuki: { en: "Cool winter snow", vi: "Tuyết mùa đông" },
  tplRevFront: { en: "Card 2 (reverse) · front", vi: "Card 2 (reverse) · mặt trước" },
  tplRevBack: { en: "Card 2 (reverse) · back", vi: "Card 2 (reverse) · mặt sau" },
  shHaveSheet: { en: "Already have a Google Sheet?", vi: "Đã có Google Sheet?" },
  shHaveSheetHint: { en: "Paste its link straight into Sheet to Anki", vi: "Dán link thẳng vào Sheet to Anki" },
  shPrivacy: {
    en: "The sheet is kept in this browser. Nothing is sent to SheetCards' servers.",
    vi: "Sheet được lưu ngay trong trình duyệt này. Không có gì được gửi lên máy chủ của SheetCards.",
  },
  shWorkLabel: { en: "Your sheet", vi: "Sheet của bạn" },
  // The set's name — `name=` in the marker — is its deck and its identity in
  // Anki, which is why it is asked for and why renaming it asks first.
  setName: { en: "Flashcard set name", vi: "Tên bộ flashcard" },
  setNameEmpty: {
    en: "Give the flashcard set a name to create the sheet.",
    vi: "Đặt tên cho bộ flashcard để tạo sheet.",
  },
  setNameUsed: {
    en: "This name is already used for another flashcard set — the same name overwrites that deck in Anki.",
    vi: "Tên này đã dùng cho một bộ flashcard khác — trùng tên sẽ ghi đè vào deck đó trong Anki.",
  },
  renameTitle: { en: "Rename the flashcard set?", vi: "Đổi tên bộ flashcard?" },
  renameText: {
    en: (old, name) =>
      `A new name is a new deck in Anki; your progress stays in the deck “${old}”. Rename it to “${name}” anyway?`,
    vi: (old, name) =>
      `Đổi tên = deck mới trong Anki; tiến độ học ở deck cũ “${old}”. Vẫn đổi thành “${name}”?`,
  },
  renameYes: { en: "Rename", vi: "Vẫn đổi" },
  renameNo: { en: "Keep the name", vi: "Giữ tên cũ" },
  nameOffer: {
    en: (file) =>
      `This sheet does not carry its flashcard set's name yet, so it is recognised by the file name “${file}”: keep the name as it is and importing still updates the deck you have.`,
    vi: (file) =>
      `Sheet này chưa ghi tên bộ flashcard bên trong, nên được nhận ra theo tên file “${file}”: giữ nguyên tên thì import vẫn cập nhật deck đang có.`,
  },
  nameOfferGo: { en: "Write the name into the sheet", vi: "Ghi tên vào sheet" },
  // The same draft open in two tabs (sheet.js, the storage event).
  otherTab: {
    en: "This sheet is being edited in another tab. Whichever tab saves last overwrites the other.",
    vi: "Sheet này đang được sửa ở một tab khác. Tab nào lưu sau sẽ ghi đè tab kia.",
  },
  otherTabGo: { en: "Open the latest version", vi: "Mở bản mới nhất" },
  nameAddTitle: { en: "Write the name into the sheet?", vi: "Ghi tên vào sheet?" },
  nameAddText: {
    en: (_old, name) =>
      `From now on the sheet is “${name}” whatever its file is called or saved as. The next import makes a new deck in Anki, this once: progress in the old deck does not move over.`,
    vi: (_old, name) =>
      `Từ nay sheet mang tên “${name}” dù file bị đổi tên hay lưu ra .xlsx. Lần import tới sẽ là một deck mới trong Anki, chỉ một lần này: tiến độ học ở deck cũ không chuyển sang.`,
  },
  nameAddYes: { en: "Write it in", vi: "Ghi tên" },
  // A sheet keyed by its first column (Basic, Học từ vựng).
  keyBlank: {
    en: (col, rows) => `Row ${rows}: words but nothing in ${col}, the column each word is known by. Fill it in or clear the row.`,
    vi: (col, rows) => `Dòng ${rows}: có chữ nhưng ô ${col} trống — cột ${col} là khoá của từng từ. Điền vào hoặc xoá dòng.`,
  },
  keyTwice: {
    en: (word, rows, second) => `“${word}” is on rows ${rows}: both become cards, the second as “${second}”.`,
    vi: (word, rows, second) => `“${word}” có ở dòng ${rows}: cả hai đều thành card, dòng sau thành “${second}”.`,
  },
  idDup: {
    en: (id, rows) => `ID ${id} is used twice (rows ${rows}). Each word needs its own ID — fix it, then try again.`,
    vi: (id, rows) => `ID ${id} bị trùng (dòng ${rows}). Mỗi từ cần một ID riêng — sửa rồi thử lại.`,
  },
  idBlank: {
    en: (rows) => `Row ${rows} has no ID. Each word needs one.`,
    vi: (rows) => `Dòng ${rows} chưa có ID. Mỗi từ cần một ID.`,
  },
  idReused: {
    en: (id) =>
      `ID ${id} belonged to a word you deleted. Anki keeps that word's review history, so a new word with this ID would inherit it — give it a new ID.`,
    vi: (id) =>
      `ID ${id} từng thuộc về một từ đã xoá. Anki vẫn giữ lịch sử ôn của từ đó, nên từ mới mang ID này sẽ thừa hưởng nó — hãy cho từ mới một ID khác.`,
  },
  idFixFirst: { en: "Fix the IDs first", vi: "Sửa ID trước đã" },
  shNotSaved: {
    en: "Not saved — this browser won't keep a draft",
    vi: "Chưa lưu — trình duyệt này không giữ nháp",
  },
  shSavedLink: { en: "Saved in your sheet link", vi: "Đã lưu vào link sheet" },
  shSavedFile: { en: "Saved to a file", vi: "Đã lưu file" },
  shUnsavedLink: { en: "Not saved — only a draft in this browser", vi: "Chưa lưu link — mới là nháp trong trình duyệt" },
  shUnsavedFile: { en: "Not saved — only a draft in this browser", vi: "Chưa lưu file — mới là nháp trong trình duyệt" },
  shSaveLink: { en: "Save sheet link", vi: "Lưu link sheet" },
  shSaveLinkLead: {
    en: "Keep this link (send it to yourself in Messenger, Telegram or Notes). Next time: open the link in Chrome or Safari → add words → Make flashcards. Added words? Save a new link — the old one opens the old sheet.",
    vi: "Giữ link này (gửi cho chính bạn qua Messenger/Telegram hoặc Ghi chú). Lần sau mở link bằng Chrome hoặc Safari → thêm từ → Tạo flashcard. Thêm từ rồi thì lưu link mới — link cũ mở bản cũ.",
  },
  shShareLabel: {
    en: (name, n, when) => `${name} — ${n} word${n === 1 ? "" : "s"} — ${when}`,
    vi: (name, n, when) => `${name} — ${n} từ — ${when}`,
  },
  shLinkKept: { en: "Link sent — your sheet is in it", vi: "Đã gửi link — sheet nằm trong link đó" },
  shFileLineLink: {
    en: "The draft lives only in this browser, which may clear it (an iPhone does after 7 days away). Press Save sheet link and send it to yourself to keep the sheet.",
    vi: "Bản nháp chỉ nằm trong trình duyệt này, và trình duyệt có thể xoá nó (iPhone xoá sau 7 ngày không mở trang). Bấm Lưu link sheet rồi gửi cho chính bạn để giữ sheet.",
  },
  shOtherFormatsAll: { en: "Need a .csv or .xlsx file?", vi: "Cần file .csv / .xlsx?" },
  shUnlinkedTitle: { en: "Save the sheet link first?", vi: "Lưu link sheet trước?" },
  shUnlinkedText: {
    en: "The changes are only in this browser. Save the link and you can open it again next week to add words.",
    vi: "Thay đổi mới chỉ nằm trong trình duyệt này. Lưu link sheet để tuần sau mở lại và thêm từ.",
  },
  shComeBack: {
    en: "Back to add words? Open the sheet link you saved (in Messenger, Telegram, Notes…) and the sheet appears here; saved a .csv instead? Press Open .xlsx/.csv file. Then press Make flashcards and import the new .apkg.",
    vi: "Quay lại để thêm từ? Mở link sheet bạn đã lưu (trong Messenger, Telegram, Ghi chú…) là sheet hiện ra ở đây; đã lưu file .csv thì bấm Mở file .xlsx/.csv. Thêm từ xong, bấm Tạo flashcard và import file .apkg mới.",
  },
  shAskAi: { en: "Ask AI to make a word set", vi: "Nhờ AI tạo bộ từ" },
  shAskAiHint: {
    en: "— ChatGPT, Gemini or Claude writes the .csv for you, then press Open .xlsx/.csv file.",
    vi: "— ChatGPT, Gemini hoặc Claude viết file .csv cho bạn, rồi bấm Mở file .xlsx/.csv.",
  },
  shIosNote: {
    en: "On iPhone and iPad, Safari deletes this draft if you don't open the page for 7 days. Press <b>Save sheet link</b> to keep the sheet. Tip: <b>Share → Add to Home Screen</b> puts this page one tap away.",
    vi: "Trên iPhone/iPad, Safari xoá bản nháp này nếu 7 ngày bạn không mở trang. Bấm <b>Lưu link sheet</b> để giữ sheet. Mẹo: <b>Share → Add to Home Screen</b> (Thêm vào MH chính) để mở lại trang này chỉ với một chạm.",
  },
  shAndroidCsvNote: {
    en: "To add words later, open this .csv with <b>Open .xlsx/.csv file</b> on this page — not from the Files app. There, Android may open it in AnkiDroid, whose CSV import turns every row, settings row included, into a junk note.",
    vi: "Lần sau muốn thêm từ, mở file .csv này bằng nút <b>Mở file .xlsx/.csv</b> ở trang này — đừng chạm vào nó trong app Files. Ở đó Android có thể mở bằng AnkiDroid, và AnkiDroid import CSV sẽ biến từng dòng, kể cả settings row, thành note rác.",
  },
  gotIt: { en: "Got it", vi: "Đã hiểu" },
  shUndo: { en: "Undo", vi: "Hoàn tác" },
  shRedo: { en: "Redo", vi: "Làm lại" },
  shNew: { en: "New sheet", vi: "Tạo sheet mới" },
  shNewTitle: { en: "Start a new sheet?", vi: "Tạo sheet mới?" },
  shNewText: {
    en: (n) => `The ${n} word${n === 1 ? "" : "s"} in this sheet will be cleared from this browser. To keep them, press Save .csv file (or Save sheet link) first.`,
    vi: (n) => `${n} từ trong sheet này sẽ bị xoá khỏi trình duyệt. Muốn giữ thì bấm Lưu file .csv (hoặc Lưu link sheet) trước.`,
  },
  shNewYes: { en: "Clear and start over", vi: "Xoá và làm lại" },
  shKeep: { en: "Keep my sheet", vi: "Giữ sheet hiện tại" },
  shViewLabel: { en: "Steps", vi: "Các bước" },
  shViewLook: { en: "Columns & card", vi: "Cột & card" },
  shRows: { en: "Add cards", vi: "Thêm thẻ" },
  shStepTemplate: { en: "Columns & card", vi: "Cột & card" },
  shStepTemplateSub: { en: "names, settings row", vi: "tên cột, settings row" },
  shStepCards: { en: "Add cards", vi: "Thêm thẻ" },
  shStepCardsSub: { en: "words", vi: "từ" },
  shEditTemplate: { en: "Edit columns & card", vi: "Sửa cột & card" },
  shFoldTemplate: { en: "Done", vi: "Xong" },
  shFileLine: {
    en: "The draft lives only in this browser. Save the .csv to keep it for good and carry on from any device, in Google Sheets or in Excel.",
    vi: "Bản nháp chỉ nằm trong trình duyệt này. Lưu file .csv để giữ mãi và làm tiếp trên máy khác, trong Google Sheets hay Excel.",
  },
  shSaveCsv: { en: "Save .csv", vi: "Lưu file .csv" },
  shOtherFormats: { en: "Need an .xlsx?", vi: "Cần file .xlsx?" },
  shUnfiledTitle: { en: "Save the sheet as a file first?", vi: "Lưu sheet thành file trước?" },
  shUnfiledText: {
    en: "The changes are only in this browser. Save the .csv and you can open it again to add words, on any device.",
    vi: "Thay đổi mới chỉ nằm trong trình duyệt này. Lưu file .csv để lần sau mở lại và thêm từ, trên máy nào cũng được.",
  },
  shUnfiledGo: { en: "Continue without saving", vi: "Tiếp tục, không lưu" },
  shGridHint: {
    en: "Drag to select cells · Ctrl+V pastes many rows from Excel or Google Sheets · right-click to insert, move or delete rows",
    vi: "Kéo để chọn ô · Ctrl+V dán nhiều dòng từ Excel hoặc Google Sheets · chuột phải để chèn, chuyển hoặc xoá dòng",
  },
  shAddWord: { en: "Add word", vi: "Thêm từ" },
  shEmptyWord: { en: "(empty)", vi: "(trống)" },
  shWordN: { en: (n, total) => `Word ${n} / ${total}`, vi: (n, total) => `Từ ${n} / ${total}` },
  shWords: { en: (n) => `${n} word${n === 1 ? "" : "s"}`, vi: (n) => `${n} từ` },
  shColumnsN: { en: (n) => `${n} column${n === 1 ? "" : "s"}`, vi: (n) => `${n} cột` },
  shColumns: { en: "Columns & settings row", vi: "Cột & settings row" },
  shColumnsLabel: { en: "Columns", vi: "Cột" },
  shDeckCellNote: {
    en: "The #config cell holds settings for the whole sheet: align, speed, reverse, theme.",
    vi: "Ô #config chứa settings cho cả sheet: align, speed, reverse, theme.",
  },
  shIdLabel: { en: "This word's ID", vi: "ID của dòng này" },
  shEnterHint: {
    en: "Enter moves to the next field. On the last one, Enter starts a new word.",
    vi: "Enter để sang ô tiếp theo. Ở ô cuối, Enter sang từ mới.",
  },

  // ---- Create sheet: paste a word list (wordpaste.js), suggest (suggestpanel.js)
  wlOpen: { en: "Paste a word list", vi: "Dán danh sách từ" },
  wlTitle: { en: "Paste a word list", vi: "Dán danh sách từ" },
  wlLead: {
    en: "One word per line, with its meaning if you like: <code>apple - quả táo</code>, <code>apple ; quả táo</code>, <code>apple: quả táo</code>, or two columns copied from Excel or Google Sheets.",
    vi: "Mỗi dòng một từ, có thể kèm nghĩa: <code>apple - quả táo</code>, <code>apple ; quả táo</code>, <code>apple: quả táo</code>, hoặc hai cột copy từ Excel hay Google Sheets.",
  },
  wlPlaceholder: { en: "apple - quả táo\nbook - quyển sách\njourney", vi: "apple - quả táo\nbook - quyển sách\njourney" },
  wlPasteBtn: { en: "Paste", vi: "Dán" },
  wlSeparator: { en: "Separator", vi: "Dấu tách" },
  wlSepAuto: { en: (found) => `Detect (${found})`, vi: (found) => `Tự nhận (${found})` },
  wlSepNone: { en: "none: one word per line", vi: "không tách: mỗi dòng một từ" },
  wlPart: { en: (n) => `Part ${n}`, vi: (n) => `Phần ${n}` },
  wlSkipPart: { en: "Leave out", vi: "Bỏ qua" },
  wlFillPinyin: {
    en: (col) => `Fill pinyin into “${col}” where it is empty (a suggestion: check it)`,
    vi: (col) => `Điền pinyin vào “${col}” cho ô còn trống (là gợi ý, nên xem lại)`,
  },
  wlFillRoman: {
    en: (col) => `Fill the romanisation into “${col}” where it is empty (a suggestion: check it)`,
    vi: (col) => `Điền romanization vào “${col}” cho ô còn trống (là gợi ý, nên xem lại)`,
  },
  wlNoJaReading: {
    en: "Japanese readings are not filled in automatically yet.",
    vi: "Chưa tự điền cách đọc cho tiếng Nhật.",
  },
  wlReaderFailed: {
    en: "Could not load the reading list. Check your connection.",
    vi: "Không tải được bộ phiên âm. Kiểm tra kết nối mạng.",
  },
  wlCount: { en: (n) => `${n} word${n === 1 ? "" : "s"} to add`, vi: (n) => `${n} từ sẽ được thêm` },
  wlDupes: { en: (n) => `${n} duplicate${n === 1 ? "" : "s"} left out`, vi: (n) => `${n} từ trùng, đã bỏ ra` },
  wlDupList: { en: "repeated in the list", vi: "lặp trong danh sách" },
  wlDupSheet: { en: "already in the sheet", vi: "đã có trong sheet" },
  wlMore: { en: (n) => `and ${n} more`, vi: (n) => `và ${n} dòng nữa` },
  wlAdd: { en: (n) => `Add ${n} word${n === 1 ? "" : "s"}`, vi: (n) => `Thêm ${n} từ` },
  wlSuggestN: { en: (n) => `Suggest for ${n} word${n === 1 ? "" : "s"}`, vi: (n) => `Gợi ý cho ${n} từ` },
  wlAdded: { en: (n) => `Added ${n} word${n === 1 ? "" : "s"}`, vi: (n) => `Đã thêm ${n} từ` },

  // ---- Sheet to Anki: paste text (textimport.js), other apps' files --------
  txOpen: { en: "Paste text", vi: "Dán văn bản" },
  txOpenHint: { en: "A word list, a note, Quizlet, CSV", vi: "Danh sách từ, ghi chú, Quizlet, CSV" },
  pickHint: { en: ".csv, .txt, .apkg, or drop it on the page", vi: ".csv, .txt, .apkg hoặc kéo thả vào trang" },
  txTitle: { en: "Paste text", vi: "Dán văn bản" },
  txLead: {
    en: "One card per line: <code>apple - quả táo</code>. To keep the set's name and settings with it, write <code>#config name=…</code> on line 1 and the column names on line 2; paste only the words and the page suggests both lines.",
    vi: "Mỗi dòng một card: <code>apple - quả táo</code>. Muốn giữ tên bộ và cài đặt, ghi <code>#config name=…</code> ở dòng 1 và tên cột ở dòng 2; chỉ dán từ thì trang gợi ý hai dòng đó cho bạn.",
  },
  txName: { en: "Flashcard set name", vi: "Tên bộ flashcard" },
  txNamePlaceholder: { en: "e.g. English vocabulary week 1", vi: "Ví dụ: Từ vựng tiếng Anh tuần 1" },
  txNameHint: {
    en: "The deck's name in Anki. Paste a longer list under the same name later and importing it updates the cards you already have.",
    vi: "Tên deck trong Anki. Lần sau dán danh sách dài hơn với cùng tên này, import sẽ cập nhật các card đã có.",
  },
  txNameEmpty: { en: "Give the set a name.", vi: "Hãy đặt tên cho bộ flashcard." },
  txPlaceholder: {
    en: "apple - quả táo\nbook - quyển sách\njourney - chuyến đi",
    vi: "apple - quả táo\nbook - quyển sách\njourney - chuyến đi",
  },
  txSides: { en: "Between front and back", vi: "Giữa mặt trước và mặt sau" },
  txRows: { en: "Between cards", vi: "Giữa các card" },
  txRowsNewline: { en: "new line", vi: "xuống dòng" },
  txEdit: { en: "Open in Create sheet", vi: "Mở trong Tạo Sheet" },
  txCount: { en: (n) => `${n} card${n === 1 ? "" : "s"}`, vi: (n) => `${n} card` },
  txOneSided: {
    en: (n) => `${n} with nothing on the back`,
    vi: (n) => `${n} card không có mặt sau`,
  },
  txWholeSheet: {
    en: (cols, rows) => `A whole sheet: ${cols} columns, ${rows} row${rows === 1 ? "" : "s"}, opened as it is`,
    vi: (cols, rows) => `Một sheet đầy đủ: ${cols} cột, ${rows} dòng, mở nguyên như vậy`,
  },
  txSettings: { en: "Settings", vi: "Cài đặt" },
  txSpeak: { en: "Read aloud", vi: "Đọc to" },
  txSpeakNone: { en: "Don't read", vi: "Không đọc" },
  txSpeakExample: { en: "read the example sentence too", vi: "đọc cả câu ví dụ" },
  txTheme: { en: "Theme", vi: "Theme" },
  txThemeNone: { en: "Default", vi: "Mặc định" },
  txRoles: { en: "Where each column goes", vi: "Vai trò từng cột" },
  txSideFront: { en: "Front", vi: "Mặt trước" },
  txSideBack: { en: "Back", vi: "Mặt sau" },
  txSideHide: { en: "Hidden", vi: "Ẩn" },
  txMore: { en: "Fine-tune in Create sheet", vi: "Chỉnh thêm trong Tạo Sheet" },
  txReused: { en: "Using this set's settings from last time", vi: "Dùng lại cài đặt lần trước của bộ này" },
  txGivenTitle: { en: "Settings in your text", vi: "Cài đặt trong văn bản" },
  txGivenDeck: { en: "Whole set", vi: "Cả bộ" },
  txGivenNone: { en: "(default)", vi: "(mặc định)" },
  txEditSettings: { en: "Edit", vi: "Sửa" },
  txOutTitle: { en: "Your text, with the settings added", vi: "Văn bản của bạn, đã thêm cài đặt" },
  txOutHint: {
    en: "Line 1 is the settings, line 2 the column names. Paste this into your note; paste it here again next time and the same set is updated.",
    vi: "Dòng đầu là cài đặt, dòng hai là tên cột. Dán đoạn này vào ghi chú; lần sau dán lại là cập nhật đúng bộ cũ.",
  },
  txCopy: { en: "Copy", vi: "Copy" },
  txCopied: { en: "Copied.", vi: "Đã copy." },
  txCopyFailed: { en: "Could not copy: select the text and copy it by hand.", vi: "Không copy được: chọn đoạn chữ và copy bằng tay." },
  txCardLoading: { en: "The card appears here once the page has finished loading.", vi: "Card hiện ở đây khi trang tải xong." },
  txTwice: {
    en: (col, key) => `“${col}”: ${key} is written both in #config and in brackets; the one in brackets is used.`,
    vi: (col, key) => `“${col}”: ${key} được ghi cả trong #config và trong ngoặc; dùng giá trị trong ngoặc.`,
  },
  txExtraCell: {
    en: (n) => `#config has a cell for column ${n}, but the cards have no column ${n}: that cell is left out.`,
    vi: (n) => `#config có ô cho cột ${n}, nhưng các card không có cột ${n}: ô đó bị bỏ qua.`,
  },
  hdSynth: {
    en: "The first row looked like a card, not column names, so the columns are called Front and Back.",
    vi: "Dòng đầu trông như một card chứ không phải tên cột, nên các cột được đặt tên Mặt trước, Mặt sau.",
  },
  hdKept: { en: "The first row is read as column names.", vi: "Dòng đầu được đọc là tên cột." },
  hdUseFirst: { en: "The first row is column names", vi: "Dòng đầu là tên cột" },
  hdUseCard: { en: "The first row is a card", vi: "Dòng đầu là một card" },
  apkgNewFormat: {
    en: "This deck was exported by a newer Anki, in a format this page cannot read. In Anki choose File → Export → Anki Deck Package and tick “Support older Anki versions”, then open the new file here.",
    vi: "Deck này xuất bằng Anki mới; trong Anki chọn File → Export → Anki Deck Package và tick “Support older Anki versions”, rồi mở file mới ở đây.",
  },
  apkgBroken: {
    en: "This file is named .apkg but is not an Anki package, or it is damaged.",
    vi: "File này tên .apkg nhưng không phải deck Anki, hoặc đã bị hỏng.",
  },
  apkgEmpty: { en: "This Anki package has no notes in it.", vi: "Deck Anki này không có note nào." },
  apkgMedia: {
    en: (n) => `${n} picture${n === 1 ? "" : "s"}/sound${n === 1 ? "" : "s"} could not come along: they are files inside the package, and a sheet can only link to the web.`,
    vi: (n) => `${n} ảnh/âm thanh không chuyển được: chúng là file nằm trong deck, còn sheet chỉ có thể link tới web.`,
  },
  sgOpen: { en: "Suggest", vi: "Gợi ý" },
  sgTitle: { en: "Suggestions", vi: "Gợi ý" },
  sgTitleWord: { en: (w) => `Suggestions: ${w}`, vi: (w) => `Gợi ý: ${w}` },
  sgProgress: { en: (n, total) => `looked up ${n}/${total}`, vi: (n, total) => `đã tra ${n}/${total}` },
  sgConsent: {
    en: "Suggestions send each word to <b>wikimedia.org</b> (Wiktionary, Commons) and <b>tatoeba.org</b> to look up its meanings, pronunciation, examples and pictures. Nothing else from your sheet is sent.",
    vi: "Gợi ý sẽ gửi từng từ tới <b>wikimedia.org</b> (Wiktionary, Commons) và <b>tatoeba.org</b> để tra nghĩa, phát âm, câu ví dụ và ảnh. Không gửi gì khác trong sheet của bạn.",
  },
  sgAgree: { en: "OK, look words up", vi: "Đồng ý, tra từ" },
  sgDecline: { en: "Not now", vi: "Để sau" },
  sgLooking: { en: (w) => `Looking up “${w}”…`, vi: (w) => `Đang tra “${w}”…` },
  sgNoWord: { en: "This word is empty: write it first.", vi: "Từ này đang trống: hãy viết từ trước." },
  sgNoLanguage: {
    en: "Suggestions are not available for this sheet's language yet.",
    vi: "Chưa có gợi ý cho ngôn ngữ của sheet này.",
  },
  sgCjkNote: {
    en: "For Chinese, Japanese and Korean there are only English meanings from Wiktionary, plus pinyin or romanisation. No Vietnamese meanings yet.",
    vi: "Với tiếng Trung, Nhật, Hàn: chỉ có nghĩa tiếng Anh từ Wiktionary, cùng pinyin hoặc romanization. Chưa có nghĩa tiếng Việt.",
  },
  sgMeaning: { en: "Meaning", vi: "Nghĩa" },
  sgPickSense: { en: "Pick a meaning above.", vi: "Chọn một nghĩa ở trên." },
  sgNoSenses: { en: "Wiktionary has no entry for this word.", vi: "Wiktionary chưa có mục cho từ này." },
  sgPinyin: { en: "Pinyin", vi: "Pinyin" },
  sgRoman: { en: "Romanisation", vi: "Romanization" },
  sgExample: { en: "Example", vi: "Ví dụ" },
  sgPickExample: { en: "Pick an example above.", vi: "Chọn một câu ví dụ ở trên." },
  sgCheckExample: {
    en: "Tatoeba's translations are written by volunteers: read one before you use it.",
    vi: "Bản dịch trên Tatoeba do người dùng đóng góp: đọc lại trước khi dùng.",
  },
  sgNoExamples: { en: "No example with a Vietnamese translation.", vi: "Không có câu ví dụ nào có bản dịch tiếng Việt." },
  sgAudio: { en: "Pronunciation audio", vi: "File phát âm" },
  sgImage: { en: "Picture", vi: "Ảnh" },
  sgPickImage: { en: "Pick a picture above.", vi: "Chọn một ảnh ở trên." },
  sgNoImages: { en: "No picture found on Wikimedia Commons.", vi: "Không tìm thấy ảnh trên Wikimedia Commons." },
  sgInto: { en: "Into column", vi: "Vào cột" },
  sgNow: { en: "Now:", vi: "Hiện tại:" },
  sgSuggestion: { en: "Suggestion", vi: "Gợi ý" },
  sgUse: { en: "Use", vi: "Dùng" },
  sgReplace: { en: "Replace", vi: "Thay" },
  sgSkip: { en: "Skip", vi: "Bỏ" },
  sgSkipped: { en: "Skipped.", vi: "Đã bỏ." },
  sgUsedIn: { en: (col) => `Written into “${col}”.`, vi: (col) => `Đã ghi vào “${col}”.` },
  sgSame: { en: (col) => `“${col}” already says this.`, vi: (col) => `Ô “${col}” đã có đúng giá trị này.` },
  sgUseAll: { en: "Use the ones chosen", vi: "Dùng các gợi ý đã chọn" },
  sgNext: { en: "Next word", vi: "Từ tiếp" },
  sgOffline: {
    en: "No connection. Suggestions come back when you are online again.",
    vi: "Không có mạng. Khi có mạng lại, bấm Thử lại.",
  },
  sgFailed: {
    en: (names) => `${names} did not answer. Try again in a moment.`,
    vi: (names) => `${names} không trả lời. Thử lại sau ít phút.`,
  },
  sgRetry: { en: "Try again", vi: "Thử lại" },
  sgSourceColumn: { en: "Source", vi: "Nguồn" },
  sgCreditNote: {
    en: "The sources of what you use are written into the Note or Source column (or a hidden “Source” column you can delete): Wiktionary CC BY-SA, Tatoeba CC BY 2.0 FR, each Commons file's own licence.",
    vi: "Nguồn của những gì bạn dùng được ghi vào cột Note hoặc Nguồn (hoặc một cột “Nguồn” ẩn, xoá được): Wiktionary CC BY-SA, Tatoeba CC BY 2.0 FR, ảnh Commons theo license của từng file.",
  },

  shDeleteWord: { en: "Delete word", vi: "Xoá từ" },
  shDeleted: {
    en: (id) => `Deleted ${id} — Undo brings it back`,
    vi: (id) => `Đã xoá ${id} — bấm Hoàn tác để lấy lại`,
  },
  shPrevWord: { en: "Previous word", vi: "Từ trước" },
  shNextWord: { en: "Next word", vi: "Từ sau" },
  shDone: { en: "Done", vi: "Xong" },
  shInsertAbove: { en: "Insert row above", vi: "Chèn dòng phía trên" },
  shInsertBelow: { en: "Insert row below", vi: "Chèn dòng phía dưới" },
  shMoveUp: { en: "Move up", vi: "Chuyển lên" },
  shMoveDown: { en: "Move down", vi: "Chuyển xuống" },
  shDeleteRows: {
    en: (n) => (n === 1 ? "Delete row" : `Delete ${n} rows`),
    vi: (n) => (n === 1 ? "Xoá dòng" : `Xoá ${n} dòng`),
  },
  shPastedSheet: {
    en: (n) => `Pasted a whole sheet — ${n} word${n === 1 ? "" : "s"}`,
    vi: (n) => `Đã dán cả sheet — ${n} từ`,
  },
  shPastedRows: {
    en: (n) => `Added ${n} word${n === 1 ? "" : "s"} from the clipboard`,
    vi: (n) => `Đã thêm ${n} từ từ clipboard`,
  },
  shPastedCells: {
    en: (n) => `Pasted ${n} row${n === 1 ? "" : "s"} of cells`,
    vi: (n) => `Đã dán ${n} dòng ô`,
  },
  shOpened: {
    en: (name, n) => `Opened ${name} — ${n} word${n === 1 ? "" : "s"}`,
    vi: (name, n) => `Đã mở ${name} — ${n} từ`,
  },
  shPickTab: { en: "Which sheet to open?", vi: "Mở sheet nào?" },
  shShare: { en: "Share link", vi: "Share link" },
  shToDeck: { en: "Make flashcards", vi: "Tạo flashcard" },
  shNeedWord: { en: "Add at least one word first", vi: "Thêm ít nhất một từ trước đã" },
  shHandoffFailed: {
    en: "This browser would not pass the sheet on. Download it and open the file in Sheet to Anki.",
    vi: "Trình duyệt không chuyển được sheet. Hãy Download rồi mở file trong Sheet to Anki.",
  },
  shDownloadTitle: { en: "Save the sheet as a file", vi: "Tải sheet về máy" },
  shXlsxHint: {
    en: "Opens in Excel, or upload it to Google Drive to make it a Google Sheet",
    vi: "Mở bằng Excel, hoặc upload lên Google Drive thành Google Sheets",
  },
  shCsvHint: { en: "Plain text, opens anywhere", vi: "File chữ đơn giản, mở được ở mọi nơi" },
  shReopenHint: {
    en: "Open the file here again any time to keep editing.",
    vi: "Mở lại file này ở đây bất cứ lúc nào để sửa tiếp.",
  },
  shPreparingXlsx: { en: "Preparing the .xlsx…", vi: "Đang tạo file .xlsx…" },
  shDownloaded: { en: (name) => `Downloaded ${name}`, vi: (name) => `Đã tải ${name}` },
  shShareLead: {
    en: "Whoever opens this link sees exactly your sheet, and can keep editing their own copy.",
    vi: "Ai mở link này sẽ thấy đúng sheet của bạn và sửa tiếp được trên bản của họ.",
  },
  shShareToDeck: { en: "Open straight as cards in Sheet to Anki", vi: "Mở thẳng thành cards trong Sheet to Anki" },
  shLinkSize: {
    en: (size, n) => `${size} for ${n} word${n === 1 ? "" : "s"}`,
    vi: (size, n) => `Link dài ${size} cho ${n} từ`,
  },
  shLinkLong: {
    en: "This link is long, and some chat apps cut long links short. If it doesn't open, send the downloaded file instead.",
    vi: "Link này khá dài, và vài app chat cắt bớt link dài. Nếu link không mở được, hãy gửi file đã Download thay vào đó.",
  },
  shCopyLink: { en: "Copy link", vi: "Copy link" },
  shCopied: { en: "Copied", vi: "Đã copy" },
  shShareVia: { en: "Send via…", vi: "Gửi qua…" },
  shSharePrivacy: {
    en: "The sheet travels inside the link itself. Nothing is sent to any server.",
    vi: "Sheet nằm ngay trong link. Không có gì được gửi lên máy chủ nào.",
  },
  shSharedTitle: { en: "Open the shared sheet?", vi: "Mở sheet được chia sẻ?" },
  shSharedText: {
    en: (shared, mine) => `This link holds “${shared}”. Opening it replaces your draft “${mine}” in this browser.`,
    vi: (shared, mine) => `Link này chứa sheet “${shared}”. Mở nó sẽ thay bản nháp “${mine}” trong trình duyệt này.`,
  },
  shSharedYes: { en: "Open the shared sheet", vi: "Mở sheet trong link" },
  crEditSheet: { en: "Edit sheet", vi: "Sửa sheet" },
  shareBroken: {
    en: "This share link is broken or was cut short. Ask for the file instead.",
    vi: "Share link này bị hỏng hoặc bị cắt ngắn. Hãy xin file thay vào đó.",
  },
  shareTooNew: {
    en: "This share link was made by a newer SheetCards. Reload the page and try again.",
    vi: "Share link này được tạo bởi bản SheetCards mới hơn. Tải lại trang rồi thử lại.",
  },

  // --- the settings row's chips and panels ----------------------------------
  edName: { en: "Column name", vi: "Tên cột" },
  edCell: { en: "Settings row cell", vi: "Ô trong settings row" },
  edSheet: { en: "The sheet you are writing", vi: "Sheet bạn đang soạn" },
  edDeckCell: { en: "The #config cell — settings for the whole sheet", vi: "Ô #config — settings cho cả sheet" },
  edAddColumn: { en: "Add a column", vi: "Thêm cột" },
  edRemoveColumn: { en: "Remove this column", vi: "Bỏ cột này" },
  edTemplate: { en: "Card template", vi: "Card template" },
  edForDeck: { en: "for the whole sheet", vi: "cho cả sheet" },
  edAdvanced: { en: "Advanced", vi: "Nâng cao" },
  edForColumn: { en: (name) => `for ${name}`, vi: (name) => `cho ${name}` },
  edNoMarker: {
    en: "Row 2 no longer starts with #config, so it is an ordinary note",
    vi: "Dòng 2 không còn bắt đầu bằng #config, nên nó là một note bình thường",
  },
  edAdd: { en: "Add a directive", vi: "Thêm directive" },
  edOther: { en: "other", vi: "khác" },
  edSample: { en: "try this value", vi: "thử giá trị này" },

  // --- what each directive is ---------------------------------------------
  // One sentence each, and for the ones that only work with the cell written a
  // certain way, the sentence says which way — that is the whole difficulty.
  helpSide: {
    en: "Which side of the card this column goes on. Without it the first column is the front and the rest are the back.",
    vi: "Cột này nằm ở mặt nào của card. Không ghi thì cột đầu tiên là mặt trước, các cột còn lại ở mặt sau.",
  },
  helpSize: {
    en: "Text size in pixels, 6–200. On a picture or a writing box it is the width instead, and the range is 1–2000.",
    vi: "Cỡ chữ tính bằng pixel, 6–200. Trên cột ảnh hoặc ô draw thì nó là chiều rộng, khoảng 1–2000.",
  },
  helpColor: {
    en: "Text colour. muted and accent follow the card's light/dark theme; anything else is a CSS colour name or a #hex.",
    vi: "Màu chữ. muted và accent đổi theo nền sáng/tối của card; ngoài ra là tên màu CSS hoặc mã #hex.",
  },
  helpAlign: {
    en: "Text alignment for this column: left, center or right.",
    vi: "Căn lề chữ của cột này: left, center hoặc right.",
  },
  helpTts: {
    en: "Anki reads this column aloud. The code must be the full form: zh on its own matches no installed voice and plays silence.",
    vi: "Anki đọc to cột này. Mã phải đủ dạng: chỉ ghi zh thì không khớp giọng nào và phát ra im lặng.",
  },
  helpVoices: {
    en: "Preferred voice names, comma separated. A preference only — Anki falls back to any voice of that language.",
    vi: "Tên giọng ưu tiên, cách nhau bằng dấu phẩy. Chỉ là ưu tiên — Anki vẫn dùng giọng khác cùng ngôn ngữ nếu không có.",
  },
  helpSpeed: {
    en: "Speaking rate for this column's tts, 0.5–2.0.",
    vi: "Tốc độ đọc tts của cột này, 0.5–2.0.",
  },
  helpLabel: {
    en: "A small caption printed above the field. Bare label uses the column's name; label=… writes your own.",
    vi: "Một dòng nhãn nhỏ in phía trên field. Ghi trần label thì nhãn là tên cột; label=… để tự đặt.",
  },
  helpType: {
    en: "Anki draws a box on the question and compares what you type against this column. type=nc ignores accents. One column per sheet.",
    vi: "Anki hiện ô nhập ở mặt câu hỏi rồi so cái bạn gõ với cột này. type=nc bỏ qua dấu. Mỗi sheet một cột.",
  },
  helpSubdeck: {
    en: "This column becomes a level of the deck path. It is never drawn on the card — filing a note and printing on it are different jobs.",
    vi: "Cột này thành một tầng trong đường dẫn deck. Nó không bao giờ hiện trên card — xếp note vào deck và in lên card là hai việc khác nhau.",
  },
  helpMath: {
    en: "The cell is a formula, drawn by the MathJax that Anki already ships — write TeX without the delimiters. Bare math is inline; math=block is the centred display form.",
    vi: "Ô là một công thức, do MathJax có sẵn trong Anki vẽ — bạn viết TeX, không cần dấu bao. Ghi math là công thức nằm trong dòng; math=block là công thức căn giữa một dòng riêng.",
  },
  helpCode: {
    en: "The cell is source code: kept exactly as typed, in a monospace block, coloured by language. code=python names the language; bare code just keeps the formatting.",
    vi: "Ô là code: giữ nguyên như bạn gõ, khối chữ đều nét, tô màu theo ngôn ngữ. code=python là chỉ định ngôn ngữ; ghi trần code thì chỉ giữ định dạng.",
  },
  helpFont: {
    en: "The typeface for this column. sc/tc/jp/kr load a Noto CJK font — worth it because 直 and 骨 are drawn differently in Chinese and Japanese. A column with tts=zh_CN, zh_TW, ja_JP or ko_KR gets its font without asking. Any installed family name also works.",
    vi: "Font cho cột này. sc/tc/jp/kr nạp font Noto CJK — đáng dùng vì 直 hay 骨 có tự dạng khác nhau giữa tiếng Trung và tiếng Nhật. Cột có tts=zh_CN, zh_TW, ja_JP hay ko_KR tự có font, không cần ghi. Gõ tên font đã cài trong máy cũng được.",
  },
  helpBold: { en: "Bold text.", vi: "Chữ đậm." },
  helpItalic: { en: "Italic text.", vi: "Chữ nghiêng." },
  helpHint: {
    en: "Hides the value behind a link you click to reveal. On a picture or a player it hides the element instead.",
    vi: "Giấu giá trị sau một link, bấm mới hiện. Trên cột ảnh hoặc player thì nó giấu chính phần tử đó.",
  },
  helpFurigana: {
    en: "Prints the reading above the text, for Japanese. It only works when the cell is written kanji[reading] — the brackets are the whole trick.",
    vi: "In cách đọc phía trên chữ, dùng cho tiếng Nhật. Chỉ chạy khi ô được viết dạng kanji[cách đọc] — cặp ngoặc vuông chính là mấu chốt.",
  },
  helpCloze: {
    en: "This column holds the {{c1::…}} deletions. Declaring it makes the whole sheet cloze and this column becomes the prompt — a cell with no deletion in it renders as nothing at all.",
    vi: "Cột này chứa các chỗ cloze {{c1::…}}. Khai báo nó thì cả sheet thành cloze và cột này thành câu hỏi — ô nào không có {{c1::…}} sẽ hiện ra trống trơn.",
  },
  helpDraw: {
    en: "Turns the column into a writing box for a Chinese character: on the question you write it stroke by stroke, on the answer it animates the strokes. Needs the network.",
    vi: "Biến cột thành ô viết chữ Hán: ở mặt câu hỏi bạn viết từng nét, ở mặt đáp án nó chạy lại thứ tự nét. Cần mạng.",
  },
  helpImage: {
    en: "The cell holds a bare image URL and the card shows the picture instead of the address. size caps its width.",
    vi: "Ô chứa link ảnh trần, card hiện ảnh thay vì hiện địa chỉ. size giới hạn chiều rộng.",
  },
  helpAudio: {
    en: "The cell holds a bare audio URL and the card shows a player. The file is fetched each time, so the card needs the network.",
    vi: "Ô chứa link audio trần, card hiện trình phát. File tải lại mỗi lần nên card cần mạng.",
  },
  helpVideo: {
    en: "The cell holds a video link — YouTube, Drive, or a direct file. The address is rewritten into that site's own player when the note is made.",
    vi: "Ô chứa link video — YouTube, Drive, hoặc file trực tiếp. Địa chỉ được đổi sang trình phát của chính trang đó khi tạo note.",
  },
  helpReverse: {
    en: "Adds a second card that asks the back and answers with the front. One row, two cards, scheduled separately.",
    vi: "Thêm card thứ hai hỏi mặt sau và trả lời bằng mặt trước. Một dòng, hai card, review riêng nhau.",
  },
  helpTheme: {
    en: "A colour palette for the whole card, in both light and dark mode.",
    vi: "Bảng màu cho cả card, dùng được ở cả nền sáng và nền tối.",
  },
  edRemoveKey: { en: "Remove this directive", vi: "Bỏ directive này" },
  edCopiedCells: { en: "Copied — paste it into your sheet", vi: "Đã copy — dán vào sheet của bạn" },
  edCopyFailed: { en: "The browser refused to copy", vi: "Trình duyệt không cho copy" },
  edOk: { en: "Every setting was understood", vi: "Mọi setting đều hợp lệ" },
  edRefused: {
    en: (n) => `${n} setting${n === 1 ? "" : "s"} refused`,
    vi: (n) => `${n} setting bị từ chối`,
  },
  edSides: {
    en: (front, back) =>
      `${front} field on the front, ${back} on the back — as the card will be in Anki.`,
    vi: (front, back) =>
      `${front} field ở mặt trước, ${back} ở mặt sau — đúng như card trong Anki.`,
  },
  edSelectAll: { en: "Select every cell", vi: "Chọn tất cả các ô" },
  edInsertLeft: { en: "Insert column left", vi: "Chèn cột bên trái" },
  edInsertRight: { en: "Insert column right", vi: "Chèn cột bên phải" },
  edClearCells: { en: "Clear cells", vi: "Xoá nội dung ô" },
  edUndone: { en: "Undone — Ctrl+Y puts it back", vi: "Đã hoàn tác — Ctrl+Y để làm lại" },
  edRedone: { en: "Redone", vi: "Đã làm lại" },
  edTags: { en: "Tags", vi: "Tags" },
  // The real root is `sc_{file}::{sheet}` — the file and the sheet this row came
  // from, which a sheet still being written does not have yet. Named for what it
  // is instead of invented, so nothing on screen claims to be a deck name.
  edDeckRoot: { en: "your sheet's deck", vi: "deck của sheet bạn" },
  toLight: { en: "Switch to light", vi: "Chuyển sang nền sáng" },
  urlPlaceholder: {
    en: "Paste a Google Sheets link, or a link to an .xlsx",
    vi: "Dán link Google Sheets hoặc link file .xlsx",
  },
  urlLabel: { en: "Google Sheets link", vi: "Link Google Sheets" },
  go: { en: "Make flashcards", vi: "Tạo flashcard" },
  pick: { en: "Open .xlsx/.csv file", vi: "Mở file .xlsx/.csv" },
  tabLabel: { en: "Sheet", vi: "Sheet" },
  reloadLabel: {
    en: "Fetch this sheet again",
    vi: "Tải lại sheet này",
  },
  reloading: { en: "Fetching again…", vi: "Đang tải lại…" },
  fileGone: {
    en: "This file changed on disk. Drop it on the page again.",
    vi: "File trên máy đã đổi. Kéo thả lại vào trang.",
  },

  // --- Create sheet's deck heading -----------------------------------------
  panelDeck: { en: "Deck", vi: "Deck" },

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
    vi: (level) => `Tầng deck ${level} — cột dành riêng, không bao giờ lên card`,
  },
  roleSubdeckOnly: {
    en: (level) => `Deck level ${level} — files the note, never drawn on the card`,
    vi: (level) => `Tầng deck ${level} — xếp note vào deck, không hiện trên card`,
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
  sideHidden: { en: "note only, hidden on the card", vi: "chỉ trong note, ẩn trên card" },
  nothingSet: {
    en: "The settings row says nothing about this column.",
    vi: "Settings row không nói gì về cột này.",
  },
  // The sheet drawn as itself. Row numbers and column letters are the
  // spreadsheet's own, so a row named here is the row you would scroll to there.
  gridHead: { en: "The sheet", vi: "Sheet gốc" },
  gridCut: {
    en: (shown, total) => `Showing the first ${shown} of ${total} rows`,
    vi: (shown, total) => `Đang hiện ${shown} dòng đầu trong ${total} dòng`,
  },
  valueInRow: { en: (line) => `Row ${line}`, vi: (line) => `Dòng ${line}` },
  cellEmpty: { en: "empty", vi: "trống" },
  dropHere: { en: "Drop the file here", vi: "Thả file vào đây" },
  dropTypes: {
    en: ".xlsx, .xlsm, .csv or .tsv — nothing leaves this browser",
    vi: ".xlsx, .xlsm, .csv hoặc .tsv — file không rời khỏi trình duyệt",
  },

  // --- status -------------------------------------------------------------
  // The previewer is the add-on itself running in Python, which is a download of
  // its own. Said in the words of somebody waiting for a page, with the two facts
  // that make the wait bearable: how big, and that it happens once.
  booting: {
    en: "Loading the sheet reader (~6 MB, first time only)…",
    vi: "Đang tải bộ đọc sheet (~6 MB, chỉ lần đầu)…",
  },
  loadingCode: { en: "Almost ready…", vi: "Sắp xong…" },
  slowBoot: {
    en: "The network seems slow — still loading, nothing is wrong.",
    vi: "Mạng có vẻ chậm — vẫn đang tải, bạn cứ chờ nhé.",
  },
  queued: {
    en: "Got your link — the cards appear as soon as this finishes.",
    vi: "Đã nhận link — card sẽ hiện ngay khi tải xong.",
  },
  // The first load, counted (pyodide.js): what has come in, of how much, and on
  // mobile data a line about the data it costs.
  queuedFile: {
    en: "Got your file — the cards appear as soon as this finishes.",
    vi: "Đã nhận file — card sẽ hiện ngay khi tải xong.",
  },
  publishedLink: {
    en: "This is a Publish to web link, and this sheet could not be read through it. Use the Share link instead: Share → General access → Anyone with the link, then Copy link.",
    vi: "Đây là link Publish to web, và không đọc được sheet qua link này. Hãy dùng link Share thay vì Publish: Share → General access → Anyone with the link, rồi Copy link.",
  },
  queuedSheet: {
    en: "Got the sheet — the cards appear as soon as this finishes.",
    vi: "Đã nhận sheet — card sẽ hiện ngay khi tải xong.",
  },
  bootingMB: {
    en: (done, total) => `Loading the sheet reader: ${done} of ${total} MB (first time only)…`,
    vi: (done, total) => `Đang tải bộ đọc sheet: ${done} / ${total} MB (chỉ lần đầu)…`,
  },
  bootData: {
    en: (total) => `You seem to be on mobile data: the first visit downloads about ${total} MB, once.`,
    vi: (total) => `Bạn có vẻ đang dùng dữ liệu di động: lần đầu sẽ tải khoảng ${total} MB, chỉ một lần.`,
  },
  downloading: { en: "Downloading the sheet…", vi: "Đang tải sheet về…" },
  reading: { en: "Reading the file…", vi: "Đang đọc file…" },
  analysing: { en: "Building the cards…", vi: "Đang dựng card…" },
  readRows: {
    en: (n, s) => `${n} rows · ${s} will become notes`,
    vi: (n, s) => `${n} dòng · ${s} sẽ thành note`,
  },
  bootFailed: {
    en: (m) => `Sheet to Anki could not load (${m}). Reload the page to try again.`,
    vi: (m) => `Không tải được Sheet to Anki (${m}). Tải lại trang để thử lại.`,
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
  // Read out before the message by a screen reader, the way GOV.UK does it: the
  // red is not something everybody can see.
  errorPrefix: { en: "Error:", vi: "Lỗi:" },
  // What went wrong, said as what to do next. Only a Google link is told about
  // sharing, because only Google has a Share button to press.
  notShared: {
    en:
      "This sheet is not shared yet. In Google Sheets: Share → “Anyone with the " +
      "link” → Viewer, then try again.",
    vi:
      "Sheet chưa được chia sẻ. Trong Google Sheets: Share → “Anyone with the " +
      "link” → Viewer, rồi thử lại.",
  },
  notFound: {
    en: (sheet) =>
      sheet
        ? "Sheet not found. Check the link — copy it again from the address bar. " +
          "If the link is right, the sheet may not be shared yet."
        : "There is no file at that address. Check the link.",
    vi: (sheet) =>
      sheet
        ? "Không tìm thấy sheet. Kiểm tra lại link — copy lại từ thanh địa chỉ. " +
          "Nếu link đúng, có thể sheet chưa được chia sẻ."
        : "Không có file nào ở địa chỉ này. Kiểm tra lại link.",
  },
  offline: {
    en: "No internet connection. Check your connection and try again.",
    vi: "Không có kết nối mạng. Kiểm tra mạng rồi thử lại.",
  },
  fileUnreachable: {
    en: "Could not download a file from that link. Check the link and your connection.",
    vi: "Không tải được file từ link này. Kiểm tra lại link và kết nối mạng.",
  },
  fileRefused: {
    en: "That site refused the download. The link has to open without signing in.",
    vi: "Trang web đó không cho tải file. Link phải mở được mà không cần đăng nhập.",
  },
  notAFile: {
    en: "That link opens a web page, not an .xlsx file. Use a link that downloads the file itself.",
    vi: "Link này mở ra một trang web, không phải file .xlsx. Hãy dùng link tải thẳng file.",
  },
  httpError: {
    en: (code) => `The server answered with error ${code}. Try again in a moment.`,
    vi: (code) => `Máy chủ báo lỗi ${code}. Thử lại sau ít phút.`,
  },

  // --- demo ---------------------------------------------------------------
  // A sheet with no ID column is keyed by its first column (column_model.derived_ids).
  idFromColumn: {
    en: (col) => `No ID column → using column <strong>${col}</strong> as the ID. Fixing the spelling of a word there makes it a new card.`,
    vi: (col) => `Không có cột ID → dùng cột <strong>${col}</strong> làm ID. Sửa chính tả chính từ đó sẽ thành card mới.`,
  },
  demoNote: {
    en: "This is the example workbook. Pick another sheet above, or change to your own link.",
    vi: "Đang xem file ví dụ. Chọn sheet khác ở ô phía trên, hoặc đổi sang link của bạn.",
  },
  // The same note, in the one line a phone has room for above the fold.

  // --- the numbers --------------------------------------------------------
  statRows: { en: "rows in the sheet", vi: "dòng trong sheet" },
  statWithId: { en: "with an ID", vi: "có ID" },
  statSync: { en: "will become notes", vi: "sẽ thành note" },
  statNotes: { en: "notes in Anki", vi: "note trong Anki" },
  statCloze: { en: "cloze rows", vi: "dòng cloze" },
  statDecks: { en: "decks", vi: "deck" },

  // --- panes --------------------------------------------------------------
  decks: { en: "Decks", vi: "Deck" },
  allDecks: { en: "All decks", vi: "Tất cả deck" },
  noSyncRows: {
    en: "No row will become a note.",
    vi: "Không dòng nào sẽ thành note.",
  },
  rows: { en: "Rows", vi: "Dòng" },
  noRowsHere: { en: "No rows in this deck.", vi: "Deck này không có dòng nào." },
  noRowsAtAll: { en: "No rows to show.", vi: "Không có dòng nào để hiện." },
  // The extension sits beside this as a tag of its own, next to Anki's icon.
  // The button's own words stay English in both languages: it names the file
  // Anki asks for, and "Download" is what the learner's phone will say next.
  downloadApkg: { en: "Download .apkg", vi: "Download .apkg" },
  // The caveats used to be a four-sentence paragraph under the button, which is a
  // lot of reading to sit permanently under a control most people press once.
  // The docs page on sheets and files carries the long version.
  apkgTitle: {
    en:
      "Import straight into AnkiDroid or AnkiMobile. Importing again updates these " +
      "notes rather than duplicating them, but it cannot delete.",
    vi:
      "Import thẳng vào AnkiDroid hoặc AnkiMobile. Import lại sẽ cập nhật chứ không " +
      "nhân đôi, nhưng không xoá được.",
  },
  packing: { en: "Building the package…", vi: "Đang đóng gói…" },
  packed: {
    en: (kb) => `Package ready — ${kb} KB`,
    vi: (kb) => `Đã đóng gói xong — ${kb} KB`,
  },
  packFailed: {
    en: (m) => `Could not build the package: ${m}`,
    vi: (m) => `Không đóng gói được: ${m}`,
  },

  // --- tabs ---------------------------------------------------------------
  // Four tabs on one strip: "mặt" is said by the strip itself, and the two words
  // it saves are the difference between one row of controls and two.
  tabFront: { en: "front", vi: "trước" },
  tabBoth: { en: "both", vi: "cả hai" },
  tabBack: { en: "back", vi: "sau" },
  tabTemplate: { en: "card template", vi: "card template" },
  prevRow: { en: "Previous card", vi: "Card trước" },
  clozeCard: { en: "Cloze card", vi: "Card cloze" },
  clozeCardN: { en: (n) => `card c${n}`, vi: (n) => `card c${n}` },
  cardFrameTitle: { en: "Card preview", vi: "Preview card" },
  nextRow: { en: "Next card", vi: "Card sau" },

  // --- card ---------------------------------------------------------------
  rowSkipped: {
    en: "This row is not ticked in the SYNC column, so it does not become a note.",
    vi: "Dòng này chưa tick ở cột SYNC nên không thành note.",
  },
  rowInvalid: {
    en: "This row has no ID, so nothing can key it and it does not become a note.",
    vi: "Dòng này không có ID nên không thành note.",
  },
  clozeStranded: {
    en: (cols) =>
      `The deletion in <code>${cols}</code> is not on the front, so Anki blanks ` +
      `the prompt and prints the raw <code>{{c1::…}}</code> below. The picture ` +
      `above shows that faithfully.`,
    vi: (cols) =>
      `Chỗ cloze nằm ở <code>${cols}</code> chứ không ở mặt trước, nên Anki để ` +
      `trống câu hỏi và in nguyên <code>{{c1::…}}</code> bên dưới. Ảnh trên tái ` +
      `hiện đúng như vậy.`,
  },
  missingFields: {
    en: (f) => `The card template references a field the row has no column for: <code>${f}</code>`,
    vi: (f) => `Card template gọi field mà dòng này không có cột: <code>${f}</code>`,
  },
  unknownFilters: {
    en: (f) => `Filter not reproduced here: <code>${f}</code>`,
    vi: (f) => `Filter trang này chưa mô phỏng: <code>${f}</code>`,
  },
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
      `${count} dòng (${rows}) đặt chỗ cloze ở <code>${cols}</code>, nhưng câu hỏi ` +
      `của card là <code>${prompt}</code>. Anki render một field bọc cloze mà không ` +
      `có chỗ cloze thành rỗng, nên mấy card này ra mặt trước trắng và in nguyên ` +
      `<code>{{c1::…}}</code> ở mặt sau. Thêm <code>cloze</code> vào cột đó trong ` +
      `settings row.`,
  },
  warnDuplicateTitle: { en: "Duplicate IDs", vi: "ID trùng" },
  warnDuplicateBody: {
    en: (ids) =>
      `${ids}. Notes are keyed by ID, so only the first row of each becomes a card; ` +
      `the rows after it are left out. Give each row its own ID.`,
    vi: (ids) =>
      `${ids}. Note được khoá theo ID, nên chỉ dòng đầu tiên của mỗi ID thành card; ` +
      `các dòng sau bị bỏ qua. Hãy cho mỗi dòng một ID riêng.`,
  },
  // A changed note type, before and after the download. Verified against Anki
  // 25.07: with the default import options a changed field list or card list
  // makes every note "conflicting" and none is updated. Merging re-stamps the
  // notes already there with the import time, so "If newer" would then skip
  // them too — hence Update notes: Always, once.
  schemaTitle: {
    en: "You changed the columns → turn on Merge note types when you import",
    vi: "Bạn đã đổi cột → khi import hãy bật Merge note types",
  },
  schemaBody: {
    en: (fields) =>
      `Since the last download of this deck its fields or cards changed (now: ${fields}). ` +
      "With Anki's default options no note would be updated. Once, for this import:",
    vi: (fields) =>
      `Từ lần tải trước, field hoặc card của deck này đã đổi (giờ là: ${fields}). ` +
      "Với tuỳ chọn mặc định, Anki sẽ không cập nhật note nào. Chỉ cần một lần, ở lần import này:",
  },
  // Only the card templates changed (reverse turned on), not the columns.
  templateTitle: {
    en: "You changed the card templates → turn on Merge note types when you import",
    vi: "Bạn đã đổi card template → khi import hãy bật Merge note types",
  },
  templateBody: {
    en: "Since the last download of this deck its cards changed (for example reverse was turned on), so to Anki it is a new note type. With Anki's default options no note would be updated. Once, for this import:",
    vi: "Từ lần tải trước, card của deck này đã đổi (ví dụ bật reverse), nên với Anki đây là note type mới. Với tuỳ chọn mặc định, Anki sẽ không cập nhật note nào. Chỉ cần một lần, ở lần import này:",
  },
  // Nothing known about the last download (a Google Sheet never downloaded here).
  schemaMaybe: {
    en: "If you changed the columns since the last import: turn on <b>Merge note types</b> and set <b>Update notes</b> to <b>Always</b>.",
    vi: "Nếu bạn đã đổi cột từ lần import trước: bật <b>Merge note types</b> và đặt <b>Update notes</b> thành <b>Always</b>.",
  },
  // A named set imported when its deck was still called sc_<name>.
  renameTitle: {
    en: "First rename the old deck in Anki",
    vi: "Trước tiên đổi tên deck cũ trong Anki",
  },
  renameBody: {
    en: (from, to) =>
      `This set used to arrive in Anki as <b>${from}</b>; it is now called exactly what you named it, <b>${to}</b>. ` +
      `Before importing, rename <b>${from}</b> to <b>${to}</b> in Anki (the gear beside the deck → Rename). ` +
      "Anki keeps a note's existing cards in their deck, so otherwise the old cards stay in the old deck and the new ones go to the new one.",
    vi: (from, to) =>
      `Bộ này trước đây vào Anki với tên <b>${from}</b>; giờ deck mang đúng tên bạn đặt, <b>${to}</b>. ` +
      `Trước khi import, đổi tên deck <b>${from}</b> thành <b>${to}</b> trong Anki (bánh răng cạnh deck → Rename). ` +
      "Anki giữ card cũ ở deck cũ, nên nếu không đổi tên, card cũ ở lại deck cũ còn card mới vào deck mới.",
  },
  mergeDesktop: {
    en: "<b>Anki on a computer</b>: File → Import…, pick the file, then tick <b>Merge note types</b> and set <b>Update notes</b> to <b>Always</b> before pressing Import.",
    vi: "<b>Anki trên máy tính</b>: File → Import…, chọn file, rồi tick <b>Merge note types</b> và đặt <b>Update notes</b> thành <b>Always</b> trước khi bấm Import.",
  },
  mergeAndroid: {
    en: "<b>AnkiDroid</b>: open the file with AnkiDroid; its import screen has the same options — turn on <b>Merge note types</b>, set <b>Update notes</b> to <b>Always</b>.",
    vi: "<b>AnkiDroid</b>: mở file bằng AnkiDroid; màn hình import có cùng các tuỳ chọn — bật <b>Merge note types</b>, đặt <b>Update notes</b> thành <b>Always</b>.",
  },
  mergeIos: {
    en: "<b>AnkiMobile</b>: we could not confirm these options on its Import screen. If you see <b>Merge note types</b> and <b>Update notes</b>, set them as above; if not, import this file in Anki on a computer and sync.",
    vi: "<b>AnkiMobile</b>: chúng tôi chưa xác nhận được màn hình Import của app có các tuỳ chọn này. Nếu thấy <b>Merge note types</b> và <b>Update notes</b>, chỉnh như trên; nếu không, hãy import file này bằng Anki trên máy tính rồi sync.",
  },
  mergeAfter: {
    en: "After that, normal imports update again. Anki will ask for a one-way sync once.",
    vi: "Sau lần đó, import bình thường sẽ lại cập nhật. Anki sẽ hỏi sync một chiều một lần.",
  },
  // reverse taken out of the settings row: Anki keeps the cards it already made.
  emptyCardsTitle: { en: "Reverse cards turned off", vi: "Đã tắt card ngược" },
  emptyCards: {
    en: "The sheet no longer makes reverse cards (<b>reverse</b>), and this file makes none — but Anki keeps the ones it already made. After importing, remove them with <b>Tools → Empty Cards</b> in Anki on a computer.",
    vi: "Sheet không còn tạo card ngược (<b>reverse</b>) và file này không tạo thêm — nhưng Anki vẫn giữ các card ngược đã có. Sau khi import, xoá chúng bằng <b>Tools → Empty Cards</b> trong Anki trên máy tính.",
  },
  clozeTitle: {
    en: "You switched this deck to or from cloze",
    vi: "Bạn đã chuyển deck này sang hoặc ra khỏi cloze",
  },
  clozeBody: {
    en: (type) =>
      "Anki cannot merge a cloze note type with a regular one, so the notes you already have " +
      "will not be updated (and Merge note types would refuse — leave it off). New words still " +
      "arrive. To move the old notes over and keep their progress: import, then in Anki on a " +
      `computer open Browse, select them, Notes → Change Note Type… to <b>${type}</b>, and import again with <b>Update notes</b> set to <b>Always</b>.`,
    vi: (type) =>
      "Anki không gộp được note type cloze với note type thường, nên các note đã có sẽ không " +
      "được cập nhật (và Merge note types sẽ báo lỗi — để tắt). Từ mới vẫn vào. Muốn chuyển note " +
      "cũ sang và giữ tiến độ: import, rồi trong Anki trên máy tính mở Browse, chọn các note đó, " +
      `Notes → Change Note Type… sang <b>${type}</b>, rồi import lại với <b>Update notes</b> là <b>Always</b>.`,
  },
  // One sentence, and the reasoning behind a disclosure for whoever wonders.
  warningsFrom: {
    en:
      "Lines labelled “Settings row” are what the add-on reports for the same sheet." +
      "<details><summary>Why?</summary>Nothing is silently ignored: a value the " +
      "add-on does not understand is refused, never guessed at, and the column " +
      "keeps its default until the sheet is fixed.</details>",
    vi:
      "Các dòng gắn nhãn “Settings row” là điều add-on cũng sẽ báo cho sheet này." +
      "<details><summary>Tại sao?</summary>Không có gì bị bỏ qua âm thầm: giá trị " +
      "add-on không hiểu thì bị từ chối chứ không bị đoán, và cột giữ mặc định cho " +
      "tới khi sheet được sửa.</details>",
  },

  templateFrom: {
    en: (name) =>
      `The exact text the add-on writes into Anki for <code>${name}</code>, produced ` +
      `here by the same <code>card_layout.py</code> that runs in the add-on.`,
    vi: (name) =>
      `Đúng đoạn text add-on ghi vào Anki cho <code>${name}</code>, sinh ra ở đây ` +
      `bằng chính <code>card_layout.py</code> đang chạy trong add-on.`,
  },
  frontTemplate: { en: "Front template", vi: "Front template" },
  backTemplate: { en: "Back template", vi: "Back template" },

  rowTitle: {
    en: (line, state) => `Row ${line} — ${state}`,
    vi: (line, state) => `Dòng ${line} — ${state}`,
  },
  legendSynced: { en: "becomes a note", vi: "sẽ thành note" },
  legendSkipped: { en: "not ticked in SYNC", vi: "chưa tick SYNC" },
  legendInvalid: { en: "no ID", vi: "không có ID" },
  legendGhost: {
    en: "Blank rows are ignored entirely.",
    vi: "Dòng trống bị bỏ qua hoàn toàn.",
  },

  // --- Sheet to Anki: the three steps ----------------------------------------
  railLabel: { en: "Steps", vi: "Các bước" },
  crStep1: { en: "Add your sheet", vi: "Dán link sheet" },
  crStep2: { en: "Check the cards", vi: "Kiểm tra cards" },
  crStep3: { en: "Download .apkg", vi: "Download .apkg" },
  crTitle: {
    en: "Anki flashcards from <mark>Google Sheets</mark>",
    vi: "Tạo flashcard Anki từ <mark>Google Sheets</mark>",
  },
  crLead: {
    en:
      "Paste your sheet's link, look through the cards, then download an .apkg that " +
      "AnkiDroid, AnkiMobile or Anki on a computer opens. No add-on to install.",
    vi:
      "Dán link sheet, xem từng card, rồi tải file .apkg mở bằng AnkiDroid, " +
      "AnkiMobile hoặc Anki trên máy tính. Không cần cài add-on.",
  },
  paste: { en: "Paste", vi: "Dán" },
  emptyLink: {
    en: "Paste the link of your Google Sheet first.",
    vi: "Hãy dán link Google Sheets của bạn trước.",
  },
  useExample: { en: "See an example", vi: "Xem ví dụ" },
  exampleHint: {
    en: "31 sample sheets, simple to advanced",
    vi: "31 sheet mẫu, từ đơn giản tới nâng cao",
  },
  // The four buttons themselves are drawn in English: they are English in every
  // learner's Google Sheets, so they are the words to look for.
  shareTitle: { en: "Share your sheet first", vi: "Sheet phải được chia sẻ trước" },
  shareIntro: { en: "In Google Sheets, press in turn:", vi: "Trong Google Sheets, bấm lần lượt:" },
  shareThen: {
    en: "Then press Copy link and paste it above.",
    vi: "Rồi bấm Copy link và dán vào ô phía trên.",
  },
  privacy: {
    en: "Your sheet is read right here in your browser. Nothing is sent to a SheetCards server.",
    vi: "Sheet được đọc ngay trong trình duyệt của bạn. Không có gì được gửi lên máy chủ của SheetCards.",
  },
  readyNow: { en: "Ready.", vi: "Đã sẵn sàng." },
  deckLabel: { en: "Your deck", vi: "Deck của bạn" },
  changeSource: { en: "Use another link", vi: "Đổi link" },
  // The source bar's share button: the address, with the card in it.
  shareCard: { en: "Share a link to this card", vi: "Chia sẻ link tới card này" },
  shareCardCopied: {
    en: "Link copied. Whoever opens it sees this card.",
    vi: "Đã copy link. Ai mở link sẽ thấy đúng card này.",
  },
  shareCardFailed: {
    en: "Could not copy. Copy the address from the address bar instead.",
    vi: "Không copy được. Hãy copy địa chỉ trên thanh địa chỉ.",
  },
  shareCardFile: {
    en: "A file opened from this device has no link to share. Upload it to Google Sheets and paste that link here, or open it in Create sheet and use Share link.",
    vi: "File mở từ máy này không có link để chia sẻ. Hãy đưa file lên Google Sheets rồi dán link đó vào đây, hoặc mở nó trong Tạo Sheet và dùng Share link.",
  },
  deckPanel: { en: "Decks & filter", vi: "Deck & bộ lọc" },
  flipBack: { en: "Show front", vi: "Lật lại" },
  flipHintTouch: {
    en: "Tap the card to turn it · swipe for the next",
    vi: "Chạm card để lật · vuốt để đổi card",
  },
  flipHintKeys: {
    en: "Click or Space to turn · ← → for the next",
    vi: "Bấm card hoặc Space để lật · ← → để đổi card",
  },
  warnTitle: {
    en: (n) => `${n} thing${n === 1 ? "" : "s"} to check in this sheet`,
    vi: (n) => `${n} điều cần xem lại trong sheet`,
  },
  viewGrid: { en: "Grid", vi: "Bảng" },
  viewTemplate: { en: "Card template", vi: "Card template" },
  dlCards: {
    en: (n) => `${n} card${n === 1 ? "" : "s"}`,
    vi: (n) => `${n} cards`,
  },
  dlDecks: {
    en: (d) => `in ${d} deck${d === 1 ? "" : "s"}`,
    vi: (d) => `trong ${d} deck`,
  },

  // --- after the download: opening the file -----------------------------------
  // App and menu names stay English: they are what the learner's phone shows.
  doneTitle: { en: "Open it in Anki", vi: "Mở file trong Anki" },
  deviceLabel: { en: "Device", vi: "Thiết bị" },
  devAndroid: { en: "AnkiDroid", vi: "AnkiDroid" },
  devAndroidSub: { en: "Android", vi: "Android" },
  devIos: { en: "AnkiMobile", vi: "AnkiMobile" },
  devIosSub: { en: "iPhone, iPad", vi: "iPhone, iPad" },
  devDesktop: { en: "Anki", vi: "Anki" },
  devDesktopSub: { en: "Windows, Mac, Linux", vi: "Windows, Mac, Linux" },
  instAndroid1: {
    en: (file) =>
      `Tap the download notification, or open <b>Files</b> → <b>Downloads</b> and tap <code>${file}</code>.`,
    vi: (file) =>
      `Chạm vào thông báo tải xong, hoặc mở app <b>Files</b> → <b>Downloads</b> rồi chạm vào <code>${file}</code>.`,
  },
  instAndroid2: {
    en: () => "When asked which app to open it with, pick <b>AnkiDroid</b>. The deck imports straight away.",
    vi: () => "Khi được hỏi mở bằng app nào, chọn <b>AnkiDroid</b>. Deck được import ngay.",
  },
  instAndroid3: {
    en: () => "Or, inside AnkiDroid: open the menu → <b>Import</b> → choose the file.",
    vi: () => "Hoặc trong AnkiDroid: mở menu → <b>Import</b> → chọn file.",
  },
  instIos1: {
    en: (file) =>
      `Open the <b>Files</b> app → <b>Downloads</b> (or Safari's downloads list) and tap <code>${file}</code>.`,
    vi: (file) =>
      `Mở app <b>Files</b> (Tệp) → <b>Downloads</b> (hoặc danh sách tải về của Safari) rồi chạm vào <code>${file}</code>.`,
  },
  instIos2: {
    en: () => "Tap <b>Share</b>, then <b>AnkiMobile</b> — or <b>Copy to AnkiMobile</b>.",
    vi: () => "Chạm nút <b>Share</b> → chọn <b>AnkiMobile</b> (hoặc <b>Copy to AnkiMobile</b>).",
  },
  instIos3: {
    en: () => "AnkiMobile opens and offers to <b>Import</b> it. Tap that, and the deck is in.",
    vi: () => "AnkiMobile mở ra và hỏi <b>Import</b>. Chạm vào là deck được thêm.",
  },
  instDesktop1: {
    en: (file) => `Double-click <code>${file}</code> in your downloads. Anki opens and imports it.`,
    vi: (file) => `Nhấp đúp vào <code>${file}</code> trong thư mục tải về. Anki tự mở và import.`,
  },
  instDesktop2: {
    en: () => "Or, in Anki: <b>File → Import…</b> and choose the file.",
    vi: () => "Hoặc trong Anki: <b>File → Import…</b> rồi chọn file.",
  },
  assureTitle: {
    en: "Edited the sheet? Download again and import over it.",
    vi: "Sửa sheet rồi tải lại? Cứ import đè.",
  },
  assureBody: {
    en: (key = "ID") =>
      `Each note is matched by its ${key} column and by the flashcard set name written in the sheet ` +
      "itself, so importing a new file updates the notes you already have and keeps " +
      "your review progress — no duplicate cards, even if the file was renamed, saved as " +
      ".xlsx or moved to Google Sheets. A word deleted from the sheet stays in Anki; " +
      "delete it there if you want it gone.",
    vi: (key = "ID") =>
      `Mỗi note được nhận ra nhờ cột ${key} và tên bộ flashcard ghi ngay trong sheet, nên ` +
      "import file mới sẽ cập nhật đúng các note cũ và giữ nguyên tiến độ ôn tập, không " +
      "nhân đôi card — dù file bị đổi tên, lưu ra .xlsx hay đưa lên Google Sheets. Từ đã " +
      "xoá khỏi sheet vẫn còn trong Anki; muốn bỏ thì xoá trong Anki.",
  },
  // The same promise for a sheet that does not name itself: true only while
  // the link, or the file's name, stays the same.
  assureBodyLink: {
    en: (key = "ID") =>
      `Each note is matched by its ${key} column and by this Google Sheets link, so downloading ` +
      "from the same link again updates the notes you already have and keeps your review " +
      "progress. The same sheet saved as a file and uploaded would be a different deck, " +
      "unless the sheet names itself (name=).",
    vi: (key = "ID") =>
      `Mỗi note được nhận ra nhờ cột ${key} và link Google Sheets này, nên tải lại từ đúng ` +
      "link này sẽ cập nhật note cũ và giữ nguyên tiến độ ôn tập. Cùng sheet đó lưu ra file " +
      "rồi tải lên sẽ thành deck khác, trừ khi sheet có tên riêng (name=).",
  },
  assureBodyFile: {
    en: (file, key = "ID") =>
      `Each note is matched by its ${key} column and by the file's name, <b>${file}</b>. Upload a file with ` +
      "that same name and the import updates the notes you already have and keeps your review " +
      "progress. Renamed, or moved to Google Sheets, it would be a new deck — unless the sheet " +
      "names itself (name=).",
    vi: (file, key = "ID") =>
      `Mỗi note được nhận ra nhờ cột ${key} và tên file <b>${file}</b>. Tải lên file đúng tên đó ` +
      "thì import sẽ cập nhật note cũ và giữ nguyên tiến độ ôn tập. Đổi tên file hay chuyển " +
      "lên Google Sheets sẽ thành deck mới — trừ khi sheet có tên riêng (name=).",
  },
  nameOfferAdd: { en: "Add name=", vi: "Thêm name=" },
  nameOfferWhy: {
    en: (cell) =>
      "With a name of its own the sheet stays the same deck however it travels — renamed, " +
      `saved as .xlsx, moved to Google Sheets. Write <code>${cell}</code> in the ID cell of row 2, right under the column names ` +
      "(it becomes the deck's name in Anki), then download again. Best done before this set's first import: " +
      "a set already in Anki becomes a new deck once, and its old cards stop being updated.",
    vi: (cell) =>
      "Có tên riêng, sheet luôn là cùng một deck dù đổi tên file, lưu ra .xlsx hay chuyển lên " +
      `Google Sheets. Ghi <code>${cell}</code> vào ô ID của dòng 2, ngay dưới tên cột ` +
      "(đó sẽ là tên deck trong Anki), rồi tải lại. Nên làm trước lần import đầu tiên: " +
      "bộ đã có trong Anki sẽ thành deck mới một lần, và card cũ không được cập nhật nữa.",
  },
  nameOfferCopy: { en: "Copy", vi: "Copy" },
  nameOfferCopied: { en: "Copied", vi: "Đã copy" },
  addonTip: {
    en:
      'Studying on a computer? The <a href="./#addon">SheetCards add-on</a> updates ' +
      "your deck by itself whenever the sheet changes, deleted rows included.",
    vi:
      'Học trên máy tính? <a href="./#addon">Add-on SheetCards</a> tự cập nhật deck mỗi khi ' +
      "sheet đổi, kể cả dòng đã xoá.",
  },
  downloadAgain: { en: "No file? Download again", vi: "Không thấy file? Tải lại" },
  doneOk: { en: "Done", vi: "Xong" },

  nextTimeTitle: { en: "Adding words next week", vi: "Tuần sau thêm từ" },
  nextTimeBody: {
    en: "Open the sheet again — the sheet link you saved, your .csv file or your Google Sheet — add the words, press Make flashcards, download the new .apkg and import it. Your old cards are updated, not doubled.",
    vi: "Mở lại sheet — link sheet bạn đã lưu, file .csv hoặc Google Sheet của bạn — thêm từ, bấm Tạo flashcard, tải file .apkg mới rồi import. Card cũ được cập nhật, không nhân đôi.",
  },

  // --- the landing page, continued ------------------------------------------
  homeExample: { en: "See an example", vi: "Xem ví dụ" },
  homeLinkLabel: { en: "Paste a Google Sheets link to start", vi: "Dán link Google Sheets để bắt đầu" },
  homeLinkPlaceholder: {
    en: "https://docs.google.com/spreadsheets/d/…",
    vi: "https://docs.google.com/spreadsheets/d/…",
  },
  homeGo: { en: "Make flashcards", vi: "Tạo flashcard" },
  homeUpload: { en: "Open .xlsx/.csv file", vi: "Mở file .xlsx/.csv" },
  doorHaveText: {
    en: "Google Sheets, Excel, or a list in your notes.",
    vi: "Google Sheets, Excel, hoặc danh sách trong ghi chú.",
  },
  homeStep1: { en: "Link, file or text", vi: "Link, file hoặc chữ" },
  homeNoteSample: {
    en: "#config name=New words\nWord [tts=en_US] | Meaning\napple | quả táo\nborrow | mượn",
    vi: "#config name=Từ mới\nWord [tts=en_US] | Meaning\napple | quả táo\nborrow | mượn",
  },
  doorHaveTitle: {
    en: "Already have a word list",
    vi: "Đã có danh sách từ",
  },
  aiTitle: { en: "Ask AI to make your word set", vi: "Nhờ AI tạo bộ từ" },
  aiLead: {
    en: "Copy this into ChatGPT, Gemini or Claude, change the highlighted parts, then paste the answer into Paste text in Sheet to Anki (or open the file it gives you).",
    vi: "Copy câu này vào ChatGPT, Gemini hoặc Claude, sửa phần tô màu, rồi dán câu trả lời vào Dán văn bản của Sheet to Anki (hoặc mở file nó gửi).",
  },
  aiFormLabel: { en: "Answer as", vi: "Kiểu câu trả lời" },
  aiFormText: { en: "Text", vi: "Văn bản" },
  aiFormTable: { en: "Table", vi: "Bảng" },
  aiPrompt: {
    en: () =>
      `Make <span class="ai-slot">30</span> <span class="ai-slot">English</span> words about <span class="ai-slot">travel</span>, level <span class="ai-slot">B1</span>, meanings in <span class="ai-slot">Vietnamese</span>. Answer in one code block. Line 1 exactly: #config name=<span class="ai-slot">Travel B1</span>. Line 2: Word [tts=en_US; bold] | IPA [color=muted] | Meaning | Example [italic]. Then one word per line, columns separated by |.`,
    vi: () =>
      `Làm <span class="ai-slot">30</span> từ <span class="ai-slot">tiếng Anh</span> chủ đề <span class="ai-slot">du lịch</span>, trình độ <span class="ai-slot">B1</span>, nghĩa tiếng Việt. Trả lời bằng một khối code. Dòng 1 ghi đúng: #config name=<span class="ai-slot">Du lịch B1</span>. Dòng 2: Word [tts=en_US; bold] | IPA [color=muted] | Meaning | Example [italic]. Sau đó mỗi từ một dòng, các cột cách nhau bằng |.`,
  },
  aiPromptTable: {
    en: () =>
      `Make <span class="ai-slot">30</span> <span class="ai-slot">English</span> words about <span class="ai-slot">travel</span>, level <span class="ai-slot">B1</span>, meanings in <span class="ai-slot">Vietnamese</span>, as a table (or a CSV file if you can attach files). Row 1: Word | IPA | Meaning | Example. Row 2 is the settings row: first cell exactly #config name=<span class="ai-slot">Travel B1</span>; tts=en_US; bold, then color=muted, an empty cell, italic. Then one word per row.`,
    vi: () =>
      `Làm <span class="ai-slot">30</span> từ <span class="ai-slot">tiếng Anh</span> chủ đề <span class="ai-slot">du lịch</span>, trình độ <span class="ai-slot">B1</span>, nghĩa tiếng Việt, dạng bảng (hoặc file CSV nếu bạn đính kèm được file). Hàng 1: Word | IPA | Meaning | Example. Hàng 2 là settings row: ô đầu ghi đúng #config name=<span class="ai-slot">Du lịch B1</span>; tts=en_US; bold, rồi color=muted, một ô trống, italic. Sau đó mỗi từ một hàng.`,
  },
  aiPromptLabel: { en: "Prompt for the AI (you can edit it here)", vi: "Câu lệnh cho AI (sửa được ngay ở đây)" },
  aiCopy: { en: "Copy", vi: "Copy" },
  aiCopied: { en: "Copied.", vi: "Đã copy." },
  aiCopiedPaste: { en: "Copied. Paste it into the chat.", vi: "Đã copy. Dán vào khung chat." },
  aiCopyFailed: { en: "Could not copy: select the prompt and copy it by hand.", vi: "Không copy được: chọn câu lệnh và copy bằng tay." },
  aiOpenChatgpt: { en: "Open ChatGPT", vi: "Mở ChatGPT" },
  aiOpenClaude: { en: "Open Claude", vi: "Mở Claude" },
  aiOpenGemini: { en: "Open Gemini", vi: "Mở Gemini" },
  aiMore: { en: "More prompts, and fancier cards (pictures, typing, cloze) →", vi: "Thêm câu lệnh mẫu, và card cầu kỳ hơn (ảnh, gõ đáp án, cloze) →" },
  doorNewTitle: {
    en: "No sheet yet? Write one on the web",
    vi: "Chưa có sheet? Soạn trên web",
  },
  doorNewText: {
    en: "Pick a template and a theme, type your words, then press Make flashcards. No Google Sheets needed.",
    vi: "Chọn template và theme, gõ từ, rồi bấm Tạo flashcard. Không cần Google Sheets.",
  },
  doorNewGo: { en: "Open Create sheet", vi: "Mở Tạo Sheet" },
  homeTemplate: { en: "starter file (.xlsx)", vi: "file mẫu (.xlsx)" },
  homeExamplesFile: { en: "31 example sheets", vi: "31 sheet ví dụ" },
  homeDrop: { en: "Drop an .xlsx or .csv file here", vi: "Thả file .xlsx hoặc .csv vào đây" },
  homeNoLink: {
    en: "Paste the link of your Google Sheet first — or upload a file.",
    vi: "Dán link Google Sheets trước — hoặc upload một file.",
  },
  homeNotLink: {
    en: "That doesn't look like a link. Copy it from the address bar while the sheet is open.",
    vi: "Đây chưa phải một link. Hãy copy từ thanh địa chỉ khi đang mở sheet.",
  },
  homeBadFile: {
    en: "SheetCards reads .xlsx, .xlsm, .csv and .tsv files.",
    vi: "SheetCards đọc được file .xlsx, .xlsm, .csv và .tsv.",
  },
  homeStashFailed: {
    en: "This browser would not keep the file for the next page. Open Sheet to Anki and upload it there.",
    vi: "Trình duyệt không giữ được file để chuyển trang. Hãy mở Sheet to Anki và upload ở đó.",
  },
  badFileType: {
    en: (name) => `“${name}” is not a spreadsheet. SheetCards reads .xlsx, .xlsm, .csv and .tsv files.`,
    vi: (name) => `“${name}” không phải file bảng tính. SheetCards đọc được file .xlsx, .xlsm, .csv và .tsv.`,
  },
  // The parser's other refusals (pythonMessage), said in the page's language.
  emptySheet: {
    en: "This sheet is empty. Row 1 needs the column names (at least one, such as Word), with a word in each row below.",
    vi: "Sheet này đang trống. Dòng 1 cần tên các cột (ít nhất một cột, ví dụ Word), mỗi dòng bên dưới là một từ.",
  },
  noContentColumns: {
    en: "This sheet has only ID, SYNC, TAGS or SUBDECK columns. Add at least one column for what goes on the card, such as Word or Meaning.",
    vi: "Sheet này chỉ có cột ID, SYNC, TAGS hoặc SUBDECK. Thêm ít nhất một cột cho nội dung card, ví dụ Word hay Meaning.",
  },
  notAWorkbook: {
    en: "This file is named .xlsx but is not one. If it came out of an older Excel, open it and choose Save As → .xlsx.",
    vi: "File này mang đuôi .xlsx nhưng không phải file .xlsx thật. Nếu nó từ Excel đời cũ, mở ra rồi chọn Save As → .xlsx.",
  },
  oldXls: {
    en: "This is the old .xls format, which this page cannot read. Open it and choose Save As → .xlsx, or upload it to Google Sheets.",
    vi: "Đây là định dạng .xls cũ, trang này không đọc được. Mở file rồi chọn Save As → .xlsx, hoặc đưa lên Google Sheets.",
  },
  noSheets: {
    en: "This workbook has no visible sheet in it.",
    vi: "File này không có sheet nào đang hiện.",
  },
  // --- opened inside a chat app's own browser ---------------------------------
  inappTitle: { en: "You're in an app's built-in browser.", vi: "Bạn đang mở trang trong trình duyệt của một app." },
  inappTitleIn: { en: "You're inside", vi: "Bạn đang mở trang trong" },
  inappAndroid: {
    en: "Open this page in Chrome to download files — an app's built-in browser cannot save them.",
    vi: "Mở trang này bằng Chrome để tải file — trình duyệt trong app không lưu được file.",
  },
  inappIos: {
    en: "Open this page in Safari or Chrome to download files: copy the link and paste it there — or open the app's menu (the three dots) and choose to open in a browser.",
    vi: "Mở trang này bằng Safari hoặc Chrome để tải file: copy link rồi dán vào đó — hoặc mở menu của app (dấu ba chấm) và chọn mở bằng trình duyệt.",
  },
  inappOpenChrome: { en: "Open in Chrome", vi: "Mở bằng Chrome" },
  inappCopy: { en: "Copy link", vi: "Copy link" },
  inappCopied: { en: "Copied — paste it into your browser", vi: "Đã copy — dán vào trình duyệt" },
  readAsEncoding: {
    en: (enc) =>
      `This file is not UTF-8, so it was read as ${enc === "cp1258" ? "Vietnamese Windows text (cp1258)" : "Western Windows text (cp1252)"}. Check the accents look right — or save it again from Excel as “CSV UTF-8”.`,
    vi: (enc) =>
      `File này không phải UTF-8 nên đã được đọc theo ${enc === "cp1258" ? "bảng mã Windows tiếng Việt (cp1258)" : "bảng mã Windows phương Tây (cp1252)"}. Hãy kiểm tra dấu có đúng không — hoặc lưu lại từ Excel bằng “CSV UTF-8”.`,
  },
  badEncoding: {
    en: "This file's text could not be read: it is not UTF-8 and no Windows code page fits. In Excel, choose Save As → “CSV UTF-8”, then open that file.",
    vi: "Không đọc được chữ trong file này: không phải UTF-8 và không khớp bảng mã Windows nào. Trong Excel, chọn Save As → “CSV UTF-8” rồi mở file đó.",
  },
  demoImported: { en: "Imported into AnkiDroid", vi: "Đã import vào AnkiDroid" },
  featThemeTitle: {
    en: "A theme for the whole set",
    vi: "Theme cho cả bộ flashcard",
  },
  featTheme: {
    en: "Picked when you make the sheet, made for light and dark.",
    vi: "Chọn ngay khi tạo sheet, đẹp cả nền sáng lẫn nền tối.",
  },
  addonEyebrow: { en: "The add-on for Anki on a computer", vi: "Add-on cho Anki trên máy tính" },
  addonTitle: {
    en: "Studying on a computer? Install the add-on and it updates your deck by itself.",
    vi: "Học trên máy tính? Cài add-on để deck tự cập nhật.",
  },
  addonLead: {
    en: "The add-on connects Anki on a computer to your Google Sheet: each sync adds, updates and removes cards to match the sheet.",
    vi: "Add-on nối Anki trên máy tính với Google Sheet: mỗi lần sync, card được thêm, sửa và xoá theo sheet.",
  },
  addonSteps: {
    en: "Install it with <b>Tools → Add-ons → Install from file…</b>, then open <b>Tools → SheetCards → Connect a Google Sheet…</b>",
    vi: "Cài bằng <b>Tools → Add-ons → Install from file…</b>, rồi mở <b>Tools → SheetCards → Connect a Google Sheet…</b>",
  },

  // --- Liên hệ & góp ý (contact.html) ------------------------------------
  // The link at the foot of every page, where a signature used to stand.
  contactLink: { en: "Contact &amp; feedback", vi: "Liên hệ &amp; góp ý" },
  // The masthead icon's label and tooltip: an attribute, so a plain ampersand.
  contactIcon: { en: "Contact & feedback", vi: "Liên hệ & góp ý" },
  titleContact: { en: "Contact &amp; feedback — SheetCards", vi: "Liên hệ &amp; góp ý — SheetCards" },
  contactTitle: { en: "Contact &amp; feedback", vi: "Liên hệ &amp; góp ý" },
  contactLead: {
    en: "Found a bug, want a feature, or just have a question? Pick whichever way suits you.",
    vi: "Gặp lỗi, muốn có thêm tính năng, hay chỉ muốn hỏi? Chọn cách nào tiện cho bạn.",
  },
  fbTitle: { en: "Send feedback", vi: "Gửi góp ý" },
  fbClosed: {
    en: "The feedback form opens soon — in the meantime, reach me on GitHub or Facebook.",
    vi: "Form góp ý sắp mở — trong lúc chờ, bạn liên hệ qua GitHub hoặc Facebook.",
  },
  fbWhy: {
    en: "Sign in with Google to keep out spam, and so I can reply to you.",
    vi: "Cần đăng nhập Google để chống spam và để mình có thể trả lời bạn.",
  },
  fbSignedIn: {
    en: (name, email) => `Signed in: <b>${name}</b> (${email})`,
    vi: (name, email) => `Đã đăng nhập: <b>${name}</b> (${email})`,
  },
  fbSwitch: { en: "Switch account", vi: "Đổi tài khoản" },
  fbKind: { en: "What are you sending?", vi: "Bạn muốn gửi gì?" },
  fbKindBug: { en: "Bug report", vi: "Báo lỗi" },
  fbKindFeature: { en: "Feature idea", vi: "Đề xuất tính năng" },
  fbKindOther: { en: "Other", vi: "Khác" },
  fbMessage: { en: "Message", vi: "Nội dung" },
  fbImage: { en: "Screenshot (optional)", vi: "Ảnh chụp màn hình (không bắt buộc)" },
  fbImageHint: {
    en: "PNG, JPEG, WebP or GIF, up to 4 MB. Pick a file, or paste an image (Ctrl+V / ⌘V) anywhere on the page.",
    vi: "PNG, JPEG, WebP hoặc GIF, tối đa 4 MB. Chọn file, hoặc dán ảnh (Ctrl+V / ⌘V) ở bất kỳ đâu trên trang.",
  },
  fbImagePick: { en: "Choose image", vi: "Chọn ảnh" },
  fbImageRemove: { en: "Remove image", vi: "Bỏ ảnh" },
  fbSheet: { en: "Link to the sheet involved (optional)", vi: "Link sheet liên quan (không bắt buộc)" },
  fbExtra: { en: "Sent along with it", vi: "Thông tin gửi kèm" },
  fbExtraHint: {
    en: "So I can find the problem faster. Along with the email and name on your Google account.",
    vi: "Để mình tìm ra lỗi nhanh hơn. Cùng với email và tên trong tài khoản Google của bạn.",
  },
  fbExtraDevice: { en: "Device", vi: "Thiết bị" },
  fbExtraPage: { en: "Page", vi: "Trang" },
  fbExtraLang: { en: "Language", vi: "Ngôn ngữ" },
  fbExtraAgent: { en: "Browser", vi: "Trình duyệt" },
  fbSend: { en: "Send feedback", vi: "Gửi góp ý" },
  fbSending: { en: "Sending…", vi: "Đang gửi…" },
  fbDoneTitle: { en: "Thank you!", vi: "Cảm ơn bạn!" },
  fbDoneText: {
    en: (email) => `Your feedback has arrived. If I need to reply, I'll write to ${email}.`,
    vi: (email) => `Mình đã nhận được góp ý. Nếu cần trả lời, mình sẽ viết cho ${email}.`,
  },
  fbAgain: { en: "Send more feedback", vi: "Gửi thêm góp ý" },
  fbErrSignIn: { en: "Sign in with Google before sending.", vi: "Hãy đăng nhập Google trước khi gửi." },
  fbErrAuth: {
    en: "Your sign-in has expired. Sign in with Google again, then press Send.",
    vi: "Lần đăng nhập đã hết hạn. Hãy đăng nhập Google lại rồi bấm Gửi.",
  },
  fbErrRate: {
    en: "You've sent several in a row. Wait a few minutes, then send again.",
    vi: "Bạn vừa gửi khá nhiều góp ý. Hãy đợi vài phút rồi gửi lại.",
  },
  fbErrEmpty: { en: "Write your message first.", vi: "Hãy viết nội dung góp ý." },
  fbErrImage: {
    en: "The screenshot was refused: only PNG, JPEG, WebP or GIF, up to 4 MB. Remove it or pick another.",
    vi: "Ảnh không gửi được: chỉ nhận PNG, JPEG, WebP hoặc GIF, tối đa 4 MB. Bỏ ảnh hoặc chọn ảnh khác.",
  },
  fbErrImageType: {
    en: "This file is not a PNG, JPEG, WebP or GIF image.",
    vi: "File này không phải ảnh PNG, JPEG, WebP hoặc GIF.",
  },
  fbErrImageSize: { en: "This image is over 4 MB.", vi: "Ảnh này lớn hơn 4 MB." },
  fbErrImageRead: { en: "This image could not be read.", vi: "Không đọc được ảnh này." },
  fbErrServer: {
    en: "The feedback service ran into a problem. Try again later, or reach me on GitHub or Facebook.",
    vi: "Máy chủ góp ý đang gặp lỗi. Hãy thử lại sau, hoặc liên hệ qua GitHub hoặc Facebook.",
  },
  fbErrNetwork: {
    en: "Could not send: check your connection and try again.",
    vi: "Không gửi được: kiểm tra kết nối mạng rồi thử lại.",
  },
  fbErrGsi: {
    en: "The Google sign-in button did not load. An ad blocker may be blocking it — allow it on this page, or reach me on GitHub or Facebook.",
    vi: "Không tải được nút đăng nhập Google. Có thể trình chặn quảng cáo đang chặn nó — hãy tắt cho trang này, hoặc liên hệ qua GitHub hoặc Facebook.",
  },
  fbErrInApp: {
    en: "Google does not allow signing in inside a chat app's browser. Open this page in Chrome or Safari to send feedback.",
    vi: "Google không cho đăng nhập trong trình duyệt của app chat. Mở trang này bằng Chrome hoặc Safari để gửi góp ý.",
  },
  ghText: {
    en: "The source code and releases. Public bug reports go under Issues; you need a GitHub account.",
    vi: "Mã nguồn và các bản phát hành. Báo lỗi công khai ở mục Issues, cần tài khoản GitHub.",
  },
  ghIssues: { en: "Issues: report a bug", vi: "Issues: báo lỗi" },
  facebookText: { en: "Message me directly.", vi: "Nhắn tin trực tiếp cho mình." },
};

export const LANGUAGES = [
  { code: "en", label: "EN" },
  { code: "vi", label: "VI" },
];

const STORAGE_KEY = "sc-lang";

/** Remembered choice, else Vietnamese.

The site is made for Vietnamese learners first, so it opens in Vietnamese
whatever the browser says; English is one tap away and remembered once chosen. */
function initial() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && LANGUAGES.some((l) => l.code === saved)) return saved;
  } catch {
    /* private browsing: fall through to the browser's language */
  }
  return "vi";
}

let current = initial();

export const lang = () => current;

/** Switch language; `remember` false shows it without making it the choice. */
export function setLang(code, remember = true) {
  if (!LANGUAGES.some((l) => l.code === code)) return;
  current = code;
  document.documentElement.lang = code;
  if (!remember) return;
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

/**
 * Links into the docs, pointed at the docs in the page's language.
 *
 * The Vietnamese docs are at docs/, the English at docs/en/. A link carries the
 * page it means in `data-doc` (`""` for the docs' front page, `settings-row/`
 * for a page) and a static href
 * to the Vietnamese one, which is right before any script runs.
 */
export function paintDocLinks() {
  for (const a of document.querySelectorAll("a[data-doc]")) {
    a.setAttribute("href", site(`docs/${current === "en" ? "en/" : ""}${a.dataset.doc}`));
  }
}

/**
 * Every `data-i18n` element and attribute on the page, in the current language.
 * A link inside a string is written from the site's root and pointed at the
 * right page here (paths.js), since the same string is painted at several depths.
 */
export function paintStrings() {
  paintDocLinks();
  for (const el of document.querySelectorAll("[data-i18n]")) {
    el.innerHTML = t(el.dataset.i18n);
    rootLinks(el);
  }
  for (const el of document.querySelectorAll("[data-i18n-attr]")) {
    for (const pair of el.dataset.i18nAttr.split(",")) {
      const [attr, key] = pair.split(":").map((s) => s.trim());
      el.setAttribute(attr, t(key));
    }
  }
}

export { STRINGS };
