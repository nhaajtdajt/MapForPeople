import { useState } from "react";

import type { Health } from "../api";
import { fakePartLabels, statusChipText } from "../lib/format";

/** Nhãn "Dữ liệu mẫu" hoặc "Đang dùng bản giả"; chạm vào để xem chi tiết (spec 01, mục 3.2). */
export default function StatusChip({ health }: { health: Health | null }) {
  const [open, setOpen] = useState(false);
  const text = statusChipText(health);
  if (!health || !text) return null;
  const fakes = fakePartLabels(health);
  return (
    <div className="relative">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        className="min-h-8 shrink-0 rounded-full bg-caution-tint px-3 text-xs font-semibold text-caution-ink shadow-float"
      >
        {text}
      </button>
      {open && (
        <div role="status" className="pop-in absolute right-0 top-10 z-20 w-64 rounded-2xl bg-white p-4 text-sm text-ink-soft shadow-float ring-1 ring-line">
          <p>{health.data === "sample" ? "Đang chạy trên dữ liệu mẫu, không phải dữ liệu thật." : "Đang chạy trên dữ liệu thật."}</p>
          {fakes.length > 0 ? (
            <p className="mt-1">Các phần đang là bản giả: {fakes.join(", ")}.</p>
          ) : (
            <p className="mt-1">Mọi phần đều đã nối với bản thật.</p>
          )}
        </div>
      )}
    </div>
  );
}
