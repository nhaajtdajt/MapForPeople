# Spec 05: Tìm đường

**Mã theo dõi:** S5.1, S5.2, S5.3 (lõi, ngày 2); S5.4 (lõi, ngày 4–5); S5.5 (nên, ngày 7).

Spec này được viết lại ngày 04/10/2026. Bản trước coi thuật toán riêng chỉ là công cụ tránh ngập, còn đường nhanh nhất thì lấy của Goong. Bản này đặt thuật toán riêng làm bộ máy chính cho mọi lộ trình, kể cả lúc trời khô, rồi mới thêm việc tránh ngập lên trên. Việc tìm địa điểm đã chuyển sang spec 08.

## Mục tiêu

Người dùng chọn điểm đi, điểm đến và loại xe. Họ thấy vài lộ trình khác nhau trên bản đồ, mỗi lộ trình có quãng đường, thời gian dự kiến và giờ tới nơi; chọn lộ trình nào thì lộ trình đó nổi lên cùng danh sách chỉ dẫn. Đó là hành vi lúc bình thường. Khi có nguy cơ ngập, danh sách có thêm một đường tránh ngập, và mỗi lộ trình ghi rõ đi qua bao nhiêu mét nguy cơ cao.

## 1. Vì sao thuật toán riêng là bộ máy chính

| Câu hỏi | Trả lời |
|---|---|
| Goong có trả nhiều lộ trình không? | Chỉ 1 hoặc 2. Tám lần gọi với khóa thật ngày 04/10: bốn lần trả 1 lộ trình, bốn lần trả 2 |
| Vì sao không chỉ hiện lộ trình của Goong? | Không đủ lựa chọn để tránh ngập, và Goong không cho đặt điểm trung gian |
| Vì sao không trộn thời gian của Goong với thời gian tự tính? | Hai con số từ hai cách tính khác nhau thì không so được với nhau. Người dùng cần biết đường tránh dài hơn mấy phút, nên mọi lộ trình phải được tính giờ bằng cùng một cách |
| Goong còn dùng làm gì? | Nền bản đồ, tìm địa điểm, chỉ dẫn từng bước bằng tiếng Việt, và làm mốc đối chiếu cho thuật toán riêng (mục 5). Khi thành phố chưa có mạng đường thì Goong là phương án lùi |
| TomTom có trả lộ trình không? | Có. Gọi thử ngày 04/10 cho Bến Thành tới Landmark 81: 4 lộ trình, mỗi lộ trình có thời gian lúc không có giao thông và thời gian có giao thông. Nó được dùng làm mốc đối chiếu thứ hai, không hiện cho người dùng (spec 09, mục 8) |

## 2. Tìm đường lúc bình thường (S5.1)

### 2.1 Thời gian đi một cạnh

```
thời gian = chiều dài / (tốc độ theo loại đường × α × (1 − β × (1 − g)))
```

- **Tốc độ theo loại đường** lấy từ bảng ở QĐKT mục 7.2, theo xe máy và ô tô. Xe máy không đi `motorway`.
- **`α`** hiệu chỉnh tốc độ lúc đường thông, một giá trị cho mỗi loại xe. Trước khi đối chiếu (mục 5), `α` bằng 1.
- **`g`** là hệ số giao thông của cạnh ở thời điểm xuất phát, từ 0 tới 1 (spec 09). Chưa có số liệu nào thì `g` bằng 1.
- **`β`** là mức ảnh hưởng của giao thông lên tốc độ, cũng tìm được ở mục 5. Trước khi đối chiếu, `β` bằng 1.

### 2.2 Đường nhanh nhất

Thuật toán Dijkstra trên mạng đường OpenStreetMap, với chi phí là thời gian ở trên. Điểm đi và điểm đến được gắn vào nút gần nhất; nếu nút gần nhất xa hơn 300 m thì trả lỗi "Điểm này không gần đường nào".

### 2.3 Các lộ trình thay thế

Dùng phương pháp phạt lặp:

1. Tìm đường nhanh nhất. Đó là lộ trình số 1.
2. Nhân chi phí của mọi cạnh trên lộ trình vừa tìm với 1,5, rồi tìm lại.
3. Lộ trình mới được coi là **hợp lý**, và được giữ, nếu nó trùng với mỗi lộ trình đã giữ không quá 75% chiều dài, và thời gian thật của nó (tính bằng chi phí gốc, không phạt) không quá 1,4 lần đường nhanh nhất.
4. Lặp tới khi ba lần liên tiếp không ra lộ trình hợp lý nào, hoặc đã thử 12 lần.

