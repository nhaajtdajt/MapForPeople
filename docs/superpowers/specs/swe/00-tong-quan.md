# Phần kỹ sư phần mềm: tổng quan và bảng theo dõi

Tài liệu này dành cho kỹ sư phần mềm của nhóm và các agent viết mã cùng người đó. Nó trả lời bốn câu hỏi: phải dựng những tính năng nào, dựng theo thứ tự nào, làm sao chạy được khi phần của người dữ liệu và người AI chưa xong, và mỗi tính năng đang ở trạng thái nào.

- **Ngày viết:** 04/10/2026. **Bản 2**, cùng ngày: thêm bản đồ cơ bản (spec 08), giao thông (spec 09), và viết lại tìm đường (spec 05) theo yêu cầu của chủ dự án.
- **Tài liệu ràng buộc:** `docs/superpowers/plans/2026-10-04-00-quyet-dinh-ky-thuat.md`, gọi tắt là QĐKT. Hợp đồng dữ liệu (QĐKT mục 5), chữ ký hàm (mục 6) và quy tắc mô hình (mục 4) trong đó được ưu tiên hơn mọi thứ viết ở đây.
- **Mã tham khảo:** `docs/superpowers/plans/2026-10-04-04-web.md`, gọi tắt là KH04. Mã trong đó viết cho bản 1 của thiết kế và kiểm thử Python của nó đã chạy đạt. Mục "Bản 3" ở đầu file ghi những chỗ phải sửa. Spec 05, 08 và 09 có nhiều phần mới mà KH04 chưa có mã.
- **Chín spec tính năng** nằm cùng thư mục này, đánh số 01 tới 09.

## 1. Phần này dựng cái gì

Sản phẩm trước hết là một bản đồ dùng được như bản đồ thông thường: tìm địa điểm, xem vị trí của mình, tìm đường với vài lộ trình và thời gian dự kiến. Trên nền đó là hai lớp riêng của nhóm: nguy cơ ngập từng đoạn đường, và đường tránh ngập. Người dùng báo ngập được bằng một chạm và xem được cảnh báo cho 1–2 giờ tới. Phạm vi là TP.HCM và Đà Nẵng, cho xe máy và ô tô.

Kỹ sư phần mềm giữ máy chủ, mọi endpoint, thuật toán tìm đường, số liệu giao thông, giao diện, bàn thử và việc triển khai. Người dữ liệu giao các file đường, mạng đường và ghi nhận ngập. Người AI giao điểm của từng đoạn, bảng nguy cơ theo giờ, các kịch bản phát lại và hàm cập nhật theo báo cáo.

## 2. Bốn điều đổi so với QĐKT

1. **Kỹ sư phần mềm dựng phần nền** (kế hoạch 01, Task 1–3) thay cho người AI, vì là người bắt đầu trước.
2. **Phần của hai người kia được thay tạm bằng bản giả** (spec 01), nên không việc nào ở đây phải chờ ai.
3. **Thuật toán tìm đường riêng là bộ máy chính cho mọi lộ trình,** kể cả lúc trời khô. Goong làm mốc đối chiếu và phương án lùi (spec 05). Trước đây đường nhanh nhất lấy của Goong.
4. **Số liệu giao thông được đưa trở lại** (spec 09). Trước đây nó bị bỏ.

Cả bốn đã được ghi vào QĐKT mục 18.3, điểm 13 tới 19.

## 3. Năm nguyên tắc

1. **Đường nối là hợp đồng dữ liệu và chữ ký hàm.** Bản giả phải đúng hợp đồng. Khi bản thật đến thì chép file vào đúng chỗ hoặc gộp nhánh, không sửa mã của phần web.
2. **Mọi lời gọi sang mã của hai người kia đi qua một file,** `src/floodrisk/api/ports.py`.
3. **Thứ gì giả hoặc ước lượng thì luôn lộ ra.** `GET /api/health` ghi phần nào đang giả; giao diện ghi nhãn cho dữ liệu mẫu, cho giao thông điển hình, và cho thời gian ước lượng.
4. **Kiểm thử máy chủ chỉ khẳng định điều hợp đồng hứa,** nên cùng một bộ kiểm thử đạt với cả bản giả lẫn bản thật.
5. **Chỉ sửa trong phần của mình:** `src/floodrisk/api/`, `tests/api/`, `web/`, `Dockerfile`, `docker-compose.yml`, `deploy/`. Ngoại lệ là phần nền ở ngày 1 và việc thêm một thư viện vào `requirements.txt`.

## 4. Bảng theo dõi

Mỗi tính năng có hai cột trạng thái, vì "xong" có hai bậc: chạy được trên dữ liệu mẫu, rồi chạy được trên dữ liệu thật. Ghi `—` (chưa làm), `đang`, hoặc `xong` kèm ngày.

