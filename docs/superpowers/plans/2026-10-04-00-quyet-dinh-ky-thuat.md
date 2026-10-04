# Quyết định kỹ thuật và hợp đồng dữ liệu

Tài liệu này chốt công nghệ, mô hình, giao diện giữa ba người, phân công và lịch. Khi nó khác với spec hoặc với bốn kế hoạch triển khai (01–04) thì tài liệu này đúng.

- **Spec:** `docs/superpowers/specs/2026-10-04-du-bao-nguy-co-ngap-duong-design.md`
- **Bản này:** 04/10/2026, bản 3. Bản 3 được viết sau hai việc: xem dữ liệu và nghiên cứu đã có trong dự án `mlai-car-access` (mục 14), và hai vòng phản biện của một agent độc lập không biết bối cảnh (mục 16).

## 0. Ba điều phải nắm trước

1. **Sản phẩm không phụ thuộc vào mô hình học máy.** Nguy cơ của mỗi đoạn đường bằng lịch sử ngập của đoạn đó nhân với mức mưa hoặc triều lúc này, rồi được sửa theo báo cáo của người dùng. Mô hình học máy (Mô hình 1) chỉ bổ sung cho nơi chưa có lịch sử, và chỉ khi nó qua kiểm chứng.
2. **Mô hình 1 nhiều khả năng không qua kiểm chứng.** Phép thử ngày 28/09/2026 trong dự án `mlai-car-access` cho thấy địa hình 30 m gần như không phân biệt được chỗ ngập: AUC 0,64 với ngập do triều, 0,48 với ngập do mưa (0,5 là ngẫu nhiên). Kết quả "mô hình không hơn ngẫu nhiên" là hợp lệ và phải được báo cáo đúng như vậy. Bài thuyết trình cần được viết sẵn cho trường hợp này.
3. **Kịch bản trình diễn chính là phát lại một ngày ngập đã xảy ra.** Hôm trình diễn mà trời khô thì bản đồ trực tiếp không có gì để xem. Chế độ phát lại (mục 4.8) là một phần của lõi, không phải phần thêm.

## 1. Các quyết định chính

| Hạng mục | Chọn | Lý do |
|---|---|---|
| Ngôn ngữ cho dữ liệu, mô hình, máy chủ | Python 3.12, một gói `floodrisk` | Ba người dùng chung hàm |
| Môi trường | `venv` + `pip`, một file `requirements.txt` | Chạy được trên Windows mà không cài thêm gì |
| Dữ liệu không gian | GeoPandas, Shapely 2, Rasterio, OSMnx 2 | Bản cài pip đã kèm GDAL |
| Lưu dữ liệu tĩnh | File Parquet và GeoParquet | Chép file là triển khai xong |
| Lưu báo cáo người dùng | SQLite; không lưu tọa độ; xóa sau 24 giờ | Đủ cho một máy chủ; ít dữ liệu cá nhân nhất có thể |
| Đơn vị | Hai cấp: **đoạn** khoảng 200 m nằm trong **tuyến** khoảng 1 km | Ngập thường chỉ xảy ra trên 100–200 m; tuyến là cấp lùi |
| Điểm của mỗi đoạn | Điểm lịch sử; mô hình chỉ thêm hai bậc thấp hơn cho nơi chưa có lịch sử | Ghi nhận thật đáng tin hơn mô hình |
| Ba mức nguy cơ | Hai ngưỡng cố định trên chỉ số nguy cơ: 0,35 và 0,60 | Ngưỡng theo phân vị bị hỏng khi phần lớn đoạn có điểm 0 |
| Thang mưa và triều | Đường cong logistic, rồi neo lại theo tần suất: 10% số ngày mạnh nhất là "đáng kể", 3% là "lớn" | Đầu ra thô của đường cong không có nghĩa cố định |
| Mô hình 1 | LightGBM có ràng buộc đơn điệu, ở cấp tuyến; giới hạn một ngày công | Chỉ làm khi lõi đã chạy |
| Mưa | Open-Meteo cho cả lúc học lẫn lúc chạy | Cùng một nguồn ở hai phía |
| Triều | Triều thiên văn Vũng Tàu (`utide`) | Tính trước được cho mọi thời điểm |
| Địa hình | FABDEM 30 m | Một file 1,7 GB phủ cả hai thành phố |
| Máy chủ | FastAPI + Uvicorn | Gọi thẳng được hàm của phần mô hình |
| Giao diện | React + Vite + TypeScript, Tailwind, MapLibre GL JS trên style của Goong | Đây là cách Goong hướng dẫn chính thức |
| Dịch vụ Goong | Map, Autocomplete V2, Place Detail V2, Direction V2 | Đã thử bằng khóa thật ngày 04/10 (mục 7.3) |
| Tìm đường tránh ngập | Thuật toán riêng trên mạng đường OpenStreetMap; Goong cho lộ trình nhanh nhất để so sánh | Goong chỉ trả 1 hoặc 2 lộ trình cho mỗi cặp điểm, nên không đủ để chọn đường tránh |
| Định vị tên đường | Khớp tên trực tiếp với các đoạn trong `units.parquet` | Forward Geocode của Goong trả cùng một kết quả sai cho ba tên đường khác nhau |
| Giao thông đông đúc | **Có dùng (đổi ngày 04/10, mục 18.3 điểm 17):** TomTom Traffic Flow khi có khóa, bảng điển hình theo giờ khi không có, cộng hệ số "ngập làm chậm" | Thời gian tới nơi không hợp lý nếu không tính mức độ đông của đường. Google Maps bị loại vì điều khoản cấm dùng với bản đồ khác |
| Công cụ thử | "Bàn thử": kịch bản giả lập, thời điểm quá khứ, ngày có ghi nhận (mục 4.8) | Nhóm phải tự thử được khi trời khô |
| Triển khai | Một container Docker trên một máy AWS EC2 `t3.small` | Nhóm có 100 đô credit AWS |
| Kiểm thử | pytest; vitest cho hàm thuần phía web | — |

Đã cân nhắc và loại: PostgreSQL + PostGIS (để sau hackathon), vector tiles, mạng nơ-ron và LarNO, mô phỏng thủy lực, ngưỡng theo phân vị, Mô hình 1 cho ra điểm liên tục.

## 2. Kiến trúc

```
   NGƯỜI DỮ LIỆU                     NGƯỜI AI                      KỸ SƯ PHẦN MỀM
   OpenStreetMap, IRD, Đà Nẵng,      Điểm lịch sử, Mô hình 2,      FastAPI + SQLite
   Open-Meteo, FABDEM, WorldCover    triều, tính nguy cơ,          React + MapLibre + Goong
                                     phát lại, Mô hình 1
         │                                  │                             │
         ▼                                  ▼                             │
   units.parquet ────────────────►  scores.parquet                        │
   observations.parquet ─────────►  trigger.json                          │
   obs_units.parquet ────────────►  model_choice.json                     │
   rain_daily.parquet ───────────►  tide_coef.joblib                      │
         │                                  │                             │
         └── mưa dự báo ──► tác vụ mỗi giờ (người AI) ──► risk.parquet ──►│
                             bản phát lại ─────────────► replay/*.parquet │
                                                                          ▼
                             apply_evidence() ──────────────► /api/risk, /api/route,
                                                              /api/reports, /api/units
```

## 3. Cấu trúc thư mục

```
src/floodrisk/
├── config.py            # thành phố, hằng số, ngưỡng, đường dẫn file
├── contracts.py         # kiểm tra định dạng các bảng
├── samples.py           # dữ liệu mẫu cho phần web
├── data/                # NGƯỜI DỮ LIỆU
│   ├── loggers.py       # ghi mưa trạm đo và dự báo mỗi giờ
│   ├── observations.py  # bảng ghi nhận ngập, bảng gán ghi nhận vào đoạn
│   ├── units.py         # đoạn và tuyến từ OpenStreetMap
│   ├── cells.py         # ô lưới mưa
│   ├── rain.py          # mưa Open-Meteo: lịch sử và dự báo
│   ├── terrain.py       # đặc điểm địa hình (chỉ khi làm Mô hình 1)
│   └── features.py      # ghi units.parquet
├── model/               # NGƯỜI AI
│   ├── evidence.py      # cập nhật theo báo cáo
│   ├── combine.py       # ghép, neo thang T, chia mức
│   ├── history.py       # điểm lịch sử
│   ├── trigger.py       # Mô hình 2
│   ├── tide.py          # triều thiên văn
│   ├── scoring.py       # scores.parquet, nguy cơ theo giờ
│   ├── scenarios.py     # các bộ tạo kịch bản: ngày có ghi nhận, thời điểm quá khứ, giả lập
│   ├── evaluate.py, susceptibility.py, run_eval.py   # Mô hình 1 và cổng kiểm chứng
│   └── run_checks.py    # hai bảng kiểm chứng trên dữ liệu 2025–2026
├── jobs/hourly.py       # NGƯỜI AI: tác vụ mỗi giờ
└── api/                 # KỸ SƯ PHẦN MỀM; có graphroute.py là thuật toán tìm đường riêng
tests/{data,model,api}/
web/                     # KỸ SƯ PHẦN MỀM
reports/                 # kết quả kiểm chứng (markdown)
data/                    # KHÔNG commit: raw/, processed/{hcm,danang}/, sample/
```

## 4. Mô hình

### 4.1 Hai cấp đơn vị

