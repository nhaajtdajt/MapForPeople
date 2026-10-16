// Các địa điểm người dùng vừa chọn khi chỉ đường, giữ trong máy này. Không lưu được (chế độ ẩn danh) thì coi như rỗng.
export interface RecentPlace {
  lat: number;
  lon: number;
  label: string;
  address: string;
}

const KEY = "floodrisk-recent-places";
export const RECENT_LIMIT = 5;

export function loadRecent(): RecentPlace[] {
  try {
    const raw = JSON.parse(window.localStorage.getItem(KEY) ?? "[]");
    return Array.isArray(raw) ? raw.filter((p) => typeof p?.lat === "number" && typeof p?.lon === "number" && typeof p?.label === "string").slice(0, RECENT_LIMIT) : [];
  } catch {
    return [];
  }
}

/** Đưa một địa điểm lên đầu danh sách; địa điểm trùng (cách dưới 30 m) được gộp. */
export function rememberPlace(place: RecentPlace, list: RecentPlace[] = loadRecent()): RecentPlace[] {
  const near = (a: RecentPlace) => Math.abs(a.lat - place.lat) < 0.0003 && Math.abs(a.lon - place.lon) < 0.0003;
  const next = [place, ...list.filter((p) => !near(p))].slice(0, RECENT_LIMIT);
  try {
    window.localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // không lưu được thì thôi
  }
  return next;
}