**Ưu tiên:** *Lõi* là phải có trong buổi trình diễn. *Nên* là có thì ăn điểm rõ, bị cắt đầu tiên khi trễ. *Thêm* là chỉ làm khi mọi thứ lõi đã chạy trên dữ liệu thật.

| Mã | Tính năng | Ưu tiên | Ngày | Spec | Trên dữ liệu mẫu | Trên dữ liệu thật |
|---|---|---|---|---|---|---|
| S1.1 | Khung repo, cấu hình, hợp đồng, dữ liệu mẫu | Lõi | 1 | 01 | — | không áp dụng |
| S1.2 | Lớp giả: `devdata`, `ports`, `fakes` | Lõi | 1 | 01 | — | không áp dụng |
| S1.3 | Lệnh kiểm tra nối ghép `doctor`, trạng thái trong `/api/health` | Lõi | 1–3 | 01 | — | — |
| S8.1 | Khung bản đồ và điều khiển | Lõi | 1 | 08 | — | không áp dụng |
| S8.2 | Ô tìm kiếm và thẻ địa điểm | Lõi | 1 | 08 | — | không áp dụng |
| S8.3 | Chạm để ghim và xem địa chỉ | Lõi | 1 | 08 | — | không áp dụng |
| S8.4 | Vị trí của tôi | Lõi | 1 | 08 | — | — |
| S5.1 | Tìm đường lúc bình thường: nhanh nhất, lộ trình thay thế, chỉ dẫn | Lõi | 2 | 05 | — | — |
| S5.2 | Giao diện lộ trình: nhiều lộ trình, thời gian, giờ tới nơi | Lõi | 2 | 05 | — | — |
| S9.1 | Giao thông điển hình theo giờ | Lõi | 2 | 09 | — | không áp dụng |
| S5.3 | Đối chiếu thuật toán riêng với Goong | Lõi | 2, 8 | 05 | — | — |
| S2.1 | Máy chủ phục vụ lớp nguy cơ | Lõi | 3 | 02 | — | — |
| S2.2 | Lớp nguy cơ trên bản đồ, chú thích, chọn giờ | Lõi | 3 | 02 | — | — |
| S4.1 | Chọn kịch bản và phát lại | Lõi | 3 | 04 | — | — |
| S7.1 | Docker, máy EC2, chạy bằng HTTP | Lõi | 3 | 07 | — | — |
| S7.2 | Tác vụ nền mỗi giờ | Lõi | 3 | 07 | — | — |
| S3 | Báo ngập một chạm, đếm số người đã báo | Lõi | 4 | 03 | — | — |
| S7.3 | Tên miền và HTTPS | Lõi | 4 | 07 | không áp dụng | — |
| S9.2 | Giao thông thật từ TomTom | Nên | 4 | 09 | — | — |
| S5.4 | Tránh ngập: chi phí có phạt, đường tránh, bảng so sánh | Lõi | 4–5 | 05 | — | — |
| S9.4 | Ngập làm chậm giao thông | Lõi | 5 | 09 | — | — |
| S9.3 | Lớp giao thông trên bản đồ | Nên | 5 | 09 | — | — |
| S6.1 | Cảnh báo sớm quanh một vị trí | Lõi | 6 | 06 | — | — |
| S4.2 | Bàn thử trên giao diện, có điều khiển giao thông | Nên | 6 | 04, 09 | — | — |
| S2.3 | Thẻ giải thích vì sao đoạn này có nguy cơ | Nên | 7 | 02 | — | — |
| S5.5 | Hệ số xe, `POST /api/score-route` | Nên | 7 | 05 | — | — |
| S8.5 | Bật tắt lớp, đổi kiểu nền | Nên | 7 | 08 | — | — |
| S6.2 | Lời khuyên giờ đi | Thêm | 7 | 06 | — | — |
| S7.4 | Bản dự phòng cho buổi trình diễn | Lõi | 9 | 07 | không áp dụng | — |
| S4.3 | Liên kết mở đúng trạng thái | Thêm | 9 | 04 | — | — |
| S8.6 | Nơi đã lưu và tìm kiếm gần đây | Thêm | 9 | 08 | — | — |
| S9.5 | Ghi giao thông để học bảng điển hình | Thêm | — | 09 | — | — |

Điều kiện nghiệm thu chi tiết của từng tính năng nằm trong spec của nó, dạng ô đánh dấu.

## 5. Thứ tự làm

Bảng này thay cho cột "Kỹ sư phần mềm" ở QĐKT mục 11.2. Bản đồ cơ bản và tìm đường lúc bình thường đi trước, lớp ngập đi sau.

