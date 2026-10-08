import SearchBar from "./SearchBar";
import { formatCoords } from "../lib/format";
import { floodSummary, formatArrival, formatDistance, formatDuration, prioritizeRoutes, type Vehicle } from "../lib/directions";
import type { DirectionsController, DirectionEnd } from "../lib/useDirections";

interface Props {
  directions: DirectionsController;
  near: { lat: number; lon: number };
}

function routeName(kind: string, index: number): string {
  if (kind === "fastest") return "Đường nhanh nhất";
  if (kind === "flood_avoid") return "Đường tránh ngập";
  return `Lộ trình ${index + 1}`;
}

const TURN_LABELS: Record<string, string> = {
  start: "Bắt đầu",
  straight: "Đi thẳng",
  left: "Rẽ trái",
  right: "Rẽ phải",
  uturn: "Quay đầu",
};

function EndpointRow({
  end,
  title,
  value,
  active,
  onChoose,
}: {
  end: DirectionEnd;
  title: string;
  value: DirectionsController["origin"];
  active: boolean;
  onChoose: (end: DirectionEnd) => void;
}) {
  return (
    <div className={`flex min-w-0 items-center gap-3 rounded-xl border px-3 py-2 ${active ? "border-blue-500 ring-1 ring-blue-500" : "border-slate-200"}`}>
      <span aria-hidden="true" className={`h-3 w-3 shrink-0 rounded-full ${end === "origin" ? "bg-green-700" : "bg-blue-700"}`} />
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium text-slate-600">{title}</p>
        <p className="truncate text-sm font-semibold text-slate-900">{value?.label ?? "Chưa chọn"}</p>
        {value?.address && <p className="truncate text-xs text-slate-600">{value.address}</p>}
        {value && <p className="text-xs text-slate-500">{formatCoords(value.lat, value.lon)}</p>}
      </div>
      <button
        type="button"
        aria-pressed={active}
        onClick={() => onChoose(end)}
        className="min-h-11 shrink-0 rounded-lg px-3 text-sm font-medium text-blue-800 hover:bg-blue-50 focus-visible:outline-2 focus-visible:outline-blue-700"
      >
        {value ? "Đổi" : "Chọn"}
      </button>
    </div>
  );
}

