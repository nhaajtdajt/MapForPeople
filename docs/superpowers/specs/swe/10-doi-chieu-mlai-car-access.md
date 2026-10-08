# Ghi chú 10: Đối chiếu với dự án `mlai-car-access` (tên tạm "Vào Được")

Đọc ngày 07/10/2026, tại `D:\HK1 4 year\Hackathon\mlai-car-access`, nhánh `main` (commit `f000823`) và nhánh `docs/rush-hour-eval`. Đây là ghi chú để tham khảo, không phải spec: chưa có việc nào ở đây được đưa vào bảng theo dõi.

**Cách đọc:** tôi đọc mã nguồn, sổ quyết định và các bản đánh giá trong repo đó. Các con số về camera, triều, mưa trong ghi chú này là số bạn ấy ghi lại, trừ bảng độ phủ camera ở mục 4.3 và số tuyến Goong trả về ở mục 3 là tôi tự đo. Sau khi viết ghi chú này tôi đã chạy thử `hydro.py` và `cameras.py` của bạn ấy; kết quả nằm ở ghi chú 11.

**Repo đó là của một thành viên trong nhóm**, làm song song với repo này. Ghi chú này chỉ so sánh và rút ra điểm hay. **Quyết định lấy gì về repo này, theo thứ tự nào, nằm ở ghi chú 11**; chỗ nào hai ghi chú khác nhau thì ghi chú 11 đúng.

## 1. Repo kia làm gì

Cùng đề Tasco & Goong, nhưng khác câu hỏi. Sản phẩm của bạn ấy trả lời: **chiếc ô tô này có vào được con hẻm này và ra lại được không**; nếu không thì đỗ ở đâu và đi bộ bao xa. Bạn ấy chỉ làm ô tô và chỉ làm TP.HCM.

Hai phần của bạn ấy chạm vào việc của mình:

- **Chọn đường lớn từ A tới B** theo kẹt xe và ngập lúc này (`backend/app/corridor.py`, làm ngày 05/10). Đây chính là cách "lấy đường của Goong rồi xét từng đoạn" mà bạn kể.
- **Ngập theo triều, mưa và lịch sử** (`flood.py`, `hydro.py`), dùng đúng bộ IRD mà repo này cũng dùng.

Công nghệ gần như trùng với mình: FastAPI, React, Vite, TypeScript, MapLibre, bản đồ nền Goong.

## 2. Hai bên khác nhau ở đâu

| | Repo này (MapForPeople) | Repo `mlai-car-access` |
|---|---|---|
| Câu hỏi | Đường nào có nguy cơ ngập, đi đường nào để tránh | Xe này vào hẻm này được không, đỗ ở đâu |
| Loại xe | Xe máy và ô tô | Ô tô, theo từng mẫu xe (34 mẫu) |
| Thành phố | TP.HCM và Đà Nẵng | Chỉ TP.HCM |
| Mạng đường | Nạp sẵn cả thành phố (120 nghìn nút, 272 nghìn cạnh) | Tải OpenStreetMap quanh điểm đến, bán kính 1,2 km, khi có yêu cầu |
| Tìm đường A tới B | Thuật toán của nhóm, 1 tới 6 tuyến, khoảng 0,2 giây | Hỏi Goong: 1 tuyến chính và tối đa 4 tuyến "ép đi qua một camera"; khoảng 30 giây khi có đọc camera |
| Thời gian tới nơi | Bảng tốc độ theo loại đường, đã chỉnh cho khớp Goong | Thời gian của Goong nhân hệ số kẹt do camera thấy |
| Giao thông | Chưa có; dự định TomTom và bảng theo giờ (spec 09) | Camera công khai của thành phố, mô hình Gemini đọc ảnh |
| Ngập | Nguy cơ 0 tới 1 cho mỗi đoạn; người AI làm, chưa giao | Khoảng độ sâu (cm) cho mỗi đường, so với mức nước xe lội được |
| Triều và mưa lúc này | Open-Meteo, bản tin triều nhập tay | Đo trực tiếp từ cổng giám sát thiên tai, rồi nối bằng mô hình |
| Kiểm thử | 87 phép thử Python, 19 phép thử web | 22 phép thử cho phần backend |
| Tài liệu | Spec và kế hoạch viết trước | Sổ quyết định viết dần (35 mục), kèm nghiên cứu và đánh giá |

## 3. Cách tìm đường của bạn ấy so với của mình

**Bạn ấy làm thế này.** Hỏi Goong một tuyến ô tô. Chọn tối đa 4 camera nằm lệch hai bên tuyến đó (cách tuyến trên 800 m, ở khoảng giữa chuyến đi), rồi hỏi Goong thêm 4 lần, mỗi lần ép đi qua một camera. Bỏ tuyến dài hơn 1,6 lần hoặc trùng tuyến khác từ 80%. Mỗi tuyến được cộng phút theo mức kẹt camera thấy (đông ×1,3; ùn ứ ×2,0 và thêm 3 phút; kẹt cứng ×4,0 và thêm 10 phút) và bị loại nếu nước sâu hơn mức xe lội được.

