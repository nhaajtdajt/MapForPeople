import { useCallback, useEffect, useRef, useState } from "react";

import { api, isAbort, type PlaceDetail, type RouteOption } from "../api";
import { buildRouteParams, chooseRoute, type RoutePoint, type Vehicle } from "./directions";

export type DirectionEnd = "origin" | "destination";

export interface DirectionEndpoint extends RoutePoint {
  label: string;
  address: string;
}

interface PlacePoint {
  lat: number;
  lon: number;
  name?: string;
  address?: string;
}

export interface DirectionsController {
  isOpen: boolean;
  origin: DirectionEndpoint | null;
  destination: DirectionEndpoint | null;
  activeEndpoint: DirectionEnd | null;
  vehicle: Vehicle;
  routes: RouteOption[];
  selectedRouteId: number | null;
  routeRevision: number;
  notes: string[];
  error: string | null;
  loading: boolean;
  startTo: (pin: PlacePoint, userLocation: RoutePoint | null) => void;
  startFrom: (pin: PlacePoint) => void;
  openBlank: () => void;
  close: () => void;
  swap: () => void;
  setVehicle: (vehicle: Vehicle) => void;
  setActiveEndpoint: (endpoint: DirectionEnd | null) => void;
  choosePlace: (place: PlaceDetail) => void;
  choosePoint: (end: DirectionEnd, point: DirectionEndpoint) => void;
  handleMapTap: (lat: number, lon: number) => boolean;
  selectRoute: (routeId: number) => void;
}

function endpointFromPlace(place: PlaceDetail): DirectionEndpoint {
  return { lat: place.lat, lon: place.lon, label: place.name, address: place.address };
}

function endpointFromPoint(point: PlacePoint, fallback: string): DirectionEndpoint {
  return {
    lat: point.lat,
    lon: point.lon,
    label: point.name?.trim() || fallback,
    address: point.address ?? "",
  };
}

