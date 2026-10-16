import { useCallback, useEffect, useRef, useState } from "react";

import { api, ApiError, isAbort, type Camera, type City, type CityKey, type FloodPoints, type FloodReport, type Health, type PlaceDetail, type ReportBody, type RiskState } from "./api";
import CameraCard from "./components/CameraCard";
import LayersPanel from "./components/LayersPanel";
import PlaceCard, { type Pin } from "./components/PlaceCard";
import DirectionsPanel from "./components/DirectionsPanel";
import DirectionsTop from "./components/DirectionsTop";
import ReportSheet from "./components/ReportSheet";
import Icon from "./components/Icon";
import Legend from "./components/Legend";
import SearchBar from "./components/SearchBar";
import StatusBar from "./components/StatusBar";
import StatusChip from "./components/StatusChip";
import { floodNote, tideExtentOf } from "./lib/floodnote";
import { loadView, saveView } from "./lib/viewstore";
import { useDirections } from "./lib/useDirections";
import MapView, { type FlyTarget, type MapHit, type MapViewState } from "./MapView";

// Khung nhìn khi mở lần đầu: trung tâm TP.HCM (trùng config.py). Đổi thành phố thì lấy tâm từ /api/cities.
const FALLBACK_VIEW: MapViewState = { center: [106.7, 10.78], zoom: 12 };
const CITY_ZOOM = 12;
const NOTICE_MS = 6000;
const RISK_REFRESH_MS = 5 * 60_000;
const USER_KEY = "floodrisk-user";

/** Mã ẩn danh của máy này, để một người chỉ được tính một lần cho mỗi tuyến trong 30 phút. */
function userId(): string {
  try {
    const saved = window.localStorage.getItem(USER_KEY);
    if (saved) return saved;
    const made = `web-${Math.random().toString(36).slice(2, 12)}`;
    window.localStorage.setItem(USER_KEY, made);
    return made;
  } catch {
    return "web-khong-luu";
  }
}
const CITY_LABELS: Record<CityKey, string> = { hcm: "TP.HCM", danang: "Đà Nẵng" };

