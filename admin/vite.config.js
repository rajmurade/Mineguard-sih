import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev proxy -> FastAPI backend. For the self-served production build the app
// is served from /admin-simulator by FastAPI, so API calls use relative paths.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/environmental-readings": "http://localhost:8000",
      "/emergency-drill": "http://localhost:8000",
      "/incidents": "http://localhost:8000",
      "/workers": "http://localhost:8000",
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
  build: {
    outDir: "dist",
  },
});