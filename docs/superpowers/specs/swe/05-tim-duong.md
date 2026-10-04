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

- **Tốc độ theo loại đường** là bảng `SPEEDS_KMH` trong `graphroute.py`, **đã hiệu chỉnh với Goong** ngày 04/10/2026 (mục 5.2): xe máy đường dân cư 11,6 km/giờ, `tertiary` 14,5, `secondary` 18,1, `primary` 18,6, `trunk` 23,3; ô tô dân cư 10,0, `tertiary` 14,7, `secondary` 17,3, `primary` 21,3, `trunk` 30,0, `motorway` 47,0. Xe máy không đi `motorway`. Đường `*_link` dùng tốc độ của loại đường mẹ.
- Hệ số hiệu chỉnh `α` đã nằm sẵn trong bảng, không còn là tham số riêng.
- **`g`** là hệ số giao thông của cạnh ở thời điểm xuất phát, từ 0 tới 1 (spec 09). Hiện chưa dùng: mã nhận hệ số làm chậm từng cạnh qua tham số `slow` (1 là không đổi) để spec 09 và tránh ngập cắm vào mà không sửa thuật toán.
- **`β`** (mức ảnh hưởng của giao thông lên tốc độ) sẽ tìm được khi có số liệu TomTom.

### 2.2 Đường nhanh nhất

Thuật toán Dijkstra (`scipy.sparse.csgraph.dijkstra`) trên mạng đường OpenStreetMap, với chi phí là thời gian ở trên. Điểm đi và điểm đến được gắn vào nút gần nhất **thuộc thành phần liên thông mạnh lớn nhất của loại xe đó** (trên mạng TP.HCM thật là 91% số nút dùng được cho xe máy); nếu nút gần nhất xa hơn 300 m thì trả lỗi "Điểm này không gần đường nào".

### 2.3 Các lộ trình thay thế

Dựa trên ba nguồn nghiên cứu (mục 12). Một lộ trình thay thế được nhận khi nó **chấp nhận được** (Abraham và cộng sự):

1. **Không dài bất hợp lý:** thời gian tối đa 1,4 lần đường nhanh nhất (tham số của nghiên cứu người dùng Li và cộng sự).
2. **Chia sẻ giới hạn:** dùng chung tối đa 70% thời gian với mỗi lộ trình đã nhận. Bài gốc dùng 80% cho mạng cả lục địa; ở đô thị dày hạ xuống 70% vì các lộ trình thay thế của Goong chia sẻ trung vị chỉ 27% với đường chính của nó.
3. **Không có đường vòng dư thừa:** đoạn vòng không dài hơn 1,4 lần đoạn nó thay.
4. **Tối ưu cục bộ:** mọi đoạn dài bằng 1/4 phần vòng đều phải là đường ngắn nhất giữa hai đầu của nó. Điều kiện này loại các lộ trình ngoằn ngoèo bên trong một đoạn vòng.

Cách sinh ứng viên, theo thứ tự:

- **Đường qua nút trung gian.** Hai cây đường ngắn nhất, một từ điểm đi và một (trên đồ thị đảo chiều) từ điểm đến. Mỗi nút `v` cho một đường `đi→v→đến`. Cả 120 nghìn nút được lọc cùng lúc bằng numpy theo các điều kiện 1 đến 3, rồi xếp theo `2·thời gian + phần dùng chung − độ dài cao nguyên`. "Cao nguyên" là đoạn nằm trong cả hai cây; nếu dài hơn 1/4 phần vòng thì đảm bảo tối ưu cục bộ và khỏi kiểm tra. Nếu không, điều kiện 4 được kiểm tra trực tiếp bằng các cửa sổ Dijkstra (khoảng 4 ms mỗi lần). Phải kiểm tra trực tiếp vì trên lưới đều nhiều đường hòa nhau, cao nguyên vỡ thành mảnh ngắn dù lộ trình vẫn tốt. Mỗi đường chỉ dựng một lần, các nút nằm trên nó được đánh dấu để bỏ qua.
- **Phương pháp phạt** nếu chưa đủ: nhân 1,4 chi phí các cạnh đã chọn rồi tìm lại, tối đa 10 vòng, dừng sau 3 vòng liên tiếp không ra ứng viên mới. Ứng viên phải qua cùng bộ lọc.

