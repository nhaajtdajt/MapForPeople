import {
  LngLatBounds,
  type FilterSpecification,
  type GeoJSONSource,
  type Map as MapLibreMap,
  type PointLike,
} from "maplibre-gl";
import type { Feature, FeatureCollection, LineString, Point } from "geojson";

import type { RouteOption } from "../api";
import type { DirectionEndpoint } from "./useDirections";

const ROUTE_SOURCE = "directions-routes";
const ENDPOINT_SOURCE = "directions-endpoints";
const ALTERNATIVE_LAYER = "directions-routes-alternatives";
const SELECTED_LAYER = "directions-routes-selected";
const ENDPOINT_CIRCLES = "directions-endpoint-circles";

const EMPTY_ROUTES: FeatureCollection<LineString, { route_id: number }> = { type: "FeatureCollection", features: [] };
const EMPTY_ENDPOINTS: FeatureCollection<Point, { end: string }> = { type: "FeatureCollection", features: [] };

export function emptySelectedRouteFilter(): FilterSpecification {
  return ["==", ["get", "route_id"], -1];
}

export function addRouteLayers(map: MapLibreMap): void {
  const firstSymbol = map.getStyle().layers.find((layer) => layer.type === "symbol")?.id;
  map.addSource(ROUTE_SOURCE, { type: "geojson", data: EMPTY_ROUTES });
  map.addLayer(
    {
      id: ALTERNATIVE_LAYER,
      type: "line",
      source: ROUTE_SOURCE,

      layout: { "line-cap": "round", "line-join": "round" },
      paint: {
        "line-color": "#94a3b8",
        "line-width": ["interpolate", ["linear"], ["zoom"], 10, 2, 14, 3, 17, 5],
        "line-opacity": 0.8,
      },
    },
    firstSymbol,
  );
  map.addLayer(
    {
      id: SELECTED_LAYER,
      type: "line",
      source: ROUTE_SOURCE,
      filter: emptySelectedRouteFilter(),
      layout: { "line-cap": "round", "line-join": "round" },
      paint: {
        "line-color": "#1d4ed8",
        "line-width": ["interpolate", ["linear"], ["zoom"], 10, 4, 14, 6, 17, 9],
        "line-opacity": 1,
      },
    },
    firstSymbol,
  );
  map.addSource(ENDPOINT_SOURCE, { type: "geojson", data: EMPTY_ENDPOINTS });
  map.addLayer(
    {
      id: ENDPOINT_CIRCLES,
      type: "circle",
      source: ENDPOINT_SOURCE,
      paint: {
        "circle-radius": 14,
        "circle-color": ["match", ["get", "end"], "origin", "#15803d", "#1d4ed8"],
        "circle-stroke-color": "#ffffff",
        "circle-stroke-width": 3,
      },
    },
    firstSymbol,
  );
  // Chữ "Đi" và "Đến" trong hai chấm đầu mút, để nhìn là biết lộ trình chạy theo chiều nào.
  // Phông chữ lấy của bản đồ nền (chỉ nó có sẵn bộ chữ trên máy chủ ô bản đồ); không tìm thấy thì chỉ còn hai màu.
  const font = map
    .getStyle()
    .layers.map((layer) => (layer.type === "symbol" ? layer.layout?.["text-font"] : undefined))
    .find((value): value is string[] => Array.isArray(value) && value.every((item) => typeof item === "string"));
  if (font) {
    map.addLayer({
      id: `${ENDPOINT_CIRCLES}-labels`,
      type: "symbol",
      source: ENDPOINT_SOURCE,
      layout: {
        "text-field": ["match", ["get", "end"], "origin", "Đi", "Đến"],
        "text-font": font,
        "text-size": 12,
        "text-allow-overlap": true,
        "text-ignore-placement": true,
      },
      paint: { "text-color": "#ffffff" },
    });
  }
}

function routeFeatures(routes: RouteOption[]): FeatureCollection<LineString, { route_id: number }> {
  const features: Feature<LineString, { route_id: number }>[] = routes.map((route) => ({
    type: "Feature",
    id: route.id,
    geometry: route.geometry,
    properties: { route_id: route.id },
  }));
  return { type: "FeatureCollection", features };
}

function endpointFeatures(
  origin: DirectionEndpoint | null,
  destination: DirectionEndpoint | null,
): FeatureCollection<Point, { end: string }> {
  const features: Feature<Point, { end: string }>[] = [];
  if (origin) {
    features.push({
      type: "Feature",
      geometry: { type: "Point", coordinates: [origin.lon, origin.lat] },
      properties: { end: "origin" },
    });
  }
  if (destination) {
    features.push({
      type: "Feature",
      geometry: { type: "Point", coordinates: [destination.lon, destination.lat] },
      properties: { end: "destination" },
    });
  }
  return { type: "FeatureCollection", features };
}

export function updateRouteLayers(
  map: MapLibreMap,
  routes: RouteOption[],
  selectedRouteId: number | null,
  origin: DirectionEndpoint | null,
  destination: DirectionEndpoint | null,
  fitToRoutes: boolean,
): void {
  const routeSource = map.getSource(ROUTE_SOURCE) as GeoJSONSource | undefined;
  const endpointSource = map.getSource(ENDPOINT_SOURCE) as GeoJSONSource | undefined;
  if (!routeSource || !endpointSource) return;

  routeSource.setData(routeFeatures(routes));
  endpointSource.setData(endpointFeatures(origin, destination));
  map.setFilter(
    ALTERNATIVE_LAYER,
    selectedRouteId === null ? null : (["!=", ["get", "route_id"], selectedRouteId] as FilterSpecification),
  );
  map.setFilter(
    SELECTED_LAYER,
    selectedRouteId === null ? emptySelectedRouteFilter() : (["==", ["get", "route_id"], selectedRouteId] as FilterSpecification),
  );
  if (fitToRoutes && routes.length > 0) fitBoundsToRoutes(map, routes, origin, destination);
}

function fitBoundsToRoutes(
  map: MapLibreMap,
  routes: RouteOption[],
  origin: DirectionEndpoint | null,
  destination: DirectionEndpoint | null,
): void {
  const coordinates = routes.flatMap((route) => route.geometry.coordinates);
  if (origin) coordinates.push([origin.lon, origin.lat]);
  if (destination) coordinates.push([destination.lon, destination.lat]);
  if (coordinates.length === 0) return;

  const bounds = new LngLatBounds(coordinates[0], coordinates[0]);
  for (const coordinate of coordinates.slice(1)) bounds.extend(coordinate);

  const width = map.getContainer().clientWidth;
  const height = map.getContainer().clientHeight;
  const padding = width <= 640
    ? { top: 120, right: 28, bottom: Math.min(height * 0.5, 520) + 24, left: 28 }
    : { top: 56, right: 36, bottom: 36, left: 420 };
  map.fitBounds(bounds, { padding, duration: 550, maxZoom: 16 });
}

export function selectRouteAtPoint(map: MapLibreMap, point: PointLike, onSelect: (routeId: number) => void): boolean {
  const layers = [SELECTED_LAYER, ALTERNATIVE_LAYER].filter((id) => map.getLayer(id));
  if (layers.length === 0) return false;
  const feature = map.queryRenderedFeatures(point, { layers })[0];
  if (!feature) return false;
  const routeId = Number(feature.properties?.route_id);
  if (!Number.isFinite(routeId)) return false;
  onSelect(routeId);
  return true;
}
