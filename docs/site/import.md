# Chuyển từ Quizlet, Noji, Anki

Đã có từ vựng ở nơi khác? Đưa chúng vào Sheet to Anki mà không phải gõ lại.
Mọi thứ đều được đọc ngay trong trình duyệt, không gửi lên đâu cả.

## Dán văn bản

Trong Sheet to Anki, bấm **Dán văn bản**, đặt **Tên bộ flashcard**, rồi dán
danh sách vào ô. Mỗi dòng một card, ví dụ:

```
apple - quả táo
book - quyển sách
journey - chuyến đi
```

- **Dấu tách được tự nhận**: tab, ` - `, `=`, `|`, `;`, `:`, `,`, `>>`. Nếu đoán
  sai, chọn lại ở ô *Giữa mặt trước và mặt sau*.
- Dòng có hơn hai phần thì các phần sau thành thêm cột ở mặt sau.
- Dòng trùng được đánh dấu và bỏ ra; tick lại nếu bạn muốn giữ.
- Card được tạo thành một sheet Basic với hai cột **Mặt trước** / **Mặt sau** và
  `#config name=<tên>`. Link của trang chứa cả sheet, nên tải lại trang hay gửi
  link cho người khác đều mở lại đúng bộ này.
- **Tuần sau dán danh sách dài hơn với cùng tên**: mỗi card được nhận theo chữ ở
  mặt trước, nên import file `.apkg` mới sẽ cập nhật card cũ (giữ tiến độ ôn) và
  thêm card mới. Sửa chính tả mặt trước thì thành một card mới.
- **Mở trong Tạo Sheet** đưa danh sách sang Tạo Sheet để thêm cột (phiên âm, ví
  dụ, ảnh…).

### Một sheet CSV do trợ lý AI viết

Nếu bạn nhờ ChatGPT, Gemini hay Claude soạn sheet, chúng thường trả lời bằng
một khối CSV. Dán nguyên câu trả lời vào **Dán văn bản**: khối ` ```csv ` được
lấy ra, và nếu dòng đầu có cột `ID` hoặc dòng thứ hai là `#config`, sheet được
mở nguyên như vậy, với các cột và settings row của nó.

## Quizlet

Trong Quizlet, mở học phần → **⋯** → **Export** → **Copy text**, rồi dán vào
**Dán văn bản**.

- Mặc định Quizlet dùng tab giữa thuật ngữ và định nghĩa, xuống dòng giữa các
  card. Cả hai đều được tự nhận.
- Nếu bạn chọn dấu khác ở *Between rows* (ví dụ `;` hay một dấu tự đặt), cả
  học phần nằm trên một dòng; dấu lặp lại đó được nhận ra và có sẵn trong ô
  *Giữa các card*.
- Quizlet không cho export học phần bạn copy từ người khác.

## Noji, Brainscape và các file CSV khác

Noji (trước đây là Anki Pro) export deck thành file CSV, chỉ có chữ. Mở file
bằng **Mở file** trong Sheet to Anki hoặc Tạo Sheet; file `.txt` cũng được.

- **File không có dòng tên cột** (chỉ có thuật ngữ, định nghĩa) vẫn đọc đúng:
  nếu dòng đầu trông giống các dòng bên dưới thì nó được đọc như một card, và các
  cột được đặt tên **Mặt trước** / **Mặt sau**. Nếu đoán sai, bấm *Dòng đầu là
  tên cột* (hoặc *Dòng đầu là một card*) ở dòng thông báo.
- Dòng đầu có `ID`, `TAGS`, hoặc tên cột quen thuộc (Front, Back,
  Term, Definition, Mặt trước, Nghĩa…) thì luôn được đọc là tên cột.

## Deck chia sẻ của Anki (.apkg)

Một deck tải từ AnkiWeb Shared Decks, hay một file `.apkg`/`.colpkg` xuất từ Anki,
mở được bằng **Mở file** để thành sheet bạn sửa được rồi tạo lại `.apkg`.

- **Mỗi note type thành một sheet**: các field là các cột, guid của note thành
  cột `ID`, deck con thành các cột `Deck 1`, `Deck 2`… (ghi `subdeck=1`, `subdeck=2`…
  ở settings row), tag thành `TAGS`. Settings
  row ghi lại field nào ở mặt trước, field cloze, ô gõ đáp án và card ngược.
- **Định dạng**: giữ in đậm, in nghiêng, gạch dưới, chỉ số trên/dưới và xuống
  dòng; các thẻ HTML khác bị bỏ, chỉ giữ chữ.
- **Ảnh và âm thanh không chuyển được**: chúng là file nằm trong deck, còn sheet
  chỉ link được tới web. Trang sẽ báo số ảnh/âm thanh đã bị bỏ. Thêm lại bằng cột
  `image` / `audio` với link (xem [Hình ảnh, âm thanh và video](media.md)).
- Deck tạo từ sheet là **deck mới** trong Anki, không cập nhật note của deck gốc:
  hai bên khác guid.
- **Deck xuất bằng Anki mới**: từ Anki 2.1.50, file `.apkg` mặc định dùng định
  dạng nén mà trình duyệt không đọc được. Trang sẽ nói: *Deck này xuất bằng Anki
  mới*. Trong Anki chọn **File → Export → Anki Deck Package** và tick **Support
  older Anki versions**, rồi mở file mới.
