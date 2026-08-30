import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev server proxies API to the FastAPI backend so the SPA can use relative paths
// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/auth': 'http://127.0.0.1:8000',
    },
  },
})
