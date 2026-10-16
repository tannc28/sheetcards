# Các loại card

Một sheet bình thường tạo một card cho mỗi dòng: mặt trước hỏi, mặt sau trả lời.
[Settings row](settings-row.md) có thể biến nó thành các loại card khác.

## Reverse card

`reverse` trong ô `#config` thêm, cho mỗi dòng, một card thứ hai hỏi mặt sau và
trả lời bằng mặt trước.

```text
ID       Vietnamese   English
#config reverse
r01      đọc          to read
```

cho một card hỏi `đọc` và một card hỏi `to read`. Hai card được lên lịch review
riêng, từ cùng một dòng. Sau này bỏ `reverse` đi thì các card thứ hai đó biến mất
mà không đụng tới nội dung của bạn. Sheet cloze không có reverse card, và card nào
có một mặt trống cũng không có.

## Cloze

Cloze card (điền chỗ trống) giấu một phần của câu. Viết các chỗ trống bằng
markup quen thuộc của Anki `{{c1::…}}` và **nói cột nào chứa chúng** bằng
`cloze`:

```text
ID       Word      Example
#config            cloze
1        熟悉       我对这里{{c1::很熟悉}}，也{{c2::常来}}。
```

- Cột đó thành câu hỏi, dù nó nằm ở đâu trong sheet.
- Anki tạo **một card cho mỗi chỗ trống**: dòng trên cho hai card.
- Các cột khác hiện bên cạnh như bình thường.
- Mỗi sheet một cột cloze. Cột thứ hai bị bỏ qua kèm cảnh báo.

Tại sao phải khai báo? Một sheet dùng chung một thiết kế card cho mọi dòng, nên
câu hỏi "cột nào là cloze" phải được trả lời một lần. Anki hiện một field cloze
không có chỗ trống nào thành trống trơn, nên đoán sai sẽ lặng lẽ làm mất một cột.

Dòng có `{{c1::…}}` trên một sheet không khai báo cột cloze nào sẽ bị báo cảnh
báo, trong Sheet to Anki và trong cửa sổ Card Layout của Anki.

## Gõ đáp án

`type` trên một cột đặt một ô nhập ở mặt hỏi. Bạn gõ đáp án, và khi lật card Anki
so nó với cột đó, từng chữ một.

```text
ID       Hán tự    Pinyin        Meaning
#config            type=nc
```

- `type=nc` bỏ qua dấu và thanh điệu, nên gõ `shuxi` vẫn khớp `shúxī`. Hữu ích
  khi dấu khó gõ mà lại không phải điều cần học.
- Mỗi sheet một cột `type`; Anki chỉ cho một ô nhập mỗi card.
- Ô nhập không lặp lại trên reverse card.
- Trên sheet cloze, `type` trên cột cloze sẽ bắt bạn gõ những chữ bị giấu.

## Viết chữ bằng tay

`draw` biến một cột chứa chữ Hán thành ô viết chữ. Gõ thì kiểm tra bạn có đánh
vần được một từ không; cái này kiểm tra bạn có viết được nó không.

- **Ở mặt hỏi** ô để trống. Bạn viết chữ từng nét, mỗi nét đều được kiểm tra, và
  gợi ý hiện ra sau hai lần sai.
- **Ở mặt trả lời** các nét đúng được chạy hoạt hình.
- Một ô có thể chứa nhiều chữ: `你好` cho hai ô viết.
- `size` là cạnh của ô tính bằng pixel (1–2000); 200–300 là vừa tay.
- `color` đặt màu của các nét. `tts` vẫn chạy, nên chữ đó cũng có thể được đọc
  to.
- `hint` giấu ô viết sau một cú bấm.

Dữ liệu nét chữ lấy từ [HanziWriter](https://hanziwriter.org) qua internet, nên
card có `draw` cần mạng. Không có mạng thì ô hiện chữ đó mờ mờ thay vào. Đã thử
trên Anki cho máy tính; trên AnkiDroid và AnkiMobile thì tuỳ app có cho card tải
nó hay không. Chỉ chữ Hán mới có dữ liệu nét; thứ khác thì được in vào ô.

Sheet `12 Chinese drawing (viết tay)` trong file ví dụ là một deck dùng được
ngay.
