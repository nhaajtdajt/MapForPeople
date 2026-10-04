import { describe, expect, it } from "vitest";

import { loadView, saveView, type SavedView } from "./viewstore";

function memory(initial: Record<string, string> = {}) {
  const data = { ...initial };
  return {
    data,
    getItem: (key: string) => data[key] ?? null,
    setItem: (key: string, value: string) => {
      data[key] = value;
    },
  };
}

const view: SavedView = { city: "danang", center: [108.21, 16.06], zoom: 13.5 };

describe("viewstore", () => {
  it("lưu rồi đọc lại đúng khung nhìn", () => {
    const store = memory();
    saveView(view, store);
    expect(loadView(store)).toEqual(view);
  });

  it("chưa có gì thì trả null", () => {
    expect(loadView(memory())).toBeNull();
  });

  it("không có bộ nhớ trình duyệt thì không ném lỗi", () => {
    expect(loadView(null)).toBeNull();
    expect(() => saveView(view, null)).not.toThrow();
  });

  it("bộ nhớ ném lỗi khi ghi thì bỏ qua", () => {
    const broken = {
      getItem: () => null,
      setItem: () => {
        throw new Error("đầy");
      },
    };
    expect(() => saveView(view, broken)).not.toThrow();
  });

  it.each([
    ["không phải JSON", "{hỏng"],
    ["thành phố lạ", JSON.stringify({ city: "hanoi", center: [105.8, 21.0], zoom: 12 })],
    ["tọa độ không phải số", JSON.stringify({ city: "hcm", center: ["a", 10], zoom: 12 })],
    ["tọa độ ngoài phạm vi", JSON.stringify({ city: "hcm", center: [300, 10], zoom: 12 })],
    ["mức phóng quá lớn", JSON.stringify({ city: "hcm", center: [106.7, 10.78], zoom: 99 })],
    ["thiếu trường", JSON.stringify({ city: "hcm" })],
  ])("giá trị hỏng (%s) được bỏ qua", (_name, raw) => {
    expect(loadView(memory({ "floodrisk-view": raw }))).toBeNull();
  });
});
