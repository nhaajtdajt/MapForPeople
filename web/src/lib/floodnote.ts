import type { RiskHour, RiskState } from "../api";
import type { FloodNote } from "../components/PlaceCard";
import type { MapHit } from "../MapView";
import { clockOf, LEVEL_LABEL, NO_TIDE, routeLevel, routeReasons, STATE_LABEL, type DayState, type TideExtent } from "./risk";

/** "19:40" theo giờ Việt Nam từ một mốc giờ ISO bất kỳ múi giờ. */
export function clockInVietnam(iso: string): string {
  const time = new Date(iso);
  if (Number.isNaN(time.getTime())) return "";
  return new Date(time.getTime() + 7 * 3600_000).toISOString().slice(11, 16);
}

function metres(level: number): string {
  return `${level.toFixed(2).replace(".", ",")} m`;
}

/** Phần tô theo triều đang dùng: lấy từ máy chủ, không có thì không tô. */
export function tideExtentOf(risk: Pick<RiskState, "tide_extent"> | null): TideExtent {
  return risk?.tide_extent ?? NO_TIDE;
}

/** Nội dung ô thông tin ngập trên thẻ địa điểm, từ thứ người dùng vừa chạm trúng. */
export function floodNote(hit: MapHit | null, now: RiskHour | null, risk: RiskState | null = null): FloodNote | null {
  if (!hit || hit.kind === "camera" || hit.kind === "history") return null;
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
  const tide = tideExtentOf(risk);
  const tideNow = risk?.local?.tide ? `Phú An ${metres(risk.local.tide.level_m)}` : "";
  const own = risk?.overrides[String(hit.id)];
  const level = (own ?? routeLevel(hit.route, rain, tide)) as 0 | 1 | 2;
  if (level === 0) return null;
  const name = hit.route.name || "Đường chưa có tên";
  const reported = risk?.reports.find((r) => r.id === hit.id);
  if (reported && (reported.shown === "high" || reported.shown === "moderate" || reported.shown === "unknown")) {
    const who = reported.sources.includes("camera") ? "camera và người đi đường" : "người đi đường";
    return { tone: "high", title: `${name}: đang có báo ngập`, lines: [`${reported.count} báo cáo từ ${who} trong 90 phút qua.`, ...routeReasons(hit.route, rain, tide, tideNow)] };
  }
  const lines = routeReasons(hit.route, rain, tide, tideNow);
  if (own !== undefined && !reported) {
    lines.length = 0;
    const seen = risk?.radar && (risk.radar.watch.includes(hit.id) || risk.radar.alert.includes(hit.id));
    const source = seen ? `Radar lúc ${clockInVietnam(risk.radar!.image_time)} thấy mưa lớn tại đây` : "Trạm đo mưa trong 4 km quanh tuyến này đang ghi nhận mưa lớn";
    if (hit.route.br > 0) lines.push(`${source}, và mô hình xếp tuyến này vào nhóm dễ ngập do mưa.`);
    if (hit.route.hr + hit.route.ht > 0) lines.push(`Từng có ghi nhận ngập trước 2025: ${hit.route.hr + hit.route.ht} ngày.`);
  }
  return {
    tone: level === 2 ? "high" : "medium",
    title: `${name}: nguy cơ ngập mức ${LEVEL_LABEL[level]}`,
    lines: [...lines, "Đây là dự báo, chưa có ai quan sát tại chỗ."],
  };
}

export type Tone = "quiet" | "watch" | "alert";

/** Thanh trạng thái gọn: mưa và triều mỗi thứ một ô, kèm đỉnh triều kế tiếp và giờ đọc số liệu. */
export interface StatusParts {
  rain: { tone: Tone; text: string };
  tide: { tone: Tone; text: string };
  peak: { tone: Tone; text: string } | null;
  updated: string;
  details: string[];
}

const TONE_OF: Record<DayState, Tone> = { quiet: "quiet", watch: "watch", alert: "alert" };

function tideTone(level: number): Tone {
  return level >= 1.5 ? "alert" : level >= 1.4 ? "watch" : "quiet";
}

export function statusParts(risk: RiskState | null): StatusParts | null {
  if (!risk) return null;
  const gauges = risk.local?.gauges ?? [];
  const wet = gauges.filter((g) => g.state !== "quiet");
  const radarAlert = risk.radar?.alert.length ?? 0;
  const radarWatch = risk.radar?.watch.length ?? 0;
  const rainTone: Tone = wet.some((g) => g.state === "alert") || radarAlert > 0 ? "alert" : wet.length > 0 || radarWatch > 0 ? "watch" : "quiet";
  const rainText =
    rainTone === "quiet"
      ? "Không có mưa lớn"
      : wet.length > 0
        ? `Mưa lớn quanh ${wet.length} trạm đo`
        : `Radar thấy mưa lớn`;
  const level = risk.local?.tide?.level_m;
  const tide = level === undefined
    ? { tone: TONE_OF[risk.states.tide], text: `Triều ${STATE_LABEL[risk.states.tide]}` }
    : { tone: tideTone(level), text: `Phú An ${metres(level)}` };
  const ahead = risk.tide_forecast ?? [];
  const top = ahead.length ? ahead.reduce((best, hour) => (hour.level_m > best.level_m ? hour : best)) : null;
  const peak = top ? { tone: tideTone(top.level_m), text: `Đỉnh ${metres(top.level_m)} lúc ${clockOf(top.time)}` } : null;
  const updated = clockInVietnam(risk.local?.at ?? risk.hours[0].valid_time);
  const details = [
    wet.length > 0 ? `Trạm đang mưa lớn: ${wet.map((g) => `${g.name} ${g.last_1h_mm.toLocaleString("vi-VN")} mm/giờ`).join(", ")}.` : "Không trạm đo nào mưa từ 30 mm/giờ.",
    risk.radar ? `Radar lúc ${clockInVietnam(risk.radar.image_time)}: ${radarWatch + radarAlert} tuyến có mưa lớn.` : "Chưa có số liệu radar mới.",
    risk.rain_missing ? "Dự báo mưa chung cả thành phố: chưa có số liệu." : `Dự báo mưa chung cả thành phố: ${STATE_LABEL[risk.model_rain]}.`,
    "Báo động triều tại Phú An: 1,40 m (mức 1), 1,50 m (mức 2), 1,60 m (mức 3).",
  ];
  if (risk.stale && !risk.rain_missing) details.push("Số liệu có thể đã cũ.");
  return { rain: { tone: rainTone, text: rainText }, tide, peak, updated, details };
}
