# Sheet, file và .apkg

Card của bạn có thể nằm ở đâu, và có những cách nào để chúng vào Anki.

## Một file, mỗi sheet một deck

Một file Google Sheets chứa nhiều sheet, tức các tab ở phía dưới. SheetCards kết
nối **mỗi sheet thành một deck riêng**, tên là `sc_<file>::<sheet>`, với cột,
settings row và note type của riêng nó. Chỉ cần dán link của file một lần là một
spreadsheet có thể chứa cả collection của bạn. Sau đó `Ctrl+Shift+S` liệt kê mỗi
sheet một dòng, để bạn chọn sheet nào cần cập nhật.

- **Sheet không có cột `ID` sẽ bị bỏ qua**, và cửa sổ cho biết là sheet nào. Ghi
  chép, bảng chú thích màu hay bản nháp có thể nằm chung file. Sheet bị ẩn cũng
  bị bỏ qua.
- **Deck nhớ sheet của nó theo tên.** Chuyển sheet sang vị trí khác thì deck vẫn
  theo được. **Đổi tên sheet thì deck không tìm thấy nó nữa**: sync sẽ báo và
  liệt kê các tên đang có. Kết nối lại file để nhận tên mới.

## File .xlsx thay cho Google Sheet

Link tới một file `.xlsx` hoặc `.xlsm` cũng dùng được, đọc theo cùng một cách,
mỗi sheet một deck. File nằm trong một repository GitHub cũng được: dán địa chỉ
`…/blob/main/decks.xlsx` mà trình duyệt hiện, add-on sẽ tải file phía sau nó.

- **File phải được upload lại thì sync mới thấy thay đổi.** Với deck bạn sửa
  thường xuyên, Google Sheets là chỗ hợp hơn.
- **Địa chỉ phải công khai và bắt đầu bằng `https`.** Add-on từ chối các loại
  địa chỉ khác, và mọi địa chỉ trong mạng nội bộ.

## Create deck

[Create deck](../preview.html) tạo deck Anki từ sheet ngay trên điện thoại hoặc
máy tính, không cần cài add-on. Trước khi tải về, nó cho bạn thấy SheetCards làm
ra gì từ sheet: từng dòng và việc nó có được sync hay không, cây deck, tag, cảnh
báo từ settings row, và từng card hoàn chỉnh, mà bạn có thể lật, nghe và gõ đáp
án vào. Nó chạy chính code của add-on trong trình duyệt, nên những gì nó hiện ra
được làm đúng như cách sync làm. Chỉ có bước cuối cùng, vẽ card, là trang tự mô
phỏng lại Anki; còn nội dung template nó hiện ra là chính xác.

Sau khi sửa sheet, bấm nút tải lại cạnh tên sheet, Create deck sẽ tải sheet lại và
giữ nguyên chỗ bạn đang xem.

### Upload một file

Bấm **Tải lên một file**, hoặc kéo một file vào trang, để mở một file `.xlsx`,
`.xlsm`, `.csv` hoặc `.tsv` trên máy bạn. Mỗi tab của workbook thành một deck
riêng. File không bao giờ rời khỏi trình duyệt của bạn.

- **Bản thân add-on vẫn cần một link.** File đã upload đến được Anki qua bản tải
  `.apkg` bên dưới.
- **Ô được đọc đúng như sheet hiện.** Ngày ra dạng `2025-01-21`, số nguyên ra
  `1` chứ không phải `1.0`.

### Tải về một file .apkg

Nút **Tải về cho Anki** dựng deck thành một file `.apkg`. **AnkiDroid và AnkiMobile
import thẳng được file này**, nên sheet có thể lên điện thoại mà không cần Anki
trên máy tính. File được dựng bằng chính code của add-on, với cùng field và
thiết kế card, và danh tính của note lấy từ cột `ID` của bạn, nên **import lại sẽ
cập nhật các note đó chứ không nhân đôi**.

Điều import không làm được là **xoá**: Anki không bao giờ xoá một note không có
trong file. Dòng bạn xoá khỏi sheet vẫn nằm trong collection cho tới khi bạn xoá
nó ở đó. Đó chính là khác biệt thật sự giữa import và sync.

## Editor

[Editor](../editor.html) là một spreadsheet nhỏ để viết
[settings row](settings-row.md). Bạn chọn setting từ một danh sách thay vì phải
nhớ, và deck cùng card cập nhật ngay bên cạnh khi bạn gõ. Khi đã ưng ý, copy dòng
1 và 2 rồi dán vào ô A1 của sheet.
