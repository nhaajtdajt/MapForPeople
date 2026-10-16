import type { City, CityKey } from "../api";
import { CAMERA_COLOR, LEVEL_COLOR, POINT_COLOR, REPORT_COLOR } from "../MapView";
import Icon, { CloseButton } from "./Icon";

interface Props {
  cities: City[];
  current: CityKey;
  showRisk: boolean;
  showPoints: boolean;
  showCameras: boolean;
  onCity: (key: CityKey) => void;
  onShowRisk: (value: boolean) => void;
  onShowPoints: (value: boolean) => void;
  onShowCameras: (value: boolean) => void;
  onHistory: () => void;
  onClose: () => void;
}

function Line({ color }: { color: string }) {
  return <span aria-hidden="true" className="inline-block h-1.5 w-6 rounded-full" style={{ backgroundColor: color }} />;
}

function Dot({ color }: { color: string }) {
  return <span aria-hidden="true" className="inline-block h-3 w-3 rounded-full ring-2 ring-white" style={{ backgroundColor: color }} />;
}

/** Bảng "Lớp": bật tắt lớp ngập kèm chú giải, và chọn thành phố. Lớp giao thông và kiểu nền được thêm cùng spec 09. */
export default function LayersPanel({ cities, current, showRisk, showPoints, showCameras, onCity, onShowRisk, onShowPoints, onShowCameras, onHistory, onClose }: Props) {
  return (
    <section
      aria-label="Lớp bản đồ"
      className="pop-in absolute right-3 top-[4.25rem] z-20 max-h-[calc(100dvh-6rem)] w-[min(19rem,calc(100vw-1.5rem))] overflow-y-auto rounded-3xl bg-white p-4 pt-3 shadow-float ring-1 ring-line"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold tracking-[-0.01em] text-ink">Lớp ngập</h2>
        <CloseButton label="Đóng bảng lớp" onClick={onClose} className="-mr-2" />
      </div>
      <label className="flex min-h-11 items-center gap-3 text-[15px] font-medium text-ink">
        <input type="checkbox" className="h-5 w-5 accent-[#0b3a6e]" checked={showRisk} onChange={(event) => onShowRisk(event.target.checked)} />
        Nguy cơ ngập
      </label>
      <ul className="mb-1 ml-8 space-y-1 text-[13px] text-ink-soft">
        <li className="flex items-center gap-2">
          <Line color={LEVEL_COLOR[2]} /> Mức cao
        </li>
        <li className="flex items-center gap-2">
          <Line color={LEVEL_COLOR[1]} /> Mức vừa
        </li>
        <li>Nét đậm: tuyến từng có ghi nhận ngập. Nét nhạt: chỉ do mô hình xếp hạng.</li>
        <li className="flex items-center gap-2">
          <Dot color={REPORT_COLOR.flooded} /> Có người hoặc camera báo ngập
        </li>
        <li className="flex items-center gap-2">
          <Dot color={REPORT_COLOR.clear} /> Có báo không ngập
        </li>
      </ul>
      <label className="flex min-h-11 items-center gap-3 text-[15px] font-medium text-ink">
        <input type="checkbox" className="h-5 w-5 accent-[#0b3a6e]" checked={showPoints} onChange={(event) => onShowPoints(event.target.checked)} />
        Điểm ngập CSGT công bố
      </label>
      <ul className="mb-2 ml-8 space-y-1 text-[13px] text-ink-soft">
        <li className="flex items-center gap-2">
          <Dot color={POINT_COLOR.rain} /> Ngập do mưa
        </li>
        <li className="flex items-center gap-2">
          <Dot color={POINT_COLOR.tide} /> Ngập do triều
        </li>
      </ul>

      <label className="flex min-h-11 items-center gap-3 text-[15px] font-medium text-ink">
        <input type="checkbox" className="h-5 w-5 accent-[#0b3a6e]" checked={showCameras} onChange={(event) => onShowCameras(event.target.checked)} />
        Camera giao thông
      </label>
      <ul className="mb-2 ml-8 space-y-1 text-[13px] text-ink-soft">
        <li className="flex items-center gap-2">
          <Dot color={CAMERA_COLOR} /> Phóng gần để thấy; chạm để xem ảnh
        </li>
      </ul>

      <button
        type="button"
        onClick={onHistory}
        className="mt-1 flex min-h-12 w-full items-center gap-3 rounded-2xl bg-brand-tint px-3 text-left text-brand-strong transition-colors hover:bg-[#d8e5f4]"
      >
        <Icon name="clock" className="h-5 w-5 shrink-0" />
        <span className="min-w-0 flex-1">
          <span className="block text-[15px] font-semibold">Xem lại các trận ngập</span>
          <span className="block text-xs text-ink-soft">App đã báo đúng, sót ở đâu, vì sao</span>
        </span>
      </button>

      <h2 className="mt-3 border-t border-line pt-3 text-base font-semibold tracking-[-0.01em] text-ink">Thành phố</h2>
      <div role="radiogroup" aria-label="Thành phố" className="mt-1 flex flex-col gap-1">
        {cities.map((city) => (
          <button
            key={city.key}
            type="button"
            role="radio"
            aria-checked={city.key === current}
            onClick={() => onCity(city.key)}
            className={`min-h-11 rounded-xl px-3 text-left text-[15px] transition-colors ${
              city.key === current ? "bg-brand-tint font-semibold text-brand-strong" : "text-ink hover:bg-mist"
            }`}
          >
            {city.name}
          </button>
        ))}
      </div>
    </section>
  );
}
