# Spec 09: Giao thông

**Mã theo dõi:** S9.1 (lõi, ngày 2); S9.2, S9.3 (nên, ngày 4–5); S9.4 (lõi, ngày 5); S9.5 (thêm).

Spec này được thêm ngày 04/10/2026. Nó đảo lại quyết định "không dùng số liệu giao thông" ở QĐKT mục 1 và mục 15: chủ dự án thấy thời gian tới nơi không thể hợp lý nếu không tính mức độ đông của đường. Bản 2, cùng ngày: thêm kết quả gọi thử TomTom bằng khóa của nhóm.

## Mục tiêu

Thời gian dự kiến của một lộ trình phải đổi theo giờ trong ngày và theo tình trạng đường. Người dùng bật được một lớp giao thông trên bản đồ. Khi một đoạn có nguy cơ ngập cao, thời gian đi qua đoạn đó phải dài ra, vì ngập kéo theo kẹt xe.

## 1. Đã tìm nguồn ở đâu

Tra cứu ngày 04/10/2026. Cột "Phủ Việt Nam" lấy từ tài liệu công bố của từng hãng. TomTom và Goong đã được gọi thử bằng khóa của nhóm; các nguồn còn lại thì chưa.

| Nguồn | Phủ Việt Nam | Kết luận | Lý do |
|---|---|---|---|
| Google Maps (Routes API) | Có | **Không dùng** | Điều khoản của Google cấm dùng dịch vụ của họ "với hoặc gần một bản đồ không phải của Google" trong cùng ứng dụng. Sản phẩm này chạy trên bản đồ Goong, nên dùng là vi phạm. Thêm nữa, đề bài là về bản đồ của người Việt |
| **TomTom Traffic Flow** | Có: cả tốc độ dòng xe lẫn sự cố | **Chọn; đã gọi thử, chạy được** | Gói miễn phí 50.000 ô bản đồ và 2.500 yêu cầu khác mỗi ngày, không cần thẻ. Trả về số: tốc độ hiện tại so với lúc thông thoáng, theo từng đoạn đường |
| HERE Traffic API v7 | Có: tốc độ dòng xe; không có sự cố | Dự phòng | Chỉ cần tới nếu TomTom hỏng. Gói miễn phí cần đăng ký tài khoản HERE |
| Mapbox | Việt Nam không có trong danh sách phủ giao thông | Không dùng | — |
| Vietmap Traffic | Có | Không dùng để tính | Chỉ trả ảnh PNG tô màu, không có con số tốc độ; trên khóa dùng thử thì tắt sẵn, phải liên hệ để bật |
| Goong | Không rõ | Không dùng làm nguồn giao thông | Direction V2 chỉ trả một trường thời gian, không tách riêng phần do giao thông. Goong không công bố thời gian đó có tính giao thông hay không |

### 1.1 Kết quả gọi thử TomTom

Gọi bằng khóa của nhóm lúc 17 giờ 15, Chủ nhật 04/10/2026, trên một khung 6 × 5,7 km ở trung tâm TP.HCM (Quận 1, Quận 3, Bình Thạnh).

| Phép thử | Kết quả |
|---|---|
| Ô vector Traffic Flow, loại `relative` | Tải được. Mỗi đoạn có `traffic_level` (0 tới 1), `road_type`, `road_closure`, `traffic_road_coverage` |
| Mức phóng nào đủ | Mức 13 đã có cả đường nhỏ; mức 14 và 15 không thêm được gì. Mức 12 chỉ có đường lớn. Khung thử cần 4 ô ở mức 13 |
| **Độ dày: khớp với mạng đường OpenStreetMap** (điểm giữa cạnh cách một đoạn TomTom không quá 20 m) | `trunk` 100%, `primary` 100%, `secondary` 98%, `tertiary` 76%, đường dân cư 10%. Tính chung từ `tertiary` trở lên: **89% chiều dài** |
| Mức độ đông lúc thử | Trung vị `traffic_level` là 0,64; 20% chiều dài dưới 0,5 |
| Số liệu có sống không | Một điểm trên Điện Biên Phủ gần Hàng Xanh: 12 km/giờ lúc 17 giờ 13, 19 km/giờ lúc 17 giờ 19 (tốc độ lúc thông thoáng là 19) |
| Tốc độ tải | Khoảng 1,3 giây mỗi ô khi tải lần lượt; phải tải song song |
| Routing API của TomTom, Bến Thành tới Landmark 81 | Trả 4 lộ trình, mỗi lộ trình có thời gian lúc không có giao thông (981 giây ở lộ trình đầu) và thời gian có giao thông (1.187 giây) |
| Routing API với loại xe là xe máy | Trả đúng các con số của ô tô. TomTom không tính riêng cho xe máy ở Việt Nam |

