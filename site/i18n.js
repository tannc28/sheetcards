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
 * Vietnamese is the default: the site is made for Vietnamese learners first.
 * The Vietnamese keeps every technical word in English — deck, note, field,
 * card, cloze, sync, settings row, Create sheet, Create deck, every Anki and Google Sheets
 * label — and only the explanation around it is translated. The learners run
 * Anki in English, so a translated term is a word they will never see again.
 *
 * Each `data-i18n` element in the HTML carries its `vi` string as static text
 * (what shows before any script runs); tests/test_site_i18n.py keeps the two equal.
 */

const STRINGS = {
  // --- masthead and entry ---------------------------------------------------
  skip: { en: "Skip to Create deck", vi: "Tới phần Create deck" },
  toDark: { en: "Switch to dark", vi: "Chuyển sang nền tối" },
  langLabel: { en: "Language", vi: "Ngôn ngữ" },
  close: { en: "Close", vi: "Đóng" },

  // --- the site's own navigation, on every page ---------------------------
  navLabel: { en: "Site", vi: "Các trang" },
  navHome: { en: "Home", vi: "Home" },
  navPreview: { en: "Create deck", vi: "Create deck" },
  navSheet: { en: "Create sheet", vi: "Create sheet" },
  navDocs: { en: "Docs", vi: "Docs" },
  docsTag: { en: "docs", vi: "docs" },
  skipMain: { en: "Skip to the content", vi: "Tới nội dung chính" },

  // --- what the browser tab says ------------------------------------------
  // In the reader's language like the rest of the page, and on Create deck the
  // loaded sheet's name first: that is what tells two open tabs, or two entries
  // in the history, apart.
  titleHome: {
    en: "SheetCards — Anki decks from Google Sheets, right on your phone",
    vi: "SheetCards — tạo deck Anki từ Google Sheets ngay trên điện thoại",
  },
  titleCreate: {
    en: "SheetCards — Create deck: Anki decks from Google Sheets",
    vi: "SheetCards — Create deck: deck Anki từ Google Sheets",
  },
  titleDeck: { en: (name) => `${name} — Create deck · SheetCards`, vi: (name) => `${name} — Create deck · SheetCards` },
  titleSheet: {
    en: "SheetCards — Create sheet: write a flashcard sheet on the web",
    vi: "SheetCards — Create sheet: soạn sheet flashcard ngay trên web",
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
  homeEyebrow: { en: "Free · Nothing to install", vi: "Miễn phí · Không cần cài đặt" },
  homeTitle: {
    en: "Turn a Google Sheet into an Anki deck — <mark>right on your phone</mark>.",
    vi: "Tạo deck Anki từ Google Sheets — <mark>ngay trên điện thoại</mark>.",
  },
  homeLead: {
    en:
      "Write your vocabulary in a sheet, one row per card. Paste the link into " +
      "Create deck, check every card, then download an .apkg that opens straight in " +
      "AnkiDroid or AnkiMobile.",
    vi:
      "Soạn từ vựng trong sheet, mỗi dòng một card. Dán link vào Create deck, xem " +
      "trước từng card, rồi tải file .apkg mở thẳng bằng AnkiDroid hoặc AnkiMobile.",
  },
  homeDownload: { en: "Download", vi: "Tải về" },
  homeTry: { en: "Create deck", vi: "Create deck" },
  homeNeeds: {
    en: "Free and open source · Anki 25.x or later on a computer",
    vi: "Miễn phí, mã nguồn mở · Cần Anki 25.x trở lên trên máy tính",
  },

  // The demo: a row of the example workbook and the card it becomes.
  demoLabel: {
    en: "Example: from a row of a sheet to an .apkg on a phone",
    vi: "Ví dụ: từ một dòng trong sheet tới file .apkg trên điện thoại",
  },
  demoEnglish: { en: "English · paper", vi: "English · paper" },
  demoJapanese: { en: "Furigana · sakura", vi: "Furigana · sakura" },
  demoCloze: { en: "Cloze · matcha", vi: "Cloze · matcha" },
  demoFront: { en: "Card front", vi: "Mặt trước card" },
  demoBack: { en: "Card back", vi: "Mặt sau card" },
  demoPause: { en: "Pause the example", vi: "Tạm dừng ví dụ" },
  demoPlay: { en: "Play the example", vi: "Chạy ví dụ" },
  // Anki's own words on its review screen, kept in English in both languages:
  // the learners this is for run Anki in English, and a demo that says "Lại"
  // where their Anki says "Again" is showing a screen they will never see.
  showAnswer: { en: "Show Answer", vi: "Show Answer" },

  featTitle: { en: "One sheet, many kinds of card", vi: "Một sheet, nhiều kiểu card" },
  featColumnsTitle: { en: "Your columns, any language", vi: "Cột của bạn, tiếng gì cũng được" },
  featColumns: {
    en: "Name columns <code>Word</code>, <code>Nghĩa</code> or <code>汉字</code>. Each one becomes a field in Anki.",
    vi: "Đặt tên cột là <code>Word</code>, <code>Nghĩa</code> hay <code>汉字</code>. Mỗi cột thành một field trong Anki.",
  },
  featSettingsTitle: { en: "One row of settings", vi: "Một settings row" },
  featSettings: {
    en: "Row 2 sets each column's side, size and colour — <code>size=48; color=muted</code>. No template editing.",
    vi: "Dòng 2 quy định mặt, cỡ chữ và màu của từng cột — <code>size=48; color=muted</code>. Không phải sửa template.",
  },
  featSpeechTitle: { en: "Read aloud", vi: "Đọc thành tiếng" },
  featSpeech: {
    en: "Add <code>tts=en_US</code> and Anki speaks the column with the voices on your device.",
    vi: "Thêm <code>tts=en_US</code> là Anki đọc cột đó bằng giọng có sẵn trên máy.",
  },
  featTypeTitle: { en: "Type the answer", vi: "Gõ đáp án" },
  featType: {
    en: "<code>type=nc</code> puts a box on the card and checks your spelling — tone marks optional.",
    vi: "<code>type=nc</code> đặt một ô nhập trên card và kiểm tra chính tả — không cần gõ dấu.",
  },
  featDrawTitle: { en: "Cloze and handwriting", vi: "Cloze và viết tay" },
  featDraw: {
    en: "Hide words with <code>{{c1::…}}</code>, or write Chinese characters stroke by stroke with <code>draw</code>.",
    vi: "Che từ bằng <code>{{c1::…}}</code>, hoặc viết chữ Hán từng nét với <code>draw</code>.",
  },

  homeHow: { en: "How it works", vi: "Cách hoạt động" },
  homeHow1Title: { en: "Write a sheet", vi: "Soạn sheet" },
  homeHow1: {
    en:
      "In Google Sheets, in Excel, or right here with <b>Create sheet</b>. Row 1 holds " +
      "the column names: <code>ID</code>, then any columns you like. Each row below is a card.",
    vi:
      "Trong Google Sheets, Excel, hoặc ngay trên web với <b>Create sheet</b>. Dòng 1 là " +
      "tên cột: <code>ID</code>, rồi bất kỳ cột nào bạn muốn. Mỗi dòng bên dưới là một card.",
  },
  homeHow2Title: { en: "Open it in Create deck", vi: "Mở trong Create deck" },
  homeHow2: {
    en:
      "From Create sheet, one tap on <b>Create deck</b>. From Google Sheets: " +
      "<b>Share → General access → Anyone with the link → Viewer</b>, then paste the link. " +
      "Look through the cards one by one.",
    vi:
      "Từ Create sheet, bấm <b>Create deck</b> là xong. Từ Google Sheets: " +
      "<b>Share → General access → Anyone with the link → Viewer</b>, rồi dán link. " +
      "Xem lại từng card.",
  },
  homeHow3Title: { en: "Download .apkg", vi: "Download .apkg" },
  homeHow3: {
    en:
      "Press <b>Download .apkg</b> and open the file in <b>AnkiDroid</b>, " +
      "<b>AnkiMobile</b> or Anki on a computer. Changed the sheet? Download again and " +
      "import over it.",
    vi:
      "Bấm <b>Download .apkg</b> rồi mở file bằng <b>AnkiDroid</b>, <b>AnkiMobile</b> " +
      "hoặc Anki trên máy tính. Sửa sheet thì tải lại và import đè.",
  },
  homeInstall1: {
    en: "Download <code>sheetcards.ankiaddon</code>.",
    vi: "Tải file <code>sheetcards.ankiaddon</code>.",
  },
  homeInstall2: {
    en: "In Anki, open <b>Tools → Add-ons</b>, press <b>Install from file…</b> and pick that file.",
    vi: "Trong Anki, mở <b>Tools → Add-ons</b>, bấm <b>Install from file…</b> rồi chọn file vừa tải.",
  },
  homeInstall3: {
    en: "Restart Anki. A <b>SheetCards</b> menu appears under <b>Tools</b>.",
    vi: "Khởi động lại Anki. Menu <b>SheetCards</b> sẽ xuất hiện trong <b>Tools</b>.",
  },
  homePreviewText: {
    en: "Make an Anki deck from Google Sheets on your phone or computer, no add-on needed.",
    vi: "Tạo deck Anki từ Google Sheets ngay trên điện thoại hoặc máy tính, không cần cài add-on.",
  },
  homeSheetText: {
    en: "No Google Sheet? Write the whole sheet right on the web, and watch each card as you type.",
    vi: "Không có Google Sheet? Soạn cả sheet ngay trên web và xem từng card khi gõ.",
  },
  homeDocsText: {
    en: "Columns, settings, sound, pictures and syncing, explained.",
    vi: "Cột, settings row, âm thanh, hình ảnh và sync, giải thích từng phần.",
  },
  homeGithubText: {
    en: "Source code, releases and bug reports.",
    vi: "Mã nguồn, các bản phát hành và báo lỗi.",
  },
  homeFootNote: {
    en: "MIT licence. SheetCards is not made by or affiliated with Anki or Ankitects.",
    vi: "Giấy phép MIT. SheetCards không do Anki hay Ankitects làm ra và không liên kết với họ.",
  },


  // --- Create sheet ---------------------------------------------------------
  // The step before Create deck: a whole sheet written in the browser. Its
  // reader is usually on a phone and may never have opened a spreadsheet, so
  // the words are a learner's — "từ", a word — rather than a spreadsheet's.
  skipSheet: { en: "Skip to Create sheet", vi: "Tới phần Create sheet" },
  shStep1: { en: "Write the sheet", vi: "Viết sheet" },
  shTitle: {
    en: "Write a flashcard sheet <mark>right on the web</mark>",
    vi: "Soạn sheet flashcard <mark>ngay trên web</mark>",
  },
  shLead: {
    en: "No Google Sheets needed. Pick a template, type your words, then press Create deck for an .apkg that AnkiDroid, AnkiMobile or Anki opens.",
    vi: "Không cần Google Sheets. Chọn một mẫu, gõ từ của bạn, rồi bấm Create deck để có file .apkg cho AnkiDroid, AnkiMobile hoặc Anki.",
  },
  shPickTemplate: { en: "Start from a template", vi: "Bắt đầu từ một mẫu" },
  tplBlank: { en: "Blank", vi: "Trống" },
  tplBlankText: { en: "Front and Back — name the columns yourself", vi: "Front và Back — tự đặt tên cột" },
  tplBlankName: { en: "New sheet", vi: "Sheet mới" },
  tplEnglish: { en: "English vocab", vi: "Từ vựng tiếng Anh" },
  tplEnglishText: { en: "Word, IPA, Meaning, Example — read aloud", vi: "Word, IPA, Meaning, Example — có đọc to" },
  tplEnglishName: { en: "English vocab", vi: "Từ vựng tiếng Anh" },
  tplKanji: { en: "Kanji", vi: "Kanji" },
  tplKanjiText: { en: "Japanese with furigana over the kanji", vi: "Tiếng Nhật, có furigana trên kanji" },
  tplKanjiName: { en: "Kanji", vi: "Kanji" },
  tplCloze: { en: "Cloze", vi: "Cloze" },
  tplClozeText: { en: "Sentences with a word hidden: {{c1::…}}", vi: "Câu có từ bị che: {{c1::…}}" },
  tplClozeName: { en: "Cloze", vi: "Cloze" },
  shOpenFile: { en: "Open an .xlsx or .csv file", vi: "Mở file .xlsx hoặc .csv" },
  shOpenFileHint: { en: "to keep editing a sheet you already have", vi: "để sửa tiếp một sheet bạn đã có" },
  shHaveSheet: { en: "Already have a Google Sheet?", vi: "Đã có Google Sheet?" },
  shHaveSheetHint: { en: "Paste its link straight into Create deck", vi: "Dán link thẳng vào Create deck" },
  shPrivacy: {
    en: "The sheet is kept in this browser. Nothing is sent to SheetCards' servers.",
    vi: "Sheet được lưu ngay trong trình duyệt này. Không có gì được gửi lên máy chủ của SheetCards.",
  },
  shWorkLabel: { en: "Your sheet", vi: "Sheet của bạn" },
  shTitleLabel: { en: "Sheet name", vi: "Tên sheet" },
  shSaved: { en: "Draft saved in this browser", vi: "Đã lưu nháp trong trình duyệt" },
  shNotSaved: {
    en: "This browser won't keep a draft — download the file to keep it",
    vi: "Trình duyệt không cho lưu nháp — hãy tải file về để giữ",
  },
  shUndo: { en: "Undo", vi: "Hoàn tác" },
  shRedo: { en: "Redo", vi: "Làm lại" },
  shNew: { en: "New sheet", vi: "Tạo sheet mới" },
  shNewTitle: { en: "Start a new sheet?", vi: "Tạo sheet mới?" },
  shNewText: {
    en: (n) => `The ${n} word${n === 1 ? "" : "s"} in this sheet will be cleared from this browser. Download it or copy its Share link first if you want to keep it.`,
    vi: (n) => `${n} từ trong sheet này sẽ bị xoá khỏi trình duyệt. Muốn giữ thì Download hoặc copy Share link trước.`,
  },
  shNewYes: { en: "Clear and start over", vi: "Xoá và làm lại" },
  shKeep: { en: "Keep my sheet", vi: "Giữ sheet hiện tại" },
  shViewLabel: { en: "Showing", vi: "Phần đang xem" },
  shViewRows: { en: "Words", vi: "Các từ" },
  shViewLook: { en: "Columns & card", vi: "Cột & card" },
  shRows: { en: "Words", vi: "Các từ" },
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
  shDownload: { en: "Download", vi: "Download" },
  shToDeck: { en: "Create deck", vi: "Create deck" },
  shNeedWord: { en: "Add at least one word first", vi: "Thêm ít nhất một từ trước đã" },
  shHandoffFailed: {
    en: "This browser would not pass the sheet on. Download it and open the file in Create deck.",
    vi: "Trình duyệt không chuyển được sheet. Hãy Download rồi mở file trong Create deck.",
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
  shShareToDeck: { en: "Open straight as cards in Create deck", vi: "Mở thẳng thành cards trong Create deck" },
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
    en: "Text alignment. Written in the #config cell it sets the default for every column.",
    vi: "Căn lề chữ. Viết trong ô #config thì nó là mặc định cho mọi cột.",
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
    en: "Speaking rate, 0.5–2.0. Written in the #config cell it sets the default for every column.",
    vi: "Tốc độ đọc, 0.5–2.0. Viết trong ô #config thì nó là mặc định cho mọi cột.",
  },
  helpLabel: {
    en: "A small caption printed above the field.",
    vi: "Một dòng nhãn nhỏ in phía trên field.",
  },
  helpType: {
    en: "Anki draws a box on the question and compares what you type against this column. type=nc ignores accents. One column per sheet.",
    vi: "Anki hiện ô nhập ở mặt câu hỏi rồi so cái bạn gõ với cột này. type=nc bỏ qua dấu. Mỗi sheet một cột.",
  },
  helpSubdeck: {
    en: "This column becomes a level of the deck path. It is never drawn on the card — filing a note and printing on it are different jobs.",
    vi: "Cột này thành một tầng trong đường dẫn deck. Nó không bao giờ hiện trên card — xếp note vào deck và in lên card là hai việc khác nhau.",
  },
  helpSort: {
    en: "Anki lists notes by this column in the browser and sorts a deck by it. Without it that is the ID column, which is a list of nothing. One column per sheet, and it is drawn on the card exactly as before.",
    vi: "Anki sẽ hiện cột này ở Browse và sắp xếp deck theo nó. Không đặt thì nó lấy cột ID, tức là một danh sách vô nghĩa. Mỗi sheet một cột, và cột đó vẫn hiện trên card như bình thường.",
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
    en: "The typeface for this column. sc/tc/jp/kr load a Noto CJK font — worth it because 直 and 骨 are drawn differently in Chinese and Japanese and a machine with one CJK font picks for you. Any installed family name also works.",
    vi: "Font cho cột này. sc/tc/jp/kr nạp font Noto CJK — đáng dùng vì 直 hay 骨 có tự dạng khác nhau giữa tiếng Trung và tiếng Nhật, máy chỉ có một font CJK thì nó chọn thay bạn. Gõ tên font đã cài trong máy cũng được.",
  },
  helpRtl: {
    en: "Right to left, for Arabic, Hebrew and Persian. The column also starts from the right unless align says otherwise.",
    vi: "Viết từ phải sang trái, cho tiếng Ả Rập, Do Thái, Ba Tư. Cột cũng canh phải luôn, trừ khi bạn ghi align khác.",
  },
  helpVertical: {
    en: "Top to bottom, right to left — classical Japanese and Chinese. Latin words inside the line stay upright.",
    vi: "Viết từ trên xuống, phải sang trái — kiểu văn bản Nhật/Trung cổ. Chữ Latin trong dòng vẫn đứng thẳng.",
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
    en: "The cell holds a video link — YouTube, Drive, or a direct file. The address is rewritten into that site's own player while it syncs.",
    vi: "Ô chứa link video — YouTube, Drive, hoặc file trực tiếp. Địa chỉ được đổi sang trình phát của chính trang đó lúc sync.",
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
      `${front} field on the front, ${back} on the back — the same split the sync makes.`,
    vi: (front, back) =>
      `${front} field ở mặt trước, ${back} ở mặt sau — đúng cách sync chia.`,
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
  go: { en: "Create deck", vi: "Tạo deck" },
  pick: { en: "Choose an .xlsx or .csv file", vi: "Chọn file .xlsx hoặc .csv" },
  orDrop: { en: "or drop one anywhere on this page", vi: "hoặc kéo thả file vào trang này" },
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
    en: "Getting Create deck ready (~5 MB, first time only)…",
    vi: "Đang chuẩn bị Create deck (~5 MB, chỉ lần đầu)…",
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
  downloading: { en: "Downloading the sheet…", vi: "Đang tải sheet về…" },
  reading: { en: "Reading the file…", vi: "Đang đọc file…" },
  analysing: { en: "Building the cards…", vi: "Đang dựng card…" },
  readRows: {
    en: (n, s) => `${n} rows · ${s} will sync`,
    vi: (n, s) => `${n} dòng · ${s} sẽ sync`,
  },
  bootFailed: {
    en: (m) => `Create deck could not load (${m}). Reload the page to try again.`,
    vi: (m) => `Không tải được Create deck (${m}). Tải lại trang để thử lại.`,
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
  demoNote: {
    en: "This is the example workbook. Pick another sheet above, or change to your own link.",
    vi: "Đang xem file ví dụ. Chọn sheet khác ở ô phía trên, hoặc đổi sang link của bạn.",
  },
  // The same note, in the one line a phone has room for above the fold.

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
  tabTemplate: { en: "template", vi: "template" },
  prevRow: { en: "Previous card", vi: "Card trước" },
  clozeCard: { en: "Cloze card", vi: "Card cloze" },
  clozeCardN: { en: (n) => `card c${n}`, vi: (n) => `card c${n}` },
  cardFrameTitle: { en: "Card preview", vi: "Preview card" },
  nextRow: { en: "Next card", vi: "Card sau" },

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
      `Chỗ cloze nằm ở <code>${cols}</code> chứ không ở mặt trước, nên Anki để ` +
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
      `${ids}. Notes are keyed by ID, so only one row of each survives the sync.`,
    vi: (ids) =>
      `${ids}. Note được khoá theo ID, nên mỗi ID chỉ một dòng sống sót sau sync.`,
  },
  // One sentence, and the reasoning behind a disclosure for whoever wonders.
  warningsFrom: {
    en:
      "Lines labelled “Settings row” are the add-on's own words, kept in English " +
      "because that is exactly what Anki will show you at sync time." +
      "<details><summary>Why?</summary>Translated, they would no longer match what " +
      "Anki says. Nothing is silently ignored: a value the add-on does not " +
      "understand is refused, never guessed at, and the column keeps its default " +
      "until the sheet is fixed.</details>",
    vi:
      "Các dòng gắn nhãn “Settings row” là nguyên văn add-on báo, được giữ tiếng " +
      "Anh vì đó đúng là câu Anki sẽ hiện lúc sync." +
      "<details><summary>Tại sao?</summary>Dịch ra thì nó sẽ không còn khớp với " +
      "câu Anki báo. Không có gì bị bỏ qua âm thầm: giá trị add-on không hiểu thì " +
      "bị từ chối chứ không bị đoán, và cột giữ mặc định cho tới khi sheet được " +
      "sửa.</details>",
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
  legendSynced: { en: "syncs", vi: "sẽ sync" },
  legendSkipped: { en: "not ticked in SYNC", vi: "chưa tick SYNC" },
  legendInvalid: { en: "no ID", vi: "không có ID" },
  legendGhost: {
    en: "Blank rows are ignored entirely.",
    vi: "Dòng trống bị bỏ qua hoàn toàn.",
  },

  // --- Create deck: the three steps ------------------------------------------
  railLabel: { en: "Steps", vi: "Các bước" },
  crStep1: { en: "Add your sheet", vi: "Dán link sheet" },
  crStep2: { en: "Check the cards", vi: "Kiểm tra cards" },
  crStep3: { en: "Download .apkg", vi: "Download .apkg" },
  crTitle: {
    en: "Make an Anki deck from <mark>Google Sheets</mark>",
    vi: "Tạo deck Anki từ <mark>Google Sheets</mark>",
  },
  crLead: {
    en:
      "Paste your sheet's link, look through the cards, then download an .apkg that " +
      "AnkiDroid, AnkiMobile or Anki on a computer opens. Nothing to install.",
    vi:
      "Dán link sheet, xem từng card, rồi tải file .apkg mở bằng AnkiDroid, " +
      "AnkiMobile hoặc Anki trên máy tính. Không cần cài gì.",
  },
  paste: { en: "Paste", vi: "Dán" },
  emptyLink: {
    en: "Paste the link of your Google Sheet first.",
    vi: "Hãy dán link Google Sheets của bạn trước.",
  },
  useExample: { en: "Try the example file", vi: "Dùng file ví dụ" },
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
  viewTemplate: { en: "Template", vi: "Template" },
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
    en:
      "Each note is matched by its ID column, so importing a new file updates the notes " +
      "you already have and keeps your review progress — no duplicate cards. Use the same " +
      "link (or the same file name) each time. A row deleted from the sheet is not removed " +
      "from Anki.",
    vi:
      "Mỗi note được nhận ra nhờ cột ID, nên import file mới sẽ cập nhật đúng các note cũ " +
      "và giữ nguyên tiến độ ôn tập, không nhân đôi card. Chỉ cần dùng lại cùng link " +
      "(hoặc cùng tên file). Dòng đã xoá khỏi sheet thì không tự mất trong Anki.",
  },
  addonTip: {
    en:
      'Studying on a computer? The <a href="./#addon">SheetCards add-on</a> syncs ' +
      "automatically whenever the sheet changes, deleted rows included.",
    vi:
      'Học trên máy tính? <a href="./#addon">Add-on SheetCards</a> sync tự động mỗi khi ' +
      "sheet đổi, kể cả dòng đã xoá.",
  },
  downloadAgain: { en: "No file? Download again", vi: "Không thấy file? Tải lại" },
  doneOk: { en: "Done", vi: "Xong" },

  // --- the landing page, continued ------------------------------------------
  homeExample: { en: "See an example", vi: "Xem ví dụ" },
  homeLinkLabel: { en: "Paste a Google Sheets link to start", vi: "Dán link Google Sheets để bắt đầu" },
  homeLinkPlaceholder: {
    en: "https://docs.google.com/spreadsheets/d/…",
    vi: "https://docs.google.com/spreadsheets/d/…",
  },
  homeGo: { en: "Create deck", vi: "Tạo deck" },
  homeUpload: { en: "Upload .xlsx / .csv", vi: "Upload file .xlsx / .csv" },
  homeTemplateLead: { en: "No Google Sheet?", vi: "Chưa có Google Sheet?" },
  homeWriteHere: { en: "Write one on the web → Create sheet", vi: "Soạn ngay trên web → Create sheet" },
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
    en: "This browser would not keep the file for the next page. Open Create deck and upload it there.",
    vi: "Trình duyệt không giữ được file để chuyển trang. Hãy mở Create deck và upload ở đó.",
  },
  badFileType: {
    en: (name) => `“${name}” is not a spreadsheet. SheetCards reads .xlsx, .xlsm, .csv and .tsv files.`,
    vi: (name) => `“${name}” không phải file bảng tính. SheetCards đọc được file .xlsx, .xlsm, .csv và .tsv.`,
  },
  noIdColumn: {
    en: "This sheet has no ID column. Row 1 needs a column named ID, with a different value in each row below it.",
    vi: "Sheet này chưa có cột ID. Dòng 1 cần một cột tên ID, mỗi dòng bên dưới ghi một giá trị khác nhau.",
  },
  homeRuns: {
    en: "Runs in your browser · Android, iPhone, computer",
    vi: "Chạy ngay trong trình duyệt · Android, iPhone, máy tính",
  },
  demoImported: { en: "Imported into AnkiDroid", vi: "Đã import vào AnkiDroid" },
  whyTitle: { en: "Why Create deck", vi: "Vì sao dùng Create deck" },
  whyPhoneTitle: { en: "No computer needed", vi: "Không cần máy tính" },
  whyPhone: {
    en: "Paste the link, check the cards, download the file and open it in AnkiDroid or AnkiMobile — every step works on a phone.",
    vi: "Dán link, xem card, tải file và mở bằng AnkiDroid hoặc AnkiMobile — mọi bước đều làm được trên điện thoại.",
  },
  whyFreeTitle: { en: "Free, no account", vi: "Miễn phí, không cần tài khoản" },
  whyFree: {
    en: "No sign-up, no ads. Your sheet is read right in your browser and sent to no server.",
    vi: "Không đăng ký, không quảng cáo. Sheet được đọc ngay trong trình duyệt, không gửi lên máy chủ nào.",
  },
  whySourceTitle: { en: "Your sheet stays the original", vi: "Sheet vẫn là bản gốc" },
  whySource: {
    en: "Edit and add words in Google Sheets, write them with classmates or a teacher. The deck is always made again from the sheet.",
    vi: "Sửa và thêm từ ngay trong Google Sheets, soạn chung với bạn học hay giáo viên. Deck luôn được tạo lại từ sheet.",
  },
  whyKeepTitle: { en: "Re-importing keeps your progress", vi: "Import lại vẫn giữ tiến độ" },
  whyKeep: {
    en: "Every note is tied to its ID column, so a new file updates the old cards instead of doubling them — your review schedule stays.",
    vi: "Mỗi note gắn với cột ID, nên file mới cập nhật card cũ thay vì nhân đôi — lịch ôn tập không mất.",
  },
  featThemeTitle: { en: "A theme for the whole deck", vi: "Theme cho cả deck" },
  featTheme: {
    en: "Add <code>theme=sakura</code> to the settings row and every card changes colour, in light and dark.",
    vi: "Thêm <code>theme=sakura</code> vào settings row là mọi card đổi màu, cả nền sáng lẫn nền tối.",
  },
  featEditorLink: { en: "Try a settings row in Create sheet →", vi: "Thử settings row trong Create sheet →" },
  addonEyebrow: { en: "The add-on for Anki on a computer", vi: "Add-on cho Anki trên máy tính" },
  addonTitle: {
    en: "Studying on a computer? Install the add-on and it syncs by itself.",
    vi: "Học trên máy tính? Cài add-on để sync tự động.",
  },
  addonLead: {
    en:
      "The SheetCards add-on connects Anki on your computer straight to your sheet. " +
      "Each sync adds new rows, updates changed ones and removes deleted ones — then " +
      "AnkiWeb carries it all to your phone.",
    vi:
      "Add-on SheetCards nối Anki trên máy tính thẳng với sheet của bạn. Mỗi lần sync, " +
      "nó thêm dòng mới, sửa dòng đã đổi và xoá dòng đã bỏ — rồi AnkiWeb đưa tất cả " +
      "sang điện thoại.",
  },
  homeInstall4: {
    en:
      "Open <b>Tools → SheetCards → Connect a Google Sheet…</b> and paste the link. " +
      "After that, <b>Ctrl+Shift+S</b> brings in whatever changed.",
    vi:
      "Mở <b>Tools → SheetCards → Connect a Google Sheet…</b> rồi dán link. Từ đó, " +
      "<b>Ctrl+Shift+S</b> sync những gì đã thay đổi.",
  },
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
 * page it means in `data-doc` (`""` for the docs' front page) and a static href
 * to the Vietnamese one, which is right before any script runs.
 */
export function paintDocLinks() {
  for (const a of document.querySelectorAll("a[data-doc]")) {
    a.setAttribute(
      "href",
      `./docs/${current === "en" ? "en/" : ""}${a.dataset.doc}`,
    );
  }
}

export { STRINGS };
