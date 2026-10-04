import { useCallback, useEffect, useRef, useState } from "react";

import { api, isAbort, type City, type CityKey, type Health, type PlaceDetail } from "./api";
import LayersPanel from "./components/LayersPanel";
import PlaceCard, { type Pin } from "./components/PlaceCard";
import SearchBar from "./components/SearchBar";
import StatusChip from "./components/StatusChip";
import { loadView, saveView } from "./lib/viewstore";
import MapView, { type FlyTarget, type MapViewState } from "./MapView";

// Khung nhìn khi mở lần đầu: trung tâm TP.HCM (trùng config.py). Đổi thành phố thì lấy tâm từ /api/cities.
const FALLBACK_VIEW: MapViewState = { center: [106.7, 10.78], zoom: 12 };
const CITY_ZOOM = 12;
const NOTICE_MS = 6000;
const CITY_LABELS: Record<CityKey, string> = { hcm: "TP.HCM", danang: "Đà Nẵng" };

export default function App() {
  const [saved] = useState(loadView);
  const [initial] = useState<MapViewState>(saved ?? FALLBACK_VIEW);
  const [cityKey, setCityKey] = useState<CityKey>(saved?.city ?? "hcm");
  const [cities, setCities] = useState<City[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [pin, setPin] = useState<Pin | null>(null);
  const [flyTo, setFlyTo] = useState<FlyTarget | null>(null);
  const [center, setCenter] = useState({ lat: initial.center[1], lon: initial.center[0] });
  const [notice, setNotice] = useState<string | null>(null);
  const [layersOpen, setLayersOpen] = useState(false);
  const [, setUserLocation] = useState<{ lat: number; lon: number; accuracy: number } | null>(null);

  const cityRef = useRef(cityKey);
  cityRef.current = cityKey;
  const reverseRef = useRef<AbortController | null>(null);
  const flyCount = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    api.health(controller.signal).then(setHealth).catch(() => undefined);
    api
      .cities(controller.signal)
      .then(setCities)
      .catch((error) => {
        if (!isAbort(error)) setNotice("Không kết nối được tới máy chủ. Bản đồ vẫn dùng được nhưng chưa tìm được địa điểm.");
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(null), NOTICE_MS);
    return () => window.clearTimeout(timer);
  }, [notice]);

  const fly = useCallback((lon: number, lat: number, zoom?: number) => {
    flyCount.current += 1;
    setFlyTo({ lon, lat, zoom, nonce: flyCount.current });
  }, []);

  const handleMoveEnd = useCallback((view: MapViewState) => {
    setCenter({ lat: view.center[1], lon: view.center[0] });
    saveView({ city: cityRef.current, center: view.center, zoom: view.zoom });
  }, []);

  const handleTap = useCallback((lat: number, lon: number) => {
    reverseRef.current?.abort();
    const controller = new AbortController();
    reverseRef.current = controller;
    setLayersOpen(false);
    setPin({ lat, lon, name: "", address: "", loading: true });
    api
      .reverse(lat, lon, controller.signal)
      .then((found) => setPin({ lat, lon, name: found.name, address: found.address, loading: false }))
      // Không có địa chỉ (Goong lỗi hoặc không có kết quả): thẻ vẫn hiện tọa độ và vẫn dùng được.
      .catch((error) => {
        if (!isAbort(error)) setPin({ lat, lon, name: "", address: "", loading: false });
      });
  }, []);

  const handlePick = useCallback(
    (place: PlaceDetail) => {
      reverseRef.current?.abort();
      setLayersOpen(false);
      setPin({ lat: place.lat, lon: place.lon, name: place.name, address: place.address, loading: false });
      fly(place.lon, place.lat, 16);
    },
    [fly],
  );

  const closePin = useCallback(() => {
    reverseRef.current?.abort();
    setPin(null);
  }, []);

  const changeCity = useCallback(
    (key: CityKey) => {
      const city = cities.find((c) => c.key === key);
      if (!city) return;
      setCityKey(key);
      setLayersOpen(false);
      closePin();
      fly(city.center[0], city.center[1], CITY_ZOOM);
    },
    [cities, closePin, fly],
  );

  return (
    <div className="relative h-dvh w-full overflow-hidden" style={{ ["--sheet-h" as string]: pin ? "13rem" : "0px" }}>
      <MapView
        initial={initial}
        pin={pin}
        flyTo={flyTo}
        onTap={handleTap}
        onMoveEnd={handleMoveEnd}
        onLocate={(lat, lon, accuracy) => setUserLocation({ lat, lon, accuracy })}
        onNotice={setNotice}
      />

      <div className="pointer-events-none absolute inset-x-0 top-0 z-10 flex flex-col gap-1.5 p-3">
        <div className="pointer-events-auto flex items-start gap-2">
          <SearchBar near={center} onPick={handlePick} />
          <button
            type="button"
            aria-expanded={layersOpen}
            onClick={() => setLayersOpen((value) => !value)}
            className="flex h-12 shrink-0 items-center rounded-xl bg-white px-4 text-base font-medium text-slate-900 shadow-md ring-1 ring-slate-200 hover:bg-slate-50"
          >
            Lớp
          </button>
        </div>
        <div className="pointer-events-auto flex items-center justify-between gap-2">
          <span className="rounded-full bg-white/90 px-3 py-1 text-xs font-medium text-slate-800 shadow-sm ring-1 ring-slate-200">
            {CITY_LABELS[cityKey]} · Trực tiếp
          </span>
          <StatusChip health={health} />
        </div>
      </div>

      {layersOpen && <LayersPanel cities={cities} current={cityKey} onCity={changeCity} onClose={() => setLayersOpen(false)} />}
      {pin && <PlaceCard pin={pin} onClose={closePin} />}

      {notice && (
        <div role="status" className="pointer-events-none absolute inset-x-0 top-28 z-30 flex justify-center px-4">
          <p className="pointer-events-auto max-w-sm rounded-xl bg-slate-900 px-4 py-3 text-center text-sm text-white shadow-lg">{notice}</p>
        </div>
      )}
    </div>
  );
}
