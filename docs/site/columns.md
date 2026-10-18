# Các cột

Không có danh sách cột cố định. **Dòng 1 đặt tên các cột, và mỗi dòng bên dưới
là một card** (một note trong Anki). Chỉ vài tên có ý nghĩa đặc biệt; mọi cột
khác thành một field cùng tên, bằng ngôn ngữ nào cũng được.

Tên cột được so khớp không phân biệt chữ hoa chữ thường hay dấu cách ở hai đầu,
nên `id`, `ID ` và `Id` là cùng một cột.

## Các cột dành riêng

Chỉ những tên này là đặc biệt:

| Cột | Bắt buộc? | Tác dụng |
| :--- | :--- | :--- |
| `ID` | **Nên có** | Khoá cố định của dòng. Ghi gì cũng được (`1`, `Q-101`, `w01`) miễn là không có hai dòng trùng nhau. **Đừng bao giờ đổi hay dùng lại một ID.** Sheet không có cột này vẫn dùng được, xem [Sheet không có cột ID](#sheet-khong-co-cot-id). |
| `SYNC` | Không | Bật hoặc tắt một dòng. Dòng được sync khi ô ghi `TRUE`, `1`, `yes`, `sim`, `x` hoặc `✓`. Mọi giá trị khác, kể cả ô trống, nghĩa là "bỏ qua dòng này". **Sheet không có cột `SYNC` thì sync mọi dòng.** |
| `TAGS` | Không | Tag Anki thêm cho dòng, cách nhau bằng dấu phẩy hoặc chấm phẩy. |

## Sheet không có cột ID

Sheet không có cột `ID` vẫn thành card. Khi đó **chữ ở cột nội dung đầu tiên của
mỗi dòng là ID của dòng**, và trang Tạo flashcard báo một dòng:
*"Không có cột ID → dùng cột Word làm ID. Sửa chính tả chính từ đó sẽ thành card
mới."*

- Chữ được chuẩn hoá trước khi làm ID: bỏ dấu cách ở hai đầu, gộp các dấu cách
  liền nhau, và thống nhất cách gõ dấu tiếng Việt (bàn phím điện thoại và máy tính
  có thể ghép `ệ` khác nhau). Hoa thường được giữ nguyên.
- Hai dòng cùng một chữ (không tính hoa thường) thì dòng sau thành `từ (2)`, rồi
  `từ (3)`, theo thứ tự trong sheet.
- Chèn dòng mới vào giữa hay đổi thứ tự các dòng không sao: khoá là chữ, không
  phải vị trí, nên import lại vẫn cập nhật đúng note cũ và giữ tiến độ ôn tập.
- **Sửa chính tả chính chữ đó là một card mới**, và card cũ (cùng tiến độ của nó)
  vẫn nằm trong Anki. Nếu bạn hay sửa từ ở cột đầu, hãy thêm một cột `ID`.
- Dòng có cột đầu trống là dòng lỗi (không có gì làm khoá), dù các ô khác có chữ.
- [Settings row](settings-row.md) vẫn dùng được: không có ô ID thì `#config` mở đầu
  ô settings của cột đầu tiên, ví dụ `#config name=Từ vựng; size=40`. Các key cho cả
  sheet (`name`, `reverse`, `theme`, `next`, `shape`) thuộc về sheet; các key còn lại
  trong ô đó thuộc về cột đầu.

Template *Mặt trước / Mặt sau* và *Học từ vựng* của Tạo Sheet là sheet như vậy: cột
đầu (Mặt trước, hay Word) là khoá, không có cột `ID`. Mở một file không có cột `ID`
trong Tạo Sheet thì nó vẫn không có cột `ID`. Sheet có cột `ID` thì giữ nguyên ID
và `next=`.

## Các cột của bạn

Mọi cột khác thành một field của note, đặt tên đúng như tên cột. `Word`,
`Pinyin`, `Nghĩa`, `例句`: đặt tên theo môn bạn học.

- **Cần ít nhất một cột.** Sheet chỉ có các cột dành riêng sẽ bị từ chối với lỗi
  *"The sheet has no content columns"*.
- **Trái sang phải là thứ tự trên card.** Cột đầu tiên của bạn ở mặt trước, các
  cột khác ở mặt sau. Dời một cột là card đổi theo. Muốn quyết định riêng cho
  từng cột thì dùng `side=` trong [settings row](settings-row.md).
- **Một tên dùng hai lần chỉ tính một lần.** Cột đầu tiên mang tên đó thắng, cột
  kia bị bỏ qua.

## Subdeck

Mỗi sheet là một deck. Sheet có `name=` trong
[settings row](settings-row.md#key-cho-ca-sheet) thì deck mang đúng tên đó, như bạn
gõ (ví dụ `Từ vựng IELTS tuần 1`), cả trong file `.apkg` lẫn add-on. Sheet không có
`name=` thì deck mang tiền tố `sc_`: `sc_<tên file>` trong trang Tạo flashcard,
`sc_<file>::<sheet>` trong add-on. Một cột có `subdeck=1` trong
[settings row](settings-row.md#xep-note-vao-deck-bang-mot-cot-subdeck) thêm một tầng
bên dưới nó, `subdeck=2` thêm tầng tiếp theo:

| ID | Ngôn ngữ | Bài học | Word | Meaning |
| :--- | :--- | :--- | :--- | :--- |
| `#config` | `subdeck=1` | `subdeck=2` | | |
| 1 | Japanese | Kanji | 水 | water |

xếp card vào `<deck>::Japanese::Kanji`. Hai cột tầng không hiện trên card.

- Sheet không có cột tầng nào thì giữ mọi thứ ngay trong deck đó.
- Trên sheet có chia tầng, **dòng nào không ghi tầng nào sẽ nằm trong một subdeck
  tên `Unsorted`**, để dễ tìm.
- Sheet cũ có cột tên `SUBDECK 1`, `SUBDECK 2` vẫn được xếp tầng như trước, kèm
  cảnh báo nhắc đổi sang `subdeck=`.
- Subdeck nào trống sau khi sync sẽ bị xoá.

## Tag

Mỗi note nhận ba loại tag:

1. `sheetcards`, trên mọi note do add-on tạo, để bạn tìm được tất cả.
2. `sheetcards::<đường dẫn subdeck>`, phản chiếu cây deck trong thanh bên của
   Browse trong Anki.
3. Những gì cột `TAGS` liệt kê.

Tag được dọn gọn: chữ thường, dấu cách và `:`/`;` đổi thành `_`, dấu câu khác bị
bỏ. `Unit 3: Intro` thành `unit_3_intro`.

## Một ví dụ cụ thể

Dòng 1:

```text
ID | SYNC | Ngôn ngữ | Bài học | Word | Reading | Meaning | Example | TAGS
```

Settings row ghi `subdeck=1` dưới `Ngôn ngữ` và `subdeck=2` dưới `Bài học`. Một dòng:

```text
42 | TRUE | Japanese | Kanji | 水 | みず | water | 水を飲む | jlpt-n5; nature
```

Kết quả:

- **Field:** `ID`, `Word`, `Reading`, `Meaning`, `Example`. `ID` luôn đứng đầu.
- **Card:** mặt trước `Word`; mặt sau `Reading`, `Meaning` và `Example`.
- **Deck:** `<deck>::Japanese::Kanji`.
- **Tag:** `sheetcards`, `sheetcards::japanese::kanji`, `jlpt-n5`, `nature`.

## Cloze là do sheet chọn

Một ô chứa `{{c1::…}}` không tự tạo ra cloze card. Bạn nói cột nào chứa các chỗ
trống bằng `cloze` trong settings row; xem
[Các loại card](card-types.md#cloze). Dòng có `{{c1::…}}` trên một sheet không khai
báo cột cloze nào sẽ bị báo cảnh báo, vì nếu không thì đoạn markup sẽ bị in
nguyên văn lên card.
