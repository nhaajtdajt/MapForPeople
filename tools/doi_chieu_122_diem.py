"""Đối chiếu Mô hình 1 với danh sách 122 điểm ngập của Phòng CSGT TP.HCM (PC08, công bố 06/10/2026).

    python tools/doi_chieu_122_diem.py

Cần repo flood_prediction_models nằm cạnh repo này và đã dựng bảng tuyến
(data/processed/ho_chi_minh/routes.parquet). Chỉ dùng các tuyến có tên: mã của chúng giống nhau trên mọi máy.

Mỗi điểm trong danh sách được định vị bằng tên đường và đường giao nêu trong tin. Vài điểm chỉ có số nhà hoặc
tên chỗ thì lấy đoạn đường quanh một vị trí ước lượng (cột located_by ghi rõ). Kết quả:
- in ra: các điểm đó có nằm trong nhóm 5% / 20% tuyến mô hình chấm nguy cơ cao nhất không, so với chọn bừa
  một tuyến có tên cùng loại đường;
- ghi data/processed/hcm/diem_ngap_pc08_2026-10-06.csv: từng điểm kèm mã các tuyến khớp, để đưa lên bản đồ
  và làm nhãn bổ sung cho mô hình.

Nguồn danh sách: Tuổi Trẻ 06/10/2026,
https://tuoitre.vn/canh-sat-giao-thong-canh-bao-122-diem-ngap-o-tphcm-co-duong-ly-te-xuyen-tran-xuan-soan-10026100617461927.htm
"""
from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import Transformer
from shapely.geometry import LineString, Point
from shapely.ops import nearest_points, unary_union

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT.parent / "flood_prediction_models"
OUT = ROOT / "data" / "processed" / "hcm" / "diem_ngap_pc08_2026-10-06.csv"
CROSS_M = 120       # đường giao cách đường chính không quá chừng này thì coi là giao nhau
AT_CROSS_M = 70     # tuyến của đường chính nằm trong bán kính này quanh chỗ giao thì được lấy
HIT = 0.5           # một điểm tính là "thuộc nhóm" khi từ một nửa chiều dài tuyến khớp nằm trong nhóm


def norm(value) -> str:
    """Chuẩn hóa tên đường đúng như flood_prediction_models/src/floodrisk/records.py."""
    s = str(value or "").replace("Đ", "D").replace("đ", "d").casefold()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = " ".join(s.split())
    return re.sub(r"^(duong|pho)\s+", "", s).strip()


