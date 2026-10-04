# Spec 01: Nền dự án và lớp giả

**Mã theo dõi:** S1.1, S1.2, S1.3. **Ưu tiên:** lõi. **Ngày:** 1–2.

## Mục tiêu

Sau spec này, kỹ sư phần mềm chạy được máy chủ và giao diện trên máy mình mà không cần bất cứ thứ gì từ người dữ liệu hay người AI. Khi phần thật của họ đến, việc nối chỉ là chép file hoặc gộp nhánh.

## 1. Nền dự án (S1.1)

Làm đúng kế hoạch 01, Task 1 tới 3 (`docs/superpowers/plans/2026-10-04-01-nen-tang-chung.md`). Mã của ba task này đã được chạy thử ngày 04/10/2026 và đạt 12 trên 12 kiểm thử. Ba điều dễ sai:

- **Tạo môi trường ảo bằng đường dẫn đầy đủ tới Python 3.12.** Lệnh `python` trong Git Bash trỏ tới bản của MSYS2, và bản mặc định của Windows là 3.14. Lệnh chính xác nằm ở Task 1 của kế hoạch 01.
- **Dùng đúng `requirements.txt` đã ghim phiên bản** trong kế hoạch 01, để ba người có cùng môi trường.
- **Khởi tạo git, đẩy nhánh `main` lên, rồi làm việc trên nhánh `web`.** Hai người kia cần `config.py`, `contracts.py` trên `main` trước khi bắt đầu.

Khung giao diện trong `web/`: Vite 8, React 19, TypeScript 6, Tailwind 4, MapLibre GL 6, vitest 5. Bộ này đã cài và dựng được ngày 04/10. MapLibre GL 6 không có export mặc định, nên phải nhập theo tên: `import { Map, NavigationControl, GeolocateControl } from "maplibre-gl"`.

Trong lúc phát triển, Vite chuyển tiếp mọi đường dẫn `/api` sang `http://127.0.0.1:8000`, để giao diện và máy chủ chạy riêng mà không vướng CORS.

## 2. Lớp giả (S1.2)

Lớp giả gồm ba phần, tất cả nằm trong `src/floodrisk/api/`.

### 2.1 Dữ liệu mẫu trên đĩa: `api/devdata.py`

Lệnh `python -m floodrisk.api.devdata data/sample` làm các việc sau:

1. Gọi `floodrisk.samples.make_sample` cho cả `hcm` và `danang`. Mỗi thành phố có tám đường mẫu, một lưới đường 4 × 4 giao lộ và một kịch bản phát lại `2024-10-18`.
2. Ghi thêm `observations.parquet` và `obs_units.parquet` cho mỗi thành phố, khớp với cột `history` của `scores.parquet`, để thẻ giải thích có thứ để hiện. Hai bảng phải qua `contracts.OBSERVATIONS` và `contracts.OBS_UNITS`.
3. Ghi thêm một kịch bản thứ hai, mã `sample-synthetic`, có `kind` là `synthetic`. Trong kịch bản này mưa tăng dần qua ba giờ (ngược với bảng nguy cơ mẫu, vốn giảm dần), và đoạn mẫu số 2 có `reporters` bằng 4 ở giờ 0. Nó dùng để thử dải chữ "GIẢ LẬP", dòng "4 người đã báo", và câu khuyên "nên đi ngay" của spec 06.
4. Đặt `computed_at` của `risk.parquet` về giờ hiện tại, để giao diện không báo dữ liệu cũ. Thêm cờ `--stale` để giữ thời điểm cũ khi cần thử dòng cảnh báo đó.
5. Ghi `model_choice.json` với `validated` chỉ gồm `hcm`. Như vậy Đà Nẵng mẫu hiện dòng "chưa được kiểm chứng" và cả hai trạng thái đều thử được.
6. Ghi một file đánh dấu rỗng `processed/SAMPLE`. Máy chủ dựa vào file này để biết mình đang chạy trên dữ liệu mẫu.

Không sửa `samples.py` của kế hoạch 01: mọi thứ phần web cần thêm đều nằm trong `devdata.py`.

### 2.2 Một cửa duy nhất sang mã của người khác: `api/ports.py`

