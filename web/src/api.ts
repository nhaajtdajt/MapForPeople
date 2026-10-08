// Nơi duy nhất giao diện gọi máy chủ. Khóa REST của Goong và TomTom chỉ nằm ở máy chủ.

import type { FeatureCollection, Point } from "geojson";

import type { DayState } from "./lib/risk";
import type { RouteRequestParams } from "./lib/directions";

const BASE: string = import.meta.env.VITE_API_BASE ?? "";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export type CityKey = "hcm" | "danang";

export interface City {
  key: CityKey;
  name: string;
  center: [number, number]; // lon, lat
  bbox: [number, number, number, number]; // tây, nam, đông, bắc
  has_tide: boolean;
  validated: boolean;
}

export interface Health {
  ok: boolean;
  test_tools: boolean;
  data: "sample" | "real";
  parts: Record<string, "real" | "fake">;
  traffic: Record<string, { source: "tomtom" | "typical"; observed_at: string | null }>;
  last_refresh: string | null;
  last_error: string | null;
}

export interface Suggestion {
  place_id: string;
  main: string;
  secondary: string;
}

export interface PlaceDetail {
  name: string;
  address: string;
  lat: number;
  lon: number;
}

export interface ReverseResult {
  name: string;
  address: string;
  place_id: string | null;
}

export interface CauseNow {
  state: DayState;
  trigger: number;
  max_3h_mm?: number;
  total_24h_mm?: number;
  astro_m?: number;
}

export interface RiskHour {
  valid_time: string;
  rain: CauseNow;
  tide: CauseNow;
  counts: { high: number; medium: number };
}

/** Mức nguy cơ lúc này và hai giờ tới của một thành phố (GET /api/risk). */
export interface RiskState {
  city: CityKey;
  model_version: string;
  generated_at: string;
  rain_source: string;
  stale: boolean;
  /** Chưa lấy được mưa cho mô hình lần nào: trạng thái mưa của thành phố là chưa biết. */
  rain_missing: boolean;
  error: string | null;
  hours: RiskHour[];
  /** Trạng thái đang áp cho cả thành phố: triều đã xét mực nước Phú An. */
  states: { rain: DayState; tide: DayState };
  /** Mức riêng của những tuyến lệch khỏi `states`, khóa là `id` của tuyến trong lớp bản đồ. */
  overrides: Record<string, number>;
  counts_now: { high: number; medium: number };
  /** Tuyến đang có báo cáo: `shown` là mức được báo nhiều nhất (none là "không ngập"). */
  reports: { id: number; shown: "none" | "light" | "unknown" | "moderate" | "high"; count: number; last_at: string; sources: string[] }[];
  local: {
    tide: { station: string; level_m: number; kind: "measured" | "model"; state: DayState } | null;
    gauges: { name: string; lat: number; lon: number; last_1h_mm: number; max_3h_mm: number; total_24h_mm: number; state: DayState }[];
    errors: string[];
  } | null;
  layer: { url: string } | null;
}

export interface Camera {
  id: string;
  name: string;
  lat: number;
  lon: number;
  has_image: boolean;
}

export interface CameraReading {
  state: "ok" | "unusable" | "offline";
  at?: string;
  flooded?: boolean;
  depth_class?: string;
  traffic?: string;
  evidence?: string;
  confidence?: number;
  model?: string;
}

export interface FloodReport {
  id: number;
  route: number;
  lat: number;
  lon: number;
  status: "flooded" | "clear";
  depth: "light" | "medium" | "high" | null;
  depth_label: string | null;
  source: "user" | "camera";
  note: string | null;
  at: string;
}

export interface ReportBody {
  city: CityKey;
  lat: number;
  lon: number;
  status: "flooded" | "clear";
  depth: "light" | "medium" | "high" | null;
  user: string;
}

export interface FloodPointProps {
  no: number;
  cause: "rain" | "tide";
  place: string;
  located_by: string;
  routes: string;
}

