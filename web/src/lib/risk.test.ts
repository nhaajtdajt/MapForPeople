import { describe, expect, it } from "vitest";

import { causeLevel, clockOf, levelExpression, routeLevel, routeReasons, type RouteProps } from "./risk";

const route: RouteProps = { id: "r1", name: "Trần Xuân Soạn", cls: "secondary", len: 800, br: 1, bt: 2, hr: 0, ht: 3 };

describe("causeLevel", () => {
  it("báo động: nhóm A lên cao, nhóm B lên vừa", () => {
    expect([causeLevel(2, "alert"), causeLevel(1, "alert"), causeLevel(0, "alert")]).toEqual([2, 1, 0]);
  });

  it("cảnh giác: chỉ nhóm A lên vừa", () => {
    expect([causeLevel(2, "watch"), causeLevel(1, "watch"), causeLevel(0, "watch")]).toEqual([1, 0, 0]);
  });

  it("yên: không tuyến nào có mức", () => {
    expect([causeLevel(2, "quiet"), causeLevel(1, "quiet")]).toEqual([0, 0]);
  });
});

describe("routeLevel", () => {
  it("lấy mức lớn hơn giữa mưa và triều", () => {
    expect(routeLevel(route, "alert", "quiet")).toBe(1);
    expect(routeLevel(route, "quiet", "watch")).toBe(1);
    expect(routeLevel(route, "watch", "alert")).toBe(2);
    expect(routeLevel(route, "quiet", "quiet")).toBe(0);
  });
});

describe("levelExpression", () => {
  it("khớp với routeLevel ở mọi tổ hợp trạng thái", () => {
    // Tự tính biểu thức trên vài tuyến để chắc bản đồ và thẻ thông tin không bao giờ lệch nhau.
    const evaluate = (expr: unknown, props: Record<string, number>): number => {
      if (typeof expr === "number") return expr;
      const [op, ...args] = expr as [string, ...unknown[]];
      if (op === "get") return props[args[0] as string];
      if (op === "max") return Math.max(...args.map((a) => evaluate(a, props)));
      if (op === "==") return evaluate(args[0], props) === evaluate(args[1], props) ? 1 : 0;
      if (op === "case") return evaluate(args[0], props) ? evaluate(args[1], props) : evaluate(args[2], props);
      throw new Error(`toán tử chưa hỗ trợ: ${op}`);
    };
    const states = ["quiet", "watch", "alert"] as const;
    for (const rain of states) {
      for (const tide of states) {
        for (const br of [0, 1, 2] as const) {
          for (const bt of [0, 1, 2] as const) {
            expect(evaluate(levelExpression(rain, tide), { br, bt })).toBe(routeLevel({ br, bt }, rain, tide));
          }
        }
      }
    }
  });
});

describe("routeReasons", () => {
  it("chỉ nêu nguyên nhân đang làm tuyến có mức, và nêu lịch sử ngập", () => {
    expect(routeReasons(route, "quiet", "watch")).toEqual([
      "Mô hình xếp tuyến này vào nhóm 5% tuyến dễ ngập nhất do triều, và triều hôm nay ở mức cảnh giác.",
      "Từng có ghi nhận ngập trước 2025: 3 ngày do triều.",
    ]);
  });

  it("tuyến không có mức và không có lịch sử thì không có dòng nào", () => {
    expect(routeReasons({ ...route, ht: 0 }, "watch", "quiet")).toEqual([]);
  });
});

describe("clockOf", () => {
  it("lấy giờ phút từ mốc giờ ISO", () => {
    expect(clockOf("2026-10-08T13:00:00+07:00")).toBe("13:00");
  });
});