Phép khớp ở trên chưa xét hướng của đoạn đường; con số 89% vì vậy hơi lạc quan.

**Ba điều còn chưa biết:**

1. **Giờ cao điểm ngày thường trông ra sao.** Lần thử rơi vào chiều Chủ nhật.
2. **Đà Nẵng** chưa được thử.
3. **Điều khoản về việc lưu số liệu.** Tôi không tải được toàn văn điều khoản của TomTom. Trước khi làm S9.5 phải đọc mục về lưu trữ. Khi hiện số liệu của TomTom, bản đồ phải ghi "© TomTom".

Khóa nằm trong `.env` với tên `TOMTOM_API_KEY`. File này không được commit.

## 2. Ba tầng số liệu

Hệ số giao thông `g` của một cạnh là tỉ số giữa tốc độ lúc này và tốc độ lúc thông thoáng, từ 0 tới 1. `g` bằng 1 nghĩa là đường thông.

| Tầng | Khi nào dùng | Nhãn trên giao diện |
|---|---|---|
| **Thật:** TomTom, lấy mỗi 10 phút | Chế độ trực tiếp, trên cạnh khớp được với một đoạn của TomTom | "Giao thông: TomTom, lúc HH:MM" |
| **Điển hình:** bảng theo giờ và loại đường | Cạnh không khớp (chủ yếu là đường dân cư); mọi kịch bản phát lại, vì không ai lưu giao thông của một ngày đã qua | "Giao thông điển hình theo giờ (ước lượng)" |
| **Ngập làm chậm:** nhân thêm vào hai tầng trên | Cạnh thuộc đoạn có nguy cơ vừa hoặc cao | "Có tính chậm do ngập (giả lập)" |

Tầng điển hình và tầng ngập làm chậm là số do nhóm đặt ra. Đề bài cho phép dữ liệu giả lập miễn là ghi rõ, nên nhãn ở cột ba là bắt buộc.

### 2.1 Từ `g` tới thời gian

Thời gian đi một cạnh (spec 05, mục 2.1) dùng `g` qua một hệ số ảnh hưởng `β`:

```
tốc độ lúc này = tốc độ lúc thông thoáng × (1 − β × (1 − g))
```

- `β` của ô tô được hiệu chỉnh để thời gian của mình khớp thời gian có giao thông của TomTom (spec 05, mục 5). Trước khi hiệu chỉnh, `β` bằng 1.
- `β` của xe máy bằng 0,6 lần của ô tô. Xe máy luồn được nên chậm đi ít hơn ô tô khi đường đông, và TomTom không có số riêng cho xe máy. Con số 0,6 là ước lượng do tôi đặt.

### 2.2 Giao thông điển hình (S9.1)

Một bảng `g` theo loại đường và khung giờ. Giá trị khởi đầu cho ngày thường:

| Loại đường | Đêm (22–6 giờ) | Ban ngày | Cao điểm (7–9 giờ, 16 giờ 30–19 giờ) |
|---|---|---|---|
| trunk, primary, secondary | 1,0 | 0,65 | 0,50 |
| tertiary | 1,0 | 0,70 | 0,60 |
| Còn lại | 1,0 | 0,90 | 0,80 |

Cuối tuần dùng cột "Ban ngày" cho cả hai khung cao điểm. Cột "Ban ngày" được đặt theo lần đo duy nhất ở mục 1.1 (trung vị 0,64); cột "Cao điểm" là số tôi đoán. Bảng này sẽ được thay bằng số đo nếu S9.5 chạy.

Tầng này làm xong ở ngày 2, cùng lúc với thuật toán tìm đường.

### 2.3 Giao thông thật từ TomTom (S9.2)

