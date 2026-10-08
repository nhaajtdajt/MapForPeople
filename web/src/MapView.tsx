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

import { serverUrl, type FloodPointProps, type FloodPoints, type RouteOption } from "./api";
import { addRouteLayers, selectRouteAtPoint, updateRouteLayers } from "./lib/routeLayer";
import type { DirectionEndpoint } from "./lib/useDirections";
import { levelExpression, type DayState, type RouteProps } from "./lib/risk";

setWorkerUrl(workerUrl);

const MAP_KEY: string = import.meta.env.VITE_GOONG_MAP_KEY ?? "";
const STYLE_URL = `https://tiles.goong.io/assets/goong_map_web.json?api_key=${MAP_KEY}`;
const PIN_COLOR = "#1d4ed8";

// Lớp nguy cơ: các tuyến mô hình xếp vào nhóm A hoặc B, tô theo mức của giờ này (xem lib/risk.ts).
const RISK_SOURCE = "risk-routes";
const POINT_SOURCE = "flood-points";
const POINT_LAYER = "flood-points";
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
export type MapHit = { kind: "route"; route: RouteProps } | { kind: "point"; point: FloodPointProps };

export interface RiskView {
  url: string; // đường dẫn lớp tuyến trên máy chủ, đổi khi mô hình được dựng lại
  rain: DayState;
  tide: DayState;
}

function riskFilter(level: number, major: boolean, rain: DayState, tide: DayState): FilterSpecification {
  const isMajor = ["in", ["get", "cls"], ["literal", MAJOR_CLASSES]];
  return ["all", ["==", levelExpression(rain, tide), level], major ? isMajor : ["!", isMajor]] as unknown as FilterSpecification;
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
        filter: riskFilter(layer.level, layer.major, "quiet", "quiet"),
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

export default function MapView({ initial, pin, flyTo, risk, showRisk, points, showPoints, routes, selectedRouteId, routeRevision, directionOrigin, directionDestination, directionsOpen, onRouteSelect, onTap, onMoveEnd, onLocate, onNotice }: Props) {
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
      const layers = [POINT_LAYER, ...RISK_LAYERS.map((layer) => layer.id)].filter((id) => map.getLayer(id));
      const hits = layers.length > 0 ? map.queryRenderedFeatures([[x - TAP_RADIUS_PX, y - TAP_RADIUS_PX], [x + TAP_RADIUS_PX, y + TAP_RADIUS_PX]], { layers }) : [];
      const point = hits.find((feature) => feature.layer.id === POINT_LAYER);
      const route = hits.find((feature) => feature.layer.id !== POINT_LAYER);
      const hit: MapHit | null = point
        ? { kind: "point", point: point.properties as FloodPointProps }
        : route
          ? { kind: "route", route: route.properties as RouteProps }
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
  const tide = risk?.tide ?? "quiet";
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    for (const layer of RISK_LAYERS) {
      map.setFilter(layer.id, riskFilter(layer.level, layer.major, rain, tide));
      map.setLayoutProperty(layer.id, "visibility", showRisk ? "visible" : "none");
    }
  }, [ready, rain, tide, showRisk]);

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
      <div className="flex h-full items-center justify-center p-6 text-center text-slate-700">
        Thiếu khóa bản đồ. Đặt VITE_GOONG_MAP_KEY trong file .env ở thư mục gốc rồi chạy lại.
      </div>
    );
  }
  return <div ref={containerRef} className="h-full w-full" data-testid="map" />;
}
