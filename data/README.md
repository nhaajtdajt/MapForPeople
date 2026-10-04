# Dữ liệu của dự án

Tệp này được sinh tự động bởi `python -m floodrisk.api.inventory`. Đừng sửa tay; chạy lại lệnh khi có file mới.

## Đọc cho đúng: thật hay mẫu

| Thư mục | Là gì | Dùng để |
|---|---|---|
| `data/processed/` | **DỮ LIỆU THẬT** do người dữ liệu và người AI giao | Chạy sản phẩm thật, đo, trình diễn |
| `data/sample/processed/` | **DỮ LIỆU MẪU, GIẢ.** Tám đường tưởng tượng mỗi thành phố, sinh bằng lệnh | Phát triển khi file thật chưa đến. Không dùng làm bằng chứng cho bất cứ điều gì |

Hai nơi không bao giờ trộn file với nhau. Máy chủ chọn nơi nào theo biến `FLOODRISK_DATA` (`data` là thật, `data/sample` là mẫu). `/api/health` ghi `data: real` hay `data: sample`.

Cập nhật lúc 21:18 04/10/2026.

## Dữ liệu thật (`data/processed/`)

### TP. Hồ Chí Minh (`hcm`)

| File | Ai giao | Trạng thái | Số dòng | Dung lượng | Sửa lần cuối |
|---|---|---|---|---|---|
| `hcm/units.parquet` | Dữ liệu | có | 43.352 | 6.5 MB | 04/10/2026 |
| `hcm/observations.parquet` | Dữ liệu | **thiếu** | — | — | — |
| `hcm/obs_units.parquet` | Dữ liệu | **thiếu** | — | — | — |
| `hcm/graph_nodes.parquet` | Dữ liệu | có | 120.120 | 3.1 MB | 04/10/2026 |
| `hcm/graph_edges.parquet` | Dữ liệu | có | 272.052 | 17.3 MB | 04/10/2026 |
| `hcm/edge_units.parquet` | Dữ liệu | có | 148.662 | 2.7 MB | 04/10/2026 |
| `hcm/rain_cells.parquet` | Dữ liệu | **thiếu** | — | — | — |
| `hcm/rain_daily.parquet` | Dữ liệu | **thiếu** | — | — | — |
| `hcm/scores.parquet` | AI | **thiếu** | — | — | — |
| `hcm/risk.parquet` | AI | **thiếu** | — | — | — |
| `hcm/model/trigger.json` | AI | **thiếu** | — | — | — |
| `hcm/replay/index.json` | AI | **thiếu** | — | — | — |

Có 4/12 file.

### Đà Nẵng (`danang`)

| File | Ai giao | Trạng thái | Số dòng | Dung lượng | Sửa lần cuối |
|---|---|---|---|---|---|
| `danang/units.parquet` | Dữ liệu | **thiếu** | — | — | — |
| `danang/observations.parquet` | Dữ liệu | **thiếu** | — | — | — |
| `danang/obs_units.parquet` | Dữ liệu | **thiếu** | — | — | — |
| `danang/graph_nodes.parquet` | Dữ liệu | **thiếu** | — | — | — |
| `danang/graph_edges.parquet` | Dữ liệu | **thiếu** | — | — | — |
| `danang/edge_units.parquet` | Dữ liệu | **thiếu** | — | — | — |
| `danang/rain_cells.parquet` | Dữ liệu | **thiếu** | — | — | — |
| `danang/rain_daily.parquet` | Dữ liệu | **thiếu** | — | — | — |
| `danang/scores.parquet` | AI | **thiếu** | — | — | — |
| `danang/risk.parquet` | AI | **thiếu** | — | — | — |
| `danang/model/trigger.json` | AI | **thiếu** | — | — | — |
| `danang/replay/index.json` | AI | **thiếu** | — | — | — |

Chưa có thư mục này.

### Dùng chung cho mọi thành phố