**Không có con số cố định cho số lộ trình.** Lộ trình nào chấp nhận được thì được giữ, tối đa 6 mỗi phản hồi để phản hồi không quá nặng. Trên 120 cặp điểm thật ở TP.HCM: 5 cặp chỉ có một đường, trung bình 3,8 đường.

Lộ trình đầu luôn là đường nhanh nhất thật sự (kiểm tra bằng một bản Dijkstra độc lập), các lộ trình sau xếp theo thời gian.

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

**Trạng thái (04/10/2026):** đã làm bước 2 và phần phản hồi của thuật toán riêng, trong `routes_route.py`. Chưa làm các bước 1, 3, 4, 5, 6 (giao thông, tránh ngập, Goong, chấm ngập), nên các trường `flooded_m`, `exposure`, `max_level`, `units`, `by_hour`, `goong_duration_s` chưa có trong phản hồi; `replay` chưa được dùng; `traffic` ghi `{"source": "none"}`; `duration_normal_s` bằng `duration_s`; mọi lộ trình có `engine: "own"` và `estimated: true`. Phản hồi hiện có thêm `snapped` (nút mà điểm đi và điểm đến được gắn vào, kèm khoảng cách) để giao diện vẽ đoạn nối từ điểm người dùng chọn tới đường. Mỗi chặng trong `steps` có thêm `duration_s`.

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

### 5.2 Lệnh `python -m floodrisk.api.routecheck hcm --pairs 60 --vehicle bike`

**Đã làm (chỉ với Goong).** Chọn ngẫu nhiên các cặp điểm cách nhau 3 tới 15 km theo hạt giống cố định (`--seed`), lấy lộ trình nhanh nhất của Goong và của mình, rồi ghi `reports/route_check_{city}_{vehicle}.md`:

- tỉ lệ chiều dài và tỉ lệ thời gian (trung vị, p10 đến p90);
- mức trùng của hai đường đi (trung bình hai chiều của phần nằm trong 30 m quanh nhau);
- năm cặp ít trùng nhất, để mở trên bản đồ xem vì sao;
- hệ số gợi ý để co giãn bảng tốc độ, và giờ chạy (đường vắng hay đông).

Lệnh không tự sửa bảng tốc độ; sửa bảng là việc làm tay. Mỗi lượt gọi Goong một lần mỗi cặp.

**Chưa làm:** phần TomTom (lộ trình ô tô có thời gian tách giao thông) và hiệu chỉnh `β`; chờ spec 09. Tỉ lệ giữa các loại đường của xe máy đã được tinh chỉnh một lần bằng tìm kiếm từng tham số trên 54 cặp, bằng mã tạm không đưa vào kho.

### 5.2.1 Kết quả ngày 04/10/2026 (khoảng 21 giờ Chủ nhật, đường vắng)

| Phép đo | Xe máy | Ô tô |
|---|---|---|
| Chiều dài ta / Goong, trung vị | 0,999 | 1,000 |
| Thời gian ta / Goong, trung vị, **trước** hiệu chỉnh | 0,60 | 0,65 |
| Thời gian ta / Goong, trung vị, **sau** hiệu chỉnh (cặp mới) | 0,99 | 0,985 |
| Mức trùng trung bình với đường Goong (80 cặp mới) | 0,650 (bảng ban đầu: 0,632) | chưa đo trên cặp mới |
| Số cặp dùng để chỉnh / kiểm | 54 / 26, rồi 80 cặp mới | 26 / 13 |

**Giới hạn phải nhớ:**

- Khớp thời gian là kết quả đáng tin. Khớp *hình dạng* đường thì yếu: phần tinh chỉnh tỉ lệ giữa các loại đường chỉ hơn bảng ban đầu 0,018 điểm trùng, tốt hơn ở 13 cặp, kém hơn ở 11, bằng nhau ở 56 trong 80 cặp mới. Đừng nói với ai rằng nó "tối ưu".
- Mức trùng trung bình 0,65 (trung vị khoảng 0,73) nghĩa là đường của ta và của Goong thường đi qua cùng các trục lớn nhưng khác ở đoạn đầu và đoạn cuối. Ta không biết bên nào gần thực tế hơn.
- Đo lúc đường vắng. Giờ cao điểm cần lớp giao thông (spec 09).
- Ô tô chỉ có 39 cặp.

