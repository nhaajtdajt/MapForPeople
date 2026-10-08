import { useEffect, useState } from "react";

import { api, ApiError, serverUrl, type Camera, type CameraReading } from "../api";

const REFRESH_MS = 15_000; // cổng camera đổi ảnh khoảng 12 giây một lần
const TRAFFIC: Record<string, string> = { thong_thoang: "thông thoáng", dong: "đông, vẫn chạy", un_u: "ùn ứ", ket_cung: "kẹt cứng" };
const DEPTH: Record<string, string> = {
  kho: "đường khô", uot: "đường ướt, không ngập", duoi_15cm: "ngập dưới 15 cm", "15_30cm": "ngập 15 tới 30 cm",
  "30_50cm": "ngập 30 tới 50 cm", tren_50cm: "ngập trên 50 cm", khong_ro: "không rõ mặt đường",
};

/** Câu tóm tắt một lượt Gemini đọc camera. */
export function readingSummary(reading: CameraReading): string {
  if (reading.state === "offline") return "Camera hiện không có hình.";
  if (reading.state === "unusable") return "Ảnh không đủ rõ để đọc mặt đường.";
  const water = DEPTH[reading.depth_class ?? ""] ?? (reading.flooded ? "có ngập" : "không ngập");
  const traffic = TRAFFIC[reading.traffic ?? ""];
  return `${water.charAt(0).toUpperCase()}${water.slice(1)}${traffic ? `; giao thông ${traffic}` : ""}.`;
}

interface Props {
  camera: Camera;
  onClose: () => void;
  onRead: () => void; // sau một lượt đọc, để bản đồ lấy lại mức và báo cáo
}

/** Thẻ camera: ảnh đường lúc này, và nút nhờ Gemini đọc ảnh (mỗi lượt mất khoảng nửa phút). */
export default function CameraCard({ camera, onClose, onRead }: Props) {
  const [tick, setTick] = useState(0);
  const [reading, setReading] = useState<CameraReading | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setReading(null);
    setError(null);
    const timer = window.setInterval(() => setTick((value) => value + 1), REFRESH_MS);
    return () => window.clearInterval(timer);
  }, [camera.id]);

  const read = () => {
    setBusy(true);
    setError(null);
    api
      .readCamera(camera.id)
      .then((result) => {
        setReading(result.reading);
        onRead();
      })
      .catch((problem) => setError(problem instanceof ApiError ? problem.message : "Chưa đọc được camera này."))
      .finally(() => setBusy(false));
  };

  return (
    <section
      aria-label="Camera giao thông"
      className="absolute inset-x-0 bottom-0 z-10 rounded-t-2xl bg-white px-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-3 shadow-[0_-4px_16px_rgba(0,0,0,0.15)] sm:inset-x-auto sm:bottom-4 sm:left-4 sm:w-96 sm:rounded-2xl"
    >
      <div className="flex items-start gap-2">
        <div className="min-w-0 flex-1">
          <h2 className="text-lg font-semibold leading-snug text-slate-900">{camera.name}</h2>
          <p className="text-xs text-slate-500">Camera của Cổng thông tin giao thông TP.HCM, ảnh làm mới mỗi 15 giây</p>
        </div>
        <button type="button" aria-label="Đóng thẻ camera" onClick={onClose} className="-mr-2 -mt-1 flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-2xl text-slate-500 hover:bg-slate-100">
          ×
        </button>
      </div>
      {camera.has_image ? (
        <img src={serverUrl(`/api/cameras/${camera.id}.jpg?t=${tick}`)} alt={`Ảnh camera ${camera.name} lúc này`} className="mt-2 aspect-video w-full rounded-lg bg-slate-200 object-cover" />
      ) : (
        <p className="mt-2 rounded-lg bg-slate-100 px-3 py-6 text-center text-sm text-slate-600">Camera này hiện không có hình.</p>
      )}
      {reading && (
        <div role="status" className={`mt-2 rounded-lg border px-3 py-2 text-sm ${reading.flooded ? "border-red-300 bg-red-50 text-red-950" : "border-emerald-300 bg-emerald-50 text-emerald-950"}`}>
          <p className="font-semibold">Gemini đọc: {readingSummary(reading)}</p>
          {reading.evidence && <p className="mt-0.5">{reading.evidence}</p>}
          {reading.confidence !== undefined && <p className="mt-0.5 text-xs">Độ chắc {Math.round(reading.confidence * 100)}%. Lượt đọc đủ chắc được ghi thành một báo cáo trên tuyến này.</p>}
        </div>
      )}
      {error && <p role="alert" className="mt-2 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-950">{error}</p>}
      {camera.has_image && (
        <button type="button" disabled={busy} onClick={read} className="mt-3 min-h-11 w-full rounded-lg bg-blue-700 px-3 text-sm font-medium text-white enabled:hover:bg-blue-800 disabled:opacity-60">
          {busy ? "Đang đọc, khoảng nửa phút…" : "Nhờ Gemini đọc ảnh này"}
        </button>
      )}
    </section>
  );
}
