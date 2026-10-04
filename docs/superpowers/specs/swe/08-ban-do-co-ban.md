# Spec 08: Bản đồ cơ bản

**Mã theo dõi:** S8.1 tới S8.4 (lõi, ngày 1); S8.5 (nên, ngày 7); S8.6 (thêm).

Spec này được thêm ngày 04/10/2026, sau khi chủ dự án yêu cầu: trước khi có lớp ngập, sản phẩm phải dùng được như một bản đồ thông thường. Nó là việc đầu tiên sau phần nền.

## Mục tiêu

Một người chưa từng nghe về dự án mở trang ra và dùng được ngay như dùng một ứng dụng bản đồ quen thuộc: tìm một địa điểm, xem nó ở đâu, xem mình đang ở đâu, chạm vào một điểm để biết địa chỉ, rồi bấm "Chỉ đường". Lớp ngập và lớp giao thông là thứ được bật lên trên nền đó.

## 1. Bản đồ thông thường có gì, và mình làm tới đâu

| Tính năng | Trong kế hoạch trước ngày 04/10 | Bây giờ |
|---|---|---|
| Kéo, phóng to, xoay, la bàn, thước tỉ lệ | Có một phần | S8.1 |
| Vị trí của tôi, chấm xanh | Có, nhưng tới ngày 7 mới chạy trên máy chủ | S8.4; HTTPS kéo lên ngày 4 |
| Ô tìm kiếm ở trên cùng | Chỉ có bên trong bảng tìm đường | S8.2 |
| Thẻ địa điểm: tên, địa chỉ, nút "Chỉ đường" | Chưa có | S8.2 |
| Chạm vào bản đồ để ghim và xem địa chỉ | Chưa có | S8.3 |
| Nhiều lộ trình, chọn lộ trình, thời gian tới nơi | Chỉ 1–2 lộ trình của Goong | Spec 05 |
| Danh sách chỉ dẫn từng chặng | Chưa có | Spec 05 |
| Lớp giao thông | Đã bỏ | Spec 09 |
| Bật tắt lớp, đổi kiểu bản đồ | Chưa có | S8.5 |
| Nơi đã lưu, tìm kiếm gần đây | Chỉ có nơi đã lưu cho cảnh báo | S8.6 |
| Dẫn đường theo GPS từng bước, giọng nói | Không làm | Không làm |
| Ảnh đường phố, đánh giá, giờ mở cửa | Không làm | Không làm |

Hai dòng cuối cần một ứng dụng di động và dữ liệu địa điểm riêng, không phải việc của một bản demo web trong 10 ngày.

## 2. Khung bản đồ và điều khiển (S8.1)

- Nền bản đồ là style của Goong, vẽ bằng MapLibre GL JS (đã thử ngày 04/10, tải được).
- Điều khiển: nút phóng to và thu nhỏ, la bàn, thước tỉ lệ, dòng ghi công bản quyền của Goong và OpenStreetMap.
- Mở trang lần đầu thì bản đồ nằm ở trung tâm thành phố đang chọn. Lần sau thì nằm ở chỗ người dùng rời đi lần trước (lưu khung nhìn trong `localStorage`).
- Bố cục màn hình ở spec 02, mục 1, với một thay đổi: thanh trên cùng giờ là ô tìm kiếm; ô chọn thành phố và ô chọn chế độ chuyển vào nút "Lớp" (S8.5) và một dòng nhỏ dưới ô tìm kiếm.

## 3. Tìm kiếm và thẻ địa điểm (S8.2)

- Ô tìm kiếm luôn nằm trên cùng. Gõ từ 2 ký tự thì hiện gợi ý, chờ 300 mili giây sau phím cuối. Gợi ý ưu tiên nơi gần tâm bản đồ.
- Chọn một gợi ý: bản đồ bay tới đó, đặt một ghim, và mở **thẻ địa điểm**.
- Thẻ địa điểm có tên, địa chỉ, và ba nút:

| Nút | Việc |
|---|---|
| Chỉ đường tới đây | Mở bảng tìm đường với điểm đến là nơi này; điểm đi là vị trí của tôi nếu có |
| Đi từ đây | Mở bảng tìm đường với điểm đi là nơi này |
| Báo ngập ở đây | Mở bảng báo ngập cho đoạn đường gần nhất (spec 03) |

