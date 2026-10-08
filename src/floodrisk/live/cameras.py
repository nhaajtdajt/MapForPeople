"""Camera giao thông công cộng của TP.HCM: danh sách, ảnh lúc này, và Gemini đọc ảnh.

Chép từ mlai-car-access, commit f000823, file `backend/app/cameras.py` (quyết định D34 của repo đó): nguyên văn cách hỏi
cổng (`fetch_official`, `_ajaxpro_json`, `_table`), địa chỉ ảnh, dấu của ảnh "không có hình" và câu lệnh cho Gemini (`PROMPT`).
Phần gọi Gemini viết gọn lại cho một camera mỗi lần: khóa lấy từ GEMINI_API_KEY, GEMINI_API_KEY_2... trong môi trường,
xoay vòng, gửi trong tiêu đề yêu cầu; hết hạn mức ở mô hình này thì thử mô hình kế.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone

import httpx

VN_TZ = timezone(timedelta(hours=7))
SNAPSHOT_URL = "https://giaothong.hochiminhcity.gov.vn/render/ImageHandler.ashx?id={cam}&t={ms}"
PORTAL_URL = "https://giaothong.hochiminhcity.gov.vn/Map.aspx"
LAYER_URL = "https://giaothong.hochiminhcity.gov.vn/ajaxpro/VDMS.Web.Library.AJAX.FolderAjax,VDMS.Web.Library.ashx"
# The request the portal's map page sends when its "Camera" layer is switched on.
LAYER_QUERY = {"path": "/root/vdms/tangthu/data/layerdata/camera", "isInTree": False, "searchKey": "",
               "layer": ["CAMERA"], "detail": True, "page": 0, "limit": -1, "filterQuery": ["Publish:true"],
               "sortby": None, "returnFields": ["CamId", "Code", "Location", "CamType", "CamStatus"]}
PLACEHOLDER_MD5 = "27bc56b5710fe8ddb7e6665dfd735f1e"  # "IMAGE NOT AVAILABLE", 2,638 bytes
REGISTRY_TTL_S = 3600
SNAP_TTL_S = 10
READ_TTL_S = 180
ASK_TIMEOUT_S = 30  # một lần gọi Gemini
ASK_BUDGET_S = 70  # tổng thời gian cho một camera, qua mọi khóa và mọi mô hình
REFRESH_S = 13  # ảnh của cổng đổi khoảng 12 giây một lần: hai khung cách nhau chừng này mới khác nhau
MODELS = [m.strip() for m in os.environ.get("CAMERA_MODELS", "gemini-3.5-flash,gemini-3.1-flash-lite").split(",") if m.strip()]
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEPTH_OF = {"duoi_15cm": "light", "15_30cm": "medium", "30_50cm": "high", "tren_50cm": "high"}  # lớp của Gemini -> ba lớp của báo ngập

PROMPT = """Ảnh tĩnh từ {n} camera giao thông TP.HCM. Mỗi camera có 1 hoặc 2 ảnh; 2 ảnh là cùng camera chụp cách
nhau ~13 giây: so sánh vị trí xe giữa hai ảnh để biết xe đang chạy hay đứng yên. Đọc từng camera độc lập.
Trả về JSON {"cameras":[...]}, mỗi camera một phần tử:
{"camera":số thứ tự camera,
 "image_time":"giờ in trên ảnh (ảnh cuối), dạng YYYY-MM-DDTHH:MM:SS, hoặc null",
 "usable":true|false,
 "flooded":true|false,
 "depth_class":"kho|uot|duoi_15cm|15_30cm|30_50cm|tren_50cm|khong_ro",
 "traffic":"thong_thoang|dong|un_u|ket_cung|khong_ro",
 "evidence":"ngắn gọn, tiếng Việt: dựa vào đâu",
 "confidence":0-1}
