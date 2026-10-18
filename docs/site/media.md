# Hình ảnh, âm thanh và video

Một ô có thể chứa link tới một hình ảnh, một file âm thanh hoặc một video. Đánh
dấu cột là `image`, `audio` hoặc `video` trong [settings row](settings-row.md),
và card sẽ hiện thứ mà link trỏ tới thay vì hiện địa chỉ.

| Ô của cột trong settings row | Card hiện gì |
| :--- | :--- |
| `image; size=320` | Hình ảnh, rộng tối đa 320 px |
| `audio` | Một trình phát âm thanh, nghe lại được |
| `video; size=480` | Trình phát video của chính trang đó, rộng tối đa 480 px |

Các ô ở những dòng dữ liệu **chỉ chứa link**, không gì khác. Mỗi cột chỉ chứa
một loại media; `image; video` sẽ giữ `image` và báo cảnh báo.

## Video: dán link từ thanh địa chỉ

Ghi `video` rồi dán đúng cái trình duyệt đang hiện. Khi card được tạo (lúc sync
bằng add-on, hoặc trong Sheet to Anki), địa chỉ được đổi thành địa chỉ trình phát
của trang đó:

| Bạn dán | Nó thành |
| :--- | :--- |
| `youtube.com/watch?v=ID`, `youtu.be/ID`, `youtube.com/shorts/ID`, `youtube.com/live/ID` | `youtube.com/embed/ID` |
| `youtu.be/ID?t=1m30s` | `youtube.com/embed/ID?start=90` (giữ thời điểm bắt đầu) |
| `drive.google.com/file/d/ID/view?usp=sharing`, `drive.google.com/open?id=ID` | `drive.google.com/file/d/ID/preview` |
| `vimeo.com/123456789` | `player.vimeo.com/video/123456789` |
| `example.com/lesson.mp4` | giữ nguyên; file trực tiếp cũng phát được |

Link không trỏ tới một video cụ thể (một channel, một playlist, một thư mục
Drive) sẽ được giữ nguyên và báo cảnh báo, vì nó sẽ hiện lỗi ở chỗ lẽ ra là
video.

Trên AnkiDroid và AnkiMobile, YouTube không cho phát trong card được mở từ chính
điện thoại. Vì vậy card video đi qua một trang player nhỏ trên site này, trang đó
phát video ngay trong card trên điện thoại, và còn hiện một link thường bên dưới
khung, phòng khi trang đó không truy cập được. Chữ của link là `label` của cột,
nếu cột có `label`.

## Cần biết

- **Link cần có mạng.** Hình ảnh hay video được tải lại mỗi lần card hiện ra,
  nên khi offline sẽ trống, và app trên điện thoại khắt khe hơn bản máy tính
  trong việc tải nội dung từ xa. Với deck phải chạy được offline, hãy đặt file
  vào thư mục media của Anki và dùng theo cách thông thường của Anki.
- **Hình dán thẳng vào ô không phải là link.** Google Sheets lưu nó như một hình
  vẽ, và Anki không lấy được. Hãy tải hình lên chỗ nào có link (Google Drive,
  Wikimedia Commons, một repository GitHub) rồi đặt link đó vào ô.
- **Các setting về chữ không áp dụng cho media.** `color`, `bold`, `italic` và
  `align` riêng của cột bị bỏ qua trên cột media, kèm cảnh báo. `size` đặt chiều
  rộng (1–2000), và video giữ tỉ lệ 16 : 9. `size` trên `audio` bị từ chối.
- **`tts` và `furigana` bị từ chối** trên cột media, vì chúng sẽ tác động lên
  địa chỉ: card sẽ đọc to cái link.
- **`hint`** giấu hình hoặc trình phát sau một cú bấm.
- **Quên ghi `image`?** Một cột mà phần lớn ô trông như link ảnh sẽ có cảnh báo
  *trông như link ảnh — thêm `image`*, vì không có nó card chỉ in cái link ra.
