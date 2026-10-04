# Spec 04: Chọn kịch bản, phát lại và bàn thử

**Mã theo dõi:** S4.1 (lõi, ngày 3); S4.2 (nên, ngày 6); S4.3 (thêm, ngày 9).

## Mục tiêu

Hôm trình diễn mà trời khô thì bản đồ trực tiếp không có gì để xem. Tính năng này cho phép chuyển cả ứng dụng sang một kịch bản đã lưu: một ngày ngập thật trong quá khứ, một thời điểm quá khứ bất kỳ, hoặc một tình huống giả lập. Nó cũng là công cụ để nhóm tự thử mọi tính năng khác.

Bốn loại kịch bản và điều mỗi loại chứng minh được nằm ở QĐKT mục 4.8. Các bộ tạo kịch bản do người AI viết. Spec này chỉ lo việc chọn, hiển thị, và bảng điều khiển để tạo.

## 1. Chọn kịch bản và phát lại (S4.1)

### 1.1 Ô chọn chế độ

Ô chọn chế độ nằm trong bảng của nút "Lớp" (spec 08). Nó liệt kê "Trực tiếp" và mọi kịch bản của thành phố đang chọn, lấy từ `GET /api/replays`. Mỗi dòng hiện nhãn và một chữ ngắn theo loại:

| `kind` | Chữ kèm theo |
|---|---|
| `recorded-day` | Ngày ngập đã ghi nhận |
| `past-moment` | Mưa thật, thời điểm quá khứ |
| `snapshot` | Điều hệ thống đã thấy |
| `synthetic` | Giả lập |

Đổi thành phố thì ô chọn quay về "Trực tiếp".

### 1.2 Khi một kịch bản được chọn

- Mọi lời gọi `risk`, `units`, `route`, `alerts`, `reports` truyền kèm `replay=<mã>`. Việc này làm ở một chỗ trong `api.ts`, không rải ở từng thành phần.
- Thanh trên hiện một dải chữ, không tắt được:

| Trường hợp | Dải chữ |
|---|---|
| `synthetic` | "GIẢ LẬP, không phải dữ liệu thật" trên nền vàng |
| `recorded-day`, ngày trước 01/01/2025 | "Đang phát lại: {nhãn}. Ngày này nằm trong dữ liệu đã học" |
| Các trường hợp khác | "Đang phát lại: {nhãn}" |

- Đoạn có `recorded` đúng được vẽ nét liền mức cao với nguồn `official`; thẻ giải thích ghi "Ghi nhận ngập ngày đó".
- Dòng "Cập nhật lúc" trong chú thích được thay bằng thời điểm của kịch bản. `stale` luôn sai.
- Giao diện không tự tải lại mỗi 5 phút.

Dòng về ngày trước 2025 là bắt buộc (QĐKT mục 18.3, điểm 1): ghi nhận của những ngày đó đã nằm sẵn trong điểm lịch sử, nên bản phát lại không chứng minh được dự báo đúng.

### 1.3 Máy chủ

- `GET /api/replays?city=` đọc `replay/index.json` và trả `id`, `label`, `kind`, `time`, `recorded_count`. Thư mục chưa tồn tại thì trả danh sách rỗng.
- Mọi endpoint nhận `replay` đều đọc `replay/{id}.parquet` thay cho `risk.parquet`. Mã không có trong `index.json` trả 404.
- Trong bảng kịch bản, đoạn có `reporters` lớn hơn 0 nhận `source` là `report` cùng `reporters` và `reported_level` ghi sẵn. Báo cáo thử gửi trong lúc xem (spec 03) được áp thêm lên trên.
- Danh sách kịch bản được đọc lại từ đĩa mỗi lần gọi, để kịch bản vừa tạo hiện ra mà không phải khởi động lại máy chủ.

## 2. Bàn thử (S4.2)

Bàn thử chỉ tồn tại khi `FLOODRISK_TEST_TOOLS=1`. `GET /api/health` trả `test_tools` để giao diện biết có hiện hay không. Ở bản công khai, biến này để trống và endpoint trả 404.

### 2.1 Bảng điều khiển `TestBench`

Mở từ một nút nhỏ cạnh ô chọn chế độ. Bảng có hai phần:

**Tạo kịch bản giả lập**

| Ô nhập | Giá trị |
|---|---|
| Lượng mưa 3 giờ | Thanh kéo 0 tới 150 mm |
| Triều | Không, đáng kể, lớn. Chỉ hiện ở thành phố có triều |
| Mưa cục bộ ngẫu nhiên | Ô đánh dấu, kèm ô hạt giống |
| Số báo cáo ngẫu nhiên | 0 tới 50 |
| Nhãn | Tự điền, sửa được |

**Lấy dữ liệu thật của một thời điểm quá khứ:** một ô chọn ngày giờ và một ô nhãn.

Sau khi tạo xong, giao diện tải lại danh sách kịch bản và chuyển bản đồ sang kịch bản vừa tạo. Trong lúc chờ, nút hiện "Đang tạo…"; lỗi từ máy chủ hiện nguyên văn trong bảng.

