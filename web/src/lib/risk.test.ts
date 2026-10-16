import { describe, expect, it } from "vitest";

import { causeLevel, clockOf, levelExpression, routeLevel, routeReasons, tideLevel, type RouteProps, type TideExtent } from "./risk";

const route: RouteProps = { id: "r1", name: "Trần Xuân Soạn", cls: "secondary", len: 800, br: 1, bt: 2, pt: 120, hr: 0, ht: 3 };
const NONE: TideExtent = { red: 0, coloured: 0 };
const BD2: TideExtent = { red: 2805, coloured: 7012 }; // Phú An 1,50-1,59 m: 2% đầu bảng triều đỏ, tới 5% vàng
const BD1: TideExtent = { red: 0, coloured: 2805 }; // 1,40-1,49 m: 2% đầu bảng vàng

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

describe("tideLevel", () => {
  it("theo thứ hạng triều: dưới `red` là cao, dưới `coloured` là vừa, tuyến không có thứ hạng thì không có mức", () => {
    expect([tideLevel(0, BD2), tideLevel(2804, BD2), tideLevel(2805, BD2), tideLevel(7011, BD2), tideLevel(7012, BD2)]).toEqual([2, 2, 1, 1, 0]);
    expect(tideLevel(undefined, BD2)).toBe(0);
  });
});

describe("routeLevel", () => {
  it("lấy mức lớn hơn giữa mưa và triều", () => {
    expect(routeLevel(route, "alert", NONE)).toBe(1);
    expect(routeLevel(route, "quiet", BD1)).toBe(1);
    expect(routeLevel(route, "watch", BD2)).toBe(2);
    expect(routeLevel(route, "quiet", NONE)).toBe(0);
  });
});

describe("levelExpression", () => {
  it("khớp với routeLevel ở mọi tổ hợp", () => {
    // Tự tính biểu thức trên vài tuyến để chắc bản đồ và thẻ thông tin không bao giờ lệch nhau.
    const evaluate = (expr: unknown, props: Record<string, number | undefined>): number => {
      if (typeof expr === "number") return expr;
      const [op, ...args] = expr as [string, ...unknown[]];
      if (op === "get") return props[args[0] as string] as number;
      if (op === "coalesce") return args.map((a) => evaluate(a, props)).find((v) => v !== undefined) as number;
      if (op === "max") return Math.max(...args.map((a) => evaluate(a, props)));
      if (op === "==") return evaluate(args[0], props) === evaluate(args[1], props) ? 1 : 0;
      if (op === "coalesce") return args.map((a) => evaluate(a, props)).find((v) => v !== undefined) as number;
      if (op === "<") return evaluate(args[0], props) < evaluate(args[1], props) ? 1 : 0;
      if (op === "case") {
        for (let i = 0; i + 1 < args.length; i += 2) if (evaluate(args[i], props)) return evaluate(args[i + 1], props);
        return evaluate(args[args.length - 1], props);
      }
      throw new Error(`toán tử chưa hỗ trợ: ${op}`);
    };
    for (const rain of ["quiet", "watch", "alert"] as const) {
      for (const tide of [NONE, BD1, BD2]) {
        for (const br of [0, 1, 2] as const) {
          for (const pt of [0, 2804, 2805, 7011, 7012, undefined]) {
            for (const ev of [undefined, 1]) {
              expect(evaluate(levelExpression(rain, tide), { br, pt, ev })).toBe(routeLevel({ br, pt, ev }, rain, tide));
            }
          }
        }
      }
    }
  });
});

describe("cầu vượt", () => {
  it("không bao giờ có mức, kể cả khi mưa và triều báo động", () => {
    expect(routeLevel({ ...route, br: 2, pt: 0, ev: 1 }, "alert", BD2)).toBe(0);
  });
});

describe("routeReasons", () => {
  it("chỉ nêu nguyên nhân đang làm tuyến có mức, và nêu lịch sử ngập", () => {
    expect(routeReasons(route, "quiet", BD2, "Phú An 1,55 m")).toEqual([
      "Triều đang lên (Phú An 1,55 m): ở mực nước này bản đồ tô 2.805 tuyến dễ ngập nhất do triều, và tuyến này nằm trong số đó.",
      "Từng có ghi nhận ngập trước 2025: 3 ngày do triều.",
    ]);
  });

  it("tuyến không có mức và không có lịch sử thì không có dòng nào", () => {
    expect(routeReasons({ ...route, ht: 0 }, "watch", NONE)).toEqual([]);
  });
});

describe("clockOf", () => {
  it("lấy giờ phút từ mốc giờ ISO", () => {
    expect(clockOf("2026-10-08T13:00:00+07:00")).toBe("13:00");
  });
});
