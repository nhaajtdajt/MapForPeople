// Nơi duy nhất giao diện gọi máy chủ. Khóa REST của Goong và TomTom chỉ nằm ở máy chủ.

import type { FeatureCollection, Point } from "geojson";

import type { DayState } from "./lib/risk";

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
  error: string | null;
  hours: RiskHour[];
  layer: { url: string } | null;
}

export interface FloodPointProps {
  no: number;
  cause: "rain" | "tide";
  place: string;
  located_by: string;
  routes: string;
}

export type FloodPoints = FeatureCollection<Point, FloodPointProps> & { source: string };

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
};

/** Đường dẫn đầy đủ tới một tài nguyên của máy chủ, cho những chỗ MapLibre tự tải (lớp tuyến). */
export function serverUrl(path: string): string {
  return `${BASE}${path}`;
}

export function isAbort(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}