| Ngày | Làm | Kết quả phải thấy |
|---|---|---|
| 1 | S1.1, S1.2; S8.1 tới S8.4; tạo máy EC2 | Trang chạy trên máy mình như một bản đồ: tìm "Chợ Bến Thành", chạm để xem địa chỉ, thấy vị trí của mình |
| 2 | S5.1, S5.2, S9.1; lượt đầu của S5.3 | Chọn hai điểm, thấy mọi lộ trình hợp lý kèm thời gian và giờ tới nơi. Sáng làm trên lưới mẫu; chiều chuyển sang mạng đường thật của TP.HCM khi file đến |
| **3** | S2.1, S2.2, S4.1, S7.1, S7.2; S1.3 | **Mốc ngày 3:** TP.HCM chạy trên máy EC2 với lớp nguy cơ thật và chọn được kịch bản |
| 4 | S3; S7.3; S9.2; phần máy chủ của S5.4 | Báo ngập được; trang chạy bằng HTTPS nên nút định vị hoạt động; thời gian lộ trình dùng số liệu TomTom |
| 5 | Xong S5.4; S9.4; S9.3 | Có đường tránh ngập cạnh đường nhanh nhất; thời gian đường qua chỗ ngập dài ra; bật được lớp giao thông |
| 6 | S6.1; S4.2 | Thẻ cảnh báo cho vị trí đã lưu; tạo được kịch bản giả lập và đổi được giao thông từ bàn thử |
| 7 | S2.3; S5.5; S8.5; S6.2 nếu kịp | Chạm vào đoạn mở thẻ giải thích; ô tô và xe máy cho kết quả khác nhau |
| 8 | Nối và sửa lỗi trên dữ liệu thật của cả hai thành phố; chạy lại S5.3 | `/api/health` không còn phần nào là bản giả; có báo cáo đối chiếu cho cả hai thành phố |
| 9 | Hoàn thiện giao diện; S7.4; các mục "Thêm" nếu kịp | Chạy trọn kịch bản trình diễn trên điện thoại và trên máy dự phòng |
| 10 | Tổng duyệt | — |

**Cái giá của việc thêm ba spec:** bản đồ cơ bản, tìm đường lúc bình thường và giao thông cộng lại khoảng hai tới ba ngày công. Để có chỗ, báo ngập lùi từ ngày 2 sang ngày 4, và các mục "Nên" dồn về ngày 6–7. Nếu trễ, những thứ có nguy cơ bị cắt là bàn thử trên giao diện, thẻ giải thích và mọi mục "Thêm".

## 6. Bảng nối ghép

Mỗi dòng là một thứ sẽ đến từ người khác. Hạn lấy theo QĐKT mục 11.3.

| Thứ đến | Từ ai | Hạn | Thay cho bản giả nào | Việc phải làm khi nhận | Cách biết đã nối xong |
|---|---|---|---|---|---|
| `model/evidence.py`, `model/combine.py` | AI | Hết ngày 1 | `fakes.apply_evidence`, `fakes.to_level` | Gộp nhánh `main` vào nhánh `web` | `/api/health` ghi `evidence` và `levels` là `real`; `pytest tests/api` đạt |
| TP.HCM: ba file mạng đường, `units` | Dữ liệu | Trưa ngày 2 | Lưới mẫu | Chép vào `data/processed/hcm/`; chạy `doctor hcm`; đo tốc độ tìm đường; chạy `routecheck` | Lộ trình chạy trên đường thật; có báo cáo đối chiếu |
| TP.HCM: `observations`, `obs_units` | Dữ liệu | Trưa ngày 2 | Bảng mẫu | Chép file | Thẻ giải thích có lịch sử thật |
| TP.HCM: `scores`, `risk`; `jobs/hourly.py` | AI | Hết ngày 2 | Điểm và nguy cơ mẫu; `fakes.run_hourly` | Đặt `FLOODRISK_DATA=data`, `REFRESH_MINUTES=60` | `/api/health` ghi `data` và `hourly` là `real`; chú thích không còn dòng "chưa được cập nhật" |
| Các kịch bản đầu tiên trong `replay/` | AI | Trưa ngày 3 | Kịch bản mẫu | Tạo ngay trên máy EC2 bằng lệnh của người AI (spec 07) | Ô chọn chế độ có ngày thật |
| `model/scenarios.py` | AI | Ngày 3 | `fakes.make_synthetic`, `fakes.make_past_moment` | Gộp nhánh | `/api/health` ghi `scenarios` là `real`; sáu kịch bản thử chuẩn cho đúng kết quả trên giao diện |
| Đà Nẵng: trọn bộ file | Dữ liệu, AI | Hết ngày 3 | Dữ liệu mẫu của Đà Nẵng | Chép file; chạy `doctor danang` và `routecheck danang` | Đổi thành phố trên giao diện thấy dữ liệu thật |
| `model_choice.json` có danh sách `validated` | AI | Ngày 6 | — | Không phải làm gì | Dòng "chưa được kiểm chứng" biến mất ở thành phố có trong danh sách |
| Khóa TomTom | Chủ dự án | **Đã có ngày 04/10** | Giao thông điển hình | Khóa đã nằm trong `.env`; phép thử độ dày dữ liệu đã chạy (spec 09, mục 1.1) | `/api/health` ghi nguồn giao thông là `tomtom` |

