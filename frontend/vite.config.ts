import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// The backend serves routes at the root (/plots, /tasks...). The dev server
// exposes them under /api so frontend routes never collide with API routes.
// `make dev BACKEND_PORT=8001` points the proxy elsewhere through
// FIELDPILOT_API_TARGET; nothing here needs editing.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "FIELDPILOT_");
  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: env.FIELDPILOT_API_TARGET ?? "http://localhost:8000",
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ""),
        },
      },
    },
  };
});
