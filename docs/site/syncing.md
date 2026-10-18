# Sync

Mỗi lần bạn chọn **Update Decks from Sheets…** (`Ctrl+Shift+S`), add-on tải về
từng sheet bạn đã tick và làm cho Anki khớp với nó. Add-on không bao giờ ghi gì
ngược lại vào sheet.

## Note được nhận ra nhờ `ID`

`ID` của mỗi dòng được lưu trong field đầu tiên của note, cũng tên là `ID`. Mỗi
lần sync, add-on đọc field đó để ghép dòng với note. Vì vậy:

- **Đừng bao giờ đổi ID.** Đổi ID trông như xoá một dòng và thêm một dòng mới:
  note cũ bị xoá và một note mới được tạo, mất luôn lịch sử review.
- **Đừng dùng lại ID.** Hai dòng cùng ID thành một note. Sync báo trùng lặp như
  một lỗi: *"Duplicate IDs in the spreadsheet"*.
- **Dòng có `ID` trống không bao giờ được sync.** Sheet không có cột `ID` thì chữ
  ở cột đầu tiên làm ID, nên sửa chính tả chữ đó là một note mới (xem
  [Các cột](columns.md#sheet-khong-co-cot-id)).
- **Để note nằm yên trong deck của nó.** Note bị chuyển ra khỏi deck của sheet
  trong Anki sẽ không còn được tìm thấy, và lần sync sau sẽ tạo lại nó.

## Mỗi thay đổi dẫn tới gì

| Bạn làm điều này trong sheet | Sync sẽ làm điều này |
| :--- | :--- |
| Thêm một dòng | Tạo một note |
| Sửa một ô | Cập nhật field đó; note giữ nguyên lịch sử review |
| Đổi một ô của cột `subdeck=` | Chuyển card của note sang subdeck mới và cập nhật tag |
| Đặt `SYNC` thành bất cứ gì khác yes | **Giữ nguyên note** và ngừng cập nhật nó. Note không bị xoá |
| Đặt `SYNC` lại thành yes | Cập nhật note đó trở lại |
| Xoá một dòng | **Xoá note** |
| Thêm một cột | Thêm một field cùng tên và đặt nó ở mặt sau card |
| Bỏ một cột | **Giữ field và nội dung của nó trong Anki** và thôi hiện nó |
| Đổi tên một cột | Tính như bỏ một cột và thêm một cột khác: một field trống mới xuất hiện, field cũ vẫn giữ nội dung |
| Sửa [settings row](settings-row.md) | Dựng lại thiết kế card. Note và lịch sử review không bị đụng tới |

## Quy tắc an toàn

- **Không có dòng hợp lệ thì không xoá gì.** Nếu bản tải về không có dòng nào có
  `ID` (sheet trống, nhầm tab, export bị lỗi), mọi note sẽ trông như đã bị xoá.
  Add-on không xoá gì cả và báo rõ: *"Sync safety: the spreadsheet returned no
  valid rows…"*.
- **Đổi note type không bao giờ làm mất note.** Khi một sheet trở thành sheet
  cloze, hoặc thôi là sheet cloze, mỗi note phải được tạo lại theo note type kia.
  Note mới được tạo trước khi note cũ bị xoá. Lịch sử review của nó bắt đầu lại
  từ đầu; Anki không đổi được note type của một note tại chỗ.
- **Bỏ một cột không bao giờ xoá những gì bạn đã thu thập** trong cột đó.

## Tên lấy từ sheet

Deck được đặt theo tên file spreadsheet và tên sheet: `sc_<file>::<sheet>`, còn
note type là `SheetCards - <deck> - Basic` và `- Cloze`. Khi bạn đổi tên file
spreadsheet, lần sync sau sẽ đổi tên deck và note type cho khớp.

Khi sheet có `name=` trong [settings row](settings-row.md), add-on dùng đúng tên đó
làm tên deck, không có tiền tố `sc_`, giống file `.apkg` của Sheet to Anki. **Muốn add-on và file `.apkg`
là cùng một deck (ví dụ học trên điện thoại bằng `.apkg`, sync trên máy tính bằng
add-on): đặt `name=` trong settings row.** Khi đó hai cách nhận ra cùng các note,
không nhân đôi. Sheet không có `name=` mà là sheet duy nhất của file thì deck mang
tên `sc_<file>`; các deck add-on đã kết nối từ trước vẫn giữ tên `sc_<file>::<sheet>`.

**Đổi tên deck hay note type của SheetCards ngay trong Anki sẽ không giữ được**:
lần sync sau sẽ đổi lại. Hãy đổi tên spreadsheet thay vào đó.

Sửa front template hay back template của một note type SheetCards trong Anki
cũng không giữ được: nó được dựng lại từ sheet mỗi lần sync. Phần Styling thì có
thể chứa CSS của riêng bạn; xem [settings row](settings-row.md#dinh-dang-mot-cot-bang-css).

## Khi sync xong

- Subdeck không còn card nào sẽ bị xoá.
- Mọi deck đã kết nối dùng chung một preset của Anki, **SheetCards - Default
  Options**, được tạo nếu chưa có. Preset mới bắt đầu với 20 card mới và 200
  card review mỗi ngày. Hãy đổi nó trong deck options của Anki; add-on không bao
  giờ ghi đè một preset đã có.
- Một lần sync suôn sẻ kết thúc bằng một thông báo ngắn. Nếu có gì cần bạn để
  ý, một cửa sổ tóm tắt sẽ mở ra với ba chế độ xem (*Summary*, *Full details*,
  *Errors only*) và các con số: số dòng trong sheet, số dòng có ID, số dòng bị
  bỏ qua vì thiếu ID, số dòng trống bị bỏ qua, số dòng được tick và không được
  tick ở `SYNC`, và số note được tạo, cập nhật, xoá và giữ nguyên.
- Nếu **Upload to AnkiWeb** đang bật trong Settings, sync của chính Anki sẽ chạy
  tiếp theo, nên card mới lên được điện thoại của bạn.

Một deck bị lỗi không làm dừng các deck khác; lỗi của nó hiện trong bản tóm tắt.
Sync chạy ở chế độ nền, và **Cancel** sẽ dừng sau deck đang chạy.

## Setting được lưu ở đâu

| Cái gì | Ở đâu | Có theo sang thiết bị khác không? |
| :--- | :--- | :--- |
| Thiết kế card đọc từ settings row | Collection của Anki | **Có**, qua AnkiWeb |
| Note type, note và card | Collection của Anki | **Có** |
| Những sheet nào đã kết nối, setting AnkiWeb và debug | `meta.json` trong thư mục của add-on | Không, chỉ máy này |

Settings row được chép vào collection để máy tính thứ hai hiện đúng các card đó
trước cả khi nó tự tải sheet về. Sheet vẫn là nguồn gốc: lần sync sau sẽ ghi đè
bản chép đó.