| File | Ai giao | Trạng thái | Số dòng | Dung lượng | Sửa lần cuối |
|---|---|---|---|---|---|
| `model_choice.json` | AI | **thiếu** | — | — | — |
| `tide_daily.parquet` | AI | **thiếu** | — | — | — |
| `tide_coef.joblib` | AI | **thiếu** | — | — | — |

## Dữ liệu mẫu, giả (`data/sample/processed/`)

> Mọi file dưới đây là giả. Chúng chỉ tồn tại để phần web chạy được khi file thật chưa đến.

### TP. Hồ Chí Minh (`hcm`)

| File | Ai giao | Trạng thái | Số dòng | Dung lượng | Sửa lần cuối |
|---|---|---|---|---|---|
| `hcm/units.parquet` | Dữ liệu | có | 8 | 0.0 MB | 04/10/2026 |
| `hcm/observations.parquet` | Dữ liệu | có | 21 | 0.0 MB | 04/10/2026 |
| `hcm/obs_units.parquet` | Dữ liệu | có | 21 | 0.0 MB | 04/10/2026 |
| `hcm/graph_nodes.parquet` | Dữ liệu | có | 16 | 0.0 MB | 04/10/2026 |
| `hcm/graph_edges.parquet` | Dữ liệu | có | 48 | 0.0 MB | 04/10/2026 |
| `hcm/edge_units.parquet` | Dữ liệu | có | 48 | 0.0 MB | 04/10/2026 |
| `hcm/rain_cells.parquet` | Dữ liệu | có | 1 | 0.0 MB | 04/10/2026 |
| `hcm/rain_daily.parquet` | Dữ liệu | **thiếu** | — | — | — |
| `hcm/scores.parquet` | AI | có | 8 | 0.0 MB | 04/10/2026 |
| `hcm/risk.parquet` | AI | có | 24 | 0.0 MB | 04/10/2026 |
| `hcm/model/trigger.json` | AI | có |  | 0.0 MB | 04/10/2026 |
| `hcm/replay/index.json` | AI | có | 2 kịch bản | 0.0 MB | 04/10/2026 |

Có 11/12 file.

### Đà Nẵng (`danang`)

| File | Ai giao | Trạng thái | Số dòng | Dung lượng | Sửa lần cuối |
|---|---|---|---|---|---|
| `danang/units.parquet` | Dữ liệu | có | 8 | 0.0 MB | 04/10/2026 |
| `danang/observations.parquet` | Dữ liệu | có | 21 | 0.0 MB | 04/10/2026 |
| `danang/obs_units.parquet` | Dữ liệu | có | 21 | 0.0 MB | 04/10/2026 |
| `danang/graph_nodes.parquet` | Dữ liệu | có | 16 | 0.0 MB | 04/10/2026 |
| `danang/graph_edges.parquet` | Dữ liệu | có | 48 | 0.0 MB | 04/10/2026 |
| `danang/edge_units.parquet` | Dữ liệu | có | 48 | 0.0 MB | 04/10/2026 |
| `danang/rain_cells.parquet` | Dữ liệu | có | 1 | 0.0 MB | 04/10/2026 |
| `danang/rain_daily.parquet` | Dữ liệu | **thiếu** | — | — | — |
| `danang/scores.parquet` | AI | có | 8 | 0.0 MB | 04/10/2026 |
| `danang/risk.parquet` | AI | có | 24 | 0.0 MB | 04/10/2026 |
| `danang/model/trigger.json` | AI | có |  | 0.0 MB | 04/10/2026 |
| `danang/replay/index.json` | AI | có | 2 kịch bản | 0.0 MB | 04/10/2026 |

Có 11/12 file.

### Dùng chung cho mọi thành phố

| File | Ai giao | Trạng thái | Số dòng | Dung lượng | Sửa lần cuối |
|---|---|---|---|---|---|
| `model_choice.json` | AI | có |  | 0.0 MB | 04/10/2026 |
| `tide_daily.parquet` | AI | **thiếu** | — | — | — |
| `tide_coef.joblib` | AI | **thiếu** | — | — | — |
