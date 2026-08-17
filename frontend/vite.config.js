import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// Vite config for the YantraSetu frontend.
// - react(): enables React + fast refresh
// - tailwindcss(): Tailwind v4's official Vite plugin (no separate PostCSS config)
// - server.proxy: forwards /api calls to the FastAPI backend during dev so we
//   avoid CORS headaches and can use relative URLs from the frontend.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      // Business endpoints (Phase 1+) live under /api on the backend.
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      // Health probe sits at the backend root.
      '/health': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
