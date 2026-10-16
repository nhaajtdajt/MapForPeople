"""Dựng dữ liệu "Xem lại các trận ngập": bản đồ lúc đó tô gì (chạy lại bằng đúng quy tắc đang dùng), chỗ ngập thật theo báo chí
hoặc camera, chỗ nào app báo đúng, chỗ nào sót, và dự đoán ở mỗi chỗ dựa trên cơ sở nào.

    python tools/dung_lich_su_ngap.py

Không chỉnh quy tắc cho khớp các trận này: mọi ngưỡng lấy từ src/floodrisk/live (local.py, radar.py) như bản đang chạy.
Ghi data/processed/hcm/lich_su_ngap.json (máy chủ phục vụ ở /api/history). Cần các ảnh radar bộ ghi đã lưu ở data/raw/live.

Nguồn số liệu từng trận:
- 01/10, 06/10, 07/10: giờ mưa lớn nhất của từng trạm trong ngày, chép từ cổng vndms ngày 08/10 (cổng chỉ giữ 7 ngày);
  không có ảnh radar. Dùng giờ lớn nhất của mọi trạm cùng lúc nên là cận trên của những gì app thấy trong ngày.
- 08/10 và 15/10: số đo từng giờ của 44 trạm và ảnh radar đã lưu, chạy lại đúng giờ đó.
- 11/10: số đo thật ở Phú An lúc đỉnh triều.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from floodrisk import config  # noqa: E402
from floodrisk.live import hydro, local, radar  # noqa: E402
from floodrisk.model import levels  # noqa: E402
from floodrisk.model.live import CityModel  # noqa: E402

VN = timezone(timedelta(hours=7))
LIVE = ROOT / "data" / "raw" / "live"
LEVEL_WORD = {0: "không tô", 1: "vàng (có thể ngập)", 2: "đỏ (nguy cơ cao)"}

model = CityModel("hcm")
routes = model.routes
LAT, LON = routes.lat.to_numpy(float), routes.lon.to_numpy(float)
NAMES = routes["name"].map(lambda x: unicodedata.normalize("NFC", x).lower().strip() if isinstance(x, str) else "").to_numpy()
BAND_RAIN = model.bands_rain
GAUGES = {g["name"]: g for g in hydro.rain_gauges()}


def km(lat, lon, lat0, lon0):
    return np.hypot((np.asarray(lon) - lon0) * 109.5, (np.asarray(lat) - lat0) * 110.5)


def segments(name: str, box: tuple[float, float, float, float]) -> np.ndarray:
    s, n, w, e = box
    key = unicodedata.normalize("NFC", name).lower()
    return np.flatnonzero(np.isin(NAMES, [key, "đường " + key]) & (LAT >= s) & (LAT <= n) & (LON >= w) & (LON <= e))


def band_word(row: int) -> str:
    return {2: "nhóm 5% đường dễ ngập nhất do mưa", 1: "nhóm 20% đường dễ ngập do mưa", 0: "nhóm ít ngập do mưa"}[int(BAND_RAIN[row])]


def tide_rank_word(row: int) -> str:
    share = (model.tide_order[row] + 1) / len(model.tide_order)
    return f"đứng trong {max(1, round(share * 100))}% đường dễ ngập nhất do triều"


# ---------------- mưa: số đo trạm + radar -> trạng thái từng tuyến, kèm nguồn ----------------

def rain_state(stations: list[dict], rate: np.ndarray | None):
    """stations: [{name, lat, lon, mm1, mm3}]. Trả (trạng thái mưa từng tuyến, trạng thái theo trạm, theo radar, giá trị radar)."""
    gauge_state = np.zeros(len(routes), np.uint8)
    for st in stations:
        st["state"] = local.gauge_state_of(st["mm1"], st["mm3"])
        if st["state"]:
            near = km(LAT, LON, st["lat"], st["lon"]) * 1000 <= local.RADIUS_M
            gauge_state[near] = np.maximum(gauge_state[near], st["state"])
    radar_state = np.zeros(len(routes), np.uint8)
    radar_value = np.zeros(len(routes), np.float32)
    if rate is not None:
        radar_state = radar.states_at(LAT, LON, rate)
        radar_state[BAND_RAIN == 0] = 0
        e = (LON - radar.SITE[1]) * 111.32 * np.cos(np.radians(radar.SITE[0]))
        n = (LAT - radar.SITE[0]) * 110.54
        c = rate.shape[0] // 2
        col = np.clip(np.round(c + e / radar.KM_PER_PX).astype(int) + radar.SHIFT_PX[0], 0, rate.shape[1] - 1)
        row = np.clip(np.round(c - n / radar.KM_PER_PX).astype(int) + radar.SHIFT_PX[1], 0, rate.shape[0] - 1)
        radar_value = rate[row, col]
    return np.maximum(gauge_state, radar_state), gauge_state, radar_state, radar_value


def rain_basis(row: int, level: int, stations, gauge_state, radar_state, radar_value, has_radar: bool) -> list[str]:
    """Vì sao tuyến này có (hay không có) màu."""
    lines = []
    d = {st["name"]: float(km(LAT[row], LON[row], st["lat"], st["lon"])) for st in stations}
    nearest = min(stations, key=lambda st: d[st["name"]]) if stations else None
    trig = [st for st in stations if st["state"] and d[st["name"]] * 1000 <= local.RADIUS_M]
    if trig:
        st = max(trig, key=lambda s: (s["state"], s["mm1"]))
        lines.append(f"Trạm {st['name']} cách {d[st['name']]:.1f} km đo {st['mm1']:g} mm trong một giờ"
                     + (f" ({st['mm3']:g} mm trong 3 giờ)" if st["mm3"] > st["mm1"] else "") + ": "
                     f"{'báo động (từ 35 mm/giờ)' if st['state'] == 2 else 'cảnh giác (từ 30 mm/giờ)'}, áp cho đường trong {local.RADIUS_M / 1000:g} km.")
    elif nearest is not None:
        lines.append(f"Trạm đo gần nhất ({nearest['name']}, cách {d[nearest['name']]:.1f} km) chỉ đo {nearest['mm1']:g} mm trong một giờ: "
                     f"{'dưới ngưỡng cảnh giác 30 mm/giờ' if nearest['mm1'] < 30 else f'nhưng ở xa hơn {local.RADIUS_M / 1000:g} km'}.")
    if has_radar:
        v = float(radar_value[row])
        if radar_state[row]:
            lines.append(f"Radar Nhà Bè thấy mưa khoảng {v:.0f} mm/giờ ngay tại đây (trung bình một giờ, đã trừ nhiễu): "
                         f"{'báo động (từ 35)' if radar_state[row] == 2 else 'cảnh giác (từ 20)'}.")
        else:
            lines.append(f"Radar thấy khoảng {v:.0f} mm/giờ tại đây, dưới ngưỡng cảnh giác 20.")
    else:
        lines.append("Ngày này không còn ảnh radar để xét.")
    lines.append(f"Mô hình 1 xếp đoạn này vào {band_word(row)}" + (
        ": khi mưa ở mức cảnh giác chỉ nhóm 5% được tô vàng; báo động thì nhóm 5% đỏ, nhóm 20% vàng." if level or gauge_state[row] or radar_state[row] else "."))
    return lines


def rain_event(eid, title, when, stations, rate, truth, sources, note, kind="flood"):
    state, gauge_state, radar_state, radar_value = rain_state(stations, rate)
    level = levels.cause_levels(BAND_RAIN, state)
    return finish(eid, "rain", title, when, level, truth, sources, note,
                  # chỉ nêu trạm có đường nằm trong bán kính của nó (bỏ trạm ở Long An, Bà Rịa không tô đường nào trong thành phố)
                  basis=[f"Trạm {s['name']}: {s['mm1']:g} mm/giờ ({'báo động' if s['state'] == 2 else 'cảnh giác'})" for s in stations
                         if s["state"] and (level[km(LAT, LON, s["lat"], s["lon"]) * 1000 <= local.RADIUS_M] > 0).any()]
                  + ([f"Radar: {int((radar_state == 1).sum())} đoạn cảnh giác, {int((radar_state == 2).sum())} đoạn báo động"] if rate is not None else []),
                  why=lambda row: rain_basis(row, int(level[row]), stations, gauge_state, radar_state, radar_value, rate is not None),
                  kind=kind)


# ---------------- triều ----------------

def tide_event(eid, title, when, level_m, truth, sources, note):
    extent = local.tide_extent_of(level_m)
    level = levels.extent_levels(model.tide_order, extent)
    red, coloured = levels.extent_counts(len(level), extent)

    def why(row):
        level_text = f"{level_m:.2f}".replace(".", ",")
        return [f"Phú An đo {level_text} m lúc đỉnh triều (báo động 3 từ 1,60 m): ở mực nước này bản đồ tô đỏ {red:,} và vàng tới {coloured:,} đoạn dễ ngập nhất do triều.".replace(",", ".").replace(level_text.replace(",", "."), level_text).replace("1.60 m", "1,60 m"),
                f"Mô hình 1: đoạn này {tide_rank_word(row)}."]
    return finish(eid, "tide", title, when, level, truth, sources, note,
                  basis=[f"Mực nước Phú An {level_m:.2f} m".replace(".", ","), f"Tô đỏ {red:,} đoạn; có màu {coloured:,} đoạn".replace(",", ".")], why=why,
                  tide_extent={"red": red, "coloured": coloured})


# ---------------- gộp kết quả ----------------

def finish(eid, cause, title, when, level, truth, sources, note, basis, why, kind="flood", tide_extent=None):
    drawn = {int(i) for i in np.flatnonzero((model.bands_rain > 0) | (model.bands_tide > 0))}
    # Triều: web tô theo thứ hạng triều (thuộc tính pt của lớp bản đồ), không cần gửi từng tuyến.
    predicted = [] if tide_extent else [[int(i), int(level[i])] for i in np.flatnonzero(level > 0) if int(i) in drawn]
    places = []
    for item in truth:
        rows = item["rows"]
        if not len(rows):
            print(f"  bỏ {item['name']}: không tìm thấy trong bảng tuyến")
            continue
        lv = level[rows]
        best = rows[int(np.argmax(lv))] if lv.max() > 0 else rows[int(np.argmin(km(LAT[rows], LON[rows], np.median(LAT[rows]), np.median(LON[rows]))))]
        if kind == "flood":
            result = "hit" if lv.max() > 0 else "miss"
        else:  # chỗ camera thấy không ngập
            result = "false_alarm" if lv.max() > 0 else "quiet_ok"
        places.append({
            "name": item["name"], "lat": round(float(LAT[best]), 6), "lon": round(float(LON[best]), 6),
            "observed": item["observed"], "result": result, "level": int(lv.max()),
            "segments": {"total": int(len(rows)), "coloured": int((lv > 0).sum()), "red": int((lv == 2).sum())},
            "shown": f"App tô {LEVEL_WORD[int(lv.max())]} ở {int((lv > 0).sum())}/{len(rows)} đoạn của đường này" if lv.max() > 0 else "App không tô đoạn nào của đường này",
            "basis": why(int(best)),
        })
    flood = [p for p in places if p["result"] in ("hit", "miss")]
    dry = [p for p in places if p["result"] in ("false_alarm", "quiet_ok")]
    summary = {"hit": sum(p["result"] == "hit" for p in flood), "miss": sum(p["result"] == "miss" for p in flood),
               "false_alarm": sum(p["result"] == "false_alarm" for p in dry), "quiet_ok": sum(p["result"] == "quiet_ok" for p in dry),
               "red": int((level == 2).sum()), "yellow": int((level == 1).sum())}
    print(f"{eid}: {summary}")
    decimal = lambda text: re.sub(r"(\d)\.(\d)(?!\d)", lambda m: m.group(1) + "," + m.group(2), text)  # noqa: E731  (1.3 km -> 1,3 km; 7.012 giữ nguyên)
    basis = [decimal(line) for line in basis]
    for place in places:
        place["basis"] = [decimal(line) for line in place["basis"]]
    return {"id": eid, "cause": cause, "title": title, "when": when, "note": note, "basis": basis, "sources": sources,
            "summary": summary, "predicted": predicted, "tide_extent": tide_extent, "places": places}


def truth_streets(items, observed):
    return [{"name": name, "rows": segments(name, box), "observed": observed} for name, box in items]


def stations_from_max(values: dict[str, float]):
    out = []
    for name, mm in values.items():
        g = GAUGES[name]
        out.append({"name": name, "lat": g["lat"], "lon": g["lon"], "mm1": mm, "mm3": mm})
    return out


def stations_at(day_dir: str, end: datetime):
    """Số đo từng trạm tại giờ `end` (mưa 1 giờ, mưa 3 giờ lớn nhất trong 6 giờ qua).

    Lấy từ cổng vndms nếu cổng còn giữ ngày đó (7 ngày), không thì từ hydro.jsonl bộ ghi đã lưu.
    """
    out = []
    if datetime.now(VN) - end < timedelta(days=6):
        for g in GAUGES.values():
            inp = local.gauge_inputs(hydro._series(g["id"], g["source"], 7), end)
            if inp:
                out.append({"name": g["name"], "lat": g["lat"], "lon": g["lon"], "mm1": inp["last_1h_mm"], "mm3": inp["max_3h_mm"]})
        return out
    rows = [json.loads(line) for line in open(LIVE / day_dir / "hydro.jsonl", encoding="utf-8")]
    rec = min((r for r in rows if datetime.fromisoformat(r["at"]) >= end), key=lambda r: datetime.fromisoformat(r["at"]), default=rows[-1])
    for g in rec["gauges"]:
        hours = [(datetime.fromisoformat(t), float(v)) for t, v in g["hours"]]
        inp = local.gauge_inputs(hours, end)
        if inp:
            out.append({"name": g["name"], "lat": g["lat"], "lon": g["lon"], "mm1": inp["last_1h_mm"], "mm3": inp["max_3h_mm"]})
    return out


def radar_rate(day_dir: str, end: datetime):
    files = sorted((LIVE / day_dir / "radar").glob("NHB_*.png"))
    frames = [(radar.image_time(p), radar.levels(p)) for p in files if radar.image_time(p) <= end.astimezone(timezone.utc)]
    return radar.held_rate(frames, end.astimezone(timezone.utc), radar.dry_background())


def main() -> None:
    events = []
    events.append(rain_event(
        "mua-2026-10-15", "Mưa dông chiều 15/10", "15/10/2026, 13:40",
        stations_at("2026-10-15", datetime(2026, 10, 15, 13, 40, tzinfo=VN)) if (LIVE / "2026-10-15" / "hydro.jsonl").exists() else
        [{"name": k, "lat": GAUGES[k]["lat"], "lon": GAUGES[k]["lon"], "mm1": v, "mm3": v} for k, v in {"Đa Phước": 11.8, "Lê Đình Cẩn": 0.0}.items()],
        radar_rate("2026-10-15", datetime(2026, 10, 15, 13, 40, tzinfo=VN)),
        truth_streets([("Phạm Đức Sơn", (10.72, 10.75, 106.61, 106.65)), ("Hồ Học Lãm", (10.71, 10.75, 106.59, 106.63)),
                       ("Võ Văn Kiệt", (10.71, 10.76, 106.58, 106.64)), ("Sinco", (10.70, 10.75, 106.58, 106.64))],
                      "Báo chí: ngập cục bộ khoảng 13–14h"),
        [{"label": "Tiền Phong: Mưa dông ập xuống, nhiều tuyến đường TPHCM lại biến thành sông", "url": "https://tienphong.vn/mua-dong-ap-xuong-nhieu-tuyen-duong-tphcm-lai-bien-thanh-song-post1885480.tpo"}],
        "Trận mới, không dùng để chọn ngưỡng. Chạy lại đúng lúc 13:40 với số đo 44 trạm và ảnh radar đã lưu."))
    events.append(rain_event(
        "mua-2026-10-07", "Mưa lớn chiều tối 07/10", "07/10/2026, khoảng 18h",
        stations_from_max({"Nguyễn Thiện Thuật": 63.3, "Cát Lái": 56.8, "Quang Trung": 46.9, "Nhà Bè": 36.8, "Phạm Văn Cội": 32.0, "Đa Phước": 25.0}),
        None,
        truth_streets([("Phan Văn Trị", (10.81, 10.86, 106.66, 106.70)), ("Nguyễn Oanh", (10.82, 10.87, 106.66, 106.69)), ("Lê Văn Thọ", (10.83, 10.86, 106.64, 106.67)),
                       ("D5", (10.79, 10.81, 106.70, 106.72)), ("Nguyễn Hữu Cảnh", (10.77, 10.80, 106.70, 106.74)),
                       ("Điện Biên Phủ", (10.79, 10.81, 106.69, 106.72)), ("Xô Viết Nghệ Tĩnh", (10.79, 10.83, 106.70, 106.72))],
                      "Báo chí: ngập chiều tối 07/10"),
        [{"label": "Dân Việt: Mưa xối xả chiều 7/10, nhiều tuyến đường ở Gò Vấp ít khi ngập, nay lênh láng", "url": "https://danviet.vn/mua-xoi-xa-chieu-7-10-nhieu-tuyen-duong-o-go-vap-it-khi-ngap-nay-lenh-lang-d1465474.html"},
         {"label": "Tuổi Trẻ: Trung tâm TP.HCM mưa to rồi lan rộng", "url": "https://tuoitre.vn/dung-gio-tan-tam-7-10-trung-tam-tphcm-mua-to-roi-lan-ra-khap-cac-phuong-xa-100261007173452622.htm"}],
        "Dựng lại từ giờ mưa lớn nhất của từng trạm trong ngày; không có ảnh radar. Trận này đã được dùng khi chọn ngưỡng mưa."))
    events.append(rain_event(
        "mua-2026-10-06", "Mưa lớn trưa 06/10", "06/10/2026, trưa",
        stations_from_max({"Cô Bắc": 36.0}), None,
        truth_streets([("Lê Lợi", (10.77, 10.78, 106.69, 106.71)), ("Bùi Viện", (10.76, 10.77, 106.68, 106.70)),
                       ("Lý Tự Trọng", (10.77, 10.785, 106.69, 106.71)), ("Nguyễn Trung Trực", (10.77, 10.78, 106.69, 106.71))],
                      "Báo chí: ngập sau mưa lớn giữa trưa"),
        [{"label": "Tuổi Trẻ: TP.HCM mưa lớn giữa trưa 6-10, đường Lê Lợi và Bùi Viện ngập trong nước", "url": "https://tuoitre.vn/tphcm-mua-lon-giua-trua-6-10-duong-le-loi-va-bui-vien-ngap-trong-nuoc-100261006123829707.htm"}],
        "Chỉ có số của trạm Cô Bắc (trạm duy nhất từ 30 mm/giờ hôm đó); không có ảnh radar. Trận này đã được dùng khi chọn ngưỡng mưa."))
    events.append(rain_event(
        "mua-2026-10-01", "Mưa lớn tối 01/10", "01/10/2026, khoảng 18–19h",
        stations_from_max({"Nguyễn Thiện Thuật": 67.9, "Lê Đình Cẩn": 59.4, "Lê Minh Xuân 1": 58.2, "Cát Lái": 32.0, "Cô Bắc": 30.0,
                           "Củ Chi": 28.4, "Hóc Môn": 26.2, "Quang Trung": 25.0}),
        None,
        truth_streets([("Nguyễn Văn Khối", (10.83, 10.86, 106.65, 106.69)), ("Mai Chí Thọ", (10.765, 10.80, 106.71, 106.77))],
                      "Báo chí: ngập sâu tối 01/10"),
        [{"label": "Thanh Niên: Đường Nguyễn Văn Khối ngập như sông, hơn 2 tiếng nước chưa rút", "url": "https://thanhnien.vn/mua-lon-o-tphcm-tags585410.html"}],
        "Dựng lại từ giờ mưa lớn nhất của từng trạm trong ngày; không có ảnh radar. Trận này đã được dùng khi chọn ngưỡng mưa."))
    cams = {c["id"]: c for c in json.loads((LIVE / "watchlist.json").read_text(encoding="utf-8"))["cameras"]}
    dry_ids = ["587ee7d7b807da0011e33d55", "6623e7b76f998a001b25242d", "5d9ddd49766c880017188c94", "58af99abbd82540010390c39",
               "5a8254b05058170011f6eac3", "63b65f8dbfd3d90017eaa434", "63b65f33bfd3d90017eaa405", "5a8253bc5058170011f6eac1"]
    dry_truth = []
    for cid in dry_ids:
        c = cams[cid]
        rows = np.flatnonzero(km(LAT, LON, c["lat"], c["lon"]) * 1000 <= 120)
        dry_truth.append({"name": c["name"], "rows": rows, "observed": "Ảnh camera 21:00–21:10: đường ướt, không ngập"})
    events.append(rain_event(
        "mua-2026-10-08", "Mưa tối 08/10 (không ngập)", "08/10/2026, 21:10",
        stations_at("2026-10-08", datetime(2026, 10, 8, 21, 10, tzinfo=VN)), radar_rate("2026-10-08", datetime(2026, 10, 8, 21, 10, tzinfo=VN)),
        dry_truth, [{"label": "Ảnh 8 camera giao thông quanh trạm Nguyễn Thiện Thuật, bộ ghi lưu lúc 21:00–21:10", "url": ""}],
        "Mưa 29,6 mm/giờ ở trạm Nguyễn Thiện Thuật nhưng 8 camera trên các đường dễ ngập quanh đó chỉ thấy đường ướt. Ở đây 'đúng' nghĩa là app không tô.",
        kind="dry"))
    events.append(tide_event(
        "trieu-2026-10-11", "Triều cường chiều 11/10", "11/10/2026, 17:00", 1.72,
        truth_streets([("Trần Xuân Soạn", (10.74, 10.76, 106.69, 106.73)), ("Phạm Hữu Lầu", (10.68, 10.74, 106.70, 106.75)),
                       ("Huỳnh Tấn Phát", (10.68, 10.76, 106.72, 106.76)), ("Bùi Văn Ba", (10.73, 10.76, 106.72, 106.76)),
                       ("Võ Thị Nhờ", (10.73, 10.76, 106.70, 106.74)), ("Nguyễn Bình", (10.62, 10.70, 106.70, 106.80)),
                       ("Lê Văn Lương", (10.68, 10.75, 106.69, 106.72))], "Báo chí: ngập do triều cường 10–13/10"),
        [{"label": "Tuổi Trẻ: Nhiều tuyến đường ở TP.HCM ngập vì triều cường đạt đỉnh", "url": "https://tuoitre.vn/nhieu-tuyen-duong-o-tphcm-ngap-vi-trieu-cuong-dat-dinh-100261011145716767.htm"},
         {"label": "Dân trí: Triều cường dâng cao, đường phố TPHCM ngập gần nửa mét", "url": "https://dantri.com.vn/dt360/trieu-cuong-dang-cao-duong-pho-tphcm-ngap-gan-nua-met-20261010190600412.htm"}],
        "Phú An 1,72 m lúc 17:00, số đo thật. Các bậc tô theo mực nước được đặt trước khi chấm, nhưng đã chấm trên đợt triều này."))
    out = config.processed_dir("hcm") / "lich_su_ngap.json"
    out.write_text(json.dumps({"city": "hcm", "built": datetime.now(VN).isoformat(timespec="minutes"), "events": events},
                              ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"đã ghi {out} ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
