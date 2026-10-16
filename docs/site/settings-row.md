# Settings row

Khi không có settings row, cột đầu tiên của bạn là mặt trước của card, các cột
còn lại là mặt sau, chữ thường. **Settings row (dòng thiết lập) quy định mỗi cột
trông ra sao và hoạt động thế nào**: nằm ở mặt nào, cỡ chữ bao nhiêu, có được đọc
thành tiếng không, link trong ô có thành ảnh hay video không, và nhiều thứ khác.

Đây là một dòng không bắt buộc, nằm ngay dưới dòng tên cột. Bạn không sửa gì
trong Anki cả: đổi dòng này, sync lại, và card đổi theo.

[Tạo Sheet](../sheet.html) cho bạn tạo settings row bằng cách bấm chọn, và
hiện card ngay khi bạn soạn.

## Cách viết

**Dòng 2 là settings row khi ô `ID` của nó bắt đầu bằng `#config`.** Khi đó card
của bạn bắt đầu từ dòng 3. Không có dấu hiệu đó thì dòng 2 là một card bình
thường, nên sheet không cần settings thì không bị ảnh hưởng gì.

| ID | Word | Reading | Meaning |
| :--- | :--- | :--- | :--- |
| `#config` | `size=48; tts=zh_CN` | `furigana; color=muted` | |
| 1 | 推迟 | 推迟[tuī chí] | to postpone |

- **Mỗi ô chứa các cặp `key=value`, cách nhau bằng `;`.** `size=48; color=muted`.
- **Một key đứng một mình là một công tắc (switch)**: `bold`, `hint`, `reverse`.
  Ghi `bold=false` (hoặc `no`, `0`, `off`) nếu muốn nói rõ là tắt.
- **Ô trống nghĩa là "dùng mặc định"**, nên bạn chỉ cần ghi những gì muốn đổi.
- **Settings cho cả sheet nằm ngay trong ô `#config`**, sau dấu hiệu và một dấu
  cách: `#config align=left; speed=0.9; reverse`.
- `#CONFIG` cũng được. `#config;align=left` cũng được, nhưng một giá trị như
  `#configuration` thì không phải dấu hiệu, nên dòng đó sẽ là một card.
- Chỉ các cột của bạn mới đọc ô của mình. Mọi thứ trong ô `SYNC`, `TAGS` hay
  `SUBDECK` của settings row đều bị bỏ qua.
- Settings row không bao giờ là một card và không được tính vào tổng số dòng khi
  sync.

**Lỗi được báo ra, không bao giờ bị đoán.** Một key lạ (`siz=48`), một giá trị
sai (`color=notacolour`) hay một số ngoài khoảng cho phép (`size=400`) sẽ tạo ra
một cảnh báo nêu tên cột, và chỉ setting đó bị bỏ đi. Phần còn lại của dòng vẫn
áp dụng. Bạn thấy các cảnh báo trong [Sheet to Anki](../create.html), trong Tạo Sheet, và
trong Anki ở **Tools → SheetCards → Card Layout…**.

## Key cho từng cột

Ghi trong ô của chính cột đó.

