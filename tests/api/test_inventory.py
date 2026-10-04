from floodrisk.api import inventory
from floodrisk.api.devdata import make_dev_data


def test_inventory_separates_real_from_sample_and_counts_rows(tmp_path):
    real = tmp_path / "data"
    sample = real / "sample"
    make_dev_data(sample)
    # "dữ liệu thật" chỉ có mạng đường, lấy từ bộ mẫu để có file thật sự
    (real / "processed" / "hcm").mkdir(parents=True)
    (real / "processed" / "hcm" / "units.parquet").write_bytes((sample / "processed" / "hcm" / "units.parquet").read_bytes())

    text = inventory.build(real, sample)
    real_part, sample_part = text.split("## Dữ liệu mẫu, giả")

    assert "DỮ LIỆU THẬT" in text and "DỮ LIỆU MẪU, GIẢ" in text
    # phần thật: units có, mọi thứ khác thiếu, Đà Nẵng chưa có thư mục
    assert "| `hcm/units.parquet` | Dữ liệu | có | 8 |" in real_part
    assert "| `hcm/scores.parquet` | AI | **thiếu**" in real_part
    assert "Chưa có thư mục này." in real_part
    # phần mẫu: đủ file, có đếm kịch bản
    assert "| `hcm/rain_daily.parquet` | Dữ liệu | **thiếu**" in sample_part  # bộ mẫu không có mưa theo ngày
    assert "| `hcm/replay/index.json` | AI | có | 2 kịch bản |" in sample_part
    assert "giả" in sample_part
    assert "| `hcm/graph_edges.parquet` | Dữ liệu | có | 48 |" in sample_part
