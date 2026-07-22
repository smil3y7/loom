import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { readFileSync } from 'fs'
import { resolve } from 'path'

// Enoten vir resnice za verzijo — bere /VERSION (koren repozitorija),
// isto datoteko kot backend (loom/lib/version.py). Bere se ob vsakem
// buildu, torej je vedno pravilno brez ročnega koraka — za razliko od
// loom-extension/manifest.json, kjer Chrome zahteva statičen niz in
// zato rabi scripts/sync-extension-version.js pred pakiranjem.
const appVersion = readFileSync(
  resolve(__dirname, '..', 'VERSION'), 'utf-8'
).trim()

export default defineConfig({
  plugins: [react()],
  define: {
    __APP_VERSION__: JSON.stringify(appVersion),
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  },
  test: {
    environment: 'jsdom',
    globals: true,
  }
})
