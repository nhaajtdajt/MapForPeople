# Lớp nguy cơ ngập đường và tìm đường tránh ngập — bản thiết kế

- **Ngày viết:** 04/10/2026
- **Bối cảnh:** hackathon "Xây dựng lớp ứng dụng cho bản đồ của người Việt" (đề bài trong `de.md`)
- **Hạn hoàn thành:** khoảng 1,5 tuần kể từ ngày viết (quanh 14–15/10/2026)
- **Nhóm:** 3 người (một người dữ liệu, một người AI, một kỹ sư phần mềm); chưa có người làm GIS hay thủy lực; làm việc cùng AI agent
- **Trạng thái:** thiết kế, chưa có code
- **Chi tiết kỹ thuật đã chốt:** `docs/superpowers/plans/2026-10-04-00-quyet-dinh-ky-thuat.md` (bản 3). Khi hai tài liệu khác nhau thì tài liệu đó đúng.

> **Cách đọc file này.** Đây là bản thiết kế ban đầu: nó giải thích bài toán, các nguồn dữ liệu và lý do chọn hướng làm. Sau khi viết nó, nhóm đã xem lại dữ liệu có sẵn và cho một agent độc lập phản biện hai vòng. Các mục 4 (mô hình), 7 (kiểm chứng) và 9 (phân công, lịch) đã được thay bằng các mục 4, 4.9 và 11 của tài liệu quyết định kỹ thuật. Ba thay đổi lớn nhất: nguy cơ lấy từ lịch sử ngập trước rồi mới tới mô hình; có chế độ phát lại một ngày ngập để trình diễn; và mốc chạy thật được kéo từ ngày 6 về ngày 3.

## 1. Mục tiêu

Xây một lớp dữ liệu trên bản đồ Goong cho biết nguy cơ ngập của từng tuyến đường đô thị theo giờ, và dùng nó cho ba tính năng:

1. **Tìm đường tránh ngập** (tính năng chính).
2. **Cảnh báo sớm** nguy cơ ngập trong 1–2 giờ tới.
3. **Bản đồ ngập hiện tại**, được sửa theo báo cáo của người dùng.

Người dùng mục tiêu là người đi xe máy và ô tô trong đô thị.

### Vì sao chọn hướng này theo đề bài

- AI chỉ chiếm 10/100 điểm, tiêu chí là dùng AI "phù hợp".
- 15 điểm cho việc phù hợp điều kiện dữ liệu Việt Nam và chiến lược thu thập dữ liệu.
- 10 điểm cho khả năng mở rộng và tích hợp hệ sinh thái di chuyển.
- Đề cho phép dữ liệu giả lập đại diện cho dữ liệu có thể xin từ Sở, ngành, miễn ghi rõ.
- Dữ liệu cộng đồng được nêu đích danh.

## 2. Phạm vi

### Trong bản hackathon

- Ngập đô thị do **mưa** và do **triều**.
- Quy trình chạy được cho bất kỳ thành phố nào bằng một lệnh.
- **TP.HCM** và **Đà Nẵng** là hai thành phố có học và có kiểm chứng.
- Dự báo ở hai cấp: **đoạn** dài tối đa khoảng 200 m, nằm trong **tuyến** dài tối đa khoảng 1 km. Đầu ra là chỉ số nguy cơ và ba mức nguy cơ.
- Điểm của mỗi đoạn lấy từ lịch sử ngập trước; mô hình chỉ bổ sung cho nơi chưa có lịch sử, và chỉ khi qua kiểm chứng.
- Báo ngập một chạm và hiển thị số người đã báo.

### Làm nếu còn thời gian

- **Hà Nội:** kiểm thử Mô hình 1 trên 45 điểm hay ngập, và dùng trạng thái điểm ngập trực tiếp làm bằng chứng.
- **Bộ đọc báo bằng mô hình ngôn ngữ**, trình diễn cách dựng ghi nhận ngập cho một thành phố mới.

### Không làm trong bản hackathon

- Mô phỏng thủy lực (SWMM, mô hình dòng chảy 2D) và LarNO.
- Dự báo độ sâu theo cm.
- Lũ sông, lũ quét, ngập trên quốc lộ ngoài đô thị.
- Đọc ảnh người dùng gửi; đọc camera thành phố.
- Gợi ý giờ khởi hành.
- Lan bằng chứng sang tuyến lân cận; tự động huấn luyện lại từ báo cáo.