- **Đoạn** là đơn vị nhỏ nhất. Cách tạo, áp dụng đúng một quy tắc: mỗi cạnh OpenStreetMap (khúc đường giữa hai giao lộ) được cắt theo chiều dài thành các mảnh bằng nhau, mỗi mảnh không dài quá 200 m; mỗi mảnh thuộc về ô lưới 200 m chứa điểm giữa của nó; các mảnh cùng tên đường trong cùng một ô gộp thành một đoạn.
- **Tuyến** là nhóm các đoạn cùng tên đường trong cùng một ô lưới 1 km. Mỗi đoạn mang mã tuyến trong cột `parent_id`.
- Trong mã nguồn, đoạn là một dòng của `units.parquet` và mang `unit_id`.
- Chỉ lấy đường có tên thuộc mạng đường xe chạy (`network_type="drive"` của OSMnx). Tên được chuẩn hóa: chữ thường, bỏ dấu, bỏ tiền tố "đường", "phố".
- Giữ hai thẻ `bridge` và `tunnel` của OpenStreetMap. Đoạn có trên một nửa chiều dài là cầu mang `is_bridge = true`: cầu không bao giờ nhận điểm từ Mô hình 1 và không tham gia học hay kiểm chứng. Lý do là cầu vượt sông nằm sát nước và có cao độ nền thấp trong DEM, nên mô hình sẽ xếp nó là chỗ dễ ngập nhất.

**Ví dụ.** Một con đường dài khoảng 3 km chạy qua ba ô lưới 1 km thành ba tuyến, mỗi tuyến gồm khoảng năm đoạn:

```
        tuyến 1               tuyến 2               tuyến 3
  ┌─────────────────────┬─────────────────────┬─────────────────────┐
  │ ━━━ ━━━ ━━━ ━━━ ━━━ │ ━━━ ━━━ ▓▓▓ ━━━ ━━━ │ ━━━ ━━━ ━━━ ━━━ ━━━ │
  │  5 đoạn, mỗi đoạn   │  đoạn ▓ có người    │                     │
  │  khoảng 200 m       │  báo ngập tại chỗ   │                     │
  └─────────────────────┴─────────────────────┴─────────────────────┘
          1 km
```

### 4.2 Gán ghi nhận ngập vào đoạn

Mỗi ghi nhận có một mức chính xác vị trí trong cột `loc_precision`. Mức này quyết định ghi nhận được gán cho bao nhiêu đoạn.

| Mức | Nghĩa | Nguồn | Gán cho |
|---|---|---|---|
| `high` | Sai số dưới 100 m | IRD ghi "High"; Đà Nẵng loại `point` | Một đoạn gần nhất trong 100 m |
| `medium` | Sai số 100–500 m | IRD ghi "Medium"; Đà Nẵng loại `street` | Các đoạn liền nhau cùng tên đường, trong 500 m quanh điểm |
| `low` | Trên 500 m, có tên đường | IRD ghi "Low" kèm tên đường; 34 tuyến của Sở Xây dựng | Các đoạn liền nhau cùng tên đường, trong 1.500 m quanh điểm |
| `area` | Chỉ nêu khu dân cư, phường, xã | IRD loại "Area point", "Ward point" | Không gán vào đường nào; chỉ dùng để biết ngày đó có ngập |

Quy tắc gán:

- **Đoạn neo:** nếu ghi nhận có tên đường thì lấy đoạn cùng tên gần nhất trong 300 m; nếu không thì lấy đoạn gần nhất trong 100 m. Không có đoạn neo thì ghi nhận không được gán.
- **Liền nhau:** từ đoạn neo, lan sang các đoạn cùng tên mà hình học cách nhau không quá 30 m, không vượt khoảng cách giới hạn. Điều này tránh nhầm hai con đường trùng tên như "Đường số 1".
- **Kết quả** là bảng `obs_units.parquet`: mỗi dòng là một cặp (ghi nhận, đoạn), kèm `exact` (đúng khi mức là `high`) và `spread_m` (tổng chiều dài các đoạn ghi nhận đó được gán).
- **Sau mỗi lần chạy phải in ra:** bao nhiêu ghi nhận được gán, bao nhiêu nhờ khớp tên, và 20 tên đường không khớp nhiều nhất.

Bộ IRD ghi sai chính tả ở vài dòng ("Hugh", "Hgh", khoảng trắng thừa); bộ đọc phải chuẩn hóa trước khi so.

### 4.3 Điểm lịch sử

Tính cho từng đoạn và từng nguyên nhân (mưa, triều) từ `obs_units`. Ghi nhận có nguyên nhân "kết hợp" tính cho cả hai.

| Điều kiện trên các ghi nhận đã gán vào đoạn | `h` |
|---|---|
| Có ghi nhận ở từ 3 năm khác nhau, hoặc có ghi nhận từ danh sách chính thức | 0,95 |
| Có ít nhất một ghi nhận từ năm 2016 | 0,85 |
| Chỉ có ghi nhận trước 2016 | 0,70 |
| Không có | 0 |

Kèm theo mỗi đoạn:

- **`exact`:** đúng nếu đoạn có ít nhất một ghi nhận `high`.
- **`loc_weight`:** 1 nếu `exact`; nếu không thì `min(1, 250 / spread_m)` với `spread_m` nhỏ nhất trong các ghi nhận của đoạn. Một con đường 3 km chỉ được biết là "có ngập ở đâu đó" sẽ có trọng số khoảng 0,08 trên mỗi mét. Trọng số này chỉ dùng khi chấm điểm lộ trình (mục 7.2); nó không đổi màu trên bản đồ.
- **`history`**, **`max_depth_cm`**, **`last_year`**: số ghi nhận, độ sâu lớn nhất và năm gần nhất, để hiện trong thẻ giải thích.

Ba con số 0,95, 0,85, 0,70 là giá trị khởi đầu do tôi đặt, chưa được hiệu chỉnh bằng dữ liệu.

### 4.4 Mô hình 2 và thang mưa, triều

**Đường cong thô.** `LogisticRegression(class_weight="balanced")`, khớp riêng cho từng thành phố.

- **Mưa:** hai biến `log1p(r3max)` và `log1p(r24)`, theo từng ô lưới mưa 0,1° của Open-Meteo. Lúc học, `r3max` là tổng mưa 3 giờ lớn nhất trong ngày và `r24` là tổng mưa ngày. Lúc chạy, `r3max` là tổng 3 giờ kết thúc tại mốc giờ đang xét và `r24` là tổng 24 giờ. Mẫu dương là cặp (ô lưới, ngày) có ghi nhận ngập do mưa; mẫu âm là mọi cặp còn lại từ 01/01/2016.
- **Triều:** một biến, đỉnh triều thiên văn Vũng Tàu (mét, so với mực trung bình). Lúc học lấy đỉnh trong ngày; lúc chạy lấy đỉnh trong 4 giờ trước mốc giờ đang xét.
- **Một chiều:** nếu có hệ số âm thì loại đúng một biến có hệ số âm nhất rồi khớp lại. Nếu không còn biến nào có hệ số dương thì dùng đường cong mặc định và ghi `"fitted": false`.
- **Đường cong mặc định cho mưa:** `T = sigmoid(−9,06 + 2,44 × log1p(r3max))`, tức 0,5 ở 40 mm trong 3 giờ và khoảng 0,9 ở 100 mm. Đây là giá trị do tôi đặt, không học từ dữ liệu. Mốc ngày 3 dùng đường cong này.

**Neo lại theo tần suất.** Vì `class_weight="balanced"` làm lệch hệ số chặn, giá trị thô của `T` không có nghĩa cố định. Nó được neo như sau:

- `t_med` là phân vị 90 của `T` thô trên mọi cặp (ô lưới, ngày) từ 2016 tới ngày chốt; `t_high` là phân vị 97. Với triều thì tính trên mọi ngày.
- `T` đã neo là hàm tuyến tính từng khúc đi qua bốn điểm: (0 → 0), (`t_med` → 0,45), (`t_high` → 0,75), (1 → 1).
- Nghĩa: 0,45 là "mưa hoặc triều thuộc 10% ngày mạnh nhất", gọi là **đáng kể**; 0,75 là "thuộc 3% ngày mạnh nhất", gọi là **lớn**.
- `trigger.json` ghi cả hai điểm cắt và lượng mưa 3 giờ tương ứng tính bằng mm, để người đọc kiểm tra bằng mắt.

Hai tần suất 10% và 3% là giá trị khởi đầu do tôi đặt.

### 4.5 Ghép và ba mức

```
R = 1 − (1 − s_rain × T_mưa) × (1 − s_tide × T_triều)
```

`R` là **chỉ số nguy cơ** từ 0 đến 1, không phải xác suất. Hai ngưỡng cố định: `R ≥ 0,35` là mức **vừa**, `R ≥ 0,60` là mức **cao**.

Bảng dưới cho thấy mỗi loại đoạn lên được mức nào, khi chỉ có một nguyên nhân:

| Điểm của đoạn | Mưa hoặc triều "đáng kể" (0,45) | "Lớn" (0,75) | Lên được mức cao khi |
|---|---|---|---|
| 0,95 (ngập nhiều năm, hoặc chính thức) | 0,43, vừa | 0,71, cao | `T` từ 0,63 |
| 0,85 (có ghi nhận từ 2016) | 0,38, vừa | 0,64, cao | `T` từ 0,71 |
| 0,70 (chỉ có ghi nhận cũ) | 0,32, thấp | 0,53, vừa | `T` từ 0,86 |
| 0,55 (mô hình, 3% tuyến đầu) | 0,25, thấp | 0,41, vừa | Không bao giờ |
| 0,50 (mô hình, 10% tuyến đầu) | 0,23, thấp | 0,38, vừa | Không bao giờ |

Mô hình tự nó không tạo được mức cao. Chỉ lịch sử hoặc báo cáo trực tiếp mới làm được.

### 4.6 Mô hình 1 (làm sau lõi, giới hạn một ngày công)

**Chỉ làm khi `units.parquet` có đặc điểm địa hình của cả hai thành phố được giao đúng hạn hết ngày 4.** Nếu trễ thì bỏ hẳn, đặt `"rain": "none"`, `"tide": "none"`, và bài thuyết trình dẫn kết quả phép thử 28/09.

