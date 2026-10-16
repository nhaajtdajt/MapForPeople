import {
  GeolocateControl,
  Map as MapLibreMap,
  Marker,
  NavigationControl,
  ScaleControl,
  setWorkerUrl,
  type ExpressionSpecification,
  type FilterSpecification,
  type GeoJSONSource,
  type IControl,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
// MapLibre 6 tìm worker cạnh file của chính nó, nhưng bản dựng Vite gộp mã vào /assets/index-*.js nên worker biến mất
// ("Worker failed to load"). Để Vite đóng gói worker thành tài nguyên riêng rồi khai báo đường dẫn cho MapLibre.
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import type { FeatureCollection } from "geojson";
import { useEffect, useRef, useState } from "react";

import { serverUrl, type Camera, type FloodPointProps, type FloodPoints, type FloodReport, type HistoryPlace, type RouteOption } from "./api";
import { addRouteLayers, selectRouteAtPoint, updateRouteLayers } from "./lib/routeLayer";
import type { DirectionEndpoint } from "./lib/useDirections";
import { levelExpression, NO_TIDE, type DayState, type RouteProps, type TideExtent } from "./lib/risk";

setWorkerUrl(workerUrl);

const MAP_KEY: string = import.meta.env.VITE_GOONG_MAP_KEY ?? "";
const STYLE_URL = `https://tiles.goong.io/assets/goong_map_web.json?api_key=${MAP_KEY}`;
const PIN_COLOR = "#1d4ed8";

// Lớp nguy cơ: các tuyến mô hình xếp vào nhóm A hoặc B, tô theo mức của giờ này (xem lib/risk.ts).
const RISK_SOURCE = "risk-routes";
const POINT_SOURCE = "flood-points";
const POINT_LAYER = "flood-points";
const CAMERA_SOURCE = "cameras";
const CAMERA_LAYER = "cameras";
const REPORT_SOURCE = "reports";
const REPORT_LAYER = "reports";
const HISTORY_SOURCE = "history-places";
const HISTORY_LAYER = "history-places";
// Chỗ ngập thật khi xem lại: xanh lá là app báo đúng, đỏ viền là app bỏ sót; chỗ camera thấy khô: xanh nhạt là đúng, cam là báo thừa.
export const HISTORY_COLOR = { hit: "#15803d", miss: "#dc2626", quiet_ok: "#0d9488", false_alarm: "#ea580c" } as const;
export const CAMERA_COLOR = "#475569";
export const REPORT_COLOR = { flooded: "#b91c1c", clear: "#15803d" } as const;
export const LEVEL_COLOR = { 1: "#f59e0b", 2: "#dc2626" } as const;
export const POINT_COLOR = { rain: "#2563eb", tide: "#0d9488" } as const;
const MAJOR_CLASSES = ["motorway", "trunk", "primary", "secondary", "tertiary", "motorway_link", "trunk_link", "primary_link", "secondary_link", "tertiary_link"];
const MINOR_MIN_ZOOM = 13; // đường nhỏ chỉ hiện khi phóng gần, để khung nhìn cả thành phố không kín màu
const RISK_LAYERS = [
  { id: "risk-medium-minor", level: 1, major: false },
  { id: "risk-medium-major", level: 1, major: true },
  { id: "risk-high-minor", level: 2, major: false },
  { id: "risk-high-major", level: 2, major: true },
] as const;
const TAP_RADIUS_PX = 7;
const EMPTY: FeatureCollection = { type: "FeatureCollection", features: [] };

/** Thứ người dùng chạm trúng trên lớp ngập, nếu có. */
export type MapHit =
  | { kind: "route"; route: RouteProps; id: number }
  | { kind: "point"; point: FloodPointProps }
  | { kind: "camera"; camera: Camera }
  | { kind: "history"; place: HistoryPlace };

export interface RiskView {
  url: string; // đường dẫn lớp tuyến trên máy chủ, đổi khi mô hình được dựng lại
  rain: DayState;
  tide: TideExtent; // phần tô theo triều, xem lib/risk.ts
  overrides: Record<string, number>; // mức riêng của vài tuyến, xem lib/risk.ts
}

function riskFilter(level: number, major: boolean, risk: Pick<RiskView, "rain" | "tide" | "overrides">): FilterSpecification {
  const isMajor = ["in", ["get", "cls"], ["literal", MAJOR_CLASSES]];
  const levelNow = levelExpression(risk.rain, risk.tide, risk.overrides);
  return ["all", ["==", levelNow, level], major ? isMajor : ["!", isMajor]] as unknown as FilterSpecification;
}

const QUIET: Pick<RiskView, "rain" | "tide" | "overrides"> = { rain: "quiet", tide: NO_TIDE, overrides: {} };

function pointFeatures<T extends { lat: number; lon: number }>(items: T[]): FeatureCollection {
  return {
    type: "FeatureCollection",
    features: items.map((item) => ({ type: "Feature", geometry: { type: "Point", coordinates: [item.lon, item.lat] }, properties: { ...item } })),
  };
}

function addRiskLayers(map: MapLibreMap): void {
  // Vẽ dưới chữ của bản đồ nền để tên đường vẫn đọc được.
  const firstSymbol = map.getStyle().layers.find((layer) => layer.type === "symbol")?.id;
  const hasHistory: ExpressionSpecification = [">", ["+", ["get", "hr"], ["get", "ht"]], 0];
  map.addSource(RISK_SOURCE, { type: "geojson", data: EMPTY });
  for (const layer of RISK_LAYERS) {
    const base = layer.major ? 1 : 0.6;
    map.addLayer(
      {
        id: layer.id,
        type: "line",
        source: RISK_SOURCE,
        minzoom: layer.major ? 9 : MINOR_MIN_ZOOM,
        filter: riskFilter(layer.level, layer.major, QUIET),
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-color": LEVEL_COLOR[layer.level],
          "line-width": ["interpolate", ["linear"], ["zoom"], 10, 1.5 * base, 14, 4 * base, 17, 9 * base],
          // Tuyến từng có ghi nhận ngập được tô đậm; tuyến chỉ do mô hình xếp hạng thì nhạt hơn.
          "line-opacity": ["case", hasHistory, 0.95, 0.55],
        },
      },
      firstSymbol,
    );
  }
  map.addSource(POINT_SOURCE, { type: "geojson", data: EMPTY });
  map.addLayer({
    id: POINT_LAYER,
    type: "circle",
    source: POINT_SOURCE,
    minzoom: 9,
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 10, 3, 14, 6, 17, 9],
      "circle-color": ["match", ["get", "cause"], "tide", POINT_COLOR.tide, POINT_COLOR.rain],
      "circle-stroke-color": "#ffffff",
      "circle-stroke-width": 1.5,
    },
  });
  map.addSource(CAMERA_SOURCE, { type: "geojson", data: EMPTY });
  map.addLayer({
    id: CAMERA_LAYER,
    type: "circle",
    source: CAMERA_SOURCE,
    minzoom: 12,
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 12, 2.5, 15, 5, 17, 7],
      "circle-color": CAMERA_COLOR,
      "circle-opacity": ["case", ["get", "has_image"], 0.9, 0.3],
      "circle-stroke-color": "#ffffff",
      "circle-stroke-width": 1,
    },
  });
  map.addSource(HISTORY_SOURCE, { type: "geojson", data: EMPTY });
  map.addLayer({
    id: HISTORY_LAYER,
    type: "circle",
    source: HISTORY_SOURCE,
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 10, 7, 15, 12],
      "circle-color": ["match", ["get", "result"], "miss", "#ffffff", "hit", HISTORY_COLOR.hit, "false_alarm", HISTORY_COLOR.false_alarm, HISTORY_COLOR.quiet_ok],
      "circle-stroke-color": ["match", ["get", "result"], "miss", HISTORY_COLOR.miss, "#ffffff"],
      "circle-stroke-width": ["match", ["get", "result"], "miss", 4, 2.5],
    },
  });
  const font = map
    .getStyle()
    .layers.map((layer) => (layer.type === "symbol" ? layer.layout?.["text-font"] : undefined))
    .find((value): value is string[] => Array.isArray(value) && value.every((item) => typeof item === "string"));
  if (font) {
    map.addLayer({
      id: `${HISTORY_LAYER}-labels`,
      type: "symbol",
      source: HISTORY_SOURCE,
      layout: {
        "text-field": ["concat", ["match", ["get", "result"], "hit", "Đúng · ", "miss", "Sót · ", "false_alarm", "Báo thừa · ", ""], ["get", "name"]],
        "text-font": font,
        "text-size": 12,
        "text-offset": [0, 1.5],
        "text-anchor": "top",
        "text-max-width": 10,
        // Vài nhãn đối chiếu luôn hiện, không nhường chỗ cho nhãn của bản đồ nền.
        "text-allow-overlap": true,
        "text-ignore-placement": true,
      },
      paint: {
        "text-color": ["match", ["get", "result"], "miss", HISTORY_COLOR.miss, "hit", HISTORY_COLOR.hit, "false_alarm", HISTORY_COLOR.false_alarm, "#0f1d2e"],
        "text-halo-color": "#ffffff",
        "text-halo-width": 1.6,
      },
    });
  }
  map.addSource(REPORT_SOURCE, { type: "geojson", data: EMPTY });
  map.addLayer({
    id: REPORT_LAYER,
    type: "circle",
    source: REPORT_SOURCE,
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 10, 5, 15, 9],
      "circle-color": ["match", ["get", "status"], "clear", REPORT_COLOR.clear, REPORT_COLOR.flooded],
      "circle-stroke-color": "#ffffff",
      "circle-stroke-width": 2,
    },
  });
}

