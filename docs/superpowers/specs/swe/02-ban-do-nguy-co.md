# Spec 02: Bản đồ nguy cơ ngập

**Mã theo dõi:** S2.1, S2.2 (lõi, ngày 3); S2.3 (nên, ngày 7).

Lớp nguy cơ được vẽ lên trên bản đồ cơ bản của spec 08. Spec 08 làm trước.

## Mục tiêu

Người dùng mở trang trên điện thoại và trong vài giây thấy đoạn đường nào quanh mình đang có nguy cơ ngập, mức nào, và thông tin đó đến từ đâu: có người vừa báo, hay là dự báo.

## 1. Khung giao diện

Thiết kế cho điện thoại trước, chiều rộng nhỏ nhất 360 px. Trên màn hình rộng, các bảng điều khiển nằm thành một cột bên trái thay vì trượt từ dưới lên.

```
┌────────────────────────────────┐
│ [🔍 Tìm địa điểm…        ][Lớp]│  ô tìm kiếm; nút lớp
│ TP.HCM · Trực tiếp             │  dòng trạng thái; dải chữ khi phát lại
│                                │
│            BẢN ĐỒ              │
│                          [◎]   │  vị trí của tôi
│ [Bây giờ | +1 giờ | +2 giờ]    │  chọn giờ
│ Chú thích ▸        Dữ liệu mẫu │  chú thích thu gọn; nhãn bản giả
├────────────────────────────────┤
│  Tìm đường │ Báo ngập │ Cảnh báo │  thanh dưới
└────────────────────────────────┘
```

Mỗi mục ở thanh dưới mở một bảng trượt từ dưới lên, che tối đa nửa màn hình để bản đồ vẫn nhìn thấy được. Ba bảng đó thuộc spec 05, 03 và 06. Thành phố và chế độ được đổi trong bảng của nút "Lớp" (spec 08).

Các thành phần giao diện, mỗi thành phần một file trong `web/src/components/`:

| Thành phần | Việc | Spec |
|---|---|---|
| `SearchBar`, `PlaceCard` | Ô tìm kiếm, thẻ địa điểm | 08 |
| `LayersPanel` | Bật tắt lớp, chọn thành phố, chế độ, kiểu nền | 08, 04 |
| `StatusLine` | Thành phố, chế độ, dải chữ khi phát lại | 02, 04 |
| `HourPicker` | Bây giờ, +1 giờ, +2 giờ | 02 |
| `Legend` | Chú thích màu và nét; dòng trạng thái dữ liệu; nguồn giao thông | 02, 09 |
| `StatusChip` | Nhãn "Dữ liệu mẫu", "Đang dùng bản giả" | 01 |
| `UnitCard` | Thẻ giải thích | 02 |
| `ReportSheet` | Bảng báo ngập | 03 |
| `TestBench` | Bàn thử | 04 |
| `RoutePanel` | Bảng lộ trình | 05 |
| `AlertCard` | Thẻ cảnh báo | 06 |

`MapView.tsx` giữ bản đồ và mọi lớp vẽ. `App.tsx` giữ trạng thái chung: thành phố, chế độ, giờ, bảng đang mở. `api.ts` là nơi duy nhất gọi máy chủ.

## 2. Lớp nguy cơ

### 2.1 Vẽ gì

Mặc định chỉ vẽ đoạn mức vừa và mức cao (`min_level=1`). Đoạn mức thấp không được vẽ, để bản đồ không bị phủ kín màu xanh.

| Mức | Màu |
|---|---|
| Vừa | `#f29f05` |
| Cao | `#d7263d` |
| Thấp (chỉ dùng trong chú thích và thẻ) | `#3aa655` |

Kiểu nét cho biết thông tin đến từ đâu (QĐKT mục 7.1):

| `source` | Nét | Dòng trong chú thích |
|---|---|---|
| `report` | Liền | Có người vừa báo |
| `official` | Liền | Nguồn chính thức, hoặc ghi nhận của ngày đang phát lại |
| `history`, `exact` đúng | Đứt | Dự báo theo lịch sử ngập |
| `history`, `exact` sai | Đứt, mờ một nửa | Dự báo theo lịch sử, chưa rõ đoạn nào |
| `model` | Chấm | Dự báo của mô hình |

### 2.2 Tải dữ liệu

- Giao diện gọi `GET /api/risk` với khung nhìn hiện tại mỗi khi bản đồ dừng di chuyển, chờ 300 mili giây sau lần di chuyển cuối, và hủy yêu cầu cũ còn dang dở.
- Máy chủ trả tối đa 3.000 đoạn mỗi lần, ưu tiên mức cao rồi tới nguy cơ lớn. Khi còn đoạn bị bỏ, phản hồi có `truncated: true` và chú thích ghi "Phóng to để xem đủ".
- Đổi thành phố, đổi giờ hoặc đổi chế độ thì tải lại.
- Ở chế độ trực tiếp, giao diện tự tải lại mỗi 5 phút, để báo cáo của người khác hiện lên.

### 2.3 Các dòng trạng thái trong chú thích

| Điều kiện | Dòng hiện ra |
|---|---|
| Bình thường | "Cập nhật lúc HH:MM" |
| `stale` đúng: bảng nguy cơ cũ hơn 3 giờ, hoặc chưa có | "Chưa được cập nhật từ HH:MM" hoặc "Chưa có dữ liệu nguy cơ" |
| Đang chọn +1 giờ hoặc +2 giờ | "Dự báo, độ tin thấp hơn hiện tại" |
| Thành phố không nằm trong `validated` | "Dự báo ở thành phố này chưa được kiểm chứng" |