- **Lấy gì:** ô vector `https://api.tomtom.com/traffic/map/4/tile/flow/relative/13/{x}/{y}.pbf`, mức phóng 13.
- **Bao nhiêu:** khung TP.HCM khoảng 80 ô, khung Đà Nẵng khoảng 45 ô. Lấy mỗi 10 phút từ 6 tới 23 giờ là khoảng 13.000 ô mỗi ngày, dưới hạn mức 50.000. Tải 8 ô cùng lúc để một lượt xong trong khoảng 20 giây.
- **Khớp vào mạng đường của mình:** với mỗi cạnh, lấy điểm giữa, tìm đoạn TomTom gần nhất trong 20 m có hướng lệch không quá 30 độ. Khớp được thì `g` của cạnh là `traffic_level` của đoạn đó. Bảng khớp chỉ tính một lần cho mỗi thành phố rồi lưu lại, vì hình học của hai bên không đổi.
- **Đường đóng:** cạnh khớp với đoạn có `road_closure` đúng thì không được đi qua.
- **Ghi ra:** `processed/{city}/traffic.parquet` với `edge_id`, `g`, `source`, `observed_at`. File này thuộc phần web, không nằm trong hợp đồng dữ liệu chung.
- **Khi lỗi:** TomTom không trả lời, hoặc số liệu cũ hơn 30 phút, thì lùi về tầng điển hình và nhãn đổi theo.
- **Thư viện:** đọc ô vector cần thêm `mapbox-vector-tile==2.2.0` vào `requirements.txt` (bản này đã dùng trong lần thử). Báo hai người kia khi thêm.

### 2.4 Ngập làm chậm giao thông (S9.4)

Trên cạnh thuộc một đoạn có nguy cơ, tốc độ lúc này được nhân thêm:

| Mức của đoạn | Xe máy | Ô tô |
|---|---|---|
| Vừa | 0,7 | 0,6 |
| Cao | 0,3 | 0,2 |

Hệ số được làm nhẹ theo `loc_weight` của đoạn: `1 − loc_weight × (1 − hệ số)`. Đoạn chưa rõ vị trí chính xác thì bị làm chậm ít hơn. Bốn con số trong bảng là ước lượng do tôi đặt.

Nhờ tầng này, bảng lộ trình nói được một câu mà bản đồ thông thường không nói được: "Bình thường mất 19 phút; lúc này ước 31 phút vì đi qua 350 m nguy cơ ngập cao."

Không mô phỏng ùn tắc lan sang các đường xung quanh. Đây là giới hạn phải nói rõ khi trình diễn.

## 3. Lớp giao thông trên bản đồ (S9.3)

- Bật từ nút "Lớp" (spec 08). Mặc định tắt, để không tranh chỗ với lớp ngập.
- Vẽ các cạnh từ loại `tertiary` trở lên theo `g`: từ 0,55 trở lên không vẽ; từ 0,35 tới 0,55 là "đông", màu cam nhạt; dưới 0,35 là "kẹt", màu đỏ sẫm. Nét mảnh hơn và nằm dưới lớp ngập.
- Hai ngưỡng 0,55 và 0,35 đặt theo lần đo chiều Chủ nhật, khi trung vị đã là 0,64: nếu lấy ngưỡng cao hơn thì gần như cả thành phố có màu. Chỉnh lại sau khi xem một giờ cao điểm ngày thường.
- Chú thích ghi nguồn theo bảng ở mục 2.
- `GET /api/traffic?city=&bbox=&replay=` trả GeoJSON các cạnh có `g` dưới 0,55, kèm `source` và `observed_at`. Tối đa 3.000 cạnh mỗi lần, ưu tiên `g` nhỏ.

## 4. Điều khiển giao thông trong bàn thử

Khi `FLOODRISK_TEST_TOOLS=1`, bàn thử (spec 04) có thêm một ô chọn giao thông cho phiên đang xem: theo thực tế, thông thoáng, giờ cao điểm, hoặc kẹt cục bộ ngẫu nhiên kèm hạt giống. Lựa chọn được gửi kèm mọi lời gọi `route` và `traffic` qua tham số `traffic`. Tham số này bị bỏ qua khi bàn thử tắt.

Mục đích: cho thấy lộ trình và thời gian tới nơi phản ứng đúng khi đường đông lên, kể cả khi lúc trình diễn đường đang vắng. Đây là phần "giả lập mức độ đông" mà chủ dự án đã nêu.