`ports.py` là file duy nhất trong `api/` được nhập từ `floodrisk.model` và `floodrisk.jobs`. Nó xuất ra đúng các tên sau, với chữ ký ở QĐKT mục 6:

| Tên | Bản thật nằm ở | Tên phần trong `/api/health` |
|---|---|---|
| `Report`, `EvidenceResult`, `apply_evidence` | `floodrisk.model.evidence` | `evidence` |
| `to_level` | `floodrisk.model.combine` | `levels` |
| `make_synthetic`, `make_past_moment` | `floodrisk.model.scenarios` | `scenarios` |
| `run_hourly` | `floodrisk.jobs.hourly.run_all` | `hourly` |
| `status() -> dict[str, str]` | — | Trả `"real"` hoặc `"fake"` cho từng phần |

**Quy tắc chọn bản thật hay bản giả**, áp dụng riêng cho từng phần lúc máy chủ khởi động:

- Nhập được module thật thì dùng bản thật.
- Nhập thất bại vì thiếu một module có tên bắt đầu bằng `floodrisk.` thì dùng bản giả, và ghi một dòng cảnh báo nêu tên module thiếu. Đây là trường hợp "người kia chưa giao".
- Mọi lỗi khác được ném ra nguyên vẹn. Một module thật có lỗi cú pháp, hoặc thiếu thư viện ngoài, phải làm máy chủ dừng ngay; nếu lặng lẽ lùi về bản giả thì lỗi đó sẽ bị giấu tới buổi trình diễn.

### 2.3 Các hàm giả: `api/fakes.py`

Bản giả có cùng chữ ký với bản thật và làm một phép tính đơn giản, đủ để giao diện phản ứng hợp lý.

| Hàm giả | Cách tính |
|---|---|
| `to_level(risk)` | Hai ngưỡng `LEVEL_MEDIUM`, `LEVEL_HIGH` trong `config`. Giống bản thật |
| `apply_evidence(prior, reports, now)` | Giữ báo cáo mới nhất của mỗi người; bỏ báo cáo quá 180 phút. Số người đã báo là số người báo "ngập" trong 30 phút qua. Mức được báo là mức nhiều người chọn nhất, hòa thì lấy mức cao hơn. Nguy cơ bằng `prior` cộng 0,15 cho mỗi người báo ngập và trừ 0,15 cho mỗi người báo không ngập, kẹp trong khoảng 0 tới 1; có người báo "ngập vừa" thì ít nhất 0,35, "ngập cao" thì ít nhất 0,60. Không có trọng số giảm theo thời gian |
| `make_synthetic(city, label, rain_3h_mm, rain_24h_mm=None, cells="all", tide="none", n_reports=0, seed=0)` | `T_mưa = min(1, rain_3h_mm / 100)`; `T_triều` là 0, 0,45 hoặc 0,75 theo `tide`; nguy cơ theo công thức ghép ở QĐKT mục 4.5 trên `scores.parquet`. `cells="random"` chọn một nửa số đoạn theo `seed`. `n_reports` đoạn nhận 1–5 người báo. Ghi `replay/{mã}.parquet` và một dòng `index.json` có `kind` là `synthetic`, nhãn thêm đuôi "(bản giả)". Trả về mã kịch bản |
| `make_past_moment(city, when, label)` | Không gọi mạng. Lấy một `T_mưa` giả cố định theo ngày giờ của `when`, rồi tính như trên. `kind` là `past-moment`, nhãn thêm đuôi "(bản giả)". Trả về mã kịch bản |
| `run_hourly()` | Không làm gì, trả danh sách rỗng |

Bản giả không được dùng làm bằng chứng cho bất cứ điều gì về mô hình. Nó chỉ để phần web có thứ để gọi.

### 2.4 Kiểm thử hợp đồng

`tests/api/test_port_contract.py` chạy cùng một bộ khẳng định trên bản đang được `ports` chọn, dù là giả hay thật. Đây là danh sách những điều phần web dựa vào:

- Không có báo cáo: nguy cơ bằng `prior`, số người báo bằng 0, mức được báo rỗng.
- Bốn người khác nhau báo "ngập cao" trong 10 phút qua: `to_level` của kết quả bằng 2, số người báo bằng 4, mức được báo bằng 3.
- Một người báo hai lần chỉ được đếm một lần.
- Báo cáo quá 180 phút không có tác dụng.
- Báo cáo "không ngập" không làm tăng nguy cơ.
- `make_synthetic` trả về một chuỗi; file kịch bản qua `contracts.REPLAY`; `index.json` có đúng một dòng với mã đó dù gọi hai lần; cùng `seed` cho cùng kết quả; tăng lượng mưa không làm giảm mức của đoạn nào.
- `run_hourly` trả về một danh sách.

Khi bản thật của người AI được gộp vào, bộ kiểm thử này tự chuyển sang kiểm bản thật. Nếu nó trượt, chỗ lệch nằm ở đường nối và phải được báo cho người AI ngay.

## 3. Trạng thái và lệnh kiểm tra nối ghép (S1.3)

### 3.1 `GET /api/health`

```json
{
  "ok": true,
  "test_tools": false,
  "data": "sample",
  "parts": {"evidence": "fake", "levels": "fake", "scenarios": "fake", "hourly": "fake"},
  "traffic": {"hcm": {"source": "typical", "observed_at": null}},
  "last_refresh": null,
  "last_error": null
}
```

- `data` là `"sample"` khi có file đánh dấu `processed/SAMPLE` trong thư mục dữ liệu, ngược lại là `"real"`.
- `traffic` ghi nguồn giao thông đang dùng cho từng thành phố: `"tomtom"` hoặc `"typical"` (spec 09).
- `last_refresh` và `last_error` do tác vụ nền ghi (spec 07).

### 3.2 Nhãn trên giao diện

Khi `data` là `"sample"` hoặc có phần nào là `"fake"`, góc dưới bản đồ hiện một nhãn nhỏ: "Dữ liệu mẫu" hoặc "Đang dùng bản giả: báo cáo, kịch bản". Chạm vào nhãn mở danh sách đầy đủ. Khi mọi thứ đều thật thì không có nhãn nào.

### 3.3 Lệnh `python -m floodrisk.api.doctor hcm danang`

Lệnh này là bước đầu tiên mỗi khi nhận file từ người khác. Với mỗi thành phố, nó in một bảng và kết thúc bằng mã lỗi khác 0 nếu có dòng nào hỏng.

| Kiểm | Lỗi hay cảnh báo |
|---|---|
| Từng file phần web đọc có tồn tại không: `units`, `scores`, `risk`, ba file mạng đường | Lỗi |
| Từng bảng có qua `contracts.validate` không; thông báo nêu tên cột thiếu | Lỗi |
| Mọi `unit_id` trong `scores`, `risk`, `edge_units` đều có trong `units` | Lỗi |
| Mỗi đoạn trong `risk` có đủ ba `hour_offset` | Lỗi |
| Mọi `u`, `v` của `graph_edges` đều có trong `graph_nodes` | Lỗi |
| Mỗi mã trong `replay/index.json` có file tương ứng và file đó qua `contracts.REPLAY` | Lỗi |
| Thiếu `observations` hoặc `obs_units` | Cảnh báo: thẻ giải thích sẽ không có lịch sử |
| Chưa có kịch bản nào; thành phố chưa có trong `validated`; `risk.computed_at` cũ hơn 3 giờ | Cảnh báo |
| Số dòng của từng bảng và thời gian nạp cả thành phố vào bộ nhớ | Chỉ in ra |

## 4. Cách chạy lúc phát triển

Hai lệnh, mỗi lệnh một cửa sổ dòng lệnh, đều chạy từ thư mục gốc (đã kích hoạt môi trường ảo):

```bash
python -m floodrisk.api.dev
```

```bash
npm --prefix web run dev
```