- **Đơn vị học và đơn vị công bố đều là tuyến**, không phải đoạn. Đặc điểm của tuyến gộp từ các đoạn không phải cầu: `elev_min`, `tpi_300`, `tpi_1000`, `dist_water_m` lấy nhỏ nhất; `elev_mean`, `built_frac_200` lấy trung bình; `road_rank` lấy lớn nhất; `length_m` lấy tổng.
- **Biến nhiễu:** `road_rank`, `length_m`, `built_frac_200`. Mô hình được học chúng vì chúng dự đoán việc *được báo chí ghi nhận*, nhưng lúc tính điểm thì cố định ở trung vị.
- **Ràng buộc đơn điệu:** mô hình mưa ép `tpi_300` và `tpi_1000` giảm; mô hình triều ép thêm `elev_min` và `dist_water_m` giảm. Các biến khác không ràng buộc.
- **Thuật toán:** `LGBMClassifier`, 300 cây, `learning_rate=0.03`, `num_leaves=8`, `max_depth=3`, `min_child_samples=20`, `subsample=0.8`, `colsample_bytree=0.8`, `reg_lambda=5`.
- **Nhãn:** tuyến có ít nhất một đoạn được gán ghi nhận với nguyên nhân tương ứng.
- **Tập đánh giá và tập công bố là một:** các tuyến có `built_frac_200` từ 0,5 trở lên.
- **Đầu ra:** nếu qua cổng (mục 4.9), tuyến thuộc 3% điểm cao nhất của tập đó trong thành phố nhận 0,55; thuộc 10% nhận 0,50; còn lại 0. Mọi đoạn không phải cầu của tuyến nhận điểm đó, với `loc_weight = min(1, 250 / chiều dài tuyến)`.
- **Điểm tổng hợp:** `s = max(h, điểm mô hình)`. Cột `basis` ghi `"history"` nếu `h > 0`, `"model"` nếu chỉ có điểm mô hình, `"none"` nếu cả hai bằng 0.

### 4.7 Cập nhật theo bằng chứng

- Mỗi người chỉ tính báo cáo mới nhất của mình cho mỗi đoạn.
- Trọng số báo cáo giảm một nửa sau mỗi 30 phút; quá 180 phút thì bỏ.
- Báo cáo "ngập" cộng `trọng số × ln(3)` vào log-odds của `R`; "không ngập" trừ đi chừng đó. Nguồn chính thức dùng `ln(10)`.
- Số người đã báo là số người có báo cáo "ngập" trong 30 phút qua. Mức được báo là mức nhiều người chọn nhất; hòa thì lấy mức cao hơn.
- Báo "ngập vừa" đẩy đoạn lên ít nhất mức vừa; báo "ngập cao" đẩy lên mức cao.
- Bằng chứng chỉ áp dụng cho giờ hiện tại.
- **Quyền riêng tư:** máy chủ chỉ lưu mã đoạn, không lưu tọa độ người báo. Báo cáo bị xóa sau 24 giờ; trước khi xóa, chúng được cộng vào bảng tổng hợp theo (đoạn, giờ, trạng thái, số lượng) không kèm mã người báo.

### 4.8 Phát lại và bàn thử

Đây vừa là kịch bản trình diễn chính, vừa là công cụ để nhóm tự thử. Mọi loại dưới đây đi qua đúng hàm `score_units` của bản chạy thật; chỉ khác ở chỗ số liệu mưa và triều lấy từ đâu.

**Một kịch bản** là một bảng nguy cơ ghi trong `replay/{mã}.parquet`, cùng định dạng với `risk.parquet`, kèm một dòng trong `replay/index.json` ghi `id`, `label`, `kind`, `time`. Giao diện chọn "Trực tiếp" hoặc một kịch bản.

| `kind` | Số liệu đưa vào | Chứng minh được gì | Không chứng minh được gì |
|---|---|---|---|
| `recorded-day` | Mưa và triều thật của một ngày có ghi nhận ngập; các đoạn có ghi nhận `high` hôm đó được đánh dấu `recorded` | So được dự báo với điều đã xảy ra. Đây là bằng chứng duy nhất rằng hệ thống đúng với thực tế | Tính tổng quát: chỉ có vài chục ngày |
| `past-moment` | Mưa thật theo giờ của một thời điểm bất kỳ trong quá khứ, lấy từ Open-Meteo lúc tạo kịch bản; triều thiên văn của giờ đó | Đường ống chạy được trên số liệu thật ở độ mịn theo giờ | Đúng hay sai, nếu ngày đó không có ghi nhận |
| `snapshot` | Đúng bảng mưa mà tác vụ mỗi giờ đã dùng ở một giờ trước đó (tác vụ lưu lại đầu vào của nó trong 14 ngày) | Tái hiện được chính xác điều hệ thống đã thấy; so được dự báo hôm qua với điều xảy ra sau đó | — |
| `synthetic` | Số tự đặt hoặc ngẫu nhiên: lượng mưa 3 giờ, mức triều, mưa cục bộ ở vài ô lưới, một số báo cáo người dùng ngẫu nhiên | Hệ thống phản ứng đúng: mưa tăng thì nguy cơ không giảm, chỉ vùng có mưa đổi màu, báo cáo nâng mức, lộ trình đổi hướng | **Không chứng minh được mô hình đúng với thực tế.** Số ngẫu nhiên chỉ cho thấy hệ thống chạy và phản ứng hợp lý |

**Quy tắc bắt buộc:**

- Kịch bản `synthetic` luôn hiện dải chữ "GIẢ LẬP, không phải dữ liệu thật" trên bản đồ, và không được dùng làm bằng chứng về độ chính xác trong bài thuyết trình. Đề bài cho phép dữ liệu giả lập miễn là ghi rõ.
- Để nói "mô hình hoạt động trên dữ liệu thật", chỉ dùng kịch bản `recorded-day` của các ngày từ 2025 trở đi, là những ngày mô hình chưa từng thấy lúc học, cùng với hai bảng kiểm chứng ở mục 4.9.
- **Chọn ngày `recorded-day`:** người AI in bảng các ngày có ghi nhận kèm `T` đã neo và số ghi nhận, rồi chọn 2–3 ngày có cả `T` từ 0,45 trở lên lẫn nhiều ghi nhận. Nếu mưa dạng lưới bỏ sót một trận thì ngày đó không dùng được; phải kiểm tra điều này trước mốc ngày 3.
- Đoạn `recorded` vẽ nét liền mức cao với nguồn "ghi nhận ngày đó".
- Báo cáo người dùng vẫn hoạt động trong mọi kịch bản để trình diễn, và mang nhãn "báo cáo thử".

**Bàn thử trên giao diện** (chỉ bật khi đặt biến `FLOODRISK_TEST_TOOLS=1`): một bảng nhỏ để tạo kịch bản mà không cần dòng lệnh.

- Giả lập: thanh kéo lượng mưa 3 giờ (0–150 mm), ô chọn mức triều (không, đáng kể, lớn), ô chọn "mưa cục bộ ngẫu nhiên" kèm hạt giống, số báo cáo ngẫu nhiên.
- Thời điểm quá khứ: ô chọn ngày và giờ.

**Sáu kịch bản thử chuẩn**, chạy lại sau mỗi lần gộp code:

| Kịch bản | Kết quả phải thấy |
|---|---|
| Trời khô, triều thấp | Mọi đoạn mức thấp; lộ trình đề xuất trùng lộ trình nhanh nhất |
| Mưa 30 mm trong 3 giờ, cả thành phố | Đoạn có lịch sử ngập nhiều năm lên mức vừa; đoạn không có lịch sử vẫn thấp |
| Mưa 80 mm trong 3 giờ, cả thành phố | Đoạn có lịch sử lên mức cao; lộ trình qua đó đổi hướng |
| Mưa 80 mm chỉ ở một ô lưới | Chỉ các đoạn trong ô đó đổi màu |
| Triều lớn, không mưa (TP.HCM) | Chỉ đoạn có lịch sử ngập triều đổi màu |
| Mưa 10 mm và bốn báo cáo "ngập cao" trên một đoạn | Đoạn đó lên mức cao, nét liền, ghi "4 người đã báo" |

Sáu kết quả này cũng được viết thành kiểm thử tự động, cùng một bất biến chung: tăng lượng mưa không bao giờ làm giảm mức của bất kỳ đoạn nào.

### 4.9 Kiểm chứng

Mọi phép kiểm dưới đây dùng mô hình và điểm lịch sử chỉ học từ dữ liệu trước 01/01/2025, kể cả việc chọn có dùng Mô hình 1 hay không.

**Cổng cho Mô hình 1.**

- Mưa: học TP.HCM kiểm Đà Nẵng, rồi đảo lại. Triều: chỉ trong TP.HCM, giữ lại từng khối 5 km.
- Chỉ số: trong 10% tuyến điểm cao nhất của tập đánh giá, có bao nhiêu phần tuyến dương.
- Mốc so sánh: xếp hạng theo cao độ thấp, theo độ trũng, theo gần nước, và theo tỉ lệ xây dựng.
- Khoảng dao động: bootstrap theo khối 3 km (không theo từng tuyến, vì ghi nhận tụm theo khu), 1.000 lần; hiệu số giữa mô hình và mốc tốt nhất tính trong cùng một lần lấy mẫu.
- Qua khi cận dưới 95% của hiệu số lớn hơn 0, ở cả hai chiều với mưa.
- Kết quả ghi vào `model_choice.json`: `"model"` hoặc `"none"` cho từng nguyên nhân.

**Bảng điểm vận hành của Mô hình 2.** Cho từng thành phố và từng nguyên nhân, trên mọi ngày từ 01/01/2025 tới ngày ghi nhận cuối của nguồn đó:

- số ngày hệ thống báo ở mức đáng kể, và ở mức lớn;
- trong đó bao nhiêu ngày có ghi nhận ngập (trúng), bao nhiêu ngày có ghi nhận mà không báo (trượt);
- trong các ngày báo mà không có ghi nhận, bao nhiêu ngày có mưa từ 10 mm;
- cùng các số đó cho quy tắc đơn giản "tổng mưa ngày từ 50 mm".