Khi một thứ đến trễ, tính năng liên quan vẫn chạy bằng bản giả và cột "Trên dữ liệu thật" để trống. Không dừng việc để chờ.

## 7. Khi trễ thì cắt theo thứ tự này

1. Mọi mục "Thêm": S4.3, S6.2, S8.6, S9.5.
2. S2.3 thẻ giải thích, S5.5 hệ số xe và `POST /api/score-route`, S8.5.
3. S4.2 bàn thử trên giao diện. Kịch bản vẫn tạo được bằng dòng lệnh của người AI.
4. S9.2 và S9.3: giao thông thật và lớp giao thông. Thời gian tới nơi khi đó dùng giao thông điển hình, có ghi nhãn.
5. Đà Nẵng.

Không được cắt: bản đồ cơ bản, tìm đường có nhiều lộ trình và thời gian, lớp nguy cơ, chọn kịch bản, báo ngập, tránh ngập, cảnh báo sớm, triển khai.

## 8. Thế nào là xong

Một tính năng được ghi `xong` ở cột "Trên dữ liệu mẫu" khi:

- Mọi ô nghiệm thu trong spec của nó đã được đánh dấu.
- `pytest tests/api` đạt, không kiểm thử nào gọi mạng.
- `npm run build` trong `web/` đạt, kể cả bước kiểm kiểu.
- Đã tự tay dùng thử trên trình duyệt ở chiều rộng 360 px.

Nó được ghi `xong` ở cột "Trên dữ liệu thật" khi dòng tương ứng ở bảng nối ghép đã đạt và tính năng đã được dùng thử lại trên máy EC2.

## 9. Mỗi tính năng ăn điểm ở tiêu chí nào

| Tiêu chí của đề bài | Điểm | Tính năng đóng góp |
|---|---|---|
| Giải quyết vấn đề và tác động | 20 | Tìm đường tránh ngập, cảnh báo sớm |
| Phù hợp với Việt Nam | 15 | Xe máy và ô tô được tính khác nhau, kể cả khi đường đông; ngập do mưa và do triều; báo ngập không cần đăng nhập |
| Sáng tạo và khác biệt | 20 | Lộ trình được chấm theo nguy cơ ngập; thời gian tới nơi tính cả việc ngập làm chậm; thẻ giải thích |
| Dữ liệu và AI | 20 | Báo cáo cộng đồng sửa dự báo ngay; phát lại ngày ngập thật; ghép số liệu giao thông vào mạng đường mở |
| Khả thi và sản phẩm thử nghiệm | 15 | Chạy thật trên EC2; thuật toán tìm đường được đối chiếu với Goong; `POST /api/score-route` là điểm tích hợp cho ứng dụng dẫn đường khác |
| Trình bày và trải nghiệm | 10 | Dùng được như một bản đồ quen thuộc trên điện thoại |

## 10. Việc cần người khác làm hoặc xác nhận

1. **Khóa TomTom đã có** và đã gọi thử được ở TP.HCM (spec 09, mục 1.1). Việc còn lại của chủ dự án: đọc mục lưu trữ dữ liệu trong điều khoản của TomTom trước khi bật việc ghi số liệu nhiều ngày, và đổi khóa sau cuộc thi vì khóa đã được gửi qua khung trò chuyện.
2. **Bốn hàm tạo kịch bản trả về mã kịch bản** dạng chuỗi (QĐKT mục 18.3, điểm 14).
3. **Tác vụ mỗi giờ có đúng một cửa vào:** `floodrisk.jobs.hourly.run_all() -> list[str]`.
4. **`observations.parquet` và `obs_units.parquet` cũng được giao cho phần web,** vì thẻ giải thích đọc chúng.
5. **Ba file mạng đường của TP.HCM đúng hạn trưa ngày 2.** Tìm đường là việc của ngày 2, nên đây là file được cần sớm nhất.
6. **Nơi để file dùng chung:** một thư mục Google Drive của nhóm, bố cục giống hệt `data/processed/` (spec 07).