def bands(score: np.ndarray, tie: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Nhóm tuyến như combine.route_bands: 2 = 5% điểm cao nhất, 1 = 15% kế tiếp, tính trong các tuyến được chấm."""
    ids = np.flatnonzero(mask)
    state = np.zeros(len(mask), np.uint8)
    order = np.lexsort((-tie[ids], -score[ids]))
    a = max(1, int(np.ceil(.05 * len(ids))))
    b = max(a, int(np.ceil(.20 * len(ids))))
    state[ids[order[:a]]] = 2
    state[ids[order[a:b]]] = 1
    return state


def pt(lat: float, lon: float):
    return gpd.GeoSeries([Point(lon, lat)], crs=4326).to_crs(32648).iloc[0]


def load() -> gpd.GeoDataFrame:
    S = pd.read_parquet(MODEL / "models" / "final_2025-01-01" / "ho_chi_minh" / "route_susceptibility.parquet")
    scored = S.in_universe.to_numpy() == 1
    everyone = np.ones(len(S), bool)
    for cause in ("rain", "tide"):
        model = S[f"S_{cause}"].to_numpy()
        hybrid = S[f"S_hyb_{cause}"].to_numpy()
        S[f"live_{cause}"] = bands(hybrid, hybrid, everyone)  # như run_hourly.py: điểm có cộng lịch sử, xếp trên mọi tuyến
        S[f"model_{cause}"] = bands(model, model, scored)     # riêng điểm của mô hình, xếp trong các tuyến được chấm
    R = gpd.read_parquet(MODEL / "data" / "processed" / "ho_chi_minh" / "routes.parquet")
    R = R[R.named & R.name_norm.notna()].to_crs(32648)
    R = R.merge(S.drop(columns=["in_universe"]), on="route_id", how="inner")
    return R


NAMED = load()
BY = {k: g for k, g in NAMED.groupby("name_norm")}
CENTER = pt(10.7725, 106.6980)  # chợ Bến Thành
TO_WGS84 = Transformer.from_crs(32648, 4326, always_xy=True).transform


def named(names: str) -> gpd.GeoDataFrame:
    parts = [BY[k] for k in {norm(n) for n in names.split("|")} if k in BY]
    return pd.concat(parts) if parts else NAMED.iloc[:0]


def locate(e: dict) -> tuple[gpd.GeoDataFrame, str, Point | None]:
    """Các tuyến của mô hình ứng với một điểm trong danh sách, cách đã định vị, và một điểm đại diện trên đường."""
    M = named(e["main"])
    if M.empty:
        return M, "không có tên đường này trong vùng mô hình", None
    hint = pt(*e["hint"]) if e.get("hint") else None
    if hint is not None:
        M = M[M.distance(hint) <= e["r"]]
        if M.empty:
            return M, "có tên đường nhưng không ở gần vị trí nêu", None
    kind = e["kind"]
    mu = unary_union(M.geometry.values)
    if kind in ("all", "near"):
        anchor = nearest_points(mu, hint if hint is not None else mu.centroid)[0]
        return M, "cả con đường" if kind == "all" else "đoạn quanh vị trí ước lượng", anchor
    found = []
    for cross in e["cross"]:
        C = named(cross)
        if hint is not None:
            C = C[C.distance(hint) <= e["r"] + 1500]
        if C.empty:
            continue
        a, b = nearest_points(mu, unary_union(C.geometry.values))
        if a.distance(b) <= CROSS_M:
            found.append(a)
    if not found:
        return M.iloc[:0], "không tìm thấy chỗ giao với đường nêu trong tin", None
    if kind == "seg" and len(found) >= 2:
        chord = LineString([found[0], found[1]])
        middle = nearest_points(mu, chord.interpolate(0.5, normalized=True))[0]
        return M[M.distance(chord) <= max(120.0, 0.15 * chord.length)], "đoạn giữa hai đường giao", middle
    near = unary_union([p.buffer(AT_CROSS_M) for p in found])
    return M[M.intersects(near)], "tại chỗ giao" if kind == "x" else "tại một đầu đoạn", found[0]


def E(cause, label, main, kind="all", cross=(), hint=None, r=1500):
    return {"cause": cause, "label": label, "main": main, "kind": kind, "cross": list(cross), "hint": hint, "r": r}


OUTSIDE = "__ngoai_vung__"
VNG = "Võ Nguyên Giáp|Xa lộ Hà Nội|Song hành Xa lộ Hà Nội|Song hành Võ Nguyên Giáp|Đường song hành Võ Nguyên Giáp"
RACH_CHIEC = (10.8086, 106.7563)
ENTRIES = [
    # ---- 83 điểm do mưa ----
    E("rain", "Lý Thường Kiệt, số 387 → Trường Nguyễn Thái Bình", "Lý Thường Kiệt", "near", hint=(10.7885, 106.6530), r=700),
    E("rain", "Ngã tư Bảy Hiền", "Cách Mạng Tháng Tám|Trường Chinh|Hoàng Văn Thụ|Lý Thường Kiệt", "near", hint=(10.7929, 106.6531), r=150),
    E("rain", "Lê Đức Anh - Hồ Học Lãm", "Lê Đức Anh|Quốc lộ 1|Quốc lộ 1A", "x", ["Hồ Học Lãm"]),
    E("rain", "Tỉnh lộ 10, Tên Lửa → Lê Đức Anh", "Tỉnh lộ 10|Đường tỉnh 10|ĐT 10|Tỉnh Lộ 10", "seg", ["Tên Lửa", "Lê Đức Anh|Quốc lộ 1|Quốc lộ 1A"]),
    E("rain", "Trần Đại Nghĩa, số 4 → Lê Khả Phiêu", "Trần Đại Nghĩa", "x", ["Lê Khả Phiêu|Quốc lộ 1|Quốc lộ 1A"]),
    E("rain", "Trần Văn Giàu, số 55 → Vườn Thơm", "Trần Văn Giàu", "x", ["Vườn Thơm"]),
    E("rain", "Vĩnh Lộc, Trần Văn Giàu → Lại Hùng Cường", "Vĩnh Lộc", "seg", ["Trần Văn Giàu", "Lại Hùng Cường"]),
    E("rain", "Võ Văn Vân, số 700–730 (Trục Tổ 7)", "Võ Văn Vân", "x", ["Trục Tổ 7|Tổ 7|Trục tổ 7"]),
    E("rain", "Lê Quang Đạo, Võ Thị Hồi → Nguyễn Thị Sóc", "Lê Quang Đạo|Quốc lộ 22", "seg", ["Võ Thị Hồi", "Nguyễn Thị Sóc"]),
    E("rain", "Lê Quang Đạo - Trần Văn Mười", "Lê Quang Đạo|Quốc lộ 22", "x", ["Trần Văn Mười"]),
    E("rain", "Trần Văn Mười, Lê Quang Đạo → Xuân Thới 2", "Trần Văn Mười", "seg", ["Lê Quang Đạo|Quốc lộ 22", "Xuân Thới 2"]),
    E("rain", "Nguyễn Thị Thử, Võ Thị Hồi → Xuân Thới Sơn 5", "Nguyễn Thị Thử", "seg", ["Võ Thị Hồi", "Xuân Thới Sơn 5"]),
    E("rain", "Song hành quốc lộ 22, Đỗ Mười → Bà Triệu", "Song hành Quốc lộ 22|Song Hành Quốc Lộ 22|Song hành|Đường song hành Quốc lộ 22|Song hành QL22", "seg", ["Đỗ Mười|Quốc lộ 1|Quốc lộ 1A", "Bà Triệu"], hint=(10.8640, 106.6090), r=4000),
    E("rain", "Nguyễn Ảnh Thủ, Lê Quang Đạo → Đồng Tâm", "Nguyễn Ảnh Thủ", "seg", ["Lê Quang Đạo|Quốc lộ 22", "Đồng Tâm"]),
    E("rain", "Bà Triệu, Quang Trung → Song hành", "Bà Triệu", "seg", ["Quang Trung", "Song hành Quốc lộ 22|Song Hành Quốc Lộ 22|Song hành"], hint=(10.8850, 106.5950), r=3000),
    E("rain", "Trưng Nữ Vương, Quang Trung → Đỗ Văn Dậy", "Trưng Nữ Vương", "seg", ["Quang Trung", "Đỗ Văn Dậy"], hint=(10.8880, 106.5930), r=3000),
    E("rain", "Đỗ Mười, trước số 2539/3A (An Phú Đông)", "Đỗ Mười|Quốc lộ 1|Quốc lộ 1A", "near", hint=(10.8600, 106.7040), r=600),
    E("rain", "Đỗ Mười, trước số 139 (Tam Bình)", "Đỗ Mười|Quốc lộ 1|Quốc lộ 1A", "near", hint=(10.8665, 106.7350), r=600),
    E("rain", "Đỗ Mười, hai bên cầu Bình Phước", "Đỗ Mười|Quốc lộ 1|Quốc lộ 1A", "near", hint=(10.8610, 106.7150), r=600),
    E("rain", "Đỗ Mười, trước chợ đầu mối Thủ Đức", "Đỗ Mười|Quốc lộ 1|Quốc lộ 1A", "near", hint=(10.8685, 106.7335), r=600),
    E("rain", "Đỗ Mười - đường 17", "Đỗ Mười|Quốc lộ 1|Quốc lộ 1A", "x", ["số 17|17|Đường 17"], hint=(10.8650, 106.7250), r=3500),
    E("rain", "Hầm chui cầu Bến Cát (Thới An)", OUTSIDE + "khong_dinh_vi"),
    E("rain", "Vòng xoay Bình Phước", "Đỗ Mười|Quốc lộ 1|Quốc lộ 1A|Quốc lộ 13", "x", ["Quốc lộ 13"], hint=(10.8640, 106.7245), r=1200),
    E("rain", "Hai bên ngã tư Bình Phước", "Quốc lộ 13|Đỗ Mười|Quốc lộ 1|Quốc lộ 1A", "x", ["Đỗ Mười|Quốc lộ 1|Quốc lộ 1A"], hint=(10.8640, 106.7245), r=1200),
    E("rain", "Võ Nguyên Giáp, cầu Trắng → điểm quay đầu", VNG, "near", hint=RACH_CHIEC, r=900),
    E("rain", "Võ Nguyên Giáp, điểm quay đầu → cầu Rạch Chiếc", VNG, "near", hint=RACH_CHIEC, r=900),
    E("rain", "Võ Trường Toản × song hành Võ Nguyên Giáp", VNG, "x", ["Võ Trường Toản"]),
    E("rain", "Chân cầu Rạch Chiếc, hướng ra ga metro", VNG, "near", hint=RACH_CHIEC, r=500),
    E("rain", "Tố Hữu - Mai Chí Thọ", "Mai Chí Thọ", "x", ["Tố Hữu"]),
    E("rain", "Mai Chí Thọ - Lương Định Của", "Mai Chí Thọ", "x", ["Lương Định Của"]),
    E("rain", "Mai Chí Thọ, cầu vượt A → Lương Định Của", "Mai Chí Thọ", "x", ["Lương Định Của"]),
    E("rain", "Tô Ngọc Vân × Phạm Văn Đồng", "Tô Ngọc Vân", "x", ["Phạm Văn Đồng"]),
    E("rain", "Tô Ngọc Vân × Linh Đông", "Tô Ngọc Vân", "x", ["Linh Đông"]),
    E("rain", "Tô Ngọc Vân × đường 35", "Tô Ngọc Vân", "x", ["số 35|35|Đường 35"]),
    E("rain", "Phạm Văn Đồng - Linh Đông", "Phạm Văn Đồng", "x", ["Linh Đông"]),
    E("rain", "Số 69 Trịnh Thị Dối (Đông Thạnh)", "Trịnh Thị Dối"),
    E("rain", "Võ Chí Công - đường số 5", "Võ Chí Công", "x", ["số 5|5|Đường số 5"]),
    E("rain", "Thảo Điền - Quốc Hương", "Thảo Điền", "x", ["Quốc Hương"]),
    E("rain", "Đỗ Xuân Hợp - Tây Hòa", "Đỗ Xuân Hợp", "x", ["Tây Hòa"]),
    E("rain", "Đường số 2 (phường Thủ Đức)", "số 2|2", "near", hint=(10.8395, 106.7575), r=900),
    E("rain", "Tạ Quang Bửu, Võ Liêm Sơn → Cao Lỗ", "Tạ Quang Bửu", "seg", ["Võ Liêm Sơn", "Cao Lỗ"]),
    E("rain", "Chợ Thủ Đức", "Kha Vạn Cân", "x", ["Võ Văn Ngân"]),
    E("rain", "Lý Tế Xuyên", "Lý Tế Xuyên"),
    E("rain", "Cổng KCN Sóng Thần", OUTSIDE + "khong_dinh_vi"),
    E("rain", "ĐT743A - Mỹ Phước Tân Vạn", "ĐT743A|ĐT 743A|Đường tỉnh 743A|ĐT.743A|Tỉnh lộ 743A|ĐT743a|ĐT 743a", "x", ["Mỹ Phước - Tân Vạn|Mỹ Phước Tân Vạn|Đường Mỹ Phước - Tân Vạn"]),
    E("rain", "Lê Văn Việt, Đình Phong Phú → Lã Xuân Oai", "Lê Văn Việt", "seg", ["Đình Phong Phú", "Lã Xuân Oai"]),
    E("rain", "Nguyễn Xiển, số 581 → cầu Gò Công", "Nguyễn Xiển", "near", hint=(10.8390, 106.8400), r=1500),
    E("rain", "Quốc lộ 50, Nguyễn Văn Linh → cầu Chánh Hưng", "Quốc lộ 50", "x", ["Nguyễn Văn Linh"]),
    E("rain", "Văn Tiến Dũng", "Văn Tiến Dũng"),
    E("rain", "Nguyễn Văn Tạo, cầu Kênh Lộ → cầu Rạch Chim", "Nguyễn Văn Tạo"),
    E("rain", "Nguyễn Bình - Lê Văn Lương", "Nguyễn Bình", "x", ["Lê Văn Lương"]),
    E("rain", "Huỳnh Tấn Phát - Phú Thuận", "Huỳnh Tấn Phát", "x", ["Phú Thuận"]),
    E("rain", "Nguyễn Văn Linh, trước cầu Ông Lớn (Phạm Hùng → Nguyễn Hữu Thọ)", "Nguyễn Văn Linh", "seg", ["Phạm Hùng", "Nguyễn Hữu Thọ"]),
    E("rain", "Nguyễn Văn Linh, Phạm Văn Nghị → cầu Cả Cấm", "Nguyễn Văn Linh", "x", ["Phạm Văn Nghị"]),
    E("rain", "Đường D1 (Him Lam), D6 → Nguyễn Văn Linh", "D1", "x", ["D6", "Nguyễn Văn Linh"], hint=(10.7420, 106.6990), r=3000),
    E("rain", "Đường D6, Nguyễn Hữu Thọ → D1", "D6", "x", ["Nguyễn Hữu Thọ", "D1"], hint=(10.7420, 106.6990), r=3000),
    E("rain", "Hoàng Trọng Mậu", "Hoàng Trọng Mậu"),
    E("rain", "Đặng Thùy Trâm (Bình Lợi Trung)", "Đặng Thùy Trâm|Đặng Thuỳ Trâm"),
    E("rain", "Ung Văn Khiêm, Nguyễn Gia Trí → Điện Biên Phủ", "Ung Văn Khiêm", "seg", ["Nguyễn Gia Trí", "Điện Biên Phủ"]),
    E("rain", "Nguyễn Văn Khối, Lê Văn Thọ → UBND Thông Tây Hội", "Nguyễn Văn Khối", "x", ["Lê Văn Thọ"]),
    E("rain", "Phạm Thế Hiển, hẻm 2695 → Lê Bôi", "Phạm Thế Hiển", "x", ["Lê Bôi"]),
    E("rain", "Phạm Thế Hiển, chân cầu Bà Tàng", "Phạm Thế Hiển", "x", ["Cầu Bà Tàng|Bà Tàng"]),
    E("rain", "Phan Văn Khải, số 534 (Tân An Hội)", "Phan Văn Khải"),
    E("rain", "Phan Văn Khải, số 437 (Tân An Hội)", "Phan Văn Khải"),
    E("rain", "Phan Văn Khải, số 124 (Củ Chi)", "Phan Văn Khải"),
    E("rain", "ĐT744, An Tây", OUTSIDE + "binh_duong"),
    E("rain", "ĐT744, Rạch Bắp → Bưng Còng", OUTSIDE + "binh_duong"),
    E("rain", "Bùi Thanh Khiết, Nguyễn Hữu Trí → Bình Thuận - Chợ Đệm", "Bùi Thanh Khiết", "x", ["Nguyễn Hữu Trí"]),
    E("rain", "Trịnh Quang Nghị, Nguyễn Văn Linh → cầu Ba Tơ", "Trịnh Quang Nghị", "x", ["Nguyễn Văn Linh"]),
    E("rain", "Mã Lò → Hương lộ 2", "Mã Lò", "x", ["Hương lộ 2|Hương Lộ 2"]),
    E("rain", "Bình Trị Đông - Chiến Lược", "Bình Trị Đông", "x", ["Chiến Lược"]),
] + [E("rain", f"Quốc lộ 51, điểm {i} (Phú Mỹ – Vũng Tàu)", OUTSIDE + "vung_tau") for i in range(1, 7)] + [
    E("rain", "Lê Hồng Phong nối dài (Vũng Tàu)", OUTSIDE + "vung_tau"),
    E("rain", "Đường 30-4 (Vũng Tàu)", OUTSIDE + "vung_tau"),
    E("rain", "Đường 2-9 (Vũng Tàu)", OUTSIDE + "vung_tau"),
    E("rain", "Nguyễn An Ninh (Vũng Tàu)", OUTSIDE + "vung_tau"),
    E("rain", "Trương Công Định (Vũng Tàu)", OUTSIDE + "vung_tau"),
    E("rain", "Nguyễn Tất Thành (Long Hải)", OUTSIDE + "vung_tau"),
    # ---- 39 điểm do triều ----
    E("tide", "Lê Khả Phiêu (song hành), Hưng Nhơn → Dương Đình Cúc", "Lê Khả Phiêu|Quốc lộ 1|Quốc lộ 1A|Song hành Quốc lộ 1|Song hành Lê Khả Phiêu", "seg", ["Hưng Nhơn", "Dương Đình Cúc"]),
    E("tide", "Lê Khả Phiêu × Hoàng Đạo Thúy", "Lê Khả Phiêu|Quốc lộ 1|Quốc lộ 1A", "x", ["Hoàng Đạo Thúy"]),
    E("tide", "Bến Nghé, số 4 (Tân Thuận)", "Bến Nghé", "all", hint=(10.7560, 106.7290), r=2500),
    E("tide", "Trần Xuân Soạn, Huỳnh Tấn Phát → Lâm Văn Bền", "Trần Xuân Soạn", "seg", ["Huỳnh Tấn Phát", "Lâm Văn Bền"]),
    E("tide", "Nguyễn Thị Thập - Tân Mỹ", "Nguyễn Thị Thập", "x", ["Tân Mỹ"]),
    E("tide", "Nguyễn Thị Thập - Lê Văn Lương", "Nguyễn Thị Thập", "x", ["Lê Văn Lương"]),
    E("tide", "Lê Văn Lương, đoạn qua xã Nhà Bè", "Lê Văn Lương", "seg", ["Phạm Hữu Lầu", "Nguyễn Bình"]),
    E("tide", "Lê Văn Lương, trước cầu Rạch Tôm", "Lê Văn Lương", "seg", ["Phạm Hữu Lầu", "Nguyễn Bình"]),
    E("tide", "Huỳnh Tấn Phát × Phạm Hữu Lầu", "Huỳnh Tấn Phát", "x", ["Phạm Hữu Lầu"]),
    E("tide", "Huỳnh Tấn Phát × Hoàng Quốc Việt", "Huỳnh Tấn Phát", "x", ["Hoàng Quốc Việt"]),
    E("tide", "Nguyễn Lương Bằng × Hoàng Quốc Việt", "Nguyễn Lương Bằng", "x", ["Hoàng Quốc Việt"]),
    E("tide", "Nguyễn Lương Bằng × Phạm Hữu Lầu", "Nguyễn Lương Bằng", "x", ["Phạm Hữu Lầu"]),
    E("tide", "Phạm Hữu Lầu, Huỳnh Tấn Phát → cầu Phước Long", "Phạm Hữu Lầu", "seg", ["Huỳnh Tấn Phát", "Nguyễn Lương Bằng"]),
    E("tide", "Nguyễn Hữu Thọ, Phạm Hữu Lầu → cầu Rạch Dĩa 2", "Nguyễn Hữu Thọ", "x", ["Phạm Hữu Lầu"]),
    E("tide", "Nguyễn Bình, Huỳnh Tấn Phát → cầu Mương Chuối", "Nguyễn Bình", "x", ["Huỳnh Tấn Phát"]),
    E("tide", "Lê Thị Tám (Hiệp Phước)", "Lê Thị Tám"),
    E("tide", "Nguyễn Văn Quỳ, hai bên cầu Phú Mỹ", "Nguyễn Văn Quỳ"),
    E("tide", "Gò Công (Chợ Lớn)", "Gò Công", "all", hint=(10.7495, 106.6510), r=1500),
    E("tide", "Phan Phú Tiên", "Phan Phú Tiên"),
    E("tide", "Võ Văn Kiệt, Phạm Phú Thứ → Bình Tiên", "Võ Văn Kiệt", "seg", ["Phạm Phú Thứ", "Bình Tiên"]),
    E("tide", "Phạm Phú Thứ, Võ Văn Kiệt → Phạm Văn Chí", "Phạm Phú Thứ", "seg", ["Võ Văn Kiệt", "Phạm Văn Chí"]),
    E("tide", "Song Hành Lớn (Bình Phú)", "Song Hành|Song Hành Lớn|Song hành", "all", hint=(10.7440, 106.6290), r=1500),
    E("tide", "Trần Văn Kiểu - đường 32", "Trần Văn Kiểu", "x", ["số 32|32|Đường số 32"]),
    E("tide", "Chân cầu Lò Gốm", "Võ Văn Kiệt", "x", ["Lò Gốm|Bến Lò Gốm"]),
    E("tide", "Mai Xuân Thưởng (quận 6 cũ)", "Mai Xuân Thưởng", "all", hint=(10.7480, 106.6470), r=1500),
    E("tide", "Cao Đạt", "Cao Đạt"),
    E("tide", "An Bình (quận 5 cũ)", "An Bình", "all", hint=(10.7530, 106.6720), r=1200),
    E("tide", "Nguyễn Biểu", "Nguyễn Biểu"),
    E("tide", "Trần Hưng Đạo, Nguyễn Biểu → Nguyễn Tri Phương", "Trần Hưng Đạo", "seg", ["Nguyễn Biểu", "Nguyễn Tri Phương"]),
    E("tide", "Phạm Thế Hiển (cả đường)", "Phạm Thế Hiển"),
    E("tide", "Dương Bá Trạc", "Dương Bá Trạc"),
    E("tide", "Chân cầu Rạch Chiếc (làn xe máy)", VNG, "near", hint=RACH_CHIEC, r=500),
    E("tide", "Mai Chí Thọ, trước chung cư New City", "Mai Chí Thọ", "near", hint=(10.7790, 106.7440), r=700),
    E("tide", "R12, chân cầu Ba Son", "R12"),
    E("tide", "Nguyễn Văn Hưởng", "Nguyễn Văn Hưởng"),
    E("tide", "Nguyễn Duy Trinh, cây xăng Kim Long 813 (Long Trường)", "Nguyễn Duy Trinh", "near", hint=(10.7975, 106.8150), r=1200),
    E("tide", "Liên Phường - Bưng Ông Thoàn", "Liên Phường", "x", ["Bưng Ông Thoàn"]),
    E("tide", "Bờ kè lô F, cư xá Thanh Đa", OUTSIDE + "khong_dinh_vi"),
    E("tide", "Hà Huy Giáp (An Phú Đông)", "Hà Huy Giáp"),
]
assert sum(e["cause"] == "rain" for e in ENTRIES) == 83 and sum(e["cause"] == "tide" for e in ENTRIES) == 39


WHY_NOT = {"vung_tau": "ngoài vùng mô hình (Bà Rịa – Vũng Tàu cũ)", "binh_duong": "ngoài vùng mô hình (Bình Dương cũ)",
           "khong_dinh_vi": "không phải tên đường, chưa định vị"}


def evaluate() -> pd.DataFrame:
    rows = []
    for no, e in enumerate(ENTRIES, 1):
        c = e["cause"]
        row = {"no": no, "cause": c, "place": e["label"], "kind": e["kind"], "n_routes": 0}
        if e["main"].startswith(OUTSIDE):
            rows.append({**row, "located_by": WHY_NOT[e["main"][len(OUTSIDE):]]})
            continue
        M, how, point = locate(e)
        U = M[M.in_universe] if len(M) else M
        row.update(located_by=how, n_routes=len(U))
        if len(U):
            L = U.length_m.to_numpy()
            w = L / L.sum()
            share = lambda flag: round(float((w * flag).sum()), 3)  # noqa: E731
            lon, lat = TO_WGS84(point.x, point.y)
            row.update(lon=round(lon, 6), lat=round(lat, 6), km=round(L.sum() / 1000, 2), road_class=U.highway_class.mode().iloc[0],
                       dist_center_km=round(float(unary_union(U.geometry.values).centroid.distance(CENTER) / 1000), 1),
                       in_model_history=share(U.H_any.to_numpy() > 0),
                       live_high=share(U[f"live_{c}"].to_numpy() == 2), live_coloured=share(U[f"live_{c}"].to_numpy() >= 1),
                       model_top5=share(U[f"model_{c}"].to_numpy() == 2), model_top20=share(U[f"model_{c}"].to_numpy() >= 1),
                       route_ids=";".join(U.route_id))
        rows.append(row)
    return pd.DataFrame(rows)


def report(T: pd.DataFrame) -> None:
    L = T[T.n_routes > 0]
    print(f"định vị được {len(L)}/122 điểm trên tuyến có tên của mô hình ({(L.cause == 'rain').sum()} do mưa, {(L.cause == 'tide').sum()} do triều); "
          f"{T.located_by.str.startswith('ngoài vùng').sum()} điểm ngoài vùng mô hình; "
          f"{(L.kind == 'near').sum()} điểm định vị ước lượng; {(L.in_model_history == 0).sum()} điểm chưa có ghi nhận ngập nào trong dữ liệu mô hình")
    U = NAMED[NAMED.in_universe]
    length = U.groupby("highway_class").length_m.sum()

    def chance(column: str, floor: int, classes: pd.Series) -> float:
        """Tỉ lệ chiều dài tuyến có tên cùng loại đường nằm trong nhóm: mức trúng nếu chọn bừa."""
        inside = U[U[column] >= floor].groupby("highway_class").length_m.sum().reindex(length.index, fill_value=0)
        return float((inside / length)[classes].mean())

    # (cột nhóm trong bảng tuyến, hai cột kết quả, tên hai nhóm)
    measures = (("BẢN CHẠY MỖI GIỜ (run_hourly.py: 7.012 tuyến mức cao và 21.036 tuyến mức vừa khi báo động)",
                 "live", "live_high", "live_coloured", "mức cao", "có màu"),
                ("RIÊNG ĐIỂM CỦA MÔ HÌNH (không cộng lịch sử, xếp trong 66.017 tuyến được chấm)",
                 "model", "model_top5", "model_top20", "nhóm 5%", "nhóm 20%"))
    for title, key, narrow, wide, narrow_vi, wide_vi in measures:
        print(f"\n{title}")
        for c, vi in (("rain", "mưa"), ("tide", "triều")):
            sub = L[L.cause == c]
            column = f"{key}_{c}"
            print(f" Ngập do {vi}, {len(sub)} điểm. Chọn bừa tuyến có tên cùng loại đường: {narrow_vi} khoảng "
                  f"{chance(column, 2, sub.road_class):.0%}, {wide_vi} khoảng {chance(column, 1, sub.road_class):.0%}.")
            groups = (("tất cả", sub), ("trong 10 km quanh chợ Bến Thành", sub[sub.dist_center_km <= 10]),
                      ("xa hơn 10 km", sub[sub.dist_center_km > 10]), ("định vị bằng đường giao", sub[sub.kind.isin(["x", "seg"])]),
                      ("chưa có trong dữ liệu mô hình", sub[sub.in_model_history == 0]))
            for name, g in groups:
                if len(g):
                    print(f"   {name:32s} {len(g):2d} điểm | {narrow_vi}: {(g[narrow] >= HIT).sum():2d} ({(g[narrow] >= HIT).mean():.0%}) | "
                          f"{wide_vi}: {(g[wide] >= HIT).sum():2d} ({(g[wide] >= HIT).mean():.0%}) | chọn bừa: "
                          f"{chance(column, 2, g.road_class):.0%} và {chance(column, 1, g.road_class):.0%}")
            miss = sub[sub[wide] < HIT]
            print(f"   không {wide_vi}: " + "; ".join(f"{r.place} ({r.dist_center_km:.0f} km)" for r in miss.itertuples()))
    left = T[(T.n_routes == 0) & ~T.located_by.str.startswith("ngoài vùng")]
    print("\nchưa định vị được: " + "; ".join(f"{r.place} [{r.located_by}]" for r in left.itertuples()))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    table = evaluate()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    table.drop(columns=["kind"]).to_csv(OUT, index=False, encoding="utf-8-sig")
    report(table)
    print(f"\nđã ghi {OUT.relative_to(ROOT)} ({len(table)} dòng)")