Báo số đếm, không báo tỉ lệ, vì số ngày ít.

**Lịch sử phủ được bao nhiêu, mô hình thêm được gì.** Trên các ghi nhận 2025–2026 đã gán vào đoạn, tính theo từng ghi nhận:

- bao nhiêu phần rơi vào đoạn đã có lịch sử trước 2025. Đây là trần của cách "chỉ dùng danh sách điểm ngập cũ";
- trong phần nằm ngoài, bao nhiêu rơi vào tuyến thuộc bậc 3% và 10% của Mô hình 1. Đây là phép thử thật cho Mô hình 1.

**Giới hạn phải nêu kèm mọi con số:** đoạn không có ghi nhận chưa chắc là không ngập; ghi nhận thiên về đường lớn được báo chí đưa tin; 392 trong 633 ghi nhận Đà Nẵng thuộc một ngày.

### 4.10 Hai ghi đè tùy chọn, làm sau khi lõi đã triển khai

Cả hai chỉ được **nâng** `T`, không bao giờ hạ, và bản đồ phải ghi rõ nguồn.

| Ghi đè | Quy tắc | Ghi trên bản đồ |
|---|---|---|
| Trạm đo mưa VRain | Trạm trong 5 km đo được từ 30 mm trong 3 giờ thì `T_mưa` của các đoạn quanh trạm không thấp hơn 0,45; từ 50 mm thì không thấp hơn 0,75. Hết hiệu lực sau 3 giờ. Thiếu ảnh chụp thì không ghi đè. Không đi qua đường cong của Mô hình 2 | "theo trạm đo" |
| Bản tin triều của Đài KTTV Nam Bộ cho trạm Phú An | Mực nước dự báo từ 1,40 m (báo động 1) thì `T_triều` không thấp hơn 0,45; từ 1,60 m (báo động 3) thì không thấp hơn 0,75. Nhập tay mỗi sáng | "theo bản tin" |

Khi bật ghi đè trạm đo, phải báo thêm số ngày khô bị báo nhầm. Các ngưỡng 30 mm, 50 mm là giá trị do tôi đặt; ba cấp báo động là số chính thức theo QĐ 05/2020/QĐ-TTg.

## 5. Hợp đồng dữ liệu

Mọi file nằm dưới thư mục dữ liệu (`data/` mặc định, đổi bằng biến `FLOODRISK_DATA`). Đường dẫn lấy qua hàm trong `config.py`.

| File | Ai ghi | Ai đọc | Cột |
|---|---|---|---|
| `processed/{city}/units.parquet` | Dữ liệu | AI, web | `unit_id`, `parent_id`, `city`, `name`, `road_class`, `road_rank`, `length_m`, `is_bridge`, `is_tunnel`, `rain_cell`, `geometry` (EPSG:4326); thêm `elev_min`, `elev_mean`, `tpi_300`, `tpi_1000`, `dist_water_m`, `built_frac_200` (được phép rỗng cho tới khi có địa hình) |
| `processed/{city}/observations.parquet` | Dữ liệu | AI | `obs_id`, `city`, `source`, `provenance`, `date`, `year`, `hour`, `lon`, `lat`, `loc_precision`, `flooded`, `depth_cm`, `depth_class`, `cause`, `street_name`, `unit_id` (đoạn neo), `evidence_url` |
| `processed/{city}/obs_units.parquet` | Dữ liệu | AI | `obs_id`, `unit_id`, `exact`, `spread_m` |
| `processed/{city}/rain_cells.parquet` | Dữ liệu | AI | `city`, `cell_id`, `lon`, `lat` |
| `processed/{city}/rain_daily.parquet` | Dữ liệu | AI | `cell_id`, `date`, `r3max`, `r24` |
| `processed/tide_coef.joblib`, `processed/tide_daily.parquet` | AI | AI | Hệ số `utide`; `date`, `tide_max` |
| `processed/{city}/scores.parquet` | AI | Tác vụ giờ, web | `unit_id`, `s_rain`, `s_tide`, `basis`, `exact`, `loc_weight`, `history`, `max_depth_cm`, `last_year` |
| `processed/{city}/model/trigger.json` | AI | Tác vụ giờ | Cho `rain` và `tide`: `features`, `intercept`, `coef`, `fitted`, `cuts` (`medium`, `high`), `cut_mm` |
| `processed/model_choice.json` | AI | AI, web | `{"rain": "model" / "none", "tide": "model" / "none", "validated": [danh sách thành phố]}` |
| `processed/{city}/risk.parquet` | Tác vụ giờ | Web | `unit_id`, `hour_offset` (0, 1, 2), `risk`, `level` (0, 1, 2), `t_rain`, `t_tide`, `computed_at` |
| `processed/{city}/replay/{mã}.parquet`, `replay/index.json` | AI | Web | Như `risk.parquet`, thêm `recorded`, `reporters`, `reported_level`; `index.json` liệt kê `id`, `label`, `kind`, `time`, `recorded_count` |
| `processed/{city}/graph_nodes.parquet` | Dữ liệu | Web | `node_id`, `lon`, `lat` |
| `processed/{city}/graph_edges.parquet` | Dữ liệu | Web | `edge_id`, `u`, `v` (mỗi chiều đi được là một dòng), `length_m`, `highway`, `geometry` |
| `processed/{city}/edge_units.parquet` | Dữ liệu | Web | `edge_id`, `unit_id`, `length_m`: phần của cạnh thuộc về đoạn nào. Cạnh không tên không có dòng nào |
| `raw/inputs/{city}/{YYYYMMDDHH}.parquet` | Tác vụ giờ | AI | Bảng mưa mà tác vụ đã dùng ở giờ đó; giữ 14 ngày |
| `raw/live/{nguồn}/*.jsonl` | Bộ ghi | AI (sau này) | Mỗi dòng: `fetched_at`, `payload` |
| `reports.sqlite` | Web | Web | Bảng `reports` (không có tọa độ) và `report_hours` |

Giá trị quy ước:

- `provenance`: 1 quan sát chính thức, 2 người dùng báo, 3 AI trích từ báo chí, 4 mô hình dự báo, 5 giả lập.
- `cause`: `rain`, `tide`, `combined`, `unknown`.
- `loc_precision`: `high`, `medium`, `low`, `area`.
- `depth_class`: 1 dưới 10 cm, 2 từ 10 đến 30 cm, 3 trên 30 cm, rỗng nếu không rõ.
- `level`: 0 thấp, 1 vừa, 2 cao. Hai ngưỡng 0,35 và 0,60 là hằng số trong `config.py`.
- `basis`: `history`, `model`, `none`.
- Thời gian trong các bảng là giờ Việt Nam, không kèm múi giờ. Báo cáo người dùng lưu dạng giây Unix.
- Tọa độ theo thứ tự (kinh độ, vĩ độ), EPSG:4326.

**Hợp đồng này được đóng băng.** Muốn đổi cột hay tên file thì cả ba người phải đồng ý, và sửa tài liệu này trước khi sửa code.

## 6. Hàm giao giữa ba người

```python
# NGƯỜI DỮ LIỆU viết, NGƯỜI AI gọi
# floodrisk/data/rain.py
def fetch_forecast(city: str, cells: pd.DataFrame) -> pd.DataFrame   # cell_id, time, precip_mm
def fetch_range(city: str, cells: pd.DataFrame, start, end) -> pd.DataFrame   # mưa theo giờ của một khoảng thời gian đã qua
# floodrisk/data/cells.py
def nearest_cell(lons, lats, cells: pd.DataFrame) -> np.ndarray
# floodrisk/data/units.py
def norm_name(name: str) -> str

# NGƯỜI AI viết, KỸ SƯ PHẦN MỀM gọi
# floodrisk/model/evidence.py
@dataclass(frozen=True)
class Report:
    reporter: str
    status: str                  # "light" | "medium" | "high" | "clear"
    at: datetime                 # có múi giờ, UTC
    official: bool = False

@dataclass(frozen=True)
class EvidenceResult:
    risk: float
    reporters: int
    reported_level: int | None   # 1 nhẹ, 2 vừa, 3 cao

def apply_evidence(prior: float, reports: list[Report], now: datetime) -> EvidenceResult

# floodrisk/model/combine.py
def to_level(risk: np.ndarray) -> np.ndarray                  # 0, 1, 2 theo hai ngưỡng trong config
def calibrate(t_raw: np.ndarray, cuts: dict) -> np.ndarray    # neo thang T (mục 4.4)

# floodrisk/model/scoring.py  (người AI viết và tự gọi trong tác vụ mỗi giờ)
def score_units(
    scores: pd.DataFrame,        # unit_id, rain_cell, s_rain, s_tide
    rain_hourly: pd.DataFrame,   # cell_id, time, precip_mm; phủ từ now-24h tới now+2h
    trigger: dict,               # nội dung trigger.json
    now: pd.Timestamp,           # giờ Việt Nam, làm tròn xuống giờ
    t_tide_fn: Callable[[pd.Timestamp], float] | None = None,   # trả T_triều đã neo
    hours: tuple[int, ...] = (0, 1, 2),
) -> pd.DataFrame                # unit_id, hour_offset, risk, level, t_rain, t_tide
```

## 7. API máy chủ

### 7.1 Endpoint

