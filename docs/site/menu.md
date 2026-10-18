# Menu và phím tắt

Mọi thứ đều nằm trong **Tools → SheetCards** của Anki.

| Menu item | Phím tắt | Chức năng |
| :--- | :--- | :--- |
| Connect a Google Sheet… | không có | Thêm deck từ một link sheet |
| Update Decks from Sheets… | `Ctrl+Shift+S` | Sync các deck bạn tick |
| Disconnect a Sheet… | không có | Ngừng sync một deck, và có thể xoá nó |
| Card Layout… | `Ctrl+Shift+C` | Cho xem settings row của sheet nói gì |
| Settings… | `Ctrl+Shift+O` | Upload lên AnkiWeb và debug log |

Trên macOS, `Cmd` thay cho `Ctrl`. Connect và Disconnect không có phím tắt vì
Anki đã dùng `Ctrl+Shift+A` (Add-ons) và `Ctrl+Shift+D` (Set Due Date).

## Connect a Google Sheet…

Dán link tới một Google Sheet, hoặc tới một file `.xlsx`. Cửa sổ kiểm tra link
ngay sau khi bạn ngừng gõ, tải nó về và cho biết nó tìm thấy gì: các sheet, số
dòng của từng sheet, và các deck sẽ được tạo. Mỗi sheet có cột `ID` thành một
deck (file không sheet nào có cột `ID` thì mỗi sheet đều thành deck); xem [Sheet, file và .apkg](sources.md).

- Không có ô đặt tên: deck mang `name=` của sheet nếu có (đúng như bạn gõ), không
  thì được đặt theo tên file và tên sheet.
- Một sheet đã kết nối thì không thêm lần thứ hai được.
- Sheet phải được chia sẻ ở chế độ **Anyone with the link → Viewer**.

Khi chưa có sheet nào được kết nối, các cửa sổ khác cũng mở cửa sổ này cho bạn.

## Update Decks from Sheets…

Liệt kê mọi deck đã kết nối, mỗi deck một ô tick kèm số card. Các ô bạn tick
được nhớ cho lần sau. Bấm **Update** để sync; xem [Sync](syncing.md).

## Disconnect a Sheet…

Tick các deck muốn ngừng sync. Một ô tick quyết định chuyện gì xảy ra với chúng
trong Anki:

- **Để trống (mặc định):** deck, card và lịch sử review vẫn nằm nguyên trong
  Anki; chỉ có liên kết tới sheet bị gỡ.
- **Tick ô "Also delete the local decks, cards and note types":** deck cùng các
  subdeck, mọi card trong đó và các note type SheetCards của chúng đều bị xoá.

Bấm Enter ở hộp xác nhận sẽ huỷ chứ không xoá. Nếu lỡ xoá nhầm, **Edit → Undo**
của Anki và các bản backup tự động (**Preferences → Backups**) có thể khôi phục
collection, và sheet vẫn còn đó để sync lại. Riêng lịch sử review của các card
đã xoá thì không lấy lại từ sheet được.

## Card Layout…

Một cửa sổ chỉ để xem, cho biết với từng deck, add-on đã hiểu gì từ
[settings row](settings-row.md) của sheet:

- **What the add-on understood**: cột nào ở mặt trước, cột nào ở mặt sau, cột
  nào bị ẩn, và setting của từng cột đúng như add-on đọc được.
- **Warnings**: mọi thứ nó không hiểu, theo từng cột.
- **Preview**: thiết kế card mà nó dựng ra, với nội dung mẫu.

Cửa sổ hiện kết quả của **lần sync gần nhất**, nên sau khi sửa sheet hãy bấm
`Ctrl+Shift+S` trước. Nó cố ý không có nút chỉnh sửa: giao diện card được đổi
trong sheet, nên chỉ có đúng một chỗ để đổi.

## Settings…

Cũng mở được bằng nút **Config** của SheetCards trong **Tools → Add-ons**.

- **Upload to AnkiWeb** (mục *After a sync*). Bật sẵn. Sau khi sync xong, Anki tự chạy
  sync của chính nó, nên card mới lên điện thoại mà không cần bấm thêm. Bạn cần
  đăng nhập AnkiWeb một lần qua **Tools → Sync**.
- **Write a debug log.** Tắt sẵn. Ghi lại từng bước của một lần sync vào
  `debug_sheetcards.log` trong thư mục của add-on; cửa sổ hiện đường dẫn và mở
  thư mục đó cho bạn. Ô thứ hai, **Keep the logs from earlier syncs** (bật
  sẵn), giữ log của các lần sync trước; bỏ tick thì mỗi lần sync bắt đầu một log
  mới. Hãy bật nó trước khi làm lại một lỗi. Log có chứa nội dung
  sheet của bạn, nên đọc qua trước khi chia sẻ công khai.

Thay đổi được lưu khi bạn bấm **Save**.
