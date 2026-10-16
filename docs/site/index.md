# Bắt đầu

SheetCards biến bảng tính thành flashcard cho Anki. Bạn soạn card trong Google
Sheets, mỗi dòng một card, và SheetCards làm thành một deck. Bạn luôn sửa trên
sheet; Anki chỉ giữ một bản sao.

Chưa có Google Sheet? [Tạo Sheet](../sheet.html) cho bạn soạn cả sheet ngay
trên web, kể cả trên điện thoại, rồi chuyển thẳng sang Sheet to Anki.

Có hai cách đưa deck vào Anki:

- **Sheet to Anki**, ngay trên website này: dán link sheet, kiểm tra các card, tải
  file `.apkg` về rồi mở bằng Anki. Dùng được trên điện thoại hoặc máy tính,
  không cần cài add-on — chỉ cần app Anki để học.
- **Add-on**, trên máy tính: kết nối sheet một lần, từ đó về sau chỉ một phím tắt
  là sync mọi thay đổi.

Trang này đưa bạn từ một sheet trống tới những card có thể học ngay.

## Bạn cần gì

- **App Anki, để học.** SheetCards làm ra file `.apkg`; học và ôn bài diễn ra
  trong Anki. Cài một trong ba app:
  [AnkiDroid](https://play.google.com/store/apps/details?id=com.ichi2.anki)
  trên Android (miễn phí),
  [AnkiMobile](https://apps.apple.com/app/ankimobile-flashcards/id373493387)
  trên iPhone/iPad (**trả phí** một lần, 799.000đ ở Việt Nam vào tháng 10/2026), hoặc
  [Anki](https://apps.ankiweb.net/) trên máy tính (miễn phí). SheetCards thì
  miễn phí.
- **Một tài khoản Google**, chỉ khi bạn soạn trong Google Sheets. Soạn bằng
  [Tạo Sheet](../sheet.html) thì không cần gì cả. SheetCards đọc sheet mà không
  cần đăng nhập.
- Add-on chỉ dùng cho cách thứ hai và cần Anki 25.x trở lên trên máy tính.

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

### Sheet là bản gốc

Mọi thứ nằm trong sheet: card, cách trình bày, deck. SheetCards chỉ đọc nó. Một
file `.csv` cũng là một sheet, và đây là toàn bộ định dạng: dòng 1 là tên cột,
dòng 2 (không bắt buộc) là [settings row](settings-row.md) bắt đầu bằng
`#config`, mỗi dòng sau là một card.

```
ID,Word,Nghĩa
#config,size=40; tts=en_US,size=24
1,library,thư viện
2,airport,sân bay
```

Mở được bằng Google Sheets, Excel hay Tạo Sheet; mẫu nào trong Tạo Sheet
cũng có nút tải đúng file này về.

### Soạn trong Tạo Sheet: hai bước

Tạo Sheet chia sheet làm hai bước. **① Cột & card**: tên cột và settings row
(dòng 2 của sheet, mỗi ô ghi cột đó hiện thế nào trên card), có card xem trước
ngay bên cạnh. **② Thẻ**: thêm, sửa,
xoá từ. Chọn một template có sẵn (Học từ vựng, Từ vựng + ảnh, Hai chiều, Gõ đáp
án, mỗi theme một kiểu…) là vào thẳng bước 2; *Tùy chỉnh* bắt đầu từ bước 1.
Một sheet bạn đã có (`.xlsx` hoặc `.csv`) cũng lưu được làm template, ở mục
*Template của bạn*, chỉ trong trình duyệt này.

Bản nháp chỉ nằm trong trình duyệt (và Safari trên iPhone xoá nó sau 7 ngày
không mở trang), nên hãy lưu sheet:

- **Trên điện thoại: bấm Lưu link sheet.** Cả sheet nằm trong link đó. Giữ link
  này (gửi cho chính bạn qua Messenger/Telegram hoặc Ghi chú). Lần sau mở link
  → thêm từ → Tạo flashcard. Thêm từ rồi thì lưu link mới, vì link cũ mở bản cũ.
- **Trên máy tính: bấm Lưu file .csv.** Lần sau bấm **Mở file để thêm từ**.

ID của từ cũ giữ nguyên, nên import lại file `.apkg` sẽ cập nhật note và giữ
tiến độ ôn.

## 2. Chia sẻ sheet

Trong Google Sheets bấm **Share**, ở mục *General access* chọn **Anyone with the
link → Viewer**. Sau đó copy địa chỉ trên thanh địa chỉ của trình duyệt (link
bình thường kết thúc bằng `/edit…`).

SheetCards tải sheet mà không đăng nhập, nên sheet riêng tư sẽ không đọc được.
Quyền Viewer là đủ: không có gì được ghi ngược vào sheet của bạn.

## 3. Tạo flashcard

1. Dán link vào [Sheet to Anki](../create.html). Trang này chạy chính code của
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

## Tuần sau: thêm từ

1. Mở lại sheet: link sheet bạn đã lưu, file `.csv` (bằng **Mở file để thêm từ**
   trong Tạo Sheet — trên Android đừng chạm vào nó trong app Files, kẻo AnkiDroid
   import thẳng file CSV thành note rác), hoặc Google Sheet của bạn.
2. Thêm từ. Đừng đổi **Tên bộ flashcard**: đó là thứ giúp Anki nhận ra deck cũ.
3. Bấm **Tạo flashcard**, tải file `.apkg` mới và import. Card cũ được cập nhật,
   tiến độ ôn giữ nguyên, không nhân đôi.

Có trục trặc? Xem [FAQ: trên điện thoại](faq.md#tren-dien-thoai).

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
  nhiều thứ khác. [Tạo Sheet](../sheet.html) giúp bạn viết dòng này bằng cách
  bấm chọn.
- **Bắt đầu từ ví dụ.** [File ví dụ](examples.md) có 31 deck nhỏ, mỗi deck minh
  hoạ một tính năng.
- **Có gì không chạy?** Xem [FAQ và xử lý lỗi](faq.md).