| Endpoint | Tham số | Trả về |
|---|---|---|
| `GET /api/health` | — | `{"ok": true}` |
| `GET /api/cities` | — | `key`, `name`, `center`, `bbox`, `has_tide`, `validated` (lấy từ `model_choice.json`) |
| `GET /api/replays` | `city` | Danh sách kịch bản: `id`, `label`, `kind`, `time`, `recorded_count` |
| `GET /api/risk` | `city`, `bbox=w,s,e,n`, `hour` (0–2), `min_level` (mặc định 1), `replay` (tùy chọn) | GeoJSON các đoạn; mỗi đoạn có `unit_id`, `name`, `level`, `risk`, `source`, `exact`, `reporters`, `reported_level`, `history`; kèm `computed_at`, `stale`, `truncated` |
| `GET /api/units/{unit_id}` | `city`, `replay` | Thẻ giải thích: tên, mức, nguồn, các ghi nhận lịch sử (năm, nguyên nhân, độ sâu, đường dẫn), độ sâu lớn nhất, mức mưa và triều hiện tại bằng chữ, số người đã báo |
| `POST /api/reports` | `city`, `lat`, `lon`, `status`, `reporter` | Đoạn được gán và nguy cơ sau cập nhật; 404 nếu không có đoạn nào trong 60 m. Tọa độ chỉ dùng để tìm đoạn, không được lưu |
| `GET /api/route` | `city`, `origin=lat,lon`, `destination=lat,lon`, `vehicle`, `replay` | Lộ trình nhanh nhất của Goong và lộ trình tránh ngập của thuật toán riêng, đều đã chấm điểm; một lộ trình có `recommended: true` |
| `POST /api/admin/scenarios` | `city`, `kind` (`synthetic` hoặc `past-moment`) và tham số của loại đó | Tạo một kịch bản và trả `id`. Chỉ tồn tại khi `FLOODRISK_TEST_TOOLS=1` |
| `POST /api/score-route` | `city`, `coordinates` (danh sách `[lon, lat]`), `vehicle` | Điểm nguy cơ của một lộ trình bất kỳ. Đây là điểm tích hợp cho ứng dụng dẫn đường khác |
| `GET /api/alerts` | `city`, `lat`, `lon`, `radius_m`, `replay` | Với mỗi giờ 0, 1, 2: mức cao nhất, số đoạn mức cao và vừa, 5 đoạn nguy cơ nhất |
| `GET /api/places/autocomplete`, `/api/places/detail` | `q`, `lat`, `lon`; `place_id` | Gợi ý và chi tiết địa điểm từ Goong |

Giá trị `source` và cách vẽ:

| `source` | Nghĩa | Nét vẽ |
|---|---|---|
| `report` | Có người dùng báo trong giờ này | Liền |
| `official` | Nguồn chính thức, hoặc ghi nhận của ngày đang phát lại | Liền |
| `history` | Dự báo dựa trên lịch sử ngập của đoạn | Đứt; nhạt hơn nếu `exact` sai, kèm chữ "chưa rõ đoạn nào" |
| `model` | Dự báo chỉ dựa trên Mô hình 1 | Chấm |

### 7.2 Tìm đường tránh ngập

Goong chỉ trả 1 hoặc 2 lộ trình cho mỗi cặp điểm (mục 7.3), nên việc tránh ngập do thuật toán riêng làm. Goong vẫn cho lộ trình nhanh nhất để so sánh.

**Chấm điểm một lộ trình bất kỳ** (dùng cho lộ trình của Goong và cho `POST /api/score-route`):

- Một đoạn được tính khi lộ trình chạy dọc nó: phần chồng với hành lang 15 m quanh lộ trình dài từ 50 m, hoặc từ 30% chiều dài đoạn.
- `exposure` cộng dồn `chiều dài chồng × R × loc_weight × hệ số xe`.
- `flooded_m` cộng dồn `chiều dài chồng × loc_weight × hệ số xe` trên các đoạn mức cao.
- **Hệ số xe:** xe máy luôn là 1. Ô tô là 0,5 trên đoạn có độ sâu lớn nhất từng ghi nhận dưới 30 cm, và 1 ở mọi đoạn khác.

**Thuật toán riêng** chạy trên mạng đường OpenStreetMap đã lưu sẵn (`graph_nodes`, `graph_edges`, `edge_units`):

- **Thời gian đi một cạnh** bằng chiều dài chia tốc độ theo loại đường. Tốc độ khởi đầu, tính bằng km/giờ, cho xe máy: trunk 40, primary 32, secondary 28, tertiary 24, còn lại 18; xe máy không đi motorway. Cho ô tô: motorway 70, trunk 45, primary 32, secondary 26, tertiary 22, còn lại 15. Đây là số ước lượng do tôi đặt.
- **Chi phí của cạnh** bằng thời gian đi cộng phần phạt: với mỗi đoạn mà cạnh đi qua, thời gian trên đoạn đó nhân với `loc_weight × hệ số xe × mức phạt`, trong đó mức phạt là 2 cho mức vừa và 20 cho mức cao.
- **Tìm đường** bằng thuật toán Dijkstra (`scipy.sparse.csgraph.dijkstra`) hai lần: một lần chỉ với thời gian đi, một lần với chi phí có phạt. Điểm đi và điểm đến được gắn vào nút gần nhất.
- **Kết quả** là hình học của đường tìm được, chiều dài, và thời gian ước lượng (không tính phần phạt).

**Chọn lộ trình đề xuất:** nếu lộ trình nhanh nhất của Goong có `flooded_m` bằng 0 thì đề xuất nó. Nếu không, đề xuất đường tránh ngập của thuật toán riêng khi `flooded_m` của nó nhỏ hơn, kèm thời gian chênh so với đường nhanh nhất theo cùng cách ước lượng. Khi đường tránh dài hơn 1,5 lần, vẫn hiện nó nhưng ghi rõ mức chênh để người dùng tự quyết.

**Giới hạn phải ghi trên giao diện:** thời gian của đường tránh ngập là ước lượng theo loại đường, không có số liệu giao thông; OpenStreetMap không biết hết các đoạn cấm xe máy hay cấm rẽ. Ở lộ trình đi qua đoạn nguy cơ cao, ghi thêm: ngập thường kéo theo ùn tắc, nên thời gian thực tế có thể dài hơn.

### 7.3 Endpoint Goong đã xác minh

| Dịch vụ | URL | Tham số chính |
|---|---|---|
| Direction V2 | `https://rsapi.goong.io/v2/direction` | `origin=lat,lng`, `destination=lat,lng`, `vehicle=car\|bike`, `alternatives=true\|false`, `api_key` |
| Autocomplete V2 | `https://rsapi.goong.io/v2/place/autocomplete` | `input`, `location=lat,lng`, `limit`, `api_key` |
| Place Detail V2 | `https://rsapi.goong.io/v2/place/detail` | `place_id`, `api_key` |
| Geocode V2 | `https://rsapi.goong.io/v2/geocode` | `address` hoặc `latlng=lat,lng`, `api_key` |
| Style bản đồ | `https://tiles.goong.io/assets/goong_map_web.json?api_key={khóa bản đồ}` | Dùng với MapLibre GL JS |

Direction V2 không có tham số điểm trung gian.

**Kết quả thử bằng khóa thật của nhóm, ngày 04/10/2026:**

| Phép thử | Kết quả |
|---|---|
| Direction V2, `alternatives=true`, bảy lần gọi (bốn cặp điểm cách nhau 4–13 km ở TP.HCM và Đà Nẵng, xe máy và ô tô) | Ba lần trả 1 lộ trình, bốn lần trả 2 lộ trình; không lần nào nhiều hơn |
| Hình dạng phản hồi của Direction V2 | `routes[].legs[].distance.value`, `duration.value`; `routes[].overview_polyline.points` là chuỗi mã hóa; mỗi lộ trình một chặng |
| Autocomplete V2 với "cho ben thanh" | Đúng: "Chợ Bến Thành"; có `structured_formatting.main_text` và `secondary_text` |
| Autocomplete V2 với tên đường ("đường Nguyễn Hữu Cảnh") | Trả về các địa điểm không liên quan. Dùng tốt cho địa điểm, không dùng được để tìm một con đường |
| Forward Geocode V2 với ba tên đường khác nhau | Cả ba trả cùng một kết quả sai ("Tân Sơn, Hồ Chí Minh"). Không dùng |
| Style bản đồ với khóa bản đồ | Tải được, 157 lớp |

Hai khóa nằm trong file `.env` ở thư mục gốc; file này đã có trong `.gitignore`. Nên giới hạn hai khóa theo tên miền và địa chỉ IP trong trang quản lý Goong, và đổi khóa sau hackathon.

## 8. Khóa và biến môi trường

| Biến | Dùng ở | Ý nghĩa |
|---|---|---|
| `GOONG_API_KEY` | Máy chủ | Khóa REST của Goong |
| `VITE_GOONG_MAP_KEY` | Giao diện | Khóa bản đồ của Goong |
| `VITE_API_BASE` | Giao diện | Địa chỉ máy chủ khi chạy riêng |
| `FLOODRISK_DATA` | Mọi nơi | Thư mục dữ liệu, mặc định `data` |
| `REFRESH_MINUTES` | Máy chủ | Chu kỳ tác vụ nền, mặc định 60; đặt 0 để tắt |
| `FLOODRISK_CONTACT` | Bộ ghi | Email liên hệ gửi kèm mỗi yêu cầu |
| `FLOODRISK_TEST_TOOLS` | Máy chủ, giao diện | Đặt 1 để bật bàn thử; để trống ở bản công khai |
| `TOMTOM_API_KEY` | Máy chủ | Khóa TomTom cho số liệu giao thông; để trống thì dùng bảng giao thông điển hình |

## 9. Quy ước làm việc chung

- **Nhánh git:** mỗi người một nhánh (`data`, `model`, `web`), gộp vào `main` ít nhất một lần mỗi ngày.
- **Ranh giới thư mục:** mỗi người chỉ sửa thư mục của mình. `config.py` và `contracts.py` thuộc hợp đồng đã đóng băng.
- **Kiểm thử:** mọi thay đổi phải qua `pytest` trước khi gộp. Kiểm thử không được gọi mạng.
- **Lệnh:** chạy từ thư mục gốc, dạng `python -m floodrisk....`, để dùng được trên Windows.

## 10. Triển khai