## 5. Ghi lại để học giao thông điển hình (S9.5)

Nếu điều khoản của TomTom cho phép lưu: giữ lại các bảng `g` mỗi 10 phút, và sau vài ngày thay bảng ở mục 2.2 bằng trung vị của `g` theo loại đường, giờ, và ngày thường hay cuối tuần. Khi đó tầng điển hình trở thành số đo thật thay vì số đoán.

Nếu trong những ngày ghi có một trận ngập, số liệu đó còn cho biết hệ số "ngập làm chậm" ở mục 2.4 gần hay xa thực tế.

Chưa đọc được điều khoản thì không làm mục này.

## 6. Nơi đặt mã

| File | Việc |
|---|---|
| `api/traffic.py` | Bảng điển hình; ghép ba tầng thành tốc độ cho từng cạnh theo thành phố, thời điểm, loại xe, bảng nguy cơ |
| `api/tomtom.py` | Lấy ô vector, khớp vào cạnh, ghi `traffic.parquet`; gọi Routing API cho lệnh đối chiếu của spec 05 |
| `api/routes_traffic.py` | `GET /api/traffic` |
| `api/main.py` | Tác vụ nền thứ hai: gọi `tomtom.refresh` mỗi 10 phút khi có `TOMTOM_API_KEY` |

`GET /api/health` thêm `traffic`: nguồn đang dùng cho từng thành phố và thời điểm số liệu.

## 7. Nghiệm thu

**S9.1:**

- [ ] Cùng một lộ trình, thời gian lúc 8 giờ sáng thứ Ba dài hơn lúc 2 giờ sáng. Kiểm thử truyền thời điểm vào, không dùng đồng hồ thật.
- [ ] Trong một kịch bản phát lại, giao thông lấy theo giờ của kịch bản.

**S9.2:**

- [x] Phép thử độ dày dữ liệu đã chạy ngày 04/10/2026: 89% chiều dài đường từ `tertiary` trở lên ở trung tâm TP.HCM khớp được (mục 1.1).
- [ ] Lặp lại phép thử vào một giờ cao điểm ngày thường, và cho Đà Nẵng. Ghi kết quả: ……
- [ ] Với một ô vector mẫu lưu sẵn trong `tests/api/fixtures/`, bước khớp gán đúng `g` cho cạnh nằm trùng, bỏ qua cạnh cách xa hơn 20 m và cạnh lệch hướng quá 30 độ. Kiểm thử không gọi mạng.
- [ ] Không có khóa, hoặc TomTom lỗi: máy chủ vẫn chạy, dùng tầng điển hình, `/api/health` ghi đúng nguồn.
- [ ] Cạnh có `road_closure` không xuất hiện trong lộ trình nào.
- [ ] Một lượt lấy số liệu cho TP.HCM xong dưới 60 giây.

**S9.3:**

- [ ] Bật lớp giao thông thấy các đường đông và kẹt; chú thích ghi đúng nguồn, và có "© TomTom" khi nguồn là TomTom.

**S9.4:**

- [ ] Lộ trình qua đoạn mẫu số 6 (mức cao, `loc_weight` bằng 1) có thời gian dài hơn hẳn so với cùng lộ trình khi mọi đoạn mức thấp.
- [ ] Bảng lộ trình hiện cả thời gian lúc bình thường lẫn thời gian lúc này cho lộ trình đó.

**Bàn thử:**

- [ ] Chọn "giờ cao điểm" làm thời gian mọi lộ trình tăng; chọn "thông thoáng" đưa về như lúc đêm.

## 8. Không làm

- Không dùng Google Maps cho bất cứ số liệu nào.
- Không hiện lộ trình của TomTom cho người dùng. Routing API của TomTom chỉ làm mốc đối chiếu (spec 05, mục 5): thuật toán tìm đường là của nhóm, và điều khoản hiển thị của TomTom chưa được đọc.
- Không mô phỏng ùn tắc lan truyền, không mô phỏng từng xe.
- Không dự báo giao thông cho 1–2 giờ tới. Lời khuyên giờ đi của spec 06 chỉ dựa vào nguy cơ ngập.
- Không đếm xe từ ảnh camera.