**Độ phủ lộ trình thay thế (70 cặp, xe máy):** 44% lộ trình thay thế của Goong nằm trong tập của ta (từ 85% nằm trong 30 m). Lộ trình thay thế của Goong chia sẻ trung vị 27% với đường chính của nó và chậm hơn 1,00 đến 1,18 lần. Các lộ trình của ta chia sẻ trung bình 0,33 với nhau và chậm hơn đường nhanh nhất trung bình 1,10 lần.

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

Đánh dấu `[x]` là đã làm và đã chạy kiểm thử hoặc đo thật ngày 04/10/2026; `[ ]` là chưa làm hoặc chưa kiểm chứng được. Mã kiểm thử: `tests/api/test_graphroute.py`, `test_route.py`, `test_routecheck.py`.

**S5.1, kiểm thử trên đồ thị tổng hợp:**

- [x] Đường nhanh nhất giữa hai góc đối diện của lưới 4 × 4 dài đúng 1.200 m, và lộ trình đầu bằng đường ngắn nhất tính bằng một bản Dijkstra độc lập (`heapq`) trên 40 cặp ngẫu nhiên.
- [x] Lưới đều có ít nhất hai lộ trình giữa hai góc đối diện, với từng cơ chế riêng (chỉ qua nút trung gian, chỉ phạt, cả hai).
- [x] Ba hành lang song song dài 10,0, 10,8 và 18,0 km: đúng hai lộ trình đầu được trả về; hành lang 18 km (chậm hơn 1,4 lần) bị loại.
- [x] Một hành lang duy nhất: đúng một lộ trình.
- [x] Đường vòng 100 m quanh một ngã tư của đường dài 10 km không phải lộ trình thay thế (chia sẻ 95%).
- [x] Kiểm tra tối ưu cục bộ loại một lộ trình có đoạn ngoằn ngoèo bên trong đoạn vòng dài, và nhận lộ trình tương tự không ngoằn ngoèo.
- [x] Trên 40 cặp ngẫu nhiên của mạng có đường một chiều: mọi lộ trình nối đúng đầu tới cuối, không lặp nút, các cạnh nối liền nhau, thời gian khớp tổng chi phí, sắp theo thời gian, chậm hơn đường nhanh nhất tối đa 1,4 lần, chia sẻ giữa mọi cặp tối đa 70%, không quá 6.
- [x] Đường một chiều được tôn trọng; cạnh `motorway` không đi được bằng xe máy và đi được bằng ô tô; hệ số làm chậm đổi đường đi.
- [x] Hai điểm không nối được với nhau: không có lộ trình.
- [x] Gắn điểm vào thành phần liên thông lớn nhất, không vào đảo gần hơn; theo từng loại xe.
- [x] Chỉ dẫn gộp theo tên đường, nhận ra rẽ trái, rẽ phải; hình học lưu ngược chiều vẫn trả đúng chiều đi; cạnh khuyên và cạnh song song không làm hỏng.
- [x] 24 yêu cầu song song với chi phí khác nhau cho kết quả giống hệt chạy lần lượt (đồ thị được dùng chung giữa các yêu cầu).
- [x] Điểm ngoài khung thành phố, tọa độ sai dạng, hai điểm trùng nhau, điểm cách đường quá 300 m: 422 với lời tiếng Việt cụ thể.
- [ ] Goong lỗi thì vẫn trả lộ trình của thuật toán riêng. Hiện `GET /api/route` chưa gọi Goong, nên chưa có gì để lỗi; xem mục 3.

**S5.1, trên mạng đường thật:**

- [x] Nạp mạng đường TP.HCM: 0,4 giây. Mỗi lần `find_routes`: trung vị khoảng 170–240 ms, p95 khoảng 300–330 ms, lớn nhất 446 ms (120 cặp cách nhau 3–15 km, máy phát triển đang chạy thêm máy chủ). Cả lời gọi `GET /api/route` khoảng 280 ms; lần đầu 1,7 giây vì nạp mạng đường.
- [x] Ba cặp điểm quen thuộc, xem bằng mắt trên bản đồ Goong: Chợ Bến Thành → Landmark 81 (5,35 km, 20,0 phút; Goong: 5,41 km, 18,8 phút), ĐH Bách Khoa → Đầm Sen (4,06 km, 14,5 phút), và Bến Thành → sân bay (từ chối đúng vì tọa độ nằm giữa đường băng, cách đường 827 m). Các lộ trình thay thế đi qua những trục quen thuộc: Điện Biên Phủ, Nguyễn Thị Minh Khai, Xô Viết Nghệ Tĩnh, cầu Thủ Thiêm. Chưa đủ năm cặp và chưa có người sống ở TP.HCM xem; việc này cần làm.

