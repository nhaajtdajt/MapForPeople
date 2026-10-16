import type { ReportBody } from "../api";

type Choice = Pick<ReportBody, "status" | "depth">;

const CHOICES: { label: string; hint: string; tone: string; choice: Choice }[] = [
  { label: "Không ngập", hint: "Đường đi bình thường", tone: "bg-safe hover:bg-safe-ink", choice: { status: "clear", depth: null } },
  { label: "Ngập nhẹ", hint: "Dưới 10 cm, xe máy đi được", tone: "bg-amber-600 hover:bg-amber-700", choice: { status: "flooded", depth: "light" } },
  { label: "Ngập vừa", hint: "10 tới 30 cm, gần ngập bô xe máy", tone: "bg-orange-600 hover:bg-orange-700", choice: { status: "flooded", depth: "medium" } },
  { label: "Ngập cao", hint: "Trên 30 cm, xe máy dễ chết máy", tone: "bg-danger hover:bg-danger-ink", choice: { status: "flooded", depth: "high" } },
];

interface Props {
  place: string;
  busy: boolean;
  onChoose: (choice: Choice) => void;
  onClose: () => void;
}

/** Báo ngập một chạm: bốn nút lớn, bấm là gửi. */
export default function ReportSheet({ place, busy, onChoose, onClose }: Props) {
  return (
    <div className="absolute inset-0 z-30 flex items-end justify-center bg-ink/45 sm:items-center" onClick={onClose}>
      <section
        role="dialog"
        aria-label="Báo ngập"
        onClick={(event) => event.stopPropagation()}
        className="sheet-in w-full max-w-md rounded-t-3xl bg-white p-4 pb-[max(1rem,env(safe-area-inset-bottom))] shadow-sheet sm:rounded-3xl"
      >
        <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-line sm:hidden" aria-hidden="true" />
        <h2 className="text-lg font-semibold tracking-[-0.01em] text-ink">Chỗ này đang thế nào?</h2>
        <p className="mt-0.5 text-sm text-ink-faint">{place}</p>
        <div className="mt-3 grid grid-cols-2 gap-2">
          {CHOICES.map((item) => (
            <button
              key={item.label}
              type="button"
              disabled={busy}
              onClick={() => onChoose(item.choice)}
              className={`min-h-20 rounded-2xl px-3.5 py-3 text-left text-white transition-[transform,background-color] active:scale-[0.97] disabled:opacity-60 ${item.tone}`}
            >
              <span className="block text-base font-semibold">{item.label}</span>
              <span className="block text-xs opacity-90">{item.hint}</span>
            </button>
          ))}
        </div>
        <p className="mt-3 text-xs text-ink-faint">Bấm là gửi ngay. Báo cáo giữ trên bản đồ 90 phút.</p>
        <button type="button" onClick={onClose} className="mt-2 min-h-12 w-full rounded-xl bg-mist text-sm font-semibold text-ink hover:bg-line">
          Hủy
        </button>
      </section>
    </div>
  );
}
