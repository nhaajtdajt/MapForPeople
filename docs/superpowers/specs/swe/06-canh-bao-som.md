# Spec 06: Cảnh báo sớm và lời khuyên giờ đi

**Mã theo dõi:** S6.1 (lõi, ngày 6); S6.2 (thêm, ngày 7).

## Mục tiêu

Người dùng biết trước, cho một nơi mình quan tâm, nguy cơ ngập bây giờ và trong 1–2 giờ tới. Khi đã có lộ trình, họ nhận thêm một câu khuyên: nên đi ngay hay chờ.

Dự báo của hệ thống tính theo giờ: bây giờ, sau 1 giờ và sau 2 giờ. Vì vậy mọi lời khuyên ở đây cũng theo giờ. Câu kiểu "chờ 10 phút nữa" nằm ngoài khả năng của dữ liệu hiện có và không được viết ra.

## 1. Cảnh báo sớm quanh một vị trí (S6.1)

### 1.1 Hành vi

- Mục "Cảnh báo" ở thanh dưới mở bảng có hai lựa chọn: "Quanh vị trí của tôi" và "Quanh nơi đã lưu".
- Người dùng lưu được một nơi (nhà, chỗ làm) bằng cách tìm địa điểm hoặc chạm trên bản đồ. Nơi đã lưu nằm trong `localStorage` của trình duyệt; máy chủ không biết nó.
- Thẻ `AlertCard` hiện ba ô cho ba giờ:

| Ô | Nội dung |
|---|---|
| Bây giờ | Mức cao nhất trong bán kính, kèm màu; "2 đoạn nguy cơ cao, 3 đoạn nguy cơ vừa" |
| Sau 1 giờ | Như trên |
| Sau 2 giờ | Như trên |

- Bên dưới là tối đa 5 đoạn nguy cơ nhất của giờ đang chọn. Chạm một đoạn thì bản đồ bay tới đó và mở thẻ giải thích.
- Một câu tóm tắt ở đầu thẻ, chọn theo xu hướng:

| Xu hướng trong 2 giờ | Câu |
|---|---|
| Mức cao nhất tăng | "Nguy cơ ngập quanh đây đang tăng trong 1–2 giờ tới." |
| Mức cao nhất giảm | "Nguy cơ ngập quanh đây giảm dần trong 1–2 giờ tới." |
| Không đổi, đang có mức vừa hoặc cao | "Nguy cơ ngập quanh đây giữ nguyên trong 2 giờ tới." |
| Mọi giờ đều thấp | "Chưa thấy nguy cơ ngập quanh đây trong 2 giờ tới." |

- Khi mở trang mà nơi đã lưu đang có mức cao ở bất kỳ giờ nào, thẻ tự hiện ra một lần.
- Dòng nhỏ cuối thẻ: "Dự báo 1–2 giờ tới có độ tin thấp hơn hiện tại."

### 1.2 `GET /api/alerts`

Tham số: `city`, `lat`, `lon`, `radius_m` (mặc định 1.500, lớn hơn 0 và tối đa 5.000), `replay` tùy chọn.

Trả `{"hours": [{"hour_offset", "max_level", "count_high", "count_medium", "top": [{"unit_id", "name", "level", "risk"}]}], "computed_at"}`, mỗi giờ một phần tử.

- Giờ 0 có áp báo cáo của người dùng; giờ 1 và 2 thì không.
- Điểm ngoài khung thành phố trả 422. Bán kính không hợp lệ trả 422.
- Không có đoạn nào trong bán kính thì mọi giờ có `max_level` bằng 0 và `top` rỗng, không phải lỗi.

Tọa độ gửi lên endpoint này không được lưu và không được ghi vào nhật ký máy chủ.

## 2. Lời khuyên giờ đi (S6.2)

### 2.1 Hành vi

Sau khi tìm đường (spec 05), lộ trình đề xuất được chấm lại theo lớp nguy cơ của giờ 1 và giờ 2. Kết quả nằm trong `by_hour` của từng lộ trình, và máy chủ rút ra một câu khuyên đặt trong `advice`:

| Điều kiện trên lộ trình đề xuất | `kind` | Câu hiện trên đầu `RoutePanel` |
|---|---|---|
| `flooded_m` bằng 0 ở giờ 0 và lớn hơn 0 ở giờ 1 hoặc 2 | `go-now` | "Nên đi ngay: nguy cơ ngập trên lộ trình tăng trong 1–2 giờ tới." |
| `flooded_m` lớn hơn 0 ở giờ 0, và bằng 0 ở giờ `h` (lấy giờ sớm nhất) | `wait` | "Nếu chờ được, đi sau khoảng `h` giờ: dự báo lộ trình không còn đoạn nguy cơ cao." |
| Các trường hợp khác | — | Không hiện gì; `advice` rỗng |

`advice` có dạng `{"kind": "go-now" | "wait", "hour": 1, "text": "…"}`.

### 2.2 Ba giới hạn phải giữ

- Lộ trình không được tìm lại cho giờ 1 và giờ 2. Chỉ chấm lại đúng hình học đã có.
- Báo cáo của người dùng chỉ có tác dụng ở giờ 0. Một đoạn đang được nhiều người báo ngập sẽ hiện là "hết nguy cơ" ở giờ 1 nếu dự báo mưa giảm, dù nước chưa chắc đã rút. Vì vậy khi lộ trình ở giờ 0 có đoạn mang nguồn `report`, câu khuyên `wait` không được đưa ra.
- Trong kịch bản phát lại loại `recorded-day`, ba giờ có cùng một bảng nguy cơ, nên sẽ không có lời khuyên nào. Muốn trình diễn tính năng này thì dùng kịch bản `past-moment` hoặc `synthetic`.

## 3. Chỗ đang dùng bản giả

| Cần | Bản giả | Bản thật đến khi nào |
|---|---|---|
| Nguy cơ ba giờ | Bảng mẫu: mưa giảm dần qua ba giờ (0,9, 0,6, 0,3), nên xu hướng mẫu luôn là "giảm". Ở giờ 0 có ba đoạn mức cao; ở giờ 1 và 2 không còn đoạn nào mức cao | Hết ngày 2 |
| Kịch bản có xu hướng tăng | Kịch bản `sample-synthetic` của `devdata` (spec 01, mục 2.1): mưa tăng dần, chỉ ở giờ 2 mới có đoạn mức cao | Ngày 3 |

## 4. Nghiệm thu

**S6.1:**

- [ ] Trên dữ liệu mẫu, `GET /api/alerts` quanh tâm lưới mẫu trả ở giờ 0: mức cao nhất 2, ba đoạn mức cao, hai đoạn mức vừa.
- [ ] Mức cao nhất ở giờ 2 không lớn hơn ở giờ 0, và câu tóm tắt là câu "giảm dần".
- [ ] Điểm xa mọi đoạn: ba giờ đều mức thấp, `top` rỗng, câu "Chưa thấy nguy cơ".
- [ ] `radius_m` bằng 0 trả 422.
- [ ] Lưu một nơi, tải lại trang: nơi đó còn nguyên. Xóa được nơi đã lưu.
- [ ] Chạm một đoạn trong danh sách làm bản đồ bay tới đoạn đó.
- [ ] Khi đang xem một kịch bản, thẻ cảnh báo dùng số liệu của kịch bản đó.

**S6.2:**

- [ ] Trên kịch bản `sample-synthetic` (nguy cơ tăng dần), lộ trình dọc đoạn mẫu số 6 khô ở giờ 0 và nhận câu `go-now`.
- [ ] Trên bảng nguy cơ mẫu (giảm dần), lộ trình dọc đoạn mẫu số 6 có `flooded_m` lớn hơn 0 ở giờ 0 và nhận câu `wait` với `hour` bằng 1.
- [ ] Cùng tình huống đó, sau khi có một báo cáo "ngập cao" trên đoạn ấy thì không còn câu `wait`.
- [ ] Lộ trình khô ở cả ba giờ không có lời khuyên.

## 5. Không làm

- Không gửi thông báo đẩy, không gửi tin nhắn. Cảnh báo chỉ hiện khi người dùng mở trang.
- Không lưu nơi quan tâm của người dùng trên máy chủ.
- Không dự báo xa hơn 2 giờ.
- Không đưa ra lời khuyên theo phút.
