import { useEffect, useRef, useState } from "react";

import { api, type Suggestion } from "../api";
import { chooseRoute, formatDuration, type Vehicle } from "../lib/directions";
import { locateMe } from "../lib/locate";
import { loadRecent, rememberPlace, type RecentPlace } from "../lib/recent";
import type { DirectionEnd, DirectionEndpoint, DirectionsController } from "../lib/useDirections";
import { MIN_CHARS, usePlaceSearch } from "../lib/usePlaceSearch";
import Icon, { type IconName } from "./Icon";

interface Props {
  directions: DirectionsController;
  near: { lat: number; lon: number };
  onLocated: (lat: number, lon: number, accuracy: number) => void;
  replay?: string | null; // tên trận đang tái hiện, nếu có
}

const PLACEHOLDER: Record<DirectionEnd, string> = { origin: "Chọn điểm đi", destination: "Chọn điểm đến" };
const VEHICLES: { value: Vehicle; label: string; icon: IconName }[] = [
  { value: "bike", label: "Xe máy", icon: "bike" },
  { value: "car", label: "Ô tô", icon: "car" },
];

function Row({ icon, title, sub, onClick, tone = "text-ink-soft" }: { icon: IconName; title: string; sub?: string; onClick: () => void; tone?: string }) {
  return (
    <li>
      <button type="button" onClick={onClick} className="flex min-h-12 w-full items-center gap-3 px-4 py-2 text-left hover:bg-mist active:bg-line">
        <span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-mist ${tone}`}>
          <Icon name={icon} className="h-[18px] w-[18px]" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[15px] font-medium text-ink">{title}</span>
          {sub && <span className="block truncate text-sm text-ink-faint">{sub}</span>}
        </span>
      </button>
    </li>
  );
}

/** Đầu màn hình khi chỉ đường, giống Google Maps: hai ô điểm đi, điểm đến có đường nối, nút đổi chiều, chọn loại xe. */
export default function DirectionsTop({ directions, near, onLocated, replay = null }: Props) {
  const { origin, destination, activeEndpoint } = directions;
  const [editing, setEditing] = useState<DirectionEnd | null>(null);
  const [picking, setPicking] = useState(false);
  const [text, setText] = useState("");
  const [recent, setRecent] = useState<RecentPlace[]>(loadRecent);
  const [problem, setProblem] = useState<string | null>(null);
  const [locating, setLocating] = useState(false);
  const search = usePlaceSearch(editing ? text : "", near);
  const inputRef = useRef<HTMLInputElement>(null);

  // Mở chỉ đường mà còn thiếu một điểm (hoặc vừa chọn xong một điểm trên bản đồ): mở ngay ô của điểm còn thiếu.
  useEffect(() => {
    if (!directions.isOpen) {
      setEditing(null);
      setPicking(false);
      return;
    }
    if (activeEndpoint && !picking) {
      setEditing(activeEndpoint);
      setText("");
    }
    if (!activeEndpoint) setPicking(false);
  }, [directions.isOpen, activeEndpoint, picking]);

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const open = (end: DirectionEnd) => {
    setProblem(null);
    setPicking(false);
    setText("");
    setEditing(end);
    directions.setActiveEndpoint(end);
  };
  const stopEditing = () => {
    setEditing(null);
    setPicking(false);
    directions.setActiveEndpoint(null);
  };
  const choose = (end: DirectionEnd, point: DirectionEndpoint, remember = true) => {
    if (remember) setRecent(rememberPlace({ lat: point.lat, lon: point.lon, label: point.label, address: point.address }));
    setEditing(null);
    setPicking(false);
    directions.choosePoint(end, point);
  };
  const pickSuggestion = async (end: DirectionEnd, item: Suggestion) => {
    try {
      const place = await api.placeDetail(item.place_id);
      choose(end, { lat: place.lat, lon: place.lon, label: place.name || item.main, address: place.address });
    } catch (error) {
      setProblem(error instanceof Error ? error.message : "Không lấy được địa điểm này");
    }
  };
  const useMyLocation = (end: DirectionEnd) => {
    setLocating(true);
    setProblem(null);
    locateMe()
      .then(({ lat, lon, accuracy }) => {
        onLocated(lat, lon, accuracy);
        choose(end, { lat, lon, label: "Vị trí của tôi", address: "" }, false);
      })
      .catch((error: Error) => setProblem(error.message))
      .finally(() => setLocating(false));
  };
  const pickOnMap = (end: DirectionEnd) => {
    setEditing(null);
    setPicking(true);
    directions.setActiveEndpoint(end);
  };

  if (!directions.isOpen) return null;

  const best = chooseRoute(directions.routes);
  const query = text.trim();

  const field = (end: DirectionEnd) => {
    const value = end === "origin" ? origin : destination;
    const isEditing = editing === end;
    return (
      <div className={`flex h-11 items-center rounded-xl px-3 transition-colors ${isEditing ? "bg-white ring-2 ring-brand" : "bg-mist"}`}>
        {isEditing ? (
          <input
            ref={inputRef}
            type="search"
            aria-label={PLACEHOLDER[end]}
            placeholder={value ? value.label : PLACEHOLDER[end]}
            value={text}
            autoComplete="off"
            onChange={(event) => setText(event.target.value)}
            onKeyDown={(event) => event.key === "Escape" && stopEditing()}
            className="h-full min-w-0 flex-1 bg-transparent text-[15px] text-ink outline-none placeholder:text-ink-faint focus-visible:outline-none"
          />
        ) : (
          <button type="button" onClick={() => open(end)} className="h-full min-w-0 flex-1 truncate text-left text-[15px]">
            {value ? (
              <span className={value.label === "Vị trí của tôi" ? "font-medium text-brand" : "text-ink"}>{value.label}</span>
            ) : (
              <span className="text-ink-faint">{PLACEHOLDER[end]}</span>
            )}
          </button>
        )}
      </div>
    );
  };

  return (
    <div className="pointer-events-none absolute inset-x-0 top-0 z-20 flex flex-col gap-2 p-3 pt-[max(0.75rem,env(safe-area-inset-top))] sm:w-[26rem]">
      <section aria-label="Điểm đi và điểm đến" className="sheet-in pointer-events-auto rounded-3xl bg-white p-2 pr-1 shadow-float">
        <div className="flex items-stretch gap-1">
          <button
            type="button"
            aria-label="Thoát chỉ đường"
            onClick={directions.close}
            className="flex h-11 w-10 shrink-0 items-center justify-center rounded-full text-ink-soft hover:bg-mist"
          >
            <Icon name="back" />
          </button>
          <div aria-hidden="true" className="flex w-4 shrink-0 flex-col items-center py-4">
            <span className="h-3 w-3 rounded-full border-[3px] border-brand bg-white" />
            <span className="my-1 w-0 flex-1 border-l-2 border-dotted border-ink-faint/60" />
            <Icon name="pin" className="h-4 w-4 text-danger" />
          </div>
          <div className="flex min-w-0 flex-1 flex-col gap-1.5 py-0.5">
            {field("origin")}
            {field("destination")}
          </div>
          <button
            type="button"
            aria-label="Đổi chiều điểm đi và điểm đến"
            onClick={directions.swap}
            className="flex w-11 shrink-0 items-center justify-center self-center rounded-full text-ink-soft hover:bg-mist"
          >
            <Icon name="swap" />
          </button>
        </div>
        <div role="radiogroup" aria-label="Loại xe" className="mt-1.5 flex gap-1.5 pl-[3.25rem]">
          {VEHICLES.map((option) => {
            const active = directions.vehicle === option.value;
            return (
              <button
                key={option.value}
                type="button"
                role="radio"
                aria-checked={active}
                onClick={() => directions.setVehicle(option.value)}
                className={`flex h-9 items-center gap-1.5 rounded-full px-3 text-sm font-semibold transition-colors ${active ? "bg-brand-tint text-brand-strong" : "text-ink-soft hover:bg-mist"}`}
              >
                <Icon name={option.icon} className="h-[18px] w-[18px]" />
                {active && best ? formatDuration(best.duration_s) : option.label}
              </button>
            );
          })}
        </div>
      </section>

      {replay && (
        <div className="pop-in pointer-events-auto flex items-center gap-2 self-start rounded-full bg-ink px-3 py-1.5 text-[13px] font-medium text-white shadow-float">
          <Icon name="clock" className="h-4 w-4 shrink-0 text-amber-300" />
          Tái hiện bản đồ ngập: {replay}
        </div>
      )}

      {picking && activeEndpoint && (
        <div className="pop-in pointer-events-auto flex items-center gap-2 rounded-2xl bg-ink px-4 py-2.5 text-sm text-white shadow-float">
          <Icon name="map" className="h-4 w-4 shrink-0 text-sky-300" />
          <span className="flex-1">Chạm vào bản đồ để chọn {activeEndpoint === "origin" ? "điểm đi" : "điểm đến"}</span>
          <button type="button" onClick={stopEditing} className="rounded-lg px-2 py-1 font-semibold text-sky-200 hover:bg-white/10">
            Hủy
          </button>
        </div>
      )}

      {editing && (
        <section aria-label="Gợi ý địa điểm" className="pop-in pointer-events-auto max-h-[60dvh] overflow-y-auto rounded-3xl bg-white py-2 shadow-float">
          <ul>
            <Row icon="locate" tone="text-brand" title={locating ? "Đang lấy vị trí…" : "Vị trí của tôi"} sub="Dùng định vị của điện thoại" onClick={() => useMyLocation(editing)} />
            <Row icon="map" title="Chọn trên bản đồ" sub="Chạm vào một điểm trên bản đồ" onClick={() => pickOnMap(editing)} />
          </ul>
          {problem && (
            <p role="alert" className="mx-4 my-1 rounded-xl bg-caution-tint px-3 py-2 text-sm text-caution-ink">
              {problem}
            </p>
          )}
          {query.length < MIN_CHARS && recent.length > 0 && (
            <>
              <p className="px-4 pb-1 pt-3 text-xs font-semibold text-ink-faint">Gần đây</p>
              <ul>
                {recent.map((place) => (
                  <Row key={`${place.lat},${place.lon}`} icon="clock" title={place.label} sub={place.address} onClick={() => choose(editing, { ...place })} />
                ))}
              </ul>
            </>
          )}
          {query.length >= MIN_CHARS && (
            <ul className="mt-1 border-t border-line pt-1">
              {search.status === "loading" && search.items.length === 0 && <li className="px-4 py-3 text-sm text-ink-faint">Đang tìm…</li>}
              {search.status === "empty" && <li className="px-4 py-3 text-sm text-ink-faint">Không thấy địa điểm nào khớp</li>}
              {search.status === "error" && (
                <li role="alert" className="px-4 py-3 text-sm text-danger-ink">
                  {search.message}
                </li>
              )}
              {search.items.map((item) => (
                <Row key={item.place_id} icon="pin" title={item.main} sub={item.secondary} onClick={() => void pickSuggestion(editing, item)} />
              ))}
            </ul>
          )}
          <div className="flex justify-end px-3 pt-1">
            <button type="button" onClick={stopEditing} className="min-h-10 rounded-xl px-3 text-sm font-semibold text-brand hover:bg-brand-tint">
              Xong
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
