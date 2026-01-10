// vite.config.js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Use port 5000 for deployed, 8000 for local development
const BACKEND_PORT = process.env.VITE_BACKEND_PORT || '8000'
const BACKEND_URL = `http://localhost:${BACKEND_PORT}`

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
      '/chat': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
      '/reset-history': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
      '/chat-history': {
        target: BACKEND_URL,
        changeOrigin: true,
      },
      '/uploads': {
        target: BACKEND_URL,
        changeOrigin: true,
      }
    },
  },
})
