"""Tìm đường trên mạng đường OpenStreetMap: đường nhanh nhất và các lộ trình thay thế hợp lý.

Thiết kế dựa trên:
  - Abraham, Delling, Goldberg, Werneck, "Alternative Routes in Road Networks" (SEA 2010; JEA 2013): một lộ trình thay thế
    "chấp nhận được" phải (1) chia sẻ ít với đường nhanh nhất, (2) không dài bất hợp lý, (3) tối ưu cục bộ, tức không có
    đường vòng nhỏ. Ứng viên là các đường qua một nút trung gian v: s→v nối v→t, mỗi đoạn là đường ngắn nhất.
  - Dees, Geisberger, Sanders, Bader, "Defining and Computing Alternative Routes in Road Networks" (2010): độ dài "cao
    nguyên" (đoạn chung của hai cây đường ngắn nhất) là cận dưới của tối ưu cục bộ; phương pháp phạt hay sinh ra
    "đường vòng nhỏ" nên phải lọc.
  - Li, Cheema, Lu, Ali, Toosi, "Comparing Alternative Route Planning Techniques" (2021): người dùng đánh giá phương
    pháp phạt (×1,4) và phương pháp cao nguyên ngang Google Maps; tham số kéo dài tối đa 1,4.

Các bước (xem `RoadGraph.find_routes`):
  1. Đường nhanh nhất bằng Dijkstra.
  2. Ứng viên qua nút trung gian, lọc bằng numpy trên toàn bộ nút, rồi lấy mỗi "cao nguyên" một đại diện.
  3. Nếu chưa đủ, phương pháp phạt: nhân chi phí các cạnh đã chọn rồi tìm lại; ứng viên phải qua kiểm tra tối ưu cục bộ.
  4. Mọi ứng viên đều phải qua cùng một bộ lọc chấp nhận được (`_admissible`).

Thời gian đi một cạnh là chiều dài chia tốc độ theo loại đường và loại xe (QĐKT mục 7.2). Phần giao thông và ngập
đi vào qua tham số `slow`: hệ số làm chậm từng cạnh, 1 là không đổi.
"""
from __future__ import annotations

import math
import threading
from dataclasses import dataclass

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import shapely
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree

from floodrisk import config

# Tốc độ trung bình theo loại đường, km/giờ, đã hiệu chỉnh với Direction V2 của Goong trên mạng đường TP.HCM
# (04/10/2026, khoảng 21 giờ Chủ nhật, nên là mức lúc đường vắng; giao thông giờ cao điểm nhân thêm ở spec 09).
#   Xe máy: chỉnh trên 54 cặp điểm cách nhau 3-15 km. Có hai tác dụng, với độ tin cậy rất khác nhau:
#           - Hệ số thời gian (đáng tin): tỉ lệ thời gian ta/Goong 0,60 → 0,99, đo trên 80 cặp mới chưa từng dùng.
#           - Tỉ lệ giữa các loại đường (yếu): mức trùng với đường Goong 0,632 → 0,650 trên 80 cặp mới, tốt hơn ở 13
#             cặp, kém hơn ở 11, bằng nhau ở 56. Nằm trong vùng nhiễu; con số 0,737 → 0,778 trên 26 cặp là lạc quan.
#   Ô tô:   39 cặp. Tinh chỉnh tỉ lệ không cải thiện trên tập kiểm tra nên giữ tỉ lệ ban đầu, chỉ co giãn cho khớp
#           thời gian (ta/Goong 0,65 → 0,985).
# Đây là khớp với Goong, không phải đo thực tế. Chạy lại `python -m floodrisk.api.routecheck` khi có thêm dữ liệu.
SPEEDS_KMH: dict[str, dict[str, float]] = {
    "bike": {"trunk": 23.3, "primary": 18.6, "secondary": 18.1, "tertiary": 14.5, "default": 11.6},
    "car": {"motorway": 47.0, "trunk": 30.0, "primary": 21.3, "secondary": 17.3, "tertiary": 14.7, "default": 10.0},
}
BANNED: dict[str, frozenset[str]] = {"bike": frozenset({"motorway"}), "car": frozenset()}
VEHICLES = tuple(SPEEDS_KMH)
UNNAMED = "Đường không tên"


