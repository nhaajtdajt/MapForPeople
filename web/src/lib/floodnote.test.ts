import { describe, expect, it } from "vitest";

import type { RiskState } from "../api";
import { statusParts } from "./floodnote";

const base = {
  city: "hcm",
  model_version: "x",
  generated_at: "2026-10-16T19:00:00+07:00",
  rain_source: "x",
  stale: false,
  rain_missing: false,
  error: null,
  hours: [{ valid_time: "2026-10-16T19:00:00+07:00", rain: { state: "quiet", trigger: 0 }, tide: { state: "quiet", trigger: 0 }, counts: { high: 0, medium: 0 } }],
  states: { rain: "quiet", tide: "quiet" },
  model_rain: "watch",
  wet_gauges: 0,
  radar: null,
  overrides: {},
  counts_now: { high: 0, medium: 0 },
  reports: [],
  local: { at: "2026-10-16T12:24:00+00:00", tide: { station: "Phú An", level_m: 1.52, kind: "model", state: "alert" }, gauges: [], errors: [] },
  tide_forecast: [
    { time: "2026-10-16T20:00:00+07:00", level_m: 1.2, state: "quiet" },
    { time: "2026-10-17T06:00:00+07:00", level_m: 1.45, state: "watch" },
  ],
} as unknown as RiskState;

describe("statusParts", () => {
  it("tách mưa, triều và đỉnh triều kế tiếp thành từng ô có mức", () => {
    const parts = statusParts(base)!;
    expect(parts.rain).toEqual({ tone: "quiet", text: "Không có mưa lớn" });
    expect(parts.tide).toEqual({ tone: "alert", text: "Phú An 1,52 m" });
    expect(parts.peak).toEqual({ tone: "watch", text: "Đỉnh 1,45 m lúc 06:00" });
    expect(parts.updated).toBe("19:24");
  });

  it("trạm đo đang mưa lớn làm ô mưa lên mức và được nêu tên trong chi tiết", () => {
    const wet = { ...base, local: { ...base.local!, gauges: [{ name: "Cô Bắc", lat: 0, lon: 0, last_1h_mm: 36, max_3h_mm: 36, total_24h_mm: 40, state: "alert" }] } } as RiskState;
    const parts = statusParts(wet)!;
    expect(parts.rain).toEqual({ tone: "alert", text: "Mưa lớn quanh 1 trạm đo" });
    expect(parts.details[0]).toBe("Trạm đang mưa lớn: Cô Bắc 36 mm/giờ.");
  });

  it("chưa có số liệu thì không có thanh trạng thái", () => {
    expect(statusParts(null)).toBeNull();
  });
});