**Không có con số cố định cho số lộ trình.** Lộ trình nào hợp lý theo bước 3 thì đều được giữ: cặp điểm chỉ có một đường đi tốt thì trả một, cặp điểm có nhiều đường song song thì trả nhiều. Giới hạn duy nhất là giới hạn kỹ thuật: tối đa 6 lộ trình mỗi phản hồi, để phản hồi không quá nặng. Càng nhiều lộ trình hợp lý thì càng có nhiều lựa chọn để tránh ngập.

Ba con số 1,5, 75% và 1,4 là giá trị khởi đầu, chỉnh sau khi nhìn kết quả trên mạng đường thật. Cách này đơn giản và dùng lại đúng hàm tìm đường ngắn nhất. Nhược điểm đã biết: đôi khi lộ trình thay thế chỉ là một đoạn vòng nhỏ quanh lộ trình chính; ngưỡng 75% lọc bớt trường hợp đó.

### 2.4 Chỉ dẫn

Gộp các cạnh liền nhau cùng tên đường thành một chặng. Mỗi chặng có tên đường, chiều dài, và hướng rẽ vào chặng đó (thẳng, trái, phải, quay đầu), suy từ góc giữa hai cạnh. Tên đường lấy từ `units.parquet` qua `edge_units.parquet`; cạnh không tên ghi là "đường không tên".

Chỉ dẫn này đủ để người dùng hình dung lộ trình. Nó không thay được chỉ dẫn của một ứng dụng dẫn đường.

### 2.5 Tốc độ xử lý

Một lần tìm đường trên mạng đường thật của TP.HCM phải dưới 0,5 giây, và cả lời gọi `GET /api/route` dưới 3 giây dù phải tìm nhiều lần. Hai cách để đạt, áp dụng theo thứ tự:

1. Dựng ma trận thưa một lần lúc khởi động; mỗi lần tìm chỉ thay mảng chi phí.
2. Chỉ tìm trong phần mạng đường nằm trong khung chữ nhật quanh hai điểm, nới 3 km mỗi phía.

Phải đo ngay khi nhận được ba file mạng đường.

## 3. `GET /api/route`

Tham số: `city`, `origin=lat,lon`, `destination=lat,lon`, `vehicle` (`bike` mặc định, hoặc `car`), `replay` tùy chọn.

Các bước:

1. Lấy hệ số giao thông của từng cạnh cho thời điểm này (spec 09).
2. Tìm đường nhanh nhất và mọi lộ trình thay thế hợp lý (mục 2.3).
3. Nếu có ít nhất một lộ trình đi qua đoạn mức vừa hoặc cao, tìm thêm đường tránh ngập (mục 6).
4. Gọi Direction V2 của Goong. Lộ trình của Goong được tính giờ lại bằng cách của mình (mục 5.1). Nếu nó khác mọi lộ trình đã có trên 25% chiều dài thì thêm nó vào danh sách.
5. Chấm nguy cơ ngập cho từng lộ trình bằng `score_route`.
6. Chọn lộ trình đề xuất: `flooded_m` nhỏ nhất, rồi `exposure` nhỏ nhất, rồi thời gian ngắn nhất. Lúc trời khô, quy tắc này cho ra đúng đường nhanh nhất.

Phản hồi:

```json
{
  "routes": [
    {
      "id": 0,
      "kind": "fastest",
      "engine": "own",
      "recommended": true,
      "long_detour": false,
      "distance_m": 7400,
      "duration_s": 1260,
      "duration_normal_s": 1140,
      "arrive_at": "2026-10-06T17:42:00+07:00",
      "goong_duration_s": null,
      "flooded_m": 0.0,
      "exposure": 12.3,
      "max_level": 0,
      "units": [],
      "steps": [{"name": "Nguyễn Hữu Cảnh", "distance_m": 1200, "turn": "right"}],
      "by_hour": [{"hour": 0, "flooded_m": 0.0, "exposure": 12.3}],
      "geometry": {"type": "LineString", "coordinates": [[106.7, 10.78]]}
    }
  ],
  "traffic": {"source": "typical", "observed_at": null},
  "advice": null,
  "notes": []
}
```

