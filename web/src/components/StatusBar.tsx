import { useState } from "react";

import type { RiskState } from "../api";
import { statusParts, type Tone } from "../lib/floodnote";
import Icon, { type IconName } from "./Icon";

const TONE: Record<Tone, string> = {
  quiet: "bg-white text-ink",
  watch: "bg-caution-tint text-caution-ink",
  alert: "bg-danger-tint text-danger-ink",
};
const DOT: Record<Tone, string> = { quiet: "bg-safe", watch: "bg-caution", alert: "bg-danger" };

function Cell({ icon, tone, text }: { icon: IconName; tone: Tone; text: string }) {
  return (
    <span className={`flex min-w-0 items-center gap-1.5 rounded-full px-2.5 py-1.5 text-[13px] font-medium shadow-float ${TONE[tone]}`}>
      <Icon name={icon} className="h-4 w-4 shrink-0" />
      <span className="truncate">{text}</span>
      <span aria-hidden="true" className={`h-1.5 w-1.5 shrink-0 rounded-full ${DOT[tone]}`} />
    </span>
  );
}

/** Mưa và triều lúc này, mỗi thứ một ô màu theo mức; chạm để xem số liệu đứng sau. */
export default function StatusBar({ city, risk }: { city: string; risk: RiskState | null }) {
  const [open, setOpen] = useState(false);
  const parts = statusParts(risk);
  if (!parts) {
    return <span className="rounded-full bg-white px-3 py-1.5 text-[13px] font-medium text-ink-soft shadow-float">{city} · Đang lấy số liệu mưa và triều…</span>;
  }
  return (
    <div className="relative min-w-0">
      <button
        type="button"
        aria-expanded={open}
        aria-label={`${city}: ${parts.rain.text}, ${parts.tide.text}${parts.peak ? `, ${parts.peak.text}` : ""}. Cập nhật ${parts.updated}. Chạm để xem chi tiết.`}
        onClick={() => setOpen((value) => !value)}
        className="flex max-w-full flex-wrap items-center gap-1.5 text-left"
      >
        <Cell icon="rain" tone={parts.rain.tone} text={parts.rain.text} />
        <Cell icon="tide" tone={parts.tide.tone} text={parts.tide.text} />
        {parts.peak && <Cell icon="tide" tone={parts.peak.tone} text={parts.peak.text} />}
      </button>
      {open && (
        <div role="status" className="pop-in absolute left-0 top-full z-20 mt-2 w-[min(22rem,calc(100vw-1.5rem))] rounded-2xl bg-white p-4 text-sm text-ink-soft shadow-float ring-1 ring-line">
          <p className="font-semibold text-ink">
            {city} · số liệu lúc {parts.updated}
          </p>
          <ul className="mt-2 space-y-1.5">
            {parts.details.map((line) => (
              <li key={line} className="leading-snug">
                {line}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
