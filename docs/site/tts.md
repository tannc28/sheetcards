# Text to speech

`tts=` trên một cột khiến Anki đọc to cột đó bằng các giọng có sẵn trên máy của
bạn (text to speech, tức chuyển chữ thành giọng nói):

```text
ID       Word                 Meaning
#config  tts=en_US            size=20
1        library              thư viện
```

Từ được đọc khi mặt chứa nó hiện ra, và có một nút để nghe lại.

## Mã ngôn ngữ phải đầy đủ

Ghi mã đầy đủ: **`en_US`, `zh_CN`, `ja_JP`, `ko_KR`, `de_DE`, `pt_BR`**. Ghi
`zh-CN` cũng được. Mã ngắn như `zh` sẽ **bị từ chối kèm cảnh báo**: Anki so mã
này với các giọng đã cài một cách chính xác tuyệt đối, nên `zh` không khớp giọng
nào và chỉ phát ra im lặng. Đoán thay cũng không an toàn: `zh_CN` sẽ sai với
người học tiếng Trung phồn thể (`zh_TW`).

## Chọn giọng và tốc độ

- **`voices=`** ghi tên các giọng bạn muốn, cách nhau bằng dấu phẩy:
  `tts=zh_CN; voices=Huihui,Yaoyao`. Đây chỉ là ưu tiên: nếu máy không có giọng
  nào trong số đó, Anki dùng bất kỳ giọng nào của ngôn ngữ đó. Nhờ vậy cùng một
  sheet chạy được cả trên máy tính lẫn điện thoại.
- **`speed=`** đặt tốc độ đọc, từ 0.5 đến 2.0. Ghi trong ô `#config` thì nó là
  mặc định cho mọi cột được đọc.

## Tìm các giọng có trên máy

Máy nào có giọng nào là tuỳ vào thiết bị bạn dùng để review, và điện thoại
thường có giọng khác với máy tính. Vì vậy **mỗi card có cột được đọc đều mang một
mục "TTS voices" nhỏ, thu gọn, ở mặt trả lời**. Mở nó trên thiết bị bạn học để
xem:

- các giọng thiết bị đó có cho ngôn ngữ của bạn, các giọng nghe tự nhiên
  *Premium* và *Enhanced* đứng đầu;
- mỗi giọng được viết sẵn đúng cách ghi vào sheet (`voices=…`), copy là dùng
  được;
- nếu không có giọng nào khớp, danh sách mã ngôn ngữ mà thiết bị có, để bạn thấy
  có phải mã `tts=` của bạn là vấn đề không.

Trên điện thoại mỗi giọng có một nút play để nghe thử trước. Các giọng đùa
(Zarvox, Bells, Bubbles và những giọng tương tự) bị bỏ ra, còn các giọng nhân vật
dùng chung cho mọi ngôn ngữ (Eddy, Flo, Grandma…) được gom sau một nút bấm.

## Cài giọng đọc

Ngôn ngữ chưa cài giọng nào sẽ **im lặng, không báo lỗi gì**: sheet không sai,
chỉ là thiết bị thiếu giọng.

- **Windows:** Settings → Time & Language → Speech.
- **macOS:** System Settings → Accessibility → Spoken Content.
- **iPhone và iPad:** Settings → Accessibility → Spoken Content → Voices.
- **Android:** phần cài đặt text-to-speech của điện thoại, nằm trong
  Accessibility hoặc Languages.

## Cần biết

- **Một ô, một ngôn ngữ.** Anki đọc cả field bằng một giọng, nên ô chứa một câu
  tiếng Trung kèm bản dịch tiếng Anh sẽ bị đọc toàn bộ bằng tiếng Trung. Hãy để
  mỗi ngôn ngữ một cột, mỗi cột có `tts=` riêng.
- **Ô trống thì không được đọc.**
- **`hint` giấu chữ, không giấu tiếng.** Cột có cả `hint` và `tts` vẫn được đọc
  khi mặt của nó hiện ra.
- **`furigana` đi cùng `tts` thì đọc phần phiên âm.** Trên cột furigana, giọng
  đọc được đưa phần phiên âm trong ngoặc vuông, nên `日本語[にほんご]` được đọc
  một lần, và đọc đúng.
- **Nghe được nhưng không hiện:** `side=hide; tts=…` đọc một cột mà không in nó
  lên card; xem [settings row](settings-row.md#nghe-duoc-nhung-khong-hien-sidehide-voi-tts).