| | Cách của bạn ấy | Cách của mình |
|---|---|---|
| Số tuyến xét được | Tối đa 5, và phụ thuộc chỗ đặt camera | Bất kỳ tuyến nào trên mạng đường |
| Tránh một đoạn ngập cụ thể | Chỉ khi một trong 5 tuyến tình cờ không đi qua | Được: tăng thời gian của đúng cạnh đó rồi tìm lại |
| Hiểu cấm rẽ, cấm xe | Có phần, vì đường là của Goong | Thiếu, vì OpenStreetMap thiếu thuộc tính này |
| Số liệu lúc này | Có (camera) | Chưa có |
| Tốc độ trả lời | Khoảng 30 giây, 5 lần gọi Goong | Khoảng 0,2 giây, không gọi ra ngoài |

**Kết luận:** hai cách bù cho nhau chứ không cái nào thay cái nào. Thuật toán của mình hợp hơn cho việc tránh ngập, vì nó phạt được từng đoạn. Cái bạn ấy hơn mình là **nguồn số liệu lúc này**. Chỗ cắm đã có sẵn: tham số `slow` của `find_routes` nhận hệ số làm chậm cho từng cạnh, nên hệ số kẹt từ camera hay từ TomTom đều đưa vào đó được.

### 3.1 Goong có trả nhiều tuyến không

Có, nhưng nhiều nhất là 2. Sổ quyết định của bạn ấy ghi Goong chỉ trả một tuyến cho ô tô và bỏ qua tham số `alternatives`; mã `corridor.py` vì vậy không gửi tham số này. Tôi gọi thử ngày 07/10 bằng khóa của nhóm, trên 16 cặp điểm ngẫu nhiên ở TP.HCM (`/v2/direction`):

| Cách gọi | Trả 1 tuyến | Trả 2 tuyến | Trả 3 tuyến trở lên |
|---|---|---|---|
| Ô tô, `alternatives=true` | 6 | 10 | 0 |
| Xe máy, `alternatives=true` | 7 | 9 | 0 |
| Ô tô, `alternatives=false` | 16 | 0 | 0 |

- Tuyến thứ hai chậm hơn tuyến chính từ 0 tới 12 phút trong các lần thử này; đa số chậm hơn 1 tới 3 phút.
- Chuyến bạn ấy dùng để thử (Quận 1 tới Vạn Phúc City) đúng là chỉ trả 1 tuyến dù có gửi `alternatives=true`. Nhiều khả năng vì vậy mà bạn ấy kết luận Goong bỏ qua tham số.
- Chưa thử: `alternatives=true` có còn tác dụng khi ép đi qua một điểm giữa đường hay không.

**Hệ quả:** thêm `alternatives=true` vào lần gọi đầu thì khoảng 6 trên 10 chuyến có thêm một tuyến mà không tốn lượt gọi nào. Việc này đúng cho cả mã của bạn ấy lẫn việc đưa tuyến Goong vào danh sách ở repo này.

**Giới hạn số lần gọi.** Trong lần thử trước đó, lần gọi thứ sáu liên tiếp bị Goong từ chối (mã 429). Cách gọi Goong 5 lần song song cho một lần tìm đường dễ chạm giới hạn này khi có nhiều người dùng.

## 4. Điểm hay nên học

Xếp theo mức đáng làm đối với mình.

### 4.1 Khi hiện một tuyến, nói luôn lý do và nguồn

Mỗi tuyến của bạn ấy có một danh sách lý do và một câu tóm tắt: "Nên đi qua Điện Biên Phủ (~41 phút), nhanh hơn tuyến Goong gợi ý ~12 phút. Lý do: Camera Đinh Bộ Lĩnh – Bạch Đằng 2 lúc 07:23: kẹt cứng (+10 phút)." Mỗi con số đều kèm nguồn và giờ đo, ví dụ "Triều 1,45 m (BĐ1, mô hình ±15 cm)".

Hai quy tắc viết của bạn ấy đáng lấy nguyên:

- Không viết "Không ngập". Viết "Chưa có ghi nhận ngập" hoặc "Trong ngưỡng của xe", vì không có ghi nhận không có nghĩa là không ngập.
- Số liệu "lúc này" chỉ dùng cho chuyến đi trong khoảng 15 phút trước tới 45 phút sau. Chuyến đi muộn hơn thì chỉ dùng dự báo, và thẻ lộ trình nói rõ điều đó.