## 3. Dữ liệu

Trạng thái "đã xác nhận" nghĩa là đã mở trang và thấy dữ liệu trong ngày 04/10/2026.

### 3.1 Các lần ngập đã ghi nhận (dùng để học và kiểm chứng)

| Thành phố | Nguồn | Nội dung | Giới hạn |
|---|---|---|---|
| TP.HCM | Bộ IRD trên Dataverse (doi:10.23708/8Y16HU) | 425 quan sát, 2002–08/2026, file GPKG có tọa độ | Chỉ 64 ngày khác nhau; 63 dòng không có ngày; 341 dòng là một điểm đại diện cả tuyến; 257 dòng không rõ nhóm độ sâu; tổng hợp chủ yếu từ báo chí nên thiên về đường lớn |
| TP.HCM | 34 tuyến ngập Sở Xây dựng công bố 6/2026 (26 do mưa, 8 do triều) | Tên đường trong bài báo | Không có ngày và tọa độ; phải định vị bằng Goong Forward Geocode rồi soát bằng mắt |
| Đà Nẵng | Cổng `muangap.danang.gov.vn` | 633 phản ánh, 35 ngày (14/10/2022–04/08/2026), đều có tọa độ và độ sâu cm | 392 bản ghi thuộc riêng ngày 14/10/2022; không ghi giấy phép dữ liệu mở |
| Hà Nội | `thoatnuochanoi.vn/ungngap` | 45 điểm có tọa độ, cấp ngập hiện tại | Không có lịch sử theo trận mưa; không ghi giấy phép |

Phân bố nguyên nhân trong bộ IRD: 198 do mưa, 176 do triều, 51 kết hợp.

### 3.2 Đặc điểm cố định của tuyến

| Dữ liệu | Nguồn | Giới hạn |
|---|---|---|
| Mạng đường | OpenStreetMap | Goong không có chức năng xuất cả mạng đường; nếu Ban Tổ chức cấp bộ dữ liệu đường thì thay thế |
| Địa hình | FABDEM 30 m (bắt đầu), DeltaDTM 30 m (thay vào khi tải xong) | DeltaDTM sai số trung bình 0,43 m nhưng chỉ phủ vùng dưới 10 m và nặng 17,3 GB; FABDEM sai số lớn hơn và giấy phép phi thương mại (chưa xác nhận) |
| Sông, kênh rạch | OpenStreetMap | Kênh nhỏ có thể thiếu |
| Lớp phủ bề mặt | ESA WorldCover 10 m | Chỉ phân biệt được vùng xây dựng, không phân biệt loại mặt đường |
| Bổ sung riêng TP.HCM | HCMGIS WFS: sụt lún, điểm cao độ, ranh phường | Không ghi giấy phép; chỉ dùng cổng WFS công khai |

Lưới 30 m không đủ để tính độ sâu ngập. Nó chỉ được dùng để tính các đặc điểm tương đối (trũng hơn hay cao hơn xung quanh).

### 3.3 Mưa

| Nguồn | Loại | Vai trò | Giới hạn |
|---|---|---|---|
| Open-Meteo | Mô hình, không cần khóa | **Mặc định**: lịch sử theo giờ để học, dự báo để chạy | Không phải số đo; dữ liệu 15 phút ở Việt Nam là nội suy từ dữ liệu giờ; bỏ sót mưa dông cục bộ |
| JAXA GSMaP | Vệ tinh, 0,1°, theo giờ, lịch sử từ 2017 | Nâng cấp nếu đăng ký xong trước hết ngày 4 | Cần đăng ký tài khoản, lấy file qua FTP |
| VRain, địa chỉ công khai | Trạm đo, không cần khóa | Mưa các giờ đã qua lúc chạy thật | Chỉ có số hiện tại, cộng dồn từ 19 giờ hôm trước; không có lịch sử |
| VRain, API có khóa | Trạm đo | Nâng cấp cho việc học nếu có khóa và có lịch sử trước hết ngày 4 | Đang xin khóa; cần hỏi thêm lịch sử và tọa độ trạm |
| Cổng Đà Nẵng | 86 trạm đo mưa | Nâng cấp cho Đà Nẵng nếu được phép | API không có tài liệu hay điều khoản |
| RainViewer | Radar, 10 phút, không cần khóa | Chỉ làm lớp hiển thị "đang mưa ở đâu" | Chỉ giữ 2 giờ, là ảnh màu chứ không phải mm, điều khoản chỉ cho cá nhân và giáo dục |

