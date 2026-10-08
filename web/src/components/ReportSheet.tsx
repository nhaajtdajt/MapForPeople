import type { ReportBody } from "../api";

type Choice = Pick<ReportBody, "status" | "depth">;

const CHOICES: { label: string; hint: string; tone: string; choice: Choice }[] = [
  { label: "Không ngập", hint: "Đường đi bình thường", tone: "bg-emerald-600 hover:bg-emerald-700", choice: { status: "clear", depth: null } },
  { label: "Ngập nhẹ", hint: "Dưới 10 cm, xe máy đi được", tone: "bg-amber-500 hover:bg-amber-600", choice: { status: "flooded", depth: "light" } },
  { label: "Ngập vừa", hint: "10 tới 30 cm, gần ngập bô xe máy", tone: "bg-orange-600 hover:bg-orange-700", choice: { status: "flooded", depth: "medium" } },
  { label: "Ngập cao", hint: "Trên 30 cm, xe máy dễ chết máy", tone: "bg-red-700 hover:bg-red-800", choice: { status: "flooded", depth: "high" } },
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
    <div className="absolute inset-0 z-30 flex items-end justify-center bg-slate-900/40 sm:items-center" onClick={onClose}>
      <section
        role="dialog"
        aria-label="Báo ngập"
        onClick={(event) => event.stopPropagation()}
        className="w-full max-w-md rounded-t-2xl bg-white p-4 pb-[max(1rem,env(safe-area-inset-bottom))] shadow-xl sm:rounded-2xl"
      >
        <h2 className="text-lg font-semibold text-slate-900">Chỗ này đang thế nào?</h2>
        <p className="text-sm text-slate-600">{place}</p>
        <div className="mt-3 grid grid-cols-2 gap-2">
          {CHOICES.map((item) => (
            <button
              key={item.label}
              type="button"
              disabled={busy}
              onClick={() => onChoose(item.choice)}
              className={`min-h-20 rounded-xl px-3 py-2 text-left text-white disabled:opacity-60 ${item.tone}`}
            >
              <span className="block text-base font-semibold">{item.label}</span>
              <span className="block text-xs opacity-90">{item.hint}</span>
            </button>
          ))}
        </div>
        <button type="button" onClick={onClose} className="mt-3 min-h-11 w-full rounded-lg bg-slate-100 text-sm font-medium text-slate-900 hover:bg-slate-200">
          Hủy
        </button>
      </section>
    </div>
  );
}
