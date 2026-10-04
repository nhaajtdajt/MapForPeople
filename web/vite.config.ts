import path from "node:path";
import { fileURLToPath } from "node:url";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

const here = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Khóa bản đồ VITE_GOONG_MAP_KEY nằm trong .env ở thư mục gốc. Vite chỉ đưa các biến có tiền tố VITE_ vào trình duyệt,
  // nên GOONG_API_KEY và TOMTOM_API_KEY không bao giờ lọt xuống giao diện.
  envDir: path.resolve(here, ".."),
  // Worker của MapLibre được đóng gói riêng dạng module (xem MapView.tsx).
  worker: { format: "es" },
  server: {
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