- `floodrisk.api.dev` mặc định đặt `FLOODRISK_DATA=data/sample`, `REFRESH_MINUTES=0`, `FLOODRISK_TEST_TOOLS=1`, tự sinh dữ liệu mẫu nếu chưa có, và đọc khóa Goong, TomTom từ `.env`. Muốn chạy trên dữ liệu thật hoặc đổi cổng thì đặt biến môi trường trong cửa sổ dòng lệnh trước (giá trị đặt ở đó thắng giá trị trong `.env`). Muốn làm mới dữ liệu mẫu (ví dụ để `computed_at` là giờ hiện tại) thì chạy `python -m floodrisk.api.devdata data/sample`.
- Giao diện đọc `VITE_GOONG_MAP_KEY` thẳng từ `.env` ở thư mục gốc (Vite đặt `envDir` ở đó), nên **không cần** chép khóa sang `web/.env.local`. Vite chỉ đưa các biến có tiền tố `VITE_` xuống trình duyệt, nên `GOONG_API_KEY` và `TOMTOM_API_KEY` không lọt ra ngoài.
- Cổng 5173 chuyển tiếp mọi đường dẫn `/api` sang cổng 8000.
- Tệp `.claude/launch.json` có sẵn ba cấu hình (`api`, `web`, `web-preview`) để ứng dụng Claude mở được máy chủ và trình duyệt tích hợp. `web-preview` chạy bản dựng sản xuất ở cổng 4173, dùng để kiểm tra bản dựng.

**Hai lỗi MapLibre GL 6 + Vite đã gặp ngày 04/10, đã sửa trong mã (đừng gỡ):** bản đồ trắng và console báo `Worker failed to load`. MapLibre tìm file worker cạnh chính nó, mà Vite gộp mã vào một tệp. Cách sửa nằm ở `web/src/MapView.tsx` (nhập worker bằng `?worker&url` rồi gọi `setWorkerUrl`) và `worker: { format: "es" }` trong `web/vite.config.ts`. Cả chế độ dev lẫn bản dựng sản xuất đều đã được thử trên trình duyệt.

## 5. Nghiệm thu

Đánh dấu `[x]` là đã thử ngày 04/10/2026; `[ ]` là chưa làm hoặc chưa thử.

- [x] `pytest` đạt 12 kiểm thử của kế hoạch 01 trong môi trường ảo Python 3.12 (toàn bộ hiện là 47 kiểm thử đạt).
- [ ] Repo có nhánh `main` đã đẩy lên và nhánh `web` (việc git do chủ dự án giữ).
- [x] `python -m floodrisk.api.devdata data/sample` tạo dữ liệu cho cả `hcm` và `danang`, có file đánh dấu `SAMPLE`.
- [x] Khi chưa có file `floodrisk/model/evidence.py`, máy chủ vẫn khởi động và `/api/health` ghi cả bốn phần là `fake`. (Kiểm bằng kiểm thử `test_ports_selection.py` và gọi thật `/api/health`.)
- [x] Một module thật có lỗi cú pháp, hoặc thiếu thư viện ngoài, làm máy chủ dừng với lỗi đó, không lùi về bản giả. (Kiểm bằng kiểm thử giả lập lỗi khi nhập, chưa thử bằng file thật đặt vào `floodrisk/model/`.)
- [x] Không file nào trong `src/floodrisk/api/` ngoài `ports.py` có dòng nhập từ `floodrisk.model`, `floodrisk.data` hay `floodrisk.jobs`. Có kiểm thử quét mã nguồn để giữ điều này.
- [x] `tests/api/test_port_contract.py` đạt với bản giả.
- [ ] `python -m floodrisk.api.doctor hcm danang` đạt trên dữ liệu mẫu, và báo lỗi nêu đúng tên cột khi xóa một cột của `scores.parquet`. (Chưa làm; làm cùng lúc nhận file thật, ngày 2–3.)
- [x] Giao diện hiện nhãn "Dữ liệu mẫu" khi chạy trên `data/sample`.

## 6. Không làm

- Không viết lại `evidence.py`, `combine.py`, `scenarios.py` thật. Đó là việc của người AI; bản giả ở đây cố ý đơn giản hơn.
- Không dựng dữ liệu mẫu từ OpenStreetMap. Trường hợp duy nhất được làm: hết ngày 2 mà mạng đường thật của TP.HCM chưa đến, thì tự tải một vùng 5 × 5 km ở trung tâm bằng OSMnx để việc tìm đường không bị chặn (spec 05, mục 9).
- Không thêm biến môi trường để bật tắt bản giả. Việc chọn hoàn toàn tự động theo quy tắc ở mục 2.2.