export default function DirectionsPanel({ directions, near }: Props) {
  const selected = directions.routes.find((route) => route.id === directions.selectedRouteId) ?? null;
  const routes = prioritizeRoutes(directions.routes);
  const vehicleOptions: { value: Vehicle; label: string }[] = [
    { value: "bike", label: "Xe máy" },
    { value: "car", label: "Ô tô" },
  ];

  return (
    <section
      aria-label="Bảng chỉ đường"
      aria-hidden={!directions.isOpen}
      inert={!directions.isOpen}
      className={`absolute inset-x-0 bottom-0 z-20 max-h-[50dvh] overflow-y-auto overscroll-contain rounded-t-2xl bg-white px-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-3 shadow-[0_-4px_16px_rgba(0,0,0,0.18)] transition-[transform,opacity] duration-200 sm:inset-x-auto sm:bottom-4 sm:left-4 sm:w-96 sm:max-h-[70vh] sm:rounded-2xl ${directions.isOpen ? "translate-y-0 opacity-100" : "pointer-events-none translate-y-full opacity-0"}`}
    >
      <div className="mx-auto mb-2 h-1 w-10 rounded-full bg-slate-300 sm:hidden" aria-hidden="true" />
      <header className="flex items-center gap-2">
        <h2 className="min-w-0 flex-1 text-lg font-semibold text-slate-900">Chỉ đường</h2>
        <button
          type="button"
          aria-label="Đóng chỉ đường"
          onClick={directions.close}
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-2xl text-slate-600 hover:bg-slate-100"
        >
          ×
        </button>
      </header>

      <div className="mt-2 grid grid-cols-2 gap-2" aria-label="Chọn loại xe">
        {vehicleOptions.map((option) => (
          <button
            key={option.value}
            type="button"
            aria-pressed={directions.vehicle === option.value}
            onClick={() => directions.setVehicle(option.value)}
            className={`min-h-11 rounded-lg border px-3 text-sm font-semibold ${directions.vehicle === option.value ? "border-blue-700 bg-blue-700 text-white" : "border-slate-300 bg-white text-slate-800 hover:bg-slate-50"}`}
          >
            {option.label}
          </button>
        ))}
      </div>

      {directions.activeEndpoint && (
        <div className="mt-3 space-y-2">
          <p className="text-sm text-slate-700">Tìm địa điểm hoặc chạm vào bản đồ để chọn {directions.activeEndpoint === "origin" ? "điểm đi" : "điểm đến"}.</p>
          <SearchBar near={near} onPick={directions.choosePlace} />
        </div>
      )}
      <div className="mt-3 flex flex-col gap-2">
        <EndpointRow
          end="origin"
          title="Điểm đi"
          value={directions.origin}
          active={directions.activeEndpoint === "origin"}
          onChoose={directions.setActiveEndpoint}
        />
        <div className="flex justify-center">
          <button
            type="button"
            aria-label="Đổi điểm đi và điểm đến"
            onClick={directions.swap}
            className="min-h-11 rounded-lg px-4 text-sm font-medium text-blue-800 hover:bg-blue-50"
          >
            Đổi chiều
          </button>
        </div>
        <EndpointRow
          end="destination"
          title="Điểm đến"
          value={directions.destination}
          active={directions.activeEndpoint === "destination"}
          onChoose={directions.setActiveEndpoint}
        />
      </div>


      {directions.loading && <p role="status" className="mt-3 text-sm text-slate-700">Đang tìm lộ trình…</p>}
      {directions.error && <p role="alert" className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-sm text-red-800">{directions.error}</p>}

      {directions.routes.length > 0 && (
        <div className="mt-3 space-y-2">
          <h3 className="text-sm font-semibold text-slate-900">Các lộ trình</h3>
          {routes.map((route, index) => {
            const isSelected = route.id === directions.selectedRouteId;
            const flood = floodSummary(route.flood);
            const floodTone = { bad: "text-red-800", warn: "text-amber-800", good: "text-emerald-800" } as const;
            return (
              <button
                key={route.id}
                type="button"
                aria-pressed={isSelected}
                onClick={() => directions.selectRoute(route.id)}
                className={`min-h-11 w-full rounded-xl border px-3 py-2 text-left ${isSelected ? "border-blue-700 bg-blue-50 ring-1 ring-blue-700" : "border-slate-200 bg-white hover:bg-slate-50"}`}
              >
                <span className="flex flex-wrap items-center gap-2 text-sm font-semibold text-slate-900">
                  <span>{routeName(route.kind, index)}</span>
                  {route.recommended && <span className="rounded-full bg-blue-700 px-2 py-0.5 text-xs font-medium text-white">Đề xuất</span>}
                  {route.long_detour && <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900">Vòng xa</span>}
                </span>
                <span className="mt-1 block text-sm text-slate-700">
                  {formatDuration(route.duration_s)} · {formatDistance(route.distance_m)} · tới nơi khoảng {formatArrival(route.arrive_at)}
                </span>
                {flood && <span className={`mt-0.5 block text-sm font-medium ${floodTone[flood.tone]}`}>{flood.text}</span>}
              </button>
            );
          })}
        </div>
      )}

      {selected && (
        <section className="mt-3 border-t border-slate-200 pt-3" aria-label="Các bước đi">
          <h3 className="text-sm font-semibold text-slate-900">Các bước đi</h3>
          {selected.steps.length === 0 ? (
            <p className="mt-2 text-sm text-slate-600">Chưa có chỉ dẫn chi tiết cho lộ trình này.</p>
          ) : (
            <ol className="mt-2 space-y-2">
              {selected.steps.map((step, index) => (
                <li key={`${selected.id}-${index}`} className="flex gap-3 rounded-lg bg-slate-50 px-3 py-2 text-sm">
                  <span aria-hidden="true" className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-white font-semibold text-blue-800 ring-1 ring-slate-200">{index + 1}</span>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-slate-900">{step.turn === "text" ? step.name : `${TURN_LABELS[step.turn] ?? "Tiếp tục"} · ${step.name}`}</p>
                    <p className="mt-0.5 text-slate-600">{formatDistance(step.distance_m)} · {formatDuration(step.duration_s)}</p>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </section>
      )}

      {directions.notes.length > 0 && (
        <div className="mt-3 space-y-1 border-t border-slate-200 pt-3" aria-label="Ghi chú lộ trình">
          {directions.notes.map((note) => <p key={note} className="text-xs leading-relaxed text-slate-600">{note}</p>)}
        </div>
      )}
    </section>
  );
}