**Áp dụng:** làm ngay trong giao diện lộ trình (S5.2). API của mình đã có sẵn trường `notes` và `advice`, hiện đang để trống.

### 4.2 Đoạn không có số liệu không được tính là đường thông

Camera chỉ nhìn một phần tuyến. Phần còn lại bạn ấy gán mức kẹt trung vị của mọi camera vừa đọc, để một tuyến không "nhanh hơn" chỉ vì ít camera nhìn nó.

**Áp dụng:** spec 09 của mình có đúng lỗ hổng này. TomTom phủ 89% đường từ `tertiary` trở lên nhưng chỉ 10% đường dân cư. Bảng giao thông điển hình cho đường dân cư lại gần như thông (0,8 tới 0,9). Giờ cao điểm thuật toán có thể đẩy xe vào hẻm vì hẻm "không kẹt". Cần sửa khi làm S9.2: cạnh không khớp TomTom lấy mức điển hình nhân với tỉ lệ đo được trên các cạnh có khớp ở gần đó.

### 4.3 Camera giao thông công khai của TP.HCM

- Khoảng 800 camera của Cổng thông tin giao thông TP.HCM (796 trong file, 684 đang có hình). Danh sách kèm tọa độ nằm ở `data/cameras/hcmc_cameras.json` bên repo của bạn ấy.
- Mỗi camera chụp hai ảnh cách nhau 13 giây, để thấy xe có nhúc nhích hay không. Gemini đọc 6 camera một lần gọi và trả: mức kẹt (4 mức), có ngập không, nhóm độ sâu, độ tin cậy, giờ in trên ảnh.
- Bạn ấy soi lại bằng mắt 15 ảnh giờ cao điểm sáng 05/10: 13 ảnh khớp, 2 ảnh lệch một mức. Nhãn ngập chưa được kiểm vì sáng đó trời khô.
- Điểm yếu bạn ấy tự ghi: không phân biệt chiều đường; đèn đỏ dễ bị đọc thành ùn ứ; gói Gemini miễn phí chỉ cho 20 lần gọi mỗi khóa mỗi ngày, nên bạn ấy xoay vòng 11 khóa.

**Đối với mình:** camera cho được hai thứ từ một lần đọc: đường có ngập không, và đường đông tới mức nào. Một camera đọc ra "ngập 25 cm" được xử lý như một báo cáo của người dùng. Cách dùng cụ thể nằm ở ghi chú 11, quyết định 4 và 6. Việc này cần một khóa Gemini.

**Camera phủ được bao nhiêu** (đo ngày 07/10 trên `units.parquet` thật của TP.HCM và bộ IRD; chỉ tính 684 camera đang có hình):

| Câu hỏi | Kết quả |
|---|---|
| Bao nhiêu đoạn đường nằm trong 150 m quanh một camera | 4.664 trên 43.352 đoạn (11% số đoạn, 14% chiều dài); riêng đường từ `tertiary` trở lên là 26% chiều dài |
| Ghi nhận ngập IRD có vị trí chính xác cao hoặc trung bình (177 dòng) có camera trong 150 m | 31 dòng (18%); trong 300 m là 66 dòng (37%) |
| Chín con đường ngập lặp lại nhiều năm có camera trong 80 m | 7 trên 9: Nguyễn Hữu Cảnh 10 camera, Huỳnh Tấn Phát 10, Nguyễn Duy Trinh 6, Võ Văn Ngân 5, Kha Vạn Cân 4, Ung Văn Khiêm 4, Thảo Điền 1. Quốc Hương và Nguyễn Văn Hưởng không có |

Camera ở gần một con đường chưa chắc nhìn đúng khúc hay ngập. Kết luận từ bảng: camera xác nhận tốt cho các trục lớn hay ngập, nhưng không phủ được phần lớn bản đồ.

### 4.4 Ngập so với từng loại xe

Bạn ấy không hỏi "đường này ngập không" mà hỏi "nước ở đây có quá mức chiếc xe này lội được không": khoảng độ sâu thấp nhất tới cao nhất, so với ngưỡng của xe (Vios 13 cm, Fortuner 35 cm). Kết quả là qua được, rủi ro, hoặc không qua được. Nước chảy do mưa từ 30 cm thì chặn mọi xe.

**Đối với mình:** tiêu chí "phù hợp với Việt Nam" đòi xe máy và ô tô được tính khác nhau. Hiện mức nguy cơ của mình giống nhau cho hai loại xe. Dữ liệu nguy cơ của mình có sẵn "độ sâu lớn nhất từng ghi nhận"; khi làm tránh ngập (S5.4) có thể dùng nó với hai ngưỡng khác nhau cho xe máy và ô tô. Phần này cần bàn với người AI.

### 4.5 Công tắc cho từng nguồn dữ liệu