### 2.4 Bằng chứng từ báo cáo

Máy chủ áp `apply_evidence` lên từng đoạn có báo cáo trước khi trả về, và chỉ làm vậy với `hour=0`. Ở +1 giờ và +2 giờ, lớp nguy cơ là dự báo thuần.

## 3. Thẻ giải thích (S2.3)

Chạm vào một đoạn đã tô màu mở thẻ `UnitCard`. Thẻ trả lời câu hỏi "vì sao đoạn này có màu này":

- Tên đường và mức, kèm màu.
- Nguồn bằng chữ: "Có người vừa báo", "Dự báo theo lịch sử ngập", "Dự báo của mô hình".
- Lịch sử: các năm từng ngập, nguyên nhân, độ sâu lớn nhất từng ghi nhận, đường dẫn tới bài báo nếu có.
- Mưa và triều lúc này bằng chữ: `t_rain` hoặc `t_tide` từ 0,45 là "đáng kể", từ 0,75 là "lớn", thấp hơn thì không ghi.
- Số người đã báo trong 30 phút qua.
- Nút "Báo tình trạng ở đây", mở bảng báo ngập cho đúng đoạn đó.

Chạm vào chỗ không có đoạn tô màu thì không mở thẻ này; lúc đó bản đồ đặt ghim và mở thẻ địa điểm (spec 08).

## 4. Endpoint

Tham số và trường trả về theo QĐKT mục 7.1.

| Endpoint | Ghi chú riêng của spec này |
|---|---|
| `GET /api/health` | Hình dạng ở spec 01, mục 3.1 |
| `GET /api/cities` | `validated` đọc từ `model_choice.json`; thiếu file thì mọi thành phố là sai |
| `GET /api/risk` | `bbox` sai dạng trả 422; thành phố không có dữ liệu trả 404; chưa có `risk.parquet` thì mọi đoạn mức thấp và `stale` đúng, không trả lỗi 500 |
| `GET /api/units/{unit_id}` | Trả 404 khi mã đoạn không tồn tại. Thiếu `observations.parquet` thì phần lịch sử chỉ còn số lần và độ sâu lớn nhất lấy từ `scores.parquet` |

Mọi thông báo lỗi viết bằng tiếng Việt trong trường `detail`.

## 5. Chỗ đang dùng bản giả

| Cần | Bản giả | Bản thật đến khi nào |
|---|---|---|
| Đoạn đường, điểm, bảng nguy cơ | Tám đường mẫu của `devdata` | Trưa và hết ngày 2 |
| `to_level`, `apply_evidence` | `fakes` qua `ports` | Hết ngày 1 |
| Ghi nhận ngập cho thẻ giải thích | Bảng mẫu của `devdata` | Trưa ngày 2 |

Khi dữ liệu thật của TP.HCM đến, phải đo hai thứ: thời gian nạp thành phố vào bộ nhớ lúc khởi động, và thời gian trả một lần `GET /api/risk` ở khung nhìn toàn thành phố. Mục tiêu là dưới 1 giây cho lần gọi đó. Nếu chậm hơn thì giảm độ chi tiết hình học khi nạp, trước khi nghĩ tới cách khác.

## 6. Nghiệm thu

**S2.1, máy chủ:**

- [ ] Trên dữ liệu mẫu, `GET /api/risk` ở `hour=0` trả ba đoạn mức cao và hai đoạn mức vừa.
- [ ] Hai đoạn mẫu đầu có `source` là `model`, các đoạn còn lại là `history`.
- [ ] `bbox` sai dạng trả 422, thành phố lạ trả 404, đều có `detail` tiếng Việt.
- [ ] Xóa `risk.parquet` thì máy chủ vẫn chạy, mọi đoạn mức thấp, `stale` đúng.
- [ ] `/api/cities` ghi `hcm` đã kiểm chứng và `danang` chưa, đúng như `model_choice.json` mẫu.

**S2.2, giao diện:**

- [ ] Bản đồ Goong hiện đúng trung tâm thành phố đang chọn; đổi thành phố thì bay sang thành phố kia.
- [ ] Năm kiểu vẽ ở mục 2.1 phân biệt được bằng mắt, và chú thích ghi đủ.
- [ ] Đổi giờ làm lớp nguy cơ đổi theo, và dòng "Dự báo, độ tin thấp hơn hiện tại" xuất hiện.
- [ ] Bốn dòng trạng thái ở mục 2.3 hiện đúng điều kiện. Dòng dữ liệu cũ thử bằng `devdata --stale`.
- [ ] Dùng được bằng một tay ở chiều rộng 360 px: không có phần nào tràn ngang, mọi nút bấm cao ít nhất 44 px.
- [ ] `npm run build` đạt, kể cả kiểm kiểu.

**S2.3, thẻ giải thích:**

- [ ] Chạm vào đoạn mẫu số 7 mở thẻ có năm ngập gần nhất 2025 và độ sâu lớn nhất 60 cm.
- [ ] Nút "Báo tình trạng ở đây" mở bảng báo ngập cho đúng đoạn đó.
- [ ] Mã đoạn không tồn tại trả 404.

## 7. Không làm

- Không vẽ vùng ngập dạng mảng màu. Đơn vị dự báo là đoạn đường.
- Không hiện con số nguy cơ cho người dùng. `R` là chỉ số, không phải xác suất; người dùng chỉ thấy ba mức.
- Không dùng vector tiles (đã loại ở QĐKT mục 1).
