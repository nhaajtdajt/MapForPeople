import type { RiskHour, RiskState } from "../api";
import type { FloodNote } from "../components/PlaceCard";
import type { MapHit } from "../MapView";
import { clockOf, LEVEL_LABEL, routeLevel, routeReasons, STATE_LABEL } from "./risk";

/** Dòng trạng thái dưới ô tìm kiếm: mưa và triều của cả thành phố theo mô hình, kèm giờ tính. */
export function riskLine(risk: RiskState | null): string {
  if (!risk) return "Chưa có mức nguy cơ";
  const now = risk.hours[0];
  const text = `Mưa: ${STATE_LABEL[now.rain.state]} · Triều: ${STATE_LABEL[now.tide.state]} · ${clockOf(now.valid_time)}`;
  return risk.stale ? `${text} · số liệu cũ` : text;
}

/** Nội dung ô thông tin ngập trên thẻ địa điểm, từ thứ người dùng vừa chạm trúng. */
export function floodNote(hit: MapHit | null, now: RiskHour | null): FloodNote | null {
  if (!hit) return null;
  if (hit.kind === "point") {
    const cause = hit.point.cause === "tide" ? "triều cường" : "mưa lớn, nước không thoát kịp";
    return {
      tone: "info",
      title: `Điểm ngập đã công bố: ${hit.point.place}`,
      lines: [`Nguyên nhân: ${cause}.`, "Nguồn: Phòng CSGT Công an TP.HCM, công bố ngày 06/10/2026."],
    };
  }
  if (!now) return null;
  const level = routeLevel(hit.route, now.rain.state, now.tide.state);
  if (level === 0) return null;
  return {
    tone: level === 2 ? "high" : "medium",
    title: `${hit.route.name || "Đường chưa có tên"}: nguy cơ ngập mức ${LEVEL_LABEL[level]}`,
    lines: [...routeReasons(hit.route, now.rain.state, now.tide.state), "Đây là dự báo của mô hình, chưa có ai quan sát tại chỗ."],
  };
}
