# Góp ý trên web: cài đặt một lần (~15 phút)

Trang **Liên hệ & góp ý** của web có một form ngay trên trang. Người gửi phải
**đăng nhập bằng Google** trước khi gửi. Góp ý được ghi vào **Google Sheet của
bạn**, ảnh chụp màn hình vào **Google Drive của bạn**, và bạn nhận **email báo**
mỗi lần có góp ý mới.

Không có máy chủ nào khác: web gửi góp ý tới một Google Apps Script chạy bằng
tài khoản của bạn. Script hỏi Google để kiểm tra người gửi đã đăng nhập thật
(email đã được Google xác minh) rồi mới ghi. Không ai giả được email.

Bạn làm hai việc, rồi gửi lại **hai giá trị**: `Client ID` và `link web app`.

---

## Bước 1 — Tạo OAuth Client ID (cho nút "Đăng nhập bằng Google")

1. Mở <https://console.cloud.google.com/> bằng tài khoản Google của bạn.
2. Góc trên bên trái → **Select a project** → **New project** → tên `SheetCards`
   → **Create**. Chọn project vừa tạo.
3. Menu ☰ → **APIs & Services** → **OAuth consent screen** (có thể hiện là
   **Google Auth Platform → Branding**):
   - **App name**: `SheetCards`
   - **User support email**: email của bạn
   - **Audience / User type**: **External**
   - **Developer contact**: email của bạn → **Save**.
   - **Quan trọng:** ở mục **Audience** (hoặc **Publishing status**) bấm
     **Publish app** → **In production**. Nếu để *Testing*, chỉ những email bạn
     thêm tay mới đăng nhập được. Web chỉ xin `email` và `profile`, nên
     **không cần** Google duyệt app.
4. **APIs & Services** → **Credentials** (hoặc **Clients**) → **Create
   credentials** → **OAuth client ID**:
   - **Application type**: **Web application**
   - **Name**: `SheetCards web`
   - **Authorized JavaScript origins** → **Add URI**:
     - `https://tannc28.github.io`
     - `http://localhost` (để thử trên máy)
     - `http://localhost:8000`
   - Để trống *Authorized redirect URIs* → **Create**.
5. Sao chép **Client ID** (dạng `1234…-abc….apps.googleusercontent.com`).
   Đây là mã **công khai**, không phải mật khẩu, nên gửi cho mình qua chat được.

## Bước 2 — Tạo Google Sheet nhận góp ý + Apps Script

1. Mở <https://sheets.new> → đặt tên file `Góp ý SheetCards`.
2. **Extensions** (Tiện ích mở rộng) → **Apps Script**.
3. Xoá hết code mẫu, dán toàn bộ nội dung file `tools/feedback/Code.gs`.
4. Ở dòng `const CLIENT_ID = "…"`, thay bằng Client ID ở Bước 1.
5. Bấm 💾 **Save**. Ở thanh trên, chọn hàm **`setup`** → **Run**.
   - Google sẽ hỏi quyền (Sheets, Drive, gửi email, gọi URL ngoài) → chọn tài
     khoản của bạn → **Advanced** → **Go to … (unsafe)** → **Allow**.
     Màn hình "unsafe" chỉ vì script do chính bạn viết, chưa qua Google duyệt.
   - Xong, Sheet sẽ có tab **Góp ý** với hàng tiêu đề, và Drive có thư mục
     **SheetCards — ảnh góp ý**.
6. **Deploy** → **New deployment** → biểu tượng ⚙ → **Web app**:
   - **Description**: `feedback`
   - **Execute as**: **Me**
   - **Who has access**: **Anyone**
   - **Deploy** → sao chép **Web app URL** (dạng
     `https://script.google.com/macros/s/…/exec`).
7. Kiểm tra: mở link đó trên trình duyệt, phải thấy
   `{"ok":true,"service":"sheetcards-feedback"}`.

"Anyone" nghĩa là ai cũng *gọi* được địa chỉ này, nhưng script từ chối mọi yêu
cầu không mang theo lần đăng nhập Google hợp lệ của chính web SheetCards.

## Gửi lại cho mình

- `Client ID`
- `Web app URL`

## Về sau

- **Xem góp ý:** mở Sheet `Góp ý SheetCards`. Mỗi email báo có nút trả lời
  thẳng cho người gửi.
- **Sửa script:** sửa code → **Deploy** → **Manage deployments** → ✏️ →
  **Version: New version** → **Deploy**. Link web app giữ nguyên.
- **Giới hạn:** mỗi người tối đa 5 góp ý trong 10 phút; ảnh ≤ 4 MB
  (png/jpg/webp/gif); Apps Script gửi tối đa 100 email/ngày với tài khoản
  Gmail thường.
