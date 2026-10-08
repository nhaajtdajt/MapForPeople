import type { City, CityKey } from "../api";
import { LEVEL_COLOR, POINT_COLOR } from "../MapView";

interface Props {
  cities: City[];
  current: CityKey;
  showRisk: boolean;
  showPoints: boolean;
  onCity: (key: CityKey) => void;
  onShowRisk: (value: boolean) => void;
  onShowPoints: (value: boolean) => void;
  onClose: () => void;
}

function Line({ color }: { color: string }) {
  return <span aria-hidden="true" className="inline-block h-1.5 w-6 rounded-full" style={{ backgroundColor: color }} />;
}

function Dot({ color }: { color: string }) {
  return <span aria-hidden="true" className="inline-block h-3 w-3 rounded-full ring-2 ring-white" style={{ backgroundColor: color }} />;
}

/** Bảng "Lớp": bật tắt lớp ngập kèm chú giải, và chọn thành phố. Lớp giao thông và kiểu nền được thêm cùng spec 09. */
export default function LayersPanel({ cities, current, showRisk, showPoints, onCity, onShowRisk, onShowPoints, onClose }: Props) {
  return (
    <section
      aria-label="Lớp bản đồ"
      className="absolute right-3 top-[4.25rem] z-20 max-h-[calc(100dvh-6rem)] w-72 overflow-y-auto rounded-xl bg-white p-3 shadow-lg ring-1 ring-slate-200"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">Lớp ngập</h2>
        <button type="button" aria-label="Đóng bảng lớp" onClick={onClose} className="flex h-11 w-11 items-center justify-center rounded-full text-xl text-slate-500 hover:bg-slate-100">
          ×
        </button>
      </div>
      <label className="flex min-h-11 items-center gap-3 text-base text-slate-900">
        <input type="checkbox" className="h-5 w-5" checked={showRisk} onChange={(event) => onShowRisk(event.target.checked)} />
        Nguy cơ ngập theo mô hình
      </label>
      <ul className="mb-1 ml-8 space-y-1 text-sm text-slate-700">
        <li className="flex items-center gap-2">
          <Line color={LEVEL_COLOR[2]} /> Mức cao
        </li>
        <li className="flex items-center gap-2">
          <Line color={LEVEL_COLOR[1]} /> Mức vừa
        </li>
        <li>Nét đậm: tuyến từng có ghi nhận ngập. Nét nhạt: chỉ do mô hình xếp hạng.</li>
      </ul>
      <label className="flex min-h-11 items-center gap-3 text-base text-slate-900">
        <input type="checkbox" className="h-5 w-5" checked={showPoints} onChange={(event) => onShowPoints(event.target.checked)} />
        Điểm ngập CSGT công bố
      </label>
      <ul className="mb-2 ml-8 space-y-1 text-sm text-slate-700">
        <li className="flex items-center gap-2">
          <Dot color={POINT_COLOR.rain} /> Ngập do mưa
        </li>
        <li className="flex items-center gap-2">
          <Dot color={POINT_COLOR.tide} /> Ngập do triều
        </li>
      </ul>

      <h2 className="border-t border-slate-200 pt-2 text-sm font-semibold text-slate-900">Thành phố</h2>
      <div role="radiogroup" aria-label="Thành phố" className="mt-1 flex flex-col gap-1">
        {cities.map((city) => (
          <button
            key={city.key}
            type="button"
            role="radio"
            aria-checked={city.key === current}
            onClick={() => onCity(city.key)}
            className={`min-h-11 rounded-lg px-3 text-left text-base ${
              city.key === current ? "bg-blue-50 font-medium text-blue-800 ring-1 ring-blue-300" : "text-slate-900 hover:bg-slate-50"
            }`}
          >
            {city.name}
          </button>
        ))}
      </div>
    </section>
  );
}