usable=false khi ảnh lỗi, mất tín hiệu, bị che, hoặc quá tối/mờ để thấy mặt đường.
Ngập: chỉ khi thấy nước đọng phủ mặt đường. Mặt đường ướt do mưa là "uot", không phải ngập. Ước lượng độ sâu
bằng vật tham chiếu (bánh xe máy cao ~60 cm, lề đường ~15 cm, nước tóe quanh bánh xe).
Giao thông trên lòng đường camera nhìn rõ nhất: thong_thoang = xe chạy tự do, nhiều khoảng trống;
dong = nhiều xe nhưng vẫn chạy đều; un_u = xe chen kín, nhích chậm; ket_cung = xe kín lòng đường và gần như
không di chuyển giữa hai ảnh. Đường vắng ban đêm là thong_thoang.
Nếu hai chiều đường khác nhau, đánh giá theo chiều kẹt hơn và nói rõ chiều nào trong evidence."""


class NoKey(Exception):
    """Chưa có khóa Gemini trong môi trường."""


class OutOfQuota(Exception):
    """Mọi khóa và mọi mô hình đều đã hết hạn mức hoặc đang quá tải."""


def fetch_official() -> list[dict]:
    """The portal's camera layer, asked for exactly as its public map page asks (anonymous visitor session)."""
    with httpx.Client(headers={"User-Agent": "Mozilla/5.0 (VaoDuoc-hackathon)"}, timeout=60,
                      follow_redirects=True) as c:
        c.get(PORTAL_URL).raise_for_status()
        r = c.post(LAYER_URL, content=json.dumps(LAYER_QUERY),
                   headers={"Content-Type": "text/plain; charset=utf-8", "X-AjaxPro-Method": "SearchQuery"})
        r.raise_for_status()
    value = _ajaxpro_json(r.text)["value"]
    rows = next(t for t in value[1] if isinstance(t, list) and t and isinstance(t[0], list)
                and any(col[0] == "CamId" for col in t[0]))
    cams = []
    for row in _table(rows):
        point = re.match(r"POINT\(([\d.]+) ([\d.]+)\)", (_table(row["Location"]) or [{}])[0].get("Shape") or "")
        if not row.get("CamId") or not point:
            continue
        cams.append({"id": row["CamId"], "name": (row.get("DisplayName") or row.get("Title") or "").strip(),
                     "lat": round(float(point.group(2)), 7), "lon": round(float(point.group(1)), 7),
                     "code": row.get("Code") or "", "type": row.get("CamType") or "",
                     "status": row.get("CamStatus") or ""})
    if len(cams) < 100:
        raise ValueError(f"only {len(cams)} cameras")
    return cams


_DATATABLE = "new Ajax.Web.DataTable("


def _ajaxpro_json(text: str):
    """AjaxPro answers JSON with `new Ajax.Web.DataTable(cols, rows)` literals; turn those into arrays."""
    out, i, in_str, n = [], 0, False, len(text)
    while i < n:
        ch = text[i]
        if in_str:
            out.append(ch)
            if ch == "\\":
                out.append(text[i + 1])
                i += 2
                continue
            in_str = ch != '"'
        elif ch == '"':
            in_str = True
            out.append(ch)
        elif text.startswith(_DATATABLE, i):
            out.append("[")
            i += len(_DATATABLE)
            continue
        else:
            out.append("]" if ch == ")" else ch)
        i += 1
    return json.loads("".join(out))


def _table(dt) -> list[dict]:
    if not dt:
        return []
    names = [c[0] for c in dt[0]]
    return [dict(zip(names, r)) for r in dt[1]]


_registry: dict = {"t": 0.0, "cameras": []}
_snaps: dict[str, tuple[float, bytes | None]] = {}
_reads: dict[str, tuple[float, dict]] = {}
_lock = threading.Lock()
_turn = 0


def registry() -> list[dict]:
    """Danh sách camera kèm trạng thái của cổng, làm mới mỗi giờ. Cổng lỗi thì giữ danh sách cũ."""
    with _lock:
        if time.time() - _registry["t"] > REGISTRY_TTL_S:
            _registry["t"] = time.time()
            try:
                _registry["cameras"] = fetch_official()
            except Exception as exc:  # cổng lỗi: thử lại sau một giờ, không phải ở mỗi yêu cầu
                print(f"camera: không lấy được danh sách ({type(exc).__name__})")
        return _registry["cameras"]


