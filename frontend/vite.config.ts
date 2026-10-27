import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The backend serves routes at the root (/plots, /tasks...). The dev server
// exposes them under /api so frontend routes never collide with API routes.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