**Quy tắc:** Mô hình 2 phải học và chạy thật trên cùng một nguồn mưa. Hết ngày 4 mà chưa có nguồn nâng cấp kèm lịch sử thì ở lại với Open-Meteo.

### 3.4 Triều

- **Nguồn:** chuỗi mực nước theo giờ trạm Vũng Tàu của UHSLC (2007–07/2026).
- **Cách dùng:** phân tích điều hòa để tính triều thiên văn cho bất kỳ thời điểm nào, dùng cùng một cách tính cho lúc học và lúc chạy.
- **Giới hạn:** Vũng Tàu là trạm ven biển. Nó không phản ánh mực nước kênh rạch nội thành, xả hồ thượng nguồn hay nước dâng do gió.
- **Phạm vi:** chỉ áp dụng cho TP.HCM. Đà Nẵng và Hà Nội có thành phần triều bằng 0.
- **Bản tin chính thức:** Đài KTTV Nam Bộ phát bản tin triều lúc 9 giờ mỗi ngày dưới dạng PDF, có đỉnh triều dự báo tại trạm Phú An và ba cấp báo động 1,4 m, 1,5 m, 1,6 m. Lúc chạy thật, bản tin này được ưu tiên hơn triều thiên văn Vũng Tàu; nó phải được nhập tay mỗi ngày.

### 3.5 Không lấy được

- Mạng cống, hố ga, trạm bơm, cống ngăn triều.
- Mực nước Phú An, Nhà Bè; dữ liệu radar Nhà Bè dạng số.
- Trạm đo của Trung tâm chống ngập TP.HCM (máy chủ dữ liệu đang lỗi).
- Dữ liệu giao thông từ Goong. Danh mục API được cấp gồm Autocomplete, Forward/Reverse Geocode, Place Detail, Distance Matrix, Direction, Speed Limit, Area Speed Limit, Area Speedcam, Geo Location, Static Map, Trip và Map; không có mức ùn tắc.
- VNDMS: xem được trong trình duyệt nhưng chặn truy cập tự động; không tìm cách vượt.

### 3.6 Năm loại nguồn gốc

Mọi thông tin trên bản đồ mang một trong năm nhãn nguồn gốc, hiển thị khác nhau:

1. **Quan sát chính thức:** IRD, cổng Đà Nẵng, điểm ngập Hà Nội.
2. **Người dùng báo.**
3. **AI trích từ báo chí**, kèm đường dẫn bài gốc.
4. **Mô hình dự báo.**
5. **Giả lập:** dữ liệu giao thông và camera mẫu, đại diện cho dữ liệu có thể xin từ Sở, ngành.

Bản hackathon không có dữ liệu mô phỏng thủy lực.

## 4. Mô hình

### 4.1 Đơn vị dự báo

Có hai cấp. **Đoạn** là các khúc của một con đường có tên, mỗi khúc dài không quá 200 m, gộp theo ô lưới 200 m; bản đồ tô màu, báo cáo người dùng và chấm điểm lộ trình đều theo đoạn. **Tuyến** là nhóm các đoạn của cùng con đường trong một ô lưới 1 km; đây là cấp lùi khi ghi nhận chỉ nêu tên đường hoặc khi mô hình không định vị được trong tuyến. Đường không tên bị loại khỏi bản hackathon. Ô lưới được chọn thay cho ranh phường vì ranh phường trong OpenStreetMap không đồng nhất sau đợt sáp nhập 2025.

Các mục 4.2 đến 4.6 dưới đây viết khi đơn vị còn là tuyến; chữ "tuyến" trong đó nay hiểu là "đoạn". Ba điểm đã đổi so với các mục đó được mô tả đầy đủ trong tài liệu quyết định kỹ thuật, mục 4:

- Ghi nhận ngập được gán theo độ chính xác vị trí của nó: chính xác dưới 100 m thì gán vào một đoạn, chỉ có tên đường thì gán cho cả tuyến.
- Lịch sử ngập được đưa thẳng vào nguy cơ dưới dạng điểm lịch sử; Mô hình 1 chỉ bổ sung khi qua cổng kiểm chứng.
- Lúc chạy thật, mưa các giờ đã qua lấy từ trạm đo VRain công khai, và triều lấy từ bản tin trạm Phú An khi có.

