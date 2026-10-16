import { LEVEL_COLOR, REPORT_COLOR } from "../MapView";

function Swatch({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span aria-hidden="true" className="h-1.5 w-5 rounded-full" style={{ backgroundColor: color }} />
      {label}
    </span>
  );
}

/** Chú giải gọn ở góc bản đồ: người lái xe đọc được màu mà không phải mở bảng lớp. */
export default function Legend() {
  return (
    <div aria-label="Chú giải màu" className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-2xl bg-white/95 px-3 py-1.5 text-xs font-medium text-ink-soft shadow-float">
      <Swatch color={LEVEL_COLOR[2]} label="Nguy cơ cao" />
      <Swatch color={LEVEL_COLOR[1]} label="Có thể ngập" />
      <span className="flex items-center gap-1.5">
        <span aria-hidden="true" className="h-2.5 w-2.5 rounded-full ring-2 ring-white" style={{ backgroundColor: REPORT_COLOR.flooded }} />
        Báo ngập
      </span>
    </div>
  );
}
