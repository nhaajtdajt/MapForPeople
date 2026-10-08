import type { RiskHour, RiskState } from "../api";
import type { FloodNote } from "../components/PlaceCard";
import type { MapHit } from "../MapView";
import { clockOf, LEVEL_LABEL, routeLevel, routeReasons, STATE_LABEL } from "./risk";

/** Dòng trạng thái dưới ô tìm kiếm: mưa và triều của cả thành phố theo mô hình, kèm giờ tính. */
export function riskLine(risk: RiskState | null): string {
  if (!risk) return "Chưa có mức nguy cơ";
  const now = risk.hours[0];
  const tide = risk.local?.tide ? ` (Phú An ${risk.local.tide.level_m.toFixed(2).replace(".", ",")} m)` : "";
  const rain = risk.rain_missing ? "chưa có số liệu" : STATE_LABEL[risk.states.rain];
  const text = `Mưa: ${rain} · Triều: ${STATE_LABEL[risk.states.tide]}${tide} · ${clockOf(now.valid_time)}`;
  return risk.stale && !risk.rain_missing ? `${text} · số liệu cũ` : text;
}

/** Nội dung ô thông tin ngập trên thẻ địa điểm, từ thứ người dùng vừa chạm trúng. */
export function floodNote(hit: MapHit | null, now: RiskHour | null, risk: RiskState | null = null): FloodNote | null {
  if (!hit || hit.kind === "camera") return null;
  if (hit.kind === "point") {
    const cause = hit.point.cause === "tide" ? "triều cường" : "mưa lớn, nước không thoát kịp";
    return {
      tone: "info",
      title: `Điểm ngập đã công bố: ${hit.point.place}`,
      lines: [`Nguyên nhân: ${cause}.`, "Nguồn: Phòng CSGT Công an TP.HCM, công bố ngày 06/10/2026."],
    };
  }
  if (!now) return null;
  const rain = risk?.states.rain ?? now.rain.state;
  const tide = risk?.states.tide ?? now.tide.state;
  const own = risk?.overrides[String(hit.id)];
  const level = (own ?? routeLevel(hit.route, rain, tide)) as 0 | 1 | 2;
  if (level === 0) return null;
  const name = hit.route.name || "Đường chưa có tên";
  const reported = risk?.reports.find((r) => r.id === hit.id);
  if (reported && (reported.shown === "high" || reported.shown === "moderate" || reported.shown === "unknown")) {
    const who = reported.sources.includes("camera") ? "camera và người đi đường" : "người đi đường";
    return { tone: "high", title: `${name}: đang có báo ngập`, lines: [`${reported.count} báo cáo từ ${who} trong 90 phút qua.`, ...routeReasons(hit.route, rain, tide)] };
  }
  const lines = routeReasons(hit.route, rain, tide);
  if (own !== undefined && lines.length === 0) lines.push("Trạm đo mưa gần tuyến này đang ghi nhận mưa lớn.");
  return {
    tone: level === 2 ? "high" : "medium",
    title: `${name}: nguy cơ ngập mức ${LEVEL_LABEL[level]}`,
    lines: [...lines, "Đây là dự báo, chưa có ai quan sát tại chỗ."],
  };
}