Lý do: phần lớn ghi nhận chỉ có một điểm đại diện cho cả tuyến, nên không kiểm chứng được ở mức mịn hơn.

### 4.2 Mô hình 1: độ dễ ngập của tuyến

- **Câu hỏi:** tuyến này có thuộc loại dễ ngập không?
- **Đầu ra:** hai điểm số cố định từ 0 đến 1 cho mỗi tuyến, `S_mưa` và `S_triều`.
- **Nhãn:** `S_mưa` học từ tuyến có ít nhất một ghi nhận do mưa hoặc kết hợp; `S_triều` học từ tuyến có ít nhất một ghi nhận do triều hoặc kết hợp. Ghi nhận ở Đà Nẵng được coi là do mưa (giả định).
- **Tuyến không có ghi nhận** được coi là "chưa biết", đưa vào học như mẫu âm với trọng số thấp.
- **Đầu vào:**
  - cao độ thấp nhất và trung bình của tuyến;
  - độ trũng so với vùng 300 m và 1 km xung quanh;
  - khoảng cách tới sông, kênh gần nhất;
  - tỉ lệ vùng xây dựng trong bán kính 200 m;
  - loại đường.
- **Không đưa vào đầu vào:** tọa độ, tên đường, tên phường, tên quận, và việc tuyến từng ngập hay chưa.
- **Loại mô hình:** cây tăng cường nhỏ (XGBoost hoặc LightGBM), so với hồi quy logistic.
- **`S_triều`** chỉ học và dùng ở TP.HCM.

### 4.3 Mô hình 2: mức kích hoạt

- **Câu hỏi:** mưa hoặc triều lúc này đã tới mức gây ngập chưa?
- **Đầu ra:** `T_mưa` và `T_triều` từ 0 đến 1, đổi theo giờ.
- **`T_mưa`:** đường cong logistic một chiều theo mưa tích lũy 3 giờ lớn nhất và mưa 24 giờ trước đó, lấy tại vị trí tuyến.
- **`T_triều`:** đường cong logistic một chiều theo đỉnh triều thiên văn tại Vũng Tàu.
- **Khớp riêng cho từng thành phố**, vì khả năng thoát nước mỗi nơi khác nhau.
- **Mẫu dương:** các ngày có ghi nhận ngập theo nguyên nhân tương ứng. **Mẫu âm:** các ngày khác trong mùa mưa cùng giai đoạn, lấy mẫu ngẫu nhiên.
- **Giới hạn:** ghi nhận chỉ có ngày, không có giờ, nên đường cong được khớp ở mức ngày rồi áp dụng theo cửa sổ giờ khi chạy thật.

### 4.4 Ghép

Tuyến ngập khi nó dễ ngập do mưa và mưa đủ lớn, hoặc dễ ngập do triều và triều đủ cao:

```
P = 1 − (1 − S_mưa × T_mưa) × (1 − S_triều × T_triều)
```

`P` là chỉ số nguy cơ từ 0 đến 1, không phải xác suất đã hiệu chỉnh, vì dữ liệu ghi nhận thiên lệch theo việc báo chí có đưa tin hay không.

Ba mức nguy cơ lấy theo phân vị của `P` trên các ngày ngập trong dữ liệu học. Giá trị khởi đầu: **cao** là 5% trên cùng, **vừa** là 15% kế tiếp, **thấp** là phần còn lại. Các ngưỡng này được chỉnh sau khi xem dữ liệu.

### 4.5 Bước 3: sửa theo bằng chứng

**Một bản ghi bằng chứng** gồm: nguồn, loại nguồn gốc, thời gian, tuyến, trạng thái, mã người báo ẩn danh.

**Trạng thái** người dùng chọn bằng một chạm. Hai mốc 10 cm và 30 cm lấy từ thang cấp ngập của Công ty Thoát nước Hà Nội:

| Trạng thái | Độ sâu tương ứng | Ý nghĩa với xe |
|---|---|---|
| Ngập nhẹ | dưới 10 cm | Đi bình thường |
| Ngập vừa | 10–30 cm | Xe máy nên tránh |
| Ngập cao | trên 30 cm | Không nên đi |
| Không ngập / đã rút | — | — |

**Quy tắc cập nhật:**

