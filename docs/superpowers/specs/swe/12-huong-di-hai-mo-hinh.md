# Ghi chú 12: Có nên train thêm hai mô hình không

Viết trưa 08/10/2026, còn 9 ngày tới buổi trình diễn. Ghi chú này trả lời một câu hỏi của nhóm: nên lấy thêm dữ liệu để train tiếp hai mô hình, hay giữ như đang có và dồn sức vào việc khác. Mọi con số bên dưới đều đo trên máy này trong hai ngày 07–08/10.

## 1. Kết luận

1. **Giữ hai mô hình như đang có để trình diễn.** Không train lại bằng máy mạnh. Không cần Kaggle hay EC2 cho việc train: hai mô hình đều nhỏ, thứ đang thiếu là nhãn chứ không phải máy.
2. **Mô hình 2 (hôm nay có ngập không): không train lại phần mưa.** Đổi nguồn mưa hay thêm ngày học đều không kéo nó lên được bao nhiêu (mục 2). Dùng nó làm cảnh báo chung cho cả thành phố. Chỗ nào đang mưa to thì lấy từ 44 trạm đo mưa theo giờ.
3. **Mô hình 1 (ngập ở đâu): có một bộ dữ liệu đáng thêm ngay**, là danh sách 122 điểm ngập Phòng CSGT công bố ngày 06/10. Phần triều của mô hình khớp danh sách này rất tốt. Phần mưa khớp ở nội thành; ở ngoại thành nó không hơn chọn bừa (mục 3).
4. **Dữ liệu quý nhất lúc này là thứ đang diễn ra ngoài đường.** Bộ ghi đã chạy từ 12:02 hôm nay. Đợt triều cường 10–13/10 là đợt duy nhất trước buổi trình diễn (mục 5).
5. **Gemini đọc camera chạy được với ba khóa của nhóm**, nhưng hạn mức miễn phí nhỏ và camera không phủ ngoại thành (mục 4).

Việc chính của 9 ngày còn lại vẫn là xây sản phẩm theo lịch ở ghi chú 11.

## 2. Vì sao không train lại phần mưa của Mô hình 2

Thước đo dùng ở đây là điểm phân biệt ngày ngập với ngày thường: 0,5 là đoán bừa, 1,0 là hoàn hảo. Báo cáo của repo mô hình chấm phần mưa ở TP.HCM được 0,635; trong 6 ngày ngập do mưa của giai đoạn 2025–2026, mô hình xếp 5 ngày vào "yên" và không ngày nào vào "báo động". Phần triều được 0,876.

Tôi đã thử hai cách nhóm nghĩ tới, chỉ dùng nhãn trước 2025 để không đụng bộ kiểm khóa:

| Thử gì | Kết quả |
|---|---|
| Đổi nguồn mưa sang ô nhỏ hơn: ERA5 28 km, IFS 9 km (đang dùng), vệ tinh PDIR-Now 4 km, trạm đo Tân Sơn Hòa | Nguồn nào cũng chỉ được 0,62–0,70. Ô nhỏ hơn không giúp |
| Thêm ngày ngập lấy từ tiêu đề báo (6.347 tiêu đề, 2016–2024) | Số ngày ngập rõ tăng từ 37 lên 56; riêng 2020–2024 từ 10 lên 48. Điểm của IFS tăng từ 0,64 lên 0,70–0,73 |

Lý do nằm ở cách đặt bài toán, không ở dữ liệu. Mô hình 2 trả một câu cho cả thành phố và cả ngày, trong khi mưa dông ở TP.HCM rơi từng vùng:

- Ngày 01/10 và 07/10, chỉ 5 trong 44 trạm có giờ mưa từ 30 mm, đúng các khu báo chí đưa tin ngập.
- Trưa nay, giờ 11–12, chỉ 1 trong 44 trạm đo được từ 1 mm, và trạm đó đo 32,4 mm (Nguyễn Thị Sẳng, phía tây bắc thành phố); các trạm còn lại từ 0 tới 0,2 mm. Mô hình 2 lúc đó ở mức "cảnh giác" cho toàn thành phố.

Số liệu mưa theo giờ của từng trạm thì cổng chỉ giữ 7 ngày, nên không có quá khứ để train một mô hình theo vùng. Muốn có thì phải tự ghi từ bây giờ (mục 5).

