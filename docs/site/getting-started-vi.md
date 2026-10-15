# Bắt đầu

SheetCards là một add-on cho Anki, biến bảng tính thành flashcard. Bạn soạn thẻ
trong Google Sheets, mỗi dòng là một thẻ, và add-on đưa chúng vào Anki. Khi bạn
sửa sheet, chỉ cần một cú bấm là thẻ được cập nhật. Bạn luôn sửa trên sheet; Anki
chỉ giữ một bản sao.

Trang này đưa bạn từ một sheet trống tới những thẻ có thể học ngay, qua năm bước.
Các trang tài liệu khác hiện chỉ có tiếng Anh.
*Read in English: [Getting started](index.md).*

## Bạn cần gì

- **Anki 25.x trở lên** trên máy tính (Windows, macOS hoặc Linux).
- **Một tài khoản Google**, chỉ để soạn sheet. Add-on đọc sheet mà không cần đăng
  nhập.

## Cài add-on

1. Tải file
   [`sheetcards.ankiaddon`](https://github.com/tannc28/sheetcards/releases/latest/download/sheetcards.ankiaddon).
2. Trong Anki, mở **Tools → Add-ons**, bấm **Install from file…** rồi chọn file
   vừa tải.
3. Khởi động lại Anki.

Menu **SheetCards** sẽ xuất hiện trong **Tools**. Mọi chức năng của add-on đều
nằm trong menu đó.

## 1. Tạo sheet

Mở một Google Sheet mới và gõ bảng sau, bắt đầu từ ô A1:

| ID | Word | Nghĩa |
| :--- | :--- | :--- |
| 1 | library | thư viện |
| 2 | airport | sân bay |
| 3 | season | mùa |

- **Dòng 1 là tên các cột.** `ID` là tên cột duy nhất bắt buộc.
- **`ID` là nhãn cố định của mỗi thẻ.** Ghi gì cũng được (`1`, `w01`, `HSK-17`),
  miễn là không có hai dòng trùng nhau. Đừng bao giờ đổi hay dùng lại một ID:
  add-on dựa vào nó để biết thẻ nào là thẻ nào.
- **Các cột còn lại là của bạn.** `Word` và `Nghĩa` có thể đặt là `Từ` và
  `Ý nghĩa`, hay `汉字` và `拼音`. Mỗi cột thành một field cùng tên trong Anki.

Mặc định cột đầu tiên của bạn nằm ở mặt trước thẻ, các cột còn lại ở mặt sau.
Vậy sheet này tạo ra thẻ hỏi `library` và trả lời `thư viện`.

## 2. Chia sẻ sheet

Trong Google Sheets bấm **Share**, ở mục *General access* chọn **Anyone with the
link → Viewer**. Sau đó copy địa chỉ trên thanh địa chỉ của trình duyệt (link
bình thường kết thúc bằng `/edit…`).

Add-on tải sheet mà không đăng nhập, nên sheet riêng tư sẽ không đọc được. Quyền
Viewer là đủ: add-on không bao giờ ghi gì vào sheet của bạn.

## 3. Kiểm tra bằng trang xem trước (không bắt buộc)

Dán link vào [trang xem trước](../preview.html). Trang này chạy chính code của
add-on ngay trong trình duyệt và cho bạn xem các deck, từng dòng và thẻ hoàn
chỉnh, không cần cài gì. Nếu trang xem trước đọc được sheet thì Anki cũng đọc
được.

## 4. Kết nối

Trong Anki chọn **Tools → SheetCards → Connect a Google Sheet…** rồi dán link.
Cửa sổ sẽ kiểm tra link khi bạn gõ và cho biết nó tìm thấy gì: bao nhiêu sheet,
bao nhiêu dòng, và tên các deck sẽ được tạo.

Bạn không cần đặt tên deck. Deck được đặt theo tên file và tên sheet, dạng
`sc_<tên file>::<tên sheet>`. Mỗi tab trong file thành một deck riêng.

## 5. Đồng bộ

Chọn **Tools → SheetCards → Update Decks from Sheets…** (`Ctrl+Shift+S`), tick
vào deck của bạn rồi bấm **Update**. Xong là thẻ đã sẵn sàng để học.

Từ giờ trở đi chỉ cần: sửa sheet, bấm `Ctrl+Shift+S`. Dòng mới thành thẻ mới, ô
được sửa thì thẻ được cập nhật (lịch sử ôn tập vẫn giữ nguyên), dòng bị xoá thì
thẻ bị xoá theo.

## Tiếp theo

- **Đổi giao diện thẻ.** Thêm một [settings row](settings-row.md) ngay dưới dòng
  tên cột để chỉnh cỡ chữ, màu, cột nào ở mặt nào, âm thanh, hình ảnh và nhiều
  thứ khác. [Trình soạn](../editor.html) giúp bạn viết dòng này.
- **Bắt đầu từ ví dụ.** [Bộ ví dụ](examples.md) có 31 deck nhỏ, mỗi deck minh
  hoạ một tính năng.
- **Có gì không chạy?** Xem [Câu hỏi thường gặp](faq.md) (tiếng Anh).