/** `event`: id của một trận đã qua để tìm đường theo bản đồ ngập của trận đó; null là lúc này. */
export function useDirections(event: string | null = null): DirectionsController {
  const [isOpen, setIsOpen] = useState(false);
  const [origin, setOrigin] = useState<DirectionEndpoint | null>(null);
  const [destination, setDestination] = useState<DirectionEndpoint | null>(null);
  const [activeEndpoint, setActiveEndpointState] = useState<DirectionEnd | null>(null);
  const [vehicle, setVehicleState] = useState<Vehicle>("bike");
  const [routes, setRoutes] = useState<RouteOption[]>([]);
  const [selectedRouteId, setSelectedRouteId] = useState<number | null>(null);
  const [routeRevision, setRouteRevision] = useState(0);
  const [notes, setNotes] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const requestRef = useRef<AbortController | null>(null);

  const cancelRequest = useCallback(() => {
    requestRef.current?.abort();
    requestRef.current = null;
  }, []);

  const clearResult = useCallback(() => {
    setRoutes([]);
    setSelectedRouteId(null);
    setNotes([]);
    setError(null);
    setLoading(false);
  }, []);

  const startTo = useCallback(
    (pin: PlacePoint, userLocation: RoutePoint | null) => {
      cancelRequest();
      clearResult();
      setIsOpen(true);
      setOrigin(userLocation ? { ...userLocation, label: "Vị trí của tôi", address: "" } : null);
      setDestination(endpointFromPoint(pin, "Điểm đã chọn"));
      setActiveEndpointState(userLocation ? null : "origin");
    },
    [cancelRequest, clearResult],
  );

  const startFrom = useCallback(
    (pin: PlacePoint) => {
      cancelRequest();
      clearResult();
      setIsOpen(true);
      setOrigin(endpointFromPoint(pin, "Điểm đã chọn"));
      setDestination(null);
      setActiveEndpointState("destination");
    },
    [cancelRequest, clearResult],
  );

  const openBlank = useCallback(() => {
    cancelRequest();
    clearResult();
    setIsOpen(true);
    setOrigin(null);
    setDestination(null);
    setActiveEndpointState("origin");
  }, [cancelRequest, clearResult]);

  const close = useCallback(() => {
    cancelRequest();
    clearResult();
    setIsOpen(false);
    setOrigin(null);
    setDestination(null);
    setActiveEndpointState(null);
  }, [cancelRequest, clearResult]);

  const setVehicle = useCallback(
    (nextVehicle: Vehicle) => {
      if (nextVehicle === vehicle) return;
      cancelRequest();
      clearResult();
      setVehicleState(nextVehicle);
    },
    [cancelRequest, clearResult, vehicle],
  );

  const swap = useCallback(() => {
    cancelRequest();
    clearResult();
    setOrigin(destination);
    setDestination(origin);
    setActiveEndpointState((current) => (current === "origin" ? "destination" : current === "destination" ? "origin" : null));
  }, [cancelRequest, clearResult, destination, origin]);

  // Chọn ô đang sửa không xóa lộ trình đang có: chỉ khi điểm thật sự đổi thì mới tìm lại.
  const activateEndpoint = useCallback((end: DirectionEnd | null) => setActiveEndpointState(end), []);

  const setEndpoint = useCallback(
    (end: DirectionEnd, point: DirectionEndpoint) => {
      cancelRequest();
      clearResult();
      if (end === "origin") {
        setOrigin(point);
        setActiveEndpointState(destination ? null : "destination");
      } else {
        setDestination(point);
        setActiveEndpointState(origin ? null : "origin");
      }
    },
    [cancelRequest, clearResult, destination, origin],
  );

  const choosePlace = useCallback(
    (place: PlaceDetail) => {
      if (activeEndpoint) setEndpoint(activeEndpoint, endpointFromPlace(place));
    },
    [activeEndpoint, setEndpoint],
  );

  const handleMapTap = useCallback(
    (lat: number, lon: number) => {
      if (!isOpen || !activeEndpoint) return false;
      const point = {
        lat,
        lon,
        label: `${lat.toFixed(5)}, ${lon.toFixed(5)}`,
        address: "",
      };
      const end = activeEndpoint;
      setEndpoint(end, { ...point, label: "Điểm trên bản đồ" });
      // Đổi tọa độ ra tên đường cho dễ đọc; lỗi thì giữ nhãn "Điểm trên bản đồ".
      api
        .reverse(lat, lon)
        .then((found) => {
          const label = found.name || found.address;
          if (!label) return;
          const rename = (current: DirectionEndpoint | null) =>
            current && current.lat === lat && current.lon === lon ? { ...current, label, address: found.address } : current;
          if (end === "origin") setOrigin(rename);
          else setDestination(rename);
        })
        .catch(() => undefined);
      return true;
    },
    [activeEndpoint, isOpen, setEndpoint],
  );

  const selectRoute = useCallback((routeId: number) => setSelectedRouteId(routeId), []);

  useEffect(() => {
    if (!isOpen || !origin || !destination) return;
    const controller = new AbortController();
    requestRef.current = controller;
    setLoading(true);
    setError(null);

    api
      .route(buildRouteParams(origin, destination, vehicle, event), controller.signal)
      .then((result) => {
        if (controller.signal.aborted) return;
        setRoutes(result.routes);
        setRouteRevision((revision) => revision + 1);
        setNotes(result.notes);
        setSelectedRouteId(chooseRoute(result.routes)?.id ?? null);
        if (result.routes.length === 0) setError("Không tìm được lộ trình giữa hai điểm này");
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted || isAbort(reason)) return;
        setRoutes([]);
        setSelectedRouteId(null);
        setNotes([]);
        setError(reason instanceof Error ? reason.message : "Không tìm được lộ trình lúc này");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => {
      controller.abort();
      if (requestRef.current === controller) requestRef.current = null;
    };
  }, [destination, isOpen, origin, vehicle, event]);

  return {
    isOpen,
    origin,
    destination,
    activeEndpoint,
    vehicle,
    routes,
    selectedRouteId,
    routeRevision,
    notes,
    error,
    loading,
    startTo,
    startFrom,
    openBlank,
    close,
    swap,
    setVehicle,
    setActiveEndpoint: activateEndpoint,
    choosePlace,
    choosePoint: setEndpoint,
    handleMapTap,
    selectRoute,
  };
}
