import { addressRest, formatCoords } from "../lib/format";

export interface Pin {
  lat: number;
  lon: number;
  name: string;
  address: string;
  loading: boolean;
}

/** Thông tin ngập tại chỗ vừa chạm: mức của tuyến theo mô hình, hoặc một điểm ngập đã công bố. */
export interface FloodNote {
  tone: "high" | "medium" | "info";
  title: string;
  lines: string[];
}

const NOTE_TONE: Record<FloodNote["tone"], string> = {
  high: "border-red-300 bg-red-50 text-red-950",
  medium: "border-amber-300 bg-amber-50 text-amber-950",
  info: "border-sky-300 bg-sky-50 text-sky-950",
};

interface Props {
  pin: Pin;
  flood?: FloodNote | null;
  onClose: () => void;
  onDirectionsTo?: () => void;
  onDirectionsFrom?: () => void;
  onReport?: () => void;
}

function ActionButton({ label, onClick, primary = false }: { label: string; onClick?: () => void; primary?: boolean }) {
  const enabled = onClick !== undefined;
  const tone = primary
    ? "bg-blue-700 text-white enabled:hover:bg-blue-800"
    : "bg-slate-100 text-slate-900 enabled:hover:bg-slate-200";
  return (
    <button
      type="button"
      disabled={!enabled}
      title={enabled ? undefined : "Sắp có"}
      onClick={onClick}
      className={`min-h-11 flex-1 rounded-lg px-3 text-sm font-medium disabled:opacity-45 ${tone}`}
    >
      {label}
    </button>
  );
}

export default function PlaceCard({ pin, flood, onClose, onDirectionsTo, onDirectionsFrom, onReport }: Props) {
  const title = pin.name || (pin.loading ? "Đang tìm địa chỉ…" : "Điểm đã chọn");
  const rest = addressRest(pin.name, pin.address);
  return (
    <section
      aria-label="Thông tin địa điểm"
      className="absolute inset-x-0 bottom-0 z-10 rounded-t-2xl bg-white px-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-3 shadow-[0_-4px_16px_rgba(0,0,0,0.15)] sm:inset-x-auto sm:bottom-4 sm:left-4 sm:w-96 sm:rounded-2xl"
    >
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <h2 className="text-lg font-semibold leading-snug text-slate-900">{title}</h2>
          {rest && <p className="text-sm text-slate-700">{rest}</p>}
          <p className="mt-0.5 text-xs text-slate-500">{formatCoords(pin.lat, pin.lon)}</p>
        </div>
        <button
          type="button"
          aria-label="Đóng thẻ địa điểm"
          onClick={onClose}
          className="-mr-2 -mt-1 flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-2xl text-slate-500 hover:bg-slate-100"
        >
          ×
        </button>
      </div>
      {flood && (
        <div role="note" aria-label="Thông tin ngập" className={`mt-2 rounded-lg border px-3 py-2 text-sm ${NOTE_TONE[flood.tone]}`}>
          <p className="font-semibold">{flood.title}</p>
          {flood.lines.map((line) => (
            <p key={line} className="mt-0.5">
              {line}
            </p>
          ))}
        </div>
      )}
      <div className="mt-3 flex gap-2">
        <ActionButton label="Chỉ đường tới đây" onClick={onDirectionsTo} primary />
        <ActionButton label="Đi từ đây" onClick={onDirectionsFrom} />
        <ActionButton label="Báo ngập ở đây" onClick={onReport} />
      </div>
    </section>
  );
}