class GraphError(Exception):
    """Lỗi dữ liệu hoặc đầu vào của mạng đường, với lời giải thích tiếng Việt."""


@dataclass(frozen=True)
class RouteParams:
    max_routes: int = 6  # kể cả đường nhanh nhất
    max_stretch: float = 1.4  # thời gian tối đa so với đường nhanh nhất (Li và cộng sự)
    detour_stretch: float = 0.4  # ε: đoạn vòng không dài hơn (1+ε) lần đoạn nó thay
    # γ: tối đa 70% thời gian dùng chung giữa hai lộ trình. Bài gốc dùng 0,8 cho mạng cả lục địa; ở đô thị dày thì
    # thấp hơn: các lộ trình thay thế của Goong chia sẻ trung vị 27% với đường chính của nó, và với 0,7 độ đa dạng
    # của ta (chia sẻ trung bình 0,33) tương đương. Đo trên 70 cặp điểm thật, 04/10/2026.
    max_sharing: float = 0.7
    local_opt: float = 0.25  # α: cao nguyên dài ít nhất α lần đoạn vòng
    penalty_factor: float = 1.4  # hệ số phạt (Li và cộng sự)
    penalty_rounds: int = 10
    penalty_patience: int = 3  # dừng sau ngần ấy lần liên tiếp không ra ứng viên mới
    lo_tolerance: float = 0.03  # sai số cho phép khi kiểm tra tối ưu cục bộ
    max_via_evaluations: int = 60  # số đường qua nút trung gian khác nhau được dựng và kiểm tra tối đa
    use_via: bool = True
    use_penalty: bool = True
    max_snap_m: float = 300.0


@dataclass
class Route:
    nodes: np.ndarray  # chỉ số nút theo thứ tự đi
    edges: np.ndarray  # chỉ số cạnh theo thứ tự đi
    duration_s: float
    distance_m: float
    edge_time: np.ndarray  # giây đi từng cạnh của lộ trình này, theo chi phí lúc tìm
    kind: str = "alternative"


def _climb(step: np.ndarray) -> np.ndarray:
    """Điểm cố định của `step` khi áp dụng liên tiếp, tính bằng bình phương liên tục (nhảy con trỏ)."""
    while True:
        nxt = step[step]
        if np.array_equal(nxt, step):
            return step
        step = nxt


def _walk_back(pred: np.ndarray, src: int, dst: int) -> list[int] | None:
    nodes = [dst]
    while nodes[-1] != src:
        previous = int(pred[nodes[-1]])
        if previous < 0:
            return None
        nodes.append(previous)
    return nodes[::-1]


def _walk_forward(succ: np.ndarray, start: int, dst: int) -> list[int] | None:
    nodes = [start]
    while nodes[-1] != dst:
        nxt = int(succ[nodes[-1]])
        if nxt < 0:
            return None
        nodes.append(nxt)
    return nodes