export interface FlyTarget {
  lon: number;
  lat: number;
  zoom?: number;
  nonce: number; // đổi giá trị để bay lại tới cùng một chỗ
}

export interface MapViewState {
  center: [number, number]; // lon, lat
  zoom: number;
}

interface Props {
  initial: MapViewState;
  pin: { lat: number; lon: number } | null;
  flyTo: FlyTarget | null;
  risk: RiskView | null;
  showRisk: boolean;
  points: FloodPoints | null;
  showPoints: boolean;
  cameras: Camera[];
  showCameras: boolean;
  reports: FloodReport[];
  historyPlaces: HistoryPlace[];
  routes: RouteOption[];
  selectedRouteId: number | null;
  routeRevision: number;
  directionOrigin: DirectionEndpoint | null;
  directionDestination: DirectionEndpoint | null;
  directionsOpen: boolean;
  onRouteSelect: (routeId: number) => void;
  onTap: (lat: number, lon: number, hit: MapHit | null) => void;
  onMoveEnd: (view: MapViewState) => void;
  onLocate: (lat: number, lon: number, accuracy: number) => void;
  onNotice: (message: string) => void;
}

export const INSECURE_LOCATE_MESSAGE = "Cần HTTPS để dùng định vị. Hãy chạm vào bản đồ để chọn điểm.";
export const DENIED_LOCATE_MESSAGE = "Chưa lấy được vị trí của bạn. Vẫn có thể chạm vào bản đồ để chọn điểm.";

