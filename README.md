# SheetCards

Flashcard Anki từ bảng tính · Anki flashcards from a spreadsheet.
Website: <https://tannc28.github.io/sheetcards/>

## Tiếng Việt

SheetCards biến một sheet thành flashcard Anki: mỗi dòng là một card, mỗi cột
bạn đặt tên là một field. Một settings row (không bắt buộc) quy định card trông
thế nào, đọc to cột nào và xếp vào deck con nào. Bạn luôn sửa trên sheet; Anki
giữ bản sao.

**[Sheet to Anki](https://tannc28.github.io/sheetcards/create.html)**, dùng trên
điện thoại hay máy tính đều được:

1. Dán link Google Sheets, upload file `.xlsx`/`.csv` (CSV từ Excel tiếng Việt
   cũng đọc được) hoặc mở một share link.
2. Kiểm tra các card, đúng như Anki sẽ hiện.
3. Download `.apkg` rồi mở bằng app Anki (AnkiDroid, AnkiMobile hoặc Anki trên
   máy tính). Sửa sheet rồi import lại: note được cập nhật, tiến độ học vẫn giữ.
   Nếu đã đổi cột, lúc import bật **Merge note types** và chọn **Update notes:
   Always**.

Chưa có sheet? **[Tạo Sheet](https://tannc28.github.io/sheetcards/sheet.html)**
soạn cả sheet trên web: chọn template và theme, đặt tên bộ flashcard, rồi
① Cột & card → ② Thẻ. Lưu bằng **Lưu link sheet** hoặc file `.csv`; template
riêng của bạn nằm ở **Template của bạn**.

Danh tính của một deck là `name=` trong settings row; không có thì lấy từ id của
Google Sheet hoặc tên file. Đổi tên là thành deck mới.

**Add-on** là phần đi kèm, để sync tự động trên máy tính (Anki 25.x trở lên):
tải [`sheetcards.ankiaddon`](https://github.com/tannc28/sheetcards/releases/latest/download/sheetcards.ankiaddon),
vào **Tools → Add-ons → Install from file…**, khởi động lại Anki, rồi
**Tools → SheetCards → Connect a Google Sheet…**. Sheet có `name=` thì add-on và
file `.apkg` nhận cùng một bộ note.

[Docs](https://tannc28.github.io/sheetcards/docs/) ·
[Liên hệ & góp ý](https://tannc28.github.io/sheetcards/contact.html)

## English

SheetCards turns a sheet into Anki flashcards: one row is one card, and every
column you name becomes a field. An optional settings row says how the card
looks, what is read aloud and which subdeck it goes in. You always edit the
sheet; Anki keeps the copy.

**[Sheet to Anki](https://tannc28.github.io/sheetcards/create.html)** works on a
phone or a computer:

1. Paste a Google Sheets link, upload an `.xlsx`/`.csv`, or open a share link.
2. Check the cards, exactly as Anki will show them.
3. Download the `.apkg` and open it in the Anki app (AnkiDroid, AnkiMobile or
   desktop Anki). Edit the sheet and import again: the notes update and your
   progress is kept. If the columns changed, turn on **Merge note types** and set
   **Update notes** to **Always** when importing.

No sheet yet? **[Create sheet](https://tannc28.github.io/sheetcards/sheet.html)**
writes one in the browser: pick a template and a theme, name the flashcard set,
then ① Columns & card → ② Cards. Keep it with **Save sheet link** or as a `.csv`;
your own templates live under **Your templates**.

A deck's identity is the settings row's `name=`; without one, the Google
spreadsheet id or the file name. Renaming a set makes a new deck.

**The add-on** is the companion for automatic sync on a computer (Anki 25.x or
later): download
[`sheetcards.ankiaddon`](https://github.com/tannc28/sheetcards/releases/latest/download/sheetcards.ankiaddon),
open **Tools → Add-ons → Install from file…**, restart Anki, then
**Tools → SheetCards → Connect a Google Sheet…** and **Update Decks from
Sheets…** (`Ctrl+Shift+S`). With `name=` set, the add-on and the `.apkg` recognise
the same notes.

[Docs](https://tannc28.github.io/sheetcards/docs/en/) ·
[Contact & feedback](https://tannc28.github.io/sheetcards/contact.html)

## Example workbook · File ví dụ

Thirty-one sheets, from the simplest to the most advanced, each showing a
feature. Open it in Sheet to Anki or connect it with the add-on:

```text
https://github.com/tannc28/sheetcards/blob/main/examples/sheetcards-examples.xlsx
```

## Developing

Tests, the build and releases: [For developers](https://tannc28.github.io/sheetcards/docs/en/developers.html).

## License

[MIT](LICENSE). SheetCards is not made by or affiliated with Anki or Ankitects.
