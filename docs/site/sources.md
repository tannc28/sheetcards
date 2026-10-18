# Sheet, file và .apkg

Card của bạn có thể nằm ở đâu, và có những cách nào để chúng vào Anki.

## Một file, mỗi sheet một deck

Một file Google Sheets chứa nhiều sheet, tức các tab ở phía dưới. SheetCards kết
nối **mỗi sheet thành một deck riêng**, tên là `sc_<file>::<sheet>` (hoặc đúng
tên `name=` của sheet, nếu có), với cột,
settings row và note type của riêng nó. Chỉ cần dán link của file một lần là một
spreadsheet có thể chứa cả collection của bạn. Sau đó `Ctrl+Shift+S` liệt kê mỗi
sheet một dòng, để bạn chọn sheet nào cần cập nhật.

- **Trong một file mà các sheet khác có cột `ID`, sheet không có cột `ID` sẽ bị
  bỏ qua**, và cửa sổ cho biết là sheet nào. Ghi chép, bảng chú thích màu hay bản
  nháp có thể nằm chung file. Nếu không sheet nào có cột `ID`, mỗi sheet thành một
  deck và dùng cột đầu tiên làm ID (xem [Cột](columns.md#sheet-khong-co-cot-id)).
  Sheet bị ẩn luôn bị bỏ qua.
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

## Sheet to Anki

[Sheet to Anki](../create/) tạo flashcard Anki từ sheet trên điện thoại hoặc
máy tính, không cần cài add-on. Trước khi tải về, nó cho bạn thấy SheetCards làm
ra gì từ sheet: từng dòng và việc nó có thành note hay không, cây deck, tag, cảnh
báo từ settings row, và từng card hoàn chỉnh, mà bạn có thể lật, nghe và gõ đáp
án vào. Nó chạy chính code của add-on trong trình duyệt, nên những gì nó hiện ra
được làm đúng như add-on làm. Chỉ có bước cuối cùng, vẽ card, là trang tự mô
phỏng lại Anki; còn nội dung template nó hiện ra là chính xác.

Sau khi sửa sheet, bấm nút tải lại cạnh tên sheet, Sheet to Anki sẽ tải sheet lại và
giữ nguyên chỗ bạn đang xem.

### Upload một file

Bấm **Chọn file .xlsx hoặc .csv**, hoặc kéo một file vào trang, để mở một file
`.xlsx`, `.xlsm`, `.csv` hoặc `.tsv` trên máy bạn. Mỗi tab của workbook thành một
deck riêng. File không bao giờ rời khỏi trình duyệt của bạn.

- **Bản thân add-on vẫn cần một link.** File đã upload đến được Anki qua bản tải
  `.apkg` bên dưới.
- **Ô được đọc đúng như sheet hiện.** Ngày ra dạng `2025-01-21`, số nguyên ra
  `1` chứ không phải `1.0`.
- **File CSV lưu từ Excel cũng đọc được.** Dấu phân cách (phẩy, chấm phẩy hay
  tab) được tự nhận ra, file UTF-16 ("Unicode Text") cũng vậy. File không phải
  UTF-8, như "CSV (Comma delimited)" của Excel tiếng Việt, được đọc theo bảng mã
  Windows tiếng Việt (cp1258) hoặc phương Tây (cp1252), và trang báo cho bạn biết
  để kiểm tra dấu. Chắc nhất là lưu bằng **CSV UTF-8** trong Excel.

### Tải về một file .apkg

Nút **Download .apkg** dựng deck thành một file `.apkg`. **AnkiDroid và AnkiMobile
import thẳng được file này**, nên sheet có thể lên điện thoại mà không cần Anki
trên máy tính. File được dựng bằng chính code của add-on, với cùng field và
thiết kế card, và danh tính của note lấy từ cột `ID` của bạn, nên **import lại sẽ
cập nhật các note đó chứ không nhân đôi**.

Điều import không làm được là **xoá**: Anki không bao giờ xoá một note không có
trong file. Dòng bạn xoá khỏi sheet vẫn nằm trong collection cho tới khi bạn xoá
nó ở đó. Đó chính là khác biệt thật sự giữa import và sync.

Deck nào là deck nào được quyết định theo thứ tự này:

1. **`name=` trong [settings row](settings-row.md#key-cho-ca-sheet)**, nếu có. Deck
   mang đúng tên đó, không có tiền tố `sc_`; add-on cũng dùng tên này.
   Tạo Sheet luôn ghi nó (đó là **Tên bộ flashcard**), nên file bị đổi tên (`Từ vựng (1).csv`), bản `.xlsx`,
   link chia sẻ hay cùng sheet đó trên Google Sheets đều cập nhật cùng một deck.
   Hai sheet cùng `name` là một deck và sẽ ghi đè note của nhau; một sheet
   copy ra vẫn là deck cũ cho tới khi bạn đổi tên nó.
2. Không có thì theo link Google Sheets và tên tab.
3. Không có link thì theo tên file, bỏ đuôi `.csv`/`.tsv`/`.xlsx` và hậu tố
   ` (1)`, `(1)`, `-2` mà điện thoại thêm vào bản tải thứ hai.

Tạo Sheet còn ghi `next=` vào cùng ô: số ID tiếp theo sẽ cấp. Nhờ đó ID của một
từ đã xoá không bao giờ được dùng lại cho từ khác, vì Anki sẽ coi đó là từ cũ.

**Đổi cột thì phải bật Merge note types một lần.** Thêm, đổi tên một cột, bật
`reverse`… là đổi note type; với tuỳ chọn mặc định Anki sẽ không cập nhật note nào.
Sheet to Anki so sheet với `shape=` mà Tạo Sheet ghi trong ô `#config` (và với lần
tải trước trên máy này) rồi nhắc bạn: khi import, bật **Merge
note types** và đặt **Update notes** thành **Always**. Bỏ hoặc đổi chỗ một cột thì
không cần. Chuyển sang hoặc ra khỏi `cloze` thì Anki không gộp được; trang sẽ nói
cách giữ tiến độ.

## Tạo Sheet

[Tạo Sheet](../sheet/) là chỗ soạn cả một sheet trên web, không cần
Google Sheets: tên cột, [settings row](settings-row.md) và từng từ. Bắt đầu từ
một trong 8 template (xem [Soạn trong Tạo Sheet](index.md#soan-trong-tao-sheet)),
một template của bạn, hoặc mở một file `.xlsx`/`.csv` có sẵn. Trên máy tính nó là một spreadsheet: dán nhiều dòng từ Excel hay Google
Sheets là thêm từ. Trên điện thoại mỗi từ mở ra thành một form, mỗi cột một ô.
Setting được chọn từ danh sách, và card của từ đang sửa hiện ngay bên cạnh.

Bản nháp được lưu trong trình duyệt sau mỗi thay đổi, nhưng chỉ trong trình
duyệt này, nên hãy lưu sheet ra ngoài: **trên điện thoại bấm Lưu link sheet,
trên máy tính bấm Lưu file .csv**. Trang ghi *Chưa lưu… mới là nháp trong trình duyệt* cho tới khi bạn lưu. Từ
đó có ba lối ra:

- **Tạo flashcard**: chuyển thẳng sheet sang Sheet to Anki để xem card và tải `.apkg`.
- **Tải sheet về máy** dạng `.xlsx` hoặc `.csv`: giữ sheet thành file, mở lại ở đây để sửa
  tiếp, hoặc upload lên Google Drive thành Google Sheets.
- **Share link**: cả sheet được nén vào chính link (sau dấu `#`), không gửi lên
  máy chủ nào. Người mở link thấy đúng sheet đó và sửa tiếp trên bản của họ; link
  cũng mở thẳng được thành card trong Sheet to Anki. Link rất dài có thể bị vài app
  chat cắt bớt, khi đó hãy gửi file. **Trên điện thoại, nút này là Lưu link
  sheet và là cách lưu chính**: giữ link (gửi cho chính bạn), lần sau mở link là
  thêm từ tiếp được. Trên máy tính, cách lưu chính là file `.csv`.

### Dán danh sách từ

Ở bước ② **Thêm thẻ** có nút **Dán danh sách từ** (trên điện thoại nằm trên danh
sách từ, trên máy tính dưới spreadsheet). Dán vào mỗi dòng một từ, có thể kèm nghĩa:
`apple - quả táo`, `apple ; quả táo`, `apple: quả táo`, `apple = quả táo`, hoặc
hai cột copy từ Excel hay Google Sheets. Dấu tách được tự nhận (đổi được), dấu
đầu dòng của app ghi chú như `- `, `• `, `1. ` được bỏ đi, và gạch nối trong
một từ như `well-known` không bị tách.

Bảng xem trước cho thấy từng dòng sẽ vào cột nào: phần đầu vào cột từ, phần sau
vào cột nghĩa; đổi được cho từng phần. **Từ trùng** (lặp trong danh sách, hoặc
đã có trong sheet, không phân biệt hoa thường) bị gạch đi và bỏ ra, trừ khi bạn
tick lại. Với sheet tiếng Trung hoặc tiếng Hàn (đọc từ `tts=` của cột từ) có
cột Phiên âm, pinyin hoặc romanization được điền vào ô còn trống. Đây là gợi ý
tính trên máy bạn, nên xem lại; tiếng Nhật chưa được điền. **Thêm N từ** thêm
các từ đó. Với sheet lấy cột đầu làm khoá, một từ trùng mà bạn vẫn tick lại được
giữ thành `từ (2)`; với sheet có cột `ID`, các từ mới nhận ID nối tiếp.

### Gợi ý

Nút **Gợi ý** (trong form một từ trên điện thoại, dưới spreadsheet cho các dòng
đang chọn trên máy tính, hoặc *Gợi ý cho N từ* khi dán danh sách) tra từ ở các
nguồn mở rồi đưa ra lựa chọn cho từng cột có trong sheet:

- **Nghĩa**: tối đa 5 nghĩa từ Wiktionary, mỗi nghĩa có từ loại, nghĩa tiếng Anh
  và nghĩa tiếng Việt khi en.wiktionary hoặc vi.wiktionary có.
- **IPA** giọng US hoặc UK, từ en.wiktionary.
- **Câu ví dụ** từ Tatoeba kèm bản dịch tiếng Việt. Bản dịch do người dùng đóng
  góp, nên đọc lại trước khi dùng.
- **File phát âm** từ Wikimedia Commons, nếu sheet có cột `audio`.
- **Ảnh** từ Wikimedia Commons, nếu sheet có cột `image`. Ô lưu địa chỉ
  `Special:FilePath/…` giống file ví dụ.

Không có gì được chọn sẵn. Bạn chọn một nghĩa, một câu, một ảnh; gợi ý hiện
cạnh giá trị đang có của ô, được đánh dấu cho tới khi bạn bấm **Dùng**, sửa,
hoặc **Bỏ**. Ô bạn đã tự gõ chỉ bị thay khi bạn bấm **Thay**. Với tiếng Trung,
Nhật, Hàn chỉ có nghĩa tiếng Anh từ Wiktionary cùng pinyin hoặc romanization,
chưa có nghĩa tiếng Việt.

**Quyền riêng tư:** lần đầu dùng, trang hỏi trước khi gửi. Gợi ý gửi từng từ tới
wikimedia.org (Wiktionary, Commons) và tatoeba.org, không gửi gì khác trong
sheet. Kết quả được lưu trong trình duyệt để lần sau không phải tra lại.

**Nguồn:** khi bạn dùng một gợi ý, nguồn của nó được ghi vào cột Note hoặc
Nguồn của từ đó (nếu cột Note đã có chữ bạn viết, hoặc sheet không có hai cột
này, trang thêm một cột *Nguồn* với `side=hide`, không hiện trên card, xoá được).
Giấy phép: Wiktionary [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/),
Tatoeba [CC BY 2.0 FR](https://creativecommons.org/licenses/by/2.0/fr/), mỗi
file trên Commons theo tác giả và giấy phép riêng (ghi kèm tên file). Pinyin
dùng thư viện pinyin-pro, romanization tiếng Hàn dùng es-hangul (cả hai MIT),
tải về trình duyệt chỉ khi cần.
