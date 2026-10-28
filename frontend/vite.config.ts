import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  // Chemins relatifs : la version PC sert les fichiers depuis le disque,
  // et la version autonome depuis un dossier statique.
  base: "./",
  server: {
    port: 5173,
    strictPort: true,
    host: "127.0.0.1",
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    // Tauri cible WebView2 sur Windows 10 et 11.
    target: "chrome105",
    sourcemap: false,
  },
});