/** Nút định vị thay cho GeolocateControl khi trang không phải HTTPS: trình duyệt sẽ từ chối định vị. */
class DisabledLocateControl implements IControl {
  private container: HTMLElement | null = null;
  constructor(private readonly onClick: () => void) {}

  onAdd(): HTMLElement {
    const container = document.createElement("div");
    container.className = "maplibregl-ctrl maplibregl-ctrl-group";
    const button = document.createElement("button");
    button.type = "button";
    button.title = "Vị trí của tôi";
    button.setAttribute("aria-label", "Vị trí của tôi (cần HTTPS)");
    button.className = "maplibregl-ctrl-geolocate";
    button.style.opacity = "0.5";
    button.addEventListener("click", this.onClick);
    const icon = document.createElement("span");
    icon.className = "maplibregl-ctrl-icon";
    icon.setAttribute("aria-hidden", "true");
    button.appendChild(icon);
    container.appendChild(button);
    this.container = container;
    return container;
  }

  onRemove(): void {
    this.container?.remove();
    this.container = null;
  }
}

export default function MapView({ initial, pin, flyTo, risk, showRisk, points, showPoints, cameras, showCameras, reports, historyPlaces, routes, selectedRouteId, routeRevision, directionOrigin, directionDestination, directionsOpen, onRouteSelect, onTap, onMoveEnd, onLocate, onNotice }: Props) {
  const [ready, setReady] = useState(false); // kiểu bản đồ nền đã nạp xong, thêm lớp được
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const markerRef = useRef<Marker | null>(null);
  // Các hàm gọi lại mới nhất, để bản đồ chỉ cần tạo một lần.
  const callbacks = useRef({ onTap, onMoveEnd, onLocate, onNotice, onRouteSelect });
  callbacks.current = { onTap, onMoveEnd, onLocate, onNotice, onRouteSelect };

  useEffect(() => {
    if (!MAP_KEY || !containerRef.current) return;
    const map = new MapLibreMap({
      container: containerRef.current,
      style: STYLE_URL,
      center: initial.center,
      zoom: initial.zoom,
      attributionControl: { compact: true },
    });
    mapRef.current = map;

    map.addControl(new NavigationControl({ visualizePitch: true }), "bottom-right");
    if (window.isSecureContext) {
      const locate = new GeolocateControl({
        positionOptions: { enableHighAccuracy: true },
        trackUserLocation: true,
        showUserLocation: true,
        showAccuracyCircle: true,
      });
      locate.on("geolocate", (event) => {
        callbacks.current.onLocate(event.coords.latitude, event.coords.longitude, event.coords.accuracy);
      });
      locate.on("error", () => callbacks.current.onNotice(DENIED_LOCATE_MESSAGE));
      map.addControl(locate, "bottom-right");
    } else {
      map.addControl(new DisabledLocateControl(() => callbacks.current.onNotice(INSECURE_LOCATE_MESSAGE)), "bottom-right");
    }
    map.addControl(new ScaleControl({ unit: "metric" }), "bottom-left");

    map.on("load", () => {
      addRiskLayers(map);
      addRouteLayers(map);
      setReady(true);
    });
    map.on("click", (event) => {
      if (selectRouteAtPoint(map, event.point, callbacks.current.onRouteSelect)) return;
      const { x, y } = event.point;
      const layers = [HISTORY_LAYER, CAMERA_LAYER, POINT_LAYER, ...RISK_LAYERS.map((layer) => layer.id)].filter((id) => map.getLayer(id));
      const hits = layers.length > 0 ? map.queryRenderedFeatures([[x - TAP_RADIUS_PX, y - TAP_RADIUS_PX], [x + TAP_RADIUS_PX, y + TAP_RADIUS_PX]], { layers }) : [];
      const past = hits.find((feature) => feature.layer.id === HISTORY_LAYER);
      if (past) {
        const props = past.properties as Record<string, unknown>;
        const place = { ...props, basis: JSON.parse(String(props.basis)), segments: JSON.parse(String(props.segments)) } as HistoryPlace;
        callbacks.current.onTap(event.lngLat.lat, event.lngLat.lng, { kind: "history", place });
        return;
      }
      const camera = hits.find((feature) => feature.layer.id === CAMERA_LAYER);
      const point = hits.find((feature) => feature.layer.id === POINT_LAYER);
      const route = hits.find((feature) => feature.layer.id !== POINT_LAYER && feature.layer.id !== CAMERA_LAYER && feature.layer.id !== HISTORY_LAYER);
      const hit: MapHit | null = camera
        ? { kind: "camera", camera: camera.properties as Camera }
        : point
          ? { kind: "point", point: point.properties as FloodPointProps }
          : route
            ? { kind: "route", route: route.properties as RouteProps, id: Number(route.id) }
            : null;
      callbacks.current.onTap(event.lngLat.lat, event.lngLat.lng, hit);
    });
    map.on("moveend", () => {
      const center = map.getCenter();
      callbacks.current.onMoveEnd({ center: [center.lng, center.lat], zoom: map.getZoom() });
    });

    return () => {
      markerRef.current?.remove();
      markerRef.current = null;
      map.remove();
      mapRef.current = null;
      setReady(false);
    };
    // Chỉ tạo bản đồ một lần; khung nhìn ban đầu không được tạo lại bản đồ.
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (!pin) {
      markerRef.current?.remove();
      markerRef.current = null;
      return;
    }
    if (!markerRef.current) markerRef.current = new Marker({ color: PIN_COLOR });
    markerRef.current.setLngLat([pin.lon, pin.lat]).addTo(map);
  }, [pin]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !flyTo) return;
    map.flyTo({ center: [flyTo.lon, flyTo.lat], zoom: flyTo.zoom ?? Math.max(map.getZoom(), 16), essential: true });
  }, [flyTo]);

  const riskUrl = risk?.url ?? null;
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    (map.getSource(RISK_SOURCE) as GeoJSONSource).setData(riskUrl ? serverUrl(riskUrl) : EMPTY);
  }, [ready, riskUrl]);

  const rain = risk?.rain ?? "quiet";
  const tideKey = JSON.stringify(risk?.tide ?? NO_TIDE);
  const overridesKey = JSON.stringify(risk?.overrides ?? {});
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const now = { rain, tide: JSON.parse(tideKey) as TideExtent, overrides: JSON.parse(overridesKey) as Record<string, number> };
    for (const layer of RISK_LAYERS) {
      map.setFilter(layer.id, riskFilter(layer.level, layer.major, now));
      map.setLayoutProperty(layer.id, "visibility", showRisk ? "visible" : "none");
    }
  }, [ready, rain, tideKey, overridesKey, showRisk]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    (map.getSource(CAMERA_SOURCE) as GeoJSONSource).setData(pointFeatures(cameras));
    map.setLayoutProperty(CAMERA_LAYER, "visibility", showCameras ? "visible" : "none");
  }, [ready, cameras, showCameras]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    (map.getSource(REPORT_SOURCE) as GeoJSONSource).setData(pointFeatures(reports));
  }, [ready, reports]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    // MapLibre chỉ giữ thuộc tính phẳng: mảng lý do và số đoạn được gói thành chuỗi, mở lại khi chạm.
    const flat = historyPlaces.map((place) => ({ ...place, basis: JSON.stringify(place.basis), segments: JSON.stringify(place.segments) }));
    (map.getSource(HISTORY_SOURCE) as GeoJSONSource).setData(pointFeatures(flat));
    if (historyPlaces.length > 0) {
      const lats = historyPlaces.map((p) => p.lat);
      const lons = historyPlaces.map((p) => p.lon);
      map.fitBounds([[Math.min(...lons), Math.min(...lats)], [Math.max(...lons), Math.max(...lats)]], { padding: { top: 260, bottom: 70, left: 50, right: 60 }, maxZoom: 15, duration: 900 });
    }
  }, [ready, historyPlaces]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    (map.getSource(POINT_SOURCE) as GeoJSONSource).setData(points ?? EMPTY);
    map.setLayoutProperty(POINT_LAYER, "visibility", showPoints ? "visible" : "none");
  }, [ready, points, showPoints]);

  const lastRouteRevision = useRef(0);
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const fitToRoutes = directionsOpen && routes.length > 0 && routeRevision !== lastRouteRevision.current;
    lastRouteRevision.current = routeRevision;
    updateRouteLayers(map, routes, selectedRouteId, directionOrigin, directionDestination, fitToRoutes);
  }, [ready, routes, selectedRouteId, routeRevision, directionOrigin, directionDestination, directionsOpen]);
  if (!MAP_KEY) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-center text-ink-soft">
        Thiếu khóa bản đồ. Đặt VITE_GOONG_MAP_KEY trong file .env ở thư mục gốc rồi chạy lại.
      </div>
    );
  }
  return <div ref={containerRef} className="h-full w-full" data-testid="map" />;
}
