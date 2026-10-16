import Icon, { CloseButton } from "./Icon";
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
    <div className={`flex min-w-0 items-center gap-3 rounded-2xl border px-3 py-2.5 transition-colors ${active ? "border-brand bg-brand-tint/40 ring-1 ring-brand" : "border-line"}`}>
      <span aria-hidden="true" className={`h-3 w-3 shrink-0 rounded-full ${end === "origin" ? "bg-safe ring-4 ring-safe-tint" : "bg-danger ring-4 ring-danger-tint"}`} />
      <div className="min-w-0 flex-1">
        <p className="text-xs font-medium text-ink-faint">{title}</p>
        <p className="truncate text-[15px] font-semibold text-ink">{value?.label ?? "Chưa chọn"}</p>
        {value?.address && <p className="truncate text-xs text-ink-soft">{value.address}</p>}
        {value && <p className="text-xs text-ink-faint">{formatCoords(value.lat, value.lon)}</p>}
      </div>
      <button
        type="button"
        aria-pressed={active}
        onClick={() => onChoose(end)}
        className="min-h-11 shrink-0 rounded-xl px-3 text-sm font-semibold text-brand hover:bg-brand-tint"
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
      className={`absolute inset-x-0 bottom-0 z-20 max-h-[55dvh] overflow-y-auto overscroll-contain rounded-t-3xl bg-white px-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-2.5 shadow-sheet transition-[transform,opacity] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] sm:inset-x-auto sm:bottom-4 sm:left-4 sm:w-[26rem] sm:max-h-[75vh] sm:rounded-3xl sm:shadow-float ${directions.isOpen ? "translate-y-0 opacity-100" : "pointer-events-none translate-y-full opacity-0"}`}
    >
      <div className="mx-auto mb-2 h-1 w-10 rounded-full bg-line sm:hidden" aria-hidden="true" />
      <header className="flex items-center gap-2">
        <h2 className="min-w-0 flex-1 text-lg font-semibold tracking-[-0.01em] text-ink">Chỉ đường tránh ngập</h2>
        <CloseButton label="Đóng chỉ đường" onClick={directions.close} className="-mr-2" />
      </header>

      <div className="mt-2 grid grid-cols-2 gap-1 rounded-xl bg-mist p-1" aria-label="Chọn loại xe">
        {vehicleOptions.map((option) => (
          <button
            key={option.value}
            type="button"
            aria-pressed={directions.vehicle === option.value}
            onClick={() => directions.setVehicle(option.value)}
            className={`min-h-10 rounded-lg px-3 text-sm font-semibold transition-colors ${directions.vehicle === option.value ? "bg-white text-ink shadow-float" : "text-ink-soft hover:text-ink"}`}
          >
            {option.label}
          </button>
        ))}
      </div>

      {directions.activeEndpoint && (
        <div className="mt-3 space-y-2">
          <p className="text-sm text-ink-soft">Tìm địa điểm hoặc chạm vào bản đồ để chọn {directions.activeEndpoint === "origin" ? "điểm đi" : "điểm đến"}.</p>
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
            className="flex min-h-10 items-center gap-1.5 rounded-xl px-3 text-sm font-semibold text-brand hover:bg-brand-tint"
          >
            <Icon name="swap" className="h-4 w-4" />
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


      {directions.loading && <p role="status" className="mt-3 animate-pulse text-sm font-medium text-ink-soft">Đang tìm lộ trình và đo đoạn ngập…</p>}
      {directions.error && <p role="alert" className="mt-3 rounded-2xl bg-danger-tint px-3.5 py-3 text-sm text-danger-ink">{directions.error}</p>}

      {directions.routes.length > 0 && (
        <div className="mt-3 space-y-2">
          <h3 className="text-sm font-semibold text-ink">Các lộ trình</h3>
          {routes.map((route, index) => {
            const isSelected = route.id === directions.selectedRouteId;
            const flood = floodSummary(route.flood);
            const floodTone = { bad: "bg-danger-tint text-danger-ink", warn: "bg-caution-tint text-caution-ink", good: "bg-safe-tint text-safe-ink" } as const;
            return (
              <button
                key={route.id}
                type="button"
                aria-pressed={isSelected}
                onClick={() => directions.selectRoute(route.id)}
                className={`min-h-11 w-full rounded-2xl border px-3.5 py-3 text-left transition-colors ${isSelected ? "border-brand bg-brand-tint/50 ring-1 ring-brand" : "border-line bg-white hover:bg-mist"}`}
              >
                <span className="flex flex-wrap items-center gap-2 text-[15px] font-semibold text-ink">
                  <span>{routeName(route.kind, index)}</span>
                  {route.recommended && <span className="rounded-full bg-brand px-2 py-0.5 text-xs font-semibold text-white">Đề xuất</span>}
                  {route.long_detour && <span className="rounded-full bg-caution-tint px-2 py-0.5 text-xs font-semibold text-caution-ink">Vòng xa</span>}
                </span>
                <span className="mt-1 block text-sm text-ink-soft">
                  {formatDuration(route.duration_s)} · {formatDistance(route.distance_m)} · tới nơi khoảng {formatArrival(route.arrive_at)}
                </span>
                {flood && <span className={`mt-2 inline-block rounded-lg px-2 py-1 text-[13px] font-semibold ${floodTone[flood.tone]}`}>{flood.text}</span>}
              </button>
            );
          })}
        </div>
      )}

      {selected && (
        <section className="mt-3 border-t border-line pt-3" aria-label="Các bước đi">
          <h3 className="text-sm font-semibold text-ink">Các bước đi</h3>
          {selected.steps.length === 0 ? (
            <p className="mt-2 text-sm text-ink-faint">Chưa có chỉ dẫn chi tiết cho lộ trình này.</p>
          ) : (
            <ol className="mt-2 space-y-2">
              {selected.steps.map((step, index) => (
                <li key={`${selected.id}-${index}`} className="flex gap-3 rounded-xl bg-mist px-3 py-2.5 text-sm">
                  <span aria-hidden="true" className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-white text-xs font-semibold text-brand shadow-float">{index + 1}</span>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-ink">{step.turn === "text" ? step.name : `${TURN_LABELS[step.turn] ?? "Tiếp tục"} · ${step.name}`}</p>
                    <p className="mt-0.5 text-ink-faint">{formatDistance(step.distance_m)} · {formatDuration(step.duration_s)}</p>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </section>
      )}

      {directions.notes.length > 0 && (
        <div className="mt-3 space-y-1 border-t border-line pt-3" aria-label="Ghi chú lộ trình">
          {directions.notes.map((note) => <p key={note} className="text-xs leading-relaxed text-ink-faint">{note}</p>)}
        </div>
      )}
    </section>
  );
}
