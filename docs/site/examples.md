# File ví dụ

Mỗi tính năng đều có một ví dụ chạy được, và tất cả nằm trong một file ba mươi
mốt sheet, xếp từ đơn giản tới nâng cao. Mỗi sheet là một deck học được và minh
hoạ một tính năng.

```text
https://github.com/tannc28/sheetcards/blob/main/examples/sheetcards-examples.xlsx
```

- **Xem trong [Sheet to Anki](../create/#example)**: dán link trên, hoặc
  [tải file về](../sheetcards-examples.xlsx) rồi upload. Chọn sheet ở thanh phía
  trên, xem card, rồi Download `.apkg`.
- **Lấy một sheet làm điểm xuất phát trong [Tạo Sheet](../sheet/)**: tải file
  về, bấm **Mở file để thêm từ** rồi chọn sheet. Chỉ muốn giữ cột và settings
  row thì upload file vào **Template của bạn**.
- **Với add-on**: dán link vào **Tools → SheetCards → Connect a Google Sheet…**;
  mỗi sheet trong file thành một deck.

Sheet không có `name=` thành deck mang tên file và tên sheet, ví dụ
`sheetcards-examples::05 Type the answer (gõ đáp án)`. Sheet 16 có `name=`, nên
deck của nó mang đúng tên đó, cả từ `.apkg` lẫn từ add-on.

Phần lớn là tiếng Anh cho người Việt; tiếng Trung, Nhật, Hàn và các thứ tiếng
khác xuất hiện ở những tính năng dành cho chúng. Không có gì trong SheetCards gắn
với riêng một ngôn ngữ: một deck giải phẫu học cũng chạy y như vậy. Cách nhanh
nhất để học một tính năng là tìm sheet dùng nó trong bảng dưới và copy settings
row của nó.

| Sheet | Nội dung minh hoạ |
| :--- | :--- |
| `01 Basic (cơ bản)` | `ID`, `Front`, `Back` — mỗi thứ tiếng một từ: Anh, Trung, Nhật, Hàn, Đức và Tây Ban Nha, trả lời bằng tiếng Việt. Không có settings row, không có `SYNC` |
| `02 Sync & subdecks (deck con)` | bật/tắt dòng bằng `SYNC`, `SUBDECK 1`/`2` (dòng không ghi tầng nào vào `Unsorted`), `TAGS` |
| `03 Card layout (bố cục thẻ)` | `side`, `size`, cả ba dạng màu, `bold`, `italic`, `label`, `hint`, `side=hide`, `align` cho cả deck |
| `04 Reverse (thẻ ngược)` | một dòng, hai card |
| `05 Type the answer (gõ đáp án)` | `type=nc`, nên không phải gõ dấu tiếng Việt |
| `06 Cloze (điền chỗ trống)` | một cột `cloze` được khai báo, có cả một dòng với hai chỗ trống |
| `07 Images (hình ảnh)` | `image` ở mặt hỏi, kèm `size` — ảnh hỏi và từ tiếng Trung trả lời |
| `08 Audio (âm thanh)` | `audio`, nghe rồi nhớ lại: một từ tiếng Anh do người thật đọc, không phải giọng máy |
| `09 Video (video nhúng)` | mọi dạng link YouTube được chuyển thành trình phát, cộng một file trực tiếp |
| `10 Speech (đọc thành tiếng)` | `tts=en_US`, ưu tiên giọng bằng `voices=`, `speed` cho cả deck, và một cột ẩn đọc lại câu với nửa tốc độ |
| `11 Chinese writing (gõ chữ)` | viết chữ, rồi đối chiếu với hoạt hình thứ tự nét — `type` + `image` + `hint` + `tts` trên một card, và `subdeck=1` xếp theo cấp HSK |
| `12 Chinese drawing (viết tay)` | `draw` — bạn viết chữ từng nét và mỗi nét đều được chấm |
| `13 Furigana (phiên âm kanji)` | `furigana` trên chữ kanji |
| `14 Any headers (mọi ngôn ngữ)` | tên cột viết là `汉字`, `拼音`, `释义`, `例句` |
| `15 Theme + subdeck (màu, tầng)` | từ vựng tiếng Anh xếp sâu ba tầng `SUBDECK` — `English::B1::Verbs` — với `theme=sakura`, có đọc to, và sắp xếp theo từ |
| `16 Picture words (từ vựng ảnh)` | ảnh ở mặt trước và giọng người bản xứ ở mặt sau — `image` và `audio` trên một card, xếp theo `Group`; ô `#config` có `name=` (tên bộ flashcard, cũng là danh tính của deck) và `next=` |
| `17 Draw & type (viết và gõ)` | viết chữ từng nét *và* gõ pinyin của nó: `draw` và `type=nc` hỏi cùng một thứ theo hai cách |
| `18 Grammar cloze (ngữ pháp)` | giấu từ mang điểm ngữ pháp, và gõ ra chứ không chỉ nhớ — `cloze` cộng `type` |
| `19 Dictation (nghe rồi gõ)` | câu được đọc lên mà không hiện ở đâu: `side=hide` + `tts` + `type`, nên cách duy nhất là nghe |
| `20 Video lesson (bài video)` | đoạn clip *chính là* câu hỏi — `video` ở mặt trước, xếp theo bài |
| `21 Formulas & code (công thức)` | `math` cho công thức và `code=python` cho code — hai loại ô không phải văn xuôi, cộng thêm `sort` |
| `22 Arabic (phải sang trái)` | `rtl`, hướng viết của tiếng Ả Rập, Do Thái và Ba Tư |
| `23 Vertical text (viết dọc)` | `vertical` — từ trên xuống, phải sang trái, như tiếng Nhật in trong sách |
| `24 Korean (tiếng Hàn)` | `font=kr` và một giọng tiếng Hàn — một hệ chữ có font riêng |
| `25 Traditional (chữ phồn thể)` | cùng một từ bằng `font=tc` và `font=sc` cạnh nhau, đọc bằng `zh_TW` |
| `26 Shell commands (dòng lệnh)` | `code=bash` — đáp án là một câu lệnh, xếp theo công dụng |
| `27 Web dev (HTML & JS)` | hai cột code trên một card, `code=html` và `code=javascript` |
| `28 Chemistry (hoá học)` | phương trình `math=block` dưới một đáp án bằng lời thường |
| `29 Phrasal verbs (cụm động từ)` | `cloze` trên tiểu từ khó tra nhất, và câu được đọc to |
| `30 German (tiếng Đức)` | hỏi der/die/das ở mặt trước, `tts=de_DE` trên danh từ và câu ví dụ |
| `31 Spanish (tiếng Tây Ban Nha)` | lại là `type=nc`, lần này dấu là của tiếng Tây Ban Nha và `ñ` vẫn phải gõ |

File này được sinh ra từ `SHEETS` trong
[`scripts/build_examples.py`](https://github.com/tannc28/sheetcards/blob/main/scripts/build_examples.py),
và bộ test sẽ fail nếu có setting nào không có ví dụ trong đó.
[`examples/README.md`](https://github.com/tannc28/sheetcards/blob/main/examples/README.md)
nói thêm về từng sheet và cách sửa file.