- Khi lớp ngập đang bật, thẻ thêm một dòng về nguy cơ quanh nơi đó, lấy từ `GET /api/alerts` với bán kính 500 m: "Quanh đây: 2 đoạn nguy cơ cao".
- Máy chủ gọi Autocomplete V2 và Place Detail V2 của Goong. Khóa REST không xuống trình duyệt.
- Autocomplete của Goong tốt cho địa điểm và kém cho tên đường (đã thử). Không endpoint nào gọi Forward Geocode.

## 4. Chạm để ghim và xem địa chỉ (S8.3)

- Chạm vào một điểm trống trên bản đồ: đặt ghim, gọi `GET /api/places/reverse`, mở thẻ địa điểm với địa chỉ vừa nhận. Trong lúc chờ, thẻ hiện tọa độ.
- Chạm vào một điểm khác khi đã có ghim thì ghim chuyển sang điểm đó. Chạm vào một đoạn đã tô màu của lớp ngập thì mở thẻ giải thích (spec 02), không đặt ghim.
- Bấm nút × trên thẻ thì bỏ ghim. (Bản trước viết "chạm ra ngoài thẻ thì bỏ ghim"; điều đó mâu thuẫn với việc chạm để đặt ghim mới nên đã bỏ.)
- Thẻ bỏ phần trùng giữa tên và địa chỉ: Goong thường trả địa chỉ bắt đầu bằng đúng tên địa điểm, nên dòng phụ chỉ giữ phần còn lại ("Chợ Bến Thành" và "Bến Thành, Hồ Chí Minh").

Điều này thay cho hành vi cũ "chạm vào bản đồ là mở bảng báo ngập". Báo ngập giờ đi qua nút trong thẻ địa điểm hoặc mục "Báo ngập" ở thanh dưới.

`GET /api/places/reverse?lat=&lon=` gọi Geocode V2 của Goong với `latlng`. Đã thử ngày 04/10 với khóa của nhóm: điểm ở chợ Bến Thành trả về "Công trường Quách Thị Trang, Chợ Bến Thành, Bến Thành, Hồ Chí Minh". Goong không trả lời thì thẻ chỉ hiện tọa độ và ba nút vẫn dùng được.

## 5. Vị trí của tôi (S8.4)

- Nút định vị ở góc bản đồ. Bấm thì trình duyệt hỏi quyền, rồi bản đồ bay tới và hiện chấm xanh kèm vòng sai số.
- Vị trí chỉ nằm trong trình duyệt. Nó chỉ được gửi lên máy chủ khi người dùng chủ động dùng nó: làm điểm đi của một lộ trình, hoặc để báo ngập.
- Trình duyệt chỉ cho định vị trên trang HTTPS hoặc `localhost`. Vì vậy mục HTTPS của spec 07 được kéo từ ngày 7 lên ngày 4. Trước đó, trên máy chủ, nút định vị hiện lời "Cần HTTPS để dùng định vị; hãy chạm vào bản đồ để chọn điểm".
- Người dùng từ chối quyền thì hiện lời giải thích một lần, mọi tính năng khác vẫn dùng được bằng cách chạm chọn điểm.

## 6. Lớp và kiểu bản đồ (S8.5)

Một nút "Lớp" mở bảng nhỏ:

| Mục | Mặc định |
|---|---|
| Nguy cơ ngập | Bật |
| Giao thông | Tắt |
| Thành phố | TP.HCM |
| Chế độ: trực tiếp hoặc một kịch bản | Trực tiếp |
| Kiểu nền: thường, tối, vệ tinh | Thường |

Chỉ kiểu nền "thường" đã được thử với khóa của nhóm. Hai kiểu còn lại phải thử địa chỉ style trước khi đưa vào; kiểu nào không tải được thì bỏ khỏi bảng.

## 7. Nơi đã lưu và tìm kiếm gần đây (S8.6)

- Năm lần tìm gần nhất hiện ra khi chạm vào ô tìm kiếm lúc còn trống.
- Lưu được "Nhà" và "Chỗ làm" từ thẻ địa điểm. Hai nơi này dùng chung với thẻ cảnh báo của spec 06.
- Tất cả nằm trong `localStorage`; máy chủ không biết.

