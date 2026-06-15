import { fileURLToPath, URL } from "node:url";

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: "0.0.0.0",
    port: Number(process.env.PORT) || 4173,
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    // MapLibre is an isolated, route-lazy vendor chunk (~800 kB) — off the
    // critical path, so the default 500 kB advisory does not apply.
    chunkSizeWarningLimit: 900,
    rollupOptions: {
      output: {
        manualChunks: {
          maplibre: ["maplibre-gl"],
          charts: ["recharts"],
          react: ["react", "react-dom", "react-router-dom"],
        },
      },
    },
  },
});
