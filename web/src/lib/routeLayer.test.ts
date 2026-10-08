import { describe, expect, it } from "vitest";

import { emptySelectedRouteFilter } from "./routeLayer";

describe("bộ lọc lộ trình", () => {
  it("dùng biểu thức GeoJSON hợp lệ khi chưa chọn lộ trình", () => {
    expect(emptySelectedRouteFilter()).toEqual(["==", ["get", "route_id"], -1]);
  });
});
