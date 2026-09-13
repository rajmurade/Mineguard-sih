import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Built for base /dashboard/ so FastAPI can serve it from that path next to
// the existing /admin-simulator mount. Production API calls use relative paths
// (same origin). The dev server proxies API/WS to the backend on :8000.
export default defineConfig({
  plugins: [react()],
  base: "/dashboard/",
  server: {
    port: 5138,
    proxy: {
      "/incidents": "http://localhost:8000",
      "/workers": "http://localhost:8000",
      "/environmental-readings": "http://localhost:8000",
      "/dashboard": "http://localhost:8000",
      "/reports": "http://localhost:8000",
      "/cv-stream": "http://localhost:8000",
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
  build: {
    outDir: "dist",
  },
});