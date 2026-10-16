/**
 * What the settings row got wrong, in the reader's language.
 *
 * The parser (src/sheet_config.py, src/tsv_model.py) writes each warning as an
 * English sentence for the add-on and its log, and tags it with a stable code
 * and the values that filled it (SheetWarning). The page says the same thing
 * from the code; a code this table does not know keeps the parser's English.
 * tests/test_site_warnings.py holds this table to sheet_config.WARNING_CODES.
 *
 * Anki's and the settings row's own words stay English, as everywhere on the
 * site: the key, the value and the column are what the reader types.
 *
 * No DOM in here, so the test can import it in node.
 */

const q = (s) => `'${s}'`;
const does = (list) => (String(list).includes(",") ? "do" : "does");
const MEDIA_VI = { image: "ảnh", audio: "âm thanh", video: "video", drawn: "ô tập viết" };
const media = (m) => MEDIA_VI[m] || m;

export const WARNINGS = {
  "media-twice": {
    en: (p) => `${q(p.col)}: already set to ${p.media}, ignoring ${q(p.key)} — a column holds one kind of media`,
    vi: (p) => `${q(p.col)}: cột đã là ${p.media}, bỏ qua ${q(p.key)} — mỗi cột chỉ chứa một loại media`,
  },
  "math-mode": {
    en: (p) => `${q(p.col)}: math is written bare or as math=block — got ${q(p.value)}`,
    vi: (p) => `${q(p.col)}: math viết trơn hoặc math=block — đang là ${q(p.value)}`,
  },
  "type-mode": {
    en: (p) => `${q(p.col)}: type must be written bare or as type=nc — got ${q(p.value)}`,
    vi: (p) => `${q(p.col)}: type viết trơn hoặc type=nc — đang là ${q(p.value)}`,
  },
  "needs-value": {
    en: (p) => `${q(p.col)}: ${q(p.key)} needs a value (write ${p.key}=…)`,
    vi: (p) => `${q(p.col)}: ${q(p.key)} cần một giá trị (viết ${p.key}=…)`,
  },
  "side-bad": {
    en: (p) => `${q(p.col)}: side must be one of front, back, hide — got ${q(p.value)}`,
    vi: (p) => `${q(p.col)}: side phải là front, back hoặc hide — đang là ${q(p.value)}`,
  },
  "font-empty": {
    en: (p) => `${q(p.col)}: font needs a name — ${p.fonts}, or a family`,
    vi: (p) => `${q(p.col)}: font cần một tên — ${p.fonts}, hoặc tên một font`,
  },
  "align-bad": {
    en: (p) => `${q(p.col)}: align must be left, center or right — got ${q(p.value)}`,
    vi: (p) => `${q(p.col)}: align phải là left, center hoặc right — đang là ${q(p.value)}`,
  },
  "size-nan": {
    en: (p) => `${q(p.col)}: size must be a number of pixels — got ${q(p.value)}`,
    vi: (p) => `${q(p.col)}: size phải là một số pixel — đang là ${q(p.value)}`,
  },
  "color-bad": {
    en: (p) => `${q(p.col)}: ${q(p.value)} is not a colour name or #hex value`,
    vi: (p) => `${q(p.col)}: ${q(p.value)} không phải tên màu hay mã #hex`,
  },
  "tts-short": {
    en: (p) =>
      `${q(p.col)}: tts needs a full language code such as zh_CN or en_US — got ${q(p.value)}. ` +
      "Anki matches the code against installed voices exactly, so a short code plays nothing.",
    vi: (p) =>
      `${q(p.col)}: tts cần mã ngôn ngữ đầy đủ như zh_CN hay en_US — đang là ${q(p.value)}. ` +
      "Anki so mã này đúng từng chữ với giọng đọc đã cài, nên mã ngắn sẽ không đọc gì.",
  },
  "voices-empty": {
    en: (p) => `${q(p.col)}: voices needs at least one voice name`,
    vi: (p) => `${q(p.col)}: voices cần ít nhất một tên giọng đọc`,
  },
  "speed-nan": {
    en: (p) => `${q(p.col)}: speed must be a number — got ${q(p.value)}`,
    vi: (p) => `${q(p.col)}: speed phải là một số — đang là ${q(p.value)}`,
  },
  "speed-range": {
    en: (p) => `${q(p.col)}: speed ${p.value} is outside 0.5–2.0`,
    vi: (p) => `${q(p.col)}: speed ${p.value} nằm ngoài khoảng 0.5–2.0`,
  },
  "subdeck-nan": {
    en: (p) => `${q(p.col)}: subdeck must be a level number — got ${q(p.value)}`,
    vi: (p) => `${q(p.col)}: subdeck phải là số tầng — đang là ${q(p.value)}`,
  },
  "subdeck-low": {
    en: (p) => `${q(p.col)}: subdeck level ${p.value} is below 1`,
    vi: (p) => `${q(p.col)}: subdeck tầng ${p.value} nhỏ hơn 1`,
  },
  "media-subdeck": {
    en: (p) => `${q(p.col)}: a ${p.media} column cannot be a deck level`,
    vi: (p) => `${q(p.col)}: cột ${media(p.media)} không thể làm một tầng của deck`,
  },
  "subdeck-inert": {
    en: (p) => `${q(p.col)}: a deck level is not part of the card, so ${p.keys} ${does(p.keys)} nothing here`,
    vi: (p) => `${q(p.col)}: cột làm tầng deck không hiện trên card, nên ${p.keys} không có tác dụng ở đây`,
  },
  "only-one-cloze": {
    en: (p) => `only one column can carry the cloze deletions — keeping ${q(p.col)}, ignoring ${p.others}`,
    vi: (p) => `chỉ một cột được chứa cloze — giữ ${q(p.col)}, bỏ qua ${p.others}`,
  },
  "only-one-type": {
    en: (p) => `only one column can be typed in — keeping ${q(p.col)}, ignoring ${p.others}`,
    vi: (p) => `chỉ một cột được gõ đáp án (type) — giữ ${q(p.col)}, bỏ qua ${p.others}`,
  },
  "only-one-sort": {
    en: (p) => `only one column can be the one the browser sorts by — keeping ${q(p.col)}, ignoring ${p.others}`,
    vi: (p) => `chỉ một cột được dùng để sắp xếp (sort) — giữ ${q(p.col)}, bỏ qua ${p.others}`,
  },
  "sort-media": {
    en: (p) => `${q(p.col)}: a media column is no use to sort by`,
    vi: (p) => `${q(p.col)}: không sắp xếp được theo cột media`,
  },
  "role-media": {
    en: (p) => `${q(p.col)}: ${p.key} does nothing on a media column`,
    vi: (p) => `${q(p.col)}: ${p.key} không có tác dụng trên cột media`,
  },
  "level-twice": {
    en: (p) => `${q(p.col)}: level ${p.value} is already ${q(p.other)} — two columns cannot be the same level of the deck`,
    vi: (p) => `${q(p.col)}: tầng ${p.value} đã là ${q(p.other)} — hai cột không thể cùng một tầng deck`,
  },
  "subdeck-headers-ignored": {
    en: (p) => `the settings row builds the deck path, so the reserved ${p.others} column${p.others.includes(",") ? "s are" : " is"} ignored`,
    vi: (p) => `settings row đã chia tầng deck, nên (các) cột ${p.others} bị bỏ qua`,
  },
  "deck-unknown": {
    en: (p) => `'#config': unknown deck setting ${q(p.key)}`,
    vi: (p) => `'#config': không có setting ${q(p.key)} cho cả deck`,
  },
  "deck-needs-value": {
    en: (p) => `'#config': ${q(p.key)} needs a value`,
    vi: (p) => `'#config': ${q(p.key)} cần một giá trị`,
  },
  "deck-align-bad": {
    en: () => "'#config': align must be left, center or right",
    vi: () => "'#config': align phải là left, center hoặc right",
  },
  "theme-unknown": {
    en: (p) => `'#config': unknown theme ${q(p.value)} — the themes are ${p.themes}`,
    vi: (p) => `'#config': không có theme ${q(p.value)} — các theme là ${p.themes}`,
  },
  "deck-speed-nan": {
    en: (p) => `'#config': speed must be a number — got ${q(p.value)}`,
    vi: (p) => `'#config': speed phải là một số — đang là ${q(p.value)}`,
  },
  "deck-speed-range": {
    en: (p) => `'#config': speed ${p.value} is outside 0.5–2.0`,
    vi: (p) => `'#config': speed ${p.value} nằm ngoài khoảng 0.5–2.0`,
  },
  "name-long": {
    en: (p) => `'#config': name is longer than ${p.value} characters`,
    vi: (p) => `'#config': name dài quá ${p.value} ký tự`,
  },
  "name-empty-level": {
    en: (p) => `'#config': name ${q(p.value)} has an empty level`,
    vi: (p) => `'#config': name ${q(p.value)} có một tầng trống (hai dấu :: liền nhau)`,
  },
  "next-bad": {
    en: (p) => `'#config': next must be an ID ending in a number, like w15 — got ${q(p.value)}`,
    vi: (p) => `'#config': next phải là một ID kết thúc bằng số, như w15 — đang là ${q(p.value)}`,
  },
  "unknown-setting": {
    en: (p) => `${q(p.col)}: unknown setting ${q(p.key)}`,
    vi: (p) => `${q(p.col)}: không có setting ${q(p.key)}`,
  },
  "size-range-width": {
    en: (p) => `${q(p.col)}: width ${p.value}px is outside ${p.low}–${p.high}px`,
    vi: (p) => `${q(p.col)}: chiều rộng ${p.value}px nằm ngoài ${p.low}–${p.high}px`,
  },
  "size-range-box": {
    en: (p) => `${q(p.col)}: box ${p.value}px is outside ${p.low}–${p.high}px`,
    vi: (p) => `${q(p.col)}: ô tập viết ${p.value}px nằm ngoài ${p.low}–${p.high}px`,
  },
  "size-range-font": {
    en: (p) => `${q(p.col)}: font size ${p.value}px is outside ${p.low}–${p.high}px`,
    vi: (p) => `${q(p.col)}: cỡ chữ ${p.value}px nằm ngoài ${p.low}–${p.high}px`,
  },
  "media-tts": {
    en: (p) => `${q(p.col)}: tts on a ${p.media} column would read the URL aloud — removed`,
    vi: (p) => `${q(p.col)}: tts trên cột ${media(p.media)} sẽ đọc to cái link — đã bỏ`,
  },
  "furigana-on": {
    en: (p) => `${q(p.col)}: furigana does nothing on a ${p.media} column`,
    vi: (p) => `${q(p.col)}: furigana không có tác dụng trên cột ${media(p.media)}`,
  },
  "inert-on": {
    en: (p) => `${q(p.col)}: ${p.keys} ${does(p.keys)} nothing on a ${p.media} column`,
    vi: (p) => `${q(p.col)}: ${p.keys} không có tác dụng trên cột ${media(p.media)}`,
  },
  "media-drawn": {
    en: (p) => `${q(p.col)}: a ${p.media} column holds an address, so ${p.key} has nothing to draw — removed`,
    vi: (p) => `${q(p.col)}: cột ${media(p.media)} chứa một link, nên ${p.key} không có gì để vẽ — đã bỏ`,
  },
  "audio-size": {
    en: (p) => `${q(p.col)}: size does nothing on an audio column`,
    vi: (p) => `${q(p.col)}: size không có tác dụng trên cột âm thanh`,
  },
  "draw-media": {
    en: (p) => `${q(p.col)}: a ${p.media} column holds an address, not a character — draw removed`,
    vi: (p) => `${q(p.col)}: cột ${media(p.media)} chứa một link, không phải một chữ — đã bỏ draw`,
  },
  "draw-cloze": {
    en: (p) => `${q(p.col)}: a cloze column cannot also be drawn — draw removed`,
    vi: (p) => `${q(p.col)}: cột cloze không thể đồng thời là ô tập viết — đã bỏ draw`,
  },
  "math-and-code": {
    en: (p) => `${q(p.col)}: a column is drawn as a formula or as code, not both`,
    vi: (p) => `${q(p.col)}: một cột chỉ là công thức (math) hoặc code, không thể cả hai`,
  },
  "draw-drops": {
    en: (p) => `${q(p.col)}: a writing box draws a character, so ${p.key} is removed`,
    vi: (p) => `${q(p.col)}: ô tập viết vẽ một chữ, nên đã bỏ ${p.key}`,
  },
  "cloze-drops": {
    en: (p) => `${q(p.col)}: the cloze column has to reach the card through {{cloze:}}, which ${p.key} would replace — ${p.key} removed`,
    vi: (p) => `${q(p.col)}: cột cloze phải lên card qua {{cloze:}}, mà ${p.key} sẽ thay mất — đã bỏ ${p.key}`,
  },
  "rtl-vertical": {
    en: (p) => `${q(p.col)}: rtl and vertical are two directions — keeping rtl`,
    vi: (p) => `${q(p.col)}: rtl và vertical là hai hướng viết khác nhau — giữ rtl`,
  },
  "embed-not-single": {
    en: (p) =>
      `row ${p.row}: ${q(p.col)}: ${q(p.url)} is a ${p.host} address with no video in it — ` +
      "a channel, a playlist or a folder cannot be embedded, only a single video or file",
    vi: (p) =>
      `dòng ${p.row}: ${q(p.col)}: ${q(p.url)} là link ${p.host} không trỏ tới video nào — ` +
      "kênh, playlist hay thư mục không nhúng được, chỉ một video hoặc một file",
  },
  "cloze-unmarked": {
    en: (p) =>
      `${p.count} row(s) contain {{c1::…}} but no column is marked \`cloze\` in the settings row ` +
      `(rows ${p.rows}) — the markup will show as text. Add \`cloze\` to the column holding the sentences.`,
    vi: (p) =>
      `${p.count} dòng có {{c1::…}} nhưng chưa cột nào ghi cloze trong settings row ` +
      `(dòng ${p.rows}) — phần đánh dấu sẽ hiện nguyên như chữ. Thêm cloze vào cột chứa câu.`,
  },
};

/**
 * One warning in `lang`: `{code, params, text}` as the analyzer hands it over.
 * A code this table does not know keeps the parser's own English sentence.
 */
export function warningText(warning, lang = "vi") {
  const say = WARNINGS[warning?.code]?.[lang] ?? WARNINGS[warning?.code]?.en;
  if (!say) return String(warning?.text ?? warning ?? "");
  try {
    return say(warning.params || {});
  } catch {
    return String(warning.text ?? "");
  }
}
