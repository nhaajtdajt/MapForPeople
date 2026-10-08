import { describe, expect, it } from "vitest";

import type { Health } from "../api";
import { addressRest, fakePartLabels, formatCoords, statusChipText } from "./format";

const base: Health = {
  ok: true,
  test_tools: false,
  data: "real",
  parts: { risk: "real", evidence: "real", scenarios: "real" },
  traffic: {},
  last_refresh: null,
  last_error: null,
};

describe("formatCoords", () => {
  it("giữ 5 chữ số thập phân, vĩ độ trước kinh độ", () => {
    expect(formatCoords(10.772536, 106.697981)).toBe("10.77254, 106.69798");
  });
});

describe("addressRest", () => {
  it("bỏ phần tên lặp ở đầu địa chỉ", () => {
    expect(addressRest("Chợ Bến Thành", "Chợ Bến Thành, Bến Thành, Hồ Chí Minh")).toBe("Bến Thành, Hồ Chí Minh");
    expect(addressRest("86 Đường Nam Kỳ Khởi Nghĩa", "86 Đường Nam Kỳ Khởi Nghĩa, Sài Gòn, Hồ Chí Minh")).toBe(
      "Sài Gòn, Hồ Chí Minh",
    );
  });

  it("địa chỉ trùng hẳn với tên thì không còn dòng phụ", () => {
    expect(addressRest("Chợ", "Chợ")).toBe("");
  });

  it("địa chỉ không bắt đầu bằng tên thì giữ nguyên", () => {
    expect(addressRest("Highlands", "12 Lê Lợi, Quận 1")).toBe("12 Lê Lợi, Quận 1");
  });

  it("thiếu tên hoặc thiếu địa chỉ", () => {
    expect(addressRest("", "12 Lê Lợi")).toBe("12 Lê Lợi");
    expect(addressRest("Chợ", "")).toBe("");
  });
});

describe("statusChipText", () => {
  it("không hiện gì khi chưa biết trạng thái", () => {
    expect(statusChipText(null)).toBeNull();
  });

  it("không hiện gì khi dữ liệu thật và mọi phần đều thật", () => {
    expect(statusChipText(base)).toBeNull();
  });

  it("dữ liệu mẫu được ghi là dữ liệu mẫu, dù các phần đều thật", () => {
    expect(statusChipText({ ...base, data: "sample" })).toBe("Dữ liệu mẫu");
  });

  it("liệt kê các phần đang là bản giả", () => {
    const health = { ...base, parts: { ...base.parts, evidence: "fake", scenarios: "fake" } } as Health;
    expect(statusChipText(health)).toBe("Đang dùng bản giả: báo cáo người dùng, kịch bản");
    expect(fakePartLabels(health)).toHaveLength(2);
  });
});
