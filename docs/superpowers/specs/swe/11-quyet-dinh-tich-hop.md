# Ghi chú 11: Quyết định tích hợp ba repo (bản 2)

Viết đêm 07/10/2026. **Bản này thay hoàn toàn bản viết tối cùng ngày.** Bản trước sai vì tôi quyết định khi mới đọc README và hai file của repo mô hình. Lần này mọi quyết định bên dưới đều dựa trên mã đã đọc hết và đã chạy thử trên máy này.

Ba repo, đều nằm trong `D:\HK1 4 year\Hackathon\`:

| Repo | Là gì |
|---|---|
| `MapForPeople` (repo này) | Bản đồ, tìm kiếm, tìm đường riêng. Đây là sản phẩm cuối |
| `flood_prediction_models` | Hai mô hình đã train và đã chấm, tác vụ mỗi giờ, hàm cập nhật theo báo cáo |
| `mlai-car-access` | Triều và mưa đo trực tiếp, camera giao thông, Gemini đọc ảnh |

## 1. Bản trước sai ở đâu

| Bản trước nói | Sự thật sau khi đọc và chạy |
|---|---|
| Đổi "tuyến" của mô hình sang đoạn 200 m của repo này | Sai. Đoạn 200 m chỉ có đường có tên, sẽ làm mất 84.865 tuyến không tên của TP.HCM (60% số tuyến). Mô hình được chấm theo tuyến, nên phải giữ tuyến |
| Chờ bạn làm mô hình gửi file và chạy thử trước | Không cần. Tác vụ mỗi giờ của bạn ấy chạy được trên máy này ngay tối nay, và tôi dựng lại được hình học các tuyến |
| Dùng số cộng dồn của VRain | Kém hơn thứ nhóm đã có. Mã `hydro.py` lấy được mưa từng giờ của 44 trạm và mực nước Phú An |
| Giữ hàm cập nhật theo báo cáo của repo này | Sai. Repo mô hình đã có `evidence.py`, kèm kiểm thử |
| Chia mức theo ngưỡng 0,35 và 0,60 của chỉ số nguy cơ | Sai. Mô hình ra mức bằng quy tắc hai yếu tố (hạng của tuyến và trạng thái của ngày), không bằng ngưỡng trên `P` |

## 2. Đã đọc gì, đã chạy gì

**Repo mô hình.** Có hai nhánh. `main` (commit `842da0a`) chứa mọi thứ của `codex/flood-risk-models` và thêm hai commit sửa lỗi chạy trực tiếp. Tôi đã đọc toàn bộ `src/`, các script xuất và chạy mỗi giờ, hợp đồng dữ liệu, thẻ mô hình, báo cáo khóa 2025–2026 và nhật ký làm việc.

| Việc đã chạy trên máy này | Kết quả |
|---|---|
| `run_hourly.py` của repo mô hình, chế độ trực tiếp | Chạy được. TP.HCM 56 giây, Đà Nẵng 13 giây |
| Kết quả lúc 22:00 ngày 07/10 | TP.HCM: mưa ở trạng thái báo động; 7.012 tuyến mức cao, 21.036 mức vừa. Đà Nẵng: cảnh giác; 1.072 tuyến mức vừa |
| Tự tính lại mức mưa chỉ từ các file mô hình đã commit | Ra đúng cùng con số với mã của bạn ấy (T = 0,5447). Vậy phần suy luận chép sang được mà không lệch |
| Dựng lại các tuyến từ đúng bản OpenStreetMap ngày 04/10 | Số lượng khớp tuyệt đối: 140.236 và 21.429 tuyến; 893 ghi nhận ngập cho ra kết quả gắn trùng với báo cáo của repo đó |
| So mã tuyến dựng lại với bảng điểm đã commit | Tuyến có tên: trùng 100%. Tuyến không tên: chỉ trùng một phần (dựng trên Linux thì cả TP.HCM trùng 82,5%), nhiều khả năng vì mã của chúng được băm từ tọa độ và tọa độ lệch ở chữ số cuối giữa các máy. Thứ tự dòng thì trùng 100%, nên ghép được theo dòng |
| Gắn mạng đường của repo này vào tuyến của mô hình | 99,6% số cạnh gắn được; điểm mẫu nằm cách tuyến 0 m vì cùng gốc OpenStreetMap |
| `hydro.py` và `cameras.py` của `mlai-car-access`, chạy nguyên xi | Triều Phú An: 45 số đo trong 7 ngày. Mưa: 44 trạm, có số từng giờ của 7 ngày. Camera: 796 cái, 671 đang có hình, tải được ảnh |
| Gemini đọc ảnh camera | Đã thử ngày 08/10 với ba khóa của nhóm: 3.5 Flash và 3.1 Flash-Lite đọc đúng 6 camera lúc đường khô; chưa có cảnh ngập để thử (ghi chú 12, mục 4) |

## 3. Ba điều số liệu cho thấy

**3.1 Mô hình chạy trực tiếp được ngay, không cần ai làm thêm gì.**

**3.2 Mức của mô hình rất rộng trong vùng nội thành.** Mức mưa là một con số chung cho cả thành phố. Hạng của tuyến tính trên cả 140.236 tuyến, kể cả đường nội bộ và vùng ven. Hệ quả trên mạng đường xe chạy được của vùng lõi:

| | Tỉ lệ chiều dài đường |
|---|---|
| Thuộc nhóm A (5% tuyến điểm cao nhất) | 17,5% |
| Thuộc nhóm B (15% kế tiếp) | 43,8% |
| Riêng đường `primary`: nhóm A hoặc B | 84% |

Ngày mô hình báo động, khoảng 17% chiều dài đường nội thành là mức cao và 44% là mức vừa. Bản đồ sẽ gần như kín màu, và tìm đường không thể "tránh mọi tuyến mức cao". Trong khi đó mưa thật thì cục bộ: hôm nay chỉ 5 trong 44 trạm có giờ mưa từ 30 mm trở lên.

Vì vậy sản phẩm cần thêm thứ phân biệt được chỗ này với chỗ kia: lịch sử ngập (310 tuyến, 143 km), trạm mưa, triều, camera, người báo. README của repo mô hình cũng viết đúng ý này: ở TP.HCM hãy dựa vào xếp hạng tuyến, báo cáo của người dùng và triều.

**3.3 Tuần này có dữ liệu thật để kiểm và để trình diễn.**

- Hôm nay 07/10, trạm Nguyễn Thiện Thuật đo 63,3 mm trong giờ kết thúc lúc 18:00 và 102 mm cả ngày. Lúc 22:00 mô hình ở trạng thái báo động.
- Theo mô hình triều của `hydro.py`, từ 10/10 tới 13/10 mực nước Phú An vượt báo động 3 (1,60 m) hai lần mỗi ngày, trong đó có các đỉnh buổi chiều lúc 15:45 tới 17:45. Con số có sai số ±0,15 m. Đã đối chiếu ngày 08/10: bản tin chỉ nói "trên báo động 2, xấp xỉ báo động 3" cho đợt này, thấp hơn con số của mô hình triều ít nhất 0,1 m (ghi chú 12, mục 5).
- Ngày trình diễn 17/10 nhiều khả năng triều đã rút. Muốn có cảnh ngập thật để chiếu thì phải ghi lại trong các ngày 10–13/10.

## 4. Quyết định

### QĐ1. Repo này là sản phẩm. Chép phần chạy lúc vận hành của hai repo kia vào đây

- Từ repo mô hình chép vào `src/floodrisk/model/`: `evidence.py` nguyên văn; các hàm xếp nhóm tuyến và ra mức; hàm tính mức mưa và triều. Chép thư mục `models/final_2025-01-01/` và ba file ngưỡng vào `data/model/`.
- Từ `mlai-car-access` chép vào `src/floodrisk/live/`: `hydro.py`, `cameras.py`, phần gọi Gemini của `ai.py`.
- Mỗi file chép ghi rõ repo và commit gốc ở đầu file. Có một phép thử so kết quả với `run_hourly.py` gốc.
- Lý do: hai gói Python trùng tên `floodrisk` nên không nhập chung được; một dịch vụ thì dễ đưa lên máy chủ; tác vụ gốc tốn 56 giây cho TP.HCM (và hơn 1 GB bộ nhớ theo nhật ký của repo đó) vì dựng 420.000 dòng, trong khi cùng phép tính viết gọn chỉ là vài phép nhân trên mảng.
- Mô hình không bị sửa. Khi bạn làm mô hình train lại, chỉ cần thay thư mục `data/model/`.

### QĐ2. Đơn vị là tuyến của mô hình, giữ nguyên mã tuyến

Bản đồ tô theo tuyến, báo ngập gắn vào tuyến, tìm đường tra mức theo tuyến. Bỏ đoạn 200 m và các bảng `units`, `scores`, `risk` của kế hoạch 04/10.

### QĐ3. Hình học các tuyến tự dựng trên máy này

Chạy script dựng tuyến của repo mô hình trong Ubuntu (WSL) có sẵn trên máy, trên bản OpenStreetMap ngày 04/10, rồi lấy mã tuyến của bảng điểm theo thứ tự dòng. Tôi đã kiểm cách ghép này: mọi tuyến có tên trùng mã tại đúng dòng, và cờ "trong phạm vi mô hình" trùng ở cả 140.236 dòng.

Cách gọn hơn về lâu dài là bạn làm mô hình commit hai file `data/export/<thành phố>/routes.parquet` (27 MB). Việc đó nên làm nhưng không ai phải chờ.

### QĐ4. Mức trên bản đồ = mức của mô hình, cộng ba nguồn tại chỗ chỉ được nâng mức

Mức của mô hình được giữ nguyên. Ba nguồn dưới đây chỉ làm mức cao lên, và bản đồ ghi rõ mức đó đến từ nguồn nào.

| Nguồn | Quy tắc | Phạm vi |
|---|---|---|
| Trạm đo mưa (44 trạm, số từng giờ) | Đưa mưa 3 giờ và 24 giờ của trạm qua đúng hàm mức mưa của mô hình; lấy giá trị lớn hơn giữa trạm và cả thành phố | Các tuyến trong 5 km quanh trạm |
| Mực nước Phú An | Từ 1,40 m (báo động 1): cảnh giác. Từ 1,50 m (báo động 2): báo động | Cả TP.HCM, cho phần ngập do triều |
| Camera có Gemini đọc, và người dùng báo | Dùng `evidence.py`. Báo "ngập vừa" trở lên thì tuyến đó lên ít nhất mức vừa, "ngập cao" thì lên mức cao. Đa số báo "không ngập" thì hạ một bậc | Đúng tuyến có camera hoặc có người báo |

Ba con số 5 km, 1,40 m và 1,50 m là tôi đặt. Bạn làm mô hình có quyền đổi.

Không hiện chỉ số `P` cho người dùng. Mức mưa `T` của mô hình luôn nằm trong khoảng 0,41 tới 0,59, kể cả ngày khô, nên `P` không đọc như xác suất được.

### QĐ5. Tìm đường tránh ngập theo bậc bằng chứng

| Bậc | Tuyến | Cách xử lý |
|---|---|---|
| 1 | Đang có camera hoặc người báo ngập vừa trở lên | Tránh hẳn nếu còn đường khác |
| 2 | Từng ngập (310 tuyến) và hôm nay mưa hoặc triều tới ngưỡng | Cộng thời gian nặng |
| 3 | Chỉ do mô hình xếp hạng cao | Cộng thời gian nhẹ |

Mỗi lộ trình hiện kèm lý do: tránh đoạn nào, vì nguồn nào, lúc mấy giờ.

### QĐ6. Giao thông lấy từ camera và bảng theo giờ

Một lần Gemini đọc camera cho cả hai thứ: có ngập không, và đường thông thoáng, đông, ùn ứ hay kẹt cứng. Mức kẹt làm chậm các cạnh quanh camera. Nơi không có camera dùng bảng theo giờ. TomTom chỉ làm nếu dư thời gian.

### QĐ7. Những thứ bỏ

Bộ đọc báo. Lớp giả cho phần mô hình (`fakes`, `devdata`, các bảng mẫu). Bộ chuyển tuyến sang đoạn của bản trước.

## 5. Thứ tự làm, 08/10 tới 16/10

| Ngày | Việc | Kết quả nhìn thấy |
|---|---|---|
| 08/10 | Tuyến và mức của mô hình vào repo này cho TP.HCM; `GET /api/risk`; lớp nguy cơ; thẻ của một tuyến | Mở bản đồ thấy đúng các tuyến và mức mà `run_hourly.py` gốc cho ra |
| 09/10 | Trạm mưa và triều Phú An vào mức; thẻ "mưa và triều lúc này"; lớp camera xem ảnh trực tiếp; **bật bộ ghi** | Chạm vào camera thấy ảnh đường lúc này. Bộ ghi lưu mỗi 10 phút: mức, số đo, ảnh của 113 camera nằm sát tuyến từng ngập |
| 10/10 | Giao diện lộ trình; tìm đường tránh ngập theo QĐ5 | Chọn hai điểm, thấy lộ trình né tuyến ngập kèm lý do |
| 11/10 | Báo ngập một chạm; Gemini đọc camera thành bằng chứng | Báo ngập làm tuyến đổi mức; camera thấy nước làm tuyến đổi mức |
| 12/10 | Đưa lên máy chủ có HTTPS; tác vụ mỗi giờ chạy thật; chuyển bộ ghi lên máy chủ | Mở được trên điện thoại, có vị trí của tôi |
| 13/10 | Đà Nẵng; chế độ phát lại ngày 07/10 và một ngày triều cường | Đổi thành phố được; phát lại một ngày ngập thật |
| 14/10 | Giao thông theo QĐ6; cảnh báo sớm 1–2 giờ | Thời gian tới nơi đổi theo giờ và theo camera |
| 15–16/10 | Thử trên điện thoại thật, sửa lỗi, tập trình diễn | — |

Từ tối 09/10 tới 13/10, máy chạy bộ ghi phải bật liên tục.

Cắt trước nếu trễ: TomTom, cảnh báo sớm, giao thông từ camera. Không cắt: lớp nguy cơ, tìm đường tránh ngập, báo ngập, bộ ghi, triển khai.

## 6. Cần từ người khác

Không việc nào ở mục 5 phải chờ ai, trừ một thứ:

| Ai | Cần gì | Dùng cho |
|---|---|---|
| Bạn làm `mlai-car-access`, hoặc chủ dự án tự tạo | Một khóa Gemini | Việc ngày 11/10. Theo ghi chép của bạn ấy, khóa miễn phí chỉ được 20 lần gọi mỗi ngày cho mô hình chính; ngày trình diễn nên có khóa trả phí |
| Bạn làm mô hình | Xem ba con số ở QĐ4 và phát hiện ở mục 3.2; nếu tiện thì commit hai file `routes.parquet` | Không chặn việc nào |

## 7. Tài liệu cũ

Các phần sau của kế hoạch 04/10 hết hiệu lực: mục 4 (mô hình), mục 6 (hợp đồng dữ liệu) và mục 11 (lịch) của tài liệu quyết định kỹ thuật; phần lớp giả của spec 01; phần kịch bản giả lập của spec 04. Chuẩn cho phần mô hình bây giờ là `README.md` và `reports/data_contract.md` của repo mô hình. Tôi sẽ sửa các tài liệu đó và bảng theo dõi sau khi chủ dự án duyệt ghi chú này.

## 8. Những thứ đã tạo trên máy trong lúc kiểm

| Ở đâu | Gì | Có vào git không |
|---|---|---|
| `flood_prediction_models/data/` | Bản OpenStreetMap ngày 04/10, tuyến, ghi nhận ngập, bảng triều, kết quả tác vụ mỗi giờ (khoảng 450 MB) | Không; thư mục `data/` của repo đó đã nằm trong `.gitignore` |
| Ubuntu (WSL), thư mục `~/fpm` | Môi trường Python 3.14 và bản dựng tuyến trên Linux | Không |
| `MapForPeople/data/raw/live/2026-10-07/` | Số mưa từng giờ 7 ngày của 44 trạm, số đo triều, kết quả mô hình lúc 22:00 | Không |

Hai điều cần biết khi chạy script của repo mô hình trên Windows: phải đặt `PYTHONUTF8=1` (script đọc file JSON tiếng Việt không khai báo bảng mã), và `fetch_city_bboxes.py` không kết nối được Nominatim từ máy này nên tôi ghi file `city_bboxes.json` bằng tay từ `cities.py`.
