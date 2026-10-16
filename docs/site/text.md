# Theme và chữ

Trang này nói về vẻ ngoài của card: bảng màu (theme), rồi màu, font và hướng viết
của chữ trên card, cộng thêm hai loại ô không phải chữ thường. Tất cả đều là key
trong [settings row](settings-row.md).

## Theme

Không có theme thì card dùng màu mặc định của Anki. Theme tô màu cho cả card.
Ghi tên theme trong ô đánh dấu của settings row:

```text
#config theme=paper
```

Trong [Tạo Sheet](../sheet.html), theme được chọn ngay ở bước chọn template, hàng
**Theme** dưới card xem trước: bấm **Mặc định** (màu của Anki) hoặc một theme, card
đổi màu ngay, và Tạo Sheet ghi `theme=` vào ô `#config` giúp bạn. Theme không phải
là template: template nào cũng dùng được với theme nào.

| Theme | Trông như thế nào |
| :--- | :--- |
| `paper` | Giấy ấm và mực; dịu mắt nhất khi học lâu. |
| `contrast` | Đen trắng, điểm nhấn màu xanh (ban đêm là màu vàng), cho người mắt kém hoặc khi dùng điện thoại ngoài nắng. |
| `matcha` | Màu trà xanh nhẹ. |
| `momiji` | Mùa thu: tông ấm, có lá phong vẽ phía sau chữ. |
| `yuki` | Mùa đông: xanh lạnh, có bông tuyết. |
| `sakura` | Mùa xuân: hồng hoa anh đào, có hoa vẽ phía sau chữ. |

- Theme nào cũng có bản sáng và bản tối, và tự đổi theo night mode của Anki.
- Theme quyết định `color=muted` và `color=accent` là màu gì, nên các cột dùng
  hai giá trị này luôn hợp với theme.
- Lá, bông tuyết và hoa do chính card vẽ ra; không cần mạng.
- Theme tô màu card chứ không tô phần Anki xung quanh: trên máy tính, thanh trên
  cùng và các nút trả lời vẫn giữ màu của Anki. Trên điện thoại thì card chiếm
  cả màn hình.
- Tên theme không có sẵn sẽ bị từ chối kèm cảnh báo, và card giữ màu của Anki.

## Màu chữ

`color=` nhận một trong các giá trị:

- **`muted`** hoặc **`accent`**: một màu xám dịu và một màu nổi bật, đổi theo
  chế độ sáng/tối của Anki. Nên ưu tiên dùng hai giá trị này.
- **Tên màu CSS** như `crimson` hay `teal`.
- **Mã `#hex`** như `#c2410c`.

Màu cố định thì vẫn giữ nguyên trong night mode, nên `color=black` sẽ biến mất
trên card nền tối. `muted` và `accent` không bị vấn đề này.

## Font cho tiếng Trung, Nhật và Hàn

Nhiều chữ Trung, Nhật và Hàn dùng chung một mã nhưng mỗi ngôn ngữ vẽ một kiểu:
`直` và `骨` trông khác nhau trong font tiếng Trung và font tiếng Nhật. Máy chỉ có
font tiếng Nhật sẽ vẽ deck tiếng Trung bằng nét chữ Nhật. `font=` cho card biết
bạn muốn kiểu nào:

| Giá trị | Font |
| :--- | :--- |
| `sc` | Noto Sans SC, tiếng Trung giản thể |
| `tc` | Noto Sans TC, tiếng Trung phồn thể |
| `jp` | Noto Sans JP, tiếng Nhật |
| `kr` | Noto Sans KR, tiếng Hàn |
| `serif`, `sans`, `mono` | Font serif, sans-serif hoặc monospace có sẵn trên máy |
| tên bất kỳ khác | Font đó, nếu máy có cài |

Bốn font Noto được tải từ Google Fonts, nên lần đầu cần có mạng.

## Hướng viết

- **`rtl`** viết từ phải sang trái, cho tiếng Ả Rập, Do Thái và Ba Tư. Chữ được
  canh phải, trừ khi `align` ghi khác.
- **`vertical`** viết từ trên xuống, các cột từ phải sang trái, như tiếng Nhật
  in trong sách. Chữ Latin vẫn đứng thẳng.

Mỗi cột chỉ một hướng viết; nếu ghi cả hai thì `rtl` thắng.

## Công thức và code

**`math`** cho biết ô là một công thức viết bằng LaTeX. Anki vẽ nó bằng MathJax
có sẵn, nên không cần cài thêm gì. `math` giữ công thức nằm trong dòng;
`math=block` đặt nó căn giữa trên một dòng riêng.

```text
ID       Formula               Meaning
#config  math=block
1        E = mc^2              mass-energy equivalence
```

**`code`** cho biết ô là source code. Code được giữ nguyên như bạn gõ, canh trái,
và tô màu theo ngôn ngữ: `code=python`, `code=bash`, `code=html`,
`code=javascript`, v.v. Phần tô màu do highlight.js làm, tải qua mạng; không có
mạng thì code hiện ra không màu.

## Thứ tự sắp xếp trong Browse của Anki

`sort` trên một cột khiến Browse của Anki liệt kê và sắp xếp các note theo cột
đó. Không có nó thì note được liệt kê theo `ID`, đọc lên là `w01, w02, w03`.
