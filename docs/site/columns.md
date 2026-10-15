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
| `ID` | **Có** | Khoá cố định của dòng. Ghi gì cũng được (`1`, `Q-101`, `w01`) miễn là không có hai dòng trùng nhau. **Đừng bao giờ đổi hay dùng lại một ID.** |
| `SYNC` | Không | Bật hoặc tắt một dòng. Dòng được sync khi ô ghi `TRUE`, `1`, `yes`, `sim`, `x` hoặc `✓`. Mọi giá trị khác, kể cả ô trống, nghĩa là "bỏ qua dòng này". **Sheet không có cột `SYNC` thì sync mọi dòng.** |
| `SUBDECK 1`, `SUBDECK 2`, … | Không | Mỗi cột là một tầng của đường dẫn deck. Thứ tự theo con số, không theo vị trí trong sheet, và ô trống thì bỏ tầng đó. `subdeck2` và `Subdeck  10` cũng được. |
| `TAGS` | Không | Tag Anki thêm cho dòng, cách nhau bằng dấu phẩy hoặc chấm phẩy. |

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

Mỗi sheet là một deck tên `sc_<file>::<sheet>`. Các cột `SUBDECK` thêm tầng bên
dưới nó:

| ID | SUBDECK 1 | SUBDECK 2 | Word | Meaning |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Japanese | Kanji | 水 | water |

xếp card vào `sc_<file>::<sheet>::Japanese::Kanji`.

- Sheet không có cột `SUBDECK` thì giữ mọi thứ ngay trong deck đó.
- Trên sheet có chia tầng, **dòng nào không ghi tầng nào sẽ nằm trong một subdeck
  tên `Unsorted`**, để dễ tìm.
- Một cột bình thường cũng có thể là một tầng deck, bằng `subdeck=1` trong
  [settings row](settings-row.md#xep-note-vao-deck-bang-mot-cot-subdeck).
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
ID | SYNC | SUBDECK 1 | SUBDECK 2 | Word | Reading | Meaning | Example | TAGS
```

Một dòng:

```text
42 | TRUE | Japanese | Kanji | 水 | みず | water | 水を飲む | jlpt-n5; nature
```

Kết quả:

- **Field:** `ID`, `Word`, `Reading`, `Meaning`, `Example`. `ID` luôn đứng đầu.
- **Card:** mặt trước `Word`; mặt sau `Reading`, `Meaning` và `Example`.
- **Deck:** `sc_<file>::<sheet>::Japanese::Kanji`.
- **Tag:** `sheetcards`, `sheetcards::japanese::kanji`, `jlpt-n5`, `nature`.

## Cloze là do sheet chọn

Một ô chứa `{{c1::…}}` không tự tạo ra cloze card. Bạn nói cột nào chứa các chỗ
trống bằng `cloze` trong settings row; xem
[Các loại card](card-types.md#cloze). Dòng có `{{c1::…}}` trên một sheet không khai
báo cột cloze nào sẽ bị báo cảnh báo, vì nếu không thì đoạn markup sẽ bị in
nguyên văn lên card.