| Key | Giá trị | Tác dụng |
| :--- | :--- | :--- |
| `side` | `front`, `back`, `hide` | Cột hiện ở mặt nào. `hide` giữ field trong Anki nhưng không hiện ở mặt nào cả. Mặc định: cột đầu tiên ở mặt trước, các cột còn lại ở mặt sau. |
| `size` | số pixel: **6–200** cho chữ, **1–2000** cho ảnh, video hoặc ô viết chữ (`size=48` hoặc `size=48px`) | Cỡ chữ với chữ; chiều rộng tối đa với `image` hoặc `video`; cạnh của ô với `draw`. Mặc định: 40 px ở mặt trước (nhỏ hơn trên điện thoại), 18 px ở mặt sau. |
| `color` | `muted`, `accent`, tên màu CSS (`crimson`), hoặc `#hex` | Màu chữ. `muted` và `accent` đổi theo chế độ sáng/tối của Anki và [theme](text.md#theme) của sheet. Màu cố định như `black` thì không, và sẽ biến mất ở night mode. |
| `bold`, `italic` | switch | Chữ đậm hoặc nghiêng. |
| `align` | `left`, `center`, `right` | Căn lề, chỉ cho cột này. |
| `label` | chữ bất kỳ | Một nhãn nhỏ phía trên giá trị. |
| `hint` | switch | Giấu giá trị sau một link, bấm vào mới hiện. |
| `furigana` | switch | In cách đọc phía trên chữ. Ô phải viết dạng `日本語[にほんご]`: chữ, rồi cách đọc trong ngoặc vuông. |
| `font` | `sc`, `tc`, `jp`, `kr`, `serif`, `sans`, `mono`, hoặc tên font bất kỳ | Kiểu chữ. Xem [Theme và chữ](text.md#font-cho-tieng-trung-nhat-va-han). |
| `rtl` | switch | Chữ viết từ phải sang trái, cho tiếng Ả Rập, Do Thái và Ba Tư. |
| `vertical` | switch | Chữ viết từ trên xuống, như tiếng Nhật in trong sách. |
| `math` | switch, hoặc `math=block` | Ô là một công thức. Xem [Theme và chữ](text.md#cong-thuc-va-code). |
| `code` | switch, hoặc `code=python` (tên ngôn ngữ bất kỳ) | Ô là source code, tô màu theo ngôn ngữ. |
| `tts` | mã ngôn ngữ **đầy đủ**: `en_US`, `zh_CN`, `ja_JP` | Anki đọc to cột này. Xem [Text to speech](tts.md). |
| `voices` | tên giọng, cách nhau bằng dấu phẩy | Giọng bạn muốn ưu tiên. Không có thì Anki dùng giọng bất kỳ của ngôn ngữ đó. |
| `speed` | **0.5–2.0** | Tốc độ đọc cho cột này. |
| `image`, `audio`, `video` | switch | Ô chứa một link, và card hiện ảnh, trình phát, hoặc video. Xem [Media](media.md). |
| `cloze` | switch | Cột chứa các chỗ trống `{{c1::…}}`, và cả sheet thành sheet cloze. Xem [Các loại card](card-types.md#cloze). |
| `type` | switch, hoặc `type=nc` | Một ô ở mặt hỏi để bạn gõ đáp án. `nc` bỏ qua dấu. Xem [Các loại card](card-types.md#go-dap-an). |
| `draw` | switch | Ô chứa một chữ Hán để bạn viết tay trên card. Xem [Các loại card](card-types.md#viet-chu-bang-tay). |
| `subdeck` | số tầng: `subdeck=1` | Cột là tầng đó của đường dẫn deck, và không hiện trên card. Xem bên dưới. |
| `sort` | switch | Browse của Anki liệt kê và sắp xếp note theo cột này thay vì theo `ID`. |

## Key cho cả sheet

Ghi sau `#config` trong ô dấu hiệu.

| Key | Giá trị | Tác dụng |
| :--- | :--- | :--- |
| `align` | `left`, `center`, `right` | Căn lề cho cả card. `align` riêng của một cột vẫn được ưu tiên. |
| `speed` | một con số từ 0.5 đến 2.0 | Tốc độ đọc cho mọi cột có đọc mà không tự đặt tốc độ. |
| `reverse` | switch | Thêm card thứ hai hỏi mặt sau và trả lời bằng mặt trước. Xem [Các loại card](card-types.md#reverse-card). |
| `theme` | `paper`, `contrast`, `matcha`, `momiji`, `yuki`, `sakura` | Bảng màu cho cả card. Trong Tạo Sheet bạn chọn theme ngay ở bước chọn template. Xem [Theme và chữ](text.md#theme). |
| `name` | tên bộ flashcard, có dấu cách và tiếng Việt cũng được, tối đa 100 ký tự | Tên bộ flashcard — cũng là tên deck Anki hiện — đồng thời là danh tính của sheet. Sheet to Anki nhận ra note của sheet nhờ nó, nên đổi tên file, tải về thành `Từ vựng (1).csv`, lưu ra .xlsx hay đưa lên Google Sheets đều vẫn là cùng một bộ. Hai sheet cùng `name` là **một** bộ: import sheet này sẽ ghi đè note cùng ID của sheet kia. Đổi `name` là tạo bộ mới (một deck mới trong Anki); tiến độ ôn tập ở lại deck cũ. Hoa thường và dấu cách thừa không tính. |
| `next` | một ID kết thúc bằng số, như `w15` | ID tiếp theo Tạo Sheet sẽ cấp. Nhờ nó, ID của một từ đã xoá không bao giờ được cấp lại cho từ mới, vì từ mới sẽ thừa hưởng lịch sử ôn tập của từ cũ trong Anki. |

Tạo Sheet tự viết hai key cuối, ví dụ `#config name=Từ vựng tiếng Anh; next=w15`:
`name` là ô **Tên bộ flashcard** bạn điền khi chọn template, và Tạo Sheet hỏi lại
trước khi đổi nó, vì tên mới là một deck mới trong Anki. `next` không hiện trong
bảng; Tạo Sheet tự giữ nó.
Sheet không có `name` thì được nhận ra theo link Google Sheets, hoặc theo tên
file (bỏ đuôi `.csv`/`.tsv`/`.xlsx` và hậu tố ` (1)`, `-2`). Add-on đọc hai key này
mà không cảnh báo nhưng chưa dùng tới: add-on nhận ra note theo deck và cột `ID`.

## Xếp note vào deck bằng một cột (`subdeck`)

`SUBDECK 1`, `SUBDECK 2` là tên do add-on đặt. `subdeck=1` nói cùng một điều đó
từ một cột của bạn, nên bạn giữ được tên cột của mình:

```text
ID       Level        Word     Meaning
#config  subdeck=1    size=48
w01      HSK 1        写       to write
w02      HSK 2        山       mountain
```

Sheet này xếp `w01` vào subdeck `HSK 1` của deck, và `Level` không hiện trên
card. Note nằm ở đâu thì deck chứa nó đã cho thấy, nên không cần lặp lại trên
card; các setting của card (`size`, `color`, `side`, `tts` và những cái khác) bị
từ chối trên cột như vậy, kèm cảnh báo. `sort` là ngoại lệ duy nhất, vì nó cũng
nói về note.

- Con số là tầng, nên thứ tự lấy theo con số, không theo vị trí các cột.
- Ô trống thì bỏ tầng đó, giống hệt một ô `SUBDECK` trống.
- Hai cột không thể cùng một tầng, và cột media không thể là một tầng.
- Nếu sheet dùng cả hai cách, settings row thắng, và cảnh báo sẽ nêu tên các cột
  `SUBDECK` bị nó ghi đè.

## Nghe được nhưng không hiện (`side=hide` với `tts`)

Một cột có cả `side=hide` và `tts` thì được đọc to nhưng không in ra. Đó là một
card luyện nghe: câu được đọc lên mà không có gì trên màn hình để nhìn theo.

```text
ID       Chinese              Pinyin   Meaning   Once more, slowly
#config  size=40; tts=zh_CN                      side=hide; tts=zh_CN; speed=0.5
```

Cột được đọc ở mặt mà lẽ ra nó sẽ hiện, và một reverse card đảo nó cùng với mọi
thứ khác.

## Một ví dụ cụ thể

| Cột | Ô của nó trong settings row |
| :--- | :--- |
| `ID` | `#config reverse` |
| `Word` | `side=front; size=48; tts=zh_CN; voices=Huihui` |
| `Reading` | `label=Pinyin; furigana; color=muted` |
| `Meaning` | `size=20` |
| `Example` | `size=16; color=muted; hint` |

Với dòng dữ liệu `42 | 推迟 | 推迟[tuī chí] | to postpone, to delay | 会议推迟到下周。`
kết quả là:

- **Mặt trước:** `推迟` cỡ 48 px, được đọc to bằng tiếng Phổ thông, bằng giọng
  *Huihui* nếu thiết bị có.
- **Mặt sau:** cách đọc in phía trên chữ Hán, có nhãn *Pinyin*, màu muted; nghĩa
  cỡ 20 px; câu ví dụ cỡ 16 px, màu muted, giấu sau một link hint.
- **Một card thứ hai** (`reverse`) hỏi mặt sau và trả lời bằng `推迟`.

Những gì không nhắc tới đều giữ mặc định, nên `Meaning` chỉ cần `size=20`.

## Định dạng một cột bằng CSS

Mỗi khối trên card đều mang tên của cột sinh ra nó:

```html
<div class="sc-back" data-sc-col="Pinyin">…</div>
```

Nên với những gì settings row không làm được, phần **Styling** của note type
trong Anki có thể nhắm tới đúng một cột, ví dụ
`[data-sc-col="Pinyin"] { letter-spacing: .04em; }`. Chỉ sửa phần Styling: template
mặt trước và mặt sau được dựng lại từ sheet mỗi lần sync, nên sửa ở đó sẽ không
giữ được.