- Mỗi người chỉ tính một lần cho một tuyến trong 30 phút.
- Hiệu lực của mỗi báo cáo giảm một nửa sau mỗi 30 phút.
- Mỗi báo cáo "ngập" còn hiệu lực nhân tỉ số odds của `P` với 3; mỗi báo cáo "không ngập" chia cho 3. Con số 3 là giá trị khởi đầu.
- Nguồn chính thức trực tiếp (cổng Đà Nẵng, điểm ngập Hà Nội) dùng hệ số 10.
- Mức ngập hiển thị là mức được báo nhiều nhất trong các báo cáo còn hiệu lực.
- Bản đồ hiện số người đã báo, ví dụ "4 người đã báo ngập ở đây trong 20 phút qua".
- Khi người dùng đi qua tuyến có nguy cơ vừa hoặc cao, ứng dụng hỏi "đoạn này có ngập không?" để thu cả câu trả lời "không ngập".

**Chỗ cắm giả lập:** giao thông và camera có sẵn định dạng bản ghi bằng chứng, chạy bằng dữ liệu mẫu có nhãn "giả lập".

### 4.6 Mức độ ngập và phạm vi ngập

- **Mức độ ngập** không do mô hình dự báo. Nó lấy từ độ sâu lớn nhất từng ghi nhận ở tuyến đó (nhãn "đã từng ghi nhận") và từ báo cáo cộng đồng khi có.
- **"Ngập từ đâu tới đâu"** được suy ra bằng cách tô các đoạn thấp nhất của tuyến theo địa hình, hiển thị là ước lượng chưa kiểm chứng.

## 5. Quy trình dữ liệu

### 5.1 Bảng ghi nhận ngập chung

Mọi nguồn được đưa về cùng một dạng bản ghi:

| Trường | Ghi chú |
|---|---|
| Thành phố, tuyến | Gán bằng tên đường và khoảng cách tới đường gần nhất |
| Tọa độ, độ chính xác vị trí | Điểm, đoạn, hoặc cả tuyến |
| Ngày, giờ | Giờ để trống nếu nguồn không có |
| Có ngập hay không | |
| Độ sâu cm, nhóm độ sâu | Để trống nếu không rõ |
| Nguyên nhân | Mưa, triều, kết hợp, không rõ |
| Nguồn, loại nguồn gốc, đường dẫn bằng chứng | |

Ghi nhận không có ngày chỉ dùng cho Mô hình 1.

### 5.2 Đặc điểm tuyến, một lệnh cho mỗi thành phố

1. Tải mạng đường và sông kênh OpenStreetMap theo khung bao của thành phố.
2. Gộp đoạn đường thành tuyến trong phường.
3. Cắt địa hình và lớp phủ theo khung bao, tính các đặc điểm ở mục 4.2.
4. Xuất bảng đặc điểm và hình học tuyến.

### 5.3 Chạy thật

- **Mỗi giờ:** lấy mưa dự báo, tính `T_mưa`, `T_triều`, ghép với `S`, xuất nguy cơ cho giờ hiện tại và từng mốc giờ trong 2 giờ tới.
- **Mỗi khi có báo cáo:** cập nhật `P` của tuyến liên quan theo mục 4.5.

### 5.4 Ghi dữ liệu trực tiếp trong thời gian hackathon

Mỗi 10–15 phút, lưu lại: phản ánh và trạm báo ngập Đà Nẵng, điểm ngập Hà Nội, dự báo mưa Open-Meteo. Tháng 10–11 còn mưa và triều cường ở TP.HCM và là mùa mưa ở Đà Nẵng, nên mỗi trận là dữ liệu thật để kiểm tra và trình diễn.

### 5.5 Bộ đọc báo (nếu còn thời gian)

- **Vào:** nội dung một bài báo về ngập.
- **Ra:** ngày, tên đường, đoạn từ đâu tới đâu nếu bài có nêu, độ sâu, nguyên nhân, và nguyên câu trích làm bằng chứng. Trường nào bài không nêu thì để trống.
- **Định vị** bằng Goong Forward Geocode, rồi gán vào tuyến.
- **Soát tay** 20 bài trước khi đưa kết quả vào bảng ghi nhận.
- **Lưu** dữ kiện trích được và đường dẫn, không lưu nội dung bài.

## 6. Đầu ra trên bản đồ Goong

### 6.1 Hợp đồng dữ liệu giữa phần mô hình và phần web

Phần mô hình xuất, cho mỗi thành phố:

