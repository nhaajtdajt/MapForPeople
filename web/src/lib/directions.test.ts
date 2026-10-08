import { describe, expect, it } from "vitest";

import { floodSummary, buildRouteParams, chooseRoute, formatArrival, formatDistance, formatDuration, prioritizeRoutes } from "./directions";

describe("định dạng chỉ đường", () => {
  it("hiển thị thời gian dưới một phút rõ ràng", () => {
    expect(formatDuration(20)).toBe("Dưới 1 phút");
  });

  it("gộp giờ và phút trong thời gian hành trình", () => {
    expect(formatDuration(4320)).toBe("1 giờ 12 phút");
    expect(formatDuration(1250)).toBe("21 phút");
  });

  it("định dạng quãng đường theo mét hoặc ki-lô-mét", () => {
    expect(formatDistance(845)).toBe("845 m");
    expect(formatDistance(1560)).toBe("1,6 km");
  });

  it("hiển thị giờ đến theo giờ Việt Nam", () => {
    expect(formatArrival("2026-10-08T08:05:00+07:00")).toBe("08:05");
  });
});

describe("chọn và gọi lộ trình", () => {
  const routes = [
    { id: 1, recommended: false },
    { id: 2, recommended: true },
  ];

  it("xếp lộ trình đề xuất lên đầu rồi sắp các lựa chọn còn lại theo thời gian", () => {
    const ordered = prioritizeRoutes([
      { id: 0, recommended: false, duration_s: 100 },
      { id: 1, recommended: true, duration_s: 200 },
      { id: 2, recommended: false, duration_s: 50 },
    ]);
    expect(ordered.map((route) => route.id)).toEqual([1, 2, 0]);
  });
  it("ưu tiên lộ trình được máy chủ đề xuất", () => {
    expect(chooseRoute(routes)).toBe(routes[1]);
  });

  it("chọn lộ trình đầu tiên khi không có nhãn đề xuất", () => {
    expect(chooseRoute([{ id: 1, recommended: false }])).toEqual({ id: 1, recommended: false });
    expect(chooseRoute([])).toBeNull();
  });

  it("dựng đúng tham số gốc, đích và loại xe", () => {
    expect(
      buildRouteParams({ lat: 10.7725, lon: 106.698 }, { lat: 10.8156, lon: 106.664 }, "car"),
    ).toEqual({ city: "hcm", origin: "10.7725,106.698", destination: "10.8156,106.664", vehicle: "car" });
  });
});

describe("floodSummary", () => {
  const segments = [
    { name: "Lê Văn Sỹ", basis: "report", length_m: 300 },
    { name: "Phan Đình Giót", basis: "history", length_m: 636 },
  ];

  it("ưu tiên nói về đường đang có báo ngập", () => {
    expect(floodSummary({ confirmed_m: 300, history_m: 636, segments })).toEqual({ tone: "bad", text: "Qua 300 m đường đang có báo ngập: Lê Văn Sỹ" });
  });

  it("không có báo ngập thì nói về đường từng ngập", () => {
    expect(floodSummary({ confirmed_m: 0, history_m: 636, segments })?.tone).toBe("warn");
  });

  it("lộ trình sạch thì nói rõ là sạch, và không có mô hình thì không nói gì", () => {
    expect(floodSummary({ confirmed_m: 0, history_m: 0, segments: [] })?.tone).toBe("good");
    expect(floodSummary(null)).toBeNull();
  });
});
