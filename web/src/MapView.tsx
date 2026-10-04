import {
  GeolocateControl,
  Map as MapLibreMap,
  Marker,
  NavigationControl,
  ScaleControl,
  setWorkerUrl,
  type IControl,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
// MapLibre 6 tìm worker cạnh file của chính nó, nhưng bản dựng Vite gộp mã vào /assets/index-*.js nên worker biến mất
// ("Worker failed to load"). Để Vite đóng gói worker thành tài nguyên riêng rồi khai báo đường dẫn cho MapLibre.
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { useEffect, useRef } from "react";

setWorkerUrl(workerUrl);

const MAP_KEY: string = import.meta.env.VITE_GOONG_MAP_KEY ?? "";
const STYLE_URL = `https://tiles.goong.io/assets/goong_map_web.json?api_key=${MAP_KEY}`;
const PIN_COLOR = "#1d4ed8";

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
  onTap: (lat: number, lon: number) => void;
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

export default function MapView({ initial, pin, flyTo, onTap, onMoveEnd, onLocate, onNotice }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const markerRef = useRef<Marker | null>(null);
  // Các hàm gọi lại mới nhất, để bản đồ chỉ cần tạo một lần.
  const callbacks = useRef({ onTap, onMoveEnd, onLocate, onNotice });
  callbacks.current = { onTap, onMoveEnd, onLocate, onNotice };

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

    map.on("click", (event) => callbacks.current.onTap(event.lngLat.lat, event.lngLat.lng));
    map.on("moveend", () => {
      const center = map.getCenter();
      callbacks.current.onMoveEnd({ center: [center.lng, center.lat], zoom: map.getZoom() });
    });

    return () => {
      markerRef.current?.remove();
      markerRef.current = null;
      map.remove();
      mapRef.current = null;
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

  if (!MAP_KEY) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-center text-slate-700">
        Thiếu khóa bản đồ. Đặt VITE_GOONG_MAP_KEY trong file .env ở thư mục gốc rồi chạy lại.
      </div>
    );
  }
  return <div ref={containerRef} className="h-full w-full" data-testid="map" />;
}