| Trường | Nghĩa |
|---|---|
| `kind` | `fastest`, `alternative`, `flood-safe`, hoặc `goong` |
| `engine` | `own` hoặc `goong` |
| `duration_s` | Thời gian lúc này: có giao thông, có chậm do ngập |
| `duration_normal_s` | Thời gian khi đường thông và không ngập. Giao diện dùng nó để nói "bình thường mất 19 phút" |
| `goong_duration_s` | Thời gian do Goong ước tính; chỉ có ở lộ trình của Goong |
| `long_detour` | Đúng khi `duration_s` lớn hơn 1,5 lần đường nhanh nhất |
| `steps` | Chỉ dẫn theo chặng. Lộ trình của Goong dùng chỉ dẫn tiếng Việt Goong trả về |
| `traffic` | Nguồn giao thông đã dùng, để giao diện ghi nhãn (spec 09) |
| `by_hour`, `advice` | Thuộc spec 06 |

Khi có sự cố:

| Tình huống | Hành vi |
|---|---|
| Điểm ngoài khung thành phố, hoặc hai điểm trùng nhau | 422, không gọi Goong |
| Goong lỗi | Vẫn trả các lộ trình của thuật toán riêng với mã 200; `notes` ghi "Không đối chiếu được với Goong" |
| Thành phố chưa có mạng đường | Chỉ trả lộ trình của Goong, giờ theo Goong; `notes` ghi rõ |
| Không tìm được đường nào | 404 với lời "Không tìm được đường giữa hai điểm này" |

## 4. Giao diện lộ trình (S5.2)

- Bảng `RoutePanel` có ô điểm đi, ô điểm đến, nút đổi chỗ hai điểm, và ô chọn xe máy hay ô tô. Mỗi ô nhập dùng cùng bộ tìm kiếm của spec 08, kèm hai lựa chọn "Vị trí của tôi" và "Chọn trên bản đồ".
- Bản đồ vẽ mọi lộ trình cùng lúc: lộ trình đang chọn nét đậm màu xanh dương, các lộ trình khác nét mảnh màu xám, chạm vào được. Lớp ngập nằm dưới, để thấy lộ trình tránh đoạn nào.
- Mỗi lộ trình một thẻ:

| Dòng trên thẻ | Ví dụ |
|---|---|
| Tên | "Nhanh nhất", "Lộ trình khác", "Tránh ngập", "Theo Goong"; thẻ đề xuất có chữ "Nên đi" |
| Thời gian | "21 phút · 7,4 km · tới nơi khoảng 17:42" |
| So với bình thường | "Bình thường mất 19 phút"; chỉ hiện khi chênh từ 2 phút |
| Nguy cơ ngập | "Đi qua 350 m nguy cơ cao: Nguyễn Hữu Cảnh" hoặc "Không qua đoạn nguy cơ cao" |
| So với đường nhanh nhất | "Lâu hơn 5 phút"; có `long_detour` thì thêm "Đường vòng xa" |

- Các thẻ được sắp theo thời gian lúc này, thẻ đề xuất luôn đứng đầu. Bảng hiện ba thẻ đầu; nếu còn lộ trình thì có dòng "Xem thêm N lộ trình". Bản đồ vẫn vẽ tất cả.
- Chạm một thẻ: lộ trình đó nổi lên, bản đồ phóng cho vừa, và thẻ mở ra danh sách chỉ dẫn.
- Lúc trời khô và không lộ trình nào qua đoạn có nguy cơ, dòng nguy cơ ngập không hiện. Bảng lúc đó trông như bảng lộ trình của một bản đồ thông thường.
- Ghi chú cố định cuối bảng: "Thời gian là ước lượng theo loại đường và mức độ đông. Bản đồ có thể thiếu một số đoạn cấm xe hoặc cấm rẽ." Dưới đó là nhãn nguồn giao thông.
- Khi lộ trình đề xuất vẫn qua đoạn mức cao: "Ngập thường kéo theo ùn tắc; thời gian thực tế có thể dài hơn."

## 5. Đối chiếu với Goong và TomTom (S5.3)

Đây là cách trả lời câu hỏi "đường mình tìm có đúng là nhanh nhất không, và thời gian mình báo có hợp lý không". Có hai mốc: Goong cho lộ trình và thời gian của xe máy; TomTom cho thời gian của ô tô, tách riêng lúc không có giao thông và lúc có giao thông.

### 5.1 Tính giờ cho một lộ trình bất kỳ

Hàm `time_polyline(coords, vehicle, when)`: rải điểm mỗi 20 m dọc lộ trình, mỗi điểm tìm cạnh gần nhất trong 25 m có hướng lệch không quá 30 độ, rồi cộng `20 m / tốc độ của cạnh đó`. Điểm không khớp cạnh nào dùng tốc độ của loại đường thấp nhất. Nhờ hàm này, lộ trình của Goong và lộ trình gửi tới `POST /api/score-route` được tính giờ theo cùng một cách với lộ trình của mình.