## 3. Mô hình 1 so với 122 điểm ngập của CSGT

Danh sách gồm 83 điểm ngập do mưa và 39 điểm do triều ([Tuổi Trẻ 06/10/2026](https://tuoitre.vn/canh-sat-giao-thong-canh-bao-122-diem-ngap-o-tphcm-co-duong-ly-te-xuyen-tran-xuan-soan-10026100617461927.htm)). Phần lớn là dữ liệu mô hình chưa từng thấy: 84 trong 102 điểm định vị được không có ghi nhận ngập nào trong dữ liệu học.

Tôi xem các điểm CSGT nêu theo hai cách:

- **(a) Bản đồ có tô màu chỗ đó vào ngày báo động không.** Bản chạy mỗi giờ (`run_hourly.py`) lấy điểm đã cộng lịch sử ngập, xếp hạng cả 140.236 tuyến: 7.012 tuyến điểm cao nhất lên mức cao, 21.036 tuyến kế tiếp lên mức vừa.
- **(b) Riêng điểm của mô hình, không cộng lịch sử, có xếp chỗ đó vào nhóm 20% điểm cao nhất của 66.017 tuyến được chấm không.** Cách này đo khả năng tự đoán của mô hình.

Mỗi con số đi kèm tỉ lệ nếu chọn bừa một tuyến có tên cùng loại đường, vì mô hình vốn chấm đường lớn cao hơn đường nhỏ.

| | Số điểm | (a) Bản đồ tô màu khi báo động | Chọn bừa | (b) Nhóm 20% theo điểm riêng của mô hình | Chọn bừa |
|---|---|---|---|---|---|
| Ngập do triều | 37 | **37 (100%)** | 53% | **35 (95%)** | 34% |
| Ngập do mưa, trong 10 km quanh chợ Bến Thành | 30 | **30 (100%)** | 70% | **23 (77%)** | 42% |
| Ngập do mưa, xa hơn 10 km | 35 | **23 (66%)** | 67% | **14 (40%)** | 40% |

Riêng mức cao của cách (a): triều 26 trong 37 (chọn bừa 23%), mưa nội thành 18 trong 30 (29%), mưa ngoại thành 13 trong 35 (27%).

Đọc bảng:

- **Triều: tốt theo cả hai cách.** Mọi điểm đều được tô màu, 26 điểm ở mức cao. Với 30 điểm mô hình chưa từng có ghi nhận, riêng điểm của mô hình vẫn xếp 28 điểm vào nhóm 20%.
- **Mưa, nội thành: dùng được.** Mọi điểm đều được tô màu. Nhưng lưu ý tỉ lệ chọn bừa ở đây đã là 70%: ngày báo động, phần lớn đường lớn nội thành đều có màu (ghi chú 11, mục 3.2).
- **Mưa, ngoại thành: ngang chọn bừa theo cả hai cách.** 12 trong 35 điểm không được tô: Lê Quang Đạo – Trần Văn Mười, Trần Văn Mười, Nguyễn Thị Thử, Bà Triệu (Hóc Môn); Vĩnh Lộc, Võ Văn Vân, Bùi Thanh Khiết, Trịnh Quang Nghị (Bình Chánh); Nguyễn Văn Tạo (Nhà Bè); Trịnh Thị Dối, Văn Tiến Dũng; ĐT743A – Mỹ Phước Tân Vạn. Nhiều khả năng vì ghi nhận ngập dùng để học tập trung ở nội thành; tôi chưa kiểm chứng nguyên nhân này.

Cách làm và giới hạn:

- Mỗi điểm được định vị bằng tên đường và đường giao nêu trong tin. Định vị được 102 trong 122 điểm; 14 điểm nằm ngoài vùng mô hình (Vũng Tàu và Bình Dương cũ); 6 điểm chưa định vị được; 14 điểm chỉ có số nhà hoặc tên chỗ nên lấy đoạn đường quanh một vị trí ước lượng.
- Đơn vị là "tuyến" của mô hình. Tuyến trên đường trục có thể dài vài km, nên 21 điểm đang khớp vào đoạn dài hơn 6 km.
- Một điểm tính là "nằm trong nhóm" khi từ một nửa chiều dài tuyến khớp thuộc nhóm đó. Với luật dễ hơn (chỉ cần một tuyến khớp thuộc nhóm), mưa ngoại thành là 27 trong 35 theo cách (a) và 23 trong 35 theo cách (b); triều là 37 trong 37 theo cả hai cách. Kết luận không đổi.
- Bản đầu của ghi chú này (trưa 08/10) chỉ có cách (b) và gọi đó là nhóm bản đồ sẽ tô. Điều đó sai: bản chạy mỗi giờ xếp nhóm trên mọi tuyến nên tô rộng gấp đôi. Bảng trên đã sửa.
- Chạy lại: `python tools/doi_chieu_122_diem.py`. Danh sách đã định vị, kèm mã tuyến: `data/processed/hcm/diem_ngap_pc08_2026-10-06.csv`.

Việc làm với danh sách này:

| Ai | Việc | Tốn |
|---|---|---|
| Repo này | Đưa các điểm lên bản đồ như chỗ ngập đã biết, theo đúng nguyên nhân trong danh sách: điểm mưa lên mức cao khi trạm gần đó mưa tới ngưỡng hoặc Mô hình 2 báo động; điểm triều lên mức cao khi Phú An từ 1,50 m. Tìm đường coi chúng như tuyến có lịch sử ngập (ghi chú 11, quyết định 5). Với 21 điểm khớp vào đoạn dài, phải thu hẹp về đúng chỗ trước khi tô | Nằm trong bước 1 và 2 của lịch |
| Bạn làm mô hình, nếu còn thời gian | Thêm các tuyến trong file CSV làm nhãn dương cho Mô hình 1 rồi train lại. Giữ lại một phần điểm để kiểm, và không dùng bộ kiểm khóa 2025–2026 để chọn | Train lại ước chừng vài phút trên laptop |

Không có việc thứ hai thì sản phẩm vẫn đúng tại 102 điểm này; train lại chỉ giúp mô hình đoán tốt hơn ở những đường ngoại thành chưa ai liệt kê.

## 4. Gemini đọc camera

Ba khóa của nhóm đã nằm trong `.env` (`GEMINI_API_KEY`, `GEMINI_API_KEY_2`, `GEMINI_API_KEY_3`) và đều chạy. Thử lúc 11:45 hôm nay với 6 camera nằm sát tuyến từng ngập, mỗi camera 2 ảnh cách nhau 13 giây, dùng nguyên câu lệnh trong `cameras.py`:

| Mô hình | Kết quả |
|---|---|
| Gemini 2.5 Flash | Không dùng được: Google trả lời mô hình này không còn mở cho khóa mới |
| Gemini 3.8 Flash | Hai lần hết giờ sau 120 giây, một lần báo quá tải |
| Gemini 3.5 Flash | Trả lời sau 14 giây. Cả 6 camera: đường khô, không ngập; 5 thông thoáng, 1 đông |
| Gemini 3.1 Flash-Lite | Trả lời sau 8 giây. Cùng kết quả với 3.5 Flash trên cả 6 camera |

Tôi mở 2 trong 6 ảnh ra xem; mô tả của Gemini khớp với ảnh. Mỗi lần gọi 6 camera tốn khoảng 13.700 token đầu vào.

Ba điều chưa có hoặc cần biết:

- **Chưa thử được với cảnh ngập thật.** Lúc thử, các camera đều khô. Trạm mưa 32,4 mm trưa nay không có camera nào trong 2 km.
- **Hạn mức miễn phí nhỏ.** Theo nhật ký của bạn làm camera, 3.5 Flash cho 20 lần gọi mỗi khóa mỗi ngày. Ba khóa là 60 lần, tức khoảng 360 lượt đọc camera một ngày. Flash-Lite có hạn mức riêng, tôi chưa đo. Vì vậy chỉ gọi Gemini cho camera gần trạm đang mưa tới ngưỡng hoặc khi triều cao, không đọc đều cả 796 camera.
- **Camera chỉ phủ nội thành và các trục chính.** Ngoại thành phải dựa vào trạm mưa và báo ngập của người dùng.

Thứ tự mô hình giữ như `cameras.py` đang dùng: 3.5 Flash trước, hết hạn mức thì sang 3.1 Flash-Lite. Khi có ảnh ngập thật (mục 5), cho cả hai đọc cùng một bộ ảnh rồi mới quyết định có đổi không.

## 5. Dữ liệu đang ghi và lịch triều

`tools/ghi_du_lieu.py` chạy từ 12:02 ngày 08/10, ghi vào `data/raw/live/` (không vào git):

- mỗi 10 phút: ảnh radar Nhà Bè, mưa từng giờ của 44 trạm, mực nước Phú An;
- mỗi giờ: mức mưa Mô hình 2 tính ra cho hai thành phố;
- ảnh của 115 camera nằm sát tuyến từng ngập: mỗi giờ một lần; mỗi 10 phút khi có trạm mưa từ 5 mm trong giờ gần nhất hoặc triều từ 1,30 m.

Một lượt ghi mất 23 giây, lấy được 115 trong 115 camera, khoảng 6 MB ảnh.

**Bộ ghi đang chạy trong phiên làm việc với Claude trên laptop, nên đóng ứng dụng hoặc để máy ngủ là nó dừng.** Muốn chắc thì mở một cửa sổ PowerShell riêng và chạy:

```
cd "D:\HK1 4 year\Hackathon\MapForPeople"; $env:PYTHONUTF8 = '1'; .\.venv\Scripts\python.exe tools\ghi_du_lieu.py
```

Không chạy hai bản cùng lúc. Để dừng một bản: tạo file `data/raw/live/STOP`, chờ dòng "thấy file STOP, dừng" hiện trong `data/raw/live/recorder.log` (tối đa 10 phút), rồi xóa file `STOP` trước khi chạy bản mới.

Lịch triều tại Phú An (báo động 1, 2, 3 là 1,40 m, 1,50 m, 1,60 m):

- Bản tin: từ 08/10, sáng sớm mực nước lên trên báo động 2 và xấp xỉ báo động 3 ([Tuổi Trẻ 06/10](https://tuoitre.vn/du-bao-tphcm-va-nam-bo-co-mua-dong-ket-hop-trieu-cuong-nhung-ngay-toi-nguoi-dan-luu-y-gi-100261006125305219.htm)). Đỉnh cao nhất năm rơi vào 27–29/10, Phú An 1,70–1,75 m ([Tuổi Trẻ 02/10](https://tuoitre.vn/trieu-cuong-thang-10-co-the-toi-187m-tphcm-yeu-cau-san-sang-ung-pho-100261002141801211.htm)), tức sau buổi trình diễn.
- Mô hình triều trong `hydro.py` cho các đỉnh buổi chiều: 10/10 lúc 15:40, 11/10 lúc 16:40, 12/10 lúc 16:50, 13/10 lúc 17:50, và các đỉnh rạng sáng khoảng 03:40–04:40. Về độ cao nó ra 1,7–1,8 m cho 10–12/10, sai số ±0,15 m. Con số này cao hơn mức bản tin dự báo cho đỉnh cao nhất năm, nên tôi tin giờ đỉnh hơn tin độ cao.

Các đỉnh buổi chiều rơi vào lúc trời còn sáng và đường đông, là lúc camera cho ảnh rõ nhất. Ảnh ghi được trong bốn ngày đó dùng cho ba việc: kiểm Gemini với cảnh ngập thật, chỉnh ngưỡng mưa và triều của sản phẩm, và làm chế độ phát lại cho buổi trình diễn.

## 6. Máy tính

- **Train:** laptop là đủ. Mô hình 1 là LightGBM trên bảng 66 nghìn dòng, Mô hình 2 là hồi quy hai biến.
- **EC2, nếu nhóm mở:** dùng cho bộ ghi chạy suốt ngày đêm và làm máy chủ cho buổi trình diễn (bước ngày 12/10 trong lịch). Việc đầu tiên phải thử trên máy đó là từ đó có tải được ảnh camera, số liệu vndms và radar không. Nếu không được thì bộ ghi phải nằm trên một máy ở Việt Nam bật liên tục.

## 7. Việc tiếp theo

1. Repo này: bước 1 của ghi chú 11, đưa tuyến và mức của mô hình lên bản đồ, kèm lớp 122 điểm.
2. Giữ bộ ghi chạy tới hết 13/10.
3. Sau mỗi đỉnh triều chiều, lấy ảnh vừa ghi cho Gemini đọc và so với mắt người.
4. Bạn làm mô hình quyết định có train lại Mô hình 1 với file CSV hay không.
