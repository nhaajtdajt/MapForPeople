import type { Health } from "../api";

export function formatCoords(lat: number, lon: number): string {
  return `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
}

/**
 * Dòng phụ dưới tên địa điểm. Goong thường trả địa chỉ bắt đầu bằng chính tên đó
 * ("Chợ Bến Thành, Bến Thành, Hồ Chí Minh"), nên bỏ phần trùng để thẻ không lặp lại tên.
 */
export function addressRest(name: string, address: string): string {
  const full = address.trim();
  const title = name.trim();
  if (!full || full === title) return "";
  if (title && full.startsWith(title)) return full.slice(title.length).replace(/^[\s,]+/, "");
  return full;
}

const PART_LABELS: Record<string, string> = {
  evidence: "báo cáo người dùng",
  levels: "mức nguy cơ",
  scenarios: "kịch bản",
  hourly: "tác vụ mỗi giờ",
};

export function fakePartLabels(health: Health | null): string[] {
  if (!health) return [];
  return Object.entries(health.parts)
    .filter(([, state]) => state === "fake")
    .map(([part]) => PART_LABELS[part] ?? part);
}

/** Nhãn nhỏ cho dữ liệu mẫu hoặc bản giả; rỗng khi mọi thứ đều thật (spec 01, mục 3.2). */
export function statusChipText(health: Health | null): string | null {
  if (!health) return null;
  if (health.data === "sample") return "Dữ liệu mẫu";
  const fakes = fakePartLabels(health);
  return fakes.length > 0 ? `Đang dùng bản giả: ${fakes.join(", ")}` : null;
}
