import { useEffect, useState } from "react";

import { floodSummary, formatArrival, formatDistance, formatDuration, prioritizeRoutes } from "../lib/directions";
import type { DirectionsController } from "../lib/useDirections";
import Icon from "./Icon";

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
const FLOOD_TONE = { bad: "bg-danger-tint text-danger-ink", warn: "bg-caution-tint text-caution-ink", good: "bg-safe-tint text-safe-ink" } as const;
const TIME_TONE = { bad: "text-danger", warn: "text-caution-ink", good: "text-safe" } as const;

/** Bảng lộ trình ở dưới khi chỉ đường: thời gian to, đoạn ngập trên đường, các bước đi gập mở được. */
export default function DirectionsPanel({ directions }: { directions: DirectionsController }) {
  const [showSteps, setShowSteps] = useState(false);
  const selected = directions.routes.find((route) => route.id === directions.selectedRouteId) ?? null;
  const routes = prioritizeRoutes(directions.routes);
  const visible = directions.isOpen && (directions.loading || directions.error !== null || directions.routes.length > 0);

  useEffect(() => setShowSteps(false), [directions.selectedRouteId, directions.routeRevision]);

  return (
    <section
      aria-label="Các lộ trình"
      aria-hidden={!visible}
      inert={!visible}
      className={`absolute inset-x-0 bottom-0 z-10 max-h-[48dvh] overflow-y-auto overscroll-contain rounded-t-3xl bg-white px-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-2.5 shadow-sheet transition-[transform,opacity] duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] sm:inset-x-auto sm:bottom-4 sm:left-4 sm:w-[26rem] sm:max-h-[60vh] sm:rounded-3xl sm:shadow-float ${visible ? "translate-y-0 opacity-100" : "pointer-events-none translate-y-full opacity-0"}`}
    >
      <div className="mx-auto mb-2 h-1 w-10 rounded-full bg-line sm:hidden" aria-hidden="true" />

      {directions.loading && (
        <div role="status" className="space-y-2 py-1">
          <p className="text-sm font-medium text-ink-soft">Đang tìm lộ trình và đo các đoạn ngập…</p>
          <div className="h-16 animate-pulse rounded-2xl bg-mist" />
          <div className="h-16 animate-pulse rounded-2xl bg-mist" />
        </div>
      )}
      {directions.error && (
        <p role="alert" className="flex gap-2.5 rounded-2xl bg-danger-tint px-3.5 py-3 text-sm text-danger-ink">
          <Icon name="alert" className="mt-0.5 h-4 w-4 shrink-0 text-danger" />
          {directions.error}
        </p>
      )}

      {!directions.loading && routes.length > 0 && (
        <div className="space-y-2">
          {routes.map((route, index) => {
            const isSelected = route.id === directions.selectedRouteId;
            const flood = floodSummary(route.flood);
            return (
              <button
                key={route.id}
                type="button"
                aria-pressed={isSelected}
                onClick={() => directions.selectRoute(route.id)}
                className={`w-full rounded-2xl border px-4 py-3 text-left transition-colors ${isSelected ? "border-brand bg-brand-tint/40 ring-1 ring-brand" : "border-line bg-white hover:bg-mist"}`}
              >
                <span className="flex items-baseline gap-2">
                  <span className={`text-xl font-bold tracking-[-0.02em] ${flood ? TIME_TONE[flood.tone] : "text-ink"}`}>{formatDuration(route.duration_s)}</span>
                  <span className="text-sm text-ink-faint">({formatDistance(route.distance_m)})</span>
                  <span className="ml-auto flex gap-1.5">
                    {route.recommended && <span className="rounded-full bg-brand px-2 py-0.5 text-xs font-semibold text-white">Đề xuất</span>}
                    {route.long_detour && <span className="rounded-full bg-caution-tint px-2 py-0.5 text-xs font-semibold text-caution-ink">Vòng xa</span>}
                  </span>
                </span>
                <span className="mt-0.5 block text-sm text-ink-soft">
                  {routeName(route.kind, index)} · tới nơi khoảng {formatArrival(route.arrive_at)}
                </span>
                {flood && <span className={`mt-2 inline-block rounded-lg px-2 py-1 text-[13px] font-semibold ${FLOOD_TONE[flood.tone]}`}>{flood.text}</span>}
              </button>
            );
          })}
        </div>
      )}

      {!directions.loading && selected && (
        <div className="mt-3 border-t border-line pt-2">
          <button
            type="button"
            aria-expanded={showSteps}
            onClick={() => setShowSteps((value) => !value)}
            className="flex min-h-11 w-full items-center justify-between rounded-xl px-1 text-sm font-semibold text-ink hover:bg-mist"
          >
            Các bước đi{selected.steps.length > 0 ? ` (${selected.steps.length})` : ""}
            <Icon name="chevron" className={`h-5 w-5 text-ink-faint transition-transform ${showSteps ? "rotate-180" : ""}`} />
          </button>
          {showSteps &&
            (selected.steps.length === 0 ? (
              <p className="mt-1 text-sm text-ink-faint">Chưa có chỉ dẫn chi tiết cho lộ trình này.</p>
            ) : (
              <ol className="mt-1 space-y-1.5">
                {selected.steps.map((step, index) => (
                  <li key={`${selected.id}-${index}`} className="flex gap-3 rounded-xl bg-mist px-3 py-2.5 text-sm">
                    <span aria-hidden="true" className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-white text-xs font-semibold text-brand shadow-float">
                      {index + 1}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-ink">{step.turn === "text" ? step.name : `${TURN_LABELS[step.turn] ?? "Tiếp tục"} · ${step.name}`}</p>
                      <p className="mt-0.5 text-ink-faint">
                        {formatDistance(step.distance_m)} · {formatDuration(step.duration_s)}
                      </p>
                    </div>
                  </li>
                ))}
              </ol>
            ))}
        </div>
      )}

      {!directions.loading && directions.notes.length > 0 && (
        <div className="mt-3 space-y-1 border-t border-line pt-3" aria-label="Ghi chú lộ trình">
          {directions.notes.map((note) => (
            <p key={note} className="text-xs leading-relaxed text-ink-faint">
              {note}
            </p>
          ))}
        </div>
      )}
    </section>
  );
}