## 8. Endpoint

| Endpoint | Tham số | Trả về |
|---|---|---|
| `GET /api/places/autocomplete` | `q`, `lat`, `lon` | Danh sách `place_id`, `main`, `secondary` |
| `GET /api/places/detail` | `place_id` | `name`, `address`, `lat`, `lon` |
| `GET /api/places/reverse` | `lat`, `lon` | `name`, `address`, `place_id` nếu có |

Goong lỗi thì cả ba trả 502 với lời "Không tìm được địa điểm lúc này". Điểm ngoài lãnh thổ Việt Nam trả 422.

## 9. Chỗ đang dùng bản giả

Không có. Spec này chỉ phụ thuộc vào Goong, và hai khóa đã có. Trong kiểm thử, Goong được thay bằng đối tượng giả; kiểm thử không gọi mạng.

## 10. Nghiệm thu

Đánh dấu `[x]` là đã thử ngày 04/10/2026 trên trình duyệt tích hợp của ứng dụng Claude (cả khung máy tính và khung 360 px), trên dữ liệu mẫu. `[ ]` là chưa làm hoặc chưa thử được; lý do ghi ngay sau.

**S8.1:**

- [x] Bản đồ Goong hiện đúng ở khung 360 px, không tràn ngang; có nút phóng, la bàn, thước tỉ lệ, dòng bản quyền. Cả dev lẫn bản dựng sản xuất đều hiện bản đồ.
- [ ] Kéo và phóng mượt bằng cảm ứng trên điện thoại thật. Chưa thử: công cụ kiểm chỉ giả lập khung hình, không giả lập thao tác chạm.
- [x] Tải lại trang thì bản đồ ở đúng chỗ vừa rời đi.

**S8.2:**

- [x] Gõ "cho ben thanh" hiện "Chợ Bến Thành" đầu danh sách; chọn thì bản đồ bay tới, có ghim và thẻ địa điểm.
- [ ] Ba nút trên thẻ mở đúng bảng với đúng điểm đã điền. Ba nút hiện đang bị khóa vì bảng tìm đường (spec 05) và bảng báo ngập (spec 03) chưa làm.
- [ ] Goong lỗi thì ô tìm kiếm báo bằng tiếng Việt, trang không hỏng. Mã đã có và phía máy chủ đã có kiểm thử (lỗi Goong thành 502 có lời tiếng Việt); chưa thử trên trình duyệt với Goong hỏng thật.

**S8.3:**

- [x] Chạm vào một điểm trống đặt ghim và hiện địa chỉ (đã thử ở khung máy tính và khung 360 px).
- [ ] Chạm vào một đoạn tô màu mở thẻ giải thích, không đặt ghim. Lớp ngập chưa vẽ (spec 02).
- [ ] Goong lỗi thì thẻ hiện tọa độ, ba nút vẫn dùng được. Mã đã có; chưa thử trên trình duyệt với Goong hỏng thật.

**S8.4:**

- [ ] Trên `localhost`, nút định vị đưa bản đồ tới vị trí hiện tại và hiện chấm xanh. Chưa thử được: trình duyệt tích hợp báo "Geolocation support is not available". Phải thử trên Chrome thật.
- [ ] Trên máy chủ chưa có HTTPS, nút hiện lời giải thích thay vì im lặng. Mã đã có (nút mờ, bấm hiện lời giải thích); chưa thử vì `localhost` luôn được coi là an toàn, cần mở qua địa chỉ mạng LAN hoặc máy EC2.
- [ ] Từ chối quyền định vị không làm hỏng tính năng nào. Chưa thử, cùng lý do.

**S8.5:**

- [ ] Bật tắt được lớp nguy cơ ngập và lớp giao thông.
- [ ] Kiểu nền nào có trong bảng thì đều tải được.

**S8.6:**

- [ ] Năm lần tìm gần nhất hiện lại sau khi tải lại trang; xóa được.

## 11. Không làm

- Không dẫn đường theo GPS từng bước, không giọng nói.
- Không có trang chi tiết địa điểm với ảnh, đánh giá, giờ mở cửa.
- Không tìm theo loại địa điểm ("quán cà phê gần đây").
- Không có tài khoản người dùng; mọi thứ cá nhân nằm trong trình duyệt.