- **Hình học tuyến:** mã tuyến, tên đường, đường nét, đoạn thấp nhất.
- **Nguy cơ theo giờ:** mã tuyến, mốc giờ, `P`, mức nguy cơ, `S_mưa`, `S_triều`, loại nguồn gốc, số báo cáo còn hiệu lực, độ sâu lớn nhất từng ghi nhận.
- **Mức tin cậy của thành phố:** đã kiểm chứng hoặc ước lượng chưa kiểm chứng.

Phần web chỉ đọc ba thứ này, nên có thể phát triển song song bằng dữ liệu mẫu.

### 6.2 Tính năng

- **Lớp nguy cơ:** tô màu tuyến theo ba mức. Nét liền là có ghi nhận hoặc báo cáo; nét đứt là mô hình dự báo.
- **Tìm đường tránh ngập:**
  1. Gọi Goong Direction với lộ trình thay thế.
  2. Với mỗi lộ trình, tìm các tuyến nó đi qua (trong vùng đệm 15 m) và cộng nguy cơ theo chiều dài.
  3. Đề xuất lộ trình ít nguy cơ nhất có thời gian không quá 1,5 lần lộ trình nhanh nhất, kèm thời gian chênh.
  4. Nếu mọi lộ trình đều qua tuyến nguy cơ cao, thử tối đa 2 điểm trung gian (hai bên tuyến ngập) trên tuyến nguy cơ thấp gần đó để ép đường vòng.
- **Cảnh báo sớm:** nguy cơ theo từng mốc giờ trong 2 giờ tới cho tuyến hoặc khu vực đã lưu.
- **Báo ngập một chạm** và số người đã báo.

Goong không có tham số "tránh khu vực", nên tìm đường tránh ngập là chọn trong các phương án Goong đưa ra, không phải lời giải tối ưu.

## 7. Kiểm chứng

**Mục này đã được thay bằng mục 4.9 của tài liệu quyết định kỹ thuật.** Phép "ghép cả hai" dưới đây bị bỏ vì nó không thể trượt, và việc chọn mô hình nay chỉ dùng dữ liệu trước 2025. Nội dung cũ được giữ lại để đối chiếu.

Hai phép kiểm, mỗi phép so với một cách làm đơn giản.

| Phép kiểm | Chia dữ liệu | So với | Đo bằng |
|---|---|---|---|
| **Mô hình 1, khác thành phố** | Học TP.HCM, kiểm tra Đà Nẵng; rồi đảo lại | Xếp hạng chỉ theo cao độ thấp; chỉ theo gần sông kênh | Trong 10% tuyến điểm cao nhất có bao nhiêu phần trăm tuyến từng ngập |
| **Ghép cả hai** | Giữ lại các ngày ngập 2025–2026 của hai thành phố | Danh sách tuyến từng ngập trước 2025 | Tuyến có ghi nhận ngập hôm đó có rơi vào mức vừa hoặc cao không |

- **Bộ kiểm tra cuối** (2025–2026) được khóa và chỉ dùng một lần.
- **Mọi con số kèm khoảng dao động**, vì số ngày ít.
- **Phương án lùi:** nếu Mô hình 1 không thắng quy tắc đơn giản thì dùng quy tắc đơn giản và nói rõ.

Điều hai phép kiểm này không chứng minh được:

- Ngập do triều chỉ kiểm được trong TP.HCM.
- Tuyến không có ghi nhận chưa chắc là không ngập, nên không báo cáo tỉ lệ báo nhầm như một con số chắc chắn.
- Báo chí thiên về đường lớn; mô hình có thể đang học "đường lớn thì ngập".
- Phạm vi ngập trong một tuyến và mức độ ngập chưa được kiểm chứng.

## 8. Mở rộng sang thành phố mới

| Dùng chung | Phải làm lại |
|---|---|
| Quy trình tính đặc điểm tuyến | Ghi nhận ngập địa phương |
| Mô hình 1 | Đường cong kích hoạt của Mô hình 2 |
| Nguồn mưa mặc định | Trạm triều, nếu là thành phố ven biển |
| Bộ đọc báo, ứng dụng web | Nguồn mưa trạm đo, nếu có |

Thành phố chưa có ghi nhận ngập vẫn có lớp nguy cơ, nhưng mang nhãn "ước lượng chưa kiểm chứng". Báo cáo cộng đồng là cách thành phố đó dần có dữ liệu riêng.

## 9. Phân công và thứ tự làm trong 10 ngày

