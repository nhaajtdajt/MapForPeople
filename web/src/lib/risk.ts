// Quy tắc ra mức nguy cơ của một tuyến, giống hệt máy chủ (src/floodrisk/model/levels.py, lấy từ repo mô hình).
// Lớp bản đồ chỉ mang nhóm mưa (br) và thứ hạng triều (pt) của tuyến; trạng thái mưa và phần tô theo triều đến từ /api/risk.

export type DayState = "quiet" | "watch" | "alert";
export type Level = 0 | 1 | 2; // 0 thấp, 1 vừa, 2 cao
export type Band = 0 | 1 | 2; // 2 là nhóm A (5% điểm cao nhất), 1 là nhóm B (15% kế tiếp)

/** Thuộc tính của một tuyến trong /api/risk/routes. */
export interface RouteProps {
  id: string;
  name: string;
  cls: string;
  len: number;
  br: Band; // nhóm theo mưa
  bt: Band; // nhóm theo triều
  pt?: number; // vị trí trong bảng xếp hạng dễ ngập do triều, 0 là dễ ngập nhất
  ev?: number; // 1 khi tuyến là cầu, cầu vượt: không bao giờ tô ngập
  hr: number; // số ngày từng ghi nhận ngập do mưa trước 2025
  ht: number; // số ngày từng ghi nhận ngập do triều trước 2025
}

export const STATE_LABEL: Record<DayState, string> = { quiet: "yên", watch: "cảnh giác", alert: "báo động" };
export const LEVEL_LABEL: Record<Level, string> = { 0: "thấp", 1: "vừa", 2: "cao" };

/** Mức do một nguyên nhân: báo động thì nhóm A lên cao và nhóm B lên vừa; cảnh giác thì chỉ nhóm A lên vừa. */
export function causeLevel(band: Band, state: DayState): Level {
  if (state === "alert") return band;
  if (state === "watch") return band === 2 ? 1 : 0;
  return 0;
}

/**
 * Phần tô theo triều (từ /api/risk, `tide_extent`): tuyến có thứ hạng triều dưới `red` là cao, dưới `coloured` là vừa.
 * Máy chủ chọn hai số này theo bậc mực nước Phú An: triều càng cao càng tô nhiều tuyến.
 */
export interface TideExtent {
  red: number;
  coloured: number;
}

export const NO_TIDE: TideExtent = { red: 0, coloured: 0 };

const NOT_RANKED = 1e9; // tuyến không có thứ hạng triều trong lớp bản đồ

export function tideLevel(position: number | undefined, tide: TideExtent): Level {
  const at = position ?? NOT_RANKED;
  return at < tide.red ? 2 : at < tide.coloured ? 1 : 0;
}

export function routeLevel(route: Pick<RouteProps, "br" | "pt" | "ev">, rain: DayState, tide: TideExtent): Level {
  if (route.ev === 1) return 0;
  return Math.max(causeLevel(route.br, rain), tideLevel(route.pt, tide)) as Level;
}

type Expr = unknown[];

function causeExpression(property: "br" | "bt", state: DayState): Expr | number {
  if (state === "alert") return ["get", property];
  if (state === "watch") return ["case", ["==", ["get", property], 2], 1, 0];
  return 0;
}

function tideExpression(tide: TideExtent): Expr | number {
  if (tide.coloured <= 0) return 0;
  const position: Expr = ["coalesce", ["get", "pt"], NOT_RANKED];
  return ["case", ["<", position, tide.red], 2, ["<", position, tide.coloured], 1, 0];
}

/**
 * Biểu thức MapLibre cho mức của một tuyến khi trạng thái mưa và triều đã biết.
 * `overrides` là mức riêng của vài tuyến (do trạm mưa gần đó hoặc do báo cáo), khóa là `id` của tuyến trong lớp bản đồ.
 */
export function levelExpression(rain: DayState, tide: TideExtent, overrides: Record<string, number> = {}): Expr {
  // Cầu, cầu vượt (ev = 1) không bao giờ tô ngập: mặt cầu không ngập dù đường dưới gầm ngập.
  const base: Expr = ["case", ["==", ["coalesce", ["get", "ev"], 0], 1], 0, ["max", causeExpression("br", rain), tideExpression(tide)]];
  const cases: unknown[] = [];
  for (const level of [0, 1, 2]) {
    const ids = Object.keys(overrides).filter((id) => overrides[id] === level).map(Number);
    if (ids.length > 0) cases.push(ids, level);
  }
  return cases.length > 0 ? ["match", ["id"], ...cases, base] : base;
}

/** Các dòng giải thích trên thẻ của một tuyến: mức đến từ đâu, và tuyến có từng ngập không. */
export function routeReasons(route: RouteProps, rain: DayState, tide: TideExtent, tideNow = ""): string[] {
  const lines: string[] = [];
  if (causeLevel(route.br, rain) > 0) {
    const group = route.br === 2 ? "5% tuyến dễ ngập nhất" : "20% tuyến dễ ngập nhất";
    lines.push(`Mô hình xếp tuyến này vào nhóm ${group} do mưa, và mưa hôm nay ở mức ${STATE_LABEL[rain]}.`);
  }
  const byTide = tideLevel(route.pt, tide);
  if (byTide > 0) {
    const top = (byTide === 2 ? tide.red : tide.coloured).toLocaleString("vi-VN");
    lines.push(`Triều đang lên${tideNow ? ` (${tideNow})` : ""}: ở mực nước này bản đồ tô ${top} tuyến dễ ngập nhất do triều, và tuyến này nằm trong số đó.`);
  }
  const history = [route.hr > 0 ? `${route.hr} ngày do mưa` : "", route.ht > 0 ? `${route.ht} ngày do triều` : ""].filter(Boolean);
  if (history.length > 0) lines.push(`Từng có ghi nhận ngập trước 2025: ${history.join(", ")}.`);
  return lines;
}

/** "13:00" từ một mốc giờ ISO có múi giờ Việt Nam. */
export function clockOf(iso: string): string {
  const match = /T(\d{2}:\d{2})/.exec(iso);
  return match ? match[1] : "";
}