- **Nơi chạy:** một máy AWS EC2 `t3.small` (2 GB RAM), Ubuntu, vùng Singapore, ổ đĩa 30 GB. Ước tính 25–30 đô mỗi tháng (con số ước tính, cần xem lại bảng giá). Đặt cảnh báo ngân sách ở 50 đô.
- **Mốc ngày 3:** chạy bằng HTTP trên địa chỉ IP của máy. Mọi thứ hoạt động trừ nút định vị của trình duyệt.
- **Hết ngày 7:** có tên miền và HTTPS (Caddy đặt trước container), vì trình duyệt chỉ cho định vị trên trang HTTPS. Kỹ sư phần mềm lo tên miền.
- **Đóng gói:** một ảnh Docker chứa máy chủ FastAPI và bản dựng của giao diện; cả thư mục `data/` gắn vào `/data`, và `FLOODRISK_DATA=/data`.
- **Tác vụ nền:** chạy ngay khi khởi động rồi lặp lại mỗi `REFRESH_MINUTES`.
- **Dự phòng cho buổi trình diễn:** chạy trên máy cá nhân bằng cùng lệnh Docker, ở chế độ phát lại.

## 11. Phân công và lịch

### 11.1 Ai giữ gì

| Người | Giữ |
|---|---|
| **Người dữ liệu** | Bộ ghi, ghi nhận ngập, đoạn và tuyến, mạng đường cho thuật toán tìm đường, bảng gán ghi nhận vào đoạn, mưa Open-Meteo, địa hình (nếu kịp), bộ đọc báo (nếu kịp), bảng so sánh với ứng dụng hiện có, đề cương và ghép bài thuyết trình |
| **Người AI** | Bằng chứng, ghép và neo thang, điểm lịch sử, Mô hình 2, triều, tính nguy cơ, tác vụ mỗi giờ, các bộ tạo kịch bản và sáu kịch bản thử chuẩn, Mô hình 1 và cổng (nếu kịp), hai bảng kiểm chứng, câu lệnh trích cho bộ đọc báo |
| **Kỹ sư phần mềm** | Kế hoạch 01 (Task 1–3), lớp giả cho phần của hai người kia, máy chủ, mọi endpoint, thuật toán tìm đường tránh ngập, giao diện, bàn thử, triển khai, tên miền |

### 11.2 Lịch

| Ngày | Người dữ liệu | Người AI | Kỹ sư phần mềm |
|---|---|---|---|
| 1 | Chép bộ IRD từ `mlai-car-access`; bật bộ ghi; ghi nhận ngập TP.HCM; bắt đầu tải mưa lịch sử | Chạy thử trên dữ liệu thật (kế hoạch 01, Task 4); bằng chứng; ghép | Kế hoạch 01 (Task 1–3); lớp giả; máy chủ phục vụ lớp nguy cơ mẫu; bản đồ Goong; dựng máy EC2 |
| 2 | Đoạn, tuyến và mạng đường TP.HCM; bảng gán ghi nhận vào đoạn; bảng mưa theo ngày TP.HCM | Điểm lịch sử; đường cong mặc định; tính nguy cơ; tác vụ mỗi giờ | Lớp nguy cơ trên bản đồ; báo ngập |
| **3** | Đà Nẵng: ghi nhận, đoạn, mạng đường, bảng gán, bảng mưa theo ngày; soát kết quả gán; đề cương bài thuyết trình | Bộ tạo kịch bản: ngày có ghi nhận, thời điểm quá khứ, giả lập; chọn ngày phát lại | **Mốc: TP.HCM chạy thật trên EC2, chọn được kịch bản** |
| 4 | Địa hình cho hai thành phố (hạn chót để còn làm Mô hình 1) | Mô hình 2 khớp thật và neo thang; triều; sáu kịch bản thử chuẩn | Tìm địa điểm; thuật toán tìm đường |
| 5 | Dự phòng; bắt đầu bộ đọc báo | Mô hình 1 và cổng (một ngày) | Tìm đường tránh ngập hoàn chỉnh; giao diện lộ trình |
| 6 | Bộ đọc báo, hoặc hoàn tất địa hình | Hai bảng kiểm chứng; câu lệnh trích | Bàn thử trên giao diện; cảnh báo sớm |
| 7 | Bảng so sánh với ứng dụng hiện có; ghép bài thuyết trình | Số liệu và hình cho bài thuyết trình | Tên miền, HTTPS; thẻ giải thích; hệ số xe; endpoint chấm lộ trình |
| 8 | Bài thuyết trình | Sửa lỗi theo dữ liệu thật | Nối, sửa lỗi |
| 9 | Việc ngoài lõi (mục 15) | Việc ngoài lõi | Hoàn thiện giao diện; kịch bản trình diễn |
| 10 | Tổng duyệt | Tổng duyệt | Tổng duyệt |

### 11.3 Mốc bàn giao

| Hạn | Từ | Tới | Giao cái gì |
|---|---|---|---|
| Trưa ngày 1 | Kỹ sư phần mềm | Cả nhóm | Repo, `config.py`, `contracts.py`, dữ liệu mẫu (kế hoạch 01, Task 1–3) |
| Hết ngày 1 | AI | Kỹ sư phần mềm | `evidence.py`, `combine.py` |
| Hết ngày 1 | Dữ liệu | AI | `observations.parquet` của TP.HCM; file triều `data/raw/tide/h383.csv` |
| Trưa ngày 2 | Dữ liệu | AI, kỹ sư phần mềm | Của TP.HCM: `units.parquet` (chưa có địa hình), `obs_units.parquet`, ba file mạng đường |
| Hết ngày 2 | Dữ liệu | AI | Của TP.HCM: `rain_cells.parquet`, `rain_daily.parquet`; hàm `fetch_forecast` và `fetch_range` |
| Hết ngày 2 | AI | Kỹ sư phần mềm | `scores.parquet`, `risk.parquet` thật của TP.HCM; `jobs/hourly.py` |
| Trưa ngày 3 | AI | Kỹ sư phần mềm | Các kịch bản đầu tiên trong `replay/` |
| Hết ngày 3 | Dữ liệu | AI, kỹ sư phần mềm | Của Đà Nẵng: `units`, `observations`, `obs_units`, `rain_cells`, `rain_daily`, ba file mạng đường |
| Hết ngày 4 | Dữ liệu | AI | Đặc điểm địa hình của hai thành phố. Trễ mốc này thì bỏ Mô hình 1 |

### 11.4 Khi trễ thì cắt theo thứ tự này

1. Mô hình 1 và địa hình.
2. Bộ đọc báo.
3. Thẻ giải thích, hệ số xe và endpoint chấm lộ trình.
4. Bàn thử trên giao diện (các kịch bản vẫn tạo được bằng dòng lệnh).
5. Triều (TP.HCM chỉ còn ngập do mưa).
6. Đà Nẵng.

Không được cắt: điểm lịch sử, tác vụ mỗi giờ, các bộ tạo kịch bản, báo ngập, tìm đường tránh ngập, triển khai.

## 12. Việc phải làm ngay ngày 1

- **Khóa Goong đã được thử** (mục 7.3). Không cần thử lại số lộ trình thay thế.
- **Chạy thử mã trong các kế hoạch trên dữ liệu thật của TP.HCM**, để lộ lỗi thư viện (OSMnx, GeoPandas, utide) sớm. Mã trong các kế hoạch chưa từng được chạy.
- **Người dữ liệu đặt email** cho biến `FLOODRISK_CONTACT`.
- **Gửi thư** cho cổng mưa ngập Đà Nẵng, VRain và nhóm tác giả IRD (mục 13.3).

## 13. Nguồn dữ liệu thô và quyền sử dụng

### 13.1 Đã xác nhận trong ngày 04/10/2026

| Nguồn | Chi tiết |
|---|---|
| Mưa trạm đo VRain, không cần khóa | `https://data.vrain.vn/public/current/all.json` (khoảng 2.600 trạm, các trường `sn`, `lt`, `lg`, `d`); theo tỉnh: `/56.json` TP.HCM (32 trạm), `/32.json` Đà Nẵng (94 trạm), `/20.json` Hà Nội (25 trạm). Số liệu là mm cộng dồn từ 19 giờ hôm trước. Không có lịch sử |
| Cổng mưa ngập Đà Nẵng | Trang gọi `/v1/flood/reports?from_time=…&to_time=…` (giây Unix). Trang mưa gọi `/v2/client/stations/detail_ten_minute_report?fromTime=…&toTime=…` cho mưa 10 phút. Chưa thử nới khoảng thời gian có trả đủ lịch sử hay không |
| Camera giao thông TP.HCM | Trang công khai liệt kê 796 camera, tọa độ nằm trong dữ liệu trả về; trang không nêu điều khoản sử dụng |
| Danh sách điểm ngập Hà Nội trên báo chí | Có mô tả đoạn và số nhà, ví dụ "Hoa Bằng (từ số nhà 91 đến 97…)", vài bài có độ sâu. Tìm qua Google News RSS với truy vấn `"điểm úng ngập" "Thoát nước Hà Nội" "đoạn từ"`; ước tính 100–200 đoạn cho 2023–2026 |
| Danh sách TP.HCM trên báo chí | 34 tuyến của Sở Xây dựng chỉ có tên đường và phường. 23 tuyến ngập triều chỉ có tên đường và độ sâu theo nhóm |
| Danh sách Đà Nẵng trên báo chí | Thưa; mỗi bài chỉ nêu 5–15 đường, ít khi có đoạn |

Hệ quả cho mong muốn đoạn nhỏ 100–200 m: ở Hà Nội báo chí cho được nhãn mức đoạn; ở TP.HCM thì không, nên đoạn nhỏ ở đó phải đến từ báo cáo người dùng và từ 78 ghi nhận IRD có độ chính xác cao; ở Đà Nẵng thì đến từ các ghi nhận loại `point` của cổng mưa ngập.

### 13.2 Bộ ghi dữ liệu

