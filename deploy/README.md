# Đưa sản phẩm lên máy chủ

Một ảnh Docker chứa cả máy chủ lẫn giao diện, kèm mô hình và mạng đường của TP.HCM.

## Cách nhanh nhất: Render

1. Đăng nhập [render.com](https://render.com) bằng tài khoản GitHub có repo này.
2. Bấm **New** > **Blueprint**, chọn repo `MapForPeople`. Render đọc file `render.yaml` ở nhánh `web`.
3. Render hỏi giá trị của năm khóa: `GOONG_API_KEY`, `VITE_GOONG_MAP_KEY`, `GEMINI_API_KEY`, `GEMINI_API_KEY_2`, `GEMINI_API_KEY_3`. Chép từ file `.env` trên máy mình. Khóa Gemini nào chưa có thì để trống.
4. Bấm **Apply**. Lần dựng đầu mất khoảng 5 tới 10 phút. Xong thì có đường dẫn dạng `https://mapforpeople.onrender.com`, đã có HTTPS.

Ba điều cần biết về gói miễn phí của Render:

- Máy ngủ sau 15 phút không ai vào; lần mở kế tiếp mất khoảng một phút để thức dậy. Trước khi trình diễn, mở trang trước vài phút.
- Bộ nhớ 512 MB. Máy chủ của ta dùng đỉnh khoảng 370 MB (đo trên máy cá nhân). Nếu Render báo hết bộ nhớ thì đổi sang gói có 2 GB.
- Không có ổ đĩa giữ lại: báo ngập của người dùng mất mỗi khi máy khởi động lại hoặc dựng lại.

Đổi mã thì chỉ cần push lên nhánh `web`, Render tự dựng lại.

### Mức của mô hình trên Render

Open-Meteo từ chối máy của Render (lỗi 429, vì Render dùng chung địa chỉ mạng), nên máy chủ ở đó không tự tính được trạng thái mưa của mô hình. Một máy ở Việt Nam tính hộ rồi đẩy lên:

1. Đặt cùng một giá trị cho biến `RISK_PUSH_TOKEN` trên Render (mục Environment) và trong `.env` của máy tính hộ.
2. Trong `.env` của máy tính hộ, đặt `RISK_PUSH_URL=https://mapforpeople.onrender.com`.
3. Chạy `python tools/ghi_du_lieu.py` trên máy đó. Mỗi 10 phút nó tính mức và đẩy lên; việc này cũng giữ cho máy Render không ngủ.

Máy tính hộ tắt thì bản trên mạng vẫn có mức từ trạm mưa, mực nước Phú An và báo cáo, và ghi rõ trạng thái mưa của mô hình là số liệu cũ hoặc chưa có.

## Tự chạy trên một máy Ubuntu

Mô hình, mạng đường và báo cáo của người dùng nằm trong thư mục `data/` của máy, gắn vào container.

```bash
# 1. Cài Docker
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER   # rồi đăng xuất và đăng nhập lại

# 2. Lấy mã (nhánh web đã chứa data/model và data/processed/hcm)
git clone -b web https://github.com/nhaajtdajt/MapForPeople.git
cd MapForPeople

# 3. Tạo file .env từ mẫu rồi điền khóa
cp .env.example .env
nano .env

# 4. Dựng và chạy
docker compose up -d --build
```

Các biến trong `.env`:

| Biến | Dùng cho |
|---|---|
| `GOONG_API_KEY` | Tìm địa điểm và tìm đường (chỉ máy chủ dùng) |
| `VITE_GOONG_MAP_KEY` | Ô bản đồ nền; được đưa vào giao diện lúc dựng ảnh |
| `GEMINI_API_KEY`, `GEMINI_API_KEY_2`, ... | Gemini đọc camera, xoay vòng khi một khóa hết hạn mức |
| `SITE_DOMAIN` | Tên miền, chỉ cần khi bật HTTPS |
| `APP_PORT` | Cổng trên máy, mặc định 8000 |

Mở `http://<địa chỉ máy>:8000`. Kiểm nhanh:

```bash
curl -s http://localhost:8000/api/health
curl -s "http://localhost:8000/api/risk?city=hcm" | head -c 400
```

`/api/risk` phải trả `"stale": false`. Nếu nó báo lỗi về trạm mưa hoặc camera thì máy chủ không vào được cổng số liệu trong nước; khi đó mức nguy cơ vẫn có (từ mô hình), chỉ thiếu phần nâng mức theo trạm mưa, triều và camera.

## HTTPS

Nút "Vị trí của tôi" chỉ chạy trên trang HTTPS. Trỏ tên miền về địa chỉ của máy, mở cổng 80 và 443, đặt `SITE_DOMAIN=ten-mien-cua-ban` trong `.env`, rồi:

```bash
docker compose --profile https up -d --build
```

## Cập nhật

```bash
git pull
docker compose up -d --build
```

Thư mục `data/` không bị đụng tới khi dựng lại: báo cáo của người dùng (`data/reports.sqlite`) và bản tính gần nhất được giữ nguyên.

## Chạy thử trên máy cá nhân

Cùng lệnh `docker compose up --build`. Nếu cổng 8000 đang bận thì đặt `APP_PORT=8010` trong `.env`.