def snapshot(cam_id: str, max_age_s: float = SNAP_TTL_S) -> bytes | None:
    """Ảnh lúc này của một camera, hoặc None nếu camera không có hình."""
    hit = _snaps.get(cam_id)
    if hit and time.time() - hit[0] < max_age_s:
        return hit[1]
    image = None
    try:
        r = httpx.get(SNAPSHOT_URL.format(cam=cam_id, ms=int(time.time() * 1000)), timeout=12,
                      headers={"User-Agent": "Mozilla/5.0 (floodrisk-hackathon)"})
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/") \
                and hashlib.md5(r.content).hexdigest() != PLACEHOLDER_MD5:
            image = r.content
    except httpx.HTTPError:
        pass
    _snaps[cam_id] = (time.time(), image)
    return image


def gemini_keys() -> list[str]:
    global _turn
    keys = [os.environ[k] for k in sorted(os.environ, key=lambda k: (len(k), k))
            if (k == "GEMINI_API_KEY" or k.startswith("GEMINI_API_KEY_")) and os.environ[k]]
    if not keys:
        return []
    _turn = (_turn + 1) % len(keys)
    return keys[_turn:] + keys[:_turn]


def ask_gemini(name: str, frames: list[bytes]) -> tuple[dict, str]:
    """Một lần hỏi Gemini cho một camera. Trả (câu trả lời cho camera đó, tên mô hình đã trả lời)."""
    keys = gemini_keys()
    if not keys:
        raise NoKey("Chưa có GEMINI_API_KEY trong .env")
    parts = [{"text": PROMPT.replace("{n}", "1")}, {"text": f"Camera 1: {name} ({len(frames)} ảnh)"}]
    parts += [{"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(f).decode()}} for f in frames]
    body = {"contents": [{"parts": parts}], "generationConfig": {"responseMimeType": "application/json", "temperature": 0}}
    deadline = time.time() + ASK_BUDGET_S
    for model in MODELS:
        for key in keys:
            if time.time() > deadline:
                raise OutOfQuota("Gemini trả lời quá chậm, thử lại sau ít phút")
            try:
                r = httpx.post(GEMINI_URL.format(model=model), headers={"x-goog-api-key": key}, json=body, timeout=ASK_TIMEOUT_S)
            except httpx.HTTPError:
                continue
            if r.status_code != 200:
                continue  # hết hạn mức, quá tải hoặc khóa không dùng được mô hình này: thử khóa kế, rồi mô hình kế
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            found = re.search(r"\{.*\}", text, re.S)
            answer = json.loads(found.group(0) if found else text)
            cameras = answer.get("cameras") or [answer]
            return cameras[0], model
    raise OutOfQuota("Gemini đang hết hạn mức hoặc quá tải ở mọi khóa")


def read(cam: dict) -> dict:
    """Gemini đọc một camera: hai khung cách nhau một lần làm mới. Kết quả giữ READ_TTL_S giây."""
    hit = _reads.get(cam["id"])
    if hit and time.time() - hit[0] < READ_TTL_S:
        return hit[1]
    first = snapshot(cam["id"], max_age_s=0)
    if first is None:
        return {"id": cam["id"], "state": "offline"}
    time.sleep(REFRESH_S)
    second = snapshot(cam["id"], max_age_s=0)
    frames = [first] + ([second] if second and second != first else [])
    answer, model = ask_gemini(cam["name"], frames)
    flooded = bool(answer.get("flooded")) and bool(answer.get("usable", True))
    result = {"id": cam["id"], "state": "ok" if answer.get("usable", True) else "unusable", "at": datetime.now(VN_TZ).isoformat(timespec="seconds"),
              "frames": len(frames), "flooded": flooded, "depth_class": answer.get("depth_class"), "depth": DEPTH_OF.get(answer.get("depth_class")) if flooded else None,
              "traffic": answer.get("traffic"), "evidence": answer.get("evidence"), "confidence": float(answer.get("confidence") or 0),
              "image_time": answer.get("image_time"), "model": model}
    _reads[cam["id"]] = (time.time(), result)
    return result
