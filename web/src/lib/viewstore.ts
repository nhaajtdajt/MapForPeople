import type { CityKey } from "../api";

const KEY = "floodrisk-view";
const CITY_KEYS: readonly string[] = ["hcm", "danang"];

export interface SavedView {
  city: CityKey;
  center: [number, number]; // lon, lat
  zoom: number;
}

type Store = Pick<Storage, "getItem" | "setItem">;

function browserStore(): Store | null {
  try {
    return window.localStorage;
  } catch {
    return null; // cửa sổ riêng tư hoặc bị chặn
  }
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

/** Đọc khung nhìn lần trước. Mọi giá trị hỏng hoặc không đọc được đều cho `null`, không bao giờ ném lỗi. */
export function loadView(store: Store | null = browserStore()): SavedView | null {
  if (!store) return null;
  try {
    const raw = store.getItem(KEY);
    if (!raw) return null;
    const value = JSON.parse(raw) as Partial<SavedView>;
    const [lon, lat] = value.center ?? [];
    if (typeof value.city !== "string" || !CITY_KEYS.includes(value.city)) return null;
    if (!isFiniteNumber(lon) || !isFiniteNumber(lat) || !isFiniteNumber(value.zoom)) return null;
    if (lon < -180 || lon > 180 || lat < -90 || lat > 90 || value.zoom < 0 || value.zoom > 24) return null;
    return { city: value.city as CityKey, center: [lon, lat], zoom: value.zoom };
  } catch {
    return null;
  }
}

export function saveView(view: SavedView, store: Store | null = browserStore()): void {
  if (!store) return;
  try {
    store.setItem(KEY, JSON.stringify(view));
  } catch {
    // đầy bộ nhớ hoặc bị chặn: bỏ qua, ứng dụng vẫn chạy
  }
}
