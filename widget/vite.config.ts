import { defineConfig } from "vite";
import { resolve } from "path";

export default defineConfig({
  build: {
    cssCodeSplit: false,
    lib: {
      entry: resolve(__dirname, "src/widget.ts"),
      name: "ChatbotWidget",
      formats: ["iife"],
      fileName: () => "widget.js",
    },
  },
});
