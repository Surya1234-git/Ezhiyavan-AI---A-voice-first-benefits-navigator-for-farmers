import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
const target = (globalThis as any).process?.env?.API_TARGET || "http://localhost:8000";   // docker-compose points this at the backend service
export default defineConfig({ plugins: [react()], server: { proxy: { "/api": target } } });
