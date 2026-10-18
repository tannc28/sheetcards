# Tạo bộ từ bằng AI

ChatGPT, Gemini và Claude soạn được cả bộ từ cho bạn. Bạn đưa cho AI link hướng
dẫn của SheetCards và nói bạn muốn học gì; AI gửi lại một file `.csv` mở được
ngay trong SheetCards, có sẵn settings row nên card đã đẹp.

Hướng dẫn cho AI nằm ở đây, bằng tiếng Anh vì AI làm theo tiếng Anh tốt nhất:

```text
https://tannc28.github.io/sheetcards/ai.md
```

## Các bước

1. **Copy một câu lệnh** ở dưới, sửa phần trong ngoặc theo ý bạn.
2. **Dán vào ChatGPT, Gemini hoặc Claude** rồi gửi.
3. **Nhận file `.csv`.** Nếu AI chỉ in ra một khối chữ, nhắn thêm: *"Gửi dưới
   dạng file .csv để tôi tải về."*
4. **Mở file trong SheetCards**: vào [Sheet to Anki](../create/), bấm **Mở file
   .xlsx/.csv** và chọn file. Muốn sửa vài từ trước thì mở bằng
   [Tạo Sheet](../sheet/) cũng bằng nút **Mở file .xlsx/.csv**.
5. **Xem từng card**, rồi bấm **Download `.apkg`** và mở file đó bằng AnkiDroid,
   AnkiMobile hoặc Anki.

Đừng import file `.csv` thẳng vào Anki hay AnkiDroid: chúng sẽ biến settings row
thành một card rác. File `.csv` luôn đi qua SheetCards trước.

## Câu lệnh mẫu

Từ vựng tiếng Anh:

```text
Đọc hướng dẫn tại https://tannc28.github.io/sheetcards/ai.md rồi tạo cho tôi file CSV: 30 từ tiếng Anh chủ đề du lịch, trình độ B1, kiểu thẻ Học từ vựng, nghĩa tiếng Việt, có câu ví dụ. Tên bộ: Du lịch B1.
```

Tiếng Trung, luyện viết chữ:

```text
Đọc hướng dẫn tại https://tannc28.github.io/sheetcards/ai.md rồi tạo cho tôi file CSV: 20 chữ Hán HSK 1, kiểu thẻ luyện viết chữ (draw), có pinyin và nghĩa tiếng Việt, mỗi chữ một câu ví dụ ngắn. Tên bộ: HSK 1 viết chữ.
```

Tiếng Nhật, có furigana:

```text
Đọc hướng dẫn tại https://tannc28.github.io/sheetcards/ai.md rồi tạo cho tôi file CSV: 25 từ JLPT N5 chủ đề trường học, có furigana cho chữ kanji, nghĩa tiếng Việt và câu ví dụ. Tên bộ: JLPT N5 trường học.
```

Tiếng Hàn cơ bản:

```text
Đọc hướng dẫn tại https://tannc28.github.io/sheetcards/ai.md rồi tạo cho tôi file CSV: 20 từ tiếng Hàn sơ cấp về gia đình, có phiên âm Latin, nghĩa tiếng Việt và câu ví dụ, đọc to từ bằng giọng ko_KR. Tên bộ: Tiếng Hàn gia đình.
```

IELTS, điền chỗ trống (cloze):

```text
Đọc hướng dẫn tại https://tannc28.github.io/sheetcards/ai.md rồi tạo cho tôi file CSV kiểu cloze: 20 câu IELTS Writing band 6.5, mỗi câu xoá một collocation học thuật, kèm nghĩa tiếng Việt của cả câu. Tên bộ: IELTS collocations.
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

Đính kèm file `.csv` lần trước và nhắn:

```text
Đọc hướng dẫn tại https://tannc28.github.io/sheetcards/ai.md. Đây là file của tôi. Thêm 20 từ, tiếp tục ID, giữ nguyên tên bộ.
```

Giữ nguyên ID và tên bộ (`name=`) thì file `.apkg` mới cập nhật đúng deck cũ và
giữ tiến độ ôn; đổi tên bộ là ra một deck mới. Xem
[ID của từng từ](columns.md) nếu muốn biết vì sao.

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
