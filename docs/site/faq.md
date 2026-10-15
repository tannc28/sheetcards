# FAQ và xử lý lỗi

## Các thông báo thường gặp

Các thông báo dưới đây được giữ nguyên tiếng Anh, đúng như add-on hiện ra.

**"This sheet isn't shared."**
Sheet đang ở chế độ riêng tư. Trong Google Sheets: **Share → General access →
Anyone with the link → Viewer**.

**"This file isn't public."**
Link `.xlsx` đòi đăng nhập. Hãy chắc rằng ai có link cũng mở được.

**"There's no sheet at this address."**
Link bị gõ sai, hoặc file đã bị xoá.

**"Can't reach Google."**
Không có mạng, hoặc không kết nối được tới Google. Thử lại.

**"URL must be a Google Sheets edit URL…"**
Dán link từ thanh địa chỉ của trình duyệt, link có dạng
`https://docs.google.com/spreadsheets/d/…/edit…`.

**"Refusing to download over 'http'…" / "…inside a private network"**
Địa chỉ phải là địa chỉ công khai và bắt đầu bằng `https`. Xem
[Sheet, file và .apkg](sources.md#file-xlsx-thay-cho-google-sheet).

**"Mandatory header missing: 'ID'"**
Dòng 1 không có cột `ID`. Chỉ dòng 1 được đọc làm tên cột, nên một dòng tiêu đề
nằm phía trên nó sẽ gây ra lỗi này.

**"The sheet has no content columns"**
Sheet chỉ có các cột `ID`, `SYNC`, `TAGS` hoặc `SUBDECK`. Thêm ít nhất một cột
của riêng bạn.

**"Duplicate IDs in the spreadsheet"**
Hai dòng trở lên dùng chung một `ID`, và chỉ một trong số đó vào được Anki. Hãy
cho mỗi dòng một ID riêng.

**"Sync safety: the spreadsheet returned no valid rows…"**
Không có gì bị xoá, và đó là cố ý. Kiểm tra dòng 1 có chứa tên cột và cột `ID`
đã được điền, rồi sync lại.

**"AnkiWeb not configured - access Tools > Sync in Anki"**
Đăng nhập AnkiWeb một lần qua **Tools → Sync** của chính Anki; add-on dùng phiên
đăng nhập đó.

## Card và setting

**Tôi đã sửa settings row mà không thấy gì thay đổi.**
Settings row được đọc trong lúc sync, nên hãy bấm `Ctrl+Shift+S` trước. Sau đó
mở **Card Layout…** (`Ctrl+Shift+C`) và xem phần **Warnings**: key gõ sai
(`siz=48`) hay giá trị nằm ngoài khoảng cho phép sẽ được báo ở đó thay vì được
áp dụng.

**Một dòng toàn chữ `key=value` lại thành card, hoặc card đầu tiên của tôi bị mất.**
Settings row chỉ được nhận ra khi ô `ID` của nó bắt đầu bằng `#config`. Ghi
`#config` một mình, hoặc `#config` rồi một dấu cách và các setting cho cả sheet.
Ngược lại, dòng nào có `ID` tình cờ bắt đầu bằng `#config` sẽ bị coi là settings
và không bao giờ thành card.

**Text to speech không phát ra tiếng.**
Kiểm tra lần lượt: mã ngôn ngữ đầy đủ (`zh_CN`, không phải `zh`); thiết bị đã cài
giọng cho ngôn ngữ đó (mở mục **TTS voices** ở mặt sau card để xem máy có gì); ô
không bị trống. Xem [Text to speech](tts.md).

**Một phần của card bị đọc sai ngôn ngữ.**
Anki đọc cả field bằng một giọng. Hãy để mỗi ngôn ngữ một cột, với `tts=` riêng.

**`furigana` không in gì phía trên chữ.**
Ô phải được viết dạng `推迟[tuī chí]`: chữ, rồi cách đọc trong ngoặc vuông.

**`reverse` không có tác dụng ở một số sheet.**
Sheet cloze không có reverse card được.

**Câu hỏi của card cloze bị trống, còn `{{c1::…}}` bị in ra ở mặt sau.**
Sheet chưa nói cột nào chứa phần cần che. Thêm `cloze` vào cột đó trong settings
row. Xem [Các loại card](card-types.md#cloze).

**Hình ảnh không hiện.**
Hình dán thẳng vào ô không phải là link mà Anki lấy được. Hãy tải hình lên chỗ
nào có link, đặt link vào ô và đánh dấu cột là `image`. Khi đó card cần có mạng
để hiện hình. Xem [Hình ảnh, âm thanh và video](media.md).

**Video hiện lỗi.**
Link trỏ tới một channel, playlist hoặc thư mục thay vì một video, hoặc video
không cho phép nhúng. Phần cảnh báo trong Create deck sẽ cho biết là trường hợp nào.

## Deck

**Tôi đổi tên deck rồi mà Anki lại đổi về tên cũ.**
Đó là bình thường: tên lấy từ sheet. Hãy đổi tên file spreadsheet thay vì đổi
tên deck. Xem [Sync](syncing.md#ten-lay-tu-sheet).

**Tôi đổi tên một tab sheet và deck của nó không còn cập nhật nữa.**
Deck nhớ sheet của nó theo tên. Hãy kết nối lại file để add-on nhận tên mới.

**Tôi đã xoá một dòng mà card vẫn còn trong Anki.**
Nếu bạn import file `.apkg` từ Create deck thì import vốn hoạt động như vậy: nó cập
nhật và thêm mới nhưng không bao giờ xoá. Sync bằng add-on thì có xoá.

**Tôi đặt `SYNC` là no mà card không bị xoá.**
Đó là cố ý: dòng không được tick sẽ được giữ nguyên và ngừng cập nhật. Muốn xoá
card thì xoá dòng.

## Những vấn đề khác

Bật **Write a debug log** trong **Settings…** (`Ctrl+Shift+O`), làm lại thao tác
bị lỗi, rồi xem file `debug_sheetcards.log` (nút **Open folder** sẽ đưa bạn tới
đó). Hãy báo lỗi tại
[github.com/tannc28/sheetcards/issues](https://github.com/tannc28/sheetcards/issues),
và đọc qua file log trước khi đính kèm: nó chứa nội dung sheet của bạn.
