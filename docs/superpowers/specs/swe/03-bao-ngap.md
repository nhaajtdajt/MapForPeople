# Spec 03: Báo ngập một chạm

**Mã theo dõi:** S3. **Ưu tiên:** lõi. **Ngày:** 4.

## Mục tiêu

Người đang đứng ở một đoạn đường ngập báo được tình trạng trong hai lần chạm, không cần đăng nhập. Báo cáo đó sửa ngay mức nguy cơ của đoạn cho mọi người khác, và bản đồ ghi "4 người đã báo" để người chưa tới biết thông tin đáng tin tới đâu.

## 1. Hành vi

### 1.1 Cách mở bảng báo ngập

- Mục "Báo ngập" ở thanh dưới: dùng vị trí hiện tại của người dùng. Nếu trình duyệt không cho định vị, bảng nhắc "Chạm vào đoạn đường trên bản đồ, rồi chọn Báo ngập ở đây".
- Nút "Báo ngập ở đây" trong thẻ địa điểm (spec 08): dùng điểm đang được ghim. Đây là cách báo cho một điểm tự chọn.
- Nút "Báo tình trạng ở đây" trong thẻ giải thích: dùng điểm giữa của đoạn đó.

Trình duyệt không cho định vị trên trang HTTP, nên trước khi có HTTPS (ngày 4) thì cách thứ hai và thứ ba là cách chính trên máy chủ. Trong các kịch bản phát lại cũng vậy, vì người trình diễn không đứng ở chỗ ngập.

### 1.2 Bảng báo ngập

Bảng `ReportSheet` hiện tên đường được gán và bốn nút lớn:

| Nút | `status` gửi lên | Ý nghĩa với người dùng |
|---|---|---|
| Không ngập | `clear` | Đường khô hoặc chỉ ướt |
| Ngập nhẹ | `light` | Dưới 10 cm, xe máy đi bình thường |
| Ngập vừa | `medium` | 10 tới 30 cm, tới bô xe máy |
| Ngập cao | `high` | Trên 30 cm, xe máy dễ chết máy |

Ba khoảng độ sâu này trùng với `depth_class` ở QĐKT mục 5.

Sau khi chạm một nút, bảng hiện kết quả: tên đường, mức mới của đoạn, và "N người đã báo trong 30 phút qua". Lớp nguy cơ được tải lại để đoạn đó đổi sang nét liền.

### 1.3 Mã người báo

Lần đầu mở trang, trình duyệt tự sinh một mã ngẫu nhiên và lưu trong `localStorage`. Mã này chỉ dùng để một người không được đếm hai lần. Nó không gắn với tên, số điện thoại hay tài khoản nào.

### 1.4 Khi đang xem một kịch bản

Báo cáo vẫn được nhận, để trình diễn được khi trời khô. Nó được lưu kèm mã kịch bản, chỉ có tác dụng khi xem đúng kịch bản đó, và không bao giờ lọt vào chế độ trực tiếp (QĐKT mục 18.3, điểm 6). Bảng kết quả ghi thêm chữ "báo cáo thử".

## 2. Máy chủ

### 2.1 `POST /api/reports`

Nhận `city`, `lat`, `lon`, `status`, `reporter`, và `replay` tùy chọn.

1. Tìm đoạn gần nhất trong 60 m quanh điểm gửi lên. Không có đoạn nào thì trả 404 với lời giải thích "Không có đoạn đường nào trong 60 m quanh điểm này".
2. Lưu báo cáo. **Tọa độ không được lưu;** nó chỉ dùng cho bước 1.
3. Gọi `apply_evidence` qua `ports` với mọi báo cáo còn hiệu lực của đoạn đó.
4. Trả về `unit_id`, `name`, `level`, `risk`, `reporters`, `reported_level`.