**Mục này đã được thay bằng mục 11 của tài liệu quyết định kỹ thuật.** Khác biệt chính: triều, tác vụ mỗi giờ và phát lại do người AI làm; mốc chạy thật là ngày 3; Mô hình 1 chỉ làm nếu địa hình xong đúng hạn. Nội dung cũ được giữ lại để đối chiếu.

Ba người làm song song sau khi chốt hợp đồng dữ liệu ở mục 6.1. Ranh giới trách nhiệm:

- **Người dữ liệu** lo mọi thứ đi vào mô hình, cả lịch sử lẫn trực tiếp.
- **Người AI** lo phần tính điểm: từ dữ liệu vào ra nguy cơ theo tuyến theo giờ, và kiểm chứng.
- **Kỹ sư phần mềm** lo phần phục vụ và hiển thị: máy chủ, lưu báo cáo, giao diện, tìm đường.

### 9.1 Lịch theo ngày

| Ngày | Người dữ liệu | Người AI | Kỹ sư phần mềm |
|---|---|---|---|
| 1 | Tải dữ liệu; bật ghi dữ liệu trực tiếp; đăng ký JAXA; gửi thư xin phép | Chốt hợp đồng dữ liệu; tạo lớp nguy cơ mẫu | Khung web, bản đồ Goong, tìm địa điểm |
| 2 | Bảng ghi nhận ngập hai thành phố; bảng mưa và triều lịch sử | Hàm ghép và hàm cập nhật bằng chứng, có kiểm thử; khung đánh giá | Lớp nguy cơ từ dữ liệu mẫu: ba mức màu, nét liền và đứt |
| 3 | Tuyến và đặc điểm tuyến TP.HCM | Mô hình 2 cho hai thành phố | Máy chủ: đọc lớp nguy cơ, lưu báo cáo; báo ngập một chạm |
| 4 | Tuyến và đặc điểm tuyến Đà Nẵng | Mô hình 2 xong; Mô hình 1 trên TP.HCM | Số người đã báo; bắt đầu tìm đường |
| 5 | Soát việc gán ghi nhận vào tuyến; thay FABDEM bằng DeltaDTM | Mô hình 1 xong; kiểm chéo thành phố | Tìm đường tránh ngập |
| 6 | Tác vụ mỗi giờ: lấy mưa dự báo, gọi hàm tính điểm, ghi kết quả | Hàm tính nguy cơ theo giờ; chọn ngưỡng ba mức | Cảnh báo sớm; nối hàm cập nhật bằng chứng |
| 7–8 | Chiến lược dữ liệu và giấy phép cho bài thuyết trình; ghép bài | Phép kiểm ghép 2025–2026; số liệu và hình | Nối dữ liệu thật; đưa bản demo lên mạng; sửa lỗi |
| 9 | Hà Nội, nếu còn thời gian | Bộ đọc báo, nếu còn thời gian | Hoàn thiện giao diện; kịch bản trình diễn |
| 10 | Tổng duyệt và dự phòng | Tổng duyệt và dự phòng | Tổng duyệt và dự phòng |

### 9.2 Các mốc bàn giao

Bảng dưới là bản đầu. Bản đã cập nhật theo kế hoạch triển khai nằm ở mục 13 của tài liệu quyết định kỹ thuật, và các việc từng ngày của mỗi người nằm trong bốn file kế hoạch `docs/superpowers/plans/2026-10-04-01` đến `04`.

| Hạn | Từ | Tới | Giao cái gì |
|---|---|---|---|
| Hết ngày 1 | AI | Kỹ sư phần mềm | Hợp đồng dữ liệu và lớp nguy cơ mẫu |
| Hết ngày 2 | Dữ liệu | AI | Bảng ghi nhận ngập hai thành phố; bảng mưa và triều lịch sử |
| Hết ngày 3 | Dữ liệu | AI, kỹ sư phần mềm | Hình học tuyến và đặc điểm tuyến TP.HCM |
| Hết ngày 4 | Dữ liệu | AI, kỹ sư phần mềm | Hình học tuyến và đặc điểm tuyến Đà Nẵng |
| Hết ngày 4 | AI | Kỹ sư phần mềm | Hàm cập nhật bằng chứng |
| Hết ngày 6 | Dữ liệu, AI | Kỹ sư phần mềm | Lớp nguy cơ thật, cập nhật mỗi giờ |

### 9.3 Rủi ro của cách chia này