Mỗi nguồn (camera, triều đo trực tiếp, lịch sử ngập, tin rao…) có một công tắc bật tắt ngay trên giao diện. Tắt thì hệ thống chạy như thể nguồn đó không tồn tại. Lúc trình diễn, việc này cho thấy từng nguồn đóng góp gì, và cứu được buổi diễn khi một nguồn hỏng.

**Áp dụng:** mình đã có `/api/health` báo phần nào thật, phần nào giả. Thêm công tắc cho "giao thông" và "chậm do ngập" khi làm S9 là việc nhỏ.

### 4.6 Chịu lỗi khi gọi nguồn ngoài

Một hàm nhỏ `_cached` trong `hydro.py` làm ba việc: giữ kết quả trong một thời hạn; khi nguồn hỏng thì dùng tiếp kết quả tốt gần nhất; thử lại sau một phút chứ không chờ hết thời hạn. Thêm vào đó luôn có một file đóng sẵn làm phương án cuối.

**Áp dụng:** dùng đúng mẫu này khi mình nối TomTom và Open-Meteo.

### 4.7 Giao diện

- Bản đồ phủ kín màn hình; thẻ chỉ đường nổi lên trên, có điểm đi, điểm đến, vị trí của tôi, nút đổi chiều. Trên điện thoại kết quả nằm trong tấm trượt từ dưới lên.
- Đổi bất kỳ ô nào là tự tìm lại, chờ 0,2 giây. Mỗi yêu cầu có một số thứ tự; kết quả của yêu cầu cũ về muộn thì bị bỏ.
- Nhấn giữ (hoặc chuột phải) trên bản đồ để đặt điểm đi hoặc điểm đến.
- Số viết kiểu Việt Nam (dấu phẩy thập phân). Không viết hoa toàn bộ nhãn vì chữ hoa làm mất dấu.
- Mọi màu, cỡ chữ, khoảng cách nằm trong một file (`frontend/src/ds/tokens.css`).

**Áp dụng:** lấy bốn ý đầu khi làm S5.2.

### 4.8 Thứ nên chuyển cho hai bạn kia

| Cho ai | Thứ gì | Ở đâu trong repo của bạn ấy |
|---|---|---|
| Người dữ liệu | Cách gắn một ghi nhận ngập IRD vào đường: độ chính xác cao thì trong 50 m; trung bình thì trong 120 m và cùng tên đường (hoặc trong 40 m); cùng tên đường thì trong 700 m. Hẻm mở ra đường ngập thì thừa hưởng ghi nhận của đường đó | `flood.py`, hàm `flood_profiles` |
| Người dữ liệu | Bộ IRD đã đổi sẵn sang GeoJSON hệ tọa độ thường dùng | `data/flood/ird-hcmc/flood_points.geojson` |
| Người AI | Triều tại Phú An: lấy mực nước biển của Open-Meteo ở cửa Soài Rạp, rồi tìm độ trễ, hệ số và độ lệch cho khớp số đo 7 ngày gần nhất. Sai số bạn ấy đo được 0,14 m; khi dùng thì mang theo khoảng ±0,15 m | `hydro.py`, hàm `_fit` và `tide_point` |
| Người AI | Mưa: lấy trạm ướt hơn trong hai trạm gần nhất (trong 5 km), vì bỏ sót một trận mưa tệ hơn báo thừa. Mỗi giờ mưa còn tính thêm 1 giờ vì đường thoát nước chậm | `hydro.py`, hàm `rain_spells` |

## 5. Chỗ repo này làm tốt hơn, nên giữ

- **Thuật toán tìm đường riêng.** Trả lời trong khoảng 0,2 giây thay vì khoảng 30 giây, không tốn lượt gọi Goong, và là cách duy nhất để tránh đúng đoạn ngập.
- **Hai thành phố và xe máy.** Gần như mọi nguồn của bạn ấy chỉ có ở TP.HCM.

## 6. Lấy gì về repo này

Xem ghi chú 11. Tóm tắt phần liên quan tới repo `mlai-car-access`:

| Lấy | Dùng ở đâu |
|---|---|
| `hydro.py`: mưa từng giờ của 44 trạm, mực nước Phú An | Nâng mức nguy cơ tại chỗ (ghi chú 11, quyết định 4) |
| `cameras.py` và phần gọi Gemini của `ai.py` | Bằng chứng ngập và mức kẹt xe (quyết định 4 và 6) |
| Câu tóm tắt và danh sách lý do cho mỗi lộ trình; tự tìm lại khi đổi ô; nhấn giữ để đặt điểm; nút đổi chiều | Giao diện lộ trình |
| Quy tắc "đoạn không có số liệu lấy mức chung" (mục 4.2); mẫu chịu lỗi (mục 4.6); công tắc nguồn (mục 4.5) | Giao thông và các nguồn trực tiếp |