- **Chạy từ ngày 1, mỗi giờ một lần:** hai file VRain của TP.HCM và Đà Nẵng, và dự báo Open-Meteo cho tâm mỗi thành phố. Số liệu VRain là cộng dồn nên mỗi giờ một lần là đủ.
- **Phải gửi `User-Agent` có tên dự án và email liên hệ.** Đã thử ngày 04/10: VRain trả 200 với `User-Agent` có tên, và trả 403 với `User-Agent` mặc định của thư viện `requests`.
- **Không gọi định kỳ** cổng Đà Nẵng. Lịch sử Đà Nẵng được lấy một lần.
- **Hà Nội không nằm trong bộ ghi** của bản hackathon.

### 13.3 Quyền sử dụng

- **Gửi thư là thông báo, chưa phải được phép.** Phải nói đúng như vậy trong bài thuyết trình, và sẵn sàng gỡ dữ liệu Đà Nẵng nếu bị từ chối.
- **VRain công khai:** chưa có điều khoản rõ; hỏi luôn trong thư xin khóa.
- **IRD:** trang dữ liệu ghi CC BY-NC 4.0, file ReadMe ghi CC BY 4.0. Hackathon dùng được cả hai; thương mại hóa phải hỏi tác giả.
- **FABDEM:** phi thương mại (chưa xác nhận).
- **Mạng xã hội:** điều khoản của Meta cấm thu thập tự động khi chưa được cho phép bằng văn bản. Không thu thập.
- **Camera TP.HCM:** truy cập được nhưng không có điều khoản; phải xin phép trước khi dùng.
- **Bài báo:** chỉ lưu dữ kiện và đường dẫn, không lưu nội dung.
- Bài thuyết trình có một trang liệt kê giấy phép và nguồn thay thế cho từng loại dữ liệu.

## 14. Tận dụng từ dự án `mlai-car-access`

Thư mục `D:\HK1 4 year\Hackathon\mlai-car-access` đã có sẵn những thứ sau.

| Có sẵn | Ở đâu | Dùng cho |
|---|---|---|
| Bộ IRD đầy đủ | `data/flood/ird-hcmc/` | Chép `HCMC_Floods_BDD.gpkg` vào `data/raw/ird/`; khỏi tải lại |
| Chín con đường ngập lặp lại nhiều năm, có hình học | `data/flood/ird-hcmc/flood_roads.geojson` | Đối chiếu với các đoạn đạt điểm lịch sử 0,95 |
| Nghiên cứu nguồn ngập ngày 28/09/2026 | `docs/research/03-flood.md` | Danh sách nguồn đã thử, kèm phép thử địa hình ở mục 0 |
| Hàm khớp ghi nhận vào đường theo độ chính xác | `backend/app/flood.py` | Tham khảo khi viết bảng gán ở mục 4.2 |
| Mẫu bản tin triều và hàm nội suy mực nước giữa các đỉnh | `data/flood/tide_forecast.json`, `backend/app/flood.py` | Ghi đè bản tin triều (mục 4.10) |
| Mã tìm bài báo theo tên đường qua Google News RSS | `backend/app/news.py` | Bộ đọc báo (mục 15) |
| Địa chỉ ảnh camera và câu lệnh đọc ảnh | `backend/app/ai.py` | Đọc camera (mục 15) |

Tên cột trong file GPKG của IRD dùng dấu gạch dưới (`Location_name`, `Water_height_max_cm`, `Spatial_precision`, `Geocoding_method`). Bộ đọc trong kế hoạch 02 chuẩn hóa tên cột nên đọc được.

Phân bố thật của bộ IRD, đo trên file trong thư mục trên: 362 dòng có ngày, 64 ngày khác nhau, trong đó 45 ngày từ 2016 trở đi. Mô hình 2 của TP.HCM vì vậy có tối đa 45 ngày ngập để học. Về độ chính xác vị trí: 78 dòng "High", 99 "Medium", 248 "Low"; 72 dòng là điểm đại diện cho một khu chứ không phải một con đường.

## 15. Ngoài lõi, theo thứ tự ưu tiên

Chỉ làm sau khi mốc ngày 3 đã đạt và các việc lõi của ngày 4–7 đã xong.

1. **Bộ đọc báo cho Hà Nội:** tìm bài qua Google News RSS, trích ngày, tên đường, đoạn, độ sâu bằng mô hình ngôn ngữ, soát tay 20 bài. Người AI viết câu lệnh trích; người dữ liệu chạy và nạp vào bảng ghi nhận. Đây là phần AI chắc chắn chạy được, và là cách trình diễn việc thêm một thành phố mới.
2. **Ghi đè theo trạm đo VRain** (mục 4.10).
3. **Ghi đè theo bản tin triều** (mục 4.10), nếu buổi trình diễn rơi vào kỳ triều cường.
4. **Lấy thời gian của Goong cho đường tránh ngập:** gọi Goong qua một hoặc hai điểm trung gian lấy từ đường mà thuật toán riêng tìm ra, để thời gian hai lộ trình so được với nhau.
5. **Hà Nội:** chạy quy trình cho thành phố thứ ba.
6. **Đọc ảnh camera giao thông TP.HCM**, sau khi được phép.
7. **Đổi FABDEM sang DeltaDTM; lớp radar Nhà Bè.**

Số liệu giao thông đông đúc từng bị bỏ khỏi dự án, và được đưa trở lại ngày 04/10/2026 (mục 18.3, điểm 17). Mục 4 ở trên (lấy thời gian của Goong cho đường tránh ngập) không còn cần: mọi lộ trình giờ được tính giờ bằng cùng một cách (điểm 16).

## 16. Kết quả phản biện độc lập

Một agent không biết bối cảnh đã đọc toàn bộ tài liệu và phản biện hai vòng. Những thay đổi đến từ đó:

| Vấn đề nó tìm ra | Cách sửa trong bản 3 |
|---|---|
| Bản demo trống khi trời khô | Chế độ phát lại là một phần của lõi (mục 4.8) |
| Dữ liệu thật ghép vào ở ngày 6, dồn việc vào người dữ liệu | Mốc ngày 3 chạy thật chỉ bằng lịch sử; triều, tác vụ mỗi giờ và phát lại chuyển sang người AI (mục 11) |
| Ngưỡng theo phân vị về 0 khi phần lớn đoạn có điểm 0, làm cả thành phố lên mức vừa | Hai ngưỡng cố định 0,35 và 0,60 (mục 4.5) |
| Giá trị thô của `T` không có nghĩa cố định | Neo `T` theo tần suất (mục 4.4) |
| Mô hình có thể tự tạo mức cao | Hai bậc 0,55 và 0,50, tính ở cấp tuyến (mục 4.6) |
| Phép kiểm ghép không thể trượt | Thay bằng bảng điểm vận hành và phép thử ngoài danh sách cũ (mục 4.9) |
| Cổng kiểm chứng đo thiên lệch báo chí | Tỉ lệ xây dựng thành biến nhiễu và thành mốc so sánh; chỉ đánh giá vùng xây dựng; bootstrap theo khối 3 km (mục 4.9) |
| Dữ liệu 2025–2026 bị dùng để chọn mô hình | Mọi lựa chọn chỉ dùng dữ liệu trước 2025 (mục 4.9) |
| Ghi nhận chỉ có tên đường bị gán vào một cây số bất kỳ | Lan theo các đoạn liền nhau cùng tên; trọng số vị trí khi chấm lộ trình (mục 4.2, 4.3, 7.2) |
| Cầu vượt sông bị xếp là dễ ngập nhất | Giữ thẻ cầu, loại cầu khỏi Mô hình 1 (mục 4.1) |
| Trạm đo và bản tin triều lệch nguồn với lúc học | Đưa ra khỏi lõi; chỉ là ghi đè tùy chọn, chỉ được nâng, có ngưỡng riêng (mục 4.10) |
| Thiếu việc cho 30 điểm tiêu chí khác biệt và tích hợp | Thẻ giải thích, hệ số xe, endpoint chấm lộ trình, bảng so sánh có người làm và ngày làm (mục 7, 11) |
| Gọi định kỳ cổng chính quyền trước khi được phép; lưu tọa độ người báo | Bộ ghi chỉ còn VRain và Open-Meteo; báo cáo không lưu tọa độ, xóa sau 24 giờ (mục 13, 4.7) |
| Hệ số âm làm hỏng việc khớp Mô hình 2 | Loại từng biến một; có đường cong mặc định (mục 4.4) |

Một điểm tôi và agent phản biện không hoàn toàn đồng ý: nó muốn bỏ hẳn ghi đè theo trạm đo; tôi giữ lại ở dạng tùy chọn với ngưỡng riêng và yêu cầu báo số ngày báo nhầm, vì mưa đo được vẫn là tín hiệu tốt nhất cho câu hỏi "lúc này có đang mưa to ở đây không".

## 17. Cách đọc bốn kế hoạch

- Các kế hoạch 01–04 chứa mã và kiểm thử viết cho bản 1 của thiết kế. **Chưa dòng mã nào được chạy.**
- Đầu mỗi kế hoạch có mục **"Bản 3: trạng thái từng task"**, ghi task nào giữ nguyên, task nào phải sửa và sửa gì, task nào bỏ, task nào chuyển người làm, cùng các task mới.
- Khi mã trong kế hoạch khác tài liệu này thì làm theo tài liệu này. Hợp đồng dữ liệu ở mục 5 và các hàm ở mục 6 là ràng buộc; mã trong kế hoạch là điểm xuất phát.
- Agent phản biện khuyên không viết lại toàn bộ mã lần nữa khi chưa chạy thử, và tôi làm theo: phần mã chỉ được sửa trực tiếp ở kế hoạch 01, vì mọi thứ khác phụ thuộc vào nó.
- Kết quả chạy thử và các điểm làm rõ sau lần rà cuối nằm ở mục 18.

## 18. Kết quả chạy thử và các điểm làm rõ (04/10/2026)

### 18.1 Đã chạy thử

Mã được chép nguyên văn từ các kế hoạch ra một thư mục tạm, cài bằng `requirements.txt` của kế hoạch 01 trên Windows với Python 3.12.

