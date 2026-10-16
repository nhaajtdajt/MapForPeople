import { useState } from "react";

import type { FloodHistory, HistoryEvent, HistoryPlace } from "../api";
import { HISTORY_COLOR, LEVEL_COLOR } from "../MapView";
import Icon, { CloseButton } from "./Icon";

export const RESULT_LABEL: Record<HistoryPlace["result"], string> = {
  hit: "Báo đúng",
  miss: "Bỏ sót",
  false_alarm: "Báo thừa",
  quiet_ok: "Đúng: không báo",
};
const RESULT_TONE: Record<HistoryPlace["result"], string> = {
  hit: "bg-safe-tint text-safe-ink",
  miss: "bg-danger-tint text-danger-ink",
  false_alarm: "bg-caution-tint text-caution-ink",
  quiet_ok: "bg-safe-tint text-safe-ink",
};

function Score({ event }: { event: HistoryEvent }) {
  const s = event.summary;
  const flood = s.hit + s.miss;
  const dry = s.quiet_ok + s.false_alarm;
  return (
    <span className="flex flex-wrap gap-1.5">
      {flood > 0 && (
        <span className="rounded-full bg-safe-tint px-2 py-0.5 text-xs font-semibold text-safe-ink">
          Đúng {s.hit}/{flood} chỗ ngập
        </span>
      )}
      {s.miss > 0 && <span className="rounded-full bg-danger-tint px-2 py-0.5 text-xs font-semibold text-danger-ink">Sót {s.miss}</span>}
      {dry > 0 && (
        <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${s.false_alarm ? "bg-caution-tint text-caution-ink" : "bg-safe-tint text-safe-ink"}`}>
          {s.false_alarm ? `Báo thừa ${s.false_alarm}/${dry} chỗ khô` : `Không báo thừa ${s.quiet_ok}/${dry} chỗ khô`}
        </span>
      )}
    </span>
  );
}

function Dot({ result }: { result: HistoryPlace["result"] }) {
  const miss = result === "miss";
  return (
    <span
      aria-hidden="true"
      className="inline-block h-3 w-3 shrink-0 rounded-full"
      style={{ backgroundColor: miss ? "#ffffff" : HISTORY_COLOR[result], boxShadow: miss ? `inset 0 0 0 3px ${HISTORY_COLOR.miss}` : "0 0 0 2px #fff" }}
    />
  );
}

interface Props {
  history: FloodHistory | null;
  error: string | null;
  selected: HistoryEvent | null;
  onSelect: (id: string | null) => void;
  onRoute: () => void;
  onClose: () => void;
}

/** Xem lại các trận ngập: chọn một trận, bản đồ tô lại đúng như app đã tô lúc đó, kèm chỗ ngập thật đúng hay sót. */
export default function HistoryPanel({ history, error, selected, onSelect, onRoute, onClose }: Props) {
  const [details, setDetails] = useState(false);

  return (
    <div className="pointer-events-none absolute inset-x-0 top-0 z-20 flex flex-col gap-2 p-3 pt-[max(0.75rem,env(safe-area-inset-top))] sm:w-[26rem]">
      <section aria-label="Xem lại các trận ngập" className="sheet-in pointer-events-auto max-h-[60dvh] overflow-y-auto rounded-3xl bg-white p-4 pt-3 shadow-float">
        <header className="flex items-center gap-1">
          {selected && (
            <button type="button" aria-label="Về danh sách trận" onClick={() => onSelect(null)} className="-ml-2 flex h-11 w-10 items-center justify-center rounded-full text-ink-soft hover:bg-mist">
              <Icon name="back" />
            </button>
          )}
          <h2 className="min-w-0 flex-1 text-base font-semibold tracking-[-0.01em] text-ink">{selected ? selected.title : "Xem lại các trận ngập"}</h2>
          <CloseButton label="Thoát xem lại" onClick={onClose} className="-mr-2" />
        </header>

        {!selected && (
          <>
            <p className="mt-1 text-sm text-ink-soft">
              Bản đồ được tô lại bằng đúng quy tắc app đang chạy, rồi so với chỗ ngập thật trên báo hoặc ảnh camera. Không chỉnh gì cho khớp. Chỉ chấm được những chỗ báo chí hoặc camera nêu; đường khác chưa có gì để đối chiếu.
            </p>
            {error && <p role="alert" className="mt-3 rounded-2xl bg-caution-tint px-3.5 py-3 text-sm text-caution-ink">{error}</p>}
            {!history && !error && <div className="mt-3 h-24 animate-pulse rounded-2xl bg-mist" />}
            <ul className="mt-3 space-y-2">
              {history?.events.map((event) => (
                <li key={event.id}>
                  <button type="button" onClick={() => onSelect(event.id)} className="flex w-full gap-3 rounded-2xl border border-line px-3.5 py-3 text-left transition-colors hover:bg-mist">
                    <span className={`mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${event.cause === "tide" ? "bg-[#e0f2f1] text-water" : "bg-brand-tint text-brand"}`}>
                      <Icon name={event.cause === "tide" ? "tide" : "rain"} className="h-[18px] w-[18px]" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-[15px] font-semibold text-ink">{event.title}</span>
                      <span className="mb-1.5 block text-xs text-ink-faint">{event.when}</span>
                      <Score event={event} />
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}

        {selected && (
          <div className="mt-1">
            <p className="text-xs text-ink-faint">{selected.when}</p>
            <div className="mt-2">
              <Score event={selected} />
            </div>
            <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1.5 text-xs font-medium text-ink-soft">
              {selected.summary.hit + selected.summary.miss > 0 && (
                <>
                  <span className="flex items-center gap-1.5"><Dot result="hit" /> Báo đúng</span>
                  <span className="flex items-center gap-1.5"><Dot result="miss" /> Bỏ sót</span>
                </>
              )}
              {selected.summary.quiet_ok + selected.summary.false_alarm > 0 && (
                <>
                  <span className="flex items-center gap-1.5"><Dot result="quiet_ok" /> Khô, không báo</span>
                  <span className="flex items-center gap-1.5"><Dot result="false_alarm" /> Báo thừa</span>
                </>
              )}
              <span className="flex items-center gap-1.5"><span aria-hidden="true" className="h-1.5 w-5 rounded-full" style={{ backgroundColor: LEVEL_COLOR[2] }} /> App tô đỏ</span>
              <span className="flex items-center gap-1.5"><span aria-hidden="true" className="h-1.5 w-5 rounded-full" style={{ backgroundColor: LEVEL_COLOR[1] }} /> App tô vàng</span>
            </div>
            <button
              type="button"
              aria-expanded={details}
              onClick={() => setDetails((value) => !value)}
              className="mt-2 flex min-h-10 w-full items-center justify-between rounded-xl px-1 text-sm font-semibold text-brand hover:bg-brand-tint"
            >
              Cơ sở dự đoán và nguồn
              <Icon name="chevron" className={`h-5 w-5 transition-transform ${details ? "rotate-180" : ""}`} />
            </button>
            {details && (
              <div className="space-y-2 pb-1 text-sm text-ink-soft">
                <ul className="space-y-1">
                  {selected.basis.map((line) => (
                    <li key={line} className="flex gap-2">
                      <span aria-hidden="true" className="mt-2 h-1 w-1 shrink-0 rounded-full bg-ink-faint" />
                      {line}
                    </li>
                  ))}
                  <li className="flex gap-2">
                    <span aria-hidden="true" className="mt-2 h-1 w-1 shrink-0 rounded-full bg-ink-faint" />
                    Tổng cộng app tô {selected.summary.red.toLocaleString("vi-VN")} đoạn đỏ và {selected.summary.yellow.toLocaleString("vi-VN")} đoạn vàng.
                  </li>
                </ul>
                <p className="rounded-xl bg-mist px-3 py-2 text-xs leading-relaxed">{selected.note}</p>
                {selected.sources.map((source) =>
                  source.url ? (
                    <a key={source.label} href={source.url} target="_blank" rel="noreferrer" className="block text-xs font-medium text-brand underline underline-offset-2">
                      {source.label}
                    </a>
                  ) : (
                    <p key={source.label} className="text-xs">{source.label}</p>
                  ),
                )}
              </div>
            )}
            <button
              type="button"
              onClick={onRoute}
              className="mt-2 flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-brand px-3 text-sm font-semibold text-white transition-colors hover:bg-brand-strong"
            >
              <Icon name="route" className="h-[18px] w-[18px]" />
              Tìm đường trong trận này
            </button>
            <p className="mt-2 text-xs text-ink-faint">Chạm vào từng chấm trên bản đồ để xem vì sao app báo như vậy.</p>
          </div>
        )}
      </section>
    </div>
  );
}

/** Thẻ dưới khi chạm một chỗ trong trận đang xem lại: thực tế, app đã báo gì, và dựa trên cơ sở nào. */
export function HistoryPlaceCard({ place, onClose }: { place: HistoryPlace; onClose: () => void }) {
  return (
    <section
      aria-label="Đối chiếu tại chỗ"
      className="sheet-in absolute inset-x-0 bottom-0 z-10 max-h-[55dvh] overflow-y-auto rounded-t-3xl bg-white px-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-2.5 shadow-sheet sm:inset-x-auto sm:bottom-4 sm:left-4 sm:w-[26rem] sm:rounded-3xl sm:shadow-float"
    >
      <div className="mx-auto mb-2 h-1 w-10 rounded-full bg-line sm:hidden" aria-hidden="true" />
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1 pt-1">
          <span className={`inline-block rounded-full px-2.5 py-0.5 text-xs font-semibold ${RESULT_TONE[place.result]}`}>{RESULT_LABEL[place.result]}</span>
          <h2 className="mt-1.5 text-lg font-semibold leading-snug tracking-[-0.01em] text-ink">{place.name}</h2>
        </div>
        <CloseButton label="Đóng thẻ đối chiếu" onClick={onClose} className="-mr-2" />
      </div>
      <dl className="mt-2 space-y-2 text-sm">
        <div className="rounded-2xl bg-mist px-3.5 py-2.5">
          <dt className="text-xs font-semibold text-ink-faint">Thực tế</dt>
          <dd className="mt-0.5 text-ink">{place.observed}</dd>
        </div>
        <div className="rounded-2xl bg-mist px-3.5 py-2.5">
          <dt className="text-xs font-semibold text-ink-faint">App đã báo</dt>
          <dd className="mt-0.5 text-ink">{place.shown}</dd>
        </div>
      </dl>
      <h3 className="mt-3 text-sm font-semibold text-ink">Vì sao app báo như vậy</h3>
      <ul className="mt-1.5 space-y-1.5 text-sm text-ink-soft">
        {place.basis.map((line) => (
          <li key={line} className="flex gap-2 leading-snug">
            <span aria-hidden="true" className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-brand" />
            {line}
          </li>
        ))}
      </ul>
    </section>
  );
}
