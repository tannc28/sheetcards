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

**"Không có cột ID → dùng cột … làm ID."**
Sheet không có cột `ID`, nên chữ ở cột nội dung đầu tiên làm ID của mỗi dòng.
Thêm, chèn hay đổi thứ tự dòng vẫn cập nhật đúng note cũ, nhưng sửa chính tả chính
chữ đó sẽ thành một card mới. Muốn sửa chữ thoải mái thì thêm một cột `ID`. Chỉ
dòng 1 được đọc làm tên cột, nên nếu cột `ID` của bạn nằm dưới một dòng tiêu đề,
hãy xoá dòng tiêu đề đó. Xem [Sheet không có cột ID](columns.md#sheet-khong-co-cot-id).

**"Dùng link Share, không phải Publish"**
Link **File → Share → Publish to web** (`…/spreadsheets/d/e/…/pub…`) được đọc
nếu nó xuất bản cả sheet, nhưng nên dùng link **Share → Anyone with the link →
Viewer**: nó luôn là bản mới nhất và giữ đúng từng tab.

**"The sheet has no content columns"**
Sheet chỉ có các cột `ID`, `SYNC` hoặc `TAGS`. Thêm ít nhất một cột
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
không cho phép nhúng. Phần cảnh báo trong trang Tạo flashcard sẽ cho biết là trường hợp nào.

## Deck

**Tôi đổi tên deck rồi mà Anki lại đổi về tên cũ.**
Đó là bình thường: tên lấy từ sheet. Hãy đổi tên file spreadsheet thay vì đổi
tên deck. Xem [Sync](syncing.md#ten-lay-tu-sheet).

**Bộ có `name=` giờ có hai deck: `sc_Tên bộ` và `Tên bộ`.**
Bộ có `name=` giờ vào Anki đúng tên bạn đặt, không còn tiền tố `sc_`. Anki nhận deck
theo tên và giữ card cũ ở deck cũ, nên nếu bạn đã import bộ này trước thay đổi đó,
card cũ ở lại `sc_Tên bộ` còn card mới vào `Tên bộ`. Cách sửa, một lần: trong Anki
mở Browse, chọn deck `sc_Tên bộ`, chọn hết card, **Cards → Change Deck…** sang
`Tên bộ`, rồi xoá deck `sc_Tên bộ` đã trống. Chưa import file mới thì đơn giản hơn:
đổi tên deck `sc_Tên bộ` thành `Tên bộ` trước (bánh răng cạnh deck → **Rename**).
Trang Tạo flashcard tự nhắc việc này nếu trình duyệt đã từng tải bộ đó. Add-on tự đổi tên
deck của nó, không cần làm gì.

**Tôi đổi tên một tab sheet và deck của nó không còn cập nhật nữa.**
Deck nhớ sheet của nó theo tên. Hãy kết nối lại file để add-on nhận tên mới.

**Tôi đã xoá một dòng mà card vẫn còn trong Anki.**
Nếu bạn import file `.apkg` từ trang Tạo flashcard thì import vốn hoạt động như vậy: nó cập
nhật và thêm mới nhưng không bao giờ xoá. Sync bằng add-on thì có xoá.

**Tôi đặt `SYNC` là no mà card không bị xoá.**
Đó là cố ý: dòng không được tick sẽ được giữ nguyên và ngừng cập nhật. Muốn xoá
card thì xoá dòng.

## Trên điện thoại

**Bấm Download mà không có file nào, hoặc trang hiện báo "Mở trang này bằng
Chrome/Safari".**
Bạn đang mở trang trong trình duyệt riêng của một app (Messenger, Telegram,
Facebook, Instagram, TikTok, Line…). Trình duyệt đó không lưu được file. Bấm
**Copy link** trên thanh báo rồi dán vào Chrome hoặc Safari; trên Android bấm
**Mở bằng Chrome**. Hoặc mở menu của app (dấu ba chấm) và chọn mở bằng trình
duyệt.

**Chrome trên Android lưu file thành `….apkg.zip` và AnkiDroid không mở được.**
File vẫn nguyên vẹn, chỉ bị thêm đuôi `.zip`. Mở app **Files**, nhấn giữ file →
**Rename**, xoá `.zip` ở cuối để tên kết thúc bằng `.apkg`, rồi chạm vào file và
chọn AnkiDroid. Hoặc trong AnkiDroid: menu → **Import** → chọn file đó.

**Trên iPhone, AnkiMobile không có trong danh sách Share.**
Mở AnkiMobile một lần trước (app phải được cài và mở ít nhất một lần). Trong app
**Files**, chạm vào file `.apkg` → **Share**, kéo dãy app sang phải tới
**More** (Thêm) và bật AnkiMobile.

**Card của tôi bị nhân đôi sau khi import lại.**
Anki chỉ cập nhật note cũ khi file mới được nhận ra là cùng một deck. Deck được
nhận ra theo **Tên bộ flashcard** (`name=` ở ô `#config` của settings row); sheet
không có tên thì theo link Google Sheets, rồi theo tên file. Đổi tên bộ, hay một
sheet cũ không có tên mà file bị đổi tên, sẽ thành deck mới. Cách sửa: trong Anki
xoá deck thừa (giữ deck có lịch sử ôn), rồi giữ nguyên tên bộ ở mọi lần sau.
Tạo Sheet luôn hỏi tên này và đề nghị ghi nó vào một sheet cũ chưa có. Xem
[Sheet, file và .apkg](sources.md#tai-ve-mot-file-apkg).

**Import xong mà không có gì thay đổi.**
Bạn đã thêm, đổi tên cột hay bật `reverse` nên note type đã đổi, và với tuỳ chọn
mặc định Anki bỏ qua mọi note. Import lại file đó, lần này bật **Merge note
types** và đặt **Update notes** thành **Always**. Trang Tạo flashcard cũng nhắc việc này
ngay trước khi tải.

**Import sau khi Merge note types mà note không đổi.**
Khi bật **Merge note types**, Anki ghi lại thời điểm sửa của các note cũ, nên
**Update notes: If newer** sẽ bỏ qua chúng. Lần import đó hãy đặt **Update
notes** thành **Always**. Chuyển giữa Basic và Cloze thì không gộp được: trong
Anki, chọn các note và dùng **Change Note Type**.

**Tôi tắt `reverse` mà card ngược vẫn còn.**
Anki giữ những card một card template đã tạo ra. SheetCards giữ template đó lại
dưới dạng một template rỗng, nên import vẫn cập nhật note bình thường; sau đó
trong Anki chọn **Tools → Empty Cards** để xoá các card ngược. Nếu bạn tải file
trên một máy chưa từng tải deck này, hãy bật **Merge note types** một lần khi
import.

**Từ đã xoá khỏi sheet vẫn còn trong Anki.**
Import `.apkg` chỉ thêm và cập nhật, không bao giờ xoá. Muốn bỏ thì xoá trong
Anki: **Browse**, tìm từ đó, **Delete**. Add-on trên máy tính thì sync cả việc
xoá.

**Tôi lưu file `.csv` trên Android, chạm vào nó và AnkiDroid import một mớ note lạ.**
AnkiDroid nhận cả file CSV và import từng dòng thành note, kể cả settings row.
Xoá các note đó trong AnkiDroid, và lần sau mở file `.csv` bằng **Mở file .xlsx/.csv** trong Tạo Sheet. Trên điện thoại, **Tải về / Lưu → Link sheet** tiện hơn file.

**File CSV lưu từ Excel bị lỗi dấu tiếng Việt.**
Trang Tạo flashcard và Tạo Sheet tự nhận ra dấu phân cách và bảng mã của file CSV từ
Excel (kể cả "CSV (Comma delimited)" trên Windows tiếng Việt) và báo khi phải
đoán bảng mã. Nếu dấu vẫn sai, trong Excel chọn **Save As → CSV UTF-8** rồi mở
file đó. Xem [Upload một file](sources.md#upload-mot-file).

**Bản nháp trong Tạo Sheet biến mất.**
Bản nháp chỉ nằm trong trình duyệt, và Safari trên iPhone xoá dữ liệu của trang
sau 7 ngày không mở. Lưu sheet bằng **Tải về / Lưu → Link sheet** (điện thoại) hoặc
**Tải về / Lưu → .csv** (máy tính); thêm trang vào màn hình chính (**Share → Add to Home
Screen**) để mở lại nhanh.

## Những vấn đề khác

Gặp lỗi? → [Liên hệ & góp ý](../contact/?from=docs/faq&kind=bug): gửi góp ý ngay trên
web, hoặc nhắn qua GitHub hay Facebook.

Bật **Write a debug log** trong **Settings…** (`Ctrl+Shift+O`), làm lại thao tác
bị lỗi, rồi xem file `debug_sheetcards.log` (nút **Open folder** sẽ đưa bạn tới
đó). Hãy báo lỗi tại
[github.com/tannc28/sheetcards/issues](https://github.com/tannc28/sheetcards/issues),
và đọc qua file log trước khi đính kèm: nó chứa nội dung sheet của bạn.