- **Người dữ liệu là điểm nghẽn ở ngày 2–4** và chưa quen dữ liệu không gian. Nếu mốc ngày 3 trễ, người AI sang hỗ trợ việc gán ghi nhận vào tuyến.
- **Nếu đặc điểm tuyến Đà Nẵng trễ quá ngày 5**, bỏ kiểm chéo thành phố, trình diễn TP.HCM và nói rõ trong bài thuyết trình.
- **Kỹ sư phần mềm không bị chặn bởi ai** nhờ lớp nguy cơ mẫu, nên mọi trễ ở hai nhánh kia chỉ ảnh hưởng tới ngày nối dữ liệu thật.

Những việc AI agent không rút ngắn được: chờ khóa và thư trả lời, tải file lớn, dữ liệu chỉ tích lũy theo thời gian, soát tay kết quả định vị, tập thuyết trình.

## 10. Việc nhóm cần chuẩn bị

**Ngay hôm nay:**

- Người dữ liệu: bật ghi dữ liệu trực tiếp (mục 5.4).
- Người dữ liệu: tải FABDEM, DeltaDTM, bộ IRD, dữ liệu OpenStreetMap của Việt Nam; cần khoảng 30 GB ổ đĩa.
- Người dữ liệu: đăng ký tài khoản JAXA GSMaP.
- Người dữ liệu: khi xin khóa VRain, hỏi thêm dữ liệu lịch sử, tọa độ trạm, giới hạn số lần gọi.

**Trong ba ngày đầu:**

- Kỹ sư phần mềm: hỏi mentor có bộ dữ liệu đường tải về không, có dữ liệu giao thông hay thời tiết không, hạn mức API Goong.
- Người AI: kiểm tra credit ChatGPT có gọi được qua API không.
- Người dữ liệu: gửi thư xin phép và ghi nguồn tới cổng mưa ngập Đà Nẵng, Công ty Thoát nước Hà Nội, và nhóm tác giả IRD.
- Người dữ liệu: định vị 34 tuyến ngập chính thức của TP.HCM và soát bằng mắt.

## 11. Giấy phép và quyền sử dụng

- **IRD:** trang dữ liệu ghi CC BY-NC 4.0, file ReadMe ghi CC BY 4.0. Hackathon dùng được cả hai; thương mại hóa phải hỏi tác giả.
- **Cổng Đà Nẵng và Hà Nội:** không ghi giấy phép. Ghi nguồn, lấy dữ liệu với tần suất thấp, và xin phép.
- **HCMGIS:** không ghi giấy phép; chỉ dùng cổng WFS công khai.
- **DeltaDTM:** CC BY 4.0.
- **RainViewer:** chỉ cho cá nhân và giáo dục.
- **Bài báo:** chỉ lưu dữ kiện và đường dẫn.
- **Chủ quyền dữ liệu:** bộ đọc dùng API nước ngoài trong bản hackathon; thiết kế cho phép thay bằng mô hình chạy trong nước.

## 12. Trả lời các câu hỏi đánh giá ban đầu

- **Có tìm được mạng cống và địa hình đủ chi tiết không?** Không, với dữ liệu mở. Vì vậy bản này dự báo nguy cơ theo tuyến chứ không dự báo độ sâu.
- **Thiết kế mô phỏng và nhãn ra sao?** Không mô phỏng. Nhãn là các lần ngập đã ghi nhận, bổ sung dần bằng báo chí và báo cáo cộng đồng.
- **Dự báo có/không, mức nguy cơ, hay độ sâu?** Xác suất ngập và ba mức nguy cơ. Mức độ ngập lấy từ lịch sử và báo cáo.
- **Kiểm chứng thế nào để tránh học thuộc?** Loại mọi thông tin vị trí khỏi đầu vào, và kiểm tra ở thành phố khác với thành phố đã học.
- **Mở rộng thì dùng chung gì, thu thập lại gì?** Xem mục 8.

## 13. Việc làm sau hackathon

- Gợi ý giờ khởi hành. Với triều thì đáng tin vì tính trước được giờ triều rút; với mưa cần dữ liệu radar.
- Đọc ảnh người dùng gửi và camera thành phố.
- Tự động đưa báo cáo đã xác nhận vào dữ liệu học.
- Thay nguồn mưa bằng trạm đo; thêm mực nước nội thành khi xin được.
- Mô phỏng thủy lực cho một lưu vực nhỏ khi có mạng cống và địa hình chi tiết, để tiến tới dự báo độ sâu.