export default function App() {
  const [saved] = useState(loadView);
  const [initial] = useState<MapViewState>(saved ?? FALLBACK_VIEW);
  const [cityKey, setCityKey] = useState<CityKey>(saved?.city ?? "hcm");
  const [cities, setCities] = useState<City[]>([]);
  const [health, setHealth] = useState<Health | null>(null);
  const [pin, setPin] = useState<Pin | null>(null);
  const [hit, setHit] = useState<MapHit | null>(null);
  const [risk, setRisk] = useState<RiskState | null>(null);
  const [points, setPoints] = useState<FloodPoints | null>(null);
  const [showRisk, setShowRisk] = useState(true);
  const [showPoints, setShowPoints] = useState(true);
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [showCameras, setShowCameras] = useState(true);
  const [reports, setReports] = useState<FloodReport[]>([]);
  const [camera, setCamera] = useState<Camera | null>(null);
  const [reporting, setReporting] = useState(false);
  const [sending, setSending] = useState(false);
  const [riskTick, setRiskTick] = useState(0); // tăng lên để lấy lại mức và báo cáo ngay
  const [flyTo, setFlyTo] = useState<FlyTarget | null>(null);
  const [center, setCenter] = useState({ lat: initial.center[1], lon: initial.center[0] });
  const [notice, setNotice] = useState<string | null>(null);
  const [layersOpen, setLayersOpen] = useState(false);
  const [userLocation, setUserLocation] = useState<{ lat: number; lon: number; accuracy: number } | null>(null);
  const directions = useDirections();

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
    // Mức nguy cơ của thành phố đang xem: lấy ngay, rồi lấy lại mỗi 5 phút. Thành phố chưa có mô hình thì để trống.
    const controller = new AbortController();
    const load = () => {
      api
        .risk(cityKey, controller.signal)
        .then(setRisk)
        .catch((error) => {
          if (!isAbort(error)) setRisk(null);
        });
      api.reports(cityKey, controller.signal).then(setReports).catch(() => undefined);
    };
    load();
    const timer = window.setInterval(load, RISK_REFRESH_MS);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, [cityKey, riskTick]);

  useEffect(() => {
    const controller = new AbortController();
    setRisk(null);
    setPoints(null);
    setCameras([]);
    setReports([]);
    setCamera(null);
    api.floodPoints(cityKey, controller.signal).then(setPoints).catch(() => undefined);
    api.cameras(cityKey, controller.signal).then(setCameras).catch(() => undefined);
    return () => controller.abort();
  }, [cityKey]);

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

  const handleTap = useCallback((lat: number, lon: number, tapped: MapHit | null) => {
    if (directions.handleMapTap(lat, lon)) return;
    reverseRef.current?.abort();
    setLayersOpen(false);
    if (tapped?.kind === "camera") {
      setPin(null);
      setHit(null);
      setCamera(tapped.camera);
      return;
    }
    setCamera(null);
    const controller = new AbortController();
    reverseRef.current = controller;
    setHit(tapped);
    setPin({ lat, lon, name: "", address: "", loading: true });
    api
      .reverse(lat, lon, controller.signal)
      .then((found) => setPin({ lat, lon, name: found.name, address: found.address, loading: false }))
      // Không có địa chỉ (Goong lỗi hoặc không có kết quả): thẻ vẫn hiện tọa độ và vẫn dùng được.
      .catch((error) => {
        if (!isAbort(error)) setPin({ lat, lon, name: "", address: "", loading: false });
      });
  }, [directions.handleMapTap]);

  const handlePick = useCallback(
    (place: PlaceDetail) => {
      reverseRef.current?.abort();
      setLayersOpen(false);
      setHit(null);
      setPin({ lat: place.lat, lon: place.lon, name: place.name, address: place.address, loading: false });
      fly(place.lon, place.lat, 16);
    },
    [fly],
  );

  const closePin = useCallback(() => {
    reverseRef.current?.abort();
    setPin(null);
    setHit(null);
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

  const sendReport = useCallback(
    (choice: Pick<ReportBody, "status" | "depth">) => {
      if (!pin) return;
      setSending(true);
      api
        .sendReport({ city: cityRef.current, lat: pin.lat, lon: pin.lon, user: userId(), ...choice })
        .then((result) => {
          setNotice(`Đã ghi nhận báo cáo của bạn cho ${result.route.name}. Cảm ơn bạn.`);
          setReporting(false);
          setRiskTick((value) => value + 1);
        })
        .catch((error) => setNotice(error instanceof ApiError ? error.message : "Chưa gửi được báo cáo."))
        .finally(() => setSending(false));
    },
    [pin],
  );

  const now = risk?.hours[0] ?? null;
  const note = pin ? floodNote(hit, now, risk) : null;
  const riskView = risk?.layer ? { url: risk.layer.url, rain: risk.states.rain, tide: tideExtentOf(risk), overrides: risk.overrides } : null;
  const sheet = camera ? "24rem" : pin ? (note ? "20rem" : "13rem") : "0px";

  return (
    <div className="relative h-dvh w-full overflow-hidden" style={{ ["--sheet-h" as string]: directions.isOpen ? (directions.routes.length || directions.loading ? "48dvh" : "0px") : sheet }}>
      <MapView
        initial={initial}
        pin={directions.isOpen ? null : pin}
        flyTo={flyTo}
        risk={riskView}
        showRisk={showRisk}
        points={points}
        showPoints={showPoints}
        cameras={cameras}
        showCameras={showCameras}
        reports={reports}
        routes={directions.routes}
        selectedRouteId={directions.selectedRouteId}
        routeRevision={directions.routeRevision}
        directionOrigin={directions.origin}
        directionDestination={directions.destination}
        directionsOpen={directions.isOpen}
        onRouteSelect={directions.selectRoute}
        onTap={handleTap}
        onMoveEnd={handleMoveEnd}
        onLocate={(lat, lon, accuracy) => setUserLocation({ lat, lon, accuracy })}
        onNotice={setNotice}
      />

      <div hidden={directions.isOpen} className="pointer-events-none absolute inset-x-0 top-0 z-10 flex flex-col gap-2 p-3 pt-[max(0.75rem,env(safe-area-inset-top))] sm:max-w-xl">
        <div className="pointer-events-auto flex items-start gap-2">
          <SearchBar near={center} onPick={handlePick} />
          <button
            type="button"
            aria-expanded={layersOpen}
            aria-label="Lớp bản đồ và thành phố"
            onClick={() => setLayersOpen((value) => !value)}
            className={`flex h-12 shrink-0 items-center gap-1.5 rounded-2xl px-3.5 text-[15px] font-semibold shadow-float transition-colors ${layersOpen ? "bg-brand text-white" : "bg-white text-ink hover:bg-mist"}`}
          >
            <Icon name="layers" />
            <span className="hidden min-[380px]:inline">Lớp</span>
          </button>
        </div>
        <div className="pointer-events-auto flex items-start justify-between gap-2">
          <StatusBar city={CITY_LABELS[cityKey]} risk={risk} />
          <StatusChip health={health} />
        </div>
      </div>

      {showRisk && riskView && !directions.isOpen && !pin && !camera && (
        <div className="pointer-events-none absolute inset-x-0 bottom-0 z-[5] flex justify-start pb-[max(2.25rem,calc(env(safe-area-inset-bottom)+2rem))] pl-3 pr-16">
          <div className="pointer-events-auto">
            <Legend />
          </div>
        </div>
      )}

      {layersOpen && (
        <LayersPanel
          cities={cities}
          current={cityKey}
          showRisk={showRisk}
          showPoints={showPoints}
          showCameras={showCameras}
          onCity={changeCity}
          onShowRisk={setShowRisk}
          onShowPoints={setShowPoints}
          onShowCameras={setShowCameras}
          onClose={() => setLayersOpen(false)}
        />
      )}
      {pin && !directions.isOpen && (
        <PlaceCard
          pin={pin}
          flood={note}
          onClose={closePin}
          onDirectionsTo={() => directions.startTo(pin, userLocation)}
          onDirectionsFrom={() => directions.startFrom(pin)}
          onReport={() => setReporting(true)}
        />
      )}
      {camera && !directions.isOpen && <CameraCard camera={camera} onClose={() => setCamera(null)} onRead={() => setRiskTick((value) => value + 1)} />}
      {reporting && pin && (
        <ReportSheet place={pin.name || "Điểm đã chọn"} busy={sending} onChoose={sendReport} onClose={() => setReporting(false)} />
      )}
      <DirectionsTop directions={directions} near={center} onLocated={(lat, lon, accuracy) => setUserLocation({ lat, lon, accuracy })} />
      <DirectionsPanel directions={directions} />

      {notice && (
        <div role="status" className="pointer-events-none absolute inset-x-0 top-32 z-30 flex justify-center px-4">
          <p className="pop-in pointer-events-auto flex max-w-sm items-start gap-2.5 rounded-2xl bg-ink px-4 py-3 text-sm leading-snug text-white shadow-float">
            <Icon name="info" className="mt-0.5 h-4 w-4 shrink-0 text-sky-300" />
            {notice}
          </p>
        </div>
      )}
    </div>
  );
}
