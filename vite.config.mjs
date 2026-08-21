import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [tailwindcss()],
  publicDir: false,
  build: {
    outDir: "public",
    emptyOutDir: false,
    manifest: "manifest.json",
    rollupOptions: {
      input: "assets/js/main.js",
    },
  },
});
