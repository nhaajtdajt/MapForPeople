import { useEffect, useState } from "react";

import { api, ApiError, serverUrl, type Camera, type CameraReading } from "../api";
import Icon, { CloseButton } from "./Icon";

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
      className="sheet-in absolute inset-x-0 bottom-0 z-10 max-h-[80dvh] overflow-y-auto rounded-t-3xl bg-white px-4 pb-[max(1rem,env(safe-area-inset-bottom))] pt-2.5 shadow-sheet sm:inset-x-auto sm:bottom-4 sm:left-4 sm:w-[26rem] sm:rounded-3xl sm:shadow-float"
    >
      <div className="mx-auto mb-2 h-1 w-10 rounded-full bg-line sm:hidden" aria-hidden="true" />
      <div className="flex items-start gap-2">
        <span className="mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-mist text-ink-soft">
          <Icon name="camera" className="h-[18px] w-[18px]" />
        </span>
        <div className="min-w-0 flex-1 pt-1">
          <h2 className="text-[17px] font-semibold leading-snug tracking-[-0.01em] text-ink">{camera.name}</h2>
          <p className="mt-0.5 text-xs text-ink-faint">Cổng thông tin giao thông TP.HCM · ảnh làm mới mỗi 15 giây</p>
        </div>
        <CloseButton label="Đóng thẻ camera" onClick={onClose} className="-mr-2" />
      </div>
      {camera.has_image ? (
        <div className="relative mt-3 overflow-hidden rounded-2xl bg-mist">
          <img src={serverUrl(`/api/cameras/${camera.id}.jpg?t=${tick}`)} alt={`Ảnh camera ${camera.name} lúc này`} className="aspect-video w-full object-cover" />
          <span className="absolute left-2 top-2 flex items-center gap-1.5 rounded-full bg-ink/75 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide text-white">
            <span aria-hidden="true" className="h-1.5 w-1.5 animate-pulse rounded-full bg-red-400" />
            Trực tiếp
          </span>
        </div>
      ) : (
        <p className="mt-3 rounded-2xl bg-mist px-3 py-8 text-center text-sm text-ink-faint">Camera này hiện không có hình.</p>
      )}
      {reading && (
        <div role="status" className={`mt-3 flex gap-2.5 rounded-2xl px-3.5 py-3 text-sm ${reading.flooded ? "bg-danger-tint text-danger-ink" : "bg-safe-tint text-safe-ink"}`}>
          <Icon name={reading.flooded ? "alert" : "check"} className={`mt-0.5 h-[18px] w-[18px] shrink-0 ${reading.flooded ? "text-danger" : "text-safe"}`} />
          <div className="min-w-0">
            <p className="font-semibold leading-snug">Gemini đọc: {readingSummary(reading)}</p>
            {reading.evidence && <p className="mt-1 leading-snug opacity-90">{reading.evidence}</p>}
            {reading.confidence !== undefined && <p className="mt-1 text-xs opacity-80">Độ chắc {Math.round(reading.confidence * 100)}%. Lượt đọc đủ chắc được ghi thành một báo cáo trên tuyến này.</p>}
          </div>
        </div>
      )}
      {error && <p role="alert" className="mt-3 rounded-2xl bg-caution-tint px-3.5 py-3 text-sm text-caution-ink">{error}</p>}
      {camera.has_image && (
        <button type="button" disabled={busy} onClick={read} className="mt-3 flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-brand px-3 text-sm font-semibold text-white transition-colors enabled:hover:bg-brand-strong enabled:active:scale-[0.99] disabled:opacity-70">
          <Icon name="sparkle" className={`h-[18px] w-[18px] ${busy ? "animate-spin" : ""}`} />
          {busy ? "Đang đọc ảnh, khoảng nửa phút…" : "Nhờ Gemini đọc mặt đường"}
        </button>
      )}
    </section>
  );
}
