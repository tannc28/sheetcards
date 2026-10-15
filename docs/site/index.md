# Bắt đầu

SheetCards biến bảng tính thành flashcard cho Anki. Bạn soạn card trong Google
Sheets, mỗi dòng một card, và SheetCards làm thành một deck. Bạn luôn sửa trên
sheet; Anki chỉ giữ một bản sao.

Có hai cách đưa deck vào Anki:

- **Create deck**, ngay trên website này: dán link sheet, kiểm tra các card, tải
  file `.apkg` về rồi mở bằng Anki. Dùng được trên điện thoại hoặc máy tính,
  không cần cài gì.
- **Add-on**, trên máy tính: kết nối sheet một lần, từ đó về sau chỉ một phím tắt
  là sync mọi thay đổi.

Trang này đưa bạn từ một sheet trống tới những card có thể học ngay.

## Bạn cần gì

- **Một tài khoản Google**, chỉ để soạn sheet. SheetCards đọc sheet mà không cần
  đăng nhập.
- **Anki** ở đâu cũng được: AnkiDroid, AnkiMobile, hoặc Anki 25.x trở lên trên
  máy tính. Add-on chỉ dùng cho cách thứ hai và cần máy tính.

## 1. Tạo sheet

Mở một Google Sheet mới và gõ bảng sau, bắt đầu từ ô A1:

| ID | Word | Nghĩa |
| :--- | :--- | :--- |
| 1 | library | thư viện |
| 2 | airport | sân bay |
| 3 | season | mùa |

- **Dòng 1 là tên các cột.** `ID` là tên cột duy nhất bắt buộc.
- **`ID` là nhãn cố định của mỗi card.** Ghi gì cũng được (`1`, `w01`,
  `HSK-17`), miễn là không có hai dòng trùng nhau. Đừng bao giờ đổi hay dùng lại
  một ID: SheetCards dựa vào nó để biết card nào là card nào.
- **Các cột còn lại là của bạn.** `Word` và `Nghĩa` có thể đặt là `Từ` và
  `Ý nghĩa`, hay `汉字` và `拼音`. Mỗi cột thành một field cùng tên trong Anki.

Mặc định cột đầu tiên của bạn nằm ở mặt trước card, các cột còn lại ở mặt sau.
Vậy sheet này tạo ra card hỏi `library` và trả lời `thư viện`.

## 2. Chia sẻ sheet

Trong Google Sheets bấm **Share**, ở mục *General access* chọn **Anyone with the
link → Viewer**. Sau đó copy địa chỉ trên thanh địa chỉ của trình duyệt (link
bình thường kết thúc bằng `/edit…`).

SheetCards tải sheet mà không đăng nhập, nên sheet riêng tư sẽ không đọc được.
Quyền Viewer là đủ: không có gì được ghi ngược vào sheet của bạn.

## 3. Tạo deck

1. Dán link vào [Create deck](../preview.html). Trang này chạy chính code của
   add-on ngay trong trình duyệt, nên những gì bạn thấy cũng là những gì add-on
   sẽ làm ra.
2. Kiểm tra các card: các deck, từng dòng, và từng card hoàn chỉnh mà bạn có thể
   lật, nghe và gõ đáp án vào.
3. Bấm **Tải về cho Anki** để lấy file `.apkg`.
4. Mở file bằng Anki. Trên điện thoại, mở file bằng **AnkiDroid** hoặc
   **AnkiMobile**; trên máy tính, bấm đúp vào file hoặc dùng **File → Import…**.

Sau này import lại cùng sheet đó sẽ cập nhật các note chứ không nhân đôi, nhưng
không xoá được: dòng bạn bỏ khỏi sheet vẫn nằm trong Anki cho tới khi bạn tự xoá
nó ở đó. Xem chi tiết ở [Sheet, file và .apkg](sources.md).

## Hoặc: sync tự động từ máy tính

Add-on giữ deck luôn khớp với sheet, kể cả khi bạn xoá dòng, nên cả quy trình chỉ
còn là: sửa sheet rồi bấm một phím tắt.

### Cài add-on

1. Tải file
   [`sheetcards.ankiaddon`](https://github.com/tannc28/sheetcards/releases/latest/download/sheetcards.ankiaddon).
2. Trong Anki, mở **Tools → Add-ons**, bấm **Install from file…** rồi chọn file
   vừa tải.
3. Khởi động lại Anki.

Menu **SheetCards** sẽ xuất hiện trong **Tools**. Mọi chức năng của add-on đều
nằm trong menu đó.

### Kết nối sheet

Trong Anki chọn **Tools → SheetCards → Connect a Google Sheet…** rồi dán link.
Cửa sổ sẽ kiểm tra link khi bạn gõ và cho biết nó tìm thấy gì: bao nhiêu sheet,
bao nhiêu dòng, và tên các deck sẽ được tạo.

Bạn không cần đặt tên deck. Deck được đặt theo tên file và tên sheet, dạng
`sc_<tên file>::<tên sheet>`. Mỗi tab trong file thành một deck riêng (xem
[Sheet, file và .apkg](sources.md)).

### Sync

Chọn **Tools → SheetCards → Update Decks from Sheets…** (`Ctrl+Shift+S`), tick
vào deck của bạn rồi bấm **Update**. Xong là card đã sẵn sàng để học.

Từ giờ trở đi chỉ cần: sửa sheet, bấm `Ctrl+Shift+S`. Dòng mới thành card mới,
ô được sửa thì card được cập nhật (lịch sử review vẫn giữ nguyên), dòng bị xoá
thì card bị xoá theo. Xem chi tiết ở [Sync](syncing.md).

## Tiếp theo

- **Đổi giao diện card.** Thêm một [settings row](settings-row.md) ngay dưới
  dòng tên cột để chỉnh cỡ chữ, màu, cột nào ở mặt nào, âm thanh, hình ảnh và
  nhiều thứ khác. [Editor](../editor.html) giúp bạn viết dòng này.
- **Bắt đầu từ ví dụ.** [File ví dụ](examples.md) có 31 deck nhỏ, mỗi deck minh
  hoạ một tính năng.
- **Có gì không chạy?** Xem [FAQ và xử lý lỗi](faq.md).
