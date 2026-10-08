# Ghi chú 13: Bản chạy được ngày 08/10

Viết chiều 08/10/2026 để nhóm biết ứng dụng đang làm được gì, mở nó thế nào, và chỗ nào chưa kiểm. Mã nằm trên nhánh `web`.

## 1. Mở ứng dụng

Trên máy cá nhân, từ gốc repo, sau khi có file `.env` (xem `.env.example`):

```
.venv\Scripts\python.exe -m floodrisk.api.dev --real
node web/node_modules/vite/bin/vite.js web --port 5173 --strictPort
```

rồi mở `http://localhost:5173`. Đưa lên mạng: xem `deploy/README.md` (Render, hoặc Docker trên một máy Ubuntu).

## 2. Ứng dụng làm được gì

| Việc | Cách xem | Nguồn |
|---|---|---|
| Mức nguy cơ ngập của từng tuyến | Đường tô cam (mức vừa) và đỏ (mức cao); nét đậm là tuyến từng ngập | Hai mô hình của repo `flood_prediction_models`, tính lại mỗi giờ. Đã so với `run_hourly.py` gốc: 0 trên 140.236 tuyến lệch |
| Trạm mưa và triều nâng mức | Dòng trạng thái dưới ô tìm kiếm ghi mưa, triều và mực nước Phú An | 44 trạm mưa và trạm Phú An trên vndms.gov.vn, đọc mỗi 10 phút; tuyến trong 5 km quanh trạm mưa to được nâng mức |
| 102 điểm ngập CSGT công bố 06/10 | Chấm xanh dương (mưa) và xanh lục (triều) | Danh sách PC08, định vị bằng `tools/doi_chieu_122_diem.py` |
| Camera giao thông | Phóng gần, chạm chấm xám để xem ảnh; nút "Nhờ Gemini đọc ảnh này" | Cổng giao thông TP.HCM, 796 camera; Gemini 3.5 Flash, dự phòng 3.1 Flash-Lite |
| Báo ngập một chạm | Chạm một điểm, "Báo ngập ở đây", chọn một trong bốn mức | Lưu vào `data/reports.sqlite`, hết hiệu lực sau 90 phút |
| Tìm đường có soi ngập | "Chỉ đường tới đây"; mỗi lộ trình ghi số mét qua đường đang có báo ngập hoặc từng ngập | Lộ trình chính của Goong; thêm đường tránh ngập do hệ thống tự tính khi nó né được nhiều hơn |

Thứ tự bằng chứng khi tìm đường (ghi chú 11, quyết định 5): đường đang có người hoặc camera báo ngập vừa trở lên bị né mạnh nhất; đường từng ngập mà hôm nay mưa hoặc triều đang ở mức cảnh giác bị né vừa; đường chỉ do mô hình xếp hạng thì chỉ ghi nhận, không làm đổi đề xuất.

## 3. Đã kiểm bằng cách nào

- 119 bài kiểm thử Python và 39 bài kiểm thử web đều qua.
- Trên máy chủ thật: báo ngập một tuyến rồi tìm đường lại thì lộ trình đề xuất đổi và không còn qua tuyến đó; Gemini đọc một camera mất khoảng 50 giây và ghi kết quả thành báo cáo.
- Chiều đường: 6 đường một chiều quen thuộc đúng chiều thật; 40 đoạn hai chiều ngẫu nhiên trong nội thành, Goong cũng cho đi hai chiều (`tools/tim_duong_mot_chieu_thieu.py`).

## 4. Chưa kiểm hoặc còn thiếu

| Việc | Tình trạng |
|---|---|
| Gemini đọc cảnh ngập thật | Chưa có ảnh ngập nào. Ngày 08/10 các trạm mưa to đều ở ngoại thành, không camera nào trong 3 km |
| Ảnh Docker | Chưa dựng thử lần nào (Docker trên máy phát triển đang tắt) |
| Máy chủ ở nước ngoài có vào được cổng camera và cổng trạm mưa không | Chưa biết |
| Thẻ camera, màu tuyến được nâng mức, chữ "Đi" và "Đến" | Mã qua kiểm tra kiểu, luồng báo ngập đã thử trên trang; phần hình chưa được nhìn lại sau khi gộp nhánh tìm đường |
| Đà Nẵng, chế độ phát lại, giao thông, cảnh báo sớm | Chưa làm |
| Ba con số 5 km, 1,40 m, 1,50 m và các hệ số phạt khi tìm đường | Do người làm web đặt, chưa hiệu chỉnh |

## 5. Bộ ghi dữ liệu

`tools/ghi_du_lieu.py` chạy từ 12:02 ngày 08/10 trên máy phát triển, mỗi 10 phút ghi radar, mưa 44 trạm, triều Phú An và ảnh camera vào `data/raw/live/`. Từ 16:57 danh sách ghi là 167 camera: 115 camera sát tuyến từng ngập và 52 camera trong 250 m quanh điểm ngập CSGT (21 camera sát điểm triều). Các buổi chiều 10 tới 13/10 có triều cường; ảnh ghi được dùng để kiểm Gemini với cảnh ngập thật.