Lỗi: `status` lạ trả 422; điểm ngoài khung thành phố trả 422; cùng một `reporter` gửi quá 20 báo cáo trong 10 phút trả 429 với lời "Bạn đã báo quá nhiều lần, thử lại sau ít phút". Giới hạn này đủ rộng để người dùng sửa lại một lần chạm nhầm, và đủ hẹp để một đoạn mã không bơm được hàng nghìn báo cáo.

### 2.2 Lưu trữ

Một file SQLite `reports.sqlite` trong thư mục dữ liệu, hai bảng:

| Bảng | Cột | Ghi chú |
|---|---|---|
| `reports` | `id`, `city`, `unit_id`, `status`, `reporter`, `at` (giây Unix), `official`, `replay` (rỗng ở chế độ trực tiếp) | Không có cột tọa độ |
| `report_hours` | `city`, `unit_id`, `hour`, `status`, `n` | Bảng tổng hợp, không có mã người báo |

Mỗi lần thêm một báo cáo, máy chủ gọi `purge`: các báo cáo cũ hơn 24 giờ được cộng vào `report_hours` rồi xóa. Báo cáo thử của các kịch bản bị xóa mà không cộng vào bảng tổng hợp.

### 2.3 Quy tắc bằng chứng

Quy tắc đầy đủ ở QĐKT mục 4.7 và do người AI viết trong `evidence.py`. Phần web chỉ cần biết: nó đưa vào nguy cơ trước khi có báo cáo cùng danh sách báo cáo, và nhận lại nguy cơ mới, số người đã báo, mức được báo. Bằng chứng chỉ áp dụng cho giờ hiện tại.

## 3. Chỗ đang dùng bản giả

| Cần | Bản giả | Bản thật đến khi nào |
|---|---|---|
| `Report`, `apply_evidence` | `fakes` qua `ports`: cộng 0,15 mỗi người báo, không giảm theo thời gian | Hết ngày 1 |
| Đoạn đường để gán | Tám đường mẫu | Trưa ngày 2 |

Vì bản giả không giảm trọng số theo thời gian, đừng viết kiểm thử nào dựa vào con số nguy cơ cụ thể sau báo cáo. Chỉ khẳng định mức, số người báo và mức được báo.

## 4. Nghiệm thu

- [ ] Ghim một điểm trên một đường mẫu, bấm "Báo ngập ở đây", chọn "Ngập cao": bảng kết quả ghi mức cao và "1 người đã báo"; đoạn đó chuyển sang nét liền.
- [ ] Bốn mã người báo khác nhau cùng báo "Ngập cao" trên một đoạn mức thấp: đoạn lên mức cao và ghi "4 người đã báo".
- [ ] Cùng một người báo hai lần trên một đoạn: vẫn ghi "1 người đã báo", và mức được báo là mức của lần sau.
- [ ] Điểm cách mọi đoạn hơn 60 m trả 404, giao diện hiện lời giải thích thay vì im lặng.
- [ ] Bảng `reports` không có cột `lat`, `lon`. Có kiểm thử đọc lược đồ bảng để giữ điều này.
- [ ] Sau `purge`, báo cáo 25 giờ tuổi biến mất và `report_hours` có đúng một dòng với `n` bằng số báo cáo đã gộp.
- [ ] Báo cáo gửi lúc đang xem kịch bản mẫu không xuất hiện khi chuyển về "Trực tiếp", và ngược lại.
- [ ] Báo cáo thứ 21 trong 10 phút từ cùng một mã trả 429.
- [ ] Ở `hour=1`, đoạn vừa được báo vẫn giữ mức dự báo cũ.

## 5. Không làm

- Không nhận ảnh. Việc đọc ảnh người dùng gửi đã được để sau hackathon.
- Không có tài khoản, không có điểm uy tín của người báo.
- Không lưu tọa độ, kể cả dưới dạng làm tròn.
- Không có trang quản trị để duyệt báo cáo. Trọng số giảm dần theo thời gian trong `evidence.py` là cơ chế tự làm sạch.
