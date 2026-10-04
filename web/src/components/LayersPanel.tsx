import type { City, CityKey } from "../api";

interface Props {
  cities: City[];
  current: CityKey;
  onCity: (key: CityKey) => void;
  onClose: () => void;
}

/** Bảng "Lớp". Hiện chỉ có chọn thành phố; bật tắt lớp ngập, giao thông và kiểu nền được thêm cùng spec 02 và 09. */
export default function LayersPanel({ cities, current, onCity, onClose }: Props) {
  return (
    <section
      aria-label="Lớp bản đồ"
      className="absolute right-3 top-[4.25rem] z-20 w-64 rounded-xl bg-white p-3 shadow-lg ring-1 ring-slate-200"
    >
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-900">Thành phố</h2>
        <button type="button" aria-label="Đóng bảng lớp" onClick={onClose} className="flex h-11 w-11 items-center justify-center rounded-full text-xl text-slate-500 hover:bg-slate-100">
          ×
        </button>
      </div>
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