| Phần | Kết quả |
|---|---|
| Kế hoạch 01 | 12 trên 12 kiểm thử đạt; lệnh tạo dữ liệu mẫu và lệnh `smoke` chạy được |
| Mã Python bản 1 của kế hoạch 02, 03, 04 | 137 kiểm thử, 134 đạt. Ba kiểm thử không đạt đều thuộc phần mà bản 3 đã thay: `assemble` thiếu ba cột mới, `fit_thresholds`, `train_final` |
| Đọc bộ IRD thật | 425 dòng, 362 dòng có ngày |
| OSMnx tải mạng đường và chia tuyến | Chạy được trên một ô 1 km ở trung tâm TP.HCM |
| WorldCover đọc từ xa | Chạy được |
| Open-Meteo lịch sử và dự báo | Chạy được |
| Triều Vũng Tàu qua `utide` trên số thật | Chạy được; 10 ngày triều cao nhất của năm 2025 rơi vào tháng 10 tới tháng 12, đúng mùa triều cường |
| Goong | Mục 7.3 |
| Giao diện web bản 1 (Vite 8, React 19, TypeScript 6, MapLibre GL 6, Tailwind 4, vitest 5) | Cài được; 4 trên 4 kiểm thử `format` đạt; kiểm kiểu báo 1 lỗi ở `MapView.tsx` (mục 18.2), các file còn lại không lỗi |

Để mã bản 1 chạy trên nền bản 3, lần thử này dùng một lớp đệm tạm thêm lại `thresholds_path` và trường `validated`. Lớp đệm đó không nằm trong dự án.

**Chưa chạy:** giao diện trên trình duyệt thật, Docker, và mọi mã mới của bản 3 (điểm lịch sử, bảng gán ghi nhận, các bộ tạo kịch bản, thuật toán tìm đường).

### 18.2 Lỗi thật tìm thấy khi chạy

- **Cột ngày của bộ IRD có kèm múi giờ UTC.** So sánh nó với một ngày không có múi giờ sẽ báo lỗi, và việc này xảy ra ở Mô hình 2 và các bộ tạo kịch bản. Bộ đọc phải bỏ múi giờ, giữ nguyên ngày.
- **OpenStreetMap không trả cột `bridge`, `tunnel`** khi vùng tải không có cầu hay hầm. Mã phải tự thêm cột rỗng.
- **Lệnh `python` trên máy đã thử** trỏ tới bản của MSYS2 trong Git Bash, và bản mặc định của Windows là 3.14. Môi trường ảo phải được tạo bằng đường dẫn đầy đủ tới Python 3.12 (kế hoạch 01, Task 1).
- **MapLibre GL 6 không có export mặc định.** Dòng `import maplibregl from "maplibre-gl"` trong `MapView.tsx` không qua được kiểm kiểu. Phải nhập theo tên, ví dụ `import { Map, NavigationControl, GeolocateControl } from "maplibre-gl"`, và sửa các chỗ dùng `maplibregl.` cho khớp.
- **Một kiểm thử cũ so sánh số thực đúng tại ngưỡng** (`test_thresholds_and_levels`) và trượt vì sai số dấu phẩy động. Hàm nó kiểm đã bị bỏ, nhưng kiểm thử mới cho `to_level` phải dùng đúng hằng số trong `config`, không dùng giá trị tính ra.

### 18.3 Các điểm làm rõ

Các quy tắc dưới đây bổ sung cho những mục phía trên, và được ưu tiên khi có chỗ khác nhau.

1. **Kịch bản `recorded-day` của ngày từ 2025 trở đi** phải dùng điểm lịch sử và Mô hình 2 chỉ học từ dữ liệu trước 2025. Nếu không, ghi nhận của chính ngày đó sẽ nằm sẵn trong điểm lịch sử và bản trình diễn thành ra tự chấm điểm cho mình. Kịch bản của ngày trước 2025 phải ghi rõ "ngày này nằm trong dữ liệu đã học".
2. **Đoạn chỉ có điểm mô hình không bao giờ lên mức cao**, kể cả khi mưa và triều cùng lớn: mức của đoạn có `basis` là `model` bị chặn ở mức vừa.
3. **Ghi nhận `high`** được gán vào đoạn gần nhất trong 100 m, không xét tên đường. Tên đường chỉ dùng cho `medium` và `low`.
4. **Ghi nhận có nguyên nhân `unknown`** không vào điểm lịch sử của nguyên nhân nào, nhưng vẫn được đếm trong `history`.
5. **Việc nâng mức theo báo cáo** ("ngập vừa" lên ít nhất mức vừa, "ngập cao" lên mức cao) nằm trong `evidence.py`, để máy chủ và các bộ tạo kịch bản dùng chung.
6. **Báo cáo gửi lúc đang xem một kịch bản** được lưu kèm mã kịch bản và chỉ áp dụng khi xem kịch bản đó; chúng không lọt vào chế độ trực tiếp.
7. **Danh sách `validated`** trong `model_choice.json` do `run_checks` ghi, sau khi hai bảng kiểm chứng của thành phố đó được tạo. Trước đó giao diện ghi "chưa được kiểm chứng".
8. **Bảng "lịch sử phủ được bao nhiêu"** chỉ tính ghi nhận có ngày, và không tính 34 tuyến chính thức.
9. **`split_into_units` trả về một bộ đôi** `(units, pieces)`; các kiểm thử cũ phải tách bộ đôi đó.
10. **Phần web đọc thêm** `observations.parquet` và `obs_units.parquet` để hiện thẻ giải thích.
11. **Chọn lộ trình đề xuất:** trong mọi lộ trình tìm được (của Goong và của thuật toán riêng), lấy lộ trình có `flooded_m` nhỏ nhất; bằng nhau thì lấy `exposure` nhỏ nhất, rồi thời gian ngắn nhất. Không loại lộ trình nào vì dài; lộ trình dài hơn 1,5 lần đường nhanh nhất mang cờ `long_detour` để giao diện ghi rõ. Hàm `choose` và trường `via_detour` của mã cũ bị bỏ.
12. **Ngày làm thẻ giải thích, hệ số xe và endpoint chấm lộ trình** là ngày 7, theo mục 11.2.
13. **Kỹ sư phần mềm dựng kế hoạch 01 (Task 1–3)** thay cho người AI, vì là người bắt đầu trước. Mốc trưa ngày 1 ở mục 11.3 giữ nguyên, chỉ đổi người giao. Hai người còn lại vẫn đọc và xác nhận `config.py`, `contracts.py`.
14. **Bốn hàm tạo kịch bản** (`make_recorded_day`, `make_past_moment`, `make_snapshot`, `make_synthetic`) **trả về mã kịch bản** dạng chuỗi, cũng là tên file trong `replay/`. Endpoint của bàn thử cần mã này.
15. **Phần web gọi mã của người AI qua một file duy nhất,** `floodrisk/api/ports.py`. Khi module thật chưa có, file này dùng một bản giả đơn giản có cùng chữ ký, và `GET /api/health` ghi phần nào đang là bản giả. Nhờ vậy kỹ sư phần mềm không phải chờ ai, và việc nối chỉ là gộp nhánh hoặc chép file. Lớp giả được mô tả ở `docs/superpowers/specs/swe/01-nen-va-lop-gia.md`; danh sách tính năng, bảng theo dõi và bảng nối ghép của phần web ở `docs/superpowers/specs/swe/00-tong-quan.md`.
16. **Thuật toán tìm đường riêng là bộ máy chính cho mọi lộ trình,** kể cả lúc trời khô: đường nhanh nhất, mọi lộ trình thay thế hợp lý (không giới hạn ở hai), và đường tránh ngập, tất cả được tính giờ bằng cùng một cách. Goong làm mốc đối chiếu, nguồn chỉ dẫn và phương án lùi. Điểm này thay cho câu "Goong cho lộ trình nhanh nhất để so sánh" ở mục 1 và mục 7.2; các quy tắc chấm điểm, mức phạt và cách chọn lộ trình đề xuất ở mục 7.2 và điểm 11 giữ nguyên. Chi tiết ở `docs/superpowers/specs/swe/05-tim-duong.md`.
17. **Số liệu giao thông được đưa trở lại,** theo yêu cầu của chủ dự án. Ba tầng: TomTom Traffic Flow khi có khóa; bảng điển hình theo giờ và loại đường; và hệ số "ngập làm chậm" trên đoạn có nguy cơ. Hai tầng sau là số ước lượng và phải ghi nhãn trên giao diện. Google Maps không được dùng: điều khoản của Google cấm dùng dịch vụ của họ với một bản đồ không phải của Google. TomTom đã được gọi thử bằng khóa của nhóm chiều 04/10/2026: ở trung tâm TP.HCM, 89% chiều dài đường từ loại `tertiary` trở lên khớp được với số liệu của TomTom. Chi tiết và kết quả tra cứu nguồn ở `docs/superpowers/specs/swe/09-giao-thong.md`.
18. **Sản phẩm trước hết phải dùng được như một bản đồ thông thường:** ô tìm kiếm, thẻ địa điểm, chạm để ghim và xem địa chỉ, vị trí của tôi. Chạm vào bản đồ giờ mở thẻ địa điểm; báo ngập đi qua nút trong thẻ đó. Chi tiết ở `docs/superpowers/specs/swe/08-ban-do-co-ban.md`.
19. **Lịch của kỹ sư phần mềm ở mục 11.2 được thay** bằng bảng ở `docs/superpowers/specs/swe/00-tong-quan.md`, mục 5: bản đồ cơ bản ngày 1, tìm đường lúc bình thường ngày 2, lớp nguy cơ và triển khai ngày 3, báo ngập và HTTPS ngày 4. Mốc ngày 3 giữ nguyên, nhưng điều kiện "báo ngập được" đổi thành "tìm đường chạy trên mạng đường thật". Hạn giao ba file mạng đường của TP.HCM (trưa ngày 2) trở thành hạn quan trọng nhất với kỹ sư phần mềm.
