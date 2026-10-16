import { addressRest, formatCoords } from "../lib/format";
import Icon, { CloseButton, type IconName } from "./Icon";

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

const NOTE_TONE: Record<FloodNote["tone"], { box: string; icon: string; name: IconName }> = {
  high: { box: "bg-danger-tint text-danger-ink", icon: "text-danger", name: "alert" },
  medium: { box: "bg-caution-tint text-caution-ink", icon: "text-caution", name: "alert" },
  info: { box: "bg-brand-tint text-brand-strong", icon: "text-brand", name: "info" },
};

interface Props {
  pin: Pin;
  flood?: FloodNote | null;
  onClose: () => void;
  onDirectionsTo?: () => void;
  onDirectionsFrom?: () => void;
  onReport?: () => void;
}

function ActionButton({ label, icon, onClick, primary = false }: { label: string; icon: IconName; onClick?: () => void; primary?: boolean }) {
  const enabled = onClick !== undefined;
  const tone = primary
    ? "bg-brand text-white enabled:hover:bg-brand-strong"
    : "bg-mist text-ink enabled:hover:bg-line";
  return (
    <button
      type="button"
      disabled={!enabled}
      title={enabled ? undefined : "Sắp có"}
      onClick={onClick}
      className={`flex min-h-12 items-center justify-center gap-2 rounded-xl px-3 text-sm font-semibold transition-colors enabled:active:scale-[0.98] disabled:opacity-45 ${primary ? "col-span-2" : ""} ${tone}`}
    >
      <Icon name={icon} className="h-[18px] w-[18px]" />
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
      className="sheet-in absolute inset-x-0 bottom-0 z-10 max-h-[70dvh] overflow-y-auto rounded-t-3xl bg-white px-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-2.5 shadow-sheet sm:inset-x-auto sm:bottom-4 sm:left-4 sm:w-96 sm:rounded-3xl sm:shadow-float"
    >
      <div className="mx-auto mb-2 h-1 w-10 rounded-full bg-line sm:hidden" aria-hidden="true" />
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1 pt-1">
          <h2 className="text-lg font-semibold leading-snug tracking-[-0.01em] text-ink">{title}</h2>
          {rest && <p className="mt-0.5 text-sm text-ink-soft">{rest}</p>}
          <p className="mt-1 text-xs text-ink-faint">{formatCoords(pin.lat, pin.lon)}</p>
        </div>
        <CloseButton label="Đóng thẻ địa điểm" onClick={onClose} className="-mr-2" />
      </div>
      {flood && (
        <div role="note" aria-label="Thông tin ngập" className={`mt-3 flex gap-2.5 rounded-2xl px-3.5 py-3 text-sm ${NOTE_TONE[flood.tone].box}`}>
          <Icon name={NOTE_TONE[flood.tone].name} className={`mt-0.5 h-[18px] w-[18px] shrink-0 ${NOTE_TONE[flood.tone].icon}`} />
          <div className="min-w-0">
            <p className="font-semibold leading-snug">{flood.title}</p>
            {flood.lines.map((line) => (
              <p key={line} className="mt-1 leading-snug opacity-90">
                {line}
              </p>
            ))}
          </div>
        </div>
      )}
      <div className="mt-3 grid grid-cols-2 gap-2">
        <ActionButton label="Chỉ đường tới đây" icon="route" onClick={onDirectionsTo} primary />
        <ActionButton label="Đi từ đây" icon="from" onClick={onDirectionsFrom} />
        <ActionButton label="Báo ngập" icon="flag" onClick={onReport} />
      </div>
    </section>
  );
}
