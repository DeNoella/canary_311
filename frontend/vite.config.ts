import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies /api to the FastAPI backend on :8000 so the frontend
// can be served from a single origin with no CORS fuss.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    plugins: [react()],
    server: {
      port: 5173,
      proxy: {
        "/api": {
          target: env.CANARY_API ?? "http://localhost:8000",
          changeOrigin: true,
        },
      },
    },
    build: { outDir: "dist", sourcemap: true },
  };
});
