// This project was developed with assistance from AI tools.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8090",
      "/healthz": "http://localhost:8090",
      "/readyz": "http://localhost:8090",
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
  },
});