def _bearing(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Hướng đi từ a tới b theo độ, 0 là bắc, tăng theo chiều kim đồng hồ."""
    dx = (b[0] - a[0]) * math.cos(math.radians((a[1] + b[1]) / 2))
    dy = b[1] - a[1]
    return math.degrees(math.atan2(dx, dy)) % 360


def _turn_name(incoming: float, outgoing: float) -> str:
    delta = (outgoing - incoming + 540) % 360 - 180
    if abs(delta) < 25:
        return "straight"
    if abs(delta) > 150:
        return "uturn"
    return "right" if delta > 0 else "left"


class RoadGraph:
    def __init__(
        self,
        node_lon: np.ndarray,
        node_lat: np.ndarray,
        u: np.ndarray,
        v: np.ndarray,
        length_m: np.ndarray,
        highway: np.ndarray,
        names: np.ndarray | None = None,
        geometry_wkb: pa.Array | None = None,
    ) -> None:
        self.n = len(node_lon)
        self.node_lon = np.asarray(node_lon, dtype=float)
        self.node_lat = np.asarray(node_lat, dtype=float)
        self.u = np.asarray(u, dtype=np.int64)
        self.v = np.asarray(v, dtype=np.int64)
        self.length_m = np.asarray(length_m, dtype=float)
        self.highway = np.asarray(highway, dtype=object)
        self.m = len(self.u)
        if self.m and (self.u.max() >= self.n or self.v.max() >= self.n or self.u.min() < 0 or self.v.min() < 0):
            raise GraphError("Mạng đường có cạnh trỏ tới nút không tồn tại")
        self.names = np.asarray(names if names is not None else [""] * self.m, dtype=object)
        self._wkb = geometry_wkb

        # Cạnh khuyên và cạnh song song không dùng được: scipy sẽ cộng dồn các phần tử trùng vị trí.
        usable = self.u != self.v
        key = self.u * self.n + self.v
        order = np.lexsort((self.length_m, key))
        seen_key = key[order]
        first = np.ones(self.m, dtype=bool)
        first[1:] = seen_key[1:] != seen_key[:-1]
        parallel = np.zeros(self.m, dtype=bool)
        parallel[order[~first]] = True
        self._structural = usable & ~parallel
        self._key = key
        sel = np.flatnonzero(self._structural)
        self._key_order = sel[np.argsort(key[sel])]
        self._key_sorted = key[self._key_order]

        self._lock = threading.RLock()
        self._base_time: dict[str, np.ndarray] = {}
        self._snap: dict[str, tuple[cKDTree, np.ndarray]] = {}
        lat0 = float(np.mean(self.node_lat)) if self.n else 0.0
        self._lon0 = float(np.mean(self.node_lon)) if self.n else 0.0
        self._lat0 = lat0
        self._kx = 111_320.0 * math.cos(math.radians(lat0))
        self._ky = 110_540.0

    # ------------------------------------------------------------------ nạp dữ liệu
    @classmethod
    def load(cls, city: str) -> RoadGraph:
        paths = [config.graph_nodes_path(city), config.graph_edges_path(city)]
        missing = [p.name for p in paths if not p.exists()]
        if missing:
            raise GraphError(f"Thành phố này chưa có mạng đường (thiếu {', '.join(missing)})")

        nodes = pd.read_parquet(paths[0])
        table = pq.read_table(paths[1])
        edges = table.select(["edge_id", "u", "v", "length_m", "highway"]).to_pandas()
        node_ids = nodes["node_id"].to_numpy()
        order = np.argsort(node_ids)
        sorted_ids = node_ids[order]

        def position(ids: np.ndarray) -> np.ndarray:
            at = np.searchsorted(sorted_ids, ids)
            if (at >= len(sorted_ids)).any() or (sorted_ids[np.clip(at, 0, len(sorted_ids) - 1)] != ids).any():
                raise GraphError("Mạng đường có cạnh trỏ tới nút không tồn tại")
            return order[at]

        names = np.full(len(edges), "", dtype=object)
        eu_path, units_path = config.edge_units_path(city), config.units_path(city)
        if eu_path.exists() and units_path.exists():
            links = pd.read_parquet(eu_path, columns=["edge_id", "unit_id", "length_m"])
            links = links.sort_values(["edge_id", "length_m"], ascending=[True, False]).drop_duplicates("edge_id")
            unit_names = pd.read_parquet(units_path, columns=["unit_id", "name"]).set_index("unit_id")["name"]
            row_of_edge = pd.Series(np.arange(len(edges)), index=edges["edge_id"].to_numpy())
            links = links[links["edge_id"].isin(row_of_edge.index)]
            names[row_of_edge.loc[links["edge_id"]].to_numpy()] = unit_names.reindex(links["unit_id"]).fillna("").to_numpy()

        return cls(
            node_lon=nodes["lon"].to_numpy(),
            node_lat=nodes["lat"].to_numpy(),
            u=position(edges["u"].to_numpy()),
            v=position(edges["v"].to_numpy()),
            length_m=edges["length_m"].to_numpy(),
            highway=edges["highway"].to_numpy(),
            names=names,
            geometry_wkb=table.column("geometry").combine_chunks(),
        )

    # ------------------------------------------------------------------ chi phí
    def time_s(self, vehicle: str, slow: np.ndarray | float | None = None) -> np.ndarray:
        """Thời gian đi từng cạnh, giây. Vô cùng ở cạnh xe đó không được đi."""
        if vehicle not in SPEEDS_KMH:
            raise GraphError(f"Loại xe không hợp lệ: {vehicle}")
        with self._lock:
            base = self._base_time.get(vehicle)
            if base is None:
                table = SPEEDS_KMH[vehicle]
                klass = pd.Series(self.highway).astype(str).str.replace("_link", "", regex=False)
                speed = klass.map(table).fillna(table["default"]).to_numpy(dtype=float)
                base = self.length_m / (speed / 3.6)
                banned = klass.isin(BANNED[vehicle]).to_numpy()
                base = np.where(banned | ~self._structural, np.inf, base)
                self._base_time[vehicle] = base
        if slow is None:
            return base
        return base * np.asarray(slow, dtype=float)

    def _matrix(self, cost: np.ndarray, reverse: bool = False) -> csr_matrix:
        ok = np.isfinite(cost)
        rows, cols = (self.v, self.u) if reverse else (self.u, self.v)
        return csr_matrix((cost[ok], (rows[ok], cols[ok])), shape=(self.n, self.n))

    def edges_of(self, nodes: np.ndarray) -> np.ndarray:
        """Chỉ số cạnh nối từng cặp nút liên tiếp."""
        keys = nodes[:-1].astype(np.int64) * self.n + nodes[1:]
        at = np.searchsorted(self._key_sorted, keys)
        at = np.clip(at, 0, len(self._key_sorted) - 1)
        if (self._key_sorted[at] != keys).any():
            raise GraphError("Lộ trình có hai nút liên tiếp không nối với nhau")
        return self._key_order[at]

    # ------------------------------------------------------------------ gắn điểm vào mạng đường
    def project(self, lon: np.ndarray, lat: np.ndarray) -> np.ndarray:
        """Tọa độ phẳng theo mét (xấp xỉ, đủ chính xác trong phạm vi một thành phố)."""
        return np.column_stack([(np.asarray(lon) - self._lon0) * self._kx, (np.asarray(lat) - self._lat0) * self._ky])

    def snap(self, lon: float, lat: float, vehicle: str) -> tuple[int, float]:
        """Nút gần nhất thuộc thành phần liên thông lớn nhất của xe đó, và khoảng cách tới nó (mét).

        Mạng thật có hàng nghìn thành phần liên thông nhỏ (ngõ cụt tách rời, đường một chiều khép kín); gắn vào đó
        thì không đi tới đâu được.
        """
        with self._lock:
            if vehicle not in self._snap:
                cost = self.time_s(vehicle)
                matrix = self._matrix(cost)
                _, labels = connected_components(matrix, directed=True, connection="strong")
                connected = np.isfinite(cost)
                touched = np.zeros(self.n, dtype=bool)
                touched[self.u[connected]] = True
                touched[self.v[connected]] = True
                sizes = np.bincount(labels[touched]) if touched.any() else np.array([0])
                main = np.flatnonzero(touched & (labels == int(np.argmax(sizes))))
                tree = cKDTree(self.project(self.node_lon[main], self.node_lat[main]))
                self._snap[vehicle] = (tree, main)
            tree, main = self._snap[vehicle]
        distance, at = tree.query(self.project(np.array([lon]), np.array([lat]))[0])
        return int(main[at]), float(distance)

    # ------------------------------------------------------------------ hình học và chỉ dẫn
    def edge_coords(self, edge: int) -> np.ndarray:
        """Tọa độ (kinh độ, vĩ độ) dọc một cạnh, theo chiều từ u tới v."""
        u, v = int(self.u[edge]), int(self.v[edge])
        a = np.array([self.node_lon[u], self.node_lat[u]])
        b = np.array([self.node_lon[v], self.node_lat[v]])
        if self._wkb is not None:
            coords = np.array(shapely.from_wkb(self._wkb[edge].as_py()).coords)[:, :2]
            if len(coords) >= 2:
                # Hình học có thể được lưu ngược chiều; luôn trả theo chiều đi.
                if np.abs(coords[0] - a).sum() > np.abs(coords[-1] - a).sum():
                    coords = coords[::-1]
                return coords
        return np.array([a, b])

    def geometry(self, route: Route) -> list[list[float]]:
        points: list[list[float]] = []
        for edge in route.edges:
            for lon, lat in self.edge_coords(int(edge)):
                point = [round(float(lon), 6), round(float(lat), 6)]
                if not points or points[-1] != point:
                    points.append(point)
        return points

    def steps(self, route: Route) -> list[dict]:
        """Chỉ dẫn theo chặng: gộp các cạnh liền nhau cùng tên đường."""
        if len(route.edges) == 0:
            return []
        label = np.where(self.names[route.edges] == "", UNNAMED, self.names[route.edges])
        starts = np.flatnonzero(np.r_[True, label[1:] != label[:-1]])
        ends = np.r_[starts[1:], len(label)]
        time = route.edge_time
        out: list[dict] = []
        for index, (first, last) in enumerate(zip(starts, ends)):
            turn = "start"
            if index > 0:
                before = self.edge_coords(int(route.edges[first - 1]))
                after = self.edge_coords(int(route.edges[first]))
                turn = _turn_name(
                    _bearing(tuple(before[-2]), tuple(before[-1])), _bearing(tuple(after[0]), tuple(after[1]))
                )
            out.append({
                "name": str(label[first]),
                "distance_m": round(float(self.length_m[route.edges[first:last]].sum()), 1),
                "duration_s": round(float(time[first:last].sum()), 1),
                "turn": turn,
            })
        return out

    # ------------------------------------------------------------------ tìm đường
    def find_routes(
        self,
        src: int,
        dst: int,
        vehicle: str = "bike",
        params: RouteParams | None = None,
        slow: np.ndarray | float | None = None,
    ) -> list[Route]:
        """Đường nhanh nhất rồi các lộ trình thay thế hợp lý, sắp theo thời gian. Rỗng nếu không tới được."""
        params = params or RouteParams()
        if src == dst:
            raise GraphError("Điểm đi và điểm đến trùng nhau")
        cost = self.time_s(vehicle, slow)
        forward = self._matrix(cost)
        backward = self._matrix(cost, reverse=True)

        ds, pf = dijkstra(forward, directed=True, indices=src, return_predecessors=True)
        if not np.isfinite(ds[dst]):
            return []
        opt = self._make_route(_walk_back(pf, src, dst), cost, "fastest")
        chosen = [opt]
        d_star = opt.duration_s

        dt = ps = None
        if params.use_via and params.max_routes > 1:
            dt, ps = dijkstra(backward, directed=True, indices=dst, return_predecessors=True,
                              limit=params.max_stretch * d_star)
            nodes, certified = self._via_nodes(ds, dt, pf, ps, opt, d_star, params)
            covered = np.zeros(self.n, dtype=bool)  # nút đã nằm trên một đường vừa xét: bỏ qua, khỏi dựng lại
            evaluated = 0
            for node, sure in zip(nodes.tolist(), certified.tolist()):
                if len(chosen) >= params.max_routes or evaluated >= params.max_via_evaluations:
                    break
                if covered[node]:
                    continue
                evaluated += 1
                path = self._via_path(pf, ps, src, dst, node)
                if path is None:
                    covered[node] = True
                    continue
                candidate = self._make_route(path, cost)
                self._cover(covered, candidate, ds, dt)
                # Cao nguyên đủ dài đảm bảo tối ưu cục bộ (Abraham và cộng sự, bổ đề 4); không thì kiểm tra trực tiếp.
                if self._admissible(candidate, chosen, d_star, params) and (
                    sure or self._locally_optimal(candidate, opt, cost, forward, params)
                ):
                    chosen.append(candidate)

        if params.use_penalty and len(chosen) < params.max_routes:
            self._penalty_routes(src, dst, cost, forward, chosen, params)

        chosen.sort(key=lambda r: r.duration_s)
        chosen[0].kind = "fastest"
        for route in chosen[1:]:
            route.kind = "alternative"
        return chosen

    def _make_route(self, nodes: list[int], cost: np.ndarray, kind: str = "alternative") -> Route:
        arr = np.asarray(nodes, dtype=np.int64)
        edges = self.edges_of(arr)
        edge_time = cost[edges]
        return Route(arr, edges, float(edge_time.sum()), float(self.length_m[edges].sum()), edge_time, kind)

    @staticmethod
    def _via_path(pf: np.ndarray, ps: np.ndarray, src: int, dst: int, via: int) -> list[int] | None:
        head = _walk_back(pf, src, via)
        tail = _walk_forward(ps, via, dst)
        if head is None or tail is None:
            return None
        nodes = head + tail[1:]
        return nodes if len(set(nodes)) == len(nodes) else None  # đường có vòng lặp thì bỏ

    @staticmethod
    def _cover(covered: np.ndarray, route: Route, ds: np.ndarray, dt: np.ndarray) -> None:
        """Đánh dấu các nút mà đường qua chúng chính là `route` (cả hai nửa đều là đường ngắn nhất)."""
        elapsed = np.concatenate([[0.0], np.cumsum(route.edge_time)])
        tol = 1e-6 * route.duration_s + 1e-6
        same = (np.abs(elapsed - ds[route.nodes]) <= tol) & (np.abs(route.duration_s - elapsed - dt[route.nodes]) <= tol)
        covered[route.nodes[same]] = True

    def _via_nodes(self, ds, dt, pf, ps, opt: Route, d_star: float, p: RouteParams) -> tuple[np.ndarray, np.ndarray]:
        """Các nút trung gian thỏa chia sẻ, kéo dài và đường vòng, tốt nhất trước.

        Trả về (nút, cờ "cao nguyên đủ dài"). Cờ đúng thì lộ trình chắc chắn tối ưu cục bộ; cờ sai thì phải kiểm tra
        trực tiếp, vì khi nhiều đường hòa nhau (lưới đều) cao nguyên bị vỡ thành mảnh ngắn dù lộ trình vẫn tốt.
        """
        n = self.n
        idx = np.arange(n)
        empty = (np.array([], dtype=np.int64), np.array([], dtype=bool))
        on_opt = np.zeros(n, dtype=bool)
        on_opt[opt.nodes] = True
        total = ds + dt
        cand = np.isfinite(total) & ~on_opt & (total <= p.max_stretch * d_star)
        if not cand.any():
            return empty

        pf_safe = np.where(pf >= 0, pf, idx)
        ps_safe = np.where(ps >= 0, ps, idx)
        # a(v): nút cuối cùng của đường s→v còn nằm trên đường nhanh nhất; b(v): nút đầu tiên của v→t quay lại nó.
        a = _climb(np.where(on_opt, idx, pf_safe))
        b = _climb(np.where(on_opt, idx, ps_safe))
        with np.errstate(invalid="ignore"):
            shared = ds[a] + dt[b]
            skipped = d_star - shared
            detour = total - shared
            ok = (
                cand
                & np.isfinite(shared)
                & (ds[a] <= ds[b])
                & (skipped > 0)
                & (shared <= p.max_sharing * d_star)
                & (detour <= (1 + p.detour_stretch) * skipped)
            )
            if not ok.any():
                return empty

            # Cao nguyên: cạnh x→y nằm trong cả hai cây thì thuộc cùng một cao nguyên.
            up_ok = (pf >= 0) & (ps[pf_safe] == idx)
            down_ok = (ps >= 0) & (pf[ps_safe] == idx)
            start = _climb(np.where(up_ok, pf_safe, idx))
            end = _climb(np.where(down_ok, ps_safe, idx))
            plateau = np.where(np.isfinite(ds[end]) & np.isfinite(ds[start]), ds[end] - ds[start], 0.0)
            certified = plateau > p.local_opt * detour
        nodes = np.flatnonzero(ok)
        rank = 2 * total[nodes] + shared[nodes] - plateau[nodes]
        order = np.argsort(rank, kind="stable")
        return nodes[order], certified[nodes][order]

    def _admissible(self, cand: Route, chosen: list[Route], d_star: float, p: RouteParams) -> bool:
        if cand.duration_s > p.max_stretch * d_star * (1 + 1e-9):
            return False
        if len(set(cand.nodes.tolist())) != len(cand.nodes):
            return False
        for other in chosen:
            shared_time = float(cand.edge_time[np.isin(cand.edges, other.edges)].sum())
            if shared_time > p.max_sharing * min(cand.duration_s, other.duration_s) * (1 + 1e-9):
                return False
        return True

    # ------------------------------------------------------------------ phương pháp phạt
    def _penalty_routes(self, src, dst, cost, forward, chosen: list[Route], p: RouteParams) -> None:
        opt = chosen[0]
        d_star = opt.duration_s
        penalised = cost.copy()
        for route in chosen:
            penalised[route.edges] *= p.penalty_factor
        misses = 0
        for _ in range(p.penalty_rounds):
            if len(chosen) >= p.max_routes or misses >= p.penalty_patience:
                return
            _, pred = dijkstra(self._matrix(penalised), directed=True, indices=src, return_predecessors=True)
            path = _walk_back(pred, src, dst)
            if path is None:
                return
            cand = self._make_route(path, cost)
            penalised[cand.edges] *= p.penalty_factor  # phạt dù có nhận hay không, để vòng sau ra đường khác
            if self._admissible(cand, chosen, d_star, p) and self._locally_optimal(cand, opt, cost, forward, p):
                chosen.append(cand)
                misses = 0
            else:
                misses += 1

    def _locally_optimal(self, cand: Route, opt: Route, cost: np.ndarray, forward: csr_matrix, p: RouteParams) -> bool:
        """Kiểm tra T-test theo cửa sổ: mọi đoạn dài T = α × (phần vòng) của lộ trình phải là đường ngắn nhất."""
        off = ~np.isin(cand.edges, opt.edges)
        detour = float(cost[cand.edges[off]].sum())
        if detour <= 0:
            return True
        window = p.local_opt * detour
        elapsed = np.concatenate([[0.0], np.cumsum(cost[cand.edges])])
        off_at = np.flatnonzero(off)
        lo = max(0.0, elapsed[off_at[0]] - window)
        hi = elapsed[off_at[-1] + 1]
        starts = np.arange(lo, max(hi - window / 2, lo + 1e-9), window / 2)
        first = np.searchsorted(elapsed, starts, side="left")
        last = np.searchsorted(elapsed, starts + window, side="right") - 1
        keep = last > first
        first, last = first[keep], last[keep]
        if len(first) == 0:
            return True
        length = elapsed[last] - elapsed[first]
        for chunk in range(0, len(first), 8):
            sl = slice(chunk, chunk + 8)
            dist = dijkstra(forward, directed=True, indices=cand.nodes[first[sl]], limit=float(length[sl].max()) * 1.001)
            shortest = dist[np.arange(len(dist)), cand.nodes[last[sl]]]
            if (length[sl] > shortest * (1 + p.lo_tolerance)).any():
                return False
        return True