### 5.2 Lệnh `python -m floodrisk.api.routecheck hcm --pairs 50 --vehicle bike`

1. Chọn ngẫu nhiên 50 cặp điểm cách nhau 3 tới 12 km trên các đường có tên, theo một hạt giống cố định.
2. Với mỗi cặp: lấy lộ trình của Goong, lộ trình nhanh nhất của TomTom (khi có khóa), và đường nhanh nhất của mình.
3. Hiệu chỉnh, rồi ghi vào `processed/{city}/routing.json`:
   - **Ô tô:** `α` sao cho thời gian lúc đường thông của mình khớp thời gian không có giao thông của TomTom (trung vị của tỉ lệ bằng 1). Sau đó `β` sao cho thời gian có giao thông của mình khớp thời gian có giao thông của TomTom.
   - **Xe máy:** `α` sao cho thời gian của mình khớp thời gian của Goong, chạy vào giờ thấp điểm. `β` của xe máy bằng 0,6 lần của ô tô (spec 09, mục 2.1).
4. Ghi `reports/route_check_{city}_{vehicle}.md` gồm:
   - Tỉ lệ thời gian của mình trên thời gian của từng mốc, trước và sau hiệu chỉnh: trung vị, và khoảng từ phân vị 10 tới 90.
   - Phần chiều dài trùng nhau giữa lộ trình của mình và của từng mốc: trung vị, và số cặp trùng dưới 50%.
   - Năm cặp lệch nhiều nhất, kèm tọa độ, để mở trên bản đồ xem vì sao.

Mỗi lượt gọi Goong 50 lần và TomTom 50 lần; hạn mức miễn phí của TomTom là 2.500 yêu cầu mỗi ngày. Không có khóa TomTom thì lệnh chỉ dùng Goong, `β` giữ bằng 1, và báo cáo ghi rõ điều đó.

### 5.3 Đọc kết quả thế nào

| Kết quả | Nghĩa | Việc làm |
|---|---|---|
| Trùng trung vị từ 70%, tỉ lệ thời gian sau hiệu chỉnh nằm trong 0,8–1,25 ở phần lớn các cặp | Thuật toán riêng đi gần giống Goong | Dùng được; đưa hai con số vào bài thuyết trình |
| Trùng thấp, nhưng thời gian của mình tính trên lộ trình của Goong lại dài hơn đường của mình | Bảng tốc độ đang ưu tiên sai loại đường | Chỉnh bảng tốc độ theo từng loại đường, chạy lại |
| Nhiều cặp mà lộ trình của mình đi qua chỗ Goong tránh | Mạng đường thiếu thông tin cấm xe, cấm rẽ, một chiều | Xem năm cặp lệch nhất; báo người dữ liệu nếu lỗi nằm ở dữ liệu |

Cả hai mốc đều không phải là sự thật tuyệt đối. Không ai biết thời gian của Goong có tính giao thông hay không, và TomTom không tính riêng cho xe máy (gọi thử với loại xe là xe máy cho đúng con số của ô tô). Phép đối chiếu này cho biết thuật toán riêng có hợp lý không; nó không chứng minh thời gian dự kiến là đúng, nhất là với xe máy.

## 6. Tránh ngập (S5.4)

Cộng thêm vào phần ở trên, theo QĐKT mục 7.2:

- **Chi phí có phạt:** với mỗi đoạn mà cạnh đi qua, thời gian trên đoạn đó được nhân thêm `loc_weight × hệ số xe × mức phạt`, với mức phạt 2 cho mức vừa và 20 cho mức cao. Phần phạt chỉ dùng để chọn đường; thời gian báo cho người dùng không tính nó.
- **Đường tránh ngập** là đường ngắn nhất theo chi phí có phạt. Nó có `kind` là `flood-safe`. Nếu nó trùng một lộ trình đã có trên 90% chiều dài thì lộ trình đó được đổi `kind` thành `flood-safe`, không thêm lộ trình mới.
- **Thời gian lúc này** của mọi lộ trình đã tính cả việc ngập làm chậm (spec 09, mục 2.3). Vì vậy đường nhanh nhất lúc bình thường có thể không còn nhanh nhất khi nó đi qua đoạn ngập, và danh sách được sắp theo thời gian lúc này.
- Lớp nguy cơ dùng để phạt và để chấm là lớp của giờ 0, đã áp báo cáo của người dùng.

