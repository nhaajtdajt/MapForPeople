# Đưa sản phẩm lên máy chủ

Một ảnh Docker chứa cả máy chủ lẫn giao diện. Mô hình, mạng đường và báo cáo của người dùng nằm trong thư mục `data/` của máy, gắn vào container.

## Lần đầu, trên một máy Ubuntu

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