**S5.2:**

- [ ] Các lộ trình hiện cùng lúc; chạm một lộ trình trên bản đồ hoặc một thẻ thì nó nổi lên.
- [ ] Mỗi thẻ có thời gian, quãng đường và giờ tới nơi; mở thẻ thấy danh sách chỉ dẫn.
- [ ] Nút đổi chỗ hai điểm và ô chọn loại xe làm tìm lại.
- [ ] Lúc mọi đoạn mức thấp, bảng không có dòng nào về ngập.
- [ ] Bảng dùng được ở chiều rộng 360 px mà không che hết bản đồ.

**S5.3:**

- [x] `routecheck` chạy xong cho TP.HCM với xe máy, có báo cáo trong `reports/` (kết quả ở mục 5.2.1). Ô tô chưa chạy bằng lệnh này (đã đo bằng mã tạm).
- [ ] Năm cặp lệch nhất đã được xem trên bản đồ, có một dòng kết luận cho mỗi cặp. Chưa làm.
- [x] Với Goong giả trong kiểm thử, lệnh ghi đúng báo cáo, tính đúng hệ số gợi ý, và bỏ qua cặp khi Goong lỗi. (Không có `routing.json`: bảng tốc độ nằm trong mã, xem mục 2.1.)
- [ ] `β` và phần TomTom: chờ spec 09.

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

## 12. Nguồn nghiên cứu

Thiết kế mục 2.3 dựa trên các bài sau (đã đọc ngày 04/10/2026):

- I. Abraham, D. Delling, A. V. Goldberg, R. F. Werneck, ["Alternative Routes in Road Networks"](https://microsoft.com/en-us/research/wp-content/uploads/2010/01/alternativeSea2010.pdf), SEA 2010 (Journal of Experimental Algorithmics 2013). Định nghĩa lộ trình thay thế *chấp nhận được* (chia sẻ giới hạn γ, kéo dài đồng đều ε, tối ưu cục bộ α), phép thử T, lộ trình qua một nút trung gian, độ dài cao nguyên làm cận dưới của tối ưu cục bộ. Tham số trong bài: ε = 25%, γ = 80%, α = 25%, trên mạng châu Âu 18 triệu nút. Bài cũng cho biết thành công tìm *một* lộ trình thay thế là 91–94%, và giảm còn 43–62% khi cần ba lộ trình.
- J. Dees, R. Geisberger, P. Sanders, R. Bader, ["Defining and Computing Alternative Routes in Road Networks"](https://arxiv.org/abs/1002.4330), 2010. Các phương pháp cao nguyên và phạt, vấn đề "đường vòng nhỏ" của phương pháp phạt, ý tưởng kết hợp hai phương pháp.
- L. Li, M. A. Cheema, H. Lu, M. E. Ali, A. N. Toosi, ["Comparing Alternative Route Planning Techniques: A Comparative User Study on Melbourne, Dhaka and Copenhagen Road Networks"](https://arxiv.org/abs/2006.08475), 2021. 520 đánh giá của người dùng cho bốn phương pháp (Google Maps, cao nguyên, phạt, khác biệt): không có khác biệt có ý nghĩa thống kê, phương pháp phạt có điểm trung bình cao nhất (3,53 trên 5). Tham số: phạt ×1,4, kéo dài tối đa 1,4. Người dùng phàn nàn về đường ngoằn ngoèo và nhiều chỗ rẽ.

**Khác với các bài trên:** bài gốc kiểm tra tối ưu cục bộ bằng phép thử T trên đường qua một nút; ở đây phép thử được làm trực tiếp bằng các cửa sổ Dijkstra vì mạng một thành phố đủ nhỏ để làm được trong vài mili giây, và dùng được cho cả ứng viên của phương pháp phạt. Ngưỡng γ hạ từ 80% xuống 70% là quyết định riêng của dự án, dựa trên đo với Goong, không phải kết luận của bài báo nào.
