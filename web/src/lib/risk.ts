// Quy tắc ra mức nguy cơ của một tuyến, giống hệt máy chủ (src/floodrisk/model/levels.py, lấy từ repo mô hình).
// Lớp bản đồ chỉ mang nhóm của tuyến (br, bt); trạng thái của ngày đến từ /api/risk, nên mức được tính ở đây.

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

export function routeLevel(route: Pick<RouteProps, "br" | "bt">, rain: DayState, tide: DayState): Level {
  return Math.max(causeLevel(route.br, rain), causeLevel(route.bt, tide)) as Level;
}

type Expr = unknown[];

function causeExpression(property: "br" | "bt", state: DayState): Expr | number {
  if (state === "alert") return ["get", property];
  if (state === "watch") return ["case", ["==", ["get", property], 2], 1, 0];
  return 0;
}

/** Biểu thức MapLibre cho mức của một tuyến khi trạng thái mưa và triều đã biết. */
export function levelExpression(rain: DayState, tide: DayState): Expr {
  return ["max", causeExpression("br", rain), causeExpression("bt", tide)];
}

/** Các dòng giải thích trên thẻ của một tuyến: mức đến từ đâu, và tuyến có từng ngập không. */
export function routeReasons(route: RouteProps, rain: DayState, tide: DayState): string[] {
  const lines: string[] = [];
  const explain = (band: Band, state: DayState, cause: string) => {
    if (causeLevel(band, state) === 0) return;
    const group = band === 2 ? "5% tuyến dễ ngập nhất" : "20% tuyến dễ ngập nhất";
    lines.push(`Mô hình xếp tuyến này vào nhóm ${group} do ${cause}, và ${cause} hôm nay ở mức ${STATE_LABEL[state]}.`);
  };
  explain(route.br, rain, "mưa");
  explain(route.bt, tide, "triều");
  const history = [route.hr > 0 ? `${route.hr} ngày do mưa` : "", route.ht > 0 ? `${route.ht} ngày do triều` : ""].filter(Boolean);
  if (history.length > 0) lines.push(`Từng có ghi nhận ngập trước 2025: ${history.join(", ")}.`);
  return lines;
}

/** "13:00" từ một mốc giờ ISO có múi giờ Việt Nam. */
export function clockOf(iso: string): string {
  const match = /T(\d{2}:\d{2})/.exec(iso);
  return match ? match[1] : "";
}