## 7. Hệ số xe và chấm lộ trình cho ứng dụng khác (S5.5)

- **Hệ số xe:** ô tô chỉ tính một nửa trên đoạn có độ sâu lớn nhất từng ghi nhận dưới 30 cm; xe máy luôn tính đủ. Hệ số đi vào cả `score_route` lẫn phần phạt.
- **`POST /api/score-route`:** nhận `{city, coordinates, vehicle}` với `coordinates` là danh sách `[lon, lat]`. Trả điểm nguy cơ ngập của `score_route` và thời gian của `time_polyline`. Trả 422 khi có dưới hai điểm hoặc có điểm ngoài khung thành phố. Một ứng dụng dẫn đường khác gửi lộ trình của nó tới đây và nhận về mức nguy cơ ngập; đây là điểm tích hợp với hệ sinh thái của ban tổ chức.
- Trang `/docs` do FastAPI tự sinh là tài liệu tích hợp. Mỗi endpoint có một dòng mô tả tiếng Việt và một ví dụ.

## 8. Nơi đặt mã

| File | Việc |
|---|---|
| `api/graphroute.py` | Lớp `RoadGraph`: nạp mạng đường, thời gian từng cạnh, đường ngắn nhất, lộ trình thay thế, chi phí có phạt, chỉ dẫn, `time_polyline` |
| `api/routing.py` | `score_route`: chấm nguy cơ ngập cho một chuỗi tọa độ |
| `api/routes_route.py` | `GET /api/route`, `POST /api/score-route` |
| `api/routecheck.py` | Lệnh đối chiếu với Goong |
| `api/traffic.py` | Hệ số giao thông (spec 09) |

Chữ ký khởi đầu của `RoadGraph` và phần lõi của hàm tìm đường ngắn nhất ở KH04 mục F. Hai hàm mới so với KH04: `alternatives(src, dst, cost, max_routes=6)` và `time_polyline`.

## 9. Chỗ đang dùng bản giả

| Cần | Bản giả | Bản thật đến khi nào |
|---|---|---|
| Mạng đường | Lưới 4 × 4 giao lộ của dữ liệu mẫu | Trưa ngày 2 (TP.HCM), hết ngày 3 (Đà Nẵng) |
| Lớp nguy cơ để phạt | Bảng mẫu: đoạn 5, 6, 7 mức cao | Hết ngày 2 |
| Giao thông | Tầng điển hình của spec 09 | Khi có khóa TomTom |
| Goong trong kiểm thử | Đối tượng giả; kiểm thử không gọi mạng | Không thay |

**Mạng đường thật của TP.HCM đã có (04/10/2026), ở `data/processed/hcm/`.** Đã kiểm theo hợp đồng và đạt: 120.120 nút, 272.052 cạnh, 43.352 đoạn, 148.662 dòng `edge_units`. Bốn điều phải xử lý khi nạp:

- **Mạng không liên thông hoàn toàn:** 1.613 thành phần liên thông mạnh; thành phần lớn nhất chiếm 96% số nút. Điểm đi hoặc đến phải gắn vào nút gần nhất *thuộc thành phần lớn nhất*, nếu không sẽ gắn vào một ngõ cụt tách rời và không đi tới đâu được.
- **133 cạnh khuyên** (`u` bằng `v`), hầu hết là đường nhỏ. Bỏ chúng khỏi ma trận khi dựng đồ thị.
- **Cạnh dài bất thường:** 21 cạnh dài trên 3 km (dài nhất 15,5 km) và 16 cạnh ngắn hơn 1 m. Các cạnh dài đều là `motorway`, xe máy không đi, nên không ảnh hưởng xe máy; vẫn phải để ý khi tính "gắn nút gần nhất".
- **Chỉ một nửa số cạnh có dòng trong `edge_units`** (cạnh không tên không có đoạn, đúng hợp đồng). Cạnh không có đoạn không bao giờ bị phạt ngập, kể cả khi nằm giữa vùng ngập. Phải nói rõ điều này trên giao diện khi đã có lớp ngập.

Cột địa hình của `units.parquet` còn rỗng toàn bộ (đúng như dự kiến, đến hết ngày 4).

Lưới mẫu quá nhỏ để thấy lộ trình thay thế có hợp lý hay không. Nếu hết ngày 2 mà mạng đường thật của TP.HCM chưa đến, kỹ sư phần mềm tự tải một vùng 5 × 5 km ở trung tâm bằng OSMnx, ghi ra đúng ba file theo hợp đồng (bảng `edge_units` để rỗng), và dùng nó cho tới khi file thật đến.

