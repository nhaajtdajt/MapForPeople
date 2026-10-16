import { beforeEach, describe, expect, it } from "vitest";

import { loadRecent, rememberPlace, RECENT_LIMIT } from "./recent";

const store = new Map<string, string>();
beforeEach(() => {
  store.clear();
  Object.defineProperty(globalThis, "window", {
    value: { localStorage: { getItem: (k: string) => store.get(k) ?? null, setItem: (k: string, v: string) => store.set(k, v) } },
    configurable: true,
  });
});

describe("địa điểm gần đây", () => {
  it("mới nhất lên đầu, gộp chỗ trùng, giữ tối đa năm chỗ", () => {
    for (let i = 0; i < 7; i += 1) rememberPlace({ lat: 10.7 + i * 0.01, lon: 106.7, label: `Chỗ ${i}`, address: "" });
    rememberPlace({ lat: 10.76001, lon: 106.7, label: "Chỗ 6 lần nữa", address: "" });
    const list = loadRecent();
    expect(list).toHaveLength(RECENT_LIMIT);
    expect(list[0].label).toBe("Chỗ 6 lần nữa");
    expect(list.filter((p) => Math.abs(p.lat - 10.76) < 0.001)).toHaveLength(1);
  });

  it("dữ liệu hỏng thì coi như rỗng", () => {
    store.set("floodrisk-recent-places", "{không phải json");
    expect(loadRecent()).toEqual([]);
  });
});
