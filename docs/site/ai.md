# Tạo bộ từ bằng AI

ChatGPT, Gemini và Claude soạn được cả bộ từ cho bạn. Bạn chọn một trong hai kiểu
câu trả lời, cùng một bộ, cùng các cài đặt (xem
[Viết cả bộ bằng chữ](import.md#viet-ca-bo-bang-chu)):

- **Văn bản**: một khối chữ, dòng 1 là `#config name=…`, dòng 2 là tên cột kèm
  cài đặt trong ngoặc vuông, sau đó mỗi từ một dòng. Dán thẳng vào **Dán văn
  bản** của Sheet to Anki, và giữ trong ghi chú để lần sau thêm từ.
- **Bảng**: hàng 1 là tên cột, hàng 2 là settings row `#config`, sau đó mỗi từ một
  hàng. AI gửi file `.csv` (nếu đính kèm được file) để mở bằng **Mở file**, hoặc
  một bảng để dán vào **Dán văn bản**. Hợp khi bạn muốn đưa bộ từ vào Google
  Sheets hay Excel.

Bộ đơn giản thì câu lệnh tự nói đủ định dạng. Card cầu kỳ hơn (luyện viết chữ,
furigana, cloze, ảnh) thì đưa AI hướng dẫn đầy đủ, bằng tiếng Anh vì AI làm theo
tiếng Anh tốt nhất:

```text
%%SITE%%ai.md
```

## Các bước

1. **Copy một câu lệnh** ở dưới, sửa phần chủ đề, số từ, tên bộ theo ý bạn.
2. **Dán vào ChatGPT, Gemini hoặc Claude** rồi gửi.
3. **Văn bản**: copy khối chữ AI trả về, vào [Sheet to Anki](../create/), bấm
   **Dán văn bản** và dán vào. **Bảng**: mở file `.csv` bằng **Mở file
   .xlsx/.csv**, hoặc copy bảng rồi dán vào **Dán văn bản**.
4. **Xem từng card**, rồi bấm **Download `.apkg`** và mở file đó bằng AnkiDroid,
   AnkiMobile hoặc Anki.

Đừng import file `.csv` thẳng vào Anki hay AnkiDroid: chúng sẽ biến settings row
thành một card rác. File `.csv` luôn đi qua SheetCards trước.

## Câu lệnh mẫu

Từ vựng tiếng Anh, kiểu **Văn bản**:

```text
Làm 30 từ tiếng Anh chủ đề du lịch, trình độ B1, nghĩa tiếng Việt. Trả lời bằng một khối code. Dòng 1 ghi đúng: #config name=Du lịch B1. Dòng 2: Word [tts=en_US; bold] | IPA [color=muted] | Meaning | Example [italic]. Sau đó mỗi từ một dòng, các cột cách nhau bằng |.
```

Cùng bộ đó, kiểu **Bảng**:

```text
Làm 30 từ tiếng Anh chủ đề du lịch, trình độ B1, nghĩa tiếng Việt, dạng bảng (hoặc file CSV nếu bạn đính kèm được file). Hàng 1: Word | IPA | Meaning | Example. Hàng 2 là settings row: ô đầu ghi đúng #config name=Du lịch B1; tts=en_US; bold, rồi color=muted, một ô trống, italic. Sau đó mỗi từ một hàng.
```

Tiếng Trung, luyện viết chữ:

```text
Đọc hướng dẫn tại %%SITE%%ai.md rồi làm cho tôi 20 chữ Hán HSK 1, kiểu thẻ luyện viết chữ (draw), có pinyin và nghĩa tiếng Việt, mỗi chữ một câu ví dụ ngắn. Tên bộ: HSK 1 viết chữ.
```

Tiếng Nhật, có furigana:

```text
Đọc hướng dẫn tại %%SITE%%ai.md rồi làm cho tôi 25 từ JLPT N5 chủ đề trường học, có furigana cho chữ kanji, nghĩa tiếng Việt và câu ví dụ. Tên bộ: JLPT N5 trường học.
```

Tiếng Hàn cơ bản, dạng bảng:

```text
Đọc hướng dẫn tại %%SITE%%ai.md rồi làm cho tôi file CSV: 20 từ tiếng Hàn sơ cấp về gia đình, có phiên âm Latin, nghĩa tiếng Việt và câu ví dụ, đọc to từ bằng giọng ko_KR. Tên bộ: Tiếng Hàn gia đình.
```

IELTS, điền chỗ trống (cloze):

```text
Đọc hướng dẫn tại %%SITE%%ai.md rồi làm cho tôi bộ cloze: 20 câu IELTS Writing band 6.5, mỗi câu xoá một collocation học thuật, kèm nghĩa tiếng Việt của cả câu. Tên bộ: IELTS collocations.
```

Bạn có thể nói thêm bất cứ gì: số từ, chủ đề, trình độ, muốn gõ đáp án
(*"kiểu Gõ đáp án"*), thẻ hai chiều (*"thẻ hai chiều"*) hay một theme
(*"theme sakura"*). Thiếu thứ tiếng hoặc chủ đề, AI sẽ hỏi lại tối đa hai câu.

## Nếu AI không mở được link

Một số bản miễn phí không đọc được trang web, và AI sẽ nói thế hoặc đoán bừa.
Khi đó:

1. [Tải file `ai.md`](../ai.md) về máy.
2. Đính kèm file vào khung chat (nút kẹp giấy hoặc dấu +), rồi gửi câu lệnh, thay
   *"Đọc hướng dẫn tại …"* bằng *"Đọc file hướng dẫn đính kèm"*.

Không đính kèm được thì mở file, copy toàn bộ nội dung và dán vào trước câu lệnh.

## Thêm từ lần sau

Kiểu **Văn bản**: tự viết thêm từ xuống dưới đoạn chữ trong ghi chú, hoặc dán
đoạn chữ đó cho AI và nhắn *"Thêm 20 từ, giữ nguyên các dòng cũ, dòng #config và
dòng tên cột."* Kiểu **Bảng**: đính kèm file `.csv` lần trước và nhắn:

```text
Đọc hướng dẫn tại %%SITE%%ai.md. Đây là file của tôi. Thêm 20 từ, giữ nguyên các dòng cũ và tên bộ.
```

Giữ nguyên tên bộ (`name=`) và các dòng cũ thì file `.apkg` mới cập nhật đúng
deck cũ và giữ tiến độ ôn; đổi tên bộ là ra một deck mới.

## Có cột ID hay không

Bộ từ AI làm theo kiểu thẻ Học từ vựng **không có cột `ID`**: cột đầu tiên (từ)
là khoá của từng card. Như thế là đủ cho một bộ từ đơn giản, nhưng sửa chính tả
một từ về sau sẽ ra một card mới (tiến độ ôn của từ đó bắt đầu lại).

Nếu bạn định sửa từ về sau, nhắn thêm *"có cột ID"*: AI thêm cột `ID` với `w01`,
`w02`… Khi thêm từ, nó đánh số tiếp và không bao giờ dùng lại một ID. Xem
[Sheet không có cột ID](columns.md#sheet-khong-co-cot-id).

## Lưu ý

- **AI có thể sai**: phiên âm IPA, pinyin, nghĩa hay câu ví dụ đôi khi không
  đúng. Xem từng card trong Sheet to Anki trước khi Download `.apkg`, và sửa
  trong [Tạo Sheet](../sheet/) nếu cần.
- **Từ của bạn được gửi tới công ty làm ra AI đó** (OpenAI, Google hoặc
  Anthropic). SheetCards không nhận gì cả: file được đọc ngay trên trình duyệt của
  bạn.
- AI không được bịa link ảnh hay âm thanh. Muốn có ảnh, hãy tự đưa link cho AI.
- Có cảnh báo trong Sheet to Anki nghĩa là AI viết sai settings row. Gửi lại cảnh
  báo đó cho AI và nhờ nó sửa.