## 10. Nghiệm thu

**S5.1, kiểm thử trên lưới mẫu:**

- [ ] Đường nhanh nhất giữa hai góc đối diện của lưới dài đúng 1.200 m.
- [ ] `alternatives` trả ít nhất hai lộ trình giữa hai góc đối diện; không cặp nào trùng nhau quá 75%; không lộ trình nào chậm hơn 1,4 lần lộ trình đầu.
- [ ] Giữa hai đầu của cùng một đường thẳng trên lưới, `alternatives` trả đúng một lộ trình: mọi đường khác đều chậm hơn 1,4 lần.
- [ ] Không phản hồi nào có quá 6 lộ trình.
- [ ] Cạnh `motorway` không đi được bằng xe máy và đi được bằng ô tô.
- [ ] Hai điểm không nối được với nhau: không có lộ trình của thuật toán riêng, endpoint lùi về Goong.
- [ ] Chỉ dẫn của một lộ trình hình chữ L có đúng hai chặng và một lần rẽ.
- [ ] Điểm ngoài khung thành phố, hoặc hai điểm trùng nhau, trả 422 và Goong không bị gọi.
- [ ] Goong lỗi: endpoint vẫn trả lộ trình của thuật toán riêng với mã 200 và có ghi chú.

**S5.1, trên mạng đường thật:**

- [ ] Một lần tìm đường ở TP.HCM dưới 0,5 giây; cả lời gọi dưới 3 giây. Ghi số đo: ……
- [ ] Năm cặp điểm quen thuộc cho lộ trình mà một người sống ở TP.HCM thấy hợp lý. Ghi các cặp đã thử: ……

**S5.2:**

- [ ] Các lộ trình hiện cùng lúc; chạm một lộ trình trên bản đồ hoặc một thẻ thì nó nổi lên.
- [ ] Mỗi thẻ có thời gian, quãng đường và giờ tới nơi; mở thẻ thấy danh sách chỉ dẫn.
- [ ] Nút đổi chỗ hai điểm và ô chọn loại xe làm tìm lại.
- [ ] Lúc mọi đoạn mức thấp, bảng không có dòng nào về ngập.
- [ ] Bảng dùng được ở chiều rộng 360 px mà không che hết bản đồ.

**S5.3:**

- [ ] `routecheck` chạy xong cho TP.HCM với xe máy và ô tô, có báo cáo trong `reports/`. Ghi kết quả: trùng trung vị …… %, tỉ lệ thời gian trước hiệu chỉnh ……, `α` = ……, `β` = ……
- [ ] Năm cặp lệch nhất đã được xem trên bản đồ, có một dòng kết luận cho mỗi cặp.
- [ ] Với Goong giả trong kiểm thử, lệnh ghi đúng `routing.json` và báo cáo.

**S5.4:**

- [ ] Mọi đoạn mức thấp: không có lộ trình `flood-safe`, lộ trình đề xuất là đường nhanh nhất.
- [ ] Đi từ đầu tới cuối đoạn mẫu số 6 (mức cao, `loc_weight` bằng 1): đường tránh ngập không dùng cạnh nào của đoạn đó.
- [ ] Chi phí có phạt của đường tránh ngập không lớn hơn của bất kỳ lộ trình nào khác.
- [ ] Lộ trình đề xuất luôn là lộ trình có `flooded_m` nhỏ nhất trong phản hồi.
- [ ] Trên mạng đường thật, kịch bản mưa 80 mm làm lộ trình qua một đoạn có lịch sử ngập đổi hướng.

**S5.5:**

- [ ] Ô tô trên đoạn có độ sâu lớn nhất 25 cm nhận nửa điểm; xe máy nhận đủ.
- [ ] `POST /api/score-route` với lộ trình dọc đoạn mẫu số 7 trả `flooded_m` khoảng 0,3 lần chiều dài chồng, và có `duration_s`.
- [ ] Trang `/docs` mở được và mỗi endpoint có mô tả tiếng Việt.

## 11. Không làm

- Không dẫn đường theo GPS từng bước, không giọng nói.
- Không có điểm dừng trung gian.
- Không xử lý cấm rẽ và cấm xe theo giờ. OpenStreetMap ở Việt Nam thiếu phần lớn thông tin này; giới hạn được ghi trên giao diện.
- Không dùng Google Maps, kể cả để đối chiếu (lý do ở spec 09).
