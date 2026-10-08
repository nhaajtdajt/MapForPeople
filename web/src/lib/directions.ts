export type Vehicle = "bike" | "car";

export interface RoutePoint {
  lat: number;
  lon: number;
}

export interface RouteRequestParams {
  city: "hcm";
  origin: string;
  destination: string;
  vehicle: Vehicle;
}

export function buildRouteParams(origin: RoutePoint, destination: RoutePoint, vehicle: Vehicle): RouteRequestParams {
  return {
    city: "hcm",
    origin: `${origin.lat},${origin.lon}`,
    destination: `${destination.lat},${destination.lon}`,
    vehicle,
  };
}

export function chooseRoute<Route extends { recommended: boolean }>(routes: readonly Route[]): Route | null {
  return routes.find((route) => route.recommended) ?? routes[0] ?? null;
}

export function prioritizeRoutes<Route extends { recommended: boolean; duration_s: number }>(routes: readonly Route[]): Route[] {
  return [...routes].sort(
    (first, second) => Number(second.recommended) - Number(first.recommended) || first.duration_s - second.duration_s,
  );
}
export function formatDuration(durationSeconds: number): string {
  if (durationSeconds < 30) return "Dưới 1 phút";
  const minutes = Math.max(1, Math.round(durationSeconds / 60));
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  if (hours === 0) return `${minutes} phút`;
  return remainder === 0 ? `${hours} giờ` : `${hours} giờ ${remainder} phút`;
}

export function formatDistance(distanceMeters: number): string {
  if (distanceMeters < 1000) return `${Math.round(distanceMeters)} m`;
  const kilometers = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 1, minimumFractionDigits: 1 }).format(distanceMeters / 1000);
  return `${kilometers} km`;
}

export function formatArrival(arriveAt: string): string {
  const date = new Date(arriveAt);
  if (!Number.isFinite(date.getTime())) return "Không rõ giờ đến";
  return new Intl.DateTimeFormat("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone: "Asia/Ho_Chi_Minh",
  }).format(date);
}