**Điều khiển giao thông cho phiên đang xem:** theo thực tế, thông thoáng, giờ cao điểm, hoặc kẹt cục bộ ngẫu nhiên. Chi tiết ở spec 09, mục 4.

Bảng cũng hiện trạng thái hệ thống lấy từ `/api/health`: dữ liệu mẫu hay thật, phần nào đang là bản giả, tác vụ nền chạy lần cuối lúc nào. Đây là chỗ nhìn nhanh nhất để biết việc nối ghép đã tới đâu.

### 2.2 `POST /api/admin/scenarios`

Nhận một trong hai dạng (KH04 mục H):

- `{"city", "kind": "synthetic", "label", "rain_3h_mm", "rain_24h_mm", "cells": "all" | "random", "tide": "none" | "significant" | "large", "n_reports", "seed"}`
- `{"city", "kind": "past-moment", "label", "when"}`

Gọi `make_synthetic` hoặc `make_past_moment` qua `ports`, rồi trả `{"id": ...}`.

Lỗi: `rain_3h_mm` ngoài khoảng 0–150 trả 422; `n_reports` ngoài 0–50 trả 422; `when` ở tương lai trả 422; lỗi lấy mưa từ Open-Meteo trả 502 kèm lời giải thích.

### 2.3 Sáu kịch bản thử chuẩn

Bảng ở QĐKT mục 4.8. Người AI viết chúng thành kiểm thử tự động cho phần mô hình. Kỹ sư phần mềm chạy lại cả sáu trên giao diện sau mỗi lần nối một phần thật, và ghi kết quả vào mục nghiệm thu bên dưới. Kịch bản thứ sáu (mưa 10 mm và bốn báo cáo "ngập cao") thử luôn spec 03, và kịch bản thứ ba (lộ trình đổi hướng) thử luôn spec 05.

## 3. Liên kết mở đúng trạng thái (S4.3)

Trạng thái của trang được ghi vào phần truy vấn của địa chỉ: `city`, `replay`, `hour`, `from`, `to`, `vehicle`. Mở một liên kết như vậy đưa trang về đúng trạng thái đó.

Lợi ích: bài thuyết trình chứa sẵn các liên kết tới từng bước của kịch bản trình diễn, nên người trình bày không phải thao tác lại từ đầu khi có trục trặc.

Chỉ ghi tọa độ điểm đi và điểm đến mà người dùng đã chủ động chọn trên bản đồ. Vị trí lấy từ định vị của trình duyệt không được ghi vào địa chỉ.

## 4. Chỗ đang dùng bản giả

| Cần | Bản giả | Bản thật đến khi nào |
|---|---|---|
| Kịch bản để chọn | `2024-10-18` (ngày ghi nhận mẫu) và một kịch bản `synthetic` mẫu của `devdata` | Trưa ngày 3 |
| `make_synthetic`, `make_past_moment` | `fakes` qua `ports`; nhãn có đuôi "(bản giả)" | Ngày 3 |

Kịch bản do bản giả tạo ra nằm trong `data/sample/`, không bao giờ nằm trong thư mục dữ liệu thật.

## 5. Nghiệm thu

**S4.1:**

- [ ] Ô chọn chế độ liệt kê "Trực tiếp" và hai kịch bản mẫu.
- [ ] Chọn kịch bản `2024-10-18`: hai đoạn `recorded` vẽ nét liền mức cao; dải chữ ghi cả câu "Ngày này nằm trong dữ liệu đã học".
- [ ] Chọn kịch bản `synthetic` mẫu: dải chữ "GIẢ LẬP, không phải dữ liệu thật"; một đoạn ghi "4 người đã báo".
- [ ] Mã kịch bản lạ trả 404 ở cả `risk`, `units`, `route`, `alerts`.
- [ ] Đổi thành phố đưa ô chọn về "Trực tiếp".

**S4.2:**

- [ ] Với `FLOODRISK_TEST_TOOLS` để trống, endpoint trả 404 và giao diện không có nút bàn thử.
- [ ] Tạo kịch bản mưa 80 mm từ bàn thử: bản đồ tự chuyển sang kịch bản mới và các đoạn có lịch sử đổi màu.
- [ ] `rain_3h_mm` bằng 500 trả 422; `when` ở tương lai trả 422.
- [ ] Bảng trạng thái hệ thống khớp với `/api/health`.
- [ ] Sáu kịch bản thử chuẩn cho đúng kết quả trên giao diện, với các bộ tạo thật của người AI. Ghi ngày chạy: ……

**S4.3:**

- [ ] Chép địa chỉ đang mở sang một thẻ trình duyệt mới cho đúng thành phố, kịch bản, giờ và lộ trình.
- [ ] Địa chỉ không chứa tọa độ lấy từ định vị.

## 6. Không làm

- Không viết bộ tạo kịch bản thật. Đó là `floodrisk/model/scenarios.py` của người AI.
- Không cho tạo kịch bản `recorded-day` và `snapshot` từ giao diện. Hai loại này cần người AI chọn ngày bằng dòng lệnh.
- Không có nút xóa kịch bản trên giao diện. Xóa bằng cách xóa file và dòng trong `index.json`.