export type FloodPoints = FeatureCollection<Point, FloodPointProps> & { source: string };
export interface RouteStep {
  name: string;
  distance_m: number;
  duration_s: number;
  turn: string;
}

export interface RouteOption {
  id: number;
  kind: string;
  recommended: boolean;
  long_detour: boolean;
  distance_m: number;
  duration_s: number;
  arrive_at: string;
  steps: RouteStep[];
  geometry: { type: "LineString"; coordinates: [number, number][] };
  /** Số mét lộ trình đi qua đường đang có mức ngập, theo nguồn; null khi thành phố chưa có mô hình. */
  flood: {
    high_m: number;
    medium_m: number;
    history_m: number;
    confirmed_m: number;
    segments: { name: string; level: number; basis: "report" | "history" | "model"; length_m: number }[];
  } | null;
}

export interface RouteResponse {
  routes: RouteOption[];
  snapped: {
    origin: { lat: number; lon: number; distance_m: number };
    destination: { lat: number; lon: number; distance_m: number };
  };
  traffic: { source: string; observed_at: string | null };
  advice: string | null;
  notes: string[];
}

type Params = Record<string, string | number | undefined>;

async function getJson<T>(path: string, params: Params = {}, signal?: AbortSignal): Promise<T> {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) query.set(key, String(value));
  }
  const suffix = query.size > 0 ? `?${query}` : "";
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}${suffix}`, { signal });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new ApiError(0, "Không kết nối được tới máy chủ");
  }
  if (!response.ok) {
    let detail = `Lỗi ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      // phản hồi không phải JSON: giữ lời mặc định
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

async function postJson<T>(path: string, body?: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      method: "POST",
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "Không kết nối được tới máy chủ");
  }
  if (!response.ok) {
    let detail = `Lỗi ${response.status}`;
    try {
      const data = (await response.json()) as { detail?: unknown };
      if (typeof data.detail === "string") detail = data.detail;
    } catch {
      // phản hồi không phải JSON: giữ lời mặc định
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
}

export const api = {
  health: (signal?: AbortSignal) => getJson<Health>("/api/health", {}, signal),
  cities: (signal?: AbortSignal) => getJson<City[]>("/api/cities", {}, signal),
  autocomplete: (q: string, near?: { lat: number; lon: number }, signal?: AbortSignal) =>
    getJson<Suggestion[]>("/api/places/autocomplete", { q, lat: near?.lat, lon: near?.lon }, signal),
  placeDetail: (placeId: string, signal?: AbortSignal) =>
    getJson<PlaceDetail>("/api/places/detail", { place_id: placeId }, signal),
  reverse: (lat: number, lon: number, signal?: AbortSignal) =>
    getJson<ReverseResult>("/api/places/reverse", { lat, lon }, signal),
  risk: (city: CityKey, signal?: AbortSignal) => getJson<RiskState>("/api/risk", { city }, signal),
  floodPoints: (city: CityKey, signal?: AbortSignal) => getJson<FloodPoints>("/api/risk/points", { city }, signal),
  cameras: (city: CityKey, signal?: AbortSignal) => getJson<Camera[]>("/api/cameras", { city }, signal),
  readCamera: (id: string) => postJson<{ reading: CameraReading }>(`/api/cameras/${id}/read`),
  reports: (city: CityKey, signal?: AbortSignal) => getJson<FloodReport[]>("/api/reports", { city }, signal),
  sendReport: (body: ReportBody) => postJson<{ route: { id: number; name: string } }>("/api/reports", body),
  route: (params: RouteRequestParams, signal?: AbortSignal) => getJson<RouteResponse>("/api/route", { ...params }, signal),
};

/** Đường dẫn đầy đủ tới một tài nguyên của máy chủ, cho những chỗ MapLibre tự tải (lớp tuyến). */
export function serverUrl(path: string): string {
  return `${BASE}${path}`;
}

export function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}
